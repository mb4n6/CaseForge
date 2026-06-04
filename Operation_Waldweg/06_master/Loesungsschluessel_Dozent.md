# Operation Waldweg — Lösungsschlüssel (NUR für Dozierende)

> **Synthetisches Lehrmaterial.** Rein fiktiv, nur lose an einen realen Fall *angelehnt*. Keine echten Personendaten, keine reproduzierbaren Tatanleitungen. Diese Datei enthält die Auflösung und gehört **nicht** in das an Studierende ausgegebene Material.

Stand: 29.05.2026 · Generator-Seed `20260125` · Alle Artefakte deterministisch aus `09_build/case_master.yaml` projiziert.

---

## 1. Primäre Hypothese

**Täter: Daniel Reuter (Ehemann des Opfers).**

Anna Reuter wird am 25.01.2026 zwischen ca. 07:45 und 08:15 getötet; Fundort ist der Parkplatz/Waldweg (nicht zwingend Primärtatort). Motivlage doppelt: (a) **drohende Trennung** — Anna hatte sich entschieden, Daniel zu verlassen (Affäre mit Jonas Brehm), und (b) **finanzieller Druck** — offene Schulden bei Tobias Klenk mit Ultimatum „bis Montag". Gelegenheit: Alibi-Lücke 07:30–08:30, Gerätestandort nahe Waldweg, Anruf an Tobias direkt nach dem Tatzeitfenster.

## 2. Beweiskette (geräteübergreifend)

| # | Indiz | Gerät / Artefakt | Zeit (CET) |
|---|-------|------------------|-----------|
| 1 | Anna kündigt Trennung an, vereinbart Treffen | iPhone · `sms.db`/iMessage (Anna↔Jonas) | 24.01 21:48 ff. |
| 2 | Schulden-Ultimatum „bis Montag, kein Spiel mehr" | Samsung · WhatsApp (Daniel↔Tobias) | 24.01 20:05 |
| 3 | Daniel weiß vom frühen Aufbruch: „Wo willst du so früh hin?" — **auf beiden Geräten** | iPhone `sms.db` (empfangen) **+** Samsung WhatsApp (gesendet) | 25.01 07:25 |
| 4 | Annas belastende Suchen „anwalt trennung sorgerecht", Bahnverbindung | iPhone · BIOME `_DKEvent.Safari.History` | 25.01 07:05–07:09 |
| 5 | Herzfrequenz steigt 64→**138 bpm**, dann **Messende 07:50** | iPhone · `healthdb_secure` | 25.01 06:50–07:50 |
| 6 | Daniel ruft Tobias an, **41 s**, direkt nach Tatfenster | Samsung · `calllog.db` | 25.01 08:25 |
| 7 | Kontrollverhalten: „handy orten partner" | Samsung · Chrome History | 23.01 23:50 |
| 8 | Notebook bestätigt Motiv: „lebensversicherung auszahlung todesfall", Kreditvergleich | Windows · Edge History | 24.01 22:20 |
| 9 | Vermisstenmeldung erst 12:18 | Samsung · `calllog.db` (→110) | 25.01 12:18 |
| 10 | Annas Standortspur Home→Waldweg, letzte Ortung 07:52 | iPhone · `cache_encryptedB.db` (`CellLocation`) | 25.01 07:33–07:52 |
| 11 | Offene Werkstattrechnung 1.480 € (Klenk) + Kreditvergleich-Notiz | Samsung · Downloads/`Rechnung_Werkstatt_Klenk_7711.pdf`, `Privatkredit_Vergleich.docx` | — |
| 12 | Risikolebensversicherung (Begünstigte: Ehepartner) | Notebook · `Versicherungen_Uebersicht.docx`, Kontoauszug 300 € an Klenk | — |
| 13 | Anwalts-Infoblatt + 2-Zimmer-Wohnungsexposé (Auszugsplanung) | iPhone · `Infoblatt_Familienrecht_Trennung.pdf`, `Wohnung_Expose_2Zimmer.docx` | — |
| 14 | Anruf Anna→Jonas (38 s) kurz vor Aufbruch, dann **verpasster Anruf von Daniel** | iPhone · `CallHistory.storedata` | 25.01 07:18 / 07:26 |
| 15 | Health-**Workout mit GPS-Route Home→Waldweg** (endet im Fundortbereich) | iPhone · `healthdb` (`workout_routes`) | 25.01 07:33–07:50 |
| 16 | **Google-Maps-Ziel „Waldweg Parkplatz"** auf Daniels Gerät — er kannte/navigierte den Ort | Samsung · `gmm_myplaces.db` | 25.01 07:31 |
| 17 | Samsung Health: am 25.01 nur 2110 Schritte, **Exercise 08:00–08:30** (Bewegung im Tatfenster) | Samsung · `SecureHealthData.db` | 25.01 08:00–08:30 |

**Entscheidende Korrelationen:** Annas Health-Messende (07:50) deckt sich mit dem Obduktionsfenster (07:45–08:15); Daniels Anruf an Tobias (08:25) liegt unmittelbar danach; die Chrome-/Edge-Suchen liefern beide Motivstränge. Erst die **Zusammenschau über drei Geräte** trägt die Hypothese — kein Einzelartefakt allein.

## 3. Red Herrings (lösen sich entlastend auf)

- **Jonas Brehm (Affäre).** Wirkt verdächtig, war aber am Treffpunkt und wartete vergeblich: „Wo bleibst du? Hier ist niemand." (09:10) und besorgte Nachfrage (09:34). → Anna kam dort **nie** an; Jonas scheidet aus.
- **Tobias Klenk (Schulden, dunkler Kombi).** Liefert Fahrzeug- und Geldmotiv, war aber Anrufer (24.01) und im Werkstatt-Kontext. Das Zeugen-Fahrzeug („dunkler Kombi") ist ein bewusster Ablenker.

## 4. Geplante Widersprüche (didaktische Stolpersteine)

| PI | Inhalt | Lernziel |
|----|--------|----------|
| 1 | Daniel-Telefon: 07:38 WLAN „Home" (alt/gecacht) vs. 08:02 Cell-Standort Waldweg | Quellqualität gewichten (WiFi-Assoziation ≠ Aufenthalt) |
| 2 | Zeuge Harald: „kurz nach acht" (unsicher) vs. präzise Geräte-Timestamps | Zeugenaussage nicht überbewerten |
| 3 | HR-Peak 138 mehrdeutig: Sport **oder** Stress/Gewalt | nur mit Location + BIOME auflösbar |
| 4 | Annas gelöschte iMessage „Wenn er das mitkriegt, dreht er durch" (24.01 22:11) | **nur als WAL-Fragment** rekonstruierbar, nicht in der Tabelle |
| 5 | Cloud-/Sync-Lücke im kritischen Fenster (iCloud bis 07:09, Google erst ab 09:05) | Fehlen ≠ „war nicht dort" — Daniels Telefon-Cell zeigt 08:02 Waldweg **trotz** Cloud-Lücke |

Alle fünf geplanten Widersprüche (PI#1–#5) sind als **echte, tool-lesbare Daten** umgesetzt (nicht nur dokumentiert).

## 5. Automatisierte Abnahme

Zwei Skripte belegen Lösbarkeit und Konsistenz reproduzierbar:

- `09_build/generators/correlate.py` → vereinheitlichte `06_master/Master_Timeline.csv` (**108 Ereignisse**, geräteübergreifend, mit Quellen-Attribution: iMessage, WhatsApp (iOS+Android), Calllog, Chrome/Edge, Health, BIOME-Streams, locationd-Zell-/WLAN-Spuren, Cloud-Exporte).
- `09_build/generators/verify_solution.py` → prüft Beweiskette, Red Herrings und geplante Widersprüche programmatisch. **Aktueller Stand: 12/12 PASS** (inkl. PI#1 und PI#5, beide datenseitig materialisiert).
- `09_build/generators/run_all.py` → Gesamtlauf: erzeugt BIOME + Cloud, fährt alle Format-Gates und die Lösbarkeitsprüfung → **„ALLE GATES BESTANDEN ✓"**.

### Datenumfang (Stand 29.05.2026)
- **BIOME** (4 Streams): `_DKEvent.Safari.History`, `App.InFocus`, `Device.BootSession` (letzte Aktivität 07:52), `Device.ScreenLocked` (22:30).
- **iOS locationd** `cache_encryptedB.db` (`CellLocation`/`WifiLocation`): Annas Bewegung Home→Waldweg 07:33–07:52.
- **Android** `location_cache.db`: **PI#1** — WLAN „Home" 07:38 (stale) vs. Cell-Standort Waldweg 08:02 (±1400 m).
- **Cloud** `04_cloud_exports/` (Google Takeout + iCloud): **PI#5** — Sync-Lücke im kritischen Fenster.
- **WhatsApp in zwei Schemata**: iOS `ChatStorage.sqlite` (gym_crew-Gruppe) + Android `msgstore.db` (1:1 + 2 Gruppen).
- **Dokumente** (`06_master/Dokumente_Manifest.csv`): 17 Downloads/Dokumente je Gerät — 9 noise, 8 dezent fallrelevant (Werkstattrechnung/Kredit, Anwalt/Wohnung, Risiko-LV).
- **07_multimedia** (Bild-/Audio-/Video-Forensik, an Fall angepasst) und **08_multilingual** (DE/EN/TR/RU, Relevanz zu begründen).
- Reichlich Alltags-Noise in iMessage, Chrome, Fotos (12 Assets, GPS/EXIF).

Format-/Parser-Abnahme der Einzelartefakte: `validate_ios.py` (inkl. iOS-WhatsApp), `validate_android.py`, `validate_windows.py` (mit **regipy**, echtem Registry-Parser), `gen_biome.py` (gegen Original-`biome_core.py`) und `gen_cloud.py`.
