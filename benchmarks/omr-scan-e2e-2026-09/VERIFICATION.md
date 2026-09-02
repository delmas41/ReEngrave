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
