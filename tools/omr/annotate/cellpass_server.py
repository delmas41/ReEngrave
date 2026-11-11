"""The CELL PASS of the labelling tool (ROADMAP 2.287 round 3): pass 2, mounted next to the page pass.

    GET  /cellpass                      the pass-2 view (static/cellpass.html + .js): one cell zoomed, a queue
    GET  /api/cp/state                  meta, every label, the cell queue (% of ink unclaimed), page totals
    GET  /api/cp/render?x0&y0&x1&y1&w   the page's ink tinted by state for a region (PNG)
    GET  /api/cp/owned/<id>             exactly the ink one label owns (hover / select)
    POST /api/cp/label                  {kind, cls?, shape, cell_id?}   draw a label (confirmed)
    POST /api/cp/label/<id>             {action: confirm|reject|delete|edit, ...}
    POST /api/cp/bulk                   {cell_id, kind}  confirm every waiting pre-fill of ONE kind in ONE cell
    POST /api/cp/undo                   undo the last change (a bulk confirm is one change)

NOTHING is built outside this process's memory: the cells are the page file's recorded cells, the picture is the
page render the page pass already makes. No bench directory, no detector. Writes go to ONE file,
``<page>.cellpass.json`` (see ``hand_truth.cellpass``); the page file and the page-pass file are only read.

Pass 1's ink is FINAL: pass-2 claims read ``free = ink - confirmed pass-1 ink`` (``hand_truth.cellink``).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from tools.omr.hand_truth import cellink
from tools.omr.hand_truth import cellpass as cpm
from tools.omr.hand_truth import pagepass as pp
from tools.omr.hand_truth import store
from tools.omr.hand_truth.pageink import PALETTE_RGB, CLAIMED, PENDING, UNCLAIMED, CELLPASS, owned_overlay_rgba

_STATIC = Path(__file__).parent / "static"
UNDO_DEPTH = 40
#: the pass-2 picture's states: BG, unclaimed, claimed in pass 1, under a waiting pre-fill, claimed in pass 2, noise
S_BG, S_UNCLAIMED, S_PAGE, S_PENDING, S_CELL, S_NOISE = range(6)
PALETTE = {S_BG: (255, 255, 255), S_UNCLAIMED: PALETTE_RGB[UNCLAIMED], S_PAGE: PALETTE_RGB[CLAIMED],
           S_PENDING: PALETTE_RGB[PENDING], S_CELL: PALETTE_RGB[CELLPASS], S_NOISE: (140, 140, 140)}
STATE_NAMES = {S_UNCLAIMED: "unclaimed", S_PAGE: "page pass", S_PENDING: "pre-fill", S_CELL: "cell pass",
               S_NOISE: "noise"}
#: a pre-fill is "mostly claimed by pass 1" when at least this share of the (non-staff) ink in its box is
AUTO_SHARE = 0.5
#: a cell with no more unclaimed ink than this (px) and nothing waiting counts as finished for Tab (a speck
#: under a label's own minimum cannot be claimed by shape; mark it noise to bring the page to zero)
DONE_PX = 0


def _classes_by_kind() -> Dict[str, List[str]]:
    raw = json.loads((Path(__file__).parents[1] / "training" / "deepscoresv2_208_classes.json").read_text())
    extra = ["barlineSingle", "noise"]
    out: Dict[str, List[str]] = {k: [] for k in cpm.KINDS}
    for c in dict.fromkeys(list(raw) + extra):
        k = cpm.cell_kind_of_class(c)
        if k and c not in out[k]:
            out[k].append(c)
    out["noise"] = ["noise"]
    out["staffedge"] = ["staffedge"]
    # the classes Sean's old boxes use come first
    pref = {"notehead": ["noteheadBlackOnLine", "noteheadBlackInSpace", "noteheadHalfOnLine", "noteheadHalfInSpace",
                         "noteheadWholeOnLine", "noteheadWholeInSpace"],
            "dot": ["augmentationDot"], "ledger": ["ledgerLine"]}
    for k, first in pref.items():
        out[k] = [c for c in first if c in out[k]] + [c for c in out[k] if c not in first]
    return out


class CellPassService:
    def __init__(self, page_service, cellpass_file: Optional[Path] = None):
        self.ps = page_service
        self.truth = page_service.truth
        self.file = Path(cellpass_file) if cellpass_file else cpm.cellpass_path(
            self.truth.edition, self.truth.pdf_page_index, page_service.page_store.parents[1])
        self.lock = page_service.lock
        self.history: List[str] = []
        self.classes = _classes_by_kind()
        self.prefill_counts: Dict = {}
        if self.file.exists():
            self.cp = cpm.load(self.file)
        else:
            self.cp, self.prefill_counts = cpm.build(self.truth)
            self.cp.save(self.file)
            print(f"[cell pass] new cell-pass file: {self.prefill_counts['imported']} pre-fills from your old boxes, "
                  f"{self.prefill_counts['dropped_page_wide']} page-wide boxes dropped (pass 1 superseded them), "
                  f"{self.prefill_counts['staff_edge']} staff-edge strips: {self.file}")
        self._src = None
        self._ci: Optional[cellink.CellInk] = None
        self._p1: Optional[np.ndarray] = None
        self._auto: Optional[Dict[str, int]] = None
        self._claims = None

    # ------------------------------------------------------------ pass 1's ink, and the free ink
    def sync(self) -> None:
        """(Re)build the free ink when pass 1 changed (or on first use). Pass 1 is only read."""
        with self.lock:
            pc = self.ps.claims()
            if pc is self._src:
                return
            ink = self.ps.ink()
            lut = np.zeros(len(pc.labels) + 1, bool)
            for i, lab in enumerate(pc.labels):
                lut[i + 1] = lab.state == "confirmed"
            self._p1 = lut[pc.owner] & ink.ink
            free = ink.ink & ~self._p1
            print(f"[cell pass] splitting {int(free.sum())} px of unclaimed ink into heads, stems, ledger lines ...")
            self._ci = cellink.CellInk(free, ink.sp, ink.line, ink.line_thickness, ink.hb)
            self._src, self._auto, self._claims = pc, None, None

    def ci(self) -> cellink.CellInk:
        self.sync()
        return self._ci

    def p1(self) -> np.ndarray:
        self.sync()
        return self._p1

    def auto(self) -> Dict[str, int]:
        """Pending pre-fills whose ink pass 1 already claimed (>= AUTO_SHARE of the ink in the box): id -> percent.
        Derived, never written: they need no answer."""
        with self.lock:
            self.sync()
            if self._auto is None:
                rest = self.ps.ink().rest
                p1 = self._p1
                out: Dict[str, int] = {}
                for lab in self.cp.labels:
                    if lab.state != "pending" or lab.source == "staff-edge":
                        continue
                    x0, y0, x1, y1 = pp.shape_bbox(lab.shape)
                    sl = (slice(max(0, int(y0)), min(rest.shape[0], int(y1) + 1)),
                          slice(max(0, int(x0)), min(rest.shape[1], int(x1) + 1)))
                    r = rest[sl]
                    tot = int(r.sum())
                    if tot and int((p1[sl] & r).sum()) >= AUTO_SHARE * tot:
                        out[lab.id] = int(round(100.0 * int((p1[sl] & r).sum()) / tot))
                self._auto = out
            return self._auto

    # ------------------------------------------------------------ the claims of pass 2
    def claims(self):
        with self.lock:
            ci = self.ci()
            if self._claims is not None:
                return self._claims
            auto = self.auto()
            labs = [lab for lab in self.cp.claimers() if lab.id not in auto]
            areas = [pp.shape_area(lab.shape) for lab in labs]
            order = sorted(range(len(labs)), key=lambda i: (labs[i].state != "confirmed", areas[i], labs[i].id))
            if len(labs) >= 32000:
                raise HTTPException(500, detail="too many labels for the claim map")
            owner = np.zeros(ci.free.shape, np.int16)
            px: Dict[str, int] = {}
            raw: Dict[str, int] = {}
            refs: Dict[str, Dict] = {}
            lost: Dict[str, int] = {}
            for i in order:
                lab = labs[i]
                c = ci.claim(lab.shape, lab.kind)
                raw[lab.id] = c.px
                px[lab.id] = 0
                if c.mask.size == 0:
                    continue
                x0, y0, x1, y1 = c.bbox
                reg = owner[y0:y1, x0:x1]
                take = c.mask & (reg == 0)
                reg[take] = i + 1
                px[lab.id] = int(take.sum())
                lost[lab.id] = int((c.mask & (reg != 0)).sum()) - px[lab.id]
            for i, lab in enumerate(labs):
                if lab.state == "confirmed" and px.get(lab.id):
                    c = ci.claim(lab.shape, lab.kind)
                    x0, y0, x1, y1 = c.bbox
                    refs[lab.id] = cellink.ink_ref(lab.kind, c, owner[y0:y1, x0:x1] == i + 1)
            self._claims = {"owner": owner, "labels": labs, "px": px, "raw": raw, "refs": refs, "lost": lost}
            return self._claims

    # ------------------------------------------------------------ mutation (snapshot -> change -> claims -> save)
    def mutate(self, fn) -> Dict:
        with self.lock:
            snap = json.dumps(self.cp.to_json())
            try:
                out = fn(self.cp)
            except store.StoreError as e:
                raise HTTPException(400, detail=str(e))
            self.history.append(snap)
            del self.history[:-UNDO_DEPTH]
            self._claims = None
            self._auto = None
            self._stamp()
            self.cp.save(self.file)
            return {"label": out.to_json() if out is not None and not isinstance(out, list) else None,
                    **self.state_payload()}

    def undo(self) -> Dict:
        with self.lock:
            if not self.history:
                raise HTTPException(400, detail="nothing to undo")
            self.cp = cpm.CellPass.from_json(json.loads(self.history.pop()))
            self._claims = None
            self._auto = None
            self._stamp()
            self.cp.save(self.file)
            return self.state_payload()

    def _stamp(self) -> None:
        c = self.claims()
        for lab in self.cp.labels:
            lab.ink_ref = c["refs"].get(lab.id) if lab.state == "confirmed" else None

    # ------------------------------------------------------------ payloads
    def _state_lut(self, labs) -> np.ndarray:
        lut = np.zeros(len(labs) + 1, np.uint8)
        for i, lab in enumerate(labs):
            lut[i + 1] = (S_NOISE if lab.kind == "noise" else S_CELL) if lab.state == "confirmed" else S_PENDING
        return lut

    def done_mask(self) -> np.ndarray:
        """Ink claimed by pass 1 or by a CONFIRMED pass-2 label (noise included)."""
        c = self.claims()
        if "conf" not in c:
            conf = np.zeros(len(c["labels"]) + 1, bool)
            for i, lab in enumerate(c["labels"]):
                conf[i + 1] = lab.state == "confirmed"
            c["conf"] = conf[c["owner"]]
        return self._p1 | c["conf"]

    def roles_unclaimed(self) -> Dict[str, int]:
        """Unclaimed ink (not yet claimed by a confirmed label of either pass) by the role the shape rule gave it."""
        un = self._ci.free & ~self.done_mask()
        return {r: int((un & (self._ci.role == cellink.ROLE_ID[r])).sum()) for r in cellink.ROLES}

    def cells(self, done: np.ndarray) -> List[Dict]:
        ink = self.ps.ink().ink
        auto = self.auto()
        waiting: Dict[str, int] = {}
        c = self.claims()
        for lab in self.cp.labels:
            if lab.state == "pending" and lab.id not in auto and c["px"].get(lab.id, 0) > 0:
                waiting[lab.cell_id or ""] = waiting.get(lab.cell_id or "", 0) + 1
        rows = []
        for cell in self.truth.cells:
            x0, y0, x1, y1 = (int(round(v)) for v in cell.rect)
            sl = (slice(max(0, y0), min(ink.shape[0], y1)), slice(max(0, x0), min(ink.shape[1], x1)))
            tot = int(ink[sl].sum())
            un = int((ink[sl] & ~done[sl]).sum())
            rows.append({"id": cell.id, "kind": cell.kind, "system": cell.system, "staff": cell.staff,
                         "measure": cell.measure, "rect": [x0, y0, x1, y1], "ink_px": tot, "unclaimed_px": un,
                         "pct": round(100.0 * un / tot, 1) if tot else 0.0, "waiting": waiting.get(cell.id, 0)})
        # top-left to bottom-right: a staff's cells together, staves top to bottom, a staff left to right
        ymean: Dict = {}
        for r in rows:
            if r["kind"] == "measure":
                ymean.setdefault((r["system"], r["staff"]), []).append(r["rect"][1])
        for r in rows:
            r["_y"] = float(np.mean(ymean[(r["system"], r["staff"])])) if r["kind"] == "measure" else float(r["rect"][1])
        rows.sort(key=lambda r: (r["_y"], r["rect"][0], r["id"]))
        for i, r in enumerate(rows):
            r["order"] = i
            del r["_y"]
        return rows

    def state_payload(self) -> Dict:
        c = self.claims()
        auto = self.auto()
        ink = self.ps.ink().ink
        done = self.done_mask()
        tot = int(ink.sum())
        # totals from the labels' own pixel counts (every claimed pixel is free ink, owned by exactly one label)
        p1px = int(self._p1.sum())
        p2px = noise_px = under_pending = 0
        for lab in c["labels"]:
            n = c["px"].get(lab.id) or 0
            if lab.state == "pending":
                under_pending += n
            elif lab.kind == "noise":
                noise_px += n
            else:
                p2px += n
        free_px = int(self._ci.free.sum())
        cells = self.cells(done)
        out_labels = []
        n_pending = n_confirmed = n_auto = n_empty = n_covered = 0
        for lab in self.cp.labels:
            d = lab.to_json()
            d["px"] = c["px"].get(lab.id)
            d["ink_ref"] = c["refs"].get(lab.id) if lab.state == "confirmed" else None
            d["raw_px"] = c["raw"].get(lab.id)
            if lab.id in auto:
                d["auto_pct"] = auto[lab.id]
            if lab.state == "pending" and lab.id not in auto and (c["raw"].get(lab.id) or 0) == 0:
                d["empty"] = True
            elif lab.state == "pending" and lab.id not in auto and (c["px"].get(lab.id) or 0) == 0:
                d["covered"] = True          # its ink is already owned by a confirmed label (a twin from the next cell)
            out_labels.append(d)
            if lab.state == "pending":
                if lab.id in auto:
                    n_auto += 1
                elif d.get("empty"):
                    n_empty += 1
                elif d.get("covered"):
                    n_covered += 1
                else:
                    n_pending += 1
            elif lab.state == "confirmed":
                n_confirmed += 1
        un_px = free_px - p2px - noise_px
        return {
            "meta": {"edition": self.truth.edition, "page": self.truth.pdf_page_index, "width": self.truth.width,
                     "height": self.truth.height, "dpi": self.truth.dpi, "sp": self.cp.sp, "file": str(self.file),
                     "rule": cellink.RULE_VERSION, "kinds": list(cpm.KINDS), "classes": self.classes,
                     "palette": {STATE_NAMES[k]: "#%02x%02x%02x" % PALETTE[k]
                                 for k in (S_UNCLAIMED, S_PAGE, S_PENDING, S_CELL, S_NOISE)}},
            "labels": out_labels, "cells": cells,
            "totals": {"ink_px": tot, "page_px": p1px, "cell_px": p2px, "noise_px": noise_px,
                       "under_prefill_px": under_pending, "unclaimed_px": un_px,
                       "page_pct": 100.0 * p1px / max(1, tot), "cell_pct": 100.0 * p2px / max(1, tot),
                       "noise_pct": 100.0 * noise_px / max(1, tot), "unclaimed_pct": 100.0 * un_px / max(1, tot),
                       "under_prefill_pct": 100.0 * under_pending / max(1, tot),
                       "done": un_px == 0 and n_pending == 0,
                       "confirmed": n_confirmed, "pending": n_pending, "auto_resolved": n_auto, "empty": n_empty, "covered": n_covered,
                       "cells_left": sum(1 for r in cells if r["unclaimed_px"] > DONE_PX or r["waiting"])},
        }

    # ------------------------------------------------------------ bulk
    def bulk_ids(self, cell_id: str, kind: str) -> Dict:
        """The pending pre-fills of ONE kind proposed in ONE cell that a bulk confirm may take: not resolved by
        pass 1, and claiming some ink. Empty ones are reported, never confirmed."""
        if kind not in cpm.KINDS:
            raise HTTPException(400, detail=f"kind {kind!r}")
        c = self.claims()
        auto = self.auto()
        ids, empty = [], []
        for lab in self.cp.labels:
            if lab.state != "pending" or lab.kind != kind or lab.cell_id != cell_id or lab.id in auto:
                continue
            if (c["px"].get(lab.id) or 0) > 0:
                ids.append(lab.id)
            elif (c["raw"].get(lab.id) or 0) == 0:
                empty.append(lab.id)           # claims no ink: reported, never confirmed
            # else: its ink is already owned by a confirmed label (a twin): nothing to confirm
        return {"ids": ids, "empty": empty}


def _render_png(code: np.ndarray, out_w: int) -> bytes:
    h, w = code.shape
    pal = np.zeros((6, 3), np.uint8)
    for k, (r, g, b) in PALETTE.items():
        pal[k] = (b, g, r)
    img = pal[code]
    scale = out_w / float(w)
    out_h = max(1, int(round(h * scale)))
    if scale >= 1.0:
        img = cv2.resize(img, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
    else:
        small = cv2.resize(img, (out_w, out_h), interpolation=cv2.INTER_AREA).astype(np.float32)
        gain = min(6.0, max(1.0, 0.35 / scale))
        img = np.clip(255.0 - (255.0 - small) * gain, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 1])
    return buf.tobytes()


def mount(app, service: CellPassService) -> None:
    r = APIRouter()

    @r.get("/cellpass", response_class=HTMLResponse)
    def cell_view() -> HTMLResponse:
        return HTMLResponse((_STATIC / "cellpass.html").read_text())

    @r.get("/api/cp/state")
    def state() -> Dict:
        with service.lock:
            return service.state_payload()

    @r.get("/api/cp/roles")
    def roles() -> Dict:
        """Unclaimed ink by the role the shape rule gave it (for a lane report; not in the UI)."""
        with service.lock:
            return service.roles_unclaimed()

    @r.get("/api/cp/render")
    def render(x0: float, y0: float, x1: float, y1: float, w: int = 1400) -> Response:
        c = service.claims()
        ink = service.ps.ink().ink
        H, W = ink.shape
        X0, Y0 = max(0, int(np.floor(x0))), max(0, int(np.floor(y0)))
        X1, Y1 = min(W, int(np.ceil(x1))), min(H, int(np.ceil(y1)))
        if X1 <= X0 or Y1 <= Y0:
            raise HTTPException(400, detail="empty region")
        sl = (slice(Y0, Y1), slice(X0, X1))
        im = ink[sl]
        code = np.where(im, S_UNCLAIMED, S_BG).astype(np.uint8)
        code[im & service._p1[sl]] = S_PAGE
        ow = c["owner"][sl]
        lut = service._state_lut(c["labels"])
        m = im & (ow > 0) & ~service._p1[sl]
        code[m] = lut[ow][m]
        out_w = max(1, int(round(w * (X1 - X0) / max(1e-6, x1 - x0))))
        return Response(_render_png(code, out_w), media_type="image/png",
                        headers={"X-Region": f"{X0},{Y0},{X1},{Y1}", "Cache-Control": "no-store"})

    @r.get("/api/cp/owned/{label_id}")
    def owned(label_id: str, w: int = 0) -> Response:
        c = service.claims()
        idx = next((i for i, lab in enumerate(c["labels"]) if lab.id == label_id), None)
        if idx is None:
            raise HTTPException(404, detail=f"no claiming label {label_id}")
        lab = c["labels"][idx]
        cl = service.ci().claim(lab.shape, lab.kind)
        if cl.mask.size == 0:
            return Response(status_code=204, headers={"X-Region": "0,0,0,0", "Cache-Control": "no-store"})
        x0, y0, x1, y1 = cl.bbox
        mask = (c["owner"][y0:y1, x0:x1] == idx + 1)
        if not mask.any():
            return Response(status_code=204, headers={"X-Region": "0,0,0,0", "Cache-Control": "no-store"})
        pad = 3
        mask = np.pad(mask, pad)
        rgba = owned_overlay_rgba(mask, max(1, min(int(w) or mask.shape[1], 4000)))
        ok, buf = cv2.imencode(".png", rgba, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        return Response(buf.tobytes(), media_type="image/png",
                        headers={"X-Region": f"{x0 - pad},{y0 - pad},{x1 + pad},{y1 + pad}", "Cache-Control": "no-store"})

    @r.post("/api/cp/label")
    async def draw(request: Request) -> Dict:
        b = await request.json()
        kind = b.get("kind")
        if kind not in cpm.KINDS:
            raise HTTPException(400, detail=f"kind {kind!r} not in {cpm.KINDS}")
        try:
            shape = pp.check_shape(b["shape"])
        except (store.StoreError, KeyError) as e:
            raise HTTPException(400, detail=str(e))
        return service.mutate(lambda p: p.draw(kind, b.get("cls"), shape, cell_id=b.get("cell_id")))

    @r.post("/api/cp/label/{label_id}")
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
            return service.mutate(lambda p: p.edit(label_id, kind=b.get("kind"), cls=b.get("cls"), shape=shape))
        raise HTTPException(400, detail=f"unknown action {a!r}")

    @r.post("/api/cp/bulk")
    async def bulk(request: Request) -> Dict:
        b = await request.json()
        sel = service.bulk_ids(b.get("cell_id", ""), b.get("kind", ""))
        if not sel["ids"]:
            raise HTTPException(400, detail="nothing waiting of that kind in this cell" +
                                            (f" ({len(sel['empty'])} claim no ink)" if sel["empty"] else ""))
        out = service.mutate(lambda p: p.bulk_confirm(sel["ids"]))
        out["bulk"] = {"confirmed": len(sel["ids"]), "skipped_empty": len(sel["empty"]), "kind": b.get("kind"),
                       "cell_id": b.get("cell_id")}
        return out

    @r.post("/api/cp/undo")
    def undo() -> Dict:
        return service.undo()

    app.include_router(r)
