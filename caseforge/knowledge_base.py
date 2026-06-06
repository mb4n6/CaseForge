#!/usr/bin/env python3
# =====================================================================
# CaseForge — Wissensbasis forensischer Problemstellungen
# ---------------------------------------------------------------------
# Verwaltet den Fundus kuratierter "Problemstellungen" (knowledge/problems/*.yaml):
# Laden, Schema-Validierung, Filtern/Indizieren, deterministisches Matching
# (Lernziel/Delikt -> Vorschlag), Prompt-Zusammenfassung sowie den Anlern-
# Workflow (Freitext-Entwurf ablegen -> menschliche Freigabe -> nach problems/).
#
# Leitidee (Mensch+KI-Expertensystem):
#   * Menschen kuratieren/approven Wissen (problems/, status: approved).
#   * Das LLM hilft beim ANLERNEN (Freitext -> strukturierter Entwurf) und beim
#     ANWENDEN (Auswahl/Verweben der Problemstellungen in neue Faelle).
#   * Determinismus & Tool-Validierung der Faelle bleiben unberuehrt: die
#     Wissensbasis steuert nur, WELCHE Artefaktklassen/Widersprueche ein Fall traegt.
#
# CLI:
#   python3 knowledge_base.py list [--category C] [--platform P] [--status S]
#   python3 knowledge_base.py show <id>
#   python3 knowledge_base.py match "<freitext>" [--platform ios,android] [-k 5]
#   python3 knowledge_base.py validate            (alle Eintraege gegen Schema)
#   python3 knowledge_base.py drafts              (Entwuerfe in incoming/)
#   python3 knowledge_base.py approve <id> [--by NAME]
# =====================================================================
import argparse
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("PyYAML fehlt — pip install pyyaml --break-system-packages")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.join(HERE, "knowledge")
PROBLEMS = os.path.join(KDIR, "problems")
INCOMING = os.path.join(KDIR, "incoming")
SCHEMA = os.path.join(KDIR, "schema", "problem.schema.json")
TAXONOMY = os.path.join(KDIR, "taxonomy.yaml")

CATEGORIES = ("computer_forensics", "mobile_forensics", "app_analysis")
PLATFORMS = ("ios", "android", "windows", "cloud", "crossdevice")
DIFFICULTY = ("basic", "intermediate", "advanced")
STATUS = ("draft", "approved", "deprecated")
_REQUIRED = ("id", "title", "category", "platforms", "difficulty",
             "learning_objective", "description", "artifact_classes", "provenance")


# ---------------------------------------------------------------- laden
def _load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_taxonomy():
    return _load_yaml(TAXONOMY) if os.path.exists(TAXONOMY) else {}


def _load_dir(path):
    out = []
    for p in sorted(glob.glob(os.path.join(path, "*.yaml")) +
                    glob.glob(os.path.join(path, "*.yml"))):
        try:
            e = _load_yaml(p)
            if isinstance(e, dict):
                e["_path"] = p
                out.append(e)
        except Exception as ex:
            print(f"[WARN] {os.path.basename(p)}: {ex}", file=sys.stderr)
    return out


def load_all(include_drafts=False):
    """Alle Problemstellungen. approved aus problems/, optional drafts aus incoming/."""
    items = _load_dir(PROBLEMS)
    if include_drafts:
        items += _load_dir(INCOMING)
    # nach id eindeutig (problems/ hat Vorrang vor incoming/)
    seen, uniq = set(), []
    for e in items:
        i = e.get("id")
        if i and i not in seen:
            seen.add(i); uniq.append(e)
    return uniq


def approved():
    return [e for e in load_all() if (e.get("provenance") or {}).get("status") == "approved"]


def get(pid, include_drafts=True):
    for e in load_all(include_drafts=include_drafts):
        if e.get("id") == pid:
            return e
    return None


def get_many(ids):
    idx = {e["id"]: e for e in load_all(include_drafts=True) if e.get("id")}
    return [idx[i] for i in ids if i in idx]


# ----------------------------------------------------------- validierung
def _validate_jsonschema(entry):
    """Vollvalidierung, falls 'jsonschema' installiert ist (sonst None)."""
    try:
        import json
        import jsonschema
    except Exception:
        return None
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    e = {k: v for k, v in entry.items() if k != "_path"}
    try:
        jsonschema.validate(e, schema)
        return []
    except jsonschema.ValidationError as ex:
        return [f"{'/'.join(str(p) for p in ex.path)}: {ex.message}"]


def _validate_light(entry):
    """Schlanke Eigenvalidierung ohne externe Abhaengigkeit."""
    errs = []
    for k in _REQUIRED:
        if not entry.get(k):
            errs.append(f"Pflichtfeld fehlt: {k}")
    cid = entry.get("id", "")
    if cid and not re.fullmatch(r"[a-z0-9]+(?:[_-][a-z0-9]+)*", cid):
        errs.append(f"id-Format ungueltig: {cid!r}")
    if entry.get("category") and entry["category"] not in CATEGORIES:
        errs.append(f"category unbekannt: {entry['category']}")
    if entry.get("difficulty") and entry["difficulty"] not in DIFFICULTY:
        errs.append(f"difficulty unbekannt: {entry['difficulty']}")
    for p in entry.get("platforms", []) or []:
        if p not in PLATFORMS:
            errs.append(f"platform unbekannt: {p}")
    prov = entry.get("provenance") or {}
    if prov.get("status") and prov["status"] not in STATUS:
        errs.append(f"provenance.status unbekannt: {prov['status']}")
    if prov.get("source") and prov["source"] not in ("expert", "llm_extracted", "llm_extracted_reviewed"):
        errs.append(f"provenance.source unbekannt: {prov['source']}")
    return errs


def validate_entry(entry):
    """Gibt Liste von Fehlermeldungen zurueck ([] = ok). Nutzt jsonschema, sonst light."""
    js = _validate_jsonschema(entry)
    return js if js is not None else _validate_light(entry)


def validate_all(include_drafts=True):
    rep = {}
    for e in load_all(include_drafts=include_drafts):
        rep[e.get("id", e.get("_path"))] = validate_entry(e)
    return rep


# --------------------------------------------------------------- filter
def filter_entries(items=None, category=None, platform=None, difficulty=None,
                   subdomain=None, status="approved"):
    items = items if items is not None else load_all(include_drafts=(status != "approved"))
    out = []
    for e in items:
        prov = e.get("provenance") or {}
        if status and prov.get("status") != status:
            continue
        if category and e.get("category") != category:
            continue
        if platform and platform not in (e.get("platforms") or []):
            continue
        if difficulty and e.get("difficulty") != difficulty:
            continue
        if subdomain and subdomain not in (e.get("subdomains") or []):
            continue
        out.append(e)
    return out


# -------------------------------------------------------------- matching
_DELIKT_HINTS = {
    "stalking": ["location", "messaging", "cloud_sync"],
    "betrug": ["messaging", "browser", "app_schema"],
    "scam": ["messaging", "browser", "app_schema"],
    "toetung": ["location", "timeline", "messaging"],
    "mord": ["location", "timeline", "messaging"],
    "btm": ["messaging", "location", "encryption"],
    "drogen": ["messaging", "location", "encryption"],
    "exfiltration": ["usb_exfiltration", "filesystem", "registry"],
    "diebstahl": ["usb_exfiltration", "filesystem"],
    "einbruch": ["location", "timeline"],
}


def _tokens(*parts):
    txt = " ".join(p for p in parts if p).lower()
    return set(re.findall(r"[a-z0-9]{3,}", txt))


def _entry_tokens(e):
    return _tokens(
        e.get("title", ""), e.get("learning_objective", ""),
        e.get("description", ""), e.get("category", ""),
        " ".join(e.get("subdomains", []) or []),
        " ".join(e.get("artifact_classes", []) or []),
        " ".join(e.get("registry_refs", []) or []),
    )


def match(text="", platforms=None, category=None, k=5, items=None):
    """Deterministisches Ranking: Token-Overlap + Plattform-/Delikt-/Kategorie-Bonus.

    Liefert Liste von (entry, score), score>0, stabil nach (-score, id) sortiert.
    Reines Python, keine LLM-Abhaengigkeit -> auch offline nutzbar.
    """
    cand = filter_entries(items=items, category=category, status="approved")
    if platforms:
        pset = set(platforms)
        cand = [e for e in cand
                if pset & set(e.get("platforms", [])) or "crossdevice" in (e.get("platforms") or [])]
    q = _tokens(text)
    # Delikt-Hinweise erweitern die Query um passende Subdomains
    extra = set()
    low = (text or "").lower()
    for key, subs in _DELIKT_HINTS.items():
        if key in low:
            extra.update(subs)
    scored = []
    for e in cand:
        et = _entry_tokens(e)
        score = len(q & et)
        if extra & set(e.get("subdomains", []) or []):
            score += 2 * len(extra & set(e.get("subdomains", [])))
        if platforms and set(platforms) & set(e.get("platforms", [])):
            score += 1
        if score > 0:
            scored.append((e, score))
    scored.sort(key=lambda x: (-x[1], x[0].get("id", "")))
    return scored[:k] if k else scored


# ----------------------------------------------------- prompt-summary
def summary_for_prompt(items=None, status="approved"):
    """Kompakter Katalog fuer den LLM-Prompt (eine Zeile je Problemstellung)."""
    items = items if items is not None else filter_entries(status=status)
    lines = []
    for e in items:
        plats = ",".join(e.get("platforms", []) or [])
        cls = ",".join(e.get("artifact_classes", []) or [])
        lines.append(f"- {e['id']} [{e.get('category')}/{plats}/{e.get('difficulty')}] "
                     f"{e.get('title')} | Lernziel: {e.get('learning_objective','').strip()} "
                     f"| Klassen: {cls}")
    return "\n".join(lines)


def case_hook_digest(ids):
    """Fuer Build/Report: gewaehlte Problemstellungen -> aktivierbare Klassen +
    Widerspruchs-Vorlagen + Loesungswege (Dozentenwissen)."""
    out = {"enable_artifact_classes": [], "planted": [], "detection": [], "selected": []}
    for e in get_many(ids):
        out["selected"].append({"id": e["id"], "title": e.get("title", "")})
        hooks = e.get("case_hooks", {}) or {}
        for c in hooks.get("enable_artifact_classes", []) or []:
            if c not in out["enable_artifact_classes"]:
                out["enable_artifact_classes"].append(c)
        pi = hooks.get("planted_inconsistency")
        if pi:
            out["planted"].append({"id": e["id"], **pi})
        if e.get("detection_method"):
            out["detection"].append({"id": e["id"], "title": e.get("title", ""),
                                     "method": e["detection_method"],
                                     "pitfalls": e.get("pitfalls", [])})
    return out


# --------------------------------------------------------- anlern-workflow
def _slugify(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "problemstellung"


def save_draft(entry, filename=None):
    """Schreibt einen Entwurf nach incoming/ (status: draft)."""
    os.makedirs(INCOMING, exist_ok=True)
    entry.setdefault("provenance", {})
    entry["provenance"].setdefault("source", "llm_extracted")
    entry["provenance"]["status"] = "draft"
    pid = entry.get("id") or _slugify(entry.get("title"))
    entry["id"] = pid
    fn = filename or f"{pid}.draft.yaml"
    out = os.path.join(INCOMING, fn)
    entry.pop("_path", None)
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(entry, f, allow_unicode=True, sort_keys=False, width=100)
    return out


def list_drafts():
    return _load_dir(INCOMING)


def approve(pid, by=None):
    """Hebt einen Entwurf nach problems/ (status: approved) — menschliche Freigabe."""
    draft = None
    for e in list_drafts():
        if e.get("id") == pid:
            draft = e; break
    if not draft:
        raise SystemExit(f"Kein Entwurf mit id '{pid}' in {INCOMING}")
    errs = validate_entry(draft)
    if errs:
        raise SystemExit("Freigabe abgelehnt — Schema-Fehler:\n  - " + "\n  - ".join(errs))
    prov = draft.setdefault("provenance", {})
    prov["status"] = "approved"
    if prov.get("source") == "llm_extracted":
        prov["source"] = "llm_extracted_reviewed"
    if by:
        prov["reviewed_by"] = by
    src_path = draft.pop("_path", None)
    os.makedirs(PROBLEMS, exist_ok=True)
    dst = os.path.join(PROBLEMS, f"{pid}.yaml")
    with open(dst, "w", encoding="utf-8") as f:
        yaml.safe_dump(draft, f, allow_unicode=True, sort_keys=False, width=100)
    if src_path and os.path.exists(src_path):
        try:
            os.remove(src_path)
        except OSError as ex:
            print(f"[WARN] Entwurf konnte nicht entfernt werden ({ex}); "
                  f"bitte manuell loeschen: {src_path}", file=sys.stderr)
    return dst


# ----------------------------------------------------------------- CLI
def _cli():
    ap = argparse.ArgumentParser(description="CaseForge Wissensbasis (Problemstellungen)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list")
    pl.add_argument("--category", choices=CATEGORIES)
    pl.add_argument("--platform", choices=PLATFORMS)
    pl.add_argument("--difficulty", choices=DIFFICULTY)
    pl.add_argument("--status", default="approved")

    ps = sub.add_parser("show"); ps.add_argument("id")

    pm = sub.add_parser("match"); pm.add_argument("text")
    pm.add_argument("--platform", help="Komma-Liste, z.B. ios,android")
    pm.add_argument("--category", choices=CATEGORIES)
    pm.add_argument("-k", type=int, default=5)

    sub.add_parser("validate")
    sub.add_parser("drafts")
    pa = sub.add_parser("approve"); pa.add_argument("id"); pa.add_argument("--by")
    args = ap.parse_args()

    if args.cmd == "list":
        items = filter_entries(category=args.category, platform=args.platform,
                               difficulty=args.difficulty, status=args.status)
        print(f"{len(items)} Problemstellungen ({args.status}):\n")
        print(summary_for_prompt(items, status=args.status) or "  (keine)")
    elif args.cmd == "show":
        e = get(args.id)
        if not e:
            raise SystemExit(f"Nicht gefunden: {args.id}")
        e.pop("_path", None)
        print(yaml.safe_dump(e, allow_unicode=True, sort_keys=False, width=100))
    elif args.cmd == "match":
        plats = args.platform.split(",") if args.platform else None
        res = match(args.text, platforms=plats, category=args.category, k=args.k)
        if not res:
            print("Keine passende Problemstellung gefunden."); return
        print(f"Top {len(res)} Treffer fuer: {args.text!r}\n")
        for e, sc in res:
            print(f"  [{sc:>2}] {e['id']:<34} {e.get('title')}")
    elif args.cmd == "validate":
        rep = validate_all()
        bad = {k: v for k, v in rep.items() if v}
        for k, v in rep.items():
            print(f"  {'OK ' if not v else 'ERR'} {k}")
            for msg in v:
                print(f"        - {msg}")
        print(f"\n{len(rep) - len(bad)}/{len(rep)} valide.")
        sys.exit(1 if bad else 0)
    elif args.cmd == "drafts":
        ds = list_drafts()
        print(f"{len(ds)} Entwuerfe in incoming/:")
        for e in ds:
            print(f"  - {e.get('id')}  ({(e.get('provenance') or {}).get('source','?')})")
    elif args.cmd == "approve":
        dst = approve(args.id, by=args.by)
        print(f"Freigegeben -> {os.path.relpath(dst, HERE)}")


if __name__ == "__main__":
    _cli()
