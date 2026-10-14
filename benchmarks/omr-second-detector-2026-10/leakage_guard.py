"""ROADMAP 2.112 -- reusable TEST-vs-TRAIN leakage guard.  Reads files and hashes images only; no detector, no gather.

    python3 benchmarks/omr-test-leakage-2026-10/leakage_guard.py --test-keys litolff:1 --mix control
    from leakage_guard import check_leak, load_mix, TestCell

Three ways a test cell can be a training cell (CLAUDE.md rule 7: who says the test is clean?):
  1. EXACT   -- SHA-256 of the decoded pixel array (shape + bytes) equal.
  2. KEY     -- the same SOURCE key (edition, pdf page index 0-based, system, staff, measure), parsed from the cell
                manifests under benchmarks/**/*cells*.json (the old cutter and the product cutter name a cell by the
                same s<sys>-st<staff>-m<measure> triple; `beet5-p2` = Litolff 984073 page IDX 1: names are 1-based,
                manifests 0-based, so the key is read from the manifest, never from the name).
  3. NEAR    -- same cell re-cut at another pad / canonical frame: both images are scaled to a common staff space and
                the smaller is template-matched in the larger (TM_CCOEFF_NORMED).  Only run on KEY-candidate pairs
                (same page) unless asked, because an empty staff matches any empty staff (see FINDINGS controls).
`check_leak` returns every overlap; `refuse_if_leaked` raises.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")          # gitignored assets live in the main checkout
Key = Tuple[str, int, int, int, int]                           # edition, page, system, staff, measure


_RAW_EDITION = None


def _raw_edition(pdf: str) -> str:
    s = os.path.basename(pdf or "")
    m = re.search(r"imslp(\d+)", s, re.I)
    return ("imslp" + m.group(1)) if m else re.sub(r"\.pdf$", "", s)


def edition_key(pdf: str) -> str:
    """Canonical edition id.  Two PDF paths with the SAME SHA-1 are one edition (pdf_sha1.json, written by audit prep):
    `Mahler_5_.pdf` (Gradus-Assets) and `mahler--symphony-5--unidentified-scan-2016--local.pdf` are the same file, so cells
    named by either are the same pages.  Falls back to the imslp id / file stem."""
    global _RAW_EDITION
    if _RAW_EDITION is None:
        _RAW_EDITION = {}
        f = Path(__file__).parent / "pdf_sha1.json"
        if f.exists():
            by = {}
            for path, h in json.loads(f.read_text()).items():
                if h:
                    by.setdefault(h, []).append(path)
            for h, paths in by.items():
                lab = sorted((_raw_edition(p) for p in paths), key=lambda x: (not x.startswith("imslp"), "--" not in x, len(x)))[0]
                for p in paths:
                    _RAW_EDITION[p] = lab
    return _RAW_EDITION.get(pdf) or _raw_edition(pdf)


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


_MANIFEST: Optional[Dict[str, dict]] = None


def manifest_index(bench: Path = None) -> Dict[str, dict]:
    """cell_id -> {edition, page, key parts, staff_line_ys}, first manifest wins (as tools.omr.hand_truth.inventory does)."""
    global _MANIFEST
    if _MANIFEST is not None and bench is None:
        return _MANIFEST
    out: Dict[str, dict] = {}
    for f in sorted((bench or REPO / "benchmarks").glob("**/*cells*.json")):
        d = _json(f)
        rows = d if isinstance(d, list) else (d.get("cells") if isinstance(d, dict) else None)
        for r in rows or []:
            if isinstance(r, dict) and "cell_id" in r and r.get("pdf") and r.get("page") is not None:
                k = (r.get("system_index"), r.get("staff_index"), r.get("measure_index"))
                if None in k or r["cell_id"] in out:
                    continue
                out[r["cell_id"]] = {"edition": edition_key(r["pdf"]), "page": int(r["page"]), "sys": k[0], "staff": k[1],
                                     "meas": k[2], "lines": r.get("staff_line_ys_canonical")}
    if bench is None:
        _MANIFEST = out
    return out


def sha(im: np.ndarray) -> str:
    return hashlib.sha256(str(im.shape).encode() + np.ascontiguousarray(im).tobytes()).hexdigest()


def dhash(im: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    s = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    return (s[:, 1:] > s[:, :-1]).flatten()


def staff_space(im: np.ndarray, lines=None) -> Optional[float]:
    """Staff space in px: from the manifest's five line ys if given, else the median gap of the 5 strongest row peaks."""
    if lines and len(lines) >= 2:
        return float(np.median(np.diff(sorted(lines))))
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    prof = (g < 128).sum(1).astype(float)
    if prof.max() < 0.3 * g.shape[1]:
        return None
    idx = [i for i in np.argsort(-prof) if prof[i] > 0.5 * prof.max()]
    picked = []
    for i in idx:
        if all(abs(i - j) > 8 for j in picked):
            picked.append(i)
        if len(picked) == 5:
            break
    if len(picked) < 4:
        return None
    return float(np.median(np.diff(sorted(picked))))


def near_score(a: np.ndarray, b: np.ndarray, sa=None, sb=None, target=6.0) -> Optional[float]:
    """Best TM_CCOEFF_NORMED of the smaller image inside the larger, both scaled to staff space `target` px."""
    sa = sa or staff_space(a); sb = sb or staff_space(b)
    if not sa or not sb:
        return None
    def prep(im, s):
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
        f = target / s
        return cv2.resize(255 - g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA).astype(np.float32)
    A, B = prep(a, sa), prep(b, sb)
    if A.shape[0] * A.shape[1] > B.shape[0] * B.shape[1]:
        A, B = B, A
    # the template may poke out of the larger frame (different pad): trim it to fit, but keep >= 60% of each side
    th, tw = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
    if th < 0.6 * A.shape[0] or tw < 0.6 * A.shape[1] or A.std() < 1e-3:
        return None
    best = -1.0
    # try centred and four corner trims of the template
    for y0 in (0, A.shape[0] - th):
        for x0 in (0, A.shape[1] - tw):
            T = A[y0:y0 + th, x0:x0 + tw]
            if T.std() < 1e-3:
                continue
            r = cv2.matchTemplate(B, T, cv2.TM_CCOEFF_NORMED)
            best = max(best, float(r.max()))
    return best


@dataclass
class Cell:
    name: str                       # human label, e.g. "v13.../beet5-p2-sys0-s2-m3"
    path: Optional[Path]            # image, if one exists
    key: Optional[Key]              # None if the cell cannot be placed on a page
    group: str = ""                 # test set id or training version
    lines: Optional[list] = None
    _im: Optional[np.ndarray] = field(default=None, repr=False)

    def image(self):
        if self._im is None and self.path is not None:
            self._im = cv2.imread(str(self.path))
        return self._im


def key_of(cell_id: str) -> Optional[Key]:
    m = manifest_index().get(cell_id)
    return (m["edition"], m["page"], m["sys"], m["staff"], m["meas"]) if m else None


def load_version(root: Path, version: str) -> List[Cell]:
    d = Path(root) / version / "images"
    out = []
    for p in sorted(d.glob("*.png")):
        if p.stem.endswith("_nostaff"):
            continue
        m = manifest_index().get(p.stem)
        out.append(Cell(f"{version}/{p.stem}", p, key_of(p.stem), version, m["lines"] if m else None))
    return out


def check_leak(test: List[Cell], train: List[Cell], near_threshold=0.9, near=True) -> dict:
    """Overlaps between a TEST list and a TRAIN list.  Never mutates; returns {'exact','key','near'} lists of pairs."""
    th = {}
    for c in test:
        im = c.image()
        if im is not None:
            th.setdefault(sha(im), []).append(c)
    by_key: Dict[Key, List[Cell]] = {}
    for c in test:
        if c.key:
            by_key.setdefault(c.key, []).append(c)
    by_page: Dict[Tuple[str, int], List[Cell]] = {}
    for c in test:
        if c.key:
            by_page.setdefault(c.key[:2], []).append(c)
    exact, keyed, nearp = [], [], []
    for t in train:
        im = t.image()
        if im is not None:
            for c in th.get(sha(im), []):
                exact.append((t.name, c.name))
        for c in by_key.get(t.key, []) if t.key else []:
            keyed.append((t.name, c.name))
        if near and im is not None and t.key:
            for c in by_page.get(t.key[:2], []):
                ci = c.image()
                if ci is None:
                    continue
                s = near_score(im, ci, staff_space(im, t.lines), staff_space(ci, c.lines))
                if s is not None and s >= near_threshold:
                    nearp.append((t.name, c.name, round(s, 3)))
    return {"exact": exact, "key": keyed, "near": nearp}


def refuse_if_leaked(test, train, **kw):
    r = check_leak(test, train, **kw)
    if r["exact"] or r["key"] or r["near"]:
        raise SystemExit(f"LEAKED TEST: {len(r['exact'])} exact, {len(r['key'])} same-key, {len(r['near'])} near-duplicate cells")
    return r


def load_mix(name: str) -> List[Cell]:
    """Named training mixes.  'production' = distill25 catalog (v1-v4,v13-v22) -- the graft's feature source;
    'control' = production + v24 (2.4b/2.110 control arm uses v1-v4,v13-v22 [+v24])."""
    d25 = MAIN / "data" / "user-labeled-distill25"
    lab = MAIN / "data" / "user-labeled"
    vs = [l.strip() for l in (d25 / "catalog-versions.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    cells: List[Cell] = []
    for v in vs:
        cells += load_version(d25, v)
    if name == "plus_v24":
        cells += load_version(lab, "v24-2026-10-13-hollow4-train")
    return cells


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-dir", required=True, help="dir of test cell PNGs named by cell_id, with --cells manifest json")
    ap.add_argument("--cells", required=True)
    ap.add_argument("--mix", default="production")
    a = ap.parse_args()
    rows = json.loads(Path(a.cells).read_text())
    test = [Cell(r["cell_id"], Path(a.test_dir) / f"{r['cell_id']}.png",
                 (edition_key(r["pdf"]), int(r["page"]), r["system_index"], r["staff_index"], r["measure_index"]), "test",
                 r.get("staff_line_ys_canonical")) for r in rows]
    print(json.dumps(check_leak(test, load_mix(a.mix)), indent=1))
