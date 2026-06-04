#!/usr/bin/env python3
# =====================================================================
# gen_audio_piper.py  —  LOKAL: Fall-Sprachnachrichten via Piper TTS
# ---------------------------------------------------------------------
# Erzeugt die Sprach-Audios des Falls mit Piper (OHF-Voice/piper1-gpl)
# und legt sie unter den korrekten Projektpfaden ab. Danach optional
# Resampling auf WAV mono 44,1 kHz (ffmpeg), passend zur Fall-Spezifikation.
#
# NICHT in der Cowork-Sandbox lauffaehig — fuer den lokalen Einsatz.
#
# Voraussetzungen lokal:
#   pip install piper-tts        # OHF-Voice piper1-gpl
#   Stimmen (werden bei Bedarf nach --voices-dir geladen)
#   optional ffmpeg im PATH (Resampling 44,1 kHz mono)
#
# Aufruf (Default-Stimmen, Root aus Skriptpfad):
#   python3 gen_audio_piper.py
# Mit eigenen Stimmen/Pfaden:
#   python3 gen_audio_piper.py --de-female de_DE-kerstin-low \
#       --en-male en_US-ryan-medium --tr-male tr_TR-fahrettin-medium
#   # oder volle .onnx-Pfade statt Namen uebergeben
#
# Hinweis: Das Wald-Umgebungsgeraeusch (forest_ambient_01.wav) ist KEIN
# TTS -> bewusst NICHT enthalten (Sound-FX/Freesound, siehe Anleitung).
# =====================================================================
import argparse
import os
import shutil
import subprocess
import sys

_DEFAULT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# (relativer Zielpfad, sprach-/stimm-key, text)
JOBS = [
    ("07_multimedia/audio/voicemail/voicemail_anna_office_de.wav", "de_female",
     "Hallo Anna, hier ist das Büro. Du bist heute Morgen nicht da und auch nicht "
     "erreichbar. Bitte melde dich kurz, sobald du das hörst. Danke."),
    ("07_multimedia/audio/whatsapp_voice/voice_lena_de.wav", "de_female",
     "Hey, alles gut bei dir? Du klangst neulich irgendwie gestresst. Melde dich, "
     "wenn du reden willst, ich bin für dich da, ja?"),
    ("08_multilingual/audio_foreign/voice_projektpartner_en.wav", "en_male",
     "Hi Anna, can you send the updated spreadsheet before noon? We need the final "
     "version for the meeting. Thanks."),
    ("08_multilingual/audio_foreign/voice_bekannter_tr.wav", "tr_male",
     "Merhaba, toplantıyı yarına alabilir miyiz? Bu sabah gelmem biraz zor."),
]


def resolve_voice(name_or_path, voices_dir):
    """Gibt einen .onnx-Pfad zurueck. Ist 'name_or_path' bereits eine
    existierende .onnx-Datei, wird sie genutzt; sonst als Voice-NAME
    behandelt und (best effort) nach voices_dir geladen (piper1-gpl)."""
    def complete(onnx):
        # Piper benoetigt sowohl die .onnx als auch die Config .onnx.json
        return os.path.exists(onnx) and os.path.exists(onnx + ".json")

    if name_or_path.endswith(".onnx") and os.path.exists(name_or_path):
        if not complete(name_or_path):
            print(f"    WARN: Config fehlt: {name_or_path}.json")
        return name_or_path
    os.makedirs(voices_dir, exist_ok=True)
    cand = os.path.join(voices_dir, name_or_path + ".onnx")
    if complete(cand):
        print(f"    '{name_or_path}' bereits vorhanden (onnx + json).")
        return cand
    if os.path.exists(cand):
        print(f"    '{name_or_path}': .onnx vorhanden, aber .json fehlt -> erneuter Download.")

    print(f"    Lade Stimme '{name_or_path}' nach {voices_dir} ...")
    # piper1-gpl nutzt --download-dir (NICHT --data-dir). Mehrere Varianten
    # durchprobieren, da sich die CLI zwischen Versionen unterscheidet.
    variants = [
        [sys.executable, "-m", "piper.download_voices", name_or_path, "--download-dir", voices_dir],
        [sys.executable, "-m", "piper.download_voices", "--download-dir", voices_dir, name_or_path],
        ["python3", "-m", "piper.download_voices", name_or_path, "--download-dir", voices_dir],
    ]
    last_err = ""
    for cmd in variants:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0 and complete(cand):
                print("    OK heruntergeladen (onnx + json).")
                return cand
            last_err = (r.stderr or r.stdout or "").strip()
        except FileNotFoundError as e:
            last_err = str(e)
    print("    WARN: Download fehlgeschlagen. Original-Fehlermeldung:")
    for line in (last_err or "(keine Ausgabe)").splitlines()[-6:]:
        print("      | " + line)
    print(f"    -> Manuell: python3 -m piper.download_voices {name_or_path} --download-dir {voices_dir}")
    print(f"       oder Stimme als .onnx ablegen und Pfad uebergeben (--{'?'}).")
    return cand


def piper_say(text, model_path, out_wav):
    """Synthese via Piper-CLI (stdin->wav). Faellt auf 'python -m piper' zurueck."""
    cmds = [["piper", "-m", model_path, "-f", out_wav],
            [sys.executable, "-m", "piper", "-m", model_path, "-f", out_wav]]
    last = None
    for cmd in cmds:
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, capture_output=True)
            return True
        except FileNotFoundError as e:
            last = e; continue
        except subprocess.CalledProcessError as e:
            last = e; break
    print(f"    FEHLER Piper: {getattr(last,'stderr',last)}")
    return False


def to_wav_44k_mono(src, dst):
    """Resample auf 44,1 kHz mono PCM16 (Fall-Spezifikation), falls ffmpeg da."""
    if not shutil.which("ffmpeg"):
        if src != dst:
            shutil.move(src, dst)
        print("    (ffmpeg fehlt -> Piper-WAV unveraendert, 22,05 kHz)")
        return
    subprocess.run(["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", "44100",
                    "-c:a", "pcm_s16le", dst], check=True, capture_output=True)
    if os.path.exists(src) and src != dst:
        os.remove(src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=_DEFAULT_ROOT)
    ap.add_argument("--voices-dir", default=os.path.join(_DEFAULT_ROOT, "09_build", "piper_voices"))
    ap.add_argument("--de-female", default="de_DE-kerstin-low")
    ap.add_argument("--en-male", default="en_US-ryan-medium")
    ap.add_argument("--tr-male", default="tr_TR-dfki-medium")
    args = ap.parse_args()

    def is_project_root(p):
        return os.path.isfile(os.path.join(p, "09_build", "case_master.yaml")) and \
               os.path.isdir(os.path.join(p, "06_master"))
    root = os.path.abspath(args.root)
    if not is_project_root(root) and is_project_root(_DEFAULT_ROOT):
        print(f"Hinweis: '{root}' ist nicht das Projektverzeichnis — verwende {_DEFAULT_ROOT}")
        root = _DEFAULT_ROOT
    args.root = root
    print(f"Zielverzeichnis (root): {root}")

    voice_args = {"de_female": args.de_female, "en_male": args.en_male, "tr_male": args.tr_male}
    print("Stimmen aufloesen ...")
    voices = {k: resolve_voice(v, args.voices_dir) for k, v in voice_args.items()}

    for rel, key, text in JOBS:
        out = os.path.join(args.root, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        model = voices[key]
        print(f"  -> {rel}  [{key}: {os.path.basename(model)}]")
        if not os.path.exists(model):
            print(f"     UEBERSPRUNGEN: Stimmmodell fehlt ({model})")
            continue
        tmp = out + ".raw.wav"
        if piper_say(text, model, tmp):
            to_wav_44k_mono(tmp, out)
            print(f"     gespeichert: {os.path.basename(out)}")

    print("\nHinweis: forest_ambient_01.wav separat erzeugen (Sound-FX/Freesound).")
    print("Danach Gegencheck:  python3 09_build/generators/run_all.py")


if __name__ == "__main__":
    main()
