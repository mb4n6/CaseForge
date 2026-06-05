# Artefakt-Katalog

> Generiert von CaseForge aus der Generator-Registry.


## iOS (iPhone)

| Artefaktklasse | Format | Pfade | Forensik-Tool (Gegenpruefung) | Generator |
|---|---|---|---|---|
| messaging | sqlite | private/var/mobile/Library/SMS/sms.db | iLEAPP (iMessage) | `gen_ios_sms.py` |
| media, health | sqlite | private/var/mobile/Media/PhotoData/Photos.sqlite ; private/var/mobile/Library/Health/healthdb_secure.sqlite | iLEAPP (Photos/Health) | `gen_ios_photos_health.py` |
| location | sqlite | private/var/mobile/Library/Caches/locationd/cache_encryptedB.db | iLEAPP (LocationD) | `gen_ios_location.py` |
| messaging | sqlite | ...57T9237FN3~net~whatsapp~WhatsApp/ChatStorage.sqlite | iLEAPP (WhatsApp) | `gen_ios_whatsapp.py` |
| activity, browser, device_state | binxml | private/var/db/biome/streams/restricted/* | BIOME-Stream-Analyzer (mb4n6) | `gen_biome.py` |
| browser, calls, snapshots | sqlite/plist/media | ...Library/Safari/History.db ; private/var/mobile/Library/CallHistoryDB/CallHistory.storedata ; private/var/mobile/Library/Voicemail/voicemail.db ; private/var/mobile/Library/Caches/Snapshots/* | iLEAPP (Safari/CallHistory) | `gen_ios_extra.py` |
| app_sandbox | plist/sqlite | private/var/mobile/Containers/Data/Application/<GUID>/* | iLEAPP (App-Mapping) | `gen_app_skeletons.py` |

## Android (Samsung)

| Artefaktklasse | Format | Pfade | Forensik-Tool (Gegenpruefung) | Generator |
|---|---|---|---|---|
| messaging, calls, contacts, browser | sqlite | data/data/com.android.providers.telephony/databases/mmssms.db ; data/data/com.whatsapp/databases/msgstore.db ; data/data/com.android.chrome/app_chrome/Default/History | ALEAPP | `gen_android.py` |
| location | sqlite | data/data/com.google.android.gms/databases/location_cache.db | ALEAPP (Loc) | `gen_android_location.py` |
| usage, health, maps, accounts | sqlite/xml | data/system/usagestats/* ; data/data/com.sec.android.app.shealth/databases/* ; data/data/com.google.android.apps.maps/databases/* ; data/system/sync/accounts.xml | ALEAPP | `gen_android_extra.py` |
| app_sandbox | xml/sqlite | data/data/<pkg>/{shared_prefs,databases} | ALEAPP | `gen_app_skeletons.py` |

## Windows (Notebook)

| Artefaktklasse | Format | Pfade | Forensik-Tool (Gegenpruefung) | Generator |
|---|---|---|---|---|
| registry | regf | C/Windows/System32/config/{SAM,SYSTEM,SOFTWARE} ; C/Users/<U>/NTUSER.DAT ; C/Windows/AppCompat/Programs/Amcache.hve ; C/Users/<U>/AppData/Local/Microsoft/Windows/UsrClass.dat | RegRipper (samparse/compname/timezone/usbstor/bam/networklist/userassist/shellbags/amcache) | `gen_win_hives.py` |
| recyclebin, setupapi, tasks, prefetch | binary/text/xml | C/$Recycle.Bin/<SID>/$I* ; C/Windows/INF/setupapi.dev.log ; C/Windows/System32/Tasks/* ; C/Windows/Prefetch/*.pf | RBCmd / Texteditor | `gen_win_artifacts.py` |
| browser | sqlite/json | C/Users/<U>/AppData/Local/Microsoft/Edge/User Data/Default/{History,Bookmarks,Web Data,Login Data} | Hindsight / DB-Browser | `gen_win_browser.py` |
| powershell, notifications | text/sqlite | ...PSReadline/ConsoleHost_history.txt ; ...Notifications/wpndatabase.db | Texteditor / SQLite | `gen_win_extra.py` |
| shortcuts | shelllink | C/Users/<U>/AppData/Roaming/Microsoft/Windows/Recent/*.lnk | LECmd / LnkParse3 | `gen_win_lnk.py` |
| eventlog | evtx | C/Windows/System32/winevt/Logs/{Security,System}.evtx | EvtxECmd / python-evtx | `gen_win_evtx.py` |

## Cloud

| Artefaktklasse | Format | Pfade | Forensik-Tool (Gegenpruefung) | Generator |
|---|---|---|---|---|
| cloud_location, cloud_sync | json/csv | google/location-history.json ; icloud/icloud_sync.csv | Manuell / JSON-Viewer | `gen_cloud.py` |

## Geraeteuebergreifend

| Artefaktklasse | Format | Pfade | Forensik-Tool (Gegenpruefung) | Generator |
|---|---|---|---|---|
| media_placement | media | <geraet>/<realistische Medienpfade> ; 05_police_records/* | — | `embed_media.py` |
| documents | pdf/docx/xlsx/csv/txt | <Downloads>/<Dokumente> je Geraet | Office/Viewer | `gen_documents.py` |
| timeline | csv | 08_master/Master_Timeline.csv | — | `correlate.py` |

## Forensik-Tools zur Gegenpruefung

- ALEAPP
- ALEAPP (Loc)
- BIOME-Stream-Analyzer (mb4n6)
- EvtxECmd / python-evtx
- Hindsight / DB-Browser
- LECmd / LnkParse3
- Manuell / JSON-Viewer
- Office/Viewer
- RBCmd / Texteditor
- RegRipper (samparse/compname/timezone/usbstor/bam/networklist/userassist/shellbags/amcache)
- Texteditor / SQLite
- iLEAPP (App-Mapping)
- iLEAPP (LocationD)
- iLEAPP (Photos/Health)
- iLEAPP (Safari/CallHistory)
- iLEAPP (WhatsApp)
- iLEAPP (iMessage)
