# The reference should be the most-LABELLED system, not the most-frequent one

**`OMR_REFERENCE_MOST_LABELLED`, merged default-off 2026-09-06.** Closes a bug
that is live for anyone using the running system, not only for whole-work runs.

*(Written up by the coordinating session from the agent's report and its five
commit messages — its harness refused it a `.md` file. `PRE_REGISTERED.md` beside
this went through before any arm ran.)*

---

## The bug

Same PDF, same page, changing only which pages are in the run:

```
--pages 1     ->  12/12 staves correctly named
--pages 0-2   ->   4/12
```

**Two extra pages OF THE SAME MOVEMENT collapse it**, so this has nothing to do
with movements. Page 1 prints 12 staves; pages 2+ print **11**, because
`Violoncello e Basso` condense onto one staff. Over the run 11 recurs and 12 does
not, `slots.build_reference` picks the largest **RECURRING** system — the
condensed shape — and `slots.align`, which deletes on the reference side only,
then drops the twelve-staff system's **TOP** staff and slides every name up one:
`Corni` → Bassoon, `Timpani` → Trumpet.

⚠️ **The web app's own default `OMR_MAX_PAGES=5` reproduces this exactly.**

The insight: **condensation is what repeats.** A shape that recurs is
systematically the *reduced* one, so "largest recurring" selects against the
lineup you want.

## The fix, and the arm it refused

Build the reference from the system that carries the most **resolved labels** — a
system printing its full lineup with names is better evidence of what the parts
are than a shape that merely recurs.

⚠️ **Pure most-labelled was REFUSED on measured evidence**: it can pick a
reference *shorter* than a later system in the same run — Bote's Dvořák serenade
names a 5-staff opening and prints 6-staff systems afterwards, and `align` then
leaves the sixth staff at slot −1. **The shipped rule never shrinks the reference
below the recurring rule's pick.** `most_labelled="pure"` reproduces the refused
arm for anyone who wants to see it.

## Publisher convention — the kill criterion, answered first

The risk was a rule that works on one house's labelling convention. Measured over
**53 documents in 12 houses**, scoring whether the rule lands on the run's
*largest* system (what `build_reference`'s own docstring aims at):

| | picks the largest system |
|---|--:|
| all (n=53) | old 0.604 → **new 0.868** |
| documents that name nothing | **identical picks**, asserted |

**No house is worse at any point of the sweep, 14 documents disagree and all
resolve toward a LARGER reference, 0 shrink** under the never-shrink guard. Every
changed document is one shape: **the document's first system is both the largest
and the labelled one, and the recurring filter threw it away for occurring
once.** Simrock reads **0.750 under both rules** — a house the rule does not
REACH, not one it harms.

⚠️⚠️ **THE INCUMBENT'S RATE FALLS AS THE CORPUS GROWS, AND THE FIX'S DOES NOT.**

| n | old | new |
|--:|--:|--:|
| 24 | 0.708 | ~0.87 |
| 30 | 0.700 | 0.867 |
| 45 | 0.622 | 0.889 |
| **53** | **0.604** | **0.868** |

**That is the small samples having flattered the INCUMBENT, not the fix
improving.** The shape the old rule misses — a document whose first system is the
only labelled one — is common, and every house added keeps turning up more of it.
⚠️ **Any figure quoted from an early cut understates the bug**, and the same
caution applies to the next person's small sweep of anything else here.

⚠️ **The sweep's history is worth keeping because it moved in both directions.**
At n=27 Simrock read 1.000 on two documents; at n=30, with three, it read 0.667
under both rules; at n=53 it is 0.750 under both. At n=30 Litolff was flat at
1.000, which was the headline evidence that this is *not* a Litolff rule; from
n=45 it reads 0.800 → 1.000.

⚠️ **Read that Litolff movement carefully — it is not new independent support.**
The document that moved it is `beethoven--symphony-5--575951`, the **other scan
of the same Litolff plates** the fix was diagnosed on (sizes
`[12, 11, 11, 11, 8, …]`, labels `[12, 7, 7, 7, 4, …]` — the 12-then-11 shape
exactly; reference 11 → 12, named slots 7 → 12). So it is **an independent
instance of the same mechanism in the same edition** — not a second measurement
of the same page, and not an independent edition either. The claim "not a
Litolff rule" now rests on the other eleven changed documents, in Breitkopf,
Eulenburg, Ricordi, Universal, Durand and two Berlioz volumes.

Method note: the probe records each system's staff count and resolved label count
once per document (one staff detection + one Surya read per page, no
transcription), and all three rules are replayed over the *same recorded views* —
so no rule can win by re-reading a margin.

## Headline

End-to-end `transcribe`, Litolff Beethoven 5 / imslp984073, `--no-direction-text`
on every arm:

| | reference | full system named correctly |
|---|---|---|
| `--pages 1` off | 12 slots | 12/12 |
| `--pages 1` on | 12 slots | 12/12 (control) |
| `--pages 0-2` off | 11 slots | **4/12** |
| `--pages 0-2` on | 12 slots | **12/12** |

The control is stronger than an equal score: the two `--pages 1` result files are
**identical field-for-field** apart from wall-clock and a 0.2 ms timing. The
off-arm's confusions are the slide-by-one signature exactly (Oboe→Flute …
Violin→Timpani, one staff left at slot −1).

⚠️ **Pre-registration said 4/12 → 11/12 with an 11/12 control; both control arms
read 12/12 on this tree** — main's ambiguous-alias fixes (`c0a80ae7`, `fa8258c1`)
land the twelfth staff. Measured on the agent's own merge base, so both arms move
together and the delta stands.

**It also prices the case that could have LOST**: the condensed 11-staff pages,
which under the old rule align 1:1 and are named by construction. They *improve* —
pages 0-2 14/22 → **16/22**, pages 0-4 35/55 → **39/55** — because the old
reference took its labels from a page-2 system that names no strings at all.

## Safety

Default-off is not merely structurally unchanged: `probe_flag_off_identity.py`
runs `origin/main`'s `build_reference` against this tree's with
`most_labelled="off"` over **3000 random system sets — 0 differences**. Seven new
unit tests pin the bug, the fix, the abstention (no labels anywhere → today's
behaviour), the tie-break, the never-shrink guard, the env default, and why a
condensed reference *misnames* rather than under-names.

## ⚠️ What is NOT measured, stated plainly

**No scan-gate figure.** The machine was carrying two sibling whole-work runs
(load 30–45) and the two `scan_eval` arms had reached row 2 when the session ended.
Nothing in the branch reports a gate number and nothing should until they land.

**And a flat gate result would be coverage of nothing, not a clean bill.** This
was pre-registered as an argument and has since been settled **by measurement**:

> ⚠️ **The 20-row scan gate cannot exercise this flag — 0 of 20 references
> change.**

```
9 rows print ONE system                    both rules return it
beethoven p2/p4, brahms p3/p4,             two systems of EQUAL staff count, where
dvorak p7, bach p1                         (size, labels) and (labels, size) rank
                                           identically
beethoven p3 (11, 8)                       unequal — but the larger system is also
                                           the better labelled one (7 vs 4)
brahms p2 (14, 13)                         unequal — labels tie 12/12, size decides
```

A difference needs a page whose *smaller* system carries strictly more labels,
and this corpus contains none. **So a "no regression" report from the gate would
have overstated the evidence badly** — the same shape as the FILL and
roster-clef negatives, where a consumer's *population* rather than its quality
settled the question. The exposure probe costs ~15 s a row against ~2 min to
transcribe one.

**Confirmed under the pipeline's OWN reader, not a proxy: 0 of 20 under the
ladder AND 0 of 20 under Surya alone.** No hedge is needed — the two rows that
were briefly settled by construction were then measured and agreed:

```
mahler-sym5-mvt1-local-p5     systems=[21]      labels=[14]    ref 21/21   SAME
bach-brandenburg3-mvt1-p1     systems=[12, 12]  labels=[5, 0]  ref 12/12   SAME
```

Both `scan_eval` arms were then killed as a provable null. (They were suspended
with SIGSTOP first rather than pre-empted, so the decision stayed reversible
until the ladder result was in. **No partial gate figure was ever produced and
none should be quoted.**)

⚠️⚠️ **A fault found in the probe itself, and it is NOT hypothetical: THE PROBE
AND THE PIPELINE READ THE MARGIN BY DIFFERENT MEANS, AND THEY DISAGREED.** The
first exposure run used **Surya alone**; the pipeline runs a ladder (PDF text
layer → Surya → Tesseract). On `beethoven-sym5-mvt1-575951-p1` — **the one gate
row whose PDF carries a text layer** — **Surya alone resolves 12 labels and the
ladder resolves 11.** The two readers genuinely disagree on exactly the row the
mechanism predicts.

The verdict was unchanged (12 slots under both rules either way) — **but that
was luck, not design.** A probe whose correctness rests on a disagreement not
mattering is a probe that will eventually be wrong quietly. `--ladder` runs the
real `contextual._labels_for_page` chain and is now the default.

> **The findable form: the probe and the pipeline read the margin by different
> means, and the row where they diverge is the row with the text layer.**

⚠️ Relatedly: **all ten rows the roster's evidence came from are single-PAGE
runs**, the one regime this bug cannot occur in. That is why it went unseen.
