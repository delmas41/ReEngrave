# Overnight pipeline audit — handoff, 2026-09-07

**Commissioned by Sean**: a full pipeline audit — information, decisions, and
measurement — then authority to turn analysis into fixes. Nine agents, five
merges. **Read §1 and §6; the rest is reference.**

⚠️ **Everything merged tonight is byte-identical to the exported MusicXML**, on
both families, proven by `diff` and not by argument. **No default changed. No
decision changed.** The pipeline reads exactly what it read yesterday; it now
writes down why.

---

## 1. The four things worth your attention

### 1a. Three neighbouring decisions, one fault, three levels of protection

Within one thirty-line span of `transcribe.py`, the clef, the key signature and
the meter are each overwritten **per cell with no confidence floor**. The
surviving-flip counts rank **inversely with the guard**:

| fact | guard | scan (193 staves) | engraved (224) |
|---|---|--:|--:|
| **clef** | 2-entry hand-listed allowlist, identity-gated, **OFF** | **11** | 0 |
| **key signature** | **none at all** | **7** | 0 |
| **meter** | cross-staff corroboration, **ON** | **0** | 0 |

The meter guard's own docstring describes the clef's defect almost verbatim.
**The pipeline has already met this bug, already built the repair, and applied
it to one of three facts that behave identically.**

⚠️ **The key-signature mechanism is exact**: when the slot fit abstains, the
reader falls back to *counting* markers, so one stray marker reads as one
accidental whatever the staff was in. **Five of the seven overturn a reading the
cross-page vote had already confirmed** — Mahler p2 s15 was kept as four sharps
with the recorded reason *"agrees with the system's 4 sharps"*, then destroyed to
**one sharp by a single detection at confidence 0.33**, with every note after
bar 6 spelled against it.

⚠️ And **the protection that exists is on the wrong cell**: the reader is
silenced on cell 0 *because the vote already ruled*, and left running on later
cells — where the argument is strictly stronger, because cell 0 looks at a
printed key signature and cell 11 looks at ink that resembles one.

**Not built tonight.** The clef arm is coupled to the held
`OMR_INSTRUMENT_CLEF_DEFAULT` decision, which is yours. ✅ **The key-signature
arm is NOT coupled to it** and is the cheaper first arm.

### 1b. A number that looked like a ceiling was a failure

Hairpins read at ~1% on scans and nobody could say whether the ink was
unreadable or the reader was broken. The hand-labeling corpus answers it,
because a human's box is an **independent** record of what ink a reader could
recover — which no truth MusicXML can be. Across 55 completion cells a person
drew **17 hairpins, 62 ties and 27 slurs**; on the same three pages the detector
made **10,523 detections and ZERO of either hairpin class**.

So the 1% is not a thin sample — it is **zero where the detector was otherwise
productive**. Bar-level ceiling **0.80** (n=5): we run at about **one part in
eighty** of what a reader sees. ⚠️ **Breitkopf & Härtel, Brahms 1** — one
edition, and that must be quoted with the number every time.

### 1c. Roughly 40–50% of the scan "error" is the metric billing a printing convention

Measured, not estimated: scoring the page-normalised truth **as the prediction**
on 15 rows of the canonical arm, three controls passing (the identity rows score
**exactly 0 edits**). Pooled **0.8417 → 20.09% of achievable**, reported as a
ladder with only the **conservative** rung used, because a larger floor flatters
every score above it.

### 1d. Human review cost — your stated purpose — is measurable, and its number is a trap

**97.07% of achievable** (46 of 1,571 records). ⚠️⚠️ **It scores staff NAMING
only.** The reviewer's real load — note-level diffs — **has no harness at all**.
**97 printed beside a scan 20 is the most misleading pairing this board can
produce**, and the registry now enforces a caption that cannot be dropped: *if
the renderer can drop it, the schema is wrong.*

---

## 2. Merged to main, in order

| commit | what |
|---|---|
| `77e46b5f` | `Barline` carries the evidence that admitted it — vote count, connectivity, span score, which of five prongs fired, open-score verdict. Plus a per-reason deletion census over 26 previously silent `_bump` sites. |
| `29cfbddc` | The audit's own findings: information lifecycle · decision types · measurement critique · metric registry · technology ledger · verification. |
| `3c6691b8` | Six sites where a computed number was destroyed in the expression that refused it now record: the clef locator's trace (a recorder already written that no call site passed), the clef argmax contest with winner/runner-up/margin **and the blocked readers**, `propose_clef`'s `fits` at all five exits, band distances, the key-signature majority **and its tally**, the meter runner-up including abstaining systems. |
| `3b337030` | A measure cell records the pad it was cut with — per cell, per side, because the pad **grows**. |
| `2d4bcc03` | The CLI never let `OMR_DIRECTION_TEXT` be heard (one argparse default), plus a runaway guard on the OCR reader where its sibling gate already was. |

**Awaiting review or a number:** the serialisation of the barline evidence and
the cell pad (in review); the beam-bar fix (`scan_eval` A/B running); the
% of achievable renderer (**rejected**, being rebuilt); probe hygiene (approved,
must be re-applied on current main — see §5).

---

## 3. Decisions — ANSWERED by Sean, 2026-09-07 morning

| decision | Sean's call | state |
|---|---|---|
| **`/uploads` served without auth** | **Leave it alone** — treated as intentional | closed, no change made |
| **Key-signature corroboration guard** | **Build it, default OFF** | ✅ built, `claude/fix-keysig-corroboration`, in review |
| **`OMR_INSTRUMENT_CLEF_DEFAULT`** | **Keep held; decouple the clef work from it** | clef guard to be scoped without instrument names |

⚠️ **The decoupling has evidence behind it**: 29 of 29 unresolved non-treble scan
staves print **no margin label at all**, so a name-based clef repair cannot reach
that population regardless of the flag. The clef guard must therefore rest on
something other than identity — the same "corroborate the EVENT, not the VALUE"
shape the key-signature guard found is the obvious candidate and is untested there.

### Superseded — the original text of this section



1. ⚠️ **`/uploads` is served over HTTP with no authentication**, and
   `local_omr.py` writes the entire result JSON there. That is how an
   11,708-character hallucinated OCR string became HTTP-reachable. Route-level
   auth does not cover a `StaticFiles` mount. It may well be intentional —
   snippet images are served that way by design. **Independent of tonight's
   fixes and not closed by them.**
2. **The key-signature guard** (§1a) — cheap, uncoupled, and the corpus can
   measure its benefit but **not its cost**, because there are zero real
   mid-staff key changes in it.
3. **`OMR_INSTRUMENT_CLEF_DEFAULT`** stays held; the clef arm waits on it.

---

## 4. What NOT to do — refuted tonight, with reasons

- ⚠️ **Do not re-open the arc `drop` arm.** It scores **2,388 against the
  shipped 2,371 — worse**, and is better only *arm-for-arm* against the
  same-margin move arm. It was refused on a **count control**: slurs 199 → 183
  against a truth of 241, moving *away* from it.
- ⚠️ **Do not put a confidence floor on ledger rungs.** A 0.40 floor destroys
  **42–58% of complete ladders**; the low-confidence rungs are load-bearing, and
  the impossible in-band rungs contribute **zero** matches anyway.
- ⚠️ **`staff`-class detections cannot be compared against staff detection.**
  `detect_staves` runs **before** the detector, so there is no moment at which
  both answers exist. Not an A/B — a new inference regime.
- ⚠️ **The ScoreAug/Augraphy refutation is not reproducible.** Its probe JSONs
  were scratch and never committed. Probably right; **one bad memory away from
  being re-tried.**

---

## 5. Method lessons, which outlived their findings

- ⚠️ **A survivor-count instrument is blind to anything a later pass repairs.**
  An audit reading the final page dict measures **what survived, not what
  happened** — and the two diverge exactly where a correction layer is doing its
  job. A probe found 0 clef flips on 224 engraved staves; the argmax flips one
  at confidence 0.935 and the dossier override puts it back.
- ⚠️ **"The only", "never", "nobody", "zero" are the highest-risk sentences
  here.** Two independent verification passes, on independent material, each
  found ~75% of their errors in negatives and universals. Prefer *n of m*.
- ⚠️ **A null gets the same sampling scrutiny as a positive.** A real defect was
  declared UNREACHABLE from a census of two pages that were **both the cleanest
  prints in the gate**. Re-run wider: 51 multi-bar components, 4 changing a
  duration. **The sample was unlucky in its EDITION, not its page depth.**
- ⚠️ **A probe that finds nothing must FAIL.** Several printed clean all-zero
  tables at **exit 0** from the wrong tree — the stale-tree incident installed
  into the audit's own instruments. One caused the false retraction above.
- ⚠️ **Fixture hygiene does not protect against the wrong field.** One probe's
  globs were right, its files were read, and it asked for a key that does not
  exist — a tidy table at exit 0. That needs a **schema assertion at the point
  of read**, which is a different guard.
- ⚠️ **A canonical hash must mask everything the writer takes from its
  environment.** A committed control passed 15/15 one day and **0/15 the next**
  on unchanged code: it hashes `<encoding-date>`. *A control that cries wolf on
  a schedule is worse than none, because it gets believed once and then
  disabled.*
- ⚠️ **Corroboration is not evidence when the two views share a cause.** Two
  agents reported the same 436 off one substrate; a probe's "independent
  corroboration" was a cause and its own effect agreeing.
- ⚠️ **An instrument that is off is not a record.** `OMR_CONTEST_DUMP` and
  `locate_clef(trace=)` are complete recorders that record nothing. **New
  records may not be flag-gated to buy back their bytes** — project at write
  time instead.
- **Six agents caught a vacuous test of their own**, each by a mutation somebody
  bothered to run: a renamed `def`, a too-clean fixture, a swap below the line
  that records it, a whole record whose deletion left 44 tests green.

---

## 6. If you read one more thing

**`docs/architecture-decision-map.md`** — ~176 decision points with a BLIND TO
column — and **`benchmarks/omr-pipeline-audit-2026-09/`**, which holds the
information lifecycle, the decision-type analysis with reversibility, the
measurement critique, the metric registry (55 rows, 39 scoreable, **17 marked
unscoreable rather than given a flattering number**), the technology ledger
(*why* each target is read the way it is, and whether each losing alternative is
REFUTED / UNTRIED / UNREACHABLE), and the verification pass over all of it.

**The scale**: everything is now **% of achievable, higher is better,
everywhere.** Engraved **88.8%** (Audiveris **87.5%** on the same fixtures and
scorer — a head-to-head, never a delta). Scans **20.1%** against a measured
floor.

---

# Addendum — the morning session, 2026-09-07

⚠️ **§1's programme recommendation is SUPERSEDED. Read this before acting on it.**

## A1. What moves the numbers — the answer changed twice, and both changes were measured

The coordinator recommended a **hollow-notehead labeling campaign** on the grounds
that `wrong note` (22,165 edits, 29.6% of the scan pool) is duration-driven. Sean
challenged it: *could it be pitch, from the system issues this audit just found?*

**Neither was right, and the campaign would have backfired.**

| claim | verdict |
|---|---|
| hollow noteheads are the #1 scan weakness | ⚠️ **an EDITION effect running BOTH ways** — pooled 0.932 of truth, but Mahler **0.53** and one Beethoven raster **0.62** under-detect while Brahms **3.11** and Dvořák **3.85** OVER-detect. **A campaign to detect more would help two editions and harm three.** |
| `wrong note` is duration-driven | **not supported** — 1.77:1, or 1.23:1 wide |
| `wrong note` is pitch-driven (Sean) | **substantially strengthened** — pitch spelling is 3,714–5,350 edits, not the 555 first reported |
| clef flips drive it | **≤978 edits, 1.3%** — and `wrong note` *rises* when clef spelling is neutralised |
| key-signature flips drive it | **structurally cannot enter** — a key flip changes `alter`, the scorer annotates by step+octave |

⚠️ **The two Beethoven rows are the same music on the same Litolff plate — 509
hollow notes in both truths — and score 0.62 and 0.95. The variable is the raster.**
CLAUDE.md's hollow-notehead forensics came from the worst of the six pages.

**Where the evidence now points:** clef ≤978, key impossible, ownership ≤~1,100 —
**yet pitch spelling is 3,714–5,350. So most of the pitch mass is none of the three.**
Under voice-aware alignment a note pairs by voice and chord position, so a note whose
**staff position** was misread now pairs and reports a pitch-name edit. That points at
the **pitch-resolution grid** — the fractional residual computed and discarded, the gap
spread never formed, the tilt `OMR_CELL_LINE_TRACE` exists for.

⚠️ **That is a POINTER, NOT A MEASUREMENT.** Three causes are excluded by measurement;
the grid hypothesis is **not measured**. Nobody should commit a week to it until
someone does — which is the same mistake the hollow-notehead recommendation was.

## A2. ⚠️ 29% of the scan gate is the metric's own configuration

Same predictions, same truths, different musicdiff detail level: pooled **74,956 →
53,097**, `entire measure` −76%, `wrong note` −54%. **Nothing improved** — only the
accounting changed. Voice-aware scoring is genuinely **better**, not merely different:
musicdiff's own source says that under the current setting *"chords are IGNORED"*,
notes are paired **by pitch**, and voices are ignored completely.

**Not adopted, and stamped rather than subtracted** (registry v0.6.0): the detail level
now rides inside every OMR-NED row's `era_key` and both comparability keys. ⚠️ It is
explicitly **NOT a ceiling** — a ceiling bounds what is *achievable*, this bounds what
is *attributable*, and filing it as a ceiling would license **subtracting** it.

**Recommendation to Sean, not yet acted on:** run one era reporting **both columns**,
detail level inside the era key so they cannot be differenced. One extra scoring pass;
nothing re-transcribes.

## A3. `OMR_SLOT_STITCH` — Sean's hypothesis confirmed, and the recorded reason was FALSE

**−240 edits raw over 20 rows; −2,278 normalised over 19; `entire staff` 2,238 → 0 on
the reached rows.** All three reached rows improve on the **raw, unreshaped** truth
(−17, −9, −214), so the result does **not** rest on a truth we reshaped.

⚠️ **CLAUDE.md said the flag is off because "it still costs OMR-NED." The FINDINGS it
cites records an IMPROVEMENT of −216 edits** — and carries a bold warning that the
named bucket doubling *"is not a contradiction, it is what the bucket measures."* The
summary **took the one bucket that warning exists to explain is not the cost, and
reported it as the cost.** Corrected in this session.

**Not defaulted ON**: n=3 rows is **n=2 distinct pages of the same structural shape**.
The blocker is named and costed — one multi-system scanned page from a different work
and publisher where the ordinal join refuses; **the current gate cannot supply one.**

## A4. Reach is bounded by the identity layer — reached twice, independently

Slot stitch abstains on **a single** staff lacking a slot index, so its ceiling is set
by **contextual slot completeness, not by the ordinal join's refusal rate**. And the
`wrong note` decomposition put most of the bucket in non-pairing, whose largest
component is `entire staff` at 17,520 — **part correspondence**. **Structure and
identity gate this pipeline; detection work is downstream of them.**

## A5. Landed this session

| | |
|---|---|
| `OMR_KEYSIG_CORROBORATION` | default OFF, Sean-approved. 7/7 spurious flips stop. Witness corroborates **the event, not the value** — a key change is printed at one bar on every staff; the value differs per transposition, the bar does not. |
| CV hairpin reader wired | default OFF. **56 hairpins recovered where the detector finds zero**, 2 invented. Reads lines-**intact**, deliberately. |
| Registry v0.6.0 → v0.7.0 | detail level in the era key; `ceiling.control` for flag-conditional ceilings |

⚠️ **CORRECTED — the first version of this line was wrong and is withdrawn.** The
page-fidelity floor (**0.2123**) is **NOT** flag-conditional: it scores derived truth
against raw truth, so **no prediction of ours appears in it** and no pipeline flag can
move it.

**The real discriminator is not "measured under the default" — it is
`reads_our_output`.** Two *other* structural ceilings are conditional, both estimated as
`min(ours, audiveris)`: `ceiling_measured_15rows` (0.1340) and
`ceiling_corroborated_subset` (0.1520).

⚠️ **And the hazard runs the flattering way.** Flipping `OMR_SLOT_STITCH` moves our raw
`entire staff` charge **87 → 1,062** on two rows, and a larger floor **RAISES** every
`% of achievable` above it. **A ceiling that reads our own output can be improved by
making our output worse.** Now machine-readable: `ceiling.measured_under` on all 21
measured ceilings, 19 declaring `reads_our_output: false` with the reason, 2 declaring
`true` and naming their flags, with the re-measure stop condition in the row.

## A6. The methodological finding of the morning

Four figures needed correcting, and the shape was identical every time:

> **I validated the computation and not the thing being computed on.** 11.85:1
> reproduced perfectly from the contaminated file every time it was run —
> **exact reproducibility is not evidence that a number measures what its label says.**

And a precondition worth keeping, from the hairpin work: **an edition effect is
attributable to the edition only once its rows are shown to agree in DIRECTION** —
otherwise it is a row effect wearing the edition's name. One Peters page under-emits
hairpins by 15 while another invents 2; an edition aggregate conceals that entirely.
