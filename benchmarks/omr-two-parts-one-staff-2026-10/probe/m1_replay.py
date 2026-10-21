"""ROADMAP 2.182 -- replay a record ADJUDICATE..INFER..EXPORT with main's defaults, per arm, and measure the EXPORTED FILE.

  off -- OMR_TWO_PARTS_ONE_STAFF=0 OMR_REST_CHAIN_KEPT_OUTRANKS=0 (main)
  a   -- two parts only            b -- rest chain only            on -- both

usage: m1_replay.py DOC SOURCE OUTDIR ARM[,ARM...]
SOURCE is a whole record .json (the 5-page 2.179 records) or a slice directory of per-page jsonl (`sp/slices/<doc>`, the
20261018-night records cut by 2.177's slice_record.py). Writes OUTDIR/DOC.ARM.json (summary + red bars + Q.VOICES reasons +
two-voice bars + rest refusals + the written bars' keys) and OUTDIR/DOC.ARM.record.json (judged quantities for `judged score`).
"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SRC, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
A, B = "OMR_TWO_PARTS_ONE_STAFF", "OMR_REST_CHAIN_KEPT_OUTRANKS"
ENV = {"off": ("0", "0"), "a": ("1", "0"), "b": ("0", "1"), "on": ("1", "1")}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind",
            "rest_is_not_a_rest"}
os.environ.setdefault("OMR_RED_BARS", "1")
os.makedirs(OUTDIR, exist_ok=True)
t0 = time.time()
if os.path.isdir(SRC):
    def rows(kind):
        out = []
        for p in sorted(glob.glob(os.path.join(SRC, "*.%s.jsonl" % kind))):
            out += [json.loads(line) for line in open(p)]
        return out
    rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
else:
    rec = load_record(SRC)["record"]
print(DOC, "loaded %.0fs" % (time.time() - t0), flush=True)


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


for arm in ARMS:
    os.environ[A], os.environ[B] = ENV[arm]
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    vs = result["record"]["verdicts"]
    voices = live(vs, "voices", "cell/")
    vreason = collections.Counter((v["outcome"], v.get("reason")) for v in voices.values())
    two_parts = {c[5:]: dict(reason=v.get("reason"), voices=(v.get("value") or {}).get("voices"),
                             guessed=(v.get("value") or {}).get("voice_guessed"))
                 for c, v in voices.items() if v.get("reason") in ("two_parts_by_stem_and_height", "two_parts_one_resting")}
    rest_ref = {g: v.get("reason") for g, v in live(vs, "rest_is_not_a_rest", "glyph/").items() if v["value"] is True}
    t1 = time.time()
    xml, rep = E.to_musicxml(result)
    w = rep["written"]
    red = rep.get("bars_written_red") or {}
    try:
        from tools.omr import acceptance as AC
        addup = AC.bars_add_up(xml)
    except Exception as exc:  # noqa: BLE001
        addup = "error %s" % type(exc).__name__
    summ = dict(doc=DOC, arm=arm, notes=w.get("notes"), rests=w.get("rests"), notes_in_xml=xml.count("<note"),
                bars_with_events=w.get("bars_with_events"), two_voice_bars=w.get("two_voice_bars"),
                two_voice_bars_red=red.get("two_voice"), bars_red=red.get("bars"), bars_add_up=addup,
                guessed_voice=sum(v for k, v in w.items() if k.endswith("voice_guessed")),
                guessed=rep.get("guessed"), voices_reasons={"%s:%s" % k: n for k, n in vreason.items()},
                n_two_parts=len(two_parts), rest_refusals=collections.Counter(rest_ref.values()),
                two_voice_refused={k: v for k, v in w.items() if k.startswith("two_voice_bars_refused_")},
                secs_export=round(time.time() - t1), secs=round(time.time() - t0))
    out = dict(summary=summ, red_bars=["%d/%d/%d/%d" % (r["page"], r["system"], r["staff"], r["cell"]) for r in red.get("bars_list", [])],
               red_rows=red.get("bars_list", []), two_parts=two_parts, rest_refused=rest_ref,
               voices={c[5:]: [v["outcome"], v.get("reason"), (v.get("value") or {}).get("n_voices")] for c, v in voices.items()})
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    json.dump({"observations": [o for o in result["record"]["observations"] if o["quantity"] == "glyph_box"],
               "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w").write(xml)
    del vs, result, xml
    print(json.dumps({k: summ[k] for k in ("arm", "notes", "rests", "notes_in_xml", "two_voice_bars", "bars_red", "n_two_parts",
                                           "guessed_voice", "secs")}, default=str), flush=True)
