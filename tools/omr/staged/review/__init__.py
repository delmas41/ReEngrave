"""The STAGE REVIEW (roadmap 3.4) — a human's corrections as WITNESSES.

Sean, 2026-09-23: *"corrections as witnesses — I mainly want this information
so that we can then use it to determine how to refine the build, rules and
decisions — structurally. All of the info would be given to you to turn into
fixes."*

Two lanes on one contract, the review-actions sidecar (`SIDECAR.md`):

  (A) this package — `human_evidence.py` ingests the sidecar into a record,
      `rerun.py` re-runs ADJUDICATE→EXPORT off the saved record and diffs,
      `feedback.py` writes the session-readable feedback file.
  (B) the viewer that WRITES the sidecar.

⚠️ NOTHING HERE MUTATES A MACHINE ROW AND NOTHING HERE OVERWRITES A VERDICT.
A human correction is an appended Observation with its own reader; a
disagreement with a verdict is an Observation filed against the verdict's
subject naming the verdict id. The stages then RE-DECIDE over a record that
holds both readings, and what they do with the human's row is MEASURED rather
than assumed — `rerun.py` reports a human row that reached no verdict beside
the ones that changed something, because a witness that changed nothing is the
finding roadmap 3.4 exists to collect.

⚠️ REGISTERED IN `reach.NOT_A_STAGE`. These modules report on quantities and
run outside the pipeline; a staged `.py` in neither list breaks
`reach.unaccounted_modules()`.
"""
