"""The owner of s2 tile 11's head (Litolff p4 glyph/4/1/1/4/3) from the litolff16 ON record. python3 benchmarks/page-ledger-2026-10/s3/tile11.py"""
import sys

sys.path.insert(0, "benchmarks/page-ledger-2026-10/s3")
import measure as M  # noqa: E402
from tools.omr.staged import cell_map as CM  # noqa: E402
from tools.omr.staged import claim_readout as CR  # noqa: E402

rec = "/private/tmp/s3work/litolff16.on.gathered.record.json"
src = CR.resolve_source(rec)
pdf = CR.LIB / CR.edition_info(CR.read_rows(src, [4]))["edition_path"]
H, _ = M.arms(rec, [4], CM.ROOT_DEFAULT, pdf, True)
for k, v in H.items():
    if "glyph/4/1/1/4/3" in v["members"]:
        print(k, v["status"], v["owner"], v["reason"], v["candidates"], v["seen_from"])
