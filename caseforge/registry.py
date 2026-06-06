#!/usr/bin/env python3
# =====================================================================
# CaseForge — Generator-Registry
# ---------------------------------------------------------------------
# Zentrales, metadaten-getriebenes Verzeichnis aller Artefakt-Generatoren.
# Jeder Eintrag beschreibt: welche Plattform/OS-Version, welche Artefakt-
# klasse, welche Dateipfade/Formate erzeugt werden und mit welchem
# FORENSIK-TOOL gegengeprueft wird. Daraus erzeugt catalog.py die
# Artefaktuebersicht und forge.py die Build-/Validierungs-Pipeline.
#
# Neue OS-Version -> neues Profil (profiles/) + ggf. neuer/angepasster
# Generator hier registriert. Kein Hardcoding mehr in run_all.
# =====================================================================
from dataclasses import dataclass, field
from typing import List


@dataclass
class Generator:
    id: str
    platform: str                 # ios | android | windows | cloud | crossdevice
    os_min: str                   # z.B. "ios>=16", "android>=12", "win>=10", "*"
    module: str                   # Generator-Skript in 09_build/generators
    artifact_classes: List[str]   # logische Klassen (messaging, browser, registry, ...)
    produces: List[str]           # Pfad-Muster (relativ zum Geraete-FS)
    fmt: str                      # sqlite | regf | evtx | plist | json | xml | binxml | media | text
    parser: str                   # Forensik-Tool zur Gegenpruefung
    validator: str = ""           # CaseForge-Gate-Skript (validate_*.py)
    relevance_capable: bool = True
    notes: str = ""


# ---------------------------------------------------------------------
# REGISTRY  (Stand: Operation Waldweg Referenz-Fall)
# ---------------------------------------------------------------------
REGISTRY: List[Generator] = [
    # ---- iOS ----
    Generator("ios.sms", "ios", "ios>=14", "gen_ios_sms.py", ["messaging"],
              ["private/var/mobile/Library/SMS/sms.db"], "sqlite", "iLEAPP (iMessage)", "validate_ios.py",
              notes="WAL-Fragment fuer geloeschte Nachricht (PI#4)"),
    Generator("ios.photos_health", "ios", "ios>=15", "gen_ios_photos_health.py", ["media", "health"],
              ["private/var/mobile/Media/PhotoData/Photos.sqlite",
               "private/var/mobile/Library/Health/healthdb_secure.sqlite"], "sqlite",
              "iLEAPP (Photos/Health)", "validate_ios.py"),
    Generator("ios.location", "ios", "ios>=14", "gen_ios_location.py", ["location"],
              ["private/var/mobile/Library/Caches/locationd/cache_encryptedB.db"], "sqlite",
              "iLEAPP (LocationD)", "validate_ios.py"),
    Generator("ios.whatsapp", "ios", "ios>=15", "gen_ios_whatsapp.py", ["messaging"],
              ["...57T9237FN3~net~whatsapp~WhatsApp/ChatStorage.sqlite"], "sqlite",
              "iLEAPP (WhatsApp)", "validate_ios.py"),
    Generator("ios.biome", "ios", "ios>=17", "gen_biome.py", ["activity", "browser", "device_state"],
              ["private/var/db/biome/streams/restricted/*"], "binxml", "BIOME-Stream-Analyzer (mb4n6)",
              "gen_biome.py", notes="SEGB v2; ersetzt knowledgeC.db ab iOS 17"),
    Generator("ios.knowledgec", "ios", "ios<=16", "gen_ios_knowledgec.py", ["activity"],
              ["private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db"], "sqlite",
              "iLEAPP / APOLLO (knowledgeC)", "validate_ios.py",
              notes="NUR <= iOS 16 (Profil-Flag knowledgec); ab iOS 17 -> BIOME"),
    Generator("ios.extra", "ios", "ios>=15", "gen_ios_extra.py", ["browser", "calls", "snapshots"],
              ["...Library/Safari/History.db", "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata",
               "private/var/mobile/Library/Voicemail/voicemail.db",
               "private/var/mobile/Library/Caches/Snapshots/*"], "sqlite/plist/media",
              "iLEAPP (Safari/CallHistory)", "validate_ios.py"),
    Generator("ios.apps", "ios", "ios>=14", "gen_app_skeletons.py", ["app_sandbox"],
              ["private/var/mobile/Containers/Data/Application/<GUID>/*"], "plist/sqlite",
              "iLEAPP (App-Mapping)", "validate_apps.py", notes="Skelette + teils Inhalt"),

    # ---- Android ----
    Generator("android.core", "android", "android>=12", "gen_android.py", ["messaging", "calls", "contacts", "browser"],
              ["data/data/com.android.providers.telephony/databases/mmssms.db",
               "data/data/com.whatsapp/databases/msgstore.db",
               "data/data/com.android.chrome/app_chrome/Default/History"], "sqlite",
              "ALEAPP", "validate_android.py"),
    Generator("android.location", "android", "android>=12", "gen_android_location.py", ["location"],
              ["data/data/com.google.android.gms/databases/location_cache.db"], "sqlite",
              "ALEAPP (Loc)", "validate_android.py", notes="PI#1 WiFi vs. Cell"),
    Generator("android.extra", "android", "android>=12", "gen_android_extra.py",
              ["usage", "health", "maps", "accounts"],
              ["data/system/usagestats/*", "data/data/com.sec.android.app.shealth/databases/*",
               "data/data/com.google.android.apps.maps/databases/*",
               "data/system/sync/accounts.xml"], "sqlite/xml", "ALEAPP", "validate_android.py"),
    Generator("android.scoped", "android", "android>=11", "gen_android_scoped.py", ["storage", "media"],
              ["data/data/com.google.android.providers.media.module/databases/external.db"], "sqlite",
              "ALEAPP (MediaStore)", "validate_android.py",
              notes="Scoped-Storage external.db (Profil-Flag scoped_storage); module- vs legacy-Pfad"),
    Generator("android.apps", "android", "android>=12", "gen_app_skeletons.py", ["app_sandbox"],
              ["data/data/<pkg>/{shared_prefs,databases}"], "xml/sqlite", "ALEAPP", "validate_apps.py"),

    # ---- Windows ----
    Generator("win.hives", "windows", "win>=10", "gen_win_hives.py", ["registry"],
              ["C/Windows/System32/config/{SAM,SYSTEM,SOFTWARE}", "C/Users/<U>/NTUSER.DAT",
               "C/Windows/AppCompat/Programs/Amcache.hve",
               "C/Users/<U>/AppData/Local/Microsoft/Windows/UsrClass.dat"], "regf",
              "RegRipper (samparse/compname/timezone/usbstor/bam/networklist/userassist/shellbags/amcache)",
              "validate_windows.py"),
    Generator("win.files", "windows", "win>=10", "gen_win_artifacts.py", ["recyclebin", "setupapi", "tasks", "prefetch"],
              ["C/$Recycle.Bin/<SID>/$I*", "C/Windows/INF/setupapi.dev.log",
               "C/Windows/System32/Tasks/*", "C/Windows/Prefetch/*.pf"], "binary/text/xml",
              "RBCmd / Texteditor", "validate_windows.py", notes="Prefetch = Platzhalter (kein SCCA)"),
    Generator("win.browser", "windows", "win>=10", "gen_win_browser.py", ["browser"],
              ["C/Users/<U>/AppData/Local/Microsoft/Edge/User Data/Default/{History,Bookmarks,Web Data,Login Data}"],
              "sqlite/json", "Hindsight / DB-Browser", "validate_windows.py"),
    Generator("win.extra", "windows", "win>=10", "gen_win_extra.py", ["powershell", "notifications"],
              ["...PSReadline/ConsoleHost_history.txt", "...Notifications/wpndatabase.db"], "text/sqlite",
              "Texteditor / SQLite", "validate_windows.py"),
    Generator("win.lnk", "windows", "win>=10", "gen_win_lnk.py", ["shortcuts"],
              ["C/Users/<U>/AppData/Roaming/Microsoft/Windows/Recent/*.lnk"], "shelllink",
              "LECmd / LnkParse3", "validate_windows.py"),
    Generator("win.evtx", "windows", "win>=10", "gen_win_evtx.py", ["eventlog"],
              ["C/Windows/System32/winevt/Logs/{Security,System}.evtx"], "evtx",
              "EvtxECmd / python-evtx", "validate_windows.py", notes="template-basiertes BinXML"),
    Generator("win.mft", "windows", "win>=10", "gen_win_mft.py", ["filesystem"],
              ["C/$MFT"], "ntfs-mft", "MFTECmd / analyzeMFT", "validate_windows.py",
              notes="FILE-Records mit Fixups + $SI/$FN (Profil-Flag mft); inkl. geloeschter Datei"),
    Generator("win.srum", "windows", "win>=10", "gen_win_srum.py", ["telemetry"],
              ["C/Windows/System32/sru/SRUDB.dat"], "ese-stub", "SrumECmd / esedbexport",
              "validate_windows.py", notes="ESE-Header-Stub (Profil-Flag srum); kein voll-faithful ESE"),
    Generator("win.usnjrnl", "windows", "win>=10", "gen_win_usnjrnl.py", ["filesystem"],
              ["C/$Extend/$UsnJrnl_$J"], "ntfs-usn", "MFTECmd ($J) / UsnJrnl2Csv",
              "validate_windows.py", notes="USN_RECORD_V2 (Profil-Flag usnjrnl)"),
    # win.hives erzeugt zusaetzlich ShimCache/AppCompatCache im SYSTEM-Hive (Profil-Flag shimcache).

    # ---- weitere iOS/Android (profilgesteuert) ----
    Generator("ios.powerlog", "ios", "ios>=14", "gen_ios_powerlog.py", ["activity", "power"],
              ["private/var/mobile/Library/BatteryLife/CurrentPowerlog.PLSQL"], "sqlite",
              "iLEAPP (Powerlog)", "validate_ios.py", notes="Profil-Flag powerlog"),
    Generator("android.system", "android", "android>=12", "gen_android_system.py", ["system"],
              ["data/system/netpolicy.xml", "data/system_ce/0/recent_tasks/*"], "xml/abx",
              "ALEAPP", "validate_android.py", notes="Profil-Flags netpolicy/recent_tasks"),

    # ---- Cloud / Cross-device ----
    Generator("cloud.exports", "cloud", "*", "gen_cloud.py", ["cloud_location", "cloud_sync"],
              ["google/location-history.json", "icloud/icloud_sync.csv"], "json/csv",
              "Manuell / JSON-Viewer", "verify_solution.py", notes="PI#5 Sync-Luecke"),
    Generator("media.embed", "crossdevice", "*", "embed_media.py", ["media_placement"],
              ["<geraet>/<realistische Medienpfade>", "05_police_records/*"], "media",
              "—", relevance_capable=False, notes="bettet Bild/Audio/Video schluessig ins FS ein"),
    Generator("docs.noise", "crossdevice", "*", "gen_documents.py", ["documents"],
              ["<Downloads>/<Dokumente> je Geraet"], "pdf/docx/xlsx/csv/txt", "Office/Viewer",
              notes="Alltagsdokumente (Noise + dezent relevant)"),
    Generator("correlate", "crossdevice", "*", "correlate.py", ["timeline"],
              ["08_master/Master_Timeline.csv"], "csv", "—", relevance_capable=False,
              notes="vereinheitlichte geraeteuebergreifende Zeitleiste"),
]


def by_platform(platform=None):
    return [g for g in REGISTRY if platform is None or g.platform == platform]


def select_for_spec(spec: dict):
    """Waehlt Generator-Module anhand eines Case-Specs aus.
    - Plattformen aus spec.devices[].platform
    - je Geraet optional artifact_classes -> nur passende Generatoren der Plattform
    - crossdevice/cloud werden immer beruecksichtigt (gefiltert auf gewuenschte Klassen)
    Gibt geordnete, eindeutige Modul-Liste in REGISTRY-Reihenfolge zurueck.
    """
    devices = spec.get("devices", [])
    plats = {d.get("platform") for d in devices if d.get("platform")}
    # gewuenschte Klassen je Plattform (leer = alle)
    want = {}
    for d in devices:
        p = d.get("platform")
        cls = set(d.get("artifact_classes", []) or [])
        want.setdefault(p, set())
        want[p] |= cls
    modules, seen = [], set()
    for g in REGISTRY:
        take = False
        if g.platform in plats:
            wc = want.get(g.platform, set())
            take = (not wc) or bool(set(g.artifact_classes) & wc)
        elif g.platform in ("crossdevice", "cloud"):
            take = True   # Querschnitt immer (Timeline/Cloud/Doku/Medien)
        if take and g.module not in seen:
            seen.add(g.module); modules.append(g.module)
    return modules


def parsers():
    return sorted({g.parser for g in REGISTRY if g.parser and g.parser != "—"})


def artifact_classes():
    cs = set()
    for g in REGISTRY:
        cs.update(g.artifact_classes)
    return sorted(cs)
