# 04_cloud_exports — Cloud-Asservate (Operation Waldweg)

> Synthetisch, fallkonform zu `case_master` v3.0. Erzeugt von `09_build/generators/gen_cloud.py`. Materialisiert **planted_inconsistency #5** (unvollständige Cloud-Timeline).

## Inhalte
- `google/location-history.json` — Google-Takeout-Standortverlauf (Daniel, Android). Format: `timelineObjects` mit `placeVisit`/`activitySegment`, Koordinaten als `latitudeE7`/`longitudeE7`, Zeiten in UTC (Z).
- `icloud/icloud_sync.csv` — iCloud-Sync-Protokoll (Anna, iPhone).

## PI#5 — die Sync-Lücke (Auflösung für Dozenten)
Beide Quellen haben eine **Lücke im kritischen Fenster** (25.01 ~07:15–09:05 CET):
- iCloud: letzte Syncs Health 06:55 / Kalender 07:09, danach erst 13:40 ein verzögerter Teil-Sync (Annas Gerät war ab 07:52 still → BootSession-Ende).
- Google: Aufenthalt „Zuhause" bis 07:14, dann nichts, Wiederaufnahme erst 09:05 nahe Gewerbegebiet/Werkstatt.

**Lehrziel:** „Keine Cloud-Spur" ist **kein** Beweis „war nicht dort". Daniels Telefon-seitige Cell-Ortung (`02_android_full_fs/.../location_cache.db`) zeigt **08:02 Waldweg** trotz der Cloud-Lücke — die geräteseitige Quelle schlägt die Cloud-Abwesenheit.

## Hinweis zu Koordinaten
Alle Punkte nutzen die Fallkoordinaten aus `case_master` (Home 48.7758/9.1829, Werkstatt 48.7510/9.2100, Waldweg 48.7305/9.2480). Eine ältere, koordinaten-inkonsistente Variante liegt in `_backup_legacy/04_cloud_exports/`.
