"""
Staged OMR — runs the STAGED pipeline (``tools/omr/staged``) in-process,
BESIDE the legacy ``local`` engine (``backend/modules/local_omr.py``).
ROADMAP 3.3: ``omr_engine=staged`` in the web app (first half), plus the
page-cap -> job-budget half (this module's ``parse_page_range`` /
``estimate_budget_s``). The default web engine stays ``local`` (CLAUDE.md
§3: STAGED is the product path per DECISIONS 2026-09-22, but it does not
yet export LilyPond by default here and is not yet the web app's default).

Provides ``run_staged_omr(pdf_path, output_dir, pages=None) -> StagedOmrResult``,
mirroring ``local_omr.run_local_omr``'s contract:

  * writes ``{stem}.record.json`` — the pooled staged record, via
    ``tools.omr.staged.record_io.dumps_for_file`` (the SAME writer
    ``python3 -m tools.omr.staged`` uses for ``--out``);
  * writes ``{stem}.musicxml`` via
    ``tools.omr.staged.export.to_musicxml``;
  * never turns ``tools.omr.staged.export.Unbalanced`` into a quiet
    success. It propagates out of the blocking worker and is caught by the
    SAME broad ``except Exception`` every other worker failure is, so it is
    reported as ``error_message`` with ``musicxml_path=""`` — the caller
    (``backend/main.py``) then marks the job ``error`` with that message.
    Not a special case: a special case is exactly the kind of
    un-exercised branch this repo's own findings keep calling out.

⚠️ SAME ENV KNOBS AS ``local_omr`` (CLAUDE.md rule 9: no new flags).
``OMR_WEIGHTS_PATH``, ``OMR_DPI``, ``OMR_CONF_THRESHOLD`` and ``OMR_IMGSZ``
are read via ``local_omr``'s own helpers, imported rather than restated, so
the two engines can never silently disagree about what one of these means.
``OMR_MAX_PAGES`` is still the fallback when a caller supplies no explicit
``pages`` — see ``parse_page_range`` / ``run_staged_omr``'s own ``pages``
argument for the whole-movement path this route now also accepts.

ROADMAP 3.3's job budget (the "page cap → job budget" item): a request for
an explicit page RANGE is priced with ``tools.omr.staged.budget.
estimate_job_budget_s`` (the ONE place those per-page constants live —
CLAUDE.md §5b, ROADMAP 1.2b) BEFORE the job starts, and ``backend/main.py``
refuses a request whose estimate exceeds ``settings.omr_job_budget_s`` up
front rather than starting a job that would run for hours and then be
silently capped. ``parse_page_range`` / ``estimate_budget_s`` below are thin
wrappers so ``main.py`` never has to reach past this module into
``tools.omr.staged`` directly — the same layering ``run_staged_omr`` itself
already keeps.

⚠️ WEIGHT ROUTING is ``staged/weight_routing.py:resolve_staged_weights`` —
the SAME call the staged CLI makes under ``--route-weights`` — never a
re-implementation of the legacy picking logic (that port is roadmap 3.2's
job, not this one's). ``OMR_WEIGHTS_PATH`` unset routes by input domain,
mirroring ``local_omr``'s own default (legacy ``transcribe()`` routes on a
bare ``None``); set, it pins exactly as it always has and no classification
runs.

⚠️ NO ``--dossier`` EQUIVALENT, and there will not be one — CLAUDE.md §4c /
§5b: a dossier reaches the staged pipeline only through a human-confirmed
fact sheet (``--sheet``), which the web upload flow has no way to supply.
The roster lookup mirrors the CLI's own default (``roster_for_pdf``
abstains — returns ``None`` — for any PDF the catalog does not hold, which
is every web upload today, so it is a no-op here and kept for parity rather
than because it does anything yet).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Same two-layout resolution as local_omr.py / export_module.py: Docker
# flattens backend/ to /app, dev runs from the repo checkout.
def _find_omr_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[1], here.parents[2]):
        if (candidate / "tools" / "omr").is_dir():
            return candidate
    return here.parents[2]  # last-resort fallback


_REPO_ROOT = _find_omr_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ⚠️ THE SAME ENV-READING HELPERS `local_omr` USES — imported, never
# restated (CLAUDE.md rule 9: no new flags, and a copy here would be a
# second place these five names could drift apart).
from modules.local_omr import (  # noqa: E402
    _conf_threshold,
    _dpi,
    _imgsz,
    _max_pages,
    _weights_path,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StagedOmrResult:
    """Mirrors ``local_omr.LocalOmrResult`` so the caller in ``main.py`` can
    branch on ``omr_engine`` with a similar shape on both sides.

    ``held_out_staves``, ``unread_bars`` and ``status_census`` are read
    straight off ``staged.export.to_musicxml``'s own coverage report — never
    recomputed — so the web app's accounting can never disagree with the
    exporter's about what it did not write.
    """
    musicxml_path: str
    record_path: str
    pages_processed: int = 0
    runtime_seconds: float = 0.0
    held_out_staves: Optional[int] = None
    unread_bars: Optional[int] = None
    status_census: Optional[dict] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Page range / job budget (ROADMAP 3.3, second half)
# ---------------------------------------------------------------------------


def parse_page_range(pages: str) -> List[int]:
    """Parse a `pages` query param ("0-26", "0,2,4-6") into a page list.

    ⚠️ REUSES `tools.omr.staged.__main__.parse_pages` — the SAME parser the
    staged CLI's own `--pages` and `gather_movement.sh` use — rather than a
    second, web-only spelling of "what does a page range string mean" that
    could silently disagree with the CLI's. Raises `ValueError` on a
    malformed string; `backend/main.py` turns that into a 400.
    """
    from tools.omr.staged.__main__ import parse_pages
    return parse_pages(pages)


def estimate_budget_s(n_pages: int, *,
                      direction_text_scan_gate: bool = True) -> Dict[str, Any]:
    """The same per-page time estimate `gather_movement.sh` prints
    (ROADMAP 1.2b) — `tools.omr.staged.budget.estimate_job_budget_s`,
    imported rather than restated, so the CLI script and this web job can
    never quote two different numbers for one page count. See that
    module's docstring for why the post-GATHER half is an UPPER BOUND, not
    a measurement.
    """
    from tools.omr.staged.budget import estimate_job_budget_s
    return estimate_job_budget_s(
        n_pages, direction_text_scan_gate=direction_text_scan_gate)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_staged_omr(pdf_path: str, output_dir: str,
                         pages: Optional[List[int]] = None) -> StagedOmrResult:
    """Run the staged pipeline on `pdf_path` and write the pooled record +
    a MusicXML file to `output_dir`.

    `pages`, when given, is the EXACT page list to gather (ROADMAP 3.3's
    whole-movement job, priced by the caller with `estimate_budget_s`
    BEFORE this is called) — it overrides `OMR_MAX_PAGES` entirely rather
    than being clamped by it, since a caller that already paid for the
    budget check gets the range it asked for. `None` (no `pages` query
    param — the pre-3.3-second-half behaviour) keeps reading the first
    `OMR_MAX_PAGES` pages, unchanged.

    Heavy compute runs in a thread, matching ``run_local_omr``.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if not os.path.isfile(pdf_path):
        return StagedOmrResult(
            musicxml_path="",
            record_path="",
            error_message=f"PDF not found at {pdf_path}",
        )

    try:
        result = await asyncio.to_thread(
            _run_staged_blocking,
            pdf_path=pdf_path,
            output_dir=output_dir,
            weights=_weights_path(),
            max_pages=_max_pages(),
            pages=pages,
            conf_threshold=_conf_threshold(),
            imgsz=_imgsz(),
            dpi=_dpi(),
        )
        return result
    except Exception as exc:
        # ⚠️ INCLUDES `tools.omr.staged.export.Unbalanced` — see module
        # docstring. Caught here exactly like any other worker failure and
        # reported with its own message; never swallowed into a partial
        # "success" with an empty or truncated file.
        logger.exception("Staged OMR failed for %s", pdf_path)
        return StagedOmrResult(
            musicxml_path="",
            record_path="",
            error_message=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Blocking worker (called via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _run_staged_blocking(
    *,
    pdf_path: str,
    output_dir: str,
    weights: str | None,
    max_pages: int,
    conf_threshold: float,
    imgsz: int | None,
    dpi: int,
    pages: Optional[List[int]] = None,
) -> StagedOmrResult:
    import fitz  # PyMuPDF

    from tools.omr.staged import export as staged_export
    from tools.omr.staged import pipeline as staged_pipeline
    from tools.omr.staged import record_io
    from tools.omr.staged import weight_routing as staged_weight_routing

    doc = fitz.open(pdf_path)
    n_pages = doc.page_count
    doc.close()

    # ⚠️ ROADMAP 3.3, second half: an EXPLICIT `pages` list — already priced
    # against the job budget by `backend/main.py` before this thread was
    # even started — overrides `OMR_MAX_PAGES` entirely, rather than being
    # clamped by it: a caller that asked for (and was approved for) pages
    # 0-26 gets 0-26, not whatever OMR_MAX_PAGES happens to be set to today.
    # `None` (no `pages` query param) keeps the pre-3.3-second-half cap,
    # byte-identical to before.
    if pages is not None:
        requested = list(pages)
        page_list = [p for p in requested if 0 <= p < n_pages]
    else:
        requested = None
        page_list = list(range(min(n_pages, max_pages)))

    if not page_list:
        if n_pages == 0:
            msg = f"PDF has no pages: {pdf_path}"
        else:
            msg = (f"none of the requested pages {requested} fall within "
                  f"{pdf_path}'s {n_pages} pages")
        return StagedOmrResult(musicxml_path="", record_path="",
                               error_message=msg)
    pages = page_list

    # ⚠️ THE SAME CALL THE STAGED CLI MAKES under --route-weights
    # (tools/omr/staged/__main__.py). An explicit OMR_WEIGHTS_PATH pins (no
    # classification runs, exactly as `--weights <path>` always has); its
    # absence routes by input domain — mirroring `local_omr`'s own default,
    # where a bare `None` lets legacy `transcribe()` route. Never the legacy
    # picking logic re-implemented (that is roadmap 3.2's job).
    weights_path, weight_routing, input_domain_classification = (
        staged_weight_routing.resolve_staged_weights(
            pdf_path, pages,
            weights=(weights if weights else "auto"),
            route_weights=True))

    detector = None
    if weights_path:
        from tools.omr.yolo_detector import YoloDetector
        detector = YoloDetector(weights_path)

    logger.info(
        "staged_omr: %s -> %d pages, weights=%s, conf=%.2f, imgsz=%s, dpi=%d",
        Path(pdf_path).name, len(pages),
        Path(weights_path).name if weights_path else "none (no detector)",
        conf_threshold, imgsz if imgsz else "per-cell", dpi,
    )

    # ⚠️ Roster lookup mirrors the CLI's own default (no `--no-roster`
    # passed): `roster_for_pdf` abstains (returns None) for any PDF the
    # catalog does not hold, which is every web upload today, so this is a
    # no-op in practice and kept only for parity with the product path's
    # own default. No dossier — see module docstring.
    from tools.omr.work_roster import roster_for_pdf
    roster = roster_for_pdf(pdf_path)

    result = staged_pipeline.run_staged(
        pdf_path, pages, detector=detector, dpi=dpi,
        conf_threshold=conf_threshold, imgsz=imgsz, roster=roster,
        dossier=None,
        input_domain_classification=input_domain_classification,
        progress=False)
    result["weight_routing"] = weight_routing

    pdf_stem = Path(pdf_path).stem

    # ⚠️ THE POOLED WRITER (roadmap 1.1b), the same one `--out` uses on the
    # CLI — never a bare `json.dump`. A record read back must go through
    # `record_io.load_record` (see `export_module.export_as_lilypond`).
    record_path = os.path.join(output_dir, f"{pdf_stem}.record.json")
    Path(record_path).write_text(
        record_io.dumps_for_file(result, separators=(",", ":"), default=str))

    musicxml_path = os.path.join(output_dir, f"{pdf_stem}.musicxml")
    # ⚠️⚠️ `to_musicxml` RAISES `Unbalanced` RATHER THAN RETURNING A FLAG
    # (tools/omr/staged/export.py). Deliberately NOT caught here — it
    # propagates to `run_staged_omr`'s own try/except, which reports it as a
    # job error. Catching it here to "at least write something" would be the
    # exact CANNOT-TELL-into-an-answer conversion CLAUDE.md rule 8 forbids.
    xml, report = staged_export.to_musicxml(result)
    Path(musicxml_path).write_text(xml)

    part_join = report.get("part_join") or {}
    bars_held = report.get("bars_held_out_sum") or {}

    return StagedOmrResult(
        musicxml_path=musicxml_path,
        record_path=record_path,
        pages_processed=len(pages),
        held_out_staves=part_join.get("held_out_staves"),
        unread_bars=bars_held.get("bars"),
        status_census=report.get("status_census"),
    )
