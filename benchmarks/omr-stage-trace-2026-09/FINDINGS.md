# The stage trace: what each stage DID to one symbol, and where the loss actually falls

**2026-09-18.** Sean asked for *"a systematic process for walking each symbol
through the whole process and testing what each stage does to the recognition"*,
starting with noteheads because *"historically we have been best at recognizing
notes."* Phase 1: the instrument, calibrated on noteheads.

```bash
python3 -m tools.omr.staged.trace --check
python3 -m tools.omr.staged.trace --run rec.json --subject glyph/1/0/2/4/1
python3 -m tools.omr.staged.trace --run rec.json --family note
```

⚠️ **PROVENANCE.** The measuring session was a subagent and the harness refused
it a findings file, as the handoff warned. Its synthesis is in commit
`cd18d5d8`'s message and its raw output under `out/`. This file is that record
transposed at integration; everything marked **[mgr]** was re-derived by the
managing session from the committed output rather than relayed. **The commit
message is the primary source.**

---

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED**: nothing about engraving — this is an instrument, not a reader.
**FALSIFIED BY**: failing to reproduce CLAUDE.md's own hand-written five-stages
worked example. It reproduces it to the value (below).
**NOT CONFIRMED WITH SEAN**: the two live faults in §5 are reported, not fixed;
both are another lane's file and a default-affecting call.

## 1. WHY IT WAS NEEDED — verified, not assumed

There are **ten** derived checks and **every one is aggregate and static.** The
complete set of value-taking options across all of them is `--out`, `--run`,
`--root`, `--scan`. **None can be given a SUBJECT and asked what happened to
it.** That is why the wiring keeps passing while the surprises keep coming: the
connections are verified in the abstract and nothing replays one symbol.

⚠️ **POSITIVE CONTROL: it reproduces CLAUDE.md's own hand-written five-stages
example to the value, unprompted** — and carries a step the hand trace omitted
(`stem_direction` abstained there, `stems_disagree`, 0 of 5 rows read). It then
reproduced a **second** documented case on Breitkopf, `glyph/1/1/5/7/11`, where
the whole-rest rule accepts a printed note and only the ownership contest saves
it — both rules and the final owner on one screen.

## 2. ⚠️⚠️ THE NOTEHEADS FUNNEL — AND THE LOSS IS NOT RECOGNITION

**[mgr] Re-derived from `out/funnel-note-litolff.txt` and
`out/funnel-note-breitkopf.txt`.** Both balance on the exporter's own equality.

| | Litolff | Breitkopf |
|---|--:|--:|
| population (its own ink) | 2,347 | 3,337 |
| `<note>` **written** | **965 (41%)** | **2,513 (75%)** |
| refused `staff_not_identified` | **783** | **0** |
| refused `no_pitch` | **205** | **0** |
| refused `duration_narrowed` | 335 | **537** |
| `stem_direction` abstained | 904 (38.5%) | 1,546 (46.3%) |

⚠️⚠️ **ON LITOLFF THE DOMINANT LOSS IS IDENTITY, NOT READING.**
`staff_not_identified` + `no_pitch` = **988**, and both are **ZERO on
Breitkopf**. Those notes were gathered, decided, pitched and arbitrated —
**they are absent from the file because nobody could NAME THE STAFF.** An
identity shortfall wearing the shape of a reading one.

⚠️ **`staff_not_identified` is `OMR_HOLD_OUT_UNIDENTIFIED` WORKING AS
DESIGNED** — default-ON by Sean's own call (*"hold out — I want truth"*),
because emitting a part for an unnamed staff is a positive claim that invents an
instrument. **So the 41% is not a measure of how well that page was read.** The
music is counted rather than swallowed, which is the flag's whole point.

⚠️ **On Breitkopf the dominant loss is `duration_narrowed` (537) — which is
INFER's exact population, and INFER is default OFF.** Two publishers, two
completely different bottlenecks, neither of them the detector's recall.

⚠️⚠️ **CAVEAT THAT BOUNDS THE 65%: three of the five export refusal reasons
POOL noteheads with rests**, so no notes-only partition closes from the
report — the exporter's balance is `events_in_log 2993 = written 1472 +
not_written 1521` for notes AND rests together. **Inventoried, not computed
around.** The direction of the finding is unaffected (both pooled reasons are
zero on Breitkopf) but the exact share is not a notes-only figure.

### What the funnel shows that no aggregate tool does

Per stage it separates **rows written** (what the stage DID) from **STAND**
(subjects whose FINAL answer it owns), with the direction of each move —
`first_answer`, `changed_the_value`, `collapsed_a_narrowing`. That is what makes
stage-correction visible: on Litolff **EVALUATE changes 50 duration values and
collapses 5 narrowings**, and **`pitch` changes 186 values as `reowned`** — the
ownership repair reaching pitch, which no net count would show.

## 3. ⚠️ ABLATION VERSUS TRACE — the brief's framing, corrected in the module

**Exactly 1 of 4 row-writing stages is genuinely ablatable** (`OMR_INFER`).
`export.py` reads ADJUDICATE's verdicts, so **there is no GATHER-only arm**:
switching a stage off yields **no file, not a worse one**. Stated at the head of
the module rather than worked around, and Sean's *"add each step progressively"*
was not silently redefined.

## 4. ⚠️⚠️ A STAGE CLAIMS THE PAGE IS EMPTY WHILE A WITNESS SHOWS INK — 2,377 TIMES

**[mgr] Re-derived from `out/empty-claims-litolff.txt`.** Litolff: 2,476 such
claims on the record, of which **2,377 are CONTRADICTED**:

| quantity / reason | n |
|---|--:|
| `dynamic_letter/no_ink` | **997** |
| `beam_stroke/no_ink` | **980** |
| `stem/no_ink` | **400** |

⚠️ **`Q.INK` covers all 1,183 Litolff cells and its own `no_ink` fires ZERO
times** (excluded as the one honest use), **so every `no_ink` on that record is
false about the ink.** The honest contrast is on the same record:
`meter_glyph/no_detections`, 60 — a reader saying what it actually knows.

⚠️ Breitkopf reads **2,295** but **predates `OMR_INK`**, so its figure rests on
the weaker `Q.GLYPH_BOX` witness — **reported apart, never pooled.**

⚠️ This is the first use of `Q.INK` as a witness by anything, and it is exactly
what it was built for.

## 5. TWO LIVE FAULTS, REPORTED AND NOT FIXED

⚠️⚠️ **THE SHARPEST IS TEN LINES APART INSIDE ONE GATHERER, AND IT IS
BACKWARDS.** **[mgr] verified by reading `gather.py:1066-1081`:**
`gather.py:1070` writes **`ABSTAIN.NO_INK`** for a cell that **HAD detections**
and simply no dynamic among them (**997 firings**), while `gather.py:1079`
writes the honest **`ABSTAIN.NO_DETECTIONS`** for a cell with **no detections at
all** (3 firings). **The emptier case gets the honest word and the fuller case
gets the overclaiming one.** Not fixed: another lane's file, and a
default-affecting call.

⚠️ The companion instance is already documented in
[docs/diagnosis-2026-09-18-who-actually-decided-it.md](../../docs/diagnosis-2026-09-18-who-actually-decided-it.md)
§3 — `gather.py:1305-1311` recording a filter-rejected stem candidate as
`NO_INK`. **The trace turns that one observation into a population of 2,377.**

## 6. THREE CONTRADICTIONS WITH THE TREE

1. ⚠️⚠️ **`Q.PITCH` — the note family's own deciding quantity — HAS NO
   ADJUDICATOR.** **[mgr] verified: `grep "def adjudicate_pitch"` returns
   nothing.** Pitch is an EVALUATE consequence (`restate_pitch`, position +
   clef), which is correct by design — but it means a `subjects_from`-only
   derivation reports **the best-read family in the project as DEAD.**
2. **Three of five export refusal reasons pool noteheads with rests** (§2).
3. `reach --check` had no baseline in the brief; a file-aside control proved the
   regression was the instrument's own, and registration fixed it.

## 7. TWO FAULTS THE TESTS FOUND IN THE INSTRUMENT ITSELF

⚠️ **`balanced` absorbed `unaccounted` into its own sum and therefore COULD
NEVER FAIL** — *a control that computes the wrong thing*, inside the tool built
to find them. And a fixture passing `id=""` to four verdicts stored one.
**Battery: 20 arms, 20 red, 0 survived**, restore verified.

## 8. ⚠️ WHAT IT CANNOT SEE

* **ACCURACY — the brief asked for it and it is not deliverable from these
  records.** Both are SCANS, and `page_truth` exists only for a page we RENDER.
  It needs **one ENGRAVED staged record** (LilyPond and weights are on this
  machine; a GATHER run, out of lane). **So this funnel says where symbols are
  LOST, never whether the survivors are RIGHT.**
* **Any GATHER change**, and **the DETECTOR** — the largest blind spot, and it
  points the same way the funnel does.
* n = 2 publishers, 8 pages. **No OMR-NED figure**, deliberately.
* Suite **4521 passed / 19 skipped / 0 failed** (base 4477/19); `inventory`,
  `health`, `wiring`, `capture`, `reach`, `brakes`, `trace --check` and
  `no_producer` all exit 0.
