#!/usr/bin/env python3
# =====================================================================
# gen_android_scoped.py  —  Scoped-Storage Media-Provider external.db
# ---------------------------------------------------------------------
# Versionsmerkmal: Scoped Storage (ab Android 10/11 zunehmend erzwungen)
# protokolliert ueber den Media-Provider, welche App wann welche Datei
# beruehrt hat -> external.db (Tabelle 'files'). Der Provider-PAKETPFAD
# wechselte mit Android 11 von 'com.android.providers.media' (legacy) zu
# 'com.google.android.providers.media.module' (module).
#
# Erzeugt external.db NUR, wenn das aktive Android-Geraet das Profil-Flag
# 'scoped_storage' traegt (Profile android_13/14/15). Der Pfad richtet sich
# nach Flag 'media_provider' (module|legacy).
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

AND = os.environ.get("WALDWEG_AND_FS", os.path.join(ROOT, "02_android_full_fs"))

PROVIDER = {
    "module": "com.google.android.providers.media.module",
    "legacy": "com.android.providers.media",
}


def ms(iso):
    return int(datetime.fromisoformat(iso).timestamp())  # MediaStore: Sekunden


# (relpath, mime, owner_pkg, added_iso, modified_iso)
FILES = [
    ("/storage/emulated/0/DCIM/Camera/IMG_20260124_2003.jpg", "image/jpeg",
     "com.sec.android.app.camera", "2026-01-24T20:03:00+01:00", "2026-01-24T20:03:00+01:00"),
    ("/storage/emulated/0/Download/Rechnung_Werkstatt.pdf", "application/pdf",
     "com.android.chrome", "2026-01-24T22:35:00+01:00", "2026-01-24T22:35:00+01:00"),
    ("/storage/emulated/0/Pictures/Screenshots/Screenshot_Route.png", "image/png",
     "com.sec.android.app.launcher", "2026-01-25T07:20:00+01:00", "2026-01-25T07:20:00+01:00"),
    ("/storage/emulated/0/WhatsApp/Media/WhatsApp Voice Notes/voice.opus", "audio/ogg",
     "com.whatsapp", "2026-01-24T20:05:00+01:00", "2026-01-24T20:05:00+01:00"),
]


# Privacy Dashboard (ab Android 12): permission-Nutzung je App in /system/appops/discrete
# Reales Format ist ABX (Android Binary XML, Magic 'ABX\0'). Hier: ABX-Magic +
# lesbare XML-Repraesentation (vereinfacht; voll-faithful ABX-Codec = Folgearbeit).
PRIVACY_ACCESS = [
    ("com.android.chrome", "android:fine_location", "2026-01-25T07:18:00+01:00"),
    ("com.whatsapp", "android:record_audio", "2026-01-24T20:05:00+01:00"),
    ("com.sec.android.app.camera", "android:camera", "2026-01-24T20:03:00+01:00"),
    ("com.google.android.apps.maps", "android:fine_location", "2026-01-25T08:02:00+01:00"),
]


def privacy_dashboard():
    if not cmio.device_profile_flag("android", "privacy_dashboard", False):
        return
    from datetime import datetime as _dt
    import abx_writer as abx
    d = os.path.join(AND, "data/system/appops/discrete")
    os.makedirs(d, exist_ok=True)
    # Voll-faithful ABX (AOSP BinaryXmlSerializer): <dl><pkg><op><a .../></op></pkg></dl>
    w = abx.AbxSerializer().start_document().start_tag("dl")
    for pkg, op, iso in PRIVACY_ACCESS:
        ts = int(_dt.fromisoformat(iso).timestamp() * 1000)
        w.start_tag("pkg").attr("n", pkg)
        w.start_tag("op").attr("n", op)
        w.start_tag("a").attr("t", ts).attr("d", 2000).end_tag("a")
        w.end_tag("op").end_tag("pkg")
    w.end_tag("dl").end_document()
    with open(os.path.join(d, "1.xml"), "wb") as f:
        f.write(w.getvalue())
    print(f"Privacy Dashboard: data/system/appops/discrete/1.xml "
          f"({len(PRIVACY_ACCESS)} Zugriffe, voll-faithful ABX)")


def main():
    if not cmio.device_profile_flag("android", "scoped_storage", False):
        print("Scoped Storage: [SKIP] Android-Profil ohne Flag 'scoped_storage'.")
        privacy_dashboard()
        return
    prov = cmio.device_profile_flag("android", "media_provider", "module")
    pkg = PROVIDER.get(str(prov), PROVIDER["module"])
    db = os.path.join(AND, "data/data", pkg, "databases/external.db")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    for s in ("", "-wal", "-shm"):
        if os.path.exists(db + s):
            os.remove(db + s)
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE files (
        _id INTEGER PRIMARY KEY AUTOINCREMENT,
        _data TEXT UNIQUE COLLATE NOCASE,
        _size INTEGER,
        date_added INTEGER,
        date_modified INTEGER,
        mime_type TEXT,
        media_type INTEGER,
        volume_name TEXT,
        owner_package_name TEXT,
        is_pending INTEGER DEFAULT 0,
        is_trashed INTEGER DEFAULT 0,
        _display_name TEXT
    );
    """)
    cur = con.cursor()
    mtmap = {"image/jpeg": 1, "image/png": 1, "video/mp4": 3, "audio/ogg": 2, "application/pdf": 6}
    for rel, mime, owner, a_iso, m_iso in FILES:
        cur.execute("""INSERT INTO files
            (_data,_size,date_added,date_modified,mime_type,media_type,volume_name,
             owner_package_name,_display_name)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (rel, 1024 * (len(rel) % 900 + 50), ms(a_iso), ms(m_iso), mime,
             mtmap.get(mime, 0), "external_primary", owner, os.path.basename(rel)))
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    con.close()
    print(f"external.db erzeugt (Scoped Storage, Provider={prov}): "
          f"data/data/{pkg}/databases/external.db  ({n} Dateieintraege)")
    privacy_dashboard()


if __name__ == "__main__":
    main()
