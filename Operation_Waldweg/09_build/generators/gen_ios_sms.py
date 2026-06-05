#!/usr/bin/env python3
# =====================================================================
# gen_ios_sms.py  —  erzeugt iOS sms.db (iMessage/SMS) fuer Anna
# ---------------------------------------------------------------------
# Reales iOS-17-Schema (message/handle/chat/*_join, Apple-Nanosekunden-
# Timestamps). Inhalte sind semantisch echte, ausformulierte Dialoge,
# konsistent zur Timeline im Case Master. Eine Nachricht ist als
# "geloescht" markiert -> taucht nur im WAL-Fragment auf (planted_inc #4).
#
# Validierbar mit iLEAPP (Modul "iMessage") sowie jedem SQLite-Viewer.
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
# OUT_BASE erlaubt das Bauen in einem Scratch-Verzeichnis (Mount blockt
# das Loeschen bestehender Dateien). Default: in-place im iOS-FS.
IOS_FS = os.environ.get('WALDWEG_IOS_FS', os.path.join(ROOT, '01_ios_full_fs'))
SMS_PATH = os.path.join(IOS_FS, 'private/var/mobile/Library/SMS/sms.db')

APPLE_EPOCH_OFFSET = 978307200  # Unix -> CFAbsoluteTime


def apple_ns(iso: str) -> int:
    """ISO 8601 -> Apple-Nanosekunden (iOS 11+)."""
    dt = datetime.fromisoformat(iso)
    cf = dt.timestamp() - APPLE_EPOCH_OFFSET
    return int(round(cf * 1_000_000_000))


# Telefonnummern (Referenz-Fallback)
ANNA = "+4915123456789"
DANIEL = "+4915223456788"
JONAS = "+4915333456787"
LENA = "+4915512345670"

# ---------------------------------------------------------------------
# SEMANTISCH ECHTE DIALOGE  (is_from_me: 1 = Anna sendet)
# Jeder Eintrag: (iso_zeit, handle_nummer, is_from_me, text)
# REFERENZ-FALLBACK — wird genutzt, wenn der Master keine strukturierten
# 'messages' fuer iMessage-Threads des iPhone-Besitzers traegt.
# ---------------------------------------------------------------------
FALLBACK_THREADS = {
    # --- Anna <-> Jonas (Affaere, iMessage) ----------------------------
    JONAS: [
        ("2025-11-20T21:30:00+01:00", 0, "Schön war's heute. Hab den ganzen Nachmittag an dich gedacht."),
        ("2025-11-20T21:41:00+01:00", 1, "Ich auch. Aber wir müssen vorsichtig sein, Jonas."),
        ("2025-11-20T21:43:00+01:00", 0, "Lösch das hier besser wieder, ja? Sicher ist sicher."),
        ("2025-12-14T13:05:00+01:00", 1, "Mittagspause? 20 Min am üblichen Platz?"),
        ("2025-12-14T13:07:00+01:00", 0, "Bin schon da ☕️"),
        ("2026-01-18T22:50:00+01:00", 1, "Ich halt das zuhause kaum noch aus. Mit Daniel wird's immer kälter."),
        ("2026-01-18T22:58:00+01:00", 0, "Du musst da raus. Ich bin für dich da, das weißt du."),
        ("2026-01-24T21:48:00+01:00", 1, "Ich hab mich entschieden. Ich zieh das durch, ich trenne mich von ihm."),
        ("2026-01-24T21:52:00+01:00", 0, "Endlich. Lass uns morgen früh in Ruhe reden, bevor der Tag losgeht."),
        ("2026-01-24T21:55:00+01:00", 1, "Ja. Treffen wir uns am Parkplatz am Waldweg? Da stört uns keiner."),
        ("2026-01-24T21:56:00+01:00", 0, "Halb neun? Ich bring Kaffee mit."),
        ("2026-01-25T07:20:00+01:00", 1, "Bin in 30 Min am Parkplatz. Wir reden in Ruhe."),
        ("2026-01-25T09:10:00+01:00", 0, "Wo bleibst du? Hier ist niemand."),
        ("2026-01-25T09:34:00+01:00", 0, "Anna? Ich mach mir Sorgen. Melde dich bitte."),
    ],
    # --- Anna <-> Lena (beste Freundin) --------------------------------
    LENA: [
        ("2025-12-22T18:20:00+01:00", 1, "Schaffst du's Samstag zum Glühwein? Brauch mal wieder dich :)"),
        ("2025-12-22T18:25:00+01:00", 0, "Klar! Ich bring Plätzchen mit. Alles ok bei dir?"),
        ("2026-01-10T19:12:00+01:00", 1, "Mit Daniel wird es gerade echt schwierig. Erzähl ich dir bald."),
        ("2026-01-10T19:20:00+01:00", 0, "Oh nein. Willst du reden? Ich hör zu, immer."),
        ("2026-01-10T19:24:00+01:00", 1, "Bald. Ist kompliziert. Danke, dass du da bist ❤️"),
        ("2026-01-21T20:02:00+01:00", 0, "Wie geht's dir? Hab an dich gedacht."),
        ("2026-01-21T20:30:00+01:00", 1, "Geht so. Ich glaub, ich muss eine große Entscheidung treffen."),
        ("2026-01-03T11:00:00+01:00", 0, "Frohes neues! Wann sehen wir uns mal wieder?"),
        ("2026-01-03T11:15:00+01:00", 1, "Bald! Vielleicht nächste Woche Kaffee?"),
        ("2026-01-16T14:22:00+01:00", 1, "Hast du das neue Café in der Altstadt schon getestet?"),
        ("2026-01-16T14:40:00+01:00", 0, "Noch nicht, aber steht auf der Liste 😄"),
    ],
    # --- Anna <-> Daniel (Ehe, iMessage-Anteil; Alltag + 25.01) --------
    DANIEL: [
        ("2026-01-12T17:40:00+01:00", 0, "Holst du Ben um 17:30 vom Training ab?"),
        ("2026-01-12T17:42:00+01:00", 1, "Mach ich. Brauchen wir noch was vom Supermarkt?"),
        ("2026-01-12T17:43:00+01:00", 0, "Milch und Brot. Danke."),
        ("2026-01-20T08:05:00+01:00", 1, "Bin heute später, Meeting bis 18 Uhr."),
        ("2026-01-20T08:30:00+01:00", 0, "Ok."),
        ("2026-01-05T19:10:00+01:00", 0, "Mülltonne rausstellen nicht vergessen."),
        ("2026-01-08T07:55:00+01:00", 1, "Tankst du auf dem Heimweg? Tank fast leer."),
        ("2026-01-08T12:20:00+01:00", 0, "Mach ich."),
        ("2026-01-14T16:48:00+01:00", 1, "Bens Elternabend ist am Donnerstag 19 Uhr."),
        ("2026-01-25T07:25:00+01:00", 0, "Wo willst du so früh hin?"),
    ],
    # --- Noise: Studio/Yoga-Studio Terminbot ---------------------------
    "+4971160000000": [
        ("2026-01-19T08:00:00+01:00", 0, "Erinnerung: Kurs 'Power Yoga' heute 18:00. Antworten Sie mit STOP zum Abmelden."),
        ("2026-01-23T08:00:00+01:00", 0, "Erinnerung: Kurs 'Rücken Fit' heute 17:30."),
    ],
}

# Geloeschte Nachricht (planted_inconsistency #4): nur als WAL-Fragment,
# NICHT in der Haupttabelle. (Referenz-Fallback; Liste von (num,iso,fromme,text))
FALLBACK_DELETED = [(JONAS, "2026-01-24T22:11:00+01:00", 1,
                     "Wenn er das mitkriegt, dreht er durch.")]


def resolve_content():
    """Liefert (account_number, THREADS, DELETED_LIST).
    Aus dem Master, wenn iMessage-Threads strukturierte 'messages' tragen,
    sonst Referenz-Fallback."""
    cm = cmio.load_master()
    owner = cmio.device_owner("ios", cm)
    acct_num = cmio.phone_of(owner, cm, ANNA) if owner else ANNA
    mt = cmio.threads_for("imessage", owner, cm) if owner else None
    if not mt:
        return ANNA, FALLBACK_THREADS, FALLBACK_DELETED
    threads, deleted = {}, []
    for cp, seq in mt.items():
        live = []
        for iso, is_from_me, text, is_deleted in seq:
            if is_deleted:
                deleted.append((cp, iso, is_from_me, text))
            else:
                live.append((iso, is_from_me, text))
        if live:
            threads[cp] = live
    return acct_num, threads, deleted


def create_schema(con):
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE handle (
        ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL,
        country TEXT,
        service TEXT NOT NULL,
        uncanonicalized_id TEXT,
        person_centric_id TEXT,
        UNIQUE (id, service)
    );
    CREATE TABLE chat (
        ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
        guid TEXT NOT NULL UNIQUE,
        style INTEGER,
        state INTEGER,
        account_id TEXT,
        chat_identifier TEXT,
        service_name TEXT,
        room_name TEXT,
        display_name TEXT,
        is_archived INTEGER DEFAULT 0,
        last_read_message_timestamp INTEGER DEFAULT 0%s
    );""" % (",\n        chat_properties BLOB" if cmio.device_profile_flag("ios", "chat_properties", False) else "") + """
    CREATE TABLE message (
        ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
        guid TEXT NOT NULL UNIQUE,
        text TEXT,
        handle_id INTEGER DEFAULT 0,
        service TEXT,
        account TEXT,
        date INTEGER,
        date_read INTEGER,
        date_delivered INTEGER,
        is_from_me INTEGER DEFAULT 0,
        is_read INTEGER DEFAULT 0,
        is_sent INTEGER DEFAULT 0,
        is_delivered INTEGER DEFAULT 0,
        is_finished INTEGER DEFAULT 1,
        item_type INTEGER DEFAULT 0,
        associated_message_guid TEXT
    );
    CREATE TABLE chat_message_join (
        chat_id INTEGER,
        message_id INTEGER,
        message_date INTEGER,
        PRIMARY KEY (chat_id, message_id)
    );
    CREATE TABLE chat_handle_join (
        chat_id INTEGER,
        handle_id INTEGER,
        UNIQUE (chat_id, handle_id)
    );
    """)
    con.commit()


def populate(con, threads, account_number):
    cur = con.cursor()
    account = f"iMessage;-;{account_number}"
    handle_ids = {}
    chat_ids = {}

    for number in threads:
        cur.execute("INSERT INTO handle (id, country, service) VALUES (?,?,?)",
                    (number, "de", "iMessage"))
        handle_ids[number] = cur.lastrowid
        guid = f"iMessage;-;{number}"
        cur.execute("""INSERT INTO chat (guid, style, state, account_id,
                       chat_identifier, service_name, display_name)
                       VALUES (?,?,?,?,?,?,?)""",
                    (guid, 45, 3, account, number, "iMessage", ""))
        chat_ids[number] = cur.lastrowid
        # iOS 26: chat.chat_properties-PLIST (z.B. Chat-Hintergrund) — nur mit Profil-Flag
        if cmio.device_profile_flag("ios", "chat_properties", False):
            import plistlib
            blob = plistlib.dumps({
                "CHAT_PROPERTIES_VERSION": 1,
                "backgroundIdentifier": "com.apple.messages.background.gradient.sunset",
                "isPinned": False,
            }, fmt=plistlib.FMT_BINARY)
            cur.execute("UPDATE chat SET chat_properties=? WHERE ROWID=?", (blob, chat_ids[number]))
        cur.execute("INSERT INTO chat_handle_join (chat_id, handle_id) VALUES (?,?)",
                    (chat_ids[number], handle_ids[number]))

    msg_counter = 0
    for number, msgs in threads.items():
        for iso, is_from_me, text in msgs:
            msg_counter += 1
            d = apple_ns(iso)
            guid = f"WALDWEG-{msg_counter:04d}-{number[-4:]}"
            hid = 0 if is_from_me else handle_ids[number]
            read_ts = d + 30_000_000_000 if not is_from_me else d
            cur.execute("""INSERT INTO message
                (guid, text, handle_id, service, account, date, date_read,
                 date_delivered, is_from_me, is_read, is_sent, is_delivered)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (guid, text, hid, "iMessage", account, d, read_ts, d,
                 is_from_me, 1, 1 if is_from_me else 0, 1))
            mid = cur.lastrowid
            cur.execute("""INSERT INTO chat_message_join
                (chat_id, message_id, message_date) VALUES (?,?,?)""",
                (chat_ids[number], mid, d))
    con.commit()
    return chat_ids, handle_ids


def inject_deleted_into_wal(con, chat_ids, handle_ids, deleted_list, account_number):
    """Fuegt geloeschte Nachricht(en) ein und loescht sie wieder, ohne
    Checkpoint -> der Klartext bleibt als Fragment im WAL erhalten
    (forensisch rekonstruierbar, planted_inconsistency #4)."""
    cur = con.cursor()
    for i, (number, iso, is_from_me, text) in enumerate(deleted_list, 1):
        if number not in chat_ids:
            continue  # Gegenpart hat keinen Live-Thread -> ueberspringen
        d = apple_ns(iso)
        guid = f"WALDWEG-DELETED-{i:04d}"
        cur.execute("""INSERT INTO message
            (guid, text, handle_id, service, account, date, date_read,
             date_delivered, is_from_me, is_read, is_sent, is_delivered)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (guid, text, 0, "iMessage", f"iMessage;-;{account_number}", d, d, d,
             is_from_me, 1, 1, 1))
        mid = cur.lastrowid
        cur.execute("""INSERT INTO chat_message_join
            (chat_id, message_id, message_date) VALUES (?,?,?)""",
            (chat_ids[number], mid, d))
        con.commit()
        # wieder loeschen -> Eintrag verschwindet aus der Tabelle,
        # Klartext verbleibt aber in der WAL-Datei (kein checkpoint!)
        cur.execute("DELETE FROM message WHERE guid = ?", (guid,))
        cur.execute("DELETE FROM chat_message_join WHERE message_id = ?", (mid,))
        con.commit()


def main():
    os.makedirs(os.path.dirname(SMS_PATH), exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        p = SMS_PATH + suffix
        if os.path.exists(p):
            os.remove(p)

    account_number, threads, deleted_list = resolve_content()
    src_label = "Master" if threads is not FALLBACK_THREADS else "Referenz-Fallback"
    print(f"Inhaltsquelle: {src_label}  (Threads={len(threads)}, geloescht={len(deleted_list)})")

    import shutil
    con = sqlite3.connect(SMS_PATH)
    con.execute("PRAGMA journal_mode=WAL;")  # iOS nutzt WAL
    con.execute("PRAGMA wal_autocheckpoint=0;")  # kein Auto-Checkpoint
    create_schema(con)
    chat_ids, handle_ids = populate(con, threads, account_number)
    inject_deleted_into_wal(con, chat_ids, handle_ids, deleted_list, account_number)
    # Snapshot der drei Dateien NOCH MIT offener Verbindung ziehen:
    # so enthaelt die -wal das geloeschte Klartext-Fragment, bevor
    # SQLite beim Schliessen einen Checkpoint faehrt.
    snap = SMS_PATH + ".snapshot"
    for suffix in ("", "-wal", "-shm"):
        src = SMS_PATH + suffix
        if os.path.exists(src):
            shutil.copy(src, snap + suffix)
    con.close()
    # Snapshot zurueckspielen -> WAL bleibt mit Fragment erhalten
    for suffix in ("", "-wal", "-shm"):
        s = snap + suffix
        if os.path.exists(s):
            shutil.move(s, SMS_PATH + suffix)

    print(f"sms.db erzeugt: {os.path.relpath(SMS_PATH, ROOT)}")
    for suffix in ("", "-wal", "-shm"):
        p = SMS_PATH + suffix
        if os.path.exists(p):
            print(f"  {os.path.basename(p)}: {os.path.getsize(p)} bytes")

    # ---- Verifikation (auf Wegwerf-Kopie, damit die echte WAL bleibt) ----
    vdir = SMS_PATH + ".verify"
    for suffix in ("", "-wal", "-shm"):
        s = SMS_PATH + suffix
        if os.path.exists(s):
            shutil.copy(s, vdir + suffix)
    con = sqlite3.connect(vdir)
    cur = con.cursor()
    n_msg = cur.execute("SELECT COUNT(*) FROM message").fetchone()[0]
    n_chat = cur.execute("SELECT COUNT(*) FROM chat").fetchone()[0]
    n_handle = cur.execute("SELECT COUNT(*) FROM handle").fetchone()[0]
    print(f"\nVerifikation: {n_msg} Nachrichten, {n_chat} Chats, {n_handle} Handles")
    print("Kritische Nachrichten (Fokusfenster 25.01):")
    rows = cur.execute("""
        SELECT m.date, h.id, m.is_from_me, m.text
        FROM message m LEFT JOIN handle h ON m.handle_id=h.ROWID
        WHERE m.date >= ? ORDER BY m.date
    """, (apple_ns("2026-01-25T00:00:00+01:00"),)).fetchall()
    for d, hid, fromme, text in rows:
        who = "me→" if fromme else f"{hid}→me"
        ts = datetime.utcfromtimestamp(d/1e9 + APPLE_EPOCH_OFFSET)
        print(f"  {ts:%Y-%m-%d %H:%M} UTC  {who}: {text}")
    con.close()
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(vdir + suffix):
            os.remove(vdir + suffix)

    # geloeschtes Fragment im WAL nachweisen
    wal = SMS_PATH + "-wal"
    if os.path.exists(wal) and deleted_list:
        blob = open(wal, "rb").read()
        frag = deleted_list[0][3].encode("utf-8")
        found = frag in blob
        print(f"\nGeloeschtes Fragment im WAL auffindbar: {found}")


if __name__ == "__main__":
    main()
