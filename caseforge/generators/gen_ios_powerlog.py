#!/usr/bin/env python3
# =====================================================================
# gen_ios_powerlog.py  —  iOS Powerlog (CurrentPowerlog.PLSQL)
# ---------------------------------------------------------------------
# Powerlog ist eine SQLite-DB mit PL*-Tabellen (App-Laufzeiten, Akku,
# Display, Standortnutzung). iLEAPP besitzt Powerlog-Module. Erzeugt eine
# schema-plausible PLSQL mit App-Runtime- und Battery-Tabellen.
# Pfad: private/var/mobile/Library/BatteryLife/CurrentPowerlog.PLSQL
# Profil-Flag 'powerlog'. (Unified Logs *.tracev3 sind proprietaer/binaer
# und werden bewusst NICHT faithful nachgebildet.)
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

IOS = os.environ.get("WALDWEG_IOS_FS", os.path.join(ROOT, "01_ios_full_fs"))
DB = os.path.join(IOS, "private/var/mobile/Library/BatteryLife/CurrentPowerlog.PLSQL")
APPLE = 978307200


def mac(iso):
    return datetime.fromisoformat(iso).timestamp() - APPLE


APPRUN = [
    ("com.apple.mobilesafari", "2026-01-24T18:40:00+01:00", 720),
    ("net.whatsapp.WhatsApp", "2026-01-24T20:03:00+01:00", 360),
    ("com.apple.mobilephone", "2026-01-25T07:33:00+01:00", 65),
    ("com.spotify.client", "2026-01-24T18:40:00+01:00", 1800),
]
BATTERY = [
    ("2026-01-24T22:30:00+01:00", 74, 0),
    ("2026-01-25T06:50:00+01:00", 61, 0),
    ("2026-01-25T07:50:00+01:00", 55, 0),
]


def main():
    if not cmio.device_profile_flag("ios", "powerlog", False):
        print("Powerlog: [SKIP] iOS-Profil ohne Flag 'powerlog'.")
        return
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(DB + s):
            os.remove(DB + s)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE PLAppTimeService_Aggregate_AppRunTime (
        ID INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
        BundleID TEXT, appBundleID TEXT, timeInterval REAL
    );
    CREATE TABLE PLBatteryAgent_EventBackward_Battery (
        ID INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
        Level INTEGER, IsCharging INTEGER
    );
    CREATE TABLE MetadataKeyValue (key TEXT, value TEXT);
    """)
    cur = con.cursor()
    cur.execute("INSERT INTO MetadataKeyValue VALUES ('PLSQLVersion','1')")
    for bid, iso, dur in APPRUN:
        cur.execute("""INSERT INTO PLAppTimeService_Aggregate_AppRunTime
            (timestamp,BundleID,appBundleID,timeInterval) VALUES (?,?,?,?)""",
            (mac(iso), bid, bid, dur))
    for iso, lvl, chg in BATTERY:
        cur.execute("""INSERT INTO PLBatteryAgent_EventBackward_Battery
            (timestamp,Level,IsCharging) VALUES (?,?,?)""", (mac(iso), lvl, chg))
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM PLAppTimeService_Aggregate_AppRunTime").fetchone()[0]
    con.close()
    print(f"Powerlog erzeugt: {os.path.relpath(DB, ROOT)}  ({n} App-Runtime-Zeilen + Battery)")


if __name__ == "__main__":
    main()
