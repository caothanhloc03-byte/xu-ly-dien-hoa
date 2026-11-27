# -*- coding: utf-8 -*-
"""
Phía app của "AURON làm việc trong thư mục": đọc lệnh AURON gửi (mỗi giây), quét thư mục, rồi chạy LẦN LƯỢT từng bài.
  • CV/LSV/IT/EIS/ECSA/Tafel/tự nhận dạng: dùng chính đường chạy của app (đúng thông số đang đặt trong cửa sổ chính: pH, Eref, diện tích, bù iR, Origin...).
  • GCD/XPS/XRD: chạy không cửa sổ bằng thiết lập mặc định (auron_thu_muc.CHAY_RIENG) trong luồng nền.
Mọi kết quả vào <thư mục>/Ket_qua_AURON; mọi lỗi của một bài được ghi lại và chạy tiếp các bài sau. Tiến độ và nhận xét hiện trong cửa sổ AURON.
"""
import datetime
import os
import re
import threading
import time

import auron_danh_gia as ag
import auron_thu_muc as at

NGUON = "Thư mục làm việc"


class DieuKhien:
    def __init__(self, app, bang_loai):
        """bang_loai: danh sách LOAI của giao diện (để đặt 'Loại phép đo')."""
        self.app = app
        self.bang_loai = bang_loai
        self.goc = None
        self.bai = []
        self.hang = []
        self.tong = 0
        self.dang = False
        self.hien = None
        self.ket_qua = []
        self.luu = None
        self.t0 = 0.0
        self.huy = False

    # ---------- vòng nhận lệnh ----------
    def bat_dau(self):
        self.app.root.after(1000, self._vong)

    def _vong(self):
        try:
            for lenh in at.lay_lenh():
                try:
                    self.xu_ly(lenh)
                except Exception as e:  # noqa: BLE001
                    self.phat("Lỗi khi thực hiện lệnh", "confused", f"Không thực hiện được lệnh: {e}")
        finally:
            self.app.root.after(1000, self._vong)

    def phat(self, tieu_de, mood, chi_tiet, tom_tat=None):
        ag.ghi_su_kien(dict(nguon=NGUON, tieu_de=tieu_de, mood=mood, tom_tat=tom_tat or chi_tiet.split("\n")[0][:160], chi_tiet=chi_tiet))
        self.app.q.put(f"[AURON · thư mục làm việc] {tieu_de}\n")

    # ---------- lệnh ----------
    def xu_ly(self, lenh):
        k = lenh.get("lenh")
        if k == "chon_thu_muc":
            p = lenh.get("duong_dan")
            if not p:
                try:
                    self.app.root.lift()
                except Exception:  # noqa: BLE001
                    pass
                from tkinter import filedialog
                p = filedialog.askdirectory(title="Chọn thư mục làm việc cho AURON", parent=self.app.root)
                if not p:
                    self.phat("Chưa chọn thư mục", "neutral", "Ngài chưa chọn thư mục nào. Khi sẵn sàng, bấm '📁 Chọn thư mục' hoặc gõ: mở thư mục D:\\Du_lieu")
                    return
            self.dat_thu_muc(p)
        elif k == "quet":
            if not self.goc:
                self.phat("Chưa có thư mục", "confused", "Chưa có thư mục làm việc. Bấm '📁 Chọn thư mục' hoặc gõ: mở thư mục D:\\Du_lieu")
                return
            self.dat_thu_muc(self.goc)
        elif k == "chay":
            self.lenh_chay(lenh)
        elif k == "dung":
            self.dung_lai()
        elif k == "trang_thai":
            self.bao_tien_do()

    def dat_thu_muc(self, p):
        p = os.path.normpath(p.strip().strip('"'))
        if not os.path.isdir(p):
            self.phat("Không tìm thấy thư mục", "confused", f"Không có thư mục: {p}\nNgài kiểm tra lại đường dẫn (ổ mạng có thể chưa kết nối).")
            return
        if self.dang:
            self.phat("Đang chạy dở", "thinking", "Đang chạy một loạt dữ liệu. Ngài gõ 'dừng' trước nếu muốn đổi thư mục.")
            return
        self.goc = p
        self.bai = at.quet(p)
        n_chay = sum(1 for b in self.bai if b["chay"])
        mood = "happy" if n_chay else "confused"
        goi_y = ("\nNgài gõ: 'chạy toàn bộ data' hoặc 'chỉ chạy EIS và GCD' hoặc 'chạy thư mục <tên>'." if n_chay else "")
        self.phat("Đã nhận diện thư mục", mood, at.tom_tat_ke_hoach(self.bai, p) + goi_y,
                  tom_tat=f"Đã nhận diện {len(self.bai)} thư mục dữ liệu, {n_chay} thư mục chạy được." if self.bai else "Thư mục này chưa có dữ liệu tôi nhận ra.")

    def lenh_chay(self, lenh):
        if not self.goc:
            self.phat("Chưa có thư mục", "confused", "Ngài chưa chỉ định thư mục. Bấm '📁 Chọn thư mục' hoặc gõ: mở thư mục D:\\Du_lieu")
            return
        if self.dang or self.app.dang_chay:
            self.phat("App đang bận", "thinking", "Echem Studio đang xử lý một việc khác. Ngài đợi xong hoặc gõ 'dừng'.")
            return
        loai, ten = set(lenh.get("loai") or []), lenh.get("ten") or []
        if not (lenh.get("tat_ca") or loai or ten):
            self.phat("Cần nói rõ phạm vi", "confused", "Ngài muốn chạy toàn bộ hay chỉ một số phép đo? Ví dụ: 'chạy toàn bộ data', 'chỉ chạy EIS và GCD', 'chạy thư mục EIS_1'.")
            return
        self.bai = at.quet(self.goc)                     # quét lại để bắt file mới thêm
        ds = at.loc_bai(self.bai, loai or None, ten or None)
        bo = [b for b in self.bai if not b["chay"] and (not loai or b["loai"] in loai)]
        if not ds:
            self.phat("Không có bài phù hợp", "confused", "Không có thư mục nào khớp yêu cầu.\n" + at.tom_tat_ke_hoach(self.bai, self.goc))
            return
        self.hang, self.tong, self.ket_qua, self.huy = list(ds), len(ds), [], False
        self.luu = dict(muc=list(self.app.muc), loai=self.app.loai.get(), ra=self.app.thu_muc_ra.get(), csv=self.app.dung_csv.get())
        self.dang, self.t0 = True, time.time()
        dong = [f"Bắt đầu chạy {len(ds)} bài lần lượt:"] + [f"{b['id']}. {b['ten']} → {at.LOAI_HIEN.get(b['loai'], b['loai'])} ({b['so_file']} file)" for b in ds]
        if bo:
            dong.append("Không tự chạy: " + ", ".join(f"{b['ten']} ({at.LOAI_HIEN.get(b['loai'], b['loai'])})" for b in bo) + " (xem ghi chú ở bước nhận diện).")
        if self.app.dung_origin.get():
            dong.append("Lưu ý: ô 'Vẽ bằng Origin' đang bật nên mỗi bài CV/LSV/IT/EIS sẽ mở Origin; bỏ tick nếu chỉ cần hình Matplotlib/CSV.")
        dong.append("Thông số quy đổi (pH, Eref, diện tích, bù iR...) lấy theo cửa sổ chính; GCD/XPS/XRD dùng thiết lập mặc định.")
        self.phat("Bắt đầu chạy", "happy", "\n".join(dong), tom_tat=f"Bắt đầu chạy {len(ds)} bài trong thư mục làm việc.")
        self.app.root.after(300, self.tiep)

    def dung_lai(self):
        if not self.dang:
            self.phat("Không có việc đang chạy", "neutral", "Hiện không có loạt nào đang chạy.")
            return
        self.huy = True
        self.hang = []
        if self.hien and self.hien["loai"] in at.LOAI_DUONG_APP:
            try:
                self.app.bam_dung()
            except Exception:  # noqa: BLE001
                pass
        self.phat("Đang dừng", "neutral", "Sẽ dừng sau bài đang chạy; các bài chưa chạy bị hủy.")

    def bao_tien_do(self):
        if not self.dang:
            self.phat("Tiến độ", "neutral", "Hiện không có loạt nào đang chạy." + (f"\nThư mục làm việc: {self.goc}" if self.goc else ""))
            return
        xong = len(self.ket_qua)
        self.phat("Tiến độ", "thinking", f"Đã xong {xong}/{self.tong} bài; đang chạy: {self.hien['ten'] if self.hien else '—'}; còn {len(self.hang)} bài chờ.")

    # ---------- chạy lần lượt ----------
    def tiep(self):
        if self.huy or not self.hang:
            self.ket_thuc()
            return
        job = self.hang.pop(0)
        self.hien = job
        stt = self.tong - len(self.hang)
        self.phat(f"[{stt}/{self.tong}] {job['ten']}", "thinking", f"Đang chạy bài {stt}/{self.tong}: {job['ten']} ({at.LOAI_HIEN.get(job['loai'], job['loai'])}, {job['so_file']} file).",
                  tom_tat=f"Đang chạy {job['ten']}, bài {stt} trên {self.tong}.")
        goc_ra = os.path.join(self.goc, at.TEN_KET_QUA)
        try:
            os.makedirs(goc_ra, exist_ok=True)
        except OSError as e:
            self.xong_bai(job, False, f"Không tạo được thư mục kết quả: {e}")
            return
        if job["loai"] in at.LOAI_DUONG_APP:
            self.chay_duong_app(job, goc_ra)
        else:
            f = at.CHAY_RIENG.get(job["loai"])
            if f is None:
                self.xong_bai(job, False, "Chưa hỗ trợ chạy tự động loại này.")
                return

            def lam():
                try:
                    r = f(job, goc_ra)
                    ok, tom = True, r["tom_tat"] + ("; tạo " + ", ".join(r["tep"][:4]) + (" ..." if len(r["tep"]) > 4 else "") if r["tep"] else "")
                    if r["loi"]:
                        tom += "\n   Lưu ý: " + " | ".join(r["loi"][:4])
                    tom += f"\n   Kết quả: {r['thu_muc_ra']}"
                except Exception as e:  # noqa: BLE001
                    ok, tom = False, str(e)
                self.app.q.put(("auron_xong_rieng", job["id"], ok, tom))
            threading.Thread(target=lam, daemon=True).start()

    def chay_duong_app(self, job, goc_ra):
        a = self.app
        ten_an_toan = re.sub(r"[^\w\-. ]+", "_", job["ten"]).strip() or "bai"
        ra = os.path.join(goc_ra, ten_an_toan)
        os.makedirs(ra, exist_ok=True)
        anh_xa = {"CV": "CV", "LSV": "LSV", "IT": "IT", "EIS": "EIS"}
        if job["loai"] in anh_xa:
            dat = next((x for x in self.bang_loai if x == anh_xa[job["loai"]]), self.bang_loai[0])
        elif job["loai"] == "ECSA":
            dat = next(x for x in self.bang_loai if x.startswith("ECSA"))
        elif job["loai"] == "TAFEL":
            dat = next(x for x in self.bang_loai if x == "Tafel")
        else:
            dat = self.bang_loai[0]
        a.muc.clear()
        a.them_cac_file(job["files"])
        a.loai.set(dat)
        a.thu_muc_ra.set(ra)
        if not (a.dung_origin.get() or a.dung_csv.get()):
            a.dung_csv.set(True)
        a.auron_loi = ""
        job["ra"] = ra
        if not a.bam_chay(tu_dong=True):
            self.xong_bai(job, False, a.auron_loi or "App không bắt đầu chạy được (kiểm tra thông số trong cửa sổ chính).")

    def sau_chay(self, ket, log=""):
        """Gọi khi app báo 'chay_xong' trong lúc đang chạy loạt."""
        if not self.dang or not self.hien or self.hien["loai"] not in at.LOAI_DUONG_APP:
            return
        job = self.hien
        if ket == "thanh_cong":
            self.xong_bai(job, True, f"Kết quả: {job.get('ra', '')}")
        else:
            dong = [d for d in (log or "").splitlines() if d.startswith("[LỖI")]
            self.xong_bai(job, False, (dong[0] if dong else "Có lỗi khi chạy" if ket != "dung" else "Đã dừng"))

    def sau_rieng(self, id_bai, ok, tom):
        if self.dang and self.hien and self.hien["id"] == id_bai:
            self.xong_bai(self.hien, ok, tom)

    def xong_bai(self, job, ok, tom):
        self.ket_qua.append(dict(job=job, ok=ok, tom=tom))
        self.phat(f"{'Xong' if ok else 'Lỗi'}: {job['ten']}", "happy" if ok else "confused",
                  f"{job['ten']} ({at.LOAI_HIEN.get(job['loai'], job['loai'])}): " + ("hoàn thành. " if ok else "KHÔNG chạy được: ") + tom,
                  tom_tat=f"{job['ten']} " + ("xong." if ok else "gặp lỗi, tôi chạy tiếp bài sau."))
        self.hien = None
        self.app.root.after(700, self.tiep)

    def ket_thuc(self):
        a = self.app
        try:
            if self.luu:
                a.muc[:] = self.luu["muc"]
                a.loai.set(self.luu["loai"])
                a.thu_muc_ra.set(self.luu["ra"])
                a.dung_csv.set(self.luu["csv"])
                a.lam_moi_bang()
        except Exception:  # noqa: BLE001
            pass
        self.dang = False
        so_ok = sum(1 for r in self.ket_qua if r["ok"])
        dong = [f"Đã chạy {len(self.ket_qua)} bài trong {time.time() - self.t0:.0f} giây: {so_ok} thành công, {len(self.ket_qua) - so_ok} lỗi."
                + (" (đã dừng theo lệnh)" if self.huy else "")]
        for r in self.ket_qua:
            dong.append(("✓ " if r["ok"] else "✗ ") + f"{r['job']['ten']} [{at.LOAI_HIEN.get(r['job']['loai'], r['job']['loai'])}]: " + r["tom"].split("\n")[0][:200])
        dong.append("Kết quả nằm trong: " + os.path.join(self.goc or "", at.TEN_KET_QUA))
        van_ban = "\n".join(dong)
        try:
            with open(os.path.join(self.goc, at.TEN_KET_QUA, "tom_tat_AURON.txt"), "w", encoding="utf-8") as f:
                f.write(f"Echem Studio · AURON · {datetime.datetime.now():%Y-%m-%d %H:%M}\n\n" + van_ban + "\n")
        except OSError:
            pass
        self.hien, self.hang = None, []
        self.phat("Hoàn thành loạt dữ liệu", "happy" if so_ok == len(self.ket_qua) and so_ok else "thinking", van_ban,
                  tom_tat=f"Xong {len(self.ket_qua)} bài: {so_ok} thành công" + (f", {len(self.ket_qua) - so_ok} lỗi." if len(self.ket_qua) > so_ok else "."))
