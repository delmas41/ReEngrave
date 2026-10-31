"""ROADMAP 2.223: Brahms p0 hand truth for arcs bound to their notes, scored on the EXPORTED file (a lane_report work dir).

    python3 benchmarks/omr-arc-binding-2026-10/p0_spans.py DIR/work [--arms off,on]

A written tie/slur is the pair (start note, stop note) the MusicXML joins: ties by `<tie type=start/stop>` on one pitch in one
part, slurs by `<slur number=..>`. Each note is placed by its `rg` glyph key (the traced export) on its GATHER page box. A truth
arc (Sean's p0 boxes, `data/hand-truth/pages/imslp317803/0.json`) is BOUND RIGHT when one written span of the same staff
(the truth box's cell id `sS-stT-mM`) starts on a note whose head lies within REACH staff spaces in x of the truth box's left
end and stops on one within REACH of its right end, and has the truth's kind. A written span matching no truth arc's two ends
is counted `no_truth`. Ends only: whether the head is the right one of a chord is not asked (the hand truth names no head).

Hairpins: p0 holds none (the truth's classes, 2026-10-31), so this scores arcs only; hairpins are proved by tiles.
"""
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
TRUTH = ROOT / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json"
SP = 32.0          # Brahms staff space, px at 600 dpi (lane_report.PLATES)
REACH = 2.5        # spaces: a slur drawn to a stem tip ends ~2-3 spaces from its head (omr-arc-recovery s6)


def boxes_of(mini: pathlib.Path):
    out = {}
    for o in json.loads(mini.read_text())["observations"]:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and o["subject"].startswith("glyph/0/"):
            out[o["subject"]] = [float(v) for v in b]
    return out


def spans(xml: str, boxes):
    """[(kind, staff key 'sys/staff', start box, stop box)] for every written tie and slur on page 0."""
    root = ET.fromstring(xml)
    out = []
    for part in root.iter("part"):
        open_ties = {}
        open_slurs = {}
        for m in part.findall("measure"):
            for el in m.iter("note"):
                rg = el.get("rg") or ""
                b = boxes.get(rg)
                p = el.find("pitch")
                pitch = None if p is None else (p.findtext("step"), p.findtext("octave"), p.findtext("alter"))
                for t in el.findall("tie"):
                    if t.get("type") == "stop" and pitch in open_ties:
                        a = open_ties.pop(pitch)
                        out.append(("tie", a, (rg, b)))
                for t in el.findall("tie"):
                    if t.get("type") == "start":
                        open_ties[pitch] = (rg, b)
                n = el.find("notations")
                for s in ([] if n is None else n.findall("slur")):
                    num = s.get("number") or "1"
                    if s.get("type") == "start":
                        open_slurs[num] = (rg, b)
                    elif s.get("type") == "stop" and num in open_slurs:
                        out.append(("slur", open_slurs.pop(num), (rg, b)))
    res = []
    for kind, (ra, ba), (rz, bz) in out:
        if not ra.startswith("glyph/0/") or ba is None or bz is None:
            continue
        sa = "/".join(ra.split("/")[2:4])
        res.append((kind, sa, ba, bz))
    return res


def truth_arcs():
    d = json.loads(TRUTH.read_text())
    out = []
    for b in d["boxes"]:
        if b.get("cls") not in ("tie", "slur"):
            continue
        c = (b.get("cell_id") or "").split("-")
        st = "%s/%s" % (c[0][1:], c[1][2:])
        out.append((b["cls"], st, b["rect"], b["id"]))
    return out


def score(work: pathlib.Path, arm: str):
    xml = (work / ("brahms.%s.musicxml" % arm)).read_text()
    boxes = boxes_of(work / ("brahms.%s.mini-record.json" % arm))
    written = spans(xml, boxes)
    truth = truth_arcs()
    used = set()
    res = {"tie": [0, 0, 0], "slur": [0, 0, 0]}        # truth n, bound right, bound wrong kind
    for kind, st, r, _id in truth:
        res[kind][0] += 1
        best = None
        for i, (wk, wst, ba, bz) in enumerate(written):
            if wst != st or i in used:
                continue
            ca, cz = (ba[0] + ba[2]) / 2, (bz[0] + bz[2]) / 2
            if abs(ca - r[0]) <= REACH * SP and abs(cz - r[2]) <= REACH * SP:
                if best is None or wk == kind:
                    best = (i, wk)
        if best is not None:
            used.add(best[0])
            res[kind][1 if best[1] == kind else 2] += 1
    nt = {"tie": 0, "slur": 0}
    for i, (wk, *_r) in enumerate(written):
        if i not in used:
            nt[wk] += 1
    w = {"tie": sum(1 for s in written if s[0] == "tie"), "slur": sum(1 for s in written if s[0] == "slur")}
    return res, nt, w


def main(argv):
    work = pathlib.Path(argv[0])
    arms = (argv[2] if len(argv) > 2 and argv[1] == "--arms" else "off,on").split(",")
    for arm in arms:
        res, nt, w = score(work, arm)
        print("%-4s " % arm + "  ".join(
            "%ss: truth %d, bound right %d, other kind %d; written %d, matching no truth %d" % (
                k, res[k][0], res[k][1], res[k][2], w[k], nt[k]) for k in ("tie", "slur")))


if __name__ == "__main__":
    main(sys.argv[1:])
