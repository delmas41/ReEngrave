"""What the cross-page vote was actually shown, and what it did with it.

The per-staff JSON records a verdict and its reason but not the CANDIDATE that
produced it — so a page can report "rejected: 3 flats differs from the system's
1 flat" without anything saying where the system's 1 flat came from or how much
weight stood behind it. This probe wraps `key_signature_vote.reconcile` for the
duration of one transcription and prints both sides.

Read-only: it monkeypatches inside its own process and writes nothing to the
pipeline.

    python3 benchmarks/omr-keysig-from-music-2026-09/probe_vote_inputs.py \
        --pdf <score.pdf> --page 15 --dpi 600 --label beet5-p15
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr import key_signature_vote as ksv  # noqa: E402
from tools.omr import transcribe as tr  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = ROOT / "tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"

CAPTURED: list[tuple[list, object]] = []


def _wrapped(candidates, config=ksv.DEFAULT_VOTE_CONFIG):
    result = ksv._real_reconcile(candidates, config)
    CAPTURED.append((list(candidates), result))
    return result


def fname(f):
    return "-" if f is None else (f"{f}#" if f > 0 else (f"{-f}b" if f < 0 else "0"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dump", action="store_true",
                    help="persist the candidate list to artifacts/<label>.cands.json "
                         "so the vote can be replayed under another revision "
                         "WITHOUT re-running the model")
    args = ap.parse_args()

    ksv._real_reconcile = ksv.reconcile
    ksv.reconcile = _wrapped
    tr.reconcile = _wrapped

    tr.transcribe(pdf_path=Path(args.pdf), pages=[args.page],
                  weights=WEIGHTS, dpi=args.dpi)

    for n, (cands, result) in enumerate(CAPTURED):
        print(f"\n=== reconcile() call {n}: {len(cands)} candidates ===")
        print(f"{'sys':>3} {'ord':>3} {'stf':>4} {'read':>5} {'wt':>5} "
              f"{'source':>22}  {'carry':>5}  verdict")
        for c in sorted(cands, key=lambda c: (c.system_index, c.ordinal)):
            v = result.verdicts.get(c.staff_index)
            print(f"{c.system_index:>3} {c.ordinal:>3} {c.staff_index:>4} "
                  f"{fname(c.fifths):>5} {c.weight:>5.2f} {c.source[:22]:>22}  "
                  f"{'y' if c.can_carry else 'n':>5}  "
                  f"{(v.action + ': ' + v.reason) if v else '-'}")
        print(f"  reference per system: "
              f"{ {k: fname(v) for k, v in result.reference_written_by_system.items()} }")

        # What the reference vote actually counted.
        totals: dict[int, float] = defaultdict(float)
        dropped: list = []
        for c in cands:
            if not c.fifths:
                continue
            if c.weight < 1.0:
                dropped.append(c)
                continue
            totals[c.fifths] += max(c.weight, 1.0)
        print(f"  modal tally (weight >= 1 only): "
              f"{ {fname(k): round(v, 2) for k, v in sorted(totals.items())} }")
        if dropped:
            print(f"  EXCLUDED from the reference for weight < 1.0: " +
                  ", ".join(f"sys{c.system_index}/ord{c.ordinal}={fname(c.fifths)}"
                            f"@{c.weight:.2f}({c.source})" for c in dropped))

    if args.dump:
        out = HERE / "artifacts" / f"{args.label}.cands.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([
            [[c.system_index, c.ordinal, c.fifths, c.weight, c.source]
             for c in sorted(cands, key=lambda c: (c.system_index, c.ordinal))]
            for cands, _ in CAPTURED], indent=1))
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
