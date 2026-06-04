#!/usr/bin/env python3
# =====================================================================
# run_all.py  —  Gesamt-Validierungslauf (Tag 7)
# ---------------------------------------------------------------------
# Fuehrt alle Format-Gates und die Loesbarkeitspruefung in einem Lauf
# gegen die im Workspace persistierten Geraete-Artefakte aus und gibt
# einen Gesamtstatus aus. Reproduzierbare Abnahme des kompletten Builds.
# =====================================================================
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OW = os.path.normpath(os.path.join(HERE, '..', '..'))   # .../Operation_Waldweg

env = dict(os.environ)
env['WALDWEG_IOS_FS'] = os.path.join(OW, '01_ios_full_fs')
env['WALDWEG_AND_FS'] = os.path.join(OW, '02_android_full_fs')
env['WALDWEG_WIN_FS'] = os.path.join(OW, '03_windows_triage')
env['WALDWEG_OW'] = OW

env['WALDWEG_CLOUD'] = os.path.join(OW, '04_cloud_exports')

STEPS = [
    ("BIOME-Streams (gegen biome_core.py)", "gen_biome.py"),
    ("Cloud-Exporte (PI#5)",                 "gen_cloud.py"),
    ("iOS-Extra (Safari/Voicemail/CallHistory/Snapshots)", "gen_ios_extra.py"),
    ("iOS-Artefakte (iLEAPP-Gate)",          "validate_ios.py"),
    ("Android-Extra (usagestats/SHealth/Maps/Accounts/wa.db)", "gen_android_extra.py"),
    ("Android-Artefakte (ALEAPP-Gate)",      "validate_android.py"),
    ("Windows-Hives (SAM/SYSTEM/SOFTWARE/NTUSER/Amcache/UsrClass)", "gen_win_hives.py"),
    ("Windows-Datei-Artefakte (RecycleBin/setupapi/Tasks)", "gen_win_artifacts.py"),
    ("Windows-Browser-Tiefe (Downloads/Bookmarks/WebData/Login)", "gen_win_browser.py"),
    ("Windows-Extra (PowerShell/Notifications)", "gen_win_extra.py"),
    ("Windows-LNK-Shortcuts (Recent)",       "gen_win_lnk.py"),
    ("Windows-EVTX (Security/System)",       "gen_win_evtx.py"),
    ("Windows-Artefakte (regipy/Edge/Reg)",  "validate_windows.py"),
    ("App-Sandbox-Skelette (iOS+Android)",   "gen_app_skeletons.py"),
    ("App-Sandbox-Gate",                     "validate_apps.py"),
    ("Loesbarkeit & Konsistenz",             "verify_solution.py"),
]


def main():
    print("=" * 64)
    print("OPERATION WALDWEG — GESAMT-VALIDIERUNG")
    print("=" * 64)
    summary = []
    for label, script in STEPS:
        path = os.path.join(HERE, script)
        print(f"\n----- {label}  ({script}) -----")
        r = subprocess.run([sys.executable, path], env=env)
        summary.append((label, r.returncode == 0))

    print("\n" + "=" * 64)
    print("ZUSAMMENFASSUNG")
    print("=" * 64)
    allok = True
    for label, ok in summary:
        print(f"  [{'OK' if ok else 'FEHLER'}]  {label}")
        allok = allok and ok
    print("-" * 64)
    print("GESAMT:", "ALLE GATES BESTANDEN ✓" if allok else "MIND. 1 GATE FEHLGESCHLAGEN ✗")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
