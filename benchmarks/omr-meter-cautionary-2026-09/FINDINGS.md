The cautionary as a COMPETING CANDIDATE — measured, and it is n = 1.

    python3 benchmarks/omr-meter-cautionary-2026-09/run_all.py   # the numbers

────────────────────────────────────────────────────────────────────────────
2026-09-15. **No file under `tools/` was touched**; this is a measurement job
and every figure is read off artefacts already committed to the tree.

THE QUESTION. Breitkopf Brahms 1 / p.1 votes its opening meter `9/4` where the
page prints `9/8`. One system earlier the document holds its own answer — a
CAUTIONARY, the courtesy signature an engraver prints after a system's final
barline — reading `9/8` on nine staves at support 26.5, recorded on `Q.METER`'s
value and consumed by nothing. Can that be put to the voted opening as a
COMPETING CANDIDATE, and can anything separate them?

THE ANSWER, IN ONE LINE. *It can be put, the evidence structure really is
different from the refuted bars route, and the only quantity both sides state
points the WRONG WAY — while the whole corpus holds THREE cautionaries on ONE
piece of music.* **Do not ship. Get a second document**, named in §5.

Every number below is in `out/REPORT.txt`, `out/reach.json`,
`out/contest.json`, `out/digits.json`, `out/second-document.json`. Nothing here
was hand-counted.

════════════════════════════════════════════════════════════════════════════
0. ⚠️⚠️ REACH FIRST, AND HERE REACH *IS* THE RESULT
════════════════════════════════════════════════════════════════════════════

`probe_reach.py`, over 67 committed arms spanning 6 fixtures and six
re-measured trees, deduped on the address of the INK —
`(fixture, system, from_cell, raw)` — never on the address of the run:

    distinct cautionaries in the whole corpus ....... 3
    fixtures carrying one .......................... 2 of 6
    DISTINCT PIECES OF MUSIC ....................... 1
        (Brahms 1 mvt 1: the engraved render AND the Breitkopf scan)
    fixtures with zero ............................. 4
        (both Beethoven 5 finale renders, Brahms 1 finale, Litolff Beethoven 5)

**Three instances on one work. A rule fitted here is a rule fitted to a wish.**

⚠️ The dedupe matters and a naive count is 2x too big. `out/` holds the same
fixtures re-run across trees `m2`..`m7` and up to four flag arms each, and only
the `m5` and `m7` trees carry the cautionary rule at all — an earlier arm
records the same printed glyph as an ordinary mid-system SEGMENT. Counting
files would have reported the rule's arrival as the ink's absence.

⚠️ AND THE RECORDED REACH UNDERSTATES THE PRINTED ONE, BY A KNOWN MECHANISM —
checked against the source, not asserted. `_meter_changes` skips `cell == 0`
outright (*"cell 0 states the staff's OPENING"*), so **a system whose only cell
IS cell 0 can never produce a cautionary row**, however clearly the courtesy
signature is printed on it. The boundary benchmark has exactly such a page —
`boundary-m150-180` page 1, *"m154 alone, the fermata bar"*, whose own §4b says
the one-cell shape is what hid the cautionary bug from that fixture — and the
committed `full-OFF` record shows that system abstaining `no_evidence`.
`probe_reach.py` greps for the skip and says so if it ever stops being true.

════════════════════════════════════════════════════════════════════════════
1. THE THREE PAIRS — and they span every situation a contest can face
════════════════════════════════════════════════════════════════════════════

A cautionary names the meter of the NEXT system, so a pair exists only where
that next system is in the same run. All three are.

  A  brahms1-317803 (scan)     system/0/0 cell 7
       CAUTIONARY  9/8   support 26.5   9 staves
       OPENING     9/4   share 1.0     10 staves spoke
       TRUTH       9/8   -> DISAGREE — cautionary RIGHT, opening WRONG

  B  brahms1-317803 (scan)     system/1/0 cell 6
       CAUTIONARY  4/4   support  3.5   1 staff
       OPENING     unknown (`change_only`, opening_unknown_because no_evidence)
       TRUTH       6/8   -> OPENING UNKNOWN — cautionary WRONG

  C  brahms1-m1-22 (engraved)  system/0/0 cell 6
       CAUTIONARY  9/8   support 57.0  19 staves
       OPENING     9/8   share 1.0     21 staves spoke
       TRUTH       9/8   -> AGREE — both right

Truth is `report_boundary.TRUTH`, IMPORTED rather than restated so this
benchmark and the boundary one cannot drift about what the page prints.

⚠️⚠️ PAIR B CORRECTS A CLAIM IN THE BOUNDARY FINDINGS, AND THE CORRECTION
REVERSES ITS RECOMMENDATION. §4c records the safe-looking half of this idea —
*"The cautionary route is not dead in the OTHER case: a system that ABSTAINS
needs no arbitration, because there is nothing to overturn ... Reach on this
corpus: ZERO — no system that abstains here is preceded by a recorded
cautionary — so it is recorded as available and unbuilt rather than shipped
untested."*

**The reach is not zero. It is one, and that one would be filled WRONG.**
`system/1/1` reports `opening_unknown_because: "no_evidence"` and is preceded
by `system/1/0`, which carries a recorded cautionary of `4/4` against a printed
`6/8`. So the branch that looked safe BECAUSE it only fills abstentions is the
branch that, on the only instance the corpus has, converts an honest abstention
into a confident error.

════════════════════════════════════════════════════════════════════════════
2. CAN GLYPH-VS-GLYPH ARBITRATION SEPARATE THEM?  No.
════════════════════════════════════════════════════════════════════════════

`probe_contest.py` lays the two sides out in every quantity the record carries:

  pair                     caut open truth  c.support c.staves c.loose  o.share o.staves
  scan system/0/0          9/8  9/4  9/8        26.5        9       1      1.0       10
  scan system/1/0          4/4  —    6/8         3.5        1       1        —        —
  eng  system/0/0          9/8  9/8  9/8        57.0       19       0      1.0       21

The cautionary carries `support`; the opening carries `share`. **Neither side
states the other's quantity.** There is exactly ONE quantity both sides state —
how many staves read it — and:

⚠️⚠️ ON THE ONE CONTESTED PAIR THE SHARED QUANTITY READS 9 FOR THE CAUTIONARY
AND 10 FOR THE OPENING. THE WRONG READING HAS MORE STAVES. It is the same on
the engraved control (19 against 21). A contest decided on staff count picks
the opening every time, including the time it is wrong.

That is the substantive answer to the question this job was set: **the two
readings cannot be arbitrated against each other on the record as it stands**,
because the only thing they both say is the thing that gets it wrong.

── 2b. What DOES separate — and it is a different question ──────────────────

The cautionary side ALONE separates on two quantities:

    support               TRUE [26.5, 57.0]   FALSE [3.5]   empty 3.5 -> 26.5
    staves_reading_it     TRUE [9, 19]        FALSE [1]     empty 1 -> 9
    loose_digits          TRUE [0, 1]         FALSE [1]     does NOT separate
    bars_fit/contradict   TRUE [0,0],[0,1]    FALSE [0,0]   does NOT separate

⚠️ This is NOT the contest. It says whether a cautionary can be trusted at all,
not whether it beats an opening. And the interval is defined by TWO points on
one side and ONE on the other. `METER_CHANGE_FLOOR` is 3.0 and the false
cautionary sits at 3.5, so the separation is *"one staff reading a complete
meter is not enough"* — a plausible claim this corpus cannot distinguish from
an accident.

── 2c. Every candidate rule, scored against the print ──────────────────────

⚠️ `ABSTENTION -> WRONG` is counted APART from `kept_wrong`, and it is the
load-bearing column. Netted into "still wrong" — which is what a naive
right/wrong scorer does, since the answer was not right before either — the
ABSENT/DECLINED collapse disappears and the rule that commits it reads as
costless.

    rule                                  fixed BROKEN ABST->WRONG kept-R kept-W
    R0 do nothing (incumbent)                 0      0           0      1      2
    R1 cautionary always wins                 1      0           1      1      0
    R2 more staves wins                       0      0           1      1      1
    R3 support >= 10.0                        1      0           0      1      1
    R4 >= 3 staves read it                    1      0           0      1      1
    R5 fill an unknown opening only           0      0           1      1      1
    RX inverted cautionary (CONTROL)          0      1           1      0      1

⚠️ RX IS THE POSITIVE CONTROL FOR THE `BROKEN` COLUMN AND IT EARNS ITS PLACE.
Every honest rule scores BROKEN 0, and a column that reads zero for every arm
is indistinguishable from one that CANNOT be non-zero. RX installs the
cautionary upside down and breaks the AGREE pair, so the zeros are results.

Three readings of that table:

  1. R3 and R4 are the shape that works — a floor on the cautionary's OWN
     evidence, gating the overturn, refusing the fill. 1 fixed / 0 broken / 0
     abstentions lost, on 3 pairs. AND THE FLOOR HAS EXACTLY ONE BOUNDARY POINT
     ON EACH SIDE, which is the definition of fitted.
  2. R2 — the only rule expressible in a shared currency — fixes NOTHING.
  3. R5, the route the boundary FINDINGS parked as safe-but-unreached, is the
     WORST of the honest arms: the only one that fixes nothing AND loses an
     abstention.

── 2d. The quantity that WOULD separate is on the record and nothing reads it ─

Grepped, not asserted (`probe_contest.py` §4; `raw` is the grep's own positive
control, being written AND read):

    field on Q.METER_TEMPLATE   written by GATHER   read by adjudicate_meter
    raw                         yes                 YES  <- positive control
    score                       yes                 no
    runner_up                   yes                 no
    runner_up_score             yes                 no
    score_margin                yes                 no

`adjudicate_meter` reads `row.detail["raw"]` and counts staves. **A fourth
instance of *the value existed and nothing read it* in the meter family**,
after `Q.METER_GLYPH`'s `letter` flag and `score_margin`.

⚠️ `score_margin` is already REFUTED (boundary §4c: TRUE 0.0681-0.3840 vs FALSE
0.0675, a gap of 0.0006) and is not revisited. THE ABSOLUTE `score` IS THE ONE
THAT SEPARATES — boundary §4c measures 7 true system votes at 0.744-0.781
against the one false one at 0.514, an empty interval 0.531 -> 0.656 around a
`min_score` of 0.50. **That figure is INHERITED and was not re-measured here**:
it needs the locator and the page, and a cloud container has neither.

⚠️⚠️ AND HERE IS THE ONE PIECE OF GOOD NEWS, WHICH IS ABOUT SCOPE RATHER THAN
EVIDENCE. Boundary §4c refused moving `min_score` because *"`min_score` belongs
to `time_signature_locator`, which the LEGACY `transcribe` path shares ...
pricing it means re-running the eleven-work engraved benchmark and the 20-row
scan gate."* **A STAGED consumer reading the already-recorded
`Q.METER_TEMPLATE.score` shares nothing with the legacy path** —
`grep -rn METER_TEMPLATE tools/` returns no legacy caller. That scope objection
does not transfer. What DOES transfer, undiminished, is the evidence objection:
it would still be a threshold fitted to ONE wrong reading.

⚠️ SAY WHICH ACT A PROPOSAL IS. Moving `min_score` is a global threshold on a
shared reader. A staged-side floor on a recorded score is a DIFFERENT threshold
in a DIFFERENT place. **Neither is a contest** — a contest needs both sides
scored, and the template reader never looks at a system's last cell, so the
cautionary has no score to be compared with. What is available is a one-sided
*"where the opening's own score is weak, prefer the cautionary"*: a gate with a
fallback, not an arbitration.

════════════════════════════════════════════════════════════════════════════
3. ⚠️⚠️ THE CHEAP HIGH-REACH ALTERNATIVE IS DEAD, AND THAT IS THE BEST RESULT
════════════════════════════════════════════════════════════════════════════

If the two readers could be put to the SAME cell, the cautionary would be
unnecessary and the contest would have the reach of every system. The opening
is voted off `Q.METER_TEMPLATE` (template correlation on the header crop); the
cautionary is built off `Q.METER_GLYPH` (the detector's `timeSig*` boxes
stacked by `y_center`). `_meter_changes` skips cell 0, so **nobody has ever
asked what the DETECTOR says about an opening.**

`probe_digit_reader.py` asks, driving the pipeline's own `_meter_from_digits`
and `_meter_from_letter` over the committed Breitkopf Brahms 1 transcription
(pdf pages 1-3, same weights, 600 dpi, 706 staff-cells):

    staff-cells holding any timeSig glyph .......... 116
    ...forming a DIGIT STACK ...................... 69  <- positive control
    ...forming a LETTER meter ..................... 0
    systems where the detector forms an OPENING stack  1 of 6

and the one it forms is `1/1`, which `_PLAUSIBLE_METERS` refuses outright.

⚠️⚠️ AT CELL 0 OF THE VERY SYSTEM THAT VOTES `9/4`, THE DETECTOR HOLDS TWO
GLYPHS — one `timeSig1` and one `timeSig6` — AND FORMS NO STACK. At cell 1,
where the page prints the change back to `6/8`, it holds one `timeSig4` and
forms nothing. **The detector is silent at exactly the two cells where a meter
is printed.**

What it is NOT silent about: 69 stacks, of which **67 read `4/4`**, plus one
`4/1` and one `1/1`. The glyph census is `{timeSig4: 234, timeSig1: 8,
timeSig3: 1, timeSig6: 1}` on a movement printing only `6/8` and `9/8`.

⚠️ So the digit reader on this scan has, on the cells this benchmark can score,
ZERO recall and a stack population that is essentially all noise — and the
cautionary at page 0's last cell (9 staves reading 9-over-8) is the ONLY right
answer that reader gives anywhere on this document. **Its correctness cannot be
attributed to the reader being good.** That is the single strongest argument
against shipping anything from pair A.

⚠️ It also prices the false-positive side. Brahms 1 mvt 1 prints its only meter
change at m8, announced by the cautionary at the end of pdf page 0; pages 1-3
print NO cautionary at all, so every last-cell stack there is false — and there
are 3, all `4/4`, one per page-system. The rule's own `not best["bars_fit"]`
condition and `METER_CHANGE_FLOOR` cut that to the one that reaches the record.

⚠️ CAVEAT, STATED BEFORE THE RESULT AND NOT AFTER. The input is the LEGACY
`transcription.json` (`transcribe()` passes `iou=0.5, agnostic_nms=True`) where
`gather.py` takes the detector's own `0.7 / False`. Class-agnostic NMS
suppresses ACROSS classes, so GATHER sees AT LEAST AS MANY boxes: every count
above is a LOWER BOUND, and the bias runs toward the staged path seeing MORE
noise, not less. The cautionary itself stands on pdf page 0, which this
artefact does not cover.

════════════════════════════════════════════════════════════════════════════
4. ⚠️ IS THE SILENT-ARBITER LAW IN FORCE HERE? Partly
════════════════════════════════════════════════════════════════════════════

CLAUDE.md's law: *the case that most needs an arbiter is the case where the
arbiter is silent* — scoped explicitly to *"two readers that depend on the SAME
INK"*. Two things measured here bear on it:

  * AT CELL 0 THE LAW HOLDS EXACTLY. Template reader and digit reader look at
    the same printed symbol through the same raster, and on the page the
    template mangles, the detector produces two unpaired glyphs. Two readers,
    two algorithms, one piece of ink — and both fail together. A third
    instance, alongside the bars and `arc_kind`.
  * THE CAUTIONARY IS THE ONE PLACE THE LAW'S PRECONDITION IS NOT MET, and
    that is precisely its value: it is a DIFFERENT PHYSICAL PRINTING of the
    same fact, at the end of the previous system. A toner blob ruins one
    printing, not both.

⚠️ That is an argument about the evidence STRUCTURE and it is not evidence. The
corpus contains one instance of the good case (pair A) and one of the bad one
(pair B). Whether nine separate staff-printings of a courtesy signature
constitute an independent witness is exactly what a second document would
answer, and **this one cannot**.

════════════════════════════════════════════════════════════════════════════
5. THE SECOND DOCUMENT — named, ranked, and derived
════════════════════════════════════════════════════════════════════════════

A cautionary can only be engraved where a meter change falls on a system
boundary. `probe_second_document.py` joins the 97 committed dossiers to the 235
committed catalog editions and ranks by how many mid-movement changes the
encoding holds.

⚠️ CONTROL: the dossier-id -> library-id mapping is DERIVED and checked against
the 41 catalog rows carrying an explicit `dossier_prefix` (6 distinct pairs).
All 6 reproduce; the probe exits non-zero if they do not. 17 dossier ids the
mapping refuses are reported BY NAME rather than forced to a nearest match.

    dossier works ................................. 97
    ...with a mid-movement meter change ........... 32
    ...and a held edition PDF ..................... 21

The top of the ranking, and it is not close:

    beethoven-sym9-mvt4   15 changes   943 bars   Litolff 1870
        at bars 31, 39, 64, 66, 78, 82, 93, 209, 238, 332, 596, 657 ...
    beethoven-sym9-mvt3    5 changes   157 bars   Litolff 1870
    brahms-sym2-mvt3       5 changes   240 bars   Simrock 1878
    brahms-sym2-mvt2       4 changes   105 bars   Simrock 1878
    brahms-sym3-mvt1       4 changes   226 bars   Breitkopf
    beethoven-sym5-mvt4    3 changes   446 bars   Litolff 1870 x2
        at bars 155, 209, 364   <- 155 and 209 are ALREADY rendered fixtures;
                                   364 IS NOT, and is free

⚠️ A DOSSIER METER CHANGE IS A FACT ABOUT THE ENCODING, NOT ABOUT THE PRINT. It
names the BAR; whether a system break falls just before it — the only thing
that makes an engraver print a courtesy — is a property of the PLATE and is not
derivable from any committed file. Every row is a CANDIDATE to check against
the page. The ranking is simply *more changes, more chances*.

THE CHEAPEST ARM THAT WOULD SETTLE THIS, in order:

  1. `beethoven-sym5-mvt4` BAR 364 — a change on a fixture that ALREADY EXISTS,
     whose weights and windows are hand-verified, and which the meter thread
     has never rendered. `render_boundary.py --first <n> --last <m>` then
     `run_arms.py`. Zero new acquisition.
  2. `beethoven-sym9-mvt4` on the held Litolff scan — 15 changes in one
     movement on a DIFFERENT PUBLISHER'S PLATE from the Breitkopf pair A, and
     the movement CLAUDE.md already names as going `3/4 -> 2/4 -> 3/4 -> 4/4
     -> 3/4` seventeen times. Highest yield per page.
  3. `brahms-sym2-mvt3` / Simrock — a third publisher.

WHAT THE SECOND DOCUMENT HAS TO SHOW, stated BEFORE it is run so the result
cannot be fitted afterwards:

  * how many cautionaries it produces AT ALL — if a movement with 15 changes
    yields none, the mechanism is rarer than the engraving convention suggests
    and the whole idea is shelved on reach;
  * AT LEAST ONE MORE `DISAGREE` PAIR. Without one there is still exactly one
    instance of the case the rule exists for;
  * whether `support` and `staves_reading_it` STILL separate true from false
    across documents. Two points against one is not an interval;
  * WHETHER THE CAUTIONARY IS EVER WRONG WHILE THE OPENING IS RIGHT. That case
    does not exist in this corpus and is the cost side of R3/R4. Until it is
    observed, "1 fixed / 0 broken" describes a corpus with no opportunity to
    break;
  * whether the SHARED QUANTITY keeps pointing the wrong way. If a second
    document also shows the cautionary read by fewer staves than the opening,
    that settles §2's negative structurally rather than anecdotally.

════════════════════════════════════════════════════════════════════════════
6. ⚠️ WHAT IS NOT ESTABLISHED
════════════════════════════════════════════════════════════════════════════

  * n = 1 PIECE OF MUSIC. Three cautionaries, one DISAGREE pair, one AGREE
    control, one FILL. Every rule in §2c is scored on three rows.
  * NOTHING WAS RE-GATHERED, RE-ADJUDICATED OR RE-EXPORTED. A cloud container
    has no weights and no `library/`. Every figure is read off committed
    artefacts, and no proposal here has been run end to end.
  * NO OMR-NED, no edit count, no file. This says nothing about what any of
    these rules would cost in an exported MusicXML.
  * The template `score` figure in §2d is INHERITED from boundary §4c, not
    re-measured. It needs the locator and the page.
  * §3's counts are a LOWER BOUND from a legacy-NMS transcription, and do not
    cover pdf page 0 — the page the cautionary is actually on.
  * Pages 2-3 of §3 carry no committed per-cell truth; their `4/4` stacks are
    COUNTED, not SCORED.
  * The one-cell blind spot is a SOURCE-LEVEL claim, not a measurement. The
    skip is greppable; that a cautionary is PRINTED on `boundary-m150-180`
    page 1 rests on the boundary FINDINGS' description of its render, not on
    anything this session looked at.
  * `loose_digits` not separating is n = 3. Reported as *"does not separate
    here"*, never as *"does not separate"*.
  * NOTHING HERE WAS CHECKED AGAINST THE PRINT BY THIS SESSION. Truth is
    `report_boundary.TRUTH`, hand-read by an earlier one.

════════════════════════════════════════════════════════════════════════════
7. VERDICT — DON'T SHIP. NEEDS A SECOND DOCUMENT.
════════════════════════════════════════════════════════════════════════════

  * the BARS route stays dead (boundary §4c; untouched here);
  * GLYPH-VS-GLYPH ARBITRATION IS NOT AVAILABLE: the two sides carry no common
    currency, and the one quantity they share prefers the wrong reading on the
    only case that matters;
  * the CELL-0 CONTEST, which would have had real reach, is REFUTED — the
    detector's digit reader is silent at every printed opening on the one
    document that can be examined, and forms 67 spurious `4/4` stacks instead;
  * a FLOOR ON THE CAUTIONARY'S OWN SUPPORT OR STAFF COUNT (R3/R4) is the only
    shape that scores 1 fixed / 0 broken / 0 abstentions lost — on three rows,
    with the interval defined by one point on each side, and with the cost side
    (a cautionary wrong where the opening is right) NEVER ONCE OBSERVED;
  * the FILL-AN-ABSTENTION route recorded as safe-and-unreached is reachable
    and, on its one instance, WRONG;
  * the one genuinely new lever is that `Q.METER_TEMPLATE.score` IS ON THE
    RECORD AND READ BY NOTHING, and a staged consumer of it does not inherit
    the legacy-scope objection that blocked `min_score`. It inherits the n = 1
    objection instead.

**The cheapest thing that would move any of this is `beethoven-sym5-mvt4` bar
364 — a fixture that already exists.**
