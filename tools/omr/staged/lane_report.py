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
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

DERIVED_CHECK = False
ROOT = pathlib.Path(__file__).resolve().parents[3]
SAMPLE_PATH = pathlib.Path(os.environ.get("LANE_REPORT_SAMPLE") or ROOT / "benchmarks" / "lane-report" / "sample.json")  # env: a one-page control (2.189)
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
RECORDS = LIB / "_shared-records"
DETECTOR_CACHE: Optional[pathlib.Path] = RECORDS / "detector-cache"      # ROADMAP 2.189: OFF and ON share it; None = no cache
LOCK = RECORDS / ".record-load.lock"
ORANGE = (255, 140, 0)

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


def make_sample(seed: int = 2188, n: int = 8, tag: str = "20261020-night") -> Dict[str, Any]:
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


def parse_symbols(xml: str, boxes: Dict[str, dict]) -> Dict[str, Any]:
    """The written file as symbols: `hosts` (notes / rests with their sub-marks), `loose` (directions anchored to the
    next note, and attributes) -- each with page and centre where the glyph key gives one."""
    root = ET.fromstring(xml)
    hosts: List[dict] = []
    loose: List[dict] = []

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
            for el in m:
                tag = el.tag
                if tag == "attributes":
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
                                      chord=el.find("chord") is not None))
                    for d in pending:
                        d.update(page=pg, cx=cx, cy=cy, box=bx, rg=rg)
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
    (work / (stem + ".symbols.json")).write_text(json.dumps(out, default=str))
    return out


# ───────────────────────────── 6. the diff (pure counting) ─────────────────────────────

def pair_hosts(off: Sequence[dict], on: Sequence[dict], tol: float) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Pair two arms' written notes/rests by page position: same page, centres within `tol` px, nearest first, one to
    one. A host with no page position (no glyph key) is never paired. Returns (pairs, unmatched_off, unmatched_on)."""
    cands = []
    by_page: Dict[Any, List[int]] = collections.defaultdict(list)
    for j, h in enumerate(on):
        if h.get("page") is not None and h.get("cx") is not None:
            by_page[h["page"]].append(j)
    for i, h in enumerate(off):
        if h.get("page") is None or h.get("cx") is None:
            continue
        for j in by_page.get(h["page"], ()):
            g = on[j]
            d = ((h["cx"] - g["cx"]) ** 2 + (h["cy"] - g["cy"]) ** 2) ** 0.5
            if d <= tol:
                cands.append((d, i, j))
    cands.sort()
    used_i, used_j, pairs = set(), set(), []
    for _d, i, j in cands:
        if i in used_i or j in used_j:
            continue
        used_i.add(i)
        used_j.add(j)
        pairs.append((i, j))
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

def judged_moves(off_rec: pathlib.Path, on_rec: pathlib.Path, doc: str) -> Dict[str, Any]:
    """Sean's judged tiles scored against the OFF and the ON mini-records (tools.omr.staged.judged, one scorer)."""
    from . import judged as J
    idx = json.loads(J.INDEX_PATH.read_text())
    a = J.score(idx, off_rec, doc)
    b = J.score(idx, on_rec, doc)
    return compare_judged(a["tiles"], b["tiles"])


def compare_judged(off_tiles: Sequence[dict], on_tiles: Sequence[dict]) -> Dict[str, Any]:
    """Per judged tile, OFF status -> ON status. `worse` = right -> wrong (must be 0); `lost` = right -> narrowed /
    abstained / not_found; `better` = wrong -> right."""
    def k(t):
        return (t["item"], t["tile"])
    on_by = {k(t): t for t in on_tiles}
    worse, lost, better, n_scored = [], [], [], 0
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
    return dict(worse=worse, lost=lost, better=better, scored=n_scored)


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
            if sig in seen:
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
        cand = [s for s in ctrl_pool.get(k, []) if (s["plate"], s["rg"]) not in taken]
        if cand:
            s = rng.choice(cand)
            controls.append(dict(s, role="control", side="unchanged"))
            taken.add((s["plate"], s["rg"]))
    items = cases + controls
    rng.shuffle(items)
    return items


def cut_tiles(items: List[dict], out_dir: pathlib.Path, tile_dir_name: str = "tiles") -> Dict[str, Any]:
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
        key.append({k: v for k, v in it.items() if k not in ("cx", "cy")} | dict(tile=n, crop_origin=[x0, y0]))
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
        "that we might have written wrongly?\n\nAnswer by tile number.\n")
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))
    return dict(n=len(key), cases=sum(k["role"] == "case" for k in key), controls=sum(k["role"] == "control" for k in key))


# ───────────────────────────── 9. the command ─────────────────────────────

def _spawn(args: List[str], env: Dict[str, str], logpath: pathlib.Path) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-u", "-m", "tools.omr.staged.lane_report"] + args, cwd=str(ROOT), env=env,
                            stdout=open(logpath, "w"), stderr=subprocess.STDOUT)


def run_report(flags: Sequence[Tuple[str, str, str]], plates: Sequence[str], mode: str, out: pathlib.Path,
               tag: str, seed: int, workers: int, sample: Dict[str, Any], note_lines: Sequence[str],
               reuse: bool = False) -> Dict[str, Any]:
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
            rp = work / ("%s.%s.gathered.record.json" % (p, a))
            env = dict(env0)
            for name, off, on in flags:
                env[name] = on if a == "on" else off
            env["OMR_SURYA_KEEP_ALIVE"] = "0"
            if DETECTOR_CACHE is not None:      # ROADMAP 2.189: the raw detector output, read once, for both arms and every later run
                env["OMR_DETECTOR_CACHE"] = str(DETECTOR_CACHE)
            else:
                env.pop("OMR_DETECTOR_CACHE", None)
            cmd = [sys.executable, "-u", "-m", "tools.omr.staged", str(LIB / PLATES[p]["pdf"]), "--pages",
                   ",".join(map(str, pages[p])), "--dpi", "600", "--weights", "auto", "--route-weights", "--out", str(rp)]
            print("  gather %s %s pages %s ..." % (p, a, pages[p]), flush=True)
            logp = work / ("%s.%s.gather.log" % (p, a))
            r = subprocess.run(cmd, cwd=str(ROOT), env=env, stdout=open(logp, "w"), stderr=subprocess.STDOUT)
            if r.returncode != 0 or not rp.exists():
                raise SystemExit("gather failed for %s %s (see %s)" % (p, a, logp))
            gather_recs[(p, a)] = rp
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
    all_changes, all_same = {}, {}
    for p in plates:
        off, on = done[(p, "off")], done[(p, "on")]
        d = diff_arms(off, on, tol=0.5 * PLATES[p]["unit"])
        jm = judged_moves(work / ("%s.off.mini-record.json" % p), work / ("%s.on.mini-record.json" % p), p)
        all_changes[p], all_same[p] = d["changes"], d["same"]
        rep["plates"][p] = dict(pages=pages[p], counts=d["counts"], hosts=d["hosts"], paired=d["paired"],
                                red_bars=[off["red_bars"], on["red_bars"]],
                                notes_not_written=[off["notes_not_written"], on["notes_not_written"]],
                                control=control_of(off["control"], on["control"]), judged=jm, seconds=[off["seconds"], on["seconds"]])
    items = pick_tiles(all_changes, all_same, seed)
    rep["tiles"] = cut_tiles(items, out) if items else dict(n=0, cases=0, controls=0)
    rep["tile_seed"] = seed
    rep["wall_seconds"] = round(time.time() - t0, 1)
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "report.txt").write_text(render_text(rep) + "\n")
    return rep


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
        L.append("  Sean's judged answers (%d tiles on these pages): right->wrong %d | right->narrowed/abstained/gone %d | wrong->right %d"
                 % (j["scored"], len(j["worse"]), len(j["lost"]), len(j["better"])))
        for w in j["worse"]:
            L.append("      RIGHT->WRONG  %s tile %s %s  Sean: %s  now: %s" % (w["item"], w["tile"], w["subject"], w["answer"], w["now"]))
        for w in j["lost"][:10]:
            L.append("      right->%s  %s tile %s %s" % (w["now"], w["item"], w["tile"], w["subject"]))
    t = rep["tiles"]
    L.append("")
    L.append("tiles: %d (%d from the changes, %d controls), seed %d -> tiles/ (sheet.png), key.json outside the folder"
             % (t["n"], t["cases"], t["controls"], rep["tile_seed"]))
    L.append("wall time %.0f s" % rep["wall_seconds"])
    return "\n".join(L)


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = "run"
    if argv and argv[0] in ("sample", "arm"):
        cmd = argv.pop(0)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flag", action="append", default=[], help="OMR_X (OFF=0, ON=1), OMR_X=V (ON=V) or OMR_X=OFFV:ONV")
    ap.add_argument("--plates", default="litolff,brahms")
    ap.add_argument("--from", dest="mode", default="auto", choices=("auto", "adjudicate", "gather"))
    ap.add_argument("--out")
    ap.add_argument("--tag", default=None, help="the night record to replay (default: the sample file's)")
    ap.add_argument("--seed", type=int, default=2188, help="tile draw seed (the page sample's seed is in sample.json)")
    ap.add_argument("--workers", type=int, default=2, help="arm processes at once (<= 4)")
    ap.add_argument("--allow-unknown-flag", action="store_true")
    ap.add_argument("--detector-cache", default=None,
                    help="--from gather: the detector's raw-output cache dir (default library/_shared-records/detector-cache; 'off' = none)")
    ap.add_argument("--replay-gathered", action="store_true",
                    help="--tag names a record GATHERED with the GATHER-side flags on (2.190); replay ADJUDICATE..EXPORT for both arms")
    ap.add_argument("--reuse", action="store_true", help="development: re-parse the arms already in DIR/work")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--work")
    ap.add_argument("--plate")
    ap.add_argument("--pages", default="")
    ap.add_argument("--arm")
    ap.add_argument("--gathered")
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args(argv)
    if cmd == "sample":
        if SAMPLE_PATH.exists() and not a.force:
            raise SystemExit("%s exists: the sample is frozen. Re-draw only by Sean's word (--force)." % SAMPLE_PATH)
        s = make_sample(seed=2188, n=a.n, tag=a.tag or "20261020-night")
        SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAMPLE_PATH.write_text(json.dumps(s, indent=1) + "\n")
        print({p: v["pages"] for p, v in s["plates"].items()})
        return 0
    sample = load_sample()
    tag = a.tag or sample["record_tag"]
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
    rep = run_report(flags, plates, mode, out, tag, a.seed, min(4, max(1, a.workers)), sample, notes, reuse=a.reuse)
    print(render_text(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
