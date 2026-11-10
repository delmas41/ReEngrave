"""The PAGE PASS of the labelling tool (ROADMAP 2.287): routes mounted on the existing server.

    GET  /page                         the page-pass view (static/pagepass.html + .js)
    GET  /api/pp/state                 meta, systems, every label, ink-claim numbers
    GET  /api/pp/render?x0&y0&x1&y1&w  the page's ink, tinted by claim state, for a region (PNG)
    POST /api/pp/label                 {kind, shape, text?, sub?}     draw a label (confirmed)
    POST /api/pp/label/<id>            {action: confirm|reject|delete|edit, ...}
    POST /api/pp/undo                  undo the last change
    GET  /api/cell/<cell_id>/claimed.png   PASS-1 ink claimed in this cell, as a transparent overlay
                                           the cell view lays over the cell image (the hand-off to pass 2)

READ-ONLY on the page: the PDF is rendered with the same ``render_page`` the cells are cut from
and only ever read. Writes go to ONE file, ``<page>.pagepass.json``, atomically, after every change.
Nothing under ``tools/omr/staged/`` is touched or imported.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from tools.omr.hand_truth import pagepass as pp
from tools.omr.hand_truth import pagepass_prefill, store
from tools.omr.hand_truth.pageink import (
    CELLPASS, CLAIMED, CONTESTED, PALETTE_RGB, PENDING, RULE_VERSION, STATE_NAMES, UNCLAIMED, Claims, InkMap,
    claimed_overlay_rgba, measure_sp, owned_overlay_rgba, render_states, staff_lines_from_cells,
)

_STATIC = Path(__file__).parent / "static"
UNDO_DEPTH = 60


def find_pdf(name: str) -> Optional[Path]:
    """The library PDF by file name: this checkout's library/, then the main checkout's (worktrees have none)."""
    import subprocess

    roots = [store.REPO / "library"]
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=store.REPO, capture_output=True,
                                text=True, check=True).stdout.strip()
        roots.append((store.REPO / common).resolve().parent / "library")
    except Exception:  # noqa: BLE001
        pass
    for r in roots:
        if r.exists():
            hit = next(iter(r.glob(f"**/{name}")), None)
            if hit:
                return hit
    return None


class PagePassService:
    def __init__(self, page_store: Path, pdf: Optional[Path] = None, pagepass_file: Optional[Path] = None,
                 arc_key: Optional[Path] = None):
        self.page_store = Path(page_store)
        self.truth = store.load(self.page_store)
        self.file = Path(pagepass_file) if pagepass_file else pp.pagepass_path(
            self.truth.edition, self.truth.pdf_page_index, self.page_store.parents[1])
        if pdf is None:
            name = self.truth.provenance.get("pdf")
            pdf = find_pdf(name) if name else None
        if pdf is None or not Path(pdf).exists():
            raise SystemExit("[page pass] no PDF: pass --pdf (the page is rendered from it, read-only)")
        self.pdf = Path(pdf)
        self.lock = threading.RLock()
        self.history: List[str] = []
        self._ink: Optional[InkMap] = None
        self._cellpass: Optional[np.ndarray] = None
        self._claims: Optional[Claims] = None
        if self.file.exists():
            self.page = pp.load(self.file)
        else:
            key = json.loads(Path(arc_key).read_text()) if arc_key else None
            # the ink lets a barline / bracket pre-fill join across cells only where the print is unbroken
            self.page = pagepass_prefill.build(self.truth, arc_key=key, ink=self.ink().ink)
            self.page.save(self.file)
            print(f"[page pass] new page-pass file with {len(self.page.labels)} pre-fills: {self.file}")

    # ------------------------------------------------------------ ink (built once, on first use)
    def ink(self) -> InkMap:
        with self.lock:
            if self._ink is None:
                from tools.omr.preprocessing import render_page

                print(f"[page pass] rendering {self.pdf.name} p{self.truth.pdf_page_index} at {self.truth.dpi} dpi ...")
                img = render_page(self.pdf, self.truth.pdf_page_index, dpi=self.truth.dpi)
                ink = img.binary < 128
                if ink.shape != (self.truth.height, self.truth.width):
                    raise HTTPException(500, detail=f"rendered page {ink.shape} is not the page file's "
                                                    f"{(self.truth.height, self.truth.width)}")
                lines = staff_lines_from_cells(self.truth.cells)
                self._ink = InkMap(ink, measure_sp(lines) or getattr(getattr(self, "page", None), "sp", 0.0), lines)
                rects = [b.rect for b in self.truth.boxes
                         if pp.kind_of_class(b.cls) is None and b.cls not in ("noise",)]
                self._cellpass = self._ink.cellpass_mask(rects)
                print(f"[page pass] ink ready: {int(ink.sum())} px, {len(rects)} cell-pass boxes")
            return self._ink

    def claims(self) -> Claims:
        with self.lock:
            ink = self.ink()
            if self._claims is None:
                self._claims = ink.claims(self.page.claimers(), self._cellpass)
                if not getattr(self, "_restamped", False):
                    # a file written under an older rule: re-derive every label's ink_ref (and a meter's digit
                    # pieces) in memory now; it reaches the disk with the next change, never at load
                    self._restamped = True
                    self._stamp_refs()
            return self._claims

    # ------------------------------------------------------------ mutation (snapshot -> change -> claims -> save)
    def mutate(self, fn) -> Dict:
        with self.lock:
            snap = json.dumps(self.page.to_json())
            try:
                out = fn(self.page)
            except store.StoreError as e:
                raise HTTPException(400, detail=str(e))
            self.history.append(snap)
            del self.history[:-UNDO_DEPTH]
            self._claims = None
            self._stamp_refs()
            self.page.save(self.file)
            return {"label": out.to_json() if out else None, **self.state_payload()}

    def undo(self) -> Dict:
        with self.lock:
            if not self.history:
                raise HTTPException(400, detail="nothing to undo")
            self.page = pp.PagePass.from_json(json.loads(self.history.pop()))
            self._claims = None
            self._stamp_refs()
            self.page.save(self.file)
            return self.state_payload()

    def _stamp_refs(self) -> None:
        """Derived data on every label: its ink_ref under the CURRENT rule, and a meter's digit pieces."""
        c = self.claims()
        ink = self.ink()
        for lab in self.page.labels:
            lab.ink_ref = c.refs.get(lab.id) if lab.state == "confirmed" else None
            if lab.kind == "meter" and lab.state == "confirmed" and lab.parts is None and lab.ink_ref \
                    and lab.ink_ref.get("bbox"):
                bbox, mask = ink.owned_mask(c, lab.id)
                lab.parts = ink.meter_parts(bbox, mask, lab.text) or None

    # ------------------------------------------------------------ payloads
    def systems(self) -> List[Dict]:
        by: Dict[int, List] = {}
        for c in self.truth.cells:
            if c.kind == "measure" and c.system is not None:
                by.setdefault(c.system, []).append(c.rect)
        sp = self.page.sp or 32.0
        out = []
        for s, rs in sorted(by.items()):
            out.append({"i": s, "rect": [0, max(0, min(r[1] for r in rs) - 2 * sp),
                                         self.truth.width, min(self.truth.height, max(r[3] for r in rs) + 2 * sp)]})
        return out

    def strips(self) -> List[Dict]:
        """One strip per staff, full page width: the working zoom (a one-system page, like a full score's, is
        too tall to label at 'fit system'). Rect = the staff's lines plus 4 spaces above and below."""
        sp = self.page.sp or 32.0
        by: Dict[tuple, List[float]] = {}
        for c in self.truth.cells:
            if c.kind == "measure" and c.staff_line_ys and c.system is not None and c.staff is not None:
                y0, y1 = c.rect[1], c.rect[3]
                sy = (y1 - y0) / c.canonical_h
                ys = [y0 + y * sy for y in c.staff_line_ys]
                lo, hi = by.setdefault((c.system, c.staff), [min(ys), max(ys)])
                by[(c.system, c.staff)] = [min(lo, min(ys)), max(hi, max(ys))]
        return [{"system": k[0], "staff": k[1],
                 "rect": [0, max(0, v[0] - 4 * sp), self.truth.width, min(self.truth.height, v[1] + 4 * sp)]}
                for k, v in sorted(by.items())]

    def state_payload(self) -> Dict:
        c = self.claims()
        covered = self.page.covered_prefills()
        labels = []
        for lab in self.page.labels:
            d = lab.to_json()
            d["px"] = c.px.get(lab.id)
            d["raw_px"] = c.raw_px.get(lab.id)
            d["lost_px"] = c.lost_px.get(lab.id, 0)
            d["lost_to"] = c.lost_to.get(lab.id, [])
            d["contested_px"] = c.contested_of.get(lab.id, 0)
            d["contested_with"] = c.contested_with.get(lab.id, [])
            d["cut"] = bool((c.refs.get(lab.id) or {}).get("cut"))
            if lab.id in covered:
                d["covered_by"] = covered[lab.id]
            labels.append(d)
        counts = {k: {"pending": 0, "confirmed": 0, "rejected": 0} for k in pp.KINDS}
        for lab in self.page.labels:
            if lab.id not in covered:           # a pre-fill a confirmed text block covers is not waiting for you
                counts[lab.kind][lab.state] += 1
        return {"meta": {"edition": self.truth.edition, "page": self.truth.pdf_page_index,
                         "width": self.truth.width, "height": self.truth.height, "dpi": self.truth.dpi,
                         "sp": self.page.sp, "systems": self.systems(), "strips": self.strips(), "kinds": list(pp.KINDS),
                         "text_kinds": list(pp.TEXT_KINDS), "word_blocks": list(pp.BLOCK_SUBS),
                         "file": str(self.file), "rule": RULE_VERSION,
                         "palette": {STATE_NAMES[k]: "#%02x%02x%02x" % PALETTE_RGB[k]
                                     for k in (UNCLAIMED, CLAIMED, PENDING, CELLPASS, CONTESTED)}},
                "labels": labels, "counts": counts, "covered": covered, "stats": c.summary()}


def mount(app, service: PagePassService) -> None:
    r = APIRouter()

    @r.get("/page", response_class=HTMLResponse)
    def page_view() -> HTMLResponse:
        return HTMLResponse((_STATIC / "pagepass.html").read_text())

    @r.get("/api/pp/state")
    def state() -> Dict:
        return service.state_payload()

    @r.get("/api/pp/render")
    def render(x0: float, y0: float, x1: float, y1: float, w: int = 1400) -> Response:
        ink = service.ink()
        c = service.claims()
        X0, Y0 = max(0, int(np.floor(x0))), max(0, int(np.floor(y0)))
        X1, Y1 = min(ink.w, int(np.ceil(x1))), min(ink.h, int(np.ceil(y1)))
        if X1 <= X0 or Y1 <= Y0:
            raise HTTPException(400, detail="empty region")
        code = ink.states(c, service._cellpass, (X0, Y0, X1, Y1))
        # the region may be clipped by the page edge: keep the client's scale
        out_w = max(1, int(round(w * (X1 - X0) / max(1e-6, x1 - x0))))
        img = render_states(code, out_w)
        ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        return Response(buf.tobytes(), media_type="image/png",
                        headers={"X-Region": f"{X0},{Y0},{X1},{Y1}", "Cache-Control": "no-store"})

    @r.get("/api/pp/owned/{label_id}")
    def owned(label_id: str, w: int = 0) -> Response:
        """EXACTLY the ink this label owns after precedence, as a transparent picture covering its bbox
        (+3 px of margin; X-Region says where). Hovering or selecting a label draws this: the answer to
        'where those two boxes overlap, how does it know which is which?'"""
        c = service.claims()
        if not any(l.id == label_id for l in c.labels):
            raise HTTPException(404, detail=f"no claiming label {label_id}")
        (x0, y0, x1, y1), mask = service.ink().owned_mask(c, label_id)
        if mask.size == 0:
            return Response(status_code=204, headers={"X-Region": "0,0,0,0", "Cache-Control": "no-store"})
        pad = 3
        mask = np.pad(mask, pad)
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
        rgba = owned_overlay_rgba(mask, max(1, min(int(w) or mask.shape[1], 4000)))
        ok, buf = cv2.imencode(".png", rgba, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        return Response(buf.tobytes(), media_type="image/png",
                        headers={"X-Region": f"{x0},{y0},{x1},{y1}", "Cache-Control": "no-store"})

    @r.post("/api/pp/label")
    async def draw(request: Request) -> Dict:
        b = await request.json()
        kind = b.get("kind")
        if kind not in pp.KINDS:
            raise HTTPException(400, detail=f"kind {kind!r} not in {pp.KINDS}")
        try:
            shape = pp.check_shape(b["shape"])
        except (store.StoreError, KeyError) as e:
            raise HTTPException(400, detail=str(e))
        return service.mutate(lambda p: p.draw(kind, shape, text=b.get("text"), sub=b.get("sub")))

    @r.post("/api/pp/label/{label_id}")
    async def act(label_id: str, request: Request) -> Dict:
        b = await request.json()
        a = b.get("action")
        if a == "confirm":
            return service.mutate(lambda p: p.confirm(label_id))
        if a == "reject":
            return service.mutate(lambda p: p.reject(label_id))
        if a == "delete":
            return service.mutate(lambda p: p.delete(label_id))
        if a == "edit":
            shape = pp.check_shape(b["shape"]) if b.get("shape") else None
            return service.mutate(lambda p: p.edit(label_id, kind=b.get("kind"), shape=shape,
                                                   text=b.get("text"), sub=b.get("sub")))
        raise HTTPException(400, detail=f"unknown action {a!r}")

    @r.post("/api/pp/undo")
    def undo() -> Dict:
        return service.undo()

    @r.get("/api/cell/{cell_id}/claimed.png")
    def cell_claimed(cell_id: str) -> Response:
        """Pass-1 ink (confirmed page-pass labels only) in this cell, transparent elsewhere."""
        try:
            cell = service.truth.cell(cell_id)
        except store.StoreError:
            raise HTTPException(404, detail=f"no cell {cell_id}")
        ink = service.ink()
        c = service.claims()
        rgba = claimed_overlay_rgba(c, None, ink.ink, cell.rect, cell.canonical_w, cell.canonical_h,
                                    states=(CLAIMED,))
        ok, buf = cv2.imencode(".png", rgba)
        return Response(buf.tobytes(), media_type="image/png", headers={"Cache-Control": "no-store"})

    app.include_router(r)
