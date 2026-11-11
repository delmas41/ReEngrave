"""Arcs, ONE COMBINED STACK (2.274 step 2 `OMR_PAGE_ARC_WRITE` + 2.281 `OMR_ARC_MEETING_AT_HEAD`): both flags OFF (= main) vs both ON, scored and diffed.

    python3 arcs_combined.py score  WORK_DIR  [--page 0] [--reach 2.5] [--controls]
    python3 arcs_combined.py keys                       # the two keys against each other (corrected key vs Sean's page-pass arc labels)
    python3 arcs_combined.py lost   PLATE WORK_DIR      # every arc present OFF and absent ON (and every gained arc), one by one, with its place and the ON arcs that stand there

WORK_DIR = a `lane_report --out DIR/work` folder (PLATE.off|on.musicxml, PLATE.off|on.gathered.record.json).

The two KEYS (both read-only):
  corrected  = key-brahms-p0-corrected.json (2.281 r1, Claude's join of Sean's per-cell hand boxes; `assumed_for_sean` where it is not Sean's box);
  sean       = data/hand-truth/pages/imslp317803/0.pagepass.json on branch origin/lane-2.287-page-labelling: Sean's own WHOLE-PAGE labels of 2026-11-10
               (kind "arc", state "confirmed"; `sub` tie|slur; 75 of the 98 were a pre-fill he CONFIRMED, 21 he FIXED, 2 he DREW). Copied to PAGEPASS below ONLY as data.

MATCHING RULE (score_key.py's, unchanged): a written arc (kind, start head, stop head; each end = its head box centre) satisfies a key arc when its start head is within REACH
sp (x) of the key's left end and its stop head within REACH of the right end, both heads within 6 sp (y) of the key's y band; REACH 2.5 sp (slurs) / 3.5 sp (ties); one written
arc satisfies one key arc (global greedy, kind-right pairs first). RIGHT = kind agrees (or the key marks the kind unsettled); OTHER_KIND = the ends fit and the kind is wrong;
NONE = no written arc fits. WRITTEN_UNMATCHED = a written arc that satisfies no key arc (not necessarily 'not printed': the key may lack it; the list is shown).
CONTROLS THAT CAN FAIL: --controls drops 20 written arcs (the score must fall) and shifts every key arc 6 sp (it must collapse).
"""
import collections
import json
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402

SP = 32.0
CORRECTED = HERE / "key-brahms-p0-corrected.json"
PAGEPASS = pathlib.Path("/private/tmp/claude-501/scr-arcs/pagepass0.json")      # git show origin/lane-2.287-page-labelling:data/hand-truth/pages/imslp317803/0.pagepass.json


def key_corrected():
    out = []
    for k in json.load(open(CORRECTED))["arcs"]:
        if k["scorable"]:
            out.append(dict(id=k["id"], kind=k["kind"], x0=k["x0"], x1=k["x1"], y0=k["y0"], y1=k["y1"], kind_conflict=bool(k["kind_conflict"])))
    return out


def key_sean():
    out = []
    for l in json.load(open(PAGEPASS))["labels"]:
        if l.get("kind") == "arc" and l.get("state") == "confirmed":
            x0, y0, x1, y1 = l["shape"]["rect"]
            out.append(dict(id=l["id"], kind=l.get("sub"), x0=x0, x1=x1, y0=y0, y1=y1, kind_conflict=False, origin=l.get("origin"), note=l.get("note") or ""))
    return out


def head_boxes(record_path, page):
    out = {}
    pre = "glyph/%d/" % page
    for o in json.loads(pathlib.Path(record_path).read_text())["observations"]:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and o["subject"].startswith(pre):
            out.setdefault(o["subject"], [float(v) for v in b])
    return out


def spans_of(xml, boxes, page):
    out = []
    pre = "glyph/%d/" % page
    for a in A.arcs_of_xml(xml):
        if not a["start"].startswith(pre) or a["start"] not in boxes or a["stop"] not in boxes:
            continue
        ba, bz = boxes[a["start"]], boxes[a["stop"]]
        xa, xz = (ba[0] + ba[2]) / 2, (bz[0] + bz[2]) / 2
        if xz < xa:
            xa, xz, ba, bz = xz, xa, bz, ba
        out.append(dict(kind=a["kind"], xa=xa, xz=xz, ya=(ba[1] + ba[3]) / 2, yz=(bz[1] + bz[3]) / 2, start=a["start"], stop=a["stop"]))
    return out


def yd(y, y0, y1):
    return 0.0 if y0 <= y <= y1 else min(abs(y - y0), abs(y - y1))


def score(keys, spans, reach=2.5, shift=0.0):
    pairs = []
    for ki, k in enumerate(keys):
        r = (3.5 if k["kind"] == "tie" else reach) * SP if reach == 2.5 else reach * SP
        x0, x1 = k["x0"] + shift * SP, k["x1"] + shift * SP
        for i, s in enumerate(spans):
            if abs(s["xa"] - x0) <= r and abs(s["xz"] - x1) <= r and yd(s["ya"], k["y0"], k["y1"]) <= 6 * SP and yd(s["yz"], k["y0"], k["y1"]) <= 6 * SP:
                good = bool(k["kind_conflict"] or s["kind"] == k["kind"])
                cost = abs(s["xa"] - x0) + abs(s["xz"] - x1) + yd(s["ya"], k["y0"], k["y1"]) + yd(s["yz"], k["y0"], k["y1"])
                pairs.append((not good, cost, ki, i, good))
    pairs.sort()
    used_k, used_w = {}, set()
    for _ng, _c, ki, i, good in pairs:
        if ki in used_k or i in used_w:
            continue
        used_k[ki] = (i, good)
        used_w.add(i)
    res = collections.Counter()
    rows = {}
    for ki, k in enumerate(keys):
        if ki in used_k:
            i, good = used_k[ki]
            res["right" if good else "other_kind"] += 1
            rows[k["id"]] = ("right" if good else "other_kind", i)
        else:
            res["none"] += 1
            rows[k["id"]] = ("none", None)
    res["keys"] = len(keys)
    res["written"] = len(spans)
    res["written_unmatched"] = len(spans) - len(used_w)
    return res, rows, sorted(set(range(len(spans))) - used_w)


def cmd_score(work, page, reach, controls):
    work = pathlib.Path(work)
    plate = "brahms"
    arms = {}
    for arm in ("off", "on"):
        xml = (work / ("%s.%s.musicxml" % (plate, arm))).read_text()
        boxes = head_boxes(work / ("%s.%s.gathered.record.json" % (plate, arm)), page)
        arms[arm] = (spans_of(xml, boxes, page), boxes)
    # one head-box table for both arms (a glyph key is the same detection in both gathers; the ON gather adds no box)
    for kname, keys in (("corrected", key_corrected()), ("sean", key_sean())):
        print("== key %s (%d arcs)" % (kname, len(keys)))
        got = {}
        for arm in ("off", "on"):
            res, rows, un = score(keys, arms[arm][0], reach)
            got[arm] = (res, rows, un)
            print("  %-3s written %3d | right %3d  other_kind %2d  none %3d | written matching no key arc %3d" % (arm, res["written"], res["right"], res["other_kind"], res["none"], res["written_unmatched"]))
        lost = [k for k, (st, _i) in got["off"][1].items() if st == "right" and got["on"][1][k][0] != "right"]
        won = [k for k, (st, _i) in got["on"][1].items() if st == "right" and got["off"][1][k][0] != "right"]
        print("  key arcs right OFF -> not right ON: %d %s | not right OFF -> right ON: %d %s" % (len(lost), lost, len(won), won))
        if controls:
            for arm in ("off", "on"):
                sp = list(arms[arm][0])
                random.Random(7).shuffle(sp)
                r1, _, _ = score(keys, sp[20:], reach)
                r2, _, _ = score(keys, arms[arm][0], reach, shift=6.0)
                print("  control %-3s drop 20 written: right %d (was %d) | key shifted 6 sp: right %d" % (arm, r1["right"], got[arm][0]["right"], r2["right"]))
        kinds = collections.Counter()
        for arm in ("off", "on"):
            for k in keys:
                kinds[(arm, k["kind"], got[arm][1][k["id"]][0])] += 1
        print("  by kind:", dict(sorted(kinds.items())))
        for arm in ("off", "on"):
            un = got[arm][2]
            print("  %s written, matching no key arc (%d): %s" % (arm, len(un), [(arms[arm][0][i]["kind"], round(arms[arm][0][i]["xa"]), round(arms[arm][0][i]["xz"]), round(arms[arm][0][i]["ya"])) for i in un][:40]))


def cmd_keys():
    ck, sk = key_corrected(), key_sean()
    print("corrected %d scorable, sean %d confirmed" % (len(ck), len(sk)))
    used = set()
    only_sean, kind_diff, ext_diff = [], [], []
    for s in sk:
        best, bc = None, None
        for j, c in enumerate(ck):
            if j in used:
                continue
            d = abs(s["x0"] - c["x0"]) + abs(s["x1"] - c["x1"]) + yd((s["y0"] + s["y1"]) / 2, c["y0"], c["y1"])
            if abs(s["x0"] - c["x0"]) <= 3 * SP and abs(s["x1"] - c["x1"]) <= 3 * SP and yd((s["y0"] + s["y1"]) / 2, c["y0"], c["y1"]) <= 3 * SP:
                if bc is None or d < bc:
                    best, bc = j, d
        if best is None:
            only_sean.append(s)
            continue
        used.add(best)
        c = ck[best]
        if c["kind"] != s["kind"] and not c["kind_conflict"]:
            kind_diff.append((s["id"], c["id"], s["kind"], c["kind"], round(s["x0"]), round(s["y0"])))
        if abs(s["x0"] - c["x0"]) > 1 * SP or abs(s["x1"] - c["x1"]) > 1 * SP:
            ext_diff.append((s["id"], c["id"], round((s["x0"] - c["x0"]) / SP, 1), round((s["x1"] - c["x1"]) / SP, 1)))
    only_c = [c for j, c in enumerate(ck) if j not in used]
    print("Sean arcs with no corrected-key arc within 3 sp:", len(only_sean), [(s["id"], s["kind"], round(s["x0"]), round(s["x1"]), round(s["y0"]), s["origin"]) for s in only_sean])
    print("corrected-key arcs Sean did not confirm (or moved > 3 sp):", len(only_c), [(c["id"], c["kind"], round(c["x0"]), round(c["x1"]), round(c["y0"])) for c in only_c])
    print("kind differs (Sean vs corrected key):", len(kind_diff), kind_diff)
    print("extent differs by more than 1 sp at an end (Sean dx0, dx1 in sp):", len(ext_diff), ext_diff)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "score":
        cmd_score(a[1], int(a[a.index("--page") + 1]) if "--page" in a else 0, float(a[a.index("--reach") + 1]) if "--reach" in a else 2.5, "--controls" in a)
    elif a[0] == "keys":
        cmd_keys()
