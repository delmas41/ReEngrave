import sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from load import load, LITOLFF
d, R = load(LITOLFF)
a = d["provenance"]["settings"]["args"]; print(a["pdf"], a["dpi"], a["pages"], d["provenance"]["settings"]["env_overrides"])
