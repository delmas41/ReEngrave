# Brahms 1's finale names a staff `Tuba`, in a work that has no tuba

**2026-09-06.** `benchmarks/omr-brahms-lineup-2026-09/FINDINGS.md` located the
residue that `OMR_SPAN_REFERENCE_FIT` does not touch: the finale lineup
`p45-85/16` reads **255/272 = 0.9375 in every arm**, with `Trombone -> Tuba`
**×17** surviving all three. The finale braces its **3 trombones over TWO
staves** (alto C clef, then bass), so slot 9 is the second trombone staff — and
the work's IMSLP roster is `3, 0` for trombones and tuba.

This session measured the mechanism, measured how general it is, and shipped a
flag-guarded veto. Every number below is reproducible from committed artefacts;
the commands are in §8.

---

## 1. THE MECHANISM, measured

`probe/why_tuba.py`, run on the committed compose blob — no re-transcription.

**Every affected staff record is `instrument_source == "score_order"`.** 102 of
102 on the whole-work run, 23 of 23 on the shipped-default run. Nothing was
read; the name was **deduced**.

The deduction, reproduced offline through the shipped `fit_layouts`:

```
labels fed to fit_layouts (n=16): 15 of the 16 slots — 14 `label`, 1 `roster`
  best layout: late-romantic-large   score/staff 6.312   voters: (that one)
   ...
    8 emitted=Trombone   src=label        fit=Trombone   agr=1.00
    9 emitted=Tuba       src=score_order  fit=Tuba       agr=1.00   <<<
   10 emitted=Timpani    src=label        fit=Timpani    agr=1.00
```

Fifteen slots are anchored by a margin label or the document roster, so the
ballot is nearly complete, one layout is the sole voter, and the single hole is
filled with the part that layout prints between a trombone and a timpani.
`late-romantic-large` prints `Tuba` there. So does `romantic`, and so does
`french-large`.

⚠️ **The prior is not being reckless — it is being confident for the right
reason and wrong anyway.** Given no labels at all it agrees on essentially
nothing on this page (`probe/continuation_direction.py`: **1 of 16** against the
hand-read truth, fourteen slots `None` under `MIN_AGREEMENT`). It only speaks
loudly when labels have pinned everything around the hole. That is exactly the
configuration in which a hole is *not* free evidence.

## 2. WHY `absent_instrument.py` DID NOT CATCH IT — two independent reasons

`probe/veto_reach.py` replays the blob's own recorded `label_evidence` through
the shipped `find_vetoes` in four arms.

| sources | anchored_exempt | total vetoes | on a Tuba slot |
|---|---|--:|--:|
| `("label",)` (shipped) | True | 16 | **0** |
| `("label",)` | False | 23 | **0** |
| `("label", "score_order")` | True | 16 | **0** |
| `("label", "score_order")` | False | 23 | **0** |

1. `VETOABLE_SOURCES == ("label",)`, stated in that module's own docstring, and
   deliberately;
2. **and widening it changes nothing.** `find_vetoes` guards on
   `if not pages: continue`, and `Tuba` is attested on **ZERO** of the 86 pages.

An attestation-locality test asks *where* a name was read. **A name that was
never read anywhere has no attestation to be local to.** The question here is a
different one — *can this name be right at all* — and it needs a different
evidence tier. Pinned by `TestTheAttestationVetoCannotDoThis`, so a future
session cannot "fix" this by relaxing `VETOABLE_SOURCES` over there and believe
it worked.

## 3. GENERALITY — and this is the part bigger than 17 edits

### 3a. The layout model can REPRESENT a two-staff section and cannot CHOOSE it

`score_layouts.ScoreLayout` documents its own convention: `parts` are "one per
STAFF as the tradition normally prints it". Three trombones over two staves is
an ordinary Romantic convention and the library has **one `Trombone` entry**.

`probe/continuation_direction.py` scores the readings as explicit layouts, on
the winning layout and the real labels:

| arm | total | /staff | slot 9 |
|---|--:|--:|---|
| as shipped (`Tuba` present) | 100.99 | 6.312 | **Tuba** |
| `Tuba` removed — the generic continuation move | 100.57 | 6.285 | Timpani |
| `Tuba` removed, `Trombone` entered twice | **100.99** | 6.312 | Trombone |
| `Tuba` removed, `Timpani` entered twice | **100.99** | 6.312 | Timpani |

Three readings of the same:

* the model **can** represent the truth — a duplicated `Trombone` entry scores
  *exactly* what the `Tuba` reading scores;
* it has **no evidence to choose** — duplicating `Trombone` and duplicating
  `Timpani` are numerically identical, to the hundredth;
* its generic continuation move (`EXTEND_PENALTY`, the two-horns-on-two-staves
  case) is **strictly worse** than naming the next part, so it never wins where
  a part is available.

⚠️ **THIS FALSIFIES THE OBVIOUS REPAIR, and that is the most useful result
here.** "Filter the layout's parts by the work's roster, then let the existing
continuation move do the work" is elegant, needs no new evidence, and **gives
`Timpani`** (`probe/counterfactuals.py`, `constrain` arm). One wrong name for
another. Do not re-try it without new evidence about *which* neighbour
continues; the tie is exact, not marginal.

### 3b. The exposure, over every roster the catalog holds

`probe/generality.py`, 213 works with a parsed catalog roster:

* **the exact Brahms shape — roster holds `Trombone`, lacks `Tuba` — is 42 of
  213 works (19.7%)**: Beethoven 5, 6 and 9, Berlioz *Fantastique*, Bizet,
  Missa Solemnis …;
* every adjacent `(part the work has, part it lacks)` pair the ten layouts can
  produce, top of the list: `Timpani -> Percussion` 380 works,
  `Oboe -> English horn` 322, `Clarinet -> Bass clarinet` 284,
  `Trumpet -> Trombone` 189, `Bassoon -> Contrabassoon` 154,
  `Flute -> Piccolo` 135, **`Trombone -> Tuba` 126**, `Trumpet -> Tuba` 104.

So the *shape* is common. The *live cost*, over the two whole-work runs that
exist, is not:

| run | slot sources | off-roster `score_order` slots | staff records |
|---|---|---|--:|
| Brahms 1 / Breitkopf, shipped | 14 label, 1 roster, 1 score_order | `{9: Tuba}` | **23** of 1927 |
| Brahms 1, spans-off | 14 label, 1 roster, 1 score_order | `{9: Tuba}` | 31 of 1927 |
| Beethoven 5 / Litolff, whole work | 16 label, 1 score_order_ambiguity | `{}` | **0** of 1616 |

⚠️ **Beethoven 5 is a clean control and not a coincidence**: it has no plain
`score_order` slot at all. The fault needs a lineup the margin labels *nearly*
cover, and it fires where a section is braced over more staves than the layout
holds entries for.

## 4. THE FIX — `tools/omr/offroster_name.py`, `OMR_ROSTER_SCORE_ORDER_VETO`

    A slot whose name the score-order prior DEDUCED may not name an instrument
    the work's roster does not contain. The slot is left UNNAMED.

A veto, never an assignment — the shape of `absent_instrument.py`, the ledger
ladder and the written-range veto. `score_order` only: `score_order_ambiguity`
is a label the prior *disambiguated* and `roster` is a name printed on the
document's own roster system, and vetoing either would discard a reading rather
than a deduction.

**Graded against the hand-read truth** (`score_brahms_lineups.py`, the arms
sharing one 1927-key staff-record set, which it asserts on):

| arm | judgeable | correct | wrong | unnamed | rate |
|---|--:|--:|--:|--:|--:|
| shipped defaults | 764 | 741 | 23 | 0 | 0.9699 |
| **+ the veto** | 764 | **741** | **6** | 17 | 0.9699 |

* **all 17 `Trombone -> Tuba` removed**, wrong 23 → 6;
* **zero correct names lost** — `correct` is identical at 741;
* the four residual confusions (`Trumpet -> Horn` ×2, `Timpani -> Trumpet` ×2,
  `Violin -> Timpani` ×2) are untouched: they are on-roster names in the wrong
  slot, which this rule has, and should have, no opinion about.

⚠️ **The `rate` column does not move, and that is honest rather than
disappointing.** A refusal converts a wrong name into an unnamed staff; it
cannot create a right one. `correct/judgeable` is blind to the difference and
the `wrong`/`unnamed` split is where the change lives — the same asymmetry
`benchmarks/omr-brahms-lineup-2026-09` records between a correct/wrong grade
and an impossible count.

The shipped-baseline row reproduces `omr-brahms-lineup`'s recorded `fit-search`
figures **exactly** (741 / 23 / 0.9699, same four confusions), which is the
control that says this tree is the tree those numbers were taken on.

## 5. ⚠️ THE MEASUREMENT OVERTURNED THE FIRST CUT OF THE RULE

The first version carried `absent_instrument.py`'s **"the staff speaks for
itself"** exemption — a staff the reader named on this page is never touched.
Copied without thinking, and **it is backwards here.**

Over there, the name under veto came FROM a label elsewhere, so the staff's own
label is **corroboration**. Here the name is a DEDUCTION, so the staff's own
label is a **CONTRADICTION** — and exempting on it protects a wrong name using
the very evidence that disproves it.

`probe/exempted_records.py`, on the shipped run: the exemption spares 8 of the
23, and what those staves' own margins say is

```
  the page says Trombone -> we export Tuba   x4
  the page says Trumpet  -> we export Tuba   x3
  the page says Timpani  -> we export Tuba   x1

  the FULL finale systems among them (the graded population):
    p68 sy0 staff 9  page says Trombone   truth says Trombone
    p75 sy0 staff 9  page says Trombone   truth says Trombone
    p81 sy0 staff 9  page says Trombone   truth says Trombone
    p82 sy0 staff 9  page says Trombone   truth says Trombone
```

Graded, the exemption leaves **4 of the 17** standing for nothing:

| arm | correct | wrong | unnamed | `Trombone -> Tuba` left |
|---|--:|--:|--:|--:|
| shipped | 741 | 23 | 0 | 17 |
| veto, exemption ON | 741 | 10 | 13 | **4** |
| veto, exemption OFF (shipped rule) | 741 | 6 | 17 | **0** |

The clause is removed and the staff's own label is kept on the veto record as
`read` — reported, never acted on. `label_contradiction` reports the same four
independently, from the other direction. `test_the_staffs_own_label_does_NOT_exempt_it`
pins the reversal so it cannot be "restored" as a tidy-up.

## 6. BLAST RADIUS — provably the exported part name, and nothing else

Checked mechanically, not by reading, because it is what makes this priceable
without running either benchmark family:

* `contextual._not_clef_evidence = {"score_order"}`, so `read_instruments` —
  the **only** instrument map `clef_correction` is ever handed — cannot contain
  a deduced slot. Both `correct_clefs_from_instruments`' FILL path and its
  `treble_override` path are unreachable for one (the latter twice over: it
  also tests `sources.get(slot) == "label"`). ⚠️ Worth stating because the FILL
  path is **not** gated on source at its own call site — the gate is upstream,
  in the map that is passed;
* `_dedupe_cross_staff_detections`' written-range veto runs before the
  contextual pass and off the dossier, not off these names — and CLAUDE.md
  already records that it has never fired on a scan;
* `label_contradiction` and `transcribe` only REPORT the source.

So the change alters `<part-name>` and the reports. **musicdiff does not score
`<part-name>`** (measured by the roster-wiring session: 15 truth part names
rewritten to a bogus value for 0 edits). Pinned by
`test_the_blast_radius_is_the_exported_name_and_nothing_else`.

### The controls, run

| control | result |
|---|---|
| flag **off**, spans off + on, vs the committed shipped run | **byte-identical** ×2 |
| flag **on**, spans off + on, same comparison | **byte-identical** ×2 |
| `tools/omr/tests/` | 2427 passed, 1 pre-existing failure |
| nine mechanism breaks | **all RED** (`probe/verify_red.sh`) |

⚠️ **Flag ON is byte-identical too, and that is the headline of this section.**
`work_roster.py` — the roster supplier — is on a sibling branch and not in this
tree, so the wiring's import fails, `admissible` is None, and the layer
abstains. **Turning the flag on today changes nothing anywhere.** That is
correct behaviour and it is also precisely the shape of a change that looks live
and is not, so it was checked rather than assumed.

⚠️ The one suite failure is `test_direction_text.py::TestReaderSelection::
test_the_env_var_restricts_the_rungs`, **pre-existing and environmental** —
verified by re-running it with this session's changes stashed. It is the
documented worktree `.venv-surya` trap.

### And the wiring, proven end to end

`probe/run_with_stub_roster.py` installs a test double under the name the wiring
imports and runs the real `compose.py` unchanged. It agrees with the offline
replay **record for record — 23 of 23, 0 wired-only, 0 offline-only** — and the
summary carries `work_id=brahms--symphony-1`, `roster` present, 13 names.

⚠️ The **staff-dict** half is not exercised by that probe and the probe says so
rather than reporting a silent zero: `compose.py` builds its result as
`[{"page_index": i, "systems": []}]` and feeds staves in through `staved=`, so
the loop that writes `instrument_veto` iterates nothing. Guarded by
`TestTheWiring`'s source-level anti-drift tests instead, both verified RED.

## 7. COORDINATION — the roster-label agent's work does NOT supersede this

Checked against `claude/roster-constrained-labels`
(`benchmarks/omr-roster-constrained-labels-2026-09/FINDINGS.md` and
`tools/omr/work_roster.py`, read in that worktree). Its layer **"runs at the
margin-label boundary only"** — four outcomes, all of them about what a label
that was READ resolves to: recovered, disambiguated, vetoed, unchanged.

**Slot 9 has no label at all.** Its name is a deduction made where the reader
found nothing, so nothing that decides between readings can reach it. The two
layers are complements on the same evidence tier and neither is the other:

| | acts on | supplies |
|---|---|---|
| `work_roster` + `contextual._labels_for_page` | a label the reader READ | a better name |
| `offroster_name` (this) | a name the prior DEDUCED | a refusal |

**No second roster reader was built.** `offroster_name.py` takes `admissible`
as an argument, reads no catalog, and the wiring imports `work_roster` — so it
is inert until that branch lands and live the moment it does, with no further
work. `test_it_reads_no_catalog_of_its_own` pins the boundary.

### What I need

1. **`work_roster.py` on main.** That is the whole dependency; the flag cannot
   fire without it. Nothing about the interface needs to change —
   `roster_for_pdf(pdf) -> WorkRoster | None` with `.instruments` and
   `.work_id` is exactly what the wiring calls.
2. **Confirmation that `contextual.py` is not being edited by another agent**
   in the veto region (the block between `absent_instrument_veto` and
   `label_contradiction`). The roster-labels agent touches
   `contextual._labels_for_page`, which is a different function, but this is
   worth saying out loud rather than discovering in a merge.
3. **A decision on the default is NOT requested yet.** It should stay off until
   someone prices it on a second work with a live roster. Brahms 1 is n=1.

## 8. Reproducing

```bash
# the mechanism, offline, from committed artefacts                  (~2 s each)
python3 benchmarks/omr-brahms-tuba-2026-09/probe/why_tuba.py \
    benchmarks/omr-slot-alignment-2026-09/out/brahms1/-ordinal-spans-on.json
python3 benchmarks/omr-brahms-tuba-2026-09/probe/veto_reach.py \
    benchmarks/omr-slot-alignment-2026-09/out/brahms1/-ordinal-spans-on.json
python3 benchmarks/omr-brahms-tuba-2026-09/probe/counterfactuals.py \
    benchmarks/omr-slot-alignment-2026-09/out/brahms1/-ordinal-spans-on.json
python3 benchmarks/omr-brahms-tuba-2026-09/probe/continuation_direction.py \
    benchmarks/omr-slot-alignment-2026-09/out/brahms1/-ordinal-spans-on.json
python3 benchmarks/omr-brahms-tuba-2026-09/probe/generality.py \
    benchmarks/omr-slot-alignment-2026-09/out/brahms1/-ordinal-spans-{on,off}.json \
    benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json

# a fresh whole-work arm off the committed read cache                   (~20 s)
bash benchmarks/omr-brahms-tuba-2026-09/probe/run_shipped.sh

# apply the rule offline, then grade against the hand-read truth         (~5 s)
python3 benchmarks/omr-brahms-tuba-2026-09/probe/price_offline.py \
    benchmarks/omr-brahms-tuba-2026-09/out/run/-shipped-spans-on.json \
    benchmarks/omr-brahms-tuba-2026-09/out/run/veto.json
python3 benchmarks/omr-brahms-lineup-2026-09/probe/score_brahms_lineups.py \
    shipped=benchmarks/omr-brahms-tuba-2026-09/out/run/-shipped-spans-on.json \
    veto=benchmarks/omr-brahms-tuba-2026-09/out/run/veto.json --veto on

# what the removed exemption used to spare                               (~2 s)
python3 benchmarks/omr-brahms-tuba-2026-09/probe/exempted_records.py \
    benchmarks/omr-brahms-tuba-2026-09/out/run/-shipped-spans-on.json

# flag off / flag on are both no-ops, byte for byte                     (~25 s)
bash benchmarks/omr-brahms-tuba-2026-09/probe/control_flag.sh

# the wiring, end to end, with a stubbed supplier                       (~20 s)
python3 benchmarks/omr-brahms-tuba-2026-09/probe/run_with_stub_roster.py
python3 benchmarks/omr-brahms-tuba-2026-09/probe/check_stub_blob.py \
    benchmarks/omr-brahms-tuba-2026-09/out/stub/wired-spans-on.json \
    benchmarks/omr-brahms-tuba-2026-09/out/run/veto.json

# every test verified RED by breaking the mechanism it guards            (~8 s)
bash benchmarks/omr-brahms-tuba-2026-09/probe/verify_red.sh
```

Committed under `out/`: `grade-final.txt` is §4, `grade-shipped.txt` is the §5
exemption A/B, `grade-veto.txt` is the same A/B on the older pre-span-fix blob,
`verify-red.txt` is §6's nine breaks. The intermediate exemption-arm blobs are
NOT committed — they are one flag away and reproducible in five seconds — and
neither is `out/control/`, whose whole content is that it is byte-identical to
`out/run/`.

⚠️ The read-pass cache and `library/` are machine-local and gitignored. From a
worktree the paths in `probe/run_shipped.sh` point at the main checkout and at
the veto-pricing session's `cache600`; **an absent cache reads exactly like a
slow run, not like an error.** The wall time printed by those scripts is the
tell — 20 s is cached, minutes is not.

## 9. What is NOT measured, stated plainly

* **n=1 work.** The rule fires on Brahms 1 and on nothing else that has been
  run whole. 42 works share the shape and none of them has a whole-work run.
* **The engraved 11-work benchmark and the 20-row scan gate were not run**, and
  running them would have measured nothing: the flag is off, the layer is inert
  without `work_roster`, and part names do not reach OMR-NED (§6). The
  substitute is the mechanical blast-radius argument, which is pinned by a test
  rather than asserted here.
* **Whether a refusal is what we want long-term.** The right answer for slot 9
  is `Trombone`, and §3a shows the layout DP is exactly indifferent between the
  two continuations. A rule that picks one needs evidence this session did not
  find — and the obvious count argument (the roster says Trombone ×3 and
  Timpani ×1, so only the trombones can spread) is refused for now on
  CLAUDE.md's own warning that **N instruments is not N staves**, with harp,
  piano and organ as standing counter-examples to a count-1-cannot-spread rule.
