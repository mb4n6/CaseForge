#!/usr/bin/env python3
# =====================================================================
# caseforge_rng.py  —  seed-gesteuerte Pseudo-Zufaelligkeit (Schritt 1+2)
# ---------------------------------------------------------------------
# Ein zentraler Seed (meta.generator_seed -> WALDWEG_GENERATOR_SEED) speist
# deterministische RNG-Streams. Gleicher Seed => identischer Fall (A3),
# anderer Seed => individuelle Identifikatoren/Mengen/Reihenfolgen.
#
# WICHTIG — Referenz-Stabilitaet: Beim REFERENZ-Seed (REF_SEED) liefern alle
# Faker EXAKT die bisherigen Waldweg-Werte, damit der 12/12-Selbsttest und die
# literalen Gate-Checks unveraendert gruen bleiben. Nur bei abweichendem Seed
# wird variiert.
#
# Was hier randomisiert wird, veraendert die LOESUNG NICHT (IDs, GUIDs, SID,
# Rechnername, IMEI, BSSID, Reihenfolge/Anzahl von Noise). Fall-/loesungstragende
# Inhalte kommen weiterhin deterministisch aus dem Master.
# =====================================================================
import hashlib
import os
import random

REF_SEED = "20260125"           # generator_seed des Referenzfalls Operation Waldweg
REF_SID = "S-1-5-21-1004336348-1177238915-682003330-1000"
REF_COMPUTER = "DESKTOP-REUTER"


def active_seed():
    """Aktiver Seed als String (Env hat Vorrang, sonst Referenz-Seed)."""
    return str(os.environ.get("WALDWEG_GENERATOR_SEED", REF_SEED))


def is_reference():
    return active_seed() == REF_SEED


def _h(*parts):
    return hashlib.sha256(("|".join(str(p) for p in parts)).encode()).hexdigest()


def stream(salt=""):
    """Deterministischer RNG-Stream je Domaene (salt), aus dem aktiven Seed."""
    return random.Random(int(_h(active_seed(), salt), 16) % (2**63))


# ---------------------------------------------------------------------
# Identifikatoren (Referenz-Seed -> Originalwerte; sonst seed-variiert)
# ---------------------------------------------------------------------
def app_guid(bundle):
    """iOS App-Container-UUID. Referenz-Seed -> identisch zu frueher
    (md5(bundle+'20260125')), sonst seed-variiert, gleiches UUID-Format."""
    salt = active_seed()
    h = hashlib.md5((bundle + salt).encode()).hexdigest().upper()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def win_computer_name():
    if is_reference():
        return REF_COMPUTER
    r = stream("win_computer")
    return "DESKTOP-" + "".join(r.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(7))


def win_sid():
    if is_reference():
        return REF_SID
    r = stream("win_sid")
    a, b, c = (r.randint(1000000000, 4000000000) for _ in range(3))
    return f"S-1-5-21-{a}-{b}-{c}-1001"


def imei():
    """14 Stellen + Luhn-Pruefziffer (gueltige IMEI)."""
    if is_reference():
        body = "35693805420879"          # stabiler Referenzwert
    else:
        r = stream("imei")
        body = "35" + "".join(str(r.randint(0, 9)) for _ in range(12))
    digits = [int(d) for d in body]
    s = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    check = (10 - (s % 10)) % 10
    return body + str(check)


def serial(prefix="C7"):
    if is_reference():
        return prefix + "REF0WALDWEG"
    r = stream("serial")
    return prefix + "".join(r.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(10))


def bssid():
    if is_reference():
        return "a4:5e:60:11:22:33"
    r = stream("bssid")
    return ":".join(f"{r.randint(0,255):02x}" for _ in range(6))


# ---------------------------------------------------------------------
# Mengen / Reihenfolge / Zeit-Jitter (Schritt 2-Bausteine)
# ---------------------------------------------------------------------
def sample(pool, n, salt="sample"):
    """n Elemente ohne Wiederholung aus pool (seed-stabil). n>len -> ganzer Pool."""
    r = stream(salt)
    pool = list(pool)
    if n >= len(pool):
        r.shuffle(pool)
        return pool
    return r.sample(pool, n)


def shuffled(seq, salt="shuffle"):
    r = stream(salt)
    out = list(seq)
    r.shuffle(out)
    return out


def jitter_seconds(max_seconds, salt="jitter"):
    if is_reference() or max_seconds <= 0:
        return 0
    return stream(salt).randint(-max_seconds, max_seconds)


if __name__ == "__main__":
    for s in (REF_SEED, "777", "abc"):
        os.environ["WALDWEG_GENERATOR_SEED"] = s
        print(f"seed={s:>10}  comp={win_computer_name():14} sid=...{win_sid()[-6:]}  "
              f"imei={imei()}  guid={app_guid('org.whispersystems.signal')}")
