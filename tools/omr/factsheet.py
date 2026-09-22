"""The session-start FACT SHEET: what the machine already knows, and what it needs you for.

    python3 -m tools.omr.factsheet draft score.pdf --record rec.json -o sheet.json
    # ... read the page, fill the blanks, correct what is wrong ...
    python3 -m tools.omr.factsheet check sheet.json --record rec.json

Sean, 2026-09-21: *"I want the reader and dossier process to work as well as
possible by itself but I can supply this info when necessary. The session
start fact sheet should auto populate what it can by itself. then I can do
the rest/double check."*

⚠️⚠️ **THIS IS AN INSTRUMENT, NOT A CRUTCH, AND ONE RULE MAKES IT SO: every
field a human CORRECTS is a recorded disagreement with a reader.** A sheet
that merely accepted hand facts would hide exactly the reader failures this
project is trying to measure -- so `report()` is the headline output of
`check`, and it says how many facts the readers supplied, how many they were
SILENT about, and how many they got WRONG. The third number is the reader's
error rate on the facts that actually gate the pipeline, measured for free,
every session, on whatever document is in front of you.

**THE SHAPE OF A FACT IS ITS PROVENANCE, and that is deliberate.** A leaf is:

    "Flute"                                   -> a HAND fact. A human typed it.
    {"value": "Flute", "source": "reader"}    -> a machine fact, with its tier.
    null                                      -> nobody knows. Not "none".

So you cannot accidentally mark something confirmed: to confirm a machine
fact you replace the dict with the bare value, which is also the least typing.
And `null` is never written as a definite answer -- *a fallback must never
convert "cannot tell" into a definite answer*, which is this repo's own rule
and the reason `unread` is a source word distinct from an empty value.

**THE FOUR TIERS IT FILLS BY ITSELF**, cheapest first, none of which needs
weights, a raster, or a run:

| source     | where it comes from                        | needs        |
|------------|--------------------------------------------|--------------|
| `catalog`  | committed `data/score-library/catalog.json` | the PDF name |
| `dossier`  | committed `data/dossiers/*.json`            | a work id    |
| `reader`   | a staged record's own verdicts              | `--record`   |
| `derived`  | arithmetic over the above                   | --           |

⚠️ **`catalog` AND `dossier` ARE NOT THE SAME KIND OF FACT.** The catalog's
`works` tier is read off IMSLP's work page -- `source_kind: "catalog"`,
independent of the MusicXML anything is scored against, and therefore
admissible anywhere. A **dossier is generated FROM the reference encoding**,
so it is `source_kind: "encoding"`: fine for reading a score you care about,
and never admissible inside a measurement path. That is exactly why
`staged/__main__.py` has no `--dossier` flag, and this module does not add
one to that CLI. It puts the dossier in a sheet a human reads, which is a
different act from feeding it to a benchmark.

⚠️⚠️ **A HAND FACT IS TRUTH, NOT INPUT.** Reading
the printed lineup off the plate is an observation of the PAGE by the best
reader available, not a leak from the encoding -- `printed-lineups.json` is
already used that way, as ground truth readers are SCORED AGAINST. So a hand
fact may drive production freely, and a measurement path must score against
it rather than consume it. Every fact carries its `source` precisely so a
consumer can make that split; nothing here can make it for them.

⚠️ **THE ID SPACES DIFFER AND THIS MODULE REFUSES TO GUESS BETWEEN THEM.**
The catalog keys on genre+number (`beethoven--symphony-5`); a dossier keys on
work+movement (`beethoven-sym5-mvt1`). The trap has cost this repo twice and
is recorded twice in CLAUDE.md. `_dossier_candidates` PROPOSES the movements
that plausibly match and writes them into `check`; it never picks one. A PDF
usually spans several movements anyway, so there is no single right answer to
guess at.

⚠️ **THE LINEUP IS PER-EDITION, NOT PER-PAGE, which is what makes this five
minutes rather than an afternoon.** A conductor's score prints one canonical
top-to-bottom lineup and then SUPPRESSES tacet staves on some systems, so the
whole fact is one list of names plus, per system, which of them are missing.
That is the shape `printed-lineups.json` already uses (`full` + `systems`),
and it is the fact the dossier structurally cannot supply: which encoded part
sits on which printed staff is a property of the ENGRAVING, absent from the
MusicXML entirely, and it is what `dossier.slot_facts_for_system` abstains on
whenever `len(parts) != n_staves` -- i.e. on every condensed page.

⚠️ **WHAT IT DOES NOT DO: it never writes into the pipeline.** Nothing
consumes a sheet yet, deliberately -- the `Q.INK` discipline, where a producer
and its first consumer landing together makes the reach measurement circular.
This draft exists to be read, corrected, and to report what the correction
cost. Wiring it is a separate change with its own measurement.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SHEET_VERSION = 1

#: Sheet metadata, not facts: excluded from `walk` so the scorecard counts
#: only things a reader could have answered.
META = ("sheet_version", "pdf", "check", "_README")

#: Paths whose VALUE is a list, as opposed to a list OF facts.
#:
#: ⚠️⚠️ THE ONE PLACE THE SHAPE RULE IS AMBIGUOUS, AND IT HAD TO BE DECLARED
#: RATHER THAN SNIFFED. `suppressed: ["Timpani"]` is a hand fact whose value
#: happens to be a list; `lineup.full: [...]` is a container of twelve facts.
#: Nothing about the two objects distinguishes them, so without this table
#: `merge` treated a hand-typed suppression list as a container, found no
#: container to merge it against, and DISCARDED THE EDIT -- the one failure
#: this module exists to prevent, committed by the module itself. Found by
#: filling a real sheet rather than by reading the code.
LIST_VALUED = ("work.scored_for", "lineup.systems.*.suppressed")

#: Source tiers, weakest claim first. `unread` is not a value -- it records
#: that a reader was never run, which is a different fact from a reader that
#: ran and found nothing.
SOURCES = ("unread", "reader", "derived", "dossier", "catalog", "hand")

_STAFF = re.compile(r"^staff/(\d+)/(\d+)/(\d+)$")
_SYSTEM = re.compile(r"^system/(\d+)/(\d+)$")


# --------------------------------------------------------------------------
# A fact, and the shape rule that carries its provenance
# --------------------------------------------------------------------------

def fact(value: Any, source: str, **extra: Any) -> Any:
    """Wrap a machine-supplied value with its tier.

    A HAND fact is never built here: it is what a human types into the file,
    and it is recognised by being a bare value rather than a dict. That is
    the whole provenance mechanism -- see `source_of`.

    ⚠️ AN `unread` FACT COLLAPSES TO BARE `null`, and that is the shape rule
    being consistent rather than a shortcut: `null` already MEANS nobody's
    answer, so `{"value": null, "source": "unread"}` says it twice and costs
    three lines of a file a human has to read. A tier that was CONSULTED and
    came back empty keeps its dict -- "the catalog holds no page count" is a
    different fact from "nobody looked".
    """
    if source not in SOURCES:
        raise ValueError(f"unknown source tier: {source!r}")
    if value is None and source == "unread":
        return None
    out: dict[str, Any] = {"value": value, "source": source}
    out.update({k: v for k, v in extra.items() if v is not None})
    return out


def is_machine_fact(f: Any) -> bool:
    """True where a leaf carries its own provenance, i.e. the machine wrote it."""
    return isinstance(f, dict) and "source" in f and "value" in f


def _path_matches(path: str, pattern: str) -> bool:
    ps, qs = path.split("."), pattern.split(".")
    return len(ps) == len(qs) and all(
        q == "*" or p == q for p, q in zip(ps, qs))


def is_list_valued(path: str) -> bool:
    """True where this path holds a list AS A VALUE. See `LIST_VALUED`."""
    return any(_path_matches(path, pat) for pat in LIST_VALUED)


def is_leaf(f: Any, path: str = "") -> bool:
    """True where a node is a FACT rather than a container of facts.

    ⚠️⚠️ LOAD-BEARING, AND ITS ABSENCE WAS A REAL BUG. `source_of` answers
    "hand" for anything that is not a machine fact -- which is right for a
    leaf a human typed and CATASTROPHIC for a container, because a dict of
    facts is also "not a machine fact". Without this test `merge` asked
    `source_of` about the whole sheet, got "hand", and returned the old sheet
    untouched: every re-draft silently merged nothing, and the scorecard read
    a clean zero. A believable zero from a merge that never ran.
    """
    if is_machine_fact(f):
        return True
    if isinstance(f, list) and path and is_list_valued(path):
        return True
    return not isinstance(f, (dict, list))


def value_of(f: Any) -> Any:
    """The value, whichever shape the leaf is in."""
    return f["value"] if is_machine_fact(f) else f


def source_of(f: Any) -> str:
    """The tier a leaf came from.

    ⚠️ A bare leaf is a HAND fact by construction -- the machine always writes
    the dict form, so anything else in the file was typed by a person. `None`
    is the one exception: it is nobody's answer, not a human's.

    ⚠️⚠️ ONLY EVER ASK THIS OF A LEAF (`is_leaf`). A container is not a
    machine fact either, so this would call the whole sheet a hand fact.
    """
    if f is None:
        return "unread"
    if is_machine_fact(f):
        return str(f["source"])
    return "hand"


def walk(node: Any, path: str = "") -> list[tuple[str, Any]]:
    """Every leaf of a sheet, as (dotted path, leaf).

    A machine fact is a leaf even though it is a dict, which is why this
    cannot be a plain recursive descent over dicts.
    """
    out: list[tuple[str, Any]] = []
    if is_leaf(node, path):
        return [(path, node)]
    if isinstance(node, dict):
        for k, v in node.items():
            if k.startswith("_") or k in META:
                continue
            out += walk(v, f"{path}.{k}" if path else str(k))
    else:
        for i, v in enumerate(node):
            out += walk(v, f"{path}[{i}]")
    return out


# --------------------------------------------------------------------------
# Tier 1 -- the catalog. Costs a filename.
# --------------------------------------------------------------------------

def _catalog(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else Path(__file__).resolve().parents[2] / "data" / "score-library" / "catalog.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def _entry_for_pdf(cat: dict[str, Any], pdf: str | Path) -> dict[str, Any] | None:
    """The catalog entry for this PDF, by IMSLP id in its name.

    ⚠️ Keyed on the id rather than the path because the same plate is reached
    through the legacy `tools/omr/training/data/imslp/...` symlinks as well as
    through `library/`, and `work_roster` already keys it loosely for exactly
    that reason.
    """
    name = Path(pdf).name
    ids = re.findall(r"imslp[-_]?(\d+)", name, flags=re.I)
    if not ids:
        return None
    want = ids[0]
    for e in cat.get("entries", []):
        if str(e.get("imslp_id") or "") == want:
            return e
    return None


def _from_catalog(cat: dict[str, Any], pdf: str | Path) -> tuple[dict[str, Any], list[str]]:
    checks: list[str] = []
    e = _entry_for_pdf(cat, pdf)
    if e is None:
        checks.append("work: this PDF is not in the catalog -- fill work_id, "
                      "publisher and composer by hand (nothing below could be "
                      "auto-filled from the catalog or a dossier)")
        return ({k: None for k in
                 ("work_id", "title", "composer", "publisher", "imslp_id",
                  "image_type", "n_pages")}, checks)

    wid = e.get("work_id")
    out = {
        "work_id": fact(wid, "catalog"),
        "title": fact(e.get("title"), "catalog"),
        "composer": fact(e.get("composer"), "catalog"),
        "publisher": fact(e.get("publisher"), "catalog"),
        "imslp_id": fact(e.get("imslp_id"), "catalog"),
        "image_type": fact(e.get("image_type"), "catalog",
                           note="IMSLP's own label, not a measurement of legibility"),
        "n_pages": fact(e.get("pages"), "catalog"),
        "has_text_layer": fact(e.get("has_text_layer"), "catalog",
                               note="False means the FREE margin-label rung "
                                    "cannot run; the names must come from OCR "
                                    "or from you"),
    }

    roster = (cat.get("works", {}).get(wid, {}) or {}).get("instrumentation") or {}
    chairs = roster.get("roster")
    if chairs:
        parsed = [f"{c.get('count')}x {c.get('instrument')}"
                  if (c.get("count") or 1) > 1 else str(c.get("instrument"))
                  for c in chairs if c.get("instrument")]
        out["scored_for"] = fact(parsed, "catalog",
                                 note="what the WORK is scored for (IMSLP work page). "
                                      "N instruments is NOT N staves -- an edition condenses.")
    else:
        out["scored_for"] = None
        checks.append("work.scored_for: the catalog holds no parsed roster for "
                      "this work")
    return out, checks


# --------------------------------------------------------------------------
# Tier 2 -- the dossier. Proposed, never chosen.
# --------------------------------------------------------------------------

def _dossier_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "dossiers"


def _dossier_candidates(work_id: str | None,
                        prefix: str | None = None) -> tuple[list[str], str]:
    """Dossier ids that plausibly match a catalog work id.

    ⚠️ PROPOSES, NEVER PICKS. The two id spaces differ (`beethoven--symphony-5`
    against `beethoven-sym5-mvt1`) and one PDF usually spans several movements,
    so there is no single correct answer to guess at. Getting this wrong has
    cost this repo twice.

    ⚠️ TWO ROUTES, AND WHICH ONE ANSWERED IS REPORTED. The catalog entry may
    carry `dossier_prefix`, which is a COMMITTED bridge between the two id
    spaces and is authoritative where it exists -- on 19 of 289 editions. Where
    it does not, the composer+number heuristic below proposes candidates, and
    the check line says so, because a proposal off a filename is a much weaker
    claim than a recorded mapping.
    """
    d = _dossier_dir()
    if not d.is_dir():
        return [], "none"
    if prefix:
        hit = sorted(f.stem for f in d.glob(f"{prefix}*.json"))
        if hit:
            return hit, "catalog"
    if not work_id:
        return [], "none"
    bits = [b for b in re.split(r"[-]+", work_id) if b]
    if not bits:
        return [], "none"
    composer = bits[0]
    nums = re.findall(r"\d+", work_id)
    out = []
    for f in sorted(d.glob("*.json")):
        stem = f.stem
        if not stem.startswith(composer):
            continue
        if nums and not any(n in stem for n in nums):
            continue
        out.append(stem)
    return out, "heuristic"


def _from_dossier(dossier_id: str | None) -> tuple[dict[str, Any], list[str]]:
    checks: list[str] = []
    blank = {k: None for k in
             ("dossier_id", "meter", "constant_meter", "total_measures",
              "n_reference_parts")}
    if not dossier_id:
        return blank, checks
    p = _dossier_dir() / f"{dossier_id}.json"
    if not p.is_file():
        checks.append(f"movement: no dossier named {dossier_id!r}")
        return blank, checks
    d = json.loads(p.read_text())
    m = d.get("starting_meter") or {}
    meter = (f"{m.get('beats')}/{m.get('beat_type')}"
             if m.get("beats") and m.get("beat_type") else None)
    return ({
        "dossier_id": fact(dossier_id, "dossier"),
        "meter": fact(meter, "dossier",
                      note="the ENCODING's meter; the page may print it as a letter"),
        "constant_meter": fact(d.get("constant_meter"), "dossier"),
        "total_measures": fact(d.get("total_measures"), "dossier"),
        "n_reference_parts": fact(d.get("n_parts"), "dossier",
                                  note="parts in the ENCODING -- a printed score "
                                       "condenses, so this is not a staff count"),
    }, checks)


# --------------------------------------------------------------------------
# Tier 3 -- the readers' own answers, out of a staged record
# --------------------------------------------------------------------------

def _load_record(path: str | Path) -> dict[str, Any]:
    d = json.loads(Path(path).read_text())
    return d.get("record", d)


def _reader_view(rec: dict[str, Any]) -> dict[str, Any]:
    """Everything the fact sheet wants from a record, in one pass.

    ⚠️ ABSENT AND DECLINED ARE KEPT APART. A staff whose `instrument` abstained
    `no_evidence` because the margin reader never ran is NOT the same fact as a
    staff whose margin prints nothing, and the sheet must not collapse them --
    the first is a reader that was not given its input, the second is the page.
    """
    verdicts = rec.get("verdicts", [])
    obs = rec.get("observations", [])
    absts = rec.get("abstentions", [])

    labels: dict[str, str] = {}
    for o in obs:
        if o.get("quantity") == "margin_label" and o.get("value"):
            labels[o["subject"]] = str(o["value"])

    v_by: dict[str, dict[str, Any]] = defaultdict(dict)
    for v in verdicts:
        v_by[v.get("quantity", "")][v.get("subject", "")] = v

    label_never_ran = sum(
        1 for a in absts
        if a.get("quantity") == "margin_label"
        and a.get("reason") in ("not_implemented", "reader_unavailable"))

    systems: dict[str, dict[str, Any]] = {}
    for subj, v in v_by.get("system_membership", {}).items():
        m = _SYSTEM.match(subj)
        if m and v.get("outcome") == "decided":
            systems[subj] = {"page": int(m.group(1)), "index": int(m.group(2)),
                             "n_staves": v.get("value")}

    staves: dict[str, dict[str, Any]] = {}
    for subj in sorted({s for q in ("clef", "instrument", "staff_ordinal")
                        for s in v_by.get(q, {})}):
        m = _STAFF.match(subj)
        if not m:
            continue
        inst = v_by.get("instrument", {}).get(subj, {})
        iv = inst.get("value")
        staves[subj] = {
            "page": int(m.group(1)), "system": int(m.group(2)),
            "index": int(m.group(3)),
            "label": labels.get(subj),
            "instrument": (iv.get("name") if isinstance(iv, dict) else iv),
            "instrument_outcome": inst.get("outcome"),
            "instrument_reason": inst.get("reason"),
            "clef": _decided(v_by.get("clef", {}).get(subj)),
            "key": _decided(v_by.get("key_signature", {}).get(subj)),
            "bars": _decided(v_by.get("measure_partition", {}).get(subj)),
        }

    meters = {s: _decided(v) for s, v in v_by.get("meter", {}).items()}
    return {"systems": systems, "staves": staves, "meters": meters,
            "label_reader_never_ran": label_never_ran,
            "n_staff_systems": len(staves)}


def _decided(v: dict[str, Any] | None) -> Any:
    return v.get("value") if v and v.get("outcome") == "decided" else None


# --------------------------------------------------------------------------
# The payload: the printed lineup
# --------------------------------------------------------------------------

def _draft_lineup(view: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The canonical top-to-bottom lineup, plus what each system suppresses.

    ⚠️ THE FULL LINEUP IS TAKEN FROM THE SYSTEM THAT PRINTS THE MOST STAVES,
    which is a claim about this edition and not about the work: a page that
    suppresses nothing shows the whole lineup in order. Where several systems
    tie at that count they must AGREE, or the draft refuses and says so --
    two full-height systems with different lineups is the `p4/s0` vs `p4/s1`
    shape this repo already records, and it is exactly the case an equal-count
    join gets silently wrong.
    """
    checks: list[str] = []
    staves = view["staves"]
    if not staves:
        return {"full": None, "systems": {}}, [
            "lineup.full: no record supplied, so nothing could be drafted -- "
            "write the printed lineup top to bottom"]

    by_sys: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for s in staves.values():
        by_sys[(s["page"], s["system"])].append(s)
    for v in by_sys.values():
        v.sort(key=lambda s: s["index"])

    widest = max(len(v) for v in by_sys.values())
    fulls = {k: v for k, v in by_sys.items() if len(v) == widest}

    # ⚠️ The canonical lineup is taken from the widest system the LEXICON
    # named most of, not merely the first one of that width: a system where
    # two horn labels lost their noun describes the same staves less well,
    # and whichever list is taken becomes the key every other system is
    # matched against.
    def _quality(v: list[dict[str, Any]]) -> int:
        return sum(1 for s in v if _name_of(s)[1] == "instrument")

    best = max(fulls, key=lambda k: (_quality(fulls[k]), -k[0], -k[1]))
    named = [_name_of(s) for s in fulls[best]]
    names = [n for n, _ in named]

    disagree = sorted(f"p{k[0]}/s{k[1]}" for k, v in fulls.items()
                      if [_name_of(s)[0] for s in v] != names)
    weak = [f"{i}:{n!r}" for i, (n, q) in enumerate(named) if q != "instrument"]
    if disagree:
        checks.append(
            "lineup.full: taken from p%d/s%d; %d of the %d systems that print "
            "%d staves name them differently (%s)%s"
            % (best[0], best[1], len(disagree), len(fulls), widest,
               ", ".join(disagree),
               " -- and %d slot(s) of the chosen lineup were NOT named by the "
               "lexicon (%s), which is enough on its own to make the lists "
               "differ. Settle the lineup by reading the margin."
               % (len(weak), ", ".join(weak)) if weak else
               " -- read the margins and settle it; an equal-count join "
               "accepts this silently."))

    full = [fact(n, "reader" if n else "unread",
                 note=("from the raw margin label; the lexicon did NOT name "
                       "it, so nothing may be derived from it"
                       if q == "label_only" else None))
            for n, q in named]
    unread = sum(1 for n, _ in named if n is None)
    reliable = all(q == "instrument" for _, q in named)
    if unread:
        checks.append(
            "lineup.full: %d of %d staves have no name -- %s"
            % (unread, len(names),
               "the margin reader never ran on this record"
               if view["label_reader_never_ran"] else
               "the margin prints nothing the lexicon could read"))
    elif not reliable:
        checks.append(
            "lineup.full: %d of %d slots carry a RAW margin string the "
            "lexicon refused (%s) -- confirm the instrument. Until then no "
            "suppression list can be derived from this lineup."
            % (len(weak), len(names), ", ".join(weak)))

    systems: dict[str, Any] = {}
    for (pg, sy), v in sorted(by_sys.items()):
        key = f"p{pg}/s{sy}"
        named_here = [_name_of(s) for s in v]
        got = [n for n, _ in named_here]
        here_ok = all(q == "instrument" for _, q in named_here)
        entry: dict[str, Any] = {
            "n_staves": fact(len(v), "reader"),
            "bars": fact(_modal([s["bars"] for s in v]), "reader"),
        }
        if len(v) == widest and got == names:
            entry["suppressed"] = fact([], "derived",
                                       note="prints the full lineup")
        elif not (reliable and here_ok):
            entry["suppressed"] = None
            checks.append(
                "lineup.systems.%s.suppressed: %s. NOT derived: %s" % (
                    key,
                    "prints the full %d staves, but the lineup could not be "
                    "confirmed against it" % widest if len(v) == widest else
                    "prints %d of %d staves -- name which are suppressed"
                    % (len(v), widest),
                    "the full lineup is not fully named"
                    if not reliable else
                    "this system has a staff the lexicon did not name"))
        else:
            missing, unmatched = _missing(names, got)
            if unmatched:
                entry["suppressed"] = None
                checks.append(
                    "lineup.systems.%s.suppressed: prints %d of %d staves and %d of them are in "
                    "NO slot of the full lineup (%s) -- the two lists are not "
                    "describing the same staves, so no suppression list is "
                    "derived. Settle the lineup first."
                    % (key, len(v), widest, len(unmatched), ", ".join(unmatched)))
            else:
                entry["suppressed"] = fact(
                    missing, "derived",
                    note="derived by name from the full lineup")
        entry["first_ref_measure"] = None
        systems[key] = entry

    if len(fulls) == 1 and widest < max(
            (len(v) for k, v in by_sys.items() if k != best), default=0) + 1:
        pass
    checks.append(
        "lineup.full: this assumes the widest system (%d staves) prints the "
        "WHOLE lineup. If every system on these pages suppresses something, "
        "the real lineup is longer and nothing here can tell -- it is one of "
        "the facts worth a glance at the score's first page." % widest)
    checks.append(
        "lineup.systems.*.first_ref_measure: which reference bar each system opens "
        "on. NOTHING can draft this cold -- it is the one fact that needs the "
        "print, and every measure number downstream rests on it.")
    return {"full": full, "systems": systems}, checks


def _name_of(s: dict[str, Any]) -> tuple[str | None, str]:
    """This staff's name, and HOW GOOD that name is.

    ⚠️⚠️ THE TWO ARE NOT INTERCHANGEABLE AND CONFLATING THEM EMITS A WRONG
    SUPPRESSION LIST SILENTLY. A name the lexicon resolved (`instrument`) can
    be matched against another system's; a raw margin string that the lexicon
    REFUSED (`in C 1 2`, `(Es)` -- a Hörner label whose noun was truncated
    away) cannot, because the same staff prints a different string elsewhere.
    Falling back to the raw text is right for SHOWING a human what was read;
    it is wrong for deriving anything, so the quality travels with the name.
    """
    if s.get("instrument"):
        return str(s["instrument"]), "instrument"
    if s.get("label"):
        return str(s["label"]), "label_only"
    return None, "unread"


def _missing(full: list[str | None],
             got: list[str | None]) -> tuple[list[str], list[str]]:
    """(suppressed, unmatched) against the full lineup.

    Multiset-aware: a lineup with two `Violin` entries and a system printing
    one must report one missing, not none.

    ⚠️ `unmatched` is the safety. A printed staff whose name is in no slot of
    the full lineup means the two lists are not describing the same staves --
    so the caller must ABSTAIN rather than publish a suppression list that is
    half right, which is how a wrong join gets in quietly.
    """
    pool = Counter(g for g in got if g)
    missing: list[str] = []
    for n in full:
        if n is None:
            continue
        if pool.get(n):
            pool[n] -= 1
        else:
            missing.append(n)
    return missing, sorted(k for k, v in pool.items() if v > 0)


def _modal(xs: list[Any]) -> Any:
    xs = [x for x in xs if x is not None]
    return Counter(xs).most_common(1)[0][0] if xs else None


# --------------------------------------------------------------------------
# Draft, merge, check
# --------------------------------------------------------------------------

def draft(pdf: str | Path, *, record: dict[str, Any] | None = None,
          dossier_id: str | None = None,
          catalog_path: str | Path | None = None) -> dict[str, Any]:
    """Fill everything the machine can, and NAME what it could not."""
    cat = _catalog(catalog_path)
    entry = _entry_for_pdf(cat, pdf)
    work, checks = _from_catalog(cat, pdf)
    wid = value_of(work.get("work_id"))

    if dossier_id is None:
        cands, how = _dossier_candidates(
            wid, (entry or {}).get("dossier_prefix"))
        if len(cands) == 1:
            dossier_id = cands[0]
        elif cands:
            checks.append(
                "movement.dossier_id: %d movements could be this PDF (%s) -- "
                "name the one it holds. Route: %s. The catalog and the "
                "dossiers use DIFFERENT id spaces and this refuses to guess "
                "between them; a PDF also usually spans several movements."
                % (len(cands), ", ".join(cands[:8]),
                   "the catalog's committed dossier_prefix" if how == "catalog"
                   else "a composer+number GUESS off the work id -- weaker, "
                        "this edition carries no dossier_prefix"))

    movement, dchecks = _from_dossier(dossier_id)
    checks += dchecks

    view = _reader_view(record) if record else {
        "systems": {}, "staves": {}, "meters": {},
        "label_reader_never_ran": 0, "n_staff_systems": 0}
    lineup, lchecks = _draft_lineup(view)
    checks += lchecks

    if record and view["label_reader_never_ran"]:
        checks.append(
            "READER HEALTH: `margin_label` reports `not_implemented` on %d "
            "staves -- the reader was never given its input on this record, "
            "which is a DIFFERENT fact from a page that prints no labels. "
            "Anything you fill in below is standing in for a reader that did "
            "not run, not one that failed."
            % view["label_reader_never_ran"])

    return {
        "_README": (
            "Auto-drafted. A bare value is a fact YOU supplied; a "
            "{value, source} dict is one the machine supplied; null is "
            "nobody's answer. To confirm a machine fact, replace the dict "
            "with its bare value. Then: python3 -m tools.omr.factsheet check "
            "<this file> --record <rec.json>"),
        "sheet_version": SHEET_VERSION,
        "pdf": str(pdf),
        "work": work,
        "movement": movement,
        "lineup": lineup,
        "check": checks,
    }


def merge(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Re-draft over an edited sheet. A HAND fact always wins.

    ⚠️⚠️ **THIS IS WHERE THE MEASUREMENT IS RECOVERED.** When a human replaced
    a machine fact with their own, the reader's answer is gone from the file --
    so on every re-draft a hand fact that DISAGREES with what the reader now
    says gets `reader_said` written back beside it. The human never has to
    preserve anything for the disagreement to be counted, which is the only
    way a scorecard survives ordinary editing.
    """
    def _merge(o: Any, n: Any, path: str = "") -> Any:
        if is_leaf(o, path) and source_of(o) == "hand":
            nv = value_of(n)
            if is_machine_fact(n) and source_of(n) != "unread" and nv != o:
                return {"value": o, "source": "hand", "reader_said": nv,
                        "note": "you corrected the machine here"}
            return o
        if isinstance(o, dict) and isinstance(n, dict) and not is_leaf(o, path):
            return {k: (_merge(o[k], n[k], f"{path}.{k}" if path else k)
                        if k in o else n[k]) for k in n}
        if isinstance(o, list) and isinstance(n, list) and not is_leaf(o, path):
            if len(o) != len(n):
                # ⚠️ A HUMAN'S LENGTH WINS. He counted the staves off the page;
                # the reader's list is the one that is wrong about how many
                # there are, so re-drafting must not truncate or pad his.
                return o
            return [_merge(a, b, f"{path}[{i}]")
                    for i, (a, b) in enumerate(zip(o, n))]
        return n

    out = _merge({k: v for k, v in old.items() if k not in ("check", "_README")},
                 {k: v for k, v in new.items() if k not in ("check", "_README")})
    out["_README"] = new["_README"]
    chained = chain_windows(out)
    out["check"] = [c for c in new.get("check", [])
                    if not _answered(out, c)] + chained
    return out


def _answered(sheet: dict[str, Any], check: str) -> bool:
    """Drop a check whose field a human has since filled.

    ⚠️ THE LABEL BEFORE THE COLON MUST BE A REAL DOTTED PATH INTO THE SHEET.
    Where it is not, this silently never matches and the check outlives its
    answer -- which is how a to-do list stops being read. `lineup.full`, not
    `full`; `lineup.systems.p2/s0.suppressed`, not `systems.p2/s0`.
    """
    path = check.split(":", 1)[0].strip()
    if not path or " " in path:
        return False
    leaves = dict(walk(sheet))
    if "*" in path:
        # A wildcard check is answered only when EVERY field it names is.
        hit = [v for p, v in leaves.items() if _path_matches(p, path)]
        return bool(hit) and all(v is not None for v in hit)
    hit = [v for p, v in leaves.items() if p == path or p.startswith(path + ".")
           or p.startswith(path + "[")]
    return bool(hit) and all(source_of(v) == "hand" for v in hit)


def chain_windows(sheet: dict[str, Any]) -> list[str]:
    """Carry `first_ref_measure` forward from the first one a human supplied.

    A system opens where the previous one left off, so ONE hand-read bar number
    places every system after it -- which is what turns seven questions into
    one. `draft_windows.py` chains the same way from a hand-verified base row;
    this is that idea at session start, where there is no base row yet.

    ⚠️⚠️ **IT RESTS ENTIRELY ON THE READER'S BAR COUNTS, AND A BARLINE ERROR
    SHIFTS EVERY SYSTEM AFTER IT.** So each derived value is marked `derived`
    and says so, and the chain BREAKS at the first system whose bar count the
    reader did not decide rather than carrying a number across a gap it cannot
    measure -- a chain that guessed one span would put every later system
    wrong while looking exactly as confident as the ones that are right.

    ⚠️ A hand value always wins and RE-ANCHORS the chain: correcting one bar
    number downstream fixes everything below it, which is the shape you want
    when you find the barline the reader miscounted.
    """
    systems = sheet.get("lineup", {}).get("systems", {})
    notes: list[str] = []
    running: int | None = None
    for key, sysm in systems.items():
        first = sysm.get("first_ref_measure")
        if source_of(first) == "hand":
            running = value_of(first)
        elif running is not None:
            sysm["first_ref_measure"] = fact(
                running, "derived",
                note="chained from the previous system's bar count -- a "
                     "miscounted barline above shifts this and everything below")
        bars = value_of(sysm.get("bars"))
        if running is None:
            continue
        if bars is None:
            running = None
            notes.append(
                "lineup.systems.%s.first_ref_measure: the reader decided no bar count here, so the "
                "window chain STOPS -- every system below needs its own "
                "first_ref_measure by hand" % key)
        else:
            running += int(bars)
    return notes


def report(sheet: dict[str, Any]) -> dict[str, Any]:
    """The scorecard. **The point of the whole exercise.**

    `disagreements` is the number that matters: facts a reader answered and a
    human then overrode. It costs nothing to collect and it is measured on
    exactly the facts that gate the pipeline.

    ⚠️⚠️ IT IS A DISAGREEMENT COUNT, NOT AN ERROR COUNT, AND THE FIRST TEST OF
    THIS MODULE PROVED WHY: a hand-typed publisher dropped an umlaut the
    catalog had right, and the sheet dutifully filed the CATALOG as the thing
    that was wrong. Which side is correct is a further act of adjudication that
    nothing here performs -- `reader_said` is kept beside every override
    precisely so that act stays possible. Calling this an error rate would
    convert "these two disagree" into "the machine was wrong", which is the
    same move this project refuses everywhere else.
    """
    leaves = walk(sheet)
    by = Counter(source_of(v) for _, v in leaves)
    corrected = [p for p, v in leaves
                 if is_machine_fact(v) and "reader_said" in v]
    hand = [p for p, v in leaves if source_of(v) == "hand"]
    unknown = [p for p, v in leaves if v is None]
    machine = [p for p, v in leaves
               if source_of(v) in ("catalog", "dossier", "reader", "derived")]
    return {
        "facts": len(leaves),
        "by_source": dict(by),
        "machine_supplied": len(machine),
        "hand_supplied": len(hand),
        "disagreements": len(corrected),
        "corrected_fields": sorted(corrected),
        "still_unknown": sorted(unknown),
        "open_checks": len(sheet.get("check", [])),
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def show(sheet: dict[str, Any]) -> str:
    """The sheet as a human reads it: one line per fact, blanks marked.

    ⚠️ A VIEW, NEVER A FORMAT. Nothing parses this back -- the JSON stays the
    one editable artefact, because a round-trippable prose form is a parser
    nobody asked for and the thing it would silently mis-read is the fact the
    whole sheet exists to get right.
    """
    lines = [f"  {sheet.get('pdf','')}"]
    for section in ("work", "movement"):
        lines.append(f"\n  [{section}]")
        for k, v in sheet.get(section, {}).items():
            lines.append("    %-20s %-42s %s" % (
                k, json.dumps(value_of(v))[:42],
                "<-- FILL" if v is None else f"({source_of(v)})"))
    full = sheet.get("lineup", {}).get("full")
    lines.append("\n  [lineup]  the printed staves, top to bottom")
    if not full:
        lines.append("    <-- FILL: no lineup could be drafted")
    else:
        for i, f in enumerate(full):
            lines.append("    %-3d %-24s %s" % (
                i, json.dumps(value_of(f))[:24],
                "<-- FILL" if f is None else f"({source_of(f)})"))
    lines.append("\n  [systems]")
    for key, sysm in sheet.get("lineup", {}).get("systems", {}).items():
        sup = sysm.get("suppressed")
        first = sysm.get("first_ref_measure")
        lines.append(
            "    %-9s %2s staves  %2s bars  opens at bar %-8s suppressed %s" % (
                key, value_of(sysm.get("n_staves")), value_of(sysm.get("bars")),
                "<-- FILL" if first is None else value_of(first),
                "<-- FILL" if sup is None else json.dumps(value_of(sup))))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("draft", help="auto-fill what the machine knows")
    d.add_argument("pdf")
    d.add_argument("--record", default=None,
                   help="a staged record, for the reader tier")
    d.add_argument("--dossier", default=None, help="dossier id (never guessed)")
    d.add_argument("-o", "--out", default=None)

    v = sub.add_parser("show", help="the sheet as a human reads it")
    v.add_argument("sheet")

    c = sub.add_parser("check", help="what you filled, and where you overrode a reader")
    c.add_argument("sheet")
    c.add_argument("--record", default=None)
    c.add_argument("--dossier", default=None)
    c.add_argument("--write", action="store_true",
                   help="re-draft in place, preserving your edits")

    a = ap.parse_args(argv)

    if a.cmd == "draft":
        rec = _load_record(a.record) if a.record else None
        sheet = draft(a.pdf, record=rec, dossier_id=a.dossier)
        text = json.dumps(sheet, indent=2)
        if a.out:
            Path(a.out).write_text(text + "\n")
            print(f"wrote {a.out}")
        else:
            print(text)
        print(show(sheet))
        _print_report(sheet)
        return 0

    if a.cmd == "show":
        sheet = json.loads(Path(a.sheet).read_text())
        print(show(sheet))
        _print_report(sheet)
        return 0

    old = json.loads(Path(a.sheet).read_text())
    rec = _load_record(a.record) if a.record else None
    fresh = draft(old.get("pdf", ""), record=rec,
                  dossier_id=a.dossier or value_of(old.get("movement", {}).get("dossier_id")))
    merged = merge(old, fresh)
    if a.write:
        Path(a.sheet).write_text(json.dumps(merged, indent=2) + "\n")
        print(f"rewrote {a.sheet}")
    _print_report(merged)
    return 0


def _print_report(sheet: dict[str, Any]) -> None:
    r = report(sheet)
    print()
    print("  facts on the sheet     %d" % r["facts"])
    print("  machine supplied       %d" % r["machine_supplied"])
    print("  you supplied           %d" % r["hand_supplied"])
    print("  you overrode a reader  %d%s" % (
        r["disagreements"],
        "   <- a DISAGREEMENT, not proof the reader was wrong"
        if r["disagreements"] else ""))
    for p in r["corrected_fields"]:
        print("      %s" % p)
    print("  still unknown          %d" % len(r["still_unknown"]))
    print("  open checks            %d" % r["open_checks"])
    for c in sheet.get("check", []):
        print("    - %s" % c)


if __name__ == "__main__":
    raise SystemExit(main())
