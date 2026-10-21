"""ROADMAP 2.180 -- direct check against lane 2.179's labelled Brahms red bars (pdf pp 0,1,6,23,24, re-gathered on main's feed):
its labels/brahms.txt code `e` = "a dot boxed beside its head, written undotted". Replays that BASE record ADJUDICATE..EXPORT with
OMR_DOT_POSITION_OVER_WEDGE off vs on and asks, per labelled dot bar: is it still red, and which notes gained a dot.
usage: check_2179_bars.py BASE_RECORD CENSUS.json LABELS.txt OUT.json"""
import json
import os
import re
import sys

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

base, census, labels, out = sys.argv[1:5]
C = json.load(open(census))
dot_bars = {}
for line in open(labels):
    if line.startswith("#") or "|" not in line:
        continue
    i, codes, note = [x.strip() for x in line.split("|", 2)]
    cs = codes.split()
    if cs and cs[0] == "e" and "dot" in note:
        dot_bars.setdefault(C[int(i)]["bar"], []).append((int(i), note))
print("labelled dot bars (main cause e, distinct):", len(dot_bars), flush=True)
rec = load_record(base)["record"]
gather = {"observations": rec["observations"], "abstentions": rec.get("abstentions", []), "verdicts": []}
res = {}
for arm, v in (("off", "0"), ("on", "1")):
    os.environ["OMR_DOT_POSITION_OVER_WEDGE"] = v
    log, _ = RR.rebuild_gather(gather)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    xml, rep = E.to_musicxml(result)
    red = {"%s/%s/%s/%s" % (b["page"], b["system"], b["staff"], b["cell"]): b for b in (rep.get("bars_written_red") or {}).get("bars_list", [])}
    dur = {}
    for vv in result["record"]["verdicts"]:
        if vv["quantity"] == "duration" and isinstance(vv.get("value"), dict):
            dur[vv["subject"]] = (vv["outcome"], vv["value"].get("written"), vv["value"].get("dots"), vv.get("reason"))
    roles = {vv["subject"]: (vv["outcome"], vv.get("value"), vv.get("reason")) for vv in result["record"]["verdicts"]
             if vv["quantity"] == "dot_role"}
    res[arm] = dict(red=set(red), dur=dur, roles=roles, n_red=len(red),
                    dotted=sum(1 for n in re.findall(r"<note\b.*?</note>", xml, flags=re.S) if "<dot/>" in n and "<rest" not in n))
    print(arm, "red bars", len(red), "dotted notes", res[arm]["dotted"], flush=True)
    del log, result, xml
rows = []
for bar, labs in sorted(dot_bars.items()):
    pre = "glyph/" + "/".join(bar.split("/")[:3]) + "/"
    cell = bar.split("/")[3]
    gained = [g for g in res["on"]["dur"] if g.startswith(pre) and g.split("/")[5 - 1] == cell
              and res["off"]["dur"].get(g) != res["on"]["dur"].get(g)]
    rows.append(dict(bar=bar, labels=labs, red_off=bar in res["off"]["red"], red_on=bar in res["on"]["red"],
                     changed={g: (res["off"]["dur"].get(g), res["on"]["dur"].get(g)) for g in gained}))
fixed = sum(1 for r in rows if r["red_off"] and not r["red_on"])
gain = sum(1 for r in rows if r["changed"])
print("of %d labelled dot bars: red OFF %d, red ON %d; bars whose note values changed ON: %d; bars no longer red: %d"
      % (len(rows), sum(r["red_off"] for r in rows), sum(r["red_on"] for r in rows), gain, fixed))
print("roles changed:", sum(1 for g in res["on"]["roles"] if res["on"]["roles"][g] != res["off"]["roles"].get(g)))
json.dump(dict(rows=rows, n_red={a: res[a]["n_red"] for a in res}, dotted={a: res[a]["dotted"] for a in res}),
          open(out, "w"), default=str, indent=1)
