# -*- coding: utf-8 -*-
"""Test: XPS C1s có đỉnh phụ năng lượng cao -> cắt vùng fit ở đáy thung lũng, nền neo ở đó."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import xps  # noqa: E402


def pho(bump, seed=1):
    rng = np.random.default_rng(seed)
    be = np.arange(276.0, 295.0, 0.1)

    def pk(x0, w, A):
        g = xps.gl(be, x0, w)
        return A * g / g.max()
    nho = pk(284.8, 1.4, 1) + pk(286.3, 1.6, .5)
    y = pk(284.8, 1.4, 3500) + pk(286.3, 1.6, 1800) + pk(288.6, 1.6, 500) + (pk(292.3, 1.8, 1400) if bump else 0)
    y = y + 4400 + 2000 * np.cumsum(nho) / nho.sum() + rng.normal(0, 35, len(be))
    return be, y


class TestThungLung(unittest.TestCase):
    def test_co_dinh_phu_thi_cat_vung(self):
        for seed in (1, 2, 3):
            be, y = pho(True, seed)
            kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False)
            hi = kq["tham_so_fit"]["vung"][1]
            self.assertTrue(289.5 < hi < 290.6, hi)
            self.assertLess(kq["fit"]["rstd"], 1.4)
            self.assertTrue(any(g.startswith("Có đỉnh phụ") for g in kq["ghi"]))

    def test_khong_cat_neu_tat(self):
        be, y = pho(True)
        kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False, cat_thung_lung=False)
        self.assertEqual(kq["tham_so_fit"]["vung"], (281.5, 291.0))
        self.assertGreater(kq["fit"]["rstd"], 2.0)             # đối chứng: neo nền trên sườn đỉnh phụ làm fit xấu

    def test_khong_dinh_phu_thi_giu_nguyen(self):
        for seed in (1, 2, 3):
            be, y = pho(False, seed)
            kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False)
            self.assertEqual(kq["tham_so_fit"]["vung"], (281.5, 291.0))
            self.assertFalse(any(g.startswith("Có đỉnh phụ") for g in kq["ghi"]))

    def test_ham_tim_thung_lung(self):
        be, y = pho(True)
        d, g = xps.cat_vung_thung_lung(be, y, (281.5, 291.0))
        self.assertTrue(289.5 < d < 290.6)
        self.assertIn("đáy thung lũng", g)
        be, y = pho(False)
        self.assertEqual(xps.cat_vung_thung_lung(be, y, (281.5, 291.0)), (None, None))


if __name__ == "__main__":
    unittest.main()
