#!/usr/bin/env python3
# =====================================================================
# gen_ios_knowledgec.py  —  knowledgeC.db (iOS <= 16) — Kontrast zu BIOME
# ---------------------------------------------------------------------
# Versionsmerkmal: Bis iOS 16 fuehrt iOS die Aktivitaets-/Nutzungsdaten in
# knowledgeC.db (CoreDuet). Ab iOS 17 entfaellt diese DB zugunsten von
# BIOME/SEGB. Dieser Generator erzeugt knowledgeC.db NUR, wenn das aktive
# iOS-Geraet das Profil-Flag 'knowledgec' traegt (Profil ios_16).
#
# Schema-getreu: ZOBJECT / ZSTRUCTUREDMETADATA / ZSOURCE (Kernrelationen,
# wie sie iLEAPP/APOLLO erwarten). Zeitstempel = Apple-CFAbsoluteTime (s).
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
DB = os.path.join(IOS, "private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db")
APPLE = 978307200


def cf(iso):
    return datetime.fromisoformat(iso).timestamp() - APPLE


# (stream, value, start_iso, end_iso)  — /app/inFocus + /app/usage + Safari
EVENTS = [
    ("/app/inFocus", "com.apple.mobilesafari", "2026-01-24T18:40:00+01:00", "2026-01-24T18:52:00+01:00"),
    ("/app/inFocus", "net.whatsapp.WhatsApp", "2026-01-24T20:03:00+01:00", "2026-01-24T20:09:00+01:00"),
    ("/app/inFocus", "com.apple.mobilephone", "2026-01-25T07:33:00+01:00", "2026-01-25T07:34:00+01:00"),
    ("/app/usage", "com.apple.mobilesafari", "2026-01-24T18:40:00+01:00", "2026-01-24T18:52:00+01:00"),
    ("/safari/history", "google.com/search?q=anwalt+trennung", "2026-01-25T07:05:00+01:00", "2026-01-25T07:05:30+01:00"),
]


def build():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(DB + s):
            os.remove(DB + s)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE ZSOURCE (
        Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,
        ZDEVICEID TEXT, ZBUNDLEID TEXT
    );
    CREATE TABLE ZSTRUCTUREDMETADATA (
        Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,
        Z_DKAPPLICATIONACTIVITYMETADATAKEY__LAUNCHREASON TEXT,
        Z_DKBLUETOOTHMETADATAKEY__NAME TEXT
    );
    CREATE TABLE ZOBJECT (
        Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,
        ZSTREAMNAME TEXT, ZVALUESTRING TEXT,
        ZSTARTDATE REAL, ZENDDATE REAL, ZCREATIONDATE REAL,
        ZSECONDSFROMGMT INTEGER, ZSOURCE INTEGER, ZSTRUCTUREDMETADATA INTEGER,
        ZUUID TEXT
    );
    """)
    cur = con.cursor()
    cur.execute("INSERT INTO ZSOURCE (Z_PK,Z_ENT,Z_OPT,ZDEVICEID,ZBUNDLEID) VALUES (1,1,1,?,?)",
                ("local", "com.apple.coreduetd"))
    cur.execute("INSERT INTO ZSTRUCTUREDMETADATA (Z_PK,Z_ENT,Z_OPT) VALUES (1,2,1)")
    for i, (stream, val, s_iso, e_iso) in enumerate(EVENTS, 1):
        cur.execute("""INSERT INTO ZOBJECT
            (Z_PK,Z_ENT,Z_OPT,ZSTREAMNAME,ZVALUESTRING,ZSTARTDATE,ZENDDATE,
             ZCREATIONDATE,ZSECONDSFROMGMT,ZSOURCE,ZSTRUCTUREDMETADATA,ZUUID)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (i, 3, 1, stream, val, cf(s_iso), cf(e_iso), cf(s_iso), 3600, 1, 1,
             f"KC-{i:04d}-0000-0000"))
    con.commit()
    # Gegenprobe-Query (analog iLEAPP/APOLLO)
    n = cur.execute("""SELECT COUNT(*) FROM ZOBJECT o
                       LEFT JOIN ZSOURCE s ON o.ZSOURCE=s.Z_PK
                       WHERE o.ZSTREAMNAME LIKE '/app/%'""").fetchone()[0]
    con.close()
    return n


def main():
    flag = cmio.device_profile_flag("ios", "knowledgec", False)
    if not flag:
        print("knowledgeC: [SKIP] iOS-Profil ohne Flag 'knowledgec' (>= iOS 17 nutzt BIOME).")
        return
    n = build()
    print(f"knowledgeC.db erzeugt (iOS <= 16): {os.path.relpath(DB, ROOT)}  "
          f"({n} /app/*-Events, Schema ZOBJECT/ZSOURCE/ZSTRUCTUREDMETADATA)")


if __name__ == "__main__":
    main()
