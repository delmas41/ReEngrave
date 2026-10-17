#!/bin/sh
# ROADMAP 2.164 Phase 1: one crop per mechanism (blue = our head box, orange = the arc box from the previous bar)
L=benchmarks/omr-head-fill-2026-09/probe/look_2_164.py
O=out/print/2.164-why
mkdir -p $O
python3 $L $O/1-tie-cut-at-the-barline-litolff.png litolff:glyph/5/1/4/2/1:glyph/5/1/4/1/1
python3 $L $O/2-hollow-class-so-no-width-floor-brahms.png brahms:glyph/21/0/3/6/18:glyph/21/0/3/5/9
python3 $L $O/3-black-class-wider-than-the-floor-litolff.png litolff:glyph/3/1/5/3/1:glyph/3/1/5/2/0
python3 $L $O/4-written-as-a-half-brahms.png brahms:glyph/26/1/2/6/21:glyph/26/1/2/5/11
python3 $L $O/5-barline-sliver-already-refused-brahms.png brahms:glyph/7/0/8/3/5:glyph/7/0/8/2/4
python3 $L $O/6-control-box-holds-a-real-head-litolff.png litolff:glyph/14/1/2/11/5:glyph/14/1/2/10/2
