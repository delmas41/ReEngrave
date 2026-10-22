"""Who resolves the margin when the free readers cannot: a person, or the model.

The two label tiers that cost nothing — the PDF text layer and OCR of the margin
crop — carry most pages most of the way
(`benchmarks/omr-margin-labels-2026-08/TESSERACT_2026-08-31.md`: 66 of 69 staves
on the clef corpus, unaided). What is left is small and expensive in different
currencies:

* **vision** — about a cent per system, needs nobody present, measured 29 of 29
  labels on two hand-verified pages;
* **human** — free in money, costs attention, and is the only source that is
  AUTHORITATIVE rather than merely accurate: an answer can be banked as ground
  truth, which is the binding constraint on measuring anything in this project.

**There is no default, deliberately.** The two differ in what they spend, not
just in how well they do, and a default would quietly pick one — spending the
user's money, or their attention, without being asked. `apply_contextual_analysis`
takes an `Assist` and will not run without one; `Assist.ask()` prompts and
refuses to proceed on an empty answer.

**The choice is not final.** A run can switch part-way — a human working through
a long score can hand the rest to the model, and a model run that stalls on a
page can be handed back — and every switch is recorded on the object, so a result
can always say who answered what.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

# The three states. NONE is not "no opinion": it is the deliberate choice to run
# on the free tiers alone and let the layer abstain where they fall short, which
# is the right answer for a batch that will be checked some other way.
MODES = ("human", "vision", "none")

_PROMPT = """
How should the margin be resolved where the free readers fall short?

  [h] human   — you are asked about the staves that failed, one at a time.
                Free, authoritative, and the answers can be kept as ground
                truth. Costs your attention.
  [v] vision  — the margin is read by Claude, about a cent per system, no one
                needed. Measured 29/29 labels on two hand-verified pages.
  [n] none    — free tiers only. The layer abstains where they fall short.

You can switch part-way: answer 'v' to any question to hand the rest over.
"""


@dataclass
class Assist:
    """The chosen mode, the switches, and what a human supplied along the way."""

    mode: str
    #: `(from, to, why)` for every switch, so a run can say who answered what.
    switches: list[tuple[str, str, str]] = field(default_factory=list)
    #: Every human answer, with provenance. See `staff_labels_human`.
    answers: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"assist mode must be one of {MODES}, got {self.mode!r}")

    def switch(self, mode: str, why: str = "") -> None:
        if mode not in MODES:
            raise ValueError(f"assist mode must be one of {MODES}, got {mode!r}")
        if mode == self.mode:
            return
        self.switches.append((self.mode, mode, why))
        self.mode = mode

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "switched": [{"from": a, "to": b, "why": w} for a, b, w in self.switches],
            "human_answers": len(self.answers),
        }

    @classmethod
    def ask(cls, stream=None, out=None) -> "Assist":
        """Put the question. No default — an empty answer is asked again.

        Raises if there is nobody to ask, rather than choosing: a non-interactive
        caller has to state the mode itself, which is the whole point.
        """
        stream = stream or sys.stdin
        out = out or sys.stderr
        if not (hasattr(stream, "isatty") and stream.isatty()):
            raise RuntimeError(
                "no assist mode given and no terminal to ask on — pass "
                "--assist human|vision|none (there is deliberately no default)")
        print(_PROMPT, file=out)
        while True:
            print("  human, vision or none? [h/v/n] ", end="", file=out, flush=True)
            answer = (stream.readline() or "").strip().lower()
            if answer in ("h", "human"):
                return cls("human")
            if answer in ("v", "vision"):
                return cls("vision")
            if answer in ("n", "none"):
                return cls("none")
            print("  please answer h, v or n.", file=out)


def add_cli_argument(parser) -> None:
    """`--assist`, with no default, for a command that runs the contextual pass."""
    parser.add_argument(
        "--assist", choices=MODES, default=None,
        help="who resolves the margin where the free readers fall short: "
             "'human' asks you, 'vision' calls Claude (~1c/system), 'none' "
             "abstains. REQUIRED — there is no default, because the two cost "
             "different things. Omit it on a terminal and you will be asked.")


def from_cli(args) -> Assist:
    """The mode from `--assist`, or the question if there is a terminal."""
    return Assist(args.assist) if args.assist else Assist.ask()
