#!/usr/bin/env python3
# =====================================================================
# gen_win_evtx.py  —  Windows Event Logs (.evtx) fuer Daniels Notebook
# ---------------------------------------------------------------------
# Security.evtx: 4624 (Anmeldung Daniel 25.01 06:40), 4634 (Abmeldung)
# System.evtx:   6005 (EventLog-Start/Boot), 6006 (sauberer Shutdown 12:30)
# Valides EVTX (evtx_writer) -> lesbar mit python-evtx / EvtxECmd.
# =====================================================================
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evtx_writer as ew
import caseforge_rng as cfr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
LOGS = os.path.join(WIN, "C/Windows/System32/winevt/Logs")
COMP = cfr.win_computer_name()


def build_security():
    sec = "Microsoft-Windows-Security-Auditing"
    ch = "Security"
    events = [
        (1001, "2026-01-25T05:40:00+00:00", ew.event_template(sec, 4624, COMP, ch, {
            "TargetUserName": "Daniel", "LogonType": "2", "WorkstationName": COMP,
            "IpAddress": "-"})),  # interaktive Anmeldung
        (1002, "2026-01-25T06:33:00+00:00", ew.event_template(sec, 4648, COMP, ch, {
            "TargetUserName": "Daniel", "TargetServerName": "localhost",
            "ProcessName": r"C:\Windows\System32\runas.exe"})),
        (1003, "2026-01-25T11:25:00+00:00", ew.event_template(sec, 4634, COMP, ch, {
            "TargetUserName": "Daniel", "LogonType": "2"})),  # Abmeldung
    ]
    return ew.build(events)


def build_system():
    el = "EventLog"
    ch = "System"
    events = [
        (5001, "2026-01-25T05:38:00+00:00", ew.event_template(el, 6005, COMP, ch, {
            "Message": "Der Ereignisprotokolldienst wurde gestartet."})),  # Boot
        (5002, "2026-01-25T11:30:00+00:00", ew.event_template(el, 6006, COMP, ch, {
            "Message": "Der Ereignisprotokolldienst wurde beendet."})),    # sauberer Shutdown
        (5003, "2026-01-24T21:05:00+00:00", ew.event_template("Microsoft-Windows-Kernel-Power", 42, COMP, ch, {
            "Reason": "0", "Message": "Das System wechselt in den Energiesparmodus."})),
    ]
    return ew.build(events)


def main():
    os.makedirs(LOGS, exist_ok=True)
    out = {"Security.evtx": build_security(), "System.evtx": build_system()}
    for name, data in out.items():
        p = os.path.join(LOGS, name)
        with open(p, "wb") as f:
            f.write(data)
        print(f"  {name:14s} {len(data):>6d} B -> {os.path.relpath(p, ROOT)}")

    # ---- Validierung mit python-evtx ----
    print("\n=== Validierung (python-evtx) ===")
    try:
        from Evtx.Evtx import Evtx
        import re
    except ImportError:
        print("python-evtx fehlt — uebersprungen."); return
    ok = True
    for name in out:
        p = os.path.join(LOGS, name)
        ids = []
        with Evtx(p) as log:
            for rec in log.records():
                xml = rec.xml()
                m = re.search(r"<EventID>(\d+)</EventID>", xml)
                if m:
                    ids.append(int(m.group(1)))
        print(f"  {name}: EventIDs {ids}")
        ok = ok and len(ids) >= 2
    print("\nGESAMT:", "EVTX valide & parsebar ✓" if ok else "FEHLER ✗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
