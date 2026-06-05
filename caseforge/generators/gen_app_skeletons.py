#!/usr/bin/env python3
# =====================================================================
# gen_app_skeletons.py  —  App-Sandbox-Strukturen (iOS + Android)
# ---------------------------------------------------------------------
# Legt fuer eine kuratierte App-Auswahl realistische Sandbox-Verzeichnisse
# an: ueberwiegend Skelett (Config-Plist/XML, leere DBs in Basisschema,
# Cache-Platzhalter), einzelne fallrelevante Apps mit Inhalt.
#
# iOS:    private/var/mobile/Containers/Data/Application/<GUID>/
#           .com.apple.mobile_container_manager.metadata.plist  (Bundle-ID)
#           Library/Preferences/<bundle>.plist, Library/Caches, Documents, tmp
# Android: data/data/<pkg>/
#           shared_prefs/<pkg>_preferences.xml, databases/<db>, cache, files
#
# SQLite wird in /tmp gebaut und kopiert (Mount erlaubt kein In-Place-SQLite).
# =====================================================================
import os
import csv
import json
import hashlib
import plistlib
import shutil
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)
ROOT = os.path.join(os.path.dirname(BUILD), "examples", "operation_waldweg")
import sys
sys.path.insert(0, HERE)
import case_master_io as cmio
IOS = os.environ.get("WALDWEG_IOS_FS", os.path.join(ROOT, "01_ios_full_fs"))
AND = os.environ.get("WALDWEG_AND_FS", os.path.join(ROOT, "02_android_full_fs"))
TMP = "/tmp/app_db_build"
import caseforge_rng as cfr
SEED = "20260125"
manifest = []


def guid(bundle):
    # seed-gesteuert: Referenz-Seed -> identisch zu frueher, sonst variiert
    return cfr.app_guid(bundle)


def ensure(d):
    os.makedirs(d, exist_ok=True)


def w_plist(path, obj):
    ensure(os.path.dirname(path))
    with open(path, "wb") as f:
        plistlib.dump(obj, f)


def w_text(path, s):
    ensure(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


def w_json(path, obj):
    ensure(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def w_sqlite(path, script, rows=None):
    """rows: list of (sql, params-iterable)."""
    ensure(os.path.dirname(path))
    tmp = os.path.join(TMP, hashlib.md5(path.encode()).hexdigest() + ".db")
    ensure(os.path.dirname(tmp))
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript(script)
    if rows:
        for sql, params in rows:
            con.execute(sql, params)
    con.commit(); con.close()
    shutil.copy(tmp, path)


def android_prefs(pairs):
    x = ['<?xml version="1.0" encoding="utf-8" standalone="yes" ?>', "<map>"]
    for k, v in pairs:
        if isinstance(v, bool):
            x.append(f'    <boolean name="{k}" value="{"true" if v else "false"}" />')
        elif isinstance(v, int):
            x.append(f'    <long name="{k}" value="{v}" />')
        else:
            x.append(f'    <string name="{k}">{v}</string>')
    x.append("</map>")
    return "\n".join(x)


def ios_app(bundle, files, relevanz="noise", desc=""):
    base = os.path.join(IOS, "private/var/mobile/Containers/Data/Application", guid(bundle))
    for sub in ("Documents", "Library/Preferences", "Library/Caches", "tmp",
                "Library/Application Support"):
        ensure(os.path.join(base, sub))
    w_plist(os.path.join(base, ".com.apple.mobile_container_manager.metadata.plist"),
            {"MCMMetadataIdentifier": bundle, "MCMMetadataUUID": guid(bundle),
             "MCMMetadataSchemaVersion": 2})
    for rel, kind, content in files:
        p = os.path.join(base, rel)
        if kind == "plist":
            w_plist(p, content)
        elif kind == "sqlite":
            w_sqlite(p, content[0], content[1] if len(content) > 1 else None)
        elif kind == "json":
            w_json(p, content)
        elif kind == "text":
            w_text(p, content)
        elif kind == "blob":
            ensure(os.path.dirname(p)); open(p, "wb").write(content)
    manifest.append(("iPhone", os.path.relpath(base, ROOT), bundle, relevanz, desc))


def android_app(pkg, files, relevanz="noise", desc=""):
    base = os.path.join(AND, "data/data", pkg)
    for sub in ("shared_prefs", "databases", "cache", "files", "code_cache", "app_webview"):
        ensure(os.path.join(base, sub))
    for rel, kind, content in files:
        p = os.path.join(base, rel)
        if kind == "xml":
            w_text(p, content)
        elif kind == "sqlite":
            w_sqlite(p, content[0], content[1] if len(content) > 1 else None)
        elif kind == "json":
            w_json(p, content)
        elif kind == "text":
            w_text(p, content)
        elif kind == "blob":
            ensure(os.path.dirname(p)); open(p, "wb").write(content)
    # externer App-Ordner (haeufig vorhanden)
    ensure(os.path.join(AND, "storage/emulated/0/Android/data", pkg, "files"))
    manifest.append(("Samsung", os.path.relpath(base, ROOT), pkg, relevanz, desc))


def ts(iso):
    return int(datetime.fromisoformat(iso).timestamp())


# =====================================================================
# iOS-Apps (Anna)
# =====================================================================
def build_ios_apps():
    # Signal — Datenbank in echt SQLCipher-verschluesselt -> hier Skelett + Hinweis
    ios_app("org.whispersystems.signal", [
        ("Library/Preferences/org.whispersystems.signal.plist", "plist",
         {"OWSDatabaseEncrypted": True, "lastAppVersion": "7.2.0",
          "RegistrationPhoneNumber": "+4915123456789"}),
        ("Documents/database/signal.sqlite", "blob", b"SQLCipher\x00encrypted-db-skeleton (kein Klartext)"),
        ("Library/Caches/.skeleton", "text", ""),
    ], "context", "Signal (verschluesselt) – verdeckte Kommunikation, Inhalt nicht im Klartext")

    # Threema — verschluesselt
    ios_app("ch.threema.iapp.ThreemaApp", [
        ("Library/Preferences/ch.threema.iapp.ThreemaApp.plist", "plist",
         {"PushIdentity": "ANNA1234", "LinkedMobileNo": "+4915123456789"}),
        ("Documents/ThreemaData.sqlite", "blob", b"encrypted-threema-skeleton"),
    ], "context", "Threema (verschluesselt) – verdeckte Kommunikation")

    # Telegram — Postbox-Skelett
    ios_app("ph.telegra.Telegraph", [
        ("Library/Preferences/ph.telegra.Telegraph.plist", "plist", {"accountId": 778899}),
        ("Documents/telegram-data/account-778899/postbox/db/db_sqlite", "sqlite",
         ("CREATE TABLE t0 (key BLOB PRIMARY KEY, value BLOB);", None)),
    ], "noise", "Telegram – Postbox-Skelett")

    # Instagram
    ios_app("com.burbn.instagram", [
        ("Library/Preferences/com.burbn.instagram.plist", "plist",
         {"current_user": "anna.reuter", "last_login": "2026-01-23T20:11:00"}),
        ("Documents/direct.db", "sqlite",
         ("CREATE TABLE threads (thread_id TEXT, title TEXT, last_activity INTEGER);",
          [("INSERT INTO threads VALUES (?,?,?)", ("t_1", "lena_vogt", ts("2026-01-21T20:30:00+01:00")))])),
    ], "noise", "Instagram – Direct-Skelett")

    # Spotify / Netflix — reine Skelette
    ios_app("com.spotify.client", [
        ("Library/Preferences/com.spotify.client.plist", "plist", {"username": "anna_r", "premium": True}),
        ("Library/Application Support/PersistentCache/Storage/.skeleton", "text", "")], "noise", "Spotify")
    ios_app("com.netflix.Netflix", [
        ("Library/Preferences/com.netflix.Netflix.plist", "plist", {"profileName": "Anna"})], "noise", "Netflix")

    # DB Navigator — letzte Reisesuchen (fallrelevant: Bahn 25.01)
    ios_app("de.bahn.dbnavigator", [
        ("Library/Preferences/de.bahn.dbnavigator.plist", "plist", {"lastSearchDate": "2026-01-25"}),
        ("Documents/recents.sqlite", "sqlite",
         ("CREATE TABLE recent_journeys (id INTEGER PRIMARY KEY, from_st TEXT, to_st TEXT, ts INTEGER);",
          [("INSERT INTO recent_journeys (from_st,to_st,ts) VALUES (?,?,?)",
            ("Stuttgart Hbf", "Nachbarstadt", ts("2026-01-25T07:09:00+01:00")))])),
    ], "context", "DB Navigator – Reisesuche Stuttgart->Nachbarstadt 25.01 07:09 (passt zu Safari/BIOME)")

    # ImmobilienScout24 — gespeicherte Suche 2-Zimmer (fallrelevant)
    ios_app("de.is24.iphone", [
        ("Library/Preferences/de.is24.iphone.plist", "plist", {"loggedIn": True}),
        ("Documents/saved_searches.sqlite", "sqlite",
         ("CREATE TABLE searches (id INTEGER PRIMARY KEY, query TEXT, rooms INTEGER, created INTEGER);",
          [("INSERT INTO searches (query,rooms,created) VALUES (?,?,?)",
            ("Wohnung mieten Nachbarstadt", 2, ts("2026-01-22T22:40:00+01:00")))])),
    ], "context", "ImmobilienScout24 – gespeicherte 2-Zimmer-Suche (passt zu Trennungsabsicht)")

    # Komoot (gym/outdoor), Gmail, Outlook — Skelette
    ios_app("de.komoot.iphone", [
        ("Library/Preferences/de.komoot.iphone.plist", "plist", {"user": "anna"})], "noise", "Komoot")
    ios_app("com.google.Gmail", [
        ("Library/Preferences/com.google.Gmail.plist", "plist", {"account": "anna.reuter@gmail.com"})], "noise", "Gmail")
    ios_app("com.apple.mobilenotes", [
        ("Documents/NoteStore.sqlite", "sqlite",
         ("CREATE TABLE ZICNOTEDATA (Z_PK INTEGER PRIMARY KEY, ZDATA BLOB);"
          "CREATE TABLE notes_plain (pk INTEGER, title TEXT, body TEXT, modified INTEGER);",
          [("INSERT INTO notes_plain VALUES (?,?,?,?)",
            (1, "Gedanken", "Ich muss mit Daniel reden. Es geht so nicht weiter.", ts("2026-01-18T23:05:00+01:00")))]))],
        "context", "Notizen – persoenliche Notiz (Belastungskontext)")


# =====================================================================
# Android-Apps (Daniel)
# =====================================================================
def build_android_apps():
    android_app("org.thoughtcrime.securesms", [
        ("shared_prefs/org.thoughtcrime.securesms_preferences.xml", "xml",
         android_prefs([("pref_local_number", "+4915223456788"),
                        ("pref_database_encrypted", True)])),
        ("databases/signal.db", "blob", b"SQLCipher\x00encrypted (kein Klartext)"),
    ], "context", "Signal (verschluesselt) – verdeckte Kommunikation Daniel")

    android_app("ch.threema.app", [
        ("shared_prefs/ch.threema.app_preferences.xml", "xml",
         android_prefs([("identity", "DANI5678")])),
        ("databases/threema.db", "blob", b"encrypted-threema")], "context", "Threema (verschluesselt)")

    android_app("org.telegram.messenger", [
        ("shared_prefs/userconfing.xml", "xml", android_prefs([("user", 445566)])),
        ("files/tgnet.dat", "blob", b"telegram-tgnet-skeleton"),
        ("files/cache4.db", "sqlite", ("CREATE TABLE messages_v2 (mid INTEGER, uid INTEGER, date INTEGER, data BLOB);", None)),
    ], "noise", "Telegram – cache4-Skelett")

    # Sparkasse Banking (fallrelevant: Schulden/Finanzen)
    android_app("com.starfinanz.smob.android.sfinanzstatus", [
        ("shared_prefs/com.starfinanz.smob.android.sfinanzstatus_preferences.xml", "xml",
         android_prefs([("last_login", "2026-01-24T22:35:00"), ("biometric_enabled", True)])),
        ("databases/finanzstatus.db", "sqlite",
         ("CREATE TABLE accounts (id INTEGER PRIMARY KEY, iban TEXT, balance_cents INTEGER, updated INTEGER);"
          "CREATE TABLE transactions (id INTEGER PRIMARY KEY, account INTEGER, ts INTEGER, amount_cents INTEGER, purpose TEXT);",
          [("INSERT INTO accounts (iban,balance_cents,updated) VALUES (?,?,?)",
            ("DE12500105170648489890", -184213, ts("2026-01-24T22:35:00+01:00"))),
           ("INSERT INTO transactions (account,ts,amount_cents,purpose) VALUES (?,?,?,?)",
            (1, ts("2026-01-15T09:00:00+01:00"), -30000, "Ueberweisung T. Klenk")),
           ("INSERT INTO transactions (account,ts,amount_cents,purpose) VALUES (?,?,?,?)",
            (1, ts("2026-01-05T08:00:00+01:00"), 312000, "Gehalt"))])),
    ], "context", "Sparkasse-App – Konto im Minus, Teilzahlung an Klenk (Schuldenmotiv)")

    # Kleinanzeigen (passt zu Suche), PayPal, Outlook, Gmail, Komoot, Discord, Finanzguru
    android_app("com.ebay.kleinanzeigen", [
        ("shared_prefs/com.ebay.kleinanzeigen_preferences.xml", "xml", android_prefs([("userId", "u_99")])),
        ("databases/search_history.db", "sqlite",
         ("CREATE TABLE searches (id INTEGER PRIMARY KEY, term TEXT, ts INTEGER);",
          [("INSERT INTO searches (term,ts) VALUES (?,?)", ("gebrauchtwagen schnell verkaufen", ts("2026-01-23T21:00:00+01:00")))]))],
        "context", "Kleinanzeigen – Suche 'Auto schnell verkaufen' (Geldnot)")

    android_app("com.paypal.android.p2pmobile", [
        ("shared_prefs/com.paypal.android.p2pmobile_preferences.xml", "xml", android_prefs([("email", "d.reuter@example.de")]))],
        "noise", "PayPal")
    android_app("com.microsoft.office.outlook", [
        ("shared_prefs/com.microsoft.office.outlook_preferences.xml", "xml", android_prefs([("primary_email", "d.reuter@example.de")])),
        ("databases/outlook.db", "sqlite", ("CREATE TABLE messages (id INTEGER PRIMARY KEY, subject TEXT, from_addr TEXT, ts INTEGER);", None))],
        "noise", "Outlook – Mail-Skelett")
    android_app("com.google.android.gm", [
        ("shared_prefs/Gmail.xml", "xml", android_prefs([("account", "daniel.reuter@gmail.com")]))], "noise", "Gmail")
    android_app("de.komoot.android", [
        ("shared_prefs/de.komoot.android_preferences.xml", "xml", android_prefs([("user", "daniel")]))], "noise", "Komoot")
    android_app("com.discord", [
        ("shared_prefs/com.discord_preferences.xml", "xml", android_prefs([("user_id", "1122334455")]))], "noise", "Discord")
    android_app("de.foduufinanz.finanzguru", [
        ("shared_prefs/finanzguru_prefs.xml", "xml", android_prefs([("onboarding_done", True)])),
        ("databases/finanzguru.db", "sqlite",
         ("CREATE TABLE budgets (id INTEGER PRIMARY KEY, name TEXT, planned_cents INTEGER, spent_cents INTEGER);",
          [("INSERT INTO budgets (name,planned_cents,spent_cents) VALUES (?,?,?)", ("Schulden/Kredite", 0, 184213))]))],
        "context", "Finanzguru – Budget 'Schulden/Kredite' (Geldnot)")


def write_manifest():
    out = os.path.join(ROOT, "06_master", "App_Skeletons_Manifest.csv")
    ensure(os.path.dirname(out))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["geraet", "sandbox_pfad", "bundle/paket", "relevanz", "beschreibung"])
        w.writerows(sorted(manifest))
    return out


def build_min_ios(bundle):
    """Minimal-valides iOS-Sandbox-Skelett (metadata.plist + Standardordner)."""
    ios_app(bundle, [("Library/Caches/.skeleton", "text", "")], "noise",
            "App-Sandbox (Skelett, spec-getrieben)")


def build_min_android(pkg):
    """Minimal-valides Android-Sandbox-Skelett (shared_prefs/databases)."""
    android_app(pkg, [("shared_prefs/%s_preferences.xml" % pkg, "xml",
                       android_prefs([("installed", True)]))], "noise",
                "App-Sandbox (Skelett, spec-getrieben)")


def main():
    ensure(TMP)
    ios_pkgs = cmio.app_packages("ios")
    and_pkgs = cmio.app_packages("android")
    if ios_pkgs or and_pkgs:
        print(f"App-Sandbox-Inhaltsquelle: Master "
              f"(iOS={len(ios_pkgs or [])}, Android={len(and_pkgs or [])})")
        for b in (ios_pkgs or []):
            build_min_ios(b)
        for p in (and_pkgs or []):
            build_min_android(p)
    elif cfr.is_reference():
        print("App-Sandbox-Inhaltsquelle: Referenz-Fallback")
        build_ios_apps()
        build_android_apps()
    else:
        # seed-gezogene, scope-skalierte Noise-Apps aus dem Pool
        import noise_pools as npool
        ni = cmio.noise_count(10, key="ios_apps")
        na = cmio.noise_count(10, key="android_apps")
        ios_sel = cfr.sample(npool.apps("ios"), ni, salt="ios_apps")
        and_sel = cfr.sample(npool.apps("android"), na, salt="android_apps")
        print(f"App-Sandbox-Inhaltsquelle: Pool/seed (scope, iOS={len(ios_sel)}, Android={len(and_sel)})")
        for b in ios_sel:
            build_min_ios(b)
        for p in and_sel:
            build_min_android(p)
    out = write_manifest()
    ni = sum(1 for m in manifest if m[0] == "iPhone")
    na = sum(1 for m in manifest if m[0] == "Samsung")
    print(f"App-Skelette erzeugt: {ni} iOS + {na} Android = {len(manifest)} Apps")
    print(f"Manifest: {os.path.relpath(out, ROOT)}")
    for g, p, b, r, d in sorted(manifest):
        print(f"  [{r:7s}] {g:8s} {b}")


if __name__ == "__main__":
    main()
