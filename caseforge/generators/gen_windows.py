#!/usr/bin/env python3
# =====================================================================
# gen_windows.py  —  Windows-11-Minimalgeraet (Notebook Daniel)
# ---------------------------------------------------------------------
# Erzeugt:
#   * Edge History (SQLite, WebKit-Epoch) — Browserspuren auf dem Notebook
#   * NTUSER.DAT-Auszug (minimaler, gueltiger regf-Hive) mit TypedPaths
# Status laut Case Master: optional / Folgeerweiterung. SRUDB.dat (ESE)
# bleibt dokumentierte Folgearbeit (siehe README_validation.md), da das
# Schreiben valider ESE-Datenbanken Spezialwerkzeug erfordert.
# =====================================================================
import os
import sqlite3
import struct
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
WFS = os.environ.get('WALDWEG_WIN_FS', os.path.join(ROOT, '03_windows_triage'))

P_EDGE = os.path.join(WFS, 'C/Users/Daniel/AppData/Local/Microsoft/Edge/User Data/Default/History')
P_NTUSER = os.path.join(WFS, 'C/Users/Daniel/NTUSER.DAT')


def chrome_time(iso: str) -> int:
    unix = datetime.fromisoformat(iso).timestamp()
    return int((unix + 11644473600) * 1_000_000)


def reset(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for s in ("", "-wal", "-shm", "-journal"):
        if os.path.exists(path + s):
            os.remove(path + s)


EDGE_URLS = [
    ("2026-01-24T22:20:00+01:00", "https://www.google.com/search?q=lebensversicherung+auszahlung+todesfall", "lebensversicherung auszahlung todesfall - Google Suche"),
    ("2026-01-24T22:31:00+01:00", "https://www.check24.de/kredit/", "Kreditvergleich - CHECK24"),
    ("2026-01-21T20:05:00+01:00", "https://www.sparkasse.de/", "Sparkasse Online-Banking"),
    ("2026-01-19T21:00:00+01:00", "https://www.amazon.de/", "Amazon.de"),  # Noise
]


def build_edge():
    reset(P_EDGE)
    con = sqlite3.connect(P_EDGE)
    con.executescript("""
    CREATE TABLE urls (
        id INTEGER PRIMARY KEY, url TEXT, title TEXT,
        visit_count INTEGER DEFAULT 1, typed_count INTEGER DEFAULT 0,
        last_visit_time INTEGER, hidden INTEGER DEFAULT 0
    );
    CREATE TABLE visits (
        id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER,
        from_visit INTEGER, transition INTEGER DEFAULT 805306368
    );
    """)
    cur = con.cursor()
    for i, (iso, url, title) in enumerate(EDGE_URLS, 1):
        ct = chrome_time(iso)
        cur.execute("""INSERT INTO urls (id,url,title,visit_count,typed_count,
                       last_visit_time) VALUES (?,?,?,1,1,?)""", (i, url, title, ct))
        cur.execute("INSERT INTO visits (id,url,visit_time) VALUES (?,?,?)", (i, i, ct))
    con.commit(); con.close()
    print(f"Edge History: {len(EDGE_URLS)} URLs -> {os.path.relpath(P_EDGE, ROOT)}")


# =====================================================================
# Minimaler, gueltiger Windows-Registry-Hive (regf)
# ---------------------------------------------------------------------
# Genug Struktur, damit regipy (echter Parser) ihn liest. Enthaelt:
#   ROOT\TypedPaths  mit Wert url1 = C:\Users\Daniel\Documents\Finanzen
# Format: 4096-Byte Base Block + ein hbin mit nk/vk/lh/sk-Zellen.
# Zellgroessen sind negativ kodiert (allokiert).
# =====================================================================
HIVE_BLOCK = 4096
HBIN_HDR = 32   # hbin-Header am Anfang der Hive-Bins-Daten (Offset 0)


def _cell(payload: bytes) -> bytes:
    """Zelle = 4-Byte size (negativ=allokiert) + payload, auf 8 ausgerichtet."""
    size = 4 + len(payload)
    size = (size + 7) & ~7
    pad = size - 4 - len(payload)
    return struct.pack('<i', -size) + payload + (b'\x00' * pad)


def build_hive():
    reset(P_NTUSER)
    # ---- Zellen ab hbin-Datenbereich (relativ zu hbin-Start = 0) ----
    # Wir bauen die Zellen sequentiell und merken uns Offsets.
    cells = bytearray()
    offsets = {}

    def add(name, payload):
        offsets[name] = len(cells)   # relativ zum hbin-Datenanfang
        cells.extend(_cell(payload))

    # WICHTIG: regipy nimmt die ERSTE Zelle im ersten hbin als Root-NK.
    # Daher muss nk_root als allererste Zelle liegen (Platzhalter, wird
    # am Ende mit dem fertigen Inhalt ueberschrieben).
    offsets['nk_root'] = len(cells)
    cells.extend(_cell(b'\x00' * 80))

    # sk (Security) — minimal, self-referencing
    sk = struct.pack('<HHIIII', 0x6b73, 0, 0, 0, 1, 0)  # 'sk',flink,blink,refcnt,desc_len
    sk += b'\x00' * 20
    add('sk', sk)

    # vk (Value): url1 = REG_SZ "C:\Users\Daniel\Documents\Finanzen"
    val_name = b'url1'
    val_data = "C:\\Users\\Daniel\\Documents\\Finanzen".encode('utf-16-le') + b'\x00\x00'
    # Datenzelle separat
    add('valdata', val_data)

    # Platzhalter fuer vk (braucht valdata-offset, schon bekannt)
    def make_vk(data_off):
        # 'vk', name_len, data_len, data_off, type(REG_SZ=1), flags(name present=1), spare
        return (struct.pack('<HHIIIHH', 0x6b76, len(val_name), len(val_data),
                            HBIN_HDR + data_off, 1, 1, 0) + val_name)
    add('vk', make_vk(offsets['valdata']))

    # Value-List (Liste der vk-Offsets)
    add('vallist', struct.pack('<I', HBIN_HDR + offsets['vk']))

    # nk (TypedPaths) — Subkey, traegt den Wert url1
    sub_name = b'TypedPaths'

    def make_nk_sub():
        # 'nk', flags(0x20=key), timestamp(8), spare(4), parent_off, subkeys(0),
        # vol_subkeys(0), subkeys_list_off(-1), ... values_count(1), values_list_off,
        # sk_off, classname_off(-1), maxnamelen.., name_len, classname_len
        b = struct.pack('<HH', 0x6b6e, 0x0020)
        b += b'\x00' * 8                       # timestamp
        b += struct.pack('<I', 0)              # spare/access
        b += struct.pack('<i', HBIN_HDR + offsets['nk_root'])  # parent
        b += struct.pack('<I', 0)              # num subkeys
        b += struct.pack('<I', 0)              # num volatile subkeys
        b += struct.pack('<i', -1)             # subkeys list off
        b += struct.pack('<i', -1)             # volatile subkeys list
        b += struct.pack('<I', 1)              # num values
        b += struct.pack('<i', HBIN_HDR + offsets['vallist'])  # values list off
        b += struct.pack('<i', HBIN_HDR + offsets['sk'])       # sk off
        b += struct.pack('<i', -1)             # classname off
        b += struct.pack('<IIIII', 0, 0, 0, 0, 0)  # max name/class lens etc.
        b += struct.pack('<HH', len(sub_name), 0)  # name_len, classname_len
        b += sub_name
        return b

    # nk_root braucht subkey-list -> wir brauchen lh, das nk_sub referenziert.
    # Reihenfolge: erst nk_sub (braucht nk_root off), Henne-Ei -> wir
    # reservieren nk_root offset vorab durch zweistufiges Schreiben.

    # Da Offsets relativ und vorher bekannt sein muessen, legen wir die
    # Reihenfolge fest: sk, valdata, vk, vallist (oben), dann:
    #   nk_root (placeholder parent), lh (subkey list), nk_sub
    # nk_sub.parent zeigt auf nk_root; nk_root.subkeys zeigt auf lh; lh -> nk_sub.
    # Wir kennen nk_root-Offset, sobald wir ihn anlegen.

    # (nk_root-Platzhalter wurde bereits als erste Zelle angelegt)

    # nk_sub jetzt (kennt nk_root)
    add('nk_sub', make_nk_sub())

    # lh (Subkey-Liste): 'lh', count=1, (offset, namehash)
    name_hash = 0
    for ch in sub_name.decode():
        name_hash = (name_hash * 37 + ord(ch)) & 0xFFFFFFFF
    lh = struct.pack('<HH', 0x686c, 1) + struct.pack('<II', HBIN_HDR + offsets['nk_sub'], name_hash)
    add('lh', lh)

    # nk_root final
    root_name = b'ROOT'
    nk_root = struct.pack('<HH', 0x6b6e, 0x002c)   # 0x2c = root + key
    nk_root += b'\x00' * 8
    nk_root += struct.pack('<I', 0)
    nk_root += struct.pack('<i', -1)               # parent (root hat keinen)
    nk_root += struct.pack('<I', 1)                # num subkeys
    nk_root += struct.pack('<I', 0)
    nk_root += struct.pack('<i', HBIN_HDR + offsets['lh'])  # subkeys list
    nk_root += struct.pack('<i', -1)
    nk_root += struct.pack('<I', 0)                # num values
    nk_root += struct.pack('<i', -1)               # values list
    nk_root += struct.pack('<i', HBIN_HDR + offsets['sk'])
    nk_root += struct.pack('<i', -1)
    nk_root += struct.pack('<IIIII', 0, 0, 0, 0, 0)
    nk_root += struct.pack('<HH', len(root_name), 0)
    nk_root += root_name
    root_cell = _cell(nk_root)
    # an reservierter Stelle einsetzen (gleiche Zellgroesse sicherstellen)
    placeholder_size = struct.unpack('<i', bytes(cells[offsets['nk_root']:offsets['nk_root']+4]))[0]
    assert -placeholder_size >= len(root_cell), \
        f"Root-Zelle ({len(root_cell)}) groesser als Platzhalter ({-placeholder_size})"
    # in Platzhalter kopieren (Rest bleibt Padding)
    cells[offsets['nk_root']:offsets['nk_root']+len(root_cell)] = root_cell

    # ---- hbin zusammensetzen ----
    data = bytes(cells)
    # hbin auf Vielfaches von 4096 auffuellen
    hbin_data_size = (len(data) + 0xFFF) & ~0xFFF
    if hbin_data_size < 4096:
        hbin_data_size = 4096
    data = data + b'\x00' * (hbin_data_size - len(data))
    hbin_header = struct.pack('<4sII', b'hbin', 0, hbin_data_size)
    hbin_header += b'\x00' * (32 - len(hbin_header))
    hbin = hbin_header + data

    # ---- Base Block (4096 Byte) ----
    base = bytearray(HIVE_BLOCK)
    struct.pack_into('<4sIIQ', base, 0, b'regf', 1, 1, 0)  # signature, seq1, seq2, timestamp
    struct.pack_into('<II', base, 20, 1, 3)                # major, minor version
    struct.pack_into('<II', base, 28, 0, 1)                # file type, file format
    struct.pack_into('<I', base, 36, HBIN_HDR + offsets['nk_root'])  # root cell offset (rel hbin-data)
    struct.pack_into('<I', base, 40, len(hbin) - 0)        # hive bins data size
    struct.pack_into('<I', base, 44, 1)                    # clustering factor
    name = "NTUSER.DAT".encode('utf-16-le')
    base[48:48+len(name)] = name
    # Checksum (XOR der ersten 508 Byte / als uint32)
    csum = 0
    for i in range(0, 508, 4):
        csum ^= struct.unpack_from('<I', base, i)[0]
    if csum == 0xFFFFFFFF:
        csum = 0xFFFFFFFE
    elif csum == 0:
        csum = 1
    struct.pack_into('<I', base, 508, csum)

    with open(P_NTUSER, 'wb') as f:
        f.write(bytes(base) + hbin)
    print(f"NTUSER.DAT (regf): {os.path.getsize(P_NTUSER)} bytes -> {os.path.relpath(P_NTUSER, ROOT)}")


def main():
    build_edge()
    try:
        build_hive()
    except AssertionError as e:
        print("Hive-Bau uebersprungen:", e)


if __name__ == "__main__":
    main()
