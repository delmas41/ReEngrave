"""Appends section 8 to FINDINGS.md. The Bash tool refuses a heredoc holding a
shell code block, so the block is written from here instead."""
import os

DEST = os.path.join(os.path.dirname(__file__), "..", "FINDINGS.md")

TEXT = """
---

## 8. Reproducing

Fixtures are gitignored build products, so in a worktree point the probes at the
main checkout with `OMR_FIXTURE_ROOT`.

```
export OMR_FIXTURE_ROOT=/Users/seanjohnson/Desktop/ReEngrave
P=benchmarks/omr-additive-vs-gated-2026-09/probe

python3 $P/probe_gate_reach.py              # 3    gate firing rates, both families
python3 $P/probe_register_warning.py        # 4.4  every clef_register_warning, adjudicable
python3 $P/probe_clef_proposals.py          # 4.5  the clef funnel as the pipeline ran it
python3 $P/probe_propose_clef_branches.py   # 4.5  which `return None` each staff takes
python3 $P/probe_fill_population.py         # 4.5  is the fill population noteheadless?
python3 $P/probe_clef_provenance_gate.py    # 4.5  what contextual.py:1202 refuses
python3 $P/probe_dynamic_runs.py            # 4.3  refused dynamic runs + edit distance
python3 $P/probe_low_labels.py              # 4.6  the `low` drop and its neighbour
python3 $P/probe_absent_veto_scale.py       # 4.2  the veto at document scale

OMR_SURYA_KEEP_ALIVE=0 python3 $P/dump_contests.py   # ~50 s/row x 20 rows
python3 $P/analyse_contests.py                       # 4.1
```

Every output is committed under `out/`; the per-row contest dumps are under
`out/contests/`.

⚠️ `dump_contests.py` writes to this benchmark's own `out/`, never to the scan
gate's `fixtures/`, and sets `OMR_SURYA_KEEP_ALIVE=0` — **never blanket-kill
`llama-server`**; a shared instance is up, and killing one destroyed another
agent's multi-hour run on 2026-09-06.

⚠️ `probe_propose_clef_branches.py` REIMPLEMENTS `propose_clef`'s branch
structure (using that module's own helpers and constants) because the function
records nothing at its exits. **If those constants or that branch order move,
this probe goes silently stale** — which is itself the argument for shortlist
item 1.

⚠️ The scan family here is the 11 committed `.graft09` fixtures (11 pages); the
contest dump covers all 20 gate rows because it re-runs them. Where a figure is
quoted "over 193 staves" it is the 11-page set; where it is quoted over 4,521
pairs it is the 20-row set. They are different denominators on purpose and
should not be mixed.
"""

with open(DEST, "a") as fh:
    fh.write(TEXT)
print("appended")
