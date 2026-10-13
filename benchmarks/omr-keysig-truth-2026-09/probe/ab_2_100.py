"""2.100 base vs arm on ONE tree, from ONE saved gather record.

    python3 benchmarks/omr-keysig-truth-2026-09/probe/ab_2_100.py REC.json OUTDIR

REC.json is a small-re-gather record (`acceptance_quick`, `--through
adjudicate` is enough: only its GATHER rows are used). Both arms re-run
ADJUDICATE..INFER from the SAME gather rows; the ONLY difference is that the
OFF arm makes `key_slots.key_slot_occupant` answer None (the tree before
2.100). REACH first: how many rest / notehead glyphs the ON arm refuses in key
slots, by class and reason; then the bars they sit in, via the exporter's own
`_bar_holds_out` (wrapped, not restated); then every KEY verdict that differs.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged import adjudicate, export as EXPORT  # noqa: E402
from tools.omr.staged.adjudicators import key_slots as KS  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

rec_path, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
adjudicate._ensure_decisions()
real_occ = KS.key_slot_occupant


def cell_of(sub):
    p = (sub or "").split("/")
    if len(p) >= 6 and p[0] == "glyph":
        return "/".join(p[1:5])
    return None


def run(arm):
    log, _ = rerun.rebuild_gather(rec)
    if arm == "off":
        KS.key_slot_occupant = lambda ev, row: None
    bars = {}
    real_hold = EXPORT._bar_holds_out

    def wrapped(events, streams, divisions, meter):
        r = real_hold(events, streams, divisions, meter)
        c = None
        for ev in events:
            for h in (ev.get("noteheads") or [(ev.get("rest") or {})]):
                c = cell_of((h or {}).get("glyph"))
                if c:
                    break
            if c:
                break
        if c:
            bars[c] = {"held": r is not None,
                       "no_meter": EXPORT._bar_quarters(meter) is None,
                       "quarters": (r or {}).get("quarters"),
                       "want": (r or {}).get("want_quarters"),
                       "n_events": len(events)}
        return r

    EXPORT._bar_holds_out = wrapped
    try:
        rerun.run_stages(log)
        result = {"record": log.to_json(), "summary": log.summary()}
        xml, report = EXPORT.to_musicxml(result)
    finally:
        EXPORT._bar_holds_out = real_hold
        KS.key_slot_occupant = real_occ
    (out / f"{arm}.musicxml").write_text(xml)
    r = result["record"]
    return {"verdicts": r["verdicts"], "obs": r["observations"], "bars": bars,
            "held": (report.get("bars_held_out_sum") or {}).get("bars"),
            "of": (report.get("bars_held_out_sum") or {}).get("of_bars_with_events"),
            "balanced": (report.get("balance") or {}).get("balanced"),
            "notes_not_written_total": report.get("notes_not_written_total")}


off, on = run("off"), run("on")

# ── REACH ────────────────────────────────────────────────────────────────
box = {o["subject"]: o["value"] for o in on["obs"] if o["quantity"] == Q.GLYPH_BOX}
last = {}
for v in on["verdicts"]:
    if v["quantity"] in (Q.REST_IS_NOT_A_REST, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD):
        last[(v["quantity"], v["subject"])] = v
refused = [(q, s, v) for (q, s), v in last.items()
           if v["reason"] in ("rest_in_a_key_signature_slot",
                              "notehead_in_a_key_signature_slot")]
byc = collections.Counter((box[s][0], v["reason"]) for q, s, v in refused)
print("REACH refused in key slots:", len(refused))
for k, n in sorted(byc.items()):
    print("  ", n, k)

# the rest of the window's occupants (classes this build does NOT refuse)
cells = collections.defaultdict(list)
for o in on["obs"]:
    if o["quantity"] == Q.GLYPH_BOX and o["subject"].startswith("glyph/"):
        p = o["subject"].split("/")
        if p[4] == "0":
            cells["/".join(p[1:4])].append(o)
space = {o["subject"][5:-2]: o["value"] for o in on["obs"]
         if o["quantity"] == Q.CELL_STAFF_SPACE and o["subject"].endswith("/0")}
other = collections.Counter()
n_win = 0
for st, rows in cells.items():
    sp = space.get(st)
    if not sp:
        continue
    boxes = [KS.KeyBox(r["id"], r["value"][0], *map(float, r["value"][1:])) for r in rows
             if isinstance(r["value"], list) and len(r["value"]) == 5]
    w = KS.key_slot_window(boxes, float(sp))
    if w is None:
        continue
    n_win += 1
    for b in boxes:
        if KS.stands_in_the_window(w, b):
            other[(b.cls, "music-class" if KS.is_music_class(b.cls) else "other")] += 1
print("header cells with a key window:", n_win, "of", len(cells))
print("every non-key box standing in a window:", dict(other))

# ── BARS of the refused glyphs ──────────────────────────────────────────
cls = collections.defaultdict(list)
for q, s, v in refused:
    c = cell_of(s)
    b0, b1 = off["bars"].get(c), on["bars"].get(c)
    if b0 is None and b1 is None:
        k = "no_bar_either_arm"
    elif b0 is None or b1 is None:
        k = "bar_missing_one_arm"
    elif b0["no_meter"] or b1["no_meter"]:
        k = "no_verdict"
    elif b0["held"] and not b1["held"]:
        k = "released"
    elif b0["held"] and b1["held"]:
        k = "still_held"
    elif not b0["held"] and b1["held"]:
        k = "newly_held"
    else:
        k = "unchanged_ok"
    cls[k].append({"subject": s, "cell": c, "class": box[s][0], "off": b0, "on": b1})
print("BARS of the refused glyphs:", {k: len(v) for k, v in cls.items()})
print("held OFF/ON:", off["held"], on["held"], "of", off["of"], on["of"],
      "balanced", off["balanced"], on["balanced"],
      "notes_not_written", off["notes_not_written_total"], on["notes_not_written_total"])

# ── KEYS ───────────────────────────────────────────────────────────────
def keys(a):
    d = {}
    for v in a["verdicts"]:
        if v["quantity"] in (Q.KEY_SIGNATURE,):
            d[v["subject"]] = (v["outcome"], v["value"], v["reason"])
    return d


k0, k1 = keys(off), keys(on)
chg = {s: (k0.get(s), k1.get(s)) for s in set(k0) | set(k1) if k0.get(s) != k1.get(s)}
print("KEY verdicts changed:", len(chg))
for s, (a, b) in sorted(chg.items())[:40]:
    print("  ", s, a, "->", b)


def bars_xml(xml):
    d = {}
    for pm in re.finditer(r'<part id="([^"]+)">(.*?)</part>', xml, re.S):
        for mm in re.finditer(r'<measure number="([^"]+)"[^>]*>(.*?)</measure>',
                              pm.group(2), re.S):
            d[(pm.group(1), mm.group(1))] = mm.group(2)
    return d


b0 = bars_xml((out / "off.musicxml").read_text())
b1 = bars_xml((out / "on.musicxml").read_text())
changed = sorted(k for k in set(b0) | set(b1) if b0.get(k) != b1.get(k))
print("MusicXML bars changed:", len(changed))
(out / "ab_2_100.json").write_text(json.dumps({
    "refused": [{"subject": s, "reason": v["reason"], "class": box[s][0],
                 "detail": v.get("detail")} for q, s, v in refused],
    "classes": cls, "keys_changed": {s: list(x) for s, x in chg.items()},
    "changed_bars": [list(k) for k in changed],
    "held": [off["held"], on["held"]], "of": [off["of"], on["of"]]},
    indent=1, default=str))
