# Overnight session plan — 2026-09-01 → 09-02

Written at the start of an unattended overnight session on branch
`claude/transcription-overnight-progress-426c90`. Sean asked for an assessment
of where the project stands and a plan for the next big parts of transcription
improvement, executed as far as possible overnight. This file records the
assessment and the plan as decided *before* the work; the morning summary
(`docs/overnight-2026-09-01-summary.md`) records what actually happened.

---

## Assessment — where transcription stands tonight

Four facts organize everything:

1. **Engraved-domain recognition is deep into diminishing returns on a
   three-page benchmark.** Pooled OMR-NED went 0.3164 → 0.1364 (966 edits) in
   two days — sixteen landed fixes, five of them export bugs on data already
   computed, three placement, three thresholds in the wrong unit. The residue
   is now idiosyncratic: a bassoon pair worth ~8 edits, a triplet group that
   carries no marker at any confidence, two `[` `]` glyphs the lexicon rightly
   refuses. Every one of those sixteen fixes was tuned against the same three
   pages (Beethoven 5, Brahms 1, Mahler 5 openings, LilyPond-engraved).

2. **The project's own most-repeated lesson applies to its main benchmark.**
   "A benchmark that cannot go down cannot show an improvement" (clef 52/52 →
   widened to 166 and two conclusions reversed); "a sweep corpus cannot price
   what a rule costs" (second edition took clef FPs 7 → 48); "agreement across
   staves cannot catch an error every staff shares." The 3-work engraved
   benchmark now *selects for the pages everything was tuned on*. Nothing
   currently measures whether the sixteen fixes generalize even to other
   **engraved** pages, let alone scans.

3. **The scan domain — the actual use case — has exactly one measured page.**
   Beethoven 5 p.1, OMR-NED 0.8706, explicitly "a starting point, not a
   regression baseline." Sean's real inputs are scanned IMSLP editions; the
   score library pairs **27 works** of edition PDF ↔ reference MusicXML and
   nothing consumes those pairs as a benchmark. The known scan blockers
   (hollow noteheads → labeling batch, prepared, needs Sean's hands; key
   signatures 7/12; instrument labels) were all found on that *single page* —
   there is no evidence yet about what breaks on pages 2–N or other editions.

4. **The clef ceiling is labels, not clef reading** (146/166 free, 17 of 21
   remaining errors are the positional default; the machinery to replace it is
   starved of instrument names). The paid margin reader closes 3 more. This is
   understood and does not need more overnight measurement — it needs either
   more text-layered editions or acceptance of the paid rung.

### What this implies

The next big parts are **measurement-led generalization**, in this order:

- **Widen the engraved corpus** — cheap (the machinery exists: 97 dossiers,
  `orchestral_eval --works` takes any of them), and every past widening found
  real bugs within hours. This is the fastest source of the next ranked
  fix list.
- **Make the scan domain a tracking number, not an anecdote** — build the
  edition-PDF ↔ reference-MXL pairs into a scan benchmark. Higher effort
  (reference must be trimmed to the measures the scanned pages cover) but it
  is the domain Sean actually processes.
- **Key signature from the music** — the one recognition feature Sean has
  explicitly asked for that remains untouched. Research-first: establish
  whether the failure is reading or detecting before building.
- **Close the open assessment** on `claude/omr-dossier-verification-layer-eaf6d0`
  (the last branch with a capability main lacks).

Explicitly **not** for tonight: anything on the do-not-spend-time list
(detector fine-tuning, synthetic augmentation, VLM transcription, system-break
threshold rules); the hollow-notehead labeling batch (human work — it is
prepared and waiting for Sean); the direction-text default-on decision (Sean's
call); training-run escalations (budget decisions).

---

## The plan

### Workstream A — widen the engraved benchmark (opus agent, first)

Run `orchestral_eval --omr-ned` over ~6–10 additional dossier works chosen for
composer/texture diversity. Rules of engagement:

- The canonical 3-work pooled figure and `DEFAULT_WORKS` are **untouched**;
  new works are reported as their own table in
  `benchmarks/omr-corpus-widening-2026-09/`. The single-home rule for the
  pooled figure (CLAUDE.md only) stands.
- Deliverable 1: per-work OMR-NED + note recall + the top edit buckets, and a
  **ranked list of new systematic failure modes** with op-list evidence
  (open the ops before believing a bucket — standing rule).
- Deliverable 2: fixes for the clearly-mechanical failures found, one at a
  time, each measured on canonical-3 + the new works. A regression on
  canonical-3 means stop and record.

### Workstream B — scan-domain benchmark v1 (opus agent, scoping in parallel, build after A lands)

`benchmarks/omr-scan-e2e-2026-09/`: 3–5 scanned editions from the library's 27
paired works, first page(s), scored against the reference MusicXML trimmed to
the measures the pages cover.

- Protocol follows `benchmarks/omr-first-run-2026-08`: defaults, **no dossier
  seeding** (the dossiers derive from the truth files — answer-key rule).
- Page → measure coverage is hand-verified per page (render the page, count),
  never inferred from the OMR output being scored.
- Deliverable: a runner + RESULTS.md + per-work rows + ranked scan-side bug
  list; explicitly marked as the scan baseline row set going forward.
- Also answers: is the hollow-notehead counter-closing failure a property of
  one 600 dpi bitonal print, or of scans generally? (Prices the labeling batch.)

### Workstream C — key signature from the music (opus agent, research-first)

Handoff item #9, explicitly wanted by Sean. Phase 1 (tonight): attribute the
known failures (Beethoven 5 p.15 reads 0 sharps/0 flats on a C-minor movement
carrying 33 inline flat detections; Boléro p.10 reads five signatures across 32
staves) — is the signature *detected-and-dropped* (the beams/dots/dynamics
shape: check upstream signal first, standing rule) or genuinely unread, and
would a movement-level vote over inline accidentals be corroborated enough to
speak only into gaps? Constraints from the record: **never** per-staff key-profile
fitting (measured as noise); a wrong signature costs more than a missing one,
so any implementation must abstain by default and be 0-wrong on the existing
ground-truth corpus. Phase 2 (only if Phase 1 supports it): implement + measure.

### Workstream D — branch assessment (sonnet agent, anytime)

Read-only assessment of `claude/omr-dossier-verification-layer-eaf6d0` (handoff
item #14): what does it have that main lacks (dossier-steered re-segmentation
on a known bar count), is it worth porting against today's main, and what would
the port cost. Deliverable: a short assessment doc; no merge.

### Execution discipline

- Baseline first: `orchestral_eval --omr-ned` must reproduce ~0.1364/966 in
  this worktree before anything builds on it (running now).
- Heavy compute serialized — one full benchmark run at a time on this machine.
- Every landing: tests → measure canonical benchmark on the tree being
  committed → commit → push. Docs at every natural breaking point.
- Morning deliverable: `docs/overnight-2026-09-01-summary.md` with what
  landed, what was measured and refused, and the ranked morning-after list
  (including: serve the hollow-notehead labeling batch for Sean).
