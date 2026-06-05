#!/usr/bin/env python3
# =====================================================================
# gen_win_mft.py  —  NTFS $MFT (Auszug) — profilgesteuert (Flag 'mft')
# ---------------------------------------------------------------------
# Erzeugt C/$MFT als Folge valider FILE-Records (mft_writer): Verzeichnis-
# kette Users\<User>\Documents\Finanzen + Downloads, darin Dateien — inkl.
# einer GELOESCHTEN 'Schuldenaufstellung_Jan.xlsx' (in-use-Flag geloescht).
# Parsebar mit MFTECmd/analyzeMFT (FILE-Signatur, Fixups, $SI/$FN).
# Nur wenn das Windows-Geraet das Profil-Flag 'mft' traegt (win10/win11).
# =====================================================================
import os
import sys
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
sys.path.insert(0, HERE)
import case_master_io as cmio
import mft_writer as mw

WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
WUSER = cmio.windows_username()
MFT = os.path.join(WIN, "C/$MFT")

T1 = ("2026-01-20T21:00:00+00:00",) * 4
T2 = ("2026-01-24T22:15:00+00:00",) * 4
T3 = ("2026-01-25T08:10:00+00:00",) * 4


def ref(n):
    return mw.mft_ref(n, 1)


# (rec_no, name, parent_rec, is_dir, data, deleted, times)
PLAN = [
    (30, "Users", 5, True, b"", False, T1),
    (31, WUSER, 30, True, b"", False, T1),
    (32, "Documents", 31, True, b"", False, T1),
    (33, "Finanzen", 32, True, b"", False, T1),
    (34, "Downloads", 31, True, b"", False, T1),
    (40, "Schuldenaufstellung_Jan.xlsx", 33, False,
     b"PK\x03\x04 (geloeschter XLSX-Inhalt) Schuldenaufstellung", True, T3),
    (41, "Kreditantrag_Sofort.pdf", 34, False,
     b"%PDF-1.7 (synthetischer Kreditantrag)", False, T2),
    (42, "rufus-4.4p.exe", 34, False, b"MZ (synthetische EXE)", False, T2),
]


def build():
    os.makedirs(os.path.dirname(MFT), exist_ok=True)
    out = bytearray()
    for rec_no, name, parent, is_dir, data, deleted, times in PLAN:
        rec = bytearray(mw.build_record(rec_no, 1, name, ref(parent),
                                        times, times, data=data, is_dir=is_dir))
        if deleted:
            # In-Use-Bit (0x01) im Flags-Feld (0x16) loeschen -> geloeschter Eintrag
            flags = struct.unpack_from("<H", rec, 0x16)[0] & ~0x01
            struct.pack_into("<H", rec, 0x16, flags)
        out += rec
    with open(MFT, "wb") as f:
        f.write(out)
    return len(PLAN)


def verify():
    """Selbstpruefung: erste 2 Records parsen (Signatur, Fixups ruecksetzen, $FN-Name)."""
    data = open(MFT, "rb").read()
    names = []
    for i in range(min(2, len(data) // mw.REC_SIZE)):
        rec = bytearray(data[i * mw.REC_SIZE:(i + 1) * mw.REC_SIZE])
        assert rec[0:4] == b"FILE", "FILE-Signatur fehlt"
        usa_off = struct.unpack_from("<H", rec, 0x04)[0]
        usa_cnt = struct.unpack_from("<H", rec, 0x06)[0]
        usn = rec[usa_off:usa_off + 2]
        for s in range(usa_cnt - 1):
            sec_end = (s + 1) * mw.SECTOR - 2
            assert rec[sec_end:sec_end + 2] == usn, "Fixup-USN stimmt nicht"
            rec[sec_end:sec_end + 2] = rec[usa_off + 2 + s * 2:usa_off + 4 + s * 2]
        # erstes Attribut suchen -> $FILE_NAME (0x30) Name auslesen
        off = struct.unpack_from("<H", rec, 0x14)[0]
        while off < mw.REC_SIZE - 4:
            atype = struct.unpack_from("<I", rec, off)[0]
            if atype == 0xFFFFFFFF:
                break
            alen = struct.unpack_from("<I", rec, off + 4)[0]
            if atype == 0x30:
                coff = struct.unpack_from("<H", rec, off + 0x14)[0]
                nlen = rec[off + coff + 0x40]
                nm = rec[off + coff + 0x42:off + coff + 0x42 + nlen * 2].decode("utf-16-le")
                names.append(nm)
            off += alen if alen else 8
    return names


def main():
    if not cmio.device_profile_flag("windows", "mft", False):
        print("$MFT: [SKIP] Windows-Profil ohne Flag 'mft'.")
        return
    n = build()
    names = verify()
    print(f"$MFT erzeugt: C/$MFT ({n} FILE-Records, {mw.REC_SIZE} B je Record)")
    print(f"  Selbsttest (Fixups+$FILE_NAME): {names}")


if __name__ == "__main__":
    main()
