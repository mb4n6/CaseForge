#!/usr/bin/env python3
# =====================================================================
# gen_win_srum.py  —  SRUM SRUDB.dat (ESE) — STRUKTURELLER STUB
# ---------------------------------------------------------------------
# WICHTIG / TRANSPARENZ: SRUDB.dat ist eine ESE/JET-B-Tree-Datenbank.
# Ein VOLL-FAITHFUL ESE-Writer (Katalog, B-Trees, Long-Values) ist hier
# bewusst NICHT umgesetzt. Erzeugt wird eine ESE-HEADER-VALIDE Datei
# (Signatur 0x89ABCDEF, Formatversion, Seitengroesse) — von esedbinfo als
# ESE erkannt — PLUS eine Begleit-CSV mit den vorgesehenen SRUM-Inhalten
# (Netz-/App-Nutzung). So bleibt der Charakter dokumentiert und nutzbar,
# ohne Faithfulness vorzutaeuschen. Profil-Flag 'srum'.
# =====================================================================
import os
import sys
import csv
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
sys.path.insert(0, HERE)
import case_master_io as cmio

WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
SRU = os.path.join(WIN, "C/Windows/System32/sru/SRUDB.dat")
PAGE = 32768

# (timestamp, app, user_sid_kurz, bytes_sent, bytes_recv)  — Netznutzung
ROWS = [
    ("2026-01-24T22:20:00+00:00", "msedge.exe", "S-1-5-21-...-1001", 1048576, 8388608),
    ("2026-01-24T22:48:00+00:00", "rufus-4.4p.exe", "S-1-5-21-...-1001", 20480, 4096),
    ("2026-01-25T08:11:00+00:00", "robocopy.exe", "S-1-5-21-...-1001", 524288, 12288),
]


def _ese_header():
    h = bytearray(PAGE)
    struct.pack_into("<I", h, 0x00, 0)              # checksum (Platzhalter)
    struct.pack_into("<I", h, 0x04, 0x89ABCDEF)     # ESE-Signatur
    struct.pack_into("<I", h, 0x08, 0x620)          # ulVersion (Win-typisch)
    struct.pack_into("<I", h, 0x0C, 0)              # ulFileType = 0 (Database)
    struct.pack_into("<I", h, 0xEC, PAGE)           # cbDbPageSize
    return bytes(h)


def main():
    if not cmio.device_profile_flag("windows", "srum", False):
        print("SRUM: [SKIP] Windows-Profil ohne Flag 'srum'.")
        return
    os.makedirs(os.path.dirname(SRU), exist_ok=True)
    with open(SRU, "wb") as f:
        f.write(_ese_header())
    out = os.path.join(WIN, "C/Windows/System32/sru/SRUDB_inhalt.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "app", "user_sid", "bytes_sent", "bytes_recv"])
        w.writerows(ROWS)
    print(f"SRUDB.dat (ESE-Header-Stub) + Begleit-CSV erzeugt: "
          f"C/Windows/System32/sru/  ({len(ROWS)} Netznutzungs-Zeilen)")
    print("  Hinweis: ESE-Header valide; voll-faithful ESE-Tabellen = dokumentierte Folgearbeit.")


if __name__ == "__main__":
    main()
