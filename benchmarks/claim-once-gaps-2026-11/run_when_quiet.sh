#!/bin/bash
# wait while any python process holds > 4 GB (another agent's), then run the given command
while ps -axo rss,args | grep -E "[Pp]ython" | awk '$1>4000000{f=1} END{exit !f}'; do sleep 30; done
exec "$@"
