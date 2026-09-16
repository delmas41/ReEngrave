<!--
PROVENANCE: this file is the PR #41 description, transcribed verbatim into the
place this repo's convention puts it. The measuring session's environment
refused both the Write tool and a shell heredoc, so it put its whole write-up
in the PR body instead and said so. Nothing here was re-derived, re-worded or
added by the transcribing session: the text is the measuring session's own, and
every figure in it is that session's. The only edits are this note and the
removal of the PR trailer.
-->

# `OMR_WHOLE_REST_INK` on the SECOND PUBLISHER — the cuts do not transfer

**No code under `tools/` changed. No constant moved. No flag flipped.** The
knobs-table row for `OMR_WHOLE_REST_INK` asks for exactly this — *"Breitkopf
Brahms 1 p0-3 is where it should be re-measured"* — and the answer is that the
rule's **outcome** survives and its **stated safety case does not**.

⚠️ **This is the one staged repair that DELETES music**, and it shipped
default-ON from n = 1 document. Everything below is about whether that evidence
travels.

## The receipt

Record md5 computed here is **`52b98f1cdfee3b39f10e56c592828ea4`**, which
matches the receipt in `benchmarks/omr-shared-records-2026-09/FINDINGS.md`.
`rhythm.py` and `export.py` are **byte-identical between the measured tree
(`669d25dc`) and `origin/main`**, checked rather than assumed — so these
figures describe the rule that is on main today.

## The probe IS the decision, established in both directions

*Backwards*, onto the document the cuts came from: it reproduces the shipped
derivation to the third decimal (`0.460 / 0.840 / 1.631 / 3.087`) and **25
fires at `slot 20 / neighbour 5`**, the published figures.
*Forwards*: its **12 Breitkopf fires are subject-for-subject identical** to the
12 `notehead_is_a_whole_rest: true` verdicts the record already holds.

## What changed between the two publishers

| | Litolff (cuts came from here) | **Breitkopf** |
|---|--:|--:|
| `restWhole` population | 395 | 398 |
| **the shipped band over that document's OWN whole rests** | **89.9%** | **52.5%** |
| …refused as WIDER than the max aspect | 4.8% | **42.5%** |
| `restWhole` standing OUTSIDE their own staff | 3.5% | **18.3%** |
| …more than a space BELOW it | **0** | **64** |
| witness split of the fires | **slot 20 / nb 5** | **slot 1 / nb 11** |
| fires standing outside their own staff | 3 of 25 | **11 of 12** |
| **hand-adjudicated as a WHOLE REST** | **25 of 25** | **1 of 12** |

Max height p95 moves `0.840 → 0.670` and max aspect p95 `3.087 → 4.633` — the
two cuts move in **opposite** directions. Only `MIN_ASPECT` transfers.

**The neighbour witness is the mechanism.** It rests on *a tacet part prints a
whole rest in every bar* — a claim about rests INSIDE their own staff. On this
plate 64 `restWhole` rows sit more than a space below their own staff (Litolff
has zero), so the witness corroborates cross-staff crop contamination with more
of the same. That is the *correlated witnesses* hazard with the correlation
running through the **measure-cell crop**.

## All 12 cropped, behind a frame control that CAN fail

Passed at **+133 to +229 grey levels** on every page carrying a fire.
Adjudication row-by-row in `adjudicated-12-fires.json`:
**1 whole rest · 8 upper hooks of eighth rests on the staff below · 2 real
noteheads on a neighbouring staff · 1 top arc of the printed `6` of the `6/8`.**

⚠️ **The record corroborates the hand verdicts on 8 of 12 from an independent
direction** — page-pixel overlap with **no class matching** — the staff below
reading `restWhole` (IoU 0.57), `rest8th` ×6 and `noteheadHalfInSpace`
(IoU 0.69) on the same ink. It was not consulted while the crops were read.

⚠️⚠️ **The one real note among the fires is spared by a DIFFERENT mechanism.**
`glyph/1/1/5/7/11` is a printed hollow notehead with an augmentation dot;
**both of this rule's witnesses accepted it**, and only the 2026-09-11
ownership contest keeps it in the file.

## The arm — and why it takes 4 seconds, not 2.5 hours

A plain re-export is normally BLIND to an ADJUDICATE change and this is one.
It does not apply here for a checkable reason: `grep -rn
NOTEHEAD_IS_A_WHOLE_REST tools/ --include='*.py'` returns the declaration, the
producer, the `ORDER` entry and **exactly one reader, `export.py:542`**, with
the flag read at EXPORT time.

pitched `<note>` **2,524 → 2,513**, **11 removed / 0 added**,
`ink_is_a_whole_rest` 0 → 12, `owned_by_another_staff` 294 → 293 —
**12 = 11 + 1 to the unit**. ⚠️ The structural control **FAILED** and its
residue is one `<backup>` (a bar that stopped being two-voice);
`two_voice_bars 71 → 70` says the same from the other side. **The strip was not
widened until it passed.**

All 11 removed notes are spurious readings, so **the rule's outcome is good
here and its reason is wrong eleven times in twelve.**

## The false-negative side, which nobody had looked at

Of 248 non-fires POSITION already vouches for, ranked by fractional excess over
the cut they failed, **the closest is a REAL WHOLE REST at the slot** — its box
clips the rest's left half so the aspect reads **1.51** against the 1.63 floor,
and the record exports it as an **eighth note C5**. Sean's original observation,
un-repaired on this publisher.

## Two hardenings, priced — a MEASUREMENT, not a recommendation

| | Litolff (25 adjudicated) | Breitkopf (12 adjudicated) |
|---|---|---|
| SHIPPED | 25 fires, 25 whole rests | 12 fires, 1 whole rest |
| + glyph must stand **inside its own staff** | 22 fires, **22 whole rests** | **1 fire** (the time-sig digit) |
| + **slot witness only** | 20 fires, 20 whole rests | 1 fire |

One predicate, no new constant, true on 22 of 23 fires across both documents
instead of 26 of 37 — ⚠️ **at a measured cost of 3 correct Litolff catches and
11 useful Breitkopf deletions put back.**

## The dotted rest — answered on the same record, no arm needed

`benchmarks/omr-staged-dotted-rest-2026-09/FINDINGS.md` moved ZERO verdicts on
Litolff, blamed reach, and named this document, which fires **656** dots.
The repair is already in the tree the record was gathered on, so the record's
own verdicts carry it:

**656 `aug_dot` rows, 1,129 decided rest durations, exactly ONE dotted rest**
(Litolff: 35 → 0). The **454 dotted NOTES of 2,828 (16.1%)** are the positive
control. ⚠️⚠️ **And that one firing is a FALSE dot** — the **smallest `aug_dot`
of all 656** (0.180 staff spaces against a 0.490 median) on a crop showing a
clean undotted whole rest. **691 rows across two publishers attach to a rest
once, and that once is wrong.** Not an argument for reverting it; an argument
that no work should be ranked by it.

## Recommendation vs measurement

**Leave the flag ON** — it is doing net good on both documents measured, and
turning it off puts 11 spurious notes back here and 22 on Litolff. **But stop
quoting *"25 of 25, zero real notes"* as its safety case**: that is a Litolff
figure. The transferable statement is weaker — *it removes ink that should not
have been written as a note, usually for the wrong reason.*

## What is NOT established

That the rule is wrong to be on; accuracy of the 11 removed beyond their ink;
that a third publisher behaves like either of these (**n = 2 documents, 7
pages**); anything about the ENGRAVED family; and **no OMR-NED figure is
claimed, deliberately** — the metric is symmetric and would pay for these
deletions whether or not they were right. The adjudication is **one reader's**,
this session's, corroborated by the record on 8 of 12.

## Process notes

* **Priority 2 (the meter-carry re-run) was DROPPED mid-flight** on the
  coordinator's instruction, after `89620d27` landed the same arm on the same
  document and measured **reach zero** — the meter is decided on 7 systems of 7,
  so neither flag has a domain here. Two arms had run 20 minutes and were killed
  **by PID** (never by name).
* ⚠️ **`benchmarks/**/crops/` is gitignored and always has been**, despite an
  earlier commit message claiming crops were committed "1.5 MB on purpose".
  The crop *verdicts* are committed; `probe/whole_rest_crops.py` reproduces the
  images.
* ⚠️ **The measuring session could not write this file**: its environment
  refused both the Write tool and a shell heredoc, so it put the whole write-up
  in the PR #41 description and said so there. **This file IS that description,
  transcribed** by the coordinating session before merge — see the provenance
  note at the top. The CLAUDE.md section and the probe docstrings carry the
  same reasoning. ⚠️ The bullet that stood here said *"no FINDINGS.md is in
  this PR"*; leaving it would have been the `fixed-then-kept-open-in-prose`
  pattern this file's own §process notes name, inside the file that closes it.
* The knobs-table row's satisfied work order (*"Breitkopf … is where it should
  be re-measured"*) was replaced rather than left standing — otherwise it is
  the `fixed-then-kept-open-in-prose` pattern this file records repeatedly.
