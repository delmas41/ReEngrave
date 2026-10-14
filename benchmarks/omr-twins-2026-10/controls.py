"""2.119 controls (rule 7): can the study fail?  python3 controls.py -> out/controls.json"""
import json, sys, re, collections, random
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import match as M
OUT = Path(__file__).resolve().parent / "out"
a = json.load(open(OUT / "analysis_ranked.json"))
bg = json.load(open(OUT / "brahms_p0.json"))["glyphs"]; lg = json.load(open(OUT / "litolff_p1.json"))["glyphs"]
res = {}
# C1: self-match -- fake "detector" = the truth boxes themselves, marked written: every truth note must come out stage 7
for doc, truth, frame in (("brahms", a["brahms"]["truth"], "page"), ("litolff", a["litolff"]["truth"], "canon")):
    fake = {}
    for i, t in enumerate(truth):
        k = f"fake{i}"
        g = {"cls": t["cls"], "score": 1.0, "place": "written", "rendered": {"guess": None, "rest": False}, "bar_fate": None, "system": t["system"], "staff": t["staff"],
             "cell": (t["cell"][2] if frame == "canon" else 0), "box_page": tuple(t["rect"]) if frame == "page" else None, "box_canon": tuple(t["rect"]) if frame == "canon" else None}
        fake[k] = g
    tt = [dict(t) for t in truth]
    if doc == "brahms": M.match_brahms(fake, tt)
    else:
        for t in tt: t["cell"] = tuple(t["cell"])
        M.match_litolff(fake, tt)
    stages = collections.Counter(M.fate_of_truth(t, fake)[0] for t in tt)
    res[f"self_match_{doc}"] = {"n": len(tt), "stage7": stages[7], "other": {str(k): v for k, v in stages.items() if k != 7}}
# C2: shifted truth (3 spaces) must match ~nothing
for doc, truth in (("brahms", a["brahms"]["truth"]), ("litolff", a["litolff"]["truth"])):
    tt = [dict(t) for t in truth]
    if doc == "brahms":
        M.match_brahms(bg, tt, shift=3.0); n = sum(bool(t["cands"]) for t in tt)
    else:
        for t in tt: t["cell"] = tuple(t["cell"])
        M.match_litolff(lg, tt, shift_frac=3.0, wmed=sorted(t["rect"][2]-t["rect"][0] for t in tt)[len(tt)//2]); n = sum(bool(t["cands"]) for t in tt)
    res[f"shifted3_{doc}"] = {"n": len(tt), "matched_any_notehead_box": n}
# C2b: shift by 1 space, still matches only part (sensitivity)
# C3: 10 spot-checks by key: written Brahms notes in the string parts (Violin I/II, Viola, Cello = staves 9-12) must be IN THE FILE (pitch present in that part's bar)
root = ET.parse(OUT / "brahms_p0.musicxml").getroot(); parts = root.findall("part")
def pitch_of(g):
    for r in reversed(g["rows"]):
        if r["q"] == "pitch" and r["stage"].startswith("EVAL") and r["outcome"] == "decided": return json.loads(r["value"])
def xml_pitches(staff, cell):
    ms = parts[staff].findall("measure"); out = []
    if cell + 1 >= len(ms): return out
    for n in ms[cell + 1 - 0].findall("note") if False else ms[cell].findall("note"):
        p = n.find("pitch")
        if p is not None: out.append(p.find("step").text + p.find("octave").text)
    return out
def cell_idx(t): return int(t["cell"].split("-m")[1])
written = [t for t in a["brahms"]["truth"] if t["stage"] == 7 and 9 <= t["staff"] <= 12 and t["box"] and pitch_of(bg[t["box"]])]
missed = [t for t in a["brahms"]["truth"] if t["stage"] < 7 and 9 <= t["staff"] <= 12 and t["box"] and pitch_of(bg[t["box"]])]
random.Random(7).shuffle(written)
checks = []
for t in written[:40]:
    p = pitch_of(bg[t["box"]]); step = re.match(r"([A-G])[#b]*(-?\d+)", p)
    want = step.group(1) + step.group(2)
    # measure number == cell index + 1 -> list index cell (measures[0] is measure 1)
    got = xml_pitches(t["staff"], cell_idx(t))
    checks.append({"id": t["id"], "key": bg[t["box"]] and t["box"], "part": t["staff"], "cell": t["cell"], "record_pitch": p, "in_file": want in got, "file_bar_pitches": got})
ok = sum(c["in_file"] for c in checks)
res["xml_spot_check_written"] = {"checked": len(checks), "found_in_file": ok, "first10": checks[:10]}
# the same check on NOT-written notes (must FAIL to find them, otherwise the check cannot tell): how many missed notes' pitch is nevertheless in that bar (a chord-mate or repeat may carry it)
neg = []
for t in missed[:40]:
    p = pitch_of(bg[t["box"]]); step = re.match(r"([A-G])[#b]*(-?\d+)", p); want = step.group(1) + step.group(2)
    got = xml_pitches(t["staff"], cell_idx(t)); neg.append({"id": t["id"], "code": t["code"], "record_pitch": p, "pitch_in_bar": want in got, "n_notes_in_bar": len(got)})
res["xml_spot_check_missed"] = {"checked": len(neg), "pitch_present_anyway": sum(n["pitch_present_anyway"] if False else n["pitch_in_bar"] for n in neg),
                                "bars_empty_in_file": sum(n["n_notes_in_bar"] == 0 for n in neg), "rows": neg[:12]}
# C4: the exporter's own total equals the hook's total (hook reproduces the file)
for doc, f in (("brahms", "brahms_p0"), ("litolff", "litolff_p1")):
    res[f"hook_total_{doc}"] = json.load(open(OUT / f"{f}.report.json"))["written"]["notes"]
json.dump(res, open(OUT / "controls.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k not in ("xml_spot_check_written", "xml_spot_check_missed")}, indent=1))
print("xml written:", res["xml_spot_check_written"]["checked"], "found", res["xml_spot_check_written"]["found_in_file"])
for c in res["xml_spot_check_written"]["first10"]: print(" ", c["id"], c["key"], "staff", c["part"], c["cell"], c["record_pitch"], c["in_file"], c["file_bar_pitches"][:8])
print("xml missed:", {k: v for k, v in res["xml_spot_check_missed"].items() if k != "rows"})
