"""The pairs to put to the PRINT — a CENSUS of the candidates, plus controls.

⚠️ A CENSUS, NOT A SAMPLE, AND THAT IS ONLY POSSIBLE BECAUSE THE REACH IS
SMALL. Every (stemless head, joined mate) pair the widened join would create
is rendered; there is nothing to pre-register a draw from, so the circularity
the sibling lane had to guard against (choosing pairs after seeing them)
cannot arise for the CANDIDATE stratum.

⚠️ THE CONTROLS CAN FAIL AND ARE THE POINT. A control is a pair of heads the
shipped overlap test ALREADY joins to one stroke -- a chord the record is
confident about. If the adjudicator reads those as *separate stems*, the
question is not being understood or the marking is wrong, and no candidate
verdict means anything. They are drawn with a seeded RNG, and the seed is
committed with the sample.

⚠️ IDS ARE OPAQUE AND THE STRATUM LIVES IN A SEPARATE MANIFEST, so the pass
can be blind: an adjudicator who can see which stratum a strip came from is
being told the answer.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import _boxes_overlap, _stems_on, collect  # noqa: E402
from reach import unjoined_members  # noqa: E402

QUESTION = (
    "The RED brackets mark one notehead and the BLUE brackets mark another. "
    "Do these two noteheads share ONE printed stem -- are they two members of "
    "the same chord?")
VERDICTS = ["one_shared_stem", "separate_stems", "red_is_not_a_notehead",
            "blue_is_not_a_notehead", "cannot_tell"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--controls", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    stems, heads, _b, _n = collect(a.record)

    cand, ctrl = [], []
    for c, hs in heads.items():
        ss = stems.get(c, [])
        if not ss:
            continue
        by_subject = {h.subject: h for h in hs}
        for r in unjoined_members(ss, hs):
            red, blue = by_subject[r["head"]], by_subject[r["mates"][0]]
            if red.page and blue.page:
                cand.append({"subject": r["head"], "mate": r["mates"][0],
                             "stem": r["stem"], "stratum": "CANDIDATE",
                             "red_page_box": red.page,
                             "blue_page_box": blue.page,
                             "x_gap_head_widths": r["x_gap_head_widths"],
                             "dy_head_heights": r["dy_head_heights"]})
        # controls: two heads the SHIPPED test already puts on one stroke
        for s in ss:
            members = [h for h in hs if _boxes_overlap(s.value, h.value)]
            if len(members) < 2:
                continue
            members.sort(key=lambda h: h.value[1])
            red, blue = members[0], members[-1]
            if not (red.page and blue.page):
                continue
            # keep the control honest: it must also be a head the shipped
            # test joins to exactly this stroke and no other
            if len(_stems_on(red.value, ss)) != 1:
                continue
            ctrl.append({"subject": red.subject, "mate": blue.subject,
                         "stem": s.id, "stratum": "CONTROL",
                         "red_page_box": red.page, "blue_page_box": blue.page,
                         "x_gap_head_widths": 0.0,
                         "dy_head_heights": round(
                             ((red.value[1] + red.value[3] / 2.0)
                              - (blue.value[1] + blue.value[3] / 2.0))
                             / max(red.value[3], 1e-6), 3)})

    rng = random.Random(a.seed)
    rng.shuffle(ctrl)
    rows = cand + ctrl[:a.controls]
    rng.shuffle(rows)

    out = {"label": a.label, "seed": a.seed, "question": QUESTION,
           "verdicts_allowed": VERDICTS,
           "n_candidates": len(cand), "n_controls_available": len(ctrl),
           "n_controls_drawn": min(a.controls, len(ctrl)),
           "rows": rows}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
    if not rows:
        print("DEAD: nothing to render", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
