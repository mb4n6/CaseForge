#!/usr/bin/env python3
# =====================================================================
# embed_media.py  —  Medien schluessig in die FS-Ebene einbetten (Option B)
# ---------------------------------------------------------------------
# Verschiebt (nicht kopiert!) die Mediendateien aus 07_multimedia /
# 08_multilingual an realistische Speicherorte:
#   * geraetezuordenbare Medien  -> in das jeweilige Geraete-Dateisystem
#   * echte Tatort-/Ermittlungs-Exhibits -> 05_police_records
# Reine Referenz-/Index-Dateien (README, *_metadata.csv, Transkripte,
# chat_extensions.json, abgeleitete Frames) bleiben liegen.
# Photos.sqlite erhaelt fuer das Geraete-Video eine passende ZASSET-Zeile,
# damit DB-Eintrag und Datei konsistent sind.
#
# Idempotent: bereits verschobene Dateien werden uebersprungen.
# Schreibt ein Mapping-Manifest nach 06_master/Medien_FS_Mapping.csv.
# =====================================================================
import os
import csv
import shutil
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
APPLE = 978307200

# Fall-Root aus Env ableiten (CaseForge), sonst Referenzfall
IOS = os.environ.get("WALDWEG_IOS_FS", os.path.join(ROOT, "01_ios_full_fs"))
AND = os.environ.get("WALDWEG_AND_FS", os.path.join(ROOT, "02_android_full_fs"))
CASE_ROOT = os.path.dirname(IOS) if os.environ.get("WALDWEG_IOS_FS") else ROOT
POLICE = os.path.join(CASE_ROOT, "05_police_records")
MM = os.path.join(CASE_ROOT, "07_multimedia")
ML = os.path.join(CASE_ROOT, "08_multilingual")

WA_IOS_MEDIA = os.path.join(IOS, "private/var/mobile/Library/Mobile Documents/"
                            "57T9237FN3~net~whatsapp~WhatsApp/Message/Media")
VOICEMAIL = os.path.join(IOS, "private/var/mobile/Library/Voicemail")
IOS_DCIM = os.path.join(IOS, "private/var/mobile/Media/DCIM/108APPLE")
AND_SHOTS = os.path.join(AND, "storage/emulated/0/Pictures/Screenshots")
PHOTOS_DB = os.path.join(IOS, "private/var/mobile/Media/PhotoData/Photos.sqlite")

mapping = []  # (quelle_rel, ziel_rel, kategorie, begruendung)

# (src_abs, dst_abs, kategorie, begruendung)
MOVES = [
    # --- Geraete-Medien: Annas iPhone ---
    (os.path.join(MM, "audio/voicemail/voicemail_anna_office_de.wav"),
     os.path.join(VOICEMAIL, "voicemail_anna_office_de.wav"),
     "iPhone/Voicemail", "Mailbox-Nachricht Stadtwerke -> Anna"),
    (os.path.join(MM, "audio/whatsapp_voice/voice_lena_de.wav"),
     os.path.join(WA_IOS_MEDIA, "voice_lena_de.wav"),
     "iPhone/WhatsApp-Media", "WhatsApp-Sprachnachricht Lena -> Anna"),
    (os.path.join(ML, "audio_foreign/voice_projektpartner_en.wav"),
     os.path.join(WA_IOS_MEDIA, "voice_projektpartner_en.wav"),
     "iPhone/WhatsApp-Media", "fremdsprachige Sprachnachricht (EN) an Anna"),
    (os.path.join(ML, "audio_foreign/voice_bekannter_tr.wav"),
     os.path.join(WA_IOS_MEDIA, "voice_bekannter_tr.wav"),
     "iPhone/WhatsApp-Media", "fremdsprachige Sprachnachricht (TR) an Anna"),
    # --- Geraete-Medien: Daniels Samsung ---
    (os.path.join(MM, "images/screenshots/maps_route_screenshot.png"),
     os.path.join(AND_SHOTS, "Screenshot_Route_Waldweg.png"),
     "Samsung/Screenshots", "Routen-Screenshot Richtung Waldweg (Daniel)"),
    # --- Geraete-Medien: Annas iPhone Video (wird in Photos.sqlite registriert) ---
    (os.path.join(MM, "video/noise/home_clip_noise.mp4"),
     os.path.join(IOS_DCIM, "IMG_2075.MP4"),
     "iPhone/DCIM(Video)", "harmloser Heim-Videoclip (Noise) + ZASSET-Eintrag"),
    # --- Tatort-/Ermittlungs-Exhibits -> Polizeiakte ---
    (os.path.join(MM, "images/original/forest_path_01.jpg"),
     os.path.join(POLICE, "tatort_fotos/forest_path_01.jpg"),
     "Polizei/Tatortfotos", "Fundortumgebung Waldweg"),
    (os.path.join(MM, "images/original/forest_path_02.jpg"),
     os.path.join(POLICE, "tatort_fotos/forest_path_02.jpg"),
     "Polizei/Tatortfotos", "Fundortumgebung mit Silhouette"),
    (os.path.join(MM, "images/manipulated/forest_path_02_manipulated.jpg"),
     os.path.join(POLICE, "bildforensik/forest_path_02_manipulated.jpg"),
     "Polizei/Bildforensik", "manipulierte Vergleichsvariante (ELA-Uebung)"),
    (os.path.join(MM, "audio/ambient/forest_ambient_01.wav"),
     os.path.join(POLICE, "tatort_av/forest_ambient_01.wav"),
     "Polizei/Tatort-AV", "Umgebungston Fundort (stuetzt Zeugen-Kfz)"),
    (os.path.join(MM, "video/critical/critical_walkthrough.mp4"),
     os.path.join(POLICE, "tatort_av/critical_walkthrough.mp4"),
     "Polizei/Tatort-AV", "Tatort-Begehung Waldweg"),
]


def move(src, dst):
    if not os.path.exists(src):
        return "fehlt/bereits verschoben"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    return "verschoben"


def move_frames():
    """frames_critical/ wandert mit dem Tatortvideo in die Polizeiakte."""
    src = os.path.join(MM, "video/critical/frames_critical")
    dst = os.path.join(POLICE, "tatort_av/frames_critical")
    if os.path.isdir(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        mapping.append((os.path.relpath(src, ROOT), os.path.relpath(dst, ROOT),
                        "Polizei/Tatort-AV", "extrahierte Frames der Tatort-Begehung"))


def register_video_in_photos(dst_video):
    """Fuegt das Geraete-Video als ZASSET (Video) in Photos.sqlite ein,
    damit DB-Eintrag und Datei konsistent sind. Mount erlaubt kein
    In-Place-SQLite -> ueber /tmp-Kopie arbeiten."""
    if not os.path.exists(PHOTOS_DB) or not os.path.exists(dst_video):
        return False
    tmp = "/tmp/_photos_embed.sqlite"
    for s in ("", "-wal", "-shm"):
        if os.path.exists(PHOTOS_DB + s):
            shutil.copy(PHOTOS_DB + s, tmp + s)
    con = sqlite3.connect(tmp)
    cur = con.cursor()
    # bereits registriert?
    n = cur.execute("SELECT COUNT(*) FROM ZASSET WHERE ZFILENAME=?", ("IMG_2075.MP4",)).fetchone()[0]
    if n == 0:
        pk = (cur.execute("SELECT MAX(Z_PK) FROM ZASSET").fetchone()[0] or 0) + 1
        t = datetime.fromisoformat("2026-01-21T20:15:00+01:00").timestamp() - APPLE
        cur.execute("""INSERT INTO ZASSET
            (Z_PK,Z_ENT,Z_OPT,ZDATECREATED,ZMODIFICATIONDATE,ZADDEDDATE,
             ZLATITUDE,ZLONGITUDE,ZKIND,ZWIDTH,ZHEIGHT,ZFILENAME,ZDIRECTORY,
             ZADDITIONALATTRIBUTES) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pk, 1, 1, t, t, t, 48.7758, 9.1829, 1, 1920, 1080,
             "IMG_2075.MP4", "DCIM/108APPLE", pk))
        cur.execute("""INSERT INTO ZADDITIONALASSETATTRIBUTES
            (Z_PK,Z_ENT,Z_OPT,ZASSET,ZORIGINALFILENAME,ZTIMEZONENAME,ZEXIFTIMESTAMPSTRING)
            VALUES (?,?,?,?,?,?,?)""",
            (pk, 2, 1, pk, "IMG_2075.MP4", "Europe/Berlin", "2026:01:21 20:15:00"))
        con.commit()
    con.close()
    # zurueckspielen
    for s in ("", "-wal", "-shm"):
        if os.path.exists(tmp + s):
            shutil.copy(tmp + s, PHOTOS_DB + s)
            os.remove(tmp + s)
    return True


def write_manifest():
    out = os.path.join(CASE_ROOT, "06_master", "Medien_FS_Mapping.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["quelle (vorher)", "ziel (FS-Ebene)", "kategorie", "begruendung"])
        w.writerows(mapping)
    return out


def main():
    print("Betten Medien in die FS-Ebene ein (Option B)...\n")
    for src, dst, kat, grund in MOVES:
        status = move(src, dst)
        rel_dst = os.path.relpath(dst, ROOT)
        print(f"  [{status:22s}] {kat:22s} -> {rel_dst}")
        if status == "verschoben":
            mapping.append((os.path.relpath(src, ROOT), rel_dst, kat, grund))
            if dst.endswith("IMG_2075.MP4"):
                ok = register_video_in_photos(dst)
                print(f"      Photos.sqlite ZASSET (Video) registriert: {ok}")
    move_frames()
    # .DS_Store aufraeumen
    for d in (MM, ML, os.path.join(IOS, "private/var/mobile/Media/DCIM")):
        for root, _, files in os.walk(d):
            for fn in files:
                if fn == ".DS_Store":
                    try: os.remove(os.path.join(root, fn))
                    except OSError: pass
    out = write_manifest()
    print(f"\nMapping-Manifest: {os.path.relpath(out, ROOT)} ({len(mapping)} Eintraege)")


if __name__ == "__main__":
    main()
