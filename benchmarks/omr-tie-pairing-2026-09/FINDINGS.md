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
