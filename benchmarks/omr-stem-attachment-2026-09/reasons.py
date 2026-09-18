"""What each record already says about `stem_direction` -- the reason census.

⚠️ THIS IS THE FIRST THING TO RUN, and it decides whether the rest of this
directory is measuring anything. The convention probe's committed figures
(`out/litolff-convention.json`: 472 heads it can speak for) were taken against
a record, and whether that record is BEFORE or AFTER the beam-mate tier landed
decides whether 472 is a MARGINAL reach or a gross one that double-counts 152
heads another tier already serves.

The discriminator needs no argument: a pre-tier record reports `no_stem` 793
and no `beam_mate` at all; a post-tier one reports 641 and 152 `beam_mate`.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: reasons.py <record.json> [...]", file=sys.stderr)
        return 2
    for p in sys.argv[1:]:
        c = collections.Counter()
        for v in stream_array(p, "verdicts"):
            if v.get("quantity") == "stem_direction":
                c[(v.get("outcome"), v.get("reason"))] += 1
        if not c:
            print(f"DEAD: {Path(p).name} holds no stem_direction verdict",
                  file=sys.stderr)
            return 2
        print(f"{Path(p).name}   total {sum(c.values())}")
        for k, n in c.most_common():
            print(f"   {k}: {n}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
