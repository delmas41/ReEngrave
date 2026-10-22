"""ROADMAP 2.12 — how often does a detector class's ROLE-half disagree with
the geometry the tree can already compute?

A detector class is two claims. `noteheadBlackOnLine` says SHAPE (a black
notehead) and ROLE (it stands on a line). `keyFlat` says SHAPE (a flat) and
ROLE (it is part of a key signature). `restWhole` says SHAPE (a small filled
rectangle) and ROLE (it hangs under the second line from the top). The
detector is good at the first and guesses the second from a crop.

This probe reads a committed staged record and, family by family, counts:

  * the POPULATION — how many boxes carry a role-half at all;
  * the DISAGREEMENT — how many of those have a role-half the record's own
    geometry contradicts;
  * the UNCOMPUTABLE — how many the tree cannot check today, and why.

⚠️ IT DECIDES NOTHING AND IT IS NOT AN ARM. It reads the record only, changes
no code, and every number it prints is a count over rows that are already on
disk. Where the geometry cannot be recomputed from the record (because the
gather never filed the quantity) the family reports `uncomputable` with a
reason — that is a finding, not a gap in this script.

⚠️ EVERY RECORD IS READ THROUGH `record_io.load_record` AND NOWHERE ELSE
(CLAUDE.md §4b / roadmap 1.1b): a verdict's id lists are pooled in the file
and a naive `json.load` iterates the strings `"$pool"` and `"ins"`.

Run:

    python3 benchmarks/omr-shape-role-2026-09/probe/role_disagreement.py \
        --record <path> --label <id> --out <json>
    python3 benchmarks/omr-shape-role-2026-09/probe/role_disagreement.py --all

`--all` resolves the three acceptance documents from
`benchmarks/acceptance/manifest.json` and runs each in its own SUBPROCESS,
because the two scan records are 314 MB and 478 MB on disk and holding two of
them in one interpreter is the difference between minutes and swap.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))

from tools.omr.staged import record_io          # noqa: E402

# ── the conventions this probe measures against ──────────────────────────────
#
# Positions are in HALF-STEPS measured DOWN FROM THE TOP STAFF LINE, the same
# unit `gather_notehead_positions` files `Q.NOTEHEAD_STAFF_POSITION` in:
# top line 0, first space 1, second line 2, ... bottom line 8. So an EVEN
# rounded position is a LINE and an ODD one is a SPACE.
_LINE, _SPACE = "line", "space"

#: A whole rest hangs UNDER the second line from the top (half-step 2) and
#: occupies the half space below it, so its centre sits at ~2.5. A half rest
#: sits ON the middle line (half-step 4) and occupies the half space above it,
#: so its centre sits at ~3.5. One half-step apart — half a staff space.
#: ⚠️ CONVENTION ASSUMED / WHAT WOULD FALSIFY IT: a record whose correctly
#: read `restWhole` population does NOT cluster near 2.5. The probe prints the
#: observed median for both classes so the assumption can be checked rather
#: than believed; on the engraved fixture the first `restWhole` measures 2.56.
_WHOLE_REST_CENTRE = 2.5
_HALF_REST_CENTRE = 3.5

#: Half-steps of slack before a rest's measured centre is called a
#: disagreement. The two conventions are 1.0 half-step apart, so anything
#: under 0.5 would make every borderline row a disagreement and anything over
#: 0.5 would make none; 0.5 is the midpoint and is reported with the
#: distribution beside it so the choice is visible.
_REST_SLACK = 0.5

#: A notehead is ~1.3 staff spaces wide (CLAUDE.md §10) and about one staff
#: space tall. A clef is 4-7 staff spaces tall (Sean, 2026-09-23, ROADMAP
#: 2.11). Three staff spaces is well clear of both.
_CLEF_SIZED_SPACES = 3.0

_KEYSIG_CLASSES = ("keySharp", "keyFlat", "keyNatural")
_ACCIDENTAL_PREFIX = "accidental"
_NOTEHEAD_PREFIX = "notehead"


# ── record helpers ───────────────────────────────────────────────────────────

def _subject_parts(key: str):
    """`glyph/0/1/2/3/4` -> ('glyph', 0, 1, 2, 3, 4)."""
    bits = key.split("/")
    out = [bits[0]]
    for b in bits[1:]:
        try:
            out.append(int(b))
        except ValueError:
            out.append(b)
    return tuple(out)


def _cell_of(key: str):
    p = _subject_parts(key)
    if p[0] == "glyph" and len(p) >= 6:
        return "cell/%d/%d/%d/%d" % p[1:5]
    if p[0] == "cell":
        return key
    return None


def _staff_of(key: str):
    p = _subject_parts(key)
    if p[0] in ("glyph", "cell") and len(p) >= 4:
        return "staff/%d/%d/%d" % p[1:4]
    if p[0] == "staff":
        return key
    return None


def _cell_index(key: str):
    p = _subject_parts(key)
    if p[0] == "glyph" and len(p) >= 6:
        return p[4]
    if p[0] == "cell" and len(p) >= 5:
        return p[4]
    return None


def _box_value(v):
    """`Q.GLYPH_BOX`'s value is `[name, x, y, w, h]` in the cell's canonical
    frame."""
    if isinstance(v, (list, tuple)) and len(v) >= 5:
        return str(v[0]), float(v[1]), float(v[2]), float(v[3]), float(v[4])
    return None


class Rec:
    """The rows this probe reads, indexed once."""

    def __init__(self, path: Path):
        data = record_io.load_record(path)
        rec = data["record"]
        self.provenance = data.get("provenance") or {}
        self.observations = rec.get("observations") or []
        self.abstentions = rec.get("abstentions") or []
        self.verdicts = rec.get("verdicts") or []

        self.by_q = collections.defaultdict(list)
        for o in self.observations:
            self.by_q[o["quantity"]].append(o)

        # glyph subject -> its Q.GLYPH_BOX row
        self.box = {}
        for o in self.by_q.get("glyph_box", ()):
            self.box[o["subject"]] = o
        # glyph subject -> its rounded staff position
        self.pos = {}
        for o in self.by_q.get("notehead_staff_position", ()):
            self.pos[o["subject"]] = o
        # cell subject -> staff space (canonical px per staff space)
        self.cell_space = {}
        for o in self.by_q.get("cell_staff_space", ()):
            self.cell_space[o["subject"]] = o
        # staff subject -> line ys (page px)
        self.staff_lines = {}
        for o in self.by_q.get("staff_lines", ()):
            v = o["value"]
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                self.staff_lines[o["subject"]] = [float(y) for y in v]
        # boxes per cell, in gather order
        self.cell_boxes = collections.defaultdict(list)
        for subj, o in self.box.items():
            c = _cell_of(subj)
            if c is not None:
                self.cell_boxes[c].append((subj, o))

        self.verdict = collections.defaultdict(dict)
        for v in self.verdicts:
            self.verdict[v["quantity"]][v["subject"]] = v

    def staff_step(self, subject: str, y_center_page):
        """Half-steps down from this staff's top line, in PAGE pixels."""
        if y_center_page is None:
            return None
        lines = self.staff_lines.get(_staff_of(subject) or "")
        if not lines or len(lines) < 2:
            return None
        half = (max(lines) - min(lines)) / (2.0 * (len(lines) - 1))
        if not half:
            return None
        return (float(y_center_page) - min(lines)) / half

    def cell_space_px(self, subject: str):
        row = self.cell_space.get(_cell_of(subject) or "")
        return float(row["value"]) if row else None


# ── the families ─────────────────────────────────────────────────────────────

def f_keysig(r: Rec):
    """`key*` vs `accidental*` — SHAPE a flat/sharp/natural, ROLE key
    signature vs in-bar accidental.

    `gather._gather_keysig_markers` admits `_KEYSIG_CLASSES` in cell 0 and
    nothing else, so the disagreement runs both ways:

      * an `accidental*` box standing in cell 0 LEFT of that cell's leftmost
        notehead is geometrically in the header window and is dropped;
      * a `key*` box standing in a cell other than 0 claims a key signature
        past the first barline and is dropped too (nothing reads it).
    """
    dropped_header = 0
    accidental_in_cell0 = 0
    key_after_bar = 0
    key_in_cell0 = 0
    no_head_reference = 0
    per_staff_dropped = collections.Counter()

    for cell, rows in r.cell_boxes.items():
        idx = _cell_index(cell)
        heads = []
        accs = []
        keys = []
        for subj, o in rows:
            b = _box_value(o["value"])
            if b is None:
                continue
            name, x, _y, w, _h = b
            if name.startswith(_NOTEHEAD_PREFIX):
                heads.append(x)
            elif name.startswith(_ACCIDENTAL_PREFIX):
                accs.append((subj, x + w))
            elif name in _KEYSIG_CLASSES:
                keys.append((subj, x))
        if idx == 0:
            accidental_in_cell0 += len(accs)
            key_in_cell0 += len(keys)
            if accs:
                if not heads:
                    # ⚠️ NO NOTEHEAD IN CELL 0 MEANS NO HEADER BOUNDARY THIS
                    # PROBE CAN DRAW. Counted separately rather than folded in
                    # either direction.
                    no_head_reference += len(accs)
                else:
                    first_head = min(heads)
                    for subj, right in accs:
                        if right <= first_head:
                            dropped_header += 1
                            per_staff_dropped[_staff_of(subj)] += 1
        else:
            key_after_bar += len(keys)

    accidental_total = sum(
        1 for o in r.by_q.get("glyph_box", ())
        if (_box_value(o["value"]) or ("",))[0].startswith(_ACCIDENTAL_PREFIX))
    return {
        "population": key_in_cell0 + key_after_bar + accidental_total,
        "population_key_classes": key_in_cell0 + key_after_bar,
        "population_accidental_classes": accidental_total,
        "disagree": dropped_header + key_after_bar,
        "detail": {
            "accidental_in_cell0_left_of_first_notehead": dropped_header,
            "accidental_in_cell0_total": accidental_in_cell0,
            "accidental_in_cell0_no_notehead_reference": no_head_reference,
            "key_class_after_cell0": key_after_bar,
            "key_class_in_cell0": key_in_cell0,
            "staves_losing_a_header_accidental": len(per_staff_dropped),
        },
    }


def f_notehead_line_space(r: Rec):
    """`*OnLine` / `*InSpace` — SHAPE a black/half/whole head, ROLE which of a
    line and a space it stands on. `Q.NOTEHEAD_STAFF_POSITION` is the same
    fact measured off this staff's own lines."""
    pop = agree = disagree = 0
    no_position = 0
    no_role_half = 0
    ambiguous = 0
    confident_disagree = [0]
    residuals = []
    for subj, o in r.box.items():
        b = _box_value(o["value"])
        if b is None:
            continue
        name = b[0]
        if not name.startswith(_NOTEHEAD_PREFIX):
            continue
        if name.endswith("OnLine"):
            claim = _LINE
        elif name.endswith("InSpace"):
            claim = _SPACE
        else:
            no_role_half += 1
            continue
        pop += 1
        p = r.pos.get(subj)
        if p is None:
            no_position += 1
            continue
        rounded = (p.get("detail") or {}).get("rounded")
        resid = (p.get("detail") or {}).get("residual")
        if rounded is None:
            no_position += 1
            continue
        soft = False
        if resid is not None:
            residuals.append(float(resid))
            # ⚠️ A WARPED SCAN MAKES THE LINE/SPACE CALL ITSELF SOFT. A head
            # sitting a quarter-step off the grid is not evidence either way,
            # so the confident half of the population is reported separately
            # and is the number a change should be priced on.
            if float(resid) > 0.25:
                ambiguous += 1
                soft = True
        measured = _LINE if int(rounded) % 2 == 0 else _SPACE
        if measured == claim:
            agree += 1
        else:
            disagree += 1
            if not soft:
                confident_disagree[0] += 1
    residuals.sort()
    return {
        "population": pop,
        "disagree": disagree,
        "detail": {
            "agree": agree,
            "disagree_where_the_grid_is_confident": confident_disagree[0],
            "no_measured_position": no_position,
            "notehead_classes_with_no_role_half": no_role_half,
            "residual_over_quarter_step": ambiguous,
            "median_residual": (round(residuals[len(residuals) // 2], 4)
                                if residuals else None),
        },
    }


def f_rest_whole_half(r: Rec):
    """`restWhole` / `restHalf` — SHAPE one small filled rectangle, ROLE which
    line it hangs from. Measured against this staff's own lines in page px."""
    obs = collections.Counter()
    steps = collections.defaultdict(list)
    disagree = 0
    fits_other = 0
    fits_neither = 0
    no_geometry = 0
    pop = 0
    for o in r.by_q.get("rest", ()):
        name = str(o["value"])
        if name not in ("restWhole", "restHalf"):
            obs[name] += 1
            continue
        pop += 1
        y = (o.get("detail") or {}).get("y_center_page")
        step = r.staff_step(o["subject"], y)
        if step is None:
            no_geometry += 1
            continue
        steps[name].append(step)
        want = _WHOLE_REST_CENTRE if name == "restWhole" else _HALF_REST_CENTRE
        other = _HALF_REST_CENTRE if name == "restWhole" else _WHOLE_REST_CENTRE
        if abs(step - other) + _REST_SLACK < abs(step - want):
            disagree += 1
            # ⚠️ TWO DIFFERENT FACTS AND THEY MUST NOT COLLAPSE. A rest whose
            # centre lands ON the other convention is a ROLE error the
            # geometry can repair; one that lands on NEITHER is ink standing
            # where no rest of either kind can hang, which is a different
            # finding and a weaker claim for this lane.
            if abs(step - other) <= _REST_SLACK:
                fits_other += 1
            else:
                fits_neither += 1
    med = {}
    for k, v in steps.items():
        v.sort()
        med[k] = {"n": len(v), "median_step": round(v[len(v) // 2], 3),
                  "p10": round(v[len(v) // 10], 3),
                  "p90": round(v[(len(v) * 9) // 10], 3)}
    return {
        "population": pop,
        "disagree": disagree,
        "detail": {
            "lands_on_the_other_convention": fits_other,
            "lands_on_neither_convention": fits_neither,
            "no_staff_geometry": no_geometry,
            "measured": med,
            "convention": {"restWhole": _WHOLE_REST_CENTRE,
                           "restHalf": _HALF_REST_CENTRE,
                           "slack_half_steps": _REST_SLACK},
            "other_rest_classes": dict(obs.most_common(12)),
        },
    }


def f_flag_stem(r: Rec):
    """`flag8thUp` / `flag8thDown` — SHAPE a flag of N hooks, ROLE which way
    the stem it hangs on points. `adjudicate_stem_direction` decides that
    same fact from `Q.STEM`.

    ⚠️ THE JOIN IS THE HARD PART AND IS NOT RE-DERIVED HERE. A flag is filed
    on its OWN glyph subject and the stem direction on the notehead's, and
    attaching them is `_attached_flags`'s job. So this counts only the
    UNAMBIGUOUS cells — exactly one flag row and exactly one DECIDED
    `stem_direction` in the cell — and reports the rest as unjoinable.
    """
    flags_by_cell = collections.defaultdict(list)
    pop = 0
    no_role_half = 0
    for o in r.by_q.get("flag", ()):
        name = str(o["value"])
        if name.endswith("Up"):
            claim = "up"
        elif name.endswith("Down"):
            claim = "down"
        else:
            no_role_half += 1
            continue
        pop += 1
        c = _cell_of(o["subject"])
        if c:
            flags_by_cell[c].append(claim)

    dirs_by_cell = collections.defaultdict(list)
    for subj, v in r.verdict.get("stem_direction", {}).items():
        if v.get("outcome") == "decided":
            c = _cell_of(subj)
            if c:
                dirs_by_cell[c].append(str(v.get("value")))

    joined = agree = disagree = 0
    unjoinable = 0
    for c, claims in flags_by_cell.items():
        ds = set(dirs_by_cell.get(c, ()))
        if len(claims) == 1 and len(ds) == 1:
            joined += 1
            if claims[0] == next(iter(ds)):
                agree += 1
            else:
                disagree += 1
        else:
            unjoinable += len(claims)
    return {
        "population": pop,
        "disagree": disagree,
        "detail": {
            "joined_unambiguous_cells": joined,
            "agree": agree,
            "unjoinable_flags": unjoinable,
            "flag_classes_with_no_role_half": no_role_half,
            "note": ("a flag is filed on its own glyph subject and the stem "
                     "direction on the notehead's; only cells holding exactly "
                     "one of each are joined here"),
        },
    }


def f_arc_kind(r: Rec):
    """`tie` / `slur` — SHAPE one arc, ROLE whether its two ends are the same
    written pitch. `adjudicate_arc_kind` ALREADY computes the grammar from
    `Q.NOTEHEAD_STAFF_POSITION` and records it beside the class without acting
    on it (`OMR_ARC_RECLASS` default OFF, measured refusal). So the
    disagreement is already on the record and only has to be counted."""
    pop = 0
    says = collections.Counter()
    disagree = 0
    silent = 0
    for subj, v in r.verdict.get("arc_kind", {}).items():
        pop += 1
        g = (v.get("detail") or {}).get("grammar") or {}
        reading = g.get("reading")
        grammar_says = g.get("says")
        says[str(grammar_says)] += 1
        if grammar_says is None:
            silent += 1
        elif reading is not None and str(grammar_says) != str(reading):
            disagree += 1
    return {
        "population": pop,
        "disagree": disagree,
        "detail": {
            "grammar_silent": silent,
            "grammar_says": dict(says),
            "note": ("the geometry is already computed and recorded; the "
                     "class still decides (OMR_ARC_RECLASS default OFF)"),
        },
    }


def f_aug_dot_vs_staccato(r: Rec):
    """`augmentationDot` / `articStaccato*` — SHAPE one small filled dot, ROLE
    'after the head, level with it' vs 'above or below it'.

    A dot sits to the RIGHT of its notehead and within about one staff space
    of its centre (a space higher on a line note; the window is asymmetric —
    CLAUDE.md §10). A staccato sits ABOVE or BELOW, at least one staff space
    off the head's centre and roughly over it in x.
    """
    pop_dot = pop_stacc = 0
    dot_not_right = 0
    stacc_is_right = 0
    no_head = 0
    no_space = 0

    heads_by_cell = collections.defaultdict(list)
    for subj, o in r.box.items():
        b = _box_value(o["value"])
        if b and b[0].startswith(_NOTEHEAD_PREFIX):
            _n, x, y, w, h = b
            heads_by_cell[_cell_of(subj)].append((x + w / 2.0, y + h / 2.0,
                                                  x + w))

    def _nearest(cell, x, y):
        best = None
        for hx, hy, hright in heads_by_cell.get(cell, ()):
            d = (hx - x) ** 2 + (hy - y) ** 2
            if best is None or d < best[0]:
                best = (d, hx, hy, hright)
        return best

    for o in r.by_q.get("aug_dot", ()):
        pop_dot += 1
        v = o["value"]
        if not (isinstance(v, (list, tuple)) and len(v) >= 2):
            continue
        x, y = float(v[0]), float(v[1])
        cell = _cell_of(o["subject"])
        sp = r.cell_space_px(o["subject"])
        if sp is None:
            no_space += 1
            continue
        near = _nearest(cell, x, y)
        if near is None:
            no_head += 1
            continue
        _d, hx, hy, hright = near
        # a dot is to the RIGHT of the head's ink and within a space in y
        if not (x > hright and abs(y - hy) <= sp):
            dot_not_right += 1

    for subj, o in r.box.items():
        b = _box_value(o["value"])
        if b is None or not b[0].startswith("articStaccato"):
            continue
        pop_stacc += 1
        _n, x, y, w, h = b
        cell = _cell_of(subj)
        sp = r.cell_space_px(subj)
        if sp is None:
            no_space += 1
            continue
        near = _nearest(cell, x + w / 2.0, y + h / 2.0)
        if near is None:
            no_head += 1
            continue
        _d, hx, hy, hright = near
        if (x + w / 2.0) > hright and abs((y + h / 2.0) - hy) <= sp:
            stacc_is_right += 1

    return {
        "population": pop_dot + pop_stacc,
        "disagree": dot_not_right + stacc_is_right,
        "detail": {
            "aug_dot_rows": pop_dot,
            "aug_dot_not_right_of_a_head": dot_not_right,
            "artic_staccato_rows": pop_stacc,
            "artic_staccato_sitting_where_a_dot_sits": stacc_is_right,
            "no_notehead_in_cell": no_head,
            "no_cell_staff_space": no_space,
        },
    }


def f_timesig_role(r: Rec):
    """`timeSig*` — SHAPE a numeral or a C, ROLE 'this states the meter'.
    The coarse spelling `numeral*` drops the role entirely and
    `class_aliases` refuses to map it; the fine spelling ASSERTS it.

    Geometry the tree has: WHERE the glyph stands. At cell 0 it states the
    staff's opening meter; elsewhere it announces a change, and
    `gather._meter_candidate_columns` already requires other staves of the
    system to agree before the template reader is asked. A `timeSig*` box in
    a cell other than 0 that NO other staff of its system corroborates has a
    role nothing supports."""
    per_system_cell = collections.defaultdict(lambda: collections.Counter())
    rows = []
    for o in r.by_q.get("meter_glyph", ()):
        d = o.get("detail") or {}
        cell = d.get("cell")
        p = _subject_parts(o["subject"])
        if p[0] != "staff" or len(p) < 4:
            continue
        sys_key = (p[1], p[2])
        rows.append((sys_key, cell, str(o["value"]), o["subject"]))
        if cell is not None and cell != 0:
            per_system_cell[sys_key][cell] += 1

    at_header = uncorroborated = corroborated = 0
    for sys_key, cell, _name, _subj in rows:
        if cell == 0:
            at_header += 1
        elif per_system_cell[sys_key][cell] >= 2:
            corroborated += 1
        else:
            uncorroborated += 1
    return {
        "population": len(rows),
        "disagree": uncorroborated,
        "detail": {
            "at_cell_0_header": at_header,
            "mid_staff_corroborated_by_another_staff": corroborated,
            "mid_staff_alone_on_its_system": uncorroborated,
        },
    }


def f_clef_sized_notehead(r: Rec):
    """ROADMAP 2.11's population, counted. A box the detector called a
    NOTEHEAD whose height is clef-sized. A notehead is about one staff space
    tall; a clef is 4-7."""
    pop = big = 0
    no_space = 0
    heights = []
    for subj, o in r.box.items():
        b = _box_value(o["value"])
        if b is None or not b[0].startswith(_NOTEHEAD_PREFIX):
            continue
        if _cell_index(subj) != 0:
            continue
        pop += 1
        sp = r.cell_space_px(subj)
        if not sp:
            no_space += 1
            continue
        spaces = b[4] / sp
        heights.append(spaces)
        if spaces >= _CLEF_SIZED_SPACES:
            big += 1
    heights.sort()
    return {
        "population": pop,
        "disagree": big,
        "detail": {
            "threshold_staff_spaces": _CLEF_SIZED_SPACES,
            "no_cell_staff_space": no_space,
            "median_height_spaces": (round(heights[len(heights) // 2], 3)
                                     if heights else None),
            "note": "cell 0 only — the header, where a clef stands",
        },
    }


def f_artic_fermata_side(r: Rec):
    """`*Above` / `*Below` — SHAPE the mark, ROLE which side of the notes it
    sits on. Measured against the nearest notehead in the same cell."""
    out = {}
    for quantity, key in (("articulation_mark", "artic"),
                          ("fermata_mark", "fermata")):
        pop = disagree = no_head = no_side = 0
        heads_by_cell = collections.defaultdict(list)
        for subj, o in r.box.items():
            b = _box_value(o["value"])
            if b and b[0].startswith(_NOTEHEAD_PREFIX):
                heads_by_cell[_cell_of(subj)].append(
                    (b[1] + b[3] / 2.0, b[2] + b[4] / 2.0))
        for o in r.by_q.get(quantity, ()):
            d = o.get("detail") or {}
            side = d.get("side")
            if side not in ("above", "below"):
                no_side += 1
                continue
            pop += 1
            yc = d.get("y_center")
            xc = d.get("x_center")
            cell = _cell_of(o["subject"])
            cands = heads_by_cell.get(cell) or []
            if not cands or yc is None or xc is None:
                no_head += 1
                continue
            hx, hy = min(cands, key=lambda h: (h[0] - float(xc)) ** 2)
            # canonical y grows DOWNWARD, so "above" means a SMALLER y
            measured = "above" if float(yc) < hy else "below"
            if measured != side:
                disagree += 1
        out[key] = {"population": pop, "disagree": disagree,
                    "no_notehead_in_cell": no_head,
                    "class_states_no_side": no_side}
    return {
        "population": out["artic"]["population"] + out["fermata"]["population"],
        "disagree": out["artic"]["disagree"] + out["fermata"]["disagree"],
        "detail": out,
    }


#: The ROLE-half suffixes a class name can carry. Stripping one leaves the
#: SHAPE core, which is what a shape-only vocabulary would keep.
_ROLE_SUFFIXES = ("OnLine", "InSpace", "Above", "Below", "Up", "Down")


def _shape_core(name: str):
    """`noteheadBlackOnLine` -> `noteheadBlack`, or None where the class
    carries no role-half. ⚠️ `keyFlat`/`accidentalFlat` is a role PREFIX, not
    a suffix, and is handled by `f_keysig`; this is the suffix half only."""
    for suf in _ROLE_SUFFIXES:
        if name.endswith(suf) and len(name) > len(suf):
            return name[:-len(suf)], suf
    return None


def f_role_twin_boxes(r: Rec):
    """TWO SPELLINGS OF ONE PIECE OF INK, both surviving class-wise NMS.

    ⚠️ THIS IS THE ONE COST OF THE SPLIT VOCABULARY THAT NO ADJUDICATOR CAN
    REPAIR. Ultralytics runs NMS PER CLASS by default (`agnostic_nms=False`,
    `yolo_detector.detect`), so `noteheadBlackOnLine` and
    `noteheadBlackInSpace` on one head do not suppress each other: the ink's
    evidence is split across two output channels, both boxes are emitted, and
    a head whose split leaves BOTH under `conf 0.25` is emitted as neither.
    That second half is invisible from a record — a box the detector never
    drew has no subject — so this counts only the visible half: surviving
    pairs of boxes in ONE cell, at high IoU, whose classes share a shape core
    and differ only in the role suffix.

    The IoU is `gather.CONTEST_IOU` (0.3), the frozen reference reader's own
    swept value, so this test and the ownership contest cannot drift apart.
    """
    from tools.omr.staged.gather import CONTEST_IOU

    pairs = 0
    by_kind = collections.Counter()
    cells_touched = set()
    for cell, rows in r.cell_boxes.items():
        items = []
        for subj, o in rows:
            b = _box_value(o["value"])
            if b is None:
                continue
            core = _shape_core(b[0])
            if core is None:
                continue
            items.append((core[0], core[1], b[1], b[2], b[1] + b[3],
                          b[2] + b[4]))
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, bb = items[i], items[j]
                if a[0] != bb[0] or a[1] == bb[1]:
                    continue
                x0 = max(a[2], bb[2])
                y0 = max(a[3], bb[3])
                x1 = min(a[4], bb[4])
                y1 = min(a[5], bb[5])
                if x1 <= x0 or y1 <= y0:
                    continue
                inter = (x1 - x0) * (y1 - y0)
                union = ((a[4] - a[2]) * (a[5] - a[3])
                         + (bb[4] - bb[2]) * (bb[5] - bb[3]) - inter)
                if union > 0 and inter / union > CONTEST_IOU:
                    pairs += 1
                    by_kind["%s:%s/%s" % (a[0], *sorted((a[1], bb[1])))] += 1
                    cells_touched.add(cell)
    return {
        "population": len(r.box),
        "disagree": pairs,
        "detail": {
            "iou_threshold": CONTEST_IOU,
            "cells_holding_a_twin_pair": len(cells_touched),
            "by_shape_core": dict(by_kind.most_common(12)),
            "note": ("the INVISIBLE half -- a head whose evidence split below "
                     "conf 0.25 and was emitted as neither spelling -- cannot "
                     "be counted from a record and needs a detector arm"),
        },
    }


def f_uncomputable(r: Rec):
    """Families whose ROLE the tree cannot check today, with the reason.

    ⚠️ A ROW HERE IS A FINDING, NOT A HOLE IN THIS SCRIPT. It says the gather
    never filed the quantity a geometric re-reading would need.
    """
    box_classes = collections.Counter()
    for _s, o in r.box.items():
        b = _box_value(o["value"])
        if b:
            box_classes[b[0]] += 1
    dyn = sum(v for k, v in box_classes.items() if k.startswith("dynamic")
              and "Hairpin" not in k)
    tuplets = {k: v for k, v in box_classes.items()
               if k.startswith(("tuplet", "fingering", "tuple", "numeral"))}
    ped = {k: v for k, v in box_classes.items() if k.startswith("keyboardPedal")}
    beams = box_classes.get("beam", 0)
    ledgers = box_classes.get("ledgerLine", 0) + box_classes.get("legerLine", 0)
    clefc = {k: v for k, v in box_classes.items() if k.startswith("clefC")}
    return {
        "dynamic_letters": {
            "population": dyn,
            "reason": ("the class names a LETTER and claims no role; the role "
                       "question is 'is this run of letters a dynamic or a "
                       "word' and lives in direction_text._blank_detections, "
                       "which already overrules the category with an ink "
                       "measurement"),
        },
        "tuplet_vs_fingering_vs_numeral": {
            "population": sum(tuplets.values()),
            "by_class": tuplets,
            "reason": ("gather admits BOTH tuplet3 and fingering3 and gates "
                       "positionally in adjudicate_tuplet_ratio — already the "
                       "2.12 shape. `numeral*` carries no role at all and "
                       "class_aliases REFUSES to map it"),
        },
        "keyboard_pedal": {
            "population": sum(ped.values()),
            "by_class": ped,
            "reason": "no quantity is gathered for it; nothing reads it",
        },
        "beam": {
            "population": beams,
            "reason": ("the role question is 'beam vs slur vs ledger line', "
                       "and line_detection.detect_beams already decides it by "
                       "ATTACHED STEM COUNT, not by a class name; gather "
                       "unions the two readers rather than gating"),
        },
        "ledger_line": {
            "population": ledgers,
            "reason": ("ledgerLine claims no role; _ledger_index reads it as "
                       "geometry already"),
        },
        "clefC_line": {
            "population": sum(clefc.values()),
            "by_class": clefc,
            "reason": ("clef_geometry.resolve_clef MEASURES the line and "
                       "prefers it over the class fallback — already the 2.12 "
                       "shape"),
        },
    }


FAMILIES = [
    ("keysig_vs_accidental", f_keysig),
    ("notehead_on_line_in_space", f_notehead_line_space),
    ("rest_whole_vs_half", f_rest_whole_half),
    ("flag_up_down_vs_stem", f_flag_stem),
    ("arc_tie_vs_slur", f_arc_kind),
    ("aug_dot_vs_staccato", f_aug_dot_vs_staccato),
    ("timesig_role", f_timesig_role),
    ("clef_sized_notehead", f_clef_sized_notehead),
    ("artic_fermata_side", f_artic_fermata_side),
    ("role_twin_boxes", f_role_twin_boxes),
]


def run(path: Path, label: str) -> dict:
    r = Rec(path)
    out = {
        "label": label,
        "record": str(path),
        "provenance": {"commit": r.provenance.get("commit"),
                       "dirty": r.provenance.get("dirty")},
        "counts": {"observations": len(r.observations),
                   "verdicts": len(r.verdicts),
                   "glyph_box": len(r.by_q.get("glyph_box", ()))},
        "families": {},
        "uncomputable": f_uncomputable(r),
    }
    for name, fn in FAMILIES:
        out["families"][name] = fn(r)
    return out


def _resolve(doc) -> Path:
    rec = doc["record"]
    if rec["root"] == "library":
        from tools.library.score_library import library_root
        return Path(library_root()) / rec["path"]
    return _REPO / rec["path"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record")
    ap.add_argument("--label", default="?")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.all:
        man = json.loads(
            (_REPO / "benchmarks/acceptance/manifest.json").read_text())
        results = []
        outdir = _REPO / "benchmarks/omr-shape-role-2026-09/out"
        outdir.mkdir(parents=True, exist_ok=True)
        for doc in man["documents"]:
            p = _resolve(doc)
            dst = outdir / ("role-disagreement--%s.json" % doc["id"])
            print("=== %s  %s" % (doc["id"], p), flush=True)
            if not p.exists():
                print("   MISSING", flush=True)
                continue
            # ⚠️ ONE SUBPROCESS PER RECORD. The two scan records are 314 MB
            # and 478 MB on disk; holding two expanded in one interpreter is
            # the difference between minutes and swap.
            rc = subprocess.call(
                [sys.executable, __file__, "--record", str(p),
                 "--label", doc["id"], "--out", str(dst)],
                env={**os.environ, "PYTHONPATH": str(_REPO)})
            if rc != 0:
                print("   FAILED rc=%d" % rc, flush=True)
                continue
            results.append(json.loads(dst.read_text()))
        (outdir / "role-disagreement--all.json").write_text(
            json.dumps(results, indent=1))
        _summary(results)
        return 0

    if not a.record:
        ap.error("--record or --all")
    res = run(Path(a.record), a.label)
    text = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(text)
        print("wrote", a.out)
    else:
        print(text)
    return 0


def _summary(results):
    print()
    print("%-28s %s" % ("family", "  ".join("%-22s" % r["label"]
                                            for r in results)))
    total = collections.Counter()
    for name, _fn in FAMILIES:
        cells = []
        for r in results:
            f = r["families"][name]
            cells.append("%6d / %-13d" % (f["disagree"], f["population"]))
            total[name] += f["disagree"]
        print("%-28s %s" % (name, "  ".join(cells)))
    print()
    print("by reach (disagreeing boxes, three records):")
    for name, n in total.most_common():
        print("  %-30s %d" % (name, n))


if __name__ == "__main__":
    raise SystemExit(main())
