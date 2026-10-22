"""ROADMAP 2.54 -- re-decide `Q.TIE_PAIR` ONLY over a saved record's own
GATHER rows, STREAMING the input so a multi-GB record is never loaded whole
(`ijson`, same approach as `positional_store.stream_observations`).

    python3 benchmarks/omr-tie-pairing-2026-09/probe/readjudicate_2_54.py \
        REC [--pages 0,1,2,3] [--out SUMMARY.json]

Reads only what `adjudicate_tie_pair` itself declares (`Q.ARC_BOX`,
`Q.GLYPH_BOX`, `Q.CELL_BOX` as observations; `Q.ARC_KIND`, `Q.ARC_OWNER`,
`Q.ARC_IS_NOT_AN_ARC`, `Q.GLYPH_OWNER`, `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` as
upstream verdicts, INJECTED exactly as saved, never recomputed) and filters
by PAGE while streaming, before anything is held in memory. The upstream
verdicts' own `considered`/`basis`/`correlated` fields are never read by
this decision, so they are dropped rather than pool-expanded -- the one
simplification that lets this skip `record.pools` (and its own cost)
entirely.

⚠️ BLIND TO GATHER, like every tool of this shape (CLAUDE.md): a change to
what GATHER files is invisible here, and a zero is not evidence about one.
⚠️ `--pages` is the record's OWN page coordinate; a lone page loses the
meter/key carry upstream decisions needed, but `Q.TIE_PAIR` itself only
reaches one bar either side, never across a system, so a page SLICE (not a
single page) is a cheap INPUT here, not a different reader.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import ijson  # noqa: E402

from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401
from tools.omr.staged.record import Log, Outcome, Q, Subject, Verdict  # noqa: E402

OBS_WANT = {Q.ARC_BOX, Q.GLYPH_BOX, Q.CELL_BOX}
VRD_WANT = (Q.ARC_KIND, Q.ARC_OWNER, Q.ARC_IS_NOT_AN_ARC, Q.GLYPH_OWNER,
            Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)

_PAGE_RE = re.compile(r"^[a-z]+/(\d+)")


def _page_of(subject_key: str):
    m = _PAGE_RE.match(subject_key)
    return int(m.group(1)) if m else None


def _keep(subject_key: str, pages) -> bool:
    if pages is None:
        return True
    p = _page_of(subject_key)
    return p is None or p in pages


def _outcome(word: str) -> Outcome:
    return {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED,
            "abstained": Outcome.ABSTAINED}[word]


def stream_build(path: str, pages) -> Log:
    log = Log()
    n_obs = 0
    with open(path, "rb") as fh:
        for item in ijson.items(fh, "record.observations.item",
                                 use_float=True):
            if item["quantity"] not in OBS_WANT:
                continue
            if not _keep(item["subject"], pages):
                continue
            detail = dict(item.get("detail") or {})
            log.observe(Subject.from_key(item["subject"]), item["quantity"],
                        item["value"], reader=item["reader"],
                        frame=item["frame"], score=item.get("score"),
                        **detail)
            n_obs += 1
    log.freeze()
    print(f"  streamed {n_obs} observations", file=sys.stderr)

    # ⚠️ TWO-PASS over verdicts, in memory, because a revision must be
    # resolved (superseded rows dropped) before the log sees either one --
    # `Log.record` raises `AlreadyAdjudicated` on a second write to one
    # (quantity, subject). The kept set is small: five quantities, the
    # requested pages only.
    current, superseded = {}, set()
    with open(path, "rb") as fh:
        for item in ijson.items(fh, "record.verdicts.item", use_float=True):
            if item["quantity"] not in VRD_WANT:
                continue
            if not _keep(item["subject"], pages):
                continue
            if item.get("supersedes"):
                superseded.add(item["supersedes"])
            current[(item["quantity"], item["subject"])] = item
    n_vrd = 0
    for (q, key), v in current.items():
        if v["id"] in superseded:
            continue
        log.record(Verdict(
            id=v["id"], subject=Subject.from_key(key), quantity=q,
            outcome=_outcome(v["outcome"]), value=v.get("value"),
            decider=v["decider"], reason=v["reason"]))
        n_vrd += 1
    print(f"  streamed {n_vrd} upstream verdicts", file=sys.stderr)
    return log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--pages", default="",
                     help="keep only these record pages (comma list); "
                          "omitted = the whole record")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    pages = {int(p) for p in a.pages.split(",")} if a.pages else None
    t0 = time.time()
    log = stream_build(a.record, pages)

    A._ensure_decisions()
    spec = A.REGISTRY[Q.TIE_PAIR]
    subjects = A.subjects_for(log, spec)
    by_reason = collections.Counter()
    decided_pairs = []
    for sub in subjects:
        v = A.adjudicate_one(log, spec, sub)
        by_reason[(v.outcome.value, v.reason)] += 1
        if v.outcome is Outcome.DECIDED:
            decided_pairs.append({"arc": sub.to_key(), **v.value,
                                   "dy_spaces": v.detail.get("dy_spaces"),
                                   "crosses_barline":
                                       v.detail.get("crosses_barline")})

    n_arcs = len(subjects)
    elapsed = round(time.time() - t0, 1)
    print(f"arcs considered: {n_arcs}  ({elapsed}s)")
    for (outcome, reason), c in by_reason.most_common():
        print(f"  {outcome:10s} {reason:28s} {c}")
    if a.out:
        json.dump({
            "record": a.record, "pages": sorted(pages) if pages else "all",
            "seconds": elapsed, "arcs_considered": n_arcs,
            "tie_pair": {f"{o}:{r}": c for (o, r), c in by_reason.items()},
            "decided_pairs": decided_pairs,
        }, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
