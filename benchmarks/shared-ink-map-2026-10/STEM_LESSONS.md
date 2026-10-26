# Stem lessons we already paid for (read-only survey for ROADMAP 2.204, 2026-10-26)

Sean, 2026-10-26: "the lesson for stem strokes sounds like lessons we already learned with our current stem readers.
We should check those and see what can be ideas along with what we have learned."

Scope: STAGED unless a line says LEGACY (the finder `line_detection.detect_stems`, `_drop_paired_strokes`, `refuse_owned`
are shared GATHER code that both paths read). Sources are the tree: the stem benchmarks under `benchmarks/omr-stem-*`,
`omr-beam-confirm-2026-10` (2.146, 2.155), `omr-head-fill-2026-09` (2.71, 2.78, 2.137, 2.161), `omr-bar-sum-holdout-2026-09`
(2.141, 2.150b), `omr-unseen-symbols-2026-10` (2.179), `omr-unison-two-voices-2026-10` (2.175), `shared-ink-map-2026-10`
(2.194, 2.202; 2.204/2.204c on `origin/crop-2.204`; 2.205 on `origin/lane-2.205-stroke-owner`), `staff-eraser-2026-10`
(2.206, `origin/lane-2.206-staff-eraser`), `docs/DECISIONS.md`, `docs/page-facts.md`. I read each file's findings and the
sections named below, not every line; every number is quoted from the file named, none is mine. Where I judge, I say "my read".

**Count by kind (Sean, 2026-10-26: "make sure all ink is accounted for one time"): 10 CONVENTION (A), 2 ERASURE WORKAROUND (B, retire with 2.206), 4 DOUBLE-COUNT WORKAROUND (C, retire with 2.205).** Each lesson below is exactly one kind.

Kinds. **A CONVENTION**: a real engraving fact or reading rule; the stroke rule must carry it. **B ERASURE WORKAROUND**: exists because the staff-line eraser shaved ink; lane 2.206 fixes the eraser. **C DOUBLE-COUNT WORKAROUND**: exists because one ink was boxed or measured twice; the ownership step (2.205) retires it. Scope is stems only. A cut-off in any lesson is a one- or two-plate measurement and may only narrow (CLAUDE section 4); print each.

## Lessons

**L1 [A]. The stem ink is almost never missing; it was refused or never attached.** 2.17 `omr-stem-ink-2026-09`: the "90% of
stems missing" was 34% (793 of 2,347 Litolff heads) and 46% on Breitkopf; 95.8% / 93.1% of those heads had a vertical run
>= 1.75 sp beside them. "There is ink" alone was nearly content-free (its own control said so); the convention (right-up,
left-down) agreed with already-read stems 95.9% / 98.2% and spoke for 1,125 heads. The 2.195 stroke map confirms it from the
other side: `Q.STEM` is covered 100% by vertical strokes. So the simplified rule starts from ink that exists; its risk is the
join, not the finding.

**L2 [C]. Two stems eaten by the accidental rule (LEGACY+STAGED `_drop_paired_strokes`).** Two verticals within 0.9 sp
were deleted as a sharp's two strokes. `omr-stem-pair-rule-2026-09`: 244 strokes deleted, of the 80 carrying a head 62 (77.5%)
were paired with another stem-with-head (Litolff sets seconds and chords tighter than the LilyPond fixture the rule was proved
on); 73 heads (9.2%) stopped abstaining without it. The gate "overlaps a head box" (`omr-stem-notehead-gate`) fixed the plate
but inverted on the fixture (it keeps a sharp's stroke; per-bar 7 vs 3). 2.169 (`omr-stem-refusals-2026-10`) restated it as the
convention "a stem ENDS at its head; a sharp/natural is two verticals ~0.5 sp apart reaching past the head at both ends": 346
Litolff / 280 Brahms no_stem heads gained a stem, 0 on an accidental box; Sean's 2.167 tiles 1/3/5/7/9 were real left stems (5 of 5
connected). Under strokes there is no pair-deletion, and 2.205 gives the accidental its own strokes first, but the test that
separates the two things is still "ends at a head vs reaches past it at both ends".

**L3 [A]. A stem is one stroke shared by every head on it.** 2.169-era `omr-stem-attribution-2026-09`: the claim "148 / 228 heads
take a direction from a stroke that is not theirs" came from a chord test that required a companion above AND below; an octave
pair has one, so it failed by construction. Sean on the first strip: "it is an octave of C's and the stem belongs to both."
Corrected, the suspect group fell to 51 / 14. Sean 2026-10-26 repeated it for stacked and displaced heads (page-facts). This is
the base of the simplified rule and it has been correct every time Sean looked.

**L4 [B]. Size a fault before building for it.** `omr-stem-run-split-2026-09`: Sean's diagnosis "two stems measured as one"
was right, and the lane found it reaches 3 vertical runs of 4,225 and at most 13 of 5,684 heads (0.23%); nothing was built. The
same shape returns in 2.169/2.204 as "two collinear halves cut by a beam or ledger rung": count it first (2.204 counts it as
one stem with cuts 0.3 / 0.6 sp, unfitted).

**L5 [A]. Direction: the head's own attachment beats a neighbour, and side alone fails in chords.** 2.17 shipped a beam-mate
tier (direction borrowed from a head on the same beam; 0.984 measured on Litolff only). `omr-stem-crop-pass-2026-09` put the
26 Breitkopf heads where attachment and beam-mate disagree to the print: attachment 16, beam-mate 0 (8 cannot tell, 2 are dots);
Sean-style convention "right-up, left-down" held 96 of 96 printed stems. Then 2.204c, Sean's 12 tiles: every boxed note has a
stem; shared stems with a second put heads on both sides, so the side rule cannot read them; the direction is the tip beyond the
outer head. Both lessons agree with Sean's new proposal (direction afterwards, from the tip). Trap [3]: a stroke that reaches
past the heads at both ends has no obvious free tip.

**L6 [A]. Barline versus stem (2.155, 2.204c).** The finder refuses a run within 0.8 sp of the cell edge and one taller than 8 sp
(`STEM_MAX_HEIGHT_LINES`, a number measured on single-note stems; 2.202 found the 4,260 verticals that coincide with a `Q.STEM`
row are 1-8 sp). 2.155 (`omr-beam-confirm-2026-10` section 10): the last note of a Litolff bar stands 0.26-0.74 sp from the cell
edge, so real stems were refused (190 Litolff stems rescued; Sean's 20 tiles went 12/3 to 12/5, then 18/2 after tightening). The
rescue rule that held: a stroke at the edge that ENDS in its own head and passes through no other head. What went wrong first: a
stroke that ends in one head and passes through another read as a down stem of five heads (tile 9); a rescued stem fed the beam
reader a false second beam (tile 4, tile 13); 3 of 18 sampled rescues were barlines ending in a 0.3 sp sliver head box (a box
the cell edge cuts says nothing about whose head it is). 2.204c: the 8 sp cut called all 6 sampled long chord stems (8.2-9.9 sp)
barlines; none was. Breitkopf's "too tall" bucket (476 heads) was 12 of 12 barlines boxed as heads (stem-crop-pass). So a long
stroke touching a head is a stem or a barline and length alone decides neither; a simplified "touches a notehead" rule inherits
the barline problem at both plates.

**L7 [C]. The head's box is not the head's ink; stems fuse with it.** 2.161 (`omr-head-fill`, section 17): the finder found
the stem but it stood 0.13-0.27 sp beside a box that stops short of the head's stem side (S1: 9 of 32 Litolff unread halves);
`OMR_HEAD_STEM_BRIDGE` (gap <= 0.35 sp, one plate) is ON. 2.204 first gather (`origin/crop-2.204`): a Litolff vertical stroke
keeps the head's ink fused to it (up to 1.2 sp wide), read as a stem running through the head: 510 `through_head` abstentions.
Fix: place a fused stroke's stem at its tip end (median error 0.09 sp against the finder; 0.41 for the box centre) and demand
flush with the box edge. 2.204c: in 5 of 9 `wrong_side` cases the stroke was head+stem, its side read off a box centred away from
the stem. Touch must be measured against the head's ink and tolerate a small gap, not against the detector box or a stroke's box
centre.

**L8 [C]. A false rest, flag or letter box sat on real stems.** `refuse_owned` took 58 / 126 real stems away; 2.150b
(`omr-bar-sum-holdout`): rest boxes that are one thin stroke running into a notehead are stems (Sean's tiles: "stems of quarter
notes"; 15 of 21 stems); 2.182a tile 2 "tip of an 8th stem" was boxed as a rest; the rule that held: a rest never touches a note
(2.150b/2.33c). 2.205 bypasses `refuse_owned` for the stroke reading, so a stem under a false box is found. But 2.205's own
first milestone found the same mistake the other way: a Litolff flag boxed `dynamicF` took the eighth's flag (right-to-wrong), so
the claim order must let a head's touching stroke outrank a rest or letter claim. 2.205 also lists 247 / 246 finder stems it
would give to a mark (accidental 44 / 150, dynamic 112 / 46 unjudged): tile them.

**L9 [A]. A whole note has no stem.** Sean 2026-10-09, 2026-10-19: whole notes never have stems; a whole-class box a stem touches
is never a whole; a hollow head with nothing on the stem is a half. 53 of 56 whole notes in one export were not notes. 2.204
already treats `whole_head` as "show the stroke, never make it the stem". With a simplified rule the stroke still touches the
whole head's box in real print (the neighbour's stem, a barline, a rest's stroke), so "touches a notehead" must exclude whole heads
or it makes stems for notes that have none.

**L10 [A]. A tremolo slash is not a head and not a beam.** Sean 2026-10-01/09/15: a notehead's ink lies on ONE side of its stem; a
thick diagonal line crossing both sides of one stem and joined to no other note is a slash. 49 slashes stood as heads (Brahms 37,
Litolff 12) before `OMR_SLASH_AT_STEM_END`. A slash box touching a stem makes "a stroke that touches a notehead" true for the
wrong reason, and the real head is elsewhere on the stem. 2.205 found the opposite trap: real chord heads beside their stem read as
slashes (56 / 204 strokes); a slash is a line (length / thickness >= 2.5) crossed in its middle.

**L11 [A]. Grace notes have short stems and take no bar value.** Sean 2026-10-16: grace notes are significantly smaller and never
count in the bar. 2.155 tiles 6 / 11 / 13 (three Brahms grace notes) were wrong in BOTH arms: the rescued "stem" is the grace
note's own ~1.2 sp stem, and the note gained a stem and dropped to a quarter or eighth. The finder refuses runs under 2 sp, the
2.204 stroke needs 1.5 sp; a simplified rule at 1.0 sp would admit grace stems and need a size test for the head
(`omr-grace-notes-2026-10/RESEARCH.md`: grace stems point up by default, even among down-stem notes).

**L12 [A]. Every stem has a head at one end; an orphan stem is an unseen head.** 2.179 (`omr-unseen-symbols-2026-10`, section 4):
a stem with no head at either end triggers a second, lower-threshold detector read at the end the direction gives; Sean's tiles
8 of 9 new boxes real (tile 12 part of a rest). Litolff +108 notes, 37 red bars cleared. With strokes this is free: a stroke no
head touches is a candidate, never a stem (rule 6), and is the place to look.

**L13 [A]. A head with a stem each side is two notes; two voices share heads.** Sean 2026-10-19 (2.175): all 10 shared heads were
two notes, each valued from its own stem; 2.141h `OMR_OWN_STEM_UNISON_BOTH` ON; 2.169/2.204 call it `two_stems` (a stem each
side, each ending in the head; two same-side strokes are `ambiguous`). The simplified rule's "every head touching one stroke
shares it" must be per stroke, not per head: a head touching two strokes owns two stems, and a stroke belonging to the other
voice must not be shared into the first voice's chord just because a head of a second touches it.

**L14 [A]. Direction feeds three later readers.** Articulations sit on the notehead side opposite the stem (Sean 2026-10-09, 2.12f;
2.12m: an articulation at the tip of a long chord stem is the chord's); an augmentation dot goes in the space below for the lower
(stems-down) voice (2026-10-14). A direction read wrong or unread is an error in those, so a direction that is a guess must carry
its candidates (CLAUDE section 4).

**L15 [B]. The tip window and the staff-line eraser.** 2.146: a clean stem tip decides "no beam", 33 of 33 tiles, 74 of 74 with the
hand-truth page. 2.204 first gather: 4 right-to-wrong dotted quarters because 1.9 sp staff-line remnants touching the stem 2-5 sp
from its tip sat inside the 3.3 sp tip window and read as flags; fixed by using only strokes that start at the tip. 2.206
(`origin/lane-2.206-staff-eraser`, `OMR_ERASER_FIX` OFF, three measures not yet run): the eraser's walk reaches past its crossing
cut, so a mark hanging from or standing on a line loses up to 0.37 sp; 159,313 of 12.4 M Litolff line columns, 153,744 of 16.6 M
Brahms; lost ink on the black-head-in-a-space class 338k px (Litolff) and 906k px (Brahms) on main. Fifteen readers carry local
workarounds for "the erase thins or splits ink", including `HEAD_STEM_GAP_SPACES` ("a staff line erased or thinned") and the tip
reader's `STEM_TIP_HOOKS_CLOSE_SPACES` healing. Stems cross lines as tall runs and survive; the exposed spots are a stem's two ends
(head junction and tip) when they sit flush on a line, and any halves a line splits.

**L16 [C]. A new reader that vetoes the old one needs the old one's crops, not just geometry.** 2.204 first full gather: Litolff
notes -713, Brahms -983, right-to-wrong 4. 2.204c crop look of the 167 `disagree` abstentions (24 sampled): finder right or both
right in 22, strokes never right (0), 2 cannot tell, so about 165 decided notes were unread for nothing. Causes: fused head+stem
side (5 of 9), a second's displaced head (2), a chord stem called a barline (6 of 6), a neighbour's stem on a beamed group (9 of 9
"not a stroke"). The silent-map case is not a disagreement either (rule 8 both ways). All six cut-offs of 2.204 were stated before
any count, not fitted; the fail-fast subset that passed was not the full sample.

Notes on the kinds. L2 is C because its job was to stop an accidental's two strokes counting as stems; the useful test it
carried, "a stem ENDS at a head, an accidental reaches past it at both ends", is a convention and is carried by idea 1.
L4 is B because the collinear halves it sizes (3 of 4,225 runs) are cut by a ledger rung or an erased line and join with a 0.3 sp
gap. L7's bridge (0.35 sp) and fused-stroke placement exist because box and stem ink were measured as one thing. L16 is C because
the finder and the strokes were two measurements of one stem. L15 (the 3.3 sp tip window read flags from line remnants; 15 readers
carry workarounds for "the erase thins ink") retires with 2.206; do not build a tip workaround, and read the tip result only with
`OMR_ERASER_FIX` known (ON and OFF). 2.206's three measures are not yet run (disk), so B retirement is a prediction until they are.

## Ideas for the simplified stem rule (no new mechanism; each is a convention it must carry, tied to a lesson)

1. **Heads group by stroke; all heads touching one stroke share it; direction is read from the stroke's free end (A: L3, L5, L13).**
   A stroke that reaches past the touching heads at BOTH ends is not their stem (L2's test): keep it as a candidate, never a stem.
2. **A stroke that ends in a head is a stem at any length; a stroke touching no head at either end, or spanning the staff, is a
   barline (A: L6).** Length (the 8 sp cut) decides neither; a head box the cell edge cuts says nothing.
3. **Whole-class heads take no stem (A: L9); a slash is not a head (A: L10); two strokes on opposite sides of one head are two
   stems and two notes, two on the same side are ambiguous (A: L13).** These are the exclusions "touches a notehead" needs.
4. **Until 2.205 lands, the finder's stem stands where the stroke rule disagrees (C: L16)**; the rule only adds (`gained`) or
   confirms. Right-to-wrong must stay 0. After 2.205, ownership removes the three known causes (fused side, chord-as-barline,
   neighbour's stem) and the disagreement path can go.
5. **Touch is measured against the head's ink, not the detector box, with the 2.161 bridge gap (C: L7); a rest, letter or flag box
   may not take a stroke a head touches (C: L8).** These are retired by 2.205's order; they are listed so they are not rebuilt.
6. **Control before any gather: replay Sean's 12 answered 2.204c tiles, the 2.167 left-stem tiles 1/3/5/7/9 and the two
   "stems of quarter notes" tiles (2.150 tile 11, 2.150b tile 20).** A control that can fail on data we already have.
7. **Print heads by number of strokes touched (0, 1, 2) and by state, per plate, before the first milestone gather.**

Trap not solved by the simplified rule alone: grace notes (A: L11). Their stem is ~1.2 sp and the finder/2.204 minimum is 2 / 1.5
sp, so they stay unread; lowering the minimum without a head-size test turned three Brahms grace notes into quarters or eighths
in BOTH arms of 2.155. Leave the minimum alone and count them. Orphan strokes (A: L12) stay candidates for the existing 2.179
re-read; they are not made stems.

## Open questions for Sean

1. A long vertical that reaches past the touching heads at both ends (note heads in the middle, nothing at either end): is that
   ever a chord stem in your scores, or is it always an accidental, a barline, or the other voice's stem?
2. A very short stem (about one space) beside a small notehead: is that always a grace note's stem, so it takes no value in the
   bar, even when the grace note has no slash?
