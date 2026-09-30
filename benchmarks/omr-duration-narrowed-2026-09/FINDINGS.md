# `duration_narrowed` triage — ROADMAP 2.36

STAGED only. Read-only triage of the two 2026-09-29 afternoon acceptance
records (`benchmarks/acceptance/manifest.json`), loaded via plain
`json.loads` (no `record_io.expand_id_lists` — `reason`/`candidates`/`detail`
are never pooled, only `considered`/`basis`/`correlated` are, so this
tabulation needed no pool expansion). No re-gather, no re-adjudication, no
crop batches — one parse of each committed file, once, unattended.

Scripts: `triage.py` (ranks every NARROWED `Q.DURATION` verdict by reason,
candidate set and disagreement class) and `chord_reach.py` (measures one
candidate connection's reach before building it). Raw output in `out/`.

## 1. The ranked table

| reason | Litolff (n=1,187 narrowed) | Brahms (n=3,211 narrowed) |
|---|---:|---:|
| `beams_ambiguous` | 779 | 1,960 |
| `beam_discounted_uncertain` (2.25b) | 320 | 1,102 |
| `flags_disagree` | 5 | 75 |
| `flag_ink_unread` (2.18c) | 23 | 54 |
| `rest_slot_contradicts_class` | 38 | 11 |
| `head_fill_from_ink` (2.23) | 22 | 9 |

(`n_narrowed` here is the raw ADJUDICATE-level count before EVALUATE's
`reconcile_duration` bar-sum repair runs — EXPORT's own `duration_narrowed`
bucket after that repair is smaller: ~902 Litolff, ~2,559 Brahms per
`benchmarks/acceptance/current.json`.)

`beams_ambiguous`'s own disagreement classes (`by_disagreement_class` in
`out/*.json`), both documents dominated by the same shape:

| disagreement | Litolff |
|---|---:|
| `beam_count_certain=0_possible=1` | 495 |
| `beam_count_certain=1_possible=2` | 132 |
| `beam_count_certain=0_possible=2` | 51 |

"certain=0, possible=1" is *"nothing certainly covers this note, but one
stroke might"* — the biggest single bucket in both documents by a wide
margin (Brahms's own breakdown is in `out/brahms.json`, same shape).

## 2. Does the biggest class FOLLOW from anything filed? Measured, not guessed

**No connection was found for `beam_count_certain=0_possible=1` itself.**
It is a first-hand geometric judgement about ONE stroke's relationship to
ONE note (`rhythm._beam_levels`), and nothing else on the record witnesses
the same fact from a different angle — the ambiguity is genuinely
undecidable from what is filed today. Deciding it would need a NEW reader
(a second, independent measurement of "does this stroke belong to this
stem" — e.g. an ink-continuity test between the stem's own pixels and the
stroke, in the shape of 2.18c's `Q.STEM_TIP_INK`, but for the BEAM rather
than the flag). **Not built here** — building it without a second witness
would be exactly the guess CLAUDE.md rule 6 forbids.

## 3. The connection that DOES follow: a chord's members share one stem

A physical fact of notation, not an inference: two noteheads struck on ONE
stem are one note event and carry one duration. The record already states,
per glyph, which `Q.STEM` observation its own head box overlapped
(`rhythm._stem_joined`'s `attached`, written into `Ruling.used` by
`adjudicate_duration`) — so two glyphs whose `Q.DURATION` verdicts both name
the SAME stem row are provably chord mates, no re-measurement needed.

**Reach measured first** (`chord_reach.py`, CLAUDE.md rule 5):

| | Litolff | Brahms |
|---|---:|---:|
| narrowed notes (rests excluded) | 1,149 | 3,200 |
| … with a stem in their own `used` | 633 | 1,783 |
| … with >=1 DECIDED stem-mate | 49 | 63 |
| … with EXACTLY ONE DECIDED stem-mate | 38 | 40 |
| … whose narrowing already admits that mate's level -> **would be DECIDED** | **32** | **37** |

All 69 resolved rows are `beams_ambiguous`. This is modest — about 2.8% of
Litolff's narrowed notes, 1.2% of Brahms's — and it is reported as modest
rather than inflated: most narrowed notes have no stem in `used` at all (the
majority of `beams_ambiguous` is a single, un-beamed-looking note with no
sibling to connect to), and most that DO have a stem have no DECIDED
stem-mate in the same bar (chords are a minority of notes). It is the
connection that FOLLOWS, not the biggest bucket.

### Wired (EVALUATE): `consequences.reconcile_chord_duration`

New rule, `tools/omr/staged/consequences.py`, registered under a new
`Consequence.RECONCILE_CHORD_DURATION` tag (kept separate from
`RECONCILE_DURATION` — the existing `test_the_rule_is_downhill_and_carries_a_
bound` in `test_staged_duration.py` picks `evaluate.RULES` by consequence
tag and expects exactly one row per tag; giving the new rule its own tag
avoided colliding with that test rather than weakening it). Same
`cause=Q.METER`, `effect=Q.DURATION`, `scope=Kind.CELL` as
`reconcile_duration`; registered earlier in the file so it runs FIRST in the
same EVALUATE pass (file order is the stable-sort tie-break for rules
sharing a cause), letting a chord-settled note feed the bar-sum search that
follows it.

Per cell: for every NARROWED, non-rest `Q.DURATION` verdict, find the
`Q.STEM` ids in its OWN `used` (not `considered`/`basis` — `adjudicate_
duration` reads EVERY stem in the cell into those, the same set for every
note in the bar; only `used` narrows to the ids `_stem_joined` actually
attached to THIS head's box). If exactly one OTHER glyph's DECIDED duration
in the cell shares one of those ids, AND that mate's own `beam_levels` is
one of the narrowing's OWN candidates, decide it to that candidate. Refuses
(stays NARROWED) on: no stem in `used`; zero or >=2 decided stem-mates
(ambiguous which stem is this note's own — rule 8); a mate level the
narrowing never offered (never invents past what the reader admitted —
caught the `head_fill_from_ink` case directly, where three candidates all
carry `beam_levels: 0` and a beam_levels-0 mate would otherwise look like it
picks one arbitrarily).

### Tests (RED confirmed, GREEN after)

`tools/omr/tests/test_staged_chord_duration.py`, 12 tests. RED confirmed by
copying `origin/main`'s `consequences.py` in over the edited file and
running the suite (12/12 fail with `AttributeError`, the function does not
exist there), then restoring the edited file (12/12 pass). Positive case +
one variant (candidate order doesn't matter, only membership); seven
negative controls (no shared stem; empty `used`; two disagreeing decided
mates; a mate level never offered; the `head_fill_from_ink` three-way-tie
case; a rest, defensively, though `_is_rest` already excludes it
structurally — no rest-reading function touched; no decided note in the
cell at all); a provenance check (superseded row stays on the record); two
registration checks (it is downhill/bounded; it runs before
`reconcile_duration` in the same pass).

## 4. Not built

- The biggest class itself (§2) — needs a new GATHER-side witness, named,
  not built.
- `beam_discounted_uncertain` (2.25b's own rule 8 narrowing) and
  `flags_disagree` were checked against the same chord-mate connection by
  the same script logic (any reason qualifies structurally) — the 69
  resolved rows above are ALL `beams_ambiguous`; no `beam_discounted_
  uncertain` or `flags_disagree` row happened to have a qualifying decided
  stem-mate on either acceptance record. Not a design gap — just this
  population's shape today.
- `rest_slot_contradicts_class` — a rest carries no stem and is out of
  scope for this lane (rest-related functions and `family_precision.py` are
  reserved for the concurrent 2.35 lane).
- `head_fill_from_ink` beyond the guard above — no connection attempted;
  the mate speaks to beam count, not notehead fill, and the two must not be
  conflated.

## 5. Questions for Sean

- Is "two noteheads on one stem share one duration" itself something worth
  spelling out as a rule/DECISIONS line, or is it self-evident enough to
  leave as code commentary only (it is notation, not a convention with an
  edge case)?
- Worth a follow-on lane building the missing GATHER-side witness named in
  §2 (a beam/stem ink-continuity test, mirroring 2.18c's `Q.STEM_TIP_INK`
  but for beam strokes)? That is the one that would move the biggest
  bucket, and it was intentionally NOT built here (no second witness to
  connect it to yet).
