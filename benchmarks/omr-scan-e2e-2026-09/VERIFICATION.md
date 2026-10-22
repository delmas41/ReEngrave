# The windows, and how each one was proved

Every measure window in `works.json` started as a first-pass visual count. This
is what it took to promote each to `verified`, and what one of them cost.

The rule this whole file exists to honour is in the first run's own findings:

> ⚠️ **The ground truth was wrong before the pipeline was.** The first run
> scored the page against seventeen measures; it has sixteen. … All five tacet
> staves agreed, and **the agreement was worthless, because they all print the
> same time signature and so all made the same mistake. Agreement across staves
> cannot catch an error every staff shares.**

So no window here rests on one kind of evidence. Each has an ink witness and a
witness that cannot fail the same way.

---

## The two tools

**`probe_page_measures.py`** counts full-height ink columns on a staff that
rests for the whole page — on such a staff almost the only full-height ink is a
barline. Generalised from the first run's version; the constants are carried
over unchanged, including the fix that separates a barline from a time
signature (*a barline continues past the staff into the gap, a meter stops at
the staff lines*: measured reach 1.00 against 0.05).

Two things changed, both forced by a second edition:

- **Staff bands are found here, not taken from the pipeline.** The original read
  them out of `staff_geometry` in the run it was checking. This finds five-line
  groups by horizontal projection and can draw them for a human to confirm. On
  Beethoven 5 p.1 the found bands land **within 2 px** of the original's
  hand-entered constants, which is the check that the substitution is fair.
- **The whole leading CLUSTER of left-edge furniture is collapsed, not just a
  pair.** On Dvořák 9 the Violino I/II staves carry a curly brace 2.4 staff
  spaces right of the initial rule and the trombone and timpani staves do not,
  so those two staves reported 9 measures against the others' 8 — while every
  *interior* barline agreed to within 6 px across all four. `BRACKET_MERGE_SPACES`
  went 1.6 → 3.0, past that brace and nowhere near music: the narrowest interior
  measure on any page measured here is 18 staff spaces wide. Beethoven 5 p.1
  still returns 16.

**`verify_window.py`** prints, from the reference, which parts *sound* in which
measure of the window and of the measures either side. A reader compares it to
the page. It fails on encoding differences and on transposition; it cannot fail
on a column of ink being mistaken for a barline. The measures *outside* the
window are the sharp end — they say what the page must **not** contain.

---

## Row by row

### Beethoven 5 / 984073 / p.1 → mm. 1–16 ✅

Ink: five tacet staves, 17 barlines each. The time-signature column at x≈832 is
**rejected on every one of them**, reach 0.00–0.09 against 1.00 for a real
barline — the 2026-08-31 correction reproduced from the ink rather than
inherited from the note.

Content: the trimmed window holds 147 visible note objects, which is the same
147 reference pitches `eval_first_run.py` scores against.

### Beethoven 5 / 575951 / p.1 → mm. 1–16 ✅

Ink: five tacet staves, 17 barlines / 16 measures.

**The barline fingerprint.** Normalise each page's 17 Flauti barlines to its own
system width and the two scans agree to a maximum of **0.0014** — 0.14% of the
system, about 5 px on the high-res scan:

| | 984073 p.1 | 575951 p.1 |
|---|---|---|
| system width | 1941 px | 3773 px |
| barlines | 17 | 17 |
| max normalised disagreement | — | **0.0014** |

Bar-by-bar spacing on an engraved page is a fingerprint; seventeen of them
cannot coincide to 1.4 parts per thousand unless it is the same engraving with
the same page break. So the window is shared, and the row is a controlled
comparison rather than two loosely-similar pages.

It also settles a question the scoping raised: 575951 really is Litolff plate
2769, reprinted with modern English running heads (`2 SYMPHONY NO. 5 (1)`). The
catalogue's identical provenance for the two files is substantively right.

### Dvořák 9 / 405834 / p.5 → mm. 1–8 ✅

Ink: four fully tacet staves (Tromboni I.II., Tympani, Violino I, Violino II),
all 9 barlines / 8 measures.

Content, which is the strong half here. The reference's mm.1–8 predict:
Viole/Violoncelli/Contrabassi sounding mm.1–4 then silent; Clarinetti and
Fagotti entering mm.3–4; Corni III.IV. mm.4–5; Flauto and Oboi entering mm.6–8;
Trombe, Tromboni, Trombone III, Timpani and both Violini silent throughout. **The
printed page shows exactly that.** And decisively, the reference has Violini I
and II entering at **m9** and Timpani at **m10**, and neither appears anywhere on
the page.

### Brahms 1 / 317803 / p.1 → mm. 1–7 ✅

**The ink probe abstains here and its number must not be quoted.** The page has
no fully tacet staff; the system's opening rule is rejected as too wide (it is
the bracket); and the final barline plus the cautionary meter's rule count as
two. Its near-tacet staves report 7, 9 and 9. The 7 it prints for the Pauken
staff is one loss cancelling one gain, not a measurement.

What carries the row instead is better than what the probe would have given:

- **A cautionary 9/8 is printed after the final barline on every staff, and the
  reference changes meter to 9/8 at measure 8.** The page ends at m7. This is a
  fact taken from the reference with no failure mode shared with counting ink.
- Content: the reference has C Trumpet 1/2 sounding in m1 and silent from m2,
  and the printed *2 Trompeten in C* staff carries notes in the first cell and
  then **exactly six** whole-bar rests. Six rests after m1 is seven measures.
  *Eb Horn 3/4* sounding mm.1–4 then silent matches the printed *in Es 3./4.*
  staff, and every part's density jumps at m8 (Flute 4 → 9 notes, Violin 1
  6 → 10) in a way the page does not show.

### Mahler 5 / local / p.2 → mm. 0–8 ✅

Ink: six tacet staves, 10 barlines / **9 cells**. The first cell holds a quarter
rest — the pickup — so the page is measures 0..8, which is the 9 measures the
trimmed truth contains.

Printed confirmation of the anacrusis, on the page itself:

> *) Die **Auftakt**-Triolen dieses Themas müssen stets etwas flüchtig …

*Auftakt* is upbeat, and the reference numbers that measure **0**, ql 1.0,
`paddingLeft` 3.0. Three independent things agreeing on the pickup: the printed
footnote, the encoded measure, and a quarter rest in a short first cell.

Two findings came out of this row and neither is about measure counting.

**The reference's pickup carries twenty invisible notes.** `verify_window.py`
showed m0 sounding on nearly every part, where the page prints a quarter rest on
every staff but the solo trumpet. They are notes with
`style.hideObjectOnPrint = True` — a hidden quarter (C♯5 on flutes, oboes and
violins, G4 on horns) in a second voice beside the visible rest. MuseScore
writes these for playback. **The page is the truth, so the trimmer drops them**;
charging the pipeline for failing to read a note the engraver marked invisible
is not measuring reading. Scale across the corpus:

| row | visible notes | hidden notes | hidden rests |
|---|--:|--:|--:|
| Beethoven mm.1–16 | 147 | 0 | 0 |
| Brahms mm.1–7 | 482 | 0 | 0 |
| Dvořák mm.1–8 | 93 | 0 | **19** |
| Mahler mm.0–8 | 27 | **20** | 0 |

Rests are deliberately not touched, and the distinction was checked rather than
assumed: Dvořák's 19 hidden rests are ordinary second-voice padding — two
players condensed on one staff, voice 2's duplicated rests hidden so they do not
print twice while its notes print normally. Removing them would leave voice 2
short. Beethoven and Brahms have neither kind, so the reproduction row is
untouched by any of this.

**The percussion is printed on one-line staves.** Below *Pauken*, each of
Becken, Grosse Trommel, Kleine Trommel and Tamtam gets a single rule with its
own 2/2 and a quarter rest. A five-line staff detector cannot find them by
construction, so `page.n_staves` records **17 five-line staves** and the
one-line staves are noted separately. Compare `detected` against 17, not 21.

### Bach Brandenburg 3 / 468678 / p.1 — dropped for tonight

Recorded rather than forced. It is a Bach tutti with no tacet staff anywhere, so
the ink probe has nothing to count on. The band finder reports 24 five-line
bands, consistent with **two systems of twelve** (3 Violini + 3 Viole + 3
Violoncelli + Contrabasso + Cembalo on two staves), each with its Cembalo set
apart by a gap — so the page total needs system 2 counted by hand.

System 1 *is* established: a narrow pickup cell (two sixteenths) plus four full
bars, confirmed by the boxed **5** opening the next block. Since this reference
numbers the **pickup** measure 1, system 1 is reference mm. 1–5 and the print
runs one behind the file. That is the row's whole reason to exist and it is
still worth doing — with the second system counted first.

---

## What is still soft

- `page.n_staves` for Brahms (14) and Dvořák (15) was read off a render by eye,
  not counted by a tool. Both agree with the reference's part structure, so an
  error would have to be a coincidence, but they are eyeball numbers.
- The band finder misses staves that are entirely empty and faintly printed —
  4 of Dvořák's 15, 1 of Brahms's 14. It does not matter here, because a missed
  band is a staff not offered for counting rather than a wrong count, and every
  band actually used was confirmed on an overlay. It would matter if someone
  reused it as a staff detector. It is not one.

---

## 2026-09-04 — Six rows promoted: the gate widens 5 → 11

Drafted on branch `claude/scan-gate-rows` (evidence assembly:
`ROW_VERIFICATION_CHECKLIST_2026-09-04.md`; drafts preserved there in
`works-drafts.json`), then verified by Sean against the print with the advisor
session pre-reading each page and cutting zoomed crops. Full evidence per row
is in each row's `window.verified_by`; the one-line stories:

- **beethoven-984073-p2 (mm 17–48).** The engraver's own numbers: 17 over
  system 1, 34 over system 2, 49 opening p.3. Sean confirmed the condensed
  bottom staff and refined the reading — "Basso" is the double bass sounding
  the lower octave, celli and basses sharing one staff from p.2 on. Known
  pipeline miss: the m19|m20 barline on this low-res raster (expect 31/32).
- **beethoven-575951-p2 (mm 17–48).** Same plates; the window transfers by
  plate identity (boundary fingerprint ≤ 0.0024). Confirmed: this reprint
  prints NO marginal measure numbers.
- **mahler-local-p3 (mm 9–16).** Peters prints 9 and 17, each twice. Thirteen
  five-line + two one-line staves, margins matching the draft word for word;
  the m13 ff tutti with "nicht teilen!" sighted.
- **brahms-317803-p2 (mm 8–22).** Printed 8 / 15 / 23; the m8 9/8 bar with
  6/8 at m9. The draft's one tool error — the (Es) Hr. margin misread as
  "Trumpet", silently dropping a horn staff from system 2's map — was
  hand-corrected, and the CORRECTION was what Sean verified: 13 staves, no
  Trpt., with the Es-horn and Pauken pp re-entries before rehearsal A exactly
  where the reference puts them (mm 21–22).
- **dvorak-405834-p6 (mm 9–15).** The one counting row (no printed numbers on
  this plate): 7 bars counted on the Flauti staff against a numbered-strip
  crop and consistent on the page-long-resting Trombe/Tromboni staves;
  strings ff at bar 1, Timpani at bar 2, the flute/oboe p flourish closing
  m15. The italic "32" over the Viola is a tremolo-subdivision marking —
  recorded so nobody ever reads it as a measure number.
- **bach-468678-p1 (mm 1–10, +1 numbering).** The parked row, completed by
  the engraver: boxed 5 printed twice (one system, two blocks) and boxed 10
  opening p.60 (also twice; p.60's second system prints boxed 14 — a free
  anchor for a future row). System 2's five bars counted; 12 staves per
  system, so the parked `n_staves: 13` is corrected to 24. The header's large
  "3" is the concerto number, not a measure number. ⚠️ Stress row: the
  current pipeline shatters this page (six "systems"); it will score terribly
  and honestly — that is its purpose.

⚠️ **The pooled figure changes meaning at this commit.** Every scan-e2e
pooled number measured before this widening — production 0.7517 / 7894 and
the shipped graft 0.7493 / 7872 — is a **5-row figure**, and comparing it to
any figure pooled over the widened set is invalid in either direction: the
same boundary discipline as the engraved benchmark's 3→11 widening. The first
widened baselines for production and the shipped graft are measured once,
directly after this commit, and recorded beside this file; because
`scan_eval.py` has no per-row pool-exclusion mechanism, the Bach stress row
enters the default pool, and the baseline record therefore states the pooled
figure BOTH with and without it — whether Bach keeps pool membership is an
open decision for Sean (the Boulanger precedent: a structure-failure row can
dominate a pool and turn it into a segmentation metric).

---

## 2026-09-04 — Bach excluded from the default pool (Sean's decision)

The Bach stress row stays in works.json, verified and runnable, and is now
marked `"pooled": false`: `scan_eval.py` runs and reports it per-row on every
default invocation but keeps it out of the pooled figure. Why: the pipeline
shatters the page (~6 "systems", 122 detected measures against a true 10), so
its OMR-NED measures page-structure parsing rather than recognition; pooled,
it contributed ~19% of the 11-row edit budget and CHARGED recognition
improvements as regressions (the graft found 326 more real symbols there and
paid +358 edits — whole-measure amplification on a shattered page). Same
call, same signature as boulanger-printemps-mvt1 in the engraved benchmark.

**The canonical scan-gate baselines are therefore the 10-row readings** from
WIDENED_BASELINE_2026-09-04.md: prior-prod (hollow-ft) **0.8457 / 29081**,
production (hollow-graft-shift09) **0.8387 / 29082**. The 11-row readings
stay recorded there for the row's eventual re-admission — which happens when
its segmentation reads ~10 measures, with a boundary note, since pool
membership changes what the pooled figure means. The fragments align with
the instrument choirs (3 Vni / 3 Vle / 3 Vc / Cb / Cembalo), so the row
doubles as the tracked stress metric for choir-grouped system layouts.

---

## 2026-09-05 — Bach re-admitted to the pool (Sean's decision, coupled ship)

`OMR_CHOIR_GROUPING` shipped default-ON and the Bach row's `pooled` flag
flipped back to true in the same event. The exclusion rationale no longer
holds: under the cues the page reads 2 systems [12,12] and 11 cells against
the true 10 (the +1 a pre-existing barline defect present in both arms), so
its errors are recognition-shaped. ⚠️ **Benchmark boundary:** from the
re-stamped baseline onward the pool is ELEVEN rows under the composed
default config (tilt localization ON × choir cues ON); every earlier pooled
figure (10-row 0.8387/0.8345 included) is on the other side of the boundary
and is never compared across it. The re-stamp run's figures are recorded in
the second baseline addendum beside WIDENED_BASELINE_2026-09-04.md.

---

## 2026-09-05 — Nine more rows promoted: the gate reaches 20, in continuous spans

Tranche 2 (drafted on `claude/scan-gate-rows-2`, checklist + 33 crops in
`crops-2026-09-05/`), verified by Sean against the rendered crops after the
advisor session pre-read every decisive crop. The engraver carried almost all
of it: Beethoven p3/p4 close on printed 49/65/83/98/113 (both twins, windows
transferring by the established plate identity); Brahms p3/p4 on printed
23/29/38-with-Allegro/48/59, including the corpus's first REPEAT BARLINE
(the m39–40 start-repeat, future repeat-export test material); Mahler p4/p5
on printed 17/24/32 (twice per page, as always on this Peters plate); Dvořák
p7 counted on numbered strips (mm 16–30) and anchored mid-page by the m23‖24
double bar + "Allegro molto. M.M. ♩=136" + 2/4-with-repeat-dots. The one
drafter correction — 984073-p4's two systems printing DIFFERENT lineups
(system 1: no Tp., Vcl./Basso split; system 2: Tp. restored, "Bassi.") — is
proven by the printed margins and reference-corroborated (Timpani's first
note exactly m98). Known pipeline miscounts recorded in the rows (the Mahler
p4 header sliver; 575951-p4's gained mm94–95 barline) are read facts, not
window facts.

⚠️ **Boundary: the pool becomes TWENTY rows at the post-reconciliation
re-stamp**, and no pooled figure crosses that line in either direction. The
11-row era's figures (0.8303 composed canonical included) are history the
moment the 20-row baseline is stamped.
