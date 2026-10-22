# Handoff — 2026-09-08 evening: cloud session → local session

Written at the close of the cloud session `Ornaments export gap closure`
(started from iOS 06:53, teleported to the Mac Studio midday). **Everything
described here is committed and pushed to
`claude/ornaments-export-gap-pcfwfm` (head `be76d961`), PR #22, draft.**

⚠️ **Read `docs/handoff-2026-09-08-next-steps.md` first** — it defines Steps
1–5 and the standing rules. This file says what happened to Steps 1 and 2 and
what is open. **The tree outranks both**, and this session proved that twice.

---

## Why the session moved

The cloud container has **no weights, no fixtures, no `.venv-omrned`, no
`.venv-surya`, no `library/`**. It can read code, write fixes, run the unit
suite and reason over committed artefacts. It **cannot** run
`orchestral_eval`, `scan_eval`, OMR-NED, or the detector. Steps 2–4 all need
real transcriptions, so the work belongs where the data is.

---

## Step 1 — DONE

The `<ornaments>` export gap and the blindness in `export_coverage`. Full
record: `benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md`.

⚠️ **The headline inverted on contact with the evidence.** The Step-1 table in
the previous handoff listed `<ornaments>` (truth 12) and `tremolo` (truth 12)
as two gaps. They are ONE: `beethoven-sym3-mvt1` is the only one of the eleven
benchmark truths carrying ornaments and all 12 of its blocks hold nothing but
`<tremolo type="single">1</tremolo>`. The export is now wired, but the
detector produces **zero tremolo detections** (positive control: 34,115
detections walked over 11 transcriptions), so the engraved count stays 0. **It
is now a DETECTION problem**, filed in `KNOWN_GAPS`.

⚠️ The class IS taught — `tremolo*` appears as hand-labeled boxes with
`human_category: ornament` in `benchmarks/omr-labeling-*/verdicts/`, 46
occurrences over 8 files. *A class the label corpus carries and the checkpoint
does not produce* — which points at the fine-tune, not the labeling backlog.

## Step 2 — STARTED, first real shadow run executed

Command that produced it (Beethoven 5 / Litolff, `pdf_page_index` 1, 12
staves, 1 system — row `beethoven-sym5-mvt1-984073-p1`):

```
python3 -m tools.omr.transcribe "$PDF" --pages 1 --out /tmp/legacy.omr.json
OMR_SURYA_KEEP_ALIVE=0 python3 -m tools.omr.staged "$PDF" --pages 1 \
    --weights "$WEIGHTS" --against /tmp/legacy.omr.json --out /tmp/staged.json
```

**Result: agree 50, differ 4, new_abstention 20, new_decision 0,
legacy_only 0, over 74 rows.**

**JOIN CONTROL: `staff_ordinal` 12 of 12 agree.** The subject keys line up, so
the rest of the table means something. Read this before any other number.

### Two fixes landed as a result

1. **`4e089e00` — one gather, not two.** `--against` used to run
   prepare/gather/adjudicate a SECOND time and build the divergence table from
   that second log, so `result["adjudication"]` and `result["divergence"]`
   described different passes of a detector with documented jitter. It also
   doubled every `--against` run. `run_staged` now takes `legacy` and builds
   the table from the log it already has, **immediately after ADJUDICATE and
   before GROUPS/EVALUATE** — a consequence may restate a value, and a table
   built after EVALUATE would compare legacy against post-consequence values
   while calling them decisions.
2. **`be76d961` — compare like with like, or say you cannot.**
   `key_signature`: legacy writes `{'sharps':0,'flats':2,...}`, staged returns
   `int(fifths)`. A dict never equals an int, so **every decided key-signature
   row was DIFFER by construction, including perfect agreement.**
   `instrument`: legacy `{"name":...}` vs staged name+family+more — same
   defect, **latent**, found by asking what each adjudicator returns rather
   than by reading a table. Adds `NOT_COMPARABLE` as a counted first-class
   outcome. ⚠️ The adapter may only re-express a unit; it must never make two
   different readings look equal — a false DIFFER gets investigated, a false
   AGREE does not. `TestTheAdapterCannotManufactureAgreement` pins that.

### The finding, and the honest way to state it

All four `differ` rows are `key_signature`. Adjudicated against
`data/dossiers/beethoven-sym5-mvt1.json` joined through `works.json`'s
hand-verified `staves[i].parts`:

| staff | instrument | true | legacy | staged |
|---|---|--:|--:|--:|
| 2 | B♭ Clarinet | −1 | 0 ✗ | **−1 ✓** |
| 8 | Violin 2 | −3 | 0 ✗ | **−3 ✓** |
| 9 | Viola | −3 | 0 ✗ | −1 ✗ |
| 10 | Violoncello | −3 | −2 ✗ | **−3 ✓** |

⚠️ **Do NOT state this as "staged 3/4 vs legacy 0/4".** Only **4 of 12** staves
got a key from the staged path; **8 abstained**. Legacy emitted a value for all
twelve and is wrong on every one that can be checked. The honest form:
**staged decided 4, got 3 right, declined 8; legacy decided 12 and got at
least 4 wrong.** That is `NEW_ABSTENTION` being a feature that scores as a
loss, exactly as the design predicted.

### ANSWERED 2026-09-08 (local session) — it is a READER, not the alto table

**`detail.n_accidentals` is 1.** Only one flat was found, so this is the
detection-shortfall branch and the fit reported what it had; the alto slot
table is not implicated. Two staves that found three boxes read −3, and the
Clarinet found one box and is CORRECTLY −1 — the Viola behaves exactly like the
Clarinet. Its one box also sits at x 1161 against a system-wide accidental band
of 580–948, so it is likely not a flat at all.

Underneath it: **GATHER imports `locate_key_signature` and nothing else**, and
`key_signature_template` — measured at 11 of 12 on THIS page against the
locator's 2 of 12 — is referenced nowhere under `tools/omr/staged/`. The Viola
is one symptom of that, and the least informative one. Parked as **D20** in
`ASSUMPTIONS.md` with the measured restraint that constrains the fix.
Full reading: `benchmarks/omr-staged-shadow-2026-09/FINDINGS.md`.

<details><summary>The question as it was posed (kept — a park keeps its evidence)</summary>

#### OPEN — the Viola, and the one number that splits it

Sean's hypothesis was that the alto clef fired a wrong signal. **Falsified:
the clef read `alto` correctly.** And his correction is the right one — an
alto clef changes *where the accidentals are drawn*, not *how many*; Viola is
non-transposing, so C minor is −3 like everyone else. Correct clef, correct
slot table, still −1.

So the fit itself failed, and `detail.n_accidentals` on that verdict splits
the two candidates:

* **1** → only one flat was FOUND. A detection shortfall; the fit honestly
  reported what it had (`fit_key_signature` may not infer).
* **3** → all three found and mis-fitted. A real bug in the alto slot table.

They need different fixes. **This is the first thing to do on the new
session.**

⚠️ **The script that "showed" the basis was empty was WRONG, and it was the
coordinator's own.** It indexed rows on `'row_id'`; the serialised key is
`'id'`, so the index was empty, every lookup missed, and the walk returned
`Counter()` regardless of content. `a zero is a suspect` — and the corrected
version prints `len(by)` and `len(basis)` as positive controls. The
adjudicator declares `used=(row.id, clef.id)` and abstains `needs_clef`
without one, so the clef is certainly in the basis.

</details>

### What Step 2 still needs

1. **Six of fifteen wired decisions are INVISIBLE in the table.**
   `divergence()` iterates `legacy.items()`, so a staged decision with no
   legacy counterpart produces no row. `legacy.extract` covers 9 quantities
   (`system_staff_count`, `system_membership`, `staff_ordinal`, `clef`,
   `key_signature`, `instrument`, `slot_index`, `measure_partition`, `meter`);
   `staff_group`, `group_symbol`, `part_partition`, `glyph_owner`,
   `tuplet_ratio`, `duration` are absent. `LEGACY_ONLY` covers only the
   opposite direction. Extend `extract` or report them separately — do not
   leave them invisible.
2. **The GROUPS stage has never been exercised.** This row is `n_systems: 1`,
   so every `*_across_systems` group had exactly one witness by construction
   and the report says so itself: `checked_nothing` names four of six. **Run a
   multi-system page** — a Brahms 1 / Breitkopf row — before concluding
   anything about whether redundant groups earn their keep.
3. **Rank by staves touched**, each row carrying its `Verdict.basis` closure.
4. **Compare `clef` against TRUTH, not just against legacy.** `clef` shows 12
   decided and 0 differ, i.e. the two paths agree on all twelve. That is not
   evidence they are right — two paths sharing an upstream reader are ONE
   signal. Only the dossier can say. That is the ledger's job, not the
   divergence table's.

## The other sessions — audited 2026-09-08, nothing to merge

| branch | on origin | state |
|---|---|---|
| `claude/agitated-bassi-e3a0ab` (`Tp.` fix) | yes | **0 ahead of main**, 282 behind — merged |
| `claude/dynamics-letters-clef-approach-fba804` | yes | **0 ahead**, 473 behind — merged (PR #16) |
| `claude/compassionate-kilby-4a9f08` (LilyPond mid-staff key) | **NO** | never pushed — review-ready work may exist ONLY on the Mac |
| `claude/slot-group-mapping-2026-09` | **NO** | never pushed |

Open PRs #21, #14, #3, #1 touch **zero** files this branch changed.

⚠️ **First pass reported `agitated-bassi` as "634 ahead" with "no merge base"**
— both artefacts of a **shallow clone**, not facts. `git rev-parse
--is-shallow-repository` was `true`; after `--unshallow` the same branch reads
0 ahead. A surprising result is a suspect, not a finding.

⚠️ **CLAUDE.md contradicted itself and was corrected (`49247b6f`)**: it said
the `Tp.` defect was "diagnosed on `claude/agitated-bassi-e3a0ab` and not in
main" while the section above described the same fix as shipped.
`fixed-then-kept-open-in-prose`, second recorded instance. Worse than a stale
sentence — naming a branch as the place to go and get something is a work
order. The claim shape *"X is on branch B and not in main"* is mechanically
falsifiable: `git rev-list --count origin/main..origin/B` is 0 when false.

## TODO on the Mac, outside git

```
git branch -a | grep -E "compassionate-kilby|slot-group-mapping"
```
If those exist locally, **push them** — that work is one disk failure from
gone.

## What has NOT been measured anywhere

No `orchestral_eval`, no `scan_eval`, no OMR-NED on this branch at all. The
five items in FINDINGS §7 stand. The unit suite is green (2,974 passed, 64
skipped, 2 pre-existing `.venv-surya` failures) but **the 64 skips are the
point** — every fixture-gated test, including `TestTheRepositoryItself`, has
never run.
