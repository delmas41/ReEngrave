"""Score the pipeline's notes against `truth/<page>.json` — on a REAL SCAN.

    python3 benchmarks/omr-real-scan-notes-2026-08/score.py --page beet5-p2

Requires a truth file, which `build_truth.py` writes only when its measure-range
tripwire passes. There is no path from here to a number without that file.

THE ALIGNMENT IS NOT NEW. It is the same longest-common-subsequence over pitch
names that `tools/omr/training/end_to_end_eval.py` uses and
`orchestral_eval.py` reuses — imported, not reimplemented, so that the real-scan
row and the engraved rows are the same measurement on different input and can
honestly be put in one table. It is deliberately generous: it does not care
where a note sits in the bar, only that the sequence of pitches is right.

JOINING A PART TO A STAFF. `export.to_musicxml` emits one <part> per (page,
system, staff-within-system) and names it `Staff p{page}-s{system}-{staff}`, so
a printed part that runs across both systems of a page arrives as two parts.
This walks those names, concatenates the two halves of each scored staff in
system order, and refuses if the names are not the ones the page's layout
predicts — the join is by position, and position is only meaningful while the
detected layout matches the hand-read one. That is re-checked here rather than
trusted from build time, because the cached run can be replaced with `--fresh`.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from build_truth import TRUTH_DIR, check_layout  # noqa: E402
from omr_run import load_or_run  # noqa: E402
from pages import DEFAULT_WEIGHTS, page_config  # noqa: E402

# The alignment itself, from the engraved-input benchmarks. Same code, so the
# real-scan number is comparable to theirs.
from tools.omr.training.end_to_end_eval import _lcs, part_sequences  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402


def omr_part_names(path: Path) -> list[str]:
    """The <part-name> of every part, in document order."""
    root = ET.parse(path).getroot()
    part_list = root.find("part-list")
    if part_list is None:
        raise SystemExit(f"no <part-list> in {path}")
    names = []
    for sp in part_list.findall("score-part"):
        node = sp.find("part-name")
        names.append("" if node is None or node.text is None else node.text)
    return names


def expected_names(page_index: int, systems: list[int], n_staves: int) -> list[str]:
    return [f"Staff p{page_index}-s{s}-{k}"
            for s in range(len(systems)) for k in range(n_staves)]


def omr_sequences_by_staff(omr_xml: Path, cfg: dict[str, Any]
                           ) -> dict[int, list[tuple[str, float]]]:
    """Per staff ordinal, the page's notes with the systems concatenated."""
    names = omr_part_names(omr_xml)
    want = expected_names(cfg["page_index"], cfg["systems"], cfg["n_staves"])
    if names != want:
        raise SystemExit(
            "the exported parts are not the ones this page's layout predicts, "
            "so a staff ordinal does not name an instrument.\n"
            f"  expected {len(want)} parts starting {want[:2]}\n"
            f"  got      {len(names)} parts starting {names[:2]}")

    seqs = part_sequences(omr_xml)
    if len(seqs) != len(names):
        raise SystemExit(f"{len(seqs)} sequences for {len(names)} parts")

    out: dict[int, list[tuple[str, float]]] = {}
    for ordinal in range(cfg["n_staves"]):
        joined: list[tuple[str, float]] = []
        for s in range(len(cfg["systems"])):
            joined.extend(seqs[s * cfg["n_staves"] + ordinal])
        out[ordinal] = joined
    return out


def score_page(cfg: dict[str, Any], truth: dict[str, Any], *, weights: Path,
               fresh: bool) -> dict[str, Any]:
    result, run_file, cached = load_or_run(cfg, weights=weights, fresh=fresh)
    print(f"  run        {run_file}{' (cached)' if cached else ''}")

    print("\nTRIPWIRE — hand-read layout vs. the Phase 1 of the run being scored")
    ok, lines = check_layout(cfg, result)
    print("\n".join(lines))
    if not ok:
        raise SystemExit(
            "\nREFUSED. The truth file was built against a page layout this run "
            "does not reproduce, so the staff-ordinal join is not trustworthy "
            "and the bar range may not be the one on the page. No score.")

    omr_xml = run_file.with_suffix(".musicxml")
    omr_xml.write_text(to_musicxml(result))
    by_staff = omr_sequences_by_staff(omr_xml, cfg)

    rows = []
    tot_truth = tot_omr = tot_matched = tot_dur = 0
    for p in truth["parts"]:
        t_seq = [(name, ql) for name, ql in p["sequence"]]
        o_seq = by_staff[p["staff_ordinal"]]
        matched, duration_ok = _lcs(t_seq, o_seq)
        rows.append({
            "printed": p["printed"],
            "gradus_part": p["gradus_part"],
            "staff_ordinal": p["staff_ordinal"],
            "truth_notes": len(t_seq),
            "omr_notes": len(o_seq),
            "pitch_matched": matched,
            "pitch_recall": round(matched / len(t_seq), 3) if t_seq else 0.0,
            "pitch_precision": round(matched / len(o_seq), 3) if o_seq else 0.0,
            "duration_ok_on_matched": duration_ok,
            "duration_rate": round(duration_ok / matched, 3) if matched else 0.0,
        })
        tot_truth += len(t_seq)
        tot_omr += len(o_seq)
        tot_matched += matched
        tot_dur += duration_ok

    overall = {
        "truth_notes": tot_truth,
        "omr_notes": tot_omr,
        "pitch_matched": tot_matched,
        "pitch_recall": round(tot_matched / tot_truth, 3) if tot_truth else 0.0,
        "pitch_precision": round(tot_matched / tot_omr, 3) if tot_omr else 0.0,
        "duration_ok_on_matched": tot_dur,
        "duration_rate": round(tot_dur / tot_matched, 3) if tot_matched else 0.0,
    }
    return {
        "page_id": cfg["id"],
        "caption": CAPTION.format(
            page=cfg["id"], dpi=cfg["dpi"], first=truth["measures"]["first"],
            last=truth["measures"]["last"], n=len(rows),
            total=cfg["n_staves"], notes=tot_truth),
        "input": "real 19th-century scan",
        "pdf": str(cfg["pdf"]),
        "page_index": cfg["page_index"],
        "dpi": cfg["dpi"],
        "measures": truth["measures"],
        "omr_musicxml": str(omr_xml),
        "run": str(run_file),
        "scored_parts": rows,
        "overall": overall,
        "excluded_staves": truth["excluded_staves"],
    }


# The caption is part of the number. A recall figure from this benchmark that
# travels without it will be read as "the pipeline's accuracy on this page",
# which is four staves of eleven and is not what was measured.
CAPTION = ("{page} @ {dpi} dpi, mm.{first}-{last}: {n} of the page's {total} "
           "staves — the parts that own a printed staff alone — {notes} notes. "
           "Real scan.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", default="beet5-p2")
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--fresh", action="store_true",
                    help="re-run the pipeline instead of reusing the cached run")
    ap.add_argument("--truth", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    cfg = page_config(args.page)
    truth_file = args.truth or (TRUTH_DIR / f"{cfg['id']}.json")
    if not truth_file.is_file():
        raise SystemExit(
            f"no truth file at {truth_file}.\n"
            "Run build_truth.py first. If it refused, the page's bar range and "
            "the pipeline's Phase 1 disagree and there is nothing to score "
            "against — fix that rather than hand-writing a truth file.")
    truth = json.loads(truth_file.read_text())
    if truth["page_id"] != cfg["id"]:
        raise SystemExit(f"truth file is for {truth['page_id']}, not {cfg['id']}")

    print(f"page {cfg['id']}: {cfg['title']}")
    print(f"  truth      {truth_file}  "
          f"(mm.{truth['measures']['first']}-{truth['measures']['last']}, "
          f"{truth['total_notes']} notes over {len(truth['parts'])} staves)")

    report = score_page(cfg, truth, weights=args.weights, fresh=args.fresh)

    print(f"\n{'part':22s} {'staff':>5s} {'notes':>12s} {'recall':>7s} "
          f"{'prec':>6s} {'dur':>6s}")
    for r in report["scored_parts"]:
        print(f"{r['printed']:22s} {r['staff_ordinal']:>5d} "
              f"{str(r['omr_notes']) + '/' + str(r['truth_notes']):>12s} "
              f"{r['pitch_recall']:>7.3f} {r['pitch_precision']:>6.3f} "
              f"{r['duration_rate']:>6.3f}")
    o = report["overall"]
    print(f"{'OVERALL':22s} {'':>5s} "
          f"{str(o['omr_notes']) + '/' + str(o['truth_notes']):>12s} "
          f"{o['pitch_recall']:>7.3f} {o['pitch_precision']:>6.3f} "
          f"{o['duration_rate']:>6.3f}")
    print(f"\n{report['caption']}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
