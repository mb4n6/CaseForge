#!/usr/bin/env python3
# =====================================================================
# gen_win_lnk.py  —  Windows-Shortcuts (.lnk) in Recent\
# ---------------------------------------------------------------------
# Erzeugt valide Shell-Link-Dateien (MS-SHLLINK) mit Header-Zeitstempeln
# und LinkInfo (VolumeID + LocalBasePath). Parsebar mit LECmd/lnkparse.
# Fallbezug: Verweise auf die (geloeschte) Schuldenaufstellung, den
# Finanzen-Ordner und das USB-Laufwerk E:\Backup -> Datei-/USB-Nutzung.
# =====================================================================
import os
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_master_io as cmio
import struct
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
WUSER = cmio.windows_username()   # Windows-Profilordner aus Fall-Besitzer
RECENT = os.path.join(WIN, f"C/Users/{WUSER}/AppData/Roaming/Microsoft/Windows/Recent")
CLSID = bytes.fromhex("0114020000000000c000000000000046")  # 00021401-0000-0000-C000-000000000046


def ft(iso):
    dt = datetime.fromisoformat(iso)
    return struct.pack("<Q", int((dt - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10_000_000))


def make_lnk(local_path, is_dir, drive_type, serial, vol_label, ctime, atime, wtime, size=0):
    flags = 0x00000002          # HasLinkInfo
    attr = 0x10 if is_dir else 0x20
    header = struct.pack("<I", 0x4C) + CLSID + struct.pack("<I", flags) + struct.pack("<I", attr)
    header += ft(ctime) + ft(atime) + ft(wtime)
    header += struct.pack("<I", size) + struct.pack("<i", 0) + struct.pack("<i", 1)  # filesize, icon, showcmd
    header += struct.pack("<H", 0) + b"\x00" * 10                                    # hotkey + reserved
    # ---- LinkInfo ----
    label = vol_label.encode("ascii") + b"\x00"
    path = local_path.encode("ascii") + b"\x00"
    volid_size = 16 + len(label)
    volid = struct.pack("<IIII", volid_size, drive_type, serial, 16) + label
    header_size = 0x1C
    volid_off = header_size
    localpath_off = header_size + len(volid)
    suffix = b"\x00"
    suffix_off = localpath_off + len(path)
    li_size = suffix_off + len(suffix)
    linkinfo = struct.pack("<IIIIIII", li_size, header_size, 0x00000001,
                           volid_off, localpath_off, 0, suffix_off) + volid + path + suffix
    return header + linkinfo + b"\x00\x00\x00\x00"   # TerminalBlock


LNKS = [
    ("Schuldenaufstellung_Jan.xlsx.lnk", rf"C:\Users\{WUSER}\Documents\Finanzen\Schuldenaufstellung_Jan.xlsx",
     False, 3, 0x9C5E1A2B, "OS", "2026-01-20T21:00:00+01:00", "2026-01-25T09:05:00+01:00", "2026-01-24T22:15:00+01:00", 18342,
     "context", "LNK auf die spaeter geloeschte Schuldenaufstellung -> belegt frueheres Vorhandensein"),
    ("Finanzen.lnk", rf"C:\Users\{WUSER}\Documents\Finanzen", True, 3, 0x9C5E1A2B, "OS",
     "2025-09-10T10:00:00+01:00", "2026-01-25T09:05:00+01:00", "2026-01-25T09:05:00+01:00", 0,
     "context", "LNK auf den Finanzen-Ordner"),
    ("Backup (E).lnk", r"E:\Backup", True, 2, 0x4C530001, "CRUZER", "2026-01-24T22:50:00+01:00",
     "2026-01-25T07:10:00+01:00", "2026-01-25T07:10:00+01:00", 0,
     "context", "LNK auf USB E:\\Backup (DriveType=removable, Serial) -> USB-Nutzung"),
    ("Kreditantrag_Sofort.lnk", rf"C:\Users\{WUSER}\Downloads\Kreditantrag_Sofort.pdf", False, 3,
     0x9C5E1A2B, "OS", "2026-01-24T22:33:00+01:00", "2026-01-24T22:34:00+01:00", "2026-01-24T22:33:00+01:00", 248123,
     "noise", "LNK auf heruntergeladenen Kreditantrag"),
]


def main():
    os.makedirs(RECENT, exist_ok=True)
    manifest = []
    for fn, path, is_dir, dtype, serial, label, ct, at, wt, size, rel, desc in LNKS:
        data = make_lnk(path, is_dir, dtype, serial, label, ct, at, wt, size)
        out = os.path.join(RECENT, fn)
        with open(out, "wb") as f:
            f.write(data)
        manifest.append((os.path.relpath(out, ROOT), rel, desc, len(data)))
        print(f"  [{rel:7s}] {fn}  ({len(data)} B) -> {path}")

    # Struktur-Selbstcheck: CLSID + LocalBasePath ruecklesen
    print("\nSelbstcheck:")
    for fn, path, *_ in [(l[0], l[1]) + tuple(l[2:]) for l in LNKS]:
        d = open(os.path.join(RECENT, fn), "rb").read()
        hdr_ok = d[0:4] == b"\x4C\x00\x00\x00" and d[4:20] == CLSID
        has_path = path.encode("ascii") in d
        print(f"  {fn}: header={hdr_ok} pfad_im_LinkInfo={has_path}")
    return manifest


if __name__ == "__main__":
    main()
