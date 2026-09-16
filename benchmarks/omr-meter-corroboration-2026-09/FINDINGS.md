# A meter change needs a second staff — and the obvious guard is REFUSED

2026-09-15. Sean's decision: **`OMR_METER_CARRY` and `OMR_METER_FROM_BARS`
default ON**, with a corroboration guard landing in the same change, because
the flip is exactly what turns a misread change from a one-system fact into a
document-wide one.

Both halves landed. **The guard is not the one the brief specified, and the
measurement that changed it is worth more than the repair.**

---

## 1. ⚠️⚠️ THE BRIEF'S EMPTY INTERVAL DOES NOT EXIST ON THE CURRENT TREE

The brief supplied a reach measurement and asked for a rule built to it:

```
every TRUE change  : 9, 19, 21, 21, 24 staves
every FALSE change : 1, 1, 1, 1, 1, 1 staves     <- "an EMPTY INTERVAL from 1 to 9"
```

Reproduced with `probe/reach.py`, which takes TRUE/FALSE from
`report_boundary.TRUTH_CHANGES` — the boundary session's own hand-read print
truth, **imported rather than restated** — the interval is not empty and the
populations **OVERLAP AT EXACTLY 1**.

Two separate faults, and they pull the same way.

### 1a. The two largest "TRUE" changes are CAUTIONARIES, which the committed truth calls FALSE

Pooled over every generation in `out/`:

| verdict | `staves_reading_it` |
|---|---|
| TRUE | **1**, 21, 23, 24 |
| FALSE | 1x8, **9**, **19** |

The **9** and the **19** are the `9/8` at the last cell of page 0 of Brahms 1
mvt 1, scanned and engraved. `TRUTH_CHANGES` records both as `None` with the
reason in its own comment:

> *p0's 9/8 is a CAUTIONARY printed AFTER the final barline; it announces the
> NEXT system's meter and governs no bar on this page. A change proposed at
> that page's last cell is WRONG — it would re-size m7.*

They are not true changes. They are also **already gone**: the cautionary rule
shipped default-on, and neither appears in the `m7` generation at all. Counting
them as TRUE builds the new guard's floor on a defect the tree no longer has.

### 1b. The one TRUE change on a scan reads ONE STAFF, and the brief omits it

**Beethoven 5 / Litolff p.62 prints `3/4` at the bar the reference names, and
we read it on ONE staff of seventeen at support 3.0.** It is the flagship scan
result of this whole thread. CLAUDE.md already says so from the other
direction, in the letter-meter section: *"the p.62 `3/4` this project
celebrates is **also one staff of seventeen**."*

### 1c. The current tree, generation `m7`, in full

```
verdict  stv  support  fit  cont  raw    cell   fixture
TRUE      24     74.0    1     0  C|        6   brahms4-m386-412  p0 s0
TRUE      23     71.0    1     4  C         3   boundary-m204-232 p1 s0
TRUE      21     70.0    0     3  6/8       1   brahms1-m1-22     p1 s0
TRUE       1      3.0    0     0  3/4       8   litolff-984073    p62 s0   <- the flagship
FALSE      1      4.0    0     0  4/4       2   brahms1-317803    p1 s0
FALSE      1      3.0    0     1  4/4       4   brahms1-317803    p1 s1
FALSE      1      4.5    1     0  C         3   litolff-984073    p61 s0
```

**Nothing separates the one-staff rows.** Two of the three FALSE ones score
HIGHER than the TRUE one (4.0 and 4.5 against 3.0), and the only one-staff row
whose bars say anything at all — p.61's `C`, one bar fitting — is **FALSE**.
Stave count, support and bar math each fail in the same place, which is *the
bars are not an independent umpire over a bad reading* arriving a fourth time.

> **A veto keyed on any of them removes three false changes by deleting the one
> true meter change this project has ever found on a scan.**

---

## 2. SO THE ACTION IS WEAKENED UNTIL IT IS ONE-SIDED

A change does two things, and only the second is where one staff's reading gets
amplified:

1. it governs the bars of **its own system**, through `record.meter_at` —
   local, visible in the file, checkable against the print;
2. it becomes, through `_meter_in_force_at_end`, the meter **carried onto every
   following system that abstains** — a document-wide claim built out of one
   glyph on one staff.

**A-METER-6 gates (2) and leaves (1) exactly as it was.**

> An uncorroborated meter change governs its own system and may not be carried
> off it.

`METER_CHANGE_MIN_STAVES = 2` — the staff itself plus one witness, equal to
`key_signature_corroboration.MIN_WITNESSES` and asserted equal to it. ⚠️ **Not
a tuned constant, and on this corpus it could not be one**: the populations
overlap at 1, so every value above 1 confines the same four segments. 2 is the
weakest bar that confines anything.

This is `METER_SOURCE_REASONS`' own discipline extended one step — from *which
verdicts may be carried from* to *which segments of them* — on its own stated
ground: *"neither is ink on the source's own page, so admitting either would
make `pages_since_read` a lie about the distance back to ink."*

### ⚠️ The witness is the STRONGER one, paired with the WEAKER action

`key_signature_corroboration` takes the opposite pair, for a reason it states:
it **REVERTS**, so it needs the weakest possible witness (another staff changes
at the same BAR, whatever value it reads) or it breaks transposing instruments,
which genuinely carry different keys at one bar. A meter has no such exemption
— that module's own docstring says *"A meter change is corroborated by other
staves reading THE SAME METER, because a meter is one fact shared by the
system"* — and confining costs at most a carry where reverting costs the music.

`staves_reading_a_meter` (staves reading **any** complete meter at that bar) is
recorded on every segment and **read by nothing**, so the weaker witness can be
priced later without a re-gather. It is declared as recorded-only rather than
left to be discovered.

---

## 3. WHAT THE RULE DOES — measured on the committed records

`corroboration_arm.py`, calling the **SHIPPED** `_meter_in_force_at_end` on
each decided meter value, once as the tree has it and once with the filter
bypassed. Generation `m7`, deduped on `(fixture, page, system, cell, raw)`.

| | |
|---|--:|
| change segments reached | **7** |
| corroborated (>= 2 staves) | 3 |
| uncorroborated | 4 |

| verdict | staves | corrob | carried BEFORE | carried AFTER | fixture |
|---|--:|---|---|---|---|
| FALSE | 1 | False | `4/4` | **`9/4`** | brahms1-317803 p1 s0 |
| FALSE | 1 | False | `4/4` | **NOTHING CARRYABLE** | brahms1-317803 p1 s1 |
| FALSE | 1 | False | `C` | **NOTHING CARRYABLE** | litolff-984073 p61 s0 |
| TRUE | 24 | True | `C\|` | `C\|` | brahms4-m386-412 p0 s0 |
| TRUE | 23 | True | `C` | `C` | boundary-m204-232 p1 s0 |
| TRUE | 21 | True | `6/8` | `6/8` | brahms1-m1-22 p1 s0 |
| TRUE | 1 | False | `3/4` | **NOTHING CARRYABLE** | litolff-984073 p62 s0 |

**Controls, each able to fail:**

* every TRUE change still reaches its own system's `segments` — **4 of 4**;
* a corroborated change's carry **MOVES 0 of 3** — the positive control, and
  without it the arm would pass for a rule that confined everything;
* an uncorroborated change's carry **moves 4 of 4** — without this the arm
  would pass for a rule that confined nothing.

### ⚠️ THE COST IS NAMED, NOT NETTED AWAY

The p.62 `3/4` is confined. Page 63 is no longer handed it **by the carry**.
That is a real cost and it is one of the four confinements.

⚠️ **It is bounded by the other half of this same change and that is not a
coincidence.** `OMR_METER_FROM_BARS` also went default-ON, and CLAUDE.md
already records that p.63's own bars name **length 3.0 at +5.0 — the printed
`3/4`** — independently, without looking at another system. The two flags
landing together is what makes the confinement affordable here. ⚠️ **That is a
reading of a committed measurement, not something this session ran**; no
end-to-end arm was possible in this container.

### ⚠️ AND ONE CONFINEMENT SUBSTITUTES ONE WRONG ANSWER FOR ANOTHER

`brahms1-317803 p1 s0` carries `4/4` before and **`9/4` after**. The `9/4` is
the misread opening this whole thread is blocked on. Neither is right. The rule
removed a false change from the carry and handed on a false *opening* instead,
because that is all the system has. **Do not read the FALSE column as three
repairs.**

---

## 4. THE FLAG FLIP — and the derived guard could not see either flag

Both flags were `os.environ.get(ENV, "0").strip() == "1"` — the right shape for
a default-OFF mechanism (*a typo must not switch a document ONTO something
whose hazard is a whole wrong movement*) and exactly wrong once the default is
ON, because then `OMR_X=`, `OMR_X=yess` and `OMR_X=ON!` all read as FALSE and
**silently restore the behaviour the default exists to replace**.

Both are now deny-lists, copied from `OMR_METER_SEGMENTS` rather than invented
so this repo does not grow a third convention for what an empty value means:

```python
os.environ.get(ENV, "1").strip().lower() not in ("0", "", "false", "no", "off")
```

⚠️⚠️ **`tools/omr/tests/test_flag_default_direction.py` COULD NOT SEE EITHER
FLAG BEFORE THIS CHANGE.** Its AST scan matches `os.environ.get(FLAG, default)`
**compared to a literal word set** — an `In`/`NotIn` test — and a `== "1"`
comparison is neither. Measured:

| | default-ON | default-OFF | the two meter flags |
|---|--:|--:|---|
| before | 10 | 10 | **not listed at all** |
| after | **12** | 10 | listed, `NotIn`, default `'1'` |

So the guard that exists to catch exactly this hazard was structurally blind to
the two flags that had it. It is not blind now, and the gap is **the
comparison form, not the flag list** — a `>`/`==` predicate still escapes it.
Recorded rather than fixed: widening the scan touches every flag at once and
belongs with whoever prices that.

### ⚠️ Three test harnesses expressed "off" by POPPING the variable

`test_staged_header_rhythm.py`'s three `_run` helpers set the flag to `"1"` for
their on-arm and **deleted it** for their off-arm. Under the new default an
absent variable is ON, so every "off" assertion would have been running the ON
code. Ten tests went red on the flip and **all ten were this**; they set `"0"`
now.

Two tests named `test_off_by_default_the_system_still_abstains` are renamed to
`test_with_the_flag_OFF_...` and a `test_the_DEFAULT_is_now_ON` added beside
each. **An assertion about where the default sits is a property of the BUILD'S
PROGRESS, not of the mechanism** — the `stubs()` lesson, arriving in the meter.

---

## 5. ⚠️⚠️ A DEFECT THE TESTS FOUND: THE FLAG REACHED ONE OF TWO SEGMENT BUILDERS

`_with_segments` and `_change_only` **both** build `segments`, and each
hand-listed its fields. A-METER-6 was added to the first only. So a
`change_only` verdict's segment carried no `corroborated` key,
`_meter_in_force_at_end`'s `seg.get("corroborated", True)` read it as a
pre-rule record — the branch that exists so old records still carry — and the
change was carried forward **exactly as before, with every unit test green**.

That is the worst case for this rule, not a corner: `change_only` is precisely
the shape Litolff p.61-62 has, a system with no opening whose only meter fact
is a change one staff read.

It was caught by the behavioural test asserting **the carry walk RUNS OUT**,
not by review. The projection is now written once (`_segment_from_change`,
`_SEGMENT_FIELDS`) with a source-level anti-drift assertion over both call
sites, so the next field cannot be added to one of them.

> **A field list written twice is two records of one thing nothing forces to
> agree** — the shape this project already records for `works.json`'s arity
> fields and for the accuracy figure held in four files.

---

## 5b. THE MUTATION BATTERY — and the one survivor was a real gap

**15 arms, all red, tree restored and VERIFIED byte-for-byte against a
snapshot taken before the first arm** — not against the version control, since
two days earlier a battery restored `export.py` from HEAD, HEAD did not have
the function under test, and the tests that had just passed were testing code
no longer on disk. `everything_refuses` is an arm, not a footnote: a battery of
refusal tests passes for a rule that refuses everything.

⚠️ **The first run reported 14 arms and one SURVIVOR: `never_none`.** Mutating
`if not value: return None` to `return {}` left the whole suite green, and it
was a genuine test gap rather than an equivalent mutant: `{}` is falsy but it
is **not None**, and `_carry_meter` tests `carried is None`, so an empty dict
walks straight into `_corroborate` as though a meter had been handed on.

⚠️⚠️ **Closing it found a SECOND hazard the entry guard does not cover.** A
value of `{"segments": []}` is **truthy**, so the filter is skipped entirely,
`meter_at` falls back to the value itself, and the helper returned `{}` — the
same accepted-as-a-meter path, reached a different way. The contract is now
stated on the way OUT (*a meter or nothing*: no numerator or no denominator
returns None) with its own arm, `a_meter_or_nothing`.

Both are unreachable from `_carry_meter` today, because `_with_segments`
always writes the opening — **which is exactly why nothing exercised them**.
*"A fallback must never convert cannot-tell into a definite answer"* is about
the value a caller READS, so the guard belongs on the way out and not only on
the way in.

---

## 6. ⚠️ THE HAZARD, STATED PLAINLY

**A-METER-6 does not fix the scan meter problem, and this write-up must not be
read as saying it does.**

Corroboration kills the one-staff FALSE *changes*. It does **nothing** to the
misread `9/8` -> `9/4` **opening** on Breitkopf Brahms 1, because there the
majority is wrong: the template reader returns `[9, 4]` on 10 staves at
0.500-0.531, and a rule that asks for a second witness gets ten. A separate
session is on that, and the document's own answer — the recorded `cautionary`
reading `9/8` on nine staves one system earlier — is still consumed by nothing.

The flip makes that misread *travel*. That is the cost side the flag was held
off for, and it is what `local_arm.sh` exists to price.

---

## 7. THE LOCAL ARM — written, documented, NEVER RUN

A cloud container has no `omr-weights/` and no `library/`, so nothing
end-to-end was possible here. `local_arm.sh` prices the flip on the document
whose meter reading is known bad:

```bash
bash benchmarks/omr-meter-corroboration-2026-09/local_arm.sh \
  library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
  omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
  0-3
```

Two arms (both flags OFF / both ON), each with its own `--out`, both variables
set explicitly in every arm, the environment passed per command rather than
through an unquoted expansion, and a refusal to start on an existing output —
the three traps `run_arms.py` documents. It gathers **without** `--musicxml`
and exports separately, because the exporter is imported after the gather.

It reports, per arm: the meter decisions by reason, **change segments and how
many are uncorroborated**, **carry sources SKIPPED** (A-METER-6's reach on a
real gather — the number no committed record can supply), `<time>` elements by
value, and `probe/bar_fill.py`, the instrument Sean's *"none of the measure
math makes sense"* became.

⚠️ **If `bars that add up` FALLS, the flip is propagating the misread `9/4`.**
Report it; do not tune `METER_CARRY_FLOOR` against it — this project has
refused that twice.

---

## 8. WHAT IS NOT ESTABLISHED

* **No end-to-end arm ran.** Nothing here re-gathered, re-adjudicated or
  re-exported. The carry's own weighing (`_corroborate`) is not exercised by
  `corroboration_arm.py`, so whether a confined carry then survives its bars on
  the next system is **not measured**.
* **No OMR-NED figure is claimed**, on either family.
* **No print was consulted.** TRUE/FALSE comes from the boundary session's
  committed truth table; this session read no page.
* **n = 6 fixtures, 4 documents, 2 publishers, and the reach is 7 change
  segments.** Three of the six fixtures contribute no change at all on `m7`.
* The three confinements that remove a FALSE change are **3 segments**. That is
  a count, not a rate, and one of the three substitutes a false opening.
* **The cost side is one row** — the Litolff p.62 `3/4` — and the argument that
  `OMR_METER_FROM_BARS` covers p.63 independently is read off a committed
  measurement, not re-run.
* `staves_reading_a_meter` is recorded and **consumed by nothing**; the weaker
  witness is unpriced.
* The flag-direction guard's blindness to `==` comparisons is **recorded, not
  fixed**.

---

## Files

| | |
|---|---|
| `probe/reach.py` | the reach, TRUE/FALSE from the committed truth table; exits non-zero if dead |
| `corroboration_arm.py` | what confinement does, calling the shipped helper; three controls |
| `mutation_battery.py` | **15 arms, all red**, byte snapshot, **restore VERIFIED** |
| `local_arm.sh` | the end-to-end pricing for Sean's machine — never run |
| `out/reach.json`, `out/arm-m7.json` | the tables above, machine-readable |
