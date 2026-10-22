"""ROADMAP 2.186 -- ONE INK, ONE MARK (flag `OMR_ONE_INK_ONE_MARK`, default ON). STAGED GATHER (the merge) + ADJUDICATE (ownership first
for accidentals, the narrowing for rests) + EXPORT (the blue guess). Sean 2026-10-21: "the one mark one box was what I had in mind for
claiming ink. Each cell should claim its own and the one it belongs to should decide what it is not the other staff".

THE CAUSE (2.184 / 2.185, reproduced by re-running the detector): the production pass runs the detector once per CELL with class-wise NMS
(`YoloDetector.detect`, `agnostic_nms=False`, iou 0.7, conf floor 0.25). (a) INSIDE one cell every class channel scores an ink on its own,
so where two classes of ONE family both clear the floor both boxes reach GATHER; `family_precision._duplicate_box_refusal` then refuses BOTH
rests (rule 8) and `consequences.apply_printed_accidental` writes NOTHING onto a head two glyphs of different alteration own. (b) ACROSS
cells a neighbouring staff's crop boxes the same ink again; the exporter already drops the non-owner copy of a note or rest
(`glyph_owner`, `is_relocated_copy`), but NOTHING asks `glyph_owner` about an ACCIDENTAL: the copy in the wrong cell is paired with a head of
the wrong staff (`adjudicate_accidental_owner` reads the ownership of HEADS only).

THE FIX, two steps in Sean's order. (1) OWNERSHIP FIRST, at ADJUDICATE: an accidental whose own `glyph_owner` verdict names another staff
is dropped (`owned_by_another_staff`, it is the same raster read twice, never a witness); a contested accidental whose owner is not decided
abstains (`ownership_undecided`) and is counted. The stronger box of either cell never wins by confidence alone. (2) WITHIN a cell, at the
merge: boxes of DIFFERENT classes of ONE family overlapping at IoU >= `ONE_INK_IOU_MIN` become ONE box -- the stronger class, carrying every
weaker class and the confidence margin (`rivals`, `margin`); the weaker boxes are never filed, so no later rule sees two boxes for one mark,
and the surviving box goes through EVERY later rule (a stem tip, a barline, a letter still refuse it by the rule that names them).

FAMILIES are the existing `yolo_detector._CATEGORY_MAP` categories `rest` and `accidental`, and nothing else:
  * `key*` classes are NOT merged (the key signature owns them; ROADMAP 2.183 fences them, as `yolo_detector`'s own 2.12g note does);
  * FLAGS ARE NOT MERGED. `rhythm.adjudicate_duration` already treats a `flag8th*` + `flag16th*` pair as a DISAGREEMENT of two votes and
    settles it with a second witness (the stem-tip hook count) or NARROWS (`flags_disagree`); a merge would replace that by an argmax of
    detector confidence -- a fallback converting "cannot tell" into an answer (rule 8). FINDINGS records what became of the 76 pairs;
  * heads: 2.12g's role-twin collapse and 2.30's duplicate rule own them; dots, clefs, dynamics, arcs are untouched.
SAME-CLASS doubles inside a cell are left alone. NEVER ACROSS FAMILIES: an accidental beside a head, a rest under a chord stay two marks.

READ OR GUESSED. A merged box is READ only when `reads(margin)`: the margin clears `ONE_INK_READ_MARGIN`. That bar is None until Sean sets it
on blind tiles (CLAUDE section 4, rule 5: never tuned on two plates), so EVERY merged box is GUESSED (blue) carrying its candidates. A
merged rest is NARROWED `{rest, not a rest}` (reason `one_ink_merged`); a merged accidental stays DECIDED on the record and the head it
alters and the later notes it governs are written GUESSED (`export.one_ink_guess_of`).

REGISTER (2.181): NOT USED. `claims.covering` only reads rows, but the filer (`gather_claimed_register`) and the one consult
(`claimed_by.consult`, owners `clef|leading_column|meter`, any other owner falls into the `leading_column` branch) are register internals
2.183 is editing; an `ink` owner cannot be expressed without editing them. Reported in FINDINGS, not done.
"""
from __future__ import annotations

import dataclasses
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ONE_INK_ENV = "OMR_ONE_INK_ONE_MARK"
ONE_INK_REASON = "one_ink_merged"
OWNED_ELSEWHERE_REASON = "owned_by_another_staff"
OWNERSHIP_UNDECIDED_REASON = "ownership_undecided"
ABSORBED_REASON = "one_ink_absorbed"

#: The overlap that means "the same ink". 2.185 checked it on crops (20/20 random crops at >= 0.5 real doubles; the 0.3-0.5 band was half
#: neighbours). A convention checked on crops, not a measurement tuned for this lane.
ONE_INK_IOU_MIN = 0.5

#: The `yolo_detector._CATEGORY_MAP` categories this merge is allowed to act inside.
ONE_INK_FAMILIES = ("rest", "accidental")

#: The detector-confidence margin at or above which a merged box is READ instead of GUESSED. None = no margin reads (every merged box is
#: GUESSED): it is Sean's to set on blind tiles, never tuned on the two plates (CLAUDE section 4).
ONE_INK_READ_MARGIN: Optional[float] = None


def enabled() -> bool:
    """`OMR_ONE_INK_ONE_MARK`, default ON (ROADMAP 2.186, Sean 2026-10-22); an explicit 0/false/no/off disables."""
    return os.environ.get(ONE_INK_ENV, "").strip().lower() not in ("0", "false", "no", "off")


def reads(margin: Optional[float]) -> bool:
    """Does this margin clear the (unset) READ bar? With the bar unset nothing reads."""
    return ONE_INK_READ_MARGIN is not None and margin is not None and margin >= ONE_INK_READ_MARGIN


def family_of(class_name: str) -> Optional[str]:
    """The merge family of a detector class, or None. Derived from the detector's own category map, minus `key*`."""
    from ..yolo_detector import _class_name_to_category
    if str(class_name).lower().startswith("key"):
        return None
    cat = _class_name_to_category(str(class_name))
    return cat if cat in ONE_INK_FAMILIES else None


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    """IoU of two `(x, y, w, h)` boxes in ONE cell's canonical frame (shared inside a cell, so the ratio is exact)."""
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    iw = max(0.0, min(ax0 + aw, bx0 + bw) - max(ax0, bx0))
    ih = max(0.0, min(ay0 + ah, by0 + bh) - max(ay0, by0))
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def plan(boxes: Sequence[Tuple[str, float, float, float, float, float]]) -> Dict[int, Dict[str, Any]]:
    """The merge on plain tuples `(class, x, y, w, h, conf)` of ONE cell -- the one function the live path and the record replay share.

    Returns `{winner_index: {"absorbed": [index...], "rivals": [{"class", "conf"}...], "margin": float}}`. Greedy by descending confidence
    (ties: lower index): a box not yet absorbed absorbs every later-ranked, not-yet-absorbed box of the same family whose CLASS differs and
    whose IoU with it is >= `ONE_INK_IOU_MIN`. Winner-centred, not chained. A same-class box that overlaps is left alone."""
    order = sorted(range(len(boxes)), key=lambda i: (-float(boxes[i][5]), i))
    fam = [family_of(b[0]) for b in boxes]
    taken: set = set()
    out: Dict[int, Dict[str, Any]] = {}
    for pos, i in enumerate(order):
        if i in taken or fam[i] is None:
            continue
        mine: List[int] = []
        for j in order[pos + 1:]:
            if j in taken or fam[j] != fam[i] or boxes[j][0] == boxes[i][0]:
                continue
            if iou(boxes[i][1:5], boxes[j][1:5]) >= ONE_INK_IOU_MIN:
                mine.append(j)
        if mine:
            taken.update(mine)
            out[i] = {"absorbed": mine,
                      "rivals": [{"class": str(boxes[j][0]), "conf": round(float(boxes[j][5]), 4)} for j in mine],
                      "margin": round(float(boxes[i][5]) - max(float(boxes[j][5]) for j in mine), 4)}
    return out


def detail_of(info: Optional[Dict[str, Any]], winner_class: str, winner_conf: float) -> Dict[str, Any]:
    """The `one_ink` row detail a merged box carries, or {} for an untouched box."""
    if not info:
        return {}
    return {"one_ink": {"rivals": [dict(r) for r in info["rivals"]], "margin": info["margin"],
                        "winner": {"class": str(winner_class), "conf": round(float(winner_conf), 4)},
                        "iou_min": ONE_INK_IOU_MIN}}


def merge(detections: Sequence[Any]) -> List[Any]:
    """LIVE path (GATHER, right after `detector.detect`): `SymbolDetection`s of ONE cell in, SAME-LENGTH, SAME-ORDER list out -- so every glyph index
    (the key Sean's answers, the review corrections and the judged index name) is unchanged. A winner is a copy with `one_ink_rivals` /
    `one_ink_margin` set; an absorbed box is kept as a copy with `one_ink_absorbed_by` = its winner's index and is REFUSED downstream as a
    duplicate (the rest rule `rest_is_a_duplicate_box`, the accidental owner `one_ink_absorbed`), exactly as every other refused box is kept."""
    if len(detections) < 2:
        return list(detections)
    boxes = [(d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical, d.confidence) for d in detections]
    p = plan(boxes)
    if not p:
        return list(detections)
    winner_of = {j: i for i, info in p.items() for j in info["absorbed"]}
    out: List[Any] = []
    for i, d in enumerate(detections):
        info = p.get(i)
        if info is not None:
            d = dataclasses.replace(d, one_ink_rivals=tuple((r["class"], r["conf"]) for r in info["rivals"]), one_ink_margin=info["margin"])
        elif i in winner_of:
            d = dataclasses.replace(d, one_ink_absorbed_by=winner_of[i])
        out.append(d)
    return out


def box_detail(d: Any) -> Dict[str, Any]:
    """`one_ink` for a GLYPH_BOX / ACCIDENTAL_STAFF_POSITION row detail, from a merged `SymbolDetection`; {} otherwise."""
    absorbed = getattr(d, "one_ink_absorbed_by", None)
    if absorbed is not None:
        return {"one_ink_absorbed_by_index": int(absorbed)}
    rivals = getattr(d, "one_ink_rivals", None)
    if not rivals:
        return {}
    return detail_of({"rivals": [{"class": c, "conf": f} for c, f in rivals], "margin": getattr(d, "one_ink_margin", None)},
                     d.smufl_name, d.confidence)


def candidates_of(one_ink: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The merged box's candidate classes for a guess, the chosen (winner) first."""
    w = one_ink.get("winner") or {}
    return [{"value": w.get("class"), "support": w.get("conf")}] + \
           [{"value": r.get("class"), "support": r.get("conf")} for r in one_ink.get("rivals") or ()]
