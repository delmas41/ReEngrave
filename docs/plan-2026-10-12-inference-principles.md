# Inference principles: how close before we throw it out

**Date:** 2026-10-12. **Status:** proposal for Sean. **Path:** STAGED only.

Sean's brief: *"When something should be trusted and when it should be
definitive is so difficult ... there should be a set of principles allied to
every infer decision. Before something is thrown out I want to know how
close we can get and should be."*

This document is the set of principles, a way to make every refusal say
how close it was, a checklist, a cheap calibration method, an audit of the
six INFER rules on the tree today, and a plan. Nothing here is code.

---

## 1. Principles

Each has a one-line *why* and a one-line *test* (what would show a rule
breaks it).

**P1. A convention is a prior; a threshold is a measurement of two plates.**
*Why:* every rule built on an engraving convention (whole rest = bar, lone
whole rest, key-slot refusal, hollow half) held across publishers; every
rule built on a cut fitted while looking at a tile (2.99's 45% stroke cut,
2.88's raster centre) strained the moment it left Litolff and Breitkopf.
*Test:* name the convention the rule rests on, or name the plates its number
came from. A rule with a number and no convention is NARROW-only until a
third publisher confirms it.

**P2. Count signals by provenance, not by number.**
*Why:* two readings off the same ink, the same crop or the same assumption
agree for free (the bar sum and the notes it sums; a stem and the head it
stands on). `Evidence.correlated_groups` already says this at the row level;
it must hold at the rule level. *Test:* for each witness ask "if the ink
were misread, would this witness be wrong too?" If yes, it is the same
signal. Independence must come from a different SOURCE: catalog/roster, a
convention, another staff's different ink.

**P3. Likelihoods compose; cuts do not.**
*Why:* a hard cut throws away the distance to the cut, which is exactly the
information Sean wants ("how close can we get"). Two weak independent
signals at 0.8 each compose to ~0.94 as likelihood ratios; two cuts at 0.8
compose to a rule that refuses 36% of real cases. *Test:* can the rule
report a number for a near-miss, or only "refused"? If only refused, it is
a cut, and must be re-expressed as a measurement plus a margin (§2).

**P4. Arithmetic confirms a reading; it never supplies one.**
*Why:* 2.97's single-note settlements were 4/4 WRONG because the bar sum
inherits every other error in the bar (a missed rest, a second voice, a
tuplet, a misread meter) and then votes with full confidence. Chords on one
stem were 4/4 right because the sum there only picked among readings the
ink already supported. *Test:* remove the bar sum; does the rule still have
a candidate from ink? If not, it is supplying.

**P5. The sum is weak evidence in proportion to what else in the bar is
unread.** *Why:* a bar with 0 narrowed neighbours and 0 unboxed ink is a
strong witness; a bar with three narrowings and a `Q.CELL_INK_PIECES`
residue is nearly none. *Test:* the rule reads the bar's own health
(unexplained ink, narrowed count, tuplet mark, voice count) before it
counts the sum as support, and records it.

**P6. The bar for DECIDED is set by the cost of being wrong, not by a fixed
percentage.** *Why:* Sean (2026-10-12): *"I am not tied to 95%"*. A wrong
DECIDED note is a hidden error Sean must find by proofreading; a NARROWED
or unread one is marked and costs one visible click. The bar follows from
the ratio of those costs (§2b). *Test:* the number is from held-out tiles
(another page or publisher), with its Wilson interval, and the interval's
floor clears the bar for that family before the rule may decide. 2.81 read
0.96 on its tuning page and 0.76 pooled: the pooled floor is the number.

**P7. A near-miss is a narrowing with a margin, never a refusal.**
*Why:* a refusal says nothing about how close the rule came; a narrowing
with `margin` keeps the candidate order and lets INFER or a human finish
the job. *Test:* every reason word in a rule's `reasons` either carries a
measured margin or is a structural impossibility (no ink, no subject).

**P8. Abstain with a margin, not at a point.** *Why:* a cut at 0.45 on a
plate where real rests sit at 0.47–0.67 is a coin toss dressed as a rule.
*Test:* a rule declares a band around its cut; inside the band it NARROWS
and files the measurement; only outside the band does it decide or refuse.

**P9. Instinct names the hypothesis; math decides the band.** *Why:* Sean's
conventions have never been wrong; our thresholds often have. *Test:* a
rule's convention comes from Sean or the print; its band comes from a
measured distribution of Sean-judged tiles, never from one tile.

**P10. Where the maths and the instinct disagree, record both and narrow.**
*Why:* this is INFER's job: to choose the best among candidates. Both
answers survive as candidates with support; the disagreement is a signal
for the next round of tiles, not a bug to hide.

### Where instinct and math part company
- *Math* says a 0.96 rule on 49 heads is nearly there (Wilson floor 0.86).
  *Instinct* says it is one page, the page it was tuned on; the two wrong
  cases were in a tuplet and on another publisher. Instinct wins: the floor
  must come from a second page (P6).
- *Math* says two 0.8 signals compose to 0.94. *Instinct* says on a scan
  they are rarely independent (a thin plate thins both). P2 wins: compose
  only across sources, never across readers of one raster.
- *Instinct* says "the bar must add up" is strong. *Math* (2.97) says it is
  the weakest witness in the system because it inherits every error. P4/P5.

---

## 2. How close before we throw it out

Every rule that can refuse must say how close it came. The record already
has the fields: `Verdict.candidates` (optional on DECIDED, required on
NARROWED), `Verdict.margin`, and `Candidate.support` (relative, not a
probability, and that stays true).

**What to record, per decision:**
1. `candidates` always, ordered best first, even on a refusal. A refusal
   with an empty list is a structural impossibility and says so in its
   reason (`no_ink`, `no_subject`). Any other refusal lists what it would
   have chosen.
2. `margin`: the measured distance from the cut in the rule's own units
   (staff spaces, stroke thickness in line-widths, density), signed:
   negative = refused by this much, positive = passed by this much.
3. `detail.band`: the declared abstention band (P8), so a reader of the
   record can see whether the margin fell inside it.
4. The convention claimed (the `conventions.py` entry) so P1 is visible.

**How to show Sean.** A `near-miss gallery` per rule, derived from the
record: the ten decisions with the smallest |margin| on each side of the cut,
cropped as tiles, no verdict shown. His answers settle the band directly.

**"Keep working" vs "this signal can't do it".** Two numbers from one
gallery:
- *Separation:* do Sean's YES tiles and NO tiles overlap on the rule's
  measurement? If the YESes and NOs interleave across the band (2.99 on
  Tchaikovsky: rests at 0.47–0.67 around a 0.45 cut with slur ends nearby),
  the measurement is the wrong axis and no cut will do it. Stop tuning;
  find a second axis (shape, position, a convention).
- *Band width:* if YES and NO separate but the gap moves per plate, the cut
  must be measured LOCALLY (per plate, per staff: CLAUDE.md §10 on local
  geometry) rather than tuned. Keep working: the signal is right, the
  reference is wrong.
- A rule whose misses are all one kind (2.81: six eighths whose flags the
  tip reader missed) is a GATHER gap, not an INFER problem. Fix the reader.

### 2b. What the bar should be

The product's definition of done is counted in fix-actions per page, so the
bar is the point where deciding costs Sean less cleanup than marking.

- Let a marked (NARROWED/unread) symbol cost **1** fix-action: visible,
  one click. Let a wrong DECIDED symbol cost **c**: it is not marked, so he
  must find it, and in some families it cascades (a wrong duration breaks
  the bar sum, holds out the bar and misplaces every later onset).
- A rule right with probability *p* should DECIDE when its expected cost
  (1 − *p*)·c is below the cost of marking, 1. So **bar = 1 − 1/c**:
  c = 5 → 0.80; c = 10 → 0.90; c = 20 → 0.95. The old 95% was c ≈ 20.
- *c* is per family and is Sean's one answer, not ours: "how many marked
  fixes would you trade for one hidden wrong X?" Instinct says duration and
  pitch are c ≈ 10–20 (cascade, hard to spot); an articulation or dynamic
  c ≈ 2–3 (local, obvious); a part name c is large (every bar of the part).
- **Per stage:** DECIDED must clear 1 − 1/c on a pooled held-out floor.
  NARROWED must hold the answer among its candidates at ≥ 0.98 (an answer
  missing from the candidates costs c, like a wrong decision; a narrowing
  with the answer costs 1). An INFER collapse writes to the file, so it
  clears the DECIDED bar for its family, never a lower one.
- **How it is checked:** the cleanup count (`CATEGORIES.md`: `wrong` vs
  `missing` per page) IS this calculation run on a real page. Expected
  fix-actions per page = Σ decided (1 − p)·c + Σ marked · 1; the count
  measures the realised one. If the count's `wrong` bucket grows while
  `missing` shrinks, c was set too low for that family. The per-rule
  margin galleries (§2) supply *p*; the count supplies the audit.

---

## 3. The per-rule checklist

Applied to every INFER rule and every threshold-based ADJUDICATE rule,
before Sean sees tiles. Yes/no each.

1. **Source.** Convention (named) or threshold (which plates)? (P1)
2. **Witnesses.** For each: which source? Would it fall with the ink? (P2)
3. **Candidate from ink.** Does a candidate exist before any arithmetic? (P4)
4. **Bar health.** Does the rule read unexplained ink, narrowed count,
   tuplets, voices, and refuse where they are present? (P5)
5. **Margin filed.** Does every non-structural refusal carry `candidates`
   and a signed `margin`? (P7)
6. **Band declared.** Is there an abstention band, and does it NARROW
   inside it? (P8)
7. **Held-out number.** Blind tiles from a page other than the tuning page,
   with a Wilson interval; floor above the family's bar 1 − 1/c for
   DECIDED. (P6, §2b)
8. **Positive control.** Does the rule fire on the cases it should and
   refuse on a planted one in the same class?
9. **Reach.** Population printed; a zero declares itself dead.
10. **What it costs when wrong.** A wrong DECIDED note is a fix-action Sean
    cannot see; a NARROWED one is visible. Prefer visible.

---

## 4. Cheap validation

**Calibrating with 10–15 tiles.** Fifteen tiles cannot prove a high bar;
they can refute one. 15/15 right gives a Wilson floor of ~0.78 (enough for
a family with c ≈ 5, not for c ≈ 20); 14/15 ~0.70. So:
- Use tiles to *rank* candidates and to *place the band*, not to certify.
- Certification (DECIDED) accumulates: pool every round's tiles for the same
  rule across pages, keyed by the rule's reason word, until the pooled floor
  clears the family's bar (c = 10: about 20 of 21; c = 20: about 40 of 42).
  The pool must span at least two pages and, for threshold rules, two
  publishers.
- Choose tiles by margin, not at random: half from inside the band, half
  just outside on each side. A random sample of easy cases flatters the
  rule; the band is where the information is.

**When a rule needs a held-out score.** Whenever it carries a number fitted
on Litolff/Breitkopf (checklist item 1 says "threshold"), or whenever its
misses on the tuning page were all of one class. 2.101 is this for the
2026-10-11/12 landings and should be the template: a few pages from 2–3
other publishers, base vs arm, blind tiles.

**Re-using Sean's answers.** 43 `out/print/*/answers.json` files hold 128
judged tiles, each keyed by glyph subject (`glyph/3/1/4/12/3`), movement
and pdf page, plus the verdict at the time. Build one derived index
(`tools.omr.staged.review` can own it): subject → Sean's reading. Then any
rule's new arm is scored against every past answer it touches before a
single new tile is cut, and a rule that flips a previously-right subject is
caught for free. `docs/DECISIONS.md` lines from 2026-10-10 on carry the
verbatim answers for tiles whose JSON predates the key field; grep by
`out/print/<dir>` to join them. Never read either whole.

**Avoiding fitting to the page being judged.**
- The band is set from one page's gallery and judged on another. A number
  changed after seeing a tile (2.99's 45%, 2.88's first 0.2 draft) is
  recorded as `fitted_on: <tile dir>` and the rule stays NARROW-only until
  the next page confirms.
- Controls in the same class in every gallery (the clef, the ledger, the
  slur end), so a rule cannot pass by refusing everything.
- The subject's own tuning page is excluded from its certification pool.

---

## 5. Audit of the INFER rules on the tree

Six rules in `inferences.py`, read off `@rule(...)` and `infer.RULES`.

| rule | switch | evidence (`reads`) | principle at risk | risk |
|---|---|---|---|---|
| `collapse_duration_by_column` | `OMR_INFER` (ON) | onset columns, events, other staves' DECIDED durations spanning the same k→m; `independent_groups` by provenance; one dissenter refuses | P2 is handled honestly (one-sided independence declared). P7: a dissent is a silent refusal with no margin, no candidate order | **med** |
| `collapse_duration_to_barline` | `OMR_INFER` (ON) | same, witnesses are neighbours that also run to the barline; refuses meter-derived witnesses | Same as above; P5: a neighbour whose bar is unhealthy still counts as a full witness | **med** |
| `collapse_slot_index_to_family_block` | always on | slot index, instrument, raw clef glyph (never the clef verdict) | Print-verified 25/25; P6 met. Low | **low** |
| `fill_clef_gap` | always on | other systems' DECIDED clefs on the same slot (majority), instrument | P2 fine (other ink). P7: a tie abstains silently; the majority's size is not filed as margin | **low** |
| `fill_part_key` | `OMR_PART_KEY` (ON) | document majority of concert keys re-transposed by the staff's own `fifths_offset`; same part's other systems | P5 analogue: a majority over a stretch that contains a missed key change flattens it; bounded by `Q.PART_KEY` stretches, so acceptable. Margin not filed | **low** |
| `collapse_bare_stem_by_bar` | `OMR_BARE_STEM_BAR` (ON) | meter, events, durations, owners, not-a-note/not-a-rest; arithmetic only, tip-clean condition | **P4/P5 directly**: it declares its witnesses are not independent and still decides. 2.102 found tuplets; 2.97 found the single-note failure mode. Only the "every landing agrees" guard stands between it and 2.97's 4/4 wrong. No bar-health read, no margin | **high** |

Threshold-based ADJUDICATE rules that belong on the same list (checklist
item 1 = threshold): `adjudicate_unboxed_ink_is_a_rest` (2.99, 45% stroke
cut, **high** until Tchaikovsky's band is measured), the hollow-half rule
(2.88, raster centre 0.2–0.75, **med**: C-meter and tremolo misses are
convention gaps, now 2.102), `adjudicate_narrow_box_is_an_eighth_rest`
(2.80b, 2/2, **med**, too few tiles), the stem-tip flag reader (2.83, shape
+ density band, **med**).

---

## 6. Plan of action

Ordered. Each step says what it produces and Sean's time.

**Step 1 — Margin and candidates on every refusal** (record only; ~0 Sean).
Make `candidates` + signed `margin` + `detail.band` mandatory on every
non-structural verdict from the six INFER rules and the four threshold
adjudicators. `check` gains a derived part (`margins`: rules whose reason
words refuse without a margin). Produces: the data every later step reads.

**Step 2 — The answer index** (~0 Sean). Derive subject → Sean's reading
from the 43 `answers.json` files plus the DECISIONS lines; a scorer that
runs any record against it. Produces: every past tile re-scored on every
arm for free; flips caught before Sean sees anything.

**Step 3 — Near-miss galleries** (Sean: one gallery of 10–15 tiles per rule,
~5 min each, phone). Cut the smallest-|margin| tiles per rule, half each
side, with same-class controls. First targets: `collapse_bare_stem_by_bar`,
2.99 rests, 2.88 halves. Produces: the band for each, and the verdict
"separable / local / wrong axis" (§2).

**Step 4 — Bar health as a declared input** (Sean: ~10 tiles). Give
`collapse_bare_stem_by_bar` and the two column rules a read of unexplained
ink (`Q.CELL_INK_PIECES`), narrowed count, tuplet marks and voice count,
and refuse to settle where any is present; file the health in `detail`.
Absorbs 2.102(a). Produces: 2.97's failure mode structurally closed.

**Step 5 — The certification pool** (Sean: nothing new; pools what he has
answered). Per reason word, pool tiles across rounds and pages; publish the
Wilson floor in the rule's FINDINGS and in `check`. Sean sets c per family
(one answer each: duration, pitch, rest, articulation, dynamic, name). A
rule may DECIDE only where the pooled floor from at least two pages clears
1 − 1/c; otherwise it narrows with the measured likelihood labelled.
Produces: 2.81's "is 0.96 on one page enough" answered by a rule, not a
call, and the cleanup count's `wrong`/`missing` split becomes the audit of
c itself.

**Step 6 — Held-out publishers as the standing test** (Sean: ~15 tiles per
round). Make 2.101 permanent: every threshold rule's gallery includes one
other-publisher page. Produces: P1 enforced by measurement.

**Step 7 — Local bands where the gallery says "local"** (Sean: ~10 tiles).
Where step 3 finds the gap moves per plate (2.99's stroke cut), re-express
the cut relative to the plate's own measured stroke/line thickness, as §10
already requires for geometry. Produces: the rule travels.

**Step 8 — Retire or promote** (Sean: one line each). A rule whose gallery
says "wrong axis" after two rounds is set NARROW-only and its roadmap row
says why; one whose pool clears the floor on two publishers loses its flag.

Total Sean time across the plan: roughly six galleries of 10–15 tiles over
two weeks, on his phone, each cut by margin so every answer moves a band.
