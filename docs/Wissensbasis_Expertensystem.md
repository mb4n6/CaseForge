# CaseForge als forensisches Expertensystem — Wissensbasis & Anlernen

*Konzept und Bedienung der Problemstellungs-Wissensbasis. Begleitet das CaseForge-Framework
und die Paper (`paper/`). Stand: 2026.*

---

## 1. Motivation: vom Fall-Generator zum Expertensystem

CaseForge erzeugt synthetische, tool-validierte Forensik-Trainingsfälle nach dem Prinzip
*„Eine Wahrheit, viele Projektionen"*. Bisher beschrieb ein Case-Spec **einen konkreten Fall**.
Die hier dokumentierte Erweiterung hebt das Framework auf eine zweite Ebene: eine **Wissensbasis
wiederverwendbarer forensischer Problemstellungen**, aus der sich Fälle zusammensetzen lassen.

Damit wird die klassische akademische Frage adressiert, **wie menschliches Expertenwissen und KI
kombiniert werden** — und insbesondere, wie sich **KI-Wissen mit menschlichem Expertenwissen
anreichern** lässt. Die Antwort von CaseForge ist eine bewusste, doppelte Arbeitsteilung:

- **Menschen kuratieren Wissen.** Erfahrene Forensiker:innen halten charakteristische
  Problemstellungen fest (Lösungswege, Fallstricke, Artefaktbezug). Nur **freigegebenes** Wissen
  fließt in Fälle ein.
- **Das LLM senkt die Hürde und wendet das Wissen an.** Es hilft beim **Anlernen**
  (Freitext → strukturierter Entwurf) und beim **Anwenden** (Auswahl und Verweben passender
  Problemstellungen in neue Fälle). Es **entscheidet aber nie allein**.

Dies löst zugleich den in der Expertensystem-Literatur bekannten *knowledge-acquisition
bottleneck*: Die Strukturierung von Wissen — traditionell der teure Flaschenhals — übernimmt das
LLM als „Wissensingenieur-Assistent", während der Mensch die fachliche Hoheit behält.

## 2. Wissensrepräsentation: die Problemstellung

Eine **Problemstellung** (`knowledge/problems/<id>.yaml`) ist die Wissenseinheit. Sie ist bewusst
**fallunabhängig** und beschreibt eine wiederkehrende forensische Herausforderung, nicht einen
konkreten Tatablauf. Schema: `knowledge/schema/problem.schema.json`.

| Feld | Bedeutung |
|---|---|
| `id`, `title` | stabiler Slug + sprechender Titel |
| `category` | `computer_forensics` \| `mobile_forensics` \| `app_analysis` |
| `subdomains`, `platforms`, `difficulty` | kontrolliertes Vokabular (`taxonomy.yaml`) |
| `learning_objective` | didaktisches Ziel in einem Satz |
| `description` | die Problemstellung in Expertensprache |
| `artifact_classes`, `registry_refs` | Bezug zu Registry-Artefaktklassen/Generatoren |
| `case_hooks` | **wie** die Problemstellung in einen Fall einwebt: zu aktivierende Artefaktklassen, `planted_inconsistency`-Vorlage (≥2 widersprüchliche Quellen), `timeline_hint` |
| `detection_method` | **Lösungsweg** (Dozentenwissen) |
| `pitfalls` | typische Fehlschlüsse / red herrings |
| `ethics` | `sensitive`-Flag + Hinweise (bei sensiblen Delikten nur Strukturen/Metadaten) |
| `provenance` | `source` (expert \| llm_extracted \| llm_extracted_reviewed), `status` (draft \| approved \| deprecated), `author`/`reviewed_by`/`created` |

Nur Einträge mit `provenance.status: approved` werden beim Fallbau verwendet. Der mitgelieferte
Seed-Korpus umfasst 12 Problemstellungen über alle drei Kategorien (mehrere davon aus dem
Referenzfall „Operation Waldweg" abgeleitet).

## 3. Anlernen: Freitext → LLM-Struktur → menschliche Freigabe

Der Anlern-Pfad ist so niedrigschwellig wie möglich gehalten — **kein Formular-Ausfüllen**, kein
Schema-Studium:

1. **Freitext.** Die/der Expert:in schreibt formlos, was die Problemstellung ausmacht (gern aus
   einer echten, **anonymisierten** Fallbeobachtung).
2. **Strukturierung (LLM).** `forge teach` bündelt einen Extraktions-System-Prompt
   (`knowledge/prompts/knowledge_extraction_system.md`), die Taxonomie, die erlaubten
   Artefaktklassen und das Schema mit dem Freitext. Das LLM gibt **ein YAML-Dokument** der
   Problemstellung aus (`status: draft`). Die Ethik-Leitplanken sind im Extraktions-Prompt fest
   verankert (Anonymisierung, keine Anleitungen, Sensibilitäts-Flag).
3. **Freigabe (Mensch).** Der Entwurf landet in `knowledge/incoming/`. Nach Sichtung gibt ein
   Mensch ihn frei; CaseForge validiert gegen das Schema, setzt `status: approved`, vermerkt
   `reviewed_by` und verschiebt den Eintrag nach `knowledge/problems/`.

```bash
# Cowork (Claude ist das LLM):
python3 forge.py teach --input expertentext.txt
#   -> out/teach_prompt.md in Claude Cowork stellen; YAML-Antwort als
#      knowledge/incoming/<id>.draft.yaml speichern
# ODER offline:
python3 forge.py teach --input expertentext.txt --backend ollama --model qwen2.5:32b-instruct

python3 forge.py teach --list-drafts
python3 forge.py teach --approve <id> --by "Marc Brandt"
```

Die Trennung **Vorschlag (LLM) / Freigabe (Mensch)** spiegelt exakt die Fall-Pipeline
(PROPOSE/REVIEW) — diesmal auf der Wissensebene. So wird das Framework-/KI-Wissen kontrolliert mit
menschlicher Expertise **angereichert**.

## 4. Anwenden: Auswahl beim Fallbau

Beim Fall-Vorschlag (`forge propose`) lassen sich Problemstellungen auf drei Wegen einbinden:

- **`--problems auto`** — das LLM erhält den Problemstellungs-Katalog und wählt **eigenständig**
  2–4 zueinander passende Einträge zu Delikt und Lernziel und webt sie ein.
- **`--problems match`** — ein **deterministischer**, LLM-freier Matcher (Token-Overlap +
  Plattform-/Delikt-Heuristik in `knowledge_base.match`) schlägt offline passende IDs vor.
- **`--problems id1,id2,…`** — der Mensch wählt **explizit** aus (`forge problems --list/--match/
  --show` unterstützen die Auswahl).

Die gewählten IDs schreibt das LLM in das Spec-Feld `forensic_problems`. Beim Build:

1. `spec_to_master.py` trägt `forensic_problems` in `meta` (für Report/Determinismus).
2. `forge build` aktiviert die zugehörigen Artefaktklassen auf bereits eingeschränkten Geräten
   (Slim-/Teilfälle bleiben gezielt, Vollfälle unverändert vollständig).
3. `gen_report.py` rendert aus dem Korpus einen Dozenten-Abschnitt **„Forensische
   Problemstellungen & Lösungswege"** (Lernziel, Lösungsweg, Fallstricke je Problemstellung).

Determinismus, Tool-Validierung und Ethik der erzeugten Artefakte bleiben dabei vollständig
erhalten — die Wissensbasis steuert **Auswahl und Komposition**, nicht die Byte-Erzeugung.

## 5. Architektur-Einordnung

```
   Experten-Freitext ──teach──►  LLM (Wissensingenieur)  ──►  Entwurf (draft)
                                                                  │  REVIEW (Mensch)
                                                                  ▼
                                            knowledge/problems/*.yaml  (approved)
                                                                  │
   Nutzereingabe ──propose(--problems auto|match|fix)──►  Auswahl/Komposition
                                                                  │
                                                  Case-Spec.forensic_problems
                                                                  │  BUILD (deterministisch)
                                                                  ▼
                            Artefakte + Fall-Report (Lösungswege)  ──VALIDATE──►  Forensik-Tools
```

Zwei Mensch-in-the-loop-Punkte (Wissens-Freigabe **und** Fall-Review) und zwei LLM-Beiträge
(Strukturieren **und** Komponieren) ergeben ein Expertensystem, dessen Wissen wächst, ohne dass
die deterministische, tool-belegte Fallerzeugung an Strenge verliert.

## 6. CLI-Kurzreferenz

```bash
# Wissensbasis
python3 forge.py problems --list [--category C] [--platform P]
python3 forge.py problems --match "<freitext>" [--platform ios,android] [-k 5]
python3 forge.py problems --show <id>
python3 knowledge_base.py validate          # gesamten Korpus gegen Schema prüfen

# Anlernen
python3 forge.py teach --input text.txt [--backend cowork|ollama]
python3 forge.py teach --list-drafts
python3 forge.py teach --approve <id> --by "Name"

# Anwenden
python3 forge.py propose --problems auto|match|none|id1,id2,... --input eingabe.json
```

## 7. Grenzen & nächste Stufen

- Der Offline-Matcher ist bewusst einfach (lexikalisch); für feineres Ranking ließe sich optional
  ein Embedding-Backend ergänzen (ändert die Determinismus-Eigenschaften nicht, da nur die
  **Auswahl** betroffen ist).
- Problemstellungen referenzieren Artefaktklassen; ein automatischer Abgleich „verlangt die
  Problemstellung Klassen, die kein aktives Profil erzeugt?" wäre eine sinnvolle Lint-Stufe.
- Mittelfristig denkbar: ein geteiltes, kuratiertes Korpus mehrerer Lehrender (Bibliotheks-Ansatz)
  — wachsendes, prüfbares Repertoire an Problemstellungen ohne ein einziges reales Asservat.
