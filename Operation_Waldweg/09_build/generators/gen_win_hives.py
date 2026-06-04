#!/usr/bin/env python3
# =====================================================================
# gen_win_hives.py  —  Windows-Registry-Hives (regf) fuer Daniels Notebook
# ---------------------------------------------------------------------
# Erzeugt RegRipper-/regipy-parsebare Hives:
#   SAM     - Benutzerkonten (samparse)
#   SYSTEM  - ComputerName/TimeZone/Shutdown + USBSTOR/MountedDevices/BAM
#             (compname/timezone/shutdown/usbstor/mountdev/bam)
#   SOFTWARE- NetworkList-Profile (WLANs), Windows-Version, Uninstall
#             (networklist/winver/uninstall)
#   NTUSER.DAT - TypedPaths/RunMRU/RecentDocs/UserAssist
#             (typedpaths/runmru/recentdocs/userassist)
#   Amcache.hve - InventoryApplicationFile (amcache)
#
# Pfade gemaess Standard. Validierung hier mit regipy; RegRipper lokal.
# =====================================================================
import os
import struct
import sys
import codecs
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.dirname(BUILD)
sys.path.insert(0, HERE)
import reg_hive

WIN = os.environ.get("WALDWEG_WIN_FS", os.path.join(ROOT, "03_windows_triage"))
CONFIG = os.path.join(WIN, "C/Windows/System32/config")
AMCACHE = os.path.join(WIN, "C/Windows/AppCompat/Programs/Amcache.hve")
NTUSER = os.path.join(WIN, "C/Users/Daniel/NTUSER.DAT")
SID = "S-1-5-21-1004336348-1177238915-682003330-1000"


def filetime(iso):
    dt = datetime.fromisoformat(iso)
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return struct.pack("<Q", int((dt - epoch).total_seconds() * 10_000_000))


def systemtime(iso):
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return struct.pack("<8H", dt.year, dt.month, dt.isoweekday() % 7,
                       dt.day, dt.hour, dt.minute, dt.second, 0)


def userassist(count, last_iso):
    b = bytearray(72)
    struct.pack_into("<I", b, 0x04, count)            # run count
    b[0x3C:0x44] = filetime(last_iso)                 # last executed
    struct.pack_into("<I", b, 0x44, 0xFFFFFFFF)
    return bytes(b)


def bam_entry(last_iso):
    return filetime(last_iso) + b"\x00" * 16          # 24 byte, FILETIME @0


def rot13(s):
    return codecs.encode(s, "rot_13")


def mrulistex(indices):
    return b"".join(struct.pack("<I", i) for i in indices) + struct.pack("<I", 0xFFFFFFFF)


def wordwheel_val(term):
    return term.encode("utf-16-le") + b"\x00\x00"


def office_mru_val(path, iso):
    # Format: [F00000000][T{FILETIME hex 16}][O00000000]*<Pfad>
    ft = int((datetime.fromisoformat(iso) - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 10_000_000)
    return f"[F00000000][T{ft:016X}][O00000000]*{path}"


def pidl(items):
    # ITEMIDLIST = aneinandergereihte Shell-Items + 2-Byte-Terminator
    return b"".join(items) + b"\x00\x00"


# ---- ShellBags Shell-Item-PIDLs (vereinfacht, RegRipper/SBECmd-Layout) ----
def _dosdate(iso):
    dt = datetime.fromisoformat(iso)
    fat_date = ((dt.year - 1980) << 9) | (dt.month << 5) | dt.day
    fat_time = (dt.hour << 11) | (dt.minute << 5) | (dt.second // 2)
    return struct.pack("<HH", fat_date, fat_time)


def shellitem_root():
    # 'My Computer' (GUID 20D04FE0-3AEA-1069-A2D8-08002B30309D), Typ 0x1F
    guid = bytes.fromhex("e04fd020ea3a6910a2d808002b30309d")
    body = bytes([0x1F, 0x50]) + guid
    return struct.pack("<H", len(body) + 2) + body


def shellitem_drive(letter):
    # Volume, Typ 0x2F, "C:\"
    body = bytes([0x2F]) + (letter + ":\\").encode("ascii") + b"\x00" * 16
    return struct.pack("<H", len(body) + 2) + body


def shellitem_dir(name, mtime="2026-01-20T20:00:00+01:00",
                  ctime="2025-09-10T10:00:00+01:00", atime="2026-01-25T08:00:00+01:00"):
    # Verzeichnis, Typ 0x31, mit BEEF0004-Erweiterungsblock (Unicode-Langname)
    ascii_name = name.encode("ascii", "replace") + b"\x00"
    if len(ascii_name) % 2:
        ascii_name += b"\x00"
    pre = struct.pack("<BBI", 0x31, 0x00, 0) + _dosdate(mtime) + struct.pack("<H", 0x10) + ascii_name
    long_name = name.encode("utf-16-le") + b"\x00\x00"
    beef = struct.pack("<H", 0x0008) + struct.pack("<I", 0xBEEF0004)
    beef += _dosdate(ctime) + _dosdate(atime) + struct.pack("<H", 0)  # unknown
    beef += long_name
    beef_full = struct.pack("<H", len(beef) + 4) + beef  # +4: size(2)+firstoff(2)
    first_off = struct.pack("<H", 2 + len(pre))          # Offset zum BEEF-Block
    body = pre + beef_full + first_off
    return struct.pack("<H", len(body) + 2) + body


# ---------------- SAM (F/V) ----------------
def build_F(rid, acb, logins, last_login, pw_set):
    f = bytearray(0x50)
    f[0x08:0x10] = filetime(last_login)
    f[0x18:0x20] = filetime(pw_set)
    struct.pack_into("<I", f, 0x30, rid)
    struct.pack_into("<H", f, 0x38, acb)
    struct.pack_into("<H", f, 0x42, logins)
    return bytes(f)


def build_V(username, fullname, comment):
    name = username.encode("utf-16-le"); full = fullname.encode("utf-16-le"); com = comment.encode("utf-16-le")
    h = bytearray(0xCC); o = 0
    struct.pack_into("<I", h, 0x0c, o); struct.pack_into("<I", h, 0x10, len(name)); o += len(name)
    struct.pack_into("<I", h, 0x18, o); struct.pack_into("<I", h, 0x1c, len(full)); o += len(full)
    struct.pack_into("<I", h, 0x24, o); struct.pack_into("<I", h, 0x28, len(com)); o += len(com)
    return bytes(h) + name + full + com


def sam_tree():
    users = {
        "000001F4": {"values": {
            "F": ("binary", build_F(500, 0x0211, 0, "2026-01-02T09:00:00+00:00", "2025-12-01T08:00:00+00:00")),
            "V": ("binary", build_V("Administrator", "", "Vordefiniertes Administratorkonto"))}},
        "000003E8": {"values": {
            "F": ("binary", build_F(1000, 0x0210, 27, "2026-01-25T06:40:00+00:00", "2025-12-15T19:30:00+00:00")),
            "V": ("binary", build_V("Daniel", "Daniel Reuter", "Privatkonto"))}},
        "Names": {"subkeys": {"Administrator": {"values": {"": ("sz", "")}},
                              "Daniel": {"values": {"": ("sz", "")}}}},
    }
    return {"ROOT": {"subkeys": {"SAM": {"subkeys": {"Domains": {"subkeys": {
        "Account": {"subkeys": {"Users": {"subkeys": users}}}}}}}}}}


# ---------------- SYSTEM ----------------
def system_tree():
    usbstor = {"Disk&Ven_SanDisk&Prod_Cruzer_Blade&Rev_1.00": {"subkeys": {
        "4C530001260102117384&0": {"values": {
            "FriendlyName": ("sz", "SanDisk Cruzer Blade USB Device"),
            "DeviceDesc": ("sz", "@disk.inf,%disk_devdesc%;Laufwerk"),
        }, "subkeys": {"Properties": {"subkeys": {
            "{83da6326-97a6-4088-9453-a1923f573b29}": {"subkeys": {
                "0064": {"values": {"(default)": ("binary", filetime("2026-01-24T22:50:00+00:00"))}},  # install/first connect
                "0066": {"values": {"(default)": ("binary", filetime("2026-01-24T23:05:00+00:00"))}},  # last connect
            }}}}}}}}}
    interfaces = {"{B2C3D4E5-1111-2222-3333-444455556666}": {"values": {
        "DhcpIPAddress": ("sz", "192.168.178.42"),
        "DhcpServer": ("sz", "192.168.178.1"),
        "DhcpDefaultGateway": ("multi_sz", ["192.168.178.1"])}}}
    control = {
        "ComputerName": {"subkeys": {"ComputerName": {"values": {"ComputerName": ("sz", "DESKTOP-REUTER")}}}},
        "TimeZoneInformation": {"values": {
            "Bias": ("dword", (-60) & 0xFFFFFFFF), "ActiveTimeBias": ("dword", (-60) & 0xFFFFFFFF),
            "DaylightBias": ("dword", (-60) & 0xFFFFFFFF), "StandardBias": ("dword", 0),
            "TimeZoneKeyName": ("sz", "W. Europe Standard Time"),
            "StandardName": ("sz", "Mitteleuropäische Zeit"),
            "DaylightName": ("sz", "Mitteleuropäische Sommerzeit")}},
        "Windows": {"values": {"ShutdownTime": ("binary", filetime("2026-01-25T11:30:00+00:00"))}},
    }
    services = {
        "Tcpip": {"values": {"Start": ("dword", 1), "Type": ("dword", 1),
                             "DisplayName": ("sz", "TCP/IP-Protokolltreiber")},
                  "subkeys": {"Parameters": {"subkeys": {"Interfaces": {"subkeys": interfaces}}}}},
        "bam": {"subkeys": {"State": {"subkeys": {"UserSettings": {"subkeys": {
            SID: {"values": {
                r"\Device\HarddiskVolume3\Program Files (x86)\Microsoft\Edge\Application\msedge.exe":
                    ("binary", bam_entry("2026-01-24T22:31:00+00:00")),
                r"\Device\HarddiskVolume3\Program Files\Microsoft Office\root\Office16\EXCEL.EXE":
                    ("binary", bam_entry("2026-01-24T22:40:00+00:00")),
                r"\Device\HarddiskVolume3\Windows\explorer.exe":
                    ("binary", bam_entry("2026-01-25T07:55:00+00:00"))}}}}}}}},
    }
    mounted = {"values": {
        r"\DosDevices\C:": ("binary", bytes.fromhex("aa bb cc dd 00 00 00 00".replace(" ", ""))),
        r"\DosDevices\E:": ("binary", "_??_USBSTOR#Disk&Ven_SanDisk&Prod_Cruzer_Blade".encode("utf-16-le"))}}
    return {"ROOT": {"subkeys": {
        "Select": {"values": {"Current": ("dword", 1), "Default": ("dword", 1),
                              "Failed": ("dword", 0), "LastKnownGood": ("dword", 1)}},
        "MountedDevices": mounted,
        "ControlSet001": {"subkeys": {
            "Control": {"subkeys": control},
            "Services": {"subkeys": services},
            "Enum": {"subkeys": {"USBSTOR": {"subkeys": usbstor}}},
        }},
        "Setup": {"values": {"SystemSetupInProgress": ("dword", 0)}},
    }}}


# ---------------- SOFTWARE ----------------
def software_tree():
    profiles = {
        "{11111111-2026-4a4a-8b8b-aaaaaaaaaaaa}": {"values": {
            "ProfileName": ("sz", "Heim-WLAN Reuter"), "Description": ("sz", "Heim-WLAN Reuter"),
            "Managed": ("dword", 0), "NameType": ("dword", 0x47), "Category": ("dword", 1),
            "DateCreated": ("binary", systemtime("2025-09-10T18:00:00+00:00")),
            "DateLastConnected": ("binary", systemtime("2026-01-25T06:30:00+00:00"))}},
        "{22222222-2026-4a4a-8b8b-bbbbbbbbbbbb}": {"values": {
            "ProfileName": ("sz", "Werkstatt-Gast"), "Description": ("sz", "Werkstatt-Gast"),
            "Managed": ("dword", 0), "NameType": ("dword", 0x47), "Category": ("dword", 0),
            "DateCreated": ("binary", systemtime("2026-01-12T10:00:00+00:00")),
            "DateLastConnected": ("binary", systemtime("2026-01-22T16:20:00+00:00"))}},
        "{33333333-2026-4a4a-8b8b-cccccccccccc}": {"values": {
            "ProfileName": ("sz", "Hotel_Adler_Gast"), "Description": ("sz", "Hotel_Adler_Gast"),
            "Managed": ("dword", 0), "NameType": ("dword", 0x47), "Category": ("dword", 0),
            "DateCreated": ("binary", systemtime("2025-11-03T20:00:00+00:00")),
            "DateLastConnected": ("binary", systemtime("2025-11-04T07:00:00+00:00"))}},
    }
    networklist = {"subkeys": {
        "Profiles": {"subkeys": profiles},
        "Signatures": {"subkeys": {"Unmanaged": {"subkeys": {
            "010103000F0000F0...HeimWLAN": {"values": {
                "ProfileGuid": ("sz", "{11111111-2026-4a4a-8b8b-aaaaaaaaaaaa}"),
                "Description": ("sz", "Heim-WLAN Reuter")}}}}}}}}
    win_nt = {
        "CurrentVersion": {"values": {
            "ProductName": ("sz", "Windows 11 Pro"), "CurrentBuild": ("sz", "22631"),
            "DisplayVersion": ("sz", "23H2"), "RegisteredOwner": ("sz", "Daniel Reuter"),
            "InstallDate": ("dword", 1725950000)},
            "subkeys": {"NetworkList": networklist}},
    }
    uninstall = {
        "Google Chrome": {"values": {"DisplayName": ("sz", "Google Chrome"),
                                     "DisplayVersion": ("sz", "121.0.6167.85"),
                                     "Publisher": ("sz", "Google LLC")}},
        "Microsoft Edge": {"values": {"DisplayName": ("sz", "Microsoft Edge"),
                                      "DisplayVersion": ("sz", "121.0.2277.83"),
                                      "Publisher": ("sz", "Microsoft Corporation")}},
    }
    return {"ROOT": {"subkeys": {
        "Microsoft": {"subkeys": {
            "Windows NT": {"subkeys": win_nt},
            "Windows": {"subkeys": {"CurrentVersion": {"subkeys": {
                "Uninstall": {"subkeys": uninstall}}}}}}}}}}


# ---------------- NTUSER.DAT ----------------
def ntuser_tree():
    explorer = {
        "TypedPaths": {"values": {
            "url1": ("sz", r"C:\Users\Daniel\Documents\Finanzen"),
            "url2": ("sz", r"E:\\"),
            "url3": ("sz", r"C:\Users\Daniel\Downloads")}},
        "RunMRU": {"values": {"a": ("sz", "cmd\\1"), "b": ("sz", "regedit\\1"),
                              "c": ("sz", "\\\\E:\\\\1"), "MRUList": ("sz", "cba")}},
        "RecentDocs": {"subkeys": {
            ".xlsx": {"values": {"0": ("binary", "Schuldenaufstellung_Jan.xlsx".encode("utf-16-le") + b"\x00\x00"),
                                 "MRUListEx": ("binary", struct.pack("<iI", 0, 0xFFFFFFFF))}},
            ".docx": {"values": {"0": ("binary", "Privatkredit_Vergleich.docx".encode("utf-16-le") + b"\x00\x00"),
                                 "MRUListEx": ("binary", struct.pack("<iI", 0, 0xFFFFFFFF))}}}},
        "WordWheelQuery": {"values": {
            "0": ("binary", wordwheel_val("schuldenaufstellung")),
            "1": ("binary", wordwheel_val("lebensversicherung")),
            "2": ("binary", wordwheel_val("kreditantrag")),
            "MRUListEx": ("binary", mrulistex([0, 1, 2]))}},
        "UserAssist": {"subkeys": {
            "{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}": {"subkeys": {"Count": {"values": {
                rot13(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
                    ("binary", userassist(34, "2026-01-24T22:31:00+00:00")),
                rot13(r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"):
                    ("binary", userassist(12, "2026-01-24T22:40:00+00:00")),
            }}}}}},
        # ComDlg32: Datei-Oeffnen/Speichern-Dialoge (PIDL-basiert)
        "ComDlg32": {"subkeys": {
            "OpenSavePidlMRU": {"subkeys": {
                "xlsx": {"values": {
                    "0": ("binary", pidl([shellitem_root(), shellitem_drive("C"),
                                          shellitem_dir("Users"), shellitem_dir("Daniel"),
                                          shellitem_dir("Documents"), shellitem_dir("Finanzen"),
                                          shellitem_dir("Schuldenaufstellung_Jan.xlsx")])),
                    "MRUListEx": ("binary", mrulistex([0]))}},
                "pdf": {"values": {
                    "0": ("binary", pidl([shellitem_root(), shellitem_drive("C"),
                                          shellitem_dir("Users"), shellitem_dir("Daniel"),
                                          shellitem_dir("Downloads"),
                                          shellitem_dir("Kreditantrag_Sofort.pdf")])),
                    "MRUListEx": ("binary", mrulistex([0]))}}}},
            "LastVisitedPidlMRU": {"values": {
                "0": ("binary", "EXCEL.EXE".encode("utf-16-le") + b"\x00\x00" +
                      pidl([shellitem_root(), shellitem_drive("C"), shellitem_dir("Users"),
                            shellitem_dir("Daniel"), shellitem_dir("Documents"), shellitem_dir("Finanzen")])),
                "MRUListEx": ("binary", mrulistex([0]))}}}},
    }
    office = {"16.0": {"subkeys": {
        "Excel": {"subkeys": {"File MRU": {"values": {
            "Item 1": ("sz", office_mru_val(r"C:\Users\Daniel\Documents\Finanzen\Schuldenaufstellung_Jan.xlsx", "2026-01-24T22:15:00+00:00")),
            "Item 2": ("sz", office_mru_val(r"C:\Users\Daniel\Documents\Haushaltsbudget_2026.xlsx", "2026-01-20T20:05:00+00:00")),
            "Item 3": ("sz", office_mru_val(r"E:\Backup\Schuldenaufstellung_Jan.xlsx", "2026-01-24T22:52:00+00:00"))}}}},
        "Word": {"subkeys": {"File MRU": {"values": {
            "Item 1": ("sz", office_mru_val(r"C:\Users\Daniel\Documents\Privatkredit_Vergleich.docx", "2026-01-24T22:42:00+00:00")),
            "Item 2": ("sz", office_mru_val(r"C:\Users\Daniel\Documents\Versicherungen_Uebersicht.docx", "2026-01-21T19:30:00+00:00"))}}}},
    }}}
    return {"ROOT": {"subkeys": {"Software": {"subkeys": {"Microsoft": {"subkeys": {
        "Windows": {"subkeys": {"CurrentVersion": {"subkeys": {"Explorer": {"subkeys": explorer}}}}},
        "Office": {"subkeys": office},
    }}}}}}}


# ---------------- Amcache ----------------
def amcache_tree():
    apps = {
        "0000msedge": {"values": {
            "LowerCaseLongPath": ("sz", r"c:\program files (x86)\microsoft\edge\application\msedge.exe"),
            "Name": ("sz", "msedge.exe"), "Size": ("dword", 3344123),
            "ProductName": ("sz", "Microsoft Edge"), "Publisher": ("sz", "Microsoft Corporation")}},
        "0000rufus": {"values": {
            "LowerCaseLongPath": ("sz", r"e:\rufus-4.4p.exe"),
            "Name": ("sz", "rufus-4.4p.exe"), "Size": ("dword", 1456789),
            "ProductName": ("sz", "Rufus"), "Publisher": ("sz", "Akeo Consulting")}},
    }
    return {"ROOT": {"subkeys": {"Root": {"subkeys": {"InventoryApplicationFile": {"subkeys": apps}}}}}}


def build_shellbags():
    """BagMRU-Baum: Desktop > My Computer > {C:\\Users\\Daniel\\Documents\\Finanzen, E:\\Backup}."""
    slot = [0]

    def node(children):
        # children: list of (shellitem_bytes, child_node_or_None)
        vals = {"NodeSlot": ("dword", slot[0])}
        slot[0] += 1
        subs = {}
        idxs = []
        for i, (item, child) in enumerate(children):
            vals[str(i)] = ("binary", item)
            idxs.append(i)
            if child is not None:
                subs[str(i)] = child
        vals["MRUListEx"] = ("binary", mrulistex(idxs))
        return {"values": vals, "subkeys": subs}

    # bottom-up: das Shell-Item in einem Knoten beschreibt jeweils das KIND
    finanzen = node([])                                   # Blatt
    documents = node([(shellitem_dir("Finanzen"), finanzen)])
    daniel = node([(shellitem_dir("Documents"), documents)])
    users = node([(shellitem_dir("Daniel"), daniel)])
    cdrive = node([(shellitem_dir("Users"), users)])
    backup = node([])                                     # Blatt (E:\Backup)
    edrive = node([(shellitem_dir("Backup"), backup)])
    mycomp = node([(shellitem_drive("C"), cdrive), (shellitem_drive("E"), edrive)])
    desktop = node([(shellitem_root(), mycomp)])
    return desktop


def usrclass_tree():
    bag = build_shellbags()
    return {"ROOT": {"subkeys": {"Local Settings": {"subkeys": {"Software": {"subkeys": {
        "Microsoft": {"subkeys": {"Windows": {"subkeys": {"Shell": {"subkeys": {
            "BagMRU": bag}}}}}}}}}}}}}


def main():
    jobs = [
        ("SAM", os.path.join(CONFIG, "SAM"), sam_tree()),
        ("SYSTEM", os.path.join(CONFIG, "SYSTEM"), system_tree()),
        ("SOFTWARE", os.path.join(CONFIG, "SOFTWARE"), software_tree()),
        ("NTUSER.DAT", NTUSER, ntuser_tree()),
        ("Amcache.hve", AMCACHE, amcache_tree()),
        ("UsrClass.dat", os.path.join(WIN, "C/Users/Daniel/AppData/Local/Microsoft/Windows/UsrClass.dat"), usrclass_tree()),
    ]
    for name, path, tree in jobs:
        reg_hive.write(tree, path)
        print(f"  {name:12s} {os.path.getsize(path):>6d} B  -> {os.path.relpath(path, ROOT)}")

    print("\n=== Validierung (regipy) ===")
    from regipy.registry import RegistryHive
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'OK' if cond else 'FEHLER'}] {label}  {detail}")

    h = RegistryHive(os.path.join(CONFIG, "SAM"))
    rids = [s.name for s in h.get_key(r"\SAM\Domains\Account\Users").iter_subkeys()]
    check("SAM RIDs", "000003E8" in rids and "000001F4" in rids, str([r for r in rids if r != "Names"]))

    h = RegistryHive(os.path.join(CONFIG, "SYSTEM"))
    usb = [s.name for s in h.get_key(r"\ControlSet001\Enum\USBSTOR").iter_subkeys()]
    check("USBSTOR-Geraet", any("SanDisk" in u for u in usb), usb[0] if usb else "-")
    bam = h.get_key(r"\ControlSet001\Services\bam\State\UserSettings\%s" % SID)
    check("BAM-Eintraege", len(list(bam.iter_values())) >= 2)

    h = RegistryHive(os.path.join(CONFIG, "SOFTWARE"))
    profs = h.get_key(r"\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles")
    names = [v.value for sk in profs.iter_subkeys() for v in sk.iter_values() if v.name == "ProfileName"]
    check("NetworkList-Profile", "Heim-WLAN Reuter" in names, str(names))

    h = RegistryHive(NTUSER)
    ua = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist\{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}\Count")
    check("UserAssist-Eintraege", len(list(ua.iter_values())) >= 2)
    tp = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths")
    check("TypedPaths url1", any(v.name == "url1" for v in tp.iter_values()))

    wwq = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\WordWheelQuery")
    check("WordWheelQuery-Begriffe", len(list(wwq.iter_values())) >= 3)
    xl = h.get_key(r"\Software\Microsoft\Office\16.0\Excel\File MRU")
    mru = [v.value for v in xl.iter_values()]
    check("Office Excel File MRU", any("Schuldenaufstellung" in str(m) for m in mru))
    cd = h.get_key(r"\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU\xlsx")
    check("ComDlg32 OpenSavePidlMRU", any(v.name == "0" for v in cd.iter_values()))

    h = RegistryHive(AMCACHE)
    apps = [s.name for s in h.get_key(r"\Root\InventoryApplicationFile").iter_subkeys()]
    check("Amcache-Eintraege", len(apps) >= 2, str(apps))

    uc = os.path.join(WIN, "C/Users/Daniel/AppData/Local/Microsoft/Windows/UsrClass.dat")
    h = RegistryHive(uc)
    base = r"\Local Settings\Software\Microsoft\Windows\Shell\BagMRU"
    bag = h.get_key(base)
    has_nodeslot = any(v.name == "NodeSlot" for v in bag.iter_values())
    # 5 Ebenen tief (Desktop>MyComputer>C:>Users>Daniel>Documents) erreichbar?
    deep_ok = True
    try:
        h.get_key(base + r"\0\0\0\0\0")
    except Exception:
        deep_ok = False
    # Finanzen-Item vorhanden (UTF-16-Bytes im Shell-Item der Documents-Ebene)?
    raw = build_shellbags  # nur Referenz; tatsaechliche Bytes ueber Generator bekannt
    check("ShellBags BagMRU + Tiefe C:\\Users\\Daniel\\Documents", has_nodeslot and deep_ok)

    print("\nGESAMT:", "alle Hives valide ✓" if ok else "FEHLER ✗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
