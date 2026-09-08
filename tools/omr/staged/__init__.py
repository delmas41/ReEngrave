"""The staged pipeline — GATHER · ADJUDICATE · EVALUATE.

An alternative path built ALONGSIDE `tools/omr/transcribe.py`, selected by
`OMR_ADJUDICATE`. With the flag off nothing in here runs and the existing
pipeline is untouched.

Design: `docs/architecture-design-2026-09-07.md`.
Assumptions made during the build, for the tester: `ASSUMPTIONS.md`.

⚠️ NOTHING HERE HAS BEEN MEASURED. Not one accuracy arm has been run against
it. Every ordering, every constant and every precedence rule is an ASSUMPTION
recorded in ASSUMPTIONS.md, and the point of writing them down is that they
are what the testing phase will attack.

The three stages, and what distinguishes them:

    GATHER      produces MEASUREMENTS. A measurement is a quantity read off
                the raster that does not require any other reading to be
                true. It is never a name: `pos_float = 5.47`, not `E4`.
                Readers emit rows; they conclude nothing.

    ADJUDICATE  produces NAMED FACTS. A decision is a pure function of the
                gathered record plus earlier-adjudicated facts. It reads no
                raster. It returns a value AND a record of what it saw --
                including when it abstained.

    EVALUATE    produces CONSEQUENCES. When a decision settles, other facts
                that were computed against the old answer must be restated:
                a clef settles, so pitches restate; a key settles, so
                accidentals respell; a part boundary settles, so parts join.
                Downhill only, one pass, no fixpoint.
"""

from .record import (  # noqa: F401
    ABSTAIN, READERS, Abstention, Kind, Log, Observation, Outcome, Q, Scope,
    State, Subject, Verdict,
)
