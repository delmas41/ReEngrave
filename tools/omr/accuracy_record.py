"""The current accuracy figure, held once and written into the docs mechanically.

WHY THIS EXISTS. The pooled OMR-NED figure was stated in the present tense in
six places across four files, by hand. On 2026-09-01 two branches landed within
an hour, each having edited a DIFFERENT copy of it. The merge produced exactly
one conflict — CLAUDE.md — which forced a resolution, and the resolver
re-measured on the merge and got it right. The other three files did not
collide, git merged both sides cleanly, and five figures survived describing one
branch rather than main.

    The file that CONFLICTED came out correct.
    The files that merged silently came out wrong.

A conflict is loud and gets a measurement. A clean auto-merge of one fact held
in several places is silent, and the copy that loses is whichever file happened
not to collide. No amount of care at the keyboard fixes that, because the
mistake is not made at the keyboard.

TWO HALVES, AND `68be549` DID THE BIGGER ONE. That commit deleted the
duplication: the figure is stated in exactly one place now, CLAUDE.md's OMR-NED
section, and NOTES.md, PROJECT_STATUS.md and next-steps point at it instead of
restating it. Three copies that cannot exist cannot go stale — eliminating the
problem beats automating it, and nothing here tries to reinstate them.

What that leaves is the remaining copy, which is still hand-typed: measure,
forget to edit CLAUDE.md, and it goes quietly wrong with no second copy to
disagree with it. This closes that. One JSON file (`RECORD_PATH`) holds the
measurement, and the surviving statement is wrapped in markers:

    <!-- accuracy:begin name=headline -->
    ...generated text...
    <!-- accuracy:end -->

`--update` rewrites the block from the JSON; `--check` reports drift and exits
non-zero, and `tools/omr/tests/test_accuracy_record.py` runs it. So the one
surviving figure cannot diverge from the measurement without a test going red.

    python3 -m tools.omr.training.orchestral_eval --omr-ned --record   # measure + record
    python3 -m tools.omr.accuracy_record --check                        # drift?
    python3 -m tools.omr.accuracy_record --update                       # rewrite blocks

WHAT IS AND IS NOT MANAGED HERE. Only the PRESENT-TENSE figure. A historical
transition — "pooled 0.2595 → 0.2489" against the commit that did it — is a
frozen fact about the past, belongs in whatever narrative it explains, and must
never be rewritten by this. The distinction is the whole design: history is
written once and stays; the present is measured and propagated.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]

#: The single source. Written by `orchestral_eval --record`.
RECORD_PATH = ROOT / "benchmarks" / "omr-ned-2026-08" / "current-accuracy.json"

#: The opening measurement, quoted alongside the current one to give it scale.
#: A historical constant, not part of the record.
OPENING_POOLED = "0.3164"

_BEGIN = re.compile(r"<!--\s*accuracy:begin\s+name=([a-z0-9_-]+)\s*-->")
_END = "<!-- accuracy:end -->"


def _fmt(value: float, places: int = 4) -> str:
    return f"{value:.{places}f}"


#: The configurations the benchmark is quoted for. `--direction-text` is off by
#: default and needs `.venv-surya`, so it is measured separately and recorded
#: separately — one run cannot produce both, and a record that let one clobber
#: the other would silently restate a figure for the wrong configuration.
DEFAULT_RUN = "default"
DIRECTION_TEXT_RUN = "direction_text"


def _run(record: dict[str, Any], name: str) -> dict[str, Any] | None:
    return (record.get("runs") or {}).get(name)


def _short(work_id: str) -> str:
    return work_id.split("-")[0].capitalize()


def _works_phrase(run: dict[str, Any]) -> str:
    """`Mahler 0.0455, Beethoven 0.1649, Brahms 0.1709`, in ascending order."""
    works = sorted(run.get("works", []), key=lambda w: w["omr_ned"])
    return ", ".join(f"{_short(w['work_id'])} {_fmt(w['omr_ned'])}" for w in works)


# ---------------------------------------------------------------------------
# The one statement
# ---------------------------------------------------------------------------
#
# There is exactly one block because `68be549` left exactly one copy of the
# figure. If a second document ever needs the number again, the answer is a
# pointer to this one — not a second block. The registry stays a dict so that
# is a deliberate act rather than a copy-paste.


def _headline(record: dict[str, Any]) -> str:
    """The paragraph CLAUDE.md's OMR-NED section opens with.

    Every present-tense number in it is generated, including the per-work rows.
    The line they replace read "Beethoven's note row is 81/81, recall and
    precision 1.000" — exactly the kind of sentence that survives three fixes
    after it stops being true.
    """
    run = _run(record, DEFAULT_RUN)
    if run is None:
        raise ValueError("the record has no default run")
    rows = "\n".join(
        f"| {_short(w['work_id'])} | {_fmt(w['omr_ned'])} | {w['edits']} | "
        f"{_fmt(w['pitch_recall'], 3)} | {_fmt(w['pitch_precision'], 3)} | "
        f"{_fmt(w['duration_rate'], 3)} |"
        for w in sorted(run["works"], key=lambda w: w["omr_ned"])
    )
    variant = _run(record, DIRECTION_TEXT_RUN)
    variant_clause = ""
    if variant:
        variant_clause = (
            f" With `--direction-text` (off by default, needs `.venv-surya`), "
            f"**{_fmt(variant['pooled'])} / {variant['edits']}**, measured on "
            f"`{variant['commit']}`."
        )
    return (
        f"Current on the engraved orchestral benchmark, measured on "
        f"`{run['commit']}`: **pooled {_fmt(run['pooled'])} / {run['edits']} "
        f"edits** ({_works_phrase(run)}), over {run['truth_symbols']} truth + "
        f"{run['pred_symbols']} predicted symbols, from an opening baseline of "
        f"{OPENING_POOLED} on 2026-08-31.{variant_clause}\n\n"
        "| work | OMR-NED | edits | note recall | precision | duration rate |\n"
        "|---|--:|--:|--:|--:|--:|\n" + rows
    )


#: name -> (file, renderer).
BLOCKS: dict[str, tuple[str, Callable[[dict[str, Any]], str]]] = {
    "headline": ("CLAUDE.md", _headline),
}


def load_record(path: Path | None = None) -> dict[str, Any]:
    path = path or RECORD_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"no accuracy record at {path} — run "
            "`python3 -m tools.omr.training.orchestral_eval --omr-ned --record`"
        )
    return json.loads(path.read_text())


def record_from_results(results: list[dict[str, Any]],
                        run_name: str = DEFAULT_RUN,
                        previous: dict[str, Any] | None = None,
                        commit: str | None = None) -> dict[str, Any]:
    """Fold one measured run into the record, leaving the other runs alone.

    Raises when a work has no OMR-NED score: a partial record is worse than no
    record, because the docs would state a pooled figure over a subset without
    saying so.
    """
    works = []
    for r in results:
        scored = r.get("omr_ned")
        if not scored:
            raise ValueError(
                f"{r['work_id']} has no OMR-NED score — record refused, since a "
                "pooled figure over a subset would be stated as if it were the "
                "whole benchmark"
            )
        works.append({
            "work_id": r["work_id"],
            "omr_ned": scored["omr_ned"],
            "edits": scored["omr_ed"],
            "pitch_recall": r["notes"]["pitch_recall"],
            "pitch_precision": r["notes"]["pitch_precision"],
            "duration_rate": r["notes"]["duration_rate"],
        })
    edits = sum(w["edits"] for w in works)
    truth = sum(r["omr_ned"]["truth_symbols"] for r in results)
    pred = sum(r["omr_ned"]["pred_symbols"] for r in results)
    run = {
        "pooled": edits / max(1, truth + pred),
        "edits": edits,
        "truth_symbols": truth,
        "pred_symbols": pred,
        "commit": commit if commit is not None else _git_commit(),
        "works": works,
    }
    record = dict(previous or {})
    record["_comment"] = (
        "The single source for the CURRENT accuracy figures. Written by "
        "`orchestral_eval --omr-ned --record`; propagated into CLAUDE.md by "
        "`python3 -m tools.omr.accuracy_record --update`. Do not hand-edit, and "
        "do not restate a current figure in another document — see "
        "tools/omr/accuracy_record.py, and 68be549 for why there is only one."
    )
    runs = dict(record.get("runs") or {})
    runs[run_name] = run
    record["runs"] = runs
    return record


def _git_commit() -> str:
    """The short commit the measurement was taken on, best effort."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 — a missing git must not fail a measurement
        pass
    return "unknown"


def _rewrite(text: str, record: dict[str, Any], path_label: str,
             ) -> tuple[str, list[str]]:
    """Return `(new_text, names_seen)`, replacing each block's body."""
    out: list[str] = []
    seen: list[str] = []
    pos = 0
    while True:
        m = _BEGIN.search(text, pos)
        if m is None:
            out.append(text[pos:])
            break
        name = m.group(1)
        end = text.find(_END, m.end())
        if end == -1:
            raise ValueError(f"{path_label}: accuracy:begin name={name} has no end marker")
        if name not in BLOCKS:
            raise ValueError(f"{path_label}: unknown accuracy block name {name!r}")
        seen.append(name)
        out.append(text[pos:m.end()])
        out.append("\n" + BLOCKS[name][1](record) + "\n")
        pos = end
    return "".join(out), seen


def update(record: dict[str, Any] | None = None) -> list[str]:
    """Rewrite every block from the record. Returns the files changed."""
    record = record or load_record()
    changed = []
    for path in sorted({ROOT / f for f, _ in BLOCKS.values()}):
        text = path.read_text()
        new, _ = _rewrite(text, record, path.name)
        if new != text:
            path.write_text(new)
            changed.append(str(path.relative_to(ROOT)))
    return changed


def check(record: dict[str, Any] | None = None) -> list[str]:
    """Every way the docs and the record can disagree. Empty means clean."""
    record = record or load_record()
    problems: list[str] = []
    found: set[str] = set()
    for path in sorted({ROOT / f for f, _ in BLOCKS.values()}):
        if not path.is_file():
            problems.append(f"{path.name}: missing")
            continue
        text = path.read_text()
        try:
            new, seen = _rewrite(text, record, path.name)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        found.update(seen)
        if new != text:
            problems.append(
                f"{path.name}: an accuracy block is stale — run "
                "`python3 -m tools.omr.accuracy_record --update`"
            )
    for name, (file, _) in BLOCKS.items():
        if name not in found:
            problems.append(f"{file}: accuracy block {name!r} is missing")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true", help="rewrite the blocks")
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit non-zero")
    args = ap.parse_args(argv)

    if args.update:
        changed = update()
        print("\n".join(changed) if changed else "already up to date")
        return 0
    problems = check()
    for p in problems:
        print(p, file=sys.stderr)
    if not problems:
        run = _run(load_record(), DEFAULT_RUN) or {}
        print(f"CLAUDE.md agrees with the record: pooled "
              f"{_fmt(run.get('pooled', 0.0))}, {run.get('edits')} edits, "
              f"measured on {run.get('commit')}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
