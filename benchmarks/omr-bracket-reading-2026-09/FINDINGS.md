# Reading the bracket: it is a real object, and it loses to the inference

2026-09-06. Branch `worktree-agent-aa1bd3b1a2dc3ca54`, on `main` at `504a1e34`.
New module `tools/omr/bracket_reader.py` — **no consumer, no flag, nothing in
the pipeline calls it.**

Nothing in this pipeline detects a bracket. `system_grouping` INFERS family
boundaries from where the interior barlines stop, and the `OMR_BRACKET_COLUMNS`
repair that landed earlier today
([omr-bracket-stability-2026-09](../omr-bracket-stability-2026-09/FINDINGS.md))
explicitly DISCARDS any ink cluster crossing every gap — which is what a
full-system bracket is. The commission: read the bracket instead, and test
Sean's second idea, that the discarded full-height objects define the SYSTEM.

---

## Headline

**1. The bracket is readable, and its convention is a property of the
PUBLISHER, not of music.** Two of the five editions in the scan corpus print
*no section bracket at all* — one rule over the whole orchestra, with the
families marked only by stopping the barlines, which is exactly the signal the
incumbent already reads. Read off the print, at 600 dpi, by hand:

| publisher (work) | what stands at the left edge | section brackets? |
|---|---|---|
| **Peters** (Bach, Brandenburg 3) | three brackets 3\|3\|3 + a brace on the continuo | **yes, 3** |
| **Breitkopf** (Brahms 1) | two brackets 9\|5 + braces on instrument pairs | **yes, 2** |
| unidentified scan (Mahler 5) | section brackets + braces on pairs | yes |
| **Litolff** (Beethoven 5) | ONE bracket, whole orchestra | **no** |
| **Simrock** (Dvořák 9) | ONE bracket, whole orchestra, + braces on pairs | **no** |

⚠️ **And a bracket block is an ENGRAVING unit, not an instrument family.**
Breitkopf brackets winds + brass + timpani as ONE block against the strings
(`out/crops/brahms-p3-gap2.png`: the bracket runs straight through the
clarinet/bassoon boundary; `brahms-p3-gap8.png`: it terminates between timpani
and violin I while the systemic barline runs on). The same conclusion
`benchmarks/omr-structural-parts-2026-09` reached from the other side.

**2. Reading the bracket is WORSE than inferring it, against hand-verified
printed truth.** Scored on the two editions whose printed blocks are known:

| | systems | bracket reader, exact | incumbent (`px`, shipping default) | incumbent (`cols`, today's fix) |
|---|--:|--:|--:|--:|
| Bach / Peters, 12 staves, printed **3\|3\|3** | 22 | **5** | 16 contain all three | **22 contain all three; 21 exactly `[2,5,8,9]`** |
| Brahms / Breitkopf, 14 staves, printed **9\|5** | 15 | **1** | — | **15 of 15 exactly `[8]`** |

and on the consistency measure the stability work used — two systems on one
page with the same staff count are the same printed lineup — the reader
disagrees with itself on **0.882** of pairs against the repaired incumbent's
**0.055**.

**3. ✅ Which incidentally supplies the measurement the bracket-stability work
said it most wanted.** That FINDINGS.md closes with *"I did not re-run that
audit under the flag, and it is the measurement this work most wants next…
it would convert 'the readings now agree with each other' into 'the readings
are now right'."* Rows 1-2 above are that measurement, against printed truth
read off the page rather than derived from an encoding: **`OMR_BRACKET_COLUMNS`
reads the printed bracket blocks exactly on 21 of 22 Bach systems and 15 of 15
Brahms systems**, where the shipping default is right on 16 and 0 respectively.

**4. Sean's system hypothesis is half right, and the right half is already
implemented.** Over 57 pages, no left-edge object ever bridged a system break —
**0 of 147 read blocks span two systems** — which is precisely the property the
existing connectivity VETO relies on. What they cannot do is state a system's
extent: on a section-bracketed edition the maximal left-edge object is a
section bracket, so the reading over-splits on 27 of 57 pages (Bach 0 of 11
exact, against Litolff's one-bracket pages at 7 of 12).

**Recommendation: do not wire it in.** §7.

---

## 1. What is actually there

`probe_strokes.py` reads the band around each system's own left edge
(`median(x_start) − 9 … +3` staff spacings), closes vertical breaks the way
`gap_bridging_counts` does, and reports every tall vertical stroke as an object:
x span, thickness, y extent, straightness, and which staves it covers.
Model-free; 102 systems over 60 pages of the five scan-gate editions.

**The crops are the evidence, and they are NOT committed.**
`benchmarks/**/crops/` is gitignored repo-wide (`.gitignore:112`), so
`out/crops/` exists on disk and in no commit. `sh probe/regenerate_crops.sh`
rebuilds every one of them from the library store — verified byte-identical by
md5 after deleting the directory. ⚠️ **The same rule has already caught a
neighbouring benchmark**: `benchmarks/omr-brahms-lineup-2026-09/FINDINGS.md`
sources its page reading to crops "committed as `0a3c50f6`", and `git ls-files`
on that directory returns six files and no image. Do not write "committed" of
anything under a `crops/` directory without checking.

**Peters / Bach** (`bach-p8-s0.png`, four strips of three staves): three
brackets, each with visible square terminals, ending at the bottom line of
staves 2, 5 and 8; the systemic barline beside them runs on; the last strip
shows an unmistakable **brace** over the continuo. The reader sees them:

```
bach p3 sys1   x= 93-103  thick 0.47sp  y 3229-3800  covers [0,1,2]
               x= 96-105  thick 0.43sp  y 3977-4586  covers [3,4,5]
               x= 99-108  thick 0.43sp  y 4794-5376  covers [6,7,8]
```

**Litolff / Beethoven 5** (`wide-p38-top.png`, legible at 2×): one thick rule
with a small terminal at the top, running the whole system past `Fl. Ob. Cl.
Fag. Cor.` without a break. The winds|brass boundary that
`omr-bracket-stability-2026-09` §1b measured — every interior barline column at
0.01-0.17 coverage there — **is not bracketed at all**. A full-band run
inventory over x 200-400 confirms it: every run at x 343-361 spans y 420→1944,
the whole system, and there is nothing to its left.

**Simrock / Dvořák** (`dvorak-gaps-3-and-9.png`): the two gaps the incumbent
calls boundaries, side by side at 3×. The bracket runs **continuously through
both**; the braces on the instrument pairs are the curly shapes. One bracket.

**Breitkopf / Brahms** (`brahms-p3-gap8.png` vs `brahms-p3-gap2.png`): at the
timpani|violin gap the thick bracket ends with a terminal and a new one begins
below, while the thin systemic barline continues — the discriminator, visible
in one image. At the clarinet|bassoon gap the same bracket runs straight
through.

---

## 2. Reach

`probe_vs_incumbent.py`, 102 systems, 60 pages, five publishers.

| publisher | systems | states blocks | one spanning rule only | no rule found |
|---|--:|--:|--:|--:|
| bach | 22 | 22 | 0 | 0 |
| beethoven | 24 | 3 | 16 | 5 |
| brahms | 24 | 24 | 0 | 0 |
| dvorak | 18 | 16 | 0 | 2 |
| mahler | 14 | 14 | 0 | 0 |
| **TOTAL** | **102** | **79** | **16** | **7** |

⚠️ **Read this table against §1, not on its own.** Dvořák prints one bracket
and the reader "states blocks" on 16 of 18 of its systems — those are its
BRACES, and they are wrong about the bracket. Litolff's mixture of
`spanning_only` (16) and `no_rule` (5) is not a printing difference either;
it is the reader losing a rule it found on the neighbouring page. Reach as
"the reader produced an answer" is 79/102; reach as "the page carries section
brackets AND the reader found them" is much smaller, and §4 is the honest
version of it.

---

## 3. Three faults found while building the reader

All three produced *confident* wrong answers, which is the shape this repo
keeps paying for. Each is now pinned by a test that has been verified RED
(`probe/verify_red.py`, log in `out/verify-red.log`).

**(a) The closing merges the staff lines.** `BRIDGE_GAP_TOLERANCE_SPACINGS`
(0.6) is sized to bridge a dotted rule; the white between two staff lines is
about 0.8 spacings but the kernel is `2·round(0.6·sp)+1`, which on a 15.75 px
spacing is 19 px against a 12.75 px gap. Every column standing inside the staff
produces one solid run per staff — shaped exactly like a bracket over a single
staff. `gap_bridging_counts` is immune by construction (it only ever looks
BETWEEN staves); a left-edge reader is not. Removed by dropping runs that cross
no inter-staff gap.

**(b) The filter has to run at the RUN level, not the stroke level.** Filtering
finished strokes leaves the artefact free to be absorbed into the rule standing
beside it: the staff-height run is x-adjacent to the systemic barline and fully
contained in its run, and the stroke's median y then follows the many short
runs rather than the one long one. A six-staff synthetic system with one
bracket over everything reported a single stroke *"covering staves 2-3"*.

**(c) IoU linking was tried and is worse — and the two failures pull opposite
ways.** Containment-linking is what allows (b); intersection-over-union refuses
that link (50/690 = 0.07) and also refuses REAL ones, because a scanned rule's
columns have ragged runs. At IoU 0.7 a warped bracket fragments into two-staff
pieces and the reader asserts a boundary at nearly every gap — measured on
Peters Bach, where the printed 3|3|3 read back as
`[0,1,2,3,4,5,6,7,8,9,10]`. ⚠️ **The synthetic suite cannot falsify this
choice** (a synthetic rule is perfect, so IoU ≈ 1 and every test still passes —
see the IoU row of `out/verify-red.log`); the corpus did.

**And one refused variant worth recording.** A level containing the systemic
barline was first *disqualified*; the barline stands within about one staff
spacing of the section brackets, so on a clean page it took the brackets down
with it and the reading came back `spanning_only`. A spanning rule is now
DROPPED from its level instead — which is exactly what
`system_grouping.systemic_column_counts` does with a cluster crossing every
gap, for the same reason.

⚠️ **Fixing (a)+(b) RAISED reach and LOWERED precision**, which is worth
stating plainly: 63 → 79 systems stating blocks, and within-page
self-consistency 0.294 → 0.118. The artefact had been accidentally silencing
the brace level by swallowing it. `out/vs-incumbent-v1-blockcount-level.log`
holds the earlier arm.

---

## 4. Against the incumbent

### 4a. The hand-verified printed truth

The two editions whose printed blocks are known independently — Bach 3|3|3 from
the crop above and from `omr-structural-parts-2026-09`'s hand adjudication of
the same edition (`3,3,3,1,2`), Brahms 9|5 from the crop above:

```
Bach / Peters, 22 twelve-staff systems, printed boundaries {2,5,8}
  bracket reader   exactly [2,5,8]            5 / 22      (contains all three: 19)
  incumbent px     contains all three        16 / 22
  incumbent cols   contains all three        22 / 22      exactly [2,5,8,9]: 21 / 22

Brahms / Breitkopf, 15 fourteen-staff systems, printed boundary {8}
  bracket reader   exactly [8]                1 / 15
  incumbent cols   exactly [8]               15 / 15
```

`cols` adds gap 9 on Bach, which is the **brace** boundary below the third
choir — a true printed boundary at the next nesting level, not an error.

### 4b. Self-consistency

Same measure as `omr-bracket-stability-2026-09` §2: two systems on one page with
the same staff count are the same printed lineup, so a disagreement is the
detector disagreeing with itself about ink it read twice.

| | disagreement rate |
|---|--:|
| incumbent, shipping default (pixels) | 0.384 |
| incumbent, `OMR_BRACKET_COLUMNS` | **0.055** |
| **bracket reader** | **0.882** |

### 4c. Can it tell when it is wrong?

`probe_admission.py`, offline over the dump, with the gates stated before they
were scored: **TILES** (the stated blocks form one contiguous run of staves — a
section-bracket level tiles a stretch of the score, a level of braces over
instrument PAIRS does not), **FROM_TOP**, **HALF**.

| gate | admitted | agree with incumbent | bracket-only | incumbent-only |
|---|--:|--:|--:|--:|
| none | 79 | 156 | 192 | 32 |
| TILES | 16 | 26 | 4 | 13 |
| TILES+FROM_TOP+HALF | 15 | 25 | 2 | 13 |

The gate removes most of the noise and admits 15 of 102 systems — but **3 of
the 15 are still wrong** (two Bach systems read the barline + continuo brace as
the bracket level, `[9,10]` and `[9]`; one Beethoven reads `[6]` where the
incumbent reads `[3,5]`), and one that "agrees" does so by accident: Dvořák
p8 s1 reads `[3,9]`, matching the incumbent, on a page §1 shows carries no
section bracket at those gaps at all.

⚠️ **On the earlier reader revision the same gate admitted 11 systems with
ZERO bracket-only boundaries against `cols` and exactly ONE against the
shipping default — and that one was correct** (Bach p3 s0: the bracket
supplies gap 8, which `px` misses and the print confirms). That is the
strongest case this work can make for the reading, and it is made by the
revision with the known extent bug. Both arms are in `out/`.

### 4d. The failure modes are OPPOSITE, and that is the one durable structural fact

Incidental ink can only push a crossing count UP, so the barline-stop rule
fails by **merging** blocks — `omr-structural-parts-2026-09` measures boundary
precision 0.920 against recall 0.523, almost nothing invented. A rule broken by
a bad scan splits one stroke in two, so the bracket reader fails by
**splitting**. In principle that is the argument for combining them.

**In practice the combination needs a terminus/break discriminator and there
isn't one.** `probe_endpoints.py` measures both candidates on Bach, where every
end that is not at gap 2, 5 or 8 is a break by construction:

| discriminator | keeps termini | keeps breaks |
|---|--:|--:|
| bottom end, distance to the block's last staff line, \|d\| ≤ 1.52 sp | 61/63 | 4/16 |
| bottom end, **terminal flare** (widest tip row / body row), ≤ 1.96 | 62/63 | 11/16 |

The flare — the serif a printed bracket ends in, which is the physically right
signal — **does not separate at all**: all 16 breaks fall inside the termini's
range. The distance test is better but it is not a gate either; a break lands
near a staff line about a quarter of the time, which is roughly what chance
gives when boundaries recur every eight spacings and the tolerance is 1.5.

---

## 5. Sean's system hypothesis

> *"lines that go through the whole system could help determine what a system
> is and we may be discarding that info."*

`probe_system_extent.py` tests it honestly: the band is anchored on the PAGE
(one scan per distinct `x_start` mode, so a differently-indented system is not
cut out — the poisoning `OMR_CHOIR_GROUPING`'s cue B exists for), the maximal
left-edge objects induce a partition of the page's staves, and only afterwards
is that compared with `Staff.system_index`. 57 pages.

| publisher | pages | exact | ≥1 staff unassigned | over-split | under-split |
|---|--:|--:|--:|--:|--:|
| bach | 11 | 0 | 11 | 4 | 0 |
| beethoven | 12 | **7** | 3 | 2 | 0 |
| brahms | 12 | 5 | 1 | 7 | 0 |
| dvorak | 10 | 2 | 7 | 4 | 1 |
| mahler | 12 | 2 | 9 | 10 | 0 |
| **TOTAL** | **57** | **16** | **31** | **27** | **1** |

**The verdict is a split one, and both halves are useful.**

✅ **The half that is TRUE: a left-edge object never bridges a system break.**
**0 of 147** read blocks span two of the incumbent's systems. The single
"under-split" row (Dvořák p13) is not a merge — it is a miss, with 16 of 30
staves unassigned because the second system's rule was not found. So these
objects can only ever over-split, which is exactly the property that makes the
existing use of them — a VETO on a gap-based break, never a positive
definition — sound. Sean's intuition that the information is load-bearing for
system identity is correct; the pipeline is already extracting the part of it
that is safe.

❌ **The half that is FALSE: they cannot state a system's extent**, and the
reason is §1. On a one-bracket edition the maximal left-edge object *is* the
system (Litolff 7 of 12 exact); on a section-bracketed edition it is a section
bracket, and the reading over-splits (Peters **0 of 11**). Which of those an
edition is, is the thing you would need to know first. Preferring the systemic
BARLINE instead does not escape the circle: which object spans the system is
what you are trying to find out.

⚠️ **And 31 of 57 pages leave at least one staff unassigned**, a failure the
veto never has to face — a veto that finds nothing simply does not fire, while
a definition that finds nothing has to invent a system.

---

## 6. What I did not do

- **No default changed, no flag added, and nothing calls the module.** There is
  no measured improvement to justify a consumer.
- **No `remove_staff_lines` before the scan** — measured and refused 2026-09-04.
  The search here is bounded, not erased.
- **No YOLO class.** Phase 4f's precedent (thin lines belong to classical CV)
  points away from the detector, and §1-4 say the problem is not detection
  anyway.
- **`tools/omr/system_grouping.py` is untouched**, and so is `slots.py`.
- ⚠️ **No engraved arm.** `OMR_CHOIR_GROUPING`'s cue C was falsified by the
  engraved family (pooled OMR-NED 0.1306 → 0.8560) and cue C's own trap —
  uniformly low counts feeding a relative threshold — could recur here. It has
  not been checked, and it does not need to be while nothing consumes the
  module: **anyone wiring this in must run the eleven engraved fixtures first.**
  Recorded as a precondition, not as a result.
- **No 20-row scan-gate A/B**, for the same reason: an unconsumed module
  cannot move an edit count, and spending hours of shared CPU to confirm a
  structural zero is theatre.

## 7. Recommendation

**Leave it unwired, and treat the bracket as answered rather than open.**

The commission asked whether reading the bracket beats inferring it. It does
not, on this corpus, by a wide margin, and §1 says why it never could in
general: **two of five publishers print no section bracket at all**, so on
those editions there is nothing to read, and the barline-stop inference is not
a workaround for a missing detector — it is the reading of the only signal the
page carries.

The one thing that would change the calculus is a consumer that needs
boundaries on a *specific* section-bracketed edition and can afford an
abstaining reader: there, §4c's gate admits about 15% of systems and the
earlier revision's arm suggests those are nearly clean. That is a narrow enough
prize that it should wait for a consumer to ask for it.

**What this work should be remembered for instead** is §4a — the
bracket-stability fix now has an accuracy number against printed truth, not
only a consistency one — and §5's `0 of 147`, which is the first direct
evidence that the connectivity veto's premise holds on real pages.

## 8. Suite

`python3 -m pytest tools/omr/tests -q` on this branch: **2431 passed, 8
skipped** in 6m09s — the 2422 already on `main` plus the 9 added here. Nothing
existing was modified: `git status` on this branch is three untracked paths.

## 9. Files

```
tools/omr/bracket_reader.py            the reader (no consumer, no flag)
tools/omr/tests/test_bracket_reader.py 9 tests, each verified RED

probe/left_edge.py            the reader as first drafted, kept for the record
probe/probe_strokes.py        every left-edge stroke, per system  (§1)
probe/crop_left_edge.py       one system's left edge as a legible strip
probe/probe_reach.py          first (too strict) reach cut — kept, superseded
probe/probe_vs_incumbent.py   reader vs both incumbent arms      (§2, §4a, §4b)
probe/probe_admission.py      admission gates, offline           (§4c)
probe/probe_endpoints.py      terminus vs break                  (§4d)
probe/probe_system_extent.py  Sean's hypothesis                  (§5)
probe/verify_red.py           every test, with each mechanism disabled
probe/regenerate_crops.sh     rebuilds §1's crops (gitignored, not committed)

out/*.log, out/*.json         every run above
out/crops/                    §1's crops — ON DISK ONLY, see §1
```
