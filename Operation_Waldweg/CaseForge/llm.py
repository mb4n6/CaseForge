#!/usr/bin/env python3
# =====================================================================
# CaseForge — LLM-Schicht (Fall-Vorschlag)
# ---------------------------------------------------------------------
# Baut aus Nutzereingabe + Registry + OS-Profilen + Schema einen Prompt
# und holt einen Case-Spec-Vorschlag. Zwei Backends:
#   A) cowork  : schreibt ein Prompt-Bundle; in Claude Cowork ausfuehren
#                (Claude ist das LLM) -> Antwort als case_spec.json sichern.
#   B) ollama  : lokaler HTTP-Call an http://localhost:11434 (offline).
# =====================================================================
import json
import os
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import registry as R
import i18n


def _profiles_summary():
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "profiles", "*.yaml"))):
        out.append(f"- {os.path.basename(p)[:-5]}: " + open(p).read().splitlines()[1].lstrip("# ").strip())
    return "\n".join(out)


def _registry_summary():
    lines = []
    for g in R.REGISTRY:
        lines.append(f"- {g.id} [{g.platform}/{g.os_min}] Klassen={','.join(g.artifact_classes)} "
                     f"Format={g.fmt} Tool={g.parser}")
    return "\n".join(lines)


def build_prompt(user_input: dict) -> str:
    system = open(os.path.join(HERE, "prompts", "case_proposal_system.md"), encoding="utf-8").read()
    schema = open(os.path.join(HERE, "schema", "case_spec.schema.json"), encoding="utf-8").read()
    # Sprachauswahl: user_input.language (Code/Locale/Endonym) -> harte LLM-Anweisung
    lang_block = i18n.proposal_language_instruction(user_input.get("language"))
    return f"""{system}

{lang_block}

## Verfuegbare OS-Profile
{_profiles_summary()}

## Verfuegbare Generatoren / Artefaktklassen (Registry)
{_registry_summary()}

## Verfuegbare Forensik-Tools (Validierung)
{', '.join(R.parsers())}

## Case-Spec JSON-Schema
{schema}

## NUTZEREINGABE
{json.dumps(user_input, ensure_ascii=False, indent=2)}

## DEINE AUSGABE
Gib einen vollstaendigen Case-Spec als JSON (Schema-konform) + einen `_proposal_summary`-Block aus.
"""


def _ollama_models(url, timeout=5):
    """Liste der lokal installierten ollama-Modelle (oder None bei Fehler)."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=timeout) as r:
            return [m.get("name") for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return None


def _model_present(model, available):
    """Toleranter Abgleich: 'qwen2.5' matcht 'qwen2.5:latest' etc."""
    if not available:
        return True  # keine Liste -> nicht blockieren
    if model in available:
        return True
    base = model.split(":")[0]
    return any(a == model or a.split(":")[0] == base for a in available)


def propose_ollama(prompt, model="qwen2.5:32b-instruct", url="http://localhost:11434",
                   timeout=1800, temperature=0.7):
    """Ruft ollama via STREAMING auf (/api/generate, stream=True).

    Streaming verhindert den blockierenden Einzel-Read: Ollama laedt das
    Modell beim ersten Aufruf in den RAM/VRAM (Cold Start kann Minuten
    dauern) und generiert dann tokenweise. `timeout` ist der Socket-Read-
    Timeout PRO Chunk, nicht fuer die Gesamtdauer — grosszuegig waehlen.
    """
    import urllib.request
    import urllib.error
    import socket

    # --- Preflight: Server erreichbar? Modell vorhanden? ---
    available = _ollama_models(url)
    if available is None:
        raise SystemExit(
            f"[ollama] Server unter {url} nicht erreichbar.\n"
            f"  -> laeuft 'ollama serve'?  Test: curl {url}/api/tags")
    if not _model_present(model, available):
        raise SystemExit(
            f"[ollama] Modell '{model}' nicht installiert.\n"
            f"  Verfuegbar: {', '.join(available) or '(keine)'}\n"
            f"  -> 'ollama pull {model}'  (Hinweis: gueltige Tags z.B. "
            f"qwen2.5:7b, qwen2.5:14b-instruct, llama3.1:8b)")

    body = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "keep_alive": "10m",
        "options": {"temperature": temperature},
    }).encode()
    req = urllib.request.Request(f"{url}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})

    chunks, n = [], 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for line in r:  # zeilenweise NDJSON
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if "error" in obj:
                    raise SystemExit(f"[ollama] Fehler: {obj['error']}")
                chunks.append(obj.get("response", ""))
                n += 1
                if n % 25 == 0:
                    sys.stderr.write("."); sys.stderr.flush()
                if obj.get("done"):
                    break
    except socket.timeout:
        raise SystemExit(
            f"[ollama] Timeout nach {timeout}s ohne Antwort-Chunk.\n"
            f"  Moegliche Ursachen: Modell wird noch geladen (Cold Start) oder "
            f"zu gross fuer den Speicher.\n"
            f"  -> kleineres Modell waehlen oder --timeout erhoehen; "
            f"vorab 'ollama run {model}' zum Vorladen.")
    except urllib.error.URLError as e:
        raise SystemExit(f"[ollama] Verbindungsfehler: {e}")
    sys.stderr.write("\n")
    return "".join(chunks)


def propose_cowork(prompt, outdir):
    """Schreibt das Prompt-Bundle; in Claude Cowork ausfuehren lassen."""
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, "proposal_prompt.md")
    open(p, "w", encoding="utf-8").write(prompt)
    return ("[cowork] Prompt-Bundle geschrieben: %s\n"
            "In Claude Cowork: Inhalt als Anfrage stellen -> Antwort als "
            "out/case_spec.json speichern, dann 'forge.py build --spec ...'." % p)


if __name__ == "__main__":
    # Demo: Prompt aus Beispieleingabe bauen
    demo = {"deliktart": "Betrug (Romance Scam)", "lernziel": "Cross-Device-Chat + Krypto-Spuren",
            "devices": [{"platform": "ios", "os_profile": "ios_17", "owner": "Opfer"},
                        {"platform": "android", "os_profile": "android_14", "owner": "Beschuldigter"}],
            "assets_count": 2}
    print(build_prompt(demo)[:1200], "\n...[gekuerzt]")
