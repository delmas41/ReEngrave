# GATHER: the five families that were detected and read by nothing

The next lever after the inventory/exporter/health pass, and the one those
tools identified: **the work is in GATHER, not in the adjudicators.** Five
notation families reached `GLYPH_BOX` and no typed row, so four stubs could
not have been filled where they stood and rests had nowhere to go at all.

```bash
python3 -m tools.omr.staged <pdf> --pages 2 --weights <...> --musicxml out.musicxml
```

---

## 1. What landed

`gather.gather_glyph_families` emits one typed row per glyph for **rests,
arcs, wedges, dynamic letters and articulation marks**. `Q.REST` is a new
quantity; the other four existed in `Q` and in a stub's `wants` and were
observed by nothing.

⚠️ **Routed by CLASS, not by the detector's `category`, and the hairpins are
why.** `dynamicDiminuendoHairpin` carries category `dynamic` AND a class name
starting with `dynamic`, so a prefix test alone spells a crescendo into a
dynamic word. Articulations are the mirror: all ten `artic*` classes carry
category `ornament`, which they share with `ornamentTrill`, `fermataAbove` and
`arpeggiato`.

| family | beet5 p3 | brahms p2 | reaching a typed row before |
|---|--:|--:|--:|
| rest | 228 | 350 | **0** |
| arc (tie + slur) | 199 | 686 | **0** |
| dynamic letter | 284 | 204 | **0** |
| articulation | 15 | 22 | **0** |
| wedge | 0 | 1 | **0** |

## 2. ⚠️ THE STUBS NOW ABSTAIN ON THEIR OWN POPULATION

A stub with no `subjects_from` runs on every subject at its scope. `arc_owner`
therefore abstained **once per detection** — 2,728 rows on Beethoven p3 — so
its 199 real subjects sat inside 2,529 no-ops, and its abstention meant "there
was a glyph here" rather than "I could not read this arc".

| stub | abstentions before | after |
|---|--:|--:|
| `arc_owner` / `arc_kind` | 2,728 each | **199** / 686 |
| `articulation_owner` | 2,728 | **15** / 22 |
| `wedge_anchor` | 2,728 | **0** on a page with no hairpin, 1 on Brahms |
| `dynamic` | 341 cells | **107** / 71 |

⚠️ **A zero is now meaningful.** `wedge_anchor` writes nothing at all on
Beethoven p3 because that page prints no hairpin — silence where there is
nothing to decide, rather than a no-op per glyph.

## 3. Rests, end to end — and the BAR convention as a CONSEQUENCE

`adjudicate_duration`'s domain is now `(notehead_class, rest)`. ⚠️ **A tuple,
not a second quantity**: `duration` answers ONE question — how long is this
event — for two kinds of ink, and "one quantity, one owner" is about the
ANSWER. A `rest_duration` would make every consumer ask twice for one fact.

The value comes from `rhythm._REST_DURATIONS`, **imported rather than
restated**, including the two entries it deliberately omits: `restHBar` /
`restHNr` are multi-measure indicators naming no single value, so the lookup
returns `None` and the decision abstains `unreadable_rest`. Recording the ink
and declining to read it is the honest pair — dropping it at the gather site
is how `Q.REST` came to be missing in the first place.

⚠️ **The bar-length convention is a CONSEQUENCE, not part of the reading.**
`consequences.size_measure_rest` (cause `meter`, effect `duration`, scope
CELL): a bar whose only standing duration is one dotless `restWhole` takes the
BAR's length. Its evidence is the CELL's contents and the SETTLED meter,
neither of which `adjudicate_duration` has when it reads one glyph.

Measured on the six cases the legacy fix was priced on:

| bar | result |
|---|---|
| 2/4, lone whole rest | 2.0, marked |
| 4/8, lone whole rest | 2.0, marked |
| **4/4, lone whole rest** | **4.0, marked** — the number does not move and the MARKING still must be made |
| no meter | untouched, unmarked |
| lone **quarter** rest | untouched — *the glyph is part of the rule* (34 edits) |
| whole rest **plus a note** | untouched — not a silent bar |

⚠️ **AND IT EXPOSED A REAL HAZARD IN `reconcile_duration`.** That rule offers a
DECIDED event its own beam level ±1, so a lone 4.0 whole rest in a 2/4 bar
would "land exactly" at 2.0 and be UNIQUE — **the right number by the wrong
reasoning**, reported as a HALF rest with `<type>half</type>` where the
engraving prints a measure rest with no type at all. A rest carries no beam to
re-read, so rests are excluded there and the convention is
`size_measure_rest`'s.

⚠️ **A second latent bug, introduced by adding a second writer.**
`reconcile_duration` summed `log.verdicts(...)` — every ROW, not the standing
one — so once `size_measure_rest` superseded a duration the bar would be
double-counted. That could not happen while reconcile was the only writer of
`Q.DURATION` in EVALUATE. `_standing()` resolves `supersedes` once, for both.

## 4. What reaches the file now

| | beet5 p3 | brahms p2 |
|---|--:|--:|
| notes | 516 | 664 |
| **rests written** | **209 + 19 measure rests** | **338 + 11** |
| bars padded because we read NOTHING | 148 → **48** | 60 → **4** |
| detected glyphs the record cannot carry | 761 → **533** | 1,270 → **920** |

Both files balance (939 = 744 + 195; 1,365 = 1,013 + 352) and both parse under
music21.

⚠️ **`empty_bars_padded` is now reported apart from `measure_rests_read`**, and
the split is not cosmetic: the first is a bar we read NOTHING in, the second a
bar where a whole rest was actually read. Conflating them reports a page as
full of measure rests when what it is full of is unread bars — Beethoven p3 is
48 padded against 19 read.

## 5. ⚠️ THREE CHECKS FIRED ON THIS WORK, WHICH IS WHY THEY EXIST

* **`inventory --check` refused ten `KNOWN_GAPS` entries as STALE** — the five
  starved-stub entries and their five twins now report nothing. A closed gap
  must LEAVE the list.
* **A latent `NameError` in `_problems`** surfaced the moment a domain was not
  directly gathered: it referenced `indirect`, which was never a parameter. No
  domain could reach that line until `duration`'s became a tuple.
* **`test_an_unsatisfiable_want_is_reported` followed its own instruction.** It
  said: *"if this ever reads zero, either the gather sites landed (good —
  delete the expectation) or the check stopped looking (bad)."* It reads zero
  for the good reason, so the expectation is gone and what remains is the
  DISTINCTION — the check still fires on a fabricated starved decision.

## 6. ⚠️ THE DERIVED CHECK FOUND A DETECTOR FAULT NOBODY WAS LOOKING FOR

Listing notation families by hand has the same failure mode as
`export_coverage`'s old `VISIBLE` allow-list: a class nobody thought about is
*silently unchecked*. So `coverage()` DERIVES what it has not claimed —
families claim their prefixes, `NOT_NOTATION` excuses the rest **with a written
reason**, and whatever is left is reported by name and count.

What it left, over two pages: **`arpeggiato` 98 + 86**, plus one
`stringsDownBow` and one `caesura`.

⚠️ **Neither Beethoven 5 nor Brahms 1 prints ninety arpeggios a page, and the
geometry says what these are:**

| | n | median conf | median w × h |
|---|--:|--:|---|
| `arpeggiato`, beet5 p3 | 98 | **0.39** | **56 × 388** |
| `noteheads`, same page | 711 | 0.67 | 146 × 131 |
| `arpeggiato`, brahms p2 | 86 | **0.35** | **40 × 243** |
| `noteheads`, same page | 1015 | 0.72 | 110 × 85 |

A 1:7 tall thin box at half the confidence of a notehead is a **stem or a
barline**, not an arpeggio sign. It is the largest single unclaimed class on
both pages and it is a DETECTION fault, so it is deliberately NOT excused into
`NOT_NOTATION` — `arpeggiato` really is a notation family, and burying it
there would hide the misread rather than record it.

⚠️ This is what a derived check buys over a hand list: nobody was looking for
it, and a hand-written family table would have been silently complete without
it.

## 7. What is still unrepresented, and what each needs

| family | detected (2 pages) | what it needs |
|---|--:|---|
| tie + slur | 843 | the adjudicators: `arc_kind` (tie vs slur) and `arc_owner` (which staff, and pairing across the barline) |
| dynamic | 489 | `adjudicate_dynamic`: spell `f`+`f` into `ff` by x-adjacency, then place it |
| fermata | 35 | ⚠️ **still NO QUANTITY** |
| articulation | 37 | `articulation_owner`: nearest notehead on the side its class names, within 0.75 notehead widths |
| ornament | 6 | ⚠️ **still NO QUANTITY** |
| wedge | 1 | `wedge_anchor`; and on scans this is a DETECTION problem first — the CV reader exists on the legacy path (`cf81b524`) and is not wired into `gather` |

The five gathered families are now ordinary stubs — one piece of work each,
not two.
