#!/usr/bin/env python3
# =====================================================================
# gen_ios_photos_health.py
# ---------------------------------------------------------------------
# Erzeugt zwei iOS-Kern-Datenbanken, iLEAPP-kompatibel:
#   * Photos.sqlite          (ZASSET / ZADDITIONALASSETATTRIBUTES)
#   * healthdb_secure.sqlite (samples / quantity_samples / category_samples
#                             / metadata / data_provenances)
# Werte aus dem Case Master:
#   - HR-Peak 138 bpm um 07:50, danach Abbruch (Sensorkontakt verloren)
#   - Schlafphase 22:30 -> 06:50 (sleep_end)
#   - Foto-Bursts (Ben Training, Mittagessen, Screenshots Kursplan)
# Timestamps: Apple CFAbsoluteTime (Sekunden seit 2001-01-01) als REAL.
# =====================================================================
import os
import sqlite3
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
IOS_FS = os.environ.get('WALDWEG_IOS_FS', os.path.join(ROOT, '01_ios_full_fs'))

PHOTOS = os.path.join(IOS_FS, 'private/var/mobile/Media/PhotoData/Photos.sqlite')
HEALTH = os.path.join(IOS_FS, 'private/var/mobile/Library/Health/healthdb_secure.sqlite')

APPLE = 978307200  # Unix-Offset


def cf(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp() - APPLE


def reset(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        p = path + suffix
        if os.path.exists(p):
            os.remove(p)


# ---------------------------------------------------------------------
# PHOTOS.sqlite
# ---------------------------------------------------------------------
PHOTO_ROWS = [
    # (iso, filename, dir, lat, lon, w, h)
    ("2026-01-18T16:30:12+01:00", "IMG_2041.HEIC", "DCIM/108APPLE", 48.7689, 9.1740, 4032, 3024),  # Ben Training (Gym)
    ("2026-01-18T16:31:05+01:00", "IMG_2042.HEIC", "DCIM/108APPLE", 48.7689, 9.1740, 4032, 3024),
    ("2026-01-20T12:42:33+01:00", "IMG_2055.HEIC", "DCIM/108APPLE", 48.7831, 9.1817, 4032, 3024),  # Mittagessen (Buero)
    ("2026-01-22T09:15:00+01:00", "IMG_2061.PNG",  "DCIM/108APPLE", 0.0, 0.0, 1170, 2532),         # Screenshot Kursplan
    ("2026-01-24T18:42:50+01:00", "IMG_2068.HEIC", "DCIM/108APPLE", 48.7770, 9.1880, 4032, 3024),  # Supermarkt-Stopp
    # --- weitere Noise-Welle: Alltags-Bursts mit GPS ---
    ("2026-01-11T15:05:40+01:00", "IMG_2012.HEIC", "DCIM/107APPLE", 48.7702, 9.1955, 4032, 3024),  # Ben Training Burst 1
    ("2026-01-11T15:05:43+01:00", "IMG_2013.HEIC", "DCIM/107APPLE", 48.7702, 9.1955, 4032, 3024),  # Ben Training Burst 2
    ("2026-01-11T15:05:46+01:00", "IMG_2014.HEIC", "DCIM/107APPLE", 48.7702, 9.1955, 4032, 3024),  # Ben Training Burst 3
    ("2026-01-13T13:20:11+01:00", "IMG_2027.HEIC", "DCIM/108APPLE", 48.7831, 9.1817, 4032, 3024),  # Mittagessen Büro
    ("2026-01-15T19:48:02+01:00", "IMG_2033.HEIC", "DCIM/108APPLE", 48.7758, 9.1829, 4032, 3024),  # Abendessen zuhause
    ("2026-01-17T10:02:55+01:00", "IMG_2039.PNG",  "DCIM/108APPLE", 0.0, 0.0, 1170, 2532),         # Screenshot Rezept
    ("2026-01-23T08:31:17+01:00", "IMG_2063.HEIC", "DCIM/108APPLE", 48.7689, 9.1740, 4032, 3024),  # Gym Selfie
]


def build_photos():
    reset(PHOTOS)
    con = sqlite3.connect(PHOTOS)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE ZASSET (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER, Z_OPT INTEGER,
        ZDATECREATED REAL, ZMODIFICATIONDATE REAL, ZADDEDDATE REAL,
        ZLATITUDE REAL, ZLONGITUDE REAL,
        ZKIND INTEGER, ZWIDTH INTEGER, ZHEIGHT INTEGER,
        ZFILENAME TEXT, ZDIRECTORY TEXT,
        ZADDITIONALATTRIBUTES INTEGER, ZTRASHEDSTATE INTEGER DEFAULT 0
    );
    CREATE TABLE ZADDITIONALASSETATTRIBUTES (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER, Z_OPT INTEGER,
        ZASSET INTEGER,
        ZORIGINALFILENAME TEXT,
        ZTIMEZONENAME TEXT,
        ZEXIFTIMESTAMPSTRING TEXT
    );
    """)
    for i, (iso, fn, d, lat, lon, w, h) in enumerate(PHOTO_ROWS, start=1):
        t = cf(iso)
        kind = 0  # 0 = photo, 1 = video
        cur.execute("""INSERT INTO ZASSET
            (Z_PK,Z_ENT,Z_OPT,ZDATECREATED,ZMODIFICATIONDATE,ZADDEDDATE,
             ZLATITUDE,ZLONGITUDE,ZKIND,ZWIDTH,ZHEIGHT,ZFILENAME,ZDIRECTORY,
             ZADDITIONALATTRIBUTES)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (i, 1, 1, t, t, t, lat if lat else None, lon if lon else None,
             kind, w, h, fn, d, i))
        exif = datetime.fromisoformat(iso).strftime("%Y:%m:%d %H:%M:%S")
        cur.execute("""INSERT INTO ZADDITIONALASSETATTRIBUTES
            (Z_PK,Z_ENT,Z_OPT,ZASSET,ZORIGINALFILENAME,ZTIMEZONENAME,
             ZEXIFTIMESTAMPSTRING)
            VALUES (?,?,?,?,?,?,?)""",
            (i, 2, 1, i, fn, "Europe/Berlin", exif))
    con.commit()
    con.close()
    print(f"Photos.sqlite: {len(PHOTO_ROWS)} Assets -> {os.path.relpath(PHOTOS, ROOT)}")


# ---------------------------------------------------------------------
# healthdb_secure.sqlite
# ---------------------------------------------------------------------
# HK data_type IDs (wie von Apple/iLEAPP verwendet)
HR_TYPE = 5      # HKQuantityTypeIdentifierHeartRate
SLEEP_TYPE = 63  # HKCategoryTypeIdentifierSleepAnalysis

# Herzfrequenz-Serie 25.01 morgens: Anstieg -> Peak 138 @07:50 -> Abbruch
HR_SERIES = [
    ("2026-01-25T06:50:00+01:00", 58),
    ("2026-01-25T07:05:00+01:00", 64),
    ("2026-01-25T07:20:00+01:00", 72),
    ("2026-01-25T07:33:00+01:00", 95),
    ("2026-01-25T07:45:00+01:00", 121),
    ("2026-01-25T07:50:00+01:00", 138),  # Peak (planted_inc #3: Sport ODER Stress)
    # danach KEINE Werte mehr -> Sensorkontakt verloren / Geraet still
]

# Schlafphase Nacht 24.->25.01
SLEEP = [("2026-01-24T22:30:00+01:00", "2026-01-25T06:50:00+01:00", 1)]  # 1=asleep
STEP_TYPE, DIST_TYPE, WORKOUT_RUN = 7, 8, 37
# Schritt-Samples Tatmorgen (Aufbruch -> Bewegung)
STEPS = [("2026-01-25T07:33:00+01:00", "2026-01-25T07:40:00+01:00", 740),
         ("2026-01-25T07:40:00+01:00", "2026-01-25T07:50:00+01:00", 1120)]
# Workout (Spaziergang/Lauf) 07:33-07:50 + GPS-Route Home->Waldweg (deckt locationd)
WORKOUT = ("2026-01-25T07:33:00+01:00", "2026-01-25T07:50:00+01:00", 1020.0, 1450.0, 88.0)
ROUTE = [("2026-01-25T07:33:00+01:00", 48.7758, 9.1829, 250),
         ("2026-01-25T07:40:00+01:00", 48.7600, 9.2080, 255),
         ("2026-01-25T07:45:00+01:00", 48.7460, 9.2300, 248),
         ("2026-01-25T07:50:00+01:00", 48.7330, 9.2460, 243)]


def build_health():
    reset(HEALTH)
    con = sqlite3.connect(HEALTH)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE data_provenances (
        ROWID INTEGER PRIMARY KEY,
        origin_product_type TEXT,
        origin_build TEXT,
        source_id INTEGER,
        device_id INTEGER,
        source_version TEXT,
        tz_name TEXT
    );
    CREATE TABLE objects (
        data_id INTEGER PRIMARY KEY,
        provenance INTEGER,
        type INTEGER,
        creation_date REAL
    );
    CREATE TABLE samples (
        data_id INTEGER PRIMARY KEY,
        start_date REAL,
        end_date REAL,
        data_type INTEGER
    );
    CREATE TABLE quantity_samples (
        data_id INTEGER PRIMARY KEY,
        quantity REAL,
        original_quantity REAL,
        original_unit TEXT
    );
    CREATE TABLE category_samples (
        data_id INTEGER PRIMARY KEY,
        value INTEGER
    );
    CREATE TABLE metadata_keys (ROWID INTEGER PRIMARY KEY, key TEXT);
    CREATE TABLE metadata_values (
        ROWID INTEGER PRIMARY KEY, key_id INTEGER, object_id INTEGER,
        value TEXT
    );
    CREATE TABLE workouts (
        data_id INTEGER PRIMARY KEY, workout_type INTEGER,
        duration REAL, total_distance REAL, total_energy_burned REAL
    );
    CREATE TABLE workout_routes (
        ROWID INTEGER PRIMARY KEY, workout_id INTEGER, ts REAL,
        latitude REAL, longitude REAL, altitude REAL
    );
    """)
    # Provenance: Apple Watch (Annas Geraet)
    cur.execute("""INSERT INTO data_provenances
        (ROWID,origin_product_type,origin_build,source_id,device_id,
         source_version,tz_name)
        VALUES (1,'Watch6,7','21T...',1,1,'10.5','Europe/Berlin')""")

    did = 0
    # Herzfrequenz (quantity samples)
    for iso, bpm in HR_SERIES:
        did += 1
        t = cf(iso)
        cur.execute("INSERT INTO objects VALUES (?,?,?,?)", (did, 1, HR_TYPE, t))
        cur.execute("INSERT INTO samples VALUES (?,?,?,?)", (did, t, t, HR_TYPE))
        # HK speichert HR in count/s -> bpm/60
        cur.execute("INSERT INTO quantity_samples VALUES (?,?,?,?)",
                    (did, bpm / 60.0, float(bpm), "count/min"))
    # Schlaf (category samples)
    for start, end, val in SLEEP:
        did += 1
        s, e = cf(start), cf(end)
        cur.execute("INSERT INTO objects VALUES (?,?,?,?)", (did, 1, SLEEP_TYPE, s))
        cur.execute("INSERT INTO samples VALUES (?,?,?,?)", (did, s, e, SLEEP_TYPE))
        cur.execute("INSERT INTO category_samples VALUES (?,?)", (did, val))
    # Schritte + Distanz (quantity samples)
    for start, end, n in STEPS:
        did += 1; s, e = cf(start), cf(end)
        cur.execute("INSERT INTO objects VALUES (?,?,?,?)", (did, 1, STEP_TYPE, s))
        cur.execute("INSERT INTO samples VALUES (?,?,?,?)", (did, s, e, STEP_TYPE))
        cur.execute("INSERT INTO quantity_samples VALUES (?,?,?,?)", (did, float(n), float(n), "count"))
    # Workout + GPS-Route (Bewegung Home->Waldweg)
    did += 1; wid = did
    ws, we = cf(WORKOUT[0]), cf(WORKOUT[1])
    cur.execute("INSERT INTO objects VALUES (?,?,?,?)", (did, 1, 80, ws))   # 80 = workout
    cur.execute("INSERT INTO samples VALUES (?,?,?,?)", (did, ws, we, 80))
    cur.execute("INSERT INTO workouts VALUES (?,?,?,?,?)",
                (wid, WORKOUT_RUN, WORKOUT[2], WORKOUT[3], WORKOUT[4]))
    for iso, la, lo, alt in ROUTE:
        cur.execute("INSERT INTO workout_routes (workout_id,ts,latitude,longitude,altitude) VALUES (?,?,?,?,?)",
                    (wid, cf(iso), la, lo, alt))
    con.commit()
    con.close()
    print(f"healthdb_secure.sqlite: {len(HR_SERIES)} HR + {len(SLEEP)} Schlaf + "
          f"{len(STEPS)} Schritt-Samples + 1 Workout ({len(ROUTE)} Routenpunkte) "
          f"-> {os.path.relpath(HEALTH, ROOT)}")


def verify():
    print("\n=== Verifikation Health ===")
    con = sqlite3.connect(HEALTH)
    rows = con.execute("""
        SELECT s.start_date, q.original_quantity
        FROM samples s JOIN quantity_samples q ON s.data_id=q.data_id
        WHERE s.data_type=? ORDER BY s.start_date""", (HR_TYPE,)).fetchall()
    for t, bpm in rows:
        ts = datetime.utcfromtimestamp(t + APPLE)
        print(f"  HR {ts:%H:%M} UTC: {bpm:.0f} bpm")
    peak = max(r[1] for r in rows)
    print(f"  -> Peak: {peak:.0f} bpm (erwartet 138):", "OK" if peak == 138 else "FEHLER")
    con.close()

    print("=== Verifikation Photos ===")
    con = sqlite3.connect(PHOTOS)
    n = con.execute("SELECT COUNT(*) FROM ZASSET").fetchone()[0]
    geo = con.execute("SELECT COUNT(*) FROM ZASSET WHERE ZLATITUDE IS NOT NULL").fetchone()[0]
    print(f"  {n} Assets, davon {geo} mit GPS")
    con.close()


def main():
    build_photos()
    build_health()
    verify()


if __name__ == "__main__":
    main()
