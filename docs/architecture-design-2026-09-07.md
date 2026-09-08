# The architecture, specified to be built

**Commissioned by Sean, 2026-09-07:**

> *"I think we should reason the best architecture, build it, then test and move
> things around because of all the interdependencies."*
>
> *"Let's wire everything up the way we imagine it will work best. Then test it."*

**This is a DESIGN, not a migration plan.** The whole alternative path is built
behind one flag, off by default, and proved by running both paths **in one
process on one gather**. That side-by-side is the entire safety argument, and
§6 specifies it before §7 specifies what to build.

⚠️ **No pipeline code was changed to write this.** Every anchor below was
re-read in this tree at `88a06c7f`. Anchors quoted from an input document and
**not** re-read are marked `[inherited]`.

⚠️ **THREE PREMISES I WAS HANDED TURNED OUT TO BE WRONG, and each changed the
design.** They are argued where they belong and collected here so nobody builds
on the old version:

| premise | verdict | where |
|---|---|---|
| *"gathering has two hard edges"* | ❌ **three.** The meter vote consumes the `duration_beats` **field**, not a conclusion. Forces `Q.DURATION` to be a Verdict and adds a build step | §3.1, §7.4 |
| *"pages are assembled independently"* | ❌ **false.** `_ClefContinuity` and `carried_meter` make page *N+1*'s inputs page *N*'s outputs | §3.1 |
| *"`clef → key signature` is soft"* | ⚠️ **half.** The run's positions are clef-free geometry; the reader nonetheless refuses to run without a clef (`key_signature_locator.py:310`). Soft in principle, hard as coded | §3.1, §7.4 |

⚠️ **No new model, no new corpus, no ML, and no probabilistic fusion.** If any
step below appears to need one, it is a defect in this document — say so and
stop. Evidence combines as **signed terms with a threshold** (the shape
`slots._pair_score` already uses) or as **ordering**. Never as a multiplier, and
never as a calibrated probability: measured here at ECE 0.1277 with a top bin
promising 0.989 and delivering 0.692.

---

# PAGE ONE — THE DESIGN A BUILDER FOLLOWS

## 0. What changes, in one sentence

> **A reader stops writing conclusions onto a dict and starts appending rows to
> a log. A decision stops reading dicts and starts declaring which rows it
> wants. The harness — not the decision — records what was there, what was
> missing, and what was refused.**

Nothing about recognition changes. The detector, the template key-signature
reader, the CV clef locator, the margin-label cascade, the weights: **untouched
and un-rewritten.** What changes is the *record* between them.

## 1. The record — three row types and one log

New module: **`tools/omr/record.py`**. Stdlib only. No pipeline imports, so
every other module may import it without a cycle.

### 1.1 Subject — what a row is about

```python
class Kind(str, Enum):
    DOCUMENT = "document"
    PAGE     = "page"
    SYSTEM   = "system"
    STAFF    = "staff"
    CELL     = "cell"
    GLYPH    = "glyph"

@dataclass(frozen=True, slots=True, order=True)
class Subject:
    kind: Kind
    page: int | None = None
    system: int | None = None
    staff: int | None = None
    cell: int | None = None
    glyph: int | None = None

    def parent(self) -> "Subject | None": ...
    def ancestors(self) -> tuple["Subject", ...]: ...
    def contains(self, other: "Subject") -> bool: ...
```

`Subject` is the addressing scheme the whole design turns on: a staff-scope
decision asks for its own rows, its **system's** rows, and its **cells'** rows
by scope, without knowing how anyone stored them.

⚠️ `staff` is the index **within its system**, never the page-wide running
index. The project has already been bitten by that exact ambiguity —
`draft_windows` documents that `staff_index` is numbered across the PAGE while
every join must be by position within the system. `Subject.staff` is
system-local and `record.py` says so in one line at the field.

### 1.2 The three row types

```python
@dataclass(frozen=True, slots=True)
class Observation:
    """A quantity read off the raster. NEVER a name, NEVER an interpretation."""
    id: str                      # "obs:<8 hex>", assigned by the log
    subject: Subject
    quantity: str                # from record.Q — a closed vocabulary
    value: Any                   # the MEASUREMENT. Has no sentinel and no default.
    reader: str                  # from record.READERS
    frame: str                   # the crop it was read in: "header_window",
                                 # "cell:0", "page", "system_margin"
    score: float | None          # the reader's own score IN ITS OWN UNITS.
                                 # None means "this reader produces no score",
                                 # which is not the same as 0.0.
    detail: Mapping[str, Any] = field(default_factory=dict)
```

```python
@dataclass(frozen=True, slots=True)
class Abstention:
    """A reader RAN on this subject and declined. Not the same as never running."""
    id: str                      # "abs:<8 hex>"
    subject: Subject
    quantity: str
    reader: str
    frame: str
    reason: str                  # from record.ABSTAIN — a closed vocabulary
    detail: Mapping[str, Any] = field(default_factory=dict)
```

```python
@dataclass(frozen=True, slots=True)
class Verdict:
    """An adjudicated fact. Produced only in Phase A. Reads no raster."""
    id: str                      # "vrd:<8 hex>"
    subject: Subject
    quantity: str
    outcome: Outcome             # DECIDED | ABSTAINED
    value: Any | None            # None iff ABSTAINED — enforced in __post_init__
    decider: str                 # the decision function's name
    reason: str                  # from the decision's own closed vocabulary

    # ── every field below is filled by the HARNESS, not by the decision ──
    considered: tuple[str, ...]  # row ids actually handed in
    missing:    tuple[str, ...]  # declared quantities the log had NOTHING for
    declined:   tuple[str, ...]  # declared quantities where a reader ABSTAINED
    excluded:   tuple[tuple[str, str], ...]   # (row_id, why) — §4
    correlated: tuple[frozenset[str], ...]    # groups counted once — §4
    basis:      tuple[str, ...]  # transitive ancestor closure

    margin: float | None = None  # winner − runner-up, in the decision's units
    supersedes: str | None = None
```

### 1.3 The log

```python
class Log:
    def observe(self, **kw) -> Observation: ...
    def abstain(self, **kw) -> Abstention: ...
    def record(self, verdict: Verdict) -> Verdict: ...          # append-only

    def rows(self, quantity: str, subject: Subject, *,
             scope: Scope = Scope.EXACT) -> tuple[Observation, ...]: ...
    def refusals(self, quantity: str, subject: Subject, *,
                 scope: Scope = Scope.EXACT) -> tuple[Abstention, ...]: ...
    def verdict(self, quantity: str, subject: Subject) -> Verdict | None: ...

    def state(self, quantity: str, subject: Subject) -> State: ...
```

`Scope` is `EXACT | SELF_AND_ANCESTORS | SELF_AND_DESCENDANTS`.

**The log is append-only.** There is no `update`, no `set`, no `del`. §5 is why.

## 2. ⚠️ How absence is represented — four mechanisms, none of them a convention

The brief's requirement is that *"not measured"* be distinguishable from
*"measured as zero"* **by construction**. Four mechanisms, in order of how much
work they do:

### 2.1 There is no field, so there is no default

A measurement is a **row**, not a key on a dict. `log.rows(...)` returns a
`tuple`. `()` is not a value a consumer can mistake for a reading, and there is
no `.get(key, default)` to write because there is no key.

⚠️ **This is the mechanism, and the pipeline has three dead carries and one live
sentinel proving it is needed:**

| the live instance | what the record cannot say today |
|---|---|
| `system_grouping._assign_groups` — `staves[s_i].group_index = 0` at **`:596`** (system has fewer than 3 staves) and **`:611`** (no column evidence to take a ratio of), against `:620` which assigns a real block | *"I declined to partition"* and *"I read one family"* are **byte-identical on the record** — and the function knows which branch it took and discards that |
| the three carry dicts — read `transcribe.py:4851/4873/4885`, written `:5232-5234` `[inherited]` | *"the carry fired and agreed"* and *"the carry never fired"* are indistinguishable from the output. **A dead `.get()` with a good default is invisible.** |
| ⚠️ `contextual.py:1451` — `staff["instrument_source"] = instrument_source.get(slot, "label")` | **the provenance tag that guards all three standing circularity refusals is itself read through a `.get()` whose default is `"label"` — the one tier the refusals admit.** Same at `:1298`. Whether the default is reachable is **UNMEASURED**; the *shape* is the hazard this design exists to remove |

### 2.2 Three states, not two

`Log.state()` returns one of three, and a decision can act on the difference:

```python
class State(str, Enum):
    READ       = "read"        # ≥1 Observation
    DECLINED   = "declined"    # 0 Observations, ≥1 Abstention — a reader looked
    ABSENT     = "absent"      # nothing at all — no reader ran on this subject
```

`DECLINED` carries information (`reason`); `ABSENT` carries none. Collapsing
them is what a sentinel does.

### 2.3 The harness fills `missing`, so the decision cannot forget

A decision declares `wants=(...)`. After it returns, the harness computes
`missing` and `declined` as *set differences between the declaration and the
log* and stamps them on the `Verdict`. **The decision is not asked to be honest;
it is not consulted.**

### 2.4 The declaration is enforced, not documentation

`Evidence.rows(q)` **raises** `UndeclaredEvidence` if `q` is not in `wants`.
A decision that reads something it did not declare fails loudly in the first
test that exercises it. This is what makes "the signature IS the declaration"
true rather than aspirational.

### 2.5 The lint that keeps it true

`tools/omr/tests/test_record_discipline.py`, by AST over
`tools/omr/adjudicators/`:

* no `.get(` with a second argument on any `Evidence` or `Log` result;
* no comparison of an `Observation.score` to a literal without the score's
  `None` case handled;
* every `Abstention.reason` and `Verdict.reason` string is in the closed
  vocabulary (`record.ABSTAIN`, and the decision's own `reasons=` declaration);
* every adjudicator module is registered.

⚠️ **Run every one of these tests RED before green.** This project has shipped a
regression test that passed vacuously either way (the margin-label blob test
asserted on label LENGTH, where a single huge glyph is one character) and only
caught it by disabling the mechanism and watching the test still pass.

## 3. The two phases

### 3.1 Phase G — GATHER

A reader emits rows and **stops concluding**. Its existing return value is kept
so the flag-off path is untouched (§6).

**The hard edges. ⚠️ I was asked to verify the claim that there are two. THE
CLAIM IS WRONG — there are THREE, and the third one changes a build step.**

| edge | hard for GATHERING? | verified where |
|---|---|---|
| page geometry (staves → systems → barlines → cells) → every reader | ✅ **yes** | `transcribe.py:4603-4607`, and it is self-enforcing: `measure_extractor.py:1441-1442` inside `extract_measures` reads `if not pws.barlines: detect_barlines(pws)`. Every reader's input is a `MeasureCell` or a `Staff` — `pitch_resolver.py:167` returns `None` without `staff_line_ys_canonical`; `key_signature_locator.py:312` aborts without `staff_metrics(cell)` |
| detections → direction text | ✅ **yes** | `direction_text.py:301` `_blank_detections` — *"Erase every detected glyph from the mask"* — walking `page_dict → systems → staves → measures → detections` at `:317-332`, called from `find_candidates` at `:519`. A genuine **input** edge: the detection list changes the mask pixels the candidate finder sees |
| ⚠️ **durations → meter vote** | ✅ **YES — and the input document says no** | `rhythm.py:382-390` `measure_length_beats` sums `ev["duration_beats"]`; `:453` `_page_column_lengths` calls it per measure; `:467` `infer_page_time_signature` votes those lengths. `duration_beats` is **written** at `transcribe.py:2335`. The vote's input is the rhythm pass's **output field**, not its conclusion |
| clef → key signature | ⚠️ **soft in the geometry, HARD AS CODED** | the run's positions are pure geometry — `key_signature_locator.py:322-337` finds components and clusters them, `:347-368` locates where the clef *ended* by **height in staff spaces** (never consulting the `clef` argument), `:396` `_positions(run, top_y, spacing)`. The clef enters **only** at `:398-399` `fit_key_signature(positions, clef, …)`. **But `:310` is `if not clef: return None`** — the reader refuses to run at all |
| clef → pitch | ❌ **no — genuinely soft** | `pitch_resolver.py:180-181` computes `pos_float` and `pos` from cell geometry and the notehead's y-centre alone; the clef is untouched until `:183` `_pitch_from_position(pos, clef)`. Same at `:231-232` vs `:243` |

**What the third hard edge means for the design, and it is not fatal.** The
meter vote is a **decision**, not a measurement — so under the split it consumes
the *duration verdict*, and adjudication-order constraints are free. But that is
only true if **duration is adjudicated rather than measured**, which forces a
classification the target document does not make:

> `Q.BEAM_STROKE`, `Q.FLAG`, `Q.AUG_DOT`, `Q.NOTEHEAD_CLASS` are
> **measurements**. `Q.DURATION` is a **Verdict**. The meter is a Verdict that
> consumes it, and `_reconcile_measure_to_meter` is a bounded `revises=` of the
> duration verdict (§5.2).

⚠️ **And it is a genuine feedback loop, broken today only by ordering:**
`transcribe.py:5382` votes the meter out of committed durations, then `:5410`
`_reconcile_page_to_meter` **rewrites** `duration_beats` from the settled meter
and `beam_levels`. Vote once, repair once. §5.2's `revises=` bound is what keeps
that from becoming a fixpoint, and the bound is `_reconcile_measure_to_meter`'s
own — copied, not loosened.

**Two more corrections to the inherited picture, both from the same
verification:**

* ⚠️ **The clef → key-signature build step is a code change, not just a
  reclassification.** For the gather phase the locator must emit
  `Q.KEYSIG_RUN_POSITION` rows **without a clef**, which means moving the
  `if not clef: return None` guard from the top of the reader to the *fit*. The
  guard is deliberate and reasoned (`transcribe.py:4659-4683`: *"Reading a key
  signature against a guessed clef is guessing twice"*, and fitting against a
  guessed clef once read three flats as **two sharps**). **The guard is not
  removed — it moves to the adjudicator**, where the clef verdict is available
  and can abstain instead of guessing.
* ⚠️ **One reader runs BEFORE geometry**, so "every reader" is wrong:
  `_route_weights` (`transcribe.py:4521`, def `:4294`) classifies the raw PDF via
  `input_domain.classify_pdf_domain` and picks the weights. The honest statement
  is *"every reader except weight routing."*

**Parallelism — and the inherited claim that pages are independent is FALSE.**

⚠️ `docs/pipeline-gather-then-adjudicate-2026-09-07.md` §5 says *"every page is
assembled independently until 5628"*. It is not. Three cross-page carries make
page *N+1*'s inputs page *N*'s outputs: `_ClefContinuity` (`transcribe.py:740`,
instantiated `:4587`, driven `:4834/:4853/:5236/:5239`) — which is the **only**
reason a continuation system's clefs are not uniformly the positional default —
and `carried_meter` (`:5389-5403`). **Pages cannot be parallelised without
replicating that carry**, and doing so is not in this design.

⚠️ **Nothing is parallelised today and this design parallelises nothing.** It
makes parallelism *expressible* — the `Log` is append-only, so per-subject rows
never collide — and that is all it claims. What would be saved is **UNMEASURED
and deliberately not estimated**: the one cost figure in hand is direction text
at ~19% of page wall clock at the median on **single-page** runs against ~75% on
a **whole-work** run, and those two regimes are explicitly not comparable.

⚠️ **Two things must NOT be parallelised, and the design must not tempt anyone:**
the three margin-label readers are a **cheapest-first cascade** that only pays
for the next rung when the free one is empty — running them together spends the
money the cascade exists to save; and the CV rungs and YOLO read **different
images** on purpose (erasing staff lines before YOLO measured −7 to −13 reading
points and up to a third of the noteheads). Both are recorded in
`record.py`'s module docstring as `DO NOT PARALLELISE`, with the numbers.

### 3.2 Phase A — ADJUDICATE

New package: **`tools/omr/adjudicators/`**, one module per decision. New module
**`tools/omr/adjudicate.py`** holds the harness.

```python
@decision(
    quantity   = Q.CLEF,
    scope      = Kind.STAFF,
    wants      = (Q.CLEF_GLYPH, Q.CLEF_LOCATED, Q.CLEF_SEED,
                  Q.STAFF_POSITION, Q.INSTRUMENT, Q.MARGIN_LABEL),
    reasons    = ("argmax", "margin_below_floor", "no_candidates",
                  "all_candidates_excluded", "corroborated"),
    mode         = Mode.COMPETITIVE,
    margin_floor = CLEF_MARGIN_FLOOR,
    excludes_tiers = ("roster",),   # §4.2 — a QUALITY hold-out, not circularity
)
def adjudicate_clef(ev: Evidence) -> Ruling: ...
```

⚠️ **`reasons` is a closed vocabulary per decision, and the model for it is
already in the tree**: `propose_clef`'s `_note(exit_, **fields)` closure
(`clef_correction.py:239-243`) records which of its exits was taken —
`no_clef_anchor`, `already_in_effect`, `no_candidate_clefs` — which is the
single best existing expression of *"a decision says why it declined"*. Copy it;
do not design a rival.

`Ruling` is what a decision returns — deliberately smaller than `Verdict`,
because the decision fills only what it knows:

```python
@dataclass(frozen=True, slots=True)
class Ruling:
    value: Any | None
    reason: str
    margin: float | None = None
    used: tuple[str, ...] = ()      # row ids the decision actually weighed
```

The harness turns a `Ruling` into a `Verdict`, filling `considered`, `missing`,
`declined`, `excluded`, `correlated` and `basis`.

**The `Evidence` API** — the whole surface a decision sees:

```python
class Evidence:
    subject: Subject
    def rows(self, q, *, scope=Scope.EXACT) -> tuple[Observation, ...]   # raises if undeclared
    def refusals(self, q, *, scope=Scope.EXACT) -> tuple[Abstention, ...]
    def verdict(self, q, *, subject=None) -> Verdict | None
    def state(self, q, *, scope=Scope.EXACT) -> State
    def independent(self, rows) -> tuple[tuple[Observation, ...], ...]    # §4.3
```

**How evidence combines — signed terms, and nothing else.** The one sanctioned
shape, already in the tree as `slots._pair_score`:

```python
@dataclass(frozen=True, slots=True)
class Term:
    name: str
    weight: float             # signed. Positive supports, negative opposes.
    rows: tuple[str, ...]     # the Observation/Verdict ids this term rests on

def tally(terms: Sequence[Term], ev: Evidence) -> float:
    """Sum, counting each CORRELATED GROUP once (§4.3)."""
```

A decision scores each candidate with `tally`, takes the top, and **abstains
when `top − runner_up < margin_floor`**. `margin` goes on the record either way.

⚠️ **A decision may also be ADDITIVE rather than competitive, and the
distinction is load-bearing.** Measured on the grouping fact across 67 stored
transcriptions: consuming it *additively* changed 20 exports, added 108 bracket
groups, kept braces at 2 → 2 with none lost and **zero content differences**
outside the group lines; letting it *overrule* the incumbent brace rule would
have declared five wind pairs to be pianos (§7.2). So `@decision` carries a
`mode`:

```python
class Mode(str, Enum):
    ADDITIVE    = "additive"     # may only ADD a fact where none stood
    COMPETITIVE = "competitive"  # may overturn — needs a margin_floor
```

`ADDITIVE` is the default. `COMPETITIVE` must name what it may overturn, and
the harness refuses to record an overturn whose `margin` is `None`.

## 4. ⚠️ What may not flow — a local check on a row's provenance

### 4.1 The rule

> **A decision may consume a fact only if that fact's provenance chain does not
> contain the decision's own output; and two facts sharing an ancestor count
> once, not twice.**

Unchanged from `docs/scope-identity-upstream-2026-09-06.md` §7. What this design
adds is that **it is checked by the harness from the ids on the rows**, not
reasoned about by a human who must remember to.

### 4.2 The independent-witness rule — the self-loop check

Every `Verdict` carries `basis`: the transitive closure of the row ids it rests
on. `Observation.basis` is empty by definition — its only ancestor is the
raster. So the closure is finite, cheap, and computed once per row.

> **An interpretation may anchor a decision only if its `basis` contains at
> least one Observation that is NOT a descendant of the decision's own
> quantity.**

The harness applies this at hand-in time and stamps `excluded`. The decision
writes no circularity code at all.

⚠️ **THE DESIGN'S FIRST ACCEPTANCE TEST IS THAT THIS RULE REPRODUCES THE THREE
STANDING REFUSALS.** They were each won by measurement, not by reasoning, and a
mechanism that does not reproduce them is wrong however elegant:

| standing refusal | why the rule should reproduce it |
|---|---|
| `clef_correction.py:566` — `if instrument_source_by_slot.get(slot) != "label"` refuses **deduced identity → clef** | a `score_order` identity's basis runs through `fit_layouts`, which is handed **`clefs=clef_by_slot`** at `contextual.py:1208-1209` (the map's `:1076` has drifted). So clef is in its ancestry and it is excluded. A `label` identity's basis is an OCR row — no clef — and is admitted |
| `dossier.py:434` — refuses **clef → the part↔staff pin** `[inherited]` | on a seeded run the clef's basis contains the join, so scoring the join on clefs is a self-loop. This is the same fact as CLAUDE.md's *"a clef adjudicator must exclude `clef_evidence["dossier"]` on a dossier-seeded run"* — one mechanism, not two |
| `score_layouts.py:682` — refuses **clef → layout pin** `[inherited]` | same shape |

⚠️ **And it must reproduce the deliberate EXCEPTION, which is what makes the
rule's exact wording load-bearing.** `score_order_ambiguity` — a label the
layout prior disambiguated — is admitted on purpose at `contextual.py:409`. Its
basis contains **both** an OCR row and the layout prior. A cruder rule
(*"exclude anything with clef in its ancestry"*) would wrongly exclude it. The
rule as written asks for *at least one independent observation*, and the OCR
row supplies it. **A rule that excludes `score_order_ambiguity` is the wrong
rule.**

⚠️ **What the rule does NOT replace: quality hold-outs.** `roster` identity is
held out of clef decisions by default (`OMR_ROSTER_CLEF=0`) `[inherited]` and
its basis is a catalog row, not a clef descendant — so the circularity filter
**admits** it. That is correct and must stay: the hold-out is a judgement about
the tier's reliability, not about circularity. Quality hold-outs remain explicit
flags, declared per decision as `excludes_tiers=("roster",)`. **Do not fold them
into the provenance filter** — merging a measured quality decision into a
structural safety rule is how one of them goes silently missing.

### 4.3 Correlated evidence counts once

Two rows whose bases intersect **outside the raster** are one signal.
`Evidence.independent()` partitions the handed-in rows into groups and `tally`
counts each group's best term once.

⚠️ **The live example is the reason this is not theoretical.** The header clef
pre-pass and the measure-pass clef argmax look like two readings and are
measured to be **the same call on the same object**: `start_cells` and
`staff_cells` are both `systems[sys_idx][staff_idx]`, the same list object, and
over 396 staves they were **divergent on exactly 0** `[inherited]`. Comparing
them as an agreement signal would have produced a healthy-looking 77% agreement
rate carrying no information. Under this design they share a basis and `tally`
counts them once, **without anyone noticing they are the same call.**

⚠️ **A refuted edge, named so it is not re-proposed:** detection confidence as
the ownership tie-break. Measured over 4,521 contested pairs — P(winner conf >
loser conf) = **0.545** against a 0.500 null, and a `|Δconf| > 0` tie-break
would overturn distance on **45.5%** of contests `[inherited]`. `Q.GLYPH_CONF`
is gathered and is available to the ownership adjudicator; **the shipped
ownership decision must not weight it**, and the reason goes in the module
docstring with the number.

## 5. Propagation — the tail of adjudication, and it is EVENT-shaped

**Sean asked whether propagation is a third phase. It is not.** Nothing in the
tree iterates: all three existing propagations are single-pass `for` loops with
no `while` and no repeat-until-stable `[inherited]`. Consequences flow downhill
once.

**But the RECORD of what changed is a real, unowned concern, and the shape
decides whether it can stay true.** The tree has both shapes and the outcome is
exactly what the shape predicts `[inherited]`:

| shape | fields | outcome |
|---|---|---|
| **VALUE** — *"the clef at the end of the staff"* | `clef_final`, `key_signature_final`, `time_signature_final` | must be re-maintained by **every** later writer. `clef_final` 9 of 20 stale, `key_signature_final` 19 of 26 stale, `time_signature_final` has **no keeper at all**. Two keepers were added; a third field is stale now |
| **EVENT** — *"at measure N, X became Y, on evidence E"* | `rhythm_reconciliation`, `key_signature_corroboration` | append-only, describes a moment. **Cannot go stale** |

### 5.1 This design is EVENT-shaped, and there is no value to maintain

`Verdict` is an event. The log is append-only. **"The current clef" is a QUERY
over the log, never a stored field:**

```python
def current(log, quantity, subject) -> Verdict | None:
    """The last non-superseded Verdict. There is no cached copy to go stale."""
```

A later decision that changes a fact appends a new `Verdict` with
`supersedes=<earlier id>` and its own `reason`. Nothing is overwritten, so
nothing can be missed by a writer.

⚠️ **The `*_final` fields are not migrated and not repaired here.** They keep
their current behaviour on the flag-off path. On the flag-on path they are
**derived from the log at serialisation time** by one function, so there is one
writer instead of N. That is the shape fix; whether the old fields are then
deleted is a separate decision with its own diff.

### 5.2 Downhill-only is enforced, not promised

Two harness rules keep the single-pass regime a property of the machine:

1. **One adjudication per `(subject, quantity)` per run.** A second call raises
   `AlreadyAdjudicated` unless the decision declares `revises=<quantity>` with a
   **bounded** justification. The model is `_reconcile_measure_to_meter`: re-read
   a beam level by **±1 only**, the bar must land **exactly** on the meter, the
   answer must be **unique**, single-voice measures only, and never add, delete
   or re-pitch a note. A `revises=` declaration must carry a bound of that kind
   in its docstring, and `test_record_discipline.py` asserts every one has one.
2. **A Verdict may not be superseded by a Verdict that has it in its own
   `basis`.** That is the fixpoint, refused mechanically. If a future version
   re-derives the clef contest from *restated pitches*, the edge becomes uphill
   and the harness raises rather than looping. **This project has twice declined
   to build a convergence argument**; the harness makes declining the default.

## 6. The switch, and the A/B

### 6.1 One flag, three values

```python
def _adjudicate_mode() -> str:
    """OMR_ADJUDICATE: "0" (default) | "shadow" | "1"."""
    return os.environ.get("OMR_ADJUDICATE", "0").strip().lower()
```

| value | rows **computed** | rows **serialised** | adjudicators run | authoritative | output |
|---|---|---|---|---|---|
| **`0`** (default) | ✅ **always** | no | no | legacy | ⚠️ **byte-identical to today** |
| `shadow` | ✅ | yes | yes | **legacy** | today's output **plus** `record` and `divergence` |
| `1` | ✅ | yes | yes | **adjudicated** | the new path's output |

⚠️ **The split between COMPUTED and SERIALISED is not an optimisation — it is
obedience to a rule this project wrote after being bitten.**
`transcribe.py:1753-1758` records that `OMR_CONTEST_DUMP` and
`locate_clef(trace=)` were *"complete recorders that recorded NOTHING because
they were off"*, and `contested_notehead_pairs` is **still on the wrong side of
that line** (gated by `OMR_CONTEST_DUMP`, default off). So the emitting code
runs on **every** run, in every mode, and is exercised by every test — while
only serialisation is gated, because serialising at `0` would change the result
JSON and forfeit the byte-identity acceptance test the project already applies
to arcs, reclass, condensed parts and slot stitch. **A reader may never be able
to say "I did not record because I was switched off."**

⚠️ **And rows are handed to the log as an OUT-PARAMETER, never by widening a
reader's return type.** That convention is already in the tree with its reason
stated: `transcribe.py:1744-1746` (`clef_evidence`) and `:1492-1495`
(`_header_key_signatures(evidence=)`) — *"widening a return to carry a record is
how a recording change acquires a blast radius"*. Every reader gains one
keyword-only `log: Log | None = None`; nothing about its return changes; a
`None` log makes every `observe`/`abstain` a no-op. **That is what makes the
flag-off byte-identity claim cheap to believe.**

### 6.2 ⚠️ The A/B is ONE process on ONE gather — and that is the point

**`shadow` runs both adjudications over the same rows in the same process.** The
raster is read once. This is not a convenience; it removes three failure modes
this project has actually been bitten by:

| the trap | why `shadow` is immune |
|---|---|
| ⚠️ **the cached A/B.** `scan_eval.run_pipeline` returns early if the prediction exists, so **two arms sharing a fixtures dir with an empty `--tag` reuse the first arm's transcriptions and the second arm never runs** — reporting *"identical on every bucket and every row"*, which is exactly the clean result a flag-guarded change hopes for. The only tell was wall time | there is no second arm to cache. One run, two outputs |
| ⚠️ **detector jitter.** A from-scratch rebuild of the hairpin fix reproduced the categorical result and **not** the edit count — the same four boxes' confidences moved between runs on byte-identical code (0.83 → 0.69 on the widest) | both paths consume the **same** detections. Jitter cancels exactly |
| ⚠️ **the worktree venv traps.** Four symlinks, three of which fail on the scan side only, so a worktree that runs `orchestral_eval` cleanly proves nothing about `scan_eval` | the divergence table needs no venv, no scorer and no benchmark |

### 6.3 What the A/B compares

`shadow` writes a `divergence` block. For every `(subject, quantity)` where a
legacy value and a `Verdict` both exist, one of five outcomes:

| outcome | meaning | how to read it |
|---|---|---|
| `agree` | same value | the migration is inert here |
| `differ` | both decided, different values | **the population to hand-adjudicate.** Not a regression and not a win until someone reads the print |
| `new_abstention` | legacy decided, the adjudicator declined | ⚠️ **counted separately, because it is a FEATURE that scores as a loss.** musicdiff charges an absent element |
| `new_decision` | legacy had nothing, the adjudicator decided | the additive population |
| `legacy_only` | no `Verdict` at all | the decision is not migrated yet — expected during the build |

Three commands, and none of them runs a benchmark:

```bash
OMR_ADJUDICATE=0      python3 -m tools.omr.transcribe score.pdf --out a.json
OMR_ADJUDICATE=shadow python3 -m tools.omr.transcribe score.pdf --out b.json
python3 -m tools.omr.record --divergence b.json          # the table
python3 -m tools.omr.record --assert-legacy-identical a.json b.json
```

⚠️ **`--assert-legacy-identical` compares the LEGACY half of the shadow output
to the flag-off output**, which must be byte-identical: `shadow` may not perturb
the path it is shadowing. That is the check that keeps `shadow` honest, and it
is separate from the flag-off byte-identity check.

### 6.4 The gate, and what a worse score does and does not mean

Scoring on `scan_eval` / `orchestral_eval` is the **builder's** step, not
this document's, and it is gated on the divergence table first: *a decision with
zero `differ` and zero `new_decision` rows has no reachable effect and must not
be scored*, which is the fill-tier's lesson (5 proposals on 193 staves, **0
applied**) and the reach-before-accuracy discipline this project has applied
four times.

⚠️ **And the standing rule applies with unusual force here.** Abstention is a
product of this design, and OMR-NED charges an absent element — so **the pooled
number is expected to move the wrong way where the design is working.**
`OMR_SLOT_STITCH` is the precedent already in the tree: structurally correct,
`entire staff` doubled 715 → 1,632, shipped default-off with the reason
recorded. Read `new_abstention` and matched-note recall **before** reading the
pooled figure.

## 7. What the build agent does, in order

Each task has an acceptance test that can be run **without a benchmark**.

### 7.1 First — the record, the harness, and ZERO migrated decisions

**Build:** `tools/omr/record.py`, `tools/omr/adjudicate.py`, the
`tools/omr/adjudicators/` package (empty), the flag, the divergence writer,
`tools/omr/tests/test_record_discipline.py`.

**Depends on:** nothing.

**Acceptance, all four required:**

1. **Flag off is byte-identical.** Result JSON and exported MusicXML hash-equal
   to `main` on one engraved and one scanned fixture.
2. **`shadow` with no migrated decisions** produces a `divergence` table with
   zero rows and a legacy half byte-identical to flag-off.
3. ⚠️ **The five hard-edge rows of §3.1 are re-asserted mechanically** — a
   static check in the shape of
   `benchmarks/omr-gather-adjudicate-2026-09/verify_order.py`, exiting non-zero
   if any row is wrong, **plus** the nine further input edges §3.1's
   verification turned up (pitch → cross-staff dedupe at `transcribe.py:3153`;
   detections → the CV locators' `occupied_boxes` at `:1964-1968` and
   `key_signature_locator.py:292`; ledger detections → notehead survival at
   `:3503`; dedupe/furniture → the meter vote, ordered deliberately at
   `:5329-5333`; header key vote → measure-loop suppression at `:4994`; header
   meter vote → `active_time_sig` seed at `:4885`; CV stems → notehead-class
   correction at `:2169`; contextual → the roster range veto at `:5651`; the
   cross-page carries at `:4587`/`:5389`). ⚠️ **The premise handed to this
   design was "two hard edges" and verification found three.** Do not inherit a
   count — assert it.
4. ⚠️ **The independent-witness rule reproduces the three standing refusals and
   admits `score_order_ambiguity`** (§4.2), driven by hand-built basis chains —
   no pipeline run. **If it does not, stop: the design is wrong and this is
   where it is cheapest to find out.**

⚠️ Run every discipline test RED first.

### 7.2 Second — migrate STAFF GROUPING, as two questions

**Why this one:** it is a **measurement** (page geometry, no lexicon, no
template, no provenance question can arise), and its abstention defect is
already in the wild (§2.1), so the discipline the harness exists to install is
exercised on the first try rather than hypothetically.

**Build:**

* `system_grouping` emits, on **four** branches — three abstentions and one
  reading, all four currently writing the identical `group_index = 0`:

  | `system_grouping.py` | branch | emits |
  |---|---|---|
  | `:596` | `len(members) < 3` — the system is too small to partition | `Abstention(SYSTEM_TOO_SMALL)` |
  | `:611` | `not inner or median < BRACKET_COLUMN_MIN_EVIDENCE` — nothing to take a ratio of | `Abstention(NO_COLUMN_EVIDENCE)` |
  | `:672` | `assign_systems`, `len(staves) < 2` — the page is one staff | `Abstention(NO_SYSTEM)` |
  | `:620` | the real assignment | `Observation(Q.BRACKET_BLOCK, value=group)` |

  ⚠️ There is also a **fifth** case with no site at all: the gap-heuristic
  fallback path never calls `_assign_groups`, so those staves keep the
  dataclass default `0` and no branch ever runs. That one is `State.ABSENT`
  rather than an `Abstention` — *nothing looked* — and the distinction is the
  whole of §2.2. **The existing `group_index` assignments all stay**; flag-off
  is untouched.
* `adjudicators/grouping.py` with **two decisions, not one**:

  | decision | question | evidence |
  |---|---|---|
  | `adjudicate_staff_group` (`Q.STAFF_GROUP`) | *which staves are one family* | `Q.BRACKET_BLOCK` |
  | `adjudicate_group_symbol` (`Q.GROUP_SYMBOL`) | *brace, bracket, or none* | `Q.STAFF_GROUP` + `Q.INSTRUMENT` + `Q.SYSTEM_STAFF_COUNT` |

  ⚠️ **This split is not tidiness; conflating them is a shipped-bug shape.** A
  bracket block of two staves is **not** a grand staff: Brahms 1 p.1 reads
  blocks `[2,2,2,2,2,7,1,3]` — five *pairs* that are `2 Flöten`, `2 Oboen` and
  so on. Consuming *"block of 2"* as a brace **declares five wind pairs to be
  pianos.** The block decides the GROUPING; it says nothing about the SYMBOL.
* Both decisions are `Mode.ADDITIVE` — measured safe (20 exports changed, 108
  groups added, braces 2 → 2 with none lost, zero content differences outside
  the group lines) and measured dangerous the moment they overrule.
* **All THREE brace sites consume the verdicts** — `export.py:681` (LilyPond,
  `len(staves) == 2`), `:3523` (MusicXML per-system, `len(staves) == 2`), and
  ⚠️ **`:3446` on the STITCHED path, `len(slots) == 2`** — a different quantity
  (parts across the piece, not staves in one system) answering the same
  question. **Multi-system scores go through `:3446`**, so a change touching
  only the two commonly-cited sites leaves the main path on the old rule. All
  three verified in this tree.

**Acceptance:** `shadow` divergence table is non-empty and every `differ` row is
hand-adjudicated against the print; flag-off byte-identical; the two-question
split is asserted by a test in which a 2-staff wind pair produces
`STAFF_GROUP = {two staves}` and `GROUP_SYMBOL = bracket`, **not** brace.

⚠️ **Three things the builder must state rather than discover:**

* **`group_index` is DELIVERED AND UNREAD, not stranded.** `transcribe.py:4921`
  already writes it onto the serialised staff dict; it survives the JSON
  boundary and sits in `to_musicxml`'s input on every fresh run. **It simply has
  no reader.** That is a *different* failure from the barline evidence and the
  cell pad, which genuinely do not cross the boundary — the two need different
  fixes and this project has examples of each. The design's transport machinery
  is not what fixes this one; the *adjudicator* is.
* ⚠️ **Do not measure this fact's reach from committed artefacts.** Over 67
  stored transcriptions **890 of 1338 staves carry `group_index: null`** and
  only 17 of 102 systems carry a usable partition — **all engraved; no stored
  scan carries the fact at all.** Those artefacts are *pre-emission*, not
  evidence the fact is rare. Any reach figure must come from a fresh run.
* ⚠️ **The measurement is structurally silent on the population the incumbent
  rule fires on.** `_assign_groups` refuses systems with fewer than 3 staves
  (`:596`), so **on a real two-staff page `Q.BRACKET_BLOCK` cannot speak at
  all.** The two failure modes people cite — a two-staff orchestral extract read
  as a piano, and a real piano on a crowded page — are different problems, and
  this measurement can only ever address the second. The `ABSENT` state makes
  that visible; the adjudicator must fall back to `len(staves) == 2` and record
  that it did.

### 7.3 Third — migrate the CLEF

**Why third:** it is the pipeline's documented ceiling, it is the decision with
the most readers already recording evidence nobody consumes, and it is the first
step where the circularity filter actually binds.

**Depends on:** 7.1 (the harness) and 7.2 (proof that transport + additive
abstention works on a measurement).

**Build:**

* Every clef reader emits `Q.CLEF_GLYPH` / `Q.CLEF_LOCATED` / `Q.CLEF_SEED`
  rows with `reader` and `frame`, plus `Abstention`s carrying the CV locator's
  own rejecting branch (`occupied`, `too_big`, `no_clusters`).
* ⚠️ **Delete the crop-choice GATE from the gather phase.**
  `_header_cell_beats_measure_cell` is a boolean that picks ONE crop for the
  locator to read, and on **14 of 14** divergent staves it chose the measure
  cell — the crop the reader could not read — while the other crop had already
  been read and thrown away in the same run `[inherited]`. Under this design
  **both crops are read and both are recorded**, and the choice becomes a
  scoring term in Phase A. Same for `transcribe.py:1953`
  (`if read_clef and locate_c_clefs and clef_source is None`), which silences the
  locator by **presence** rather than by score — a detector clef at 0.11
  permanently mutes it. **Verified in this tree.**
* `adjudicators/clef.py`: signed terms over candidates, `Mode.COMPETITIVE`
  with a `margin_floor`, abstaining below it and recording `margin`.
* **Keep `pos_float`.** `pitch_resolver.py:180` computes it and `:181` rounds it
  away. Emit `Q.STAFF_POSITION` with the fraction. Additive; the rounded `pos`
  still drives today's path.

**Acceptance:** the divergence table's `differ` and `new_abstention` rows,
hand-adjudicated against the print on a handful of staves. ⚠️ **Reach before
accuracy**: if `differ + new_decision` is zero, the step is machinery-only and
must be *stated* as that.

### 7.4 Then — and only then

**Fourth: glyph ownership** (§8.3). **Fifth: part boundaries** (§8.4). Both are
specified below as worked examples because the brief asks for the mechanism
shown on them; neither is in the first three tasks, because both need the
circularity filter proved first, and part boundaries is the one a pre-registered
gate has already falsified once.

**Sixth: the key signature**, and it is sixth because it is the only migration
that needs a reader's control flow changed rather than a decision moved. The
gather phase needs `Q.KEYSIG_RUN_POSITION` rows emitted with **no clef**, which
means `key_signature_locator.py:310`'s `if not clef: return None` (and
`key_signature_template.py:133`) moves from the top of the reader down to
`fit_key_signature` at `:398-399`. ⚠️ **The guard is not deleted.** It is
deliberate, reasoned in the tree, and paid for: fitting against a guessed clef
once read three flats as **two sharps**. After the move the reader still refuses
to *name* a key without a clef; what changes is that the run's **positions**
survive to the adjudicator, where the clef verdict is in hand and abstention is
recordable. The existing `key_signature_vote` evidence and
`key_signature_corroboration` become this decision's `Evidence` and `Verdict`
with their logic untouched.

**Seventh and beyond: the meter and the durations**, as one migration, because
§3.1 found them to be a genuine loop broken only by ordering. `Q.DURATION` and
`Q.METER` are both Verdicts; `_reconcile_measure_to_meter` becomes the design's
first `revises=`, carrying its own existing bound.

---

# PART 2 — THE MECHANISM ON THREE WORKED EXAMPLES

## 8.1 Why these three

The brief names them and they are well chosen: one is a **competitive decision
with five readers and no floor**, one is a **high-volume decision resolved by a
quantity measured to be a coin flip**, and one is the decision where **a
pre-registered gate falsified the obvious change**. Between them they exercise
every part of the design.

## 8.2 The clef — five readers, currently argmax with no floor

### Today

| reader | where | what happens to it |
|---|---|---|
| detector, measure cell | `_detections_for_cell:1816-1855` argmax → `clef_source="detector"` | **wins**, at any confidence — there is no floor |
| detector, header pre-pass | `_header_detections` at `:4711`, `_clef_from_dets` at `:4723` | ⚠️ **discarded by design** — `:4677` says so verbatim: *"it is not written to the output, and the measure pass below still reads the clef its own way"* — and measured to be the *same call on the same object*, divergent on 0 of 396 staves `[inherited]` |
| CV locator, header crop | `locate_clef` at `:4728` | read only if `_header_cell_beats_measure_cell` (`:1669`, called `:4940`) picks that crop |
| CV locator, measure cell | `locate_clef` at `:1953-1998` → `clef_source="cv_locator"` | ⚠️ silenced by **presence**, not by score: `if read_clef and locate_c_clefs and clef_source is None` |
| detector on the header crop | `:2021-2033` → `clef_source="detector_header"` | gap-fill only, same `clef_source is None` gate |
| clef specialist weights | `_read_staff_header` at `:2066-2107` → `clef_source="specialist"` | gap-fill only; `OMR_CLEF_WEIGHTS` off by default |
| dossier seed | `:2123-2140` → `clef_source="dossier"` | the one reader that **overrides regardless**, and it runs last |

The losing candidates *are* recorded — `clef_evidence["contest"]` carries
candidates, winner, runner-up, margin, `clef_in_effect_before/after`,
`overturns_inherited` — with **29 writer references and 0 consumers anywhere**
`[inherited]`.

### Under the design

**Gather.** Six row streams. The two detector rungs share a basis (they are the
same call) so `tally` counts them once — **without anyone having to notice.**
The locator runs on **both** crops unconditionally and emits an `Abstention`
naming its rejecting branch where it declines.

**Adjudicate.** `adjudicate_clef` declares its wants, scores candidates with
signed terms, and:

* returns `ABSTAINED(reason="margin_below_floor")` where the top two are within
  `CLEF_MARGIN_FLOOR` — **today there is no floor at all and the argmax always
  wins**;
* the harness excludes a `Q.CLEF_SEED` row on a dossier-seeded run
  automatically, because the seed's basis contains the join the dossier made —
  the same fact as CLAUDE.md's standing warning, obtained mechanically;
* the harness excludes a `score_order` `Q.INSTRUMENT` verdict and admits a
  `label` or `score_order_ambiguity` one, reproducing `clef_correction.py:566`
  and its deliberate exception (§4.2).

**What this makes visible that nothing does today:** the 14 staves where the two
crops disagree — 13 of them the header crop reading a C clef at symmetry
0.78–0.97 that the measure cell refused — become `differ` or `new_abstention`
rows in the divergence table instead of a gate's silent choice `[inherited]`.

⚠️ **This is reach, not accuracy.** 5 of those 14 have a final clef
contradicting the located one; **no page was hand-read**, so 5 is an upper bound
on defects, not a defect count. Converting it needs a human against the print.

⚠️ **Do not resurrect the adjacent-staff register→clef check.** Measured reach
7/193, precision **0 of 11** — every firing is a family boundary, because an
orchestral score is ordered by family, not by register `[inherited]`. Under
standing rule A00 that condemns *the adjacent-pair form*, not the mechanism:
comparing a staff against **its own** positions under different clef hypotheses
is untried and needs its own reach measurement first. `Q.STAFF_POSITION` is what
makes it expressible.

## 8.3 Glyph ownership — 4,521 contests, 94.1% decided by distance

### Today

`_dedupe_cross_staff_detections` (`transcribe.py:3054`) awards a contested glyph
by ledger ladder, then written range, then by **distance to the nearer five-line
band**. Its strongest tier needs identity, which runs **309 lines later**
`[inherited]`. The deferred pass that would use it (`OMR_ROSTER_RANGE_VETO`) is
off by default. On a scan the tier is additionally **vacuous**:
`_staff_written_ranges` returns `{}` with no dossier and the scan gate runs
dossier-free by protocol, so **all 4,256 duplicates resolve on ladder or
distance** `[inherited]`.

⚠️ **And the range tier's input is a resolved PITCH, which is an
interpretation.** `transcribe.py:3153-3154`:

```python
fit_i = _in_written_range(di.get("pitch"), ranges.get(si))
fit_j = _in_written_range(dj.get("pitch"), ranges.get(sj))
```

So ownership consumes the clef's output — verified in this tree. That is not a
cycle today (nothing feeds ownership back into the clef), but it is exactly the
edge that becomes one the moment a clef adjudicator reads ownership. Under this
design the tier's input becomes `Q.STAFF_POSITION` **plus the clef Verdict**,
which is the same arithmetic with its provenance visible — and the harness can
then see the loop if anyone ever closes it.

`contested_notehead_pairs` records both confidences and the deciding tier —
written at `transcribe.py:3242`, **read by no module** `[inherited]`, and ⚠️
gated by `OMR_CONTEST_DUMP`, **default off**, which is the "a recorder that is
switched off records nothing" fault the pipeline has already named (§6.1).

### Under the design

**The change is not a better rule. It is that the decision moves.** Ownership is
adjudicated after identity, which costs nothing because adjudication reads a
frozen record — Sean's *"all the info needs to flow in any direction once it is
gathered"*, and this is the clearest case of it.

**Gather** (`Q.GLYPH_BAND_DISTANCE`, `Q.GLYPH_LADDER`, `Q.GLYPH_CONF`, one row
per (glyph, candidate staff)) — including ⚠️ **the per-pair band distances and
ladder rung counts, which today's `OMR_CONTEST_DUMP` does NOT record** `[inherited]`,
i.e. the quantity documented as a coin flip is the one quantity not written down.

**Adjudicate**, signed terms in this order:

1. **ladder completeness** — an unbroken run of rungs. ⚠️ **Completeness only,
   never count**: two broken ladders are not evidence either way, because a
   found rung can belong to the other staff's note exactly as a gap can.
2. **written range** — a veto on the IMPOSSIBLE, never on the unlikely. Now
   available, because identity is already adjudicated.
3. **distance** — the tie-break, unchanged.
4. ⚠️ **confidence is gathered and NOT weighted.** P = 0.545 against a 0.500
   null; a tie-break on it would overturn 45.5% of contests `[inherited]`.

**What the record gains:** every contest carries which tier decided it *and*
`missing` — so *"the range tier was unavailable on this page"* is on the record
for 4,256 pairs instead of being a fact someone has to rediscover.

⚠️ **`Q.GLYPH_OWNER` carries no provenance tag today and that is currently moot**
— the fact has no cross-decision consumer `[inherited]`. Under this design it
gets one for free (`Verdict.basis`), which is bookkeeping until something
consumes it. **Say so; do not claim it as a win.**

## 8.4 Part boundaries — the one the gate falsified

### What happened, because the design must not repeat it

`export._stitch_slots` (`:3218`) decides what a `<part>` IS from **staff ordinal
alone**, refusing when systems disagree about staff count. `_stitch_slots_by_slot`
(`:3338`) is the stronger join, reachable only behind `OMR_SLOT_STITCH`,
default off.

The recommendation — *"consume `slot_index`"* — was falsified by a
pre-registered gate:

| population | result |
|---|---|
| where ordinal **succeeds** (2 of 3 documents) | slot and ordinal both match hand truth **exactly**, 100% per-staff, using the real exporter functions |
| where ordinal **refuses** (1 of 3) — the only population the change touches | the slot join **succeeds and is wrong on 3 of 27 staves (0.889)**: it fails to continue *"4 Hörner in Es"* across a tacet break and grafts the genuinely-tacet *"2 Trompeten in C"* slot onto the horn's continuation |

**Two lessons the design has to carry, and they are different lessons:**

1. ⚠️ **A completeness figure is not an accuracy figure.** `slot_index` was
   cited as *"set on 193 of 193 staves, measured"*. The probe behind that counts
   `len(slots)` and **never which staff landed in which slot**, so a 14-slot
   output that is wrong in three places and one that is exactly right are
   indistinguishable to it. In this design, coverage is `Verdict.outcome ==
   DECIDED` and accuracy is a `differ` row hand-adjudicated. **They are
   different columns of the divergence table and must never be summed.**
2. ⚠️ **The root cause is a provenance-chain violation, so the gate did not
   falsify the architecture — it exhibited it.** All four contested staves carry
   `instrument_source: "score_order"` — **no margin label was read** — and
   contextual is already wrong there, calling both horn-family staves *Trumpet*.
   `slots.assign_slots` inherits that into `slot_index`, and the exporter would
   have consumed a **deduced** identity as though it were a **read** one.

### Under the design

`adjudicate_part_partition` declares
`wants=(Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT, Q.SLOT_INDEX, Q.INSTRUMENT)`.
The harness resolves `Q.SLOT_INDEX` to a `Verdict` whose `basis` runs through an
`Q.INSTRUMENT` verdict, and the independent-witness rule (§4.2) fires:

| situation | outcome | mechanism |
|---|---|---|
| ordinal **succeeds** | no-op | measured identical to truth and to the slot join on 3 documents |
| ordinal **refuses**, slot identity has an OCR row in its basis | use the slot join | `label` / `score_order_ambiguity` admitted |
| ordinal **refuses**, slot identity has **no** independent observation | ⚠️ **`ABSTAINED(reason="deduced_anchor")`**, fall back to ordinal | the harness excludes it; **the decision writes no gate** |

On Brahms 1 p.2 all four contested staves are `score_order`, so **the measured
3-of-27 error never ships**: the row abstains and behaves exactly as today.

⚠️ **The reach of this is UNMEASURED and may be zero** — how many refusing rows
carry label-read slots is not known, and Brahms 1 p.2 has none. That is its
pre-registered gate, on the same terms the clef-contest reach gate was run:
**measure the population before claiming the accuracy.**

⚠️ **And a third failure shape neither this design nor that gate addresses,
recorded so nobody thinks it is covered.** `beethoven-sym5-mvt1-984073-p4`
prints 11 staves in both systems **with different lineups** — system 1 suppresses
Timpani and splits the bottom staff, system 2 keeps Timpani and condenses it. The
ordinal join's equal-count check **succeeds** there and is **still wrong**. No
transcription of that page is on disk, so it is flagged, not measured. What this
design contributes is only that `Verdict.considered` makes *"decided on zero
corroborating observations"* visible — an equal-count check is a constraint that
can be satisfied by accident, and today nothing distinguishes a partition reached
with three witnesses from one reached with none.

⚠️ **Before this step: replay both partitions over every stored transcription
under `OMR_SPAN_REFERENCE_FIT=off`**, the arm known to poison the reference — it
once named 149 Brahms staves an instrument the work has not got. That hazard is a
**bad ancestor**, not a circular one, and **no provenance tag fixes it**; the
replay is its guard.

---

# PART 3 — JUSTIFICATION

## 9.1 Why not incremental — the evidence, not the preference

Sean ruled on this and the ruling is well supported by the tree's own history.
**Four documents in one week each reduced to a point fix**, and the last one
reduced to *flipping a flag*: the gather-then-adjudicate document's single
recommendation was *"give `clef_evidence["contest"]` its consumer"*, the reach
gate cleared, and the finding was *"the consumer already exists, is disabled, and
its coverage table is two rows long."*

That is not bad luck. **One bespoke consumer for one orphan record is a point fix
by construction** — it creates one coupling and leaves the next orphan costing
exactly as much. There are three orphan records (`pitch_candidates`,
`clef_evidence["contest"]`, `contested_notehead_pairs`) and the fourth one that
got a consumer got a *bespoke* one.

The generalisation is one *shape*, and this design's claim is that after §7.1
lands, decisions four, five and six cost the same as decision three.

## 9.2 Why this is a generalisation and not a rival vocabulary

Every element below already exists. `git log --all -S 'class Observation'`,
`-S 'def adjudicate'` and `-S 'EvidenceLog'` over `tools/` each return
**nothing**, so the *plumbing* is genuinely unbuilt — but the *shapes* are not:

| this design | the thing it generalises | status |
|---|---|---|
| `Verdict.basis` + the independent-witness rule | `instrument_source` (4 values, `contextual.py:1235/1247/409`), `clef_source` (7 values), `time_signature["source"]` / `rhythm._READING_SOURCES` (`rhythm.py:501-507`) | the tags stay; the rule is one more reader of them |
| a decision returning `(value, record)` | **`key_signature_corroboration.drop_uncorroborated_key_changes`** (`:333`), default-ON 2026-09-07 — the pattern that already landed | the model, not a replacement |
| `Ruling.reason` from a closed vocabulary | ⚠️ **`propose_clef`'s `_note(exit_, **fields)` closure** (`clef_correction.py:239-243`) — the tree's cleanest *"a decision declares its exit"* primitive, with labels like `no_clef_anchor`, `already_in_effect`, `no_candidate_clefs` | **copy this**, do not design a rival |
| signed `Term`s with a threshold | `slots._pair_score` (`:472-490`), `score_layouts._pair_score` (`:338-355`) | same shape, made reusable |
| a term **withheld** when its evidence is incomparable | `slots._pair_score`'s group term — `group_map is None` withholds rather than guesses, because *"a wrong group verdict is worth 3.0 against a position signal worth ~0.05"* | this is `State.ABSENT` (§2.2), already in the tree |
| a term's weight conditioned on **provenance** | ⚠️ `score_layouts.SCORE_TREBLE_CONFLICT = -0.3` against `SCORE_CLEF_CONFLICT = -1.5` — a *treble* reading is weak evidence because treble is both the failure mode and the positional default | the nearest existing thing to what this design generalises |
| judge everything, then apply strongest-first | `_dedupe_cross_staff_detections` — verdicts collected as `(rank, loser, winner)` at `:3126-3177` and applied in rank order at `:3244-3248`, documented at `:3105-3117` as the fix for order-dependence | this is `Ruling` → `Verdict`; already in the tree |
| per-decision `excludes_tiers=` | ⚠️ `VETOABLE_SOURCES` is `("label",)` in `absent_instrument.py:66` and `("score_order",)` in `offroster_name.py:89` — **deliberately inverted**, each with its own measured justification | admissibility is per-consumer, not global. The design must not unify them |
| `Mode.ADDITIVE` | `clef_continuity`, `_fill_defaulted_clefs` (`contextual.py:182`) | named, not invented |
| bounded `revises=` | `_reconcile_measure_to_meter`'s ±1 / exact / unique / single-voice | the bound is copied, not loosened |
| the EVENT-shaped log | `rhythm_reconciliation`, `key_signature_corroboration` | already the right shape, twice |
| the divergence table's columns | `label_contradiction.summarise` (`:136-151`) — numerator, denominator and two histograms | the shape for any adjudicator's report |
| a decision that refuses to default silently | `apply_contextual_analysis` raises `TypeError` if `assist is None` (`contextual.py:986-991`) — no silent default for a decision that *spends* something | the precedent for `UndeclaredEvidence` (§2.4) |

⚠️ **`veto_implausible_clef_changes`, `key_signature_corroboration`,
`clef_continuity` and `apply_contextual_analysis` are NOT to be reimplemented.**
Each becomes a *decision function* — its body kept, its inputs arriving through
`Evidence`, its record becoming a `Verdict`. The design moves their plumbing, not
their logic.

⚠️ **And before building anything: `git log --all --oneline -S "<the thing>" --
tools/omr/`.** This project has built a duplicate of a landed export fix once,
and `hairpin_detection.py` is a whole reader whose docstring reports shipped
results for code with no call site.

## 9.3 What this design does NOT claim

* **It does not claim an accuracy improvement.** Nothing here has been scored.
  The divergence table is a *population*, and every `differ` row needs a human
  against the print before it is a win or a loss.
* **It does not parallelise anything** (§3.1) and does not estimate a saving.
* **It does not repair the three dead carries.** That is a defect with an
  **UNMEASURED** blast radius and deserves its own decision; the design makes it
  *visible* (a carry that never fires shows as `ABSENT`, not as a good default)
  and stops there.
* **It does not fix the `*_final` fields** (§5.1) — it derives them from one
  writer on the flag-on path and leaves the question of deleting them open.
* **It does not touch the readers, the weights, or any corpus.**

---

# PART 4 — WHAT IS UNMEASURED HERE

* **Everything about accuracy.** No arm was run. No `scan_eval`, no
  `orchestral_eval`, no transcription.
* **Whether the independent-witness rule reproduces the three refusals**
  (§4.2). It is derived from `contextual.py:1208-1209` (`fit_layouts(...,
  clefs=clef_by_slot)`), which is re-read in this tree — but the **basis chains
  themselves have not been built or run**. This is acceptance test §7.1(4) and
  the design's first falsifier.
* ⚠️ **The hard-edge count is now MEASURED, not inherited, and the input
  document was wrong.** All five rows of §3.1 were re-read in this tree:
  gathering has **three** hard edges, not two, because the meter vote consumes
  the `duration_beats` field rather than a conclusion. `clef → key signature` is
  soft in the geometry and hard as coded. This is the one premise the brief told
  me to verify before building on it, and verifying it changed a build step
  (§7.4, sixth) and forced a classification (`Q.DURATION` is a Verdict, not a
  measurement). **What is still unmeasured is whether §3.1's list is now
  complete** — nine further input edges were found and are listed in §7.1(3),
  and a tenth is not ruled out. §7.1(3) is the standing assertion.
* **The reach of every migrated decision**: grouping (⚠️ and it *cannot* be
  measured from committed artefacts — 890 of 1338 stored staves carry
  `group_index: null` and no stored scan carries the fact at all), clef, part
  boundaries, ownership.
* **The cost of the log.** Row volume on a dense orchestral page is not
  estimated. `Observation` is `slots=True` and frozen for that reason; if it
  matters, it will show as wall clock in `shadow` mode and is a `shadow`-only
  cost.
* **Whether `contextual.py:1451`'s `.get(slot, "label")` default is reachable.**
  The *shape* is the finding (§2.1); the reach is not measured.
* **Every figure quoted from another benchmark** — 4,521 contests, P = 0.545,
  0 of 396 divergent detector rungs, 14 divergent crops, 22/39 bracket recall,
  the ECE figures, the 67-transcription grouping replay, `[2,2,2,2,2,7,1,3]`,
  the fill-tier funnel, the `*_final` staleness counts. **Cited with source; not
  re-run here.**
