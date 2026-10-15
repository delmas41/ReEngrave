"""ROADMAP 2.136 step 1 -- which gate of `reconcile_duration` leaves a bar-unique
narrowed head unsettled?

PATH: STAGED EVALUATE (tools/omr/staged/consequences.py). Reads the 20261014-night
record via record_io.load_record, re-decides it on this tree (review.rerun, as
reconcile_why_2_22.py did), and replays the rule's own gates for every bar in the
2.134 N population (out/2.134/<lab>-held-part.json: tier evidenced, cause N).
Nothing in tools/ is edited. The rule's helpers are IMPORTED
(_standing, _left_the_bar, _event_totals, _narrowed_chords, _bar_heads_are_clean,
_bar_has_tuplet, _common_options, _admitted, _is_rest, _missed_rest_witness,
_bar_beats_at); only the ten-line landing loop is restated, because it is inline
in the rule. THE CONTROL (rule 7) that can fail: the same replay is run on EVERY
cell of the document that holds a NARROWED non-rest duration or a
`reconcile_duration` verdict, with the pre-fire state rebuilt for fired cells,
and must say "landed" exactly where the re-decided log holds a
reconcile_duration verdict (and nowhere else, or the row is reported).

Gate order is the rule's own; the first that applies wins:
  G0_cause_not_reached   evaluate skipped the rule (cause absent/abstained/narrowed)
  G1_no_meter_in_force   _bar_beats_at is None
  G2_unvalued            no standing D/N note, or a note with no current value
  G3_no_event_grouping   _event_totals is None
  G4_zero_landings       no admitted single event lands the bar (+ counterfactuals)
  G5_many_landings       more than one lands (competing landing named)
  G6_witness_refused     one landing, a LENGTHENING, missed-rest witness != clear
  G7_landed_no_verdict   replay lands and passes, the log holds no reconcile verdict
  LANDED                 replay lands and the log holds the verdict (control only)

    python3 .../reconcile_gates_2_136.py <record.json> --label lit|brah --out out.json
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
T0 = time.time()


def say(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--population", default=None)
    a = ap.parse_args()

    from tools.omr.staged import consequences as C
    from tools.omr.staged import evaluate as EV
    from tools.omr.staged.record import Kind, Outcome, Q, Scope, Subject, Verdict
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    pop_path = a.population or str(
        HERE.parent / "out" / "2.134" / f"{a.label}-held-part.json")
    P = json.load(open(pop_path))
    pop = [tuple(r["cell"]) for r in P["rows"]
           if r["tier"] == "evidenced" and r["cause"] == "N"]
    prow = {tuple(r["cell"]): r for r in P["rows"]
            if r["tier"] == "evidenced" and r["cause"] == "N"}
    say(f"population {len(pop)} N bars from {pop_path}")

    doc = load_record(a.record)
    say("loaded")
    rec = doc["record"] if "record" in doc else doc
    # The log the EXPORTER saw: GATHER rows rebuilt, then the record's OWN
    # verdicts inserted as written (ids kept, so `supersedes` still resolves).
    # NOT re-decided -- 2.134 exported this file as it stands, and a re-decide
    # on today's tree would answer a different question (tree drift).
    from tools.omr.staged.record import Candidate
    log, _ = RR.rebuild_gather(rec)
    n_v = 0
    for v in rec.get("verdicts") or ():
        cands = tuple(Candidate(value=c["value"], support=c.get("support", 0.0))
                      for c in v.get("candidates") or ())
        vv = Verdict(
            id=v["id"], subject=Subject.from_key(v["subject"]),
            quantity=v["quantity"], outcome=Outcome(v["outcome"]),
            value=v.get("value"), decider=v["decider"], reason=v["reason"],
            considered=tuple(v.get("considered") or ()),
            used=tuple(v.get("used") or ()),
            missing=tuple(v.get("missing") or ()),
            declined=tuple(v.get("declined") or ()),
            excluded=tuple(tuple(e) for e in v.get("excluded") or ()),
            correlated=tuple(frozenset(g) for g in v.get("correlated") or ()),
            basis=tuple(v.get("basis") or ()), candidates=cands,
            margin=v.get("margin"), supersedes=v.get("supersedes"),
            detail=dict(v.get("detail") or {}))
        log._vrd[vv.id] = vv
        log._index(vv.quantity, vv.subject, vv.id)
        n_v += 1
    del doc, rec
    say(f"log built: {n_v} verdicts inserted as written")
    skipped = {}

    fired = collections.defaultdict(list)
    for v in log.all_verdicts():
        if v.quantity == Q.DURATION and v.decider == "reconcile_duration":
            s = v.subject
            fired[(s.page, s.system, s.staff, s.cell)].append(v)
    say(f"reconcile_duration verdicts in the re-decided log: "
        f"{sum(len(x) for x in fired.values())} over {len(fired)} cells")

    def cell_subject(c):
        return Subject(Kind.CELL, page=c[0], system=c[1], staff=c[2], cell=c[3])

    def standing_notes(cell, pre):
        """Standing D/N durations of the cell. pre=0: as written. pre=1: the
        rule's own revisions replaced by what they superseded. pre=2: also
        every `infer:*` revision undone (the state EVALUATE's first pass saw).
        """
        undo = set()
        if pre >= 1:
            undo.add("reconcile_duration")
        out = []
        for v in C._standing(log, cell, Q.DURATION):
            while v is not None and v.supersedes and (
                    v.decider in undo
                    or (pre >= 2 and v.decider.startswith("infer:"))):
                old = log.row(v.supersedes)
                if old is None:
                    break
                v = old
            out.append(v)
        return out

    def landing_search(cell, notes, current, total, expected, *, chords,
                       evidence_filter=True, skip_tuplet=True):
        """The rule's landing loop. chords=False => no chord units at all."""
        saved = C._shortens_without_evidence
        if not evidence_filter:
            C._shortens_without_evidence = lambda note, value: False
        try:
            units = C._narrowed_chords(log, cell, notes) if chords else []
            in_chord = {m.id for ms in units for m in ms}
            lands = []
            for ms in units:
                if skip_tuplet and any(
                        float(current[m.id].get("beats") or 0.0)
                        != float(current[m.id].get("written") or -1.0) for m in ms):
                    continue
                now_b = collections.Counter(
                    float(current[m.id].get("beats") or 0.0)
                    for m in ms).most_common(1)[0][0]
                for new_b, opts in C._common_options(ms):
                    if abs(total - now_b + new_b - expected) < 1e-6:
                        lands.append((ms, opts, now_b, new_b))
            for note in notes:
                if note.id in in_chord or C._is_rest(note):
                    continue
                now = current[note.id]
                if skip_tuplet and float(now.get("beats") or 0.0) \
                        != float(now.get("written") or -1.0):
                    continue
                for option in C._admitted(note):
                    if note.outcome is Outcome.DECIDED \
                            and option.get("beam_levels") == now.get("beam_levels"):
                        continue
                    moved = total - float(now.get("beats") or 0.0) \
                        + float(option.get("beats") or 0.0)
                    if abs(moved - expected) < 1e-6:
                        lands.append(([note], [option],
                                      float(now.get("beats") or 0.0),
                                      float(option.get("beats") or 0.0)))
            return lands
        finally:
            C._shortens_without_evidence = saved

    def describe(land):
        ms, opts, was, new = land
        return {"glyphs": [m.subject.to_key() for m in ms],
                "was_beats": was, "new_beats": new,
                "new_levels": [o.get("beam_levels") for o in opts],
                "cands": [[round(float(c.value.get("beats") or 0), 3),
                           c.value.get("beam_levels")] for c in ms[0].candidates]
                if ms[0].candidates else None}

    def joint_lands(cell, notes, current, total, expected, evidence_filter):
        """Counterfactual: change ANY number of narrowed events (a chord on one
        stem is one event); how many assignments land, and the fewest events
        moved off their best-supported reading."""
        saved = C._shortens_without_evidence
        if not evidence_filter:
            C._shortens_without_evidence = lambda note, value: False
        try:
            units = C._narrowed_chords(log, cell, notes)
            in_chord = {m.id for ms in units for m in ms}
            unit_opts = []   # (now_beats, [beats of each admitted option])
            for ms in units:
                now_b = collections.Counter(
                    float(current[m.id].get("beats") or 0.0)
                    for m in ms).most_common(1)[0][0]
                unit_opts.append((now_b, [b for b, _ in C._common_options(ms)]))
            for n in notes:
                if n.id in in_chord or C._is_rest(n) \
                        or n.outcome is not Outcome.NARROWED:
                    continue
                nb = float(current[n.id].get("beats") or 0.0)
                unit_opts.append((nb, [float(o.get("beats") or 0.0)
                                       for o in C._admitted(n)]))
            if not unit_opts or len(unit_opts) > 6:
                return None, None
            best_k, count = None, 0
            for combo in itertools.product(*[o for _, o in unit_opts]):
                moved = total + sum(nb2 - nb for (nb, _), nb2 in
                                    zip(unit_opts, combo))
                if abs(moved - expected) < 1e-6:
                    count += 1
                    k = sum(1 for (nb, _), nb2 in zip(unit_opts, combo)
                            if abs(nb2 - nb) > 1e-9)
                    best_k = k if best_k is None else min(best_k, k)
            return count, best_k
        finally:
            C._shortens_without_evidence = saved

    from tools.omr.staged import inferences as INF

    def infer_view(cell):
        """What INFER's widened bar rule (2.97, `collapse_narrowed_by_bar`) says
        about the same cell: read-only, `solve_bare_stem_bar(any_reason=True)`."""
        try:
            o = INF.solve_bare_stem_bar(log, cell, any_reason=True)
        except Exception as e:           # a probe must name its own failure
            return {"error": repr(e)[:120]}
        return {"decline": o.decline, "members": o.members, "unknowns": o.unknowns,
                "landings": o.landings, "forced": o.forced,
                "ambiguous": o.ambiguous, "tip_not_clean": o.tip_not_clean,
                "lengthening_unwitnessed": o.lengthening_unwitnessed,
                "shortened_refused": o.shortened_refused}

    def settled_by(cell):
        """Deciders of the standing DECIDED durations that superseded a NARROWED one."""
        out = []
        for v in log.verdicts(Q.DURATION, cell, scope=Scope.SELF_AND_DESCENDANTS):
            if v.supersedes:
                old = log.row(v.supersedes)
                if old is not None and getattr(old, "outcome", None) is Outcome.NARROWED:
                    out.append(v.decider)
        return out

    def replay(c, pre):
        cell = cell_subject(c)
        row = {"cell": list(c)}
        if pre == 0:
            row["infer_any_reason"] = infer_view(cell)
            row["settled_by"] = settled_by(cell)
        sysk = Subject(Kind.SYSTEM, page=c[0], system=c[1])
        meter = EV._cause_for(log, Q.METER, cell)
        if meter is None:
            row["gate"], row["why"] = "G0_cause_not_reached", "cause_absent"
            return row
        row["meter_outcome"] = meter.outcome.value
        row["meter_reason"] = meter.reason
        if meter.outcome is not Outcome.DECIDED:
            row["gate"] = "G0_cause_not_reached"
            row["why"] = f"cause_{meter.outcome.value}"
            return row
        key = cell.to_key()
        if key in skipped and pre == 0:
            row["gate"], row["why"] = "G0_cause_not_reached", skipped[key]
            return row
        expected = C._bar_beats_at(meter, cell)
        row["expected"] = expected
        if expected is None:
            row["gate"] = "G1_no_meter_in_force"
            return row
        notes, set_aside = [], []
        for v in standing_notes(cell, pre):
            if v.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
                continue
            if C._left_the_bar(log, v.subject) is None:
                notes.append(v)
            else:
                set_aside.append(v.subject.to_key())
        row["n_set_aside"] = len(set_aside)
        row["n_notes"] = len(notes)
        row["n_narrowed"] = sum(1 for n in notes if n.outcome is Outcome.NARROWED
                                and not C._is_rest(n))
        if not notes:
            row["gate"], row["why"] = "G2_unvalued", "no_notes"
            return row

        def cur(v):
            if v.outcome is Outcome.DECIDED:
                return v.value
            return v.candidates[0].value if v.candidates else None
        current = {v.id: cur(v) for v in notes}
        if any(x is None for x in current.values()):
            row["gate"], row["why"] = "G2_unvalued", "none_current"
            return row
        total = C._event_totals(log, cell, notes, current)
        if total is None:
            row["gate"] = "G3_no_event_grouping"
            return row
        row["total"] = total
        row["fits"] = abs(total - expected) < 1e-6
        if row["fits"] and not any(n.outcome is Outcome.NARROWED
                                   and not C._is_rest(n) for n in notes):
            row["gate"], row["why"] = "G2_unvalued", "all_decided_and_fits"
            return row

        chord_units = C._narrowed_chords(log, cell, notes)
        row["n_chord_units"] = len(chord_units)
        row["chord_heads"] = [len(ms) for ms in chord_units]
        why_chords = None
        if chord_units:
            if not C._bar_heads_are_clean(log, cell, notes):
                why_chords = "heads_not_clean"
            elif C._bar_has_tuplet(log, cell, notes):
                why_chords = "tuplet_evidence"
        row["chords_dropped_by"] = why_chords
        lands = landing_search(cell, notes, current, total, expected,
                               chords=why_chords is None)
        row["n_landings"] = len(lands)
        row["tuplet_member_notes"] = sum(
            1 for n in notes if not C._is_rest(n) and float(
                current[n.id].get("beats") or 0.0)
            != float(current[n.id].get("written") or -1.0))
        # narrowed notes' candidates
        row["narrowed_cands"] = [
            [n.subject.to_key().split("/", 5)[-1],
             [[round(float(cc.value.get("beats") or 0), 3),
               cc.value.get("beam_levels")] for cc in n.candidates],
             n.reason, C._eighth_evidence(n)]
            for n in notes if n.outcome is Outcome.NARROWED and not C._is_rest(n)]
        if len(lands) == 0:
            row["gate"] = "G4_zero_landings"
            cf = {}
            if why_chords is not None:
                l2 = landing_search(cell, notes, current, total, expected,
                                    chords=True)
                cf["chords_not_dropped"] = len(l2)
            l3 = landing_search(cell, notes, current, total, expected,
                                chords=why_chords is None, evidence_filter=False)
            cf["unevidenced_eighth_allowed"] = len(l3)
            l4 = landing_search(cell, notes, current, total, expected,
                                chords=why_chords is None, skip_tuplet=False)
            cf["tuplet_member_allowed"] = len(l4)
            nj, kj = joint_lands(cell, notes, current, total, expected, True)
            cf["joint_assignments_filter_on"] = nj
            cf["joint_min_events_moved_filter_on"] = kj
            nj2, kj2 = joint_lands(cell, notes, current, total, expected, False)
            cf["joint_assignments_filter_off"] = nj2
            cf["joint_min_events_moved_filter_off"] = kj2
            row["counterfactual"] = cf
            row["fits_at_best_candidates"] = bool(row.get("fits"))
            if cf.get("chords_not_dropped") == 1:
                row["why"] = "chord_unit_dropped_" + why_chords
            elif cf["unevidenced_eighth_allowed"] >= 1:
                row["why"] = ("unevidenced_eighth__bar_fits_at_best_candidates"
                              if row["fits"] else
                              "unevidenced_eighth__single_event_lands")
            elif cf["tuplet_member_allowed"] >= 1:
                row["why"] = "tuplet_member_skipped"
            elif cf["joint_assignments_filter_on"] and \
                    (cf["joint_min_events_moved_filter_on"] or 0) >= 2:
                row["why"] = "needs_two_or_more_events"
            elif cf["joint_assignments_filter_off"]:
                row["why"] = "needs_two_or_more_events_and_unevidenced_eighth"
            else:
                row["why"] = "no_assignment_of_own_candidates_lands"
            return row
        if len(lands) > 1:
            row["gate"] = "G5_many_landings"
            row["landings"] = [describe(x) for x in lands[:4]]
            row["why"] = ("chord_vs_head" if any(len(x[0]) > 1 for x in lands)
                          and any(len(x[0]) == 1 for x in lands) else
                          "same_event_or_columns")
            return row
        members, options, was_b, new_b = lands[0]
        row["landing"] = describe(lands[0])
        if new_b > was_b + 1e-9:
            pieces = []
            answer, left = C._missed_rest_witness(log, cell, pieces_out=pieces)
            row["witness"] = answer
            row["witness_unexplained"] = left
            row["witness_pieces"] = pieces[:4]
            if answer != C.WITNESS_CLEAR:
                row["gate"] = "G6_witness_refused"
                row["why"] = f"witness_{answer}"
                return row
        else:
            row["witness"] = "shortening_no_witness_needed"
        row["gate"] = "REPLAY_LANDS"
        return row

    def _was(v):
        old = log.row(v.supersedes) if v.supersedes else None
        out = getattr(old, "outcome", None)
        return out.value if out is not None else None

    # --- the population -----------------------------------------------------
    rows = []
    for c in pop:
        r = replay(c, pre=0)
        r["fired_in_log"] = c in fired
        if c in fired:
            # The rule ran in this very bar and a narrowed head is STILL narrowed:
            # what did it change? (pre=1 puts back what it revised.)
            r1 = replay(c, pre=1)
            r["rule_fired_here"] = {
                "verdicts": [{"glyph": v.subject.to_key(), "to_beats":
                              (v.value or {}).get("beats"),
                              "to_levels": (v.value or {}).get("beam_levels"),
                              "was_outcome": _was(v)}
                             for v in fired[c]],
                "pre_gate": r1["gate"], "pre_landing": r1.get("landing"),
                "pre_n_landings": r1.get("n_landings")}
            r["gate"] = "G9_rule_fired_on_another_note"
            r["why"] = ("changed_a_decided_neighbour"
                        if any(x["was_outcome"] == "decided"
                               for x in r["rule_fired_here"]["verdicts"])
                        else "changed_a_narrowed_note_elsewhere")
        if r["gate"] == "REPLAY_LANDS":
            r["gate"] = "LANDED" if c in fired else "G7_landed_no_verdict"
        r2 = replay(c, pre=2)
        r["evaluate_time"] = {"gate": r2["gate"], "why": r2.get("why"),
                              "n_landings": r2.get("n_landings")}
        r["part_row"] = {k: prow[c].get(k) for k in
                         ("measure", "part", "T", "judged", "residual",
                          "evidenced_tokens", "n_streams", "ink")}
        rows.append(r)
    gates = collections.Counter(r["gate"] for r in rows)
    sub = collections.Counter((r["gate"], r.get("why")) for r in rows)
    say(f"population gates: {dict(gates)}")

    # --- the control: every fired cell, pre-state, must replay as landed ----
    ctl_rows = []
    for c in sorted(fired):
        r = replay(c, pre=1)
        r["pre_state"] = 1
        if r["gate"] != "REPLAY_LANDS":
            r2 = replay(c, pre=2)
            if r2["gate"] == "REPLAY_LANDS":
                r, r["pre_state"] = r2, 2
        r["fired_in_log"] = True
        ok = r["gate"] == "REPLAY_LANDS"
        r["control_ok"] = ok
        if ok:
            r["gate"] = "LANDED"
        ctl_rows.append(r)
    ctl_ok = sum(1 for r in ctl_rows if r["control_ok"])
    ctl_gates = collections.Counter(r["gate"] for r in ctl_rows)
    say(f"control (fired cells, pre-state): {ctl_ok}/{len(ctl_rows)} replay "
        f"as landed; {dict(ctl_gates)}")

    # --- the control's other direction: unfired cells that replay as landed --
    extra = []
    seen = set(fired)
    narrowed_cells = set()
    for v in log.all_verdicts():
        if v.quantity == Q.DURATION and v.outcome is Outcome.NARROWED:
            s = v.subject
            if s.glyph is not None:
                narrowed_cells.add((s.page, s.system, s.staff, s.cell))
    unfired_checked = 0
    for c in sorted(narrowed_cells - seen):
        r = replay(c, pre=0)
        unfired_checked += 1
        if r["gate"] == "REPLAY_LANDS":
            r["by_other_stage"] = bool(r.get("settled_by"))
            extra.append(r)
    say(f"cells with a narrowed duration and no reconcile verdict: "
        f"{unfired_checked}; of which replay LANDS (rule should have fired): "
        f"{len(extra)}")

    # --- counterfactual on INFER's twin (read-only, in-process patch, tools/ untouched) --
    # `_printed_meter_roots` compares a CARRIED meter with the top-level numerator of
    # the system it was carried from -- which is that system's FIRST segment (2.79's
    # warning). Counterfactual: compare with the source's LAST segment, the one that
    # was in force at its end and is what a carry carries. Everything else unchanged.
    def patched_roots(lg, meter, cell, _depth=0):
        if _depth > 40 or meter.outcome is not Outcome.DECIDED \
                or meter.reason not in INF._PRINTED_METER_REASONS:
            return None
        if _depth == 0:
            segs = (meter.value or {}).get("segments") or ()
            if len(segs) > 1 and cell.cell is not None \
                    and int(cell.cell) >= int(segs[1].get("from_cell") or 0):
                return None
        if meter.reason == "voted":
            rows = [r for r in meter.used
                    if (lg.row(r) is not None
                        and lg.row(r).quantity in (Q.METER_TEMPLATE, Q.METER_GLYPH,
                                                   Q.METER_OCR))]
            return tuple(rows) or None
        for r in meter.used:
            src = lg.row(r)
            if isinstance(src, Verdict) and src.quantity == Q.METER:
                sv = src.value or {}
                last = (sv.get("segments") or [sv])[-1]
                if last.get("numerator") != (meter.value or {}).get("numerator") \
                        or last.get("denominator") != (meter.value or {}).get("denominator"):
                    return None
                return patched_roots(lg, src, cell, _depth + 1)
        return None

    def clean_why(cell):
        """Which clause of `_bar_heads_are_clean` fails for this bar (DIAGNOSIS ONLY: the
        three clauses are restated from the helper, which answers a bare bool; the
        helper itself is asserted to agree below)."""
        notes_ = [v for v in standing_notes(cell, 0)
                  if v.outcome in (Outcome.DECIDED, Outcome.NARROWED)
                  and C._left_the_bar(log, v.subject) is None]
        boxes = []
        for v in notes_:
            if C._is_rest(v):
                continue
            rr = log.rows(Q.GLYPH_BOX, v.subject)
            b = (rr[-1].detail or {}).get("bbox_page_px") if rr else None
            if b and len(b) == 4:
                boxes.append((v, [float(x) for x in b]))
        lines = log.rows(Q.STAFF_LINES, cell.at(Kind.STAFF))
        ln = lines[-1].value if lines else None
        why = []
        for i, (v, b) in enumerate(boxes):
            for v2, c2 in boxes[i + 1:]:
                if C._box_iou(b, c2) > C.CLEAN_HEAD_DUPLICATE_IOU:
                    why.append({"clause": "duplicate_box", "glyph": v.subject.glyph})
            if ln and len(ln) == 5:
                sp = (ln[-1] - ln[0]) / 4.0
                cy = (b[1] + b[3]) / 2.0
                if sp > 0 and (cy < ln[0] - C.CLEAN_HEAD_OFF_STAFF_SPACES * sp
                               or cy > ln[-1] + C.CLEAN_HEAD_OFF_STAFF_SPACES * sp):
                    own = log.verdict(Q.GLYPH_OWNER, v.subject)
                    why.append({
                        "clause": "off_staff", "glyph": v.subject.glyph,
                        "spaces_off": round((ln[0] - cy) / sp if cy < ln[0]
                                            else (cy - ln[-1]) / sp, 2),
                        "owner": None if own is None else [own.outcome.value, own.reason,
                                                           str(own.value)[:40]],
                        "narrowed": v.outcome is Outcome.NARROWED})
        if boxes:
            for r in log.rows(Q.GLYPH_BOX, cell.at(Kind.SYSTEM),
                              scope=Scope.SELF_AND_DESCENDANTS):
                if r.subject.staff == cell.staff:
                    continue
                ob = (r.detail or {}).get("bbox_page_px")
                if not ob or len(ob) != 4 or C._left_the_bar(log, r.subject) is not None:
                    continue
                if any(C._box_iou(b, [float(x) for x in ob]) > C.CLEAN_HEAD_DUPLICATE_IOU
                       for _v, b in boxes):
                    why.append({"clause": "other_staff_same_ink",
                                "other": r.subject.to_key()})
        agree = (not why) == C._bar_heads_are_clean(log, cell, notes_)
        return {"fails": [w["clause"] for w in why], "detail": why[:4],
                "restatement_agrees_with_helper": agree}

    cf_rows = []
    orig_roots = INF._printed_meter_roots
    INF._printed_meter_roots = patched_roots
    try:
        for c in pop:
            cell = cell_subject(c)
            o = INF.solve_bare_stem_bar(log, cell, any_reason=True)
            narrowed = {v.subject.to_key() for v in C._standing(log, cell, Q.DURATION)
                        if v.outcome is Outcome.NARROWED and not C._is_rest(v)
                        and C._left_the_bar(log, v.subject) is None}
            props = {p_.subject.to_key(): p_ for p_ in (o.proposals or [])}
            cf_rows.append({
                "cell": list(c), "clean_why": clean_why(cell),
                "decline": o.decline, "members": o.members,
                "landings": o.landings, "forced": o.forced, "ambiguous": o.ambiguous,
                "tip_not_clean": o.tip_not_clean,
                "lengthening_unwitnessed": o.lengthening_unwitnessed,
                "shortened_refused": o.shortened_refused,
                "narrowed_heads": len(narrowed), "settled_heads": len(props),
                "bar_fully_released": bool(narrowed) and set(props) >= narrowed,
                "settled_to": [[k.split("/", 5)[-1], (p_.value or {}).get("beats"),
                                (p_.value or {}).get("beam_levels")]
                               for k, p_ in props.items()]})
    finally:
        INF._printed_meter_roots = orig_roots
    # --- counterfactual 2: the off-staff clause of `_bar_heads_are_clean` honours a DECIDED
    # `Q.GLYPH_OWNER` naming THIS staff (the ledger lines name the owner, CLAUDE.md s5).
    # Duplicate-box and another-staff-same-ink clauses stay exactly as they are. In-process
    # patch of the module attribute both rules read at call time; tools/ untouched.
    orig_clean = C._bar_heads_are_clean

    def ledger_aware_clean(lg, subject, notes):
        cell_ = subject.at(Kind.CELL)
        own_staff = subject.at(Kind.STAFF).to_key()
        boxes = []
        for v in notes:
            if C._is_rest(v):
                continue
            rr = lg.rows(Q.GLYPH_BOX, v.subject)
            b = (rr[-1].detail or {}).get("bbox_page_px") if rr else None
            if b and len(b) == 4:
                boxes.append((v.subject, [float(x) for x in b]))
        lines = lg.rows(Q.STAFF_LINES, subject.at(Kind.STAFF))
        ln = lines[-1].value if lines else None
        for i, (s_, b) in enumerate(boxes):
            for t_, c2 in boxes[i + 1:]:
                if C._box_iou(b, c2) > C.CLEAN_HEAD_DUPLICATE_IOU:
                    return False
            if ln and len(ln) == 5:
                sp = (ln[-1] - ln[0]) / 4.0
                cy = (b[1] + b[3]) / 2.0
                if sp > 0 and (cy < ln[0] - C.CLEAN_HEAD_OFF_STAFF_SPACES * sp
                               or cy > ln[-1] + C.CLEAN_HEAD_OFF_STAFF_SPACES * sp):
                    own = lg.verdict(Q.GLYPH_OWNER, s_)
                    if not (own is not None and own.outcome is Outcome.DECIDED
                            and str(own.value) == own_staff):
                        return False
        if boxes:
            for r in lg.rows(Q.GLYPH_BOX, subject.at(Kind.SYSTEM),
                             scope=Scope.SELF_AND_DESCENDANTS):
                if r.subject.staff == subject.staff:
                    continue
                ob = (r.detail or {}).get("bbox_page_px")
                if not ob or len(ob) != 4 or C._left_the_bar(lg, r.subject) is not None:
                    continue
                ob = [float(x) for x in ob]
                if any(C._box_iou(b, ob) > C.CLEAN_HEAD_DUPLICATE_IOU for _s, b in boxes):
                    return False
        return True

    # control (can fail): on every cell of the document the patched helper may only turn
    # False into True where an off-staff head with a decided own-staff owner is the cause;
    # it must never turn True into False.
    flips = {"false_to_true": 0, "true_to_false": 0, "checked": 0}
    for c in sorted(narrowed_cells):
        cell = cell_subject(c)
        nn = [v for v in standing_notes(cell, 0)
              if v.outcome in (Outcome.DECIDED, Outcome.NARROWED)
              and C._left_the_bar(log, v.subject) is None]
        a0, a1 = orig_clean(log, cell, nn), ledger_aware_clean(log, cell, nn)
        flips["checked"] += 1
        flips["false_to_true"] += (not a0) and a1
        flips["true_to_false"] += a0 and (not a1)
    say(f"clean-helper control over {flips['checked']} cells with a narrowed duration: {flips}")

    cf2_rows = []
    C._bar_heads_are_clean = ledger_aware_clean
    INF._printed_meter_roots = patched_roots
    try:
        for c in pop:
            cell = cell_subject(c)
            o = INF.solve_bare_stem_bar(log, cell, any_reason=True)
            narrowed = {v.subject.to_key() for v in C._standing(log, cell, Q.DURATION)
                        if v.outcome is Outcome.NARROWED and not C._is_rest(v)
                        and C._left_the_bar(log, v.subject) is None}
            props = {p_.subject.to_key(): p_ for p_ in (o.proposals or [])}
            cf2_rows.append({
                "cell": list(c), "decline": o.decline, "forced": o.forced,
                "ambiguous": o.ambiguous, "tip_not_clean": o.tip_not_clean,
                "lengthening_unwitnessed": o.lengthening_unwitnessed,
                "shortened_refused": o.shortened_refused,
                "narrowed_heads": len(narrowed), "settled_heads": len(props),
                "bar_fully_released": bool(narrowed) and set(props) >= narrowed,
                "settled_to": [[k.split("/", 5)[-1], (p_.value or {}).get("beats"),
                                (p_.value or {}).get("beam_levels")]
                               for k, p_ in props.items()]})
        # the EVALUATE rule with only the clean-helper patch (meter chain is not its gate)
        rc_rows = []
        for c in pop:
            r = replay(c, pre=0)
            if c in fired:
                r["gate"] = "G9_rule_fired_on_another_note"
            rc_rows.append({"cell": list(c), "gate": r["gate"], "why": r.get("why"),
                            "n_landings": r.get("n_landings"),
                            "landing": r.get("landing"), "witness": r.get("witness")})
    finally:
        C._bar_heads_are_clean = orig_clean
        INF._printed_meter_roots = orig_roots
    cf2_summary = {
        "infer_declines": dict(collections.Counter(r["decline"] for r in cf2_rows)),
        "infer_bars_fully_released": sum(1 for r in cf2_rows if r["bar_fully_released"]),
        "infer_settled_heads": sum(r["settled_heads"] for r in cf2_rows),
        "reconcile_gates_with_clean_patch": dict(collections.Counter(
            f"{r['gate']} | {r['why']}" for r in rc_rows)),
        "clean_helper_control": flips}
    say(f"counterfactual 2 (carry vs last segment + ledger-owner-aware clean helper): {cf2_summary}")
    Path(a.out).with_suffix(".cf2.json").write_text(json.dumps(
        {"summary": cf2_summary, "infer_rows": cf2_rows, "reconcile_rows": rc_rows},
        indent=1, default=str))

    cf_decl = collections.Counter(r["decline"] for r in cf_rows)
    cf_summary = {"declines_after_patch": dict(cf_decl),
                  "bars_with_a_settled_head": sum(1 for r in cf_rows if r["settled_heads"]),
                  "bars_fully_released": sum(1 for r in cf_rows if r["bar_fully_released"]),
                  "settled_heads": sum(r["settled_heads"] for r in cf_rows)}
    say(f"INFER counterfactual (carry compared with the source's LAST segment): {cf_summary}")
    Path(a.out).with_suffix(".infer-cf.json").write_text(
        json.dumps({"summary": cf_summary, "rows": cf_rows}, indent=1, default=str))

    out = {
        "label": a.label, "record": a.record,
        "population": len(pop), "gates": dict(gates),
        "sub": {f"{g} | {w}": n for (g, w), n in sub.items()},
        "partition_sums": sum(gates.values()) == len(pop),
        "control": {"fired_cells": len(ctl_rows), "replay_landed": ctl_ok,
                    "pass": ctl_ok == len(ctl_rows) and len(ctl_rows) > 0
                    and all(r["by_other_stage"] for r in extra),
                    "unfired_narrowed_cells": unfired_checked,
                    "unfired_but_replay_lands": len(extra),
                    "of_which_settled_by_another_decider": sum(
                        1 for r in extra if r["by_other_stage"]),
                    "settled_by_deciders": dict(collections.Counter(
                        d for r in extra for d in r.get("settled_by", []))),
                    "gates_of_fired": dict(ctl_gates)},
        "rows": rows, "control_rows": ctl_rows[:20],
        "control_failures": [r for r in ctl_rows if not r["control_ok"]],
        "unfired_replay_lands": extra,
    }
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    say(f"control PASS={out['control']['pass']}; partition sums="
        f"{out['partition_sums']}; written {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
