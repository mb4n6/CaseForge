#!/usr/bin/env python3
# =====================================================================
# gen_report.py  —  Auto-Report je Fall (Markdown)
# ---------------------------------------------------------------------
# Erzeugt aus dem aktiven case_master.yaml (WALDWEG_CASE_MASTER) + ggf.
# vorhandenem Artefakt-Katalog einen Fall-Report:
#   * Aufgabenstellung / Eckdaten (Delikt, Lernziel, Sprache, Umfang, Seed)
#   * Asservate (Geraete + OS-Profile + versionstypische Artefakt-Flags)
#   * Personen / Timeline (mit Relevanz)
#   * Geplante Widersprueche + Loesungsschluessel (Dozenten-Teil)
#   * Artefaktuebersicht (aus 06_master/Artefakt_Katalog.csv, falls vorhanden)
# Ziel: <root>/06_master/Fall_Report.md
# =====================================================================
import os
import sys
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_master_io as cmio

ROOT_ENV = os.environ.get("WALDWEG_OW")           # Fall-Root (von forge gesetzt)


def _problem_digest(ids):
    """Laedt Loesungswege der gewaehlten Problemstellungen aus der Wissensbasis."""
    try:
        sys.path.insert(0, os.path.dirname(HERE))  # caseforge/ (Elternverzeichnis)
        import knowledge_base as kb
    except Exception:
        return []
    out = []
    for e in kb.get_many(ids):
        out.append({"id": e.get("id"), "title": e.get("title", e.get("id")),
                    "learning_objective": e.get("learning_objective", ""),
                    "method": e.get("detection_method", ""),
                    "pitfalls": e.get("pitfalls", [])})
    return out


def _root():
    if ROOT_ENV:
        return ROOT_ENV
    mp = cmio.master_path()
    return os.path.dirname(mp)


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def build_report(cm):
    meta = cm.get("meta", {}) or {}
    L = []
    L.append(f"# Fall-Report: {meta.get('case_name', '(unbenannt)')}")
    L.append("")
    L.append("> **Synthetischer Trainingsfall — `synthetic_training_data_only`.** "
             "Automatisch von CaseForge erzeugt.")
    L.append("")
    L.append("## 1. Eckdaten")
    L.append("")
    eck = [
        ("Deliktart", meta.get("deliktart", "—")),
        ("Lernziel", meta.get("lernziel", "—")),
        ("Sprache", meta.get("language_primary", "de-DE")),
        ("Fallumfang (scope)", meta.get("scope", "M")),
        ("generator_seed", meta.get("generator_seed", "—")),
        ("Fokusfenster", f"{(meta.get('focus_window') or {}).get('start','?')} – "
                         f"{(meta.get('focus_window') or {}).get('end','?')}"),
    ]
    L.append(_table(["Feld", "Wert"], eck))

    # ---- Asservate / Geraete ----
    L.append("\n## 2. Asservate (Geraete)\n")
    drows = []
    for d in cm.get("devices", []):
        ov = d.get("overrides", {}) or {}
        flags = ", ".join(f"{k}={v}" for k, v in ov.items()) if ov else "—"
        drows.append((d.get("id"), d.get("owner"), d.get("type"),
                      d.get("os_version", "?"), d.get("os_profile", "—"), flags))
    L.append(_table(["id", "Besitzer", "Typ", "OS", "Profil", "Profil-Flags"], drows) if drows else "_keine_")

    # ---- Personen ----
    L.append("\n## 3. Personen\n")
    prows = [(p.get("id"), p.get("name"), p.get("role", "—"), p.get("phone", "—"))
             for p in cm.get("persons", [])]
    L.append(_table(["id", "Name", "Rolle", "Telefon"], prows) if prows else "_keine_")

    # ---- Timeline ----
    L.append("\n## 4. Timeline\n")
    tl = sorted(cm.get("timeline", []), key=lambda e: e.get("t", ""))
    trows = [(e.get("t"), e.get("actor", "—"), e.get("type", "—"),
              e.get("relevance", "—"), (e.get("content", "") or "")[:70]) for e in tl]
    L.append(_table(["Zeit", "Akteur", "Typ", "Relevanz", "Inhalt"], trows) if trows else "_leer_")

    # ---- Artefaktuebersicht (aus Katalog-CSV) ----
    cat = os.path.join(_root(), "06_master", "Artefakt_Katalog.csv")
    if os.path.exists(cat):
        L.append("\n## 5. Artefaktuebersicht (Katalog)\n")
        with open(cat, encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if rows:
            head, body = rows[0], rows[1:]
            L.append(_table(head, body[:60]))
            if len(body) > 60:
                L.append(f"\n_… {len(body) - 60} weitere Eintraege im Katalog._")

    # ---- Dozenten-Teil: Forensische Problemstellungen (Wissensbasis) ----
    fp = meta.get("forensic_problems") or []
    if fp:
        L.append("\n## 6. Forensische Problemstellungen & Loesungswege (Dozent)\n")
        L.append("_Aus der CaseForge-Wissensbasis eingewoben — kuratiertes Expertenwissen._\n")
        dig = _problem_digest(fp)
        if dig:
            for d in dig:
                L.append(f"### {d['title']}  `({d['id']})`")
                if d.get("learning_objective"):
                    L.append(f"- **Lernziel:** {d['learning_objective']}")
                if d.get("method"):
                    L.append(f"- **Loesungsweg:** {d['method']}")
                for pit in d.get("pitfalls", []) or []:
                    L.append(f"  - _Fallstrick:_ {pit}")
                L.append("")
        else:
            L.append("- " + ", ".join(fp))

    # ---- Dozenten-Teil: Widersprueche + Loesung ----
    pi = cm.get("planted_inconsistencies", [])
    if pi:
        L.append("\n## 7. Geplante Widersprueche (Dozent)\n")
        for x in pi:
            if isinstance(x, dict):
                L.append(f"- **{x.get('title', x.get('id', '?'))}** — {x.get('detail', '')} "
                         f"_(Status: {x.get('status', '?')})_")
            else:
                L.append(f"- {x}")
    sk = cm.get("solution_key")
    if sk:
        L.append("\n## 8. Loesungsschluessel (Dozent)\n")
        if isinstance(sk, dict):
            for k, v in sk.items():
                L.append(f"- **{k}:** {v}")
        else:
            L.append(str(sk))

    L.append("\n---\n")
    L.append("_CaseForge Auto-Report. Dozenten-Abschnitte (6/7/8) vor Weitergabe an "
             "Studierende entfernen._")
    return "\n".join(L) + "\n"


def main():
    cm = cmio.load_master()
    if not cm:
        print("[report] kein case_master gefunden — uebersprungen.")
        return
    out_dir = os.path.join(_root(), "06_master")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Fall_Report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build_report(cm))
    print(f"Fall-Report erzeugt: {os.path.relpath(out, _root())}")


if __name__ == "__main__":
    main()
