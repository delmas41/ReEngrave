import sys, json
from pathlib import Path
REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/benchmarks/omr-local-staff-2026-09")
import score_2_48 as S

S.RECORD_PATHS = {
    ("beethoven5-litolff", "base"): Path("/tmp/aa-base-1/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json"),
    ("beethoven5-litolff", "arm"): Path("/tmp/aa-base-2/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json"),
    ("brahms1-breitkopf", "base"): Path("/tmp/aa-base-1/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json"),
    ("brahms1-breitkopf", "arm"): Path("/tmp/aa-base-2/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json"),
}

S.main()
