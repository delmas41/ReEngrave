# The re-gather with `OMR_DOCUMENT_IDENTITY=1` — the store conditions on a plate

The one unfinished measurement of
[docs/handoff-2026-09-17-regather-with-identity.md](../../../docs/handoff-2026-09-17-regather-with-identity.md).
The 2026-09-17 re-gather proved `Q.INK`'s reach and left `publisher` unset on
all 15,579 store entries, because the identity rung is default OFF and that run
used defaults. **Both of the handoff's acceptance criteria pass**, and the
result is a wiring confirmation, as it predicted — nothing was discovered about
the rung itself.

## 1. THE RUN

```bash
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
O=benchmarks/omr-positional-store-2026-09/out
# ⚠️ the record goes to the SHARED dir, not to $O: `out/` now ignores
# `*.record.json`, because a 140 MB record there is a duplicate (§6).
REC=library/_shared-records/beethoven5-p1-p4-ink-identity.record.json

env OMR_INK=1 OMR_DOCUMENT_IDENTITY=1 OMR_DIRECTION_TEXT_SCAN_GATE=1 \
  python3 -u -m tools.omr.staged "$PDF" --pages 1-4 --weights "$W" \
  --out "$REC" --progress

python3 -m tools.omr.positional_store "$REC" --out $O/store.jsonl
```

| | |
|---|---|
| record | `library/_shared-records/beethoven5-p1-p4-ink-identity.record.json`, 140 MB, **md5 `ea80ae5908288c76baaa502054a37d43`** |
| provenance | commit `e38dbc25`, **`dirty: false`** |
| wall clock | ~15 min (GATHER + ADJUDICATE + EVALUATE), exit 0 |
| shared copy | `library/_shared-records/beethoven5-p1-p4-ink-identity.record.json`, md5 **re-verified after the copy** |

**The two criteria, both met:**

```
  beet5-p1-p4-ink-identity.record.json     litolff       15579 entries  (identity from record)
  per publisher : {'litolff': 15579}
```

against the OFF arm, which this session re-derived from code rather than
relaying — `identity_of_record` on the 2026-09-17 record returns
`{'from': 'none'}` → publisher `unknown`.

⚠️ **ONE CORRECTION TO THE CRITERION'S FORM.** The handoff asks that
`per publisher` read `Henry Litolff's Verlag, Braunschweig, 1870, plate 2769`.
It reads **`litolff`**, and that is `publisher_label`'s documented intent — the
full imprint is *"right to keep and wrong to key on: two plates of one house
must land in one bucket set."* The imprint is kept, verbatim, as the
`document_identity` row's own value and `detail.publisher`. So the criterion
is met in substance and the form it names belongs to the record, not the store.

## 2. ⚠️ THE HANDOFF'S COMMAND OMITS `OMR_INK=1`, AND IT IS LOAD-BEARING

Caught before it cost the run. The store reads TWO quantities — `glyph_box`
(named) and `ink` (unnamed) — and the prior record is **7,093 `ink` + 8,486
`glyph_box` = 15,579**, exactly the entry count the handoff quotes. Run as
written, the arm would have dropped the whole unnamed-ink half of the store
(7,093 of 15,579 entries) **and changed two variables instead of one**, which
is the only thing this measurement was for.

The prior arm's flags are not recoverable from its provenance (§5); they were
recovered from the OUTPUT — `OMR_INK` from the 7,093 ink rows, the scan gate
from `direction_word` abstaining `out_of_scope` ×1187. Both happen to leave a
trace. **A flag that changes a VALUE rather than a row's existence would leave
none.**

## 3. THE ARMS ARE IDENTICAL ON EVERY INK COUNTER — and the off-by-one is two definitions

| | OLD `374d1905` | NEW `e38dbc25` | |
|---|--:|--:|---|
| `ink` rows | 7093 | 7093 | same |
| no `ink_explained_by` | 3018 | 3018 | same |
| `ink_explained_by` > 1 | 1607 | 1607 | same |
| `ink_detector_coverage` falsy | 3019 | 3019 | same |

So the gather **reproduces across the two commits** and the flag added exactly
one row (observations 40,877 → 40,878). Adjudication is identical too
(`duration` 2636, `glyph_owner` 1368, `notehead_is_a_whole_rest` 2347, …),
which is what producer-only is supposed to mean, measured rather than trusted.

⚠️ **The handoff says "3,019 UNNAMED — no detection explains them"; the store
reports 3,018.** Neither is wrong — they are two fields that disagree on
**exactly one row**, found by the number being off by one:

    glyph/2/1/1/2/200001
      ink_explained_by: ['ledgerLine']      ← a class IS named
      ink_detector_coverage: 0.0            ← no detection covers a measurable fraction
      ink_area_px 42253, ink_n_components 15, ink_share_of_cell 0.2969

A 537×1200 canonical blob holding 15 components and 29.7% of its cell's ink,
which one ledger line touches. That is the MERGE the ink work already records
(*"Litolff MERGES … the median Litolff cell's largest component holds 46% of
its ink"*), and it is why both fields exist. **The store buckets by NAME, so
`explained_by` (3,018) is the figure it must use, and does.** The precise
statement: **3,019 rows have no detection covering them; 3,018 have no class
named at all.**

## 4. TWO PUBLISHERS — the conditioning variable as a real partition

One publisher makes conditioning degenerate (`eds 1` in every bucket), so the
Breitkopf shared record was accumulated beside it. **1.48 s, 113 MB peak RSS
over 563 MB of records** — it streams.

```
  beet5-p1-p4-ink-identity.record.json     litolff       15579 entries  (identity from record)
  brahms1-breitkopf-p0-p3.record.json      breitkopf     12932 entries  (identity from legacy-table)
  per publisher : {'litolff': 15579, 'breitkopf': 12932}
```

⚠️ **The two identity PROVENANCES are visibly distinguished**, which is the
design working: `from record` is the new rung, `from legacy-table` is
`LEGACY_RECORD_EDITIONS`, the hand-made patch that exists precisely because
both shared records predate the rung. A consumer can tell a derived fact from
an asserted one.

⚠️⚠️ **THE UNNAMED-INK HALF OF THE STORE IS STILL n = 1 PUBLISHER, and adding
Breitkopf did not change it.** `no membership 3018 / several 1607` are
UNCHANGED across the two stores — verified, not inferred: the Breitkopf shared
record holds **12,932 `glyph_box` and ZERO `ink`** (and zero
`document_identity`). So every Breitkopf entry has a membership by
construction, and **conditioning UNNAMED ink on the plate is untested** — which
is exactly where the ink findings expect trouble, since that document's
composition inverts (56% specks against Litolff's 1%, 5.6 components per cell
against 30).

**RANKED NEXT WORK, one command from a clean tree** (~40 min, no discovery):

```bash
env OMR_INK=1 OMR_DOCUMENT_IDENTITY=1 OMR_DIRECTION_TEXT_SCAN_GATE=1 \
  python3 -u -m tools.omr.staged \
  library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
  --pages 0-3 --weights "$W" \
  --out library/_shared-records/brahms1-breitkopf-p0-p3-ink-identity.record.json --progress
```

It would also retire that record's line in `LEGACY_RECORD_EDITIONS`.

## 5. ⚠️ A RECORD STAMPS ITS TREE AND NOT ITS CONFIGURATION — latent, reach measured

`_provenance()` is `{commit, dirty}` and nothing else. Its own argument is that
without it *"comparing two records is an unprovenanced A/B … equally consistent
with having compared two runs of the SAME tree"*, under the rule **anything
that cannot uniquely name a tree must never compare equal to anything,
including itself.** On a flag-driven pipeline **the commit does not uniquely
name the configuration**: two records from one clean commit under different
flags are byte-different in content and identically stamped. §2 is that cost,
paid.

It composes with a second gap in the consumer.
`regather_control.check_provenance` **REFUSES** a same-clean-tree pair:

> both records were built from the SAME clean tree (X): this comparison cannot
> show a code change and 'MOVED: nothing' would mean nothing

That is true of a code change and is the wrong inference for a **flag arm**,
where same-clean-tree is the REQUIRED condition rather than a defect. So the
one control that checks provenance rejects the ideal setup for most A/Bs this
project runs.

⚠️ **REACH: ZERO. No flag arm in the repo calls it** — `grep` finds its only
caller is its own test file (`test_staged_provenance.py`). Nothing has been
misled; it fails in the SAFE direction, by refusing. This is a **LATENT** trap
in `wiring.py`'s own sense — *armed for whoever closes it*, which is precisely
what a careful next session wiring the control into a flag arm would do.

⚠️ **DELIBERATELY NOT FIXED.** Stamping flags is additive to every record this
repo writes, which is the *perturbs upstream by existing* call CLAUDE.md
reserves for Sean. Recorded with its reach instead.

## 6. A build product slipped past the gitignore written to exclude it

`out/.gitignore` says the base store is *"a BUILD PRODUCT, not an artefact …
it is 13 MB"* and ignores `store.jsonl` / `store.jsonl.gz`. **The handoff's
command writes `--out store.json`**, which that list does not match on the
extension — a 9 MB build product one `git add` from the tree. The CLI's own
help says *"write the base store (JSONL) here"*, and the file IS JSONL (1 meta
line + 15,579 entries), so `.json` was simply the wrong spelling. Written as
`store.jsonl`, and the `.json` spelling added to the ignore list so the
handoff's form cannot land it either.

## 7. CONTROLS, and what is NOT established

Baseline taken BEFORE anything, on `e38dbc25` — *"checks fail after a change"*
and *"checks were already failing"* look identical in a terminal. **All eight
derived checks exit 0**: `capture --check`, `wiring --check` (56 problems, 0
unaccounted, 0 stale), `inventory --check`, `gather_coverage`,
`health --check`, `no_producer --check`, `export_coverage --all`,
`accuracy_record --check`.

⚠️⚠️ **AND THE RE-RUN OF THOSE CHECKS CAME BACK ALL-RED FROM THE SHELL, WHICH
IS THIS FILE'S OWN RECORDED HAZARD.** Looping `for m in "staged.capture
--check" …; do python3 -m tools.omr.$m; done` reports **exit 1 on all eight**,
because **zsh does not word-split an unquoted `$m`** — it ran
`-m "tools.omr.staged.capture --check"`, one module name containing a space.
CLAUDE.md already records this as *"a clean, believable zero that was the
shell (zsh does not word-split `env $3`)"*; here it is a clean, believable
**all-red**, which is worse, because eight simultaneous failures immediately
after a merge read as a broken tree. What named it was that `tools/` was
provably untouched (`git diff HEAD -- tools/` empty). Re-run as eight explicit
commands: **0 on all eight**, matching the baseline. Use `${=m}` or do not
loop.

⚠️ **NOT ESTABLISHED.** That the identity facts are RIGHT beyond this one plate
(they are the catalog's, `source_kind: "catalog"`, and were checked against
`edition_for_pdf` and nothing else); that any consumer reads
`Q.DOCUMENT_IDENTITY` — **nothing does, by design**; that conditioning HELPS
anything, which is `A-INK-4`'s point and cannot be asked yet because the
partners do not exist; anything about unnamed ink on a second plate (§4); and
anything about an ENGRAVED page. n = 1 document for the ink half, 2 publishers
for the named half, 4 pages.
