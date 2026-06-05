#!/usr/bin/env python3
# =====================================================================
# biome_writer.py  —  SEGB v2 encoder fuer Operation Waldweg
# ---------------------------------------------------------------------
# Erzeugt BIOME-Streamdateien im SEGB-v2-Format, das EXAKT vom
# Validator biome_core.BIOMEAnalyzer (mb4n6/BIOME-Stream-Analyzer)
# gelesen werden kann. Der Writer ist das Spiegelbild des Parsers:
#
#   _detect_version: data[0:4]=='SEGB' und data[52:56]!='SEGB' -> v2
#   _analyze_v2    : Frames ab Offset BASE=32, je 8-Byte-Header
#                    (CRC32-LE der Payload + uint32 unknown),
#                    Footer rueckwaerts ab n-16 in 16-Byte-Eintraegen
#                    struct '<IId' (end_rel, unk, apple_ts),
#                    16-Byte-Null-Separator beendet den Footer.
#
# Harte Invarianten, die der Writer garantiert:
#   * niederwertigstes CRC-Byte != 0  (sonst zaehlt der Parser es als
#     Frame-Padding und verschiebt die Grenze)
#   * 4-Byte-Ausrichtung der Frames; Padding < 16 Null-Bytes
#   * 16 Null-Bytes als Separator zwischen letztem Frame und Footer
#   * data[52:56] != 'SEGB'
# =====================================================================
import struct
import zlib

SEGB_MAGIC = b'SEGB'
BASE = 32
APPLE_EPOCH_OFFSET = 978307200  # Unix-Sekunden am 2001-01-01T00:00:00Z


def unix_to_apple(unix_seconds: float) -> float:
    """CFAbsoluteTime: Sekunden seit 2001-01-01."""
    return float(unix_seconds) - APPLE_EPOCH_OFFSET


# ---------------------------------------------------------------------
# Minimaler Protobuf-Encoder (kompatibel zum ProtobufAnalyzer im Parser)
# ---------------------------------------------------------------------
def _encode_varint(value: int) -> bytes:
    out = bytearray()
    v = value
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def pb_string(field_id: int, text: str) -> bytes:
    raw = text.encode('utf-8')
    key = (field_id << 3) | 2          # wire type 2 = length-delimited
    return bytes([key]) + _encode_varint(len(raw)) + raw


def pb_varint(field_id: int, value: int) -> bytes:
    key = (field_id << 3) | 0          # wire type 0 = varint
    return bytes([key]) + _encode_varint(value)


def pb_double(field_id: int, value: float) -> bytes:
    key = (field_id << 3) | 1          # wire type 1 = fixed64/double
    return bytes([key]) + struct.pack('<d', value)


def build_protobuf(fields: list) -> bytes:
    """fields: Liste von Bytes-Fragmenten aus pb_* Hilfen."""
    return b''.join(fields)


# ---------------------------------------------------------------------
# SEGB-v2-Stream
# ---------------------------------------------------------------------
def _stream_header(stream_apple_ts: float) -> bytes:
    """32-Byte-Kopf. Inhalt ist fuer den v2-Parser irrelevant ausser
    data[0:4]=='SEGB'; wir fuellen plausibel und stabil."""
    h = bytearray()
    h += SEGB_MAGIC                         # 0:4
    h += struct.pack('<I', 0x47)            # 4:8
    h += struct.pack('<d', stream_apple_ts) # 8:16
    h += struct.pack('<I', 0x0A)            # 16:20
    h += struct.pack('<I', 0xFFFFFFFF)      # 20:24
    h += b'\x00' * 8                        # 24:32
    assert len(h) == BASE
    return bytes(h)


def _make_frame(payload: bytes) -> bytes:
    """8-Byte-Header (CRC32-LE + unknown) + Payload.
    Garantiert CRC-Low-Byte != 0, damit der Parser die folgende
    Padding-Erkennung nicht in den Frame hineinlaufen laesst."""
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    if (crc & 0xFF) == 0:
        # Payload minimal variieren, bis das niederwertigste CRC-Byte != 0.
        payload = payload + b'\x01'
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        # extrem unwahrscheinlich, dass es wieder 0 ist
    header = struct.pack('<II', crc, 0x0B)
    return header + payload, crc


def write_stream(path, records, stream_apple_ts=None):
    """records: Liste von (payload_bytes, apple_ts_double).
    Schreibt eine valide SEGB-v2-Datei nach `path` und gibt die
    rohen Bytes zurueck."""
    if stream_apple_ts is None:
        stream_apple_ts = records[0][1] if records else 0.0

    out = bytearray()
    out += _stream_header(stream_apple_ts)

    footer_entries = []  # (end_rel, apple_ts)

    for payload, apple_ts in records:
        # 4-Byte-Ausrichtung des Frame-Starts
        while len(out) % 4 != 0:
            out += b'\x00'
        frame_bytes, _crc = _make_frame(payload)
        out += frame_bytes
        frame_end = len(out)
        end_rel = frame_end - BASE
        footer_entries.append((end_rel, apple_ts))

    # 16-Byte-Null-Separator vor dem Footer (beendet Rueckwaertslesen)
    out += b'\x00' * 16

    # Footer: Eintraege in Reihenfolge (Parser sortiert selbst nach end_rel).
    # struct '<IId' = end_rel(uint32), unk(int32)=1, apple_ts(double)
    for end_rel, apple_ts in footer_entries:
        out += struct.pack('<IId', end_rel, 1, apple_ts)

    data = bytes(out)
    # Invariante absichern
    assert data[0:4] == SEGB_MAGIC
    assert data[52:56] != SEGB_MAGIC, "Position 52-56 darf nicht 'SEGB' sein"

    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    return data
