"""ROADMAP 2.153 -- replay a SLICE of a record faithfully.

`review.rerun.rebuild_gather` gives every row a dense NEW id and remaps only `basis`. A WHOLE record's GATHER rows are already
dense, so the map is the identity and that is enough; a SLICE (named systems) has sparse ids, so every id a row's `detail`
carries (`stem_row_id`, `beam_row_id` ...) points at a row that no longer has that id, and the readers that match on them
(`_stem_tip_flag_ink`, `_beam_join_witness`) read nothing: a silent difference from the saved verdicts (found on Litolff
`glyph/13/0/2/3/0`: stored `hooks_counted`, a slice replay on the SAME code `head_and_marks`).
This builds the log twice: pass 1 yields the id map; pass 2 rebuilds with every id string inside `detail` remapped.
CONTROL: `python3 replay_util_2_153.py SLICE.json` re-decides at the current tree and compares the FIRST `adjudicate_duration`
verdict of every glyph (the reader, not the EVALUATE/INFER consequences that need other systems for the meter) with the
record's own stored one: counts the glyphs that differ.
"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record import Log, Subject  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402


def _remap(x, m):
    if isinstance(x, str):
        return m.get(x, x)
    if isinstance(x, list):
        return [_remap(i, m) for i in x]
    if isinstance(x, tuple):
        return tuple(_remap(i, m) for i in x)
    if isinstance(x, dict):
        return {k: _remap(v, m) for k, v in x.items()}
    return x


def rebuild(rec):
    _, id_map = RR.rebuild_gather(rec)
    log = Log()
    rows = [(r, "obs") for r in rec.get("observations") or ()]
    rows += [(r, "abs") for r in rec.get("abstentions") or ()]
    rows.sort(key=lambda t: RR._row_no(t[0]["id"]))
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = _remap(dict(r.get("detail") or {}), id_map)
        if kind == "obs":
            basis = tuple(id_map[b] for b in (r.get("basis") or ()) if b in id_map)
            new = log.observe(sub, r["quantity"], _remap(r["value"], id_map), reader=r["reader"], frame=r["frame"],
                              score=r.get("score"), derived_from=basis, **detail)
        else:
            new = log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **detail)
        assert new.id == id_map[r["id"]], (new.id, id_map[r["id"]])
    return log, id_map


def live(chain):
    sup = {v.get("supersedes") for v in chain if v.get("supersedes")}
    l = [v for v in chain if v["id"] not in sup]
    return (l or chain)[-1]


if __name__ == "__main__":
    rec = json.load(open(sys.argv[1]))
    log, _ = rebuild(rec)
    RR.run_stages(log)
    new = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] == "duration":
            new.setdefault(v["subject"], []).append(v)
    old = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "duration":
            old.setdefault(v["subject"], []).append(v)
    diff = []
    for g, ch in old.items():
        if g not in new:
            diff.append((g, "missing"))
            continue
        a = next((v for v in ch if v.get("decider") == "adjudicate_duration"), None)
        b = next((v for v in new[g] if v.get("decider") == "adjudicate_duration"), None)
        if a is None or b is None:
            continue
        ka = (a["outcome"], a.get("reason"), json.dumps(a["value"], sort_keys=True, default=str))
        kb = (b["outcome"], b.get("reason"), json.dumps(b["value"], sort_keys=True, default=str))
        if ka != kb:
            diff.append((g, ka[:2], kb[:2]))
    print("glyphs", len(old), "differ", len(diff))
    for d in diff[:15]:
        print("  ", d)
