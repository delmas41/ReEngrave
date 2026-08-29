# Evidence — what was actually looked at

The hand-labeled cells understate precision by design (they include ink-bleed cells as
hard negatives with sparse labels), so the `imgsz` question was settled by rendering
cells and counting.

| image | what it settled |
|---|---|
| `handel-cells-counted-by-eye.png` | Six consecutive cells of handel-reduction p20: **4 + 1 + 3 + 1 + 4 + 3 = 16 noteheads, 2.7 per cell.** That matches `imgsz=1280`'s 2.6 and refutes `imgsz=2048`'s 29.2. |
| `cell-predictions-640-vs-2048.png` | One cell with green ground truth and red predictions at both settings. At 2048 the model emits 42 boxes, most of them small and sitting on **staff lines**, largely missing the 8 labeled noteheads; at 640 it emits 38, larger and far better aligned. |
