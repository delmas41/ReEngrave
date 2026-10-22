#!/usr/bin/env python3
"""Phase 1 of the staff-identity audit: one evidence row per staff per system.

MEASUREMENT ONLY. This script changes no pipeline behaviour; it reads the scan
benchmark's already-committed transcriptions and emits every signal S1-S9 that
`docs/staff-identity-audit-plan-2026-09-04.md` defines, beside the hand-verified
truth from `benchmarks/omr-scan-e2e-2026-09/works.json`.

    python3 benchmarks/omr-staff-identity-2026-09/build_evidence.py

Writes `evidence.json` (full, nested) and `evidence.csv` (flat, one row per
staff) into this directory so a later session can re-score without re-deriving.

⚠️ ANSWER-KEY DISCIPLINE. `works.json` and the reference `.mxl` are SCORING KEYS
and are never consulted by a signal. Two fields are truth-derived and are named
so they cannot be mistaken for signals: `TRUTH_*` and `CEILING_hand_label`.
Dossiers are not read at all (they are generated from the same MusicXML).

⚠️ TRANSCRIPTION PROVENANCE. The `..graft09` fixtures in the scan benchmark were
produced by `scan_eval.py` with `OMR_SCAN_EVAL_WEIGHTS` pinned to
`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt` (the shipped scan
slot). They are read, never regenerated, so no detector time is spent and the
evidence is exactly what the shipped pipeline produced.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                     # noqa: E402
from tools.omr.score_layouts import LAYOUTS                   # noqa: E402

SCAN_BENCH = REPO / "benchmarks" / "omr-scan-e2e-2026-09"
WORKS = SCAN_BENCH / "works.json"
# The fixtures are gitignored build products and live in the MAIN checkout.
FIXTURES_CANDIDATES = [
    SCAN_BENCH / "fixtures",
    Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-scan-e2e-2026-09/fixtures"),
]
TAG = os.getenv("STAFF_IDENTITY_TAG", ".graft09")


def fixtures_dir() -> Path:
    for c in FIXTURES_CANDIDATES:
        if c.is_dir() and any(c.glob(f"*{TAG}.omr.json")):
            return c
    raise SystemExit(
        "no transcription fixtures found; run the scan benchmark first "
        f"(looked in {[str(c) for c in FIXTURES_CANDIDATES]})")


def library_root() -> Path:
    from tools.library.score_library import library_root as lr
    return Path(lr())


# ────────────────────────────────────────────────────────── truth (scoring key)

def _resolve_staff_truth(row: dict, rows_by_id: dict) -> tuple[list | None, str]:
    """Return (list of {name, parts, clef?, key?}, provenance)."""
    st = row.get("staves")
    if isinstance(st, str) and st.startswith("same-as:"):
        other = rows_by_id[st.split(":", 1)[1]]
        got, prov = _resolve_staff_truth(other, rows_by_id)
        return got, f"alias->{st.split(':', 1)[1]}:{prov}"
    if isinstance(st, list):
        return st, "works.json:staves"
    cond = row.get("condensation") or {}
    sap = cond.get("staves_as_printed")
    if isinstance(sap, list):
        # Five-line staves only: a one-line percussion staff is invisible to a
        # five-line detector, so a positional join past it would be wrong.
        return ([x for x in sap if x.get("lines") == 5],
                "works.json:condensation.staves_as_printed (5-line only)")
    sysp = row.get("systems_as_printed")
    if isinstance(sysp, dict):
        out = []
        for k in sorted(k for k in sysp if k.startswith("system_")):
            out.append(sysp[k])
        return out, "works.json:systems_as_printed (per-system, INFORMATIONAL)"
    return None, "none"


# ─────────────────────────────────────────── reference-derived clef/key (truth)

_NS = {"mx": "http://www.musicxml.org/ns/musicxml"}


def _read_musicxml(path: Path) -> ET.Element | None:
    try:
        if path.suffix == ".mxl":
            with zipfile.ZipFile(path) as z:
                name = None
                try:
                    container = ET.fromstring(z.read("META-INF/container.xml"))
                    rf = container.find(".//rootfile")
                    if rf is not None:
                        name = rf.get("full-path")
                except KeyError:
                    pass
                if not name:
                    cands = [n for n in z.namelist()
                             if n.endswith((".xml", ".musicxml"))
                             and not n.startswith("META-INF")]
                    if not cands:
                        return None
                    name = cands[0]
                return ET.fromstring(z.read(name))
        return ET.parse(path).getroot()
    except Exception:
        return None


def _tag(el) -> str:
    return el.tag.split("}")[-1]


def reference_part_facts(path: Path) -> list[dict]:
    """Per reference part: written clef + written fifths at the file's start.

    Stdlib only (host python is 3.9; music21 lives in .venv-omrned). This is a
    SCORING KEY, used only to extend clef/key truth to rows whose works.json
    entry hand-reads neither. Validated against the one row that hand-reads
    both (see `validate_reference_truth` below).
    """
    root = _read_musicxml(path)
    if root is None:
        return []
    names = {}
    for sp in root.iter():
        if _tag(sp) == "score-part":
            pn = sp.find("./{*}part-name")
            names[sp.get("id")] = (pn.text or "").strip() if pn is not None else ""
    out = []
    for part in root.iter():
        if _tag(part) != "part":
            continue
        pid = part.get("id")
        clef, fifths = None, None
        for m in part:
            if _tag(m) != "measure":
                continue
            for attrs in m:
                if _tag(attrs) != "attributes":
                    continue
                for ch in attrs:
                    if _tag(ch) == "key" and fifths is None:
                        f = ch.find("./{*}fifths")
                        if f is not None and f.text:
                            fifths = int(f.text)
                    if _tag(ch) == "clef" and clef is None:
                        sign = ch.find("./{*}sign")
                        line = ch.find("./{*}line")
                        if sign is not None:
                            clef = (sign.text or "").strip(), int(line.text) if line is not None and line.text else None
            if clef is not None and fifths is not None:
                break
        out.append({"part_id": pid, "part_name": names.get(pid, ""),
                    "clef_sign_line": clef, "written_fifths": fifths})
    return out


_CLEF_FROM_SIGN = {
    ("G", 2): "treble", ("G", 1): "french", ("F", 4): "bass", ("F", 3): "baritone",
    ("C", 3): "alto", ("C", 4): "tenor", ("C", 1): "soprano", ("C", 2): "mezzo",
    ("percussion", None): "percussion",
}


def clef_name_from_sign(sl) -> str | None:
    if not sl:
        return None
    return _CLEF_FROM_SIGN.get((sl[0], sl[1]))


# ──────────────────────────────────────────────────────────────── the signals

def signed_fifths(ks: dict | None) -> int | None:
    """The pipeline stores sharps/flats as counts; the circle-of-fifths value is
    signed. A staff that read neither returns None (abstention), which is NOT
    the same as 0 (C major / a natural key)."""
    if not ks:
        return None
    sharps = int(ks.get("sharps") or 0)
    flats = int(ks.get("flats") or 0)
    if sharps and flats:
        return None                    # incoherent reading; abstain
    return sharps if sharps else -flats


def instruments_with_offset(offset: int) -> list[str]:
    """Every instrument whose transposition can produce this written-vs-concert
    offset. `default_fifths_offset` is what `instruments.py` stores; a
    key-dependent instrument (clarinet, horn) has `chromatic is None` and its
    real offset depends on the key the label names, so we admit it for any
    offset it can plausibly take (its default, and the common alternatives)."""
    out = []
    for inst in INST.INSTRUMENTS:
        if inst.unpitched:
            continue
        if inst.chromatic is None:
            # key-dependent: B-flat (+2), A (+3), F (+1), E-flat (-3), C (0),
            # D (-2) are the pitches these instruments are actually built in.
            if offset in (0, 1, 2, 3, -2, -3):
                out.append(inst.name)
        elif inst.default_fifths_offset == offset:
            out.append(inst.name)
    return out


def pitch_to_midi(p) -> int | None:
    """The transcription stores `pitch` as a dict or a string; accept both."""
    if p is None:
        return None
    if isinstance(p, dict):
        for k in ("midi", "midi_note", "value"):
            if k in p and isinstance(p[k], (int, float)):
                return int(p[k])
        step, octv, alt = p.get("step"), p.get("octave"), p.get("alter") or 0
        if step is not None and octv is not None:
            base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
            if step in base:
                return 12 * (int(octv) + 1) + base[step] + int(alt)
        return None
    if isinstance(p, str):
        m = re.match(r"^([A-Ga-g])([#b\-]*)(-?\d+)$", p.strip())
        if m:
            base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
            alt = m.group(2).count("#") - m.group(2).count("b") - m.group(2).count("-")
            return 12 * (int(m.group(3)) + 1) + base[m.group(1).upper()] + alt
    if isinstance(p, (int, float)):
        return int(p)
    return None


NOTEHEAD_RE = re.compile(r"^notehead", re.I)
DYNAMIC_RE = re.compile(r"^dynamic", re.I)


def staff_detections(staff: dict) -> list[dict]:
    out = []
    for m in staff.get("measures", []):
        for d in m.get("detections", []):
            d = dict(d)
            d["_measure_index"] = m.get("measure_index")
            out.append(d)
    return out


def s4_envelope(dets: list[dict]) -> dict:
    midis = []
    for d in dets:
        if d.get("category") != "notehead":
            continue
        mi = pitch_to_midi(d.get("pitch"))
        if mi is not None:
            midis.append(mi)
    if not midis:
        return {"lo": None, "hi": None, "n": 0, "median": None, "bimodal_gap": None}
    midis.sort()
    n = len(midis)
    # crude two-envelope test: the largest interior gap in the sorted pitches
    gaps = [(midis[i + 1] - midis[i], i) for i in range(n - 1)]
    biggest = max(gaps)[0] if gaps else 0
    return {"lo": midis[0], "hi": midis[-1], "n": n,
            "median": midis[n // 2], "bimodal_gap": biggest}


def s4_range_compatible(lo, hi) -> list[str]:
    if lo is None:
        return []
    out = []
    for inst in INST.INSTRUMENTS:
        if inst.unpitched:
            continue
        r_lo, r_hi = inst.written_range
        if lo >= r_lo and hi <= r_hi:
            out.append(inst.name)
    return out


def s7_texture(staff: dict) -> dict:
    """Intra-staff multiplicity texture, measured per measure.

    A dyad bar is one whose noteheads include two at the same x within a
    notehead's width but different y (a chord, i.e. divisi written as a double
    stop). A divisi bar is one carrying stems in both directions."""
    dyad_bars = divisi_bars = rest_bars = note_bars = 0
    for m in staff.get("measures", []):
        heads = [d for d in m.get("detections", []) if d.get("category") == "notehead"]
        rests = [d for d in m.get("detections", []) if d.get("category") == "rest"]
        flags = [d for d in m.get("detections", []) if d.get("category") == "flag"]
        if heads:
            note_bars += 1
        if rests and not heads:
            rest_bars += 1
        # dyads: two heads whose x-centres are within one head width
        xs = sorted(((h["bbox_page"][0] + h["bbox_page"][2] / 2.0,
                      h["bbox_page"][1], h["bbox_page"][2]) for h in heads))
        got_dyad = False
        for i in range(len(xs) - 1):
            if abs(xs[i + 1][0] - xs[i][0]) <= max(xs[i][2], 1) and \
                    abs(xs[i + 1][1] - xs[i][1]) > 2:
                got_dyad = True
                break
        if got_dyad:
            dyad_bars += 1
        ups = sum(1 for f in flags if "Up" in f.get("class", ""))
        downs = sum(1 for f in flags if "Down" in f.get("class", ""))
        if ups and downs:
            divisi_bars += 1
    return {"dyad_bars": dyad_bars, "divisi_bars": divisi_bars,
            "rest_only_bars": rest_bars, "note_bars": note_bars,
            "n_bars": len(staff.get("measures", []))}


def staff_band(staff: dict) -> tuple[float, float, float] | None:
    g = staff.get("staff_geometry") or {}
    ys = g.get("line_ys_page")
    if not ys:
        return None
    return float(min(ys)), float(max(ys)), float(g.get("line_spacing_px") or 0)


def s9_placement(staff: dict, above: dict | None, below: dict | None) -> dict:
    """Where this staff's dynamics / arcs sit relative to the gaps around it.

    ⚠️ Ownership here is the PIPELINE's: a detection is already filed under the
    staff whose measure cell it fell in. So this measures whether a mark the
    pipeline gave to THIS staff is actually printed in the gap it shares with a
    neighbour — the ambiguity S9 is about — not an independent re-attribution.
    """
    band = staff_band(staff)
    if band is None:
        return {"available": False}
    top, bot, sp = band
    gap_above_lo = (staff_band(above)[1] if above and staff_band(above) else None)
    gap_below_hi = (staff_band(below)[0] if below and staff_band(below) else None)

    def where(y: float) -> str:
        if y < top - 0.25 * sp:
            if gap_above_lo is not None and y > gap_above_lo:
                mid = (gap_above_lo + top) / 2.0
                return "gap_above_near_me" if y > mid else "gap_above_near_them"
            return "above_outside"
        if y > bot + 0.25 * sp:
            if gap_below_hi is not None and y < gap_below_hi:
                mid = (bot + gap_below_hi) / 2.0
                return "gap_below_near_me" if y < mid else "gap_below_near_them"
            return "below_outside"
        return "inside_staff"

    counts = Counter()
    arc_split = 0
    for d in staff_detections(staff):
        cls = d.get("class", "")
        cat = d.get("category", "")
        bb = d.get("bbox_page")
        if not bb:
            continue
        ycen = bb[1] + bb[3] / 2.0
        if cat == "dynamic" or DYNAMIC_RE.match(cls):
            counts["dyn_" + where(ycen)] += 1
        elif cls in ("slur", "tie"):
            counts[cls + "_" + where(ycen)] += 1
            # an arc whose vertical span straddles a neighbouring staff's band
            if gap_above_lo is not None and bb[1] < gap_above_lo:
                arc_split += 1
            if gap_below_hi is not None and bb[1] + bb[3] > gap_below_hi:
                arc_split += 1
    return {
        "available": True,
        "dyn_total": sum(v for k, v in counts.items() if k.startswith("dyn_")),
        "dyn_inside_staff": counts.get("dyn_inside_staff", 0),
        "dyn_gap_above_near_me": counts.get("dyn_gap_above_near_me", 0),
        "dyn_gap_above_near_them": counts.get("dyn_gap_above_near_them", 0),
        "dyn_gap_below_near_me": counts.get("dyn_gap_below_near_me", 0),
        "dyn_gap_below_near_them": counts.get("dyn_gap_below_near_them", 0),
        "dyn_ambiguous": (counts.get("dyn_gap_above_near_them", 0)
                          + counts.get("dyn_gap_below_near_them", 0)),
        "slur_total": sum(v for k, v in counts.items() if k.startswith("slur_")),
        "tie_total": sum(v for k, v in counts.items() if k.startswith("tie_")),
        "arc_reaches_neighbour_band": arc_split,
        "hairpin_total": 0,   # no wedge/hairpin class fires on this corpus at all
    }


def s8_brace(staff: dict) -> int:
    return sum(1 for d in staff_detections(staff)
               if d.get("class") == "brace")


# ───────────────────────────────────────────────────────── S5, the order prior

def score_order_prediction(n_staves: int) -> dict:
    """The pure positional prior: for each standard layout, what instrument does
    a staff at this position get, with NO label and NO clef consulted?

    Reported as the prediction of the layout whose part count matches the page's
    staff count (the only fit a label-free prior can make), plus the set of
    predictions across every layout that could fit."""
    exact = [L for L in LAYOUTS if len(L.parts) == n_staves]
    by_pos: list[list[str]] = [[] for _ in range(n_staves)]
    for L in exact:
        for i, p in enumerate(L.parts):
            by_pos[i].append(p)
    fallback = []
    if not exact:
        # no layout has exactly this many parts: scale each layout's part list
        # onto the page's staff count proportionally (the weakest honest prior)
        for L in LAYOUTS:
            if len(L.parts) < 3:
                continue
            for i in range(n_staves):
                j = min(len(L.parts) - 1, int(i * len(L.parts) / n_staves))
                by_pos[i].append(L.parts[j])
            fallback.append(L.name)
    return {
        "exact_layouts": [L.name for L in exact],
        "fallback_layouts": fallback,
        "per_position": [sorted(set(c)) for c in by_pos],
        "per_position_modal": [Counter(c).most_common(1)[0][0] if c else None
                               for c in by_pos],
    }


# ────────────────────────────────────────────────────────────────────── build

def build() -> dict:
    works = json.loads(WORKS.read_text())
    rows_by_id = {r["row_id"]: r for r in works["rows"]}
    fx = fixtures_dir()
    lib = library_root()

    out_rows = []
    per_row_meta = []

    for row in works["rows"]:
        rid = row["row_id"]
        tj = fx / f"{rid}.{TAG.lstrip('.')}.omr.json"
        if not tj.is_file():
            tj = fx / f"{rid}.{TAG}.omr.json"
        if not tj.is_file():
            cands = list(fx.glob(f"{rid}*{TAG}.omr.json"))
            if not cands:
                per_row_meta.append({"row_id": rid, "skipped": "no transcription"})
                continue
            tj = cands[0]
        d = json.loads(tj.read_text())

        truth_staves, truth_prov = _resolve_staff_truth(row, rows_by_id)

        # reference-derived clef/key (scoring key only)
        ref_path = lib / row["reference"]["catalog_path"]
        ref_facts = reference_part_facts(ref_path) if ref_path.is_file() else []

        ctx = d.get("contextual") or {}
        group_by_slot = {r["slot"]: r.get("group") for r in (ctx.get("reference") or [])}
        layout_inst_by_slot = {r["slot"]: r.get("instrument")
                               for r in (ctx.get("reference") or [])}

        pages = d.get("pages", [])
        n_sys_total = sum(len(p.get("systems", [])) for p in pages)
        prev_system_slots = None

        # page modal fifths: the mode over every staff that READ a signature.
        all_fifths = []
        for p in pages:
            for sy in p.get("systems", []):
                for st in sy.get("staves", []):
                    f = signed_fifths(st.get("key_signature"))
                    if f is not None and st.get("key_signature_read"):
                        all_fifths.append(f)
        page_modal = Counter(all_fifths).most_common(1)[0][0] if all_fifths else None

        for p in pages:
            for sy in p.get("systems", []):
                staves = sy.get("staves", [])
                order = score_order_prediction(len(staves))
                sys_slots = []
                for i, st in enumerate(staves):
                    above = staves[i - 1] if i > 0 else None
                    below = staves[i + 1] if i + 1 < len(staves) else None
                    dets = staff_detections(st)
                    env = s4_envelope(dets)
                    slot = st.get("slot_index")
                    sys_slots.append(slot)
                    fifths = signed_fifths(st.get("key_signature"))
                    implied = (None if (fifths is None or page_modal is None)
                               else fifths - page_modal)
                    grp = group_by_slot.get(slot)

                    # truth join
                    tr = None
                    if truth_staves:
                        if truth_prov.startswith("works.json:systems_as_printed"):
                            si = sy.get("system_index", 0)
                            block = (truth_staves[si]
                                     if si < len(truth_staves) else None)
                            tr = block[i] if block and i < len(block) else None
                        elif i < len(truth_staves):
                            tr = truth_staves[i]

                    truth_clef = tr.get("clef") if tr else None
                    truth_key = tr.get("key") if tr else None
                    parts = (tr or {}).get("parts")
                    if truth_clef is None and parts and ref_facts:
                        pf = [ref_facts[k] for k in parts if k < len(ref_facts)]
                        if pf:
                            truth_clef = clef_name_from_sign(pf[0]["clef_sign_line"])
                    if truth_key is None and parts and ref_facts:
                        pf = [ref_facts[k] for k in parts if k < len(ref_facts)]
                        if pf:
                            truth_key = pf[0]["written_fifths"]

                    out_rows.append({
                        "row_id": rid,
                        "publisher": row["edition"].get("publisher_as_catalogued", ""),
                        "page": p.get("page_index"),
                        "system": sy.get("system_index"),
                        "staff_index": i,
                        "n_staves_in_system": len(staves),
                        "n_systems_on_page": len(p.get("systems", [])),

                        # S1 — margin label (the pipeline's own reader ladder)
                        "s1_instrument": st.get("instrument"),
                        "s1_family": st.get("instrument_family"),
                        "s1_source": st.get("instrument_source"),

                        # S2 — clef
                        "s2_clef": st.get("clef"),
                        "s2_source": st.get("clef_source"),
                        "s2_defaulted": st.get("clef_source") in (None, "default",
                                                                  "positional_default",
                                                                  "positional"),

                        # S3 — printed key vs the page's modal key
                        "s3_staff_fifths": fifths,
                        "s3_read": bool(st.get("key_signature_read")),
                        "s3_key_source": st.get("key_signature_source"),
                        "s3_page_modal_fifths": page_modal,
                        "s3_implied_offset": implied,
                        "s3_candidates": (instruments_with_offset(implied)
                                          if implied is not None else []),

                        # S4 — observed pitch envelope
                        "s4_pitch_lo": env["lo"], "s4_pitch_hi": env["hi"],
                        "s4_n_notes": env["n"], "s4_median": env["median"],
                        "s4_bimodal_gap": env["bimodal_gap"],
                        "s4_range_compatible": s4_range_compatible(env["lo"], env["hi"]),

                        # S5 — vertical position / score order (label-free prior)
                        "s5_position_index": i,
                        "s5_prediction": (order["per_position_modal"][i]
                                          if i < len(order["per_position_modal"]) else None),
                        "s5_prediction_set": (order["per_position"][i]
                                              if i < len(order["per_position"]) else []),
                        "s5_exact_layouts": order["exact_layouts"],

                        # S6 — continuity
                        "s6_slot_index": slot,
                        "s6_layout_instrument": layout_inst_by_slot.get(slot),

                        # S7 — intra-staff texture (multiplicity only)
                        **{f"s7_{k}": v for k, v in s7_texture(st).items()},

                        # S8 — bracket / brace grouping
                        "s8_group_index": grp,
                        "s8_brace_detections": s8_brace(st),

                        # S9 — placement
                        **{f"s9_{k}": v for k, v in s9_placement(st, above, below).items()},

                        # TRUTH (scoring key; never an input above)
                        "TRUTH_available": tr is not None,
                        "TRUTH_name": (tr or {}).get("name"),
                        "TRUTH_parts": parts,
                        "TRUTH_n_parts": len(parts) if parts else None,
                        "TRUTH_clef": truth_clef,
                        "TRUTH_key": truth_key,
                        "TRUTH_clef_source": (
                            "hand-read" if (tr or {}).get("clef") is not None
                            else ("reference-derived" if truth_clef is not None else None)),
                        "TRUTH_key_source": (
                            "hand-read" if (tr or {}).get("key") is not None
                            else ("reference-derived" if truth_key is not None else None)),
                        "TRUTH_source": truth_prov,
                        # CEILING arm — the hand-read printed string. Labelled so
                        # it cannot be mistaken for a signal.
                        "CEILING_hand_label": (tr or {}).get("name"),
                    })

                # group sizes, block position
                prev_system_slots = sys_slots

        per_row_meta.append({
            "row_id": rid,
            "transcription": str(tj),
            "weights": d.get("weights"),
            "n_systems": n_sys_total,
            "truth_provenance": truth_prov,
            "n_truth_staves": len(truth_staves) if truth_staves else 0,
            "n_reference_parts": len(ref_facts),
            "page_modal_fifths": page_modal,
            "contextual_available": ctx.get("available"),
            "label_tiers": ctx.get("label_tiers"),
            "layout": ctx.get("layout"),
        })

    # fill in group sizes now that every row is present
    by_group = defaultdict(list)
    for r in out_rows:
        by_group[(r["row_id"], r["page"], r["system"], r["s8_group_index"])].append(r)
    for key, members in by_group.items():
        for j, r in enumerate(sorted(members, key=lambda x: x["staff_index"])):
            r["s8_group_size"] = len(members)
            r["s8_block_position"] = j
    # continuity: is this slot present on the previous system of the same page?
    seen_slots = defaultdict(set)
    for r in sorted(out_rows, key=lambda x: (x["row_id"], x["page"], x["system"],
                                             x["staff_index"])):
        k = (r["row_id"], r["page"])
        r["s6_continuous_with_prev"] = (
            None if r["system"] in (0, None)
            else r["s6_slot_index"] in seen_slots[(k, r["system"] - 1)])
        seen_slots[(k, r["system"])].add(r["s6_slot_index"])

    return {"meta": {"tag": TAG, "rows": per_row_meta,
                     "n_evidence_rows": len(out_rows)},
            "evidence": out_rows}


def validate_reference_truth(doc: dict) -> dict:
    """The one row that hand-reads BOTH clef and key is the control that says
    whether reference-derived clef/key can stand in for a hand read elsewhere."""
    agree_c = dis_c = agree_k = dis_k = 0
    detail = []
    works = json.loads(WORKS.read_text())
    rows_by_id = {r["row_id"]: r for r in works["rows"]}
    lib = library_root()
    for row in works["rows"]:
        st, prov = _resolve_staff_truth(row, rows_by_id)
        if not st or not isinstance(st, list) or not st or "clef" not in st[0]:
            continue
        ref = reference_part_facts(lib / row["reference"]["catalog_path"])
        for e in st:
            parts = e.get("parts") or []
            pf = [ref[k] for k in parts if k < len(ref)]
            if not pf:
                continue
            rc = clef_name_from_sign(pf[0]["clef_sign_line"])
            rk = pf[0]["written_fifths"]
            if e.get("clef") is not None:
                (agree_c, dis_c) = ((agree_c + 1, dis_c) if rc == e["clef"]
                                    else (agree_c, dis_c + 1))
            if e.get("key") is not None:
                (agree_k, dis_k) = ((agree_k + 1, dis_k) if rk == e["key"]
                                    else (agree_k, dis_k + 1))
            detail.append({"row": row["row_id"], "name": e.get("name"),
                           "hand_clef": e.get("clef"), "ref_clef": rc,
                           "hand_key": e.get("key"), "ref_key": rk})
    return {"clef_agree": agree_c, "clef_disagree": dis_c,
            "key_agree": agree_k, "key_disagree": dis_k, "detail": detail}


def main() -> int:
    doc = build()
    doc["reference_truth_validation"] = validate_reference_truth(doc)
    (HERE / "evidence.json").write_text(json.dumps(doc, indent=1) + "\n")

    rows = doc["evidence"]
    if rows:
        keys = sorted({k for r in rows for k in r})
        with (HERE / "evidence.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                            for k, v in r.items()})

    print(f"evidence rows: {len(rows)}")
    v = doc["reference_truth_validation"]
    print(f"reference-vs-hand truth control: "
          f"clef {v['clef_agree']}/{v['clef_agree'] + v['clef_disagree']} agree, "
          f"key {v['key_agree']}/{v['key_agree'] + v['key_disagree']} agree")
    print(f"rows with truth: {sum(1 for r in rows if r['TRUTH_available'])}")
    for m in doc["meta"]["rows"]:
        print(f"  {m['row_id']:38s} truth={m['n_truth_staves']:3d} "
              f"modal_fifths={m['page_modal_fifths']} {m['truth_provenance']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
