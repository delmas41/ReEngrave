"""The DETAILED RE-GATHER REPORT -- ROADMAP 2.118 (STAGED path, reads only).

Sean, 2026-10-14: *"Our regather reports need to start becoming more
detailed. We should have details like (but not limited to). How many total
bars, how many symbols of each kind, how much is unknown, unread, what is
being held out or guessed, how much certainty surround the guessing, and
ultimately what happens to those numbers at each stage, including export."*

    # 1. the record side, reduced once to a small JSON (a Brahms record is
    #    6.7 GB on disk; it is loaded once here and then freed)
    python3 -m tools.omr.staged.regather_report extract REC --out facts.json
    # 2. one movement's report, with the previous night beside it
    python3 -m tools.omr.staged.regather_report build --facts F --export-report COV \\
        --musicxml X [--prev-facts F0 --prev-export-report COV0 --prev-musicxml X0] --out DIR
    # 3. a whole night, both movements, found by the overnight naming convention
    python3 -m tools.omr.staged.regather_report night --tag 20261013-night --base 20261011-night --out DIR

## Where each number comes from (rule 1: derive, do not re-count)

* EXPORT side -- the exporter's OWN report (`export.coverage` as written by
  `export --coverage`, or `current.json`'s `export.report`): families, `written`,
  `guessed` (2.103), `partial_bars` (2.117), `bars_held_out_sum`,
  `unread_bar_marks`, `*_not_written`, `*_balance`, `balance`, `part_join`,
  `unclaimed_classes`, `decided_and_unwritten`. Nothing there is recounted.
* RECORD side -- `export.Record` (the standing verdict), `export.FAMILIES` and
  `_claims` (class -> family), `export.guess_of` (what is GUESSED, its rule and
  candidates), `trace.stage_of_decider` (which stage wrote a verdict -- no
  second table), `Verdict.margin` and `detail["margin_unit"]` (2.106), the
  record's own `adjudication` summary and `family_precision.FAMILY_REFUSALS`.
* FILE side -- the MusicXML itself, for the two things only the file knows:
  which parts and pages carry the blue and the red.
* COMPUTED HERE, once, and labelled so: the per-symbol ADJUDICATE -> INFER
  funnel at glyph level, the margin bands, the bar states per part, the
  night-over-night deltas.

⚠️ Every funnel row BALANCES (in = the sum of its outs) or is printed as an
IMBALANCE with its difference. A row that cannot fail is not a control.
⚠️ `DERIVED_CHECK = True`: this module names quantities to report them and
consumes none at run time. Registered in `reach.NOT_A_STAGE`.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

#: See the module docstring. Must stay a bare module-level literal `True`.
DERIVED_CHECK = True

GUESS_BLUE = "#1F6FEB"
UNREAD_RED = "#D00000"

#: How many example reasons / worst items a section lists.
TOP_REASONS = 6

# ─────────────────────────────────────────────────────────────────────────────
# The funnels: which symbol kind, which refusal, which meaning.
# ─────────────────────────────────────────────────────────────────────────────

#: (row name, family in `export.FAMILIES`, "is it really one?" refusal
#: quantity or None, the meaning quantity that gives the symbol its value,
#: plain-words gloss). ⚠️ A PRESENTATION table: what a human calls the
#: question. The refusal quantities are checked against
#: `family_precision.FAMILY_REFUSALS` by a test, so a new refusal that no row
#: shows is a failure, not a silent omission.
FUNNELS: Tuple[Tuple[str, str, Optional[str], str, str], ...] = (
    ("noteheads: how long", "note", "notehead_is_not_a_notehead", "duration",
     "each detected notehead box: is it a real notehead, and what length is it"),
    ("noteheads: which pitch", "note", "notehead_is_not_a_notehead", "pitch",
     "the same boxes: which line or space, and so which note name"),
    ("rests", "rest", "rest_is_not_a_rest", "duration",
     "each detected rest box: is it a real rest, and what length"),
    ("accidentals", "accidental", "accidental_is_not_an_accidental",
     "accidental_owner", "sharps/flats/naturals: which notehead they belong to"),
    ("slurs", "slur", "arc_is_not_an_arc", "arc_kind",
     "curved lines read as slurs"),
    ("ties", "tie", "arc_is_not_an_arc", "arc_kind",
     "curved lines read as ties"),
    ("articulations", "articulation", "articulation_is_not_an_articulation",
     "articulation_owner", "staccato dots, accents, tenuto: which note"),
    ("fermatas", "fermata", None, "fermata_owner", "fermatas: which note"),
    ("ornaments", "ornament", None, "ornament_owner", "trills, turns, tremolo"),
    ("hairpins", "wedge", None, "wedge_anchor", "crescendo/diminuendo wedges"),
)

#: Refusal quantities (`family_precision.FAMILY_REFUSALS`) that have no row of
#: their own in the funnel above: a ledger line, a flag and an arpeggio are
#: not symbols a musician counts. They are still in the exporter's own
#: `family_refusals`. A test fails when a NEW refusal is in neither list.
REFUSALS_NOT_SHOWN_AS_ROWS = frozenset({
    "ledger_is_not_a_ledger", "arpeggiato_is_not_an_arpeggiato", "flag_is_not_a_flag",
    # shown as unit rows (one verdict per place), refusals via `family_refusals`
    "dynamic_is_not_a_dynamic", "keysig_marker_is_not_a_marker",
    "tuplet_marker_is_not_a_marker"})

#: Quantities whose verdicts live on a STAFF/SYSTEM, not on a glyph box: their
#: funnel is by verdict, with the boxes shown as context only.
UNIT_QUANTITIES: Tuple[Tuple[str, str, str, Optional[str]], ...] = (
    ("clefs", "clef", "one per staff and system", "clef"),
    ("key signatures", "key_signature", "one per staff and system", "key"),
    ("meters (time signatures)", "meter", "one per system", "time"),
    ("instrument names", "instrument", "one per staff", None),
    ("direction words", "direction", "one verdict per inked cell; most say no word is there", None),
    ("dynamic words", "dynamic", "one verdict per inked cell (most say no dynamic); the boxes are single letters", "dynamic"),
    ("tuplet ratios", "tuplet_ratio", "the 3 over a triplet", "tuplet"),
)

#: Units whose verdict is a plain yes/no/none per place, not a reading that
#: can be read-or-carried: shown as decided / narrowed / abstained only.
COUNT_ONLY_UNITS = frozenset({"direction words", "dynamic words", "tuplet ratios"})

#: Reason words -> how a clef/key/meter reading was reached. ⚠️ HAND-WRITTEN
#: classification of reason WORDS the deciders file; a reason in none of the
#: three lands in "other" and is printed, never folded into READ.
READ_REASONS = frozenset({
    "scored", "markers", "label", "roster", "voted", "from_instrument",
    "fitted_no_markers", "printed"})
CARRIED_REASONS = frozenset({
    "carried", "clef_from_other_systems", "key_from_other_systems",
    "key_from_document_majority", "key_from_part", "carry"})


def _stage_of(decider: str) -> str:
    from . import trace
    return trace.stage_of_decider(decider or "")


def _kind_of(subject: str) -> str:
    return subject.split("/", 1)[0]


def _key(subject: str) -> str:
    """`glyph/1/0/11/2/4` -> `p1 sys0 staff11 bar2 glyph4`: the address a crop
    can be cut from. Cell index restarts per system (CLAUDE.md §5)."""
    parts = subject.split("/")
    names = {"document": [], "page": ["p"], "system": ["p", "sys"],
             "staff": ["p", "sys", "staff"], "cell": ["p", "sys", "staff", "cell"],
             "glyph": ["p", "sys", "staff", "cell", "glyph"]}.get(parts[0], [])
    return " ".join(f"{n}{v}" for n, v in zip(names, parts[1:])) or subject


def _top(counter: Dict[str, int], n: int = TOP_REASONS) -> List[List[Any]]:
    return [[k, v] for k, v in sorted(counter.items(), key=lambda kv: -kv[1])[:n]]


# ─────────────────────────────────────────────────────────────────────────────
# RECORD SIDE
# ─────────────────────────────────────────────────────────────────────────────

def _balance(name: str, n_in: int, outs: Dict[str, int], note: str = ""
             ) -> Dict[str, Any]:
    """One balance row. `imbalance` is `in - sum(outs)`: zero is balanced and
    anything else is printed as a finding, never hidden."""
    total = sum(outs.values())
    return {"name": name, "in": n_in, "outs": dict(outs), "out_total": total,
            "imbalance": n_in - total, "balanced": n_in == total, "note": note}


def _margin_bands(values: List[float]) -> Dict[str, Any]:
    """Terciles of |margin| inside one (decider, reason, unit) group -- a
    RELATIVE band (near / middle / far), labelled so: no declared abstention
    band exists for most rules (2.106 files `band: None` itself)."""
    ab = sorted(abs(v) for v in values)
    n = len(ab)
    if not n:
        return {}
    k = -(-n // 3)                      # ceil(n/3): the size of a third
    lo, hi = ab[k - 1], ab[n - k]
    near = sum(1 for a in ab if a <= lo)
    far = sum(1 for a in ab if a >= hi and a > lo)
    return {"n": n, "tercile_lo": lo, "tercile_hi": hi,
            "near": near, "middle": n - near - far, "far": far,
            "median_abs": ab[n // 2], "min_abs": ab[0]}


def extract_facts(result: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce one loaded record (`record_io.load_record`) to a small dict.

    Everything here is counted from the record's rows by the helpers the
    exporter itself uses; see the module docstring for the list.
    """
    from . import export as E
    rec = E.Record(result)
    r = result["record"]
    obs, verdicts = r["observations"], r["verdicts"]
    facts: Dict[str, Any] = {
        "provenance": result.get("provenance") or {},
        "rows": {"observations": len(obs), "abstentions": len(r["abstentions"]),
                 "verdicts": len(verdicts)},
        "adjudication": result.get("adjudication") or {},
    }

    # ── boxes, by family ────────────────────────────────────────────────
    box_class: Dict[str, str] = {}
    boxes_by_class: Dict[str, int] = collections.Counter()
    ink_rows = 0
    for o in obs:
        q = o["quantity"]
        if q == "glyph_box":
            v = o["value"]
            name = str(v[0] if isinstance(v, (list, tuple)) else v)
            box_class[o["subject"]] = name
            boxes_by_class[name] += 1
        elif q == "ink":
            ink_rows += 1
    fam_of_class: Dict[str, Optional[str]] = {}
    for cls in boxes_by_class:
        fam_of_class[cls] = next((f for f in E.FAMILIES if E._claims(f, cls)), None)
    facts["boxes_by_class"] = dict(boxes_by_class)
    facts["boxes_total"] = sum(boxes_by_class.values())
    facts["unclaimed_ink_rows"] = ink_rows
    box_family = {s: fam_of_class.get(c) for s, c in box_class.items()}

    # ── standing verdicts, one per (quantity, subject) ──────────────────
    standing = rec._v      # the exporter's own resolution of supersession
    by_q: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for (q, _s), v in standing.items():
        by_q[q].append(v)

    guess_cache: Dict[str, Any] = {}

    def guess(sub: str):
        if sub not in guess_cache:
            guess_cache[sub] = E.guess_of(rec, sub)
        return guess_cache[sub]

    # ── 1. per-symbol funnels (glyph level) ─────────────────────────────
    def root_of(v):
        """The FIRST verdict of a chain (what ADJUDICATE said before EVALUATE
        or INFER superseded it)."""
        seen = set()
        while v.get("supersedes") and v["id"] not in seen:
            seen.add(v["id"])
            nxt = rec.verdict_by_id(v["supersedes"])
            if nxt is None:
                break
            v = nxt
        return v

    def trace_of(v) -> Dict[str, str]:
        """How one subject moved through the stages: ADJUDICATE's own outcome,
        and who settled or revised it."""
        root = root_of(v)
        rs, fs = _stage_of(root.get("decider")), _stage_of(v.get("decider"))
        t = {"adj": root["outcome"], "final": v["outcome"], "final_stage": fs}
        if v["id"] == root["id"]:
            t["move"] = "stays"
        elif root["outcome"] == "decided":
            t["move"] = f"revised by {fs}"
        elif v["outcome"] == "decided":
            t["move"] = f"settled by {fs}"
        else:
            t["move"] = f"still {v['outcome']}"
        return t

    funnels: List[Dict[str, Any]] = []
    examples: Dict[str, str] = {}
    standing_glyph_by_q: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for q, vs in by_q.items():
        standing_glyph_by_q[q] = [v for v in vs if _kind_of(v["subject"]) == "glyph"]
    assigned: Dict[str, set] = collections.defaultdict(set)
    refused_subjects: Dict[str, set] = collections.defaultdict(set)

    def tally(v, sub, name, outs, reasons, by_stage, moves, adj):
        outs[v["outcome"]] += 1
        reason = str(v.get("reason"))
        t = trace_of(v)
        adj[t["adj"]] += 1
        moves[t["move"]] += 1
        if v["outcome"] == "decided":
            by_stage[t["final_stage"]] += 1
        else:
            reasons[f'{v["outcome"]}: {reason}'] += 1
            examples.setdefault(f'{name}|{v["outcome"]}:{reason}', _key(sub))
        return t

    for name, family, refq, meanq, gloss in FUNNELS:
        boxes = [s for s, f in box_family.items() if f == family]
        refused: Dict[str, int] = collections.Counter()
        kept: List[str] = []
        for s in boxes:
            ref = rec.verdict(refq, s) if refq else None
            if ref is not None and ref["outcome"] == "decided" and ref["value"] is True:
                reason = str(ref.get("reason") or "?")
                refused[reason] += 1
                refused_subjects[meanq].add(s)
                examples.setdefault(f"{name}|refused:{reason}", _key(s))
            else:
                kept.append(s)
        mv = [v for v in standing_glyph_by_q.get(meanq, [])]
        if family in ("note", "rest"):
            def _is_rest(v):
                val = v.get("value")
                return isinstance(val, dict) and bool(val.get("is_rest"))
            orphan = [v for v in mv if v["subject"] not in box_class and
                      meanq == "duration" and (family == "rest") == _is_rest(v)]
            if meanq == "pitch":
                orphan = [v for v in mv if v["subject"] not in box_class and family == "note"]
        else:
            orphan = [v for v in mv if v["subject"] not in box_class]
        outs: Dict[str, int] = collections.Counter()
        adj: Dict[str, int] = collections.Counter()
        moves: Dict[str, int] = collections.Counter()
        reasons: Dict[str, int] = collections.Counter()
        by_stage: Dict[str, int] = collections.Counter()
        no_verdict = 0
        n_guessed = 0
        subs_with = []
        for s in kept:
            v = rec.verdict(meanq, s)
            if v is None:
                no_verdict += 1
                examples.setdefault(f"{name}|no verdict", _key(s))
                continue
            tally(v, s, name, outs, reasons, by_stage, moves, adj)
            subs_with.append(s)
            assigned[meanq].add(s)
        for v in orphan:
            tally(v, v["subject"], name, outs, reasons, by_stage, moves, adj)
            subs_with.append(v["subject"])
            assigned[meanq].add(v["subject"])
        for s in subs_with:
            v = rec.verdict(meanq, s)
            if meanq in ("duration", "pitch"):
                if guess(s) is not None:
                    n_guessed += 1
            elif _stage_of(v.get("decider")) == "INFER":
                n_guessed += 1
        n_in = len(boxes) + len(orphan)
        out_rows = {**{f"refused: {k}": n for k, n in refused.items()},
                    "decided": outs["decided"], "narrowed": outs["narrowed"],
                    "abstained": outs["abstained"], "no verdict": no_verdict}
        funnels.append({
            "name": name, "family": family, "meaning": meanq, "gloss": gloss,
            "boxes": len(boxes), "added_without_a_box": len(orphan),
            "refused": dict(refused), "refused_total": sum(refused.values()),
            "kept": len(kept),
            "decided": outs["decided"], "narrowed": outs["narrowed"],
            "abstained": outs["abstained"], "no_verdict": no_verdict,
            "adjudicate_said": dict(adj), "then": dict(moves),
            "by_stage_decided": dict(by_stage),
            "guessed_at_glyph_level": n_guessed,
            "top_reasons": _top(reasons, 8),
            "balance": _balance(name, n_in, out_rows,
                                "boxes + symbols added without a box = refused + decided + narrowed + abstained + no verdict"),
            "stage_balance": _balance(
                name + " (stage flow)", sum(adj.values()),
                {k: v for k, v in moves.items()},
                "what ADJUDICATE said about the symbols that have a verdict = how each was left after EVALUATE and INFER"),
        })
    facts["funnels"] = funnels
    facts["funnel_examples"] = examples
    # cross-check per meaning quantity: every standing GLYPH verdict is in a
    # row, or on a refused box, or on a box of a kind no row covers.
    cross = {}
    for q, vs in standing_glyph_by_q.items():
        if q not in {f[3] for f in FUNNELS}:
            continue
        in_rows = sum(1 for v in vs if v["subject"] in assigned[q])
        on_refused = sum(1 for v in vs if v["subject"] in refused_subjects[q]
                         and v["subject"] not in assigned[q])
        other = len(vs) - in_rows - on_refused
        cross[q] = _balance(f"verdicts on glyphs: {q}", len(vs),
                            {"in a row above": in_rows, "on a refused box": on_refused,
                             "on a box of a kind no row covers, or unplaced": other},
                            "every standing glyph verdict of the quantity, accounted for")
    facts["glyph_verdict_crosscheck"] = cross

    # ── 2. every quantity: decided (by stage) / narrowed / abstained ────
    quantities: Dict[str, Any] = {}
    for q, vs in sorted(by_q.items()):
        c = collections.Counter()
        stage_dec = collections.Counter()
        reasons = collections.Counter()
        first: Dict[str, str] = {}
        for v in vs:
            c[v["outcome"]] += 1
            if v["outcome"] == "decided":
                stage_dec[_stage_of(v.get("decider"))] += 1
            else:
                rk = f'{v["outcome"]}: {v.get("reason")}'
                reasons[rk] += 1
                first.setdefault(rk, _key(v["subject"]))
        quantities[q] = {"n": len(vs), "decided": c["decided"],
                         "narrowed": c["narrowed"], "abstained": c["abstained"],
                         "decided_by_stage": dict(stage_dec),
                         "top_reasons": _top(reasons, 8),
                         "example_of_reason": {k: first[k] for k, _ in _top(reasons, 8)}}
    facts["quantities"] = quantities

    # ── 3. unit-level decisions (clef, key, meter, ...) ─────────────────
    units = []
    for label, q, gloss, fam in UNIT_QUANTITIES:
        vs = by_q.get(q, [])
        cat = collections.Counter()
        adj = collections.Counter()
        moves = collections.Counter()
        reasons_by_cat: Dict[str, Dict[str, int]] = {}
        for v in vs:
            reason = str(v.get("reason"))
            t = trace_of(v)
            adj[t["adj"]] += 1
            moves[t["move"]] += 1
            if v["outcome"] == "abstained":
                k = "abstained"
            elif v["outcome"] == "narrowed":
                k = "narrowed"
            elif t["final_stage"] == "INFER":
                k = "guessed (INFER)"
            elif reason in CARRIED_REASONS:
                k = "carried"
            elif reason in READ_REASONS:
                k = "read"
            elif label in COUNT_ONLY_UNITS:
                k = "decided"
            else:
                k = "decided, other reason"
            cat[k] += 1
            reasons_by_cat.setdefault(k, collections.Counter())[reason] += 1
            if v["outcome"] != "decided":
                examples.setdefault(f"{label}|{v['outcome']}:{reason}", _key(v["subject"]))
        boxes_n = sum(n for cls, n in boxes_by_class.items() if fam and fam_of_class.get(cls) == fam)
        units.append({"name": label, "quantity": q, "gloss": gloss,
                      "boxes_for_context": boxes_n, "verdicts": len(vs),
                      "by_category": dict(cat), "adjudicate_said": dict(adj),
                      "then": dict(moves),
                      "reasons": {k: _top(dict(v), 6) for k, v in reasons_by_cat.items()},
                      "balance": _balance(label, len(vs), dict(cat)),
                      "stage_balance": _balance(label + " (stage flow)", sum(adj.values()), dict(moves))})
    facts["units"] = units

    # ── 4. guesses: rules, candidates, support gap ──────────────────────
    guessed_rules: Dict[str, int] = collections.Counter()
    cand_hist: Dict[str, int] = collections.Counter()
    gap_hist: Dict[str, int] = collections.Counter()
    bar_sum_only = 0
    guessed_total = 0
    infer_rows = [v for v in standing.values()
                  if (v.get("decider") or "").startswith("infer:")]
    for v in infer_rows:
        rule = v["decider"][len("infer:"):]
        guessed_rules[rule] += 1
        cands = v.get("candidates") or []
        cand_hist[str(len(cands))] += 1
        sup = sorted((c.get("support") or 0 for c in cands), reverse=True)
        if len(sup) >= 2:
            gap = sup[0] - sup[1]
            gap_hist["tie" if gap == 0 else ("gap 1" if gap <= 1 else "gap > 1")] += 1
        else:
            gap_hist["one candidate"] += 1
    for v in standing.values():
        if v["quantity"] == "duration" and v["outcome"] == "decided":
            g = guess(v["subject"])
            if g is not None:
                guessed_total += 1
                if g["stage"] == "EVALUATE":
                    bar_sum_only += 1
    facts["guessed"] = {
        "infer_verdicts_standing": len(infer_rows),
        "by_infer_rule": dict(guessed_rules),
        "candidates_per_infer_guess": dict(cand_hist),
        "support_gap_of_infer_guess": dict(gap_hist),
        "durations_guessed_at_glyph_level": guessed_total,
        "durations_guessed_by_the_bar_sum_only": bar_sum_only,
    }

    # ── 5. refusal margins (2.106) ──────────────────────────────────────
    groups: Dict[Tuple[str, str, str, str], List[Tuple[float, str]]] = collections.defaultdict(list)
    n_refusals = 0
    n_with_margin = 0
    for v in verdicts:
        if v["outcome"] == "decided":
            continue
        n_refusals += 1
        m = v.get("margin")
        if m is None:
            continue
        n_with_margin += 1
        det = v.get("detail") or {}
        groups[(v.get("decider") or "?", str(v.get("reason")), v["outcome"],
                str(det.get("margin_unit")))].append((float(m), v["subject"]))
    mrows = []
    for (decider, reason, outcome, unit), pairs in groups.items():
        vals = [p[0] for p in pairs]
        row = {"decider": decider, "reason": reason, "outcome": outcome,
               "unit": unit, "short_of_the_cut": sum(1 for x in vals if x < 0),
               **_margin_bands(vals)}
        closest = min(pairs, key=lambda p: abs(p[0]))
        row["closest_call"] = {"margin": closest[0], "at": _key(closest[1])}
        mrows.append(row)
    mrows.sort(key=lambda r: -r.get("n", 0))
    facts["margins"] = {"refusals_total": n_refusals,
                        "with_a_margin": n_with_margin,
                        "without_a_margin": n_refusals - n_with_margin,
                        "groups": mrows[:40]}
    return facts


def _count_outcome(v, sub, name, outs, reasons, by_stage, examples) -> None:
    outcome = v["outcome"]
    outs[outcome] += 1
    reason = str(v.get("reason"))
    if outcome == "decided":
        by_stage[_stage_of(v.get("decider"))] += 1
    else:
        reasons[f"{outcome}: {reason}"] += 1
        examples.setdefault(f"{name}|{outcome}:{reason}", _key(sub))


# ─────────────────────────────────────────────────────────────────────────────
# FILE SIDE
# ─────────────────────────────────────────────────────────────────────────────

def read_musicxml(path: Path) -> Dict[str, Any]:
    """Per part and measure: plain / blue / red items, from the file itself.

    A *blue* item is any element with `color="#1F6FEB"` (a GUESSED note, rest
    or dynamic); a *red* one carries `color="#D00000"` (UNREAD). The measure
    number is the document bar number the exporter wrote."""
    import xml.etree.ElementTree as ET
    parts: Dict[str, str] = {}
    cells: Dict[Tuple[str, int], Dict[str, int]] = {}
    seen: Dict[Tuple[str, int], int] = collections.Counter()
    ordinal = 0
    cur_part = None
    for ev, el in ET.iterparse(str(path), events=("start", "end")):
        tag = el.tag
        if ev == "end" and tag == "score-part":
            parts[el.get("id")] = (el.findtext("part-name") or el.get("id")).strip()
        elif ev == "start" and tag == "part":
            cur_part = el.get("id")
            ordinal = 0
        elif ev == "end" and tag == "measure":
            try:
                num = int(re.match(r"\d+", el.get("number") or "0").group(0))
            except Exception:                                   # noqa: BLE001
                num = -1
            ordinal += 1
            c = {"notes": 0, "rests": 0, "blue_notes": 0, "blue_other": 0,
                 "red": 0, "unread_words": 0, "number": num}
            for sub in el.iter():
                col = (sub.get("color") or "").upper()
                if sub.tag == "note":
                    if sub.find("rest") is not None:
                        c["rests"] += 1
                    else:
                        c["notes"] += 1
                    if col == GUESS_BLUE.upper():
                        c["blue_notes"] += 1
                elif sub.tag in ("words", "dynamics") and col == GUESS_BLUE.upper():
                    c["blue_other"] += 1
                if sub.tag == "words" and (sub.text or "").strip() == "unread":
                    c["unread_words"] += 1     # red since 2.103; uncoloured before
                if col == UNREAD_RED.upper():
                    c["red"] += 1
            # ⚠️ ROADMAP 2.123. A bar number can REPEAT inside one part
            # (first and second endings: Brahms 1 prints 189 and 190 twice),
            # so a bar is named by its ORDINAL -- its place among the part's
            # `<measure>` elements, the same `ordinal` the exporter files on
            # every bar list -- and the printed number is only a label.
            seen[(cur_part, num)] += 1
            c["repeat"] = seen[(cur_part, num)]
            cells[(cur_part, ordinal)] = c
            el.clear()
    return {"parts": parts,
            "cells": {f"{p}|{o}": c for (p, o), c in cells.items()},
            "repeated_bar_numbers": sorted({c["number"] for c in cells.values()
                                            if c["repeat"] > 1})}


def bar_states(cov: Dict[str, Any], mx: Dict[str, Any]) -> Dict[str, Any]:
    """Every bar of the file (parts x measures) in exactly ONE state.

    States, in priority: partial (2.117), held out because it does not add up
    (red), unread-empty (red, padded), written with guesses (blue), written
    plain. The exporter's own lists name the partial and held bars; the file
    supplies the rest. ⚠️ The derived counts are compared with the exporter's
    own totals -- a mismatch is returned, never smoothed."""
    def bid(e):
        """ROADMAP 2.123: a bar is (part, ordinal); (part, printed number)
        only for an old coverage file that carries no ordinal."""
        return (e["part"], e["ordinal"] if "ordinal" in e else e["measure"])
    partial = {bid(b) for b in
               (cov.get("partial_bars") or {}).get("bars", []) if b.get("status") == "partial"}
    held = {bid(h) for h in
            (cov.get("bars_held_out_sum") or {}).get("held", [])}
    held |= {bid(h) for h in
             (cov.get("bars_held_out_unread_mark") or {}).get("held", [])}
    held_in_partial_list = {bid(b) for b in
                            (cov.get("partial_bars") or {}).get("bars", [])
                            if b.get("status") == "held"}
    ordinal_keyed = all("ordinal" in e for e in (
        list((cov.get("partial_bars") or {}).get("bars", []))
        + list((cov.get("bars_held_out_sum") or {}).get("held", []))))
    states = collections.Counter()
    per_cell: Dict[str, str] = {}
    dup_bars = 0
    for key, c in mx["cells"].items():
        part, m = key.rsplit("|", 1)
        if c.get("repeat", 1) > 1:
            dup_bars += 1                  # a repeated printed number (labelled)
        # an old coverage file (no ordinals) can only say a bar by its number
        k2 = (part, int(m) if ordinal_keyed else c.get("number", int(m)))
        if not ordinal_keyed and c.get("repeat", 1) > 1:
            s = ("unread, repeated bar number" if c["unread_words"] else
                 "written with guesses" if (c["blue_notes"] or c["blue_other"]) else "written plain")
            states[s] += 1
            per_cell[key] = s
            continue
        if k2 in partial:
            s = "partial"
        elif k2 in held or k2 in held_in_partial_list:
            s = "held out"
        elif c["unread_words"]:
            s = "unread, empty"
        elif c["blue_notes"] or c["blue_other"]:
            s = "written with guesses"
        else:
            s = "written plain"
        states[s] += 1
        per_cell[key] = s
    # ⚠️ The exporter does not NAME a held bar on a doubled staff (the copy of
    # a condensed staff), so those red bars arrive here as "unread, empty".
    # The exporter counts them (`bars_on_a_doubled_staff`); move exactly that
    # many across -- and compare, because fewer red bars than the exporter
    # says would be a fault.
    hs = cov.get("bars_held_out_sum") or {}
    hu = cov.get("bars_held_out_unread_mark") or {}
    doubled = int(hs.get("bars_on_a_doubled_staff") or 0) + int(hu.get("bars_on_a_doubled_staff") or 0)
    moved = min(states["unread, empty"], doubled)
    states["unread, empty"] -= moved
    states["held out"] += moved
    if not states["unread, empty"]:
        del states["unread, empty"]
    ub = cov.get("unread_bar_marks") or {}
    checks = []
    exp_partial = (cov.get("partial_bars") or {}).get("written")
    if exp_partial is not None:
        checks.append(("partial bars", states["partial"], exp_partial))
    if hs.get("bars") is not None:
        checks.append(("held-out bars (named + doubled-staff copies)", states["held out"],
                       int(hs["bars"]) + int(hu.get("bars") or 0)))
    if ub.get("unread") is not None:
        checks.append(("unread-empty bars", states["unread, empty"], ub["unread"]))
    ue = (cov.get("unread_empty_bars") or {}).get("list")
    if ue is not None and ordinal_keyed:
        # ROADMAP 2.123: the exporter names each of these bars; the file's
        # bar at that ordinal must carry the red `unread` word.
        in_file = sum(1 for b in ue
                      if (mx["cells"].get(f"{b['part']}|{b['ordinal']}") or {}).get("unread_words"))
        checks.append(("unread-empty bars named by the exporter", in_file, len(ue)))
    rn = mx.get("repeated_bar_numbers") or []
    return {"states": dict(states), "total": sum(states.values()),
            "repeated_bar_numbers": rn, "bars_on_repeated_numbers": dup_bars,
            "doubled_staff_bars_not_named": moved, "cells": per_cell,
            "checks": [{"name": n + ": file vs exporter", "file": a, "exporter": b, "agrees": a == b}
                       for n, a, b in checks]}


def page_of_bar(cov: Dict[str, Any]):
    systems = (cov.get("measure_numbering") or {}).get("systems") or []
    spans = [(int(s.get("offset", 0)), int(s.get("offset", 0)) + int(s.get("bars", 0)),
              s.get("page")) for s in systems]

    def f(m: int):
        for lo, hi, page in spans:
            if lo < m <= hi:
                return page
        return None
    return f


def cleanup_proxy(cov: Dict[str, Any], mx: Dict[str, Any], st: Dict[str, Any]) -> Dict[str, Any]:
    """Red + blue items per page and per (instrument, page); and per part."""
    pg = page_of_bar(cov)
    per_page: Dict[Any, Dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    per_cell: Dict[Tuple[str, Any], Dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    per_part: Dict[str, Dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    names = dict(mx["parts"])
    counts = collections.Counter(names.values())
    names = {pid: (nm if counts[nm] == 1 else f"{nm} [{pid}]") for pid, nm in names.items()}
    for key, c in mx["cells"].items():
        part, m = key.rsplit("|", 1)
        page = pg(int(c.get("number", m)))
        red = c["unread_words"]
        blue = c["blue_notes"] + c["blue_other"]
        for d in (per_page[page], per_cell[(names.get(part, part), page)]):
            d["red"] += red
            d["blue"] += blue
            d["items"] += red + blue
        p = per_part[names.get(part, part)]
        p["notes_plain"] += c["notes"] - c["blue_notes"]
        p["notes_guessed"] += c["blue_notes"]
        p["rests"] += c["rests"]
        p["unread_marks"] += red
        s = st["cells"].get(key)
        p["bars_" + s.replace(" ", "_").replace(",", "")] += 1 if s else 0
    # events not written, by part, from the exporter's own held / partial lists
    for h in (cov.get("bars_held_out_sum") or {}).get("held", []):
        nm = names.get(h["part"], h["part"])
        per_part[nm]["events_held_out"] += int(h.get("noteheads_and_rests") or 0)
    for b in (cov.get("partial_bars") or {}).get("bars", []):
        if b.get("status") == "partial":
            nm = names.get(b["part"], b["part"])
            per_part[nm]["rows_in_unread_gaps"] += int(b.get("rows_in_gap") or 0)
    worst_pages = sorted(per_page.items(), key=lambda kv: -kv[1]["items"])[:5]
    worst_cells = sorted(per_cell.items(), key=lambda kv: -kv[1]["items"])[:5]
    return {
        "per_page": {str(k): dict(v) for k, v in sorted(per_page.items(), key=lambda kv: (kv[0] is None, kv[0]))},
        "worst_pages": [{"page": k, **dict(v)} for k, v in worst_pages],
        "worst_staves": [{"instrument": k[0], "page": k[1], **dict(v)} for k, v in worst_cells],
        "per_part": {k: dict(v) for k, v in per_part.items()},
        "items_total": sum(v["items"] for v in per_page.values()),
        "pages": len(per_page),
    }


# ─────────────────────────────────────────────────────────────────────────────
# THE REPORT
# ─────────────────────────────────────────────────────────────────────────────

def load_export_report(path: Path, doc: Optional[str] = None) -> Dict[str, Any]:
    """`export --coverage` output, or `current.json` (then `doc` picks the
    movement). Either way: the exporter's own report dict."""
    d = json.loads(Path(path).read_text())
    if "documents" in d:
        return d["documents"][doc]["export"]["report"]
    return d.get("report", d)


def export_side(cov: Dict[str, Any]) -> Dict[str, Any]:
    """The EXPORT step, taken from the exporter's report (nothing recounted)."""
    g = cov.get("guessed") or {}
    w = cov.get("written") or {}
    fams = {r["family"]: r for r in cov.get("families", [])}
    rows = []
    guessed_of = {"note": g.get("notes", 0), "rest": g.get("rests", 0),
                  "dynamic": g.get("dynamics", 0)}
    for f, r in sorted(fams.items()):
        gu = guessed_of.get(f)
        rows.append({"family": f, "ink_rows": r.get("detector_glyphs"), "cv_rows": r.get("cv_glyphs"), "decided": r.get("decided"),
                     "abstained": sum((r.get("abstained") or {}).values()),
                     "written": r.get("written"),
                     "of_which_guessed_blue": gu,
                     "status": r.get("status")})
    bal = cov.get("balance") or {}
    ev = {
        "name": "notes and rests (events)",
        "in": bal.get("events_in_log"),
        "plus_added": int(bal.get("unboxed_rests_placed") or 0),
        "doubled_to_condensed_slot": bal.get("notes_doubled_to_condensed_slot"),
        "rests_duplicated_across_voices": bal.get("rests_duplicated_across_voices"),
        "written": bal.get("events_written"),
        "not_written": bal.get("events_not_written"),
        "relocated": bal.get("relocated_heads_written", 0),
    }
    if bal.get("events_in_log") is not None:
        ev["balance"] = _balance(
            "export: events in the log -> file",
            int(bal["events_in_log"]) + ev["plus_added"],
            {"written": int(bal.get("events_written") or 0),
             "not written (reasons below)": int(bal.get("events_not_written") or 0)},
            "events in the log + rests read off unboxed ink = events written (net of doubled and duplicated copies) + events not written; the exporter's own `balance`, re-checked here")
    other_balances = []
    for k in sorted(cov):
        if k.endswith("_balance") and isinstance(cov[k], dict):
            other_balances.append({"name": k, "balanced_as_reported": cov[k].get("balanced"),
                                   "detail": {a: b for a, b in cov[k].items() if isinstance(b, (int, float)) and not isinstance(b, bool)}})
    fr = {}
    for q, d in (cov.get("family_refusals") or {}).items():
        if isinstance(d, dict):
            fr[q] = {"kept": d.get("kept"), "refused": d.get("refused_total"),
                     "abstained": d.get("abstained"),
                     "refused_reasons": d.get("refused") or {}}
    return {"families": rows, "events": ev, "family_refusals": fr,
            "not_written_reasons": cov.get("notes_not_written") or {},
            "arcs_not_written": cov.get("arcs_not_written") or {},
            "other_balances": other_balances,
            "status_census_balanced": (cov.get("status_census") or {}).get("balanced")}


def build_report(facts: Dict[str, Any], cov: Dict[str, Any], mx: Optional[Dict[str, Any]],
                 label: str, run: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One movement's report as a dict (the JSON beside the Markdown)."""
    rep: Dict[str, Any] = {"label": label, "run": run or {}}
    rep["provenance"] = facts.get("provenance", {})
    ex = export_side(cov)
    rep["export"] = ex
    # ── bars ───────────────────────────────────────────────────────────
    st = bar_states(cov, mx) if mx else None
    ub = cov.get("unread_bar_marks") or {}
    pb = cov.get("partial_bars") or {}
    bars = {
        "total_bars_in_file": st["total"] if st else None,
        "bars_with_notes_from_the_page": (cov.get("bars_held_out_sum") or {}).get("of_bars_with_events"),
        "held_out_does_not_add_up": (cov.get("bars_held_out_sum") or {}).get("bars"),
        "held_out_unread_mark": (cov.get("bars_held_out_unread_mark") or {}).get("bars"),
        "partial_bars": pb.get("written") if pb else None,
        "partial_bars_stay_held_by_reason": pb.get("stay_held_by_reason") if pb else None,
        "unread_empty_padded": ub.get("unread"),
        "tacet_bars_padded_with_rests": (cov.get("tacet_padding") or {}).get("bars_padded"),
        "unread_marks_in_file": ub.get("written"),
        "meter_carried": (cov.get("bars_held_out_sum") or {}).get("bars_judged_by_a_carried_meter"),
        "meter_missing": (cov.get("bars_held_out_sum") or {}).get("bars_with_events_without_a_meter"),
        "states_from_the_file": st["states"] if st else None,
        "states_checks": st["checks"] if st else None,
        "repeated_bar_numbers": st["repeated_bar_numbers"] if st else None,
        "bars_on_repeated_numbers": st["bars_on_repeated_numbers"] if st else None,
    }
    hold_reasons: Dict[str, int] = collections.Counter()
    for h in (cov.get("bars_held_out_sum") or {}).get("held", []):
        hold_reasons["does not add up"] += 1
    bars["held_out_by_reason"] = {k: v for k, v in hold_reasons.items()}
    rep["bars"] = bars
    if st:
        mrows = [("bars: every bar of the file in one state", st["total"], dict(st["states"]))]
        rep["bar_balance"] = _balance("bars", st["total"], dict(st["states"]),
                                      "parts x measures in the MusicXML = the bar states")
    rep["unread_marks"] = {"red_marks_written": ub.get("written"),
                           "empty": ub.get("unread"), "held_out_sum": ub.get("held_out_sum"),
                           "held_out_unread_mark": ub.get("held_out_unread_mark"),
                           "partial_gaps_marked": ub.get("partial"),
                           "unread_gaps_written": (cov.get("written") or {}).get("unread_gaps_written"),
                           "equation": {"empty + held_out + partial": (ub.get("unread") or 0) +
                                        (ub.get("held_out_sum") or 0) + (ub.get("partial") or 0),
                                        "written": ub.get("written")}}
    rep["unread_marks"]["balanced"] = (rep["unread_marks"]["equation"]["empty + held_out + partial"] ==
                                       rep["unread_marks"]["equation"]["written"])
    # ── symbols ────────────────────────────────────────────────────────
    rep["funnels"] = facts.get("funnels", [])
    rep["units"] = facts.get("units", [])
    rep["quantities"] = facts.get("quantities", {})
    rep["glyph_verdict_crosscheck"] = facts.get("glyph_verdict_crosscheck", {})
    # cross-check: the record's refusals against the exporter's drops
    rep["refusals_vs_export_drops"] = _refusal_crosscheck(facts, cov)
    # ── guesses ────────────────────────────────────────────────────────
    gd = cov.get("guessed") or {}
    by_rule = dict(gd.get("by_rule") or {})
    partial_blue = {k: by_rule.pop(k) for k in list(by_rule) if k.startswith("onset_from_partial_bar_")}
    rep["guessed"] = {
        "written_blue": {"notes": gd.get("notes"), "rests": gd.get("rests"),
                         "dynamics": gd.get("dynamics"), "total": gd.get("total")},
        "by_rule_other": by_rule,
        "kept_notes_in_partial_bars_blue": partial_blue,
        "record": facts.get("guessed", {}),
        "margins": facts.get("margins", {}),
    }
    # ── unknown / unread in one place ──────────────────────────────────
    nw = cov.get("notes_not_written") or {}
    pj = cov.get("part_join") or {}
    rep["unknown"] = {
        "unread_marks_red": ub.get("written"),
        "staves_held_out_unidentified": pj.get("held_out_staves"),
        "unidentified_parts": len(pj.get("unidentified_parts") or []),
        "noteheads_staff_not_identified": nw.get("staff_not_identified"),
        "noteheads_owner_not_read": nw.get("owner_not_read"),
        "noteheads_no_pitch": nw.get("no_pitch"),
        "notes_whose_length_is_undecided": {"narrowed": nw.get("duration_narrowed"),
                                            "rest abstained": nw.get("rest_duration_abstained"),
                                            "chord undecided": nw.get("chord_value_undecided")},
        "adjudication_missing_evidence": (facts.get("adjudication") or {}).get("missing_evidence"),
    }
    # ── definition of done ─────────────────────────────────────────────
    rep["definition_of_done"] = _dod(facts, cov, run or {})
    # ── detected then dropped ──────────────────────────────────────────
    rep["detected_then_dropped"] = {
        "classes_no_family_reads": cov.get("unclaimed_classes") or {},
        "detected_and_unrepresented": cov.get("detected_and_unrepresented") or {},
        "decided_and_unwritten": cov.get("decided_and_unwritten") or {},
        "unexplained_ink_rows_Q_INK": facts.get("unclaimed_ink_rows"),
        "boxes_total": facts.get("boxes_total"),
    }
    # ── cleanup cost ───────────────────────────────────────────────────
    if mx:
        rep["cleanup"] = cleanup_proxy(cov, mx, st)
    rep["examples"] = _examples(facts, cov)
    return rep


def _refusal_crosscheck(facts, cov) -> List[Dict[str, Any]]:
    """RECORD refusals (an `X_is_not_a_X` verdict) against the EXPORTER's drop
    reasons of the same name: two counts of one fact, from two stages."""
    nw = cov.get("notes_not_written") or {}
    out = []
    rec_ref = collections.Counter()
    for f in facts.get("funnels", []):
        if f["meaning"] in ("duration",):
            for k, n in f["refused"].items():
                pre = "not_a_rest:" if f["family"] == "rest" else "not_a_notehead:"
                rec_ref[pre + k] += n
    for k, n in sorted(rec_ref.items()):
        e = nw.get(k, 0)
        # ROADMAP 2.122: a refused box that ADJUDICATE then read as an eighth
        # rest is WRITTEN (as a rest), so it is in `refusals_reinstated`, not
        # in the drops. The record's refusals = dropped + reinstated.
        r = ((cov.get("part_join") or {}).get("refusals_reinstated") or {}) \
            .get("refused_then_read_as_rest", {}).get(k, 0)
        out.append({"reason": k, "record_refused": n, "export_dropped": e,
                    "export_read_as_rest": r, "agrees": n == e + r})
    return out


def _dod(facts, cov, run) -> Dict[str, Any]:
    pj = cov.get("part_join") or {}
    units = {u["name"]: u for u in facts.get("units", [])}
    inst = units.get("instrument names", {}).get("by_category", {})
    d = {
        "staves_named": inst.get("read", 0) + inst.get("carried", 0) + inst.get("decided, other reason", 0),
        "staves_not_named_abstained": inst.get("abstained", 0),
        "staves_held_out": pj.get("held_out_staves"),
        "parts_in_file": (cov.get("written") or {}).get("parts"),
        "clefs": units.get("clefs", {}).get("by_category"),
        "keys": units.get("key signatures", {}).get("by_category"),
        "meters": units.get("meters (time signatures)", {}).get("by_category"),
        "inferred_clefs": len(cov.get("inferred_clefs") or []),
        "unread_marks": (cov.get("unread_bar_marks") or {}).get("written"),
        "musicxml": run.get("musicxml"),
        "lilypond": run.get("lilypond"),
    }
    return d


def _examples(facts, cov) -> List[Dict[str, Any]]:
    """The top ~8 refusal / hold-out reasons, each with ONE address a crop can
    be cut from (no crops are cut here)."""
    rows: List[Tuple[int, str, str, str]] = []
    for f in facts.get("funnels", []):
        for k, n in f["refused"].items():
            if f["meaning"] == "pitch":
                continue                    # same boxes as the length row
            rows.append((n, f"{f['name']}: refused, {k}",
                         facts["funnel_examples"].get(f"{f['name']}|refused:{k}", "?"), "record"))
        for rk, n in f["top_reasons"]:
            outcome, _, reason = rk.partition(": ")
            rows.append((n, f"{f['name']}: {rk}",
                         facts["funnel_examples"].get(f"{f['name']}|{outcome}:{reason}", "?"), "record"))
    held = (cov.get("bars_held_out_sum") or {}).get("held") or []
    if held:
        h = held[0]
        rows.append((len(held), "bar held out: does not add up",
                     f"p{h['page']} sys{h['system']} staff{h['staff']} cell{h['cell']} (bar {h['measure']}, part {h['part']})",
                     "export"))
    pb = cov.get("partial_bars") or {}
    seen = set()
    for b in pb.get("bars", []):
        if b.get("status") == "held" and b.get("why") not in seen:
            seen.add(b["why"])
            n = (pb.get("stay_held_by_reason") or {}).get(b["why"], 0)
            rows.append((n, f"bar stays held: {b['why']}",
                         f"p{b['page']} sys{b['system']} staff{b['staff']} cell{b['cell']} (bar {b['measure']}, part {b['part']})",
                         "export"))
    rows.sort(key=lambda r: -r[0])
    return [{"count": n, "reason": r, "example": e, "source": s} for n, r, e, s in rows[:10]]


# ─────────────────────────────────────────────────────────────────────────────
# NIGHT OVER NIGHT
# ─────────────────────────────────────────────────────────────────────────────

def flatten(rep: Dict[str, Any]) -> Dict[str, float]:
    """Every NUMBER in the report under a readable path -- the deltas' input."""
    out: Dict[str, float] = {}

    def put(path, v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            out[path] = v

    b = rep.get("bars", {})
    for k in ("total_bars_in_file", "partial_bars",
              "unread_empty_padded", "tacet_bars_padded_with_rests", "unread_marks_in_file"):
        put(f"bars / {k.replace('_', ' ')}", b.get(k))
    for k, v in (b.get("states_from_the_file") or {}).items():
        put(f"bars / {k}", v)
    for f in rep.get("funnels", []):
        n = f["name"]
        for k in ("boxes", "added_without_a_box", "refused_total", "decided", "narrowed",
                  "abstained", "no_verdict", "guessed_at_glyph_level"):
            put(f"{n} / {k.replace('_', ' ')}", f.get(k))
        for k, v in f["refused"].items():
            put(f"{n} / refused: {k}", v)
    for fam in rep.get("export", {}).get("families", []):
        put(f"export {fam['family']} / written", fam.get("written"))
    for k, v in (rep.get("export", {}).get("not_written_reasons") or {}).items():
        put(f"export not written / {k}", v)
    g = rep.get("guessed", {})
    for k, v in (g.get("written_blue") or {}).items():
        put(f"blue guessed / {k}", v)
    for k, v in (g.get("by_rule_other") or {}).items():
        put(f"blue guessed by rule / {k}", v)
    for k, v in (g.get("kept_notes_in_partial_bars_blue") or {}).items():
        put(f"blue kept in partial bars / {k}", v)
    for u in rep.get("units", []):
        for k, v in u["by_category"].items():
            put(f"{u['name']} / {k}", v)
    u = rep.get("unknown", {})
    for k in ("staves_held_out_unidentified", "noteheads_staff_not_identified",
              "noteheads_owner_not_read", "noteheads_no_pitch"):
        put(f"unknown / {k.replace('_', ' ')}", u.get(k))
    for k, v in (rep.get("detected_then_dropped", {}).get("classes_no_family_reads") or {}).items():
        put(f"detected, no family reads / {k}", v)
    return out


def movers(cur: Dict[str, float], prev: Dict[str, float], n: int = 10,
           min_base: int = 20) -> List[Dict[str, Any]]:
    """The n largest night-over-night changes. Ranked by size of the change
    relative to the larger of the two values (so a 20 -> 80 outranks a
    10,000 -> 10,030), among rows big enough to mean something."""
    rows = []
    for k in set(cur) | set(prev):
        a, b = cur.get(k), prev.get(k)
        if a is None or b is None or a == b:
            continue
        big = max(abs(a), abs(b))
        if big < min_base:
            continue
        rows.append({"row": k, "was": b, "now": a, "delta": a - b,
                     "relative": abs(a - b) / big})
    rows.sort(key=lambda r: (-r["relative"] * min(1.0, max(abs(r["was"]), abs(r["now"])) / 300), -abs(r["delta"])))
    return rows[:n]


# ─────────────────────────────────────────────────────────────────────────────
# MARKDOWN
# ─────────────────────────────────────────────────────────────────────────────

def _d(cur, prev) -> str:
    """`cur (+3)` -- the number with its night-over-night change."""
    if cur is None:
        return "n/a"
    if prev is None:
        return f"{cur:,}" if isinstance(cur, int) else f"{cur}"
    try:
        dl = cur - prev
    except TypeError:
        return str(cur)
    s = f"{cur:,}" if isinstance(cur, int) else f"{cur}"
    return s if dl == 0 else f"{s} ({'+' if dl > 0 else ''}{dl:,})"


def render_md(rep: Dict[str, Any], prev: Optional[Dict[str, Any]] = None) -> str:
    P = prev or {}
    L: List[str] = []
    a = L.append
    pf, pc = flatten(rep), flatten(P) if P else {}

    def g(path, key):                       # previous night's value at a path
        d = P
        for p in path:
            d = (d or {}).get(p) if isinstance(d, dict) else None
        return (d or {}).get(key) if isinstance(d, dict) else None

    run = rep.get("run", {})
    prun = P.get("run", {}) if P else {}
    a(f"# Re-gather report: {rep['label']}")
    a("")
    a("Every number below is read off the saved record, the exporter's own report or the MusicXML "
      "(sources named in `tools/omr/staged/regather_report.py`). "
      "A figure in brackets such as `(+12)` is the change since the previous night"
      + (f" ({P.get('label')})" if P else "") + ". "
      "**IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.")
    a("")
    a("## 0. One screen")
    a("")
    a("### Run")
    a("")
    for k, label in (("tree", "tree"), ("landings", "landings since the previous night"),
                     ("flags", "flags/settings that differ from defaults"), ("weights", "weights"),
                     ("pages", "pages"), ("wall", "wall time")):
        v = run.get(k)
        if v in (None, "", []):
            continue
        if isinstance(v, list):
            a(f"- **{label}**:")
            for x in v[:40]:
                a(f"  - {x}")
            if len(v) > 40:
                a(f"  - ... and {len(v) - 40} more")
        else:
            a(f"- **{label}**: {v}" + (f" (previous: {prun.get(k)})" if prun.get(k) and prun.get(k) != v else ""))
    a("")
    a("### Definition of done (one command, a whole movement, nothing invented)")
    a("")
    dod = rep["definition_of_done"]
    pdod = (P.get("definition_of_done") or {}) if P else {}
    a("| question | this night | previous |")
    a("|---|---|---|")
    a(f"| parts in the file | {dod['parts_in_file']} | {pdod.get('parts_in_file', 'n/a')} |")
    a(f"| staves named (staff rows over all systems) | {dod['staves_named']} (not named: {dod['staves_not_named_abstained']}) | "
      f"{pdod.get('staves_named', 'n/a')} (not named: {pdod.get('staves_not_named_abstained', 'n/a')}) |")
    a(f"| staves held out (counted, not placed in a part) | {dod['staves_held_out']} | {pdod.get('staves_held_out', 'n/a')} |")
    for key, label in (("meters", "meter, per system"), ("keys", "key, per staff and system"),
                       ("clefs", "clef, per staff and system")):
        a(f"| {label}: read / carried / guessed / narrowed / abstained | {_cat(dod.get(key))} | {_cat(pdod.get(key)) if P else 'n/a'} |")
    a(f"| bars marked unread (red) | {_d(dod['unread_marks'], pdod.get('unread_marks'))} | |")
    mx_ = dod.get("musicxml") or {}
    ly_ = dod.get("lilypond") or {}
    a(f"| MusicXML written | {mx_.get('status', 'n/a')} {mx_.get('detail', '')} | {((pdod.get('musicxml') or {}).get('status', 'n/a'))} |")
    a(f"| LilyPond written / compiled / warnings | {_ly(ly_)} | {_ly(pdod.get('lilypond') or {}) if P else 'n/a'} |")
    a("")
    if pc:
        a("### Biggest movers since the previous night")
        a("")
        a("| row | was | now | change |")
        a("|---|---|---|---|")
        for m in movers(pf, pc):
            a(f"| {m['row']} | {m['was']:,} | {m['now']:,} | {m['delta']:+,} |")
        a("")
    # ── 1. bars ──
    a("## 1. Bars")
    a("")
    b = rep["bars"]
    pb_ = P.get("bars", {}) if P else {}
    a("A bar is one measure of one part. Each bar of the file is in exactly one state.")
    a("")
    a("| state | bars | plain words |")
    a("|---|---|---|")
    st = b.get("states_from_the_file") or {}
    pst = pb_.get("states_from_the_file") or {}
    glossary = {"written plain": "all notes written, none guessed",
                "written with guesses": "written; at least one note/dynamic is a guess (blue)",
                "partial": "kept in part: readable notes written, the unreadable gap marked red (2.117)",
                "held out": "notes held back because the bar does not add up; red mark (not written)",
                "unread, empty": "nothing read in this bar; padded and marked red"}
    glossary["unread, repeated bar number"] = ("red mark on a bar whose number repeats (first/second ending): "
                                                "cannot be matched to the exporter's lists")
    for s in ("written plain", "written with guesses", "partial", "held out", "unread, empty",
              "unread, repeated bar number"):
        if s == "unread, repeated bar number" and not st.get(s) and not pst.get(s):
            continue
        a(f"| {s} | {_d(st.get(s), pst.get(s) if P else None)} | {glossary[s]} |")
    a(f"| **total bars (parts x measures)** | {_d(b.get('total_bars_in_file'), pb_.get('total_bars_in_file') if P else None)} | |")
    bb = rep.get("bar_balance")
    if bb:
        a("")
        a(_bal_line(bb))
    if b.get("repeated_bar_numbers"):
        a(f"- bar numbers that repeat inside a part (endings): {b['repeated_bar_numbers']}; "
          f"{b.get('bars_on_repeated_numbers')} bars sit on them. The exporter's held/partial lists are keyed by bar number, "
          f"so they cannot tell the two apart.")
    for c in b.get("states_checks") or []:
        a(f"- check, {c['name']}: file {c['file']}, exporter {c['exporter']} -> {'agrees' if c['agrees'] else '**IMBALANCE**'}")
    a("")
    a(f"Bars with notes read off the page: {_d(b.get('bars_with_notes_from_the_page'), pb_.get('bars_with_notes_from_the_page') if P else None)}. "
      f"Tacet bars padded with rests (written, not unread): {_d(b.get('tacet_bars_padded_with_rests'), pb_.get('tacet_bars_padded_with_rests') if P else None)}. "
      f"Meter: {b.get('meter_carried')} bars judged on a carried meter, {b.get('meter_missing')} with notes and no meter.")
    if b.get("partial_bars_stay_held_by_reason"):
        a("")
        a("Bars that could have been partial but stay held, by reason: " +
          ", ".join(f"{k} {v}" for k, v in b["partial_bars_stay_held_by_reason"].items()) + ".")
    um = rep["unread_marks"]
    a("")
    a(f"Red marks written: {um['red_marks_written']}. Equation: empty {um['empty']} + held out {um['held_out_sum']} + "
      f"partial {um['partial_gaps_marked']} = {um['equation']['empty + held_out + partial']} "
      f"(the partial bars carry {um['unread_gaps_written']} red bracketed gaps) "
      f"-> {'balanced' if um['balanced'] else '**IMBALANCE**'}.")
    a("")
    # ── 2. symbols ──
    a("## 2. Symbols: what happens to each kind at each stage")
    a("")
    a("GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it "
      "mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the "
      "ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.")
    a("")
    a("### 2a. Per symbol kind, at glyph level (computed here from the record)")
    a("")
    a("| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |")
    a("|---|---|---|---|---|---|---|---|---|")
    pf_ = {f["name"]: f for f in P.get("funnels", [])} if P else {}
    for f in rep["funnels"]:
        p = pf_.get(f["name"], {})
        bal = f["balance"]
        a(f"| {f['name']} | {_d(f['boxes'], p.get('boxes'))}{' +' + str(f['added_without_a_box']) if f['added_without_a_box'] else ''} | "
          f"{_d(f['refused_total'], p.get('refused_total'))} | {_d(f['decided'], p.get('decided'))} | "
          f"{_d(f['narrowed'], p.get('narrowed'))} | {_d(f['abstained'], p.get('abstained'))} | "
          f"{_d(f['no_verdict'], p.get('no_verdict'))} | {_d(f['guessed_at_glyph_level'], p.get('guessed_at_glyph_level'))} | "
          f"{'balanced' if bal['balanced'] else '**IMBALANCE ' + format(bal['imbalance'], '+') + '**'} |")
    a("")
    a("Is-it-really-one refusals for every family, from the exporter's own `family_refusals` (kept / refused / abstained):")
    a("")
    for q, d in (rep["export"].get("family_refusals") or {}).items():
        rr = ", ".join(f"{k} {v}" for k, v in sorted(d["refused_reasons"].items(), key=lambda kv: -kv[1])[:3])
        a(f"- {q}: kept {d['kept']:,}, refused {d['refused']:,}, abstained {d['abstained']:,}" + (f" ({rr})" if rr else ""))
    a("")
    a("Top reasons per kind (refused, narrowed, abstained):")
    a("")
    for f in rep["funnels"]:
        parts = [f"refused {k} {n}" for k, n in sorted(f["refused"].items(), key=lambda kv: -kv[1])[:3]]
        parts += [f"{k} {n}" for k, n in f["top_reasons"][:4]]
        if parts:
            a(f"- **{f['name']}** ({f['gloss']}): " + "; ".join(parts))
    a("")
    a("### 2b. Readings that belong to a staff or system, not to one box")
    a("")
    a("| reading | boxes | verdicts | read | carried | guessed (INFER) | decided (yes/no) | narrowed | abstained | other | balance |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    pu = {u["name"]: u for u in P.get("units", [])} if P else {}
    for u in rep["units"]:
        c = u["by_category"]
        pc_ = (pu.get(u["name"]) or {}).get("by_category", {})
        a(f"| {u['name']} ({u['gloss']}) | {u['boxes_for_context']:,} | {u['verdicts']:,} | " +
          " | ".join(_d(c.get(k, 0), pc_.get(k, 0) if pu else None) for k in
                     ("read", "carried", "guessed (INFER)", "decided", "narrowed", "abstained", "decided, other reason")) +
          f" | {'balanced' if u['balance']['balanced'] else '**IMBALANCE**'} |")
    a("")
    a("### 2c. EXPORT: what reached the file (the exporter's own report)")
    a("")
    ex = rep["export"]
    pex = {r['family']: r for r in P.get("export", {}).get("families", [])} if P else {}
    a("| family | detector boxes | decided | abstained | written to the file | of which guessed (blue) | exporter status |")
    a("|---|---|---|---|---|---|---|")
    for r in ex["families"]:
        p = pex.get(r["family"], {})
        a(f"| {r['family']} | {_d(r['ink_rows'], p.get('ink_rows'))} | {_d(r['decided'], p.get('decided'))} | "
          f"{_d(r['abstained'], p.get('abstained'))} | {_d(r['written'], p.get('written'))} | "
          f"{r['of_which_guessed_blue'] if r['of_which_guessed_blue'] is not None else 'n/a'} | {r['status']} |")
    a("")
    a("")
    a("(`rest` reads 'abstained' only because the exporter has no separate rest verdict; rests are read, see 2a. "
      "`decided` counts verdicts, which can exceed boxes where one box has several.)")
    a("")
    ev = ex["events"]
    if ev.get("balance"):
        a(_bal_line(ev["balance"]))
        a(f"(Of the written events, {ev.get('doubled_to_condensed_slot')} notes were doubled onto a condensed slot and "
          f"{ev.get('rests_duplicated_across_voices')} rests duplicated across voices; the exporter nets those out.)")
    a("")
    nwr = ex["not_written_reasons"]
    if nwr:
        pn = P.get("export", {}).get("not_written_reasons", {}) if P else {}
        a("Notes and rests not written, by reason (top 12):")
        a("")
        for k, v in sorted(nwr.items(), key=lambda kv: -kv[1])[:12]:
            a(f"- {k}: {_d(v, pn.get(k) if P else None)}")
        a("")
    rc_ = [r for r in rep["refusals_vs_export_drops"] if r["record_refused"] or r["export_dropped"]]
    bad_r = [r for r in rc_ if not r["agrees"]]
    a(f"Two stages, one fact: the record's refusals (ADJUDICATE) against the exporter's drop reasons of the same name: "
      f"{len(rc_) - len(bad_r)} of {len(rc_)} reasons agree exactly.")
    for r in bad_r:
        a(f"- {r['reason']}: record {r['record_refused']}, exporter {r['export_dropped']} -> **IMBALANCE {r['export_dropped'] - r['record_refused']:+}**")
    a("")
    xs = rep.get("glyph_verdict_crosscheck") or {}
    bad_x = [r for r in xs.values() if not r["balanced"]]
    a(f"Every standing glyph verdict of the quantities above is in a row, on a refused box, or on a box of a kind "
      f"no row covers: {len(xs) - len(bad_x)} of {len(xs)} quantities account for all their verdicts.")
    for q, r in xs.items():
        o = r["outs"]
        if o.get("on a box of a kind no row covers, or unplaced"):
            a(f"- {q}: {o['on a box of a kind no row covers, or unplaced']:,} of {r['in']:,} verdicts sit on boxes of another kind "
              f"(e.g. a pitch computed for a rest box) -- listed, not hidden")
    for r in bad_x:
        a(_bal_line(r))
    nov = [f for f in rep["funnels"] if f["no_verdict"]]
    if nov:
        a("")
        a("Kept boxes that nothing was asked about (no verdict): " + "; ".join(
            f"{f['name']} {f['no_verdict']:,}" for f in nov) + ".")
    a("")
    # ── 3. certainty ──
    a("## 3. How sure are the guesses")
    a("")
    gs = rep["guessed"]
    pgs = P.get("guessed", {}) if P else {}
    wb = gs["written_blue"]
    pwb = pgs.get("written_blue", {}) if P else {}
    a(f"Blue items written: **{_d(wb['total'], pwb.get('total'))}** (notes {_d(wb['notes'], pwb.get('notes'))}, "
      f"rests {_d(wb['rests'], pwb.get('rests'))}, dynamics {_d(wb['dynamics'], pwb.get('dynamics'))}). By the rule that guessed:")
    a("")
    for k, v in sorted(gs["by_rule_other"].items(), key=lambda kv: -kv[1]):
        a(f"- {k}: {_d(v, (pgs.get('by_rule_other') or {}).get(k) if P else None)} {_gloss_rule(k)}")
    if gs["kept_notes_in_partial_bars_blue"]:
        a("")
        a("Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the "
          "readable notes either side of an unread gap):")
        a("")
        for k, v in gs["kept_notes_in_partial_bars_blue"].items():
            a(f"- {k}: {_d(v, (pgs.get('kept_notes_in_partial_bars_blue') or {}).get(k) if P else None)}")
    rg = gs["record"]
    a("")
    a(f"Of the guesses INFER made (record): {rg.get('infer_verdicts_standing')} standing. Candidates it chose between: "
      f"{rg.get('candidates_per_infer_guess')}. Evidence gap between the chosen candidate and the runner-up: "
      f"{rg.get('support_gap_of_infer_guess')} ('tie' = the chosen value had no more support than another).")
    a(f"Durations that are guesses at glyph level: {rg.get('durations_guessed_at_glyph_level')}; "
      f"of those, settled by the bar's arithmetic alone (the weakest witness): {rg.get('durations_guessed_by_the_bar_sum_only')}.")
    a("")
    mg = gs["margins"]
    a(f"**Refusals and how close they came** (2.106): {mg.get('refusals_total')} refusals/narrowings in the record, "
      f"{mg.get('with_a_margin')} carry a margin, **{mg.get('without_a_margin')} carry none** (rules not yet covered, or "
      f"structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, "
      f"since most rules declare no band). Biggest groups:")
    a("")
    a("| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |")
    a("|---|---|---|---|---|---|---|---|---|")
    for r in (mg.get("groups") or [])[:12]:
        cc = r.get("closest_call") or {}
        a(f"| {r['decider'].replace('adjudicate_', '')} | {r['reason']} | {r['outcome']} | {r.get('n')} | "
          f"{r.get('short_of_the_cut')} | {r.get('near')} | {r.get('middle')} | {r.get('far')} | {cc.get('margin'):.3g} at {cc.get('at')} |")
    a("")
    # ── 4. unknown ──
    a("## 4. Unknown and unread, in one place")
    a("")
    un = rep["unknown"]
    pun = P.get("unknown", {}) if P else {}
    for k, v in un.items():
        if k in ("adjudication_missing_evidence", "notes_whose_length_is_undecided"):
            continue
        if isinstance(v, (int, float)):
            a(f"- {k.replace('_', ' ')}: {_d(v, pun.get(k) if P else None)}")
    nu = un.get("notes_whose_length_is_undecided") or {}
    a(f"- notes whose length stayed undecided (narrowed, abstained, chord): {nu}")
    me = un.get("adjudication_missing_evidence") or {}
    top = sorted(me.items(), key=lambda kv: -kv[1])[:8]
    a("- evidence the deciders asked for and did not find (record `adjudication.missing_evidence`, top 8): " +
      ", ".join(f"{k} {v:,}" for k, v in top))
    a("")
    # ── 5. cleanup ──
    if rep.get("cleanup"):
        cl = rep["cleanup"]
        a("## 5. Where the fixing time goes")
        a("")
        a(f"Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: {cl['items_total']:,} over {cl['pages']} pages "
          f"(about {cl['items_total'] / max(cl['pages'], 1):.0f} per page). Previous: "
          f"{(P.get('cleanup') or {}).get('items_total', 'n/a') if P else 'n/a'}.")
        a("")
        a("Five worst pages: " + "; ".join(f"p{w['page']}: {w['red']} red + {w['blue']} blue" for w in cl["worst_pages"]) + ".")
        a("")
        a("Five worst staves (instrument, page): " + "; ".join(
            f"{w['instrument']} p{w['page']}: {w['red']} red + {w['blue']} blue" for w in cl["worst_staves"]) + ".")
        a("")
        a("Per instrument (part):")
        a("")
        a("| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |")
        a("|---|---|---|---|---|---|")
        pp = (P.get("cleanup") or {}).get("per_part", {}) if P else {}
        for nm, v in sorted(cl["per_part"].items(), key=lambda kv: -(kv[1].get("unread_marks", 0) + kv[1].get("notes_guessed", 0))):
            p = pp.get(nm, {})
            a(f"| {nm} | {_d(v.get('notes_plain', 0), p.get('notes_plain') if pp else None)} | "
              f"{_d(v.get('notes_guessed', 0), p.get('notes_guessed') if pp else None)} | "
              f"{_d(v.get('unread_marks', 0), p.get('unread_marks') if pp else None)} | "
              f"{_d(v.get('events_held_out', 0), p.get('events_held_out') if pp else None)} | {v.get('rows_in_unread_gaps', 0)} |")
        a("")
    # ── 6. dropped ──
    a("## 6. Detected, then dropped")
    a("")
    dd = rep["detected_then_dropped"]
    a(f"Detector boxes whose class no family reads (never reach a decision): {dd['classes_no_family_reads']} "
      f"(of {dd['boxes_total']:,} boxes).")
    a(f"Detected and unrepresented in the record: {dd['detected_and_unrepresented'] or 'none'}. "
      f"Decided but not written to the file: {dd['decided_and_unwritten'] or 'none'}.")
    a(f"Ink rows no class explains (Q.INK): {dd['unexplained_ink_rows_Q_INK']}.")
    a("")
    # ── 7. examples ──
    a("## 7. The top reasons, with one place to look")
    a("")
    a("(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)")
    a("")
    for e in rep["examples"]:
        a(f"- {e['count']:,} x {e['reason']} -- e.g. {e['example']}")
    a("")
    # ── 8. guards ──
    a("## 8. Regression guards")
    a("")
    gd = run.get("guards") or {}
    pgd = prun.get("guards") or {}
    for k in ("judged", "check_open"):
        if k in gd:
            a(f"- {k.replace('_', ' ')}: {gd[k]}" + (f"  (previous: {pgd.get(k)})" if pgd.get(k) else ""))
    a("")
    # ── 9. ledger ──
    a("## 9. Balance ledger (every row that must add up)")
    a("")
    bal_rows = ([f["balance"] for f in rep["funnels"]] + [f["stage_balance"] for f in rep["funnels"]]
                + [u["balance"] for u in rep["units"]] + [u["stage_balance"] for u in rep["units"]]
                + list((rep.get("glyph_verdict_crosscheck") or {}).values()))
    if rep.get("bar_balance"):
        bal_rows.append(rep["bar_balance"])
    for r in rep["refusals_vs_export_drops"]:
        if r["record_refused"] or r["export_dropped"]:
            bal_rows.append(_balance(f"refusal vs exporter drop: {r['reason']}", r["record_refused"],
                                     {"exporter dropped": r["export_dropped"]}))
    for c in rep["bars"].get("states_checks") or []:
        bal_rows.append(_balance(c["name"], c["exporter"], {"file": c["file"]}, "file vs exporter"))
    bal_rows.append(_balance("red marks: empty + held out + partial = written",
                             rep["unread_marks"]["equation"]["written"] or 0,
                             {"sum": rep["unread_marks"]["equation"]["empty + held_out + partial"]}))
    if ex["events"].get("balance"):
        bal_rows.append(ex["events"]["balance"])
    bad = [r for r in bal_rows if not r["balanced"]]
    a(f"{len(bal_rows) - len(bad)} of {len(bal_rows)} rows balance. " + ("**Imbalances:**" if bad else "No imbalance."))
    a("")
    for r in bad:
        a(_bal_line(r))
    for o in ex["other_balances"]:
        if o["balanced_as_reported"] is False:
            a(f"- exporter's own `{o['name']}` says balanced = False: {o['detail']}")
    a("")
    return "\n".join(L) + "\n"


def _bal_line(r: Dict[str, Any]) -> str:
    outs = ", ".join(f"{k} {v:,}" for k, v in r["outs"].items() if v)
    return (f"- {r['name']}: in {r['in']:,} = {outs} (sum {r['out_total']:,}) -> " +
            ("balanced" if r["balanced"] else f"**IMBALANCE {r['imbalance']:+,}**"))


def _cat(c) -> str:
    if not c:
        return "n/a"
    return " / ".join(str(c.get(k, 0)) for k in ("read", "carried", "guessed (INFER)", "narrowed", "abstained"))


def _ly(ly) -> str:
    if not ly:
        return "n/a"
    return f"{ly.get('written', 'n/a')} / {ly.get('compiled', 'n/a')} / {ly.get('warnings', 'n/a')}"


_RULE_GLOSS = {
    "fill_part_key": "(a pitch read through a key signature that was inferred for the part)",
    "fill_clef_gap": "(a pitch read through a clef that was inferred)",
    "reconcile_duration": "(length chosen only because the bar then adds up)",
    "collapse_bare_stem_by_bar": "(a stem with no flag/beam seen, length chosen by the bar)",
    "collapse_narrowed_by_bar": "(length narrowed to a few candidates, one chosen by the bar)",
    "collapse_duration_to_barline": "(length chosen to run to the barline)",
    "dynamic_with_an_unread_letter": "(a dynamic word with a letter that could not be read)",
}


def _gloss_rule(k: str) -> str:
    return _RULE_GLOSS.get(k, "")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _git(args: List[str], cwd: Optional[str] = None) -> str:
    try:
        return subprocess.run(["git"] + args, capture_output=True, text=True,
                              cwd=cwd, timeout=60).stdout.strip()
    except Exception:                                            # noqa: BLE001
        return ""


def lilypond_status(night_dir: Path, doc: str) -> Dict[str, Any]:
    """LilyPond written / compiled / warnings, from the files the compare
    step left. Absent files say so; nothing is assumed compiled."""
    ly = night_dir / f"{doc}.ly"
    pdf = night_dir / f"{doc}.pdf"
    log = night_dir / f"{doc}-lilypond.log"
    exlog = night_dir / f"{doc}-export.log"
    warn = None
    if log.exists():
        txt = log.read_text(errors="replace")
        warn = len(re.findall(r"warning", txt, flags=re.I))
    err = None
    if exlog.exists():
        m = re.search(r"^(?:\S+\.)?(Unbalanced|\w*Error): (.{0,120})", exlog.read_text(errors="replace"), re.M)
        err = m.group(0) if m else None
    return {"written": "yes" if ly.exists() and ly.stat().st_size else ("NO (" + err + ")" if err else "NO"),
            "compiled": "yes" if pdf.exists() else ("no" if ly.exists() else "n/a"),
            "warnings": warn if warn is not None else "n/a"}


def cmd_extract(a) -> int:
    from . import record_io
    res = record_io.load_record(a.record)
    facts = extract_facts(res)
    del res
    Path(a.out).write_text(json.dumps(facts, indent=1))
    print(f"wrote {a.out}")
    return 0


def cmd_build(a) -> int:
    facts = json.loads(Path(a.facts).read_text())
    cov = load_export_report(Path(a.export_report), a.doc)
    mx = read_musicxml(Path(a.musicxml)) if a.musicxml else None
    run = json.loads(a.run_json) if a.run_json else {}
    rep = build_report(facts, cov, mx, a.label or a.doc or "movement", run)
    prev = None
    if a.prev_facts:
        pcov = load_export_report(Path(a.prev_export_report), a.doc)
        pmx = read_musicxml(Path(a.prev_musicxml)) if a.prev_musicxml else None
        prev = build_report(json.loads(Path(a.prev_facts).read_text()), pcov, pmx,
                            a.prev_label or "previous", json.loads(a.prev_run_json) if a.prev_run_json else {})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = a.doc or "report"
    (out / f"{stem}.report.json").write_text(json.dumps({"report": rep, "previous": prev}, indent=1))
    (out / f"{stem}.report.md").write_text(render_md(rep, prev))
    print(f"wrote {out}/{stem}.report.md")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# A WHOLE NIGHT
# ─────────────────────────────────────────────────────────────────────────────

DOCS = (("beethoven5-litolff", "litolff", "Beethoven 5 mvt 1 (Litolff scan)"),
        ("brahms1-breitkopf", "brahms", "Brahms 1 mvt 1 (Breitkopf scan)"))

#: Settings that are the pipeline's normal state; anything else in the
#: provenance is shown as "differs from the default".
_DEFAULT_ARGS = {"against": None, "conf": 0.25, "dpi": 600, "imgsz": None, "ink_rows": False,
                 "movements": None, "no_roster": False, "no_weight_routing": False, "ocr": True,
                 "route_weights": False, "sheet": None, "surya": True, "through": "infer",
                 "weights": "auto", "work_id": None}


def _run_info(tag: str, doc: str, facts: Dict[str, Any], rdir: Path, cdir: Path,
              base_commit: Optional[str], repo: Optional[str],
              export_tree: Optional[str] = None) -> Dict[str, Any]:
    prov = facts.get("provenance") or {}
    settings = prov.get("settings") or {}
    args = settings.get("args") or {}
    commit = prov.get("commit")
    run: Dict[str, Any] = {"tree": f"{commit[:8] if commit else 'unknown'}"
                                   f"{' (dirty)' if prov.get('dirty') else ''}"}
    if commit and base_commit and commit != base_commit:
        lines = _git(["log", "--oneline", "--no-merges", f"{base_commit}..{commit}"], cwd=repo).splitlines()
        if lines:
            run["landings"] = [f"{len(lines)} commits (merges left out); the newest 15:"] + lines[:15]
        else:
            run["landings"] = [f"(no commits found between {base_commit[:8]} and {commit[:8]} in this checkout)"]
    elif commit and base_commit:
        run["landings"] = ["none: same tree as the previous night"]
    if export_tree and commit and export_tree != commit[:8]:
        run["tree"] += f"; the export, LilyPond and this report were re-run on tree {export_tree}"
    flags = [f"{k}={v}" for k, v in (settings.get("env_overrides") or {}).items()]
    flags += [f"--{k}={v}" for k, v in args.items()
              if k in _DEFAULT_ARGS and v != _DEFAULT_ARGS[k]]
    run["flags"] = flags or ["none (all defaults)"]
    run["weights"] = f"--weights {args.get('weights')}" + (" (weight routing off)" if not args.get("route_weights") else " (routed)")
    run["pages"] = args.get("pages")
    sm = rdir / "summary.txt"
    if sm.exists():
        m = re.search(rf"^{re.escape(doc)} pages (\S+) exit (\d+) wall (\d+) min", sm.read_text(), re.M)
        if m:
            run["wall"] = f"{m.group(3)} min (gather through INFER; exit {m.group(2)})"
    return run


def _wait_for_memory(limit_gb: float = 15.0, poll_s: int = 300) -> None:
    """Block while ANY python process holds more than `limit_gb` of RSS (a
    Brahms record is 6.7 GB on disk and several times that in memory; two
    lanes loading it at once has crashed this machine before)."""
    import os
    import time
    me = os.getpid()
    while True:
        try:
            ps = subprocess.run(["ps", "-eo", "pid,rss,command"], capture_output=True, text=True).stdout
        except Exception:                                        # noqa: BLE001
            return
        big = [ln for ln in ps.splitlines()[1:]
               if "python" in ln.lower() and int(ln.split(None, 2)[0]) != me
               and int(ln.split(None, 2)[1]) / 1048576 > limit_gb]
        if not big:
            return
        print(f"waiting: a python process holds > {limit_gb} GB ({big[0][:80]})", flush=True)
        time.sleep(poll_s)


def cmd_night(a) -> int:
    R = Path(a.records)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rdir = R / f"overnight-{a.tag}"
    cdir = Path(a.compare_dir) if a.compare_dir else rdir / "compare"
    pdir = Path(a.base_compare_dir) if a.base_compare_dir else (R / f"overnight-{a.base}" / "compare" if a.base else None)
    repo = str(Path(__file__).resolve().parents[3])
    cache = R / f"overnight-{a.tag}" / "regather-report-facts"
    cache.mkdir(parents=True, exist_ok=True)
    rc = 0
    for doc, short, title in DOCS:
        def facts_for(tag, force=False):
            rec = R / f"{doc}-mvt1-whole-{tag}.record.json"
            fp = (R / f"overnight-{tag}" / "regather-report-facts")
            fp.mkdir(parents=True, exist_ok=True)
            fp = fp / f"{doc}.facts.json"
            if fp.exists() and not force:
                return json.loads(fp.read_text()), rec
            if not rec.exists():
                return None, rec
            if rec.stat().st_size > 2_000_000_000:
                _wait_for_memory()
            r = subprocess.run(["nice", "-n", "10", sys.executable, "-m", "tools.omr.staged.regather_report",
                                "extract", str(rec), "--out", str(fp)], cwd=repo)
            return (json.loads(fp.read_text()) if r.returncode == 0 else None), rec

        def guards(rec: Path):
            g: Dict[str, Any] = {}
            try:
                jp = out / f".{doc}.judged.json"
                subprocess.run([sys.executable, "-m", "tools.omr.staged.judged", "score", str(rec),
                                "--doc", short, "--json", str(jp)], cwd=repo, capture_output=True, timeout=1800)
                t = json.loads(jp.read_text())["totals"]
                g["judged"] = ", ".join(f"{k} {t[k]}" for k in ("right", "wrong", "narrowed", "abstained", "not_found", "unscored") if k in t) + \
                    " (Sean's past answers on the tiles that fall on this record)"
                jp.unlink()
            except Exception as e:                                # noqa: BLE001
                g["judged"] = f"not scored ({type(e).__name__})"
            return g

        facts, rec = facts_for(a.tag)
        if facts is None:
            print(f"{doc}: no record/facts for {a.tag}")
            rc = 1
            continue
        covp = cdir / f"{doc}.coverage.json"
        if not covp.exists():
            covp = cdir / "current.json"
        cov = load_export_report(covp, doc)
        mxp = cdir / f"{doc}.musicxml"
        mx = read_musicxml(mxp) if mxp.exists() else None
        pfacts = pcov = pmx = None
        if a.base:
            pfacts, prec = facts_for(a.base)
            if pfacts is not None and pdir is not None:
                pp = pdir / f"{doc}.coverage.json"
                if not pp.exists():
                    pp = pdir / "current.json"
                if pp.exists():
                    pcov = load_export_report(pp, doc)
                    pm = pdir / f"{doc}.musicxml"
                    pmx = read_musicxml(pm) if pm.exists() else None
        base_commit = (pfacts or {}).get("provenance", {}).get("commit") if pfacts else None
        run = _run_info(a.tag, doc, facts, rdir, cdir, base_commit, repo,
                        a.export_tree or _git(["rev-parse", "--short=8", "HEAD"], cwd=repo))
        run["musicxml"] = ({"status": "yes", "detail": f"{mxp.stat().st_size / 1e6:.1f} MB"}
                           if mxp.exists() else {"status": "NO"})
        run["lilypond"] = lilypond_status(cdir, doc)
        run["guards"] = guards(rec)
        chk = out / "check.txt"
        if chk.exists():
            m = re.search(r"TOTAL\s+open=(\d+)", chk.read_text())
            run["guards"]["check_open"] = f"{m.group(1)} open findings (tree-level, same for both movements)" if m else "n/a"
        rep = build_report(facts, cov, mx, f"{title}, {a.tag}", run)
        prev = None
        if pfacts is not None and pcov is not None:
            prun = _run_info(a.base, doc, pfacts, R / f"overnight-{a.base}", pdir, None, repo)
            prun["musicxml"] = {"status": "yes"} if pmx is not None else {"status": "n/a"}
            prun["lilypond"] = lilypond_status(pdir, doc)
            prun["guards"] = guards(R / f"{doc}-mvt1-whole-{a.base}.record.json")
            prev = build_report(pfacts, pcov, pmx, f"{title}, {a.base}", prun)
        (out / f"{doc}.report.json").write_text(json.dumps({"report": rep, "previous": prev}, indent=1))
        (out / f"{doc}.report.md").write_text(render_md(rep, prev))
        print(f"wrote {out}/{doc}.report.md")
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("record")
    e.add_argument("--out", required=True)
    b = sub.add_parser("build")
    b.add_argument("--facts", required=True)
    b.add_argument("--export-report", required=True)
    b.add_argument("--musicxml")
    b.add_argument("--doc")
    b.add_argument("--label")
    b.add_argument("--run-json")
    b.add_argument("--prev-facts")
    b.add_argument("--prev-export-report")
    b.add_argument("--prev-musicxml")
    b.add_argument("--prev-label")
    b.add_argument("--prev-run-json")
    b.add_argument("--out", required=True)
    n = sub.add_parser("night")
    n.add_argument("--tag", required=True)
    n.add_argument("--base")
    n.add_argument("--out", required=True)
    n.add_argument("--records", default="/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
    n.add_argument("--compare-dir", help="where this night's export/musicxml/.ly live (default overnight-TAG/compare)")
    n.add_argument("--base-compare-dir")
    n.add_argument("--export-tree", help="short sha the export ran on (default: this checkout's HEAD)")
    a = ap.parse_args(argv)
    if a.cmd == "extract":
        return cmd_extract(a)
    if a.cmd == "build":
        return cmd_build(a)
    return cmd_night(a)


if __name__ == "__main__":
    raise SystemExit(main())
