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

**`current.json`** (plan §5 Phase 1.3, not built by this item) will be the
acceptance-harness output: the three acceptance documents run end to end,
their machine proxies, and the engraved reading score. It answers *"is the
product closer to done"*, which `open-findings.json` cannot — a check can go
green because a gap got wired OR because someone deleted the mechanism it was
watching, and only a real run against the acceptance set tells those apart.

Neither file is a headline on its own. Read them beside the cleanup count
(plan §4), which is the only number Sean adjudicates by hand.
