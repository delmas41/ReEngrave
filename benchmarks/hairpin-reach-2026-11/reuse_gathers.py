"""ROADMAP 2.254: run `lane_report` on gathered records already on disk (same tree's GATHER), re-running ADJUDICATE..EXPORT for both
arms on this tree. Used because an arm whose Surya OCR timed out under machine load loses margin labels and whole staves (Brahms p25
horns / 1.Viol.: 'L.Viol.', '(C)' dropped), which is test noise, not the flag; the clean OFF and ON gathers are paired instead.

    python3 benchmarks/hairpin-reach-2026-11/reuse_gathers.py OFF.gathered.record.json ON.gathered.record.json -- <lane_report args>
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR  # noqa: E402


def main(argv):
    i = argv.index("--")
    off, on = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    src = {"off": off, "on": on}

    def gather_one(plate, arm, flag_env, pages, work, env0):
        rp = work / ("%s.%s.gathered.record.json" % (plate, arm))
        if rp.resolve() != src[arm].resolve():
            shutil.copyfile(src[arm], rp)
        print("  reused gather %s %s <- %s" % (plate, arm, src[arm]), flush=True)
        return rp

    LR.gather_one = gather_one
    return LR.main(argv[i + 1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
