# Agent-Assisted Generation of Synthetic, Tool-Validated Forensic Training Cases

### A deterministic projection architecture, demonstrated with "Operation Waldweg" and the CaseForge framework

**Marc Brandt**
Institute for Continuing Education · Baden-Württemberg State Police University (HfPolBW)
Contact: mb4n6@gmx.de · 2026

*German version: [Paper_Agentengestuetzte_Fallgenerierung.md](Paper_Agentengestuetzte_Fallgenerierung.md)*

---

## Abstract

Digital-forensics education suffers from a structural data problem: real exhibits are legally
restricted and cannot be shared, freely available practice datasets are scarce, age quickly,
and rarely cover a complete, cross-device crime scene. This paper presents an architecture
that produces synthetic training cases **not as static datasets but as reproducible
projections of a single source of truth**, joining two normally separate worlds: the
**deterministic, schema-faithful generation of artifacts** and the **generative case design
by language-model agents**. At its core is the principle *"one truth, many projections"*: a
central case description (`case_master.yaml`) is projected into all device artifacts — iOS,
Android, Windows, cloud, wearable, multimedia — which are created in their **native formats**
(SQLite, plist, registry hives, EVTX, BIOME/SEGB, LNK) at forensically correct paths. An LLM
agent performs **only the case design** (proposing a schema-conformant specification), while
the data itself is produced **deterministically and model-independently**; a mandatory
**human-in-the-loop** step and **ethics guardrails** embedded in the system prompt safeguard
correctness and harmlessness. Realism is not asserted but **demonstrated by cross-checking
with real open-source forensic tools** (iLEAPP, ALEAPP, regipy, python-evtx, LnkParse3). A
novel two-tier validation concept separates **format-level** from **solution-level** checks,
making even freely specified cases independently verifiable. Beyond the individual case, the
framework grows into a **forensic expert system**: a knowledge base of reusable *forensic
problems* spanning computer forensics, mobile forensics and app analysis is **taught** by the
language model from expert free text (with mandatory human approval) and selected automatically
or manually at build time — a concrete mechanism for mutually enriching machine and human
expertise. The framework is **multilingual**:
the case language is selected up front and flows into the LLM proposal and the case metadata.
Using the reference case "Operation Waldweg" — a fictional homicide with three devices and
planted inconsistencies — we show the approach to be sound, reproducible and didactically
valuable. We position the method within the agent-based tool landscape and discuss use,
limitations and transferability for lecture and workshop.

---

## 1. Introduction

Anyone who teaches digital forensics knows the dilemma: the most valuable learning objects —
real seized media — must stay out of the classroom for reasons of data protection, personality
rights and the secrecy of proceedings. What remains is a handful of public reference corpora
that are didactically useful but limited in device diversity, outdated in their app and OS
versions, and rarely designed as a coherent, cross-device **crime scene**. As a result,
learners practise individual artifact types in isolation but seldom train the actual core
competency of forensics: **reconstructing a defensible hypothesis from contradictory traces
across several devices.**

Synthetic data solve the legal problem — but raise a new one: **credibility**. A simplified,
"invented" SQLite schema may convince in a demo but is immediately exposed when processed with
standard tools, which expect exact tables, columns and joins. A synthetic data basis is only
valuable for training if it **behaves like a real logical extraction** — i.e. runs cleanly
through the very parsers that would be used in a real case.

This paper combines three observations into one architecture:

1. **Truth belongs in exactly one source.** Cross-device consistency can only be guaranteed if
   all artifacts are deterministically *projected* from *one* authoritative case description —
   not if each database is filled by hand.
2. **Realism is provable, not assertable.** Instead of postulating authenticity, one runs the
   real open-source forensic tools over the generated artifacts as an **acceptance gate**.
3. **Language models are excellent case authors but poor database writers.** Use their strength
   (coherent, creative, contradiction-rich plot design) and keep them strictly away from data
   generation, which must remain deterministic.

From these principles **CaseForge** emerged — a framework that turns a short brief (offence,
exhibits, OS versions, learning objective) into a complete, tool-validated forensic case, with
"Operation Waldweg" as its first fully worked reference case. This paper describes the
methodology, the agent layer and validation, and addresses researchers and educators who wish
to use synthetic cases for research, lecture and workshop.

---

## 2. Related work

Generating synthetic forensic traces is not a new field; the architecture presented here
positions itself as follows.

**Image and disk generators.** *ForGe* (Visti et al.) generates synthetic NTFS images with
planted "trivial" and "hidden" files and suits data-hiding exercises on Windows exhibits.
*hystck* (formerly *forensig2*) goes further and simulates real user behaviour in virtual
machines, producing realistic disk and network artifacts — highest realism for Windows noise,
but with considerable operational overhead and no explicit, checkable case logic.

**Smartphone-focused frameworks.** *TraceGen* (DFRWS/FSI:DI context) is conceptually the
closest relative: a framework specifically for synthetic smartphone artifacts (app usage,
browsing, location) based on simulated activity sequences. CaseForge shares the goal of
schema-faithful smartphone traces but adds the cross-device single-source projection and the
agent-based design layer.

**Evidence-package approaches.** *EviPlant/EviGen* separate a base image from injectable
"evidence packages", allowing several difficulty levels to be derived from one base. This idea
of separable, case-dependent traces reappears in CaseForge's separation of *noise* (everyday
background) and *case-relevant* traces.

**Reference and benchmark corpora.** *NIST CFReDS* and *Digital Corpora* (e.g. M57-Patents)
serve as a yardstick for "what real looks like" and as a benchmark for the plausibility of
synthetic data.

**Language models in forensics.** LLM use has so far concentrated on *analysis support*
(triage, report drafting, artifact explanation). The approach pursued here is complementary
and, as far as can be surveyed, unusual: the language model is used not for **analysis** but
for the **construction** of training cases — and deliberately only at the conceptual level, not
at the data level.

**Delineation.** No existing framework was adopted as-is. The decision favoured **bespoke,
deterministic Python generators** (full control over case logic), with TraceGen/EviPlant as
architectural models and the open-source parsers as the acceptance authority.

---

## 3. Problem statement and requirements

The training mandate and the tool landscape yield concrete requirements:

- **R1 — Column-level schema fidelity.** Artifacts must carry the real tables, columns, joins
  and time formats so that standard tools process them without error.
- **R2 — Cross-device consistency.** An event must be reflected coherently in the traces of
  *all* involved devices (e.g. message ↔ location ↔ device activity).
- **R3 — Determinism and reproducibility.** Same input ⇒ bit-stable output (seed-based), so
  cases remain versionable and traceable.
- **R4 — Didactic controllability.** Learning objectives, difficulty and targeted
  contradictions must be *designable*, not accidental.
- **R5 — Updatability.** New iOS/Android/Windows versions must be representable with reasonable
  effort.
- **R6 — Provable realism.** Authenticity must be *evidenced* by real tools.
- **R7 — Harmlessness.** No real personal data, no reproducible offence/procurement
  instructions, no incriminating content for sensitive offences.

The central technical challenge is not the individual database but **consistency across formats
and devices** with simultaneously **provable** schema fidelity.

---

## 4. Methodology: one truth, many projections

### 4.1 Single source of truth

The core is an authoritative case description, `case_master.yaml`. It contains persons, devices
(with OS versions), locations, an event-based timeline, communication threads, planted
inconsistencies and the solution key. **No generator invents its own content** — each
*projects* a slice of this truth into its target format. This directly satisfies R2 (because
all traces stem from the same source they are necessarily consistent) and R3 (because the
projection is deterministic).

### 4.2 Deterministic, schema-faithful generators

Around 33 generators create the artifacts in their native formats:

- **SQLite** with real schemas (e.g. iOS `sms.db` with `message/handle/chat/*_join`; Android
  WhatsApp in the normalised `message/jid/chat` model rather than the legacy `key_remote_jid`
  schema; `Photos.sqlite` in its multi-table model).
- **plist** (binary/XML), **registry hives** in the `regf` binary format (custom hive writer),
  **EVTX** as template-based BinXML, **BIOME/SEGB v2** (protobuf segments that replace
  `knowledgeC.db` from iOS 17), **LNK** shell links and **$I** recycle-bin records.
- **Time-format diversity** across all relevant epochs — Apple CFAbsolute (nanoseconds), Unix
  milliseconds, WebKit/Chrome microseconds, FILETIME — as a particularly valuable exercise.

A shared loader module (`case_master_io.py`) provides the generators with structured access to
the truth. Where a content structure is missing in the master, a **documented reference
fallback** applies, so the established reference case stays stable while a new spec actually
determines the content.

### 4.3 Validation as an acceptance gate

Realism (R6) is evidenced by **cross-checking**: the characteristic queries of the real parsers
are run over the generated artifacts — iLEAPP (iOS), ALEAPP (Android), regipy/RegRipper
(registry), python-evtx (event logs), LnkParse3 (LNK), a BIOME parser (SEGB). If these run
cleanly and return plausible rows, schema fidelity is demonstrated. These gates are reproducible
and part of the pipeline.

---

## 5. The agent layer: design by language models

### 5.1 Division of labour — and why it matters

The conceptual core of the approach is a **sharp division of labour**:

> The language model designs the **case**. The generators create the **data**.

An LLM is excellent at turning "stalking, two smartphones, learning objective location history"
into a coherent, credible plot with persons, motives, a timeline and subtle contradictions. It
is, however, unsuited to writing byte-exact registry hives or WAL fragments. Consequently the
agent produces **only a schema-conformant specification** (case spec, JSON) — that is, the
*truth*, not the *artifacts*. An important consequence: **data quality does not depend on the
model.** Even a mid-sized local model yields usable specifications because the downstream
generation is deterministic.

### 5.2 The pipeline: PROPOSE → REVIEW → BUILD → VALIDATE

![Agentic division of labour in CaseForge: the LLM agent designs the case as a schema-conformant specification (PROPOSE), a mandatory human REVIEW verifies and approves it, deterministic generators project the single source of truth into native-format artifacts (BUILD), and real forensic tools evidence schema fidelity (VALIDATE) — enclosed by hard-wired ethics guardrails.](figures/agentic_approach_en.svg)

*Figure 1: Agentic division of labour — the agent designs the case, audited deterministic code builds and validates the data, the human decides.*

1. **PROPOSE.** From the user brief the framework builds a prompt bundling the "case designer"
   system prompt, the available OS profiles, the generator catalogue (registry), the list of
   forensic tools and the case-spec JSON schema. The agent answers with a spec proposal plus an
   **artifact overview per device/platform/OS**.
2. **REVIEW.** The human verifies and adjusts the spec — persons, timeline, messages, location
   tracks, contradictions, solution key. This step is **mandatory**.
3. **BUILD.** An adapter projects the spec onto `case_master.yaml`; the registry selects the
   matching generators by platform and `artifact_classes`; artifacts are produced
   deterministically, plus a per-case catalogue.
4. **VALIDATE.** The forensic gates check the artifacts (see 5.4).

### 5.3 Backends and model choice

Two operating modes cover different security requirements:

- **Claude Cowork** (recommended for highest proposal quality) — best reasoning and consistency,
  German-capable, ideal for complex multi-device plots and the deliberate design of
  contradictions.
- **Local/offline (ollama)** — when data must not leave the building. Recommended default
  `qwen2.5:32b-instruct` (very good German, reliable schema JSON), below it `qwen2.5:14b` (24 GB
  card) or `qwen2.5:7b`/`llama3.1:8b` (laptop), at the top `llama3.3:70b` (max local quality).
  For strictly valid JSON, a JSON-schema constraint or `format=json` is advisable.

Since the model only designs, the pragmatic recommendation is: **Cowork for the draft**, a local
model for fast iteration.

### 5.4 Two-tier validation: format vs. solution

A novelty over classic acceptance tests hard-wired to *one* case is the **mode separation** of
the gates. Each check is classified as

- a **format check** — schema, joins, parseability, timestamp decoding; applies to **every**
  case — or
- a **reference-solution check** — case-specific content (particular texts, values, coordinates).

The mode is chosen automatically: a spec-derived case is checked in `format` mode (does the data
basis run cleanly through the real parsers?), the canonical reference case additionally in
solution mode (is the scenario solvable and consistent?). Only this separation makes **freely
specified cases independently validatable** without giving up the reference case's strict
self-check.

### 5.5 Ethics guardrails in the system prompt

Requirement R7 is not optional but **hard-wired into the case designer's system prompt** and
thus part of every generation: synthetic data only; no real persons, addresses, phone numbers,
accounts; no reproducible offence, construction or procurement instructions and no malicious
code; for sensitive offences (e.g. child sexual abuse material) **never** incriminating media
content, only artifact **structures**/metadata and neutral, didactic placeholders. Every case
carries the immutable marker `synthetic_training_data_only`.

### 5.6 A knowledge base of forensic problems (expert system)

![Knowledge-base loop in CaseForge: when teaching, the LLM structures expert free text into a draft that a human approves — growing the knowledge base of forensic problems. When applying, problems are selected automatically, deterministically or manually, woven into PROPOSE (forensic_problems), reviewed by a human and built deterministically. Two human-in-the-loop points, enclosed by ethics guardrails.](figures/knowledge_base_en.svg)

*Figure 2: The knowledge-base loop — humans enrich the knowledge (teaching, left), the AI composes cases from it (applying, right); the curated corpus is the hub.*

Beyond the individual case, CaseForge maintains a **knowledge base of reusable forensic
problems** (`knowledge/problems/`) drawn from computer forensics, mobile forensics and app
analysis. A *forensic problem* is deliberately case-independent and describes a characteristic
challenge — e.g. the source conflict between a cached Wi-Fi association and a simultaneous
cell-tower fix, a deleted message recoverable only as a WAL fragment, USB exfiltration across
correlated Windows artifacts, or timestomping (`$SI` vs. `$FN`). Each entry carries a learning
objective, the affected artifact classes, a **detection method** (instructor knowledge),
pitfalls, an ethics flag and its provenance; only human-**approved** entries flow into cases.

This gives the framework a concrete answer to how **machine and human expertise can enrich one
another** — through a twofold division of labour. During **teaching**, the language model
structures an expert's **free text** into a schema-conformant draft, which a human approves
after review. This addresses the classic *knowledge-acquisition bottleneck* of expert-systems
research: the costly structuring is delegated to the model as a knowledge-engineering assistant,
while domain authority stays with the human. During **application**, either the model itself
(`auto`), a deterministic LLM-free matcher (`match`), or the human (explicit selection) picks
suitable problems; their identifiers land in the spec field `forensic_problems`, activate the
corresponding artifact classes and appear with their detection method in the case report.
Determinism, tool validation and ethics guardrails remain untouched — the knowledge base governs
**selection and composition**, not byte generation. The result is two human-in-the-loop points
(knowledge approval *and* case review) and two complementary LLM contributions (structuring
*and* composing): an expert system whose knowledge grows without sacrificing the rigour of
deterministic, tool-evidenced case generation.

### 5.7 Multilingualism

The case language is selected up front (`forge.py propose --lang <code>`; supported out of the
box: de, en, fr, es, tr, plus BCP-47 locales). The selection injects a hard output-language
instruction into the LLM prompt, sets `meta.language_primary` in the generated master, and
localises framework strings via `CaseForge/i18n.py`. Because artifact content is projected
verbatim from the spec, the generated case is in the chosen language; parts not provided by the
spec fall back to the reference content. New languages are added by extending the i18n layer.

---

## 6. Implementation: the CaseForge architecture

The framework layer consists of few, clearly separated components:

| Component | Role |
|---|---|
| `registry.py` | Metadata index of all generators (platform, OS minimum, artifact class, paths, format, **cross-check tool**); drives selection and catalogue. |
| `profiles/*.yaml` | OS profiles (e.g. `ios_17` → BIOME instead of `knowledgeC`); new OS version = new profile. |
| `schema/case_spec.schema.json` | JSON schema of the case spec (input/proposal format). |
| `prompts/case_proposal_system.md` | System prompt of the case designer including ethics rules. |
| `i18n.py` | Language layer: output-language instruction, framework strings, locale metadata. |
| `llm.py` | Prompt construction and backends (Cowork, ollama). |
| `spec_to_master.py` | Adapter spec → `case_master.yaml` (projection of the verified truth). |
| `knowledge_base.py` + `knowledge/` | Knowledge base of forensic problems: schema, taxonomy, corpus, deterministic matching and the teaching workflow (free text → LLM → approval). |
| `catalog.py` | Artifact overview per device/platform/OS (MD/CSV). |
| `gate_common.py` | Format/reference mode of the validation gates. |
| `forge.py` | CLI orchestrator: `propose · build · validate · run · catalog`. |

The actual generators remain separate from the framework layer and are driven through the
registry — a design that reduces extending by a new artifact type or OS version to adding *one*
registry line and possibly *one* profile (R5).

---

## 7. Case study: Operation Waldweg

The reference case is a fictional homicide (ref. AZ 2026-KK-00892) in a rural area near
Stuttgart, focus window 24–25 January 2026. It involves the victim's iPhone (iOS 17), a
suspect's Samsung (Android 14) and Windows 11 triage image, plus cloud, wearable and multimedia
traces.

The case is deliberately **not trivially solvable**: it contains five planted inconsistencies —
e.g. a **source conflict** between a stale cached Wi-Fi association ("home") and a simultaneous,
less accurate cell-tower location near the scene; a **deleted message** recoverable only as a
WAL fragment; and a **sync gap** between cloud location history and device cache. Such
constellations train the core competency "no artifact is ground truth" and force learners into
**multi-source correlation** rather than single-artifact reading.

Accompanying material includes a credible case file (missing-person report, interview, autopsy),
a consolidated master timeline, a solution key with red herrings and decisive correlations, and
realistic **noise** in magnitudes that feel real (several thousand messages and activity events,
foreign-language everyday contacts).

---

## 8. Validation and results

The reference case passes the pipeline green and reproducibly: the format gates of all three
device classes pass, and the solution self-check confirms the scenario's consistency and
solvability. Decisive for the **framework's** viability, however, is the second proof: a
**freely specified case** (different offence, different persons, own message and location
content) is built from a spec and passes format validation **on its own** — the reference case's
case-specific solution checks are correctly skipped. This demonstrates that not merely a single
dataset "looks real", but that the **method** generates arbitrary, schema-faithful cases. The
multilingual path was likewise verified end-to-end: an English-language spec produces an
English case that passes format validation, while the reference case retains its full
self-check.

The strength of the approach lies in the interplay: determinism ensures reproducibility (R3),
the single-source projection ensures consistency (R2), the real parsers evidence schema fidelity
(R1, R6), and the agent layer delivers didactic controllability (R4) with minimal effort for new
OS versions (R5).

---

## 9. Use in lecture and workshop

Several immediately usable scenarios arise for teaching:

- **Full-case exercise.** Learners receive the three device extracts and reconstruct hypothesis
  and timeline via the tool chain — including the planted contradictions.
- **Focused sub-cases.** Restricting `artifact_classes` in the spec yields slim mini-cases for a
  single learning objective (only ShellBags, only BIOME, only EVTX logons) — ideal for short
  exercise blocks.
- **Live demonstration of the agent workflow.** In a workshop, PROPOSE → REVIEW → BUILD →
  VALIDATE can be shown in minutes; the REVIEW step makes the role of human expert oversight and
  the ethics guardrails tangible.
- **Variant generation.** From one brief, several difficulty levels can be derived, e.g. through
  additional noise layers or subtler contradictions.

The agent lecture can use the approach as a model of **responsible division of labour between
human and AI**: creative design by the model, deterministic execution by audited code, binding
expert and ethical control by the human.

---

## 10. Limitations

The approach produces **logical extractions**, not bit-exact physical full images; Secure
Enclave, keystore, AFU/BFU states and raw NAND encryption cannot be reproduced 1:1 synthetically
— a deliberate, documented boundary. Some format families (SRUM/ESE, `$MFT`/`$UsnJrnl`, valid
prefetch SCCA, ShimCache) are flagged as follow-up work. App schemas drift per version; the
coupling of app to OS version must be maintained. Where a spec does not supply a given content
structure, the generator falls back to the (German) reference content; a fully localised case
therefore requires the spec to provide that content. Finally, generative design relies on the
human REVIEW — the agent **proposes**, it does not decide.

---

## 11. Conclusion and outlook

Synthetic forensic training cases derive their value not from the volume of generated data but
from **consistency, schema fidelity and verifiability**. The architecture presented here
achieves this by deterministically projecting a single source of truth into native formats,
evidencing realism with real forensic tools, and leaving the creative case design to a
language-model agent — with a strict separation of design and data generation, a mandatory
human in the loop, and hard-wired ethics guardrails. "Operation Waldweg" shows that a complete,
cross-device, contradiction-rich case can be produced reproducibly this way; CaseForge shows
that **arbitrary** new cases can be derived from it, in multiple languages.

Future work concerns the full spec parametrisation of all content generators (largely
completed), additional OS profiles (iOS 18, Android 15, Windows 10), broader format coverage
(ESE/SRUM, $MFT) and the automatic generation of task sheet and solution key per case. In the
medium term, the presented knowledge base of forensic problems is a first step towards a
**library approach** in which educators share curated problems (and spec templates), growing a
checkable repertoire of exercise cases — without touching a single real exhibit.

---

## References (selection)

- Visti, H. et al.: *ForGe — Computer Forensic Test Image Generator.*
- Scanlon, M. et al.: *EviPlant / EviGen — Evidence Package Generation for Digital Forensics
  Education.*
- Du, X.; Scanlon, M. et al.: *TraceGen — Synthetic Smartphone Trace Generation* (DFRWS /
  Forensic Science International: Digital Investigation).
- Göbel, T. et al.: *hystck / forensig2 — VM-based Generation of Realistic Forensic Disk and
  Network Artefacts.*
- National Institute of Standards and Technology: *Computer Forensic Reference Data Sets
  (CFReDS).*
- Garfinkel, S. et al.: *Digital Corpora / M57-Patents
  
---

> **Usage note.** This paper accompanies the "Operation Waldweg / CaseForge" project and may be
> used freely for lecture, workshop and teaching with attribution.
> Marc Brandt · Baden-Württemberg State Police University · 2026.
