# Does the slot partition match hand-read truth where the ordinal join refuses?

**On the one distinct document where the ordinal join refuses and hand-read
truth exists — Brahms 1 / Breitkopf p.2 — the slot partition (`export.
_stitch_slots_by_slot`) does NOT match the truth.** It misgroups 3 of 27
staves (89% correct, not 100%): it fails to continue the "4 Hörner in Es"
staff across the system break, and instead merges the truly-tacet "2
Trompeten in C" staff into that Horn's slot. This directly falsifies the
specific claim in `docs/scope-part-correspondence-2026-09-07.md` that on
this exact row "the slot join expresses exactly the tacet case the page
prints." Where the ordinal join *succeeds* the two joins still agree
(3 of 3 distinct documents, 100% per-staff, exact partition equality) —
that earlier finding stands. But the refusing population — the only
population the proposed change would newly touch — is 0-for-1 on the only
document available to test it.

Reach is thin and stated plainly below: only **3 distinct documents**
carry both (a) a stored transcription and (b) a hand-read truth map, and
only **1** of those has the ordinal join refusing. This is a kill of the
specific evidence the recommendation cites, not a high-confidence
population estimate — n=1 in the population that matters. Do not read
"1 of 1 fails" as "the slot join is reliably wrong"; read it as "the one
piece of evidence offered for 'exactly right' does not hold up," which is
enough to block shipping on the stated justification.

## Reach: what could and could not be tested

`benchmarks/omr-scan-e2e-2026-09/works.json` holds 20 rows. Of those:

- **9 excluded, single-system** (the join is a no-op there — partition
  correctness cannot be exercised): `beethoven-sym5-mvt1-984073-p1`,
  `beethoven-sym5-mvt1-575951-p1`, `dvorak-sym9-mvt1-405834-p5`,
  `dvorak-sym9-mvt1-405834-p6`, `brahms-sym1-mvt1-317803-p1`,
  `mahler-sym5-mvt1-local-p2/p3/p4/p5`.
- **7 excluded, no stored transcription** for the `restamp-composed` arm in
  `benchmarks/omr-scan-e2e-2026-09/fixtures/`: `beethoven-sym5-mvt1-984073-p3`,
  `beethoven-sym5-mvt1-984073-p4`, `beethoven-sym5-mvt1-575951-p3`,
  `beethoven-sym5-mvt1-575951-p4`, `dvorak-sym9-mvt1-405834-p7`,
  `brahms-sym1-mvt1-317803-p3`, `brahms-sym1-mvt1-317803-p4`. **Two of
  these — `984073-p3` and `984073-p4` — carry hand-read `systems_as_printed`
  maps and cannot be scored for lack of a transcription artefact.**
  ⚠️ `984073-p4` is a DIFFERENT hazard than the one this probe measures: its
  two systems both print 11 staves but with **different lineups**
  (`n_staves_note`: "system 1 suppresses Timpani and SPLITS the bottom
  staff … system 2 keeps Timpani … condenses the bottom staff again"), so
  the ordinal join's equal-count check would **succeed** there and still be
  wrong — a case this probe's population (which only compares where ordinal
  either succeeds correctly or refuses) does not reach at all, because no
  transcription of that page is on disk. Flagged, not measured.
- 0 excluded for missing hand-read truth after resolving the 2 `"staves":
  "same-as:<row_id>"` references (`575951-p1`, `575951-p2` both borrow
  `984073-p1`/`p2`'s truth).
- **4 rows tested** → **3 distinct documents** after fingerprinting each
  tested transcription by its (system, slot_index, instrument) content:
  `beethoven-sym5-mvt1-984073-p2` and `beethoven-sym5-mvt1-575951-p2`
  hash **identical** (two different IMSLP scans of the *same plate* —
  `575951-p2`'s own row label already says "same engraving as 984073 p.2",
  and the transcriptions confirm it byte-for-byte on every partition-
  relevant field) and are counted as **one** document, not two.

That leaves exactly **3 distinct documents**: `beethoven-sym5-mvt1-984073-p2`
(=`575951-p2`), `bach-brandenburg3-mvt1-468678-p1`, and
`brahms-sym1-mvt1-317803-p2`.

## The result, per document

Produced by `probe_partition_truth.py`, which imports `_stitch_slots` and
`_stitch_slots_by_slot` **from `tools.omr.export` directly** — it does not
restate their logic, unlike the earlier `probe_correspondence.py` in this
same benchmark directory (whose `_default_parts`/`_slot_parts` are explicit
restatements and were not trusted here for that reason).

| document | system sizes | ordinal | slot | ordinal = truth | slot = truth | ordinal per-staff | slot per-staff |
|---|---|---|---|---|---|--:|--:|
| `beethoven-sym5-mvt1-984073-p2` (=`575951-p2`) | [11, 11] | succeeded | succeeded | **True** | **True** | 1.000 (11/11) | 1.000 (11/11) |
| `bach-brandenburg3-mvt1-468678-p1` | [12, 12] | succeeded | succeeded | **True** | **True** | 1.000 (12/12) | 1.000 (12/12) |
| `brahms-sym1-mvt1-317803-p2` | [14, 13] | **REFUSED** | succeeded | n/a | **False** | n/a | **0.889 (24/27)** |

### Where the ordinal join succeeds (2 of 3 documents)

Both agree with hand truth exactly, and with each other — this reproduces
the prior falsifier's finding on a re-verified, dedupe-aware population,
using the real exporter functions rather than a restatement. Truth here is
the weaker "uniform lineup positional" derivation (hand truth states no
staff is suppressed and no reordering occurs across the systems on these two
pages, which the printed `n_staves_note` text for both rows confirms; it is
not independently name-aligned per system the way the refusing row is,
because neither row carries a `systems_as_printed` map — only a flat
`staves` list is on file for them).

### Where the ordinal join refuses (1 of 3 documents) — THE WHOLE QUESTION

`brahms-sym1-mvt1-317803-p2`: system 1 prints 14 staves, system 2 prints 13
(the "2 Trompeten in C" staff is genuinely tacet through the window — hand
truth's `systems_as_printed.system_2` omits it, name-aligned as an exact
order-preserving subsequence of `system_1`'s 14 names, confirmed
programmatically rather than assumed).

The slot join **succeeds** (does not abstain) but gets **3 of 27 staves
wrong**:

```
MISMATCH staff [0, 6]: true groupmates=[[0, 6], [1, 6]]   slot groupmates=[[0, 6]]
MISMATCH staff [0, 7]: true groupmates=[[0, 7]]            slot groupmates=[[0, 7], [1, 6]]
MISMATCH staff [1, 6]: true groupmates=[[0, 6], [1, 6]]   slot groupmates=[[0, 7], [1, 6]]
```

In print terms: system 0's 7th staff (0-indexed position 6 — "4 Hörner in
Es 3./4.") should continue as the SAME part on system 1's 7th staff
(position 6 there too — the horn section does not go tacet). Instead the
slot join assigns system-0-position-6 to `slot_index=6` **alone** (a
singleton — WRONG, it should have a partner) and merges system-1-position-6
into `slot_index=7` alongside system 0's TRULY tacet "2 Trompeten in C"
staff (position 7) — grafting the horn continuation's music onto the
trumpet part, and orphaning the horn's own first-system music into an
unpartnered fragment. The genuinely-tacet Trompeten staff (position 7,
system 0 only) is exactly the one staff whose ABSENCE from system 2 the
slot join is supposed to express correctly — and it is not the one that
went missing; the horn did.

**Root cause, cross-checked by a second, independently-keyed field on the
same staves** (not derived from this probe's own alignment logic):

```
system 0 staff_index 6  slot 6  instrument Trumpet  instrument_source score_order
system 0 staff_index 7  slot 7  instrument Trumpet  instrument_source score_order
system 1 staff_index 19 slot 5  instrument Horn     instrument_source score_order
system 1 staff_index 20 slot 7  instrument Trumpet  instrument_source score_order
```

Every one of these four staves has `instrument_source: "score_order"` —
none of them was named from a printed margin label. The contextual pass's
own instrument guess is already wrong on system 0 (it calls BOTH
of system 0's Horn-family staves "Trumpet," when only one of the 14
staves on that system is truly a trumpet staff), and `slots.assign_slots`
inherits that error into the `slot_index` it hands the exporter. This is
the same failure shape the project has already named and priced elsewhere
in this codebase (`CLAUDE.md`'s "ambiguous alias" family, and the ordinal-
join-refuses population itself being where score-order fitting has the
least real evidence to work with — a suppressed staff is exactly the case
where the canonical layout DP has the fewest anchors). It is not a new
mechanism; it is the same one, showing up in the specific place the
recommendation proposes to newly rely on.

## What this does and does not decide

- It **falsifies the specific factual claim** that `_stitch_slots_by_slot`
  "expresses exactly the tacet case" on Brahms 1 p.2 — the only row cited
  by name in the recommendation doc as evidence the slot join handles the
  refusing case correctly. That claim does not hold on inspection of the
  actual partition (as opposed to the part *count*, which the doc's own
  cited probe — `probe_correspondence.py` — only ever checked; it counts
  `len(slots)`, never which staves ended up in which slot, so a 14-slot
  output that is wrong in 3 places and a 14-slot output that is exactly
  right are indistinguishable to it).
- It does **not** establish a failure rate for the refusing population in
  general — n=1 distinct document is what the stored artefacts allow, and
  a single counterexample does not average. It does establish that "zero
  disagreement" is no longer a true description of the evidence: at least
  one refusing row disagrees, and it is not a marginal one (11% of its
  staves, in a case — instrument continuity across a tacet break — that is
  exactly the scenario the whole change is supposed to repair correctly).
- The un-transcribed `984073-p4` row is flagged, not measured: it is a
  *third* failure shape (ordinal succeeds on equal counts but the lineups
  differ), outside what either this probe or the cited recommendation
  evidence currently covers, and it should be transcribed and scored before
  any claim is made about the equal-count population either.

## Reproduce

```bash
cd /Users/seanjohnson/Desktop/ReEngrave   # or a worktree; fixtures resolve via REENGRAVE_MAIN
python3 benchmarks/omr-partition-truth-2026-09/probe_partition_truth.py \
    --json benchmarks/omr-partition-truth-2026-09/results.json
```

Guards proven, not asserted: `--works /path/to/nonexistent.json` exits 2
(`FATAL: no works.json at …`); `--works` pointed at a file whose `"rows"` is
`[]` exits 2 (`FATAL: works.json carries zero rows`). Both checked live
before this file was written.
