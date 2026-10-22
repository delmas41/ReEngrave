# The last 89 printed staves of the scan gate — mappable after all

2026-09-06. Branch `worktree-agent-a8f6cb1ef5753728b`, on `eafca887` plus the
staves-map UI branch. **Nothing here changes a default and nothing here writes
`works.json`.**

```bash
python3 probe_one_line_staves.py        # are the percussion rules detected?
python3 probe_mappable.py --patched     # does the consumer accept a map?
python3 probe_note_recall_join.py       # does a map break note_recall?
python3 probe_bach_grand_staff.py       # is the Cembalo a grand staff?
python3 probe_merge_path.py             # would a confirmed map merge?
OMRNED_PYTHON=… python3 price_maps.py   # what is it worth?
.venv-omrned/bin/python attribute_residual.py   # what is left, and whose is it?
```

---

## The answer in one table

| row | printed staves | mappable? | `entire staff` today | after a map | what the residual IS |
|---|---|---|--:|--:|---|
| mahler-…-p2 | 22 (17 five-line + 5 one-line) | **yes** | 649 | 100 | the one-line percussion staves |
| mahler-…-p3 | 15 (13 + 2) | **yes**, after one 1-line fix to `page_normalise` | 1674 | 207 | ditto |
| mahler-…-p4 | 21 (18 + 3) | **yes**, after a second 1-line fix | 1764 | 361 | ditto |
| mahler-…-p5 | 21 (17 + 4) | **yes** | 1220 | 504 | ditto |
| bach-…-p1 | 24 (2 systems × 12) | **a map is legal and worth exactly zero** | 286 | 286 | the Cembalo GRAND STAFF |
| | | | **5,593** | **1,458** | |

⚠️ **"printed staves" above is the count a reader sees**, from each row's own
hand-read `n_staves_note`. It is not `works.json`'s `page.n_staves`, which
counts FIVE-LINE staves only and says so; and it is not the detected count.
All three are given separately in §2.

⚠️ **The right-hand column is a DIFFERENT BENCHMARK ERA** (`page_normalise`
rule 5). It is structural charge removed — the metric ceasing to bill a
printing convention — never the pipeline improving, and it may not be
differenced against the recorded 20-row 0.8444.

---

## 1. The recorded objection is true of a different consumer

`works.json`'s own README says why Mahler has a `condensation` block instead of
a `staves` map:

> its printed staves cannot double as a note-recall map: five of them are
> ONE-LINE percussion staves a five-line detector cannot find, so a positional
> join to the prediction's parts would be wrong from staff 13 on.

Three consumers read `staves`, and the sentence is about ONE of them:

| consumer | what it does with the map | does the objection reach it? |
|---|---|---|
| `scan_eval.note_recall` | `staves[i]` ↔ `pred.parts[i]`, **by ordinal** | **yes** — this is exactly it |
| `scan_eval.structural_divergence` | counts parts and condensed staves | no — it never looks at the prediction |
| `page_normalise.normalise` | merges REFERENCE parts into a derived truth | **no** — its only inputs are the trimmed truth and the map |

`page_normalise` is the consumer the `entire staff` bucket is about. Its
signature is `normalise(truth_xml, staves_map)`; the prediction is not an
argument, and `musicdiff` pairs afterwards, on parts, exactly as before. That
is the same distinction `benchmarks/omr-staves-map-2026-09/FINDINGS.md` §4 drew
for its own five rows — *"asked of the consumer, not of the note"* — and it
lands the same way here.

**And the map carries the repair for `note_recall` too.** A one-line percussion
staff is precisely the entry with no predicted part to pair with, and it is
precisely the entry works.json's own Mahler idiom already marks `"lines": 1`.
Measured (`note-recall-join.json`), over the canonical run's own exports:

| row | map entries | of which one-line | predicted parts | ordinal join over ALL entries | over FIVE-LINE entries |
|---|--:|--:|--:|---|---|
| mahler p2 | 21 | 4 | 17 | ✗ | **✓** |
| mahler p3 | 15 | 2 | 13 | ✗ | **✓** |
| mahler p4 | 21 | 3 | 18 | ✗ | **✓** |
| mahler p5 | 21 | 4 | 17 | ✗ | **✓** |
| bach p1 | 11 | 0 | 12 | ✗ | ✗ |

**4 of 4.** So `note_recall` does not have to abstain on Mahler; it has to skip
`lines == 1` entries when it walks the map. That is a proposal, not a change —
see §7.

---

## 2. ⚠️ THE ONE-LINE PERCUSSION STAVES ARE DETECTED. They are dropped at cell extraction, on purpose.

`probe_one_line_staves.py` renders each page at 600 dpi and runs the phase-1
stages on the CURRENT tree, so this is about the code and not about a stored
artefact:

| row | `detect_staves` total | five-line | **one-line** | staves that produce a measure cell | one-line staves that do |
|---|--:|--:|--:|--:|--:|
| mahler p2 | 19 | 17 | **2** | 17 | **0** |
| mahler p3 | 15 | 13 | **2** | 13 | **0** |
| mahler p4 | 21 | 18 | **3** | 18 | **0** |
| mahler p5 | 21 | 17 | **4** | 17 | **0** |

Every one of the 11 comes back full width (`x_start`≈515, `x_end`≈4222 on p5,
against a 4385 px page), at zero height (`span_px` 0), and at the `staff_index`
values that are exactly the gaps in the stored run's own numbering — p5's
artefact goes 0-9 then 14-20, and the four one-line rules are 10, 11, 12, 13.

`staff_detector._single_line_staff_rows` finds them **deliberately**: it is a
documented rule with its own three constants and its own worked example on this
very edition ("Mahler 5 p10 … the Gr.Tr. rule (width 1857), the long WAVY TRILL
LINE printed between the two parts (1410), and the Kl.Tr. rule (1858)").

What drops them is one line of `measure_extractor.extract_measures`:

```python
    for s in pws.staves:
        if len(s.line_ys) >= 5:
            sys_staves.setdefault(s.system_index, []).append(s)
```

with its own comment saying why — *"a cell is canonicalised by its staff's
five-line span and a single rule has none"*. So they never reach a measure
cell, a detection, the export, or the JSON. **This is a stated design decision,
not a bug and not an accident**, and the project memory's shorthand
"a zero-height filter" is this line.

⚠️ **It is a PIPELINE fact, and it does not block a map.** A `staves` map is
about the page and the reference; it does not need the pipeline to have read a
staff. What the gap does is set the ceiling: those staves' reference parts can
never pair, so their charge is honest recognition cost.

⚠️ **Mahler p2 detects 2 of its 5 printed rules.** The other three — including
the `Becken u. Gr.Trommel von einem geschlagen` combined-player rule — are
missed by `_single_line_staff_rows` itself. p3, p4 and p5 detect all of theirs.
That asymmetry is why p2 is the one row whose crop panel cannot be shown
per-slot (§6).

---

## 3. Every one of the five rows normalises

`probe_mappable.py`, asking `page_normalise.normalise` directly:

| row | reference parts | map entries | names every part | duplicate part | accepted | source → output parts | divisi share |
|---|--:|--:|---|---|---|---|--:|
| mahler p2 | 38 | 21 | ✓ | none | **yes** | 38 → 21 | 0.000 |
| mahler p3 | 38 | 15 | ✓ | none | **yes*** | 38 → 15 | 0.025 |
| mahler p4 | 38 | 21 | ✓ | none | **yes*** | 38 → 21 | 0.041 |
| mahler p5 | 38 | 21 | ✓ | none | **yes** | 38 → 21 | 0.006 |
| bach p1 | 11 | 11 | ✓ | none | **yes** | 11 → 11 | 0.000 |

\* after the two one-line fixes in §4.

**The maps are not my reading.** `candidate_maps.py` transcribes what
`works.json` already holds:

* **p2** — `condensation.staves_as_printed`, a complete structured 22-entry map
  with its own `derived_from` evidence, verbatim, minus the one entry whose
  `parts` is empty;
* **p3 / p4 / p5** — the allocation written out instrument by instrument in
  each row's own `notes` field ("Fag.1/2->[10], Contraf.->[11], …"), drafted by
  the sessions that verified those windows against the print.

### Two conventions are mine, and both are marked

**(a) One printed staff is dropped from p2's map because the reference has no
part for it.** works.json records it itself: *"THE PAGE PRINTS A 22nd STAFF THE
REFERENCE HAS NO PART FOR … the condensed truth has 21 parts against 22 printed
staves and CANNOT represent that staff."* `page_normalise` raises on an entry
whose `parts` is empty, and `merge_additions` and the UI both refuse one. So the
map has 21 entries for 22 printed staves, and `UNREPRESENTABLE` in
`candidate_maps.py` records the missing one rather than losing it.

**(b) A part with no printed staff on this page is FOLDED onto a nominated
staff.** Mahler's pages are one system each and tacet-suppress whole sections —
p3 prints no flute, oboe or clarinet staff at all — while `page_normalise`
refuses to drop a part, correctly (*"a normalised truth missing a part scores
BETTER for the wrong reason"*). 13 parts on p3, 4 on p4, 6 on p5.

Two things are checked rather than assumed:

* ⚠️ **every folded part is SILENT over the row's own window** — measured on
  the trimmed truth, `absent_all_silent: true` on all three rows, 0 sounding
  events. A fold of a SOUNDING part would hide a real failure.
* ⚠️ **the fold TARGET is arbitrary and the arbitrariness is harmless** — moving
  every folded part to a different staff (the last entry) leaves the derived
  truth's per-part content **identical** on all three rows
  (`fold_target_control.identical_content: true`). That control is the reason
  the convention is defensible instead of merely unnoticed.

⚠️ **The control failed the first time it was run, and the failure was real.**
Sorting each entry's `parts` ascending puts a silent folded Piccolo AHEAD of the
printed Fagotte, and `page_normalise` keeps `parts[idx[0]]` — so the derived
truth carried a silent part's bars, and its RESTS, wherever a measure was
`silent_all`. Priced rather than argued (§5).

---

## 4. ⚠️ TWO LATENT FAULTS IN `page_normalise`, and neither is Mahler-specific

Both are one-liners, both are in the shipped module, and both are reached by
ordinary orchestral material that the eight already-normalised rows happen not
to contain. `probe_fault_shapes.py` names the exact bar for each.

**FAULT A — `_tokens` sorts a heterogeneous key** (`page_normalise.py:93`).

```python
        if isinstance(el, note.Rest):
            body: Any = "R"                     # a str …
        elif isinstance(el, chord.Chord):
            body = tuple(sorted(...))           # … next to a tuple
        ...
    return tuple(sorted(out))                   # TypeError when (off,dur) tie
```

Two events sharing `(offset, duration)` and differing in kind compare `str`
against `tuple`. **It needs those two events in the SAME measure**, which takes
a source part whose bar already has two `Voice`s, one resting where the other
sounds. Mahler's `Vier Trompeten in B.` writes exactly that: p3 mm 12 and 14,
p4 mm 17-19. Fix: give a rest the tuple body `("R",)`.

**FAULT B — `_voice_merge` inserts a deepcopy that still points at its old
site** (`page_normalise.py:233`).

```python
            v.insert(el.getOffsetInHierarchy(m), copy.deepcopy(el))
```

music21's `sortTuple()` then looks `id(self.activeSite)` up in the copy's own
`sites` dict and raises `KeyError: <id>`. Fires on p3's `Sechs Hörner in F.`
mm 15-16 — unaligned divisi, no nested voices — and **not** on p5 m31, which is
the same shape, so it is a latent usage fault rather than a property of the map.
Fix: clear `activeSite` on the copy before inserting it.

**FAULT C, only for a diagnostic arm but worth recording** — `_tokens` reaches
for `el.pitch` on a `music21.note.Unpitched`, which is what every one-line
percussion part parses to. It cannot fire on an honest map here (each percussion
part is alone on its staff, so `classify` is never called), but it would on any
edition that condenses two percussion parts onto one rule.

**FAULT D, no exception, and the nastier one** — `_is_silent` tests
`isinstance(el, (note.Note, chord.Chord))`, so a bar of `Unpitched` percussion
notes reads as SILENT. Condensing a percussion part therefore DISCARDS its
notes without a word. Same reason it cannot bite an honest map here; same reason
it would bite a condensed one.

⚠️ **`page_normalise.py` belongs to the headline-validity workstream and I have
not touched it.** The patches live in `normalise_patched.py` in this directory,
monkeypatched at probe time and labelled *not the fix*.

**They block the merge, not just the probe.** `merge_additions.check_row` proves
a map by running `page_normalise.normalise` on it before writing —
`probe_merge_path.py` runs the reviewed tool's own validation both ways:

```
shipped page_normalise
  OK   mahler-…-p2   21 entries  38 -> 21 parts
  FAIL mahler-…-p3   page_normalise REFUSED this map: KeyError: 4397159184
  FAIL mahler-…-p4   page_normalise REFUSED this map: TypeError: '<' not supported …
  OK   mahler-…-p5   21 entries  38 -> 21 parts
  OK   bach-…-p1     11 entries  11 -> 11 parts

with the two one-line fixes
  OK   all five
```

So: **the confirmation pass can be run today, and two of its five rows cannot be
merged until Faults A and B are fixed.**

---

## 5. What it is worth

`price_maps.py`. Both columns measured here, on one tree, in one `musicdiff`
batch, from the canonical run's own predictions (`.reconciliation`, the
artefacts behind `results-reconciliation.json` / pooled 0.8444). Nothing is
re-transcribed, so this prices the MAP and only the map.

```
row                                   raw NED  raw ed  raw ES |  nrm NED  nrm ed  nrm ES |    d ed   d ES
mahler-sym5-mvt1-local-p2              0.6884    1118     649 |   0.5802     702     100 |    -416   -549
mahler-sym5-mvt1-local-p3              0.8867    3075    1674 |   0.7424    2159     207 |    -916  -1467
mahler-sym5-mvt1-local-p4              0.9153    4149    1764 |   0.7815    3209     361 |    -940  -1403
mahler-sym5-mvt1-local-p5              0.9298    2967    1220 |   0.8382    2300     504 |    -667   -716
bach-brandenburg3-mvt1-468678-p1       0.8046    6148     286 |   0.8046    6148     286 |      +0     +0
dvorak-sym9-mvt1-405834-p5             0.4221     661       0 |   0.4221     661       0 |      +0     +0   <- CONTROL

pooled over the five candidate rows  raw 0.8534 / 17457 ed  (entire staff 5593)
                                     nrm 0.7802 / 14518 ed  (entire staff 1458)
```

**CONTROL: Dvořák p5 moves by exactly 0.** Its own works.json map is 15 parts
into 15 staves — the transform asked to change nothing — so a non-zero delta
there would mean the harness distorts the truth and no other row's number would
mean anything. It is 0 to the edit, and so is Bach.

⚠️ The raw `entire staff` column reproduces `map-coverage-cost.json`'s five
figures exactly (649 / 1674 / 1764 / 1220 / 286), which is the check that this
harness is scoring the same thing the coverage probe counted.

### The sorted-parts arm: works.json's convention costs 8 edits and keeps it

`merge_additions.shape_problems` refuses an entry whose `parts` is not
sorted-unique, and every already-merged row satisfies that. But
`page_normalise` treats `parts[0]` as load-bearing. On the existing rows the two
agree by luck — a condensed staff's parts are contiguous and ascending, so the
lowest index IS the printed staff's own first part. A tacet fold breaks the
luck. Priced:

| | p3 | p4 | p5 | total |
|---|--:|--:|--:|--:|
| printed part first | 2159 | 3209 | 2300 | 7668 |
| **`parts` sorted (works.json's shape)** | 2156 | 3228 | 2292 | **7676** |

**+8 edits of 7,668, 0.1%, all of it rest spelling.** The convention wins; the
UI emits sorted maps and `merge_additions` needs no change. Recorded because
the reasoning ("a silent part's bars survive") sounds much worse than the
measurement, and because the same latent coupling exists on every mapped row.

---

## 6. ⚠️ THE RESIDUAL IS THE PERCUSSION — but not on the staves you would guess

Arithmetic says the leftover must be the one-line staves: `n_output_parts −
n_predicted_parts` is 4 / 2 / 3 / 4, exactly each map's one-line entry count.
Arithmetic is not attribution, so `attribute_residual.py` opens the op list:

```
mahler-…-p2: pred 17 parts vs normalised truth 21; 4 part-level ops costing 100
    inspart  truth (missed)  idx 17 Zweite Violinen.   cost 25
    inspart  truth (missed)  idx 18 Violen.            cost 25
    inspart  truth (missed)  idx 19 Violoncelle.       cost 25
    inspart  truth (missed)  idx 20 Bässe.             cost 25
mahler-…-p5: 4 ops costing 504 — Violoncelle ×2, Bässe ×2
bach-…-p1 : 1 op  costing 286 — delpart, pred (INVENTED) idx 11 "Staff 11"
```

**The unpaired parts are not the percussion. They are the string section.**
musicdiff's part alignment is monotonic, so when the truth is four parts longer
than the prediction it sheds four parts from the END — and on a conductor's page
the end of the score is the strings, which are the most expensive staves there
are. That is why p2's residual is 100 and p5's is 504 on the same four-part
shortfall.

**A corollary worth carrying: the `entire staff` bucket names the staves the
alignment SHED, never the staves that were missed.** The same caution
`OMR_SLOT_STITCH` already records for a different reason.

The diagnostic arm proves it. Folding each one-line entry into the five-line
staff above it — musically false, and marked so — makes the truth exactly as
long as the prediction:

| | honest map | five-line diagnostic |
|---|--:|--:|
| mahler p2 | 702 ed, ES 100 | 578 ed, **ES 0** |
| mahler p3 | 2159, ES 207 | 1850, **ES 0** |
| mahler p4 | 3209, ES 361 | 2770, **ES 0** |
| mahler p5 | 2300, ES 504 | 1984, **ES 0** |

⚠️ **The diagnostic arm is not a candidate map and must not be merged.** It says
the Becken is printed on the Pauken staff, which is false — and because of
Fault D above it also silently deletes those percussion parts' notes. It exists
only to separate two things the honest map conflates.

### Bach: measured, and the direction is the other way

`probe_bach_grand_staff.py`, on the source `.mxl` with a real XML parser: the
Cembalo is **one `<score-part>`, one `<part>`, `<staves>` absent, no `<staff>`
elements** — a single-staff part. The trim is faithful. The page prints the
Cembalo on TWO staves and we read two, so the prediction has 12 parts against
the truth's 11, and the whole 286 is **one `delpart` on our own part 11**.

That is a charge for being right, and it is the mirror of the condensation this
whole exercise is about — but `page_normalise` only ever MERGES reference parts,
so the map idiom cannot express a split. An 11-entry map is legal, names every
part, normalises, and is a bit-for-bit identity transform worth **exactly zero
edits**.

**So Bach is not unmapped for want of a human. It is a page whose reference
condenses where the print does not, and no map over the current idiom reaches
it.**

---

## 7. Re-pricing the remainder

`entire staff` over the 20-row gate, `map-coverage-cost.json`'s accounting,
before and after:

| | today | with the four Mahler maps + Bach |
|---|--:|--:|
| rows with a hand-read map | 15 of 20 | **20 of 20** |
| `entire staff`, attributable | 11,927 | **17,520** |
| `entire staff`, cause UNKNOWN | **5,593** | **0** |
| printed staves a human would read | 89 | 0 |

⚠️ **Merging a `staves` map changes NO headline figure.** It changes what
`scan_eval.pooled_structural` can say, it makes the row normalisable, and it
makes `note_recall` computable. The 0.8444 is untouched by all of it.

The 5,593 decomposes as:

| | edits | |
|---|--:|---|
| Mahler condensation — 38 encoded parts onto 15-21 printed staves | **4,135** | removed by a map (a new era) |
| Mahler one-line percussion — 11 printed staves the pipeline skips at cell extraction | **1,172** | a PIPELINE ceiling, not a labelling gap |
| Bach Cembalo grand staff — 1 encoded part on 2 printed staves | **286** | not expressible by the map idiom |

**So: nothing here stays unattributable.** Mahler is not the ceiling the
commission braced for — it is the largest single block of removable structural
charge left in the gate, and its residual is a named pipeline gap with a
measured size.

### Two proposals, neither made here

1. **`note_recall` should skip `lines == 1` entries** when it walks the map.
   Measured 4/4 above; without it, giving Mahler a `staves` map makes
   `note_recall` print a per-staff table that is wrong from the first percussion
   rule down. It already reports `positional: false`, so the failure is flagged
   but not prevented. ⚠️ This needs `lines` to survive into `works.json`, and
   `merge_additions.shape_problems` currently refuses any key but `name` and
   `parts`. Allowing an optional `lines` is a one-line change to a reviewed
   tool that writes hand-verified truth — Sean's call, not mine.
2. **Faults A and B in `page_normalise`** (§4), which block two of the five
   merges. Owned by the headline-validity workstream.

---

## 8. The confirmation pass, if it is wanted

⚠️ **The reading is already done**, exactly as
`benchmarks/omr-staves-map-2026-09/FINDINGS.md` found for its own five rows.
p2's map is structured in `works.json` verbatim; p3/p4/p5's are written out
instrument by instrument in their own `notes`. What has never happened is
anyone checking those prose allocations AS A STRUCTURED MAP against the print.

`build_cache.py` now builds them (`--research`), and `server.py` serves them
unchanged. Three things had to be added and each is marked in the diff:

* the one-line percussion bands, recovered by re-running `detect_staves` on the
  same render and spliced into the run's own numbering by `staff_index` — the
  artefact does not carry them (§2). A single rule has zero height, so the band
  is opened to the page's own line spacing; the crops read cleanly (`Gr. Tr.`
  boxed with its rule, `Becken` above and `Kl. Tr.` below);
* a proposal source for rows with no `systems_as_printed`;
* a row-level note naming every tacet fold, part by part, so a fold is visible
  as a fold rather than as an allocation.

```bash
python3 benchmarks/omr-staves-map-2026-09/build_cache.py --research \
        --cache-dir ~/.cache/reengrave-staves-map-completion       # ~6 min
python3 benchmarks/omr-staves-map-2026-09/server.py \
        --cache-dir ~/.cache/reengrave-staves-map-completion \
        --out <MAIN>/benchmarks/omr-scan-e2e-2026-09/works.staves-additions-completion.json \
        --port 5076
```

**http://127.0.0.1:5076 — 89 slots**, and they are not equal work:

| row | slots | crop per slot? | what is actually being decided |
|---|--:|---|---|
| mahler p3 | 15 | **yes** | the prose transcription, and 13 tacet folds |
| mahler p4 | 21 | **yes** | the prose transcription, 4 folds, the `get.` divisi split |
| mahler p5 | 21 | **yes** | the prose transcription, 6 folds |
| mahler p2 | 21 | no — 19 bands against 21 entries | already verbatim in works.json; one forced deletion |
| bach p1 | 11 | no — 12 bands against 11 entries | whether to record a zero-valued map at all |

**57 of the 89 slots are the ones with real confirmation value** (p3/p4/p5), and
on those the printed lineup and the detected bands agree exactly, so every slot
shows its own margin crop with the instrument name boxed — the thing that made
the last batch 58 slots in five minutes. p2 and Bach show the boxed system strip
instead, which is enough for a page whose map is already written down.

⚠️ **A separate cache directory and a separate additions file**, so nothing here
can touch the five rows already merged or the store they were decided in.

---

## 9. What was verified, and what was not

**Verified.** Phase 1 re-run on all four Mahler pages on this tree (the one-line
counts are measurements, not the memory's recollection); `page_normalise`
driven directly on all five maps, both patched and not; the fold-silence and
fold-target controls; the Dvořák identity control at exactly 0 edits; the raw
`entire staff` column reproducing `map-coverage-cost.json` to the edit; the
part-level op list opened and its parts named; the Bach source parsed with
ElementTree; `merge_additions.check_row` run on all five simulated-done rows
both ways, against a works.json it never writes; the UI built, served, and
driven — p4's slot 0 shows `Hoboen` boxed in its own margin crop, and p4's slot
12 shows the `Gr. Tr.` one-line rule with its notes.

**Not verified.** No pooled figure was re-measured and no default was changed.
`works.json` is untouched — no map here has been merged, and two of them cannot
be until §4 is fixed. The `note_recall` proposal in §7 is arithmetic about the
join, not a measurement of what `note_recall` would then report. And the
one-line percussion staves were not read: whether a single rule CAN be
transcribed is a different piece of work, which `measure_extractor`'s own
comment already calls one.
