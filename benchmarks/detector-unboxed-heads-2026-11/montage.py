"""Crop each anchor (page point) with record head boxes drawn (green = detector, magenta = rescue pass) and stack 2 per image."""
import sys
import numpy as np
import cv2
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import crop as cr

ANCH = {
    'a_r1t3_p2': ('litolff', 2, 2230, 2592), 'b_r1t12_p3': ('litolff', 3, 1290, 1039), 'c_r1t10_p2': ('litolff', 2, 1975, 2592),
    'd_r1t2_p2': ('litolff', 2, 2232, 2276), 'e_r1t7_p10': ('litolff', 10, 670, 2683), 'f_r1t6_p10': ('litolff', 10, 801, 2680),
    'g_r1t8_p3': ('litolff', 3, 1551, 1034), 'h_r1t5_p2': ('litolff', 2, 2233, 2726),
    'i_260b_t2_p10': ('litolff', 10, 2000, 2747), 'j_260b_t9_p10': ('litolff', 10, 1840, 2875),
}
if __name__ == '__main__':
    names = list(ANCH)
    S = 3
    for i in range(0, len(names), 2):
        ims = []
        for n in names[i:i + 2]:
            d, p, x, y = ANCH[n]
            f = 'out/print/2.267-unboxed/anch_%s.png' % n
            cr.make(d, p, x - 150, y - 60, x + 150, y + 60, f, S)
            im = cv2.imread(f)
            cv2.putText(im, n, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            ims.append(im)
        cv2.imwrite('out/print/2.267-unboxed/montage_%d.png' % (i // 2), np.vstack(ims))
