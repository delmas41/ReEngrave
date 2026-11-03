"""Spy the ledger walk for given subjects: bands found, walk result, and what survives to the reader.
usage: POOL_JSON=... probe.py PLATE subject..."""
import sys
import importlib.util
import os

from tools.omr.annotate import ledger_grid as lg

spec = importlib.util.spec_from_file_location("reread", os.path.join(os.path.dirname(os.path.abspath(__file__)), "reread.py"))
RR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RR)

o_band, o_walk, o_meas = lg._band_centers, lg._walk_ladder, lg.measure_ledger_rungs


def band(ink, cx, sp, yoff, *a, **k):
    r = o_band(ink, cx, sp, yoff, *a, **k)
    print("   bands(yoff=%d,h=%d)" % (yoff, ink.shape[0]), [round(v, 1) for v in r])
    return r


def walk(edge, sign, bands, sp, target=None, tol=0.0):
    r = o_walk(edge, sign, bands, sp, target, tol)
    print("   walk edge %.1f sign %+d target %s ->" % (edge, sign, target), [round(v, 1) for v in r])
    return r


def meas(*a, **k):
    r = o_meas(*a, **k)
    print("   measure_ledger_rungs ->", {s: [round(v, 1) for v in r[s]] for s in r})
    return r


o_clear, o_coll = lg._rung_row_clears_box, lg.collapse_head_edge_rungs_to_middle


def clear(img, y, *a, **k):
    r = o_clear(img, y, *a, **k)
    print("   clears_box y=%.1f -> %s" % (y, r))
    return r


def coll(rungs, *a, **k):
    r = o_coll(rungs, *a, **k)
    print("   collapse", [round(v, 1) for v in rungs], "->", [round(v, 1) for v in r])
    return r


lg._band_centers, lg._walk_ladder, lg.measure_ledger_rungs = band, walk, meas
lg._rung_row_clears_box, lg.collapse_head_edge_rungs_to_middle = clear, coll
os.environ["LEDGER_TRACE"] = "1"
RR.main(sys.argv[1], "/dev/null", set(sys.argv[2:]))
