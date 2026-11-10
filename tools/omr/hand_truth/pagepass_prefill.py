"""Pre-fills for the page pass (ROADMAP 2.287): proposals Sean confirms, rejects or fixes -- never truth.

Three sources, all page-wide kinds only (a head, stem, dot or accidental is the cell pass's):

  staff    one proposal per staff: the five lines the cells measured, across the staff's cells
  hand     Sean's own per-cell labels (``<page>.json`` boxes) of the page-wide kinds, re-read at the
           page's grain: key / meter pieces of one mark joined into one box; twin boxes (the same
           mark boxed from two cells) dropped to one; tie / slur halves cut at a barline JOINED
  arc key  where the 2.281 corrected arc key (``benchmarks/omr-arc-binding-2026-10/
           key-brahms-p0-corrected.json``, e1e0bf726) is given, ITS arcs stand in for the raw tie / slur
           boxes -- the arcs the key says are one arc across a barline. Its own assumptions
           (``assumed_for_sean``) ride along in each pre-fill's ``note``

Every proposal is ``pending`` and drawn visibly different from a confirmed label (assisted-label bias:
a mark Sean only ticks is weaker evidence than a mark he drew).

    python3 -m tools.omr.hand_truth.pagepass_prefill new data/hand-truth/pages/imslp317803/0.json \
        --arc-key benchmarks/omr-arc-binding-2026-10/key-brahms-p0-corrected.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from tools.omr.hand_truth import pagepass as pp
from tools.omr.hand_truth import store
from tools.omr.hand_truth.pageink import measure_sp, staff_lines_from_cells

Rect = Tuple[float, float, float, float]
#: a tie / slur half within this many spaces of a barline x is cut AT it
JOIN_EDGE_SP = 1.5
#: two halves must overlap this fraction of the shorter one's height to be one arc
JOIN_Y_OVERLAP = 0.5
#: key-signature pieces within this many spaces horizontally are one key signature; meter digits stack
KEY_JOIN_SP = 1.2
METER_JOIN_SP = 0.6


def _iou(a: Rect, b: Rect) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def _union(rs: Sequence[Rect]) -> Rect:
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))


def dedupe(items: List[Dict], iou: float = 0.6) -> List[Dict]:
    """Twins: the same kind boxed twice over one mark (two cells' pads) -> one."""
    out: List[Dict] = []
    for it in items:
        if any(o["kind"] == it["kind"] and _iou(o["rect"], it["rect"]) >= iou for o in out):
            continue
        out.append(it)
    return out


def join_pieces(items: List[Dict], gx: float, gy: float) -> List[Dict]:
    """Union boxes of one kind whose rectangles, grown by (gx, gy), touch (key accidentals, meter digits)."""
    n = len(items)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            a, b = items[i]["rect"], items[j]["rect"]
            if a[0] - gx <= b[2] and b[0] - gx <= a[2] and a[1] - gy <= b[3] and b[1] - gy <= a[3]:
                parent[find(i)] = find(j)
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    out = []
    for idx in groups.values():
        out.append({**items[idx[0]], "rect": _union([items[i]["rect"] for i in idx]),
                    "n_pieces": len(idx),
                    "pieces": [{"rect": tuple(items[i]["rect"]), "cls": items[i].get("cls")} for i in idx]})
    return out


#: a vertical join: boxes whose centres are within this many spaces in x are one printed vertical (a barline
#: through several cells; a brace / bracket); their gap is joined when the print is unbroken across it
BARLINE_X_SP = 0.6
BRACKET_X_SP = 0.6
#: with no ink to look at (tests, a page not rendered yet): join boxes whose vertical gap is under this many spaces
JOIN_GAP_SP = 0.5
#: the share of the gap's rows that must carry ink in the verticals' own columns for the print to be unbroken
UNBROKEN_FRAC = 0.9


def _gap_unbroken(ink: Optional[np.ndarray], x0: float, x1: float, y0: float, y1: float) -> bool:
    """True if every (almost every) row of the gap y0..y1 has ink inside the central columns x0..x1."""
    if y1 <= y0:
        return True
    if ink is None:
        return False
    h, w = ink.shape
    a, b = max(0, int(round(y0))), min(h, int(round(y1)))
    c, d = max(0, int(round(x0))), min(w, int(round(x1)) + 1)
    if b <= a or d <= c:
        return False
    return float(ink[a:b, c:d].any(axis=1).mean()) >= UNBROKEN_FRAC


def join_vertical(items: List[Dict], sp: float, *, x_sp: float, ink: Optional[np.ndarray] = None) -> List[Dict]:
    """Per-cell pieces of one printed vertical (a barline, a brace / bracket) -> ONE full-height box.

    Sean 2026-11-10: "I did the full length of the bar lines that goes through all of the systems, which I
    think is the way that it should be." A cell cuts a barline at every staff; the print does not. Boxes whose
    centres lie within ``x_sp`` spaces of one another's column are one candidate; consecutive boxes (top to
    bottom) join when the gap between them is unbroken ink in the column (``ink`` = the page's ink), or, with no ink to
    look at, no more than ``JOIN_GAP_SP``. Where the print breaks (between instrument groups, between systems) the
    proposal breaks too. Never regenerated over labels Sean has already acted on (build only makes a new file)."""
    tol = x_sp * sp
    cols: List[List[Dict]] = []
    for it in sorted(items, key=lambda i: (i["rect"][0] + i["rect"][2]) / 2):
        cx = (it["rect"][0] + it["rect"][2]) / 2
        for col in cols:
            # one class per column: a brace and the bracket it sits inside are two marks, however close
            if col[0].get("cls") == it.get("cls") and abs(
                    cx - sum((c["rect"][0] + c["rect"][2]) / 2 for c in col) / len(col)) <= tol:
                col.append(it)
                break
        else:
            cols.append([it])
    out: List[Dict] = []
    for col in cols:
        col.sort(key=lambda i: i["rect"][1])
        cur = [col[0]]
        runs = []
        for it in col[1:]:
            gap0, gap1 = max(c["rect"][3] for c in cur), it["rect"][1]
            xs = [(c["rect"][0] + c["rect"][2]) / 2 for c in cur + [it]]
            core0, core1 = min(xs) - 0.1 * sp, max(xs) + 0.1 * sp
            if gap1 - gap0 <= JOIN_GAP_SP * sp or _gap_unbroken(ink, core0, core1, gap0, gap1):
                cur.append(it)
            else:
                runs.append(cur)
                cur = [it]
        runs.append(cur)
        for run in runs:
            out.append({**run[0], "rect": _union([c["rect"] for c in run]), "n_pieces": len(run),
                        "joined_from": [c.get("id") for c in run],
                        "note": (f"{len(run)} per-cell pieces joined into one full-height {run[0]['kind']}"
                                 if len(run) > 1 else run[0].get("note", ""))})
    return out


def _meter_piece(cls: Optional[str]) -> Optional[str]:
    """The value one hand-labelled meter piece stands for (``timeSig6`` -> ``6``; common time -> ``C``)."""
    if not cls or not cls.lower().startswith("timesig"):
        return None
    t = cls[len("timeSig"):]
    if t.isdigit():
        return t
    return {"common": "C", "cutcommon": "C|"}.get(t.lower())


def meter_from_pieces(pieces: List[Dict]) -> Tuple[Optional[str], List[Dict], str]:
    """(value, parts, note) for the digit boxes of ONE meter: top digit over bottom digit -> ``'6/8'``.

    The value is pre-typed for Sean to confirm and only when it is fully known (two stacked rows of digits, or one
    common / cut-time sign); one digit alone is NOT guessed into a meter. ``parts`` keeps each digit's own box."""
    ps = sorted(({"rect": [float(v) for v in p["rect"]], "text": _meter_piece(p.get("cls")), "from": "hand"}
                 for p in pieces), key=lambda p: ((p["rect"][1] + p["rect"][3]) / 2, p["rect"][0]))
    parts = [{**p} for p in ps]
    if not ps or any(p["text"] is None for p in ps):
        return None, parts, ""
    rows: List[List[Dict]] = []
    for p in ps:
        h = p["rect"][3] - p["rect"][1]
        if rows and (p["rect"][1] + p["rect"][3]) / 2 - sum(
                (q["rect"][1] + q["rect"][3]) / 2 for q in rows[-1]) / len(rows[-1]) < 0.5 * h:
            rows[-1].append(p)
        else:
            rows.append([p])
    texts = ["".join(q["text"] for q in sorted(r, key=lambda q: q["rect"][0])) for r in rows]
    if len(texts) == 2 and all(t.isdigit() for t in texts):
        return "/".join(texts), parts, "value read from the hand-labelled digits; confirm it"
    if len(texts) == 1 and texts[0] in ("C", "C|"):
        return texts[0], parts, "value read from the hand-labelled sign; confirm it"
    return None, parts, f"hand-labelled digits found: {' over '.join(texts)} (not a whole meter)"


def join_arc_pieces(arcs: List[Dict], barline_xs: Sequence[float], sp: float) -> List[Dict]:
    """Tie / slur halves that a barline cut are ONE arc.

    Two boxes are halves of one arc when the left one's right end and the right one's left end sit
    within ``JOIN_EDGE_SP`` of the SAME barline x and their y bands overlap by ``JOIN_Y_OVERLAP`` of the
    shorter. One-to-one per barline (the closest y centre wins), repeated so a chain over two barlines
    joins. Staff labels are ignored (a box near a cell edge often carries its neighbour's staff).
    A joined arc whose halves disagree on kind keeps the left half's and says so in ``note``.
    """
    tol = JOIN_EDGE_SP * sp
    arcs = [dict(a) for a in arcs]
    changed = True
    while changed:
        changed = False
        for bx in barline_xs:
            lefts = [a for a in arcs if abs(a["rect"][2] - bx) <= tol]
            rights = [a for a in arcs if abs(a["rect"][0] - bx) <= tol]
            used = set()
            pairs = []
            for L in lefts:
                best, bd = None, None
                for R in rights:
                    if R is L or id(R) in used or R["rect"][0] < L["rect"][0]:
                        continue
                    ov = min(L["rect"][3], R["rect"][3]) - max(L["rect"][1], R["rect"][1])
                    short = min(L["rect"][3] - L["rect"][1], R["rect"][3] - R["rect"][1])
                    if short <= 0 or ov < JOIN_Y_OVERLAP * short:
                        continue
                    d = abs((L["rect"][1] + L["rect"][3]) - (R["rect"][1] + R["rect"][3]))
                    if bd is None or d < bd:
                        best, bd = R, d
                if best is not None:
                    used.add(id(best))
                    pairs.append((L, best))
            for L, R in pairs:
                note = L.get("note", "")
                if L.get("sub") and R.get("sub") and L["sub"] != R["sub"]:
                    note = (note + f" halves disagree on kind ({L['sub']} / {R['sub']}); left half's kept.").strip()
                joined = {**L, "rect": _union([L["rect"], R["rect"]]), "note": note,
                          "joined_from": L.get("joined_from", [L.get("id")]) + R.get("joined_from", [R.get("id")])}
                arcs.remove(L)
                arcs.remove(R)
                arcs.append(joined)
                changed = True
    return arcs


def staff_prefills(truth: store.PageTruth) -> List[Dict]:
    """One proposal per (system, staff): its lines across all its measure cells."""
    out = []
    by: Dict[Tuple[int, int], List] = {}
    for c in truth.cells:
        if c.kind == "measure" and c.staff_line_ys and c.system is not None and c.staff is not None:
            by.setdefault((c.system, c.staff), []).append(c)
    sp = measure_sp(staff_lines_from_cells(truth.cells))
    pad = 0.15 * (sp or 32.0)
    for (s, st), cells in sorted(by.items()):
        lines = staff_lines_from_cells(cells)
        out.append({"kind": "staff", "source": "staff-lines", "sub": None, "text": None,
                    "note": f"system {s} staff {st}: the five lines the cells measured",
                    "rect": (min(l[0] for l in lines), min(min(l[2]) for l in lines) - pad,
                             max(l[1] for l in lines), max(max(l[2]) for l in lines) + pad)})
    return out


def _dynamic_text(cls: str) -> str:
    return cls[len("dynamic"):].lower() if cls.lower().startswith("dynamic") else cls


def hand_prefills(truth: store.PageTruth, sp: float, *, arcs_from_labels: bool = True,
                  ink: Optional[np.ndarray] = None) -> List[Dict]:
    """Sean's per-cell labels of the page-wide kinds, re-read at the page's grain (a barline or a bracket is
    one full-height box, a meter is one box with its value pre-typed)."""
    kinds: Dict[str, List[Dict]] = {}
    for b in truth.boxes:
        k = pp.kind_of_class(b.cls)
        if k is None or k == "staff":
            continue
        it = {"kind": k, "rect": tuple(b.rect), "source": "hand-cell-labels", "id": b.id, "cls": b.cls,
              "sub": b.cls if b.cls in ("tie", "slur") else None,
              "text": (b.text if b.cls == "text" else _dynamic_text(b.cls) if k == "dynamic" else None),
              "note": ""}
        kinds.setdefault(k, []).append(it)
    out: List[Dict] = []
    for k, items in kinds.items():
        items = dedupe(items)
        if k == "key":
            items = join_pieces(items, KEY_JOIN_SP * sp, 1.0 * sp)
        elif k == "meter":
            items = join_pieces(items, METER_JOIN_SP * sp, METER_JOIN_SP * sp)
            for it in items:
                it["text"], it["parts"], why = meter_from_pieces(it.get("pieces", []))
                it["note"] = why or it.get("note", "")
        elif k == "barline":
            items = join_vertical(items, sp, x_sp=BARLINE_X_SP, ink=ink)
        elif k == "bracket":
            items = join_vertical(items, sp, x_sp=BRACKET_X_SP, ink=ink)
        elif k == "arc":
            if not arcs_from_labels:
                continue
            bx = [(b.rect[0] + b.rect[2]) / 2 for b in truth.boxes if b.cls.lower().startswith("barline")]
            items = join_arc_pieces(items, sorted(set(round(x) for x in bx)), sp)
        out.extend(items)
    return out


def key_prefills(key: Dict) -> List[Dict]:
    """The 2.281 corrected arc key's arcs (page px) as proposals, with its assumptions in the note."""
    changes: Dict[str, List[str]] = {}
    for ch in key.get("changes", []):
        if ch.get("assumed_for_sean"):
            for i in ch.get("ids", []):
                changes.setdefault(i, []).append(f"{ch.get('change')}: {ch.get('reason', '')}")
    out = []
    for a in key["arcs"]:
        notes = [n for i in a.get("ids", []) for n in changes.get(i, [])]
        flags = []
        if a.get("extended"):
            flags.append(f"end(s) {','.join(a['extended'])} extended past the hand box")
        if a.get("cross_system"):
            flags.append("leaves the system (cross-system tie)")
        if a.get("kind_conflict"):
            flags.append("halves disagree on tie / slur")
        out.append({"kind": "arc", "source": "arc-key-2.281", "sub": a.get("kind"), "text": None,
                    "rect": (float(a["x0"]), float(a["y0"]), float(a["x1"]), float(a["y1"])),
                    "note": "; ".join(flags + notes)[:400], "id": a.get("id")})
    return out


def build(truth: store.PageTruth, *, arc_key: Optional[Dict] = None, ink: Optional[np.ndarray] = None) -> pp.PagePass:
    """A fresh page pass: pre-fills only (pending), nothing confirmed. ``ink`` (the page's dark pixels) lets a
    barline / bracket pre-fill join across the gaps between cells only where the print is unbroken."""
    sp = measure_sp(staff_lines_from_cells(truth.cells)) or 32.0
    page = pp.PagePass(edition=truth.edition, pdf_page_index=truth.pdf_page_index, dpi=truth.dpi,
                       width=truth.width, height=truth.height, sp=sp,
                       provenance={"built_from": f"{truth.edition}/{truth.pdf_page_index}.json (never edited)",
                                   "arc_key": "2.281 corrected key" if arc_key else None})
    items = staff_prefills(truth) + hand_prefills(truth, sp, arcs_from_labels=arc_key is None, ink=ink)
    if arc_key is not None:
        items += key_prefills(arc_key)
    for it in items:
        shape = pp.rect_shape(it["rect"])
        page.add_prefill(it["kind"], shape, it["source"], text=it.get("text"), sub=it.get("sub"),
                         note=it.get("note", ""), parts=it.get("parts"))
    return page


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["new"])
    ap.add_argument("page", help="the page file, data/hand-truth/pages/<edition>/<n>.json (read only)")
    ap.add_argument("--arc-key", help="the 2.281 corrected arc key json")
    ap.add_argument("--out", help="default: <page>.pagepass.json beside it")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    truth = store.load(Path(a.page))
    out = Path(a.out) if a.out else pp.pagepass_path(truth.edition, truth.pdf_page_index, Path(a.page).parents[1])
    if out.exists() and not a.force:
        raise SystemExit(f"{out} exists -- Sean's page-pass labels are never overwritten (--force to start over)")
    key = json.loads(Path(a.arc_key).read_text()) if a.arc_key else None
    page = build(truth, arc_key=key)
    page.save(out)
    kinds: Dict[str, int] = {}
    for lab in page.labels:
        kinds[lab.kind] = kinds.get(lab.kind, 0) + 1
    print(json.dumps({"pagepass": str(out), "prefills": len(page.labels), "by_kind": kinds, "sp": page.sp}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
