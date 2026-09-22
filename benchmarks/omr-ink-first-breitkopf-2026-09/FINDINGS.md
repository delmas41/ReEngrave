# The ink-first test on the SHATTERING plate — §7's falsifier FIRES

**2026-09-22, Lane D.** The governing document's own falsification test
(`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §7), run where that
section says it belongs. **Read-only: nothing under `tools/` changed.**

⚠️ **PROVENANCE.** The measuring session was refused a findings file — the
**fifth** time in this repo (see `benchmarks/omr-ink-first-2026-09/FINDINGS.md`'s
own provenance note, which records the fourth) — so its synthesis lived in its
commit messages. **This file is that record transposed at integration, verbatim
from `4f420417`, `b040808c` and `b5210bf4`**, following the precedent the
sibling lane set. `[mgr]` marks what the managing session re-derived itself.

**[mgr] What I checked against the tree before believing any of it**, because
this repo's record is that five of six agent reports contain a claim the tree
contradicts:

| claim | check | result |
|---|---|---|
| the branch is pushed | `git ls-remote --heads origin` | `27311d68` present |
| `b4eed4a4` exists and is on main | `git merge-base --is-ancestor` | **YES — the stale-premise finding is real** |
| nothing under `tools/` changed | `git diff --stat origin/main...<branch> -- tools/` | **empty** |
| the headline AUC | read from the committed `out/breitkopf-p0p3-main.txt`, not the report | `BOX ALONE: box width … AUC 0.061` → 0.939 direction-free, best ink axis 0.744 — **faithful** |

**[mgr] And the brief I wrote carried the stale premise.** I told this lane the
Breitkopf ink record "cannot be run there at all … it is one gather", quoting
the governing document. `b4eed4a4`, *on main since 2026-09-18*, had already made
one page of it. The lane found it with `ls benchmarks/ | grep -i ink` — **the
check that works when `git log -S` does not**, because a withdrawn or
partially-landed investigation changes no code.

---

## ✅ ADDENDUM — the FULL staged record landed, and it validates the shortcut

The lane reported on a **gather-only projection** while the full staged run was
still inside `adjudicate_glyph_owner`. **That run completed**:
`library/_shared-records/brahms1-breitkopf-p0-p3-ink.record.json`, **461 MB**,
md5 **`4df63a752df9d7cca3d916a67b37ebf4`**, provenance `27311d68` with
**`dirty: false`** — the tree was kept clean across the whole ~1h40m run for
exactly this.

**[mgr] Verified against the file itself**: the md5 matches to the character,
and the stamp reads `commit 27311d68`, `dirty: false`.

**It reproduces the shortcut in EVERY number** (`out/shortcut-vs-fullrecord.txt`):

| | shortcut | full record |
|---|--:|--:|
| ink rows / glyph_box / cells with ink | 15212 / 12932 / 818 | **identical** |
| subjects present, class agreement | 106/106, 1.000 | **identical** |
| junk / real / cannot_tell | 33 / 55 / 18 | **identical** |
| zero-coverage pieces | 8028 | **identical** |
| **all 15 AUCs, to six decimal places** | — | **identical** |
| residue strata | — | **identical** |

**So no figure in this lane is a property of the shortcut, and §7's falsifier
fires on the full pipeline's own record.**

⚠️ **THE RECORD IS STAMPED `OMR_DIRECTION_TEXT=0` AND `surya: false`.** That is
a legitimate choice for a long unattended run — CLAUDE.md prices the direction
reader at **~267 s/page on a scan for six accepted words** — and it is ON the
record. **But it means the configuration differs from the 2026-09-15 shared
Brahms record, and a lane comparing the two must read the stamp.**

⚠️ The **committed** artefact remains the 24 MB gather-only projection
(`out/…gather.json`, md5 `213bcb92…`), because `library/` is gitignored — which
is the property that lets a cloud session **with no weights and no `library/`**
re-run, extend or refute this test, and is why the 2026-09-18 lane committed
its single-page version the same way.

---

## The measuring session's own record, verbatim

§7 ON THE SHATTERING PLATE: the falsifier FIRES, and the blocking artefact was already half-made

The governing document's own falsification test, run where §7 says it belongs.
⚠️ A findings .md was REFUSED by the harness (the fifth time in this repo -- see
`omr-ink-first-2026-09/FINDINGS.md`'s own provenance note), so the synthesis is
here and the artefacts are under `out/`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN
ASSUMED: the breakthrough document's own claim, that the unit of enquiry should
be a piece of INK rather than an index into the detector's output list.
FALSIFIER: §7's own words -- "IF THAT TABLE COMES BACK UNDIFFERENTIATED ... THE
FRAMING IS WRONG and the detector's box is as good a subject as the ink."
Operationalised as: no ink-derived axis separates print-confirmed non-noteheads
from print-confirmed noteheads better than a feature of the BOX ALONE,
threshold-free, against a permutation null.
⚠️ NOT CONFIRMED WITH SEAN (he is asleep). Three calls are mine and flagged at
their sites: that `not_a_notehead` is the right target; that a box should be
attributed to an ink piece by fill-weighted overlap (BOTH arms are reported --
the choice moves the result); and the SPECK/BLOB boundaries, two of which are
INVENTED and swept rather than argued.

## 0. THE PREMISE, AND THE PART OF IT THAT IS 4 DAYS STALE
* `OMR_INK` default ON, deny-list -- CONFIRMED (`gather.py:_ink_enabled`).
* The committed `brahms1-breitkopf-p0-p3.record.json` (443 MB, 2026-09-15)
  carries `"quantity": "ink"` ZERO times -- CONFIRMED, with 12,933 `glyph_box`
  rows in the same grep as the positive control that the string form is right.
* ⚠️⚠️ BUT "it cannot be run there at all" IS NO LONGER TRUE, AND HAS NOT BEEN
  SINCE 2026-09-18. `b4eed4a4` ("THE BLOCKING ARTEFACT EXISTS") committed
  `omr-ink-first-2026-09/out/brahms1-breitkopf-p2.gather.json` -- 6,055 `Q.INK`
  rows on the shattering plate. It is ONE page of the four (pdf page index 1,
  named for the HUMAN page), and the print verdicts spread 16/22/29/39 across
  pages 0-3, so it covers 22 of 106. The blocker was half-closed and nothing
  said so. **Found by `ls benchmarks/ | grep -i ink`, which is the check that
  works when `git log -S` does not.**

## 1. THE ARTEFACT, now for all four pages
`out/brahms1-breitkopf-p0-p3.gather.json`, md5 213bcb92…, 24 MB, 67,546
observations, **15,212 `Q.INK` rows over 818 cells**. Receipt in
`out/RECEIPT.json`; copy at `library/_shared-records/`.
⚠️ It is a GATHER-ONLY projection, not a record: no verdicts. A full staged
run for the same pages was launched first and was still inside
`adjudicate_glyph_owner` (the O(n^2) step) when this landed.
✅ CROSS-GATHER CONTROL: page 1 reproduces the committed 2026-09-18 single-page
gather EXACTLY -- ink 6055=6055, glyph_box 3951, glyph_conf 3951,
notehead_class 1015, stem 792, cell_staff_space 202, beam_stroke 924, rest 350,
and the ink SUBJECT KEY SET identical, 0 on either side only. Two independent
detector runs, four days and one branch apart.

## 2. THE RESULT: §7's FALSIFIER FIRES ON BOTH PLATES
106 print verdicts, 106/106 present, 106/106 class agreement. 33 confirmed
NON-noteheads vs 55 confirmed noteheads (18 `cannot_tell` excluded) -- against
Litolff's 14 vs 29 with 63 `cannot_tell`, which is why §7 named this plate.

                          best INK axis      best BOX-ALONE axis
  Breitkopf, fill attrib   0.747 (CARVED)     **0.939** (box width)
  Breitkopf, area attrib   0.844 (MERGE)      **0.939** (box width)
  Breitkopf, all 3 passes  0.660 (CARVED)     **0.904** (confidence)
  Litolff (control)        0.736 (CARVED)     **0.937** (box width)

(direction-free |AUC-0.5|+0.5; 2000-draw permutation null per axis.)
**The box alone separates better than any ink-derived axis in every arm, on
both publishers, under both attributions.** That is §7's falsifying condition
in its own words.
⚠️ The box-width result is not new and that is what makes it credible: it
REPRODUCES `omr-notehead-width-2026-09`'s independently measured "box width
< 1.0 spaces catches 39 of 46 junk at a cost of 0 of 63 real" from a different
instrument. My Litolff empty interval sits at (0.769, 0.990).

## 3. ⚠️⚠️ THE ARRANGEMENT DOES MATTER -- the predecessor's method finding is
CONFIRMED, and it does not rescue the framing. Asked box-first, 2026-09-18 got
an undifferentiated table on Litolff. Asked INK-FIRST on the same record, four
ink axes DO clear the null (MERGE 0.734, CARVED 0.264, piece height 0.700,
piece width 0.294). So ink-first is genuinely more informative than box-first --
and still loses to the box.

## 4. THE FOUR-WAY SORT IS UNDIFFERENTIATED, which is the same answer again
Breitkopf: `not_a_notehead` sorts CARVED 19 / AGREES 8 / BARLINE 5 / SHATTERED
1; `stem_printed_down` sorts AGREES 35 / CARVED 1 / SHATTERED 1. The junk is
spread across three of the four shapes and the dominant real shape (AGREES)
holds 8 junk cases. ⚠️ The cuts are DERIVED from the confirmed-notehead
population's own percentiles, i.e. fitted to the plate, and are reported
because §7 asks for the table -- not as a proposed rule.

## 5. ⚠️⚠️ THE SAMPLE CANNOT ANSWER THE QUESTION CLEANLY, AND SAYING SO IS THE
METHOD FINDING. The crop pass sampled from the rejection census's buckets, and
on Breitkopf the junk is concentrated where geometry put it: `too TALL` is
12/12 junk and `at a CELL EDGE` 11/12, while `too WIDE` is 1/30 and `CONTROL`
1/16. So every pooled AUC above is inflated FOR INK AND BOX ALIKE. Within a
bucket holding both classes: on Litolff NO bucket has >=3 of each (DEAD); on
Breitkopf with all three print passes, three do, and BOX width (0.000) and box
h/w (1.000) separate perfectly in `NO component overlaps`, alongside one ink
axis each in two buckets. The answer survives the correction; the pooled
numbers should not be quoted without it.

## 6. THE RESIDUE SPLIT -- and it INVERTS the predecessor's own caveat
`omr-ink-extent` reported "42.5% of ink pieces have ZERO detections" and warned
"much of that will be specks and staff residue". Reproduced here to the unit
(3,019 of 7,093 = 42.6%) and then split:

  composition of the ZERO-COVERAGE population   Breitkopf   Litolff
    SPECK                                          66.9%      3.8%
    MARK_SIZED                                     28.4%     58.1%
    VERTICAL_TALL                                   3.2%     27.4%

**The caveat is TRUE on Breitkopf and FALSE on Litolff -- the very plate the
figure was measured on.** On Litolff specks are 3.8% of it; the mass is
mark-sized ink (58.1%) and tall verticals (27.4%, i.e. structural). The whole
populations invert too: SPECK is 42.8% of Breitkopf's pieces and 1.8% of
Litolff's, which reproduces CLAUDE.md's "Litolff MERGES and Breitkopf
SHATTERS" from a third direction. **So "42.5%" is not one fact and must stop
being quoted as one.**

## 7. CONTROLS, all able to fail, two shown failing
* A (document identity, class-agreement): PASS 106/106. Its positive control
  joins the OTHER plate's verdicts and REFUSES -- ⚠️ **38 of 106 Litolff
  subjects are PRESENT in the Breitkopf record by coincidence (36%)**, 4 of 38
  agreeing on class. The 2026-09-18 draft was caught by 11 of 26; on four pages
  the hazard is far larger, and it is the breakthrough document's own point (a
  subject's last coordinate is a positional index) arriving as a number.
* B1 (ink corners reproduce `width_spaces`): median error 0.0001 spaces over
  15,212 rows. B1' reads the SAME numbers as `[x,y,w,h]` and errs by 7.60
  spaces -- the control has TEETH rather than merely passing.
* B2 (glyph canonical w/h == page w/h): 0.0000 over 12,932 rows.
* Battery: **11 arms, 11 RED, 0 survivors**, restore hash-verified.
  ⚠️ Its FIRST run had 2 survivors and neither was a probe defect -- both were
  controls at their CEILING (class agreement already 22/22; neither side
  empty), so the probe gained `--wrong-join` and `--drop-junk` and those arms
  now run against them. ⚠️ Its own positive control then broke on a SUBSTRING
  COLLISION: the probe grew a within-stratum section printing `too few, DEAD`
  on healthy runs, and a bare `"DEAD" in output` guard declared the unmutated
  probe refusing. Repaired by spelling the terminal refusals out.

## 8. NOT ESTABLISHED
n = 2 documents, 2 publishers, 8 pages, BOTH SCANS; the engraved family is
untouched. **No print was consulted by this session** -- every verdict is the
2026-09-18 crop pass's, and its own `cannot_tell` rate is 58.9%/62.5% on
Litolff. 33 junk cases is the whole Breitkopf junk population. Nothing under
`tools/` changed, no record was re-adjudicated, no file was exported, no
OMR-NED. The residue strata are DESCRIPTIVE: nothing here shows a zero-coverage
MARK_SIZED piece is a missed mark -- that needs crops, and it is the ranked
next work. And the falsifier firing does NOT establish that the box is a GOOD
subject; it establishes that on these two plates the ink is not a better one.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>


---

## Addendum — the separating VALUES (commit `b040808c`)

The separating VALUES in the one bucket geometry did not choose — and the margin is 0.02 spaces

An AUC of 0.000 reads as "perfect separation" and says nothing about the
MARGIN. Printed rather than summarised, inside `NO component overlaps the head
at all` (the one census bucket selected on the ABSENCE of a component rather
than on any dimension, so box width is not correlated with the sampling there):

  box width, junk : 0.515 0.530 0.600 0.630 0.651 1.105
  box width, real : 1.128 1.316 1.720
  perfectly ordered, MARGIN 0.0227 staff spaces on nine cases.

So the headline survives the sampling correction and its evidence there is
THIN: an ordering claim, not a measured empty interval. Box h/w is ordered too
(margin 0.068); detector confidence is NOT ordered; and NO ink axis is ordered
in this bucket at all.

⚠️ It also shows why the probe's `widest empty interval` column must be read
beside the ordering: `ink_over_box` reports a gap of 558 that lies INSIDE the
junk population (0.95 … 10.7 | 569 … 763), not between the classes. The
function finds the widest gap in the COMBINED set, which is a diagnostic and
not a separator.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>


---

## Addendum — the tree check (commit `b5210bf4`)

Receipt: the ink layer this gather ran is byte-identical to origin/main

The base branch diverges from origin/main under tools/ (1,006 deletions), so
'I changed nothing' is not the same claim as 'this ran against main'. Checked
rather than assumed: the divergence in gather.py is entirely inside
gather_clef_seed (a dossier path this run did not take, dossier=None), and the
ink section md5s identically on both trees -- 70ba9808029f836d8b430f8f7056e68a.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>

