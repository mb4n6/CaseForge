# Operation Waldweg — Fallakte & Arbeitsauftrag

**Modul:** IT-Forensik · Hochschule für Polizei Baden-Württemberg
**Bearbeitungsform:** Einzeln oder Kleingruppe · **Werkzeuge:** iLEAPP, ALEAPP, regipy, SQLite-Viewer, Hex-Editor

> **Hinweis:** Sämtliche Daten in diesem Szenario sind **synthetisch** und ausschließlich zu Übungszwecken erzeugt. Personen, Nummern, Orte und Inhalte sind frei erfunden und nur lose an einen realen Fall angelehnt.

---

## 1. Sachverhalt

Am **25.01.2026** wird **Anna Reuter** (38) am Morgen tot an einem Waldweg-Parkplatz im Großraum Stuttgart aufgefunden. Die Rechtsmedizin datiert den Todeszeitpunkt auf **07:45–08:15 Uhr**. Ihr Ehemann **Daniel Reuter** (41) meldet sie am selben Tag um 12:18 Uhr als vermisst.

Im Umfeld stehen mehrere Personen:

- **Daniel Reuter** — Ehemann, Außendienst Medizintechnik.
- **Jonas Brehm** (35) — Architekt, Kontakt zu Anna.
- **Tobias Klenk** (44) — Inhaber einer Kfz-Werkstatt, Geschäftskontakt Daniels; fährt einen dunklen Kombi.
- **Lena Vogt** — beste Freundin des Opfers.
- **Harald K.** — Zeuge: will „kurz nach acht" eine Frau und ein dunkles Fahrzeug am Waldweg gesehen haben (Uhrzeit unsicher).

## 2. Asservate (Datenträger-Images)

| Asservat | Gerät | Eigentümer | OS | Extraktion |
|----------|-------|-----------|-----|-----------|
| A1 | iPhone 14 | Anna Reuter | iOS 17.5.1 | Full File System | `01_ios_full_fs/` |
| A2 | Samsung Galaxy S23 | Daniel Reuter | Android 14 (One UI 6.1) | Full File System | `02_android_full_fs/` |
| A3 | Notebook (privat) | Daniel Reuter | Windows 11 23H2 | Logische Triage | `03_windows_triage/` |

Notebook (A3) enthält u. a. Registry-Hives `NTUSER.DAT`, `SAM`, `SYSTEM`, `SOFTWARE` (`…/config/`) und `Amcache.hve` — mit RegRipper auswertbar: Benutzerkonten, Rechnername, Zeitzone, letzter Shutdown, **USB-Geräte (USBSTOR/MountedDevices), WLAN-Profile (NetworkList), Ausführungsspuren (BAM/UserAssist/Amcache), zuletzt genutzte Items (RecentDocs/RunMRU)**. Dazu Datei-Artefakte: Papierkorb (`$Recycle.Bin`), `setupapi.dev.log`, geplante Tasks, `Zone.Identifier`, Prefetch.

Hinweis A1: Auf dem iPhone (iOS 17) existiert **keine** `knowledgeC.db` mehr — Aktivitäts-, Safari- und Mikro-Standortspuren liegen in **BIOME-Streams** (`/private/var/db/biome/streams/…`, SEGB-Format). Nutzt hierfür den BIOME-Stream-Analyzer.

Auf den Asservaten findet ihr u. a.: Nachrichten (iMessage `sms.db`, WhatsApp in **zwei** Schemata — iOS-`ChatStorage.sqlite` und Android-`msgstore.db` inkl. Gruppen), Anruflisten, Kontakte, Browserverläufe (Safari via BIOME, Chrome, Edge), Health-Daten, **Standort-Datenbanken** (iOS `cache_encryptedB.db`, Android `location_cache.db`), heruntergeladene **Dokumente** (PDF/DOCX/XLSX/CSV/TXT in Downloads/Dokumente) sowie Foto-/EXIF-Daten.

**Ergänzende Asservate:**

| Asservat | Inhalt | Verzeichnis |
|----------|--------|-------------|
| A4 | Cloud-Exporte (Google-Standortverlauf, iCloud-Sync) | `04_cloud_exports/` |
| A5 | Multimedia (Bild-/Audio-/Video-Forensik) | `07_multimedia/` |
| A6 | Mehrsprachige Inhalte (DE/EN/TR/RU) | `08_multilingual/` |
| A7 | Ermittlungsakten (Obduktion, Zeuge, Vermisstenanzeige) | `05_police_records/` |

## 3. Arbeitsauftrag

Erstellt einen **forensischen Kurzbericht**, der folgende Punkte beantwortet. Belegt jede Aussage mit dem konkreten Artefakt (Pfad, Tabelle/Stream, Zeitstempel-Format).

1. **Rekonstruiert die Zeitleiste** des 25.01.2026 zwischen 07:00 und 12:30 — geräteübergreifend. Achtet auf die korrekte Umrechnung der unterschiedlichen Zeitstempel-Formate (Apple-Nanosekunden, Apple-CFAbsoluteTime, Unix-Millisekunden, WebKit-Mikrosekunden).
2. **Kommunikation:** Welche Nachrichten und Anrufe sind im Tatzeitumfeld relevant? Gibt es **gelöschte** Inhalte, und wie lassen sie sich (teilweise) wiederherstellen?
3. **Bewegungs-/Aktivitätsbild:** Was sagen Health-Daten, BIOME-Streams und Standortspuren über den Morgen aus? Wie verlässlich sind die einzelnen Quellen?
4. **Motiv & Gelegenheit:** Welche Hinweise auf Motive finden sich auf den Geräten? Wer hatte Gelegenheit?
5. **Bewertung der Verdächtigen:** Begründet, wen die Spurenlage be- bzw. entlastet. Benennt mindestens **zwei Quellenkonflikte** und wie ihr sie auflöst.
6. **Multimedia & Sprachen:** Wertet Bild-/Audio-/Videospuren (A5) aus — Authentizität (Original vs. manipuliert), Transkription, Frame-Abgleich mit der Zeitleiste. Erkennt und übersetzt die fremdsprachigen Inhalte (A6) und begründet deren Relevanz (das meiste ist Noise).
7. **Methodik:** Dokumentiert eure Werkzeuge, Hashes der Artefakte und die Nachvollziehbarkeit (Chain of Custody-Logik).

## 4. Leitfragen (zur Orientierung)

- Welche Quelle ist höherwertig, wenn WLAN-Assoziation und Mobilfunk-Standort widersprechen?
- Ein einzelner Herzfrequenz-Peak — was kann er bedeuten, und was braucht ihr, um ihn zu deuten?
- Wie geht ihr mit einer **fehlenden** Spur im kritischen Zeitfenster um (Cloud-Sync-Lücke)? Ist „keine Spur" ein Beweis?
- Wie zuverlässig ist eine Zeugenaussage gegenüber präzisen Geräte-Zeitstempeln?

## 5. Abgabe

Forensischer Bericht (PDF), Roh-Exporte eurer Tools (iLEAPP/ALEAPP-HTML, Query-Ergebnisse) sowie eine tabellarische Master-Zeitleiste. Bewertung gemäß ausgehängtem Raster.
