#!/usr/bin/env python3
"""l281_truth: what a notehead on Sean's hand-labeled page is WRITTEN as, derived from
HIS boxes -- the stem it stands on, the beams and flags on that stem, the dots by it,
its fill. ROADMAP 2.81 Phase 1, measure (a).

SOURCE. `data/hand-truth/pages/imslp317803/0.json` (Brahms 317803, pdf index 0), read
through `tools.omr.hand_truth.store.load`, never written. Only heads in a FULLY LABELED
measure cell are judged (a box in a cell nobody swept says nothing about what is NOT
printed there). The record's side is never consulted here: this module reads the truth
alone, so a head's written value does not depend on our reading (rule 7: Sean's boxes
are the evidence).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (rule 3; nobody was asked
about THIS derivation, though the boxes are Sean's):
  * a head STANDS ON the truth `stem` box whose x-span reaches within `STEM_X_SPACES`
    of the head box and whose y-span overlaps the head's by at least a third of the
    head's height; the TIP is the stem's end farther from the head's centre;
  * a BEAM LEVEL on that stem is a truth `beam` box whose x-span covers the stem's x
    and whose y-span reaches the stem's tip end (within `TIP_REACH_SPACES` of the tip,
    walking inward); boxes whose y-spans overlap by more than half are ONE level;
  * a FLAG on that stem is a truth `flag8th*`/`flag16th*`/... box whose x starts within
    `FLAG_X_SPACES` of the stem and whose y-span reaches the tip end; level 1/2/3/4 from
    its class; the larger of beam levels and flag level is the stem's level;
  * a DOT is a truth `augmentationDot` box whose centre lies within `DOT_X_SPACES` right
    of the head and within `DOT_Y_SPACES` of the head's centre line (a dot sits a space
    higher on a line note: the window is asymmetric, CLAUDE.md §10);
  * a TREMOLO slash (`tremolo*`) crossing the stem is NOT a beam level and never shortens
    the value (Sean, DECISIONS 2026-10-09; ROADMAP 2.71).
Falsified by a head whose truth value, read off the crop, differs from what this derives
-- `l281_truth.py --crops` cuts them so they can be looked at.

The derivation does not decide "right/wrong" for a head it cannot place: a filled head
with NO stem box under it is `no_truth_stem` (a quarter with a missed stem box and a
head the detector doubled look the same), reported separately and never counted.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.hand_truth import score as S, store  # noqa: E402

PAGE_PATH = REPO / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json"

STEM_X_SPACES = 0.35
TIP_REACH_SPACES = 2.6
FLAG_X_SPACES = 0.6
DOT_X_SPACES = 1.8
DOT_Y_SPACES = 0.8
DOT_RAISE_SPACES = 0.5
STEM_TOUCH_SPACES = 0.35
MARK_REACH_SPACES = 5.0
FLAG_X_FROM_HEAD_SPACES = 1.6
FLAG_LEVEL = (("flag64th", 4), ("flag32nd", 3), ("flag16th", 2), ("flag8th", 1),
              ("flag128th", 5))


def cx(r):
    return (r[0] + r[2]) / 2.0


def cy(r):
    return (r[1] + r[3]) / 2.0


def flag_level(cls):
    for p, lv in FLAG_LEVEL:
        if str(cls).startswith(p):
            return lv
    return 1


def hbase(cls):
    c = str(cls)
    if c.startswith("noteheadBlack"):
        return 1.0
    if c.startswith("noteheadHalf"):
        return 2.0
    if c.startswith("noteheadWhole"):
        return 4.0
    if c.startswith("noteheadDoubleWhole"):
        return 8.0
    return None


def in_full_cell(full, r):
    x, y = cx(r), cy(r)
    for c in full:
        if c.rect[0] <= x < c.rect[2] and c.rect[1] <= y < c.rect[3]:
            return c
    return None


def merge_levels(boxes):
    """Boxes (x0,y0,x1,y1) -> the count of distinct stacked levels (y-overlap > 50% = one)."""
    boxes = sorted(boxes, key=lambda b: cy(b))
    levels = []
    for b in boxes:
        for lv in levels:
            ov = min(b[3], lv[3]) - max(b[1], lv[1])
            if ov > 0.5 * min(b[3] - b[1], lv[3] - lv[1]):
                break
        else:
            levels.append(b)
    return len(levels)


class Truth:
    def __init__(self, path=PAGE_PATH):
        self.page = store.load(Path(path))
        self.items = S.truth_items(self.page, derive=True)
        self.full = S.fully_labeled(self.page)
        bands = S.staff_bands(self.page)
        import statistics
        self.space = statistics.median([b.space for b in bands])
        by = collections.defaultdict(list)
        for it in self.items:
            by[it.cls if it.family not in ("flag", "tremolo") else it.family].append(it)
        self.stems = [i for i in self.items if i.cls == "stem"]
        self.beams = [i for i in self.items if i.family == "beam"]
        self.flags = [i for i in self.items if i.family == "flag"]
        self.dots = [i for i in self.items if i.family == "augmentation_dot"]
        self.trems = [i for i in self.items if i.family == "tremolo"]
        self.heads = [i for i in self.items if i.family == "notehead"]

    def stem_of(self, h):
        """The truth stem boxes this head stands on (a chord's heads share one)."""
        sp = self.space
        out = []
        for s in self.stems:
            r = s.rect
            if r[0] > h.rect[2] + STEM_X_SPACES * sp or r[2] < h.rect[0] - STEM_X_SPACES * sp:
                continue
            # Sean's stem box usually starts where the head's own ink ends (the head's bottom edge
            # for a down-stem), so TOUCHING the head box counts: the stem's y-span meets the head's
            # y-span widened by `STEM_TOUCH_SPACES`.
            tol = STEM_TOUCH_SPACES * sp
            if min(r[3], h.rect[3] + tol) - max(r[1], h.rect[1] - tol) > 0:
                out.append(s)
        return out

    def marks_near(self, h):
        """Flag / beam truth boxes that are THIS head's, for a head whose stem Sean did not box.

        A flag belongs to the head whose x-interval is nearest the flag box's left edge (ties =
        a chord, all share it) and whose centre is within `MARK_REACH_SPACES` vertically. A beam
        belongs to the heads whose centre x lies within the beam's x-span (+/- 0.4 space) and
        whose centre is within `MARK_REACH_SPACES` vertically of the beam's centre line. A head
        that has a different head nearer a flag does not claim it."""
        sp = self.space
        reach = MARK_REACH_SPACES * sp
        out = {"flags": [], "beams": []}
        hx0, hx1, hy = h.rect[0], h.rect[2], cy(h.rect)
        for f in self.flags:
            r = f.rect
            if abs(cy(r) - hy) > reach:
                continue
            best, mine = None, None
            for o in self.heads:
                if abs(cy(r) - cy(o.rect)) > reach:
                    continue
                dx = 0.0 if o.rect[0] <= r[0] <= o.rect[2] else min(abs(r[0] - o.rect[0]), abs(r[0] - o.rect[2]))
                if best is None or dx < best - 1e-6:
                    best = dx
                if o.idx == h.idx:
                    mine = dx
            if mine is not None and best is not None and mine <= best + 0.4 * sp \
                    and mine <= FLAG_X_FROM_HEAD_SPACES * sp:
                out["flags"].append(f.id)
        for b in self.beams:
            r = b.rect
            if r[0] - 0.4 * sp <= cx(h.rect) <= r[2] + 0.4 * sp and abs(cy(r) - hy) <= reach:
                out["beams"].append(b.id)
        return out

    def derive(self, h):
        """The head's written value from the truth boxes. Returns a dict."""
        sp = self.space
        base = hbase(h.cls)
        cell = in_full_cell(self.full, h.rect)
        d = {"idx": h.idx, "id": h.id, "cls": h.cls, "rect": [round(v, 1) for v in h.rect],
             "base": base, "full_cell": cell.id if cell else None}
        stems = self.stem_of(h)
        d["n_stems"] = len(stems)
        if not stems:
            # Sean did not box this head's stem (stems are CV-only: he drew only some). The head is
            # NOT judged right on that account. A flag or beam box of his that is plainly THIS head's
            # (nearest head by x, within a stem's reach) is evidence it is NOT level 0: reported as
            # `marks_near` so the caller can bound the page, never counted as a right answer.
            d.update(status="no_truth_stem", levels=None, dots=None, marks_near=self.marks_near(h))
            return d
        # the stem the head stands on: the one nearest the head's side edge
        stem = min(stems, key=lambda s: min(abs(cx(s.rect) - h.rect[0]), abs(cx(s.rect) - h.rect[2])))
        up = cy(stem.rect) < cy(h.rect) or (stem.rect[1] + stem.rect[3]) / 2 < cy(h.rect)
        # tip = the end farther from the head's centre
        top_gap = abs(stem.rect[1] - cy(h.rect))
        bot_gap = abs(stem.rect[3] - cy(h.rect))
        tip_end = "top" if top_gap >= bot_gap else "bottom"
        tip_y = stem.rect[1] if tip_end == "top" else stem.rect[3]
        sx0, sx1 = stem.rect[0], stem.rect[2]
        reach = TIP_REACH_SPACES * sp
        y_lo, y_hi = (tip_y - 0.6 * sp, tip_y + reach) if tip_end == "top" else (tip_y - reach, tip_y + 0.6 * sp)
        beams = []
        beam_ids = []
        for b in self.beams:
            r = b.rect
            if r[0] <= (sx0 + sx1) / 2 + 0.3 * sp and r[2] >= (sx0 + sx1) / 2 - 0.3 * sp:
                if r[3] >= y_lo and r[1] <= y_hi:
                    beams.append(r)
                    beam_ids.append(b.id)
        flags = []
        for f in self.flags:
            r = f.rect
            if r[0] >= sx0 - FLAG_X_SPACES * sp and r[0] <= sx1 + FLAG_X_SPACES * sp:
                if r[3] >= y_lo and r[1] <= y_hi:
                    flags.append(f)
        trem = [t for t in self.trems
                if t.rect[0] <= sx1 + 1.2 * sp and t.rect[2] >= sx0 - 1.2 * sp
                and t.rect[3] >= stem.rect[1] and t.rect[1] <= stem.rect[3]]
        levels_b = merge_levels(beams)
        levels_f = max([flag_level(f.cls) for f in flags], default=0)
        levels = max(levels_b, levels_f)
        dots = []
        for dd in self.dots:
            dx = cx(dd.rect) - h.rect[2]
            dy = cy(dd.rect) - cy(h.rect)
            if 0.0 <= dx <= DOT_X_SPACES * sp and -DOT_Y_SPACES * sp <= dy <= 0.6 * sp:
                # a dot belongs to the NEAREST head in y among the heads it could stand beside (a
                # stacked pair, a second at a space's distance, has a dot of its own each); a dot on a
                # line note sits a space higher, so the distance is measured from the head's centre
                # raised by `DOT_RAISE_SPACES` for a line note
                mine = abs(dy + (DOT_RAISE_SPACES * sp if h.cls.endswith("OnLine") else 0.0))
                rivals = []
                for o in self.heads:
                    if o.idx == h.idx or o.rect[2] > dd.rect[0] or dd.rect[0] - o.rect[2] > DOT_X_SPACES * sp:
                        continue
                    odx = cy(dd.rect) - cy(o.rect)
                    rivals.append(abs(odx + (DOT_RAISE_SPACES * sp if o.cls.endswith("OnLine") else 0.0)))
                if all(mine <= r for r in rivals):
                    dots.append(dd)
        d.update(status="ok", stem=stem.id, stem_rect=[round(v, 1) for v in stem.rect],
                 tip_end=tip_end, levels=levels, levels_beam=levels_b, levels_flag=levels_f,
                 dots=len(dots), tremolo=len(trem), n_beam_boxes=len(beams),
                 n_flag_boxes=len(flags), beam_ids=beam_ids, flag_ids=[f.id for f in flags])
        if base is not None:
            t = base / (2 ** levels) if levels else base
            add = t
            for _ in range(len(dots)):
                add /= 2.0
                t += add
            d["written"] = t
        return d

    def derive_all(self):
        return [self.derive(h) for h in self.heads if in_full_cell(self.full, h.rect)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    T = Truth()
    ds = T.derive_all()
    print(f"truth heads in fully labeled cells: {len(ds)} (of {len(T.heads)}); space {T.space:.1f}px")
    print("status:", dict(collections.Counter(d["status"] for d in ds)))
    ok = [d for d in ds if d["status"] == "ok"]
    print("fill:", dict(collections.Counter(("black" if d["base"] == 1.0 else "open") for d in ok)))
    print("levels (all):", dict(collections.Counter(d["levels"] for d in ok)))
    print("levels (black):", dict(collections.Counter(d["levels"] for d in ok if d["base"] == 1.0)))
    print("dots:", dict(collections.Counter(d["dots"] for d in ok)))
    print("tremolo:", dict(collections.Counter(d["tremolo"] for d in ok)))
    print("written (black):", dict(collections.Counter(d.get("written") for d in ok if d["base"] == 1.0)))
    if a.out:
        Path(a.out).write_text(json.dumps(ds, separators=(",", ":")))


if __name__ == "__main__":
    main()
