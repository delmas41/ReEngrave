# Curated movements.yaml — Phase E catalog-ready editions

These are the hand-curated per-movement page-range yaml files for the
catalog-ready editions, copied here as the **version-controlled canonical
source**. The pipeline at runtime reads them from
`tools/omr/training/data/imslp/{work}/pdfs/{edition}/movements.yaml`, but
that path lives under a gitignored, symlinked dataset directory, so the
checked-in copies here are the authoritative version of these files.

If you're setting up a fresh checkout (or recovering after the dataset
symlink is regenerated): copy each `{work}--{edition}.movements.yaml`
file from this directory into the dataset path it names. The naming
convention is `{work}--{edition}.movements.yaml` →
`tools/omr/training/data/imslp/{work}/pdfs/{edition}/movements.yaml`.

| File | Edition | Verified |
|---|---|:---:|
| `beethoven-symphony-1--imslp-52848.movements.yaml` | Werke 1862 Breitkopf | YES |
| `beethoven-symphony-2--imslp-503997.movements.yaml` | Litolff 1870 | YES |
| `beethoven-symphony-2--imslp-977672.movements.yaml` | Ricordi 1909 | YES |
| `beethoven-symphony-4--imslp-411721.movements.yaml` | Heugel & Cie Paris (n.d.) | NO (mvt 3 boundary unconfirmed) |
| `beethoven-symphony-5--imslp-52624.movements.yaml` | Werke 1862 Breitkopf — **the Phase C anchor**; pre-existing | partial (Sean's prior file; mvt 1 verified) |
| `beethoven-symphony-6--imslp-57857.movements.yaml` | Werke 1863 Breitkopf — has mid-page mvt 3→4 transition | YES |
| `beethoven-symphony-8--imslp-06303.movements.yaml` | Eulenburg 1938 (Unger) | YES |
| `beethoven-symphony-8--imslp-875077.movements.yaml` | Werke 1863 Breitkopf | YES |

See `../PHASE_E_SUMMARY.md` for the full table and the methodology used to
verify each boundary.
