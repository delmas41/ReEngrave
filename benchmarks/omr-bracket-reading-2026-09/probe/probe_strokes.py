"""Dump the left-edge strokes of every system on the given pages.

The first question the commission asks: what is actually THERE?  Is a bracket
present, how thick, how tall, where exactly, and can it be told from the
systemic barline standing beside it?

    probe_strokes.py PDF --pages=38 [--dpi 600] [--crops DIR]
    probe_strokes.py --corpus scan --pages-per-edition 6
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2                                                  # noqa: E402
from tools.omr.preprocessing import render_page             # noqa: E402
from tools.omr.staff_detector import detect_staves          # noqa: E402
from left_edge import strokes_at_left_edge, covered_staves, stroke_dict  # noqa: E402

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
             "omr-scan-e2e-2026-09/works.json")


def scan_editions() -> list[tuple[str, Path]]:
    rows = json.loads(WORKS.read_text())["rows"]
    seen: dict[str, Path] = {}
    for r in rows:
        cp = r["edition"]["catalog_path"]
        seen.setdefault(cp.split("/")[1], LIB / cp)
    return sorted(seen.items())


def parse_pages(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def page_report(pdf: str, page_index: int, dpi: int, crops: Path | None,
                tag: str) -> dict:
    pi = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    by_system: dict[int, list] = {}
    for s in staves:
        by_system.setdefault(s.system_index, []).append(s)

    systems = []
    for sys_idx in sorted(by_system):
        members = by_system[sys_idx]
        spacing = statistics.median([s.line_spacing_px for s in members]) or 1.0
        strokes, geom = strokes_at_left_edge(pi.binary, members)
        recs = []
        for st in strokes:
            d = stroke_dict(st)
            d["covers"] = covered_staves(st, members)
            recs.append(d)
        systems.append({
            "system_index": sys_idx,
            "n_staves": len(members),
            "spacing": round(spacing, 2),
            "geom": {k: (round(v, 1) if isinstance(v, float) else v)
                     for k, v in geom.items()},
            "strokes": recs,
        })
        if crops is not None:
            crops.mkdir(parents=True, exist_ok=True)
            img = pi.binary[geom["y0"]:geom["y1"], geom["x0"]:geom["x1"]]
            cv2.imwrite(str(crops / f"{tag}-p{page_index}-s{sys_idx}.png"), img)
    return {"page": page_index, "n_staves": len(staves), "systems": systems}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--corpus", choices=["scan"], default=None)
    ap.add_argument("--pages", default=None)
    ap.add_argument("--pages-per-edition", type=int, default=6)
    ap.add_argument("--first-page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--crops", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    crops = Path(args.crops) if args.crops else None
    targets: list[tuple[str, Path, list[int]]] = []
    if args.corpus == "scan":
        for tag, pdf in scan_editions():
            pages = (parse_pages(args.pages) if args.pages else
                     list(range(args.first_page,
                                args.first_page + args.pages_per_edition)))
            targets.append((tag, pdf, pages))
    for p in args.pdfs:
        targets.append((Path(p).stem[:20], Path(p),
                        parse_pages(args.pages) if args.pages else [0]))

    report = []
    for tag, pdf, pages in targets:
        for pg in pages:
            try:
                r = page_report(str(pdf), pg, args.dpi, crops, tag)
            except Exception as exc:                      # noqa: BLE001
                print(f"{tag} p{pg}: FAILED {type(exc).__name__}: {exc}",
                      flush=True)
                continue
            r["tag"] = tag
            r["pdf"] = str(pdf)
            report.append(r)
            for sy in r["systems"]:
                print(f"{tag} p{pg} sys{sy['system_index']} "
                      f"{sy['n_staves']} staves  spacing={sy['spacing']}",
                      flush=True)
                for st in sy["strokes"]:
                    print(f"    x={st['x_left']}-{st['x_right']} "
                          f"thick={st['thickness_px']}px/"
                          f"{st['thickness_spacings']}sp  "
                          f"off={st['offset_spacings']}sp  "
                          f"y={st['y_top']}-{st['y_bot']} "
                          f"h={st['height_spacings']}sp "
                          f"straight={st['straightness']}  "
                          f"covers={st['covers']}", flush=True)

    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"\nwrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
