#!/usr/bin/env python3
# =====================================================================
# gen_ios_extra.py  —  zusaetzliche iOS-Artefakte
# ---------------------------------------------------------------------
#   * Safari   : History.db (real Schema) + Bookmarks.db + RecentlyClosedTabs.plist
#                im mobilesafari-App-Container
#   * Voicemail: voicemail.db neben der bereits eingebetteten .wav
#   * CallHistory.storedata (ZCALLRECORD) mit Anrufen
#   * App-Snapshots (Library/Caches/Snapshots/<bundle>) – letzter App-Zustand
# Zeit: Apple-CFAbsoluteTime (Safari/CallHistory), Unix (Voicemail).
# SQLite in /tmp gebaut, dann kopiert.
# =====================================================================
import os
import shutil
import sqlite3
import hashlib
import plistlib
import struct
import zlib
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
import sys
sys.path.insert(0, HERE)
import case_master_io as cmio
IOS = os.environ.get("WALDWEG_IOS_FS", os.path.join(ROOT, "01_ios_full_fs"))
TMP = "/tmp/ios_extra_build"
APPLE = 978307200
manifest = []


def cf(iso):
    return datetime.fromisoformat(iso).timestamp() - APPLE


def ux(iso):
    return int(datetime.fromisoformat(iso).timestamp())


import caseforge_rng as cfr
def guid(bundle):
    return cfr.app_guid(bundle)


def ensure(d):
    os.makedirs(d, exist_ok=True)


def build_sqlite(rel, script, rows=None):
    dst = os.path.join(IOS, rel)
    ensure(os.path.dirname(dst))
    tmp = os.path.join(TMP, hashlib.md5(rel.encode()).hexdigest() + ".db")
    ensure(TMP)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(tmp + s):
            os.remove(tmp + s)
    con = sqlite3.connect(tmp)
    con.executescript(script)
    if rows:
        for sql, params in rows:
            con.execute(sql, params)
    con.commit(); con.close()
    shutil.copy(tmp, dst)
    return dst


def tiny_png(w=120, h=200, rgb=(40, 40, 60)):
    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes(rgb) * w
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


# ---------------- Safari ----------------
SAFARI = "private/var/mobile/Containers/Data/Application/%s" % guid("com.apple.mobilesafari")
FALLBACK_SAFARI_URLS = [
    ("2026-01-25T07:05:00+01:00", "https://www.google.com/search?q=anwalt+trennung+sorgerecht", "anwalt trennung sorgerecht - Google Suche"),
    ("2026-01-25T07:09:00+01:00", "https://www.bahn.de/verbindungen", "Reiseauskunft - Deutsche Bahn"),
    ("2026-01-22T22:40:00+01:00", "https://www.immobilienscout24.de/wohnung-mieten", "wohnung mieten 2 zimmer - ImmoScout24"),
    ("2026-01-20T19:30:00+01:00", "https://www.chefkoch.de/", "Chefkoch - Rezepte"),
]
# Master-getrieben (Safari = iOS-Browser), sonst Pool/seed (Nicht-Referenz) bzw. Fallback
def _resolve_safari():
    import noise_pools as _np
    from datetime import datetime as _dt, timedelta as _td
    mt = cmio.browser_history("ios")
    if mt:
        return mt
    if cfr.is_reference():
        return FALLBACK_SAFARI_URLS
    lang = cmio.language_short()
    n = cmio.noise_count(4, key="browser_noise")
    picked = cfr.sample(_np.web(lang), n, salt="safari_noise")
    base = _dt.fromisoformat("2026-01-20T19:00:00+01:00")
    return [((base + _td(hours=i)).isoformat(), u, t) for i, (u, t) in enumerate(picked)]


SAFARI_URLS = _resolve_safari()


def build_safari():
    rel = SAFARI + "/Library/Safari/History.db"
    items, visits = [], []
    for i, (iso, url, title) in enumerate(SAFARI_URLS, 1):
        dom = url.split("/")[2]
        items.append(("INSERT INTO history_items (id,url,domain_expansion,visit_count) VALUES (?,?,?,1)",
                      (i, url, dom)))
        visits.append(("INSERT INTO history_visits (id,history_item,visit_time,title) VALUES (?,?,?,?)",
                       (i, i, cf(iso), title)))
    build_sqlite(rel,
        "CREATE TABLE history_items (id INTEGER PRIMARY KEY, url TEXT, domain_expansion TEXT, visit_count INTEGER);"
        "CREATE TABLE history_visits (id INTEGER PRIMARY KEY, history_item INTEGER, visit_time REAL, title TEXT);",
        items + visits)
    manifest.append(("iPhone", os.path.relpath(os.path.join(IOS, rel), ROOT), "context",
                     "Safari History.db (Anwalt/Bahn/Wohnung) – deckungsgleich mit BIOME-Safari"))
    # Bookmarks
    relb = SAFARI + "/Library/Safari/Bookmarks.db"
    build_sqlite(relb,
        "CREATE TABLE bookmarks (id INTEGER PRIMARY KEY, title TEXT, url TEXT, parent INTEGER);",
        [("INSERT INTO bookmarks (title,url,parent) VALUES (?,?,?)", t) for t in [
            ("Familienrecht Beratung", "https://www.anwalt.de/familienrecht", 1),
            ("Deutsche Bahn", "https://www.bahn.de", 1),
            ("ImmoScout24", "https://www.immobilienscout24.de", 1)]])
    manifest.append(("iPhone", os.path.relpath(os.path.join(IOS, relb), ROOT), "context", "Safari-Lesezeichen"))
    # RecentlyClosedTabs.plist
    relt = os.path.join(IOS, SAFARI, "Library/Safari/RecentlyClosedTabs.plist")
    ensure(os.path.dirname(relt))
    with open(relt, "wb") as f:
        tabs = []
        for (iso, url, title) in SAFARI_URLS[:2]:
            tabs.append({"Title": title, "URL": url,
                         "DateClosed": datetime.fromisoformat(iso)})
        plistlib.dump({"ClosedTabOrWindowPersistentStates": tabs}, f)
    manifest.append(("iPhone", os.path.relpath(relt, ROOT), "context", "Safari zuletzt geschlossene Tabs"))
    # App-Container-Metadaten
    mp = os.path.join(IOS, SAFARI, ".com.apple.mobile_container_manager.metadata.plist")
    with open(mp, "wb") as f:
        plistlib.dump({"MCMMetadataIdentifier": "com.apple.mobilesafari"}, f)


# ---------------- Voicemail-DB ----------------
def build_voicemail():
    rel = "private/var/mobile/Library/Voicemail/voicemail.db"
    build_sqlite(rel,
        "CREATE TABLE voicemail (ROWID INTEGER PRIMARY KEY, remote_uid INTEGER, date INTEGER, token TEXT,"
        " sender TEXT, callback_num TEXT, duration INTEGER, expiration INTEGER, trashed_date INTEGER, flags INTEGER);",
        [("INSERT INTO voicemail (date,sender,callback_num,duration,flags) VALUES (?,?,?,?,0)",
          (ux("2026-01-25T11:05:00+01:00"), "Stadtwerke Buero", "+49711000000", 18))])
    manifest.append(("iPhone", os.path.relpath(os.path.join(IOS, rel), ROOT), "context",
                     "voicemail.db -> verweist auf voicemail_anna_office_de.wav (Buero sucht Anna)"))


# ---------------- CallHistory.storedata ----------------
DANIEL, JONAS, LENA = "+4915223456788", "+4915333456787", "+4915512345670"
CALLS = [
    # (iso, address, duration_s, originated(1=outgoing), answered, calltype)
    ("2026-01-24T19:40:00+01:00", LENA, 612, 1, 1, 1),
    ("2026-01-24T21:05:00+01:00", JONAS, 433, 0, 1, 1),
    ("2026-01-25T07:18:00+01:00", JONAS, 38, 1, 1, 1),     # kurz vor Aufbruch
    ("2026-01-25T07:26:00+01:00", DANIEL, 0, 0, 0, 1),     # verpasst (Daniel ruft an)
]


def build_callhistory():
    rel = "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata"
    rows = []
    for i, (iso, addr, dur, orig, ans, ctype) in enumerate(CALLS, 1):
        rows.append(("INSERT INTO ZCALLRECORD (Z_PK,Z_ENT,Z_OPT,ZADDRESS,ZDATE,ZDURATION,ZORIGINATED,ZANSWERED,ZCALLTYPE)"
                     " VALUES (?,1,1,?,?,?,?,?,?)",
                     (i, addr.encode(), cf(iso), float(dur), orig, ans, ctype)))
    build_sqlite(rel,
        "CREATE TABLE Z_METADATA (Z_VERSION INTEGER, Z_UUID VARCHAR(255), Z_PLIST BLOB);"
        "CREATE TABLE ZCALLRECORD (Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER,"
        " ZADDRESS BLOB, ZDATE REAL, ZDURATION REAL, ZORIGINATED INTEGER, ZANSWERED INTEGER, ZCALLTYPE INTEGER);",
        rows)
    manifest.append(("iPhone", os.path.relpath(os.path.join(IOS, rel), ROOT), "critical",
                     "CallHistory: 07:18 Anruf->Jonas (38s), 07:26 verpasst von Daniel (passt zur Timeline)"))


# ---------------- App-Snapshots (echte gerenderte Screenshots) ----------------
def _render_snapshot(bundle):
    """Rendert einen plausiblen App-Screenshot (letzter sichtbarer Zustand) als JPEG."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 390, 844
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    def font(sz, bold=False):
        for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
                  "/Library/Fonts/Arial.ttf"]:
            if os.path.exists(p):
                return ImageFont.truetype(p, sz)
        return ImageFont.load_default()
    # Statusbar
    d.rectangle([0, 0, W, 44], fill=(247, 247, 247))
    d.text((16, 14), "08:31", font=font(15, True), fill=(0, 0, 0))
    d.text((W - 60, 14), "61 %", font=font(14), fill=(0, 0, 0))

    if bundle == "com.apple.mobilesafari":
        d.rectangle([0, 44, W, 92], fill=(247, 247, 247))
        d.rounded_rectangle([12, 54, W - 12, 84], 8, fill=(230, 230, 232))
        d.text((28, 62), "google.com/search?q=anwalt trennung…", font=font(13), fill=(60, 60, 60))
        d.text((16, 110), "anwalt trennung sorgerecht", font=font(20, True), fill=(20, 20, 20))
        for i, (t, s) in enumerate([
            ("Trennung & Scheidung – Erstberatung", "anwalt.de › familienrecht"),
            ("Sorgerecht: gemeinsam oder allein?", "familienrecht-ratgeber.de"),
            ("Ablauf einer einvernehmlichen Trennung", "kanzlei-... › trennung")]):
            y = 150 + i * 70
            d.text((16, y), s, font=font(12), fill=(20, 120, 40))
            d.text((16, y + 18), t, font=font(15), fill=(30, 30, 140))
        col = (60, 90, 120)
    elif bundle == "org.whispersystems.signal":
        d.rectangle([0, 44, W, 92], fill=(42, 110, 230))
        d.text((60, 60), "Jonas", font=font(17, True), fill=(255, 255, 255))
        bubbles = [("Bist du wach? Wir muessen reden.", False, 150),
                   ("Ja. Morgen frueh, am Parkplatz?", True, 210),
                   ("Halb neun. Ich bring Kaffee mit.", False, 270),
                   ("Bin in 30 Min da.", True, 330)]
        for txt, mine, y in bubbles:
            w = 230
            x0 = W - w - 14 if mine else 14
            d.rounded_rectangle([x0, y, x0 + w, y + 40], 14,
                                fill=(70, 160, 90) if mine else (235, 235, 235))
            d.text((x0 + 12, y + 11), txt, font=font(13),
                   fill=(255, 255, 255) if mine else (20, 20, 20))
        col = (20, 60, 40)
    else:  # Instagram
        d.rectangle([0, 44, W, 88], fill=(255, 255, 255))
        d.text((16, 56), "Instagram", font=font(20, True), fill=(20, 20, 20))
        d.ellipse([16, 100, 56, 140], fill=(220, 220, 220))
        d.text((64, 112), "lena_vogt", font=font(14, True), fill=(20, 20, 20))
        d.rectangle([0, 150, W, 560], fill=(210, 215, 220))
        d.text((20, 350), "[Foto]", font=font(16), fill=(120, 120, 120))
        d.text((16, 575), "gefaellt anna.reuter und 23 weiteren", font=font(12), fill=(40, 40, 40))
        col = (80, 30, 60)
    # Homebar
    d.rounded_rectangle([W // 2 - 60, H - 12, W // 2 + 60, H - 8], 2, fill=(0, 0, 0))
    return img


def build_snapshots():
    from io import BytesIO
    base = os.path.join(IOS, "private/var/mobile/Library/Caches/Snapshots")
    for bundle in ("com.apple.mobilesafari", "org.whispersystems.signal", "com.burbn.instagram"):
        d = os.path.join(base, bundle, "sceneID-default")
        ensure(d)
        img = _render_snapshot(bundle)
        img.save(os.path.join(d, "downscaled.jpeg"), "JPEG", quality=85)
    manifest.append(("iPhone", os.path.relpath(base, ROOT), "context",
                     "App-Snapshots (gerenderter letzter App-Zustand): Safari-Suche 'anwalt trennung', "
                     "Signal-Chat mit Jonas (Treffen Parkplatz), Instagram"))


def build_shutdownlog():
    """shutdown.log (Sysdiag) — iOS 26 (Profil-Flag shutdown_log). Forensisch
    relevant fuer Reboot-/Spyware-Analyse (verbleibende Power-Assertion-PIDs)."""
    if not cmio.device_profile_flag("ios", "shutdown_log", False):
        return
    p = os.path.join(IOS, "private/var/db/com.apple.shutdown.log")
    ensure(os.path.dirname(p))
    lines = [
        "2026-01-24 22:59:41.001 +0000: After 30 seconds shutdown is not complete.",
        "2026-01-24 22:59:41.002 +0000:   remaining client pid: 184 (com.apple.mobilesafari)",
        "2026-01-24 22:59:41.003 +0000:   remaining client pid: 233 (net.whatsapp.WhatsApp)",
        "2026-01-24 22:59:44.110 +0000: SIGKILL sent to remaining clients.",
        "2026-01-25 06:48:12.500 +0000: After 30 seconds shutdown is not complete.",
        "2026-01-25 06:48:12.501 +0000:   remaining client pid: 91 (com.apple.locationd)",
        "2026-01-25 06:48:15.900 +0000: shutdown complete.",
    ]
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    manifest.append(("iPhone", os.path.relpath(p, ROOT), "context",
                     "shutdown.log (iOS 26) — verbleibende PIDs bei Reboot (Spyware-/Reboot-Forensik)"))


def main():
    ensure(TMP)
    build_safari(); build_voicemail(); build_callhistory(); build_snapshots(); build_shutdownlog()
    print(f"iOS-Extra erzeugt: {len(manifest)} Artefakte")
    for g, p, r, d in manifest:
        print(f"  [{r:8s}] {p}")
    # Verifikation
    sh = os.path.join(IOS, SAFARI, "Library/Safari/History.db")
    con = sqlite3.connect(f"file:{sh}?mode=ro&immutable=1", uri=True)
    n = con.execute("SELECT COUNT(*) FROM history_visits").fetchone()[0]; con.close()
    print(f"Verifikation: Safari History {n} Visits")


if __name__ == "__main__":
    main()
