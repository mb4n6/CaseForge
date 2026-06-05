#!/usr/bin/env python3
# =====================================================================
# gen_biome.py  —  projiziert BIOME-Streams aus dem Case Master
# ---------------------------------------------------------------------
# Liest case_master.yaml (Single Source of Truth) und erzeugt deterministisch
# zwei BIOME-Streams in das iOS-Dateisystem:
#   * _DKEvent.Safari.History  (aus browsing.anna_safari)
#   * /App/InFocus             (aus timeline app_activity + Tagesnutzung)
# Beide werden anschliessend mit biome_core.BIOMEAnalyzer validiert.
# =====================================================================
import os
import sys
import json
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)                      # .../caseforge
ROOT = os.path.join(BUILD, "..", "examples", "operation_waldweg")  # Beispiel-Case
sys.path.insert(0, HERE)

import biome_writer as bw

# YAML-Loader: PyYAML falls vorhanden, sonst Minimal-Fallback
try:
    import yaml
    def load_yaml(p):
        with open(p) as f:
            return yaml.safe_load(f)
except ImportError:
    print("PyYAML fehlt — bitte: pip install pyyaml --break-system-packages")
    sys.exit(1)

CASE = os.environ.get('WALDWEG_CASE_MASTER', os.path.join(ROOT, 'case_master.yaml'))
IOS_FS = os.environ.get('WALDWEG_IOS_FS', os.path.join(ROOT, '01_ios_full_fs'))
BIOME_BASE = os.path.join(IOS_FS, 'private/var/db/biome/streams/restricted')


def parse_ts(s: str) -> float:
    """ISO 8601 mit Offset -> Unix-Sekunden."""
    dt = datetime.fromisoformat(s)
    return dt.timestamp()


def build_safari_stream(cm):
    """_DKEvent.Safari.History — ein Frame je besuchter URL."""
    entries = []
    safari = cm.get('browsing', {}).get('anna_safari', {})
    items = list(safari.get('relevant', []))
    for it in items:
        unix = parse_ts(it['t'])
        apple = bw.unix_to_apple(unix)
        payload = bw.build_protobuf([
            bw.pb_string(1, it['url']),
            bw.pb_string(2, it['title']),
            bw.pb_double(5, apple),
            bw.pb_varint(6, 1),            # visit_count
        ])
        entries.append((payload, apple))
    # nach Zeit sortieren (stabile, deterministische Reihenfolge)
    entries.sort(key=lambda e: e[1])
    return entries


def build_appfocus_stream(cm):
    """/App/InFocus — App-Vordergrund-Ereignisse aus der Timeline."""
    entries = []
    for ev in cm.get('timeline', []):
        if ev.get('type') == 'app_activity' and ev.get('app'):
            unix = parse_ts(ev['t'])
            apple = bw.unix_to_apple(unix)
            payload = bw.build_protobuf([
                bw.pb_string(1, ev['app']),
                bw.pb_double(2, apple),       # start
                bw.pb_double(3, apple + 240), # end (+4 min)
                bw.pb_varint(4, 1),           # foreground
            ])
            entries.append((payload, apple))
    entries.sort(key=lambda e: e[1])
    return entries


def build_device_state_stream(cm, stream_name):
    """Device.* Streams (BootSession, ScreenLocked) aus device_state-Events."""
    entries = []
    for ev in cm.get('timeline', []):
        if ev.get('type') == 'device_state' and ev.get('stream') == stream_name:
            unix = parse_ts(ev['t'])
            apple = bw.unix_to_apple(unix)
            payload = bw.build_protobuf([
                bw.pb_string(1, stream_name),
                bw.pb_double(2, apple),
                bw.pb_varint(3, 1),   # state-flag (1 = ereignis aktiv)
            ])
            entries.append((payload, apple))
    entries.sort(key=lambda e: e[1])
    return entries


def write_databaseversion(stream_dir):
    """BIOME-Streams liegen neben einer databaseVersion.json."""
    p = os.path.join(stream_dir, 'databaseVersion.json')
    os.makedirs(stream_dir, exist_ok=True)
    with open(p, 'w') as f:
        json.dump({"databaseVersion": "2", "streamVersion": "2"}, f)


def emit(stream_name, numeric_id, entries):
    stream_dir = os.path.join(BIOME_BASE, stream_name)
    local_dir = os.path.join(stream_dir, 'local')
    target = os.path.join(local_dir, numeric_id)
    data = bw.write_stream(target, entries)
    write_databaseversion(stream_dir)
    return target, data


def main():
    cm = load_yaml(CASE)

    safari = build_safari_stream(cm)
    appfocus = build_appfocus_stream(cm)

    outputs = []
    if safari:
        outputs.append(emit('_DKEvent.Safari.History', '674567890', safari))
    if appfocus:
        outputs.append(emit('App.InFocus', '674567891', appfocus))

    # --- zusaetzliche statische Streams (App-Install, Battery, NowPlaying, Bluetooth) ---
    def static_stream(entries):
        out = []
        for iso, fields in entries:
            apple = bw.unix_to_apple(parse_ts(iso))
            out.append((bw.build_protobuf(fields), apple))
        out.sort(key=lambda e: e[1])
        return out

    extra = {
        'App.Install': ('674567894', static_stream([
            ("2025-11-20T20:00:00+01:00", [bw.pb_string(1, "net.whatsapp.WhatsApp"), bw.pb_varint(2, 1)]),
            ("2025-12-02T18:30:00+01:00", [bw.pb_string(1, "org.whispersystems.signal"), bw.pb_varint(2, 1)]),
            ("2026-01-22T22:30:00+01:00", [bw.pb_string(1, "de.is24.iphone"), bw.pb_varint(2, 1)])])),
        '_DKEvent.App.Activity.Battery': ('674567895', static_stream([
            ("2026-01-24T22:30:00+01:00", [bw.pb_double(1, 0.74), bw.pb_varint(2, 0)]),
            ("2026-01-25T06:50:00+01:00", [bw.pb_double(1, 0.61), bw.pb_varint(2, 0)]),
            ("2026-01-25T07:50:00+01:00", [bw.pb_double(1, 0.55), bw.pb_varint(2, 0)])])),
        '_DKEvent.Media.NowPlaying': ('674567896', static_stream([
            ("2026-01-24T18:40:00+01:00", [bw.pb_string(1, "com.spotify.client"), bw.pb_string(2, "Abendlauf-Playlist")])])),
        'Device.BluetoothConnection': ('674567897', static_stream([
            ("2026-01-24T18:35:00+01:00", [bw.pb_string(1, "AirPods Anna"), bw.pb_varint(2, 1)]),
            ("2026-01-25T07:33:00+01:00", [bw.pb_string(1, "AirPods Anna"), bw.pb_varint(2, 1)])])),
    }
    for sname, (nid, ents) in extra.items():
        if ents:
            outputs.append(emit(sname, nid, ents))

    boot = build_device_state_stream(cm, 'Device.BootSession')
    if boot:
        outputs.append(emit('Device.BootSession', '674567892', boot))
    locked = build_device_state_stream(cm, 'Device.ScreenLocked')
    if locked:
        outputs.append(emit('Device.ScreenLocked', '674567893', locked))

    print(f"Erzeugt: {len(outputs)} Streams")
    for path, data in outputs:
        rel = os.path.relpath(path, ROOT)
        print(f"  {rel}  ({len(data)} bytes)")

    # ----- Validierung gegen den echten Parser -----
    print("\n=== VALIDIERUNG (biome_core.BIOMEAnalyzer) ===")
    try:
        import biome_core
    except ImportError:
        bc = os.path.join(BUILD, 'biome_core.py')
        if os.path.exists(bc):
            sys.path.insert(0, BUILD)
            import biome_core
        else:
            print("biome_core.py nicht gefunden — Validierung uebersprungen.")
            return

    all_ok = True
    for path, _ in outputs:
        an = biome_core.BIOMEAnalyzer(path, max_frames=100, verbose=False)
        ok = an.analyze()
        n = len(an.frames)
        crc_all = all(fr.crc_ok for fr in an.frames) if an.frames else False
        status = "OK" if (ok and n > 0 and crc_all and an.version == 2) else "FEHLER"
        if status != "OK":
            all_ok = False
        print(f"  [{status}] {os.path.basename(path)}  v={an.version}  frames={n}  crc_all={crc_all}")
        for fr in an.frames:
            pb = fr.protobuf_data
            print(f"      frame {fr.index}: ts={fr.get_timestamp_str()}  crc_ok={fr.crc_ok}  pb={pb}")

    print("\nGESAMT:", "ALLE STREAMS VALIDE ✓" if all_ok else "MIND. 1 FEHLER ✗")


if __name__ == '__main__':
    main()
