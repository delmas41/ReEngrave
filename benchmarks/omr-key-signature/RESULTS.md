# Key-signature reading — measured results

Everything here is reproducible from this directory:

```bash
python3 benchmarks/omr-key-signature/eval_key_signatures.py
```

Ground truth is `ground_truth.json` — the printed key signature of every staff
on three pages, read off the page by eye. That file is the irreplaceable part;
the rest regenerates.

The layer being measured is described in `tools/omr/README.md` → "Reading a
staff's header". Briefly: a key signature is N copies of one glyph at staff
positions fixed by the clef, so it is read by fitting POSITIONS to the slot
table for (clef, N) rather than by counting detections, and the readings are
then reconciled across the whole page.

---

## The headline: three layers, three different failures

Bach WTC p.17 — E major, four sharps on every staff of five systems, a clean
modern engraving where the detector fires on its own.

| | correct |
|---|---|
| counting the detector's markers (what the pipeline used to do) | 6 / 10 |
| fitting their positions to the slot table | 7 / 10 |
| …then reconciling across the page | **10 / 10** |

Each step fixes a different thing, which is why all three are needed:

- **The fit** rescued one staff whose five markers were the four real sharps —
  landing exactly on the bass slots [2, 5, 1, 4] — plus one stray above the
  staff. Counting reads five sharps; the fit sets the stray aside and reads
  four.
- **The vote** rescued three staves that had lost their FIRST sharp to the
  detector and read +1, +1 and +2. Nothing local can recover that: the fit
  requires the first slot to be observed, and lifting that rule is what once let
  two glyphs report five sharps. Only the page can say, and it does — the same
  part reads four sharps in the other systems.

## Degraded prints: the vote's real job is rejection

Beethoven 5 p.2 and Beethoven 6 p.2 — 19th-century orchestral prints where the
detector emits **zero** key-signature markers, so the CV locator is doing the
reading. 42 staves across both systems of both pages, with the true clef
supplied (see "What component mode does not measure" below).

| | correct | wrong | missed | correct abstentions |
|---|---|---|---|---|
| locator, per-staff | 14 | 6 | 14 | 8 |
| locator, after the vote | 18 | **0** | 16 | 8 |

The vote takes every remaining wrong answer off the page, and gains four
correct ones on top — it carries a part's reading from the system where it was
legible to the system where it was not. The trade it makes is `wrong → missed`,
and that is the right trade: a missed key signature leaves a staff where it
already was, a wrong one re-pitches every note on it.

The two staves that used to survive as errors — the Beethoven 6 clarinet, the
same part in both systems, printing one sharp against a page of flats — now
come back missed rather than wrong. Nothing structural can tell a transposing
part from a misread one, so abstaining is the correct end state for them, not a
lucky one.

Thirty-four of the 42 staves carry a signature, so this is recall of about a
half (18/34), up from about a third before the merge. Where the layer does read
a signature it reads it exactly: the three-flat staves come back with all three
accidentals matched at residuals of 0.03 and 0.24 steps against a half-step
tolerance.

---

## Retuning against the Phase-1 geometry (2026-08-28)

The clef-branch merge moved the geometry this layer was tuned against, in two
ways: `staff_detector._staff_x_extent` now bridges breaks of up to a staff
space, and `header_ink` strips heavy system rules as well as thin ones. The
figures above are AFTER retuning against that. Before it:

| the two orchestral pages, after the vote | correct | wrong |
|---|---|---|
| before the merge | 10 | 2 |
| after the merge, untuned (`efd59f7`) | 6 | 7 |
| **after this retune** | **18** | **0** |

Two faults, both of them "the geometry moved and a rule that assumed the old
geometry kept firing":

**The header window stopped containing the header on three systems of four.**
`staff_header._anchor_column` walked left from `Staff.x_start`, documented as
safe because the longest strictly-contiguous run "can only push it right". Gap
bridging removed that guarantee: the run now reaches back across the gap from
the system bracket to the instrument name, so `x_start` lands in the TEXT, and
a walk starting there never meets the bracket that was supposed to stop it.
`system_left_edge` takes the MINIMUM over the system, so one such staff set the
window for all eleven — 110 px too far left, which also stopped the window
being trimmed at the system's own initial rule instead of starting there. On
Beethoven 5 p.2 system 1 that window held the instrument names and no clef at
all, and the locator read the letters of "Fl." and "Cor." as key signatures.
The fix enforces the lost guarantee instead of assuming it: a full-band
vertical rule is the staff's left boundary, so an anchor left of one is outside
the staff and is moved past it.

**Any large piece of ink could be "the clef".** The locator anchors the run on
where the clef ends, and took that as the rightmost oversized cluster in the
window — but a beam, a slur and a stemmed note group are all oversized too. On
Beethoven 6 p.2 that put the anchor 13.6 staff spaces into a 16-space window,
and the "a key signature is printed hard against its clef" rule then licensed
ink nine spaces past the real clef. The two questions are now separate: a
cluster is skipped for being too big to be an accidental, but it only anchors
the run if it stands at the head of the window and has a clef's height. If
nothing does, the locator abstains — `clef_right` of 0 used to mean "the anchor
is at x = 0", which put the search window over the bracket and the margin.

### Correcting the earlier record

The note this section replaces said the merge regression "does not reach the
output", on the strength of Beethoven 5 p.2 reading identically either side of
the merge. That page does — its clef gate stays shut — but it was the only
orchestral page measured end to end, and the generalisation was wrong.
Beethoven 6 p.2 reads two staves in pipeline mode, and at `efd59f7` **both of
them were wrong**:

| page | mode | before (`efd59f7`) | after |
|---|---|---|---|
| wtc-p17 | pipeline | 10 correct / 0 wrong, 10/10 voted | 10 correct / 0 wrong, 10/10 voted |
| beet5-p2 | pipeline | 0 correct / 0 wrong, 0/22 voted | 0 correct / 0 wrong, 0/22 voted |
| pastoral-p2 | pipeline | **0 correct / 2 wrong**, 2/20 voted | **2 correct / 0 wrong**, 2/20 voted |

So this was a live defect in shipped output, not a latent one. The lesson is
the cheap one: a mode that "does not ship" only proves it on the pages you
actually ran it on.

### The window, measured without ground truth

Hand-read ground truth exists for three pages, which is too few to tell whether
a window fix generalises. `probe_header_windows.py` scores the WINDOW instead
of the reading — a staff counts when a clef-sized cluster stands at the head of
its measured window — which needs no ground truth and so can run over the whole
corpus:

```bash
python3 benchmarks/omr-key-signature/probe_header_windows.py --scores 20 --pages 3
```

Across 26 pages of 20 scores, **186/455 staves → 233/455**. One page of the 26
went backwards, by one staff, on a sub-staff-space shift in the left edge.

## What component mode does not measure

`--mode component` forces the CV locator onto every staff and hands it the true
clef. That is deliberate — it isolates the reader from clef detection, which is
a real ceiling on the end-to-end result and would otherwise hide what the reader
itself can do — but it is **not a score for the layer**, for two reasons.

**It bypasses the detector.** Component mode forces the locator onto WTC p.17, a
page the detector reads perfectly well; the pipeline scores 10/10 there because
it prefers the detector and falls back to the locator only where the detector is
silent. That ordering is the whole game on clean engravings, and component mode
inverts it. (The locator now abstains on all ten of those staves rather than
reading five of them wrongly, which is the right behaviour for a reader being
shown a page that is not its job — but it is still not a measurement of the
layer.)

**It supplies the clef.** In the pipeline the clef must be read, and a staff
whose clef is only the positional default is skipped, because a signature fitted
against a guessed clef is a guess squared — measurably: with every staff
defaulted to treble, two bass staves carrying three flats fitted cleanly as two
sharps. So end-to-end recall on degraded scans is far lower than component mode
suggests — two staves of twenty on Beethoven 6 p.2, none at all on Beethoven 5
p.2 — and key-signature reading **inherits the clef problem**. The two improve
together.

Use `--mode pipeline` for the number that describes what lands in the output.

---

## Reading the score columns

`missed` and `wrong` are kept apart everywhere in this benchmark and should stay
that way. They are not the same failure:

- **missed** — the layer abstained on a staff that has a signature. Costs
  recall; the staff keeps whatever it had.
- **wrong** — the layer asserted a signature that isn't there. Re-pitches every
  note on the staff for the rest of the system.

A layer that abstains is behaving correctly even when its recall is poor. Any
future summary that merges these two columns hides the property this whole layer
is designed around.

---

## Pages, and why each is here

| page | material | what it tests |
|---|---|---|
| `beet5-p2` | degraded 19th-c orchestral, concert C minor | three different written signatures for one concert key (3♭ / 1♭ clarinet / none for horns, trumpets, timpani) — breaks both naive counting and any "all staves agree" check |
| `pastoral-p2` | degraded 19th-c orchestral, concert F major | a transposing part printing the OPPOSITE accidental to the rest of the page (1♯ clarinet against 1♭) |
| `wtc-p17` | clean modern engraving, E major | the path where the DETECTOR fires, which the locator never reaches — and five systems of the same signature, so the cross-page vote is checkable by eye |

One caveat is recorded in `ground_truth.json` itself: Beethoven 6 ordinal 5
(Violino I) is read as one flat, but the flat is hard to make out at that
staff's print quality. It is marked `uncertain` in the file rather than silently
asserted.

---

## Beethoven 5 p.15 — why a C minor page read as C major

**2026-08-28.** The 2026-08-28 handoff reported this page as the evidence that
key-signature reading was broken: `0 sharps / 0 flats` on every staff of a
movement that prints three flats on most of them. Four separate things were
happening, and only the first was in the key-signature layer's control.

**1. The header was not in the window.** `_staff_x_extent` lost the staff's left
edge (see `benchmarks/omr-phase1-baseline/RESULTS.md`), so the clef and the
signature were cropped out of every measure cell. Nine of the twelve staves in
system 0 started between x=274 and x=773 on a system whose staves all begin at
x≈172. Fixed. Every header window on the page now holds its clef and its flats
— checked by rendering all 23 of them.

**2. Clefs followed immediately.** 0 of 23 read → **13 of 23** by the detector
in the pipeline, and 16 of 23 counting the detector's raw output on staff-start
cells. The key-signature reader abstains where the clef is only a positional
default, so this alone moved it from silent to speaking on 4 staves.

**3. The detector is blind to these flats, and it is not a threshold.** Running
the production weights over the 23 staff-start cells at 600 DPI:

| conf | key markers found | staff-start cells with one | clefs found |
|---|---|---|---|
| 0.25 | 3 | 2 / 23 | 16 |
| 0.10 | 3 | 2 / 23 | 21 |
| 0.05 | **3** | **2 / 23** | 28 |

Lowering the threshold by a factor of five adds **no** key markers while adding
75% more clefs. The cells are fine and the model simply does not fire on these
glyphs — a domain gap for this class on this print, measured on the current
tree with a correct window and the per-cell `imgsz`.

**4. The CV locator fragments them.** On s2 — a treble staff printing three
flats, plainly visible in its window — the locator finds exactly one
accidental-sized cluster after the clef, 0.35 staff spaces wide against a
flat's 0.7–0.9. The rest is either fused into the oversized cluster the clef
anchors on, or split below the size floor. That is why the fits fail: the runs
being fitted are not the signature.

**And the dossier cannot stand in.** `--dossier beethoven-sym5-mvt1` changes
nothing here: the work has 18 parts and the page has 23 staves, so the
part→staff join abstains, as designed.

### What this leaves

The output no longer asserts C major on a C minor page — `key_signature_read`
is false on the 19 unread staves, with the reason on each. The remaining work
is **the locator's ink mask on degraded prints** (why a printed flat arrives as
a 0.35-space fragment), or **a part→staff join that survives condensation**
(18 parts, 23 staves). It is not a threshold, and it is not inference from the
music: the printed signature is sitting in the window, legible to a human,
unread by both readers.

Reproduce: `benchmarks/omr-key-signature/probe_header_windows.py` for the window,
and the conf sweep above with `tools/omr/yolo_detector.py` over the staff-start
cells of PDF page 14 of IMSLP984073 at 600 DPI.
