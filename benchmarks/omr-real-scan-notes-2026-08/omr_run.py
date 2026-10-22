"""One pipeline run per page, shared by `build_truth.py` and `score.py`.

The truth builder needs the pipeline's Phase 1 for its tripwire and the scorer
needs the pipeline's notes, and running `transcribe` twice on the same page
would not merely be slow — it would let the two halves disagree about which run
they are talking about. So the run is cached on disk and both read the same
file.

`--fresh` re-runs. Anything that changes the pipeline's output changes what the
tripwire is asserting against, so re-run after a pipeline change rather than
scoring a new build against an old Phase 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNS = HERE / "pipeline-runs"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def run_path(page_id: str) -> Path:
    return RUNS / f"{page_id}.omr.json"


def load_or_run(cfg: dict[str, Any], *, weights: Path, fresh: bool = False,
                dpi: int | None = None) -> tuple[dict[str, Any], Path, bool]:
    """Return `(result, path, was_cached)` for this page's pipeline run."""
    path = run_path(cfg["id"])
    if path.is_file() and not fresh:
        return json.loads(path.read_text()), path, True

    from tools.omr.transcribe import transcribe

    pdf = Path(cfg["pdf"])
    if not pdf.is_file():
        raise SystemExit(f"PDF not on this machine: {pdf}")
    if not Path(weights).is_file():
        raise SystemExit(f"weights not found: {weights}")

    result = transcribe(
        pdf_path=pdf,
        pages=[cfg["page_index"]],
        weights=str(weights),
        dpi=cfg["dpi"] if dpi is None else dpi,
        progress=False,
    )
    RUNS.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result))
    return result, path, False


def layout(result: dict[str, Any]) -> list[list[int]]:
    """Per system, the measure count of each staff — what Phase 1 reports."""
    page = result["pages"][0]
    return [[len(st.get("measures", [])) for st in sys_.get("staves", [])]
            for sys_ in page.get("systems", [])]
