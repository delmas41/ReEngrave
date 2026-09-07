"""What is actually on the staff dicts of the wired run?

Usage:  inspect_wired.py WIRED.json
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

w = json.loads(Path(sys.argv[1]).read_text())
staves = [st for p in w["pages"] for s in p["systems"] for st in s["staves"]]
print(f"staff dicts: {len(staves)}")
print("instrument_veto:", dict(collections.Counter(
    st.get("instrument_veto") for st in staves)))
print("instrument (top 8):", collections.Counter(
    st.get("instrument") for st in staves).most_common(8))
print("instrument_source:", dict(collections.Counter(
    st.get("instrument_source") for st in staves)))
slot9 = [st for st in staves if st.get("slot_index") == 9]
print(f"\nslot_index == 9: {len(slot9)}")
print("  instrument:", dict(collections.Counter(
    st.get("instrument") for st in slot9)))
print("  veto:", dict(collections.Counter(
    st.get("instrument_veto") for st in slot9)))
