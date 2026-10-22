"""Which held works could exercise the movement-span code at all?

A span boundary needs ONE document containing several movements whose printed
lineup GROWS. So the candidate set is the intersection of three properties, and
each is read from a different half of the library:

    1. an EDITION pdf long enough to be a whole work (many pages);
    2. several movements' REFERENCE encodings, so the per-movement part counts
       can be compared;
    3. a later movement holding MORE parts than an earlier one.

⚠️ (3) is an ENCODING-derived fact and is used here to SELECT candidates only.
It is never measurement truth: an encoding's part count is a property of the
encoding (a condensed `Flauti` staff is 1 part in one edition and 2 in
another), and what the span code reads is STAVES ON THE PAGE.
"""
from __future__ import annotations

import collections
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.library.score_library import library_root  # noqa: E402
LIB = library_root()


def read_mxl(path: Path) -> bytes | None:
    if path.suffix == ".mxl":
        try:
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist()
                         if n.endswith(".xml") and not n.startswith("META-INF")]
                # container.xml names the rootfile; fall back to the first xml
                if "META-INF/container.xml" in z.namelist():
                    cx = ET.fromstring(z.read("META-INF/container.xml"))
                    rf = cx.find(".//{*}rootfile")
                    if rf is not None and rf.get("full-path") in z.namelist():
                        return z.read(rf.get("full-path"))
                return z.read(names[0]) if names else None
        except Exception:
            return None
    try:
        return path.read_bytes()
    except Exception:
        return None


def part_count(path: Path) -> tuple[int, list[str]] | None:
    blob = read_mxl(path)
    if not blob:
        return None
    try:
        root = ET.fromstring(blob)
    except Exception:
        return None
    parts = root.findall(".//{*}part-list/{*}score-part")
    names = []
    for p in parts:
        n = p.find("{*}part-name")
        names.append((n.text or "").strip() if n is not None else "")
    return len(parts), names


MVT_RE = re.compile(r"--mvt(\d+)")


def main() -> int:
    cat = json.load(open(ROOT / "data/score-library/catalog.json"))
    by_work = collections.defaultdict(lambda: {"ed": [], "ref": []})
    for e in cat["entries"]:
        by_work[e.get("work_id")]["ed" if e["kind"] == "edition"
                                  else "ref"].append(e)

    rows = []
    for work, v in by_work.items():
        if not v["ed"]:
            continue
        # movement-numbered references only; a work whose refs are unnumbered
        # cannot be ordered and cannot answer "does a LATER movement grow".
        mvts: dict[int, list[Path]] = collections.defaultdict(list)
        for r in v["ref"]:
            m = MVT_RE.search(Path(r["path"]).name)
            if m:
                mvts[int(m.group(1))].append(LIB / r["path"])
        if len(mvts) < 2:
            continue
        counts: dict[int, int] = {}
        names: dict[int, list[str]] = {}
        for n, paths in sorted(mvts.items()):
            for p in paths:
                got = part_count(p)
                if got:
                    counts[n], names[n] = got
                    break
        if len(counts) < 2:
            continue
        order = sorted(counts)
        grew = any(counts[b] > max(counts[a] for a in order if a < b)
                   for b in order[1:])
        maxed = max(e.get("pages") or 0 for e in v["ed"])
        rows.append({
            "work_id": work,
            "movement_parts": {str(k): counts[k] for k in order},
            "grows": grew,
            "max_edition_pages": maxed,
            "editions": [{"path": e["path"], "pages": e.get("pages"),
                          "publisher": e.get("publisher")} for e in v["ed"]],
            "part_names": {str(k): names[k] for k in order},
        })

    rows.sort(key=lambda r: (not r["grows"], -r["max_edition_pages"]))
    out = ROOT / "benchmarks/omr-span-reach-2026-09/out/inventory.json"
    json.dump(rows, open(out, "w"), indent=1, sort_keys=True)
    grow = [r for r in rows if r["grows"]]
    print(f"{len(rows)} works with an edition + >=2 numbered movements; "
          f"{len(grow)} show a LATER movement with MORE parts")
    for r in rows:
        flag = "GROWS" if r["grows"] else "     "
        print(f"{flag} {r['work_id']:48s} pages<={r['max_edition_pages']:4d} "
              f"{r['movement_parts']}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
