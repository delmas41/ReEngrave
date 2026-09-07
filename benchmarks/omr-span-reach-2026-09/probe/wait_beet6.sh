#!/bin/bash
# Block until the Beethoven 6 compose run has written both arms.
d="$(cd "$(dirname "$0")/../out/beet6" && pwd)"
while [ ! -f "$d/spans-on.json" ]; do sleep 30; done
echo "BEET6 BOTH ARMS WRITTEN"
