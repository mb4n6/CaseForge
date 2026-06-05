# CaseForge — Agenten-gestützte, tool-validierte synthetische Forensik-Fälle

**Ein deterministisches Framework, das vollständige, schema-getreue IT-Forensik-Trainingsfälle
(iOS, Android, Windows, Cloud, Multimedia) erzeugt und gegen echte Open-Source-Forensiktools
validiert.**
Verfasser: Marc Brandt — Hochschule für Polizei Baden-Württemberg

> 🇬🇧 English: [README.md](README.md) · 📄 Paper: [paper/](paper/)
>
> ⚠️ **Nur synthetische Daten.** Alles ist fiktiv und trägt das Kennzeichen
> `synthetic_training_data_only`. Keine realen Personen, Adressen, Nummern, Konten.

---

## Warum CaseForge

Echte Asservate dürfen nicht in die Lehre; öffentliche Übungskorpora sind rar, veralten schnell
und bilden selten einen zusammenhängenden, geräteübergreifenden Tatort. CaseForge behandelt einen
Fall als **reproduzierbare Projektion einer einzigen Wahrheitsquelle**: Aus einer kurzen Eingabe
(Delikt, Asservate, OS-Versionen, Lernziel) **schlägt** ein LLM einen Case-Spec vor, ein Mensch
**verifiziert** ihn, und deterministische Generatoren **projizieren** ihn in Geräteartefakte in
ihren **Originalformaten** (SQLite, plist, Registry-Hives/regf, EVTX, BIOME/SEGB, LNK, $I,
**$MFT**, ABX …) auf forensisch korrekten Pfaden — danach prüfen **echte Tools** (iLEAPP, ALEAPP,
regipy, python-evtx, LnkParse3) sie als Abnahme-Gate gegen.

**Leitprinzip:** *Eine Wahrheit, viele Projektionen* — ein `case_master.yaml`, alle Geräteartefakte
deterministisch daraus abgeleitet (garantierte Konsistenz).

Das Repository liefert **CaseForge** (das Framework) plus **Operation Waldweg** als ersten,
vollständig ausgearbeiteten **Beispielfall**.

---

## Struktur

```
caseforge/                  das Framework (forge.py, registry, profiles, schema, generators/ …)
paper/                      akademisches Paper (EN + DE)
docs/                       Architektur, Toolchain, Variabilitäts-Analyse
examples/operation_waldweg/ der Beispielfall (case_master.yaml + 01–08 + 06_master)
```

## Schnellstart

```bash
cd caseforge
pip install pyyaml
python3 forge.py build    --root ../examples/operation_waldweg
python3 forge.py validate --root ../examples/operation_waldweg     # -> 12/12, lösbar
```

## Neuen Fall erzeugen (PROPOSE → REVIEW → BUILD → VALIDATE)

```bash
cd caseforge
python3 forge.py propose  --backend cowork --lang de --input eingabe.json
python3 forge.py build    --case MeinFall --spec out/case_spec.json --scope L --seed 4242
python3 forge.py validate --case MeinFall
python3 forge.py report   --case MeinFall      # Fall-Report (läuft auch automatisch im build)
```

## Kernfunktionen

- **Deterministisch & reproduzierbar** (seed-gesteuert); Spec-Fälle erhalten einen Zufalls-Seed,
  damit jeder Fall individuell ist (App-UUIDs, SID, Rechnername, IMEI, **Benutzername**, Noise).
- **Umfang/Noise**: `scope: S|M|L|XL`, `volume`, `noise_density`; lokalisierte Pools (de/en/fr/es/tr).
- **Mehrsprachig**: Sprache vorab wählen; LLM schreibt Inhalte, Generatoren übernehmen sie.
- **OS-Versions-Kontrastprofile** (steuern Generatoren via `artifact_overrides`): Win10/11
  (**PCA**, **$MFT** inkl. Non-Resident-Runs + Systemrecords, **SRUM**-Stub), iOS 16
  (**knowledgeC.db**) vs 17/18 (BIOME) vs 26 (**chat_properties**, **shutdown.log**),
  Android 13/14/15 (**Scoped-Storage `external.db`**, **Privacy-Dashboard** als voll-faithful ABX).
- **Zweistufige Validierung** (Format vs. Referenz-Lösung), Auto-Modus, `--mode` erzwingbar.
- **Ethik-Leitplanken** fest im LLM-System-Prompt; jeder Fall `synthetic_training_data_only`.

Vollständige Doku: [caseforge/README.md](caseforge/README.md) · Paper:
[paper/Paper_Agentengestuetzte_Fallgenerierung.md](paper/Paper_Agentengestuetzte_Fallgenerierung.md).

---

## Lizenz & Zitation

Frei für Ausbildungszwecke mit Namensnennung.

> Marc Brandt · Institut für Fortbildung · Hochschule für Polizei Baden-Württemberg · 2026
