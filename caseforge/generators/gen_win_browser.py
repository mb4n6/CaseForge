#!/usr/bin/env python3
# =====================================================================
# gen_win_browser.py  —  Edge-Browser-Tiefe (Notebook Daniel)
# ---------------------------------------------------------------------
# Erweitert die Edge-Artefakte um forensisch wertvolle Strukturen:
#   * History         : urls + visits + DOWNLOADS (downloads/_url_chains)
#   * Bookmarks       : JSON (Bank/Kredit/Lebensversicherung)
#   * Web Data        : autofill (Suchbegriffe/Adressen)  [SQLite]
#   * Login Data      : logins (Bank-Account)             [SQLite]
# Chromium-Schemata; Zeit = WebKit-µs (seit 1601). SQLite -> Build in
# /tmp, dann Copy (Mount erlaubt kein In-Place-SQLite).
# =====================================================================
import os
import sys
import json
import shutil
import sqlite3
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
sys.path.insert(0, HERE)
import case_master_io as cmio
import caseforge_rng as cfr
import noise_pools as npool
WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
WUSER = cmio.windows_username()   # Windows-Profilordner aus Fall-Besitzer
EDGE = os.path.join(WIN, f"C/Users/{WUSER}/AppData/Local/Microsoft/Edge/User Data/Default")
TMP = "/tmp/edge_build"


def webkit(iso):
    return int((datetime.fromisoformat(iso).timestamp() + 11644473600) * 1_000_000)


FALLBACK_URLS = [
    ("2026-01-24T22:20:00+01:00", "https://www.google.com/search?q=lebensversicherung+auszahlung+todesfall", "lebensversicherung auszahlung todesfall - Google Suche"),
    ("2026-01-24T22:31:00+01:00", "https://www.check24.de/kredit/", "Kreditvergleich - CHECK24"),
    ("2026-01-21T20:05:00+01:00", "https://www.sparkasse.de/", "Sparkasse Online-Banking"),
    ("2026-01-19T21:00:00+01:00", "https://www.amazon.de/", "Amazon.de"),
]
DOWNLOADS = [
    # (start, target_path, url, bytes, mime, referrer)
    ("2026-01-24T22:33:00+01:00", rf"C:\Users\{WUSER}\Downloads\Kreditantrag_Sofort.pdf",
     "https://www.check24.de/kredit/antrag.pdf", 248123, "application/pdf", "https://www.check24.de/kredit/"),
    ("2026-01-24T22:48:00+01:00", rf"C:\Users\{WUSER}\Downloads\rufus-4.4p.exe",
     "https://github.com/pbatard/rufus/releases/download/v4.4/rufus-4.4p.exe", 1456789,
     "application/x-msdownload", "https://rufus.ie/"),
]


def build_history():
    mt = cmio.browser_history("windows")
    if mt:
        URLS = mt; src = "Master"
    elif cfr.is_reference():
        URLS = FALLBACK_URLS; src = "Referenz-Fallback"
    else:
        lang = cmio.language_short()
        n = cmio.noise_count(4, key="browser_noise")
        picked = cfr.sample(npool.web(lang), n, salt="edge_noise")
        base = datetime.fromisoformat("2026-01-19T20:00:00+01:00")
        URLS = [((base + timedelta(hours=i)).isoformat(), u, t) for i, (u, t) in enumerate(picked)]
        src = f"Pool/seed (scope, {len(URLS)})"
    print(f"  Edge-Inhaltsquelle: {src} ({len(URLS)} URLs)")
    p = os.path.join(TMP, "History")
    con = sqlite3.connect(p)
    con.executescript("""
    CREATE TABLE urls(id INTEGER PRIMARY KEY,url TEXT,title TEXT,visit_count INT DEFAULT 1,
        typed_count INT DEFAULT 0,last_visit_time INT,hidden INT DEFAULT 0);
    CREATE TABLE visits(id INTEGER PRIMARY KEY,url INT,visit_time INT,from_visit INT,
        transition INT DEFAULT 805306368);
    CREATE TABLE downloads(id INTEGER PRIMARY KEY,guid TEXT,current_path TEXT,target_path TEXT,
        start_time INT,received_bytes INT,total_bytes INT,state INT DEFAULT 1,danger_type INT DEFAULT 0,
        interrupt_reason INT DEFAULT 0,end_time INT,opened INT DEFAULT 0,referrer TEXT,
        tab_url TEXT,mime_type TEXT,original_mime_type TEXT,last_access_time INT);
    CREATE TABLE downloads_url_chains(id INT,chain_index INT,url TEXT,PRIMARY KEY(id,chain_index));
    """)
    cur = con.cursor()
    for i, (iso, url, title) in enumerate(URLS, 1):
        t = webkit(iso)
        cur.execute("INSERT INTO urls(id,url,title,visit_count,typed_count,last_visit_time) VALUES(?,?,?,1,1,?)", (i, url, title, t))
        cur.execute("INSERT INTO visits(id,url,visit_time) VALUES(?,?,?)", (i, i, t))
    for i, (iso, tgt, url, sz, mime, ref) in enumerate(DOWNLOADS, 1):
        t = webkit(iso)
        cur.execute("""INSERT INTO downloads(id,guid,current_path,target_path,start_time,received_bytes,
            total_bytes,state,end_time,opened,referrer,tab_url,mime_type,original_mime_type,last_access_time)
            VALUES(?,?,?,?,?,?,?,1,?,1,?,?,?,?,?)""",
            (i, f"GUID-{i:04d}", tgt, tgt, t, sz, sz, t + 5_000_000, ref, ref, mime, mime, t))
        cur.execute("INSERT INTO downloads_url_chains(id,chain_index,url) VALUES(?,0,?)", (i, url))
    con.commit(); con.close()
    return p


def build_bookmarks():
    p = os.path.join(TMP, "Bookmarks")
    def bm(name, url, iso):
        return {"type": "url", "name": name, "url": url,
                "date_added": str(webkit(iso))}
    data = {"roots": {"bookmark_bar": {"type": "folder", "name": "Lesezeichenleiste", "children": [
        bm("Sparkasse Banking", "https://www.sparkasse.de/", "2025-10-01T10:00:00+01:00"),
        bm("CHECK24 Kredit", "https://www.check24.de/kredit/", "2026-01-24T22:31:00+01:00"),
        bm("Lebensversicherung kuendigen/auszahlen", "https://www.google.com/search?q=lebensversicherung+auszahlung+todesfall", "2026-01-24T22:21:00+01:00"),
    ]}, "other": {"type": "folder", "name": "Weitere", "children": []},
        "synced": {"type": "folder", "name": "Mobil", "children": []}}, "version": 1}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=3, ensure_ascii=False)
    return p


def build_webdata():
    p = os.path.join(TMP, "Web Data")
    con = sqlite3.connect(p)
    con.executescript("""
    CREATE TABLE autofill(name TEXT,value TEXT,value_lower TEXT,date_created INT,date_last_used INT,count INT);
    CREATE TABLE keywords(id INTEGER PRIMARY KEY,short_name TEXT,keyword TEXT,url TEXT);
    """)
    cur = con.cursor()
    rows = [("q", "lebensversicherung auszahlung todesfall", "lebensversicherung auszahlung todesfall"),
            ("q", "kredit sofort ohne schufa", "kredit sofort ohne schufa"),
            ("email", "d.reuter@example.de", "d.reuter@example.de"),
            ("name", "Daniel Reuter", "daniel reuter")]
    base = webkit("2026-01-24T22:00:00+01:00") // 1_000_000  # autofill nutzt Unix-Sek? Chromium: Unix epoch sec
    import time
    for nm, val, low in rows:
        ts = int(datetime.fromisoformat("2026-01-24T22:25:00+01:00").timestamp())
        cur.execute("INSERT INTO autofill VALUES(?,?,?,?,?,?)", (nm, val, low, ts, ts, 2))
    con.commit(); con.close()
    return p


def build_logindata():
    p = os.path.join(TMP, "Login Data")
    con = sqlite3.connect(p)
    con.executescript("""
    CREATE TABLE logins(origin_url TEXT,action_url TEXT,username_element TEXT,username_value TEXT,
        password_element TEXT,password_value BLOB,date_created INT,times_used INT,date_last_used INT,
        signon_realm TEXT,blacklisted_by_user INT DEFAULT 0);
    """)
    cur = con.cursor()
    rows = [("https://www.sparkasse.de/", "Daniel.Reuter", "sparkasse.de"),
            ("https://www.check24.de/", "d.reuter@example.de", "check24.de")]
    t = webkit("2025-10-01T10:00:00+01:00")
    for origin, user, realm in rows:
        cur.execute("""INSERT INTO logins(origin_url,action_url,username_element,username_value,
            password_element,password_value,date_created,times_used,date_last_used,signon_realm)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (origin, origin, "user", user, "pass",
             b"v10\x00ENCRYPTED-DPAPI-BLOB-PLACEHOLDER", t, 5, t, "https://" + realm + "/"))
    con.commit(); con.close()
    return p


def main():
    os.makedirs(TMP, exist_ok=True)
    for fn in ("History", "Bookmarks", "Web Data", "Login Data"):
        fp = os.path.join(TMP, fn)
        if os.path.exists(fp):
            os.remove(fp)
    build_history(); build_bookmarks(); build_webdata(); build_logindata()
    os.makedirs(EDGE, exist_ok=True)
    for fn in ("History", "Bookmarks", "Web Data", "Login Data"):
        shutil.copy(os.path.join(TMP, fn), os.path.join(EDGE, fn))
        print(f"  {fn} -> {os.path.relpath(os.path.join(EDGE, fn), ROOT)}")

    # Verifikation
    con = sqlite3.connect(f"file:{os.path.join(EDGE,'History')}?mode=ro&immutable=1", uri=True)
    nd = con.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
    tgt = con.execute("SELECT target_path FROM downloads ORDER BY id").fetchall()
    con.close()
    print(f"\nVerifikation: {nd} Downloads -> {[os.path.basename(t[0]) for t in tgt]}")
    bm = json.load(open(os.path.join(EDGE, "Bookmarks")))
    print("Bookmarks:", [c["name"] for c in bm["roots"]["bookmark_bar"]["children"]])


if __name__ == "__main__":
    main()
