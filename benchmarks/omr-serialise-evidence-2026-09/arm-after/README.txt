The `after` arm of the byte-identity gate for `claude/fix-serialise-evidence`.

Committed so a record-the-evidence branch's own evidence does not need a
re-run to check.

  *.json.gz   the pipeline's result JSON, gzipped. The DECOMPRESSED bytes are
              the arm's own output unmodified — not a projection, not trimmed.
              A probe reading a hand-reduced file would not be demonstrating
              that the record reaches disk. 340 KB here against 1.6 MB raw.
  *.musicxml  the export. ⚠️ BYTE-IDENTICAL to the `before` arm's, verified by
              `cmp`, so these double as the gate's artefact: the headline
              claim is checkable against them without producing a before arm.

    python3 ../probe/probe_barline_prongs.py .          # reads .json.gz
    python3 ../probe/run_arm.py /tmp/mine               # regenerate an arm
    python3 ../../omr-pipeline-audit-2026-09/probe/compare_arms.py <before> /tmp/mine

Provenance: page 1 of the Litolff Beethoven 5 scan (scan-gate row
`beethoven-sym5-mvt1-984073-p1`) and page 0 of the LilyPond
`brahms-sym1-mvt1` e2e fixture. Both PDFs are gitignored build products /
machine-local library files; `run_arm.py` resolves them via OMR_FIXTURE_ROOT.
