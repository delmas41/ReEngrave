"""Second-opinion QC pass over a whole score's `.omr.json`.

Runs an external OMR engine per page and flags clef / time-signature
disagreements — GATED to where the local pipeline is actually weak, so the
output is signal, not noise:
  - meter: the pipeline ABSTAINED (null) and the engine reads one, or the two
    disagree outright;
  - clefs: the engine sees clef types the pipeline missed AND the page's clefs
    were largely DEFAULTED (few clef glyphs detected → position fallback, the
    real-orchestral failure mode).

Engine routing (`--engine auto`): oemer for pages that resolve to a 2-staff
grand staff (piano/keyboard); LEGATO for orchestral (>2 staves), since oemer
hard-asserts 2 staves. Per-page engine output is cached so re-runs and gate
tweaks are cheap.

Host-side + opt-in, like the Maestro theory bridge — LEGATO/oemer don't run in
the Docker backend. LEGATO needs LEGATO_DIR + LEGATO_PY set (see
tools/omr/legato_cloud/README.md and the setup recipe).

Output: `{stem}.second_opinion.json` + a printed report.

CLI:
    python3 -m tools.omr.second_opinion_pass \
        --omr-json score.omr.json --pdf score.pdf --pages 0-4 --engine auto
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from tools.omr.oemer_second_opinion import (
    Summary,
    _clef_presence,
    _pretty_clef,
    render_pdf_page,
    run_legato,
    run_oemer,
    summarize_abc,
    summarize_musicxml,
    summarize_omr_json,
)


# --------------------------------------------------------------------------- #
# Page facts from the .omr.json
# --------------------------------------------------------------------------- #
def _page(omr: dict, page: int) -> dict:
    pages = omr.get("pages", [])
    if page >= len(pages):
        raise IndexError(f"omr.json has {len(pages)} page(s); page {page} requested")
    return pages[page]


def page_staff_count(omr: dict, page: int) -> int:
    return sum(len(s.get("staves", [])) for s in _page(omr, page).get("systems", []))


def clef_detection_rate(omr: dict, page: int) -> float:
    """Fraction of staves whose clef was actually DETECTED (vs position-default).

    Low rate == the page's clefs are largely defaulted, so a clef disagreement
    is a meaningful flag rather than an engine error.
    """
    staves = 0
    clef_dets = 0
    for sysm in _page(omr, page).get("systems", []):
        for st in sysm.get("staves", []):
            staves += 1
            for m in st.get("measures", []):
                if any(d.get("category") == "clef" for d in m.get("detections", [])):
                    clef_dets += 1
                    break  # this staff has at least one detected clef
    return (clef_dets / staves) if staves else 0.0


def route_engine(staff_count: int) -> str:
    # oemer only handles a 2-staff grand staff; everything else -> LEGATO.
    return "oemer" if staff_count <= 2 else "legato"


# --------------------------------------------------------------------------- #
# The gate — pure, unit-tested
# --------------------------------------------------------------------------- #
def gate_flags(pipeline: Summary, engine: Summary, clef_rate: float,
               clef_rate_threshold: float = 0.5) -> dict:
    """Turn a pipeline-vs-engine comparison into gated QC flags."""
    eng = engine.source
    flags: list[str] = []

    p_changes, e_changes = pipeline.global_time_changes(), engine.global_time_changes()
    p_m = p_changes[0][1] if p_changes else None
    e_m = e_changes[0][1] if e_changes else None
    meter: dict[str, Any] = {"pipeline": p_m, "engine": e_m, "flag": None}
    if p_m is None and e_m is not None:
        meter["flag"] = "meter_suggestion"
        meter["suggested"] = e_m
        flags.append(f"meter: pipeline abstained; {eng} suggests {e_m}")
    elif p_m and e_m and p_m != e_m:
        meter["flag"] = "meter_disagree"
        flags.append(f"meter: pipeline {p_m} vs {eng} {e_m}")

    pp, ee = _clef_presence(pipeline), _clef_presence(engine)
    only_engine = sorted(ee - pp)
    clefs: dict[str, Any] = {
        "pipeline_present": sorted(pp),
        "engine_present": sorted(ee),
        "only_engine": only_engine,
        "clef_detection_rate": round(clef_rate, 3),
        "flag": None,
    }
    if only_engine and clef_rate < clef_rate_threshold:
        clefs["flag"] = "clefs_defaulted"
        flags.append(
            f"clefs: pipeline saw {[_pretty_clef(t) for t in sorted(pp)]} "
            f"(only {clef_rate:.0%} of staves had a detected clef); {eng} also sees "
            f"{[_pretty_clef(t) for t in only_engine]}")
    return {"meter": meter, "clefs": clefs, "flags": flags}


# --------------------------------------------------------------------------- #
# Per-page engine run (with caching)
# --------------------------------------------------------------------------- #
def engine_summary_for_page(engine: str, pdf: str | Path, page: int,
                            cache_dir: Path, dpi: int = 200,
                            timeout: int = 1800) -> tuple[Optional[Summary], str]:
    """Render + run the engine for one page (reusing cache). Returns (summary, note)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    if engine == "oemer":
        cache = cache_dir / f"page{page}.oemer.musicxml"
        if not cache.exists():
            png = render_pdf_page(pdf, page, cache_dir / f"page{page}.png", dpi=dpi)
            try:
                run_oemer(png, cache, timeout=timeout)
            except Exception as e:  # oemer can't do >2 staves, etc.
                return None, f"oemer unavailable: {str(e).splitlines()[0]}"
        return summarize_musicxml(cache, source="oemer"), "ok"
    # legato
    cache = cache_dir / f"page{page}.legato.abc.json"
    if not cache.exists():
        png = render_pdf_page(pdf, page, cache_dir / f"page{page}.png", dpi=dpi)
        try:
            abc = run_legato(png, cache_dir / f"page{page}.legato", timeout=timeout)
        except Exception as e:
            return None, f"legato unavailable: {str(e).splitlines()[0]}"
        cache.write_text(json.dumps({"abc_transcription": [abc]}))
    return summarize_abc(cache, source="legato"), "ok"


# --------------------------------------------------------------------------- #
# The pass
# --------------------------------------------------------------------------- #
def second_opinion_pass(omr_json_path: str | Path, pdf: str | Path,
                        pages: Optional[list[int]] = None, engine: str = "auto",
                        cache_dir: Optional[Path] = None, dpi: int = 200,
                        clef_rate_threshold: float = 0.5) -> dict:
    omr_json_path = Path(omr_json_path)
    omr = json.loads(omr_json_path.read_text())
    n_pages = len(omr.get("pages", []))
    if pages is None:
        pages = list(range(n_pages))
    cache_dir = cache_dir or (omr_json_path.parent / "second_opinion_cache")

    page_reports: list[dict] = []
    for pg in pages:
        staves = page_staff_count(omr, pg)
        eng = route_engine(staves) if engine == "auto" else engine
        pipeline_summary = summarize_omr_json(omr, page=pg)
        eng_summary, note = engine_summary_for_page(eng, pdf, pg, cache_dir, dpi=dpi)
        if eng_summary is None:
            page_reports.append({"page": pg, "engine": eng, "n_staves": staves,
                                 "status": note, "flags": []})
            print(f"[page {pg}] {eng}: {note}", file=sys.stderr)
            continue
        rate = clef_detection_rate(omr, pg)
        gated = gate_flags(pipeline_summary, eng_summary, rate, clef_rate_threshold)
        page_reports.append({
            "page": pg, "engine": eng, "n_staves": staves,
            "n_voices_engine": eng_summary.n_parts, "status": "ok", **gated,
        })
        print(f"[page {pg}] {eng}: {len(gated['flags'])} flag(s)", file=sys.stderr)

    flagged = [p for p in page_reports if p.get("flags")]
    report = {
        "omr_json": str(omr_json_path),
        "pages_checked": len(page_reports),
        "pages_flagged": len(flagged),
        "meter_flags": sum(1 for p in page_reports if p.get("meter", {}).get("flag")),
        "clef_flags": sum(1 for p in page_reports if p.get("clefs", {}).get("flag")),
        "pages": page_reports,
    }
    return report


def render_report(report: dict) -> str:
    L = ["=" * 66, "  second-opinion QC pass — gated clef/meter flags", "=" * 66,
         f"pages checked: {report['pages_checked']}   flagged: {report['pages_flagged']}"
         f"   (meter: {report['meter_flags']}, clef: {report['clef_flags']})", ""]
    for p in report["pages"]:
        if p["status"] != "ok":
            L.append(f"  page {p['page']:>3} [{p['engine']}]  — {p['status']}")
            continue
        if not p["flags"]:
            L.append(f"  page {p['page']:>3} [{p['engine']}]  OK (no gated disagreement)")
            continue
        L.append(f"  page {p['page']:>3} [{p['engine']}]  {p['n_staves']} staves / "
                 f"{p['n_voices_engine']} engine voices  !!")
        for f in p["flags"]:
            L.append(f"        - {f}")
    L.append("=" * 66)
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_pages(spec: str, n_pages: int) -> Optional[list[int]]:
    if not spec:
        return None
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--omr-json", required=True, help="Pipeline .omr.json result.")
    ap.add_argument("--pdf", required=True, help="Source PDF (pages rendered for the engine).")
    ap.add_argument("--pages", default="", help="e.g. 0-4,7 (default: all).")
    ap.add_argument("--engine", choices=["auto", "oemer", "legato"], default="auto")
    ap.add_argument("--cache-dir", default=None, help="Per-page engine-output cache.")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--clef-rate-threshold", type=float, default=0.5,
                    help="Flag clef disagreements only when detected-clef rate is below this.")
    ap.add_argument("--out", default=None, help="Artifact path (default {stem}.second_opinion.json).")
    args = ap.parse_args(argv)

    omr_path = Path(args.omr_json)
    n_pages = len(json.loads(omr_path.read_text()).get("pages", []))
    report = second_opinion_pass(
        omr_path, args.pdf, pages=_parse_pages(args.pages, n_pages), engine=args.engine,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None, dpi=args.dpi,
        clef_rate_threshold=args.clef_rate_threshold)
    print(render_report(report))

    stem = omr_path.name[:-len(".omr.json")] if omr_path.name.endswith(".omr.json") else omr_path.stem
    out = Path(args.out) if args.out else omr_path.parent / f"{stem}.second_opinion.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\n[artifact] -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
