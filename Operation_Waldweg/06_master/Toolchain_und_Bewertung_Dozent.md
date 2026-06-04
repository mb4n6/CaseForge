# Operation Waldweg — Toolchain-Anleitung & Bewertungsraster (Dozierende)

> Begleitdokument zum Lösungsschlüssel. Enthält die lokale Werkzeug-Anleitung und das Bewertungsraster.

---

## 1. Lokale Validierungs-Toolchain

Die Artefakte wurden so erzeugt, dass die gängigen Open-Source-Forensiktools sie **out of the box** parsen. Empfohlener lokaler Aufbau (Python 3.10+):

### 1.1 iLEAPP (iOS) — Asservat A1
```bash
git clone https://github.com/abrignoni/iLEAPP.git
cd iLEAPP && pip install -r requirements.txt
python ileapp.py -t fs -i <Pfad>/01_ios_full_fs -o <Ausgabe>
```
Relevante Module: **iMessage/SMS** (`sms.db`), **Apple Health** (`healthdb_secure.sqlite`), **Photos** (`Photos.sqlite`). BIOME-Streams: separat mit dem **BIOME-Stream-Analyzer** (siehe 1.4).

### 1.2 ALEAPP (Android) — Asservat A2
```bash
git clone https://github.com/abrignoni/ALEAPP.git
cd ALEAPP && pip install -r requirements.txt
python aleapp.py -t fs -i <Pfad>/02_android_full_fs -o <Ausgabe>
```
Relevante Module: **Calls** (`calllog.db`), **SMS/MMS** (`mmssms.db`), **WhatsApp** (`msgstore.db`, modernes Schema), **Chrome** (`History`).

### 1.3 regipy (Windows-Registry) — Asservat A3
```bash
pip install regipy
regipy-dump <Pfad>/03_windows_triage/C/Users/Daniel/NTUSER.DAT
```
Edge-History (`…/Edge/User Data/Default/History`) öffnet jeder SQLite-Viewer; Zeitstempel = WebKit-µs (seit 1601).

**System-Hives mit RegRipper** (`C/Windows/System32/config/{SAM,SYSTEM,SOFTWARE}`, `Amcache.hve`, `NTUSER.DAT`):
```bash
# SAM
rip.pl -r .../config/SAM      -p samparse     # Konten: Administrator RID500, Daniel RID1000
# SYSTEM
rip.pl -r .../config/SYSTEM   -p compname      # DESKTOP-REUTER
rip.pl -r .../config/SYSTEM   -p timezone      # W. Europe Standard Time
rip.pl -r .../config/SYSTEM   -p shutdown      # letzter Shutdown 25.01
rip.pl -r .../config/SYSTEM   -p usbstor       # SanDisk Cruzer Blade (USB)
rip.pl -r .../config/SYSTEM   -p mountdev      # MountedDevices (C:, E:=USB)
rip.pl -r .../config/SYSTEM   -p bam           # Last-Execution: msedge/EXCEL/explorer
# SOFTWARE
rip.pl -r .../config/SOFTWARE -p networklist   # WLANs: Heim-WLAN Reuter, Werkstatt-Gast, Hotel
rip.pl -r .../config/SOFTWARE -p winver        # Windows 11 Pro 23H2
# NTUSER (Benutzeraktivitaet)
rip.pl -r .../Daniel/NTUSER.DAT -p userassist  # Ausfuehrung msedge/EXCEL + Zeit
rip.pl -r .../Daniel/NTUSER.DAT -p recentdocs  # zuletzt: Schuldenaufstellung.xlsx, Privatkredit.docx
rip.pl -r .../Daniel/NTUSER.DAT -p runmru      # ausgefuehrte Run-Befehle
# Amcache
rip.pl -r .../Programs/Amcache.hve -p amcache  # msedge.exe, rufus-4.4p.exe (USB-Tool)
# NTUSER weitere
rip.pl -r .../Daniel/NTUSER.DAT -p wordwheelquery  # Explorer-Suchen: schuldenaufstellung, lebensversicherung
rip.pl -r .../Daniel/NTUSER.DAT -p recentdocs       # zuletzt geoeffnete Dokumente
# ShellBags (UsrClass.dat)
rip.pl -r .../Local/Microsoft/Windows/UsrClass.dat -p shellbags  # C:\...\Finanzen, E:\Backup
# Office File MRU / ComDlg32 (NTUSER)
rip.pl -r .../Daniel/NTUSER.DAT -p officedocs   # zuletzt geoeffnete Office-Dateien (auch E:\Backup)
rip.pl -r .../Daniel/NTUSER.DAT -p comdlg32     # Datei-Oeffnen/Speichern-Dialoge
```
**Event Logs (`C/Windows/System32/winevt/Logs/*.evtx`)** — EvtxECmd / python-evtx / Event Viewer:
```bash
EvtxECmd.exe -f .../Logs/Security.evtx --csv out   # 4624 Anmeldung Daniel 06:40, 4634 Abmeldung
EvtxECmd.exe -f .../Logs/System.evtx   --csv out   # 6005 Boot, 6006 Shutdown 12:30
```
Template-basiertes BinXML; mit `python-evtx` verifiziert (EventID/EventData rendern, Record-FILETIME korrekt).

**Weitere parsebare Artefakte (nicht RegRipper):**
- Edge `History` (downloads-Tabelle), `Bookmarks` (JSON), `Web Data`/`Login Data` (SQLite) — Hindsight/DB-Browser.
- LNK in `Recent\` — LECmd / `LnkParse3` (lokal mit `LnkParse3` verifiziert).
- `ConsoleHost_history.txt` (PowerShell) — Texteditor; enthält Wipe-/Backup-Befehlskette.
- `wpndatabase.db` (Toasts) — SQLite.
Datei-Artefakte: Papierkorb `$Recycle.Bin/<SID>/$I*` (RBCmd; gelöschte `Schuldenaufstellung_Jan.xlsx`), `Windows/INF/setupapi.dev.log` (USB-Install 24.01), `System32/Tasks/BackupFinanzen` (robocopy → USB), `*.Zone.Identifier` (Download-Herkunft). Übersicht: `06_master/Windows_Artefakte_Manifest.csv`. (Alle Hives auch mit regipy lesbar — `validate_windows.py`.)

### 1.4 BIOME-Stream-Analyzer (mb4n6) — iOS-Aktivität
```bash
git clone https://github.com/mb4n6/BIOME-Stream-Analyzer.git
python biome_analyzer.py <Pfad>/01_ios_full_fs/private/var/db/biome/streams/restricted/_DKEvent.Safari.History/local/*
```
Streams sind SEGB-v2 (CRC32-geprüft); alle Frames müssen `crc_ok` liefern.

### 1.5 Schnell-Abnahme ohne Toolinstallation
Im Repo liegen Abnahme-Skripte, die die Tool-Logik replizieren bzw. echte Parser nutzen:
```bash
cd Operation_Waldweg/09_build/generators
python run_all.py      # führt alle Gates + Lösbarkeitsprüfung aus
```
**Erwartetes Ergebnis: „ALLE GATES BESTANDEN ✓"** (BIOME-, Cloud-, iOS-, Android-, Windows-Gate; **12/12 Lösbarkeitsprüfungen**, inkl. PI#1 und PI#5). Die vereinheitlichte `06_master/Master_Timeline.csv` umfasst **108 Ereignisse**.

### 1.6 Weitere Asservate
- **Standort-DBs:** iOS `cache_encryptedB.db` (Tabellen `CellLocation`/`WifiLocation`, iLEAPP-Modul „LocationD") und Android `location_cache.db` (`wifi_assoc`/`network_location_cache`) → tragen PI#1.
- **Cloud (`04_cloud_exports/`):** Google-Takeout `location-history.json` (JSON, `latitudeE7`/`longitudeE7`, UTC) und iCloud `icloud_sync.csv` → PI#5.
- **WhatsApp:** iOS `ChatStorage.sqlite` (Core-Data: `ZWAMESSAGE`/`ZWAGROUPMEMBER`) **und** Android `msgstore.db` (`message`/`chat`/`jid`, inkl. Gruppen).
- **Dokumente:** PDF/DOCX/XLSX/CSV/TXT in Downloads/Dokumente je Gerät — Standard-Viewer/Office; Übersicht in `06_master/Dokumente_Manifest.csv`.
- **Registry:** `NTUSER.DAT` (TypedPaths) sowie System-Hives `SAM`/`SYSTEM` unter `…/config/` — RegRipper/regipy.
- **Multimedia (`07_multimedia/`)** und **Mehrsprachiges (`08_multilingual/`)** — siehe jeweilige README/Metadaten.

### 1.7 Bekannte Grenzen (Windows)
Aus Aufwands-/Werkzeuggründen **nicht** als valide Binärformate enthalten (dokumentierte Folgearbeit): `SRUDB.dat` (ESE), NTFS-Strukturen `$MFT`/`$UsnJrnl`/`$LogFile`, ShimCache/AppCompatCache sowie **valides Prefetch (SCCA)** — die `*.pf` sind nur korrekt benannte Platzhalter. Die übrigen Registry- und Datei-Artefakte tragen die Windows-Beweislast.

## 2. Zeitstempel-Spickzettel (für die Korrektur)

| Format | Vorkommen | Umrechnung nach UTC |
|--------|-----------|---------------------|
| Apple-Nanosekunden | iOS `sms.db.date` | `epoch2001 + ns/1e9` |
| Apple-CFAbsoluteTime (s) | Health, Photos, BIOME | `epoch2001 + s` |
| Unix-Millisekunden | Android Telephony/Calllog/WhatsApp | `ms/1000` |
| WebKit-Mikrosekunden | Chrome/Edge `last_visit_time` | `1601 + µs` |
| ISO 8601 (UTC, „Z") | Google Takeout, iCloud-Sync | direkt; CET = UTC+1 beachten |

(`epoch2001` = 2001-01-01Z = Unix 978307200; WebKit-Offset = 11644473600 s.)

## 3. Bewertungsraster (100 Punkte)

| Kriterium | Punkte | Erwartung |
|-----------|-------:|-----------|
| **Zeitleisten-Rekonstruktion** | 20 | Geräteübergreifend, korrekte Zeitzonen-/Format-Umrechnung, plausible Lücken benannt |
| **Korrekte Tatzeit-Eingrenzung** | 10 | Health-Messende 07:50 + Obduktionsfenster sauber verknüpft |
| **Kommunikationsanalyse** | 15 | Relevante Chats/Anrufe identifiziert; gelöschte iMessage als WAL-Fragment erkannt |
| **Quellenkritik / Widersprüche** | 20 | Mind. 2 Konflikte aufgelöst (WiFi vs. Cell; Zeuge vs. Gerät; HR-Peak mehrdeutig) |
| **Bewertung der Verdächtigen** | 15 | Jonas & Tobias begründet entlastet; Daniel als Haupthypothese mit Belegen |
| **Methodik & Nachvollziehbarkeit** | 10 | Tools, Hashes, Chain-of-Custody-Logik dokumentiert |
| **Berichtsqualität** | 10 | Struktur, Belege je Aussage, klare Sprache |

### Muss-Kriterien für „bestanden"
- Haupthypothese **Daniel** mit mindestens drei geräteübergreifenden Belegen.
- Beide Red Herrings (Jonas, Tobias) korrekt entlastet.
- Mindestens **ein** Quellenkonflikt sauber argumentiert.

### Häufige Fehler (Punktabzug)
- Zeugenaussage „kurz nach acht" überbewertet (PI#2).
- WLAN-Assoziation „Home" als Aufenthaltsbeweis gewertet (PI#1).
- HR-Peak vorschnell als Gewalt **oder** als Sport gedeutet ohne Kontext (PI#3).
- Cloud-Sync-Lücke als „war nicht dort" fehlinterpretiert (PI#5).
