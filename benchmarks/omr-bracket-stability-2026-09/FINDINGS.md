# Bracket-group detection is unstable, and the instability is a UNIT ERROR

2026-09-06. Branch `worktree-agent-af8995d8aa51a7cbc`.
Flag: `OMR_BRACKET_COLUMNS`, **default OFF**.

`Staff.group_index` disagreed with itself across pages of one movement printing
one lineup. This finds the mechanism, prices the instability over five
publishers, repairs it, and — the part that decides whether it should land —
measures how far the repair can actually reach.

**Headline.** The rule compares a gap's crossing-column count to the system
median. That count is `(number of crossing objects) x (each object's width in
px)`, and only the object count is evidence: a barline stands at the same x in
every gap of the system, a stem or a slur stands wherever the music put it.
Counting the objects instead takes within-page bracket disagreement from
**0.384 to 0.055** over 144 pages of five publishers, and moves the rule's
0.5 cut off a continuum onto an **empty interval**: over 1130 gaps the largest
ratio below the cut is 0.333 and the smallest above it is 0.778, where under
the incumbent they are 0.4962 and 0.5000.

⚠️ **And it is worth nothing today.** `group_index` reaches the pipeline's
output through two consumers and both are inert here: the exported MusicXML is
**byte-identical** on the engraved fixtures and on the scan gate's most exposed
row. This is a repair to an internal signal, priced at zero edits — see
§6 before deciding whether to default it on.

---

## 1. The mechanism, measured

`Staff.group_index` comes from `system_grouping._assign_groups`, called at the
end of `assign_systems`. Its input is `gap_bridging_counts`: per adjacent staff
pair, the number of image COLUMNS whose ink covers ≥ `BRIDGE_INK_FRACTION`
(0.8) of the band from the upper staff's top line to the lower staff's bottom
line, after closing vertical breaks under 0.6 staff spacings, scanned over the
page-median staff extent widened by 4 spacings. Within a system,

```python
threshold = statistics.median(inner) * GROUP_BOUNDARY_RATIO   # 0.5
if 0 <= bridging[gap] < threshold: group += 1
```

### 1a. What the count is made of

`probe_what_crosses.py` keeps the crossing columns as RUNS instead of summing
them. Beethoven 5 / Litolff (`imslp984073`) p.38 prints the same 12-staff
lineup twice, and the two systems disagreed:

```
system 1  (3 groups — correct)              system 0  (2 groups — wrong)
 gap   px  runs                              gap   px  runs
   0  104   12                                 0  131   20
   1   64   10                                 1  135   19
   2   64   11                                 2   85   14
   3   23    3   <- winds|brass                3   52    9   <- winds|brass
   4   62   10                                 4   67   12
   5   61   10                                 5   61   11
   6   22    3   <- brass|strings              6   29    4   <- brass|strings
   7   67   10                                 7  107   13
   8   83   13                                 8   65   10
   9   65   10                                 9   66   11
  10   69   11                                10   61   10
 median 64, threshold 32                     median 66, threshold 33
 gaps 3 and 6 split                          gap 6 splits; gap 3 (0.788) does not
```

System 1's boundary gaps keep exactly **three** runs — x ≈ 342, 358, 2631: the
bracket, the systemic barline, the final barline. Every interior barline stops.

System 0's gap 3 keeps **nine**, at x = 346, 360, 743, 1001, 1220, 1253, 1779,
2385, 2633. The system's own barline columns are 353, 364, 684, 933, 1191,
1478, 1759, 2049, 2334, 2361, 2633. Only the left-edge pair and the final
barline coincide; **six of the nine stand at no barline column at all** — they
are ordinary music ink that happens to run the height of a gap. They take the
pixel count from ~19 to 52 and the ratio from ~0.29 to 0.788, over the cut.

### 1b. The boundary is real — the barlines demonstrably stop

Before repairing anything: is gap 3 a boundary? `probe_barlines_stop.py`
measures the ink coverage of the system's own barline columns (taken from a
reference gap the boundary did not help choose) inside every gap band. Beethoven
5 p.38 system 0:

| gap | max coverage at an INTERIOR barline column |
|---|--:|
| 0,1,2 (inside winds) | 1.00 |
| **3 (winds\|brass)** | **0.17** |
| 4,5 (inside brass) | 1.00 |
| **6 (brass\|strings)** | **0.09** |
| 7…10 (inside strings) | 1.00 |

At gaps 3 and 6 every interior barline column reads 0.01–0.17. The barlines
stop; the boundary is printed. The lineup agrees independently — the hand-read
roster `benchmarks/omr-scan-e2e-2026-09/works.json` records for this edition's
12-staff page is `Fl Ob Cl Fg | Cor Tr Timp | Vl1 Vl2 Vla Vc Basso`, exactly
4 | 3 | 5, which is what system 1 reads and system 0 does not. (That row is
p.1, not p.38; what makes it usable here is that p.38's two systems print the
same twelve staves, which is why they were comparable in the first place.)

### 1c. Why a ratio of pixels cannot separate these

On a boundary gap the pixels come from ~3 system-spanning objects; on an
interior gap from the interior barlines, whose number is *how many bars the
system prints*. So the ratio is roughly `3 / (n_bars + 3)` and crosses 0.5 near
three bars a system — which is squarely inside what these editions print. The
same physical boundary lands on both sides of the cut:

| page | system | boundary px | median px | ratio | split? |
|---|---|--:|--:|--:|:--|
| p.23 | 1 | 33 | 57 | 0.579 | no |
| p.31 | 1 | 34 | 80 | 0.425 | yes |
| p.38 | 1 | 23 | 64 | 0.359 | yes |
| p.38 | 0 | 52 | 66 | 0.788 | no |

**And the population confirms there is no cut to find.** Over 2841 gaps of 248
systems, the pixel ratio is a continuum straight through the decision region:
the largest ratio below the cut is **0.4962** and the smallest above it is
**0.5000**. There is no gap around the constant at all — the rule is not
reading a separation, it is slicing a continuum, and every one of the 194 gaps
within ±0.15 of the cut is a coin toss.

## 2. The rate, before any fix

`probe_stability_rate.py`, 144 pages, 6 edition files, **5 publishers**
(Litolff, Breitkopf, Simrock, Peters, and the Mahler scan), 0-based pages 0-23
of each. Model-free, so the whole corpus costs five minutes.

The measure is **within-page**: two systems printed on the SAME page with the
same staff count are the same printed lineup essentially always — a page turn
does not change which instruments are tacet mid-page — so a disagreement
between their group vectors is the detector disagreeing with itself about ink
it read twice. (A within-edition measure is also reported in `out/`, as an
upper bound: two different tacet subsets can share a staff count.)

| publisher | pairs | disagreeing | rate |
|---|--:|--:|--:|
| bach (Peters) | 23 | 16 | **0.696** |
| beethoven (Litolff) | 19 | 3 | 0.158 |
| brahms (Breitkopf) | 14 | 4 | 0.286 |
| dvorak (Simrock) | 16 | 4 | 0.250 |
| mahler (unidentified) | 1 | 1 | 1.000 |
| **TOTAL** | **73** | **28** | **0.384** |

**Not confined to one publisher** — every one of the five shows it, so the clean
negative that would have ended this investigation is not available. Bach /
Peters is the worst: its 12-staff systems produced **nine distinct group
vectors** across 46 systems (`000111222344`, `000111222333`, `000000111222`,
`000111111222`, `000000111233`, …), modal share 0.457.

## 3. The fix

`OMR_BRACKET_COLUMNS`. Same split rule, same 0.5 ratio; a different quantity
under it.

* `gap_crossing_runs` — `gap_bridging_counts` refactored to keep the crossing
  columns as `(centre_x, width)` runs. The old function is now derived from it
  (`sum(w)` is exactly the old column count), so the two cannot drift.
* `systemic_column_counts` — within one system, cluster run centres across its
  gaps at `BRACKET_COLUMN_TOL_SPACINGS` (0.75 staff spacings: the page's warp
  drifts a barline ~9 px across a system, the pitch between barlines is ~250).
  A cluster recurring at `BRACKET_COLUMN_SUPPORT` (0.5) of the gaps is the
  system's own column; anything seen once is incidental and contributes nothing.
* **A cluster seen at EVERY gap is dropped.** The left-edge complex and the
  final barline are drawn through the whole system by definition, so they
  distinguish no gap from any other — and a constant added to both sides of a
  ratio is not neutral. Measured on p.23 system 1, both variants run through
  the shipped clustering:

  ```
  without the exclusion:  [6, 6, 5, 3, 6, 6, 2, 6, 6, 6, 6]  median 6
                                    ^ gap 3 = 0.500 — the rule's own knife
                                      edge, and `<` means NO split
  with    the exclusion:  [4, 4, 3, 1, 4, 4, 0, 4, 4, 4, 4]  median 4
                                    ^ gap 3 = 0.250 — split, agreeing with
                                      every other system of that lineup
  ```
* `BRACKET_COLUMN_MIN_EVIDENCE` — the abstention, forced by the engraved
  family. See §5.

⚠️ **The clustering is greedy chain-linking, so it can in principle swallow two
real barlines into one column and undercount.** Checked rather than assumed:
over 165 clusters on six pages of two publishers the widest cluster spans
**2.47 staff spacings** end to end, against a barline pitch of roughly 16
spacings on the same pages. Chaining happens (up to about three links) and
never comes within a factor of six of merging two barlines.

### The cut is now on an empty interval, and that is the strongest result here

Same measurement as §1c, over **1130 gaps of 95 systems, all five publishers**:

```
                       largest below the cut    smallest above it
  pixels (incumbent)          0.4962                0.5000      <- continuous
  columns (this fix)          0.3333                0.7778      <- EMPTY
```

Nothing lands in `0.3333 < r < 0.7778`. `GROUP_BOUNDARY_RATIO = 0.5` is
inherited unchanged and now sits inside an empty interval, which is what this
repo asks of a constant — while under the incumbent **292 of 2841 gaps
(10.3%) fall inside that same interval**, each of them decided by which side
of a continuum it happened to land on.

| ratio bin | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **columns** | 208 | 8 | 8 | 1 | **0** | **0** | **0** | **0** | 13 | 35 | 829 | 23 | 5 |

### The rate, after

| publisher | pairs | off | on |
|---|--:|--:|--:|
| bach | 23 | 0.696 | **0.043** |
| beethoven | 19 | 0.158 | **0.105** |
| brahms | 14 | 0.286 | **0.000** |
| dvorak | 16 | 0.250 | **0.000** |
| mahler | 1 | 1.000 | 1.000 |
| **TOTAL** | **73** | **0.384** | **0.055** |

Within-edition modal share moves with it: Bach 12-staff 0.457 → 0.978 (9
distinct vectors → 2), Brahms 14-staff 0.84 → 1.000, Dvorak 15-staff 0.824 →
1.000, Beethoven 12-staff 0.857 → 1.000.

The four residual disagreements are all boundary shifts of ONE staff
(`00001122222` vs `00001112222`), not structural collapses. Mahler's single
pair is unhelped and is the one publisher this does not reach; its edition is
also the only one whose 16/17/19-staff buckets never repeat a vector under
either arm, so its instability may be lineup change rather than detection.

### ✅ An independent prior measurement says the same thing from the other side

`benchmarks/omr-structural-parts-2026-09/FINDINGS.md` §Phase 4 audits the
incumbent's bracket blocks against HAND-ADJUDICATED truth, on this same 20-row
scan corpus, and reports

> block boundary precision **0.920** (23/25), recall **0.523** (23/44)

That is the same fault seen from the accuracy side rather than the consistency
side: **21 of 44 real bracket boundaries are missed, and almost nothing is
invented.** It is exactly what §1a predicts — incidental ink can only push a
gap's count UP, so the pixel rule fails by MERGING groups, never by splitting
them. My within-page disagreements have that shape too: p.23 and p.38 read two
groups where three are printed, and Bach's nine vectors are mostly one boundary
short of each other rather than differently placed.

⚠️ **I did not re-run that audit under the flag, and it is the measurement this
work most wants next.** It would convert "the readings now agree with each
other" into "the readings are now right", against truth I did not construct.
Its `evidence.json` is built from full transcriptions of the 20 rows
(`build_evidence.py`), so it is a benchmark-scale run rather than a probe, and
it did not fit in this session. The anchors I do have are narrower: the roster
agreement below, and the direct barline-coverage measurement in §1b.

### The named pages

The three pages the task named now agree with each other and with the roster:

```
p23 sys1  ->  [0,0,0,0,1,1,1,2,2,2,2,2]
p31 sys1  ->  [0,0,0,0,1,1,1,2,2,2,2,2]
p38 sys0  ->  [0,0,0,0,1,1,1,2,2,2,2,2]      (was [0]*7 + [1]*5)
p38 sys1  ->  [0,0,0,0,1,1,1,2,2,2,2,2]
```

## 4. What I refused

**Sean's hypothesis — "this needs to be CV, thin lines" — is not what the
measurement supports, and I did not build a detector.** The precedent is real
(Phase 4f moved stems and beams off YOLO on exactly those grounds) but it does
not apply here: brackets were never detected by YOLO in the first place. The
signal is already classical CV — a morphological closing and a column coverage
test — and it was reading the right ink. What was wrong was the UNIT it was
summarised in. A new detector would have been built on top of a working
measurement.

**Not `remove_staff_lines` before the scan.** Measured and refused 2026-09-04
(7-13 pooled reading points, a third of the noteheads, `beam` precision
0.783 → 0.343). Nothing here needs it: the search is bounded, not erased.

**Not a wider `BRACKET_COLUMN_SUPPORT`, and not a tuned `GROUP_BOUNDARY_RATIO`.**
Given the empty interval in §3, no ratio anywhere in 0.334-0.777 changes an
answer on the measured corpus, so there is nothing to tune and the incumbent
constant stays where it is.

**Not `tools/omr/slots.py`.** Off limits this session, and nothing here needs
it: `map_groups` already relates the two bracket vocabularies by monotone block
correspondence, which is the right layer for that and stays right whether or
not detection is repaired.

## 5. The engraved family — where this nearly repeated cue C's mistake

⚠️ **A ratio needs something to be a ratio of, and the engraved corpus has
nothing.** The rule's premise is that interior barlines STOP at a group edge;
that is only testable where interior barlines cross gaps at all. A LilyPond
render of a conductor's score bars per staff, so the only ink crossing any gap
is the system-start bar. A whole 25-staff Bruckner system carries **two**
crossing columns in total, against a scan's sixty to a hundred and thirty:

```
bruckner-sym5-mvt1.pdf, system 0, 25 staves, 24 gaps
  systemic columns: 2, at x = 828 and 904
  per-gap pixel counts: 7 to 18       (a scan's are 22 to 135)
```

The first version of this fix read 1 against a median of 2 as "half the usual"
and manufactured a boundary at every gap the start bar happened to miss —
**11 groups on that Bruckner system**. That is `OMR_CHOIR_GROUPING` cue C's
falsification arriving by the same road (uniformly low counts feeding a
relative threshold; engraved pooled OMR-NED 0.1306 → 0.8560, nine works'
barlines deleted), and it is why cue C carries a second required condition.

The populations are disjoint with room to spare. Median informative columns per
system:

| corpus | distribution | |
|---|---|--:|
| engraved (11 LilyPond fixtures, 11 systems) | 0 ×6, 1 ×3, 1.5, 2 | max **2** |
| scanned (5 publishers, 95 systems) | 4 ×12, 5 ×12, 6 ×4, 7 ×5, 8 ×8, 9 ×16, … 21 | min **4** |

`BRACKET_COLUMN_MIN_EVIDENCE = 3`. The test is `median < MIN`, so a floor of
either 3 or 4 reads both corpora identically; 3 is taken, one unit clear of
each population. **5 would be wrong** — it would silence Bach and Mahler, whose
systems sit at 4, and that only became visible when the evidence sample was
widened from three publishers to five. Below the floor the system abstains to
one group, the honest answer for a page carrying no bracket evidence, and the
answer `_is_grouped_system` reads as "not grouped" so cue C cannot reach it
either. With the floor, **all 11 engraved fixtures read exactly one group**.

## 6. ⚠️ REACH — the part that decides whether this should land

Reach before accuracy. `Staff.group_index` has exactly two consumers:

1. **`measure_extractor._is_grouped_system`** — cue C of `OMR_CHOIR_GROUPING`,
   which can flip a system out of open-score mode and therefore change its
   BARLINES. This is the one that moves OMR-NED.
2. **`slots.py`** — part naming, measured elsewhere in this repo to change the
   score by exactly nothing.

Cue C is model-free, so its input can be checked EXACTLY under both arms —
better than a benchmark A/B, which on the 20-row scan gate carries a ±6-edit
noise floor. `probe_cue_c_reach.py`:

**Scan gate, all 20 hand-verified rows.** `_is_grouped_system` is identical on
**19 of 20**. The one difference (`brahms-sym1-mvt1-317803-p4`, system 1,
False → True) cannot reach anything: cue C also requires a window-blind
internal gap and that page has none. The only gate page that HAS one — Bach
Brandenburg 3 p.1, the row `OMR_CHOIR_GROUPING` was shipped for — reads
identically under both arms.

**Engraved fixtures.** `_is_grouped_system` changes on 9 of 11 (True → False,
the abstention of §5) and reaches nothing: `blind == []` on all eleven, so cue
C's second condition fails under both arms.

**Widened beyond the gate**, because a whole-work run touches pages the gate
never scores: the same probe over **144 pages of all five publishers**
(`--corpus scan`, `out/cue-c-wide.log`). The two conditions cue C needs are
almost disjoint on this corpus, and completely disjoint in fact:

```
144 pages
    139  _is_grouped_system identical under both arms
      5  it differs        — all five report blind == []
      2  carry a window-blind system (Bach p.0, p.16) — both identical
      0  BOTH differ AND carry a blind system
```

So across 144 pages there is no page on which cue C could act on the
difference. That is the generalisation the gate alone does not license.

**End-to-end, full pipeline, real weights, direction text forced off in both
arms** (it is orthogonal and it is the one stage this repo records as
non-deterministic):

| page | why this one | result |
|---|---|---|
| Bach Brandenburg 3 p.1 | the ONLY gate page with a window-blind system — the one page where cue C can fire at all | **BYTE-IDENTICAL** |
| Brahms 1 p.4 | the ONLY gate page where `_is_grouped_system` differs between the arms | **BYTE-IDENTICAL** |
| Beethoven 3, Beethoven 5, Brahms 1, Brahms 4, Bruckner 5, Dvořák 9 (engraved) | the family that falsified cue C | **BYTE-IDENTICAL, 6 of 6 run** |

The two scan pages are the complete exposed set: every other gate row has
neither a blind system nor a changed `_is_grouped_system`, so it cannot differ
by construction. A byte-identical export is strictly stronger than an equal
OMR-NED and has no noise floor to argue about — where a pooled 20-row figure
would have had to be read against ±6 edits.

⚠️ **Five engraved fixtures (Mahler 5, both Mozarts, both Tchaikovskys) were
still running when this was written** and are not claimed. They are
confirmatory rather than decisive: the exact control above already says the
change cannot reach cue C on any of the eleven. `out/ab-engraved-export.log`
(the first three) and `out/ab-engraved-export-nosurya.log` (the rest) carry
whatever they finished as.

⚠️ **The engraved run had to be restarted, and the reason is a real hazard for
anyone repeating this.** The first attempt wedged mid-work on its own Surya
worker (the documented 0%-CPU stall). Killing the worker let the run continue —
**and that is the trap**: the arm in flight then fell back to a no-Surya label
read while the *other* arm would have got Surya's, so a byte comparison across
them would have been measuring the OCR rung, not the flag. The restart removes
the `.venv-surya` symlink so Surya self-disables identically in both arms.
Direction text is off in both arms for the same reason. Neither is production
configuration, and neither needs to be: the claim is "arm A equals arm B", not
"this matches a shipping run".

**So: the fix is correct and currently costs and earns nothing.** It should land
default-OFF as a repaired signal waiting for a consumer, not as an accuracy
change. What would make it earn its keep is a consumer that trusts
`group_index` — `slots.py`'s group term with `map_groups` removed, a
condensation prior, a roster join — and every one of those is a separate
decision that should be taken knowing the signal underneath is now stable.

## 7. Tests

`tools/omr/tests/test_system_grouping.py`:

* `test_incidental_ink_hides_a_bracket_boundary_from_the_pixel_rule` — the
  RED-side control: a synthetic page carrying six crossing columns at no
  barline x (Beethoven 5 p.38 system 0 in miniature) and the assertion that
  the incumbent MISSES the boundary. If it ever stops missing it, the fix test
  below is no longer testing anything, and this fails loudly.
* `test_bracket_columns_recover_the_boundary_the_pixel_rule_misses` —
  **verified RED** with the mechanism disabled (`use_columns = False`):
  `assert [0,0,0,0,0,0,...] == [0,0,0,1,1,1,...]`, `At index 3 diff: 0 != 1`.
* `test_bracket_columns_read_the_clean_page_identically` — both arms agree with
  no incidental ink, so the flag is a repair rather than a rewrite.
* three unit tests on `systemic_column_counts`: ink seen at one gap only is
  dropped, columns crossing every gap are excluded, and the `-1` no-evidence
  marker is mirrored.

Full suite on the merged tree (main at `9d40b084`):
**2422 passed, 8 skipped** in 12m25s.

## 8. Recommendation

**Land default-OFF.** Everything measured says the flag is correct and that
nothing downstream can tell. A default change in this repo is justified by a
measured improvement, and there is none to quote: the exports are
byte-identical, so an ON default would be a change nobody can price and nobody
can regression-test by score. `test_bracket_columns_recover_the_boundary_the_
pixel_rule_misses` is what guards it in the meantime, which is the same
arrangement `OMR_SLOT_STITCH` and `OMR_CONDENSED_PARTS` sit in.

**The trigger for flipping it on** is a consumer that trusts `group_index` —
`slots.py`'s group term without `map_groups` softening it, a condensation
prior, a roster join. On the day one of those is priced, this flag goes on in
the same measurement, because the alternative is pricing that consumer against
a signal that disagrees with itself 38% of the time.

⚠️ **One asymmetry worth stating before that day.** Turning this on makes
`_is_grouped_system` FALSE on every engraved fixture (§5), where today it is
True on 9 of 11 for no reason but jitter. Cue C's second condition means that
costs nothing now — but it does mean the flag removes an accidental
True that some future cue could come to depend on. It should not, and this is
the note that says so.

## 9. Files

```
probe/probe_bracket_groups.py    per-system bridging, median, threshold, groups
probe/probe_what_crosses.py      the count as RUNS — objects vs pixels
probe/probe_barlines_stop.py     do the interior barlines really stop? (§1b)
probe/probe_consensus.py         both rules side by side on one page
probe/probe_stability_rate.py    the corpus rate, within-page and within-edition
probe/probe_evidence_floor.py    the abstention floor's two populations (§5)
probe/probe_cue_c_reach.py       EXACT reach control on cue C (§6)
probe/ab_export.py               full-pipeline byte A/B, one page
probe/ab_export_batch.py         full-pipeline byte A/B, many pages
probe/ab_group_vectors.py        group vectors only, both arms, one process
```

Every probe is model-free except the two `ab_export*` ones.
