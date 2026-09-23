# `benchmarks/acceptance/`

Two things live here, and they answer different questions.

**`open-findings.json`** — the running total of open findings across every
derived self-check this repo has (`tools/omr/staged/check.py`, Phase 0 item
0.4b of
[`docs/plan-2026-09-22-from-here-to-a-finished-score.md`](../../docs/plan-2026-09-22-from-here-to-a-finished-score.md)).
It answers *"is the wiring getting more or less complete over time"*. It is
written by

```bash
python3 -m tools.omr.staged.check --write          # refuses on a dirty tree
python3 -m tools.omr.staged.check --write --force  # writes anyway, dirty: true
```

and refuses to write on a dirty tree unless `--force` is given, because a
number meant to be watched falling must name the commit it was true of — a
figure taken mid-edit cannot later be told apart from one taken after a real
repair.

**`current.json`** (ROADMAP.md Phase 1 item 1.3, built by
`python3 -m tools.omr.acceptance`) is the acceptance-harness output: the
three documents named in `manifest.json` run end to end — MusicXML export,
the machine proxies, and, for the engraved document, reading F1 against the
exact page truth, OMR-NED against the encoding, and a LilyPond conversion.
It answers *"is the product closer to done"*, which `open-findings.json`
cannot — a check can go green because a gap got wired OR because someone
deleted the mechanism it was watching, and only a real run against the
acceptance set tells those apart.

```bash
python3 -m tools.omr.acceptance                    # all three documents
python3 -m tools.omr.acceptance --doc <id>          # one document
python3 -m tools.omr.acceptance --no-write          # dry run
```

`manifest.json` names each document (record path, count page, works.json row
where one exists, truth files for the engraved document) and carries an md5
RECEIPT for each record — recorded on first run, and any later mismatch
refuses the whole run loudly, because the shared records under
`library/_shared-records/` are machine-local and gitignored. **Today the two
scan documents are scored on the four-page partial records built before
ROADMAP 1.1's whole-movement gather** (see `current.json`'s own
`caveats`/`provenance` fields per document) — the manifest and the receipts
are what let a later run swap in the whole-movement record without this
tool changing.

Neither file is a headline on its own. Read them beside the cleanup count
(plan §4), which is the only number Sean adjudicates by hand.
