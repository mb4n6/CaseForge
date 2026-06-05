#!/usr/bin/env python3
# =====================================================================
# CaseForge — Spec -> case_master.yaml Adapter
# ---------------------------------------------------------------------
# Projiziert einen (LLM-vorgeschlagenen, vom Menschen verifizierten)
# Case-Spec (schema/case_spec.schema.json) auf ein generator-taugliches
# case_master.yaml ("Eine Wahrheit, viele Projektionen").
#
# Prinzip: Der Referenz-Master dient als BASIS, damit alle Subtrees, die
# einzelne Generatoren noch fest erwarten (browsing, chat_threads,
# noise_profiles, app_sandboxes, ios_extra, ...), vorhanden bleiben und
# der Build gruen bleibt. Die im Spec GELIEFERTEN Abschnitte (meta,
# persons, devices, timeline, locations, browsing, chat_threads,
# planted_inconsistencies, solution_key) UEBERSCHREIBEN die Basis —
# so kommen Inhalte wirklich aus dem Spec, nicht aus dem Referenzfall.
#
# OS-Profile (profiles/<os_profile>.yaml) liefern os_version und die
# zu bauenden BIOME-Streams je Geraet.
#
# Verwendung:
#   python3 spec_to_master.py --spec out/case_spec.json --out cases/x/case_master.yaml
#   (forge.py build --spec ... ruft dies automatisch auf)
# =====================================================================
import argparse
import os
import sys

try:
    import yaml
except ImportError:
    print("PyYAML fehlt — pip install pyyaml --break-system-packages")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REF_MASTER = os.path.join(ROOT, "09_build", "case_master.yaml")
PROFILES = os.path.join(HERE, "profiles")

# Spec-Abschnitte, die – wenn vorhanden – die Referenz-Basis ERSETZEN.
# 'devices' bewusst NICHT hier — wird via map_device() separat projiziert.
OVERRIDE_SECTIONS = [
    "persons", "timeline", "locations", "browsing",
    "chat_threads", "location_tracks", "browser_history",
    "documents", "app_packages", "planted_inconsistencies",
    "solution_key", "noise_profiles",
]

# Profil-Standard fuer BIOME-Streams je Plattform (falls Profil nichts nennt)
DEFAULT_BIOME = ["_DKEvent.Safari.History", "App.InFocus",
                 "Device.BootSession", "Device.ScreenLocked"]


def load_yaml(p):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_profile(name):
    p = os.path.join(PROFILES, f"{name}.yaml")
    return load_yaml(p) if os.path.exists(p) else {}


def map_device(d):
    """Spec-Device -> case_master-Device. Plattform->type; OS-Profil->os_version."""
    prof = load_profile(d.get("os_profile", ""))
    plat = d.get("platform", prof.get("platform", ""))
    out = {
        "id": d.get("id"),
        "owner": d.get("owner"),
        "type": plat,
        "model": d.get("model") or (prof.get("device_examples", [""]) or [""])[0],
        "os_version": prof.get("os_version", d.get("os_version", "")),
        "extraction": d.get("extraction", "Full File System"),
        "os_profile": d.get("os_profile", ""),
    }
    if d.get("artifact_classes"):
        out["artifact_classes"] = d["artifact_classes"]
    if plat == "ios":
        out["biome_streams_built"] = prof.get("biome_streams", DEFAULT_BIOME)
    # Profil-gesteuerte Artefakt-Flags (versionstypische Spuren) ans Geraet haengen.
    # Spec-Device kann sie ueber 'overrides' gezielt ueberschreiben.
    ov = dict(prof.get("artifact_overrides", {}) or {})
    ov.update(d.get("overrides", {}) or {})
    if ov:
        out["overrides"] = ov
    return out


def build_master(spec, base):
    """Ueberlagert den Spec auf den Referenz-Master (Basis)."""
    cm = dict(base)  # flache Kopie der Top-Level-Keys

    # ---- meta ----
    sm = spec.get("meta", {})
    meta = dict(base.get("meta", {}))
    for k in ("case_name", "version", "generator_seed", "timezone",
              "language_primary", "focus_window", "data_period", "real_basis"):
        if k in sm:
            meta[k] = sm[k]
    if spec.get("deliktart"):
        meta["deliktart"] = spec["deliktart"]
    if spec.get("lernziel"):
        meta["lernziel"] = spec["lernziel"]
    # Seed: Spec-Wert hat Vorrang; sonst NEUEN Zufalls-Seed vergeben (nicht den
    # Referenz-Seed erben!), damit jeder Fall eigene Identifikatoren/Mengen erhaelt.
    # Reproduzierbar, da der Seed im Master gespeichert wird.
    if "generator_seed" not in sm:
        import random as _r
        meta["generator_seed"] = _r.randint(10_000_000, 99_999_999)
    meta["disclaimer"] = "synthetic_training_data_only"  # Leitplanke: immer erzwingen
    meta["derived_from"] = "CaseForge spec_to_master.py"
    cm["meta"] = meta

    # Umfang/Noise-Steuerung durchreichen (Schritt 2)
    for k in ("scope", "volume", "noise_density"):
        if k in sm:
            meta[k] = sm[k]

    # ---- devices (gemappt) ----
    if spec.get("devices"):
        cm["devices"] = [map_device(d) for d in spec["devices"]]

    # ---- direkt uebernommene Abschnitte ----
    for sec in OVERRIDE_SECTIONS:
        if sec in spec and spec[sec] is not None:
            cm[sec] = spec[sec]

    return cm


def main():
    ap = argparse.ArgumentParser(description="Spec -> case_master.yaml")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default=REF_MASTER,
                    help="Referenz-Master als Basis (Default: 09_build/case_master.yaml)")
    args = ap.parse_args()

    import json
    spec = json.load(open(args.spec, encoding="utf-8"))
    base = load_yaml(args.base)
    cm = build_master(spec, base)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        yaml.safe_dump(cm, f, allow_unicode=True, sort_keys=False, width=100)
    nd = len(cm.get("devices", []))
    nt = len(cm.get("timeline", []))
    np_ = len(cm.get("persons", []))
    print(f"case_master geschrieben: {args.out}")
    print(f"  Personen={np_}  Geraete={nd}  Timeline={nt}  "
          f"Delikt={cm['meta'].get('deliktart','-')}")


if __name__ == "__main__":
    main()
