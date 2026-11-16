"""ROADMAP 2.311 -- THE RED-BAR RANKING CLASSIFIER: the first thing that stopped each red bar, in a musician's words, from the record.

Reads only: the saved facts file (`extract.py`) and the few record rows `redbar_extra.py` pulled. Decides nothing, writes nothing into a record.

A red bar is `redbars.red_bars` (the 309 Litolff / 276 Brahms the 2.311 count used). The FIRST CAUSE keeps `redbars.cause_of`'s order (Sean read
12 random bars aloud and its cause matched every time): staff lost > a read mark not written > nothing boxed at all > every mark twin/owned
elsewhere > the sum. Each vague bucket is then split by a mechanism TEST on the record's own rows; where no test fires the row says so
("unexplained"). Tests, in the order tried, and what each reads:

  short sum    1 missed dot     a plain written note whose half-value fills the shortfall EXACTLY, with dot evidence right of the head:
                                (a) a detector dot box decided `augmentation` that no note carries, (b) a dot box whose role is undecided,
                                (c) NO dot box but a dot-sized unclassified ink piece (0.15-0.7 space each way, not an arc/stem/beam) right of it
               2 foreign note   a written note nearer another staff of the system than this one (counted here)
               3 unboxed rest   an unboxed-ink-is-a-rest verdict that abstained (shape cannot tell / claimed by another class / head beside it)
               4 head given away a head standing on this staff's own lines given to another staff (`owned_by_another_staff`)
               5 all guessed    every written mark of the bar is GUESSED (blue): the sum inherits the guesses
               6 beam/flag value a note written shorter than a quarter, its value from beams or flags (the weakest witness)
               7 unexplained
  long sum     1 foreign note  2 duplicate head (two written heads on one place)  3 a printed tuplet mark in the bar  4 a small (grace-sized) head
               5 a dot written that, taken away, fills the bar exactly  6 all guessed  7 unexplained
  two voices   the foreign / duplicate / tuplet tests, then the short tests on the short voice, else unexplained

Distances are in staff spaces of THIS staff (`staff_lines`); the dot window is the one `dotcheck.py` used (0.3 space inside the head's right edge to
3.5 spaces beyond, within 1.2 spaces of its centre) with the dot-sized ink size above.
"""
from __future__ import annotations

import collections
import itertools
import json
import math

from redbars import STAFF_LOST, red_bars, cause_of
from tools.omr.staged.export import _NOT_A_GAP_REASONS

QV = {"whole": 4.0, "half": 2.0, "quarter": 1.0, "eighth": 0.5, "16th": 0.25, "32nd": 0.125, "64th": 0.0625}
INK_MIN = 375000          # generic unclassified ink pieces (Q.INK); 350000.. are rest candidates
REST_CAND = 350000
OTHERS = ("owned_by_another_staff", "not_a_notehead:belongs_to_a_nearer_staff")


class Ctx:
    def __init__(self, plate: str, f: dict, extra: dict, pages: set):
        self.plate, self.f, self.pages = plate, f, pages
        self.lines = {tuple(int(x) for x in k.split("/")): v for k, v in extra["staff_lines"].items()}
        self.roles = extra["dot_role"]
        self.cell_box = {tuple(int(x) for x in k.split("/")): v for k, v in extra["cell_box"].items()}
        self.cell = collections.defaultdict(list)          # (page, system, staff, cell) -> [(key, glyph)]
        self.small_ink = collections.defaultdict(list)     # page -> [(key, glyph)] dot-sized unclassified pieces
        self.dots = collections.defaultdict(list)          # page -> detector augmentationDot boxes
        for k, g in f["glyphs"].items():
            p = k.split("/")
            if len(p) != 6:
                continue
            ck = tuple(int(x) for x in p[1:5])
            if ck[0] not in pages:
                continue
            self.cell[ck].append((k, g))
            if g["cls"] == "augmentationDot":
                self.dots[ck[0]].append((k, g))
            elif g["cls"] is None and int(p[5]) >= INK_MIN:
                sp = self.sp(ck)
                if sp and _dot_sized(g["box"], sp):
                    self.small_ink[(ck[0], ck[1])].append((k, g))
        self.written = collections.defaultdict(list)       # glyph key -> written rows
        for w in f["written"]:
            self.written[w.get("rg", "")].append(w)

    def sp(self, key) -> float | None:
        ln = self.lines.get(tuple(key[:3]))
        return (ln[4] - ln[0]) / 4.0 if ln else None

    def piece_sizes(self, key):
        """dot-sized unclassified ink pieces of the page, built lazily from the cells of the bar's neighbourhood."""
        return self.small_ink[key[0]]


def _dot_sized(box, sp) -> bool:
    w, h = (box[2] - box[0]) / sp, (box[3] - box[1]) / sp
    return 0.3 <= w <= 0.8 and 0.3 <= h <= 0.8          # the size `dotcheck.py` used for "dot-sized"


def _rows(ctx: Ctx, b: dict) -> list:
    pre = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
    seen, out = set(), []
    for rg in [g for g in b.get("glyphs", [])] + [k for k in ctx.written if k.startswith(pre)]:
        if rg in seen:
            continue
        seen.add(rg)
        out += ctx.written.get(rg, [])
    return out


def _dur(w) -> float | None:
    t = QV.get(w["type"])
    if t is None:
        return None
    d = len((w.get("sub") or {}).get("dot") or [])
    return t * (2 - 0.5 ** d)


def _near_dot_evidence(ctx: Ctx, key, w, sp) -> str | None:
    """dot evidence right of written note `w`: 'boxed_augmentation' | 'boxed_undecided' | 'ink_never_boxed' | None."""
    box = w["box"]
    cy = (box[1] + box[3]) / 2.0
    best = None
    page = key[0]
    for k, g in ctx.dots[page]:
        d = g["box"]
        dcx, dcy = (d[0] + d[2]) / 2, (d[1] + d[3]) / 2
        if box[2] - 0.3 * sp <= dcx <= box[2] + 3.5 * sp and abs(dcy - cy) <= 1.2 * sp:
            role = ctx.roles.get(k) or [None, None, None]
            if role[1] == "augmentation":
                return "boxed_augmentation"
            if role[1] in ("staccato", "staccatissimo"):
                continue
            best = "boxed_undecided"
    if best:
        return best
    # no dot box: a dot-sized unclassified ink piece in the window (pieces live in the cells of the page; look in this system's cells)
    for k, g in ctx.small_ink[(page, key[1])]:
        d = g["box"]
        dcx, dcy = (d[0] + d[2]) / 2, (d[1] + d[3]) / 2
        if box[2] - 0.3 * sp <= dcx <= box[2] + 3.5 * sp and abs(dcy - cy) <= 1.2 * sp:
            return "ink_never_boxed"
    return None


def _subset_hits(cands: list, need: float) -> list | None:
    for r in range(1, min(len(cands), 6) + 1):
        for comb in itertools.combinations(cands, r):
            if abs(sum(c[1] for c in comb) - need) < 1e-6:
                return list(comb)
    return None


def _nearer_other_staff(ctx: Ctx, key, w, sp) -> bool:
    ln = ctx.lines.get(tuple(key[:3]))
    cy = w["cy"]
    own = max(0.0, (ln[0] - cy) / sp, (cy - ln[4]) / sp)
    if own <= 3.0:
        return False
    best = 1e9
    for k, other in ctx.lines.items():
        if k[0] == key[0] and k[1] == key[1] and k[2] != key[2]:
            osp = (other[4] - other[0]) / 4.0
            best = min(best, max(0.0, (other[0] - cy) / osp, (cy - other[4]) / osp))
    return best + 1.0 < own


def _same_place(a, c) -> bool:
    return all(abs(a["box"][i] - c["box"][i]) < 3 for i in range(4))


def _voice_is_a_copy(rows: list, want: float) -> bool:
    """a voice that does not fill the bar, every mark of which stands on the very place of a mark of a voice that does: a copy, not a second part."""
    byv = collections.defaultdict(list)
    for w in rows:
        if w["type"] != "?":
            byv[w.get("voice")].append(w)
    if len(byv) < 2:
        return False

    def total(ws):
        on = {}
        for w in ws:
            on[w.get("onset")] = max(on.get(w.get("onset"), 0.0), _dur(w) or 0.0)
        return sum(on.values())
    good = [v for v, ws in byv.items() if abs(total(ws) - want) < 1e-6]
    bad = [v for v in byv if v not in good]
    if not good or not bad:
        return False
    others = [o for v in good for o in byv[v]]
    return all(any(_same_place(w, o) for o in others) for v in bad for w in byv[v])


def sum_mechanism(ctx: Ctx, b: dict, rows: list, side: str) -> tuple:
    """-> (row key, detail). `side` is short / long / two voices."""
    key = (b["page"], b["system"], b["staff"], b["cell"])
    sp = ctx.sp(key)
    want, got = b.get("want_quarters"), b.get("counted_quarters") or []
    notes = [w for w in rows if w["kind"] == "note"]
    plain = [w for w in notes if not w.get("blue")]
    det = {}
    if sp is None or want is None or not got:
        return "sum_unexplained", det
    if _voice_is_a_copy(rows, want):
        return "sum_voice_is_a_copy", det
    # foreign note (any side): a note counted here that stands nearer another staff
    foreign = [w for w in notes if _nearer_other_staff(ctx, key, w, sp)]
    if foreign:
        det["foreign"] = len(foreign)
        return "sum_foreign_note", det
    # duplicate head: two written note rows whose boxes cover each other
    for a, c in itertools.combinations(notes, 2):
        ix = min(a["box"][2], c["box"][2]) - max(a["box"][0], c["box"][0])
        iy = min(a["box"][3], c["box"][3]) - max(a["box"][1], c["box"][1])
        if ix > 0 and iy > 0 and ix * iy > 0.5 * min((a["box"][2] - a["box"][0]) * (a["box"][3] - a["box"][1]),
                                                        (c["box"][2] - c["box"][0]) * (c["box"][3] - c["box"][1])) and a.get("onset") != c.get("onset"):
            det["duplicate"] = True
            return "sum_duplicate_head", det
    tup = [g for k, g in ctx.cell[key] if g["cls"] in ("tuplet3", "tupletBracket")]
    if tup:
        return "sum_tuplet_mark", det
    if side in ("short", "two voices"):
        short = [c for c in got if c < want - 1e-6]
        if short:
            need = want - max(short) if len(short) == len(got) else want - min(short)
            need = round(need, 6)
            cands = []
            for w in plain:
                d = _dur(w)
                if d is None or (w.get("sub") or {}).get("dot"):
                    continue
                ev = _near_dot_evidence(ctx, key, w, sp)
                if ev:
                    cands.append((w, d / 2.0, ev))
            hit = _subset_hits(cands, need)
            if hit:
                order = ["boxed_augmentation", "boxed_undecided", "ink_never_boxed"]
                ev = min((h[2] for h in hit), key=order.index)
                det["dot_evidence"] = ev
                det["dot_notes"] = len(hit)
                return "sum_short_dot_" + ev, det
    if side == "long":
        dotted = [w for w in notes if (w.get("sub") or {}).get("dot")]
        over = min(got) - want
        for w in dotted:
            d = _dur(w)
            nd = len((w.get("sub") or {}).get("dot") or [])
            if d is not None and nd == 1 and abs(d - d / 1.5 - over) < 1e-6:
                det["spurious_dot"] = True
                return "sum_long_dot_written_too_many", det
        small = [w for w in notes if (w["box"][3] - w["box"][1]) < 0.75 * sp]
        if small:
            return "sum_small_head", det
        for w in rows:
            if w["kind"] == "rest" and w["type"] == "whole" and any(o is not w and o.get("voice") == w.get("voice") and o["type"] != "?" and
                                                                      o.get("onset") != w.get("onset") for o in rows):
                return "sum_long_whole_rest_beside_notes", det
        over = round(min(got) - want, 6)
        cell = ctx.f["cells"].get("cell/%d/%d/%d/%d" % key)
        if cell:
            edge = [w for w in notes if _dur(w) is not None and abs(_dur(w) - over) < 1e-6 and
                    (w["cx"] <= cell[0] + 1.0 * sp or w["cx"] >= cell[2] - 1.0 * sp)]
            if edge:
                return "sum_long_note_at_barline", det
        rests = [w for w in rows if w["kind"] == "rest" and _dur(w) is not None]
        if any(abs(_dur(w) - over) < 1e-6 or abs(_dur(w) / 2.0 - over) < 1e-6 for w in rests) and len(got) == 1:
            return "sum_long_a_rest_too_long", det
        step = [w for w in plain if _dur(w) is not None and abs(_dur(w) / 2.0 - over) < 1e-6 and not (w.get("sub") or {}).get("dot")]
        # one note a step shorter would fill the bar: the note is a half/quarter/eighth whose flag/beam/head the bar may contradict
        if step and len(got) == 1:
            det["step_types"] = sorted({w["type"] for w in step})
            return "sum_long_one_note_a_step_long", det
        if len(got) == 1 and min(got) in (2.0, 3.0, 4.0, 6.0) and abs(min(got) - want) > 1e-6:
            return "sum_long_fills_another_meter", det
    if side in ("short", "two voices"):
        for k, g in ctx.cell[key]:
            if g["cls"] is None and REST_CAND <= int(k.split("/")[-1]) < INK_MIN and g.get("v"):
                u = g["v"].get("unboxed_ink_is_a_rest") or {}
                if u.get("outcome") == "abstained" and u.get("reason") in ("shape_cannot_tell", "claimed_by_another_class", "head_beside_it") \
                        and g["fate"] is None:
                    det["unboxed"] = u.get("reason")
                    return "sum_unboxed_rest_ink", det
        um = unboxed_marks(ctx, key)
        if um:
            det["unboxed_ink"] = um[:4]
            return "sum_unboxed_mark_ink", det
        ln = ctx.lines.get(key[:3])
        for k, g in ctx.cell[key]:
            if g["head"] and g["fate"] == "owned_by_another_staff":
                cy = (g["box"][1] + g["box"][3]) / 2.0
                if ln[0] - 1.5 * sp <= cy <= ln[4] + 1.5 * sp:
                    return "sum_head_given_away", det
    onsets = {(w.get("voice"), w.get("onset")) for w in rows if w["type"] != "?"}
    if side == "short" and len(onsets) == 1 and not any(w.get("blue") for w in rows):
        return "sum_short_single_event", det
    if rows and all(w.get("blue") for w in rows if w["type"] != "?"):
        return "sum_all_guessed", det
    if side in ("short", "two voices") and any(w["type"] in ("eighth", "16th", "32nd") for w in notes):
        return "sum_beam_flag_values", det
    return "sum_unexplained", det


def unboxed_marks(ctx: Ctx, key) -> list:
    """unclassified ink pieces of this bar standing on the staff, mark-sized, inside no detector box (a note/rest the detector never boxed)."""
    sp = ctx.sp(key)
    ln = ctx.lines.get(key[:3])
    cell = ctx.f["cells"].get("cell/%d/%d/%d/%d" % key)
    if sp is None or ln is None or cell is None:
        return []
    boxes = [g["box"] for k, g in ctx.cell[key] if g["cls"] not in (None, "staff") ]
    out = []
    for k, g in ctx.cell[key]:
        if g["cls"] is not None or int(k.split("/")[-1]) < INK_MIN:
            continue
        b = g["box"]
        w, h = (b[2] - b[0]) / sp, (b[3] - b[1]) / sp
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        # head-sized (0.8-2.0 x 0.6-1.6 spaces) or rest-sized (0.5-1.8 x 1.4-3.5): the sizes a note or a rest ink piece has; any other piece is a
        # stroke, a slur remnant or text. These sizes are ours (a measurement, not a convention): the control in `base_rates` says how often they fire.
        if not ((0.8 <= w <= 2.0 and 0.6 <= h <= 1.6) or (0.5 <= w <= 1.8 and 1.4 <= h <= 3.5)):
            continue
        if not (ln[0] - 1.5 * sp <= cy <= ln[4] + 1.5 * sp) or not (cell[0] + 0.8 * sp <= cx <= cell[2] - 0.8 * sp):
            continue
        if any(o[0] - 0.15 * sp <= cx <= o[2] + 0.15 * sp and o[1] - 0.15 * sp <= cy <= o[3] + 0.15 * sp for o in boxes):
            continue
        out.append((k, [round(x) for x in b]))
    return out


def edge_and_overlap(ctx: Ctx, key, g, gkey) -> str:
    """for a refused box: 'edge' (touches the cell's top/bottom: a neighbour's tip or a cut), 'sliver' (inside a head box we read), else 'alone'."""
    sp = ctx.sp(key)
    cell = ctx.f["cells"].get("cell/%d/%d/%d/%d" % key)
    ln = ctx.lines.get(key[:3])
    if sp is None or cell is None:
        return "unknown"
    b = g["box"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    if b[1] <= cell[1] + sp or b[3] >= cell[3] - sp:
        # cut by the cell's edge: is the mark nearer THIS staff (its own far head, the cell pad cutting it) or another staff of the system (a neighbour's tip)?
        own = max(0.0, (ln[0] - cy) / sp, (cy - ln[4]) / sp) if ln else 99.0
        other = 99.0
        for k2, o in ctx.lines.items():
            if k2[0] == key[0] and k2[1] == key[1] and k2[2] != key[2]:
                osp = (o[4] - o[0]) / 4.0
                other = min(other, max(0.0, (o[0] - cy) / osp, (cy - o[4]) / osp))
        return "edge_own" if own <= other else "edge_other"
    for ck in ((key[0], key[1], key[2], key[3]),):
        for k, o in ctx.cell[ck]:
            if k == gkey or not o["head"] or o["fate"] not in ("written", "written_relocated", "duration_narrowed", "chord_value_undecided"):
                continue
            ob = o["box"]
            if ob[0] - 0.3 * sp <= cx <= ob[2] + 0.3 * sp and ob[1] - 0.3 * sp <= cy <= ob[3] + 0.3 * sp:
                return "sliver"
    if ln and (cy < ln[0] - 3.5 * sp or cy > ln[4] + 3.5 * sp):
        return "far"
    return "alone"


LOST_ROWS = {
    ("duration_narrowed", "beams_ambiguous"): "lost_beam_ambiguous",
    ("duration_narrowed", "beam_discounted_uncertain"): "lost_bare_stem",
    ("duration_narrowed", "beam_certain_not_joined"): "lost_beam_not_joined",
    ("duration_narrowed", "dot_seen_beside_a_plain_note"): "lost_dot_or_staccato",
    ("duration_narrowed", "flag_ink_unread"): "lost_flag_unread",
    ("duration_narrowed", "open_head_flag_contradiction"): "lost_head_flag_contradiction",
    ("duration_narrowed", "whole_class_filled_on_a_stem"): "lost_head_flag_contradiction",
    ("rest_duration_narrowed", "rest_slot_contradicts_class"): "lost_rest_value",
}


def first_cause(ctx: Ctx, b: dict) -> tuple:
    """-> (row key, record reason words, detail)."""
    key = (b["page"], b["system"], b["staff"], b["cell"])
    cells = {key: [dict(g, key=k) for k, g in ctx.cell[key]]}
    # a refusal that is RIGHT and says nothing about this bar's own marks -- a neighbour staff's mark cut by the cell edge, or a sliver of a head we
    # read -- is not the first cause of anything: it only makes the exporter mark a gap. Set aside, then the next cause decides (2.311, Sean's tiles 1-2).
    neutral = set()
    for gd in cells[key]:
        fa = gd["fate"] or ""
        if (gd["head"] or gd["rest"]) and fa.startswith(("not_a_notehead:", "not_a_rest:")) and fa not in _NOT_A_GAP_REASONS:
            if edge_and_overlap(ctx, key, gd, gd["key"]) in ("edge_other", "sliver"):
                neutral.add(gd["key"])
    cells[key] = [gd for gd in cells[key] if gd["key"] not in neutral]
    cause, why = cause_of(b, cells)
    rows = _rows(ctx, b)
    det = {"neutral_refusals": len(neutral)} if neutral else {}
    if cause == "5 sum" and neutral and b["kind"] != "does_not_add_up":
        return "red_only_for_a_refused_tip", "%s; only refusals: a neighbour's mark cut by the cell edge / a sliver of a head read (%d)" % (b["kind"], len(neutral)), det
    if cause == "1 staff":
        return "staff_lost", why, det
    if cause == "2 lost":
        w0 = why
        gl = [(k, g) for k, g in ctx.cell[key] if (g["head"] or g["rest"]) and g["fate"] == w0 and k not in neutral]
        k, g = gl[0]
        v = g.get("v") or {}
        if w0 in ("duration_narrowed", "rest_duration_narrowed", "duration_abstained", "rest_duration_abstained"):
            r = (v.get("duration") or {}).get("reason")
            hollow = "Half" in (g.get("head_class") or "") or "Whole" in (g.get("head_class") or "")
            det["head_class"] = g.get("head_class")
            if hollow and r in ("beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined", "flag_ink_unread"):
                return "lost_hollow_head_held", "%s: %s (head %s)" % (w0, r, g.get("head_class")), det
            return LOST_ROWS.get((w0, r), "lost_value_other"), "%s: %s" % (w0, r), det
        if w0 == "chord_value_undecided":
            r = (v.get("duration") or {}).get("reason")
            return "lost_chord_value", "%s: %s" % (w0, r), det
        if w0 == "no_pitch":
            return "lost_no_pitch", w0, det
        if w0.startswith("not_a_notehead:"):
            e = edge_and_overlap(ctx, key, g, k)
            det["refused_box"] = e
            return "lost_refused_head_" + e, w0, det
        if w0.startswith("not_a_rest:"):
            e = edge_and_overlap(ctx, key, g, k)
            det["refused_box"] = e
            return "lost_refused_rest_" + (e if e.startswith("edge") else "inside"), w0, det
        if w0 == "unread:wide_box_unread":
            return "lost_wide_box", w0, det
        return "lost_other", w0, det
    if cause == "3 nothing":
        # is there ink the detector never boxed? rest-candidate verdicts first, then any non-line ink piece of mark size in the staff band
        ln = ctx.lines.get(key[:3])
        sp = ctx.sp(key)
        cands = []
        for k, g in ctx.cell[key]:
            if g["cls"] is None and g.get("v"):
                u = g["v"].get("unboxed_ink_is_a_rest") or {}
                if u.get("outcome") == "abstained":
                    cands.append(u.get("reason"))
        if cands:
            det["unboxed"] = cands
            return "nothing_unboxed_rest_ink", "no head or rest box; rest-sized ink abstained: %s" % cands[0], det
        ink = len(unboxed_marks(ctx, key))
        det["ink_pieces_in_staff_band"] = ink
        if ink:
            return "nothing_other_ink", "no head or rest box in the bar; %d unboxed head- or rest-sized ink pieces on the staff" % ink, det
        return "nothing_blank", "no head or rest box and no head- or rest-sized ink on the staff", det
    if cause == "4 all-twin":
        return "twin_" + {"owned_by_another_staff": "owned_elsewhere"}.get(why, "claimed_or_twin"), why, det
    # 5 sum
    want, got = b.get("want_quarters"), b.get("counted_quarters") or []
    if b["kind"] == "does_not_add_up" and want is not None and got:
        side = "short" if max(got) < want else ("long" if min(got) > want else "two voices disagree")
        mech, d2 = sum_mechanism(ctx, b, rows, "two voices" if side.startswith("two") else side)
        d2["side"] = side
        return mech if mech != "sum_unexplained" else "sum_unexplained_" + side.split()[0], "does not add up, %s (want %s, counted %s)" % (
            side, want, "/".join("%g" % x for x in got)), d2
    return "sum_other_kind", "%s with every read mark written" % b["kind"], det


def classify(ctx: Ctx) -> list:
    out = []
    for b in red_bars(ctx.f, ctx.pages):
        row, why, det = first_cause(ctx, b)
        rows = _rows(ctx, b)
        plain = sum(1 for w in rows if not w.get("blue") and w["type"] != "?")
        blue = sum(1 for w in rows if w.get("blue") and w["type"] != "?")
        out.append(dict(plate=ctx.plate, page=b["page"], system=b["system"], staff=b["staff"], cell=b["cell"], measure=b["measure"], part=b["part"],
                        kind=b["kind"], also=b.get("also", []), row=row, reason=why, detail=det, n_written_plain=plain, n_written_blue=blue,
                        want=b.get("want_quarters"), counted=b.get("counted_quarters"), two_voice=b.get("two_voice")))
    return out


def presence(ctx: Ctx, key: tuple, rows: list) -> set:
    """which mechanism tests find their evidence in this bar, ORDER IGNORED -- used to put a base rate (every bar that is NOT red) beside each test."""
    sp = ctx.sp(key)
    out = set()
    if sp is None:
        return out
    notes = [w for w in rows if w["kind"] == "note"]
    if any(_nearer_other_staff(ctx, key, w, sp) for w in notes):
        out.add("foreign_note")
    for a, c in itertools.combinations(notes, 2):
        ix = min(a["box"][2], c["box"][2]) - max(a["box"][0], c["box"][0])
        iy = min(a["box"][3], c["box"][3]) - max(a["box"][1], c["box"][1])
        if ix > 0 and iy > 0 and ix * iy > 0.5 * min((a["box"][2] - a["box"][0]) * (a["box"][3] - a["box"][1]),
                                                        (c["box"][2] - c["box"][0]) * (c["box"][3] - c["box"][1])) and a.get("onset") != c.get("onset"):
            out.add("duplicate_head")
            break
    if any(g["cls"] in ("tuplet3", "tupletBracket") for k, g in ctx.cell[key]):
        out.add("tuplet_mark")
    voices = {w.get("voice") for w in notes}
    if any(w["kind"] == "rest" and w["type"] == "whole" and w.get("voice") in voices for w in rows):
        out.add("whole_rest_beside_notes")
    if any(not w.get("blue") and (w["box"][3] - w["box"][1]) < 0.75 * sp for w in notes):
        out.add("small_head")
    if unboxed_marks(ctx, key):
        out.add("unboxed_mark_ink")
    if any(g["cls"] is None and REST_CAND <= int(k.split("/")[-1]) < INK_MIN and g.get("v") and g["fate"] is None
           and ((g["v"].get("unboxed_ink_is_a_rest") or {}).get("outcome") == "abstained") for k, g in ctx.cell[key]):
        out.add("unboxed_rest_ink")
    ln = ctx.lines.get(key[:3])
    if ln and any(g["head"] and g["fate"] == "owned_by_another_staff" and ln[0] - 1.5 * sp <= (g["box"][1] + g["box"][3]) / 2.0 <= ln[4] + 1.5 * sp
                  for k, g in ctx.cell[key]):
        out.add("head_given_away")
    for w in notes:
        if not w.get("blue") and not (w.get("sub") or {}).get("dot") and _dur(w) is not None and _near_dot_evidence(ctx, key, w, sp):
            out.add("dot_evidence_beside_a_plain_note")
            break
    return out


def base_rates(ctx: Ctx, red_keys: set) -> dict:
    """every cell of the plate's count pages, red vs not red: how many carry each mechanism's evidence (the control: a test that fires as
    often on bars that add up as on red ones explains nothing)."""
    cnt = collections.defaultdict(collections.Counter)
    for ck in ctx.cell:
        if ck[0] not in ctx.pages or not ctx.f["cells"].get("cell/%d/%d/%d/%d" % ck):
            continue
        pre = "glyph/%d/%d/%d/%d/" % ck
        rows = [w for rg in [k for k in ctx.written if k.startswith(pre)] for w in ctx.written[rg]]
        grp = "red" if ck in red_keys else "not red"
        cnt[grp]["bars"] += 1
        for fl in presence(ctx, ck, rows):
            cnt[grp][fl] += 1
    return {g: dict(c) for g, c in cnt.items()}
