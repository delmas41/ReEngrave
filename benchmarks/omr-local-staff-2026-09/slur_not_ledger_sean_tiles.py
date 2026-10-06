"""lane-slur-not-ledger: the subjects of Sean's confirmed-right tiles. note_first_sample.png tiles 1-11 (re-drawn by the
sheet's own seed, 20261005 over the two OOS jsons in the order litolff, brahms; control that can fail: tile 12 must be
Brahms `glyph/5/0/6/3/2`, the 'cre' tile) and night_1006_sample.json tiles 1-5,7,8,11,12 (6 is the slur tile).
Prints one JSON list of [doc-short, subject]."""
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent


def note_first_pick():
    pool = []
    for which in ("litolff", "brahms"):
        for r in json.loads((HERE / f"farhead_note_first_oos_{which}.json").read_text()):
            if r["new"]["pos"] is not None and r["new"]["line_y"] is not None:
                r["doc"] = which
                pool.append(r)
    return random.Random(20261005).sample(pool, 12)


def night_pick():
    d = json.loads((HERE.parents[1] / "out/print/ledgers/night_1006_sample.json").read_text())
    return d


def tiles():
    nf = note_first_pick()
    assert nf[11]["subject"] == "glyph/5/0/6/3/2" and nf[11]["doc"] == "brahms", (nf[11]["doc"], nf[11]["subject"])
    out = [[r["doc"], r["subject"], "nf%d" % (i + 1)] for i, r in enumerate(nf[:11])]
    nt = night_pick()
    for i in (1, 2, 3, 4, 5, 7, 8, 11, 12):
        t = nt[i - 1]
        out.append(["litolff" if "beethoven" in t["doc"] else "brahms", t["subject"], "night%d" % i])
    return out


if __name__ == "__main__":
    print(json.dumps(tiles()))
