# Analyse: Fall-Variabilität, Umfangssteuerung, Artefakt-Anreicherung & OS-Profile

**CaseForge / Operation Waldweg · Verfasser-Kontext: Marc Brandt · Stand: 2026**

Diese Analyse beantwortet vier Fragen: (1) Wo erzeugt das Framework heute *immer dieselben*
Artefakte? (2) Wie lässt sich **Zufälligkeit** einführen, ohne die Fall-Konsistenz zu
verlieren? (3) Wie lässt sich **Umfang/Noise** je Fall auswählen? (4) Welche **weiteren
Artefakte** und **OS-Profile** sind sinnvoll, versionstypisch begründet?

---

## 1. Bestandsaufnahme — was macht Fälle aktuell „gleich"?

Befund aus der Code-Analyse:

- **`generator_seed` wird nirgends gelesen.** Im gesamten `09_build/generators/` gibt es **kein
  `import random`** und keine seed-basierte Variation. Inhalte stammen aus dem Master, aber alle
  *Strukturmerkmale* sind hart kodiert.
- **Feste Identifikatoren über alle Fälle hinweg:**
  - App-Container-GUIDs werden aus einem **festen SEED `"20260125"`** per MD5 abgeleitet
    (`gen_app_skeletons.py`) → jeder Fall hat *identische* Container-UUIDs.
  - Windows: **feste SID** `S-1-5-21-1004336348-…-1000`, fester Rechnername **`DESKTOP-REUTER`**,
    fester Benutzer `Daniel`.
  - iOS: fester WhatsApp-App-Group-Container `57T9237FN3~net~whatsapp~WhatsApp`, feste
    `account_id`-Schemata.
  - Telefonnummern, IMEI/Seriennummern, BSSIDs, Zell-IDs: feste Fallback-Werte.
- **Feste Mengen/Layouts:** Noise-Listen (SMS, Anrufe, Chrome-URLs, Dokumente, Gruppen-Mitglieder)
  haben *feste Längen und feste Texte*; App-Set ist eine feste Liste; Zeitstempel hängen am
  festen Fokusfenster.
- **Generatoren verzweigen kaum nach OS-Profil.** Das Profil liefert Faktentext, aber z. B.
  `gen_biome.py` baut BIOME unabhängig von der iOS-Version; für iOS < 17 gibt es keinen
  `knowledgeC.db`-Pfad. Profile sind heute *dokumentarisch*, nicht *steuernd*.

**Konsequenz:** Selbst mit unterschiedlichem Spec-Inhalt sind zwei Fälle an GUIDs, SID,
Rechnername, Containerpfaden, Mengengerüst und Zeitachse als „dasselbe Skelett" erkennbar — für
die Ausbildung ungünstig (Wiedererkennungseffekt, Lösungen kursieren).

---

## 2. Frage A — Mehr Zufälligkeit (machbar, empfohlen)

**Machbar und mit dem Determinismus vereinbar.** Der Schlüssel ist *seed-gesteuerte*
Pseudo-Zufälligkeit: ein einziger `meta.generator_seed` speist einen zentralen RNG. Gleicher
Seed ⇒ gleicher Fall (Reproduzierbarkeit, A3 bleibt erhalten); neuer Seed ⇒ individueller Fall.
Wichtig ist die Trennung in **zwei Klassen**:

**Frei randomisierbar (verändert die Lösung nicht):**

| Merkmal | Heute fix | Vorschlag |
|---|---|---|
| App-Container-GUIDs | MD5 von festem SEED | MD5 von `seed`+Bundle → pro Fall andere UUIDs |
| Windows SID / RID | fest | seed-abgeleitete, valide SID/RIDs |
| Rechnername, Benutzerprofil-Pfad | `DESKTOP-REUTER`/`Daniel` | aus Personen-Spec + seed (`DESKTOP-XXXXX`) |
| IMEI/Serial/BSSID/Zell-IDs/Ports | fest | seed-zufällig, formatgültig (Luhn-IMEI etc.) |
| WhatsApp-App-Group-Hash | fest | seed-abgeleitet |
| Reihenfolge & Anzahl der Noise-Einträge | fest | seed-permutiert, Anzahl in Spanne (s. §3) |
| Zeit-Jitter (Sekunden/Minuten) | exakt | ±Jitter um Sollzeit, Reihenfolge bleibt |
| Pfad-Varianten (z. B. `108APPLE` DCIM-Ordner) | fest | seed-variiert im gültigen Rahmen |

**Bewusst *nicht* randomisieren (fall- und lösungstragend):** kausale Timeline-Reihenfolge,
geplante Widersprüche, Inhalte aus dem Spec (Nachrichten, Standortspur, Lösungsschlüssel),
schema-tragende Strukturen. Diese kommen weiterhin deterministisch aus dem Master.

**Umsetzungsskizze:** ein Modul `caseforge_rng.py` mit `rng(seed)` + Helfern (`pick`, `jitter`,
`fake_imei`, `fake_sid`, `fake_guid`, `shuffle`). Generatoren ziehen daraus statt aus Konstanten;
`forge.py build` erzeugt bei fehlendem Seed automatisch einen und schreibt ihn in den Fall
(`generator_seed`), damit der Fall reproduzierbar bleibt. Aufwand: mittel, klar abgrenzbar.

---

## 3. Frage B — Umfang & Noise auswählen (machbar, empfohlen)

Heute steuert `artifact_classes` *welche* Generatoren laufen, aber nicht *wie viel*. Vorschlag:
**zwei Stellschrauben im Spec**, beide optional mit sinnvollen Defaults.

1. **Fallumfang als Preset** — `meta.scope: S | M | L | XL` (klein → sehr groß). Skaliert die
   Noise-Mengen multiplikativ (z. B. Anzahl Alltags-SMS, Browser-URLs, Dokumente, Foto-Bursts,
   App-Sandboxen, Kalendereinträge). „S" = schlanker Übungsfall, „XL" = realitätsnaher
   Großdatenbestand.
2. **Feinsteuerung pro Klasse** — `volume: {documents: 25, browser_noise: 40, sms_noise: 200, …}`
   überschreibt das Preset gezielt. Plus `noise_density` (0.0–1.0) als globaler Regler
   „fallrelevant ↔ verrauscht".

Dazu eine **Mengen-Bibliothek** (`noise_pools.py`): kuratierte, sprach-lokalisierte Pools für
Alltags-SMS, Webseiten, Dateinamen, App-Listen, Kontaktnamen. Der seed-RNG zieht daraus *n*
Einträge ohne Wiederholung → jeder Fall andere, aber plausible Noise-Spuren. Das verbindet
direkt mit §2 (Variabilität) und liefert den eigentlichen „Individualitäts"-Effekt.

**Wirkung:** `forge.py build --scope L` o. ä. erlaubt, denselben Plot als 15-Minuten-Übung (S)
oder als forensischen Großfall (XL) auszuspielen — gleiche Lösung, anderer Aufwand.

---

## 4. Frage A' — Weitere Artefakte anreichern (sinnvoll; priorisiert)

Lohnend, weil sie reale, prüfbare Spuren mit hohem didaktischem Wert ergänzen. Geordnet nach
Nutzen/Aufwand:

**Windows (hoher Nutzen):**
- **PCA — Program Compatibility Assistant** (`%WinDir%\appcompat\pca\PcaAppLaunchDic.txt`,
  `PcaGeneralDb*.txt`): textbasierte Ausführungsspuren **neu ab Windows 11 22H2** — ideal als
  *versionsunterscheidendes* Merkmal Win10 ↔ Win11. Geringer Aufwand (Textdateien).
- **SRUM** (`SRUDB.dat`, ESE): Netz-/App-/Energie-Telemetrie. Bisher als Folgearbeit markiert;
  ESE ist aufwändig, aber hochwertig.
- **$MFT/$UsnJrnl, ShimCache (AppCompatCache in SYSTEM), AmCache-Vertiefung**: Ausführungs- und
  Dateisystem-Timeline. $MFT aufwändig; ShimCache als Registry-Wert gut machbar.
- **Windows Recall** (`UKP`/Screenshots+`ukg.db`, nur Win11/Copilot+PCs, opt-in): didaktisch
  spektakulär, aber sensibel — nur **Struktur/Metadaten**, keine echten Screenshots (Ethik).

**iOS (mittel):**
- **`knowledgeC.db`** für Profile **iOS ≤ 16** (heute fehlt es bewusst) — macht den Kontrast
  „knowledgeC vs. BIOME" als Lernziel greifbar.
- **`shutdown.log`** (Sysdiag): Spyware-/Reboot-Forensik; ab iOS 26 verändert, in 26.2 restauriert
  — schönes Versionsdetail.
- **iMessage `chat.chat_properties`-PLIST** (Chat-Hintergründe, **neu in iOS 26**) — kleines,
  präzises Versionsmerkmal in der bereits vorhandenen `sms.db`.
- **Unified Logs / Powerlog**-Strukturen (aufwändig) als Stretch-Goal.

**Android (mittel):**
- **Scoped-Storage-Artefakte** (`…/com.google.android.providers.media.module/databases/external.db`):
  „welche App hat wann welche Datei berührt" — ab Android 11/13/14 zunehmend relevant.
- **Privacy Dashboard** (`/system/appops/discrete`, **ABX**-Binärformat ab Android 12) — neues
  Format, gutes Versionsmerkmal.
- **`netpolicy`/`net_stats`, `recent_tasks`/`snapshots`**, `CarrierServices`-Caches.

---

## 5. Frage B' — Weitere OS-Profile (klar empfohlen)

Mehr Profile sind **sinnvoll und sogar nötig**, damit ein Fall „typisch für seine OS-Version"
aussieht. Profile sollten künftig nicht nur Faktentext liefern, sondern **steuern**, welche
Generator-Varianten/Pfade aktiv sind. Empfohlene Neuanlagen mit den versionstypischen Deltas:

| Profil | Charakteristische, *unterscheidende* Artefakte ggü. Nachbarversion |
|---|---|
| **windows_10** | **Kein** `appcompat\pca\` (PCA erst Win11 22H2); ShimCache/$MFT-Verhalten abweichend; klassische Recall-Abwesenheit; ältere Edge/IE-Spuren möglich. |
| **windows_11** (vorhanden, schärfen) | **PCA**-Textdateien; geänderte `$STANDARD_INFORMATION`/`$FILE_NAME`-NTFS-Semantik; optional **Recall** (Copilot+); Chromium-Edge Standard. |
| **ios_16** | `knowledgeC.db` **vorhanden** (3-Tabellen-Modell), BIOME nur teilweise. |
| **ios_17** (vorhanden) | BIOME/SEGB ersetzt knowledgeC; kein `knowledgeC.db`. |
| **ios_18** | BIOME ausgeweitet; reorganisierte Log-/Sysdiag-Pfade; Apple-Intelligence-Spuren (geräteabhängig). |
| **ios_26** | iMessage `chat_properties` (Chat-Hintergründe); verändertes `shutdown.log` (26.0) bzw. restauriert (26.2); year-based Versionsschema; mehr „shared data" in logischer Extraktion. |
| **android_13** | Foto-Picker/Scoped-Storage strenger; Privacy Dashboard (ABX) etabliert. |
| **android_14** (vorhanden) | Scoped Storage voll erzwungen; `external.db`-Medienprovider; stärkere FS-Verschlüsselung. |
| **android_15/16** | weitere Scoped-Storage-/Permission-Telemetrie; (Versionszählung Hersteller-/Jahr-abhängig — Profil als „android_15" mit dokumentierten Deltas). |

> Hinweis zur Versionsbenennung: Apple ist 2025 auf **Jahreszahlen** umgestiegen (iOS **26**),
> daher „iOS 26" statt „iOS 19". Bei Android ist eine fortlaufend hohe Nummer („17") je nach
> Veröffentlichungsstand zu prüfen; das Framework behandelt Profile rein als benannte Faktensätze
> und ist damit zukunftsoffen.

**Mechanik:** Pro Profil ein `artifact_overrides`-Block (welche Pfade/Tabellen/Zusatzdateien an
sind), den die Generatoren über den vorhandenen Loader auswerten. So bleibt „neue Version = neues
Profil" wahr, ohne Generator-Wildwuchs.

---

## 6. Empfohlene Umsetzungsreihenfolge

1. **Seed-RNG-Modul** + Randomisierung der Identifikatoren (GUIDs, SID, Rechnername, IMEI/Serial,
   Container-Hashes) — größter Individualitäts-Gewinn bei klarem Aufwand. *(Frage A)*
2. **Noise-Pools + Umfangssteuerung** (`scope`-Preset + `volume`/`noise_density`), seed-gezogen —
   macht Mengen und Texte je Fall verschieden und wählbar. *(Frage B)*
3. **Profil-Steuerung aktivieren** (`artifact_overrides`) + **windows_10** und **ios_16** als erste
   echte Kontrastprofile, dann **ios_18/ios_26**, **android_13/15**. *(Frage B')*
4. **Artefakt-Anreicherung** entlang der Profile: zuerst **PCA (Win11)** und **knowledgeC (iOS 16)**
   als klar version-unterscheidende, günstige Spuren; danach Scoped-Storage `external.db`,
   `shutdown.log`, iMessage `chat_properties`; SRUM/$MFT/Recall als ambitionierte Folgeschritte. *(Frage A')*
5. **Validierungs-Gates** je Profil erweitern (Format-Checks für die neuen Artefakte), Referenz
   bleibt 12/12.

Alle Schritte fügen sich in die bestehende Architektur (Master-Loader, Registry, Profile,
Gate-Modi) ein und erhalten Determinismus, Tool-Validierung und Ethik-Leitplanken.

---

## Quellen

- ElcomSoft: *New and updated security features in iOS 26 and their forensic implications* — https://blog.elcomsoft.com/2026/04/new-and-updated-security-features-in-ios-26-and-their-forensic-implications/
- Matthew Plascencia: *New Forensic Artifacts in iOS 26* (u. a. iMessage `chat_properties`) — https://matthewplascencia.substack.com/p/am-i-that-old-already-new-forensic
- CyberInsider: *Apple restores spyware detection artifact (shutdown.log) in iOS 26.2* — https://cyberinsider.com/apple-restores-spyware-detection-artifact-in-ios-26-2-after-backlash/
- Zena Forensics: *A first look at iOS 18 forensics* — https://blog.digital-forensics.it/2024/09/a-first-look-at-ios-18.html
- skiddie.life: *Apple's Biome: The Successor to knowledgeC* — https://skiddie.life/posts/iOS-biome-knowledgeC-dfir-forensics/
- Securelist (Kaspersky): *What makes Windows 11 interesting from a digital forensics perspective* — https://securelist.com/forensic-artifacts-in-windows-11/117680/
- Andrea Fortuna: *Windows 11 quietly introduced a new execution artifact (PCA)* — https://andreafortuna.org/2026/03/19/windows11-pca-artifact/
- Magnet Forensics: *ShimCache vs AmCache* — https://www.magnetforensics.com/blog/shimcache-vs-amcache-key-windows-forensic-artifacts/
- Zena Forensics: *A first look at Android 14 forensics* — https://blog.digital-forensics.it/2024/01/a-first-look-at-android-14-forensics.html
- Forensafe: *Android Scoped Storage* (`external.db`) — https://forensafe.com/blogs/AndroidScopedStorage.html
- Andrea Fortuna: *Digital Detectives vs. Android 14* — https://andreafortuna.org/2024/08/15/digital-detectives-vs-android-14-overcoming-new-forensic-challenges
