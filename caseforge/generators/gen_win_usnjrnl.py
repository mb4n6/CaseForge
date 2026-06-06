#!/usr/bin/env python3
# =====================================================================
# gen_win_usnjrnl.py  —  NTFS $UsnJrnl:$J (USN_RECORD_V2)
# ---------------------------------------------------------------------
# Schreibt den USN-Change-Journal-Datenstrom als Folge von
# USN_RECORD_V2-Eintraegen (Datei-Erstellung/-Aenderung/-Loeschung/-Umbenennung).
# Da Alternate Data Streams auf ext4/APFS nicht darstellbar sind, liegt der
# $J-Strom als eigene Datei unter C/$Extend/$UsnJrnl_$J (so wie ihn MFTECmd
# nach der Extraktion erwartet). Parsebar mit MFTECmd -f / UsnJrnl2Csv.
# Nur wenn das Windows-Geraet das Profil-Flag 'usnjrnl' traegt.
# =====================================================================
import os
import sys
import struct
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
sys.path.insert(0, HERE)
import case_master_io as cmio

WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
JPATH = os.path.join(WIN, "C/$Extend/$UsnJrnl_$J")

# USN-Reason-Flags
R_DATA_OVERWRITE = 0x00000001
R_FILE_CREATE = 0x00000100
R_FILE_DELETE = 0x00000200
R_RENAME_OLD = 0x00001000
R_RENAME_NEW = 0x00002000
R_CLOSE = 0x80000000


def filetime(iso):
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int((dt - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10_000_000)


def ref(rec, seq=1):
    return (seq << 48) | rec


# (file_ref, parent_ref, reason, attrs, name, iso)
EVENTS = [
    (ref(40), ref(33), R_FILE_CREATE, 0x20, "Schuldenaufstellung_Jan.xlsx", "2026-01-20T21:00:00+00:00"),
    (ref(40), ref(33), R_DATA_OVERWRITE | R_CLOSE, 0x20, "Schuldenaufstellung_Jan.xlsx", "2026-01-24T22:15:00+00:00"),
    (ref(41), ref(34), R_FILE_CREATE | R_CLOSE, 0x20, "Kreditantrag_Sofort.pdf", "2026-01-24T22:33:00+00:00"),
    (ref(42), ref(34), R_FILE_CREATE | R_CLOSE, 0x20, "rufus-4.4p.exe", "2026-01-24T22:48:00+00:00"),
    (ref(40), ref(33), R_FILE_DELETE | R_CLOSE, 0x20, "Schuldenaufstellung_Jan.xlsx", "2026-01-25T08:10:00+00:00"),
]


def _record(usn, file_ref, parent_ref, reason, attrs, name, iso):
    name_u = name.encode("utf-16-le")
    body = bytearray()
    body += struct.pack("<HH", 2, 0)               # Major/Minor
    body += struct.pack("<Q", file_ref)
    body += struct.pack("<Q", parent_ref)
    body += struct.pack("<Q", usn)
    body += struct.pack("<q", filetime(iso))
    body += struct.pack("<I", reason)
    body += struct.pack("<I", 0)                    # SourceInfo
    body += struct.pack("<I", 0)                    # SecurityId
    body += struct.pack("<I", attrs)
    body += struct.pack("<H", len(name_u))          # FileNameLength
    body += struct.pack("<H", 0x3C)                 # FileNameOffset
    body += name_u
    total = 4 + len(body)
    if total % 8:
        pad = 8 - total % 8
        body += b"\x00" * pad
        total += pad
    return struct.pack("<I", total) + bytes(body)


def main():
    if not cmio.device_profile_flag("windows", "usnjrnl", False):
        print("$UsnJrnl: [SKIP] Windows-Profil ohne Flag 'usnjrnl'.")
        return
    os.makedirs(os.path.dirname(JPATH), exist_ok=True)
    out = bytearray()
    usn = 0
    for fr, pr, reason, attrs, name, iso in EVENTS:
        rec = _record(usn, fr, pr, reason, attrs, name, iso)
        out += rec
        usn += len(rec)
    with open(JPATH, "wb") as f:
        f.write(out)
    print(f"$UsnJrnl:$J erzeugt: C/$Extend/$UsnJrnl_$J  ({len(EVENTS)} USN_RECORD_V2, {len(out)} bytes)")


if __name__ == "__main__":
    main()
