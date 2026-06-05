#!/usr/bin/env python3
# =====================================================================
# gen_win_artifacts.py  —  weitere Standard-Windows-Artefakte (Dateien)
# ---------------------------------------------------------------------
# Ergaenzt das Windows-FS um datei-basierte Artefakte gemaess dem
# Artefakt-Katalog (Windows_Artefakte.docx):
#   * Recycle Bin  $I/$R   (valides $I-v2-Format -> z.B. RBCmd)
#   * setupapi.dev.log     (USB-Geraeteinstallation, Text)
#   * Scheduled Tasks XML  (C:\Windows\System32\Tasks)
#   * Zone.Identifier      (Herkunft heruntergeladener Dateien; als
#                           Sidecar, da ADS auf ext4/APFS nicht moeglich)
#   * Prefetch             (NAME-HASH.pf — PLATZHALTER, kein valides SCCA)
# Schreibt ein Manifest mit Relevanz-Einordnung.
# =====================================================================
import os
import csv
import struct
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
import sys
sys.path.insert(0, HERE)
import caseforge_rng as cfr
WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
C = os.path.join(WIN, "C")
SID = cfr.win_sid()
COMPUTER = cfr.win_computer_name()
manifest = []


def ensure(d): os.makedirs(d, exist_ok=True)


def reg(path, relevanz, beschr):
    manifest.append((os.path.relpath(path, ROOT), relevanz, beschr))


def filetime(iso):
    dt = datetime.fromisoformat(iso)
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return struct.pack("<Q", int((dt - epoch).total_seconds() * 10_000_000))


# ---------------- Recycle Bin ($I v2 + $R) ----------------
def recycle_bin():
    d = os.path.join(C, "$Recycle.Bin", SID)
    ensure(d)
    orig = r"C:\Users\Daniel\Documents\Finanzen\Schuldenaufstellung_Jan.xlsx"
    content = b"PK\x03\x04 (synthetischer geloeschter XLSX-Inhalt) Schuldenaufstellung Januar"
    name = orig.encode("utf-16-le") + b"\x00\x00"
    i = struct.pack("<Q", 2) + struct.pack("<Q", len(content)) + filetime("2026-01-25T08:10:00+00:00")
    i += struct.pack("<I", len(name) // 2) + name
    with open(os.path.join(d, "$IA1B2C3.xlsx"), "wb") as f:
        f.write(i)
    with open(os.path.join(d, "$RA1B2C3.xlsx"), "wb") as f:
        f.write(content)
    reg(os.path.join(d, "$IA1B2C3.xlsx"), "context",
        "Papierkorb: geloeschte 'Schuldenaufstellung_Jan.xlsx' (Loeschzeit 25.01 09:10 CET)")
    reg(os.path.join(d, "$RA1B2C3.xlsx"), "context", "Papierkorb: Inhalt der geloeschten Datei")


# ---------------- setupapi.dev.log ----------------
def setupapi():
    p = os.path.join(C, "Windows/INF/setupapi.dev.log")
    ensure(os.path.dirname(p))
    txt = (
        ">>>  [Device Install (Hardware initiated) - "
        "USBSTOR\\Disk&Ven_SanDisk&Prod_Cruzer_Blade&Rev_1.00\\4C530001260102117384&0]\n"
        ">>>  Section start 2026/01/24 23:50:11.482\n"
        "     dvi: {Build Driver List} 23:50:11.490\n"
        "     dvi: Searching for hardware ID(s): usbstor\\disksandisk_cruzer_blade____1.00\n"
        "     sto: {Setup Import Driver Package - disk.inf}\n"
        "     dvi: Device install status=0x00000000 (SanDisk Cruzer Blade USB Device)\n"
        "<<<  Section end 2026/01/24 23:50:13.114\n"
        "<<<  [Exit status: SUCCESS]\n")
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)
    reg(p, "context", "USB-Erstinstallation SanDisk Cruzer 24.01 23:50 (deckt sich mit USBSTOR/MountedDevices)")


# ---------------- Scheduled Tasks (XML) ----------------
TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{created}</Date>
    <Author>{author}</Author>
    <Description>{desc}</Description>
  </RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>{start}</StartBoundary>
    <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Actions><Exec><Command>{cmd}</Command></Exec></Actions>
</Task>
"""


def scheduled_tasks():
    base = os.path.join(C, "Windows/System32/Tasks")
    ensure(os.path.join(base, "Microsoft/EdgeUpdate"))
    with open(os.path.join(base, "Microsoft/EdgeUpdate/MicrosoftEdgeUpdateTaskMachineCore"), "w", encoding="utf-16") as f:
        f.write(TASK_XML.format(created="2025-09-10T12:00:00", author="Microsoft Corporation",
                                desc="Hält Microsoft Edge aktuell.", start="2025-09-10T06:00:00",
                                cmd=r"C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe"))
    reg(os.path.join(base, "Microsoft/EdgeUpdate/MicrosoftEdgeUpdateTaskMachineCore"), "noise", "Edge-Update-Task")
    with open(os.path.join(base, "BackupFinanzen"), "w", encoding="utf-16") as f:
        f.write(TASK_XML.format(created="2026-01-20T21:00:00", author=f"{COMPUTER}\\Daniel",
                                desc="Tägliche Sicherung Finanzordner auf USB.", start="2026-01-20T22:00:00",
                                cmd=r"C:\Windows\System32\robocopy.exe C:\Users\Daniel\Documents\Finanzen E:\Backup /MIR"))
    reg(os.path.join(base, "BackupFinanzen"), "context",
        "Geplanter Task 'BackupFinanzen' -> Sicherung Finanzordner auf USB (E:) — passt zu USB-Nutzung")


# ---------------- Zone.Identifier (Sidecar) ----------------
def zone_identifier():
    targets = [
        ("C/Users/Daniel/Downloads/Bedienungsanleitung_Router.pdf", "https://example-isp.de/router/manual.pdf"),
        ("C/Users/Daniel/Downloads/kontoauszug_export.csv", "https://onlinebanking.sparkasse.de/export"),
    ]
    for rel, host in targets:
        src = os.path.join(WIN, rel)
        sidecar = src + ".Zone.Identifier"   # echtes NTFS: <datei>:Zone.Identifier (ADS)
        ensure(os.path.dirname(sidecar))
        with open(sidecar, "w", encoding="utf-8") as f:
            f.write("[ZoneTransfer]\nZoneId=3\nReferrerUrl=%s\nHostUrl=%s\n" % (host, host))
        reg(sidecar, "context", "Zone.Identifier (ZoneId=3=Internet) -> Herkunftsnachweis Download")


# ---------------- Prefetch (Platzhalter) ----------------
def prefetch():
    d = os.path.join(C, "Windows/Prefetch")
    ensure(d)
    for name in ["MSEDGE.EXE-1B2D3C4E.pf", "EXCEL.EXE-A1B2C3D4.pf", "RUFUS.EXE-9F8E7D6C.pf",
                 "ROBOCOPY.EXE-5A6B7C8D.pf"]:
        p = os.path.join(d, name)
        with open(p, "wb") as f:
            f.write(b"MAM\x04" + b"\x00" * 60)  # Platzhalter (kein valides SCCA)
        reg(p, "noise", "Prefetch-Platzhalter (Dateiname=Ausfuehrungshinweis; kein valides SCCA)")


def write_manifest():
    out = os.path.join(ROOT, "06_master", "Windows_Artefakte_Manifest.csv")
    ensure(os.path.dirname(out))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["pfad", "relevanz", "beschreibung"]); w.writerows(sorted(manifest))
    return out


def main():
    recycle_bin(); setupapi(); scheduled_tasks(); zone_identifier(); prefetch()
    out = write_manifest()
    print(f"Windows-Datei-Artefakte erzeugt: {len(manifest)} Eintraege")
    for p, r, b in sorted(manifest):
        print(f"  [{r:7s}] {p}")
    print(f"Manifest: {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
