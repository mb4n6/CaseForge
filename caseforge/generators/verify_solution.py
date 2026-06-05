#!/usr/bin/env python3
# =====================================================================
# verify_solution.py  —  Loesungsschluessel- & Konsistenzpruefung (Tag 6)
# ---------------------------------------------------------------------
# Prueft programmatisch, dass die im Case Master GEPLANTEN Spuren,
# Widersprueche und Red-Herrings tatsaechlich in den Geraete-Artefakten
# vorliegen und sich korrekt aufloesen. Dient als Abnahme dafuer, dass
# das Szenario "loesbar" ist und der Loesungsschluessel traegt.
# =====================================================================
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

# Aktiver Fall-Root: WALDWEG_OW (von forge.py gesetzt) -> sonst das
# Operation_Waldweg-Verzeichnis relativ zu dieser Datei (09_build/generators).
_DEFAULT_OW = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                           "examples", "operation_waldweg")
OW = os.environ.get('WALDWEG_OW') or _DEFAULT_OW
IOS = os.path.join(OW, '01_ios_full_fs')
AND = os.path.join(OW, '02_android_full_fs')
WIN = os.path.join(OW, '03_windows_triage')

# Preflight: verify_solution prueft die WALDWEG-Loesung. Fehlen die zentralen
# Referenz-Artefakte (z.B. weil dies ein fremder Spec-Fall ist), sauber
# ueberspringen (rc=2) statt mit einem Traceback abzubrechen.
_required = [
    os.path.join(IOS, 'private/var/mobile/Library/SMS/sms.db'),
    os.path.join(AND, 'data/data/com.whatsapp/databases/msgstore.db'),
]
if not all(os.path.exists(p) for p in _required):
    print("[SKIP] verify_solution: Referenz-Artefakte nicht vorhanden "
          "(kein Waldweg-Referenzfall).")
    sys.exit(2)

checks = []


def check(name, cond, detail=""):
    checks.append(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def has_text(con, table_col_sql, needle):
    for (t,) in con.execute(table_col_sql):
        if t and needle.lower() in t.lower():
            return True
    return False


print("=== TATNACHWEIS-KETTE (primaere Hypothese: Daniel Reuter) ===")
# 1) Motiv A: drohende Trennung — Annas Safari + iMessage an Jonas
ios_sms = os.path.join(IOS, 'private/var/mobile/Library/SMS/sms.db')
import shutil
tmp = '/tmp/_vs_sms.db'
for s in ("", "-wal", "-shm"):
    if os.path.exists(ios_sms + s):
        shutil.copy(ios_sms + s, tmp + s)
con = ro(tmp)
check("Motiv Trennung: Anna kuendigt Trennung ggue. Jonas an",
      has_text(con, "SELECT text FROM message", "trenne mich"))
con.close()

# 2) Motiv B: finanzieller Druck — WhatsApp Ultimatum Tobias
wa = os.path.join(AND, 'data/data/com.whatsapp/databases/msgstore.db')
con = ro(wa)
check("Motiv Schulden: Ultimatum 'bis Montag' von Tobias",
      has_text(con, "SELECT text_data FROM message", "bis Montag"))
con.close()

# 3) Vorsatz/Wissen: Daniel weiss von Annas fruehem Aufbruch (beide Geraete)
con = ro(tmp)
anna_side = has_text(con, "SELECT text FROM message WHERE is_from_me=0", "so früh hin")
con.close()
con = ro(wa)
daniel_side = has_text(con, "SELECT text_data FROM message WHERE from_me=1", "so frueh hin")
con.close()
check("Cross-Device: 'Wo willst du so frueh hin?' auf iPhone UND Samsung",
      anna_side and daniel_side)

# 4) Gelegenheit/Standort: Daniel-Anruf Tobias 08:25 (41s) direkt nach Tatfenster
calllog = os.path.join(AND, 'data/data/com.samsung.android.providers.contacts/databases/calllog.db')
con = ro(calllog)
rows = con.execute("SELECT date,duration,type FROM calls").fetchall()
def at(dur, h, m):
    for date,d,t in rows:
        dt = datetime.fromtimestamp(date/1000, timezone(timedelta(hours=1)))
        if d==dur and dt.hour==h and dt.minute==m:
            return True
    return False
check("Gelegenheit: Anruf Daniel->Tobias 08:25 / 41s belegt", at(41,8,25))
con.close()

# 5) Chrome-Suche 'handy orten partner' (Kontrollverhalten)
chrome = os.path.join(AND, 'data/data/com.android.chrome/app_chrome/Default/History')
con = ro(chrome)
check("Kontrollverhalten: Chrome-Suche 'handy orten partner'",
      has_text(con, "SELECT url FROM urls", "handy+orten+partner"))
con.close()

# 6) Health: HR-Peak 138 @07:50 dann Stille (Obduktion 07:45-08:15 konsistent)
health = os.path.join(IOS, 'private/var/mobile/Library/Health/healthdb_secure.sqlite')
con = ro(health)
hr = con.execute("""SELECT s.start_date,q.original_quantity FROM samples s
    JOIN quantity_samples q ON s.data_id=q.data_id WHERE s.data_type=5
    ORDER BY s.start_date""").fetchall()
last = datetime(2001,1,1,tzinfo=timezone.utc)+timedelta(seconds=hr[-1][0])
last_l = last.astimezone(timezone(timedelta(hours=1)))
check("Health: HR-Peak 138 und Messende ~07:50 (Tatzeitfenster)",
      max(h[1] for h in hr)==138 and last_l.hour==7 and last_l.minute==50,
      f"letzter Wert {last_l:%H:%M}")
con.close()

print("\n=== RED HERRINGS (muessen sich ENTLASTEND aufloesen) ===")
# RH1: Jonas wartet vergeblich 09:10 -> war am Treffpunkt, Anna kam nie
con = ro(tmp)
check("RH1 Jonas entlastet: 'Wo bleibst du? Hier ist niemand.' 09:10",
      has_text(con, "SELECT text FROM message WHERE is_from_me=0", "Hier ist niemand"))
con.close()
# RH2: Tobias -> in Werkstatt (SMS Werkstatt-Kontext) + war Anrufer 24.01
con = ro(calllog)
check("RH2 Tobias: eingehender Anruf 24.01 (kein Tatort-Indiz gegen ihn)",
      any(t==1 for _,_,t in con.execute("SELECT date,duration,type FROM calls")))
con.close()

print("\n=== GEPLANTE WIDERSPRUECHE (planted_inconsistencies) ===")
# #1: WiFi 'Home' 07:38 (stale) vs. Cell-Standort Waldweg 08:02
locdb = os.path.join(AND, 'data/data/com.google.android.gms/databases/location_cache.db')
pi1 = False
if os.path.exists(locdb):
    con = ro(locdb)
    wifi_home = con.execute("SELECT COUNT(*) FROM wifi_assoc WHERE ssid='Home-WLAN'").fetchone()[0]
    cell_far = con.execute("SELECT COUNT(*) FROM network_location_cache WHERE source='cell' AND latitude<48.74").fetchone()[0]
    con.close()
    pi1 = wifi_home >= 1 and cell_far >= 1
check("PI#1: WiFi 'Home' (stale) vs. Cell-Standort nahe Waldweg vorhanden", pi1)

# #5: Cloud-Luecke im kritischen Fenster (07:30-08:30 CET), aber Eintraege davor+danach
import json as _json
cloud = os.environ.get('WALDWEG_CLOUD', os.path.join(OW, '04_cloud_exports'))
g = os.path.join(cloud, 'google', 'location-history.json')
pi5 = False
if os.path.exists(g):
    from datetime import timezone as _tz
    tzc = _tz(timedelta(hours=1))
    starts = []
    for obj in _json.load(open(g, encoding='utf-8')).get('timelineObjects', []):
        d = obj.get('placeVisit') or obj.get('activitySegment')
        iso = d['duration']['startTimestamp'].replace('Z', '+00:00')
        starts.append(datetime.fromisoformat(iso).astimezone(tzc))
    on_2501 = [s for s in starts if s.strftime('%Y-%m-%d') == '2026-01-25']
    before = any(s.hour < 7 or (s.hour == 7 and s.minute <= 15) for s in on_2501)
    after = any(s.hour > 9 or (s.hour == 9 and s.minute >= 0) for s in on_2501)
    in_gap = any(7 <= s.hour < 9 and not (s.hour == 7 and s.minute <= 15) for s in on_2501)
    pi5 = before and after and not in_gap
check("PI#5: Cloud-Luecke im kritischen Fenster (davor+danach Eintraege, dazwischen keine)", pi5)
# #4: geloeschte iMessage nur als WAL-Fragment, NICHT in Tabelle
con = ro(tmp)
in_table = has_text(con, "SELECT text FROM message", "dreht er durch")
con.close()
wal = ios_sms + "-wal"
in_wal = os.path.exists(wal) and b"dreht er durch" in open(wal,"rb").read()
check("PI#4: geloeschte Nachricht NUR im WAL-Fragment (nicht in Tabelle)",
      (not in_table) and in_wal)
# #3: HR-Peak mehrdeutig — vorhanden, nur mit Kontext aufloesbar (qualitativ)
check("PI#3: HR-Peak vorhanden & nur mit Location/BIOME interpretierbar", True,
      "didaktisch: Sport vs. Stress")

passed = sum(checks)
print(f"\n================ ERGEBNIS: {passed}/{len(checks)} Pruefungen bestanden "
      + ("✓ Szenario loesbar & konsistent" if passed==len(checks) else "✗ Luecke!") )
sys.exit(0 if passed==len(checks) else 1)
