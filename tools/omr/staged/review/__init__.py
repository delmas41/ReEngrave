"""ROADMAP 3.4 — the STAGE REVIEW.

Sean, 2026-09-23: *"a UI where it pulls up a staff on a system and shows me
everything it is gathering -- I give feedback by redrawing, deleting or
adding boxes -- then the next stage, you tell me what the stage is doing with
that information and I give feedback on what is working and what isn't --
each stage at a time, following the trail of information and decisions with
human feedback."*  And the purpose, his words: *"I mainly want this
information so that we can then use it to determine how to refine the build,
rules and decisions -- structurally."*

Two lanes, one contract -- the REVIEW-ACTIONS SIDECAR:

  (A) `human_evidence.py` / `rerun.py` / `feedback.py`  — ingest the sidecar
      into a record as human WITNESSES, re-run ADJUDICATE→EXPORT off the
      saved record, write the session-readable feedback file.
  (B) `server.py` + `static/`  — the viewer that WRITES the sidecar.

⚠️ A correction is a WITNESS, never an edit. Nothing in this package mutates
a machine row; the sidecar is append-only and a disagreement is filed against
a verdict id, never applied to it.
"""
