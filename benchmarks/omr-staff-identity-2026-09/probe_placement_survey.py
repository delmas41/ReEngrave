#!/usr/bin/env python3
"""Survey how PLACEMENT is encoded across the score library's reference encodings.

PHASE 0 of the staff-identity audit: defines the evidence base for signal "S9"
(placement of dynamics / slurs / ties relative to a braced staff pair).

Measurement only — writes JSON, changes nothing.  Stdlib only (zipfile +
xml.etree), so it runs on the host's python 3.9 with no music21.

    python3 benchmarks/omr-staff-identity-2026-09/probe_placement_survey.py \
        [--limit N] [--out placement-survey.json]

WHAT IT COUNTS, per question:

 1. multi-staff parts   -- <attributes><staves>N, distribution of N
 2. directions          -- placement= / <staff> child / (placement, staff) pairs
 3. direction types     -- the same, split by direction-type child tag
 4. section pairs       -- consecutive parts with the same instrument-name stem
                           ("Flute 1"/"Flute 2"): is a dynamic emitted once or twice?
 5. slurs / ties        -- do start and stop land on different <staff> values?
 6. by source           -- catalog `source` and the encoding software (raw.encoder)

⚠️  This measures ENCODING convention, not printed-page convention.  See the
    caveat printed in the summary.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

MAIN_CHECKOUT = Path("/Users/seanjohnson/Desktop/ReEngrave")
LIBRARY = MAIN_CHECKOUT / "library" / "reference"
CATALOG = MAIN_CHECKOUT / "data" / "score-library" / "catalog.json"
OUT_DEFAULT = Path(__file__).resolve().parent / "placement-survey.json"

# Works behind the scan benchmark's five editions (question 6).
SCAN_BENCHMARK_WORK_IDS = {
    "beethoven--symphony-5": "Litolff (Beethoven 5)",
    "dvorak--symphony-9": "Simrock (Dvorak 9)",
    "brahms--symphony-1": "Breitkopf (Brahms 1)",
    "mahler--symphony-5": "Peters (Mahler 5)",
    "bach--concerto-3": "Peters (Bach Brandenburg 3)",
}

# quantisation of a within-measure position, in quarter notes
QUANT = 48


# --------------------------------------------------------------------------- IO


def read_root_xml(path: Path) -> bytes:
    """Return the MusicXML bytes for a .mxl (zipped) or plain .musicxml file."""
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as z:
            root_name = None
            try:
                container = ET.fromstring(z.read("META-INF/container.xml"))
                rf = container.find(".//rootfile")
                if rf is not None:
                    root_name = rf.get("full-path")
            except (KeyError, ET.ParseError):
                root_name = None
            if not root_name or root_name not in z.namelist():
                cands = [
                    n
                    for n in z.namelist()
                    if not n.startswith("META-INF/")
                    and n.lower().endswith((".xml", ".musicxml"))
                ]
                if not cands:
                    raise ValueError("no xml member in mxl")
                root_name = cands[0]
            return z.read(root_name)
    return path.read_bytes()


def strip_ns(elem: ET.Element) -> None:
    for e in elem.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]


def parse(path: Path) -> ET.Element:
    root = ET.fromstring(read_root_xml(path))
    strip_ns(root)
    return root


# ------------------------------------------------------------------ name stems

ROMAN = re.compile(r"^[ivxl]+$")
_SPLIT = re.compile(r"[\s.,/&+·\-–—()\[\]]+")


def name_stem(name: str) -> str:
    """'Flute 1' / 'Flauto II.' / 'Horn in F 2' -> a comparable stem.

    Strips TRAILING number-ish tokens only; interior words (the key of a horn,
    'in F') are kept, so 'Horn in F 1' and 'Horn in F 2' pair but 'Horn in F 1'
    and 'Horn in Eb 1' do not.
    """
    toks = [t for t in _SPLIT.split(name.strip().lower()) if t]
    while toks:
        t = toks[-1]
        if t.isdigit() or ROMAN.match(t) or t in {"a", "and", "e", "u", "und", "&"}:
            toks.pop()
        else:
            break
    return " ".join(toks)


# ---------------------------------------------------------------- one document


def survey_score(root: ET.Element) -> dict:
    """Walk one score-partwise document; return raw per-file counters."""
    out = {
        "timewise": False,
        "parts": 0,
        "multistaff_parts": 0,
        "staves_hist": collections.Counter(),
        "directions": 0,
        "dir_placement": collections.Counter(),   # above / below / (none)
        "dir_has_staff": 0,
        "dir_has_offset": 0,
        "dir_types": collections.Counter(),
        # (staves, placement, staff) for parts with staves >= 2
        "multistaff_dir_ps": collections.Counter(),
        # same, keyed by (staves, dtype, placement, staff)
        "multistaff_dir_type_ps": collections.Counter(),
        "two_staff_dir_total": 0,
        "two_staff_dir_s1_below": 0,
        "two_staff_dyn_wedge_total": 0,
        "two_staff_dyn_wedge_s1_below": 0,
        "slur_pairs": 0,
        "slur_cross_staff": 0,
        "tied_pairs": 0,
        "tied_cross_staff": 0,
        "slur_unpaired": 0,
        "note_staff_written": 0,
        "notes": 0,
        # question 4
        "section_pairs": 0,
        "pair_dyn_both": 0,
        "pair_dyn_first_only": 0,
        "pair_dyn_second_only": 0,
        "pair_wedge_both": 0,
        "pair_wedge_first_only": 0,
        "pair_wedge_second_only": 0,
    }

    if root.tag == "score-timewise":
        out["timewise"] = True
        return out

    # ---- part-list: id -> printed name, in document order
    order: list = []
    names: dict = {}
    plist = root.find("part-list")
    if plist is not None:
        for sp in plist.findall("score-part"):
            pid = sp.get("id")
            if pid is None:
                continue
            order.append(pid)
            nm = sp.findtext("part-name") or ""
            names[pid] = nm.strip()

    # dynamic/wedge events per part, for question 4
    events: dict = {}

    for part in root.findall("part"):
        pid = part.get("id")
        out["parts"] += 1
        staves = 1
        divisions = 1
        ev = []
        open_slurs: dict = {}
        open_ties: dict = {}

        # first pass for staves count (attributes can appear mid-part)
        for st in part.iter("staves"):
            try:
                staves = max(staves, int((st.text or "1").strip()))
            except ValueError:
                pass
        out["staves_hist"][staves] += 1
        if staves >= 2:
            out["multistaff_parts"] += 1

        for measure in part.findall("measure"):
            mnum = measure.get("number") or ""
            pos = 0  # in divisions
            for el in measure:
                tag = el.tag
                if tag == "attributes":
                    d = el.findtext("divisions")
                    if d:
                        try:
                            divisions = int(float(d.strip()))
                        except ValueError:
                            pass
                    if divisions <= 0:
                        divisions = 1
                elif tag == "note":
                    out["notes"] += 1
                    nstaff = el.findtext("staff")
                    nstaff = nstaff.strip() if nstaff else "1"
                    if el.find("staff") is not None:
                        out["note_staff_written"] += 1
                    notations = el.find("notations")
                    if notations is not None:
                        for slur in notations.iter("slur"):
                            num = slur.get("number") or "1"
                            typ = slur.get("type")
                            if typ == "start":
                                open_slurs[num] = nstaff
                            elif typ == "stop":
                                if num in open_slurs:
                                    out["slur_pairs"] += 1
                                    if open_slurs.pop(num) != nstaff:
                                        out["slur_cross_staff"] += 1
                                else:
                                    out["slur_unpaired"] += 1
                        for tied in notations.iter("tied"):
                            num = tied.get("number") or "1"
                            typ = tied.get("type")
                            if typ == "start":
                                open_ties.setdefault(num, []).append(nstaff)
                            elif typ == "stop":
                                stack = open_ties.get(num)
                                if stack:
                                    out["tied_pairs"] += 1
                                    if stack.pop(0) != nstaff:
                                        out["tied_cross_staff"] += 1
                    if el.find("chord") is None and el.find("grace") is None:
                        dur = el.findtext("duration")
                        if dur:
                            try:
                                pos += int(float(dur.strip()))
                            except ValueError:
                                pass
                elif tag == "backup":
                    d = el.findtext("duration")
                    if d:
                        try:
                            pos -= int(float(d.strip()))
                        except ValueError:
                            pass
                elif tag == "forward":
                    d = el.findtext("duration")
                    if d:
                        try:
                            pos += int(float(d.strip()))
                        except ValueError:
                            pass
                elif tag == "direction":
                    out["directions"] += 1
                    placement = el.get("placement") or "(none)"
                    out["dir_placement"][placement] += 1
                    dstaff_el = el.find("staff")
                    dstaff = (dstaff_el.text or "1").strip() if dstaff_el is not None else "(none)"
                    if dstaff_el is not None:
                        out["dir_has_staff"] += 1
                    if el.find("offset") is not None:
                        out["dir_has_offset"] += 1

                    dtypes = []
                    for dt in el.findall("direction-type"):
                        for child in dt:
                            dtypes.append(child.tag)
                    if not dtypes:
                        dtypes = ["(empty)"]
                    for t in dtypes:
                        out["dir_types"][t] += 1

                    if staves >= 2:
                        out["multistaff_dir_ps"][(staves, placement, dstaff)] += 1
                        for t in dtypes:
                            out["multistaff_dir_type_ps"][(staves, t, placement, dstaff)] += 1
                    if staves == 2:
                        out["two_staff_dir_total"] += 1
                        if dstaff == "1" and placement == "below":
                            out["two_staff_dir_s1_below"] += 1
                        if any(t in ("dynamics", "wedge") for t in dtypes):
                            out["two_staff_dyn_wedge_total"] += 1
                            if dstaff == "1" and placement == "below":
                                out["two_staff_dyn_wedge_s1_below"] += 1

                    # event key for question 4
                    q = round(pos / float(divisions) * QUANT)
                    for dt in el.findall("direction-type"):
                        for child in dt:
                            if child.tag == "dynamics":
                                vals = sorted(c.tag for c in child) or ["?"]
                                ev.append(("dynamics", mnum, q, "|".join(vals)))
                            elif child.tag == "wedge":
                                ev.append(("wedge", mnum, q, child.get("type") or "?"))
        if pid is not None:
            events[pid] = set(ev)

    # ---- question 4: consecutive same-stem parts
    for a, b in zip(order, order[1:]):
        sa, sb = name_stem(names.get(a, "")), name_stem(names.get(b, ""))
        if not sa or len(sa) < 3 or sa != sb:
            continue
        out["section_pairs"] += 1
        ea, eb = events.get(a, set()), events.get(b, set())
        for kind, both, first, second in (
            ("dynamics", "pair_dyn_both", "pair_dyn_first_only", "pair_dyn_second_only"),
            ("wedge", "pair_wedge_both", "pair_wedge_first_only", "pair_wedge_second_only"),
        ):
            ka = {e for e in ea if e[0] == kind}
            kb = {e for e in eb if e[0] == kind}
            out[both] += len(ka & kb)
            out[first] += len(ka - kb)
            out[second] += len(kb - ka)
    return out


# ------------------------------------------------------------------ aggregation

COUNTER_KEYS = (
    "staves_hist",
    "dir_placement",
    "dir_types",
    "multistaff_dir_ps",
    "multistaff_dir_type_ps",
)
SCALAR_KEYS = tuple(
    k
    for k in survey_score(ET.fromstring("<score-partwise/>")).keys()
    if k not in COUNTER_KEYS and k != "timewise"
)


def blank_agg() -> dict:
    a = {k: 0 for k in SCALAR_KEYS}
    a["files"] = 0
    for k in COUNTER_KEYS:
        a[k] = collections.Counter()
    return a


def add(agg: dict, per: dict) -> None:
    agg["files"] += 1
    for k in SCALAR_KEYS:
        agg[k] += per[k]
    for k in COUNTER_KEYS:
        agg[k].update(per[k])


def jsonable(agg: dict) -> dict:
    out = {}
    for k, v in agg.items():
        if isinstance(v, collections.Counter):
            out[k] = {
                ("|".join(str(x) for x in key) if isinstance(key, tuple) else str(key)): n
                for key, n in sorted(v.items(), key=lambda kv: -kv[1])
            }
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------------ main


def load_catalog() -> dict:
    by_path = {}
    if not CATALOG.exists():
        return by_path
    cat = json.load(CATALOG.open())
    for e in cat.get("entries", []):
        if e.get("kind") != "reference":
            continue
        by_path[e["path"]] = e
    return by_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="sweep only the first N files")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args(argv)

    t0 = time.time()
    catalog = load_catalog()
    files = sorted(
        p
        for p in LIBRARY.rglob("*")
        if p.is_file() and p.suffix.lower() in (".mxl", ".musicxml", ".xml")
    )
    if args.limit:
        files = files[: args.limit]

    overall = blank_agg()
    by_source = collections.defaultdict(blank_agg)
    by_encoder = collections.defaultdict(blank_agg)
    by_work = collections.defaultdict(blank_agg)
    failures = collections.Counter()
    timewise = 0
    per_bench_files = collections.defaultdict(list)

    for p in files:
        rel = "reference/" + str(p.relative_to(LIBRARY))
        entry = catalog.get(rel, {})
        source = entry.get("source", "(not in catalog)")
        encoder = (entry.get("raw") or {}).get("encoder") or "(no encoder recorded)"
        work_id = entry.get("work_id", "(unknown)")
        try:
            root = parse(p)
            per = survey_score(root)
        except Exception as exc:  # noqa: BLE001 - counted, not listed
            failures[type(exc).__name__] += 1
            continue
        if per["timewise"]:
            timewise += 1
            continue
        add(overall, per)
        add(by_source[source], per)
        add(by_encoder[_encoder_family(encoder)], per)
        if work_id in SCAN_BENCHMARK_WORK_IDS:
            add(by_work[work_id], per)
            per_bench_files[work_id].append(
                {"path": rel, "source": source, "encoder": encoder}
            )

    elapsed = time.time() - t0
    result = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "library_root": str(LIBRARY),
        "files_found": len(files),
        "files_parsed": overall["files"],
        "parse_failures": dict(failures),
        "score_timewise_skipped": timewise,
        "wall_seconds": round(elapsed, 1),
        "quantisation_per_quarter": QUANT,
        "overall": jsonable(overall),
        "by_source": {k: jsonable(v) for k, v in sorted(by_source.items())},
        "by_encoder_family": {k: jsonable(v) for k, v in sorted(by_encoder.items())},
        "scan_benchmark_works": {
            k: {
                "edition_label": SCAN_BENCHMARK_WORK_IDS[k],
                "reference_files": per_bench_files[k],
                "stats": jsonable(by_work[k]),
            }
            for k in SCAN_BENCHMARK_WORK_IDS
            if k in by_work or per_bench_files[k]
        },
        "caveat": (
            "These are ENCODING conventions in modern digital reference files, "
            "not the conventions of the historical printed editions. Every file "
            "here carries catalog source 'gradus' or 'gradus-assets'."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    print_summary(result)
    print("\nwrote %s" % args.out)
    return 0


def _encoder_family(enc: str) -> str:
    e = enc.strip()
    low = e.lower()
    for fam in ("musescore", "finale", "sibelius", "dolet", "notion", "lilypond", "capella"):
        if fam in low:
            return fam
    if low.startswith("(no encoder"):
        return "(none recorded)"
    return e.split()[0] if e else "(blank)"


def print_summary(r: dict) -> None:
    o = r["overall"]
    p = print
    p("=" * 72)
    p("PLACEMENT SURVEY — %s files parsed of %s found in %.1fs"
      % (o["files"], r["files_found"], r["wall_seconds"]))
    if r["parse_failures"]:
        p("parse failures: %s" % r["parse_failures"])
    p("score-timewise skipped: %d" % r["score_timewise_skipped"])
    p("")
    p("[1] PARTS: %d parts, %d multi-staff (>=2)" % (o["parts"], o["multistaff_parts"]))
    p("    staves-per-part: %s" % o["staves_hist"])
    p("")
    p("[2] DIRECTIONS: %d total" % o["directions"])
    p("    placement=: %s" % o["dir_placement"])
    p("    with explicit <staff> child: %d (%.1f%%)"
      % (o["dir_has_staff"], 100.0 * o["dir_has_staff"] / max(1, o["directions"])))
    p("    with <offset> child:         %d" % o["dir_has_offset"])
    p("    2-staff parts: %d directions, %d are staff=1 placement=below (%.1f%%)"
      % (o["two_staff_dir_total"], o["two_staff_dir_s1_below"],
         100.0 * o["two_staff_dir_s1_below"] / max(1, o["two_staff_dir_total"])))
    p("      of those, dynamics/wedge: %d total, %d staff=1 below (%.1f%%)"
      % (o["two_staff_dyn_wedge_total"], o["two_staff_dyn_wedge_s1_below"],
         100.0 * o["two_staff_dyn_wedge_s1_below"] / max(1, o["two_staff_dyn_wedge_total"])))
    p("")
    p("[3] DIRECTION TYPES: %s" % _top(o["dir_types"], 12))
    p("    (staves|placement|staff) on multi-staff parts, top 12:")
    for k, n in list(o["multistaff_dir_ps"].items())[:12]:
        p("      %-28s %d" % (k, n))
    p("    (staves|type|placement|staff) for dynamics/wedge, top 12:")
    shown = 0
    for k, n in o["multistaff_dir_type_ps"].items():
        if "|dynamics|" in k or "|wedge|" in k:
            p("      %-34s %d" % (k, n))
            shown += 1
            if shown >= 12:
                break
    p("")
    p("[4] SECTION PAIRS (consecutive parts, same name stem): %d" % o["section_pairs"])
    p("    dynamics: both=%d  first-only=%d  second-only=%d"
      % (o["pair_dyn_both"], o["pair_dyn_first_only"], o["pair_dyn_second_only"]))
    p("    wedges:   both=%d  first-only=%d  second-only=%d"
      % (o["pair_wedge_both"], o["pair_wedge_first_only"], o["pair_wedge_second_only"]))
    p("")
    p("[5] SLURS / TIES")
    p("    slur start/stop pairs: %d, cross-staff: %d (%.2f%%), unpaired stops: %d"
      % (o["slur_pairs"], o["slur_cross_staff"],
         100.0 * o["slur_cross_staff"] / max(1, o["slur_pairs"]), o["slur_unpaired"]))
    p("    tied start/stop pairs: %d, cross-staff: %d (%.2f%%)"
      % (o["tied_pairs"], o["tied_cross_staff"],
         100.0 * o["tied_cross_staff"] / max(1, o["tied_pairs"])))
    p("    notes: %d, of which carry an explicit <staff>: %d (%.1f%%)"
      % (o["notes"], o["note_staff_written"],
         100.0 * o["note_staff_written"] / max(1, o["notes"])))
    p("")
    p("[6] BY SOURCE")
    for src, s in r["by_source"].items():
        p("    %-16s files=%-5d dirs=%-7d staff-child=%.1f%%  2st s1-below=%.1f%%"
          % (src, s["files"], s["directions"],
             100.0 * s["dir_has_staff"] / max(1, s["directions"]),
             100.0 * s["two_staff_dir_s1_below"] / max(1, s["two_staff_dir_total"])))
    p("    BY ENCODER FAMILY")
    for enc, s in r["by_encoder_family"].items():
        p("    %-18s files=%-5d dirs=%-7d staff-child=%.1f%%  2st s1-below=%.1f%%"
          % (enc, s["files"], s["directions"],
             100.0 * s["dir_has_staff"] / max(1, s["directions"]),
             100.0 * s["two_staff_dir_s1_below"] / max(1, s["two_staff_dir_total"])))
    p("    SCAN-BENCHMARK WORKS")
    for wid, w in r["scan_benchmark_works"].items():
        s = w["stats"]
        p("    %-24s (%s) files=%d parts=%d multistaff=%d dirs=%d staff-child=%d"
          % (wid, w["edition_label"], s["files"], s["parts"],
             s["multistaff_parts"], s["directions"], s["dir_has_staff"]))
    p("")
    p("CAVEAT: %s" % r["caveat"])
    p("=" * 72)


def _top(d: dict, n: int) -> str:
    return ", ".join("%s=%d" % (k, v) for k, v in list(d.items())[:n])


if __name__ == "__main__":
    sys.exit(main())
