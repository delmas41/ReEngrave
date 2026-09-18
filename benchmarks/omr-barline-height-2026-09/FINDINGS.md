# A barline does NOT run a system's full height — and it is publisher-dependent

2026-09-17. **No code outside `benchmarks/`.** One probe,
`probe_barline_height.py`, two documents, no re-gather.

## 0. WHY IT WAS ASKED

Sean, on being shown that CLAUDE.md's bracket claim is recorded elsewhere in
the tree as an error:

> *"A barline goes all the way through a system at the beginning and end of
> the system but not necessarily in the other bars in the system. Right?"*

The sentence under test is `CLAUDE.md:4896-4897`, and it is the stated
justification for a LIVE rule:

> *"A barline runs a system's full height and the bracket encloses exactly
> it, so a column inked through the whole gap VETOES a gap-based break."*

The BRACKET half is already recorded as false in
`benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md:127`
(*"is FALSE and is an error in our CLAUDE.md"*). This asks whether the
BARLINE half survives, because the veto rests on it.

## 1. THE CONVENTION, IN A FORM A READER CAN TEST

A barline's height is a function of **where in the system it stands**. The
systemic barline at the left edge joins every staff. Interior barlines are
continuous **within an instrument family** and broken between families — MOLA:
*"barlines continuous within each family of instruments"* — which is the same
fact `OMR_BRACKET_COLUMNS` already leans on from the other side, inferring
family boundaries from **where interior barlines stop**.

## 2. METHOD, AND THE FILTER IS THE CONVENTION ITSELF

For each system, the inter-staff GAPS are taken between one staff's bottom
printed line and the next staff's top line. A barline candidate is an x-column
inking **every staff BODY** — that is the convention doing the filtering, and
it is what separates a barline from a column of aligned stems: an interior
barline is drawn in every family, so it crosses all five lines of every staff
and skips only the gaps BETWEEN families.

⚠️⚠️ **THE FIRST CUT REQUIRED ONLY HALF THE BODIES AND WAS WRONG IN THE
DIRECTION THAT FLATTERED THE ANSWER.** It reported **18-33 "barlines" per
system** on systems that print at most nine bars — the interior population was
mostly stem columns, which lowers the measured crossing rate and pushes the
result toward the conclusion under test. Tightened to every staff body, the
counts fall to 2-15 per system, which is a bar count.

## 3. THE RESULT — Sean is right on Litolff, and it does not transfer

**Litolff Beethoven 5 pp.1-4**, 75 staves, 7 systems:

| position in the system | n | crosses EVERY gap | crosses none | median share |
|---|--:|--:|--:|--:|
| **FIRST** | 7 | **7 — 100%** | 0 | 1.00 |
| **interior** | 68 | **0 — 0%** | 1 | 0.71 |
| **LAST** | 7 | 4 — 57% | 0 | 1.00 |

**Breitkopf Brahms 1 pp.0-3**, 97 staves, 7 systems:

| position in the system | n | crosses EVERY gap | crosses none | median share |
|---|--:|--:|--:|--:|
| FIRST | 7 | **0 — 0%** | 0 | 0.92 |
| interior | 35 | 4 — 11% | 2 | 0.92 |
| LAST | 7 | **0 — 0%** | 0 | 0.92 |

**On Litolff the convention holds categorically**: every first barline crosses
every gap, and **not one of 68 interior barlines does**.

⚠️⚠️ **On Breitkopf position does not separate at all.** Nothing crosses every
gap — the first barline included — and all three populations sit at a median
0.92. Whatever that plate does at its system edge, it is not "full height".

## 4. WHAT THIS SETTLES

**`CLAUDE.md:4896-4897` is false on both documents.** Interior barlines cross
every gap 0 of 68 and 4 of 35. The sentence describes no barline on the
merging plate and no barline at all on the other.

⚠️ **The RULE it justifies is not thereby wrong.** The veto reads *a column
inked through the whole gap*, and on Litolff the systemic barline supplies
exactly that, 7 systems of 7. What is false is the REASON printed beside it —
which is the dangerous kind of error, because anyone reasoning forward from
that sentence (to build bracket detection, or to expect interior barlines to
span) is misled by a rule that works.

⚠️ **Sean's statement is itself publisher-dependent**, which neither he nor
this probe assumed going in: it is a house convention of the Litolff plate,
not a universal.

## 5. WHAT IS NOT ESTABLISHED

* **n = 2 documents, 2 publishers, 14 systems.** Nothing here says which
  behaviour is the common one.
* **Nothing was changed.** No rule, no constant, and CLAUDE.md is untouched —
  the correction is recorded, not applied.
* **The candidate finder is not a barline detector.** It finds x-columns
  inking every staff body; a systemic bracket, a long slur column or a
  brace could in principle qualify, and none was excluded by hand.
* **Why Breitkopf's first barline falls short of every gap is unexamined** —
  one persistently uncrossed gap would produce exactly this, and no crop was
  cut to find out.
