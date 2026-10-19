"""2.171 probe 0: what scale was the production weights file trained at? Prints train_args from the checkpoint."""
import sys
import torch
p = sys.argv[1]
c = torch.load(p, map_location='cpu', weights_only=False)
ta = c.get('train_args') or {}
print({k: v for k, v in ta.items() if k in ('imgsz', 'data', 'epochs', 'scale', 'mosaic', 'rect', 'model', 'batch', 'fliplr', 'translate', 'multi_scale', 'close_mosaic')})
print('keys', list(c.keys()))
