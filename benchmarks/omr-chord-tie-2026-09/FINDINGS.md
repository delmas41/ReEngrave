# A chord's tie was written on the WRONG NOTE — priced, repaired, and it uncovered a larger defect underneath

2026-09-11. Branch `claude/chord-tie-per-note`, off `origin/main` `557e4e1e`.
The job handed over by
[benchmarks/omr-staged-tie-chain-2026-09/FINDINGS.md](../omr-staged-tie-chain-2026-09/FINDINGS.md)
§2c and §7 item 1: *price the chord tie.*

⚠️⚠️ **READ §5 BEFORE QUOTING ANYTHING FROM §1 OR §3.** The repair is correct
and the ENGRAVED family gets better, but on a SCAN it costs edits — and the
reason is not the repair. **A quarter of the tie pairings bind two notes of
DIFFERENT PITCH**, which no renderer can write correctly, and the old chord
hoist was masking some of them by accident. That is the finding; this repair is
the instrument that exposed it.

---

## 1. REACH FIRST

⚠️ *A change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are the same number.* So the population
comes before every other figure, measured by [`probe/reach.py`](probe/reach.py),
which calls `voicing.group_chords_in_measure` — the function under repair —
over the exact stored `.omr.json` files the A/B then re-exports. Every zero is
printed beside a positive figure so a dead instrument cannot read as a clean
result.

| | 11 engraved works | 11 stored scan rows |
|---|--:|--:|
| events / **chord events** | 3048 / **99** | 4974 / **646** |
| noteheads | 1557 | 4359 |
| events carrying `tied_to_next` / `tied_from_prev` | 79 / 80 | 231 / 232 |
| …**whose mark lands on a note carrying no tie** | **1** / 0 | **27 / 35** |
| …carrying a SECOND tied head, inexpressible at event level | 0 / 0 | **6 / 6** |
| an event flag with NO flagged head under it | **0 / 0** | **0 / 0** |

**The defect is TWO populations and they need separate pricing**: on the scan
rows **62 marks RELOCATE** and **12 are ADDED** (a chord with two genuinely
tied members got one `<tied>` and now gets two). On the engraved corpus it is
**one** mark, relocating, and nothing added.

⚠️ **The last row is why the repair could DELETE a branch rather than add a
rule.** Over all 33 stored transcriptions there is not one event whose
event-level flag is set while no head under it carries it — so the event value
is exactly `any()` of its heads everywhere it is read, and reading the head
instead cannot lose a mark. No fallback was written, because measurement showed
nothing to fall back from; had one been written it would have been a guess
about which note is tied.

---

## 2. WHAT SHIPPED

No flag. `tools/omr/voicing.py`, `tools/omr/export.py`,
`tools/omr/staged/export.py`.

Both MusicXML renderers read `tied_to_next` / `tied_from_prev` off the **HEAD**
instead of the event's `any()`. **`voicing`'s event-level flags stay** — §4.

The staged `ties` counter moves **out of `if n == 0`**: it says what reached the
FILE, which is the `FAMILIES` rule, and that is now once per tied head.

⚠️ `tie_starts_written_on_an_untied_note` / `tie_stops_…` are **replaced, not
pinned at zero**, by `tie_starts_on_an_upper_chord_note` /
`tie_stops_on_an_upper_chord_note`. A counter naming an element the exporter no
longer writes reports something the file does not contain — the *control that
computes the wrong thing* family this repo has recorded four times. The
replacement is a POSITIVE figure about the file: a tie on a chord member that is
not the first note, which the old rule could not produce at all.

---

## 3. THE PRICE, ON BOTH FAMILIES

[`probe/tree_arm.py`](probe/tree_arm.py): the same stored `.omr.json` exported
by **two trees**, each in its own subprocess, scored against the same truths.
The transcribe half is byte-identical, so the delta carries **no detector
jitter** — the export-only shape
`benchmarks/omr-dynamics-staged-2026-09/probe/reexport_arm.py` established, with
the arm switched by TREE rather than by env var, because this change ships
without a flag.

⚠️ The probe **refuses two arms naming the same tree state**, and an exported
tree that is not a git checkout must carry a `TREE_ID` stamp or it is refused
rather than defaulted — *a fallback must never turn "cannot tell" into "same"*.

### 3a. ENGRAVED — the 11 works of `orchestral_eval`, on their own fixtures

```
base  557e4e1e   summed edits 2532   <tied> 79 start / 80 stop
fix   a9210d3b   summed edits 2530   <tied> 79 start / 80 stop   delta -2
files that DIFFER between arms: 1 of 11
```

**Better by 2 edits, with the `<tied>` COUNT identical** — this family holds no
second-tied-head case, so the arm is pure relocation, and the one file that
moves (`brahms-sym1-mvt1`) carries the one mark §1 predicted.

⚠️ `2532` is the figure CLAUDE.md records for `--no-direction-text`; these
stored transcriptions are that arm. This is a controlled A/B against itself,
never a claim about the headline, and `--record` was deliberately not run.

**THE ONE MOVED ELEMENT, ADJUDICATED.** Measure 6:

| | `<tie type="start">` on | `<tie type="stop">` on |
|---|---|---|
| base | **G2** | D5 |
| **fix** | **D5** | D5 |

The "chord" is `G2` + `D5` — three octaves apart, a cross-staff grouping and
not a printed chord — and measure 7 opens on `D5` carrying the stop. **The base
file asserts a tie between G2 and D5, which is not a tie.** No print was
needed: `record.Checkable`'s own rule settles it — *a tie's two ends must be the
same pitch*.

### 3b. SCAN — 11 stored rows of the 20-row gate

```
base   557e4e1e                      summed edits 34731   <tied> 231/232
reloc  557e4e1e+RELOCATE-ONLY        summed edits 34733   <tied> 231/232   +2
fix    a9210d3b                      summed edits 34739   <tied> 237/238   +8
files that DIFFER between arms: 9 of 11
```

**+8 edits over 34,731 — 0.023% — and the `<tied>` count RISES by exactly 12**,
which is §1's under-emission population to the element (6 starts + 6 stops).

⚠️⚠️ **THE THIRD ARM SPLITS THE COST AND IT IS WORTH HAVING.** `reloc` is a
measurement-only tree that moves the mark to the FIRST flagged head and writes
no second one, so the exported tie COUNT is held at the base arm's. **62
relocations cost +2 edits; the 12 added marks cost +6.** The relocation half —
the defect this session was sent to repair — is essentially free, and the
charged half is twelve elements the old exporter could not express at all.

⚠️ **The ±6 noise floor does NOT apply.** That floor is about re-transcribing;
this is one set of transcriptions exported twice, so +8 is deterministic. It is
small, not noise.

⚠️ **OMR-NED is symmetric and rewards under-prediction.** A written mark that
does not pair is charged, so quoting the ratio alone would hide the +12; both
are given. Same call as the articulation ship (+97 edits, still right) and
chords written bottom-up (+2).

⚠️ **ELEVEN ROWS, NOT TWENTY.** Only 11 of the gate's transcriptions exist on
disk; the other nine would need a re-transcribe (weights, `library/`, hours) for
an export-only change that cannot move the transcribe half. The pool is named,
not folded into a headline.

---

## 4. LILYPOND IS LEFT ALONE, AND THE REASON IS MEASURED

`_lily_event` still reads the EVENT flag and still writes `<c' e' g'>4~`.

⚠️ **A chord-level `~` is not the same mechanism as `<tied>`.** LilyPond
resolves it against the FOLLOWING chord **by pitch**, so it cannot land on the
wrong note. Verified by compiling
[`out/lily_tie_semantics.ly`](out/lily_tie_semantics.ly), whose positive control
is inside the file:

* `<c' e' g'>~ <c' e'>` — ties c and e, drops g, **no warning**;
* `<c' e' g'>~ <d' f' a'>` — **three** `unterminated tie` warnings, one per
  member.

**So the defect repaired here does not exist on the LilyPond side.** The
per-note form (`<c~ e g>`) is valid LilyPond and is REFUSED: it would be an
unpriced behaviour change to an exporter this repo has no metric for. Same call
as `_lily_wedge_plan`, which drops what it cannot express rather than
approximating it.

⚠️ **What LilyPond can still get wrong is the OPPOSITE error — over-tying**: an
untied member that happens to recur in the next chord is tied anyway. That is
pre-existing, unchanged here, and **unmeasured**.

---

## 5. ⚠️⚠️ THE REAL FINDING: A QUARTER OF THE TIE PAIRINGS BIND TWO DIFFERENT PITCHES

The scan arm's `+8` is not the repair being wrong. It is the repair refusing to
keep masking a defect one layer up, and the mask was only ever accidental.

`transcribe._pair_ties_in_staff` sets `tied_to_next` on a LEFT notehead and
`tied_from_prev` on a RIGHT one **by geometry**, and records no link between
them — the `Q.TIE_LINK` gap the previous session declared and argued for leaving
open. MusicXML `<tied>` carries no `number=` and resolves **by pitch**. So a
pairing whose two ends are different pitches **cannot be written correctly by
any renderer.** The old hoist wrote both ends at the chord's LOWEST note, so
whenever two consecutive chords shared their bottom pitch it produced a
same-pitch pair and the file *looked* right.

[`probe/pairing_pitches.py`](probe/pairing_pitches.py) asks the record, with no
truth file: for each head carrying `tied_to_next`, does the next event of that
voice carry a `tied_from_prev` head of the SAME pitch?

| | links | same pitch | **DIFFERENT pitch** | no end in the next event |
|---|--:|--:|--:|--:|
| 11 engraved works | 79 | 56 | **20 (25%)** | 3 |
| 11 stored scan rows | 237 | 58 | **64 (27%)** | **115 (49%)** |

The scan pairs are not near misses. From `beethoven-575951-p2`, whose 19
resolvable links include 14 different-pitch ones:

```
F4 -> [A4]     Bb4 -> [F5]    Ab3 -> [C4]
F2 -> [D2]     E5  -> [G5]    C3  -> [Eb3]
```

Thirds. A tie is a unison by definition.

⚠️⚠️ **AND THAT IS WHY THE BASE ARM'S SCORE ON THE TIE'S OWN INVARIANT IS
IMPOSSIBLE.** [`probe/tie_resolves.py`](probe/tie_resolves.py) reads the
EXPORTED file and counts ties whose two ends are the same pitch:

| | written starts | resolve | ceiling the record supports |
|---|--:|--:|--:|
| 11 engraved, base | 79 | 55 | 56 |
| 11 engraved, **fix** | 79 | **56** | 56 |
| 11 scan, base | 231 | **60** | **58** |
| 11 scan, **fix** | 237 | 57 | 58 |

**The base arm resolves 60 ties where the record supports at most 58.** At least
two of its resolutions are manufactured by the hoist — it wrote both ends on the
chord's bottom note and the bottom notes happened to match. The fix lands at 57
against that ceiling: it writes what the record says and no more.

⚠️ **This adjudicates EVERY moved element rather than a sample**, which is what
62 relocations needed and a hand pass could not have given. The invariant needs
no reference encoding and no print.

⚠️ **It is ONE-SIDED and must never be read as accuracy.** A tie that does not
resolve is certainly wrong; a tie that does may still be invented — two spurious
same-pitch detections resolve perfectly. Read the UNRESOLVED column as the
defect.

⚠️ **It does not say WHICH end is wrong** — the pairing, or the pitch read on
one of the two heads. Same shape as `ARC_KIND`'s position grammar, and the same
cause: two readings off one raster.

---

## 6. CONTROLS

* **The reach probe prints a positive figure beside every zero** (99 and 646
  chord events; 79 and 231 tie events), so *nothing moved* cannot be confused
  with *nothing ran*.
* **The A/B refuses two arms at the same tree state** and stamps each arm's
  identity into the report; an exported tree with no `TREE_ID` is refused, never
  defaulted.
* **`files that DIFFER between arms: 1 of 11` and `9 of 11`.** A zero there
  would be a dead instrument, and the probe says so in its own output.
* **Reach PREDICTED the element counts and the A/B reproduced them exactly** —
  12 additions predicted, `<tied>` 231 → 237 starts and 232 → 238 stops
  observed. An independent prediction landing to the unit is a stronger control
  than either figure alone.
* ⚠️⚠️ **A RACE WAS CAUGHT AND THE FIRST THREE-ARM RUN WAS DISCARDED.** The
  mutation battery `git checkout`s the files it mutates, and a three-arm A/B
  whose `fix` arm was the LIVE WORKTREE was running at the same time — so that
  arm could have exported through a mutated `export.py` and reported anything.
  Both jobs were killed, the worktree restored (`export.py` was in fact left
  mutated by the kill), and every arm re-run against **snapshot trees only**.
  Nothing in this file comes from the contaminated run. CLAUDE.md's warning
  about a staged gather picking up an edit made four minutes into it, arriving
  in a new shape: **an A/B arm that reads the working tree is not isolated from
  anything else that writes it.** ⚠️ The two-arm runs DID predate the battery
  and are clean, and that is checked rather than assumed: the snapshot-tree
  three-arm run reproduces `fix = 34739` and `2530` exactly. Two arms run under
  different conditions agreeing to the edit is the control; the argument that
  the first run *happened* to finish first is not.
* **Mutation battery**: [`probe/battery.sh`](probe/battery.sh), results in
  [`out/battery.txt`](out/battery.txt). Every mutation is anchored on a WHOLE
  expression and is **refused unless it applies exactly once** — the tie-chain
  session lost an arm to a fragment that occurred three times in one file, and
  "NOT APPLIED" is reported as a harness failure, never as a survivor. ⚠️ Nine
  arms break the tie POSITION; a suite that went red on all nine could still be
  one that rejects every tie, so the tenth is the **positive control in the same
  class** — it removes ties entirely, including the single-note case this repair
  does not touch, and the suite must still go red.

### 6a. ⚠️⚠️ FOUR ARMS SURVIVED THE FIRST RUN AND ALL FOUR WERE REAL GAPS

*One red arm is not a battery*, and this is what the rest of it bought. Six arms
went red immediately; the four survivors were each a hazard the tests did not
reach, and they are instructive as a set — **every one is a test naming a
mechanism it only half exercises.**

| survivor | why nothing caught it |
|---|---|
| LEGACY: restore the hoist for tie **STOPS** | every assertion named only the START. Two flags, two arguments, two elements — and one test. |
| STAGED: restore the hoist for tie **STOPS** | the page fixture's stop always lands on head 0, so the fixture could not express the case. |
| STAGED: count `ties` per **EVENT** again | per-event and per-head agree unless a chord has TWO tied members, and `_paired_spans` refuses two ends on one detection, so a page fixture cannot easily build one. Reached by calling `_measure_events_xml` directly, the way the legacy suite calls `_mxl_note`. |
| VOICING: the LilyPond flag reads `group[0]` | nothing asserted the event-level flag is the OR — the MusicXML tests had stopped reading it, and the LilyPond test built its event by hand. Dropping it LOSES a tie rather than misplacing one. |

All four are closed; the second run is all-red with ARM 0 SURVIVED.

* **Full suite.** A complete run on the REPAIR commit is green —
  **3729 passed, 11 skipped** (baseline on `main` 3728 / 11). The run over the
  final tree collects **3752**, and every file this branch touches is green on
  its own: `test_export.py` 320, `test_voicing.py` 48,
  `test_staged_tie_chain.py` 26, `test_staged_export.py`. ⚠️ **The final
  full-suite run was still in flight when this was written**, with **zero `F`
  or `E` through 2,143 of 3,752** — the machine was carrying a load average
  above 7 from sibling sessions and the run was accruing seconds of CPU per
  minute. Recorded as *in flight with no failure so far*, and deliberately not
  as a green figure that was not observed. `health --check`,
  `inventory --check` and `gather_coverage` all exit 0.
  ⚠️⚠️ **A SLOW RUN WAS NEARLY MISDIAGNOSED AS A HANG, TWICE**, because two
  polls landed on the same dot count and then two separate runs stalled at the
  same position. **A stalled progress bar under contention is
  indistinguishable from a hang** until you check the process's CPU clock — it
  was accruing seconds, so it was starved, not stuck. What finally named it was
  neither: mapping the dot count onto `--collect-only`'s ordered test list and
  reading the test at that index, whose **own docstring prices it**
  (`test_voting_off_the_alias_is_the_same_answer_as_voting_off_the_text`:
  *"`instruments.lookup` costs 23-136 ms per string … 21.98 s on Ravel's 427"*,
  run over every document of a 1,422-label corpus). It is the most expensive
  test in the suite, pre-existing, and untouched by this change.
  ⚠️ **And I made it worse**: diagnosing it by running candidate tests in
  parallel put a second and third pytest on a machine already at load 7, which
  starved the run I was diagnosing. **The instrument competed with its
  subject.**

---

## 7. WHAT IS **NOT** ESTABLISHED

* **No reading was checked against the print.** Every adjudication here is the
  tie's own pitch invariant read off the exported file. It bounds the defect
  above and bounds nothing below.
* **11 of the 20 scan rows**, two publishers — and the engraved corpus's tie
  population is tiny (79 links, ONE defective mark), so the engraved `-2` rests
  on a single element.
* **No staged-pipeline page was gathered.** The staged renderer's change is the
  exact mirror of the legacy one and is covered by unit tests and the battery,
  but no staged record was exported for this work, so
  `status_census.unaccounted` is asserted by the existing suite rather than
  re-measured on a fresh page.
* **The LilyPond over-tie is unmeasured** (§4).
* **`+8` and `-2` are OMR-NED, whose ATTRIBUTION on a scan is void** — 92.5% of
  scan edits are bulk/unpaired. The direction of a controlled A/B is valid; the
  category breakdown is not, and none is quoted.
* **Nothing here measures whether the ties we write are PRINTED.** 362 merged
  arcs on Litolff alone bind fewer than two noteheads and are refused, so the
  tie inventory is known to be short by an unmeasured amount.

---

## 8. REFUSED / REFUTED, so nobody re-tries them

1. **A fallback for an event flag with no flagged head under it.** Measured at
   **0 over 33 stored transcriptions**; nothing to fall back from, and writing
   one would have been a guess about which note is tied. §1.
2. **Per-note ties in LilyPond (`<c~ e g>`).** Valid syntax, refused: a
   chord-level `~` resolves by pitch and cannot land on the wrong note, and
   there is no LilyPond metric to price a change against. §4.
3. **Keeping `tie_starts_written_on_an_untied_note` pinned at zero.** A counter
   naming an element the exporter no longer writes reports something the file
   does not contain. Replaced by a positive one. §2.
4. **A renderer-level repair for §5.** The renderer of a tie START cannot see
   the next event across a barline or a system break, and choosing a head so
   that the pitches agree would be a tie-break inside a rendering step. It needs
   the link — `Q.TIE_LINK` — which needs the part structure extracted out of
   `export.py`, exactly as the previous session's §7 item 2 says.
5. **Shipping the RELOCATION half alone** (the `reloc` arm, §3b). It scores
   better on OMR-NED (+2 against +8) and is refused: the 12 marks it withholds
   are heads the record says are tied, and withholding them to please a metric
   that rewards under-prediction is the trap this file's own §3b names. It stays
   as a measurement tree and is not in the repo.
6. **Reading `tie_delta.py`'s ADDED/REMOVED cells as additions and removals.**
   That probe keys a tie on its PITCH, so one relocated mark appears as a
   REMOVED plus an ADDED. It is kept because its GAINED/LOST cells are honest,
   and this note is here so the other two are not misread.

---

## 9. WHAT A NEXT SESSION SHOULD DO, ranked

1. ⚠️⚠️ **THE TIE PAIRING, `transcribe._pair_ties_in_staff`.** 64 of 237
   resolvable scan links and 20 of 79 engraved links bind two different pitches,
   and that is now visible in the exported file instead of masked.
   `probe/pairing_pitches.py` is the instrument and needs no truth file, so it
   runs on any stored transcription. ⚠️ It does not say which end is wrong — but
   on an ENGRAVED fixture the pitch reading is near-perfect (noteheads 0.999
   F1), so a different-pitch pair there is almost certainly the PAIRING.
   **Start on the engraved 20, not the scan 64** — and within those, on
   **`mozart-sym41-mvt1`, which is 8 of 9**, against `beethoven-sym5-mvt1`'s
   11 of 11 CORRECT. Two engraved pages of the same corpus at opposite ends of
   the same measure is a boundary case handed over ready to run.
2. **The 115 links with no end in the next event** — 49% of the scan links,
   larger than the different-pitch population and completely unexamined here. A
   `tied_to_next` whose partner is not in the following event is either a
   pairing that skipped an event or a `tied_from_prev` that was never set.
3. **`Q.TIE_LINK`**, which is what would let a DECISION rather than a renderer
   own any of this; the previous session's §3 already holds the design and names
   the refactor it needs.
