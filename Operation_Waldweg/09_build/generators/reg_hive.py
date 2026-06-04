#!/usr/bin/env python3
# =====================================================================
# reg_hive.py  —  allgemeiner Windows-Registry-Hive-Writer (regf)
# ---------------------------------------------------------------------
# Baut aus einem verschachtelten Python-Dict einen gueltigen regf-Hive,
# den sowohl regipy als auch Parse::Win32Registry / RegRipper lesen.
#
# Format-Eckpunkte (mit beiden Parsern abgeglichen):
#   * 4096-Byte Base Block; root_key_offset @0x24; XOR-Checksum @0x1FC
#   * Root-NK ist die ERSTE Zelle im hbin (regipy nimmt die erste Zelle),
#     UND base.root_key_offset zeigt darauf (Parse::Win32Registry).
#   * Zell-Offsets relativ zum hbin-Datenbereich: 32 + cell_index.
#   * Subkey-Listen als 'lh' (Offset + Name-Hash), Wertelisten als
#     uint32-Array; Werte nicht-resident (eigene Datenzelle).
#
# Knoten-Schema:
#   node = {"values": {name: (vtype, value)}, "subkeys": {name: node}}
#   vtype in: 'sz','dword','qword','binary','multi_sz'
# =====================================================================
import struct

SEGB = b"regf"  # (Basisblock-Signatur; SEGB ist BIOME — hier regf!)
REGF_MAGIC = b"regf"
HBIN_HDR = 32
BLOCK = 4096

TYPE_ID = {"sz": 1, "expand_sz": 2, "binary": 3, "dword": 4,
           "qword": 11, "multi_sz": 7}


def _cell(payload: bytes) -> bytes:
    size = 4 + len(payload)
    size = (size + 7) & ~7
    pad = size - 4 - len(payload)
    return struct.pack("<i", -size) + payload + b"\x00" * pad


def _nk_payload(flags, parent_off, n_sub, sub_off, n_val, val_off, sk_off, name):
    nm = name.encode("latin-1", "replace")
    b = struct.pack("<HH", 0x6b6e, flags)      # 'nk', flags
    b += b"\x00" * 8                            # last_modified
    b += struct.pack("<I", 0)                   # access bits / spare
    b += struct.pack("<i", parent_off)          # parent
    b += struct.pack("<I", n_sub)               # subkey count
    b += struct.pack("<I", 0)                   # volatile subkey count
    b += struct.pack("<i", sub_off)             # subkeys list off
    b += struct.pack("<i", -1)                  # volatile subkeys list
    b += struct.pack("<I", n_val)               # values count
    b += struct.pack("<i", val_off)             # values list off
    b += struct.pack("<i", sk_off)              # security key off
    b += struct.pack("<i", -1)                  # class name off
    b += struct.pack("<IIIII", 0, 0, 0, 0, 0)   # max name/class lens + spare
    b += struct.pack("<HH", len(nm), 0)         # name len, class len
    b += nm
    return b


def _nk_cell_size(name):
    return len(_cell(_nk_payload(0, -1, 0, -1, 0, -1, -1, name)))


def _encode_value(vtype, value):
    if vtype == "sz" or vtype == "expand_sz":
        return value.encode("utf-16-le") + b"\x00\x00"
    if vtype == "dword":
        return struct.pack("<I", value & 0xFFFFFFFF)
    if vtype == "qword":
        return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)
    if vtype == "binary":
        return bytes(value)
    if vtype == "multi_sz":
        out = b""
        for s in value:
            out += s.encode("utf-16-le") + b"\x00\x00"
        return out + b"\x00\x00"
    raise ValueError(vtype)


def build(tree, root_name="ROOT"):
    """tree: {root_name: node}. Gibt die vollstaendigen Hive-Bytes zurueck."""
    assert len(tree) == 1
    root_name = list(tree.keys())[0]
    root_node = tree[root_name]

    cells = bytearray()

    def append(payload):
        idx = len(cells)
        cells.extend(_cell(payload))
        return idx

    def off(idx):
        return HBIN_HDR + idx

    # Root-Zelle reservieren (erste Zelle)
    root_size = _nk_cell_size(root_name)
    root_idx = len(cells)
    cells.extend(_cell(b"\x00" * (root_size - 8)))  # Platzhalter gleicher Groesse

    # gemeinsame Security-Zelle (minimal)
    sk = struct.pack("<HHIIII", 0x6b73, 0, 0, 0, 1, 0) + b"\x00" * 20
    sk_idx = append(sk)
    sk_off = off(sk_idx)

    def emit_value(name, vtype, value):
        data = _encode_value(vtype, value)
        data_idx = append(data)
        nm = name.encode("latin-1", "replace")
        flags = 1 if nm else 0
        vk = struct.pack("<HHIIIHH", 0x6b76, len(nm), len(data),
                         off(data_idx), TYPE_ID[vtype], flags, 0) + nm
        return off(append(vk))

    def emit_value_list(offs):
        if not offs:
            return -1
        payload = b"".join(struct.pack("<I", o) for o in offs)
        return off(append(payload))

    def emit_subkey_list(children):  # children: list of (name, nk_off)
        if not children:
            return -1
        payload = struct.pack("<HH", 0x686c, len(children))  # 'lh'
        for name, nk_off in children:
            h = 0
            for ch in name:
                h = (h * 37 + ord(ch)) & 0xFFFFFFFF
            payload += struct.pack("<II", nk_off, h)
        return off(append(payload))

    def build_node(name, node, is_root):
        values = node.get("values", {})
        subkeys = node.get("subkeys", {})
        val_offs = [emit_value(vn, vt, vv) for vn, (vt, vv) in values.items()]
        vlist = emit_value_list(val_offs)

        child_infos = []   # (name, nk_off, nk_idx)
        for cname in sorted(subkeys.keys(), key=str.lower):
            c_off, c_idx = build_node(cname, subkeys[cname], False)
            child_infos.append((cname, c_off, c_idx))
        sub_off = emit_subkey_list([(n, o) for n, o, _ in child_infos])

        flags = 0x2c if is_root else 0x20
        payload = _nk_payload(flags, -1 if is_root else 0,
                              len(child_infos), sub_off,
                              len(val_offs), vlist, sk_off, name)
        if is_root:
            cell = _cell(payload)
            assert len(cell) <= root_size, f"Root-Zelle {len(cell)}>{root_size}"
            cells[root_idx:root_idx + len(cell)] = cell
            nk_idx = root_idx
        else:
            nk_idx = append(payload)
        nk_off = off(nk_idx)
        # Parent-Zeiger der direkten Kinder patchen (Feld @ payload+16)
        for _, _, c_idx in child_infos:
            pos = c_idx + 4 + 16
            cells[pos:pos + 4] = struct.pack("<i", nk_off)
        return nk_off, nk_idx

    build_node(root_name, root_node, True)

    # hbin auf 4 KiB aufrunden
    data = bytes(cells)
    hbin_size = (len(data) + 0xFFF) & ~0xFFF
    if hbin_size < BLOCK:
        hbin_size = BLOCK
    data = data + b"\x00" * (hbin_size - len(data))
    hbin = struct.pack("<4sII", b"hbin", 0, hbin_size) + b"\x00" * (HBIN_HDR - 12) + data

    base = bytearray(BLOCK)
    struct.pack_into("<4sIIQ", base, 0, REGF_MAGIC, 1, 1, 0)
    struct.pack_into("<II", base, 20, 1, 5)               # major, minor
    struct.pack_into("<II", base, 28, 0, 1)               # file type, format
    struct.pack_into("<I", base, 36, off(root_idx))       # root key offset
    struct.pack_into("<I", base, 40, len(hbin))           # hive bins data size
    struct.pack_into("<I", base, 44, 1)                   # clustering
    nm = "WALDWEG.HIV".encode("utf-16-le")
    base[48:48 + len(nm)] = nm
    csum = 0
    for i in range(0, 508, 4):
        csum ^= struct.unpack_from("<I", base, i)[0]
    csum = 0xFFFFFFFE if csum == 0xFFFFFFFF else (1 if csum == 0 else csum)
    struct.pack_into("<I", base, 508, csum)

    return bytes(base) + hbin


def write(tree, path, root_name="ROOT"):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = build(tree, root_name)
    with open(path, "wb") as f:
        f.write(data)
    return data
