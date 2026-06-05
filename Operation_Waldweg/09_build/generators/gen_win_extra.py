#!/usr/bin/env python3
# =====================================================================
# gen_win_extra.py  —  PowerShell-History + Windows-Notification-DB
# ---------------------------------------------------------------------
#   * PSReadline ConsoleHost_history.txt  (Text) — Aufraeum-/Wipe-Spur
#   * Notifications\wpndatabase.db (SQLite) — Toast-Benachrichtigungen
# Beides fallbezogen (Loeschung Finanzunterlagen; Banking/Messenger-Toasts).
# =====================================================================
import os
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_master_io as cmio
import shutil
import sqlite3
import struct
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
WUSER = cmio.windows_username()   # Windows-Profilordner aus Fall-Besitzer

PS_HIST = os.path.join(WIN, f"C/Users/{WUSER}/AppData/Roaming/Microsoft/Windows/PowerShell/PSReadline/ConsoleHost_history.txt")
WPN_DIR = os.path.join(WIN, f"C/Users/{WUSER}/AppData/Local/Microsoft/Windows/Notifications")
WPN = os.path.join(WPN_DIR, "wpndatabase.db")
TMP = "/tmp/wpn_build.db"


def filetime(iso):
    dt = datetime.fromisoformat(iso)
    return int((dt - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10_000_000)


def powershell_history():
    os.makedirs(os.path.dirname(PS_HIST), exist_ok=True)
    cmds = [
        "Get-Date",
        "cd $env:USERPROFILE\\Documents\\Finanzen",
        "dir",
        "robocopy . E:\\Backup /MIR",
        "Remove-Item .\\Schuldenaufstellung_Jan.xlsx",
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue",
        f"cipher /w:C:\\Users\\{WUSER}\\Documents\\Finanzen",
        "Get-History | Clear-History",
    ]
    with open(PS_HIST, "w", encoding="utf-8") as f:
        f.write("\n".join(cmds) + "\n")
    return PS_HIST


# Toast-Payload (vereinfachtes Toast-XML wie im Payload-BLOB)
def toast(text1, text2):
    return ("<toast><visual><binding template=\"ToastGeneric\">"
            f"<text>{text1}</text><text>{text2}</text>"
            "</binding></visual></toast>").encode("utf-8")


NOTIFS = [
    # (app_primaryid, arrival_iso, text1, text2)
    ("Sparkasse.Banking", "2026-01-24T22:35:00+01:00", "Sparkasse", "Neue TAN-Anforderung: Kreditangebot bestätigen?"),
    ("WhatsApp.Desktop",  "2026-01-24T20:06:00+01:00", "Tobias Klenk", "Ich brauch das Geld bis Montag, Daniel."),
    ("Microsoft.Outlook", "2026-01-25T12:20:00+01:00", "Outlook", "Abwesenheitsnotiz Anna Reuter (Stadtwerke)"),
]


def notification_db():
    os.makedirs(WPN_DIR, exist_ok=True)
    if os.path.exists(TMP):
        os.remove(TMP)
    con = sqlite3.connect(TMP)
    con.executescript("""
    CREATE TABLE NotificationHandler(RecordId INTEGER PRIMARY KEY, PrimaryId TEXT, CreatedTime INT);
    CREATE TABLE Notification(Id INTEGER PRIMARY KEY, HandlerId INT, Type TEXT, Payload BLOB,
        ArrivalTime INT, ExpiryTime INT);
    """)
    cur = con.cursor()
    for i, (app, iso, t1, t2) in enumerate(NOTIFS, 1):
        cur.execute("INSERT INTO NotificationHandler(RecordId,PrimaryId,CreatedTime) VALUES(?,?,?)",
                    (i, app, filetime(iso)))
        cur.execute("""INSERT INTO Notification(Id,HandlerId,Type,Payload,ArrivalTime,ExpiryTime)
            VALUES(?,?,?,?,?,?)""",
            (i, i, "toast", toast(t1, t2), filetime(iso), filetime(iso) + 3 * 864000000000))
    con.commit(); con.close()
    shutil.copy(TMP, WPN)
    return WPN


def main():
    p = powershell_history()
    print(f"PowerShell-History: {os.path.relpath(p, ROOT)}")
    for ln in open(p).read().splitlines():
        print("   " + ln)
    w = notification_db()
    print(f"\nNotification-DB: {os.path.relpath(w, ROOT)}")
    con = sqlite3.connect(f"file:{w}?mode=ro&immutable=1", uri=True)
    rows = con.execute("""SELECT h.PrimaryId,n.ArrivalTime FROM Notification n
        JOIN NotificationHandler h ON n.HandlerId=h.RecordId ORDER BY n.ArrivalTime""").fetchall()
    for app, at in rows:
        dt = datetime(1601, 1, 1, tzinfo=timezone.utc).timestamp() + at / 10_000_000
        print(f"   {datetime.utcfromtimestamp(dt):%Y-%m-%d %H:%M} UTC  {app}")
    con.close()


if __name__ == "__main__":
    main()
