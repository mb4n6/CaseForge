#!/usr/bin/env python3
# =====================================================================
# gen_android_extra.py  —  vertiefte Android-Artefakte (Samsung Daniel)
# ---------------------------------------------------------------------
#   * usagestats   : /data/system/usagestats/0/daily|... (App-Nutzung, XML)
#   * Samsung Health: com.sec.android.app.shealth (Schritte/Workout, SQLite)
#   * Google Maps  : com.google.android.apps.maps gmm_myplaces/_storage
#   * Accounts/Sync: /data/system/sync/accounts.xml, accounts_ce.db
#   * WhatsApp     : wa.db (Kontakte) + Media-Thumbnails
#   * batterystats/netstats (System)
# SQLite in /tmp gebaut, dann kopiert.
# =====================================================================
import os
import csv
import shutil
import sqlite3
import hashlib
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
AND = os.environ.get("WALDWEG_AND_FS", os.path.join(ROOT, "02_android_full_fs"))
TMP = "/tmp/and_extra_build"
manifest = []


def ux_ms(iso):
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def ux(iso):
    return int(datetime.fromisoformat(iso).timestamp())


def ensure(d):
    os.makedirs(d, exist_ok=True)


def w_text(rel, s):
    p = os.path.join(AND, rel); ensure(os.path.dirname(p))
    open(p, "w", encoding="utf-8").write(s)
    return p


def w_blob(rel, b):
    p = os.path.join(AND, rel); ensure(os.path.dirname(p))
    open(p, "wb").write(b)
    return p


def w_sqlite(rel, script, rows=None):
    dst = os.path.join(AND, rel); ensure(os.path.dirname(dst))
    tmp = os.path.join(TMP, hashlib.md5(rel.encode()).hexdigest() + ".db"); ensure(TMP)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(tmp + s):
            os.remove(tmp + s)
    con = sqlite3.connect(tmp); con.executescript(script)
    if rows:
        for sql, params in rows:
            con.execute(sql, params)
    con.commit(); con.close()
    shutil.copy(tmp, dst)
    return dst


# ---------------- usagestats ----------------
def build_usagestats():
    # Android usagestats: pro Zeitbucket eine XML mit <packages><package .../></packages>
    usage = [  # (pkg, lastTimeActive_ms, totalTimeActive_ms)
        ("com.whatsapp", "2026-01-24T20:06:00+01:00", 5400),
        ("com.android.chrome", "2026-01-24T22:15:00+01:00", 9300),
        ("org.thoughtcrime.securesms", "2026-01-24T22:20:00+01:00", 2600),
        ("com.starfinanz.smob.android.sfinanzstatus", "2026-01-24T22:35:00+01:00", 800),
        ("com.google.android.apps.maps", "2026-01-25T08:02:00+01:00", 1500),
        ("com.android.dialer", "2026-01-25T08:25:00+01:00", 60),
    ]
    rows = "\n".join(
        f'  <package token="{i}" package="{p}" lastTimeActive="{ux_ms(t)}" '
        f'timeActive="{a}" lastEvent="1" />'
        for i, (p, t, a) in enumerate(usage, 1))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<usagestats version="5" endTime="{ux_ms("2026-01-26T00:00:00+01:00")}">\n'
           f'<packages>\n{rows}\n</packages>\n</usagestats>\n')
    for bucket in ("daily", "weekly", "monthly"):
        p = w_text(f"data/system/usagestats/0/{bucket}/{ux_ms('2026-01-25T00:00:00+01:00')}", xml)
    manifest.append(("Samsung", "data/system/usagestats/0/daily/...", "context",
                     "usagestats: App-Nutzung 24./25.01 (WhatsApp/Signal/Sparkasse abends, Maps 08:02, Dialer 08:25)"))


# ---------------- Samsung Health ----------------
def build_shealth():
    pkg = "com.sec.android.app.shealth"
    rel = f"data/data/{pkg}/databases/SecureHealthData.db"
    w_sqlite(rel,
        "CREATE TABLE step_daily_trend (day_time INTEGER, count INTEGER, distance REAL, calorie REAL);"
        "CREATE TABLE exercise (start_time INTEGER, end_time INTEGER, exercise_type INTEGER, distance REAL);",
        [("INSERT INTO step_daily_trend VALUES (?,?,?,?)", (ux_ms("2026-01-24T00:00:00+01:00"), 9302, 6800.0, 310.0)),
         ("INSERT INTO step_daily_trend VALUES (?,?,?,?)", (ux_ms("2026-01-25T00:00:00+01:00"), 2110, 1500.0, 70.0)),
         ("INSERT INTO exercise VALUES (?,?,?,?)",
          (ux_ms("2026-01-25T08:00:00+01:00"), ux_ms("2026-01-25T08:30:00+01:00"), 1001, 1450.0))])
    for sub in ("shared_prefs", "cache", "files"):
        ensure(os.path.join(AND, "data/data", pkg, sub))
    w_text(f"data/data/{pkg}/shared_prefs/{pkg}_preferences.xml",
           '<?xml version="1.0" encoding="utf-8" standalone="yes" ?>\n<map>\n'
           '    <string name="profile_user">Daniel</string>\n</map>\n')
    manifest.append(("Samsung", rel, "context",
                     "Samsung Health: 25.01 nur 2110 Schritte; Exercise 08:00-08:30 (Bewegung am Tatmorgen)"))


# ---------------- Google Maps ----------------
def build_maps():
    pkg = "com.google.android.apps.maps"
    rel = f"data/data/{pkg}/databases/gmm_storage.db"
    w_sqlite(rel,
        "CREATE TABLE gmm_storage_table (_key_pri TEXT, _key_sec TEXT, _data BLOB, _timestamp INTEGER);",
        [("INSERT INTO gmm_storage_table VALUES (?,?,?,?)",
          ("search", "waldweg parkplatz", b"cached", ux_ms("2026-01-25T07:30:00+01:00")))])
    relq = f"data/data/{pkg}/databases/gmm_myplaces.db"
    w_sqlite(relq,
        "CREATE TABLE sync_item (_id INTEGER PRIMARY KEY, data_item_id TEXT, title TEXT, latitude_e6 INTEGER, longitude_e6 INTEGER, timestamp INTEGER);",
        [("INSERT INTO sync_item (data_item_id,title,latitude_e6,longitude_e6,timestamp) VALUES (?,?,?,?,?)",
          ("q1", "Waldweg Parkplatz", 48730500, 9248000, ux_ms("2026-01-25T07:31:00+01:00"))),
         ("INSERT INTO sync_item (data_item_id,title,latitude_e6,longitude_e6,timestamp) VALUES (?,?,?,?,?)",
          ("q2", "Kfz-Werkstatt Klenk", 48751000, 9210000, ux_ms("2026-01-22T16:00:00+01:00")))])
    manifest.append(("Samsung", relq, "critical",
                     "Google Maps: Suche/Ziel 'Waldweg Parkplatz' 25.01 07:31 (Kernindiz – Daniel kannte den Ort)"))


# ---------------- Accounts / Sync ----------------
def build_accounts():
    w_text("data/system/sync/accounts.xml",
           '<?xml version="1.0" encoding="utf-8" standalone="yes" ?>\n<accounts version="2" >\n'
           '  <account name="daniel.reuter@gmail.com" type="com.google" />\n'
           '  <account name="d.reuter@example.de" type="com.microsoft.office.outlook" />\n'
           '  <account name="+4915223456788" type="com.whatsapp" />\n</accounts>\n')
    w_sqlite("data/system_ce/0/accounts_ce.db",
        "CREATE TABLE accounts (_id INTEGER PRIMARY KEY, name TEXT, type TEXT);",
        [("INSERT INTO accounts (name,type) VALUES (?,?)", ("daniel.reuter@gmail.com", "com.google")),
         ("INSERT INTO accounts (name,type) VALUES (?,?)", ("+4915223456788", "com.whatsapp"))])
    manifest.append(("Samsung", "data/system/sync/accounts.xml", "context",
                     "Accounts: Google/Outlook/WhatsApp (Geraetebindung an Daniel)"))


# ---------------- WhatsApp wa.db + Media ----------------
def build_whatsapp_extra():
    pkg = "com.whatsapp"
    rel = f"data/data/{pkg}/databases/wa.db"
    w_sqlite(rel,
        "CREATE TABLE wa_contacts (jid TEXT PRIMARY KEY, display_name TEXT, number TEXT, status TEXT);",
        [("INSERT INTO wa_contacts VALUES (?,?,?,?)", ("4915443456786@s.whatsapp.net", "Tobias Klenk", "+4915443456786", "Werkstatt")),
         ("INSERT INTO wa_contacts VALUES (?,?,?,?)", ("4915123456789@s.whatsapp.net", "Anna", "+4915123456789", "")),
         ("INSERT INTO wa_contacts VALUES (?,?,?,?)", ("4915512345670@s.whatsapp.net", "Lena Vogt", "+4915512345670", ""))])
    # Media-Thumbnails (Platzhalter) im Sandcard-Pfad
    media = "storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media"
    for sub, fn in [("WhatsApp Images/Sent", "IMG-20260124-WA0007.jpg"),
                    (".Thumbs", "thumb_0007.jpg"),
                    ("WhatsApp Voice Notes/202601", "PTT-20260124-WA0003.opus")]:
        w_blob(f"{media}/{sub}/{fn}", b"WA-media-placeholder")
    manifest.append(("Samsung", rel, "context",
                     "WhatsApp wa.db: Kontakte (Tobias Klenk/Anna/Lena) + Media-Thumbnails"))


# ---------------- batterystats / netstats ----------------
def build_system_stats():
    w_text("data/system/batterystats.bin.txt",
           "# batterystats checkin (vereinfacht)\n"
           "9,0,l,bt,2026-01-25 07:50,level=55\n9,0,l,bt,2026-01-25 08:30,level=49\n")
    ensure(os.path.join(AND, "data/system/netstats"))
    w_text("data/system/netstats/uid_tag.dump.txt",
           "# net usage (vereinfacht)\nuid=10123(com.whatsapp) rx=1240321 tx=88231\n"
           "uid=10140(com.google.android.apps.maps) rx=552310 tx=12044\n")
    manifest.append(("Samsung", "data/system/batterystats.bin.txt", "noise", "batterystats/netstats (System-Telemetrie)"))


def write_manifest():
    out = os.path.join(ROOT, "06_master", "Android_Extra_Manifest.csv")
    ensure(os.path.dirname(out))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["geraet", "pfad", "relevanz", "beschreibung"]); w.writerows(manifest)
    return out


def main():
    ensure(TMP)
    build_usagestats(); build_shealth(); build_maps(); build_accounts()
    build_whatsapp_extra(); build_system_stats()
    out = write_manifest()
    print(f"Android-Extra: {len(manifest)} Artefaktgruppen")
    for g, p, r, d in manifest:
        print(f"  [{r:8s}] {p}")
    # Verifikation Maps
    mp = os.path.join(AND, "data/data/com.google.android.apps.maps/databases/gmm_myplaces.db")
    con = sqlite3.connect(f"file:{mp}?mode=ro&immutable=1", uri=True)
    titles = [r[0] for r in con.execute("SELECT title FROM sync_item").fetchall()]; con.close()
    print("Verifikation Maps-Ziele:", titles)


if __name__ == "__main__":
    main()
