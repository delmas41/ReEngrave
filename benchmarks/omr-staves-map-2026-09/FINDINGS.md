# A confirmation UI for the five scan rows that carry no `staves` map

2026-09-06. Tooling, not a measurement. Nothing here changes a default, and
nothing here writes `works.json`.

```bash
python3 benchmarks/omr-staves-map-2026-09/build_cache.py     # once, ~2 min
python3 benchmarks/omr-staves-map-2026-09/server.py          # -> :5075
python3 benchmarks/omr-staves-map-2026-09/merge_additions.py           # dry
python3 benchmarks/omr-staves-map-2026-09/merge_additions.py --write
```

---

## 1. All FIVE rows already carry the reading. What they lack is the CHOICE.

⚠️ **Two of the five look unread and are not.** `beethoven-sym5-mvt1-575951-p3`
and `-p4` carry `systems_as_printed: "same-as:beethoven-sym5-mvt1-984073-p3"` /
`"…-p4"` — the works.json idiom for two scans of one plate, resolved by seven
consumers (`scan_eval.py:122`, `condensation_arm.py:94`,
`probe_map_coverage_cost.py:38`, `normalised_arm.py:74`, and three probes).
Read as a raw string rather than followed, they read as absent. **109 of 109
staves are hand-read, not 68.**

⚠️ **And the 575951 page offset does not apply to these rows.** CLAUDE.md warns
that 575951 carries an extra leading page, so its printed p.2/p.3/p.4 land on
`pdf_page_index` 1/2/3 where 984073's printed p.1/p.2/p.3 already sit — a
`--work-id` narrowing hazard for `mxl_verdicts`. The works.json rows are keyed
by `row_id` with an explicit `pdf_page_index` and the offset is already
absorbed: `575951-p3` is **printed page 3** at pdf index 2, `984073-p3` is
printed page 3 at pdf index 3, and **both carry window 49–82**. So `575951-p3`
pairs with `984073-p3`, not with `984073-p2`.

The commission was written as though these five pages were unread. They are
not. Every one of them carries a `systems_as_printed` block that was hand-read
off the print and verified — Brahms p.2's entry records Sean sweeping system 2's
whole margin column and confirming the drafter's Trumpet misread; Beethoven
p.3's records the suppressed staves being checked against the reference's own
activity grid in both directions.

What they lack is a PAGE-LEVEL map, and the reason is structural rather than
clerical:

| | systems | printed staves | why no `staves` map |
|---|---|--:|---|
| beethoven-984073-p3 | 11 + 8 | 19 | system 2 suppresses Oboi/Trombe/Timpani |
| beethoven-984073-p4 | 11 + 11 | 22 | **same count, different lineups** |
| beethoven-575951-p3 | 11 + 8 | 19 | same plate, `same-as` the 984073 twin |
| beethoven-575951-p4 | 11 + 11 | 22 | same plate, `same-as` the 984073 twin |
| brahms-317803-p2 | 14 + 13 | 27 | system 2 suppresses the Trompeten staff |

`systems_as_printed` is per SYSTEM. A `staves` map has no system dimension —
`page_normalise` emits one output PART per entry — so collapsing several
disagreeing lineups to one page lineup is a judgement about what the page's
part structure IS. That is what the human is for, and it is why the tool is a
confirmation tool: it proposes the collapse and shows the disagreement.

## 2. ⚠️ 109 STAVES IS 58 MAP ENTRIES, AND BOTH NUMBERS ARE RIGHT

The commission asks for 109 staves; the UI offers 58 slots. Both are correct
and they count different things.

**109** is printed staff INSTANCES — `page.n_staves`, which
`probe_map_coverage_cost.py` records under the field name
`staves_a_human_would_read`, summing a page's systems (p.3 is 11 + 8 = 19). It
is reading effort.

**58** is map ENTRIES. A part is continuous across the systems of a page, so
p.3's 19 printed staves are 11 slots. **It could not be otherwise**: 19 entries
against 18 reference parts is arithmetically impossible, and a map naming a
part twice is refused here for the same reason `page_normalise.IncompleteMap`
refuses one naming a part not at all.

⚠️ **The dangerous reading of the same gap was checked and is FALSE.** The worry
worth having is that the page prints 19 and phase 1 finds 11, so a map over
detected staves would be structurally short — the shape the veto-pricing session
found on Beethoven p.86, which prints 17 staves where phase 1 detects 16. It is
not what is happening here. Measured on all five rows, detected equals printed
exactly, system for system:

| row | works.json `n_staves` | detected | per system |
|---|--:|--:|---|
| beethoven-984073-p3 | 19 | **19** | 11, 8 |
| beethoven-984073-p4 | 22 | **22** | 11, 11 |
| beethoven-575951-p3 | 19 | **19** | 11, 8 |
| beethoven-575951-p4 | 22 | **22** | 11, 11 |
| brahms-317803-p2 | 27 | **27** | 14, 13 |
| | **109** | **109** | |

**So the map reaches every printed staff on these five pages, and the UI shows
every one of the 109 instances** — the centre panel stacks one crop per system
that prints the current slot, joined through the hand-read `systems_as_printed`
lineups (by PARTS, never by ordinal — pairing by position is the exact failure
works.json records for Brahms p.2). A slot printed in no other system is
reported as tacet-suppressed, which is information rather than a hole.

## 3. ⚠️ THE 72% IN THE COMMISSION DOES NOT FOLLOW FROM ITS OWN NUMBERS

The brief says these rows "would let us attribute about **72%** of the currently
unexplainable `entire staff` bucket (3,646 of 9,239 edits)". 3,646 / 9,239 is
**0.3946**. Recomputed from `map-coverage-cost.json`, which is the file the
figure comes from:

| | `entire staff` edits |
|---|--:|
| these five rows | 3,646 |
| all ten unmapped rows | 9,239 |
| **share** | **39.5%** |
| pooled, 20 rows | 17,520 |
| share of pooled | 20.8% |

The rest of the unmapped bucket is Mahler (5,307 across four rows, out of scope
— its printed one-line percussion staves break a positional join) and Bach
Brandenburg 3 (286). **39.5% is the honest figure**; 3,646 edits is still the
largest reachable block of that bucket and the exercise is still worth doing.

## 4. ⚠️ IS PROMOTION SOUND? YES — ASKED OF THE CONSUMER, NOT OF THE NOTE

`systems_as_printed._purpose` reads like a judgement that these rows *cannot*
have a flat map: *"system counts 11 vs 8 make export stitching refuse, so
predicted parts stay per-system and a single positional map cannot pair them"*.

**That reasoning is about the PREDICTION side and does not reach
`page_normalise`, which is the consumer the `entire staff` bucket is about.**
`page_normalise` never pairs anything. It consumes the map to MERGE REFERENCE
PARTS into a derived truth whose parts are the page's staves; the prediction is
not an input, and `musicdiff` pairs afterwards, on parts, exactly as before. The
per-system fragmentation of the prediction is a real cost that prices into the
row's OMR-NED either way, and normalising the truth neither helps nor hurts it.

Asked directly (`probe_promotion_is_sound.py`), on the proposals as built:

```
ACCEPT beethoven-sym5-mvt1-984073-p3   18 parts -> 11 staves  exact-dup 0.8262  divisi 0.1738
ACCEPT beethoven-sym5-mvt1-984073-p4   18 parts -> 11 staves  exact-dup 0.6     divisi 0.4
ACCEPT beethoven-sym5-mvt1-575951-p3   18 parts -> 11 staves  exact-dup 0.8262  divisi 0.1738
ACCEPT beethoven-sym5-mvt1-575951-p4   18 parts -> 11 staves  exact-dup 0.6     divisi 0.4
ACCEPT brahms-sym1-mvt1-317803-p2      21 parts -> 14 staves  exact-dup 0.8857  divisi 0.1143
```

5 of 5. **So the blocker was never the reading, and it is not the consumer
either — it is the one judgement in the middle**, which is what this UI is
sized for. ⚠️ A per-system map is NOT the alternative to build: `page_normalise`
emits one truth FILE per row and a file has one part list, so consuming a
per-system map would mean splitting each row's window into per-system windows
and scoring them separately — a different benchmark shape and a far larger era
change than the flat collapse, for a structural cost the flat map already
avoids.

⚠️ **This shows the transform is well-defined, NOT that it improves the number.**
A normalised figure is a new benchmark era (`page_normalise` rule 5) and may not
be differenced against the un-normalised 0.8444 in either direction. Whether
promotion pays is `normalised_arm.py`'s question, and it has not been run.

## 5. What the tool proposes, and what it refuses

**Proposal.** The system whose lineup names the most distinct reference parts,
tie-broken by staff count. On all five rows that proposal already names every
part (0 unassigned), so the human's job really is confirmation.

**Refusals, all server-side, all before a page can be called done:**

- a reference part left unassigned — `page_normalise` raises `IncompleteMap`,
  because a normalised truth missing a part scores BETTER for the wrong reason;
- a part named by TWO staves — the mirror fault, which nothing downstream
  checks, so it is checked here;
- a part index out of range, or a staff entry with no parts;
- any staff still undecided;
- ⚠️ **an unacknowledged lineup difference.** Where the systems print different
  lineups and one page map cannot express both, `d` is refused until the choice
  is acknowledged with `k`. Beethoven p.4 is the case: system 1 suppresses
  Timpani and SPLITS Violoncello from Basso, system 2 keeps Timpani and
  condenses them into `Bassi`. A merely-suppressed system (p.3's 8 against 11)
  is a subset of the chosen lineup and needs no acknowledgement.

**One key adopts the twin.** The two 575951 rows are the same Litolff plate as
the 984073 rows — `same-as:` in works.json, and the p.3 window's `verified_by`
records a barline fingerprint with **zero unmatched boundaries on either side**
and max normalised disagreement 0.0013. So `y` takes the finished twin's map
wholesale, recording `adopted_from`, and refuses while the twin is unfinished.
⚠️ It is adopted, not assumed: this row's crops are rendered from **its own
PDF** at 600 dpi and stay on screen, so the adoption is checked against this
scan's ink. That takes the human's real work from 58 slots to **36** — p.3 (11),
p.4 (11, plus one acknowledgement) and Brahms p.2 (14), with the two twins
adopted.

**The merge asks the consumer before writing.** `merge_additions.py` runs
`page_normalise.normalise` on the row's own trimmed truth and refuses on any
exception. A map that passes every shape check and then raises in the consumer
is precisely the "mismatched shape is worse than no map" failure, so the
consumer is asked first rather than afterwards. It also refuses to overwrite a
row that already has a `staves` map, backs `works.json` up before touching it,
and re-reads the result to assert no other row moved.

## 6. Where every fact comes from

| fact | source | why it must be that source |
|---|---|---|
| printed staff bands | `<row>.reconciliation.omr.json` | the canonical 20-row baseline's own artefact (`results-reconciliation.json`, pooled 0.8444). Taking the staff count from the encoding would be circular — the question IS whether printed staves and encoded parts correspond |
| reference part indices | `<row>.truth.musicxml`, **music21** | `staves[i].parts` indexes `page_normalise`'s `out.parts`, which is music21's list. ⚠️ NOT the `<score-part>` list: a part declaring `<staves>2</staves>` parses to two `PartStaff`s, and that off-by-one once made an identity map drop a part and "improve" Dvořák 9 by 42 edits. Both counts are read and **cross-checked**; a disagreement blocks the row |
| part names / abbreviations | `<score-part>`, ElementTree | a real XML parser, never a regex |
| the page image | `tools.omr.preprocessing.render_page` | four of the five plates are deskewed 0.25°, and the bands are recorded in the DESKEWED frame. A plain fitz render would put every box off its staff |
| the proposal | the row's own `systems_as_printed` | hand-read and print-verified; see each row's `verified_by` |

The build refuses a row whose render does not match the size the run recorded,
whose artefact is a different page, or whose two part counts disagree.

## 7. Paths

| | |
|---|---|
| reads | `<MAIN>/benchmarks/omr-scan-e2e-2026-09/works.json` |
| reads | `<MAIN>/library/editions/…` (the PDFs) |
| reads | `<MAIN>/.claude/worktrees/reconciliation/…/fixtures` (canonical run + trimmed truths) |
| cache | `~/.cache/reengrave-staves-map/` (9 MB of crops; rebuildable, disposable) |
| **writes** | `<MAIN>/benchmarks/omr-scan-e2e-2026-09/works.staves-additions.json` |

Every durable path is in the MAIN checkout, so the work outlives any worktree.
The additions file is written atomically (tmp + rename) on every keystroke, and
an unreadable one is copied aside rather than overwritten.

## 8. What was verified, and what was not

**Verified by driving the running server:** the proposal renders for all five
rows; staff bands land on the printed staves (checked by eye on Beethoven p.3
and Brahms p.2, where all fourteen margin labels are legible and in order); four
rapid `t` presses confirm exactly four staves (an earlier build could lose one
to a stale reply, fixed with a sequence guard and optimistic advance); `d` is
refused with 7 staves undecided, and refused again on p.4 with all 11 decided
and 18/18 parts named but the lineup difference unacknowledged; `k` then `d`
completes; `y` on a 575951 row is refused while its twin is unfinished and then
adopts the finished map, with that row's OWN higher-resolution crops on screen;
the additions file carries the map plus its provenance; the merge
proves the map through `page_normalise` (18 source parts → 11 output parts),
writes to the right place in key order, changes no other row, and refuses a
second merge of the same row.

**Not verified:** nothing has been merged into the real `works.json` — the
`--write` path was exercised against a scratch copy only. No pooled figure was
re-measured; ⚠️ and when one is, note that a normalised figure is a **new
benchmark era** and may not be differenced against 0.8444 in either direction
(`page_normalise` rule 5). My own test keystrokes were deleted so Sean starts
from an empty slate.
