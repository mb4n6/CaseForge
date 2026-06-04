#!/usr/bin/env python3
# =====================================================================
# CaseForge — CLI-Orchestrator
# ---------------------------------------------------------------------
#   forge.py catalog  [--spec s.json]            Artefaktuebersicht
#   forge.py propose  --backend cowork|ollama --input e.json
#   forge.py init     --name <fall> [--from case_master.yaml]
#   forge.py build    (--case <fall> | --root <dir>) [--spec s.json]
#   forge.py validate (--case <fall> | --root <dir>)
#   forge.py run      (--case <fall> | --root <dir>)     build+validate
#
# Generatoren liegen in 09_build/generators; Registry steuert Auswahl.
# case_master pro Fall via WALDWEG_CASE_MASTER (steuert BIOME-Inhalte).
# =====================================================================
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # Operation_Waldweg (Referenzfall)
GEN = os.path.join(ROOT, "09_build", "generators")
REF_MASTER = os.path.join(ROOT, "09_build", "case_master.yaml")
CASES = os.path.join(HERE, "cases")
sys.path.insert(0, HERE)
import registry as R

DEVDIRS = ["01_ios_full_fs", "02_android_full_fs", "03_windows_triage",
           "04_cloud_exports", "05_police_records", "06_master",
           "07_multimedia", "08_multilingual"]


def case_dir(args):
    if getattr(args, "case", None):
        return os.path.join(CASES, args.case)
    return args.root


def _env(root, case_master=None):
    e = dict(os.environ)
    e["WALDWEG_IOS_FS"] = os.path.join(root, "01_ios_full_fs")
    e["WALDWEG_AND_FS"] = os.path.join(root, "02_android_full_fs")
    e["WALDWEG_WIN_FS"] = os.path.join(root, "03_windows_triage")
    e["WALDWEG_CLOUD"] = os.path.join(root, "04_cloud_exports")
    e["WALDWEG_OW"] = root  # verify_solution.py zielt auf den aktiven Root
    if case_master and os.path.exists(case_master):
        e["WALDWEG_CASE_MASTER"] = case_master
    return e


def _run(module, env):
    path = os.path.join(GEN, module)
    if not os.path.exists(path):
        print(f"  [SKIP] {module}"); return True
    return subprocess.run([sys.executable, path], env=env).returncode == 0


def cmd_catalog(args):
    cmd = [sys.executable, os.path.join(HERE, "catalog.py")]
    subprocess.run(cmd)


def cmd_propose(args):
    import llm, i18n
    ui = json.load(open(args.input, encoding="utf-8")) if args.input else {
        "deliktart": args.delikt or "(angeben)", "lernziel": args.lernziel or "",
        "devices": [], "assets_count": args.assets or 0}
    # Sprachauswahl: CLI --lang hat Vorrang, sonst Eingabefeld, sonst Default
    if getattr(args, "lang", None):
        ui["language"] = args.lang
    lang = i18n.short(ui.get("language"))
    ui["language"] = i18n.locale(lang)
    print(f"[Sprache/Language: {i18n.endonym(lang)} ({i18n.locale(lang)})]")
    prompt = llm.build_prompt(ui)
    outdir = os.path.join(HERE, "out")
    if args.backend == "ollama":
        url = getattr(args, "url", None) or "http://localhost:11434"
        to = getattr(args, "timeout", None) or 1800
        print(f"[ollama] {args.model} @ {url} (Streaming, Timeout {to}s) ...")
        os.makedirs(outdir, exist_ok=True)
        raw = llm.propose_ollama(prompt, model=args.model, url=url, timeout=to)
        open(os.path.join(outdir, "proposal_raw.txt"), "w", encoding="utf-8").write(raw)
        print(f"-> out/proposal_raw.txt ({len(raw)} Zeichen)")
    else:
        print(llm.propose_cowork(prompt, outdir))


def cmd_init(args):
    d = os.path.join(CASES, args.name)
    for sub in DEVDIRS:
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    master = os.path.join(d, "case_master.yaml")
    src = args.frm or REF_MASTER
    if os.path.exists(src) and not os.path.exists(master):
        shutil.copy(src, master)
    print(f"Fall initialisiert: {d}")
    print(f"  case_master: {master}  (anpassen, dann 'forge.py build --case {args.name}')")


def _modules_for(spec, platforms):
    if spec:
        return R.select_for_spec(spec)
    out, seen = [], set()
    for g in R.REGISTRY:
        if platforms and g.platform not in platforms and g.platform not in ("crossdevice", "cloud"):
            continue
        if g.module not in seen:
            seen.add(g.module); out.append(g.module)
    return out


def cmd_build(args):
    root = case_dir(args)
    spec = json.load(open(args.spec, encoding="utf-8")) if args.spec else None
    master = os.path.join(root, "case_master.yaml")
    # Spec -> case_master.yaml (Adapter): Fallinhalte kommen aus dem Spec
    if args.spec:
        os.makedirs(root, exist_ok=True)
        rc = subprocess.run([sys.executable, os.path.join(HERE, "spec_to_master.py"),
                             "--spec", args.spec, "--out", master]).returncode
        if rc != 0:
            print("FEHLER: spec_to_master fehlgeschlagen"); sys.exit(1)
    master = master if os.path.exists(master) else REF_MASTER
    mods = _modules_for(spec, args.platform)
    env = _env(root, master)
    print(f"Build -> {root}\ncase_master: {master}\nGeneratoren ({len(mods)}): {', '.join(m[:-3] for m in mods)}")
    ok = all(_run(m, env) for m in mods)
    # Per-Fall-Katalog
    subprocess.run([sys.executable, os.path.join(HERE, "catalog.py"),
                    "--out", os.path.join(root, "06_master", "Artefakt_Katalog.md"),
                    "--csv", os.path.join(root, "06_master", "Artefakt_Katalog.csv")])
    print("BUILD:", "OK" if ok else "FEHLER")
    sys.exit(0 if ok else 1)


def _gate_mode(root, master, override=None):
    """all = Referenz-Selbsttest (Format + Loesung); format = beliebiger Spec-Fall.

    Robuste, inhaltsbasierte Auto-Wahl (unabhaengig vom Pfad):
      - 'format', wenn der Master spec-abgeleitet ist (meta.derived_from), ODER
        wenn der Fallname NICHT der Waldweg-Referenzfall ist.
      - 'all' nur fuer den Waldweg-Referenzfall (case_name enthaelt 'Waldweg'
        und kein derived_from).
    Zusaetzliche Absicherung: verify_solution.py ueberspringt selbst (rc=2),
    wenn die Referenz-Artefakte fehlen.
    """
    if override:
        return override
    try:
        import yaml
        cm = yaml.safe_load(open(master, encoding="utf-8")) if os.path.exists(master) else {}
        meta = cm.get("meta", {}) or {}
        if meta.get("derived_from"):
            return "format"
        return "all" if "waldweg" in str(meta.get("case_name", "")).lower() else "format"
    except Exception:
        return "format"


def cmd_validate(args):
    root = case_dir(args)
    master = os.path.join(root, "case_master.yaml")
    env = _env(root, master)
    mode = _gate_mode(root, master, getattr(args, "mode", None))
    env["WALDWEG_GATE_MODE"] = mode
    print(f"[Gate-Modus: {mode}]  (format=beliebiger Fall · all=Waldweg-Selbsttest)")
    gates = ["validate_ios.py", "validate_android.py", "validate_windows.py", "validate_apps.py"]
    # verify_solution prueft die WALDWEG-Loesung -> nur im 'all'-Modus + Vollfall
    full = all(os.path.isdir(os.path.join(root, d)) and os.listdir(os.path.join(root, d))
               for d in ("01_ios_full_fs", "02_android_full_fs", "03_windows_triage"))
    if full and mode == "all":
        gates.append("verify_solution.py")
    ok = True
    for g in gates:
        print(f"----- {g} -----")
        rc = subprocess.run([sys.executable, os.path.join(GEN, g)], env=env).returncode
        if rc == 2:
            print(f"  [SKIP] {g} (Artefakte fuer diese Plattform nicht im Fall)")
        elif rc != 0:
            ok = False
    if mode == "all" and not full:
        print("  [HINWEIS] Teilfall — verify_solution (Lösbarkeit) nur bei Vollfall.")
    elif mode == "format":
        print("  [HINWEIS] Format-Modus: nur Schema/Parsebarkeit geprüft (Inhalte spec-spezifisch).")
    print("VALIDATE:", "OK" if ok else "FEHLER")
    sys.exit(0 if ok else 1)


def cmd_run(args):
    env = _env(case_dir(args), os.path.join(case_dir(args), "case_master.yaml"))
    sys.exit(subprocess.run([sys.executable, os.path.join(GEN, "run_all.py")], env=env).returncode)


def main():
    ap = argparse.ArgumentParser(prog="forge", description="CaseForge — synthetische Forensik-Faelle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("catalog").set_defaults(func=cmd_catalog)
    p = sub.add_parser("propose"); p.set_defaults(func=cmd_propose)
    p.add_argument("--backend", choices=["cowork", "ollama"], default="cowork")
    p.add_argument("--model", default="qwen2.5:32b-instruct")
    p.add_argument("--input"); p.add_argument("--delikt"); p.add_argument("--lernziel"); p.add_argument("--assets", type=int)
    p.add_argument("--lang", help="Ausgabesprache des Fall-Vorschlags (de|en|fr|es|tr | Locale wie en-US)")
    p.add_argument("--url", default="http://localhost:11434", help="ollama-Server-URL")
    p.add_argument("--timeout", type=int, default=1800, help="ollama Read-Timeout pro Chunk (Sekunden)")
    i = sub.add_parser("init"); i.set_defaults(func=cmd_init)
    i.add_argument("--name", required=True); i.add_argument("--from", dest="frm")
    for name, fn in (("build", cmd_build), ("validate", cmd_validate), ("run", cmd_run)):
        q = sub.add_parser(name); q.set_defaults(func=fn)
        q.add_argument("--case"); q.add_argument("--root", default=ROOT)
        if name == "build":
            q.add_argument("--spec"); q.add_argument("--platform", nargs="*")
        if name == "validate":
            q.add_argument("--mode", choices=["all", "format", "reference"],
                           help="Gate-Modus erzwingen (Default: auto)")
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
