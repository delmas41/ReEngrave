"""2.279 r3: does any READ note (plain, unflagged) of the OFF arm change at all in the ON arm? (must be 0: a DECIDED note is never moved)

usage (repo root): python3 probe/2.279r3/read_moves.py out/lane-report/2.279-r3/work [litolff brahms]
A host is matched by its glyph key (`rg`); a READ host is one with blue False. Reports hosts that vanished, changed type/pitch/dots, or
turned blue/red; and, separately, BLUE hosts of OFF that changed value (a guess replaced by another guess is listed, not a READ move).
"""
import json
import pathlib
import sys


def main(work, plates):
    work = pathlib.Path(work)
    total = 0
    for plate in plates:
        off = json.loads((work / ("%s.off.symbols.json" % plate)).read_text())["hosts"]
        on = json.loads((work / ("%s.on.symbols.json" % plate)).read_text())["hosts"]
        by_on = {}
        for h in on:
            if h.get("rg"):
                by_on.setdefault(h["rg"], []).append(h)
        moved, blue_moved, n_read, relabel = [], [], 0, []
        for h in off:
            if h["kind"] != "note" or not h.get("rg"):
                continue
            cands = by_on.get(h["rg"], [])
            same = [c for c in cands if c["type"] == h["type"] and c["pitch"] == h["pitch"] and c["sub"].get("dot") == h["sub"].get("dot")]
            if not h["blue"]:
                n_read += 1
                if same and all(c["blue"] for c in same):
                    relabel.append((h["rg"], h["part"], h["measure"], h["type"], h["pitch"], "same value, now blue (its bar became a partial bar)"))
                if not same:
                    moved.append((h["rg"], h["part"], h["measure"], h["type"], h["pitch"], "->", [(c["type"], c["pitch"], c["blue"]) for c in cands]))
            elif not same:
                blue_moved.append((h["rg"], h["part"], h["measure"], h["type"], h["pitch"], "->", [(c["type"], c["pitch"], c["blue"]) for c in cands]))
        print("== %s: READ notes in OFF %d | READ notes changed or gone in ON: %d | blue notes of OFF changed or gone: %d"
              % (plate, n_read, len(moved), len(blue_moved)))
        print("   (READ notes whose value is the same but whose label became blue: %d)" % len(relabel))
        for m in moved:
            print("   READ MOVED", m)
        for m in blue_moved:
            print("   blue moved", m)
        total += len(moved)
    return total


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["litolff", "brahms"])
