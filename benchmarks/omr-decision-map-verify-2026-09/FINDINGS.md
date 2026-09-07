# Adversarial verification of `docs/architecture-decision-map.md`

**Commissioned 2026-09-07** — Sean: *"I would want the map to be double checked
because of how crucial it is that we get it right."* The map (1,303 lines,
committed `dca9f44c`, line numbers stamped at `e1107b5b`) is intended as a
checkpoint every future agent reads before building, so a wrong entry in it will
be believed and built on.

**No pipeline behaviour was changed.** This is documentation plus two read-only
scripts (`probe_orphan_modules.py`, `probe_env_surface.py`). No benchmark was
run: every finding below is a code-level or grep-level fact, reproducible in
seconds. Verified against `6c7ac1e1` (11 commits after the map's stamp; nothing
in that range touches `CLAUDE.md` or the modules audited except the map itself).

---

## 0. Verdict in one paragraph

**The map is substantially sound and its mechanical half is unusually
accurate.** Every spine line number I spot-checked lands exactly on the named
call; all three circularity refusals are real and correctly directed; the
`export.py`-reads-no-confidence claim survives an adversarial re-grep; the
gate-location correction (D4) that overturns both CLAUDE.md and
`scope-identity-upstream` is exactly right. **Sean's own suspicion about D9 is
refuted** — that entry is correct and names a second, still-stale docstring.

What it gets wrong is **negatives about consumers**, in four places, and one of
those is load-bearing. What it is **missing** is larger than what it gets
wrong: §5 silently drops three whole stages it names in its own spine, and six
of its twelve tables omit the `CONSUMED BY` column — the column §0 calls the
reason the document exists — in exactly the half of the pipeline §9.5 tells
agents to build in.

---

## 1. Coverage — what I checked, and what I did not

| claim class | in the map | checked | hold | wrong / partial | not checked |
|---|--:|--:|--:|--:|--:|
| §8 code-vs-prose disagreements (D1–D27) | 27 | **27** | 24 | 3 | 0 |
| §7.4 dead-code claims | 11 items | **11** | 8 | 3 | 0 |
| §6.1 `NOBODY` keys | 7 | **7** | 7 | 0 | 0 |
| §6.1 `SERIALISED-ONLY` / `TEST-ONLY` spot checks | ~30 | 9 | 8 | 1 | ~21 |
| §6.2 application-boundary claims | 3 | **3** | 2 | 1 | 0 |
| §5 "→ NOBODY" / "→ tests only" consumer columns | ~14 | 9 | 6 | 3 | ~5 |
| §5 structural claims (gates, returns, unreachability) | ~25 | 14 | 14 | 0 | ~11 |
| §2 spine line numbers | 21 | 6 | 6 | 0 | 15 |
| §10 `verify.py` checks V1–V7 | 7 | **7** | 6 | 1 | 0 |
| §5 numeric measurements (4,521 contests; 29.7%; 0.617 CI…) | ~20 | 0 | — | — | **~20** |

**≈ 93 entries checked thoroughly of ~120 decision rows plus ~60 auxiliary
claims.** Call it a thorough pass over the *falsifiable-by-reading* half and
**no pass at all over the measured half**.

### 1.1 What I could NOT verify, stated plainly

- **Every quoted measurement.** 4,521 contested pairs / 94.1% by distance;
  29.7% of scan detections under 0.40; confidence-vs-ladder agreement 0.617
  [0.558, 0.674] n=264; 45/45 and 8/8 refused dynamic runs; reach 7/193 and
  precision 0/11 for `clef_register_warning`; 158 `label_contradiction`
  firings; the +51-records clef-channel result. I confirmed the **backing
  artefacts exist** (`benchmarks/omr-additive-vs-gated-2026-09/out/` holds
  `gate-reach.txt`, `register-warning.txt`, `dynamic-runs.txt`,
  `clef-proposals.txt`, `propose-clef-branches.txt`, `contests/`) and that two
  spot figures reproduce verbatim from them (`29.7%` at `gate-reach.txt:64`,
  median notehead `0.733` at `:79`). **I did not re-run a single arm.** A
  cached-A/B or a stale-corpus fault in those probes would be invisible to me.
- **The 12-of-21 spine rows I did not open**, and ~11 §5 structural claims.
- **Stages 1, 5, 6, 7 decision rows** beyond spot checks — my independent
  enumeration went to `pitch_resolver`, `direction_text`, `condensed_parts`,
  tie pairing and slur pairing, not to `staff_detector` or `rhythm`.
- **Whether the map's ~120 count is right.** I did not count its rows against a
  full independent enumeration of the whole pipeline; §4 below shows the count
  is at best incomplete in three named places.

---

## 2. Errors found, with evidence and correction

Ordered by how much they could mislead someone building on them.

### E1 ⚠️ LOAD-BEARING — `nominal_line_spacing_px` IS read in production

**Map, §5 Stage 3 note:**

> `Staff.nominal_line_spacing_px` exists specifically so such a staff could
> size its windows, **and no production site reads it.** This is backlog item
> C3 with its three locations.

**The tree.** It is read at `tools/omr/types.py:102`, inside the
`Staff.line_spacing_px` **property**:

```python
    @property
    def line_spacing_px(self) -> float:
        if len(self.line_ys) < 2:
            return float(self.nominal_line_spacing_px or 0.0)
```

and `Staff.line_spacing_px` has **15 production readers**, including
`system_grouping.py:237` and `:299` (`max(upper.line_spacing_px,
lower.line_spacing_px)` — the crossing band's scale), `:255`, `:357`, `:370`,
`:601`, `staff_detector.py:671`/`:755`, `measure_extractor.py:152`/`:772`/`:973`
and `direction_text.py:270`.

So a one-line percussion staff bordering an inter-staff gap **already
contributes its nominal spacing to system grouping's band geometry**. The value
is live, not dormant.

**Why the map missed it:** a direct grep for the field name finds only the
write site and the property; the consumption is transitive through a property —
exactly the indirection the audit brief names.

**Why it matters:** this is the entry the one-line-staves workstream would read
first. Acting on "no production site reads it" — by wiring it up — would change
`system_grouping`'s scale on pages that mix one-line and five-line staves,
believing the change to be inert.

**Correction applied** to the map.

⚠️ The map's *surrounding* claim is right and unaffected: the three `>= 5`
guards at `measure_extractor.py:464`, `:1148`, `:1471` are exactly there.
**There is a fourth**, `:849` (`len(other.line_ys) < 5`), which the map does
not name; "three locations" undercounts.

### E2 ⚠️ LOAD-BEARING — `musicxml_builder` is on the Claude Vision path, not the local-OMR boundary

**Map, §6.2** ("The application boundary — ten fields of a 67k-detection
JSON"):

> `musicxml_builder.py` reads `clef`, `key_signature`, `time_signature`,
> `pitch`, `dots`, `articulations`.

**The tree.** `grep -rn "musicxml_builder" backend` → imported by
`backend/modules/claude_vision_omr.py:29` and its own test, **and by nothing
else**. `local_omr.py` never touches it. Its schema is the Vision engine's, not
the pipeline's: `data.get("staves")` at top level, `s.get("staff_id")`,
`s.get("instrument_name")`, `m["staves"][…]["voices"][…]["elements"]`
(`musicxml_builder.py:581-626`) — a shape `transcribe` never emits. CLAUDE.md
agrees: *"musicxml_builder.py # JSON → MusicXML serializer (used by Vision
OMR)"*.

**Why it matters:** §6.2's conclusion is that *"the entire identity layer …
never cross[es] into the application at all"*. That conclusion is **correct and
in fact stronger than stated** — but the `musicxml_builder` sentence sitting
inside the same paragraph implies the local pipeline's `clef` / `pitch` /
`key_signature` do reach the app. An agent asking "will my clef fix show up in
the web app?" gets the wrong answer from this paragraph.

**Correction applied.**

### E3 — three `NOBODY` cells in §5 that are `probe` by the map's own legend

The legend (§5) is explicit: **`NOBODY`** = nothing reads it anywhere;
**`probe`** = only a benchmark or test.

| §5 row | map says | the tree |
|---|---|---|
| `_drop_clipped_notehead_fragments:558` | "a count → **NOBODY**" | `n_clipped_notehead_fragments_dropped` read by `benchmarks/omr-ned-2026-08/probe_edge_fragments.py:76` and `.../probe_gate_reach.py:81` ⇒ **probe** |
| `_drop_unladdered_noteheads:3098` | "a count → **NOBODY**" | read by `probe_gate_reach.py:80` ⇒ **probe** |
| `_drop_furniture_measures:3032` | "a count → **NOBODY**" | ✅ correct — `n_measures_dropped_as_furniture` has zero readers anywhere |

§6.1 classifies the first two correctly under `SERIALISED-ONLY`, so **§5 and
§6.1 disagree with each other**. The distinction is not cosmetic: a signal a
probe already reads can be priced from disk, and a signal nothing reads cannot
— which is precisely the difference §9.5 item 1 turns on.

**Correction applied.**

### E4 — §7.4's "zero callers" is "zero *production* callers"

`Decision.names_a_staff`, `Match.is_ambiguous`,
`LocatedTimeSignature.as_dict` and `staff_header.extract_header_cell` are each
listed as **"zero callers each"**. Each has 2–3 test callers
(`test_work_roster.py:136,226`; `test_instruments.py:641,643,647,736`;
`test_time_signature_locator.py:191,194,197`; `test_staff_header.py:180,187`).
The map has the vocabulary for this (`probe`) and did not use it here. Same
class: `template_matcher.detect_symbols` is called by **two** annotate tools
(`build_template.py:34`, `port_verdicts.py:39`), not "one".

Substance unaffected — none is production-live — but "zero callers" invites a
deletion that would break the suite.

### E5 — `confidence_label`'s "zero readers anywhere in the tree" is overstated

**Map, §6.1:** *"**`confidence_label`: nine write sites, zero readers anywhere
in the tree.** … the purest dead field in the schema."*

`clef_correction.py:627` reads `proposal.confidence_label` (a serialisation
pass-through into `clef_proposal`), and it is read by 13 test assertions across
`test_key_signature.py`, `test_transcribe_helpers.py`, `test_clef_register.py`,
`test_time_sig_agreement.py`, plus
`benchmarks/omr-system-grouping-2026-08/eval_clefs.py:68` and
`probe_gate_reach.py:126`.

The map's *point* — **no decision consults it** — is correct and survives
verbatim. "Anywhere in the tree" does not.

**Correction applied** (narrowed to "no decision reads it").

### E6 — `verify.py`'s V4 silently undercounts the env surface it exists to police

V4 (`verify.py:126-143`) scans `tools/omr/*.py` for the literal
`os.environ.get("OMR_…")` — not `rglob`, and not any other read form.
`probe_env_surface.py` (this directory) runs the wider scan:

```
V4 sees            : 37
wider scan sees    : 41
missed by V4       : OMR_ABSENT_INSTRUMENT_VETO, OMR_CELL_LINE_TRACE,
                     OMR_EVAL_INDENT_MM, OMR_ROSTER_SCORE_ORDER_VETO
undocumented (wide): 20   (V4 reports 17; the map's D24 says 16)
```

`OMR_ABSENT_INSTRUMENT_VETO` is missed because its name lives in a constant —
`absent_instrument.py:85: ENV_VAR = "OMR_ABSENT_INSTRUMENT_VETO"` — and is
never inlined. That is a **default-ON behaviour flag the map's own D24 names as
important**, and D24's list is right about it only because a human wrote the
list; a future `--json` re-run would drop it in silence.

Two smaller D24 faults: the list names `OMR_SPAN_REFERENCE_FIT` as
undocumented, but CLAUDE.md mentions it at line 1609 (in prose, not the env
table — the claim is true of the *table* and false as written of the file); and
the counts have drifted 36→37 / 16→17 with `OMR_LINEUP_SWAP_SPLIT` landing,
which the map anticipates ("V4 and V7 are *supposed* to change").

**Correction applied** to D24.

### E7 — D25 and D26: the substance holds, the universals do not

Both were checked in full.

- **D25** — *"`OMR_TAIL_RULE` is bound at import time … so **unlike every other
  flag** it cannot be changed per call."* The binding is real
  (`dossier.py:521`, consumed directly at `:550`/`:552`). The universal is
  false: `staff_labels_surya.py:77` and `:91` bind `OMR_SURYA_TIMEOUT_S` and
  `OMR_SURYA_KEEP_ALIVE` at import too. What *is* unique to `OMR_TAIL_RULE` is
  that it has **no per-call escape** — the Surya pair are used as
  `X if arg is None else arg` defaults (`:242`, `:248`, `:307`, `:314`).
- **D26** — *"the `"before"` branch at `:2669` is **unreachable**."* It is dead
  on every production and test path (`_WEDGE_START_RULE` has exactly two
  occurrences, `export.py:2587` and `:2668`, no env read, no reassignment in
  `tools/`), but it is reachable by
  `benchmarks/omr-hairpins-2026-09/probe_stop_rule.py:101`, which monkeypatches
  the module global — and **that probe is where the 1-of-8 vs 4-of-8 figures in
  the constant's own comment came from**. It is a retained A/B arm, not dead
  code.

**Corrections applied** to both.

### E8 — a 28th code/prose disagreement the map does not have

`export._paired_spans`, `export.py:2476-2482`:

```python
        # Both ends must belong to the same voice, for the same reason: the
        # two halves of a span split across voices are each unpaired. Prefer
        # the longest run the curve covers WITHIN one voice over dropping it.
        voice = voice_of.get(id(covered[0][2]), 0)
        in_voice = [c for c in covered if voice_of.get(id(c[2]), 0) == voice]
```

The comment promises the **longest** covered run within one voice. The code
takes the voice of `covered[0]` — the **first** head — and discards the rest.
Where an arc covers one head of voice 1 and three of voice 2, the code keeps
one, fails the `< 2` test two lines later, and drops the slur; the documented
rule would have kept it. Exactly the D11/D13 family.

**Added to the map as D28.**

### E9 — `condensed_parts` has no production producer, so `OMR_CONDENSED_PARTS` is inert

**Map, §5 Stage 11:** *"`condensed_parts.players_for_label` has four evidence
tiers … and **only the integer travels onto the staff dict**, so export cannot
weigh `Corni I.II.` against a bare `Flauti`."*

The integer does not travel. Nothing in `tools/` or `backend/` calls
`players_for_label`; the only importers are `test_condensed_parts.py` and three
benchmark scripts. Nothing in `tools/` writes the `condensed_parts` staff field
either — the sole writer is
`benchmarks/omr-condensed-parts-2026-09/run_arms.py:133`. So in a production run
`_condensed_count` (`export.py:3313`) always sees `{1}` and returns 1,
**whatever `OMR_CONDENSED_PARTS` is set to**.

This is consistent with CLAUDE.md ("blocked on a count source") and with the
flag being off — but the map's phrasing states a live data path that does not
exist, and the fact that the *knob itself is a no-op* is more useful to a
builder than the fact that the tier is lost.

Found independently twice: by tracing the field's writers (me) and by tracing
the module's call sites (the enumeration pass). Different substrates, same
conclusion.

**Correction applied.**

### E10 — §7.4's orphan list is missing two modules, one of them 390 lines

`probe_orphan_modules.py` asks which `tools/omr/*.py` have no production
importer. After removing four false positives I checked by hand — `_surya_worker`
(invoked as a **subprocess by path**, `staff_labels_surya.py:68`),
`run_pipeline` (a `python3 -m` CLI entry point), `_omrned_worker` (runs inside
`.venv-omrned`), and the four `page_truth` / `score_reading` /
`score_translation` measurement modules §11 puts out of scope — what remains is:

| module | lines | map lists it? |
|---|--:|---|
| `hairpin_detection.py` | 344 | ✅ §7.4 and the graph |
| `template_matcher.py` | (partial orphan) | ✅ §7.4 and the graph |
| **`bracket_reader.py`** | **390** | ❌ **not named anywhere in the map** |
| **`condensed_parts.py`** | **127** | named only as a *consumed* dependency (see E9) |

`bracket_reader.py` is the same shape as `hairpin_detection.py` — a complete,
tested, benchmarked classical-CV reader with no call site — and it is the
larger of the two. Its own docstring is honest (*"Nothing in the pipeline
consumes this module"*), which makes it a smaller hazard than
`hairpin_detection`'s, but §7.4 is the section an agent reads to answer *"is
this already written?"*, and §9.5's closing warning is precisely about building
a duplicate of an already-landed reader. A bracket-structure workstream reading
§7.4 today would not learn that 390 lines of it exist.

**Correction applied** — both added to §7.4 and to the graph's orphan set.

### E11 — the `clef_register_warning` verdict is stated flatter than its evidence (standing rule A00)

Not an error of fact; an error of framing, under the rule that landed today
(`docs/backlog-2026-09-07-open-items.md` §A00: *a worse score does not condemn
the mechanism*).

The map says **"Do not resurrect it"** twice, flatly (§4.2 Cycle 3, and the
consistency-checks table). The underlying measurement
(`docs/scope-identity-upstream-2026-09-06.md:293-341`, backed by
`out/register-warning.txt`) is **reach 7 of 193 scan staves and precision 0 of
11** — a refutation of *one form*, the adjacent-pair comparison, on **n = 11
firings**. The scope doc itself says "in every form tried so far", and the
map's own §9.4 names two untried variants (restricted to one bracket group; a
staff against its own reading on other systems).

So the map contradicts itself between §4.2 and §9.4, and the flat half is the
one an agent will read first. **Correction applied**: both flat statements now
name the form measured.

Same shape, **not** corrected because it is a judgement call I am not equipped
to make: §5 and §9.4 both cite `OMR_ROSTER_RANGE_VETO` as off "at 52 swaps for
+24 edits" with no A00 caveat, and `+24 edits` is an OMR-NED delta — the exact
quantity A00 says must be interrogated before it condemns a mechanism.
`OMR_SLOT_STITCH`, which CLAUDE.md documents as a *metric artefact* rather than
a real regression, sits one section away and the map does not connect them.
**Proposed**, not applied: §5's `_apply_roster_range_veto` row should say
whether the +24 was ever attributed, or say that it was not.

---

## 3. What HOLDS — the load-bearing checks that survived attack

Stated because a verification that only reports errors is not a verification.

- **V1 survives an adversarial re-grep.** `export.py` contains the string
  `confidence` exactly once (a comment at `:1003`), and there is no aliased
  read: `grep -n "conf\b|\"conf\"|\.conf" tools/omr/export.py` → one comment at
  `:870`. The exporter genuinely never reads a detection confidence.
- **All three circularity refusals stand and are correctly directed** —
  `clef_correction.py:396`, `dossier.py:434`, `score_layouts.py:682`, verified
  by `verify.py --only V5` and by reading each. The map's observation that the
  two directions are *asymmetric* is right.
- **D4 is right and overturns two documents.** `do_apply = apply and not
  detected` at `clef_correction.py:610` (FILL, no source gate);
  `sources.get(slot) == "label"` at `:616`, inside the OVERRIDE branch; the real
  fill blocker is caller-side at `contextual.py:1380`
  (`_not_clef_evidence = {"score_order"}`, plus `roster` unless
  `OMR_ROSTER_CLEF`). The consequence the map draws —
  `score_order_ambiguity` reaches FILL and is blocked from OVERRIDE — follows
  exactly.
- **⚠️ D9 is NOT stale, and the suspicion about it was wrong.** The brief noted
  that `OMR_BRACKET_COLUMNS` was flipped ON in `ca143c26` with a rewritten
  docstring, so D9 looked at best stale. Two facts: `ca143c26` is an **ancestor
  of the map's own stamp `e1107b5b`** (18:42 vs 19:30 on 2026-09-06), so the map
  was written against the flipped tree; and D9 does not cite the flag's own
  docstring. It cites **`assign_systems`'s** docstring, which still reads
  ``` `OMR_BRACKET_COLUMNS` (default OFF) changes only the last step ``` at
  `system_grouping.py:657`, while `_bracket_columns_enabled`'s docstring at
  `:484` correctly says "DEFAULT ON since 2026-09-07". Both are true at once —
  the same two-docstring split D7 records for `OMR_CHOIR_GROUPING`. **D7, D8,
  D9, D10 all hold**, verified line by line.
- **Spine line numbers are accurate.** Six of the 21 §2 rows opened at random
  (`:4615`, `:4704`, `:4769`, `:4939`, `:4970`, `:4995`) each land exactly on
  the named call. The confidence-fetch citation `:2801-2802` in the `_dedupe`
  row is exact to the line.
- **`staff_labels_human` really is unreachable, including through
  indirection.** `transcribe.py:4006` only ever builds
  `Assist("vision" | "none")`; `Assist.switch` is called only from *inside*
  `staff_labels_human.py` (`:143`, `:146`) and only ever switches **away** from
  human. Nothing escalates into it.
- **`locate_clef(trace=…)` is passed by no production call site** (`:1677` and
  `:4286`; the only `trace=` caller is `test_clef_locator.py:344`), and
  `LocatedClef.symmetry` is read by nobody — production reads `.read.name` only.
- **`locate_key_signature`'s `occupied_boxes` is a dead path** —
  `transcribe.py:1375` passes clef and cell only.
- **`pitch_candidates` is written, `pop`ped unread at `clef_correction.py:312`,
  and read only by `tools/maestro_bridge/re-rank.ts`.** `grep -c
  pitch_candidates tools/omr/export.py` → 0.
- **`align` returns `list[int]`** and `dp[m][n]` is discarded
  (`slots.py:520-542`). **`propose_clef` has exactly five `return`s**
  (`:232`, `:245`, `:262`, `:266`, `:274`).
- **All seven §6.1 `NOBODY` keys have zero readers** —
  `n_measures_dropped_as_furniture`, `clef_overridden_by_dossier`,
  `key_signature_final`, `time_signature_final`, `contextual.clef_fills`,
  `contextual.dossier_clefs`, and the per-measure `rhythm_reconciliation`
  record (only the `n_rhythm_reconciliations` counter is read).
- **§6.2's `local_omr.py` list is exact** — the ten fields, no more, verified
  by reading every `.get(` in the file; `rhythm_sum_warning` really is consumed
  at `:360` as a boolean presence count.
- **The frontend reads zero OMR-result keys**, as claimed.
- **D1–D3, D5, D6, D10–D23, D27 all hold as written**, each re-derived from the
  code rather than from the map's citation.

---

## 4. What the map is MISSING — from independent enumeration

The map's §11 says: *"Scope was cut uniformly in **depth** rather than by
dropping stages, per the commission."* **That is false, and the holes are not
in known places.**

An enumeration made **from the code alone, without reading the map**, over
three modules and four functions produced **185 decision points**. Diffing:

| area | independent count | §5 rows | in §2's spine? | in §11's cut list? |
|---|--:|--:|---|---|
| `pitch_resolver.py` | 25 | 2 | ✅ stage 6 | — (depth cut, fair) |
| **`direction_text.py`** | **72** | **0** | ✅ stage 9′ | ❌ **no** |
| `condensed_parts.py` | 17 | 0 (1 consumer row) | — | ❌ no |
| **tie pairing** (`_pair_ties_in_staff` / `_in_cell`) | **25** | **0** | ✅ stage 4b | ❌ **no** |
| **slur merge + pairing** (`_merge_arcs_across_barlines`, `annotate_slurs_in_slot` and callees) | **46** | **0** | — (export) | ❌ **no** |

`grep -n "direction_text\|_pair_ties\|_merge_arcs\|annotate_slurs" docs/architecture-decision-map.md`
returns five hits: three in §2/§3.1 (the spine and one dependency row), one in
§6.1's key list, one in D19. **§5 — the decision catalogue — contains not one
row for any of them.**

Three of the omitted decisions are the map's own thesis pattern, undocumented:

1. **`direction_text.read_directions:801` — `accepted[0]`.** The winning OCR
   rung is chosen by **list position**, not by any score, and the rung
   disagreement is computed at `:802-809` and recorded only in the report.
   Class D over a Class C. Worse, the `Reader` type at `:614` is
   `Callable[[list[np.ndarray]], list[str]]` — **no OCR confidence exists in
   the interface at all**, so this is a structural Class A. That signature is
   itself a decision and is nowhere in the map.
2. **`direction_text.read_directions:795` — the lexicon gate.** CLAUDE.md calls
   it *"load-bearing, never loosen"*. It is the accept/reject boundary for the
   feature the map itself measures at **~75% of whole-work wall clock** (§3.3),
   and §5 does not have it.
3. **`export._number_spans:2519-2520`** — a **7th simultaneous slur is dropped
   silently**: `number = next((n for n in range(1, max_number + 1) if n not in
   open_spans), None); if number is None: continue`. No counter, no warning, no
   field. That is a Class-E refusal with no record — §7.1 item 1's exact
   target — and it is absent from the shortlist it belongs on.

Also absent, and each a documented production decision:

- **`staff_labels_surya` and `staff_labels_vision`.** §5's Stage 9 table gives
  rows to `staff_labels` (text layer), `staff_labels_tesseract` and
  `staff_labels_human` — **and omits Surya**, the free default rung
  (`contextual.py:685`), **and Vision** (`:809-813`). The map catalogues the
  *unreachable* rung in detail (E-shape, blind-to column) and skips the
  default-ON one. `_surya_worker._assign:89` carries the block-height gate
  CLAUDE.md documents as a landed 2026-09-05 fix with a measured ~22× gap;
  neither the module nor the gate appears in the map.
- **`key_signature_template`.** §5 Stage 8b covers `key_signature_locator`,
  `key_signature_geometry` and `key_signature_vote`. The template reader —
  which CLAUDE.md records reading **11 of 12** staves where the locator reads 2,
  called at `transcribe.py:1394` and `:1409` — has no row, and it is the reader
  behind D20.
- **`movement_reference`** (`OMR_MOVEMENT_REFERENCE`, default ON per D24;
  `slots.py:565`, `:587`) and **`bracket_reader`** — neither module is named
  anywhere in the 1,303 lines.

**Recommendation.** The honest repair is not to write five more tables today;
it is to make §11 state the holes. Applied: §11 now names the three dropped
stages and the four unlisted modules.

---

## 5. USABILITY — does the map answer the five questions?

Per the coordinator's addendum: taking Sean's five questions to three real
areas. Reported separately from §2 because the fixes differ — these entries are
*correct* and too coarse to act on.

### 5.1 ⚠️ The structural finding: six of twelve §5 tables have no `CONSUMED BY` column

§0 states: *"Every decision point in §5 carries the same ten fields"*, and
lists ⚠️ **CONSUMED BY** — *"who reads that — `NOBODY` where that is the
truth"* — as one of "the three … the reason this document exists".

```
$ grep -n "^| decision (file:line)" docs/architecture-decision-map.md
458,473,507,535,563,580: | … | produces → consumed by | shape |
628,660,682,707,751,784: | … | shape |
```

Stages **8a (clef), 8b (key signature), 8c (time signature), 9 (labels →
instrument), 10 (slots + identity), 11 (export)** carry no `produces →
consumed by` column at all.

Those six are **the entire identity and export half of the pipeline** — and
every one of §9.5's six shortlist items lives in them. So **question 2 ("what
consumes my output — does anything?") is unanswerable from the map for exactly
the areas the map tells agents to work in.**

This is both a usability defect and a §0-vs-§5 factual inconsistency.
**Correction applied**: §0 and §5 now state which tables carry the column.

### 5.2 `measure_extractor`'s consumers — the one-line-staves blast radius

| Q | answer from the map |
|---|---|
| 1 · available and unused | ✅ **strong.** The Stage 3 table is the best in the document — `stats[i]`'s unread `y`/`area`, the discarded barline heights, `_drop_close_outliers` receiving only integers. |
| 2 · what consumes my output | ❌ **too coarse to act on.** `_build_measure_cell:1046` → *"`bbox_page_px` → **everything, incl. `app`**"*. The real set is 15 importers, and the ones that matter are not the obvious ones: **`annotate/select_cells.py`, `select_cells_orchestral.py`, `select_timesig_cells.py`, `recut_cells.py`, `annotate/server.py:1603`** and **`staff_header.py:73`** (`_build_measure_cell` directly). CLAUDE.md's single loudest warning in that area — a cell re-cut at a different padding silently invalidates every hand-drawn box in a labeled batch — is reachable **only** through those consumers, and §11 puts the labeling pipeline out of scope, so the map actively routes the reader away from it. |
| 3 · dependency satisfiable | ✅ good — the `>= 5` guards are named with exact lines (though see E1: one guard missed, and the `nominal_line_spacing_px` premise is wrong). |
| 4 · in a cycle | ✅ no — §4 correctly has no cycle here. |
| 5 · already gathered | ⚠️ partial — the `staff_line_thickness_canonical` row is excellent and exact; nothing tells the reader that `line_spacing_px` is the property through which one-line geometry already flows. |

**Verdict: 2 answered, 2 partial, 1 wrong.** The single most consequential
question for that workstream is the one it answers with "everything".

### 5.3 `page_normalise`'s consumers

Not covered, **by declared scope** — §11 puts benchmark internals out. The map
answers question 2 with silence and says so, which is honest. Reported for
completeness: the consumers are `benchmarks/omr-scan-e2e-2026-09/scan_eval.py`,
`tools/omr/tests/test_scan_eval_structural.py` (six `_load("page_normalise")`
sites), and two probes in
`benchmarks/omr-staves-map-completion-2026-09/`. **An agent working there
cannot use the map at all**, which is a scope statement rather than a defect —
but it is worth Sean knowing that one of the three live workstreams is outside
the checkpoint entirely.

### 5.4 The label path through `instruments.py`

| Q | answer from the map |
|---|---|
| 1 · available and unused | ✅ **the best single row in the document.** *"⚠️ **everything except the string.** A pure function with zero context — every contextual repair downstream exists to patch this deliberate blindness."* That is exactly right and immediately actionable. |
| 2 · what consumes my output | ❌ **absent by construction** (§5.1 above — Stage 9 has no consumer column). `instruments.lookup` has **12 production importers** spanning four stages: all five label readers (`staff_labels`, `_surya`, `_tesseract`, `_vision`, `_human`), `contextual`, `score_layouts`, `work_roster`, `clef_correction`, `dossier.py:457`, **`transcribe.py:2484` and `:2872`** (the ownership vetoes, stage 4d — two stages upstream of where the map files this decision), and `tools/library/instrumentation.py` **outside `tools/omr` entirely**. A lexicon change ripples into glyph ownership; nothing in the map says so. |
| 3 · dependency satisfiable | ✅ **excellent** — §9.4's "29 of 29 unresolved non-treble scan staves print no label at all" is the strongest entry in the document, and it is the answer that stops wasted work. |
| 4 · in a cycle | ✅ **excellent** — §4.2 Cycles 1 and 2 are precise, correctly directed, and Cycle 2 carries a number. |
| 5 · already gathered | ⚠️ **partial and, for this path, the weakest.** §4.1 states the rule (*"two signals sharing an ancestor are ONE signal"*) but §5 gives no ancestry per signal. Concretely: `Match.coverage` (§7.2 item 12) and the Stage 10 `SCORE_LABEL_MATCH` term are the **same** signal binarised twice — the map says this in §7.2 and does not connect it to the `slots._pair_score` table three pages earlier, where a builder adding a term would look. |

**Verdict: 3 answered well, 1 partial, 1 structurally absent.**

### 5.5 Usability summary

Across the three areas, **questions 1, 3 and 4 are answered well and are the
map's real value.** Question 2 is answered at file granularity where it is
answered at all, and is structurally unavailable in six of twelve tables.
Question 5 has a stated rule and no per-signal data.

If one thing is fixed for usability, it is **the missing `CONSUMED BY` column
in stages 8a–11**. It is mechanical to fill (the same grep V6 already runs), it
is the column §0 calls the reason the document exists, and it is missing from
exactly the half of the pipeline the map recommends building in.

---

## 6. Corrections applied to the map

All in `docs/architecture-decision-map.md`; documentation only, no behaviour.

| # | where | change |
|---|---|---|
| 1 | §5 Stage 3 note | `nominal_line_spacing_px` — corrected; names `types.py:102` and the 15 property readers; adds the fourth `>= 5` guard at `:849` |
| 2 | §6.2 | `musicxml_builder` moved out of the local-OMR boundary; named as the Vision engine's serializer |
| 3 | §5 Stage 4/5 | two `NOBODY` cells → `probe`, with the reading probes named |
| 4 | §6.1 | `confidence_label` — narrowed to "no decision reads it" |
| 5 | §7.4 | "zero callers" → "zero production callers"; `template_matcher` "one annotate tool" → two |
| 6 | §7.4 + §12 graph | `bracket_reader.py` (390 lines) and `condensed_parts.py` added as orphans |
| 7 | §5 Stage 11 | `_condensed_count` — records that nothing writes the field, so the knob is inert |
| 8 | §8.6 D24 | records V4's undercount, the four missed flags, and the `OMR_SPAN_REFERENCE_FIT` misclassification |
| 9 | §8.6 D25, D26 | universals narrowed |
| 10 | §8 | **D28 added** — `_paired_spans`' "longest run within one voice" |
| 11 | §4.2 Cycle 3 + the checks table | "Do not resurrect it" now names the form measured (A00) |
| 12 | §0 + §5 | records that six of twelve tables carry no `CONSUMED BY` column |
| 13 | §11 | names the three stages dropped from §5 and the four unlisted modules |
| 14 | §10 | notes that V4 undercounts and V7's drift |

**Proposed, not applied** (judgement calls):

- §5's `_apply_roster_range_veto` row and §9.4 should state whether the
  `+24 edits` was ever attributed, per A00 — I do not have the measurement.
- Filling the `CONSUMED BY` column for stages 8a–11 is the largest single
  improvement available and is a day's mechanical work, not a correction.
- `§5` rows for direction text, tie pairing and slur pairing (≈143 decision
  points by independent count). §11 now says they are missing, which is the
  honest interim.

---

## 7. Reproduce

```bash
python3 benchmarks/omr-decision-map-2026-09/verify.py            # the map's own checks
python3 benchmarks/omr-decision-map-verify-2026-09/probe_orphan_modules.py
python3 benchmarks/omr-decision-map-verify-2026-09/probe_env_surface.py
```

⚠️ **`probe_orphan_modules.py` reports four false positives by design** and
names them — a module invoked as a **subprocess** (`_surya_worker`), as a
`python3 -m` entry point (`run_pipeline`), inside another venv
(`_omrned_worker`), or only by benchmarks it belongs to (`page_truth`,
`score_reading`, `score_translation`) is not an orphan. **Do not read its
output as a delete list.** That is the same trap this audit found the map
falling into from the other side (E1): an import graph is not a consumption
graph.
