"""The STAGE READOUT — what ONE stage produced, read off a saved record, with
no engraved output in between (ROADMAP 1.5, STAGED path).

Sean, 2026-09-30: *"I think we should have a way to read the decisions of
each stage without the engraved output. Currently there are too many steps
where things could get changed or lost to be able to determine what's
happening at each step or stage. We need to be able to isolate the output
... and for all of our initial tests I want to be comparing the output of
just the first two stages."*

Three outputs, one module, and it only READS records:

    # 1. one stage's output, per symbol, stopping at the stage asked for
    python3 -m tools.omr.staged.readout show rec.json --page 3 --staff 2 --cell 4
    python3 -m tools.omr.staged.readout show rec.json --through gather --format jsonl --out g.jsonl

    # 2. two runs diffed at GATHER + ADJUDICATE only
    python3 -m tools.omr.staged.readout diff base.json arm.json --family note --arm code

    # 3. a self-contained page over the print, one system per section
    python3 -m tools.omr.staged.readout html rec.json --out page.html
    python3 -m tools.omr.staged.readout html arm.json --against base.json --out diff.html

⚠️⚠️ WHAT THIS DELIBERATELY DOES NOT DO.

* It runs NO stage and decides nothing. Every value it prints is a row the
  record already holds; the stage a verdict belongs to is `trace`'s own
  derivation (`stage_of_decider`), never a second table here. The one
  computation of its own is the pitch NAME shown on hover in the HTML, which
  calls `pitch_resolver._pitch_from_position` (the helper `restate_pitch`
  itself calls) and is labelled as a reading aid, not a stage's output.
* It matches symbols across two runs by BOX OVERLAP inside the same bar (then
  the same staff), never by glyph index: the index is the detector's output
  order for that cell and shifts whenever the detector changes, so an
  index join reports every symbol after an inserted one as "changed".
* It REFUSES a record with no gathered glyph at all. A gather without
  `--weights auto` (or a real weights file) silently never runs the
  detector, and an overnight run was lost to exactly that on 2026-09-30:
  every cell abstains and every later stage has nothing to decide, which
  diffs against another empty record as a perfect zero.
* It REFUSES (or, with no `--arm`, announces loudly) a diff between two
  records whose provenance differs in more than the arm under test. A diff of
  two records built from different pages, or from a different tree AND
  different weights, answers no question.

⚠️ `DERIVED_CHECK = True`: this module NAMES quantities and reason words in
order to show them and consumes none at run time, for the reason `trace.py`
and `capture.py` give. It is registered in `reach.NOT_A_STAGE`.
"""
from __future__ import annotations

import argparse
import base64
import collections
import csv
import html
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .record import Q, Subject

#: See the module docstring. Must stay a bare module-level literal `True`.
DERIVED_CHECK = True

#: The row-writing stages, in pipeline order. GATHER writes observations and
#: abstentions; every later stage writes verdicts, attributed by `trace`.
STAGES: Tuple[str, ...] = ("GATHER", "ADJUDICATE", "EVALUATE", "INFER")
#: The stages an INITIAL test compares (DECISIONS 2026-09-30).
FIRST_TWO: Tuple[str, ...] = ("GATHER", "ADJUDICATE")

#: The families the HTML page draws by default: the ink a bar's rhythm is
#: made of. Any `export.FAMILIES` name may be passed instead.
DEFAULT_DRAWN_FAMILIES: Tuple[str, ...] = ("note", "rest")

_ROW_ID = re.compile(r"^(obs|abs|vrd|pool):[0-9]+$")
_GLYPH_KEY = re.compile(r"^glyph/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$")


class NoGatheredGlyphs(ValueError):
    """A record whose GATHER holds no detector glyph at all."""


class ProvenanceRefused(ValueError):
    """Two records whose provenance differs in more than the arm under test."""


# ─────────────────────────────────────────────────────────────────────────────
# Loading
# ─────────────────────────────────────────────────────────────────────────────


_STAGE_CACHE: Dict[str, str] = {}


def stage_of(decider: str) -> str:
    """The stage a verdict came from — `trace.stage_of_decider`, cached.

    ⚠️ Never a second table: a decider nobody claims comes back
    `UNATTRIBUTED` and is shown as such, not guessed into ADJUDICATE.
    """
    if decider not in _STAGE_CACHE:
        from . import trace as _trace
        _STAGE_CACHE[decider] = _trace.stage_of_decider(decider)
    return _STAGE_CACHE[decider]


@dataclass
class Glyph:
    """One detector box as GATHER filed it."""
    key: str
    page: int
    system: int
    staff: int
    cell: int
    index: int
    cls: Optional[str]
    family: Optional[str]
    score: Optional[float]
    #: (x0, y0, x1, y1) in the cell's canonical frame.
    box_canon: Optional[Tuple[float, float, float, float]]
    #: (x0, y0, x1, y1) in PAGE pixels at the gather's dpi, or None where
    #: GATHER declined to place it on the page.
    box_page: Optional[Tuple[float, float, float, float]]

    @property
    def cell_key(self) -> str:
        return f"cell/{self.page}/{self.system}/{self.staff}/{self.cell}"

    @property
    def staff_key(self) -> str:
        return f"staff/{self.page}/{self.system}/{self.staff}"

    @property
    def x(self) -> float:
        if self.box_page is not None:
            return (self.box_page[0] + self.box_page[2]) / 2.0
        if self.box_canon is not None:
            return (self.box_canon[0] + self.box_canon[2]) / 2.0
        return 0.0


@dataclass
class Run:
    """One saved record, indexed for reading. No opinions, only lookups."""
    path: str
    result: Dict[str, Any]
    observations: List[dict]
    abstentions: List[dict]
    verdicts: List[dict]
    glyphs: Dict[str, Glyph]
    #: subject key -> [(stage, row kind, row)]
    by_subject: Dict[str, List[Tuple[str, str, dict]]] = field(default_factory=dict)
    _vid: Dict[str, dict] = field(default_factory=dict)

    def verdict_by_id(self, vid: str) -> Optional[dict]:
        return self._vid.get(vid)

    def rows_at(self, key: str) -> List[Tuple[str, str, dict]]:
        return self.by_subject.get(key, [])

    def verdicts_at(self, key: str, stage: Optional[str] = None,
                    quantity: Optional[str] = None) -> List[dict]:
        return [r for s, k, r in self.rows_at(key)
                if k == "verdict" and (stage is None or s == stage)
                and (quantity is None or r["quantity"] == quantity)]

    def standing(self, key: str, quantity: str, stage: str) -> Optional[dict]:
        """The last verdict one STAGE filed on (subject, quantity) — what that
        stage handed on, before any later stage touched it."""
        vs = self.verdicts_at(key, stage, quantity)
        return vs[-1] if vs else None

    def obs_at(self, key: str, quantity: str) -> List[dict]:
        return [r for s, k, r in self.rows_at(key)
                if k == "observation" and r["quantity"] == quantity]

    @property
    def provenance(self) -> dict:
        return self.result.get("provenance") or {}

    @property
    def settings_args(self) -> dict:
        return ((self.provenance.get("settings") or {}).get("args") or {})

    @property
    def dpi(self) -> Optional[int]:
        d = self.settings_args.get("dpi")
        return int(d) if d else None

    @property
    def pdf(self) -> Optional[str]:
        return self.settings_args.get("pdf")

    def pages(self) -> List[int]:
        return sorted({g.page for g in self.glyphs.values()})


def _family_of(cls: Optional[str]) -> Optional[str]:
    """The family that CLAIMS this detector class — the exporter's own router
    (`export._claims`, longest prefix wins), never a prefix list here."""
    if not cls:
        return None
    from . import export as _x
    for fam in _x.FAMILIES:
        if _x._claims(fam, cls):
            return fam
    return None


def _glyph_from_box(key: str, o: dict) -> Glyph:
    m = _GLYPH_KEY.match(key)
    p, s, st, c, g = (int(v) for v in m.groups())
    value = o.get("value")
    cls = value[0] if isinstance(value, (list, tuple)) and value else None
    canon = None
    if isinstance(value, (list, tuple)) and len(value) >= 5:
        x, y, w, h = (float(v) for v in value[1:5])
        canon = (x, y, x + w, y + h)
    det = o.get("detail") or {}
    bp = det.get("bbox_page_px")
    page_box = tuple(float(v) for v in bp) if bp else None
    return Glyph(key=key, page=p, system=s, staff=st, cell=c, index=g,
                 cls=cls, family=_family_of(cls), score=o.get("score"),
                 box_canon=canon, box_page=page_box)


def run_from_result(result: Dict[str, Any], path: str = "<memory>") -> Run:
    """Index a record dict (the CLI's whole `--out` envelope).

    Raises `NoGatheredGlyphs` when GATHER holds no detector glyph: see the
    module docstring for the run that was lost to exactly that.
    """
    if "record" not in result:
        raise KeyError(
            f"{path} has no 'record' key. A staged record is "
            "{'record': {'observations': [...], ...}}; refusing to guess.")
    rec = result["record"]
    obs = rec.get("observations", [])
    abs_ = rec.get("abstentions", [])
    vrd = rec.get("verdicts", [])

    glyphs: Dict[str, Glyph] = {}
    for o in obs:
        if o["quantity"] == Q.GLYPH_BOX and _GLYPH_KEY.match(o["subject"]):
            glyphs.setdefault(o["subject"], _glyph_from_box(o["subject"], o))
    if not glyphs:
        box_abst = collections.Counter(
            a["reason"] for a in abs_ if a["quantity"] == Q.GLYPH_BOX)
        routing = result.get("weight_routing") or {}
        weights = (routing.get("weights")
                   or ((result.get("provenance") or {}).get("settings") or {})
                   .get("args", {}).get("weights"))
        raise NoGatheredGlyphs(
            f"REFUSED: {path} holds NO gathered glyph (0 `{Q.GLYPH_BOX}` "
            f"observations; detector abstentions by reason: "
            f"{dict(box_abst) or 'none'}; weights: {weights!r}). The detector "
            "never ran -- a gather without `--weights auto` (or a real "
            "weights file) silently skips it, and every later stage then has "
            "nothing to decide. Re-gather with `--weights auto`. A readout or "
            "a diff of this record would report an empty page as a result.")

    run = Run(path=path, result=result, observations=obs, abstentions=abs_,
              verdicts=vrd, glyphs=glyphs)
    for o in obs:
        run.by_subject.setdefault(o["subject"], []).append(
            ("GATHER", "observation", o))
    for a in abs_:
        run.by_subject.setdefault(a["subject"], []).append(
            ("GATHER", "abstention", a))
    for v in vrd:
        run._vid[v["id"]] = v
        run.by_subject.setdefault(v["subject"], []).append(
            (stage_of(v["decider"]), "verdict", v))
    return run


def load_run(path: str) -> Run:
    """Read a record FILE (through `record_io.load_record`, the one way) and
    index it. Refuses a record with no gathered glyph."""
    from .record_io import load_record
    return run_from_result(load_record(path), path=str(path))


# ─────────────────────────────────────────────────────────────────────────────
# Scope
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Where:
    """Which subjects to read. A field left None does not filter."""
    page: Optional[int] = None
    system: Optional[int] = None
    staff: Optional[int] = None
    cell: Optional[int] = None
    subject: Optional[str] = None

    def admits(self, key: str) -> bool:
        if self.subject is not None:
            return key == self.subject or key.startswith(self.subject + "/")
        try:
            sub = Subject.from_key(key)
        except (ValueError, KeyError):
            return False
        for name in ("page", "system", "staff", "cell"):
            want = getattr(self, name)
            if want is None:
                continue
            if getattr(sub, name) != want:
                return False
        return True


def _stages_through(through: Optional[str]) -> Tuple[str, ...]:
    if through is None:
        return STAGES + ("UNATTRIBUTED",)
    t = through.upper()
    if t not in STAGES:
        raise ValueError(f"--through must be one of {[s.lower() for s in STAGES]}")
    return STAGES[: STAGES.index(t) + 1]


def _subject_sort_key(key: str) -> tuple:
    head, *rest = key.split("/")
    try:
        nums = tuple(int(v) for v in rest)
    except ValueError:
        nums = ()
    return (len(nums) == 0, nums[:1], nums[1:2], nums[2:3], nums[3:4],
            len(nums), nums, head)


# ─────────────────────────────────────────────────────────────────────────────
# 1. The machine form: one row per (subject, stage, quantity)
# ─────────────────────────────────────────────────────────────────────────────


def _compact(value: Any, *, digits: int = 3, limit: int = 16) -> Any:
    """A value that diffs cleanly: floats rounded, row ids masked (they shift
    between runs and mean nothing outside one file), long lists truncated
    with the truncation MARKED."""
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, str):
        return "<row>" if _ROW_ID.match(value) else value
    if isinstance(value, dict):
        return {str(k): _compact(v, digits=digits, limit=limit)
                for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        items = [_compact(v, digits=digits, limit=limit) for v in value]
        if len(items) > limit:
            items = items[:limit] + [f"...+{len(items) - limit} more"]
        return items
    return value


def _entry(stage: str, kind: str, row: dict, run: Run) -> dict:
    if kind == "observation":
        e = {"row": "observation", "value": _compact(row.get("value")),
             "by": row.get("reader")}
        if row.get("score") is not None:
            e["score"] = round(float(row["score"]), 3)
        det = row.get("detail") or {}
        if det:
            e["detail"] = _compact(det, digits=1)
        return e
    if kind == "abstention":
        return {"row": "abstention", "reason": row.get("reason"),
                "by": row.get("reader")}
    e = {"row": "verdict", "outcome": row.get("outcome"),
         "value": _compact(row.get("value")), "reason": row.get("reason"),
         "by": row.get("decider"),
         "basis_n": len(row.get("basis") or ())}
    if row.get("candidates"):
        e["candidates"] = _compact(row["candidates"])
    for k in ("missing", "declined"):
        if row.get(k):
            e[k] = sorted(row[k])
    if row.get("detail"):
        e["detail"] = _compact(row["detail"])
    sup = row.get("supersedes")
    if sup:
        prior = run.verdict_by_id(sup)
        e["revises"] = ({"stage": stage_of(prior["decider"]),
                         "outcome": prior["outcome"],
                         "value": _compact(prior.get("value"))}
                        if prior else {"stage": None, "note": "prior row absent"})
    return e


def readout_rows(run: Run, *, where: Optional[Where] = None,
                 through: Optional[str] = None,
                 family: Optional[str] = None,
                 with_ink: bool = False) -> List[dict]:
    """One row per (subject, stage, quantity), stably sorted, stopping at
    `through`. Row ids are masked and floats rounded, so two readouts of the
    same decisions are byte-identical and `diff` works on them.

    ⚠️ `Q.INK` rows (one per connected ink component) are left out unless
    `with_ink` — they are the population BENEATH the detector and no stage
    reads them; a readout that includes them is mostly them.
    """
    where = where or Where()
    stages = _stages_through(through)
    order = {s: i for i, s in enumerate(STAGES + ("UNATTRIBUTED",))}
    out: List[dict] = []
    for key in sorted(run.by_subject, key=_subject_sort_key):
        if not where.admits(key):
            continue
        g = run.glyphs.get(key)
        if family is not None and (g is None or g.family != family):
            continue
        buckets: Dict[Tuple[str, str], List[dict]] = collections.defaultdict(list)
        for stage, kind, row in run.rows_at(key):
            if stage not in stages:
                continue
            if row["quantity"] == Q.INK and not with_ink:
                continue
            buckets[(stage, row["quantity"])].append(_entry(stage, kind, row, run))
        if not buckets:
            continue
        try:
            sub = Subject.from_key(key)
        except (ValueError, KeyError):
            sub = None
        for (stage, q) in sorted(buckets, key=lambda sq: (order[sq[0]], sq[1])):
            entries = buckets[(stage, q)]
            # verdicts keep their append order (a revision reads after what it
            # revises); gathered rows are an unordered set -- sort them.
            if stage == "GATHER":
                entries = sorted(entries, key=lambda e: json.dumps(
                    e, sort_keys=True, default=str))
            out.append({
                "subject": key,
                "page": getattr(sub, "page", None),
                "system": getattr(sub, "system", None),
                "staff": getattr(sub, "staff", None),
                "cell": getattr(sub, "cell", None),
                "glyph": getattr(sub, "glyph", None),
                "family": g.family if g else None,
                "class": g.cls if g else None,
                "stage": stage, "quantity": q, "entries": entries,
            })
    return out


def write_jsonl(rows: Sequence[dict], fh) -> None:
    for r in rows:
        fh.write(json.dumps(r, sort_keys=True, default=str,
                            separators=(",", ":")) + "\n")


_CSV_FIELDS = ("subject", "page", "system", "staff", "cell", "glyph",
               "family", "class", "stage", "quantity", "kind", "outcome",
               "value", "reason", "by", "score", "candidates")


def write_csv(rows: Sequence[dict], fh) -> None:
    """One CSV line per ENTRY (a (subject, stage, quantity) row can hold
    several gathered rows), with the value as compact JSON."""
    w = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        for e in r["entries"]:
            w.writerow({
                **{k: r[k] for k in ("subject", "page", "system", "staff",
                                     "cell", "glyph", "family", "class",
                                     "stage", "quantity")},
                "kind": e["row"],
                "outcome": e.get("outcome", "read" if e["row"] == "observation"
                                 else "declined"),
                "value": json.dumps(e.get("value"), sort_keys=True,
                                    default=str) if "value" in e else "",
                "reason": e.get("reason", ""),
                "by": e.get("by", ""),
                "score": e.get("score", ""),
                "candidates": json.dumps(e["candidates"], sort_keys=True,
                                         default=str) if e.get("candidates")
                else "",
            })


# ─────────────────────────────────────────────────────────────────────────────
# Plain words
# ─────────────────────────────────────────────────────────────────────────────


_NOTE_NAMES = {4.0: "whole", 2.0: "half", 1.0: "quarter", 0.5: "eighth",
               0.25: "sixteenth", 0.125: "32nd", 0.0625: "64th"}


def plain_class(cls: Optional[str]) -> str:
    """`noteheadBlackOnLine` -> `notehead black on line`."""
    if not cls:
        return "(no detector class)"
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", cls).lower()


def plain_words(word: Optional[str]) -> str:
    return (word or "").replace("_", " ")


def plain_duration(value: Any) -> str:
    if not isinstance(value, dict) or "beats" not in value:
        return _short(value)
    written = value.get("written", value.get("beats"))
    name = _NOTE_NAMES.get(float(written)) if written is not None else None
    dots = int(value.get("dots") or 0)
    beats = value.get("beats")
    s = (("dotted " * dots) + name) if name else f"{written}-beat"
    return f"{s} ({beats:g} beat{'s' if beats != 1 else ''})"


def _short(value: Any, limit: int = 48) -> str:
    if isinstance(value, dict):
        if "beats" in value:
            return f"{value['beats']:g} beats"
        if "name" in value:
            return str(value["name"])
    if isinstance(value, float):
        s = f"{value:.2f}"
    elif isinstance(value, str):
        s = value
    else:
        s = json.dumps(_compact(value, limit=6), default=str)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def human_value(quantity: str, v: dict, own_staff: Optional[str] = None) -> str:
    """A verdict's answer in few words: the value, or its candidates."""
    oc = v.get("outcome")
    if oc == "abstained":
        return "?"
    if oc == "narrowed":
        cands = [c.get("value") for c in (v.get("candidates") or [])]
        return " | ".join(_hv(quantity, c, own_staff) for c in cands)
    return _hv(quantity, v.get("value"), own_staff)


def _hv(quantity: str, value: Any, own_staff: Optional[str]) -> str:
    if quantity == Q.DURATION:
        return plain_duration(value) if isinstance(value, dict) else _short(value)
    if quantity == Q.GLYPH_OWNER and isinstance(value, str):
        return "own staff" if value == own_staff else value
    if isinstance(value, bool):
        return "yes" if value else "no"
    return _short(value)


# ─────────────────────────────────────────────────────────────────────────────
# What ADJUDICATE did to one glyph, in one word
# ─────────────────────────────────────────────────────────────────────────────

#: The statuses the page colours, in precedence order.
KEPT, REFUSED, GIVEN_AWAY, NARROWED, ABSTAINED, UNDECIDED = (
    "kept", "refused", "given_away", "narrowed", "abstained", "undecided")


def _is_refusal_quantity(q: str) -> bool:
    """`*_is_not_a_*` / `*_is_not_an_*` — a family's refusal of its own box."""
    return "_is_not_a" in q


def adjudicate_status(run: Run, g: Glyph) -> Tuple[str, List[str]]:
    """(status, plain-language reasons) from ADJUDICATE's verdicts ONLY.

    Precedence: a DECIDED refusal (`*_is_not_a_*` true, or a notehead read as
    a whole rest) > the ownership contest given to another staff (the loser
    is DROPPED, never relocated -- CLAUDE.md §10) > its length still
    NARROWED > its length ABSTAINED > kept. `undecided` means ADJUDICATE left
    no verdict on this glyph at all (a `--through gather` record, or a class
    no adjudicator claims).
    """
    vs = run.verdicts_at(g.key, "ADJUDICATE")
    if not vs:
        return UNDECIDED, ["ADJUDICATE filed nothing on this box"]
    # standing ADJUDICATE verdict per quantity
    last: Dict[str, dict] = {}
    for v in vs:
        last[v["quantity"]] = v
    for q, v in sorted(last.items()):
        if (_is_refusal_quantity(q) and v["outcome"] == "decided"
                and v.get("value") is True):
            m = re.search(r"_is_not_an?_(.+)$", q)
            what = plain_words(m.group(1)) if m else plain_words(q)
            return REFUSED, [f"not a {what} -- {plain_words(v['reason'])}"]
    wr = last.get(Q.NOTEHEAD_IS_A_WHOLE_REST)
    if wr and wr["outcome"] == "decided" and wr.get("value") is True:
        return REFUSED, [f"read as a whole rest, not a notehead -- "
                         f"{plain_words(wr['reason'])}"]
    own = last.get(Q.GLYPH_OWNER)
    if (own and own["outcome"] == "decided" and isinstance(own.get("value"), str)
            and own["value"] != g.staff_key):
        return GIVEN_AWAY, [f"given to {own['value']} ({plain_words(own['reason'])});"
                            " this copy is dropped"]
    dur = last.get(Q.DURATION)
    if dur and dur["outcome"] == "narrowed":
        return NARROWED, [f"length still open: {human_value(Q.DURATION, dur)} "
                          f"-- {plain_words(dur['reason'])}"]
    if dur and dur["outcome"] == "abstained":
        return ABSTAINED, [f"length could not be read -- {plain_words(dur['reason'])}"]
    if dur is None and g.family in ("note", "rest"):
        return ABSTAINED, ["no length was decided for it"]
    why = []
    if dur:
        why.append(human_value(Q.DURATION, dur))
    return KEPT, why


# ─────────────────────────────────────────────────────────────────────────────
# 1b. The text table, per bar
# ─────────────────────────────────────────────────────────────────────────────

_TEXT_SKIP_GATHER = {Q.GLYPH_BOX, Q.GLYPH_CONF, Q.NOTEHEAD_CLASS, Q.INK}


def _verdict_brief(v: dict, own_staff: Optional[str]) -> str:
    q = v["quantity"]
    oc = v["outcome"]
    val = human_value(q, v, own_staff)
    tag = plain_words(v["reason"])
    if oc != "decided":
        tag = f"{oc.upper()}: {tag}"
    return f"{q}={val} [{tag}]"


def _obs_brief(o: dict) -> str:
    val = o.get("value")
    if isinstance(val, float):
        s = f"{val:.2f}"
    else:
        s = _short(val, 28)
    return f"{o['quantity']}={s}"


def render_text(run: Run, *, where: Optional[Where] = None,
                through: Optional[str] = None,
                family: Optional[str] = None) -> str:
    """Per page, per system, per staff, per bar: every glyph by x, then what
    each stage up to `through` filed on it."""
    where = where or Where()
    stages = _stages_through(through)
    L: List[str] = []
    prov = run.provenance
    L.append(f"STAGE READOUT  {run.path}")
    L.append(f"  tree {prov.get('commit')} dirty={prov.get('dirty')}  "
             f"dpi {run.dpi}  stopped after "
             f"{run.result.get('stopped_after', '?')}  "
             f"showing {' > '.join(s for s in stages if s in STAGES)}")
    by_cell: Dict[str, List[Glyph]] = collections.defaultdict(list)
    for g in run.glyphs.values():
        if not where.admits(g.key):
            continue
        if family is not None and g.family != family:
            continue
        by_cell[g.cell_key].append(g)

    staff_keys = sorted({k.rsplit("/", 1)[0].replace("cell/", "staff/", 1)
                         for k in by_cell}, key=_subject_sort_key)
    last_system = None
    for sk in staff_keys:
        sub = Subject.from_key(sk)
        sys_key = f"system/{sub.page}/{sub.system}"
        if sys_key != last_system:
            last_system = sys_key
            L.append("")
            L.append(f"== page {sub.page} · system {sub.system} ==")
            for s, k, r in run.rows_at(sys_key):
                if k == "verdict" and s in stages:
                    L.append(f"   [{s}] {_verdict_brief(r, None)}")
        L.append("")
        L.append(f"-- staff {sub.staff}  ({_staff_name(run, sk)}) --")
        for s, k, r in run.rows_at(sk):
            if k == "verdict" and s in stages and s != "GATHER":
                L.append(f"   [{s}] {_verdict_brief(r, sk)}")
        cells = sorted((c for c in by_cell if c.startswith(
            sk.replace("staff/", "cell/", 1) + "/")), key=_subject_sort_key)
        for ck in cells:
            c = Subject.from_key(ck).cell
            L.append(f"   bar {c + 1} (cell {c})")
            for s, k, r in run.rows_at(ck):
                if k == "verdict" and s in stages:
                    L.append(f"      [{s}] {_verdict_brief(r, sk)}")
            for g in sorted(by_cell[ck], key=lambda g: (g.x, g.index)):
                bp = g.box_page
                where_s = (f"x{bp[0]:.0f}-{bp[2]:.0f} y{bp[1]:.0f}-{bp[3]:.0f}"
                           if bp else "no page box")
                conf = f"{g.score:.2f}" if g.score is not None else "-"
                L.append(f"      g{g.index:<3} {g.cls or '?':<26} {where_s}  "
                         f"conf {conf}")
                gat = [_obs_brief(r) for s, k, r in run.rows_at(g.key)
                       if s == "GATHER" and k == "observation"
                       and r["quantity"] not in _TEXT_SKIP_GATHER]
                gat += [f"{r['quantity']}=DECLINED:{plain_words(r['reason'])}"
                        for s, k, r in run.rows_at(g.key)
                        if s == "GATHER" and k == "abstention"]
                if gat:
                    L.append("          GATHER      " + " · ".join(sorted(gat)))
                for stage in stages:
                    if stage == "GATHER":
                        continue
                    vs = run.verdicts_at(g.key, stage)
                    if stage == "ADJUDICATE":
                        status, why = adjudicate_status(run, g)
                        head = status.upper().replace("_", " ")
                        if why:
                            head += " (" + "; ".join(why) + ")"
                        L.append(f"          ADJUDICATE  => {head}")
                    for v in vs:
                        L.append(f"          {stage:<11} {_verdict_brief(v, sk)}"
                                 + (_revision_note(run, v)))
    if not by_cell:
        L.append("")
        L.append("(nothing in scope)")
    return "\n".join(L) + "\n"


def _revision_note(run: Run, v: dict) -> str:
    sup = v.get("supersedes")
    if not sup:
        return ""
    prior = run.verdict_by_id(sup)
    if prior is None:
        return "  (revises a row this record does not hold)"
    return (f"  (revises {stage_of(prior['decider'])}'s "
            f"{human_value(prior['quantity'], prior)} [{prior['outcome']}])")


def _staff_name(run: Run, staff_key: str) -> str:
    bits = []
    inst = run.standing(staff_key, Q.INSTRUMENT, "ADJUDICATE")
    if inst and inst["outcome"] == "decided" and isinstance(inst.get("value"), dict):
        bits.append(str(inst["value"].get("name")))
    clef = run.standing(staff_key, Q.CLEF, "ADJUDICATE")
    if clef and clef["outcome"] == "decided":
        bits.append(f"{clef['value']} clef")
    return ", ".join(bits) or "unnamed"


# ─────────────────────────────────────────────────────────────────────────────
# 2. The diff, at GATHER + ADJUDICATE only
# ─────────────────────────────────────────────────────────────────────────────

#: Provenance categories. `input` differing always refuses: two different
#: pages are not an A/B of anything.
PROVENANCE_CATEGORIES = ("input", "code", "weights", "settings", "env")
_NOT_SETTINGS = {"pdf", "pages", "weights", "route_weights",
                 "no_weight_routing", "through"}


def provenance_facts(run: Run) -> Dict[str, Dict[str, Any]]:
    prov = run.provenance
    args = run.settings_args
    routing = run.result.get("weight_routing") or {}
    w = routing.get("weights") or args.get("weights")
    return {
        "input": {"pdf": Path(str(args.get("pdf"))).name if args.get("pdf")
                  else None,
                  "pages": args.get("pages")},
        "code": {"commit": prov.get("commit"), "dirty": prov.get("dirty")},
        # ⚠️ BY FILE NAME: the same weights reached through two worktrees'
        # symlinks are one arm, and `auto` resolving differently is the fact.
        "weights": {"weights": Path(str(w)).name if w else None},
        "settings": {k: v for k, v in sorted(args.items())
                     if k not in _NOT_SETTINGS},
        "env": dict(sorted(((prov.get("settings") or {})
                            .get("env_overrides") or {}).items())),
    }


def provenance_differences(a: Run, b: Run) -> Tuple[List[tuple], List[str]]:
    """([(category, key, a_value, b_value)], [warnings])."""
    fa, fb = provenance_facts(a), provenance_facts(b)
    diffs = []
    for cat in PROVENANCE_CATEGORIES:
        for k in sorted(set(fa[cat]) | set(fb[cat])):
            va, vb = fa[cat].get(k), fb[cat].get(k)
            if va != vb:
                diffs.append((cat, k, va, vb))
    warn = []
    for label, r, f in (("A", a, fa), ("B", b, fb)):
        if f["code"]["commit"] is None or f["code"]["dirty"] is None:
            warn.append(f"{label} ({r.path}) does not name its tree "
                        "(commit/dirty unknown): which code built it cannot be "
                        "checked from the record")
        elif f["code"]["dirty"]:
            warn.append(f"{label} was built from a DIRTY tree: a SHA cannot "
                        "name uncommitted edits")
        stopped = r.result.get("stopped_after")
        if stopped == "gather":
            warn.append(f"{label} stopped after GATHER: it holds no "
                        "ADJUDICATE verdicts, so every verdict line compares "
                        "against nothing")
    if (fa["code"] == fb["code"] and fa["code"]["commit"] is not None
            and not diffs):
        warn.append("the two records name the SAME tree and the same settings: "
                    "a zero here says the run reproduces, not that an arm is "
                    "inert")
    if Path(a.path).resolve() == Path(b.path).resolve() and a.path != "<memory>":
        warn.append("A and B are the SAME FILE")
    return diffs, warn


def check_provenance(a: Run, b: Run, arm: Sequence[str] = (),
                     force: bool = False) -> Tuple[List[tuple], List[str]]:
    """Raise `ProvenanceRefused` where the two records differ in a way that is
    not the arm under test; return (differences, warnings) otherwise."""
    diffs, warn = provenance_differences(a, b)
    cats = {d[0] for d in diffs}
    if force:
        return diffs, warn
    if "input" in cats:
        raise ProvenanceRefused(
            "REFUSED: the two records were gathered from different input "
            f"({[d for d in diffs if d[0] == 'input']}). A diff of two "
            "different pages answers no question. --force to diff anyway.")
    if arm:
        extra = sorted(cats - set(arm))
        if extra:
            raise ProvenanceRefused(
                f"REFUSED: the arm under test is {sorted(arm)}, but the "
                f"records ALSO differ in {extra}: "
                f"{[d for d in diffs if d[0] in extra]}. Two things changed "
                "and the diff cannot say which one moved a verdict. "
                "--force to diff anyway.")
    return diffs, warn


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def match_glyphs(a: Run, b: Run, *, min_iou: float = 0.3,
                 where: Optional[Where] = None
                 ) -> Tuple[List[Tuple[str, str, float, str]], List[str], List[str]]:
    """Pair A's glyphs with B's by BOX OVERLAP, never by index.

    Pass 1: within the same bar (page/system/staff/cell), page boxes where
    both have one, else the cell's canonical boxes. Pass 2: what is left,
    within the same staff by page box (a barline read differently moves a
    glyph to another cell index). Greedy on IoU, best pair first, each glyph
    used once. Returns (pairs [(a_key, b_key, iou, pass)], only_a, only_b).
    """
    where = where or Where()
    ga = {k: g for k, g in a.glyphs.items() if where.admits(k)}
    gb = {k: g for k, g in b.glyphs.items() if where.admits(k)}
    used_a: set = set()
    used_b: set = set()
    pairs: List[Tuple[str, str, float, str]] = []

    def greedy(groups_a: Dict[Any, List[Glyph]], groups_b: Dict[Any, List[Glyph]],
               how: str, page_only: bool) -> None:
        cands = []
        for grp, la in groups_a.items():
            lb = groups_b.get(grp)
            if not lb:
                continue
            for x in la:
                if x.key in used_a:
                    continue
                for y in lb:
                    if y.key in used_b:
                        continue
                    if x.box_page is not None and y.box_page is not None:
                        s = _iou(x.box_page, y.box_page)
                    elif (not page_only and x.box_canon is not None
                          and y.box_canon is not None):
                        s = _iou(x.box_canon, y.box_canon)
                    else:
                        continue
                    if s >= min_iou:
                        cands.append((-s, x.key, y.key))
        for neg, ka, kb in sorted(cands):
            if ka in used_a or kb in used_b:
                continue
            used_a.add(ka)
            used_b.add(kb)
            pairs.append((ka, kb, round(-neg, 3), how))

    def group(gs: Dict[str, Glyph], by) -> Dict[Any, List[Glyph]]:
        out: Dict[Any, List[Glyph]] = collections.defaultdict(list)
        for g in gs.values():
            out[by(g)].append(g)
        return out

    greedy(group(ga, lambda g: g.cell_key), group(gb, lambda g: g.cell_key),
           "same_bar", page_only=False)
    greedy(group(ga, lambda g: g.staff_key), group(gb, lambda g: g.staff_key),
           "same_staff_other_bar", page_only=True)
    only_a = sorted((k for k in ga if k not in used_a), key=_subject_sort_key)
    only_b = sorted((k for k in gb if k not in used_b), key=_subject_sort_key)
    pairs.sort(key=lambda p: _subject_sort_key(p[0]))
    return pairs, only_a, only_b


def _verdict_sig(run: Run, key: str, quantity: str, own_staff: str) -> str:
    v = run.standing(key, quantity, "ADJUDICATE")
    if v is None:
        return "none"
    val = v.get("value")
    if quantity == Q.GLYPH_OWNER and isinstance(val, str):
        val = "own staff" if val == own_staff else val
    if v["outcome"] == "narrowed":
        val = [c.get("value") for c in v.get("candidates") or []]
    return f"{v['outcome']}:{json.dumps(_compact(val), sort_keys=True, default=str)}"


def _reason(run: Run, key: str, quantity: str) -> Optional[str]:
    v = run.standing(key, quantity, "ADJUDICATE")
    return v["reason"] if v else None


def _gather_sig(run: Run, key: str, quantity: str) -> str:
    vals = sorted(json.dumps(_compact(o.get("value"), digits=1), sort_keys=True,
                             default=str)
                  for o in run.obs_at(key, quantity))
    return "|".join(vals) if vals else "none"


#: GATHER rows on a glyph that restate its box (the match itself) and are
#: therefore never a "change" of a matched glyph.
_GATHER_NOT_COMPARED = {Q.GLYPH_BOX, Q.GLYPH_CONF, Q.INK}


def diff_runs(a: Run, b: Run, *, where: Optional[Where] = None,
              family: Optional[str] = None, min_iou: float = 0.3,
              examples: int = 5) -> Dict[str, Any]:
    """Two runs, compared at GATHER + ADJUDICATE and nothing later.

    Per family: glyphs gathered in only one run; for matched glyphs, the
    class, each gathered quantity, the ADJUDICATE status, and each
    ADJUDICATE verdict's answer before -> after. Then the non-glyph
    subjects (staff, bar, system) by key.
    """
    where = where or Where()
    pairs, only_a, only_b = match_glyphs(a, b, min_iou=min_iou, where=where)

    def fam_of(ka: Optional[str], kb: Optional[str]) -> Optional[str]:
        g = (a.glyphs.get(ka) if ka else None) or (b.glyphs.get(kb) if kb else None)
        return g.family if g else None

    def admit(f: Optional[str]) -> bool:
        return family is None or f == family

    fams: Dict[str, Dict[str, Any]] = {}

    def slot(f: Optional[str]) -> Dict[str, Any]:
        name = f or "(other classes)"
        if name not in fams:
            fams[name] = {
                "gathered_a": 0, "gathered_b": 0, "matched": 0,
                "only_a": 0, "only_b": 0,
                "matched_in_another_bar": 0,
                "classes": collections.Counter(),
                "class_changed": collections.Counter(),
                "only_a_status": collections.Counter(),
                "only_b_status": collections.Counter(),
                "status": collections.Counter(),
                "gather": collections.defaultdict(
                    lambda: {"compared": 0, "changed": 0,
                             "directions": collections.Counter()}),
                "adjudicate": collections.defaultdict(
                    lambda: {"compared": 0, "changed": 0, "reason_only": 0,
                             "directions": collections.Counter()}),
                "examples": collections.defaultdict(list),
            }
        return fams[name]

    for k, g in a.glyphs.items():
        if where.admits(k) and admit(g.family):
            slot(g.family)["gathered_a"] += 1
    for k, g in b.glyphs.items():
        if where.admits(k) and admit(g.family):
            slot(g.family)["gathered_b"] += 1
            slot(g.family)["classes"][g.cls] += 1

    for ka in only_a:
        f = fam_of(ka, None)
        if not admit(f):
            continue
        s = slot(f)
        s["only_a"] += 1
        s["only_a_status"][adjudicate_status(a, a.glyphs[ka])[0]] += 1
        if len(s["examples"]["only_a"]) < examples:
            s["examples"]["only_a"].append(ka)
    for kb in only_b:
        f = fam_of(None, kb)
        if not admit(f):
            continue
        s = slot(f)
        s["only_b"] += 1
        s["only_b_status"][adjudicate_status(b, b.glyphs[kb])[0]] += 1
        if len(s["examples"]["only_b"]) < examples:
            s["examples"]["only_b"].append(kb)

    changed_pairs: List[Dict[str, Any]] = []
    for ka, kb, iou, how in pairs:
        f = fam_of(ka, kb)
        if not admit(f):
            continue
        s = slot(f)
        s["matched"] += 1
        if how != "same_bar":
            s["matched_in_another_bar"] += 1
        gA, gB = a.glyphs[ka], b.glyphs[kb]
        pair_changes: List[str] = []
        if gA.cls != gB.cls:
            s["class_changed"][f"{gA.cls} -> {gB.cls}"] += 1
            pair_changes.append(f"class {gA.cls} -> {gB.cls}")
        st_a, why_a = adjudicate_status(a, gA)
        st_b, why_b = adjudicate_status(b, gB)
        s["status"][f"{st_a} -> {st_b}"] += 1
        if st_a != st_b:
            pair_changes.append(f"status {st_a} -> {st_b}")
        # GATHER rows other than the box itself
        gq = ({r["quantity"] for st, k, r in a.rows_at(ka)
               if st == "GATHER" and k == "observation"}
              | {r["quantity"] for st, k, r in b.rows_at(kb)
                 if st == "GATHER" and k == "observation"}) - _GATHER_NOT_COMPARED
        for q in sorted(gq):
            sa, sb = _gather_sig(a, ka, q), _gather_sig(b, kb, q)
            row = s["gather"][q]
            row["compared"] += 1
            if sa != sb:
                row["changed"] += 1
                row["directions"][f"{_trim(sa)} -> {_trim(sb)}"] += 1
                pair_changes.append(f"GATHER {q}: {_trim(sa)} -> {_trim(sb)}")
                if len(s["examples"][q]) < examples:
                    s["examples"][q].append(f"{ka} ~ {kb}")
        # ADJUDICATE verdicts
        vq = ({v["quantity"] for v in a.verdicts_at(ka, "ADJUDICATE")}
              | {v["quantity"] for v in b.verdicts_at(kb, "ADJUDICATE")})
        for q in sorted(vq):
            sa = _verdict_sig(a, ka, q, gA.staff_key)
            sb = _verdict_sig(b, kb, q, gB.staff_key)
            row = s["adjudicate"][q]
            row["compared"] += 1
            if sa != sb:
                row["changed"] += 1
                row["directions"][f"{_trim(sa)} -> {_trim(sb)}"] += 1
                pair_changes.append(f"{q}: {_trim(sa)} -> {_trim(sb)}")
                if len(s["examples"][q]) < examples:
                    s["examples"][q].append(f"{ka} ~ {kb}")
            elif _reason(a, ka, q) != _reason(b, kb, q):
                row["reason_only"] += 1
        if pair_changes:
            changed_pairs.append({"a": ka, "b": kb, "iou": iou, "how": how,
                                  "family": f, "changes": pair_changes,
                                  "status": [st_a, st_b],
                                  "why": [why_a, why_b]})

    # Non-glyph subjects, by key, ADJUDICATE only
    structure: Dict[str, Dict[str, Any]] = collections.defaultdict(
        lambda: {"compared": 0, "changed": 0, "examples": []})
    if family is None:
        keys = ({k for k in a.by_subject if not k.startswith("glyph/")}
                | {k for k in b.by_subject if not k.startswith("glyph/")})
        for key in sorted(keys, key=_subject_sort_key):
            if not where.admits(key):
                continue
            qs = ({v["quantity"] for v in a.verdicts_at(key, "ADJUDICATE")}
                  | {v["quantity"] for v in b.verdicts_at(key, "ADJUDICATE")})
            for q in sorted(qs):
                own = key if key.startswith("staff/") else ""
                sa, sb = _verdict_sig(a, key, q, own), _verdict_sig(b, key, q, own)
                row = structure[q]
                row["compared"] += 1
                if sa != sb:
                    row["changed"] += 1
                    if len(row["examples"]) < examples:
                        row["examples"].append(
                            {"subject": key, "a": _trim(sa, 120),
                             "b": _trim(sb, 120)})

    n_changes = (sum(s["only_a"] + s["only_b"] for s in fams.values())
                 + len(changed_pairs)
                 + sum(r["changed"] for r in structure.values()))
    return {
        "a": a.path, "b": b.path,
        "stages_compared": list(FIRST_TWO),
        "families": {f: _plain(s) for f, s in sorted(fams.items())},
        "changed_pairs": changed_pairs,
        "structure": {q: dict(r) for q, r in sorted(structure.items())},
        "structure_note": (
            "bar-level values that NAME glyph indexes (event, voices) change "
            "whenever the detector's output order changes; read the glyph "
            "lines above for what moved"),
        "n_differences": n_changes,
    }


def _trim(s: str, n: int = 70) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def _plain(obj: Any) -> Any:
    if isinstance(obj, collections.Counter):
        return dict(obj.most_common())
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    return obj


def render_diff(d: Dict[str, Any], diffs: Sequence[tuple], warn: Sequence[str],
                *, label_a: str = "A", label_b: str = "B",
                show_pairs: int = 40) -> str:
    L: List[str] = []
    L.append(f"READOUT DIFF at GATHER + ADJUDICATE   {label_a}={d['a']}")
    L.append(f"{'':38}{label_b}={d['b']}")
    if diffs or warn:
        L.append("")
        L.append("!" * 72)
        L.append("!! PROVENANCE: the two records differ in")
        for cat, k, va, vb in diffs:
            L.append(f"!!   {cat:<9} {k}: {label_a}={va!r}  {label_b}={vb!r}")
        for w in warn:
            L.append(f"!! WARNING: {w}")
        L.append("!" * 72)
    for f, s in d["families"].items():
        L.append("")
        L.append(f"== family {f}: gathered {label_a} {s['gathered_a']} / "
                 f"{label_b} {s['gathered_b']}; matched {s['matched']} "
                 f"({s['matched_in_another_bar']} in another bar); only "
                 f"{label_a} {s['only_a']}, only {label_b} {s['only_b']}")
        if f == "(other classes)":
            L.append(f"   classes no export family claims: "
                     f"{dict(list(s['classes'].items())[:8])} ...")
        if s["only_a_status"]:
            L.append(f"   only in {label_a}, as ADJUDICATE left them: "
                     f"{s['only_a_status']}")
        if s["only_b_status"]:
            L.append(f"   only in {label_b}, as ADJUDICATE left them: "
                     f"{s['only_b_status']}")
        for k, n in s["class_changed"].items():
            L.append(f"   GATHER class  {k}: {n}")
        moved = {k: n for k, n in s["status"].items()
                 if k.split(" -> ")[0] != k.split(" -> ")[1]}
        if moved:
            L.append(f"   ADJUDICATE status {label_a} -> {label_b}: {moved}")
        for q, r in sorted(s["gather"].items()):
            if r["changed"]:
                L.append(f"   GATHER     {q}: {r['changed']} of {r['compared']} "
                         f"changed")
                for dirn, n in list(r["directions"].items())[:6]:
                    L.append(f"        {n:>4}  {dirn}")
        for q, r in sorted(s["adjudicate"].items()):
            if r["changed"] or r["reason_only"]:
                L.append(f"   ADJUDICATE {q}: {r['changed']} of {r['compared']} "
                         f"changed answer"
                         + (f", {r['reason_only']} same answer by another "
                            f"reason" if r["reason_only"] else ""))
                for dirn, n in list(r["directions"].items())[:8]:
                    L.append(f"        {n:>4}  {dirn}")
        for q, ex in s["examples"].items():
            if ex:
                L.append(f"   e.g. {q}: {', '.join(ex)}")
    if d["structure"] and any(r["changed"] for r in d["structure"].values()):
        L.append("")
        L.append("== staves, bars, systems (ADJUDICATE, by key)")
        for q, r in d["structure"].items():
            if r["changed"]:
                L.append(f"   {q}: {r['changed']} of {r['compared']} changed")
                for ex in r["examples"][:3]:
                    L.append(f"        {ex['subject']}: {ex['a']} -> {ex['b']}")
        L.append(f"   ({d['structure_note']})")
    if d["changed_pairs"]:
        L.append("")
        n = len(d["changed_pairs"])
        L.append(f"== matched glyphs that changed ({min(n, show_pairs)} "
                 f"shown of {n})")
        for p in d["changed_pairs"][:show_pairs]:
            L.append(f"   {p['a']} ~ {p['b']} (iou {p['iou']}): "
                     + "; ".join(p["changes"]))
    L.append("")
    L.append("ZERO differences at GATHER + ADJUDICATE."
             if d["n_differences"] == 0 else
             f"{d['n_differences']} differences at GATHER + ADJUDICATE "
             "(glyphs in one run only + matched glyphs that changed + "
             "structural verdicts that changed).")
    return "\n".join(L) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# 3. The page over the print
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_STYLE = {
    KEPT: ("#15803d", "", "kept"),
    REFUSED: ("#dc2626", "", "thrown out"),
    GIVEN_AWAY: ("#6b7280", "6 4", "given to the neighbouring staff"),
    NARROWED: ("#ea580c", "", "kept, length still undecided"),
    ABSTAINED: ("#a21caf", "", "kept, length could not be read"),
    UNDECIDED: ("#0ea5e9", "2 3", "not looked at by ADJUDICATE"),
}
_GATHER_STYLE = ("#2563eb", "")
_DIFF_STYLE = {
    "only_a": ("#dc2626", "6 3", "only in {A}: the other run did not find it"),
    "only_b": ("#2563eb", "", "only in {B}: new in this run"),
    "changed": ("#d97706", "", "found in both, read or decided differently"),
    "same": ("#9ca3af", "2 4", "found in both, decided the same"),
}


def _pitch_name(run: Run, g: Glyph) -> Optional[str]:
    """A READING AID for the hover text only: the staff position named with
    the clef ADJUDICATE decided on the glyph's own staff, by the helper
    `restate_pitch` calls. Not a stage's output; the page says so."""
    pos = run.obs_at(g.key, Q.NOTEHEAD_STAFF_POSITION)
    clef = run.standing(g.staff_key, Q.CLEF, "ADJUDICATE")
    if not pos or not clef or clef["outcome"] != "decided":
        return None
    try:
        from ..pitch_resolver import _pitch_from_position
        return _pitch_from_position(int(round(float(pos[0]["value"]))),
                                    str(clef["value"]))
    except Exception:                                    # noqa: BLE001
        return None


def _position_words(run: Run, g: Glyph) -> Optional[str]:
    pos = run.obs_at(g.key, Q.NOTEHEAD_STAFF_POSITION)
    if not pos:
        return None
    p = int(round(float(pos[0]["value"])))
    kind = "line" if p % 2 == 0 else "space"
    if 0 <= p <= 8:
        where = f"{kind} {5 - p // 2}" if kind == "line" else f"space {4 - p // 2}"
        return f"on {where} (counted from the bottom)"
    steps = -p if p < 0 else p - 8
    side = "above" if p < 0 else "below"
    return f"{steps} step{'s' if steps != 1 else ''} {side} the staff"


def _hover(run: Run, g: Glyph, *, stage: str, label: str = "") -> str:
    """Plain words first; the internal names after a blank line."""
    L: List[str] = []
    conf = f"{g.score * 100:.0f}%" if g.score is not None else "?"
    L.append(f"{plain_class(g.cls)} (detector {conf} sure)")
    L.append(f"staff {g.staff} ({_staff_name(run, g.staff_key)}), "
             f"bar {g.cell + 1} of system {g.system}")
    pw = _position_words(run, g)
    if pw:
        pn = _pitch_name(run, g)
        L.append(pw + (f" -- with this staff's clef that reads {pn} "
                       "(named for reading only)" if pn else ""))
    if stage != "gather":
        status, why = adjudicate_status(run, g)
        L.append(_STATUS_STYLE[status][2].upper()
                 + (": " + "; ".join(why) if why else ""))
    if label:
        L.append(label)
    L.append("")
    L.append(f"{g.key}  {g.cls}")
    rows = run.verdicts_at(g.key, "ADJUDICATE") if stage != "gather" else []
    for v in rows:
        L.append("  " + _verdict_brief(v, g.staff_key))
    if stage == "gather":
        for s, k, r in run.rows_at(g.key):
            if s == "GATHER" and k == "observation" and \
                    r["quantity"] not in _TEXT_SKIP_GATHER:
                L.append("  " + _obs_brief(r))
    return "\n".join(L)


def _rect(box: Sequence[float], color: str, dash: str, title: str,
          cls: str, width: float) -> str:
    x0, y0, x1, y1 = box
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect class="{cls}" x="{x0:.1f}" y="{y0:.1f}" '
            f'width="{max(1.0, x1 - x0):.1f}" height="{max(1.0, y1 - y0):.1f}" '
            f'fill="{color}" fill-opacity="0.08" stroke="{color}" '
            f'stroke-width="{width:.1f}"{d}><title>{html.escape(title)}'
            f'</title></rect>')


def frame_control(image, run: Run, page: int) -> Optional[float]:
    """Does the record's frame sit on the print? Mean ink darkness ON each
    `Q.STAFF_LINES` row minus the mean half a space off it. Positive: the
    lines land on ink. Negative or ~0: the boxes are drawn in the wrong
    frame (wrong dpi, wrong page, an un-deskewed raster) and the page says
    so at the top. Returns None where nothing could be measured.

    ⚠️ A CONTROL THAT CAN FAIL: `test_staged_readout` runs it on an image
    whose lines are shifted and requires it to go non-positive.
    """
    import numpy as np
    arr = np.asarray(image)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    dark = 255.0 - arr.astype(float)
    on, off = [], []
    for key in run.by_subject:
        if not key.startswith(f"staff/{page}/"):
            continue
        lines = run.obs_at(key, Q.STAFF_LINES)
        ext = run.obs_at(key, Q.STAFF_EXTENT)
        if not lines:
            continue
        ys = [float(y) for y in lines[0]["value"]]
        if len(ys) < 2:
            continue
        sp = (ys[-1] - ys[0]) / (len(ys) - 1)
        x0, x1 = (ext[0]["value"] if ext else (0, arr.shape[1]))
        x0, x1 = int(max(0, x0)), int(min(arr.shape[1], x1))
        if x1 <= x0:
            continue
        for y in ys:
            for yy, bucket in ((y, on), (y + sp / 2.0, off)):
                r = int(round(yy))
                if 0 <= r < arr.shape[0]:
                    bucket.append(float(dark[r, x0:x1].mean()))
    if not on or not off:
        return None
    return float(np.mean(on) - np.mean(off))


def _encode_png(crop, scale: float) -> str:
    import cv2
    import numpy as np
    arr = np.asarray(crop)
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    if scale != 1.0:
        arr = cv2.resize(arr, (max(1, int(arr.shape[1] * scale)),
                               max(1, int(arr.shape[0] * scale))),
                         interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", arr, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if not ok:
        raise RuntimeError("PNG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _system_geometry(run: Run, page: int) -> Dict[int, Dict[str, Any]]:
    """{system: {"staves": [(staff, key, ys, (x0, x1))], "y0", "y1", "x0", "x1"}}"""
    out: Dict[int, Dict[str, Any]] = {}
    for key in run.by_subject:
        if not key.startswith("staff/"):
            continue
        sub = Subject.from_key(key)
        if sub.page != page:
            continue
        lines = run.obs_at(key, Q.STAFF_LINES)
        if not lines:
            continue
        ys = [float(y) for y in lines[0]["value"]]
        ext = run.obs_at(key, Q.STAFF_EXTENT)
        xr = tuple(float(v) for v in ext[0]["value"]) if ext else None
        s = out.setdefault(sub.system, {"staves": []})
        s["staves"].append((sub.staff, key, ys, xr))
    for sysd in out.values():
        sysd["staves"].sort()
        sp = [(st[2][-1] - st[2][0]) / max(1, len(st[2]) - 1)
              for st in sysd["staves"] if len(st[2]) > 1] or [15.0]
        space = sorted(sp)[len(sp) // 2]
        sysd["space"] = space
        # room above the top staff for its ledger notes AND a row of bar
        # numbers above them
        sysd["y0"] = min(st[2][0] for st in sysd["staves"]) - 10 * space
        sysd["y1"] = max(st[2][-1] for st in sysd["staves"]) + 6 * space
        xs = sorted(st[3] for st in sysd["staves"] if st[3])
        # ⚠️ The MEDIAN staff's left end, not the minimum: one staff whose
        # extent was read short (or long) must not push every label into
        # the music.
        left = xs[len(xs) // 2][0] if xs else 0.0
        sysd["left"] = left
        sysd["x0"] = min([left] + [x[0] for x in xs]) - 26 * space
        sysd["x1"] = (max(x[1] for x in xs) if xs else 0.0) + 3 * space
    return out


def build_html(run: Run, image_for_page, *, against: Optional[Run] = None,
               pages: Optional[Sequence[int]] = None,
               families: Sequence[str] = DEFAULT_DRAWN_FAMILIES,
               scale: float = 0.5, label_a: str = "A", label_b: str = "B",
               min_iou: float = 0.3) -> str:
    """A self-contained page: the print, one system per section, every
    drawn-family box on it coloured by what a stage made of it.

    `image_for_page(page) -> RGB/gray array` in the record's own page-pixel
    frame (the CLI passes `preprocessing.render_page(pdf, page, dpi).rgb`,
    the same deskewed raster GATHER read). With `against`, `run` is B (the
    arm) and `against` is A (the base); a third view marks what changed.
    """
    pages = list(pages) if pages is not None else run.pages()
    fams = set(families)
    diff_status: Dict[str, Tuple[str, str]] = {}
    only_a: List[Glyph] = []
    diffs: List[tuple] = []
    warn: List[str] = []
    if against is not None:
        diffs, warn = provenance_differences(against, run)
        # ⚠️ THE SAME DIFF THE `diff` COMMAND PRINTS, never a second
        # comparison written for the page: one matcher, one list of changes.
        d = diff_runs(against, run, min_iou=min_iou)
        changed = {p["b"]: p for p in d["changed_pairs"]}
        pairs, oa, ob = match_glyphs(against, run, min_iou=min_iou)
        for ka, kb, iou, how in pairs:
            p = changed.get(kb)
            if p is None:
                diff_status[kb] = ("same", "")
                continue
            sa, sb = p["status"]
            wa, wb = p["why"]
            lines = []
            if sa != sb:
                lines.append(f"{label_a}: {_STATUS_STYLE[sa][2]}"
                             + (f" ({'; '.join(wa)})" if wa else ""))
                lines.append(f"{label_b}: {_STATUS_STYLE[sb][2]}"
                             + (f" ({'; '.join(wb)})" if wb else ""))
            lines += [c for c in p["changes"] if not c.startswith("status ")]
            diff_status[kb] = ("changed", "\n".join(lines))
        for kb in ob:
            diff_status[kb] = ("only_b", "")
        only_a = [against.glyphs[k] for k in oa]

    counts = collections.Counter()
    gcounts = collections.Counter()
    dcounts = collections.Counter()
    sections: List[str] = []
    frame_notes: List[str] = []
    for page in pages:
        image = image_for_page(page)
        fc = frame_control(image, run, page)
        if fc is None or fc <= 0:
            frame_notes.append(
                f"page {page}: the recorded staff lines do NOT land on the "
                f"print (contrast {fc}); the boxes below are in the wrong "
                "frame -- check the dpi and the page index")
        else:
            frame_notes.append(f"page {page}: frame check passed (staff lines "
                               f"land on ink, contrast {fc:.0f})")
        geo = _system_geometry(run, page)
        h, w = image.shape[0], image.shape[1]
        for sysno in sorted(geo):
            sg = geo[sysno]
            x0 = int(max(0, sg["x0"]))
            x1 = int(min(w, sg["x1"]))
            y0 = int(max(0, sg["y0"]))
            y1 = int(min(h, sg["y1"]))
            if x1 <= x0 or y1 <= y0:
                continue
            b64 = _encode_png(image[y0:y1, x0:x1], scale)
            sw = max(1.0, sg["space"] * 0.12)
            parts: List[str] = [
                f'<image x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" '
                f'href="data:image/png;base64,{b64}"/>']
            # staff lines, thin, and a name at the left
            for staff, skey, ys, xr in sg["staves"]:
                lx0, lx1 = (xr if xr else (x0, x1))
                for y in ys:
                    parts.append(f'<line class="staffline" x1="{lx0:.0f}" '
                                 f'y1="{y:.1f}" x2="{lx1:.0f}" y2="{y:.1f}" '
                                 f'stroke-width="{sw:.2f}"/>')
                parts.append(
                    f'<text class="stafflabel" x="{x0 + 0.5 * sg["space"]:.0f}" '
                    f'y="{(ys[0] + ys[-1]) / 2 + sg["space"] * 0.5:.0f}" '
                    f'font-size="{sg["space"] * 1.1:.0f}">{staff}: '
                    f'{html.escape(_staff_name(run, skey))}</text>')
            # bar numbers over the top staff
            if sg["staves"]:
                top_staff, top_key, top_ys, _ = sg["staves"][0]
                for key in run.by_subject:
                    if not key.startswith(top_key.replace("staff/", "cell/", 1) + "/"):
                        continue
                    cb = run.obs_at(key, Q.CELL_BOX)
                    if not cb:
                        continue
                    c = Subject.from_key(key).cell
                    bx = float(cb[0]["value"][0])
                    parts.append(
                        f'<text class="barno" x="{bx + sg["space"]:.0f}" '
                        f'y="{y0 + 1.8 * sg["space"]:.0f}" '
                        f'font-size="{sg["space"] * 1.5:.0f}">bar {c + 1}</text>')
            gat, adj, dif = [], [], []
            for g in run.glyphs.values():
                if g.page != page or g.system != sysno or g.box_page is None:
                    continue
                if g.family not in fams:
                    continue
                gat.append(_rect(g.box_page, _GATHER_STYLE[0], _GATHER_STYLE[1],
                                 _hover(run, g, stage="gather"), "ov-g", sw * 2))
                gcounts[g.family] += 1
                st, _why = adjudicate_status(run, g)
                counts[st] += 1
                color, dash, _ = _STATUS_STYLE[st]
                adj.append(_rect(g.box_page, color, dash,
                                 _hover(run, g, stage="adjudicate"), "ov-a",
                                 sw * 2.5))
                if against is not None:
                    ds, note = diff_status.get(g.key, ("only_b", ""))
                    dcounts[ds] += 1
                    color, dash, words = _DIFF_STYLE[ds]
                    words = words.replace("{A}", label_a).replace("{B}", label_b)
                    dif.append(_rect(g.box_page, color, dash,
                                     _hover(run, g, stage="adjudicate",
                                            label=words.upper()
                                            + ("\n" + note if note else "")),
                                     "ov-d", sw * (3.0 if ds != "same" else 1.5)))
            if against is not None:
                for g in only_a:
                    if (g.page != page or g.system != sysno
                            or g.box_page is None or g.family not in fams):
                        continue
                    dcounts["only_a"] += 1
                    color, dash, words = _DIFF_STYLE["only_a"]
                    words = words.replace("{A}", label_a)
                    dif.append(_rect(g.box_page, color, dash,
                                     _hover(against, g, stage="adjudicate",
                                            label=words.upper()),
                                     "ov-d", sw * 3.0))
            parts.append('<g class="stage-gather">' + "".join(gat) + "</g>")
            parts.append('<g class="stage-adjudicate">' + "".join(adj) + "</g>")
            if against is not None:
                parts.append('<g class="stage-diff">' + "".join(dif) + "</g>")
            sections.append(
                f'<section><h2>Page {page}, system {sysno}</h2>'
                f'<svg viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" '
                f'preserveAspectRatio="xMinYMin meet">{"".join(parts)}</svg>'
                f'</section>')

    return _page_html(run, sections, counts, gcounts, dcounts, frame_notes,
                      against=against, diffs=diffs, warn=warn,
                      label_a=label_a, label_b=label_b, families=families)


def _legend_item(color: str, dash: str, words: str, n: Optional[int]) -> str:
    style = f"border:3px {'dashed' if dash else 'solid'} {color}"
    count = f" <span class=n>({n})</span>" if n is not None else ""
    return f'<li><span class="sw" style="{style}"></span>{html.escape(words)}{count}</li>'


def _page_html(run: Run, sections, counts, gcounts, dcounts, frame_notes, *,
               against, diffs, warn, label_a, label_b, families) -> str:
    prov = run.provenance
    fam_words = " and ".join(
        {"note": "noteheads", "rest": "rests"}.get(f, f) for f in families)
    legend_g = "<ul>" + _legend_item(
        _GATHER_STYLE[0], "", f"a box the detector drew ({fam_words})",
        sum(gcounts.values())) + "</ul>"
    legend_a = "<ul>" + "".join(
        _legend_item(c, d, w, counts.get(k, 0))
        for k, (c, d, w) in _STATUS_STYLE.items()
        if counts.get(k) or k in (KEPT, REFUSED, NARROWED, ABSTAINED)) + "</ul>"
    legend_d = ""
    if against is not None:
        legend_d = "<ul>" + "".join(
            _legend_item(c, d, w.replace("{A}", label_a).replace("{B}", label_b),
                         dcounts.get(k, 0))
            for k, (c, d, w) in _DIFF_STYLE.items()) + "</ul>"
    prov_lines = [f"record: {html.escape(run.path)}",
                  f"tree {prov.get('commit')} (dirty={prov.get('dirty')}), "
                  f"dpi {run.dpi}, stopped after "
                  f"{run.result.get('stopped_after', '?')}"]
    if against is not None:
        prov_lines.insert(0, f"{label_b} = this record; {label_a} = "
                          f"{html.escape(against.path)}")
    alarm = ""
    if against is not None and (diffs or warn):
        items = [f"{c} {html.escape(str(k))}: {label_a}={html.escape(repr(a))} "
                 f"{label_b}={html.escape(repr(b))}" for c, k, a, b in diffs]
        items += [html.escape(w) for w in warn]
        alarm = ('<div class="alarm"><b>The two runs differ in more than their '
                 'boxes:</b><ul>' + "".join(f"<li>{i}</li>" for i in items)
                 + "</ul></div>")
    bad_frame = [n for n in frame_notes if "do NOT" in n]
    frame_html = "".join(
        f'<div class="{"alarm" if n in bad_frame else "ok"}">{html.escape(n)}</div>'
        for n in frame_notes)
    diff_button = ('<button data-s="diff">What changed '
                   f'({label_a} &rarr; {label_b})</button>'
                   if against is not None else "")
    title = "Stage readout" + (" — diff" if against is not None else "")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#fafaf9; --fg:#1c1917; --muted:#57534e; --line:#0d9488; }}
body {{ margin:0; padding:16px; background:var(--bg); color:var(--fg);
  font:15px/1.45 -apple-system, system-ui, sans-serif; }}
header {{ position:sticky; top:0; background:var(--bg); padding:8px 0 10px;
  border-bottom:1px solid #d6d3d1; z-index:2; }}
h1 {{ font-size:19px; margin:0 0 4px; }} h2 {{ font-size:15px; margin:18px 0 6px; }}
.prov {{ color:var(--muted); font-size:12px; }}
button {{ font:inherit; padding:5px 11px; margin:6px 6px 0 0; border:1px solid #a8a29e;
  background:#fff; border-radius:6px; cursor:pointer; }}
body[data-stage=gather] button[data-s=gather], body[data-stage=adjudicate] button[data-s=adjudicate],
body[data-stage=diff] button[data-s=diff] {{ background:#1c1917; color:#fff; }}
.legend ul {{ list-style:none; padding:0; margin:6px 0 0; display:flex; flex-wrap:wrap; gap:4px 18px; }}
.sw {{ display:inline-block; width:18px; height:11px; margin-right:6px; vertical-align:-1px; }}
.n {{ color:var(--muted); }}
.legend > div {{ display:none; }}
body[data-stage=gather] .lg-gather, body[data-stage=adjudicate] .lg-adjudicate,
body[data-stage=diff] .lg-diff {{ display:block; }}
svg {{ width:100%; height:auto; background:#fff; border:1px solid #e7e5e4; }}
svg .stage-gather, svg .stage-adjudicate, svg .stage-diff {{ display:none; }}
body[data-stage=gather] svg .stage-gather, body[data-stage=adjudicate] svg .stage-adjudicate,
body[data-stage=diff] svg .stage-diff {{ display:inline; }}
.staffline {{ stroke:var(--line); stroke-opacity:.55; }}
.stafflabel, .barno {{ fill:var(--line); font-family:sans-serif; }}
rect:hover {{ fill-opacity:.35; }}
.alarm {{ background:#fee2e2; border:1px solid #dc2626; padding:6px 10px; margin:6px 0; font-size:13px; }}
.ok {{ color:var(--muted); font-size:12px; }}
.hint {{ color:var(--muted); font-size:13px; margin-top:4px; }}
</style></head>
<body data-stage="adjudicate">
<header>
<h1>{title}: what each stage made of the {fam_words} on this page</h1>
<div class="prov">{"<br>".join(prov_lines)}</div>
{alarm}{frame_html}
<div><button data-s="gather">What the detector found (GATHER)</button><button data-s="adjudicate">What was decided (ADJUDICATE)</button>{diff_button}</div>
<div class="legend">
<div class="lg-gather">{legend_g}</div>
<div class="lg-adjudicate">{legend_a}</div>
<div class="lg-diff">{legend_d}</div>
</div>
<div class="hint">Hold the pointer over any box to see what was read and why. Thin green-blue lines are the staff lines the reader found; they should sit on the printed lines. Bars are numbered from 1 in each system.</div>
</header>
{"".join(sections)}
<script>
document.querySelectorAll('button[data-s]').forEach(function(b){{
  b.addEventListener('click', function(){{
    document.body.dataset.stage = b.dataset.s;
    history.replaceState(null, '', '#' + b.dataset.s);
  }});
}});
var h = location.hash.slice(1);
if (document.querySelector('button[data-s="' + h + '"]')) document.body.dataset.stage = h;
</script>
</body></html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _where(args) -> Where:
    return Where(page=args.page, system=args.system, staff=args.staff,
                 cell=args.cell, subject=getattr(args, "subject", None))


def _add_scope(p: argparse.ArgumentParser) -> None:
    p.add_argument("--page", type=int, default=None,
                   help="the record's page index (= the PDF page index)")
    p.add_argument("--system", type=int, default=None)
    p.add_argument("--staff", type=int, default=None,
                   help="staff index WITHIN its system")
    p.add_argument("--cell", type=int, default=None,
                   help="bar index as the record numbers it (0-based, "
                        "restarts per system); printed as 'bar N+1'")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m tools.omr.staged.readout",
        description="Read what each stage produced, without the engraved "
                    "output (ROADMAP 1.5).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("show", help="one record, per symbol, stage by stage")
    ps.add_argument("record")
    _add_scope(ps)
    ps.add_argument("--subject", default=None, help="one subject key (and "
                    "everything under it), e.g. glyph/3/0/2/4/5")
    ps.add_argument("--family", default=None,
                    help="only glyphs this export family claims, e.g. note")
    ps.add_argument("--through", default="adjudicate",
                    choices=[s.lower() for s in STAGES],
                    help="stop after this stage (default: adjudicate)")
    ps.add_argument("--format", default="text",
                    choices=("text", "jsonl", "csv"))
    ps.add_argument("--with-ink", action="store_true",
                    help="include the Q.INK component rows (machine forms)")
    ps.add_argument("--out", default=None)

    pd = sub.add_parser("diff", help="two records at GATHER + ADJUDICATE")
    pd.add_argument("a", help="the BASE record")
    pd.add_argument("b", help="the ARM record")
    _add_scope(pd)
    pd.add_argument("--family", default=None)
    pd.add_argument("--arm", action="append", default=[],
                    choices=[c for c in PROVENANCE_CATEGORIES if c != "input"],
                    help="what the arm under test changed (repeatable); any "
                         "OTHER provenance difference is refused")
    pd.add_argument("--force", action="store_true",
                    help="diff despite a provenance refusal (printed anyway)")
    pd.add_argument("--min-iou", type=float, default=0.3)
    pd.add_argument("--label-a", default="A")
    pd.add_argument("--label-b", default="B")
    pd.add_argument("--json", default=None, help="also write the diff as JSON")
    pd.add_argument("--out", default=None)

    ph = sub.add_parser("html", help="the per-stage page over the print")
    ph.add_argument("record", help="the record to draw (the ARM, in diff mode)")
    ph.add_argument("--against", default=None,
                    help="a BASE record: adds a 'what changed' view")
    ph.add_argument("--page", type=int, action="append", default=None,
                    help="page(s) to draw (default: every page in the record)")
    ph.add_argument("--pdf", default=None,
                    help="override the PDF path the record names")
    ph.add_argument("--families", default=",".join(DEFAULT_DRAWN_FAMILIES))
    ph.add_argument("--scale", type=float, default=0.5,
                    help="image scale inside the page (0.5 of a 600-dpi "
                         "gather = 300 dpi)")
    ph.add_argument("--arm", action="append", default=[],
                    choices=[c for c in PROVENANCE_CATEGORIES if c != "input"])
    ph.add_argument("--force", action="store_true")
    ph.add_argument("--label-a", default="A")
    ph.add_argument("--label-b", default="B")
    ph.add_argument("--out", required=True)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "show":
            return _cmd_show(args)
        if args.cmd == "diff":
            return _cmd_diff(args)
        return _cmd_html(args)
    except (NoGatheredGlyphs, ProvenanceRefused) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _emit(text: str, out: Optional[str]) -> None:
    if out:
        Path(out).write_text(text)
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def _cmd_show(args) -> int:
    run = load_run(args.record)
    where = _where(args)
    if args.format == "text":
        _emit(render_text(run, where=where, through=args.through,
                          family=args.family), args.out)
        return 0
    rows = readout_rows(run, where=where, through=args.through,
                        family=args.family, with_ink=args.with_ink)
    buf = io.StringIO()
    (write_jsonl if args.format == "jsonl" else write_csv)(rows, buf)
    _emit(buf.getvalue(), args.out)
    return 0


def _cmd_diff(args) -> int:
    a, b = load_run(args.a), load_run(args.b)
    diffs, warn = check_provenance(a, b, arm=args.arm, force=args.force)
    d = diff_runs(a, b, where=_where(args), family=args.family,
                  min_iou=args.min_iou)
    _emit(render_diff(d, diffs, warn, label_a=args.label_a,
                      label_b=args.label_b), args.out)
    if args.json:
        Path(args.json).write_text(json.dumps(
            {**d, "provenance_differences": [list(x) for x in diffs],
             "warnings": list(warn)}, indent=1, default=str))
        print(f"wrote {args.json}", file=sys.stderr)
    return 0 if d["n_differences"] == 0 else 1


def _cmd_html(args) -> int:
    run = load_run(args.record)
    against = load_run(args.against) if args.against else None
    if against is not None:
        check_provenance(against, run, arm=args.arm, force=args.force)
    pdf = args.pdf or run.pdf
    if not pdf:
        raise SystemExit("the record names no PDF; pass --pdf")
    dpi = run.dpi
    if dpi is None:
        raise SystemExit("the record names no gather dpi; the boxes cannot "
                         "be placed on the print without it")
    from ..preprocessing import render_page       # READ-ONLY use

    def image_for_page(page: int):
        return render_page(pdf, page, dpi=dpi).rgb

    text = build_html(run, image_for_page, against=against, pages=args.page,
                      families=[f for f in args.families.split(",") if f],
                      scale=args.scale, label_a=args.label_a,
                      label_b=args.label_b)
    Path(args.out).write_text(text)
    print(f"wrote {args.out} ({len(text) / 1e6:.1f} MB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
