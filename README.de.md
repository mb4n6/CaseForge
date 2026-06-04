# Operation Waldweg — Synthetischer Forensik-Trainingsfall & CaseForge-Framework

**Vollständig synthetisches, tool-validiertes Mehrgeräte-Fallszenario für die IT-Forensik-Ausbildung**
Hochschule für Polizei Baden-Württemberg · Verfasser: Marc Brandt (Dozent IT-Forensik)

> **AUSSCHLIESSLICH FIKTIVE DATEN.** Alle Personen, Adressen, Rufnummern, Konten,
> Kommunikationsinhalte, Medien und Ereignisse sind frei erfunden und dienen
> ausschließlich Ausbildungs- und Forschungszwecken. Lose an reale Phänomene
> *angelehnt*, ohne jeden Bezug zu realen Personen oder Vorgängen.
> Jeder erzeugte Fall trägt das Kennzeichen `synthetic_training_data_only`.
>
> 🇬🇧 English version: [README.md](README.md)

> **Mehrsprachig:** Die Fallsprache wird vorab gewählt (`forge.py propose --lang de|en|fr|es|tr`
> bzw. Feld `language` in der Eingabe). Das LLM verfasst die Fallinhalte in dieser Sprache, die
> deterministischen Generatoren übernehmen sie wortgetreu; `meta.language_primary` wird gesetzt.
> Nicht vom Spec gelieferte Teile nutzen den Referenz-Fallback (Deutsch). Sprachen erweiterbar in
> `CaseForge/i18n.py`.

---

## 1. Worum es geht

„Operation Waldweg" ist ein synthetischer Tötungsdelikt-Fall (AZ 2026-KK-00892), dessen
digitale Asservate — iPhone (iOS 17), Samsung (Android 14), Windows-11-Triage, Cloud,
Wearable und Multimedia — auf **forensisch korrekten Pfaden** und in **schema-getreuen
Originalformaten** (SQLite, plist, Registry-Hives/regf, EVTX, BIOME/SEGB v2, LNK, $I,
JSON/XML) erzeugt werden. Die Artefakte werden gegen **reale Open-Source-Forensiktools**
gegengeprüft (iLEAPP, ALEAPP, regipy/RegRipper, python-evtx, LnkParse3, BIOME-Parser).

Das Projekt ist zugleich ein **Framework** — **CaseForge** —, mit dem sich aus einer
kurzen Eingabe (Delikt, Asservate, OS-Versionen, Lernziel) **neue** synthetische Fälle
LLM-gestützt vorschlagen, nach menschlicher Verifikation deterministisch erzeugen und
gegen Forensiktools validieren lassen.

**Leitprinzip:** *Eine Wahrheit, viele Projektionen* — eine zentrale `case_master.yaml`
ist die einzige Wahrheitsquelle; alle Geräteartefakte werden daraus deterministisch
projiziert. Das garantiert geräteübergreifende Konsistenz.

---

## 2. Projektstruktur

```
Operation_Waldweg/
├── 01_ios_full_fs/      iOS-Dateisystembaum (private/var/mobile/…)
├── 02_android_full_fs/  Android-Dateisystembaum (data/data/…, data/system/…)
├── 03_windows_triage/   Windows-Triage (Registry-Hives, EVTX, $Recycle.Bin, LNK …)
├── 04_cloud_exports/    Google Location History (JSON), iCloud-Sync (CSV)
├── 05_police_records/   Vermisstenanzeige, Vernehmung, Obduktion, Tatort-AV
├── 06_master/           Fallakte, Master-Timeline, Lösungsschlüssel, Kataloge, Doku
├── 07_multimedia/       Bild/Audio/Video (inkl. manipulierter Vergleichsvariante)
├── 08_multilingual/     fremdsprachige Kommunikationsinhalte (Alltagskontakte)
├── 09_build/            Generatoren + Validierungs-Gates + case_master.yaml
│   ├── generators/      ~33 deterministische Artefakt-Generatoren + Gates
│   └── case_master.yaml Single Source of Truth (Referenzfall)
└── CaseForge/           Framework-Schicht (Registry, Profile, Schema, LLM, CLI)
```

---

## 3. Voraussetzungen

- Python 3.10+
- `pip install pyyaml` (Minimum); für die echten Tool-Gates zusätzlich
  `pip install regipy python-evtx LnkParse3` sowie lokal iLEAPP/ALEAPP.
- Optional (Sprachsynthese für Audio-Artefakte): [Piper](https://github.com/rhasspy/piper)
  + Stimmmodelle nach `Operation_Waldweg/09_build/piper_voices/` (nicht im Repo, da groß).

---

## 4. Schnellstart — Referenzfall bauen & validieren

```bash
cd Operation_Waldweg/CaseForge

# Referenzfall (Operation Waldweg) bauen
python3 forge.py build  --root /pfad/zu/build_out

# Forensik-Gates fahren (Auto-Modus: Referenz -> voller Lösungs-Selbsttest)
python3 forge.py validate --root /pfad/zu/build_out
```

Erwartetes Ergebnis: alle Format-Gates grün, `verify_solution` 12/12 (Szenario lösbar
und konsistent).

---

## 5. Neue Fälle erzeugen (CaseForge-Workflow)

Der vollständige Bogen ist vierstufig: **PROPOSE → REVIEW → BUILD → VALIDATE**.

### 5.1 Eingabe formulieren

`eingabe.json` (Beispiel):

```json
{
  "deliktart": "Stalking/Nachstellung",
  "lernziel": "verschlüsselte Messenger + Standortverlauf",
  "devices": [
    {"platform": "ios",     "os_profile": "ios_17",     "owner": "Geschädigte"},
    {"platform": "android", "os_profile": "android_14", "owner": "Beschuldigter"}
  ],
  "assets_count": 2
}
```

### 5.2 PROPOSE — Fall vorschlagen lassen (LLM)

```bash
# A) Claude Cowork (empfohlen): erzeugt ein Prompt-Bundle
python3 forge.py propose --backend cowork --input eingabe.json
#    -> out/proposal_prompt.md in Claude Cowork stellen,
#       Antwort als out/case_spec.json speichern.

# B) Lokal/offline via ollama (Daten verlassen das Haus nicht)
python3 forge.py propose --backend ollama --model qwen2.5:32b-instruct --input eingabe.json
```

Das LLM erzeugt **nur den Fall-Vorschlag** (Spec + Narrativ). Die Artefakte entstehen
anschließend **deterministisch** — die Datenqualität hängt also nicht am Modell.

> **ollama-Hinweis.** Der Aufruf wird **gestreamt** (kein blockierender Einzel-Read). Gültigen,
> installierten Tag verwenden — `ollama list` (z. B. `qwen2.5:7b`, `qwen2.5:14b-instruct`,
> `llama3.1:8b`; `qwen3.5:9b` ist **kein** gültiger Tag). Beim Cold-Start wird das Modell zuerst
> geladen (kann Minuten dauern) — über `--timeout <sek>` steuerbar, Remote-Server über `--url`.
> Ist der Server nicht erreichbar oder das Modell nicht vorhanden, meldet `forge.py` das jetzt
> sofort statt zu hängen.

### 5.3 REVIEW — Spec prüfen/anpassen (Mensch-in-the-loop)

`out/case_spec.json` öffnen und Personen, Geräte, Timeline, Nachrichten, Standortspuren,
geplante Widersprüche und Lösungsschlüssel verifizieren bzw. anpassen. Der Spec enthält
eine **Artefaktübersicht je Gerät/Plattform/OS** (siehe `forge.py catalog`).

### 5.4 BUILD — Fall deterministisch erzeugen

```bash
python3 forge.py build --root /pfad/zu/NeuerFall --spec out/case_spec.json
```

`build --spec` ruft automatisch den Adapter `spec_to_master.py` auf (Spec →
`case_master.yaml`), wählt über die Registry die passenden Generatoren je Plattform und
`artifact_classes` und schreibt zusätzlich einen Fall-Katalog.

**Inhalte aus dem Spec:** Messaging (iMessage, Android-WhatsApp) und Standortspuren lesen
ihre Inhalte aus dem Master; fehlt eine Struktur, greift ein dokumentierter
Referenz-Fallback. Optionale Spec-Konventionen:

```yaml
persons:
  - {id: opfer, name: Petra S., phone: "+4917000001111"}   # phone -> Messaging-Handle
chat_threads:
  - id: opfer_taeter
    channel: imessage            # imessage | whatsapp | sms
    participants: [opfer, taeter]
    messages:
      - {t: "2026-03-01T09:00:00+01:00", from: taeter, text: "..."}
      - {t: "2026-03-01T18:30:00+01:00", from: opfer,  text: "...", deleted: true}  # nur WAL-Fragment
location_tracks:
  taeter:
    - {t: "2026-03-01T08:00:00+01:00", lat: 48.40, lon: 9.99, kind: cell, lac: 100, ci: 200}
    - {t: "2026-03-01T08:10:00+01:00", lat: 48.41, lon: 9.98, kind: wifi, bssid: "aa:bb:.."}
```

### 5.5 VALIDATE — gegen Forensiktools gegenprüfen

```bash
python3 forge.py validate --root /pfad/zu/NeuerFall
```

Die Gates trennen **Format-Checks** (Schema/Join/Parsebarkeit/Timestamp — gelten für
jeden Fall) von **Referenz-Lösungs-Checks** (Waldweg-spezifische Inhalte). Der Modus wird
automatisch gewählt (Spec-abgeleiteter Fall → `format`, Referenz → `all`) und ist via
`--mode all|format|reference` erzwingbar. Ein frei spezifizierter Fall validiert so
eigenständig grün.

### 5.6 Fokussierte Teilfälle (ein Teilproblem üben)

Im Spec je Gerät `artifact_classes` einschränken (z. B. nur `registry`, nur `eventlog`,
nur `browser`) — Registry-Auswahl und Gates erzeugen dann einen schlanken Mini-Fall für
ein gezieltes Lernziel.

---

## 6. Neue OS-Versionen / Erweiterung

Neue iOS/Android/Windows-Version → neues Profil unter `CaseForge/profiles/<name>.yaml`
anlegen (geänderte Pfade/Formate/Timestamps dokumentieren) und betroffene Generatoren
parametrisieren bzw. eine versionsspezifische Variante in `CaseForge/registry.py`
registrieren. Spec, Build, Katalog und Gates bleiben unverändert.

Die vollständige Architektur-, Modell- und Validierungs­dokumentation liegt in
[`Operation_Waldweg/CaseForge/README.md`](Operation_Waldweg/CaseForge/README.md).

---

## 7. Ethik & Leitplanken

Nur synthetische Daten; keine realen Personendaten; keine reproduzierbaren
Tat-/Beschaffungsanleitungen; bei sensiblen Delikten **nie** inkriminierende
Medieninhalte, sondern ausschließlich Artefakt-Strukturen/Metadaten und neutrale
Platzhalter. Diese Regeln sind im LLM-System-Prompt
(`CaseForge/prompts/case_proposal_system.md`) fest verankert.

---

## 8. Lizenz & Zitation

Frei für Ausbildungszwecke mit Namensnennung.

> Marc Brandt · Institut für Fortbildung · Hochschule für Polizei Baden-Württemberg · 2026

Begleitendes akademisches Paper zur Methodik (agenten-gestützte Fallgenerierung):
[`Operation_Waldweg/06_master/Paper_Agentengestuetzte_Fallgenerierung.md`](Operation_Waldweg/06_master/Paper_Agentengestuetzte_Fallgenerierung.md).
