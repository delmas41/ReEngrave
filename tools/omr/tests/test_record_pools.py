"""`record_io`: the id-list pools a staged record FILE carries (roadmap 1.1b).

⚠️ EVERY ROUND-TRIP TEST HERE IS PAIRED WITH THE NAIVE READING, so the pooling
is shown to have HAPPENED rather than assumed: a control that would pass on a
writer that pooled nothing is not a control. Fixtures mimic the measured
shape -- N verdicts in one system whose `considered`/`basis` share a core of
hundreds of ids and differ by one private id each, whose `correlated` inner
groups repeat verbatim -- because that is what `arc_owner` writes.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.omr.staged import record_io as RIO
from tools.omr.staged.record import Kind, Log, Outcome, Subject, Verdict

try:
    import ijson  # noqa: F401
    HAVE_IJSON = True
except ImportError:
    HAVE_IJSON = False


CORE = [f"obs:{i:06d}" for i in range(100, 100 + 300)]      # 300 shared ids
GROUP_A = sorted(CORE[:120])
GROUP_B = sorted(CORE[120:250])


def _arc_like_record(n: int = 5, system: int = 0) -> dict:
    """`n` verdicts on glyphs of one system, each carrying the shared core
    plus ONE private id (its own arc row) -- `considered` with the private
    id FIRST (insertion order), `basis` with it SORTED into place."""
    verdicts = []
    for k in range(n):
        # sorts INTO the core (after obs:000200), never before or after
        # it all, so the sorted `basis` insertion is a mid-list position
        own = f"obs:{200 + k:06d}x"
        considered = [own] + CORE
        basis = sorted(CORE + [own])
        verdicts.append({
            "id": f"vrd:{k:06d}", "subject": f"glyph/0/{system}/{k}/0/1",
            "quantity": "arc_owner", "outcome": "decided",
            "value": f"staff/0/{system}/{k}", "decider": "adjudicate_arc_owner",
            "reason": "no_better_staff", "considered": considered,
            "used": [own], "missing": [], "declined": [], "excluded": [],
            "correlated": [GROUP_A, GROUP_B, ["obs:000001", "obs:000002"]],
            "candidates": [], "basis": basis, "margin": None,
            "supersedes": None, "detail": {"own_covered": k},
        })
    return {
        "record": {
            "observations": [
                {"id": rid, "subject": "glyph/0/0/0/0/1", "quantity": "glyph_box",
                 "value": ["noteheadBlackInSpace", 0, 0, 1, 1], "reader": "detector",
                 "frame": "cell:0", "score": 0.9, "detail": {}, "basis": []}
                for rid in CORE[:3]],
            "abstentions": [],
            "verdicts": verdicts,
            "counts": {"observations": 3, "abstentions": 0, "verdicts": n},
        },
        "provenance": {"commit": "test", "dirty": False},
    }


class RoundTrip(unittest.TestCase):

    def test_pooled_file_loads_back_to_the_SAME_dict(self):
        result = _arc_like_record()
        text = RIO.dumps_for_file(result, separators=(",", ":"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rec.json")
            with open(p, "w") as f:
                f.write(text)
            loaded = RIO.load_record(p)
        self.assertEqual(loaded, result)

    def test_and_the_naive_reading_is_NOT_the_same(self):
        """The control's other half: bare `json.loads` sees the pools and
        the references, so the previous test passed because expansion
        worked, not because nothing was pooled."""
        result = _arc_like_record()
        naive = json.loads(RIO.dumps_for_file(result))
        self.assertNotEqual(naive, result)
        self.assertIn(RIO.POOL_KEY, naive["record"])
        v0 = naive["record"]["verdicts"][0]
        self.assertIsInstance(v0["considered"], dict)
        self.assertEqual(sorted(v0["considered"]), sorted([RIO.INS_KEY, RIO.REF_KEY]))
        self.assertIsInstance(v0["basis"], dict)
        self.assertIsInstance(v0["correlated"][0], dict)
        # the tiny third group stays inline: below MIN_POOL_IDS
        self.assertEqual(v0["correlated"][2], ["obs:000001", "obs:000002"])

    def test_the_private_id_lands_at_its_ORIGINAL_position(self):
        """`considered` is insertion-ordered and `basis` sorted; the
        pooled spelling must restore the id where it stood, not append it."""
        result = _arc_like_record(n=3)
        naive = json.loads(RIO.dumps_for_file(result))
        v2 = naive["record"]["verdicts"][2]
        own = result["record"]["verdicts"][2]["used"][0]
        self.assertEqual(v2["considered"][RIO.INS_KEY], [[0, own]])
        pos = result["record"]["verdicts"][2]["basis"].index(own)
        self.assertEqual(v2["basis"][RIO.INS_KEY], [[pos, own]])
        self.assertGreater(pos, 0)
        self.assertLess(pos, len(CORE))

    def test_the_file_is_SMALLER_by_the_repetition(self):
        result = _arc_like_record(n=10)
        fat = len(json.dumps(result, separators=(",", ":")))
        thin = len(RIO.dumps_for_file(result, separators=(",", ":")))
        # 10 verdicts x 3 lists x ~300 ids collapse to 3 pooled lists
        self.assertLess(thin, fat / 5)

    def test_in_memory_result_is_NEVER_mutated(self):
        result = _arc_like_record()
        before = json.dumps(result, sort_keys=True)
        RIO.dumps_for_file(result)
        self.assertEqual(json.dumps(result, sort_keys=True), before)


class WhatIsLeftAlone(unittest.TestCase):

    def test_a_small_record_is_written_EXACTLY_as_before(self):
        """Below `MIN_POOL_IDS` nothing is pooled, so every existing fixture
        and every hand-built record is byte-for-byte unchanged -- and
        `pool_id_lists` returns the very same object."""
        log = Log()
        for k in range(3):
            sub = Subject(Kind.STAFF, page=0, system=0, staff=k)
            log.record(Verdict(
                id=f"vrd:{k}", subject=sub, quantity="clef",
                outcome=Outcome.DECIDED, value="G", decider="d", reason="r",
                considered=("obs:1", "obs:2"), basis=("obs:1", "obs:2")))
        rec = log.to_json()
        self.assertIs(RIO.pool_id_lists(rec), rec)
        self.assertEqual(json.loads(RIO.dumps_for_file({"record": rec})),
                         {"record": rec})

    def test_a_group_of_ONE_is_inline(self):
        result = _arc_like_record(n=1)
        naive = json.loads(RIO.dumps_for_file(result))
        self.assertNotIn(RIO.POOL_KEY, naive["record"])
        self.assertEqual(naive, result)

    def test_two_systems_get_two_pools(self):
        a = _arc_like_record(n=3, system=0)["record"]["verdicts"]
        b = [dict(v, id=v["id"].replace("vrd:", "vrd:1"),
                  considered=[v["used"][0]] + CORE[::-1],
                  basis=sorted(CORE[::-1] + [v["used"][0]]))
             for v in _arc_like_record(n=3, system=1)["record"]["verdicts"]]
        rec = {"observations": [], "abstentions": [], "verdicts": a + b}
        pooled = RIO.pool_id_lists(rec)
        # considered: two cores (CORE in order for system 0, reversed for
        # system 1); basis: sorted(CORE) in BOTH systems -- which is CORE
        # itself, so it is interned ONCE by content with system 0's
        # considered core; correlated: GROUP_A and GROUP_B. Four pools.
        self.assertEqual(len(pooled[RIO.POOL_KEY]), 4)
        self.assertEqual(RIO.expand_id_lists(json.loads(json.dumps(pooled))),
                         rec)

    def test_an_unpooled_record_loads_unchanged_and_is_idempotent(self):
        result = _arc_like_record(n=1)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rec.json")
            with open(p, "w") as f:
                json.dump(result, f)
            loaded = RIO.load_record(p)
        self.assertEqual(loaded, result)
        self.assertEqual(RIO.expand_result(loaded), result)

    def test_a_bare_record_without_the_envelope_also_expands(self):
        rec = _arc_like_record()["record"]
        pooled = json.loads(json.dumps(RIO.pool_id_lists(rec)))
        self.assertIn(RIO.POOL_KEY, pooled)
        self.assertEqual(RIO.expand_result(pooled), rec)


class TheControlCanFail(unittest.TestCase):

    def test_a_dangling_reference_RAISES_rather_than_reading_empty(self):
        result = _arc_like_record()
        naive = json.loads(RIO.dumps_for_file(result))
        naive["record"][RIO.POOL_KEY] = {"pool:99999": []}
        with self.assertRaises(RIO.PoolMismatch):
            RIO.expand_result(naive)

    def test_the_writer_refuses_a_spelling_that_does_not_expand_back(self):
        """Break `_decode` and the writer's own self-check must catch it."""
        result = _arc_like_record()
        real = RIO._decode
        RIO._decode = lambda core, ins: list(core)      # drops the insertions
        try:
            with self.assertRaises(RIO.PoolMismatch):
                RIO.pool_id_lists(result["record"])
        finally:
            RIO._decode = real

    def test_encode_refuses_a_core_that_is_not_a_subsequence(self):
        self.assertIsNone(RIO._encode(["a", "b", "c"], ["c", "a"]))
        self.assertEqual(RIO._encode(["x", "a", "b", "y", "c"], ["a", "b", "c"]),
                         [[0, "x"], [3, "y"]])
        self.assertEqual(RIO._decode(["a", "b", "c"], [[0, "x"], [3, "y"]]),
                         ["x", "a", "b", "y", "c"])


class TheReadersGoThroughTheLoader(unittest.TestCase):
    """The in-tree consumers of the three fields read a pooled file as they
    read the unpooled one. Each is compared against ITSELF on the unpooled
    file, so a reader that silently iterated `"$pool"` would differ."""

    def _both_files(self, d, result):
        fat = os.path.join(d, "fat.json")
        thin = os.path.join(d, "thin.json")
        with open(fat, "w") as f:
            json.dump(result, f)
        with open(thin, "w") as f:
            f.write(RIO.dumps_for_file(result))
        with open(thin) as f:
            assert RIO.POOL_KEY in json.load(f)["record"]
        return fat, thin

    def test_trace_step_counts_agree(self):
        from tools.omr.staged import trace as T
        result = _arc_like_record()
        with tempfile.TemporaryDirectory() as d:
            fat, thin = self._both_files(d, result)
            a = T._load(fat)
            b = T._load(thin)
        va = a.verdicts[0]
        vb = b.verdicts[0]
        sa = T._verdict_step("ADJUDICATE", va, {})
        sb = T._verdict_step("ADJUDICATE", vb, {})
        self.assertEqual(sa, sb)
        self.assertEqual(sa["considered"], len(CORE) + 1)
        self.assertEqual(sa["basis"], len(CORE) + 1)
        self.assertEqual(sa["correlated_groups"], 3)

    def test_brakes_measure_agrees(self):
        from tools.omr.staged import brakes as B
        result = _arc_like_record()
        # an UNRESOLVED verdict is what `measure` inspects; give it one that
        # carries the pooled core so the id -> quantity walk crosses a pool
        result["record"]["verdicts"][0]["outcome"] = "abstained"
        result["record"]["verdicts"][0]["value"] = None
        with tempfile.TemporaryDirectory() as d:
            fat, thin = self._both_files(d, result)
            ma = B.measure(RIO.load_record(fat))
            mb = B.measure(RIO.load_record(thin))
        self.assertEqual(ma, mb)
        self.assertEqual(ma["unresolved_verdicts"], 1)

    @unittest.skipUnless(HAVE_IJSON, "record_slim streams with ijson")
    def test_record_slim_copies_pools_and_references_THROUGH(self):
        """`record_slim` rewrites observations and copies every other key
        verbatim, so a pooled record migrated by it still expands to the
        same verdicts."""
        from tools.omr.staged import record_slim as RS
        result = _arc_like_record()
        with tempfile.TemporaryDirectory() as d:
            _fat, thin = self._both_files(d, result)
            out = os.path.join(d, "slim.json")
            with redirect_stdout(io.StringIO()):
                RS.convert(thin, out)
            with open(out) as f:
                raw = json.load(f)
            self.assertIn(RIO.POOL_KEY, raw["record"])
            loaded = RIO.load_record(out)
        self.assertEqual(loaded["record"]["verdicts"],
                         result["record"]["verdicts"])


if __name__ == "__main__":
    unittest.main()
