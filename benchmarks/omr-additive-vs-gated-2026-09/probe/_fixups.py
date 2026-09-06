"""Corrections applied to FINDINGS.md after verifying line numbers and the fate
of `clef_locator`'s trace against the tree."""
import os

DEST = os.path.join(os.path.dirname(__file__), "..", "FINDINGS.md")
s = open(DEST).read()

SUBS = [
    ("`contextual.py:1203`", "`contextual.py:1202`"),
    ("the gate is\n`contextual.py:1203`'s", "the gate is\n`contextual.py:1202`'s"),
    ("the exclusion at `contextual.py:1203`",
     "the exclusion at `contextual.py:1202`"),

    # clef_locator: the score is not merely dropped -- a `trace` parameter
    # exists and the PIPELINE never passes one. Say that precisely.
    ("`clef_locator` (ink fraction; the refined **symmetry score** at `:845`, the most\nload-bearing instance in that file; the geometry `residual`);",
     "`clef_locator` (ink fraction; the refined **symmetry score**; the geometry\n`residual`) — ⚠️ with a wrinkle worth stating exactly: `locate_clef` takes an\noptional `trace` dict and DOES record the symmetry and the rejecting branch into\nit, but **neither of `transcribe.py`'s two call sites (`:1677`, `:4286`) passes\none**, so in production every one of those numbers is discarded and only\nbenchmark probes have ever seen them;"),
    ("| `clef_locator` symmetry, ink fraction, geometry residual | A→C | the refined symmetry score at `clef_locator.py:845` is the most load-bearing discarded number in that file | no |",
     "| `clef_locator` symmetry, ink fraction, geometry residual | A→C | the machinery already exists — `locate_clef(trace=...)` records the score and the rejecting branch — and **neither pipeline call site passes a trace**. Cheapest item on this list | no |"),

    # The 82% claim: soften, because the hairpin rule can in principle speak on
    # wedge classes, and what is measured is that it fired zero times.
    ("**3,705 of 4,521 contests (82%) are in categories no tier above distance can\nreach.**",
     "**3,705 of 4,521 contests (82%) are in categories where, on this corpus, no\ntier above distance spoke at all.** (The hairpin rule could in principle reach a\nwedge-class contest; empirically rank 1 fired zero times, so it did not.)"),
]

for old, new in SUBS:
    if old in s:
        s = s.replace(old, new)
    else:
        print("NOT FOUND:", old[:70])

open(DEST, "w").write(s)
print("done")
