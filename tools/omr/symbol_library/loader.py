"""SymbolLibrary — read-side of the symbol library.

Loads the manifest written by builder.py, lazy-loads template arrays, and
provides Hu-moment pre-screening + multi-scale NCC matching.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

DATA_DIR = Path(__file__).parent / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"


@dataclass
class LibraryEntry:
    smufl_name: str
    category: str
    size_px: int
    image_path: str          # relative to DATA_DIR
    shape: tuple[int, int]   # (h, w)
    hu_moments: np.ndarray   # length 7
    variant_id: str | None = None
    _image: np.ndarray | None = field(default=None, repr=False)

    @property
    def key(self) -> str:
        v = self.variant_id or ""
        return f"{self.smufl_name}@{self.size_px}{('|' + v) if v else ''}"

    def load_image(self, data_dir: Path = DATA_DIR) -> np.ndarray:
        if self._image is None:
            self._image = np.load(data_dir / self.image_path)
        return self._image


@dataclass
class Match:
    entry: LibraryEntry
    score: float            # NCC score, -1..1 (higher = better)
    scale: float            # scale at which the best match was found
    location: tuple[int, int] = (0, 0)  # (y, x) of top-left in component image

    @property
    def smufl_name(self) -> str:
        return self.entry.smufl_name

    @property
    def category(self) -> str:
        return self.entry.category


class SymbolLibrary:
    """Loaded symbol library, suitable for querying."""

    def __init__(self, entries: list[LibraryEntry], data_dir: Path = DATA_DIR):
        self.entries = entries
        self.data_dir = data_dir
        # Pre-stack Hu moments for fast nearest-neighbor query
        self._hu_matrix = np.stack([e.hu_moments for e in entries], axis=0) \
            if entries else np.zeros((0, 7))

    @classmethod
    def load(cls, manifest_path: Path = MANIFEST_PATH) -> "SymbolLibrary":
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"symbol library manifest not found at {manifest_path}; "
                "run `python3 -m tools.omr.symbol_library.builder` first"
            )
        raw = json.loads(manifest_path.read_text())
        entries = []
        for e in raw["entries"]:
            entries.append(LibraryEntry(
                smufl_name=e["smufl_name"],
                category=e["category"],
                size_px=e["size_px"],
                image_path=e["image_path"],
                shape=tuple(e["shape"]),
                hu_moments=np.array(e["hu_moments"], dtype=np.float64),
                variant_id=e.get("variant_id"),
            ))
        return cls(entries, data_dir=manifest_path.parent)

    def __len__(self) -> int:
        return len(self.entries)

    # ─── Pre-screening by Hu moments ─────────────────────────────────────
    def query(self, hu: np.ndarray, top_k: int = 10) -> list[LibraryEntry]:
        """Return the top-k candidates whose Hu moments are closest (L2)."""
        if len(self.entries) == 0:
            return []
        diffs = self._hu_matrix - hu[None, :]
        d = np.sqrt(np.sum(diffs * diffs, axis=1))
        order = np.argsort(d)[:top_k]
        return [self.entries[i] for i in order]

    # ─── Multi-scale NCC match ───────────────────────────────────────────
    def match(
        self,
        component_image: np.ndarray,
        candidates: list[LibraryEntry] | None = None,
        scales: tuple[float, ...] = (0.85, 1.0, 1.15),
    ) -> list[Match]:
        """For each candidate, scale the template at each of the given
        scales, perform normalized cross-correlation against the component
        image (after padding so the smallest template fits), and return one
        Match per candidate with the best score across scales.

        Higher score = better match. Skips candidates whose scaled template
        exceeds the component image dimensions.
        """
        if candidates is None:
            candidates = self.entries
        if component_image.ndim != 2:
            component_image = cv2.cvtColor(component_image, cv2.COLOR_BGR2GRAY)
        # cv2.matchTemplate wants the SAME polarity in both inputs. Phase 1
        # convention is 255 = paper, 0 = ink. Convert to ink-positive for
        # cleaner NCC (255 = ink, 0 = paper).
        comp = (255 - component_image).astype(np.uint8)

        ch, cw = comp.shape

        results: list[Match] = []
        for entry in candidates:
            tpl_raw = entry.load_image(self.data_dir)
            tpl = (255 - tpl_raw).astype(np.uint8)  # ink-positive
            best_score = -2.0
            best_scale = 1.0
            best_loc = (0, 0)
            for s in scales:
                new_h = max(2, int(round(tpl.shape[0] * s)))
                new_w = max(2, int(round(tpl.shape[1] * s)))
                if new_h > ch or new_w > cw:
                    continue
                tpl_s = cv2.resize(tpl, (new_w, new_h), interpolation=cv2.INTER_AREA)
                try:
                    res = cv2.matchTemplate(comp, tpl_s, cv2.TM_CCOEFF_NORMED)
                except cv2.error:
                    continue
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = float(max_val)
                    best_scale = s
                    best_loc = (int(max_loc[1]), int(max_loc[0]))  # (y, x)
            if best_score > -2.0:
                results.append(Match(
                    entry=entry,
                    score=best_score,
                    scale=best_scale,
                    location=best_loc,
                ))
        # Sort best-first
        results.sort(key=lambda m: m.score, reverse=True)
        return results
