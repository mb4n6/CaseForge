#!/usr/bin/env python3
# =====================================================================
# gen_ios_location.py  —  iOS locationd cache_encryptedB.db (Anna)
# ---------------------------------------------------------------------
# Reales iLEAPP-Schema: Tabellen CellLocation & WifiLocation mit
# MCC/MNC/LAC/CI bzw. MAC + Lat/Lon + Timestamp (Apple-CFAbsoluteTime).
# Projiziert Annas Bewegung am 25.01: Nachtruhe Home -> Aufbruch 07:33
# -> Annaeherung Waldweg-Parkplatz bis 07:52 (letzte Ortung).
# =====================================================================
import os
import sys
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
sys.path.insert(0, HERE)
import case_master_io as cmio
IOS = os.environ.get('WALDWEG_IOS_FS', os.path.join(ROOT, '01_ios_full_fs'))
DB = os.path.join(IOS, 'private/var/mobile/Library/Caches/locationd/cache_encryptedB.db')

APPLE = 978307200


def cf(iso):
    return datetime.fromisoformat(iso).timestamp() - APPLE


# (iso, lat, lon, mcc, mnc, lac, ci)  — Mobilfunkzellen (Referenz-Fallback)
FALLBACK_CELLS = [
    ("2026-01-24T23:10:00+01:00", 48.7758, 9.1829, 262, 2, 4101, 11001),  # Home (Nacht)
    ("2026-01-25T07:33:00+01:00", 48.7740, 9.1900, 262, 2, 4101, 11002),  # Aufbruch
    ("2026-01-25T07:45:00+01:00", 48.7520, 9.2300, 262, 2, 4107, 11045),  # unterwegs
    ("2026-01-25T07:52:00+01:00", 48.7320, 9.2470, 262, 2, 4107, 11050),  # nahe Waldweg (letzte)
]
# WLAN-Ortungen (zuhause / Büro) (Referenz-Fallback)
FALLBACK_WIFIS = [
    ("2026-01-24T22:30:00+01:00", 48.7758, 9.1829, "a4:5e:60:11:22:33"),  # Home-WLAN
    ("2026-01-24T18:40:00+01:00", 48.7770, 9.1880, "c0:25:e9:aa:bb:cc"),  # Supermarkt-Umfeld
]


def resolve_points():
    cm = cmio.load_master()
    owner = cmio.device_owner("ios", cm)
    cells, wifis = cmio.location_track(owner, cm) if owner else (None, None)
    if cells is None and wifis is None:
        return FALLBACK_CELLS, FALLBACK_WIFIS, "Referenz-Fallback"
    return (cells or []), (wifis or []), "Master"


def main():
    CELLS, WIFIS, src = resolve_points()
    print(f"Standort-Inhaltsquelle: {src} (Zellen={len(CELLS)}, WLAN={len(WIFIS)})")
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(DB + s):
            os.remove(DB + s)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE CellLocation (
        MCC INTEGER, MNC INTEGER, LAC INTEGER, CI INTEGER,
        Timestamp REAL, Latitude REAL, Longitude REAL,
        HorizontalAccuracy REAL, Altitude REAL, Speed REAL, Course REAL,
        Confidence INTEGER
    );
    CREATE TABLE WifiLocation (
        MAC TEXT, Timestamp REAL, Latitude REAL, Longitude REAL,
        HorizontalAccuracy REAL, Altitude REAL, Speed REAL, Course REAL,
        Confidence INTEGER
    );
    """)
    cur = con.cursor()
    for iso, lat, lon, mcc, mnc, lac, ci in CELLS:
        cur.execute("""INSERT INTO CellLocation
            (MCC,MNC,LAC,CI,Timestamp,Latitude,Longitude,HorizontalAccuracy,
             Altitude,Speed,Course,Confidence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mcc, mnc, lac, ci, cf(iso), lat, lon, 65.0, 250.0, -1, -1, 70))
    for iso, lat, lon, mac in WIFIS:
        cur.execute("""INSERT INTO WifiLocation
            (MAC,Timestamp,Latitude,Longitude,HorizontalAccuracy,Altitude,
             Speed,Course,Confidence) VALUES (?,?,?,?,?,?,?,?,?)""",
            (mac, cf(iso), lat, lon, 30.0, 250.0, -1, -1, 80))
    con.commit(); con.close()
    print(f"cache_encryptedB.db: {len(CELLS)} Cell + {len(WIFIS)} WiFi "
          f"-> {os.path.relpath(DB, ROOT)}")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("""SELECT Timestamp,Latitude,Longitude FROM CellLocation
                          ORDER BY Timestamp""").fetchall()
    print("Anna Cell-Spur (lokal):")
    for ts, la, lo in rows:
        dt = datetime.utcfromtimestamp(ts + APPLE)
        print(f"  {dt:%H:%M} UTC  {la:.4f},{lo:.4f}")
    con.close()


if __name__ == "__main__":
    main()
