# ROADMAP 2.21b — Sean's three-rule voice-count convention, built

PATH: STAGED. Branch `claude/voice-split-2.21b`, off `origin/main` `824e1904`
(the commit carrying Sean's answer). Per CLAUDE.md 2026-09-29: *"our process
spends too much time and context on pricing runs"* — this lane is proved
with microscopic RED→GREEN tests only, no re-gather, no base-vs-arm run.

## The convention (`docs/DECISIONS.md` 2026-09-29, Sean, answering the 8
crops in `QUESTION.md` — all 8 are ONE voice)

1. **Same beat, opposite stems, is ALWAYS two voices.**
2. **Two voices not lined up are recognised because EACH stream sums to a
   FULL measure on its own AND the two sit apart on the staff** (one above,
   one below).
3. **A single line whose durations sum to one measure is one voice** —
   *"those crops would obviously be 1 voice because the measure math adds
   up to 1 measure."*

Neither fits → ABSTAIN (rule 8), the bar held as today.

## Where: `adjudicate_voices` (`tools/omr/staged/adjudicators/rhythm.py`)

Order, exactly as the manager specified: rule 1 decides outright; else rule
3 (one line, sums) is tried before rule 2 (two full separated streams),
because it is the simpler, more committal claim. `voicing.
split_events_into_voices` (LEGACY) is still CALLED for the candidate split,
never restated — only whether its answer is KEPT is new.

- **Rule 1** (`_voices_overlap_in_time`, unchanged from the withdrawn
  `claude/voice-split-2.21` attempt): some up-stem event and some down-stem
  event share a page-frame onset, preferring `Q.ONSET_COLUMN` when decided
  for the bar, falling back to this staff's own page x under the same
  measured tolerance.
- **Rule 3 / Rule 2** (new): `_meter_in_force` reads `Q.METER` at the
  system ancestor — DECIDED under any reason, `voted` or `carried` — resolved
  to the right segment with `meter_at` (a system may print a change
  mid-system; the top-level numerator/denominator describe only the FIRST
  segment). `_sum_beats` sums one representative glyph's `Q.DURATION.beats`
  per event. `_vertically_separated` compares the RANGE (not the mean) of
  `Q.NOTEHEAD_STAFF_POSITION` — a CLEF-FREE geometric measurement — between
  the two candidate streams; the range was chosen over the mean because a
  mean can agree while individual heads interleave, and this project's own
  history (rung readings, clef guesses) is full of cases where an aggregate
  hid a real exception.
- No meter in force → abstain immediately (rules 2/3 both need one; rule 1
  does not, and is tried first regardless).

## `adjudicate.ORDER` (`tools/omr/staged/adjudicate.py`)

`Q.METER` moved from after `Q.WEDGE_ANCHOR` to directly after `Q.EVENT`
(the ONLY ADJUDICATE-stage verdict it wants), and `Q.ONSET_COLUMN` moved
from after `Q.VOICES` to directly after `Q.METER` — both now before
`Q.VOICES`. **A first attempt put `Q.METER` before `Q.EVENT`** (reusing
2.21's old reasoning that `Q.METER` only "costs nothing to move up") **and
`inventory --check` caught it in one line**: `Q.METER` itself wants
`Q.EVENT` (a bar-sum-derived reading when the printed meter digits are
ambiguous), so putting it first would have handed `adjudicate_meter` a
`None` every run — this run's own instance of the fault `Q.WEDGE_ANCHOR`'s
comment already names for a different quantity. Fixed: `Q.EVENT` stays
first, `Q.METER` second, `Q.ONSET_COLUMN` third, `Q.VOICES` fourth.
`inventory --check`: 10 open, 0 not on `KNOWN_GAPS` (unchanged from main).

## Tests, `tools/omr/tests/test_staged_voices.py` — RED confirmed by

reverting BOTH production files to `origin/main`'s content with the NEW
test file in place: **7 of 7 new/changed tests failed** (`two_voices` where
the new reason strings were expected, or a DECIDED verdict where the new
code abstains), the other **14 unrelated tests stayed green as controls**
(stem-direction geometry, `nothing_to_split`, the one-direction/no-conflict
case, the exporter-reads-it checks). Restoring the branch's own code:
**21 of 21 pass.**

The manager's five scenarios, by test:

| scenario | test | result |
|---|---|---|
| single flipping line, sums to the bar | `test_RULE_3_a_flipping_line_that_sums_to_the_bar_is_ONE_voice` | `one_voice_sums` |
| same beat, opposite stems | `test_RULE_1_SAME_BEAT_opposite_stems_are_TWO_voices_no_meter_needed` (no `Q.METER` injected at all — proves rule 1 needs neither meter nor duration) | `two_voices_same_beat` |
| two offset streams, each full, upper above lower | `test_RULE_2_two_offset_full_streams_UPPER_ABOVE_LOWER_are_TWO_voices` | `two_voices_separated_and_full` |
| two offset streams, each full, INTERLEAVED in height (Sean's own control) | `test_RULE_2_CONTROL_two_full_streams_INTERLEAVED_IN_HEIGHT_ABSTAINS` | `Outcome.ABSTAINED` / `no_voice_convention_fits` |
| neither sums | `test_NEITHER_SUMS_ABSTAINS` | `Outcome.ABSTAINED` / `no_voice_convention_fits` |

Plus one more not asked for but load-bearing: `test_NO_METER_ABSTAINS_
before_rules_2_and_3_are_even_tried` (rule 1 does not fire, no `Q.METER` at
all → abstains with `detail["why"] == "no_meter"`, never falls through to
guess). The rest-duplication tests (`test_a_REST_is_in_EVERY_voice...`)
were rebuilt on rule 1 (same beat), which needs neither meter nor duration,
keeping them the simplest possible fixture for a mechanic unrelated to the
new rules.

Every fixture injects `Q.STEM_DIRECTION`, `Q.DURATION`, `Q.METER` and
`Q.NOTEHEAD_STAFF_POSITION` directly as already-DECIDED verdicts/
observations (the `test_staged_measure_rest_left_the_bar.py` precedent),
rather than driving the real geometric readers — each test isolates
`adjudicate_voices`'s own gate, not the upstream mechanisms that feed it
(those are covered on real records elsewhere: `Q.ONSET_COLUMN`'s
`onset_column` path and all 17 of 2.19's `V`-necessary bars on Breitkopf p1
were confirmed `one_voice_no_overlap`-equivalent by eye against 8 crops in
the withdrawn `claude/voice-split-2.21` — see `QUESTION.md`'s crops, which
this lane's convention agrees with: all 8 read as one line).

## Gates

Fast tier: main's own count + 7 net new tests (5 base + 2 rewritten from
the withdrawn attempt's test count — `TestTheVoiceSplit` grew from 6 tests
to 11), 0 failed (`out/pytest-fast-2_21b.txt`). `python3 -m
tools.omr.staged.check`: **TOTAL 247, unchanged.** `inventory --check`: 10
open, 0 not on `KNOWN_GAPS`.

## Overlap with ROADMAP 2.27c (concurrent, displaced-rest voicing)

Noted in `adjudicate_voices`'s own docstring: 2.27c touches rest PLACEMENT
within an already-decided voice in `export.py`; this lane is confined to
the voice COUNT decision in ADJUDICATE, upstream of that. No file overlap
expected — both lanes touch `voicing`-adjacent code, so whichever lands
second should re-read the other's FINDINGS before assuming independence.

## What was NOT done (per CLAUDE.md 2026-09-29)

No re-gather, no base-vs-arm pricing run, no fresh crops. The withdrawn
`claude/voice-split-2.21` branch already measured this convention's SHAPE
against two real saved records (Breitkopf p1: 145→145 held, identical cell
set, all 17 `V`-bars correctly one-voice; Litolff p1-p4: 270→265, 7
released, 2 newly held for a genuine reason) under the OLDER rule-1-only
gate; a fresh pricing run under the FULL three-rule gate is future work,
not owed by a microscopic-tests lane.

## Files

- `tools/omr/staged/adjudicators/rhythm.py`: `_event_page_x`, `_voices_
  overlap_in_time`, `_meter_in_force`, `_meter_quarters`, `_sum_beats`,
  `_sums_to`, `_vertically_separated`, `adjudicate_voices` rewritten.
- `tools/omr/staged/adjudicate.py`: `Q.METER` and `Q.ONSET_COLUMN` moved
  before `Q.VOICES` (and after `Q.EVENT`, which `Q.METER` itself wants).
- `tools/omr/tests/test_staged_voices.py`: `_v`, `_direction`, `_duration`,
  `_meter`, `_spacing`, `_position` helpers; `TestTheVoiceSplit` rebuilt to
  11 tests.
