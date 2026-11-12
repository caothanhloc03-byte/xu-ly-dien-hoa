# -*- coding: utf-8 -*-
"""Cửa sổ XPS: mở file CasaXPS (.vms / text / Excel) -> hiệu chuẩn C1s = 284.8 -> fit thành phần có ràng buộc hoá học -> xuất CSV/hình
-> vẽ ra Origin. Lõi tính toán nằm ở xps.py."""
import json
import os
import subprocess
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np

import xps


class CuaSoXps:
    def __init__(self, root, lenh_origin=None):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.root = root
        self.lenh_origin = lenh_origin           # hàm trả về list lệnh con chạy ve_xps_origin (None = không có Origin)
        self.vung = []                           # các vùng đọc từ file
        self.kq = None
        self.duong_dan = ""
        w = self.w = tk.Toplevel(root)
        w.title("Phổ XPS: hiệu chuẩn, fit thành phần, vẽ Origin")
        w.geometry("1180x820")

        self.v_file = tk.StringVar(value="(chưa mở file)")
        self.v_vung = tk.StringVar()
        self.v_ten = tk.StringVar(value="C1s")
        self.v_chuan = tk.StringVar(value="284.8")
        self.v_do_tu = tk.StringVar(value="290")
        self.v_do_den = tk.StringVar(value="280")
        self.v_fit_tu = tk.StringVar(value="281.5")
        self.v_fit_den = tk.StringVar(value="291.0")
        self.v_t = tk.StringVar(value="")
        self.v_dw = tk.StringVar(value=f"{xps.DW_FWHM:g}")
        self.v_dich = tk.StringVar(value="")                 # dịch năng lượng đã biết (từ C1s); để trống = tự hiệu chuẩn
        self.dich_c1s = None
        self.cm = None                                       # kết quả 'chứng minh' (kiểm định thống kê) của lần fit hiện tại
        self.kieu = None                                     # kiểu vẽ (màu/tô vùng) do người dùng chọn
        self.cuoi_ts = {}
        self.v_nen = tk.StringVar(value="Shirley")
        self.v_mau = tk.StringVar(value="C1s")
        self.v_tu_chon = tk.BooleanVar(value=True)
        self.v_casa = tk.BooleanVar(value=True)
        self.v_tom_tat = tk.StringVar(value="")
        self.v_giu_be_casa = tk.BooleanVar(value=True)
        self.v_tt = tk.StringVar(value="Mở file .vms (CasaXPS) hoặc file text/Excel xuất từ CasaXPS.")

        f1 = ttk.Frame(w)
        f1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(f1, text="Mở file XPS...", command=self.mo_file).pack(side="left")
        ttk.Label(f1, textvariable=self.v_file, foreground="#444").pack(side="left", padx=6)
        ttk.Label(f1, text="Vùng:").pack(side="left", padx=(10, 1))
        self.cb_vung = ttk.Combobox(f1, textvariable=self.v_vung, width=34, state="readonly")
        self.cb_vung.pack(side="left")
        self.cb_vung.bind("<<ComboboxSelected>>", self.chon_vung)
        ttk.Label(f1, text="Tên hình:").pack(side="left", padx=(10, 1))
        ttk.Entry(f1, textvariable=self.v_ten, width=14).pack(side="left")

        f2 = ttk.Frame(w)
        f2.pack(fill="x", padx=6, pady=2)
        ttk.Label(f2, text="Hiệu chuẩn: đỉnh cao nhất trong").pack(side="left")
        ttk.Entry(f2, textvariable=self.v_do_tu, width=6).pack(side="left", padx=2)
        ttk.Label(f2, text="–").pack(side="left")
        ttk.Entry(f2, textvariable=self.v_do_den, width=6).pack(side="left", padx=2)
        ttk.Label(f2, text="eV  →  về").pack(side="left")
        ttk.Entry(f2, textvariable=self.v_chuan, width=7).pack(side="left", padx=2)
        ttk.Label(f2, text="eV").pack(side="left")
        f2b = ttk.Frame(w)
        f2b.pack(fill="x", padx=6, pady=2)
        ttk.Label(f2b, text="Vùng fit:").pack(side="left")
        ttk.Entry(f2b, textvariable=self.v_fit_tu, width=6).pack(side="left", padx=2)
        ttk.Label(f2b, text="–").pack(side="left")
        ttk.Entry(f2b, textvariable=self.v_fit_den, width=6).pack(side="left", padx=2)
        ttk.Label(f2b, text="   Nền:").pack(side="left")
        ttk.Combobox(f2b, textvariable=self.v_nen, values=["Shirley", "Tougaard U2", "Tuyến tính"], width=10, state="readonly").pack(side="left", padx=2)
        ttk.Label(f2b, text="   dwell×scan (s):").pack(side="left")
        ttk.Entry(f2b, textvariable=self.v_t, width=7).pack(side="left", padx=2)

        # ---- thiết lập thành phần: thu gọn được ----
        self.v_mo_nang = tk.BooleanVar(value=False)
        fk = ttk.Frame(w)
        fk.pack(fill="x", padx=6, pady=(2, 0))
        self.btn_nang = ttk.Button(fk, text="⚙ Thiết lập thành phần ▸", command=self._bat_tat_nang)
        self.btn_nang.pack(side="left")
        ttk.Label(fk, textvariable=self.v_tom_tat, foreground="#666").pack(side="left", padx=8)
        self.fx = ttk.Frame(w)
        f3 = ttk.Frame(self.fx)
        f3.pack(fill="x", pady=2)
        ttk.Label(f3, text="Mẫu:").pack(side="left")
        ttk.Combobox(f3, textvariable=self.v_mau, values=sorted(xps.MAU), width=8, state="readonly").pack(side="left", padx=2)
        ttk.Button(f3, text="Nạp mẫu", command=self.nap_mau).pack(side="left", padx=2)
        ttk.Label(f3, text="Dịch sẵn (eV):").pack(side="left", padx=(8, 1))
        ttk.Entry(f3, textvariable=self.v_dich, width=7).pack(side="left")
        ttk.Label(f3, text="Chênh FWHM tối đa (eV, 0=tắt):").pack(side="left", padx=(8, 1))
        ttk.Entry(f3, textvariable=self.v_dw, width=5).pack(side="left")
        ttk.Checkbutton(f3, text="Tự thêm thành phần ứng viên (C=O, π-π*)", variable=self.v_tu_chon).pack(side="left", padx=8)
        ttk.Label(self.fx, text="Mỗi dòng: " + xps.CAU_TRUC_DONG, foreground="#666").pack(fill="x")
        self.txt_tp = tk.Text(self.fx, height=5, font=("Consolas", 10))
        self.txt_tp.pack(fill="x", pady=2)
        self.nap_mau()

        # ---- thanh công cụ gọn: nút chính + menu ----
        f4 = ttk.Frame(w)
        f4.pack(fill="x", padx=6, pady=4)
        self._nut(f4, "▶ Fit", self.fit, "Hiệu chuẩn + Fit").pack(side="left")
        self._nut(f4, "✓ Chứng minh", self.chung_minh, "Chứng minh kết quả (F-test, phần dư, Monte Carlo, đề xuất phương án)").pack(side="left", padx=3)
        self._nut(f4, "⬆ Origin", self.ve_origin, "Vẽ ra Origin (tick bên phải: xuất luôn sang CasaXPS)").pack(side="left")
        self._nut(f4, "💾 Xuất", self.xuat, "Xuất CSV + hình").pack(side="left", padx=3)
        mc = self._menu(f4, "◧ Casa ▾", "Các thao tác với CasaXPS")
        for t, c in (("Xuất sang CasaXPS...", self.xuat_casa), ("Nhận kết quả từ Casa...", self.nhan_tu_casa), ("Nhận kết quả + bảng số Casa (.txt)...", self.nhan_tu_casa_kem_bang), ("Vẽ Origin từ file Casa...", self.ve_origin_tu_casa),
                     ("So với Casa...", self.so_voi_casa)):
            mc.add_command(label=t, command=c)
        mt = self._menu(f4, "🛠 Công cụ ▾", "Chọn vùng bằng chuột, màu, dịch, RSF, lưu/nạp mô hình")
        for t, c in (("Kéo chuột chọn vùng fit", lambda: self.chon_chuot("fit")), ("Kéo chuột chọn khoảng dò đỉnh", lambda: self.chon_chuot("do")),
                     (None, None), ("Màu & tô vùng...", self.chon_kieu), ("Dùng dịch này cho vùng khác", self.giu_dich),
                     ("Định lượng nguyên tố (RSF)...", self.dinh_luong), (None, None),
                     ("Lưu mô hình...", self.luu_mo_hinh), ("Nạp mô hình...", self.nap_mo_hinh)):
            mt.add_separator() if t is None else mt.add_command(label=t, command=c)
        ttk.Checkbutton(f4, text="Origin kèm Casa", variable=self.v_casa).pack(side="left", padx=8)
        ttk.Checkbutton(f4, text="Giữ BE đúng như Casa (không ép C-C về chuẩn)", variable=self.v_giu_be_casa).pack(side="left", padx=4)

        than = ttk.PanedWindow(w, orient="horizontal")
        than.pack(fill="both", expand=True, padx=6, pady=2)
        trai = ttk.Frame(than)
        phai = ttk.Frame(than, width=380)
        than.add(trai, weight=3)
        than.add(phai, weight=2)
        self.fig = Figure(figsize=(6.4, 5.2), dpi=100)
        gs = self.fig.add_gridspec(4, 1, hspace=0.12)
        self.ax = self.fig.add_subplot(gs[:3, 0])
        self.ax_r = self.fig.add_subplot(gs[3, 0], sharex=self.ax)
        self.cv = FigureCanvasTkAgg(self.fig, master=trai)
        self.cv.get_tk_widget().pack(fill="both", expand=True)
        self.txt_kq = tk.Text(phai, height=20, font=("Consolas", 10), wrap="word")
        self.txt_kq.pack(fill="both", expand=True)
        ttk.Label(w, textvariable=self.v_tt, foreground="#444", wraplength=1000, justify="left").pack(fill="x", padx=8, pady=(0, 6))

    # ---------- giao diện gọn ----------
    def _nut(self, cha, text, cmd, goi_y="", _=None):
        b = ttk.Button(cha, text=text, command=cmd)
        self._goi_y(b, goi_y)
        return b

    def _menu(self, cha, text, goi_y=""):
        mb = ttk.Menubutton(cha, text=text)
        m = tk.Menu(mb, tearoff=0)
        mb["menu"] = m
        mb.pack(side="left", padx=3)
        self._goi_y(mb, goi_y)
        return m

    def _goi_y(self, wd, text):
        if not text:
            return
        tip = {"w": None}

        def hien(_e):
            t = tk.Toplevel(wd)
            t.wm_overrideredirect(True)
            t.wm_geometry(f"+{wd.winfo_rootx()}+{wd.winfo_rooty() + wd.winfo_height() + 2}")
            tk.Label(t, text=text, background="#ffffe0", relief="solid", borderwidth=1, padx=4, pady=2).pack()
            tip["w"] = t

        def an(_e):
            if tip["w"] is not None:
                tip["w"].destroy()
                tip["w"] = None
        wd.bind("<Enter>", hien, add="+")
        wd.bind("<Leave>", an, add="+")
        wd.bind("<ButtonPress>", an, add="+")

    def _bat_tat_nang(self):
        mo = not self.v_mo_nang.get()
        self.v_mo_nang.set(mo)
        if mo:
            self.fx.pack(fill="x", padx=6, pady=2, after=self.btn_nang.master)
        else:
            self.fx.pack_forget()
        self.btn_nang.configure(text="⚙ Thiết lập thành phần " + ("▾" if mo else "▸"))

    # ---------- nhập liệu ----------
    @staticmethod
    def _so(var, ten):
        try:
            return float(str(var.get()).replace(",", "."))
        except ValueError:
            raise ValueError(f"'{ten}' phải là số.")

    def mo_file(self):
        p = filedialog.askopenfilename(parent=self.w, title="Chọn file XPS",
                                       filetypes=[("XPS", "*.vms *.txt *.csv *.xlsx *.dat *.asc"), ("Tất cả", "*.*")])
        if p:
            self.nap_file(p)

    def nap_file(self, p):
        try:
            self.vung = xps.doc_xps(p)
        except Exception as e:
            messagebox.showerror("XPS", f"Không đọc được file:\n{e}", parent=self.w)
            return
        self.duong_dan = p
        self.v_file.set(os.path.basename(p))
        mo_ta = [f"{v['ten']}  [{v['be'].max():.1f}–{v['be'].min():.1f} eV, {len(v['be'])} điểm]" for v in self.vung]
        self.cb_vung.configure(values=mo_ta)
        i = 0
        for k, v in enumerate(self.vung):                     # ưu tiên vùng chứa C1s (284.8 ± 6)
            if v["be"].min() < 280 and v["be"].max() > 292 and v["be"].max() < 300:
                i = k
                break
        self.v_vung.set(mo_ta[i])
        self.chon = i
        self.v_ten.set(self.vung[i]["ten"].replace(" ", "")[:20] or "C1s")
        v0 = self.vung[i]
        if v0.get("dwell") and v0.get("scans") and v0["dwell"] < 100:      # dwell x scan lấy thẳng từ file VAMAS
            self.v_t.set(f"{v0['dwell'] * v0['scans']:.4g}")
        self.ve_tho()
        self.v_tt.set(f"Đã đọc {len(self.vung)} vùng. Chọn vùng C1s (khoảng 296–280 eV) rồi bấm 'Hiệu chuẩn + Fit'.")

    def chon_vung(self, _e=None):
        try:
            self.chon = list(self.cb_vung.cget("values")).index(self.v_vung.get())
        except Exception:
            self.chon = 0
        self.v_ten.set(self.vung[self.chon]["ten"].replace(" ", "")[:20])
        v0 = self.vung[self.chon]
        if v0.get("dwell") and v0.get("scans") and v0["dwell"] < 100:
            self.v_t.set(f"{v0['dwell'] * v0['scans']:.4g}")
        self.kq = None
        self.ve_tho()

    def nap_mau(self):
        ten = self.v_mau.get()
        ds = xps.MAU[ten][0]
        self.txt_tp.delete("1.0", "end")
        self.txt_tp.insert("1.0", xps.mo_ta_thanh_phan(ds))
        self.v_tom_tat.set(f"Mẫu {ten}: " + ", ".join(c.ten.split(" /")[0] for c in ds))
        cfg = xps.VUNG_MAU.get(ten)
        if cfg and hasattr(self, "v_fit_tu"):
            self.v_fit_tu.set(f"{cfg['vung'][0]:g}")
            self.v_fit_den.set(f"{cfg['vung'][1]:g}")
            if cfg["khoang"]:
                self.v_do_tu.set(f"{cfg['khoang'][0]:g}")
                self.v_do_den.set(f"{cfg['khoang'][1]:g}")
            if cfg["ref"]:
                self.v_chuan.set(f"{cfg['ref']:g}")
        if hasattr(self, "ax"):
            self.ve_tho()

    # ---------- fit ----------
    def doc_tham_so(self):
        tp = xps.doc_dong_thanh_phan(self.txt_tp.get("1.0", "end"))
        t = self.v_t.get().strip()
        return {"tp": tp, "dich": self._so(self.v_chuan, "Năng lượng chuẩn"),
                "khoang": (self._so(self.v_do_tu, "Khoảng tìm đỉnh"), self._so(self.v_do_den, "Khoảng tìm đỉnh")),
                "vung": (self._so(self.v_fit_tu, "Vùng fit từ"), self._so(self.v_fit_den, "Vùng fit đến")),
                "nen": self._nen(),
                "t": float(t.replace(",", ".")) if t else None, "tu_chon": bool(self.v_tu_chon.get()),
                "dw": self._so(self.v_dw, "Chênh FWHM tối đa"), "bang_tp": self.txt_tp.get("1.0", "end").strip(),
                "dich_san": self._dich_san()}

    def _nen(self):
        t = self.v_nen.get().lower()
        return "shirley" if t.startswith("shirley") else "tougaard" if t.startswith("tougaard") else "tuyen_tinh"

    def _dich_san(self):
        t = self.v_dich.get().strip()
        if t:
            return float(t.replace(",", "."))
        if not (xps.VUNG_MAU.get(self.v_mau.get()) or {}).get("ten_ref"):        # mẫu không có đỉnh chuẩn: cần dịch từ C1s
            if self.dich_c1s is not None:
                return self.dich_c1s
            return 0.0
        return None

    def chay_fit(self, v, ts):
        mau = self.v_mau.get()
        uv = [xps.ThanhPhan(**c.dict()) for c in xps.MAU.get(mau, ([], []))[1]] if ts["tu_chon"] else []
        return xps.phan_tich_pho(v["be"], v["y"], mau, tp=ts["tp"], ung_vien=uv, vung=ts["vung"], dich_chuan=ts["dich"],
                                 khoang_do=ts["khoang"], nen=ts["nen"], t_thu=ts["t"], tu_chon=ts["tu_chon"], dw_fwhm=ts.get("dw", xps.DW_FWHM),
                                 dich_san=ts.get("dich_san"),
                                 tp_chuan_theo=(xps.VUNG_MAU.get(mau) or {}).get("ten_ref") or "C-C")

    def fit(self):
        if not self.vung:
            messagebox.showinfo("XPS", "Hãy mở file XPS trước.", parent=self.w)
            return
        try:
            ts = self.doc_tham_so()
            self.kq = self.chay_fit(self.vung[getattr(self, "chon", 0)], ts)
            self.cuoi_ts = ts
            self.cm = None
        except Exception as e:
            messagebox.showerror("XPS", str(e), parent=self.w)
            return
        self.hien_ket_qua()

    def hien_ket_qua(self):
        kq = self.kq
        f = kq["fit"]
        self.ax.clear()
        self.ax_r.clear()
        b = kq["be"]
        o = np.argsort(b)
        self.ax.plot(b[o], kq["ys"][o], ".", ms=2.5, color="#888", zorder=1)
        xps.ve_len_truc(self.ax, kq, "", False, None, self.kieu)
        self.ax.set_xlabel("")
        self.ax.tick_params(labelbottom=False)
        self.ax_r.plot(b[o], f["phan_du"][o], color="#b2182b", lw=0.8)
        self.ax_r.axhline(0, color="#999", lw=0.6)
        self.ax_r.set_yticks([])
        self.ax_r.set_xlabel("Binding Energy (eV)")
        self.ax_r.set_ylabel("Phần dư", fontsize=8)
        self.cv.draw_idle()
        dong = [f"Dịch hiệu chuẩn: {kq['dich_hieu_chuan']:+.3f} eV" + (f" (C-C về {self._so(self.v_chuan, 'chuẩn'):.2f} eV)" if self.cuoi_ts.get("dich_san") is None else " (dịch đã biết)"),
                f"Residual STD = {f['rstd']:.2f}   (tự tương quan phần dư {f['tu_tuong_quan']:+.2f})", "",
                f"{'Thành phần':<20}{'BE (eV)':>9}{'FWHM':>7}{'Diện tích':>11}{'%':>7}"]
        for c in f["thanh_phan"]:
            dong.append(f"{c['ten'][:19]:<20}{c['vt']:>9.2f}{c['fwhm']:>7.2f}{c['dt']:>11.0f}{c['pct']:>7.1f}" + ("  *" if c["o_bien"] else "")
                        + (f"  (doublet +{c['tach']:g})" if c.get("tach", 0) > 0 else ""))
        dong.append("(* = chạm biên ràng buộc)")
        rs = f["rstd"]
        dong.append("")
        dong.append(f"Số thành phần: {len(f['thanh_phan'])}   |   Residual STD = {rs:.2f} "
                    + ("(trong 0.85-1.15)" if 0.85 <= rs <= 1.15 else "(NGOÀI 0.85-1.15)")
                    + "   |   bấm 'Chứng minh kết quả...' để có bằng chứng thống kê")
        if kq["ghi"]:
            dong += [""] + kq["ghi"]
        if kq["canh_bao"]:
            dong += ["", "Nhận xét:"] + ["- " + c for c in kq["canh_bao"]]
        self.txt_kq.delete("1.0", "end")
        self.txt_kq.insert("1.0", "\n".join(dong))
        self.v_tt.set("Fit xong. Kiểm tra từng thành phần có hợp lý hoá học không (mục Nhận xét) trước khi xuất.")

    # ---------- xuất ----------
    def _xuat_file(self, thu_muc):
        ten = (self.v_ten.get().strip() or "XPS").replace(" ", "_")
        os.makedirs(thu_muc, exist_ok=True)
        kq = [xps.ghi_csv_fit(os.path.join(thu_muc, f"{ten}_fit.csv"), self.kq, ten),
              xps.ghi_csv_muot(os.path.join(thu_muc, f"{ten}_muot.csv"), self.kq),
              xps.ghi_csv_thanh_phan(os.path.join(thu_muc, f"{ten}_thanh_phan.csv"), self.kq)]
        for ext in ("png", "pdf"):
            p = os.path.join(thu_muc, f"{ten}_hinh.{ext}")
            xps.ve_hinh(self.kq, p, ten, 300, kieu=self.kieu)
            kq.append(p)
        n = len(self.kq["fit"]["thanh_phan"])
        kieu = xps.chuan_kieu(self.kieu, n)
        pk = os.path.join(thu_muc, f"{ten}_kieu.json")
        with open(pk, "w", encoding="utf-8") as fh:
            json.dump(kieu, fh, ensure_ascii=False)
        pr = os.path.join(thu_muc, f"{ten}_bao_cao.txt")
        with open(pr, "w", encoding="utf-8") as fh:
            fh.write(xps.bao_cao_van_ban(self.kq, ten, self.cuoi_ts))
        if self.cm:
            pc = os.path.join(thu_muc, f"{ten}_chung_minh.txt")
            with open(pc, "w", encoding="utf-8") as fh:
                fh.write(self.cm["van_ban"])
            kq.append(pc)
        kq += [xps.luu_mo_hinh(os.path.join(thu_muc, f"{ten}_mo_hinh.json"), self.kq, self._ts_luu(), kieu), pr]
        return kq, ten

    def _ts_luu(self):
        ts = dict(self.cuoi_ts)
        ts["mau"] = self.v_mau.get()
        ts.pop("tp", None)
        return ts

    def xuat(self):
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit trước.", parent=self.w)
            return
        d = filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu kết quả")
        if not d:
            return
        kq, _ = self._xuat_file(d)
        messagebox.showinfo("XPS", "Đã ghi:\n" + "\n".join(os.path.basename(x) for x in kq) + f"\n\nvào: {d}", parent=self.w)

    def ve_origin(self):
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit trước.", parent=self.w)
            return
        if self.lenh_origin is None:
            messagebox.showinfo("XPS", "Chưa kết nối được Origin từ cửa sổ này. Dùng 'Xuất CSV + hình...' rồi import file *_muot.csv vào Origin.",
                                parent=self.w)
            return
        d = filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu kết quả (CSV + dự án Origin)")
        if not d:
            return
        _, ten = self._xuat_file(d)
        self._casa_cho_mo = None
        if self.v_casa.get():
            self._casa_cho_mo = self._ghi_casa(d, ten)[-1]
        lenh = list(self.lenh_origin()) + ["--csv-muot", os.path.join(d, f"{ten}_muot.csv"), "--csv-fit", os.path.join(d, f"{ten}_fit.csv"),
                                           "--ten", ten, "--thu-muc-ra", d, "--kieu", os.path.join(d, f"{ten}_kieu.json"),
                                           "--x-min", f"{float(self.kq['be'].min()):.3f}", "--x-max", f"{float(self.kq['be'].max()):.3f}"]
        self.v_tt.set("Đang vẽ trong Origin (cần Origin đã cài; cửa sổ Origin sẽ hiện)...")
        kqc = {"xong": False, "out": ""}

        def chay():
            try:
                p = subprocess.run(lenh, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   creationflags=0x08000000 if os.name == "nt" else 0)
                kqc["out"] = (p.stdout or "") + (p.stderr or "")
            except Exception as e:
                kqc["out"] = str(e)
            kqc["xong"] = True

        threading.Thread(target=chay, daemon=True).start()
        self.w.after(500, lambda: self._cho_origin(kqc, d))

    def _hv(self):
        v0 = self.vung[self.chon] if self.vung and getattr(self, "chon", None) is not None and self.chon < len(self.vung) else {}
        return float(v0.get("hv") or 1486.6)

    def _ghi_casa(self, d, ten):
        """Ghi file .vms + bảng thành phần cho CasaXPS; trả về list file."""
        try:
            t = float(self.v_t.get().replace(",", ".")) if self.v_t.get().strip() else None
        except ValueError:
            t = None
        kq = xps.xuat_casa(self.kq, d, ten, self._hv(), t)
        if str(self.duong_dan).lower().endswith(".vms") and getattr(self, "chon", None) is not None:
            # bản sao NGUYÊN file gốc (mọi khối giữ nguyên) có thêm fit Casa-native ở khối đang chọn -> giống hệt khi fit trong Casa
            goc = xps.xuat_casa_goc(self.duong_dan, self.chon, self.kq, self.v_ten.get().strip() or "C1s", self._hv(),
                                    kq[0].replace("_casa.vms", "_casa_goc.vms"))
            if goc:
                kq.append(goc)
        return kq

    def xuat_casa(self):
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit trước.", parent=self.w)
            return
        d = filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu file cho CasaXPS")
        if not d:
            return
        ten = (self.v_ten.get().strip() or "XPS").replace(" ", "_")
        kq = self._ghi_casa(d, ten)
        self.v_tt.set("Đã ghi file CasaXPS: " + ", ".join(os.path.basename(x) for x in kq))
        self._mo_casa(kq[-1])

    def _mo_casa(self, vms):
        """Mở file .vms bằng CasaXPS. Tìm exe tự động; không thấy thì hỏi chọn CasaXPS.exe một lần (nhớ cho lần sau); cuối cùng thử
        chương trình mặc định của file .vms. Casa không tự vẽ chồng: sau khi mở, chọn các khối rồi Display > Overlay."""
        vms_goc = vms
        vms = xps.duong_an_toan_casa(vms)               # Casa không đọc được đường dẫn có dấu/dài: chép sang thư mục ngắn không dấu
        exe = xps.tim_casa_exe()
        if not exe and os.name == "nt" and messagebox.askyesno(
                "CasaXPS", "Chưa tìm thấy CasaXPS trên máy. Bạn chọn file CasaXPS.exe để app mở giúp (chỉ hỏi một lần)?", parent=self.w):
            p = filedialog.askopenfilename(parent=self.w, title="Chọn CasaXPS.exe", filetypes=[("CasaXPS", "*.exe"), ("Tất cả", "*.*")])
            if p:
                xps.luu_casa_exe(p)
                exe = p
        try:
            if exe:
                subprocess.Popen([exe, vms])
                self.v_tt.set("Đã mở CasaXPS với " + vms + (" (bản sao, vì đường dẫn gốc có dấu/dài)" if vms != vms_goc else "") + ". Trong Casa: chọn các khối rồi Display > Overlay để chồng lên nhau.")
                return
            if os.name == "nt":
                os.startfile(vms)                      # chương trình mặc định của .vms (nếu Casa đã gắn)
                self.v_tt.set("Đã yêu cầu Windows mở " + os.path.basename(vms) + " bằng chương trình mặc định.")
                return
        except Exception as e:
            messagebox.showwarning("CasaXPS", f"Không mở được CasaXPS tự động: {e}", parent=self.w)
        messagebox.showinfo("CasaXPS", "Đã ghi:\n" + vms + "\n\nHãy mở file này trong CasaXPS: File > Open; mỗi khối (Raw, Background, Envelope, "
                            "từng thành phần, Residual) là một phổ, chồng lên nhau bằng Display > Overlay.", parent=self.w)

    def _cho_origin(self, kqc, d):
        if not kqc["xong"]:
            self.w.after(500, lambda: self._cho_origin(kqc, d))
            return
        self.v_tt.set("Origin xong. " + (kqc["out"].strip().splitlines()[-1] if kqc["out"].strip() else ""))
        messagebox.showinfo("Origin", (kqc["out"].strip()[-1500:] or "(không có thông báo)") + f"\n\nThư mục: {d}", parent=self.w)
        if getattr(self, "_casa_cho_mo", None):
            vms, self._casa_cho_mo = self._casa_cho_mo, None
            self._mo_casa(vms)                         # mở luôn CasaXPS sau khi Origin vẽ xong

    # ---------- tính năng bổ sung ----------
    def giu_dich(self):
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit vùng C1s trước.", parent=self.w)
            return
        self.dich_c1s = float(self.kq["dich_hieu_chuan"])
        self.v_dich.set(f"{self.dich_c1s:.3f}")
        self.v_tt.set(f"Đã lưu dịch {self.dich_c1s:+.3f} eV. Chọn vùng khác (O1s, N1s, Ti2p...) rồi Fit: sẽ dùng cùng độ dịch "
                      "(mọi vùng của một mẫu cùng bị tích điện như nhau). Xoá ô 'Dịch sẵn' để tự hiệu chuẩn lại.")

    def chon_kieu(self):
        from tkinter import colorchooser
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit trước, rồi chọn màu cho từng thành phần.", parent=self.w)
            return
        tps = self.kq["fit"]["thanh_phan"]
        k = xps.chuan_kieu(self.kieu, len(tps))
        top = tk.Toplevel(self.w)
        top.title("Màu & tô vùng dưới đường")
        top.transient(self.w)
        mau = list(k["mau"])
        to = [tk.BooleanVar(value=v) for v in k["to"]]
        nut = []

        def doi(i):
            c = colorchooser.askcolor(color=mau[i], parent=top, title=tps[i]["ten"])[1]
            if c:
                mau[i] = c
                nut[i].configure(bg=c)

        for i, c in enumerate(tps):
            r = ttk.Frame(top)
            r.pack(fill="x", padx=8, pady=2)
            b = tk.Button(r, width=4, bg=mau[i], command=lambda i=i: doi(i))
            b.pack(side="left")
            nut.append(b)
            ttk.Checkbutton(r, text="Tô vùng dưới đường", variable=to[i]).pack(side="left", padx=6)
            ttk.Label(r, text=f"{c['ten']}  ({c['vt']:.2f} eV)").pack(side="left")
        r = ttk.Frame(top)
        r.pack(fill="x", padx=8, pady=(8, 2))
        mb = [k["mau_bao"]]
        nb = tk.Button(r, width=4, bg=mb[0])

        def doi_bao():
            c = colorchooser.askcolor(color=mb[0], parent=top, title="Đường bao")[1]
            if c:
                mb[0] = c
                nb.configure(bg=c)
        nb.configure(command=doi_bao)
        nb.pack(side="left")
        ttk.Label(r, text="Đường bao   độ dày:").pack(side="left", padx=6)
        v_day = tk.DoubleVar(value=k["day_bao"])
        ttk.Spinbox(r, from_=0.5, to=8, increment=0.2, textvariable=v_day, width=5).pack(side="left")
        r2 = ttk.Frame(top)
        r2.pack(fill="x", padx=8, pady=2)
        v_al = tk.DoubleVar(value=k["alpha"])
        ttk.Label(r2, text="Độ đậm vùng tô (0-1):").pack(side="left")
        ttk.Spinbox(r2, from_=0.1, to=1.0, increment=0.05, textvariable=v_al, width=5).pack(side="left", padx=4)
        v_dm = tk.BooleanVar(value=k["hien_diem"])
        ttk.Checkbutton(r2, text="Hiện điểm dữ liệu thô", variable=v_dm).pack(side="left", padx=10)

        def ap_dung():
            self.kieu = {"mau": mau, "to": [v.get() for v in to], "alpha": float(v_al.get()), "mau_bao": mb[0],
                         "day_bao": float(v_day.get()), "hien_diem": bool(v_dm.get())}
            self.hien_ket_qua()
            top.destroy()
        ttk.Button(top, text="Áp dụng (dùng cho hình xem trước, PNG/PDF và Origin)", command=ap_dung).pack(pady=8)

    def dinh_luong(self):
        if not self.vung:
            messagebox.showinfo("XPS", "Hãy mở file XPS (nhiều vùng: C1s, O1s, ...) trước.", parent=self.w)
            return
        h = xps.dinh_luong(self.vung, self._nen())
        if not h:
            messagebox.showinfo("XPS", "Không nhận ra vạch nguyên tố nào trong file (cần tên vùng kiểu 'C 1s', 'O 1s', 'Ru 3d'...).",
                                parent=self.w)
            return
        d = ["Định lượng bán định lượng: % nguyên tử = (diện tích sau nền Shirley / RSF Scofield) chuẩn hoá,",
             "chưa hiệu chỉnh hàm truyền máy phân tích và độ sâu thoát electron. Cần so sánh giữa các mẫu thì dùng cùng điều kiện đo.", "",
             f"{'Vùng':<16}{'Vạch':<8}{'Diện tích':>12}{'RSF':>8}{'% nguyên tử':>13}"]
        for x in h:
            d.append(f"{str(x['ten'])[:15]:<16}{x['vach']:<8}{x['dien_tich']:>12.1f}{x['rsf']:>8.2f}{x['pct']:>13.2f}")
        top = tk.Toplevel(self.w)
        top.title("Định lượng nguyên tố")
        t = tk.Text(top, width=78, height=min(30, len(d) + 2), font=("Consolas", 10))
        t.pack(fill="both", expand=True, padx=6, pady=6)
        t.insert("1.0", "\n".join(d))

        def luu():
            p = filedialog.asksaveasfilename(parent=top, defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="dinh_luong.csv")
            if p:
                import csv
                with open(p, "w", newline="", encoding="utf-8-sig") as fh:
                    w = csv.writer(fh)
                    w.writerow(["Vung", "Vach", "Dien_tich", "RSF", "Phan_tram_nguyen_tu"])
                    for x in h:
                        w.writerow([x["ten"], x["vach"], f"{x['dien_tich']:.3f}", x["rsf"], f"{x['pct']:.3f}"])
        ttk.Button(top, text="Lưu CSV...", command=luu).pack(pady=(0, 6))

    def nhan_tu_casa(self, duong=None, so_lieu=None):
        """Quy trình: app fit + xuất sang Casa -> Casa vẽ/fit (Fit Components) -> File > Save -> bấm nút này: app lấy ĐÚNG số Casa."""
        if duong is None:
            duong = filedialog.askopenfilename(parent=self.w, title="Chọn file .vms đã fit và lưu trong Casa",
                                               initialdir=os.path.dirname(getattr(self, "duong_dan", "") or "."),
                                               filetypes=[("VAMAS", "*.vms"), ("Tất cả", "*.*")])
        if not duong:
            return
        try:
            vs = xps.doc_xps(duong)
        except Exception as e:
            messagebox.showerror("XPS", f"Không đọc được file:\n{e}", parent=self.w)
            return
        i = next((k for k, v in enumerate(vs) if v.get("ghi_chu_casa") and "CASA comp" in " ".join(v["ghi_chu_casa"])), None)
        if i is None:
            messagebox.showinfo("XPS", "File này chưa có fit lưu bởi Casa. Trong Casa: fit (Fit Components) rồi File > Save.", parent=self.w)
            return False
        v = vs[i]
        t = v["dwell"] * v["scans"] if v.get("dwell") and v.get("scans") and v["dwell"] < 100 else None
        try:
            t = t or float(self.v_t.get().replace(",", "."))
        except ValueError:
            pass
        try:
            kq = None
            dich_ck = None if self.v_giu_be_casa.get() else self._so(self.v_chuan, "Năng lượng chuẩn")
            if so_lieu:
                kq = self._kq_tu_so_lieu_casa(v, t, so_lieu)
            if kq is None:
                kq = xps.kq_tu_casa(v, t, dich_ck)
        except Exception as e:
            messagebox.showerror("XPS", str(e), parent=self.w)
            return False
        self.vung, self.chon, self.duong_dan = vs, i, duong
        self.v_file.set(os.path.basename(duong))
        self.kq, self.cm = kq, None
        self.cuoi_ts = {"dich_san": None, "t": t, "nen": "shirley", "vung": kq["tham_so_fit"]["vung"], "dich": self._so(self.v_chuan, "Năng lượng chuẩn"),
                        "tp": kq["tp"], "tu_chon": False, "dw": xps.DW_FWHM, "khoang": (290.0, 280.0), "bang_tp": "", "dich_san_": None}
        self.ve_tho()
        self.hien_ket_qua()
        self.v_tt.set("Đã nhận kết quả từ Casa: số dưới đây là số của Casa. Bấm 'Chứng minh kết quả...' hoặc 'Vẽ ra Origin...' như bình thường.")
        return True

    def ve_origin_tu_casa(self, duong=None):
        """Một bước: chọn file .vms đã fit trong Casa -> nạp số của Casa -> vẽ Origin."""
        if self.nhan_tu_casa(duong):
            self.ve_origin()

    def nhan_tu_casa_kem_bang(self):
        """Nhận file .vms đã lưu trong Casa KÈM bảng số Casa xuất (TAB ASCII: nền, đường bao, thành phần, phần dư): dùng đúng số của Casa."""
        vms = filedialog.askopenfilename(parent=self.w, title="1/2 - Chọn file .vms đã fit và lưu trong Casa",
                                         initialdir=os.path.dirname(getattr(self, "duong_dan", "") or "."),
                                         filetypes=[("VAMAS", "*.vms"), ("Tất cả", "*.*")])
        if not vms:
            return
        txt = filedialog.askopenfilename(parent=self.w, title="2/2 - Chọn file bảng số Casa xuất (TAB ASCII, .txt/.csv)",
                                         initialdir=os.path.dirname(vms), filetypes=[("Bảng số", "*.txt *.csv *.tsv"), ("Tất cả", "*.*")])
        if not txt:
            return
        noi_dung = None
        for ma in ("utf-8-sig", "utf-16", "cp1252"):
            try:
                with open(txt, "r", encoding=ma) as fh:
                    noi_dung = fh.read()
                break
            except (UnicodeError, OSError):
                continue
        if not noi_dung:
            messagebox.showerror("XPS", "Không đọc được file bảng số.", parent=self.w)
            return
        self.nhan_tu_casa(vms, noi_dung)

    def _kq_tu_so_lieu_casa(self, v, t, so_lieu):
        """Dựng kết quả từ cột Casa xuất (nền, đường bao, thành phần, phần dư): số của Casa, không tính lại. Lỗi -> None (quay về số trong file .vms)."""
        import casa_xuat
        try:
            cs = xps.doc_casa_ghi_chu(v.get("ghi_chu_casa"), v.get("hv") or 1486.6)
            d = casa_xuat.doc_bang_tab(so_lieu)
            r = casa_xuat.phan_loai_cot(d["cot"], [c["ten"] for c in cs["thanh_phan"]])
            return casa_xuat.kq_tu_cot_casa(r, v, t, v.get("hv") or 1486.6, cs, 0.0)
        except Exception as e:  # noqa: BLE001
            self.v_tt.set(f"Không đọc được bảng số liệu Casa ({e}); dùng số trong file .vms.")
            return None

    def so_voi_casa(self):
        if not getattr(self, "vung", None):
            messagebox.showinfo("XPS", "Hãy mở file .vms trước.", parent=self.w)
            return
        v = dict(self.vung[self.chon])
        kq = getattr(self, "kq", None)
        try:
            vb = xps.so_sanh_casa(v, kq)
        except Exception as e:
            messagebox.showerror("XPS", f"Không đối chiếu được:\n{e}", parent=self.w)
            return
        top = tk.Toplevel(self.w)
        top.title("So với Casa")
        t = tk.Text(top, width=110, height=32, font=("Consolas", 10), wrap="word")
        t.pack(fill="both", expand=True, padx=6, pady=6)
        t.insert("1.0", vb)

    def luu_mo_hinh(self):
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit trước.", parent=self.w)
            return
        p = filedialog.asksaveasfilename(parent=self.w, defaultextension=".json", filetypes=[("Mô hình fit", "*.json")], initialfile="mo_hinh_xps.json")
        if p:
            xps.luu_mo_hinh(p, self.kq, self._ts_luu(), xps.chuan_kieu(self.kieu, len(self.kq["fit"]["thanh_phan"])))
            self.v_tt.set("Đã lưu mô hình (tham số + kết quả + màu).")

    def nap_mo_hinh(self):
        p = filedialog.askopenfilename(parent=self.w, filetypes=[("Mô hình fit", "*.json")])
        if not p:
            return
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            ts = d.get("tham_so", {})
            if ts.get("bang_tp"):
                self.txt_tp.delete("1.0", "end")
                self.txt_tp.insert("1.0", ts["bang_tp"])
            if ts.get("mau") in xps.MAU:
                self.v_mau.set(ts["mau"])
            if ts.get("vung"):
                self.v_fit_tu.set(f"{ts['vung'][0]:g}")
                self.v_fit_den.set(f"{ts['vung'][1]:g}")
            if ts.get("dw") is not None:
                self.v_dw.set(f"{ts['dw']:g}")
            if d.get("kieu"):
                self.kieu = d["kieu"]
            self.v_tt.set("Đã nạp mô hình: bảng thành phần, vùng fit, ràng buộc, màu. Bấm 'Hiệu chuẩn + Fit' để chạy lại trên phổ hiện tại.")
        except Exception as e:
            messagebox.showerror("XPS", f"Không nạp được: {e}", parent=self.w)

    # ---------- phổ thô & chọn vùng bằng chuột ----------
    def ve_tho(self):
        """Vẽ phổ thô của vùng đang chọn (chưa hiệu chuẩn) để kéo chuột chọn vùng fit / khoảng dò đỉnh."""
        if not self.vung:
            return
        v = self.vung[getattr(self, "chon", 0)]
        self.ax.clear()
        self.ax_r.clear()
        o = np.argsort(v["be"])
        self.ax.plot(v["be"][o], v["y"][o], ".-", ms=3, lw=0.6, color="#444")
        lo, hi = float(v["be"].min()), float(v["be"].max())
        self.ax.set_xlim(hi, lo)
        self.ax.set_ylabel("Cường độ", fontsize=8)
        self.ax_r.set_xlabel("Binding Energy (eV, chưa hiệu chuẩn)")
        self.ax_r.set_yticks([])
        self.cv.draw_idle()

    def chon_chuot(self, loai):
        """Kéo chuột trên hình (theo trục BE) để đặt vùng fit ('fit') hoặc khoảng dò đỉnh hiệu chuẩn ('do')."""
        from matplotlib.widgets import SpanSelector
        if not self.vung:
            messagebox.showinfo("XPS", "Hãy mở file XPS trước.", parent=self.w)
            return
        if self.kq is not None:
            self.ve_tho()                                # kéo trên phổ thô (cùng thang BE với dữ liệu gốc)
            self.v_tt.set("Đang hiện phổ thô để chọn vùng. Bấm 'Hiệu chuẩn + Fit' để quay lại kết quả.")
        self._span = SpanSelector(self.ax, lambda a, b: self._nhan_khoang(loai, a, b), "horizontal", useblit=False,
                                  props=dict(alpha=0.25, facecolor="#4c9be8"), interactive=True)
        self.v_tt.set("Kéo chuột trên hình để chọn " + ("VÙNG FIT (nên rộng, gồm cả hai chân phổ cho nền)" if loai == "fit"
                                                           else "KHOẢNG DÒ ĐỈNH hiệu chuẩn (đỉnh cao nhất trong khoảng sẽ về năng lượng chuẩn)") + ".")

    def _nhan_khoang(self, loai, a, b):
        lo, hi = sorted((float(a), float(b)))
        if hi - lo < 0.2:
            return
        if loai == "fit":
            self.v_fit_tu.set(f"{lo:.2f}")
            self.v_fit_den.set(f"{hi:.2f}")
        else:
            self.v_do_tu.set(f"{hi:.2f}")
            self.v_do_den.set(f"{lo:.2f}")
        self.v_tt.set(f"Đã đặt {'vùng fit' if loai == 'fit' else 'khoảng dò đỉnh'}: {lo:.2f} – {hi:.2f} eV.")

    # ---------- chứng minh kết quả ----------
    def chung_minh(self):
        if self.kq is None:
            messagebox.showinfo("XPS", "Hãy fit trước.", parent=self.w)
            return
        kq = self.kq
        st = {"xong": False, "cm": None, "loi": None, "tt": "Đang kiểm định..."}

        def chay():
            try:
                st["cm"] = xps.chung_minh(kq, tien_do=lambda t: st.__setitem__("tt", t))
            except Exception as e:
                st["loi"] = str(e)
            st["xong"] = True
        threading.Thread(target=chay, daemon=True).start()
        self.v_tt.set("Đang chứng minh kết quả (bỏ/thêm từng thành phần, đổi nền, Monte Carlo) - vài chục giây...")
        self.w.after(400, lambda: self._cho_chung_minh(st))

    def _cho_chung_minh(self, st):
        if not st["xong"]:
            self.v_tt.set("Chứng minh kết quả: " + st["tt"])
            self.w.after(400, lambda: self._cho_chung_minh(st))
            return
        if st["loi"]:
            messagebox.showerror("XPS", st["loi"], parent=self.w)
            return
        self.cm = cm = st["cm"]
        self.v_tt.set("Xong. " + ("ĐẠT cả số thành phần lẫn phần dư." if cm["dat"] else "CHƯA đạt hoàn toàn - xem chi tiết.")
                      + " Khi xuất, file *_chung_minh.txt sẽ được ghi kèm.")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        top = tk.Toplevel(self.w)
        top.title("Chứng minh kết quả fit")
        top.geometry("980x760")
        fig = Figure(figsize=(8.6, 2.6), dpi=100)
        a1 = fig.add_subplot(1, 2, 1)
        a2 = fig.add_subplot(1, 2, 2)
        b = np.argsort(self.kq["be"])
        z = cm["phan_du"]["z"]
        a1.plot(self.kq["be"][b], z[b], ".-", ms=3, lw=0.6, color="#b2182b")
        for y0 in (-2, 2):
            a1.axhline(y0, color="#999", ls="--", lw=0.8)
        a1.axhline(0, color="#444", lw=0.6)
        a1.set_xlim(self.kq["be"].max(), self.kq["be"].min())
        a1.set_title("Phần dư chuẩn hoá r/σ (kỳ vọng: ngẫu nhiên, ~95% trong ±2)", fontsize=8)
        a1.set_xlabel("BE (eV)", fontsize=8)
        a2.hist(z, bins=15, density=True, color="#6baed6", edgecolor="white")
        xs = np.linspace(-4, 4, 200)
        a2.plot(xs, np.exp(-xs ** 2 / 2) / np.sqrt(2 * np.pi), color="#333", lw=1.2)
        a2.set_title("Phân bố r/σ so với N(0,1)", fontsize=8)
        fig.tight_layout()
        cv = FigureCanvasTkAgg(fig, master=top)
        cv.get_tk_widget().pack(fill="x", padx=6, pady=4)
        t = tk.Text(top, font=("Consolas", 10), wrap="none")
        t.pack(fill="both", expand=True, padx=6, pady=4)
        t.insert("1.0", cm["van_ban"])

        def luu():
            p = filedialog.asksaveasfilename(parent=top, defaultextension=".txt", filetypes=[("Văn bản", "*.txt")], initialfile="chung_minh.txt")
            if p:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(cm["van_ban"])
        fb = ttk.Frame(top)
        fb.pack(fill="x", padx=6, pady=(0, 6))
        pas = cm["phuong_an"]
        ds = [("[ĐỀ XUẤT] " if i == cm["khuyen_nghi"] else "") + f"{i + 1}. {p['ten']}  (Res.STD {p['rstd']:.2f})" for i, p in enumerate(pas)]
        v_pa = tk.StringVar(value=ds[cm["khuyen_nghi"]])
        ttk.Label(fb, text="Phương án:").pack(side="left")
        cb = ttk.Combobox(fb, textvariable=v_pa, values=ds, width=62, state="readonly")
        cb.pack(side="left", padx=4)

        def ap_dung():
            try:
                i = ds.index(v_pa.get())
            except ValueError:
                i = cm["khuyen_nghi"]
            self.ap_dung_phuong_an(pas[i])
            top.destroy()
        ttk.Button(fb, text="Áp dụng phương án này", command=ap_dung).pack(side="left", padx=4)
        ttk.Button(fb, text="Lưu báo cáo...", command=luu).pack(side="left", padx=4)

    def ap_dung_phuong_an(self, pa):
        """Thay kết quả đang hiển thị bằng một phương án trong báo cáo chứng minh (chạy lại kiểm định để báo cáo khớp kết quả mới)."""
        self.kq = pa["kq"]
        self.cm = None
        self.cuoi_ts = dict(self.cuoi_ts)
        self.cuoi_ts["nen"] = self.kq["tham_so_fit"]["nen"]
        self.cuoi_ts["dw"] = self.kq["tham_so_fit"]["dw"]
        self.hien_ket_qua()
        self.v_tt.set(f"Đã áp dụng: {pa['ten']}. Bấm 'Chứng minh kết quả...' lại nếu muốn báo cáo khớp phương án mới trước khi xuất.")
