#!/usr/bin/env python3
# =====================================================================
# gen_android.py  —  Samsung Galaxy S23 (Android 14) Artefakte fuer Daniel
# ---------------------------------------------------------------------
# Erzeugt ALEAPP-kompatibel:
#   * mmssms.db    (com.android.providers.telephony)   — SMS
#   * calllog.db   (com.samsung.android.providers.contacts) — Anrufe
#   * contacts2.db (com.samsung.android.providers.contacts) — Kontakte
#   * msgstore.db  (com.whatsapp, modernes normalisiertes Schema)
#   * History      (com.android.chrome, WebKit-Epoch)
# Projiziert aus dem Case Master (Threads daniel_tobias / anna_daniel,
# Browser-Suchen, Anrufe). Timestamps:
#   - Telephony/Calllog/WhatsApp: Unix-Millisekunden
#   - Chrome: Mikrosekunden seit 1601-01-01 (WebKit)
# =====================================================================
import os
import sys
import sqlite3
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
sys.path.insert(0, HERE)
import case_master_io as cmio
import caseforge_rng as cfr
import noise_pools as npool
AFS = os.environ.get('WALDWEG_AND_FS', os.path.join(ROOT, '02_android_full_fs'))

P_MMSSMS = os.path.join(AFS, 'data/data/com.android.providers.telephony/databases/mmssms.db')
P_CALLLOG = os.path.join(AFS, 'data/data/com.samsung.android.providers.contacts/databases/calllog.db')
P_CONTACTS = os.path.join(AFS, 'data/data/com.samsung.android.providers.contacts/databases/contacts2.db')
P_WA = os.path.join(AFS, 'data/data/com.whatsapp/databases/msgstore.db')
P_CHROME = os.path.join(AFS, 'data/data/com.android.chrome/app_chrome/Default/History')

# Nummern
DANIEL = "+4915223456788"
ANNA = "+4915123456789"
TOBIAS = "+4915443456786"
POLICE = "110"

CONTACTS = [("Anna", ANNA), ("Tobias Klenk", TOBIAS), ("Werkstatt Klenk", "+4971150000")]


def ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def chrome_time(iso: str) -> int:
    # Mikrosekunden seit 1601-01-01 (Differenz zu Unix-Epoch = 11644473600 s)
    unix = datetime.fromisoformat(iso).timestamp()
    return int((unix + 11644473600) * 1_000_000)


def reset(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for s in ("", "-wal", "-shm", "-journal"):
        if os.path.exists(path + s):
            os.remove(path + s)


# ---------------------------------------------------------------------
# mmssms.db  (SMS auf Daniels Geraet — wenig, da er WhatsApp nutzt)
# ---------------------------------------------------------------------
FALLBACK_SMS_ROWS = [
    # (iso, address, type, body)   type 1=inbox(empfangen) 2=sent(gesendet)
    ("2026-01-22T11:15:00+01:00", TOBIAS, 1, "Komm heute in die Werkstatt, wir reden ueber die Rechnung."),
    ("2026-01-22T11:40:00+01:00", TOBIAS, 2, "Schaffe ich erst Donnerstag."),
]


def resolve_sms_rows():
    """Referenz -> Fallback; sonst seed-gezogene, scope-skalierte Pool-SMS."""
    if cfr.is_reference():
        return FALLBACK_SMS_ROWS, "Referenz-Fallback"
    lang = cmio.language_short()
    n = cmio.noise_count(2, key="sms_noise")
    texts = cfr.sample(npool.sms(lang), n, salt="sms_noise")
    r = cfr.stream("sms_addr")
    base = datetime.fromisoformat("2026-01-12T09:00:00+01:00")
    rows = []
    for i, t in enumerate(texts):
        addr = "+49151" + "".join(str(r.randint(0, 9)) for _ in range(8))
        rows.append(((base + timedelta(hours=i)).isoformat(), addr, 1 if i % 2 else 2, t))
    return rows, f"Pool/seed (scope, {len(rows)})"


def build_mmssms():
    SMS_ROWS, src = resolve_sms_rows()
    print(f"  SMS-Inhaltsquelle: {src} ({len(SMS_ROWS)})")
    reset(P_MMSSMS)
    con = sqlite3.connect(P_MMSSMS)
    con.executescript("""
    CREATE TABLE sms (
        _id INTEGER PRIMARY KEY,
        thread_id INTEGER,
        address TEXT,
        person INTEGER,
        date INTEGER,
        date_sent INTEGER,
        read INTEGER DEFAULT 1,
        type INTEGER,
        body TEXT,
        seen INTEGER DEFAULT 1
    );
    CREATE TABLE threads (
        _id INTEGER PRIMARY KEY,
        date INTEGER, message_count INTEGER, recipient_ids TEXT, snippet TEXT
    );
    """)
    cur = con.cursor()
    for i, (iso, addr, typ, body) in enumerate(SMS_ROWS, 1):
        d = ms(iso)
        cur.execute("""INSERT INTO sms (_id,thread_id,address,date,date_sent,
                       type,body) VALUES (?,?,?,?,?,?,?)""",
                    (i, 1, addr, d, d, typ, body))
    cur.execute("INSERT INTO threads VALUES (1,?,?,?,?)",
                (ms(SMS_ROWS[-1][0]), len(SMS_ROWS), "1", SMS_ROWS[-1][3]))
    con.commit(); con.close()
    print(f"mmssms.db: {len(SMS_ROWS)} SMS")


# ---------------------------------------------------------------------
# calllog.db
# ---------------------------------------------------------------------
CALLS = [
    # (iso, number, type, duration_s)  type 1=incoming 2=outgoing 3=missed
    ("2026-01-24T20:04:00+01:00", TOBIAS, 1, 92),    # Tobias ruft an (Ultimatum-Vorlauf)
    ("2026-01-25T08:25:00+01:00", TOBIAS, 2, 41),    # Daniel->Tobias direkt nach Tatfenster
    ("2026-01-25T12:18:00+01:00", POLICE, 2, 213),   # Daniel meldet Anna vermisst
    ("2026-01-23T18:30:00+01:00", ANNA,  2, 65),     # Noise: Alltagsanruf
]


def build_calllog():
    reset(P_CALLLOG)
    con = sqlite3.connect(P_CALLLOG)
    con.executescript("""
    CREATE TABLE calls (
        _id INTEGER PRIMARY KEY,
        number TEXT,
        date INTEGER,
        duration INTEGER,
        type INTEGER,
        name TEXT,
        countryiso TEXT DEFAULT 'DE',
        geocoded_location TEXT
    );
    """)
    cur = con.cursor()
    name_of = {n: nm for nm, n in CONTACTS}
    for i, (iso, num, typ, dur) in enumerate(CALLS, 1):
        cur.execute("""INSERT INTO calls (_id,number,date,duration,type,name)
                       VALUES (?,?,?,?,?,?)""",
                    (i, num, ms(iso), dur, typ, name_of.get(num)))
    con.commit(); con.close()
    print(f"calllog.db: {len(CALLS)} Anrufe")


# ---------------------------------------------------------------------
# contacts2.db (Minimal: raw_contacts + data fuer Telefonnummern)
# ---------------------------------------------------------------------
def build_contacts():
    reset(P_CONTACTS)
    con = sqlite3.connect(P_CONTACTS)
    con.executescript("""
    CREATE TABLE raw_contacts (
        _id INTEGER PRIMARY KEY, display_name TEXT, contact_id INTEGER
    );
    CREATE TABLE mimetypes (_id INTEGER PRIMARY KEY, mimetype TEXT);
    CREATE TABLE data (
        _id INTEGER PRIMARY KEY, raw_contact_id INTEGER, mimetype_id INTEGER,
        data1 TEXT, data2 TEXT
    );
    """)
    cur = con.cursor()
    cur.execute("INSERT INTO mimetypes VALUES (1,'vnd.android.cursor.item/phone_v2')")
    cur.execute("INSERT INTO mimetypes VALUES (2,'vnd.android.cursor.item/name')")
    for i, (name, num) in enumerate(CONTACTS, 1):
        cur.execute("INSERT INTO raw_contacts VALUES (?,?,?)", (i, name, i))
        cur.execute("INSERT INTO data (raw_contact_id,mimetype_id,data1) VALUES (?,?,?)",
                    (i, 2, name))
        cur.execute("INSERT INTO data (raw_contact_id,mimetype_id,data1) VALUES (?,?,?)",
                    (i, 1, num))
    con.commit(); con.close()
    print(f"contacts2.db: {len(CONTACTS)} Kontakte")


# ---------------------------------------------------------------------
# WhatsApp msgstore.db  (modernes normalisiertes Schema, WA 2.23+)
# ---------------------------------------------------------------------
# Threads: Daniel<->Tobias (Schulden), Daniel<->Anna (25.01 Frage)
FALLBACK_WA_THREADS = {
    f"{TOBIAS[1:]}@s.whatsapp.net": [
        ("2025-12-19T17:20:00+01:00", 0, "Die Bremsen sind fertig. Rechnung kommt per Post."),
        ("2025-12-19T17:25:00+01:00", 1, "Danke. Kann ich das in zwei Raten zahlen?"),
        ("2026-01-15T19:02:00+01:00", 0, "Daniel, die erste Rate ist ueberfaellig."),
        ("2026-01-15T19:40:00+01:00", 1, "Naechste Woche, versprochen."),
        ("2026-01-24T20:05:00+01:00", 0, "Ich brauch das Geld bis Montag, Daniel. Kein Spiel mehr."),
        ("2026-01-25T08:26:00+01:00", 1, "Hab kurz versucht dich zu erreichen. Melde mich spaeter."),
    ],
    f"{ANNA[1:]}@s.whatsapp.net": [
        ("2026-01-23T18:31:00+01:00", 1, "Holst du Ben heute? Ich schaff's nicht."),
        ("2026-01-23T18:35:00+01:00", 0, "Ok mach ich."),
        ("2026-01-25T07:25:00+01:00", 1, "Wo willst du so frueh hin?"),
    ],
}

def resolve_wa_groups():
    """WhatsApp-Gruppen des Android-Besitzers aus dem Master, sonst Fallback.
    -> ({raw_jid: {subject, msgs:[(iso,from_me,sender_label,text)]}}, quelle)"""
    cm = cmio.load_master()
    owner = cmio.device_owner("android", cm)
    groups = cmio.group_threads("whatsapp", owner, cm) if owner else None
    if not groups:
        return FALLBACK_WA_GROUPS, "Referenz-Fallback"
    out = {}
    for i, (subject, seq) in enumerate(groups, 1):
        raw = f"4917{6000000+i}-160{i:07d}@g.us"
        out[raw] = {"subject": subject, "msgs": seq}
    return out, "Master"


def resolve_wa_threads():
    """1:1-WhatsApp-Threads aus dem Master (Android-Besitzer), sonst Fallback.
    Master-Konvention -> JID-Schluessel {nummer_ohne_plus}@s.whatsapp.net."""
    cm = cmio.load_master()
    owner = cmio.device_owner("android", cm)
    mt = cmio.threads_for("whatsapp", owner, cm) if owner else None
    if not mt:
        return FALLBACK_WA_THREADS, "Referenz-Fallback"
    out = {}
    for cp, seq in mt.items():
        jid = f"{cp.lstrip('+')}@s.whatsapp.net"
        # geloeschte Nachrichten hier ignorieren (kein WAL-Mechanismus in msgstore)
        out[jid] = [(iso, fromme, text) for iso, fromme, text, _del in seq]
    return out, "Master"


# Gruppen-Threads (g.us) als Noise. Format: (iso, from_me, absender_label, text)
FALLBACK_WA_GROUPS = {
    "496170001111-1610000000@g.us": {
        "subject": "Nachbarschaft Ahornweg",
        "msgs": [
            ("2026-01-12T19:02:00+01:00", 0, "Anwohner M.", "Hat jemand Streusalz übrig? Gehweg ist spiegelglatt."),
            ("2026-01-12T19:10:00+01:00", 1, None, "Kann dir morgen einen Sack vorbeibringen."),
            ("2026-01-19T08:40:00+01:00", 0, "Hausverwaltung", "Mülltonnen werden Mittwoch geleert."),
            ("2026-01-22T20:15:00+01:00", 0, "Anwohner K.", "Faschingsumzug-Planung am Freitag im Bürgerhaus."),
        ],
    },
    "496170002222-1605000000@g.us": {
        "subject": "Außendienst Süd",
        "msgs": [
            ("2026-01-14T07:30:00+01:00", 0, "Teamleiter", "Wochenziele im CRM bitte bis Freitag eintragen."),
            ("2026-01-14T07:45:00+01:00", 1, None, "Mach ich. Bin heute Raum Stuttgart unterwegs."),
            ("2026-01-20T16:22:00+01:00", 0, "Kollege T.", "Muster für die Klinik kommen erst nächste Woche."),
            ("2026-01-24T18:10:00+01:00", 1, None, "Ok, danke für die Info."),
        ],
    },
}


def build_whatsapp():
    reset(P_WA)
    con = sqlite3.connect(P_WA)
    con.executescript("""
    CREATE TABLE jid (
        _id INTEGER PRIMARY KEY, user TEXT, server TEXT, raw_string TEXT
    );
    CREATE TABLE chat (
        _id INTEGER PRIMARY KEY, jid_row_id INTEGER, subject TEXT
    );
    CREATE TABLE message (
        _id INTEGER PRIMARY KEY,
        chat_row_id INTEGER,
        from_me INTEGER,
        key_id TEXT,
        sender_jid_row_id INTEGER,
        timestamp INTEGER,
        received_timestamp INTEGER,
        text_data TEXT,
        message_type INTEGER DEFAULT 0
    );
    """)
    cur = con.cursor()
    wa_threads, wa_src = resolve_wa_threads()
    print(f"  WhatsApp-Inhaltsquelle: {wa_src} ({len(wa_threads)} 1:1-Threads)")
    jid_id = 0; chat_id = 0; msg_id = 0
    for raw, msgs in wa_threads.items():
        jid_id += 1
        user = raw.split("@")[0]
        cur.execute("INSERT INTO jid VALUES (?,?,?,?)",
                    (jid_id, user, "s.whatsapp.net", raw))
        chat_id += 1
        cur.execute("INSERT INTO chat (_id,jid_row_id,subject) VALUES (?,?,?)",
                    (chat_id, jid_id, None))
        for iso, from_me, text in msgs:
            msg_id += 1
            t = ms(iso)
            cur.execute("""INSERT INTO message
                (_id,chat_row_id,from_me,key_id,sender_jid_row_id,timestamp,
                 received_timestamp,text_data,message_type)
                VALUES (?,?,?,?,?,?,?,?,0)""",
                (msg_id, chat_id, from_me, f"WA{msg_id:04d}",
                 0 if from_me else jid_id, t, t, text))

    # ---- Gruppen-Threads (g.us) ----
    wa_groups, grp_src = resolve_wa_groups()
    print(f"  WhatsApp-Gruppen-Inhaltsquelle: {grp_src} ({len(wa_groups)} Gruppen)")
    sender_jids = {}  # label -> jid_row_id
    n_groups = 0
    for raw, g in wa_groups.items():
        jid_id += 1
        cur.execute("INSERT INTO jid VALUES (?,?,?,?)",
                    (jid_id, raw.split("@")[0], "g.us", raw))
        chat_id += 1
        cur.execute("INSERT INTO chat (_id,jid_row_id,subject) VALUES (?,?,?)",
                    (chat_id, jid_id, g["subject"]))
        n_groups += 1
        for iso, from_me, sender_label, text in g["msgs"]:
            sjid = 0
            if not from_me:
                if sender_label not in sender_jids:
                    jid_id += 1
                    user = "4917" + str(3000000 + len(sender_jids))
                    cur.execute("INSERT INTO jid VALUES (?,?,?,?)",
                                (jid_id, user, "s.whatsapp.net", f"{user}@s.whatsapp.net"))
                    sender_jids[sender_label] = jid_id
                sjid = sender_jids[sender_label]
            msg_id += 1
            t = ms(iso)
            cur.execute("""INSERT INTO message
                (_id,chat_row_id,from_me,key_id,sender_jid_row_id,timestamp,
                 received_timestamp,text_data,message_type)
                VALUES (?,?,?,?,?,?,?,?,0)""",
                (msg_id, chat_id, from_me, f"WA{msg_id:04d}", sjid, t, t, text))
    con.commit(); con.close()
    print(f"msgstore.db: {msg_id} WhatsApp-Nachrichten in {chat_id} Chats "
          f"({n_groups} Gruppen)")


# ---------------------------------------------------------------------
# Chrome History  (WebKit-Epoch, Tabellen urls + visits)
# ---------------------------------------------------------------------
FALLBACK_CHROME_URLS = [
    # (iso, url, title)
    ("2026-01-23T23:50:00+01:00", "https://www.google.com/search?q=handy+orten+partner", "handy orten partner - Google Suche"),
    ("2026-01-24T22:15:00+01:00", "https://www.google.com/search?q=schulden+privatkredit+schnell", "schulden privatkredit schnell - Google Suche"),
    ("2026-01-20T12:10:00+01:00", "https://www.kicker.de/", "kicker - Fussball News"),  # Noise
    ("2026-01-22T08:05:00+01:00", "https://maps.google.com/", "Google Maps"),            # Noise
    ("2026-01-17T19:30:00+01:00", "https://www.wetter.com/", "Wetter Stuttgart"),        # Noise
    ("2026-01-18T10:12:00+01:00", "https://www.ebay-kleinanzeigen.de/", "Kleinanzeigen"),# Noise
    ("2026-01-21T07:50:00+01:00", "https://www.google.com/search?q=stau+a8+heute", "stau a8 heute"),  # Noise
    ("2026-01-13T21:05:00+01:00", "https://www.youtube.com/", "YouTube"),                # Noise
]


def build_chrome():
    mt = cmio.browser_history("android")
    if mt:
        CHROME_URLS = mt; src = "Master"
    elif cfr.is_reference():
        CHROME_URLS = FALLBACK_CHROME_URLS; src = "Referenz-Fallback"
    else:
        # seed-gezogener, scope-skalierter Noise aus dem lokalisierten Pool
        lang = cmio.language_short()
        n = cmio.noise_count(8, key="browser_noise")
        picked = cfr.sample(npool.web(lang), n, salt="chrome_noise")
        base_iso = "2026-01-20T12:00:00+01:00"
        CHROME_URLS = []
        for i, (url, title) in enumerate(picked):
            dt = datetime.fromisoformat(base_iso) + timedelta(hours=i, minutes=cfr.jitter_seconds(50, f"chrome{i}"))
            CHROME_URLS.append((dt.isoformat(), url, title))
        src = f"Pool/seed (scope, {len(CHROME_URLS)})"
    print(f"  Chrome-Inhaltsquelle: {src} ({len(CHROME_URLS)} URLs)")
    reset(P_CHROME)
    con = sqlite3.connect(P_CHROME)
    con.executescript("""
    CREATE TABLE urls (
        id INTEGER PRIMARY KEY, url TEXT, title TEXT,
        visit_count INTEGER DEFAULT 1, typed_count INTEGER DEFAULT 0,
        last_visit_time INTEGER, hidden INTEGER DEFAULT 0
    );
    CREATE TABLE visits (
        id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER,
        from_visit INTEGER, transition INTEGER DEFAULT 805306368
    );
    """)
    cur = con.cursor()
    for i, (iso, url, title) in enumerate(CHROME_URLS, 1):
        ct = chrome_time(iso)
        cur.execute("""INSERT INTO urls (id,url,title,visit_count,typed_count,
                       last_visit_time) VALUES (?,?,?,?,?,?)""",
                    (i, url, title, 1, 1, ct))
        cur.execute("INSERT INTO visits (id,url,visit_time) VALUES (?,?,?)",
                    (i, i, ct))
    con.commit(); con.close()
    print(f"Chrome History: {len(CHROME_URLS)} URLs")


def main():
    build_mmssms()
    build_calllog()
    build_contacts()
    build_whatsapp()
    build_chrome()
    print("\nAndroid-Artefakte erzeugt unter", os.path.relpath(AFS, ROOT))


if __name__ == "__main__":
    main()
