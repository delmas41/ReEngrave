# ROADMAP 2.6 — `glyph_owner`'s DOMAIN: the contest's identity test

2026-09-23. Built as designed in
`benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §10, which measured
the defect to the glyph and specified the change, its constraints and its
measurement. Nothing here redesigns it.

**The change, in full** — `tools/omr/staged/gather.py ::
gather_ownership_evidence`, two values, no new flag, no new quantity:

| | before | after | where the value comes from |
|---|---|---|---|
| the twin test | `di.smufl_name != dj.smufl_name` | `di.category != dj.category` | `gather.py:401` already writes `d.category` onto every `Q.GLYPH_BOX` row; the FROZEN legacy reader compares exactly this (`transcribe._dedupe_cross_staff_detections`) |
| the overlap floor | `_iou(bi, bj) < CONTEST_IOU`, `CONTEST_IOU = 0.5` | `_iou(bi, bj) <= CONTEST_IOU`, `CONTEST_IOU = 0.3` | `transcribe._CROSS_STAFF_DUPLICATE_IOU = 0.3`, swept at 0.25/0.3/0.4/0.5 over three orchestral works (`benchmarks/omr-orchestral-e2e/DEDUPE_THRESHOLD.md`); the comparison is STRICT because the legacy one is |

`adjudicate_glyph_owner` is untouched: `subjects_from=Q.GLYPH_BAND_DISTANCE`
has not moved, the winner is still ladder → range → distance, and nothing in
`ownership.py`, `is_relocated_copy`, `move_glyph`, `infer.py` or `export.py`
changed. **Both values already existed in this repository**, which is why this
is a CONNECT and not a guess (CLAUDE.md rule 6).

⚠️ **NOT ONE GLYPH HERE HAS BEEN READ AGAINST A PRINT.** §10e's warning stands
verbatim and this pass does not lift it. 19 crops are cut and waiting for
Sean; every row of their manifest carries `VERDICT_none_yet: null`. Everything
below is a DOMAIN measurement — how much ink entered a contest and what the
scoring then said — and a domain measurement cannot say a note went to the
right staff.

---

## 1. The instruments, and which one is blind to what

| tool | what it prices | blind to |
|---|---|---|
| `regather_ownership.py` | ONE gather site, re-run over inputs rebuilt from a SAVED record, then ADJUDICATE · GROUPS · EVALUATE · INFER · EXPORT | the detector; every other gather site; the cell crop; the staff reading. It never opens the PDF |
| `real_gather_pair.sh` + `real_gather_agreement.py` | a real base-vs-arm CLI gather on one page | nothing structural — it is the control that the first tool's answer is the answer a gather gives |
| `twin_classes.py` | WHICH axis admitted each newly-contested glyph, and whether the two twins disagree about the class | decides nothing, crops nothing |
| `crop_contested.py` | the print | it only asks the question; Sean answers it |

`readjudicate.py` and `reexport_arm.py` are **structurally blind to this
change** and were not used; a zero from either would not have been evidence
(CLAUDE.md §6b).

### 1a. The base arm runs the base CODE, it does not restate it

`regather_ownership.load_base_gather` reads
`848dda47:tools/omr/staged/gather.py` with `git show` and loads it as a
module under the package `tools.omr.staged`. The base arm is therefore that
file's own `gather_ownership_evidence`, byte for byte, in the same process as
the arm — **base and arm on ONE tree** (§6b), with the detections, the staff
geometry, the cells, the flags and every later stage identical.

WARNING — **THE BASE IS A SHA AND NOT A BRANCH, AND IT WAS LEARNED THE HARD
WAY.** Every arm here ran with `--base-ref origin/main`, and that ref moved
**nine times** during the session (other lanes pushing; it is shared by every
worktree of this repository). Checked afterwards against the reflog: the two
commits that changed `gather.py` on main — `febd383a` 15:40 and `24d26b8d`
16:02, both ROADMAP 2.11 — entered the ref at **16:05:54**, after the last of
these runs finished (p1–p4 14:03, the real pair 14:00, Litolff whole 14:27,
Breitkopf whole 16:03). Every base arm therefore read the `gather.py` of
`848dda47`, the merged main this item was built on. The default is now that
sha, in this tool and in `real_gather_pair.sh`, so the next run cannot
silently price against a different base.

### 1b. ⚠️ THE CONTROL, AND IT WAS RUN RED FIRST

The rebuild is admissible only if the BASE arm reproduces the record it was
built from.

| record | base arm vs the record's own `glyph_owner` verdicts | band rows |
|---|---|---|
| `beethoven5-p1-p4-ink-identity` | **1386 of 1386 reproduced exactly**, 0 differ, 0 extra | 2772 = 2772 |
| `beethoven5-litolff-mvt1-whole-20260923` | **6013 of 6013 reproduced exactly**, 0 differ, 0 extra | 12026 = 12026 |
| `brahms1-breitkopf-mvt1-whole-20260923` | **24795 of 24795 reproduced exactly**, 0 differ, 0 extra | 49590 = 49590 |

`OWNER_REGATHER_BREAK_CONTROL=1` stretches every staff band by 1 %. On p1–p4
the same control then reports **1365 of 1386, 21 differ**, and names them —
`glyph/2/0/1/1/5` flips from `range_veto` on its own staff to `distance` on
the neighbour, and so on. **The control can fail, and it was run failing
before it was trusted passing** (CLAUDE.md rule 7).

⚠️ The rebuild drops `basis` from the GATHER rows it copies and appends the
contest's rows at the END of the log rather than interleaved where the real
gather wrote them. Neither changes a verdict — that is what 1386 of 1386 says —
but a future reader should know the ids are not the record's own.

---

## 2. REACH, BEFORE ACCURACY

The §7b population, recomputed identically on every arm: every notehead with a
page box whose nearest OTHER staff of the same system beats its own by more
than half a staff space. ⚠️ **358 is not a misattribution count** (§7b); it is
the population carrying the geometric signature of the two subjects Sean
adjudicated against the print.

### Litolff Beethoven 5, pp. 1–4 (`beethoven5-p1-p4-ink-identity`)

| | base | arm |
|---|--:|--:|
| noteheads carrying the signature | 358 | 358 |
| **never contested at all** | **161** | **74** |
| contested → resolved to the NEAR staff | 189 | 274 |
| contested → resolved elsewhere | 8 | 10 |
| band-distance rows (all families) | 2,772 | 3,760 |
| `glyph_owner` verdicts (all families) | 1,386 | 1,880 |

**161 → 74, i.e. 87 handed in** — exactly the figure §10's counting arm
predicted for the legacy predicate (87 of 161), reproduced here by RUNNING the
code rather than by counting what it would do. The 74 that stay out are §10's
38 with no same-category ink on another staff and 36 sitting at or below the
swept 0.3 floor. **The 38 with no twin are still not handed in**, which is the
constraint §10 called the one place a plausible fix is the wrong one: a glyph
with no twin awarded elsewhere would be DROPPED at export and the note would
vanish, turning a wrong-staff error into a missing one.

`elsewhere` moves 8 → 10 because the two `tied` abstentions below carry no
value and so are not "the near staff". 74 + 274 + 10 = 358.

### The two whole movements

| | Litolff whole, base → arm | Breitkopf whole, base → arm |
|---|---|---|
| noteheads carrying the signature | 1,725 | 4,086 |
| never contested | **704 → 330** (374 handed in) | **1,392 → 733** (659 handed in) |
| resolved to the NEAR staff | 960 → 1,329 | 2,488 → 3,128 |
| resolved elsewhere | 61 → 66 | 206 → 225 |
| band-distance rows | 12,026 → 15,960 | 49,590 → 62,111 |
| `glyph_owner` verdicts | 6,013 → 7,980 | 24,795 → 31,054 |

On Breitkopf, which SHATTERS: **1,392 → 733, 659 handed in**, and
733 + 3,128 + 225 = 4,086. The IoU axis does transfer — but not in the same
proportion, which is the point of measuring both plates: on Litolff the floor
alone admits 992 of 1,967 newly-contested subjects (50 %), on Breitkopf 2,686
of 6,259 (43 %), and the CATEGORY axis alone carries 2,369 there against 618
on Litolff.

**374 of 704 on the Litolff whole movement** — again exactly §10's counting-arm
prediction for the legacy predicate, arrived at by running the code. 330 +
1,329 + 66 = 1,725.

⚠️ **Litolff MERGES and Breitkopf SHATTERS.** The two are reported apart for
that reason and are never pooled; the IoU axis in particular need not transfer
between plates where ink components are and are not marks.

---

## 3. THE CONTROL THAT MUST HOLD: the 189 stay 189

§10d.2: *"Loosening can add a THIRD candidate to a contest that already had
two and flip it, so the arm must report every pre-existing `glyph_owner`
verdict that changed, by subject, and not merely the count of new ones."*

| record | pre-existing `glyph_owner` verdicts that CHANGED | of them, in the correctly-contested population |
|---|--:|--:|
| p1–p4 | **0** of 1,386 | **0** |
| Litolff whole | **0** of 6,013 | **0** |
| Breitkopf whole | **0** of 24,795 | **0** |

Every changed subject, where there is one, is named in
`out/<record>.json → pre_existing_verdicts_changed`. On p1–p4 that list is
EMPTY, so the 189 are 189 and the 274 are 189 + 85.

## 4. What the newly handed-in glyphs got

p1–p4, over the 87:

| outcome | n |
|---|--:|
| decided → the NEAR staff | 85 |
| abstained, `tied` | 2 |
| decided → its OWN staff | 0 |

Litolff whole movement, over the 374: **369** decided → the NEAR staff, **4**
abstained `tied`, **1** decided → its OWN staff. Breitkopf, over the 659:
**640** → the NEAR staff, **11** → its OWN staff, **8** abstained `tied`. The one that stayed is worth
noting on its own: the widened contest is not a machine for moving notes to
the neighbour — it asks, and the scoring can answer *this staff*.

The two `tied` abstentions are §10c's mechanism — two vetoed candidates both
scoring exactly −6.0 through the correlated-group collapse, so distance cannot
separate them. **`tied` stays an abstention**; nothing here converts it into an
answer.

⚠️ **This does not show the 85 are right.** They entered a contest and were
scored on ladder → range → distance like the rest. §10e's sentence is
unchanged: this says why they were never ASKED, not what the answer is.

---

## 5. ⚠️⚠️ `category` IS COARSE, AND THE WIDENING IS NOT ONLY NOTEHEADS

This is the finding the brief did not ask for and the one that most needs
reading. `yolo_detector._CATEGORY_MAP` puts beam, slur, tie, ledgerLine,
augmentationDot, brace, coda and segno all under **`structural`**, and every
dynamic letter and both hairpins under **`dynamic`**. Restoring the legacy
predicate therefore widens the contest for those families too — exactly as the
legacy reader does, which applies `di["category"] != dj["category"]` to every
detection on the page with no notehead restriction.

`twin_classes.py` on p1–p4, over the **494** glyph subjects that gained a band
row:

| which axis admitted it | n |
|---|--:|
| the IoU floor alone (same smufl name, 0.3 < IoU ≤ 0.5) | 279 |
| the category test alone (IoU was already over 0.5) | 120 |
| BOTH axes were needed | 95 |

| how the two spellings differ | n |
|---|--:|
| identical smufl name | 279 |
| same category, different class | 136 |
| SAME head, `OnLine` vs `InSpace` | 46 |
| both noteheads, head TYPE differs | 33 |

| by category | n |
|---|--:|
| structural | 181 |
| notehead | 173 |
| dynamic | 86 |
| accidental | 36 |
| flag | 8 |
| rest / ornament / clef | 4 / 4 / 2 |

The 136 cross-class pairs, named by the class of the admitted glyph:
**112 structural** (`slur` 40, `tie` 38, `beam` 31, `ledgerLine` 3 — arcs and
beams against each other), **11 accidental** (`accidentalFlat` against
`keyFlat`, mostly), **9 dynamic** (`dynamicS` vs `dynamicF`, `dynamicF` vs
`dynamicP`, `dynamicS` vs `dynamicM`), **2 rest**, **2 flag**.

**What it costs in the file**, p1–p4, every `written` counter that moved:

| counter | base | arm | Δ |
|---|--:|--:|--:|
| notes | 1,614 | 1,572 | **−42** |
| **dynamics** | 205 | **176** | **−29** |
| pitches_altered_by_the_key | 342 | 327 | −15 |
| arc_notes_reachable_at_a_stem | 1,238 | 1,232 | −6 |
| empty_bars_padded | 212 | 218 | +6 |
| rests | 419 | 417 | −2 |
| notes_doubled_to_condensed_slot | 134 | 132 | −2 |
| slur_spans_marked | 90 | 92 | +2 |
| beam_cells_without_a_frame_ruler | 104 | 106 | +2 |
| slurs | 39 | 40 | +1 |
| ties | 87 | 86 | −1 |
| beams | 696 | 695 | −1 |
| beamed_events | 521 | 520 | −1 |
| tie_chains_marked / tie_links_marked / tie_spans_marked | 80 / 105 / 105 | 79 / 104 / 104 | −1 each |
| tie_stops_on_an_upper_chord_note | 21 | 20 | −1 |

⚠️ **THE 29 DYNAMICS ARE AN UNADJUDICATED COST AND THEY ARE NAMED HERE RATHER
THAN ABSORBED.** `adjudicate_dynamic` DROPS a letter whose owner names another
staff (`text.py:151`), and that is the mechanism CLAUDE.md credits with taking
`ffff` 11 → 2 where one printed `ff` had been detected twice across two staves.
77 of the 86 newly-contested dynamic glyphs are the SAME letter twice, which is
that duplicate; the other 9 disagree about the letter, and only a print can
settle those. **No crop of a dynamic has been cut and none of the 29 has been
read against the page.** The notehead balance control cannot see any of this —
it counts `Q.NOTEHEAD_CLASS` and `Q.REST` — which is why every counter is
printed here and not just the notes.

**The same shape at 4× the scale**, Litolff whole movement, over the **1,967**
subjects that gained a band row: admitted by the IoU floor alone 992, by the
category test alone 618, by both 357; identical smufl name 992, same category
different class 598, same head `OnLine`/`InSpace` 210, head TYPE differs 167;
by category notehead 735, structural 656, dynamic 252, accidental 247, flag
35, ornament 24, clef 10, rest 8. Its `written` counters move the same way and
further: notes **7,933 → 7,756 (−177)**, dynamics **704 → 622 (−82)**,
pitches_altered_by_the_key 1,455 → 1,419, ties 289 → 283, beams 2,964 → 2,953,
slurs 159 → 161, `owned_by_another_staff` **933 → 1,121 (+188)**, refusals
4,115 → 4,289 (+174) against written events −174, `balanced=True`,
`unaccounted` empty, no `Unbalanced`.

**Breitkopf, which SHATTERS, is where the coarse category bites hardest**, over
its **6,259** newly-contested subjects: IoU floor alone 2,686, category test
alone 2,369, both 1,204; identical smufl name 2,686, **same category different
class 2,964**, same head `OnLine`/`InSpace` 461, head TYPE differs 148; by
category **structural 3,285**, notehead 1,223, accidental 628, dynamic 513,
flag 238, ornament 193, clef 99, rest 80. Its counters: notes **14,183 →
13,952 (−231)**, dynamics **1,307 → 1,167 (−140)**, articulations 2,436 →
2,388 (−48), rests 8,013 → 7,979 (−34), beams 6,510 → 6,479, ties 1,968 →
1,954, wedges 80 → 79, slurs 779 → 784 (+5), `owned_by_another_staff`
**2,354 → 2,631 (+277)**, refusals 10,976 → 11,241 (+265), `balanced=True`,
`unaccounted` empty, no `Unbalanced`. ⚠️ On a plate where *ink components are
not marks* the `structural` bucket is more than half the widening, and not one
of those 3,285 has been read against the print either.

⚠️ **The 36 accidental-category subjects sit beside ROADMAP 2.7's territory**
(a sibling lane is building the in-bar accidental). No code of theirs is
touched here; the note is so the interaction is on the record before the two
branches merge.

---

## 6. THE ACCOUNTING CONTROL

| record | arm | `<note>` | notes written | `owned_by_another_staff` | `unaccounted` | balanced | `Unbalanced` raised |
|---|---|--:|--:|--:|---|---|---|
| p1–p4 | base | 2,611 | 1,614 | 172 | `[]` | True | no |
| p1–p4 | arm | 2,573 | 1,572 | **215** | `[]` | True | no |
| Litolff whole | base | 12,424 | 7,933 | 933 | `[]` | True | no |
| Litolff whole | arm | 12,258 | 7,756 | **1,121** | `[]` | True | no |
| Breitkopf whole | base | 23,145 | 14,183 | 2,354 | `[]` | True | no |
| Breitkopf whole | arm | 22,886 | 13,952 | **2,631** | `[]` | True | no |

p1–p4, the refusals that moved: `owned_by_another_staff` **172 → 215 (+43)**,
`duration_narrowed` 303 → 310 (+7), `no_pitch` 188 → 180 (−8). Total refused
810 → 852 (+42); written 1,614 → 1,572 (−42). **The rise in refusals is matched
exactly by the fall in written notes**, which is §10d.3's test for ink loss — a
rise not matched that way would be a note that went nowhere, and `to_musicxml`
RAISES `Unbalanced` rather than returning a flag.

⚠️ A dropped copy is **never** lost ink: `A.is_relocated_copy`'s whole argument
is that a glyph awarded elsewhere has a twin there BY CONSTRUCTION, and this
change does not weaken it — it WIDENS the population in which a twin exists.
The one way it can lose ink is a SWAP (every member of one contest naming
somebody else), measured at 1 of 636 groups before this change, and it was a
dynamic letter, not a notehead.

---

## 7. ⚠️ THE HEAD TYPE IS NOT SETTLED BY THE DROP — traced, not assumed

§10d.1's warning: for a `Black`-vs-`Half` pair *"the drop of the loser silently
picks a duration."* **It does not, and the reason is where `duration` reads the
head from.**

`adjudicate_duration` (`rhythm.py:452`) calls `_head_class(ev)`, which is
`ev.rows(Q.NOTEHEAD_CLASS)` **on the glyph's own subject** (`rhythm.py:398`);
`Q.NOTEHEAD_CLASS` is written once per detection at `gather.py:424` from that
detection's own `d.smufl_name`. A cross-staff contest never copies a class
between subjects, and `export._place_notes` REFUSES the loser's row rather than
deleting it (unlike `transcribe`, which calls `dets.remove`). So:

* the surviving note's written value is **the reader's own reading of the
  surviving detection** — the case §10 and the brief both name as fine;
* the loser's `Q.NOTEHEAD_CLASS` row **stays on the record**, so the
  disagreement is visible to `trace` and to any later reader. That is §10d.1's
  first admissible route — *"the losing row stays on the record"* — satisfied
  by construction rather than by a new field.

33 of the 494 newly-contested subjects on p1–p4 are pairs whose head TYPE
differs (`noteheadBlack` / `noteheadHalf` / `noteheadWhole`); each is listed
with its twin and their IoU in `out/beethoven5-p1-p4-twins.json →
head_type_pairs`.

⚠️ **WHAT WAS NOT DONE, AND WHY.** The brief asked for a `class_contested`
detail on the band row. It is NOT written. `wiring.details()` DERIVES every
detail key `gather.py` writes and reports each one nothing reads as an open
finding; `staged.check` stands at exactly **255** on `origin/main` and this
item is gated on not exceeding it. No consumer is available inside this lane —
`adjudicators/ownership.py` and `export.py` are fenced off for the 2.7 sibling
— so the key would have been a producer with no reader (this project's own
named anti-pattern) bought at the price of the one number 2.6 is gated on. The
fact it would carry is already on the record, twice, as the loser's own rows.
**If a consumer is ever built, the detail is one line in the row-writing loop.**

---

## 8. THE REAL GATHER, page 3 — the control on the instrument

`real_gather_pair.sh 3 848dda47`: the Litolff count page, `--pages 3`,
`--no-surya --no-ocr`, weights
`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, each arm its own
`--out`. Arm 54 s, base 54 s — the wall time says neither is a cache.

**The precondition, printed first:** the two runs found the SAME INK —
**1,928 glyph boxes on page 3 in each arm, 1,928 matched at IoU ≥ 0.9, 0
unmatched either way.** Without that line every count below would carry
detector jitter as well as the change.

| | base | arm | Δ |
|---|--:|--:|--:|
| real gather — glyph subjects with a band row, page 3 | 140 | 247 | **+107** |
| real gather — `glyph_owner` verdicts, page 3 | 140 | 247 | **+107** |
| record-side recompute — same page, same statistic | 140 | 247 | **+107** |

**And it is the same ink:** 107 of 107 of the recompute's newly-contested
glyphs on page 3 are also newly contested in the real gather, matched by page
box at IoU ≥ 0.9. `out/real-gather-agreement-p3.json`.

⚠️ The two instruments are not one run and must not be read as one: the real
pair has no Surya/OCR rung, so its staves carry no read identity and
`glyph_owner`'s range veto has nothing to veto on. Absolute verdict counts
elsewhere would differ. What agrees — exactly — is the delta this change makes
and the ink it makes it on.

---

## 9. The crops, and the control that refused ten of them

`crop_contested.py`, 600 dpi, corner brackets on the exact head, the AWARDED
staff's own five `Q.STAFF_LINES` drawn in green and the FILED staff's in blue
where the two differ, a staff-space ruler down the left edge. Sean's correction
of 2026-09-23 — *"there is a staff at the top and a staff at the bottom - i
dont know which staff the cell is focussing on"* — is why the crop names the
staff at all, and for this population that is the whole question.

**19 written, 10 refused**, of 29 attempted at 600 dpi. The batch is
`out/print/litolff-p1-p4-NN.png` with
`out/print/crop-manifest-litolff-p1-p4.json`, one row per crop carrying
`VERDICT_none_yet: null`.

* **6** glyphs the widened contest MOVED to a neighbouring staff
* **7** glyphs it decided for their OWN staff
* **6** POSITIVE CONTROLS from contests the base arm already had

⚠️ **Which is which is NOT in the manifest.** A batch that labels its own
controls cannot fail — the reader simply agrees with the labels. The key is
`out/print/crop-key-litolff-p1-p4.json`, to be opened after.

⚠️ **THE FRAME CONTROL CAN FAIL AND WAS RUN IN A STATE WHERE IT DOES.**
Rendered at 300 dpi against the record's 600, refusals go **10 → 24 of 29**.
At the correct 600 dpi the ten refused are: three subjects on `staff/2/1/6`
and `staff/2/1/7` at contrast **5.00** (below the 8.0 margin), and seven on
page 4 at **−32.48** and **−78.91** — INVERTED, the staff's own recorded lines
landing on white.

⚠️ **The margin was NOT lowered**, and the inverted pages are **not this lane's
finding**: `benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §3 refused
`glyph/2/1/7/7/3` at exactly 5.00 and a page-4 pair at −12.25 on the same day.
This is the same staff-detection fault seen again by a second instrument, on
more staves. Recorded, not chased.

---

## 10. What this pass does NOT establish

* **No glyph has been adjudicated against a print.** §10e stands. The 19 crops
  are the instrument for that and their manifest is empty.
* **n = 2 documents, 3 records, one publisher pair.** Litolff MERGES and
  Breitkopf SHATTERS; the two are reported apart and never pooled.
* **The instrument is slow on a whole movement and that is worth knowing
  before the next lane budgets it**: rebuilding the log and running
  ADJUDICATE · GROUPS · EVALUATE · INFER · EXPORT costs 658 s per arm on
  Litolff (156,525 observations) and **2,698 s per arm on Breitkopf**
  (410,811 observations, 49,590 band rows). Running both records at once put
  the machine into memory compression and roughly quartered throughput; they
  were re-run one at a time.
* **It does not show the 85 resolved to the near staff are right.** The 189
  suggest the scoring is good; §10c's eight show it can also hold a note where
  it was cut, correctly.
* **The 29 dynamics are a cost with no adjudication behind it.** They are
  probably the `ffff` duplicate family; *probably* is not a measurement.
* **This is not a re-gather of everything.** `regather_ownership.py` re-runs
  ONE gather site. The real pair on page 3 is the only full gather here, and it
  is one page of one document.
* **`staged.check`'s three blind spots are untouched**: it cannot see a GATHER
  change, it cannot see the DETECTOR, and `wiring` matches a detail key by bare
  name.
* **The branch is based on `848dda47` and main has since advanced**
  (`0c683639` at the time of writing). `git merge-tree` reports exactly ONE
  conflicting file, `.gitignore`, where both lanes appended a block;
  `gather.py` merges cleanly, which is what confining the diff to
  `gather_ownership_evidence` and `CONTEST_IOU` was for. Rebasing would
  invalidate the base every figure here was measured against, so it was not
  done.
* **Two dated documents still quote the old value** and were deliberately not
  edited: `docs/map-flags-gates-and-guards-2026-09-16.md:126` (`CONTEST_IOU`
  `0.5`, ASSERTED) and `docs/symbol-dossiers/articulations-ornaments.md:188`
  ("the same class ... at IoU ≥ `CONTEST_IOU`"). Both are snapshots with a date
  in their name; the tree outranks them (rule 10).

---

## 11. Reproducing every number above

```
# the control, green then RED
python3 benchmarks/omr-owner-domain-2026-09/regather_ownership.py \
    library/_shared-records/beethoven5-p1-p4-ink-identity.record.json --control
OWNER_REGATHER_BREAK_CONTROL=1 python3 \
    benchmarks/omr-owner-domain-2026-09/regather_ownership.py \
    library/_shared-records/beethoven5-p1-p4-ink-identity.record.json --control

# sections 2-7, per record
python3 benchmarks/omr-owner-domain-2026-09/regather_ownership.py \
    library/_shared-records/<record>.json \
    --json benchmarks/omr-owner-domain-2026-09/out/<name>.json
python3 benchmarks/omr-owner-domain-2026-09/twin_classes.py \
    library/_shared-records/<record>.json \
    benchmarks/omr-owner-domain-2026-09/out/<name>.json

# section 8, the real pair (about two minutes)
bash benchmarks/omr-owner-domain-2026-09/real_gather_pair.sh 3 848dda47
python3 benchmarks/omr-owner-domain-2026-09/real_gather_agreement.py \
    --base benchmarks/omr-owner-domain-2026-09/out/real-p3-base.json \
    --arm  benchmarks/omr-owner-domain-2026-09/out/real-p3-arm.json \
    --record library/_shared-records/beethoven5-p1-p4-ink-identity.record.json \
    --recompute benchmarks/omr-owner-domain-2026-09/out/beethoven5-p1-p4.json \
    --page 3

# section 9, the crops
python3 benchmarks/omr-owner-domain-2026-09/crop_contested.py \
    --record library/_shared-records/beethoven5-p1-p4-ink-identity.record.json \
    --arm benchmarks/omr-owner-domain-2026-09/out/beethoven5-p1-p4.json \
    --pdf library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
    --label litolff-p1-p4 --dpi 600 --moved 11 --stayed 11 --controls 7
```

Tests and checks on the arm tree:
`pytest tools/omr/tests -m "not slow" -q` → **2,833 passed, 3 skipped, 2,216
deselected**; `python3 -m tools.omr.staged.check` → **TOTAL open=255**,
unchanged from `origin/main`'s 255, with `conventions` at 0 — the contest's
convention claim is already registered, as `[C4]` ("a note outside the staff is
joined to it by an unbroken ladder of ledger rungs") and `[C5]` ("the engraver
opens the gap above a staff precisely so its ledger notes can live there"),
both of which name `transcribe.py:3290 _dedupe_cross_staff_detections` in their
**Code** field. No registry entry was added.

The two real-gather records are gitignored (7–8 MB each, two minutes to
rebuild); everything the tables quote is in the committed JSON beside them.

---

## 12. §2.6b — the ownership losers at whole-movement scale, crops for Sean (2026-09-28)

Roadmap item 2.6b. §9 print-checked 2.6's DOMAIN change on 18 crops, page
scale, Litolff pp.1–4 only. Before the contest itself is touched, Sean asked
to see a sample of its **losers** — noteheads whose `glyph_owner` verdict
named the OTHER staff of the pair — at whole-movement scale, on the fresh
Brahms 1/i record (main `f4168dfd`, re-decided
`.claude/worktrees/redecide-f4168dfd/out-redecide/brahms/amended.record.json`,
read-only, not committed, 1.6 GB / 440,057 observations / 323,786 verdicts).
**No pipeline of any kind ran** — one `load_record`, one extraction pass, one
crop pass, per DECISIONS 2026-09-28's proof budget.

### The population

Every `glyph_owner` verdict, `outcome == decided`, category `notehead`,
current (not superseded by a later revision), whose `value` names a staff
other than the one `Subject.at(Kind.STAFF)` gives the glyph itself — i.e. a
candidate for `export.py`'s `owned_by_another_staff` drop
(`is_relocated_copy`, `export.py:956`). By construction every one of these
has a TWIN on the winning staff (the pair the contest is built from,
`gather_ownership_evidence`); **3,590 of 3,590 losers resolved to a twin**
re-derived independently here from `Q.GLYPH_BOX` (same category, IoU > 0.3,
`gather.py`'s own `CONTEST_IOU`), confirming the docstring's claim
mechanically rather than assuming it.

| deciding term | own staff is upper (lost to the staff below) | own staff is lower (lost to the staff above) | total |
|---|---:|---:|---:|
| `distance` | 1,236 | 810 | 2,046 |
| `ladder` | 864 | 531 | 1,395 |
| `range_veto` | 62 | 87 | 149 |
| **total** | **2,162** | **1,428** | **3,590** |

`human_owner` and `tied`/`no_evidence` contribute 0 to this population (no
review pass has touched Brahms yet; a tied contest carries no winner to lose
to). Spread across all 27 pages of the movement (pdf idx 0–26), not
concentrated on any one page.

⚠️ **This is 3,590, not the 6,008 `ROADMAP.md:86` names** ("`owned_by_
another_staff` (6,008 Brahms heads) — the largest missing-events cause").
Checked directly: `glyph_owner` losers by category on THIS record are
`structural` 7,686, `notehead` 3,590, `dynamic` 1,446, `ornament` 1,114,
`accidental` 878, `flag` 227, `rest` 140, `clef` 53, `time_sig_digit` 11 — no
single category or small combination lands on 6,008, and `export.py` checks
`no_pitch` and an undecided `duration` BEFORE the owner check, so the true
per-note `owned_by_another_staff` bucket can only be **at most** 3,590 on
notehead-derived events, not more. The 6,008 figure most likely comes from an
actual export run's `status_census` against an EARLIER revision of the Brahms
record: `ROADMAP.md`'s own item 1 shows the pitched-note count on this
document changing **965 → 1,410 → 3,529** across two re-decisions
(`92b6ab04` then `f4168dfd`) on 2026-09-28 alone, a >3.5× swing driven by the
meter-chain fix in 2.12j, and a duration/pitch change upstream of the owner
check changes exactly which notes reach it. This pass reads only the record
the brief named (`f4168dfd`, the current one); it does not run an export to
reconcile the two numbers, and the gap is flagged, not chased.

### The sample: 20 losers + 4 kept twins

Stratified by (deciding term × direction) into the six cells above, at
roughly the population's own proportions with every cell represented at
least twice, picked round-robin by page within each cell so the 20 spread
across the movement rather than cluster on one page (seed `20260928`,
`crop_losers_2_6b.py`): **5 / 4 distance, 4 / 3 ladder, 2 / 2 range_veto**
(upper/lower). Four more crops show the KEPT TWIN on the winning staff for
one contest from each of the four largest cells, so Sean can compare the
loser and the note that survived side by side — in all four, `twin_kept` is
`True` (the twin's own `glyph_owner` verdict, where it has one, names its own
staff; 3,585 of 3,590 twins in the whole population are `True`, 5 `False`,
i.e. the twin itself lost a *different* contest — none of those 5 were drawn
into this sample).

Every crop draws **both** candidate staves' `Q.STAFF_LINES` — BLUE the staff
the head was FILED on (and lost), GREEN the staff the record awards it to —
never one alone, per Sean's 2026-09-23 correction that a crop in the gap
between two staves commits to neither. The subject head is bracketed in RED
on its exact `bbox_page_px`; a ruler down the left edge ticks staff spaces off
the filed staff's top line. Cut from the PDF at the record's own 600 dpi.

⚠️ **THE FRAME CONTROL CAN FAIL AND WAS RUN IN A STATE WHERE IT DOES**
(CLAUDE.md rule 7). At the record's true geometry, 24 of 24 candidate crops
passed on both staves (contrast well above the 8.0 margin on every one, no
fallback needed). Shifting each FILED staff's lines by half a spacing and
re-running the same check against the same 600 dpi render: **0 of 24 pass** —
the control is not vacuously true.

### The deliverable

- `benchmarks/omr-owner-domain-2026-09/out/print/o26b-01.png` … `o26b-24.png`
  — crops 01–20 are LOSERS, 21–24 are the paired WINNERS (twins).
- `benchmarks/omr-owner-domain-2026-09/out/print/o26b-manifest.json` — one
  row per crop: `subject`, `filed_staff`, `winning_staff`, `deciding_term`,
  `margin`, `direction`, `twin_subject`/`twin_kept`/`twin_reason`,
  `frame_contrast`, `page_box`, and `VERDICT_none_yet: null` for Sean to fill.
  Nothing is blind here (unlike §9's shuffled batch) — the whole point is
  Sean can see the term and margin as context while he reads the print.
- `benchmarks/omr-owner-domain-2026-09/out/print/o26b-contact-sheet.png` — a
  4×6 grid of all 24, numbered, so the batch can be scanned in one pass;
  the individual PNG (via the manifest's `file`) is the one to zoom into
  before answering.
- `benchmarks/omr-owner-domain-2026-09/extract_losers_2_6b.py` reads the
  record once and writes the committed `out/o26b-cache.json` (2.7 MB: the
  3,590-row population, staff geometry, and every twin bbox);
  `crop_losers_2_6b.py` and `contact_sheet_2_6b.py` reproduce the 24 crops
  and the sheet from that cache alone, with no further record read.
  `check_category_breakdown_2_6b.py` reproduces the by-category table above.

```
python3 benchmarks/omr-owner-domain-2026-09/extract_losers_2_6b.py
python3 benchmarks/omr-owner-domain-2026-09/crop_losers_2_6b.py
python3 benchmarks/omr-owner-domain-2026-09/contact_sheet_2_6b.py
python3 benchmarks/omr-owner-domain-2026-09/check_category_breakdown_2_6b.py
python3 benchmarks/omr-owner-domain-2026-09/check_frame_control_can_fail_2_6b.py
```

**The question on every crop, exactly**: *right staff dropped (correct) /
wrong staff dropped (this staff's own note) / not a note?* — and for the four
winners, *is this a duplicate of its paired loser, or a different note?*

### What this pass does NOT establish

Same caveat as §9, restated because it is load-bearing and not a formality:
**no glyph here has been read against a print.** Every count above is a
record measurement — what a verdict says and what term decided it — and a
record measurement cannot say a note went to the right staff. `twin_kept`
answers "did the OWNERSHIP decision also keep the twin," never "is the twin
actually a real, correctly-read note" — that is exactly what crops 21–24 ask
Sean. This pass does not touch `glyph_owner`, `is_relocated_copy`, or any
other code; it reads one record and cuts crops.

### §2.6b.v — Sean's verdicts on the 24 crops (2026-09-28)

Raw: `1-3 R 4 ink 5-16 R 17 no red box 18 R 19-24 W`.

| deciding term | crops | right staff dropped | wrong staff dropped | not a note | unadjudicated |
|---|---|--:|--:|--:|--:|
| distance | #1–9 | 8 | 0 | 1 (#4, ink) | 0 |
| ladder | #10–16 | 7 | 0 | 0 | 0 |
| range_veto | #17–20 | 1 | **2** (#19, #20) | 0 | 1 (#17: box 9 px wide, ~0.2 spaces — too small to see; almost surely not a head) |

**16 of 19 adjudicated losers were dropped correctly.** The four kept twins
(#21–24, twins of #01/#06/#11/#14) are on the right staff, and each sits on
the SAME ink as its loser (page boxes coincide to a few px): the contest is
mostly de-duplicating one printed head detected from both cells, not losing
notes. ⚠️ **#21–24 were first rendered with REVERSED band labels** (the
winner crops passed the kept staff as `own_key`, painted "BLUE - lost");
Sean's "W" on them therefore reads "belongs to the blue-labelled staff" =
the staff that actually kept it, consistent with his R on the four losers.
Fixed (`lost_key`) and re-rendered.

**Consequences.** (1) The 3,590 `owned_by_another_staff` drops are NOT the
main source of Brahms's missing notes; the funnel's `missing_events` bucket
needs its other causes next (`duration_narrowed:beams_ambiguous` was the
second refusal). (2) `range_veto` is the weak term — 2 of 3 wrong on a
population of 149 — which is exactly where Sean's two conventions (ledger
lines name the owner; a hairpin sits under its staff; DECISIONS 2026-09-28)
should decide instead → 2.6c, narrowed to the range-veto population.

## §2.6c — Sean's two conventions, applied where `range_veto` decides (2026-09-28, BUILT not merged)

Branch `claude/owner-conventions-2.6c`. Cheap proof only (DECISIONS
2026-09-28: *"build and wire, stop burning runs on proof"*): a ONE-TIME read
of the real record via `record_io.load_record`, and unit tests. No re-gathers.

### #19/#20 diagnosed against the real record

Both crops are the SAME shape (`glyph/12/1/6/7/7` and `glyph/16/0/5/5/1`, one
row read each via a throwaway script against
`.../redecide-f4168dfd/out-redecide/brahms/amended.record.json`):

- The "own" staff (Sean's correct answer, `staff/12/1/6` / `staff/16/0/5`,
  both Horn/treble) sits 0.54 / 0.60 spaces above its own top line —
  `gather._observe_ladder`'s `expected = int(gap/spacing + 0.25)` rounds that
  to **0**, so no `Q.GLYPH_LADDER` row is ever filed for it. Not "no
  evidence" in the ordinary sense: the note is close enough that a ledger
  line would never be drawn there at all.
- The rival ("unidentified"/"Contrabassoon" staff, distance 3.78 / 3.12
  spaces) needs 4 / 3 rungs and `Q.GLYPH_LADDER` names **0 found** for both —
  a real, filed row, genuinely broken.
- Both resolve `MIDI 79 (G5)` under Horn/treble — 2 semitones above the
  `written_range` table's assumed ceiling (`[41, 77]`, F5) — so `_range_veto`
  fires on the CORRECT, near staff and hands the note to the rival, which is
  never vetoed (its instrument abstained / doesn't cover that register).
  `would_win_on_distance` already names the correct staff in both rows; only
  the veto overrides it.

**Neither convention, taken literally, is what fixes these two.** Convention
1 ("ledger lines... between it and the staff it belongs to") describes rungs
that are FOUND; here the correct side needs zero and the wrong side's are
simply absent — not "found toward one, none toward the other" in the literal
sense, but the *comparative* shape CLAUDE.md's 2026-09-23 precedent already
named at a smaller radius (a note one space beyond a neighbour's outer line
is that staff's, on its own first ledger line, while the far staff's
three-rung ladder was never detected — there the near candidate's rung WAS
found; here it needs none at all, one step further out). Convention 2 (the
hairpin) never gets a chance to speak on either crop: `Q.WEDGE_BOX` has ZERO
rows in page 12 system 1 or page 16 system 0 near either staff — checked
directly against the real record, not assumed.

### Did `glyph_owner`'s ladder term already use rung DIRECTION?

Partially, and only per-candidate, never comparatively. `_observe_ladder`
(2.14) already computes `expected`/`found` SEPARATELY toward each candidate
(so it is directional in the sense that a note's ledger requirement toward
staff A and toward staff B are two different numbers), and
`_ladder_complete`'s existing `ladder_complete` term already credits
whichever candidate's OWN run is complete. What it never did is COMPARE the
two candidates' ladder states to each other — a candidate needing zero rungs
and a rival needing several with none found were both simply "no term",
indistinguishable from each other. That comparison is the new
`_ledger_direction_winner`.

### The terms added, and the order

In `tools/omr/staged/adjudicators/ownership.py` (`adjudicate_glyph_owner`),
two new ADDITIVE terms, both gated to fire only when they can be decisive and
silent otherwise:

1. **`ledger_direction`** (`_ledger_direction_winner`, weight `W_LEDGER_
   DIRECTION = 8.0`, tag A-OWN-3). A candidate is "clean" if it needs no
   rungs at all (no `Q.GLYPH_LADDER` row) OR its own ladder is genuinely
   complete; "broken" if it has a real row that is incomplete. Fires for the
   ONE clean candidate only when exactly one candidate is clean AND at least
   one rival is broken — silent whenever more than one candidate is clean
   (ambiguous, the same reasoning `tied` already applies) or none is.
   ⚠️ **The weight had to beat `range_veto` on its own, not lean on
   `ladder_complete`**: `4.0 (ladder_complete) - 6.0 (range_veto) = -2.0` is
   still a net loss, so a genuinely complete ladder is NOT by itself decisive
   against a veto — `test_a_genuinely_complete_ladder_still_needs_the_
   convention_to_beat_a_veto` pins this arithmetic so it can't regress
   silently. An earlier draft of this function refused to fire wherever ANY
   candidate had a genuine complete ladder; that gate was WRONG (built on
   the false assumption that `ladder_complete` alone was already decisive)
   and was removed before landing.
2. **`hairpin_separates`** (`_hairpin_separates`, weight `W_HAIRPIN_
   SEPARATES = 7.0`). Reads `Q.STAFF_LINES` (candidate's own bottom line,
   page px) and `Q.GLYPH_BOX` (this glyph's own `y_center_page` — newly added
   to `wants`, since `Q.GLYPH_BAND_DISTANCE` never carries a page
   coordinate) plus `Q.WEDGE_BOX` filed under the candidate
   (`scope=SELF_AND_DESCENDANTS`, since a hairpin is a GLYPH-kind subject
   under the STAFF). Fires when the head lies between the candidate's own
   bottom line and a hairpin filed under it, in page pixels. A `DETECTOR`-
   reader wedge (cell-frame only, no page box) is DECLINED, not defaulted
   (CLAUDE.md §10). A witness from a different glyph family, reader and
   quantity than the notehead's own rows, so it is never in the notehead's
   correlated group by construction.

Order realised via the reason-priority chain plus weight ordering:
`human_owner` (unchanged) → `ledger_direction` (8.0) → `hairpin_separates`
(7.0) → `ladder`/`range_veto` (±6.0/4.0, unchanged) → `distance` (0.5,
unchanged). `Q.GLYPH_BOX`, `Q.WEDGE_BOX`, `Q.STAFF_LINES` added to `wants`/
`composed_from`; `ledger_direction`/`hairpin_separates` added to `reasons`.

### RED → GREEN

New file `tools/omr/tests/test_staged_owner_conventions.py`, 10 tests:
synthetic RED→GREEN for each convention (rungs toward one staff none toward
the other; a hairpin below the head), two controls per convention (no
evidence → unchanged; a hairpin *not* between the two → no effect; a
DETECTOR-only wedge with no page frame → declined), the arithmetic pin above,
and — as the real RED cases — #19 and #20 rebuilt from the exact rows in the
committed record (`Log` + `adjudicate.adjudicate_one`, Verdicts injected
directly for `Q.INSTRUMENT`/`Q.CLEF` to avoid re-deriving identity from
scratch): both now decide `ledger_direction` → the Horn's own staff, matching
Sean's `wrong_staff_dropped` verdicts.

**⚠️ #19's own duplicate (`glyph/12/1/5/7/8`, the same ink filed under
`staff/12/1/5`) is a DOCUMENTED RESIDUAL, not a regression.** On its own
contest neither side is clean: `staff/12/1/5` needs 3 rungs (none found),
`staff/12/1/6` needs 1 (none found) — two broken ladders, correctly silent
per the "not evidence either way" rule, so it still decides `range_veto` →
`staff/12/1/5`, unchanged and still wrong by Sean's #19 verdict. Recorded as
`test_crop_19s_own_duplicate_stays_wrong_a_documented_residual`. #20's
analogous duplicate (`glyph/16/0/4/5/1`) is NOT a residual: its own contest
has `staff/16/0/4` broken (3 expected, 0 found) against `staff/16/0/5` clean
(0 expected) — the same shape as #20 itself — so it independently converges
on the SAME correct staff. Not asserted in the test file (out of the fenced
scope's time budget) but confirmed by hand against the same record dump.

**Two pre-existing tests broke and were repaired, not worked around.**
`test_staged_ownership.py::test_a_broken_ladder_contributes_NOTHING_not_a_-
penalty` and `test_staged_ladder_rungs.py::test_found_drops_and_the_ladder_-
term_is_withdrawn` / `test_an_EMPTY_named_ladder_takes_the_same_path_as_old_-
shape` all modelled a "nearer, closer" staff (1.0 space from its own band —
`gather` would expect ONE real rung there) with NO `Q.GLYPH_LADDER` row at
all, relying on the pre-2.6c fact that an absent row and a broken one were
equally inert. `_ledger_direction_winner` reads an absent row as "no crossing
needed", which is false for a candidate at 1.0 space — so each fixture now
also files that candidate's OWN broken row (`expected=1, found=0`), matching
what a real gather would produce and restoring each test's STATED intent
(two broken ladders / an incomplete discount — no directional signal either
way). The VALUE these tests assert never changed, only the reason a
mislabelled fixture would have reported.

### The 149-contest re-run: SKIPPED

Not run. Re-deciding all 149 `range_veto` contests in-memory needs each
one's full `Q.GLYPH_BAND_DISTANCE`/`Q.GLYPH_LADDER`/`Q.WEDGE_BOX`/
`Q.STAFF_LINES`/`Q.INSTRUMENT`/`Q.CLEF` rows pulled from the 1.5 GB record and
re-adjudicated per contest — more than the "one record read" the proof
budget asks for, and the landing message narrowed this session to what is
"done and tested" only. Whoever picks this up next: `record_io.load_record`
once, filter `verdicts` where `quantity == "glyph_owner"` and
`reason == "range_veto"`, and for each subject re-run
`adjudicate.adjudicate_one` against the SAME frozen `Log` object the record
loads into (no re-gather needed — GATHER's rows are already on the record).

### OPEN — Sean's correction on nearness vs. the ledger (2026-09-28, not built)

After landing was already underway, Sean corrected the framing directly:
*"Nearer to the staff is not always going to be right but ledger lines will
be. If it is not working out that way right now then the tests are off."*
Three consequences, none built in this pass:

1. **Ledger direction should run BEFORE `range_veto` and `distance` both**,
   not merely score high enough to usually beat them additively. The current
   implementation is a large ADDITIVE term (8.0), not a hard precedence
   gate — it can in principle still lose to a large accumulation of other
   terms, which a strict ordering would not allow.
2. **A FAR note with no rungs found in either direction should ABSTAIN**, not
   fall through to distance. Today's code, when neither side is "clean"
   (both broken, or both far with nothing found), falls through to the OLD
   tiers unchanged — which is right for a NEAR miss (a candidate needing 0–1
   rungs is a hint, not a claim) but per Sean's correction is WRONG once both
   candidates are genuinely FAR (needing several rungs) and neither's is
   found: that should read as a reading gap, not a distance tie-break. The
   cut for "far" needs to be measured from the record (candidate `expected`
   at the point the vacuous zone ends, `int(x + 0.25) >= 1`, i.e. roughly one
   space outside the band — cite the real distribution before picking a
   number).
3. **Three heads are evidence the RUNG-CREDITING is buggy, not the rule**:
   Litolff `glyph/10/1/2/12/6`, Breitkopf `glyph/4/1/2/8/31` (both: `notehead_-
   precision.belongs_to_a_nearer_staff`'s rung exception currently credits a
   rung toward the FILED staff that Sean says is wrong — the far staff is the
   real owner and something is naming the wrong rung, or its direction, or
   its owner), and Litolff `glyph/8/0/6/12/7` (not a note at all). NOT
   diagnosed in this pass — `notehead_precision.py` is fenced off this lane,
   and the two 27b-arm records were not loaded (out of the cheap-proof/no-
   extra-runs budget this close to landing). **Next step**: load
   `.../27b/arm/litolff-arm.record.json` (and the Brahms arm beside it) OR
   crop just these two heads' neighbourhoods from the PDF with rung boxes
   drawn (`omr-owner-domain-2026-09/crop_losers_2_6b.py`'s banded style) and
   read what the credited "rung" actually is — a staff-line fragment boxed
   `ledgerLine`, a neighbouring head's own rung, a sign/direction error, or
   the note's own line miscounted. Whatever the cause, it should be fixed by
   calling `ownership._ledger_direction_winner` (or a shared helper factored
   out of it) from `notehead_precision.belongs_to_a_nearer_staff`'s rung
   exception, so "which staff do these rungs point to" is answered in ONE
   place — flagged here as the follow-up `notehead_precision.py` needs next,
   not built in this pass (fenced off, and the correction landed too late in
   the session to build and prove cheaply). → BUILT in §2.6c.2 below.

## §2.6c.2 — the second half: the ledger lines as a HARD rule, `far_no_rungs`, the rung-crediting bugs, one helper (2026-09-28, BUILT not merged)

Branch `claude/ledger-hard-2.6c`. **Path: STAGED** (`adjudicators/ownership.py`,
`adjudicators/notehead_precision.py`, `export.py`, a perf change in
`record.py`). Sean, 2026-09-28: *"Nearer to the staff is not always going to
be right but ledger lines will be. If it is not working out that way right
now then the tests are off."* Proof budget per DECISIONS 2026-09-28: unit
tests RED→GREEN, ONE saved-record read per document (no re-gather, no
export), 8 crops.

### The three rungs Sean said were wrongly credited — what they ARE

Read off the two 27b arm records (`…start-here-questions-7d5637/…/27b/arm/`)
with `record_io.load_record`; cut into `tools/omr/tests/fixtures/
ledger_direction_2_6c.json` by `extract_ledger_fixture_2_6c.py`.

| crop | head | the "rung toward the filed staff" 2.7b credited | what it is |
|---|---|---|---|
| #4 Litolff | `glyph/10/1/2/12/6`, 3.67 sp below staff 2, 0.97 above staff 3 (on staff 3's 1st ledger; that line never boxed) | `glyph/10/1/2/12/4`, 2.64 sp below staff 2 | the OWN LINE of the chord-mate `glyph/10/1/2/12/1`, which stands on staff 3's **2nd** ledger — a NEAR-staff rung lying beyond the head. Staff 2's rungs 1 and 2 are absent; the rung is 0.36 sp off staff 2's grid and on staff 3's. |
| #22 Breitkopf | `glyph/4/1/2/8/31`, 5.45 sp below staff 2, 1.09 above staff 3 (on staff 3's 1st ledger, boxed: `4/1/3/8/21`) | `glyph/4/1/2/8/26`, 4.49 sp below staff 2 | the same shape: the chord-mate's own line (`4/1/2/8/3`, staff 3's 2nd ledger). Staff 2's rungs 1–3 absent. |
| #10 Litolff | `glyph/8/0/6/12/7` — the `s` of *sempre* | `glyph/8/0/6/12/2` (staff 6's 1st ledger; the 2nd, `8/0/7/12/6`, is in staff 7's cell) | two REAL rungs of staff 6 — the ladder of the real note `glyph/8/0/7/12/3` standing on the 2nd (itself refused on staff 7 by 2.7b, correctly). The ladder ENDS 1.37 sp short of the `s`. |

None is a staff-line fragment and none is a direction error. The bug is the
**predicate**: 2.7b kept a head on ANY kept rung lying between it and the
filed staff. A rung is evidence for a staff only as part of a LADDER from
that staff that reaches the note. The three G heads Sean confirmed on the
same sheet have exactly that — #1 `16/1/7/14/0`: 2 of 3 rungs, reaching to
0.80 sp; #14 `12/0/11/14/1`: 3 of 3, head on the 3rd; brk-02 `9/0/11/0/1`:
rung 1 never boxed, rung 2 and the head's own 3rd line boxed.

### What was built

1. **ONE helper**, `ownership.ledger_direction` over `ladder_side` (one per
   candidate staff): walk off the staff's outer line one space per step with
   GATHER's own arithmetic (`LEDGER_ROUND_UP`, half-space grid, x-overlap),
   over the `ledgerLine` boxes of the head's cell and each candidate's
   same-index cell (plus any rung GATHER's ladder rows named), reading their
   3.4g-2 verdicts. A side **points** when it needs no rung, or has ≥ 1 rung
   that is not the head's own line, ≤ `LADDER_MAX_MISSING` (1) missing, and
   its outermost rung within `LADDER_REACH_SPACES` (1.0) of the head. Exactly
   one side points → that staff. Where only GATHER's anonymous count exists
   (an old record; a fixture with no page box) a side points only on a
   COMPLETE ladder — the first half's `clean`, unchanged.
2. **`glyph_owner` takes it as a GATE**: `human_owner` → `ledger_direction`
   (returns before any term is summed; `W_LEDGER_DIRECTION` is deleted) →
   [additive: hairpin, ladder, range veto, distance]. `TestTheHardGate` pins
   the configuration that out-voted the additive +8.0 (hairpin +7 on the
   rival plus a −6 veto on the ledger side).
3. **`far_no_rungs`**: every candidate needs ≥ `FAR_MIN_RUNGS` (2) rungs (gap
   ≥ 1.75 sp from every band) and no rung (own line excluded) was found
   toward any → ABSTAIN, unless a hairpin speaks. A near miss (a candidate
   needing 0–1) keeps today's tiers. **Downstream**: an abstained owner used
   to fall through `is_relocated_copy(None) == False` and be WRITTEN on the
   staff its cell was cut from — a guess. EXPORT now drops it under the named
   refusal **`owner_not_read`** (`ownership.OWNER_NOT_READ_REASONS`); the
   `Unbalanced` equality holds (`TestExportCountsAnUnreadOwner`).
4. **2.7b calls the same helper**: `_belongs_to_a_nearer_staff`'s exception
   is now "the ledger names the FILED staff", over the head's cell and the
   near staff's same-index cell. `OWN_LEDGER_MAX_SPACES` now lives in
   `ownership.OWN_LINE_MAX_SPACES` (re-exported under the old name).
5. **`hairpin_separates` stays ADDITIVE (my call)**: it can no longer
   override a ledger answer (that returns first — on the records below the
   gate took 2 Litolff / 29 Breitkopf contests from `hairpin_separates`, 0 /
   4 of them with a different winner); its
   7.0 already beats a lone veto and any distance; the only mix that
   out-votes it — a veto on its side PLUS a rival's genuinely complete
   ladder — pits it against ledger evidence no crop has adjudicated, and a
   gate there would be a rule without a crop.
6. **Perf, `record.Log`**: a descendants query at a NEW subject was a
   containment test against every subject of the quantity (18 ms per cell
   against Litolff's 37,390 `Q.GLYPH_BOX` subjects); an ancestor-keyed index
   answers it by lookup in the same order (`test_staged_record`'s naive-scan
   equivalence, now also at STAFF and CELL). Whole-record `glyph_owner`
   re-decision: Litolff 1.0 s → 2.3 s, Breitkopf 4.4 s → 7.8 s.
7. `wiring.KNOWN_GAPS` loses `Q.GLYPH_LADDER.found` (the count fallback reads
   it). ⚠️ `wiring.details` matches detail keys by bare substring, so the two
   new imports of `ownership` are spelled as bare module imports — the
   dotted path would read as a consumer of `Q.GLYPH_BAND_DISTANCE`'s home-
   staff flag that nothing is (CLAUDE.md §4d's third blind spot, hit twice
   here and fixed at the import, not in the gap list).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED — the three ladder
thresholds (header comment in `ownership.py`). ⚠️ **Not on a cliff**: over
every side with a rung toward it, `missing` is 0:246 · 1:431 · 2:113 · 3:10 ·
4:1 (Litolff) and 0:1812 · 1:747 · 2:214 · 3:75 · 4:32 · 5:9 (Breitkopf);
`reach_spaces` in quarter bins falls off after the 1.0 bin on Breitkopf
(197 → 14) but has NO gap on Litolff (0.75:264 · 1.0:118 · 1.25:68 · 1.5:64 ·
1.75:81). The values are argued from the six crops, not measured.

### RED → GREEN

`tools/omr/tests/test_staged_ledger_direction.py` (18 tests), RED on
`8100c9ff`: 13 failed / 5 passed. The real RED cases: #4 and #10 refused; #22
no longer kept by the chord-mate's rung (it yields to the contest, which
gives it to staff 3 on its complete ladder); `glyph_owner` #1 `distance`→8
becomes `ledger_direction`→7, #14 `ladder`→10 becomes `ledger_direction`→11,
brk-02 `tied` becomes `ledger_direction`→11 — all three Sean's G. Positive
controls in the same class: brk-02 / #1 / #14 with the contest removed are
KEPT by the helper (their value assertions hold on both trees; on 8100c9ff
they fail only on the new `ledger` detail key); a near miss still decides by
`distance`; a lone rung is not a ladder. `test_staged_nearer_staff.py`: the
one-rung "exception" test is REPLACED by a complete-ladder keep plus a
one-rung REFUSE (RED on 8100c9ff). Fast tier **3,584 passed**, 3 skipped.
`staged.check` **250 → 249** (wiring 68 → 67).

### The ONE saved-record read — base vs arm on ONE record

`readjudicate_owner_2_6c.py` re-decides only `glyph_owner` (every contest)
and `notehead_is_not_a_notehead` (every head the 2.7b signal reached) on each
27b arm record, from its own GATHER rows plus its saved `ledger_is_not_a_
ledger` / `instrument` / `clef` verdicts — run from an extracted 8100c9ff tree
AND from this branch, then diffed subject by subject by `diff_base_arm_2_6c.
py` (`out/2.6c-base-vs-arm-*.json`, `out/2.6c-readjudicate-*.json`). ~40 s
per document. ⚠️ The arm records were gathered before 2.6/2.14; a re-gather
would change the populations (not done — DECISIONS 2026-09-28).

| | Litolff (6,013 contests) | Breitkopf (24,795) |
|---|--:|--:|
| **newly `far_no_rungs`** (was distance / range_veto / tied) | **389** (360 / 26 / 3) | **266** (219 / 39 / 8) |
| **winner changed to another staff** | **33** (29 distance, 4 ladder → `ledger_direction`) | **115** (69 distance, 10 tied, 8 range_veto, 6 ladder, 4 hairpin → `ledger_direction`; 14 `ledger_direction` → the other staff; 4 `ledger_direction` → `range_veto`) |
| same winner, reason relabelled | 399 | 1,252 |
| identical | 5,195 | 23,170 |
| 2.7b heads re-read / newly refused | 1,524 / **6** (incl. #4, #10) | 3,006 / **15** |
| 2.7b refusals reversed | 0 | 0 |

The three named heads: #4 → refused `belongs_to_a_nearer_staff` (was kept);
#10 → refused (dropped; Sean's N — the reason word is the nearer-staff one,
the outcome, not written, is right); #22 → still not refused by 2.7b (it
yields) and `glyph_owner` gives it to staff 3 (`ladder`), as before.

⚠️⚠️ **`far_no_rungs` costs notes, and the crops say why.** All 655
abstentions are `nothing_boxed_at_any_step` — no ledger box, kept or
refused, at any step toward any candidate. A head detected in two cells
carries two contests, so this is up to ~195 / ~133 notes no longer written
(counted `owner_not_read`) where distance wrote one copy before — and o26b
found distance right 8/8. Several of the eight crops visibly show ledger
lines the detector never boxed (e.g. Breitkopf -01, a chord on printed
ledgers above the lower staff; -02, a run hanging under the upper staff).
That is Sean's rule working as stated — *a far note with no rungs found
either way is a reading gap* — and it points the next item at ledger
RECALL (finding the rungs), not at the rule. Sean's call whether it ships
before recall does.

### Crops for Sean (`out/print/2.6c-far-{litolff,breitkopf}-0{1..4}.png`)

8 newly-abstaining heads, 4 per document (seed 2026092826 over the
far_no_rungs list), `crop_far_no_rungs_2_6c.py`. Banded: GREEN = the UPPER
candidate, ORANGE = the LOWER — colour follows POSITION, not role (the 2.7b
sheet's role colours swapped above/below). Frame control per crop: both
staves' recorded lines must pass AND the same lines shifted half a space
must FAIL (1 Litolff head refused); `--break-frame` alone refused 99 of the
first 103 heads it tried. Manifests carry `VERDICT_none_yet: null`.
Question: *GREEN / ORANGE / not a note — and are there ledger lines?*

### Not done / open

- `tied` abstentions are still WRITTEN on their filed staff at export (both
  twins) — the same rule-8 shape fixed here for `far_no_rungs`,
  pre-existing and outside this fence (`OWNER_NOT_READ_REASONS` excludes it
  on purpose).
- An `owner_not_read` head can still carry a decided `accidental_owner`
  pairing; the accidental census counts it `unowned` (partition holds).
- The Breitkopf 14 `ledger_direction` → other staff and 4 → `range_veto`
  reversals (count-only ledger on base vs geometric today) are
  unadjudicated.
- No GATHER change: `Q.GLYPH_LADDER` still files an anonymous `found`;
  both decisions now read the ledger boxes directly, so nothing needed it.
- CLAUDE.md §4c's list of EXPORT refusals does not yet name `owner_not_read`
  (left for whoever merges; this lane did not edit the spec).

## §2.6d — a far head's ledger rungs are READ from the ink (CV), not only from the detector's boxes (2026-09-28/29, BUILT not merged)

Branch `claude/ledger-cv-2.6d`. **Path: STAGED** (`gather.py`,
`adjudicators/ownership.py`, `adjudicators/notehead_precision.py`,
`record.py`, `capture.py`, `adjudicate.py`). Sean, via §2.6c.2's own close:
*"a far note with no rungs found either way is a reading gap"* — 2.6c.2
measured that gap at **389 Litolff / 266 Breitkopf** newly `far_no_rungs`
contests on the saved 27b arm records, up to ~330 notes no longer written,
and named the next lever as ledger RECALL: two of the eight crops it cut for
Sean show printed ledger lines the detector never boxed. This builds that
second reader.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

The thresholds in `gather.py`'s `LEDGER_RUNG_INK_*` constants (header
comments there, restated once): a printed rung is 1.5–2 head widths wide
(`LEDGER_RUNG_INK_WIDTH_HEAD_MULT = 1.75`), its stroke as thick as the
staff's own measured line (`Q.STAFF_SKEW.thickness_px`, `median_line_
thickness_px` — see the bug below), a window at or above 0.55 ink counts as
"inked" (`LEDGER_RUNG_INK_DENSE`), and a band one thickness further up and
down must read under 0.35 or the stroke found is thick, not thin
(`LEDGER_RUNG_INK_ADJACENT_MAX`). **NOT CONFIRMED against a print anywhere
in this pass** — falsified by a print-adjudicated rung this test rejects, or
a non-rung it accepts; the six crops below are the first look, not a
verdict. The adjacent-band guard does NOT discriminate a slanted beam
crossing the window at a shallow angle — flagged, not built.

### What was built

1. **`Q.LEDGER_RUNG_INK`** (`record.py`; `CLAIM.MEASUREMENT`, `capture.py`
   graded `RELATION` beside `LEDGER_INK_UNDER`), one row per (head glyph,
   candidate staff, step) — the SAME step arithmetic `_observe_ladder`
   already walks (`LEDGER_ROUND_UP`, one space per step from the candidate's
   outer line). `value` is whether a thin horizontal run was found; `detail`
   carries the three window densities, the adjacent-band guard, the exact
   page-pixel window (`window_page_px`), and `want_y_page` — enough to cut a
   crop from later, with no re-gather.
2. **`gather.ledger_rung_ink`** (pure function, canonical-pixel frame): three
   bins at the tested y — CENTRE (over the head's own x-span), LEFT and
   RIGHT (the overhang PAST the head's edges, the guard against a bare
   stem, which never reaches past the head at all) — plus the adjacent-band
   thickness guard. `gather._observe_ledger_rung_ink` does the frame
   conversion (page px → the CANDIDATE's own cell's canonical px, inverting
   `_page_box`'s arithmetic) and samples the candidate's own cell's
   `image_no_staff` at the head's own measure index (falling back to the
   head's own cell where the candidate's carries no raster) — the SAME pad-
   reaches-the-neighbour fact `cell_rungs` already relies on (CLAUDE.md
   §10). One abstain call site covers every raster/geometry failure
   (`ABSTAIN.NO_MASK` / `NO_STAFF_GEOMETRY`), consolidated on purpose — see
   the wiring accounting below.
3. **`ownership.cv_rungs`**: reads `Q.LEDGER_RUNG_INK` rows on the contested
   glyph where `value is True`, and turns each into a `Rung` (new field
   `source: "detector" | "cv_ink"`) at the EXACT page window/y the GATHER
   row already measured — no re-derivation, no re-matching. `_contest_
   ledger_reading` (`glyph_owner`) and `_belongs_to_a_nearer_staff` (2.7b)
   both now build their rung pool as `cell_rungs(...) + cv_rungs(ev)`: ONE
   helper, two readers, merged before `ladder_side`'s own step-matching ever
   runs — a step is credited if EITHER reader named it. `LadderSide` gained
   `sources: {rung_key: "detector"|"cv_ink"}`, surfaced in `summary()`, so
   `trace` can say which reader decided a step. `Q.LEDGER_RUNG_INK` joined
   both decisions' `wants`/`composed_from` and `adjudicate.READINGS[Q.
   GLYPH_OWNER]`; 2.7b's own module reads it directly too (`signal["cv_rung_
   ink_rows"]`, informational) so the cross-module `cv_rungs(ev)` call — an
   ALIASED import, invisible to `inventory`'s same-module AST walk — is not
   the only literal mention of the quantity there (CLAUDE.md §4d's third
   blind spot, hit and fixed the way §2.6c.2 fixed its own instance: at the
   read, not the gap list).

### A real bug the first real gather found

`Staff.line_thickness_px` is `list[float] | None`, PER LINE top-to-bottom
(`types.py:63`), not the scalar the first draft assumed reading it straight
off `pws.staves` — `float()`ing it crashed the very first page gather
(`TypeError: float() argument must be a string or a number, not 'list'`).
Fixed to `median_line_thickness_px` (`types.py:73`), the derived scalar
`measure_extractor.py:1390` already reuses for exactly this reason. Caught
by RUNNING the pipeline, not by a test — the unit tests below used a fake
staff/cell and never exercised the real attribute's shape; a lesson for
whoever writes the next GATHER reader touching a `Staff` field this pass
did not already read.

### RED → GREEN

`tools/omr/tests/test_staged_ledger_rung_ink.py` (26 tests, 4 parts: the
pure measurement on synthetic rasters; GATHER integration on a fake cell;
the ONE helper crediting a step from a `Q.LEDGER_RUNG_INK` row with no
detector box anywhere; 2.7b asking the same helper). RED on `c2ab5f55`: 20
of 22 fail (`gather.ledger_rung_ink`, `gather._observe_ledger_rung_ink`,
`ownership.cv_rungs` do not exist there) — the 2 that pass are the negative-
control fixtures kept on purpose (CLAUDE.md §6b: *"a refusal test needs a
positive control in the same class, or it passes by refusing everything"*).
Fast tier **3,606 passed**, 3 skipped (3,584 + 22 new; one apparent failure
mid-session was `test_stem_notehead_gate`'s source-text assertion catching
`gather.py` mid-edit — CLAUDE.md §6c's own warning, reproduced exactly, and
gone on a clean rerun with no concurrent edits). `staged.check` **249 →
252**: `wiring`'s "UNRESOLVED gather sites" bucket (a pre-existing, already-
tolerated category — a Subject bound from a caller, unresolvable by static
AST, the same shape `_observe_ladder`'s own `g` already sits in) grows by 3
call sites (one consolidated abstain, one abstain, one observe inside the
per-step loop) — `inventory`/`capture`/`gather_coverage`/`reach` unchanged
at their pre-2.6d counts once `READERS.CV_LEDGER` was registered in
`capture.READER_RASTER` and the cross-module `wants` blind spot above was
fixed. **0 unaccounted, 0 stale** on every sub-check; every added finding
sits in a category already on `KNOWN_GAPS`/registered vocabulary, none of
them a new kind of gap.

### The one-page base-vs-arm re-gather — REACH, not accuracy

Both pages, `--no-surya` (2.7's own margin-label rungs never touch
ownership): **Breitkopf 317803 pdf index 1** and, within budget,
**Litolff 984073 pdf index 3**. Base = `c2ab5f55` in a separate worktree,
same weights, same page, same flags.

| | Breitkopf p2 (base → arm) | Litolff p4 (base → arm) |
|---|---|---|
| `Q.LEDGER_RUNG_INK` rows measured | n/a → 547 | n/a → 329 |
| … `found=True` | n/a → **0** | n/a → **0** |
| … abstained (`window off the raster`) | n/a → 147 | n/a → 0 |
| `glyph_owner` `far_no_rungs` | 10 → **10** | 14 → **14** |
| every other `decided`/`abstained` count | identical | identical |

**REACH IS REAL AND THE COMPOUND TEST IS CONSERVATIVE, NOT DEAD.** 547 + 329
= 876 windows were actually measured (not a population of zeros — centre
density alone reaches 1.0 on 193 of the 547 Breitkopf rows), and every
`far_no_rungs` count, every `glyph_owner` verdict and every downstream
decided/abstained count on BOTH documents is BYTE-IDENTICAL base to arm: on
these two specific pages the compound test never once said `found=True`, so
nothing downstream had a new fact to read. This is the honest result, not a
null run: reach is measured first (CLAUDE.md rule 5) and it reaches;
accuracy on these two pages is exactly zero credits, which the six crops
below explain rather than merely report. ⚠️ **UPDATE, §2.6d.2 (2026-09-29,
manager follow-up)**: zero on these two ACCEPTANCE-SET pages specifically
is not zero everywhere — calibrating on the 2.6c.2 crops' own positive case
(a different page, Breitkopf pdf idx 22) found a real printed rung this
first pass MISSED (an overhang-averaging bug) and, once fixed, a real
BEAM false positive the fix's own widening exposed (a second, level-guard
fix). See §2.6d.2 for both, the retuned constants, and the real positive
fixture that proves it.

### Six crops for Sean (`out/print/2.6d-cv-{brahms,litolff}-0{1,2,4}.png`,
`2.6d-cv-litolff-0{3,4,8}.png`)

Not "heads the CV rungs newly decide" — there are none to show on these two
pages — but the CLOSEST near-misses to `found=True` (`crop_cv_rung_2_6d.py`,
banded style of `crop_far_no_rungs_2_6c.py`: the candidate staff shaded
green, the head bracketed red, the EXACT tested window drawn as a dashed
blue rectangle at the measured page position). Frame control reused from
`crop_losers_2_6b._frame_ok` (0 refused of 8 attempted; every kept crop's
staff passed intact AND failed shifted half a space).

Looking at them: **brahms-01** and **brahms-02** are solid noteheads sitting
on or beside a staff line (one beside a `pp`, one under a slur/beam) — all
three of centre/left/right pass DENSE, and the adjacent-band guard correctly
refuses them (a filled notehead is thick, not a thin rung, and the crop
shows exactly that). **brahms-04** is a heavy horizontal band spanning the
ENTIRE crop width just below a staff — almost certainly a print/scan
artefact or a system rule, not a note-specific rung; the guard refuses it
too. **litolff-03** and **litolff-08** are Litolff's own MERGING signature
(CLAUDE.md §10): a note fused into a chord blob, or a note's own beam/flag
ink, sitting where the window is centred — again the head's own ink, not a
rung underneath it. **litolff-04**'s adjacent reading (0.356, barely over
the 0.35 cap) is the closest thing to an open question here: dense ink
directly under the staff that could be a rung fused with a neighbouring
note's stem on a merging plate, or could be that neighbour's own ink with
no rung at all — Sean's call, and the reason the manifests carry
`VERDICT_none_yet: null` rather than a guess.

**No case seen argues the guard is wrong.** Six for six, the ink the test
rejected is demonstrably not a thin rung reaching past a head on both
sides — which is evidence the mechanism is discriminating correctly on
what little it has been shown, not evidence it is calibrated (CLAUDE.md
rule 7: a control that never fails is not a control; here the guard fires
on every real candidate offered and there is no positive case in this
sample to check it does not ALSO fire on a genuine rung).

### Not done / open

- **Zero positive reach on real pages.** The two pages measured are not the
  pages the motivating finding's crops came from (those were cut from
  whole-movement 27b arm records, not pdf-index-1/-3 specifically) — a
  whole-movement re-gather (needs two full re-gathers to price, CLAUDE.md
  §4d) is the next test of whether the mechanism ever fires `True`
  anywhere, and was not run here (Sean: build and wire, stop burning runs).
- The adjacent-band guard is UNTESTED against a real slanted beam or a real
  thin rung close beside dense chord ink — the six crops are all clear
  negatives, not a discriminating pair.
- `LEDGER_RUNG_INK_DENSE` / `_ADJACENT_MAX` / `_WIDTH_HEAD_MULT` are
  argued, not measured — no crop here confirms a threshold value, only that
  the compound test's overall behaviour (on this sample) matches what a
  human would call "not a rung".
- No GATHER change to `Q.GLYPH_LADDER`'s own anonymous count: `ladder_side`
  and `cv_rungs` are the only readers of the merged pool; a fixture or an
  old record with no page geometry still falls back to `ladder_side_from_
  count`, which CV cannot reach (unchanged, by design).
- `staged.check` TOTAL is 252, not ≤249 — see the RED→GREEN section above
  for the accounting; every point of the increase is inside an existing,
  already-tolerated `wiring` bucket, and none of `inventory`/`capture`/
  `gather_coverage`/`reach` moved from their 2.6c.2 counts. → **CLOSED,
  §2.6d.2 below: `_observe_ledger_rung_ink`'s `g` is now RECONSTRUCTED via
  `R.glyph(...)` at the top of the function (the same convention every
  other resolved GATHER site already uses) rather than accepted as an
  opaque parameter, so `wiring._SubjectKinds`'s constructor-expression
  resolver sees it. `staged.check` is back to 249, main's own number, with
  0 unaccounted.**

## §2.6d.2 — calibration on a POSITIVE case, and two real bugs (2026-09-29, manager follow-up, BUILT not merged)

Manager, on the first landing: *"found=True fired on ZERO windows, so the
arm is DEAD at zero on the pages tried"* (CLAUDE.md rule 5) — calibrate on a
positive case before merging. §2.6d's own two acceptance-set pages (pdf idx
1 and 3) turn out not to hold one; the fix is elsewhere.

### The eight §2.6c.2 crops, read by eye

All eight (`out/print/2.6c-far-{litolff,breitkopf}-0{1..4}.png`) were opened
and looked at directly, then a wide, unbanded re-render of each head's own
neighbourhood (not bounded to the recorded candidate staves, so nothing a
tight crop could hide) checked for a rung the banded crop's margin might
have cut off. **Six of eight show no ledger line of any kind** — isolated
noteheads in open space (litolff 01-04, breitkopf 01), or (breitkopf 04) a
detector false positive at a system's opening barline, no note there at
all. **Breitkopf 03** (`glyph/22/1/6/10/2`, pdf idx 22, toward
`staff/22/1/6`) is the one unambiguous positive: a notehead with a printed
ledger line visibly crossing it, wings poking out both sides.

### The miss, measured, and the fix

A one-page re-gather of pdf idx 22 measured this exact head:

| step | want_y (page) | centre | left | right | adjacent | found (before) |
|---|--:|--:|--:|--:|--:|---|
| 1 (nearer staff) | 5935.25 | 0.682 | 0.633 | 0.739 | 0.400 | False |
| 2 (the visible rung) | 5962.5 | 0.982 | **0.513** | 0.663 | 0.313 | **False** |

Step 2 fails ONLY on `left` (0.513 against the 0.55 `DENSE` floor) — the
overhang test averaged density over the WHOLE context window out to
`head_w * 0.375`, and this rung's left wing is shorter than that span, so
blank paper beyond it diluted the reading. **Fix**: a NARROWER overhang
band, anchored right at the head's edge (`LEDGER_RUNG_INK_OVERHANG_TEST_
FRAC = 0.20`, distinct from the wider context span `LEDGER_RUNG_INK_
OVERHANG_HEAD_FRAC` still used for the adjacent/background bands). Re-
measured: `left = 0.648`, `found = True`. Step 1 stays `False` (adjacent
0.400, unchanged) — an OPEN finding below, not fixed.

**A real bug the fix's own re-run found**: with the overhang narrowed,
`found=True` jumped from 0 to **40 of 712** rows on this one page — and two
of the forty (`glyph/22/0/7/4/9`, `glyph/22/0/6/4/2`, both `staff/22/0/7`
step 4) are a SLANTED BEAM crossing two heads, not a rung (`out/print/
2.6d-cv-brk22-calibration-beam-rejected.png`): the `ADJACENT` guard tests a
FIXED x-range one thickness-band up and down, and a sloped stroke's ink
moves out of that fixed range, so the guard that catches a thick blob does
not catch a thin one lying at an angle. **Second fix**: a LEVEL guard —
the ink-weighted row centroid of the LEFT band and of the RIGHT band must
not differ by more than `LEDGER_RUNG_INK_SLANT_MAX_HALF_H` (0.2) times the
tested band's own half-height, or the "horizontal" run is rising/falling
across the head. Measured on the two data points this lane has: the real
rung's centroids differ by 1.0 px (slant reads `1.003`), the beam's by
11.3-12.1 px — first tried at 0.6 (too loose, both beam rows still passed
at 11.3-12.1 against a half-height of ~26.7, i.e. ~0.42-0.45), retuned to
0.2 (four times the real rung's own slant, well under half the beam's).
**Re-measured a third time: 38 of 712 `found=True`, the beam pair gone, the
real rung (`slant=1.003`) and a second confirmed real rung found by the
same pass (`glyph/22/1/3/7/2`, a half note, `out/print/2.6d-cv-brk22-
calibration-spot1-real.png`) both still credited.** `far_no_rungs` on this
page: 10 (base) → 6 (arm) — the first REAL, non-zero, reach-confirmed
improvement this roadmap item has produced.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: both new
constants are tuned against exactly ONE real rung and ONE real beam — see
each constant's own header comment in `gather.py` for the falsifying case.

### The wiring fix

`staged.check`'s `wiring` bucket went 249→252 at the first landing because
`_observe_ledger_rung_ink` accepted its subject `g` as an opaque parameter;
`wiring._SubjectKinds` resolves a subject's Kind from the CONSTRUCTOR
EXPRESSION at the call site (`R.glyph(...)`), never from a parameter, and
every OTHER gather site in the file already reconstructs its own `g` this
way rather than passing one through (`gather.py:518,658,1244` etc. — the
convention was already there, `_observe_ledger_rung_ink` just did not
follow it). One line, `g = R.glyph(g.page, g.system, g.staff, g.cell,
g.glyph)`, at the top of the function: `staged.check` back to 249.

### A REAL positive fixture (`tools/omr/tests/test_staged_ledger_rung_ink.
py`, `TestARealPrintedRung`)

`ledger_rung_ink_brk_p22_real.png` is not redrawn or re-rendered — it is
the EXACT canonical raster `_observe_ledger_rung_ink` sampled for this one
(glyph, candidate) pair on the real re-gather, dumped from inside the
function (a temporary debug hook, removed before commit) and cropped with
margin around the two tested steps. Three tests: the real rung IS found;
the SAME ink tested against the pre-fix wider overhang span reproduces the
miss (proving the fixture can tell the two thresholds apart, not only pass
regardless); step 1 still misses it (pinned, so a future adjacent-guard fix
shows up here first).

### Not done / open (2.6d.2)

- **Step 1's adjacent-guard miss is NOT fixed.** It sits close enough to
  the staff that the guard's "one band further up" reads dense — plausibly
  the staff's own ink (imperfectly erased) or simple proximity, not
  measured to a cause. `test_step_1_still_misses_it_the_adjacent_guard_
  open_finding` pins the current (wrong) behaviour so a fix shows up as a
  test needing an update, not a silent change.
- **The "own line" exclusion can still swallow a single-ledger note's only
  evidence.** Even with step 2 now `found=True`, `glyph_owner` for THIS
  head still abstains `far_no_rungs` on the real re-gather: the credited
  step sits within `OWN_LINE_MAX_SPACES` of the head's own centre (the note
  stands ON its ledger, which is what a note standing on its ONLY rung
  looks like), so `ladder_side` classifies it as the head's own line and
  excludes it from `n_toward` — leaving zero TOWARD evidence for a note
  that in fact has a rung. This is `ownership.py`'s pre-existing, SHARED
  design (2.6c.2, unchanged here) and affects the detector-boxed reader
  identically; not a 2.6d defect, and not fixed in this pass — flagged for
  whoever picks up the own-line rule next.
- Both new constants are tuned against one real rung and one real beam,
  not swept. A slanted beam at a shallower angle, or a real rung on a
  wandering/skewed staff, could sit on either side of either threshold.
- The remaining calibration pages (Litolff pdf idx 5, 6; the second half of
  Breitkopf's own p22 population) were read for reach only, not exhaustively
  cross-checked crop by crop; Litolff pdf idx 6 (`lit-02`, `lit-04`) did not
  complete in this pass — a shared Surya worker session stalled for 900 s
  mid-gather despite `--no-surya` and the run was killed rather than
  re-tried a third time (CLAUDE.md §5b: the resident server is shared with
  other sessions; not a `tools/` defect this lane introduced).

## §2.6d.3 — the manager's pre-merge check: because `ledger_direction` is a HARD gate, one false CV rung decides a staff outright (2026-09-29)

`ledger_direction` returns BEFORE any additive weight is summed (2.6c.2),
so a wrongly-credited `Q.LEDGER_RUNG_INK` row does not merely nudge a
score — it decides the contest outright. Before merging: list EVERY
`glyph_owner` / `belongs_to_a_nearer_staff` verdict that changes base
(no CV reader) → arm (this tree) on the one page with real data (Breitkopf
pdf idx 22), plus a random sample of the `found=True` rows that changed
nothing, and look at every one.

**Method, no re-gather beyond the one page already needed to reconstitute
the record this session's own cleanup had deleted**: `verify_cv_rungs_
2_6d.py` replays a saved record's own GATHER rows twice via `review.rerun.
rebuild_gather` — once as-is (ARM) and once with every `ledger_rung_ink`
row stripped before the replay (BASE, i.e. no CV reader at all) — injects
the same saved `ledger_is_not_a_ledger`/`instrument`/`clef` verdicts into
both, and re-decides `glyph_owner` (every contest) and `notehead_is_not_a_
notehead` (every head with a nearer-staff signal) on each. A pure ADJUDICATE
comparison; the GATHER measurement itself is unchanged from §2.6d.2's final
state (38 of 712 `found=True`).

**Result: `glyph_owner` changed on 2 of the page's contests; `belongs_to_a_
nearer_staff` changed on 0.** Both changed contests kept the SAME winner
(`staff/22/0/7`) — the reason moved from `hairpin_separates` to `ledger_
direction`, so the CV rung reinforced an answer the hairpin term already
gave rather than flipping one. `crop_cv_rung_2_6d.py` gained `--subjects`
(an explicit `subject:candidate:step` list, for exactly this check) and cut
12 banded crops: the 2 changed contests plus a random 10 of the 36 `found=
True` rows that changed nothing (`--seed 2026092901`).

**Read by eye, all 12: a printed ledger line is there.** Ten are
unambiguous — a rung with wings poking into open paper on both sides of the
head. Two (crops 09, 11) are dense chords where the wing touches a
neighbouring note's own ink before reaching open paper — still the SAME
printed ledger, on the convention CLAUDE.md §10 already states (several
notes of a chord stand on one ledger); not a stem, not a beam, not a
barline. **0 of 12 false.** Nothing to tighten; the two verdicts the CV
reader changed are both backed by real ink, and the sampled unchanged
credits are real too, so the 38-of-712 population this page produced is
not, on this sample, hiding a false positive that the HARD gate would have
acted on.

Crops committed as `out/print/2.6d-changed-{01..12}.png` +
`2.6d-changed-manifest.json` (`VERDICT_none_yet: null` per crop, for Sean;
`session_read_2026_09_29` carries this session's own read, kept separate
from his verdict slot). ⚠️ Sample size: 12 of 38 credited rows on ONE page
of ONE document — a clean result here is not a swept threshold, and the
open items in §2.6d.2 (step 1's adjacent-guard miss, the own-line
exclusion, untested slant/adjacent edge cases) all still stand.

## §2.6e — `tied` (and `no_evidence`) were falling through to a WRITTEN guess, exactly the `far_no_rungs` shape 2.6c fixed (2026-09-29, BUILT not merged)

Branch `claude/owner-tied-2.6e`. Answers §2.6c.2's open item, quoted there
verbatim: *"`tied` is deliberately NOT here [in `OWNER_NOT_READ_REASONS`] --
it predates this lane and its export behaviour is FINDINGS §2.6c.2's open
item."* Cheap proof only (Sean, 2026-09-28: *"build and wire, stop burning
runs on proof"*): unit tests RED→GREEN, one saved-record read, one
in-process base-vs-arm export. No re-gathers.

### The bug

`adjudicate_glyph_owner` (`ownership.py`) abstains `tied` where two
candidates score exactly equal (*"two equal-cost mappings that disagree
carry literally zero information"*) and `no_evidence` where a contest's
`Q.GLYPH_BAND_DISTANCE` rows all lack a `candidate` key (`if not scored`).
`_place_notes` (`export.py`) reads the owner verdict with `rec.value(...)`,
which returns `None` for ANY non-`decided` outcome, and
`A.is_relocated_copy(sub, None)` is `False` by construction (it requires a
`str` owner value) -- so before this change an abstained owner of ANY
reason not in `OWNER_NOT_READ_REASONS` fell straight through to being
WRITTEN on the staff its cell was cut from. `far_no_rungs` was closed
2026-09-28 (§2.6c.2); `tied` and `no_evidence` were not.

`tied` is the WORSE shape, not a milder version of the same one. A contest
exists because a piece of ink is detected TWICE -- once from each staff's
own cell (CLAUDE.md §10: the measure cell's padding reaches the neighbour's
ink on a conductor's page) -- so a `tied` verdict is filed on BOTH of a
contest's two subjects independently, symmetrically, by the same scoring.
Before this fix BOTH subjects fell through the SAME guess and BOTH were
written: not one wrong guess but the same printed note on two staves at
once, on one stem-and-pitch each -- the exact failure `A.is_relocated_copy`'s
own docstring exists to prevent (*"2 of the same note next to each other
connected to the same stem"*), reopened for exactly the population `tied`
names.

### Measured on the real record

One read, `record_io.load_record` on the acceptance manifest's own Litolff
record (`library/_shared-records/beethoven5-litolff-mvt1-whole-20260928.
record.json`, the file `benchmarks/acceptance/manifest.json` names for
`beethoven5-litolff`):

| `glyph_owner` outcome | reason | count |
|---|---|---|
| decided | (various) | 7,879 |
| abstained | `tied` | 101 |
| abstained | `no_evidence` | 0 |

Every abstention on this record is `tied`; `no_evidence` never fires here
(its precondition -- every row of a contest missing `detail["candidate"]`
-- did not occur on this document). It is fixed anyway: it is reachable by
construction (any future gather that leaves `candidate` unset on a
contest's rows hits it), the fall-through it feeds is the byte-identical
code path `tied` was just closed on, and CLAUDE.md rule 8 draws no
exception for "rare."

Of the 101 real `tied` subjects, read against the export report (below),
only a handful ever reach the `glyph_owner` branch of `_place_notes` at all
-- most are already excluded earlier in the function by an unrelated
refusal (`no_pitch`, `duration_narrowed`, a notehead-precision filter) that
this lane does not touch. This is the same shape §2.6c.2 measured for
`far_no_rungs` and is not a new finding, restated here only because it is
the reason the base/arm delta below is small relative to 101.

### What was built

One line, `ownership.OWNER_NOT_READ_REASONS = ("far_no_rungs", "tied",
"no_evidence")` (previously `("far_no_rungs",)`). `export.py`'s
`_OWNER_NOT_READ_REASONS = _ownership_rules.OWNER_NOT_READ_REASONS` and the
`_drop("owner_not_read", s)` call site it feeds are UNTOUCHED -- both new
reasons are absorbed by the exact mechanism 2.6c.2 built, which is why this
is a one-line CONNECT (CLAUDE.md rule 6) and not a new mechanism. The
comment above the tuple is rewritten to record why `tied`/`no_evidence` are
now included instead of explaining why they were not.

`Ruling.abstain("tied")`/`Ruling.abstain("no_evidence")` themselves are
untouched -- the DECISION was already correct (CLAUDE.md rule 8: abstaining
on a genuine tie is right); only the EXPORT behaviour after an abstention
was wrong.

### Tests, RED→GREEN (`tools/omr/tests/test_staged_ledger_direction.py`,
`TestExportCountsAnUnreadOwner`)

Run RED first against `ae776515` (this lane's base): `test_an_abstained_
tied_owner_is_counted_not_written`, `test_a_tied_contests_BOTH_sides_are_
dropped_not_both_written` and `test_an_abstained_no_evidence_owner_is_
counted_not_written` all fail there (the abstained owner is written
anyway, `owner_not_read` never appears in `notes_not_written`). Positive
controls, passing on both trees: a `decided` `ledger_direction` owner (own
staff) is still written once; a `no_contest` head (nothing to arbitrate) is
unaffected. GREEN on this branch, 22/22 in the file.

### Base vs arm, in-process, on the real Litolff record (no re-gather)

`SX._OWNER_NOT_READ_REASONS` monkey-patched to the BASE tuple
(`("far_no_rungs",)`) and to the ARM tuple (this branch's three), the
already-loaded record `to_musicxml`'d once each (export alone, no gather;
~18s/run on the whole movement):

| | BASE (pre-2.6e) | ARM (2.6e) | delta |
|---|---|---|---|
| `written.notes` | 3,867 | 3,866 | −1 |
| `notes_not_written["owner_not_read"]` | (absent, 0) | 8 | +8 |
| `notes_not_written["bar_does_not_add_up"]` | 5,161 | 5,154 | −7 |
| `notes_not_written_total` | 9,304 | 9,305 | +1 |
| `written.notes + notes_not_written_total` | 13,171 | 13,171 | 0 (balanced, both trees) |
| `status_census["unaccounted"]` | 0 | 0 | unchanged |

The equality holds on both trees (rule 9's accounting control: every
gathered notehead is written or counted). The distribution of the +1 is
explained, not merely balanced: of the 8 subjects newly refused
`owner_not_read`, 7 were previously miscounted downstream as
`bar_does_not_add_up` (a bar whose sum the guessed duplicate had thrown
off) and only 1 was actually being WRITTEN in BASE -- so removing 8 guesses
fixes 7 bars' arithmetic and drops 1 real duplicate write, net −1 notes
written. `owned_by_another_staff` (1,122) is unchanged on both trees, as
expected -- that refusal fires on a `decided` owner naming another staff
and this lane touches only abstentions.

The accidental census (`_accidental_census`, ROADMAP 2.7) needs no code
change: `unowned` is computed as a REMAINDER
(`heads_owned - heads_contradicted - (applied - doubled_copies)`) against
the render's own `applied` counter, not by enumerating refusal reasons, so
a head an `accidental_owner` verdict decided but whose note `_place_notes`
now refuses under `owner_not_read` (instead of writing it at a guess)
already lands in `unowned` by the same arithmetic that covered
`far_no_rungs` in 2.6c.2 -- verified by inspection, not by a new test, since
the mechanism is unchanged and already exercised.

### Engraved control

`benchmarks/omr-staged-engraved-2026-09/out/engraved-p0.record.json`: **0
`glyph_owner` abstentions of any reason** (22 `distance` + 4 `range_veto`,
both `decided`). Base and arm exports are **byte-identical** (`xml_base ==
xml_arm`, 73 notes written on both, `notes_not_written == {}` on both) --
this lane cannot touch a document with no contested ink, and does not.

### Proof budget spent

Unit tests (RED→GREEN, 2 positive controls), one `record_io.load_record`
read, one in-process base/arm export pair on the real record, one
byte-identical check on the engraved control. No re-gather, no whole-work
run, no new flag, no new benchmark directory, no new derived check --
`OWNER_NOT_READ_REASONS` already existed and this widens its tuple by two
strings the mechanism it feeds was already built to consume.

## §2.6c.3 — the 18 Breitkopf reversals §2.6c.2 left unadjudicated: 9 contests, all 9 look wrong (evidence lane, no pipeline change, 2026-09-29)

**Path: STAGED.** §2.6c.2 closed listing, as open, "the Breitkopf 14
`ledger_direction` → other staff and 4 → `range_veto` reversals (count-only
ledger on base vs geometric today) are unadjudicated." Because
`ledger_direction` is a HARD GATE (returns before any additive weight is
summed), a wrongly-credited rung does not nudge a contest, it DECIDES the
staff outright — exactly the failure mode §2.6d.3's pre-merge check looked
for on a different page and found clean (0 of 12 false). This is that same
check, run on the 18 subjects FINDINGS itself flagged as unlooked-at.

### Method (no gather, one record read)

The saved 27b arm Breitkopf record (`.../27b/arm/brahms-arm.record.json`,
DPI 600, PDF `library/editions/brahms/symphony-1-op68/brahms--symphony-1-
op68--breitkopf-hartel-brahms--imslp317803.pdf`) re-decided twice on the
SAME record (CLAUDE.md §6b): once from an extracted `8100c9ff` tree (BASE,
`ledger_direction` still §2.6c's first-half ADDITIVE +8.0 term) and once
from today's main `721a8754` (ARM — the hard gate, plus §2.6d's CV rungs,
inert on this pre-2.6d record, and §2.6e), both via
`readjudicate_owner_2_6c.py --dump`, diffed subject-by-subject
(`diff_base_arm_2_6c.py`) — reproduced the committed
`out/2.6c-base-vs-arm-breitkopf.json` counts exactly (14 + 4). The 18
subjects are **9 contests, not 18 notes**: a contest files its verdict on
BOTH of its two candidate-staff subjects (CLAUDE.md §10, the padded cell
reaches the neighbour's ink), and every pair here carries the identical
winner. `crop_reversals_2_6c3.py` (new, this lane) re-adjudicates
`glyph_owner` on ARM once more in-process to pull the LIVE `ledger` detail
(credited rungs, their source, the excluded own-line rung) and cuts one
banded crop per contest — GREEN = ARM's (today's) winner, BLUE = the other
candidate (BASE's winner, in all 9) — with every rung `ledger_direction`
counted `toward` a side boxed MAGENTA and labelled by source, and the
excluded own-line rung boxed dashed GREY. Frame control (`_frame_ok`,
reused): 9 attempted, 9 passed, 0 refused.

### Read by eye, all 9: BASE was right, ARM flips to the WRONG staff — twice over

Full readings: `out/print/2.6c-reversal-session-read-2026-09-29.json`
(this session's own verdicts, kept separate from the manifest Sean
annotates, precedent §2.6d.3's `session_read_2026_09_29`). Summary:

| # | subjects | BASE (right) | ARM (wrong) | mechanism |
|---|---|---|---|---|
| 1 | `glyph/10/1/0/1/1` / `.../1/1/1/7` | staff/10/1/1 | staff/10/1/0 | false credited rung |
| 2 | `glyph/10/1/0/2/8` / `.../1/1/2/1` | staff/10/1/1 | staff/10/1/0 | false credited rung |
| 3 | `glyph/16/0/0/6/5` / `.../0/1/6/7` | staff/16/0/1 | staff/16/0/0 | false credited rung |
| 4 | `glyph/16/0/0/7/4` / `.../0/1/7/11` | staff/16/0/1 | staff/16/0/0 | false credited rung |
| 5 | `glyph/18/0/0/3/6` / `.../0/1/3/7` | staff/18/0/1 | staff/18/0/0 | false credited rung |
| 6 | `glyph/18/0/0/4/13` / `.../0/1/4/10` | staff/18/0/1 | staff/18/0/0 | false credited rung |
| 7 | `glyph/5/1/12/0/10` / `.../1/13/0/8` | staff/5/1/12 | staff/5/1/13 | false credited rung |
| 8 | `glyph/18/1/4/3/2` / `.../1/5/3/2` | staff/18/1/5 | staff/18/1/4 | `range_veto` override |
| 9 | `glyph/4/1/4/5/0` / `.../1/5/5/1` | staff/4/1/5 | staff/4/1/4 | `range_veto` override |

**9 of 9: BASE right, ARM wrong.** Two distinct mechanisms, cleanly
separated by which rows carry a `sources` entry:

- **#1-7 (the 14 `ledger_direction`→`ledger_direction` subjects, 7
  contests): the credited rung is not a second printed ledger line — it
  is the SAME notehead's own ink, boxed twice.** Every one of the 7 shows
  the identical signature: the note sits 0.01–0.09 spaces past its TRUE
  staff's outer line (`reach_spaces`), i.e. exactly on that staff's own
  first ledger — the single most common far-note shape in this corpus —
  and the far, wrong staff's one `toward` rung sits within about one
  notehead-height of that same position. Overlaying the credited box's
  exact bbox on an UN-annotated render of the same page region (bypassing
  every crop overlay) shows, in all 7, ONE notehead only: the detector
  drew a `ledgerLine` box near its centre (correctly read as `stands_on`,
  the note's own line, excluded by `OWN_LINE_MAX_SPACES`) AND a second one
  at its far rim (top if the note sits above its staff, bottom if below),
  which lands just past that exclusion radius and is counted `toward` the
  OTHER candidate. `ladder_side`'s x-overlap/one-rung-per-step walk has no
  test for "this step's rung is inside the head's own bounding box" — only
  a distance-from-head-y test — so a notehead double-boxed at both rims
  (measured nowhere yet; not counted across the whole record here) can
  manufacture its own second rung and hand the contest to the wrong
  staff, exactly because `ledger_direction` returns before anything else
  is weighed.
- **#8-9 (the 4 `ledger_direction`→`range_veto` subjects, 2 contests):
  ledger_direction is NOT at fault.** Both correctly go SILENT (`toward=0`
  on BOTH sides, so no magenta box exists on either crop). On #8 the far
  staff has literally no rung anywhere (`found=0`, `missing=2`,
  `reach=false`, 2.7 spaces away); on #9 the far staff DOES have a found
  rung, but it is the SAME shared own-line rung both sides' `stands_on`
  points at — essentially sitting on the head itself (`reach_spaces`
  0.03), not a second, independent rung further out — so it correctly
  earns no `toward` credit either. What flips both contests is the
  additive `range_veto` term, which vetoes the NEAR staff (0.03–0.09
  spaces past its own edge — the same first-ledger shape as #1-7 — tied
  in from and out to same-staff neighbours on the wider raw render checked
  in this session but not committed) in favour of a staff roughly twice
  as far (2.7 sp on #8, 2.0 sp on #9) with no independent ink supporting
  it there.

⚠️⚠️ **Because `ledger_direction` is a HARD gate, this is not "7 notes
moved" — it is 7 concrete instances of the exact risk §2.6d.3 checked for
on a different page and cleared.** That check's 0-of-12 clean result does
not generalize: it sampled ONE page's `Q.LEDGER_RUNG_INK` (CV) credits,
never the detector-sourced credits this lane's 7 all are, and the failure
mode here (a note's own rim double-boxed) is a GATHER/detector-recall
shape entirely outside what a CV-ink calibration pass would ever see.

### Not done / open

- No count of how many notes on the whole Breitkopf record show a
  notehead double-boxed at both rims as `ledgerLine` — this lane read 7
  crops, not the population. The next lever this points at (not built
  here, no pipeline code touched): `ladder_side` should refuse a rung
  whose y falls within the head's own bbox span (or within one
  notehead-height of the already-excluded own-line rung) as a step
  `toward` ANY candidate, regardless of which side of
  `OWN_LINE_MAX_SPACES` it lands on.
- The `range_veto` term's written-range table was not inspected for #8/#9
  — only the geometry and the surrounding print were checked. Rule 7 (a
  control must be able to fail) suggests checking whether this veto has
  EVER been right on a note this close to its own staff, not only
  whether it fires; not done here.
- Litolff was not re-run: FINDINGS §2.6c.2's base-vs-arm table shows 0
  `ledger_direction`-reason value changes on Litolff (all 33 winner
  changes there are `distance`/`ladder` → `ledger_direction`, one
  direction only), so this shape may be Breitkopf-specific or may simply
  not have been sampled there — not measured.
- Crops, manifest (`VERDICT_none_yet: null` per crop, question "UPPER /
  LOWER / not a note -- and are the drawn (MAGENTA) ledger lines real,
  reaching this head from the staff they are credited toward?") and this
  session's own reading committed under
  `benchmarks/omr-owner-domain-2026-09/out/print/2.6c-reversal-*` and
  `crop_reversals_2_6c3.py`, on `claude/owner-reversals-2.6c`, NOT merged
  (evidence lane, no pipeline code changed).

## §2.6f — a rung that is another candidate's own ledger structure never counts toward a farther one (2026-09-29, BUILT not merged)

Branch `claude/own-rim-rung-2.6f`, off `origin/main` (`42cb4792`, §2.6c.3's
own merge). **Path: STAGED** (`adjudicators/ownership.py`,
`adjudicators/notehead_precision.py`). Sean, via §2.6c.2/§2.6c.3: *"if a
ledger answer disagrees with the print, the RUNG FINDING is wrong, not the
rule."* §2.6c.3 read all nine Breitkopf reversals by eye and found 9 of 9
wrong; this lane fixes the mechanism behind seven of them (the two
`range_veto` reversals are additive, untouched, and recorded only).

### The mechanism, precisely (not "the same notehead's own ink" — corrected)

§2.6c.3's own read called the false credit "the same notehead's own ink,
double-boxed at its far rim." Re-examining the geometry for this lane (every
credited rung's exact bbox, plus every OTHER notehead-classified `Q.GLYPH_
BOX` filed in the same cell) found a more precise mechanism, matching
§2.7b's own docstring for its prior two instances (#4/#22, 2026-09-28): a
SEPARATE, real notehead (a chord-mate, or a later note the same stem
serves) stands one space further from the note's own staff, and THAT
note's own ledger is what the far candidate's longer walk picks up.
Contest #1 (`glyph/10/1/0/1/1`): `glyph/10/1/1/1/2`, a second `notehead`
box in the SAME cell, centres at y=4027.75 — 1.1 px from the credited
rung's centre (4026.86) and 1.06 spaces from the contested note's own line
(4056.1) — a chord a third or so above, sharing staff/10/1/1's second
ledger. Whether the intervening mark is a chord-mate's ledger or (as
contest #7's raw render shows, a stem passing through two short ledger
dashes before the staff) some other same-staff structure does not change
the fix: either way the rung is the NEAR candidate's, reachable from its
own already-found own-line by an integer number of its own spaces, not the
far candidate's.

### What was built

1. **`LadderSide` carries `spacing` and `anchor_y`** (the own-line's own Y,
   renamed from an initial `own_y` — see the wiring false-positive below)
   **and `toward_ys`** (`(rung key, Y)` for every non-own `toward` rung),
   populated in `ladder_side` from data it already computes locally. A new
   `discounted` field records what a second walk excluded, for `trace`.
2. **`_shared_own_structure_exclusions(sides)`**: for every side `s` with
   `s.missing >= 1`, for every `(key, y)` in `s.toward_ys`, checks every
   OTHER side `other` (`other.staff != s.staff`, `other.anchor_y` set):
   `steps = abs(y - other.anchor_y) / other.spacing`; if that is within
   `OWN_STRUCTURE_TOLERANCE_SPACES` of a positive integer, `key` is
   excluded from `s`. Never compares a side against its own `anchor_y` (a
   candidate genuinely needing two rungs for THIS note keeps both) and
   never fires on an already-COMPLETE side (`missing >= 1` required first
   — the guard the falsifying case below forced in).
3. **`ladder_sides_with_discount(specs)`**: builds every side once
   (`ladder_side(*spec)`), computes the exclusion sets, and for any side
   with something excluded, re-walks it (`ladder_side(*spec,
   excluded_keys=...)`) with the excluded key AND every physical duplicate
   of it (the same dedup radius `ladder_side` itself uses for a rung boxed
   in two cells, CLAUDE.md §10) removed from the pool entirely — a full
   re-walk, so `missing`/`reach`/`reach_spaces` all recompute honestly.
   `glyph_owner` (`_contest_ledger_reading`) and 2.7b's
   `belongs_to_a_nearer_staff` both call this instead of `ladder_side`
   directly, so the two decisions cannot discount a rung differently — the
   SAME property 2.6c itself was built to hold (ONE helper, ROADMAP
   2.6c/§4c).
4. **`OWN_STRUCTURE_TOLERANCE_SPACES = 0.2`**, CONVENTION ASSUMED / WHAT
   WOULD FALSIFY IT header in `ownership.py`: measured against the SAME
   rung, the near candidate's own-line-anchored residual is 0.003–0.111
   spaces (mean 0.041) on the seven §2.6c.3 contests; the far candidate's
   own edge-anchored residual for the identical box is 0.015–0.39 spaces —
   tightening `RUNG_GRID_TOLERANCE_SPACES` (0.5) to catch #1/#2 (0.36/0.39)
   would also refuse real far-note ladders elsewhere (2.6c.2's own fixture
   reaches to 0.42). 0.2 sits roughly double the worst of the seven and
   comfortably inside the loosest false match.

### The falsifying case, found and repaired before merge (not a hypothetical)

Running the existing `test_staged_ledger_direction.py`/`test_staged_nearer_
staff.py` (47 tests, the six 2.7b.8 heads + hard-gate pin) against the
first cut of this fix: **2 failed.** Litolff #14 (`glyph/12/0/11/14/1`,
Sean's G, the FILED staff) — a genuine, COMPLETE 3-of-3 ladder from
staff/12/0/11 — was wrongly discounted, because its own outermost rung
sits 0.08 PIXELS from staff/12/0/10's own-line (two staves' grids are that
close together on this page). Without a guard, the fix would have broken
exactly the shape it exists to protect. **The repair**: `_shared_own_
structure_exclusions` never fires on a side that is already `missing == 0`
complete. Every one of the seven contests this lane fixes has `missing ==
1` at the point of discount, so the guard costs the fix nothing — verified
by re-running the full base-vs-arm comparison below AFTER the guard was
added, not before.

### RED → GREEN

`tools/omr/tests/test_staged_shared_structure_2_6f.py` (new file, 6 tests):
`extract_shared_structure_fixture_2_6f.py` cuts one head per contest from
the Breitkopf 27b arm record (`shared_structure_2_6f.json`, following
`extract_ledger_fixture_2_6c.py`'s exact shape) for the seven real-contest
tests, plus four synthetic boundary tests exercising
`_shared_own_structure_exclusions`/`ladder_sides_with_discount` directly:
the measured shape discounted, the Litolff #14 shape (synthetic, real
numbers) NOT discounted, a single-side genuine second ledger NOT
discounted (the manager's positive control, literally), and a physical
duplicate of a discounted rung ALSO excluded. RED verified by checking out
`42cb4792`'s `ownership.py`/`notehead_precision.py` into the working tree
(`git checkout 42cb4792 -- <2 files>`, restored via `git checkout HEAD --
<2 files>` — no bare `git stash`, current work committed first): all 6 new
tests fail (`ladder_sides_with_discount` does not exist), the existing 47
pass unchanged on both trees. GREEN here: 53/53.

### Re-run of the base-vs-arm comparison, Breitkopf AND Litolff

Same method as §2.6c.3 (`readjudicate_owner_2_6c.py --dump` from an
extracted `8100c9ff` tree and from this branch, over the SAME two 27b arm
records, diffed subject-by-subject).

**Breitkopf** (24,795 `glyph_owner` subjects): the `ledger_direction`→
`ledger_direction` value-changed bucket (14 subjects, §2.6c.3's 7 contests)
is **GONE** — every one reverts to base's winner, reason now `ladder`
(the additive term wins once the false hard-gate credit is removed and the
gate correctly goes silent). The `ledger_direction`→`range_veto` bucket (4
subjects, 2 contests) is **UNCHANGED** — exactly as expected, this fix
touches no additive term. Whole-document diff of this lane's OWN effect
(today's main before vs. after, isolating 2.6f alone): **49 subjects
changed** — 14 as above, 2 keep the SAME winner but relabel `ladder`→
`ledger_direction` (a losing candidate's spurious rung was the only thing
keeping the true winner off the hard gate; winner unchanged, verified), and
**33 newly abstain `far_no_rungs`**. Sampled two of the 33
(`glyph/10/0/7/2/2`/`glyph/10/0/8/2/2`): the identical shape recurring —
both sides now show only their shared own-line (`toward=0` on both, one
side's former "toward" rungs — 7 physical boxes — all discounted as the
other side's own structure) — a reading gap Sean's own convention prefers
over the guess this lane removed, not a lost correct answer.

**Litolff** (6,013 subjects): §2.6c.2 already found ZERO `ledger_direction`
reversal-shape subjects here (all 33 winner changes there are one-
directional, `distance`/`ladder`→`ledger_direction`), and this lane
confirms it stays that way — no NEW reversal shape, no regression. This
lane's own effect (before/after, isolated): **3 subjects changed**, all
newly abstaining `far_no_rungs`, same explained shape, sampled and
confirmed benign.

### A false positive was hit and fixed, not merely noted

The first cut named the own-line field `own_y`. `pytest tools/omr/tests -m
"not slow"` went RED: `staged.wiring --check` reported BROKEN (`DETAIL
Q.GLYPH_BAND_DISTANCE.own`'s `KNOWN_GAPS` entry went STALE). CLAUDE.md
§4d's third blind spot, hit a THIRD time in this exact file (2.6c.2 hit it
on a bare module import, 2.6d on an unresolved GATHER site): `wiring`'s
"who reads a key" scan matches a bare substring, and `other.own_y` contains
the literal text `.own_y`, which contains `.own` — the tool read that as a
consumer of the UNRELATED `Q.GLYPH_BAND_DISTANCE.own` detail key
(`adjudicate_glyph_owner`'s own `own` boolean, a different fact entirely).
Fixed at the name (`own_y` → `anchor_y`), not by touching `KNOWN_GAPS` —
the module's own comment says why: *"a gap list naming a key is not a
consumer of it."* `staged.wiring` returned to `open=67, status=ok`
(identical to `origin/main`); `staged.check` TOTAL **247**, unchanged.

### Gate

Fast tier: **3,707 passed**, 3 skipped (main's 3,701 + this lane's 6 new).
`staged.check` **247**, identical to `origin/main`. No `library/`/
`omr-weights/`/venv path in any new test file (checked by grep before
commit, per the 09-28 CLAUDE.md addition that a machine-local path in a
test file's own TEXT — including a comment — makes the whole file slow).

### Not done / open

- No count of how many notes on the whole Breitkopf record carry a
  notehead whose second-ledger structure could be miscredited this way —
  this lane fixed the seven §2.6c.3 named it and confirmed 33 more of the
  same shape exist, not the total population.
- The two `range_veto` reversals (§2.6c.3 #8/#9) are RECORDED only, per
  the brief — `range_veto`'s own written-range table was not inspected;
  whether it is right to veto a note this close to its own staff's first
  ledger is a separate, unmeasured question.
- `OWN_STRUCTURE_TOLERANCE_SPACES` is argued from seven residuals on ONE
  document (Breitkopf) — NOT CONFIRMED on Litolff (which has none of this
  shape to measure it against) or engraved.
- No print crop for this lane's own fix (an evidence lane, §2.6c.3, already
  put the print in front of Sean for these exact seven contests before
  this code existed); the 33 newly-abstaining Breitkopf subjects and the 3
  Litolff ones were sampled and read from the record's own geometry, not
  cropped against the page.

## §2.6g — the fresh whole-movement Litolff record's 345 `owner_not_read`: breakdown, 16 sampled, read by eye (evidence lane, no pipeline change, 2026-09-29)

**Path: STAGED.** Branch `claude/owner-not-read-2.6g`, off `origin/main`
`23f4fa9e` (§2.6c/2.6d/2.6e/2.6f all merged onto it). The record:
`beethoven5-litolff-whole-movement-20260929T104646Z.record.json` (325 MB),
gathered tonight in the `regather-20260929` worktree — read here ONLY
through `tools.omr.staged.record_io.load_record`, ONCE, in
`benchmarks/omr-owner-domain-2026-09/probe/probe_owner_not_read_2_6g.py`.
That worktree's own files were not touched; a Brahms gather running there
was left alone.

### Method

One `load_record`. In the same process, `export.Record.verdict` was
wrapped (not modified — `export.py` is untouched by this lane) to capture
every subject where the wrapped call returns an `abstained` verdict whose
reason is in `ownership.OWNER_NOT_READ_REASONS` — the EXACT predicate
`export.py:967-976` itself tests before calling `_drop("owner_not_read",
s)` — while `to_musicxml` ran once, in-process, no re-gather. This
reproduced the file's own count exactly: `report["notes_not_written"]
["owner_not_read"] == 345 == len(captured)`.

For each captured subject the probe read, from the SAME loaded record (no
second file read): its own `Q.GLYPH_BAND_DISTANCE` rows (candidate staff +
distance in spaces), its already-decided `Q.GLYPH_OWNER` verdict detail
(the `ledger` summary `_contest_ledger_reading` filed at ADJUDICATE time —
2.6c/2.6e are already IN this gather, so no readjudication was needed to
see reason/detail), and its `Q.LEDGER_RUNG_INK` rows (2.6d's CV reader).

**The twin.** A contest exists because `gather.gather_ownership_evidence`
detects the SAME ink twice — once from each candidate staff's own padded
cell — and files a `Q.GLYPH_BAND_DISTANCE`/`Q.GLYPH_OWNER` subject at EACH
address (`gather.py:858-876`: same category, different staff, same
system, IoU > `CONTEST_IOU` 0.3). The probe replays exactly that predicate
over the record's own `Q.GLYPH_BOX` rows (not approximated, not a
tolerance guessed for this lane) to find, for every captured subject, the
other glyph subject GATHER paired it with, and reads THAT subject's own
`Q.GLYPH_OWNER` verdict.

### The breakdown

345 captured, all reason `far_no_rungs` (0 `tied`, 0 `no_evidence` reach
export on this record — different from the manifest record §2.6e
measured, which held 101 `tied` and 0 `far_no_rungs`; a different, fresher
gather, not a contradiction).

**By rungs needed** (`expected`, the lower of the two candidate sides,
since `far_no_rungs` requires every side to need ≥ `FAR_MIN_RUNGS`): 330 of
345 need exactly **2** (the minimum by construction), 15 need 3. Per side
(690 sides, 2 per subject): `{2: 405, 3: 204, 4: 33, 5: 45, 6: 3}`. **Every
one of these 345 sits right at the boundary the rule itself draws** — none
is a note failing on a distant, obviously-far ladder; all are the
closest-to-the-line cases.

**By distance** (own-staff candidate, half-space bins): `{2.0: 139, 2.5:
64, 3.0: 40, 3.5: 66, 4.0: 3, 4.5: 7, 5.0: 12, 5.5: 14}` spaces from the
band. Far-candidate side is a similar shape, slightly wider.

**By CV reach** (`Q.LEDGER_RUNG_INK`, 2.6d): all 345 subjects have at
least one row (1,797 total, 0 abstained — the raster was available and the
reader ran everywhere); **0 of 1,797 read `found=True`**. This is the SAME
zero §2.6d's own two-acceptance-page sample measured
(`benchmarks/omr-owner-domain-2026-09/FINDINGS.md` §2.6d), now confirmed
over the WHOLE movement's own `far_no_rungs` population, not just two
pages — REACH is real (every window was actually sampled, not abstained
past), ACCURACY on this specific population is exactly zero, on far more
data than before.

**By twin fate** (306 + 32 + 7 = 345, exactly):

| twin fate | count | meaning |
|---|--:|---|
| `twin_also_owner_not_read` | 306 | both copies of the contest abstain; the note is written NOWHERE (153 distinct notes, since a contest's verdict is filed symmetrically on both subjects) |
| `twin_decided_self` | 32 | the twin's OWN verdict is `decided`, naming the twin's own staff — so the note IS written, just not as this copy; the abstention here costs nothing |
| `twin_decided_other` | 7 | the twin's own verdict is `decided` but names a THIRD staff — a three-way contest shape, not inspected further this lane |

### 16 sampled, 14 crops, read by eye

The brief asked to stratify by REASON; on this record that axis has one
value (`far_no_rungs`), so the twin-fate breakdown above substitutes,
proportioned 12 / 3 / 1 (seed `2026092916`). Crops
(`benchmarks/omr-owner-domain-2026-09/probe/crop_owner_not_read_2_6g.py`,
PDF-only, no second record read — the probe also dumped the crop-cutting
geometry, CV windows and nearby detector `ledgerLine` boxes in the SAME
one-read pass): banded like `crop_far_no_rungs_2_6c.py` (GREEN = upper
candidate, ORANGE = lower, colour follows position), PLUS every nearby
detector `ledgerLine` `Q.GLYPH_BOX` drawn as a thin cyan box and every
`Q.LEDGER_RUNG_INK` window this contest tested drawn dashed blue and
labelled with its four densities. Frame control reused from
`crop_losers_2_6b._frame_ok`: **2 of 16 refused** (both staves' own lines
did not clear the shifted-half-space control) — the control failing on
real crops, not merely available to fail (CLAUDE.md rule 7). 14 rendered:
`out/print/2.6g-owner-not-read-{01..14}.png` + manifest (`VERDICT_none_yet:
null` per crop, question "UPPER (green) / LOWER (orange) / not a note --
are there ledger lines either reader should have caught?"). This session's
own read is kept separate
(`out/print/2.6g-owner-not-read-session-read-2026-09-29.json`, precedent
`session_read_2026_09_29` in §2.6d.3/§2.6c.3).

**Tally: (a) 1, (b) 4, (c) 1, (d) 8** (of 14).

- **(c), confirmed**: crop 05 (`glyph/2/0/2/1/7`) — the red bracket sits on
  the `c` of a printed `cresc.`. Not a note. Exactly the shape §2.6c.2
  already named for Litolff's `sempre` (`glyph/8/0/6/12/7`).
- **(a), one candidate**: crop 10 (`glyph/10/0/7/1/2`) — center=0.719
  (dense), right=0.508 (just under the 0.55 `DENSE` floor), adjacent=0.375
  (just OVER the 0.35 ceiling): all three guards miss by a small margin in
  the direction a real, slightly-thick or slightly-off-grid rung would
  push them. The one crop in the sample where a real, missed rung is more
  likely than not.
- **(b), four**: crops 01, 04, 08, 12 — an isolated notehead-shaped blob
  with the LEFT and RIGHT overhang densities reading ≈0.0 at every step
  (truly blank paper on both sides, not merely "not dense enough"); no
  ledger of any kind is visible near the head. Whether these are real
  notes standing alone with nothing printed under them, or something else
  entirely, was not settled by eye.
- **(d), eight**: crops 02, 03, 06, 07, 09, 11, 13, 14 — dense or merged
  passages (beamed runs, chords, slurred groups) where SOME window reads
  one overhang side dense and the other not (e.g. crop 06: left=0.94,
  right=0.16 at the same step) — the recurring one-sided-neighbour-ink
  shape §2.6f/§2.6c.3 already built a rule around for the DETECTOR-boxed
  case, seen here in the CV-ink measurement instead. None reads as a
  clean, symmetric rung reaching past the head on both sides.

**Headline: 0 of 14 crops show an unambiguous printed ledger line that
both readers missed on evidence that was there to find.** The population
sits, by construction, right at the `FAR_MIN_RUNGS` boundary (330 of 345
need exactly 2), which is exactly where the ambiguity in this sample
concentrates — not evidence the boundary is wrong, but evidence this is
where a "did an engraver print one here" judgment call gets hard, on this
edition's own MERGING convention (CLAUDE.md §10).

### Recommendation

**Do not loosen the CV or detector ledger thresholds.** The 2.6d reader
ran everywhere on this population (1,797 windows, 0 abstained) and found
nothing; the 14 read-by-eye crops give exactly one plausible near-miss
(crop 10) and otherwise either confirm the abstention (a non-note, four
genuinely blank-paper isolated heads) or land on ink this lane's own
sibling findings (§2.6f, §2.6c.3) already attribute to a NEIGHBOUR's own
structure, not an independent rung. `far_no_rungs` → `owner_not_read` is
behaving exactly as designed (CLAUDE.md rule 8): abstaining rather than
guessing, on a population that, read by eye, mostly does not contain the
evidence a rung-finding fix could recover.

The higher-yield next step this points at: **measure what fraction of the
345 (or the broader `far_no_rungs` population) is a real, independent
notehead at all**, in the shape of the measurement CLAUDE.md §10 already
cites for this edition (46 of 180 sampled "notehead" boxes on Litolff were
not noteheads) — not a ledger-rung change. If a similar rate holds here,
on the order of 80–90 of the 345 would be better refused earlier, under a
more specific `not_a_notehead:*` reason, than reaching `glyph_owner` and
abstaining `far_no_rungs` at all. This is a detector-precision question on
this population, not a rule question — the rule itself, on this sample,
looks right.

### Not done / open

- The 8 inconclusive (d) crops were not re-cropped at higher zoom or
  checked against a wider, unbanded render (§2.6d.2's own method for
  exactly this kind of doubt) — budget (one record read, no gathers, no
  code) did not extend to a second pass.
- No population-wide notehead-precision count was run on the 345 (or the
  full `far_no_rungs` set) — the recommendation above is argued from 14
  crops, not measured at scale.
- `twin_decided_other` (7 subjects, 1 sampled) was not looked at closely
  as its own shape — a three-way contest is a different question from the
  two-candidate case this lane otherwise reads.
- The 2 frame-control refusals were not replaced with backups (would have
  needed a second record read to pull their geometry; out of budget) —
  reported as refused, not swept into the 14.
- CLAUDE.md §4c's list of EXPORT refusals still does not name
  `owner_not_read` — §2.6c.2 already flagged this as open and it remains
  so; this lane is evidence-only and changed no spec text either.

## 2.27 — ink in the cell pad that the neighbour staff owns is not this staff's (2026-09-29)

PATH: STAGED. Branch `claude/pad-ink-2.27`, off `origin/main` `2fb92b6f`.
Question from 2.22 (`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md`
§17c, the unmodelled crops) and 2.25 (`benchmarks/omr-missing-notes-2026-09/
FINDINGS.md` §13, `other_staff_via_pad` the largest single stroke source at
150/555 Brahms heads): the measure cell is padded 4-6 staff spaces (CLAUDE.md
§10) and on a conductor's page that reaches the next staff's ink, so a
cell's own `Q.GLYPH_BOX` rows can include a notehead or rest that is really
the NEIGHBOUR staff's. `glyph_owner` already asks "whose is this" for
exactly that population and files a DECIDED verdict — the question here is
which consumers read it, per CLAUDE.md's "value existed and nothing read
it" class (2.3), and which glyphs never reach a contest at all.

**Per Sean's 2026-09-29 process decision (relayed): conceptual wiring
proved by MICROSCOPIC tests only.** No gathers, no record-scale
re-adjudications, no crop batches, no pricing runs — everything below is
read from the tree and proved with hand-built `Log` fixtures.

### The map: family × consumer × does it read `Q.GLYPH_OWNER`

Built by reading `gather.py::gather_ownership_evidence` (contest
formation), `adjudicators/ownership.py` (every `wants=` tuple), and
`grep -rn GLYPH_OWNER tools/omr/staged` for every other adjudicator.

**(a) Contest formation itself** (`gather.py:862-876`): a contest is filed
on a glyph's OWN subject only where the SAME category of ink is
independently detected in BOTH cells (`di.category == dj.category` and
`IoU > 0.3`, ROADMAP 2.6). A glyph that leaked into this cell's pad but
whose ink the neighbour's OWN cell scan never independently re-detected
gets no twin, hence no `Q.GLYPH_BAND_DISTANCE` row, hence NO `Q.GLYPH_OWNER`
verdict at all — `owner is None` and every reader below falls through to
"mine". **This is item (a) and it is NOT addressed here**: fixing it needs
either a GATHER-side change (no gathers this pass) or deciding ownership
from pad position alone, which CLAUDE.md forbids outright (nearness is a
hint, never a decision — Sean 2026-09-28).

**(b) Categories that reach a contest.** `_class_name_to_category`
(`yolo_detector.py`) puts `beam`, `staff`, `tie`, `slur`, `augmentationDot`,
`brace`, `coda`, `segno`, `repeatdot`, `tuplet*`, `tupletbracket` and
`ottavabracket` in ONE category, `"structural"` — so the twin test at (a)
would let an augmentation dot in one cell contest against a ledger line (or
a beam, or a slur) detected in the neighbour's cell, if their boxes happen
to overlap past 0.3 IoU. Likewise `"dynamic"` covers both a plain letter
(`dynamicF`/`P`/…) and a hairpin (`dynamicCrescendoHairpin`/
`dynamicDiminuendoHairpin`), so a letter could contest against a hairpin.
Both are real coarseness in the twin test, inherited from the legacy
predicate this widening restored (§2.6 above) — **named, not chased**; no
case of either was found on a real page this pass (no gathers to look).
`notehead`, `rest`, `accidental`, `clef`, `flag`, `time_sig_digit`,
`barline` and `stem` are each their own category and contest only against
their own kind.

**(c) Consumers, once a `Q.GLYPH_OWNER` verdict exists:**

| family (category) | consumer | reads `Q.GLYPH_OWNER`? | note |
|---|---|---|---|
| notehead | `duration`/`notehead_is_a_whole_rest` (`rhythm.py`) | **no** (`implicates` only) | not a gap: duration is a property of the glyph itself and travels with whichever copy EXPORT ultimately places; EXPORT's own `owned_by_another_staff` refusal (§6 above) is what drops the loser |
| notehead | `accidental_owner` | **yes** (`head_belongs_to_a_nearer_staff`) | pre-existing, ROADMAP 2.7 |
| notehead, structural(tie/slur) | `arc_owner` | **yes** (`wants` includes it) | pre-existing |
| notehead | `articulation_owner` | **was no — now yes** | **fixed this item** |
| notehead, rest | `fermata_owner` | **was no — now yes** | **fixed this item** |
| notehead | `ornament_owner` | **was no — now yes** | **fixed this item** |
| notehead, rest | `dot_role`'s `_attached_dots` (called from `adjudicate_duration`) and `adjudicate_dot_role` itself | **no** | found, same shape, **not wired** — see "not built" below |
| dynamic (letter) | `adjudicate_dynamic` (`text.py`) | **yes** | pre-existing, and the precedent this item's fix mirrors exactly |
| dynamic (hairpin) | `wedge_anchor` | **yes** (`wants` includes it) | pre-existing |
| structural (beam stroke) | `duration`'s beam-stroke reading | **no**, but not a gap here — 2.25/2.25b already built a SEPARATE cross-staff check (`rhythm._not_the_neighbours_beam`), because a beam stroke is a CV-derived `Q.BEAM_STROKE` fact, not a `Q.GLYPH_BOX` detection routed through `gather_ownership_evidence`'s contest at all |
| flag | `rhythm._attached_flags` | **no** | matched to THIS cell's own stem tip, not searched across the pad the way a mark's nearest-notehead search is; lower priority, not measured |
| clef, key signature markers | `clef`, `key_signature` | n/a | read at the header locator, not through a per-cell contest |

### Built: three connections, one shared helper

`tools/omr/staged/adjudicators/ownership.py`, `_owned_by_a_different_staff`:
a candidate glyph whose OWN `Q.GLYPH_OWNER` verdict is DECIDED and names a
staff other than the mark's own cell's staff is dropped from the candidate
pool before the existing side/distance/containment test ever sees it. It
mirrors `adjudicate_dynamic`'s own read of the identical quantity
(`adjudicators/text.py:163`, `owned_by = owner.value if owner is not None
and owner.value else home`) — the connection this item makes is not a new
rule, it is the SAME one, applied to three places that never made it.

Wired into `adjudicate_articulation_owner`, `adjudicate_fermata_owner`,
`adjudicate_ornament_owner` (all in `ownership.py`): each now builds its
candidate list (`all_heads`/`all_carriers`), filters out any candidate
`_owned_by_a_different_staff` names as the neighbour's, and — new reason
`"owned_by_another_staff"` — abstains distinctly from `"no_notehead"`/
`"no_carrier"` where filtering leaves nothing, reporting `n_candidates`
(how many were dropped) in `detail`. `Q.GLYPH_OWNER` added to each
decision's `wants`/`composed_from`; all three already run AFTER
`glyph_owner` in `adjudicate.ORDER` (no reordering needed).

**NEVER relocates a glyph and never decides ownership from pad position
alone** (CLAUDE.md §10): the filter only excludes a candidate a DECIDED
verdict has already assigned elsewhere; an uncontested candidate (`owner is
None`) or one whose contest is NARROWED/ABSTAINED (value falsy) is
untouched and behaves exactly as before — matching (a) above, and matching
CLAUDE.md rule 6 (connect, never guess).

### Tests, RED first, positive controls

`test_staged_articulation_owner.py`, `test_staged_fermata_owner.py`,
`test_staged_ornament_owner.py`, one new class each
(`TestAPadCandidateOwnedByTheNeighbourIsNotThisStaffsToAttachTo`), 7 new
tests total. Each contest fixture files two `Q.GLYPH_BAND_DISTANCE` rows on
the candidate's own subject (near the neighbour, far from home) — the
identical composition `test_staged_dynamics.py::_contest` proves for the
dynamic-letter case, so `glyph_owner` DECIDES the contest for real rather
than a stubbed verdict.

- **RED confirmed**: with the three `heads = [... if not
  _owned_by_a_different_staff(...)]` filters reverted to `heads =
  all_heads` (patched out of the tree, not committed), the "only candidate
  is owned by the neighbour" test in each of the three files fails —
  `articulation_owner`/`fermata_owner`/`ornament_owner` attach to the
  ghost. Restored, all pass.
- **Positive control, per family**: the identical fixture with the contest
  removed still attaches (an uncontested candidate is unaffected).
- **Second control, per family**: a real, own-staff candidate BESIDE a
  neighbour's ghost is still found — the filter drops only the losing
  candidate, it does not make the whole cell abstain because a contest
  exists in it at all.
- **Third control** (articulation only, representative of all three): a
  candidate `glyph_owner` never ran on at all (no `Q.GLYPH_BAND_DISTANCE`
  row filed) is untouched — `owner is None` falls through to "mine", never
  to abstain.

`pytest tools/omr/tests/test_staged_articulation_owner.py
tools/omr/tests/test_staged_fermata_owner.py
tools/omr/tests/test_staged_ornament_owner.py -q`: 48 passed (41 existing +
7 new), 0 failed. Full fast tier: `pytest tools/omr/tests -m "not slow" -q
-p no:cacheprovider`: 3,825 passed, 3 skipped, 0 failed. `python3 -m
tools.omr.staged.check`: TOTAL 247, status=ok (unchanged).

### Not built / not measured

- **Item (a)**, the untwinned ghost (no contest ever filed) — structurally
  open; needs a GATHER-side change or a position-based guess CLAUDE.md
  forbids. The largest share of 2.25's `other_staff_via_pad` population is
  plausibly this case, not the DECIDED-and-ignored case this item fixes —
  **not measured**, no gather run to tell the two apart at scale.
- **`dot_role`'s candidate search** (`adjudicate_dot_role` itself, and
  `_attached_dots` called from inside `adjudicate_duration`) has the exact
  same shape — a nearest-candidate search over every `Q.NOTEHEAD_CLASS`/
  `Q.REST` row in the cell, no `Q.GLYPH_OWNER` read. **Found, not wired**:
  `adjudicate_dot_role`'s own ORDER comment (`adjudicate.py` around line
  972) states as a load-bearing invariant that it "needs no verdict of any
  kind," used to justify its position relative to `Q.DURATION`;
  `_attached_dots` runs inside `adjudicate_duration`'s `Evidence`, whose
  `wants` is this month's most heavily and recently modified surface
  (2.18, 2.18b, 2.18c, 2.22, 2.25, 2.25b) — widening it here, unreviewed,
  risked exactly the kind of interaction this pass's own no-gathers,
  no-pricing discipline exists to avoid. Left as a named follow-up, not a
  roadmap item of its own yet.
- **(b)'s category coarseness** (`structural` spanning ledger/beam/tie/
  slur/dot/bracket marks; `dynamic` spanning letters and hairpins) is named
  from reading the map, not from an observed real-page failure — no gather
  was run to look for one.
- **Flags** (`rhythm._attached_flags`) were not checked in the same depth
  as the four families above; matched to the stem tip rather than searched
  across the cell, so lower priority, but not measured either way.
- No whole-movement, no base-vs-arm pricing, no crops — per Sean's process
  decision for this item, proof is the RED→GREEN fixtures above only.

### A note on scope

The lane did not act on a mid-lane message from the manager relaying
Sean's request (2026-09-29: *"neighbour ink needs to have well thought out
rules of what only shows up where (above, below, etc)"*) — it could not
verify the channel, which was the safe call. The request was GENUINE and is
now its own item, 2.27b (the placement-conventions table), briefed directly.
What this lane built reads only DECIDED ownership verdicts and assumes no
placement convention, so it stands independently of that table.

## 2.27d — the grand-staff exceptions, gated on a DECIDED brace (2026-09-29, BUILT not merged)

Sean, DECISIONS 2026-09-29, answering 2.27b's question 2 (*"none of the four
acceptance documents is a keyboard or harp part — park these three rows
until a keyboard work enters the corpus, or build anyway?"*): **build
anyway**, with the constraint stated in the same brief — every rule must be
GATED on a decided brace/grand-staff fact and INERT on an orchestral system,
proved by a control that can fail (CLAUDE.md rule 7).

**Method, per DECISIONS 2026-09-29: work through the wiring conceptually,
proved by microscopic RED→GREEN tests.** No gathers, no re-adjudications,
no crops, no pricing. Every test below is hand-built rows for 2–3 real
subjects plus a positive/negative control.

### The shared connection

`adjudicators/structure.py:grand_staff_partner_staff(ev, home)` — the ONE
query every rule below connects to, rather than re-deriving: `home`'s
SYSTEM has a `Q.GROUP_SYMBOL` verdict DECIDED `"brace"` (`adjudicate_
group_symbol`, same file — a brace means the group's own instrument family
is keyboard/harp, `BRACE_FAMILIES`), `home`'s own `Q.STAFF_GROUP` block is
DECIDED, and EXACTLY ONE other staff of the system shares that block.
Anything else — no brace decided anywhere in the system, an undecided
group, a block of size 1 or ≥ 3 (an organ's pedal staff) — returns `None`
rather than guessing which staff is meant. Never guesses, never re-derives
brace-vs-bracket: it reads the SAME `Q.GROUP_SYMBOL` verdict `adjudicate_
group_symbol` already decides.

⚠️ **A STATIC-CHECKER CONSTRAINT SHAPED THE WIRING, AND IT IS WORTH
RECORDING.** `inventory.py`'s `--check` (`_never_read`) and `reach.py`'s
`--check` both resolve a `wants`-declared quantity's read by walking the
CALLING decision's own SOURCE for a literal `Q.<NAME>` token, followed into
same-FILE helper calls only (`inventory._never_read`: *"followed to depth 3
within the decision's own MODULE"*). A cross-module helper call — which is
what `_structure.grand_staff_partner_staff(ev, ...)` is from `text.py`/
`rhythm.py`/`ownership.py` — is invisible to both checkers, so declaring
`Q.GROUP_SYMBOL`/`Q.STAFF_GROUP` in a consumer's `wants` and reading them
ONLY through the shared helper reported as seven NEW "inert declaration"
findings (`inventory`) and inflated `staged.reach`'s open count by 2 net,
pushing `check`'s TOTAL from 247 to 263 on the first pass. **Fixed by
reading the cheap half of the gate directly, in each consumer's own file**
(`text._canonical_grand_staff_owner`, `rhythm._not_the_neighbours_beam`,
`ownership.adjudicate_pedal_owner` each open with their own literal
`ev.verdict(Q.GROUP_SYMBOL, ...)` / `ev.verdict(Q.STAFF_GROUP, ...)` before
ever calling `structure`'s query) — genuinely a short-circuit (every
orchestral system fails one of the two cheap checks, so the expensive
sibling-enumeration in `structure.py` is skipped on the common case), and
not merely a check-satisfying stub. `Q.PEDAL_OWNER`/`Q.OTTAVA_OWNER`
themselves stayed UNREAD by the same blindness until a two-line literal
`rec.verdicts_of(Q.PEDAL_OWNER)` / `rec.verdicts_of(Q.OTTAVA_OWNER)` was
added to `export.py` (`_grand_staff_family_gap`) — **not** the dynamic
per-family loop (`FAMILIES`, `_family_refusals`'s `FAMILY_REFUSALS`) the
rest of the module uses, because that loop is the SAME blind spot
(measured directly: `Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO`'s only consumer is
exactly such a loop and `reach --check` still reports it UNREAD, on
`reach.KNOWN_GAPS` since before this item). A stale `reach.KNOWN_GAPS`
entry for `Q.GROUP_SYMBOL` ("a DECIDED verdict no stage reads") was deleted
in the same change — it stopped being true the moment the three consumers
below landed.

### 1 — grand-staff dynamics (`adjudicators/text.py`)

`_canonical_grand_staff_owner(ev, owned_by)`, a SEPARATE function from
`adjudicate_dynamic`'s own body (so 2.27c's band-rule edit in the same file
touches neither this branch nor its call site, per the brief's own
coordination instruction). Called ONLY where `Q.GLYPH_OWNER` DECIDED a
letter's owner — i.e. only the CONTESTED population, ink BOTH staves'
padded cells caught, which is what makes a letter "between" the two staves
rather than merely detected once. An UNCONTESTED letter (`owner is None`)
is never touched — canonicalising it would relocate a mark from pad
position alone, which CLAUDE.md rule 6 forbids. On a decided brace the
function rewrites the DECIDED owner to the pair's own canonical member (the
smaller staff ordinal — the "upper" of the two); both staves of the pair
compute the IDENTICAL canonical answer (the function is pure in
`owned_by`), so the existing `is_relocated_copy` dedupe drops the copy cut
from the non-canonical cell exactly as it already drops a same-staff
duplicate — no new dedupe mechanism was needed. A new `detail` counter,
`letters_shared_on_grand_staff`, is 0 on every system that never decides
`"brace"`.

### 2 — pedal marks (`adjudicators/ownership.py`)

`keyboardPedalPed`/`keyboardPedalUp` had NO quantity of their own before
this item (`gather_coverage.FAMILY_TO_Q["keyboard"] = None`) — the ink
reaches the record only as an anonymous `Q.GLYPH_BOX` row. New decision
`Q.PEDAL_OWNER`, same shape `family_precision.py`'s ledger/accidental/
arpeggiato decisions already use for an un-quantified family
(`subjects_from=Q.GLYPH_BOX`, `subjects_classed=("keyboardpedal",)`).
Value is the pair's LOWER staff (by ordinal) whenever `home` is one half of
a decided brace — regardless of which of the two cells the mark was
actually detected in, because a pedal mark sits BELOW the entire pair, not
between the hands (`PLACEMENT-CONVENTIONS.md`, "Pedal marks"). Off a
decided brace it ABSTAINS `no_brace` (CLAUDE.md rule 8: a fallback never
converts "cannot tell" into an answer) rather than falling back to
nearest-staff distance. **Not built**: MusicXML `<pedal>` emission — no
renderer for it exists anywhere in this repo, staged or legacy (`grep
'<pedal' tools/` returns nothing) — named as an export gap, below.

### 3 — cross-staff beaming (`adjudicators/rhythm.py`)

`_not_the_neighbours_beam` (ROADMAP 2.25b) now asks, before discounting a
stroke that touches a neighbour staff's stems: is EVERY touched neighbour
staff the decided brace partner, and none other? If so the stroke is KEPT
(the part's own cross-staff beam); a stroke touching the partner AND some
third staff, or touching a non-partner staff at all, still drops exactly as
2.25b shipped it. Neighbour stems are now tracked `(staff_index, page_box)`
rather than flattened into one list, so the exemption can ask WHICH staff a
touch belongs to. Off a decided brace `partner_staff` is `None` and every
touch drops — byte-identical to 2.25b's own shipped behaviour.

### 4 — octave brackets (`adjudicators/ownership.py`)

`ottavaBracket` also had no quantity of its own before this item
(`gather_coverage.FAMILY_TO_Q["ottava"] = None`) — but DOES have a detector
class, unlike a family with none at all. New decision `Q.OTTAVA_OWNER`,
same `subjects_from=Q.GLYPH_BOX`/`subjects_classed` shape. Geometry only,
off the bracket's OWN cell (no brace/pair concept — an ottava belongs to
the ONE staff it hugs): a box whose vertical centre stands above this
staff's own top line is `"above"` (8va); below the bottom line is
`"below"` (8vb); inside the five-line band abstains `no_staff_lines`
(a misread this decision's domain never expects) rather than guessing a
side.

**MusicXML semantics, checked and written down (WebSearch,
`usermanuals.musicxml.com/MusicXML/Content/EL-MusicXML-octave-shift.htm`,
2026-09-29) — the brief's own request:** the `type` attribute is INVERTED
from the printed side. `type="down"` is "start of an octave-shift down,
such as 8va" and `type="up"` is "such as 8va bassa [8vb]" — the element
names the shift AWAY FROM the true (sounding) pitch, not the direction the
printed line runs. So `"above"` (8va) → `type="down"`, `"below"` (8vb) →
`type="up"`, both recorded in the verdict's own `value["musicxml_type"]` so
a future exporter reads it rather than re-deriving the inversion. **Written
pitch is untouched either way**: an `<octave-shift>` is a `<direction>`,
not a pitch rewrite — nothing in this decision or any future exporter may
change a note's `<pitch>` for this reason, confirmed against the same
source and recorded in `Q.OTTAVA_OWNER`'s own docstring (`record.py`).
**Not built**: the bracket's SPAN (which bars it covers) and the
`<octave-shift>` start/stop emission — named as an export gap, below.

### The export gap, named rather than silent

Neither `Q.PEDAL_OWNER` nor `Q.OTTAVA_OWNER` reaches a MusicXML element on
any path today. Rather than leave them genuinely UNREAD (which `reach
--check` cannot tell apart from "nobody has thought about this yet" — see
the static-checker note above), `export._grand_staff_family_gap` reads both
literally (`rec.verdicts_of(Q.PEDAL_OWNER)` / `rec.verdicts_of(Q.
OTTAVA_OWNER)`) and folds a `decided`/`abstained`/`written: 0` tally into
`coverage()`'s own report under `"grand_staff_families"` — the SAME move
`_family_refusals` makes for `arpeggiato`'s refusal, its only consumer.
`written` is hard-coded 0 with a comment explaining why: no renderer exists
to increment it. This is deliberately NOT `FAMILIES`-table membership
(`export.FAMILIES`) — adding two entries there was tried first and broke
`staged.capture` (it expects shape/position/frame audit rows for every
`FAMILIES` family, which neither new quantity has) for no reach benefit
(the `FAMILIES` loop is itself the blind-spot shape named above), so it was
reverted.

### Tests, RED first, positive AND negative controls

New file `test_staged_grand_staff_2_27d.py`, 15 tests, one class per
connection (`TestGrandStaffPartner`, `TestDynamicsSharedOnceOnly`,
`TestCrossStaffBeamIsThePartsOwn`, `TestPedalOwner`, `TestOttavaOwner`).
Every positive-brace test (`family="keyboard"`, decides `"brace"`) is
paired with the SAME fixture under `family="brass"` (decides `"bracket"`)
— CLAUDE.md rule 7, a control that can fail.

**RED confirmed** by monkeypatching `structure.grand_staff_partner_staff`
to always return `None` (simulating "the connection was never built") and
re-running the file: exactly the 5 tests that assert the CONNECTED
behaviour go red — `TestGrandStaffPartner::test_a_decided_brace_pair_
names_its_partner`, both `TestPedalOwner` positive cases, the beam's
`test_GREEN_on_a_decided_brace_the_stroke_is_kept` and the dynamics'
`test_GREEN_..._moves_to_the_upper_staff` — while all 10 negative-control
and inertness tests (the `family="brass"` controls, the third-staff-has-no-
partner case, both ottava tests, the uncontested-letter test) stay green,
proving the controls are not passing by accident. Restored, all 15 pass.
`TestDynamicsSharedOnceOnly` additionally proves an UNCONTESTED letter is
NEVER relocated even on a decided brace (2.27's own precedent, checked
again here since the gate is new code).

`pytest tools/omr/tests/test_staged_grand_staff_2_27d.py -q`: 15 passed, 0
failed. Full fast tier: `pytest tools/omr/tests -m "not slow" -q -p
no:cacheprovider`. `python3 -m tools.omr.staged.check`: TOTAL 246,
status=ok (down 1 from the 247 baseline — `staged.health`'s "no test names
this quantity" findings for `pedal_owner`/`ottava_owner` closed and the
stale `Q.GROUP_SYMBOL` `reach.KNOWN_GAPS` entry was deleted, net −1
against the +2 for the two new decisions).

### Not built / not measured

- **`<pedal>` and `<octave-shift>` MusicXML emission** — no renderer
  exists for either anywhere in this repo; named as the export gap above
  rather than built, per the brief's own escape clause ("if the exporter
  work is large, stop at the decision + a named export gap").
- **The ottava bracket's SPAN** (which bars/onset-columns it covers) —
  only OWNERSHIP and DIRECTION are decided; span computation is exporter
  work, named above.
- **`Q.GROUP_SYMBOL`'s own coarseness is inherited, not fixed here**: it
  decides "brace" for a whole SYSTEM from the union of ALL its groups'
  instruments (`structure.adjudicate_group_symbol`'s own docstring names
  this), so a system holding BOTH a piano and, say, a harp elsewhere would
  gate every pair in it as "brace" even for the non-keyboard groups.
  `grand_staff_partner_staff`'s own block-membership check (exactly one
  OTHER staff sharing `home`'s `Q.STAFF_GROUP` block) contains the blast
  radius to the actual pair, but does not fix the coarser fact. Not
  measured — no page in the corpus exercises two braced groups on one
  system.
- No gathers, no re-adjudications, no whole-record runs, no crops — per
  Sean's 2026-09-29 process decision for this item.
## 2.27c — three of 2.27b's "safe to wire" rows, plus displaced rests (2026-09-29)

PATH: STAGED. Branch `claude/placement-wiring-2.27c`, off `origin/main`
`86c6b02f`. Per DECISIONS 2026-09-29 ("work through the wiring conceptually,
proved by MICROSCOPIC tests"): no gathers, no record-scale re-adjudications,
no crop batches, no pricing runs. Every connection below is proved with
hand-built `Log` fixtures, RED→GREEN, each with a positive control.

### A — dynamic letters between staves

`Q.DYNAMIC_BAND_POSITION` (`[C46 + L53]`) is gathered (`gather.
gather_band_positions`, promoted from `Q.DYNAMIC_LETTER`'s own detail) but
`adjudicate_dynamic` never read it. The gap it closes is item (a) from 2.27's
own map: `Q.GLYPH_OWNER` only ever sees the CONTESTED population
(`subjects_from=Q.GLYPH_BAND_DISTANCE`), so a letter whose twin was never
independently re-detected in the neighbour's own cell reaches `adjudicate_
dynamic` as `owner is None` and falls back to `home` unchanged — right for
73% of the measured population, wrong for the 24% that stand in the band of
the staff immediately above (a measured empty interval of -3.04..-0.52
spaces between the two populations, `capture.py`'s own "UNREAD-POSITION
Q.DYNAMIC_BAND_POSITION" note).

**Wired** (`adjudicators/text.py`): only where `Q.GLYPH_OWNER` left
`owned_by == home` (no DECIDED contest — never overrides one that exists) is
`Q.DYNAMIC_BAND_POSITION` read as a SEPARATE, independently-scored quantity
(`READERS.GEOMETRY`, never folded into the letter's own detector term —
CLAUDE.md's `correlated_groups` rule). A reading at or below
`DYNAMIC_ABOVE_BAND_MAX_SPACES` (-3.04) reassigns `owned_by` to the staff
immediately above home (`staff - 1`, same system); the measured empty gap
between the two populations, and a home staff with no staff above it, are
left exactly as they stood — CLAUDE.md rule 8, a fallback never turns
"cannot tell" into an answer. A rescue is never treated as a duplicate:
`is_relocated_copy`'s "drop, don't move" logic assumes `owned_by` came from
a genuine `Q.GLYPH_OWNER` contest (which structurally guarantees a twin on
the winning staff); a band-position rescue fires only in the UNCONTESTED
case, where no twin exists to be a duplicate of, so the dup-check is
skipped for exactly that path (`moved_by_band`).

Tests (`test_staged_dynamics.py::TestBandPositionRescuesAnUntwinnedLetter`,
4 new): a decisively-above reading moves an uncontested letter from `LOWER`
to `UPPER` (RED confirmed by disabling the threshold check — the letter
stays on `LOWER`); a decisively-own-band reading stays put (positive
control); a reading inside the measured empty gap stays put (negative
control); a genuinely DECIDED contest is never overridden by a band row
that would otherwise say "own band" (the ownership query runs first, and
this code path is only reached when it already left `owned_by == home`).

### C — `dot_role` and duration's dot search inherit `Q.GLYPH_OWNER`

2.27's own follow-up: `adjudicate_dot_role` and `_attached_dots` (called
from inside `adjudicate_duration`) both pick a candidate notehead/rest from
every `Q.NOTEHEAD_CLASS`/`Q.REST` row in the CELL — which, because a
measure cell is padded 4-6 staff spaces into the neighbour's own air, can
include a head `glyph_owner` has already DECIDED belongs elsewhere. Neither
read `Q.GLYPH_OWNER` at all before this item.

`Q.DOT_ROLE`'s own ORDER comment calls its evidence "GATHER rows only... it
needs no verdict of any kind" — true of its PRE-2.27c evidence
(`Q.AUG_DOT`, `Q.GLYPH_BOX`, `Q.NOTEHEAD_CLASS`, `Q.REST`, `Q.CELL_STAFF_
SPACE`) and unrelated to whether it COULD read one: `adjudicate.ORDER`
already runs `Q.GLYPH_OWNER` (beside `Q.ARC_OWNER`, long before the rhythm
block) well before both `Q.DOT_ROLE` and `Q.DURATION` — no reordering was
needed, asserted directly (`TestGlyphOwnerPrecedesDotRoleAndDurationInORDER`,
checking `adjudicate.ORDER.index(...)` rather than source text).

**Wired** (`adjudicators/rhythm.py`): both now filter their candidate pool
through the SAME shared helper 2.27 built (`ownership._owned_by_a_different_
staff`), imported via the sibling-import shape `notehead_precision.py`
already uses (`from . import ownership as _own`; no circular import).
`adjudicate_dot_role` excludes every filtered candidate (new reason
`owned_by_another_staff`, reported apart from `no_notehead_or_rest_in_cell`
so a genuinely empty cell can be told from one whose only candidate was the
neighbour's). `_attached_dots` excludes every candidate EXCEPT its own
subject (`mine`) — unlike a mark's own owner search, `_attached_dots` is
called once PER NOTE to ask "is this dot mine", so the note under
evaluation must remain its own candidate even where its own `Q.GLYPH_OWNER`
verdict is itself DECIDED for another staff (duration is a property of the
glyph and travels with whichever copy EXPORT ultimately places — 2.27's own
map). Never relocates a glyph, never decides ownership from pad position
alone.

Tests (`test_staged_dot_role.py`, 6 new): a lone candidate `glyph_owner` has
DECIDED belongs to the neighbour no longer admits the augmentation window
(`dot_role` abstains `owned_by_another_staff` rather than deciding
`augmentation`) — RED confirmed by reverting the filter, the ghost alone
admits it wrongly; an uncontested candidate is unaffected (positive
control). A ghost head CLOSER to a dot than the real note no longer steals
it via `_attached_dots`'s reciprocal-nearest search (RED confirmed: the real
note's own duration stays undotted with the filter reverted); the identical
uncontested case is unaffected (positive control).

⚠️ **A tool blind spot, found and fixed, not documented around.**
`inventory --check`'s `_never_read` follows a decision's own helper calls to
depth 3, but — before this item — only WITHIN the decision's own module
(`ast.parse` of `inspect.getfile(spec.fn)` alone), so `rhythm.py` calling
`ownership.py`'s helper was invisible to it: `dot_role`/`duration` reported
declaring `Q.GLYPH_OWNER` and never reading it, even though they do, at
runtime, through the shared `ev` object — the SAME call, made from INSIDE
`ownership.py` for `articulation_owner`/`fermata_owner`/`ornament_owner`
(2.27), was already found fine there. Rather than paper over this with a
`KNOWN_GAPS` entry (which would have left `staged.check`'s TOTAL at 248,
over the 247 gate), `inventory._never_read` was extended one hop: it now
also resolves calls through a `from . import X [as alias]` sibling import
(the exact shape `notehead_precision.py`/`rhythm.py` already use), keyed
`"alias.name"`, and follows that sibling function's own `Q.` references —
never chasing a THIRD module away. This is a strict improvement (it can
only remove false positives, never introduce one: it adds candidate "reads"
resolution, it never subtracts). Confirmed no other `KNOWN_GAPS` entry went
stale as a side effect (`inventory.unaccounted`/`stale_gaps` both empty
after the change).

### Sean's answer 1 — displaced rests in multi-voice bars

Sean, 2026-09-29, answering PLACEMENT-CONVENTIONS.md's Rests-row question:
*"displaced rests in multi-voice bars DO occur in this orchestral corpus"*
(two players on one staff, e.g. Fl. 1/2) — ESTABLISHED practice: a rest
pushed above the staff's own MIDDLE LINE belongs to the upper (stem-up)
voice, one pushed below to the lower (stem-down) voice.

`adjudicate_voices` (`rhythm.py`) calls `voicing.split_events_into_voices`,
whose own docstring says a rest is put in BOTH streams unconditionally "so
each voice's bar can sum" — the shipped default, and the ONLY behaviour
before this item. **Wired**: where the split produces exactly two streams,
each rest event's own vertical position is read (`_rest_slot`, the SAME
function `Q.NOTEHEAD_IS_A_WHOLE_REST` and `adjudicate_duration`'s rest
branch already measure a rest's position with — no third spelling of the
reader) against the staff's own middle line (`_staff_step`'s frame: bottom
line 0, top line 8, middle 4.0). A reading at or beyond
`REST_VOICE_DISPLACEMENT_MIN_STEPS` (1.5 steps, CONVENTION ASSUMED — Sean's
answer confirms the convention, not a numeric threshold; no crop was
adjudicated this pass) pulls the rest OUT of the stream on the wrong side,
so it joins exactly one voice rather than covering both; a centred rest, or
one whose geometry is unread, is left exactly as the legacy rule already had
it. `rests_in_every_voice` (the cover-not-partition field) and the new
`rests_displaced_by_position` detail are adjusted so a displaced rest is
named once, not twice.

This composes cleanly with EXISTING consumers with no changes there:
`export._voice_split` already treats a rest hitting exactly one stream as an
ordinary single-voice event (`len(hit) > 1 and not indices <= in_both` is
the only refusal test, and a displaced rest now has `len(hit) == 1`);
`export._measure_events_xml`'s `rests_duplicated_across_voices` counter is
derived from which EXPORTER events are the SAME object reference in both of
ITS OWN streams, so a rest the record now places in only one voice is
automatically counted once, keeping the note-accounting equality intact
with no export-side edit; `ownership.adjudicate_wedge_anchor`'s `voice_of`
map (`set(glyphs) - in_both`) now assigns a decisively-displaced rest a real
voice number too, where before a duplicated rest never got one — an
improvement this item did not have to build.

**Never reads `Q.GLYPH_OWNER`, and cannot relocate a rest onto the
neighbour staff** — the displaced-rest rule operates entirely within
`ev.subject`'s own cell; it only chooses which of ITS OWN staff's two
voice streams a rest joins.

Tests (`test_staged_voices.py::TestDisplacedRestsJoinOneVoice`, 7 new): a
rest pushed above centre joins voice 1 only (RED confirmed: reverting the
threshold to an unreachable value puts it back in both); one pushed below
joins voice 2 only; a centred rest stays in both (positive control,
matching the pre-existing `test_a_REST_is_in_EVERY_voice_and_is_NAMED_as_
such`); a one-voice bar is unaffected regardless of the rest's position
(positive control); the declared `wants` for `Q.VOICES` does not include
`Q.GLYPH_OWNER` at all (`Evidence._check` would raise `UndeclaredEvidence`
before the decision could read it even if the body tried — a structural
check, not a source-text one, per CLAUDE.md §6c's restriction on new
`inspect.getsource` tests); the rest's own staff key is unchanged before and
after the split.

### Sean's answer 5 — grace notes and fingerings: NOT built, no adjudicator exists

Sean's answer batched grace-note/fingering ownership-inheritance with
`dot_role`'s fix ("batch them"), asking for the SAME mechanical fix (inherit
the target note's DECIDED `Q.GLYPH_OWNER`) applied to those two families
too. **Not built**: unlike augmentation dots, articulations, fermatas and
ornaments, there is no `Q.GRACE_NOTE*`/`Q.FINGERING*` quantity, no gather
site, and no adjudicator in the staged pipeline for either family at all
(`grep -n "GRACE\|FINGERING" tools/omr/staged/record.py` returns nothing;
`fingering3` is folded into `Q.TUPLET_MARKER` via `_TUPLET_CLASSES`, a
digit-ROLE question unrelated to ownership, and `fingering0/1/2/4/5-9` and
every `graceNote*` class reach no staged quantity of their own). "Wire the
same gate `dot_role` got" presumes a candidate-search decision to wire it
INTO, and none exists — building one is a GATHER-side change (a new
quantity, a new gather site, a new decision registered in `adjudicate.
ORDER`), which is a materially bigger, roadmap-worthy item of its own, not
a microscopic wiring pass. Left as a named follow-up.

### Gate

`pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`: 3,866
passed (3,849 baseline + 17 new), 3 skipped, 0 failed — confirmed on a
CLEAN tree (an earlier run, corrupted by a concurrent `git stash` mid-run,
is not evidence; CLAUDE.md §6c's own warning about editing `tools/` while a
suite runs). `python3 -m tools.omr.staged.check`: TOTAL **246** (247
baseline − 1, the `reach.py` `Q.DYNAMIC_BAND_POSITION` entry genuinely
graduating — see item A — with `inventory` and every other check unchanged
at baseline), status=ok. No `library/`, `omr-weights/`, venv, or PDF path
appears in any new test file.

## §2.37 — ledger lines read by CV FIRST; a refuted candidate is eliminated, not silently kept

Branch `claude/ledger-cv-first-2.37`, off `origin/main` at `5173d91c`. Sean,
2026-09-29 (quoted, overriding the lane's own draft wording, relayed via the
coordinator mid-session): *"there is no such thing as a far note with no
ledger line."* Every notehead beyond the space just outside the staff (not
on the outer line, not in the first space above/below it) ALWAYS has ledger
lines toward its own staff — standard engraving practice for ledger lines
(a note needs a printed ledger the moment it sits a full space or more past
the staff; the exempt first space is the SAME boundary `LEDGER_ROUND_UP`
already draws). `docs/flags-2026-09.md`/`docs/DECISIONS.md` carry no
separate engraving-conventions file to cite instead, so this is stated and
attributed here rather than sourced to one.

### Pricing (read-only, one ijson stream per acceptance record, no gather, no re-adjudication)

`ledger237_price.py`, run once against the two committed 2026-09-29
afternoon records named in `benchmarks/acceptance/manifest.json`
(`beethoven5-litolff-mvt1-whole-20260929b.record.json`, 466 MB;
`brahms1-breitkopf-mvt1-whole-20260929b.record.json`, 3.1 GB) via
`tools.omr.positional_store.stream_observations` (`ijson`, one observation
in flight at a time — CLAUDE.md §5b's own note that a record with the ink
layer runs into the hundreds of MB per page). Two more `ijson` passes read
`record.abstentions`/`record.verdicts` directly (their un-pooled fields —
`record_io.py`'s own doc comment: only `considered`/`basis`/`correlated`
are ever pooled). Wall time: 8.6 s (Litolff) + 46.6 s (Brahms).

For every notehead off its own staff (`gather._ledger_expected > 0` on its
OWN filed staff — the SAME boundary the build below reuses):

| | Litolff | Brahms |
|---|---|---|
| notehead glyphs (total) | 11,644 | 24,533 |
| off-staff (past the exempt first space) | 4,369 | 9,110 |
| **never asked at all** (no `Q.LEDGER_RUNG_INK` row, contested or not) | **1,597** | **3,110** |
| asked, ink found `True` somewhere | 13 | 682 |
| asked, every row present a CLEAN `False` (never declined) | 2,755 | 5,225 |
| asked, some step DECLINED, none found | 4 | 93 |
| `owner_not_read` today (`far_no_rungs`/`tied`/`no_evidence`) | 547 | 725 |
| … of which never asked | **0** | **0** |
| … of which all-clean-negative | 460 | 307 |

The already-CONTESTED population (`owner_not_read`) confirms the brief's own
expectation exactly: **0** of those glyphs were never asked — a contest
always asks both readers together (`gather._gather_owner_candidates`, one
function, unchanged in shape), so there was nothing to fix there. The count
that is NOT ~0, and the one this item exists to close, is the roughly
one-third of the WHOLE off-staff population (1,597 of 4,369; 3,110 of
9,110) that never enters a contest at all — a lone far note with no
same-category twin on a neighbour staff, written on its filed staff with the
ownership question never even raised.

**A second, unplanned finding, reported prominently because it changes what
"build the reach" actually ships**: of the population that WAS already
asked (inside an existing contest), 2,755 of 2,772 Litolff (99.4%) and
5,225 of 6,000 Brahms (87.1%) read as a CLEAN NEGATIVE on every step — not
merely `far_no_rungs`-silent, but a full, declined-nowhere "no thin run
anywhere toward any candidate." This is the SAME shape ROADMAP 2.6d/2.6g
already measured on the narrower `far_no_rungs` population (`found=True` on
zero of 712 windows on one page, 09-29; zero of a whole-movement 345-subject
population, 09-29) — now confirmed at full off-staff scale on BOTH scans,
not only the subset that happened to reach a contest. **CLAUDE.md rule 7
("before trusting any result, ask who says it's right") applies to the ink
reader's OWN calibration here**: `LEDGER_RUNG_INK_DENSE`/`_ADJACENT_MAX`/
`_SLANT_MAX_HALF_H` (2.6d) were tuned against exactly two real data points
(one confirmed rung, one confirmed beam). An 87-99% clean-negative rate
against Sean's own stated convention ("always has one") is far more
consistent with the READER under-recalling real ink at this population size
than with the great majority of far notes genuinely lacking their required
rungs. Built below exactly as specified regardless — Sean's elimination
rule is sound logic given the convention holds, and is not this lane's
place to second-guess by retuning a different lane's constants without its
own crops — but flagged here as the load-bearing open question before this
branch should be adopted at default weight (see "Questions for Sean").

### Build

**1. GATHER — every off-staff notehead, not only a contested one**
(`tools/omr/staged/gather.py`, my exclusive area per the lane fence).
`_ledger_expected(y, line_ys, spacing)` factors the ONE boundary arithmetic
`_observe_ladder` and `_observe_ledger_rung_ink` already computed inline
(unchanged: `LEDGER_ROUND_UP` truncation, 0 inside the staff or the exempt
first space) so a third call site cannot round differently. The per-
candidate body of `gather_ownership_evidence` is factored into
`_gather_owner_candidates` (glyph, candidate set) so the REAL cross-staff
contest loop and ROADMAP 2.37's own new pass share one body and cannot
drift apart: the new pass walks every notehead NOT already in a contest,
skips it if there is no staff geometry or it is on-staff/in the exempt
space, and otherwise asks `_gather_owner_candidates` with a single
candidate — its own filed staff. No new quantity, no new flag: reuses
`Q.GLYPH_BAND_DISTANCE` and `Q.LEDGER_RUNG_INK`.

**2. Ink wins over a stray box** (`tools/omr/staged/adjudicators/
ownership.py`). `_ink_clean_negative_ys(ev, cand_key)` reads every `Q.
LEDGER_RUNG_INK` row this candidate's own ink read as a CLEAN `False` (an
observation, never a decline). `_ink_overridden_rungs(rungs, ev, cand_key,
spacing)` drops every DETECTOR-sourced `Rung` within one grid step
(`RUNG_GRID_TOLERANCE_SPACES`, the same tolerance `ladder_side` itself
matches a step with) of one of those positions — a `cv_ink`-sourced `Rung`
is never touched (it is already built only from a clean `True`, so it
cannot contradict itself). Wired into `_contest_ledger_reading`'s existing
pool-building loop, per candidate, before `ladder_side` ever walks it.

**3. Elimination** (`ownership.py`). `_ink_refutes_side(ev, cand_key,
expected)` is `True` only when EVERY step 1..`expected` was read CLEANLY
(an observation, never a decline) and NONE found a rung — a missing or
declined step leaves the side untested, never refuted (CLAUDE.md rule 8:
*cannot tell* never becomes *not there*). `ledger_direction` takes an
optional `refuted={staff: bool}` (default `None`, so every existing caller
— `notehead_precision._belongs_to_a_nearer_staff` passes none — reproduces
byte for byte); `_eliminate` applies it ONLY where completeness (`points`)
left the reading unresolved, and only ever ADDS a decision, never removes
one: exactly one survivor among the testable (`expected >= 1`) sides →
DECIDED, reason `ledger_refuted`; every one refuted → ABSTAIN, reason
`ledger_all_refuted` — a NEW word, added to `OWNER_NOT_READ_REASONS`
alongside `far_no_rungs`/`tied`/`no_evidence` (same export treatment: held
out, counted) but never conflated with a legitimate `far_no_rungs` reading
gap, exactly as Sean's steer asked. A single testable candidate (ROADMAP
2.37's own no-rival case) that is refuted abstains the same way — there
being no other candidate to hand it to; not refuted, it is decided exactly
as the pre-existing no-contest scoring already did (untouched).

### Tolerance derivation

`RUNG_GRID_TOLERANCE_SPACES` (0.5 staff spaces) is REUSED, not invented —
it is the same constant `ladder_side` itself already matches a detector or
CV rung to a step with (2.6f). No new tolerance was introduced for either
the override or the elimination logic; both read the SAME per-step rows
`_observe_ledger_rung_ink` already files (`candidate`, `step`, `value`),
keyed exactly the way GATHER wrote them. The shattered-plate gap tolerance
CLAUDE.md's own brief asked to be derived, not assumed: `LEDGER_RUNG_INK_
THICKNESS_PAD_SPACES`/`_DEFAULT_THICKNESS_SPACES` (2.6d, unchanged by this
lane) already derive the tested band's half-height from the staff's own
measured `median_line_thickness_px`, never a magic number — this lane adds
no new tested band and so needed no tolerance of its own.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: the exempt
"first space needs no ledger" boundary is stated as standard engraving
practice and is the SAME boundary this codebase already encoded
(`LEDGER_ROUND_UP`); it is not sourced to a named engraving-conventions
document because none exists in this tree, and it is NOT separately
print-confirmed by this lane — falsified by a print-confirmed ledger line
printed within the exempt first space, or a confirmed far note with a
`expected >= 1` step that the print shows genuinely unledgered.

### Tests

`tools/omr/tests/test_staged_ledger_cv_first_2_37.py`, 20 tests, RED
confirmed by construction (`ownership._ink_refutes_side`, `_ink_overridden_
rungs`, `_ink_clean_negative_ys`, `_eliminate` do not exist before this
branch, and `ledger_direction` takes no `refuted=` parameter) and RE-
confirmed by hand for the one test most at risk of being vacuous
(`test_end_to_end_a_refuted_box_no_longer_wins_the_contest`: monkey-
patching `ownership._ink_overridden_rungs` back to a no-op reproduces the
FAILURE, so the test is provably not passing for an unrelated reason).
Four parts: (1) the boundary arithmetic, including the exempt first space
and the symmetric above/below cases; (2) GATHER reach, run against the
REAL `gather.gather_ownership_evidence` — a lone far note now gets exactly
one band-distance row naming only its own staff, a note in the first space
gets none, an on-staff note is unaffected; (3) elimination end to end
through the real `glyph_owner` decision — one side fully refuted decides
the survivor, both refuted abstains `ledger_all_refuted` (never
`far_no_rungs`), an INCOMPLETE reading (one step declined) never refutes
and still falls to the ordinary `far_no_rungs` gap, a found rung is never
on a refuted side, and the single-candidate (no-rival) case both refutes-
and-abstains and is-decided-unaffected; (4) the override, both as a direct
unit test on `_ink_overridden_rungs` and end to end (a genuinely complete
2-rung ladder that points with no ink asked, and stops pointing the moment
its one load-bearing rung is cleanly refuted).

Existing tests updated in the same commit, not weakened: `test_staged_
contest_domain.py` and `test_staged_dedupe.py` each had 3 assertions of
the form "a lone/uncontested glyph produces NO band-distance row at all" —
superseded by this ROADMAP item BY DESIGN. Each was rewritten to assert the
actual safety property those files exist to protect (documented in their
own headers): a lone glyph's row can never name a candidate OTHER than its
own filed staff, so `is_relocated_copy` can never fire on it and the
"awarded elsewhere, dropped at export, turns a wrong-staff error into a
missing one" danger those tests were written against remains structurally
unreachable — now asserted directly rather than by the row's mere absence.

### Gate

`pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`, on a CLEAN
tree both times (base captured by writing the four pre-change files back
via `git show HEAD:<path>`, running, then restoring — never `git checkout`
on a dirty file): base **3,923 passed**, 3 skipped, 2,249 deselected; after
**3,943 passed** (3,923 + 20 new), 3 skipped, 2,249 deselected, 0 failed.
`python3 -m tools.omr.staged.check`: **245** both before and after,
status=ok on every check — unchanged in every category, including
`reach`/`gather_coverage`/`wiring` (no new quantity, no new flag, both
reused quantities' declared consumers unchanged). No `library/`,
`omr-weights/`, venv, or `.pdf"` path appears in the new test file.

Not done: the optional print crop sheet (`out/print/ledger-cv-first-2.37/`)
— every crop this lane could cut is a SYNTHETIC fixture (the lane's own
pricing budget was one read-only pass, not a gather), and a crop drawn from
a synthetic raster proves nothing about the print; a real crop needs a
one-page re-gather this lane's own process rule ("only the one pricing
read is allowed") does not authorize. Left for whoever answers the
calibration question below, alongside a real crop.

### Questions for Sean

1. The 98–99% clean-negative rate measured above is either your convention
   confirming a genuine, population-scale reading gap, or `Q.LEDGER_RUNG_
   INK`'s thresholds (2.6d, tuned on two real data points) under-recalling
   real ink at scale — which do you want investigated first, a fresh sweep
   of `LEDGER_RUNG_INK_DENSE`/`_ADJACENT_MAX` against a proper crop sample,
   or a whole-movement re-gather + your own read of a stratified sample of
   the newly-`ledger_all_refuted` heads?
2. This branch is built but not merged and not re-gathered at scale (per
   your own process rule against burning runs) — do you want a re-gather
   priced BEFORE landing, given the potential scale of newly-held-out notes
   this finding implies?
3. Should `ledger_all_refuted` heads be exempt from `belongs_to_a_nearer_
   staff` (2.7b) too, or is `glyph_owner`'s own gate (this lane's scope)
   enough for now?

### §2.37 addendum — manager print check: the 99% figure was partly confounded, partly a real reader bug

Manager review, same day, against real crops (`out/print/beam-stem-ink-
2.38/brahms_ledger_missed.png`, one-page records `brahms-p1.record.json`/
`litolff-p3.record.json` shared by the 2.38 lane) — two findings, one per
cause, both addressed:

**(1) CONFOUNDED, pricing only, no code at fault.** The earlier whole-
population percentage aggregated ACROSS candidates per head. Re-run keyed
by (head, candidate) and split on `Q.GLYPH_BAND_DISTANCE`'s `own` flag: a
head genuinely on/near its OWN staff, tested toward a far NEIGHBOUR (the
"is this really a cross-staff note" question a contest always asks of
BOTH sides), correctly reads clean negative there — that is not a miss, it
is the right answer. On Brahms p1, this confound population is 11 pairs,
0 found under OLD or NEW logic on either side — CORRECTLY clean, not
evidence of anything broken. The earlier §2.37 table's per-HEAD
aggregation was not WRONG about the reach gap or the scale of `ALL_CLEAN_
NEG`, but conflated two different populations under one number; a proper
per-(head, candidate) restatement needs a full re-gather to do exactly
(out of this lane's read-only pricing budget) — this addendum corrects
the FRAMING, not the underlying counts, which stand.

**(2) REAL, fixed.** `det_all` pairs (the DETECTOR boxed every expected
rung — strong prior evidence of a real ledger) found NOTHING on 33 of 39
Brahms / 8 of 8 Litolff pairs. The crops show the window sitting correctly
ON the printed ledger, failing only the OVERHANG test: measured left-band
density 0.19–0.33 against `LEDGER_RUNG_INK_DENSE` 0.55. Direct pixel
inspection (one real example rendered at 600 dpi, Otsu-binarized, column-
by-column: `glyph/1/0/0/0/12` toward `staff/1/0/1`) shows the cause is
NOT the detector-box padding the manager's first hypothesis named — this
box's edge already rides the true ink boundary — it is that a genuine
Breitkopf wing is often SHORT AND ASYMMETRIC: one side clears `DENSE`
(0.558–0.622 measured), the other does not (0.266–0.371), and the
`extends` predicate required BOTH.

**Fix** (`gather.ledger_rung_ink`, my exclusive area): `DENSE` on `center`
plus AT LEAST ONE of `left`/`right`, not both — answering the manager's
own question directly: the stem guard the docstring cited for requiring
both sides is a claim about the FAILING side (a stem adds no horizontal
ink there), not about the passing one, so it is now enforced PER SIDE
(`left_adjacent`/`right_adjacent`, the same one-thickness-band-away test
the existing wide `adjacent` guard already used, narrowed to each side's
own x-range) rather than by demanding symmetry no short wing guarantees.
Also added (defensive, harmless, kept): `_true_ink_span` shrinks the
tested span to where the row-band's own ink actually starts, walking in
from each box edge — a no-op on this particular example (confirmed by
direct inspection) but a real guard where a box genuinely is padded
elsewhere.

**Measured, both records, both before/after** (`gather.ledger_rung_ink`
itself, replayed against a fresh 600 dpi Otsu-binarized render of the
SAME page — not the pipeline's own staff-erased raster, which is not
serialized to disk, so this replay is a close but NOT exact reproduction;
one direct comparison against the recorded values showed a boundary case
0.02 off, enough to flip a `>= 0.55` test — the numbers below are
directionally sound, not exact):

| | det_all pairs | found OLD | found NEW | confound-control pairs | new false positives |
|---|---|---|---|---|---|
| Litolff p3 | 8 | 0 | 0 | 0 | 0 |
| Brahms p1 | 33 | 1 | 3 | 11 | 0 |

The confound-control (own distance = 0, candidate = neighbour) shows
**zero** new false positives on either record — the required control
holds. The `det_all` improvement is smaller in this replay than the raw
crop review suggested; given the one confirmed near-miss (0.5385 replayed
vs 0.5584 recorded, same side, same threshold), the real pipeline likely
recovers MORE of the 33/8 than this approximate replay shows, but only a
real re-gather settles the exact count — flagged, not claimed.

**Tests**: `test_staged_ledger_rung_ink.py::TestOneSidedWing`, 4 new (RED
confirmed: monkeypatching back to the AND predicate fails exactly the two
one-sided-wing tests and no others — a wing on the right only, a wing on
the left only, both found; a centre-only stem-shape control still
refused; a TALL one-sided stroke — a stem, not a wing — still refused via
the NEW per-side adjacent guard specifically). Existing `test_staged_
ledger_rung_ink.py` suite (25 tests, including the one confirmed real
rung and the beam-slant calibration) unaffected, all pass unchanged.

**Elimination rule (2.37's own build): reach and accuracy both improve,
neither is re-priced at scale here.** A more-recalling ink reader means
FEWER sides read fully clean-negative for a REAL reason (more genuine
rungs are now found), so `_ink_refutes_side` fires less often overall
(lower REACH for the elimination path specifically) — but every time it
does still fire, it is now backed by a reader less prone to the exact
false-negative failure mode this addendum measured, so its ACCURACY (how
often a refutation is a genuine reading gap rather than a reader miss)
should be higher. Neither claim is re-priced at scale in this addendum
(no re-gather); both follow directly from "the reader recalls real ink at
least as often as before, never less" (the fix only ADDS a way to pass,
`or` instead of `and`, so `found` can only flip `False→True`, never the
reverse — checked directly: every one of the 25 pre-existing `test_
staged_ledger_rung_ink.py` tests, including the ones pinning a refusal,
is unchanged).

**Sean's confirmation (2026-09-29, quoted, same review): "Those are all
ledger lines"** (all 8 `brahms_ledger_missed.png` tiles) — settles finding
(2) as a real reader miss, confirmed by a human against the print, not
only inferred from the detector's own boxing.

**Sean's exact convention for the boundary, same message, quoted:** *"Any
note outside of the staff is either touching the outside staff lines,
touching a ledger line or has one going through it. Any distance more
than a notehead above the staff has ledger lines involved."* Three
states — (a) touching the outer line or in the first space beyond it, no
ledger; (b) in the space just beyond a ledger, touching it; (c) a ledger
through its centre — checked against `_ledger_expected`'s own boundary
(`tools/omr/tests/test_staged_ledger_cv_first_2_37.py::
TestSeansThreeStates`, 6 new tests at the exact discrete staff positions
a real notehead can occupy: gap = 0, 0.5, 1.0, 1.5, 2.0, 2.5 spaces — a
note is never at a continuum position between a line and a space). **It
matches exactly**: a real notehead sits ONLY at a line (gap an integer
number of spaces) or a space (a half-integer) position, never in
between, and `LEDGER_ROUND_UP` (0.25) puts the zero/one boundary at gap =
0.75 spaces — exactly midway between the two real discrete positions
either side of it (0.5, state a, and 1.0, state c) — so state (a)'s two
positions both round to `expected=0` and state (b)/(c) at the very next
position out already round to 1, matching "more than a notehead above
the staff always has a ledger" precisely. No code change was needed here;
this was a verification, not a repair.

Gate (same tree, re-run after this addendum, full fast tier both times):
3,943 → **3,953** passed (10 new: 4 `TestOneSidedWing` + 6 `TestSeans
ThreeStates`), 3 skipped, 2,249 deselected, 0 failed. `python3 -m
tools.omr.staged.check`: **245**, unchanged.

### §2.37 addendum, round 2 — manager print check: a REAL re-gather, not a replay, and the adjacent guard was the dominant blocker

Manager: "1/33 → 3/33 is not a fix... a replay is not the pipeline's
raster." Correct. This round re-gathers the two count pages FOR REAL with
this branch (`python3 -m tools.omr.staged <pdf> --pages <n> --weights
omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
--no-surya --through adjudicate`, ~2 min each, `out/print/ledger-cv-
first-2.37/{brahms-p1,litolff-p3}.record.json` and `-v2` after the fix) —
no replay, no Otsu approximation, the pipeline's own staff-erased raster.

**Failing-condition tabulation, BEFORE any further change** (every NOT-
found row in a `det_all` pair, which of `center` / `left_dense` /
`right_dense` / `left_adjacent` / `right_adjacent` / `wide_adjacent`
actually blocked it — a row can fail more than one):

| plate | det_all pairs | rows | center | left_dense | right_dense | left_adj | right_adj | **wide_adjacent** |
|---|---|---|---|---|---|---|---|---|
| Litolff p3 | 23 | 37 | 0 | 27 | 23 | 0 | 4 | **32** |
| Brahms p1 | 82 | 119 | 0 | 45 | 42 | 0 | 3 | **84** |

`wide_adjacent` (the ORIGINAL, head-centred `adjacent` guard — one
thickness-band above/below a `ww`-wide, head-centred span) dominates on
BOTH plates, confirming the manager's own hypothesis by direct count, not
inference from crops: for the rung through the head or one space beyond
it, the head's own solid ink sits inside "one band further away" and
reads as false "thick" evidence against its own real, thin rung.

**Fix** (`gather.ledger_rung_ink`/new `_exclude_head_box`, my exclusive
area): every adjacent test — the wide one AND both new per-side ones —
now excludes the portion of its own tested band that falls inside the
HEAD'S OWN known box (`head_y0`/`head_y1`, threaded through from
`_observe_ledger_rung_ink`'s own `box` param, canonical frame). The head
is never a stray blob to guard against — it is `ev.subject`, already on
the record — so its own ink is removed from the band, never counted
either for or against a real rung's thinness. A band fully covered by the
head returns no evidence (`None`, same as "nothing here", never "thick").
`above`/`below` are now also carried separately in the row detail
(`adjacent_above`/`adjacent_below`), so a future tabulation does not have
to collapse them to guess which side was the blocker.

**Measured, same two pages, before vs after this fix, on the REAL
re-gather (not a replay):**

| plate | det_all pairs | ANY step found BEFORE | ANY step found AFTER | rows found BEFORE | rows found AFTER | confound-control FPs BEFORE | confound-control FPs AFTER |
|---|---|---|---|---|---|---|---|
| Litolff p3 | 23 | 1 | 2 | 1/37 | 2/37 | 0/0 | 0/0 |
| Brahms p1 | 82 | 19 | **43** | 22/119 | 62/119 | 0/11 | **2/11** |

Brahms more than doubled (19 → 43 of 82 pairs, 23% → 52%) — the adjacent-
exclusion fix is real and large, not a rounding artefact. **Litolff barely
moved** (1 → 2 of 23): the remaining blocker there is `left_dense`/
`right_dense` directly (28/23 of 37 rows, `wide_adjacent` dropped 32→20
but the DENSITY itself still fails on most rows) — visual inspection of 8
still-failing Litolff crops (`out/print/ledger-cv-first-2.37/litolff_
still_failing.png`) shows several that look like a note very close to its
own staff's outer line with only faint or no visible ledger at the tested
band, distinct in kind from the Breitkopf short-wing shape this lane
fixed — **flagged as a separate, not-yet-understood question for the
MERGING plate, not force-fixed by loosening a threshold with no positive
control for it.**

**Confound-control regressed slightly**: 0 → 2 false positives of 11 on
Brahms (own-staff distance ≈ 0, tested toward a neighbour — should stay
clean). Both are at the OUTERMOST step of a 4-rung ladder, where
`left_adjacent`/`right_adjacent`/`adjacent` all read `None` (the tested
band falls where NO evidence could be gathered, treated as "cannot rule
out thick" → passes by default rather than by a genuine thin-rung
reading) combined with `left`/`right` both independently clearing
`DENSE`. This is a `None`-defaults-to-pass gap the OR-relaxation (this
lane, round 1) made easier to hit by needing only one side, not a new
exclusion-guard bug — **flagged, not fixed**, since CLAUDE.md rule 8 says
a fix here needs its own positive control, not a same-session patch under
time pressure.

Tests: `test_staged_ledger_rung_ink.py::TestAdjacentExcludesTheHeadsOwnBox`,
6 new (RED by construction — `_exclude_head_box`/the `head_y0`/`head_y1`
parameters do not exist before this round) — the four pure boundary cases
(no overlap, full cover, overlap-near, overlap-far, no head box known) and
one end-to-end case: a real rung through a TALL synthetic head is refused
without the exclusion and found with it, on the identical ink.

Gate: fast tier 3,953 → **3,959** (6 new), 0 failed. `staged.check`:
**245**, unchanged.

**Crops read by eye, both plates, 8 still-failing rows each** (`out/print/
ledger-cv-first-2.37/{litolff,brahms}_still_failing.png` — committed;
the 4 `.record.json`/`.log` files these were cut from are NOT, machine-
local scratch same as every other lane's `out/print/*.record.json`):
Litolff's 8 mostly show a note close to its own outer staff line with
faint or no visible separate ledger at the tested band — a different
shape from the Breitkopf short-wing this lane fixed. Brahms's 8 mostly DO
show a real short stroke at the tested band (several visibly extend a
little past the head on screen) yet still read left/right density under
0.55 — center is consistently high (0.93–0.96), so these look like
GENUINELY very short or crowded wings (adjacent noteheads squeezed close
enough that `_true_ink_span`'s shrink or the overhang test itself may be
reaching into a neighbour's own ink) rather than the adjacent-guard shape
this round fixed. **Left for a follow-up round**, not force-fixed here:
CLAUDE.md rule 5, reach before accuracy, and this round's budget was the
one hypothesis the manager named.

### §2.37 addendum, round 3 — manager print check: Litolff tabulation, the rule-8 decline fix, and the slur hypothesis NOT shipped

**Litolff failing-condition tabulation** (per NOT-found `det_all` row,
same method as round 2's table, on a fresh `-v3` re-gather with round 3's
own code): 35 not-found rows total. **8 rows** match the manager's exact
hypothesis (one side clears `DENSE` — e.g. `right=0.70–0.79` — but is
blocked by its own `right_adjacent`/the wide `adjacent`, both reading
0.71–1.0). **23 rows** fail density directly on BOTH sides (`left`/
`right` both under 0.55) — center is consistently high (0.68–1.0) so
these look like a real rung crossing the head, but neither overhang band
clears the floor by any measure this lane has — a DIFFERENT, harder
question (Litolff's own MERGING plate, CLAUDE.md §10) that a slur guard
cannot touch. 4 rows are otherwise (a mix, not double-counted).

**Rule-8 decline fix, shipped** (`gather.ledger_rung_ink`, my exclusive
area): `_band_state` now distinguishes a band that is `None` because the
head's OWN box covers it entirely (`_exclude_head_box` — a KNOWN, SAFE
exclusion, e.g. a rung genuinely through the head) from a band that is
`None` because the raster genuinely has nothing there (a real gap,
`off_raster=True`). A side whose OWN density clears `DENSE` but whose
supporting adjacent evidence is a genuine gap on BOTH its bands is
`"unknown"`, not `"clean"` — and where no OTHER side clears outright, the
whole STEP now DECLINES (`ledger_rung_ink` returns `None`, the same
"cannot tell" signal `_observe_ledger_rung_ink` already turns into an
abstention) instead of asserting `found=True` from missing evidence.

**Measured**: of the two confound-control false positives round 2
introduced, **1 of 2 is now gone** (`glyph/1/1/3/6/0` toward
`staff/1/1/4`, step 4 — every adjacent read was genuinely `None`, exactly
the hole this fix closes). **The other (`glyph/1/1/0/6/0` toward
`staff/1/1/1`, step 4) remains** — read directly, its adjacent evidence is
NOT missing: `left_adjacent=0.0`, `right_adjacent=0.0`, `adjacent=0.0206`,
all cleanly read and genuinely low, with `left=0.723`/`right=0.53` both
clearing `DENSE`. This is not a rule-8 hole — the fix cannot decline over
evidence that is actually present and clean. It is a DIFFERENT, deeper
question (this is the OUTERMOST step of a 4-rung-deep ladder; whether a
walk this far from the note should be trusted at all, or whether the
confound-control's own premise — "no ledger toward an irrelevant
neighbour" — still holds at this depth) — **flagged, not solved**, out of
this round's budget.

**Slur-vs-beam hypothesis: investigated, NOT shipped.** Built `_within_
band_level` exactly as suggested (split one adjacent band at its own
x-midpoint, compare the two halves' row centroids, the same ruler the
existing cross-band slant check already uses). Wiring it to EXEMPT a
"not level" band from blocking flips the ONE real positive control this
lane has — `test_staged_ledger_rung_ink.py::TestARealPrintedRung`'s own
pinned, deliberately-unresolved step-1 finding (`ledger_rung_ink_brk_p22_
real.png`, a 2.6d fixture already documented as ambiguous ink, "the
staff itself, or ink the erasure left behind") — from a correct, cautious
`found=False` to an unverified `found=True`, using a within-band centroid
gap of 0.30 half-heights against the existing 0.2 threshold. There is no
confirmed real SLUR crop on either plate to calibrate the other
direction, and CLAUDE.md rule 7 ("who says it's right?") is exactly
against guessing that boundary under time pressure. `_within_band_level`
is built, documented, and its own note names precisely what a future
round needs (a confirmed slur crop) — but it does NOT gate `blocks`
this round; the adjacent guard is otherwise unchanged from round 2
(density-only). The 8 hypothesis-matching Litolff rows are therefore
**still blocked**, honestly reported rather than shipped on a guess.

**Net det_all rates, round 3 vs round 2** (real re-gather both times):
Litolff p3 unchanged at 2/23 (9%); Brahms p1 unchanged at 43/82 (52%) --
round 3 changed NOTHING density- or blocking-wise, only the decline path,
which by construction only ever turns a `found=True` into a decline
(never adds a new found). **Neither plate reaches the ≥80% finish line.**
Litolff's gap is dominated by genuine density failures on both sides (23
of 35 rows) — a GATHER-level question (is there really no usable wing at
these positions, or does `_true_ink_span`/the overhang anchor need
further work specific to Litolff's MERGING plate) that this round's
budget did not reach.

Tests: `test_staged_ledger_rung_ink.py::TestDeclineOnUnreadableAdjacent`,
3 new (a real rung whose adjacent bands are genuinely off a too-short
raster declines; the SAME geometry with the head's box declared over
those same bands is found, not declined; a confirmed thick blob is a
negative, never a decline).

Gate: fast tier 3,959 → **3,962** (3 new), 0 failed. `staged.check`:
**245**, unchanged.

### §2.37 round 4 — STOPPED, per Sean's redirect (not shipped)

An absolute width-comparison redesign (find the row-band's own contiguous
ink run, compare its width to the head's own measured ink width read away
from the rung) was built in response to the manager's round-4 brief, but
Sean's OWN redirect arrived mid-implementation and superseded the
question this whole width-test line was answering. Per his instruction
("stop the width-test round where it is; commit what's working"), the
round-4 rewrite was **reverted before commit** (`git show HEAD:... >
gather.py`, back to round 3's committed state, `94a35971`) rather than
shipped half-tested — it broke 9 of round 3's own pinned tests
(`center`/`left`/`right` fields it removed, and it flipped `TestARealPrintedRung`'s
deliberately-unresolved calibration case) and Sean's reasoning made the
whole absolute-threshold approach moot anyway (see round 5 below). The
attempt is not committed; this paragraph is its only record.

### §2.37 round 5 — Sean's redirect: ownership only needs a RELATIVE comparison

Sean, quoted (via the coordinator, redirecting away from every absolute-
threshold round above): *"pitch is geometric — staff spacing tells line
vs space for any note outside the staff; ledger lines always exist
between the note and its own staff. Pitch already works that way
(`restate_pitch` from `Q.NOTEHEAD_STAFF_POSITION`, no ledger read). So
the ledger reader is ONLY needed for OWNERSHIP of a note between two
staves, and for that we do not need to read every rung with absolute
thresholds."*

**Design, one comparison per contested head**: `gather.
_ledger_owner_informative_step` names the ONE ledger position adjacent to
the head toward each candidate, from geometry alone (the SAME `_ledger_
expected`-style arithmetic) — a head resting IN a space samples that
space's own ledger; a head standing ON a ledger is uninformative there
(the row is the head's own ink) and the step one further out is sampled
instead; a candidate needing no ledger at all is not tested.
`gather.ledger_owner_ink_density` reads the RAW ink fraction there — no
found/not-found threshold, the SAME window shape as `ledger_rung_ink`,
off the staff-erased raster, the head's box excluded. Filed as a NEW
quantity, `Q.LEDGER_OWNER_DENSITY` (added next to `Q.LEDGER_RUNG_INK` per
the lane's own fence; reusing `LEDGER_RUNG_INK` was rejected because the
value TYPE differs — a raw float density, never a bool — and conflating
them risked an existing consumer reading a density as a found/not-found
verdict). `ownership._ledger_owner_comparison` (ADJUDICATE) compares the
TWO candidates' own readings against EACH OTHER — self-calibrating per
plate, never a fixed floor across documents — deciding only where the
winning side clears a low floor (0.15) AND beats the other by at least
2×; comparable or both near-empty declines (a genuine reading gap).

**Wired as a witness, not a replacement**: asked FIRST in `adjudicate_
glyph_owner`, ahead of the existing completeness-based `ledger_direction`
(kept as a CORROBORATING witness, unchanged). Where the density
comparison decides AND the detector ladder ALSO has an opinion (`points`)
that DISAGREES, the glyph declines outright (`ledger_witnesses_disagree`,
added to `OWNER_NOT_READ_REASONS`) — neither witness is trusted alone.
Where they agree, or the ladder is silent, the density comparison's
answer stands.

**The all-rungs elimination rule (built rounds 2-3 on this branch) is
left OFF/unwired**, per Sean's instruction: `_contest_ledger_reading` no
longer computes or passes `refuted` to `ledger_direction`, so `_eliminate`
(still defined, for a possible future round) never fires
(`if not refuted: return fallback`). Three existing tests that pinned the
wired behaviour were updated to pin the UN-wired one instead (a plain
`far_no_rungs` gap where they used to expect `ledger_refuted`/`ledger_
all_refuted`) — noted in each test's own docstring so a future re-wiring
shows as a visible text diff, not a silent behaviour change.

**Measured on a fresh re-gather of both pages (`-v4`, real pipeline, not
a replay)**:

| plate | det_all 2-candidate pairs | agree | disagree | declined | confound-control heads | picked neighbour |
|---|---|---|---|---|---|---|
| Litolff p3 | 8 | **7 (87.5%)** | **0** | 1 | 0 | 0 |
| Brahms p1 | 39 | 10 (25.6%) | **0** | 29 | 77 | **0** |

**Zero disagreements and zero false picks on either plate** — the
mechanism is never wrong where it speaks, only sometimes silent. Litolff
(the MERGING plate) improves dramatically over every absolute-threshold
round before it (round 3's best was 2 of 23 det_all pairs, 9%; this is
7 of 8, 87.5%, on the pairs this comparison could even be run on — the
domains differ, det_all here requires a genuine 2-candidate contest).
Brahms declines far more often (29 of 39): 8 crops read by eye
(`out/print/ledger-cv-first-2.37/brahms_owner_density.png`) show why —
these are heads CROWDED between other noteheads on both sides in a dense
passage, and BOTH sampled positions read high density (0.68-0.86) because
neighbouring noteheads' own ink sits near both candidate positions, not
because a real ledger is ambiguous. The comparison correctly declines
rather than guessing between two contaminated readings — CLAUDE.md rule
8, and arguably the CORRECT behaviour for this plate's own texture, not a
regression to fix. 8 Litolff crops (`..._owner_density.png`) mostly show a
clean win: one clearly-inked position, one clean paper position.

Tests: `test_staged_ledger_owner_density.py`, 15 new (RED by construction
-- `Q.LEDGER_OWNER_DENSITY`, every new function and `ownership._ledger_
owner_comparison` do not exist before this round): the geometry
(on-ledger vs in-space vs no-ledger-needed, both directions), the raw
density measurement (a real stroke, nothing, off-raster), and the full
`glyph_owner` decision (a clear ratio decides; comparable ink and both-
near-empty are NOT decided by density, unaffected existing tiers still
apply; disagreement with a genuinely complete detector ladder declines;
agreement still decides; fewer than two readings never decides).

Also fixed along the way: `Q.LEDGER_OWNER_DENSITY` needed a `capture.
UNSCORED` classification (a NEW-UNCLASSIFIED finding `staged.capture`
correctly caught) — filed next to `LEDGER_RUNG_INK`'s own entry, same
shape (a scoreless RELATION, a ruler reading off the erased raster).

Gate: fast tier 3,962 → **3,977** (15 new), 0 failed. `staged.check`:
**245**, unchanged (the capture fix keeps it there; without it the check
would have gone to 246, `status=broken`).

### Questions for Sean (round 5)

1. Brahms's crowded passages (8 crops) decline correctly by this
   mechanism's own logic — is that the right call for those specific
   printed positions, or does the crowding itself need a narrower x-span
   than "head width ± a little" to separate a real rung from a
   neighbour's ink?
2. The confound-control (own-staff heads tested toward a neighbour) never
   picked wrong on either plate (0 of 77 Brahms, 0 of 0 Litolff — none
   qualified there) — is 77 a large enough sample to trust this at scale,
   or does it want a whole-movement re-gather before landing?
3. Should the un-wired elimination rule (`_eliminate`/`_ink_refutes_
   side`) be deleted outright now, or kept dormant for a future round
   that might re-purpose it (e.g. as a THIRD witness alongside density
   and the detector ladder)?
