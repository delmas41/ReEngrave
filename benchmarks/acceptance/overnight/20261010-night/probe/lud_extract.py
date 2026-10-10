#!/usr/bin/env python3
"""lud_extract: ONE read of a record, everything the undecided-bars write-up
needs, into a small JSON.

TWO READERS, ONE OUTPUT, AND A CONTROL BETWEEN THEM.

  default   `readout.load_run` = `record_io.load_record` + indexing: the one
            sanctioned way to read a record file. Measured on Litolff
            (813 MB file): 5.4 GB peak resident, i.e. 6.6x the file.
  --stream  `ijson` over the file, keeping only the UNPOOLED fields it needs.
            Added because the 5.3 GB Brahms record would need ~35 GB resident
            while the machine had 10.6 of 12.3 GB swap used and 11 GB of disk
            free, and two other lanes' gathers were running. It never touches
            `basis`/`considered`/`correlated` (the only pooled fields, see
            record_io), so the pooled-list hazard record_io warns of does not
            arise. Its output is bit-compared with the default reader's on
            Litolff (`--no-basis` drops the basis-derived fields from both) --
            run that comparison before trusting a --stream result.

`adjudicate_status` is readout's own function, fed through a shim that gives it
the same `verdicts_at(key, "ADJUDICATE")` the real Run gives, so the status
words are the diff's own.

Writes
  prov          dpi, pdf, commit, dirty
  bar_totals    "page/system/cell" -> {status: n} over the staves (notes only)
  cell_totals   "page/system/staff/cell" -> {status: n}
  dur           note key -> tonight's (or last night's, --side a) ADJUDICATE
                Q.DURATION verdict summary, for every note whose status is
                narrowed or that the diff lists as kept<->narrowed
  boxes         note + clef glyph boxes in PAGE px: key -> [cls, x0,y0,x1,y1]
  staves        "staff/p/s/st" -> {ys, ext}      cells  "cell/p/s/st/c" -> box
"""
import argparse
import collections
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout            # noqa: E402  (read-only use)
from tools.omr.staged.record import Q           # noqa: E402

DETAIL_KEEP_LIST_LEN = 12


def compact_detail(d):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, (list, tuple)) and len(v) > DETAIL_KEEP_LIST_LEN:
            out[k] = f"<list {len(v)}>"
        elif isinstance(v, dict) and len(json.dumps(v, default=str)) > 400:
            out[k] = f"<dict {len(v)}>"
        else:
            out[k] = v
    return out


def cand_brief(c):
    v = c.get("value") if isinstance(c, dict) else c
    if isinstance(v, dict):
        return {k: v.get(k) for k in ("beats", "written", "dots", "beam_levels")}
    return v


class Shim:
    """Just enough of `readout.Run` for `adjudicate_status`."""

    def __init__(self, by_subject):
        self.by_subject = by_subject

    def verdicts_at(self, key, stage=None, quantity=None):
        return [v for s, v in self.by_subject.get(key, [])
                if (stage is None or s == stage) and (quantity is None or v["quantity"] == quantity)]


class View:
    """glyphs, ADJUDICATE verdicts per note subject, first obs of three quantities, provenance."""
    glyphs = None
    run = None          # something with .verdicts_at
    first_obs = None    # {(key, quantity): value}
    dpi = pdf = commit = dirty = None
    basis_fn = None     # verdict -> (reach?, quantities Counter) or None


def view_loaded(path):
    run = readout.load_run(path)
    print(f"loaded + indexed: {len(run.glyphs)} glyphs, {len(run.verdicts)} verdicts, "
          f"{len(run.observations)} observations", flush=True)
    v = View()
    v.glyphs = run.glyphs
    v.run = run
    v.first_obs = {}
    for key in run.by_subject:
        if key.startswith("staff/"):
            for q in (Q.STAFF_LINES, Q.STAFF_EXTENT):
                r = run.obs_at(key, q)
                if r:
                    v.first_obs[(key, q)] = r[0]["value"]
        elif key.startswith("cell/"):
            r = run.obs_at(key, Q.CELL_BOX)
            if r:
                v.first_obs[(key, Q.CELL_BOX)] = r[0]["value"]
    v.dpi, v.pdf = run.dpi, run.pdf
    v.commit, v.dirty = run.provenance.get("commit"), run.provenance.get("dirty")
    reach_ids = {o["id"] for o in run.observations if o["quantity"] == Q.HEAD_STEM_REACH}

    def basis_fn(vd):
        reach = False
        qs = collections.Counter()
        for bid in (vd.get("basis") or []):
            if bid in reach_ids:
                reach = True
            bv = run.verdict_by_id(bid)
            if bv is not None:
                qs[bv["quantity"]] += 1
        return len(vd.get("basis") or []), reach, dict(qs)

    v.basis_fn = basis_fn
    return v


def view_stream(path, want_dur_for=None):
    import ijson
    t0 = time.time()
    glyphs = {}
    first = {}
    n_obs = 0
    with open(path, "rb") as fh:
        for o in ijson.items(fh, "record.observations.item", use_float=True):
            n_obs += 1
            q = o["quantity"]
            if q == Q.GLYPH_BOX:
                if readout._GLYPH_KEY.match(o["subject"]):
                    if o["subject"] not in glyphs:
                        glyphs[o["subject"]] = readout._glyph_from_box(o["subject"], o)
            elif q in (Q.STAFF_LINES, Q.STAFF_EXTENT, Q.CELL_BOX):
                k = (o["subject"], q)
                if k not in first and (o["subject"].startswith("staff/") or o["subject"].startswith("cell/")):
                    first[k] = o["value"]
    print(f"stream pass 1 (observations): {n_obs} rows, {len(glyphs)} glyphs, {time.time() - t0:.0f}s", flush=True)
    note_keys = {k for k, g in glyphs.items() if g.family == "note"}
    by_subject = collections.defaultdict(list)
    n_v = 0
    with open(path, "rb") as fh:
        for vd in ijson.items(fh, "record.verdicts.item", use_float=True):
            n_v += 1
            sub = vd["subject"]
            if sub not in note_keys:
                continue
            st = readout.stage_of(vd["decider"])
            if st != "ADJUDICATE":
                continue
            slim = {k: vd.get(k) for k in ("id", "subject", "quantity", "decider", "outcome", "reason", "value")}
            if vd["quantity"] == Q.DURATION:
                slim["candidates"] = vd.get("candidates")
                slim["detail"] = vd.get("detail")
            by_subject[sub].append((st, slim))
    print(f"stream pass 2 (verdicts): {n_v} rows, {len(by_subject)} note subjects with ADJUDICATE rows, "
          f"{time.time() - t0:.0f}s", flush=True)
    prov = None
    with open(path, "rb") as fh:
        for p in ijson.items(fh, "provenance", use_float=True):
            prov = p
    prov = prov or {}
    args = ((prov.get("settings") or {}).get("args") or {})
    v = View()
    v.glyphs = glyphs
    v.run = Shim(by_subject)
    v.first_obs = first
    v.dpi = int(args["dpi"]) if args.get("dpi") else None
    v.pdf = args.get("pdf")
    v.commit, v.dirty = prov.get("commit"), prov.get("dirty")
    v.basis_fn = None
    print(f"stream done {time.time() - t0:.0f}s", flush=True)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--diff", required=True, help="the saved first-two-stages diff JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stream", action="store_true", help="ijson reader (see module docstring)")
    ap.add_argument("--no-basis", action="store_true", help="omit basis-derived fields (for the stream control)")
    ap.add_argument("--dur-only", action="store_true",
                    help="only the duration verdict detail of the diff's changed notes")
    ap.add_argument("--side", choices=("a", "b"), default="b",
                    help="which side of the diff's changed pairs names these notes (a=last night, b=tonight)")
    a = ap.parse_args()

    diff = json.load(open(a.diff))
    changed = set()
    for p in diff["changed_pairs"]:
        if p["family"] == "note" and tuple(p["status"]) in (("kept", "narrowed"), ("narrowed", "kept")):
            changed.add(p[a.side])
    print(f"changed note subjects wanted: {len(changed)}", flush=True)
    del diff

    t0 = time.time()
    view = view_stream(a.record) if a.stream else view_loaded(a.record)
    use_basis = view.basis_fn is not None and not a.no_basis

    out = {"prov": {"dpi": view.dpi, "pdf": view.pdf, "record": a.record,
                    "commit": view.commit, "dirty": view.dirty, "reader": "stream" if a.stream else "load_record"},
           "bar_totals": {}, "cell_totals": {}, "dur": {}, "boxes": {}, "staves": {}, "cells": {}}
    bar_tot = collections.defaultdict(collections.Counter)
    cell_tot = collections.defaultdict(collections.Counter)
    n_notes = 0
    for key, g in view.glyphs.items():
        if a.dur_only and key not in changed:
            continue
        if g.family == "clef":
            if g.box_page:
                out["boxes"][key] = [g.cls, *[round(x, 1) for x in g.box_page]]
            continue
        if g.family != "note":
            continue
        n_notes += 1
        status, _why = readout.adjudicate_status(view.run, g)
        bar_tot[f"{g.page}/{g.system}/{g.cell}"][status] += 1
        cell_tot[f"{g.page}/{g.system}/{g.staff}/{g.cell}"][status] += 1
        if g.box_page:
            out["boxes"][key] = [g.cls, *[round(x, 1) for x in g.box_page]]
        if status == "narrowed" or key in changed:
            vs = view.run.verdicts_at(key, "ADJUDICATE", Q.DURATION)
            v = vs[-1] if vs else None
            if v is None:
                out["dur"][key] = {"status": status, "none": True}
                continue
            row = {
                "status": status, "outcome": v.get("outcome"), "reason": v.get("reason"),
                "decider": v.get("decider"),
                "value": cand_brief({"value": v.get("value")}) if v.get("value") is not None else None,
                "candidates": [cand_brief(c) for c in (v.get("candidates") or [])],
                "detail": compact_detail(v.get("detail")),
            }
            if use_basis:
                bn, reach, qs = view.basis_fn(v)
                row.update({"basis_n": bn, "basis_has_head_stem_reach": reach, "basis_quantities": qs})
            out["dur"][key] = row
    out["bar_totals"] = {k: dict(v) for k, v in bar_tot.items()}
    out["cell_totals"] = {k: dict(v) for k, v in cell_tot.items()}
    print(f"notes {n_notes}; dur rows {len(out['dur'])}", flush=True)

    if not a.dur_only:
        for (key, q), val in view.first_obs.items():
            if q == Q.STAFF_LINES:
                ext = view.first_obs.get((key, Q.STAFF_EXTENT))
                out["staves"][key] = {"ys": [float(y) for y in val],
                                      "ext": [float(x) for x in ext] if ext else None}
            elif q == Q.CELL_BOX:
                out["cells"][key] = [float(x) for x in val]
        print(f"staves {len(out['staves'])}, cells {len(out['cells'])}, boxes {len(out['boxes'])}", flush=True)

    # canonical order so two readers' files compare byte for byte
    def canon(o):
        if isinstance(o, dict):
            return {k: canon(o[k]) for k in sorted(o)}
        if isinstance(o, list):
            return [canon(x) for x in o]
        return o
    Path(a.out).write_text(json.dumps(canon(out), separators=(",", ":"), default=str))
    print(f"wrote {a.out} ({Path(a.out).stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
