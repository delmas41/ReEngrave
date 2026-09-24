"""ROADMAP 3.4, lane B — the STAGE REVIEW viewer.

One staff on one system, every stage in turn: **what did this stage READ, and
what did it DECIDE**. Sean's corrections leave as a review-actions SIDECAR
which lane (A) ingests into the record as human WITNESSES and re-decides with.

    python3 -m tools.omr.staged.review.server \\
        --record library/_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json \\
        --pdf    library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \\
        --staff  staff/3/0/9

Then open `http://127.0.0.1:5060/?staff=staff/3/0/9`.

⚠️⚠️ **NOTHING HERE RE-DECIDES ANYTHING, AND THREE RULES ENFORCE IT.**

1. **The refusal buckets are INSTRUMENTED, never restated.** `_place_notes`
   holds the ladder; this module wraps `_parse_subject`/`_place_notes` at run
   time exactly as `benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py`
   does, and files each `_drop` under its glyph. The repo has paid for the
   other choice once: `omr-cleanup-count-2026-09/build_sheet.py` kept its own
   copy of "the three refusals" and reported 542 where the exporter refused
   738. The same control that probe runs runs here at start-up: the
   per-subject log must reproduce `report["notes_not_written"]` exactly, and
   `--break-control` makes it fail on purpose so it is seen failing first.
2. **The per-stage story is `trace.py`'s**, not a second walk of the record.
   `trace.trace` is called for every subject panel and its `_verdict_step` is
   what renders a verdict; this module resolves the row ids it returns and
   adds nothing to the reasoning.
3. **The crop is a print crop**: cut from the PDF at the RECORD's own dpi,
   behind `crop_inferred._frame_ok` — IMPORTED, not copied. A render that
   fails the frame control is served with the failure on the page and the
   GATHER actions are REFUSED (a box drawn on the wrong raster is not
   evidence, and a caveat under a picture is not a control).

⚠️ An abstention is shown as an abstention with its reason word; a stage with
no row on a subject says *did not run* (`State.ABSENT`) and is kept apart from
*a reader looked and could not say* (`State.DECLINED`) — CLAUDE.md §4b, and
the reason the record exists.

⚠️ THE SIDECAR IS THE WHOLE OUTPUT. The re-run button shells out to lane
(A)'s `tools.omr.staged.review.rerun`; where that module is absent the button
says so and the sidecar is still saved. It never fakes a re-run.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               Response)
from fastapi.staticfiles import StaticFiles

from .. import export as EXPORT
from .. import trace as TRACE
from ..record import Q, State
from ..record_io import load_record

#: ⚠️ THE EXPORTER'S OWN HANDLE ON THE PURE RENDERERS, not a second import of
#: the frozen legacy module. `export.py` spells a pitch through
#: `_legacy._parse_pitch`, and reading it through the exporter's own
#: reference is what keeps the two spellings from drifting apart. No legacy
#: FLAG is read here and none may be (CLAUDE.md §3).
_legacy = EXPORT._legacy

_HERE = Path(__file__).resolve().parent
_STATIC_DIR = _HERE / "static"
_ROOT = _HERE.parents[3]          # the worktree root

#: ⚠️⚠️ `DERIVED_CHECK = True` — THE FIFTH APPLICATION OF `wiring.py`'s OWN
#: RULE, and it is not a convenience. That module's DETAIL question matches a
#: key by BARE NAME anywhere under `tools/`, and it already excludes a gap
#: list, a test, a benchmark probe and an auditor for one reason: **naming a
#: key is not consuming it.** A VIEWER is the same family one step further —
#: it SHOWS a detail key to a human and no stage reads its output, so a
#: quantity nothing consumes must go on reporting as unconsumed while this
#: page displays it.
#:
#: Measured rather than assumed: without this marker, `wiring --check` on the
#: tree that first carried this file reported `Q.DIRECTION_WORD.gate` as
#: STALE — closed — because one COMMENT in this module named it, and
#: `staged.check` went from 70 problems to 69. A gap this page cannot close
#: is the whole point; the marker must be a bare module-level assignment of
#: the literal `True` or `wiring._declares_derived_check` will not see it.
DERIVED_CHECK = True



# ═════════════════════════════════════════════════════════════════════════
# 1. THE CONTRACT — the review-actions sidecar
# ═════════════════════════════════════════════════════════════════════════

#: The stage a feedback action is ABOUT. GATHER actions carry boxes; the
#: later stages carry an agree/disagree against a verdict id.
STAGES: Tuple[str, ...] = ("gather", "adjudicate", "evaluate", "infer",
                           "export")

#: ⚠️ FIXED BY THE CONTRACT WITH LANE (A). Optional fields may be ADDED (and
#: are documented in `OPTIONAL_FIELDS`); a kind may not be renamed and a
#: required field may not be dropped.
KIND_REQUIRES: Dict[str, Tuple[str, ...]] = {
    "add_box":     ("bbox_page_px", "category"),
    "delete_box":  ("glyph",),
    "redraw_box":  ("glyph", "bbox_page_px"),
    "agree":       ("verdict",),
    "disagree":    ("verdict",),
}

#: Optional fields this lane writes BEYOND the contract, each documented.
#: A reader of the sidecar may ignore every one of them and lose nothing the
#: contract promised.
OPTIONAL_FIELDS: Dict[str, str] = {
    "note": "the reviewer's own words; empty string where he typed none",
    "quantity": "the verdict's quantity, copied so a reader need not index "
                "the record to know what the disagreement is about",
    "outcome": "the verdict's outcome at the time of the action",
    "value": "the verdict's value at the time of the action",
    "prior_bbox_page_px": "on redraw_box, the machine box that was redrawn, "
                          "so the move can be measured without the record",
    "cell": "the cell subject the box was drawn in, where the drawn "
            "rectangle falls inside exactly one `Q.CELL_BOX`; absent "
            "otherwise -- never guessed",
    "crop_px": "the rectangle as it was drawn, in the crop's own pixels, "
               "beside the page-pixel conversion, so the conversion can be "
               "re-checked from the file alone",
}

_GATHER_KINDS = frozenset({"add_box", "delete_box", "redraw_box"})
_VERDICT_KINDS = frozenset({"agree", "disagree"})


class ContractError(ValueError):
    """The action does not satisfy the sidecar contract. Never caught here —
    a sidecar that does not validate is not written."""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def validate_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """The action, or raise. ⚠️ VALIDATES THE SHAPE, never the opinion."""
    if not isinstance(action, dict):
        raise ContractError("an action must be an object")
    for fld in ("id", "t", "stage", "kind"):
        if not action.get(fld):
            raise ContractError(f"action is missing {fld!r}")
    stage = action["stage"]
    if stage not in STAGES:
        raise ContractError(f"stage {stage!r} is not one of {STAGES}")
    kind = action["kind"]
    if kind not in KIND_REQUIRES:
        raise ContractError(f"kind {kind!r} is not one of "
                            f"{tuple(KIND_REQUIRES)}")
    if kind in _GATHER_KINDS and stage != "gather":
        raise ContractError(f"{kind!r} is a GATHER action; it cannot carry "
                            f"stage {stage!r}")
    if kind in _VERDICT_KINDS and stage == "gather":
        raise ContractError("agree/disagree is about a VERDICT, and GATHER "
                            "writes no verdicts — file the box action instead")
    for fld in KIND_REQUIRES[kind]:
        if action.get(fld) in (None, ""):
            raise ContractError(f"{kind!r} needs {fld!r}")
    box = action.get("bbox_page_px")
    if box is not None:
        if (not isinstance(box, (list, tuple)) or len(box) != 4
                or not all(isinstance(v, (int, float)) for v in box)):
            raise ContractError("bbox_page_px must be [x0, y0, x1, y1] in "
                                "PAGE pixels at the record's own dpi")
        if box[2] <= box[0] or box[3] <= box[1]:
            # ⚠️ A zero-area or inverted rectangle is a mis-drag, not a box.
            # Writing one would hand lane (A) a witness with no ink under it.
            raise ContractError("bbox_page_px must be CORNERS with "
                                "x1 > x0 and y1 > y0")
    return action


class Sidecar:
    """The review-actions file. Append-only, autosaved, one staff.

    ⚠️ ONE STAFF PER FILE, because the contract carries one `staff` key. A
    second staff gets its own file rather than a second meaning for that key.
    """

    def __init__(self, path: Path, record: str, staff: str) -> None:
        self.path = Path(path)
        self.lock = threading.Lock()
        if self.path.exists():
            doc = json.loads(self.path.read_text())
            if doc.get("staff") and doc["staff"] != staff:
                raise ContractError(
                    f"{self.path} is a review of {doc['staff']}, not of "
                    f"{staff}. One staff per sidecar — point --sidecar at a "
                    f"different file.")
            self.doc = doc
            self.doc.setdefault("record", record)
            self.doc.setdefault("staff", staff)
            self.doc.setdefault("actions", [])
            for a in self.doc["actions"]:
                validate_action(a)
        else:
            self.doc = {"record": record, "staff": staff, "actions": []}
            self._write()

    # ── writing ──────────────────────────────────────────────────────────
    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.doc, indent=1))
        tmp.replace(self.path)

    def next_id(self) -> str:
        n = 0
        for a in self.doc["actions"]:
            m = re.fullmatch(r"act-(\d+)", str(a.get("id", "")))
            if m:
                n = max(n, int(m.group(1)))
        return f"act-{n + 1:04d}"

    def append(self, action: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            action = dict(action)
            action.setdefault("id", self.next_id())
            action.setdefault("t", _now())
            validate_action(action)
            self.doc["actions"].append(action)
            self._write()
            return action

    def undo(self, action_id: str) -> bool:
        """Remove one action. ⚠️ Not an edit of the record — the record has
        never seen it; this is the reviewer taking back his own note."""
        with self.lock:
            before = len(self.doc["actions"])
            self.doc["actions"] = [a for a in self.doc["actions"]
                                   if a.get("id") != action_id]
            changed = len(self.doc["actions"]) != before
            if changed:
                self._write()
            return changed


def default_sidecar_path(root: Path, staff: str) -> Path:
    """`benchmarks/omr-stage-review-2026-09/out/review-actions--staff-3-0-9.json`"""
    return (root / "benchmarks/omr-stage-review-2026-09/out"
            / f"review-actions--{staff.replace('/', '-')}.json")


# ═════════════════════════════════════════════════════════════════════════
# 2. THE CROP FRAME — page pixels ↔ crop pixels, both ways
# ═════════════════════════════════════════════════════════════════════════

# ⚠️ THE FRAME CONTROL IS IMPORTED, NOT COPIED — `crop_funnel.py`'s own move,
# for `funnel.py`'s reason. If the benchmark probe is absent (a cloud
# checkout without `benchmarks/`), `frame_ok` is None and the viewer says the
# control could not be RUN, which is not the same as passing it.
def _load_frame_ok():
    p = (_ROOT / "benchmarks/omr-infer-duration-print-2026-09/probe"
         / "crop_inferred.py")
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location("crop_inferred_for_review", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._frame_ok


@dataclass(frozen=True)
class CropFrame:
    """One staff-system window cut from the page raster.

    ⚠️⚠️ THE ONLY PLACE THE TWO COORDINATE SYSTEMS MEET. `bbox_page_px` in the
    sidecar is PAGE pixels at the record's own dpi; the browser draws in CROP
    pixels. Both directions are here, they are exact inverses, and
    `test_stage_review.py` checks the round trip on a known box in both
    directions — the repo has already paid once for two frames that were
    indistinguishable on a fixture whose boxes started at 0.
    """
    x0: int
    y0: int
    x1: int
    y1: int
    zoom: int
    dpi: int

    @property
    def width(self) -> int:
        return (self.x1 - self.x0) * self.zoom

    @property
    def height(self) -> int:
        return (self.y1 - self.y0) * self.zoom

    def to_crop(self, x: float, y: float) -> Tuple[float, float]:
        return ((x - self.x0) * self.zoom, (y - self.y0) * self.zoom)

    def to_page(self, cx: float, cy: float) -> Tuple[float, float]:
        return (cx / self.zoom + self.x0, cy / self.zoom + self.y0)

    def box_to_crop(self, box: Sequence[float]) -> List[float]:
        a = self.to_crop(box[0], box[1])
        b = self.to_crop(box[2], box[3])
        return [a[0], a[1], b[0], b[1]]

    def box_to_page(self, box: Sequence[float]) -> List[float]:
        a = self.to_page(box[0], box[1])
        b = self.to_page(box[2], box[3])
        return [a[0], a[1], b[0], b[1]]

    def as_json(self) -> Dict[str, Any]:
        return {"page_px": [self.x0, self.y0, self.x1, self.y1],
                "zoom": self.zoom, "dpi": self.dpi,
                "width": self.width, "height": self.height}


# ═════════════════════════════════════════════════════════════════════════
# 3. THE EXPORT PASS — instrumented, with the control that can fail
# ═════════════════════════════════════════════════════════════════════════

class ControlFailed(RuntimeError):
    """The per-subject refusal log does not reproduce the exporter's own
    totals. ⚠️ RAISES rather than serving a page of numbers that do not add
    up — `to_musicxml`'s own `Unbalanced` discipline."""


@dataclass
class ExportPass:
    xml: str
    report: Dict[str, Any]
    #: glyph subject -> the reasons `_place_notes` refused it (in order)
    refusals: Dict[str, List[str]]
    #: glyph subject -> the detection dict that reached a `Cell`
    placed: Dict[str, Dict[str, Any]]
    #: staff key -> the `StaffRun` the exporter built for it
    runs: Dict[str, Any]
    #: staff key -> the `<part>` id it was written into
    part_of_staff: Dict[str, str]
    #: part id -> `<part-name>`
    part_names: Dict[str, str]
    #: (page, system) -> the document bar offset, or None where refused
    offsets: Optional[Dict[Tuple[int, int], int]]


def run_export(data: Dict[str, Any], *, break_control: bool = False
               ) -> ExportPass:
    """`to_musicxml`, with every refusal and every placement filed by GLYPH.

    ⚠️ The buckets are the EXPORTER's. This wraps `_parse_subject` (called
    exactly once per `Q.GLYPH_BOX` row at the top of `_place_notes`' loop, so
    the last subject parsed IS the head being refused) and `_place_notes`, and
    restores both before returning — a module-level patch left in place would
    make every later export in this process report through a viewer.
    """
    refusals: List[Tuple[Optional[str], str]] = []
    placed: Dict[str, Dict[str, Any]] = {}
    runs_seen: Dict[str, Any] = {}
    part_of_staff: Dict[str, str] = {}
    offsets_seen: Dict[str, Any] = {}
    last = {"sub": None}

    class _LoggingCounter(collections.Counter):
        def __setitem__(self, key, value):
            if value > self.get(key, 0):
                refusals.append((last["sub"], key))
            super().__setitem__(key, value)

    class _ProbeBySystem(dict):
        def setdefault(self, key, default=None):
            if key not in self:
                dict.__setitem__(self, key, _LoggingCounter())
            return self[key]

    orig_parse = EXPORT._parse_subject
    orig_place = EXPORT._place_notes
    orig_part = EXPORT._part_xml

    def parse(key):
        s = orig_parse(key)
        last["sub"] = key
        return s

    def place(rec, runs, by_system=None, **kwargs):
        probe = _ProbeBySystem()
        dropped = orig_place(rec, runs, by_system=probe, **kwargs)
        runs_seen.update(runs)
        for run in runs.values():
            for cell in run.cells.values():
                for det in cell.detections:
                    g = det.get("glyph")
                    if g:
                        placed[g] = det
        if by_system is not None:
            by_system.update(probe)
        return dropped

    def part_xml(rec, part, pid, divisions, counters, offsets=None,
                 *args, **kwargs):
        # Pass-through on purpose: `_part_xml` grew `drops`, `held_bars` and
        # `marks` under ROADMAP 2.8 after this wrapper was written, and a
        # wrapper that restates the signature breaks on every such growth
        # while reading nothing from the new arguments. It observes the
        # (staff -> part) join and the offsets, and hands everything else on.
        for run in part:
            part_of_staff.setdefault(run.key, pid)
            if getattr(run, "condensed_from", None):
                part_of_staff.setdefault(run.condensed_from, pid)
        if offsets is not None:
            offsets_seen["v"] = offsets
        return orig_part(rec, part, pid, divisions, counters, offsets,
                         *args, **kwargs)

    EXPORT._parse_subject = parse
    EXPORT._place_notes = place
    EXPORT._part_xml = part_xml
    try:
        xml, report = EXPORT.to_musicxml(data)
    finally:
        EXPORT._parse_subject = orig_parse
        EXPORT._place_notes = orig_place
        EXPORT._part_xml = orig_part

    # ── THE CONTROL, AND IT CAN FAIL (rule 7) ────────────────────────────
    if break_control and refusals:
        refusals.pop()
    ours = collections.Counter(r for _, r in refusals)
    theirs = collections.Counter(report.get("notes_not_written") or {})
    if ours != theirs:
        raise ControlFailed(
            f"per-subject refusals {dict(ours)} != the exporter's own "
            f"{dict(theirs)} — the viewer would be showing a decomposition "
            f"that does not add up to the rule it claims to decompose")

    by_glyph: Dict[str, List[str]] = {}
    for sub, reason in refusals:
        if sub:
            by_glyph.setdefault(sub, []).append(reason)

    names: Dict[str, str] = {}
    for m in re.finditer(r'<score-part id="([^"]+)">\s*<part-name>([^<]*)</part-name>',
                         xml):
        names[m.group(1)] = m.group(2)

    return ExportPass(xml=xml, report=report, refusals=by_glyph, placed=placed,
                      runs=runs_seen, part_of_staff=part_of_staff,
                      part_names=names, offsets=offsets_seen.get("v"))


# ═════════════════════════════════════════════════════════════════════════
# 4. THE RECORD, INDEXED
# ═════════════════════════════════════════════════════════════════════════

def _is_notehead(name: str) -> bool:
    from ...yolo_detector import _class_name_to_category
    return _class_name_to_category(str(name)) == "notehead"


def _category(name: str) -> str:
    from ...yolo_detector import _class_name_to_category
    return _class_name_to_category(str(name))


#: The colour families the GATHER overlay groups detector boxes into. ⚠️ The
#: MEMBERSHIP is `_class_name_to_category`'s, never a second class list; this
#: only says which of its answers get their own colour and which share
#: `other`.
OVERLAY_FAMILIES: Tuple[str, ...] = ("notehead", "rest", "clef", "key",
                                     "accidental", "other")


def _overlay_family(name: str) -> str:
    cat = _category(name)
    if cat in ("notehead", "rest", "clef", "accidental"):
        n = str(name).lower()
        if cat == "accidental" and n.startswith("key"):
            return "key"
        return cat
    return "other"


class ReviewData:
    """One record, one PDF, indexed once and held for the session."""

    def __init__(self, record_path: Path, pdf_path: Optional[Path], *,
                 break_control: bool = False) -> None:
        self.record_path = Path(record_path)
        self.pdf_path = Path(pdf_path) if pdf_path else None
        self.data = load_record(self.record_path)
        if "record" not in self.data:
            raise KeyError(
                f"{record_path} has no 'record' key. A staged record is "
                "{'record': {...}}; refusing to guess.")
        self.rec_dict: Dict[str, Any] = self.data["record"]
        self.provenance: Dict[str, Any] = self.data.get("provenance") or {}
        args = ((self.provenance.get("settings") or {}).get("args") or {})
        self.dpi = int(args.get("dpi") or 600)

        self.obs: List[dict] = list(self.rec_dict.get("observations") or ())
        self.abst: List[dict] = list(self.rec_dict.get("abstentions") or ())
        self.vrd: List[dict] = list(self.rec_dict.get("verdicts") or ())

        self.rows_by_id: Dict[str, dict] = {}
        for bucket, kind in ((self.obs, "observation"),
                             (self.abst, "abstention"),
                             (self.vrd, "verdict")):
            for r in bucket:
                if r.get("id"):
                    self.rows_by_id[r["id"]] = r
        self._row_kind = {}
        for r in self.obs:
            self._row_kind[r.get("id")] = "observation"
        for r in self.abst:
            self._row_kind[r.get("id")] = "abstention"
        for r in self.vrd:
            self._row_kind[r.get("id")] = "verdict"

        self.obs_by_qs: Dict[Tuple[str, str], List[dict]] = {}
        for o in self.obs:
            self.obs_by_qs.setdefault((o["quantity"], o["subject"]), []).append(o)
        self.vrd_by_qs: Dict[Tuple[str, str], List[dict]] = {}
        for v in self.vrd:
            self.vrd_by_qs.setdefault((v["quantity"], v["subject"]), []).append(v)
        self.abs_by_qs: Dict[Tuple[str, str], List[dict]] = {}
        for a in self.abst:
            self.abs_by_qs.setdefault((a["quantity"], a["subject"]), []).append(a)

        #: ⚠️ BY SUBJECT, and this is not an optimisation. `staff_stage_view`
        #: asks for the verdicts of ~200 glyph subjects on one request; a
        #: linear scan of 101,361 verdicts per subject is 20 million
        #: comparisons a click, which is the difference between a viewer a
        #: human uses and one he closes.
        self.vrd_by_subject: Dict[str, List[dict]] = {}
        for v in self.vrd:
            self.vrd_by_subject.setdefault(v["subject"], []).append(v)
        self.abs_by_subject: Dict[str, List[dict]] = {}
        for a in self.abst:
            self.abs_by_subject.setdefault(a["subject"], []).append(a)

        #: staff key -> the glyph subjects gathered under it, in record order
        self.glyphs_by_staff: Dict[str, List[str]] = {}
        self.glyph_row: Dict[str, dict] = {}
        #: staff key -> {cell index: `Q.CELL_BOX` value}
        self.cells_by_staff: Dict[str, Dict[int, list]] = {}
        #: staff key -> the `Q.INK` rows filed on its cells
        self.ink_by_staff: Dict[str, List[Tuple[int, dict]]] = {}
        for o in self.obs:
            sub = o["subject"]
            p = sub.split("/")
            q = o["quantity"]
            if q == Q.GLYPH_BOX and len(p) >= 6 and p[0] == "glyph":
                self.glyph_row[sub] = o
                self.glyphs_by_staff.setdefault(
                    "/".join(["staff"] + p[1:4]), []).append(sub)
            elif q == Q.CELL_BOX and len(p) >= 5 and p[0] == "cell":
                self.cells_by_staff.setdefault(
                    "/".join(["staff"] + p[1:4]), {})[int(p[4])] = o["value"]
            elif q == Q.INK and len(p) >= 5 and p[0] == "cell":
                self.ink_by_staff.setdefault(
                    "/".join(["staff"] + p[1:4]), []).append((int(p[4]), o))

        #: every staff the record filed a `Q.STAFF_LINES` row on
        self.staff_keys: List[str] = sorted(
            {s for (q, s) in self.obs_by_qs if q == Q.STAFF_LINES},
            key=_staff_sort_key)

        self.export = run_export(self.data, break_control=break_control)
        self.rec = EXPORT.Record(self.data)      # for `trace.trace`
        self._funnels: Optional[List[dict]] = None
        self._frame_ok = _load_frame_ok()
        self._crop_cache: Dict[str, Path] = {}

    # ── the funnel, per staff ────────────────────────────────────────────
    def funnels(self) -> List[dict]:
        """Every staff, ordered by heads LOST descending.

        ⚠️ The buckets are `run_export`'s instrumentation of `_place_notes`,
        which is the exporter's own ladder. Nothing here decides a refusal.
        """
        if self._funnels is not None:
            return self._funnels
        out = []
        for key in self.staff_keys:
            out.append(self.staff_funnel(key))
        out.sort(key=lambda r: (-r["heads_lost"], _staff_sort_key(r["staff"])))
        self._funnels = out
        return out

    def staff_funnel(self, staff: str) -> Dict[str, Any]:
        p = staff.split("/")
        page, system, ordinal = int(p[1]), int(p[2]), int(p[3])
        boxed = written = 0
        refused: collections.Counter = collections.Counter()
        all_boxes = 0
        for sub in self.glyphs_by_staff.get(staff, ()):
            row = self.glyph_row[sub]
            all_boxes += 1
            name = row["value"][0]
            if not _is_notehead(name):
                continue
            boxed += 1
            det = self.export.placed.get(sub)
            if det is not None and det.get("category") == "notehead":
                written += 1
            for r in self.export.refusals.get(sub, ()):
                refused[r] += 1
        run = self.export.runs.get(staff)
        return {
            "staff": staff, "page": page, "system": system,
            "staff_ordinal": ordinal,
            "part_name": self.part_name_of(staff),
            "part_id": self.export.part_of_staff.get(staff),
            "clef": self.verdict_summary(staff, Q.CLEF),
            "key_signature": self.verdict_summary(staff, Q.KEY_SIGNATURE),
            "instrument": self.verdict_summary(staff, Q.INSTRUMENT),
            "slot_index": self.verdict_summary(staff, Q.SLOT_INDEX),
            "n_measures": getattr(run, "n_measures", None),
            "boxes_all": all_boxes,
            "heads_boxed": boxed,
            "heads_written": written,
            "heads_lost": boxed - written,
            "refused": dict(sorted(refused.items())),
        }

    # ── little readers ───────────────────────────────────────────────────
    def verdict_summary(self, subject: str, quantity: str
                        ) -> Optional[Dict[str, Any]]:
        rows = self.vrd_by_qs.get((quantity, subject))
        if not rows:
            # ⚠️ ABSENT vs DECLINED, kept apart: a reader that abstained left
            # an abstention row; no row at all means nobody ran.
            if self.abs_by_qs.get((quantity, subject)):
                return {"state": State.DECLINED.value, "outcome": None,
                        "reason": self.abs_by_qs[(quantity, subject)][-1]
                        .get("reason")}
            return None
        v = rows[-1]
        return {"state": State.READ.value, "id": v.get("id"),
                "outcome": v.get("outcome"), "value": v.get("value"),
                "reason": v.get("reason"), "decided_by": v.get("decider")}

    def part_name_of(self, staff: str) -> Optional[str]:
        run = self.export.runs.get(staff)
        if run is not None and getattr(run, "name", None):
            return run.name
        pid = self.export.part_of_staff.get(staff)
        if pid:
            return self.export.part_names.get(pid)
        v = self.verdict_summary(staff, Q.INSTRUMENT)
        if v and v.get("outcome") == "decided":
            return str(v.get("value"))
        return None

    def bar_number(self, staff: str, cell_index: int) -> Optional[int]:
        """The `<measure number=>` the exporter would write for this cell.

        ⚠️ `base + i + 1` is `_part_xml`'s own arithmetic, read off the
        offsets that pass produced rather than recomputed. None where the
        document numbering was REFUSED — which is a real answer.
        """
        if not self.export.offsets:
            return None
        p = staff.split("/")
        base = self.export.offsets.get((int(p[1]), int(p[2])))
        return None if base is None else base + cell_index + 1

    #: How many of a verdict's rows are spelled out in a payload. ⚠️ A
    #: `arc_owner` verdict considers ~1,800 rows and a staff carries hundreds
    #: of verdicts; the whole ADJUDICATE payload for one Litolff staff was
    #: 5.8 MB before this cap. The TRUNCATION IS MARKED with the number
    #: withheld and the counts are reported separately, so a short list can
    #: never read as a small basis — `trace._short`'s own discipline.
    ROW_LIMIT = 60

    def resolve_rows(self, ids: Sequence[str],
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """`reader × quantity × value × score`, for a verdict's own rows.

        ⚠️ A row id the record does not hold is reported as UNRESOLVED and
        never dropped: a silently shorter list is how a basis stops being
        checkable.
        """
        ids = list(ids)
        cap = self.ROW_LIMIT if limit is None else limit
        head, rest = ids[:cap], len(ids) - cap
        out = []
        if rest > 0:
            out.append({"row": "truncated", "n_shown": cap, "n_more": rest,
                        "note": "the payload spells out the first rows only; "
                                "the verdict's own counts are beside it and "
                                "are not truncated"})
        for rid in head:
            r = self.rows_by_id.get(rid)
            if r is None:
                out.append({"id": rid, "row": "unresolved"})
                continue
            kind = self._row_kind.get(rid, "row")
            item = {"id": rid, "row": kind, "subject": r.get("subject"),
                    "quantity": r.get("quantity"), "reader": r.get("reader"),
                    "frame": r.get("frame")}
            if kind == "abstention":
                item["reason"] = r.get("reason")
            elif kind == "verdict":
                item["outcome"] = r.get("outcome")
                item["value"] = TRACE._short(r.get("value"))
                item["reason"] = r.get("reason")
                item["decided_by"] = r.get("decider")
            else:
                item["value"] = TRACE._short(r.get("value"))
                item["score"] = r.get("score")
            det = r.get("detail") or {}
            if det:
                item["detail"] = {k: TRACE._short(v) for k, v in det.items()}
            out.append(item)
        return out


def _staff_sort_key(staff: str) -> Tuple[int, int, int]:
    p = staff.split("/")
    try:
        return (int(p[1]), int(p[2]), int(p[3]))
    except (IndexError, ValueError):
        return (10 ** 6, 0, 0)


# ═════════════════════════════════════════════════════════════════════════
# 5. THE VIEWS
# ═════════════════════════════════════════════════════════════════════════

def _row_view(r: dict, kind: str) -> Dict[str, Any]:
    out = {"id": r.get("id"), "row": kind, "quantity": r.get("quantity"),
           "reader": r.get("reader"), "frame": r.get("frame"),
           "detail": {k: TRACE._short(v) for k, v in (r.get("detail") or {}).items()}}
    if kind == "abstention":
        out["reason"] = r.get("reason")
    else:
        out["value"] = TRACE._short(r.get("value"))
        out["score"] = r.get("score")
    return out


def subject_view(D: ReviewData, key: str) -> Dict[str, Any]:
    """Every stage's story for ONE subject — `trace.trace`'s answer, with the
    row ids resolved and each stage's STATE named.

    ⚠️ The reasoning is `trace.py`'s. This adds the rows a verdict read and
    the ABSENT/DECLINED distinction; it re-derives nothing.
    """
    t = TRACE.trace(D.rec, key, export_report=D.export.report)
    buckets: Dict[str, List[dict]] = {"gather_observations": [],
                                      "gather_abstentions": [],
                                      "adjudicate": [], "evaluate": [],
                                      "infer": [], "unattributed": []}
    for step in t["steps"]:
        if step["stage"] == "GATHER":
            key_ = ("gather_abstentions" if step["row"] == "abstention"
                    else "gather_observations")
            row = D.rows_by_id.get(step["id"]) or {}
            buckets[key_].append(_row_view(
                row, "abstention" if step["row"] == "abstention"
                else "observation"))
            continue
        step = dict(step)
        step["rows_read"] = D.resolve_rows(step.get("read") or ())
        step["rows_basis"] = D.resolve_rows(
            (D.rows_by_id.get(step["id"], {}).get("basis")) or ())
        step["decided_by"] = step.get("decider")
        buckets.get(step["stage"].lower(),
                    buckets["unattributed"]).append(step)

    def _state(observed: int, declined: int) -> str:
        if observed:
            return State.READ.value
        if declined:
            return State.DECLINED.value
        return State.ABSENT.value

    stages = {
        "gather": {
            "state": _state(len(buckets["gather_observations"]),
                            len(buckets["gather_abstentions"])),
            "observations": buckets["gather_observations"],
            "abstentions": buckets["gather_abstentions"],
        },
    }
    for name in ("adjudicate", "evaluate", "infer"):
        rows = buckets[name]
        declined = sum(1 for r in rows if r.get("outcome") == "abstained")
        decided = len(rows) - declined
        stages[name] = {
            "state": _state(decided, declined),
            "verdicts": rows,
            "did_not_run": not rows,
        }
    stages["unattributed"] = {"verdicts": buckets["unattributed"]}

    refused = D.export.refusals.get(key, [])
    det = D.export.placed.get(key)
    if det is not None:
        ex = {"state": "written", "note": _note_facts(det)}
    elif refused:
        ex = {"state": "refused", "buckets": refused}
    elif key.startswith("glyph/"):
        ex = {"state": "never_asked",
              "note": "the exporter's loop never reached this row — it is "
                      "neither a notehead nor a rest, or it carried no "
                      "`notehead_class` observation"}
    else:
        ex = {"state": "not_a_note",
              "note": "EXPORT writes NOTES from glyph subjects; this subject "
                      "is not one"}
    stages["export"] = ex

    return {"subject": key, "kind": t["kind"], "context": t["context"],
            "n_rows_at_subject": t["n_rows_at_subject"], "stages": stages}


def _note_facts(det: Dict[str, Any]) -> Dict[str, Any]:
    """The `<note>` a head became, spelled the way the file spells it."""
    pitch = det.get("pitch")
    step = alter = octave = None
    if pitch:
        parsed = _legacy._parse_pitch(str(pitch))
        if parsed:
            step, spelled, octave = parsed
            alter = spelled or None
    return {"pitch": pitch, "step": step, "alter": alter, "octave": octave,
            "type": det.get("duration_type"), "dots": det.get("dots"),
            "beats": det.get("duration_beats"),
            "measure_rest": bool(det.get("measure_rest")),
            "key_alteration": det.get("key_alteration"),
            "category": det.get("category"), "class": det.get("class"),
            "tuplet": det.get("tuplet")}


def staff_stage_view(D: ReviewData, staff: str, stage: str) -> Dict[str, Any]:
    """Every verdict of ONE stage over ONE staff — the staff's own subjects
    first, then its glyphs.

    ⚠️ `stage` is matched through `trace.stage_of_decider`, which is derived
    from the registries; a decider nobody claims lands in UNATTRIBUTED and is
    SHOWN rather than dropped.
    """
    want = stage.upper()
    staff_subjects = [staff]
    p = staff.split("/")
    staff_subjects.append(f"system/{p[1]}/{p[2]}")
    cells = [f"cell/{p[1]}/{p[2]}/{p[3]}/{i}"
             for i in sorted(D.cells_by_staff.get(staff, {}))]

    def _verdicts_at(subject: str) -> List[dict]:
        out = []
        for v in D.vrd_by_subject.get(subject, ()):
            if TRACE.stage_of_decider(v["decider"]) != want:
                continue
            step = TRACE._verdict_step(want, v, D.rows_by_id)
            step["rows_read"] = D.resolve_rows(step.get("read") or ())
            step["rows_basis"] = D.resolve_rows(v.get("basis") or ())
            step["decided_by"] = v.get("decider")
            step["subject"] = subject
            out.append(step)
        return out

    def _abstentions_at(subject: str) -> List[dict]:
        return [_row_view(a, "abstention")
                for a in D.abs_by_subject.get(subject, ())]

    head = []
    for subject in staff_subjects:
        head.append({"subject": subject,
                     "verdicts": _verdicts_at(subject),
                     "abstentions": (_abstentions_at(subject)
                                     if want == "ADJUDICATE" else []),
                     })
    per_cell = []
    if want == "ADJUDICATE":
        for c in cells:
            vs = _verdicts_at(c)
            if vs:
                per_cell.append({"subject": c, "verdicts": vs})

    glyph_rows = []
    for sub in D.glyphs_by_staff.get(staff, ()):
        row = D.glyph_row[sub]
        vs = [v for v in D.vrd_by_subject.get(sub, ())
              if TRACE.stage_of_decider(v["decider"]) == want]
        abs_ = D.abs_by_subject.get(sub, [])
        if not vs and want != "ADJUDICATE":
            continue
        name = row["value"][0]
        glyph_rows.append({
            "glyph": sub, "class": name, "family": _overlay_family(name),
            "cell": int(sub.split("/")[4]),
            "bar": D.bar_number(staff, int(sub.split("/")[4])),
            "n_verdicts": len(vs), "n_abstentions": len(abs_),
            "quantities": sorted({v["quantity"] for v in vs}),
            "outcomes": dict(collections.Counter(v["outcome"] for v in vs)),
            "export": ("written" if sub in D.export.placed
                       else ("refused:" + ",".join(D.export.refusals[sub])
                             if sub in D.export.refusals else "never_asked")),
        })
    return {"staff": staff, "stage": stage, "staff_level": head,
            "cells": per_cell, "glyphs": glyph_rows}


def infer_view(D: ReviewData, staff: str) -> Dict[str, Any]:
    """Every INFERRED value on the staff, labelled, with its rule and gate.

    ⚠️ The gate is read off `infer.RULES` — the `Switch` carries the flag NAME
    and the predicate as ONE object precisely so a report can name the flag
    that held a rule back without a second table. A rule whose default moves
    is reported with the flag it actually has.

    ⚠️ The CANDIDATES an inference collapsed are the SUPERSEDED verdict's own.
    INFER may only collapse a NARROWED verdict to one of that reader's own
    candidates and never overturns a DECIDED one (CLAUDE.md §4a), so showing
    the prior row's candidates is showing what the rule was allowed to pick
    from.
    """
    from .. import infer as INF
    INF._ensure_rules()
    gates = {}
    for r in INF.RULES:
        name = getattr(r.inference, "value", str(r.inference))
        gates[name] = {"env": r.switch.env, "on": bool(r.switch()),
                       "stub": bool(r.stub), "target": r.target,
                       "reads": list(r.reads), "bound": r.bound,
                       "forbids_argmax": bool(r.forbids_argmax)}

    p = staff.split("/")
    subjects = [staff, f"system/{p[1]}/{p[2]}"]
    subjects += [f"cell/{p[1]}/{p[2]}/{p[3]}/{i}"
                 for i in sorted(D.cells_by_staff.get(staff, {}))]
    subjects += list(D.glyphs_by_staff.get(staff, ()))

    rows: List[dict] = []
    for sub in subjects:
        for v in D.vrd_by_subject.get(sub, ()):
            if TRACE.stage_of_decider(v["decider"]) != "INFER":
                continue
            step = TRACE._verdict_step("INFER", v, D.rows_by_id)
            step["subject"] = sub
            step["decided_by"] = v.get("decider")
            step["rows_read"] = D.resolve_rows(step.get("read") or ())
            step["rows_basis"] = D.resolve_rows(v.get("basis") or ())
            dec = str(v.get("decider") or "")
            rule = (dec[len(INF.DECIDER_PREFIX):]
                    if dec.startswith(INF.DECIDER_PREFIX) else dec)
            step["rule"] = rule
            step["rule_gate"] = gates.get(rule)
            step["INFERRED"] = True
            sup = step.get("supersedes") or {}
            prior = D.rows_by_id.get(sup.get("id")) if sup.get("id") else None
            step["prior_candidates"] = (prior or {}).get("candidates") or []
            step["prior_outcome"] = (prior or {}).get("outcome")
            rows.append(step)

    return {"staff": staff, "stage": "infer", "inferences": rows,
            "gates": gates,
            "reach": (D.data.get("inference") or {}).get("reach"),
            "counts": (D.data.get("inference") or {}).get("counts"),
            "did_not_run": not rows,
            "note": "INFER writes only where the record has no answer, may "
                    "only collapse a NARROWED verdict to one of that "
                    "reader's own candidates, and never overturns a DECIDED "
                    "one — CLAUDE.md §4a. An empty list is a REACH of zero "
                    "on this staff, not a rule that agreed with us."}


def export_view(D: ReviewData, staff: str) -> Dict[str, Any]:
    """Per head: the `<note>` it became, or the bucket that refused it."""
    heads = []
    for sub in D.glyphs_by_staff.get(staff, ()):
        row = D.glyph_row[sub]
        name = row["value"][0]
        cell = int(sub.split("/")[4])
        det = D.export.placed.get(sub)
        refused = D.export.refusals.get(sub, [])
        heads.append({
            "glyph": sub, "class": name, "family": _overlay_family(name),
            "is_notehead": _is_notehead(name),
            "cell": cell, "bar": D.bar_number(staff, cell),
            "bbox_page_px": (row.get("detail") or {}).get("bbox_page_px"),
            "state": ("written" if det is not None
                      else "refused" if refused else "never_asked"),
            "note": _note_facts(det) if det is not None else None,
            "refused": refused,
        })
    run = D.export.runs.get(staff)
    pid = D.export.part_of_staff.get(staff)
    lo = D.bar_number(staff, 0)
    hi = D.bar_number(staff, max(0, (getattr(run, "n_measures", 0) or 1) - 1))
    return {
        "staff": staff, "part_id": pid,
        "part_name": D.export.part_names.get(pid or ""),
        "measures": [lo, hi],
        "heads": heads,
        "counts": D.staff_funnel(staff),
        "notes_not_written_document": D.export.report.get("notes_not_written"),
    }


# ═════════════════════════════════════════════════════════════════════════
# 6. THE CROP
# ═════════════════════════════════════════════════════════════════════════

def crop_frame_for(D: ReviewData, staff: str, zoom: int) -> Tuple[CropFrame, dict]:
    """The window, and the geometry the browser draws on it.

    ⚠️ The window is cut around the staff's OWN five `Q.STAFF_LINES` and its
    own cells, so the picture says which staff it is about — Sean's own
    correction of 2026-09-23, *"there is a staff at the top and a staff at
    the bottom - i dont know which staff the cell is focussing on."*
    """
    lines = (D.obs_by_qs.get((Q.STAFF_LINES, staff)) or [{}])[0].get("value")
    if not lines:
        raise KeyError(f"{staff} has no {Q.STAFF_LINES} row")
    sp = (D.obs_by_qs.get((Q.STAFF_SPACING, staff)) or [{}])[0].get("value")
    spacing = float(sp) if sp else (float(lines[-1]) - float(lines[0])) / 4.0
    cells = dict(D.cells_by_staff.get(staff, {}))
    if cells:
        x0 = min(b[0] for b in cells.values())
        x1 = max(b[2] for b in cells.values())
    else:
        x0, x1 = 0.0, 0.0
    pad_x, pad_y = spacing * 3, spacing * 7
    frame = CropFrame(
        x0=int(max(0, x0 - pad_x)), y0=int(max(0, float(lines[0]) - pad_y)),
        x1=int(x1 + pad_x), y1=int(float(lines[-1]) + pad_y),
        zoom=zoom, dpi=D.dpi)
    geom = {"staff_lines": [float(y) for y in lines], "spacing": spacing,
            "cells": [{"index": i, "box": [float(v) for v in cells[i]],
                       "bar": D.bar_number(staff, i)}
                      for i in sorted(cells)]}
    return frame, geom


def render_crop(D: ReviewData, staff: str, frame: CropFrame,
                geom: dict) -> Tuple[Path, Dict[str, Any]]:
    """The PNG (cached to the scratchpad, never into the repo) and the frame
    control's verdict.

    ⚠️ NO OVERLAY IS BURNED IN. The browser draws every box over this raster
    so the human can toggle families and click one — and so the only place
    page pixels become crop pixels is `CropFrame`, which is tested.
    """
    import fitz
    import numpy as np
    from PIL import Image

    if D.pdf_path is None or not D.pdf_path.exists():
        raise FileNotFoundError(
            f"no PDF to cut a crop from ({D.pdf_path}) — the GATHER view is "
            f"a PRINT crop or it is nothing")
    page = int(staff.split("/")[1])
    stamp = hashlib.sha1(
        f"{D.pdf_path}|{D.pdf_path.stat().st_mtime_ns}|{page}|{staff}|"
        f"{frame.as_json()}".encode()).hexdigest()[:16]
    cache_dir = _scratch_dir() / "crops"
    cache_dir.mkdir(parents=True, exist_ok=True)
    png = cache_dir / f"{staff.replace('/', '-')}-{stamp}.png"
    meta_p = png.with_suffix(".json")
    if png.exists() and meta_p.exists():
        return png, json.loads(meta_p.read_text())

    doc = fitz.open(str(D.pdf_path))
    pm = doc[page].get_pixmap(dpi=frame.dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))
    arr = np.asarray(im.convert("L"), dtype=float)
    if D._frame_ok is None:
        control = {"ran": False, "ok": None, "contrast": None,
                   "note": "the frame control lives in "
                           "benchmarks/omr-infer-duration-print-2026-09/probe/"
                           "crop_inferred.py and this tree does not hold it — "
                           "the control was NOT RUN, which is not the same as "
                           "passing it"}
    else:
        ok, contrast = D._frame_ok(arr, geom["staff_lines"], geom["spacing"])
        control = {"ran": True, "ok": bool(ok), "contrast": round(float(contrast), 2),
                   "note": ("the staff's own five lines are materially darker "
                            "than a half-space off them, so this render IS "
                            "the record's raster"
                            if ok else
                            "THIS RENDER IS NOT THE RECORD'S RASTER — nothing "
                            "drawn on it is evidence, and GATHER actions are "
                            "refused")}
    x1 = min(im.width, frame.x1)
    y1 = min(im.height, frame.y1)
    crop = im.crop((frame.x0, frame.y0, x1, y1))
    if frame.zoom != 1:
        crop = crop.resize(((x1 - frame.x0) * frame.zoom,
                            (y1 - frame.y0) * frame.zoom), Image.LANCZOS)
    crop.save(png)
    meta = {"control": control, "raster": [im.width, im.height],
            "crop_page_px": [frame.x0, frame.y0, x1, y1],
            "zoom": frame.zoom, "dpi": frame.dpi}
    meta_p.write_text(json.dumps(meta, indent=1))
    doc.close()
    return png, meta


def _scratch_dir() -> Path:
    """⚠️ NEVER INTO THE REPO. A crop is a derived raster of a gitignored
    library PDF and belongs in the session scratchpad."""
    env = os.environ.get("CLAUDE_SCRATCHPAD") or os.environ.get("TMPDIR")
    base = Path(env) if env else Path("/tmp")
    d = base / "reengrave-stage-review"
    d.mkdir(parents=True, exist_ok=True)
    return d


def gather_view(D: ReviewData, staff: str, zoom: int) -> Dict[str, Any]:
    frame, geom = crop_frame_for(D, staff, zoom)
    p = staff.split("/")
    boxes = []
    for sub in D.glyphs_by_staff.get(staff, ()):
        row = D.glyph_row[sub]
        name, x, y, w, h = row["value"]
        page_box = (row.get("detail") or {}).get("bbox_page_px")
        conf = (D.obs_by_qs.get((Q.GLYPH_CONF, sub)) or [{}])[0].get("value")
        boxes.append({
            "glyph": sub, "class": name, "family": _overlay_family(name),
            "category": _category(name),
            "cell": int(sub.split("/")[4]),
            "bar": D.bar_number(staff, int(sub.split("/")[4])),
            "conf": conf,
            "bbox_page_px": [float(v) for v in page_box] if page_box else None,
            # ⚠️ DECLINED, not defaulted: a canonical cell frame cannot answer
            # a page question, so a row with no page box is SHOWN as having
            # none rather than placed at a made-up x.
            "page_box_state": "read" if page_box else "declined",
            "written": sub in D.export.placed,
            "refused": D.export.refusals.get(sub, []),
        })
    ink_rows: Dict[int, List[dict]] = {}
    for ci, o in D.ink_by_staff.get(staff, ()):
        ink_rows.setdefault(ci, []).append(o)
    ink = []
    for ci in sorted(ink_rows):
        det = ink_rows[ci][0].get("detail") or {}
        ink.append({"cell": ci, "bar": D.bar_number(staff, ci),
                    "n_components": det.get("ink_n_components"),
                    "detail": {k: TRACE._short(v) for k, v in det.items()},
                    "rows": len(ink_rows[ci])})
    return {
        "staff": staff, "page": int(p[1]), "system": int(p[2]),
        "staff_ordinal": int(p[3]),
        "part_name": D.part_name_of(staff),
        "crop": frame.as_json(),
        "crop_url": f"/api/crop.png?staff={staff}&zoom={zoom}",
        "staff_lines": geom["staff_lines"], "spacing": geom["spacing"],
        "cells": geom["cells"],
        "boxes": boxes,
        "ink": ink,
        "ink_note": ("`Q.INK` is the population BENEATH the detector — one "
                     "row per connected ink component, or (with "
                     "`ink_rows: False`) one per CELL carrying "
                     "`ink_n_components`. It is not a set of subjects."),
        "counts": D.staff_funnel(staff),
        "families": list(OVERLAY_FAMILIES),
    }


# ═════════════════════════════════════════════════════════════════════════
# 7. THE APP
# ═════════════════════════════════════════════════════════════════════════

def _read_static(name: str) -> str:
    return (_STATIC_DIR / name).read_text()


def rerun_available() -> bool:
    """Is lane (A)'s CLI in this tree? ⚠️ Asked by `find_spec`, not by a
    filename: a module that is present but broken fails loudly at run time
    rather than being reported as absent."""
    try:
        return importlib.util.find_spec(
            "tools.omr.staged.review.rerun") is not None
    except (ImportError, ValueError):
        return False


def create_app(D: ReviewData, sidecar_path: Optional[Path],
               default_staff: Optional[str], *, default_zoom: int = 2):
    """The app. ⚠️⚠️ FastAPI's names are imported at MODULE level, not here.

    `from __future__ import annotations` turns every annotation into a
    string, and FastAPI resolves a route's signature through pydantic in the
    MODULE namespace — so a `Request` parameter or an `HTMLResponse` return
    annotation on a route defined inside this function raises
    `PydanticUndefinedAnnotation` when the app is BUILT. That is after every
    view function has been called and passed, which is exactly how the first
    version of this file shipped six green tests and a server that could not
    listen. `test_stage_review.TestTheAppItself` builds the app and hits
    every route for that reason.
    """
    app = FastAPI(title="ReEngrave stage review",
                  description=__doc__.splitlines()[0])
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    state: Dict[str, Any] = {"sidecar": None, "rerun": None}

    def sidecar_for(staff: str) -> Sidecar:
        sc = state.get("sidecar")
        if sc is not None and sc.doc.get("staff") == staff:
            return sc
        path = (Path(sidecar_path) if sidecar_path
                else default_sidecar_path(_ROOT, staff))
        sc = Sidecar(path, record=str(D.record_path), staff=staff)
        state["sidecar"] = sc
        return sc

    # ⚠️ NO RETURN ANNOTATION ON THIS ROUTE. `from __future__ import
    # annotations` makes every annotation a string, and FastAPI resolves a
    # route's return annotation through pydantic in the MODULE namespace —
    # where `HTMLResponse`, imported inside this function, does not exist.
    # The failure is a `PydanticUndefinedAnnotation` at start-up, not at
    # import, so it is invisible to every test that does not serve.
    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(_read_static("index.html"))

    @app.get("/api/session")
    def api_session() -> dict:
        return {
            "record": str(D.record_path),
            "pdf": str(D.pdf_path) if D.pdf_path else None,
            "dpi": D.dpi,
            "provenance": {"commit": D.provenance.get("commit"),
                           "dirty": D.provenance.get("dirty")},
            # ⚠️ §4b: a record from a dirty tree, or with `dirty is None`,
            # is NOT a baseline. Said on the page rather than only here.
            "is_a_baseline": D.provenance.get("dirty") is False,
            "default_staff": default_staff,
            "zoom": default_zoom,
            "n_staves": len(D.staff_keys),
            "rows": {"observations": len(D.obs), "abstentions": len(D.abst),
                     "verdicts": len(D.vrd)},
            "export_control": "per-subject refusals reproduce "
                              "report['notes_not_written'] exactly",
            "notes_not_written": D.export.report.get("notes_not_written"),
            "rerun_available": rerun_available(),
            "sidecar_default": str(default_sidecar_path(
                _ROOT, default_staff or "staff/0/0/0")),
            "optional_fields": OPTIONAL_FIELDS,
        }

    @app.get("/api/staves")
    def api_staves() -> dict:
        return {"staves": D.funnels(),
                "ordered_by": "heads_lost descending"}

    @app.get("/api/gather")
    def api_gather(staff: str, zoom: Optional[int] = None) -> dict:
        _known(staff)
        return gather_view(D, staff, int(zoom or default_zoom))

    @app.get("/api/crop.png")
    def api_crop(staff: str, zoom: Optional[int] = None):
        _known(staff)
        frame, geom = crop_frame_for(D, staff, int(zoom or default_zoom))
        png, meta = render_crop(D, staff, frame, geom)
        return FileResponse(str(png), media_type="image/png",
                            headers={"X-Frame-Control": json.dumps(meta["control"])})

    @app.get("/api/crop_meta")
    def api_crop_meta(staff: str, zoom: Optional[int] = None) -> dict:
        _known(staff)
        frame, geom = crop_frame_for(D, staff, int(zoom or default_zoom))
        try:
            _png, meta = render_crop(D, staff, frame, geom)
        except Exception as e:                          # noqa: BLE001
            return {"control": {"ran": False, "ok": None,
                                "note": f"the crop could not be cut: {e!r}"},
                    "crop": frame.as_json()}
        meta["crop"] = frame.as_json()
        return meta

    @app.get("/api/stage")
    def api_stage(staff: str, stage: str) -> dict:
        _known(staff)
        if stage == "infer":
            return infer_view(D, staff)
        if stage == "export":
            return export_view(D, staff)
        if stage not in ("adjudicate", "evaluate"):
            raise HTTPException(400, f"unknown stage {stage!r}")
        return staff_stage_view(D, staff, stage)

    @app.get("/api/subject")
    def api_subject(key: str) -> dict:
        return subject_view(D, key)

    @app.get("/api/render.svg")
    def api_render(staff: str):
        """Our own render of the bars this staff wrote — Verovio over the
        exported MusicXML, sliced to this part.

        ⚠️ ABSTAINS rather than guessing: no Verovio, no part id, or a slice
        that will not load is reported as such, never as an empty stave.
        """
        _known(staff)
        out = _render_part_svg(D, staff)
        if out is None or out.get("svg") is None:
            return JSONResponse(
                {"svg": None, "reason": (out or {}).get("reason", "unknown")},
                status_code=200)
        return Response(out["svg"], media_type="image/svg+xml")

    @app.get("/api/classes")
    def api_classes() -> dict:
        from ...class_aliases import canonical, vocabulary
        names = sorted({canonical(n) for n in vocabulary()})
        by_family: Dict[str, List[str]] = {}
        for n in names:
            by_family.setdefault(_overlay_family(n), []).append(n)
        return {"names": names, "by_family": by_family,
                "note": "the canonical 157, from class_aliases.canonical over "
                        "the 208-class vocabulary — the model's names are "
                        "spelled twice and this is the one place they are "
                        "folded"}

    @app.get("/api/sidecar")
    def api_sidecar(staff: str) -> dict:
        sc = sidecar_for(staff)
        return {"path": str(sc.path), "sidecar": sc.doc,
                "rerun_available": rerun_available(),
                "rerun": state.get("rerun")}

    @app.post("/api/sidecar/action")
    async def api_action(request: Request) -> dict:
        body = await request.json()
        staff = body.get("staff")
        if not staff:
            raise HTTPException(400, "an action needs its staff")
        _known(staff)
        action = {k: v for k, v in body.items() if k != "staff"}
        if action.get("kind") in _GATHER_KINDS:
            # ⚠️ A BOX ON THE WRONG RASTER IS NOT EVIDENCE. The frame control
            # gates the GATHER actions, and a failure REFUSES rather than
            # annotating.
            frame, geom = crop_frame_for(D, staff, default_zoom)
            try:
                _png, meta = render_crop(D, staff, frame, geom)
            except Exception as e:                      # noqa: BLE001
                raise HTTPException(409, f"no crop, so no page pixels: {e!r}")
            ctl = meta["control"]
            if ctl.get("ran") and not ctl.get("ok"):
                raise HTTPException(
                    409, "the frame control FAILED on this render — a box "
                         "drawn on it is not evidence, so the action is "
                         "refused rather than saved with a caveat")
        try:
            saved = sidecar_for(staff).append(action)
        except ContractError as e:
            raise HTTPException(400, str(e))
        sc = sidecar_for(staff)
        return {"action": saved, "path": str(sc.path), "sidecar": sc.doc}

    @app.post("/api/sidecar/undo")
    async def api_undo(request: Request) -> dict:
        body = await request.json()
        staff, aid = body.get("staff"), body.get("id")
        _known(staff)
        sc = sidecar_for(staff)
        ok = sc.undo(aid)
        return {"removed": ok, "sidecar": sc.doc, "path": str(sc.path)}

    @app.post("/api/rerun")
    async def api_rerun(request: Request) -> dict:
        body = await request.json()
        staff = body.get("staff")
        _known(staff)
        sc = sidecar_for(staff)
        if not rerun_available():
            out = {"available": False,
                   "message": "re-run not available in this tree — "
                              "tools/omr/staged/review/rerun.py (lane A) is "
                              "not here. The sidecar IS saved: "
                              f"{sc.path}"}
            state["rerun"] = out
            return out
        out_dir = sc.path.parent / (sc.path.stem + "--rerun")
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-m", "tools.omr.staged.review.rerun",
               str(D.record_path), str(sc.path), "--out", str(out_dir)]
        proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True,
                              text=True, timeout=60 * 60)
        out = {"available": True, "cmd": " ".join(cmd),
               "returncode": proc.returncode,
               "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:],
               "out_dir": str(out_dir), "files": _feedback_files(out_dir)}
        state["rerun"] = out
        return out

    @app.get("/api/feedback")
    def api_feedback(staff: str) -> dict:
        sc = sidecar_for(staff)
        out_dir = sc.path.parent / (sc.path.stem + "--rerun")
        return {"out_dir": str(out_dir), "files": _feedback_files(out_dir),
                "rerun": state.get("rerun")}

    def _known(staff: Optional[str]) -> None:
        if not staff:
            raise HTTPException(400, "staff is required")
        if staff not in D.glyphs_by_staff and staff not in D.staff_keys:
            raise HTTPException(404, f"{staff} is not a staff in this record")

    return app


def _feedback_files(out_dir: Path) -> List[dict]:
    """Whatever lane (A) left, shown as it left it. ⚠️ Never invented: an
    empty list means the directory is empty."""
    if not out_dir.exists():
        return []
    out = []
    for p in sorted(out_dir.iterdir()):
        if not p.is_file():
            continue
        item = {"name": p.name, "bytes": p.stat().st_size}
        if p.suffix in (".json", ".md", ".txt") and p.stat().st_size < 400_000:
            item["text"] = p.read_text()
        out.append(item)
    return out


def _render_part_svg(D: ReviewData, staff: str) -> Optional[dict]:
    """Verovio over the exported MusicXML, sliced to this staff's part.

    ⚠️ `slice_measures` and `render_svg` are the COUNT PAGES' own
    (`benchmarks/omr-cleanup-count-2026-09/build_sidebyside.py`), imported
    rather than re-spelled — a second slicer would carry the attributes
    forward differently and the two renders would disagree about the clef.
    """
    pid = D.export.part_of_staff.get(staff)
    if not pid:
        return {"svg": None, "reason": f"{staff} was written into no <part> — "
                                       f"the join held it out or it has no "
                                       f"measures"}
    run = D.export.runs.get(staff)
    n = getattr(run, "n_measures", 0) or 0
    lo, hi = D.bar_number(staff, 0), D.bar_number(staff, max(0, n - 1))
    if lo is None:
        return {"svg": None, "reason": "the document bar numbering was "
                                       "REFUSED, so there is no measure range "
                                       "to slice"}
    sbs_path = (_ROOT / "benchmarks/omr-cleanup-count-2026-09"
                / "build_sidebyside.py")
    if not sbs_path.exists():
        return {"svg": None, "reason": "build_sidebyside.py is not in this "
                                       "tree, so the count pages' own slicer "
                                       "cannot be reused"}
    try:
        import verovio
    except ImportError:
        return {"svg": None, "reason": "verovio is not importable here"}
    sys.path.insert(0, str(sbs_path.parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "build_sidebyside_for_review", sbs_path)
        SBS = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(SBS)
        sliced = SBS.slice_measures(D.export.xml, {pid: (lo, hi)})
        tk = verovio.toolkit()
        svg = SBS.render_svg(tk, sliced, 2400)
    except Exception as e:                              # noqa: BLE001
        return {"svg": None, "reason": f"the slice would not render: {e!r}"}
    finally:
        if str(sbs_path.parent) in sys.path:
            sys.path.remove(str(sbs_path.parent))
    if not svg:
        return {"svg": None, "reason": "verovio returned no SVG"}
    return {"svg": svg, "part_id": pid, "measures": [lo, hi]}


# ═════════════════════════════════════════════════════════════════════════
# 8. CLI
# ═════════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    import uvicorn

    ap = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", default=None,
                    help="the edition the record was gathered from; without "
                         "it every view but GATHER still works and GATHER "
                         "says why it cannot cut a crop")
    ap.add_argument("--sidecar", default=None,
                    help="where the review-actions file goes (default: "
                         "benchmarks/omr-stage-review-2026-09/out/"
                         "review-actions--<staff>.json)")
    ap.add_argument("--staff", default=None,
                    help="open this staff directly, e.g. staff/3/0/9")
    ap.add_argument("--host", default="localhost",
                    help="`localhost` (default) listens dual-stack on ::1 AND "
                         "127.0.0.1; any other value binds literally")
    ap.add_argument("--port", type=int, default=5060)
    ap.add_argument("--zoom", type=int, default=2)
    ap.add_argument("--break-control", action="store_true",
                    help="RULE 7: drop one logged refusal on purpose so the "
                         "start-up control is SEEN failing before it is "
                         "trusted where it passes")
    ap.add_argument("--no-serve", action="store_true",
                    help="load, run the control, print the pick list and exit")
    args = ap.parse_args(argv)

    print(f"[review] loading {args.record} …", flush=True)
    D = ReviewData(Path(args.record),
                   Path(args.pdf) if args.pdf else None,
                   break_control=args.break_control)
    print(f"[review] {len(D.obs)} observations, {len(D.abst)} abstentions, "
          f"{len(D.vrd)} verdicts, {len(D.staff_keys)} staves, dpi {D.dpi}")
    print(f"[review] CONTROL PASSED: per-subject refusals reproduce "
          f"{D.export.report.get('notes_not_written')}")
    if D.provenance.get("dirty") is not False:
        print("[review] ⚠️ this record's tree was DIRTY (or unstamped) — "
              "per CLAUDE.md §4b it is not a baseline")
    top = D.funnels()[:5]
    for r in top:
        print(f"[review]   {r['staff']:<16} {str(r['part_name'] or '?'):<18} "
              f"boxed {r['heads_boxed']:>3}  written {r['heads_written']:>3}  "
              f"lost {r['heads_lost']:>3}  clef "
              f"{(r['clef'] or {}).get('outcome')}")
    if not rerun_available():
        print("[review] re-run not available in this tree (lane A's "
              "tools/omr/staged/review/rerun.py is absent) — the button will "
              "say so and the sidecar is still saved")
    if args.no_serve:
        return 0
    app = create_app(D, Path(args.sidecar) if args.sidecar else None,
                     args.staff, default_zoom=args.zoom)
    url = f"http://{args.host}:{args.port}"
    print(f"[review] listening on {url}")
    print(f"[review] open {url}/?staff={args.staff or D.funnels()[0]['staff']}")
    if args.host == "localhost":
        # ⚠️ DUAL-STACK ON PURPOSE. The first time Sean opened this page
        # (2026-09-23) it said "site can't be reached": the server listened
        # on 127.0.0.1 only and his browser resolved `localhost` to ::1
        # first. Binding `::` alone inverts the failure (IPv4 refused). One
        # socket with IPV6_V6ONLY off answers both, which is what the word
        # `localhost` means to a browser; a literal host still binds as
        # given.
        import socket
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(("::", args.port))
        sock.listen(128)
        config = uvicorn.Config(app, port=args.port)
        uvicorn.Server(config).run(sockets=[sock])
        return 0
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    sys.exit(main())
