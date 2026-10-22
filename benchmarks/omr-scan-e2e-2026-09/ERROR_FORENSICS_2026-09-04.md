# Scan-gate error forensics — where the 29,082 edits actually come from

2026-09-04. Pure analysis: no pipeline code touched, nothing re-transcribed.
Every number here is measured against the **production graft baseline** of
WIDENED_BASELINE_2026-09-04.md — pooled **0.8387 / 29,082 edits over the 10
pooled rows** (`results-widened-graft.json`; the Bach stress row reports
per-row only) — by re-scoring and dissecting the *same prediction bytes* in
the `scan-rebaseline` worktree's `fixtures/` (`*.widened-graft.omr.musicxml`).
Method per row: `dump_ops.py` op-level dumps; a positional per-staff
note classifier over the `works.json` staves maps (the adaptation of
`attribute_wrong_notes.py` described in §3); a fresh
`condensation_arm.py` run on the graft fixtures; and one simulation
(the Brahms p2 stitch, §2c). Commands in §7.

The three OMR-NED traps are honored throughout: the metric is symmetric
(element counts are checked before crediting anything — this pool
*under*-emits, 14,847 pred vs 19,828 truth symbols, so recall dominates and
dilution is not the story); whole-bar buckets are amplified (never quoted as
severity — they are opened instead, §2); and `wrong note` is unpaired notes,
not wrong pitches (§3 separates them: on scans it is mostly *missing/extra*
notes, and the truly-mispitched part is constant-offset clef damage).

---

## 1. The pooled picture, and why the category split misleads

| category | edits | share |
|---|--:|--:|
| entire measure insert/delete | 10,877 | 37.4% |
| entire staff insert/delete | 8,215 | 28.2% |
| wrong note | 7,551 | 26.0% |
| everything else (20 categories) | 2,439 | 8.4% |

The 65.6% "structural" mass reads as if the pipeline cannot find staves and
measures. **It can: segmentation is essentially solved on these pages.**
Staves are N/N on all 10 pooled rows; page measure totals are exact on 8,
one short by a single missed barline (984073-p2, m19|m20 on the low-res
raster — recorded in `works.json`), one long by a single spurious cell
(brahms-p1's cautionary 9/8 read as a bar). The structural mass is instead
(a) a **truth-convention floor** and (b) **whole-bar amplification of
recognition failures** — bars both sides have that musicdiff refuses to
pair, charged delete-whole + insert-whole.

---

## 2. Opening the structural 65.6%

### 2a. The condensation floor — measured, row by row: **~8,300–8,600 edits (28–29% of the pool) is irreducible under the current protocol**

A printed page condenses (Flauti share a staff; the reference has Flute 1
and Flute 2), so N_truth−N_staves whole parts per row can never pair and
their entire content is charged. `condensation_arm.py` was re-run **on the
graft predictions** (prior recorded run was on older bytes): it rebuilds
the truth with `partsToVoices` under the hand-read page allocation and
re-scores. Raw column reproduces `results-widened-graft.json` exactly.

| row | parts→staves | raw ed | condensed ed | floor (explained) |
|---|---|--:|--:|--:|
| beethoven-984073-p1 | 18→12 | 1,286 | 870 | 416 (32.3%) |
| beethoven-984073-p2 | 18→11 | 4,449 | 2,969 | 1,480 (33.3%) |
| beethoven-575951-p1 | 18→12 | 1,362 | 892 | 470 (34.5%) |
| beethoven-575951-p2 | 18→11 | 4,471 | 2,513 | 1,958 (43.8%) |
| dvorak-p5 (control) | 15→15 | 673 | 673 | 0 |
| dvorak-p6 (control) | 15→15 | 2,611 | 2,611 | 0 |
| brahms-p1 | 21→14 | 3,434 | 1,798 | 1,636 (47.6%) |
| mahler-p2 | 38→21 | 1,117 | 866 | 251 (22.5%) |
| **sum (8 rows)** | | 19,403 | 13,192 | **6,211 (32.0%)** |

Two rows have no allocation in `works.json` and were handled separately:

- **brahms-p2**: scored against a condensed truth built from the row's own
  `systems_as_printed.system_1` map (same trimmer, same flags): 6,610 →
  5,935 = **floor 675** on the shipped prediction (rising to 1,328 once the
  prediction is stitched, §2c — floor and stitch interact).
- **mahler-p3**: no defensible allocation exists (the six horns split
  across two staves *crossing reference-part boundaries*, plus two one-line
  percussion staves the pipeline cannot see), so its floor is **bounded,
  not measured**: of its 1,674 `inspart` mass (25 unpaired truth parts of
  38), **1,366 comes from 22 parts that are rest-only in the window** —
  pure stacked-rest convention — and 308 from 3 sounding parts (tutti
  doublings). Floor ∈ **[1,366 … 1,674]**.

**Pooled floor: 6,211 + 675 + [1,366…1,674] = 8,252–8,560 edits =
28.4–29.4% of 29,082.** Read it as a *lower-bound-flavored* floor: the
condensed truth still stacks two whole rests where the page prints one and
keeps two voices where the page prints an a2 chord, so some floor-shaped
cost remains inside the "condensed" residue (visible in §3's exact-bucket).
And the honest caveat the arm itself prints: merging parts moves the
symmetric denominator too — the raw column stays the headline.

The floor also does second-order damage the arm removes: with 38 truth
parts against 17 pred staves on mahler-p2, musicdiff's part-sequence
alignment paired the pred trumpet staff with a *resting* truth part, so the
page's **only sounding part** (the trumpet fanfare) was inserted whole
(163) while the pred trumpet's bars were deleted (40+) — ~200 edits of
pure mispairing on a page read reasonably well.

### 2b. Actual segmentation faults — under ~300 edits of the pooled figure

- 984073-p2's missed m19|m20 barline: 11 excess `insbar` (168 vs 157) plus
  the merged cell's content charges — order 60–120 edits. Its high-res twin
  (575951-p2) reads the boundary and scores +22 edits *more* overall, so
  the miss is not what separates these rows.
- brahms-p1's spurious 8th bar (the cautionary 9/8): ~14 extra pred bars
  of near-empty content, a few tens of edits inside its `count` class.
- Everything else pooled segments exactly. (Erratum noted while verifying:
  WIDENED_BASELINE's footnote calls 575951-p2's 17+15 split wrong "against
  the true 16+16", but the plate's own printed numbers 17/34/49 in
  `works.json` give 17+15 bars; the classifier aligned 17+15 positionally
  and 182 bars come out exact, which a slid boundary would not allow. The
  footnote appears to be the record's one slip, not the pipeline's.)

**Bach (unpooled)** is the opposite world and is why it is unpooled: 6
"systems" (12+3+3+3+1+2 staves), 122 cells against 10 true bars, `delpart`
1,828/13 + `insbar` 2,352 — a page-structure failure on the choir-grouped
layout (3 Vni / 3 Vle / 3 Vc / Cb / Cembalo), exactly as VERIFICATION.md
predicted. Its 6,735 edits measure grouping, not recognition.

### 2c. The Brahms p2 stitch refusal — simulated, and worth almost nothing *today*

The page prints 14 then 13 staves (trumpets tacet-suppressed), so
`export._stitch_slots` refuses and ships 27 per-system parts of 7–8 bars
against 21 truth parts of 15. Simulated the stitch the exporter *would* do
(join system-2 staves to system-1 slots by the hand-read names in
`systems_as_printed`, fill the suppressed trumpet slot with measure rests):

| prediction | vs raw truth (21 parts) | vs condensed truth (14) |
|---|--:|--:|
| shipped (27 parts) | 6,610 | 5,935 |
| stitched (14 parts) | 6,586 | **5,258** |

**The stitch alone is worth 24 edits.** Musicdiff's sequence alignment was
already absorbing the unstitched parts about as cheaply as the stitched
form, because the *content* of every bar is so wrong that whole-bar charges
dominate either way (even fully aligned, the row keeps 2,802 `wrong note`
+ 1,607 whole-measure edits). Stitch + floor jointly explain 1,352 of
6,610; the remaining **5,258 is recognition** on the pool's densest scan.
The stitch lever's value therefore *grows* as recognition improves, and it
unlocks something scoring-side immediately: a `staves` map (hence note
recall and per-staff attribution) is impossible for multi-system rows while
parts stay per-system.

---

## 3. Opening `wrong note`: it is not rhythm, and it is not "wrong pitches" either

Per printed staff, per measure, truth (condensed via the `staves` map — the
multiset union of the mapped parts) was classified against the pred staff:
`exact` / `duration` (right pitches, wrong lengths) / `shift:k` (every
disagreeing pair off by the same k staff positions) / `accid` (right
positions, wrong accidentals) / `count` (sides disagree how many notes) /
`mixed`, with `count` retested under unison-collapse (per-pitch max across
condensed parts) to tag convention artifacts. This is
`attribute_wrong_notes.py`'s classification made multiset-based (reading
order across condensed parts is ambiguous — `scan_eval.note_recall`'s own
argument) with one alignment override for 984073-p2's merged bar. Then
**every dump_ops op was located to its (staff, bar) and charged to that
bar's class** — so costs inherit amplification honestly: a shifted bar
musicdiff refused to pair contributes its whole insbar+delbar.

Edits by cause, 7 mapped rows (18,286 of the pool's 29,082):

| row | count | shift | accid | duration | count-unison | mixed | exact-bucket | unlocated |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| beethoven-984073-p1 | 191 | 38 | 45 | 0 | 78 | 0 | 351 | 583 |
| beethoven-984073-p2 | 1,281 | 477 | 109 | 24 | 68 | 101 | 731 | 1,658 |
| beethoven-575951-p1 | 211 | 108 | 12 | 16 | 65 | 10 | 359 | 581 |
| beethoven-575951-p2 | 824 | 523 | 115 | 11 | 170 | 101 | 1,054 | 1,673 |
| dvorak-p5 | 238 | 116 | 0 | 156 | 0 | 0 | 111 | 52 |
| dvorak-p6 | 1,642 | 248 | 0 | 346 | 0 | 67 | 223 | 85 |
| brahms-p1 | 766 | 359 | 247 | 160 | 0 | 40 | 636 | 1,226 |
| **pooled** | **5,153** | **1,869** | **528** | **713** | **381** | **319** | **3,465** | **5,858** |

(`unlocated` = the part-level floor ops of §2a — 5,129 of it is exactly the
rows' `inspart` cost — plus ~729 of header-level clef/key/time charges.
Totals reconcile to each row's recorded edit count exactly.)

**What this says:**

- **`count` dominates: 5,153 edits — missing/extra notes, i.e. detection.**
  Cost splits nearly evenly between missing (2,630 — recall) and invented
  (2,676 — precision); note-*count* asymmetry runs the other way on the
  Beethoven rows (139 vs 47 notes on 984073-p2), where each missing note is
  cheap but a bar with several becomes a whole-bar charge.
- **`shift` (1,869) is clef damage, with signatures**: Viola read +6
  (alto-as-treble) on both 575951 rows and 984073-p2, −6/−5
  (alto-as-bass) on 984073-p1 — the *same plate* at two rasters guessing
  two different wrong clefs; Violino II −12 on both p2 rows is
  treble-read-as-bass (checked: truth `D4 D4 D4` eighths, pred
  `F2 F2 F2` — the exact −12 diatonic constant). Wrong-pitch-as-such is
  nearly absent (`mixed` 319): when a scan's pitches are wrong they are
  wrong *by a constant*, i.e. geometry, not perception.
- **`duration` is small (713) — the engraved-era "wrong note ≈ rhythm"
  prior does NOT transfer to scans** at the whole-pool level. The rhythm
  mass that does exist concentrates in Dvořák (§below).
- **`accid` (528) + the header `wrong keysig` category (261) ≈ 800 edits
  of key-signature damage**, concentrated in brahms-p1 (247+39) and the
  Beethoven p2s.
- **The exact-bucket (3,465) is overhead on correctly-read bars**, three
  known shapes: *rest-value edits* (566 of the 568 `headedit` cost sits on rests:
  pred writes a quarter/whole rest where the truth's quiet bar has a half
  rest — the `[R]4Bpa` vs `[R]2 fermata` family; across all note-level ops,
  rest elements cost 2,211 pooled-11); *voice-structure on condensed
  staves* (truth holds two voices where the pred read one line/chord —
  insbar+headedit on Corni/Fagotti/Oboi/Trombe staves — floor-adjacent);
  and *aligner slippage* around damaged neighbors (delbar runs on Violino
  I/II). None of it is independently winnable; the first two belong to the
  rest lever and the floor respectively.

**Dvořák p6 deep-dive (2,611 edits, 2,062 wrong note — the largest
recognition row).** Its staff/measure structure is perfect and it has *no
floor* (15→15). The truth is fine-grained: 32nd/64th figures (ql 0.125 /
0.0625) in every voice, timpani rolls as written-out 32nd/64th figures, winds in
parallel-32nd flourishes (m15: 22 truth notes in one Oboi bar). The pred
finds most *pitches* (per-staff totals: Flauti 39t/40p, Vn2 15t/23p) and
wrecks the *values*: quarters and halves where 32nds are printed (beam
levels under-counted at this density), invented notes on the string
tremolo bars (truth 2–3, pred 4–6 — including a literal `C7` whole note
which is the italic **"32" tremolo-subdivision digit read as a notehead**,
the marking `works.json` explicitly warned about), and missed rests
(rest-element cost 686, the pool's highest). This row is the small-value
rhythm + tremolo-notation cluster in one page.

---

## 4. Per-row attribution summary

| row | edits | floor | segmentation | recognition (dominant causes) |
|---|--:|--:|---|---|
| beethoven-984073-p1 | 1,286 | 416 | — | count 191, exact-overhead 351 (rest values 74), header ~70 |
| beethoven-984073-p2 | 4,449 | 1,480 | ~60–120 (m19\|m20) | count 1,281, shift 477 (Viola +6/+5), exact-overhead 731 |
| beethoven-575951-p1 | 1,362 | 470 | — | count 211, shift 108 (Viola +6), exact-overhead 359 |
| beethoven-575951-p2 | 4,471 | 1,958 | — | count 824, shift 523 (Viola +6, Vn2 −12), exact-overhead 1,054 |
| dvorak-p5 | 673 | 0 | — | count 238 (invented>missing), duration 156, shift 116 (Vc −4/−5) |
| dvorak-p6 | 2,611 | 0 | — | count 1,642 + duration 346: 32nd beams, tremolo digit, rests 686 |
| brahms-p1 | 3,434 | 1,636 | ~tens (spurious 9/8 bar) | count 766, shift 359, **accid 247**, duration 160 |
| brahms-p2 | 6,610 | 675 (→1,328 stitched) | stitch 24 (§2c) | residue 5,258 aligned: wrong note 2,802 + amplified bars |
| mahler-p2 | 1,117 | 251 | — | trumpet mispairing ~200 (floor 2nd-order), keysig 47, direction 90, rest values 50 |
| mahler-p3 | 3,069 | 1,366–1,674 (bounded) | — | amplified tutti misreads (delbar 556 on paired parts), notes 573 |
| *bach (unpooled)* | *6,735* | *n/a* | *the row IS segmentation: 6 systems, 122 cells/10 bars* | *choir-grouped layout stress* |

Pooled reconciliation: floor 8,252–8,560 (28.4–29.4%) + segmentation <300
(~1%) + recognition ≈ 20,200–20,500 (69–70%), of which the located causes
on mapped rows split per §3 and the three unmapped rows contribute
~5,258 (brahms-p2) + ~850 (mahler-p2) + ~1,300–1,700 (mahler-p3).

Also worth stating because the symmetry trap cannot flatter it: exact-pitch
note recall over the 7 mapped rows is **0.693 / precision 0.775**
(1,610/2,323 matched) — the graft's recognition headroom in one number.

---

## 5. Causes → levers

A same-day cross-check against the tree (`git log --all`, 2026-09-04
evening) found three parallel sessions whose results change lever statuses;
they are folded in below and marked ⧉ (on unmerged branches).

| cause (pooled edits at stake) | rows | current lever, with its record | status |
|---|---|---|---|
| Detection recall/precision on dense scans — `count` 5,153 mapped + brahms-p2's aligned residue ~4,400 + mahler-p3 share (total stake ~8–10k, incl. amplification) | all, worst beethoven-p2s, brahms-p2, dvorak-p6 | The head-surgery candidate (`merge_class_head` shift-0.9 graft) **IS the production checkpoint this baseline measures** — its value is already banked. Beyond it the training side is now a wall of measured negatives: fine-tunes (rounds 3–4), method knobs (round 5, 11 arms), ⧉ DSv2 rehearsal (round 6 — fails all three axes, "closes the training-side lever"), ⧉ per-class specialists (round 6 — rows compose bit-exactly, but every specialist collapses its own class) | **largest cause; NO open owned lever** — genuinely open research |
| Rest recognition & values — 2,211 note-op edits on rest elements (11-row) + 566 rest-`headedit` inside exact bars + quiet-bar whole-bar charges (stake ~2.5–3k) | all; worst dvorak-p6 (686), beethoven p2s | Same wall as above (rests are among the deleted classes the graft re-floors); completion-pass labels exist (NEXT_ITERATION); rest hole known 1,637/2,671 emitted, value accuracy 0.722 OOS | same open-research status; "nobody's business" no longer — it is priced |
| Condensation floor — 8,252–8,560 | all but dvořák | Not a recognition lever. **A protocol decision**: report the condensed column beside raw (machinery exists — `condensation_arm.py`; 8 of 10 allocations recorded, brahms-p2's derivable from `systems_as_printed`, mahler-p3 needs a hand read it may never defensibly get) — or keep raw and quote the floor beside it | decision open (Sean) |
| Clef on string staves — shift 1,869 mapped + unmapped share ≈ 2.3–2.7k | beethoven all 4, dvorak-p5, brahms-p1, brahms-p2 | `OMR_CLEF_WEIGHTS` specialist (off by default, helps some orchestral scans); contextual `slot_continuity` (on, insufficient here); dossier seeding (**excluded from this benchmark by design** — truth leakage — but valid in production) | partial owners; nothing shipped moves this benchmark |
| Small-value rhythm: 32nd beam levels, rolls, measured tremolo — dvorak duration 502 + the duration-wrong inside its `count` 1,642 + brahms durX (stake ~1.5–2k) | dvorak-p6/p5, brahms-p1 | Beam-level CV fixes have a paying record (stem cap, label-mask bars — CLAUDE.md "Durations" §§); **the tremolo-digit false note and measured-tremolo convention have NO owner** (`tuplet`-style reader absent; the "32" digit is not in any gate) | partial; tremolo unowned |
| Key signatures on scans — accid 528 + `wrong keysig` 261 ≈ 800 | brahms-p1, beethoven p2s, mahler | Template reader shipped 2026-08-31 (7/12 on beet5-p1, 0 wrong) — this is the residual after it | owned, residual |
| Stitch across unequal systems — 24 today; unlocks staves maps + grows with recognition | brahms-p2 (and every future multi-system scan row) | None: `_stitch_slots` refuses by design; the fix is name/label-anchored pairing (margin sweep already recorded which staff is suppressed) | no owner |
| Choir-grouped system layout — bach's 6,735 (unpooled); re-admission gate ≈ reading ~10 measures | bach | ⧉ **Owned as of today**: `OMR_CHOIR_GROUPING` (cues B+C, default OFF, branch `claude/bach-choir-grouping`) measured on the Bach row: 6→2 systems, 122→11 cells (true 10), 0.9241→0.8152 / −499 edits, structure charges −2,540; flag-OFF arm byte-identical to this baseline's fixture | owned on branch; crosses the re-admission bar |
| Tie hole 385 of 805 remaining | beethoven, brahms, dvorak | Graft's tie recovery (293→420) — but tie edits are cheap where notes pair (`wrong tie` 25 pooled): remaining value is mostly *inside* duration/count via long-note values | owned, low direct value |
| Direction/dynamic/timesig residuals — 264 / 222 / 202 | spread; mahler-p2 direction 90, dvorak-p6 timesig 38 | Direction reader ON in this pool (this is its residual); C/¢ readers shipped; dynamics = detection | owned, residual |

---

## 6. The ranked lever table

Ranked by estimated *recoverable* pooled edits (not stake), honoring
amplification: fixing a bar's cause also removes its whole-bar charge, so
located-cost is the right price; ranges are stated where attribution is
bounded rather than measured.

| # | lever | rows touched | est. edit value (10-row pool) | owns it today |
|--:|---|---|---|---|
| 1 | **Scan detection recall/precision incl. rests** — the pool's largest cause, and after rounds 4–6 (fine-tune / method knobs / rehearsal / specialists, all measured negatives) it has **no open owned route**; what exists is banked (the shipped graft) plus composition machinery (specialist rows transplant bit-exactly) waiting for any training recipe that stops collapsing its own class | all 10; worst 4 rows carry ~80% | **~4,000–7,000** of the ~8–10k count+rest stake if a route is found (even half the count mass is the pool's largest single move) | **NOBODY** — open research; do not re-run the refuted routes |
| 2 | **Condensation-floor protocol decision** — publish the condensed column beside raw (or a floor-quoted raw) | 8 of 10 measurable now | **8,252–8,560 reattributed** (28–29% of pool) — changes meaning, not recognition; stops the floor masquerading as error in every future comparison | decision open — Sean |
| 3 | **Clef on string staves** — constant-offset shifts (±6 alto↔treble/bass, ±12 treble↔bass) | 7 rows | **~1,900–2,700** | partial (specialist weights off; slot-continuity on; dossier excluded by design) — no shipped lever moves it here |
| 4 | **Small-value rhythm + tremolo notation** — 32nd beam levels at density; the "32" digit; measured-tremolo bars | dvorak both, brahms-p1 | **~1,200–2,000** | beam CV owned (record of paying); tremolo family UNOWNED |
| 5 | **Key signatures on scans** — residual after template reader | brahms-p1, beethoven p2s, mahler | **~600–800** | owned (residual) |
| 6 | **Stitch unequal systems by staff identity** | brahms-p2 now; every future multi-system row | **24 now** — but unlocks staves maps/note-recall for multi-system rows and appreciates as #1 lands | no owner; cheap |
| 7 | **Choir-grouped layout grouping** | bach only (unpooled) | 0 pooled today; ⧉ measured −499 edits / 122→11 cells on the stress row — the re-admission gate is crossed on its branch | ⧉ owned on branch (`OMR_CHOIR_GROUPING`, default OFF), pending merge + Sean's pool call |

**Reading order matters**: #2 is not code and can land this week; #3 is the
cheapest real recognition win because it is geometry (a constant-offset
staff is one decision per staff, not thousands of noteheads); #1 is the only
stake in the thousands of *recognition* edits and currently has **no owner
at all** — the honest headline of this forensics. #4's tremolo half and #6
are the other named causes with no owner. (The tilt fix, for completeness:
its cell-level signature — ±1-step shifts — is a minor slice of the shift
class here, consistent with the recorded finding that this benchmark cannot
price it; a widened-pool pricing is in flight on `claude/tilt-pricing-widened`.)

---

## 7. Reproduction

All inputs read-only from
`/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/scan-rebaseline/benchmarks/omr-scan-e2e-2026-09/`
(fixtures + `results-widened-graft.json`); works.json read at `0487be1f`.
Worktree setup as in WIDENED_BASELINE (venv symlinks + `OMRNED_PYTHON`).

```bash
# op-level dumps, one per row (pred first — direction is asserted in-tool)
.venv-omrned/bin/python benchmarks/omr-ned-2026-08/dump_ops.py \
    fixtures/<row>.omr.musicxml fixtures/<row>.truth.musicxml --json <out>

# condensation floor on the graft bytes (raw column re-verified vs results)
python3 benchmarks/omr-scan-e2e-2026-09/condensation_arm.py --out <out>
```

The positional classifier, the cost-by-cause join, and the Brahms p2 stitch
simulation are one-shot analysis scripts (this session's scratchpad:
`forensic_note_split.py`, `join_cost_by_cause.py`,
`stitch_sim_brahms_p2.py`); each prints reconciliations against the
recorded totals (row sums match `results-widened-graft.json` exactly;
join totals match each dump's `total_cost` exactly). The stitch simulation
notes for the record: 12 complex-duration elements split for re-export and
whole-measure rests filled into the suppressed trumpet slot — both
conservative against the stitch's measured value.
