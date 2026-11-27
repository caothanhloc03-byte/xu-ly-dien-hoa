# -*- coding: utf-8 -*-
"""Tests: AURON làm việc trong thư mục (nhận diện, hiểu lệnh, kênh lệnh, điều khiển chạy lần lượt)."""
import json
import os
import queue
import sys
import tempfile
import unittest
import urllib.request

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
import auron_thu_muc as at  # noqa: E402


def ghi(p, nd="x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(nd)


class TestLenh(unittest.TestCase):
    def kt(self, cau, **mong):
        c = at.phan_tich_lenh(cau)
        self.assertIsNotNone(c, cau)
        for k, v in mong.items():
            self.assertEqual(c[k], v, (cau, k))
        return c

    def test_lenh(self):
        self.kt("Chạy toàn bộ data", lenh="chay", tat_ca=True)
        self.kt("chỉ chạy EIS và GCD", lenh="chay", loai=["EIS", "GCD"], tat_ca=False)
        self.kt("hãy vẽ lại LSV", lenh="chay", loai=["LSV"])
        self.kt("chạy thư mục EIS_1", lenh="chay", ten=["eis_1"])
        self.kt("chạy bài 2 và 3", lenh="chay", ten=["2", "3"])
        self.kt("📁 Chọn thư mục làm việc", lenh="chon_thu_muc", duong_dan=None)
        self.kt("mở thư mục D:\\Du lieu\\Dot 1", lenh="chon_thu_muc", duong_dan="D:\\Du lieu\\Dot 1")
        self.kt('mở thư mục "E:\\Số liệu tháng 11"', lenh="chon_thu_muc", duong_dan="E:\\Số liệu tháng 11")
        self.kt("quét lại", lenh="quet")
        self.kt("dừng", lenh="dung")
        self.kt("tiến độ thế nào", lenh="trang_thai")

    def test_khong_phai_lenh(self):
        for c in ("Cách chạy LSV?", "làm sao tính Tafel", "Giải thích kết quả vừa rồi", "cảm ơn", "Bản mới có gì?", "hướng dẫn chạy EIS", "", "  "):
            self.assertIsNone(at.phan_tich_lenh(c), c)

    def test_it_khong_nham_voi_ít(self):
        self.assertEqual(at.phan_tich_lenh("chạy ít dữ liệu thôi")["loai"], [])
        self.assertEqual(at.phan_tich_lenh("vẽ i-t")["loai"], ["IT"])

    def test_chay_thieu_pham_vi_thi_hoi_lai(self):
        c = at.phan_tich_lenh("chạy")
        self.assertIn("toàn bộ hay", at.mo_ta_lenh(c))

    def test_ten_thu_muc(self):
        for ten, mong in (("EIS1", "EIS"), ("OER_LSV_1M", "LSV"), ("ECSA_CV", "ECSA"), ("Stability_IT", "IT"), ("XPS_Ru", "XPS"),
                          ("hr-tem_01", "HRTEM"), ("Du_lieu_tho", None), ("NiO_GCD_23mA", "GCD"), ("XRD", "XRD"), ("Tafel_OER", "TAFEL")):
            self.assertEqual(at.doan_theo_ten(ten), mong, ten)


class TestQuet(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        r = self.t.name
        ghi(os.path.join(r, "EIS_mau1", "a.txt"), "Freq (Hz)\tZ'(Ohm)\n1\t2\n")
        ghi(os.path.join(r, "GCD", "NiO_GCD_23mA_2.0mg.txt"), "t\tV\tI\n")
        ghi(os.path.join(r, "XPS_Ru", "s.vms"), "VAMAS\n")
        ghi(os.path.join(r, "TEM", "a.tif"), "x")
        ghi(os.path.join(r, "Ket_qua_AURON", "EIS", "x.txt"), "bỏ")
        ghi(os.path.join(r, "_sao_luu", "y.txt"), "bỏ")
        ghi(os.path.join(r, "trong", "doc.pdf"), "bỏ")

    def tearDown(self):
        self.t.cleanup()

    def test_quet(self):
        b = at.quet(self.t.name)
        d = {x["ten"]: x for x in b}
        self.assertEqual(set(d), {"EIS_mau1", "GCD", "XPS_Ru", "TEM"})
        self.assertEqual(d["EIS_mau1"]["loai"], "EIS")
        self.assertEqual(d["GCD"]["loai"], "GCD")
        self.assertEqual(d["XPS_Ru"]["loai"], "XPS")
        self.assertEqual(d["TEM"]["loai"], "HRTEM")
        self.assertFalse(d["TEM"]["chay"])
        self.assertIn("HR-TEM", at.tom_tat_ke_hoach(b, self.t.name))

    def test_loc(self):
        b = at.quet(self.t.name)
        self.assertEqual([x["ten"] for x in at.loc_bai(b, {"EIS", "GCD"})], ["EIS_mau1", "GCD"])
        self.assertEqual([x["ten"] for x in at.loc_bai(b, None, ["gcd"])], ["GCD"])
        self.assertEqual(len(at.loc_bai(b)), 3)                       # HR-TEM không tự chạy

    def test_thu_muc_cha_va_noi_dung_mau_thuan(self):
        r = self.t.name
        ghi(os.path.join(r, "LSV", "m1", "1.txt"), "")                # tên cha ghi LSV
        # nội dung giống CV: E đi lên rồi đi xuống
        dong = [f"{e / 100}\t1e-4\t{e}\n" for e in list(range(0, 50)) + list(range(50, 0, -1))]
        ghi(os.path.join(r, "LSV", "m2", "cv.txt"), "".join(dong))
        d = {x["ten"]: x for x in at.quet(r)}
        self.assertEqual(d[os.path.join("LSV", "m2")]["loai"], "AUTO")
        self.assertIn("nội dung giống CV", d[os.path.join("LSV", "m2")]["ghi_chu"])


class TestKenh(unittest.TestCase):
    def test_ghi_lay(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "l.json")
            at.ghi_lenh({"lenh": "quet"}, p)
            at.ghi_lenh({"lenh": "dung"}, p)
            ds = at.lay_lenh(p)
            self.assertEqual([d["lenh"] for d in ds], ["quet", "dung"])
            self.assertEqual(at.lay_lenh(p), [])                      # đã xóa sau khi đọc

    def test_may_chu_post(self):
        import auron_cua_so as au
        with tempfile.TemporaryDirectory() as t:
            os.environ["ECHEM_AURON_LENH"] = os.path.join(t, "l.json")
            httpd, cong = au.khoi_dong_may_chu(cong=0)
            try:
                def post(cau):
                    rq = urllib.request.Request(f"http://127.0.0.1:{cong}/lenh", json.dumps({"cau": cau}).encode(), {"Content-Type": "application/json"})
                    return json.load(urllib.request.urlopen(rq, timeout=5))
                self.assertFalse(post("Cách tính Tafel?")["nhan"])
                r = post("chạy toàn bộ data")
                self.assertTrue(r["nhan"])
                self.assertEqual(at.lay_lenh()[0]["lenh"], "chay")
                self.assertTrue(post("chạy")["nhan"])
                self.assertEqual(at.lay_lenh(), [])                   # thiếu phạm vi: chỉ hỏi lại, không gửi lệnh
            finally:
                httpd.shutdown()
                httpd.server_close()
                os.environ.pop("ECHEM_AURON_LENH", None)

    def test_trang_co_gui_lenh(self):
        with open(os.path.join(GOC, "auron_web", "index.html"), encoding="utf-8") as f:
            s = f.read()
        self.assertIn("fetch('lenh'", s)
        self.assertIn("Chọn thư mục làm việc", s)


class _Bien:
    def __init__(self, v=None):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


class _Root:
    def after(self, ms, f=None, *a):
        if f:
            self.cho.append(f)

    def __init__(self):
        self.cho = []


class _App:
    def __init__(self):
        self.root, self.q = _Root(), queue.Queue()
        self.muc, self.loai, self.thu_muc_ra = [], _Bien("Tự nhận dạng"), _Bien("")
        self.dung_origin, self.dung_csv = _Bien(False), _Bien(True)
        self.dang_chay, self.auron_loi = False, ""
        self.da_chay = []

    def lam_moi_bang(self):
        pass

    def them_cac_file(self, ds):
        self.muc += [dict(path=p) for p in ds]

    def bam_chay(self, tu_dong=False):
        self.da_chay.append((self.loai.get(), [m["path"] for m in self.muc], self.thu_muc_ra.get()))
        if "loi" in os.path.basename(self.thu_muc_ra.get()):
            self.auron_loi = "thiếu thông số"
            return False
        self.dang_chay = True
        return True

    def bam_dung(self):
        pass


class TestDieuKhien(unittest.TestCase):
    def test_chay_lan_luot(self):
        import auron_danh_gia as dg
        import auron_dieu_khien as dk
        with tempfile.TemporaryDirectory() as t:
            os.environ["ECHEM_AURON_SU_KIEN"] = os.path.join(t, "sk.json")
            try:
                ghi(os.path.join(t, "du_lieu", "EIS_1", "a.txt"), "Freq (Hz)\n")
                ghi(os.path.join(t, "du_lieu", "LSV_OER", "b.txt"), "")
                ghi(os.path.join(t, "du_lieu", "LSV_loi", "c.txt"), "")
                ghi(os.path.join(t, "du_lieu", "TEM", "d.tif"), "")
                app = _App()
                muc_cu = [dict(path="cu")]
                app.muc = list(muc_cu)
                d = dk.DieuKhien(app, ["Tự nhận dạng", "LSV", "CV", "IT", "EIS", "ECSA (nhiều file CV)", "Tafel"])
                d.xu_ly(dict(lenh="chay", tat_ca=True, loai=[], ten=[]))       # chưa có thư mục
                self.assertFalse(d.dang)
                d.xu_ly(dict(lenh="chon_thu_muc", duong_dan=os.path.join(t, "du_lieu")))
                self.assertEqual(len(d.bai), 4)
                d.xu_ly(dict(lenh="chay", tat_ca=False, loai=[], ten=[]))        # thiếu phạm vi
                self.assertFalse(d.dang)
                d.xu_ly(dict(lenh="chay", tat_ca=True, loai=[], ten=[]))
                self.assertTrue(d.dang)
                for _ in range(40):                                               # mô phỏng vòng sự kiện của Tk
                    while app.root.cho:
                        app.root.cho.pop(0)()
                    if app.dang_chay:
                        app.dang_chay = False
                        d.sau_chay("thanh_cong", "")
                    if not d.dang:
                        break
                self.assertFalse(d.dang)
                self.assertEqual(len(app.da_chay), 3)
                self.assertEqual(sorted(x[0] for x in app.da_chay), ["EIS", "LSV", "LSV"])
                ok = [r["ok"] for r in d.ket_qua]
                self.assertEqual(ok.count(False), 1)                              # LSV_loi bị lỗi nhưng không dừng cả loạt
                self.assertEqual(app.muc, muc_cu)                                 # trạng thái bảng được khôi phục
                self.assertTrue(os.path.isfile(os.path.join(t, "du_lieu", at.TEN_KET_QUA, "tom_tat_AURON.txt")))
                cuoi = dg.doc_su_kien(0)[-1]
                self.assertEqual(cuoi["tieu_de"], "Hoàn thành loạt dữ liệu")
                self.assertIn("2 thành công, 1 lỗi", cuoi["chi_tiet"])
            finally:
                os.environ.pop("ECHEM_AURON_SU_KIEN", None)

    def test_dung(self):
        import auron_dieu_khien as dk
        with tempfile.TemporaryDirectory() as t:
            os.environ["ECHEM_AURON_SU_KIEN"] = os.path.join(t, "sk.json")
            try:
                ghi(os.path.join(t, "EIS_1", "a.txt"), "")
                ghi(os.path.join(t, "EIS_2", "a.txt"), "")
                app = _App()
                d = dk.DieuKhien(app, ["Tự nhận dạng", "EIS"])
                d.xu_ly(dict(lenh="chon_thu_muc", duong_dan=t))
                d.xu_ly(dict(lenh="chay", tat_ca=True, loai=[], ten=[]))
                while app.root.cho:
                    app.root.cho.pop(0)()
                d.xu_ly(dict(lenh="dung"))
                app.dang_chay = False
                d.sau_chay("dung", "")
                while app.root.cho:
                    app.root.cho.pop(0)()
                self.assertFalse(d.dang)
                self.assertEqual(len(app.da_chay), 1)                             # bài thứ 2 bị hủy
            finally:
                os.environ.pop("ECHEM_AURON_SU_KIEN", None)


@unittest.skipUnless(__import__("importlib").util.find_spec("numpy"), "thiếu numpy")
class TestChayRieng(unittest.TestCase):
    def test_gcd_khong_co_khoi_luong_thi_bao_ro(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "GCD", "x_GCD_5mA.txt")
            ghi(p, "t\tV\tI\n0\t0\t0.005\n")
            job = dict(ten="GCD", files=[p], loai="GCD")
            with self.assertRaises(ValueError) as cm:
                at.chay_gcd(job, os.path.join(t, "out"))
            self.assertIn("khối lượng", str(cm.exception))

    def test_xps_khong_co_vung_khop(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "XPS", "a.txt")
            ghi(p, "khong phai xps\n")
            with self.assertRaises(Exception):
                at.chay_xps(dict(ten="XPS", files=[p], loai="XPS"), os.path.join(t, "out"))


if __name__ == "__main__":
    unittest.main()
