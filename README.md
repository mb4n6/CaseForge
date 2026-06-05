# Operation Waldweg — Synthetic Forensic Training Case & CaseForge Framework

**A fully synthetic, tool-validated multi-device case scenario for digital-forensics education**
Baden-Württemberg State Police University (HfPolBW) · Author: Marc Brandt (Lecturer, Digital Forensics)

> **FICTIONAL DATA ONLY.** All persons, addresses, phone numbers, accounts,
> communication contents, media and events are entirely invented and exist solely for
> training and research. Loosely *inspired* by real phenomena, with no connection to any
> real person or case. Every generated case carries the marker `synthetic_training_data_only`.
>
> Deutsche Fassung: [README.de.md](README.de.md)

---

## 1. What this is

"Operation Waldweg" is a synthetic homicide case (ref. AZ 2026-KK-00892) whose digital
exhibits — iPhone (iOS 17), Samsung (Android 14), Windows 11 triage, cloud, wearable and
multimedia — are produced at **forensically correct paths** and in **schema-faithful native
formats** (SQLite, plist, registry hives/regf, EVTX, BIOME/SEGB v2, LNK, $I, JSON/XML). The
artifacts are cross-checked against **real open-source forensic tools** (iLEAPP, ALEAPP,
regipy/RegRipper, python-evtx, LnkParse3, BIOME parser).

The project is also a **framework** — **CaseForge** — that, from a short brief (offence type,
exhibits, OS versions, learning objective), proposes **new** synthetic cases with an LLM,
generates them deterministically after human verification, and validates them against
forensic tools.

**Guiding principle:** *One truth, many projections* — a single `case_master.yaml` is the
sole source of truth; all device artifacts are deterministically projected from it,
guaranteeing cross-device consistency.

**Multilingual:** the case language is selectable up front. The LLM writes the case content
in the chosen language and the deterministic generators emit it verbatim (see §6).

---

## 2. Project layout

```
Operation_Waldweg/
├── 01_ios_full_fs/      iOS file-system tree (private/var/mobile/…)
├── 02_android_full_fs/  Android file-system tree (data/data/…, data/system/…)
├── 03_windows_triage/   Windows triage (registry hives, EVTX, $Recycle.Bin, LNK …)
├── 04_cloud_exports/    Google Location History (JSON), iCloud sync (CSV)
├── 05_police_records/   missing-person report, interview, autopsy, scene A/V
├── 06_master/           case file, master timeline, solution key, catalogues, docs
├── 07_multimedia/       image/audio/video (incl. a manipulated comparison variant)
├── 08_multilingual/     foreign-language communication content (everyday contacts)
├── 09_build/            generators + validation gates + case_master.yaml
│   ├── generators/      ~33 deterministic artifact generators + gates
│   └── case_master.yaml single source of truth (reference case)
└── CaseForge/           framework layer (registry, profiles, schema, LLM, CLI)
```

---

## 3. Requirements

- Python 3.10+
- `pip install pyyaml` (minimum); for the real tool gates additionally
  `pip install regipy python-evtx LnkParse3` plus a local iLEAPP/ALEAPP.
- Optional (speech synthesis for audio artifacts): [Piper](https://github.com/rhasspy/piper)
  + voice models into `Operation_Waldweg/09_build/piper_voices/` (excluded from the repo due to size).

---

## 4. Quick start — build & validate the reference case

```bash
cd Operation_Waldweg/CaseForge

# Build the reference case (Operation Waldweg)
python3 forge.py build  --root /path/to/build_out

# Run the forensic gates (auto mode: reference -> full solution self-test)
python3 forge.py validate --root /path/to/build_out
```

Expected: all format gates green, `verify_solution` 12/12 (scenario solvable and consistent).

---

## 5. Creating new cases (CaseForge workflow)

The full arc is four stages: **PROPOSE → REVIEW → BUILD → VALIDATE**.

### 5.1 Write the brief

`brief.json` (example):

```json
{
  "deliktart": "Stalking/Harassment",
  "lernziel": "encrypted messengers + location history",
  "language": "en",
  "devices": [
    {"platform": "ios",     "os_profile": "ios_17",     "owner": "Victim"},
    {"platform": "android", "os_profile": "android_14", "owner": "Suspect"}
  ],
  "assets_count": 2
}
```

### 5.2 PROPOSE — let the LLM propose a case

```bash
# A) Claude Cowork (recommended): writes a prompt bundle
python3 forge.py propose --backend cowork --lang en --input brief.json
#    -> put out/proposal_prompt.md to Claude Cowork,
#       save the answer as out/case_spec.json.

# B) Local/offline via ollama (data never leaves the building)
python3 forge.py propose --backend ollama --lang en --model qwen2.5:32b-instruct --input brief.json
```

The LLM produces **only the case proposal** (spec + narrative). Artifacts are then created
**deterministically** — data quality does not depend on the model.

> **ollama notes.** The call is **streamed** (no blocking single read). Use a valid, installed
> tag — check with `ollama list` (e.g. `qwen2.5:7b`, `qwen2.5:14b-instruct`, `llama3.1:8b`;
> `qwen3.5:9b` is **not** a real tag). On a cold start the model is loaded first, which can take
> minutes; tune with `--timeout <seconds>` and point at a remote server with `--url`. If the
> server is unreachable or the model is missing, `forge.py` now reports it immediately instead of
> hanging.

### 5.3 REVIEW — verify/adjust the spec (human in the loop)

Open `out/case_spec.json` and verify/adjust persons, devices, timeline, messages, location
tracks, planted inconsistencies and the solution key. The spec includes an **artifact overview
per device/platform/OS** (see `forge.py catalog`).

### 5.4 BUILD — generate the case deterministically

```bash
python3 forge.py build --root /path/to/NewCase --spec out/case_spec.json
```

`build --spec` automatically invokes the adapter `spec_to_master.py` (spec →
`case_master.yaml`), selects the matching generators per platform and `artifact_classes` via
the registry, and writes a per-case catalogue.

**Content from the spec:** messaging (iMessage, Android WhatsApp 1:1 and groups), location
tracks, browser history (Chrome/Edge/Safari), documents and app sandboxes are read from the
master; where a structure is absent, a documented reference fallback applies. Optional spec
conventions:

```yaml
persons:
  - {id: victim, name: Emma C., phone: "+447700900111"}   # phone -> messaging handle
chat_threads:
  - id: victim_suspect
    channel: imessage            # imessage | whatsapp | sms | *_group
    participants: [victim, suspect]
    messages:
      - {t: "2026-03-01T09:00:00+00:00", from: suspect, text: "..."}
      - {t: "2026-03-01T20:00:00+00:00", from: victim,  text: "...", deleted: true}  # WAL fragment only
location_tracks:
  suspect:
    - {t: "2026-03-01T08:00:00+00:00", lat: 51.50, lon: -0.12, kind: cell, lac: 10, ci: 20}
browser_history:
  ip: [{t: "2026-03-01T07:00:00+00:00", url: "https://...", title: "..."}]
documents:
  - {device: ios, area: downloads, name: Contract.pdf, kind: pdf, lines: ["Investment agreement"]}
app_packages:
  ios:     ["com.coinbase.app"]
  android: ["com.binance.dev"]
```

### 5.5 VALIDATE — cross-check with forensic tools

```bash
python3 forge.py validate --root /path/to/NewCase
```

The gates separate **format checks** (schema/join/parseability/timestamp — apply to every
case) from **reference-solution checks** (Waldweg-specific content). The mode is chosen
automatically (spec-derived case → `format`, reference → `all`) and can be forced with
`--mode all|format|reference`. A freely specified case therefore validates green on its own.

### 5.6 Focused sub-cases (drill a single problem)

Restrict `artifact_classes` per device in the spec (e.g. only `registry`, only `eventlog`,
only `browser`) — registry selection and gates then produce a slim mini-case for a targeted
learning objective.

### 5.7 Individuality & case size (seed + scope)

Every case carries a `meta.generator_seed`. The seed drives **randomised, solution-neutral
identifiers and noise** so that two cases never share the same skeleton: app-container UUIDs,
Windows SID, computer name, IMEI/serial/BSSID, and the selection/order/amount of everyday
noise all vary per seed. Same seed ⇒ byte-stable reproduction; if the spec omits a seed,
CaseForge assigns a random one and stores it. The reference case keeps its fixed seed
`20260125` and therefore its exact known values.

Case size is controlled by `meta.scope: S | M | L | XL` (scales noise volume), with optional
per-class overrides `meta.volume: {documents: 25, browser_noise: 40}` and a global
`meta.noise_density`. CLI shortcuts:

```bash
python3 forge.py build --case MyCase --spec spec.json --seed 4242 --scope XL
```

---

## 6. Language selection (multilingual)

Choose the language up front via `forge.py propose --lang <code>` (or the `language` field in
the brief). Supported out of the box: `de`, `en`, `fr`, `es`, `tr` (BCP-47 locales such as
`en-US` are also accepted). The selection drives:

- the **output language of the LLM proposal** (a hard instruction is injected into the prompt),
- `meta.language_primary` in the generated `case_master.yaml`,
- framework strings (catalogue/console) via `CaseForge/i18n.py`.

Because artifact content is projected verbatim from the spec, the generated case is in the
chosen language. Parts not provided by the spec fall back to the reference content (German).
Add new languages by extending `CaseForge/i18n.py`.

---

## 7. New OS versions / extension

New iOS/Android/Windows version → add a profile under `CaseForge/profiles/<name>.yaml`
(document changed paths/formats/timestamps) and parametrise the affected generators or
register a version-specific variant in `CaseForge/registry.py`. Spec, build, catalogue and
gates stay unchanged.

Full architecture, model and validation documentation:
[`Operation_Waldweg/CaseForge/README.md`](Operation_Waldweg/CaseForge/README.md).

---

## 8. Ethics & guardrails

Synthetic data only; no real personal data; no reproducible offence/procurement instructions;
for sensitive offences **never** incriminating media content, only artifact structures/metadata
and neutral placeholders. These rules are hard-wired into the LLM system prompt
(`CaseForge/prompts/case_proposal_system.md`).

---

## 9. License & citation

Free for educational use with attribution.

> Marc Brandt · Institute for Continuing Education · Baden-Württemberg State Police University · 2026

Accompanying academic paper on the methodology (agent-assisted case generation):
[`Operation_Waldweg/06_master/Paper_Agent_Assisted_Case_Generation_EN.md`](Operation_Waldweg/06_master/Paper_Agent_Assisted_Case_Generation_EN.md)
· German: [`…/Paper_Agentengestuetzte_Fallgenerierung.md`](Operation_Waldweg/06_master/Paper_Agentengestuetzte_Fallgenerierung.md)
