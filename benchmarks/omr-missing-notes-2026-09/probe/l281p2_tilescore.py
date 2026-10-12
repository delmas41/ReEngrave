#!/usr/bin/env python3
"""l281p2_tilescore: score Sean's answers on `out/print/2.81-phase2-review/`.

`answers.json` = {"tile_01": "4", ...} -- Sean's "N. 4/8/16" (a plain 4 / 8 / 16 / 2, "dotted 4" / "4." for a
dotted quarter, "rest" / "not a note" for what is not a note). Per group:

  settled (the bar's arithmetic collapsed it)   decided right / decided WRONG against his value
  narrowed_quarter_first / narrowed_old_order   a quarter (or dotted quarter) is his value: the likelihood
                                                held / did not hold -- nothing was decided, so none is "wrong"
  controls                                      against his own hand-truth boxes; a pipeline or a reader that
                                                answers the same on a beamed and a bare control is in doubt

    python3 l281p2_tilescore.py --dir out/print/2.81-phase2-review --answers answers.json
"""
import argparse
import collections
import json
from pathlib import Path


def value_of(ans):
    """(base_denominator, dotted) from Sean's words, or None for 'not a note'."""
    a = str(ans).strip().lower()
    if a in ("rest", "not a note", "none", "?"):
        return None
    dotted = "dot" in a or a.endswith(".")
    for tok, den in (("sixteenth", 16), ("eighth", 8), ("quarter", 4), ("half", 2), ("16", 16), ("8", 8), ("4", 4),
                     ("2", 2)):
        if tok in a:
            return den, dotted
    return None


def beats(v):
    if v is None:
        return None
    den, dotted = v
    b = 4.0 / den
    return b * 1.5 if dotted else b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--answers", required=True)
    a = ap.parse_args()
    d = Path(a.dir)
    man = json.loads((d / "manifest.json").read_text())
    ans = json.loads(Path(a.answers).read_text())
    tally = collections.defaultdict(collections.Counter)
    for t in man["tiles"]:
        tid, h = t["id"], t["hidden"]
        v = value_of(ans.get(tid))
        b = beats(v)
        if b is None:
            tally["not a note / unanswered"][tid] += 1
            continue
        if t["kind"] == "control":
            want_quarter = h["control"] == "bare"
            is_quarter = abs(b - 1.0) < 1e-9 or abs(b - 1.5) < 1e-9
            tally["controls"]["agrees with his boxes" if is_quarter == want_quarter else "DISAGREES (%s)" % tid] += 1
            continue
        g = h["group"]
        fin = h["final"]
        if g == "settled":
            ok = fin.get("written") is not None and abs(float(fin["written"]) - b) < 1e-9
            tally[g]["decided right" if ok else "DECIDED WRONG (%s: ours %s, his %s)" % (tid, fin.get("written"), b)] += 1
        else:
            is_quarter = abs(b - 1.0) < 1e-9 or abs(b - 1.5) < 1e-9
            tally[g]["a quarter (likelihood held)" if is_quarter else "not a quarter (%s: his %s)" % (tid, b)] += 1
    for g, c in tally.items():
        print(g, dict(c))


if __name__ == "__main__":
    main()
