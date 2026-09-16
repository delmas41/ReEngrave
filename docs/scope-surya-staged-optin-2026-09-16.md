# Surya in the staged pipeline: what opting in costs, and what the opt-out rests on

*2026-09-16. Asked by Sean: "It sounds like we should opt in Surya for
ReEngrave — one question. I think I originally opted out due to time it adds.
How much does it add per page and are there other options? Would it be worth
training our own AI agent to do OCR instead of Surya?"*

**Answer in one line: Surya already runs on every staged page whether or not
`--surya` is passed (the direction-text reader spawns it by default), the
"~75% of a whole-work run" the opt-out cites was never measured anywhere, the
one same-pages pair that exists says +18%, and the right move is to flip BOTH
OCR flags on together — after fixing a record that today cannot tell "no OCR
installed on this machine" from "this page prints no label". Do not train an
OCR.**

Every figure below is read off artefacts already committed to this repo, or
off the code at `da2c9c1`. **No new arm was run** — this was scoped in a
remote container with no `library/`, no `.venv-surya` and no `.venv-omrned`,
so nothing here *could* be run. Where a figure is an inference rather than a
measurement it is marked as one. §10 lists what was verified by reading the
tree and what was taken on trust from a benchmark doc.

---

## 1. What is actually opted out — narrower than remembered

| Path | Surya | Where |
|---|---|---|
| `transcribe` → `contextual._labels_for_page` | **ON** — `surya_fallback=True`, self-disables without `.venv-surya` | `contextual.py:565-570, 688-693` |
| `OMR_DIRECTION_TEXT` (word reader; uses Surya + Tesseract) | **ON by default since 2026-09-02** | `transcribe.py:4359`; CLAUDE.md flag table |
| `tools/omr/staged/` — `run_staged` / `run_staged_on` | **OFF** — `surya_fallback=False, ocr_fallback=False`; opt-in via `--surya` / `--ocr` | `pipeline.py:104-110, 141-147`; `staged/__main__.py:113-119` |

The staged CLI is the only place Surya is opted out. Everything else has had
it on for weeks.

## 2. What it costs

Two separate costs, routinely conflated:

**(a) Model load.** `_surya_worker.py:17-20` quotes ~70 s on first use vs
1.5 s/system after. `staff_labels_surya.py:84-91` measures a full
spawn+load+kill subprocess at **15.8–17.5 s** vs 4.7–5.9 s resident, i.e.
~11 s per spawn. *Inference, not measured:* the 70 s is a cold-page-cache
first load and the ~15 s/page at CLAUDE.md "keep-alive" is the warm re-spawn.

**(b) Per-page read**, from CLAUDE.md's Surya keep-alive section and
`benchmarks/omr-direction-text-2026-09/DEFAULT_2026-09-02.md:60-140`:

| Work | Measured |
|---|--:|
| Margin labels, 17-staff page, spawn-and-kill | **21.4 s** |
| Same page, resident server (`--serve`) | **6.9 s** (the residue is the worker's `torch` import) |
| Whole `transcribe`, same page | 44.0 s → **30.6 s** resident |
| Direction-text OCR, per candidate crop | **0.5–5.1 s**; 13–40 crops/page on scans; one page at 177.6 s |

So with a resident server Surya is ~7 s on a page already taking 30 s: about
**23%**. Spawn-and-kill, 21.4 of 44.0: about **49%**.

### The "~75%" has no source

`tools/omr/staged/__main__.py:109-112` and CLAUDE.md's "SHIPPED: (1)
`run_staged` forwards `pdf_path`" paragraph both justified the staged opt-out
with *"CLAUDE.md measures Surya at ~75% of a whole-work run"* and *"a default
that silently trebles a gather"*. **CLAUDE.md contains no such measurement.**
Its only timing table gives 49% and 23%, and neither is a *gather*. Both sites
are corrected in the same commit as this document.

### The one same-pages pair that does exist: +282 s over 4 pages

Two committed scripts, otherwise identical — same PDF (Litolff Beethoven 5,
`imslp984073`), `--pages 1-4`, same weights, dpi 600,
`OMR_SURYA_KEEP_ALIVE=0`, `--progress`:

| script | flags | start → end (UTC, 2026-09-11) | wall |
|---|---|---|--:|
| `benchmarks/omr-cleanup-count-2026-09/run_gather.sh` | none | 10:48:18 → 11:14:38 | **1580 s** |
| `benchmarks/omr-part-join-phase2-2026-09/run_gather.sh` | `--surya --ocr` | 19:23:10 → 19:54:12 | **1862 s** |

**+282 s = +17.8%, ~70 s/page.** Caveats, all real: n=1 each; **different
trees** (the `pdf_path` forward, `pipeline.py:116-127`, landed between them,
so the control ran *no* label rung at all, not even the text layer); the
same day as the shared-server queueing in §4; and the documented page-level
variance (page 16: 440 s vs 210 s, DEFAULT doc) is as large as the effect.
The attributable prediction from (a) is ~16–20 s/page — one extra spawn ≈
11 s + 1.5 s/system × 1–2 systems + Tesseract seconds — i.e. 65–80 s for four
pages; the observed 282 s is 3.5–4× that and **the residue is unexplained.**
Not defensible as *the* number. But it is the only one, and it is nowhere
near 75% or "trebles".

## 3. The finding that changes the framing: Surya is spawned twice per staged page

`gather.py:2474` runs `gather_direction_words` last on every page.
`gather.py:2213-2229` gates it on `OMR_DIRECTION_TEXT` (default `"1"`) and
calls `direction_text.default_readers`, which (`direction_text.py:719-741`)
appends Surya **whenever `staff_labels_surya.available()`** — no flag. Label
crops and direction crops are separate subprocess calls
(`staff_labels_surya.read_staff_labels_surya` vs `.read_crops_text`).

So on a machine with `.venv-surya`, a staged page already spawns Surya once
for directions. `--surya` off saves **one of two spawns.** The "time it adds"
memory most plausibly attaches to the direction-text flag — its old
`transcribe` comment read *"OFF by default because it spends OCR: ~9 s … the
first call of a run pays ~70 s more"* (quoted in DEFAULT_2026-09-02.md:61-65)
— and that flag was flipped on 2026-09-02.

## 4. The other options, and why the tempting ones are traps

The cascade in `contextual._read_labels_for_page` (`contextual.py:694-696`):
**PDF text layer → Surya 2 → Tesseract → Claude vision (assist)**.

| Rung | Cost | Speed | Accuracy | Source |
|---|---|---|---|---|
| Text layer | free | instant | 18 of 65 IMSLP PDFs have one; **0 of 75 staves** on the Litolff scan | CLAUDE.md; `probe/margin_label_reach.py` |
| Tesseract | free | seconds, **no model load** | 26/29 labels (90%), 0 invented — but **14/17 parts** vs vision's 17/17 on beet5-p48 (one `Tr. Alt.`→`A.` misread collapses the pinned trombone block) | `TESSERACT_2026-08-31.md` |
| Surya 2 | free | 1.5 s/system + load | **0 disagreements** vs text layer; 89% of Claude's yield | `SURYA_BAKEOFF_2026-08-31.md` |
| Claude vision | ~1¢/system | ~3 s/system | 29/29; repairs a clipped label from the running order | `findings.md`, same dir |

**`--ocr` on / `--surya` off is a real, unevaluated intermediate and the wrong
default.** For it: on 575951-p1 Tesseract read 12/12 consumable
(`rungs-b5-575951-p1.json`). Against it: its error mode is in-word and
*resolving* (`Ki.Tr.`→Trumpet at high confidence), and in staged nothing
outranks a matched label — there is no vision rung (`gather.py:1989-1991`:
`Assist("none"), budget=[0]`) and identity takes the label straight through
`lookup` (`identity.py:60-86`). A confident wrong label *is* the graft.
Tesseract's measured value is as an additive rung *under* Surya (+8 gains,
0 losses on the scan gate, `contextual.py:850-870`). **Both or neither.**

**Re-ordering the cascade (Tesseract before Surya) is a trap.** It looks like
it saves the model load before a rung that needs none. It does not:

- `OMR_LABEL_MERGE_QUALITY` is **default on since 2026-09-06**
  (`contextual.py:482-486`), and both early returns between the free rungs
  are gated `if not quality_merge_enabled()` (`contextual.py:759, 799`). So
  Surya runs on every page whatever the order — **reordering saves zero
  spawns.** The only way it saves time is to reinstate a Tesseract-satisfied
  `_well_covered` gate, which recreates beet5-p48 exactly.
- Reversed, Surya must beat Tesseract *strictly* (`_merge_key(read) >
  _merge_key(labels)`), so a 12/12-vs-12/12 tie **keeps Tesseract's text**,
  and Surya — now the additive rung that "never overwrites a matched label" —
  can no longer correct a matched-wrong Tesseract read at all. Outcome
  change, wrong direction, on the precision-critical case.
- Who should win a disagreement: Surya — 0 wrong in 76 vs Tesseract 1 wrong
  in 29 with the wrong one resolving. The current order encodes that.

**`OMR_SURYA_KEEP_ALIVE=0` does not give a run its own worker.** CLAUDE.md's
"AND A CORRECTION TO THIS FILE'S OWN SURYA ESCAPE" (2026-09-11) corrects its
own earlier keep-alive section: Surya attaches through its own sentinel to
whatever server exists; the flag governs whether it is *kept*. One page
queued ~6 min behind a sibling session. Any timing arm that runs while a
server is resident measures queueing, not Surya.

## 5. Train our own OCR — no, and here is the argument

1. **What Surya loses is not character recognition.** Zero disagreements with
   Claude over 76 staves. Its misses are: crop clipping (`arinetti in C` for
   `Clarinetti in C` — a crop fault, `SURYA_BAKEOFF_2026-08-31.md` "Where
   Claude wins"); lexicon single-slips (`Fug.`/`Fag.`, `Oh.`/`Ob.` — matching,
   deliberately declined in `OCR_CONFUSIONS_2026-09-02.md`); decoder
   repetition/runaway (`staff_labels_surya.py:102-120`); and reasoning over
   qualified abbreviations (`Tr. Alt.`, `Kl. Tr.`), which Claude wins by
   reading the running order, not by reading glyphs better. A trained
   recognizer improves none of these.
2. **This project has already paid the small-corpus training bill, and it
   deleted classes.** CLAUDE.md "A fine-tune on this corpus DELETES CLASSES":
   eleven method arms on ~600 cells, tie 249→0, slur 184→0, beam 188→0,
   restWhole 396→0 — not a confidence shift, not the labels, not a
   hyper-parameter. The repair was head surgery, not retraining. The verified
   margin corpus is on the order of a few hundred staves across a handful of
   publishers; nothing generalises across 289 editions' typefaces from that.
3. **A closed classifier over the 260-alias lexicon** kills the property the
   identity layer rests on — "the reader names a staff correctly or says
   nothing" (`roster.py:94-115`). A classifier always answers, and the
   vocabulary is open across languages and editions (`score_language.py`). A
   confident wrong answer is the graft.
4. **Fine-tuning Surya** (650M, served as GGUF through llama.cpp) needs the
   PyTorch checkpoint, a GPU and a corpus, and its failure modes (runaway,
   temperature nondeterminism) are not data problems. **Tesseract LSTM
   fine-tuning** is the one cheap trainable option (CPU, hours) — but its
   ceiling is in-word error on the hard tail Surya already reads for free.

**Cheap, well-aimed, and not trained:**

- **Crop width w20 → w26.** w26 read `Fag.` cleanly where w14 repeated it 7×
  (`SURYA_BAKEOFF` "width sweep"); clipping is the largest unrecovered
  bucket; `crops-w26/` and `results-surya-w26.json` already exist. An
  afternoon.
- **Dynamics glyph templates.** `symbol_library/` holds no `dynamic*`
  template and carries `Bravura.otf`, so the 42 SMuFL dynamic glyphs in
  `glyphnames.json` (including the composites `dynamicFF`,
  `dynamicSforzando`) are *renderable*, not trainable. CLAUDE.md's own ranked
  next work for the dynamics family. Hours.
- **The roster veto** (§7) — the actual fix for the one Surya error that
  survives (`Tr. Teq.`→Trumpet, `contextual.py:915-925`).

## 6. The prerequisite nobody had spotted: the record cannot see an absent rung

`gather.py:2000-2019`: every staff without a label is
`abstain(... reader=READERS.TEXT_LAYER, reason=NO_INK)` and every label is
`observe(... reader=READERS.TEXT_LAYER ...)` — **regardless of which rung
read it.** Direction words have the four-state contract (`READER_UNAVAILABLE`
/ `OUT_OF_SCOPE` abstentions vs `NO_INK` / `NO_READING` decisions); margin
labels do not. NOTES.md records the same blindness in `transcribe` (the
Surya-rung `except` at `contextual.py:766-770` leaves no trace).

**Flipping the default without fixing this manufactures the "green check that
reached nothing" failure verbatim**: a venv-less machine would produce a
record saying every scan staff prints no label, indistinguishable from a
machine that read them all. The fix is hours, and it is needed whichever way
§9 comes out.

## 7. What was missing from the question

- **Per-work label caching exists — in `transcribe` only.** `roster.acquire_roster`
  (`OMR_ROSTER` default on, `roster.py:275-355`) reads one system, cached,
  window 3. Staged never acquires one: `staged/__main__.py:136-141` calls
  `run_staged` without `roster=`, no caller passes one, and
  `no_producer.py` names `run_staged(roster) → gather_external(roster)` as a
  chain nobody starts; `identity.py:16-29` composes from `Q.ROSTER_ENTRY` and
  gets none. It does not make per-page cost moot (continuation systems still
  need per-page labels for alignment — Litolff prints wind/brass
  abbreviations on every system and nothing for strings), but it buys
  identity on pages no OCR can read: Dvořák Simrock p6/p7 read **0/15 and
  0/30** (`benchmarks/omr-label-ladder-2026-09/gate-exposure-oneway.json`).
  Once a roster is in staged, "Tesseract per page + roster veto, Surya only
  on the ≤3-page roster window" becomes a defensible cheap intermediate.
  Unmeasured; mostly a wiring job.
- **Two subprocesses per page** (labels + directions) is the remaining
  duplication. Merging them into one worker job saves one spawn (~11 s at
  `KEEP_ALIVE=0`) or one `torch` import (~5 s resident) per page.
- **A run-private keep-alive server** would remove the shared-state hazard,
  but `OMR_SURYA_SENTINEL` (`staff_labels_surya.py:95-98`) only steers
  `--check`/`--stop`; whether surya's own attach honours a custom sentinel
  needs the venv source. **Unverified — do not advise it until it is.**
- **A smaller/quantised model** attacks the wrong term: per-system inference
  is 1.5 s; the cost is spawn + import.
- Born-digital pages already skip Surya for labels (the text layer answers
  first) and `page_is_engraved` drops Tesseract for directions.

## 8. Decision and ranked plan

**Conditional YES: flip `--surya` and `--ocr` on together, Surya-first order
untouched, after (1) and (2) below.** Flag shape `--no-surya` / `--no-ocr`
(`store_false`) so absence is ON.

- [ ] **1. Fix the record first** (§6) — `READER_UNAVAILABLE` when a
      requested rung's `available()` is False; attribute each label to the
      rung that read it (pass `tiers=[0]*5` into `_labels_for_page` and read
      them back); route the Surya-rung `except` into a recorded failure; print
      the rungs available in the `--progress` header. Hours. Needed regardless.
- [ ] **2. Run §9** — half a day of machine time, `--check`-gated, ABAB,
      census-checked. Retire the "75%" with the record path either way.
- [ ] **3. Flip both defaults ON** — conditional on 2. *Every default flip
      here is Sean's call.*
- [ ] **4. Merge the two Surya subprocesses per page into one job** —
      ~10–15 s/page back.
- [ ] **5. Wire the roster producer into staged** — the structural fix for
      unlabelled pages and the matched-wrong tail.
- [ ] **6. Dynamics templates from Bravura** — the ranked accuracy work.
- [ ] **7. Crop width w26 re-measure.**
- [ ] **8. Do not train an OCR. Do not reorder the cascade. Do not ship
      Tesseract-alone.**

## 9. The experiment that settles it

**Fixture:** the two committed `run_gather.sh` scripts' own inputs —
`library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf`,
`--pages 1-4` (75 staves, 50 labels — a census baseline), weights
`tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`,
dpi 600. Optional second document to avoid a one-edition conclusion: Brahms 1
Breitkopf 317803 p1-4 (path in `data/score-library/catalog.json`).

**Part A — the attributable numerator (no detector).** A probe in the shape
of `benchmarks/omr-label-ladder-2026-09/probe_ladder_rungs.py` with timing:

```
# benchmarks/omr-surya-staged-cost-2026-09/probe_label_rung_cost.py  (to be written)
for page in 1..4, repeat 3x:
    pws = detect_staves(render_page(PDF, page, dpi=600))
    record staff_labels_surya.resident_server() BEFORE            # must be None
    t = perf_counter(); text  = read_staff_labels(pws);             t_text
    t = perf_counter(); surya = read_staff_labels_surya(pws);       t_surya_1  (spawn)
    t = perf_counter(); surya2= read_staff_labels_surya(pws);       t_surya_2  (second spawn, same process)
    t = perf_counter(); tess  = read_staff_labels_tesseract(pws);   t_tess
    record resident_server() AFTER, KEEP_ALIVE env, git rev-parse HEAD + status --porcelain,
           n_staves, n_systems, per-rung raw/usable/consumable counts (the ladder's own _usable/_consumable)
```

```bash
OMR_SURYA_KEEP_ALIVE=0 python3 -u benchmarks/omr-surya-staged-cost-2026-09/probe_label_rung_cost.py \
    --pdf "$PDF" --pages 1-4 --repeats 3 --json-out out/rung-cost.json
```

Census: `surya` count > 0 on every page-run, or the run is void.

**Part B — the fraction of a real gather (denominator).** Four arms, ABAB,
production weights, one tree:

```bash
export PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
export W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
export OMR_SURYA_KEEP_ALIVE=0 OMR_DIRECTION_TEXT=1
mkdir -p benchmarks/omr-surya-staged-cost-2026-09/out; cd benchmarks/omr-surya-staged-cost-2026-09
for arm in L1 C1 L2 C2; do
  python3 -m tools.omr.staff_labels_surya --check | tee out/$arm.precheck   # resident server => STOP; never pkill; reschedule
  { git rev-parse HEAD; git status --porcelain | wc -l; } > out/$arm.timing
  FLAGS=$([[ $arm == L* ]] && echo "--surya --ocr")
  date -u +%s >> out/$arm.timing
  python3 -u -m tools.omr.staged "$PDF" --pages 1-4 --weights "$W" $FLAGS \
      --out out/record-$arm.json --progress 2>&1 | tee out/$arm.log
  date -u +%s >> out/$arm.timing
  grep -c '"margin_label"' out/record-$arm.json >> out/$arm.timing          # census: L >= 45, C == 0
done
# one extra arm: labels with direction text OFF -- is the model load shared between the two rungs?
OMR_DIRECTION_TEXT=0 python3 -u -m tools.omr.staged "$PDF" --pages 1-4 --weights "$W" --surya --ocr \
    --out out/record-LD.json --progress 2>&1 | tee out/LD.log
```

**Controls, each against a documented trap:**

1. *Shared server* — `--check` before every arm; a resident server means the
   arm measures queueing (§4), so abort and reschedule. Never `pkill`.
2. *Unprovenanced A/B* — every record carries `commit`/`dirty`
   (`staged/__main__.py:60-84`); all arms must share one commit with
   `dirty=false`; the flag is the only variable (unlike the 09-11 pair).
3. *Cached/void arm* — the census line: an L arm with < 45 label observations
   or a C arm with > 0 is void; the `--progress` header must show both rungs
   available (needs §8 step 1).
4. *Page variance* — Part B's delta is never quoted alone; the L1–L2 and
   C1–C2 spreads are the noise floor, and Part A's per-rung seconds are the
   attributable number, reported per page, not as a 4-page total.
   `python3 -u`, nothing else on the machine.

**Pre-registered decision rules — written before the run:**

- **Flip both ON** if Part A median attributable (Surya spawn+read +
  Tesseract) ≤ 30 s/page, max ≤ 60 s over the 12 page-runs, **and** Part B's
  L−C ≤ 25% of C or within the ABAB noise floor.
- **Keep opt-in** (but still ship §8 step 1) if Part A median > 60 s/page, or
  L−C > 50% *and* exceeds 2× the noise floor, or any page-run exceeds 180 s
  attributable more than once (the 177.6 s direction-text outlier shape).
- **Between those:** flip, put the measured number in the `--help` text, and
  prioritise the single-subprocess merge (§7).
- Either way: the record path replaces "75%" wherever it survived. If the LD
  arm shows the label rung costing ≥ 2× more when it is the only Surya user,
  the load is shared and the merge is worth more than the flag.

## 10. Verified vs taken on trust vs inferred

**Verified by reading the tree at `da2c9c1`:** the cascade and merge code
(`contextual.py:482-486, 565-600, 688-935`); `gather.py:1985-2019,
2129-2229, 2474`; `pipeline.py:104-147`; `staged/__main__.py:100-141`;
`direction_text.py:666-741`; `no_producer.py:95-108`; both `run_gather.sh`
scripts and both `.timing` files (the arithmetic is ours); CLAUDE.md's flag
table row for `OMR_DIRECTION_TEXT`, its Surya keep-alive section and the
2026-09-11 correction to it, the "SHIPPED: (1)" paragraph, the "DELETES
CLASSES" section, and the three-reader table; `DEFAULT_2026-09-02.md:60-140`;
`SURYA_BAKEOFF_2026-08-31.md` and `TESSERACT_2026-08-31.md` in full;
`OCR_CONFUSIONS_2026-09-02.md` (head); `training/README.md` and
`VAST_AI_SETUP.md`.

**Taken on trust (a benchmark doc's own figures, not re-derived):** the
bake-off tallies beyond the width lines; the 289-edition text-layer census;
`rungs-b5-575951-p1.json` and `gate-exposure-oneway.json` tallies;
`roster.py` / `identity.py` / `work_roster.py` line numbers; "38 templates"
(the `dynamic*` absence was checked, the count was not).

**Explicit inferences (not measurements):** 70 s = cold load vs ~11 s warm
re-spawn; the 09-11 pair's unexplained residue being shared-server queueing;
a smaller GGUF loading faster; anything about surya's sentinel behaviour.

**Corrections to the first draft of this analysis, recorded because the
correction is the finding:** it said the training scaffold had "never been
run" — wrong, and the truth (eleven arms, whole classes deleted) is the
stronger argument; it proposed reordering the cascade — a trap, §4; it quoted
CLAUDE.md's keep-alive escape without its own 09-11 correction, §4; and it
said the 75% had no nearby measurement at all — there is one, +18%, §2.

## 11. Start prompt for the next session (Sean's machine)

> Read `docs/scope-surya-staged-optin-2026-09-16.md` end to end before
> touching anything; it is the scope for this session and §8–§9 are the plan.
> Work on branch `claude/surya-ocr-reengraved-yo11tk` (fetch it — a draft PR
> is open). This must run in the main checkout at
> `/Users/seanjohnson/Desktop/ReEngrave`, not a worktree: it needs
> `.venv-surya`, `.venv-omrned`, `library/` and the weights, and a worktree
> has none of them (Surya silently self-disables, which is exactly the
> failure §6 is about).
>
> **Before anything else:** `python3 -m tools.omr.staff_labels_surya --check`.
> If a server is resident, stop and tell me — never `pkill -f llama-server`.
>
> **Step 1 — the record fix (§6, §8 step 1).** In `tools/omr/staged/gather.py`
> `gather_margin_labels`, make the record tell "no OCR rung on this machine"
> apart from "no ink": abstain `READER_UNAVAILABLE` when a requested rung's
> `available()` is False; attribute each label to the rung that read it
> (`tiers=[0]*5` into `_labels_for_page`); route the Surya-rung `except` in
> `contextual._read_labels_for_page` into a recorded failure; print the rungs
> available in the `--progress` header. Tests for each, and prove every new
> guard fails first on a deliberately broken input. Commit.
>
> **Step 2 — Part A** of §9: write `probe_label_rung_cost.py`, run it, 4
> pages × 3 repeats, census-checked.
>
> **Step 3 — Part B** of §9: the four ABAB arms plus the LD arm, `--check`
> before each, one commit, `dirty=false`, census line on every arm.
>
> **Step 4:** apply the pre-registered rules in §9 to the numbers and write
> `benchmarks/omr-surya-staged-cost-2026-09/FINDINGS.md`. Then STOP and show
> me the numbers and the verdict. The default flip is my call — do not change
> `pipeline.py` / `__main__.py` defaults until I say so. If I say flip: use
> `--no-surya` / `--no-ocr` (`store_false`), update the `--help` text,
> CLAUDE.md's flag table, `version_memory.md`, `PROJECT_BRIEF.md`.
>
> Do not reorder the cascade. Do not ship `--ocr` alone. Do not train
> anything. Do not touch a llama-server you did not start.
