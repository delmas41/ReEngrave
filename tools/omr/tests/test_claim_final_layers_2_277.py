"""ROADMAP 2.277 -- ANY claim layer is consumed, whatever its owner and unit (no hand list): a DUMMY layer filed as `page_ink` must refuse the box standing on its ink
`claimed_by:page_claim`; the derived check must FIND a layer no consumer reads. Every control can fail."""
from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import types
import unittest
from unittest import mock

from tools.omr.staged import claim_final as CF
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.adjudicators import claim_final as ACF
from tools.omr.staged.adjudicators import stroke_owner as ASO
from tools.omr.staged.record import Q

SP = 16.0


def _ink(o, box, kind="horizontal"):
    return SO.Ink(o, kind, tuple(float(v) for v in box), 2.0, 0.4, 0.8, SP)


class _Row:
    def __init__(self, rid, owner, unit, value, **detail):
        self.id, self.value = rid, value
        self.detail = dict(owner=owner, unit=unit, standing="READ", **detail)
        self.subject = types.SimpleNamespace(to_key=lambda: "page/1")


class _Ev:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, q, scope=None, subject=None):
        return [r for r in self._rows if q == Q.CLAIMED_AREA]


def _pipeline(rows, boxes):
    """strokes: 0 = a slash-sized stroke at (100,100)-(140,112); 1 = a head blob far away. Returns the claim_final detail for the head box over stroke `which`."""
    inks = [_ink(0, (100, 100, 40, 12)), _ink(1, (300, 100, 20, 16), "blob")]
    page = {0: (100.0, 100.0, 140.0, 112.0), 1: (300.0, 100.0, 320.0, 116.0)}
    with mock.patch.dict(os.environ, {CF.ENV: "1"}):
        layer = ASO._layer_claims(_Ev(rows), object(), page)
        claims = list(layer)
        for key, ords in boxes.items():
            claims.append(SO.Claim(key, "head", "noteheadBlack", tuple(ords), (), "obs:" + key))
        tiers = ((tuple(SO.TIERS[0]) + tuple(sorted({c.family for c in layer})),) + tuple(SO.TIERS[1:])) if layer else SO.TIERS
        owned = SO.own_strokes(inks, claims, tiers=tiers)
        by_ord = {i.ordinal: i for i in inks}
        ev = types.SimpleNamespace(rows=lambda q, scope=None, subject=None: [
            types.SimpleNamespace(value=list(ords), detail={"shares": [1.0] * len(ords)}, subject=types.SimpleNamespace(to_key=lambda k=key: k))
            for key, ords in boxes.items()] if q == Q.GLYPH_STROKES else [])
        return layer, ASO._claim_final(ev, object(), claims, owned, by_ord)


class TestAnyLayerIsConsumed(unittest.TestCase):
    def test_a_page_ink_layer_of_a_dummy_owner_holds_the_box_on_its_ink_and_refuses_it(self):
        row = _Row("obs:1", "dummy_layer", "page_ink", [], area=[98.0, 98.0, 142.0, 114.0])
        layer, cf = _pipeline([row], {"glyph/1/0/0/0/7": [0], "glyph/1/0/0/0/8": [1]})
        self.assertEqual([c.family for c in layer], ["dummy_layer"])
        held = cf["held"]["glyph/1/0/0/0/7"]
        self.assertEqual((held["by"], held["share"]), ("dummy_layer", 1.0))
        self.assertNotIn("glyph/1/0/0/0/8", cf["held"])                                   # CONTROL: the head blob away from the layer is untouched
        v = types.SimpleNamespace(id="vrd:9", detail={"claim_final": cf, "box_owns": []})
        ev = types.SimpleNamespace(subject=types.SimpleNamespace(at=lambda k: object(), to_key=lambda: "glyph/1/0/0/0/7"), verdict=lambda q, subject=None: v)
        with mock.patch.dict(os.environ, {CF.ENV: "1"}):
            f = ACF.finding(ev, types.SimpleNamespace(id="obs:7"))
        self.assertEqual((f.kind, f.by), ("page_claim", "dummy_layer"))                    # refused BY THE CLAIM, no code for this owner

    def test_the_unit_does_not_matter(self):
        for unit in ("area", "page_ink", "something_new"):
            row = _Row("obs:1", "dummy_layer", unit, [], area=[98.0, 98.0, 142.0, 114.0])
            layer, _ = _pipeline([row], {"glyph/1/0/0/0/7": [0]})
            self.assertEqual(len(layer), 1, unit)

    def test_a_value_that_is_a_rectangle_is_read_too(self):
        row = _Row("obs:1", "dummy_layer", "area", [98.0, 98.0, 142.0, 114.0])
        layer, _ = _pipeline([row], {"glyph/1/0/0/0/7": [0]})
        self.assertEqual(len(layer), 1)

    def test_CONTROL_no_row_no_claim_and_nothing_is_refused(self):
        layer, cf = _pipeline([], {"glyph/1/0/0/0/7": [0]})
        self.assertEqual(layer, [])
        self.assertEqual(cf["held"], {})

    def test_CONTROL_a_stroke_only_partly_inside_the_layer_is_not_taken(self):
        row = _Row("obs:1", "dummy_layer", "page_ink", [], area=[100.0, 100.0, 120.0, 112.0])      # half the slash stroke
        layer, _ = _pipeline([row], {"glyph/1/0/0/0/7": [0]})
        self.assertEqual(layer, [])

    def test_CONTROL_the_owners_with_their_own_path_are_not_taken_twice(self):
        for owner in ("barline", "arc", "head"):
            row = _Row("obs:1", owner, "page_ink", [], area=[98.0, 98.0, 142.0, 114.0])
            layer, _ = _pipeline([row], {"glyph/1/0/0/0/7": [0]})
            self.assertEqual(layer, [], owner)

    def test_CONTROL_flag_off_files_nothing(self):
        row = _Row("obs:1", "dummy_layer", "page_ink", [], area=[98.0, 98.0, 142.0, 114.0])
        with mock.patch.dict(os.environ, {CF.ENV: "0"}):
            self.assertEqual(ASO._layer_claims(_Ev([row]), object(), {0: (100.0, 100.0, 140.0, 112.0)}), [])

    def test_a_not_READ_layer_is_not_taken(self):
        row = _Row("obs:1", "dummy_layer", "page_ink", [], area=[98.0, 98.0, 142.0, 114.0])
        row.detail["standing"] = "GUESSED"
        layer, _ = _pipeline([row], {"glyph/1/0/0/0/7": [0]})
        self.assertEqual(layer, [])


class TestTheCheckFindsALayerNoOneReads(unittest.TestCase):
    STAGED = pathlib.Path(CF.__file__).resolve().parent

    def _tree(self, d, generic: bool, layer: bool):
        """A small SYNTHETIC staged/ tree: the few files the check reads, hand-written (no real source is read here)."""
        root = pathlib.Path(d) / "staged"
        (root / "adjudicators").mkdir(parents=True)
        (root / "stroke_owner.py").write_text('TIERS = (\n    ("clef", "barline"),\n    ("head",),\n    ("rest",),\n)\nCONSUMERS = ("stem",)\n')
        layers = ('    ("barline_bracket", ("barline",), "x"),\n' + ('    ("dummy_layer", ("dummy_layer",), "test"),\n' if layer else "")
                  + '    ("head", ("head",), "x"),\n')
        (root / "claim_order.py").write_text("LAYERS: tuple = (\n" + layers + ")\n")
        (root / "claim_final.py").write_text('MARK_ONLY = frozenset({"arc_trace"})\n')
        (root / "adjudicators" / "claimed_by.py").write_text("_ORDER = (_claims.OWNER_CLEF,)\n")
        (root / "adjudicators" / "stroke_owner.py").write_text("x = _layer_claims(ev)\n" if generic else "x = 1\n")
        for rel in CF.CONSUMER_DECIDERS.values():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("cf = _claim_final.finding(ev)\n")
        return root

    def test_a_layer_in_claim_order_with_no_generic_reader_is_a_finding(self):
        with tempfile.TemporaryDirectory() as d:
            f = CF.static_wiring(self._tree(d, generic=False, layer=True))
            self.assertIn(("dummy_layer", "stroke_owner"), {(x["claim"], x["reader"]) for x in f})

    def test_CONTROL_the_same_layer_is_no_finding_where_the_stroke_owner_reads_any_layer(self):
        with tempfile.TemporaryDirectory() as d:
            f = CF.static_wiring(self._tree(d, generic=True, layer=True))
            self.assertNotIn("dummy_layer", {x["claim"] for x in f})

    def test_CONTROL_this_tree_has_no_unread_layer(self):
        self.assertFalse([x for x in CF.static_wiring() if x["reader"] == "stroke_owner"])


if __name__ == "__main__":
    unittest.main()
