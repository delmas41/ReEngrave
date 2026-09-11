# `wedge_anchor` — hairpins reach the file on the staged path

2026-09-10, no flag. Phase 1 item 3 of
[docs/plan-2026-09-10-wire-first-then-reconcile.md](../../docs/plan-2026-09-10-wire-first-then-reconcile.md).
A WIRING pass under that plan's §2b: *connect it, let it abstain freely, do
not tune.* **No new tuned constant was introduced.**

---

## 0. ⚠️⚠️ REACH FIRST, AND THE ZERO-REACH DOCUMENT PROVES NOTHING

| document | `Q.WEDGE_BOX` rows |
|---|--:|
| Litolff Beethoven 5 `984073` p1-3 | **0** |
| Breitkopf Brahms 1 `317803` p0-3 | **47** (46 `cv_hairpins`, 1 `detector`) |

**Brahms is this family's ONLY fixture.** Measured on Litolff, every arm here
would print a clean zero that says nothing whatever about the rule — *a change
that moves nothing because it is inert and one that moves nothing because the
page holds nothing to move are the same number.* `wedge_arm.py` prints REACH
before any other line and **exits non-zero declaring itself DEAD** when the
count is 0; run on Litolff it does exactly that, which is this arm's own
negative control and is reproduced in `out/`.

⚠️ The single `detector` row **carries no box at all**, so `no_page_frame` is a
REAL abstention branch and not a defensive one — 1 row of 47.

---

## 1. WHAT LANDED — three legs at once

| leg | where |
|---|---|
| adjudicator | `adjudicate_wedge_anchor`, `staged/adjudicators/ownership.py` |
| emission | `_place_wedges` + the render in `_measure_events_xml` |
| counter | `counters["wedges"]`, at the render, and `FAMILIES["wedge"]` |

The previous three sessions each shipped a decision that decided into no file
for a day. `grep -c '<wedge' tools/omr/staged/export.py` is now non-zero.

**`stubs()` is now `('direction',)`** — `wedge_anchor` was the last of the six
original stubs whose input was already gathered, and `direction` is the only
one that was ever input-starved (two pieces of work, not one).

---

## 2. THE ONE DESIGN DECISION

Handoff §6 posed it. `_legacy._wedge_anchors` wants the exporter's `measures`
shims and three MEASURED constants — `_WEDGE_ANCHOR_PAD_NOTEHEADS`,
`_WEDGE_START_RULE`, `_WEDGE_STOP_REACH_NOTEHEADS`.

* **Call the legacy function from the staged EXPORTER** (the `_pair_arcs`
  precedent) — **REFUSED.** It leaves `adjudicate_wedge_anchor` with nothing to
  decide, and the point of the stage is that the answer *and the evidence for
  it* are on the record.
* **Restate the rule in the adjudicator** — **REFUSED.** Three numbers this
  project paid to measure once would exist in two copies, the drift
  `LETTER_METERS`, `rhythm._REST_DURATIONS` and the arc-attribution constants
  are all imported to prevent.
* **Taken: SPLIT the legacy function.** The half that knows about `measures`
  dicts stays and finds the window; the RULE moves into
  `_wedge_anchors_from_candidates(candidates, widths, left, right, voice_of)`,
  taking page-pixel candidates and an **opaque payload** — so the legacy path
  passes detection dicts and the staged decision passes subject keys. The
  constants and the rule that reads them stay defined in exactly one place.

`left` and `right` are passed **outright** rather than as a box, so neither
caller has to spell a width — the corners-vs-width confusion that turned a
140px arc into a 1190px one in the arc export's battery cannot arise at the
seam.

### ⚠️⚠️ The byte-identity control was VACUOUS on its first attempt

The obvious control — export three committed transcriptions before and after,
compare md5 — **passed, and could not have failed.** `grep -c '<wedge'` on
every one of those files is **ZERO**: the detector fires on a hairpin ~never on
a scan (1 across eleven scanned pages against a truth of 198), so none of them
calls `_wedge_anchors` at all.

`probe/legacy_identity.py` replaces it. It drives the function DIRECTLY over
twelve synthetic cases covering every branch (between-notes, degenerate
one-note, one-anchor, no-candidates, cross-barline, the stop-reach cliff on
both sides, the start-rule tie, the ±1 window), and **prints how many ANSWERED
as its own positive control — 10 of 12** — exiting non-zero on zero.
`out/legacy-anchors.BEFORE.txt` and `.AFTER.txt` are **identical**, and the 312
legacy `test_export.py` tests are green.

---

## 3. WHAT THE DECISION DOES, AND WHAT IT REFUSES

| reason | meaning |
|---|---|
| `nearest_either_side` | the rule's answer: two notes named |
| `no_page_frame` | the row has no `bbox_page_px` — the detector's own row |
| `no_anchor` | no notehead this staff owns in the bar or either neighbour |
| `no_evidence` | no wedge row on this subject |

* **PAGE PIXELS, never the cell frame.** Two staves' canonical frames coincide
  BY CONSTRUCTION; comparing a cell-frame hairpin with a page-frame notehead is
  the fault that made `Q.ONSET_COLUMN` report 1,062 columns of nothing.
* **The heads are the OWNER's, not the cell's** — `arc_owner`'s rule, for its
  reason: a cross-staff duplicate is filed on the staff that DETECTED it.
* **A REST cannot anchor a hairpin**, unlike a fermata's carriers. A hairpin is
  a dynamic over sounding notes and both exporters need a note to hang `\<` and
  `\!` on. **Found by a mutation arm**, which survived without the test.
* **No merge across barlines**, and that is a property of the READER rather
  than a simplification: `hairpin_detection` reads the whole page one
  staff-band at a time, so a CV hairpin is never cut by a cell boundary. The
  merge exists for per-cell crops.
* **A note no `Q.VOICES` verdict mentions is voice 0** — the identical default
  `_paired_spans` and `_voice_of_notehead` already apply — and **`voices_read`
  is RECORDED**, because *"one voice"* and *"voices unknown"* are the same
  NUMBER and different FACTS.

`_WEDGE_WINDOW_CELLS = 1` is **not a new constant**: it is `_wedge_anchors`'
own `+1` measure window, which that function enforces as `lo, hi = first_m - 1,
last_m + 1`, given a name because the staged path has no `measures` list to
slice.

---

## 4. ⚠️⚠️ ITS ORDER POSITION WAS WRONG, AND NO TEST COULD HAVE FOUND IT

Placed beside `fermata_owner` and `ornament_owner` — its natural home, since
all three take their subjects from a glyph row — `wedge_anchor` ran **BEFORE
`Q.VOICES` was decided and read `None` every time.** A declared input that
could never answer: the same shape as `Q.STEM`'s 916 unread rows and
`arc_owner`'s wrong frame.

**No behavioural test reaches it**, and that is the interesting part: *"one
voice"* and *"voices unknown"* produce the SAME ANSWER on every page that has
only one voice, which is every fixture in the suite. **`inventory --check`
found it in one line**, because it knows the `wants` and it knows the `ORDER`
and it compares them:

```
⚠️ wedge_anchor wants the VERDICT 'voices', which ORDER runs AFTER it
   -- it will always read None
```

⚠️ **And moving it immediately exposed a latent bug the unreachable branch had
been hiding**: `v.outcome != State.DECIDED`, where `State` holds
READ/DECLINED/ABSENT and the outcome enum is `Outcome`. The line had never
run. *A branch that cannot be reached cannot be wrong, and cannot be right
either.*

The repair is pinned by a test on `ORDER` — which exists **because** no
behavioural test can stand in for it.

---

## 5. THE REPORTING GAP — a family whose ink comes from a CV rung

`coverage()` built its `detected` census from `Q.GLYPH_BOX`, which is the
**DETECTOR's** class space. A hairpin the CV rung read was never a detector
detection, so:

| | reported | actual |
|---|--:|--:|
| `wedge` ink on Brahms p0-3 | `detector_glyphs: 1` | **47** rows |

**Anyone sizing this work off the coverage headline read its reach as 1 instead
of 47** — a 47x under-report of the only family whose ink comes from a CV
reader.

`cv_glyphs` and `ink_rows` are added, **DERIVED from the registry's own
`subjects_from`** rather than from a hand-written list of families: a
decision's `subjects_from` names the quantity whose rows ARE its population, so
counting the ones whose `reader` is not the detector adds each CV reading once
and no detector reading twice. The two readers stay **reported APART**, because
`gather_wedge_boxes` emits both precisely so a consumer can decide which to
believe and one merged number destroys that. The two headlines now read
`ink_rows`.

⚠️ A family with no `subjects_from` returns **zero**, and that is the true
number rather than a stand-in: its population *is* the detector's glyphs,
already counted. It is not a fallback converting *"cannot tell"* into a
definite answer.

---

## 6. THE MUTATION BATTERY — 9 of 19 arms were not red on the first run

`probe/battery.py`: **18 arms plus a POSITIVE CONTROL in the same class** (the
decision refuses every input, which must go red or the accept-side tests are
not reaching the code). **All 19 red** after repair; `out/battery.txt`.

The first run is the finding:

| what | n | what it was |
|---|--:|---|
| **BAD ANCHOR** | 2 | `Ruling.abstain(` and the notehead category filter each occur **twice** in `ownership.py` — the arm would have mutated `arc_owner`. Reported as loudly as a survivor, because that is exactly how the fermata battery silently mutated a different function. |
| **EQUIVALENT MUTANT** | 1 | my own `out.append(x) if True else None` — the same program. It "survived" for that reason and is not a coverage gap. |
| **GENUINE TEST GAPS** | 6 | all closed: the kind check, the rest filter, the part ordinal end-to-end, both halves of the CV-ink reporting fix, and both voice-map seams. |

⚠️ **One arm was answered by DELETING CODE, not by writing a test.** A
`wedge_states` clearing loop was written for idempotence; `build()` constructs
fresh `Cell`s and fresh detection dicts on every call, so **the rule could not
fire** and the arm deleting it stayed green. The code went, rather than
acquiring a test that could not reach it — the `METER_FROM_BARS_MIN_ASSESSABLE`
precedent. Idempotence is still asserted where it is real: two exports of one
record are byte-identical.

⚠️ **The legacy suite is in the battery's test list**, because the refactor
moved the RULE. Two of the fermata battery's survivors were *"the test list did
not include the tests that reach the file it mutates"* — a battery whose tests
cannot see the mutation measures its own scope, not the code.

---

## 7. TWO HAZARDS THE EMISSION HAD TO AVOID

⚠️ **THE ELEMENT ORDER IS THE PAIRING, NOT A STYLE.** music21 attaches a
`crescendo` to the next note it PARSES and a `stop` to the last note it parsed,
so the opening mark goes BEFORE its event and the stop AFTER it. Writing both
on one side changes WHICH NOTES the hairpin spans and **no count would
notice** — so the test asserts the element SEQUENCE, not the number of wedges.

⚠️ **A CELL INDEX IS NOT A PART ORDINAL.** It restarts at 0 on every system,
which is the `(page, cell)` defect that made the duration arm's bar-level
figures wrong when first published; a hairpin numbered against it lets system 1
close one still open in system 0. `_part_cells_in_order` supplies the part-wide
ordinal and is asserted to match `_flatten_part`'s order — and, end-to-end,
that two hairpins in successive systems take ONE number rather than two.

`wedge_balance` is a **PARTITION of the hairpin rows**, not written+dropped:
most of this family never reaches the exporter at all, and folding
`no_anchor`/`no_page_frame` into `not_written` would report a READING limit as
an exporter gap — the confusion `coverage()`'s two headlines exist to keep
apart. The `Unbalanced` control is untouched and stays an EQUALITY.

---

## 9. ⚠️ WHAT IS **NOT** ESTABLISHED

* **Nothing about ACCURACY.** Not one hairpin has been checked against the
  print. The rule's own anchoring was measured when the legacy path shipped
  (nearest-either-side pairs 4 of 8 truth hairpins and gets all 4 right); this
  session MOVED it, it did not re-price it.
* **No OMR-NED figure is claimed**, deliberately — the metric is symmetric and
  rewards emitting more symbols, and the legacy slur work's first cut LOWERED
  pooled OMR-NED while RAISING the edit count.
* **n = 1 document, 1 publisher, 4 pages.** The second publisher this thread
  keeps needing (Litolff) has ZERO reach and cannot supply one.
* **The `no_anchor` population is the DETECTOR's, not this rule's.** Where a
  hairpin is read and the notes under it are not, the abstention is correct and
  the shortfall is upstream — the same shape this repo already records for the
  arcs (76% of merged arcs bind fewer than two noteheads) and for the hairpins
  themselves (`hairpin matched_exact = 0` with **0 spurious** beside it).
* **`voices_read` has not been shown to matter.** The voice filter is now
  reachable; whether it ever changes an answer on a real page is unmeasured. It
  is recorded so a later reader can tell a refusal that FIRED from one that
  could not.
* **The `_WEDGE_STOP_REACH_NOTEHEADS` plateau is still unexercised**, and the
  legacy constant says so itself: every value from 0.0 to 1.5 scores
  identically *because the branch never fires*. Inheriting the constant
  inherits that weakness; it does not repair it.

---

## 10. REFUTED / REFUSED — do not re-try these

1. **Byte-identity by exporting committed transcriptions.** Vacuous: those
   files contain no `<wedge>`, so the code under test never runs. §2.
2. **The `_pair_arcs` precedent for the whole rule.** Refused; §2.
3. **Restating the three constants in the adjudicator.** Refused; §2.
4. **Porting `_merge_arcs_across_barlines` for hairpins.** Not needed at all —
   a CV hairpin is read whole, one staff-band at a time. §3.
5. **An idempotence guard in `_place_wedges`.** Dead code; the exporter builds
   fresh dicts. §6.
6. **Placing `wedge_anchor` beside the other glyph-owner decisions.** It looks
   right and makes `Q.VOICES` unreadable. §4.

---

## 11. NEXT

* **A second publisher with hairpin reach.** Litolff has none. Until one
  exists, every number here is one document's.
* **`direction` is the last stub**, and it is TWO pieces of work:
  `Q.DIRECTION_WORD` has no gatherer.
* **The `no_anchor` rate is a DETECTION figure** and belongs with the hairpin
  reading work (`OMR_CV_HAIRPINS`), not with this rule.
