# The 20-row era — canonical scan-gate baseline (2026-09-05)

Stamped on the reconciliation tree (the 8-way merge landing as PR to main),
composed defaults (tilt localization ON × choir cues ON), graft weights
pinned, all 20 verified rows pooled:

**CANONICAL: pooled OMR-NED 0.8444 / 74,968 edits over 49,846 truth +
38,937 predicted symbols, 20 rows.** (`results-reconciliation.json`)

The gate now reads CONTINUOUS spans: both Beethoven 5 twins mm 1–112 (four
pages each), Brahms 1 mm 1–58, Mahler 5 mm 0–31, Dvořák 9 mm 1–30, and the
Bach stress-turned-ordinary row. Windows are anchored overwhelmingly by the
engraver's own printed system-start numbers, verified by Sean against
rendered crops (VERIFICATION.md, 2026-09-04/05 entries).

⚠️ **Boundary discipline:** this figure opens the 20-row era. Nothing from
the 11-row era (0.8303 composed), the 10-row era (0.8387/0.8345), or the
5-row era (0.7517/0.7493) compares to it in either direction. Within-era,
per-row comparisons against `results-reconciliation.json` are valid.

Notes carried at the stamp: (1) the merged tree's engraved-chain fixes
(beam gap, arc attribution, hairpin export) also touch scan rows — every
previously-measured row moved slightly and favorably (e.g. Bach 6,197 →
6,148; Dvořák p5 675 → 661), so the 11 old rows are NOT byte-comparable to
the composed re-stamp, only era-internally; (2) the seven new rows' first
figures run 0.71–0.93 — deeper pages are harder pages, as the widening
predicted; (3) the "meas det/exp" display column undercounts multi-system
pages (a known summary-field quirk; the omr.json is authoritative).
