"""ROADMAP 2.188 -- THE ONE SHARED LANE REPORT (docs/measuring.md §0, Sean 2026-10-21).

    python3 -m tools.omr.staged.lane_report --flag OMR_X [--flag OMR_Y=2] [--plates litolff,brahms]
                                            [--from auto|adjudicate|gather] --out DIR
    python3 -m tools.omr.staged.lane_report sample [--force]     # (re)draw the frozen sample; the committed
                                                                  # benchmarks/lane-report/sample.json is the truth

What it does, on the FROZEN PAGE SAMPLE (about 8 pages per plate, drawn once at random, seed in the file):

  1. runs the tree OFF and ON through EXPORT on those pages -- the same tree, same inputs, one fresh process per
     (plate, arm) so an import-time flag read cannot hide a difference;
  2. prints per plate what changed in the EXPORTED MusicXML, by kind (gained / lost / changed), red bars, and an
     OFF-reproduces-the-record control;
  3. scores Sean's judged answers (tools.omr.staged.judged) OFF and ON and lists every right -> wrong;
  4. writes a 12-tile blind sheet (about 9 drawn at random from the changed symbols, stratified by kind, about 3
     unchanged controls), a NEUTRAL ORANGE box, one sheet PNG + single tiles, the key in a separate JSON.

WHICH STAGE IS RE-RUN. `--from adjudicate` (the default for a flag read in ADJUDICATE..EXPORT) replays the saved
GATHER rows of the 20261020-night record (sliced per page, streamed) through ADJUDICATE, GROUPS, EVALUATE, INFER, the
second EVALUATE and EXPORT. A flag that acts in GATHER cannot show there (the saved rows ARE the gather): `--from
auto` finds the flag's name in the GATHER modules and re-gathers those pages for both arms (the detector, minutes
per page) -- and REFUSES `--from adjudicate` for such a flag rather than report a clean zero (CLAUDE rule 7).

WHAT "THE EXPORTED FILE" MEANS HERE. The MusicXML `export.to_musicxml` writes, parsed: every written note / rest
(with the glyph key it was written from, so it has a place on the page), and on each note its accidental, dots,
flag (a value shorter than a quarter with no beam), beam, tie, slur, articulation, fermata, ornament, tuplet, blue
GUESSED mark; plus the directions (dynamics, words, wedges) and the clef/key/time in force. Two arms' notes are
paired by page position (a chord member has its own box), never by list order.

THE CONTROLS THAT CAN FAIL. `--allow-unknown-flag` is needed for a flag the tree does not mention (so a typo cannot
report a clean zero). The OFF arm's duration / rest verdicts are compared with the saved record's own; a mismatch is
printed LOUDLY. The tracing of glyph keys into the XML raises when the note count disagrees (`TraceMismatch`).
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from fractions import Fraction
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

DERIVED_CHECK = False
ROOT = pathlib.Path(__file__).resolve().parents[3]
SAMPLE_PATH = pathlib.Path(os.environ.get("LANE_REPORT_SAMPLE") or ROOT / "benchmarks" / "lane-report" / "sample.json")  # env: a one-page control (2.189)
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
RECORDS = LIB / "_shared-records"
DETECTOR_CACHE: Optional[pathlib.Path] = RECORDS / "detector-cache"      # ROADMAP 2.189: OFF and ON share it; None = no cache
CELL_MAP: Optional[pathlib.Path] = None     # ROADMAP 2.231: --cell-map DIR = both gather arms LOAD the master's cells; None = cut fresh
CELL_MAP_ROOT = RECORDS / "cell-maps"
LOCK = RECORDS / ".record-load.lock"
ORANGE = (255, 140, 0)
#: The night record the frozen sample replays by default (ROADMAP 2.244: it was 20261020-night, and every lane had to
#: remember `--tag 20261029-night`). Move it when Sean's overnight lands a newer one; `benchmarks/lane-report/sample.json`
#: `record_tag` must say the same (a test holds them together).
DEFAULT_TAG = "20261029-night"

#: The acceptance scan plates (docs/measuring.md §1). `unit` = one staff space in px at 600 dpi (tile window and the
#: pairing tolerance).
PLATES: Dict[str, Dict[str, Any]] = {
    "litolff": dict(id="beethoven5-litolff", record="beethoven5-litolff-mvt1-whole-{tag}.record.json", unit=15.75,
                    pdf="editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
    "brahms": dict(id="brahms1-breitkopf", record="brahms1-breitkopf-mvt1-whole-{tag}.record.json", unit=32.0,
                   pdf="editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"),
}
#: Stored verdicts kept in a slice: the control (OFF vs the record) and Sean's judged answers read these.
STORED_QUANTITIES = ("duration", "rest_is_not_a_rest", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest",
                     "notehead_is_an_eighth_rest", "arc_kind")
#: Modules whose code runs in GATHER: a flag named in one of them cannot show in an ADJUDICATE-only replay.
GATHER_MODULES = ("gather.py", "positions.py", "arcs_system.py", "detector_views.py", "second_hollow.py",
                  "stem_end_heads.py", "legacy.py")
SHORT = ("eighth", "16th", "32nd", "64th", "128th")
#: kinds, in print order. Hosts are the written notes/rests; the rest hang off a note or a bar.
KIND_ORDER = ("note", "rest", "accidental", "dot", "flag", "beam", "tie", "slur", "articulation", "fermata",
              "ornament", "tuplet", "value", "pitch", "blue", "dynamic", "wedge", "words", "clef", "key", "time")
LOCATED_KINDS = frozenset(KIND_ORDER) - {"clef", "key", "time"}


class TraceMismatch(RuntimeError):
    """The XML holds a different number of notes than the events it was written from."""


# ───────────────────────────── 1. the frozen sample ─────────────────────────────

def page_of(subject: Optional[str]) -> Optional[int]:
    """The page a row belongs to, from its subject key; None for a document-level row (kept in every slice)."""
    p = (subject or "").split("/")
    if len(p) >= 2 and p[0] in ("glyph", "cell", "staff", "system", "mark", "page", "mg", "measure") \
            and p[1].lstrip("-").isdigit():
        return int(p[1])
    return None


@contextlib.contextmanager
def record_lock(path: pathlib.Path = LOCK) -> Iterator[None]:
    """One big-record reader at a time on the box (the same lock the probes use)."""
    while True:
        try:
            os.mkdir(path)
            break
        except FileExistsError:
            time.sleep(10)
    try:
        yield
    finally:
        os.rmdir(path)


def record_path(plate: str, tag: str) -> pathlib.Path:
    return RECORDS / PLATES[plate]["record"].format(tag=tag)


def draw_sample(candidates: Dict[str, List[int]], seed: int, n: int) -> Dict[str, List[int]]:
    """`n` pages per plate, at random, from the sorted candidates; one `Random(seed)` walked plate by plate in
    PLATES order. Nothing is excluded by hand."""
    rng = random.Random(seed)
    out: Dict[str, List[int]] = {}
    for plate in PLATES:
        cands = sorted(candidates[plate])
        out[plate] = sorted(rng.sample(cands, min(n, len(cands))))
    return out


def candidate_pages(plate: str, tag: str) -> List[int]:
    """Every page the record holds staves for (one streamed pass over the observations; ~seconds)."""
    from .judged import iter_array
    pages = set()
    for o in iter_array(record_path(plate, tag), "observations"):
        if o.get("quantity") == "staff_lines":
            pg = page_of(o.get("subject"))
            if pg is not None:
                pages.add(pg)
    return sorted(pages)


def make_sample(seed: int = 2188, n: int = 8, tag: str = DEFAULT_TAG) -> Dict[str, Any]:
    cands = {p: candidate_pages(p, tag) for p in PLATES}
    pages = draw_sample(cands, seed, n)
    return {
        "what": "ROADMAP 2.188 frozen page sample (docs/measuring.md §0): pages drawn ONCE at random from every page of "
                "the record that holds staves; nothing excluded by hand. Re-draw only by Sean's word (`sample --force`).",
        "seed": seed, "n_per_plate": n, "record_tag": tag,
        "method": "random.Random(seed); for plate in (litolff, brahms): sorted(rng.sample(sorted(candidates), n))",
        "context": "each plate also loads its OPENING page (the first candidate): the meter / key / clef printed there are "
                   "inherited by every later bar (a change HOLDS until the printed return), and a slice without it cannot "
                   "size a whole rest. Context pages are loaded but never counted.",
        "plates": {p: {"candidates": cands[p], "pages": pages[p], "context_pages": [cands[p][0]]} for p in PLATES},
    }


def loaded_pages(sample: Dict[str, Any], plate: str) -> List[int]:
    """The sample pages plus the plate's context page(s): what a slice holds."""
    pl = sample["plates"][plate]
    return sorted(set(pl["pages"]) | set(pl.get("context_pages") or ()))


def load_sample(path: pathlib.Path = SAMPLE_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text())


def check_tag(tag: str, plates: Sequence[str], sample: Dict[str, Any]) -> None:
    """ROADMAP 2.244: a stale tag RAISES. `tag` must name, for every plate, the night record (or an already cut slice dir that
    holds every page the sample loads); a lane that forgot `--tag` once replayed a month-old night against today's tree."""
    if os.path.isdir(tag):
        return
    for p in plates:
        if record_path(p, tag).exists():
            continue
        stamp = slice_dir(p, tag) / "stamp.json"
        if stamp.exists() and set(loaded_pages(sample, p)) <= set(json.loads(stamp.read_text()).get("pages", ())):
            continue
        raise SystemExit("tag %r: no night record %s and no slice dir %s holding the sample's pages for %s -- a stale or mistyped "
                         "--tag (default %s)" % (tag, record_path(p, tag).name, slice_dir(p, tag).name, p, DEFAULT_TAG))


# ───────────────────────────── 2. per-page slices ─────────────────────────────

def slice_dir(plate: str, tag: str) -> pathlib.Path:
    """The per-page slices of the night record `tag`; or, when `tag` is an existing DIRECTORY (2.190), that directory's `<plate>/` slices as built."""
    if os.path.isdir(tag):
        return pathlib.Path(tag) / plate
    return RECORDS / ("lane-report-slices-%s" % tag) / plate


def ensure_slices(plate: str, pages: Sequence[int], tag: str, log=print) -> pathlib.Path:
    """The saved night record cut to `pages` (+ every document-level row), in ONE streamed pass per array; reused
    while the page list and the record file are unchanged. Never loads a record whole."""
    from .judged import iter_array
    d = slice_dir(plate, tag)
    if os.path.isdir(tag):      # slices built by hand (2.190 build_slices): used as they stand
        return d
    rp = record_path(plate, tag)
    st = rp.stat()
    stamp = {"pages": sorted(pages), "size": st.st_size, "mtime": int(st.st_mtime)}
    if (d / "stamp.json").exists() and json.loads((d / "stamp.json").read_text()) == stamp:
        return d
    d.mkdir(parents=True, exist_ok=True)
    keep = set(pages)
    t0 = time.time()
    with record_lock():
        for kind in ("observations", "abstentions", "verdicts"):
            n = 0
            with open(d / ("%s.jsonl" % kind), "w") as fh:
                for it in iter_array(rp, kind):
                    if kind == "verdicts" and it.get("quantity") not in STORED_QUANTITIES:
                        continue
                    pg = page_of(it.get("subject"))
                    if pg is None or pg in keep:
                        fh.write(json.dumps(it, default=str) + "\n")
                        n += 1
            log("  slice %s %s: %d rows kept (%.0fs)" % (plate, kind, n, time.time() - t0))
    (d / "stamp.json").write_text(json.dumps(stamp))
    return d


def load_slices(d: pathlib.Path) -> Dict[str, List[dict]]:
    out = {}
    for kind in ("observations", "abstentions", "verdicts"):
        with open(d / ("%s.jsonl" % kind)) as fh:
            out[kind] = [json.loads(line) for line in fh]
    return out


# ───────────────────────────── 3. the flag and the stage ─────────────────────────────

def parse_flags(specs: Sequence[str]) -> List[Tuple[str, str, str]]:
    """`NAME` -> (NAME, off "0", on "1"); `NAME=V` -> on V; `NAME=OFFV:ONV` -> both."""
    out = []
    for s in specs:
        name, _, v = s.partition("=")
        off, on = "0", "1"
        if v:
            off, on = (v.split(":", 1) if ":" in v else ("0", v))
        out.append((name.strip(), off, on))
    return out


def flag_homes(flag: str, root: pathlib.Path = ROOT / "tools" / "omr") -> List[str]:
    """Source files (relative to tools/omr) whose text names the flag, tests excluded."""
    hits = []
    for p in sorted(root.rglob("*.py")):
        if "tests" in p.parts or p.name == "lane_report.py":
            continue
        try:
            if flag in p.read_text(errors="ignore"):
                hits.append(str(p.relative_to(root)))
        except OSError:
            pass
    return hits


def acts_in_gather(homes: Iterable[str]) -> bool:
    return any(pathlib.PurePath(h).name in GATHER_MODULES and "staged" in pathlib.PurePath(h).parts for h in homes)


def decide_from(requested: str, flags: Sequence[Tuple[str, str, str]], allow_unknown: bool,
                replay_gathered: bool = False) -> Tuple[str, List[str]]:
    """`(from, notes)`. Refuses what would report a clean zero by construction. `replay_gathered` (2.190): the replayed record (`--tag`) was
    GATHERED with the GATHER-side flags already on and those flags are only MEASURING (the OFF arm ignores what they filed), so a flag homed in
    GATHER may be replayed from ADJUDICATE; the claim is the caller's and is printed in the notes."""
    notes: List[str] = []
    gather = False
    for name, _off, _on in flags:
        homes = flag_homes(name)
        if not homes:
            if not allow_unknown:
                raise SystemExit("flag %s is named nowhere in tools/omr: refusing (a typo would report a clean zero). "
                                 "--allow-unknown-flag for the can-it-fail control." % name)
            notes.append("%s: named nowhere in the tree (--allow-unknown-flag)" % name)
            continue
        g = acts_in_gather(homes)
        gather = gather or g
        notes.append("%s: read in %s -> %s" % (name, ", ".join(homes[:4]) + (" ..." if len(homes) > 4 else ""),
                                              "GATHER" if g else "ADJUDICATE..EXPORT"))
    if replay_gathered:
        if requested == "gather":
            raise SystemExit("--replay-gathered replays a record gathered with the flags on: use --from adjudicate (or auto)")
        notes.append("REPLAY OF A RECORD GATHERED WITH THE GATHER-SIDE FLAGS ON (--replay-gathered): the arms differ only in ADJUDICATE..EXPORT")
        return "adjudicate", notes
    if requested == "auto":
        return ("gather" if gather else "adjudicate"), notes
    if requested == "adjudicate" and gather:
        raise SystemExit("a flag that acts in GATHER cannot show in an ADJUDICATE replay of saved GATHER rows (it would "
                         "report a clean zero). Use --from gather (or auto). " + "; ".join(notes))
    return requested, notes


# ───────────────────────────── 4. the traced export ─────────────────────────────

_NOTE_OPEN = re.compile(r"\s*<note[ >]")


@contextlib.contextmanager
def traced_export() -> Iterator[None]:
    """Make `export._measure_events_xml` stamp every `<note>` with `rg="<glyph key>"` -- the written note's own
    notehead / rest key -- so a symbol in the FILE has a place on the PAGE. Raises `TraceMismatch` when the counts
    disagree (the control: a wrapper that mis-aligned would stamp the wrong keys)."""
    from . import export as E
    orig = E._measure_events_xml

    def traced(events, divisions, counters, voice=1, doubled=False):
        out, units = orig(events, divisions, counters, voice=voice, doubled=doubled)
        glyphs: List[Optional[str]] = []
        for ev in events:
            if ev.get("kind") == "rest":
                glyphs.append(ev.get("glyph") or (ev.get("rest") or {}).get("glyph"))
            else:
                glyphs.extend(h.get("glyph") for h in (ev.get("noteheads") or []))
        idx = [i for i, s in enumerate(out) if _NOTE_OPEN.match(s)]
        if len(idx) != len(glyphs):
            raise TraceMismatch("%d <note> elements vs %d events' heads/rests" % (len(idx), len(glyphs)))
        for i, g in zip(idx, glyphs):
            if g:
                out[i] = out[i].replace("<note", '<note rg="%s"' % g, 1)
        return out, units

    E._measure_events_xml = traced
    try:
        yield
    finally:
        E._measure_events_xml = orig


def glyph_boxes(observations: Iterable[dict]) -> Dict[str, dict]:
    """`{glyph key: {page, box, cls}}`: the page box of every glyph key -- the `glyph_box` row (the detector's box) first;
    a key with none (the unboxed ink a rest was read off, key index >= 350000) takes the first row of any quantity
    that carries a `bbox_page_px` (the ink cluster GATHER measured)."""
    out: Dict[str, dict] = {}
    spare: Dict[str, dict] = {}
    for o in observations:
        sub = o.get("subject") or ""
        if not sub.startswith("glyph/"):
            continue
        b = (o.get("detail") or {}).get("bbox_page_px")
        if not (isinstance(b, list) and len(b) == 4):
            continue
        v = o.get("value")
        rec = dict(page=page_of(sub), box=[float(x) for x in b], cls=(v[0] if isinstance(v, list) and v else None))
        if o.get("quantity") == "glyph_box":
            out.setdefault(sub, rec)
        else:
            spare.setdefault(sub, rec)
    for k, v in spare.items():
        out.setdefault(k, v)
    return out


def own_direction_box(d: dict, boxes: Dict[str, dict]) -> Optional[list]:
    """ROADMAP 2.215: the box of a direction's OWN ink, not its host note's (2.213 tiles 1, 2, 3, 9, 11 boxed a note and
    never showed the change). A dynamic is the union of the `dynamic*` glyphs of the host's cell whose letters spell its
    value; our own bar-check words ("does not add up...") have no ink on the page, so no box (no tile); other words
    have no glyph of their own in the record, so the host box stands and the item is marked `box_is_host`."""
    if d.get("kind") == "words" and str(d.get("value", "")).startswith("does not add up"):
        d["no_ink"] = True
        return None
    rg = d.get("rg") or ""
    if d.get("kind") == "dynamic":
        pre = "/".join(rg.split("/")[:5]) + "/"
        want = str(d.get("value", "")).lower()
        got = [b for k, b in boxes.items() if k.startswith(pre) and (b.get("cls") or "").startswith("dynamic")
               and (b["cls"][7:].lower() in want) and b["page"] == d.get("page")]
        if got and "".join(sorted(b["cls"][7:].lower() for b in got)) == "".join(sorted(want)):
            return [min(b["box"][0] for b in got), min(b["box"][1] for b in got),
                    max(b["box"][2] for b in got), max(b["box"][3] for b in got)]
    if d.get("kind") in ("words", "dynamic"):
        d["box_is_host"] = True
    return d.get("box")


def parse_symbols(xml: str, boxes: Dict[str, dict]) -> Dict[str, Any]:
    """The written file as symbols: `hosts` (notes / rests with their sub-marks), `loose` (directions anchored to the
    next note, and attributes) -- each with page and centre where the glyph key gives one."""
    root = ET.fromstring(xml)
    hosts: List[dict] = []
    loose: List[dict] = []
    divisions = 1

    def place(rg: Optional[str]) -> Tuple[Optional[int], Optional[float], Optional[float], Optional[list]]:
        b = boxes.get(rg or "")
        if not b:
            return None, None, None, None
        bx = b["box"]
        return b["page"], (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, bx

    for part in root.iter("part"):
        pid = part.get("id")
        for m in part.findall("measure"):
            mnum = m.get("number")
            pending: List[dict] = []
            pos, last_onset = 0, 0      # ROADMAP 2.211: the written onset, in divisions, of each note
            for el in m:
                tag = el.tag
                if tag == "backup":
                    pos -= int(el.findtext("duration") or 0)
                elif tag == "forward":
                    pos += int(el.findtext("duration") or 0)
                if tag == "attributes":
                    if el.findtext("divisions"):
                        divisions = int(el.findtext("divisions"))
                    for c in el.findall("clef"):
                        loose.append(dict(kind="clef", part=pid, measure=mnum, value="%s%s" % (c.findtext("sign"), c.findtext("line"))))
                    for c in el.findall("key"):
                        loose.append(dict(kind="key", part=pid, measure=mnum, value=c.findtext("fifths")))
                    for c in el.findall("time"):
                        loose.append(dict(kind="time", part=pid, measure=mnum, value="%s/%s" % (c.findtext("beats"), c.findtext("beat-type"))))
                elif tag == "direction":
                    for dt in el.findall("direction-type"):
                        for d in dt.findall("dynamics"):
                            for c in d:
                                pending.append(dict(kind="dynamic", part=pid, measure=mnum, value=c.tag))
                        for w in dt.findall("words"):
                            if (w.text or "").strip():
                                pending.append(dict(kind="words", part=pid, measure=mnum, value=w.text.strip()))
                        for w in dt.findall("wedge"):
                            if w.get("type") != "stop":
                                pending.append(dict(kind="wedge", part=pid, measure=mnum, value=w.get("type")))
                        for w in dt.findall("other-direction"):
                            txt = (w.text or "").strip()
                            if txt and not txt.startswith("reengrave:guessed"):
                                pending.append(dict(kind="words", part=pid, measure=mnum, value=txt))
                elif tag == "note":
                    rg = el.get("rg")
                    if el.find("chord") is not None:
                        onset_div = last_onset
                    else:
                        onset_div = last_onset = pos
                        if el.find("grace") is None:
                            pos += int(el.findtext("duration") or 0)
                    onset = str(Fraction(onset_div, divisions))
                    pg, cx, cy, bx = place(rg)
                    is_rest = el.find("rest") is not None
                    notations = el.find("notations")
                    sub: Dict[str, List[str]] = collections.defaultdict(list)
                    acc = el.findtext("accidental")
                    if acc:
                        sub["accidental"].append(acc)
                    sub["dot"].extend(["."] * len(el.findall("dot")))
                    typ = el.findtext("type") or "?"
                    beams = [b.text for b in el.findall("beam")]
                    if beams:
                        sub["beam"].append("/".join(beams))
                    elif typ in SHORT and not is_rest:
                        sub["flag"].append(typ)
                    for t in el.findall("tie"):
                        sub["tie"].append(t.get("type"))
                    tm = el.find("time-modification")
                    if tm is not None:
                        sub["tuplet"].append("%s:%s" % (tm.findtext("actual-notes"), tm.findtext("normal-notes")))
                    guessed = el.get("color") is not None
                    if notations is not None:
                        for s in notations.findall("slur"):
                            sub["slur"].append(s.get("type"))
                        for a in notations.findall("articulations"):
                            for c in a:
                                sub["articulation"].append(c.tag)
                        for _f in notations.findall("fermata"):
                            sub["fermata"].append("fermata")
                        for o in notations.findall("ornaments"):
                            for c in o:
                                sub["ornament"].append(c.tag)
                    pitch = None
                    p = el.find("pitch")
                    if p is not None:
                        pitch = "%s%s%s" % (p.findtext("step"), p.findtext("alter") or "", p.findtext("octave"))
                    kind = "rest" if is_rest else "note"
                    if pg is None:
                        # written, but not from a glyph with a box on the page (padding rests, unread-bar gaps): it has
                        # no place, so it is counted per bar like a direction, never paired by position
                        loose.append(dict(kind=kind, part=pid, measure=mnum, value="%s %s" % (typ, pitch or "")))
                        for d in pending:
                            loose.append(d)
                        pending = []
                        continue
                    hosts.append(dict(kind=kind, part=pid, measure=mnum, rg=rg, page=pg, cx=cx, cy=cy,
                                      box=bx, type=typ, pitch=pitch, blue=guessed, sub=dict(sub),
                                      chord=el.find("chord") is not None, onset=onset, voice=el.findtext("voice")))
                    for d in pending:
                        d.update(page=pg, cx=cx, cy=cy, box=bx, rg=rg)
                        ob = own_direction_box(d, boxes)
                        if ob is not bx:
                            d["box"] = ob
                            if ob:
                                d["cx"], d["cy"] = (ob[0] + ob[2]) / 2, (ob[1] + ob[3]) / 2
                        loose.append(d)
                    pending = []
            for d in pending:      # a direction with no note after it in its bar: counted, no place on the page
                loose.append(d)
    return dict(hosts=hosts, loose=loose)


# ───────────────────────────── 5. the arm worker ─────────────────────────────

def _live(verdicts: Iterable[dict], quantities: Sequence[str]) -> Dict[Tuple[str, str], dict]:
    chains: Dict[Tuple[str, str], List[dict]] = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] in quantities and str(v["subject"]).startswith("glyph/"):
            chains[(v["subject"], v["quantity"])].append(v)
    out = {}
    for k, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[k] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def _count(x: Any) -> Any:
    """A report figure that is an int, or a dict carrying its count as `n`."""
    return x.get("n") if isinstance(x, dict) else x


_ROW_ID = re.compile(r"\b(?:obs|abs|ver):\d+")


def _brief(v: dict) -> list:
    """What a verdict SAYS, with row ids blanked (a slice renumbers its rows densely, so `shared_stem: obs:064845` and
    `obs:048953` name the same stem)."""
    return [v.get("outcome"), _ROW_ID.sub("ID", json.dumps(v.get("value"), sort_keys=True, default=str)), v.get("reason")]


def reparse_arm(plate: str, arm: str, tag: str, work: pathlib.Path, count_pages: Sequence[int]) -> Dict[str, Any]:
    """Development convenience (`--reuse`): re-read an arm's saved MusicXML with the CURRENT parser; the verdict-side
    numbers (control, red bars) are kept from the arm's own run."""
    old = json.loads((work / ("%s.%s.symbols.json" % (plate, arm))).read_text())
    rec = load_slices(slice_dir(plate, tag))
    sym = parse_symbols((work / ("%s.%s.musicxml" % (plate, arm))).read_text(), glyph_boxes(rec["observations"]))
    cp = set(count_pages)
    old["hosts"] = [h for h in sym["hosts"] if h["page"] is None or h["page"] in cp]
    old["loose"] = [d for d in sym["loose"] if d.get("page") is None or d["page"] in cp]
    return old


def run_arm(plate: str, arm: str, flags: Sequence[Tuple[str, str, str]], mode: str, tag: str,
            work: pathlib.Path, count_pages: Sequence[int], gather_record: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """One (plate, arm) in THIS process: set the flags, replay or load, export traced, write the arm's files."""
    from . import export as E
    from .judged import _QUANTITIES as JQ
    for name, off, on in flags:
        os.environ[name] = on if arm == "on" else off
    t0 = time.time()
    stored: Dict[Tuple[str, str], dict] = {}
    gather_prov: Dict[str, Any] = {}
    if mode == "adjudicate":
        from .review import rerun as RR
        rec = load_slices(slice_dir(plate, tag))
        stored = _live(rec["verdicts"], ("duration", "rest_is_not_a_rest"))
        boxes = glyph_boxes(rec["observations"])
        glyph_obs = [o for o in rec["observations"] if o.get("quantity") == "glyph_box"]
        rec["verdicts"] = []
        log, _ = RR.rebuild_gather(rec)
        RR.run_stages(log)
        result = {"record": log.to_json(), "summary": log.summary()}
        del log
    else:
        from .record_io import load_record
        result = load_record(str(gather_record))
        gather_prov = result.get("provenance") or (result.get("record") or {}).get("provenance") or {}
        if "record" not in result:
            result = {"record": result, "summary": {}}
        obs = result["record"]["observations"]
        boxes = glyph_boxes(obs)
        glyph_obs = [o for o in obs if o.get("quantity") == "glyph_box"]
    vs = result["record"]["verdicts"]
    t1 = time.time()
    with traced_export():
        xml, report = E.to_musicxml(result)
    sym = parse_symbols(xml, boxes)
    cp = set(count_pages)       # context pages are loaded, never counted
    sym["hosts"] = [h for h in sym["hosts"] if h["page"] is None or h["page"] in cp]
    sym["loose"] = [d for d in sym["loose"] if d.get("page") is None or d["page"] in cp]
    red = report.get("bars_written_red") or {}
    live = {k: v for k, v in _live(vs, ("duration", "rest_is_not_a_rest")).items() if page_of(k[0]) in cp}
    stored = {k: v for k, v in stored.items() if page_of(k[0]) in cp}
    control = None
    if stored:
        same = [k for k, v in stored.items() if k in live and _brief(live[k]) == _brief(v)]
        diff = [k for k in stored if k not in set(same)]
        control = dict(stored=len(stored), same=len(same), differ=len(diff), first_differ=sorted(k[0] for k in diff)[:10])
    mini = {"observations": glyph_obs, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JQ]}
    work.mkdir(parents=True, exist_ok=True)
    stem = "%s.%s" % (plate, arm)
    (work / (stem + ".musicxml")).write_text(xml)
    (work / (stem + ".mini-record.json")).write_text(json.dumps(mini, default=str))
    out = dict(plate=plate, arm=arm, mode=mode, flags=[list(f) for f in flags], hosts=sym["hosts"], loose=sym["loose"],
               red_bars=_count(red.get("bars") if isinstance(red, dict) else red), bars_held_out=_count(report.get("bars_held_out_sum")),
               notes_not_written=report.get("notes_not_written_total"), control=control,
               blue_marks=xml.count('color="%s"' % E.GUESS_COLOR), seconds=round(time.time() - t0, 1),
               seconds_export=round(time.time() - t1, 1))
    from .one_test import arm_fingerprint     # ROADMAP 2.244: what this arm was built from (a combined run refuses a mix)
    out["fingerprint"] = arm_fingerprint(plate, mode, tag, count_pages, gather_prov, [f[0] for f in flags])
    (work / (stem + ".symbols.json")).write_text(json.dumps(out, default=str))
    return out


# ───────────────────────────── 6. the diff (pure counting) ─────────────────────────────

def place_of(h: dict) -> Optional[tuple]:
    """ROADMAP 2.211: where a written note / rest SITS, read from what EXPORT wrote, never from the detector box it was
    written from: `(page, system, staff, cell, part, measure, onset)`. The glyph key `glyph/page/system/staff/cell/n`
    gives the first four (the cell is the bar's cell on that system and staff); the XML gives the bar and the onset in
    it. None when the host has no onset or its key does not parse (then position pairing is the only way)."""
    m = re.match(r"glyph/(\d+)/(\d+)/(\d+)/(\d+)/\d+$", h.get("rg") or "")
    if not m or h.get("onset") is None:
        return None
    return tuple(int(x) for x in m.groups()) + (h.get("part"), h.get("measure"), h.get("onset"))


def pair_by_place(off: Sequence[dict], on: Sequence[dict], same_pitch: bool,
                  skip_i: Iterable[int] = (), skip_j: Iterable[int] = ()) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Pair two arms' written notes/rests by PLACE, not by box: same place and, if `same_pitch`, the same pitch (a rest is
    its own pitch), one to one, in x order within a tie. `skip_*` are hosts already paired. Returns (pairs, left_off, left_on)."""
    def pk(h):
        return h.get("pitch") or h.get("kind")
    used_i, used_j = set(skip_i), set(skip_j)
    pairs: List[Tuple[int, int]] = []
    groups_off: Dict[tuple, List[int]] = collections.defaultdict(list)
    groups_on: Dict[tuple, List[int]] = collections.defaultdict(list)
    for i, h in enumerate(off):
        pl = place_of(h)
        if pl is not None and i not in used_i:
            groups_off[pl + ((pk(h),) if same_pitch else ())].append(i)
    for j, h in enumerate(on):
        pl = place_of(h)
        if pl is not None and j not in used_j:
            groups_on[pl + ((pk(h),) if same_pitch else ())].append(j)
    for k, a in groups_off.items():
        b = groups_on.get(k)
        if not b:
            continue
        a = sorted(a, key=lambda i: (off[i].get("cx") or 0, off[i].get("cy") or 0))
        b = sorted(b, key=lambda j: (on[j].get("cx") or 0, on[j].get("cy") or 0))
        for i, j in zip(a, b):
            pairs.append((i, j))
            used_i.add(i)
            used_j.add(j)
    return pairs, [i for i in range(len(off)) if i not in used_i], [j for j in range(len(on)) if j not in used_j]


def pair_hosts(off: Sequence[dict], on: Sequence[dict], tol: float) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Pair two arms' written notes/rests, three rounds (ROADMAP 2.211; a detector box is no identity -- a twin box that
    changes keeper over the same written music must pair and report nothing):
      1. same PLACE (page, system, staff, cell, bar, onset) and same pitch;
      2. what is left, by page position: same page, centres within `tol` px, nearest first (the old rule; it carries a
         note whose onset moved because an earlier note in its bar changed value, a change that is reported on that note);
      3. what is left, same place and a different pitch or kind (a changed pitch at its place reports as one).
    A host with no place and no page position is never paired. Returns (pairs, unmatched_off, unmatched_on)."""
    pairs, lost, gain = pair_by_place(off, on, True)
    cands = []
    by_page: Dict[Any, List[int]] = collections.defaultdict(list)
    for j in gain:
        h = on[j]
        if h.get("page") is not None and h.get("cx") is not None:
            by_page[h["page"]].append(j)
    for i in lost:
        h = off[i]
        if h.get("page") is None or h.get("cx") is None:
            continue
        for j in by_page.get(h["page"], ()):
            g = on[j]
            d = ((h["cx"] - g["cx"]) ** 2 + (h["cy"] - g["cy"]) ** 2) ** 0.5
            if d <= tol:
                cands.append((d, i, j))
    cands.sort()
    used_i, used_j = {i for i, _ in pairs}, {j for _, j in pairs}
    for _d, i, j in cands:
        if i in used_i or j in used_j:
            continue
        used_i.add(i)
        used_j.add(j)
        pairs.append((i, j))
    more, _l, _g = pair_by_place(off, on, False, used_i, used_j)
    pairs += more
    used_i |= {i for i, _ in more}
    used_j |= {j for _, j in more}
    return (pairs, [i for i in range(len(off)) if i not in used_i], [j for j in range(len(on)) if j not in used_j])


def _change(kind: str, side: str, h: dict, **kw) -> dict:
    d = dict(kind=kind, side=side, page=h.get("page"), cx=h.get("cx"), cy=h.get("cy"), box=h.get("box"), rg=h.get("rg"))
    d.update(kw)
    return d


def _same(kind: str, h: dict, value: Any) -> dict:
    return dict(kind=kind, page=h.get("page"), cx=h.get("cx"), cy=h.get("cy"), box=h.get("box"), rg=h.get("rg"), value=value)


def diff_arms(off: Dict[str, Any], on: Dict[str, Any], tol: float) -> Dict[str, Any]:
    """What the exported file gained / lost / changed going OFF -> ON. Pure; the unit tests drive it."""
    changes: List[dict] = []
    same: List[dict] = []                       # unchanged symbols (the controls' pool)
    oh, nh = off["hosts"], on["hosts"]
    pairs, lost_i, gain_j = pair_hosts(oh, nh, tol)

    def whole(h: dict, side: str) -> None:
        changes.append(_change(h["kind"], side, h, value=h.get("type")))
        for k, vals in (h.get("sub") or {}).items():
            for v in vals:
                changes.append(_change(k, side, h, value=v))
        if h.get("blue"):
            changes.append(_change("blue", side, h, value="guessed"))

    for i in lost_i:
        whole(oh[i], "lost")
    for j in gain_j:
        whole(nh[j], "gained")
    for i, j in pairs:
        a, b = oh[i], nh[j]
        if a["kind"] != b["kind"]:
            whole(a, "lost")
            whole(b, "gained")
            continue
        quiet = True
        if a["kind"] == "note" and a["pitch"] != b["pitch"]:
            changes.append(_change("pitch", "changed", b, was=a["pitch"], value=b["pitch"]))
            quiet = False
        if a["type"] != b["type"]:
            changes.append(_change("value", "changed", b, was=a["type"], value=b["type"]))
            quiet = False
        if bool(a["blue"]) != bool(b["blue"]):
            changes.append(_change("blue", "gained" if b["blue"] else "lost", b, value="guessed"))
            quiet = False
        for k in sorted(set(a["sub"]) | set(b["sub"])):
            ca, cb = collections.Counter(a["sub"].get(k, ())), collections.Counter(b["sub"].get(k, ()))
            rem, add = list((ca - cb).elements()), list((cb - ca).elements())
            for r, ad in zip(rem, add):
                changes.append(_change(k, "changed", b, was=r, value=ad))
            for r in rem[len(add):]:
                changes.append(_change(k, "lost", a, value=r))
            for ad in add[len(rem):]:
                changes.append(_change(k, "gained", b, value=ad))
            if rem or add:
                quiet = False
            for v in (cb & ca).elements():
                same.append(_same(k, b, v))
        if quiet:
            same.append(_same(b["kind"], b, b.get("type")))
    # loose symbols (directions, clef/key/time): a multiset per (kind, value, part, measure); a place only if anchored
    def key(d: dict) -> tuple:
        return (d["kind"], d["value"], d["part"], d["measure"])
    lo, ln = collections.defaultdict(list), collections.defaultdict(list)
    for d in off["loose"]:
        lo[key(d)].append(d)
    for d in on["loose"]:
        ln[key(d)].append(d)
    for k in sorted(set(lo) | set(ln), key=str):
        a, b = lo.get(k, []), ln.get(k, [])
        for d in b[len(a):]:
            changes.append(_change(d["kind"], "gained", d, value=d["value"]))
        for d in a[len(b):]:
            changes.append(_change(d["kind"], "lost", d, value=d["value"]))
        for d in b[:len(a)]:
            if d["kind"] in LOCATED_KINDS and d.get("page") is not None:
                same.append(_same(d["kind"], d, d["value"]))
    counts: Dict[str, Dict[str, int]] = {}
    for c in changes:
        counts.setdefault(c["kind"], {"gained": 0, "lost": 0, "changed": 0})[c["side"]] += 1
    return dict(counts=counts, changes=changes, same=same, hosts=(len(oh), len(nh)), paired=len(pairs))


_NAMES = {"note": "notes", "rest": "rests", "accidental": "accidentals", "dot": "dots", "flag": "flags",
          "beam": "beams", "tie": "ties", "slur": "slurs", "articulation": "articulations", "fermata": "fermatas",
          "ornament": "ornaments", "tuplet": "tuplet notes", "value": "note values", "pitch": "pitches",
          "blue": "blue marks", "dynamic": "dynamics", "wedge": "wedges", "words": "words", "clef": "clefs",
          "key": "keys", "time": "meters"}


def control_of(off: Optional[dict], on: Optional[dict]) -> Optional[dict]:
    """The saved record was made at the tree's defaults, so the arm in the DEFAULT state of the flag must reproduce it and
    the other arm is allowed to differ (a landed default-ON flag turned OFF moves the OFF arm). Verdict: `off` / `on`
    reproduces, `both` (identity control), or `neither` (the tree moved: every number below is suspect)."""
    if off is None or on is None:
        return None
    r = "both" if off["differ"] == 0 and on["differ"] == 0 else "off" if off["differ"] == 0 else "on" if on["differ"] == 0 else "neither"
    return dict(reproduces=r, off=off, on=on)


def format_counts(counts: Dict[str, Dict[str, int]]) -> str:
    """`notes +3 -1 ~2 | rests -5 ...` in KIND_ORDER (+ gained, - lost, ~ changed); a plain sentence when empty."""
    parts = []
    for k in KIND_ORDER:
        c = counts.get(k)
        if not c:
            continue
        bits = []
        if c["gained"]:
            bits.append("+%d" % c["gained"])
        if c["lost"]:
            bits.append("-%d" % c["lost"])
        if c["changed"]:
            bits.append("~%d" % c["changed"])
        parts.append("%s %s" % (_NAMES[k], " ".join(bits)))
    return " | ".join(parts) if parts else "NOTHING CHANGED in the exported file"


# ───────────────────────────── 7. judged answers ─────────────────────────────

def judged_moves(off_rec: pathlib.Path, on_rec: pathlib.Path, doc: str,
                 off_hosts: Optional[Sequence[dict]] = None, on_hosts: Optional[Sequence[dict]] = None,
                 index_path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """Sean's judged tiles scored against the OFF and the ON mini-records (tools.omr.staged.judged, one scorer). With the
    arms' written hosts, each right->wrong / right->lost is then attached to its PLACE (`by_place`, ROADMAP 2.211)."""
    from . import judged as J
    idx = json.loads((index_path or J.INDEX_PATH).read_text())
    a = J.score(idx, off_rec, doc)
    b = J.score(idx, on_rec, doc)
    out = compare_judged(a["tiles"], b["tiles"])
    out["matched"] = dict(off=a.get("matched"), on=b.get("matched"))
    if off_hosts is not None and on_hosts is not None:
        subs = {s for k in ("worse", "lost", "unwritten_wrong", "unwritten_right") for r in out.get(k, ()) for s in _subject_list(r["subject"])}
        boxes: Dict[str, Sequence[float]] = {}
        if subs:
            boxes = dict(J.page_boxes(on_rec, subs))
            for s_, b_ in J.page_boxes(off_rec, subs).items():
                boxes.setdefault(s_, b_)
        out = by_place(out, boxes, off_hosts, on_hosts)
        out = invented_moves(out, idx, doc, boxes, off_hosts, on_hosts)
        out = written_moves(out, idx, doc, J.page_boxes, (off_rec, on_rec), off_hosts, on_hosts)
    return out


_TYPE_BEATS = {"whole": 4.0, "half": 2.0, "quarter": 1.0, "eighth": 0.5, "16th": 0.25, "32nd": 0.125, "64th": 0.0625}


def written_beats(h: dict) -> Optional[float]:
    """The value EXPORT wrote for a note, in quarter notes (type, plus its dots), plain or blue alike."""
    b = _TYPE_BEATS.get(h.get("type"))
    if b is None:
        return None
    n = len((h.get("sub") or {}).get("dot", ()))
    return b * (2 - 0.5 ** n)


def _right_value(h: dict, want: float) -> bool:
    """Right if the written value is Sean's, or the head's undotted value is (the dot is its own mark, as in judged._duration)."""
    b = written_beats(h)
    base = _TYPE_BEATS.get(h.get("type"))
    return b is not None and (abs(b - want) < 1e-6 or abs(base - want) < 1e-6)


def written_moves(rep: Dict[str, Any], idx: Dict[str, Any], doc: str, page_boxes, recs: Tuple[pathlib.Path, pathlib.Path],
                  off_hosts: Sequence[dict], on_hosts: Sequence[dict]) -> Dict[str, Any]:
    """Judged note VALUES scored from what EXPORT WROTE at the place, plain or blue alike (the lane-scorer-blue fix). The verdict
    scorer reads a DECIDED duration, so a note written by INFER collapse (a blue GUESSED half that becomes a blue quarter, its
    verdict `narrowed` on both arms) moved from right to wrong and scored 0. Here, for every judged one-value glyph tile of this
    document: the OFF note is the one written from the box (else the one inside it); the ON note is the one at the same place
    (never a chord-mate); right / wrong is the written value against Sean's. OFF right and ON wrong -> `worse`; OFF wrong and
    ON right -> `better`; each row says whether the ON note is blue (`blue`) and how it was found (`source: written`).
    A row the verdict scorer already put in `worse` / `better` is kept as it is, with `blue` added."""
    rows = [r for r in idx["tiles"] if not r.get("followup") and r.get("doc") == doc and r.get("subject_kind") == "glyph"
            and r.get("answer_kind") == "duration" and r.get("value") is not None and r.get("subject")]
    out = dict(rep)
    if not rows:
        return out
    subs = {r["subject"] for r in rows}
    boxes: Dict[str, Sequence[float]] = dict(page_boxes(recs[1], subs))
    for s_, b_ in page_boxes(recs[0], subs).items():
        boxes.setdefault(s_, b_)
    worse, better = list(rep.get("worse", ())), list(rep.get("better", ()))
    have = {"worse": {(w["item"], w["tile"]): w for w in worse}, "better": {(w["item"], w["tile"]): w for w in better}}
    for r in rows:
        sub = r["subject"]
        off_h = host_for_row(off_hosts, r, sub, boxes.get(sub))
        if off_h is None or off_h["kind"] != "note" or place_of(off_h) is None:
            continue
        on_h = event_at(on_hosts, place_of(off_h), off_h.get("pitch"), "note")
        if on_h is None or on_h["kind"] != "note" or on_h.get("pitch") != off_h.get("pitch"):
            continue   # the note is gone or moved pitch: a lost / changed note, not a changed value
        was, now = _right_value(off_h, r["value"]), _right_value(on_h, r["value"])
        key = (r["item"], r["tile"])
        blue = bool(on_h.get("blue"))
        if was and not now:
            kind, bucket = "worse", worse
        elif now and not was:
            kind, bucket = "better", better
        else:
            continue
        if key in have[kind]:
            have[kind][key]["blue"] = blue
            continue
        bucket.append(dict(item=r["item"], tile=r["tile"], subject=sub, answer=r["answer"], source="written", blue=blue,
                           off_blue=bool(off_h.get("blue")),
                           now="written %s%s%s (OFF %s%s)" % (on_h["type"], "." * len((on_h.get("sub") or {}).get("dot", ())),
                                                           " blue" if blue else "", off_h["type"], " blue" if off_h.get("blue") else "")))
    out["worse"], out["better"] = worse, better
    return out


def blue_count(rows: Iterable[dict]) -> str:
    """"1 (1 blue)" style: the count, with how many of those are blue (GUESSED) notes."""
    rows = list(rows)
    nb = sum(1 for r in rows if r.get("blue"))
    return "%d (%d blue)" % (len(rows), nb) if nb else "%d" % len(rows)


def _subject_list(sub: Any) -> List[str]:
    return [sub] if isinstance(sub, str) else list(sub or [])


def written_at(hosts: Sequence[dict], subject: str, box: Optional[Sequence[float]]) -> Optional[dict]:
    """The note / rest an arm WROTE for a judged box: the host written from that very key, else (the box was a twin that
    was never written) the host on the same page whose centre lies inside the box, nearest the box's centre."""
    for h in hosts:
        if h.get("rg") == subject:
            return h
    if not box:
        return None
    pg = page_of(subject)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    inside = [h for h in hosts if h.get("page") == pg and h.get("cx") is not None
              and box[0] <= h["cx"] <= box[2] and box[1] <= h["cy"] <= box[3]]
    return min(inside, key=lambda h: (h["cx"] - cx) ** 2 + (h["cy"] - cy) ** 2) if inside else None


def written_at_place(hosts: Sequence[dict], row: dict) -> Optional[dict]:
    """ROADMAP 2.244: the note / rest an arm wrote where a POSITIONED judged tile is: a host whose glyph key sits in the tile's
    (page, system, staff, cell) and whose box overlaps the tile's page box, nearest the tile's centre. Never the key alone: a
    glyph id is one gather's detector order."""
    from . import judged as J
    pl, tb = J.row_place(row), J.row_box(row)
    if pl is None or tb is None:
        return None
    cx, cy = (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2
    here = [h for h in hosts if J.key_place(h.get("rg")) == pl and h.get("box") and J.boxes_overlap(h["box"], tb)[0]]
    return min(here, key=lambda h: ((h["box"][0] + h["box"][2]) / 2 - cx) ** 2 + ((h["box"][1] + h["box"][3]) / 2 - cy) ** 2,
               default=None)


def host_for_row(hosts: Sequence[dict], row: dict, subject: str, box: Optional[Sequence[float]]) -> Optional[dict]:
    """The written host for a judged row: by PLACE when the row has a `position`, else by the old key / box (`written_at`)."""
    from . import judged as J
    if J.row_place(row) is not None:
        return written_at_place(hosts, row)
    return written_at(hosts, subject, box)


def event_at(hosts: Sequence[dict], place: tuple, pitch: Optional[str], kind: str) -> Optional[dict]:
    """The event an arm wrote at a place: same pitch (or kind, for a rest) first, else any event at that slot."""
    here = [h for h in hosts if place_of(h) == place]
    for h in here:
        if (h.get("pitch") or h.get("kind")) == (pitch or kind):
            return h
    return here[0] if here else None


_NOT_A_NOTE_TEXT = re.compile(r"^(part of\b|nothing\b|beams?\b|\d+ beams?\b|beams \(|bracket\b|fermata\b|f dyn\b|ledger line|.*\bclef\b)", re.I)


def says_not_a_note(row: dict) -> bool:
    """ROADMAP 2.218: Sean's answer says the marked ink is NOT a note: the answer kind says so, or a free-text answer to an
    identity / unknown question names another mark ('part of ff', 'part of a 4 rest', 'beams', 'nothing', a clef)."""
    if row.get("answer_kind") == "not_a_note":
        return True
    return row.get("answer_kind") == "other" and row.get("question_kind") in ("unknown", "identity") \
        and bool(_NOT_A_NOTE_TEXT.match((row.get("answer") or "").strip()))


def invented_moves(rep: Dict[str, Any], idx: Dict[str, Any], doc: str, boxes: Dict[str, Sequence[float]],
                   off_hosts: Sequence[dict], on_hosts: Sequence[dict]) -> Dict[str, Any]:
    """ROADMAP 2.218. Judged 'not a note' answers, by the place the arms WROTE. `invented`: the ON file writes a note
    from that box and the OFF file writes none there -- counted under unwritten->wrong (the worst wrong: a note made of
    other ink; CLAUDE section 1). `invented_removed`: OFF wrote a note there and ON writes none (good, its own line).
    Rows whose manifest names no document are not scored here."""
    out = dict(rep)
    wrong = list(rep.get("unwritten_wrong", ()))
    seen = {(w["item"], w["tile"]): w for w in wrong}
    removed = []
    for r in idx["tiles"]:
        if r.get("followup") or r.get("doc") != doc or r.get("subject_kind") != "glyph" or not says_not_a_note(r):
            continue
        for sub in (r.get("subjects") or ([r["subject"]] if r.get("subject") else [])):
            box = boxes.get(sub)
            on_h, off_h = host_for_row(on_hosts, r, sub, box), host_for_row(off_hosts, r, sub, box)
            key = (r["item"], r["tile"])
            if on_h and on_h["kind"] == "note" and place_of(on_h) and not _same_note_at(off_hosts, on_h):
                if key in seen:
                    seen[key]["invented"] = True
                else:
                    w = dict(item=r["item"], tile=r["tile"], subject=sub, answer=r["answer"], off="unwritten", invented=True,
                             now="INVENTED: ON writes a %s %s from non-note ink" % (on_h["type"], on_h.get("pitch")))
                    wrong.append(w)
                    seen[key] = w
            elif off_h and off_h["kind"] == "note" and place_of(off_h) and not _same_note_at(on_hosts, off_h):
                removed.append(dict(item=r["item"], tile=r["tile"], subject=sub, answer=r["answer"]))
    out["unwritten_wrong"], out["invented_removed"] = wrong, removed
    return out


def _same_note_at(hosts: Sequence[dict], h: dict) -> bool:
    """Does `hosts` hold an event at h's place with h's pitch (or kind, for a rest)? Unlike `event_at` there is no
    fallback to another event at the slot: a chord-mate or a neighbouring part's note is not this note."""
    return any(place_of(g) == place_of(h) and (g.get("pitch") or g["kind"]) == (h.get("pitch") or h["kind"]) for g in hosts)


def by_place(rep: Dict[str, Any], boxes: Dict[str, Sequence[float]], off_hosts: Sequence[dict],
             on_hosts: Sequence[dict]) -> Dict[str, Any]:
    """ROADMAP 2.211. The scorer answers per detector box; the file is the music. A right->wrong / right->lost row is
    attached to the place its box was written at in the OFF file, and kept only if the ON file WRITES something else
    there (a different pitch or value, or nothing). Moves out of `worse` / `lost`:
      `same_music`  the ON file writes the same pitch and value at that place (a twin box changed keeper);
      `not_found`   no event is written at that place in the OFF file, so nothing can be said -- never right or wrong."""
    out = dict(rep)
    same_music, not_found = [], []
    for key in ("worse", "lost"):
        keep = []
        for r in rep[key]:
            subs = _subject_list(r["subject"])
            offs = [written_at(off_hosts, s, boxes.get(s)) for s in subs]
            if not subs or any(h is None or place_of(h) is None for h in offs):
                not_found.append(dict(r, was=key, why="no written event at that place in the OFF file"))
                continue
            same = True
            for h in offs:
                g = event_at(on_hosts, place_of(h), h.get("pitch"), h["kind"])
                if g is None or g["kind"] != h["kind"] or g.get("pitch") != h.get("pitch") or g["type"] != h["type"] \
                        or collections.Counter(g["sub"].get("dot", ())) != collections.Counter(h["sub"].get("dot", ())):
                    same = False
            (same_music if same else keep).append(r if not same else dict(r, was=key))
        out[key] = keep
    # ROADMAP 2.218: unwritten -> wrong / right. The scorer's OFF status was narrowed / abstained / not found; it counts
    # only if the OFF file WRITES NOTHING at the place the ON file wrote this box (else it is an ordinary change).
    for key in ("unwritten_wrong", "unwritten_right"):
        keep = []
        for r in rep.get(key, ()):
            subs = _subject_list(r["subject"])
            ons = [written_at(on_hosts, s, boxes.get(s)) for s in subs]
            if not subs or any(h is None or place_of(h) is None for h in ons):
                not_found.append(dict(r, was=key, why="ON file writes no event at that box"))
                continue
            if any(_same_note_at(off_hosts, h) for h in ons):
                continue   # OFF wrote this very note there: not an unwritten note (a changed one, scored elsewhere)
            keep.append(r)
        out[key] = keep
    out["same_music"], out["not_found"] = same_music, not_found
    return out


def compare_judged(off_tiles: Sequence[dict], on_tiles: Sequence[dict]) -> Dict[str, Any]:
    """Per judged tile, OFF status -> ON status. `worse` = right -> wrong (must be 0); `lost` = right -> narrowed /
    abstained / not_found; `better` = wrong -> right; `unwritten_wrong` / `unwritten_right` (ROADMAP 2.218) = OFF narrowed /
    abstained / not found -> ON decided wrong / right (wrong must be 0; the place check is `by_place`)."""
    def k(t):
        return (t["item"], t["tile"])
    on_by = {k(t): t for t in on_tiles}
    worse, lost, better, n_scored = [], [], [], 0
    up_wrong, up_right = [], []
    for t in off_tiles:
        u = on_by.get(k(t))
        if u is None:
            continue
        if t["status"] != "not_found" or u["status"] != "not_found":
            n_scored += 1
        if t["status"] == "right" and u["status"] == "wrong":
            worse.append(dict(item=t["item"], tile=t["tile"], subject=t["subject"], answer=t["answer"], now=u["note"]))
        elif t["status"] == "right" and u["status"] in ("narrowed", "abstained", "not_found"):
            lost.append(dict(item=t["item"], tile=t["tile"], subject=t["subject"], now=u["status"]))
        elif t["status"] == "wrong" and u["status"] == "right":
            better.append(dict(item=t["item"], tile=t["tile"], subject=t["subject"]))
        elif t["status"] in ("narrowed", "abstained", "not_found") or (t["status"] == "wrong" and t["note"].startswith("narrowed")):
            # ROADMAP 2.218: OFF left it unwritten (narrowed -- even to a set that misses Sean's answer -- abstained, or
            # not found); `by_place` keeps it only if the OFF file writes that very note nowhere at the place
            if u["status"] == "wrong":
                up_wrong.append(dict(item=t["item"], tile=t["tile"], subject=t["subject"], answer=t["answer"],
                                     off=t["status"], now=u["note"]))
            elif u["status"] == "right":
                up_right.append(dict(item=t["item"], tile=t["tile"], subject=t["subject"], answer=t["answer"], off=t["status"]))
    return dict(worse=worse, lost=lost, better=better, unwritten_wrong=up_wrong, unwritten_right=up_right, scored=n_scored)


# ───────────────────────────── 7b. changed places nobody has judged (ROADMAP 2.244) ─────────────────────────────

_VALUE_KINDS = frozenset({"note", "rest", "value", "flag", "beam", "dot", "blue", "tuplet"})
#: the change kinds a judged tile speaks to, by what Sean was asked. A tile about a note's value says nothing about the
#: accidental in front of it, so that accidental is still unjudged.
_SPEAKS = {"duration": _VALUE_KINDS, "identity": frozenset({"note", "rest"}), "arc": frozenset({"tie", "slur"}),
           "dynamic": frozenset({"dynamic"})}


def row_speaks_to(row: dict) -> frozenset:
    if row.get("question_kind") in _SPEAKS:
        return _SPEAKS[row["question_kind"]]
    if row.get("answer_kind") in ("duration", "duration_multi", "rest"):
        return _VALUE_KINDS
    if row.get("answer_kind") == "arc":
        return _SPEAKS["arc"]
    return frozenset()


def judged_cover(idx: Dict[str, Any], doc: str, boxes: Dict[str, Sequence[float]]) -> List[Dict[str, Any]]:
    """What Sean's answers cover on this plate: `[{page, box|None, subject, kinds}]`. A row's box is its position's page box,
    else its own `page_box`, else the box of its glyph key in this record (`boxes`); a row with no box is covered by key only."""
    from . import judged as J
    out = []
    for r in idx["tiles"]:
        if r.get("followup") or r.get("doc") != doc or r.get("subject_kind") != "glyph":
            continue
        kinds = row_speaks_to(r)
        if not kinds:
            continue
        for sub in (r.get("subjects") or ([r["subject"]] if r.get("subject") else [])):
            pl = J.row_place(r) or J.key_place(sub)
            box = J.row_box(r) or (r.get("page_box") if len(r.get("page_box") or ()) == 4 else None) or boxes.get(sub)
            out.append(dict(page=pl[0] if pl else page_of(sub), cell=pl, box=list(box) if box else None, subject=sub, kinds=kinds,
                            positioned=J.row_place(r) is not None))
    return out


def unjudged_changes(changes: Sequence[dict], cover: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The changed places no judged tile covers: `{unjudged: [change + place], judged: n, no_place: n}`. A change is covered
    when a judged tile of a kind that speaks to it sits on its page with an overlapping box (same cell, for a positioned tile),
    or was cut from the very glyph key the change was written from. A change with no page box is counted as `no_place`."""
    from . import judged as J
    out, covered, no_place = [], 0, 0
    for c in changes:
        pl = J.key_place(c.get("rg"))
        if c.get("page") is None or not c.get("box"):
            no_place += 1
            continue
        hit = False
        for v in cover:
            if c["kind"] not in v["kinds"] or v["page"] != c["page"]:
                continue
            if v["positioned"] and v["cell"] != pl:
                continue
            if (c.get("rg") and c["rg"] == v["subject"]) or (v["box"] and J.boxes_overlap(c["box"], v["box"])[0]):
                hit = True
                break
        if hit:
            covered += 1
        else:
            out.append(dict(c, place=list(pl) if pl else None))
    return dict(unjudged=out, judged=covered, no_place=no_place)


def unjudged_for_plate(plate: str, changes: Sequence[dict], mini_rec: pathlib.Path,
                       index_path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """`unjudged_changes` for one plate against the committed judged index (glyph keys boxed from the arm's mini-record)."""
    from . import judged as J
    idx = json.loads((index_path or J.INDEX_PATH).read_text())
    subs = {s for r in idx["tiles"] if r.get("doc") == plate and not r.get("followup")
            for s in (r.get("subjects") or ([r["subject"]] if r.get("subject") else []))}
    return unjudged_changes(changes, judged_cover(idx, plate, J.page_boxes(mini_rec, subs)))


def unjudged_lines(plate: str, un: Sequence[dict]) -> List[str]:
    """One line per unjudged changed place: plate, page/system/staff/cell, kind, side, value."""
    rows = sorted(un, key=lambda c: (c.get("page") or 0, c.get("place") or [], c["kind"], str(c.get("value"))))
    return ["%s p%s %s  %s %s %s%s" % (plate, c.get("page"), "/".join(map(str, c["place"])) if c.get("place") else "-", c["kind"],
                                       c["side"], c.get("value"), " (was %s)" % c["was"] if c.get("was") is not None else "")
            for c in rows]


# ───────────────────────────── 8. the blind sheet ─────────────────────────────

def tile_quota(sizes: Dict[str, int], n: int, floor_share: float = 0.10) -> Dict[str, int]:
    """Tiles per kind in proportion to how many changes the kind has (largest remainder); every kind holding at least
    `floor_share` of all changes gets at least one. Never more than the kind has."""
    total = sum(sizes.values())
    if total <= 0 or n <= 0:
        return {k: 0 for k in sizes}
    q = {k: n * v / total for k, v in sizes.items()}
    out = {k: min(sizes[k], int(q[k])) for k in sizes}
    for k, v in sizes.items():
        if v / total >= floor_share and out[k] < 1:
            out[k] = 1
    # largest remainder fills what is left; the floor may overshoot n by a tile or two, never more
    for k in sorted(sizes, key=lambda k: (q[k] - int(q[k]), sizes[k]), reverse=True):
        if sum(out.values()) >= n:
            break
        if out[k] < sizes[k] and q[k] - out[k] > 0:
            out[k] += 1
    return out


def _same_ink(a: dict, b: dict) -> bool:
    """Two tile items on ONE page whose boxes overlap (a centre of one inside the other, or IoU > 0.3) show the same ink: 2.187b, after two tiles
    of one note under two box ids were drawn (Sean 2026-10-22: 'Dot 2 (same note as 9)')."""
    if (a["plate"], a["page"]) != (b["plate"], b["page"]):
        return False
    ax0, ay0, ax1, ay1 = a["box"]
    bx0, by0, bx1, by1 = b["box"]
    iw, ih = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
    if iw > 0 and ih > 0 and iw * ih / float((ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - iw * ih) > 0.3:
        return True
    inside = lambda p, q: q[0] <= (p[0] + p[2]) / 2.0 <= q[2] and q[1] <= (p[1] + p[3]) / 2.0 <= q[3]
    return inside(a["box"], b["box"]) or inside(b["box"], a["box"])


def pick_tiles(all_changes: Dict[str, List[dict]], all_same: Dict[str, List[dict]], seed: int, n_cases: int = 9,
               n_controls: int = 3) -> List[dict]:
    """About 9 changed symbols drawn at random, drawn in PROPORTION to how many changes each kind has (every kind with >= 10% gets one; a random draw inside each), + about 3 controls = unchanged symbols of the kinds drawn. Only symbols with a place on the page."""
    rng = random.Random(seed)
    pool: Dict[str, List[dict]] = collections.defaultdict(list)
    for plate, ch in sorted(all_changes.items()):
        for c in ch:
            if c.get("box") and c.get("page") is not None and c["kind"] in LOCATED_KINDS:
                pool[c["kind"]].append(dict(c, plate=plate))
    for k in sorted(pool):
        rng.shuffle(pool[k])
    kinds = sorted(pool)
    rng.shuffle(kinds)
    quota = tile_quota({k: len(pool[k]) for k in kinds}, n_cases)
    cases: List[dict] = []
    seen = set()
    for k in kinds:
        got = 0
        while pool[k] and got < quota[k]:
            c = pool[k].pop()
            sig = (c["plate"], c["rg"], c["kind"], c["side"])
            if sig in seen or any(_same_ink(c, x) for x in cases):
                continue
            seen.add(sig)
            cases.append(dict(c, role="case"))
            got += 1
    ctrl_pool: Dict[str, List[dict]] = collections.defaultdict(list)
    for plate, sm in sorted(all_same.items()):
        for s in sm:
            if s.get("box") and s.get("page") is not None:
                ctrl_pool[s["kind"]].append(dict(s, plate=plate))
    taken = {(c["plate"], c["rg"]) for c in cases}
    controls: List[dict] = []
    want = [c["kind"] for c in cases] or ["note"]
    rng.shuffle(want)
    for k in want:
        if len(controls) >= n_controls:
            break
        cand = [s for s in ctrl_pool.get(k, []) if (s["plate"], s["rg"]) not in taken
                and not any(_same_ink(s, x) for x in cases + controls)]
        if cand:
            s = rng.choice(cand)
            controls.append(dict(s, role="control", side="unchanged"))
            taken.add((s["plate"], s["rg"]))
    items = cases + controls
    rng.shuffle(items)
    return items


def tile_position(it: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.231: where a tile's mark is, by PAGE POSITION -- (page, system, staff-in-system, cell) from its
    glyph/cell key, plus the page box. A glyph index is one gather's detector order; the position and box are not."""
    from .record import Subject
    for raw in (it.get("rg"), it.get("subject")):
        if isinstance(raw, str) and raw.split("/")[0] in ("glyph", "cell"):
            try:
                s = Subject.from_key(raw)
            except (ValueError, TypeError):
                continue
            return dict(page=s.page, system=s.system, staff=s.staff, cell=s.cell, page_box=it.get("box"))
    return None


_CELL_MAP_VERSION: Dict[str, Optional[str]] = {}


def cell_map_version(plate: str) -> Optional[str]:
    """The master cell map a tile's cells came from (its version tag names the cells), or None = cut fresh."""
    if CELL_MAP is None:
        return None
    if plate not in _CELL_MAP_VERSION:
        from . import cell_map as CM
        _CELL_MAP_VERSION[plate] = CM.info(LIB / PLATES[plate]["pdf"], root=CELL_MAP)["version"]
    return _CELL_MAP_VERSION[plate]


def cut_tiles(items: List[dict], out_dir: pathlib.Path, tile_dir_name: str = "tiles", readme_extra: str = "") -> Dict[str, Any]:
    """Cut each item from its page at 600 dpi with ONE neutral orange box; write single tiles + a sheet PNG +
    README (tile folder) and the key (OUTSIDE the tile folder)."""
    from PIL import Image, ImageDraw
    from ..preprocessing import render_page
    tdir = out_dir / tile_dir_name
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    cache: Dict[Tuple[str, int], Any] = {}
    W = 520
    tiles, key = [], []
    for n, it in enumerate(items, 1):
        plate, pg = it["plate"], it["page"]
        if (plate, pg) not in cache:
            cache.clear()
            cache[(plate, pg)] = Image.fromarray(render_page(str(LIB / PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
        im = cache[(plate, pg)]
        bb = [it["box"][0] - 4, it["box"][1] - 4, it["box"][2] + 4, it["box"][3] + 4]
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        u = PLATES[plate]["unit"]
        x0, y0, x1, y1 = max(0, int(cx - 6 * u)), max(0, int(cy - 5 * u)), int(cx + 6 * u), int(cy + 5 * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)],
                                       outline=ORANGE, width=max(2, int(u / 8)))
        crop = crop.resize((W, int(W * crop.height / crop.width)))
        crop.save(tdir / ("tile_%02d.png" % n))
        tiles.append(crop)
        key.append({k: v for k, v in it.items() if k not in ("cx", "cy")} | dict(tile=n, crop_origin=[x0, y0])
                   | dict(position=tile_position(it), cell_map=cell_map_version(plate)))
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    h = max((t.height for t in tiles), default=0)
    sheet = Image.new("RGB", (cols * (W + 8) + 8, rows * (h + 30) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = 8 + (n % cols) * (W + 8), 8 + (n // cols) * (h + 30)
        d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t, (x, y + 18))
    sheet.save(tdir / "sheet.png")
    (tdir / "README.md").write_text(
        "# Lane report tiles\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing "
        "else drawn. The orange box only says where to look; it means nothing about what we read.\n\n"
        "**Question, for every tile:** what does the print show at the orange box (a note and its value, a rest and its "
        "value, an accidental, a dot, a flag or beam, a tie or slur, a mark, or nothing there)? Is anything about it "
        "that we might have written wrongly?\n\nAnswer by tile number.\n" + readme_extra)
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))
    return dict(n=len(key), cases=sum(k["role"] == "case" for k in key), controls=sum(k["role"] == "control" for k in key))


# ───────────────────────────── 9. the command ─────────────────────────────

def _spawn(args: List[str], env: Dict[str, str], logpath: pathlib.Path) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-u", "-m", "tools.omr.staged.lane_report"] + args, cwd=str(ROOT), env=env,
                            stdout=open(logpath, "w"), stderr=subprocess.STDOUT)


def gather_one(plate: str, arm: str, flag_env: Dict[str, str], pages: Sequence[int], work: pathlib.Path,
               env0: Dict[str, str]) -> pathlib.Path:
    """One page-gather of `plate` with `flag_env` set, written to `work/<plate>.<arm>.gathered.record.json`: the shared detector
    cache and (if set) the master cell map, OCR server off after (the same call `run_report` and `one_test` make)."""
    rp = work / ("%s.%s.gathered.record.json" % (plate, arm))
    env = dict(env0)
    env.update(flag_env)
    env["OMR_SURYA_KEEP_ALIVE"] = "0"
    if DETECTOR_CACHE is not None:      # ROADMAP 2.189: the raw detector output, read once, for both arms and every later run
        env["OMR_DETECTOR_CACHE"] = str(DETECTOR_CACHE)
    else:
        env.pop("OMR_DETECTOR_CACHE", None)
    cmd = [sys.executable, "-u", "-m", "tools.omr.staged", str(LIB / PLATES[plate]["pdf"]), "--pages",
           ",".join(map(str, pages)), "--dpi", "600", "--weights", "auto", "--route-weights", "--out", str(rp)]
    if CELL_MAP is not None:            # ROADMAP 2.231: both arms read the master's cells, never a fresh cut
        cmd += ["--cell-map", str(CELL_MAP)]
    print("  gather %s %s pages %s ..." % (plate, arm, list(pages)), flush=True)
    logp = work / ("%s.%s.gather.log" % (plate, arm))
    r = subprocess.run(cmd, cwd=str(ROOT), env=env, stdout=open(logp, "w"), stderr=subprocess.STDOUT)
    if r.returncode != 0 or not rp.exists():
        raise SystemExit("gather failed for %s %s (see %s)" % (plate, arm, logp))
    return rp


def run_report(flags: Sequence[Tuple[str, str, str]], plates: Sequence[str], mode: str, out: pathlib.Path,
               tag: str, seed: int, workers: int, sample: Dict[str, Any], note_lines: Sequence[str],
               reuse: bool = False, unjudged_tiles: int = 0) -> Dict[str, Any]:
    t0 = time.time()
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    pages = {p: sample["plates"][p]["pages"] for p in plates}
    env0 = dict(os.environ)
    if mode == "adjudicate":
        for p in plates:
            ensure_slices(p, loaded_pages(sample, p), tag)
    jobs = [(p, a) for p in plates for a in ("off", "on")]
    if reuse:       # development only: the arms' saved files, re-parsed; `mode == adjudicate` slices are on disk
        done0 = {(p, a): reparse_arm(p, a, tag, work, pages[p]) for p, a in jobs}
        jobs = []
    else:
        done0 = {}
    base = ["arm", "--tag", tag, "--work", str(work), "--from", mode]
    for name, off, on in flags:
        base += ["--flag", "%s=%s:%s" % (name, off, on)]
    gather_recs: Dict[Tuple[str, str], pathlib.Path] = {}
    if mode == "gather":
        for p, a in jobs:       # one page gather at a time (CLAUDE.md "lean lanes")
            gather_recs[(p, a)] = gather_one(p, a, {n: (on if a == "on" else off) for n, off, on in flags}, pages[p], work, env0)
    running: List[Tuple[Tuple[str, str], subprocess.Popen]] = []
    queue = list(jobs)
    done: Dict[Tuple[str, str], Any] = dict(done0)
    while queue or running:
        while queue and len(running) < max(1, workers):
            p, a = queue.pop(0)
            extra = ["--plate", p, "--arm", a, "--pages", ",".join(map(str, pages[p]))]
            if mode == "gather":
                extra += ["--gathered", str(gather_recs[(p, a)])]
            running.append(((p, a), _spawn(base + extra, dict(env0), work / ("%s.%s.log" % (p, a)))))
        for item in list(running):
            (p, a), proc = item
            if proc.poll() is not None:
                running.remove(item)
                if proc.returncode != 0:
                    raise SystemExit("arm %s %s failed: see %s" % (p, a, work / ("%s.%s.log" % (p, a))))
                done[(p, a)] = json.loads((work / ("%s.%s.symbols.json" % (p, a))).read_text())
        time.sleep(1)
    rep: Dict[str, Any] = dict(flags=[list(f) for f in flags], mode=mode, plates={}, notes=list(note_lines))
    all_changes, all_same, all_unjudged = {}, {}, {}
    for p in plates:
        off, on = done[(p, "off")], done[(p, "on")]
        d = diff_arms(off, on, tol=0.5 * PLATES[p]["unit"])
        jm = judged_moves(work / ("%s.off.mini-record.json" % p), work / ("%s.on.mini-record.json" % p), p,
                          off["hosts"], on["hosts"])
        all_changes[p], all_same[p] = d["changes"], d["same"]
        un = unjudged_for_plate(p, d["changes"], work / ("%s.on.mini-record.json" % p))
        all_unjudged[p] = un["unjudged"]
        rep["plates"][p] = dict(pages=pages[p], counts=d["counts"], hosts=d["hosts"], paired=d["paired"],
                                red_bars=[off["red_bars"], on["red_bars"]],
                                notes_not_written=[off["notes_not_written"], on["notes_not_written"]],
                                control=control_of(off["control"], on["control"]), judged=jm, seconds=[off["seconds"], on["seconds"]],
                                unjudged=dict(n=len(un["unjudged"]), judged=un["judged"], no_place=un["no_place"],
                                              by_kind=dict(collections.Counter(c["kind"] for c in un["unjudged"])),
                                              places=unjudged_lines(p, un["unjudged"])))
    items = pick_tiles(all_changes, all_same, seed)
    rep["tiles"] = cut_tiles(items, out) if items else dict(n=0, cases=0, controls=0)
    (out / "unjudged.txt").write_text("\n".join(l for p in plates for l in rep["plates"][p]["unjudged"]["places"]) + "\n")
    if unjudged_tiles:
        uitems = pick_tiles(all_unjudged, {}, seed, n_cases=unjudged_tiles, n_controls=0)[:unjudged_tiles]
        rep["unjudged_tiles"] = cut_tiles(uitems, out / "unjudged", readme_extra=(
            "\nThese tiles are places where our written mark CHANGED between the two runs and none of your earlier answers "
            "covers them.\n")) if uitems else dict(n=0, cases=0, controls=0)
    rep["tile_seed"] = seed
    rep["wall_seconds"] = round(time.time() - t0, 1)
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "report.txt").write_text(render_text(rep) + "\n")
    return rep


def landing_line(rep: Dict[str, Any]) -> str:
    """ROADMAP 2.218: the landing summary. Both judged controls must be 0 for a lane to land (docs/measuring.md section 0)."""
    rwl = [w for r in rep["plates"].values() for w in r["judged"]["worse"]]
    rw = len(rwl)
    rwt = blue_count(rwl)
    bt = blue_count([w for r in rep["plates"].values() for w in r["judged"].get("better", ())])
    uw = sum(len(r["judged"].get("unwritten_wrong", ())) for r in rep["plates"].values())
    ur = sum(len(r["judged"].get("unwritten_right", ())) for r in rep["plates"].values())
    if rw == 0 and uw == 0:
        return "LANDING CHECK: judged right->wrong 0, unwritten->wrong 0 (unwritten->right %d; wrong->right %s)" % (ur, bt)
    return "LANDING CHECK FAILS: judged right->wrong " + rwt + ", UNWRITTEN->WRONG %d (a note OFF left unwritten that ON writes against Sean's answer) -- must be 0 to land (wrong->right %s)" % (uw, bt)


def render_text(rep: Dict[str, Any]) -> str:
    L = []
    flags = ", ".join("%s (OFF=%s ON=%s)" % tuple(f) for f in rep["flags"]) or "(no flag)"
    L.append("LANE REPORT  %s  --from %s" % (flags, rep["mode"]))
    for n in rep["notes"]:
        L.append("  " + n)
    for p, r in rep["plates"].items():
        L.append("")
        L.append("%s  pages %s  (%d notes+rests OFF, %d ON, %d paired)" % (p, r["pages"], r["hosts"][0], r["hosts"][1], r["paired"]))
        L.append("  file:   " + format_counts(r["counts"]))
        L.append("  red bars %s -> %s | notes not written %s -> %s"
                 % (r["red_bars"][0], r["red_bars"][1], r["notes_not_written"][0], r["notes_not_written"][1]))
        c = r["control"]
        if c is None:
            L.append("  control: no saved verdicts to compare (re-gather mode) -- OFF==record NOT CHECKED")
        else:
            o, n = c["off"], c["on"]
            say = {"both": "OFF and ON both reproduce the record",
                   "off": "OFF reproduces the record (ON is the arm that moves)",
                   "on": "ON reproduces the record (the flag is default-ON; OFF is the arm that moves)",
                   "neither": "NEITHER ARM REPRODUCES THE RECORD -- the tree moved, not only the flag; distrust every number"}[c["reproduces"]]
            L.append("  control: %s: duration/rest verdicts differing from the record OFF %d / ON %d of %d%s"
                     % (say, o["differ"], n["differ"], o["stored"],
                        "" if c["reproduces"] in ("both",) else " (e.g. %s)" % ", ".join((o if o["differ"] else n)["first_differ"][:3])))
        j = r["judged"]
        L.append("  Sean's judged answers (%d tiles on these pages): right->wrong %s | right->narrowed/abstained/gone %d | wrong->right %s"
                 % (j["scored"], blue_count(j["worse"]), len(j["lost"]), blue_count(j["better"])))
        for w in j["worse"]:
            L.append("      RIGHT->WRONG%s  %s tile %s %s  Sean: %s  now: %s" % (" (blue)" if w.get("blue") else "", w["item"], w["tile"], w["subject"], w["answer"], w["now"]))
        L.append("  Sean's judged answers, OFF wrote nothing there: unwritten->wrong %d (of which invented from non-note ink %d; must be 0) | unwritten->right %d | invented->removed %d (good)"
                 % (len(j.get("unwritten_wrong", ())), sum(1 for w in j.get("unwritten_wrong", ()) if w.get("invented")),
                    len(j.get("unwritten_right", ())), len(j.get("invented_removed", ()))))
        for w in j.get("unwritten_wrong", ()):
            L.append("      UNWRITTEN->WRONG  %s tile %s %s  Sean: %s  OFF: %s  now: %s" % (w["item"], w["tile"], w["subject"], w["answer"], w["off"], w["now"]))
        m = (j.get("matched") or {}).get("on") or {}
        if m:
            L.append("  judged tiles found by place %d (at another id than asked %d) | by id key, no position %d | position but no mark here %d"
                     % (m.get("place", 0), m.get("place_moved_id", 0), m.get("key", 0), m.get("place_no_mark", 0) + m.get("place_no_box", 0)))
        u = r.get("unjudged")
        if u:
            L.append("  NOT JUDGED: %d changed places no tile of Sean's covers (%d are covered; %d have no page place): %s -> unjudged.txt"
                     % (u["n"], u["judged"], u["no_place"], ", ".join("%s %d" % kv for kv in sorted(u["by_kind"].items())) or "none"))
        for w in j["lost"][:10]:
            L.append("      right->%s  %s tile %s %s" % (w["now"], w["item"], w["tile"], w["subject"]))
        for w in j.get("same_music", ()):
            L.append("      same music at its place (box swap, not a change)  %s tile %s %s  scorer said %s" % (w["item"], w["tile"], w["subject"], w["was"]))
        for w in j.get("not_found", ()):
            L.append("      NOT FOUND (no written event at its place; neither right nor wrong)  %s tile %s %s  was %s" % (w["item"], w["tile"], w["subject"], w["was"]))
    L.append("")
    L.append(landing_line(rep))
    t = rep["tiles"]
    L.append("")
    L.append("tiles: %d (%d from the changes, %d controls), seed %d -> tiles/ (sheet.png), key.json outside the folder"
             % (t["n"], t["cases"], t["controls"], rep["tile_seed"]))
    if "unjudged_tiles" in rep:
        ut = rep["unjudged_tiles"]
        L.append("unjudged tiles: %d, from the changed places Sean has not judged -> unjudged/ (tiles/, key.json outside)" % ut["n"])
    L.append("wall time %.0f s" % rep["wall_seconds"])
    return "\n".join(L)


def load_arms(work: pathlib.Path, plate: str, box_keyed: bool = False, drop: int = 0) -> Dict[str, Any]:
    """The saved arms of a finished lane report, re-read with the CURRENT parser (onsets included). `box_keyed=True`
    strips the onsets (pairing falls back to the old box-centre rule); `drop=N` deletes N written notes from the ON file."""
    arms = {}
    for arm in ("off", "on"):
        old = json.loads((work / ("%s.%s.symbols.json" % (plate, arm))).read_text())
        boxes = {h["rg"]: dict(page=h["page"], box=h["box"], cls=None) for h in old["hosts"] if h.get("rg") and h.get("box")}
        new = parse_symbols((work / ("%s.%s.musicxml" % (plate, arm))).read_text(), boxes)
        keep = {h["rg"] for h in old["hosts"]}
        old["hosts"] = [h for h in new["hosts"] if h["rg"] in keep]
        if box_keyed:
            for h in old["hosts"]:
                h["onset"] = None
        arms[arm] = old
    if drop:
        notes = [i for i, h in enumerate(arms["on"]["hosts"]) if h["kind"] == "note" and not h.get("chord")]
        gone = {notes[(k * len(notes)) // drop] for k in range(drop)}
        arms["on"]["hosts"] = [h for i, h in enumerate(arms["on"]["hosts"]) if i not in gone]
    return arms


def rescore(work: pathlib.Path, plate: str, box_keyed: bool = False, drop: int = 0,
            index_path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """ROADMAP 2.211 control: re-score a finished lane report's saved arms with the CURRENT parser and place pairing.
    `box_keyed=True` is the BEFORE number (it must equal the saved report); `drop=N` plants N real losses in the ON file
    (they must show as N lost notes)."""
    arms = load_arms(work, plate, box_keyed, drop)
    d = diff_arms(arms["off"], arms["on"], tol=0.5 * PLATES[plate]["unit"])
    rec = (work / ("%s.off.mini-record.json" % plate), work / ("%s.on.mini-record.json" % plate))
    jm = judged_moves(rec[0], rec[1], plate, index_path=index_path) if box_keyed else \
        judged_moves(rec[0], rec[1], plate, arms["off"]["hosts"], arms["on"]["hosts"], index_path=index_path)
    return dict(counts=d["counts"], hosts=d["hosts"], paired=d["paired"], judged=jm)


def lost_notes(work: pathlib.Path, plate: str, box_keyed: bool = False, drop: int = 0) -> Dict[str, Any]:
    """The written notes present OFF with no note at their place ON (and the reverse), each with the OFF and ON verdicts
    the mini-record keeps for its box, grouped by what differs (ROADMAP 2.211: this replaces the by-box-id list of
    benchmarks/staff-eraser-2026-10/lost_notes.py -- a twin box that took over a note is not a lost note)."""
    from . import judged as J
    arms = load_arms(work, plate, box_keyed, drop)
    off, on = arms["off"]["hosts"], arms["on"]["hosts"]
    _pairs, lo, ga = pair_hosts(off, on, 0.5 * PLATES[plate]["unit"])
    lost = [off[i] for i in lo if off[i]["kind"] == "note"]
    gained = [on[j] for j in ga if on[j]["kind"] == "note"]
    want = {h["rg"] for h in lost} | {h["rg"] for h in gained}
    said: Dict[str, Dict[str, Dict[str, str]]] = {"off": collections.defaultdict(dict), "on": collections.defaultdict(dict)}
    for arm in ("off", "on"):
        for v in J.iter_array(work / ("%s.%s.mini-record.json" % (plate, arm)), "verdicts"):
            if v.get("subject") in want:
                said[arm][v["subject"]][v["quantity"]] = "%s:%s" % (v.get("outcome"), v.get("reason"))
    groups: Dict[str, List[str]] = collections.defaultdict(list)
    rows = []
    for h in lost:
        so, sn = said["off"].get(h["rg"], {}), said["on"].get(h["rg"], {})
        diff = {q: (so.get(q), sn.get(q)) for q in set(so) | set(sn) if so.get(q) != sn.get(q)}
        why = "; ".join("%s: %s -> %s" % (q, a, b) for q, (a, b) in sorted(diff.items())) or "verdicts identical (dropped later)"
        groups[why].append(h["rg"])
        rows.append(dict(rg=h["rg"], part=h["part"], measure=h["measure"], onset=h["onset"], pitch=h["pitch"], type=h["type"], reason=why))
    return dict(plate=plate, notes=(len(off), len(on)), lost=rows, gained=[g["rg"] for g in gained], groups=dict(groups))


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = "run"
    if argv and argv[0] in ("sample", "arm", "rescore", "lost-notes"):
        cmd = argv.pop(0)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flag", action="append", default=[], help="OMR_X (OFF=0, ON=1), OMR_X=V (ON=V) or OMR_X=OFFV:ONV")
    ap.add_argument("--plates", default="litolff,brahms")
    ap.add_argument("--from", dest="mode", default="auto", choices=("auto", "adjudicate", "gather"))
    ap.add_argument("--out")
    ap.add_argument("--tag", default=None, help="the night record to replay (default DEFAULT_TAG = %s; a tag with no record raises)" % DEFAULT_TAG)
    ap.add_argument("--seed", type=int, default=2188, help="tile draw seed (the page sample's seed is in sample.json)")
    ap.add_argument("--workers", type=int, default=2, help="arm processes at once (<= 4)")
    ap.add_argument("--allow-unknown-flag", action="store_true")
    ap.add_argument("--detector-cache", default=None,
                    help="--from gather: the detector's raw-output cache dir (default library/_shared-records/detector-cache; 'off' = none)")
    ap.add_argument("--cell-map", default=None, metavar="DIR|master",
                    help="ROADMAP 2.231: with --from gather, both arms LOAD the pages' cells from the master cell map "
                         "(DIR, or 'master' = library/_shared-records/cell-maps) instead of re-cutting them")
    ap.add_argument("--replay-gathered", action="store_true",
                    help="--tag names a record GATHERED with the GATHER-side flags on (2.190); replay ADJUDICATE..EXPORT for both arms")
    ap.add_argument("--unjudged-tiles", type=int, default=0, metavar="N",
                    help="ROADMAP 2.244: also cut up to N (<= 12) blind tiles from the changed places no judged tile covers, into DIR/unjudged/")
    ap.add_argument("--reuse", action="store_true", help="development: re-parse the arms already in DIR/work")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--work")
    ap.add_argument("--plate")
    ap.add_argument("--pages", default="")
    ap.add_argument("--arm")
    ap.add_argument("--gathered")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--box-keyed", action="store_true", help="rescore: the old box-centre pairing (the BEFORE number)")
    ap.add_argument("--index", default=None, help="rescore: a judged-tiles.json other than benchmarks/acceptance's (a lane branch's)")
    ap.add_argument("--drop", type=int, default=0, help="rescore: plant N lost notes in the ON file (the control that can fail)")
    a = ap.parse_args(argv)
    if cmd == "sample":
        if SAMPLE_PATH.exists() and not a.force:
            raise SystemExit("%s exists: the sample is frozen. Re-draw only by Sean's word (--force)." % SAMPLE_PATH)
        s = make_sample(seed=2188, n=a.n, tag=a.tag or DEFAULT_TAG)
        SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAMPLE_PATH.write_text(json.dumps(s, indent=1) + "\n")
        print({p: v["pages"] for p, v in s["plates"].items()})
        return 0
    if cmd == "lost-notes":
        for p in [x for x in a.plates.split(",") if x]:
            r = lost_notes(pathlib.Path(a.work), p, a.box_keyed, a.drop)
            print("%s: %d notes written OFF with no note at their place ON (%d notes OFF, %d ON); %d notes only ON"
                  % (p, len(r["lost"]), r["notes"][0], r["notes"][1], len(r["gained"])))
            for k, v in sorted(r["groups"].items(), key=lambda kv: -len(kv[1])):
                print("  %3d  %s\n        %s" % (len(v), k, ", ".join(v)))
        return 0
    if cmd == "rescore":
        for p in [x for x in a.plates.split(",") if x]:
            r = rescore(pathlib.Path(a.work), p, a.box_keyed, a.drop, pathlib.Path(a.index) if a.index else None)
            j = r["judged"]
            print("%s  %s\n  judged: right->wrong %s | wrong->right %s | right->lost %d | same music at its place %d | not found %d"
                  % (p, format_counts(r["counts"]), blue_count(j["worse"]), blue_count(j["better"]), len(j["lost"]), len(j.get("same_music", ())), len(j.get("not_found", ()))))
            print("  judged, OFF wrote nothing there: unwritten->wrong %d (of which invented from non-note ink %d; must be 0) | unwritten->right %d | invented->removed %d (good)"
                  % (len(j.get("unwritten_wrong", ())), sum(1 for w in j.get("unwritten_wrong", ()) if w.get("invented")),
                     len(j.get("unwritten_right", ())), len(j.get("invented_removed", ()))))
            for w in j["worse"]:
                print("    RIGHT->WRONG", "(blue)" if w.get("blue") else "", w["item"], w["tile"], w["subject"], w["now"])
            for w in j["better"]:
                print("    wrong->right", "(blue)" if w.get("blue") else "", w["item"], w["tile"], w["subject"])
            for w in j.get("unwritten_wrong", ()):
                print("    UNWRITTEN->WRONG", w["item"], w["tile"], w["subject"], "Sean:", w["answer"], "OFF:", w["off"], "now:", w["now"])
            for w in j.get("not_found", ()):
                print("    NOT FOUND", w["item"], w["tile"], w["subject"])
        return 0
    sample = load_sample()
    tag = a.tag or DEFAULT_TAG
    if cmd in ("run", "arm"):
        check_tag(tag, [p for p in (a.plates or "litolff,brahms").split(",") if p] if cmd == "run" else [a.plate], sample)
    if cmd == "arm":       # internal worker: --flag NAME=OFFV:ONV exactly as the parent wrote it
        flags = [(n, v.split(":")[0], v.split(":")[1]) for n, v in (f.split("=", 1) for f in a.flag)]
        run_arm(a.plate, a.arm, flags, a.mode, tag, pathlib.Path(a.work), [int(x) for x in a.pages.split(",") if x],
                gather_record=pathlib.Path(a.gathered) if a.gathered else None)
        return 0
    flags = parse_flags(a.flag)
    if not a.out:
        raise SystemExit("--out DIR is required")
    plates = [p for p in a.plates.split(",") if p]
    mode, notes = decide_from(a.mode, flags, a.allow_unknown_flag, a.replay_gathered)
    if os.environ.get("LANE_REPORT_SAMPLE"):
        notes.append("NOT THE FROZEN SAMPLE: %s (a development control)" % SAMPLE_PATH)
    if not flags:
        notes.append("no --flag: OFF and ON are the same tree (the identity control)")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    global DETECTOR_CACHE
    if a.detector_cache:
        DETECTOR_CACHE = None if a.detector_cache == "off" else pathlib.Path(a.detector_cache)
    global CELL_MAP
    if a.cell_map:
        CELL_MAP = CELL_MAP_ROOT if a.cell_map == "master" else pathlib.Path(a.cell_map)
        if mode != "gather":
            notes.append("--cell-map applies to a re-gather only: --from %s replays the saved record's own cells" % mode)
            CELL_MAP = None
        else:
            for p in plates:
                notes.append("cells LOADED from master %s (%s) for both arms" % (cell_map_version(p), p))
    rep = run_report(flags, plates, mode, out, tag, a.seed, min(4, max(1, a.workers)), sample, notes, reuse=a.reuse,
                     unjudged_tiles=min(12, max(0, a.unjudged_tiles)))
    print(render_text(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
