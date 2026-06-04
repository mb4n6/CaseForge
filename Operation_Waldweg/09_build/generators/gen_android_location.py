#!/usr/bin/env python3
# =====================================================================
# gen_android_location.py  —  Daniels Standort + PI#1 (WiFi vs. Cell)
# ---------------------------------------------------------------------
# Materialisiert planted_inconsistency #1: Daniels Telefon meldet
# 07:38 eine WLAN-Assoziation "Home" (ALT/zwischengespeichert), waehrend
# der Mobilfunk-Standort 08:02 nahe Waldweg liegt. Zwei Quellen, zwei
# Qualitaeten — die Lernenden muessen die Quellqualitaet werten.
#
# Schema bewusst einfach & dokumentiert (kein fixes Hersteller-Format):
#   wifi_assoc   — verbundene WLANs mit last_seen (Unix-ms)
#   network_location_cache — netz/zellbasierte Standortpunkte (Unix-ms)
# =====================================================================
import os
import sys
import sqlite3
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
sys.path.insert(0, HERE)
import case_master_io as cmio
AND = os.environ.get('WALDWEG_AND_FS', os.path.join(ROOT, '02_android_full_fs'))
DB = os.path.join(AND, 'data/data/com.google.android.gms/databases/location_cache.db')


def ms(iso):
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


# WLAN-Assoziationen: Home-WLAN zuletzt 07:38 "gesehen" (stale cache!) (Fallback)
FALLBACK_WIFI = [
    ("Home-WLAN",  "a4:5e:60:11:22:33", "2026-01-25T07:38:00+01:00", 48.7758, 9.1829),
    ("Werkstatt",  "d8:9e:3f:44:55:66", "2026-01-24T16:10:00+01:00", 48.7510, 9.2100),
]
# Netzwerk-/Zell-Standort: 08:02 nahe Waldweg (schwache Genauigkeit) (Fallback)
FALLBACK_NETLOC = [
    ("2026-01-25T07:15:00+01:00", 48.7758, 9.1829, 40,  "wifi"),   # Home (frueh, gut)
    ("2026-01-25T08:02:00+01:00", 48.7330, 9.2460, 1400, "cell"),  # nahe Waldweg, ungenau
    ("2026-01-25T08:31:00+01:00", 48.7505, 9.2090, 900,  "cell"),  # Richtung Werkstatt
]


def resolve_loc():
    cm = cmio.load_master()
    owner = cmio.device_owner("android", cm)
    cells, wifis = cmio.location_track(owner, cm) if owner else (None, None)
    if cells is None and wifis is None:
        return FALLBACK_WIFI, FALLBACK_NETLOC, "Referenz-Fallback"
    wifi = [("WLAN", b, iso, la, lo) for iso, la, lo, b in (wifis or [])]
    netloc = [(iso, la, lo, 60, "wifi") for iso, la, lo, _b in (wifis or [])]
    netloc += [(iso, la, lo, 1200, "cell") for iso, la, lo, *_ in (cells or [])]
    return wifi, netloc, "Master"


def main():
    WIFI, NETLOC, src = resolve_loc()
    print(f"Standort-Inhaltsquelle: {src} (WLAN={len(WIFI)}, NetLoc={len(NETLOC)})")
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(DB + s):
            os.remove(DB + s)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE wifi_assoc (
        ssid TEXT, bssid TEXT, last_seen INTEGER,
        latitude REAL, longitude REAL
    );
    CREATE TABLE network_location_cache (
        timestamp INTEGER, latitude REAL, longitude REAL,
        accuracy_m INTEGER, source TEXT
    );
    """)
    cur = con.cursor()
    for ssid, bssid, iso, la, lo in WIFI:
        cur.execute("INSERT INTO wifi_assoc VALUES (?,?,?,?,?)",
                    (ssid, bssid, ms(iso), la, lo))
    for iso, la, lo, acc, src in NETLOC:
        cur.execute("INSERT INTO network_location_cache VALUES (?,?,?,?,?)",
                    (ms(iso), la, lo, acc, src))
    con.commit(); con.close()
    print(f"location_cache.db -> {os.path.relpath(DB, ROOT)}")

    tz = timezone(timedelta(hours=1))
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("PI#1 — Quellkonflikt:")
    w = con.execute("SELECT ssid,last_seen,latitude,longitude FROM wifi_assoc WHERE ssid='Home-WLAN'").fetchone()
    c = con.execute("SELECT timestamp,latitude,longitude,accuracy_m FROM network_location_cache WHERE source='cell' ORDER BY timestamp LIMIT 1").fetchone()
    if w and c:
        wt = datetime.fromtimestamp(w[1]/1000, tz)
        print(f"  WiFi  {wt:%H:%M} '{w[0]}' @ {w[2]:.4f},{w[3]:.4f}  (gecacht/stale)")
        ct = datetime.fromtimestamp(c[0]/1000, tz)
        print(f"  Cell  {ct:%H:%M} @ {c[1]:.4f},{c[2]:.4f}  (±{c[3]}m, nahe Waldweg)")
        print("  -> WLAN 'Home' steht der Cell-Ortung nahe Waldweg entgegen.")
    else:
        print("  (Master-Track ohne Referenz-PI#1-Konstellation — Hinweis übersprungen.)")
    con.close()


if __name__ == "__main__":
    main()
