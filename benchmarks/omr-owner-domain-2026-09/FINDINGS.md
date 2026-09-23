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
