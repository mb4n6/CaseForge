#!/usr/bin/env python3
# =====================================================================
# CaseForge — Artefakt-Katalog / Uebersicht
# ---------------------------------------------------------------------
# Erzeugt aus der Registry (+ optional einem Case-Spec) die Uebersicht
# der enthaltenen digitalen Artefakte pro GERAET / PLATTFORM / OS inkl.
# Format und FORENSIK-TOOL zur Gegenpruefung. Ausgabe als Markdown + CSV.
#
#   python3 catalog.py                 # Katalog des Referenz-Falls
#   python3 catalog.py --spec case.yaml  # Katalog fuer einen Case-Spec
# =====================================================================
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import registry as R

PLATFORMS = ["ios", "android", "windows", "cloud", "crossdevice"]
PLAT_LABEL = {"ios": "iOS (iPhone)", "android": "Android (Samsung)",
              "windows": "Windows (Notebook)", "cloud": "Cloud", "crossdevice": "Geraeteuebergreifend"}


def build_catalog(selected_classes=None, os_versions=None):
    rows = []
    for g in R.REGISTRY:
        if selected_classes and not (set(g.artifact_classes) & set(selected_classes)):
            continue
        osv = (os_versions or {}).get(g.platform, g.os_min)
        rows.append({
            "platform": g.platform, "os": osv, "id": g.id,
            "artifact_classes": ", ".join(g.artifact_classes),
            "format": g.fmt, "parser": g.parser, "generator": g.module,
            "validator": g.validator or "—",
            "produces": " ; ".join(g.produces),
            "relevance": "ja" if g.relevance_capable else "—", "notes": g.notes,
        })
    return rows


def to_markdown(rows, title="Artefakt-Katalog"):
    out = [f"# {title}\n", "> Generiert von CaseForge aus der Generator-Registry.\n"]
    for plat in PLATFORMS:
        prs = [r for r in rows if r["platform"] == plat]
        if not prs:
            continue
        out.append(f"\n## {PLAT_LABEL[plat]}\n")
        out.append("| Artefaktklasse | Format | Pfade | Forensik-Tool (Gegenpruefung) | Generator |")
        out.append("|---|---|---|---|---|")
        for r in prs:
            out.append(f"| {r['artifact_classes']} | {r['format']} | {r['produces']} | {r['parser']} | `{r['generator']}` |")
    # Tool-Uebersicht
    out.append("\n## Forensik-Tools zur Gegenpruefung\n")
    for p in R.parsers():
        out.append(f"- {p}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    _ex = os.path.join(HERE, "..", "examples", "operation_waldweg", "06_master")
    ap.add_argument("--out", default=os.path.join(_ex, "Artefakt_Katalog.md"))
    ap.add_argument("--csv", default=os.path.join(_ex, "Artefakt_Katalog.csv"))
    ap.add_argument("--classes", nargs="*", help="nur diese Artefaktklassen")
    args = ap.parse_args()

    rows = build_catalog(selected_classes=args.classes)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(to_markdown(rows))
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"Katalog: {os.path.normpath(args.out)} ({len(rows)} Generatoren)")
    print(f"CSV:     {os.path.normpath(args.csv)}")
    print(f"Plattformen: {sorted({r['platform'] for r in rows})}")
    print(f"Artefaktklassen: {R.artifact_classes()}")


if __name__ == "__main__":
    main()
