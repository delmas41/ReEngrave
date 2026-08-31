"""OMR-NED worker — runs INSIDE the musicdiff venv, not in the repo's Python.

`musicdiff` requires Python >= 3.10 and music21 >= 9.9.1; this repo's host
interpreter is 3.9 with music21 8.3.0, and the backend image pins its own
music21. Upgrading the repo to suit a benchmark would be the tail wagging the
dog, so the metric runs out-of-process in its own venv and talks JSON, the same
shape `maestro_bridge.py` uses to reach node.

NOTHING IN THE REPO MAY IMPORT THIS MODULE. It is executed as a standalone
script by an interpreter that has musicdiff but does NOT have this project's
dependencies on its path. Keep it free of `tools.*` imports.

Protocol — one JSON job on stdin, one JSON result on stdout:

    {"detail": "AllObjects",
     "pairs": [{"name": "beethoven-sym5-mvt1",
                "pred":  "/abs/path/to/omr.musicxml",
                "truth": "/abs/path/to/truth.musicxml"}]}

WHY `diff_ml_training` AND NOT THE ONE-SHOT `diff()`. Only the batch entry
point exposes the per-category breakdown (`wrong clef OMR-ED`, `wrong note
OMR-ED`, ...), which is the entire reason to adopt this metric over the
project's existing note recall — a single scalar says the page is wrong, the
breakdown says the clefs are. `diff()`'s `print_omr_ned_output=True` prints
five scalars and no categories. `diff_ml_training` also computes the corpus
aggregate the way the Sheet Music Benchmark paper does — POOLED, one edit-count
sum over one symbol-count sum, not a mean of per-work scores.

It matches predicted to ground truth BY IDENTICAL FILENAME, so each pair is
staged into a private temp directory under a shared, sanitised name. Sanitised
because musicdiff writes its CSV by joining on ", " with no quoting, so a comma
anywhere in a path would silently shift every column right.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

# music21 reads the format off the extension, and a staged pair must share one
# filename, hence one extension. Anything outside this set is converted to
# MusicXML on the way in, and the conversion is reported so a reader can tell
# a native comparison from a laundered one.
_NATIVE_SUFFIXES = {".musicxml", ".xml"}

_TAIL_COLUMNS = {
    "gt numsyms": "truth_symbols",
    "pred numsyms": "pred_symbols",
    "total numsyms (in both scores)": "total_symbols",
    "OMR-ED (OMR Edit Distance)": "omr_ed",
    "OMR-NED (OMR-ED / total numsyms)": "omr_ned",
}


def _safe_stem(name: str) -> str:
    """A filename that cannot break musicdiff's unquoted ", "-joined CSV."""
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in name]
    return "".join(keep).strip("-") or "score"


def _stage(pair: dict, index: int, pred_dir: Path, truth_dir: Path) -> dict:
    """Copy one (pred, truth) pair into the staging dirs under a shared name."""
    from music21 import converter  # noqa: PLC0415 — venv-only import

    pred = Path(pair["pred"])
    truth = Path(pair["truth"])
    for role, path in (("pred", pred), ("truth", truth)):
        if not path.is_file():
            raise FileNotFoundError(f"{role} file missing: {path}")

    # A pair must share one extension. Prefer leaving both untouched.
    converted = []
    suffixes = {pred.suffix.lower(), truth.suffix.lower()}
    if len(suffixes) == 1 and suffixes <= _NATIVE_SUFFIXES:
        suffix = pred.suffix
    else:
        suffix = ".musicxml"

    stem = f"{index:03d}-{_safe_stem(pair['name'])}"
    staged = {}
    for role, path, out_dir in (("pred", pred, pred_dir),
                                ("truth", truth, truth_dir)):
        dest = out_dir / f"{stem}{suffix}"
        if path.suffix.lower() == suffix.lower():
            shutil.copyfile(path, dest)
        else:
            # NOTE: re-writing through music21 launders syntax errors. musicdiff
            # deliberately parses the prediction leniently and the truth
            # strictly, and a conversion here erases that distinction, so say so.
            converter.parse(str(path)).write("musicxml", fp=str(dest))
            converted.append(role)
        staged[role] = dest
    return {"stem": stem, "converted": converted, **staged}


def _parse_csv(csv_path: Path) -> tuple[list[dict], dict]:
    """Read musicdiff's output.csv into per-pair rows and the Total: row.

    The file is header / one line per pair / `Total:` / the header again. Cells
    are joined with ", " and never quoted, which is why staged names are
    sanitised. Category columns come in pairs — `X OMR-ED` carries the count
    and `X % contribution to OMR-NED` the share — and only the counts are kept;
    the percentages are recoverable and would double the payload.
    """
    lines = [ln for ln in csv_path.read_text().splitlines() if ln.strip()]
    if not lines:
        return [], {}
    header = [c.strip() for c in lines[0].split(",")]

    def row_to_dict(cells: list[str]) -> dict:
        out: dict = {"categories": {}}
        for name, raw in zip(header, cells):
            value = raw.strip()
            if name in _TAIL_COLUMNS:
                key = _TAIL_COLUMNS[name]
                out[key] = float(value) if key == "omr_ned" else int(value)
            elif name.endswith(" OMR-ED") and name != "OMR-ED (OMR Edit Distance)":
                count = int(value)
                if count:  # only non-zero categories — 40 zeros help nobody
                    out["categories"][name[: -len(" OMR-ED")]] = count
            elif name == "gtpath":
                out["truth_staged"] = value
            elif name == "predpath":
                out["pred_staged"] = value
        return out

    rows, total = [], {}
    for line in lines[1:]:
        cells = [c.strip() for c in line.split(",")]
        # musicdiff repeats the header as a footer, and its first cell is EMPTY
        # (the spacer column that holds "Total:"), so testing cells[0] does not
        # catch it — compare the whole row against the header instead.
        if cells == header:
            continue
        if cells and cells[0].startswith("Total:"):
            total = row_to_dict(cells)
            continue
        if len(cells) < len(header) // 2:
            continue
        rows.append(row_to_dict(cells))
    return rows, total


def main() -> int:
    job = json.load(sys.stdin)
    pairs = job.get("pairs") or []
    if not pairs:
        json.dump({"error": "no pairs supplied"}, sys.stdout)
        return 2

    from musicdiff import DetailLevel, diff_ml_training  # noqa: PLC0415

    detail_name = job.get("detail") or "AllObjects"
    try:
        detail = getattr(DetailLevel, detail_name)
    except AttributeError:
        json.dump({"error": f"unknown detail level {detail_name!r}"}, sys.stdout)
        return 2

    with tempfile.TemporaryDirectory(prefix="omrned-") as tmp:
        tmp_path = Path(tmp)
        pred_dir = tmp_path / "pred"
        truth_dir = tmp_path / "truth"
        out_dir = tmp_path / "out"
        for d in (pred_dir, truth_dir, out_dir):
            d.mkdir()

        staged = [_stage(p, i, pred_dir, truth_dir) for i, p in enumerate(pairs)]
        by_stem = {s["stem"]: (pairs[i], s) for i, s in enumerate(staged)}

        overall, csv_path = diff_ml_training(
            str(pred_dir), str(truth_dir), str(out_dir), detail=detail,
        )
        rows, total = _parse_csv(Path(csv_path))
        csv_text = Path(csv_path).read_text()

    # Re-attach each row to the caller's own name for the pair. musicdiff sorts
    # its output by score, so row order is NOT input order — match on the stem.
    results = []
    for row in rows:
        stem = Path(row.get("truth_staged", "")).stem
        original, staged_info = by_stem.get(stem, ({}, {}))
        entry = {
            "name": original.get("name", stem),
            "pred": original.get("pred"),
            "truth": original.get("truth"),
            "omr_ned": row.get("omr_ned"),
            "omr_ed": row.get("omr_ed"),
            "pred_symbols": row.get("pred_symbols"),
            "truth_symbols": row.get("truth_symbols"),
            "categories": row.get("categories", {}),
        }
        if staged_info.get("converted"):
            entry["converted_to_musicxml"] = staged_info["converted"]
        results.append(entry)

    json.dump(
        {
            "detail": detail_name,
            "overall_omr_ned": overall,
            "overall_omr_ed": total.get("omr_ed"),
            "overall_pred_symbols": total.get("pred_symbols"),
            "overall_truth_symbols": total.get("truth_symbols"),
            "overall_categories": total.get("categories", {}),
            "n_scored": len(results),
            "n_requested": len(pairs),
            "pairs": results,
            "csv": csv_text,
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
