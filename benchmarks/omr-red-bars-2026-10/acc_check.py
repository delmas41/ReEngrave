"""usage: acc_check.py OUTDIR TAG -- the acceptance control `bars_add_up` over each arm's MusicXML, plus an independent
parse: per-measure voice sums against the meter in force (imports nothing from the exporter)."""
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, ".")
from tools.omr import acceptance as A  # noqa: E402

out, tag = sys.argv[1], sys.argv[2]
for arm in ("off", "on"):
    x = open("%s/%s.%s.musicxml" % (out, tag, arm)).read()
    print(arm, A.bars_add_up(x), flush=True)
    root = ET.fromstring(x)
    red = bad = 0
    for part in root.findall("part"):
        div = beats = bt = None
        for m in part.findall("measure"):
            a = m.find("attributes")
            if a is not None:
                if a.find("divisions") is not None:
                    div = float(a.find("divisions").text)
                t = a.find("time")
                if t is not None:
                    beats, bt = float(t.find("beats").text), float(t.find("beat-type").text)
            is_red = any((w.text or "").startswith("does not add up") for w in m.iter("words"))
            red += is_red
            if is_red or div is None or beats is None:
                continue
            per = {}
            for el in m:
                if el.tag in ("note", "forward") and el.find("chord") is None and el.find("duration") is not None:
                    v = el.findtext("voice") or "1"
                    per[v] = per.get(v, 0) + float(el.findtext("duration")) / div
            if per and any(abs(x_ - beats * 4 / bt) > 1e-6 for x_ in per.values()):
                bad += 1
    print("   independent: red-marked measures", red, "| measures NOT red whose voice sum != meter", bad)
