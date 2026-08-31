"""OMR-NED — the first metric in this repo that is comparable to anyone else's.

Every accuracy number this project has ever reported is bespoke: F1 over a
25-cell verdict set, pitch recall against an authored fixture, clef accuracy
over 52 hand-read staves. Each is valid for the question it was built to
answer, and none of them can be compared to a published result, so "how good is
this pipeline" has never had an answer with an outside reference point.

OMR-NED (Martinez-Sevilla et al., *Sheet Music Benchmark*, ISMIR 2025,
arXiv:2506.10488) is the standard that OMR papers now report. It is an edit
distance over musical symbols, normalised by how many symbols the two scores
contain between them:

    OMR-NED = (insertions + deletions) / (symbols_pred + symbols_truth)

LOWER IS BETTER; 0.0 is identity and 1.0 is total disagreement. For scale, the
LEGATO 2 paper (arXiv:2607.05769) reports on rendered OpenScore string quartets:
LEGATO 2 17.1, LEGATO 1 32.9, Audiveris 64.6, Gemini 3.1 Pro 93.5 (all ×100).

TWO PROPERTIES WORTH KNOWING BEFORE READING A NUMBER.

  It is SYMMETRIC in the score. The denominator sums both sides and swapping
  prediction for truth swaps insertions with deletions, so the total is
  unchanged. Passing the arguments backwards will therefore NOT produce an
  obviously wrong figure — what it changes is that musicdiff parses the truth
  strictly and the prediction leniently, so a swap silently accepts a malformed
  ground truth. Hence the keyword-only arguments here.

  It is POOLED across a corpus, not averaged. `overall_omr_ned` is one edit-sum
  over one symbol-sum, so a dense Mahler page counts for more than a sparse one
  — deliberately, and the same way the paper does it. The per-work scores are
  reported alongside precisely because the pooled figure hides them.

WHAT IT DOES NOT MEASURE. It compares two scores, so it inherits whatever the
exporter did. `export.to_musicxml` emits one `<part>` per (page, system, staff),
which is not the same part structure as a Gradus truth file, and that
disagreement is real notation difference that OMR-NED will charge for. It is a
recognition-plus-export number, not a detector number. Read it next to the
existing note recall rather than instead of it.

RUNNING OUT OF PROCESS. musicdiff needs Python >= 3.10 and music21 >= 9.9.1;
the host runs 3.9 with music21 8.3.0. Rather than move the whole project for a
benchmark, the metric lives in its own venv and is reached by subprocess, the
same shape `backend/modules/maestro_bridge.py` uses for node.

    python3 -m tools.omr.omr_ned --bootstrap          # one-time, makes the venv
    python3 -m tools.omr.omr_ned pred.musicxml truth.musicxml
    python3 -m tools.omr.omr_ned --batch pairs.json --out scores.json

From Python:

    from tools.omr.omr_ned import score_pair
    result = score_pair(pred=omr_xml, truth=truth_xml)
    print(result["omr_ned"], result["categories"])
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKER = Path(__file__).resolve().parent / "_omrned_worker.py"

#: Where `--bootstrap` puts the venv, and where the bridge looks for it.
VENV_DIR = _REPO_ROOT / ".venv-omrned"

#: musicdiff 5.2 (Feb 2026) is the first release carrying the SMB paper's
#: OMR-NED output. Pinned below 6 because the CSV column layout parsed by the
#: worker is an output format, not an API contract.
MUSICDIFF_REQUIREMENT = "musicdiff>=5.2,<6"

#: Dense orchestral pairs are the slow case; a quartet is a second or two.
DEFAULT_TIMEOUT_S = float(os.environ.get("OMRNED_TIMEOUT_S", "600"))

#: musicdiff's own default. `NotesAndRests` scores pitch and rhythm alone,
#: which is the closer comparison to this repo's existing note recall.
DEFAULT_DETAIL = "AllObjects"


class OmrNedError(RuntimeError):
    """The metric could not be computed — bad input, or the venv is missing."""


def _candidate_interpreters() -> Iterable[Path]:
    override = os.environ.get("OMRNED_PYTHON")
    if override:
        yield Path(override)
    yield VENV_DIR / "bin" / "python"


def interpreter() -> Path:
    """The Python that has musicdiff, or an error saying how to make one."""
    for candidate in _candidate_interpreters():
        if candidate.is_file():
            return candidate
    raise OmrNedError(
        "no musicdiff interpreter found.\n"
        f"  expected: {VENV_DIR / 'bin' / 'python'}\n"
        "  create it with: python3 -m tools.omr.omr_ned --bootstrap\n"
        "  or point OMRNED_PYTHON at a Python >= 3.10 that has "
        f"{MUSICDIFF_REQUIREMENT!r} installed."
    )


def available() -> bool:
    """True when the metric can run — for callers that degrade rather than fail."""
    try:
        interpreter()
    except OmrNedError:
        return False
    return True


def _base_python_for_venv() -> str:
    """Highest Python >= 3.10 on PATH. musicdiff refuses to install below it."""
    for minor in range(14, 9, -1):
        found = shutil.which(f"python3.{minor}")
        if found:
            return found
    # A 3.10+ default `python3` is plausible on a newer host.
    default = shutil.which("python3")
    if default:
        out = subprocess.run([default, "-c",
                              "import sys; print(sys.version_info[:2])"],
                             capture_output=True, text=True)
        if out.returncode == 0 and "3, 9" not in out.stdout:
            return default
    raise OmrNedError(
        "no Python >= 3.10 found on PATH; musicdiff requires it "
        "(the host's python3 is 3.9). Install one, e.g. `brew install python@3.13`."
    )


def bootstrap(*, force: bool = False) -> Path:
    """Create `.venv-omrned` and install musicdiff into it. Returns the python."""
    python = VENV_DIR / "bin" / "python"
    if python.is_file() and not force:
        return python
    base = _base_python_for_venv()
    subprocess.run([base, "-m", "venv", str(VENV_DIR)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--quiet",
                    "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--quiet",
                    MUSICDIFF_REQUIREMENT], check=True)
    return python


def _run(job: dict, *, timeout_s: float | None = None) -> dict[str, Any]:
    python = interpreter()
    try:
        proc = subprocess.run(
            [str(python), str(_WORKER)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            timeout=timeout_s if timeout_s is not None else DEFAULT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise OmrNedError(f"musicdiff timed out after {exc.timeout}s") from exc

    if proc.returncode != 0 and not proc.stdout.strip():
        raise OmrNedError(
            f"musicdiff worker failed (exit {proc.returncode}):\n"
            f"{proc.stderr.strip()[-2000:]}"
        )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise OmrNedError(
            "musicdiff worker returned non-JSON:\n"
            f"stdout: {proc.stdout.strip()[:500]}\n"
            f"stderr: {proc.stderr.strip()[-1000:]}"
        ) from exc
    if "error" in result:
        raise OmrNedError(result["error"])
    # music21 is chatty on stderr; keep it, but only when something was scored
    # oddly, so a clean run stays quiet.
    if result.get("n_scored", 0) < result.get("n_requested", 0):
        result["worker_stderr"] = proc.stderr.strip()[-2000:]
    return result


def score_batch(
    pairs: Sequence[tuple],
    *,
    detail: str = DEFAULT_DETAIL,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Score many (name, pred, truth) triples in one musicdiff run.

    One subprocess for the whole batch, both because the interpreter start and
    the converter21 registration are per-process costs, and because the pooled
    `overall_omr_ned` is only meaningful when computed over the whole set.
    """
    job_pairs = []
    for entry in pairs:
        name, pred, truth = entry
        job_pairs.append({
            "name": str(name),
            "pred": str(Path(pred).resolve()),
            "truth": str(Path(truth).resolve()),
        })
    if not job_pairs:
        raise OmrNedError("score_batch called with no pairs")
    return _run({"detail": detail, "pairs": job_pairs}, timeout_s=timeout_s)


def score_pair(
    *,
    pred: str | os.PathLike,
    truth: str | os.PathLike,
    name: str | None = None,
    detail: str = DEFAULT_DETAIL,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Score one prediction against one ground truth.

    Keyword-only on purpose: the metric is symmetric, so swapping these does
    not produce a visibly wrong number (see the module docstring).
    """
    label = name or Path(pred).stem
    result = score_batch([(label, pred, truth)], detail=detail,
                         timeout_s=timeout_s)
    scored = result.get("pairs") or []
    if not scored:
        raise OmrNedError(
            "musicdiff scored nothing — most often the ground truth has no "
            "parts, or a file is not in a format music21 reads.\n"
            + result.get("worker_stderr", "")
        )
    return scored[0]


def format_report(result: dict[str, Any], *, top_categories: int = 6) -> str:
    """A short text report: the pooled score, then per-work, then what dominates."""
    lines = []
    overall = result.get("overall_omr_ned")
    if overall is not None:
        lines.append(
            f"OMR-NED (pooled over {result.get('n_scored', 0)} scores): "
            f"{overall:.4f}   [lower is better; 0 = identical]"
        )
        lines.append(
            f"  {result.get('overall_omr_ed')} symbol edits over "
            f"{result.get('overall_truth_symbols')} truth + "
            f"{result.get('overall_pred_symbols')} predicted symbols"
        )
    lines.append("")
    lines.append(f"{'work':30s} {'OMR-NED':>8s} {'edits':>7s} "
                 f"{'truth':>7s} {'pred':>7s}  dominant error")
    for pair in result.get("pairs", []):
        cats = pair.get("categories") or {}
        top = max(cats.items(), key=lambda kv: kv[1])[0] if cats else "-"
        lines.append(
            f"{pair['name'][:30]:30s} {pair['omr_ned']:>8.4f} "
            f"{pair['omr_ed']:>7d} {pair['truth_symbols']:>7d} "
            f"{pair['pred_symbols']:>7d}  {top}"
        )
    overall_cats = result.get("overall_categories") or {}
    if overall_cats:
        lines.append("")
        lines.append("where the edits are (pooled):")
        total = sum(overall_cats.values()) or 1
        ranked = sorted(overall_cats.items(), key=lambda kv: -kv[1])
        for cat, count in ranked[:top_categories]:
            lines.append(f"  {cat:38s} {count:>7d}  {100.0 * count / total:5.1f}%")
        if len(ranked) > top_categories:
            rest = sum(c for _, c in ranked[top_categories:])
            lines.append(f"  {'(' + str(len(ranked) - top_categories) + ' more)':38s} "
                         f"{rest:>7d}  {100.0 * rest / total:5.1f}%")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pred", nargs="?", type=Path,
                    help="the PREDICTED score (the pipeline's output)")
    ap.add_argument("truth", nargs="?", type=Path,
                    help="the GROUND TRUTH score")
    ap.add_argument("--batch", type=Path, default=None,
                    help='JSON list of {"name","pred","truth"} objects')
    ap.add_argument("--detail", default=DEFAULT_DETAIL,
                    help=f"musicdiff DetailLevel (default {DEFAULT_DETAIL}); "
                         "NotesAndRests scores pitch and rhythm only")
    ap.add_argument("--out", type=Path, default=None,
                    help="write the full result JSON here")
    ap.add_argument("--csv", type=Path, default=None,
                    help="write musicdiff's own output.csv here")
    ap.add_argument("--bootstrap", action="store_true",
                    help="create .venv-omrned and install musicdiff, then exit")
    ap.add_argument("--force", action="store_true",
                    help="with --bootstrap, rebuild an existing venv")
    args = ap.parse_args(argv)

    if args.bootstrap:
        python = bootstrap(force=args.force)
        print(f"musicdiff venv ready: {python}")
        return 0

    if args.batch:
        entries = json.loads(args.batch.read_text())
        pairs = [(e.get("name") or Path(e["pred"]).stem, e["pred"], e["truth"])
                 for e in entries]
    elif args.pred and args.truth:
        pairs = [(args.pred.stem, args.pred, args.truth)]
    else:
        ap.error("give PRED and TRUTH, or --batch pairs.json, or --bootstrap")

    try:
        result = score_batch(pairs, detail=args.detail)
    except OmrNedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(format_report(result))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in result.items() if k != "csv"}
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    if args.csv and result.get("csv"):
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        args.csv.write_text(result["csv"])
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
