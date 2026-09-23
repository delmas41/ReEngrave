"""Rewrite an EXISTING staged record's `Q.INK` rows into the summary form.

Roadmap 1.1 prep. `gather_ink` now emits the aggregate by default (one
`Q.INK` row per cell, see `gather.py`); this module is the migration path
for a record that was gathered BEFORE that change and still carries one row
per ink COMPONENT — the two committed shared records under
`library/_shared-records/` are the motivating case, at 146 MB and 461 MB.

    python3 -m tools.omr.staged.record_slim in.record.json out.record.json

⚠️⚠️ **DOES NOT NEED `json.load` ON EITHER SIDE.** `record.observations`,
`.abstentions` and `.verdicts` are streamed item by item with `ijson`
(a soft dependency, imported lazily -- `pip install ijson` if it is
missing) so peak memory is bounded by the size of ONE row plus the running
per-cell ink aggregate (a few thousand small dicts, not the component
population). The output is written incrementally too. Every VALUE outside
`Q.INK` observations -- `abstentions`, `verdicts`, and the six small
sibling keys (`adjudication`, `agreement`, `evaluation`, `provenance`,
`stubs`, `summary`) -- is unchanged.

⚠️⚠️ **THE OUTPUT IS COMPACT JSON, NOT `indent=2`, AND THAT IS A SECOND,
LARGER, UNRELATED EFFECT THIS TOOL'S OWN MEASURED NUMBERS CONFLATE WITH THE
INK CHANGE -- READ THIS BEFORE QUOTING A BEFORE/AFTER SIZE.** `__main__.py`
writes every staged record with `json.dumps(result, indent=2, ...)`. A
short, flat row -- one `Q.INK` component, or one entry of `arc_owner`'s
`considered` array -- costs proportionally MORE under `indent=2` than a
deeply-nested one, because every leaf value gets its own line: one real ink
row measured 924 bytes pretty-printed against ~540 bytes compact, a 1.7x
ratio, and `arc_owner`'s `considered` arrays (thousands of short id strings,
one per line under `indent=2`) pay the same tax at far greater scale.
**Measured, isolating each effect** (`benchmarks/omr-ink-gather-2026-09/
probe/byte_share.py`, before vs after, in COMPACT terms both times so
format cannot confound it): the ink schema change alone saves **3.4 MB
(4.4%) on Beethoven and 8.1 MB (3.3%) on Breitkopf** -- consistent with
`Q.INK` being 3.5-4.9% of a record's compact content. Running THIS TOOL
end to end, which also switches the whole file to compact JSON, measures
**146.4->75.0 MB (48.7%) and 461.1->237.3 MB (48.5%)** -- true, reproducible,
but the large majority of that reduction is the FORMAT change, not the ink
one. Whoever next touches record serialisation format should read this as
the finding it is: switching every staged record to compact JSON is a
much bigger, much lower-risk lever than either the ink summary or fixing
`arc_owner`, at the cost of `positional_store.stream_observations`'s
fragile `indent=2`-dependent line reader needing a rewrite first.

⚠️ **`arc_owner` verdicts' `considered` lists are 57-75% of a record's
compact content (unrelated to ink, reported here so nobody re-measures it
by surprise) and this tool does NOT touch them** -- out of scope for
roadmap 1.1's ink-summary item, and `record_slim`'s own compact-format
side effect is what happens to shrink them anyway on the way through.

⚠️ **VERIFIED, NOT ASSUMED, THAT SLIMMING INK IS SAFE ON THE TWO COMMITTED
RECORDS**: neither file has a single verdict whose `basis` / `considered` /
`used` / `declined` / `excluded` list names an ink observation id (checked
by building the full id set and scanning every verdict on both files -- 0
of 0 on 7,093 and 15,212 ink rows respectively). `Q.INK` ships with no
consumer by design (see `gather.py`'s own docstring), so this is expected
rather than lucky, but a THIRD record could differ -- this tool does not
check it for you, because doing so needs the same two full passes the
conversion already makes and is cheap to add if it is ever needed. A
dangling reference from a slimmed id would not raise; it would look like a
completed evidence trail pointing at nothing.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Iterator, Tuple

#: Mirrors `trace._cell_of` / `record.Subject.at(Kind.CELL)`: a glyph or cell
#: subject's cell identity is its first FOUR positional components, never the
#: fifth (glyph ordinal). Reimplemented here, not imported, so this module
#: has no dependency on `record.py`'s class machinery -- it only ever needs
#: string keys.
def _cell_of(key: str):
    parts = key.split("/")
    if parts and parts[0] in ("cell", "glyph") and len(parts) >= 5:
        return "cell/" + "/".join(parts[1:5])
    return None


class _Events:
    """One-token lookahead over an `ijson.parse` event stream."""

    def __init__(self, gen) -> None:
        self._gen = gen
        self._buf: Any = None
        self._has_buf = False

    def next(self) -> Tuple[str, str, Any]:
        if self._has_buf:
            self._has_buf = False
            t, self._buf = self._buf, None
            return t
        return next(self._gen)

    def peek(self) -> Tuple[str, str, Any]:
        if not self._has_buf:
            self._buf = next(self._gen)
            self._has_buf = True
        return self._buf


def _build_value(ev: _Events) -> Any:
    """Rebuild ONE JSON value (of any shape) from the event stream.

    A small, general recursive-descent reader over `ijson.parse`'s flat
    event stream -- used for the six small sibling top-level keys and for
    each individual row of `abstentions` / `verdicts`, never for a whole
    array at once.
    """
    prefix, event, value = ev.next()
    if event == "start_map":
        d: Dict[str, Any] = {}
        while True:
            prefix, event, value = ev.next()
            if event == "end_map":
                return d
            # `value` here is the MAP KEY (ijson's own convention).
            d[value] = _build_value(ev)
    if event == "start_array":
        arr = []
        while True:
            if ev.peek()[1] == "end_array":
                ev.next()
                return arr
            arr.append(_build_value(ev))
    return value


def _copy_array(ev: _Events, fout) -> None:
    """Stream an array through unchanged, one item at a time."""
    prefix, event, value = ev.next()
    assert event == "start_array", (prefix, event)
    fout.write("[")
    first = True
    while True:
        if ev.peek()[1] == "end_array":
            ev.next()
            break
        if not first:
            fout.write(",")
        first = False
        item = _build_value(ev)
        fout.write(json.dumps(item, separators=(",", ":"), default=str))
    fout.write("]")


def _copy_map(ev: _Events, fout) -> None:
    """Stream a map through unchanged, one VALUE at a time -- so a sibling
    key holding a big array (`record.verdicts`, seen at 183 MB proxy on the
    Breitkopf record) is never asked to fit in memory as one Python object,
    only its individual entries are."""
    prefix, event, value = ev.next()
    assert event == "start_map", (prefix, event)
    fout.write("{")
    first = True
    while True:
        prefix, event, value = ev.next()
        if event == "end_map":
            break
        assert event == "map_key", (prefix, event, value)
        if not first:
            fout.write(",")
        first = False
        fout.write(json.dumps(value) + ":")
        _copy_value(ev, fout)
    fout.write("}")


def _copy_value(ev: _Events, fout) -> None:
    """Stream ANY JSON value through unchanged, dispatching on its shape.

    `record`'s own keys are NOT always arrays -- `counts` is a map -- so the
    caller cannot assume `_copy_array` and this general form is what both
    `convert()`'s top level and `_convert_record` use for every sibling
    that is not `observations`.
    """
    nxt = ev.peek()
    if nxt[1] == "start_array":
        _copy_array(ev, fout)
    elif nxt[1] == "start_map":
        _copy_map(ev, fout)
    else:
        fout.write(json.dumps(_build_value(ev), separators=(",", ":"),
                              default=str))


def _empty_ink_agg() -> Dict[str, Any]:
    return {"n": 0, "total_area_px": 0, "largest_area_px": 0,
            "coverage_max": 0.0, "explained_by": set(),
            "cell_staff_space_px": None}


def _accumulate_ink(item: Dict[str, Any], agg_by_cell: Dict[str, Dict],
                    stats: Dict[str, int]) -> None:
    c = _cell_of(item.get("subject", ""))
    if c is None:
        stats["unattributable"] = stats.get("unattributable", 0) + 1
        return
    d = item.get("detail") or {}
    agg = agg_by_cell.setdefault(c, _empty_ink_agg())
    agg["n"] += 1
    agg["total_area_px"] += int(d.get("ink_area_px") or 0)
    agg["largest_area_px"] = max(agg["largest_area_px"],
                                  int(d.get("ink_area_px") or 0))
    agg["coverage_max"] = max(agg["coverage_max"],
                              float(d.get("ink_detector_coverage") or 0.0))
    agg["explained_by"].update(d.get("ink_explained_by") or ())
    if agg["cell_staff_space_px"] is None and "cell_staff_space_px" in d:
        agg["cell_staff_space_px"] = d["cell_staff_space_px"]
    # Sanity cross-check, not load-bearing: every component row of one cell
    # already carries that cell's total under the pre-1.1 schema, so if it
    # ever disagrees within a cell the source file is not what this module
    # assumes it is.
    n_declared = d.get("ink_n_components")
    if isinstance(n_declared, int):
        prev = agg.get("_declared_n")
        if prev is not None and prev != n_declared:
            stats["n_components_disagreed"] = \
                stats.get("n_components_disagreed", 0) + 1
        agg["_declared_n"] = n_declared


def _finalize_ink_row(cell_key: str, agg: Dict[str, Any],
                      next_id: int) -> Dict[str, Any]:
    total = agg["total_area_px"] or 1
    detail: Dict[str, Any] = {
        "ink_n_components": agg["n"],
        "ink_total_area_px": agg["total_area_px"],
        "ink_largest_share": round(agg["largest_area_px"] / total, 4),
        "ink_detector_coverage_max": round(agg["coverage_max"], 4),
        "ink_explained_by_union": sorted(agg["explained_by"]),
    }
    if agg["cell_staff_space_px"] is not None:
        detail["cell_staff_space_px"] = agg["cell_staff_space_px"]
    parts = cell_key.split("/")
    subject = "/".join(["glyph"] + parts[1:])  # cell subject, no ordinal
    return {
        "id": f"obs:slim{next_id:06d}",
        "subject": subject,
        "quantity": "ink",
        "value": "ink",
        "reader": "cv_ink",
        "frame": f"cell:{parts[4]}" if len(parts) > 4 else "cell",
        "score": None,
        "detail": detail,
        "basis": [],
    }


def _convert_observations(ev: _Events, fout, stats: Dict[str, int]) -> None:
    prefix, event, value = ev.next()
    assert event == "start_array", (prefix, event)
    fout.write("[")
    first = True
    agg_by_cell: Dict[str, Dict[str, Any]] = {}
    n_in = n_ink_in = 0
    while True:
        if ev.peek()[1] == "end_array":
            ev.next()
            break
        item = _build_value(ev)
        n_in += 1
        if item.get("quantity") == "ink":
            n_ink_in += 1
            _accumulate_ink(item, agg_by_cell, stats)
            continue
        if not first:
            fout.write(",")
        first = False
        fout.write(json.dumps(item, separators=(",", ":"), default=str))
    for i, (cell_key, agg) in enumerate(agg_by_cell.items()):
        if not first:
            fout.write(",")
        first = False
        fout.write(json.dumps(_finalize_ink_row(cell_key, agg, i),
                              separators=(",", ":"), default=str))
    fout.write("]")
    stats["observations_in"] = n_in
    stats["ink_observations_in"] = n_ink_in
    stats["ink_cells_out"] = len(agg_by_cell)


def _convert_record(ev: _Events, fout, stats: Dict[str, int]) -> None:
    prefix, event, value = ev.next()
    assert event == "start_map", (prefix, event)
    fout.write("{")
    first = True
    while True:
        prefix, event, value = ev.next()
        if event == "end_map":
            break
        assert event == "map_key", (prefix, event, value)
        key = value
        if not first:
            fout.write(",")
        first = False
        fout.write(json.dumps(key) + ":")
        if key == "observations":
            _convert_observations(ev, fout, stats)
        else:
            _copy_value(ev, fout)
    fout.write("}")


def convert(in_path: str, out_path: str) -> Dict[str, int]:
    """Stream `in_path` to `out_path`, slimming `record.observations`'
    `Q.INK` rows to one aggregate per cell. Returns a small stats dict."""
    try:
        import ijson
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ImportError(
            "record_slim needs `ijson` to stream a large record without "
            "loading it whole (`python3 -m pip install --user ijson`). "
            f"underlying error: {exc}") from exc

    stats: Dict[str, int] = {}
    with open(in_path, "rb") as fin, open(out_path, "w") as fout:
        # ⚠️ `use_float=True`, OR EVERY NUMBER SILENTLY BECOMES A STRING.
        # ijson parses JSON numbers as `decimal.Decimal` by default; `Decimal`
        # is not one of `json.dumps`'s native types, so it falls through to
        # this module's `default=str` on every re-encode -- caught by the
        # self-test round-tripping `0.9`, `1.0` and `100.0` and finding them
        # back as `"0.9"`, `"1.0"`, `"100.0"`.
        ev = _Events(ijson.parse(fin, use_float=True))
        prefix, event, value = ev.next()
        assert event == "start_map", "not a staged record: no root object"
        fout.write("{")
        first = True
        while True:
            prefix, event, value = ev.next()
            if event == "end_map":
                break
            assert event == "map_key", (prefix, event, value)
            key = value
            if not first:
                fout.write(",")
            first = False
            fout.write(json.dumps(key) + ":")
            if key == "record":
                _convert_record(ev, fout, stats)
            else:
                _copy_value(ev, fout)
        fout.write("}")
    stats["in_bytes"] = os.path.getsize(in_path)
    stats["out_bytes"] = os.path.getsize(out_path)
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record_in")
    ap.add_argument("record_out")
    args = ap.parse_args(argv)
    stats = convert(args.record_in, args.record_out)
    print(f"{args.record_in} -> {args.record_out}")
    print(f"  in:  {stats['in_bytes'] / 1e6:.1f} MB")
    print(f"  out: {stats['out_bytes'] / 1e6:.1f} MB "
          f"({stats['out_bytes'] / stats['in_bytes'] * 100:.1f}% of input)")
    print(f"  observations: {stats['observations_in']} in "
          f"({stats['ink_observations_in']} ink) -> "
          f"{stats['ink_cells_out']} ink summary rows")
    for k in ("unattributable", "n_components_disagreed"):
        if stats.get(k):
            print(f"  ⚠️ {k}: {stats[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
