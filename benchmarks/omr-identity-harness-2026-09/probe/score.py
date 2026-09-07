"""Score staff identity, and report the four axes SIDE BY SIDE.

Phase 0 of `docs/scope-identity-upstream-2026-09-06.md`.

## Why four columns and not one number

They reward different things and none is a superset of another.  The Brahms
span arms are the worked example already in the record: `refuse` grades ONE
staff better than the shipped `search` on correct/wrong (742 vs 741) while
leaving 36 categorically impossible names standing where `search` reads 0.
Averaging those into a score hides the only interesting fact about the pair.

    IDENTITY      correct / wrong / unnamed over judgeable staff records.
    IMPOSSIBLE    names the document cannot be printing there.  Can only
                  FALL, so it scores a categorically-wrong name traded for an
                  ordinarily-wrong one as free — never read it alone.
    CONTRADICTED  a staff whose own margin label the reader RESOLVED and which
                  is exported as something else.  The cost column `impossible`
                  cannot be, and it needs no hand-read truth.
    HUMAN         staves a person would have to adjudicate.  Sean's stated
                  reason for the programme is that human interaction is the
                  most expensive part of the process, so a change that
                  improves accuracy without reducing this has not delivered
                  what it was built for.  Abstention is permitted and is NOT
                  free — it is the most expensive outcome the system produces.

## ⚠️ Two different denominators, on purpose

IDENTITY is over JUDGEABLE records (full systems, ~44% of the document) —
that is the only population with hand-read truth.  HUMAN cost is over EVERY
staff record, because a person reviewing the score reviews all of it.  Both
denominators are printed on every row; mixing them is the mistake this note
exists to prevent.

## ⚠️ The provenance split is REPORTED, never filtered

`instrument_source` is load-bearing and has already caught one trap: a naive
label-contradiction check reports our own landed fixes as defects unless the
source is split out.  But it is a split to SHOW: on the current artefacts
`score_order_ambiguity` holds 96 rows of which 93 were a live defect and only
3 were the correct `Basso.` overturn, so excluding that source would have
hidden the 93.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field

import corpus
from load import Document


@dataclass
class Report:
    work: str
    arm: str
    regime: str
    # denominators
    n_records: int = 0
    n_judgeable: int = 0
    n_systems: int = 0
    n_judgeable_systems: int = 0
    # identity
    correct: int = 0
    wrong: int = 0
    unnamed: int = 0
    # cost columns, over ALL records
    impossible: int = 0
    never: int = 0
    contradicted: int = 0
    vetoed: int = 0
    human: int = 0
    human_breakdown: dict = field(default_factory=dict)
    # splits
    confusion: collections.Counter = field(default_factory=collections.Counter)
    by_lineup: dict = field(default_factory=dict)
    by_source: dict = field(default_factory=dict)
    records: list = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.correct / self.n_judgeable if self.n_judgeable else float("nan")

    @property
    def human_rate(self) -> float:
        return self.human / self.n_records if self.n_records else float("nan")


def score(doc: Document, regime: str = "whole work") -> Report:
    work = doc.work
    rep = Report(work=work, arm=doc.arm, regime=regime)

    systems: dict[tuple[int, int], list] = {}
    for s in doc.staves:
        systems.setdefault((s.page, s.system), []).append(s)
    rep.n_records = len(doc.staves)
    rep.n_systems = len(systems)

    per_lineup = collections.Counter()
    per_lineup_ok = collections.Counter()
    per_lineup_sys = collections.Counter()
    src_tot = collections.Counter()
    src_ok = collections.Counter()
    src_unnamed = collections.Counter()

    for (pg, _sy), sts in sorted(systems.items()):
        sts.sort(key=lambda s: s.staff_index)
        tag, names = corpus.truth_for(work, pg, len(sts))
        if names is None:
            continue
        rep.n_judgeable_systems += 1
        per_lineup_sys[tag] += 1
        for s in sts:
            want = names[s.ordinal]
            got = s.instrument
            rep.n_judgeable += 1
            per_lineup[tag] += 1
            src = s.source or "(none)"
            src_tot[src] += 1
            if got is None:
                rep.unnamed += 1
                rep.confusion[(want, "(unnamed)")] += 1
                src_unnamed[src] += 1
            elif got == want:
                rep.correct += 1
                per_lineup_ok[tag] += 1
                src_ok[src] += 1
            else:
                rep.wrong += 1
                rep.confusion[(want, got)] += 1
            rep.records.append({
                "work": work, "engraving": corpus.ENGRAVING.get(work),
                "publisher": corpus.PUBLISHER.get(work), "arm": doc.arm,
                "page": s.page, "system": s.system, "ordinal": s.ordinal,
                "n_staves": s.n_staves, "lineup": tag, "slot": s.slot,
                "source": s.source, "truth": want, "emitted": got,
                "correct": got == want, "named": got is not None,
                "label_read": s.label_read,
                "contradicted": bool(s.label_read and got and s.label_read != got),
            })

    # ── cost columns, over EVERY staff record ────────────────────────────────
    hb = collections.Counter()
    for s in doc.staves:
        flags = []
        if s.instrument is None:
            flags.append("unnamed")
        if corpus.is_impossible(work, s.page, s.instrument):
            rep.impossible += 1
            flags.append("impossible")
        if corpus.is_never(work, s.instrument):
            rep.never += 1
            flags.append("not-in-this-work")
        if s.label_read and s.instrument and s.label_read != s.instrument:
            rep.contradicted += 1
            flags.append("contradicted")
        if s.vetoed:
            rep.vetoed += 1
        if flags:
            rep.human += 1
            hb[tuple(sorted(flags))] += 1
    rep.human_breakdown = {"+".join(k): v for k, v in sorted(hb.items())}

    rep.by_lineup = {k: (per_lineup_ok[k], per_lineup[k], per_lineup_sys[k])
                     for k in sorted(per_lineup)}
    rep.by_source = {k: (src_ok[k], src_unnamed[k], src_tot[k])
                     for k in sorted(src_tot)}
    return rep


# ─────────────────────────────────────────────────────────────────────────────
# printing
# ─────────────────────────────────────────────────────────────────────────────
HEAD = (f"{'arm':32s} {'work':8s} {'judge':>6s} {'corr':>5s} {'wrng':>5s} "
        f"{'unnm':>5s} {'rate':>7s} | {'impos':>6s} {'nowrk':>5s} "
        f"{'contra':>6s} | {'human':>6s} {'/recs':>6s} {'rate':>7s}")


def line(r: Report) -> str:
    return (f"{r.arm:32s} {r.work:8s} {r.n_judgeable:6d} {r.correct:5d} "
            f"{r.wrong:5d} {r.unnamed:5d} {r.rate:7.4f} | {r.impossible:6d} "
            f"{r.never:5d} {r.contradicted:6d} | {r.human:6d} {r.n_records:6d} "
            f"{r.human_rate:7.4f}")


def pooled(reports: list[Report], arm: str) -> Report:
    p = Report(work="POOLED", arm=arm,
               regime="/".join(sorted({r.regime for r in reports})))
    for r in reports:
        for f in ("n_records", "n_judgeable", "n_systems", "n_judgeable_systems",
                  "correct", "wrong", "unnamed", "impossible", "never",
                  "contradicted", "vetoed", "human"):
            setattr(p, f, getattr(p, f) + getattr(r, f))
        p.confusion.update(r.confusion)
        p.records.extend(r.records)
        for k, v in r.by_lineup.items():
            p.by_lineup[f"{r.work}:{k}"] = v
        for k, v in r.by_source.items():
            a, b, c = p.by_source.get(k, (0, 0, 0))
            p.by_source[k] = (a + v[0], b + v[1], c + v[2])
        for k, v in r.human_breakdown.items():
            p.human_breakdown[k] = p.human_breakdown.get(k, 0) + v
    return p


def detail(r: Report, n_conf: int = 20) -> str:
    out = [f"--- {r.arm}   work={r.work}   regime={r.regime}",
           f"    judgeable {r.n_judgeable} of {r.n_records} staff records "
           f"({r.n_judgeable / r.n_records:.1%}); "
           f"{r.n_judgeable_systems} of {r.n_systems} systems are FULL",
           "    per lineup:"]
    for k, (ok, tot, nsys) in r.by_lineup.items():
        out.append(f"      {k:22s} ({nsys:3d} systems): {ok:4d}/{tot:4d} "
                   f"= {ok / tot:.4f}")
    out.append("    per instrument_source (REPORTED, never filtered):")
    for k, (ok, un, tot) in r.by_source.items():
        out.append(f"      {k:24s} {ok:4d} correct, {un:3d} unnamed, "
                   f"{tot:4d} judgeable  = {ok / tot:.4f}")
    out.append("    human-cost breakdown (over ALL staff records):")
    for k, v in sorted(r.human_breakdown.items(), key=lambda kv: -kv[1]):
        out.append(f"      {k:34s} {v:5d}")
    if r.confusion:
        out.append("    confusions (truth -> emitted):")
        for (w, g), n in r.confusion.most_common(n_conf):
            out.append(f"      {n:5d}  {w:16s} -> {g}")
    return "\n".join(out)
