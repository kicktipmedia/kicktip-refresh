"""Pixel diff of two px_shots.py output dirs. Reports, per image, the count of pixels differing by more than TOL (default 8 of 255 on any channel) and the max difference. python3 tests/px_diff.py BASE NEW [TOL]"""
import sys, os
import numpy as np
from PIL import Image
a, b = sys.argv[1], sys.argv[2]; tol = int(sys.argv[3]) if len(sys.argv) > 3 else 8; bad = 0; n = 0; tiny = 0
for f in sorted(os.listdir(a)):
    x = np.array(Image.open(f"{a}/{f}").convert("RGB")).astype(int); y = np.array(Image.open(f"{b}/{f}").convert("RGB")).astype(int); n += 1
    if x.shape != y.shape: print("SIZE", f, x.shape, y.shape); bad += 1; continue
    d = np.abs(x - y).max(axis=2); big = d > tol; tiny += int((d > 0).any())
    if big.any():
        ys, xs = np.where(big); print("DIFF", f, "px>tol:", int(big.sum()), "max:", int(d.max()), "bbox:", (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))); bad += 1
print(f"{n} images compared, {bad} differ by more than {tol}/255 ({tiny} have any sub-threshold difference, max noise level shown above)")
