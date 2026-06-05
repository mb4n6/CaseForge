# CaseForge — Agent-Assisted, Tool-Validated Synthetic Forensic Cases

**A deterministic framework that generates complete, schema-faithful digital-forensics training
cases (iOS, Android, Windows, cloud, multimedia) and validates them against real open-source
forensic tools.**
Author: Marc Brandt — Baden-Württemberg State Police University (HfPolBW)

> 🇩🇪 Deutsche Fassung: [README.de.md](README.de.md) · 📄 Paper: [paper/](paper/)
>
> ⚠️ **Synthetic data only.** Everything CaseForge produces is fictional and carries the marker
> `synthetic_training_data_only`. No real persons, addresses, numbers or accounts.

---

## Why CaseForge

Real seized exhibits cannot enter the classroom; public practice corpora are scarce, age fast,
and rarely form a coherent cross-device crime scene. CaseForge solves this by treating a case
as a **reproducible projection of a single source of truth**: from a short brief (offence,
exhibits, OS versions, learning objective) an LLM **proposes** a case spec, a human **verifies**
it, and deterministic generators **project** it into device artifacts in their **native formats**
(SQLite, plist, registry hives/regf, EVTX, BIOME/SEGB, LNK, $I, **$MFT**, ABX …) at forensically
correct paths — then **real tools** (iLEAPP, ALEAPP, regipy, python-evtx, LnkParse3, MFTECmd-style
parsing) cross-check them as an acceptance gate.

**Guiding principle:** *one truth, many projections* — one `case_master.yaml`, all device
artifacts deterministically derived from it (guaranteed cross-device consistency).

The repository ships **CaseForge** (the framework) plus **Operation Waldweg** as its first fully
worked **example case** (a fictional homicide across three devices, with planted inconsistencies).

---

## Repository layout

```
caseforge/                  the framework
├── forge.py                CLI: propose · build · validate · run · report · catalog
├── registry.py             metadata catalogue of all generators (+ cross-check tool)
├── spec_to_master.py       adapter: case-spec → case_master.yaml
├── llm.py · i18n.py        LLM proposal layer + language selection
├── catalog.py · gate_common.py
├── profiles/               OS profiles (ios_16/17/18/26, android_13/14/15, windows_10/11)
├── prompts/ · schema/      LLM system prompt (ethics) + case-spec JSON schema
└── generators/             ~45 deterministic generators, validators & format writers
                            (regf, EVTX, BIOME, ABX, $MFT, …) + case_master_io / rng / pools

paper/                      academic paper (EN + DE)
docs/                       architecture, toolchain, variability analysis
examples/
└── operation_waldweg/      the example case
    ├── case_master.yaml    single source of truth
    ├── 01_ios_full_fs … 08_multilingual    built artifacts
    └── 06_master/          case file, solution key, catalogue, report, manifests
```

---

## Quick start

```bash
cd caseforge
pip install pyyaml                       # minimum; for real gates: regipy python-evtx LnkParse3

# Build & validate the example case "Operation Waldweg"
python3 forge.py build    --root ../examples/operation_waldweg
python3 forge.py validate --root ../examples/operation_waldweg   # -> 12/12, scenario solvable
```

## Create a new case (PROPOSE → REVIEW → BUILD → VALIDATE)

```bash
cd caseforge
# 1) Let an LLM propose a spec (Claude Cowork or local ollama), in any supported language
python3 forge.py propose --backend cowork --lang en --input brief.json
#    -> review/adjust out/case_spec.json (human in the loop)

# 2) Build deterministically + 3) cross-check with forensic tools
python3 forge.py build    --case MyCase --spec out/case_spec.json --scope L --seed 4242
python3 forge.py validate --case MyCase
python3 forge.py report   --case MyCase    # per-case Markdown report (also auto-run in build)
```

`brief.json` example:

```json
{ "deliktart": "Stalking/Harassment", "lernziel": "encrypted messengers + location",
  "language": "en", "assets_count": 2,
  "devices": [ {"platform":"ios","os_profile":"ios_17","owner":"Victim"},
               {"platform":"android","os_profile":"android_14","owner":"Suspect"} ] }
```

---

## Key capabilities

- **Deterministic & reproducible** — one `generator_seed` drives everything; same seed ⇒
  bit-stable output. Spec-derived cases get a random seed so every case is individual
  (app-container UUIDs, Windows SID, computer name, IMEI, **user name**, noise selection all vary).
- **Case size & noise** — `scope: S|M|L|XL`, per-class `volume`, `noise_density`; localized noise
  pools (de/en/fr/es/tr).
- **Multilingual** — pick the language up front; the LLM writes content in it, generators emit it
  verbatim.
- **OS-version contrast profiles** — profiles *steer* generators via `artifact_overrides`:
  Windows 10 vs 11 (**PCA**, **$MFT** incl. non-resident runs & system records, **SRUM** stub),
  iOS 16 (**knowledgeC.db**) vs 17/18 (BIOME) vs 26 (**chat_properties**, **shutdown.log**),
  Android 13/14/15 (**Scoped-Storage `external.db`**, **Privacy Dashboard** as full-faithful ABX).
- **Two-tier validation** — format checks (apply to every case) vs reference-solution checks
  (Waldweg only); auto-selected, forceable with `--mode`.
- **Ethics guardrails** — hard-wired in the LLM system prompt; every case marked
  `synthetic_training_data_only`.

Full framework documentation: [caseforge/README.md](caseforge/README.md).
Methodology paper: [paper/Paper_Agent_Assisted_Case_Generation_EN.md](paper/Paper_Agent_Assisted_Case_Generation_EN.md).

---

## License & citation

Free for educational use with attribution.

> Marc Brandt · Institute for Continuing Education · Baden-Württemberg State Police University · 2026
