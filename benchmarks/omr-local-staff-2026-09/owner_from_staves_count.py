"""lane-owner-from-staves (2026-10-06) STEP 1: how many noteheads lie inside ANOTHER staff's five-line band, and
what `glyph_owner` says about them today. Read-only: one `record_io.load_record`, no gather.

    python3 benchmarks/omr-local-staff-2026-09/owner_from_staves_count.py REC.record.json OUT.json

Sean (DECISIONS 2026-10-06): a head ON or BETWEEN a known staff's five lines belongs to that staff. This counts, per
document, the notehead copies whose centre is in a staff band other than the one they were filed on, and for each:
the owner verdict now (none / decided home / decided the band staff / decided a third / abstained+reason), and
whether a notehead box exists on the band staff (IoU > CONTEST_IOU against this copy -- the contest's own test).

The band is page-wide (`Q.STAFF_LINES`, the only line record a finished record holds); a scanned staff wanders, so
`edge` counts the heads within `EDGE_SPACES` of a band edge, where a local measure could change the answer. A twin on
the band staff also carries a LOCAL position (`Q.NOTEHEAD_STAFF_POSITION`, that cell's own grid): `local_check`.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import record_io  # noqa: E402
from tools.omr.staged.gather import CONTEST_IOU, _iou  # noqa: E402

EDGE_SPACES = 0.5
SLACK_SPACES = 2.0          # a cell's pad: a staff's x extent plus this still counts as "beside" it


def parse(key):
    p = key.split("/")
    return tuple(int(x) for x in p[1:])


def thickness(detail):
    t = (detail or {}).get("thickness_px")
    if isinstance(t, (list, tuple)):
        t = sorted(t)[len(t) // 2] if t else None
    return float(t) if t else 0.0


def collect(rec):
    r = rec["record"]
    staves = {}
    boxes = {}
    pos = {}
    bands = defaultdict(list)
    for o in r["observations"]:
        q = o["quantity"]
        s = o["subject"]
        if q == "staff_lines":
            staves.setdefault(s, {})["lines"] = [float(v) for v in o["value"]]
        elif q == "staff_spacing":
            staves.setdefault(s, {})["sp"] = float(o["value"])
        elif q == "staff_extent":
            staves.setdefault(s, {})["x"] = [float(v) for v in o["value"]]
        elif q == "staff_skew":
            staves.setdefault(s, {})["th"] = thickness(o.get("detail"))
        elif q == "glyph_box" and s.startswith("glyph/") and str(o["value"][0]).startswith("notehead"):
            d = o["detail"]
            if d.get("bbox_page_px"):
                boxes[s] = (o["value"][0], d["bbox_page_px"])
        elif q == "notehead_staff_position":
            pos[s] = float(o["value"])
        elif q == "glyph_band_distance":
            bands[s].append(o["detail"].get("candidate"))
    verdict = {}
    for v in r["verdicts"]:
        if v["quantity"] == "glyph_owner":
            verdict[v["subject"]] = (v["outcome"], v["value"], v["reason"])
    return staves, boxes, pos, bands, verdict


def analyse(rec):
    staves, boxes, pos, bands, verdict = collect(rec)
    by_sys = defaultdict(list)
    for s in staves:
        if "lines" in staves[s] and "sp" in staves[s] and "x" in staves[s]:
            p, sy, st = parse(s)
            by_sys[(p, sy)].append(s)
    heads_by_sys = defaultdict(list)
    for g, (_n, b) in boxes.items():
        p, sy, st, _c, _gi = parse(g)
        heads_by_sys[(p, sy)].append(g)

    out = Counter()
    rows = []
    for g, (_name, b) in sorted(boxes.items()):
        p, sy, st, c, gi = parse(g)
        home = f"staff/{p}/{sy}/{st}"
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        out["noteheads"] += 1
        in_band = []
        for s in by_sys.get((p, sy), []):
            S = staves[s]
            th = S.get("th", 0.0)
            top, bot = min(S["lines"]) - th / 2, max(S["lines"]) + th / 2
            if not (S["x"][0] - SLACK_SPACES * S["sp"] <= cx <= S["x"][1] + SLACK_SPACES * S["sp"]):
                continue
            if top <= cy <= bot:
                in_band.append((s, min(cy - top, bot - cy) / S["sp"]))
        if not in_band:
            out["in_no_band"] += 1
            continue
        band_staff, edge_d = in_band[0]
        if band_staff == home:
            out["in_own_band"] += 1
            v = verdict.get(g)
            if v is not None and v[0] == "decided" and v[1] != home:
                out["own_band_but_owned_elsewhere"] += 1
            elif v is not None and v[0] == "abstained":
                out["own_band_abstained"] += 1
            continue
        # a copy filed on ANOTHER staff, lying in `band_staff`'s band
        out["in_other_band"] += 1
        v = verdict.get(g)
        if v is None:
            state = "no_verdict" + ("_but_has_band_rows" if bands.get(g) else "")
        elif v[0] == "decided":
            state = ("decided_home" if v[1] == home else "decided_band_staff"
                     if v[1] == band_staff else "decided_third") + ":" + str(v[2])
        else:
            state = "abstained:" + str(v[2])
        # twin: a notehead box on the band staff overlapping this copy
        twin = None
        for h in heads_by_sys[(p, sy)]:
            if h == g:
                continue
            hp, hs, hst = parse(h)[0], parse(h)[1], parse(h)[2]
            if f"staff/{hp}/{hs}/{hst}" != band_staff:
                continue
            if _iou(b, boxes[h][1]) > CONTEST_IOU:
                twin = h
                break
        # far from the FILED staff: this copy would need a ledger toward `home`
        S0 = staves.get(home)
        far_home = False
        if S0:
            sp0 = S0["sp"]
            top0, bot0 = min(S0["lines"]), max(S0["lines"])
            gap = (top0 - cy) if cy < top0 else (cy - bot0)
            far_home = int(gap / sp0 + 0.25) >= 1 if gap > 0 else False
        local = None
        if twin is not None and twin in pos:
            local = bool(-0.2 <= pos[twin] <= 8.2)
        out[f"state/{state}"] += 1
        out["twin_on_band_staff" if twin else "no_twin_on_band_staff"] += 1
        out[f"{state}|{'twin' if twin else 'no_twin'}"] += 1
        if edge_d < EDGE_SPACES:
            out["edge"] += 1
        if far_home:
            out["far_from_filed_staff"] += 1
        if local is not None:
            out["local_check_twin_in_band" if local else "local_check_twin_NOT_in_band"] += 1
        rows.append(dict(subject=g, home=home, band_staff=band_staff, state=state, twin=twin,
                         edge_spaces=round(edge_d, 3), far_from_filed=far_home, local_twin_in_band=local,
                         box=[round(v, 1) for v in b], cls=_name))
    return dict(counts=dict(out), rows=rows)


if __name__ == "__main__":
    rec = record_io.load_record(sys.argv[1])
    res = analyse(rec)
    res["provenance"] = rec.get("provenance", {}).get("commit")
    Path(sys.argv[2]).write_text(json.dumps(res))
    for k, v in sorted(res["counts"].items()):
        print(f"{k:60s} {v}")
