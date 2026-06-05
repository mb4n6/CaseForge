#!/usr/bin/env python3
# =====================================================================
# validate_apps.py  —  Light-Gate fuer App-Sandbox-Skelette
# ---------------------------------------------------------------------
# Prueft: iOS-Container haben lesbare metadata.plist (Bundle-ID-Mapping),
# zentrale Sandbox-DBs oeffnen, fallrelevante Inhalte vorhanden.
# =====================================================================
import os
import sys
import plistlib
import sqlite3
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IOS = os.environ.get("WALDWEG_IOS_FS", os.path.join(ROOT, "01_ios_full_fs"))
AND = os.environ.get("WALDWEG_AND_FS", os.path.join(ROOT, "02_android_full_fs"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_common import Gate, ok_exit

G = Gate()
ok = G.ok


import caseforge_rng as cfr
def guid(bundle):
    return cfr.app_guid(bundle)


def ios_container(bundle):
    return os.path.join(IOS, "private/var/mobile/Containers/Data/Application", guid(bundle))


def main():
    capp = os.path.join(IOS, "private/var/mobile/Containers/Data/Application")
    n_ios = len([d for d in os.listdir(capp)]) if os.path.isdir(capp) else 0
    # Teilfall ohne App-Sandboxen -> SKIP (rc=2), nicht FEHLER
    dd_pre = os.path.join(AND, "data/data")
    n_and_pre = len(os.listdir(dd_pre)) if os.path.isdir(dd_pre) else 0
    if n_ios == 0 and n_and_pre == 0:
        print("[SKIP] Keine App-Sandboxen in diesem Fall (app_sandbox nicht selektiert).")
        sys.exit(2)
    print("iOS App-Container:")
    ok("iOS Sandboxen vorhanden", n_ios >= 10, f"{n_ios} Container", ref=True)
    # metadata.plist -> Bundle-ID
    sig = ios_container("org.whispersystems.signal")
    mp = os.path.join(sig, ".com.apple.mobile_container_manager.metadata.plist")
    if os.path.exists(mp):
        bid = plistlib.load(open(mp, "rb")).get("MCMMetadataIdentifier")
        ok("metadata.plist Bundle-ID lesbar", bid == "org.whispersystems.signal", bid, ref=True)
    # DB Navigator Reisesuche
    dbn = os.path.join(ios_container("de.bahn.dbnavigator"), "Documents/recents.sqlite")
    if os.path.exists(dbn):
        c = sqlite3.connect(f"file:{dbn}?mode=ro&immutable=1", uri=True)
        r = c.execute("SELECT to_st FROM recent_journeys").fetchall(); c.close()
        ok("DB Navigator Reisesuche", any("Nachbarstadt" in x[0] for x in r), ref=True)

    print("Android App-Sandboxen:")
    dd = os.path.join(AND, "data/data")
    pkgs = ["org.thoughtcrime.securesms", "ch.threema.app", "org.telegram.messenger",
            "com.starfinanz.smob.android.sfinanzstatus", "com.ebay.kleinanzeigen",
            "de.foduufinanz.finanzguru"]
    present = [p for p in pkgs if os.path.isdir(os.path.join(dd, p))]
    ok("Android Sandboxen vorhanden", len(present) >= 5, f"{len(present)}/{len(pkgs)}", ref=True)
    spk = os.path.join(dd, "com.starfinanz.smob.android.sfinanzstatus/databases/finanzstatus.db")
    if os.path.exists(spk):
        c = sqlite3.connect(f"file:{spk}?mode=ro&immutable=1", uri=True)
        bal = c.execute("SELECT balance_cents FROM accounts").fetchone()[0]
        klenk = c.execute("SELECT COUNT(*) FROM transactions WHERE purpose LIKE '%Klenk%'").fetchone()[0]
        c.close()
        ok("Sparkasse-DB (Saldo negativ + Klenk)", bal < 0 and klenk >= 1, f"saldo={bal}", ref=True)

    ok_exit(G)


if __name__ == "__main__":
    main()
