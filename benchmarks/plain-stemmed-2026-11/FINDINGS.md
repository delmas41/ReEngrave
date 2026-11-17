# ROADMAP 2.314 -- a plain stemmed note has a value (2026-11-17)

STAGED. Scripts here read saved records only (`tally1.py` .. `table.py`, `look.py`).

## Part 0a. Prior work (ten lines)

LEGACY (`transcribe.py`/`export.py`, frozen) joined a stem to a head by box overlap per cell and grouped chords by x alone (`voicing.group_chords_in_measure`, 0.6 of a head width), giving a chord the MODE of its
members' values; its divisi guard (2026-07) kept apart only heads whose DECIDED stem directions are opposite. STAGED kept that grouping and added the refusal 2.89 (`export._chords_whose_value_would_be_voted`: a
group whose members disagree loses every member, `chord_value_undecided`) and 2.90 (`_settle_divisi_pairs`: opposite-direction pairs stay two voices only if every chord of the bar has a decided direction and the two
streams carry equal time, else the directions come off and 2.89 refuses). Stem join: `adjudicate_head_stem` (`one_stem`, `stem_by_side/reach/flush/one_per_head`, `no_stem`, `two_stems`, `unison_two_voices`) and
`adjudicate_stem_value` (members of one stem share a value, 2.78/2.165). 2.167 found 33 of 40 sampled `no_stem` real notes had a stem the finder refused (false rest/flag box, stem cut at a ledger line); 2.202/2.204 moved
beams/stems to the stroke map (beams landed ON, stems HELD); 2.300 joined the two heads of a second on one stem. 2.306 r1-r14 (page stem reader, `OMR_PAGE_STEMS`, built OFF on `lane-2.306-stems-beams-page`, not on main):
r8 second rule, r9 two voices in a column (upper head takes the up stem), r11 contact join; "two-voice heads (91 / 20) keep the old cell join" -- the page reader abstains on them. ink-rules rows: head with no stem
found (open, mixed), head with a stem each way is two notes (kept), readers disagree on direction (open). Tried and dropped: a second stem reader beside the first, any majority vote over a disagreeing chord.

## Part 0b. What stopped the refused notes that show no flag and no beam

Records: the 2.311 beam small test's saved `lit-a` / `bra-a` gathers (2026-11-16, red-bar names; NOT today's main -- no gather for this step; the newest saved gathers `lr/work/*.off` give the same refusals on Brahms, 214 = 214, and Litolff lost its staff names there).
Population: the 307 refused notes in red bars (Litolff 127, Brahms 180) minus those whose record shows a beam level, a beam stroke at the stem, a hook or a flag reason: **143 notes (Litolff 60, Brahms 83)**.
Classes are from the record rows (each head's `head_stem` verdict, the chord mates in its cell), then looked at on the page: 40 seeded cases per plate (seed 2314, `look.py`, orange = the note, blue = its chord mates).

| what the page shows | Litolff 60 | Brahms 83 | both 143 |
|---|---|---|---|
| two stems at one place -- a second voice or a unison; each head's own value was DECIDED (quarter beside half, dotted quarter beside quarter) and the export threw the pair away as "a chord that disagrees" | 29 | 16 | **45 (31%)** |
| a chord whose stem is on the page but no member was joined to it (Brahms p4/p5 four-note dotted chords: the stem is a thin line along the heads' edge) | 6 | 22 | 28 (20%) |
| one member joined to a stem, its partner not (the other voice's stem, or a stem cut at ledger lines) | 15 | 12 | 27 (19%) |
| a single head with no stem joined | 10 | 20 | 30 (21%) |
| one stem, members' values differ (one member read hollow/dotted differently) | 0 | 13 | 13 (9%) |

In the 80 looked at: 29 / 15 / 14 / 15 / 7. Also seen: a black square that is not a note (Litolff p11, 1 of 40); heads boxed that belong to the neighbouring staff's voice (2-3).
Tiles 2, 4, 5 of Sean's 2.311 beam set (quarter, half, half in a second voice) are in the first class: Litolff `glyph/2/0/10/2/1` (quarter, stem 048254) beside `/13` (half, stem 048255); `glyph/16/0/0/0/24` (half) beside `/8` (quarter).
The record already DECIDED each head's value and each head's stem; two different decided stems at one place were then grouped by x alone.

## Part 0c. Largest cause

**Cause:** the chord grouping (`voicing.group_chords_in_measure`, called by `export._group_chords`) groups by x and by stem DIRECTION only, so two heads on two different decided stems with different values (a second voice, a unison) become "a chord whose
members disagree" and 2.89 refuses both. 31% of the population (48% of Litolff, the plate that lost more last night), and the biggest single class. A rule that FOLLOWS from the page facts ("every note on one stem shares one value" -- and so notes on two stems do not):
heads on two different decided stems are two notes, each keeps its own decided value. Not a vote, not a guess. **Process lesson:** the refusal word named the last reader in line; the record had decided both values and both stems, and the wiring (grouping)
ignored a verdict it could read -- "value computed and unread" again; and `Q.VOICES` said `one_voice` for 19 of the 29 cells (both stems down), so direction is the wrong key for a voice.
Not touched (next classes): stem on the page not joined (20%), one member's stem not joined (19%), single head no stem (21%) -- each its own mechanism (stem join), none above the fifth alone except the first.

## Part 1. The fix (flag `OMR_TWO_STEMS_TWO_NOTES`, default OFF; branch `lane-2.314-plain-stemmed`)

**Rule (plain words).** A chord is the heads of ONE stem. Two heads at one place that stand on two different stems the reader decided, and carry different decided values, are two notes: each keeps its own value, and they are written as two voices (the upper in voice 1, the lower in voice 2). NEVER: two heads on one stem with different values stay refused; a head with no decided stem never separates anything; no value is voted or invented.
Functions: `voicing.group_chords_in_measure(keep_stems_apart=)` (`_on_another_stem`), `export._group_chords`, `export._stem_pair_streams`, `_voice_split`, the slur-voice numbering in `export` (one block), `one_chord.stems_apart_enabled`.

**Controls (Sean's real marks, saved records lit-a / bra-a, export OFF vs ON).** Fail first: OFF refuses tiles 2, 4, 5 (`chord_value_undecided`); ON writes quarter, half, half = his answers; tile 12 ON writes a dotted quarter = his answer. Tile 1 (a sharp/natural, not a note) stays unwritten. Tiles 3, 8 (beamed) unchanged; tiles 6, 7, 9, 10, 11 stay refused (other causes: ledger stack, stem not joined, unison). Brahms p0 swept cells (data/hand-truth, `judge.py`): note value wrong 4 / right 369 / unread 9 on BOTH arms (identical; the 3 -> 4 is the saved record, not the flag).
On the 143 refused notes: ON writes all 29 + 16 of the "two stems" class and none of the others (`cmp.py`).

**The three measures (`lane_report`, frozen sample, `--from adjudicate`, 1793 s).** (1) file change, Litolff: notes +31 -6, rests +7, flags +19 -4, beams +7 -22 ~9, slurs -8, ties -4, blue +20 -8, red bars 186 -> 206, notes not written 2063 -> 2040; Brahms: notes +20 -1, rests +13, dots +13, ties +10 -8, slurs +11 -1, blue +1 -19, red bars 139 -> 147, notes not written 3089 -> 3069. The report's control says NEITHER ARM REPRODUCES THE RECORD (the tree moved since 20261029-night; same tree both arms, so OFF vs ON compares, but the absolute numbers are not the record's). (3) judged right->wrong 0, unwritten->wrong 0 on both plates (302 + 256 tiles). (2) 12 blind tiles of changed notes: `out/print/2.314-r1` (key `out/print/2.314-r1-key.json`), not yet answered.

**What our own look found (rule 7), and why this is NOT ready to land.** Of the 45 notes the flag newly writes, a look at the first 24 (all Litolff) found 4-5 that are not notes: the curl of an `f`/`ff` dynamic read as a filled head with a stem (Litolff p4 `glyph/4/0/0/11/7` and `/4/1/7/4/18`, p6 `/6/1/0/10/9`, p6 `/6/0/8/0/17`; the detector's own `dynamicF` box covers 1.0 / 0.27 / 0.93 of them). The chord refusal had been hiding them (real note + fake dynamic head = "a chord that disagrees"). `notehead_precision._on_a_dynamic_letter_refusal` spares them (`a_filled_head_of_its_own`). 3 of the 12 tiles show one. Red bars rise (+20 / +8): the bars are now two voices whose rests are written in both voices (`split_events_into_voices` convention), so a bar with one voice's rest does not add up -- they were partial/unread before, now marked not-add-up.
**Process lesson:** a refusal that discards a whole group also discards the fakes inside it; lifting it surfaces them. The dynamic-letter-as-head fault is upstream (GATHER/ADJUDICATE of the head, claim order: dynamics claim before heads) and has to be closed before this flag lands.
Not done: the other classes (stem on the page not joined 20%, one member's stem 19%, single head no stem 21%); landing; Sean's answers to the 12 tiles.
