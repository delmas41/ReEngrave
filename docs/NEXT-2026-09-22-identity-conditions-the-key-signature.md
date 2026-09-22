# NEXT — gather WHICH PRINTING this is, and let the key signature read it

> ## ✅ DONE 2026-09-22 (evening) — AND TWO OF THIS BRIEF'S CLAIMS ARE REFUTED
>
> Built, measured and committed. Read
> [benchmarks/omr-document-identity-2026-09/FINDINGS.md](../benchmarks/omr-document-identity-2026-09/FINDINGS.md)
> and CLAUDE.md's *WHICH PRINTING THIS IS* section; **this file is now
> history** and two of its statements are wrong.
>
> 1. ⚠️⚠️ **§3's warning that `image_type` is "ALMOST CERTAINLY WRONG ABOUT
>    THE ENGRAVED POPULATION" IS FALSE, and Sean's own guess — *"maybe they
>    are all scans because they came from IMSLP"* — is RIGHT.** Measured over
>    all 289 committed editions: the label and the measurement agree **279 of
>    279 wherever the label exists** (272/272 `Normal Scan` scanned, 7/7
>    `Typeset` engraved). **Its failing is ABSENCE, not error.** The reason to
>    key on the measurement is §2's structural one instead, and it is
>    stronger: the engraved fixture is a RENDER in no catalog, so the catalog
>    row ABSTAINS on exactly the input the rule is proven on.
> 2. ⚠️ **§2's table of "what already exists" missed one: `Q.INPUT_DOMAIN`
>    was ALREADY DECLARED and CLAIM-classified**, produced by nothing and
>    reported a GHOST by `reach --check` every run. This session declared it a
>    second time before the derived checks caught the duplicate. *"Roughly
>    half of it already exists"* was true of more than the table named — `grep
>    Q\.` the vocabulary, not just `ls benchmarks/`.
>
> **Result**: key signature right **26 → 47** of 50, wrong **24 → 3**; bars
> exact **313 → 322 of 360**, 4 parts better and 0 worse. It reproduces §1's
> own table from a fresh gather and a different scorer.
> `OMR_DOCUMENT_IDENTITY` is now **default ON**; the consumer is
> `OMR_ENGRAVED_KEYSIG`, **default OFF**, and **the flip is Sean's**.
>
> ⚠️ §6's *"pricing needs two full re-gathers"* was right about the blindness
> and wrong about the cost: an engraved 3-page gather took **4 minutes** and a
> 1-page scan gather about **2**, so both arms were re-gathered rather than
> injected.


**Sean, 2026-09-22:** *"if a page is engraved or a scan along with the publisher
info and year — whatever we have — should be gathered in the first stage — then
we need to make sure that the key signature is determined based on that info."*

**This is a work order for a NEW SESSION.** It is written after checking the
tree, because **roughly half of it already exists and is switched off**, and a
session that starts by building it would rebuild a rung that shipped on
2026-09-17.

⚠️ **READ FIRST:** [docs/ask-first-conventions.md](ask-first-conventions.md),
then [docs/handoff-2026-09-22-four-lanes-and-three-refutations.md](handoff-2026-09-22-four-lanes-and-three-refutations.md)
§1, which is the measurement this job acts on.

---

## 1. WHY — the measurement that makes this Sean's call rather than a guess

`adjudicate_key_signature` reads two readers and **prefers the one that is
wrong**. On an ENGRAVED render of Beethoven 5 mvt 1, over 50 decided
staff-systems:

| reason | right | wrong |
|---|--:|--:|
| **`fitted_by_template`** (`Q.KEYSIG_TEMPLATE_FIT`) | **20** | **0** |
| **`fitted`** (the locator's slot fit) | **6** | **24** |

Its docstring gives the reason for that precedence: *"the locator loses
accidentals to broken ink, the template can match spurious ink and over-count
— so the one that cannot invent a glyph goes first."* **The ink on that page is
a vector render. The locator loses them anyway, 24 times in 30. The template
over-counts nowhere.** **91% of all note errors on 20 bars of 18 parts are this
one fault.**

**And the cause is now measured**
([benchmarks/omr-keysig-erasure-2026-09/FINDINGS.md](../benchmarks/omr-keysig-erasure-2026-09/FINDINGS.md)):
`erase_staff_lines` shaves 54–63% off each flat's height, so two of every three
fall under `key_signature_locator.min_height_spaces = 1.10`. Two independent
renderers agree to **0.03 staff spaces**.

⚠️⚠️ **AND THE SAME ERASURE *HELPS* ON A SCAN** — on the Litolff plate it takes
accidental-sized clusters **5 → 11**, because there the staff lines merge
glyphs and erasing separates them. **That is why the erasure exists, and why
the current precedence was defensible when it was priced on scans.**

> **So the fault is DOMAIN-SPECIFIC, and that is exactly why the fix has to
> start by knowing the domain. Sean's instruction is the right shape.**

## 2. WHAT ALREADY EXISTS — check this before writing a line

| piece | state |
|---|---|
| `gather_document_identity` (`gather.py:3325`), wired at `:3503` | **BUILT**, behind `OMR_DOCUMENT_IDENTITY`, **default OFF**, **producer-only — nothing reads it** |
| it files publisher / `work_id` / composer / `image_type` / `imslp_id` / `edition_path` | **BUILT**, `tier: "catalog"`, `source_kind: "catalog"` |
| a PDF the catalog does not hold | **ABSTAINS** `not_in_catalog` — it never defaults to *unknown publisher* |
| `input_domain._classify_page` — the MEASURED engraved-vs-scan test | **BUILT and measured** (`OMR_WEIGHT_ROUTING`'s own classifier), **imported NOWHERE under `staged/`** |

**So the job is NOT "build a gatherer."** It is: **add what is missing, turn it
on, and give it a consumer.**

## 3. WHAT IS MISSING — measured against the committed catalog (289 editions)

| field | present on | note |
|---|--:|---|
| `publisher` | 285 / 289 | already filed |
| **`publisher_year`** | **195 / 289** | ⚠️ **NOT FILED — Sean asked for the year by name** (Litolff = `'1870'`) |
| **`plate`** | **177 / 289** | not filed; a plate number identifies a printing more sharply than a year |
| `image_type` | 279 / 289 | filed — **but see the warning below** |
| **`has_text_layer`** | **289 / 289** | not filed; the only field present on every edition |

⚠️⚠️ **`image_type` IS IMSLP'S LABEL, NOT A MEASUREMENT, AND IT IS ALMOST
CERTAINLY WRONG ABOUT THE ENGRAVED POPULATION.** Its values across 289
editions are **`Normal Scan` 272, `None` 10, `Typeset` 7.** Seven. CLAUDE.md
already warns *"`image_type: 'Normal Scan'` is IMSLP's own label, not a
measurement."* **A key-signature decision keyed on it would be keyed on a
crowd-sourced string.**

> **THE ENGRAVED/SCAN FACT MUST BE MEASURED, and the measurement already
> exists**: `input_domain._classify_page` separates a scanned page (one
> full-page raster, coverage ≥ 0.95 on every scan measured) from an engraved
> one (428–2058 vector drawings), **with the gap EMPTY over 147 probed pages**,
> and it **abstains on doubt**. Lane A independently re-ran it: the engraved
> fixture classified **engraved on all 3 pages**, 1,188–1,655 drawings,
> raster coverage **0.000**.

⚠️ **KEEP THE TWO APART ON THE RECORD.** The measured verdict and IMSLP's label
are **two witnesses**, and where they disagree that is a fact worth having —
the same discipline `Q.INK` uses for `ink_detector_coverage`. **Do not
overwrite one with the other.**

## 4. THE DOCTRINE QUESTION — answer it before coding

`source_kind` decides what a measurement path may read. The catalog tier is
`"catalog"` (independent of the truth MusicXML). **What is
`_classify_page`'s verdict?** It reads the PDF's own internal structure — vector
drawings against a raster — so it is **not** a reading of the music and does
**not** fall silent when the print is bad, which is the property
`source_kind: "page"` exists to warn about. ⚠️ **It is arguably a THIRD kind,
and this file does not decide it.** Name it deliberately; an open vocabulary
makes a typo indistinguishable from an absent reading.

## 5. THE SHAPE OF THE CONSUMER — and the one-sided rule that makes it safe

**Do NOT flip the precedence globally.** The template's 20/20 is **engraved
only**; on a scan the erasure works FOR the locator and the template's
over-counting risk is exactly what the refusal was written about, **and that
side is not measured for accuracy.**

**The safe shape is one-sided:**

> **Prefer the template ONLY where the document is PROVED engraved. Everywhere
> else — scan, or the classifier abstaining, or no identity row at all — leave
> the precedence exactly as it ships.**

That fails toward the shipped behaviour on every input the new fact cannot
speak about, which is this repo's standing rule for a new gate.

⚠️ **A second shape exists and is NOT ruled out**: leave the precedence alone
and lower `min_height_spaces` for engraved input instead, since the mechanism
is measured (flats at 0.94–1.22 after erasure against a 1.10 floor). **Neither
is measured. Measure REACH first for both.**

## 6. HOW TO MEASURE IT — the arms, in order

1. **REACH before accuracy.** How many staff-systems does the new rule reach on
   (a) the engraved fixture and (b) each shared scan record? **Declare the arm
   DEAD at zero reach rather than reporting a clean zero.**
2. **The engraved arm has TRUTH for free** — `benchmarks/omr-staged-engraved-2026-09/`
   holds the fixture, its MusicXML and four staged records, and
   `locator_vs_template.py` already prints the per-staff table this job is
   scored on. **Reuse it; do not write a second scorer.**
3. **The scan arm must show the file does not move.** Flag-off must be
   **byte-identical**, with a positive control proving the comparison has teeth.
4. ⚠️ **This is a GATHER change**, so `readjudicate` and `reexport_arm` are
   **structurally blind** to it and pricing needs **two full re-gathers**.
   Budget for it: a 4-page scan gather is ~1–2 hours.
5. **Flag direction**: a new default-OFF flag takes an **allow-list** ON test.
   `test_flag_default_direction.py` derives and will check you.

## 7. TRAPS THIS REPO HAS ALREADY PAID FOR

- ⚠️ **A fresh worktree has no `.venv-omrned`, `.venv-surya`, `weights` or
  `library`.** Four symlinks, and **three fail on the SCAN side only**, so a
  worktree that runs the engraved arm cleanly proves nothing.
- ⚠️ **The staged CLI takes NO default weights.** Omit `--weights` and every
  cell abstains `reader_unavailable` and the run completes — which is honest,
  and cost this session a gather.
- ⚠️ **Do not `pkill -f llama-server`** — it is shared with other sessions.
- ⚠️ **Run a long gather WITHOUT `--musicxml`**; the exporter is imported after
  the gather, so a mid-run edit reaches it.
- ⚠️ **Subagents cannot write `.md` files** — eight occurrences. Plan to
  transpose, and say so in any brief.
- ⚠️ **`git log --all -S` cannot see a withdrawn or partly-landed
  investigation.** `ls benchmarks/` is the check that works, and it is how the
  stale premise in tonight's own brief was caught.

## 8. WHAT THIS JOB IS NOT

- **Not a re-measurement of §1.** That is done, on two renderers, with the
  mechanism isolated.
- **Not permission to change `min_height_spaces`** without measuring it.
- **Not a licence to trust `image_type`.** Seven `Typeset` in 289.
- ⚠️ **Not the in-bar accidental.** On correct-key staves we still write only
  69% of alterations and the residue is the in-bar accidental, which reaches no
  quantity at all. That is a **separate** job, already scoped in
  `docs/symbol-dossiers/accidentals-keys.md`, and blocked on a record-shape
  decision (*the record has nowhere to put a span*) that is Sean's.
