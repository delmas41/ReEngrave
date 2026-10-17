# Grace notes — engraving rules and where STAGED stands (ROADMAP 2.156, phase 1)

Sean 2026-10-16, verbatim: *"Grace Notes never take up math in the measure.
They are significantly smaller by proportion to the regular note size. Som
have a little slash through them but nit always. Do some research to make
sure we know the engraving rules."* Recorded in `docs/page-facts.md` §1 and
DECISIONS 2026-10-16. Everything below beyond those two sentences is
**NOT CONFIRMED until Sean rules on it.**

Path: STAGED, GATHER + ADJUDICATE. Nothing here changes pipeline output.

## 1. Sources and how far each is trusted

| key | source | how it was consulted |
|---|---|---|
| GOULD | Elaine Gould, *Behind Bars* (Faber 2011), "Grace notes" (pp. ~125–133; the slash-on-groups rule is quoted from p. 126 in a MuseScore forum thread) | from memory of the text + the one quoted page; page numbers other than 126 not re-checked |
| ROSS | Ted Ross, *The Art of Music Engraving and Processing* (1970), grace-note section | from memory; no page numbers |
| READ | Gardner Read, *Music Notation* (2nd ed. 1969), "Grace notes" / ornaments | from memory; no page numbers |
| MXL | W3C MusicXML 4.0 reference, `<grace>` and `<note>` | fetched 2026-10-16 (w3.org/2021/06/musicxml40/…/elements/grace/) |
| PLATE | Brahms 1 / Breitkopf (imslp317803), pdf page idx 1, the three 2.155 tiles 6/11/13 | looked at and measured, §4 |
| PRIOR | `benchmarks/omr-labeling-grace2-2026-09` + `omr-labeling-survey-2026-09/GRACE_SELECTOR_2026-09-03.md`: Sean's 30 labeled grace heads on Mahler 5 / Peters | read; measured then |

No Litolff grace note was looked at in this lane (§5 explains why none was
found on the record). "General" below means every reference agrees and
nothing on our plates contradicts it; "plate" means seen on one edition only.

## 2. The rules, per question

**R1 — Takes no time in the bar.** A grace note's value is not counted in
the measure; its time is stolen from a neighbour in performance. MXL: a
grace `<note>` carries `<grace/>` and **no `<duration>`**; playback timing
is only the optional `steal-time-previous` / `steal-time-following` /
`make-time` attributes. *Source:* Sean, GOULD, ROSS, READ, MXL. *Scope:*
general. (Already ruled by Sean.)

**R2 — Size.** Grace heads, stems, flags, beams and their accidentals are
engraved at cue/grace size, roughly 60–70% of a regular note; stems shorter
in proportion. *Source:* Sean ("significantly smaller"), GOULD, ROSS
(grace = cue-size type), SMuFL/DSv2 give them their own `*Small` glyphs.
*Scope:* general for "clearly smaller"; the **ratio** is plate-specific and
must be measured (§4: Breitkopf ≈ 0.7 of a regular head in each axis;
PRIOR Peters labels clicked at a 0.62-space box).

**R3 — Slashed (acciaccatura) vs unslashed (appoggiatura).** A single
grace with a diagonal stroke through stem and flag is the acciaccatura
(short); without it, the appoggiatura. The slash is optional evidence: its
absence never makes a small note regular (Sean). Groups of graces are
usually unslashed; GOULD (p. 126) allows one stroke through the first stem
of a beamed group, other authorities say never — so a slash on a group is
publisher practice. In 19th-c. German plates an unslashed single small
eighth is very often still played short; the slash only became routine
later. MXL: `<grace slash="yes"/>`. *Source:* Sean, GOULD, ROSS, READ, MXL.
*Scope:* general for "slash = acciaccatura, slash optional"; whether a given
publisher slashes at all is plate-specific (none seen on the Breitkopf
tiles, which are a group).

**R4 — Written value is read from the shape, like a normal note.** Flags
and beams count exactly as on a regular note: one flag/beam = eighth, two =
16th, three = 32nd. Convention: a single grace is usually an eighth (often
slashed); groups are usually 16ths (two beams), longer runs sometimes 32nds.
The old appoggiatura was written at its intended value (quarter, eighth),
so a single unslashed grace may be a quarter. *Source:* GOULD, ROSS, READ;
PLATE (the two-beam pair Sean called "16th grace note"). *Scope:* reading
the value off flags/beams is general; "single = eighth, group = 16th" is a
prior only — it may NARROW, never DECIDE (CLAUDE.md §4: a note is an eighth
only on evidence).

**R5 — Stem direction.** In a single-voice staff grace stems point UP
regardless of the main note's position (slur then goes below); when two
voices share the staff, the grace follows its voice's direction. *Source:*
GOULD, ROSS, READ. *Scope:* general (PLATE: all three Breitkopf groups are
stem-up, including tile 6 on a staff where the main notes are stem-down).
Consequence for us: "stem up → right of the head" still holds for a
grace; what fails is reading a grace's stem direction as the voice or as
evidence about the main notes.

**R6 — Placement: before the main note, after its accidental.** A grace
precedes the note it ornaments, set close to it; the main note's own
accidental sits between the grace and the main head. A grace before the
first note of a bar goes AFTER the barline (it belongs to the new bar)
— GOULD, ROSS. A grace's own accidental is small and sits in front of the
grace. *Exception — the trill termination (Nachschlag):* small notes AFTER
a trilled note, at the end of the bar BEFORE the barline, belong to the
preceding note (MXL encodes them as grace notes after the last note of the
measure; LilyPond `\afterGrace`). *Source:* GOULD, ROSS, READ, MXL; PLATE
for the Nachschlag. *Scope:* general; **all three 2.155 tiles are
Nachschläge** (§4).

**R7 — Slur from grace to main note.** Conventionally a short slur joins
the grace (group) to its main note, on the side opposite the grace stem
(below, for stem-up graces). Many editions omit it for acciaccaturas, and
it is implied when absent. *Source:* GOULD, ROSS, READ. *Scope:* the
convention is general; whether a plate prints it is plate-specific (the
Breitkopf Nachschläge sit under the trill's long slur to the next bar and
print no slur of their own). A grace slur is never a tie and never a
phrasing slur's owner.

**R8 — MusicXML encoding.** `<note><grace slash="yes|no"/><pitch>…`
`<type>16th</type>` (written value from R4), **no `<duration>`**, `<stem>`,
`<beam>` as normal; the grace notes come immediately before the note they
ornament in the same `<voice>`; a Nachschlag comes after the last note of
the bar. `<notations><slur>` for R7. *Source:* MXL. *Scope:* encoding.

## 3. What this means for the reader (proposed, not built)

A small head is a grace candidate on its SIZE against the same staff's own
regular heads (R2), measured locally; flags/beams on its own small stem give
its written value (R4); it is kept out of the bar sum always (R1); its
slash, if read, sets `slash="yes"` and is never required (R3); a group
before a barline after a trilled note is a Nachschlag (R6). Size alone on a
scan is a cut-off, not a convention — it may NARROW until a second
publisher's graces are measured.

## 4. Measured on the 2.155 tiles (Brahms 1 / Breitkopf, pdf idx 1)

From `tiles_brahms_base.record.json` (2.155 lane, already on disk; no
gather run). Boxes are the detector's own (`bbox_page_px`, 600 dpi), staff
spacing `staff_spacing` ≈ 27.3 px. Regular = median of the same staff's
other `noteheadBlack*` boxes.

| tile | glyph | class the detector gave | w × h (sp) | staff regular w × h (sp) | ratio w, h |
|---|---|---|---|---|---|
| 6 | glyph/1/0/12/0/18 | noteheadBlackOnLine | 1.01 × 0.78 | 1.39 × 1.19 | 0.73, 0.65 |
| 11 | glyph/1/0/9/0/28 | noteheadBlackOnLine | 1.14 × 0.84 | 1.39 × 1.21 | 0.82, 0.69 |
| 13 | glyph/1/0/10/0/26 | noteheadBlackInSpace | 0.93 × 0.83 | 1.37 × 1.11 | 0.67, 0.75 |

Each tile head has its grace partner ~1.1 sp to the left (glyph/1/0/12/0/11,
/9/0/14, /10/0/17: 0.75–0.84 sp tall). Over staves 9, 10 and 12, black-head
HEIGHT is bimodal: 21 heads at 0.6–0.9 sp, 103 at 1.0–1.3 sp. By eye (crop
of x 1450–2150, y 2600–3700): each is a two-note 16th Nachschlag, stem up,
two beams, small natural on the first note, no slash, after a trilled
dotted note, just before the barline into the 6/8 — R2, R4, R5, R6 all
visible on one plate.

## 5. What the detector and STAGED do with grace notes today

- **Vocabulary.** The 208-class space has `graceNoteAcciaccatura/
  Appoggiatura StemUp/StemDown` (ids 99–102, coarse 196) and the `*Small`
  family (`noteheadBlack/Half/Whole…Small`, `flag8thUp/DownSmall`,
  `accidental…Small`, coarse `noteheadFullSmall/HalfSmall`).
- **Night records (20261014-night, both whole movements), every
  `glyph_box` row counted (Litolff 37,137, Brahms 98,663):** **zero**
  `graceNote*` boxes and **zero** `*Small` boxes on either plate. The
  production heads never emit the class; grace heads arrive as regular
  `noteheadBlack*` (the three tiles prove it on Brahms). This repeats the
  legacy finding in `tools/omr/export_coverage.py` ("grace": zero `*Small`
  detections on any page).
- **Flow, if one did appear.** `gather.py` files a `Q.GLYPH_BOX` for every
  detection; a `*Small` head also gets `Q.NOTEHEAD_CLASS` (prefix
  `notehead`, line ~459) and so enters the note path as an ordinary head;
  `geometry.is_regular_notehead` returns False for `*Small`, so the five
  standard-box consumers (ledger rung ink ~2984/3043, stem gate ~4351,
  re-centre ~8307, fill ~9130, `notehead_precision`) keep the detector box
  and skip their measurement. `graceNote*` classes map to category
  `ornament` but `gather_glyph_families` routes no `grace` family
  (`gather_coverage` FAMILY `"grace": None`): a `GLYPH_BOX` row and
  nothing else. No quantity, adjudicator or export knows "grace".
- **So today** a grace note is read as a regular note with a standard
  1.4 × 1.1 sp box, given a value (or narrowed), and counted in the bar sum
  — exactly the 2.155 tiles.

## 6. Open, for Sean

The question put to him: whether R4 holds on these plates — the written
value read off the grace's own beams/flags (two beams = 16th), with
"single = eighth, group = 16th" only a fallback that may narrow — and
whether the Nachschlag (R6) is written as grace notes after the trilled
note rather than before the next bar's first note.
