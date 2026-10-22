# The staged pipeline's decisions, derived — and what the derivation found

`python3 -m tools.omr.staged.inventory` — the table is
[INVENTORY.md](INVENTORY.md), the machine copy `out/inventory.json`. Nothing
in either is typed: every column comes from `adjudicate.REGISTRY` (the
`@decision` decorator), `adjudicate.ORDER`, `evaluate.RULES`, `groups`'
redundancy declarations, `legacy.EXTRACTED_QUANTITIES` and the AST of
`gather.py`. `--check` exits non-zero on a broken invariant, the way
`export_coverage` does.

---

## 1. ⚠️ FIVE OF THE SIX STUBS ARE STARVED ONE STAGE EARLIER

The handoff records 6 declared stubs and says *"everything else in there is a
stub that can be filled incrementally."* Derived, that is true of exactly one
of them.

| stub | its input | gathered? |
|---|---|---|
| `arc_owner` | `arc_box` | **never, anywhere** |
| `arc_kind` | `arc_box` | **never, anywhere** |
| `articulation_owner` | `articulation_mark` | **never, anywhere** |
| `wedge_anchor` | `wedge_box` | **never, anywhere** |
| `dynamic` | `dynamic_letter` | **never, anywhere** |
| `direction` | `direction_word` | yes — `gather_direction_text`, which abstains `not_implemented` behind a declared hard edge |

`grep -rl 'Q.ARC_BOX' tools/omr/staged/` returns `adjudicate.py`,
`record_coverage.py` and `adjudicators/ownership.py` — the vocabulary, the
coverage checker and the stub's own `wants`. **No gather site.** Same for the
other three.

**So writing those four adjudicators would still produce nothing.** The work
is in GATHER, and the stub declaration does not say so: `stub=True` means
"this decision is not written", not "and the page is never read for it
either". Two gaps wearing one name — the same shape as `entire staff` being
four problems, and as the six stubs looking like one class of work.

⚠️ It also bounds the exporter: **arcs, articulations, hairpins and dynamics
cannot reach a staged file at all today**, and no amount of exporter work
changes that. That is a fact about the record, not about the writer.

## 2. `tuplet_ratio`'s missing row is THE PAGE, and here is the positive control

The handoff asks whether `tuplet_ratio` producing no row of any kind on
Mahler p2 is the page or the wiring. Derived answer, then measured:

* **The mechanism.** `adjudicate_tuplet` declares `subjects_from=Q.TUPLET_MARKER`.
  `adjudicate.subjects_for` returns the subjects carrying a row of that
  quantity, so an empty domain means **zero subjects, therefore zero
  verdicts** — not an abstention. Only `gather_rhythm_marks` writes
  `TUPLET_MARKER`, and only for `tuplet3` / `fingering3` / `tupletBracket` /
  `tupleBracket`.
* **The page.** Mahler p2's record holds no `tuplet_marker` row at all.
* **THE POSITIVE CONTROL.** Same tree, same weights, same CLI, one page over:
  **Beethoven 5 / Litolff `984073` `--pages 2` reads 1 `tuplet_marker` and
  decides 1 `tuplet_ratio`** — and is the only one of four pages run where
  `--run` reports *"every decision wrote at least one row"*.

| page | systems | `tuplet_marker` | `tuplet_ratio` |
|---|--:|---|---|
| mahler p2 | 1 | — | **no row** |
| beethoven 984073 p2 (`--pages 1`) | 1 | — | **no row** |
| **beethoven 984073 p3 (`--pages 2`)** | **2** | **read 1** | **decided 1** |
| brahms 317803 p2 (`--pages 1`) | 2 | — | **no row** |

**It is the page.** The wiring is sound and is pinned by
`test_staged_duration.py`.

⚠️ **But the SILENCE is a real hole and is not specific to tuplets.** Any
decision with a `subjects_from` domain writes nothing when that domain is
empty, and nothing in the record says it was supposed to appear.
`adjudicate.NoDecisionsRegistered` states exactly this principle one level up
— *"a stage that produces no verdicts because nothing was loaded is
indistinguishable from one that produced no verdicts because it had nothing
to decide"* — and it is not applied per decision. `inventory --run` is the
cheap version of the fix: read the registry against the record and name what
is missing. `glyph_owner` (`glyph_band_distance`) and `duration`
(`notehead_class`) can go silent the same way.

## 3. The redundancy layer: the handoff's diagnosis is right, its control page was wrong

The handoff proposes *"Beethoven 5 / Litolff p.2 (`--pages 1` of `984073`)"*
as the multi-system control. Run, that page reports **`system_membership:
{decided: 1}`** — one system, and all four `across_systems` groups
`checked_nothing` again. `works.json` says why and is hand-verified:
`984073`'s two-system page is `pdf_page_index` **2**, not 1.

On the right page the layer works:

| group | beethoven p2 (1 system) | **beethoven p3 (2 systems)** |
|---|---|---|
| `clef_across_systems` | 12 facts, single ×12 | 11 facts, **unanimous ×8**, split ×1, single ×2 |
| `staff_group_across_systems` | 12 facts, single ×12 | 11 facts, **unanimous ×11**, uninformative 0 |
| `checked_nothing` | 4 groups | **2 groups** |

**So the layer is not inert; the fixture was.** Judge it on `--pages 2`.

⚠️ **And a second, separate result: Brahms p2 IS two systems and still reports
all four `checked_nothing`** — 27 facts for 27 staves, one witness each. That
is not the same failure and it is not a defect either: `groups._slot_fact`
puts the system's STAFF COUNT in the join key on purpose, and Brahms p2's two
systems print 14 and 13 staves (the suppressed Trompeten), so
`("slot", n, "of", 14)` never meets `("slot", n, "of", 13)`. **The redundancy
layer's cross-system correspondence is exactly as good as the ordinal join
and inherits its refusal** — the same population `export._stitch_slots`
refuses and `OMR_SLOT_STITCH` was flipped on for. `_slot_fact`'s docstring
declares that cost; this is the first measurement of what it costs on a real
page: **all of it, on the pages that need it most.**

⚠️ `instrument_across_systems` is `witnessed_by_nobody` on **all four pages** —
`instrument` abstained on every staff, because every `margin_label` was
declined. Consistent with the standing measurement that 29 of 29 unresolved
non-treble staves on this corpus print no label at all.

## 4. What the derivation checks

`--check` is non-zero on any of these, and each is a way for a decision to be
silently unreachable rather than a style rule:

* a decision registered but absent from `ORDER` (never runs) or named in
  `ORDER` with no adjudicator;
* a `wants` entry that no gather site observes and no decision produces;
* a `wants` VERDICT that `ORDER` runs *after* the consumer — `Evidence.verdict`
  returns `None` rather than raising, so this fails silently forever;
* a `subjects_from` domain nothing produces;
* a consequence whose `cause` is not a registered decision;
* a declared stub whose input is also never gathered.

⚠️ **Two of the checks were wrong when first written, and both false alarms
are recorded in the code.** A literal-argument AST matcher missed
`gather_cv_lines`' `for quantity, kind in ((Q.STEM, …), (Q.BEAM_STROKE, …))`
and reported `duration` unsatisfiable; and treating `verdict` and
`measurement` as exclusive made `system_staff_count` — which is BOTH — look
like a dependency cycle in `system_membership`. Both are pinned by
`test_staged_inventory.py`, which also mutates `ORDER` to prove the ordering
check can fail.
