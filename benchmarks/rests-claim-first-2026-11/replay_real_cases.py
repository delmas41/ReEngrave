"""ROADMAP 2.288 round 4 -- tile by tile: does the rest reader agree with Sean's 36 answered rest tiles (`real_cases.json`, fixtures `real_cases/*.npz`)?

    python3 benchmarks/rests-claim-first-2026-11/replay_real_cases.py [--json OUT]

Each tile is replayed on its real page strokes through `page_claim_names.rest_box_verdict` (the function the gather calls). AGREES = a rest that stands READ with ink, or a not-rest
refused. A rest refused for `touches_a_head` is "agrees, merged ink" (ROADMAP 2.290 step 5 owns it); any other refusal of a rest, or a claim of a not-rest, DISAGREES.
General replay of every claim tile: `python3 -m tools.omr.staged.judged_claims` (ROADMAP 2.295); this file is the 2.288 fixtures' own, on pixels, with no gather."""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.tests import real_rest_cases as RC

WON_BY_AN_EARLIER_CLAIM = {"r1-10": "the word's READ area claim wins the settle (no claim filed on those strokes)"}


def main():
    cases = {c["id"]: c for c in json.load(open(RC.CASES_JSON))}
    out, n_agree = [], 0
    for cid in sorted(cases):
        case = cases[cid]
        if cid not in RC.case_ids():
            if case.get("group") == "accidental":
                continue                      # no detector rest box meets this accidental: nothing the rest reader could have claimed there
            out.append(dict(id=cid, sean=case["sean"], result="NO FIXTURE (no detector rest box met this tile's box)"))
            continue
        v = RC.verdict(RC.load(cid))
        if case["is_rest"]:
            ok = "AGREES" if v["standing"] == "READ" and v["ids"] else ("AGREES, merged ink" if v["why"] == "touches_a_head" else "DISAGREES")
        else:
            ok = "AGREES" if (v["standing"] != "READ" or cid in WON_BY_AN_EARLIER_CLAIM) else "DISAGREES"
        n_agree += ok.startswith("AGREES")
        out.append(dict(id=cid, sean=case["sean"], is_rest=case["is_rest"], cls=case["cls"], plate=case["plate"], page=case["page"], box=case["box"], standing=v["standing"], why=v["why"],
                        result=ok, note=WON_BY_AN_EARLIER_CLAIM.get(cid, "")))
    for r in out:
        print("%-6s %-9s p%-2s %-44s %-12s -> %-6s %-32s %s" % (r["id"], r.get("plate", ""), r.get("page", ""), r["sean"][:44], r.get("cls", ""), r.get("standing", ""), r.get("why", ""), r["result"]))
    tiles = [r for r in out if cases[r["id"]].get("group") != "accidental"]
    accs = [r for r in out if cases[r["id"]].get("group") == "accidental"]
    print("rest tiles: agrees %d of %d" % (sum(r["result"].startswith("AGREES") for r in tiles), len(tiles)))
    print("accidentals Sean named that a detector rest box meets: refused %d of %d" % (sum(r["result"].startswith("AGREES") for r in accs), len(accs)))
    if "--json" in sys.argv:
        open(sys.argv[sys.argv.index("--json") + 1], "w").write(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
