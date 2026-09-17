#!/usr/bin/env python3
"""The query, end to end: *"what has been seen HERE?"*

Sean's own framing of why the store exists:

    "if we have an undiagnosed blob or dot, we have gathered a lot of
    information on what sorts of things are more likely where."

This is that question asked of the accumulated store.  It is a DEMONSTRATION,
not a consumer: nothing in the pipeline reads any of this, deliberately.

⚠️ THE ANSWER IS A TABLE OF WHAT WAS SEEN, NEVER A PROBABILITY.  An
uncalibrated probability is worse than none -- measured in this repo at ECE
0.1277, failing worst at the top of the range -- so the store reports counts,
the spread of the shapes seen there, and how many distinct editions
contributed.  Turning that into a belief is a later stage's job, under that
stage's discipline.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.positional_store import (  # noqa: E402
    EntryStore, PositionIndex, TIER_OBSERVED, TIER_TRUE,
)


def show(idx, title, **kw):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    r = idx.ask(**kw)
    q = r["query"]
    print("  position %.2f steps (%.2f spaces) | tier=%s publisher=%s "
          "height=%s" % (q["staff_position"], q["staff_position"] / 2,
                         q["tier"], q["publisher"], q["height_spaces"]))
    print("  -> vbucket %d at %s-space resolution; %d observations, "
          "%d candidate names"
          % (q["vbucket"], q["vbucket_spaces"], r["observations_here"],
             r["n_candidates"]))
    if not r["candidates"]:
        print("     NOTHING HAS BEEN SEEN HERE. That is an answer.")
        return
    print("  %-26s %7s %8s %10s %10s %5s"
          % ("name", "n", "share", "mean_h", "sd_h", "eds"))
    for c in r["candidates"][:10]:
        print("  %-26s %7d %8.3f %10s %10s %5d"
              % (c["name"], c["count"], c["share_of_this_kind_here"],
                 c.get("mean_height_spaces"), c.get("sd_height_spaces"),
                 c["editions"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("store")
    ap.add_argument("--vbucket-spaces", type=float, default=0.25)
    args = ap.parse_args()

    st = EntryStore.read(Path(args.store))
    s = st.summary()
    print("STORE: %d entries | tiers %s | publishers %s"
          % (s["entries"], s["per_tier"], s["per_publisher"]))
    if s["entries"] == 0:
        print("DEAD: empty store.")
        return 2
    idx = PositionIndex(st, vbucket_spaces=args.vbucket_spaces)
    print("INDEX (derived, rebuildable): %s" % idx.summary())

    # ── THE HEADLINE QUERY ─────────────────────────────────────────────────
    # A whole rest hangs from the second line from the top.  A blob there,
    # about half a staff space tall, is the case Sean described.
    show(idx, "1. An undiagnosed blob at staff position 2.5, ~0.5 spaces "
              "tall, on a LITOLFF plate",
         staff_position=2.5, tier=TIER_OBSERVED, publisher="litolff",
         height_spaces=0.5)

    # ── the same position on the other house ───────────────────────────────
    show(idx, "2. THE SAME QUERY on a BREITKOPF plate — publisher is a "
              "conditioning variable, not decoration",
         staff_position=2.5, tier=TIER_OBSERVED, publisher="breitkopf",
         height_spaces=0.5)

    # ── shape withheld: what lives at this position at all? ────────────────
    show(idx, "3. The same position with NO shape constraint — everything "
              "ever seen there (Litolff)",
         staff_position=2.5, tier=TIER_OBSERVED, publisher="litolff")

    # ── the non-circular tier ──────────────────────────────────────────────
    show(idx, "4. THE SAME POSITION IN THE TRUE TIER — rendered ground "
              "truth, no detector anywhere in it",
         staff_position=2.5, tier=TIER_TRUE)

    # ── far above the staff ────────────────────────────────────────────────
    show(idx, "5. Well ABOVE the staff (position -6) — a different "
              "neighbourhood entirely",
         staff_position=-6.0, tier=TIER_OBSERVED, publisher="litolff")

    # ── the refusal that protects the store from its own output ────────────
    print("\n" + "=" * 78)
    print("6. THE TIER REFUSAL — pooling provenance must be deliberate")
    print("=" * 78)
    try:
        idx.ask(2.5, tier=None)
    except ValueError as exc:
        print("  ask(tier=None) raised, as it must:\n    %s" % exc)
    r = idx.ask(2.5, tier=None, require_tier=False)
    print("  ask(tier=None, require_tier=False) -> %d observations pooled "
          "across %d rows, which the caller has now said in as many words."
          % (r["observations_here"], r["n_candidates"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
