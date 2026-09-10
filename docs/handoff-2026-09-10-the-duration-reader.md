# Handoff — the duration reader: two faults, both fixed, and what a second publisher cost

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-the-boundary-measured.md](handoff-2026-09-09-the-boundary-measured.md)
as the entry point. That file's redirect still governs — **the metric is not
the goal, the staged pipeline is** — and its `A-DUR-8` blocker is what this
session went after.

⚠️⚠️ **A SECOND ARC CLOSED THE SAME DAY AND NEITHER SUPERSEDES THE OTHER.**
[docs/handoff-2026-09-10-the-meter-arc-closed.md](handoff-2026-09-10-the-meter-arc-closed.md)
is the METER arc; this is the DURATION arc. They met in one place and it is
worth knowing which way the dependency runs: that session re-ran its boundary
arms on top of this work and reports the carry's discrimination widening from
+6.0/−8.0 to **+8.0/−8.0**, attributing it to the durations reading better.
**So the meter numbers there rest on the duration work here, and not the other
way round.** Its §6 ranks the scan-side meter READING next; this file's §5 is
the decisions this arc leaves open.

⚠️ **Nothing here is a score.** Every number is a control or a diagnosis. The
whole change is **staged-path only**: `tools/omr/rhythm.py` is untouched, so no
engraved or scan OMR-NED figure moves, and none was taken.

---

## 1. WHAT LANDED

`A-DUR-8` said **bar sums are wrong on perfect ink** — a clean LilyPond
engraving, 23 parts, every part playing every bar — which blocked the entire
bar-sum family: the carry's second witness (`A-DUR-2`), `OMR_METER_FROM_BARS`
(`A-DUR-7`) and Sean's per-bar model (`A-DUR-6` items 3-5). Its predecessor's
§6 had separated it into **two independent faults** and asked for them to be
worked apart.

**Both are fixed, and they turned out to be ONE FAMILY**: a mark the page
prints is gathered, and the decision that needs it looks in the wrong place.

| on `beethoven-sym5-mvt4` m203-218 | assessable bars | correct | narrowed |
|---|--:|--:|--:|
| before | 12 | 7 | 147 |
| the stem tier alone (fault 1) | 14 | 10 | 29 |
| the marks alone (fault 2) | 13 | 11 | 147 |
| **both** | **16** | **16** | 29 |

**Every bar of the fixture now reads correctly.** `A-DUR-8` is closed on that
document — ⚠️ **and closing it is not licence to tune the meter floors**; see
§4.

* **Fault 1 — a note is joined to its beam by its STEM.** A beam stroke runs
  from the first stem it joins to the last, and a stem stands at the SIDE of
  its notehead, so the outer note of every beamed group has its centre roughly
  half a notehead width past the stroke's end. `_beam_levels` tested exactly
  that centre. Measured: 114 narrowed durations had a stem of their own head
  meeting a beam the centre test called `none_over_this_note`, with the
  overshoot clustering at **0.35-0.47 notehead widths** — the stem offset and
  nothing else. ⚠️ `Q.STEM` was declared in `wants` AND `composed_from`,
  carried its own `KNOWN_GAPS` entry, and was **read by nothing** — 916 rows on
  a three-page record.
* **Fault 2 — a MARK must be ATTACHED to its notehead.** `Q.FLAG` and
  `Q.AUG_DOT` are gathered on the MARK's own glyph subject and were read on the
  NOTEHEAD's, so **134 flag rows and 157 dot rows reached ZERO durations**.
  Confirmed against the encoding the page was rendered from: m211 read
  `quarter + 8th-rest` x4 = **6.0** where the truth holds **100 eighths**, and
  m207/m208 read a plain half at **2.0** where 8 parts play a **dotted half**.
* Two sub-faults came with it. `levels = len(flags)` counts GLYPHS, and one
  `flag16thUp` is one glyph and **two** levels. And the dot window needed a
  unit that was not on the record: `Q.CELL_STAFF_SPACE` is new because
  **the canonical staff space is not a constant** — the nominal is
  `CANONICAL_STAFF_SPAN_PX / 4 = 100`, but `_upscale_to_canonical` scales a
  too-wide cell by WIDTH, and on that fixture **184 of 368 cells read 100 px
  and the other 184 read 38.5-56**.

Full reading:
[benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md](../benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md).

## 2. THE SCAN ARMS — two publishers, and the second corrects the first

Both use `readjudicate.py`: **gather once, adjudicate four times**, so the arms
differ only in the rule and carry no detector jitter. Its `--control`
re-adjudicates unchanged and diffs against the record the pipeline wrote —
**2993/2993**, **4365/4365**, **1356/1356** on three documents, 0 differ, 0
extra.

| | per-staff readings right | bars |
|---|---|---|
| **Litolff Beethoven 5 mvt1** (4pp, 2/4 throughout) | 401 → **429** of 733 | 71/67 → **78/74** |
| **Breitkopf Brahms 1 mvt1** (4pp, 6/8 + one 9/8) | 42 → **108** of 493 | 8/**0** → 8/**6** |

⚠️⚠️ **THE SECOND PUBLISHER CORRECTED A GENERALISATION THE FIRST PRODUCED.**
Arm 1 concluded *"the marks half does nothing on a scan"* — the Litolff
detector fires 49 flag boxes and 35 dots over 2347 noteheads. Breitkopf fires
**371 and 656** over 3337, and there the marks half ALONE is worth **+13**
where on Litolff it was worth **0**. Litolff `984073` is catalogued *"low-res
bitonal"*; Breitkopf is not. **The limit was the DOCUMENT, not the printing.**

⚠️ **THE HALVES ARE SUPER-ADDITIVE** on Brahms: +15 and +13 separately, **+66**
together. That is what a bar sum is — a bar is right only when EVERY note in it
is right, so a bar holding one beam-missed and one flag-missed note stays wrong
until both are repaired.

⚠️ **IT IS NOT FREE, AND ONLY THE PER-STAFF VIEW SHOWS IT.** At bar level 0
bars go right → wrong on either document, but that is the cross-staff quorum
working. Underneath: Litolff 54 wrong→right against **26 RIGHT→wrong** (2:1),
Brahms 93 against **27** (3.4:1).

⚠️ **A false-attachment probe that needs no truth file**: a note under a beam
carries no flag, so a notehead with both is a contradiction — one of the two
readings is wrong, without saying which, so it is a RATE and never a count.
**Engraved 2.7% · Litolff 18.9% · Breitkopf 27.5%.** Three points, ordered by
ink quality. **No gate was added**: gating the flag half on print quality would
be a rule fitted to one scan of one publisher.

## 3. ⚠️ THREE INSTRUMENT DEFECTS FOUND, ALL IN MY OWN MEASURING TOOLS

Worth more than the numbers, and the reason to read this section before
quoting any of them.

1. ⚠️⚠️ **THE BAR KEY MERGED TWO BARS.** The probes keyed a bar on
   `(page, cell)`, and **a cell index RESTARTS at 0 on each system of a page**
   (Litolff p.2 runs 0-15 then 0-14), so system 0's third bar and system 1's
   third bar were merged into one pseudo-bar and scored. Four pages of a
   UNIFORM-meter document could not expose it; the first fixture whose truth is
   not uniform did, immediately. Corrected figures are in §2. ⚠️ The merged
   version had also been HIDING losses — it reported one bar dropping out of
   the quorum where there are four.
2. ⚠️⚠️ **I ALMOST REPORTED A VACUOUS CONTROL.** I promised to re-run
   `readjudicate --control` when a sibling's GATHER change landed.
   `readjudicate.py` rebuilds from a SAVED record's observations, so it is
   **blind by construction to any gather change** — it would have passed
   2993/2993 and proved nothing. Caught before running it. The instrument's
   honest contract: it isolates ADJUDICATE over a FIXED gather; `reexport_arm.py`
   has the mirror blind spot; the uncovered middle is *"did GATHER change what
   ADJUDICATE sees"*, and only a full re-gather answers that. The sibling then
   ran one: **`duration 939 → 939, 0 changed`**
   (`benchmarks/omr-staged-notations-2026-09/out/regather-control-beet5-p3.txt`),
   ⚠️ **and that gather change has since LANDED ON MAIN** — checked on the
   merged tree, it adds FIELDS to existing rows and no `log.observe`/`abstain`
   at any scope, so the figures in §2 stand without re-deriving.
3. ⚠️ **A MUTATION ARM SURVIVED AND I DELETED THE RULE, NOT THE TEST.**
   `_attached_flags` opened with `if not attached_stems: return [], 0`, which
   cannot be broken because `any()` over an empty list is already False — a
   second spelling of the rule one line below. ⚠️ And an EXISTING test was
   passing for free: `test_a_dot_adds_half_of_what_stands` asserted the right
   arithmetic on a fixture that wrote `Q.AUG_DOT` onto the NOTEHEAD's subject,
   a shape `gather` never produces.

⚠️ **Two caches were written for `_cell_boxes` and both deleted.** A module
dict keyed on `id(log)` went red inside a minute — CPython recycles an id the
moment an object is collected — and `Log` has `__slots__`, so nothing can hang
off it. The ~5-minute cost of one scan re-adjudication is recorded in the
docstring instead. **If it ever needs fixing, the fix is `Evidence` caching its
own row queries — one place, every decision.**

## 4. ⚠️ WHAT IS *NOT* ESTABLISHED

* **Three documents, three publishers, all 19th-century German orchestral
  prints.** One engraved render and two scans.
* ⚠️ **`A-DUR-8` IS CLOSED ON ONE ENGRAVED DOCUMENT AND THAT IS NOT LICENCE TO
  TUNE `METER_CARRY_FLOOR` OR `METER_FROM_BARS_FLOOR`.** The blocker it named
  is gone, so the bar-sum family may be RE-OPENED — re-pricing needs more than
  three documents, and the scan bar sums were **already nearly right where they
  were assessable at all** (Litolff 67 of 71 → 74 of 78). What moved is how
  MANY bars can speak, not whether they are believed.
* ⚠️ **NO ARM HAS PRICED A WRONG STEM DIRECTLY.** The contradiction rate is a
  proxy that says one of two readings is wrong without saying which. Settling
  it needs **per-note truth on a scan**, which nothing in this repo has.
* ⚠️ **The `9/8` bar the Brahms fixture was chosen for is UNASSESSABLE** — its
  23 staves read 23 different lengths. The one bar the document was picked for
  is the one it cannot speak about.
* ⚠️ **Determinism**: two sessions independently observed the STAGED path
  reproducible run-to-run (23 quantities on one page; bar sums identical across
  a merge on another). That says nothing about the DETECTOR — confidences move
  0.83 → 0.69 on byte-identical code — or the legacy gate's ±6 edit floor. A
  verdict can be stable while the confidence under it moves, because decisions
  here read confidence as a TIER or an argmax rather than a value.

## 5. ⚠️⚠️ DECISIONS THAT NEED A HUMAN — nothing below is started

(§5.5 is the exception: it CLOSED while this handoff was being written,
and is kept because the correction is the point.)

### 5.1 The dotted REST — an asymmetry this session INTRODUCED

`_rest_ruling` still does `dots = ev.rows(Q.AUG_DOT)` on the REST's own glyph
subject — **the exact fault fixed for noteheads, in the same function, one
branch over**. So a dotted rest reads as undotted, and the module now handles
dots for noteheads and silently not for rests, **which is worse than the
consistent gap it replaced**.

**Measured before deciding what it is worth: of 848 `aug_dot` rows across the
three documents, 752 attach to a notehead and exactly ONE would attach to a
rest.** So it is consistency, not payoff — a dotted quarter rest is ordinary
music, these documents just barely print one.

**Shape of the fix**: two lines, because `_attached_dots` already scores rests
and noteheads identically; plus a test and a suite run, with
`readjudicate --control` to prove nothing else moved. ⚠️ **PARKED and unclaimed
by BOTH sessions.** The staged-pipeline session declined it (they are in
`ownership.py`, not `rhythm.py`) and neither user has ruled. Whoever takes it
should say so first — this repo has already built the hairpin export twice.

### 5.2 Re-open the bar-sum family, or not

`A-DUR-8` no longer blocks it. `OMR_METER_CARRY` and `OMR_METER_FROM_BARS` are
still `0`, and the standing objection is a scanned second publisher misreading
the meter GLYPHS badly enough that the weighing never gets a fair candidate.
That is a READING problem, not a weighing one. **Someone has to decide whether
better bar sums change that verdict** — this session did not, deliberately.

### 5.3 A shared name for a fault shape found three times in one day

A per-staff or per-cell quantity used as if it were system-wide: the cell index
merging two bars (§3.1), the meter session's independent find of the same in
their rules, and a sibling's canonical coordinates being asked a cross-staff
question. ⚠️ `coverage()` cannot see the third shape — it reports the family as
`stub`, not `starved`. **A quantity can be gathered in the WRONG FRAME and look
fed.** Three sessions each hit it; it may deserve a name in `ASSUMPTIONS.md`.

### 5.4 `Evidence` caching its own row queries

See §3. Not started, and it is a change to shared machinery that would want its
own measurement.

## 5.5 ✅ CLOSED — the red `health --check`, and ⚠️ MY FIRST FRAMING OF IT WAS WRONG

**Fixed on main and verified at `origin/main` in a throwaway worktree:
`health --check` exits 0, EMPTY CELLS none.** It is not a decision any more; it
is here because the way I first described it would have cost the next reader
something.

**What I wrote, and it is wrong:** *"a gate whose own docstring says it
undercounts, going red on code that is correct"* — a false positive, the
corrosive kind, a gate crying wolf. ⚠️ **That framing invites a reader to
discount a working gate, which is the harm it claimed to be warning about.**

**The accurate position**, arrived at by the session that owns the gate, after
it disagreed with me and then found its own disagreement false:

* I was right that the tests DID establish `arc_kind` deciding —
  `test_a_tie_class_decides_tie` asserts `v.value == "tie"`, and
  `Ruling.narrow` sets `value=None` **unconditionally** (checked:
  `adjudicate.py` `return Ruling(value=None, ...)`), so on this API a
  non-DECIDED verdict never carries a value.
* ⚠️ **But only through an API invariant the reader has to already know.** The
  classifier was right about the TEXT: no test spelled the outcome. So the
  gate was **correctly reporting that a claim was IMPLICIT** — which is exactly
  the one job its docstring reserves for itself, *point at the EMPTY cells, not
  grade the full ones* — and the `grep` it tells you to run is what resolved it.
* The added assertion buys **legibility, not power**. It makes the claim
  machine-readable and drops the dependence on that invariant.

⚠️ **And the fix I suggested first was the worse of the two, for a reason I had
not checked.** I offered "teach the classifier that asserting a `value` is
asserting a decision". `assertIsNone(v.value)` appears in ABSTENTION tests in at
least three files, so that marker would have credited abstention tests as
decides and **WEAKENED the gate** — the direction that hides problems. A
suggestion aimed at making a red gate green, which is the wrong instinct.

**Carry this rather than the number:** *a check that says a claim is implicit is
not a false positive.* Verifying the claim by hand and concluding "the code is
fine, the gate is noisy" is how a working gate stops being read.

## 6. OPERATIONAL

* Four symlinks in a worktree: `library`, `tools/omr/training/data/weights`,
  `.venv-surya`, `.venv-omrned`. The staged pipeline needs only the weights.
* ⚠️ **The staged CLI does no weight routing.** Engraved fixtures want
  `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`; scans want the hollow graft.
* Timings: a staged run is ~2 min for 3 engraved pages, ~12 min for 4 Litolff
  pages, ~20 min for 4 Brahms pages. One `readjudicate` arm is ~5-9 min on a
  scan record. The full suite is ~9-10 min.
* ✅ That sibling branch **has since landed on main** (`<direction>` emission,
  `arc_kind` and `arc_owner`, the page-box fields, a `provenance` stamp on every
  record, and `coverage()`'s `status_census`). Live stubs are now **three** —
  `articulation_owner`, `direction`, `wedge_anchor` — and only `direction` is
  input-starved.
* ⚠️ **A `readjudicate --out` arm is NOT a pipeline record.** It writes
  `{"record": ...}` only, so it lacks `adjudication`, `agreement`,
  `evaluation`, `stubs`, `summary` and the new `provenance` stamp. Fine for the
  probes here, which read `["record"]` — but **do not feed an arm to anything
  that checks provenance**: it would read as unprovenanced because this tool
  never had it to copy, not because the run was untrustworthy. Nothing refuses
  one today; this is written down before something does.

```bash
python3 benchmarks/omr-staged-meter-engraved-2026-09/render_meter_change.py \
    --work beethoven-sym5-mvt4 --first 203 --last 218 --out-dir out/
OMR_SURYA_KEEP_ALIVE=0 python3 -m tools.omr.staged <pdf> --pages 0-2 \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --out staged.json
B=benchmarks/omr-staged-duration-beams-2026-09
python3 $B/readjudicate.py staged.json --control          # ALWAYS run this first
python3 $B/readjudicate.py staged.json --off all --out off.json
python3 $B/bar_delta.py off.json staged.json "0.0:0-6=3.0,1.0:0=4.5"
python3 $B/mark_census.py off.json staged.json
```
