# CaseForge — Framework für synthetische Forensik-Fälle

> Aus deiner Eingabe (Delikt, Anzahl/Art digitaler Asservate, OS-Versionen, Lernziel) wird
> **LLM-gestützt** ein fiktiver Fall **vorgeschlagen**, nach deiner **Verifikation**
> deterministisch **erzeugt** und gegen **Forensik-Tools validiert**. Rein synthetisch, nur lose
> an reale Phänomene angelehnt. „Operation Waldweg" (unter `examples/`) ist der mitgelieferte
> Beispiel-/Referenzfall.

**Leitprinzip — *Eine Wahrheit, viele Projektionen*:** Eine zentrale `case_master.yaml` ist die
einzige Wahrheitsquelle; alle Geräteartefakte werden daraus deterministisch projiziert
(garantierte geräteübergreifende Konsistenz).

---

## 1. Pipeline

```
 Eingabe (Delikt, Asservate, OS, Lernziel, Sprache, Umfang)
        │
 [1] PROPOSE  ── LLM (Cowork ODER lokal/ollama) ─► Case-Spec (JSON) + Artefaktübersicht
        │
 [2] REVIEW   ── Mensch verifiziert/ändert den Spec (Mensch-in-the-loop)
        │
 [3] BUILD    ── Adapter Spec→Master; Registry wählt Generatoren je Plattform/Profil
        │        ─► deterministische Artefakte + Katalog + Fall-Report
        │
 [4] VALIDATE ── Forensik-Gates (iLEAPP/ALEAPP/regipy/python-evtx/LnkParse3/MFTECmd/ABX…)
```

## 2. Komponenten (in `caseforge/`)

| Datei | Rolle |
|------|------|
| `forge.py` | CLI-Orchestrator: `propose · build · validate · run · report · catalog · teach · problems`. |
| `knowledge_base.py` | Wissensbasis forensischer **Problemstellungen** (s. §10): Laden/Validieren/Matching, Prompt-Katalog, Anlern-Workflow. |
| `registry.py` | Metadaten-Verzeichnis aller Generatoren (Plattform, OS-min, Artefaktklasse, Pfade, Format, **Gegenprüf-Tool**); steuert Auswahl und Katalog. |
| `spec_to_master.py` | Adapter **Spec → `case_master.yaml`**: projiziert den verifizierten Spec auf den generator-tauglichen Master (Meta/Delikt/Personen/Geräte/Timeline/Inkonsistenzen, OS-Profil → `os_version`/Flags). Vergibt einen Zufalls-Seed, wenn keiner angegeben ist. Wird von `build --spec` automatisch aufgerufen. |
| `llm.py` | Baut den Prompt aus Eingabe + Registry + Profilen + Schema; Backends **cowork** und **ollama** (gestreamt, mit Modell-/Verbindungs-Vorprüfung). |
| `i18n.py` | Sprachschicht (de/en/fr/es/tr): Ausgabesprache des LLM-Vorschlags, `meta.language_primary`, Framework-Strings. |
| `catalog.py` | Erzeugt die Artefaktübersicht (`…/06_master/Artefakt_Katalog.md/.csv`). |
| `gate_common.py` | Format- vs. Referenz-Modus der Validierungs-Gates. |
| `profiles/*.yaml` | OS-Profile (s. §5) mit versionsspezifischen Fakten **und** `artifact_overrides`, die Generatoren steuern. |
| `prompts/case_proposal_system.md` | System-Prompt des Fall-Designers inkl. Ethik-Regeln. |
| `schema/case_spec.schema.json` | JSON-Schema des Case-Specs. |
| `generators/` | ~45 deterministische Generatoren, Validatoren und Format-Writer (`reg_hive`, `evtx_writer`, `biome_writer`, `abx_writer`, `mft_writer`, …) + `case_master_io`, `caseforge_rng`, `noise_pools`. |

## 3. Typischer Ablauf

```bash
cd caseforge

# 1) Fall vorschlagen lassen (Cowork: Claude ist das LLM; Sprache wählbar)
python3 forge.py propose --backend cowork --lang de --input eingabe.json
#   -> out/proposal_prompt.md in Claude Cowork stellen; Antwort als out/case_spec.json sichern
# 1b) ODER lokal/offline:
python3 forge.py propose --backend ollama --model qwen2.5:32b-instruct --input eingabe.json

# 2) Spec prüfen/anpassen (out/case_spec.json) — Mensch-in-the-loop

# 3) bauen (inkl. Katalog + Fall-Report) und 4) validieren
python3 forge.py build    --case MeinFall --spec out/case_spec.json --scope L --seed 4242
python3 forge.py validate --case MeinFall
python3 forge.py report   --case MeinFall      # Fall-Report (läuft auch automatisch im build)

# Beispiel-/Referenzfall bauen & prüfen:
python3 forge.py build    --root ../examples/operation_waldweg
python3 forge.py validate --root ../examples/operation_waldweg   # -> 12/12, lösbar & konsistent
```

`eingabe.json` (Beispiel):
```json
{"deliktart":"Stalking/Nachstellung","lernziel":"verschluesselte Messenger + Standortverlauf",
 "language":"de","assets_count":2,
 "devices":[{"platform":"android","os_profile":"android_14","owner":"Beschuldigter"},
            {"platform":"ios","os_profile":"ios_17","owner":"Geschaedigte"}]}
```

## 4. Fallindividualität & Umfang

- **Seed-gesteuert & deterministisch:** Ein `meta.generator_seed` speist alle randomisierten,
  lösungsneutralen Identifikatoren (App-Container-UUIDs, Windows-SID, Rechnername, **Benutzername**,
  IMEI/Serial/BSSID) sowie Auswahl/Reihenfolge/Menge des Noise. Gleicher Seed ⇒ bit-stabile
  Ausgabe; Spec-Fälle erhalten automatisch einen Zufalls-Seed, sodass jeder Fall individuell ist.
  Der Referenzfall behält seinen festen Seed.
- **Umfang/Noise:** `meta.scope: S|M|L|XL` (bzw. `build --scope`), Feinsteuerung `meta.volume`
  je Klasse und `meta.noise_density`; lokalisierte Noise-Pools (de/en/fr/es/tr) in `noise_pools.py`.

## 5. OS-Profile (steuern Generatoren via `artifact_overrides`)

| Plattform | Profile | Versionstypische Artefakte (Flag) |
|---|---|---|
| Windows | `windows_10`, `windows_11` | **PCA** nur Win11 22H2+ (`pca`); **`$MFT`** mit Fixups, `$SI/$FN`, Non-Resident-`$DATA`-Runs + NTFS-Systemrecords (`mft`); **`$UsnJrnl:$J`** (USN_RECORD_V2) (`usnjrnl`); **ShimCache/AppCompatCache** im SYSTEM-Hive (`shimcache`); **SRUM `SRUDB.dat`** als ESE-Header-Stub (`srum`) |
| iOS | `ios_16`, `ios_17`, `ios_18`, `ios_26` | **`knowledgeC.db`** (3-Tabellen-Modell) ≤ iOS 16 vs. **BIOME/SEGB** ≥ 17 (`knowledgec`); `chat_properties`-PLIST + `shutdown.log` ab iOS 26; **Powerlog `CurrentPowerlog.PLSQL`** (`powerlog`) |
| Android | `android_13`, `android_14`, `android_15` | **Scoped-Storage `external.db`** (`module`/`legacy`-Pfad) (`scoped_storage`); **Privacy Dashboard** `/system/appops/discrete` als **voll-faithful ABX** (`privacy_dashboard`); **`netpolicy.xml`** + **`recent_tasks`** (ABX) (`netpolicy`/`recent_tasks`) |

Eine neue Version = ein neues `profiles/<name>.yaml`. Der Referenzfall trägt keine Overrides; die
versionstypischen Artefakte bleiben dort aus. Über `artifact_classes` je Gerät im Spec lassen sich
fokussierte Teilfälle erzeugen (z. B. nur `registry`, nur `eventlog`).

## 6. Parametrisierung (Loader + Fallback)

Jeder inhaltsführende Generator liest seine Daten aus dem aktiven `case_master.yaml`
(`WALDWEG_CASE_MASTER`); fehlt eine Struktur, greift sein Referenz-Fallback. Master-getrieben sind
Messaging (iMessage, Android-WhatsApp 1:1 + Gruppen, iOS-WhatsApp-Gruppe), Standorte (iOS/Android),
Browser-Verlauf (Chrome/Edge/Safari), Dokumente und App-Sandboxen. Optionale Master-Konventionen:

```yaml
persons:
  - {id: opfer, name: Petra S., phone: "+4917000001111"}   # phone -> Messaging-Handle
chat_threads:
  - id: opfer_taeter
    channel: imessage            # imessage | whatsapp | sms | *_group
    participants: [opfer, taeter]
    messages:
      - {t: "2026-03-01T09:00:00+01:00", from: taeter, text: "..."}
      - {t: "2026-03-01T18:30:00+01:00", from: opfer,  text: "...", deleted: true}  # nur WAL-Fragment
location_tracks:
  opfer:
    - {t: "2026-03-01T08:00:00+01:00", lat: 52.50, lon: 13.40, kind: cell, lac: 100, ci: 200}
browser_history:
  sam: [{t: "2026-03-01T08:00:00+01:00", url: "https://...", title: "..."}]
documents:
  - {device: windows, area: documents, name: Liste.xlsx, kind: xlsx,
     relevance: critical, sheet: Liste, header: [name, betrag], rows: [[Sommer, 5000]]}
app_packages:
  ios:     ["com.coinbase.app"]
  android: ["com.binance.dev", "org.telegram.messenger"]
```

Jeder Generator meldet seine Quelle in der Konsole (`Inhaltsquelle: Master` vs. `Referenz-Fallback`).

## 7. Validierung mit Forensik-Tools

Jeder Registry-Eintrag nennt sein **Gegenprüf-Tool**. `forge.py validate` fährt die Gates; lokal
zusätzlich die echten Tools laut `docs/Toolchain_und_Bewertung_Dozent.md` (iLEAPP, ALEAPP,
RegRipper, EvtxECmd, Hindsight, LnkParse3, BIOME-Stream-Analyzer, MFTECmd).

**Gate-Modi** (`gate_common.py`): Jeder Check ist als **Format** (Schema/Join/Parsebarkeit/
Timestamp — gilt für jeden Fall) oder **Referenz** (Waldweg-spezifischer Lösungsinhalt)
klassifiziert. `forge.py validate --mode` bzw. `WALDWEG_GATE_MODE` steuert `format` | `reference`
| `all`. Auto-Wahl: Spec-abgeleitete Fälle → `format`, Referenz → `all`. `verify_solution.py`
(Lösbarkeit) läuft nur im `all`-Modus. Der Referenzfall durchläuft den vollen Selbsttest (12/12),
ein frei spezifizierter Fall validiert eigenständig im Format-Modus.

## 8. LLM-Backends & Modellempfehlungen

Das LLM erzeugt **nur den Fall-Vorschlag** (Spec + Narrativ); die Artefakte entstehen
**deterministisch** aus den Generatoren — die Datenqualität hängt also nicht am Modell.

- **Claude Cowork** — höchste Vorschlagsqualität, deutschsprachig, ideal für komplexe
  Mehrgeräte-Plots und Widerspruchs-Design.
- **Lokal/offline (ollama)** — wenn Daten das Haus nicht verlassen dürfen. Gültigen, installierten
  Tag verwenden (`ollama list`):

| Modell (ollama-Tag) | VRAM (Q4) | Eignung |
|---|---|---|
| `qwen2.5:32b-instruct` | ~20–24 GB | Default-Empfehlung — sehr gutes DE + zuverlässiges Schema-JSON |
| `llama3.3:70b-instruct` | ~40+ GB | höchste lokale Qualität |
| `qwen2.5:14b-instruct` | ~10–12 GB | guter Kompromiss (24-GB-Karte) |
| `qwen2.5:7b-instruct` / `llama3.1:8b` | ~6–8 GB | Einstieg/Laptop |

Der Aufruf ist gestreamt; bei kaltem/großem Modell `--timeout <sek>`, Remote-Server `--url`.

## 9. Ethik / Leitplanken

Im System-Prompt verankert: nur synthetische Daten; keine realen Personendaten; keine
reproduzierbaren Tat-/Beschaffungsanleitungen; bei sensiblen Delikten **nie** inkriminierende
Medieninhalte, sondern nur Artefakt-Strukturen/Metadaten. Jeder Fall trägt
`disclaimer: synthetic_training_data_only`.

## 10. Wissensbasis & Problemstellungen (forensisches Expertensystem)

CaseForge wächst zu einem **forensischen Expertensystem**: kuratiertes Expertenwissen wird als
wiederverwendbarer Fundus *forensischer Problemstellungen* abgelegt
(`knowledge/problems/*.yaml`) — charakteristische Herausforderungen aus **Computerforensik**,
**Mobilfunkforensik** und **App-Analyse** (z. B. Quellkonflikt WiFi-Cache vs. Cell-Ortung,
gelöschte WAL-Nachricht, USB-Exfiltration, Timestomping `$SI`/`$FN`, Cloud-Sync-Lücke). Jede
Problemstellung trägt Lernziel, betroffene Artefaktklassen, **Lösungsweg** (Dozentenwissen),
Fallstricke, Ethik-Flag und Herkunft (`provenance`).

**Anlernen — Freitext → LLM → menschliche Freigabe.** Die niedrigste Hürde: ein/e Experte/in
schreibt formlos (auch aus einer echten, anonymisierten Fallbeobachtung), das LLM strukturiert
den Text schema-konform zu einem **Entwurf**, ein Mensch gibt frei.

```bash
python3 forge.py teach --input expertentext.txt            # Cowork: schreibt out/teach_prompt.md
#   -> in Claude Cowork ausführen, YAML-Antwort als knowledge/incoming/<id>.draft.yaml sichern
python3 forge.py teach --input expertentext.txt --backend ollama   # offline: legt Entwurf direkt an
python3 forge.py teach --list-drafts                       # Entwürfe sichten
python3 forge.py teach --approve <id> --by "Name"          # Freigabe -> knowledge/problems/
```

Das Anlernen ist damit das menschliche **Anreichern** des KI-/Framework-Wissens; Determinismus,
Tool-Validierung und Ethik der erzeugten Fälle bleiben unberührt — die Wissensbasis steuert nur,
**welche** Artefaktklassen und Widersprüche ein Fall trägt.

**Auswahl beim Fallbau — manuell oder LLM-automatisch.**

```bash
python3 forge.py problems --list                           # Katalog (approved)
python3 forge.py problems --match "USB-Datenabfluss Windows" --platform windows
python3 forge.py problems --show usb-exfiltration-correlation

python3 forge.py propose --problems auto    --input eingabe.json   # LLM wählt passende aus
python3 forge.py propose --problems match   --input eingabe.json   # deterministisch (offline) nach Delikt/Lernziel
python3 forge.py propose --problems loc-wifi-vs-cell-conflict,msg-deleted-wal-fragment ...  # fix
```

Die gewählten IDs landen im Case-Spec-Feld `forensic_problems`, aktivieren ihre Artefaktklassen,
liefern `planted_inconsistencies`-Vorlagen und erscheinen mit Lösungsweg im **Fall-Report**
(Dozenten-Abschnitt 6). `knowledge/schema/problem.schema.json` und `knowledge/taxonomy.yaml`
definieren Struktur und kontrolliertes Vokabular; `python3 knowledge_base.py validate` prüft den
gesamten Korpus.

Konzept und akademische Einordnung (Mensch-KI-Wissensanreicherung): siehe
`docs/Wissensbasis_Expertensystem.md`.
