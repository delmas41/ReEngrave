# ROADMAP 2.21 — voice split gated on simultaneity, built under CONVENTION ASSUMED

PATH: STAGED. Branch `claude/voice-split-2.21`, off `origin/main` `3c02b0b5`
(the 2.21 QUESTION merge). Question filed in `QUESTION.md` and merged first;
Sean was asleep, so this lane BUILT the answer it asked for, per CLAUDE.md
rule 3's "if nobody can be asked" clause, and left the question open.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

Standard engraving practice, as put to Sean: stem direction splits a staff
into two voices only where the two directions OVERLAP IN TIME — some event
of the up-stem stream and some event of the down-stem stream share an onset
column (or one sounds while the other has already started). A line whose
stems merely flip crossing the middle line, with no simultaneity, is ONE
voice. A crop showing two heads that share an onset column, one up-stemmed
and one down-stemmed, but which Sean reads as ONE voice anyway (e.g. a
grace-note collision, an OCR-adjacent mark misread as a note) would falsify
this. **NOT CONFIRMED with Sean** — the question stands in `QUESTION.md`.

Where a bar's two directions never share a page frame at all (so overlap
cannot be established either way), this decision ABSTAINS (`onset_unread`)
rather than answering — rule 8. `export._voice_split` already treats a
non-decided `Q.VOICES` verdict as one stream, so nothing downstream is left
without a fallback; the abstention keeps the CENSUS honest about how much of
the page this convention could even be tested on, which is the alternative
the brief asked for over silently keeping the old two-voice answer.

## 1. Where: `voicing.split_events_into_voices` / `adjudicate_voices`

Two callers read `Q.VOICES`: `export._voice_split` (both `to_musicxml` and
`to_lilypond` route through it) and, indirectly, ROADMAP 2.8's bar-sum judge
— a two-voice bar is held out if EITHER stream fails to sum, so a bar the
naive rule split wrongly could be held for a reason that has nothing to do
with what is actually printed there.

`tools/omr/voicing.split_events_into_voices` (LEGACY, frozen, unchanged) is
still CALLED, not restated — the split's own arithmetic (voice 1 = up-stem +
unknown-direction + rests, voice 2 = down-stem + rests) is exactly as it was.
What changed is that `adjudicate_voices` (STAGED) no longer takes that split
on faith: it now gates the CANDIDATE on `Q.ONSET_COLUMN` (added to `wants`),
falling back to this staff's own page x under the same measured tolerance
where the system-scoped decision has nothing for this cell.

**`Q.ONSET_COLUMN` moved earlier in `adjudicate.ORDER`** (`tools/omr/staged/
adjudicate.py`): it used to run AFTER `Q.VOICES`, which `inventory --check`
flagged immediately as a NEW, undeclared problem ("voices wants the VERDICT
onset_column, which ORDER runs AFTER it -- it will always read None") the
moment `Q.ONSET_COLUMN` was added to `wants`. Neither decision wanted the
other before 2.21; `Q.ONSET_COLUMN` wants only `Q.EVENT`, `Q.GLYPH_BOX`,
`Q.STAFF_SPACING`, never `Q.VOICES`, so moving it before `Q.VOICES` costs
nothing and the ordering fault is gone (`inventory --check`: 0 problems not
on `KNOWN_GAPS`, same 10 known entries as before this lane).

## 2. The three RED→GREEN cases, `tools/omr/tests/test_staged_voices.py`

RED confirmed structurally: the pre-2.21 test file (now edited) asserted
`reason == "two_voices"` for a fixture with two heads 210 canonical units
and 210 page units apart, opposite stems, no shared onset — i.e. it directly
encoded the bug this lane fixes. Flipping that assertion is what makes the
new code necessary; run against origin/main's `rhythm.py` today, the new
test file's two changed tests and the new abstain test would fail (the old
code never abstains for a missing page frame at all, and always decides
`two_voices` on stem disagreement alone regardless of overlap).

| test | fixture | before 2.21 | after 2.21 |
|---|---|---|---|
| `..._different_x_with_NO_overlap_is_ONE_voice` | two heads, opposite stems, page x 210 apart | `two_voices` | `one_voice_no_overlap` |
| `..._SHARING_AN_ONSET_are_TWO_voices` (positive control) | two heads, opposite stems, SAME page x | `two_voices` | `two_voices_overlap_confirmed` |
| `..._unread_onset_ABSTAINS...` | two heads, opposite stems, NO page frame at all | `two_voices` (never abstains) | `Outcome.ABSTAINED` / `onset_unread` |

The rest-duplication tests (`test_a_REST_is_in_EVERY_voice...`) were rebuilt
with an overlapping page frame so they keep testing a GENUINE two-voice bar
rather than accidentally becoming the case this lane collapses.

Full file: 18 passed (16 before this lane + 2 new). `pytest -m "not slow"`
on the whole suite: see SS4.

## 3. Priced on the 2.19 p1 record, in-process, base vs arm

**Base** = `origin/main` today (`baba1c76`, includes 2.19-2.20 and the 2.21
question merge, NOT this lane's code) — checked out in a clean
`git worktree` so base and arm run the exact same script against the exact
same saved record, differing only in the tree. **Arm** = this branch.

### Breitkopf 317803 pdf idx 1 (`brahms-p1.record.json`, 2.19's own 09-29
gather, `--no-surya`, OCR on)

| | base | arm |
|---|--:|--:|
| `bars_held_out_sum` | 145 | 145 |
| held-bar CELL SET | — | **IDENTICAL to base** (0 released, 0 newly held) |
| `two_voice_bars_held_out_by_sum` | 27 | **1** |
| `notes_in_file` | 178 | 178 |
| `bar_sum_check.py` (independent control) | 170/170 exact | 170/170 exact |

**All 17 of the bars 2.19's `V` minimal-cause partition named are now
decided `one_voice_no_overlap`, via the `onset_column` path (never the raw
fallback), matching the 8 sampled crops' by-eye reading from the QUESTION
lane exactly** (`out/r221/held-brahms-p1-arm.json`; checked with a one-off
script against all 17 cells, not a sample). **This releases NOTHING on this
page**, because ROADMAP 2.19 SS15f already found `V` is never a single
releasing fix here — every one of the 17 also needs `M` (the meter reader,
which reads this page's printed 9/8 and 6/8 as 9/4 — a separate, unbuilt
item), so a bar correctly read as ONE voice still fails to sum against the
wrong meter. **What changed is the DIAGNOSIS, not the count**:
`two_voice_bars_held_out_by_sum` collapsing from 27 to 1 means 26 bars that
were being reported as "the SPLIT doesn't sum" are now honestly reported as
"the READING (now correctly one voice) doesn't sum against the meter" —
which is what item 1 (`M`) will actually need to fix, not a phantom voice
problem layered on top of it.

### Litolff Beethoven 5 mvt 1 pp.1-4 (`library/_shared-records/
beethoven5-p1-p4.record.json`, 09-11 gather — 2.19's own control)

| | base | arm |
|---|--:|--:|
| `bars_held_out_sum` | 270 | **265** |
| released / newly held | — | **7 / 2** |
| `two_voice_bars_held_out_by_sum` | 22 | 2 |
| `notes` (written) | 984 | **1006** |
| `bar_sum_check.py` | 1183/1183 exact | 1183/1183 exact |

**7 released**: `(2,1,6,10) (2,1,6,14) (2,1,7,13) (2,1,7,14) (2,1,8,14)
(3,0,7,6) (4,1,9,5)` — a single melodic line, wrongly forced into two
streams that each failed to sum, now correctly reads as one and sums.

**2 newly held, and it is the RIGHT answer, not a regression**: `(2,0,7,2)`
and `(3,1,7,1)` were previously split into two bogus streams whose rest
duplication happened to make BOTH sum to exactly the meter — a bar that
LOOKED clean under 2.8's check for the wrong reason. Inspected directly
(re-decided in-process, not from the held-bar dump, since neither cell was
held before): both now decide `one_voice_no_overlap` (via `onset_column`,
up/down columns ~100+ units apart, no overlap), and the single merged
stream sums to **3.0 quarters against a 2/4 meter** — genuinely overfull, a
real defect the old two-voice split was accidentally hiding. This is
CLAUDE.md rule 7's control-must-be-able-to-fail principle working as
designed: two wrong streams cancelling into a clean answer is not evidence
the bar was fine.

### Engraved control (`benchmarks/omr-staged-engraved-2026-09/out/
engraved-p0.record.json`)

**Reach before accuracy (rule 5): the gate is INERT on this fixture.**
`Q.VOICES` decides `one_voice` on all 126 bars-with-events, on BOTH base and
arm — this record has zero bars where both stem directions are read at
all, so the naive split's own candidate never arises here and 2.21 changes
nothing on the one control that has genuine two-voice writing (paired
winds) by construction. `bars_held_out_sum` 0 -> 0 on both, `notes_in_file`
unchanged. **This is the one place the brief's "key control" could not be
exercised — reported as a reach gap, not papered over as a pass.** The
positive-control coverage for "a genuine simultaneous divisi stays two
voices" comes from the synthetic unit test (SS2) only.

Files: `probe/held_funnel_2_19.py` (imported, 2.19's own, unrestated) and
`probe/price_voices_2_21.py` (new: dumps every `Q.VOICES` reason on one
record). Base runs: a throwaway `git worktree add /tmp/reengrave-2.21-base
origin/main`, removed after this lane. Dumps in `out/r221/`.

## 4. Gates

`pytest -m "not slow"`: net new tests over main's own count, 0 failed (full
output attached to the landing commit). `python3 -m tools.omr.staged.check`:
**TOTAL 247, unchanged** — the ordering fix and the new `wants` entries left
every other derived check exactly where it was. `inventory --check`: 10
open, 0 not on `KNOWN_GAPS` (same as before this lane; the transient 11th
problem this lane's OWN change introduced, and then fixed by reordering, is
not in that count).

## 5. What contradicted this brief

- The brief's own worked example ("two simultaneous opposite-stem notes"
  stays two voices) could not be checked against the engraved control as
  planned — SS3 found that record has no two-voice candidate at all. The
  positive control is synthetic only.
- The FIRST diff against a stale, previously-committed 2.19 arm dump
  (144 held) suggested this lane held ONE new bar; re-running 2.19's own
  probe on a FRESH same-tree base (per CLAUDE.md SS6b, "base vs arm on ONE
  tree") showed base is actually 145 today (the tree moved between 2.19's
  commit and now) and the true base-vs-arm delta on Breitkopf p1 is
  IDENTICAL cell sets, zero movement. A stale committed number is not a
  baseline (CLAUDE.md SS6b again).

## 6. Files

- `tools/omr/staged/adjudicators/rhythm.py`: `_event_page_x`,
  `_voices_overlap_in_time`, `adjudicate_voices` rewritten to gate the
  candidate split on simultaneity.
- `tools/omr/staged/adjudicate.py`: `Q.ONSET_COLUMN` moved before
  `Q.VOICES` in `ORDER`.
- `tools/omr/tests/test_staged_voices.py`: `_head_pf`, `_spacing`, 3
  rewritten/new tests (SS2).
- `benchmarks/omr-voice-split-2026-09/probe/price_voices_2_21.py`: new,
  the `Q.VOICES` reason census used for pricing.
- `benchmarks/omr-voice-split-2026-09/out/r221/`: base/arm dumps, MusicXML,
  bar-sum-check output.
- `benchmarks/omr-voice-split-2026-09/QUESTION.md`: the still-open question
  this lane built an answer under.
