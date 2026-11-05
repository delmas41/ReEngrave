"""2.263: of the accidentals the 11-03 record writes GUESSED by rule `accidental_family`, how many would clear a READ_MARGIN of m?
One row per head (twins: the LOWEST margin of the head's owners counts, the cautious reading). Input: margin_owners.py output.
usage: python3 benchmarks/omr-accidental-family-2026-10/margin_census.py SCRATCH_DIR   (run from the repo root)"""
import json, sys
from collections import Counter, defaultdict

S = sys.argv[1].rstrip("/") + "/"
THR = [0.0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
for plate in ("litolff", "brahms"):
    rows = [json.loads(l) for l in open(S + plate + ".owners.jsonl")]
    by = defaultdict(list)
    for r in rows:
        if r["blue_by_family"]:
            by[r["head"]].append(r)
    heads = {}
    for h, rs in by.items():
        ms = [(r["family"].get("margin") if r["family"].get("margin") is not None else 9e9) for r in rs]
        heads[h] = min(zip(ms, range(len(rs))))[0], rs[min(zip(ms, range(len(rs))))[1]]
    n = len(heads)
    kinds = Counter((r["family"]["type"] in ("natural", "sharp", "flat")) and r["family"]["type"] or "unclear/unread" for _m, r in heads.values())
    print("==", plate, "heads blue by accidental_family:", n, dict(kinds))
    print("   margin None (flat, and unclear without one):", sum(1 for m, r in heads.values() if r["family"].get("margin") is None))
    # the hazard: a bar compared with the margin of a row whose type is NOT clear
    unc = [(r["family"]["margin"], r["family"]["why"]) for _m, r in heads.values() if r["family"]["type"] not in ("natural", "sharp", "flat") and r["family"].get("margin") is not None]
    print("   UNCLEAR rows that carry a margin:", len(unc), " with margin >= 0.2:", sum(1 for m, _w in unc if m >= 0.2), Counter(w for m, w in unc if m >= 0.2))
    for t in THR:
        clear = Counter()
        for _m, r in heads.values():
            f = r["family"]
            if f["type"] in ("natural", "sharp") and f.get("margin") is not None and f["margin"] >= t:
                clear[f["type"]] += 1
        # what guess_of's own gate would do TODAY with that READ_MARGIN: any row whose margin (even unclear's) is >= t
        gate = sum(1 for _m, r in heads.values() if r["family"].get("margin") is not None and r["family"]["margin"] >= t)
        print("   READ_MARGIN %.2f: natural+sharp clear %d (%s); code's gate as written (any type with a margin >= bar) %d" % (t, sum(clear.values()), dict(clear), gate))
    nat = sorted(r["family"]["margin"] for _m, r in heads.values() if r["family"]["type"] == "natural")
    if nat:
        print("   natural margins: min %.3f  p10 %.3f  median %.3f  p90 %.3f  max %.3f" % (nat[0], nat[len(nat) // 10], nat[len(nat) // 2], nat[9 * len(nat) // 10], nat[-1]))
