"""How close is Surya's decision on one character — measured, not inferred.

RUNS INSIDE `.venv-surya`, like `_surya_worker.py`, and imports nothing from
`tools.*`.

    .venv-surya/bin/python benchmarks/omr-margin-labels-2026-08/probe_surya_margin.py \
        --job benchmarks/omr-margin-labels-2026-08/.job-beet5-p48.json --contains Te

`probe_surya_determinism.py` answers "does the answer move"; this answers "how
far would it have to be pushed". A token the model picks at p=0.99 is not going
to flip because a matmul reduced in a different order; one it picks at p=0.51
over a near neighbour is one build, one backend or one batch away from flipping,
and "I could not make it move" would then be a statement about this machine
rather than about the reader.

It re-asks the server for the SAME completion with `top_logprobs`, which surya
does not request, and prints every token whose runner-up is within `--within`
nats — plus, for `--contains`, the alternatives at the tokens spelling it.

`--sample T:P --repeat N` prices the one genuinely stochastic path in surya's
client. `openai_client.chat_completions_batch` decodes at temperature 0.0, but
`_should_retry` fires on a transport error OR on a detected repeat token, and
each retry raises the temperature — `min(0.0 + 0.2 * (retries + 1), 0.8)`, with
`top_p` 0.95 on the repeat branch. A page whose first attempt fails is therefore
read by a SAMPLED decode, and this reports how much that moves the answer.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import sys
from pathlib import Path

CAPTURED: list[dict] = []
SAMPLED: list[str] = []
SAMPLE: tuple[float, float] | None = None
REPEAT = 0


def install_probe(top_logprobs: int) -> None:
    """Re-issue each of surya's own requests, asking for the alternatives too."""
    from surya.inference.backends import llamacpp
    from surya.inference.backends.openai_client import (
        _build_messages, chat_completions_batch as real,
    )
    from surya.inference.prompts import PROMPT_MAPPING
    from surya.inference.util import scale_to_fit

    def wrapper(batch, client, model_name, **kw):
        out = real(batch, client, model_name, **kw)
        for item in batch:
            if SAMPLE is not None:
                temp, top_p = SAMPLE
                messages = _build_messages(
                    scale_to_fit(item.image),
                    item.prompt or PROMPT_MAPPING[item.prompt_type])
                for _ in range(REPEAT):
                    got = client.chat.completions.create(
                        model=model_name, messages=messages,
                        max_tokens=item.max_tokens or kw.get("max_tokens_default", 2048),
                        temperature=temp, top_p=top_p,
                    )
                    SAMPLED.append(got.choices[0].message.content or "")
                continue
            messages = _build_messages(scale_to_fit(item.image),
                                       item.prompt or PROMPT_MAPPING[item.prompt_type])
            completion = client.chat.completions.create(
                model=model_name, messages=messages,
                max_tokens=item.max_tokens or kw.get("max_tokens_default", 2048),
                temperature=0.0, top_p=0.1,
                logprobs=True, top_logprobs=top_logprobs,
            )
            choice = completion.choices[0]
            CAPTURED.append({
                "text": choice.message.content or "",
                "tokens": [
                    {"token": c.token, "logprob": c.logprob,
                     "alts": [{"token": a.token, "logprob": a.logprob}
                              for a in (c.top_logprobs or [])]}
                    for c in (getattr(choice.logprobs, "content", None) or [])
                ],
            })
        return out

    llamacpp.chat_completions_batch = wrapper


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", type=Path, required=True)
    ap.add_argument("--contains", default="",
                    help="report the alternatives at the tokens spelling this")
    ap.add_argument("--within", type=float, default=2.0,
                    help="also report any token whose runner-up is this close, in nats")
    ap.add_argument("--top-logprobs", type=int, default=5)
    ap.add_argument("--sample", default="",
                    help="TEMP:TOP_P — decode at the retry ladder's settings "
                         "instead of reading logprobs (e.g. 0.2:0.95)")
    ap.add_argument("--repeat", type=int, default=8,
                    help="with --sample, how many sampled decodes")
    args = ap.parse_args()

    global SAMPLE, REPEAT
    if args.sample:
        temp, top_p = args.sample.split(":")
        SAMPLE, REPEAT = (float(temp), float(top_p)), args.repeat

    install_probe(args.top_logprobs)

    from PIL import Image
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor

    predictor = RecognitionPredictor(SuryaInferenceManager())
    job = json.loads(args.job.read_text())
    for system in job["systems"]:
        image = Image.open(io.BytesIO(
            base64.standard_b64decode(system["png_b64"]))).convert("RGB")
        margin = image.crop((int(system.get("gutter_px") or 0), 0,
                             image.width, image.height))
        predictor([margin], full_page=True)

    if SAMPLE is not None:
        import re as _re
        from collections import Counter
        temp, top_p = SAMPLE
        print(f"\n=== {len(SAMPLED)} decodes at temperature {temp}, "
              f"top_p {top_p} ===")
        texts = Counter(SAMPLED)
        print(f"  {len(texts)} distinct whole outputs")
        # The label strings alone, so a moved bbox digit is not read as a moved
        # READING — only the text reaches `instruments.lookup`.
        labels = Counter(tuple(_re.findall(r"<p>(.*?)</p>", t)) for t in SAMPLED)
        print(f"  {len(labels)} distinct label sequence(s)")
        for seq, n in labels.most_common():
            print(f"    x{n}  {list(seq)}")
        return 0

    for i, cap in enumerate(CAPTURED):
        print(f"\n=== request {i}: {len(cap['tokens'])} tokens ===")
        for pos, tok in enumerate(cap["tokens"]):
            alts = [a for a in tok["alts"] if a["token"] != tok["token"]]
            gap = (tok["logprob"] - alts[0]["logprob"]) if alts else float("inf")
            hit = args.contains and args.contains in tok["token"]
            if not hit and gap > args.within:
                continue
            p = math.exp(tok["logprob"])
            runner = (f"{alts[0]['token']!r} p={math.exp(alts[0]['logprob']):.3f}"
                      if alts else "(none offered)")
            print(f"  [{pos:3d}] {tok['token']!r:12s} p={p:.3f}  "
                  f"gap {gap:.2f} nats  runner-up {runner}"
                  + ("   <- CONTAINS" if hit else ""))
    if not CAPTURED:
        print("no requests captured — did the predictor use another backend?",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
