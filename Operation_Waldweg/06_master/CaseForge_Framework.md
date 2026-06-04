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

## 8. Ethik / Leitplanken (im System-Prompt verankert)

Nur synthetische Daten; keine realen Personendaten; keine reproduzierbaren Tat-/Beschaffungsanleitungen; bei sensiblen Delikten **nie** inkriminierende Medieninhalte, sondern nur Artefakt-Strukturen/Metadaten. Jeder Fall trägt `disclaimer: synthetic_training_data_only`.

## 9. Roadmap (Rest-Verdrahtung)

- `build` voll spec-getrieben (derzeit plattformgefiltert) — Generatoren je `artifact_classes` selektiv ansteuern.
- Spec→`case_master.yaml`-Adapter (heute teils parallel) + Multi-Case-Verzeichnisse (`cases/<name>/`).
- Profile für iOS 16/18, Android 13/15, Windows 10 ergänzen.
- Auto-Report (Aufgabenstellung/Lösungsschlüssel) je Fall aus dem Spec generieren.
- Optional: GUI/Notebook-Frontend über die CLI.
