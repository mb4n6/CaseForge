#!/usr/bin/env python3
# =====================================================================
# case_master_io.py  —  gemeinsamer Master-Loader fuer alle Generatoren
# ---------------------------------------------------------------------
# "Eine Wahrheit, viele Projektionen": liest das aktive case_master.yaml
# (WALDWEG_CASE_MASTER, sonst 09_build/case_master.yaml) und liefert
# strukturierte Accessoren. Generatoren nutzen diese mit FALLBACK auf ihre
# bisherigen Referenz-Inhalte — fehlt eine Struktur im Master, bleibt der
# Referenzfall unveraendert (Build bleibt gruen).
#
# OPTIONALE Nachrichten-Konvention (pro chat_thread):
#   chat_threads:
#     - id: anna_jonas
#       channel: imessage            # imessage | whatsapp | sms | imessage_and_whatsapp
#       participants: [anna, jonas]
#       messages:
#         - {t: "2026-01-25T07:20:00+01:00", from: anna, text: "...", deleted: false}
# Personen sollten 'phone' tragen (persons[].phone), damit Handles entstehen.
# =====================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(HERE)

try:
    import yaml
except ImportError:
    yaml = None

_CACHE = {}


def master_path():
    return os.environ.get("WALDWEG_CASE_MASTER",
                          os.path.join(BUILD, "case_master.yaml"))


def load_master():
    """Laedt das aktive case_master (gecached). Leeres dict, wenn nicht lesbar."""
    p = master_path()
    if p in _CACHE:
        return _CACHE[p]
    if yaml is None or not os.path.exists(p):
        _CACHE[p] = {}
        return {}
    with open(p, encoding="utf-8") as f:
        cm = yaml.safe_load(f) or {}
    _CACHE[p] = cm
    return cm


# ---------------------------------------------------------------------
# Umfang / Noise-Steuerung (Schritt 2)
# ---------------------------------------------------------------------
SCOPE_FACTOR = {"s": 0.4, "m": 1.0, "l": 2.0, "xl": 4.0}


def language_short(cm=None):
    cm = cm or load_master()
    loc = str((cm.get("meta", {}) or {}).get("language_primary", "de-DE"))
    return loc[:2].lower()


def scope(cm=None):
    cm = cm or load_master()
    return str((cm.get("meta", {}) or {}).get("scope", "M")).lower()


def noise_density(cm=None):
    cm = cm or load_master()
    try:
        return float((cm.get("meta", {}) or {}).get("noise_density", 1.0))
    except Exception:
        return 1.0


def noise_count(base, key=None, cm=None):
    """Skaliert eine Basis-Noise-Menge mit scope-Faktor * noise_density;
    optionaler harter Override via meta.volume[key]. Mind. 0."""
    cm = cm or load_master()
    vol = (cm.get("meta", {}) or {}).get("volume", {}) or {}
    if key and key in vol:
        try:
            return max(0, int(vol[key]))
        except Exception:
            pass
    factor = SCOPE_FACTOR.get(scope(cm), 1.0) * noise_density(cm)
    return max(0, int(round(base * factor)))


# ---------------------------------------------------------------------
# Personen / Geraete
# ---------------------------------------------------------------------
def persons_by_id(cm=None):
    cm = cm or load_master()
    return {p["id"]: p for p in cm.get("persons", []) if "id" in p}


def phone_of(person_id, cm=None, default=None):
    p = persons_by_id(cm).get(person_id, {})
    return p.get("phone", default)


def name_of(person_id, cm=None, default=None):
    p = persons_by_id(cm).get(person_id, {})
    return p.get("name", default or person_id)


def device_owner(device_type, cm=None):
    """Person-id des ersten Geraets eines Typs (ios|android|windows)."""
    cm = cm or load_master()
    for d in cm.get("devices", []):
        if d.get("type") == device_type or d.get("platform") == device_type:
            return d.get("owner")
    return None


# ---------------------------------------------------------------------
# Nachrichten je Kanal (strukturierte Konvention)
# ---------------------------------------------------------------------
def _channel_match(thread_channel, want):
    tc = (thread_channel or "").lower()
    return want in tc


def threads_for(channel, owner_id, cm=None):
    """Liefert strukturierte Threads des Geraete-Besitzers fuer einen Kanal.
    Rueckgabe: dict {counterpart_phone_or_id: [(iso, is_from_me, text, deleted), ...]}
    oder None, wenn KEIN Thread strukturierte 'messages' traegt (=> Fallback).
    """
    cm = cm or load_master()
    pbi = persons_by_id(cm)
    out = {}
    found_structured = False
    for t in cm.get("chat_threads", []):
        if not _channel_match(t.get("channel"), channel):
            continue
        parts = t.get("participants", [])
        if owner_id not in parts:
            continue
        msgs = t.get("messages")
        if not msgs:
            continue
        found_structured = True
        # Gegenpart bestimmen (erste Person != owner mit Telefon, sonst Thread-id)
        others = [p for p in parts if p != owner_id]
        cp = None
        for o in others:
            cp = pbi.get(o, {}).get("phone") or o
            if cp:
                break
        key = cp or t.get("id")
        seq = []
        for m in msgs:
            is_from_me = 1 if m.get("from") == owner_id else 0
            seq.append((m["t"], is_from_me, m.get("text", ""),
                        bool(m.get("deleted", False))))
        out.setdefault(key, []).extend(seq)
    return out if found_structured else None


# ---------------------------------------------------------------------
# Standort-Spur (optionale Konvention)
#   location_tracks:
#     anna:                      # person-id ODER device-id
#       - {t: "...", lat: 48.7, lon: 9.1, kind: cell, mcc: 262, mnc: 2, lac: 4101, ci: 11001}
#       - {t: "...", lat: 48.7, lon: 9.1, kind: wifi, bssid: "a4:5e:.."}
# ---------------------------------------------------------------------
def location_track(owner_id, cm=None):
    """Liefert (cells, wifis) als Listen oder (None, None), wenn keine Spur.
    cells: [(iso, lat, lon, mcc, mnc, lac, ci), ...]
    wifis: [(iso, lat, lon, bssid), ...]
    """
    cm = cm or load_master()
    tracks = cm.get("location_tracks", {}) or {}
    pts = tracks.get(owner_id)
    if not pts:
        return None, None
    cells, wifis = [], []
    for p in pts:
        kind = (p.get("kind") or "cell").lower()
        if kind == "wifi":
            wifis.append((p["t"], p.get("lat"), p.get("lon"), p.get("bssid", "00:00:00:00:00:00")))
        else:
            cells.append((p["t"], p.get("lat"), p.get("lon"),
                          p.get("mcc", 262), p.get("mnc", 2),
                          p.get("lac", 0), p.get("ci", 0)))
    return (cells or None), (wifis or None)


# ---------------------------------------------------------------------
# Browser-Verlauf (optionale Konvention)
#   browser_history:
#     <person- ODER device-id>:
#       - {t: "...", url: "https://...", title: "..."}
# ---------------------------------------------------------------------
def device_id_for(platform, cm=None):
    cm = cm or load_master()
    for d in cm.get("devices", []):
        if d.get("type") == platform or d.get("platform") == platform:
            return d.get("id")
    return None


def browser_history(platform, cm=None):
    """Strukturierter Browser-Verlauf fuer das Geraet einer Plattform.
    Schluessel im Master: device-id ODER owner-id. -> Liste [(iso,url,title)]
    oder None, wenn keine Struktur vorhanden (=> Fallback)."""
    cm = cm or load_master()
    bh = cm.get("browser_history", {}) or {}
    if not bh:
        return None
    did = device_id_for(platform, cm)
    owner = device_owner(platform, cm)
    entries = bh.get(did) or bh.get(owner)
    if not entries:
        return None
    return [(e["t"], e.get("url", ""), e.get("title", "")) for e in entries]


# ---------------------------------------------------------------------
# Gruppen-Chats (Konvention: chat_threads mit *_group-Kanal + messages[].sender)
# ---------------------------------------------------------------------
def group_threads(channel_base, owner_id, cm=None):
    """Gruppen-Threads des Besitzers (Kanal enthaelt channel_base + 'group').
    Rueckgabe: [(subject, [(iso, is_from_me, sender_label, text), ...]), ...]
    oder None, wenn keine strukturierten Gruppen vorhanden."""
    cm = cm or load_master()
    out = []
    found = False
    for t in cm.get("chat_threads", []):
        ch = (t.get("channel") or "").lower()
        if channel_base not in ch or "group" not in ch:
            continue
        if owner_id not in (t.get("participants") or []):
            continue
        msgs = t.get("messages")
        if not msgs:
            continue
        found = True
        seq = []
        for m in msgs:
            frm = m.get("from")
            is_me = 1 if frm == owner_id else 0
            label = None if is_me else (name_of(frm, cm, frm) if frm else m.get("sender"))
            seq.append((m["t"], is_me, label, m.get("text", "")))
        out.append((t.get("subject") or t.get("id"), seq))
    return out if found else None


# ---------------------------------------------------------------------
# Dokumente (optionale Konvention)
#   documents:
#     - {device: ios|android|windows, area: downloads|documents, name: "..",
#        kind: txt|csv|docx|xlsx|pdf, relevance: noise|context|critical,
#        desc: "..", text: "..(optional Inhalt)"}
# ---------------------------------------------------------------------
def documents(cm=None):
    cm = cm or load_master()
    return cm.get("documents") or None


# ---------------------------------------------------------------------
# App-Pakete (optionale Konvention)
#   app_packages:
#     ios:     ["org.whispersystems.signal", ...]
#     android: ["org.thoughtcrime.securesms", ...]
# ---------------------------------------------------------------------
def app_packages(platform, cm=None):
    cm = cm or load_master()
    ap = cm.get("app_packages", {}) or {}
    return ap.get(platform) or None


if __name__ == "__main__":
    cm = load_master()
    print("master:", master_path())
    print("persons:", list(persons_by_id(cm)))
    print("ios owner:", device_owner("ios", cm))
    print("imessage threads:", (threads_for("imessage", device_owner("ios", cm), cm) or "—(Fallback)"))
