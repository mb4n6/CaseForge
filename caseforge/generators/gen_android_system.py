#!/usr/bin/env python3
# =====================================================================
# gen_android_system.py  —  netpolicy.xml + recent_tasks (ABX)
# ---------------------------------------------------------------------
# * data/system/netpolicy.xml  — Netzwerk-Policy je App (Restrict Background,
#   Datenlimit) als Klartext-XML.
# * data/system_ce/0/recent_tasks/<id>_task.xml — Task-Snapshots im
#   ABX-Format (voll-faithful via abx_writer).
# Profil-Flags 'netpolicy' und 'recent_tasks'.
# =====================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
sys.path.insert(0, HERE)
import case_master_io as cmio
import abx_writer as abx

AND = os.environ.get("WALDWEG_AND_FS", os.path.join(ROOT, "02_android_full_fs"))

# (taskId, component, lastActiveTime ms, userId)
RECENTS = [
    (101, "com.android.chrome/com.google.android.apps.chrome.Main", 1772007000000, 0),
    (102, "com.whatsapp/com.whatsapp.HomeActivity", 1772008000000, 0),
    (103, "com.google.android.apps.maps/com.google.android.maps.MapsActivity", 1772009000000, 0),
]
# (uid, app, policy)  policy 1=REJECT_METERED_BACKGROUND, 4=ALLOW_METERED_BACKGROUND
NETPOLICY = [
    (10123, "com.whatsapp", 4),
    (10145, "com.android.chrome", 1),
    (10160, "com.google.android.apps.maps", 1),
]


def write_netpolicy():
    if not cmio.device_profile_flag("android", "netpolicy", False):
        return 0
    p = os.path.join(AND, "data/system/netpolicy.xml")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lines = ['<?xml version="1.0" encoding="utf-8" standalone="yes" ?>',
             '<policies version="13">',
             '  <restrict-background val="true" />']
    for uid, app, pol in NETPOLICY:
        lines.append(f'  <uid-policy uid="{uid}" policy="{pol}" app="{app}" />')
    lines.append('</policies>')
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(NETPOLICY)


def write_recent_tasks():
    if not cmio.device_profile_flag("android", "recent_tasks", False):
        return 0
    d = os.path.join(AND, "data/system_ce/0/recent_tasks")
    os.makedirs(d, exist_ok=True)
    for tid, comp, last, uid in RECENTS:
        w = abx.AbxSerializer().start_document().start_tag("task")
        w.attr("task_id", tid).attr("real_activity", comp).attr("user_id", uid)
        w.attr("last_active_time", last).attr("affinity", comp.split("/")[0])
        w.start_tag("intent").attr("action", "android.intent.action.MAIN") \
            .attr("component", comp).end_tag("intent")
        w.end_tag("task").end_document()
        with open(os.path.join(d, f"{tid}_task.xml"), "wb") as f:
            f.write(w.getvalue())
    return len(RECENTS)


def main():
    n_np = write_netpolicy()
    n_rt = write_recent_tasks()
    if not (n_np or n_rt):
        print("netpolicy/recent_tasks: [SKIP] Android-Profil ohne Flags.")
        return
    print(f"Android-System: netpolicy.xml ({n_np} UIDs) + recent_tasks ({n_rt} Tasks, ABX)")


if __name__ == "__main__":
    main()
