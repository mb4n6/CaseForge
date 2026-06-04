#!/usr/bin/env python3
# =====================================================================
# gen_ios_whatsapp.py  —  Annas iPhone-WhatsApp (ChatStorage.sqlite)
# ---------------------------------------------------------------------
# WhatsApp auf iOS nutzt ein Core-Data-Schema (ZWAMESSAGE / ZWACHATSESSION
# / ZWAGROUPMEMBER), nicht das Android-msgstore-Schema. Hier als
# gym_crew-GRUPPE (reiner Noise). Timestamps = Apple-CFAbsoluteTime (s).
# Pfad: .../57T9237FN3~net~whatsapp~WhatsApp/ (App-Group-Container).
# Validierbar mit iLEAPP-Modul "WhatsApp Messages".
# =====================================================================
import os
import sys
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
sys.path.insert(0, HERE)
import case_master_io as cmio
IOS = os.environ.get('WALDWEG_IOS_FS', os.path.join(ROOT, '01_ios_full_fs'))
DB = os.path.join(IOS, 'private/var/mobile/Library/Mobile Documents/'
                  '57T9237FN3~net~whatsapp~WhatsApp/ChatStorage.sqlite')

APPLE = 978307200


def cf(iso):
    return datetime.fromisoformat(iso).timestamp() - APPLE


FALLBACK_GROUP = "GymCrew-49170555@g.us"
FALLBACK_SUBJECT = "Gym Crew"
# (iso, from_me, member_name, text)  — Referenz-Fallback (Noise-Gruppe)
FALLBACK_MSGS = [
    ("2026-01-08T18:30:00+01:00", 0, "Trainer Mike", "Morgen 18 Uhr Kurs faellt aus, dafuer Donnerstag extra Session 💪"),
    ("2026-01-08T18:34:00+01:00", 1, None, "Schade! Donnerstag passt aber."),
    ("2026-01-09T07:12:00+01:00", 0, "Sandra", "Wer kommt heute zum Lauftreff?"),
    ("2026-01-09T07:20:00+01:00", 1, None, "Ich bin dabei, bis gleich 🏃‍♀️"),
    ("2026-01-16T20:05:00+01:00", 0, "Tom", "Gruppenfoto vom letzten Mal 📸"),
    ("2026-01-20T12:40:00+01:00", 0, "Sandra", "Neuer Kursplan haengt aus, hab ihn fotografiert."),
    ("2026-01-23T21:15:00+01:00", 1, None, "Top, danke! Bis morgen früh."),
]


def resolve_group():
    """Erste WhatsApp-Gruppe des iPhone-Besitzers aus dem Master, sonst Fallback.
    -> (group_jid, subject, [(iso, from_me, member_name, text), ...], quelle)"""
    cm = cmio.load_master()
    owner = cmio.device_owner("ios", cm)
    groups = cmio.group_threads("whatsapp", owner, cm) if owner else None
    if not groups:
        return FALLBACK_GROUP, FALLBACK_SUBJECT, FALLBACK_MSGS, "Referenz-Fallback"
    subject, seq = groups[0]
    jid = f"{subject.replace(' ', '')}-group@g.us"
    return jid, subject, seq, "Master"


def main():
    GROUP, SUBJECT, MSGS, src = resolve_group()
    print(f"WhatsApp-iOS-Gruppe-Inhaltsquelle: {src} ({len(MSGS)} Nachrichten, '{SUBJECT}')")
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(DB + s):
            os.remove(DB + s)
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE ZWACHATSESSION (
        Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,
        ZCONTACTJID TEXT, ZPARTNERNAME TEXT, ZSESSIONTYPE INTEGER,
        ZLASTMESSAGEDATE REAL, ZMESSAGECOUNTER INTEGER
    );
    CREATE TABLE ZWAGROUPMEMBER (
        Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,
        ZCHATSESSION INTEGER, ZMEMBERJID TEXT, ZCONTACTNAME TEXT
    );
    CREATE TABLE ZWAMESSAGE (
        Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,
        ZCHATSESSION INTEGER, ZISFROMME INTEGER, ZMESSAGEDATE REAL,
        ZTEXT TEXT, ZFROMJID TEXT, ZGROUPMEMBER INTEGER,
        ZMESSAGETYPE INTEGER, ZSTANZAID TEXT
    );
    """)
    cur = con.cursor()
    last = cf(MSGS[-1][0])
    cur.execute("""INSERT INTO ZWACHATSESSION
        (Z_PK,Z_ENT,Z_OPT,ZCONTACTJID,ZPARTNERNAME,ZSESSIONTYPE,
         ZLASTMESSAGEDATE,ZMESSAGECOUNTER)
        VALUES (1,1,1,?,?,1,?,?)""", (GROUP, SUBJECT, last, len(MSGS)))

    members = {}
    for _, frm, name, _ in MSGS:
        if name and name not in members:
            pk = len(members) + 1
            jid = f"4917{4000000+pk}@s.whatsapp.net"
            cur.execute("""INSERT INTO ZWAGROUPMEMBER
                (Z_PK,Z_ENT,Z_OPT,ZCHATSESSION,ZMEMBERJID,ZCONTACTNAME)
                VALUES (?,2,1,1,?,?)""", (pk, jid, name))
            members[name] = (pk, jid)

    for i, (iso, frm, name, text) in enumerate(MSGS, 1):
        gm, fromjid = (None, None)
        if not frm and name:
            gm, fromjid = members[name][0], members[name][1]
        cur.execute("""INSERT INTO ZWAMESSAGE
            (Z_PK,Z_ENT,Z_OPT,ZCHATSESSION,ZISFROMME,ZMESSAGEDATE,ZTEXT,
             ZFROMJID,ZGROUPMEMBER,ZMESSAGETYPE,ZSTANZAID)
            VALUES (?,3,1,1,?,?,?,?,?,0,?)""",
            (i, frm, cf(iso), text, fromjid, gm, f"WAIOS{i:04d}"))
    con.commit(); con.close()
    print(f"ChatStorage.sqlite: {len(MSGS)} Nachrichten ('{SUBJECT}') "
          f"-> {os.path.relpath(DB, ROOT)}")

    con = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
    rows = con.execute("""
        SELECT m.ZMESSAGEDATE, m.ZISFROMME, gm.ZCONTACTNAME, m.ZTEXT
        FROM ZWAMESSAGE m
        LEFT JOIN ZWAGROUPMEMBER gm ON m.ZGROUPMEMBER = gm.Z_PK
        ORDER BY m.ZMESSAGEDATE""").fetchall()
    print(f"Verifikation: {len(rows)} Nachrichten lesbar (Join ZWAMESSAGE/ZWAGROUPMEMBER)")
    con.close()


if __name__ == "__main__":
    main()
