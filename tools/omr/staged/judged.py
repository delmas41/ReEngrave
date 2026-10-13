"""ROADMAP 2.106 step 2 -- an index of Sean's answers, and a re-scorer.

    python3 -m tools.omr.staged.judged build            # rewrite the index
    python3 -m tools.omr.staged.judged build --check    # exit 1 if the committed index is stale
    python3 -m tools.omr.staged.judged score REC.json --doc litolff [--json OUT]
    python3 -m tools.omr.staged.judged stats

Every `out/print/**/answers.json` is Sean's word on a gallery of tiles; the
tile's `manifest.json` says which subject each one was. 28 galleries carry a
glyph key and nothing joined them, so every new rule cut its tiles without
asking what was already judged (`docs/plan-2026-10-12-inference-principles.md`
§4, "Re-using Sean's answers"). This module is that join:

* `build_index()` normalises each answered tile to
  `{item, tile, doc, subject, subjects, answer, question_kind, answer_kind,
  value, date, ...}` and writes ONE committed file,
  `benchmarks/acceptance/judged-tiles.json`.
* `score(index, record_path, doc)` reports, for each judged subject, what the
  record now says versus Sean: `right / wrong / narrowed / abstained /
  not_found / unscored`, per item.

## What this is NOT

* **Sean's answer is kept verbatim** (`answer`) beside any parse of it
  (`value`). A parse that is not certain is `None`: an answer is never turned
  into a number it did not say (CLAUDE.md rule 8). Mixed or multi-part answers
  ("6/8, two voices ...") stay `value=None`, `answer_kind="other"`.
* **A subject key is a snapshot of one gather.** A glyph index is the
  detector's output order for that cell, so the same mark on a re-gather can
  carry a different key. `not_found` therefore means *this record has no
  verdict at that key*, not *the mark is gone*; the scorer never matches by
  box overlap (that is `readout diff`'s job, and it needs the page box this
  index keeps in `page_box` where the manifest gave one).
* **The scorer compares verdicts, not exported files.** Until further notice
  every test is GATHER + ADJUDICATE (CLAUDE.md §6b), so it reads the standing
  verdict of `Q.DURATION`, `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`,
  `Q.UNBOXED_INK_IS_A_REST`, `Q.NOTEHEAD_IS_AN_EIGHTH_REST` and `Q.ARC_KIND`
  and nothing downstream. A question kind with no comparator here is
  `unscored` with its kind named; add the comparator when a lane needs it.
* **Big records are streamed.** The Brahms night record is ~6 GB; the scorer
  reads only the `verdicts` array, one object at a time, and keeps the few
  that belong to a judged subject.
"""
from __future__ import annotations

import argparse
import codecs
import json
import mmap
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

DERIVED_CHECK = True

_ROOT = pathlib.Path(__file__).resolve().parents[3]
PRINT_DIR = _ROOT / "out" / "print"
INDEX_PATH = _ROOT / "benchmarks" / "acceptance" / "judged-tiles.json"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Normalising what Sean said
# ─────────────────────────────────────────────────────────────────────────────

_NUM_BEATS = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25, "32": 0.125,
              "64": 0.0625}
_WORD_BEATS = {"whole": 4.0, "half": 2.0, "quarter": 1.0, "eighth": 0.5,
               "8th": 0.5, "sixteenth": 0.25, "16th": 0.25,
               "thirty-second": 0.125, "32nd": 0.125}
_VALUE = (r"(?P<dot>dot(?:ted)?\s*|dot\.\s*)?"
          r"(?P<v>1|2|4|8|16|32|64|whole|half|quarter|eighth|8th|sixteenth|"
          r"16th|thirty-second|32nd)(?:th|nd|st)?"
          r"(?:\s+(?P<what>note|notes|rest))?")
_ONE = re.compile(r"^\s*" + _VALUE + r"\s*\.?\s*$", re.I)
_NOT_A_NOTE = (
    (re.compile(r"barline|bar line|double bar", re.I), "barline"),
    (re.compile(r"ledger", re.I), "ledger_line"),
    (re.compile(r"\bclef\b", re.I), "clef"),
    (re.compile(r"time sig|\bmeter\b|\bc for common|^\s*\d+/\d+\s*$", re.I),
     "meter"),
    (re.compile(r"trem|slash", re.I), "tremolo"),
    (re.compile(r"accidental|\bacc\b|^(flat|sharp|natural)\b|\bkey\b", re.I),
     "accidental"),
    (re.compile(r"\bdynamic\b|^\s*(p{1,3}|f{1,3}|sf|mf|mp)\s*$", re.I),
     "dynamic"),
    (re.compile(r"end of (a )?slur|\bslur end", re.I), "other_ink"),
    (re.compile(r"not a (note|notehead)", re.I), "not_a_note"),
)


def _beats(v: str, dotted: bool) -> float:
    v = v.lower()
    b = _NUM_BEATS.get(v) if v in _NUM_BEATS else _WORD_BEATS[v]
    return b * 1.5 if dotted else b


def parse_answer(text: Any) -> Tuple[str, Any]:
    """`(answer_kind, value)` of what Sean wrote, or `("other", None)`.

    Conservative: the WHOLE answer must be the recognised form. `value` for a
    duration or a rest is beats in quarter notes (the unit `Q.DURATION`'s
    `beats` is in); for `not_a_note` it is the named thing; for an arc the
    word.
    """
    if not isinstance(text, str):
        return "other", None
    t = re.sub(r"^\s*\d+\.\s+(?=\S)", "", text.strip())   # "6. 8 rest"
    low = t.lower()
    if not t:
        return "other", None
    # several values: "4,4"  "8, 8"  "dotted quarter, quarter"
    parts = [p.strip() for p in re.split(r"\s*,\s*|\s+and\s+", t) if p.strip()]
    if len(parts) > 1:
        ms = [_ONE.match(p) for p in parts]
        if all(ms) and not any((m.group("what") or "").lower() == "rest"
                               for m in ms):
            return "duration_multi", [
                _beats(m.group("v"), bool(m.group("dot"))) for m in ms]
    m = _ONE.match(t)
    if m:
        what = (m.group("what") or "").lower()
        beats = _beats(m.group("v"), bool(m.group("dot")))
        if what == "rest":
            return "rest", beats
        return "duration", beats
    if low in ("tie", "slur"):
        return "arc", low
    first = low.split(" -")[0].split(" (")[0]
    if first in ("tie", "slur"):
        return "arc", first
    if re.match(r"^whole (note )?rest$", low):
        return "rest", 4.0
    if low in ("y", "n"):
        return "yes_no", low == "y"
    # a short answer that is not led by a value; a long one explains, and an
    # explanation that mentions a barline is not "it is a barline"
    led_by_value = re.match(r"\s*" + _VALUE + r"\b", t, re.I) is not None
    if len(t) <= 45 and not led_by_value and not re.search(r"\bnot the\b", low):
        for pat, name in _NOT_A_NOTE:
            if pat.search(t) and not re.search(r"\brest\b", low):
                return "not_a_note", name
    return "other", None


def question_kind(tile: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    q = " ".join(str(x) for x in (tile.get("question"), manifest.get("question"),
                                  tile.get("rule"), tile.get("kind"),
                                  tile.get("tile_is_for")) if x).lower()
    if "printed value" in q or "note value" in q or "value of the note" in q \
            or "what is the printed" in q:
        return "duration"
    if "tie or a slur" in q:
        return "arc"
    if "notehead, a rest, or something else" in q or "is the box" in q:
        return "identity"
    if "belong to" in q or "which staff" in q:
        return "owner"
    if "dynamic" in q:
        return "dynamic"
    if "stem" in q:
        return "stem"
    if "meter" in q or "time signature" in q:
        return "meter"
    if tile.get("kind") in ("mark", "note"):
        return "identity"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Reading the two files
# ─────────────────────────────────────────────────────────────────────────────

_META = frozenset({
    "date", "judge", "via", "verbatim", "scoring", "scoring_by_manager",
    "summary", "source", "key", "question", "words", "raw", "convention",
    "score", "order", "who", "by", "agree", "wrong", "of", "scored_by",
    "answered", "branch_of_tiles", "reading", "per_tile", "meter_answer",
    "scored", "truth_file", "quote", "verdict", "answers", "tiles"})
_TILE_KEY = re.compile(r"^(?:tile_\d+|control_\d+|\d+(?:_followup)?|"
                       r"(?:brahms|litolff)_\d+)$")


def _verb(v: Any) -> Tuple[str, Dict[str, Any]]:
    """Sean's words from one answer cell, plus whatever else the cell held."""
    if isinstance(v, str):
        return v, {}
    if isinstance(v, dict):
        for k in ("sean", "values", "answer"):
            if isinstance(v.get(k), str):
                return v[k], {x: y for x, y in v.items() if x != k}
        return json.dumps(v, sort_keys=True), dict(v)
    return json.dumps(v), {}


def answer_cells(d: Any) -> Tuple[Dict[str, Any], Dict[str, Tuple[str, Dict[str, Any]]]]:
    """`(meta, {tile key: (verbatim, extra)})` for any of the answer-file
    shapes in `out/print`. Meta carries `date` and the gallery-level
    `verbatim`."""
    meta: Dict[str, Any] = {}
    cells: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    if not isinstance(d, dict):
        return meta, cells
    for k in ("date", "answered", "verbatim", "words", "raw", "summary",
              "judge", "who", "by", "via", "source"):
        if isinstance(d.get(k), str):
            meta[k] = d[k]

    def take(src: Any) -> None:
        if isinstance(src, dict):
            for k, v in src.items():
                cells[str(k)] = _verb(v)
        elif isinstance(src, list):
            for e in src:
                if isinstance(e, dict) and "n" in e:
                    cells[str(e["n"])] = _verb(e)

    if isinstance(d.get("answers"), (dict, list)):
        take(d["answers"])
    elif isinstance(d.get("tiles"), (dict, list)):
        take(d["tiles"])
    elif isinstance(d.get("reading"), dict):
        take(d["reading"])
    elif isinstance(d.get("per_tile"), dict):
        for k, v in d["per_tile"].items():
            if isinstance(v, dict) and v.get("whole_bar_rest"):
                cells[str(k)] = ("whole rest", dict(v))
            else:
                cells[str(k)] = _verb(v)
    else:
        for k, v in d.items():
            if k in _META or not _TILE_KEY.match(str(k)):
                continue
            cells[str(k)] = _verb(v)
    if not cells and "quote" in d:           # 2.13b: one verdict for the set
        cells["all"] = (str(d["quote"]), {"verdict": d.get("verdict")})
    return meta, cells


def _stem(x: Any) -> Optional[str]:
    if isinstance(x, str):
        return pathlib.Path(x).stem
    return None


def manifest_tiles(d: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if isinstance(d, list):
        return {}, [t for t in d if isinstance(t, dict)]
    if not isinstance(d, dict):
        return {}, []
    for k in ("tiles", "heads", "arcs", "slips"):
        if isinstance(d.get(k), list):
            return d, [t for t in d[k] if isinstance(t, dict)]
    return d, []


def _aliases(t: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    n = t.get("n")
    if isinstance(n, int):
        out += [str(n), "tile_%02d" % n]
    if isinstance(t.get("tile"), int):
        out += [str(t["tile"]), "tile_%02d" % t["tile"]]
    for k in ("id", "slip"):
        if isinstance(t.get(k), (str, int)):
            out.append(str(t[k]))
    for k in ("file", "tile"):
        s = _stem(t.get(k))
        if s:
            out.append(s)
    return list(dict.fromkeys(out))


def _doc_of(t: Dict[str, Any], manifest: Dict[str, Any]) -> Optional[str]:
    h = t.get("hidden") if isinstance(t.get("hidden"), dict) else {}
    cand = (t.get("doc"), t.get("document"), t.get("movement"),
            h.get("movement"), t.get("label"), t.get("plate"),
            manifest.get("label"), manifest.get("plate"))
    for c in cand:
        if not isinstance(c, str):
            continue
        low = c.lower()
        if low.startswith("lit") or "litolff" in low or "beethoven" in low:
            return "litolff"
        if low.startswith("brah") or "breitkopf" in low or "317803" in low:
            return "brahms"
        if low.startswith("dvor"):
            return "dvorak"
        if low.startswith("tchai"):
            return "tchaikovsky"
        return low
    return None


def _subjects_of(t: Dict[str, Any]) -> Tuple[List[str], str]:
    """`(subject keys, kind)` -- kind is glyph / cell / none. Only keys the
    manifest actually gave; a key is never constructed from a guess."""
    h = t.get("hidden") if isinstance(t.get("hidden"), dict) else {}
    for raw in (t.get("subject"), t.get("glyph"), h.get("key"),
                t.get("subject_2_23")):
        if isinstance(raw, str) and raw.startswith("glyph/"):
            return [raw], "glyph"
        if isinstance(raw, list) and raw and all(
                isinstance(x, str) and x.startswith("glyph/") for x in raw):
            return list(raw), "glyph"
    if isinstance(t.get("cell"), str) and t["cell"].startswith("cell/"):
        return [t["cell"]], "cell"
    for k in ("bar", "cell"):
        v = t.get(k)
        if isinstance(v, list) and len(v) == 4 and all(
                isinstance(x, int) for x in v):
            return ["cell/%d/%d/%d/%d" % tuple(v)], "cell"
    if all(isinstance(t.get(k), int) for k in ("page", "system", "staff", "cell")):
        return ["cell/%d/%d/%d/%d" % (t["page"], t["system"], t["staff"],
                                      t["cell"])], "cell"
    return [], "none"


def _page_box(t: Dict[str, Any]) -> Optional[List[float]]:
    for k in ("page_box_600dpi", "page_box", "window_page_px"):
        v = t.get(k)
        if isinstance(v, list) and len(v) == 4 and all(
                isinstance(x, (int, float)) for x in v):
            return [float(x) for x in v]
    return None


def _git_date(path: pathlib.Path) -> Optional[str]:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)],
                           cwd=str(_ROOT), capture_output=True, text=True)
        return r.stdout.strip() or None
    except Exception:                                         # noqa: BLE001
        return None


def _date_in(s: Any) -> Optional[str]:
    m = re.search(r"20\d\d-\d\d-\d\d", s) if isinstance(s, str) else None
    return m.group(0) if m else None


def item_rows(answers_path: pathlib.Path, root: pathlib.Path = PRINT_DIR
              ) -> List[Dict[str, Any]]:
    """The normalised tiles of one gallery."""
    item = str(answers_path.parent.relative_to(root))
    d = json.loads(answers_path.read_text())
    meta, cells = answer_cells(d)
    man_path = answers_path.parent / "manifest.json"
    mmeta, tiles = (manifest_tiles(json.loads(man_path.read_text()))
                    if man_path.exists() else ({}, []))
    by_alias: Dict[str, Dict[str, Any]] = {}
    for t in tiles:
        for a in _aliases(t):
            by_alias.setdefault(a, t)
    date = (meta.get("date") or meta.get("answered") or _date_in(meta.get("source"))
            or _date_in(d.get("source") if isinstance(d, dict) else None)
            or _git_date(answers_path))
    rows: List[Dict[str, Any]] = []
    for key, (verb, extra) in sorted(cells.items(), key=lambda kv: kv[0]):
        t = by_alias.get(key) or by_alias.get(key.split("_followup")[0]) or {}
        subs, skind = _subjects_of(t)
        kind, value = parse_answer(verb)
        h = t.get("hidden") if isinstance(t.get("hidden"), dict) else {}
        rows.append({
            "item": item, "tile": key,
            "doc": _doc_of(t, mmeta) if t else None,
            "subject": subs[0] if len(subs) == 1 else None,
            "subjects": subs if len(subs) > 1 else None,
            "subject_kind": skind,
            "page_box": _page_box(t) if t else None,
            "answer": verb,
            "question_kind": question_kind(t, mmeta) if t else "unknown",
            "answer_kind": kind, "value": value,
            "date": date,
            "control": key.startswith("control") or bool(
                t.get("control") or h.get("control")),
            "followup": key.endswith("_followup"),
        })
    return rows


def build_index(root: pathlib.Path = PRINT_DIR) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for p in sorted(root.rglob("answers.json")):
        rows.extend(item_rows(p, root))
    return {"what": "Sean's judged tiles, one row per answered tile "
                    "(tools/omr/staged/judged.py; rebuild with "
                    "`python3 -m tools.omr.staged.judged build`)",
            "n_tiles": len(rows),
            "n_items": len({r["item"] for r in rows}),
            "tiles": rows}


def write_index(path: pathlib.Path = INDEX_PATH,
                root: pathlib.Path = PRINT_DIR) -> Dict[str, Any]:
    idx = build_index(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(idx, indent=1, sort_keys=True) + "\n")
    return idx


# ─────────────────────────────────────────────────────────────────────────────
# 3. Streaming the standing verdicts of a (possibly 6 GB) record
# ─────────────────────────────────────────────────────────────────────────────

_QUANTITIES = ("duration", "notehead_is_not_a_notehead",
               "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest",
               "arc_kind")


def iter_verdicts(path: pathlib.Path, chunk: int = 1 << 26) -> Iterator[Dict[str, Any]]:
    """Every object of the record's `verdicts` array, one at a time, without
    loading the file. `record_io.load_record` is the way to read a record whole;
    this reads one array of it."""
    return iter_array(path, "verdicts", chunk)


def iter_array(path: pathlib.Path, key: str, chunk: int = 1 << 26
               ) -> Iterator[Dict[str, Any]]:
    """The objects of the first JSON array under `"key"` (compact or spaced)."""
    with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
        found = re.compile(b'"' + key.encode() + b'"\\s*:\\s*\\[').search(m)
        if found is None:
            return
        start = found.end()
        dec = json.JSONDecoder()
        utf = codecs.getincrementaldecoder("utf-8")()
        buf, pos, eof = "", 0, False
        at = start
        while True:
            while not eof and len(buf) - pos < chunk // 4:
                raw = m[at:at + chunk]
                at += len(raw)
                if not raw:
                    eof = True
                    buf = buf[pos:] + utf.decode(b"", final=True)
                    pos = 0
                    break
                buf = buf[pos:] + utf.decode(raw)
                pos = 0
            while pos < len(buf) and buf[pos] in " \n\r\t,":
                pos += 1
            if pos >= len(buf):
                if eof:
                    return
                continue
            if buf[pos] == "]":
                return
            try:
                obj, end = dec.raw_decode(buf, pos)
            except json.JSONDecodeError:
                if eof:
                    return
                # an object straddles the chunk: read more
                raw = m[at:at + chunk]
                at += len(raw)
                if not raw:
                    eof = True
                    buf = buf[pos:] + utf.decode(b"", final=True)
                    pos = 0
                else:
                    buf = buf[pos:] + utf.decode(raw)
                    pos = 0
                continue
            pos = end
            yield obj


def page_boxes(path: pathlib.Path, subjects: Iterable[str]
               ) -> Dict[str, List[float]]:
    """`{subject: bbox_page_px}` from the record's gathered boxes (a detector
    box, or the ink cluster GATHER measured for an unboxed mark). The
    `observations` array is the front of the file; the scan stops at its end."""
    want = set(subjects)
    out: Dict[str, List[float]] = {}
    for o in iter_array(path, "observations"):
        sub = o.get("subject")
        if sub in want and sub not in out:
            b = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(b, list) and len(b) == 4:
                out[sub] = [float(x) for x in b]
    return out


def box_matches(rec_box: Sequence[float], tile_box: Sequence[float],
                slack: float = 40.0) -> bool:
    """Centre of the record's box inside the tile's bracket (+/- `slack` px at
    600 dpi). A key alone does not name a document: `glyph/3/0/2/3/13` exists
    in both movements."""
    cx, cy = (rec_box[0] + rec_box[2]) / 2, (rec_box[1] + rec_box[3]) / 2
    return (tile_box[0] - slack <= cx <= tile_box[2] + slack
            and tile_box[1] - slack <= cy <= tile_box[3] + slack)


def standing_for(path: pathlib.Path, subjects: Iterable[str],
                 quantities: Sequence[str] = _QUANTITIES
                 ) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """`{(subject, quantity): standing verdict dict}` for the given subjects.
    Standing = the last verdict on that (subject, quantity) that no other
    verdict supersedes."""
    want = set(subjects)
    qs = set(quantities)
    kept: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for v in iter_verdicts(path):
        if v.get("subject") in want and v.get("quantity") in qs:
            kept[(v["subject"], v["quantity"])].append({
                k: v.get(k) for k in ("id", "subject", "quantity", "outcome",
                                      "value", "decider", "reason", "margin",
                                      "supersedes", "candidates", "detail")})
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for key, vs in kept.items():
        superseded = {x["supersedes"] for x in vs if x.get("supersedes")}
        live = [x for x in vs if x["id"] not in superseded] or vs
        out[key] = live[-1]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4. Scoring a record against the index
# ─────────────────────────────────────────────────────────────────────────────

STATUSES = ("right", "wrong", "narrowed", "abstained", "not_found",
            "unscored", "other_doc", "doc_unresolved")
_EPS = 1e-6


def _beats_of(v: Any) -> Optional[float]:
    if isinstance(v, dict) and isinstance(v.get("beats"), (int, float)):
        return float(v["beats"])
    return None


def _cand_beats(cands: Any) -> List[float]:
    out: List[float] = []
    for c in cands or ():
        b = _beats_of(c.get("value") if isinstance(c, dict) else None)
        if b is not None:
            out.append(b)
    return out


def _near(a: float, b: float) -> bool:
    return abs(a - b) < _EPS


def _duration(sub: str, want: float, S: Dict) -> Tuple[str, str]:
    v = S.get((sub, "duration"))
    if v is None:
        n = S.get((sub, "notehead_is_not_a_notehead"))
        if n and n["outcome"] == "decided" and n["value"] is True:
            return "wrong", "refused as not a note (%s)" % n["reason"]
        return "not_found", "no duration verdict at this key"
    b = _beats_of(v.get("value"))
    if v["outcome"] == "decided" and b is not None:
        note = "decided %.3g beats (%s)" % (b, v["reason"])
        if not _near(b, want) and _near(b * 1.5, want):
            # Sean's dotted value over a head read undotted: the dot is its
            # own mark (`dot_role`); the head's base value is what matched
            note += "; head matches the UNDOTTED value of Sean's dotted answer"
        return ("right" if _near(b, want) else "wrong", note)
    cands = _cand_beats(v.get("candidates"))
    if v["outcome"] == "narrowed":
        if any(_near(c, want) for c in cands):
            return "narrowed", "narrowed %s, answer in set (%s)" % (
                sorted(set(cands)), v["reason"])
        return "wrong", "narrowed %s, answer NOT in set (%s)" % (
            sorted(set(cands)), v["reason"])
    return "abstained", "abstained (%s)" % v["reason"]


def _rest(sub: str, want: float, S: Dict) -> Tuple[str, str]:
    u = S.get((sub, "unboxed_ink_is_a_rest"))
    if u is not None:
        if u["outcome"] != "decided":
            return "abstained", "unboxed rest abstained (%s)" % u["reason"]
        val = u["value"]
        got = {"eighth": 0.5, "quarter": 1.0}.get(val)
        if val is False:
            return "wrong", "read as not a rest (%s)" % u["reason"]
        return ("right" if got is not None and _near(got, want) else "wrong",
                "read as %s rest (%s)" % (val, u["reason"]))
    e = S.get((sub, "notehead_is_an_eighth_rest"))
    if e is not None:
        if e["outcome"] != "decided":
            return "abstained", "narrow-box rest abstained (%s)" % e["reason"]
        if e["value"] is True:
            return ("right" if _near(want, 0.5) else "wrong",
                    "reinstated as an eighth rest (%s)" % e["reason"])
        return "wrong", "narrow box read as not a rest (%s)" % e["reason"]
    n = S.get((sub, "notehead_is_not_a_notehead"))
    if n is not None and n["outcome"] == "decided":
        if n["value"] is True:
            return "right", "refused as not a note (%s)" % n["reason"]
        return "wrong", "kept as a notehead"
    return "not_found", "no rest verdict at this key"


def _not_a_note(sub: str, what: str, S: Dict) -> Tuple[str, str]:
    u = S.get((sub, "unboxed_ink_is_a_rest"))
    if u is not None and u["outcome"] == "decided":
        return ("right" if u["value"] is False else "wrong",
                "unboxed ink read as %s (%s)" % (u["value"], u["reason"]))
    n = S.get((sub, "notehead_is_not_a_notehead"))
    if n is None:
        return "not_found", "no note-or-not verdict at this key"
    if n["outcome"] != "decided":
        return "abstained", "note-or-not abstained (%s)" % n["reason"]
    return ("right" if n["value"] is True else "wrong",
            "refused as not a note (%s)" % n["reason"] if n["value"]
            else "kept as a notehead")


def _arc(sub: str, want: str, S: Dict) -> Tuple[str, str]:
    a = S.get((sub, "arc_kind"))
    if a is None:
        return "not_found", "no arc_kind verdict at this key"
    if a["outcome"] != "decided":
        return "abstained", "arc kind abstained (%s)" % a["reason"]
    return ("right" if a["value"] == want else "wrong",
            "read as %s (%s)" % (a["value"], a["reason"]))


#: Question kinds whose answers are not a value of the verdicts compared here
#: (an owner side, a dynamic's letters, a stem count, a meter): a `2` or a
#: `beam` answered to one of those is not a duration or a refusal.
_NOT_SCORED_QUESTIONS = frozenset({"stem", "owner", "dynamic", "meter"})


def score_row(row: Dict[str, Any], S: Dict) -> Tuple[str, str, Optional[float]]:
    """`(status, note, margin)` for one judged tile against standing verdicts."""
    subs = row.get("subjects") or ([row["subject"]] if row.get("subject") else [])
    kind, value = row["answer_kind"], row["value"]
    if row["question_kind"] in _NOT_SCORED_QUESTIONS:
        return "unscored", "question kind %s has no comparator" % row[
            "question_kind"], None
    if row["subject_kind"] != "glyph" or not subs:
        return "unscored", "no glyph subject (%s)" % row["subject_kind"], None
    if kind in ("duration", "rest", "not_a_note", "arc") and value is not None:
        results = []
        for s in subs:
            if kind == "duration":
                results.append(_duration(s, value, S))
            elif kind == "rest":
                results.append(_rest(s, value, S))
            elif kind == "not_a_note":
                results.append(_not_a_note(s, value, S))
            else:
                results.append(_arc(s, value, S))
        stat = results[0][0]
        for r, _n in results:
            if r != stat:
                stat = "wrong" if "wrong" in (stat, r) else r
        note = "; ".join(n for _s, n in results)
        marg = None
        for s in subs:
            for q in ("duration", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest",
                      "notehead_is_not_a_notehead", "arc_kind"):
                v = S.get((s, q))
                if v is not None and v.get("margin") is not None:
                    marg = v["margin"]
        return stat, note, marg
    return "unscored", "no comparator for %s answer (%s)" % (kind, row["question_kind"]), None


def score(index: Dict[str, Any], record_path: pathlib.Path, doc: str
          ) -> Dict[str, Any]:
    rows = index["tiles"]
    # tiles whose manifest names no document: kept for this record only where
    # the record's own box for the key sits inside the tile's page bracket
    unknown = [r for r in rows if r["doc"] is None
               and r["subject_kind"] == "glyph" and r["page_box"]
               and not r["followup"]]
    boxes = page_boxes(record_path, {s for r in unknown
                                     for s in (r["subjects"] or [r["subject"]])})
    resolved = {id(r) for r in unknown
                if all(s in boxes and box_matches(boxes[s], r["page_box"])
                       for s in (r["subjects"] or [r["subject"]]))}
    mine = [r for r in rows if (r["doc"] == doc or id(r) in resolved)
            and r["subject_kind"] == "glyph" and not r["followup"]]
    subjects = {s for r in mine for s in (r["subjects"] or [r["subject"]])}
    S = standing_for(record_path, subjects)
    per_item: Dict[str, Counter] = defaultdict(Counter)
    detail: List[Dict[str, Any]] = []
    for r in rows:
        if r["followup"]:
            continue
        if r["doc"] != doc and id(r) not in resolved:
            per_item[r["item"]]["other_doc" if r["doc"] else "doc_unresolved"] += 1
            continue
        status, note, margin = score_row(r, S)
        per_item[r["item"]][status] += 1
        detail.append({"item": r["item"], "tile": r["tile"], "subject":
                       r["subject"] or r["subjects"], "answer": r["answer"],
                       "status": status, "note": note, "margin": margin,
                       "doc_by": "manifest" if r["doc"] == doc else "page_box"})
    total = Counter()
    for c in per_item.values():
        total.update(c)
    return {"record": str(record_path), "doc": doc, "totals": dict(total),
            "per_item": {k: dict(v) for k, v in sorted(per_item.items())},
            "tiles": detail}


def render(rep: Dict[str, Any]) -> str:
    cols = ("right", "wrong", "narrowed", "abstained", "not_found", "unscored")
    lines = ["scored against %s (doc=%s)" % (rep["record"], rep["doc"]),
             "%-34s" % "item" + "".join("%10s" % c for c in cols)]
    for item, c in rep["per_item"].items():
        if not any(c.get(k) for k in cols):
            continue
        lines.append("%-34s" % item[:34] + "".join("%10d" % c.get(k, 0) for k in cols))
    t = rep["totals"]
    lines.append("%-34s" % "TOTAL" + "".join("%10d" % t.get(k, 0) for k in cols))
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--check", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("record")
    s.add_argument("--doc", required=True)
    s.add_argument("--json")
    sub.add_parser("stats")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        if a.check:
            fresh = build_index()
            have = json.loads(INDEX_PATH.read_text()) if INDEX_PATH.exists() else {}
            if have.get("tiles") != fresh["tiles"]:
                print("judged-tiles.json is stale: run `python3 -m "
                      "tools.omr.staged.judged build`", file=sys.stderr)
                return 1
            print("judged-tiles.json current: %d tiles" % fresh["n_tiles"])
            return 0
        idx = write_index()
        print("wrote %s: %d tiles in %d items" % (INDEX_PATH, idx["n_tiles"],
                                                 idx["n_items"]))
        return 0
    idx = json.loads(INDEX_PATH.read_text())
    if a.cmd == "stats":
        rows = idx["tiles"]
        print("%d tiles, %d items" % (len(rows), idx["n_items"]))
        print("by doc:", dict(Counter(r["doc"] for r in rows)))
        print("by answer_kind:", dict(Counter(r["answer_kind"] for r in rows)))
        print("by subject_kind:", dict(Counter(r["subject_kind"] for r in rows)))
        return 0
    rep = score(idx, pathlib.Path(a.record), a.doc)
    print(render(rep))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
