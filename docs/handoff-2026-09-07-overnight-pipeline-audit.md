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
