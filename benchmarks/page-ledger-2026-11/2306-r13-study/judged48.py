"""2.306 r13 study, Q3a: Sean's judged stem places (answers-2.306-r1, -r4, -r8, -r10, -r11), OLD's and NEW's answer on each, on ONE gather.
What Sean's answer says about the STEM: a note he names with a value shorter than a whole note has a stem (r10 also gives its direction);
a mark he names as not a note (a sharp sign, part of an f / p, a tremolo slash) has none. r1 asked "is this stroke a stem" (all yes).
Who says it is right: Sean. Usage: judged48.py"""
import json, os, collections
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
D = {p: load(p) for p in ("lit", "bra")}
rows = []
for rnd in ("r1", "r4", "r8", "r10", "r11"):
    J = json.load(open(os.path.join(HERE, "..", "answers", "answers-2.306-%s.json" % rnd)))
    for t in J["tiles"]:
        g = t["glyph"]
        plate = "lit" if t.get("plate", "litolff") == "litolff" else "bra"
        s = str(t.get("sean") or "").lower()
        is_note = t.get("is_note")
        if rnd == "r1":
            is_note = bool(t.get("is_stem", True))
        if is_note is None:
            is_note = not any(w in s for w in ("sharp", "dynamic", "slash", "rest"))
        want_dir = "down" if "down" in s else ("up" if s.startswith("yes, up") or s == "up" or "yes, up" in s else None)
        if g not in D[plate]["heads"]:
            rows.append((rnd, t["tile"], plate, g, s, is_note, want_dir, None, None))
            continue
        rows.append((rnd, t["tile"], plate, g, s, is_note, want_dir, old_answer(D[plate], g), new_answer(D[plate], g)))
c = collections.Counter()
for rnd, tile, plate, g, s, is_note, want, o, n in rows:
    if o is None:
        print("%-4s %2d %s %-22s Sean: %-28s NOT IN THIS GATHER'S PAGES/BOXES" % (rnd, tile, plate, g, s[:28]))
        c["not found"] += 1
        continue
    O = ("stem %s" % o["direction"]) if o["stem"] else "none (%s)" % o["why"]
    N = ("stem %s" % n["direction"]) if n["read"] else "none (%s)" % n["how"]

    def score(has, d):
        if not is_note:
            return "right" if not has else "WRONG (stems a non-note)"
        if not has:
            return "missed"
        if want and d and d != want:
            return "WRONG direction"
        return "right"
    so, sn = score(bool(o["stem"]), o["direction"]), score(bool(n["read"]), n["direction"])
    c[("OLD", so)] += 1
    c[("NEW", sn)] += 1
    print("%-4s %2d %s %-22s Sean: %-26s | OLD %-26s %-24s | NEW %-34s %s" % (rnd, tile, plate, g, s[:26], O, so, N, sn))
print(dict(c))
