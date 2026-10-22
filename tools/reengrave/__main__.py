"""ROADMAP 4.1 -- `reengrave import <work>`, one command from a catalogued
work to finished files.

    python3 -m tools.reengrave import beethoven--symphony-5 \\
        --movements "1:0-11,2:12.1-20" --yes

Steps (docs/plan-2026-09-22-from-here-to-a-finished-score.md §4.1):

    1. RANK the work's editions -- held and catalogued -- with
       `tools.library.build_wishlist`'s own ranking logic (`tools.reengrave.
       planning.rank_editions`). Pick the best, or `--edition <imslp id>`.
    2. GET THE FILE. Held -> use it, no browser touched. Not held -> open
       the IMSLP page for the one click the gate requires, watch the
       download directory, then ingest it (`tools.reengrave.fetch`).
    3. MOVEMENTS. `--movements` is passed straight to the staged CLI and
       always wins outright when given. With none given, ROADMAP 4.2b's
       detection runs instead -- inside ADJUDICATE, on the actual gathered
       evidence, unconditionally, on every staged run -- and decides for
       itself whether the work is one movement or several. Nothing here
       tells it how many; the split is known only AFTER the gather, which
       is why `--dry-run` (below) cannot report it and says so.
    4. BUDGET. `tools.omr.staged.budget`'s own estimate, printed before the
       run. `--yes` skips the confirmation prompt for an unattended run,
       which also sets `OMR_SURYA_KEEP_ALIVE=0` (CLAUDE.md §5b) so the run
       owns its own processes.
    5. RUN the staged pipeline as the same subprocess its own CLI is,
       `--route-weights`, `--work-id`, per-movement outputs under
       `--out-dir` (default `out/<work_id>/`).
    6. REPORT. The staged CLI's own per-movement paths and accounting line
       print directly (this process's stdout is inherited, not captured).

`--dry-run` prints steps 1-4 and the exact command this would run, and
executes nothing: no browser, no download, no subprocess.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import fetch as fetch_mod
from . import planning


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python3 -m tools.reengrave")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser(
        "import",
        help="one command, a catalogued work to finished files (ROADMAP 4.1)")
    p.add_argument("work_id", help="genre + number, e.g. beethoven--symphony-5 "
                   "-- NEVER the dossier id (CLAUDE.md §8)")
    p.add_argument("--edition", default=None,
                   help="force this IMSLP id instead of the top-ranked pick")
    p.add_argument("--movements", default=None,
                   help="passed straight to the staged CLI's --movements "
                        "(e.g. '1:0-11,2:12.1-20'); omit to run the whole "
                        "work as ONE movement")
    p.add_argument("--out-dir", default=None,
                   help="default out/<work_id>/")
    p.add_argument("--downloads-dir", default=str(Path.home() / "Downloads"),
                   help="watched for the new PDF after the browser opens")
    p.add_argument("--timeout", type=float, default=1800.0,
                   help="seconds to wait for the download (default 1800 = 30 min)")
    p.add_argument("--yes", action="store_true",
                   help="skip the confirmation prompt -- for an unattended "
                        "run; sets OMR_SURYA_KEEP_ALIVE=0")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan and the exact command; run nothing")
    return ap


def _print_ranked(ranked) -> None:
    print("RANK:")
    for c in ranked:
        mark = "HELD" if c["held"] else c["source"].upper()
        print(f"  {c['score']:5.1f}  IMSLP{c['imslp_id']:<9} {mark:10.10} "
             f"{str(c.get('pages', '?')):>4}pp  {c.get('publisher', '')[:50]}")


def _pick(ranked, edition_id: Optional[str]) -> Optional[dict]:
    if not edition_id:
        return ranked[0]
    edition_id = str(edition_id)
    for c in ranked:
        if c["imslp_id"] == edition_id:
            return c
    return None


def cmd_import(args: argparse.Namespace) -> int:
    work_id = args.work_id
    out_dir = Path(args.out_dir) if args.out_dir else Path("out") / work_id

    try:
        ranked = planning.rank_editions(work_id)
    except planning.NoKnownEdition as exc:
        print(f"ERROR: {exc}")
        return 2
    _print_ranked(ranked)

    picked = _pick(ranked, args.edition)
    if picked is None:
        known = ", ".join(c["imslp_id"] for c in ranked)
        print(f"ERROR: --edition {args.edition} is not a ranked candidate "
             f"for {work_id} (known: {known})")
        return 2
    print(f"PICKED: IMSLP{picked['imslp_id']} ({picked.get('publisher', '')}) -- "
         f"{'held' if picked['held'] else 'not held, ' + picked['source']}")

    downloads_dir = Path(args.downloads_dir).expanduser()
    held_path = fetch_mod.held_pdf_path(picked)
    if held_path is not None:
        print(f"GET: already held -- {held_path}")
    else:
        url = picked.get("page_url") or (
            f"https://imslp.org/wiki/Special:ReverseLookup/{picked['imslp_id']}")
        print(f"GET: not held -- would open {url} and watch {downloads_dir} "
             f"for a new PDF (timeout {args.timeout:.0f}s)")

    if not args.movements:
        # ROADMAP 4.2b: nothing is guessed HERE -- `tools.omr.staged`'s own
        # ADJUDICATE stage runs `movement_start` on every gather regardless
        # of this flag, reading a tempo heading, a meter STATEMENT, a
        # margin-label reset and a wider indent off the actual page, and
        # requires at least two of those together before calling a system a
        # boundary (never a bare guess -- CLAUDE.md rule 6). This process
        # never gathers anything during --dry-run, so it cannot know
        # detection's answer and does not pretend to.
        print("⚠️ no --movements given: ROADMAP 4.2b detection will run "
             "during the gather and decide the movement count for itself, "
             "off the actual page (tempo heading + meter statement + "
             "margin-label reset + indent) -- pass --movements to fix the "
             "split by hand instead. The split is known only AFTER the "
             "run; a --dry-run cannot report it.")
    pages_spec, spans = planning.resolve_pages_spec(picked.get("pages"), args.movements)
    if spans:
        print(f"MOVEMENTS: {len(spans)} ({', '.join(str(s['number']) for s in spans)})")

    estimate = planning.budget_for(pages_spec)
    from tools.omr.staged import budget as budget_mod
    print(budget_mod.format_budget_report(estimate))

    display_pdf = str(held_path) if held_path is not None else "<downloaded pdf>"
    cmd = planning.build_staged_command(
        python=sys.executable, pdf_path=display_pdf, work_id=work_id,
        pages_spec=pages_spec, movements_arg=args.movements, out_dir=out_dir)

    if args.dry_run:
        print("\nDRY RUN -- would run:")
        print("  " + " ".join(cmd))
        print("\nDRY RUN: nothing downloaded, nothing gathered.")
        return 0

    if not args.yes:
        resp = input(f"\nProceed with the {work_id} import? [y/N] ")
        if resp.strip().lower() not in ("y", "yes"):
            print("aborted")
            return 1

    pdf_path = fetch_mod.get_edition_pdf(
        picked, downloads_dir=downloads_dir, timeout_s=args.timeout)

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = planning.build_staged_command(
        python=sys.executable, pdf_path=str(pdf_path), work_id=work_id,
        pages_spec=pages_spec, movements_arg=args.movements, out_dir=out_dir)

    env = dict(os.environ)
    if args.yes:
        # CLAUDE.md §5b: an unattended run owns its own processes.
        env["OMR_SURYA_KEEP_ALIVE"] = "0"

    print("RUN: " + " ".join(cmd))
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        print(f"ERROR: staged pipeline exited {proc.returncode}")
        return proc.returncode

    print(f"\nDONE -- files under {out_dir}/")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.cmd == "import":
        return cmd_import(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
