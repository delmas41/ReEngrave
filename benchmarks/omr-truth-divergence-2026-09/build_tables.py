"""Build the divergence table and the per-staff readings, as Markdown.

Two outputs, because they answer two different questions:

    DIVERGENCE.md   can the MXL serve as ground truth for this row, and if not,
                    why not — the partition Sean asked for
    READINGS.md     what the pipeline actually read on every staff, for a human
                    to look at

⚠️ Nothing here scores anything. A divergence is not an error until it is
attributed, and the attribution is what the tables carry.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from divergence import (attribute, detected, hand_read_staves,  # noqa: E402
                        raw_staff_span)
from probe_encoded_parts import part_list, staves_declared  # noqa: E402

SCAN_WORKS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"


def _library_root():
    from tools.library.score_library import library_root
    return library_root()


def _engraved_fixtures() -> Path:
    local = REPO / "benchmarks/omr-orchestral-e2e/fixtures"
    if any(local.glob("*.musicxml")):
        return local
    return _library_root().parent / "benchmarks/omr-orchestral-e2e/fixtures"


def collect() -> dict:
    doc = json.loads(SCAN_WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    lib = _library_root()

    out = {"scan": [], "engraved": []}

    ref_cache: dict[str, tuple[int, int]] = {}
    for r in rows:
        cp = r["reference"]["catalog_path"]
        if cp not in ref_cache:
            p = lib / cp
            pl = part_list(p)
            sd = staves_declared(p)
            ref_cache[cp] = (len(pl), sum(sd.get(x["id"], 1) for x in pl))
        n_parts, n_decl = ref_cache[cp]

        lineup = hand_read_staves(r, by_id)
        det = detected(r["row_id"], "scan")
        rec = {
            "row_id": r["row_id"],
            "label": r.get("label", ""),
            "reference": cp.split("/")[-1],
            "encoded_parts": n_parts,
            "encoded_staves": n_decl,
            "works_json_n_parts": r["reference"]["n_parts"],
            "page_n_staves": r["page"]["n_staves"],
            "page_n_systems": r["page"]["n_systems"],
            "hand_lineup": len(lineup) if lineup else None,
            "hand_has_parts": bool(lineup and any("parts" in s for s in lineup)),
            "detected": det and {k: det[k] for k in
                                 ("n_systems", "per_system", "total")},
            "raw_span": raw_staff_span(det["doc"]) if det else None,
        }
        rec["attribution"] = attribute(
            n_parts, lineup if rec["hand_has_parts"] else None,
            rec["page_n_staves"])
        out["scan"].append(rec)

    fixtures = _engraved_fixtures()
    from tools.omr.accuracy_record import BENCHMARK_WORKS
    for w in BENCHMARK_WORKS:
        t = fixtures / f"{w}.musicxml"
        n_parts = n_decl = None
        if t.exists():
            pl = part_list(t)
            sd = staves_declared(t)
            n_parts = len(pl)
            n_decl = sum(sd.get(x["id"], 1) for x in pl)
        det = detected(w, "engraved")
        out["engraved"].append({
            "row_id": w,
            "encoded_parts": n_parts,
            "encoded_staves": n_decl,
            "detected": det and {k: det[k] for k in
                                 ("n_systems", "per_system", "total")},
            "raw_span": raw_staff_span(det["doc"]) if det else None,
        })
    return out


def readings(corpus: str, row_id: str) -> list[dict] | None:
    p = HERE / "readings" / f"{corpus}--{row_id}.omr.json"
    if not p.exists():
        return None
    doc = json.loads(p.read_text())
    out = []
    for pg in doc["pages"]:
        for si, sy in enumerate(pg["systems"]):
            for st in sy["staves"]:
                ks = st.get("key_signature") or {}
                sharps, flats = ks.get("sharps", 0), ks.get("flats", 0)
                out.append({
                    "system": si,
                    "staff_index": st.get("staff_index"),
                    "slot": st.get("slot_index"),
                    "instrument": st.get("instrument"),
                    "source": st.get("instrument_source"),
                    "clef": st.get("clef"),
                    "clef_source": st.get("clef_source"),
                    "key": (f"{sharps}#" if sharps else
                            (f"{flats}b" if flats else "0")),
                    "time": (st.get("time_signature") or {}).get("raw"),
                    "n_measures": st.get("n_measures"),
                })
    return out


def roster_of(corpus: str, row_id: str) -> dict | None:
    p = HERE / "readings" / f"{corpus}--{row_id}.omr.json"
    if not p.exists():
        return None
    doc = json.loads(p.read_text())
    return (doc.get("contextual") or {}).get("roster")


def render(data: dict) -> str:
    """The divergence table, as Markdown on stdout.

    Printed rather than written to a file: the finding belongs in the report the
    session returns, and a generated `.md` beside it is a second copy that goes
    stale the way every restated figure in this project has.
    """
    lines: list[str] = []
    lines.append("## Scan corpus (20 rows) — the corpus where the question has "
                 "content\n")
    lines.append("| row | enc parts | enc staves | printed (hand) | detected "
                 "| raw | condensed | tacet | residual |")
    lines.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for r in data["scan"]:
        a = r["attribution"]
        det = r["detected"]
        d = "/".join(str(x) for x in det["per_system"]) if det else "—"
        hand = r["hand_lineup"] if r["hand_has_parts"] else "—"
        lines.append(
            f"| `{r['row_id']}` | {r['encoded_parts']} | {r['encoded_staves']} "
            f"| {hand} | {d} | {r['raw_span'] or '—'} "
            f"| {a.get('condensation', '—')} | {a.get('tacet_suppressed', '—')} "
            f"| {a.get('residual', '—')} |")

    lines.append("\n## Engraved corpus (11 works) — parts==staves by "
                 "construction\n")
    lines.append("| work | enc parts | enc staves | detected | raw |")
    lines.append("|---|--:|--:|--:|--:|")
    for r in data["engraved"]:
        det = r["detected"]
        d = "/".join(str(x) for x in det["per_system"]) if det else "—"
        lines.append(f"| `{r['row_id']}` | {r['encoded_parts']} "
                     f"| {r['encoded_staves']} | {d} | {r['raw_span'] or '—'} |")
    return "\n".join(lines)


if __name__ == "__main__":
    data = collect()
    (HERE / "divergence.json").write_text(json.dumps(data, indent=1))
    n_det = sum(1 for r in data["scan"] + data["engraved"] if r["detected"])
    print(f"scan rows {len(data['scan'])}, engraved {len(data['engraved'])}, "
          f"with a transcription: {n_det}\n")
    print(render(data))
