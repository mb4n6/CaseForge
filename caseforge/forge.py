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

HERE = os.path.dirname(os.path.abspath(__file__))   # caseforge/
REPO = os.path.dirname(HERE)                          # Repo-Wurzel
GEN = os.path.join(HERE, "generators")
# Beispiel-/Referenzfall "Operation Waldweg" liegt unter examples/
ROOT = os.path.join(REPO, "examples", "operation_waldweg")
REF_MASTER = os.path.join(ROOT, "case_master.yaml")
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
        seed = _master_value(case_master, "generator_seed")
        if seed is not None:
            e["WALDWEG_GENERATOR_SEED"] = str(seed)
    return e


def _master_value(master, key):
    """Liest meta.<key> aus einem case_master.yaml (oder None)."""
    try:
        import yaml
        cm = yaml.safe_load(open(master, encoding="utf-8")) if os.path.exists(master) else {}
        return (cm.get("meta", {}) or {}).get(key)
    except Exception:
        return None


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
    # Problemstellungs-Auswahl (Wissensbasis): auto | match | none | id1,id2,...
    probsel = getattr(args, "problems", None) or ui.get("problems")
    if probsel == "match":
        import knowledge_base as kb
        text = f"{ui.get('deliktart','')} {ui.get('lernziel','')}"
        plats = [d.get("platform") for d in ui.get("devices", []) if d.get("platform")] or None
        ids = [e["id"] for e, _ in kb.match(text, platforms=plats, k=4)]
        ui["problems"] = ids
        print(f"[Problemstellungen (match)]: {', '.join(ids) or '(keine)'}")
    elif probsel and probsel not in ("auto", "none"):
        ui["problems"] = [s.strip() for s in str(probsel).split(",") if s.strip()]
        print(f"[Problemstellungen (fix)]: {', '.join(ui['problems'])}")
    elif probsel:
        ui["problems"] = probsel
        if probsel == "auto":
            print("[Problemstellungen: auto — LLM waehlt aus der Wissensbasis]")
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


def _parse_yaml_block(raw):
    """Extrahiert ein YAML-Dokument aus LLM-Rohtext (toleriert Code-Zaeune/Vorspann)."""
    import yaml
    txt = raw.strip()
    if "```" in txt:  # Code-Zaeune entfernen
        parts = txt.split("```")
        # nimm den laengsten Block, der wie YAML aussieht
        cand = max(parts, key=len)
        txt = cand.lstrip()
        if txt.lower().startswith(("yaml", "yml")):
            txt = txt.split("\n", 1)[1] if "\n" in txt else txt
    try:
        obj = yaml.safe_load(txt)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def cmd_teach(args):
    """Anlernen einer Problemstellung: Freitext -> LLM-Struktur -> menschliche Freigabe."""
    import knowledge_base as kb
    if args.approve:
        print(f"Freigegeben -> {kb.approve(args.approve, by=getattr(args, 'by', None))}")
        return
    if args.list_drafts:
        ds = kb.list_drafts()
        print(f"{len(ds)} Entwuerfe (knowledge/incoming/):")
        for e in ds:
            pv = e.get("provenance", {}) or {}
            print(f"  - {e.get('id')}  ({pv.get('source','?')}/{pv.get('status','?')})")
        return
    if not args.input:
        print("Bitte --input <freitext.txt> angeben  (oder --list-drafts / --approve <id>)."); sys.exit(1)
    import llm
    freetext = open(args.input, encoding="utf-8").read()
    prompt = llm.build_teach_prompt(freetext)
    outdir = os.path.join(HERE, "out"); os.makedirs(outdir, exist_ok=True)
    if args.backend == "ollama":
        url = getattr(args, "url", None) or "http://localhost:11434"
        to = getattr(args, "timeout", None) or 1800
        print(f"[ollama] {args.model} @ {url} (Wissens-Extraktion) ...")
        raw = llm.propose_ollama(prompt, model=args.model, url=url, timeout=to)
        entry = _parse_yaml_block(raw)
        if not entry:
            p = os.path.join(outdir, "teach_raw.txt"); open(p, "w", encoding="utf-8").write(raw)
            print(f"Kein YAML parsebar -> {p} (manuell nach knowledge/incoming/ uebernehmen)."); sys.exit(1)
        path = kb.save_draft(entry)
        errs = kb.validate_entry(entry)
        print(f"Entwurf abgelegt -> {os.path.relpath(path, HERE)}")
        if errs:
            print("  [WARN] Schema-Hinweise (vor Freigabe beheben):")
            for e in errs:
                print(f"    - {e}")
        print(f"Pruefen, dann freigeben:  forge.py teach --approve {entry.get('id')}")
    else:
        p = os.path.join(outdir, "teach_prompt.md")
        open(p, "w", encoding="utf-8").write(prompt)
        print(f"[cowork] Teach-Prompt-Bundle geschrieben: {p}\n"
              "In Claude Cowork ausfuehren -> YAML-Antwort als "
              "knowledge/incoming/<id>.draft.yaml speichern, dann 'forge.py teach --approve <id>'.")


def cmd_problems(args):
    """Wissensbasis durchsuchen/anzeigen (manuelle Auswahl unterstuetzen)."""
    import knowledge_base as kb
    if args.show:
        e = kb.get(args.show)
        if not e:
            print(f"Nicht gefunden: {args.show}"); sys.exit(1)
        import yaml as _y; e.pop("_path", None)
        print(_y.safe_dump(e, allow_unicode=True, sort_keys=False, width=100)); return
    if args.match:
        plats = args.platform.split(",") if args.platform else None
        res = kb.match(args.match, platforms=plats, category=args.category, k=args.k)
        print(f"Top {len(res)} fuer {args.match!r}:")
        for e, sc in res:
            print(f"  [{sc:>2}] {e['id']:<34} {e.get('title')}")
        return
    items = kb.filter_entries(category=args.category, platform=args.platform, status="approved")
    print(f"{len(items)} Problemstellungen (approved):\n")
    print(kb.summary_for_prompt(items) or "  (keine)")


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


def _patch_master_meta(master, seed=None, scope=None):
    """Schreibt --seed/--scope in meta des Fall-Masters (idempotent)."""
    try:
        import yaml
        cm = yaml.safe_load(open(master, encoding="utf-8")) or {}
        meta = cm.setdefault("meta", {})
        if seed is not None:
            meta["generator_seed"] = seed
        if scope is not None:
            meta["scope"] = scope
        with open(master, "w", encoding="utf-8") as f:
            yaml.safe_dump(cm, f, allow_unicode=True, sort_keys=False, width=100)
    except Exception as e:
        print(f"[WARN] meta-Patch fehlgeschlagen: {e}")


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
    # CLI-Overrides (--seed/--scope) in den Fall-Master schreiben (nur Fall-Master, nicht REF)
    if (getattr(args, "seed", None) or getattr(args, "scope", None)) and master != REF_MASTER:
        _patch_master_meta(master, seed=getattr(args, "seed", None), scope=getattr(args, "scope", None))
    # Wissensbasis: gewaehlte Problemstellungen aktivieren ihre Artefaktklassen
    # auf bereits eingeschraenkten Geraeten (Slim-/Teilfaelle bleiben vollstaendig).
    if spec and spec.get("forensic_problems"):
        try:
            import knowledge_base as kb
            enable = kb.case_hook_digest(spec["forensic_problems"]).get("enable_artifact_classes", [])
            for d in spec.get("devices", []):
                if d.get("artifact_classes"):
                    d["artifact_classes"] = sorted(set(d["artifact_classes"]) | set(enable))
        except Exception as e:
            print(f"[WARN] Problemstellungs-Klassen nicht angewandt: {e}")
    mods = _modules_for(spec, args.platform)
    env = _env(root, master)
    print(f"Build -> {root}\ncase_master: {master}\nGeneratoren ({len(mods)}): {', '.join(m[:-3] for m in mods)}")
    ok = all(_run(m, env) for m in mods)
    # Per-Fall-Katalog
    subprocess.run([sys.executable, os.path.join(HERE, "catalog.py"),
                    "--out", os.path.join(root, "06_master", "Artefakt_Katalog.md"),
                    "--csv", os.path.join(root, "06_master", "Artefakt_Katalog.csv")])
    # Auto-Report je Fall
    subprocess.run([sys.executable, os.path.join(GEN, "gen_report.py")], env=env)
    print("BUILD:", "OK" if ok else "FEHLER")
    sys.exit(0 if ok else 1)


def cmd_report(args):
    root = case_dir(args)
    master = os.path.join(root, "case_master.yaml")
    master = master if os.path.exists(master) else REF_MASTER
    env = _env(root, master)
    subprocess.run([sys.executable, os.path.join(GEN, "gen_report.py")], env=env)


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
    p.add_argument("--problems", help="Problemstellungen aus der Wissensbasis: 'auto' (LLM waehlt), "
                                      "'match' (deterministisch nach Delikt/Lernziel), 'none', oder id1,id2,...")
    p.add_argument("--url", default="http://localhost:11434", help="ollama-Server-URL")
    p.add_argument("--timeout", type=int, default=1800, help="ollama Read-Timeout pro Chunk (Sekunden)")

    # ---- teach: Problemstellung anlernen (Freitext -> LLM -> Freigabe) ----
    t = sub.add_parser("teach"); t.set_defaults(func=cmd_teach)
    t.add_argument("--input", help="Freitext-Datei eines Experten (zu strukturieren)")
    t.add_argument("--backend", choices=["cowork", "ollama"], default="cowork")
    t.add_argument("--model", default="qwen2.5:32b-instruct")
    t.add_argument("--url", default="http://localhost:11434")
    t.add_argument("--timeout", type=int, default=1800)
    t.add_argument("--list-drafts", dest="list_drafts", action="store_true", help="Entwuerfe in incoming/ zeigen")
    t.add_argument("--approve", help="Entwurf <id> freigeben -> nach knowledge/problems/")
    t.add_argument("--by", help="Name der freigebenden Person (provenance.reviewed_by)")

    # ---- problems: Wissensbasis durchsuchen ----
    pr = sub.add_parser("problems"); pr.set_defaults(func=cmd_problems)
    pr.add_argument("--show", help="eine Problemstellung im Detail (id)")
    pr.add_argument("--match", help="Freitext -> Ranking passender Problemstellungen")
    pr.add_argument("--platform", help="Filter/Match-Plattform(en), Komma-Liste")
    pr.add_argument("--category", choices=["computer_forensics", "mobile_forensics", "app_analysis"])
    pr.add_argument("-k", type=int, default=5)

    i = sub.add_parser("init"); i.set_defaults(func=cmd_init)
    i.add_argument("--name", required=True); i.add_argument("--from", dest="frm")
    for name, fn in (("build", cmd_build), ("validate", cmd_validate), ("run", cmd_run),
                     ("report", cmd_report)):
        q = sub.add_parser(name); q.set_defaults(func=fn)
        q.add_argument("--case"); q.add_argument("--root", default=ROOT)
        if name == "build":
            q.add_argument("--spec"); q.add_argument("--platform", nargs="*")
            q.add_argument("--seed", type=int, help="generator_seed erzwingen (Reproduzierbarkeit/Variation)")
            q.add_argument("--scope", choices=["S", "M", "L", "XL"], help="Fallumfang (Noise-Menge)")
        if name == "validate":
            q.add_argument("--mode", choices=["all", "format", "reference"],
                           help="Gate-Modus erzwingen (Default: auto)")
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
