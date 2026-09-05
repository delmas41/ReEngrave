"""With the flag off, does this change export the same BYTES as before it?

The condensed-parts split restructures `to_musicxml`'s part-emission loop on
both paths, so "it is behind a flag" is a claim about code that has been
rewritten around the flag — not a proof. This proves it, over every fixture
both benchmarks hold:

  * the 11 scan rows  (`omr-scan-e2e-2026-09/fixtures/*.restamp-composed.omr.json`)
  * the 11 engraved works (`omr-orchestral-e2e/fixtures/*.omr.json`)

Each is exported by the CURRENT tree with `OMR_CONDENSED_PARTS` unset, and by
the PRISTINE `export.py` from the base commit, and the bytes are compared.

⚠️ The engraved benchmark is single-system with one part per staff throughout,
so it could not observe this change even if the flag were on — which is exactly
why byte-identity is the right check there and re-running `orchestral_eval`
is not: it would add detector nondeterminism to a question with an exact
answer, and cost shared CPU for it. Same call as
`benchmarks/omr-staff-structure-2026-09/FINDINGS.md` §5.

    python3 benchmarks/omr-condensed-parts-2026-09/probe_flag_off_identity.py \
        --base a78c9454
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")


def fixtures() -> list[tuple[str, Path]]:
    out = []
    scan = ROOT / "benchmarks/omr-scan-e2e-2026-09/fixtures"
    for p in sorted(scan.glob("*.restamp-composed.omr.json")):
        out.append(("scan", p))
    eng = MAIN / "benchmarks/omr-orchestral-e2e/fixtures"
    for p in sorted(eng.glob("*.omr.json")):
        out.append(("engraved", p))
    return out


def export_all(mod) -> dict[str, str]:
    digests = {}
    for kind, path in fixtures():
        result = json.loads(path.read_text())
        xml = mod.to_musicxml(result)
        digests[f"{kind}:{path.name}"] = hashlib.sha256(
            xml.encode()).hexdigest()
    return digests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="a78c9454")
    args = ap.parse_args()

    os.environ.pop("OMR_CONDENSED_PARTS", None)
    os.environ["OMR_SLOT_STITCH"] = "0"

    sys.path.insert(0, str(ROOT))
    import tools.omr.export as export  # noqa: E402
    now = export_all(export)

    # The pristine module, loaded from the base commit under its own name so
    # importing it cannot disturb the live one.
    src = subprocess.run(["git", "show", f"{args.base}:tools/omr/export.py"],
                         cwd=ROOT, capture_output=True, text=True)
    if src.returncode != 0:
        print("could not read the base export.py:", src.stderr)
        return 2
    with tempfile.TemporaryDirectory() as td:
        pristine = Path(td) / "export.py"
        pristine.write_text(src.stdout)
        spec = importlib.util.spec_from_file_location(
            "tools.omr._export_pristine", pristine)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["tools.omr._export_pristine"] = mod
        spec.loader.exec_module(mod)
        before = export_all(mod)

    same = [k for k in now if now[k] == before.get(k)]
    diff = [k for k in now if now[k] != before.get(k)]
    for kind in ("scan", "engraved"):
        n = len([k for k in now if k.startswith(kind)])
        s = len([k for k in same if k.startswith(kind)])
        print(f"{kind:9s} byte-identical {s}/{n}")
    if diff:
        print("\nDIFFER:")
        for k in diff:
            print("  ", k)
        return 1
    print("\nflag off: every fixture exports the same bytes as the base tree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
