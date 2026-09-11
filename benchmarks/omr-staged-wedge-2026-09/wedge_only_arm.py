"""Re-run ONE decision over the pipeline's own record — the tightest A/B.

⚠️ WHY THIS AND NOT A FULL RE-ADJUDICATION. `readjudicate_wedge.py` rebuilds
the whole log and re-runs every decision, which on a 4-page 27-staff record is
hours (`glyph_owner` is quadratic in a page's detections) and re-derives
`Q.GLYPH_OWNER` and `Q.VOICES` — the two verdicts `wedge_anchor` READS. That
is strictly worse as a control, not just slower: it lets those inputs move,
so a change in the wedge answer could come from the thing under test or from
its re-derived input.

This replays the record's OWN observations AND its OWN verdicts, then runs
`wedge_anchor` alone. Every input to the decision is byte-for-byte what the
pipeline decided; the only thing that differs between the arms is the rule.

⚠️ IT INHERITS `readjudicate.py`'S BLIND SPOT AND THE INHERITANCE IS CHECKED,
NOT ASSUMED: rebuilding from a SAVED record cannot see a GATHER change.
`git diff --name-only origin/main...HEAD` names neither `gather.py` nor
`record.py` for this change, so it does not apply. It would apply to the next
person's, and this file says so rather than leaving it to be rediscovered.

⚠️ REACH IS PRINTED FIRST and a zero-reach document exits non-zero, because a
change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are the same number.

    python3 .../wedge_only_arm.py /tmp/wedge/brahms.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged import adjudicate                           # noqa: E402
from tools.omr.staged import adjudicators                         # noqa: E402,F401
from tools.omr.staged.record import (Log, Outcome, Q, Subject,    # noqa: E402
                                     Verdict)


def replay(rec: dict) -> Log:
    """A Log holding the record's GATHER rows AND its VERDICTS, unchanged."""
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    log.freeze()
    # ⚠️ THE VERDICTS ARE REPLAYED, NOT RE-DERIVED — that is the whole point.
    # `wedge_anchor` reads `Q.GLYPH_OWNER` and `Q.VOICES`; recomputing them
    # would let the decision's INPUT move between arms.
    # ⚠️⚠️ ONLY THE TWO VERDICT FAMILIES THE DECISION DECLARES, and that is
    # the tighter control rather than a shortcut. Replaying EVERY verdict
    # raises `AlreadyAdjudicated` the moment an EVALUATE consequence that
    # SUPERSEDES one is reached (`restate_pitch` on a pitch), so a faithful
    # full replay would have to reproduce the supersession chain — and none of
    # it is read here. `wedge_anchor` declares `wants=(WEDGE_BOX, GLYPH_BOX,
    # GLYPH_OWNER, VOICES)`; the first two are observations, and these are the
    # other two. Naming them makes the arm say exactly what the decision is
    # given.
    wanted = {Q.GLYPH_OWNER, Q.VOICES}
    for v in rec["verdicts"]:
        if v["quantity"] not in wanted:
            continue
        # ⚠️ `candidates` TRAVELS, and it is not decoration: `Verdict` refuses
        # a NARROWED verdict with fewer than two, because with one it has
        # DECIDED and with none it has ABSTAINED. Dropping it here turned a
        # faithful replay into a constructor error — the record's own
        # invariant catching a lossy copy, which is what it is for.
        log.record(Verdict(
            id=v["id"], subject=Subject.from_key(v["subject"]),
            quantity=v["quantity"], outcome=Outcome(v["outcome"]),
            value=v.get("value"), decider=v.get("decider") or "replay",
            reason=v.get("reason") or "replayed",
            candidates=tuple(v.get("candidates") or ()),
            detail=dict(v.get("detail") or {})))
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--export", action="store_true",
                    help="export the record twice -- with the new wedge "
                         "verdicts and without -- and diff the two files")
    a = ap.parse_args()

    whole = json.load(open(a.record))
    rec = whole["record"]

    rows = [o for o in rec["observations"] if o["quantity"] == Q.WEDGE_BOX]
    readers = collections.Counter(str(o.get("reader")) for o in rows)
    with_page = sum(1 for o in rows
                    if (o.get("detail") or {}).get("bbox_page_px"))
    print("=" * 72)
    print(f"REACH: {len(rows)} Q.WEDGE_BOX rows")
    print(f"  by reader     : {dict(readers)}")
    print(f"  with page box : {with_page}  (the rest can only abstain)")
    print(f"  provenance    : {whole.get('provenance')}")
    if not rows:
        print("⚠️ INSTRUMENT DEAD on this document — nothing to measure.")
        return 1
    print("=" * 72)

    before = collections.Counter(
        (v["outcome"], v.get("reason"))
        for v in rec["verdicts"] if v["quantity"] == Q.WEDGE_ANCHOR)
    print(f"\nBEFORE (the stub, as the pipeline wrote it):")
    for k, n in sorted(before.items()):
        print(f"  {k[0]:10} {str(k[1]):24} {n}")

    print("\nrunning wedge_anchor over the record's own verdicts...")
    log = replay(rec)
    adjudicate.run(log, order=(Q.WEDGE_ANCHOR,))

    got = [v for v in log.to_json()["verdicts"]
           if v["quantity"] == Q.WEDGE_ANCHOR]
    after = collections.Counter((v["outcome"], v.get("reason")) for v in got)
    print(f"\nAFTER (this tree):")
    for k, n in sorted(after.items()):
        print(f"  {k[0]:10} {str(k[1]):24} {n}")

    decided = [v for v in got if v["outcome"] == "decided"]
    kinds = collections.Counter((v.get("detail") or {}).get("kind")
                                for v in decided)
    degen = sum(1 for v in decided
                if (v.get("detail") or {}).get("degenerate"))
    voiced = sum(1 for v in decided
                 if (v.get("detail") or {}).get("voices_read"))
    cands = [(v.get("detail") or {}).get("n_candidates") or 0
             for v in decided]
    print(f"\n  kinds                    : {dict(kinds)}")
    print(f"  under ONE note            : {degen}")
    print(f"  bars whose voices were read: {voiced}")
    if cands:
        cands.sort()
        print(f"  candidate heads per hairpin: min {cands[0]} "
              f"median {cands[len(cands) // 2]} max {cands[-1]}")
    if not a.export:
        return 0

    # ── ONE GATHER, EXPORTED TWICE ──────────────────────────────────────────
    # ⚠️ The two arms differ ONLY in whether the wedge verdicts are present,
    # so anything that moves outside the `<wedge>` elements is this change
    # reaching somewhere it should not.
    from tools.omr.staged import export as SX

    off = json.loads(json.dumps(whole))
    off["record"]["verdicts"] = [v for v in rec["verdicts"]
                                 if v["quantity"] != Q.WEDGE_ANCHOR]
    on = json.loads(json.dumps(off))
    on["record"]["verdicts"] = on["record"]["verdicts"] + got

    xml_off, rep_off = SX.to_musicxml(off)
    xml_on, rep_on = SX.to_musicxml(on)

    print(f"\nEXPORT   <wedge> {rep_off['written'].get('wedges', 0)} -> "
          f"{rep_on['written'].get('wedges', 0)}")
    for key in ("notes", "rests", "measure_rests_read", "slurs", "ties",
                "dynamics", "articulations", "fermatas", "ornaments"):
        x, y = rep_off["written"].get(key, 0), rep_on["written"].get(key, 0)
        flag = "" if x == y else "   ⚠️ MOVED"
        print(f"  {key:20} {x:6} -> {y}{flag}")
    print(f"  balance : {rep_on['wedge_balance']}")
    print(f"  not written: {rep_on['wedges_not_written']}")

    def strip(xml):
        """Remove the five-line `<direction>` block each wedge is wrapped in."""
        lines, out = xml.splitlines(), []
        i = 0
        while i < len(lines):
            if (lines[i].strip() == '<direction placement="below">'
                    and i + 2 < len(lines) and "<wedge" in lines[i + 2]):
                i += 5
                continue
            out.append(lines[i])
            i += 1
        return "\n".join(out)

    same = strip(xml_on) == strip(xml_off)
    print(f"\n  identical OUTSIDE the <wedge> elements: {same}")
    pathlib.Path("/tmp/wedge/on.musicxml").write_text(xml_on)
    pathlib.Path("/tmp/wedge/off.musicxml").write_text(xml_off)
    print("  wrote /tmp/wedge/on.musicxml and off.musicxml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
