"""Reference wedge starts per frozen page (per PART, so condensed staves over-count), with 2.253's bar ranges (ROADMAP 2.254)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "page-claim-order-2026-11"))
import hairpins as HP  # noqa: E402

for plate in ("litolff", "brahms"):
    R = HP.page_rows(plate)
    ref = HP.ref_wedges_by_bar(plate)
    for p in sorted(R):
        br = HP.bar_range(R[p], p)
        cv = [o for o in R[p]["wedge_box"] if o["reader"] == "cv_hairpins"]
        print(plate, p, br, "ref", sum(ref[b] for b in range(br[0], br[1] + 1)) if br else None, "record cv rows", len(cv))
