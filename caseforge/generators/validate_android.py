#!/usr/bin/env python3
# =====================================================================
# validate_android.py  —  ALEAPP-aequivalentes Acceptance-Gate
# ---------------------------------------------------------------------
# Fuehrt die charakteristischen Abfragen aus ALEAPPs Modulen gegen die
# Android-DBs aus (SMS, Calllog, Contacts, WhatsApp, Chrome). Den finalen
# Lauf mit dem echten ALEAPP fuehrt der/die Dozent/in lokal aus.
# =====================================================================
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_common import Gate, ok_exit

AFS = os.environ.get('WALDWEG_AND_FS', '/tmp/and_build')
P_MMSSMS = os.path.join(AFS, 'data/data/com.android.providers.telephony/databases/mmssms.db')
P_CALLLOG = os.path.join(AFS, 'data/data/com.samsung.android.providers.contacts/databases/calllog.db')
P_CONTACTS = os.path.join(AFS, 'data/data/com.samsung.android.providers.contacts/databases/contacts2.db')
P_WA = os.path.join(AFS, 'data/data/com.whatsapp/databases/msgstore.db')
P_CHROME = os.path.join(AFS, 'data/data/com.android.chrome/app_chrome/Default/History')

G = Gate()
ok = G.ok


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def gate_sms():
    print("SMS (mmssms.db):")
    con = ro(P_MMSSMS)
    rows = con.execute("""SELECT date, address, type, body FROM sms
                          ORDER BY date""").fetchall()
    ok("sms-Query laeuft", len(rows) >= 1, f"{len(rows)} SMS")
    dt = datetime.fromtimestamp(rows[0][0] / 1000, timezone.utc)
    ok("Unix-ms Timestamp plausibel", dt.year == 2026, f"{dt:%Y-%m-%d %H:%M}")
    con.close()


def gate_calllog():
    print("Calllog (calllog.db):")
    con = ro(P_CALLLOG)
    rows = con.execute("""SELECT date, number, type, duration, name FROM calls
                          ORDER BY date""").fetchall()
    ok("calls-Query laeuft", len(rows) == 4, f"{len(rows)} Anrufe")
    # Schluesselanruf Daniel->Tobias 08:25 / 41s
    tob = [r for r in rows if r[2] == 2 and r[3] == 41]
    ok("Tatzeit-Anruf Tobias 41s vorhanden", len(tob) == 1, ref=True)
    con.close()


def gate_contacts():
    print("Contacts (contacts2.db):")
    con = ro(P_CONTACTS)
    rows = con.execute("""
        SELECT rc.display_name, d.data1
        FROM data d
        JOIN raw_contacts rc ON d.raw_contact_id = rc._id
        JOIN mimetypes m ON d.mimetype_id = m._id
        WHERE m.mimetype = 'vnd.android.cursor.item/phone_v2'
    """).fetchall()
    ok("contacts-Join laeuft", len(rows) == 3, f"{len(rows)} Nummern")
    con.close()


def gate_whatsapp():
    print("WhatsApp (msgstore.db, modernes Schema):")
    con = ro(P_WA)
    rows = con.execute("""
        SELECT m.timestamp, m.from_me, j.raw_string, m.text_data
        FROM message m
        JOIN chat c ON m.chat_row_id = c._id
        JOIN jid j ON c.jid_row_id = j._id
        ORDER BY m.timestamp
    """).fetchall()
    ok("message/chat/jid-Join laeuft", len(rows) >= 1, f"{len(rows)} Nachrichten")
    ultimatum = [r for r in rows if "bis Montag" in (r[3] or "")]
    ok("Ultimatum-Nachricht Tobias vorhanden", len(ultimatum) == 1, ref=True)
    con.close()


def gate_chrome():
    print("Chrome History (WebKit-Epoch):")
    con = ro(P_CHROME)
    rows = con.execute("""
        SELECT u.last_visit_time, u.url, u.title
        FROM urls u ORDER BY u.last_visit_time
    """).fetchall()
    ok("urls-Query laeuft", len(rows) >= 1, f"{len(rows)} URLs")
    # WebKit -> lesbares Datum
    def webkit(t):
        return datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=t)
    yr = webkit(rows[0][0]).year
    ok("WebKit-Timestamp dekodierbar", yr == 2026, f"{webkit(rows[0][0]):%Y-%m-%d %H:%M}")
    relevant = [r for r in rows if "handy+orten+partner" in r[1] or "schulden" in r[1]]
    ok("Belastende Suchen vorhanden", len(relevant) == 2, ref=True)
    con.close()


def gate_extended():
    base = os.path.dirname(os.path.dirname(P_CHROME).rsplit("/data/data", 1)[0])  # FS-Root
    fs = P_CHROME.split("/data/data")[0]
    print("Android-Extra:")
    # Scoped-Storage external.db (Profil android_13/14/15) — existenz-gesteuert
    for prov in ("com.google.android.providers.media.module", "com.android.providers.media"):
        ext = os.path.join(fs, "data/data", prov, "databases/external.db")
        if os.path.exists(ext):
            print(f"Scoped Storage ({prov}):")
            c = ro(ext)
            rows = c.execute("SELECT _data, owner_package_name FROM files").fetchall(); c.close()
            ok("external.db files-Tabelle", len(rows) >= 1, f"{len(rows)} Dateieintraege")
            break
    # Privacy Dashboard /system/appops/discrete (existenz-gesteuert, voll-faithful ABX)
    pdd = os.path.join(fs, "data/system/appops/discrete/1.xml")
    if os.path.exists(pdd):
        print("Privacy Dashboard (appops/discrete, ABX):")
        data = open(pdd, "rb").read()
        ok("appops discrete ABX-Magic", data[:4] == b"ABX\x00", repr(data[:4]))
        try:
            import abx_writer as abx
            ev = abx.decode(data)
            ops = [e[2] for e in ev if e[0] == "attr" and e[1] == "n" and isinstance(e[2], str) and e[2].startswith("android:")]
            ok("ABX dekodierbar (Round-Trip) + op-Eintraege", len(ops) >= 1, f"{len(ops)} ops")
        except Exception as e:
            ok("ABX dekodierbar (Round-Trip)", False, str(e)[:40])
    # netpolicy.xml — existenz-gesteuert
    npx = os.path.join(fs, "data/system/netpolicy.xml")
    if os.path.exists(npx):
        txt = open(npx, encoding="utf-8").read()
        print("netpolicy.xml:")
        ok("netpolicy uid-policy-Eintraege", txt.count("uid-policy") >= 1, f"{txt.count('uid-policy')}")
    # recent_tasks (ABX) — existenz-gesteuert
    rtd = os.path.join(fs, "data/system_ce/0/recent_tasks")
    if os.path.isdir(rtd):
        rfiles = [x for x in os.listdir(rtd) if x.endswith(".xml")]
        if rfiles:
            print("recent_tasks (ABX):")
            head = open(os.path.join(rtd, rfiles[0]), "rb").read(4)
            ok("recent_tasks ABX-Magic", head == b"ABX\x00", f"{len(rfiles)} Tasks")
    # usagestats
    us = os.path.join(fs, "data/system/usagestats/0/daily")
    if os.path.isdir(us):
        f = os.listdir(us)
        txt = open(os.path.join(us, f[0])).read() if f else ""
        ok("usagestats XML (Maps/Dialer)", "com.google.android.apps.maps" in txt and "dialer" in txt, ref=True)
    # Samsung Health
    sh = os.path.join(fs, "data/data/com.sec.android.app.shealth/databases/SecureHealthData.db")
    if os.path.exists(sh):
        c = ro(sh); n = c.execute("SELECT COUNT(*) FROM exercise").fetchone()[0]; c.close()
        ok("Samsung Health exercise", n >= 1, ref=True)
    # Google Maps Ziel Waldweg
    mp = os.path.join(fs, "data/data/com.google.android.apps.maps/databases/gmm_myplaces.db")
    if os.path.exists(mp):
        c = ro(mp); t = [r[0] for r in c.execute("SELECT title FROM sync_item").fetchall()]; c.close()
        ok("Maps Ziel 'Waldweg Parkplatz'", any("Waldweg" in x for x in t), str(t), ref=True)
    # wa.db Kontakte
    wadb = os.path.join(fs, "data/data/com.whatsapp/databases/wa.db")
    if os.path.exists(wadb):
        c = ro(wadb); n = c.execute("SELECT COUNT(*) FROM wa_contacts WHERE display_name LIKE '%Klenk%'").fetchone()[0]; c.close()
        ok("WhatsApp wa.db Kontakt Klenk", n >= 1, ref=True)
    # accounts.xml
    ax = os.path.join(fs, "data/system/sync/accounts.xml")
    if os.path.exists(ax):
        ok("accounts.xml (Geraetebindung)", "com.google" in open(ax).read())


def main():
    for p in (P_MMSSMS, P_CALLLOG, P_CONTACTS, P_WA, P_CHROME):
        if not os.path.exists(p):
            print("FEHLT:", p); sys.exit(2)
    gate_sms(); gate_calllog(); gate_contacts(); gate_whatsapp(); gate_chrome(); gate_extended()
    ok_exit(G)


if __name__ == "__main__":
    main()
