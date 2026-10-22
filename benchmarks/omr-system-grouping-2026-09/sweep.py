#!/usr/bin/env python3
"""Layout-only system-grouping sweep across the publisher-stratified library.

No YOLO, no weights, no DB. Renders each sampled page, runs staff detection +
system grouping (`tools.omr.staff_detector.detect_staves`, which applies
`tools.omr.system_grouping.assign_systems` internally), and records the raw
per-gap evidence (`gap_bridging_counts`, `_x_overlap_frac`) alongside the
resulting partition. This is the harness other scripts in this benchmark
(`score.py`, `make_crops.py`, `summarize.py`) build on.

PDFs live in the MAIN CHECKOUT (`library/editions/` is untracked and does not
exist in this worktree). Code — `tools.omr` — is imported from THIS worktree,
so that rule edits on this branch are what get measured, per the build brief.

Usage:
    python3 sweep.py                          # full default sweep (resumable)
    python3 sweep.py --only mozart/symphony-25 # one work
    python3 sweep.py --only some.pdf --pages 0-4,9   # explicit pages, 0-based
    python3 sweep.py --all --only bach          # every page of matching PDFs
    python3 sweep.py --limit 20                 # cap this invocation (testing/chunking)

Resumable: (pdf_rel, page) pairs already present in --out are skipped on
restart (including prior error rows), unless --retry-errors is given.

Render normalization (repo-state.md §4.4): a fixed DPI silently zeroes out
editions with a small page box (measured: a 2.38x2.82in mediabox reads 0
staves at 300 dpi). We normalize to a TARGET PIXEL HEIGHT instead:
    dpi = clamp(round(target_height / mediabox_height_in), 150, 1400)
and halve the target (recording that we did) if the resulting raster would
exceed 40 megapixels.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]          # .../worktrees/system-break-rule-publishers-62ead4
sys.path.insert(0, str(WORKTREE_ROOT))   # tools.omr comes from THIS branch, not main.

import fitz  # noqa: E402  (PyMuPDF; only used here for cheap page-count/mediabox reads)

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.system_grouping import gap_bridging_counts, _x_overlap_frac  # noqa: E402

# ─── Corpus location (main checkout only — see module docstring) ────────────

LIBRARY_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")
DOWNLOADS_K183_NMA = Path(
    "/Users/seanjohnson/Downloads/"
    "IMSLP849180-PMLP1544-Mozart,_Wofgang_Amadeus-NMA_04_11_Band_04_06_KV_183_scan.pdf"
)
DEFAULT_OUT = HERE / "sweep.jsonl"

# ─── Rendering normalization ─────────────────────────────────────────────────

TARGET_HEIGHT_PX = 3300
DPI_MIN, DPI_MAX = 150, 1400
MAX_MEGAPIXELS = 40_000_000
PT_PER_INCH = 72.0


def compute_render_params(width_pt: float, height_pt: float, target_height: int = TARGET_HEIGHT_PX):
    """-> (dpi, halved). See module docstring for the rule."""
    h_in = height_pt / PT_PER_INCH
    w_in = width_pt / PT_PER_INCH

    def _dpi_for(target):
        return max(DPI_MIN, min(DPI_MAX, int(round(target / h_in))))

    dpi = _dpi_for(target_height)
    halved = False
    if round(w_in * dpi) * round(h_in * dpi) > MAX_MEGAPIXELS:
        dpi = _dpi_for(target_height / 2.0)
        halved = True
    return dpi, halved


# ─── Page sampling ────────────────────────────────────────────────────────────

DEFAULT_FRACTIONS = (0.15, 0.40, 0.65, 0.90)


def default_sample_pages(n_pages: int, pages_per_pdf: int = 4):
    """0-based page indices. Page index min 1 (skip the title page). <=6 pages
    -> every page from index 1. Deduped, order-preserving."""
    if n_pages <= 6:
        return list(range(1, n_pages))
    if pages_per_pdf == 4:
        fracs = DEFAULT_FRACTIONS
    elif pages_per_pdf <= 1:
        fracs = (0.5,)
    else:
        # Evenly spaced over the same span the documented default covers.
        lo, hi = 0.15, 0.90
        fracs = [lo + (hi - lo) * i / (pages_per_pdf - 1) for i in range(pages_per_pdf)]
    out = []
    for f in fracs:
        idx = max(1, min(n_pages - 1, int(round(f * n_pages))))
        if idx not in out:
            out.append(idx)
    return out


def parse_pages_arg(spec: str, n_pages: int):
    """'0-4,9,12' -> [0,1,2,3,4,9,12], 0-based, matching the rest of the
    tools.omr CLI convention (e.g. `transcribe.py --pages 0-4`)."""
    out = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            for i in range(int(a), int(b) + 1):
                if 0 <= i < n_pages and i not in out:
                    out.append(i)
        else:
            i = int(chunk)
            if 0 <= i < n_pages and i not in out:
                out.append(i)
    return out


# ─── Provenance (sidecar JSON, filename fallback) ────────────────────────────

# composer--work--publisher-year--imslpID.pdf
FILENAME_RE = re.compile(r"^(?P<composer>[^-]+(?:-[^-]+)*?)--(?P<work>.+)--(?P<token>.+)--imslp(?P<id>[A-Za-z0-9]+)$")


def parse_filename_fallback(pdf_path: Path):
    """(publisher_token, imslp_id) parsed from the `composer--work--publisher
    -year--imslpID.pdf` convention. Used only when the sidecar is missing or
    the field is empty."""
    m = FILENAME_RE.match(pdf_path.stem)
    if m:
        return m.group("token"), m.group("id")
    # Fall back further: split on '--' and take what we can.
    parts = pdf_path.stem.split("--")
    token = parts[-2] if len(parts) >= 2 else None
    imslp_id = None
    if parts and parts[-1].lower().startswith("imslp"):
        imslp_id = parts[-1][5:]
    return token, imslp_id


def read_sidecar(pdf_path: Path):
    json_path = pdf_path.with_suffix(".json")
    if not json_path.exists():
        return {}
    try:
        return json.loads(json_path.read_text())
    except Exception:
        return {}


def provenance_for(pdf_path: Path):
    """{publisher, publisher_token, year, imslp_id} — sidecar first, filename
    fallback per field. `publisher_token` is defined as the FILENAME's
    publisher-year token (the stable stratification key), so it is always
    parsed from the filename convention directly (sidecar `variant` mirrors it
    1:1 in every sidecar we found, since the ingest tool built the filename
    from `variant` — but the filename is the documented source of truth)."""
    sc = read_sidecar(pdf_path)
    fname_token, fname_id = parse_filename_fallback(pdf_path)
    return {
        "publisher": sc.get("publisher") or None,
        "publisher_token": fname_token or sc.get("variant") or None,
        "year": sc.get("publisher_year") or None,
        "imslp_id": (str(sc.get("imslp_id")) if sc.get("imslp_id") else None) or fname_id,
    }


# ─── Discovery ────────────────────────────────────────────────────────────────


def iter_library_pdfs(library_root: Path):
    pdfs = sorted(library_root.rglob("*.pdf"))
    # Standing user rule: never benchmark on Nottebohm. None expected under
    # library/editions (it lives in ~/Downloads only, per the corpus
    # inventory), but the exclusion is enforced defensively regardless.
    return [p for p in pdfs if "nottebohm" not in p.name.lower()]


def rel_or_abs(pdf_path: Path) -> str:
    try:
        return str(pdf_path.relative_to(LIBRARY_ROOT))
    except ValueError:
        return str(pdf_path)


# ─── Special-case pairs ───────────────────────────────────────────────────────

BEETHOVEN5_PAIR = (
    LIBRARY_ROOT / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf",
    LIBRARY_ROOT / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
)
BRAHMS1_PAIR = (
    LIBRARY_ROOT / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    LIBRARY_ROOT / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp516790.pdf",
)
MOZART41_PAIR = (
    LIBRARY_ROOT / "mozart/symphony-41-in-c-major-k551/mozart--symphony-41-in-c-major-k551--breitkopf-hartel-mozart-1880--imslp73.pdf",
    LIBRARY_ROOT / "mozart/symphony-41-in-c-major-k551/mozart--symphony-41-in-c-major-k551--breitkopf-hartel-mozart-1880--imslp984556.pdf",
)
K183_A = LIBRARY_ROOT / "mozart/symphony-25-in-g-minor-k183/mozart--symphony-25-in-g-minor-k183--breitkopf-hartel-mozart-1880--imslp57.pdf"
# The build brief specifies the Downloads copy (no sidecar, hand-labelled
# baerenreiter-nma / 1900s-critical-edition) because at spec-writing time the
# second K.183 edition had not been ingested into the library. It has been
# ingested since (library/editions/mozart/symphony-25-in-g-minor-k183-173db/
# ...imslp849180.pdf) with a real sidecar (publisher "Barenreiter (Neue
# Mozart-Ausgabe), IV, 1960", year 1960) and is byte-identical to the
# Downloads file (verified via sha256). We prefer the library copy — better
# metadata, same bytes — and fall back to the literal Downloads path with the
# brief's hand-assigned label if the library copy is ever absent.
K183_B_LIBRARY = (
    LIBRARY_ROOT / "mozart/symphony-25-in-g-minor-k183-173db/"
    "mozart--symphony-25-in-g-minor-k183-173db--barenreiter-neue-mozart-1960--imslp849180.pdf"
)


def resolve_k183_b():
    if K183_B_LIBRARY.is_file():
        return K183_B_LIBRARY, None  # sidecar-backed; provenance_for() handles it normally
    if DOWNLOADS_K183_NMA.is_file():
        # Hand-assigned per the build brief; no sidecar exists for this path.
        return DOWNLOADS_K183_NMA, {
            "publisher": None,
            "publisher_token": "baerenreiter-nma",
            "year": "1900s-critical-edition",
            "imslp_id": "849180",
        }
    return None, None


def build_pair_registry():
    """[{pair_id, mode, members: [Path,...], provenance_override: {path: dict|None}}]"""
    registry = []
    k183_b_path, k183_b_override = resolve_k183_b()
    if K183_A.is_file() and k183_b_path is not None:
        registry.append({
            "pair_id": "k183",
            "mode": "full",  # ALL pages from index 1, per the build brief.
            "members": [K183_A, k183_b_path],
            "provenance_override": {K183_A: None, k183_b_path: k183_b_override},
        })
    for pair_id, (a, b) in (
        ("beethoven5-scan-pair", BEETHOVEN5_PAIR),
        ("brahms1-scan-pair", BRAHMS1_PAIR),
        ("mozart41-scan-pair", MOZART41_PAIR),
    ):
        if a.is_file() and b.is_file():
            registry.append({
                "pair_id": pair_id,
                "mode": "shared_sample",  # identical explicit page list, from the smaller count
                "members": [a, b],
                "provenance_override": {a: None, b: None},
            })
        else:
            print(f"  [pairs] WARNING: {pair_id} incomplete on disk, skipping", file=sys.stderr)
    return registry


# ─── Plan construction ────────────────────────────────────────────────────────


def get_page_count(pdf_path: Path) -> int:
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def build_plan(pdfs, args):
    """pdf_path -> (page_list, pair_id_or_None). `pdfs` is already `--only`-filtered."""
    pdf_set = set(pdfs)
    plan = {}

    if args.pages is not None:
        if len(pdfs) != 1:
            raise SystemExit(f"--pages requires --only to match exactly one PDF; matched {len(pdfs)}")
        p = pdfs[0]
        n = get_page_count(p)
        plan[p] = (parse_pages_arg(args.pages, n), None)
        return plan

    for p in pdfs:
        n = get_page_count(p)
        pages = list(range(1, n)) if args.all else default_sample_pages(n, args.pages_per_pdf)
        plan[p] = (pages, None)

    if args.no_special_cases:
        return plan

    for pair in build_pair_registry():
        members = [m for m in pair["members"] if m in pdf_set]
        if len(members) != len(pair["members"]):
            continue  # one or both sides filtered out by --only; leave defaults alone
        if pair["mode"] == "full":
            for m in members:
                n = get_page_count(m)
                plan[m] = (list(range(1, n)), pair["pair_id"])
        elif pair["mode"] == "shared_sample" and not args.all:
            counts = {m: get_page_count(m) for m in members}
            smaller = min(counts.values())
            shared_pages = default_sample_pages(smaller, args.pages_per_pdf)
            for m in members:
                plan[m] = (shared_pages, pair["pair_id"])
        elif pair["mode"] == "shared_sample" and args.all:
            # --all already gives each member its own full range; just tag pair_id.
            for m in members:
                plan[m] = (plan[m][0], pair["pair_id"])

    return plan


PAIR_PROVENANCE_OVERRIDES = {}  # path -> provenance dict override, for pair members with no sidecar
for _pair in build_pair_registry():
    for _path, _override in _pair["provenance_override"].items():
        if _override is not None:
            PAIR_PROVENANCE_OVERRIDES[_path] = _override


# ─── Per-page processing ─────────────────────────────────────────────────────


def process_page(pdf_path: Path, page_index: int, prov: dict, pair_id):
    row = {
        "pdf_rel": rel_or_abs(pdf_path),
        "publisher": prov.get("publisher"),
        "publisher_token": prov.get("publisher_token"),
        "year": prov.get("year"),
        "imslp_id": prov.get("imslp_id"),
        "pair_id": pair_id,
        "page": page_index,
        "dpi": None,
        "dpi_halved": None,
        "width": None,
        "height": None,
        "n_staves": None,
        "staves_per_system": None,
        "group_sizes": None,
        "gaps": None,
        "used_bridging": None,
        "staff_geometry": None,
        "runtime_s": None,
        "error": None,
    }
    t0 = time.time()
    try:
        doc = fitz.open(pdf_path)
        try:
            rect = doc[page_index].rect
        finally:
            doc.close()
        dpi, halved = compute_render_params(rect.width, rect.height)
        row["dpi"] = dpi
        row["dpi_halved"] = halved

        pi = render_page(pdf_path, page_index, dpi=dpi)
        row["width"] = pi.width
        row["height"] = pi.height

        pws = detect_staves(pi)
        staves = sorted(pws.staves, key=lambda s: s.top_y)
        row["n_staves"] = len(staves)

        row["staves_per_system"] = [len(list(g)) for _, g in itertools.groupby(
            staves, key=lambda s: s.system_index)]

        group_sizes = []
        for _, sys_group in itertools.groupby(staves, key=lambda s: s.system_index):
            sys_staves = list(sys_group)
            group_sizes.append([len(list(g)) for _, g in itertools.groupby(
                sys_staves, key=lambda s: s.group_index)])
        row["group_sizes"] = group_sizes

        if len(staves) >= 2:
            bridging = gap_bridging_counts(pi.binary, staves)
            gaps = []
            for i, (up, lo) in enumerate(zip(staves, staves[1:])):
                gaps.append({
                    "gap_px": lo.top_y - up.bottom_y,
                    "bridging": bridging[i],
                    "x_overlap": round(_x_overlap_frac(up, lo), 4),
                    "break_fired": up.system_index != lo.system_index,
                })
            row["gaps"] = gaps
            row["used_bridging"] = any(b > 0 for b in bridging)
        else:
            row["gaps"] = []
            row["used_bridging"] = True  # matches assign_systems' own <2-staff short-circuit

        row["staff_geometry"] = [
            {"top_y": s.top_y, "bottom_y": s.bottom_y, "x_start": s.x_start, "x_end": s.x_end}
            for s in staves
        ]
    except Exception as exc:  # noqa: BLE001 — sweep must survive a bad page and continue
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["runtime_s"] = round(time.time() - t0, 3)
    return row


# ─── Resumability ─────────────────────────────────────────────────────────────


def load_done_keys(out_path: Path, retry_errors: bool):
    done = set()
    if not out_path.exists():
        return done
    with out_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if retry_errors and row.get("error") is not None:
                continue
            done.add((row["pdf_rel"], row["page"]))
    return done


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pages-per-pdf", type=int, default=4)
    ap.add_argument("--only", default=None, help="case-insensitive substring filter on the relative path")
    ap.add_argument("--pages", default=None, help="explicit 0-based pages/ranges, e.g. '0-4,9' — requires --only match one PDF")
    ap.add_argument("--all", action="store_true", help="every page (from index 1) of every matched PDF")
    ap.add_argument("--limit", type=int, default=None, help="cap the number of (pdf,page) tasks THIS invocation runs")
    ap.add_argument("--retry-errors", action="store_true", help="also re-run (pdf,page) pairs whose prior row was an error")
    ap.add_argument("--no-special-cases", action="store_true", help="disable the K183/scan-pair overrides (debugging)")
    args = ap.parse_args()

    pdfs = iter_library_pdfs(LIBRARY_ROOT)
    if args.only:
        needle = args.only.lower()
        pdfs = [p for p in pdfs if needle in rel_or_abs(p).lower()]
    if not pdfs:
        print("No PDFs matched.", file=sys.stderr)
        return 1

    plan = build_plan(pdfs, args)
    total_planned = sum(len(pages) for pages, _ in plan.values())
    print(f"{len(plan)} PDFs, {total_planned} planned pages "
          f"(pair-tagged PDFs: {sum(1 for _, pid in plan.values() if pid)})")

    done = load_done_keys(args.out, args.retry_errors)
    print(f"{len(done)} (pdf,page) rows already present in {args.out}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tasks = []
    for pdf_path in sorted(plan.keys()):
        pages, pair_id = plan[pdf_path]
        rel = rel_or_abs(pdf_path)
        for page in sorted(pages):
            if (rel, page) in done:
                continue
            tasks.append((pdf_path, page, pair_id))
    if args.limit:
        tasks = tasks[: args.limit]
    print(f"{len(tasks)} tasks to run this invocation")

    n_ok = n_err = 0
    t_start = time.time()
    with args.out.open("a") as f:
        for i, (pdf_path, page, pair_id) in enumerate(tasks):
            prov = provenance_for(pdf_path)
            override = PAIR_PROVENANCE_OVERRIDES.get(pdf_path)
            if override:
                prov = override
            row = process_page(pdf_path, page, prov, pair_id)
            f.write(json.dumps(row) + "\n")
            f.flush()
            if row["error"] is not None:
                n_err += 1
                print(f"  [{i+1}/{len(tasks)}] ERROR {rel_or_abs(pdf_path)} "
                      f"p{page}: {row['error']}", file=sys.stderr)
            else:
                n_ok += 1
            if (i + 1) % 25 == 0 or (i + 1) == len(tasks):
                elapsed = time.time() - t_start
                print(f"  [{i+1}/{len(tasks)}] ok={n_ok} err={n_err} elapsed={elapsed:.0f}s")

    print(f"done: {n_ok} ok, {n_err} error, wrote/updated {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
