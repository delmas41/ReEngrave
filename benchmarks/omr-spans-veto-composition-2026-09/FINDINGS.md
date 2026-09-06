# Spans and the veto, composed: the 2×2

Two independently-built fixes for the same bug — **91 of 855 staff records
before Beethoven 5's finale naming an instrument the movement does not contain**
(Trombone ×75, Contrabassoon ×10, Piccolo ×6, on 24 pages; violins coming out as
trombones). Both merged **default-off**: `OMR_MOVEMENT_REFERENCE` and
`OMR_ABSENT_INSTRUMENT_VETO`.

*(Written up by the coordinating session from the agent's report and its three
commit messages — its harness refused a `.md` file.)*

---

## The 2×2 — whole work, 88 pages, 1616 staff records, ONE shared read pass

| | IMPOSSIBLE | correct | wrong | unnamed |
|---|--:|--:|--:|--:|
| spans off / veto off | **91** | 750 | 57 | 0 |
| spans off / veto on | 0 | 750 | 50 | **7 refused** |
| **spans on / veto off** | **0** | **756** | 51 | **0** |
| spans on / veto on | 0 | 756 | 51 | 0 |

**The baseline reproduces 91 exactly** — same instruments, same 24 pages — and
the scorer refuses to let the other arms be read if it does not.

One shared read pass served to every arm through a patched `_labels_for_page`,
so the only difference between cells is the flags. That also removes the
recorded Surya nondeterminism from a comparison whose entire content is a few
dozen names.

## ⚠️ The hypothesis was WRONG, in the useful direction

It read: *spans keep the 18 while the veto removes the 91.* Measured:

- **Spans alone remove all 91 — by NAMING, not refusing.** Correct 750 → **756**,
  wrong 57 → 51, nothing unnamed. That is the better kind of fix: it does not
  merely stop asserting a falsehood, it supplies the truth.
- **The veto alone also removes all 91**, at 7 refusals, and **all 7 removed a
  name that was wrong** — correct unchanged at 750. Reproduces the veto branch's
  "zero correct lost" through a different harness.
- **The veto adds NOTHING on top of spans** — that row is identical with it on
  and off.
- ⚠️ **Spans do NOT recover the 18.** Attestation is computed over the
  *document's* labels and spans do not touch it, so once spans are on the veto's
  entire residual effect is 18 refusals — **a pure cost, unpriced rather than
  disproven**, since reduced systems carry no full-lineup truth to score against.

## ⚠️ The interesting failure EXISTS, and it argues for keeping both

Pre-registered as the thing to watch for: *a span boundary that licenses an
instrument the veto would have refused.*

On the whole work it does not happen — 91 re-licensed, 0 still finale-only.
**On a truncated page set, spans alone make it WORSE**: re-taking the movement
branch's own 24-page window, impossible goes **44 → 57**, turning 9 correct
string names into `Trombone`. The veto then cleans it up (57 → 0).

**The mechanism was measured, not inferred**, off the same page cache: **it is
not the segmentation** — both page sets cut into two spans of identical shape at
page 44. It is the span's *own reference*. **A span that lacks its movement's
opening page has no fully-labelled system**, so its three unlabelled string slots
are placed onto the document's three Trombone slots by position alone, and every
12-staff system in the span inherits it.

> **So the two fixes are NOT redundant: which one carries the load depends on
> whether the run contains its movement's opening page — and the case where
> spans fail is created by spans.**

⚠️ It does **not** argue for the veto running *inside* spans. The composition as
built already catches it (the veto reads `slot_by_staff` after spans write it),
and moving it inside would hand it a strictly smaller attestation set.

## ⚠️ The movement branch's own number moved, and neither figure travels

Its pre-merge `47 → 0` against **`44 → 57`** here. Two things differ and were
separated: `replay_slots` runs at **dpi 300** and models label-sourced identity
only; this harness runs real `apply_contextual_analysis` at **600**. At 300 dpi
page 44 misreads as 14 staves of 17 — the very case the branch's
`_first_page_above` repairs; at 600 it reads 17 and that repair never fires.

**Neither difference explains the sign reversing** — the span-reference mechanism
above does. **Quote neither number for the other's configuration.** The
unambiguous figure is the whole work: **91 → 0, +6 correct, nothing refused.**

## The residue is one known bug, repeated

Under spans, what remains is **`Timpani → Trumpet`, 51 times, and nothing else.**
That is the ambiguous-alias family (`Tp.` is Timpani in the German and Italian
traditions and Trumpet in the English one) — flagged independently by two other
agents the same day, and **not this bug**.

## Controls

109 vetoes spans-off (the veto branch's figure, different harness) · pages 23,44
→ 7 vetoes, Trombone ×6 + Cello ×1 (its control) · 210/1616 slots move under
spans · `report` == `apply` verified (slot map, veto set and slot names all
identical) · staff ordering **measured not assumed**: 0 disagreements over 140
systems, and the judgeable rule returns **exactly 807** — the veto branch's
figure, via a different field on a different artefact.

## ⚠️ Neither standing benchmark can price this, provably

All 20 scan-gate rows and every `orchestral_eval` excerpt are **single-page**.
The veto is inert there by construction (attestation distance is always 0) and
spans take no boundary (recurrence confirms one). **Both flags are no-ops on
every row of both benchmarks**, so neither was run: a flat figure would be
coverage of nothing. That is the fifth consumer this week settled by its
*population* rather than its quality.

Also surfaced, not this bug: the document reference names its bottom slot
`Bass voice` rather than `Contrabass` — the Litolff contrabass abbreviation, the
same lexicon family. And one full-suite failure
(`test_direction_text::test_the_env_var_restricts_the_rungs`) is a **pre-existing
cross-test env leak**, passing alone and alongside both branches' test files.
