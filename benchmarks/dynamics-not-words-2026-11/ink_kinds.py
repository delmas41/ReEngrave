"""ROADMAP 2.296 measure (b): `claim_readout ink` (and the comparison against Sean's page-pass labels) with a dynamic claim named a dynamic.

    python3 benchmarks/dynamics-not-words-2026-11/ink_kinds.py REC PAGES [--by-category] [--compare HT_DIR --page 0] [--out DIR]
    python3 benchmarks/dynamics-not-words-2026-11/ink_kinds.py judged REC [--against BASE.json] [--by-category]

Without `--by-category` the tool runs exactly as it stands (a dynamic claim is a `word`: the register's owner name). With it, `kind_patch.apply()` names a
claim row owner `word` + category `dynamic` a dynamic IN MEMORY (see `kind_patch.py`); `claim_readout.py` / `judged_claims.py` are not edited.
"""
import argparse
import os
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "judged":
        import kind_patch
        rest = sys.argv[2:]
        if "--by-category" in rest:
            rest.remove("--by-category")
            kind_patch.apply()
        from tools.omr.staged import judged_claims as JC
        sys.exit(JC.main(rest))
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("pages")
    ap.add_argument("--by-category", action="store_true")
    ap.add_argument("--compare", default=None, help="HT_DIR for sean_labels_compare (a dir holding tools/omr/hand_truth + data/hand-truth)")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from tools.omr.staged import claim_readout as CR
    if a.by_category:
        import kind_patch
        kind_patch.apply()
    pages = [int(x) for x in a.pages.split(",")]
    if a.compare:
        sys.argv = ["sean_labels_compare.py", "--handtruth", a.compare, "--slice", str(CR.resolve_source(a.rec)), "--page", str(a.page)] \
            + (["--out", a.out] if a.out else [])
        runpy.run_path(str(ROOT / "benchmarks" / "one-ink-number-2026-11" / "sean_labels_compare.py"), run_name="__main__")
        return
    CR.run_ink(a.rec, pages, out=pathlib.Path(a.out) if a.out else None)


main()
