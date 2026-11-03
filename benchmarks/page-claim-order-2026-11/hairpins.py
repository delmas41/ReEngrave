"""ROADMAP 2.253 step 0 -- hairpins on the frozen sample: how many the print holds, how many the CV reader files, and which of
those are letters (the 2.245 residue).

STAGED GATHER rows (the 20261029-night slices; 2.245's width rule is applied here as the gather now applies it, flag ON).
The reference encoding gives the print's count (a source that is not our reading); the page's bar range comes from the printed
bar numbers and the cell count per system.

    python3 benchmarks/page-claim-order-2026-11/hairpins.py count             # table + picks.json for the look sheet
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count as C  # noqa: E402

MIN_W_SP = 1.6     # tools/omr/staged/box_kind.HAIRPIN_MIN_W_SP (2.245)


def inside(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))
    return ix * iy / area


def ref_wedges_by_bar(plate):
    z = zipfile.ZipFile(C.REFERENCE[plate])
    name = [n for n in z.namelist() if n.endswith(".xml") and "META" not in n][0]
    s = z.read(name).decode("utf8", "replace")
    out = collections.Counter()
    for m in re.finditer(r'<measure[^>]*number="([^"]+)"(.*?)</measure>', s, re.S):
        n = re.sub(r"\D", "", m.group(1))
        if n:
            out[int(n)] += len(re.findall(r'<wedge[^>]*type="(?:crescendo|diminuendo)"', m.group(2)))
    return out


def page_rows(plate):
    pages = set(C.EDITIONS[plate][1])
    R = collections.defaultdict(lambda: collections.defaultdict(list))
    for o in C.rows(C.SLICES / plate):
        q = o["quantity"]
        if q not in ("wedge_box", "claimed_area", "staff_spacing", "printed_bar_number", "cell_box", "direction_word", "dynamic_letter"):
            continue
        p = int(o["subject"].split("/")[1])
        if p in pages:
            R[p][q].append(o)
    return R


def bar_range(prow, p):
    first = {}
    for o in prow["printed_bar_number"]:
        d = re.sub(r"\D", "", str(o["value"]))
        if d:
            first[int(o["subject"].split("/")[2])] = int(d)
    cells = collections.defaultdict(set)
    for o in prow["cell_box"]:
        _, _, s, st, c = o["subject"].split("/")
        if st == "0":
            cells[int(s)].add(int(c))
    systems = sorted(cells)
    start = first.get(systems[0], 1 if p == 0 else None)
    if start is None:
        for k, s in enumerate(systems):
            if s in first:      # a later system's printed number, less the bars of the systems before it
                start = first[s] - sum(len(cells[t]) for t in systems[:k])
                break
    if start is None:
        return None
    n = sum(len(cells[s]) for s in systems)
    return start, start + n - 1


def count(_=None):
    picks = []
    for plate in ("litolff", "brahms"):
        R = page_rows(plate)
        ref = ref_wedges_by_bar(plate)
        tot = collections.Counter()
        for p in sorted(R):
            pr = R[p]
            sp = sorted(float(o["value"]) for o in pr["staff_spacing"])
            u = sp[len(sp) // 2] if sp else None
            words = [o["value"] for o in pr["claimed_area"] if (o.get("detail") or {}).get("owner") == "word" and isinstance(o.get("value"), list)]
            words += [(o.get("detail") or {}).get("bbox_page_px") for o in pr["direction_word"] if (o.get("detail") or {}).get("bbox_page_px")]
            dyn = [(o.get("detail") or {}).get("bbox_page_px") for o in pr["dynamic_letter"] if (o.get("detail") or {}).get("bbox_page_px")]
            br = bar_range(pr, p)
            nref = sum(ref[b] for b in range(br[0], br[1] + 1)) if br else None
            cv = [o for o in pr["wedge_box"] if o["reader"] == "cv_hairpins"]
            det = [o for o in pr["wedge_box"] if o["reader"] != "cv_hairpins"]
            n_narrow = n_keep = n_inword = 0
            for o in cv:
                b = o["detail"]["bbox_page_px"]
                w = (b[2] - b[0]) / u
                iw = max([inside(b, x) for x in words] + [0.0])
                idn = max([inside(b, x) for x in dyn] + [0.0])
                if w < MIN_W_SP:
                    n_narrow += 1
                    continue
                n_keep += 1
                n_inword += iw >= 0.5
                picks.append({"plate": plate, "page": p, "pb": b, "w_sp": round(w, 2), "in_word": round(iw, 2), "in_dyn": round(idn, 2),
                              "kind": o["value"], "subject": o["subject"],
                              "caption": "%s p%d %s w%.1f wd%.1f dy%.1f" % (plate[:3], p, o["value"][:3], w, iw, idn)})
            tot.update(ref_bars=(br[1] - br[0] + 1) if br else 0, ref=nref or 0, cv=len(cv), narrow=n_narrow, kept=n_keep, inword=n_inword,
                       det=len(det))
            print("%-7s p%-2d bars %-10s ref wedges %4s | cv rows %3d (narrow, now refused %d; kept %d, of them >=half in a word %d) | detector %d"
                  % (plate, p, "%d-%d" % br if br else "?", nref, len(cv), n_narrow, n_keep, n_inword, len(det)))
        print("%-7s TOTAL %s" % (plate, dict(tot)))
    (HERE / "hairpin_picks.json").write_text(json.dumps(picks, indent=1))
    print("picks", len(picks))


if __name__ == "__main__":
    {"count": count}[sys.argv[1]]()
