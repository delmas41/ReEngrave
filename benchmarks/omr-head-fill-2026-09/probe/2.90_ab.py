"""2.90 base vs arm on ONE record, ONE tree: the same export with `_stem_facts_of`
patched to "no stem facts" (= 2.89) against the real one. EXPORT only.

    python3 .../2.90_ab.py RECORD.json [OUT_PREFIX]
"""
import json
import re
import sys

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

res = load_record(sys.argv[1])
prefix = sys.argv[2] if len(sys.argv) > 2 else None
real = E._stem_facts_of


def run(label, patch):
    E._stem_facts_of = (lambda rec, sub: {"stem_direction": None, "stem_id": None}) if patch else real
    xml, rep = E.to_musicxml(res)
    E._stem_facts_of = real
    if prefix:
        open(f"{prefix}.{label}.musicxml", "w").write(xml)
    return xml, rep


def bars(xml):
    """(part, measure number) -> (pitched notes, n voices, has measure rest)."""
    out = {}
    for pm in re.finditer(r'<part id="([^"]+)">(.*?)</part>', xml, re.S):
        for mm in re.finditer(r'<measure number="([^"]+)"[^>]*>(.*?)</measure>', pm.group(2), re.S):
            body = mm.group(2)
            out[(pm.group(1), mm.group(1))] = (
                len(re.findall(r"<pitch>", body)),
                len(set(re.findall(r"<voice>(\d+)</voice>", body))),
                'measure="yes"' in body)
    return out


bx, brep = run("base", True)
ax, arep = run("arm", False)
bb, ab = bars(bx), bars(ax)
changed = [k for k in bb if bb[k] != ab.get(k)]
pitched = lambda x: len(re.findall(r"<pitch>", x))
summary = {
    "pitched_base": pitched(bx), "pitched_arm": pitched(ax),
    "bars_changed": len(changed),
    "bars_now_more_voices": sum(1 for k in changed if ab[k][1] > bb[k][1]),
    "bars_gained_notes": sum(1 for k in changed if ab[k][0] > bb[k][0]),
    "bars_lost_notes": sum(1 for k in changed if ab[k][0] < bb[k][0]),
}


def pick(rep):
    flat = {}
    for k, v in rep.items():
        if isinstance(v, (int, float)) and any(w in k for w in ("chord", "voice", "overfull", "add_up", "held", "written")):
            flat[k] = v
    for k, v in (rep.get("dropped") or rep.get("not_written") or {}).items():
        flat["drop:" + k] = v
    return flat


summary["report_base"] = pick(brep)
summary["report_arm"] = pick(arep)
summary["balanced_base"] = brep.get("balanced")
summary["balanced_arm"] = arep.get("balanced")
print(json.dumps(summary, indent=1, default=str))
if prefix:
    json.dump({"base": brep, "arm": arep, "changed": [list(k) for k in changed]},
              open(f"{prefix}.reports.json", "w"), default=str)
