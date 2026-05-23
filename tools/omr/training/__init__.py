"""DeepScoresV2 -> YOLOv8 training pipeline.

This package contains scripts to:

    1. Download the DeepScoresV2 dataset (download_dataset.py)
    2. Convert it to YOLO format (prepare_yolo_data.py)
    3. Fine-tune YOLOv8m on it (train_yolo.py)
    4. Evaluate the resulting weights on this project's actual cells
       (eval_on_score_cells.py)

The scripts are designed to be runnable in order on a GPU machine. See
README.md in this directory for a full bootstrap walkthrough.
"""

from __future__ import annotations
