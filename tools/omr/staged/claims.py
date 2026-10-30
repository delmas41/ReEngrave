"""The claimed-area REGISTER -- ROADMAP 2.181 (docs/plan-2026-10-20-claimed-area.md §3, §7 step 2). Flag `OMR_CLAIMED_REGISTER`, default ON.

PATH: STAGED. PURE helpers (a page raster and boxes in, numbers out; no log, no cell, no quantity named): `gather.gather_claimed_register`
is the GATHER stage that files the rows, `adjudicators/claimed_by.py` is the one ADJUDICATE consult. Registered in `reach.NOT_A_STAGE`.

## What the register is, in plain words

A mark read from the big picture (a clef, the system's header column, a printed meter) CLAIMS the space it is printed in. The claim is
ONE quantity, `Q.CLAIMED_AREA`, filed on the STAFF, one row per claim, every row the same shape:

    value   the claimed area, page px [x0, y0, x1, y1]
    detail  owner      `clef` | `leading_column` | `meter` (2.177 files `meter`)
            owner_row  the read the claim rests on (a `Q.CLEF_LOCATED` / `Q.GLYPH_BOX` row id), or None
            unit       `area`
            standing   READ (the owner was read) or NARROWED (one witness only: the claim may narrow a box, never refuse it)
            prior      True where the claim rests on a convention Sean called "not normally" (the header column, 2026-10-20):
                       a box there is refused only where ITS OWN INK is line-shaped (barline / bracket / brace stroke); else narrowed
            cell       the cell the claim stands in
            boxes_inside {glyph subject key: {ink_share_inside, inside_px, ink_px, cls[, named][, through]}}
                       for every other box of that cell whose box meets the area -- MEASURED here, read by the consult

`covering(rows, key)` lists the claims that hold a box's ink; it decides nothing. The consult (ADJUDICATE) asks the plan's EVALUATE
question -- does a refusal FOLLOW? -- and answers REFUSE (`claimed_by:<owner>`), NARROW (written blue, both readings carried) or
nothing. A claim is consulted, never erased: no raster is changed.

CONVENTION ASSUMED: nothing but a clef's own ink stands inside the clef's box; nothing but the system barline, bracket, brace and
instrument name stands left of the first clef (Sean 2026-10-20: "idk possibly but not normally" -- a PRIOR, so it narrows unless the
box's own ink is a line). WHAT WOULD FALSIFY IT: a print-confirmed note inside a READ clef area, or a note left of the first clef
whose ink passes the line test. NOT CONFIRMED beyond the two plates; blind tiles `out/print/2.181-review/`.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ENV = "OMR_CLAIMED_REGISTER"

#: share of a box's own ink (bare staff-line runs left out) that must lie inside a claim for the claim to hold the box
#: (the 2.177 meter cut, one cut for every owner: a mark's own piece is wholly inside, ~1.0; a neighbour shares a sliver)
INSIDE_SHARE_MIN = 0.5
#: a detector clef box claims only where it is clef-sized (2.144: the short wide `clef*` boxes, 0.5-1.1 sp, lie on arcs and clutter)
CLEF_BOX_MIN_HEIGHT_SPACES = 2.0
#: a detector clef box is READ only in a system's FIRST bar, starting this close to the bar's left edge: a system opens with a clef
#: (convention) and the detector boxed it there -- two sources. Anywhere else (a clef change at a later bar, or mid-bar) it is the
#: detector's word alone: NARROWED (2.144: Sean's tile 4 a real eighth in a false clefG box; 2.181 Litolff: two real eighth rests and
#: a half note inside clef-sized `clef*` boxes at a later bar's start)
CLEF_WINDOW_SPACES = 6.0
#: the header column reaches this far left of the staff's start (the bracket and brace stand left of the system barline)
COLUMN_LEFT_REACH_SPACES = 2.0
#: the line test: a column of the box's ink covering this share of the box's own rows ...
THROUGH_COVER_MIN = 0.9
#: ... that goes on past the box's top or bottom edge for this many staff spaces (a barline / bracket / brace stroke runs on; a head stops)
THROUGH_BEYOND_SPACES = 0.5
#: 2.176's two tests, kept as REFUSALS through the register (Sean 2026-10-20, 2.176 tiles 9/9 and 2.181 tiles 1 and 11: a bracket and a
#: clef written blue are wrong): a box whose left edge is this close to a system's cell-0 left edge is the barline/bracket/brace ...
LEADING_EDGE_SPACES = 0.5
#: ... and a stemless head box this much inside a clef box that starts within `CLEF_WINDOW_SPACES` of its bar's left edge, scored by the
#: detector at least as high as the head, is that clef (2.176 `on_another_symbols_box`)
CLEF_BOX_COVER_MIN = 0.9

OWNER_CLEF = "clef"
OWNER_COLUMN = "leading_column"
OWNER_METER = "meter"
#: lane-arcs-claim-1029 (flag `OMR_ARC_CLAIM`, `arc_claim.py`): a traced arc's strokes, `unit: ink` rows only, ONE per system arc; not in OWNERS.
OWNER_ARC = "arc"
#: ROADMAP 2.183 (flag `OMR_KEY_SIGNATURE_CLAIM`): the key signature's run -- the cancelling naturals (Sean 2026-10-20: "Canceling
#: accidentals should be considered key signature") and the new key's sharps / flats -- from the clef's right edge to the run's last slot
OWNER_KEY = "key_signature"
#: ROADMAP 2.221 m1 / m1b (docs/plan-2026-10-28-page-claim-order.md §7, §9): a word or dynamic READ outside the staves, and a bracket or
#: brace at a system's left edge, claim their ink PAGE-WIDE before any head (flags OMR_CLAIM_WORDS_FIRST / OMR_CLAIM_BRACKETS_FIRST, OFF)
OWNER_WORD = "word"
OWNER_BRACKET = "bracket"
OWNERS = (OWNER_CLEF, OWNER_COLUMN, OWNER_METER, OWNER_KEY, OWNER_WORD, OWNER_BRACKET)
ENV_KEY = "OMR_KEY_SIGNATURE_CLAIM"
#: classes that are owners' own ink, never measured as a box inside a claim
OWNER_CLASS_PREFIXES = ("clef", "gClef", "fClef", "cClef", "timeSig", "key", "brace", "bracket")


def enabled() -> bool:
    """`OMR_CLAIMED_REGISTER`, default ON (ROADMAP 2.181, Sean 2026-10-20); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")


def key_enabled() -> bool:
    """`OMR_KEY_SIGNATURE_CLAIM` (ROADMAP 2.183), default ON (Sean 2026-10-23); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV_KEY, "").strip().lower() not in ("0", "false", "no", "off")


def key_active() -> bool:
    """The key claim files and is consulted only through the register: both `OMR_KEY_SIGNATURE_CLAIM` and `OMR_CLAIMED_REGISTER` on."""
    return key_enabled() and enabled()


#: ROADMAP 2.208 (flag `OMR_CLEF_SLOT_CLAIM`, default ON): the clef's own ink on a staff where no clef was located or boxed.
ENV_CLEF_SLOT = "OMR_CLEF_SLOT_CLAIM"
#: the slot reaches this far above the top line and below the bottom line (a G clef's curl and a bass clef's dots; the detector's own
#: clef-sized boxes measure 6-7 sp tall)
CLEF_SLOT_REACH_SPACES = 4.0
#: past the widest clef the system's other staves show (they stand at one x), the slot ends this far on (a clef wider than any sibling's still fits; past it stands a key accidental or a meter, never a head)
CLEF_SLOT_PAD_SPACES = 0.75
#: a slot narrower than this is no clef (a staff whose clef offset and key claim nearly touch)
CLEF_SLOT_MIN_SPACES = 1.0


def clef_slot_enabled() -> bool:
    """`OMR_CLEF_SLOT_CLAIM` (ROADMAP 2.208), default ON (Sean 2026-10-26); an explicit 0/false/no/off disables. Needs the register."""
    return enabled() and os.environ.get(ENV_CLEF_SLOT, "").strip().lower() not in ("0", "false", "no", "off")


def clef_slot(left: float, key_lo: Optional[float], clef_right_max: float, lines: Sequence[float], spacing: float) -> Optional[List[float]]:
    """The clef's slot on ONE staff (page px [x0, y0, x1, y1]): from `left` (where the system's clefs begin -- the header column's right
    edge) to the key claim's left edge, never beyond the widest clef the system's other staves show (`clef_right_max`) plus
    `CLEF_SLOT_PAD_SPACES`; `CLEF_SLOT_REACH_SPACES` above the top line and below the bottom line. None where the slot is narrower than
    `CLEF_SLOT_MIN_SPACES`. Pure geometry: decides nothing."""
    if not spacing or len(lines) < 5:
        return None
    hi = float(clef_right_max) + CLEF_SLOT_PAD_SPACES * spacing
    if key_lo is not None:
        hi = min(hi, float(key_lo))
    if hi - float(left) < CLEF_SLOT_MIN_SPACES * spacing:
        return None
    return [round(float(left), 1), round(float(lines[0]) - CLEF_SLOT_REACH_SPACES * spacing, 1), round(hi, 1),
            round(float(lines[4]) + CLEF_SLOT_REACH_SPACES * spacing, 1)]


def is_owner_class(name: Any) -> bool:
    return str(name).startswith(OWNER_CLASS_PREFIXES)


def is_clef_box(name: Any, box: Optional[Sequence[float]], spacing: float) -> bool:
    """A detector box the register may file as a clef claim: a `clef*` class, clef-sized."""
    if not str(name).startswith("clef") or not box or not spacing:
        return False
    return (box[3] - box[1]) / spacing >= CLEF_BOX_MIN_HEIGHT_SPACES


def clef_box_standing(box: Sequence[float], cell_box: Sequence[float], spacing: float, cell: int = 0) -> str:
    """READ where the clef box stands in a system's first bar (`cell` 0) within `CLEF_WINDOW_SPACES` of its left edge, else NARROWED."""
    return "READ" if cell == 0 and (box[0] - cell_box[0]) / spacing <= CLEF_WINDOW_SPACES else "NARROWED"


def overlaps(a: Sequence[float], b: Sequence[float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def leading_column(cell_box: Sequence[float], clef_left_x: float, spacing: float) -> Optional[List[float]]:
    """The header column of ONE staff: from `COLUMN_LEFT_REACH_SPACES` left of the staff's start (cell 0's left edge) to the first
    clef's left edge, the cell's own height. None where the clef stands at or left of the staff's start (nothing to claim)."""
    x0 = float(cell_box[0]) - COLUMN_LEFT_REACH_SPACES * spacing
    if clef_left_x <= float(cell_box[0]):
        return None
    return [round(x0, 1), float(cell_box[1]), round(float(clef_left_x), 1), float(cell_box[3])]


def through_stroke(binary: Any, box: Sequence[float], spacing: float) -> Optional[Dict[str, Any]]:
    """The line test on a box's OWN ink: the best column inside the box, its ink cover of the box's rows, and how far (staff spaces)
    the ink runs on past the box's top and bottom edges in that column (gaps of up to 2 px bridged). `through` is True where the cover
    is at least `THROUGH_COVER_MIN` and the stroke runs on at least `THROUGH_BEYOND_SPACES` past one edge. None off the raster."""
    import numpy as np
    if binary is None or getattr(binary, "ndim", 0) != 2 or not spacing:
        return None
    H, W = binary.shape
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1, y1 = min(W, int(round(box[2]))), min(H, int(round(box[3])))
    if x1 - x0 < 1 or y1 - y0 < 2:
        return None
    reach = int(round(3 * spacing))
    ink = binary[:, x0:x1] == 0
    inner = ink[y0:y1]
    cover = inner.mean(axis=0)
    best = None
    for c in np.argsort(-cover)[:6]:
        col = ink[:, c]

        def _run(start: int, step: int) -> int:
            n, gap, y = 0, 0, start
            while 0 <= y < H and n + gap < reach:
                if col[y]:
                    n += gap + 1
                    gap = 0
                else:
                    gap += 1
                    if gap > 2:
                        break
                y += step
            return n
        up, down = _run(y0 - 1, -1), _run(y1, 1)
        beyond = max(up, down) / spacing
        cand = (float(cover[c]), beyond, up / spacing, down / spacing, int(c) + x0)
        if best is None or (cand[0] >= THROUGH_COVER_MIN, cand[1]) > (best[0] >= THROUGH_COVER_MIN, best[1]):
            best = cand
    cov, beyond, up, down, cx = best
    return {"through": bool(cov >= THROUGH_COVER_MIN and beyond >= THROUGH_BEYOND_SPACES), "column_cover": round(cov, 3),
            "beyond_up_spaces": round(up, 2), "beyond_down_spaces": round(down, 2), "column_x": cx}


def covering(rows: Iterable[Any], key: str, box_strokes: Optional[Sequence[int]] = None,
             cell: Optional[int] = None) -> List[Tuple[Any, Dict[str, Any]]]:
    """Every `Q.CLAIMED_AREA` row (any owner) that holds the box `key`: its entry names the box (`named`, the owner itself said this
    box is its ink) or measured at least `INSIDE_SHARE_MIN` of the box's own ink inside the area. Decides nothing.

    ROADMAP 2.198, the `ink` branch (plan §2.3): where the caller passes `box_strokes` (the box's `Q.GLYPH_STROKES` value, stroke
    ordinals of the box's own `cell`), a `unit: ink` claim of that cell also holds the box when at least `INSIDE_SHARE_MIN` of the box's
    strokes are the claim's strokes (the claim's own owner box excepted). Its entry is `{"unit": "ink", "stroke_share", "shared"}`.
    Without `box_strokes` an ink claim is ignored, so every existing caller reads exactly what it read."""
    out = []
    for r in rows:
        d = getattr(r, "detail", None) or {}
        if d.get("unit") == "ink" and d.get("owner") in OWNERS and box_strokes:
            if cell is not None and d.get("cell") != cell:
                continue
            if d.get("owner_glyph") == key:
                continue
            mine = set(r.value or ()) if isinstance(getattr(r, "value", None), (list, tuple)) else set()
            shared = len(mine & set(box_strokes))
            share = shared / float(len(set(box_strokes)))
            if shared and share >= INSIDE_SHARE_MIN:
                out.append((r, {"unit": "ink", "stroke_share": round(share, 3), "shared": shared}))
            continue
        if d.get("unit") != "area" or d.get("owner") not in OWNERS:
            continue
        got = (d.get("boxes_inside") or {}).get(key)
        if not got:
            continue
        at_edge = d.get("owner") == OWNER_COLUMN and got.get("left_edge_spaces") is not None \
            and float(got["left_edge_spaces"]) <= LEADING_EDGE_SPACES
        clef_cover = d.get("owner") == OWNER_CLEF and float(got.get("box_cover", 0.0)) >= CLEF_BOX_COVER_MIN
        if got.get("named") or at_edge or clef_cover or got.get("tail") is not None or float(got.get("ink_share_inside", 0.0)) >= INSIDE_SHARE_MIN:
            out.append((r, got))
    return out


# ---------------------------------------------------------------------------------------------------------------------------------
# ROADMAP 2.221 m1 / m1b: the PAGE-WIDE claims (words, dynamics, brackets, braces). Sean 2026-10-29: "arcs as well as words and dynamic
# markings need to be treated system or page wide not based on individual measures"; "Can 1 and 1b read on the same pass as barlines? I
# don't want to add reading passes every time we add a symbol". So nothing here READS the page: the word claim is bookkeeping on rows the
# text readers already filed (accepted `Q.DIRECTION_WORD`, `Q.DYNAMIC_LETTER`), the bracket claim takes the left-edge vertical-rule scan's
# strokes as INPUT (`bracket_reader.Stroke`, the scan the barline lane shares). ONE row per mark per (page, system), filed on the SYSTEM.
#
# CONVENTION ASSUMED: a word read by the lexicon outside the staff lines, a dynamic spelled from two or more detector letters outside them,
# and a thin rule or a brace standing at or left of the system's staff start hold no notehead's ink. WHAT WOULD FALSIFY IT: Sean's tiles
# showing a real note under a claimed word / dynamic / bracket. NOT CONFIRMED beyond the two plates (out/print/2.221-m1-pagewide/).
# ---------------------------------------------------------------------------------------------------------------------------------
ENV_WORDS = "OMR_CLAIM_WORDS_FIRST"
ENV_BRACKETS = "OMR_CLAIM_BRACKETS_FIRST"
#: a word / dynamic is OUTSIDE the staves when at most this share of its box's height lies inside any staff's line band (top line to
#: bottom line, +- `WORD_BAND_PAD_SPACES`); a word inside the staff is milestone 4 ("almost always short", Sean 2026-10-28), not claimed
WORD_BAND_OVERLAP_MAX = 0.25
WORD_BAND_PAD_SPACES = 0.5
#: two detector dynamic letters belong to ONE printed dynamic when the gap between their boxes is at most this (staff spaces) and their
#: boxes overlap vertically by at least `LETTER_ROW_OVERLAP_MIN` of the smaller height (the `ff` of Litolff p4 is two `dynamicF` boxes)
LETTER_JOIN_GAP_SPACES = 0.6
LETTER_ROW_OVERLAP_MIN = 0.5
#: two letter boxes are the SAME ink (a twin) when they overlap by this share of the smaller box (gather `_same_ink_boxes`' cut)
LETTER_TWIN_SHARE = 0.5
#: a bracket / brace stroke claims only at or left of the system's staff start (`Stroke.offset_spacings`, the systemic barline stands AT
#: it; a tall stem to its right is a note's) and only this tall (staff spaces; a bracket spans a block, a brace a pair of staves)
BRACKET_MAX_OFFSET_SPACES = 0.5
BRACKET_MIN_HEIGHT_SPACES = 4.0


def words_first_enabled() -> bool:
    """`OMR_CLAIM_WORDS_FIRST` (ROADMAP 2.221 m1), default OFF; needs the register. An explicit 1/true/yes/on enables."""
    return enabled() and os.environ.get(ENV_WORDS, "").strip().lower() in ("1", "true", "yes", "on")


def brackets_first_enabled() -> bool:
    """`OMR_CLAIM_BRACKETS_FIRST` (ROADMAP 2.221 m1b), default OFF; needs the register. An explicit 1/true/yes/on enables."""
    return enabled() and os.environ.get(ENV_BRACKETS, "").strip().lower() in ("1", "true", "yes", "on")


def band_share(box: Sequence[float], bands: Iterable[Tuple[float, float]]) -> float:
    """The largest share of `box`'s height that lies inside any one staff line band `(lo, hi)` (page px). Measured; decides nothing."""
    h = max(1.0, float(box[3]) - float(box[1]))
    best = 0.0
    for lo, hi in bands:
        best = max(best, max(0.0, min(float(box[3]), hi) - max(float(box[1]), lo)) / h)
    return best


def _overlap_small(a: Sequence[float], b: Sequence[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    small = max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))
    return ix * iy / small


def spell_letter_runs(letters: Sequence[Tuple[Sequence[float], str, Any]], spacing: float,
                      words: Iterable[str]) -> List[Dict[str, Any]]:
    """Join one system's detector dynamic letters `(page box, letter, row id)` into printed runs, left to right; PURE.

    Twins (one ink boxed twice, `LETTER_TWIN_SHARE`) fold into one slot; a slot whose twins name DIFFERENT letters leaves the run
    unspelled (`text` None, `why` `twin_letters_disagree`). A run is READ only when it has at least two slots and its spelling is in
    `words` (the dynamic vocabulary, a convention); a lone letter is the detector's word alone (`why` `lone_letter`), a spelling outside
    the vocabulary is `not_a_dynamic`. Returns `{box, text, slots, rows, read, why}` per run; the caller claims only `read` runs."""
    vocab = set(words)
    slots: List[Dict[str, Any]] = []
    for box, letter, rid in sorted(letters, key=lambda t: (float(t[0][0]), float(t[0][1]))):
        b = [float(v) for v in box]
        twin = next((s for s in slots if _overlap_small(s["box"], b) >= LETTER_TWIN_SHARE), None)
        if twin is not None:
            twin["letters"].add(str(letter))
            twin["rows"].append(rid)
            twin["box"] = [min(twin["box"][0], b[0]), min(twin["box"][1], b[1]), max(twin["box"][2], b[2]), max(twin["box"][3], b[3])]
            continue
        slots.append({"box": b, "letters": {str(letter)}, "rows": [rid]})
    slots.sort(key=lambda s: s["box"][0])
    runs: List[List[Dict[str, Any]]] = []
    for s in slots:
        if runs:
            last = runs[-1][-1]
            gap = s["box"][0] - last["box"][2]
            hs = min(s["box"][3] - s["box"][1], last["box"][3] - last["box"][1])
            ov = min(s["box"][3], last["box"][3]) - max(s["box"][1], last["box"][1])
            if gap <= LETTER_JOIN_GAP_SPACES * spacing and hs > 0 and ov >= LETTER_ROW_OVERLAP_MIN * hs:
                runs[-1].append(s)
                continue
        runs.append([s])
    out: List[Dict[str, Any]] = []
    for run in runs:
        box = [min(s["box"][0] for s in run), min(s["box"][1] for s in run), max(s["box"][2] for s in run), max(s["box"][3] for s in run)]
        rows = [r for s in run for r in s["rows"]]
        if any(len(s["letters"]) > 1 for s in run):
            out.append({"box": box, "text": None, "slots": len(run), "rows": rows, "read": False, "why": "twin_letters_disagree"})
            continue
        text = "".join(next(iter(s["letters"])) for s in run)
        if len(run) < 2:
            why = "lone_letter"
        elif text not in vocab:
            why = "not_a_dynamic"
        else:
            why = None
        out.append({"box": box, "text": text, "slots": len(run), "rows": rows, "read": why is None, "why": why})
    return out

#: ROADMAP 2.221 word coverage -- the geometry of the extra word claims. All of it reads rows and rasters GATHER already holds.
#: a metronome note stands this far right of its tempo word (staff spaces; Litolff p1: 1200 -> 1228 = 1.8) ...
TEMPO_NOTE_GAP_SPACES = 3.0
#: ... and its `= 108` ink continues until a gap this wide, at most this far from the note
TEMPO_TAIL_GAP_SPACES = 2.0
TEMPO_TAIL_MAX_SPACES = 10.0
#: detector classes that can be the metronome's note glyph
TEMPO_NOTE_PREFIXES = ("notehead", "metronome")
#: an instrument name's ink is a component at most this tall (staff spaces): a brace, bracket or barline is taller
LABEL_MAX_COMPONENT_SPACES = 4.0
#: heading text (title, composer, plate number): ink above the first staff by `HEADING_CLEAR_SPACES`, or below the last by
#: `FOOTER_CLEAR_SPACES` (notes on ledger lines reach about 5 spaces past the staff), components at most this tall
HEADING_CLEAR_SPACES = 5.0
FOOTER_CLEAR_SPACES = 8.0
HEADING_MAX_COMPONENT_SPACES = 8.0
HEADING_JOIN_SPACES = 2.5


def _ink_cols(binary: Any, y0: int, y1: int, x0: int, x1: int) -> Tuple[Any, int]:
    import numpy as np
    H, W = binary.shape
    y0, y1, x0, x1 = max(0, y0), min(H, y1), max(0, x0), min(W, x1)
    if y1 <= y0 or x1 <= x0:
        return np.zeros(0, dtype=bool), x0
    return (binary[y0:y1, x0:x1] == 0).any(axis=0), x0


def metronome_mark(word_box: Sequence[float], notes: Iterable[Sequence[float]], binary: Any, spacing: float) -> Optional[Dict[str, Any]]:
    """A tempo word's WHOLE mark when a metronome follows it: `{box, note_box, tail_x}` -- the word, the note glyph that stands right of
    it on its line (a detector notehead within `TEMPO_NOTE_GAP_SPACES`, vertically within the word's line) and the ink that continues
    right of the note (`= 108.`) until a gap of `TEMPO_TAIL_GAP_SPACES`. None when no note follows (a tempo word alone). PURE, one
    column-ink test on the page raster the claim already holds: no new reading pass."""
    if binary is None or getattr(binary, "ndim", 0) != 2 or not spacing:
        return None
    wx0, wy0, wx1, wy1 = (float(v) for v in word_box)
    best = None
    for nb in notes:
        nx0, ny0, nx1, ny1 = (float(v) for v in nb)
        cy = (ny0 + ny1) / 2.0
        if not (wx1 - 0.5 * spacing <= nx0 <= wx1 + TEMPO_NOTE_GAP_SPACES * spacing and wy0 - spacing <= cy <= wy1 + spacing):
            continue
        if best is None or nx0 < best[0]:
            best = (nx0, ny0, nx1, ny1)
    if best is None:
        return None
    nx0, ny0, nx1, ny1 = best
    y0, y1 = int(min(wy0, ny0)), int(max(wy1, ny1))
    reach = int(nx1 + TEMPO_TAIL_MAX_SPACES * spacing)
    cols, xo = _ink_cols(binary, y0, y1, int(nx1) - 1, reach)
    gap_max, last, gap = int(TEMPO_TAIL_GAP_SPACES * spacing), None, 0
    for i, on in enumerate(cols):
        if on:
            last, gap = i, 0
        else:
            gap += 1
            if gap > gap_max:
                break
    x1 = max(nx1, float(xo + last + 1) if last is not None else nx1)
    return {"box": [min(wx0, nx0), min(wy0, ny0), x1, max(wy1, ny1)], "note_box": [nx0, ny0, nx1, ny1], "tail_x": x1}


def _components(binary: Any, box: Sequence[float]) -> List[Tuple[int, int, int, int]]:
    """Connected ink components `(x0, y0, x1, y1)` of `binary` inside `box` (page px), 8-connected; PURE."""
    import cv2
    import numpy as np
    H, W = binary.shape
    x0, y0, x1, y1 = max(0, int(box[0])), max(0, int(box[1])), min(W, int(box[2])), min(H, int(box[3]))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return []
    sub = (binary[y0:y1, x0:x1] == 0).astype(np.uint8)
    _n, _lab, stats, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    return [(x0 + int(st[0]), y0 + int(st[1]), x0 + int(st[0] + st[2]), y0 + int(st[1] + st[3]))
            for st in stats[1:] if int(st[4]) >= 6]


def margin_label_box(binary: Any, region: Sequence[float], spacing: float, avoid: Iterable[Sequence[float]] = ()) -> Optional[List[float]]:
    """The page box of ONE instrument name's ink inside `region` (the margin strip the label was read from, cut to its staff's band):
    the union of the ink components in it that are text-sized (at most `LABEL_MAX_COMPONENT_SPACES` tall: a brace, bracket or barline is
    taller) and not inside an `avoid` box (the brackets and braces the claimant already holds). None when no ink. PURE."""
    if binary is None or getattr(binary, "ndim", 0) != 2 or not spacing:
        return None
    avoid = [list(a) for a in avoid]
    keep = [c for c in _components(binary, region)
            if (c[3] - c[1]) <= LABEL_MAX_COMPONENT_SPACES * spacing and not any(_overlap_small(c, a) >= 0.5 for a in avoid)]
    if not keep:
        return None
    return [float(min(c[0] for c in keep)), float(min(c[1] for c in keep)), float(max(c[2] for c in keep)), float(max(c[3] for c in keep))]


def on_traces(comp: Sequence[float], traces: Iterable[Dict[int, Tuple[float, float]]], share: float = 0.5) -> bool:
    """True when at least `share` (the register's own cut, `stroke_map.COVER_SHARE_MIN`) of the component's columns have a traced arc's row
    (`{x: (y_lo, y_hi)}`, page px, `Q.SYSTEM_ARC`'s `trace`) crossing the component's own vertical span: the arc's ink, not text. PURE."""
    x0, x1 = int(comp[0]), max(int(comp[0]) + 1, int(comp[2]))
    for tr in traces:
        hit = sum(1 for x in range(x0, x1) if x in tr and tr[x][0] <= comp[3] and tr[x][1] >= comp[1])
        if hit >= share * (x1 - x0):
            return True
    return False


def heading_blocks(binary: Any, zone: Sequence[float], spacing: float, avoid: Iterable[Sequence[float]] = (), *,
                   letter_height: Optional[float] = None, arc_traces: Iterable[Dict[int, Tuple[float, float]]] = ()) -> List[List[float]]:
    """Blocks of heading text (title, composer, plate number) in `zone`, joined while the gap between them is at most `HEADING_JOIN_SPACES`.
    Each block is a box. PURE.

    TEXT-SHAPED, not just text-sized (ROADMAP 2.221 finisher; Sean's tile 5: a slur above a staff was filed as a heading). A LETTER is a
    connected component that is at most `HEADING_MAX_COMPONENT_SPACES` tall AND wide (a long curved stroke is wider; an arc is one), at least
    half the height of `letter_height` (the page's own READ text: the median height of the ink components inside its word claims; the staff
    space when no word was read) and not owned: not inside an `avoid` claim, not along a traced arc (`arc_traces`). A block must hold at least
    TWO letters on a line; smaller ink (an i-dot, a period) joins a block it stands beside but never starts one. A single speck, a stem tip
    or one stroke is therefore never a heading."""
    if binary is None or getattr(binary, "ndim", 0) != 2 or not spacing:
        return []
    avoid = [list(a) for a in avoid]
    traces = [t for t in arc_traces if t]
    lo, hi = 0.5 * float(letter_height or spacing), HEADING_MAX_COMPONENT_SPACES * spacing
    letters, small = [], []
    for c in _components(binary, zone):
        c = [float(v) for v in c]
        if any(_overlap_small(c, a) >= 0.5 for a in avoid) or (traces and on_traces(c, traces)):
            continue
        h, w = c[3] - c[1], c[2] - c[0]
        if lo <= h <= hi and w <= hi:
            letters.append(c)
        elif h < lo and w <= hi:
            small.append(c)
    gap = HEADING_JOIN_SPACES * spacing
    blocks = [[b, 1] for b in letters]

    def _near(a, b):
        return a[0] <= b[2] + gap and b[0] <= a[2] + gap and a[1] <= b[3] + gap and b[1] <= a[3] + gap
    changed = True
    while changed:
        changed = False
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                a, b = blocks[i][0], blocks[j][0]
                if _near(a, b):
                    blocks[i] = [[min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])], blocks[i][1] + blocks[j][1]]
                    del blocks[j]
                    changed = True
                    break
            if changed:
                break
    blocks = [b for b, n in blocks if n >= 2]
    for c in small:
        for k, b in enumerate(blocks):
            if _near(b, c):
                blocks[k] = [min(b[0], c[0]), min(b[1], c[1]), max(b[2], c[2]), max(b[3], c[3])]
                break
    return sorted(blocks)


def left_edge_claims(marks: Iterable[Dict[str, Any]], detector_boxes: Iterable[Tuple[Sequence[float], str]]) -> List[Dict[str, Any]]:
    """The bracket / brace claims of ONE system from `page_wide.system_rules(...)["left_edge"]["marks"]` (the barline lane's whole marks:
    `kind` bracket | brace | systemic_barline | None, `box` top hook to bottom hook, `staff_indices`), with the detector's own `brace` /
    `bracket` boxes (`(page box, class name)`, already filtered to the system's left edge) as the SECOND WITNESS; PURE.

    Per mark: `area` is the mark's whole box; `kind` as the shape reader named it (a bracket by its hook and width, a brace by its bend);
    `witness` is the class name of a detector box holding at least half of the smaller box, else None; `standing` READ for a bracket or the
    systemic barline (the shape is the evidence: hooks 0.70-1.27 sp against 0.00-0.09), READ for a brace the detector also boxed, GUESSED
    for a brace seen once and for a mark of no kind (`kind` None: the shape is filed, the ink is still claimed)."""
    out: List[Dict[str, Any]] = []
    boxes = [(list(b), str(n)) for b, n in detector_boxes]
    for m in marks:
        area = [float(v) for v in m["box"]]
        wit = next((n for b, n in boxes if _overlap_small(area, b) >= 0.5), None)
        kind = m.get("kind")
        if kind in ("bracket", "systemic_barline"):
            standing = "READ"
        elif kind == "brace":
            standing = "READ" if wit and wit.startswith("brace") else "GUESSED"
        else:
            standing = "GUESSED"
        out.append({"area": area, "kind": kind, "standing": standing, "witness": wit, "staff_indices": list(m.get("staff_indices") or ()),
                    "hook_spaces": m.get("hook_sp"), "bend_spaces": m.get("bend_sp"), "width_spaces": m.get("width_sp")})
    return out
