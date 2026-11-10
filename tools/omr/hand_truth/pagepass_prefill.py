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
                    "n_pieces": len(idx)})
    return out


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


def hand_prefills(truth: store.PageTruth, sp: float, *, arcs_from_labels: bool = True) -> List[Dict]:
    """Sean's per-cell labels of the page-wide kinds, re-read at the page's grain."""
    kinds: Dict[str, List[Dict]] = {}
    for b in truth.boxes:
        k = pp.kind_of_class(b.cls)
        if k is None or k == "staff":
            continue
        it = {"kind": k, "rect": tuple(b.rect), "source": "hand-cell-labels", "id": b.id,
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


def build(truth: store.PageTruth, *, arc_key: Optional[Dict] = None) -> pp.PagePass:
    """A fresh page pass: pre-fills only (pending), nothing confirmed."""
    sp = measure_sp(staff_lines_from_cells(truth.cells)) or 32.0
    page = pp.PagePass(edition=truth.edition, pdf_page_index=truth.pdf_page_index, dpi=truth.dpi,
                       width=truth.width, height=truth.height, sp=sp,
                       provenance={"built_from": f"{truth.edition}/{truth.pdf_page_index}.json (never edited)",
                                   "arc_key": "2.281 corrected key" if arc_key else None})
    items = staff_prefills(truth) + hand_prefills(truth, sp, arcs_from_labels=arc_key is None)
    if arc_key is not None:
        items += key_prefills(arc_key)
    for it in items:
        shape = pp.rect_shape(it["rect"])
        page.add_prefill(it["kind"], shape, it["source"], text=it.get("text"), sub=it.get("sub"),
                         note=it.get("note", ""))
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
