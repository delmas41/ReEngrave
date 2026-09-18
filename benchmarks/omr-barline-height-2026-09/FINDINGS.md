# How far does a barline actually reach? — CLAUDE.md's claim is false on both publishers, and Sean's is publisher-dependent

**2026-09-17/18.** ⚠️ **This directory held a probe and two output files and was
referenced NOWHERE** — found by an audit on 2026-09-18 asking whether every
benchmark added that day carries a `FINDINGS.md`. Its *measurement* was already
used (it is the evidence behind the `CLAUDE.md` system-grouping correction) but
the directory itself was orphaned. **An unlinked measurement is how a figure
gets re-derived a year later.**

`probe_barline_height.py`; outputs in `out/`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN
**ASSUMED**, Sean's own: *"A barline goes all the way through a system at the
beginning and end but not necessarily in the other bars."*
**FALSIFIED BY**: a plate where position does not predict reach. **Breitkopf is
that plate** (§2). **NOT CONFIRMED**: nothing here was put to him.

⚠️ **The candidate rule was tightened BY the convention before measuring** — a
barline inks every staff body and skips only the gaps between families. A looser
rule reported **18-33 barlines on systems printing at most nine bars**, i.e.
mostly stem columns, **and biased the result toward the conclusion.**

## 1. Litolff Beethoven 5 pp.1-4 — Sean's convention HOLDS

82 barlines. `crosses_all` = the column crosses **every** inter-staff gap:

| position | n | crosses ALL | crosses NONE | median share of gaps |
|---|--:|--:|--:|--:|
| **FIRST** | 7 | **7** | 0 | **1.000** |
| interior | 68 | **0** | 1 | 0.714 |
| **LAST** | 7 | **4** | 0 | **1.000** |

**7 of 7 first, 0 of 68 interior.** That is his statement exactly.

## 2. ⚠️⚠️ Breitkopf Brahms 1 pp.0-3 — POSITION DOES NOT SEPARATE, AND THE ORDERING INVERTS

49 barlines:

| position | n | crosses ALL | crosses NONE | median share |
|---|--:|--:|--:|--:|
| FIRST | 7 | **0** | 0 | 0.923 |
| interior | 35 | **4** | 2 | 0.923 |
| LAST | 7 | **0** | 0 | 0.923 |

⚠️⚠️ **CORRECTING THIS SESSION'S OWN SUMMARY**: the `CLAUDE.md` paragraph written
on 2026-09-18 said *"on Breitkopf position does not separate at all — **nothing
crosses every gap, first included**"*. **That is false. Four INTERIOR barlines
cross every gap while its FIRST crosses none** — so the ordering is not absent,
it is **INVERTED**. Corrected in place. The defensible claim is the median:
**0.923 for all three positions**, i.e. position carries no information on this
plate.

## 3. WHAT IT SETTLES — `CLAUDE.md`'s claim was false on BOTH plates

The system-grouping paragraph justified its rule with *"a barline runs a system's
full height and the bracket encloses exactly it."* **Both halves are false.** The
bracket half was already recorded as *"FALSE and an error in our CLAUDE.md"* in
`benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`; the
barline half is what this directory measures. ⚠️ **The RULE is unaffected and
still correct** — it is a one-sided veto that only needs a crossing column to be
*evidence* of a system, and where nothing crosses there is no veto. **The false
premise overstated WHY it works, never what it does.**

⚠️ **And Sean's own statement is publisher-dependent**: true on Litolff, absent
on Breitkopf. That is the useful form of it — not a universal convention but one
whose reach is a property of the plate, which is the same shape as *Litolff
MERGES and Breitkopf SHATTERS.*

## 4. ⚠️ NOT ESTABLISHED
n = **2 publishers, 8 pages, both scans**; the engraved family untouched. No
print was consulted — `crosses_all` is computed off the record's own
`Q.STAFF_LINES` and the detected columns, so a **misdetected** column is counted
like any other. Nothing was re-gathered. **No OMR-NED figure**, deliberately.
⚠️ The 2026-09-18 vertical-runs work later found that **a measure cell CLIPS a
barline's ends** (end offsets = the cell's padding), which does **not** affect
these figures — they are computed on gap crossings across staves, not on
endpoints — but it does mean **any future endpoint-based barline rule needs a
page-band reader**, not this data.
