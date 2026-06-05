#!/usr/bin/env python3
# =====================================================================
# test_swarmui.py  —  LOKALER Verbindungs-/Funktionstest fuer SwarmUI
# ---------------------------------------------------------------------
# Prueft Schritt fuer Schritt, ob die lokale SwarmUI-API erreichbar ist
# und eine Generierung funktioniert — BEVOR der grosse Lauf startet.
#
#   python3 test_swarmui.py --url http://localhost:7801 --model flux-2-klein-9b
#   python3 test_swarmui.py ... --generate     # macht zusaetzlich 1 Test-Bild
#
# Exit-Code 0 = alles ok, sonst != 0.
# =====================================================================
import argparse
import base64
import sys

try:
    import requests
except ImportError:
    print("FEHLT: pip install requests"); sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:7801")
    ap.add_argument("--model", default="flux-2-klein-9b")
    ap.add_argument("--generate", action="store_true",
                    help="zusaetzlich ein kleines Test-Bild generieren (8 Steps)")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--cfg", type=float, default=1.5)
    args = ap.parse_args()
    ok = True

    # 1) Erreichbarkeit
    print(f"[1] Verbinde mit {args.url} ...")
    try:
        r = requests.post(f"{args.url}/API/GetNewSession", json={}, timeout=10)
        r.raise_for_status()
        sid = r.json().get("session_id")
        print(f"    OK  session_id={sid}")
    except Exception as e:
        print(f"    FEHLER: SwarmUI nicht erreichbar — {e}")
        print("    Pruefe: laeuft SwarmUI? Richtiger Port? Firewall?")
        sys.exit(1)

    # 2) Modell-Liste / Modell vorhanden?
    print(f"[2] Pruefe Modell '{args.model}' ...")
    try:
        r = requests.post(f"{args.url}/API/ListModels",
                          json={"session_id": sid, "path": "", "depth": 2,
                                "subtype": "Stable-Diffusion"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        files = data.get("files", []) or []
        names = []
        for f in files:
            n = f.get("name") if isinstance(f, dict) else str(f)
            if n:
                names.append(n)
        hit = [n for n in names if args.model.lower() in n.lower()]
        if hit:
            print(f"    OK  gefunden: {hit[0]}")
        else:
            print(f"    WARN  '{args.model}' nicht in Liste. Verfuegbar (Auszug): {names[:8]}")
            print("    -> ggf. --model an exakten Namen anpassen.")
            ok = False
    except Exception as e:
        print(f"    WARN  ListModels nicht auswertbar ({e}) — fahre fort.")

    # 3) optionaler Mini-Generierungstest
    if args.generate:
        print(f"[3] Test-Generierung (steps={args.steps}, cfg={args.cfg}) ...")
        try:
            payload = {"session_id": sid, "images": 1,
                       "prompt": "a simple test photo of a grey stone on grass",
                       "model": args.model, "width": 512, "height": 512,
                       "steps": args.steps, "cfgscale": args.cfg}
            r = requests.post(f"{args.url}/API/GenerateText2Image", json=payload, timeout=300)
            r.raise_for_status()
            data = r.json()
            imgs = data.get("images") or []
            if not imgs:
                print(f"    FEHLER  keine 'images' im Response. Keys: {list(data.keys())}")
                print(f"    Roh-Antwort (gekuerzt): {str(data)[:300]}")
                sys.exit(1)
            img = imgs[0]
            if img.startswith("data:"):
                blob = base64.b64decode(img.split(",", 1)[1]); src = "base64"
            else:
                g = requests.get(f"{args.url}/{img.lstrip('/')}", timeout=60)
                g.raise_for_status(); blob = g.content; src = f"pfad ({img})"
            out = "swarmui_test.png"
            open(out, "wb").write(blob)
            print(f"    OK  Bild erhalten via {src}, {len(blob)} bytes -> {out}")
        except Exception as e:
            print(f"    FEHLER bei Generierung: {e}")
            sys.exit(1)

    print("\nERGEBNIS:", "alles bereit ✓" if ok else "erreichbar, aber Modellname pruefen ⚠")
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
