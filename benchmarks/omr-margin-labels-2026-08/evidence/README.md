# Evidence — what the vision reader is actually sent

`margin-crop-example.png` is one system's margin strip as the model receives it:
Beethoven 4 p59, with the grey gutter carrying each staff's index and a tick at its
vertical centre so the answer keys to our numbering rather than to reading order.

Two things are visible in it that the findings describe:

- The labels are clean and legible where the surrounding OCR text layer is garbage.
- **`Cor. (Es)` has no tick beside it** — the staff detector missed that staff
  entirely. The reader can only answer about staves that exist, which bounds its
  accuracy. It also means *more labels than numbered staves is evidence of a missed
  staff*, a signal not yet used.
