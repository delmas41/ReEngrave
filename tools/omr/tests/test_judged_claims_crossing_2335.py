"""ROADMAP 2.335 -- `judged_claims`: WHERE A TREMOLO SLASH CROSSES ITS STEM, THE CROSSING BELONGS TO BOTH (Sean 2026-11-23: "The point where a stem and a
slash cross each other belongs to both"; page-facts).

The arrays are REAL: `data_judged_claims_crossing_2335.npz` is the finished page ledger (`claim_readout.LedgerInk`) of the 20261122-night Litolff slice, cut
round eight of Sean's answered tiles (pages 2, 6, 16). Six are his slashes, where the stem runs through his box; two are his dynamics ('sf' with a beam and a
stem on it, 'dynamic p' with an arc and a stem on it), which must still contradict: the rule excuses the stem on a slash and nothing else."""
import json
import pathlib
import types

import numpy as np

from tools.omr.staged import judged_claims as JC

DATA = pathlib.Path(__file__).with_name("data_judged_claims_crossing_2335.npz")
SLASHES = ("2.276 r2 #4", "2.276 r2 #7", "2.276 r2 #8", "2.276 r2 #12", "2.290 r1 #2", "2.290 r1 #3")
OTHERS = ("2.284b r2 #2", "2.284b r1 #1")
FIELDS = ("ink", "state", "fam_eff", "src_cell", "src_area", "src_page", "open", "incell", "weak_eff", "uk")


def _key(tid):
    return "t" + "".join(ch if ch.isalnum() else "_" for ch in tid)


def _load(tid):
    z = np.load(DATA)
    k = _key(tid)
    c = types.SimpleNamespace(**{f: z[k + "__" + f] for f in FIELDS})
    c.weak = c.weak_eff
    c.shape = c.ink.shape
    return c, json.loads(str(z["meta"]))[k]


def _verdict(tid, partner=None):
    c, t = _load(tid)
    if partner is None:
        return JC.judge_tile(c, t)
    old = JC.CROSSING_PARTNER
    JC.CROSSING_PARTNER = partner
    try:
        return JC.judge_tile(c, t)
    finally:
        JC.CROSSING_PARTNER = old


def test_his_slashes_agree():
    for tid in SLASHES:
        r = _verdict(tid)
        assert r["verdict"] == "agrees", (tid, r)


def test_the_stem_through_his_slash_contradicted_before_the_ruling():
    """Without the crossing rule (the tool before 2.335) four of the six read CLAIMED TWICE on this slice: the control can fail."""
    before = {tid: _verdict(tid, partner={})["verdict"] for tid in SLASHES}
    assert sum(v == "contradicts" for v in before.values()) >= 4, before


def test_other_kinds_still_contradict():
    for tid in OTHERS:
        r = _verdict(tid)
        assert r["verdict"] == "contradicts", (tid, r)


def test_only_the_stem_is_excused_on_a_slash():
    """His 'dynamic p' relabelled a slash in memory: the dynamic and arc claims on it still stand against it (only a stem is excused)."""
    c, t = _load("2.284b r1 #1")
    r = JC.judge_tile(c, t, kind="tremolo")
    assert r["verdict"] == "contradicts" and r["wrong_any"] >= 0.8, r
    assert JC.CROSSING_PARTNER == {"tremolo": ("stem",), "stem": ("tremolo",)}
