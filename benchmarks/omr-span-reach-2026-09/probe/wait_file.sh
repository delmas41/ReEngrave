#!/bin/bash
# Block until a path exists.
p="$1"
while [ ! -e "$p" ]; do sleep 30; done
echo "EXISTS $p"
