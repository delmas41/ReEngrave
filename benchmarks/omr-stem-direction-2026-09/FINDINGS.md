# The stem direction: what ink can say, and what the STAFF cannot

2026-09-17. R3 of `docs/handoff-2026-09-17-brakes-and-the-unnamed-staves.md` —
*"`stem_direction/no_stem` — 904 and 1,546, the largest population on both and
the only one larger on the second publisher; evidence exists SIDEWAYS and no
rule takes it."*

**Shipped:** a second tier in `adjudicate_stem_direction` that borrows from a
head sharing the same BEAM. **Refused:** two other rules, each with its
number. **Found:** the convention Sean states is strong, and where it appears
to fail it is measuring something else — which makes it an AUDIT of the staff
grid rather than a reader of stems.

---

## 1. The population, split before it is a number

793 `no_stem` abstentions on Litolff Beethoven 5 pp.1-4.

⚠️ **9 of them are whole notes, and those abstentions are the decision being
RIGHT** — a whole note carries no stem. A rule aimed at the whole population
would be aimed partly at correct answers. The target is **784**.

| | |
|---|--:|
| `stem_projection` (decided by the head's own stem) | 1,443 |
| `no_stem` | 793 |
| `stems_disagree` | 111 |

⚠️ **A WHOLE NOTE HAS NO STEM; A HALF NOTE DOES** — hollow head, stem
attached. Read off the record rather than from memory: half notes get a stem
**309** times against **103** that do not, so those 103 are MISSES and not
convention. Only the 9 whole notes are correct abstentions.

### 1b. ⚠️⚠️ ABSENT, MISLABELLED, OR MERELY UNATTACHED? — mostly ABSENT

Sean, 2026-09-17: *"is the point that we don't see the ink or that we were
mislabeling it or that it was being disregarded?"* **This was not measured
before he asked, and the distinction decides the whole repair**: a stem that
is THERE but a few pixels outside the box-overlap test is an ATTACHMENT fault,
and fixing that would beat any downstream rule. `probe_is_the_ink_there.py`
asks how far the nearest stem row in the same bar actually is:

| distance to the nearest stem in the bar | heads | |
|---|--:|--:|
| touching | 1 | 0.1% |
| within ¼ staff space | 45 | 5.7% |
| ¼–1 space | 119 | 15.0% |
| 1–3 spaces | 247 | 31.1% |
| more than 3 spaces | 170 | 21.4% |
| **no stem ink ANYWHERE in the bar** | **211** | **26.6%** |

**Median gap 2.01 spaces.** So the population is **not** mislabelled and
**not** disregarded — it is ink we did not read. At most **6% look like an
attachment near-miss**, and widening the test past a quarter space starts
claiming the NEIGHBOURING note's stem, which is the fault the attachment
constant was measured to avoid in the first place.

⚠️ The same table shows the attachment test has false POSITIVES too: **8 whole
notes were given a stem**, and a whole note has none.

---

## 2. Three readings, and what each is worth

Every figure is scored on the **1,443 heads a stem already decided**, LEAVE-
ONE-OUT — a head is never part of the evidence that decides it.

| reading | accuracy | reach on `no_stem` |
|---|--:|--:|
| baseline, always the commoner direction | 0.506 | — |
| **where the beam SITS** relative to the head | 0.829 | 228 |
| **the CONVENTION** (above the middle line → stem down) | 0.787 | — |
| beam-mate, majority | 0.938 | 167 |
| **beam-mate, UNANIMOUS** ← shipped | **0.984** | **152** |

**The claim that works is physical, not geometric.** A beam joins stem TIPS,
so every stem hanging from one stroke points the same way. Asking *where is
the beam* tops out at 0.829; asking *what does a head on the same beam say*
reaches 0.984.

⚠️ **THE 0.829 RULE IS REFUSED RATHER THAN UNBUILT**, and the reason is the
consumer: `adjudicate_event`'s divisi guard reasons in its own docstring that
an UNKNOWN is better than a confident wrong answer. One head in six is not an
unknown.

⚠️ Unanimity costs 15 of 167 reach and buys 4.6 points. The `x`-CENTRE test
(rather than a box overlap) is worth 4 points on its own.

---

## 3. ⚠️⚠️ INFER IS THE RIGHT STAGE AND IT CANNOT SERVE THIS QUANTITY

Borrowing a neighbour's reading is BEST rather than FORCED, so the fourth
stage is where the claim belongs. It cannot go there:

    Q.STEM_DIRECTION   ORDER 17
    Q.EVENT            ORDER 21   ← reads it (the divisi guard)
    Q.VOICES           ORDER 22   ← reads it (the voice split)

INFER runs after **all** of ADJUDICATE, so a rule there would write the
verdict *after both readers had already looked*, and reach nothing at all.
**The handoff's "evidence exists sideways and no rule takes it" has a reason:
the stage that may take it runs too late.**

The tier therefore lives in ADJUDICATE and honours the boundary by its REASON
instead — `beam_mate` is a different word from `stem_projection`, so a
consumer, or a cleanup count, can separate what was read from what was
borrowed.

---

## 4. Sean's convention IS strong — and where it looks wrong it is measuring the GRID

Sean, 2026-09-17: *"the stem rules are very consistent unless there are
multiple voices per staff. If it is just one voice where the note falls
compared to the middle line of the staff determines direction."* Then, on
being shown 0.787: *"The convention is strong. The failure is elsewhere."*

He is right, and the split says so. Accuracy against the projected direction,
by **distance from the middle line** (in staff steps):

| distance | n | accuracy |
|---|--:|--:|
| 0-1 | 231 | **0.537** |
| 1-2 | 228 | 0.776 |
| 2-4 | 387 | 0.860 |
| **4-6** | 261 | **0.939** |
| 6+ | 336 | **0.765** |

**It rises steeply and then REVERSES.** The rise is the convention being
exactly what Sean says: at four to six steps clear of the middle line it
agrees 0.939, and on-grid there, 0.943. The two failures are at the ends and
neither is the convention's:

* **At the boundary (0-1 step), 0.537 — a coin flip.** A note on or beside
  the middle line is the one case where half a step of grid error flips the
  answer, and it is also where two-voice writing lives.
* **In ledger country (6+ steps), 0.765 — and it REVERSES the trend.** A note
  three spaces clear of the middle line is the *least* ambiguous case the
  convention has, so it cannot be the convention that fails there. ⚠️ Crossed
  with the position's own residual it does not move (off-grid 0.757, on-grid
  0.771), so it is not simple grid noise either. What lives out there is
  documented: heads standing in a neighbouring staff's padded cell — the same
  population `benchmarks/omr-phantom-notes-2026-09` measured as **14 of 25
  phantom notes standing OUTSIDE THE STAFF ALTOGETHER** — and 44% of
  ledger-country heads are off-grid against 11% inside the staff.

⚠️ **`glyph_owner` does NOT explain it** (owned-by-another-staff 0.825 against
no-verdict 0.780) and that is consistent rather than contradictory: ownership
files a verdict only where ink was detected TWICE, and CLAUDE.md already
records that for 11 of 13 phantom bars *"that decision is never asked, because
the ink was detected in ONE cell and the neighbour's cell did not see it."*

**So the convention is not shipped as a stem reader — it would inherit the
position's faults — and what it is good for is the opposite: it flags exactly
the two populations this repository already knows are bad.** A confident stem
and a confident convention that disagree mean one of `Q.NOTEHEAD_STAFF_POSITION`
and `Q.STEM` is wrong, and this says which zones to look in.

⚠️ A per-STAFF fitted boundary lifts agreement 0.804 → 0.925, but its fitted
boundaries span **−4.5 to 7.0** with only 34.7% landing on 4.0 — a free
parameter per staff is fitting VOICE STRUCTURE, not a grid offset, and is
reported here so nobody reads that 0.925 as a repair.

---

## 5. ⚠️⚠️ THE INSTRUMENT DEFECT THAT MATTERS: I PICKED A CORRELATED ARBITER

Before Sean's correction this session put the projection and the convention to
a third reading — the beam — and reported that **the beam sides with the
projection 79 times in 83**, concluding the convention does not hold. The
probe's own docstring claimed the beam *"shares an input with neither"*.

**That is false, and it is this repository's own recorded hazard in a new
place.** The projection and the beam-mate rule are BOTH readings of ink inside
the measure cell; the convention is the only one of the three that depends on
where the STAFF LINES are. An arbiter correlated with one party cannot
adjudicate between them — it will side with its own family — and 79/83 is what
that looks like.

*The bars are not an independent umpire over a bad reading*, arriving in the
stem family: the correlation ran through **the frame** rather than through the
ink or a convention, which is a fourth door onto that room.

---

## 6. Three more defects, all mine, all found by a control rather than a test

Each produced a clean, believable **ZERO**:

* beams keyed by **staff** where the heads were keyed by **cell** — because
  `beam_stroke` is filed on the CELL subject and the probe stripped a segment
  off it as if it were a glyph;
* `Q.GLYPH_BOX` read as `[x, y, w, h]` when it is `(smufl_name, x, y, w, h)` —
  `rhythm.py` spells that once in a helper whose docstring says it exists *"so
  a second reader of the same row cannot get it wrong"*, and this was that
  second reader, getting it wrong by not importing it;
* `key.rsplit("/", 1)[0]` on a subject key, which carries its KIND in the
  FIRST segment — so `glyph/1/0/2/4/1` became `glyph/1/0/2/4`, which is not
  `cell/1/0/2/4` and matches nothing.

⚠️ The third survived two rounds of fixing the other two. **The control that
caught them all was a positive one** — the same geometry run on heads whose
direction was already known — and it announced itself by printing **nothing at
all**.

---

## 7. What it does in the FILE, and it is small

One gather, the three affected quantities decided twice, **control 4,647 of
4,647 verdicts reproduced** with the tier disabled:

| | off | on |
|---|--:|--:|
| `no_stem` | 793 | **641** |
| `beam_mate` | 0 | **152** |
| voices per bar | 1,079 one / 38 two | unchanged |
| pitched notes | 965 | 965 |
| `<voice>2</voice>` | 24 | **26** |

⚠️ **152 heads gain a direction and the file gains TWO voice tags.** The
divisi guard and the voice split both already had enough to act on in the bars
that mattered. Reported as measured: this is a record improvement, not a file
improvement, and it must not be quoted as one.

---

## 8. What is NOT established

* **n = 1 document, 1 publisher, 4 pages.** The second publisher was not run
  for this tier.
* **There is no truth here.** Every accuracy is agreement with our own
  `stem_projection`, which is a reading and not a print. The convention's
  zone figures are the strongest evidence in this document that the
  projection is sometimes the wrong party, and nothing here says which of the
  two is right on any individual head.
* **No head was checked against the print.**
* ⚠️⚠️ **THE FIRST DRAFT WAS SLOW AND I HAD CAUSED IT.** To let both tiers
  share the whole-cell notehead scan, it was hoisted above the branch that
  decides which tier runs — so all **793 stemless heads paid for a
  `SELF_AND_DESCENDANTS` walk of their cell that they had never paid for**,
  and the stem pass went from 80 s to minutes on four pages. Repaired by
  asking the BEAM rows first: only the heads that actually stand on a beam
  (245 of 793) reach the scan at all. ⚠️ The lesson is not "cache it" — it is
  that **where `ev.rows` is called matters more than how the loop is
  written**, and that a tidier-looking hoist moved work onto the population
  the branch exists to exclude.
* A **whole note under a beam IS answered** by the tier (9 such heads here),
  because it reads boxes and not the detected class. The first tier has the
  identical exposure; pinned by a test rather than fixed in one tier only.
