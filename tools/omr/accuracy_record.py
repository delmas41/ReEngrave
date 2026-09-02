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

AND THE DEFINITION, since 2026-09-02. A pooled figure is only a number about a
pipeline while the thing it is pooled over holds still; change the work set and
the same machinery will happily rewrite one paragraph with a figure that cannot
be compared to the one it replaced. `BENCHMARK_WORKS` is that work set, held
here beside the record rather than in the eval, and stamped into the record so a
measurement taken under an older definition is VISIBLY older rather than
silently comparable. `check()` refuses a record whose stamp disagrees.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]

#: The single source. Written by `orchestral_eval --record`.
RECORD_PATH = ROOT / "benchmarks" / "omr-ned-2026-08" / "current-accuracy.json"

_BEGIN = re.compile(r"<!--\s*accuracy:begin\s+name=([a-z0-9_-]+)\s*-->")
_END = "<!-- accuracy:end -->"


# ---------------------------------------------------------------------------
# What the benchmark IS
# ---------------------------------------------------------------------------
#
# WIDENED FROM 3 WORKS TO 11 ON 2026-09-02, at Sean's decision.
#
# Sixteen fixes had been landed against `beethoven-sym5-mvt1`,
# `brahms-sym1-mvt1` and `mahler-sym5-mvt1`, and measured on nothing else. The
# corpus widening then ran eight more engraved orchestral pages of the same kind
# — same LilyPond, same source library — and the new works scored roughly TWICE
# the incumbents' error rate. Three of the faults that surfaced there were
# invisible to the incumbent three by accident of what those pages happen to
# print: a cut-common glyph read at 0.92 and dropped on export (zero on all
# three incumbents, because all three print digit meters), triplet digits filed
# under `fingering3` (Beethoven 5 and Brahms 1 have none at all), and
# articulations never exported (0, 2 and 6 detections across the three). The
# three-work figure was hiding a distribution rather than summarising one.
# benchmarks/omr-corpus-widening-2026-09/FINDINGS.md is the measurement.
#
# ⚠️ NO FIGURE CROSSES THIS BOUNDARY. A pooled OMR-NED is a property of the work
# set it is pooled over, not of the pipeline alone, so an 11-work figure and a
# 3-work figure are different measurements of different things and neither is
# progress against the other. See `BENCHMARK_SINCE`.
#
# `boulanger-printemps-mvt1` IS DELIBERATELY OUT, and stays runnable via
# `--works boulanger-printemps-mvt1`. At 46 parts it is the one work whose
# STRUCTURE fails — 43 parts against 46, with 76% of its budget in `entire
# measure` and `entire staff` operations before any recent work — so it measures
# page segmentation on a2 paper rather than note recognition, and it dominates
# any pool it enters: it alone moves the widening pool 0.2057 -> 0.3846. It is
# also the work where a correct fix looked like a regression (the articulation
# work read 263 of its 271 marks and its OMR-NED still ROSE, because symbols
# added to a bar already charged whole cost more). Its row is kept and honest in
# FINDINGS.md sections 2 and 4; what it must not do is set the headline.
#
#: The works the headline figure is pooled over. Changing this changes what the
#: benchmark IS — bump `BENCHMARK_SINCE` with it and re-measure both runs.
BENCHMARK_WORKS: tuple[str, ...] = (
    # The canonical three. Every fix from 2026-08-31 to 2026-09-01 was measured
    # on these and on nothing else.
    "beethoven-sym5-mvt1",     # classical orchestra, 18 parts, one alto clef
    "brahms-sym1-mvt1",        # romantic, thicker inner voices
    "mahler-sym5-mvt1",        # late romantic, largest forces
    # The eight the widening added, chosen on the three axes a fix tuned on
    # three pages could plausibly break: era, part count, texture/meter.
    "mozart-sym40-mvt1",       # 11 parts, 2/2 cut — sparsest true orchestra
    "mozart-sym41-mvt1",       # 17 parts, 4/4 common — era held, forces moved
    "beethoven-sym3-mvt1",     # 19 parts, 3/4 — near-neighbour control for sym5
    "brahms-sym4-mvt1",        # 20 parts, 2/2 cut — near-neighbour for sym1
    "dvorak-sym9-mvt4",        # 19 parts, bass_8vb; excerpt fits 3 bars only
    "tchaikovsky-sym4-mvt2",   # 20 parts, 2/4
    "tchaikovsky-sym6-mvt2",   # 17 parts, 5/4 — the only odd meter in the set
    "bruckner-sym5-mvt1",      # 25 parts, 2/2 cut — big without being dense
)

#: The name of the benchmark, and the date its work set last changed. Both are
#: stamped into the record. The date is what makes an old record legible as old:
#: every figure written before it was pooled over a DIFFERENT set of works.
BENCHMARK_NAME = "orchestral-e2e"
BENCHMARK_SINCE = "2026-09-02"


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


_SYM_RE = re.compile(r"sym(\d+)")
_MVT_RE = re.compile(r"mvt(\d+)")


def _short(work_id: str) -> str:
    """`beethoven-sym5-mvt1` -> `Beethoven 5`.

    The three-work era could label a row with the composer alone, because there
    was exactly one of each. The eleven-work set has TWO Beethovens, two
    Brahmses, two Mozarts and two Tchaikovskys, and a composer-only label would
    print two rows called `Beethoven` with different numbers in them — a table
    that looks fine and cannot be read. The symphony number is what separates
    them, so it is part of the name.
    """
    parts = work_id.split("-")
    name = parts[0].capitalize()
    for part in parts[1:]:
        m = _SYM_RE.fullmatch(part)
        if m:
            return f"{name} {int(m.group(1))}"
    # Not a numbered symphony (`boulanger-printemps-mvt1`): name the work rather
    # than drop it, since the composer alone may not be unique either.
    rest = [p.capitalize() for p in parts[1:] if not _MVT_RE.fullmatch(p)]
    return " ".join([name] + rest)


def _labels(work_ids: list[str]) -> dict[str, str]:
    """work_id -> display label, disambiguated where two would collide.

    `_short` separates the works actually in the set today; two movements of one
    symphony would still collide, so the movement is appended when — and only
    when — it has to be. A label that silently names two rows is the failure
    this exists to make impossible, not one to be caught by review.
    """
    out = {w: _short(w) for w in work_ids}
    clashes = {label for label, n in Counter(out.values()).items() if n > 1}
    for work_id, label in out.items():
        if label not in clashes:
            continue
        m = _MVT_RE.search(work_id)
        out[work_id] = f"{label} mvt{int(m.group(1))}" if m else work_id
    return out


def _spread_phrase(run: dict[str, Any]) -> str:
    """`Tchaikovsky 4 0.0571 at best, Mozart 41 0.3632 at worst`.

    Eleven works no longer fit a sentence, and the table below the paragraph
    already carries every row. What the sentence is for is the thing the table
    makes a reader work for and the widening made the point of: the SPREAD. The
    old three-work corpus ran 0.0455 to 0.1709 and the eleven-work one runs
    about an order of magnitude wide, so a pooled figure quoted alone says less
    than it appears to.
    """
    works = sorted(run.get("works", []), key=lambda w: w["omr_ned"])
    if not works:
        return ""
    labels = _labels([w["work_id"] for w in works])
    best, worst = works[0], works[-1]
    if best is worst:
        return f"{labels[best['work_id']]} {_fmt(best['omr_ned'])}"
    return (f"{labels[best['work_id']]} {_fmt(best['omr_ned'])} at best, "
            f"{labels[worst['work_id']]} {_fmt(worst['omr_ned'])} at worst")


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
    works = sorted(run["works"], key=lambda w: w["omr_ned"])
    labels = _labels([w["work_id"] for w in works])
    rows = "\n".join(
        f"| {labels[w['work_id']]} | {_fmt(w['omr_ned'])} | {w['edits']} | "
        f"{_fmt(w['pitch_recall'], 3)} | {_fmt(w['pitch_precision'], 3)} | "
        f"{_fmt(w['duration_rate'], 3)} |"
        for w in works
    )
    variant = _run(record, DIRECTION_TEXT_RUN)
    variant_clause = ""
    if variant:
        variant_clause = (
            f" With `--direction-text` (off by default, needs `.venv-surya`), "
            f"**{_fmt(variant['pooled'])} / {variant['edits']}**, measured on "
            f"`{variant['commit']}`."
        )
    # The work COUNT is generated rather than written, so widening the set
    # cannot leave a sentence saying "three works" above a table of eleven.
    # No historical baseline is quoted here any more: every figure before
    # BENCHMARK_SINCE was pooled over a different work set, and standing one
    # beside this one would be the invalid comparison the boundary exists to
    # prevent. That history lives in the prose around this block.
    return (
        f"Current on the engraved orchestral benchmark, measured on "
        f"`{run['commit']}`: **pooled {_fmt(run['pooled'])} / {run['edits']} "
        f"edits** over {len(works)} works ({_spread_phrase(run)}), across "
        f"{run['truth_symbols']} truth + {run['pred_symbols']} predicted "
        f"symbols.{variant_clause}\n\n"
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


def _works_of(run: dict[str, Any]) -> list[str]:
    """The work ids one recorded run covers, sorted."""
    return sorted(w["work_id"] for w in run.get("works", []))


def record_from_results(results: list[dict[str, Any]],
                        run_name: str = DEFAULT_RUN,
                        previous: dict[str, Any] | None = None,
                        commit: str | None = None) -> dict[str, Any]:
    """Fold one measured run into the record, leaving the other runs alone.

    Raises when a work has no OMR-NED score: a partial record is worse than no
    record, because the docs would state a pooled figure over a subset without
    saying so.

    ⚠️ A run measured over a DIFFERENT work set is dropped, not kept. The two
    configurations are measured in separate commands, so when the work set
    changes there is necessarily a moment where one has been re-measured and the
    other has not — and a record holding both would render one paragraph quoting
    an 11-work default beside a 3-work variant, with nothing in the text saying
    the two are not comparable. Dropping the stale run states the honest thing
    instead: the variant figure is gone until it is measured again.
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
    measured = _works_of(run)
    record["benchmark"] = {
        "name": BENCHMARK_NAME,
        "since": BENCHMARK_SINCE,
        "works": measured,
        "note": (
            "The work set these figures are pooled over. A pooled OMR-NED is a "
            "property of this set as much as of the pipeline, so a figure "
            "recorded under a different set is a different measurement and not "
            "a comparison — the set widened from 3 works to 11 on "
            f"{BENCHMARK_SINCE}. A record with no `benchmark` key predates that "
            "and is pre-boundary by construction."
        ),
    }
    # Runs measured over another work set do not survive a definition change.
    runs = {name: prev for name, prev in (record.get("runs") or {}).items()
            if _works_of(prev) == measured}
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
    """Rewrite every block from the record. Returns the files changed.

    Refuses a record measured over a different work set. `check()` catching it
    afterwards is not enough: `--update` is the WRITE direction, and writing a
    3-work figure into the paragraph would leave the docs and the record in
    perfect agreement about a benchmark the code does not run — after which
    `check()` is silent, because it compares the two things that now agree.
    """
    record = record or load_record()
    problems = definition_problems(record)
    if problems:
        raise ValueError(
            "refusing to write the accuracy blocks: " + " ".join(problems)
        )
    changed = []
    for path in sorted({ROOT / f for f, _ in BLOCKS.values()}):
        text = path.read_text()
        new, _ = _rewrite(text, record, path.name)
        if new != text:
            path.write_text(new)
            changed.append(str(path.relative_to(ROOT)))
    return changed


def definition_problems(record: dict[str, Any]) -> list[str]:
    """Every way the record can be a measurement of a DIFFERENT benchmark.

    Checked before the text, because a block that renders cleanly from a record
    measured over another work set is the worst of the two failures: the docs
    and the record agree, and both describe something the current code does not
    measure. The old three-work records carry no `benchmark` key at all, so
    "pre-boundary" is detectable and not merely assumed.
    """
    want = sorted(BENCHMARK_WORKS)
    definition = record.get("benchmark")
    if not definition:
        return [
            "current-accuracy.json has no `benchmark` stamp, so it predates the "
            f"benchmark-definition boundary of {BENCHMARK_SINCE} (3 works -> "
            f"{len(want)}). Its figures are not comparable to the current "
            "definition — re-measure with `orchestral_eval --omr-ned --record`."
        ]
    problems: list[str] = []
    got = sorted(definition.get("works") or [])
    if got != want:
        missing = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        problems.append(
            f"current-accuracy.json was measured over {len(got)} works and "
            f"BENCHMARK_WORKS now names {len(want)}"
            + (f"; not measured: {missing}" if missing else "")
            + (f"; no longer in the benchmark: {extra}" if extra else "")
            + " — re-measure rather than compare across the change."
        )
    for name, run in sorted((record.get("runs") or {}).items()):
        if _works_of(run) != got:
            problems.append(
                f"current-accuracy.json: run {name!r} covers "
                f"{len(_works_of(run))} works but the stamp names {len(got)} — "
                "the record is internally inconsistent."
            )
    return problems


def check(record: dict[str, Any] | None = None) -> list[str]:
    """Every way the docs and the record can disagree. Empty means clean."""
    record = record or load_record()
    problems: list[str] = list(definition_problems(record))
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
        record = load_record()
        run = _run(record, DEFAULT_RUN) or {}
        n = len((record.get("benchmark") or {}).get("works") or [])
        print(f"CLAUDE.md agrees with the record: pooled "
              f"{_fmt(run.get('pooled', 0.0))}, {run.get('edits')} edits over "
              f"{n} works, measured on {run.get('commit')}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
