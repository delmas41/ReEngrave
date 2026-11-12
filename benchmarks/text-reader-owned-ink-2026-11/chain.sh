#!/bin/bash
# ROADMAP 2.304: the measuring gathers, ONE AT A TIME (CLAUDE.md lean lanes): wait for the Litolff OFF gather, then Litolff ON, Brahms OFF, Brahms ON.
cd "$(dirname "$0")/../.."
W=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/2304-work
until grep -q "^done" $W/litolff.off.gather.log; do sleep 10; done
OMR_TEXT_CROP_OWNED_INK=1 benchmarks/text-reader-owned-ink-2026-11/gather_plate.sh litolff on 2,4,6,8,9,10,11,16
benchmarks/text-reader-owned-ink-2026-11/gather_plate.sh brahms off 0,4,12,14
OMR_TEXT_CROP_OWNED_INK=1 benchmarks/text-reader-owned-ink-2026-11/gather_plate.sh brahms on 0,4,12,14
echo chain done > $W/chain.done
