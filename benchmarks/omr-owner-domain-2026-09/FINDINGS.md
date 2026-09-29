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
