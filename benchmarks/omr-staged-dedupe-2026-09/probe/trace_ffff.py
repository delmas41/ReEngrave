"""Trace every `fff` / `ffff` in the exported file back to its letter boxes.

⚠️ NAMING, NOT COUNTING. The question is not how many long f-words there are;
it is whether the letters under one are FOUR PIECES OF INK or two pieces of ink
detected twice — and only the boxes can say.

Each `dynamic` verdict carries `detail.words[*].band_offsets` and the ids it
`used`, so the letters behind a word can be recovered exactly rather than
re-derived.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from reach import corners_to_xywh  # noqa: E402
from tools.omr.transcribe import _bbox_iou_xywh  # noqa: E402

LONG = {"fff", "ffff", "fffff", "ppp", "pppp"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args(argv)

    d = json.load(open(args.record))
    obs_by_id = {o["id"]: o for o in d["record"]["observations"]}

    n_words = collections.Counter()
    traced = []
    for v in d["record"]["verdicts"]:
        if v["quantity"] != "dynamic" or v["outcome"] != "decided":
            continue
        detail = v.get("detail") or {}
        for w in (detail.get("words") or []):
            if not w.get("spelled"):
                continue
            n_words[w["text"]] += 1

    # The `used` ids are pooled per verdict (the words pop their own `_ids`
    # into it), so recover the letters by CELL and re-run the same grouping
    # the adjudicator does — on the rows it actually used.
    for v in d["record"]["verdicts"]:
        if v["quantity"] != "dynamic" or v["outcome"] != "decided":
            continue
        detail = v.get("detail") or {}
        texts = [w["text"] for w in (detail.get("words") or []) if w.get("spelled")]
        if not any(t in LONG for t in texts):
            continue
        letters = []
        for oid in (v.get("used") or ()):
            o = obs_by_id.get(oid)
            if o is None or o["quantity"] != "dynamic_letter":
                continue
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b is None:
                continue
            letters.append((o["subject"], o["value"], corners_to_xywh(b),
                            o["score"]))
        letters.sort(key=lambda e: e[2][0])
        traced.append((v["subject"], texts, letters))

    print("spelled dynamic words on the record (by text):")
    for k, n in sorted(n_words.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<8} {n}")

    print(f"\ncells whose words include one of {sorted(LONG)}: {len(traced)}")
    shown = 0
    doubled_cells = 0
    for sub, texts, letters in traced:
        pairs = []
        for i in range(len(letters)):
            for j in range(i + 1, len(letters)):
                v = _bbox_iou_xywh(letters[i][2], letters[j][2])
                if v > 0.3:
                    pairs.append((i, j, round(v, 3)))
        # A twin is a pair on DIFFERENT STAVES (one contest) or the same cell.
        cross = [(i, j, v) for i, j, v in pairs
                 if letters[i][0].split("/")[3] != letters[j][0].split("/")[3]]
        if pairs:
            doubled_cells += 1
        if shown >= args.limit:
            continue
        shown += 1
        print(f"\n{sub}  words={texts}")
        for s, cls, box, sc in letters:
            print(f"    {s:<22} {cls:<12} conf={sc:.3f} "
                  f"box={[round(x, 1) for x in box]}")
        for i, j, v in pairs:
            tag = "CROSS-STAFF" if (i, j, v) in cross else "same-staff"
            print(f"    ⚠️ overlap {tag}: letter {i} and letter {j} IoU={v}")

    print(f"\ncells with a long f/p word AND an overlapping letter pair: "
          f"{doubled_cells} of {len(traced)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
