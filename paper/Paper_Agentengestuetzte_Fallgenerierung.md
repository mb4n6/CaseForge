# Agenten-gestützte Generierung synthetischer, tool-validierter Forensik-Trainingsfälle

### Eine deterministische Projektionsarchitektur am Beispiel von „Operation Waldweg" und dem CaseForge-Framework

**Marc Brandt**
Institut für Fortbildung · Hochschule für Polizei Baden-Württemberg
Kontakt: mb4n6@gmx.de · Stand: 2026

---

## Zusammenfassung

Die Ausbildung in der digitalen Forensik leidet an einem strukturellen Datenproblem: Echte
Asservate sind rechtlich gebunden und nicht teilbar, frei verfügbare Übungsdatensätze sind
rar, veralten schnell und decken selten einen vollständigen, geräteübergreifenden Tatort
ab. Dieser Beitrag stellt eine Architektur vor, die synthetische Trainingsfälle **nicht als
statische Datensätze, sondern als reproduzierbare Projektionen einer einzigen
Wahrheitsquelle** erzeugt und dabei zwei sonst getrennte Welten verbindet: die
**deterministische, schema-getreue Artefaktgenerierung** und die **generative
Fall-Konzeption durch Sprachmodell-Agenten**. Kern ist das Leitprinzip *„Eine Wahrheit,
viele Projektionen"*: Eine zentrale Fallbeschreibung (`case_master.yaml`) wird in alle
Geräteartefakte — iOS, Android, Windows, Cloud, Wearable, Multimedia — projiziert, die in
ihren **Originalformaten** (SQLite, plist, Registry-Hives, EVTX, BIOME/SEGB, LNK) auf
forensisch korrekten Pfaden entstehen. Ein LLM-Agent übernimmt ausschließlich die
**Fall-Konzeption** (Vorschlag eines schema-konformen Spezifikats), während die eigentlichen
Daten **deterministisch und modellunabhängig** erzeugt werden; ein verpflichtender
**Mensch-in-the-loop-Schritt** und im System-Prompt verankerte **Ethik-Leitplanken** sichern
Korrektheit und Unbedenklichkeit. Die Realitätsnähe wird nicht behauptet, sondern durch
**Gegenprüfung mit realen Open-Source-Forensiktools** (iLEAPP, ALEAPP, regipy, python-evtx,
LnkParse3) nachgewiesen. Ein neuartiges, zweistufiges Validierungskonzept trennt
**formatbezogene** von **lösungsbezogenen** Prüfungen und macht so auch frei spezifizierte
Fälle eigenständig prüfbar. Am Referenzfall „Operation Waldweg" — einem fiktiven
Tötungsdelikt mit drei Geräten und eingebauten Widersprüchen — wird gezeigt, dass der Ansatz
trag­fähig, reproduzierbar und didaktisch wertvoll ist. Der Beitrag ordnet das Vorgehen in
die agentenbasierte Werkzeuglandschaft ein und diskutiert Einsatz, Grenzen und
Übertragbarkeit für Vortrag und Workshops.

---

## 1. Einleitung

Wer digitale Forensik unterrichtet, kennt das Dilemma: Die wertvollsten Lernobjekte — echte
sichergestellte Datenträger — dürfen aus Gründen des Datenschutzes, des Persönlichkeitsrechts
und des Verfahrensgeheimnisses **nicht in die Lehre**. Was bleibt, sind wenige öffentliche
Referenzkorpora, die didaktisch hilfreich, aber in ihrer Gerätevielfalt begrenzt, in ihren
App- und OS-Versionen veraltet und in ihrer Fall-Logik selten als zusammenhängender,
geräteübergreifender **Tatort** angelegt sind. Die Folge ist, dass Lernende einzelne
Artefakttypen isoliert üben, aber selten die eigentliche forensische Kernkompetenz trainieren:
**aus widersprüchlichen Spuren über mehrere Geräte hinweg eine belastbare Hypothese zu
rekonstruieren.**

Synthetische Daten lösen das rechtliche Problem — werfen aber ein neues auf: **Glaubwürdigkeit**.
Ein vereinfachtes, „erfundenes" SQLite-Schema mag in einer Demo überzeugen, fällt aber bei
der Verarbeitung mit Standardtools sofort auf, weil diese exakte Tabellen, Spalten und Joins
erwarten. Eine synthetische Datenbasis ist für die Ausbildung nur dann wertvoll, wenn sie sich
**verhält wie ein echtes logisches Extrakt** — also durch dieselben Parser fehlerfrei läuft, die
auch im realen Fall zum Einsatz kommen.

Dieser Beitrag verbindet drei Beobachtungen zu einer Architektur:

1. **Die Wahrheit gehört in genau eine Quelle.** Geräteübergreifende Konsistenz lässt sich nur
   garantieren, wenn alle Artefakte aus *einer* maßgeblichen Fallbeschreibung deterministisch
   *projiziert* werden — nicht, wenn man jede Datenbank einzeln von Hand befüllt.
2. **Realitätsnähe ist beweisbar, nicht behauptbar.** Statt Authentizität zu postulieren, läuft
   man die realen Open-Source-Forensiktools als **Abnahme-Gate** über die erzeugten Artefakte.
3. **Sprachmodelle sind hervorragende Fall-Autoren, aber denkbar schlechte Datenbankschreiber.**
   Man nutze ihre Stärke (kohärente, kreative, widerspruchsreiche Plot-Konzeption) und halte
   sie strikt von der Datenerzeugung fern, die deterministisch bleiben muss.

Aus diesen Prinzipien ist **CaseForge** entstanden — ein Framework, das aus einer kurzen Eingabe
(Delikt, Asservate, OS-Versionen, Lernziel) einen vollständigen, tool-validierten Forensikfall
erzeugt, und „Operation Waldweg" als dessen erster, vollständig ausgearbeiteter Referenzfall.
Der vorliegende Beitrag beschreibt Methodik, Agentenschicht und Validierung und richtet sich an
Forschende und Lehrende, die synthetische Fälle für Forschung, Vortrag und Workshop einsetzen
wollen.

---

## 2. Verwandte Arbeiten

Die Erzeugung synthetischer forensischer Spuren ist kein neues Feld; die hier vorgestellte
Architektur ordnet sich wie folgt ein.

**Bild- und Datenträger-Generatoren.** *ForGe* (Visti u. a.) erzeugt synthetische
NTFS-Images mit geplanten „trivialen" und „versteckten" Dateien und eignet sich für
Data-Hiding-Übungen auf Windows-Asservaten. *hystck* (vormals *forensig2*) geht einen Schritt
weiter und simuliert in virtuellen Maschinen echtes Nutzerverhalten, wodurch realistische
Disk- und Netzwerk-Artefakte entstehen — höchste Realitätsnähe beim Windows-Noise, allerdings
mit erheblichem Betriebsaufwand und ohne explizite, prüfbare Fall-Logik.

**Smartphone-fokussierte Frameworks.** *TraceGen* (DFRWS/FSI:DI-Umfeld) ist konzeptionell die
nächste Verwandte: ein Framework speziell für synthetische Smartphone-Artefakte (App-Nutzung,
Browsing, Standort) auf Basis simulierter Aktivitätsabläufe. CaseForge teilt das Ziel
schema-getreuer Smartphone-Spuren, ergänzt aber die geräteübergreifende
Single-Source-Projektion und die agentenbasierte Konzeptionsschicht.

**Evidence-Package-Ansätze.** *EviPlant/EviGen* trennen ein Basis-Image von injizierbaren
„Spurenpaketen" und erlauben so, aus einem Grundbestand mehrere Schwierigkeitsgrade
abzuleiten. Diese Idee der separierbaren, fallabhängigen Spuren findet sich in CaseForge in der
Trennung von *Noise* (Alltagsrauschen) und *fallrelevanten* Spuren wieder.

**Referenz- und Benchmark-Korpora.** *NIST CFReDS* und *Digital Corpora* (z. B. M57-Patents)
dienen als Vergleichsmaßstab dafür, „wie echt aussieht", und als Benchmark für die Plausibilität
synthetischer Daten.

**Sprachmodelle in der Forensik.** Der Einsatz von LLMs konzentriert sich bislang auf
*Analyse­unterstützung* (Triage, Berichts­entwurf, Artefakt­erklärung). Der hier verfolgte Ansatz
ist komplementär und, soweit überschaubar, ungewöhnlich: Das Sprachmodell wird nicht zur
**Auswertung**, sondern zur **Konstruktion** von Übungsfällen eingesetzt — und dies bewusst nur
auf der Konzeptebene, nicht auf der Datenebene.

**Abgrenzung.** Kein bestehendes Framework wurde 1:1 übernommen. Die Entscheidung fiel zugunsten
**eigener, deterministischer Python-Generatoren** (volle Kontrolle über die Fall-Logik), mit
TraceGen/EviPlant als Architektur-Vorbild und den Open-Source-Parsern als Abnahme-Instanz.

---

## 3. Problemstellung und Anforderungen

Aus dem Ausbildungsauftrag und der Werkzeuglage ergeben sich konkrete Anforderungen:

- **A1 — Schematreue auf Spaltenebene.** Artefakte müssen die realen Tabellen, Spalten, Joins
  und Zeitformate tragen, sodass Standardtools sie fehlerfrei verarbeiten.
- **A2 — Geräteübergreifende Konsistenz.** Ein Ereignis muss sich in den Spuren *aller*
  beteiligten Geräte stimmig wiederfinden (z. B. Nachricht ↔ Standort ↔ Geräteaktivität).
- **A3 — Determinismus und Reproduzierbarkeit.** Gleiche Eingabe ⇒ bit-stabile Ausgabe
  (seed-basiert), damit Fälle versionierbar und nachvollziehbar bleiben.
- **A4 — Didaktische Steuerbarkeit.** Lernziele, Schwierigkeitsgrad und gezielte Widersprüche
  müssen *gestaltbar* sein, nicht zufällig entstehen.
- **A5 — Aktualisierbarkeit.** Neue iOS-/Android-/Windows-Versionen müssen mit überschaubarem
  Aufwand abbildbar sein.
- **A6 — Nachweisbare Realitätsnähe.** Authentizität ist durch reale Tools zu *belegen*.
- **A7 — Unbedenklichkeit.** Keine realen Personendaten, keine reproduzierbaren Tatanleitungen,
  bei sensiblen Delikten keine inkriminierenden Inhalte.

Die zentrale technische Herausforderung ist nicht die einzelne Datenbank, sondern die
**Konsistenz über Formate und Geräte hinweg** bei gleichzeitig **prüfbarer** Schematreue.

---

## 4. Methodik: Eine Wahrheit, viele Projektionen

### 4.1 Single Source of Truth

Den Kern bildet eine maßgebliche Fallbeschreibung, `case_master.yaml`. Sie enthält Personen,
Geräte (mit OS-Versionen), Orte, eine ereignisbasierte Timeline, Kommunikations-Threads,
geplante Widersprüche (*planted inconsistencies*) und den Lösungsschlüssel. **Kein Generator
erfindet eigene Inhalte** — jeder *projiziert* einen Ausschnitt dieser Wahrheit in sein
Zielformat. Daraus folgt unmittelbar Anforderung A2: Weil alle Spuren aus derselben Quelle
stammen, sind sie zwangsläufig konsistent; und A3, weil die Projektion deterministisch ist.

### 4.2 Deterministische, schema-getreue Generatoren

Rund 33 Generatoren erzeugen die Artefakte in ihren Originalformaten:

- **SQLite** mit realen Schemata (z. B. iOS `sms.db` mit `message/handle/chat/*_join`;
  Android-WhatsApp im normalisierten `message/jid/chat`-Modell, nicht im veralteten
  `key_remote_jid`-Schema; `Photos.sqlite` im Mehrtabellenmodell).
- **plist** (binär/XML), **Registry-Hives** im `regf`-Binärformat (eigener Hive-Writer),
  **EVTX** als template-basiertes BinXML, **BIOME/SEGB v2** (Protobuf-Segmente, die ab iOS 17
  `knowledgeC.db` ablösen), **LNK**-Shell-Links und **$I**-Papierkorb-Records.
- **Zeitformat-Diversität** über alle relevanten Epochen — Apple-CFAbsolute (Nanosekunden),
  Unix-Millisekunden, WebKit/Chrome-Mikrosekunden, FILETIME — als didaktisch besonders
  wertvolles Übungsfeld.

Ein gemeinsames Lade-Modul (`case_master_io.py`) stellt den Generatoren strukturierte
Zugriffe auf die Wahrheit bereit. Wo eine Inhaltsstruktur im Master fehlt, greift ein
**dokumentierter Referenz-Fallback**, sodass der etablierte Referenzfall stabil bleibt,
während ein neuer Spec die Inhalte tatsächlich bestimmt.

### 4.3 Validierung als Abnahme-Gate

Realitätsnähe (A6) wird durch **Gegenprüfung** belegt: Über die erzeugten Artefakte laufen die
charakteristischen Abfragen der realen Parser — iLEAPP (iOS), ALEAPP (Android),
regipy/RegRipper (Registry), python-evtx (Event-Logs), LnkParse3 (LNK), ein BIOME-Parser
(SEGB). Laufen diese fehlerfrei durch und liefern plausible Zeilen, ist die Schematreue
nachgewiesen. Diese Gates sind reproduzierbar und Teil der Pipeline.

---

## 5. Die Agentenschicht: Konzeption durch Sprachmodelle

### 5.1 Arbeitsteilung — und warum sie entscheidend ist

Der konzeptionelle Kern des Ansatzes ist eine **scharfe Arbeitsteilung**:

> Das Sprachmodell entwirft den **Fall**. Die Generatoren erzeugen die **Daten**.

Ein LLM ist hervorragend darin, aus „Stalking, zwei Smartphones, Lernziel Standortverlauf"
einen kohärenten, glaubwürdigen Plot mit Personen, Motiven, Zeitachse und subtilen
Widersprüchen zu entwerfen. Es ist jedoch ungeeignet, Byte-genaue Registry-Hives oder
WAL-Fragmente zu schreiben. Folglich erzeugt der Agent **ausschließlich ein schema-konformes
Spezifikat** (Case-Spec, JSON) — also die *Wahrheit*, nicht die *Artefakte*. Eine wichtige
Konsequenz: **Die Datenqualität hängt nicht am Modell.** Selbst ein mittelgroßes lokales
Modell liefert verwertbare Spezifikate, weil die nachgelagerte Erzeugung deterministisch ist.

### 5.2 Die Pipeline: PROPOSE → REVIEW → BUILD → VALIDATE

1. **PROPOSE.** Aus der Nutzereingabe baut das Framework einen Prompt, der den
   System-Prompt des „Fall-Designers", die verfügbaren OS-Profile, den Generator-Katalog
   (Registry), die Liste der Forensiktools und das JSON-Schema des Case-Spec bündelt. Der Agent
   antwortet mit einem Spec-Vorschlag samt **Artefaktübersicht je Gerät/Plattform/OS**.
2. **REVIEW.** Der Mensch verifiziert und justiert den Spec — Personen, Timeline, Nachrichten,
   Standortspuren, Widersprüche, Lösungsschlüssel. Dieser Schritt ist **verpflichtend**.
3. **BUILD.** Ein Adapter projiziert den Spec auf `case_master.yaml`; die Registry wählt anhand
   der Plattformen und gewünschten `artifact_classes` die passenden Generatoren; die Artefakte
   entstehen deterministisch, ergänzt um einen Fall-Katalog.
4. **VALIDATE.** Die Forensik-Gates prüfen die Artefakte (siehe 5.4).

### 5.3 Backends und Modellwahl

Zwei Betriebsarten decken unterschiedliche Sicherheitsanforderungen ab:

- **Claude Cowork** (empfohlen für höchste Vorschlagsqualität) — beste Reasoning- und
  Konsistenzleistung, deutschsprachig, ideal für komplexe Mehrgeräte-Plots und das gezielte
  Design von Widersprüchen.
- **Lokal/offline (ollama)** — wenn Daten das Haus nicht verlassen dürfen. Empfehlung als
  Default `qwen2.5:32b-instruct` (sehr gutes Deutsch, zuverlässiges Schema-JSON), darunter
  `qwen2.5:14b` (24-GB-Karte) bzw. `qwen2.5:7b`/`llama3.1:8b` (Laptop), nach oben
  `llama3.3:70b` (max. lokale Qualität). Für strikt valides JSON empfiehlt sich ein
  JSON-Schema-Constraint bzw. `format=json`.

Da das Modell nur konzipiert, ist die pragmatische Empfehlung: **Cowork für den Entwurf**, ein
lokales Modell für schnelles Iterieren.

### 5.4 Zweistufige Validierung: Format vs. Lösung

Eine Neuerung gegenüber klassischen, fest auf *einen* Fall verdrahteten Abnahmetests ist die
**Modus-Trennung** der Gates. Jeder Prüf­punkt ist klassifiziert als

- **Format-Check** — Schema, Joins, Parsebarkeit, Zeitstempel-Dekodierung; gilt für **jeden**
  Fall — oder
- **Referenz-Lösungs-Check** — fall­spezifischer Inhalt (bestimmte Texte, Werte, Koordinaten).

Der Modus wird automatisch gewählt: ein spec-abgeleiteter Fall wird im `format`-Modus geprüft
(läuft die Datenbasis sauber durch die realen Parser?), der kanonische Referenzfall zusätzlich
im Lösungs-Modus (ist das Szenario lösbar und konsistent?). Erst diese Trennung macht **frei
spezifizierte Fälle eigenständig validierbar**, ohne die strenge Selbstprüfung des
Referenzfalls aufzugeben.

### 5.5 Ethik-Leitplanken im System-Prompt

Anforderung A7 ist nicht optional, sondern **im System-Prompt des Fall-Designers fest
verankert** und damit Teil jeder Generierung: ausschließlich synthetische Daten; keine realen
Personen, Adressen, Rufnummern, Konten; keine reproduzierbaren Tat-, Bau- oder
Beschaffungsanleitungen und kein Schadcode; bei sensiblen Delikten (z. B.
Missbrauchsdarstellungen) **niemals** inkriminierende Medieninhalte, sondern ausschließlich
Artefakt-**Strukturen**/Metadaten und neutrale, didaktische Platzhalter. Jeder Fall trägt
unveränderbar das Kennzeichen `synthetic_training_data_only`.

---

## 6. Implementierung: CaseForge-Architektur

Die Framework-Schicht besteht aus wenigen, klar getrennten Komponenten:

| Komponente | Rolle |
|---|---|
| `registry.py` | Metadaten-Verzeichnis aller Generatoren (Plattform, OS-Minimum, Artefaktklasse, Pfade, Format, **Gegenprüf-Tool**); steuert Auswahl und Katalog. |
| `profiles/*.yaml` | OS-Profile (z. B. `ios_17` → BIOME statt `knowledgeC`); neue OS-Version = neues Profil. |
| `schema/case_spec.schema.json` | JSON-Schema des Case-Spec (Eingabe-/Vorschlagsformat). |
| `prompts/case_proposal_system.md` | System-Prompt des Fall-Designers inklusive Ethik-Regeln. |
| `llm.py` | Prompt-Konstruktion und Backends (Cowork, ollama). |
| `spec_to_master.py` | Adapter Spec → `case_master.yaml` (Projektion der verifizierten Wahrheit). |
| `catalog.py` | Artefaktübersicht je Gerät/Plattform/OS (MD/CSV). |
| `gate_common.py` | Format-/Referenz-Modus der Validierungs-Gates. |
| `forge.py` | CLI-Orchestrator: `propose · build · validate · run · catalog`. |

Die eigentlichen Generatoren bleiben getrennt von der Framework-Schicht und werden über die
Registry angesteuert — ein Entwurf, der die Erweiterung um neue Artefakttypen oder OS-Versionen
auf das Hinzufügen *einer* Registry-Zeile und ggf. *eines* Profils reduziert (A5).

---

## 7. Fallstudie: Operation Waldweg

Der Referenzfall ist ein fiktives Tötungsdelikt (AZ 2026-KK-00892) im ländlichen Raum bei
Stuttgart, Fokusfenster 24.–25. Januar 2026. Beteiligt sind das iPhone (iOS 17) des Opfers, das
Samsung (Android 14) und ein Windows-11-Triage-Abbild eines Beschuldigten sowie Cloud-,
Wearable- und Multimedia-Spuren.

Der Fall ist bewusst **nicht trivial lösbar**: Er enthält fünf geplante Widersprüche — etwa
einen **Quellkonflikt** zwischen einer veralteten WiFi-Assoziation („Home", gecacht) und einer
zeitgleichen, ungenaueren Mobilfunk-Ortung in Tatortnähe; eine **gelöschte Nachricht**, die nur
noch als WAL-Fragment rekonstruierbar ist; sowie eine **Synchronisationslücke** zwischen
Cloud-Standortverlauf und Geräte-Cache. Solche Konstellationen trainieren die Kernkompetenz
„kein Artefakt ist Ground Truth" und zwingen Lernende zur **Mehrquellen-Korrelation** statt zur
Einzelartefakt-Lektüre.

Begleitend liegen eine glaubwürdige Fallakte (Vermisstenanzeige, Vernehmung, Obduktion), eine
konsolidierte Master-Timeline, ein Lösungsschlüssel mit *red herrings* und entscheidenden
Korrelationen sowie realistischer **Noise** in Größenordnungen vor, die echt wirken (mehrere
Tausend Nachrichten und Aktivitätsereignisse, fremdsprachige Alltagskontakte).

---

## 8. Validierung und Ergebnisse

Der Referenzfall durchläuft die Pipeline reproduzierbar grün: Die Format-Gates aller drei
Geräteklassen bestehen, und die lösungsbezogene Selbstprüfung bestätigt die Konsistenz und
Lösbarkeit des Szenarios. Entscheidend für die Tragfähigkeit des **Frameworks** ist jedoch der
zweite Nachweis: Ein **frei spezifizierter Fall** (anderes Delikt, andere Personen, eigene
Nachrichten- und Standortinhalte) wird aus einem Spec gebaut und besteht **eigenständig** die
Format-Validierung — die fallspezifischen Lösungs-Checks des Referenzfalls werden dabei korrekt
übersprungen. Damit ist belegt, dass nicht nur ein einzelner Datensatz „echt aussieht", sondern
dass die **Methode** beliebige, schema-getreue Fälle erzeugt.

Die Stärke des Ansatzes liegt im Zusammenspiel: Determinismus sichert Reproduzierbarkeit (A3),
die Single-Source-Projektion sichert Konsistenz (A2), die realen Parser belegen Schematreue
(A1, A6), und die Agentenschicht liefert die didaktische Steuerbarkeit (A4) bei minimalem
Aufwand für neue OS-Versionen (A5).

---

## 9. Didaktischer Einsatz in Vortrag und Workshop

Für die Lehre ergeben sich mehrere unmittelbar nutzbare Szenarien:

- **Vollfall-Übung.** Lernende erhalten die drei Geräte-Extrakte und rekonstruieren über die
  Tool-Kette Hypothese und Timeline — inklusive der eingebauten Widersprüche.
- **Fokussierte Teilfälle.** Durch Einschränkung der `artifact_classes` im Spec entstehen
  schlanke Mini-Fälle für ein einzelnes Lernziel (nur ShellBags, nur BIOME, nur
  EVTX-Anmeldungen) — ideal für kurze Übungsblöcke.
- **Live-Demonstration des Agentenworkflows.** Im Workshop lässt sich PROPOSE → REVIEW →
  BUILD → VALIDATE in wenigen Minuten vorführen; der REVIEW-Schritt macht die Rolle der
  menschlichen Fachaufsicht und die Ethik-Leitplanken greifbar.
- **Variantenbildung.** Aus einer Eingabe lassen sich mehrere Schwierigkeitsgrade ableiten,
  etwa durch zusätzliche Noise-Schichten oder subtilere Widersprüche.

Der Agenten-Vortrag kann den Ansatz als Musterbeispiel einer **verantwortungsvollen
Arbeitsteilung zwischen Mensch und KI** nutzen: kreative Konzeption durch das Modell,
deterministische Ausführung durch geprüften Code, verbindliche fachliche und ethische Kontrolle
durch den Menschen.

---

## 10. Limitationen

Der Ansatz erzeugt **logische Extrakte**, keine bit-getreuen physischen Vollabbilder; Secure
Enclave, Keystore, AFU/BFU-Zustände und Roh-NAND-Verschlüsselung sind synthetisch nicht 1:1
reproduzierbar — eine bewusste, dokumentierte Grenze. Einzelne Formatfamilien (SRUM/ESE,
`$MFT`/`$UsnJrnl`, valides Prefetch-SCCA, ShimCache) sind als Folgearbeit ausgewiesen.
App-Schemata driften pro Version; die Kopplung von App- an OS-Version muss gepflegt werden.
Ein Teil der Inhalts­generatoren (Gruppen-Chats, Dokumente, Browser-Verlauf, App-Sandbox-Skelette)
ist derzeit bewusst fallback-getrieben und noch nicht voll spec-parametrisiert. Schließlich
bleibt die generative Konzeption auf den menschlichen REVIEW angewiesen — der Agent **schlägt
vor**, er entscheidet nicht.

---

## 11. Fazit und Ausblick

Synthetische Forensik-Trainingsfälle gewinnen ihren Wert nicht durch die Menge erzeugter Daten,
sondern durch **Konsistenz, Schematreue und Prüfbarkeit**. Die hier vorgestellte Architektur
erreicht dies, indem sie eine einzige Wahrheitsquelle deterministisch in Originalformate
projiziert, die Realitätsnähe mit realen Forensiktools belegt und die kreative Fall-Konzeption
einem Sprachmodell-Agenten überlässt — bei strikter Trennung von Konzeption und Datenerzeugung,
verbindlichem Mensch-in-the-loop und fest verankerten Ethik-Leitplanken. „Operation Waldweg"
zeigt, dass ein vollständiger, geräteübergreifender und widerspruchsreicher Fall auf diese Weise
reproduzierbar entsteht; CaseForge zeigt, dass sich daraus **beliebige** neue Fälle ableiten
lassen.

Künftige Arbeiten betreffen die vollständige Spec-Parametrisierung aller Inhalts­generatoren,
zusätzliche OS-Profile (iOS 18, Android 15, Windows 10), die Ausweitung der Formatabdeckung
(ESE/SRUM, $MFT) sowie die automatische Erzeugung von Aufgabenstellung und Lösungsschlüssel je
Fall. Mittelfristig erscheint ein Bibliotheks-Ansatz reizvoll, bei dem Lehrende kuratierte
Spec-Vorlagen teilen und so ein wachsendes, prüfbares Repertoire an Übungsfällen entsteht — ohne
ein einziges reales Asservat zu berühren.

---

## Literatur (Auswahl)

- Visti, H. u. a.: *ForGe — Computer Forensic Test Image Generator.*
- Scanlon, M. u. a.: *EviPlant / EviGen — Evidence Package Generation for Digital Forensics
  Education.*
- Du, X.; Scanlon, M. u. a.: *TraceGen — Synthetic Smartphone Trace Generation* (DFRWS / Forensic
  Science International: Digital Investigation).
- Göbel, T. u. a.: *hystck / forensig2 — VM-based Generation of Realistic Forensic Disk and
  Network Artefacts.*
- National Institute of Standards and Technology: *Computer Forensic Reference Data Sets
  (CFReDS).*
- Garfinkel, S. u. a.: *Digital Corpora / M57-Patents 

---

> **Hinweis zur Verwendung.** Dieses Paper begleitet das Projekt „Operation Waldweg / CaseForge"
> und darf für Vortrag, Workshop und Lehre mit Namensnennung frei verwendet werden.
> Marc Brandt · Hochschule für Polizei Baden-Württemberg · 2026.
