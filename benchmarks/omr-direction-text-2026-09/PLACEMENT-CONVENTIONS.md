# Where do direction words go? Placement conventions, checked against 1,737 reference encodings and the literature

Date: 2026-10-08. Research only: no code changed. Scripts and raw tables are under
`/private/tmp/claude-501/placement-research/` (`extract.py`, `classify.py`, `a4.py`-`a8.py`;
`rows.json` holds every extracted direction, `words_enriched.json` every `<words>` row with its class).

**The question.** The direction-word reader finds a word in the GAP between staff N and staff N+1 of one
system and must decide which staff it belongs to. Today every gap word goes to the staff ABOVE (N), except
`a 2`, which goes to the staff below when nearer to it. Sean's ruling on the oboe `Adagio` (Beethoven 5/i,
Litolff, printed in the gap above the oboe staff): it belongs to the staff beneath; tempo is above the staff,
expression usually (always?) below; and the staff above has no notes, so the word would make no sense there.

**Headline.** Sean's rule is right for tempo words, technique words and part indications, which sit ABOVE the
staff they govern. It is wrong for expression and dynamic words, which sit BELOW the staff they govern.
"Everything in the gap goes to the staff above" is therefore correct for only about 47% of orchestral gap
words in the encodings (6,561 of 13,921), and a rule that picks by word category plus a notes tie-break is
correct for about 88% (12,290 of 13,921). Caveat on that figure: it is partly circular, see section 6.

---

## 0. Method and honesty notes

- **Corpus.** `library/reference/`, 1,745 JSON sidecars, 1,737 music files after excluding every path containing
  `beethoven--symphony-5` or `brahms--symphony-1` (8 files). All 1,737 parsed (0 errors). 1,214 files
  contain at least one `<words>`; 55,403 `<words>` strings in total. Also tallied: 149,577 `<dynamics>`
  glyphs and 90,603 `<wedge>` elements as controls.
- **What the corpus is.** 99.4% of the words (55,096 of 55,403, 1,195 of 1,214 files) come from files written by
  MuseScore (versions 1.2 to 4.6); 14 files (268 words) from Finale; the rest are music21 or other. Source
  folders (origin paths of the 1,745 sidecars) are mostly Lieder (810 files), piano works and sonatas, Bach chorales/cantatas, and a few dozen
  orchestral scores (Beethoven 9, Holst Planets, Dvorak 9, Tchaikovsky 6, Mahler 5, Brahms 2-4, Bruckner 5,
  Beach and others). They are community transcriptions, not publisher data. No publisher is recorded, so
  "by publisher/era" cannot be tabulated; only "by encoder software" can, and that is almost one encoder.
  The three most important consequences: (i) an encoding's `placement` is an encoder's choice and may be a
  software default rather than the print; (ii) one encoder family dominates; (iii) there is no engraver
  diversity to separate "convention" from "MuseScore's text styles". Whether MuseScore's default text styles
  place expression text below and tempo text above is **not verified** (the MuseScore handbook page I could
  read states only that new System Text goes above the top staff).
- **Placement.** In MusicXML `placement` sits on `<direction>`; `<words>` itself never carried it in these
  files (0 of 55,403). Of 55,403 words, 27,345 are `above`, 16,572 `below`, **11,486 (20.7%) carry no
  placement**, all of them MuseScore (MuseScore 4.3.2 omits it on 60% of words, 4.4.1 on 23%, 4.5.2 on 29%;
  MuseScore 2.x and 3.x almost never). The missing ones are not random: they lean below. So I report two
  figures:
  - **explicit**: the `<direction placement>` attribute only;
  - **effective** (headline): explicit placement, else the sign of the vertical position
    `default-y + relative-y` (positive = above the top staff line; below -40 tenths = under a five-line
    staff). MuseScore 2.x writes `default-y=40` plus a `relative-y` offset, so the sum is required.
    Check that the position agrees with the attribute where both exist: of 32,010 explicit placements with a
    position, 30,042 (93.9%) agree by sign (`above`/`y>0` 19,792; `below`/`y<-40` 10,250), 1,495 (4.7%) lie
    inside the staff band, 473 (1.5%) contradict (`above`/`y<-40` 20; `below`/`y>0` 453).
- **Classification.** Layered: `tools/omr/direction_lexicon.py` `lookup()` first (its `tempo`->`tempo_head`,
  `expression`, `dynamic`->`dynamic_word`), plus my own hand-built rules in `classify.py` for what the lexicon
  refuses or has no category for. The lexicon has no `part` category and files `pizz.`, `arco`, `div.`,
  `unis.`, `sord.` under `expression`, so I split those out as `technique`, and `a 2`, `solo`, `tutti`, player
  numerals and instrument abbreviations as `part`. My classes, in priority order: `part`, `technique`,
  `tempo_return` (`a tempo`, `Tempo I`, `Erstes Tempo`), `tempo_modifier` (`rit.`, `rall.`, `accel.`,
  `string.`, `allarg.`, `piu/meno mosso`, `cedez`, `suivez`, German `langsamer`, ...), `tempo_head`
  (Allegro, Adagio, German/French tempo phrases), `dynamic_word` (`cresc.`, `dim.`, letter dynamics typed as
  text), `expression`, `other`. Coverage: `other` holds 5,620 of 55,403 (10.1%), mostly accidentals,
  brackets, single letters, chord symbols, titles. The classifier is heuristic; the per-string table in 4.2
  is the cleaner evidence for individual words. `sostenuto` and a few other words are ambiguous between
  tempo and expression and are filed as tempo (lexicon).
- **Cohorts** (by part, not file): **orchestral** = single-staff, no lyric, in a file of 8 or more parts
  (118 files, 18,663 words; the top five works supply 48.6% of them: Beethoven 9 2,940, Holst Planets
  2,001, Dvorak 9 1,712, Tchaikovsky 6 1,420, Mahler 5 991); **keyboard** = part with 2 or more staves
  (17,974 words); **vocal** = part with lyrics (18,209; includes choral parts in Bach/Beethoven 9 and
  Lieder voice parts); **small ensemble** = 2-7 parts, single staff, no lyric (557 words, too few to lean
  on). There is NO instrumental-part (single solo-instrument file) cohort: no file in the corpus is a
  lone-instrument part with words. "Full score versus parts" is therefore not testable here.
- **Notes.** "Has notes in that bar" = at least one non-rest `<note>` on that staff in that measure index
  (grace and cue notes count). Directions are attributed to the part and `<staff>` they are written in.

---

## 1. Tempo words (Allegro, Adagio, a tempo, Tempo I, rit., rall., accel., string., allarg., piu/meno mosso, ...)

### 1a. Movement or section heading over the top of the system

**Answer: above, almost always (high confidence).** Effective placement, `tempo_head` (heading words):
all cohorts 1,790 above / 64 below = **96.5% above** (n=1,854 placed, 139 with no position); orchestral
**93.1% above** (190/204, Wilson 95% CI 88.8-95.9); keyboard 95.7%; vocal 97.8%. By string, a
non-modified tempo word (Allegro/Adagio/Andante/Presto/Largo/Lento/Moderato/Vivace/Allegretto/Grave/...):
97.4% above (1,104/1,133), 98.5% orchestral (134/136); `Adagio` alone 91.7% (88/96; orchestral 11/11).
`Tempo I` 93.8% (180/192) and `piu/meno mosso` 91.4% (53/58) are also above; `a tempo` is lower, 81.5%
(688/844), see 1c.

The heading is a SYSTEM-level word: in files of 8 or more parts, 319 of 351 heading words (91%) are
attached to the first (top) staff, and 217 of those 319 (68%) sit over a first staff that holds no notes in
that bar. The encodings repeat a heading over more than one part in only 26 of 321 distinct
(file, bar, text) cases (8%), so the "repeat over the strings / at the foot of the system in full scores"
behaviour is mostly not in the encodings. The literature says it is a layout option, not an accident:
Dorico treats tempo marks as system objects shown above the top staff and, if the score so chooses, above
each instrument family (woodwind, brass, percussion, strings); see section 7.

### 1b. A tempo word applying to ONE part (a solo Adagio, a cadenza)

**Answer: also above that part's staff (medium confidence); in a gap it belongs to the staff BELOW.**
- Sean's ruling on the oboe `Adagio` is consistent with every source here. The print (Litolff 984073, PDF
  page index 9, bar 268, rendered at 300 dpi to `/private/tmp/claude-501/placement-research/litolff_p9_crop.png`
  and `litolff_p9_strings.png`) shows `Adagio.` immediately above the oboe staff, in the gap between the
  resting flute staff and the oboe, with the flute bar holding only rests and the oboe holding the notes the
  word governs. On the same page `cresc.` is printed under the wind staves and `pizz.` / `arco` above the
  string staves, so one page shows all three placements.
- The encodings cannot confirm this independently. Only 117 tempo-class words in the orchestral cohort sit in
  a genuine gap position (28 heading, 22 return, 67 modifier), and most are from Mahler 5 files (17 of 28 headings, 21 of 22
  returns, 51 of 67 modifiers). In the three MuseScore 2.3.2 Mahler 5 movements the word is attached to the
  Piccolo or Flute staff but carries a `relative-y` of -200 to -2,070 tenths (the encoder dragged a
  top-staff system text down over lower staves). In those files the encoder's owner is NOT the staff the word
  governs in print. Do not read an ownership rate off them; I did not.
- Where tempo-class words do sit on a lower staff and the position is known, the staff holding the notes is
  the owner in the one-sided bars: heading 6 of 9, return 5 of 5, modifier 23 of 26 in the simulation
  (section 6), n too small for a rate.

### 1c. Tempo-modifying words (rit., rall., accel., string., allarg., a tempo)

**Answer: mostly above, but with a real below minority and a sensitivity to context (medium-low
confidence).** Effective placement, all cohorts: `tempo_modifier` 1,787 above / 613 below = **74.5% above**;
`tempo_return` (`a tempo`, `Tempo I`) 1,024 / 210 = **83.0% above**. By string (all cohorts): `rit./riten./
ritard.` 74.7% above (842/1,127; orchestral 52/67 = 77.6%), `rall.` 74.7% (133/178; orchestral 10/10),
`accel.` 72.3% (60/83), `string.` 63.6% (28/44), `allarg.` 74.3% (26/35), `a tempo` 81.5%.
By cohort: orchestral 74.8% above (110/147, CI 67.2-81.2); vocal 90.8% (917/1,010); keyboard 60.8%
(749/1,231), and in the keyboard part the top staff has 58.6% above (631/1,077) while the second staff has 78.8%
above (115/146) (a piano word below the top staff is in the gap between the two staves, between the hands).
By encoder: MuseScore tempo_modifier 74.3% above (n=2,311 explicit); the 14 Finale files 86.8% (n=68), no
conflict but too small. At file level (files with 5 or more placed words) 73 of 179 files are at least
90% above, 10 at most 10% above and 96 mixed, so the minority below is spread across many encoders'
choices rather than being one file.

Full score vs parts: **not testable** from this corpus (no single-instrument part files). Literature:
Gould's *Behind Bars* is reported (second-hand, forum paraphrase) to say all tempo information goes
above the staff including gradual changes; a Dorico developer in the same thread calls below-staff
placement a little archaic (Steinberg forum, "Rit, Rall and a tempo below the staff"); a forum user's sample of 20 classical pieces found gradual changes below in the great majority of
cases, and Dorico forum posters report that in 19th-century solo pieces the opening tempo is above in bold
while later tempo CHANGES are written like expression text, in italics, between the systems.
These are forum assertions, not verified book text. The encodings (74-83% above) sit between the two claims.

---

## 2. Expression / character words (dolce, espr., legato, cresc., dim., sempre, marc., ten., simile, stacc.)

**Answer: below, usually, not always (medium-high confidence for "usually"; "always" is false).**
Effective placement, `expression` class: all cohorts 1,730 above / 3,610 below = **67.6% below**;
orchestral 757 / 1,810 = **70.5% below** (n=2,567, CI 68.7-72.2 below); keyboard 64.5% below; vocal 64.8%
below. The `dynamic_word` class (mostly `cresc.` / `dim.`): all 22.0% above, orchestral **86.5% below**
(4,944 of 5,715, CI 85.6-87.4); vocal only 67.4% below. The glyph-dynamics control (`<dynamics>`, the
printed `p f mf` marks) is 98.8% below in the orchestral cohort (73,398 of 74,270), 91.9% in keyboard,
88.7% in vocal; wedges 98.6% / 91.7% / 58.6% below (glyph and wedge figures use the explicit attribute only). So words track the glyphs but with more above.

Per string, all cohorts, % above: `dolce` 23.4% (200/854), `espr.` 29.5%, `legato` 38.2%, `cresc.` 23.3%
(2,555/10,943), `dim.` 13.6%, `sempre ...` 16.9%, `marc.` 20.2%, `simile` 80.2%, `stacc.` 59.4%, `ten.` 89.2%.
Orchestral: `dolce` 22.7%, `espr.` 27.7%, `legato` 25.6%, `cresc.` 14.0%, `dim.` 5.9%, `sempre` 9.0%,
`marc.` 19.8%, `stacc.` 61.9%, `simile` 95.2%, `ten.` 100% (38/38, but 30 of those are from one Beethoven 1
file, so not evidence).

**Exceptions seen in the data.**
- **Articulation words follow the notes' stem side**, not the staff: `stacc.` splits 60/40 above/below;
  `ten.` and `simile` sit above in orchestral files (the latter being a line-ending instruction over the staff).
- **Vocal parts.** Dynamic-class words are 32.6% above for vocal parts versus 13.5% for orchestral parts, and
  glyph dynamics are above in 11.3% (vocal) versus 1.2% (orchestral). This matches the engraving rule that
  vocal dynamics go above because lyrics are below (Dorico: below for instruments, above for voices; see
  section 7). It is a minority in the encodings (the vocal majority is still below), which is consistent with
  piano-vocal Lieder where the dynamic sits between the voice and the piano.
- **Keyboard second staff.** `dynamic_word` on the lower staff is 55.5% above (258/465) versus 4.3% above on
  the top staff: above the lower staff means in the gap between the hands.
- **Two parts on one staff / crowded passages / top staff:** not separable in the encodings (no field).
- **Encoder habit.** File-level, orchestral `expression` (files with 5 or more placed words): of 55, 26 are
  at least 90% below, 8 at least 90% above, 21 mixed. A whole file is often one style (e.g. Brahms 3: 0 above
  of 128; Beethoven 1: 32 above of 32), so the 29.5% above is partly a handful of encoders' choices. Only 18% of
  files with 20 or more placed words use a single placement for every word (50 of 271), and all 50 are
  `above`.

---

## 3. Technique and part indications (pizz., arco, con sord., div., unis., a 2, solo, Vcl., Basso, gestopft)

**Answer: above the staff, almost always (high confidence).** Effective placement, `technique`: all cohorts
4,132 above / 335 below = **92.5% above**; orchestral **97.5% above** (2,280 of 2,338, CI 96.8-98.1).
Per string, all cohorts: `pizz.` 98.4% (1,448/1,471), `arco` 99.5% (1,289/1,295), `con/senza sord.` 97.7%
(129/132), `div.` 92.5% (297/321), `unis.` 94.1%, `sul G` etc. 100% (33/33), `tremolo` 88.8%,
`gestopft/offen/Daempfer` 87.9% (94/107; 3 of 3 orchestral), `m.d./m.g.` 65.7% (keyboard hand marks, mixed).

`part` indications: `a 2` in all its spellings (`a 2`, `a.2.`, `a. 2`, `a2`) 99.8% above (3,901/3,909;
orchestral 2,396/2,397); `a 3/a 4` 99.0% (411/415); `solo/Solo` 92.5% (173/187; orchestral 134/146);
`1 solo`/`2 solo` 100% (393/393); `tutti` 100% (39/39). The class as a whole is lower (orchestral 89.6%)
because it also holds bare player numerals (`1`, `2`, `3`, `I.`, `II.`: 51.6% above overall, 77.5%
orchestral, ambiguous with tuplet or fingering numbers) and instrument-name cue labels (`Hn.`, `Cl.`,
`Fl.`, `Tbn.`: 18.8% above, 81% below, 344 words; these are inline cue markers, rare). I did not find `Vcl.`
or `Basso` as stand-alone direction words in any quantity (they are instrument labels, not directions).
Small ensemble: `part` 99.4% above (342/344).

**Implication for the current special case.** Only `a 2` is exempted from "gap word -> staff above" today.
`pizz.`, `arco`, `con sord.`, `div.`, `unis.`, `solo`, `1 solo`, `tutti`, `sul G`, `gestopft` are all above
the staff in 88-100% of cases and belong in the same exemption.

---

## 4. Dynamics with words (piu f, p dolce, sempre p)

**Answer: below for instruments (high confidence), but the encodings have almost no composite strings to
show it directly.** There are only 47 strings of the form letter-dynamic + word (e.g. `sempre pp`, `p cresc.`)
in the corpus (41 above, 6 below, 19 orchestral of which 14 above); that sample is dominated by `pp.` typed as
text and is not reliable. `piu f` / `meno f` appear 5 times in all. 146 bare letter dynamics (`p`, `f`, `pp`)
are typed as text, 144 of them above, but 132 of those 146 come from two choral files (Beethoven 9 finale 69,
Bach B minor mass 63), so they are part labels or encoder misuse, not evidence. Where the dynamics are
written as proper glyphs, which is what a `p dolce` reduces to, they are below 98.8% of the time in orchestral
parts (section 2), and the literature agrees for instrumental staves (Dorico, LilyPond; section 7).
Exception: vocal staves (above; lyrics below) and the keyboard gap, section 2.

---

## 5. Sean's second clue: a word beside a staff whose bar holds no notes

**Answer: for expression and dynamic words, almost never that staff's; for tempo words, often a staff with no
notes, so the clue is only sound for the first group.** Share of words whose owning staff has NO notes in that
bar (the base rate of empty bars across the orchestral files with words is **54.5%** of 1,004,717 unit-bars):

| class | all cohorts: n | no notes in bar | orchestral: n | no notes in bar |
|---|---:|---:|---:|---:|
| dynamic_word | 17,807 | 64 (0.4%) | 6,987 | 21 (0.3%) |
| expression | 6,396 | 95 (1.5%) | 2,847 | 32 (1.1%) |
| technique | 4,732 | 175 (3.7%) | 2,475 | 71 (2.9%) |
| part | 14,115 | 1,845 (13.1%) | 4,316 | 119 (2.8%) |
| tempo_modifier | 3,271 | 264 (8.1%) | 160 | 79 (49.4%) |
| tempo_return | 1,459 | 148 (10.1%) | 77 | 58 (75.3%) |
| tempo_head | 1,993 | 852 (42.7%) | 205 | 146 (71.2%) |

The expression and dynamic words are about 50-200 times less likely to be on an empty staff than chance: a
word beside a staff with no notes is not that staff's for these classes. Tempo headings and returns are the
reverse: they are system words and live on whatever staff is first, which is often resting. So for a tempo word
printed beside an empty staff the clue says nothing, and Sean's oboe case works only because a part-specific
word is above the staff that holds the notes it describes.

**Is "the staff with notes in that bar" a sound tie-breaker?** In the orchestral gap simulation (section 6), in
bars where only ONE of the two flanking staves has notes, the owner was the staff with notes for
expression 641 of 643 (99.7%), dynamic_word 1,140 of 1,153 (98.9%), technique 491 of 504 (97.4%; 9 of 22 for
the upper-only case), part 880 of 894 (98.4%), tempo_modifier 23 of 26 (88.5%), tempo_return 5 of 5,
tempo_head 6 of 9. In 70% or more of gap words both flanking staves have notes (1,741 of 2,400 expression,
3,908 of 5,065 dynamic, 1,756 of 2,318 technique), so the tie-breaker settles only the minority of cases (one-sided bars are roughly a quarter of gap words: 643 of 2,400 expression, 1,153 of 5,065 dynamic, 504 of 2,318 technique); on its
own it cannot be the rule. It should be an override on top of the category rule, and it is safe to use as
one for non-tempo words. For tempo words use it only as a hint.

---

## 6. Rule per category for a word in the gap between staff N (upper) and N+1 (lower)

### 6.1 The gap simulation, and why it is partly circular

For each word whose effective placement is above or below its owning staff, in files with 4 or more
staff-units, I took the pair of staves that flank the word's gap (above the owner: staves N-1 and N, owner is
the lower; below the owner: N and N+1, owner is the upper). Words above the top staff and below the bottom
staff have no gap and are excluded. The "truth" is the encoder's owner. Circularity: the gap is defined by
the same `placement` that the category tables tabulate, so "category rule is right" is the same fact as the
category's placement share; the independent information is the notes tie-break and the per-category share
itself. Orchestral cohort, 13,921 gap words in the 7 classes (excluding `other`):

| rule | correct |
|---|---:|
| today: every gap word -> staff above (N) | 6,561 of 13,921 = 47.1% |
| upper, but override to the staff with notes where only one has | 8,174 = 58.7% |
| category rule (tempo, technique, part -> N+1; expression, dynamic -> N) | 11,911 = 85.6% |
| category rule + notes override where only one staff has notes | 12,290 = 88.3% |

Per class (orchestral gap words): expression n=2,400 owned by upper 69.9%; dynamic_word n=5,065 upper 85.5%;
technique n=2,318 lower 98.0% (upper rule 2.0%); part n=4,021 lower 89.0% (upper 11.0%); tempo_head n=28,
tempo_return n=22, tempo_modifier n=67 are too few and are dominated by the Mahler 5 artefact in 1b, so give
no rate.

### 6.2 The table

Error rates are the orchestral-cohort share on the opposite side (effective placement), with all-cohort
figures in brackets. "In gap" means: the word printed between two staves. Confidence is the strength of the
evidence, not of the percentage.

| category | rule for a word in the gap N / N+1 | expected error | exceptions | confidence |
|---|---|---|---|---|
| tempo heading (Allegro, Adagio, Andante, ...) | belongs to N+1 (the staff beneath the word). Most headings are above the TOP staff and never reach a gap; one in a gap is part-specific (solo) or a repeat over a section | 6.9% orch (3.5% all); gap sample too small to measure | system-level words in a score may print over a group (strings) and apply to all staves under it; encoder-dragged text (Mahler 5) | high on the direction, medium on the owner |
| tempo return (a tempo, Tempo I) | N+1 | 20.8% orch (17.0% all) | `a tempo` below the staff in piano and some vocal-score prints | medium |
| tempo modifier (rit., rall., accel., string., allarg., piu mosso) | N+1 | 25.2% orch (25.5% all; keyboard 39%; vocal 9%) | gradual changes printed below the staff in italics (the common older practice reported in forum threads) | medium-low |
| expression / character (dolce, espr., legato, sempre, marc.) | N (the staff above the word), unless only N+1 has notes, then N+1 | 29.5% orch (32.4% all) before the notes override; 99.7% right in one-sided bars; 79.5% right overall on gap words | stem-side articulation words (stacc., ten.) split above/below; vocal staves put expression above; top staff | medium-high |
| dynamic word (cresc., dim., poco a poco ...) | N, unless only N+1 has notes | 13.5% orch (22.0% all; vocal 32.6%); 12.9% of gap words after the override | vocal staves above; keyboard gap between hands (lower staff 55.5% above) | high |
| technique (pizz., arco, con sord., div., unis., sul G, gestopft, tremolo) | N+1 | 2.5% orch (7.5% all); 2.2% on gap words | keyboard (26.9% below); `gestopft`/`offen` 88% above; `m.d.`/`m.g.` 66% above | high |
| part indication (a 2, a 3, solo, 1 solo, tutti) | N+1 | `a 2` 0.2% (8 in 3,909); `solo` 7.5%; the class as a whole 10.4% orch (bare numerals and cue names are the noise) | player numerals and instrument cue names print inline (about 80% below); apply the rule to the lexicon word, not to digits | high for a 2, tempo-family for the rest |

---

## 7. Literature

Verified here means I read the page text during this session; not verified means a secondary report only.
I could not see the pages of the print books themselves.

| source | what it says (paraphrased) | status |
|---|---|---|
| Elaine Gould, *Behind Bars: The Definitive Guide to Music Notation* (Faber, 2011), tempo and text sections | reported: all tempo information, including gradual changes (rit., rall.), goes above the staff and is set in bold roman type to distinguish it from expression text and dynamics in italics; she says dynamics should be as close as possible to the notes they refer to | **not verified** (print book not seen; second-hand via Steinberg forum posts and a search summary; no page number given) |
| Steinberg forum thread, "Rit, Rall and a tempo below the staff" (forums.steinberg.net/t/132390) | a user says Gould prescribes "all tempo information always goes above the staff" while published music mostly sets gradual changes below; a Dorico developer says below-staff is "considered a little archaic these days" | verified (page read); the Gould attribution is by the poster, not checked against the book |
| Dorico notation reference, "General placement conventions for dynamics" (steinberg.help, Dorico 1 archive) | dynamics go below the staff for instruments, where they can be read with the notes, and above for voices, so they do not collide with lyrics | verified |
| Dorico notation reference, "Positions of tempo marks" (Dorico 2/4 and Elements 6.1 pages, via search summary) | tempo marks are system objects placed above the top staff, can be repeated above instrument families (woodwind, brass, percussion, strings) in full scores | partly verified (search summary of the page; the first-version page itself returned a redirect I could not read) |
| Dorico notation reference, "Playing techniques" (Dorico 5.1, via search summary) | playing techniques, text and symbols (pizz., arco), are above the staff by default | partly verified (search summary only) |
| LilyPond Learning Manual, "Dynamics placement" (lilypond.org/doc/v2.26) | dynamics are normally placed beneath the staff; `\dynamicUp` moves them above | verified |
| MuseScore Handbook, "Staff, system and expression text" | new System Text is placed above the top staff of each system; the page does not state default above/below for staff, expression or tempo text | verified (but silent on the point asked) |
| Gardner Read, *Music Notation*; Ted Ross, *The Art of Music Engraving and Processing*; Kurt Stone, *Music Notation in the Twentieth Century*; MOLA guidelines; Finale/SMuFL defaults | not consulted | **not verified** |

---

## 8. Confidence, in one place

| claim | confidence | basis |
|---|---|---|
| tempo headings print above | high | 93-97% above; 55 files; print page; literature |
| a solo/part-specific tempo word prints above its own staff (so belongs to the staff beneath, in a gap) | medium | print page (Litolff p.9) and Sean; encodings cannot test it (Mahler artefact) |
| rit./rall./accel. above | medium-low | 72-78% above; below is a real minority; context dependent; no parts in corpus |
| expression and dynamic words below | medium-high ("usually"); "always" is false | 70.5% and 86.5% below orchestral; vocal and keyboard differ; file-level style |
| technique and a 2 / solo / tutti above | high | 97.5% orchestral; a 2 at 99.8% |
| composite dynamic words (piu f, p dolce) | low on the encodings, high by the glyph control | only 47 composites in the corpus |
| the staff-with-notes tie-breaker | high for expression/dynamic/technique/part words; not for tempo | 97-99.7% in one-sided bars; but only about a quarter (22-27%) of gap words are one-sided |
| error rates above transfer to scans | medium-low | MuseScore transcriptions, one encoder family, no publisher info |

## 9. What this does not tell us

- It does not say what Litolff or Breitkopf do word by word. The cheapest direct test of the rule is a crop
  per category in one print (as for the Adagio), shown to Sean.
- The encodings include the encoder's reflex (MuseScore text styles), an unmeasured confound. Where the
  encoding and Sean disagree, Sean wins (CLAUDE.md rule 7).
- Rates are word-weighted and a few large files carry most of an orchestral class; the file-level views in
  sections 1c and 2 show the spread.
