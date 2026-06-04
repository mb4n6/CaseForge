#!/usr/bin/env python3
# =====================================================================
# evtx_writer.py  —  valider Windows-EVTX-Writer (Template-Modell)
# ---------------------------------------------------------------------
# ElfFile-Header + ElfChnk-Chunk + Event-Records mit BinXML im
# Template-/Substitutions-Modell (wie echte EVTX). Lesbar mit
# python-evtx / EvtxECmd / Event Viewer.
#
# Aufbau je Record-BinXML (B = chunk-rel. Offset des BinXML):
#   [0  ] StreamStart        0f 01 01 00
#   [4  ] TemplateInstance   0c 01 id(4) template_offset(4)=B+14
#   [14 ] TemplateNode       next(4)=0 guid(16) data_len(4)=len(tmpl)
#   [38 ] tmpl               FragmentHeader + Elementbaum(mit 0x0d-Subs) + EOF
#   [.. ] Substitutions      count(4) + decl[(size2,type1,0)] + werte
# Namen sind inline; string_offset wird auf den abs. Chunk-Offset gepatcht.
# =====================================================================
import struct
import binascii
from datetime import datetime, timezone

CHUNK_SIZE = 65536
FILE_HEADER_SIZE = 4096
RECORDS_OFFSET = 512
REC_HEADER = 24
GUID = bytes.fromhex("e1 1c 73 4a 6f 2b 41 4a 9b 9e 01 02 03 04 05 06".replace(" ", ""))


def _ft(iso):
    dt = datetime.fromisoformat(iso)
    return int((dt - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10_000_000)


def _name(s):
    h = 0
    for c in s:
        h = (h * 65599 + ord(c)) & 0xFFFF
    return struct.pack("<IHH", 0, h, len(s)) + s.encode("utf-16-le") + b"\x00\x00"


class _T:
    """Sammelt Template-Bytes (mit Sub-Platzhaltern), Name-Fixups und Sub-Werte."""
    def __init__(self):
        self.subs = []  # (type, value_bytes)

    def elem(self, name, text=None, children=None):
        children = children or []
        head = b"\x01" + struct.pack("<H", 0xFFFF) + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00"
        nm = _name(name)
        fix = [(7, len(head))]
        body = bytearray(head + nm + b"\x02")
        if text is not None:
            idx = len(self.subs)
            self.subs.append((0x01, text.encode("utf-16-le")))
            body += b"\x0d" + struct.pack("<H", idx) + bytes([0x01])
        for ch in children:
            cb, cf = ch
            base = len(body)
            for (s, n) in cf:
                fix.append((base + s, base + n))
            body += cb
        body += b"\x04"
        struct.pack_into("<I", body, 3, len(body) - 7)
        return bytes(body), fix


def event_template(provider, event_id, computer, channel, data, level=4):
    t = _T()
    sysk = [t.elem("Provider", provider), t.elem("EventID", str(event_id)),
            t.elem("Level", str(level)), t.elem("Channel", channel),
            t.elem("Computer", computer)]
    datak = [t.elem(k, str(v)) for k, v in data.items()]
    root = t.elem("Event", children=[t.elem("System", children=sysk),
                                     t.elem("EventData", children=datak)])
    rb, rf = root
    tmpl = b"\x0f\x01\x01\x00" + rb + b"\x00"          # FragmentHeader + Baum + EOF
    fixups = [(s + 4, n + 4) for (s, n) in rf]
    return tmpl, fixups, t.subs


def _record(rid, iso, frag, rec_off):
    tmpl, fixups, subs = frag
    B = rec_off + REC_HEADER
    tmpl_b = bytearray(tmpl)
    for (s, n) in fixups:                               # Namen: abs. Chunk-Offset
        struct.pack_into("<I", tmpl_b, s, (B + 38) + n)
    ti = b"\x0c\x01" + struct.pack("<I", 1) + struct.pack("<I", B + 14)
    tnode = struct.pack("<I", 0) + GUID + struct.pack("<I", len(tmpl))
    subarr = struct.pack("<I", len(subs))
    subarr += b"".join(struct.pack("<H", len(v)) + bytes([ty, 0]) for (ty, v) in subs)
    subarr += b"".join(v for (ty, v) in subs)
    binxml = b"\x0f\x01\x01\x00" + ti + tnode + bytes(tmpl_b) + subarr
    body = struct.pack("<Q", rid) + struct.pack("<Q", _ft(iso)) + binxml
    total = 4 + 4 + len(body) + 4
    pad = (8 - (total % 8)) % 8
    total += pad
    return struct.pack("<II", 0x00002A2A, total) + body + b"\x00" * pad + struct.pack("<I", total)


def build(events):
    records = bytearray()
    first_id, last_id = events[0][0], events[-1][0]
    last_rec_off = RECORDS_OFFSET
    for rid, iso, frag in events:
        rec_off = RECORDS_OFFSET + len(records)
        last_rec_off = rec_off
        records += _record(rid, iso, frag, rec_off)

    free_off = RECORDS_OFFSET + len(records)
    ch = bytearray(RECORDS_OFFSET)
    ch[0:8] = b"ElfChnk\x00"
    struct.pack_into("<Q", ch, 0x08, first_id)
    struct.pack_into("<Q", ch, 0x10, last_id)
    struct.pack_into("<Q", ch, 0x18, first_id)
    struct.pack_into("<Q", ch, 0x20, last_id)
    struct.pack_into("<I", ch, 0x28, 0x80)
    struct.pack_into("<I", ch, 0x2c, last_rec_off)
    struct.pack_into("<I", ch, 0x30, free_off)
    struct.pack_into("<I", ch, 0x34, binascii.crc32(bytes(records)) & 0xFFFFFFFF)
    struct.pack_into("<I", ch, 0x7c, binascii.crc32(bytes(ch[0:120]) + bytes(ch[128:512])) & 0xFFFFFFFF)
    chunk = bytes(ch) + bytes(records)
    chunk += b"\x00" * (CHUNK_SIZE - len(chunk))

    fh = bytearray(FILE_HEADER_SIZE)
    fh[0:8] = b"ElfFile\x00"
    struct.pack_into("<Q", fh, 0x18, last_id + 1)
    struct.pack_into("<I", fh, 0x20, 0x80)
    struct.pack_into("<H", fh, 0x24, 1)
    struct.pack_into("<H", fh, 0x26, 3)
    struct.pack_into("<H", fh, 0x28, FILE_HEADER_SIZE)
    struct.pack_into("<H", fh, 0x2a, 1)
    struct.pack_into("<I", fh, 0x7c, binascii.crc32(bytes(fh[0:120])) & 0xFFFFFFFF)
    return bytes(fh) + chunk
