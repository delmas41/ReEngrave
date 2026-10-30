"""ROADMAP 2.231 -- a MASTER CELL MAP: the cells a gather reads, frozen per page, so two arms read the same cells.

STAGED. Sean, 2026-10-29: *"Is there a master version of each cell - in case multiple passes are needed and so that
our test runs are using the same cell/tiles?"* Cells are cut fresh in every gather (`pipeline.prepare_pages`: render
-> `detect_staves` -> page-wide barlines -> `extract_measures` -> `remove_staff_lines`), so any upstream change moves
them, and an A/B arm can compare different cells (2.221 m2 moved a Litolff p9 cell 1526->1470 px and a crop-sensitive
0.07 detector rescue flipped).

WHAT A MASTER HOLDS (per pdf + dpi, one gzip JSON per page, machine-local under
`library/_shared-records/cell-maps/`): everything `prepare_pages` leaves on the page EXCEPT pixels -- every Staff
(line_ys, x extent, system/group index, line thickness, wander), every Barline (x, span, system, the vote record),
the page's own extras (`system_structure` = the page-wide pass's barline COLUMNS with each column's staves,
`deletion_counts`, `staged_page_wide`), every cell's scalars (page/system/staff/measure index, `bbox_page_px`,
`staff_line_ys_canonical`, upscale, pads, the localized-grid record) -- plus a sha256 of every pixel array
(the page render, the page binary, each cell's image / image_no_staff / binary). A cell is ~6 MB of pixels and a
Litolff page has 300, so pixels are not stored: they are RE-CUT from the stored geometry by the same
`measure_extractor._build_measure_cell` + `staff_line_removal.remove_staff_lines` and then PROVED equal to the
stored hashes.

LOADING NEVER RE-DETECTS. `load_prepared` renders the page, checks the render's hashes, rebuilds the PageWithStaves
from the master (no `detect_staves`, no `detect_barlines`), cuts each stored cell at its stored box, and compares
the whole page snapshot (every scalar and every pixel hash) with the master. ANY difference -- pdf hash, dpi, a page
the master lacks, a render that differs, a cell that cuts to other pixels (the cutting code changed) -- RAISES
`CellMapError`. It never falls back to re-cutting (CLAUDE rule 8): a lane that changes the cutting itself is not a
lane that can load a master; it lists what it moved (`moved`) instead.

    python3 -m tools.omr.staged.cell_map build PDF --pages 1-16 [--root DIR] [--force]
    python3 -m tools.omr.staged.cell_map verify PDF --pages 9,10 [--root DIR]      # fresh cut == master, or exit 1
    python3 -m tools.omr.staged.cell_map moved PDF --pages 9 [--root DIR] [--json OUT]
    python3 -m tools.omr.staged.cell_map against-record PDF REC.record.json [--root DIR]
    python3 -m tools.omr.staged.cell_map show PDF [--root DIR]

and a gather loads it with `python3 -m tools.omr.staged PDF --pages ... --cell-map DIR` (or `lane_report
--cell-map DIR`). DIR is the root (the pdf's master is found by its sha256) or one master's own directory.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
SCHEMA = "reengrave-cell-map/1"
ROOT_DEFAULT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/cell-maps")
#: The pixel arrays of a cell, hashed not stored. `binary` is the side-channel `_build_measure_cell` leaves.
CELL_ARRAYS = ("image", "image_no_staff", "binary")
PAGE_ARRAYS = ("rgb", "binary")
#: PageImage / PageWithStaves members that are not geometry (`pdf_path` is the caller's own path).
_PAGE_SKIP = ("pdf_path",) + PAGE_ARRAYS
_PWS_SKIP = ("page", "staves", "barlines")


class CellMapError(RuntimeError):
    """A master that does not describe what was asked for. Never swallowed, never re-cut around."""


# ───────────────────────────── 1. a lossless JSON spelling ─────────────────────────────

def enc(v: Any) -> Any:
    """Plain JSON loses tuples and int dict keys; this spelling keeps both, so decode(enc(x)) == x exactly."""
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (np.bool_,)):
        return {"$np": "bool_", "v": bool(v)}
    if isinstance(v, np.integer):
        return {"$np": v.dtype.name, "v": int(v)}
    if isinstance(v, np.floating):
        return {"$np": v.dtype.name, "v": float(v)}
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, tuple):
        return {"$t": [enc(x) for x in v]}
    if isinstance(v, list):
        return [enc(x) for x in v]
    if isinstance(v, dict):
        if all(isinstance(k, str) and not k.startswith("$") for k in v):
            return {k: enc(x) for k, x in v.items()}
        return {"$d": [[enc(k), enc(x)] for k, x in v.items()]}
    if isinstance(v, np.ndarray):
        return {"$a": digest(v)}
    if isinstance(v, pathlib.PurePath):
        return {"$path": str(v)}
    if dataclasses.is_dataclass(v):
        return {"$obj": type(v).__name__, "v": enc(dict(vars(v)))}
    raise CellMapError("cell map cannot spell a %s (%r)" % (type(v).__name__, v))


def dec(v: Any) -> Any:
    if isinstance(v, list):
        return [dec(x) for x in v]
    if not isinstance(v, dict):
        return v
    if "$t" in v:
        return tuple(dec(x) for x in v["$t"])
    if "$d" in v:
        return {dec(k): dec(x) for k, x in v["$d"]}
    if "$np" in v:
        return getattr(np, v["$np"])(v["v"])
    if "$path" in v:
        return pathlib.Path(v["$path"])
    if "$a" in v or "$obj" in v:
        raise CellMapError("a hashed array / object cannot be decoded back into a value: %r" % (v,))
    return {k: dec(x) for k, x in v.items()}


def digest(a: np.ndarray) -> str:
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(("%s|%s|" % (a.dtype.str, a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _canon(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()


def sha256_file(path: Any) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ───────────────────────────── 2. a page's snapshot ─────────────────────────────

def _members(o: Any, skip: Sequence[str] = ()) -> Dict[str, Any]:
    return {k: v for k, v in vars(o).items() if k not in skip}


def snapshot_page(pws: Any, cells: Sequence[Any]) -> Dict[str, Any]:
    """Everything `prepare_pages` produced for one page, as a JSON value: geometry spelled out, pixels hashed.

    The same function describes a fresh cut and a loaded one, so "loaded == fresh" is one `==` on two snapshots."""
    page = pws.page
    snap: Dict[str, Any] = {
        "page_index": int(page.page_index),
        "page": enc(_members(page, _PAGE_SKIP)),
        "page_arrays": {k: digest(getattr(page, k)) for k in PAGE_ARRAYS},
        "page_shape": list(page.rgb.shape),
        "pws": enc(_members(pws, _PWS_SKIP)),
        "staves": [enc(_members(s)) for s in pws.staves],
        "barlines": [enc(_members(b)) for b in pws.barlines],
        "cells": [],
    }
    for c in cells:
        arrays = {}
        for k in CELL_ARRAYS:
            a = getattr(c, k, None)
            arrays[k] = None if a is None else digest(a)
        snap["cells"].append({"v": enc(_members(c, CELL_ARRAYS)), "arrays": arrays})
    snap["geometry_hash"] = geometry_hash(snap)
    return snap


def geometry_hash(snap: Dict[str, Any]) -> str:
    body = {k: v for k, v in snap.items() if k != "geometry_hash"}
    return hashlib.sha256(_canon(body)).hexdigest()


def first_difference(a: Any, b: Any, path: str = "") -> Optional[str]:
    """The first place two snapshots differ, as a readable path, or None."""
    if type(a) != type(b):
        return "%s: %r -> %r" % (path or "/", a, b)
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return "%s/%s: %s" % (path, k, "only in master" if k in a else "only in the new cut")
            d = first_difference(a[k], b[k], "%s/%s" % (path, k))
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return "%s: %d items -> %d" % (path or "/", len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, "%s[%d]" % (path, i))
            if d:
                return d
        return None
    return None if a == b else "%s: %r -> %r" % (path or "/", a, b)


# ───────────────────────────── 3. where a master lives ─────────────────────────────

def master_dir(root: Any, pdf_sha: str, dpi: int) -> pathlib.Path:
    """`root` may already be one master's own directory (it has a manifest.json)."""
    root = pathlib.Path(root)
    if (root / "manifest.json").exists():
        return root
    return root / ("%s-dpi%d" % (pdf_sha[:16], dpi))


def _page_file(mdir: pathlib.Path, page: int) -> pathlib.Path:
    return mdir / "pages" / ("p%03d.json.gz" % page)


def read_manifest(mdir: pathlib.Path) -> Dict[str, Any]:
    mf = mdir / "manifest.json"
    if not mf.exists():
        raise CellMapError("no cell map at %s (build one: python3 -m tools.omr.staged.cell_map build PDF --pages ...)"
                           % mdir)
    m = json.loads(mf.read_text())
    if m.get("schema") != SCHEMA:
        raise CellMapError("%s: schema %r, this code reads %r" % (mf, m.get("schema"), SCHEMA))
    return m


def read_page(mdir: pathlib.Path, page: int) -> Dict[str, Any]:
    f = _page_file(mdir, page)
    if not f.exists():
        raise CellMapError("cell map %s has no page %d" % (mdir, page))
    snap = json.loads(gzip.decompress(f.read_bytes()))
    if geometry_hash(snap) != snap.get("geometry_hash"):
        raise CellMapError("cell map %s page %d: stored geometry hash does not match its content (edited or corrupt)"
                           % (mdir, page))
    return snap


def version_tag(pdf_sha: str, dpi: int, page_hashes: Dict[str, str]) -> str:
    """Names the CELLS, not the tree: pdf + dpi + every page's geometry hash. Two masters with one tag cut the same."""
    body = {"pdf": pdf_sha, "dpi": dpi, "pages": dict(sorted(page_hashes.items(), key=lambda kv: int(kv[0])))}
    return "cm-" + hashlib.sha256(_canon(body)).hexdigest()[:12]


def _git(*args: str) -> Optional[str]:
    try:
        return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL,
                                       cwd=str(pathlib.Path(__file__).resolve().parent)).decode().strip()
    except Exception:                                                   # noqa: BLE001
        return None


def cutting_sources() -> Dict[str, str]:
    """sha256 of every tools/omr source file loaded at the time of the call -- DERIVED from `sys.modules` after a cut
    (never a hand list), so a builder records exactly the code that cut. Call it after `prepare_pages` has run."""
    base = pathlib.Path(__file__).resolve().parents[1]
    out: Dict[str, str] = {}
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = pathlib.Path(f).resolve()
        try:
            rel = p.relative_to(base)
        except ValueError:
            continue
        if p.suffix == ".py" and p.exists():
            out[str(rel)] = sha256_file(p)
    return dict(sorted(out.items()))


# ───────────────────────────── 4. build ─────────────────────────────

def build(pdf_path: Any, pages: Sequence[int], *, dpi: int = 600, root: Any = ROOT_DEFAULT, force: bool = False,
          prepared: Optional[Sequence[Tuple[Any, Sequence[Any]]]] = None, progress: bool = False) -> Dict[str, Any]:
    """Cut `pages` with THIS tree's `prepare_pages` and write (or extend) the pdf's master. A page already in the
    master that cuts differently is refused unless `force` (a master is rebuilt only deliberately)."""
    from . import pipeline
    pdf_sha = sha256_file(pdf_path)
    mdir = master_dir(root, pdf_sha, dpi)
    if (mdir / "manifest.json").exists():
        man = read_manifest(mdir)
        if man["pdf_sha256"] != pdf_sha or int(man["dpi"]) != dpi:
            raise CellMapError("%s is a master for another pdf/dpi (%s dpi %s)" % (mdir, man["pdf_sha256"][:12], man["dpi"]))
    else:
        man = {"schema": SCHEMA, "pdf_name": pathlib.Path(pdf_path).name, "pdf_sha256": pdf_sha, "dpi": dpi,
               "pages": {}, "built": {}}
    (mdir / "pages").mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pages):
        if prepared is not None:
            pws, cells = prepared[i]
        else:
            [(pws, cells)] = pipeline.prepare_pages(str(pdf_path), [p], dpi=dpi)
        if int(pws.page.page_index) != int(p):
            raise CellMapError("prepared page %s is not page %s" % (pws.page.page_index, p))
        snap = snapshot_page(pws, cells)
        old = man["pages"].get(str(p))
        if old and old != snap["geometry_hash"] and not force:
            d = first_difference(read_page(mdir, p), snap)
            raise CellMapError("page %d is already in %s and this tree cuts it differently (%s); rebuild only "
                               "deliberately (--force)" % (p, mdir, d))
        _page_file(mdir, p).write_bytes(gzip.compress(_canon(snap), 6))
        man["pages"][str(p)] = snap["geometry_hash"]
        if progress:
            print("  page %d: %d staves, %d barlines, %d cells, %s" % (p, len(snap["staves"]), len(snap["barlines"]),
                                                                       len(snap["cells"]), snap["geometry_hash"][:12]),
                  flush=True)
    commit, dirty = _git("rev-parse", "HEAD"), _git("status", "--porcelain", "--untracked-files=no")
    man["built"] = {"commit": commit, "dirty": None if dirty is None else bool(dirty),
                    "date": datetime.datetime.now().isoformat(timespec="seconds"),
                    "cutting_sources": cutting_sources(),
                    "env_overrides": {k: v for k, v in sorted(os.environ.items()) if k.startswith("OMR_")}}
    man["version"] = version_tag(pdf_sha, dpi, man["pages"])
    (mdir / "manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    return man


# ───────────────────────────── 5. load ─────────────────────────────

def _construct(cls: Any, members: Dict[str, Any]) -> Any:
    """A dataclass from its stored members: fields through the constructor, the rest (side-channel attributes) set."""
    names = {f.name for f in dataclasses.fields(cls) if f.init}
    obj = cls(**{k: v for k, v in members.items() if k in names})
    for k, v in members.items():
        if k not in names:
            obj.__dict__[k] = v
    return obj


def _rebuild_page(pdf_path: Any, page: int, dpi: int, snap: Dict[str, Any]) -> Tuple[Any, List[Any]]:
    from ..preprocessing import render_page
    from ..types import Barline, PageWithStaves, Staff
    from ..measure_extractor import _build_measure_cell
    from ..staff_line_removal import remove_staff_lines

    img = render_page(str(pdf_path), page, dpi=dpi)
    got = {k: digest(getattr(img, k)) for k in PAGE_ARRAYS}
    if got != snap["page_arrays"]:
        raise CellMapError("page %d renders to other pixels than the master's (render or pdf changed): %s"
                           % (page, first_difference(snap["page_arrays"], got)))
    for k, v in dec(snap["page"]).items():
        setattr(img, k, v)
    staves = [_construct(Staff, dec(s)) for s in snap["staves"]]
    barlines = [_construct(Barline, dec(b)) for b in snap["barlines"]]
    pws = PageWithStaves(page=img, staves=staves, barlines=barlines)
    extras = dec(snap["pws"])
    by_staff = {s.staff_index: s for s in staves}
    cells: List[Any] = []
    for c in snap["cells"]:
        v = dec(c["v"])
        st = by_staff.get(v["staff_index"])
        if st is None:
            raise CellMapError("page %d: a master cell names staff %s, which the master does not hold"
                               % (page, v["staff_index"]))
        x0, _y0, x1, _y1 = v["bbox_page_px"]
        cell = _build_measure_cell(pws, st, v["system_index"], int(x0), int(x1), v["measure_index"])
        if cell is None:
            raise CellMapError("page %d: master cell %s cuts to nothing on this tree" % (page, v["bbox_page_px"]))
        cells.append(cell)
    remove_staff_lines(cells)
    # The page's own members LAST: `_build_measure_cell` bumps `deletion_counts` only for a cell it drops, and the
    # master holds the counts the original `extract_measures` left.
    for k, val in extras.items():
        setattr(pws, k, val)
    return pws, cells


def load_prepared(pdf_path: Any, pages: Sequence[int], *, dpi: int = 600, root: Any = ROOT_DEFAULT
                  ) -> List[Tuple[Any, List[Any]]]:
    """`prepare_pages`' return value, from the master. Raises `CellMapError` on any mismatch -- never re-cuts."""
    pdf_sha = sha256_file(pdf_path)
    mdir = master_dir(root, pdf_sha, dpi)
    man = read_manifest(mdir)
    if man["pdf_sha256"] != pdf_sha:
        raise CellMapError("cell map %s is for pdf %s, not %s (%s)" % (mdir, man["pdf_sha256"][:12], pdf_sha[:12],
                                                                     pathlib.Path(pdf_path).name))
    if int(man["dpi"]) != int(dpi):
        raise CellMapError("cell map %s was cut at %s dpi, this run asks %s" % (mdir, man["dpi"], dpi))
    missing = [p for p in pages if str(p) not in man["pages"]]
    if missing:
        raise CellMapError("cell map %s (%s) has no page(s) %s" % (mdir, man.get("version"), missing))
    out = []
    for p in pages:
        snap = read_page(mdir, p)
        if snap["geometry_hash"] != man["pages"][str(p)]:
            raise CellMapError("cell map %s page %d: the page file is not the one the manifest names" % (mdir, p))
        pws, cells = _rebuild_page(pdf_path, p, dpi, snap)
        again = snapshot_page(pws, cells)
        if again["geometry_hash"] != snap["geometry_hash"]:
            raise CellMapError("cell map %s page %d: cutting the master's cells on this tree gives other cells (the "
                               "cutting code changed?): %s" % (mdir, p, first_difference(snap, again)))
        out.append((pws, cells))
    _LOADED.append({"dir": str(mdir), "version": man["version"], "pages": list(pages),
                    "built_commit": man.get("built", {}).get("commit")})
    return out


#: Every master loaded in this process -- the CLI stamps it into the record's provenance.
_LOADED: List[Dict[str, Any]] = []


def loaded() -> List[Dict[str, Any]]:
    return list(_LOADED)


def info(pdf_path: Any, *, dpi: int = 600, root: Any = ROOT_DEFAULT) -> Dict[str, Any]:
    return read_manifest(master_dir(root, sha256_file(pdf_path), dpi))


# ───────────────────────────── 6. what moved ─────────────────────────────

def _cell_key(page: int, local: Dict[int, Tuple[int, int]], v: Dict[str, Any]) -> Tuple[int, int, int, int]:
    s, st = local.get(v["staff_index"], (v["system_index"], v["staff_index"]))
    return (page, s, st, v["measure_index"])


def _local_map(staves: Sequence[Dict[str, Any]]) -> Dict[int, Tuple[int, int]]:
    """page-wide staff index -> (system, index within system): gather's own `_system_local`, so a key here is the
    `cell/p/s/st/c` subject the record and the tiles use."""
    from ..types import Staff
    from .gather import _system_local
    return _system_local([_construct(Staff, s) for s in staves])


def diff_snapshots(old: Dict[str, Any], new: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every staff, barline and cell that differs between two snapshots of ONE page. Cells are keyed
    (page, system, staff-in-system, cell) -- the record's `cell/...` subject; a moved barline renumbers the cells
    after it, so the barline rows are listed first and explain the cell rows."""
    page = int(old["page_index"])
    out: List[Dict[str, Any]] = []
    os_, ns_ = [dec(s) for s in old["staves"]], [dec(s) for s in new["staves"]]
    oloc, nloc = _local_map(os_), _local_map(ns_)
    ost = {oloc[s["staff_index"]]: s for s in os_}
    nst = {nloc[s["staff_index"]]: s for s in ns_}
    for k in sorted(set(ost) | set(nst)):
        a, b = ost.get(k), nst.get(k)
        if a is None or b is None:
            out.append(dict(what="staff", page=page, system=k[0], staff=k[1], old=a and a["line_ys"],
                            new=b and b["line_ys"]))
        elif a != b:
            ch = {f: [a.get(f), b.get(f)] for f in sorted(set(a) | set(b)) if a.get(f) != b.get(f)}
            out.append(dict(what="staff", page=page, system=k[0], staff=k[1], changed=ch))
    ob: Dict[int, List[int]] = {}
    nb: Dict[int, List[int]] = {}
    for src, dst in ((old, ob), (new, nb)):
        for b in src["barlines"]:
            b = dec(b)
            dst.setdefault(b["system_index"], []).append(int(b["x"]))
    for s in sorted(set(ob) | set(nb)):
        a, b = sorted(ob.get(s, [])), sorted(nb.get(s, []))
        if a != b:
            out.append(dict(what="barlines", page=page, system=s, old=a, new=b,
                            removed=sorted(set(a) - set(b)), added=sorted(set(b) - set(a))))
    ocols = dec(old["pws"]).get("system_structure") or {}
    ncols = dec(new["pws"]).get("system_structure") or {}
    if ocols != ncols:
        for s in sorted(set(ocols) | set(ncols), key=str):
            if ocols.get(s) != ncols.get(s):
                out.append(dict(what="system_columns", page=page, system=s,
                                old=[c.get("x") for c in (ocols.get(s) or {}).get("columns", [])],
                                new=[c.get("x") for c in (ncols.get(s) or {}).get("columns", [])]))
    oc = {_cell_key(page, oloc, dec(c["v"])): c for c in old["cells"]}
    nc = {_cell_key(page, nloc, dec(c["v"])): c for c in new["cells"]}
    for k in sorted(set(oc) | set(nc)):
        a, b = oc.get(k), nc.get(k)
        row = dict(what="cell", page=k[0], system=k[1], staff=k[2], cell=k[3])
        if a is None or b is None:
            row.update(old=a and list(dec(a["v"])["bbox_page_px"]), new=b and list(dec(b["v"])["bbox_page_px"]))
            out.append(row)
            continue
        av, bv = dec(a["v"]), dec(b["v"])
        ch = {}
        for f in ("bbox_page_px", "staff_line_ys_canonical"):
            if av.get(f) != bv.get(f):
                ch[f] = [list(av.get(f) or []), list(bv.get(f) or [])]
        if not ch and a != b:
            ch["pixels_or_other"] = first_difference(a, b)
        if ch:
            row["changed"] = ch
            out.append(row)
    return out


def moved(pdf_path: Any, pages: Sequence[int], *, dpi: int = 600, root: Any = ROOT_DEFAULT
          ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Cut `pages` with THIS tree and list what differs from the master."""
    from . import pipeline
    pdf_sha = sha256_file(pdf_path)
    mdir = master_dir(root, pdf_sha, dpi)
    man = read_manifest(mdir)
    rows: List[Dict[str, Any]] = []
    for p in pages:
        old = read_page(mdir, p)
        [(pws, cells)] = pipeline.prepare_pages(str(pdf_path), [p], dpi=dpi)
        new = snapshot_page(pws, cells)
        page_rows = diff_snapshots(old, new)
        if not page_rows and new["geometry_hash"] != old["geometry_hash"]:
            # nothing a lane reads as geometry moved, yet the cut is not the master's (a count, a pixel, a pad)
            page_rows = [dict(what="other", page=int(p), first=first_difference(old, new))]
        rows.extend(page_rows)
    return man, rows


def render_moved(man: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> str:
    lines = ["cell map %s (built on %s): %d difference(s)" % (man.get("version"), (man.get("built") or {}).get("commit", "?")[:9],
                                                             len(rows))]
    for r in rows:
        if r["what"] == "cell":
            where = "p%d s%d st%d c%d" % (r["page"], r["system"], r["staff"], r["cell"])
            if "changed" in r:
                lines.append("  cell %s: %s" % (where, "; ".join("%s %s -> %s" % (k, v[0], v[1]) if isinstance(v, list)
                                                                 else "%s %s" % (k, v) for k, v in r["changed"].items())))
            else:
                lines.append("  cell %s: %s -> %s" % (where, r["old"], r["new"]))
        elif r["what"] == "barlines":
            lines.append("  barlines p%d s%d: removed %s added %s" % (r["page"], r["system"], r["removed"], r["added"]))
        elif r["what"] == "system_columns":
            lines.append("  columns p%d s%s: %s -> %s" % (r["page"], r["system"], r["old"], r["new"]))
        elif r["what"] == "other":
            lines.append("  page p%d: %s" % (r["page"], r["first"]))
        else:
            lines.append("  staff p%d s%d st%d: %s" % (r["page"], r["system"], r["staff"],
                                                     r.get("changed") or "%s -> %s" % (r.get("old"), r.get("new"))))
    if not rows:
        lines.append("  NOTHING MOVED")
    return "\n".join(lines)


# ───────────────────────────── 7. against a gathered record ─────────────────────────────

def against_record(pdf_path: Any, record_path: Any, *, dpi: int = 600, root: Any = ROOT_DEFAULT,
                   pages: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """Does the master describe the cells a RECORD read? Compares the record's `cell_box` and `staff_lines`
    observations (streamed: never the whole file in memory) with the master, page by page."""
    from .judged import iter_array
    mdir = master_dir(root, sha256_file(pdf_path), dpi)
    man = read_manifest(mdir)
    want_pages = [int(p) for p in (pages if pages is not None else man["pages"])]
    rec_cells: Dict[str, List[float]] = {}
    rec_staves: Dict[str, List[float]] = {}
    for o in iter_array(pathlib.Path(record_path), "observations"):
        q = o.get("quantity")
        if q == "cell_box":
            rec_cells[o["subject"]] = [float(x) for x in o["value"]]
        elif q == "staff_lines":
            rec_staves[o["subject"]] = [float(x) for x in o["value"]]
    rep = {"version": man["version"], "pages": {}, "agree": True}
    for p in want_pages:
        snap = read_page(mdir, p)
        staves = [dec(s) for s in snap["staves"]]
        loc = _local_map(staves)
        mc = {}
        for c in snap["cells"]:
            v = dec(c["v"])
            k = _cell_key(p, loc, v)
            mc["cell/%d/%d/%d/%d" % k] = [float(x) for x in v["bbox_page_px"]]
        ms = {"staff/%d/%d/%d" % ((p,) + loc[s["staff_index"]]): [float(y) for y in s["line_ys"]] for s in staves}
        rc = {k: v for k, v in rec_cells.items() if k.split("/")[1] == str(p)}
        rs = {k: v for k, v in rec_staves.items() if k.split("/")[1] == str(p)}
        bad_c = sorted(k for k in set(mc) | set(rc) if mc.get(k) != rc.get(k))
        bad_s = sorted(k for k in set(ms) | set(rs) if ms.get(k) != rs.get(k))
        rep["pages"][p] = {"cells": len(mc), "record_cells": len(rc), "staves": len(ms), "record_staves": len(rs),
                           "cell_mismatch": bad_c[:20], "n_cell_mismatch": len(bad_c),
                           "staff_mismatch": bad_s[:20], "n_staff_mismatch": len(bad_s)}
        if bad_c or bad_s:
            rep["agree"] = False
    return rep


# ───────────────────────────── 8. the command ─────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    from .__main__ import parse_pages
    ap = argparse.ArgumentParser(prog="python3 -m tools.omr.staged.cell_map")
    ap.add_argument("cmd", choices=("build", "verify", "moved", "against-record", "show"))
    ap.add_argument("pdf")
    ap.add_argument("record", nargs="?")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--root", default=str(ROOT_DEFAULT))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    pages = parse_pages(a.pages) if a.pages else None
    if a.cmd == "build":
        if not pages:
            raise SystemExit("build needs --pages")
        man = build(a.pdf, pages, dpi=a.dpi, root=a.root, force=a.force, progress=True)
        print("cell map %s: %d pages, built on %s%s -> %s" % (man["version"], len(man["pages"]), man["built"]["commit"],
                                                              " (DIRTY)" if man["built"]["dirty"] else "",
                                                              master_dir(a.root, man["pdf_sha256"], a.dpi)))
        return 0
    if a.cmd == "show":
        man = info(a.pdf, dpi=a.dpi, root=a.root)
        print(json.dumps({k: v for k, v in man.items() if k != "built"} | {"built": {k: v for k, v in man["built"].items()
                                                                               if k != "cutting_sources"}}, indent=1))
        return 0
    if a.cmd == "against-record":
        rep = against_record(a.pdf, a.record, dpi=a.dpi, root=a.root, pages=pages)
        for p, r in rep["pages"].items():
            print("  p%s: cells %d (record %d) mismatched %d | staves %d (record %d) mismatched %d %s"
                  % (p, r["cells"], r["record_cells"], r["n_cell_mismatch"], r["staves"], r["record_staves"],
                     r["n_staff_mismatch"], (r["cell_mismatch"] + r["staff_mismatch"])[:3]))
        print("master %s %s the record" % (rep["version"], "AGREES WITH" if rep["agree"] else "DISAGREES WITH"))
        if a.json:
            pathlib.Path(a.json).write_text(json.dumps(rep, indent=1, default=str))
        return 0 if rep["agree"] else 1
    man, rows = moved(a.pdf, pages or [int(p) for p in info(a.pdf, dpi=a.dpi, root=a.root)["pages"]],
                      dpi=a.dpi, root=a.root)
    print(render_moved(man, rows))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"version": man["version"], "rows": rows}, indent=1, default=str))
    if a.cmd == "verify":
        print("VERIFY: %s" % ("fresh cut == master" if not rows else "FRESH CUT DIFFERS FROM THE MASTER"))
        return 0 if not rows else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
