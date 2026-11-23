# -*- coding: utf-8 -*-
"""Cửa sổ Tafel từ bộ dữ liệu Qs-LSV (mở từ công cụ Qs-LSV & TOF).
Đọc QsLSV_<nhãn>.csv do công cụ ghi → chọn vùng (theo dòng / theo điện thế / tất cả), số điểm N và cách lấy N điểm, bỏ riêng từng điểm
→ xem ngay đồ thị E–log|J| + đường fit + hệ số Tafel. Logic nằm ở tafel_qs.py."""
import os
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
import pandas as pd

import tafel_qs as tq

CHE_DO = {"Theo dòng |J| (mA/cm²)": "dong", "Theo điện thế E (V vs RHE)": "dien_the", "Tất cả điểm Qs-LSV": "tat_ca"}
KIEU = {"Tất cả điểm trong vùng": "tat_ca", "N điểm đầu vùng (|J| nhỏ nhất)": "dau", "N điểm cuối vùng (|J| lớn nhất)": "cuoi",
        "N điểm liên tiếp tốt nhất (R² cao nhất)": "tot_nhat"}
TRUC_Y = {"E (V vs RHE)": "e", "Quá thế η (mV)": "eta"}


def ten_tep(nhan):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(nhan))


class CuaSoTafelQs:
    def __init__(self, cha, mau, thu_muc, hanh_dong=None, tai_lai=None):
        """mau: [{'nhan','mau'}]; thu_muc: nơi có QsLSV_<nhãn>.csv và nơi ghi kết quả;
        hanh_dong = {'origin': f(đường dẫn json), 'mo': f(đường dẫn), 'luu': f(đường dẫn json)}; tai_lai: f() chạy lại việc đọc Qs-LSV."""
        self.cha = cha
        self.thu_muc = thu_muc
        self.hd = hanh_dong or {}
        self.tai_lai = tai_lai
        self.mau = list(mau)
        self.du_lieu = {}          # nhan -> {"e","j","mau"}
        self.cfg = {}              # nhan -> cấu hình riêng (che_do, lo, hi, so_diem, kieu, loai_bo)
        self.kq = {}               # nhan -> kết quả fit (hoặc None)
        self.loi = {}              # nhan -> thông báo lỗi
        self.hien = None
        self._dang_nap = False
        w = self.w = tk.Toplevel(cha)
        w.title("Tafel từ Qs-LSV")
        w.geometry("1180x760")
        w.minsize(980, 620)
        w.transient(cha)
        trai = ttk.Frame(w, padding=(8, 8, 4, 8))
        trai.pack(side="left", fill="y")
        phai = ttk.Frame(w, padding=(4, 8, 8, 8))
        phai.pack(side="left", fill="both", expand=True)
        self._dung_dieu_khien(trai)
        self._dung_do_thi(phai)
        self.nap()

    # ---------------------------------------------------------------- giao diện
    def _dung_dieu_khien(self, f):
        ttk.Label(f, text="E = a + b·log₁₀|J|     b (mV/dec) = độ dốc đường fit", foreground="#444").pack(anchor="w", pady=(0, 4))
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Mẫu:").pack(side="left")
        self.v_mau = tk.StringVar()
        self.cb_mau = ttk.Combobox(top, textvariable=self.v_mau, state="readonly", width=26)
        self.cb_mau.pack(side="left", padx=4)
        self.cb_mau.bind("<<ComboboxSelected>>", lambda e: self.doi_mau())
        ttk.Button(top, text="↻ Đọc lại Qs-LSV", command=self.doc_lai).pack(side="left", padx=2)

        lf = ttk.LabelFrame(f, text="Vùng fit")
        lf.pack(fill="x", pady=6)
        self.v_che_do = tk.StringVar(value=next(iter(CHE_DO)))
        cb = ttk.Combobox(lf, textvariable=self.v_che_do, values=list(CHE_DO), state="readonly", width=30)
        cb.grid(row=0, column=0, columnspan=4, sticky="w", padx=4, pady=3)
        cb.bind("<<ComboboxSelected>>", lambda e: self.thay_doi())
        self.v_lo, self.v_hi = tk.StringVar(value="1"), tk.StringVar(value="10")
        self.lb_tu = ttk.Label(lf, text="từ")
        self.lb_tu.grid(row=1, column=0, sticky="e", padx=(4, 2))
        self.o_lo = ttk.Entry(lf, textvariable=self.v_lo, width=9)
        self.o_lo.grid(row=1, column=1)
        ttk.Label(lf, text="đến").grid(row=1, column=2, sticky="e", padx=(8, 2))
        self.o_hi = ttk.Entry(lf, textvariable=self.v_hi, width=9)
        self.o_hi.grid(row=1, column=3, padx=(0, 4))
        for o in (self.o_lo, self.o_hi):
            o.bind("<Return>", lambda e: self.thay_doi())
            o.bind("<FocusOut>", lambda e: self.thay_doi())
        self.lb_don_vi = ttk.Label(lf, text="mA/cm²", foreground="#666")
        self.lb_don_vi.grid(row=2, column=0, columnspan=4, sticky="w", padx=4)

        ln = ttk.LabelFrame(f, text="Số điểm")
        ln.pack(fill="x", pady=2)
        self.v_kieu = tk.StringVar(value=next(iter(KIEU)))
        cb2 = ttk.Combobox(ln, textvariable=self.v_kieu, values=list(KIEU), state="readonly", width=36)
        cb2.grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=3)
        cb2.bind("<<ComboboxSelected>>", lambda e: self.thay_doi())
        ttk.Label(ln, text="N =").grid(row=1, column=0, sticky="e", padx=(4, 2))
        self.v_n = tk.StringVar(value="")
        o_n = ttk.Entry(ln, textvariable=self.v_n, width=6)
        o_n.grid(row=1, column=1, sticky="w")
        o_n.bind("<Return>", lambda e: self.thay_doi())
        o_n.bind("<FocusOut>", lambda e: self.thay_doi())
        ttk.Label(ln, text="(≥ 3; bỏ trống khi chọn 'Tất cả điểm trong vùng')", foreground="#666").grid(row=1, column=2, sticky="w", padx=4)

        ly = ttk.LabelFrame(f, text="Đồ thị")
        ly.pack(fill="x", pady=6)
        self.v_y = tk.StringVar(value=next(iter(TRUC_Y)))
        cb3 = ttk.Combobox(ly, textvariable=self.v_y, values=list(TRUC_Y), state="readonly", width=18)
        cb3.grid(row=0, column=0, padx=4, pady=3)
        cb3.bind("<<ComboboxSelected>>", lambda e: self.ve())
        ttk.Label(ly, text="E⁰ (V vs RHE) cho η:").grid(row=0, column=1, padx=(8, 2))
        self.v_e0 = tk.StringVar(value="1.23")
        o_e0 = ttk.Entry(ly, textvariable=self.v_e0, width=7)
        o_e0.grid(row=0, column=2)
        o_e0.bind("<Return>", lambda e: self.ve())
        o_e0.bind("<FocusOut>", lambda e: self.ve())
        ttk.Label(ly, text="OER: 1.23 · HER: 0 (chỉ dùng khi chọn trục η)", foreground="#666").grid(row=1, column=0, columnspan=3, sticky="w", padx=4)

        nut = ttk.Frame(f)
        nut.pack(fill="x", pady=2)
        ttk.Button(nut, text="Áp vùng này cho mọi mẫu", command=self.ap_tat_ca).pack(side="left", padx=(0, 4))
        ttk.Button(nut, text="Bỏ chọn điểm loại", command=self.bo_loai).pack(side="left")

        self.v_kq = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.v_kq, justify="left", wraplength=430, font=("TkDefaultFont", 10, "bold"), foreground="#1f3864").pack(fill="x", pady=(6, 0))
        self.v_cb = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.v_cb, justify="left", wraplength=430, foreground="#9c3a00").pack(fill="x")

        tv = ttk.Frame(f)
        tv.pack(fill="both", expand=True, pady=(6, 0))
        ttk.Label(tv, text="Các điểm Qs-LSV của mẫu (bấm đúp = loại/đưa lại điểm):").pack(anchor="w")
        self.tv = ttk.Treeview(tv, columns=("k", "e", "j", "lg", "tt"), show="headings", height=9, selectmode="browse")
        for c, t, r in (("k", "#", 34), ("e", "E (V)", 78), ("j", "J (mA/cm²)", 90), ("lg", "log|J|", 70), ("tt", "Trạng thái", 130)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=r, anchor="center")
        sb = ttk.Scrollbar(tv, command=self.tv.yview)
        self.tv.config(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<Double-1>", self.bam_diem)
        self.tv.tag_configure("dung", foreground="#1b5e20")
        self.tv.tag_configure("loai", foreground="#b71c1c")
        self.tv.tag_configure("ngoai", foreground="#888888")

    def _dung_do_thi(self, f):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(6.2, 5.0), dpi=100)
        self.ax = self.fig.add_subplot(111)
        ghi = ttk.Frame(f)
        ghi.pack(side="bottom", fill="x", pady=2)           # nút xuất luôn nằm dưới cùng, không bị đồ thị che
        bang = ttk.Frame(f)
        bang.pack(side="bottom", fill="x", pady=(6, 2))
        self.cv = FigureCanvasTkAgg(self.fig, master=f)
        self.cv.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.tv_tong = ttk.Treeview(bang, columns=("nhan", "b", "se", "r2", "n", "vung"), show="headings", height=4, selectmode="browse")
        for c, t, r in (("nhan", "Mẫu", 130), ("b", "b (mV/dec)", 80), ("se", "± (mV/dec)", 80), ("r2", "R²", 60), ("n", "Số điểm", 60), ("vung", "Vùng", 320)):
            self.tv_tong.heading(c, text=t)
            self.tv_tong.column(c, width=r, anchor="w" if c in ("nhan", "vung") else "center")
        self.tv_tong.pack(fill="x")
        self.tv_tong.bind("<<TreeviewSelect>>", self.chon_tu_bang)
        ttk.Button(ghi, text="💾 Xuất hình + CSV (PNG/PDF)", command=self.xuat).pack(side="left", padx=(0, 4))
        if self.hd.get("origin"):
            ttk.Button(ghi, text="Vẽ ra Origin", command=self.ra_origin).pack(side="left", padx=2)
        ttk.Button(ghi, text="Lưu kết quả cho so sánh / nộp bài / báo cáo", command=self.luu_ket_qua).pack(side="left", padx=2)
        if self.hd.get("mo"):
            ttk.Button(ghi, text="Mở thư mục", command=lambda: self.hd["mo"](self.thu_muc)).pack(side="left", padx=2)
        ttk.Button(ghi, text="Đóng", command=self.w.destroy).pack(side="right")

    # ---------------------------------------------------------------- dữ liệu
    def nap(self):
        """Đọc QsLSV_<nhãn>.csv của các mẫu."""
        self.du_lieu.clear()
        thieu = []
        for m in self.mau:
            p = os.path.join(self.thu_muc, f"QsLSV_{ten_tep(m['nhan'])}.csv")
            if not os.path.isfile(p):
                thieu.append(m["nhan"])
                continue
            try:
                d = pd.read_csv(p)
                e, j = d[tq.C_E].to_numpy(float), d[tq.C_J].to_numpy(float)
            except (OSError, KeyError, ValueError) as ex:
                self.loi[m["nhan"]] = f"không đọc được {os.path.basename(p)}: {ex}"
                continue
            self.du_lieu[m["nhan"]] = {"e": e, "j": j, "mau": m["mau"]}
            self.cfg.setdefault(m["nhan"], tq.cau_hinh_mac_dinh())
        ds = [m["nhan"] for m in self.mau if m["nhan"] in self.du_lieu]
        self.cb_mau.config(values=ds)
        if not ds:
            self.v_kq.set("Chưa có dữ liệu Qs-LSV. Bấm '↻ Đọc lại Qs-LSV' (cần đã gán thư mục/file Qs-LSV cho mẫu).")
            self.hien = None
            self.ve()
            return
        if thieu:
            self.v_cb.set("Chưa có Qs-LSV của: " + ", ".join(thieu))
        if self.hien not in ds:
            self.hien = ds[0]
        self.v_mau.set(self.hien)
        self.dat_dieu_khien(self.cfg[self.hien])
        self.tinh_tat_ca()
        self.ve()

    def doc_lai(self):
        if self.tai_lai:
            self.tai_lai(self.nap)

    def doi_mau(self):
        self.hien = self.v_mau.get()
        self.dat_dieu_khien(self.cfg[self.hien])
        self.ve()

    def chon_tu_bang(self, e=None):
        s = self.tv_tong.selection()
        if s and s[0] in self.du_lieu and s[0] != self.hien:
            self.hien = s[0]
            self.v_mau.set(self.hien)
            self.dat_dieu_khien(self.cfg[self.hien])
            self.ve()

    # ---------------------------------------------------------------- điều khiển ↔ cấu hình
    def dat_dieu_khien(self, c):
        self._dang_nap = True
        ten_cd = next(k for k, v in CHE_DO.items() if v == c["che_do"])
        self.v_che_do.set(ten_cd)
        self.v_lo.set("" if c["lo"] is None else f"{c['lo']:g}" if isinstance(c["lo"], (int, float)) else str(c["lo"]))
        self.v_hi.set("" if c["hi"] is None else f"{c['hi']:g}" if isinstance(c["hi"], (int, float)) else str(c["hi"]))
        self.v_kieu.set(next(k for k, v in KIEU.items() if v == c["kieu"]))
        self.v_n.set("" if not c["so_diem"] else str(int(c["so_diem"])))
        self._dang_nap = False
        self.cap_nhat_nhan()

    def cap_nhat_nhan(self):
        cd = CHE_DO[self.v_che_do.get()]
        self.lb_don_vi.config(text={"dong": "|J| theo mA/cm² (vd 1 đến 10)", "dien_the": "E theo V vs RHE (vd 1.45 đến 1.55)", "tat_ca": "dùng mọi điểm có J ≠ 0"}[cd])
        st = "disabled" if cd == "tat_ca" else "normal"
        self.o_lo.config(state=st)
        self.o_hi.config(state=st)

    def doc_dieu_khien(self):
        """→ cfg từ các ô; ValueError nếu nhập sai."""
        cd = CHE_DO[self.v_che_do.get()]
        c = dict(self.cfg[self.hien])
        c["che_do"] = cd
        if cd != "tat_ca":
            try:
                c["lo"], c["hi"] = tq._so(self.v_lo.get()), tq._so(self.v_hi.get())
            except ValueError:
                raise ValueError("Ô 'từ' / 'đến' phải là số.")
            if c["lo"] is None or c["hi"] is None:
                raise ValueError("Hãy nhập cả 'từ' và 'đến'.")
        c["kieu"] = KIEU[self.v_kieu.get()]
        n = self.v_n.get().strip()
        try:
            c["so_diem"] = int(float(n.replace(",", "."))) if n else None
        except ValueError:
            raise ValueError("N (số điểm) phải là số nguyên.")
        if c["kieu"] != "tat_ca" and not c["so_diem"]:
            raise ValueError("Hãy nhập N (số điểm) cho cách chọn này.")
        return c

    def thay_doi(self):
        if self._dang_nap or self.hien is None:
            return
        self.cap_nhat_nhan()
        try:
            self.cfg[self.hien] = self.doc_dieu_khien()
        except ValueError as e:
            self.v_cb.set(str(e))
            return
        self.tinh(self.hien)
        self.ve()

    def tinh(self, nhan):
        d = self.du_lieu[nhan]
        try:
            self.kq[nhan] = tq.phan_tich(d["e"], d["j"], self.cfg[nhan])
            self.loi.pop(nhan, None)
        except ValueError as e:
            self.kq[nhan] = None
            self.loi[nhan] = str(e)

    def tinh_tat_ca(self):
        for n in self.du_lieu:
            self.tinh(n)

    def ap_tat_ca(self):
        if self.hien is None:
            return
        try:
            c = self.doc_dieu_khien()
        except ValueError as e:
            messagebox.showwarning("Tafel", str(e), parent=self.w)
            return
        for n in self.du_lieu:
            self.cfg[n] = dict(c, loai_bo=list(self.cfg[n].get("loai_bo", [])) if n != self.hien else list(c.get("loai_bo", [])))
        self.tinh_tat_ca()
        self.ve()

    def bo_loai(self):
        if self.hien is None:
            return
        self.cfg[self.hien]["loai_bo"] = []
        self.tinh(self.hien)
        self.ve()

    def bam_diem(self, e):
        s = self.tv.identify_row(e.y)
        if not s or self.hien is None:
            return
        k = int(s)
        lb = self.cfg[self.hien].setdefault("loai_bo", [])
        if k in lb:
            lb.remove(k)
        else:
            lb.append(k)
        self.tinh(self.hien)
        self.ve()
        try:
            self.tv.see(str(k))
        except tk.TclError:
            pass

    # ---------------------------------------------------------------- vẽ
    def kieu_y(self):
        ky = TRUC_Y[self.v_y.get()]
        try:
            e0 = float(self.v_e0.get().replace(",", ".") or 0)
        except ValueError:
            e0 = 0.0
        return ky, e0

    def danh_sach_ve(self):
        return [dict(nhan=n, mau=d["mau"], e=d["e"], j=d["j"], kq=self.kq.get(n)) for n, d in self.du_lieu.items()]

    def ve(self):
        self.ax.clear()
        cac = self.danh_sach_ve()
        ky, e0 = self.kieu_y()
        if cac:
            tq.ve_len_truc(self.ax, cac, ky, e0, co_chu=11)
        else:
            self.ax.text(0.5, 0.5, "Chưa có dữ liệu Qs-LSV", ha="center", va="center", transform=self.ax.transAxes)
        self.fig.tight_layout()
        self.cv.draw_idle()
        self.ve_bang_diem()
        self.ve_bang_tong()
        self.ve_ket_qua()

    def ve_bang_diem(self):
        self.tv.delete(*self.tv.get_children())
        if self.hien is None or self.hien not in self.du_lieu:
            return
        d, c, kq = self.du_lieu[self.hien], self.cfg[self.hien], self.kq.get(self.hien)
        mask = kq["mask"] if kq is not None else np.zeros(len(d["e"]), bool)
        thu_tu = np.argsort(np.abs(d["j"]))
        for k in thu_tu:
            j = d["j"][k]
            lg = f"{np.log10(abs(j)):.3f}" if j != 0 else "—"
            if k in c.get("loai_bo", []):
                tt, tag = "✖ đã loại", "loai"
            elif mask[k]:
                tt, tag = "✔ dùng để fit", "dung"
            else:
                tt, tag = "ngoài vùng/N", "ngoai"
            self.tv.insert("", "end", iid=str(int(k)), values=(int(k) + 1, f"{d['e'][k]:.4f}", f"{j:.4g}", lg, tt), tags=(tag,))

    def ve_bang_tong(self):
        self.tv_tong.delete(*self.tv_tong.get_children())
        for n in self.du_lieu:
            kq = self.kq.get(n)
            if kq is None:
                self.tv_tong.insert("", "end", iid=n, values=(n, "—", "—", "—", "—", self.loi.get(n, "")))
            else:
                self.tv_tong.insert("", "end", iid=n, values=(n, f"{abs(kq['b_mV']):.1f}", f"{kq['sai_so_mV']:.1f}", f"{kq['r2']:.4f}", kq["n"], kq["vung"]))
        if self.hien in self.du_lieu:
            try:
                self.tv_tong.selection_set(self.hien)
            except tk.TclError:
                pass

    def ve_ket_qua(self):
        if self.hien is None or self.hien not in self.du_lieu:
            self.v_cb.set(self.v_cb.get())
            return
        kq = self.kq.get(self.hien)
        if kq is None:
            self.v_kq.set(f"{self.hien}: chưa fit được")
            self.v_cb.set(self.loi.get(self.hien, ""))
            return
        self.v_kq.set(f"{self.hien}:  b = {abs(kq['b_mV']):.1f} ± {kq['sai_so_mV']:.1f} mV/dec   ·   R² = {kq['r2']:.4f}   ·   {kq['n']} điểm "
                      f"({kq['decades']:.2f} decade)")
        self.v_cb.set("\n".join(kq["canh_bao"]))

    # ---------------------------------------------------------------- xuất
    def _cac_co_kq(self):
        cac = [c for c in self.danh_sach_ve() if c["kq"] is not None]
        if not cac:
            messagebox.showinfo("Tafel", "Chưa có mẫu nào fit được.", parent=self.w)
        return cac

    def _nhan_xet(self, cac):
        try:
            import auron_danh_gia as _ag
            _ag.thu_ghi(_ag.tu_tafel_qs, cac)
        except Exception:  # noqa: BLE001
            pass

    def xuat(self):
        cac = self._cac_co_kq()
        if not cac:
            return
        self._nhan_xet(cac)
        ky, e0 = self.kieu_y()
        try:
            ra = tq.xuat(cac, self.thu_muc, "Tafel_QsLSV", ky, e0)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Tafel", f"Không ghi được kết quả: {e}", parent=self.w)
            return
        self.v_cb.set("Đã ghi vào " + self.thu_muc + ": " + ", ".join(ra[:4]) + (" ..." if len(ra) > 4 else ""))
        if self.hd.get("luu"):
            self.hd["luu"](os.path.join(self.thu_muc, "Tafel_QsLSV.json"))

    def luu_ket_qua(self):
        cac = self._cac_co_kq()
        if not cac:
            return
        self._nhan_xet(cac)
        p = os.path.join(self.thu_muc, "Tafel_QsLSV.json")
        try:
            tq.luu_json(p, [tq.ban_ghi(c["nhan"], c["kq"]) for c in cac])
        except OSError as e:
            messagebox.showerror("Tafel", f"Không ghi được {p}: {e}", parent=self.w)
            return
        if self.hd.get("luu"):
            self.hd["luu"](p)
        messagebox.showinfo("Tafel", f"Đã lưu hệ số Tafel của {len(cac)} mẫu. Khi chạy so sánh / nộp bài / báo cáo ở cửa sổ chính, "
                                     "cột Tafel sẽ lấy từ kết quả này (khớp theo nhãn mẫu).", parent=self.w)

    def ra_origin(self):
        cac = self._cac_co_kq()
        if not cac:
            return
        self._nhan_xet(cac)
        ky, e0 = self.kieu_y()
        p = os.path.join(self.thu_muc, "Tafel_QsLSV_origin.json")
        try:
            tq.luu_diem_json(p, cac, ky, e0)
        except OSError as e:
            messagebox.showerror("Tafel", f"Không ghi được {p}: {e}", parent=self.w)
            return
        self.hd["origin"](p)
