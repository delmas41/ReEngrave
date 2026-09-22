"""Collate this lane's committed artefacts into ONE machine-readable result.

⚠️ EVERY FIGURE IS READ BACK FROM A COMMITTED FILE, NEVER TYPED. A result file
whose numbers were copied by hand is a ledger, and this repo's rule is that the
tree outranks the ledger -- including a ledger written inside it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args()
    b = Path(a.bench)
    out = b / "out"

    def j(name):
        return json.loads((out / name).read_text())

    rl, rb = j("reach-litolff.json"), j("reach-breitkopf.json")
    dl, db = j("decompose-litolff.json"), j("decompose-breitkopf.json")
    fl, fb = j("flip-litolff.json"), j("flip-breitkopf.json")
    wl, wb = j("width-litolff.json"), j("width-breitkopf.json")
    cl, cb = j("byclass-litolff.json"), j("byclass-breitkopf.json")
    score = j("print-score.json")

    heads = rl["REACH"]["heads_reached"] + rb["REACH"]["heads_reached"]
    no_stem = (rl["counts_today"]["no_stem"] + rb["counts_today"]["no_stem"])

    hollow = {"one_shared_stem": 0, "wrong": 0}
    black = {"one_shared_stem": 0, "wrong": 0}
    for c in (cl, cb):
        for row in c["rows"]:
            if row["verdict"] == "cannot_tell":
                continue
            k = row["red_class"] or ""
            bucket = hollow if ("Half" in k or "Whole" in k) else black
            bucket["one_shared_stem" if row["verdict"] == "one_shared_stem"
                    else "wrong"] += 1

    res = {
        "lane": b.name,
        "verdict": "REFUSED -- nothing shipped; tools/ diff is EMPTY",
        "convention_assumed":
            "A chord is several noteheads sharing ONE stem; only the "
            "outermost head sits at the stroke's END.",
        "what_would_falsify_it":
            "a CONTROL adjudicating against the record -- none did",
        "not_confirmed_with_sean": True,

        "step0_premise_check": {
            "solo_pairs": [dl["solo_pairs"], db["solo_pairs"]],
            "solo_pairs_with_a_chord_shadow_PUBLISHED_73_98":
                [dl["solo_pairs_with_a_chord_shadow"],
                 db["solo_pairs_with_a_chord_shadow"]],
            "of_which_the_shadow_IS_STEMLESS":
                [dl["shadow_rows_where_the_shadow_IS_STEMLESS"],
                 db["shadow_rows_where_the_shadow_IS_STEMLESS"]],
            "CORRECTION":
                "73/98 is NOT a reach -- two thirds of those shadows already "
                "carry a stroke of their own and are not a missing join.",
        },

        "reach": {
            "litolff": rl["REACH"], "breitkopf": rb["REACH"],
            "no_stem_today": [rl["counts_today"]["no_stem"],
                              rb["counts_today"]["no_stem"]],
            "pooled_heads_reached": heads,
            "pooled_share_of_no_stem": round(heads / no_stem, 4),
            "strokes_whose_direction_would_FLIP":
                [fl["strokes_whose_DIRECTION_FLIPS"],
                 fb["strokes_whose_DIRECTION_FLIPS"]],
        },

        "print_pass": score["POOLED"],

        "width_floor_1_0_staff_spaces": {
            "litolff": {"removes": wl["pairs_the_floor_REMOVES"],
                        "keeps": wl["pairs_the_floor_KEEPS"],
                        "against_the_print": wl["against_the_print"]},
            "breitkopf": {"removes": wb["pairs_the_floor_REMOVES"],
                          "keeps": wb["pairs_the_floor_KEEPS"],
                          "against_the_print": wb["against_the_print"]},
        },

        "hollow_vs_black_red_head": {
            "hollow": hollow, "black": black,
            "NOT_PROPOSED_AS_A_GATE":
                "n = 2 positives, and a class name is the detector's own word "
                "about the SAME box -- one signal, not a second witness.",
        },
    }
    (out / "RESULT.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
