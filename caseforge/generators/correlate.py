#!/usr/bin/env python3
# =====================================================================
# correlate.py  —  Cross-Device-Korrelation (Tag 6)
# ---------------------------------------------------------------------
# Liest ALLE erzeugten Geraete-Artefakte (iOS / Android / Windows + BIOME)
# zurueck — so, wie es ein Ermittler mit den Parser-Ausgaben taete — und
# baut daraus EINE vereinheitlichte, chronologische Master-Timeline mit
# Quellen-Attribution. Anschliessend Konsistenz- und Loesungsschluessel-
# Abgleich. Ausgabe: Master_Timeline.csv + Verifikationsreport (stdout).
# =====================================================================
import os
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_master_io as cmio
import sqlite3
import sys
import csv
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")

IOS = os.environ.get('WALDWEG_IOS_FS', '/tmp/ios_build')
AND = os.environ.get('WALDWEG_AND_FS', '/tmp/and_build')
WIN = os.environ.get('WALDWEG_WIN_FS', '/tmp/win_build')
WUSER = cmio.windows_username()   # Windows-Profilordner aus Fall-Besitzer

TZ = timezone(timedelta(hours=1))  # Europe/Berlin (Winterzeit)
APPLE = 978307200

events = []  # (datetime_utc, device, source, actor, beschreibung)


def add(dt_utc, device, source, actor, desc):
    events.append((dt_utc, device, source, actor, desc))


def local(dt_utc):
    return dt_utc.astimezone(TZ)


# ---------------------------------------------------------------------
# iOS
# ---------------------------------------------------------------------
def load_ios():
    sms = os.path.join(IOS, 'private/var/mobile/Library/SMS/sms.db')
    if os.path.exists(sms):
        # auf Kopie arbeiten (WAL nicht antasten)
        import shutil
        tmp = '/tmp/_corr_sms.db'
        for s in ("", "-wal", "-shm"):
            if os.path.exists(sms + s):
                shutil.copy(sms + s, tmp + s)
        con = sqlite3.connect(tmp)
        for d, frm, contact, text in con.execute("""
            SELECT m.date, m.is_from_me, h.id, m.text FROM message m
            LEFT JOIN handle h ON m.handle_id=h.ROWID ORDER BY m.date"""):
            dt = datetime(2001,1,1,tzinfo=timezone.utc)+timedelta(seconds=d/1e9)
            who = "Anna" if frm else (contact or "?")
            add(dt, "iPhone (Anna)", "sms.db/iMessage", who, f"„{text}“")
        con.close()
    health = os.path.join(IOS, 'private/var/mobile/Library/Health/healthdb_secure.sqlite')
    if os.path.exists(health):
        con = sqlite3.connect(f"file:{health}?mode=ro", uri=True)
        for sd, q in con.execute("""SELECT s.start_date,q.original_quantity
            FROM samples s JOIN quantity_samples q ON s.data_id=q.data_id
            WHERE s.data_type=5 ORDER BY s.start_date"""):
            dt = datetime(2001,1,1,tzinfo=timezone.utc)+timedelta(seconds=sd)
            add(dt, "iPhone (Anna)", "healthdb/HR", "Anna", f"Herzfrequenz {q:.0f} bpm")
        con.close()
    # BIOME-Streams (Safari, App-Fokus, Geraetezustaende)
    breg = os.path.join(IOS, 'private/var/db/biome/streams/restricted')
    bmap = {
        '_DKEvent.Safari.History': ("BIOME/Safari", lambda pb: f"Web: {pb.get('field_1','')}"),
        'App.InFocus':             ("BIOME/AppFocus", lambda pb: f"App im Vordergrund: {pb.get('field_1','')}"),
        'Device.BootSession':      ("BIOME/Device", lambda pb: "Geraet aktiv (BootSession) — letzte Aktivitaet"),
        'Device.ScreenLocked':     ("BIOME/Device", lambda pb: "Bildschirm gesperrt (Nachtruhe)"),
    }
    if os.path.isdir(breg):
        sys.path.insert(0, BUILD)
        try:
            import biome_core
            for stream, (label, fmt) in bmap.items():
                local = os.path.join(breg, stream, 'local')
                if not os.path.isdir(local):
                    continue
                for fn in os.listdir(local):
                    if fn.endswith('.json'):
                        continue
                    an = biome_core.BIOMEAnalyzer(os.path.join(local, fn), max_frames=100)
                    if an.analyze():
                        for fr in an.frames:
                            ts = fr.timestamp
                            if ts:
                                dt = datetime(2001,1,1,tzinfo=timezone.utc)+timedelta(seconds=ts)
                                add(dt, "iPhone (Anna)", label, "Anna", fmt(fr.protobuf_data))
        except Exception as e:
            print("BIOME-Lesefehler:", e)

    # iPhone-WhatsApp (gym_crew Gruppe, Noise)
    wai = os.path.join(IOS, 'private/var/mobile/Library/Mobile Documents/'
                       '57T9237FN3~net~whatsapp~WhatsApp/ChatStorage.sqlite')
    if os.path.exists(wai):
        con = sqlite3.connect(f"file:{wai}?mode=ro&immutable=1", uri=True)
        for md, frm, name, text in con.execute("""
            SELECT m.ZMESSAGEDATE,m.ZISFROMME,gm.ZCONTACTNAME,m.ZTEXT
            FROM ZWAMESSAGE m LEFT JOIN ZWAGROUPMEMBER gm ON m.ZGROUPMEMBER=gm.Z_PK
            ORDER BY m.ZMESSAGEDATE"""):
            dt = datetime(2001,1,1,tzinfo=timezone.utc)+timedelta(seconds=md)
            who = "Anna" if frm else (name or "?")
            add(dt, "iPhone (Anna)", "WhatsApp/gym_crew", who, f"„{text}“")
        con.close()

    # locationd Cell-Spur
    loc = os.path.join(IOS, 'private/var/mobile/Library/Caches/locationd/cache_encryptedB.db')
    if os.path.exists(loc):
        con = sqlite3.connect(f"file:{loc}?mode=ro&immutable=1", uri=True)
        for ts, la, lo in con.execute("SELECT Timestamp,Latitude,Longitude FROM CellLocation ORDER BY Timestamp"):
            dt = datetime(2001,1,1,tzinfo=timezone.utc)+timedelta(seconds=ts)
            add(dt, "iPhone (Anna)", "locationd/Cell", "Anna", f"Standort {la:.4f},{lo:.4f}")
        con.close()


# ---------------------------------------------------------------------
# Android
# ---------------------------------------------------------------------
def load_android():
    calllog = os.path.join(AND, 'data/data/com.samsung.android.providers.contacts/databases/calllog.db')
    if os.path.exists(calllog):
        con = sqlite3.connect(f"file:{calllog}?mode=ro", uri=True)
        typ = {1:"eingehend",2:"ausgehend",3:"verpasst"}
        for date,num,t,dur,name in con.execute("SELECT date,number,type,duration,name FROM calls ORDER BY date"):
            dt = datetime.fromtimestamp(date/1000, timezone.utc)
            add(dt, "Samsung (Daniel)", "calllog.db", "Daniel",
                f"Anruf {typ.get(t,'?')} {name or num} ({dur}s)")
        con.close()
    wa = os.path.join(AND, 'data/data/com.whatsapp/databases/msgstore.db')
    if os.path.exists(wa):
        con = sqlite3.connect(f"file:{wa}?mode=ro", uri=True)
        for ts,frm,raw,text in con.execute("""SELECT m.timestamp,m.from_me,j.raw_string,m.text_data
            FROM message m JOIN chat c ON m.chat_row_id=c._id JOIN jid j ON c.jid_row_id=j._id
            ORDER BY m.timestamp"""):
            dt = datetime.fromtimestamp(ts/1000, timezone.utc)
            who = "Daniel" if frm else raw.split("@")[0]
            add(dt, "Samsung (Daniel)", "WhatsApp", who, f"„{text}“")
        con.close()
    chrome = os.path.join(AND, 'data/data/com.android.chrome/app_chrome/Default/History')
    if os.path.exists(chrome):
        con = sqlite3.connect(f"file:{chrome}?mode=ro", uri=True)
        for t,url in con.execute("SELECT last_visit_time,url FROM urls ORDER BY last_visit_time"):
            dt = datetime(1601,1,1,tzinfo=timezone.utc)+timedelta(microseconds=t)
            add(dt, "Samsung (Daniel)", "Chrome", "Daniel", f"Web: {url}")
        con.close()
    locdb = os.path.join(AND, 'data/data/com.google.android.gms/databases/location_cache.db')
    if os.path.exists(locdb):
        con = sqlite3.connect(f"file:{locdb}?mode=ro&immutable=1", uri=True)
        for ssid,ls,la,lo in con.execute("SELECT ssid,last_seen,latitude,longitude FROM wifi_assoc"):
            dt = datetime.fromtimestamp(ls/1000, timezone.utc)
            add(dt, "Samsung (Daniel)", "WiFi-Assoc", "Daniel", f"WLAN '{ssid}' @ {la:.4f},{lo:.4f} (gecacht)")
        for ts,la,lo,acc,src in con.execute("SELECT timestamp,latitude,longitude,accuracy_m,source FROM network_location_cache"):
            dt = datetime.fromtimestamp(ts/1000, timezone.utc)
            add(dt, "Samsung (Daniel)", f"Loc/{src}", "Daniel", f"Standort {la:.4f},{lo:.4f} (±{acc}m)")
        con.close()


# ---------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------
def load_windows():
    edge = os.path.join(WIN, f'C/Users/{WUSER}/AppData/Local/Microsoft/Edge/User Data/Default/History')
    if os.path.exists(edge):
        con = sqlite3.connect(f"file:{edge}?mode=ro", uri=True)
        for t,url in con.execute("SELECT last_visit_time,url FROM urls ORDER BY last_visit_time"):
            dt = datetime(1601,1,1,tzinfo=timezone.utc)+timedelta(microseconds=t)
            add(dt, "Notebook (Daniel)", "Edge", "Daniel", f"Web: {url}")
        con.close()


def load_cloud():
    import json
    cloud = os.environ.get('WALDWEG_CLOUD', os.path.join(ROOT, '04_cloud_exports'))
    g = os.path.join(cloud, 'google', 'location-history.json')
    if os.path.exists(g):
        data = json.load(open(g, encoding='utf-8'))
        for obj in data.get('timelineObjects', []):
            if 'placeVisit' in obj:
                pv = obj['placeVisit']
                iso = pv['duration']['startTimestamp'].replace('Z', '+00:00')
                dt = datetime.fromisoformat(iso)
                loc = pv['location']
                add(dt, "Cloud (Google/Daniel)", "Takeout/Location",
                    "Daniel", f"Aufenthalt {loc.get('name','?')} "
                    f"({loc['latitudeE7']/1e7:.4f},{loc['longitudeE7']/1e7:.4f})")
            elif 'activitySegment' in obj:
                seg = obj['activitySegment']
                iso = seg['duration']['startTimestamp'].replace('Z', '+00:00')
                dt = datetime.fromisoformat(iso)
                add(dt, "Cloud (Google/Daniel)", "Takeout/Activity",
                    "Daniel", f"Bewegung ({seg.get('activityType','?')})")
    ic = os.path.join(cloud, 'icloud', 'icloud_sync.csv')
    if os.path.exists(ic):
        import csv as _csv
        with open(ic, encoding='utf-8') as f:
            for row in _csv.DictReader(f):
                dt = datetime.fromisoformat(row['timestamp'])
                add(dt, "Cloud (iCloud/Anna)", "iCloud-Sync", "Anna",
                    f"Sync {row['artifact']} [{row['status']}]")


def write_timeline():
    events.sort(key=lambda e: e[0])
    out = os.path.join(ROOT, '06_master', 'Master_Timeline.csv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # in Scratch schreiben, dann kopieren (Mount-WAL-Problematik gilt nicht fuer CSV)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["Zeit (lokal, CET)", "Geraet", "Quelle", "Akteur", "Beschreibung"])
        for dt, dev, src, actor, desc in events:
            w.writerow([local(dt).strftime("%Y-%m-%d %H:%M:%S"), dev, src, actor, desc])
    return out


def main():
    load_ios(); load_android(); load_windows(); load_cloud()
    out = write_timeline()
    print(f"Master-Timeline: {len(events)} Ereignisse -> {os.path.relpath(out, ROOT)}\n")
    print("=== FOKUSFENSTER 25.01.2026 (07:00-12:30 CET) — geraeteuebergreifend ===")
    for dt, dev, src, actor, desc in sorted(events, key=lambda e:e[0]):
        l = local(dt)
        if l.strftime("%Y-%m-%d")=="2026-01-25" and 7 <= l.hour <= 12:
            print(f"  {l:%H:%M}  [{dev:18s}] {actor:8s} {desc[:60]}")


if __name__ == "__main__":
    main()
