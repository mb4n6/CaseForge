#!/usr/bin/env python3
# =====================================================================
# gen_cloud.py  —  Cloud-Exporte (Google Takeout + iCloud), PI#5
# ---------------------------------------------------------------------
# Materialisiert planted_inconsistency #5 (Cloud-Timeline unvollstaendig):
# Beide Cloud-Quellen haben eine SYNC-LUECKE im kritischen Fenster
# (25.01 ~07:15-09:05). Lehrziel: Fehlen einer Cloud-Spur ist KEIN Beweis
# "war nicht dort" (Daniels Telefon-Cell zeigt 08:02 Waldweg trotz Luecke).
#
# Fallkonforme Koordinaten (case_master locations). Google = Daniel
# (Android/Google), iCloud-Sync = Anna (iPhone).
# =====================================================================
import os
import json
import csv
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
CLOUD = os.environ.get('WALDWEG_CLOUD', os.path.join(ROOT, '04_cloud_exports'))

GOOGLE = os.path.join(CLOUD, 'google', 'location-history.json')
ICLOUD = os.path.join(CLOUD, 'icloud', 'icloud_sync.csv')

# Fall-Koordinaten (aus case_master)
HOME = (48.7758, 9.1829)
WORKSHOP = (48.7510, 9.2100)
WALDWEG = (48.7305, 9.2480)


def e7(latlon):
    return {"latitudeE7": int(latlon[0] * 1e7), "longitudeE7": int(latlon[1] * 1e7)}


def seg(start_iso, end_iso, a, b, activity):
    return {"activitySegment": {
        "startLocation": e7(a), "endLocation": e7(b),
        "duration": {"startTimestamp": start_iso, "endTimestamp": end_iso},
        "activityType": activity}}


def visit(start_iso, end_iso, loc, name):
    return {"placeVisit": {
        "location": {**e7(loc), "name": name},
        "duration": {"startTimestamp": start_iso, "endTimestamp": end_iso}}}


def build_google():
    # Zeiten in UTC (Z) wie im echten Takeout-Export. 25.01 CET = UTC+1.
    objs = [
        visit("2026-01-24T17:30:00Z", "2026-01-24T21:30:00Z", HOME, "Zuhause"),
        # 25.01 morgens (CET 06:50-07:14 -> UTC 05:50-06:14)
        visit("2026-01-25T05:50:00Z", "2026-01-25T06:14:00Z", HOME, "Zuhause"),
        # >>> SYNC-LUECKE: CET 07:15-09:05 (UTC 06:14-08:05) FEHLT (PI#5) <<<
        # Wiederaufnahme CET 09:05 (UTC 08:05): nahe Werkstatt
        visit("2026-01-25T08:05:00Z", "2026-01-25T08:40:00Z", WORKSHOP, "Gewerbegebiet"),
        seg("2026-01-25T08:40:00Z", "2026-01-25T09:10:00Z", WORKSHOP, HOME, "IN_VEHICLE"),
        visit("2026-01-25T09:10:00Z", "2026-01-25T11:30:00Z", HOME, "Zuhause"),
    ]
    os.makedirs(os.path.dirname(GOOGLE), exist_ok=True)
    with open(GOOGLE, 'w', encoding='utf-8') as f:
        json.dump({"timelineObjects": objs}, f, indent=2, ensure_ascii=False)
    print(f"google/location-history.json: {len(objs)} Objekte (Luecke 07:15-09:05 CET) "
          f"-> {os.path.relpath(GOOGLE, ROOT)}")


def build_icloud():
    rows = [
        ("2026-01-24T22:11:54+01:00", "notes", "synced"),
        ("2026-01-24T22:14:02+01:00", "photos_metadata", "synced"),
        ("2026-01-25T06:55:00+01:00", "health", "synced"),
        ("2026-01-25T07:09:18+01:00", "calendar", "synced"),
        # >>> danach SYNC-LUECKE: Geraet ab 07:52 still (BootSession-Ende) <<<
        # erst spaeter Server-seitiger Teil-Sync, kritisches Fenster fehlt:
        ("2026-01-25T13:40:00+01:00", "photos_metadata", "partial/delayed"),
    ]
    os.makedirs(os.path.dirname(ICLOUD), exist_ok=True)
    with open(ICLOUD, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "artifact", "status"])
        w.writerows(rows)
    print(f"icloud/icloud_sync.csv: {len(rows)} Eintraege (Luecke nach 07:09) "
          f"-> {os.path.relpath(ICLOUD, ROOT)}")


def main():
    build_google()
    build_icloud()
    # Konsistenz-Hinweis
    print("\nPI#5 materialisiert: Cloud-Luecke im kritischen Fenster (25.01 ~07:15-09:05).")
    print("  -> Daniels Telefon-Cell (location_cache.db) zeigt 08:02 Waldweg TROTZ Cloud-Luecke.")
    print("  -> Lehrziel: 'keine Cloud-Spur' != 'war nicht dort'.")


if __name__ == "__main__":
    main()
