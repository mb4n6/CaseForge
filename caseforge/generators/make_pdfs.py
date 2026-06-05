#!/usr/bin/env python3
# =====================================================================
# make_pdfs.py  —  Markdown-Deliverables -> formatierte PDFs
# ---------------------------------------------------------------------
# Konvertiert die Dozenten-/Studierenden-Dokumente aus 06_master nach PDF
# (markdown -> HTML -> WeasyPrint) mit einem schlichten Druck-Stylesheet.
# =====================================================================
import os
import markdown
from weasyprint import HTML

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "examples", "operation_waldweg")
MASTER = os.path.join(ROOT, '06_master')
TMP = '/tmp/pdf_out'
os.makedirs(TMP, exist_ok=True)

DOCS = [
    "Aufgabenstellung_Studierende.md",
    "Loesungsschluessel_Dozent.md",
    "Toolchain_und_Bewertung_Dozent.md",
]

CSS = """
@page { size: A4; margin: 2.2cm 2cm; @bottom-center {
    content: "Operation Waldweg — synthetisches Lehrmaterial · Seite " counter(page);
    font-size: 8pt; color: #888; } }
body { font-family: 'DejaVu Sans', sans-serif; font-size: 10.5pt;
    line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 19pt; color: #1f3a5f; border-bottom: 2px solid #1f3a5f;
    padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 14pt; color: #1f3a5f; margin-top: 1.4em;
    border-bottom: 1px solid #c8d4e0; padding-bottom: 2px; }
h3 { font-size: 11.5pt; color: #2c5078; }
table { border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 9.5pt; }
th { background: #1f3a5f; color: #fff; text-align: left; padding: 5px 7px; }
td { border: 1px solid #c8d4e0; padding: 4px 7px; vertical-align: top; }
tr:nth-child(even) td { background: #f4f7fa; }
code { background: #eef1f4; padding: 1px 4px; border-radius: 3px;
    font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; }
pre { background: #f4f7fa; border: 1px solid #d6dee6; border-radius: 4px;
    padding: 8px 10px; font-size: 8.5pt; overflow-wrap: anywhere; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #c0392b; background: #fdf3f2;
    margin: 0.8em 0; padding: 6px 12px; color: #7a2018; font-size: 9.5pt; }
a { color: #1f3a5f; }
"""


def main():
    outputs = []
    for fn in DOCS:
        src = os.path.join(MASTER, fn)
        if not os.path.exists(src):
            print("uebersprungen (fehlt):", fn); continue
        text = open(src, encoding='utf-8').read()
        html_body = markdown.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists'])
        html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
        out = os.path.join(TMP, fn.replace('.md', '.pdf'))
        HTML(string=html).write_pdf(out)
        outputs.append(out)
        print(f"PDF: {os.path.basename(out)}  ({os.path.getsize(out)} bytes)")
    return outputs


if __name__ == "__main__":
    main()
