#!/usr/bin/env python3
# =====================================================================
# gen_images_swarmui.py  —  LOKAL auszufuehren (auf dem Rechner mit SwarmUI)
# ---------------------------------------------------------------------
# Generiert die Operation-Waldweg-Bilder ueber die lokale SwarmUI-API
# (Flux) und speichert sie unter den korrekten Projektpfaden.
#
# NICHT in der Cowork-Sandbox lauffaehig (kein Zugriff auf deinen
# localhost) — bewusst fuer den lokalen Einsatz gedacht.
#
# Voraussetzungen lokal:
#   - SwarmUI laeuft (Standard http://localhost:7801)
#   - Modell geladen (z.B. flux-2-klein-9b)
#   - Python 3 mit 'requests'  (pip install requests)
#   - optional 'exiftool' im PATH fuer Fall-Metadaten
#
# Aufruf (im Projekt-Root Operation_Waldweg/ oder mit --root):
#   python3 gen_images_swarmui.py --url http://localhost:7801 \
#           --model flux-2-klein-9b --root /Pfad/zu/Operation_Waldweg
# =====================================================================
import argparse
import base64
import os
import subprocess
import sys

try:
    import requests
except ImportError:
    print("Bitte 'requests' installieren: pip install requests")
    sys.exit(1)

try:
    from PIL import Image
    import io
    _HAVE_PIL = True
except ImportError:
    _HAVE_PIL = False

# Projekt-Root (Operation_Waldweg/) relativ zum Skript: generators -> 09_build -> ROOT
_DEFAULT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# (relativer Zielpfad, prompt, breite, hoehe, optional exif: (datetime, lat, lon))
JOBS = [
    ("07_multimedia/images/original/forest_path_01.jpg",
     "Photorealistic amateur smartphone photo of a quiet forest path and gravel "
     "parking area at the edge of a German mixed forest on an overcast winter "
     "morning, bare trees, damp ground, soft grey light, no people, slightly "
     "tilted handheld framing, natural muted colors",
     1024, 768, ("2026:01:25 08:05:00", None, None)),

    ("07_multimedia/images/original/forest_path_02.jpg",
     "Photorealistic amateur smartphone photo of the same German forest path on an "
     "overcast winter morning, a small indistinct dark human-like silhouette far in "
     "the background near the tree line, slightly out of focus, no recognizable face, "
     "dim flat lighting, handheld",
     1024, 768, ("2026:01:25 08:07:00", None, None)),

    ("07_multimedia/images/manipulated/forest_path_02_manipulated.jpg",
     "The same German forest path photo, overcast winter morning, with a small dark "
     "estate car (Kombi) faintly added near the parking area and the distant "
     "silhouette removed; keep lighting consistent, subtle slightly inconsistent "
     "shadows (for image-forensics training)",
     1024, 768, ("2026:01:25 08:07:30", None, None)),

    ("07_multimedia/images/screenshots/maps_route_screenshot.png",
     "Realistic smartphone screenshot of a generic maps navigation app showing a "
     "driving route from a residential area to a forest parking spot at the city "
     "edge, highlighted route line, ETA about 18 minutes, fictional German street "
     "names, clean modern UI, portrait phone aspect",
     768, 1024, None),
]

# Optionale iPhone-Fotos passend zu Photos.sqlite.
# (zielname, dcim_ordner, format, datetime, lat, lon, prompt)
PHOTO_JOBS = [
    ("IMG_2012", "107APPLE", "heic", "2026:01:11 15:05:40", 48.7702, 9.1955,
     "amateur smartphone photo of kids indoor sports training, motion blur, gym hall, candid burst shot"),
    ("IMG_2013", "107APPLE", "heic", "2026:01:11 15:05:43", 48.7702, 9.1955,
     "amateur smartphone photo of kids indoor sports training, motion, gym hall, candid burst shot"),
    ("IMG_2014", "107APPLE", "heic", "2026:01:11 15:05:46", 48.7702, 9.1955,
     "amateur smartphone photo of kids indoor sports training, gym hall, candid burst shot"),
    ("IMG_2041", "108APPLE", "heic", "2026:01:18 16:30:12", 48.7689, 9.1740,
     "candid amateur phone photo of a youth gym training session, indoor, natural light"),
    ("IMG_2042", "108APPLE", "heic", "2026:01:18 16:31:05", 48.7689, 9.1740,
     "candid amateur phone photo of a youth gym training session, indoor"),
    ("IMG_2027", "108APPLE", "heic", "2026:01:13 13:20:11", 48.7831, 9.1817,
     "top-down amateur phone photo of a lunch bowl on an office desk"),
    ("IMG_2055", "108APPLE", "heic", "2026:01:20 12:42:33", 48.7831, 9.1817,
     "top-down amateur phone photo of a takeaway lunch on an office desk, keyboard at edge"),
    ("IMG_2033", "108APPLE", "heic", "2026:01:15 19:48:02", 48.7758, 9.1829,
     "amateur phone photo of a home dinner table, warm indoor light, cozy"),
    ("IMG_2063", "108APPLE", "heic", "2026:01:23 08:31:17", 48.7689, 9.1740,
     "amateur gym mirror selfie, morning, no recognizable face, phone partly covering face"),
    ("IMG_2068", "108APPLE", "heic", "2026:01:24 18:42:50", 48.7770, 9.1880,
     "casual amateur phone photo of a supermarket shelf in the evening"),
    ("IMG_2061", "108APPLE", "png", "2026:01:22 09:15:00", None, None,
     "smartphone screenshot of a fitness studio weekly class plan, German text, clean app UI, portrait"),
    ("IMG_2039", "108APPLE", "png", "2026:01:17 10:02:55", None, None,
     "smartphone screenshot of a cooking recipe page, German text, ingredient list, portrait"),
]

NEGATIVE = "watermark, text artifacts, logo, deformed, lowres, oversharpened, people faces in focus"


def to_heic(src_png, dst_heic):
    """Konvertiert PNG/JPG -> HEIC. Versucht sips (macOS), dann ImageMagick,
    dann heif-enc. Faellt sonst auf .jpg zurueck (mit Warnung)."""
    import shutil
    if shutil.which("sips"):
        subprocess.run(["sips", "-s", "format", "heic", src_png, "--out", dst_heic],
                       check=True, capture_output=True)
        return dst_heic
    for tool in (["magick", src_png, dst_heic], ["convert", src_png, dst_heic]):
        if shutil.which(tool[0]):
            subprocess.run(tool, check=True, capture_output=True)
            return dst_heic
    if shutil.which("heif-enc"):
        subprocess.run(["heif-enc", src_png, "-o", dst_heic], check=True, capture_output=True)
        return dst_heic
    # Fallback: als JPG behalten
    alt = dst_heic[:-5] + ".jpg"
    shutil.copy(src_png, alt)
    print(f"      WARN: kein HEIC-Konverter gefunden -> {os.path.basename(alt)} "
          f"(dann Photos.sqlite-Dateinamen auf .jpg anpassen)")
    return alt


def get_session(url):
    r = requests.post(f"{url}/API/GetNewSession", json={}, timeout=15)
    r.raise_for_status()
    return r.json()["session_id"]


def generate(url, session_id, model, prompt, w, h, steps, cfg):
    payload = {
        "session_id": session_id, "images": 1, "prompt": prompt,
        "negativeprompt": NEGATIVE, "model": model,
        "width": w, "height": h, "steps": steps, "cfgscale": cfg,
    }
    r = requests.post(f"{url}/API/GenerateText2Image", json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    imgs = data.get("images") or []
    if not imgs:
        raise RuntimeError(f"Keine Bilddaten zurueck: {data}")
    img = imgs[0]
    if img.startswith("data:"):
        return base64.b64decode(img.split(",", 1)[1])
    # sonst relativer Pfad -> herunterladen
    g = requests.get(f"{url}/{img.lstrip('/')}", timeout=60)
    g.raise_for_status()
    return g.content


def save_as(blob, target):
    """Speichert die rohen Bilddaten im Format, das die Zieldatei-Endung
    vorgibt (SwarmUI liefert meist PNG -> hier ggf. nach JPG konvertieren),
    damit Endung und Inhalt zusammenpassen (sonst scheitert exiftool)."""
    ext = os.path.splitext(target)[1].lower()
    if _HAVE_PIL:
        im = Image.open(io.BytesIO(blob))
        if ext in (".jpg", ".jpeg"):
            im.convert("RGB").save(target, "JPEG", quality=90)
        elif ext == ".png":
            im.save(target, "PNG")
        else:  # andere Endung -> Originalbytes
            with open(target, "wb") as f:
                f.write(blob)
        return len(blob)
    # ohne Pillow: Bytes schreiben, vor Mismatch warnen
    with open(target, "wb") as f:
        f.write(blob)
    if blob[:8] == b"\x89PNG\r\n\x1a\n" and ext in (".jpg", ".jpeg"):
        print("      WARN: PNG-Daten in .jpg gespeichert — Pillow installieren "
              "(pip install pillow) fuer korrekte Konvertierung.")
    return len(blob)


def set_exif(path, dt, lat, lon):
    if not dt:
        return
    args = ["exiftool", "-overwrite_original",
            f"-DateTimeOriginal={dt}", f"-CreateDate={dt}"]
    if lat is not None and lon is not None:
        args += [f"-GPSLatitude={lat}", "-GPSLatitudeRef=N",
                 f"-GPSLongitude={lon}", "-GPSLongitudeRef=E"]
    args.append(path)
    try:
        subprocess.run(args, check=True, capture_output=True)
        # Dateisystem-Zeit angleichen
        ts = dt.replace(":", "").replace(" ", "")[:12] + "." + dt[-2:]
        subprocess.run(["touch", "-t", ts, path], check=False)
        print(f"      EXIF gesetzt: {dt}")
    except FileNotFoundError:
        print("      (exiftool nicht gefunden — Metadaten manuell setzen)")
    except subprocess.CalledProcessError as e:
        print(f"      exiftool-Fehler: {e.stderr.decode()[:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:7801")
    ap.add_argument("--model", default="flux-2-klein-9b")
    ap.add_argument("--root", default=_DEFAULT_ROOT,
                    help="Pfad zu Operation_Waldweg/ (Default: aus Skriptpfad abgeleitet)")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--cfg", type=float, default=1.5, help="Flux: oft 1.0-2.0")
    ap.add_argument("--with-photos", action="store_true",
                    help="zusaetzlich die iPhone-Fotos (Photos.sqlite) erzeugen + HEIC")
    args = ap.parse_args()

    # Root robust aufloesen: muss das Projektverzeichnis sein (enthaelt
    # 07_multimedia/01_ios_full_fs). Sonst (z.B. bei "--root .") automatisch
    # auf den aus dem Skriptpfad abgeleiteten Projekt-Root korrigieren.
    # Eindeutiger Marker des Projekt-Roots: 09_build/case_master.yaml + 06_master.
    # (Der generators-Ordner kann das nie versehentlich erfuellen, selbst wenn
    #  ein frueherer Fehllauf dort 07_multimedia/ angelegt hat.)
    def is_project_root(p):
        return os.path.isfile(os.path.join(p, "09_build", "case_master.yaml")) and \
               os.path.isdir(os.path.join(p, "06_master"))
    root = os.path.abspath(args.root)
    if not is_project_root(root):
        if is_project_root(_DEFAULT_ROOT):
            print(f"Hinweis: '{root}' ist nicht das Projektverzeichnis — "
                  f"verwende stattdessen {_DEFAULT_ROOT}")
            root = _DEFAULT_ROOT
        else:
            print(f"WARN: Projektverzeichnis (mit 09_build/case_master.yaml) "
                  f"nicht gefunden. Bitte --root auf Operation_Waldweg/ setzen.")
    args.root = root
    print(f"Zielverzeichnis (root): {root}")

    print(f"SwarmUI: {args.url} · Modell: {args.model}")
    sid = get_session(args.url)
    print(f"Session: {sid}\n")

    for rel, prompt, w, h, exif in JOBS:
        out = os.path.join(args.root, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        print(f"  -> {rel}  ({w}x{h})")
        try:
            blob = generate(args.url, sid, args.model, prompt, w, h, args.steps, args.cfg)
            n = save_as(blob, out)
            print(f"      gespeichert ({n} bytes, {os.path.splitext(out)[1]})")
            if exif:
                set_exif(out, *exif)
        except Exception as e:
            print(f"      FEHLER: {e}")

    if args.with_photos:
        print("\n--- iPhone-Fotos (Photos.sqlite) ---")
        dcim = os.path.join(args.root, "01_ios_full_fs/private/var/mobile/Media/DCIM")
        for name, folder, fmt, dt, lat, lon, prompt in PHOTO_JOBS:
            d = os.path.join(dcim, folder)
            os.makedirs(d, exist_ok=True)
            w, h = (768, 1024) if fmt == "png" else (1024, 768)
            print(f"  -> {folder}/{name}.{fmt}")
            try:
                blob = generate(args.url, sid, args.model, prompt, w, h, args.steps, args.cfg)
                tmp = os.path.join(d, name + ".png")
                with open(tmp, "wb") as f:
                    f.write(blob)
                if fmt == "heic":
                    final = to_heic(tmp, os.path.join(d, name + ".HEIC"))
                    if os.path.exists(tmp) and final != tmp:
                        os.remove(tmp)
                else:  # png-Screenshot
                    final = os.path.join(d, name + ".PNG")
                    os.replace(tmp, final)
                print(f"      gespeichert: {os.path.basename(final)}")
                set_exif(final, dt, lat, lon)
            except Exception as e:
                print(f"      FEHLER: {e}")

    print("\nFertig. Danach Gegencheck:  python3 09_build/generators/run_all.py")


if __name__ == "__main__":
    main()
