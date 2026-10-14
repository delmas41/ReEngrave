# The CONTROL mix of ROADMAP 2.4b (train_2.4b.sh CONTROL=1), sourced by the 2.110 scripts. No v24: labels are not a variable here.
DENSE="v1-2026-05-18-orchestral v2-2026-06-08-beet5 v3-2026-06-09-mahler5 v4-2026-06-10-la-mer"
HOLLOW="v13-2026-09-03-complete-v7-beet5-bolero v14-2026-09-03-complete-litolff v15-2026-09-03-complete-peters v16-2026-09-03-complete-eulenburg v17-2026-09-03-complete-simrock v18-2026-09-03-complete-breitkopf v19-2026-09-03-complete-mahler1 v20-2026-09-03-complete-elgar1 v21-2026-09-03-complete-lamer v22-2026-09-04-simrock-dense"
V24=v24-2026-10-13-hollow4-train
# make_catalog <srcroot> <catdir>  -- symlink the versions from <srcroot>/<v> into <catdir>, build catalog yaml + 2x dense
make_catalog() {
  local SRC="$1" CAT="$2"
  rm -rf "$CAT"; mkdir -p "$CAT"
  for v in $DENSE $HOLLOW; do ln -sfn "$SRC/$v" "$CAT/$v"; done
  python3 -m tools.omr.training.build_catalog_yaml --root "$CAT" --versions $DENSE $HOLLOW --fallback-class-names tools/omr/training/deepscoresv2_208_classes.json >/dev/null
  python3 benchmarks/omr-labeling-survey-2026-09/oversample_dense.py --catalog "$CAT/catalog.yaml" --factor 2
}
