"""ROADMAP 2.295 -- JUDGED CLAIMS: EVERY CLAIM TILE SEAN ANSWERS IS REPLAYED, FOR EVER.

    python3 -m tools.omr.staged.judged_claims REC [--doc litolff|brahms] [--pages 0,14] [--crops DIR] [--json OUT] [--controls] [--unclaimed]
    python3 -m tools.omr.staged.judged_claims --build      # regenerate data/judged-claims/registry.json from the per-lane answers files
    python3 -m tools.omr.staged.judged_claims --check      # fail if the registry on disk is not what the answers files produce

PATH: STAGED, a CHECKING TOOL ONLY. It reads a saved slice's PAGE LEDGER (`claim_readout.LedgerInk`, ROADMAP 2.293), decides nothing, changes no
reader, verdict or byte of the exported file (`reach.NOT_A_STAGE`, `rule_kinds.INFRA`).

WHY (Sean, 2026-11-10): "Make sure the fix is not just specific to this rule but is universal enough to help us avoid missing or dropping tests like
this." `judged` replays his answers about WRITTEN notes. His answers about CLAIMS -- "what is the ink in this box?", dozens of tiles, 2.276 to 2.292 --
lived in per-lane files and were replayed nowhere, so 2.288 r3 claimed a filled notehead as a whole rest and only a tile showed it. An answer he gave
once must keep working: this tool is where it does.

THE REGISTRY (`data/judged-claims/registry.json`, GENERATED; the per-lane answers files stay the source and are never edited). One entry per answered
tile: lane, source file, tile number, plate, page, box in PAGE pixels, the words Sean said for that tile (the per-tile split is the lane's, the whole
verbatim is in `sources`), a NORMALISED kind from the closed vocabulary (rest:whole|half|quarter|eighth|16th, notehead, stem, beam, flag,
accidental:sharp|flat|natural, dynamic, word, arc, barline, staff_line, ledger_line, tremolo, clef, key, other) and `whole` (false for "part of...",
"half of...", "most of...", "tip of...", "a few pixels of..."). Words that do not map cleanly stay `unmapped` and are listed: a normalisation is never
invented. Tiles with no page box (2.292 asks about a staff START) are kept and replay as "cannot tell".

THE REPLAY. For every registry tile on a page of REC: the dark pixels inside its box (the staff's own eraser-taken ink excluded, as `judge_box` does,
unless Sean named a staff line) are looked up on the page ledger. A pixel's owners are the READ claims standing on it (`fam_eff`) from THREE SOURCES, each
named in the report: `cell settle` (the stroke owner's verdict / detector boxes of the padded cell), `register area` (a page-wide rectangle claim outside
the cells) and `page-stroke claim` (a claim filed as page-stroke ids, `claim_readout.page_stroke_claims`: every READ rest since 2.288, dynamics and repeat
dots, arcs, tremolos, own-ink accidentals -- ROADMAP 2.295b; before it the tool could not see them). GUESSED / NARROWED ones are WEAK and reported apart; a
detector box refused on it is reported apart; nothing is "no owner".
  OVERLAP RULE (by page place and ink, never by box or stroke id: twins, ids restart per system): with R = share of the box's ink owned by a READ claim
  of a kind Sean's word accepts (`ACCEPT`), Wo = share owned ONLY by READ claims of other kinds, Wa = share on which a READ claim of another kind STANDS
  (whether or not his kind also stands there); staff lines, ledger lines and dots crossing a mark are the mark's -- page-facts 2026-11-10 -- and never count
  against it:
    AGREES        R >= 0.5 and Wa < 0.3
    CONTRADICTS   R >= 0.5 and Wa >= 0.3    CLAIMED TWICE (changed 2026-11-11, 2.295b): his kind owns the ink AND a READ claim of another kind stands on
                                            >= 30% of it: a wrong READ claim is a wrong claim even where the cell settle agrees with him
                  R < 0.5 and Wo > R and Wo >= 0.3      a READ claim of ANOTHER kind owns ink he named (the failure this tool exists for)
    UNCLAIMED     he named a real mark and no READ claim of its kind owns it (the to-do list; not a failure)
    CANNOT TELL   the page is not in REC; the box lands on < 8 dark px (geometry moved); no page box; the kind is unmapped. Never agrees (rule 8).
  Before 2.295b the rule was AGREES = R >= 0.5 whatever else stood on the ink, and only cell-settle and rectangle claims were visible.
  The rule can fail: `--controls` relabels one of his rest tiles in memory (it must turn into exactly that one CONTRADICTS) and shifts every box by
  three staff spaces (agrees must collapse); the REAL false claim (2.288 r3's whole rest on Sean's eighth note) is in
  `tests/test_judged_claims_2_295b.py` as rows cut from the r3 gather, and must read CONTRADICTS.
Exit status 1 when any tile CONTRADICTS, so a lane can gate on it: a lane's third measure is "judged right->wrong 0 AND judged_claims contradicts 0".

A saved slice shows the gather it was cut from, not the tree: a contradiction on a slice is a contradiction of THAT gather (the header prints the slice,
its write time and how many strokes carry page-ledger links).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
BENCH = ROOT / "benchmarks"
REGISTRY = ROOT / "data" / "judged-claims" / "registry.json"

AGREE_MIN = 0.5
CONTRA_MIN = 0.3
MIN_INK = 8

KINDS = ("rest", "notehead", "stem", "beam", "flag", "accidental", "dynamic", "word", "arc", "barline", "staff_line", "ledger_line", "tremolo",
         "clef", "key", "other", "unmapped")

# the fine kinds (claim_readout.FINE_KINDS) a Sean word accepts as "the same thing". A note's ink is its head, stem, beam, flag, dot and ledger line:
# "an eighth note" is not contradicted by the stem claim that holds the stem of that note.
NOTE_BODY = ("notehead", "stem", "beam", "flag", "dot", "ledger_line")
ACCEPT: Dict[str, Tuple[str, ...]] = {
    "rest": ("rest",), "notehead": NOTE_BODY, "stem": ("stem",), "beam": ("beam",), "flag": ("flag",), "accidental": ("accidental",),
    "dynamic": ("dynamic",), "word": ("word",), "arc": ("arc",), "barline": ("barline",), "staff_line": ("staff_line",), "ledger_line": ("ledger_line",),
    "tremolo": ("tremolo",), "clef": ("clef",), "key": ("key",),
}
#: the three places a pixel's READ owner can come from (LedgerInk.src_*), in the words the report prints
SOURCES_NAMED = (("src_cell", "cell settle"), ("src_area", "register area"), ("src_page", "page-stroke claim"))
# a mark crosses a staff line, a ledger line, an augmentation dot: that crossing ink is the mark's (page-facts / DECISIONS 2026-11-10)
NEUTRAL = ("staff_line", "ledger_line", "dot")


# ───────────────────────────── 1. the normaliser ─────────────────────────────

PARTIAL = re.compile(r"\b(part of|half of|most of|small part|a few pixels|few pixels|tip of|the cr from|rectangle around|f from ff)\b|\btip\b")
_VALUES = (("whole", r"\bwhole\b"), ("half", r"\bhalf\b"), ("quarter", r"\bquarter\b"), ("eighth", r"\beighth\b|\b8th\b|\b8\b"),
           ("16th", r"\b16th\b|\bsixteenth\b"))


def _value(t: str) -> Optional[str]:
    t = PARTIAL.sub(" ", t)
    for name, rx in _VALUES:
        if re.search(rx, t):
            return name
    return None


def normalise(words: str) -> Dict[str, Any]:
    """Sean's words for ONE tile -> {kind, value, whole, why}. `kind` is from the closed vocabulary or `unmapped` (with `why`); never a guess."""
    raw = (words or "").strip().lower().replace("’", "'")
    whole = not PARTIAL.search(raw)
    t = re.sub(r"\([^)]*\)", " ", raw)         # a parenthesis is the lane's gloss on his words
    t = re.sub(r"\s+", " ", t).strip()

    def out(kind: str, value: Optional[str] = None, why: Optional[str] = None) -> Dict[str, Any]:
        return {"kind": kind, "value": value, "whole": whole, "why": why}

    if not t:
        return out("unmapped", why="no words")
    has_accid = re.search(r"\b(sharp|flat|natural|accidental)\b", t)
    has_note = re.search(r"\b(note|notes|notehead|head)\b", t) and not re.search(r"\brests?\b|\bflag\b|\bbeam\b", t)
    if re.search(r"\b(tempo|metronome)\b", t):
        return out("unmapped", why="a note symbol inside a tempo (metronome) mark: no vocabulary kind")
    if re.search(r"\bempty\b|\bspace on the staff\b", t):
        return out("unmapped", why="he says there is no mark: not a kind")
    if has_accid and has_note and re.search(r"\band\b", t):
        return out("unmapped", why="two marks named (note and accidental)")
    if re.search(r"\b(crook|label|instrument names?|cresc\w*|cr from|word)\b", t):
        return out("word")
    if re.search(r"\brests?\b", t):
        v = _value(t)
        return out("rest:%s" % v if v else "rest", v)
    if re.search(r"\btremolo\b", t):
        return out("tremolo")
    if re.search(r"\b(arc|slur|tie)\b", t):
        return out("arc")
    if re.search(r"\bbar ?line\b", t):
        return out("barline")
    if re.search(r"\bledger line\b", t):
        return out("ledger_line")
    if re.search(r"\bstaff line\b", t):
        return out("staff_line")
    if re.match(r"^(dynamic )?(sf|ff|pp|mf|fp|f|p)\b", t) or re.search(r"\bdynamic\b", t) or re.search(r"\bf from ff\b", t):
        return out("dynamic")
    m = re.search(r"\b(sharp|flat|natural)\b", t)
    if m:
        return out("accidental:%s" % m.group(1), m.group(1))
    if re.search(r"\baccidental\b", t):
        return out("accidental")
    if re.search(r"\bflag\b", t):
        return out("flag")
    if re.search(r"\bbeam\b", t):
        return out("beam")
    if re.search(r"\b(note|notes|notehead|head)\b", t):
        return out("notehead", _value(t))
    if re.search(r"\bstem\b", t):
        return out("stem")
    return out("unmapped", why="no phrase of the vocabulary")


# ───────────────────────────── 2. the sources ─────────────────────────────

def _j(rel: str) -> Any:
    return json.loads((BENCH / rel).read_text())


def _tile_no(e: Dict[str, Any]) -> int:
    return int(e["tile"])


def _box(v: Any) -> Optional[List[float]]:
    if isinstance(v, (list, tuple)) and len(v) == 4:
        return [round(float(x), 2) for x in v]
    return None


# (lane label, answers file, how the page box is found). `key` = a key file beside it with the plate/page/box per tile.
SOURCES: List[Dict[str, Any]] = [
    {"lane": "2.284 r1", "file": "page-ledger-owns-2026-11/answers/answers-2.284.json", "key": "page-ledger-owns-2026-11/answers/key-2.284.json"},
    {"lane": "2.284b r1", "file": "page-ledger-owns-2026-11/answers/answers-2.284b.json", "key": "page-ledger-owns-2026-11/answers/key-2.284b.json"},
    {"lane": "2.284b r2", "file": "page-ledger-owns-2026-11/answers/answers-2.284b-r2.json", "key": "page-ledger-owns-2026-11/answers/key-2.284b-r2.json"},
    {"lane": "2.284 r5", "file": "page-ledger-owns-2026-11/answers/answers-2.284-r5.json", "key": "page-ledger-owns-2026-11/answers/key-2.284-r5.json",
     "unmapped_tiles": {1: "he names the NOTE's value (a flag lost / a note gained / a tie / a value changed), not the kind of the boxed ink",
                        2: "he names the NOTE's value (a flag lost / a note gained / a tie / a value changed), not the kind of the boxed ink",
                        3: "he names the NOTE's value (a flag lost / a note gained / a tie / a value changed), not the kind of the boxed ink",
                        4: "he names the NOTE's value (a flag lost / a note gained / a tie / a value changed), not the kind of the boxed ink"}},
    {"lane": "2.285 r1", "file": "accidental-own-ink-2026-11/answers/answers-2.285-r1.json"},
    {"lane": "2.285 r2", "file": "accidental-own-ink-2026-11/answers/answers-2.285-r2.json"},
    {"lane": "2.288 r1", "file": "rests-claim-first-2026-11/answers/answers-2.288-r1.json"},
    {"lane": "2.288 r2", "file": "rests-claim-first-2026-11/answers/answers-2.288-r2.json"},
    {"lane": "2.288 r3", "file": "rests-claim-first-2026-11/answers/answers-2.288-r3.json"},
    {"lane": "2.289 r1", "file": "note-loss-look-2026-11/answers/answers-2.289-r1.json"},
    {"lane": "2.290 r1", "file": "page-heads-ledger-2026-11/answers/answers-2.290-r1.json"},
    {"lane": "2.292 r1", "file": "why-key-clef-inferred-2026-11/answers/answers-2.292-r1.json", "staff_start": True},
    {"lane": "2.276 r2", "file": "tremolo-claim-2026-11/answers/answers-2.276-r2.json", "key": "tremolo-claim-2026-11/answers/key-2.276-r2.json"},
    {"lane": "2.282", "file": "claim-order-accid-stem-2026-11/answers/answers-2.282.json", "key_tiles": "claim-order-accid-stem-2026-11/answers/key-2.282.json",
     # the lane's per-tile words say "accidental"; his verbatim says "Part of an accidental" for tiles 2-4 and 8-11
     "partial_tiles": (2, 3, 4, 8, 9, 10, 11)},
]


def _raw_tiles(src: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The source's tiles as {tile, plate, page, box, words, extra}. Boxes are PAGE pixels as the lane's own key / answer carries them."""
    d = _j(src["file"])
    keyed: Dict[int, Dict[str, Any]] = {}
    if src.get("key"):
        for e in _j(src["key"]):
            keyed[_tile_no(e)] = e
    if src.get("key_tiles"):
        for k, e in _j(src["key_tiles"])["tiles"].items():
            keyed[int(k)] = e
    out = []
    for k, v in d["answers"].items():
        n = int(k)
        if isinstance(v, str):
            e = keyed.get(n, {})
            out.append({"tile": n, "plate": e.get("plate"), "page": e.get("page"), "box": _box(e.get("box")), "words": v, "extra": {}})
        elif src.get("staff_start"):
            st = str(v.get("staff", "")).split("/")
            page = int(st[1]) if len(st) >= 3 and st[1].isdigit() else None
            words = "%s clef, %s fifths" % (v.get("sean_clef"), v.get("sean_fifths"))
            out.append({"tile": n, "plate": v.get("plate"), "page": page, "box": None, "words": words,
                        "extra": {"staff": v.get("staff"), "sean_clef": v.get("sean_clef"), "sean_fifths": v.get("sean_fifths")}})
        else:
            box = _box(v.get("box")) or _box(v.get("page_box"))
            extra = {x: v[x] for x in ("cls", "group", "role", "fate", "reading", "cell", "sub", "glyph") if x in v}
            out.append({"tile": n, "plate": v.get("plate"), "page": v.get("page"), "box": box, "words": v.get("sean"), "extra": extra})
    return out


def build_registry() -> Dict[str, Any]:
    tiles: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []
    for src in SOURCES:
        d = _j(src["file"])
        raw = _raw_tiles(src)
        sources.append({"lane": src["lane"], "file": "benchmarks/" + src["file"], "date": d.get("date"), "question": d.get("question"),
                        "verbatim": d.get("verbatim") or d.get("sean_verbatim"), "n_tiles": len(raw),
                        "box_from": ("benchmarks/" + src["key"]) if src.get("key") else ("benchmarks/" + src["key_tiles"]) if src.get("key_tiles") else
                        "the answers file itself" if not src.get("staff_start") else "none (a staff start, no box)"})
        for r in sorted(raw, key=lambda x: x["tile"]):
            if src.get("staff_start"):
                norm = {"kind": "clef", "value": None, "whole": True, "why": None}
            elif r["tile"] in src.get("unmapped_tiles", {}):
                norm = {"kind": "unmapped", "value": None, "whole": True, "why": src["unmapped_tiles"][r["tile"]]}
            else:
                norm = normalise(r["words"])
                if r["tile"] in src.get("partial_tiles", ()):
                    norm["whole"] = False
            tiles.append({"id": "%s #%d" % (src["lane"], r["tile"]), "lane": src["lane"], "source": "benchmarks/" + src["file"], "tile": r["tile"],
                          "plate": r["plate"], "page": r["page"], "box": r["box"], "words": r["words"], "kind": norm["kind"], "value": norm["value"],
                          "whole": norm["whole"], "why_unmapped": norm["why"], "extra": r["extra"]})
    n = len(tiles)
    counts = {"tiles": n, "mapped": sum(t["kind"] != "unmapped" for t in tiles), "unmapped": sum(t["kind"] == "unmapped" for t in tiles),
              "no_page_box": sum(t["box"] is None for t in tiles),
              "by_lane": dict(collections.Counter(t["lane"] for t in tiles)),
              "by_kind": dict(collections.Counter(t["kind"].split(":")[0] for t in tiles))}
    return {"about": "GENERATED by `python3 -m tools.omr.staged.judged_claims --build` (ROADMAP 2.295). Never edit by hand; the per-lane answers files "
                     "named in `sources` are the source. Boxes are PAGE pixels.", "sources": sources, "counts": counts, "tiles": tiles}


def _dump(reg: Dict[str, Any]) -> str:
    return json.dumps(reg, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def load_registry(path: pathlib.Path = REGISTRY) -> Dict[str, Any]:
    return json.loads(path.read_text())


def check_registry() -> List[str]:
    """Problems with the registry on disk (empty = it is exactly what the answers files produce)."""
    if not REGISTRY.exists():
        return ["%s does not exist (run --build)" % REGISTRY]
    want = _dump(build_registry())
    return [] if REGISTRY.read_text() == want else ["%s differs from what the answers files produce (run --build)" % REGISTRY.relative_to(ROOT)]


# ───────────────────────────── 3. the replay ─────────────────────────────

def doc_of(path: pathlib.Path, rows_ident: Dict[str, Any]) -> Optional[str]:
    s = (str(rows_ident.get("edition_path") or "") + " " + str(path)).lower()
    if "litolff" in s:
        return "litolff"
    if "breitkopf" in s or "brahms" in s:
        return "brahms"
    return None


def judge_tile(c: Any, tile: Dict[str, Any], *, dx: float = 0.0, dy: float = 0.0, kind: Optional[str] = None) -> Dict[str, Any]:
    """One registry tile against one page's LedgerInk canvas `c` (after `finish`). Returns the verdict dict (module doc: the overlap rule)."""
    from . import claim_readout as CR
    k = kind or tile["kind"]
    base = k.split(":")[0]
    res: Dict[str, Any] = {"id": tile["id"], "lane": tile["lane"], "plate": tile["plate"], "page": tile["page"], "kind": k, "words": tile["words"]}

    def cannot(why: str) -> Dict[str, Any]:
        res.update({"verdict": "cannot_tell", "why": why})
        return res

    if base == "unmapped" or base not in ACCEPT:
        return cannot("kind_unmapped")
    if not tile.get("box"):
        return cannot("no_page_box")
    x0, y0, x1, y1 = (int(round(v)) for v in (tile["box"][0] + dx, tile["box"][1] + dy, tile["box"][2] + dx, tile["box"][3] + dy))
    H, W = c.shape
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return cannot("box_off_page")
    sl = (slice(y0, y1), slice(x0, x1))
    accept = ACCEPT[base]
    ink = c.ink[sl]
    st = c.state[sl]
    fam = c.fam_eff[sl].astype(np.uint32)
    staff_bit = np.uint32(CR.FINE_BIT["staff_line"])
    staffpx = ink & (st == CR.ST_STAFF)
    m = fam | np.where(staffpx, staff_bit, np.uint32(0))
    sel = ink if "staff_line" in accept else (ink & ~staffpx)
    n = int(sel.sum())
    if n < MIN_INK:
        return cannot("box_on_no_ink")
    mm = m[sel]
    A = np.uint32(sum(int(CR.FINE_BIT[x]) for x in accept))
    N = np.uint32(sum(int(CR.FINE_BIT[x]) for x in NEUTRAL if x not in accept))
    right = (mm & A) != 0
    OTHER = np.uint32(CR.FINE_BIT["other"])
    unnamed = ((mm & OTHER) != 0) & ~right            # a claim the readout files under `other`: its kind is not known here
    wrong = ((mm & ~A & ~N & ~OTHER) != 0) & ~right
    none = mm == 0
    weak = getattr(c, "weak_eff", c.weak)[sl][sel]
    src_masks = {name: (getattr(c, attr)[sl][sel] if hasattr(c, attr) else (fam[sel] if attr == "src_cell" else np.zeros(int(sel.sum()), np.uint32)))
                 for attr, name in SOURCES_NAMED}
    # "stands": a READ claim of another kind that is DECIDED. Ink the cell settle left OPEN between kinds (`contested`: it could not choose) holds every kind that
    # fits, none of them a decided READ claim, so it never counts as a wrong claim standing (reported apart as `open_share`, the old rule's AGREES kept).
    opn = (getattr(c, "open", None)[sl][sel] & getattr(c, "incell")[sl][sel]) if hasattr(c, "open") else np.zeros(int(sel.sum()), bool)
    stand = src_masks["register area"] | src_masks["page-stroke claim"] | np.where(opn, np.uint32(0), src_masks["cell settle"])
    wrong_any = (stand & ~A & ~N & ~OTHER) != 0        # a READ claim of another kind STANDS here (his kind may stand too)
    R, Wr, Wa = float(right.mean()), float(wrong.mean()), float(wrong_any.mean())
    open_share = float((opn & right).mean())
    weak_px = none & (weak != 0)
    refused_px = none & (c.uk[sl][sel] >= 5)
    claimed: Dict[str, float] = {}
    for kk in CR.FINE_KINDS:
        s = float(((mm & np.uint32(CR.FINE_BIT[kk])) != 0).mean())
        if s >= 0.02:
            claimed[kk] = round(s, 3)
    weak_by = {kk: round(float((weak_px & ((weak & np.uint32(CR.FINE_BIT[kk])) != 0)).mean()), 3) for kk in CR.FINE_KINDS
               if (weak_px & ((weak & np.uint32(CR.FINE_BIT[kk])) != 0)).any()}
    # where each READ owner came from, per kind: {kind: {source name: share of the box's ink}} (kinds he did not name show beside his)
    sources: Dict[str, Dict[str, float]] = {}
    for kk in claimed:
        bit = np.uint32(CR.FINE_BIT[kk])
        sources[kk] = {name: round(float(((sm & bit) != 0).mean()), 3) for name, sm in src_masks.items() if ((sm & bit) != 0).any()}
    U = float(unnamed.mean())
    if R < AGREE_MIN and U >= AGREE_MIN:
        return cannot("owned_by_unnamed_kind (the readout files it under `other`)")
    twice = False
    if R >= AGREE_MIN:
        if Wa >= CONTRA_MIN:
            v, twice = "contradicts", True
        else:
            v = "agrees"
    elif Wr > R and Wr >= CONTRA_MIN:
        v = "contradicts"
    else:
        v = "unclaimed"
    res.update({"verdict": v, "ink_px": n, "right": round(R, 3), "wrong": round(Wr, 3), "wrong_any": round(Wa, 3), "twice": twice, "open_share": round(open_share, 3),
                "no_owner": round(float(none.mean()), 3), "weak_only": round(float(weak_px.mean()), 3), "weak_kinds": weak_by,
                "refused_box": round(float(refused_px.mean()), 3), "read_kinds": claimed, "sources": sources, "box_px": [x0, y0, x1, y1]})
    return res


def _crop(c: Any, r: Dict[str, Any], accept_kind: str, out: pathlib.Path) -> None:
    """A crop of the ledger around one verdict: green = ink a READ claim of the kind Sean named owns, red = ink owned only by another kind, grey = no
    READ owner. The thin box is the registry box (not wider than the crop)."""
    import cv2
    from . import claim_readout as CR
    x0, y0, x1, y1 = r["box_px"]
    pad = 48
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(c.shape[1], x1 + pad), min(c.shape[0], y1 + pad)
    sl = (slice(Y0, Y1), slice(X0, X1))
    ink = c.ink[sl]
    fam = c.fam_eff[sl].astype(np.uint32)
    A = np.uint32(sum(int(CR.FINE_BIT[x]) for x in ACCEPT[accept_kind.split(":")[0]]))
    img = np.full(ink.shape + (3,), 255, np.uint8)
    img[ink] = (150, 150, 150)
    img[ink & ((fam & A) != 0)] = (60, 160, 60)
    img[ink & (fam != 0) & ((fam & A) == 0)] = (50, 50, 220)
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    cv2.rectangle(img, ((x0 - X0) * 3, (y0 - Y0) * 3), ((x1 - X0) * 3, (y1 - Y0) * 3), (230, 120, 0), 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)


def replay(rec: str, *, doc: Optional[str] = None, pages: Optional[Sequence[int]] = None, registry: Optional[Dict[str, Any]] = None,
           variants: Optional[Dict[str, Any]] = None, crops: Optional[pathlib.Path] = None, env: Optional[Dict[str, str]] = None,
           cm_root: Optional[pathlib.Path] = None, log=print) -> Dict[str, Any]:
    """Replay the registry over the slice `rec`. `variants` = {name: fn(canvas, tile, spacing_px) -> verdict dict} judged on the same canvases
    as the base run (controls). Returns {plate, slice, pages, results: {variant: [verdict dicts]}, ...}."""
    from . import cell_map as CM
    from . import claim_readout as CR
    src = CR.resolve_source(rec)
    in_rec = CR.slice_pages(src)
    reg = registry or load_registry()
    rows_all = CR.read_rows(src, in_rec if not pages else [p for p in pages if p in in_rec])
    unnamed = sorted({str(o["detail"]["owner"]) for o in rows_all["observations"] if o.get("quantity") == "claimed_area" and o.get("detail")
                      and o["detail"].get("owner") and (o["detail"].get("unit") in ("area", "page_ink") or o["detail"].get("page_strokes"))
                      and o["detail"].get("standing", "READ") == "READ" and CR.fine_of(str(o["detail"]["owner"])) == "other"})
    ed = CR.edition_info(rows_all)
    plate = doc or doc_of(src, ed)
    if plate is None:
        raise SystemExit("cannot tell the plate of %s; pass --doc litolff|brahms" % src)
    want = [t for t in reg["tiles"] if t["plate"] == plate]
    asked = set(pages) if pages else None
    pdf = CR.LIB / ed["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    todo_pages = sorted({t["page"] for t in want if t["page"] in in_rec and (asked is None or t["page"] in asked)})
    names = ["base"] + list((variants or {}).keys())
    results: Dict[str, List[Dict[str, Any]]] = {n: [] for n in names}
    by_page: Dict[Any, List[Dict[str, Any]]] = collections.defaultdict(list)
    for t in want:
        by_page[t["page"]].append(t)
    links = strokes = 0
    for pg in todo_pages:
        t0 = time.time()
        canvas, _ver, _pws, _cells = CR.build_page(rows_all, pdf, pg, cm_root, env, ledger=True)
        links += canvas.links_filed
        strokes += canvas.strokes_filed
        sp = float(canvas.sp) or 32.0
        for t in by_page[pg]:
            results["base"].append(judge_tile(canvas, t))
            for name, fn in (variants or {}).items():
                results[name].append(fn(canvas, t, sp))
            if crops is not None:
                r = results["base"][-1]
                if r["verdict"] in ("contradicts",) and "box_px" in r:
                    _crop(canvas, r, r["kind"], crops / ("%s_%s_p%d.png" % (plate, re.sub(r"[^0-9a-z]+", "-", t["id"].lower()).strip("-"), pg)))
        log("  page %d: %d tiles judged (%.0f s, spacing %.1f px)" % (pg, len(by_page[pg]), time.time() - t0, sp))
        del canvas, _pws, _cells
    for pg, ts in by_page.items():
        if pg in todo_pages:
            continue
        for t in ts:
            why = "page_not_in_rec" if pg not in in_rec else "page_not_asked"
            for n in names:
                results[n].append({"id": t["id"], "lane": t["lane"], "plate": plate, "page": pg, "kind": t["kind"], "words": t["words"],
                                   "verdict": "cannot_tell", "why": why if t["page"] is not None else "no_page"})
    stamp = json.loads((src / "stamp.json").read_text()) if (src / "stamp.json").exists() else {}
    return {"plate": plate, "slice": str(src), "slice_pages": in_rec, "pages_judged": todo_pages, "results": results,
            "links": links, "strokes": strokes, "unnamed_owners": unnamed, "slice_written": time.strftime("%Y-%m-%d %H:%M", time.localtime(
                stamp.get("mtime") or (src / "observations.jsonl").stat().st_mtime))}


# ───────────────────────────── 4. the report ─────────────────────────────

VERDICTS = ("agrees", "contradicts", "unclaimed", "cannot_tell")


def tally(rs: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    c = collections.Counter(r["verdict"] for r in rs)
    return {v: c.get(v, 0) for v in VERDICTS}


def summary_line(plate: str, rs: Sequence[Dict[str, Any]]) -> str:
    t = tally(rs)
    twice = sum(1 for r in rs if r["verdict"] == "contradicts" and r.get("twice"))
    opn = sum(1 for r in rs if r["verdict"] == "agrees" and r.get("open_share", 0.0) >= CONTRA_MIN)
    return "%s: %d tiles  agrees %d%s / contradicts %d%s / unclaimed %d / cannot tell %d" % (
        plate.upper(), len(rs), t["agrees"], (" (of which %d with >=30%% of the ink left open between kinds by the cell settle)" % opn) if opn else "",
        t["contradicts"], (" (of which claimed twice %d)" % twice) if twice else "", t["unclaimed"], t["cannot_tell"])


def render(rep: Dict[str, Any], unclaimed: bool = False) -> List[str]:
    rs = rep["results"]["base"]
    L = ["judged_claims -- Sean's answered CLAIM tiles replayed on the page ledger (ROADMAP 2.295)",
         "  slice %s (written %s), slice holds pages %s; judged on pages %s; page-ledger links %d of %d strokes%s" % (
             rep["slice"], rep["slice_written"], rep["slice_pages"], rep["pages_judged"], rep["links"], rep["strokes"],
             "" if rep["links"] else "  -- NONE: a gather before 2.284"),
         "  READ-claim owners the readout cannot name (filed under `other`): %s" % (", ".join(rep["unnamed_owners"]) or "none"),
         "  overlap rule: R = share of the box's ink a READ claim of Sean's kind owns; Wo = share only other kinds' READ claims own; Wa = share another kind's READ claim "
         "stands on, his kind or not (staff/ledger line, dot crossings are the mark's). agrees R>=%.1f and Wa<%.1f; CONTRADICTS Wa>=%.1f with R>=%.1f (CLAIMED TWICE) or R<%.1f, Wo>R, Wo>=%.1f; "
         "unclaimed otherwise; cannot tell = page not in slice / box on <%d ink px / no box / kind unmapped. Owners come from: cell settle / register area / page-stroke claim."
         % (AGREE_MIN, CONTRA_MIN, CONTRA_MIN, AGREE_MIN, AGREE_MIN, CONTRA_MIN, MIN_INK), "  " + summary_line(rep["plate"], rs)]
    why = collections.Counter(r.get("why") for r in rs if r["verdict"] == "cannot_tell")
    if why:
        L.append("  cannot tell because: " + ", ".join("%s %d" % (k, v) for k, v in why.most_common()))
    bad = [r for r in rs if r["verdict"] == "contradicts"]
    for r in bad:
        L.append("  CONTRADICTS%s  %s  p%s  Sean: %r (%s)  READ claims there: %s  (right %.2f, other kinds stand on %.2f, other kinds only %.2f, no owner %.2f; box %s)" % (
            " (CLAIMED TWICE)" if r.get("twice") else "", r["id"], r["page"], r["words"], r["kind"],
            ", ".join("%s %.0f%% [%s]" % (k, 100 * v, ", ".join("%s %.0f%%" % (sn, 100 * sv) for sn, sv in r.get("sources", {}).get(k, {}).items()) or "?")
                      for k, v in sorted(r["read_kinds"].items(), key=lambda kv: -kv[1])),
            r["right"], r.get("wrong_any", r["wrong"]), r["wrong"], r["no_owner"], r["box_px"]))
    if unclaimed:
        for r in [r for r in rs if r["verdict"] == "unclaimed"]:
            L.append("  unclaimed    %s  p%s  Sean: %r (%s)  READ: %s  weak: %s  refused box %.0f%%  no owner %.0f%%" % (
                r["id"], r["page"], r["words"], r["kind"], r["read_kinds"] or "-", r["weak_kinds"] or "-", 100 * r["refused_box"], 100 * r["no_owner"]))
    return L


# ───────────────────────────── 5. the controls ─────────────────────────────

def controls(rec: str, *, doc: Optional[str] = None, pages: Optional[Sequence[int]] = None, log=print, **kw: Any) -> int:
    """Each control must fail where it should. (a) one of his rest tiles relabelled in memory must turn into exactly that tile's CONTRADICTS;
    (b) every box shifted by three staff spaces must collapse `agrees`; (c) the 2.288 r3 mistake planted on the real pixels of Sean's eighth note (Brahms
    p14, a whole-rest claim on a notehead) must be caught as exactly that tile's CONTRADICTS. Returns the number of failed controls."""
    reg = load_registry()
    target: Dict[str, str] = {}
    PLANT_ID = "2.288 r3 #4"      # Sean: an EIGHTH NOTE (Brahms p14), which 2.288 r3 claimed as a whole rest

    def relabel(c: Any, t: Dict[str, Any], sp: float) -> Dict[str, Any]:
        return judge_tile(c, t, kind="notehead") if t["id"] == target.get("id") else judge_tile(c, t)

    def shift(c: Any, t: Dict[str, Any], sp: float) -> Dict[str, Any]:
        return judge_tile(c, t, dx=3.0 * sp)

    def plant(c: Any, t: Dict[str, Any], sp: float) -> Dict[str, Any]:
        """The 2.288 r3 mistake, planted on the real pixels of the real mark: every ink pixel of Sean's eighth note is re-owned by a whole-rest claim."""
        if t["id"] != PLANT_ID or not t.get("box"):
            return judge_tile(c, t)
        from . import claim_readout as CR
        x0, y0, x1, y1 = (int(round(v)) for v in t["box"])
        sl = (slice(max(0, y0), y1), slice(max(0, x0), x1))
        keep = c.fam_eff[sl].copy()
        keep_src = {a: getattr(c, a)[sl].copy() for a, _n in SOURCES_NAMED}
        planted = np.where(c.ink[sl], CR.FINE_BIT["rest"], np.uint32(0)).astype(c.fam_eff.dtype)
        c.fam_eff[sl] = planted
        for a, _n in SOURCES_NAMED:
            getattr(c, a)[sl] = planted if a == "src_cell" else np.uint32(0)
        try:
            return judge_tile(c, t)
        finally:
            c.fam_eff[sl] = keep
            for a, v in keep_src.items():
                getattr(c, a)[sl] = v

    # pass 1: find a rest tile that agrees (the control needs a case that passes)
    first = replay(rec, doc=doc, pages=pages, registry=reg, log=lambda *_: None, **kw)
    ok = [r for r in first["results"]["base"] if r["verdict"] == "agrees" and r["kind"].startswith("rest")]
    bad = 0
    if not ok:
        log("  control (a): NOT RUN -- no rest tile of Sean's agrees on this slice")
        bad += 1
    else:
        target["id"] = ok[0]["id"]
        rep = replay(rec, doc=doc, pages=pages, registry=reg, variants={"relabel": relabel, "shift": shift, "plant": plant}, log=lambda *_: None, **kw)
        base = {r["id"]: r["verdict"] for r in rep["results"]["base"]}
        rel = {r["id"]: r["verdict"] for r in rep["results"]["relabel"]}
        moved = sorted(i for i in base if base[i] != rel[i])
        good = moved == [target["id"]] and rel[target["id"]] == "contradicts"
        log("  control (a) relabel %s (%r, a rest) as a note in memory: %s -> %s; tiles that moved: %s   %s" % (
            target["id"], ok[0]["words"], base[target["id"]], rel[target["id"]], moved, "OK (exactly that tile)" if good else "FAILED"))
        bad += 0 if good else 1
        t0, t1 = tally(rep["results"]["base"]), tally(rep["results"]["shift"])
        collapsed = t1["agrees"] < t0["agrees"] and (t1["unclaimed"] + t1["cannot_tell"]) > (t0["unclaimed"] + t0["cannot_tell"])
        log("  control (b) every box shifted 3 staff spaces right: agrees %d -> %d, unclaimed %d -> %d, cannot tell %d -> %d, contradicts %d -> %d   %s" % (
            t0["agrees"], t1["agrees"], t0["unclaimed"], t1["unclaimed"], t0["cannot_tell"], t1["cannot_tell"], t0["contradicts"], t1["contradicts"],
            "OK (agrees collapsed)" if collapsed else "FAILED"))
        bad += 0 if collapsed else 1
        pb = {r["id"]: r for r in rep["results"]["base"]}.get(PLANT_ID)
        pp = {r["id"]: r for r in rep["results"]["plant"]}.get(PLANT_ID)
        if first["plate"] != "brahms":
            log("  control (c) plant the 2.288 r3 false claim: n/a on %s (its tile is Brahms p14)" % first["plate"])
        elif pb is None or pb["verdict"] == "cannot_tell":
            log("  control (c) plant the 2.288 r3 false claim: NOT RUN -- %s is not judged on this slice" % PLANT_ID)
            bad += 1
        else:
            moved = sorted(r["id"] for r in rep["results"]["plant"] if r["verdict"] != {x["id"]: x["verdict"] for x in rep["results"]["base"]}[r["id"]])
            good = pb["verdict"] == "agrees" and pp["verdict"] == "contradicts" and moved == [PLANT_ID]
            log("  control (c) plant a whole-rest claim on the pixels of %s (Sean: %r): %s -> %s (READ there: %s); tiles that moved: %s   %s" % (
                PLANT_ID, pb["words"], pb["verdict"], pp["verdict"], pp.get("read_kinds"), moved, "OK (caught, exactly that tile)" if good else "FAILED"))
            bad += 0 if good else 1
    return bad


# ───────────────────────────── 6. the command ─────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="judged_claims", description=__doc__.split("\n")[2].strip())
    ap.add_argument("rec", nargs="?", help="a slice directory, `plate:tag`, a small record, or `brahms.main` (= claim-readout-slices-brahms.main)")
    ap.add_argument("--doc", choices=("litolff", "brahms"), default=None)
    ap.add_argument("--pages", default="", help="comma list of pages to judge (default: every registry page the slice holds)")
    ap.add_argument("--crops", default=None, help="write a crop per CONTRADICTS here (green = Sean's kind owns it, red = another READ kind, grey = no READ owner)")
    ap.add_argument("--json", default=None, help="write the verdicts here")
    ap.add_argument("--unclaimed", action="store_true", help="also list the unclaimed tiles (the to-do list)")
    ap.add_argument("--against", default=None, help="a --json file of a BASELINE run (main): exit 1 only for contradictions it does not also have")
    ap.add_argument("--controls", action="store_true", help="run the controls (relabel one rest tile; shift every box 3 spaces)")
    ap.add_argument("--build", action="store_true", help="regenerate the registry")
    ap.add_argument("--check", action="store_true", help="fail if the registry is not what the answers files produce")
    a = ap.parse_args(argv)
    if a.build:
        REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        reg = build_registry()
        REGISTRY.write_text(_dump(reg))
        c = reg["counts"]
        print("wrote %s: %d tiles (%d mapped, %d unmapped, %d without a page box) from %d answers files" % (
            REGISTRY.relative_to(ROOT), c["tiles"], c["mapped"], c["unmapped"], c["no_page_box"], len(reg["sources"])))
        return 0
    if a.check:
        bad = check_registry()
        for b in bad:
            print("FAIL: " + b)
        print("judged-claims registry: %s" % ("matches the answers files" if not bad else "STALE"))
        return 1 if bad else 0
    if not a.rec:
        ap.error("REC is required (or --build / --check)")
    os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
    rec = a.rec
    from . import claim_readout as CR
    if not os.path.exists(rec) and ":" not in rec and (CR.RECORDS / ("claim-readout-slices-%s" % rec)).exists():
        rec = str(CR.RECORDS / ("claim-readout-slices-%s" % rec))
    pages = [int(x) for x in a.pages.split(",") if x] or None
    crops = pathlib.Path(a.crops) if a.crops else None
    if a.controls:
        print("judged_claims controls on %s" % rec)
        return 1 if controls(rec, doc=a.doc, pages=pages) else 0
    rep = replay(rec, doc=a.doc, pages=pages, crops=crops)
    for line in render(rep, a.unclaimed):
        print(line)
    if a.json:
        pathlib.Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.json).write_text(json.dumps({k: v for k, v in rep.items()}, indent=1, sort_keys=True, default=str))
    bad = {r["id"] for r in rep["results"]["base"] if r["verdict"] == "contradicts"}
    if a.against:
        base = {r["id"] for r in json.loads(pathlib.Path(a.against).read_text())["results"]["base"] if r["verdict"] == "contradicts"}
        new = sorted(bad - base)
        print("  against baseline %s: %d contradiction(s) it already has, %d NEW%s" % (a.against, len(bad & base), len(new), (": " + ", ".join(new)) if new else ""))
        return 1 if new else 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
