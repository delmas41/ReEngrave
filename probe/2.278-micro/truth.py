"""Brahms imslp317803 p0 hand truth (Sean's boxes): each truth stem -> beamed / flag / bare, from his beam and flag boxes (geometry: a stem END inside a
beam box grown by TOL, or touching a flag box). The class is DERIVED by geometry from Sean's boxes (the box set is his; the stem->beam association is ours).
Then each truth stem is matched to a record page-stem stroke (the stroke a PAGE_BEAM_TIP row stands on) by box overlap.
"""
import json, pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TRUTH = ROOT / "data/hand-truth/pages/imslp317803/0.json"
SP = 32.25      # staff space of this page in px (record: space_page_px 32.25)
TOL = 0.5 * SP  # a stem end within half a space of a beam box counts as on it


def load_truth():
    d = json.load(open(TRUTH))
    B = [b for b in d["boxes"] if b["cls"] == "beam"]
    F = [b for b in d["boxes"] if b["cls"].startswith("flag")]
    S = [b for b in d["boxes"] if b["cls"] == "stem"]
    return d, B, F, S


def _inside(x, y, r, tol):
    return r[0] - tol <= x <= r[2] + tol and r[1] - tol <= y <= r[3] + tol


def classify(stem, B, F, tol=TOL):
    x0, y0, x1, y1 = stem["rect"]
    xc = (x0 + x1) / 2
    ends = [(xc, y0), (xc, y1)]
    beams = [i for i, b in enumerate(B) if any(_inside(x, y, b["rect"], tol) for x, y in ends)]
    flags = [i for i, f in enumerate(F) if any(_inside(x, y, f["rect"], tol) for x, y in ends)]
    if beams:
        return "beamed", beams
    if flags:
        return "flag", flags
    return "bare", []


def match_stems(S, strokes, stem_ords):
    """truth stem index -> page stem stroke ordinal (best overlap of x and y; centre x within 0.4 sp, y overlap >= 50% of the shorter)."""
    out = {}
    for i, s in enumerate(S):
        x0, y0, x1, y1 = s["rect"]
        xc = (x0 + x1) / 2
        best = None
        for o in stem_ords:
            k = strokes[o]
            bx0, by0, bx1, by1 = k["bbox"]
            if bx1 - bx0 > 3 * SP * 0.5:   # not a stem (wide)
                continue
            if abs((bx0 + bx1) / 2 - xc) > 0.4 * SP:
                continue
            ov = min(y1, by1) - max(y0, by0)
            if ov <= 0.5 * min(y1 - y0, by1 - by0):
                continue
            sc = ov / max(1.0, max(y1, by1) - min(y0, by0))
            if best is None or sc > best[0]:
                best = (sc, o)
        if best:
            out[i] = best[1]
    return out


if __name__ == "__main__":
    d, B, F, S = load_truth()
    import collections
    c = collections.Counter(classify(s, B, F)[0] for s in S)
    print(len(B), "beams", len(F), "flags", len(S), "stems", dict(c))
    D = pickle.load(open(sys.argv[1], "rb"))
    P = D["pages"][0]
    stem_ords = {t["stem"] for t in P["tips"]}
    m = match_stems(S, P["strokes"], stem_ords)
    print("matched to a stem stroke with a tip row:", len(m), "of", len(S))
    print(collections.Counter(classify(S[i], B, F)[0] for i in m))
