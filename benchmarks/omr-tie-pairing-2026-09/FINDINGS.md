# The tie pairing: diagnosed as THREE causes, one of them the instrument's own

2026-09-11. Branch `claude/tie-pairing-pitch`, off `origin/main` `0b1efb31`.
The job handed over by
[benchmarks/omr-chord-tie-2026-09/FINDINGS.md](../omr-chord-tie-2026-09/FINDINGS.md)
§9 item 1: *the tie pairing — 20 of 79 engraved links and 64 of 237 scan links
bind two different pitches; start on the engraved 20, and within those on
`mozart-sym41-mvt1`, which is 8 of 9, against `beethoven-sym5-mvt1`'s 11 of 11
correct.*

⚠️⚠️ **THE HANDOVER'S PREMISE IS WRONG AND THAT IS THE HEADLINE.** It reasons
that an engraved page's pitch reading is near-perfect, so *"the pairing is the
only suspect"*. There was a third suspect it did not list — **the arc's CLASS**
— and on the boundary case it is the one. Mozart 41's page prints **one tie and
forty-four slurs**; Beethoven 5's prints **thirteen ties and no slur at all**.
The 8-of-9 against 11-of-11 is a property of what the two pages PRINT, not of
the pairing rule, which behaves identically on both.

⚠️ **A quarter of the 25% is the PROBE.** `pairing_pitches.py` compares SPELLED
pitches, and `export._pitch_step` exists in this repo precisely because that is
the wrong key. **11 of the engraved 20 are same-STEP pairs differing only in an
accidental** — the pairing is right and the invariant is wrong about them.

⚠️ **The pairing IS a real defect, and it is 4 of 70 engraved links, not 20 of
79.** It is repaired here, by geometry and never by pitch.

⚠️⚠️ **AND A SECOND, UNRECORDED DEFECT FELL OUT OF A CONTROL FAILING: 27 of 148
engraved tie flags (18%) have no tie glyph in their staff at all, and 27 of 27
are explained by the NEXT STAFF DOWN holding it.** §6. It is not repaired here.

---

## 1. REACH FIRST, AND THE INSTRUMENT SECOND

⚠️ *A change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are the same number.* Every probe here
prints a positive figure beside every zero and exits non-zero on an empty
population.

[`probe/geometry.py`](probe/geometry.py) re-runs `_pair_ties_in_staff`'s own
arithmetic over a stored `.omr.json` and reports, per tie glyph, **every
candidate the rule considered** — the question a pooled different-pitch rate
cannot answer, because the shipped function records no link and returns only a
count.

| | 11 engraved works | 11 stored scan rows |
|---|--:|--:|
| `tie` glyphs in the record | 155 | 2923 |
| ...that PAIR (both flanks found) | **70** | **302** |
| ...that pair to the same pitch | 47 | 98 |
| ...that pair to a DIFFERENT pitch | **23** | **204** |
| links where the left side had more than one candidate | 15 | 255 |
| links where the right side did | 13 | 299 |

⚠️ These are the RULE's own pairings re-derived, not the flags in the file, so
they differ from `pairing_pitches.py`'s event-stream figures (70 against 79
engraved links). Both are reported rather than reconciled into one: the
event-stream view asks what the EXPORT sees and this one asks what the RULE
did, and §6 is the reason they cannot agree.

---

## 2. THE BOUNDARY CASE, SETTLED BY ONE `grep`

Mozart 41's nine different-pitch links, dumped with their candidates
(`geometry.py --list`; `dx` is distance to the arc's edge, `dy` head minus arc
centre, both page px):

```
B5 ->C6    L(dx,pitch,dy): [(128,'A5',92), (48,'B5',70)]   R: [(2,'C6',50)]
F#5->G5    L(dx,pitch,dy): [(115,'E5',91), (46,'F#5',70)]  R: [(2,'G5',50)]
F#5->G5    L(dx,pitch,dy): [(47,'F#5',72), (116,'E5',94)]  R: [(4,'G5',51)]
F#3->G3 ...  E3->G3 ...  F#4->G4 ...   (nine in all, every one a rising STEP)
```

Every one is a **two-note step figure**, and the pairing has the flanking heads
exactly right — the stop head sits 2-4 px past the arc's right edge. A rule
error would scatter; a step every time is a shape.

```
                       truth <tied>   truth <slur>   detected tie   detected slur
mozart-sym41-mvt1                2             88             13              60
beethoven-sym5-mvt1             27              0             17               2
```

A `<tied>` and a `<slur>` are each written at BOTH ends, so that is **1 printed
tie and 44 printed slurs** against **13 detected ties** on the Mozart page, and
**13-14 printed ties and no printed slur** against 17 detected on the Beethoven
one. **Twelve of Mozart's thirteen tie detections are false positives, and a
false `tie` lands on whatever two notes a slur connects.**

⚠️ **The ordering across the corpus is by TIE OVER-DETECTION, not by slur
share, and the distinction matters.** `brahms-sym1-mvt1` prints 164 `<slur>`
elements — more than Mozart — and produces **zero** step-apart links, because
it also prints 99 `<tied>` and its tie detections are roughly right in number
(88 against ~49 printed ties). A page is exposed when it prints essentially no
ties, not when it prints many slurs.

[`probe/arc_population.py`](probe/arc_population.py) is the table for all
eleven works.

---

## 3. THE 25% IS THREE POPULATIONS AND THEY NEED THREE DIFFERENT REPAIRS

[`probe/split_causes.py`](probe/split_causes.py), keyed on
`export._pitch_step` — imported, not restated — and a diatonic ladder so "one
step apart" is a staff-position question and not a semitone one.

| | engraved | scan |
|---|--:|--:|
| paired links | 70 | 302 |
| same pitch | 47 | 98 |
| **SPELLING** — same STEP, accidental differs | **11** | **11** |
| **STEP_APART** — exactly one staff position | **8** | **71** |
| **WIDE** — further | **4** | **122** |
| ...of WIDE, a same-pitch pair was available among the candidates | 1 | 41 |

* **SPELLING is the probe's own artefact.** The canonical tie crosses a
  barline, the far head does not restate its accidental because the tie carries
  it, and `pitch_resolver` spells that head from the key signature alone —
  `F#4 -> F4`, `D#5 -> D5`, `C#3 -> C3`. `export._pitch_step`'s docstring
  already says all of this. **So `pairing_pitches.py`'s engraved "20 of 79
  (25%)" is at most 9, and its scan "64 of 237" at most 53.** Correcting a
  published figure downward is not a repair, but it is the difference between a
  pairing rule that is wrong a quarter of the time and one that is wrong a
  twentieth of the time.
* **STEP_APART is the CLASS**, §2. All 8 engraved ones are Mozart's.
* **WIDE is the pairing**, and on engraved it is **4 of 70 (5.7%)**.

---

## 4. THE TEST THAT SEPARATES THE PAIRING FROM THE PITCH, WITH NO TRUTH FILE

A tie joins one pitch to itself, and one pitch is one STAFF POSITION — so the
two heads of a correct tie sit at the same y. That is a **second reading of the
same link, off the boxes rather than off `pitch_resolver`**, and where the two
disagree they name the culprit. [`probe/dy_vs_pitch.py`](probe/dy_vs_pitch.py),
in units of the staff's own average notehead height (one staff space, so one
diatonic step is 0.5):

**ENGRAVED**

| pitch verdict | dy~0 | dy~step | dy_WIDE | total |
|---|--:|--:|--:|--:|
| same | **47** | 0 | 0 | 47 |
| SPELLING | **11** | 0 | 0 | 11 |
| STEP_APART | 0 | **8** | 0 | 8 |
| WIDE | 0 | 0 | **4** | 4 |

**Seventy of seventy on the diagonal, zero off it.** Two independent readings —
detector boxes and the pitch resolver — agreeing on every single link is a
stronger statement than either figure alone, and it is what licenses reading
§3's engraved split as causes rather than as labels.

**SCAN**

| pitch verdict | dy~0 | dy~step | dy_WIDE | total |
|---|--:|--:|--:|--:|
| same | 98 | 0 | 0 | 98 |
| SPELLING | 11 | 0 | 0 | 11 |
| STEP_APART | **11** | 60 | 0 | 71 |
| WIDE | **2** | **12** | 108 | 122 |

The diagonal breaks, and in exactly one direction: **25 links whose two heads
sit at ONE staff position and whose resolved pitches disagree anyway.** Those
are pitch-reading faults, not pairing faults — `wrong note` is 26% of the scan
pool and CLAUDE.md already says the resolved pitch at an arc's ends is
downstream of what scans get wrong. **And 108 of 302 scan links (36%) bind two
heads genuinely far apart on the staff**, which is the pairing, and on the scan
it is the largest population of all.

⚠️ **This does not adjudicate any single arc.** A head misread by one staff
position lands in the middle band too. It separates POPULATIONS.

⚠️ **Neither family says whether the ties we write are PRINTED.** Every figure
here is internal consistency.

---

## 5. THE REPAIR: THE TWO SIDES ARE CHOSEN TOGETHER

`tools/omr/transcribe.py`, no flag, mirrored into `tools/omr/export.py`.

The shipped rule picked the nearest head in x **on each side independently**,
inside a y window of three notehead heights — which admits five staff positions
either way — with nothing preferring the position the arc actually binds. The
"distance is nearly a coin flip" shape this project has recorded for noteheads,
hairpins and dynamic letters, arriving a fourth time.

⚠️⚠️ **THE MISSING PREMISE WAS ALREADY WRITTEN DOWN, IN THE SIBLING RULE'S OWN
DOCSTRING.** `_pair_ties_in_cell` says, of not checking pitch: *"Geometry alone
is fine here because real tied notes are at the same y-position by
definition."* Neither rule has ever used it. *The value existed and nothing
read it*, in its documentation-only form.

Among the pairs the dx windows already admit, a pair whose two heads sit at
**one staff position** now outranks one that does not; among equals, the
nearest in x.

* **ADDITIVE and COMPARATIVE.** It runs only where the old rule already found
  both sides, so the set of arcs that pair is untouched, the exported tie count
  cannot move, and every delta an A/B reports is a relocation. Rescuing an arc
  whose two nearest heads are the same detection would be a second, unpriced
  change and is deliberately not made.
* **It reads BOXES and never a pitch**, pinned by a test that relabels every
  head with nonsense and asserts the pairing is identical. The same claim off
  `pitch` would be `OMR_ARC_RECLASS`'s tie->slur veto, measured and REFUSED on
  scans for exactly the reason §4's scan table shows.
* **It does not ABSTAIN.** Where no candidate pair sits at one position the old
  nearest-in-x answer stands. Abstaining is allowed by the plan and would be a
  population change; it is left as a separate, unpriced decision.

### 5a. The constant is read off an empty interval

`TIE_SAME_POSITION_MAX_SPACES = 0.25`. Measured over every paired link of the
eleven engraved fixtures, in staff spaces:

```
same pitch            n=47   max 0.168
same STEP (spelling)  n=11   max 0.034
ONE step apart        n= 8   min 0.435
further apart         n= 4   min 0.906
```

An **empty interval from 0.168 to 0.435**, and a diatonic step is half a staff
space by construction, so the gap is where the geometry says it must be. 0.25
sits in the middle of it rather than on either edge. ⚠️ On a SCAN the interval
is **not** empty (same-pitch max 0.238 against a step-apart minimum of 0.013) —
and that is a measurement of the PITCH READING, §4, not of this constant.

### 5b. The export mirror was changed in the same commit

`export._tie_flank_pair` re-derives this relation for `OMR_ARC_RECLASS`'s flag
bookkeeping and its docstring says it must mirror. Letting it drift would make
the veto clear ONE pair's tie flags while the export kept ANOTHER's. The
constant is **imported** (lazily, inside the call — `export` is deliberately
importable without the detection stack), so only the arithmetic is restated.

⚠️ `test_export.TestArcReclass.test_flank_pair_mirrors_transcribes_pairing`
already pinned the mirror — **on a fixture whose heads are all at one y, which
the new branch cannot distinguish**. A test naming a hazard it only half
reaches, the family this repo recorded on 2026-09-10.
`TestTheExportMirrorAgrees` builds the three cases that separate them.

### 5c. REACH, and the ceiling of any pairing-choice repair

[`probe/counterfactual.py`](probe/counterfactual.py) asks what a different
choice **among the candidates the rule already saw** could reach at best — an
upper bound on every repair of this shape. `oracle_pitch` reads the answer and
is printed only as the ceiling.

| | engraved shipped | engraved same-position | scan shipped | scan same-position |
|---|--:|--:|--:|--:|
| links with a candidate pair | 70 | 70 | 302 | 302 |
| ...heads at ONE staff position | 58 | **59** | 122 | **183** |
| ...two heads of the same pitch | 47 | **48** | 98 | **150** |
| ...equal to the same-pitch oracle | 47 | **48** | 87 | **132** |

⚠️⚠️ **THE +52 SAME-PITCH IS NOT INDEPENDENT EVIDENCE THAT THE REPAIR IS
RIGHT.** Both heads are on one staff, so same-y and same-pitch are near
equivalent by construction: a rule that prefers same-y is being scored by a
quantity it optimises. It says the rule is now SELF-CONSISTENT. What it does
not say is whether the pair is the printed one — two spurious detections at one
position agree perfectly. **Read it as reach, never as accuracy.**

⚠️ **The engraved reach is +1 link, and only one of the eleven works moves this
count**: `bruckner-sym5-mvt1`, 3 same-position pairs → 4. §4's engraved table is
why — that family is already 70 of 70 self-consistent, so there is almost
nothing for this to find there. **The repair is addressed to the scan**, where
the same probe reads 122 → 183.

⚠️⚠️ **THIS PROBE COUNTS PROPERTIES, NOT IDENTITY, AND THEREFORE UNDERSTATES
WHAT MOVES.** A relocation between two heads that are BOTH at one staff position
and BOTH the same pitch changes none of these columns and still writes a
different note element. §7a's arm moved a `<tied>` on `brahms-sym1-mvt1`, a work
this probe reports as unchanged on every column. Use it as a ceiling on property
improvement, never as a count of links that move.

---

## 6. ⚠️⚠️ A SECOND DEFECT, FOUND BY A CONTROL FAILING: 27 ORPHANED TIE FLAGS

The cheap way to price a transcribe-side change is to replay the rule over a
stored `.omr.json`. That was built
([`probe/repair_arm.py`](probe/repair_arm.py)) and **its own control refused
it**: strip every tie flag, replay BOTH shipped rules, require the flags back
identical.

```
beethoven-sym5-mvt1    stored= 22  replay= 16   MISMATCH  -6
brahms-sym1-mvt1       stored= 89  replay= 68   MISMATCH  -21
brahms-sym4-mvt1       stored= 14  replay=  2   MISMATCH  -12
...                                             7 rows OK
reproduced 159 stored tie flags over 11 rows; 4 rows MISMATCH
```

The missing flags sit on noteheads in staves holding **no tie glyph anywhere
near them**. The ordering says why, and it is one `grep`:

```
transcribe.py:2289   _pair_ties_in_cell              sets flags
transcribe.py:5356   _pair_ties_in_staff             sets flags
transcribe.py:5557   _dedupe_cross_staff_detections  REMOVES the losing copy
```

A measure cell is padded above and below, so a neighbouring staff's tie is
detected in this staff's cell too. **Both copies pair. Then dedupe awards the
glyph to one staff and deletes the other copy — and the flags the deleted copy
set stay behind.** The losing staff exports a `<tied>` for ink the pipeline
itself decided was not its own, and the winning staff gains no tie because
pairing has already run.

Worked example, `brahms-sym4-mvt1` staff 8 measure 4: a whole note at page
`[3482, 3552]` carries `tied_to_next`, its own measure holds only a `slur`, and
a `tie` glyph sits at `[3530, 3604]` **in staff 9**.

[`probe/orphan_flags.py`](probe/orphan_flags.py) counts them with no truth file:

| | flagged heads | ORPHANED | of which a NEIGHBOUR staff holds the tie |
|---|--:|--:|--:|
| 11 engraved works | 148 | **27 (18%)** | **27 — all of them** |
| 11 stored scan rows | 460 | 5 (1.1%) | 0 |

**Twenty-seven for twenty-seven, zero exceptions** — the same signature
`arc_owner` reported for its twelve moves (plus or minus one staff, six each
way, zero exceptions). It is an ENGRAVED-side defect: on a scan the
neighbouring staff usually never detects the duplicate at all.

⚠️ **NOT REPAIRED HERE**, and the repair is not obvious: clearing a flag whose
glyph was deduped away needs the flags to carry WHICH GLYPH set them, which is
`Q.TIE_LINK` — the gap two previous sessions declared and left open. Ranked in
§10.

⚠️ It also means **a stored `.omr.json` cannot be replayed faithfully**, which
is a constraint on every future tie measurement, not only this one.

---

## 7. THE PRICE

### 7a. ENGRAVED — re-transcribed, because nothing cheaper can see it

⚠️⚠️ **AN EXPORT-ONLY ARM IS STRUCTURALLY BLIND TO THIS CHANGE.**
`_pair_ties_in_staff` runs inside `transcribe`, so `reexport_arm.py` and
`tree_arm.py` would report a clean zero that is the instrument. Checked rather
than assumed: `grep -n _pair_ties_in_staff tools/omr/export.py` returns three
hits and **all three are comments**. The replay escape was refused by §6. So
each fixture is read again, by each tree.

[`probe/retranscribe_arm.py`](probe/retranscribe_arm.py) refuses two trees
whose `transcribe.py` is identical, and **excludes any row whose DETECTIONS
moved** rather than folding the detector's jitter into the delta.

Run on the two works the reach probe named, each re-read by each tree:

```
                       base          fix
brahms-sym1-mvt1     351 edits / 44 <tied>     351 / 44    (+0)
bruckner-sym5-mvt1   199 edits /  4 <tied>     199 /  4    (+0)

comparable rows: 2 of 2   (excluded because detections moved: 0)
summed edits  base=550   fix=550   delta +0
<tied> starts base=48    fix=48
tie FLAGS     base=[48, 49]   fix=[48, 48]
```

**Zero edits, and the tie COUNT is held at 48 exactly as the design requires.**

⚠️⚠️ **AND THE ARM IS NOT DEAD — BOTH FILES DIFFER, WHICH IS THE CONTROL THAT
MAKES THE ZERO A RESULT.** The probe prints a warning when no row moves, so it
was checked rather than assumed:

```
bruckner-sym5-mvt1: files DIFFER
1770d1769
<         <tie type="stop"/>
1773,1775d1771
<         <notations>
<           <tied type="stop"/>
<         </notations>
1784a1781
>         <tie type="stop"/>
```

One `<tied type="stop">` moves from one note to another, on each work, and
**OMR-NED charges nothing for it** — the metric pairs by pitch, so a stop
relocated onto a note of the same pitch is invisible to it. That is a result
about the METRIC as much as about the change, and it is the third time this
thread has hit it.

⚠️ `tie FLAGS` falls 49 → 48 while the exported `<tied>` COUNT holds at 48:
two arcs now share an endpoint head, so one head carries a flag that two arcs
set. The number of PAIRS is unchanged; the number of FLAGGED HEADS can fall.
Reported apart because they are different facts.

⚠️ **`comparable rows: 2 of 2, excluded 0`** is the same control that excluded
**11 of 11** on the first run (§9 item 10). It is the reason these two rows can
be read at all.

⚠️⚠️ **TWO ROWS, NOT ELEVEN, AND THE REACH PROBE THAT PICKED THEM IS ITSELF
LIMITED.** The full eleven-work sweep was abandoned: `OMR_SURYA_KEEP_ALIVE=1`
is set in this environment and the run wedged on the SHARED Surya server (a
child at 0.0% CPU with its CPU clock frozen for five minutes — the stall
CLAUDE.md documents), so it was restarted under the documented unattended
escape `OMR_SURYA_KEEP_ALIVE=0`, which pays a ~70 s model load per page and is
far slower. ⚠️ **Only this session's own PIDs were killed**; the shared
`llama-server` was left alone.

⚠️ **`counterfactual.py` named ONE reachable work and the arm moved TWO**, and
that is a limitation worth carrying: **it counts link PROPERTIES (is the pair
at one staff position, is it the same pitch), not link IDENTITY.** A relocation
between two heads that are both at one position and both the same pitch changes
no count and still writes a different note element. On the freshly-read Brahms
record it reports `shipped == argmin_dy` on every column, and the file moved
anyway. *Counting cannot see a relocation; only naming the NOTES can* — the
arc-export session's lesson, arriving on a different instrument.


### 7b. SCAN — NOT MEASURED, and the reason is not cost alone

Every row of the 20-row gate would have to be re-transcribed — weights,
`library/`, hours per row — and CLAUDE.md prices that gate's noise floor at
**plus or minus 6 edits**, while §5c predicts the whole scan effect is a
relocation of roughly 60 links over 11 rows. **A per-row floor that size cannot
resolve that**, and the export-only and replay routes are both closed (§6,
§7a). So the scan side is quoted from §5c's reach and §4's grid and **no scan
OMR-NED figure is claimed**.

⚠️ That is the honest position and not a shortfall to be papered over: the
change is aimed at the scan family and its price there is unmeasured.

### 7c. `OMR_ARC_RECLASS` RE-PRICED, because it is the mechanism §3 points at

The handover's ranked next step leads to a veto that **already exists, is
already measured and is already refused**. It is re-priced here because the
cause split is evidence that did not exist when it was refused, and because
CLAUDE.md's figure for it (*"engraved 0.1306 -> 0.1306, +2 edits, 24
firings"*) predates the chord-tie repair and so no longer describes the tree.

[`probe/engraved_arm.py`](probe/engraved_arm.py), export-only and
env-switched — sound here because `OMR_ARC_RECLASS` is read inside
`export.py`:

```
off  OMR_ARC_RECLASS=0   summed edits 2530   <tied> 79 start / 80 stop
on   OMR_ARC_RECLASS=1   summed edits 2536   <tied> 69 / 70     delta +6
files that DIFFER between arms: 7 of 11
```

⚠️⚠️ **MEASURED TWICE, AND THE SECOND RUN IS THE REPORTED ONE, BECAUSE §5b's
MIRROR MOVED IT.** Before the mirror landed the same arm read **2538 / +8** and
`<tied>` 68/69. `_tie_flank_pair` is the veto's own re-derivation of the pairing
relation, so improving the pairing improves what the veto sees — an interaction
between two changes in one session, and a reader taking the first figure would
be quoting a tree that no longer exists. Both are given rather than one.

⚠️ `off = 2530` reproduces the chord-tie session's `fix` arm **to the edit** on
a different instrument — an independent control neither session planned.

**The +8 is not the provable half.**
[`probe/reclass_reasons.py`](probe/reclass_reasons.py) splits the firings by
rule, and the four do not carry equal weight:

| rule | engraved (before / after §5b) | scan (before / after) | provable? |
|---|--:|--:|---|
| `tie_to_slur_flagged_diff_pitch` | 12 / **11** | 197 / **137** | **yes** — the flanked pair is step-different |
| `tie_to_slur_unpaired_diff_pitch` | 6 / 6 | 14 / 14 | yes, but it can only ADD a slur |
| `tie_to_slur_flagged_span` | 1 / 1 | 21 / **47** | no — a third event under the arc, and an empty measure spends no ordinal |
| `tie_to_slur_unpaired_span` | 6 / 6 | 114 / 114 | no |

⚠️⚠️ **AND THAT LEFT-TO-RIGHT MOVEMENT IS THE ONLY SCAN-SIDE EVIDENCE THIS
SESSION HAS FOR THE REPAIR.** `_tie_flank_pair` mirrors the pairing relation, so
running the veto over the SAME stored scan records before and after §5b asks
what the new relation does on the scan family without re-transcribing anything:
**step-different flanked pairs 197 → 137, sixty arcs that the veto would have
had to delete as impossible and no longer must.** ⚠️ It carries §5c's warning
exactly — a rule that prefers same-y produces fewer step-different pairs by
construction, so this is the reach expressed in the veto's own currency and not
an independent check. ⚠️ The 26 that moved into `flagged_span` are arcs that are
still impossible, by a different and INFERRED rule; they are not repaired, only
re-explained.

On the **three works where only `flagged_diff_pitch` fires**
(`mozart-sym41-mvt1`, `brahms-sym4-mvt1`, `beethoven-sym3-mvt1` — 11 of the 12
provable removals under the pre-mirror tree) the arm is **-4 edits**, i.e.
BETTER. Every other work fires
a span or unpaired rule and every one of those is edit-positive. **So
CLAUDE.md's "all +130 is in the tie->slur half" needs splitting: the tie->slur
half is FOUR rules, and on the engraved family the provable one is
edit-negative while the inferred ones pay for it.**

And scored the way a REMOVAL should be — against the tie inventory, not against
a symmetric metric that rewards under-prediction
([`probe/tie_inventory.py`](probe/tie_inventory.py), truth-side `<tied
type="start">` counts):

```
work                 truth   off    on
mozart-sym41-mvt1        1     9     1     +8 over-emission -> EXACTLY RIGHT
brahms-sym4-mvt1         6     7     6     +1 -> +0
beethoven-sym3-mvt1      3     2     1     -1 -> -2
bruckner-sym5-mvt1       6     4     4     -2 -> -2   (was -3 before §5b)
summed |per-work error|       25    17
```

⚠️ **The one row that gets "worse" is the removal of a provably-impossible
tie.** That work already under-detects, so removing a step-different link
pushes the count further below a truth it was never going to reach. **The
inventory metric cannot tell a wrong removal from a right one on an
under-detecting page**, which is why the firing split above is reported beside
it and neither is quoted alone.

⚠️ `bruckner-sym5-mvt1` was −3 before §5b's mirror landed and is −2 after: **the
pairing repair removed a veto firing**, which is the same interaction as the
197 → 137 above, arriving on a second instrument.

Scan, same instrument (`reexport_arm.py`): `off = 34739`, `on = 34888`,
**+149** — CLAUDE.md records +130 at an older baseline, and the pre-mirror run
of this arm read +144. **The refusal stands**,
and §4's scan table is now direct evidence for the reason CLAUDE.md already
gives for it.

---

## 8. WHAT IS **NOT** ESTABLISHED

* **No reading was checked against a print.** Every adjudication here is either
  the tie's own pitch invariant, the boxes' own y, or a truth ENCODING's
  element count.
* **The scan price of the repair is unmeasured** (§7b), and §5c says the scan
  is where its whole reach lies. The engraved arm is the only priced arm, and
  it is **TWO WORKS**, not eleven (§7a) — chosen by a reach probe that is itself
  known to understate what moves.
* **The engraved zero is a zero on two works.** It means *this relocation costs
  nothing on OMR-NED*, which the exported diff shows is partly a fact about the
  metric (it pairs by pitch, so a stop moved onto a same-pitch note is
  invisible). It does **not** mean the relocation is correct — no print was
  consulted.
* **§5c's +52 is self-consistency, not accuracy** — its own warning.
* **11 of the 20 scan rows**, one page each, and the engraved tie population is
  small (70 paired links, four of them WIDE).
* **The orphaned-flag defect is counted, not repaired** (§6), and its count is
  an upper bound on one cause and a lower bound on another — a flag whose glyph
  moved to a staff that ALSO holds its own tie near that x is not counted.
* **`arc_population.py`'s truth counts are ELEMENTS**, halved to ties only in
  prose; a tie CHAIN writes more elements than it has ties.
* **No staged-pipeline page was gathered.** `adjudicate_arc_kind` and
  `arc_owner` decide per arc on that path and are untouched here.
* **OMR-NED attribution on a scan is void** (92.5% of edits are
  bulk/unpaired); only the direction of a controlled A/B is quoted, and no
  category breakdown is.

---

## 9. REFUSED / REFUTED, so nobody re-tries them

1. **"The Mozart Viola's divisi double stops are the cause."** REFUTED by the
   candidate dump: its two left candidates stand at dx 47 and 115 —
   SUCCESSIVE NOTES, not two heads at one x. No Mozart link involves a chord
   at all.
2. **"The arc's span is wider or narrower than the notes it binds."** REFUTED:
   on all nine Mozart links the stop head sits **2-4 px** past the arc's right
   edge. The flanking is exact; what is wrong is that the arc is a slur.
3. **"The flanking rule should pick the nearest head at the ARC's own y."**
   Half right, and the half that is wrong matters: the ARC's y is 50-94 px off
   its heads (it is drawn clear of them), so nearest-to-the-arc is not a usable
   key. What works is nearest to EACH OTHER — §5.
4. **A pitch VETO in the exporter.** That is `OMR_ARC_RECLASS`'s
   `tie_to_slur_flagged_diff_pitch`: built, measured on both families and
   refused (§7c). Re-implementing it would be a duplicate. Its refusal is not
   re-litigated here; it is re-priced, and §7c's split is the new evidence.
5. **SEARCHING for a same-pitch partner** rather than vetoing. Refused as the
   plan asks: it would manufacture ties between notes that merely share a
   pitch. The repair prefers same-POSITION, which is a fact about boxes, and it
   is comparative — it cannot reach outside the candidates the old rule already
   accepted.
6. **A joint argmin over the candidate product set.** It would rescue an arc
   whose two nearest heads are the same detection — a tie the old rule refused
   — and that is a COUNT change, not a relocation. Pinned refused by a test.
7. **ABSTAINING where no pair sits at one position.** Allowed by the plan,
   deliberately not taken: it changes the population and is separately
   unpriced.
8. **Replaying the tie rules over a stored `.omr.json` to price this cheaply.**
   Refused by its own control, §6 — and that refusal is the second finding.
9. **Reading `pairing_pitches.py`'s different-pitch rate as the pairing's error
   rate.** It compares SPELLED pitches; 11 of the engraved 20 and 11 of the
   scan 64 are the accidental-expiry artefact `_pitch_step` exists for (§3).
10. **Comparing the WHOLE record for the detection-set control.** It caught the
    weights path, a timing field, and — the one that mattered — that the base
    tree had no `.venv-surya` beside it, so Surya self-disabled there and
    Tesseract read the words. **All eleven rows excluded, for a reason that was
    not the detector.** CLAUDE.md's documented worktree trap, arriving inside a
    control built to catch something else. The control now compares only the
    DETECTIONS, which is the only thing this change could move.

---

## 10. WHAT A NEXT SESSION SHOULD DO, ranked

1. ⚠️⚠️ **THE 27 ORPHANED TIE FLAGS** (§6). Engraved-side, 18% of tie flags,
   attributed 27 for 27, and it needs `Q.TIE_LINK` — the gap two previous
   sessions declared and left open, now with a THIRD symptom and a probe that
   counts it. **Three symptoms, one fix.**
2. **The 115 links with no end in the next event** — the chord-tie session's
   own item 2, still unexamined, and §6 is now a candidate cause for part of
   it: a `tied_to_next` whose glyph was deduped away has no partner by
   construction.
3. **The scan price of this repair.** §7b says why it was not measured; it
   needs a 20-row re-transcribe or a staged-path equivalent.
4. **Tie/slur CLASSIFICATION**, which §2 says is the whole of the engraved
   different-pitch population. `OMR_ARC_RECLASS` is the export-side veto and is
   refused on scans; the untried lever is the DETECTOR, and `arc_kind`'s own
   write-up already measures that its position grammar is a coin flip on the
   arcs it can speak about.

---

## 11. CONTROLS

* **Every probe exits non-zero on an empty population** and prints a positive
  figure beside every zero (155 and 2923 tie glyphs; 148 and 460 flagged
  heads; 70 and 302 paired links).
* **The A/B refuses two trees whose `transcribe.py` is identical**, and
  `engraved_arm.py` refuses two arms naming the same environment.
* **`files that DIFFER between arms` is printed**, and a zero there is reported
  on stderr as *"inert, or the arm could not see it"* rather than as a result.
* **The replay control FAILED and was believed** (§6) rather than weakened
  until it passed. It prints the number of flags it reproduced, so "identical"
  cannot mean "both empty".
* **`off = 2530` reproduces another session's arm to the edit** on a different
  instrument.
* **Full suite: `3755 passed, 11 skipped`** in 581.70 s of TEST time, against
  a baseline on `main` of **3741 / 11**. The arithmetic is exact — this branch
  adds 14 tests and 3741 + 14 = 3755 — which is a cheaper control than reading
  the number alone. ⚠️ `581.70s` is TEST time and not elapsed, the figure that
  would make a starved run look normal in a log; the wall clock was checked
  separately and agreed here.
* **`health --check`, `inventory --check` and `gather_coverage` all exit 0.**
  ⚠️ `gather_coverage` reads 75 declared / 41 observed where CLAUDE.md's prose
  says 69 / 39 — that line already carries its own warning not to be quoted,
  and the tool is the count. Nothing here changed it.
* **Mutation battery**: [`probe/battery.sh`](probe/battery.sh), results in
  [`out/battery.txt`](out/battery.txt). Every mutation is anchored on a WHOLE
  expression and refused unless it applies exactly once; "NOT APPLIED" is a
  harness failure, never a survivor. ⚠️ Arms that break the same-position
  branch could all go red on a suite that simply refuses every tie, so **ARM P
  is the positive control in the same class** — it stops the branch being
  entered at all, and the suite must still go red.

### 11a. The battery, and its two survivors

First run: **six RED, two SURVIVED**, with ARM 0 and the NOT-APPLIED report
both behaving. Both survivors were adjudicated rather than argued away, and
they are different things:

* **`min` → `max` among same-position pairs (take the FURTHEST) SURVIVED, and
  it is a REAL GAP.** Every test above offers exactly ONE same-position pair,
  and a rule that takes the furthest of one takes the same one. Closed by
  `TestTheTieBreakAmongSamePositionPairs`, which offers two — on the start
  side and on the stop side, because the tie-break sums two terms and a test
  naming only the start reaches half the hazard. *One red arm is not a
  battery*, and this is what the rest of it bought.
* **Swapping the two dx terms SURVIVED and is an EQUIVALENT MUTANT**, not a
  gap: `dxl + dxr` is symmetric, so relabelling the loop variables cannot
  change the answer. The arm is REMOVED and the reason recorded in the
  battery's own source, so nobody writes it again.

⚠️ A third arm reported **NOT APPLIED** — it anchored on a line the branch does
not contain. The harness treats that as a harness failure and not a survivor,
which is the whole reason the anchor must be a whole expression; the arm is
removed rather than left printing noise.

Second run: **nine arms, all RED**, ARM 0 SURVIVED at 333 passed.

---

# §3.2b — THE STAGED PORT: `Q.TIE_PAIR` (2026-09-29)

Branch `claude/tie-pairing-3.2b`, off `origin/main` `efe7eb66`. ROADMAP 3.2b.
Path: **STAGED**. The legacy `transcribe._pair_ties_in_staff` (§5 above) is the
reference reader and is untouched.

CONVENTION (CLAUDE.md §10, measured in §5a): a tie's two heads are at ONE staff
position, and a tie FLANKS them. ASSUMED / WHAT WOULD FALSIFY IT / NOT
CONFIRMED: `TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS = 1.0` (below) — a Sean crop of a
scan tie whose start head sits more than one width inside the box.

## 3.2b.1 Reach first — the brief's premise was half wrong

The brief said the staged MusicXML *"may write no `<tie>` at all"*. It did
write ties — `staged/export._pair_arcs` has paired them since the arc-export
landing — but with **SLUR COVERAGE** (`_paired_spans` → `_noteheads_under`,
the heads UNDER an arc), which is the wrong question for a tie (it FLANKS its
heads; `export._tie_flank_pair`'s own docstring says so). Measured on the two
records, before (`base`, `tie_pairing: exporter`):

| | engraved p0 (Verovio, exact truth) | Litolff `984073` p3 (count page) |
|---|--:|--:|
| arcs decided `tie` (`Q.ARC_KIND`) | 22 | 135 |
| tie links the exporter marked | **1** | 37 |
| …of those, two heads of ONE placed pitch | 1 | **13** |
| …two DIFFERENT pitches | 0 | **24** |
| `<tie type="start">` in the file | 1 | 27 |
| tie symbols the page truth draws | 11 | — |

(`probe/readjudicate_tie_pair.py`; the per-link pitch split is the exporter's
own spans captured in one process. The 24 different-pitch ties on Litolff p3
are 65% of what the base file ties, each one a tie between two notes.)

## 3.2b.2 What was built, and in which stage

* **ADJUDICATE, `adjudicate_tie_pair`** (`adjudicators/ownership.py`, after
  `Q.ARC_KIND` / `Q.ARC_OWNER` / `Q.GLYPH_OWNER` in `ORDER`). Per tie arc,
  `Q.TIE_PAIR = {"start": glyph, "stop": glyph}`. Not EVALUATE: which heads
  flank an arc is a reading that can have zero or several answers, so it must
  be able to abstain and narrow. The rule is the legacy one — heads within 3
  widths outside each end, within 3 head heights of the arc, the pair at ONE
  position (`TIE_SAME_POSITION_MAX_SPACES`, imported) — with the legacy's two
  guesses turned into refusals: no same-position pair **abstains**
  `no_pair_at_one_position` (legacy: nearest in x); several **narrow**
  `more_than_one_pair` (legacy: nearest). Of two heads at the partner's
  position on one side only the nearer is a candidate — a tie joins
  CONSECUTIVE notes, so that is forced, not preferred.
* Three additions the records forced, each found by a failing reading:
  - **a barline-cut half** (arc end within `_SLUR_BOUNDARY_SPACES` of its bar's
    edge, imported) searches the whole adjacent bar on that side — 6 of 13
    engraved arcs abstained `no_start_head` without it; both halves now name
    the same pair and EXPORT writes it once (`tie_arcs_naming_an_already_named_pair`);
  - **a scan tie box begins OVER its start head** (Litolff: centres 0.37–0.54
    widths inside) — `TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS = 1.0`, NOT swept;
  - **an arc cut at BOTH edges of its bar abstains `spans_a_whole_bar`** — a tie
    never crosses a whole bar. The first Litolff crop set paired two C3s a bar
    apart through a `tie` box lying on a staff line; 20 of 135 Litolff p3 tie
    boxes are this shape.
* **System edges are named, never guessed across**: `runs_off_the_system` /
  `enters_from_previous_system` when nothing on the staff follows / precedes
  the arc in the system's last / first bar. `no_head_near_the_arc` when
  neither side has a head — usually the TWIN of a tie filed on the next staff:
  `arc_owner` asks which heads an arc COVERS, a tie covers none, so it never
  moves one (5 engraved, 17 Litolff p3). ⚠️ That is an `arc_owner` gap for
  ties, recorded here, not repaired.
* **EXPORT** reads the record's pairs and nothing else (`_record_tie_pairs`,
  `_record_tie_spans`), so the record and the file cannot pair a tie two ways
  — the objection §3 of the chain FINDINGS raised against a record-side
  pairing. A record with NO `Q.TIE_PAIR` row at all (every shared record
  gathered before today) keeps the exporter's own pairing and the report says
  which ran (`tie_pairing: record | exporter`). An ABSTAINED tie is never
  paired by the exporter instead (tested: rule 8).
* **The pitch check** (brief item 3): a named pair whose two placed pitches
  differ after EVALUATE is not written and is REPORTED by its two heads
  (`tie_contradictions`, `tie_pitch_contradiction`); same step with another
  spelling counts apart (`tie_spelling_differs`). Across two voices:
  `tie_ends_in_two_voices`. Every named pair that did not reach the file is
  counted (`tie_end_not_in_file`, `tie_pair_<reason>`).
* `gather_coverage`: `tied_to_next` / `tied_from_prev` → `TIE_PAIR`;
  `NO_VOCABULARY` is now EMPTY. What closed is the LINK; the CHAIN is still
  the exporter's count over a part, and a link across a SYSTEM BREAK is not
  named (2 of 632 on Breitkopf in the chain FINDINGS) — said in the mapping's
  own comment.

## 3.2b.3 After — one saved record each, re-adjudicated, no re-gather

`probe/readjudicate_tie_pair.py` rebuilds the record's own GATHER rows, injects
the five upstream verdicts as saved, decides `Q.TIE_PAIR` on today's tree, and
exports base and arm from the same record in one process.

**Engraved p0** (`out/3.2b-engraved-p0.json`):

| | base | arm |
|---|--:|--:|
| `<tie type="start">` | 1 | **7** |
| written pairs RIGHT against the page truth | — | **7 of 7** |
| WRONG | — | **0** |
| drawn ties MISSED | — | 4 |

`Q.TIE_PAIR`: 13 paired (7 unique + 6 second halves), 5 `runs_off_the_system`,
4 `no_head_near_the_arc`, 1 `not_a_tie`. The 4 missed truth symbols are the
system-break ties (Verovio's box for a tie crossing a system is the
continuation stub at x≈398); the record abstains `runs_off_the_system` on the
halves this page holds — the same four by count, NOT position-matched.
Contradictions 0.

**Litolff p3** (`out/3.2b-litolff-p3.json`):

| | base | arm |
|---|--:|--:|
| `<tie type="start">` | 27 | **5** |
| of the exporter's marked links, different pitches | 24 of 37 | **0** (by construction) |
| contradictions reported | — | **3** |

`Q.TIE_PAIR` over 135 tie arcs: 35 paired (19 unique pairs), 10 narrowed, 20
`spans_a_whole_bar`, 19 `no_start_head`, 17 `no_head_near_the_arc`, 16
`no_pair_at_one_position`, 9 `no_stop_head`, 7 `enters_from_previous_system`,
2 `runs_off_the_system`. Of the 19 pairs: **11 never reach the file**
(`tie_end_not_in_file` — 37 of 78 decided ends on this page are
`duration_narrowed:beams_ambiguous`, the missing-notes funnel, not this
decision), 3 contradictions, 5 written.

⚠️⚠️ **THE SCAN FILE LOSES 22 `<tie>`s, AND THAT IS THE HONEST NUMBER.** 24 of
the 37 links the base wrote joined two different pitches — not ties at all
whatever the page prints — and **none of base's 13 same-pitch links is a pair
the record names** (checked link by link), so they are pairs the coverage rule
found under an arc, not pairs flanking one. Whether any of them is a printed
tie is a question for the print; nothing here says the base's 13 are wrong.

⚠️ **A dangling tie start** (5 starts, 4 stops in the arm file): link
`glyph/3/0/0/3/7 → glyph/3/0/0/4/8` has its STOP in a bar ROADMAP 2.8 held out
(bar sum), so the stop is never rendered. The base file has the same shape (27
starts, 26 stops). Not repaired: the hold-out is decided at render time, after
the pairing; it needs the pairing to be re-checked per rendered bar.

## 3.2b.4 Crops — 8, for Sean (`out/print/3.2b-tie-0*.png`, manifest `3.2b-manifest.json`)

`crop_ties_3_2b.py` reads only `out/3.2b-litolff-p3-crops-cache.json`; frame
control on the home staff's own lines (can fail; 0 refused); START bracketed
RED `S`, STOP MAGENTA `E`, every naming arc ORANGE, the staff GREEN. 5
`linked` (every marked link on p3) + 3 `contradiction`. Every row
`VERDICT_none_yet: null`.

⚠️ **My own look, NOT a verdict:** #1, #2, #4, #5 read as printed ties on the
bracketed notes; **#3 is not** — its `tie` box lies on the staff's top line
(the same staff-line shape `spans_a_whole_bar` now refuses when it spans a
bar; this one ends inside one). #6 and #8 look like one of the two pitches
misread (#8: the E head's box sits low on the head); #7's naming arcs sit ~3
spaces below its heads, so there the PAIR may be spurious rather than a pitch.
Sean adjudicates.

`arc_dy_spaces` (arc centre to its pair, recorded on every paired verdict):
engraved 0.36–0.53; Litolff 0.04–2.95 with no gap — the legacy 3-head-height
window cannot be tightened on this evidence.

## 3.2b.5 Not established / next

* Only 2 records, 2 pages; Breitkopf not run (the chain FINDINGS' 140/632
  barline and 2 system-break links are its figures, not re-measured here).
* The shared acceptance records carry no `Q.TIE_PAIR` until re-gathered or
  re-adjudicated; `tools.omr.acceptance` exports existing verdicts, so its
  files keep the exporter's pairing (reported as `tie_pairing: exporter`).
* Next, ranked: (1) Sean's verdicts on the 8 crops; (2) resolve
  `more_than_one_pair` for tied chords with one arc per member (a staff-level
  assignment by y order — INFER, labelled); (3) `arc_owner` for ties (flanked
  heads, not covered); (4) drop a tie start whose stop's bar is held out;
  (5) the cross-system link (needs the part, i.e. extracting `build` out of
  `export.py`, chain FINDINGS §7 item 2).

## 2.54 — adjacency, and the whole-bar refusal was wrong for a real case

Sean, on the 2.52 sheet (DECISIONS 2026-10-01): *"whenever there are 2 notes
of the same pitch next to each other in a bar or across barlines and there
is an arched line between them it is a tie. The notes have to be next to
each other regardless of measures/barlines and they have to have the same
pitch."* Checked `adjudicate_tie_pair` against this and found two
contradictions:

* **`spans_a_whole_bar` refused unconditionally** whenever an arc was cut at
  BOTH edges of its own bar, on the theory that bar "would have to hold
  nothing at all". That is true of the staff-line-misread case the first
  Litolff crop found, but it is also exactly the SHAPE of a real tied
  whole/half note that fills its own bar and ties to the next bar's first
  note — which Sean's rule explicitly keeps ("regardless of measures/
  barlines"). Fixed: the refusal now fires only when the arc's own bar holds
  NO notehead at all; a bar that holds a note falls through to the ordinary
  flank search (which already extends across a cut edge).
* **No ADJACENCY check at all.** The old rule found the nearest same-position
  heads on each side and paired them, without asking whether some OTHER
  note (at any position) sat between them in time. Added `not_adjacent`: a
  candidate pair is rejected if any other usable head sits strictly between
  the two paired heads in (cell, x) order. ⚠️ First version over-refused:
  a chord's stacked onsets (heads a few px apart in x, same beat) were read
  as notes "between" the pair, costing 30 of 253 Litolff p3 arcs. Fixed by
  exempting any head within one notehead-width of either endpoint's own x
  (that head is the endpoint's own chord, not a different note in time) —
  down to 9 of 253 after the fix, all with multiple real heads between the
  chosen pair on inspection.

Did NOT reopen `3.2c`'s tied-chord disambiguation (measured dead at zero
there, see above) — a positive-control test confirms two separate, already
well-separated arcs each still pair their own position without it.

**Real data** (re-adjudicated from the 20261001 whole-movement records,
streamed with `ijson` so neither the 487 MB Litolff nor the 3.47 GB Brahms
record is ever loaded whole — `probe/readjudicate_2_54.py`):

| | Litolff whole movement (2,644 arcs) | before | after |
|---|--:|--:|--:|
| `paired` | | 277 | **242** |
| `spans_a_whole_bar` | | 271 | **61** |
| `not_adjacent` | | 0 | **135** |
| `more_than_one_pair` | | 74 | 44 |
| `no_pair_at_one_position` | | 158 | 179 |

| | Brahms pp.0-3 (2,207 arcs, SHATTERING plate) | before | after |
|---|--:|--:|--:|
| `spans_a_whole_bar` | | 812 | **179** |
| `paired` | | 255 | **260** |
| `not_adjacent` | | 0 | **141** |
| `more_than_one_pair` | | 130 | 85 |

Diffed by (arc, start, stop): Litolff **20 newly decided, 55 newly
refused**; the 812→179 Brahms swing in `spans_a_whole_bar` is mostly NOT
becoming real pairs (SHATTERING plate noise), confirmed by `paired` moving
only +5 — most released arcs land on a more specific, honest refusal
instead of a false pair.

**27 crops** (≥600 px, 600 dpi, home staff drawn GREEN, start bracketed RED
`S`, stop bracketed MAGENTA `E`, naming arc outlined ORANGE; 18 Litolff + 9
Brahms, 0 refused by the frame control) under
`out/print/2.54/{litolff,brahms}/`, one `contact_sheet.png` per document.
My own look, not a verdict: the `linked` (newly decided) crops show a real
printed curve from S to E in the large majority on both documents. The
`not_adjacent` (newly refused) crops mostly show real intervening notes
under a longer slur spanning more than two notes (clearest on Brahms
`.../2.54-tie-07/08/09.png`). One Litolff `not_adjacent` crop
(`litolff/2.54-tie-13.png`) is on dense, thick ink where individual
noteheads are hard to make out by eye — NOT confirmed, flagged rather than
resolved. Sean's verdicts on the crops: todo.

Next: Sean's crop verdicts; `3.2c`'s tied-chord work is still unmerged and
untouched by this lane.
