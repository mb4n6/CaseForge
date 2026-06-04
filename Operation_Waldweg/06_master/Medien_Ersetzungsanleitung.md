# Operation Waldweg — Anleitung: realistischere Bilder & Audio einsetzen

> Ziel: die Platzhalter-Medien durch realistischere KI-erzeugte Bilder/Audio ersetzen, **ohne** die forensische Konsistenz zu brechen. Synthetisches Lehrmaterial.

## Grundregeln (wichtig für die Konsistenz)

1. **Dateinamen und Pfade exakt beibehalten.** Generiere extern, benenne dann genau wie unten um und überschreibe die vorhandene Datei. Die Metadaten-CSVs, das `case_master.yaml` und die Korrelations-Skripte referenzieren diese Namen.
2. **Metadaten nachstellen.** KI-Bilder/Audio haben falsche oder fehlende EXIF/Erstellzeiten. Setze Aufnahmezeit (und ggf. GPS) passend zum Fall — siehe „Nachbearbeitung" unten. Sonst widersprechen die Datei-Zeitstempel der Zeitleiste.
3. **Format/Container treffen.** Audio als **WAV PCM, mono, 44,1 kHz**; Bilder als **JPG** (bzw. PNG für Screenshots). Für die iPhone-Fotos optional **HEIC** (siehe Abschnitt 4).
4. **Keine echten Personen / keine realen Orte.** Generische Gesichter vermeiden bzw. anonym halten; Orte generisch (BW-Raum, Mischwald). Rein fiktiv.
5. **KI-Wasserzeichen/-Metadaten** (C2PA) nach dem Download entfernen, dann erst die Fall-Metadaten setzen.

Benötigte CLI-Tools für die Nachbearbeitung: `exiftool` (Metadaten), `ffmpeg` (Audio-Konvertierung), optional `sips`/ImageMagick (HEIC).

---

## 1. Bilder — `07_multimedia/images/`

**Generator:** ChatGPT (GPT-4o Image / DALL·E) oder vergleichbar. Seitenverhältnis 4:3 (Fotos) bzw. Screenshot-Auflösung.

### 1.1 `original/forest_path_01.jpg`  — Fundortumgebung (unauffällig)
Prompt:
> „Photorealistic amateur smartphone photo of a quiet forest path / gravel parking area at the edge of a German mixed forest on an overcast winter morning, bare trees, damp ground, soft grey light, no people, slightly tilted handheld framing, natural colors, 4:3."

### 1.2 `original/forest_path_02.jpg` — mit entfernter Silhouette (CRITICAL)
Prompt:
> „Photorealistic amateur smartphone photo of the same German forest path on an overcast winter morning, a small indistinct dark human-like silhouette far in the background near the tree line, slightly out of focus, no recognizable face, dim flat lighting, handheld, 4:3."

### 1.3 `manipulated/forest_path_02_manipulated.jpg` — manipulierte Variante (Bildforensik-Übung)
Entweder `forest_path_02.jpg` in einem Editor sichtbar verändern (Objekt/Person wegstempeln oder hinzufügen, Helligkeit/Beschnitt ändern), **als JPG erneut speichern** (erzeugt andere Quantisierung → ELA-Übung). Oder Prompt:
> „The same forest path photo but with the distant silhouette removed and a small dark estate car (Kombi) faintly added near the parking area; keep lighting consistent."
Hinweis: bewusst leicht erkennbare Inkonsistenz (Schatten/Kanten) einbauen — das ist der Lerneffekt.

### 1.4 `screenshots/maps_route_screenshot.png` — Kartenroute (PNG)
Prompt:
> „Realistic smartphone screenshot of a generic maps navigation app showing a driving route from a residential area to a forest parking spot at the city edge, route line highlighted, ETA ~18 min, fictional street names, German UI, portrait phone aspect."
Alternativ: echten Screenshot einer Karten-App mit generischer Route anfertigen (keine realen Adressen).

---

## 2. Audio — ElevenLabs (Text-to-Speech)

**Allgemeine ElevenLabs-Einstellungen:** Model „Multilingual v2"; Stability ~45 %, Similarity ~80 %, Style 0–20 %; Sprache je Datei wählen. Nach dem Export **als WAV mono 44,1 kHz** konvertieren (siehe Nachbearbeitung) und exakt umbenennen.

> Die Skripte sind synthetisch und entsprechen den Referenz-Transkripten des Falls.

### 2.1 `audio/voicemail/voicemail_anna_office_de.wav` — Stadtwerke-Büro → Anna (DE)
- Stimme: weiblich, ~35–45, sachlich-freundlich, Hochdeutsch. Tempo normal, leicht hallig (Bürotelefon).
- Skript:
> „Hallo Anna, hier ist das Büro. Du bist heute Morgen nicht da und auch nicht erreichbar. Bitte melde dich kurz, sobald du das hörst. Danke."
- Relevanz: belegt, dass Anna am Tatmorgen nie zur Arbeit kam.

### 2.2 `audio/whatsapp_voice/voice_lena_de.wav` — Lena Vogt → Anna (DE)
- Stimme: weiblich, ~35, warm, freundschaftlich-besorgt, etwas spontan.
- Skript:
> „Hey, alles gut bei dir? Du klangst neulich irgendwie gestresst. Melde dich, wenn du reden willst — ich bin für dich da, ja?"
- Relevanz: stützt den emotionalen Belastungskontext (passt zum iMessage-Thread Anna↔Lena).

### 2.3 `audio/ambient/forest_ambient_01.wav` — Umgebungston Waldweg (KEIN TTS)
- ElevenLabs ist hier ungeeignet. Optionen: Sound-FX-Generator (ElevenLabs „Sound Effects": Prompt unten) **oder** lizenzfreies Ambiente (z. B. Freesound) zusammenschneiden.
- ElevenLabs-Sound-Effects-Prompt:
> „Cold windy forest ambience, rustling bare branches, several footsteps on uneven gravel and leaves, a distant car engine passing by, no voices, ~20 seconds."
- Relevanz: konsistent mit dem Zeugenhinweis (dunkles Fahrzeug am Waldweg).

### 2.4 `08_multilingual/audio_foreign/voice_projektpartner_en.wav` — James Carter → Anna (EN)
- Stimme: männlich, ~40, neutrales Business-Englisch.
- Skript:
> „Hi Anna, can you send the updated spreadsheet before noon? We need the final version for the meeting. Thanks."
- Relevanz: Noise (Projektarbeit).

### 2.5 `08_multilingual/audio_foreign/voice_bekannter_tr.wav` — Mehmet Y. → Anna (TR)
- Stimme: männlich, ~40, türkisch.
- Skript:
> „Merhaba, toplantıyı yarına alabilir miyiz? Bu sabah gelmem biraz zor."
- Relevanz: Noise — **Verwechslungsfalle**: nicht mit dem Jonas-Treffen vermengen.

---

## 3. Video (optional, fortgeschritten) — `07_multimedia/video/`

ChatGPT-Images/ElevenLabs decken kein Video ab. Optionen für `critical/critical_walkthrough.mp4` (Waldweg-Sequenz) und `noise/home_clip_noise.mp4` (Innenraum):
- Text-zu-Video (z. B. Sora / Runway / Pika) mit Prompt analog zu 1.1/1.2.
- Oder selbst kurze, generische Clips filmen (kein realer Bezug).
- Danach **Einzelframes neu extrahieren**, damit `frames_critical/` und `frames_home/` zum Video passen:
```bash
ffmpeg -i critical/critical_walkthrough.mp4 -vf fps=1 critical/frames_critical/frame_%03d.jpg
ffmpeg -i noise/home_clip_noise.mp4 -vf fps=1 noise/frames_home/frame_%03d.jpg
```

---

## 4. (Optional) Echte Fotodateien passend zu `Photos.sqlite`

`Photos.sqlite` referenziert Dateinamen, die als Bilddateien bislang **nicht** vorliegen. Für höhere Realität echte Bilder anlegen und in `01_ios_full_fs/private/var/mobile/Media/DCIM/<Ordner>/` ablegen. Zielnamen/Inhalte:

| Datei | DCIM-Ordner | Zeit (CET) | Ort/GPS | Motiv-Prompt (ChatGPT) |
|-------|-------------|-----------|---------|------------------------|
| IMG_2012–2014.HEIC (Burst) | 107APPLE | 2026-01-11 15:05 | Schule 48.7702, 9.1955 | „kids indoor sports training, motion, amateur phone burst" |
| IMG_2041/2042.HEIC | 108APPLE | 2026-01-18 16:30 | Gym 48.7689, 9.1740 | „youth gym training session, candid phone photo" |
| IMG_2055.HEIC | 108APPLE | 2026-01-20 12:42 | Büro 48.7831, 9.1817 | „lunch bowl on office desk, top-down phone photo" |
| IMG_2061.PNG | 108APPLE | 2026-01-22 09:15 | — | „screenshot of a fitness studio weekly class plan, German" |
| IMG_2068.HEIC | 108APPLE | 2026-01-24 18:42 | Supermarkt 48.7770, 9.1880 | „supermarket shelf, evening, casual phone photo" |
| IMG_2033.HEIC | 108APPLE | 2026-01-15 19:48 | Zuhause 48.7758, 9.1829 | „home dinner table, warm light, phone photo" |
| IMG_2063.HEIC | 108APPLE | 2026-01-23 08:31 | Gym 48.7689, 9.1740 | „mirror gym selfie, no recognizable face, morning" |

HEIC-Konvertierung (macOS): `sips -s format heic input.jpg --out IMG_2041.heic`
(Alternativ Dateinamen in `Photos.sqlite` auf `.jpg` ändern — dann entfällt die Konvertierung.)

---

## 5. Nachbearbeitung — Metadaten & Format setzen

**Audio in das richtige Format bringen** (nach ElevenLabs-Export):
```bash
ffmpeg -i export.mp3 -ac 1 -ar 44100 -c:a pcm_s16le voice_lena_de.wav
```

**Bild-Aufnahmezeit (und GPS) setzen** — Beispiel Gym-Foto:
```bash
exiftool -overwrite_original \
  -DateTimeOriginal="2026:01:18 16:30:12" -CreateDate="2026:01:18 16:30:12" \
  -GPSLatitude=48.7689 -GPSLatitudeRef=N -GPSLongitude=9.1740 -GPSLongitudeRef=E \
  IMG_2041.heic
```

**Dateisystem-Zeitstempel** angleichen (damit auch `mtime` passt):
```bash
touch -t 202601181630.12 IMG_2041.heic
```

**KI-/C2PA-Metadaten vorab entfernen:** `exiftool -all= datei.jpg` (danach Fall-Metadaten neu setzen).

---

## 6. Checkliste pro ersetzter Datei
- [ ] extern generiert (Prompt/Skript oben)
- [ ] Format korrekt (WAV mono 44,1 kHz / JPG / PNG / HEIC)
- [ ] exakt umbenannt und am richtigen Pfad überschrieben
- [ ] KI-Metadaten entfernt, Fall-EXIF/Zeit (und GPS) gesetzt
- [ ] Dateisystem-Zeit per `touch` angepasst
- [ ] bei Video: Frames neu extrahiert
- [ ] Gegencheck: `python3 09_build/generators/run_all.py` weiterhin „ALLE GATES BESTANDEN ✓"

> Tipp: Die Metadaten-CSVs (`07_multimedia/*/_metadata.csv`, `08_multilingual/...`) und die Referenz-Transkripte beschreiben Kontext und Relevanz — als Vorlage für Prompt-Feinschliff nutzen.
