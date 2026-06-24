#!/usr/bin/env python3
"""
Verfuegbarkeits-Checker fuer die Midea PortaSplit.

Laedt die in config.json hinterlegten Shop-/Produktseiten, prueft anhand von
Schluesselwoertern, ob das Produkt verfuegbar ist, und schreibt das Ergebnis
nach state.json. Findet das Skript neu verfuegbare Produkte (Wechsel von
"nicht verfuegbar" -> "verfuegbar"), wird via GitHub Actions eine E-Mail
verschickt.

Die eigentliche Mail wird im Workflow verschickt. Dieses Skript gibt nur aus,
WAS verfuegbar ist, und setzt einen GitHub-Actions-Output ("available=true").
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Konsole auf UTF-8 zwingen, damit Emojis auch unter Windows nicht crashen.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_json(path, fallback):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARN: konnte {path.name} nicht lesen: {exc}", file=sys.stderr)
    return fallback


def fetch(url):
    """Laedt die Seite, gibt (kleingeschriebener_text, fehler) zurueck."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return None, str(exc)

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True).lower()
    return text, None


def check_target(target, defaults):
    """Gibt dict mit status zurueck: available True/False/None (unbekannt)."""
    name = target.get("name", target.get("url", "?"))
    url = target["url"]
    available_kw = [k.lower() for k in target.get("available_keywords", defaults["available_keywords"])]
    unavailable_kw = [k.lower() for k in target.get("unavailable_keywords", defaults["unavailable_keywords"])]

    text, error = fetch(url)
    if error:
        return {"name": name, "shop": target.get("shop", ""), "url": url,
                "available": None, "note": f"Fehler beim Laden: {error}"}

    found_unavailable = [k for k in unavailable_kw if k in text]
    found_available = [k for k in available_kw if k in text]

    # Logik: "nicht verfuegbar"-Treffer haben Vorrang. Sonst gilt verfuegbar,
    # wenn ein Verfuegbarkeits-Keyword da ist.
    if found_unavailable:
        available = False
        note = f"nicht verfuegbar (Treffer: {', '.join(found_unavailable[:3])})"
    elif found_available:
        available = True
        note = f"VERFUEGBAR (Treffer: {', '.join(found_available[:3])})"
    else:
        available = None
        note = "unklar (keine Keywords gefunden - evtl. Bot-Schutz/JS-Seite)"

    return {"name": name, "shop": target.get("shop", ""), "url": url,
            "available": available, "note": note}


def set_action_output(key, value):
    """Schreibt einen Output fuer nachfolgende GitHub-Actions-Schritte."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def main():
    config = load_json(CONFIG_PATH, None)
    if not config:
        print("FEHLER: config.json fehlt oder ist ungueltig.", file=sys.stderr)
        sys.exit(1)

    defaults = config.get("defaults", {"available_keywords": [], "unavailable_keywords": []})
    targets = config.get("targets", [])
    old_state = load_json(STATE_PATH, {})

    results = []
    newly_available = []

    for target in targets:
        result = check_target(target, defaults)
        results.append(result)

        flag = {True: "✅ VERFUEGBAR", False: "❌ nicht verfuegbar", None: "❓ unklar"}[result["available"]]
        print(f"{flag}  [{result['shop']}] {result['name']}")
        print(f"       {result['url']}")
        print(f"       {result['note']}")

        # Nur melden, wenn jetzt verfuegbar UND vorher nicht verfuegbar war
        # (verhindert wiederholte Mails bei jedem Lauf).
        prev = old_state.get(result["url"], {}).get("available")
        if result["available"] is True and prev is not True:
            newly_available.append(result)

        time.sleep(2)  # hoeflich gegenueber den Shops

    # Neuen Zustand speichern
    new_state = {r["url"]: {"available": r["available"], "name": r["name"], "shop": r["shop"]}
                 for r in results}
    STATE_PATH.write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8")

    if newly_available:
        product = config.get("product_name", "Produkt")
        subject = f"🟢 {product} ist verfuegbar!"
        lines = [f"Folgende Treffer fuer '{product}' sind jetzt verfuegbar:", ""]
        for r in newly_available:
            lines.append(f"• [{r['shop']}] {r['name']}")
            lines.append(f"  {r['url']}")
            lines.append("")
        body = "\n".join(lines)

        Path(ROOT / "mail_body.txt").write_text(body, encoding="utf-8")
        set_action_output("available", "true")
        set_action_output("subject", subject)
        print("\n>>> NEU VERFUEGBAR – E-Mail wird verschickt.")
    else:
        set_action_output("available", "false")
        print("\n>>> Keine neuen verfuegbaren Treffer.")


if __name__ == "__main__":
    main()
