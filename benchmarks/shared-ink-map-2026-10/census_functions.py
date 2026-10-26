"""ROADMAP 2.194 -- static census: which functions read the raster (ink) themselves, in which module, measuring what.

Walks tools/omr/*.py, tools/omr/staged/*.py, tools/omr/staged/adjudicators/*.py. A function "touches ink" when its body names a
raster (`binary`, `erased`, `gray`, `img[`, `image`), an ink helper (`_ink_runs`, `_ink_components`, `_best_overlap_runs`,
`ink_runs`), or OpenCV / numpy pixel ops (`cv2.`, `connectedComponents`, `== 0`, `== 255`, `.mean(axis`). It then tags what the
function measures by keywords (vertical run -> stem/barline; horizontal run -> beam/line; hole/fill -> head; component; staff line;
thickness). Tags are heuristic (keyword), counts are exact. Read-only; prints a table and writes results/functions.json.
"""
from __future__ import annotations
import ast, collections, glob, json, os, re, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GLOBS = ["tools/omr/*.py", "tools/omr/staged/*.py", "tools/omr/staged/adjudicators/*.py"]
RASTER = re.compile(r"\b(binary|erased|gray|img|image|raster|mask|crop)\b")
HELPERS = re.compile(r"\b(_ink_runs|_ink_components|_best_overlap_runs|ink_runs|_cell_raw_ink|_local_staff_lines|line_rows_across_stem|line_band_beside|_hook_line_rows|_enclosed_holes|local_line_thickness|_median_filter_1d)\b")
PIXEL = re.compile(r"(cv2\.|connectedComponents|== 0\b|== 255\b|\.mean\(axis|np\.where|\.sum\(axis|findContours|morphologyEx|\[y0:y1|\[:, x0:x1|\[r0:r1)")
TAGS = {
    "stem/vertical": re.compile(r"stem|vertical|column|col_|barline", re.I),
    "beam/horizontal": re.compile(r"beam|horizontal|row_run|hook|flag", re.I),
    "head fill/hole": re.compile(r"hollow|fill|hole|oval|slit|white|notehead|head_", re.I),
    "component": re.compile(r"component|blob|comps|label", re.I),
    "staff line local": re.compile(r"staff_line|line_ys|line_rows|local_line|line_band|_lines\b|spacing", re.I),
    "thickness": re.compile(r"thick|width", re.I),
    "rest": re.compile(r"\brest", re.I),
    "arc/hairpin": re.compile(r"\barc|slur|tie|hairpin|wedge", re.I),
    "dot/wedge": re.compile(r"\bdot|wedge|staccat", re.I),
    "letter/text": re.compile(r"letter|word|text|ocr|tesseract", re.I),
    "ledger": re.compile(r"ledger|rung", re.I),
    "accidental": re.compile(r"accidental|flat|sharp|natural", re.I),
    "clef/key/meter": re.compile(r"clef|key_|meter|timesig", re.I),
}

def funcs(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    lines = src.splitlines()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = "\n".join(lines[node.lineno - 1: node.end_lineno])
            out.append((node.name, node.lineno, node.end_lineno - node.lineno + 1, body))
    return out

def main():
    rows = []
    per_mod = collections.Counter(); per_mod_all = collections.Counter(); per_tag = collections.Counter()
    helper_calls = collections.Counter()
    for g in GLOBS:
        for path in sorted(glob.glob(os.path.join(REPO, g))):
            mod = os.path.relpath(path, REPO)
            for name, ln, n, body in funcs(path):
                per_mod_all[mod] += 1
                r = len(RASTER.findall(body)); h = len(HELPERS.findall(body)); p = len(PIXEL.findall(body))
                for hc in HELPERS.findall(body): helper_calls[hc] += 1
                if (r and p) or h or p >= 2:
                    tags = [t for t, rx in TAGS.items() if rx.search(body)]
                    rows.append({"module": mod, "function": name, "line": ln, "lines": n, "raster_refs": r, "helper_calls": h,
                                 "pixel_ops": p, "tags": tags})
                    per_mod[mod] += 1
                    for t in tags: per_tag[t] += 1
    rows.sort(key=lambda d: (-(d["raster_refs"] + d["helper_calls"] + d["pixel_ops"])))
    total_funcs = sum(per_mod_all.values())
    print(f"{len(rows)} functions touch the raster or an ink helper, of {total_funcs} functions in {len(per_mod_all)} modules")
    print("\nby module (ink-touching / all):")
    for m, c in per_mod.most_common():
        print(f"  {c:4d} / {per_mod_all[m]:4d}  {m}")
    print("\nby what they measure (keyword tag; a function may carry several):")
    for t, c in per_tag.most_common(): print(f"  {c:4d}  {t}")
    print("\nhelper calls (static call sites):", dict(helper_calls))
    print("\nlocal staff-line readers (functions that both touch ink and name staff lines):")
    for d in rows:
        if "staff line local" in d["tags"]:
            print(f"  {d['module']}:{d['line']} {d['function']}")
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    json.dump({"functions": rows, "per_module": per_mod, "per_module_all": per_mod_all, "per_tag": per_tag,
               "total_functions": total_funcs}, open(os.path.join(os.path.dirname(__file__), "results", "functions.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
