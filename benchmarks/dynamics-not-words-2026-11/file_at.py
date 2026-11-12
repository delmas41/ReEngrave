"""ROADMAP 2.296 step 1: what does the EXPORTED FILE hold where Sean named a dynamic?

    python3 benchmarks/dynamics-not-words-2026-11/file_at.py SYMBOLS.json PAGE x0,y0,x1,y1 [x0,y0,x1,y1 ...] [--slack 40]

SYMBOLS.json = `lane_report`'s `work/<plate>.<arm>.symbols.json` (the arm's MusicXML parsed to its symbols, each with its page box). Prints every `dynamic` / `words` symbol of the file whose
box lies within `--slack` px of each box. Reads a file; decides nothing.
"""
import json
import sys


def main():
    d = json.load(open(sys.argv[1]))
    page = int(sys.argv[2])
    boxes = [[float(v) for v in a.split(",")] for a in sys.argv[3:] if "," in a and not a.startswith("--")]
    slack = float(sys.argv[sys.argv.index("--slack") + 1]) if "--slack" in sys.argv else 40.0
    syms = []
    for h in d.get("hosts", []):
        for k in ("dynamics", "words", "wedges"):
            for s in h.get(k) or []:
                syms.append((k, h, s))
    for s in d.get("loose", []):
        syms.append((s.get("kind"), s, s))
    print("symbols of kinds dynamics/words in file:", len(syms), "| keys of a host:", sorted((d["hosts"][0] if d.get("hosts") else {}).keys())[:20])
    for b in boxes:
        print("== box", b)
        for kind, host, s in syms:
            sb = (s.get("box") if isinstance(s, dict) else None) or host.get("box")
            pg = host.get("page")
            if not sb or (pg is not None and pg != page):
                continue
            if sb[0] <= b[2] + slack and sb[2] >= b[0] - slack and sb[1] <= b[3] + slack and sb[3] >= b[1] - slack:
                print("   ", kind, json.dumps(s)[:200])


main()
