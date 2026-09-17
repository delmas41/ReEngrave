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

## 2. ⚠️⚠️ I CALLED THE HANDOFF'S COMMAND DEFECTIVE AND IT IS NOT — `OMR_INK` IS DEFAULT ON, AND EIGHT LEDGERS SAID OTHERWISE

**The correction is the finding, and it cost a killed run.** The first version
of this section claimed the handoff's command omits a load-bearing
`OMR_INK=1`. That is **FALSE**. `gather._ink_enabled()` reads
`environ.get("OMR_INK", "1") not in ("0", "", "false", "no", "off")` — **default
ON since 2026-09-17 (Sean's call), a DENY-list** — so the handoff's command as
written gathers ink, and the explicit `OMR_INK=1` in §1 is a **no-op**.

⚠️ **The arm is unharmed and that is checkable rather than hopeful:** a no-op
cannot change a variable, and the ink counters come back **identical to the
prior record in all four** (§3). Had I actually altered the ink configuration
they could not have. So the A/B is still one-variable; what was wasted was a
kill and a relaunch, ~15 minutes, on a run that was already correct.

⚠️⚠️ **WHAT MISLED ME IS THE LEDGER, NOT THE CODE — AND IT IS THE FIRST THING
AN AGENT READS.** The flag flipped to default-ON and **EIGHT places still stated
it OFF**, four of them in the governing file — the eighth and seventh found by
`grep`ing for the claim after fixing the first six:

| where | says |
|---|---|
| `CLAUDE.md:409` | "`OMR_INK`, default OFF, PRODUCER ONLY" |
| `CLAUDE.md:753` (knobs table) | `` `OMR_INK` │ `0` (off) `` — and argues *"the standing argument for the flag being off until a consumer exists"* |
| `CLAUDE.md:6102` | "behind `OMR_INK`, **default OFF**" |
| `CLAUDE.md:7185` (env table) | "`0` off (default)" |
| `tools/omr/staged/wiring.py:361` | "flag `OMR_INK`, default OFF" |
| `benchmarks/omr-ink-gather-2026-09/FINDINGS.md:4` | "**default OFF**, allow-list" — wrong about BOTH halves |
| `tools/omr/staged/ASSUMPTIONS.md:897` | "`OMR_INK`, default OFF" |
| `tools/omr/staged/ASSUMPTIONS.md:933` | "PRODUCER ONLY, `OMR_INK`, default OFF" |

⚠️ **The findings file is wrong about BOTH halves** — the default *and* the
list kind. The predicate is a deny-list, which is exactly what CLAUDE.md's own
*"A flag's OFF test must follow its DEFAULT"* rule REQUIRES of a default-ON
flag. **So the code is correct and every description of it is stale**: this is
`fixed-then-kept-open-in-prose` inverted — **flipped-then-kept-off-in-prose** —
and unlike a stale claim about the past, a wrong DEFAULT in a knobs table is
read as a fact about the run you are about to make.

⚠️ **The cheap check is that the claim is mechanically falsifiable, and the
instrument already existed.** `test_flag_default_direction.default_on_flags()`
derives every flag, its default and its list kind from the AST, and evaluates
the predicate on its own default rather than guessing — it reports
`ON OMR_INK`. Nothing compared that roster to the table. **Closed in this
commit** (§8): the table is now derived-checked against the predicates.

### What IS true about the prior arm, and how its flags were recovered

The prior record is **7,093 `ink` + 8,486 `glyph_box` = 15,579**, exactly the
entry count the handoff quotes — so the store does read two quantities and the
ink half is real. Its flags are **not recoverable from its provenance** (§5);
they were recovered from the OUTPUT — ink from the 7,093 rows, the scan gate
from `direction_word` abstaining `out_of_scope` ×1187. Both happen to leave a
trace. **A flag that changes a VALUE rather than a row's existence would leave
none**, which is §5's point and is why that gap is worth more than this
section's original mistake.

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

**FULL SUITE: 4,297 passed, 11 skipped, 12m13s** — and the exit code was
captured with an explicit `echo $?` rather than through a pipe, because an
earlier attempt in this same session reported success for a run that never
started (§9).

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

## 8. THE DURABLE FIX — the flag tables are now derived-checked against the predicates

`tools/omr/tests/test_flag_docs_match_predicates.py`. Nothing compared
CLAUDE.md's two flag tables to the code, so §2's eight stale statements were
invisible, and a ninth would be too.

⚠️ **It IMPORTS the roster rather than re-deriving it.**
`test_flag_default_direction.default_on_flags()` already walks the AST for
every `environ.get(<FLAG>, <default>)`, resolves a flag named through a module
constant, and settles the direction by **evaluating the predicate on its own
default** — two copies of a derived list is exactly the drift this check is
about. It reports **29 read sites over 26 distinct flags, 15 ON / 14 OFF**.

**TWO TIERS, because one of them has to be able to pass.**

| tier | meaning | count |
|---|---|--:|
| **CONTRADICTION** — a table row stating the wrong default | hard failure | **1 → 0** (`OMR_INK`, both rows) |
| absent from both tables | recorded in `UNDOCUMENTED`, with a reason | 10 → **9** |

⚠️ **A check that can never pass cannot be a gate**, which CLAUDE.md already
records against `no_producer --check` (*"exits 1 while reporting its findings
as `RECORDED`"*). Ten pre-existing undocumented flags would have made this
permanently red, so they are ACCOUNTED rather than failed — and **documenting
one must remove it from the list**, the `export_coverage` stale-entry rule, so
the list describes the tables and not their history. `OMR_DOCUMENT_IDENTITY`
was documented in this commit and duly left it.

⚠️ **Three ways it was kept from passing vacuously**, since a check of prose
against code is the kind that reads green while measuring nothing:
1. a **POSITIVE CONTROL** injecting a row that states the opposite of a real
   predicate, which must be caught;
2. a guard that the imported roster is not tiny or empty — **a derivation over
   an empty roster passes everything**;
3. the **stale-entry test run RED on purpose**: putting
   `OMR_DOCUMENT_IDENTITY` back into `UNDOCUMENTED` fails with
   `documented now; remove from UNDOCUMENTED: ['OMR_DOCUMENT_IDENTITY']`, and
   the restore was verified.

⚠️ `states_on` **ABSTAINS rather than guessing.** The default column is
written at least six ways (`` `1` (on) ``, `` **`1` ON since 2026-09-08** ``,
`` `move` (on) ``, `_(unset)_`). It reads the first backticked token — which
IS the default value — and the words `on`/`off`, and returns None where they
CONTRADICT or neither appears. ⚠️ My own first unit expectation for it was
wrong (I asserted an abstention for a cell the rule scores by its token, which
is the stronger signal); the rule was kept and the expectation corrected.

⚠️ **What it does NOT check**: the prose BODIES, only the default COLUMN — a
body says many things and is not a claim about this run's default (the
`OMR_INK` row's body arguing *"the standing argument for the flag being off"*
is now stamped by hand, not by this check); that a documented flag's
DESCRIPTION is true; the nine undocumented flags, two of which
(`OMR_MOVEMENT_REFERENCE`, `OMR_LABEL_MERGE_QUALITY`, plus `OMR_ROSTER`) are
**default-ON and described in no table**, which is the same hazard as
`OMR_INK`'s waiting to be paid.

## 9. ⚠️ TWO RECORDED SHELL HAZARDS, BOTH HIT IN THIS SESSION, BOTH CAUGHT BY READING OUTPUT

Worth logging together, because they are the same lesson in two costumes and
CLAUDE.md already names both.

1. **zsh does not word-split an unquoted `$m`.** Re-running the eight derived
   checks as `for m in "staged.capture --check" …; do python3 -m tools.omr.$m`
   reported **exit 1 on all eight** — it ran `-m "tools.omr.staged.capture
   --check"`, one module name containing a space. The recorded form is *"a
   clean, believable zero that was the shell"*; this is a clean, believable
   **all-red**, which is worse, since eight simultaneous failures right after a
   merge read as a broken tree. Named by `git diff HEAD -- tools/` being empty.
2. **`| tail` swallows the exit code.** `pytest … --timeout=1800 | tail -6`
   reported **`exited with code 0`** and the suite **never ran at all** —
   `pytest-timeout` is not installed, pytest errored on the unrecognised
   argument, and the pipeline's status was `tail`'s. CLAUDE.md records exactly
   this (*"a `| tail` swallowed a real failure's exit code … **Read the
   OUTPUT, not the STATUS**"*). Re-run writing to a file and echoing
   `$?` directly.

⚠️ The generalisation both share, and the one worth carrying: **in this repo a
shell wrapper fails by producing a BELIEVABLE status, never an implausible
one.** Neither an all-green nor an all-red is self-evidently wrong; what
settles it is a fact from outside the wrapper — an empty diff, or the body of
the log.

## 10. ⚠️⚠️ A NAMED CLASS'S GEOMETRY IN THE STORE IS A MIXTURE — found by asking §4's own query

§4 says `per_publisher` is a real partition. It is, and **the first
conditioning query anyone runs is nonetheless misleading.** Asking the
two-publisher store for staff position 0 gives Litolff a `mean_h` of **3.646**
for `noteheadBlackOnLine` against Breitkopf's **1.199** — and a notehead is
one staff space tall, so the larger number is not a fact about a plate.

**The mechanism, isolated on `source_quantity`** (`probe/source_quantity_mixing.py`,
output in `out/source-quantity-mixing.txt`):

| name | publisher | source | n | median | p95 |
|---|---|---|--:|--:|--:|
| `noteheadBlackOnLine` | breitkopf | `glyph_box` | 1425 | **1.200** | 1.290 |
| `noteheadBlackOnLine` | litolff | `glyph_box` | 978 | **1.340** | 1.530 |
| `noteheadBlackOnLine` | litolff | **`ink`** | 799 | **5.290** | **12.000** |
| `ledgerLine` | breitkopf | `glyph_box` | 1057 | **0.288** | 0.384 |
| `ledgerLine` | litolff | `glyph_box` | 1878 | **0.280** | 0.370 |
| `ledgerLine` | litolff | **`ink`** | 1178 | **7.050** | **12.000** |

⚠️⚠️ **`Q.INK`'s `ink_explained_by` becomes a `membership` exactly as a
detection's own class does, so a MERGED BLOB lands in the NAMED class's height
distribution.** A blob five to seven staff spaces tall, explained by
`noteheadBlackOnLine`, sits beside real 1.3-space noteheads; every one of those
`ink` rows has p95 **exactly 12.000**, which is the measure cell's own height
(4 staff spaces plus 4 of padding either side). Pooled, a named class's
geometry is a mixture of the glyph and of whatever ink its class happened to
overlap.

✅ **SPLIT ON `source_quantity`, THE TWO PUBLISHERS AGREE** — `ledgerLine`
0.288 against 0.280, **eight thousandths of a staff space** — which is both
the refutation of the alarming number and the positive control that these two
records are geometrically comparable at all.

⚠️ **What it is NOT**: not a bug in `height_spaces`, and not a schema gap —
`source_quantity` is on every entry. It is a **QUERY DISCIPLINE**, and
`positional_store --ask` does not apply it.

⚠️⚠️ **AND IT CONFOUNDS EXACTLY THE COMPARISON THE STORE EXISTS FOR.** Today
Litolff has ink rows and Breitkopf has none (§4), so **a pooled per-name
`mean_h` between them measures which record was gathered with ink, not the two
plates.** That is `A-INK-4` — *a measurement retires a concept only within the
factor set it was taken in* — with `source_quantity` as the factor nobody was
holding. It is a second, independent reason the ranked next work in §4 (gather
Breitkopf WITH ink) is the right next step: it removes the confound rather
than working around it.

⚠️ **DELIBERATELY NOT FIXED.** Whether `--ask` should split, filter or merely
report the split is a design decision about the store's contract, not a bug to
patch mid-session, and this session's brief was one measurement. The probe
prints REACH first and **exits 3 declaring itself DEAD** on a store with no
`ink` rows, since a clean table there would mean nothing.

## 11. THE HANDOFF'S §3 — what was deliberately NOT concluded, and NOT built

Recorded because compliance with a *"do not conclude X"* instruction is
invisible unless stated.

⚠️ **`A-INK-4`, first half: a measurement retires a concept only within the
factor set it was taken in.** Nothing here asks whether the identity fact
HELPS, and no such answer is offered. It cannot be asked: `Q.DOCUMENT_IDENTITY`
is read by nothing, by design, so its partners do not exist and a "no" would
measure their absence. `Q.STEM` is the standing near-miss — gathered and unread
through THREE discoveries, worth 114 narrowed durations the day something read
it. ⚠️ §10 is the same rule biting from a direction the handoff did not
anticipate: `source_quantity` was a factor **nobody was holding**, and pooling
across it turns a clean cross-publisher agreement (0.280 vs 0.288) into an
apparent 3× discrepancy.

⚠️ **`A-INK-4`, second half: a factor CONTRIBUTES, it does not decide.** No
rule, veto or threshold using a position was added. Checked rather than
asserted: the only `tools/` Python change in this branch is a comment, proved
**AST-identical** to its parent, and the only new executable code is a TEST
comparing prose to predicates. The store's own `--ask` was left alone even
though §10 gives a reason to change it.

⚠️ **And one thing the handoff did NOT warn about, which this session nearly
did anyway:** I read a stale CLAUDE.md table and "corrected" a handoff command
that was already right, killing a good 15-minute run (§2). The instruction to
distrust a negative result has an obvious twin — **distrust a defect you find
in someone else's instructions until you have read the code it describes.**
The predicate was one `grep` away the whole time.

## 12. FIXED — the index keys on the membership KIND, on Sean's call

Sean, 2026-09-17, on §10: *"unless it is possible to redo the measurements
using all the same kind of measuring standard. Up to you — whatever is best
long term: fewer mistakes, clarity and flexibility."*

**They cannot be put on one standard, and they should not be.** A
`glyph_box` height is *how tall this notehead is*; an `ink` height is *how
tall the merged blob this notehead's box overlaps is*. Different objects,
different questions. Unifying them would destroy a real fact — Litolff merges
and Breitkopf shatters — which is the fact the ink layer exists to capture.

⚠️⚠️ **AND THE DATA MODEL ALREADY SAID SO. `Membership.kind` distinguishes
them exactly**, and its own docstring is the rule the index was breaking:
*"`detector_class` is an argmax over a box; `overlaps` is `ink_explained_by`,
which its own docstring says is coverage and NOT an assertion of identity"*.
So this needed **no re-measurement, no re-gather and no schema change** — only
for the index to respect a distinction the store had been recording all along.

`PositionIndex._build` now keys on `(tier, publisher, KIND, name)`:

| | before | after |
|---|---|---|
| `noteheadBlackOnLine` @ position 0, Litolff | ONE row, `mean_h` **3.646** | `detector_class` **1.316 ± 0.133** · `overlaps` **6.872 ± 2.346** |
| cross-publisher notehead | 3.646 vs 1.199 — looked 3× | **1.316 vs 1.199** |
| cross-publisher ledger line | mixed | **0.280 vs 0.295** |

✅ **Split, the two publishers agree on all four shared classes.** The store
now answers the question it was built for, and what remains between the plates
(Litolff ledger-heavy at 0.456 share, Breitkopf tie-heavy at 0.332) is the
kind of difference it exists to learn.

**Against Sean's three criteria:** *fewer mistakes* — pooling is now
structurally impossible rather than documented; *clarity* — every row says
which claim it is, with a one-line gloss in the output (`the detector says
this IS that class` / `a detection merely COVERS part of this ink; not
identity` / `nothing claims this ink`); *flexibility* — nothing is hidden or
dropped, both rows are returned, and `share` is computed WITHIN a kind, since
a detection and an overlapping blob are not competing hypotheses about one
object.

⚠️ **Filtering by default was considered and REFUSED.** Defaulting `--ask` to
`detector_class` would have hidden the ink half behind a flag — and hiding the
newest, least-understood layer is exactly how `Q.STEM` went unread through
three separate discoveries. Sean's own instruction on the ink work was *"we
need to hold on to everything because we can't yet know all of what will be
helpful."*

⚠️⚠️ **AND IT FOUND A LATENT BUG IN `kinds`, THE PARAMETER THAT HAD NO
PRODUCER.** `PositionIndex(kinds=…)` was declared and **nothing ever passed
one**, so it had never run. The first test to pass it showed that an entry
whose only memberships the filter EXCLUDED fell through to
`UNNAMED`/`UNKNOWN` — so asking for identity claims alone reported every ink
row as *unclaimed ink* and inflated the unnamed bucket by the size of the
filter. **That is the ABSENT/DECLINED collapse `record.py` exists to prevent,
inside the index.** Now only an entry with no memberships AT ALL is unnamed;
one whose claims we declined to look at is skipped.

⚠️ Two existing tests were **rewritten to the new contract, not deleted** (a
renamed share field, and an index key that gained an element — the behaviour
each pinned is intact). Five new tests pin the split, including that the
pooled mean 4.65 — *neither a notehead nor a blob* — can no longer appear.
`demo-query.txt` regenerated; `separation.json` and `cross_tier.json` do not
use the query and are unaffected. 34 tests pass; `wiring --check` and
`capture --check` still exit 0.
