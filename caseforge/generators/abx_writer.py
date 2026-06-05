#!/usr/bin/env python3
# =====================================================================
# abx_writer.py  —  voll-faithful ABX-Encoder (Android Binary XML)
# ---------------------------------------------------------------------
# Implementiert das AOSP-Protokoll von com.android.internal.util.
# BinaryXmlSerializer + FastDataOutput (PROTOCOL_MAGIC_VERSION_0 = "ABX\0").
#
# Token-Byte = (Command & 0x0f) | (DataType << 4)
#   Command (XmlPullParser-Events):
#     START_DOCUMENT=0 END_DOCUMENT=1 START_TAG=2 END_TAG=3 TEXT=4
#     ATTRIBUTE=15
#   DataType (high nibble):
#     NULL=1 STRING=2 STRING_INTERNED=3 BYTES_HEX=4 BYTES_BASE64=5
#     INT=6 INT_HEX=7 LONG=8 LONG_HEX=9 FLOAT=10 DOUBLE=11
#     BOOLEAN_TRUE=12 BOOLEAN_FALSE=13
#
# Strings: FastDataOutput.writeUTF = 2-Byte-Laenge (BE) + modified-UTF-8.
# Interned: 2-Byte-Index; bei Erstauftritt 0xFFFF + writeUTF + Index=poolgroesse.
#
# Erzeugt Byte-fuer-Byte das, was Androids abx2xml / ccl_abx erwarten.
# (Mitgelieferter Round-Trip-Decoder dient der Selbstverifikation.)
# =====================================================================
import struct

MAGIC = b"ABX\x00"

# Commands
START_DOCUMENT = 0
END_DOCUMENT = 1
START_TAG = 2
END_TAG = 3
TEXT = 4
ATTRIBUTE = 15

# DataTypes (bereits << 4 verschoben)
T_NULL = 1 << 4
T_STRING = 2 << 4
T_STRING_INTERNED = 3 << 4
T_INT = 6 << 4
T_LONG = 8 << 4
T_BOOLEAN_TRUE = 12 << 4
T_BOOLEAN_FALSE = 13 << 4


def _mutf8(s: str) -> bytes:
    """Java modified UTF-8 (Codepunkte; U+0000 -> C0 80; >0xFFFF als Surrogat-Paar)."""
    out = bytearray()
    for ch in s:
        cp = ord(ch)
        if cp == 0:
            out += b"\xc0\x80"
        elif cp < 0x80:
            out.append(cp)
        elif cp < 0x800:
            out.append(0xC0 | (cp >> 6))
            out.append(0x80 | (cp & 0x3F))
        elif cp < 0x10000:
            out.append(0xE0 | (cp >> 12))
            out.append(0x80 | ((cp >> 6) & 0x3F))
            out.append(0x80 | (cp & 0x3F))
        else:
            cp -= 0x10000
            hi = 0xD800 | (cp >> 10)
            lo = 0xDC00 | (cp & 0x3FF)
            for s16 in (hi, lo):
                out.append(0xE0 | (s16 >> 12))
                out.append(0x80 | ((s16 >> 6) & 0x3F))
                out.append(0x80 | (s16 & 0x3F))
    return bytes(out)


class AbxSerializer:
    def __init__(self):
        self.buf = bytearray(MAGIC)
        self._pool = {}

    # ---- FastDataOutput-Primitive ----
    def _u16(self, v):
        self.buf += struct.pack(">H", v & 0xFFFF)

    def _i32(self, v):
        self.buf += struct.pack(">i", v)

    def _i64(self, v):
        self.buf += struct.pack(">q", v)

    def _write_utf(self, s):
        b = _mutf8(s)
        self._u16(len(b))
        self.buf += b

    def _write_interned(self, s):
        idx = self._pool.get(s)
        if idx is not None:
            self._u16(idx)
        else:
            self._u16(0xFFFF)
            self._write_utf(s)
            n = len(self._pool)
            if n < 0xFFFF:
                self._pool[s] = n

    def _token(self, cmd, dtype):
        self.buf.append((cmd & 0x0F) | dtype)

    # ---- Serializer-API (analog BinaryXmlSerializer) ----
    def start_document(self):
        self._token(START_DOCUMENT, T_NULL)
        return self

    def end_document(self):
        self._token(END_DOCUMENT, T_NULL)
        return self

    def start_tag(self, name):
        self._token(START_TAG, T_STRING_INTERNED)
        self._write_interned(name)
        return self

    def end_tag(self, name):
        self._token(END_TAG, T_STRING_INTERNED)
        self._write_interned(name)
        return self

    def text(self, value):
        self._token(TEXT, T_STRING)
        self._write_utf(value)
        return self

    def attr(self, name, value):
        """Auto-Typ: bool -> BOOLEAN; int (passt in 32) -> INT, sonst LONG; sonst STRING."""
        if isinstance(value, bool):
            self._token(ATTRIBUTE, T_BOOLEAN_TRUE if value else T_BOOLEAN_FALSE)
            self._write_interned(name)
        elif isinstance(value, int):
            if -2**31 <= value < 2**31:
                self._token(ATTRIBUTE, T_INT)
                self._write_interned(name)
                self._i32(value)
            else:
                self._token(ATTRIBUTE, T_LONG)
                self._write_interned(name)
                self._i64(value)
        else:
            self._token(ATTRIBUTE, T_STRING)
            self._write_interned(name)
            self._write_utf(str(value))
        return self

    def getvalue(self) -> bytes:
        return bytes(self.buf)


# =====================================================================
# Minimaler Round-Trip-Decoder (Selbstverifikation; spiegelt das Protokoll)
# =====================================================================
def decode(data: bytes):
    assert data[:4] == MAGIC, "kein ABX-Magic"
    pos = 4
    pool = []
    events = []

    def ru16():
        nonlocal pos
        v = struct.unpack_from(">H", data, pos)[0]; pos += 2; return v

    def rutf():
        nonlocal pos
        n = ru16()
        b = data[pos:pos + n]; pos += n
        return b.decode("utf-8", "replace")

    def rinterned():
        idx = ru16()
        nonlocal pos
        if idx == 0xFFFF:
            s = rutf(); pool.append(s); return s
        return pool[idx]

    while pos < len(data):
        token = data[pos]; pos += 1
        cmd = token & 0x0F
        dtype = token & 0xF0
        if cmd == START_DOCUMENT or cmd == END_DOCUMENT:
            events.append(("doc", cmd))
        elif cmd == START_TAG:
            events.append(("start", rinterned()))
        elif cmd == END_TAG:
            events.append(("end", rinterned()))
        elif cmd == TEXT:
            events.append(("text", rutf()))
        elif cmd == ATTRIBUTE:
            name = rinterned()
            if dtype == T_BOOLEAN_TRUE:
                val = True
            elif dtype == T_BOOLEAN_FALSE:
                val = False
            elif dtype == T_INT:
                val = struct.unpack_from(">i", data, pos)[0]; pos += 4
            elif dtype == T_LONG:
                val = struct.unpack_from(">q", data, pos)[0]; pos += 8
            else:  # STRING / STRING_INTERNED
                val = rinterned() if dtype == T_STRING_INTERNED else rutf()
            events.append(("attr", name, val))
        else:
            raise ValueError(f"unbekannter Token cmd={cmd}")
    return events


if __name__ == "__main__":
    w = AbxSerializer().start_document().start_tag("root")
    w.attr("name", "alpha").attr("n", 7).attr("big", 5_000_000_000).attr("flag", True)
    w.start_tag("child").attr("op", "android:camera").end_tag("child")
    w.end_tag("root").end_document()
    blob = w.getvalue()
    ev = decode(blob)
    print("bytes:", len(blob), "magic:", blob[:4])
    for e in ev:
        print(" ", e)
