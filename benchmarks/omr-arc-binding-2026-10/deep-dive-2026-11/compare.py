"""Compare two arms' WRITTEN arcs (ties and slurs by their end-head glyph keys) and, by place, the notes, on the counted pages (measure only).

    python3 compare.py PLATE BASE ARM [DIR]

Gained / lost arcs are matched by END-HEAD PLACE (the head's page box centre), never by glyph key alone (twin boxes). Reports the counts of ties, slurs,
notes and (when the judged scorer is importable) right -> wrong from Sean's judged answers via tools.omr.staged.judged on the two arms' mini records is
left to lane_report; here the control is the arc file change and the note count.
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import written as W

plate, base, arm = sys.argv[1], sys.argv[2], sys.argv[3]
D = pathlib.Path(sys.argv[4] if len(sys.argv) > 4 else "scratch/dd")


def load(name):
    dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, name))))
    xml = (D / ("%s.%s.musicxml" % (plate, name))).read_text()
    wr = W.parse(xml)
    heads = {h["subject"]: h["box"] for h in dump["heads"]}
    cp = set(dump["pages"])

    def place(k):
        b = heads.get(k)
        if not b:
            return None
        return (int(k.split("/")[1]), round((b[0] + b[2]) / 2 / 8), round((b[1] + b[3]) / 2 / 8))

    def keyset(pairs):
        s = collections.Counter()
        for a, b in pairs:
            if int(a.split("/")[1]) in cp:
                pa, pb = place(a), place(b)
                s[(pa, pb)] += 1
        return s
    return dict(ties=keyset(wr["ties"]), slurs=keyset(wr["slurs"]), notes=sum(1 for k in wr["notes"] if int(k.split("/")[1]) in cp), dump=dump)


A, B = load(base), load(arm)
out = {}
for kind in ("ties", "slurs"):
    a, b = A[kind], B[kind]
    gained = sum((b - a).values())
    lost = sum((a - b).values())
    out[kind] = dict(base=sum(a.values()), arm=sum(b.values()), gained=gained, lost=lost)
out["notes"] = [A["notes"], B["notes"]]
print(json.dumps(out))
