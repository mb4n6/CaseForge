#!/usr/bin/env python3
# =====================================================================
# validate_ios.py  —  iLEAPP-aequivalentes Acceptance-Gate
# ---------------------------------------------------------------------
# iLEAPP laesst sich in dieser Sandbox nicht installieren (GitHub-Git
# blockiert, kein PyPI-Paket). Dieses Gate fuehrt stattdessen die
# CHARAKTERISTISCHEN ABFRAGEN aus, die iLEAPPs Artefakt-Module gegen
# sms.db / healthdb_secure.sqlite / Photos.sqlite stellen. Laufen sie
# sauber durch und liefern plausible Zeilen, ist das Schema fuer iLEAPP
# konsumierbar. Den finalen Lauf mit dem echten iLEAPP fuehrt der/die
# Dozent/in lokal aus (Anleitung: 09_build/README_validation.md).
# =====================================================================
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_common import Gate, ok_exit

IOS_FS = os.environ.get('WALDWEG_IOS_FS', '/tmp/ios_build')
SMS = os.path.join(IOS_FS, 'private/var/mobile/Library/SMS/sms.db')
HEALTH = os.path.join(IOS_FS, 'private/var/mobile/Library/Health/healthdb_secure.sqlite')
PHOTOS = os.path.join(IOS_FS, 'private/var/mobile/Media/PhotoData/Photos.sqlite')

APPLE = 978307200
G = Gate()
ok = G.ok


def appletime_ns(ns):
    return datetime(2001, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=ns / 1e9)


# --- iLEAPP iMessage-Query (analog scripts/artifacts/sms.py) ---------
def gate_sms():
    print("iMessage / SMS:")
    con = sqlite3.connect(f"file:{SMS}?mode=ro", uri=True)
    q = """
    SELECT message.date, message.text, message.is_from_me,
           handle.id AS contact
    FROM message
    LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
    LEFT JOIN chat ON chat.ROWID = chat_message_join.chat_id
    LEFT JOIN handle ON message.handle_id = handle.ROWID
    ORDER BY message.date
    """
    rows = con.execute(q).fetchall()
    ok("iMessage-Join laeuft", len(rows) > 0, f"{len(rows)} Nachrichten")
    # Apple-ns korrekt interpretierbar?
    first = appletime_ns(rows[0][0])
    ok("Timestamp im plausiblen Bereich", 2025 <= first.year <= 2026, f"erste {first:%Y-%m-%d %H:%M}")
    # geloeschte Nachricht NICHT in Haupttabelle (Referenz-spez. Text)
    deleted_visible = con.execute(
        "SELECT COUNT(*) FROM message WHERE text LIKE '%dreht er durch%'").fetchone()[0]
    ok("Geloeschte Nachricht nicht in Tabelle", deleted_visible == 0, ref=True)
    con.close()
    # ...aber als Fragment in der WAL (Referenz-spez. Text)
    wal = SMS + "-wal"
    frag = os.path.exists(wal) and b"dreht er durch" in open(wal, "rb").read()
    ok("Geloeschtes Fragment in WAL rekonstruierbar", frag, ref=True)
    # Format: WAL-Mechanismus generell vorhanden (geloeschte Zeile rekonstruierbar)
    ok("WAL-Datei vorhanden (Recovery moeglich)", os.path.exists(wal))


# --- iLEAPP Health-Query (analog healthdb-Module) --------------------
def gate_health():
    print("Apple Health:")
    con = sqlite3.connect(f"file:{HEALTH}?mode=ro", uri=True)
    q = """
    SELECT samples.start_date, quantity_samples.original_quantity
    FROM samples
    LEFT JOIN quantity_samples ON samples.data_id = quantity_samples.data_id
    LEFT JOIN objects ON samples.data_id = objects.data_id
    LEFT JOIN data_provenances ON objects.provenance = data_provenances.ROWID
    WHERE samples.data_type = 5
    ORDER BY samples.start_date
    """
    rows = con.execute(q).fetchall()
    ok("Heartrate-Join laeuft", len(rows) > 0, f"{len(rows)} HR-Werte")
    peak = max(r[1] for r in rows)
    ok("HR-Peak == 138", peak == 138, f"peak={peak:.0f}", ref=True)
    # Schlaf-Kategorie
    sleep = con.execute("""
        SELECT s.start_date, s.end_date, c.value
        FROM samples s JOIN category_samples c ON s.data_id=c.data_id
        WHERE s.data_type=63""").fetchall()
    ok("Schlaf-Kategorie vorhanden", len(sleep) == 1, ref=True)
    con.close()


# --- iLEAPP Photos-Query (analog photos-metadata-Module) -------------
def gate_photos():
    print("Photos.sqlite:")
    con = sqlite3.connect(f"file:{PHOTOS}?mode=ro", uri=True)
    q = """
    SELECT ZASSET.ZDATECREATED, ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME,
           ZASSET.ZLATITUDE, ZASSET.ZLONGITUDE, ZASSET.ZDIRECTORY
    FROM ZASSET
    LEFT JOIN ZADDITIONALASSETATTRIBUTES
           ON ZASSET.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSET
    ORDER BY ZASSET.ZDATECREATED
    """
    rows = con.execute(q).fetchall()
    ok("ZASSET-Join laeuft", len(rows) > 0, f"{len(rows)} Assets")
    geo = sum(1 for r in rows if r[2] is not None)
    ok("Geo-Assets vorhanden", geo >= 1, f"{geo} mit GPS")
    con.close()


def gate_whatsapp():
    wai = os.path.join(IOS_FS, 'private/var/mobile/Library/Mobile Documents/'
                       '57T9237FN3~net~whatsapp~WhatsApp/ChatStorage.sqlite')
    if not os.path.exists(wai):
        return
    print("WhatsApp iOS (ChatStorage.sqlite):")
    con = sqlite3.connect(f"file:{wai}?mode=ro&immutable=1", uri=True)
    rows = con.execute("""SELECT m.ZMESSAGEDATE,m.ZTEXT,gm.ZCONTACTNAME
        FROM ZWAMESSAGE m LEFT JOIN ZWAGROUPMEMBER gm ON m.ZGROUPMEMBER=gm.Z_PK
        ORDER BY m.ZMESSAGEDATE""").fetchall()
    ok("ZWAMESSAGE/ZWAGROUPMEMBER-Join laeuft", len(rows) >= 1, f"{len(rows)} Nachrichten")
    sess = con.execute("SELECT ZPARTNERNAME,ZCONTACTJID FROM ZWACHATSESSION").fetchall()
    ok("Gruppen-Session (g.us) vorhanden", any("g.us" in (s[1] or "") for s in sess), ref=True)
    con.close()


def gate_extra():
    import hashlib, plistlib
    import caseforge_rng as cfr
    def gid(b):
        return cfr.app_guid(b)
    # Safari History.db
    sh = os.path.join(IOS_FS, "private/var/mobile/Containers/Data/Application",
                      gid("com.apple.mobilesafari"), "Library/Safari/History.db")
    if os.path.exists(sh):
        print("Safari / Voicemail / CallHistory:")
        con = sqlite3.connect(f"file:{sh}?mode=ro&immutable=1", uri=True)
        rows = con.execute("SELECT hi.url FROM history_visits hv JOIN history_items hi ON hv.history_item=hi.id").fetchall()
        con.close()
        ok("Safari History.db lesbar", len(rows) >= 1, f"{len(rows)} Visits")
        ok("Safari belastende Suche (anwalt+trennung)",
           any("anwalt+trennung" in r[0] for r in rows), ref=True)
    # Voicemail
    vm = os.path.join(IOS_FS, "private/var/mobile/Library/Voicemail/voicemail.db")
    if os.path.exists(vm):
        con = sqlite3.connect(f"file:{vm}?mode=ro&immutable=1", uri=True)
        n = con.execute("SELECT COUNT(*) FROM voicemail").fetchone()[0]; con.close()
        ok("voicemail.db", n >= 1)
    # CallHistory
    ch = os.path.join(IOS_FS, "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata")
    if os.path.exists(ch):
        con = sqlite3.connect(f"file:{ch}?mode=ro&immutable=1", uri=True)
        n = con.execute("SELECT COUNT(*) FROM ZCALLRECORD").fetchone()[0]; con.close()
        ok("CallHistory ZCALLRECORD", n >= 3, f"{n} Anrufe")
    # Health Workout-Route (nur wenn Health-DB im Fall)
    if os.path.exists(HEALTH):
        con = sqlite3.connect(f"file:{HEALTH}?mode=ro&immutable=1", uri=True)
        try:
            wr = con.execute("SELECT COUNT(*) FROM workout_routes").fetchone()[0]
            ok("Health Workout-Route (Home->Waldweg)", wr >= 3, f"{wr} Punkte", ref=True)
        except Exception:
            ok("Health Workout-Route", False, ref=True)
        con.close()
    # BIOME zusaetzliche Streams
    breg = os.path.join(IOS_FS, "private/var/db/biome/streams/restricted")
    extra = ["App.Install", "_DKEvent.App.Activity.Battery", "_DKEvent.Media.NowPlaying", "Device.BluetoothConnection"]
    have = sum(1 for s in extra if os.path.isdir(os.path.join(breg, s, "local")))
    ok("BIOME Zusatz-Streams", have >= 3, f"{have}/{len(extra)}")
    # knowledgeC.db (nur Profil ios_16) — existenz-gesteuert (Referenz hat keine)
    kc = os.path.join(IOS_FS, "private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db")
    if os.path.exists(kc):
        print("knowledgeC.db (iOS <= 16):")
        con = sqlite3.connect(f"file:{kc}?mode=ro&immutable=1", uri=True)
        rows = con.execute("""SELECT o.ZSTREAMNAME, o.ZVALUESTRING FROM ZOBJECT o
                              LEFT JOIN ZSOURCE s ON o.ZSOURCE=s.Z_PK
                              WHERE o.ZSTREAMNAME LIKE '/app/%'""").fetchall()
        con.close()
        ok("knowledgeC ZOBJECT/ZSOURCE-Join", len(rows) >= 1, f"{len(rows)} /app/*-Events")
    # iOS 26: chat.chat_properties (existenz-gesteuert)
    con = sqlite3.connect(f"file:{SMS}?mode=ro&immutable=1", uri=True)
    cols = [r[1] for r in con.execute("PRAGMA table_info(chat)").fetchall()]
    if "chat_properties" in cols:
        n = con.execute("SELECT COUNT(*) FROM chat WHERE chat_properties IS NOT NULL").fetchone()[0]
        ok("iMessage chat.chat_properties (iOS 26)", n >= 1, f"{n} Chats mit PLIST")
    con.close()
    # iOS 26: shutdown.log (existenz-gesteuert)
    sl = os.path.join(IOS_FS, "private/var/mobile/private/var/db/com.apple.shutdown.log")
    sl2 = os.path.join(IOS_FS, "private/var/db/com.apple.shutdown.log")
    slp = sl if os.path.exists(sl) else sl2
    if os.path.exists(slp):
        txt = open(slp, encoding="utf-8").read()
        ok("shutdown.log (iOS 26)", "remaining client pid" in txt)


def main():
    # SKIP (rc=2), wenn gar keine iOS-Artefakte im Fall sind
    if not any(os.path.exists(p) for p in (SMS, HEALTH, PHOTOS)):
        print("[SKIP] keine iOS-DBs im Fall"); sys.exit(2)
    if os.path.exists(SMS):
        gate_sms()
    if os.path.exists(HEALTH):
        gate_health()
    if os.path.exists(PHOTOS):
        gate_photos()
    gate_whatsapp()
    gate_extra()
    ok_exit(G)


if __name__ == "__main__":
    main()
