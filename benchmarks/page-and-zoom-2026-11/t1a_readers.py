"""ROADMAP 2.307 T1a -- copies of another staff's mark, and how many of them reach the 13 readers 2.306 r3 named (measure only).

    python3 benchmarks/page-and-zoom-2026-11/t1a_readers.py SLICES_DIR PLATE OUT.json

Replays ADJUDICATE..EXPORT on the saved gather slices exactly as `lane_report.run_arm --from adjudicate` does (flag OMR_PAGE_OWNED_VIEW
unset = today's behaviour), with every reader below wrapped by a counter. A COPY is a glyph whose standing `Q.GLYPH_OWNER` verdict is
DECIDED and names another staff (`owned_view.copy_keys_of_log`, EXPORT's own drop test), captured the moment ownership is decided.

What "receives a copy" means: on each call, every glyph key the reader is HANDED is collected -- the Evidence subject, Subject / key
arguments, dicts and objects carrying a `subject`/`sub`/`rg` field, and lists of those (two levels deep); a CELL subject counts the copies
filed under that cell (the reader lists its boxes itself). Reported per reader: calls, calls handed at least one copy, distinct copies
handed. Readers registered as ADJUDICATE decisions are wrapped in the REGISTRY; module-level helpers by module attribute (a helper called
through a name bound elsewhere would be missed -- a floor, not a ceiling). `rhythm` nested helpers `ownership.stem_of` / `both_ways` live
inside `adjudicate_articulation_owner` and are counted through it.
"""
import collections
import dataclasses
import functools
import json
import os
import sys
import time

READERS = [
    ("tools.omr.staged.adjudicators.stem_value", "adjudicate_stem_value", "decision"),
    ("tools.omr.staged.adjudicators.stem_value", "adjudicate_head_stem", "decision"),
    ("tools.omr.staged.adjudicators.unison_two", "adjudicate_unison_voices", "decision"),
    ("tools.omr.staged.adjudicators.rhythm", "_second_evidence", "helper"),
    ("tools.omr.staged.adjudicators.rhythm", "_flag_direction", "helper"),
    ("tools.omr.staged.adjudicators.rhythm", "_own_stem_side", "helper"),
    ("tools.omr.staged.adjudicators.rhythm", "_direction_from_a_beam_mate", "helper"),
    ("tools.omr.staged.adjudicators.ownership", "_long_chord_stem_tip", "helper"),
    ("tools.omr.staged.adjudicators.ownership", "adjudicate_articulation_owner", "decision"),   # holds stem_of / both_ways
    ("tools.omr.staged.consequences", "_on_one_stem", "helper"),
    ("tools.omr.staged.consequences", "_voice_count", "helper"),
    ("tools.omr.staged.export", "_stem_facts_of", "helper"),
    ("tools.omr.staged.export", "_settle_divisi_pairs", "helper"),
    ("tools.omr.staged.export", "_voice_split", "helper"),
    # the two 2.306 r3 already fixed (only under OMR_PAGE_STEMS, not on main): controls that DO receive copies today
    ("tools.omr.staged.adjudicators.rhythm", "adjudicate_event", "decision"),
    ("tools.omr.staged.adjudicators.rhythm", "adjudicate_voices", "decision"),
]

COPIES = set()
COPY_CELL = collections.defaultdict(set)      # cell key -> copy keys in it
STATS = collections.defaultdict(lambda: {"calls": 0, "calls_with_copy": 0, "copies": set()})


def _keys(x, depth=0, out=None):
    out = set() if out is None else out
    if depth > 2 or x is None:
        return out
    from tools.omr.staged.record import Subject
    if isinstance(x, Subject):
        out.add(x.to_key())
    elif isinstance(x, str):
        if x.startswith("glyph/") or x.startswith("cell/"):
            out.add(x)
    elif isinstance(x, dict):
        for k in ("subject", "sub", "rg", "glyph"):
            if k in x:
                _keys(x[k], depth + 1, out)
        if depth < 2:
            for v in x.values():
                if isinstance(v, (list, tuple)):
                    _keys(v, depth + 1, out)
    elif isinstance(x, (list, tuple, set, frozenset)):
        for v in list(x)[:400]:
            _keys(v, depth + 1, out)
    else:
        for k in ("subject", "sub"):
            v = getattr(x, k, None)
            if v is not None:
                _keys(v, depth + 1, out)
    return out


def _copies_in(keys):
    got = set()
    for k in keys:
        if k.startswith("glyph/"):
            if k in COPIES:
                got.add(k)
        elif k.startswith("cell/"):
            got |= COPY_CELL.get(k, set())
    return got


def wrap(name, fn):
    @functools.wraps(fn)
    def w(*a, **kw):
        st = STATS[name]
        st["calls"] += 1
        if COPIES:
            got = _copies_in(_keys(list(a) + list(kw.values())))
            if got:
                st["calls_with_copy"] += 1
                st["copies"] |= got
        return fn(*a, **kw)
    return w


def main():
    root, plate, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
    os.environ.pop("OMR_PAGE_OWNED_VIEW", None)
    import importlib
    from tools.omr.staged import adjudicate as A
    from tools.omr.staged import owned_view as OV
    A._ensure_decisions()
    for mod, fn, kind in READERS:
        m = importlib.import_module(mod)
        name = fn
        if kind == "decision":
            for q, spec in list(A.REGISTRY.items()):
                if getattr(spec.fn, "__name__", None) == fn:
                    A.REGISTRY[q] = dataclasses.replace(spec, fn=wrap(name, spec.fn))
        else:
            setattr(m, fn, wrap(name, getattr(m, fn)))

    real_apply = OV.apply_to_log

    def capture(log):
        COPIES.clear()
        COPIES.update(OV.copy_keys_of_log(log))
        for k in COPIES:
            COPY_CELL["cell/" + "/".join(k.split("/")[1:5])].add(k)
        return real_apply(log)
    OV.apply_to_log = capture

    from tools.omr.staged import lane_report as LR
    from tools.omr.staged.review import rerun as RR
    from tools.omr.staged import export as E
    t0 = time.time()
    rec = LR.load_slices(LR.slice_dir(plate, root))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    # copies by family, and how EXPORT dropped them
    box = {}
    for o in result["record"]["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"] in COPIES:
            box[o["subject"]] = o["value"][0]
    sys.path.insert(0, os.path.dirname(__file__))
    from t1b_clipped import family
    count_pages = {"litolff": {5, 8, 13, 15}, "brahms": {0, 11, 18, 20}}[plate]
    fam = collections.Counter(family(box.get(k, "?")) for k in COPIES if int(k.split("/")[1]) in count_pages)
    xml, report = E.to_musicxml(result)
    out = dict(plate=plate, seconds=round(time.time() - t0, 1), copies_total=sum(fam.values()), copies_by_family=dict(fam),
               red_bars=report.get("bars_written_red"), readers={})
    for mod, fn, kind in READERS:
        st = STATS[fn]
        cps = [k for k in st["copies"] if int(k.split("/")[1]) in count_pages]
        out["readers"][fn] = dict(kind=kind, calls=st["calls"], calls_with_copy=st["calls_with_copy"], copies=len(cps),
                                  copies_by_family=dict(collections.Counter(family(box.get(k, "?")) for k in cps)))
    json.dump(out, open(outp, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "red_bars"}, indent=1, default=str))


if __name__ == "__main__":
    main()
