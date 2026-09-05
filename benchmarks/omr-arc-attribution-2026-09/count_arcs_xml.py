"""Per-part slur/tie counts in a MusicXML file — pred vs truth side by side."""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def counts(path):
    root = ET.parse(path).getroot()
    names = {}
    for sp in root.iter("score-part"):
        pn = sp.find("part-name")
        names[sp.get("id")] = (pn.text or "").strip() if pn is not None else ""
    out = []
    for part in root.iter("part"):
        pid = part.get("id")
        s = sum(1 for x in part.iter("slur") if x.get("type") == "start")
        t = sum(1 for x in part.iter("tied") if x.get("type") == "start")
        out.append((pid, names.get(pid, ""), s, t))
    return out


def main():
    pred, truth = Path(sys.argv[1]), Path(sys.argv[2])
    p, t = counts(pred), counts(truth)
    print(f"{'idx':>3} {'pred part':22s} {'slur':>5} {'tie':>4}   "
          f"{'truth part':22s} {'slur':>5} {'tie':>4}")
    for i in range(max(len(p), len(t))):
        a = p[i] if i < len(p) else ("", "", 0, 0)
        b = t[i] if i < len(t) else ("", "", 0, 0)
        mark = "  <<<" if abs(a[2] - b[2]) + abs(a[3] - b[3]) >= 3 else ""
        print(f"{i:>3} {a[1][:22]:22s} {a[2]:5d} {a[3]:4d}   "
              f"{b[1][:22]:22s} {b[2]:5d} {b[3]:4d}{mark}")
    print(f"TOTAL pred slur {sum(x[2] for x in p)} tie {sum(x[3] for x in p)} | "
          f"truth slur {sum(x[2] for x in t)} tie {sum(x[3] for x in t)}")


if __name__ == "__main__":
    main()
