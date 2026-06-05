#!/usr/bin/env python3
# =====================================================================
# gate_common.py  —  gemeinsame Gate-Logik mit Modus-Trennung
# ---------------------------------------------------------------------
# Trennt FORMAT-Checks (Schema/Join/Parsebarkeit/Timestamp-Dekodierung —
# gelten fuer JEDEN Fall) von REFERENZ-Loesungs-Checks (Waldweg-spezifische
# Inhalte wie bestimmte Texte/Werte/Koordinaten).
#
# Modus via WALDWEG_GATE_MODE:
#   all       (Default)  — beide Kategorien (z.B. Referenz-Selbsttest)
#   format               — nur Format-Checks (beliebiger Spec-Fall)
#   reference            — nur Referenz-Loesungs-Checks
#
# Verwendung im Gate:
#   from gate_common import Gate
#   G = Gate(); ok = G.ok
#   ok("Join laeuft", cond, detail)              # Format (Default)
#   ok("HR-Peak == 138", cond, detail, ref=True) # Referenz-Inhalt
#   ok_exit(G)                                    # Summary + sys.exit
# =====================================================================
import os
import sys

MODE = os.environ.get("WALDWEG_GATE_MODE", "all").lower()


class Gate:
    def __init__(self):
        self.results = []  # (name, cond, detail, ref)

    def _relevant(self, ref):
        if MODE == "all":
            return True
        if MODE == "format":
            return not ref
        if MODE == "reference":
            return ref
        return True

    def ok(self, name, cond, detail="", ref=False):
        if not self._relevant(ref):
            tag = "ref" if ref else "fmt"
            print(f"  [skip-{tag}] {name}")
            return cond
        self.results.append((name, bool(cond), detail, ref))
        print(f"  [{'OK' if cond else 'FEHLER'}] {name}  {detail}")
        return cond

    def passed(self):
        return sum(1 for _, c, _, _ in self.results if c)

    def total(self):
        return len(self.results)

    def all_ok(self):
        return self.passed() == self.total()


def ok_exit(gate):
    p, t = gate.passed(), gate.total()
    print(f"\nGATE: {p}/{t} Checks bestanden  [Modus={MODE}]",
          "✓" if p == t else "✗")
    sys.exit(0 if p == t else 1)
