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


def pho_rong(seed=1):
    """C1s rộng (FWHM ~2,8 eV, đỉnh chính ~284,5) như mẫu CoCe: mô hình chuẩn (FWHM <= 1,6) không mô tả nổi."""
    rng = np.random.default_rng(seed)
    be = np.arange(275.1, 295.1, 0.125)

    def pk(x0, w, A):
        g = xps.gl(be, x0, w)
        return A * g / g.max()
    y = pk(284.5, 2.8, 4300) + pk(286.4, 2.4, 1100) + pk(288.0, 2.0, 500) + 4450 + rng.normal(0, 40, len(be))
    y = y + np.where(be > 290.5, 1400 * np.exp(-((be - 292.4) / 1.4) ** 2), 0.0)
    return be, y


class TestNoiLongCasa(unittest.TestCase):
    def test_pho_rong_dung_mo_hinh_noi_long(self):
        be, y = pho_rong()
        chuan = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False, nho_casa=False)
        kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False)
        self.assertGreater(chuan["fit"]["rstd"], 2.0)
        self.assertLess(kq["fit"]["rstd"], 0.8 * chuan["fit"]["rstd"])
        self.assertTrue(any(g.startswith("Mô hình chuẩn không mô tả") for g in kq["ghi"]))
        main = max(kq["fit"]["thanh_phan"], key=lambda c: c["pct"])
        self.assertTrue(284.0 <= main["vt"] <= 285.0, main["vt"])
        self.assertGreater(main["fwhm"], 2.3)
        self.assertLess(kq["tham_so_fit"]["vung"][0], 281.5)       # vùng fit lùi tới nền phẳng
        self.assertTrue(289.5 < kq["tham_so_fit"]["vung"][1] < 291.0)

    def test_pho_hep_khong_bi_noi_long(self):
        for seed in (1, 2):
            be, y = pho(False, seed)
            kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False)
            self.assertFalse(any(g.startswith("Mô hình chuẩn không mô tả") for g in kq["ghi"]))

    def test_bang_thanh_phan_tu_sua_duoc_ton_trong(self):
        be, y = pho_rong()
        tp = [xps.ThanhPhan(**c.dict()) for c in xps.MAU["C1s"][0]]
        tp[0].w_hi = 1.7
        kq = xps.phan_tich_pho(be, y, "C1s", tp=tp, tu_chinh=False)
        self.assertFalse(any(g.startswith("Mô hình chuẩn không mô tả") for g in kq["ghi"]))


if __name__ == "__main__":
    unittest.main()


class TestHinhKieuCasa(unittest.TestCase):
    def test_ve_png(self):
        import tempfile
        be, y = pho(True)
        kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False)
        with tempfile.TemporaryDirectory() as d:
            p = xps.ve_kieu_casa(kq, os.path.join(d, "c.png"), "C1s", 80)
            self.assertTrue(os.path.getsize(p) > 5000)


class TestBoDinhKieuCasa(unittest.TestCase):
    def test_bang_kieu_casa_va_ket_qua(self):
        tp = xps._tp_kieu_casa()
        self.assertEqual([(round(c.vt_lo, 1), round(c.vt_hi, 1)) for c in tp], [(284.0, 285.2), (285.3, 286.1), (286.4, 287.5)])
        be, y = pho_rong()
        kq = xps.phan_tich_pho(be, y, "C1s", tu_chinh=False)
        self.assertEqual(len(kq["fit"]["thanh_phan"]), 3)
        self.assertLess(kq["fit"]["rstd"], 1.6)
