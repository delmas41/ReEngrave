import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
s = json.load(open(here.parents[1] / "benchmarks/lane-report/sample.json"))
s["plates"]["litolff"]["pages"] = [6, 10]
s["plates"]["brahms"]["pages"] = [0, 5]
json.dump(s, open(here / "sample2.json", "w"))
