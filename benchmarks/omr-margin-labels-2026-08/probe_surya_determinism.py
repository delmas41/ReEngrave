"""Is Surya a fixed function of its input — alone, and under concurrent load?

WHY THIS EXISTS. Two careful readings of the same margin crop (Beethoven 5
p.48, staff 10) came back different and each internally consistent: `Tr. Teq.`
from a reader that was driving full ten-page benchmarks at the time, `Tr. Ten.`
from single-page reads against an otherwise idle server. The one variable that
differed was LOAD. Surya spawns llama.cpp with `--parallel 8`, so requests share
a batch, and a decode that depends on what else is in the batch is not a
function of its input at all — which would mean a benchmark that reads Surya in
isolation cannot price what Surya does inside a benchmark.

METHOD. Freeze the input completely: build the margin crops once, write the
worker's own JSON job to disk, and from then on replay THOSE BYTES. Anything
that changes afterwards is the reader, not the pipeline.

    build   render the page, detect staves, cache the job payload
    serial  N replays back to back, one at a time
    load    K replays at once, in K separate processes

The comparison is on the worker's raw output — `raw_lines` as well as the
assigned labels — because a mapping change and an OCR change are
indistinguishable in the label dict alone.

    python3 benchmarks/omr-margin-labels-2026-08/probe_surya_determinism.py \
        --page beet5-p48 --serial 6 --load 4

Both phases run against whatever server state the machine is in; `--stop-first`
kills a resident one so the serial phase starts cold, which is the state a
one-off read is usually taken in.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# The pages whose margins this project has hand-checked. `pdf` is repo-relative
# or ~-relative exactly as the clef truth files record it.
PAGES = {
    "beet5-p48": ("~/Documents/Gradus-Assets/Scores/Scores For Gradus/"
                  "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 48, 600),
    "beet9-p30": ("tools/omr/training/data/imslp/beethoven-symphony-9/"
                  "pdfs/imslp-516488/score.pdf", 30, 300),
    "beet9-p60": ("tools/omr/training/data/imslp/beethoven-symphony-9/"
                  "pdfs/imslp-516488/score.pdf", 60, 300),
}


def resolve_pdf(spec: str) -> Path:
    p = Path(spec).expanduser()
    return p if p.is_absolute() else REPO / p


def build_job(page_id: str, cache: Path) -> Path:
    """Render + detect once, and write the worker's JSON job for later replay."""
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels_vision import build_margin_crop

    spec, page_index, dpi = PAGES[page_id]
    pdf = resolve_pdf(spec)
    if not pdf.exists():
        raise SystemExit(f"no PDF at {pdf}")
    pws = detect_staves(render_page(pdf, page_index, dpi=dpi))

    by_system: dict[int, list] = {}
    for staff in sorted(pws.staves, key=lambda s: s.top_y):
        by_system.setdefault(staff.system_index, []).append(staff)

    systems = []
    for _idx, staves in sorted(by_system.items()):
        crop = build_margin_crop(pws, staves)
        if crop is None:
            continue
        systems.append({
            "png_b64": base64.standard_b64encode(crop.png).decode("ascii"),
            "staff_indices": list(crop.staff_indices),
            "tick_ys": list(crop.tick_ys),
            "gutter_px": crop.gutter_px,
        })
    cache.write_text(json.dumps({"systems": systems}))
    print(f"cached {len(systems)} system crop(s) from {page_id} -> {cache}")
    return cache


def _worker_python() -> str:
    from tools.omr.staff_labels_surya import interpreter
    return str(interpreter())


def one_read(job_path: str, keep_alive: bool) -> dict:
    """One replay of the cached job, straight through the surya worker."""
    import os

    env = dict(os.environ)
    env["SURYA_INFERENCE_KEEP_ALIVE"] = "true" if keep_alive else "false"
    t0 = time.time()
    proc = subprocess.run(
        [_worker_python(), str(REPO / "tools" / "omr" / "_surya_worker.py")],
        input=Path(job_path).read_text(), capture_output=True, text=True,
        env=env, timeout=1800,
    )
    dt = time.time() - t0
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": proc.stderr.strip()[-800:], "seconds": dt}
    payload["seconds"] = dt
    return payload


def signature(payload: dict) -> str:
    """A canonical string for one read — labels AND the raw lines behind them."""
    if "error" in payload:
        return f"ERROR:{payload['error'][:120]}"
    parts = []
    for sysd in payload.get("systems", []):
        parts.append(json.dumps({"labels": sysd.get("labels", {}),
                                 "raw": sysd.get("raw_lines", [])},
                                sort_keys=True))
    return "\n".join(parts)


def report(name: str, payloads: list[dict]) -> Counter:
    sigs = Counter(signature(p) for p in payloads)
    times = [p.get("seconds", 0.0) for p in payloads]
    print(f"\n{name}: {len(payloads)} reads, "
          f"{len(sigs)} distinct answer(s), "
          f"{min(times):.1f}-{max(times):.1f}s each")
    for i, (sig, n) in enumerate(sigs.most_common()):
        head = sig.splitlines()[0] if sig else "(empty)"
        print(f"  variant {i}  x{n}  {head[:200]}")
    return sigs


def diff_variants(sigs: Counter) -> None:
    """Where two answers differ, name the field — not just the count."""
    if len(sigs) < 2:
        return
    variants = [json.loads(s.splitlines()[0]) for s in sigs
                if not s.startswith("ERROR")]
    if len(variants) < 2:
        return
    base = variants[0]
    for other in variants[1:]:
        for key in ("labels", "raw"):
            a, b = base.get(key), other.get(key)
            if a == b:
                continue
            if key == "labels":
                for staff in sorted(set(a) | set(b), key=int):
                    if a.get(staff) != b.get(staff):
                        print(f"    staff {staff}: {a.get(staff)!r} vs {b.get(staff)!r}")
            else:
                print(f"    raw lines differ: {len(a)} vs {len(b)} blocks")
                for x, y in zip(a, b):
                    if x != y:
                        print(f"      {x!r} vs {y!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="beet5-p48", choices=sorted(PAGES))
    ap.add_argument("--serial", type=int, default=5, help="back-to-back reads")
    ap.add_argument("--load", type=int, default=4, help="simultaneous reads")
    ap.add_argument("--keep-alive", action="store_true", default=True)
    ap.add_argument("--no-keep-alive", dest="keep_alive", action="store_false")
    ap.add_argument("--stop-first", action="store_true",
                    help="kill a resident llama.cpp server before starting")
    ap.add_argument("--cache", type=Path,
                    help="job payload path (built if absent)")
    args = ap.parse_args()

    cache = args.cache or (Path(__file__).parent / f".job-{args.page}.json")
    if not cache.exists():
        build_job(args.page, cache)
    else:
        print(f"reusing cached job {cache}")

    if args.stop_first:
        from tools.omr.staff_labels_surya import stop_server
        print("resident server stopped" if stop_server() else "no resident server")

    serial = [one_read(str(cache), args.keep_alive) for _ in range(args.serial)]
    sigs = report(f"SERIAL (keep_alive={args.keep_alive})", serial)
    diff_variants(sigs)

    if args.load > 1:
        with ProcessPoolExecutor(max_workers=args.load) as pool:
            loaded = list(pool.map(one_read, [str(cache)] * args.load,
                                   [args.keep_alive] * args.load))
        lsigs = report(f"CONCURRENT x{args.load}", loaded)
        diff_variants(lsigs)

        combined = Counter()
        combined.update(signature(p) for p in serial)
        combined.update(signature(p) for p in loaded)
        print(f"\nACROSS BOTH PHASES: {len(combined)} distinct answer(s) "
              f"over {len(serial) + len(loaded)} reads")
        diff_variants(combined)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
