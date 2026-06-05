#!/usr/bin/env python3
# =====================================================================
# mft_writer.py  —  NTFS $MFT FILE-Record-Writer (MFTECmd-parsebar)
# ---------------------------------------------------------------------
# Erzeugt 1024-Byte FILE-Records mit korrekter Fixup-/Update-Sequence,
# residenten Attributen $STANDARD_INFORMATION (0x10) und $FILE_NAME (0x30)
# sowie einem residenten $DATA (0x80). Zeit = Windows FILETIME (100ns seit
# 1601). Tools wie MFTECmd/analyzeMFT parsen einzelne FILE-Records.
# =====================================================================
import struct
from datetime import datetime, timezone

REC_SIZE = 1024
SECTOR = 512


def filetime(iso):
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    unix = dt.timestamp()
    return int((unix + 11644473600) * 10_000_000)


def _pad8(b):
    if len(b) % 8:
        b += b"\x00" * (8 - len(b) % 8)
    return b


def _attr_header(atype, content, attr_id, name=""):
    """Residenter Attribut-Header + Inhalt (8-Byte-aligned)."""
    name_b = name.encode("utf-16-le") if name else b""
    name_len = len(name) if name else 0
    content_off = 0x18 + len(name_b)
    if content_off % 8:
        content_off += 8 - content_off % 8
    head = bytearray(content_off)
    struct.pack_into("<I", head, 0x00, atype)
    total_len = content_off + len(content)
    if total_len % 8:
        total_len += 8 - total_len % 8
    struct.pack_into("<I", head, 0x04, total_len)        # attribute length
    head[0x08] = 0x00                                    # resident
    head[0x09] = name_len                                # name length (chars)
    struct.pack_into("<H", head, 0x0A, 0x18 if name else 0)  # name offset
    struct.pack_into("<H", head, 0x0C, 0x00)             # flags
    struct.pack_into("<H", head, 0x0E, attr_id)          # attribute id
    struct.pack_into("<I", head, 0x10, len(content))     # content length
    struct.pack_into("<H", head, 0x14, content_off)      # content offset
    head[0x16] = 0x00                                    # indexed flag
    if name_b:
        head[0x18:0x18 + len(name_b)] = name_b
    out = bytes(head) + content
    return _pad8(out)


def _si_content(times):
    """$STANDARD_INFORMATION (0x48 Bytes inkl. neuerer Felder)."""
    c, m, mft, a = (filetime(t) for t in times)
    b = bytearray(0x48)
    struct.pack_into("<Q", b, 0x00, c)
    struct.pack_into("<Q", b, 0x08, m)
    struct.pack_into("<Q", b, 0x10, mft)
    struct.pack_into("<Q", b, 0x18, a)
    struct.pack_into("<I", b, 0x20, 0x20)   # DOS-Attribute (Archive)
    # 0x24 max versions, 0x28 version, 0x2C class id, 0x30 owner, 0x34 sec id,
    # 0x38 quota (8), 0x40 USN (8) — 0 belassen
    return bytes(b)


def _fn_content(parent_ref, name, times, real_size, namespace=1):
    c, m, mft, a = (filetime(t) for t in times)
    name_u = name.encode("utf-16-le")
    b = bytearray(0x42)
    struct.pack_into("<Q", b, 0x00, parent_ref)         # parent (ref# | seq<<48)
    struct.pack_into("<Q", b, 0x08, c)
    struct.pack_into("<Q", b, 0x10, m)
    struct.pack_into("<Q", b, 0x18, mft)
    struct.pack_into("<Q", b, 0x20, a)
    alloc = (real_size + 1023) // 1024 * 1024
    struct.pack_into("<Q", b, 0x28, alloc)              # allocated size
    struct.pack_into("<Q", b, 0x30, real_size)          # real size
    struct.pack_into("<I", b, 0x38, 0x20)               # flags (archive)
    struct.pack_into("<I", b, 0x3C, 0)                  # reparse
    b[0x40] = len(name)                                 # name length (chars)
    b[0x41] = namespace                                 # 1=Win32, 2=DOS, 3=both
    return bytes(b) + name_u


def _enc_int_le(value, signed=False):
    """Kleinste LE-Bytefolge fuer einen (ggf. signed) Integer."""
    if value == 0:
        return b"\x00"
    if signed:
        length = 1
        while not (-(1 << (8 * length - 1)) <= value < (1 << (8 * length - 1))):
            length += 1
        return value.to_bytes(length, "little", signed=True)
    length = (value.bit_length() + 7) // 8
    return value.to_bytes(length, "little", signed=False)


def encode_runs(runs):
    """runs = [(length_clusters, lcn_absolut), ...] -> NTFS-DataRun-Bytes."""
    out = bytearray()
    prev_lcn = 0
    for length, lcn in runs:
        len_b = _enc_int_le(length, signed=False)
        delta = lcn - prev_lcn
        off_b = _enc_int_le(delta, signed=True)
        out.append((len(off_b) << 4) | len(len_b))
        out += len_b + off_b
        prev_lcn = lcn
    out.append(0x00)   # Terminator
    return bytes(out)


def _attr_data_nonresident(real_size, runs, attr_id, cluster_size=4096):
    """Non-Resident $DATA-Attribut (0x80) mit Data-Runs."""
    run_bytes = encode_runs(runs)
    total_clusters = sum(l for l, _ in runs)
    alloc = total_clusters * cluster_size
    runs_off = 0x40
    head = bytearray(runs_off)
    struct.pack_into("<I", head, 0x00, 0x80)
    struct.pack_into("<B", head, 0x08, 1)               # non-resident
    struct.pack_into("<H", head, 0x20, runs_off)        # data runs offset
    struct.pack_into("<Q", head, 0x10, 0)               # start VCN
    struct.pack_into("<Q", head, 0x18, total_clusters - 1)  # last VCN
    struct.pack_into("<H", head, 0x0E, attr_id)
    struct.pack_into("<Q", head, 0x28, alloc)           # allocated size
    struct.pack_into("<Q", head, 0x30, real_size)       # real size
    struct.pack_into("<Q", head, 0x38, real_size)       # initialized size
    out = bytes(head) + run_bytes
    total_len = len(out)
    if total_len % 8:
        total_len += 8 - total_len % 8
        out += b"\x00" * (total_len - len(out))
    struct.pack_into("<I", bytearray(out[:4]), 0, 0x80)  # noop, type already set
    out = bytearray(out)
    struct.pack_into("<I", out, 0x04, len(out))          # attribute length
    return _pad8(bytes(out))


def build_record(rec_no, seq, name, parent_ref, si_times, fn_times,
                 data=b"", is_dir=False, nonresident=None):
    """Ein vollstaendiger 1024-Byte FILE-Record inkl. Fixups."""
    usa_off = 0x30
    usa_count = REC_SIZE // SECTOR + 1          # 3 fuer 1024
    first_attr = usa_off + usa_count * 2
    if first_attr % 8:
        first_attr += 8 - first_attr % 8

    aid = 1
    attrs = bytearray()
    attrs += _attr_header(0x10, _si_content(si_times), aid); aid += 1
    fn_size = nonresident[0] if nonresident else len(data)
    attrs += _attr_header(0x30, _fn_content(parent_ref, name, fn_times, fn_size), aid); aid += 1
    if nonresident:
        attrs += _attr_data_nonresident(nonresident[0], nonresident[1], aid); aid += 1
    else:
        attrs += _attr_header(0x80, data, aid, name=""); aid += 1
    attrs += struct.pack("<I", 0xFFFFFFFF)      # End-Marker

    used = first_attr + len(attrs)
    rec = bytearray(REC_SIZE)
    rec[0:4] = b"FILE"
    struct.pack_into("<H", rec, 0x04, usa_off)
    struct.pack_into("<H", rec, 0x06, usa_count)
    struct.pack_into("<Q", rec, 0x08, 0)        # $LogFile seq
    struct.pack_into("<H", rec, 0x10, seq)
    struct.pack_into("<H", rec, 0x12, 1)        # hard link count
    struct.pack_into("<H", rec, 0x14, first_attr)
    struct.pack_into("<H", rec, 0x16, 0x03 if is_dir else 0x01)  # in use (+dir)
    struct.pack_into("<I", rec, 0x18, (used + 7) // 8 * 8)       # used size
    struct.pack_into("<I", rec, 0x1C, REC_SIZE) # allocated size
    struct.pack_into("<Q", rec, 0x20, 0)        # base record
    struct.pack_into("<H", rec, 0x28, aid)      # next attr id
    struct.pack_into("<I", rec, 0x2C, rec_no)   # record number
    rec[first_attr:first_attr + len(attrs)] = attrs

    # ---- Fixups (Update Sequence) ----
    usn = (rec_no & 0xFFFF) or 1
    struct.pack_into("<H", rec, usa_off, usn)
    for i in range(usa_count - 1):
        sec_end = (i + 1) * SECTOR - 2
        orig = rec[sec_end:sec_end + 2]
        rec[usa_off + 2 + i * 2:usa_off + 4 + i * 2] = orig   # Original in USA
        rec[sec_end:sec_end + 2] = struct.pack("<H", usn)     # USN ans Sektorende
    return bytes(rec)


def mft_ref(rec_no, seq):
    return (seq << 48) | rec_no
