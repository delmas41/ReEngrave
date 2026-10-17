"""ROADMAP 2.162 -- replay a WHOLE 20261016-night record's GATHER rows (re-assembled from `pages_2_162.py` per-page slices;
no gather, no detector) through INFER with review.rerun (2.157-fixed), one arm at a time. STAGED ADJUDICATE..INFER.
Arms (everything else shipped):
  base  -- OMR_NARROWED_BAR_LENGTH_UNKNOWN off, OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM off   (= main)
  mine  -- 2.162 on,  2.153 off
  b153  -- 2.162 off, 2.153 on
  both  -- 2.162 on,  2.153 on
CONTROL (base arm only): its live duration verdict vs the stored live one, every glyph (a faithful replay differs on ~0).
Writes, per arm, OUTDIR/<doc>.<arm>.json {glyphs: {glyph: brief}, meters: {system: brief}, unknown_moves: n, control?}
and OUTDIR/<doc>.<arm>.record.json, a mini record (first box per glyph + the replay's judged-quantity verdicts) for
`python3 -m tools.omr.staged.judged score`.
usage: replay_2_162.py DOC SLICEDIR OUTDIR ARM[,ARM...]"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
D = os.path.join(SD, DOC)
MINE, B153 = "OMR_NARROWED_BAR_LENGTH_UNKNOWN", "OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM"
ENV = {"base": ("0", "0"), "mine": ("1", "0"), "b153": ("0", "1"), "both": ("1", "1")}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
os.makedirs(OUTDIR, exist_ok=True)


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        out += [json.loads(l) for l in open(p)]
    return out


def live(verdicts, quantity, prefix):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == quantity and v["subject"].startswith(prefix):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def brief(v):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    d = v.get("detail") or {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                decider=v.get("decider"), reason=v.get("reason"), rest=bool(val.get("is_rest")),
                rest_glyph=d.get("rest"), measure_rest=bool(val.get("measure_rest")),
                unknown=bool(d.get("bar_length_unknown")),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def meter_brief(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    d = v.get("detail") or {}
    return dict(outcome=v["outcome"], reason=v.get("reason"), num=val.get("numerator"), den=val.get("denominator"),
                segments=[(s.get("from_cell"), s.get("numerator"), s.get("denominator")) for s in (val.get("segments") or [])],
                support=d.get("support"), agree=d.get("bars_agree"), disagree=d.get("bars_disagree"))


def key(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["beats"], tuple(b["cands"] or ()))


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
stored = {g: brief(v) for g, v in live(rows("verdicts"), "duration", "glyph/").items()}
boxes, seen = [], set()
for o in rec["observations"]:
    s = o.get("subject") or ""
    if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
        seen.add(s)
        boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
print(DOC, "rows", len(rec["observations"]), len(rec["abstentions"]), "stored glyphs", len(stored), flush=True)
for arm in ARMS:
    os.environ[MINE], os.environ[B153] = ENV[arm]
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    del log
    glyphs = {g: brief(v) for g, v in live(vs, "duration", "glyph/").items()}
    meters = {s: meter_brief(v) for s, v in live(vs, "meter", "system/").items()}
    out = dict(doc=DOC, arm=arm, env=ENV[arm], glyphs=glyphs, meters=meters,
               unknown_moves=sum(1 for v in vs if (v.get("detail") or {}).get("bar_length_unknown")))
    if arm == "base":
        ctl = collections.Counter("agree" if key(glyphs.get(g)) == key(b) else "differ" for g, b in stored.items())
        out["control"] = dict(ctl)
        out["control_rows"] = [dict(glyph=g, stored=b, off=glyphs.get(g)) for g, b in stored.items()
                               if key(glyphs.get(g)) != key(b)][:200]
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"))
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    del vs
    print(DOC, arm, "glyphs", len(glyphs), "meters", len(meters), "unknown_moves", out["unknown_moves"],
          "control", out.get("control"), "%.0fs" % (time.time() - t0), flush=True)
