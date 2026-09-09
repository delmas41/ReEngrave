# Handoff — the meter became a fact about BARS, and what that opened

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-gather-and-the-record-that-answers.md](handoff-2026-09-09-gather-and-the-record-that-answers.md)
as the entry point. That file's §1 redirect still governs — **the metric is not
the goal** — and its §7 task 1 (the meter carry) is what this session did.

Everything here is on `main`. **Suite 3,286 passed, 9 skipped, 0 failed;
`inventory --check` and `health --check` both exit 0.**

---

## 1. THE REDIRECT STILL STANDS, AND SEAN SHARPENED IT

No benchmark was run as a goal. Every number below is a control or a diagnosis.

What Sean added this session, and it is the frame for the next one:

> *"We need probability based decisions with layers of information and most of
> the implications of that information ... this is where the math that can be
> determined by its own equation could be weighed more heavily than information
> that can only be derived. If the measure is what we think it is - does the
> math of the notes make sense. If not then the meter should decrease in
> probability."*

> *"I don't want the dichotomy of it's a system or a group of notes surrounding
> it. It is both."*

---

## 2. WHAT LANDED

**`Q.EVENT` — which glyphs of a bar sound together.** Chord grouping existed in
exactly one place, `export._events`, at serialisation time, and the record held
no chord/event/onset/voicing quantity at all. So every stage before EXPORT
counted each chord member as a separate time-advancing event — including
`reconcile_duration`, the pipeline's own bar-sum check, which **failed
silently** because an inflated total simply never equals the meter. Measured:
p.17 is 38.2% chord bars and ungrouped the bars landing exactly on the printed
meter fall **18 → 13**.

**`OMR_METER_CARRY` (default `0`) — a carried meter is WEIGHED, not gated.** A
system that read no meter takes the last one that was READ, as a candidate, and
the bars move its standing: carry `+1.0`, each bar that fits `+1.0`, each that
does not `−1.0`, floor `2.0`, minimum 2 assessable bars. **The ordering is
structural** — two contradicting bars outweigh any carry and no carry outweighs
the bars — asserted on the constants so a sweep that breaks it fails even when
every behavioural test passes.

**`Q.METER` carries `segments` — a meter is a fact about a RANGE OF BARS.**
`record.meter_at(value, cell)` is how a bar's meter is read. A change is
proposed where a time-signature GLYPH stands at that bar (`+3.0`, one staff
clears the floor alone); the bar math then confirms, refuses, or chooses
between staves that read it differently. **A change-only verdict is a real
answer**: p.62 reads a usable meter on 2 staves of 17 and still records
*unknown until bar 8, 3/4 from there*.

**`rule(single_pass=True)`** — the pipeline's one sanctioned loop, declared per
rule. Corroboration makes the meter depend on the durations
`reconcile_duration` rewrites; `UphillConsequence` refused it, correctly.
Unrolled it is a straight line (*"vote once, repair once"*), and the BOUND is
what makes it safe.

**Gather widened past cell 0** — a meter glyph may stand at ANY bar. The
hardcoded `R.cell(p, ..., 0)` is why a printed meter change was invisible.

---

## 3. THE MEASUREMENTS THAT MATTER

Beethoven 5 / Litolff `984073`, one document throughout so nothing else varies.

| | result |
|---|---|
| p.2 (continuation, truth 2/4) | carry **corroborated**, support +7.0 / +8.0 |
| p.17 (*Andante*, truth 3/8) | carry **refused**, all three systems |
| **p.62 (prints 3/4 at bar 155 = cell 8)** | **change detected at cell 8 — the exact printed bar** |
| p.61, pages 0-2, p.17 | **no change proposed** — controls clean |

In the file (pages 0-2, carry off vs on): whole rests written at 4.0 ql inside a
2.0 ql bar **194 → 70**; `written.notes` 648 → 665 against
`not_written.duration_narrowed` 163 → 146; `empty_bars_padded_without_meter: 47`
disappears; `reconcile_duration` fires **13 → 47**. Controls that did NOT move:
`no_pitch` 54 → 54, `detected_and_unrepresented` 659 → 659.

---

## 4. ⚠️ WHAT IS *NOT* ESTABLISHED — read this before quoting anything above

* **n = 1 document, 1 meter change, 2 continuation pages.**
* ⚠️ **The p.17 refusal is SAFE, not DISCRIMINATING.** Scored against `3/8`,
  the meter that page actually prints, it **refuses that too** (−1.0 against
  −3.0). Its durations are noise and a noisy page refuses everything. A
  movement boundary on a page that READS WELL is unmeasured.
* ⚠️ **The bar-math half is barely exercised.** Even on p.62 it contributed
  `0 fit / 0 not`: the whole-rest exclusion removes exactly the post-change
  bars, because a change is typically followed by most instruments resting.
  **The change result rests on the GLYPH alone.**
* **The weights are asserted, not measured.** Symmetric and declared unmeasured;
  `METER_CARRY_MIN_STAVES_PER_BAR = 3` is set by analogy and never measured.
* **The staged and exporter chord groupings still disagree** (24 vs 16 members
  on one page). Mostly a population difference; the residual is the exporter's
  own filter chain. Rule parity is pinned by test; unifying them means the
  exporter consuming the verdict.

---

## 5. THE NEXT WORK, RANKED — and it is Sean's model, not mine

### 1. A LONG RUN OF BAR SUMS MAY PROPOSE A METER WITH NO GLYPH

Sean: *"If there is no meter glyph then we have to deal with bar sums... We
have 12 systems and 10 of them say 4/4 for 6 measures."* Right, and **not
built**. A run may only corroborate today.

The reason it was not admitted is p.17, where the bars name nothing coherent
(4 assessable bars at 4 different values) and would manufacture meters from
noise. **But the discriminator is the run itself** — 10 staves × 6 bars is not
4 bars at 4 values — which is Sean's *"for how long, the longer the more
likely"*.

⚠️ **THE RUN MUST BE DIRECTIONAL.** Bars AFTER a candidate change are evidence
for the NEW meter and bars BEFORE for the OLD, so a symmetric ±4 window blurs
exactly the boundary it is meant to find. Run LENGTH is evidence; a symmetric
window around a suspected change is not.

### 2. THE PER-BAR MODEL — `A-DUR-6`, quoted verbatim in ASSUMPTIONS

Sean's ranked evidence for each bar: (1) a meter glyph here, (2) meter glyphs at
this bar on other staves, (3) this bar's sum, (4) the same bar's sum on every
other staff, (5) the surrounding bars' sums, then beat subdivision and blobs.
Governing rule: **persistence by default; a change must be argued for; where
nothing is established, DERIVE rather than default.**

Items 1-4 exist. Item 5 exists only forward of a candidate. 6 and 7 do not.

**Cheap addition not on the list: a DOUBLE BARLINE at the candidate bar.** A
meter change is nearly always printed after one, it is an independent reader,
and it needs no new CV.

### 3. ⚠️⚠️ UNCLASSIFIED INK AS A FIRST-CLASS GATHERED FACT — `A-DUR-5`

Sean's standing request, flagged at the head of CLAUDE.md so it cannot be lost:

> *"I really don't want to lose the 'here is a blob of ink but we don't know
> what it is' gather data point ... this is the same unrecognizable blob on
> every system at bar 51 ... or we know what this blob is in 3 of the 10
> systems and they all line up."*

**The power is ALIGNMENT**: unnamed ink at the same bar across staves is a
printed event whatever it is, and where a few staves classify it the minority
names what the majority corroborates.

⚠️ **NOT reachable from the detection record**, and this is measured: at p.62
cell 8 the meter is printed on **every** staff, we classify it on **2 of 17**,
and the other 15 carry **no unclassified detection at that column** — the ink
was never detected at all. It needs a **RASTER pass in GATHER**. The precedent
is `direction_text._blank_detections`, which already subtracts every detection
from the page's ink so *"find the text"* becomes *"find the ink"*.

### Also open, smaller

* Unify the two chord groupings (export consumes `Q.EVENT`).
* `arc_kind` / `arc_owner` are still stubs — 843 arcs, and tie evidence for the
  beat structure is blocked on them.
* Calibration: bar sums are `Checkable`, so **this family can generate its own
  labels** from the score library with no truth files. That is the honest route
  to real probabilities, and nothing has built it.

---

## 6. ⚠️ FIVE THINGS THAT COST TIME, OR NEARLY SHIPPED WRONG

1. **A claim I had to retract.** I reported that the *Andante*'s bars
   *contradict* the carried meter. The control I had not run — *would it refuse
   the CORRECT meter too?* — says it would. Safe, not discriminating.
2. **A probe keyed on the wrong field.** The first run of that control grouped
   bars by SYSTEM and dropped the PAGE, merging page 1's systems into page 17's,
   and appeared to show a wrong meter being carried onto the Andante. Caught
   only because it contradicted the live run's own recorded detail. **Check a
   probe against the pipeline's own record.**
3. ⚠️⚠️ **macOS caches bytecode OUTSIDE the tree**, in
   `~/Library/Caches/com.apple.python/<abs path>/`. `find . -name __pycache__`
   never sees it. A reverted mutation stayed live — `grep` showed `-1.0` while
   `import` returned `-0.0` on a file whose md5 matched `inspect.getsource` —
   so one mutation arm ran on top of another without saying so. **Clear that
   path between arms.** Same family as the cached `scan_eval` A/B.
4. **A field that claimed a check that never ran.** `divisi_guard: "ran"`
   wherever `Q.STEM` rows merely existed; the guard is not built. Caught by
   reading the field's own output on a real page.
5. **A gate that failed silently inside a fix for a silent failure.** The
   plausible-meter set was written `try: ... except Exception: frozenset()`,
   swallowed a wrong relative import, and admitted nothing. Now a hard import.

**And a surviving mutation.** Disabling the lone-whole-rest exclusion broke no
test, though it is the rule that makes corroboration usable at all. A test now
covers it. **A mutation that survives is a rule with nothing behind it.**

---

## 7. OPERATIONAL

* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  daemon**.
* The staged pipeline needs only the weights; a worktree also needs a `library`
  symlink for the PDFs.
* `| tail` eats git exit codes — verify a push by re-reading the remote ref.
* The full suite takes ~9-11 minutes and sits a long while around 64% in
  `test_roster.py`. That is normal.
* Measure a carry on a **multi-page run only** — the scan gate transcribes one
  page per row and silently disables every page-spanning mechanism.
