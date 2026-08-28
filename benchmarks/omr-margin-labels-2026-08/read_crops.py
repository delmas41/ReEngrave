#!/usr/bin/env python3
"""Stage 2 of the margin-label pilot: read the crops with Claude and score them.

Scores on the RESOLVED INSTRUMENT, not the raw string — "Fg." and "Fag." are both
Bassoon and both correct. Per staff:

    agree       both paths resolve the same instrument
    disagree    both resolve, differently   <- the number that decides this
    recovered   vision resolved one where the text layer could not
    missed      the text layer resolved one where vision did not
    both_silent neither — usually a genuinely unlabelled staff

`recovered` is the point: the text layer resolves 79% of labelled staves and the
residue is garbled OCR ("V}a.", ",/\\"", "/A") that a human reads at a glance.

Needs only `anthropic` — run it from an environment with the pinned 0.116.0 SDK
(the repo's host Python has 0.28.0, which predates structured outputs).

Usage: apienv/bin/python read_crops.py --budget 1.00
"""
from __future__ import annotations

import argparse
import base64
import collections
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# instruments.py is stdlib-only, so load it directly rather than importing the
# tools.omr package (whose __init__ pulls in numpy).
_spec = importlib.util.spec_from_file_location(
    "instruments", ROOT / "tools" / "omr" / "instruments.py")
instruments = importlib.util.module_from_spec(_spec)
# Register before exec: dataclasses resolves field types through
# sys.modules[cls.__module__], which is None for an unregistered module.
sys.modules["instruments"] = instruments
_spec.loader.exec_module(instruments)

PRICE_IN, PRICE_OUT = 5.00, 25.00     # Claude Opus 5, $/MTok

_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "staff_index": {"type": "integer"},
                    "text": {"type": ["string", "null"]},
                },
                "required": ["staff_index", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["labels"],
    "additionalProperties": False,
}

PROMPT = """This is the left margin of one system of an orchestral score, rotated \
upright. Each staff is marked in the grey gutter on the left with its index number \
and a tick at the staff's vertical centre.

Read the instrument label printed beside each numbered staff and return it exactly \
as printed, including any key designation — "Cl. B", "Cor. D.", "2 Clarinetti in B", \
"Fl.", "Vla.".

Rules:
- Report one entry per numbered staff, using the number from the gutter.
- If a staff has NO label printed beside it, return null for that staff. Do not \
guess from position or from the instruments above it. Strings in particular are \
often left unlabelled, and an invented label is worse than none.
- Transcribe what is printed. Do not expand abbreviations, translate them, or \
correct spelling."""


def load_key() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    for env in (ROOT / "backend" / ".env",
                Path("/Users/seanjohnson/Desktop/ReEngrave/backend/.env")):
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops", default=str(HERE / "crops"))
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--budget", type=float, default=1.00, help="hard USD cap")
    ap.add_argument("--out", default=str(HERE / "results.json"))
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("no ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=key)

    crops = Path(args.crops)
    manifest = json.loads((crops / "manifest.json").read_text())

    tally = collections.Counter()
    notes: list[str] = []
    results = []
    spend = 0.0

    for entry in manifest:
        if spend >= args.budget:
            print(f"budget cap ${args.budget:.2f} reached; stopping", file=sys.stderr)
            break
        png = (crops / entry["png"]).read_bytes()
        try:
            response = client.messages.create(
                model=args.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/png",
                        "data": base64.standard_b64encode(png).decode("utf-8")}},
                    {"type": "text", "text": PROMPT},
                ]}],
                output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            )
        except Exception as exc:                          # noqa: BLE001
            print(f"  API error on {entry['png']}: {exc}", file=sys.stderr)
            continue

        usage = response.usage
        spend += (usage.input_tokens * PRICE_IN + usage.output_tokens * PRICE_OUT) / 1e6

        if response.stop_reason == "refusal":
            print(f"  refused: {entry['png']}", file=sys.stderr)
            continue
        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            continue
        data = json.loads(text)

        wanted = set(entry["staff_indices"])
        vision = {}
        for item in data.get("labels", []):
            idx, raw = item.get("staff_index"), item.get("text")
            if idx in wanted and isinstance(raw, str) and raw.strip():
                vision[idx] = raw.strip()

        truth = entry["truth"]
        for idx in entry["staff_indices"]:
            t = truth.get(str(idx), {})
            # Re-resolve the ground-truth STRING rather than trusting the
            # instrument stored at crop time — otherwise a lexicon fix makes
            # old manifests disagree with themselves. (This is exactly how the
            # "Tp." fix first showed up as two phantom disagreements.)
            t_hit = instruments.lookup(t.get("text")) if t.get("text") else None
            t_inst = t_hit.instrument.name if t_hit else None
            v_raw = vision.get(idx)
            v_hit = instruments.lookup(v_raw) if v_raw else None
            v_inst = v_hit.instrument.name if v_hit else None

            if t_inst and v_inst:
                key_ = "agree" if t_inst == v_inst else "disagree"
                tally[key_] += 1
                if key_ == "disagree" and len(notes) < 15:
                    notes.append(f"  DISAGREE  {entry['png']} staff {idx}: "
                                 f"text {t.get('text')!r}->{t_inst} vs "
                                 f"vision {v_raw!r}->{v_inst}")
            elif v_inst:
                tally["recovered"] += 1
                if len(notes) < 15:
                    notes.append(f"  RECOVERED {entry['png']} staff {idx}: "
                                 f"text {t.get('text')!r} -> vision {v_raw!r} -> {v_inst}")
            elif t_inst:
                tally["missed"] += 1
                if len(notes) < 15:
                    notes.append(f"  MISSED    {entry['png']} staff {idx}: "
                                 f"text {t.get('text')!r}->{t_inst}, vision {v_raw!r}")
            else:
                tally["both_silent"] += 1

        results.append({"png": entry["png"], "vision": vision, "truth": truth})

    Path(args.out).write_text(json.dumps(results, indent=2))

    print(f"\nmodel {args.model}   crops read: {len(results)}   spend: ${spend:.3f}")
    total = sum(tally.values())
    print(f"staves compared: {total}")
    for k in ("agree", "disagree", "recovered", "missed", "both_silent"):
        print(f"  {k:12s} {tally[k]:4d}")
    resolved = tally["agree"] + tally["disagree"]
    if resolved:
        print(f"\nagreement where both resolved: {tally['agree']}/{resolved} "
              f"({tally['agree']/resolved:.0%})")
    print(f"recovered (text layer could not, vision could): {tally['recovered']}")
    if notes:
        print("\ndetail:")
        for n in notes:
            print(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
