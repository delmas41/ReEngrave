"""ROADMAP 2.237: for each B / C rule and each D:cutoff rule on heads, rests, accidentals -- does it still fire, does the stroke owner
(`adjudicate_stroke_owner`, 2.205) reach the same answer on the boxes the rule refused or narrowed, and how many of its decisions were
made on a margin inside the re-read noise.  STAGED path.  Reads the verdict dumps `replay_slice.py` wrote; no gather, no record.

    python3 benchmarks/rule-page/rule_parity.py DUMP_DIR OUT.json [--noise 0.05]

PARITY (per rule, per plate), over every verdict of that rule on a box subject (`glyph/p/s/st/c/n`) that REFUSED or NARROWED the box:
  same        ownership refuses the box (owns none of its ink) or contests it (narrowed)      -- ownership would have refused too
  disagrees   ownership says the box OWNS ink (a decided or merged stroke names it)             -- ownership would have kept the box
  merged      ownership merges the box with a same-family twin on the same ink (one mark, 2.186): the rule's purpose is met, ownership
              refuses neither -- counted apart, NOT as agreement and NOT as disagreement
  silent      ownership says nothing about the box (it stands on no stroke, or only strokes its family stands beside, or the cell has no
              stroke-owner verdict)                                                            -- ownership cannot tell
A rule whose subject is not a box that owns strokes (duration, dot role, stem value, articulation owner, the unboxed-ink searches) has NO
parity here: `parity: null`, the reason says why.  Never "same" by default (CLAUDE rule 8).

MARGIN: a verdict that filed `margin` (2.106) is `near` when |margin| < NOISE (default 0.05, 2.232's measure: ink re-read moves a median 0.0,
90th percentile 0.011, 95th 0.064, 6% over 0.05).  The unit is the verdict's own (`margin_unit`); a staff-space margin is compared at the
same number, which is an assumption stated, not a measurement.  A refusal with no margin is structural (an impossibility, no cut-off).
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import rule_kinds as K  # noqa: E402

BOX_DECISIONS = ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "accidental_owner", "notehead_is_an_eighth_rest")
#: why a rule has no box-level parity with ownership
NO_BOX = {
    "duration": "subject is a note's value, not a box that owns strokes",
    "stem_value": "subject is a stem's value; ownership owns strokes, it does not read a stem's levels",
    "dot_role": "subject is a dot's role; ownership claims no dot",
    "unboxed_ink_is_a_rest": "no detector box: ownership claims only boxes and found whole rests",
    "empty_bar_whole_rest": "no detector box: the 2.52 search; ownership files its found-rest claim, not a refusal",
    "glyph_owner": "which STAFF owns a box; ownership is per cell and says nothing about the staff",
    "ledger_is_not_a_ledger": "ledger rungs are not claimants",
    "articulation_is_not_an_articulation": "articulation boxes are not claimants",
    "articulation_owner": "articulation boxes are not claimants",
    "ornament_owner": "ornament boxes are not claimants",
}


def scope_rules():
    """{(quantity, reason): entry} for B / C rules and D:cutoff rules of the heads, rests and accidentals families (the rest listed for completeness)."""
    out = {}
    for e in K.RULES:
        if e.kind in ("B", "C", "D:cutoff"):
            for r in e.reasons.split(","):
                out[(e.quantity, r.strip())] = e
    return out


def read(path):
    """(verdicts, ownership) where ownership = {box key: 'refused'|'contested'}, owns = set of box keys that own a stroke, cells with a verdict."""
    vs = []
    boxes, owns, merged, cells = {}, set(), set(), set()
    for line in open(path):
        v = json.loads(line)
        if v["quantity"] == "stroke_owner":
            cells.add(v["subject"])
            d = v.get("detail") or {}
            for k, (verdict, _lost) in (d.get("boxes") or {}).items():
                boxes[k] = verdict
            for _o, st in (d.get("strokes") or {}).items():
                if st[0] == "decided":
                    owns.update(st[2])
                elif st[0] == "merged":
                    merged.update(st[2])
        else:
            vs.append(v)
    return vs, boxes, owns, merged, cells


def cell_of(subject):
    return "cell/" + subject[len("glyph/"):].rsplit("/", 1)[0]


def is_fire(v, reason_rules):
    """A verdict that REFUSED or NARROWED a box by one of the scoped rules."""
    if v["quantity"] not in BOX_DECISIONS or not str(v.get("subject", "")).startswith("glyph/"):
        return None
    key = (v["quantity"], v.get("reason"))
    if key not in reason_rules:
        return None
    if v.get("outcome") == "decided" and v.get("value") is True:
        return key
    if v.get("outcome") in ("narrowed",):
        return key
    return None


def run(dump, noise):
    rules = scope_rules()
    res = {}
    for plate in ("litolff", "brahms"):
        if not (pathlib.Path(dump) / f"{plate}.verdicts.jsonl").exists():
            continue
        vs, boxes, owns, merged, cells = read(pathlib.Path(dump) / f"{plate}.verdicts.jsonl")
        live_ids = {v["id"] for v in vs}
        sup = {s for v in vs for s in ([v["supersedes"]] if isinstance(v.get("supersedes"), str) else (v.get("supersedes") or []))}
        per = collections.defaultdict(lambda: collections.Counter())
        examples = collections.defaultdict(list)
        old_refused = collections.defaultdict(set)      # box -> rules that refused it
        fires_all = collections.Counter()
        units = collections.defaultdict(set)
        for v in vs:
            # every verdict of a scoped (quantity, reason), refused or not, is a "fire" of that exit (as count_fires counts)
            k = (v["quantity"], v.get("reason"))
            if k in rules:
                fires_all[k] += 1
            key = is_fire(v, rules)
            if key is None:
                continue
            c = per[key]
            c["refusals"] += 1
            g = v["subject"]
            old_refused[g].add(key)
            if cell_of(g) not in cells:
                c["silent_no_cell_verdict"] += 1
                c["silent"] += 1
            elif g in boxes:
                c["same_" + boxes[g]] += 1
                c["same"] += 1
            elif g in owns:
                c["disagrees"] += 1
                if len(examples[key]) < 40:
                    examples[key].append(g)
            elif g in merged:
                c["merged"] += 1        # same family as a twin on the same ink: ONE mark (2.186), neither refused nor disagreeing
            else:
                c["silent"] += 1
            m = v.get("margin")
            d = v.get("detail") or {}
            if m is None and key[1] == "stacked_head_duplicate":
                # no margin filed: the pick is the ink-fill gap between the two stacked boxes (2.232: 41% of these are on a gap < 0.02)
                try:
                    m = abs(float(d["stacked_head_this_ink"]) - float(d["stacked_head_other_ink"]))
                    d = dict(d, margin_unit="ink-fill gap between the two stacked boxes (derived, not filed)")
                except (KeyError, TypeError, ValueError):
                    m = None
            if isinstance(m, (int, float)):
                units[key].add(str(d.get("margin_unit")))
                c["with_margin"] += 1
                if abs(m) < noise:
                    c["near"] += 1
        # boxes ownership refuses/contests that NO scoped old rule refused (ownership-only)
        only = collections.Counter()
        for g, verdict in boxes.items():
            if g not in old_refused:
                only[verdict] += 1
        res[plate] = dict(fires_all={"%s|%s" % k: n for k, n in fires_all.items()},
                          per={"%s|%s" % k: dict(c, margin_units=sorted(units[k])) for k, c in per.items()},
                          examples={"%s|%s" % k: e for k, e in examples.items()},
                          ownership_only=dict(only), boxes_refused_by_ownership=dict(collections.Counter(boxes.values())),
                          cells_with_owner_verdict=len(cells))
    return res


def main():
    dump, out = sys.argv[1], sys.argv[2]
    noise = float(sys.argv[sys.argv.index("--noise") + 1]) if "--noise" in sys.argv else 0.05
    res = run(dump, noise)
    json.dump(res, open(out, "w"), indent=1)
    for plate, r in res.items():
        print(plate, "ownership refuses/contests", r["boxes_refused_by_ownership"], "of which no scoped old rule refused:", r["ownership_only"])
        for k, c in sorted(r["per"].items(), key=lambda kv: -kv[1]["refusals"]):
            print("  %-70s n=%-5d same=%-4d disagrees=%-4d merged=%-4d silent=%-4d  near(|m|<%.2f)=%d/%d" % (
                k, c["refusals"], c.get("same", 0), c.get("disagrees", 0), c.get("merged", 0), c.get("silent", 0), noise, c.get("near", 0), c.get("with_margin", 0)))


if __name__ == "__main__":
    main()
