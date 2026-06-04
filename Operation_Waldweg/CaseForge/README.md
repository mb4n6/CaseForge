# CaseForge — Framework für synthetische Forensik-Fälle

> Aus „Operation Waldweg" wird ein wiederverwendbares Framework: aus deiner Eingabe
> (Delikt, Anzahl/Art digitaler Asservate, OS-Versionen, Lernziel) wird **LLM-gestützt** ein
> fiktiver Fall **vorgeschlagen**, nach deiner **Verifikation** deterministisch **erzeugt** und
> gegen **Forensik-Tools validiert**. Rein synthetisch, nur lose an reale Phänomene angelehnt.

## 1. Warum das schon fast steht

Operation Waldweg ist bereits zu ~80 % ein Framework:

- **`case_master.yaml`** = Single Source of Truth → alle Geräte-Artefakte werden daraus *projiziert* (garantierte Cross-Device-Konsistenz).
- **~33 Generatoren** (~6.000 Zeilen) erzeugen reale Artefaktformate: SQLite, plist, **regf** (eigener Hive-Writer), **EVTX** (template-BinXML), **BIOME/SEGB**, LNK, $I, JSON/XML, Medien.
- **`validate_*.py` + `run_all.py`** = Tool-Gates (iLEAPP/ALEAPP/regipy/RegRipper/python-evtx/LnkParse3/biome_core) als reproduzierbare Abnahme.
- **Manifeste** dokumentieren Relevanz (critical/context/noise) je Artefakt.

CaseForge ergänzt die fehlenden 20 %: **Registry, OS-Profile, Case-Spec-Schema, LLM-Vorschlag, Katalog, CLI**.

## 2. Zielarchitektur (Pipeline)

```
 Eingabe (Delikt, Asservate, OS, Lernziel)
        │
        ▼
 [1] PROPOSE  ── LLM (Cowork ODER lokal/ollama) ─► Case-Spec-Vorschlag (JSON) + _proposal_summary
        │                                           + Artefaktübersicht je Gerät/Plattform/OS
        ▼
 [2] REVIEW   ── du verifizierst/änderst den Spec  (Mensch-in-the-loop)
        │
        ▼
 [3] BUILD    ── Registry wählt Generatoren je Plattform/OS-Profil ─► deterministische Artefakte
        │
        ▼
 [4] CATALOG  ── Artefakt-Übersicht (MD/CSV) pro Gerät/Plattform/OS + Tool je Artefakt
        │
        ▼
 [5] VALIDATE ── Forensik-Gates (iLEAPP/ALEAPP/RegRipper/EVTX/…) ─► „ALLE GATES BESTANDEN ✓"
        │
        ▼
 [6] DELIVER  ── FS-Images + Master-Timeline + Lösungsschlüssel + Aufgabenstellung (PDF)
```

## 3. Komponenten (in `CaseForge/`)

| Datei | Rolle |
|------|------|
| `registry.py` | Metadaten-Verzeichnis aller Generatoren (Plattform, OS-min, Artefaktklasse, Pfade, Format, **Forensik-Tool**). |
| `profiles/*.yaml` | OS-Profile (`ios_17`, `android_14`, `windows_11`) mit versions­spezifischen Fakten (z. B. iOS 17 → BIOME statt knowledgeC). **Neue OS-Version = neues Profil.** |
| `schema/case_spec.schema.json` | JSON-Schema des Fall-Specs (Eingabe-/Vorschlagsformat). |
| `prompts/case_proposal_system.md` | System-Prompt des Fall-Designers (inkl. Ethik-Regeln). |
| `llm.py` | Baut den Prompt aus Eingabe+Registry+Profilen+Schema; Backends **cowork** und **ollama**. |
| `catalog.py` | Erzeugt die Artefaktübersicht (`06_master/Artefakt_Katalog.md/.csv`). |
| `spec_to_master.py` | **Adapter Spec → `case_master.yaml`**: projiziert den verifizierten Spec auf den generator-tauglichen Master (Meta/Delikt/Personen/Geräte/Timeline/Inkonsistenzen aus dem Spec; OS-Profil → `os_version`/BIOME-Streams; Referenz-Master als Basis für noch nicht modellierte Subtrees). `build --spec` ruft ihn automatisch auf. |
| `forge.py` | CLI: `catalog · propose · build · validate · run`. |

Die eigentlichen Generatoren bleiben in `09_build/generators/` und werden über die Registry angesteuert.

## 4. Typischer Ablauf

```bash
cd Operation_Waldweg/CaseForge

# 1) Fall vorschlagen lassen (Cowork: Claude ist das LLM)
python3 forge.py propose --backend cowork --input eingabe.json
#   -> out/proposal_prompt.md  (in Claude Cowork stellen; Antwort als out/case_spec.json sichern)
# 1b) ODER lokal/offline:
python3 forge.py propose --backend ollama --model qwen2.5:32b-instruct --input eingabe.json

# 2) Spec prüfen/anpassen (out/case_spec.json) — Mensch-in-the-loop

# 3) bauen + 4) Katalog + 5) validieren
python3 forge.py build --root /pfad/zu/NeuerFall
python3 forge.py catalog
python3 forge.py validate --root /pfad/zu/NeuerFall
#   (oder gesamt:)  python3 forge.py run --root /pfad/zu/NeuerFall
```

`eingabe.json` (Beispiel):
```json
{"deliktart":"Stalking/Nachstellung","lernziel":"verschluesselte Messenger + Standortverlauf",
 "devices":[{"platform":"android","os_profile":"android_14","owner":"Beschuldigter"},
            {"platform":"ios","os_profile":"ios_17","owner":"Geschaedigte"}],
 "assets_count":2}
```

## 5. Neue OS-Versionen / neue Teilprobleme

- **Neue iOS/Android/Windows-Version:** ein neues `profiles/<name>.yaml` anlegen (geänderte Pfade/Formate/Timestamps dokumentieren) und betroffene Generatoren parametrisieren bzw. eine versionsspezifische Variante registrieren. Der Rest (Spec, Build, Katalog, Gates) bleibt gleich.
- **Bestimmtes Teilproblem** (z. B. „nur ShellBags", „nur BIOME", „nur EVTX-Logins"): im Spec die `artifact_classes` je Gerät einschränken — `build --platform` und die Registry-Filter erzeugen dann einen fokussierten Mini-Fall.

## 6. LLM-Backends & Modellempfehlungen

Wichtig: Das LLM erzeugt **nur den Fall-Vorschlag** (Spec + Narrativ). Die Artefakte selbst entstehen **deterministisch** aus den Generatoren — die Datenqualität hängt also *nicht* am Modell. Mid-size-Modelle genügen.

**A) Claude Cowork (empfohlen für höchste Vorschlagsqualität)** — beste Reasoning-/Konsistenzleistung, deutschsprachig, direkt in dieser Umgebung; ideal für komplexe Mehrgeräte-Plots und Widerspruchs-Design.

**B) Lokal / offline (ollama, openclaw)** — wenn Daten das Haus nicht verlassen dürfen:

| Modell (ollama-Tag) | VRAM (Q4) | Eignung |
|---|---|---|
| `qwen2.5:32b-instruct` | ~20–24 GB | **Default-Empfehlung** — sehr gutes DE + zuverlässiges JSON/Schema |
| `llama3.3:70b-instruct` | ~40+ GB | höchste Qualität lokal (große GPU/Mac M3 Max/Ultra) |
| `qwen2.5:14b-instruct` | ~10–12 GB | guter Kompromiss (24-GB-Karte) |
| `qwen2.5:7b-instruct` / `llama3.1:8b` | ~6–8 GB | Einstieg/Laptop, einfache Fälle |
| `mixtral:8x7b` / `gemma2:27b` | ~26–32 GB | Alternativen |
| `qwen2.5-coder:14b` | ~10 GB | optional zum **Spec-Reparieren**/Schema-Fixing |

Empfehlung: **Cowork für den Entwurf**, danach optional ein lokales Modell zum schnellen Iterieren. Für strikt-valides JSON `format=json` (ollama) bzw. ein JSON-Schema-Constraint nutzen.

## 7. Validierung mit Forensik-Tools

Jeder Registry-Eintrag nennt sein **Gegenprüf-Tool**. `forge.py validate` fährt die Gates; lokal zusätzlich die echten Tools laut `06_master/Toolchain_und_Bewertung_Dozent.md` (iLEAPP, ALEAPP, RegRipper, EvtxECmd, Hindsight, LnkParse3, BIOME-Stream-Analyzer). Dokumentierte Grenzen: SRUM/ESE, $MFT/$UsnJrnl, valides Prefetch-SCCA, ShimCache.

**Gate-Modi** (`gate_common.py`): Jeder Check ist als **Format** (Schema/Join/Parsebarkeit/Timestamp — gilt für jeden Fall) oder **Referenz** (Waldweg-spezifischer Lösungsinhalt) klassifiziert. `WALDWEG_GATE_MODE` bzw. `forge.py validate --mode` steuert: `format` (beliebiger Spec-Fall), `reference` (nur Lösungs-Checks), `all` (beides, Referenz-Selbsttest). Auto-Wahl: Spec-abgeleitete Fälle → `format`, Referenz → `all`. `verify_solution.py` (Lösbarkeit) läuft nur im `all`-Modus.

## 8. Ethik / Leitplanken (im System-Prompt verankert)

Nur synthetische Daten; keine realen Personendaten; keine reproduzierbaren Tat-/Beschaffungsanleitungen; bei sensiblen Delikten **nie** inkriminierende Medieninhalte, sondern nur Artefakt-Strukturen/Metadaten. Jeder Fall trägt `disclaimer: synthetic_training_data_only`.

## 9. Roadmap (Rest-Verdrahtung)

- ~~`build` voll spec-getrieben — Generatoren je `artifact_classes` selektiv ansteuern.~~ ✓ erledigt (`registry.select_for_spec`).
- ~~Spec→`case_master.yaml`-Adapter~~ ✓ erledigt (`spec_to_master.py`, automatisch in `build --spec`).
- ~~Generatoren aus dem Master parametrisieren~~ ✓ **vollständig**: gemeinsamer Loader `09_build/generators/case_master_io.py`. Master-getrieben mit Fallback sind jetzt Messaging (iMessage, Android-WhatsApp 1:1 **und** Gruppen, iOS-WhatsApp-Gruppe), Standorte (iOS/Android), **Browser-Verlauf** (Chrome/Edge/Safari via `browser_history`), **Dokumente** (`documents`) und **App-Sandboxen** (`app_packages`). Fehlt eine Struktur, greift der dokumentierte Referenz-Fallback.
- ~~Validierungs-Gates entkoppeln~~ ✓ erledigt: `gate_common.py` trennt **Format-Checks** (Schema/Join/Parsebarkeit/Timestamp — gelten für jeden Fall) von **Referenz-Lösungs-Checks** (Waldweg-spezifische Inhalte). `forge.py validate` wählt den Modus automatisch (Spec-abgeleiteter Fall → `format`, Referenz → `all`); erzwingbar via `--mode all|format|reference`. So validiert ein frei spezifizierter Fall eigenständig grün, während der Referenzfall weiter den vollen Lösungs-Selbsttest (12/12) durchläuft.

### Parametrisierungs-Muster (Loader + Fallback)

Jeder inhaltsführende Generator versucht zuerst, seine Daten aus dem aktiven `case_master.yaml` (`WALDWEG_CASE_MASTER`) zu lesen; fehlt die Struktur, nutzt er seinen Referenz-Fallback — so bleibt „Operation Waldweg" unverändert grün, während ein eigener Spec den Fall wirklich bestimmt. Optionale Master-Konventionen:

```yaml
persons:
  - {id: opfer, name: Petra S., phone: "+4917000001111"}   # phone -> Messaging-Handle
chat_threads:
  - id: opfer_taeter
    channel: imessage            # imessage | whatsapp | sms | imessage_and_whatsapp
    participants: [opfer, taeter]
    messages:
      - {t: "2026-03-01T09:00:00+01:00", from: taeter, text: "..."}
      - {t: "2026-03-01T18:30:00+01:00", from: opfer,  text: "...", deleted: true}  # nur WAL-Fragment
location_tracks:
  opfer:                          # person-/device-id
    - {t: "2026-03-01T08:00:00+01:00", lat: 52.50, lon: 13.40, kind: cell, lac: 100, ci: 200}
    - {t: "2026-03-01T08:10:00+01:00", lat: 52.51, lon: 13.41, kind: wifi, bssid: "aa:bb:.."}
browser_history:                  # Chrome/Edge/Safari je device-/person-id
  sam: [{t: "2026-03-01T08:00:00+01:00", url: "https://...", title: "..."}]
documents:                        # Alltagsdokumente je Gerät
  - {device: windows, area: documents, name: Liste.xlsx, kind: xlsx,
     relevance: critical, sheet: Liste, header: [name, betrag], rows: [[Sommer, 5000]]}
  - {device: ios, area: downloads, name: Vertrag.pdf, kind: pdf, lines: ["Anlagevertrag"]}
app_packages:                     # welche App-Sandboxen je Plattform
  ios:     ["com.coinbase.app"]
  android: ["com.binance.dev", "org.telegram.messenger"]
# Gruppen-Chats: chat_threads mit *_group-Kanal + messages[].from (Absender)
```

Die Konsole jedes Generators meldet seine Quelle (`Inhaltsquelle: Master` vs. `Referenz-Fallback`).
- Profile für iOS 16/18, Android 13/15, Windows 10 ergänzen.
- Auto-Report (Aufgabenstellung/Lösungsschlüssel) je Fall aus dem Spec generieren.
- Optional: GUI/Notebook-Frontend über die CLI.
