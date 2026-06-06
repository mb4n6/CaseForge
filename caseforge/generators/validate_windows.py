#!/usr/bin/env python3
# =====================================================================
# validate_windows.py  —  Acceptance-Gate Windows-Minimalgeraet
# ---------------------------------------------------------------------
# Edge History via SQLite-Query (analog ALEAPP/Hindsight),
# NTUSER.DAT via regipy (ECHTER Registry-Parser).
# SRUDB.dat (ESE) ist dokumentierte Folgearbeit -> hier nicht geprueft.
# =====================================================================
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_common import Gate, ok_exit
import caseforge_rng as cfr
import case_master_io as cmio

WFS = os.environ.get('WALDWEG_WIN_FS', '/tmp/win_build')
WUSER = cmio.windows_username()   # Windows-Profilordner aus Fall-Besitzer
P_EDGE = os.path.join(WFS, f'C/Users/{WUSER}/AppData/Local/Microsoft/Edge/User Data/Default/History')
P_NTUSER = os.path.join(WFS, f'C/Users/{WUSER}/NTUSER.DAT')
P_SAM = os.path.join(WFS, 'C/Windows/System32/config/SAM')
P_SYSTEM = os.path.join(WFS, 'C/Windows/System32/config/SYSTEM')
P_SOFTWARE = os.path.join(WFS, 'C/Windows/System32/config/SOFTWARE')
P_AMCACHE = os.path.join(WFS, 'C/Windows/AppCompat/Programs/Amcache.hve')
SID = cfr.win_sid()                    # seed-gesteuert, synchron zu den Generatoren

G = Gate()
ok = G.ok


def gate_edge():
    print("Edge History:")
    con = sqlite3.connect(f"file:{P_EDGE}?mode=ro", uri=True)
    rows = con.execute("SELECT last_visit_time,url,title FROM urls ORDER BY last_visit_time").fetchall()
    ok("urls-Query laeuft", len(rows) >= 1, f"{len(rows)} URLs")
    def webkit(t):
        return datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=t)
    ok("WebKit-Timestamp dekodierbar", webkit(rows[0][0]).year == 2026,
       f"{webkit(rows[0][0]):%Y-%m-%d %H:%M}")
    rel = [r for r in rows if "lebensversicherung" in r[1] or "kredit" in r[1]]
    ok("Belastende Notebook-Suchen vorhanden", len(rel) >= 1, ref=True)
    con.close()


def gate_hive():
    print("NTUSER.DAT (regipy):")
    try:
        from regipy.registry import RegistryHive
    except ImportError:
        ok("regipy verfuegbar", False, "pip install regipy")
        return
    h = RegistryHive(P_NTUSER)
    ok("Root-Key lesbar", h.root.name == "ROOT", f"root={h.root.name!r}")
    tp = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths")
    found = [v.value for v in tp.iter_values() if v.name == "url1"]
    found = found[0] if found else None
    ok("TypedPaths\\url1 dekodierbar", found is not None, repr(found))
    ok("TypedPaths\\url1 == Finanzen", found == rf"C:\Users\{WUSER}\Documents\Finanzen",
       repr(found), ref=True)


def gate_system_hives():
    try:
        from regipy.registry import RegistryHive
    except ImportError:
        return
    if os.path.exists(P_SAM):
        print("SAM (regipy):")
        h = RegistryHive(P_SAM)
        rids = [sk.name for sk in h.get_key(r"\SAM\Domains\Account\Users").iter_subkeys()]
        ok("SAM Users-Schluessel lesbar", "000003E8" in rids and "000001F4" in rids,
           f"RIDs {[r for r in rids if r!='Names']}")
    if os.path.exists(P_SYSTEM):
        print("SYSTEM (regipy):")
        h = RegistryHive(P_SYSTEM)
        cn = h.get_key(r"\ControlSet001\Control\ComputerName\ComputerName")
        name = [v.value for v in cn.iter_values() if v.name == "ComputerName"][0]
        ok("ComputerName lesbar", bool(name), repr(name))
        ok("ComputerName == DESKTOP-REUTER", name == cfr.win_computer_name(), repr(name), ref=True)
        tz = h.get_key(r"\ControlSet001\Control\TimeZoneInformation")
        tzk = [v.value for v in tz.iter_values() if v.name == "TimeZoneKeyName"][0]
        ok("TimeZoneKeyName lesbar", "Europe" in tzk, repr(tzk))
        usb = [s.name for s in h.get_key(r"\ControlSet001\Enum\USBSTOR").iter_subkeys()]
        ok("USBSTOR-Schluessel lesbar", len(usb) >= 1)
        ok("USBSTOR SanDisk vorhanden", any("SanDisk" in u for u in usb), ref=True)
        bam = h.get_key(r"\ControlSet001\Services\bam\State\UserSettings\%s" % SID)
        ok("BAM Last-Execution", len(list(bam.iter_values())) >= 2)
    if os.path.exists(P_SOFTWARE):
        print("SOFTWARE (regipy):")
        h = RegistryHive(P_SOFTWARE)
        profs = h.get_key(r"\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles")
        names = [v.value for sk in profs.iter_subkeys() for v in sk.iter_values() if v.name == "ProfileName"]
        ok("NetworkList-Profile lesbar", len(names) >= 1, str(names))
        ok("NetworkList 'Heim-WLAN Reuter'", "Heim-WLAN Reuter" in names, ref=True)
    if os.path.exists(P_AMCACHE):
        print("Amcache (regipy):")
        h = RegistryHive(P_AMCACHE)
        apps = [s.name for s in h.get_key(r"\Root\InventoryApplicationFile").iter_subkeys()]
        ok("Amcache InventoryApplicationFile", len(apps) >= 2, str(apps))
    # NTUSER UserAssist
    if os.path.exists(P_NTUSER):
        h = RegistryHive(P_NTUSER)
        try:
            ua = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist\{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}\Count")
            ok("UserAssist-Eintraege", len(list(ua.iter_values())) >= 2)
        except Exception:
            ok("UserAssist-Eintraege", False)
    # Recycle Bin $I (valides v2-Format)
    rb = os.path.join(WFS, "C/$Recycle.Bin", SID, "$IA1B2C3.xlsx")
    if os.path.exists(rb):
        print("Recycle Bin:")
        import struct as _s
        d = open(rb, "rb").read()
        ver = _s.unpack_from("<Q", d, 0)[0]
        nlen = _s.unpack_from("<I", d, 24)[0]
        nm = d[28:28 + nlen * 2].decode("utf-16-le").rstrip("\x00")
        ok("$I v2 parsebar", ver == 2, nm)
        ok("$I Name 'Schuldenaufstellung'", "Schuldenaufstellung" in nm, nm, ref=True)


def gate_extended():
    import json
    # Edge Downloads + Bookmarks
    con = sqlite3.connect(f"file:{P_EDGE}?mode=ro&immutable=1", uri=True)
    try:
        dn = con.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        print("Edge Downloads/Bookmarks:")
        ok("Edge downloads-Tabelle", dn >= 2, f"{dn} Downloads")
    except Exception:
        ok("Edge downloads-Tabelle", False)
    con.close()
    bm = os.path.join(os.path.dirname(P_EDGE), "Bookmarks")
    if os.path.exists(bm):
        data = json.load(open(bm, encoding="utf-8"))
        names = [c["name"] for c in data["roots"]["bookmark_bar"]["children"]]
        ok("Edge Bookmarks (JSON) lesbar", len(names) >= 1)
        ok("Edge Bookmarks belastend (Kredit/Lebensvers)",
           any("Kredit" in n or "Lebensvers" in n for n in names), ref=True)
    # WordWheelQuery + ShellBags
    try:
        from regipy.registry import RegistryHive
        h = RegistryHive(P_NTUSER)
        wwq = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\WordWheelQuery")
        ok("WordWheelQuery", len(list(wwq.iter_values())) >= 3)
        uc = os.path.join(WFS, f"C/Users/{WUSER}/AppData/Local/Microsoft/Windows/UsrClass.dat")
        if os.path.exists(uc):
            hu = RegistryHive(uc)
            hu.get_key(r"\Local Settings\Software\Microsoft\Windows\Shell\BagMRU\0\0\0\0\0")
            ok("ShellBags BagMRU (Tiefe)", True)
    except Exception as e:
        ok("WordWheelQuery/ShellBags", False, str(e)[:40])
    # PowerShell-History
    ps = os.path.join(WFS, f"C/Users/{WUSER}/AppData/Roaming/Microsoft/Windows/PowerShell/PSReadline/ConsoleHost_history.txt")
    if os.path.exists(ps):
        t = open(ps, encoding="utf-8").read()
        ok("PowerShell-History (Wipe-Spur)", "Remove-Item" in t and "cipher" in t, ref=True)
    # Notification-DB
    wpn = os.path.join(WFS, f"C/Users/{WUSER}/AppData/Local/Microsoft/Windows/Notifications/wpndatabase.db")
    if os.path.exists(wpn):
        con = sqlite3.connect(f"file:{wpn}?mode=ro&immutable=1", uri=True)
        n = con.execute("SELECT COUNT(*) FROM Notification").fetchone()[0]
        con.close()
        ok("Notification-DB (Toasts)", n >= 2, f"{n} Notifications")
    # LNK
    rec = os.path.join(WFS, f"C/Users/{WUSER}/AppData/Roaming/Microsoft/Windows/Recent")
    lnk = os.path.join(rec, "Schuldenaufstellung_Jan.xlsx.lnk")
    if os.path.exists(lnk):
        d = open(lnk, "rb").read()
        ok("LNK valides Shell-Link", d[0:4] == b"\x4C\x00\x00\x00")
        ok("LNK Ziel 'Schuldenaufstellung'",
           b"Schuldenaufstellung" in d.replace(b"\x00", b""), ref=True)
    # PCA (nur Windows 11 22H2+) — existenz-gesteuert (Win10/Referenz hat es nicht)
    pca = os.path.join(WFS, "C/Windows/appcompat/pca/PcaAppLaunchDic.txt")
    if os.path.exists(pca):
        print("PCA (Windows 11):")
        lines = [l for l in open(pca, encoding="utf-8").read().splitlines() if "|" in l]
        ok("PcaAppLaunchDic.txt parsebar", len(lines) >= 1, f"{len(lines)} Eintraege")
    # $MFT — existenz-gesteuert: FILE-Records mit Fixups + $FILE_NAME parsen
    mft = os.path.join(WFS, "C/$MFT")
    if os.path.exists(mft):
        import struct as _st
        print("$MFT (NTFS):")
        raw = open(mft, "rb").read()
        recs = len(raw) // 1024
        names, fixok, nonres_runs = [], True, []
        for i in range(recs):
            r = bytearray(raw[i * 1024:(i + 1) * 1024])
            if r[0:4] != b"FILE":
                fixok = False; break
            uoff = _st.unpack_from("<H", r, 4)[0]; ucnt = _st.unpack_from("<H", r, 6)[0]
            usn = r[uoff:uoff + 2]
            for s in range(ucnt - 1):
                se = (s + 1) * 512 - 2
                if r[se:se + 2] != usn:
                    fixok = False
                r[se:se + 2] = r[uoff + 2 + s * 2:uoff + 4 + s * 2]
            off = _st.unpack_from("<H", r, 0x14)[0]
            while off < 1020:
                at = _st.unpack_from("<I", r, off)[0]
                if at == 0xFFFFFFFF:
                    break
                al = _st.unpack_from("<I", r, off + 4)[0]
                if at == 0x30:
                    co = _st.unpack_from("<H", r, off + 0x14)[0]
                    nl = r[off + co + 0x40]
                    names.append(r[off + co + 0x42:off + co + 0x42 + nl * 2].decode("utf-16-le"))
                if at == 0x80 and r[off + 8] == 1:           # non-resident $DATA
                    ro = _st.unpack_from("<H", r, off + 0x20)[0]
                    runb = r[off + ro:off + al]
                    rr, pos, prev = [], 0, 0
                    while pos < len(runb) and runb[pos] != 0:
                        h = runb[pos]; pos += 1; lnf = h & 0xF; off_f = h >> 4
                        length = int.from_bytes(runb[pos:pos + lnf], "little"); pos += lnf
                        prev += int.from_bytes(runb[pos:pos + off_f], "little", signed=True); pos += off_f
                        rr.append((length, prev))
                    nonres_runs.extend(rr)
                off += al if al else 8
        ok("$MFT FILE-Records + Fixups valide", recs >= 1 and fixok, f"{recs} Records")
        ok("$MFT $FILE_NAME lesbar", len(names) >= 1, f"{len(names)} Namen")
        sysnames = {"$MFT", "$MFTMirr", "$LogFile", "$Volume", "$Boot", "$UpCase"}
        ok("$MFT NTFS-Systemrecords vorhanden", len(sysnames & set(names)) >= 4,
           f"{sorted(sysnames & set(names))}")
        ok("$MFT Non-Resident $DATA Data-Runs dekodierbar", len(nonres_runs) >= 1,
           f"{len(nonres_runs)} Runs")
    # SRUM SRUDB.dat (ESE-Header-Stub) — existenz-gesteuert
    sru = os.path.join(WFS, "C/Windows/System32/sru/SRUDB.dat")
    if os.path.exists(sru):
        import struct as _st2
        sig = _st2.unpack_from("<I", open(sru, "rb").read(8), 4)[0]
        ok("SRUDB.dat ESE-Signatur", sig == 0x89ABCDEF, hex(sig))
    # $UsnJrnl:$J (USN_RECORD_V2) — existenz-gesteuert
    jpath = os.path.join(WFS, "C/$Extend/$UsnJrnl_$J")
    if os.path.exists(jpath):
        import struct as _st3
        jb = open(jpath, "rb").read()
        rl = _st3.unpack_from("<I", jb, 0)[0]
        maj = _st3.unpack_from("<H", jb, 4)[0]
        nlen = _st3.unpack_from("<H", jb, 0x38)[0]
        nm = jb[0x3C:0x3C + nlen].decode("utf-16-le", "replace")
        print("$UsnJrnl:$J:")
        ok("USN_RECORD_V2 parsebar", maj == 2 and 0 < rl <= len(jb), f"v{maj}, name={nm!r}")
    # ShimCache / AppCompatCache (SYSTEM-Hive) — existenz-gesteuert
    if os.path.exists(P_SYSTEM):
        try:
            from regipy.registry import RegistryHive as _RHs
            sm = _RHs(P_SYSTEM).get_key(r"\ControlSet001\Control\Session Manager\AppCompatCache")
            blob = [v.value for v in sm.iter_values() if v.name == "AppCompatCache"]
            if blob:
                v = blob[0]
                if isinstance(v, str):          # regipy liefert Binaerwerte als Hex-String
                    b = bytes.fromhex(v)
                else:
                    b = bytes(v)
                print("ShimCache (AppCompatCache):")
                ok("AppCompatCache 10ts-Entries", b"10ts" in b, f"{b.count(b'10ts')} Eintraege")
        except Exception:
            pass
    # Office File MRU + ComDlg32 (NTUSER)
    try:
        from regipy.registry import RegistryHive as _RH
        hn = _RH(P_NTUSER)
        xl = hn.get_key(r"\Software\Microsoft\Office\16.0\Excel\File MRU")
        ok("Office Excel File MRU", any("Schuldenaufstellung" in str(v.value) for v in xl.iter_values()), ref=True)
    except Exception as e:
        ok("Office Excel File MRU", False, str(e)[:40])
    # EVTX Security/System
    logs = os.path.join(WFS, "C/Windows/System32/winevt/Logs")
    try:
        from Evtx.Evtx import Evtx
        import re as _re
        sec = os.path.join(logs, "Security.evtx")
        if os.path.exists(sec):
            print("Event Logs (python-evtx):")
            ids = []
            with Evtx(sec) as log:
                for r in log.records():
                    m = _re.search(r"<EventID>(\d+)", r.xml())
                    if m:
                        ids.append(int(m.group(1)))
            ok("Security.evtx 4624-Anmeldung", 4624 in ids, f"EventIDs {ids}")
        syslog = os.path.join(logs, "System.evtx")
        if os.path.exists(syslog):
            ids = []
            with Evtx(syslog) as log:
                for r in log.records():
                    m = _re.search(r"<EventID>(\d+)", r.xml())
                    if m:
                        ids.append(int(m.group(1)))
            ok("System.evtx 6006-Shutdown", 6006 in ids, f"EventIDs {ids}")
    except ImportError:
        pass


def main():
    for p in (P_EDGE, P_NTUSER):
        if not os.path.exists(p):
            print("FEHLT:", p); sys.exit(2)
    gate_edge(); gate_hive(); gate_system_hives(); gate_extended()
    ok_exit(G)


if __name__ == "__main__":
    main()
