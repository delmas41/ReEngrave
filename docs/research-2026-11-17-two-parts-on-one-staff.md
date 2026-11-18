# Research 2026-11-17 — how two parts share one staff, and the loosest correct model

ROADMAP 2.314. STAGED. Asked for by Sean (DECISIONS 2026-11-17, "LOOSEN HOW WE THINK OF MULTIPLE VOICES").
A research agent's report, filed by the manager. **Nothing here is a page fact until Sean has confirmed it**;
the questions in §7 are his. Status: input to the redesign of the voice model, no code.

## Cause, and what it teaches

The reader treats a bar with two stems at one place as two complete voices that must each fill the bar. That
is a software idea, not an engraving rule. Every reference reached describes a shared staff as ONE line of
time with two players on it: marks are shared where possible and split only where the players differ.
LilyPond's part-combiner works the same way, switching between chord, apart, unison and solo note by note.
Lesson: we took our model of the texture from the file format (MusicXML voices), not from the print.

## How far to trust the sources

- Gould, *Behind Bars*: text NOT opened. Table of contents confirmed ("Double-stemmed writing", "Two players
  on one stave", "Stave sharing", "Multiple rests"). Quoted second-hand: "Separately stemmed parts share rests
  wherever possible" (p. 528, via a forum thread that could not be opened; NOT verified).
- Ross, Read, Stone: nothing opened; own knowledge only, labelled where used.
- MOLA guidelines: opened; they only say not to share a staff in PARTS; nothing about scores.
- Opened and confirmed: LilyPond notation reference (multiple voices, part combining, merging rests), the
  MusicXML `<forward>` / `<backup>` reference. Search summaries only: Dorico help, MuseScore forum.

## 1. The cases, as printed and as a player reads them

1. One stem for both (a chord): upper head player 1, lower player 2, same rhythm.
2. Split stems throughout: stems up player 1, stems down player 2; each line has its own rhythm and rests.
3. Split for part of the bar only: shared stems or a shared rest, then a divide (or the reverse). Each player
   follows the shared marks until the split, then their own stem direction.
4. One part rests while the other plays: modern practice prints the resting part's rest displaced to its side;
   in 19th-century scores it is often simply not printed (own knowledge).
5. Both rest for part of the bar: one rest in its normal place serves both.
6. Both rest the whole bar: one whole rest serves both (Sean's ruling, page-facts §1).
7. Unison, two stems on one head: both play; two stems show both lines continue.
8. Unison, one stem + "a 2": both play; "a 2" is often left out in 19th-century plates (own knowledge).
9. A long note under moving notes: the long note keeps its own stem direction (or none, a whole note) and
   covers its full value in that player's line.
10. A part that stops being shown: no mark for one player for a stretch (under "1." / "Solo", or unlabelled in
    older scores). The player reads silence.

## 2. Rests

- Printed ONCE for both when both rest for the same length at the same moment, at the rest's ordinary height.
- Printed SEPARATELY when only one rests or the lengths differ: upper player's rest high, lower player's low.
- Telling them apart: height (normal = shared, raised = player 1, lowered = player 2); company (a rest sharing
  its beat with a stemmed note belongs to the other player); count (two rests stacked at one beat = one each).
- A shared rest on beat 1 and split stems on beat 2 is legitimate: "share wherever possible".
- A player left incomplete with no rest printed: reported as allowed where the context is clear (unverified);
  common inside a bar in 19th-century Breitkopf / Litolff scores (own knowledge -- Sean's 24 bars should confirm
  or refute it).

## 3. Changing texture inside a bar

No reference forbids switching between shared and split stems inside a bar; LilyPond re-decides at each note.
When only one set of marks is printed the second player inherits the shared mark's value and place (its pitch
for a unison, the lower head of a chord; silence from a shared rest). A single line in ONE player's stem
direction with no partner gives the other player nothing: silence that is not printed (own reasoning).

## 4. The loosest correct model

**One line of time per staff. At every moment one or two players are sounding. Each mark speaks for both
players or for one, and only a second mark at the same moment can split them.**

- A mark with one stem, or a chord on one stem, speaks for both -- unless a second stemmed mark or a displaced
  rest stands at the same moment. Never split one stem into two rhythms.
- Two stems at one place: up is player 1, down is player 2. Never read a down stem in a split column as player 1.
- A rest at its normal height with nothing else at that moment speaks for both. Never let it silence only one.
- A raised or lowered rest speaks for one player only. Never read it as silencing both.
- One head with two stems is both players on that pitch. Never count it as one player.
- A split may begin or end at any beat in the bar. Never require a bar to be all shared or all split.
- A player may have no printed mark for a stretch: silent, not printed, recorded as such. Never invent a rest.
- One whole rest when both are silent all bar. Never require two.

Boundaries where two readings both fit: a second on one stem (higher head right of the stem = shared stem;
left, or two stems = two players); a rest slightly off its normal height (shared, or displaced for one --
measure against the staff locally); a lone single-stem line after a split (both again, or one alone -- stem
direction against the pitch's normal direction points to one player).

## 5. What "the bar adds up" should mean

- MUST sum to the bar: the staff's line of time -- every moment covered by at least one mark, sounding or
  resting.
- NEED NOT sum to the bar: each player separately. A shortfall is "silent, not printed".
- Still wrong: overfull (a player's own marks plus the shared marks covering them run past the barline); a gap
  (a moment no mark covers); a collision (two marks claiming one player at one moment with different values).

## 6. Writing it without inventing rests

MusicXML: shared stretches in voice 1 (a chord for a shared stem, one rest for a shared rest); for a split,
voice 1, `<backup>`, voice 2; where voice 2 has no marks, `<forward>` with `<voice>2</voice>`. Avoid invisible
rests (they state that a rest exists). Pitfalls: importers may display rests in the empty spans; part
extraction loses shared tones that live only in voice 1; a unison written twice plays doubled.
LilyPond: one voice with chords, a temporary `<< { } \\ { } >>` only for the split stretch, spacer rests `s`
for a voice's gaps, `Merge_rests_engraver` for shared rests. `\partCombine` needs each player's complete line,
which is INFER work and must be labelled.

## 7. Questions only Sean can settle (one look at a bar each)

1. When a bar goes from split stems back to single stems with no "a 2", are both players playing, or one?
2. When a rest sits only a little off its normal height next to one player's notes, is it the partner resting,
   or both?
3. Where player 1 continues alone after a split and no rest is printed for player 2, is player 2 silent for the
   rest of the bar -- and is that normal in these editions?
4. Does one head with two stems ever mean anything other than both players on that note?
5. Where one player holds a whole note under the other's moving notes, is it player 2's alone, or shared?

## Sources

- LilyPond NR, Multiple voices: https://lilypond.org/doc/v2.24/Documentation/notation/multiple-voices
- LilyPond Internals, Merge_rests_engraver: https://lilypond.org/doc/v2.24/Documentation/internals/merge_005frests_005fengraver
- lilypond-devel 2014 (unisilence): https://lists.gnu.org/archive/html/lilypond-devel/2014-11/msg00202.html
- MusicXML 4.0 forward / backup: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/forward/
- Dorico help, implicit rests in multiple-voice contexts (search summary only)
- Dorico development diary part 5 (cites Gould p. 37): https://blog.dorico.com/2014/02/development-diary-part-the-fifth/
- MuseScore forum, rests shared by two voices (cites Gould p. 528; not opened): https://musescore.org/en/node/34511
- Behind Bars table of contents: https://behindbarsnotation.co.uk/contents/toc.pdf
