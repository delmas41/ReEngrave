# Grace notes — engraving rules, the print, and where STAGED stands (ROADMAP 2.156)

Path: STAGED, GATHER + ADJUDICATE. Nothing here changes pipeline output; no
page gather was run.

**What is Sean's and what is not.** Only two things are his (2026-10-16):
a grace note **never counts in the bar** and is **significantly smaller**
than a regular note. He then withdrew the rest: *"I am not sure the slash is
optional… I was guessing. I don't know about notes after a trill. Your
research would be the most reliable info we have."* So every other rule
below rests on this file, and this file has to be checked rather than
remembered.

Each rule is marked **SOURCED** (a source fetched on 2026-10-16 says it;
URL and at most one short quote given) or **MEMORY** (from recollection of
Gould *Behind Bars*, Ross *The Art of Music Engraving*, Read *Music
Notation*, none of which was fetched). Then: what our print shows, and the
convention it implies as CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT
CONFIRMED.

## 1. Sources fetched 2026-10-16

| key | URL |
|---|---|
| MXL-grace | https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/grace/ |
| MXL-note | https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/note/ |
| MXL-type | https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/type/ |
| WP-grace | https://en.wikipedia.org/wiki/Grace_note |
| WP-acc | https://en.wikipedia.org/wiki/Acciaccatura |
| WP-app | https://en.wikipedia.org/wiki/Appoggiatura |
| WP-trill | https://en.wikipedia.org/wiki/Trill_(music) |
| LILY | https://lilypond.org/doc/v2.25/Documentation/notation/special-rhythmic-concerns (Grace notes) |
| DORICO-place | https://archive.steinberg.help/dorico/v2/en/dorico/topics/notation_reference/notation_reference_grace_notes_general_placement_conventions_c.html |
| DORICO-slur | https://archive.steinberg.help/dorico/v1/en/dorico/topics/notation_reference/notation_reference_slurs_placement_grace_notes_c.html |
| CPEB | https://versuch.cpebach.org/v-html/glossary/Nachschlag.html (C.P.E. Bach, *Versuch*, glossary "Nachschlag") |
| FORUM-Gould | https://musescore.org/en/node/310990 (quotes Gould p. 126; secondary) |

Not reachable as text: Gould, Ross and Read themselves; no Henle or
Bärenreiter editorial guide on grace notes was found. LilyPond and Dorico
are software manuals: they state a practice, not an authority.

## 2. The rules

**R1 — Takes no time in the bar.** SOURCED. MXL-note: *"Thus grace notes do
not have a <duration> element."* Timing lives only in `steal-time-previous`
/ `steal-time-following` / `make-time` (MXL-grace). Also Sean. Print: not a
print question. Scope: general. (Sean's rule; not a convention to confirm.)

**R2 — Smaller.** SOURCED. WP-grace: *"printed smaller to indicate that it
is melodically and harmonically nonessential."* MusicXML gives grace notes
`size="cue"` (MXL-type). The ratio is NOT sourced (MEMORY: about 60–70%).
Print: Brahms, the 3 groups below measure 0.67–0.82 of the staff's regular
head width and 0.65–0.75 of its height (§4). Litolff: none found.
CONVENTION ASSUMED: a grace head is about 0.65–0.8 of the same staff's
regular heads in each axis on Breitkopf. WHAT WOULD FALSIFY IT: a grace on
another page or publisher measuring ≥ 0.9, or regular heads (tremolo heads,
merged chords) routinely measuring ≤ 0.8 — the scan in §4 already shows the
second: 342 of 345 small-box groups on Brahms were NOT graces. NOT
CONFIRMED.

**R3 — The slash.** SOURCED, and the sources DISAGREE on how hard the rule
is:
- Meaning: WP-grace: *"often interpreted to indicate the intention of an
  acciaccatura or an appoggiatura, respectively"* (slash / no slash). WP-app:
  the appoggiatura is printed *"usually without the oblique stroke."* LILY
  defines the acciaccatura as *"indicated by a slurred note with a slashed
  stem"*, the appoggiatura as printed without the slash.
- The slash is NOT reliable evidence of performance: WP-acc says Mozart's
  and Haydn's long appoggiaturas are notated *"indistinguishable from"*
  later before-the-beat acciaccaturas. So an unslashed small note in 18th-
  and 19th-century print may be either kind.
- Groups: LILY (known issue) *"A multi-note beamed acciaccatura is printed
  without a slash"*; DORICO-place puts the slash *"at the beginning of a
  grace note beam"*; FORUM-Gould quotes Gould p. 126 for a stroke at the
  start of a group and Gerou/Lusk for never. Publishers differ.
- No fetched source says a slash is ever REQUIRED on a printed grace.
Print: Brahms 0 of 3 groups slashed (all three are two-note beamed groups).
No single grace note was found on either plate, so the single-grace case is
unseen. CONVENTION ASSUMED: a missing slash says nothing about whether a
small note is a grace (size decides), and nothing about how it is played;
a slash, where seen, is written `<grace slash="yes"/>`. WHAT WOULD FALSIFY
IT: a plate where every small note is slashed and unslashed small notes
mean something else (cue notes). NOT CONFIRMED.

**R4 — Written value from its own flags and beams.** SOURCED for the
mechanism, MEMORY for the habits. MXL-type: *"The <type> element indicates
the graphic note type."* — a grace's `<type>` is what is drawn, not a time
value. The habits (single grace = eighth, group = 16ths, the old
appoggiatura written at its real value) are MEMORY; WP-grace gives only
*"sometimes written as having exactly half the value of the principal
note."* Print: Brahms 3 of 3 groups have two beams = 16th (Sean called tile
6 "16th grace note"). CONVENTION ASSUMED: the written type is read off the
grace's own beams/flags exactly as for a regular note; with no flag or beam
seen, the type is UNREAD, never an assumed eighth. WHAT WOULD FALSIFY IT: a
plate whose grace beams do not match the conventional type (for example
three-beam graces that Sean reads as 16ths). NOT CONFIRMED.

**R5 — Stem up.** SOURCED (software practice, not an authority).
DORICO-place: *"Grace notes appear stem up by default"* (single voice);
DORICO's multi-voice page says lower-voice graces go down. LILY lets the
default be overridden. Print: Brahms 3 of 3 stem up, including staff 12
where the surrounding notes are stem-down. CONVENTION ASSUMED: in one voice
a grace stem points up whatever the main note does; "stem up → stem on the
right of the head" still holds. WHAT WOULD FALSIFY IT: a stem-down grace in
a single-voice staff. NOT CONFIRMED.

**R6 — Placement.** SOURCED.
- Before the main note: DORICO-place *"Grace notes are always positioned
  before a notehead"*; WP-grace: graces sound *"before the sounding of the
  relatively longer-lasting note which immediately follows them."* At a
  barline: DORICO-place *"They are normally placed after a barline"*.
- **After a trill (Nachschlag):** CPEB: *"two small notes from below are
  attached after the main note"*; WP-trill: endings are *"often marked with
  a few appoggiaturas"* *"following the note bearing the trill
  indication"*. LILY provides `\afterGrace` for grace notes that follow
  their main note. So small notes after a trilled note belong to the
  TRILLED note, ending it — they are not before-the-beat graces of the next
  bar's first note.
- Where the grace's own accidental sits (small, in front of the grace):
  MEMORY.
Print: Brahms 3 of 3 groups are Nachschläge: after a trilled dotted note,
in the same bar, immediately before the double barline into the 6/8, with
a small natural in front of the first grace. 0 before-the-note graces were
found on either plate. CONVENTION ASSUMED: small notes that follow a
trilled note and stand before the next barline end that trill and belong to
its bar, written as after-graces (MusicXML: grace notes after the last note
of the bar; LilyPond `\afterGrace`); elsewhere a grace belongs to the next
note. WHAT WOULD FALSIFY IT: Sean reading these as the first notes of the
next bar, or a plate placing a trill ending after the barline. NOT
CONFIRMED.

**R7 — Slur from grace to main note.** SOURCED (practice). LILY's
acciaccatura is *"a slurred note"*; DORICO-slur: *"slurs in Dorico appear
below grace notes and curve downwards by default"* and connect noteheads.
Whether a plate prints it is not sourced. Print: Brahms 3 of 3 groups carry
an arc from the trilled note to the grace group — above on staves 9 and 12,
below on staff 10 — i.e. the slur ties the ending to its trilled note, not
to a following main note. CONVENTION ASSUMED: an arc between a grace group
and its owner is a grace slur — never a tie, never a phrase slur for the
following notes; its absence is not evidence. WHAT WOULD FALSIFY IT: such
an arc continuing over the barline into the next bar's notes. NOT
CONFIRMED.

**R8 — MusicXML encoding.** SOURCED (MXL-grace, MXL-note, MXL-type):
`<grace/>` (with `slash="yes"` when seen), no `<duration>`, `<type>` from
the drawn shape, `size="cue"` allowed. Scope: encoding.

## 3. Where the sources disagree, plainly

1. **Slash on a group of graces:** Gould (via the forum quote) and Dorico:
   one stroke at the start of the beam. LilyPond: no slash on a beamed
   group. Gerou/Lusk (via the forum): never.
2. **Slash = how it is played:** modern references (Wikipedia, LilyPond)
   say slash = acciaccatura (short), no slash = appoggiatura (on the beat,
   takes value). Wikipedia's Acciaccatura article says classical-era
   notation does not tell them apart. So for 19th-century German plates
   the absence of a slash does NOT reliably mean "appoggiatura". For our
   output this does not matter: neither kind takes time in the bar (R1),
   and we write what is drawn.
3. **A trill ending — grace or part of the trill:** C.P.E. Bach treats the
   two small notes as part of the trill; MusicXML and LilyPond encode them
   as grace notes after the main note. Both put them AFTER the trilled
   note.

## 4. The print

**Method.** No gather. From the 20261014-night records (production,
600 dpi), every `noteheadBlack*` detector box was compared with its own
staff's median regular head height; a box ≤ 0.75 of that height and
0.7–1.25 spaces wide was a candidate, grouped by staff within 4 spaces.
Every candidate group was looked at by eye on the PDF page (PyMuPDF, page
index = record page). The trill boxes (`ornamentTrill`) on both records
were also looked at, with the bar to their right.

| | Litolff (Beethoven 5/i) | Brahms (1/i) |
|---|---|---|
| black-head boxes | 9,553 | 23,026 |
| small-box candidates / groups | 186 / 149 | 470 / 345 |
| groups looked at by eye | 21 multi-head + 24 sampled singles | all 345 |
| `ornamentTrill` boxes looked at | 3 (all false: notes under *più f*) | 24 (4 on the p1 trills, 2 on a p12 timpani roll with no ending, rest false) |
| **grace groups found** | **0** | **3** (pdf page 1, staves 9, 10, 12) |

What the false candidates were: tremolo heads, ledger-line chord fragments,
clef and key glyphs at a system start, merged or broken heads. Size alone
picks out 3 real groups from 345 on Brahms — a size cut is a ranker, not a
decider.

The three Brahms groups (all identical in kind): **2 heads, no slash, two
beams (16th), stem up, small natural on the first, after a trilled dotted
note, before the double barline into the 6/8, an arc from the trilled note
to the group** (above on 9 and 12, below on 10). They are the 2.155 tiles
11, 13 and 6.

| tile | glyph | detector class | w × h (spaces) | staff regular w × h | ratio w, h |
|---|---|---|---|---|---|
| 6 | glyph/1/0/12/0/18 | noteheadBlackOnLine | 1.01 × 0.78 | 1.39 × 1.19 | 0.73, 0.65 |
| 11 | glyph/1/0/9/0/28 | noteheadBlackOnLine | 1.14 × 0.84 | 1.39 × 1.21 | 0.82, 0.69 |
| 13 | glyph/1/0/10/0/26 | noteheadBlackInSpace | 0.93 × 0.83 | 1.37 × 1.11 | 0.67, 0.75 |

Crops for Sean: `out/print/2.156-research/01–03-*.png`, page raster at
600 dpi, one blue box around the small notes and nothing else of ours;
`key.json` lists page, staff, box and the observations above.

**Limits.** A grace the detector boxed at regular height, or never boxed,
is invisible to this scan, and only detected trills were checked (the
staff-12 trill itself was not detected). So "0 on Litolff" means none
found, not none printed; from MEMORY Beethoven 5/i prints no grace notes.

## 5. What the detector and STAGED do with grace notes today

- **Vocabulary.** 208 classes include `graceNoteAcciaccatura/Appoggiatura
  StemUp/StemDown` (99–102, coarse 196) and the `*Small` family (heads,
  `flag8thUp/DownSmall`, `accidental…Small`, coarse
  `noteheadFullSmall/HalfSmall`).
- **Night records:** **zero** `graceNote*` and **zero** `*Small` boxes on
  either plate (Litolff 37,137 boxes, Brahms 98,663). Grace heads arrive as
  regular `noteheadBlack*` (the three above). Same as the legacy finding in
  `tools/omr/export_coverage.py`.
- **Flow if one appeared:** `gather.py` files `Q.GLYPH_BOX` for every
  detection; a `*Small` head also gets `Q.NOTEHEAD_CLASS` and enters the
  note path as an ordinary head, while `geometry.is_regular_notehead`
  keeps it out of the standard-box measurements (gather ~2984/3043/4351/
  8307/9130, `notehead_precision`). A `graceNote*` class gets a
  `GLYPH_BOX` row and nothing else (`gather_coverage`: `"grace": None`).
- **So today** a grace is a regular note: standard 1.4 × 1.1-space box, a
  value or a narrowing, and a place in the bar sum.

## 6. Open

The print answers slash (none on these), value (two beams), stem (up),
placement (after a trill, before the barline) and slur (to the trilled
note) for the one kind of grace these two movements print. Left for Sean:
whether these Nachschläge are written as the ending of the trilled note's
bar (R6), which the books support and the print is consistent with but
cannot itself settle.
