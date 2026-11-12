# -*- coding: utf-8 -*-
"""Cửa sổ 'Đo mặt mạng HR-TEM': bấm vào ảnh -> FFT -> chọn đốm -> đo d -> gán pha -> xuất hình chú thích.

Thay cho chuỗi thao tác ImageJ + tính tay. Mọi phép tính nằm trong hrtem.py (numpy thuần)."""
import json
import os
import shutil
import threading
import time
import types
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np

import hrtem


class CuaSoHrTem:
    PAD = 4

    def __init__(self, root, duong_dan=None):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.root = root
        self.a = None
        self.duong_dan = None
        self.nm_px = 0.0
        self.do_ds = []          # các phép đo đã thêm vào hình
        self.dinh_ds = []        # đốm của vùng hiện tại
        self.vung = None         # (cx, cy, n)
        self.chon = None         # chỉ số đốm đang chọn
        self.ket_qua = None      # kết quả đo của đốm đang chọn
        self.bang_mau = {}
        self.ann_ds = []
        self._anh_artist = None
        self._roi_patch = None
        self.ij_luu = []
        self._ij_art = []
        self._ij_tam = []
        self._ij_chon_h = None
        self._ij_chon_cuoi = None
        self._ij_h_nhung = None
        self._ij_bar = None
        self._ij_chinh = None

        w = self.w = tk.Toplevel(root)
        w.title("Đo mặt mạng HR-TEM (FFT)")
        w.geometry("1320x860")
        w.protocol("WM_DELETE_WINDOW", self._dong_cua_so)
        w.minsize(1000, 680)
        self.v_thanh = tk.StringVar(value="")
        self.v_nm_px = tk.StringVar(value="")
        self.v_thanh_px = tk.StringVar(value="")
        self.v_thanh_nm = tk.StringVar(value="10")
        self.v_vung_nm = tk.StringVar(value="10")
        self.v_dmin = tk.StringVar(value="0.15")
        self.v_dmax = tk.StringVar(value="0.45")
        self.v_z = tk.StringVar(value="3.0")
        self.v_sai = tk.StringVar(value="3")
        self.v_pha = tk.StringVar(value="")
        self.v_tp = tk.StringVar(value="")          # thành phần mẫu: "Cu:3, NiO, Fe3O4:2"
        self.v_tp_mac = tk.StringVar(value="2")     # số đốm mặc định cho mỗi thành phần
        self.v_quet_tt = tk.StringVar(value="")
        self.v_tu_kc = tk.BooleanVar(value=True)        # tự kiểm chứng bằng ImageJ sau khi quét
        self.v_dung_chung = tk.BooleanVar(value=True)   # dùng d trung vị đa phương pháp làm d của nhãn
        self.v_bo_kxn = tk.BooleanVar(value=False)      # bỏ các đốm không được ImageJ xác nhận
        self.ij_kc = None
        self._quet = None
        self.v_nhan = tk.StringVar(value="")
        self.v_so_van = tk.StringVar(value="1")
        self.v_hien_vung = tk.BooleanVar(value=False)
        self.v_tt = tk.StringVar(value="Mở ảnh HR-TEM (jpg/png/tif) để bắt đầu.")
        self.chat_rieng = ""

        # ---------- hàng 1: ảnh & thang ----------
        f1 = ttk.Frame(w)
        f1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(f1, text="Mở ảnh...", command=self.mo_anh).pack(side="left")
        ttk.Label(f1, text="  Thang: thanh").pack(side="left")
        ttk.Entry(f1, textvariable=self.v_thanh_px, width=7).pack(side="left")
        ttk.Label(f1, text="px =").pack(side="left")
        ttk.Entry(f1, textvariable=self.v_thanh_nm, width=5).pack(side="left")
        ttk.Label(f1, text="nm").pack(side="left")
        ttk.Button(f1, text="Tự đo thanh thang", command=self.do_thanh_thang).pack(side="left", padx=4)
        ttk.Button(f1, text="Áp dụng", command=self.ap_dung_thang).pack(side="left")
        ttk.Label(f1, text="   nm/px:").pack(side="left")
        ttk.Entry(f1, textvariable=self.v_nm_px, width=10).pack(side="left")
        ttk.Button(f1, text="Dùng nm/px", command=self.dung_nm_px).pack(side="left", padx=4)
        ttk.Button(f1, text="Hiệu chuẩn theo d chuẩn...", command=self.hieu_chuan).pack(side="left", padx=(12, 0))

        # ---------- hàng 2: thông số tìm đốm ----------
        f2 = ttk.Frame(w)
        f2.pack(fill="x", padx=6, pady=2)
        for ten, var, r in (("Cỡ vùng (nm)", self.v_vung_nm, 5), ("d từ", self.v_dmin, 5), ("đến (nm)", self.v_dmax, 5),
                            ("Độ nổi tối thiểu z", self.v_z, 4), ("Dung sai pha (%)", self.v_sai, 4)):
            ttk.Label(f2, text=ten + ":").pack(side="left", padx=(6, 1))
            ttk.Entry(f2, textvariable=var, width=r).pack(side="left")
        ttk.Label(f2, text="Chỉ xét pha:").pack(side="left", padx=(12, 1))
        ttk.Entry(f2, textvariable=self.v_pha, width=22).pack(side="left")
        ttk.Button(f2, text="Chọn pha...", command=self.chon_pha).pack(side="left", padx=(2, 0))
        ttk.Button(f2, text="Mặt chuẩn riêng...", command=self.mat_chuan_rieng).pack(side="left", padx=4)
        ttk.Button(f2, text="Tính lại vùng", command=self.tinh_lai).pack(side="left", padx=4)

        # ---------- hàng 3: điều khiển ImageJ ----------
        self.v_ij = tk.StringVar(value=self._doc_cfg().get("imagej") or hrtem.tim_imagej())
        self.v_ij_an = tk.BooleanVar(value=False)
        self.ij_h = None
        f2c = ttk.Frame(w)
        f2c.pack(fill="x", padx=6, pady=2)
        ttk.Label(f2c, text="Thành phần trong mẫu (vd: Cu:3, NiO, Fe3O4:2 — số sau dấu : là số đốm cần tìm):").pack(side="left")
        ttk.Entry(f2c, textvariable=self.v_tp, width=34).pack(side="left", padx=3)
        ttk.Label(f2c, text="Mặc định:").pack(side="left")
        ttk.Entry(f2c, textvariable=self.v_tp_mac, width=3).pack(side="left", padx=2)
        self.nut_quet = ttk.Button(f2c, text="Quét ảnh & tìm đốm", command=self.quet_thanh_phan)
        self.nut_quet.pack(side="left", padx=4)
        ttk.Button(f2c, text="Dừng", command=self.dung_quet).pack(side="left")
        ttk.Label(f2c, textvariable=self.v_quet_tt, foreground="#1a5fb4").pack(side="left", padx=6)
        f2d = ttk.Frame(w)
        f2d.pack(fill="x", padx=6, pady=(0, 2))
        ttk.Button(f2d, text="Kiểm chứng tất cả bằng ImageJ", command=self.kiem_chung_imagej).pack(side="left")
        ttk.Checkbutton(f2d, text="Tự kiểm chứng sau khi quét", variable=self.v_tu_kc).pack(side="left", padx=6)
        ttk.Checkbutton(f2d, text="Dùng d chung (trung vị 5 phép đo) cho nhãn", variable=self.v_dung_chung).pack(side="left", padx=6)
        ttk.Checkbutton(f2d, text="Bỏ đốm không xác nhận", variable=self.v_bo_kxn).pack(side="left", padx=6)
        f2b = ttk.Frame(w)
        f2b.pack(fill="x", padx=6, pady=2)
        ttk.Label(f2b, text="ImageJ:").pack(side="left")
        ttk.Entry(f2b, textvariable=self.v_ij, width=40).pack(side="left", padx=2)
        ttk.Button(f2b, text="Chọn...", command=self.chon_imagej).pack(side="left")
        ttk.Button(f2b, text="Tự tìm", command=self.tim_imagej).pack(side="left", padx=2)
        ttk.Checkbutton(f2b, text="Chạy nền (không hiện cửa sổ)", variable=self.v_ij_an).pack(side="left", padx=6)
        ttk.Button(f2b, text="Chạy bằng ImageJ (đốm đang chọn)", command=self.chay_imagej).pack(side="left", padx=2)
        ttk.Button(f2b, text="Lưu macro .ijm...", command=self.luu_macro).pack(side="left", padx=2)
        self.v_nut_nhung = tk.StringVar(value="Gắn ImageJ vào ảnh")
        ttk.Button(f2b, textvariable=self.v_nut_nhung, command=self.bat_tat_nhung).pack(side="left", padx=6)
        ttk.Button(f2b, text="Làm mới ImageJ", command=self.lam_moi_nhung).pack(side="left", padx=2)

        # ---------- thân: hình + bảng ----------
        than = ttk.PanedWindow(w, orient="horizontal")
        than.pack(fill="both", expand=True, padx=6, pady=2)
        trai = ttk.Frame(than)
        ngoai = ttk.Frame(than, width=490)
        cv_p = tk.Canvas(ngoai, highlightthickness=0, width=470)
        sb_p = ttk.Scrollbar(ngoai, orient="vertical", command=cv_p.yview)
        cv_p.configure(yscrollcommand=sb_p.set)
        sb_p.pack(side="right", fill="y")
        cv_p.pack(side="left", fill="both", expand=True)
        phai = ttk.Frame(cv_p)
        _cua = cv_p.create_window((0, 0), window=phai, anchor="nw")
        phai.bind("<Configure>", lambda e: cv_p.configure(scrollregion=cv_p.bbox("all")))
        cv_p.bind("<Configure>", lambda e: cv_p.itemconfigure(_cua, width=e.width))

        def _cuon(e):
            if getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0:
                cv_p.yview_scroll(-3, "units")
            else:
                cv_p.yview_scroll(3, "units")

        def _gan_cuon(_e=None):
            cv_p.bind_all("<MouseWheel>", _cuon)
            cv_p.bind_all("<Button-4>", _cuon)
            cv_p.bind_all("<Button-5>", _cuon)

        def _go_cuon(_e=None):
            cv_p.unbind_all("<MouseWheel>")
            cv_p.unbind_all("<Button-4>")
            cv_p.unbind_all("<Button-5>")
        ngoai.bind("<Enter>", _gan_cuon)
        ngoai.bind("<Leave>", _go_cuon)
        than.add(trai, weight=3)
        than.add(ngoai, weight=2)

        self.fig = Figure(figsize=(7, 7), dpi=100)
        self.ax = self.fig.add_axes([0.01, 0.01, 0.98, 0.98])
        self.ax.set_axis_off()
        self.cv = FigureCanvasTkAgg(self.fig, master=trai)
        self.tb = types.SimpleNamespace(mode="")   # tương thích: không còn thanh công cụ matplotlib
        self.v_cong_cu = tk.StringVar(value="hcn")
        self.v_toado = tk.StringVar(value="")
        self.duong = None
        self._keo = None
        self._line_art = None
        self._diem_art = None
        # ---- thanh công cụ kiểu ImageJ ----
        thanh = ttk.Frame(trai)
        thanh.pack(fill="x", pady=(0, 2))
        self._thanh = thanh
        self._nhung = None
        self._host_ij = None
        self._ij_cho = None
        self._cho_ve = False
        for ma, bt in (("hcn", "Chữ nhật"), ("duong", "Đường"), ("diem", "Điểm"), ("kinh", "Zoom"), ("tay", "Dịch")):
            ttk.Radiobutton(thanh, text=bt, value=ma, variable=self.v_cong_cu, style="Toolbutton").pack(side="left", padx=1)
        ttk.Separator(thanh, orient="vertical").pack(side="left", fill="y", padx=4)
        ttk.Button(thanh, text="Plot Profile (K)", command=self.plot_profile_duong).pack(side="left", padx=1)
        ttk.Button(thanh, text="Zoom 100%", command=lambda: self.dat_zoom(1.0)).pack(side="left", padx=1)
        ttk.Button(thanh, text="Toàn ảnh", command=self.zoom_toan_anh).pack(side="left", padx=1)
        ttk.Label(thanh, textvariable=self.v_toado, foreground="#333").pack(side="right", padx=6)
        self.cv.get_tk_widget().pack(fill="both", expand=True)
        self.cv.mpl_connect("button_press_event", self.bam_anh)
        self.cv.get_tk_widget().configure(takefocus=True)
        self.cv.mpl_connect("motion_notify_event", self.di_chuot)
        self.cv.mpl_connect("button_release_event", self.nha_chuot)
        self.cv.mpl_connect("scroll_event", self.cuon_anh)
        self.cv.mpl_connect("key_press_event", self.phim_anh)

        self.fig2 = Figure(figsize=(4.6, 3.0), dpi=100)
        self.ax_f = self.fig2.add_subplot(121)
        self.ax_p = self.fig2.add_subplot(122)
        self.fig2.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.14, wspace=0.18)
        self.cv2 = FigureCanvasTkAgg(self.fig2, master=phai)
        self.cv2.get_tk_widget().pack(fill="x")
        self.cv2.mpl_connect("button_press_event", self.bam_pho)
        self._ve_trong_pho()

        ttk.Label(phai, text="Đốm trong FFT của vùng (chọn dòng, hoặc bấm trực tiếp vào đốm trên hình FFT):").pack(anchor="w", pady=(4, 0))
        cot = ("stt", "d", "dp", "lech", "goc", "z", "gy")
        self.tv = ttk.Treeview(phai, columns=cot, show="headings", height=6, selectmode="browse")
        for c, t, wd in (("stt", "#", 28), ("d", "d FFT", 56), ("dp", "d profile ± SD", 100), ("lech", "Lệch%", 48),
                         ("goc", "Góc", 38), ("z", "z", 34), ("gy", "Gợi ý pha (lệch %)", 190)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=wd, anchor="w" if c == "gy" else "center", stretch=(c == "gy"))
        self.tv.pack(fill="x")
        self.tv.bind("<<TreeviewSelect>>", self.chon_dong)
        self.lb_canh = ttk.Label(phai, foreground="#b03030", wraplength=450, justify="left", text="")
        self.lb_canh.pack(anchor="w", pady=2)

        f3 = ttk.Frame(phai)
        f3.pack(fill="x", pady=2)
        ttk.Label(f3, text="Nhãn:").pack(side="left")
        self.cb_nhan = ttk.Combobox(f3, textvariable=self.v_nhan, width=22)
        self.cb_nhan.pack(side="left", padx=2)
        ttk.Label(f3, text="Số vân giữa 2 mũi tên (1 = một vân):").pack(side="left", padx=(6, 1))
        ttk.Entry(f3, textvariable=self.v_so_van, width=3).pack(side="left")
        ttk.Button(phai, text="Thêm đốm đang chọn vào hình", command=self.them_phep_do).pack(fill="x", pady=2)

        ttk.Label(phai, text="Các phép đo đã thêm vào hình (kéo nhãn trên ảnh để đặt lại vị trí):").pack(anchor="w", pady=(4, 0))
        self.tv2 = ttk.Treeview(phai, columns=("stt", "nhan", "d", "xy", "xn"), show="headings", height=6, selectmode="browse")
        for c, t, wd in (("stt", "#", 28), ("nhan", "Nhãn", 120), ("d", "d (nm)", 60), ("xy", "Vị trí (px)", 80), ("xn", "ImageJ", 110)):
            self.tv2.heading(c, text=t)
            self.tv2.column(c, width=wd, anchor="center")
        self.tv2.pack(fill="x")
        f4 = ttk.Frame(phai)
        f4.pack(fill="x", pady=2)
        ttk.Button(f4, text="Xóa dòng", command=self.xoa_phep_do).pack(side="left")
        ttk.Checkbutton(f4, text="Hiện khung vùng", variable=self.v_hien_vung, command=self.ve_lai_lop_phu).pack(side="left", padx=8)
        ttk.Label(phai, text="Điểm / vùng lấy từ ImageJ (điểm tự lưu khi bạn bấm Point trong ImageJ):").pack(anchor="w", pady=(6, 0))
        self.tv3 = ttk.Treeview(phai, columns=("stt", "loai", "vt", "gt"), show="headings", height=4, selectmode="browse")
        for c, t, wd in (("stt", "#", 28), ("loai", "Loại", 80), ("vt", "Vị trí (px)", 190), ("gt", "Giá trị / nm", 110)):
            self.tv3.heading(c, text=t)
            self.tv3.column(c, width=wd, anchor="center")
        self.tv3.pack(fill="x")
        f5 = ttk.Frame(phai)
        f5.pack(fill="x", pady=2)
        ttk.Button(f5, text="Lưu vùng chọn hiện tại", command=self.luu_chon_hien_tai).pack(side="left")
        ttk.Button(f5, text="Dùng làm vùng đo / FFT", command=self.dung_chon_lam_vung).pack(side="left", padx=4)
        ttk.Button(f5, text="Xóa", command=self.xoa_chon_ij).pack(side="left")
        ttk.Button(phai, text="Xuất kết quả (ảnh chú thích, bảng CSV, hình từng vùng)...", command=self.xuat).pack(fill="x", pady=(4, 2))
        ttk.Label(w, textvariable=self.v_tt, foreground="#444", wraplength=1280, justify="left").pack(fill="x", padx=8, pady=(0, 6))

        if duong_dan:
            self.nap_anh(duong_dan)

    # ====================== ẢNH & THANG ======================
    def mo_anh(self):
        p = filedialog.askopenfilename(parent=self.w, title="Chọn ảnh HR-TEM",
                                       filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp"), ("Tất cả", "*.*")])
        if p:
            self.nap_anh(p)

    def nap_anh(self, duong_dan):
        try:
            a = hrtem.doc_anh(duong_dan)
        except Exception as e:
            messagebox.showerror("HR-TEM", f"Không đọc được ảnh:\n{e}", parent=self.w)
            return
        self.a = a
        self.duong_dan = duong_dan
        self.do_ds = []
        self.dinh_ds = []
        self.vung = None
        self.ket_qua = None
        self.w.title(f"Đo mặt mạng HR-TEM - {os.path.basename(duong_dan)}")
        self.ax.clear()
        self.ax.set_axis_off()
        lo, hi = np.percentile(a, [0.5, 99.5])
        self._a8 = (np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) * 255).astype(np.uint8)
        self._anh_artist = self.ax.imshow(self._a8[:2, :2], cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        self.ax.set_xlim(-0.5, a.shape[1] - 0.5)
        self.ax.set_ylim(a.shape[0] - 0.5, -0.5)
        self.ax.set_autoscale_on(False)
        self._ve_hien_thi()
        self._roi_patch = None
        self.ann_ds = []
        self.cv.draw()
        self.do_thanh_thang(im_lang=True)
        self.cap_nhat_bang()
        self._ve_trong_pho()
        self.v_tt.set("Thanh công cụ phía trên ảnh: Chữ nhật (bấm hoặc kéo) -> FFT, Đường (đo + Plot Profile, phím K), Điểm, "
                      "Zoom (trái vào / phải ra), Dịch ảnh. Cuộn chuột để zoom.")
        self.ij_luu = []
        self._ij_tam = []
        self._ij_art = []
        self.duong = None
        self._line_art = None
        self._diem_art = None
        self._khung_tam = None

    def do_thanh_thang(self, im_lang=False):
        if self.a is None:
            return
        tb = hrtem.tim_thanh_thang(self.a)
        if tb is None:
            if not im_lang:
                messagebox.showinfo("HR-TEM", "Không tìm thấy thanh thang tự động. Nhập nm/px trực tiếp hoặc nhập độ dài thanh (px) bằng tay.",
                                    parent=self.w)
            self.v_tt.set("Chưa tìm thấy thanh thang: hãy nhập độ dài thanh (px) và nm, hoặc nhập thẳng nm/px.")
            return
        self.v_thanh_px.set(str(tb["px"]))
        self.ap_dung_thang()
        self.v_tt.set(f"Tìm thấy thanh thang dài {tb['px']} px (tính cả viền đen). Nếu thanh có viền dày, độ dài thật có thể ngắn hơn "
                      f"vài px (sai số thang cỡ 1-3%). Hãy kiểm tra bằng một mặt mạng đã biết chắc: nút 'Hiệu chuẩn theo d chuẩn'.")

    def ap_dung_thang(self):
        try:
            px = float(self.v_thanh_px.get().replace(",", "."))
            nm = float(self.v_thanh_nm.get().replace(",", "."))
            if px <= 0 or nm <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("HR-TEM", "Nhập độ dài thanh (px) và nm là số dương.", parent=self.w)
            return
        self.dat_nm_px(nm / px)

    def dung_nm_px(self):
        try:
            v = float(self.v_nm_px.get().replace(",", "."))
            if v <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("HR-TEM", "nm/px phải là số dương.", parent=self.w)
            return
        self.dat_nm_px(v)

    def dat_nm_px(self, v):
        """Đổi thang: tính lại mọi phép đo đã thêm và vùng hiện tại."""
        self.nm_px = float(v)
        self.v_nm_px.set(f"{self.nm_px:.6f}")
        for m in self.do_ds:
            self._do_lai(m)
        if self.vung:
            self.tinh_lai()
        else:
            self.cap_nhat_bang()
            self.ve_lai_lop_phu()

    def hieu_chuan(self):
        if not self.do_ds:
            messagebox.showinfo("HR-TEM", "Hãy thêm ít nhất một phép đo (mặt mạng đã biết chắc, ví dụ Cu(111)) rồi chọn dòng đó.", parent=self.w)
            return
        sel = self.tv2.selection()
        if not sel:
            messagebox.showinfo("HR-TEM", "Chọn một dòng trong bảng 'phép đo đã thêm' để làm chuẩn.", parent=self.w)
            return
        m = self.do_ds[int(sel[0])]
        from tkinter import simpledialog
        v = simpledialog.askfloat("Hiệu chuẩn", f"Mặt mạng '{hrtem.nhan_van_ban(m.get('pha', ''), m.get('hkl', ''))}' đang đo được "
                                  f"{m['d']:.4f} nm.\nNhập giá trị d chuẩn (nm) để chỉnh thang nm/px:", parent=self.w, minvalue=0.05, maxvalue=2.0)
        if not v:
            return
        he_so = v / m["d"]
        if abs(he_so - 1) > 0.08:
            if not messagebox.askyesno("Hiệu chuẩn", f"Thang sẽ đổi {100 * (he_so - 1):+.1f}%. Tiếp tục?", parent=self.w):
                return
        self.dat_nm_px(self.nm_px * he_so)
        self.v_tt.set(f"Đã hiệu chuẩn thang theo d chuẩn = {v:.4f} nm (hệ số {he_so:.4f}). Lưu ý: chỉ nên dùng khi chắc chắn về pha đó.")

    # ====================== CHỌN VÙNG & ĐỐM ======================
    def _so(self, var, mac_dinh, ten):
        try:
            return float(var.get().replace(",", "."))
        except ValueError:
            raise ValueError(f"'{ten}' phải là số.")

    # ---------- hiển thị ảnh nhanh: chỉ vẽ phần đang xem, giảm mẫu theo cỡ khung ----------
    def _lam_moi_anh(self):
        if self._cho_ve:
            return
        self._cho_ve = True
        try:
            self.w.after(20, self._ve_hien_thi)
        except Exception:
            self._ve_hien_thi()

    def _ve_hien_thi(self):
        self._cho_ve = False
        a8 = getattr(self, "_a8", None)
        if a8 is None or self._anh_artist is None:
            return
        H, W = a8.shape
        xl, xr = sorted(self.ax.get_xlim())
        yb, yt = sorted(self.ax.get_ylim())
        x0, x1 = int(max(0, np.floor(xl + 0.5))), int(min(W, np.ceil(xr + 0.5)))
        y0, y1 = int(max(0, np.floor(yb + 0.5)), ), int(min(H, np.ceil(yt + 0.5)))
        if x1 - x0 < 2 or y1 - y0 < 2:
            return
        try:
            wd = self.cv.get_tk_widget()
            muc_tieu = max(wd.winfo_width(), wd.winfo_height(), 600)
        except Exception:
            muc_tieu = 900
        if not isinstance(muc_tieu, (int, float)):
            muc_tieu = 900
        buoc = max(1, int(np.ceil(max(x1 - x0, y1 - y0) / float(muc_tieu))))
        cw, ch = (x1 - x0) // buoc * buoc, (y1 - y0) // buoc * buoc
        if cw < buoc or ch < buoc:
            return
        blk = a8[y0:y0 + ch, x0:x0 + cw]
        if buoc > 1:
            blk = blk.reshape(ch // buoc, buoc, cw // buoc, buoc).mean(axis=(1, 3)).astype(np.uint8)
        lim_x, lim_y = self.ax.get_xlim(), self.ax.get_ylim()
        self._anh_artist.set_data(blk)
        self._anh_artist.set_extent((x0 - 0.5, x0 + cw - 0.5, y0 + ch - 0.5, y0 - 0.5))
        self.ax.set_xlim(*lim_x)
        self.ax.set_ylim(*lim_y)
        self.cv.draw_idle()

    # ---------- nhúng ImageJ thật vào khung ảnh (Windows) ----------
    def bat_tat_nhung(self):
        if self._nhung is not None or self._ij_cho is not None:
            self.tach_imagej()
        else:
            self.nhung_imagej()

    def nhung_imagej(self):
        import ij_nhung
        if not ij_nhung.HOP_LE:
            messagebox.showinfo("ImageJ", "Gắn cửa sổ ImageJ vào app chỉ chạy trên Windows.", parent=self.w)
            return
        if self.a is None:
            messagebox.showinfo("ImageJ", "Hãy mở một ảnh trước.", parent=self.w)
            return
        duong = self.v_ij.get().strip()
        try:
            self._ij_cho = ij_nhung.khoi_chay_nhung(duong, self.duong_dan, self.nm_px, hrtem.thu_muc_tam_ascii())
        except Exception as e:
            self._ij_cho = None
            messagebox.showerror("ImageJ", str(e), parent=self.w)
            return
        self.v_nut_nhung.set("Đang mở ImageJ... (bấm để hủy)")
        self.v_tt.set("Đang chờ ImageJ mở ảnh rồi sẽ gắn vào khung ảnh. Lần đầu có thể mất 10-30 giây.")
        self.w.after(500, self._cho_nhung)

    def _cho_nhung(self):
        import ij_nhung
        h = self._ij_cho
        if h is None:
            return
        self._ij_h_nhung = h
        if getattr(self, "_ij_chon_h", None) is None:
            self._bat_theo_doi_chon(h)           # theo dõi vùng chọn ngay khi ImageJ mở ảnh
        thanh, anh = ij_nhung.tim_cua_so(h["ten_anh"])
        if thanh and anh:
            # đợi cửa sổ ImageJ bố trí xong (kích thước không đổi qua 3 lần kiểm) rồi mới gắn, tránh đo chiều cao quá sớm
            try:
                kt = ij_nhung.Nhung().kich_thuoc(thanh)
            except Exception:
                kt = None
            if kt is not None and kt == h.get("kt_cuoi"):
                h["on_dinh"] = h.get("on_dinh", 0) + 1
            else:
                h["on_dinh"] = 0
            h["kt_cuoi"] = kt
            if h["on_dinh"] >= 3:
                self._gan_cua_so(thanh, anh)
                return
        if h["proc"].poll() not in (None, 0) or time.time() - h["bat_dau"] > 120:
            self._ij_cho = None
            self.v_nut_nhung.set("Gắn ImageJ vào ảnh")
            messagebox.showwarning("ImageJ", "Không thấy cửa sổ ImageJ/ảnh để gắn (quá 120 giây hoặc ImageJ đã thoát). "
                                   "Kiểm tra đường dẫn ImageJ rồi thử lại.", parent=self.w)
            return
        self.w.after(500, self._cho_nhung)

    def _gan_cua_so(self, thanh, anh):
        import ij_nhung
        self._ij_cho = None
        cha = self.cv.get_tk_widget().master
        self.cv.get_tk_widget().pack_forget()
        self._thanh.pack_forget()
        self._dung_thanh_ij(cha)
        self._host_ij = tk.Frame(cha, bg="#202020")
        self._host_ij.pack(fill="both", expand=True)
        self.w.update_idletasks()
        self._nhung = ij_nhung.Nhung()
        self._th, self._tw = 0, 0
        self._hw = (thanh, anh)
        self._ij_chinh = thanh
        self._nhung.gan(anh, self._host_ij.winfo_id(), 0, 0, 400, 400)
        ij_nhung.Nhung.an_hien(thanh, False)       # cửa sổ ImageJ gốc (chỉ có menu + công cụ) thu nhỏ, công cụ nằm ở thanh của app
        self._host_ij.bind("<Configure>", self._dat_lai_nhung)
        self._dat_lai_nhung()
        self.w.after(300, self.lam_moi_nhung)
        self.v_nut_nhung.set("Tách ImageJ ra / về ảnh của app")
        self.v_tt.set("Cửa sổ ảnh ImageJ thật nằm trong khung; thanh công cụ ImageJ ở phía trên (chọn công cụ rồi thao tác trên ảnh). "
                      "Menu Analyze/Process/Image/Edit nằm ở thanh đó. Điểm bấm trong ImageJ được lưu lên ảnh app.")

    def _dung_thanh_ij(self, cha):
        """Thanh công cụ kiểu ImageJ (các công cụ chọn vùng + menu lệnh) điều khiển ImageJ thật qua macro."""
        import ij_nhung
        bar = ttk.Frame(cha)
        bar.pack(fill="x", pady=(0, 2))
        self._ij_bar = bar
        self.v_ij_tool = tk.StringVar(value="rectangle")
        h1 = ttk.Frame(bar)
        h1.pack(fill="x")
        for ma, ten in ij_nhung.CONG_CU_IJ:
            ttk.Radiobutton(h1, text=ten, value=ma, variable=self.v_ij_tool, style="Toolbutton",
                            command=lambda m=ma: self._gui_ij("tool:" + m)).pack(side="left", padx=1)
        h2 = ttk.Frame(bar)
        h2.pack(fill="x", pady=(2, 0))
        for ten_menu, muc in ij_nhung.MENU_IJ.items():
            mb = ttk.Menubutton(h2, text=ten_menu + " ▾")
            m = tk.Menu(mb, tearoff=0)
            for lenh, nhan in muc:
                m.add_command(label=nhan, command=lambda l=lenh: self._gui_ij("run:" + l))
            mb.configure(menu=m)
            mb.pack(side="left", padx=1)
        ttk.Button(h2, text="Hiện cửa sổ ImageJ gốc", command=self._hien_ij_goc).pack(side="left", padx=(8, 1))
        ttk.Button(h2, text="Làm mới ảnh", command=self.lam_moi_nhung).pack(side="left", padx=1)

    def _gui_ij(self, noi_dung):
        import ij_nhung
        h = getattr(self, "_ij_h_nhung", None)
        if not h:
            return
        try:
            ij_nhung.gui_lenh(h["lenh"], noi_dung)
        except Exception as e:
            messagebox.showwarning("ImageJ", str(e), parent=self.w)

    def _hien_ij_goc(self):
        import ij_nhung
        if getattr(self, "_ij_chinh", None):
            ij_nhung.Nhung.an_hien(self._ij_chinh, True)

    def _dat_lai_nhung(self, _e=None):
        if self._nhung is None or self._host_ij is None:
            return
        r, c = self._host_ij.winfo_width(), self._host_ij.winfo_height()
        self._nhung.dat(self._hw[1], 0, 0, r, c)

    def lam_moi_nhung(self):
        """Ép ImageJ bố trí và vẽ lại cửa sổ ảnh trong khung."""
        if self._nhung is None or self._host_ij is None:
            return
        r, c = self._host_ij.winfo_width(), self._host_ij.winfo_height()
        self._nhung.lam_moi(self._hw[1], 0, 0, r, c)

    def tach_imagej(self):
        self._ij_cho = None
        if getattr(self, "_ij_bar", None) is not None:
            try:
                self._ij_bar.destroy()
            except Exception:
                pass
            self._ij_bar = None
        if self._nhung is not None and getattr(self, "_ij_chinh", None):
            try:
                self._hien_ij_goc()
            except Exception:
                pass
        if self._nhung is not None:
            try:
                self._nhung.tach_het()
            except Exception:
                pass
            self._nhung = None
        if self._host_ij is not None:
            try:
                self._host_ij.destroy()
            except Exception:
                pass
            self._host_ij = None
            self._thanh.pack(fill="x", pady=(0, 2))
            self.cv.get_tk_widget().pack(fill="both", expand=True)
        self.v_nut_nhung.set("Gắn ImageJ vào ảnh")

    def _dong_cua_so(self):
        self.tach_imagej()           # trả cửa sổ ImageJ về màn hình trước khi hủy khung chứa (tránh làm sập Java)
        self.w.destroy()

    # ---------- đồng bộ vùng chọn từ ImageJ về ảnh trong app ----------
    def _bat_theo_doi_chon(self, h):
        self._ij_chon_h = h
        self._ij_chon_mtime = None
        self._ij_chon_cuoi = None
        self._ij_on_dinh = 0
        self.w.after(400, self._theo_doi_chon)

    def _theo_doi_chon(self):
        h = getattr(self, "_ij_chon_h", None)
        if h is None:
            return
        import ij_nhung
        try:
            mt = os.path.getmtime(h["chon"])
        except OSError:
            mt = None
        if mt is not None and mt != self._ij_chon_mtime:
            self._ij_chon_mtime = mt
            self.nhan_chon_ij(ij_nhung.doc_chon(h["chon"]))
        if mt is None and time.time() - h["bat_dau"] > 300:
            self._ij_chon_h = None
            return
        self.w.after(400, self._theo_doi_chon)

    def nhan_chon_ij(self, c):
        """Nhận vùng chọn hiện tại của ImageJ: vẽ tạm trên ảnh app; điểm (Point) tự lưu."""
        self._ij_chon_cuoi = c
        if c is not None and c["loai"] == 10:
            moi = False
            for x, y in zip(c["xs"] or [c["x"]], c["ys"] or [c["y"]]):
                if not any(abs(m["x"] - x) < 0.5 and abs(m["y"] - y) < 0.5 and m["ten"] == "Point" for m in self.ij_luu):
                    self._them_chon({"loai": 10, "ten": "Point", "x": x, "y": y, "w": 0, "h": 0, "xs": [x], "ys": [y]})
                    moi = True
            if moi:
                self.v_tt.set(f"Đã lưu điểm từ ImageJ lên ảnh: tổng {sum(1 for m in self.ij_luu if m['ten'] == 'Point')} điểm.")
        self._ve_chon_ij()

    def _them_chon(self, c):
        c = dict(c)
        xi, yi = int(round(c["x"])), int(round(c["y"]))
        if c["ten"] == "Point" and self.a is not None and 0 <= yi < self.a.shape[0] and 0 <= xi < self.a.shape[1]:
            c["gt"] = float(self.a[yi, xi])
        self.ij_luu.append(c)
        self.cap_nhat_bang_ij()
        self._ve_chon_ij()

    def luu_chon_hien_tai(self):
        c = getattr(self, "_ij_chon_cuoi", None)
        if c is None:
            messagebox.showinfo("ImageJ", "ImageJ chưa có vùng chọn nào (hoặc chưa gắn ImageJ).", parent=self.w)
            return
        self._them_chon(c)

    def xoa_chon_ij(self):
        sel = self.tv3.selection()
        if sel:
            try:
                del self.ij_luu[int(sel[0])]
            except (ValueError, IndexError):
                pass
        elif self.ij_luu:
            self.ij_luu.pop()
        self.cap_nhat_bang_ij()
        self._ve_chon_ij()

    def _mo_ta_chon(self, c):
        if c["ten"] == "Point":
            return f"({c['x']:.1f}, {c['y']:.1f})"
        if c["ten"] == "Line" and len(c["xs"]) >= 2:
            L = float(np.hypot(c["xs"][1] - c["xs"][0], c["ys"][1] - c["ys"][0]))
            return f"dài {L:.1f} px" + (f" = {L * self.nm_px:.3f} nm" if self.nm_px else "")
        return f"x={c['x']:.0f} y={c['y']:.0f} {c['w']:.0f}x{c['h']:.0f}"

    def cap_nhat_bang_ij(self):
        for i in self.tv3.get_children():
            self.tv3.delete(i)
        for i, c in enumerate(self.ij_luu):
            gt = f"{c['gt']:.0f}" if "gt" in c else (f"{max(c['w'], c['h']) * self.nm_px:.2f} nm" if self.nm_px else "")
            self.tv3.insert("", "end", iid=str(i), values=(i + 1, c["ten"], self._mo_ta_chon(c), gt))

    def _ve_chon_ij(self):
        for a in getattr(self, "_ij_art", []):
            try:
                a.remove()
            except Exception:
                pass
        self._ij_art = []
        from matplotlib.patches import Rectangle, Ellipse, Polygon

        def ve(c, mau, nhan=None, net="-"):
            ax = self.ax
            if c["ten"] == "Point":
                self._ij_art.append(ax.plot([c["x"]], [c["y"]], "+", color=mau, ms=14, mew=1.6)[0])
            elif c["ten"] == "Rectangle":
                p = Rectangle((c["x"], c["y"]), c["w"], c["h"], fill=False, ec=mau, lw=1.3, ls=net)
                ax.add_patch(p); self._ij_art.append(p)
            elif c["ten"] == "Oval":
                p = Ellipse((c["x"] + c["w"] / 2, c["y"] + c["h"] / 2), c["w"], c["h"], fill=False, ec=mau, lw=1.3, ls=net)
                ax.add_patch(p); self._ij_art.append(p)
            elif len(c["xs"]) >= 2:
                if c["ten"] in ("Line", "Polyline", "Freeline", "Angle"):
                    self._ij_art.append(ax.plot(c["xs"], c["ys"], "-", color=mau, lw=1.3)[0])
                else:
                    p = Polygon(np.column_stack([c["xs"], c["ys"]]), closed=True, fill=False, ec=mau, lw=1.3, ls=net)
                    ax.add_patch(p); self._ij_art.append(p)
            if nhan:
                self._ij_art.append(ax.annotate(nhan, (c["x"], c["y"]), xytext=(5, -12), textcoords="offset points",
                                                color=mau, fontsize=9, fontweight="bold"))

        for i, c in enumerate(self.ij_luu, 1):
            ve(c, "#00e5ff", str(i))
        c = getattr(self, "_ij_chon_cuoi", None)
        if c is not None:
            ve(c, "#ffd75e", None, "--")
        self.cv.draw_idle()

    def dung_chon_lam_vung(self):
        sel = self.tv3.selection()
        c = self.ij_luu[int(sel[0])] if sel else (self.ij_luu[-1] if self.ij_luu else getattr(self, "_ij_chon_cuoi", None))
        if c is None:
            messagebox.showinfo("ImageJ", "Chưa có điểm/vùng nào từ ImageJ.", parent=self.w)
            return
        if not self.nm_px:
            messagebox.showwarning("HR-TEM", "Chưa có thang (nm/px).", parent=self.w)
            return
        if c["ten"] == "Line" and len(c["xs"]) >= 2:
            self.duong = (c["xs"][0], c["ys"][0], c["xs"][1], c["ys"][1])
            self._ve_duong(*self.duong)
            self.plot_profile_duong()
        elif c["ten"] == "Point":
            self.chon_vung(c["x"], c["y"])
        else:
            n = int(round(max(c["w"], c["h"])))
            if n < 16:
                messagebox.showinfo("ImageJ", "Vùng quá nhỏ (< 16 px).", parent=self.w)
                return
            self.vung = (c["x"] + c["w"] / 2.0, c["y"] + c["h"] / 2.0, n)
            try:
                self.v_vung_nm.set(f"{n * self.nm_px:.2f}")      # tinh_lai lấy cỡ từ ô này
            except Exception:
                pass
            self.tinh_lai()

    # ---------- công cụ kiểu ImageJ trên ảnh ----------
    def _tren_nhan(self, ev):
        for t in self.ann_ds:
            try:
                if t.contains(ev)[0]:
                    return True
            except Exception:
                pass
        return False

    def bam_anh(self, ev):
        try:
            self.cv.get_tk_widget().focus_set()          # để phím K, +, - hoạt động
        except Exception:
            pass
        if ev.inaxes is not self.ax or self.a is None or ev.xdata is None:
            return
        cc = self.v_cong_cu.get()
        if cc == "kinh":
            self.zoom_quanh(ev.xdata, ev.ydata, 0.5 if ev.button == 1 else 2.0)
            return
        if ev.button != 1 or self._tren_nhan(ev):
            return
        if cc == "tay":
            self._keo = ("tay", ev.x, ev.y, self.ax.get_xlim(), self.ax.get_ylim())
            return
        if cc == "diem":
            self.dat_diem(ev.xdata, ev.ydata)
            return
        self._keo = (cc, ev.xdata, ev.ydata, ev.x, ev.y)

    def di_chuot(self, ev):
        if self.a is not None and ev.inaxes is self.ax and ev.xdata is not None:
            x, y = int(ev.xdata + 0.5), int(ev.ydata + 0.5)
            if 0 <= x < self.a.shape[1] and 0 <= y < self.a.shape[0]:
                self.v_toado.set(f"x={x}, y={y}, giá trị={self.a[y, x]:.0f}")
        k = self._keo
        if not k or ev.xdata is None and k[0] != "tay":
            return
        if k[0] == "tay":
            kx = (k[3][1] - k[3][0]) / max(self.ax.bbox.width, 1)
            ky = (k[4][1] - k[4][0]) / max(self.ax.bbox.height, 1)
            dx, dy = (ev.x - k[1]) * kx, (ev.y - k[2]) * ky
            self.ax.set_xlim(k[3][0] - dx, k[3][1] - dx)
            self.ax.set_ylim(k[4][0] - dy, k[4][1] - dy)
            self._lam_moi_anh()
            return
        if ev.xdata is None:
            return
        if k[0] == "duong":
            self._ve_duong(k[1], k[2], ev.xdata, ev.ydata, tam=True)
            L = np.hypot(ev.xdata - k[1], ev.ydata - k[2])
            self.v_toado.set(f"Dài={L:.0f} px" + (f" = {L * self.nm_px:.3f} nm" if self.nm_px else "")
                             + f", góc={self._goc(k[1], k[2], ev.xdata, ev.ydata):.1f}°")
        elif k[0] == "hcn":
            x0, y0, x1, y1 = self._vuong(k[1], k[2], ev.xdata, ev.ydata)
            self._ve_khung_tam(x0, y0, x1, y1)

    def nha_chuot(self, ev):
        k, self._keo = self._keo, None
        if not k or k[0] == "tay" or ev.xdata is None:
            return
        keo_px = np.hypot(ev.x - k[3], ev.y - k[4])
        if k[0] == "duong":
            if keo_px < 4:
                return
            self.duong = (k[1], k[2], ev.xdata, ev.ydata)
            self._ve_duong(*self.duong)
            L = np.hypot(ev.xdata - k[1], ev.ydata - k[2])
            self.v_tt.set(f"Đường thẳng: dài {L:.1f} px" + (f" = {L * self.nm_px:.3f} nm" if self.nm_px else "")
                          + f", góc {self._goc(*self.duong):.1f}°. Bấm 'Plot Profile (K)' để xem profile và đo d.")
        elif k[0] == "hcn":
            self._xoa_khung_tam()
            if not self.nm_px:
                messagebox.showwarning("HR-TEM", "Chưa có thang (nm/px). Bấm 'Tự đo thanh thang' hoặc nhập nm/px.", parent=self.w)
                return
            if keo_px < 6:
                self.chon_vung(k[1], k[2])
                return
            x0, y0, x1, y1 = self._vuong(k[1], k[2], ev.xdata, ev.ydata)
            n = int(round(x1 - x0))
            if n < 16:
                return
            self.vung = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, n)
            try:
                self.v_vung_nm.set(f"{n * self.nm_px:.2f}")
            except Exception:
                pass
            self.tinh_lai()

    @staticmethod
    def _goc(x0, y0, x1, y1):
        return float(np.degrees(np.arctan2(y0 - y1, x1 - x0)) % 360.0)

    @staticmethod
    def _vuong(x0, y0, x1, y1):
        n = max(abs(x1 - x0), abs(y1 - y0))
        sx = 1 if x1 >= x0 else -1
        sy = 1 if y1 >= y0 else -1
        xa, xb = sorted((x0, x0 + sx * n))
        ya, yb = sorted((y0, y0 + sy * n))
        return xa, ya, xb, yb

    def _ve_khung_tam(self, x0, y0, x1, y1):
        from matplotlib.patches import Rectangle
        self._xoa_khung_tam()
        self._khung_tam = Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="#ffd75e", lw=1.2)
        self.ax.add_patch(self._khung_tam)
        self.cv.draw_idle()

    def _xoa_khung_tam(self):
        k = getattr(self, "_khung_tam", None)
        if k is not None:
            try:
                k.remove()
            except Exception:
                pass
            self._khung_tam = None

    def _ve_duong(self, x0, y0, x1, y1, tam=False):
        if self._line_art is not None:
            try:
                self._line_art.remove()
            except Exception:
                pass
        self._line_art = self.ax.plot([x0, x1], [y0, y1], "-", color="#ffd75e", lw=1.2, marker="+", ms=7)[0]
        self.cv.draw_idle()

    def dat_diem(self, x, y):
        if self._diem_art is not None:
            try:
                self._diem_art.remove()
            except Exception:
                pass
        self._diem_art = self.ax.plot([x], [y], "+", color="#ffd75e", ms=12, mew=1.4)[0]
        xi, yi = int(x + 0.5), int(y + 0.5)
        v = self.a[yi, xi] if 0 <= yi < self.a.shape[0] and 0 <= xi < self.a.shape[1] else float("nan")
        self.v_tt.set(f"Điểm: x={xi}, y={yi}, giá trị={v:.1f}" + (f"  (vị trí {xi * self.nm_px:.2f}, {yi * self.nm_px:.2f} nm)" if self.nm_px else ""))
        self.cv.draw_idle()

    # ---- zoom ----
    def zoom_quanh(self, x, y, he_so):
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        w, h = (x1 - x0) * he_so, (y1 - y0) * he_so
        W, H = self.a.shape[1], self.a.shape[0]
        if abs(w) > 1.6 * W:
            self.zoom_toan_anh()
            return
        if abs(w) < 24:
            return
        fx = (x - x0) / (x1 - x0)
        fy = (y - y0) / (y1 - y0)
        self.ax.set_xlim(x - fx * w, x + (1 - fx) * w)
        self.ax.set_ylim(y - fy * h, y + (1 - fy) * h)
        self._lam_moi_anh()

    def cuon_anh(self, ev):
        if ev.inaxes is self.ax and self.a is not None and ev.xdata is not None:
            self.zoom_quanh(ev.xdata, ev.ydata, 0.8 if ev.button == "up" else 1.25)

    def zoom_toan_anh(self):
        if self.a is None:
            return
        self.ax.set_xlim(-0.5, self.a.shape[1] - 0.5)
        self.ax.set_ylim(self.a.shape[0] - 0.5, -0.5)
        self._lam_moi_anh()

    def dat_zoom(self, ty_le):
        """Zoom theo tỷ lệ điểm ảnh màn hình (1.0 = 100%)."""
        if self.a is None:
            return
        wd = self.cv.get_tk_widget()
        px_w, px_h = max(wd.winfo_width(), 100), max(wd.winfo_height(), 100)
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        w, h = px_w / ty_le, px_h / ty_le
        self.ax.set_xlim(cx - w / 2, cx + w / 2)
        self.ax.set_ylim(cy + h / 2, cy - h / 2)
        self._lam_moi_anh()

    def phim_anh(self, ev):
        k = (ev.key or "").lower()
        if k in ("+", "=") and ev.xdata is not None:
            self.zoom_quanh(ev.xdata, ev.ydata, 0.5)
        elif k in ("-", "_") and ev.xdata is not None:
            self.zoom_quanh(ev.xdata, ev.ydata, 2.0)
        elif k == "k":
            self.plot_profile_duong()

    # ---- Plot Profile ----
    def plot_profile_duong(self):
        if self.a is None or self.duong is None:
            messagebox.showinfo("Plot Profile", "Hãy dùng công cụ Đường kéo một đường trước.", parent=self.w)
            return
        if not self.nm_px:
            messagebox.showwarning("Plot Profile", "Chưa có thang (nm/px).", parent=self.w)
            return
        x0, y0, x1, y1 = self.duong
        L = float(np.hypot(x1 - x0, y1 - y0))
        so_mau = max(int(L) + 1, 8)
        t = np.linspace(0.0, 1.0, so_mau)
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        px, py = -uy, ux
        v = np.zeros(so_mau)
        nb = 5                                    # trung bình dải rộng 5 px (giảm nhiễu); ImageJ mặc định 1 px
        for o in range(-(nb // 2), nb // 2 + 1):
            v += hrtem.mau_song_tuyen(self.a, x0 + (x1 - x0) * t + o * px, y0 + (y1 - y0) * t + o * py)
        v /= nb
        dx = L / (so_mau - 1) * self.nm_px
        d0 = None
        if self.chon is not None and self.chon < len(self.dinh_ds):
            d0 = self.dinh_ds[self.chon]["d"]
        if d0 is None:
            d0 = hrtem.uoc_luong_chu_ky(v, dx)
        kq = hrtem.phan_tich_chuoi(v, dx, d0)
        top = tk.Toplevel(self.w)
        top.title("Plot Profile")
        top.geometry("760x460")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        fg = Figure(figsize=(7.4, 4.3), dpi=100)
        ax = fg.add_subplot(111)
        ax.plot(np.arange(so_mau) * dx, v, color="#888", lw=0.8, label="Dữ liệu gốc")
        ax.plot(kq["t_nm"], kq["vs"] + v.mean(), color="#1f77b4", lw=1.1, label="Đã lọc nền/làm mượt")
        if len(kq["dinh_nm"]):
            ax.plot(kq["dinh_nm"], np.interp(kq["dinh_nm"], kq["t_nm"], kq["vs"]) + v.mean(), "v", color="#d62728", ms=5, label="Đỉnh")
        ax.set_xlabel("Khoảng cách (nm)")
        ax.set_ylabel("Cường độ")
        tieu = "d = " + ("không xác định" if kq["d_dinh"] is None else f"{kq['d_dinh']:.3f} ± {kq['d_sd']:.3f} nm ({kq['n_van']} vân)")
        if kq["d_fft1d"]:
            tieu += f"   |   FFT 1D: {kq['d_fft1d']:.3f} nm"
        ax.set_title(tieu, fontsize=10)
        ax.legend(fontsize=8, loc="upper right")
        fg.tight_layout()
        cvp = FigureCanvasTkAgg(fg, master=top)
        cvp.get_tk_widget().pack(fill="both", expand=True)
        cvp.draw()

    def chon_vung(self, cx, cy):
        try:
            nm = self._so(self.v_vung_nm, 10, "Cỡ vùng")
        except ValueError as e:
            messagebox.showwarning("HR-TEM", str(e), parent=self.w)
            return
        n = int(round(nm / self.nm_px))
        self.vung = (float(cx), float(cy), n)
        self.tinh_lai()

    def tinh_lai(self):
        if self.a is None or self.vung is None or not self.nm_px:
            return
        try:
            dmin = self._so(self.v_dmin, 0.15, "d từ")
            dmax = self._so(self.v_dmax, 0.45, "d đến")
            zmin = self._so(self.v_z, 3, "z")
            nm = self._so(self.v_vung_nm, 10, "Cỡ vùng")
        except ValueError as e:
            messagebox.showwarning("HR-TEM", str(e), parent=self.w)
            return
        cx, cy, _ = self.vung
        n = int(round(nm / self.nm_px))
        roi, x0, y0, n = hrtem.cat_vung(self.a, cx, cy, n)
        self.vung = (x0 + n / 2.0, y0 + n / 2.0, n)
        self.roi = roi
        self.dinh_ds = hrtem.tim_dinh(roi, self.nm_px, dmin, dmax, so_dinh=8, z_min=zmin, pad=self.PAD)
        self.ket_qua_ds = [hrtem.do_mot_vung(self.a, self.vung[0], self.vung[1], n, self.nm_px, d, self.PAD) for d in self.dinh_ds]
        self.chon = 0 if self.dinh_ds else None
        self.ve_roi()
        self.cap_nhat_dinh()
        if self.dinh_ds:
            self.tv.selection_set("0")
        else:
            self.v_tt.set("Không thấy đốm nào đủ nổi trong vùng này: thử vùng có vân rõ hơn, vùng lớn hơn, hoặc giảm 'Độ nổi tối thiểu z'.")
            self.ve_pho()

    def _goi_y(self, d):
        try:
            sai = self._so(self.v_sai, 3, "Dung sai") / 100.0
        except ValueError:
            sai = 0.03
        chi = [x.strip() for x in self.v_pha.get().replace(";", ",").split(",") if x.strip()]
        return hrtem.ghep_pha(d, sai, hrtem.doc_chat_tuy_chinh(self.chat_rieng), chi or None)

    def cap_nhat_dinh(self):
        self.tv.delete(*self.tv.get_children())
        for i, (dinh, kq) in enumerate(zip(self.dinh_ds, self.ket_qua_ds)):
            dp = "-" if kq["d_dinh"] is None else f"{kq['d_dinh']:.3f} ± {kq['d_sd']:.3f}"
            lech = "-" if kq["lech_pct"] is None else f"{kq['lech_pct']:+.1f}"
            gy = "; ".join(f"{p} {h} ({l:+.1f})" for p, h, _, l in self._goi_y(dinh["d"])[:4]) or "(không khớp pha nào)"
            self.tv.insert("", "end", iid=str(i), values=(i + 1, f"{dinh['d']:.3f}", dp, lech, f"{dinh['theta']:.0f}°", f"{dinh['z']:.1f}", gy))

    def chon_dong(self, _ev=None):
        sel = self.tv.selection()
        if not sel:
            return
        self.chon = int(sel[0])
        self.ve_pho()
        kq = self.ket_qua_ds[self.chon]
        self.lb_canh.config(text="\n".join(kq["canh_bao"]))
        gy = self._goi_y(self.dinh_ds[self.chon]["d"])
        ds = [hrtem.nhan_van_ban(p, h) for p, h, _, _ in gy]
        self.cb_nhan["values"] = ds
        self.v_nhan.set(ds[0] if ds else "")
        dinh = self.dinh_ds[self.chon]
        self.v_tt.set(f"Đốm {self.chon + 1}: d = {dinh['d']:.3f} nm (FFT)" +
                      ("" if kq["d_dinh"] is None else f", {kq['d_dinh']:.3f} ± {kq['d_sd']:.3f} nm (profile, {kq['n_van']} vân)") +
                      (". Có nhiều pha cùng khớp: d một mình KHÔNG phân biệt được, cần thêm bằng chứng (XRD, SAED, XPS)."
                       if len(gy) > 1 else ""))

    # ====================== VẼ ======================
    def ve_roi(self):
        if self._roi_patch is not None:
            try:
                self._roi_patch.remove()
            except Exception:
                pass
        from matplotlib.patches import Rectangle
        cx, cy, n = self.vung
        self._roi_patch = Rectangle((cx - n / 2, cy - n / 2), n, n, fill=False, ec="#ffd75e", lw=1.2, ls="--")
        self.ax.add_patch(self._roi_patch)
        self.cv.draw_idle()

    def _ve_trong_pho(self):
        for ax in (self.ax_f, self.ax_p):
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])
        self.ax_f.set_title("FFT của vùng", fontsize=9)
        self.ax_p.set_title("Profile vuông góc vân", fontsize=9)
        self.cv2.draw_idle()

    def ve_pho(self):
        if not self.dinh_ds and self.vung is None:
            return
        roi = self.roi
        m = roi.shape[0] * self.PAD
        c = m // 2
        dmin = self._so(self.v_dmin, 0.15, "d từ")
        r_max = m * self.nm_px / max(dmin * 0.85, 0.05)
        ex = int(min(c - 2, r_max))
        self.ax_f.clear()
        fm = hrtem.anh_pho(roi, self.PAD, ex)
        self.ax_f.imshow(fm, cmap="gray", vmin=np.percentile(fm, 5), vmax=np.percentile(fm, 99.8),
                         extent=[c - ex - 0.5, c + ex + 0.5, c + ex + 0.5, c - ex - 0.5])
        for i, d in enumerate(self.dinh_ds):
            dang = (i == self.chon)
            for s in (1, -1):
                px, py = c + s * (d["px"] - c), c + s * (d["py"] - c)
                self.ax_f.plot([px], [py], "o", mfc="none", mec="#ffd75e" if dang else "#5fb0ff", ms=13 if dang else 9, mew=1.4 if dang else 1)
            if True:
                self.ax_f.annotate(f"{i + 1}: {d['d']:.2f}", (d["px"], d["py"]), xytext=(4, -9), textcoords="offset points",
                                   color="#ffd75e" if dang else "#9fd0ff", fontsize=7)
        self.ax_f.set_xticks([])
        self.ax_f.set_yticks([])
        self.ax_f.set_title("FFT (bấm vào đốm để chọn)", fontsize=9)
        self.ax_p.clear()
        if self.chon is not None:
            pr = self.ket_qua_ds[self.chon]["profile"]
            self.ax_p.plot(pr["t_nm"], pr["v"], lw=0.8, color="#666")
            self.ax_p.plot(pr["t_nm"], pr["vs"], lw=1.1, color="#1f77b4")
            if len(pr["dinh_nm"]):
                self.ax_p.plot(pr["dinh_nm"], np.interp(pr["dinh_nm"], pr["t_nm"], pr["vs"]), "v", color="#d62728", ms=4)
            kq = self.ket_qua_ds[self.chon]
            self.ax_p.set_title("d = " + ("n/a" if kq["d_dinh"] is None else f"{kq['d_dinh']:.3f} ± {kq['d_sd']:.3f} nm ({kq['n_van']} vân)"),
                                fontsize=9)
            self.ax_p.set_xlabel("nm", fontsize=8)
            self.ax_p.tick_params(labelsize=7)
            self.ax_p.set_yticks([])
        self.cv2.draw_idle()

    def bam_pho(self, ev):
        """Bấm vào FFT: chọn đốm gần nhất; nếu không có đốm nào gần thì thêm đốm thủ công tại cực đại cục bộ."""
        if ev.inaxes is not self.ax_f or self.vung is None or ev.button != 1:
            return
        m = self.roi.shape[0] * self.PAD
        c = m // 2
        gan, kc = None, 1e9
        for i, d in enumerate(self.dinh_ds):
            for s in (1, -1):
                k = np.hypot(ev.xdata - (c + s * (d["px"] - c)), ev.ydata - (c + s * (d["py"] - c)))
                if k < kc:
                    gan, kc = i, k
        if gan is not None and kc <= 12:
            self.tv.selection_set(str(gan))
            return
        d = hrtem.dinh_thu_cong(self.roi, self.nm_px, ev.ydata, ev.xdata, self.PAD)
        if d is None:
            return
        n = self.vung[2]
        self.dinh_ds.append(d)
        self.ket_qua_ds.append(hrtem.do_mot_vung(self.a, self.vung[0], self.vung[1], n, self.nm_px, d, self.PAD))
        self.cap_nhat_dinh()
        self.tv.selection_set(str(len(self.dinh_ds) - 1))

    # ====================== PHÉP ĐO ĐÃ THÊM ======================
    def them_phep_do(self):
        if self.chon is None:
            messagebox.showinfo("HR-TEM", "Chưa có đốm nào được chọn.", parent=self.w)
            return
        kq = dict(self.ket_qua_ds[self.chon])
        d = self.dinh_ds[self.chon]
        nhan = self.v_nhan.get().strip()
        pha, hkl = hrtem.tach_nhan(nhan)
        kq.update({"pha": pha, "hkl": hkl, "d": kq["d_dinh"] if kq["d_dinh"] else d["d"], "mau": hrtem.mau_theo_nhan(nhan, self.bang_mau)})
        try:
            kq["so_van"] = max(1, int(float(self.v_so_van.get())))
        except ValueError:
            kq["so_van"] = 1
        for p, h, dc, _ in self._goi_y(kq["d"]):
            if p == pha and h == hkl:
                kq["d_chuan"] = dc
        kq["profile"] = kq["profile"]
        self.do_ds.append(kq)
        self.cap_nhat_bang()
        self.ve_lai_lop_phu()

    # ---------- quét tự động theo thành phần ----------
    def quet_thanh_phan(self):
        if self.a is None:
            messagebox.showinfo("HR-TEM", "Hãy mở một ảnh trước.", parent=self.w)
            return
        if not self.nm_px:
            messagebox.showwarning("HR-TEM", "Chưa có thang (nm/px).", parent=self.w)
            return
        if self._quet is not None and not self._quet.get("xong"):
            return
        try:
            mac = max(1, int(float(self.v_tp_mac.get())))
            nm = self._so(self.v_vung_nm, 10, "Cỡ vùng")
            sai = self._so(self.v_sai, 3, "Dung sai") / 100.0
            dmin, dmax = self._so(self.v_dmin, 0.15, "d từ"), self._so(self.v_dmax, 0.45, "d đến")
            zmin = self._so(self.v_z, 3, "z")
        except ValueError as e:
            messagebox.showwarning("HR-TEM", str(e), parent=self.w)
            return
        tc = hrtem.doc_chat_tuy_chinh(self.chat_rieng)
        tp, la = hrtem.doc_thanh_phan(self.v_tp.get(), mac, tc)
        if la:
            messagebox.showwarning("HR-TEM", "Không nhận ra: " + ", ".join(la) +
                                   "\n(Dùng nút 'Chọn pha...' để xem tên pha có sẵn, hoặc 'Mặt chuẩn riêng...' để thêm pha mới.)", parent=self.w)
        if not tp:
            messagebox.showinfo("HR-TEM", "Hãy nhập ít nhất một thành phần, ví dụ: Cu:3, NiO, Fe3O4:2", parent=self.w)
            return
        st = {"tp": tp, "tc": tc, "xong": False, "huy": False, "tien": (0, 1), "kq": None, "loi": None,
              "tham_so": (nm, sai, dmin, dmax, zmin)}
        self._quet = st
        self.nut_quet.configure(state="disabled")
        threading.Thread(target=self._quet_nen, args=(st,), daemon=True).start()
        self.w.after(300, self._cho_quet)

    def _quet_nen(self, st):
        nm, sai, dmin, dmax, zmin = st["tham_so"]
        try:
            st["kq"] = hrtem.quet_theo_thanh_phan(self.a, self.nm_px, st["tp"], nm, sai, dmin, dmax, zmin, st["tc"],
                                                  tien_do=lambda i, n: st.__setitem__("tien", (i, n)),
                                                  huy=lambda: st["huy"], pad=self.PAD)
        except Exception as e:
            st["loi"] = str(e)
        st["xong"] = True

    def _cho_quet(self):
        st = self._quet
        if st is None:
            return
        if not st["xong"]:
            i, n = st["tien"]
            self.v_quet_tt.set(f"Đang quét... {100 * i // max(n, 1)}%")
            self.w.after(300, self._cho_quet)
            return
        self.nut_quet.configure(state="normal")
        self._nhan_quet(st)

    def dung_quet(self):
        if self._quet is not None and not self._quet.get("xong"):
            self._quet["huy"] = True

    def _nhan_quet(self, st):
        """Thêm các đốm tìm được vào danh sách phép đo (thay các kết quả tự động của lần quét trước)."""
        if st.get("loi"):
            self.v_quet_tt.set("")
            messagebox.showerror("HR-TEM", "Lỗi khi quét: " + st["loi"], parent=self.w)
            return
        if st["huy"]:
            self.v_quet_tt.set("Đã dừng quét.")
            return
        kq, tk = st["kq"]
        self.do_ds = [m for m in self.do_ds if not m.get("tu_dong")]
        try:
            so_van = max(1, int(float(self.v_so_van.get())))
        except ValueError:
            so_van = 1
        for r in kq:
            r["so_van"] = so_van
            r["tu_dong"] = True
            r["mau"] = hrtem.mau_theo_nhan(r["pha"] + " " + r["hkl"], self.bang_mau)
            self.do_ds.append(r)
        self.cap_nhat_bang()
        self.ve_lai_lop_phu()
        dong = []
        for k, v in tk.items():
            dong.append(f"{k}: {v['tim_duoc']}/{v['can']}" + ("" if v["tim_duoc"] >= v["can"] else f" (chỉ có {v['ung_vien']} ứng viên)"))
        self.v_quet_tt.set("Xong: " + "; ".join(dong))
        thieu = [k for k, v in tk.items() if v["tim_duoc"] < v["can"]]
        if self.v_tu_kc.get() and kq and self.v_ij.get().strip() and os.path.isfile(self.v_ij.get().strip()):
            self.w.after(200, self.kiem_chung_imagej)
        self.v_tt.set("Đã quét xong và thêm " + str(len(kq)) + " đốm lên ảnh (nhãn kéo được, bấm 'Xóa dòng' để bỏ đốm không ưng). " +
                      ("Không đủ đốm cho: " + ", ".join(thieu) + " — thử tăng dung sai, giảm ngưỡng z hoặc đổi cỡ vùng." if thieu else ""))

    def xoa_phep_do(self):
        sel = self.tv2.selection()
        if not sel:
            return
        self._dong_bo_nhan()
        del self.do_ds[int(sel[0])]
        self.cap_nhat_bang()
        self.ve_lai_lop_phu()

    def cap_nhat_bang(self):
        self.tv2.delete(*self.tv2.get_children())
        for i, m in enumerate(self.do_ds):
            self.tv2.insert("", "end", iid=str(i), values=(i + 1, hrtem.nhan_van_ban(m.get("pha", ""), m.get("hkl", "")) or "(chưa gán)",
                                                         f"{m['d']:.3f}", f"{m['x']:.0f}, {m['y']:.0f}", self._mo_ta_xn(m)))

    @staticmethod
    def _mo_ta_xn(m):
        x = m.get("xac_nhan")
        if not x:
            return ""
        if x["tan_pct"] is None:
            return "? không đủ số liệu"
        return ("✓ " if x["trang_thai"] == "xac_nhan" else "! ") + f"tản {x['tan_pct']:.1f}%"

    def _do_lai(self, m):
        """Tính lại một phép đo sau khi đổi thang (d tỉ lệ với nm/px)."""
        dinh = dict(m["dinh"])
        dinh["d"] = dinh["m"] * self.nm_px / dinh["r_pad"]
        kq = hrtem.do_mot_vung(self.a, m["x"], m["y"], m["n"], self.nm_px, dinh, self.PAD)
        for k in ("d_fft", "d_dinh", "d_sd", "d_fft1d", "lech_pct", "profile", "n_van", "canh_bao", "dinh"):
            m[k] = kq[k]
        m["d"] = kq["d_dinh"] if kq["d_dinh"] else dinh["d"]

    def _dong_bo_nhan(self):
        """Đọc lại vị trí nhãn sau khi người dùng kéo."""
        for t in self.ann_ds:
            try:
                x, y = t.xyann
                t._do["lx"], t._do["ly"] = float(x), float(y)
            except Exception:
                pass

    def ve_lai_lop_phu(self):
        self._dong_bo_nhan()
        for t in self.ann_ds:
            try:
                t.remove()
            except Exception:
                pass
        for ln in list(self.ax.lines):
            try:
                ln.remove()
            except Exception:
                pass
        for p in list(self.ax.patches):
            if p is not self._roi_patch:
                try:
                    p.remove()
                except Exception:
                    pass
        for ch in list(self.ax.texts):
            try:
                ch.remove()
            except Exception:
                pass
        if self.a is None:
            return
        self.ann_ds = hrtem.ve_lop_phu(self.ax, self.a.shape, self.nm_px, self.do_ds, self.v_hien_vung.get(), chu=9, keo_duoc=True)
        self.cv.draw_idle()

    # ====================== TUỲ CHỌN KHÁC ======================
    def chon_pha(self):
        """Hộp chọn pha (kim loại, oxit...) cần xét khi gợi ý; để trống = xét tất cả."""
        d = tk.Toplevel(self.w)
        d.title("Chọn pha cần xét")
        d.transient(self.w)
        d.geometry("460x520")
        ttk.Label(d, justify="left", wraplength=430,
                  text="Chọn các pha có thể có trong mẫu (giữ Ctrl để chọn nhiều). Càng thu hẹp theo kết quả XRD/XPS thì gợi ý càng đáng tin; "
                       "để trống là xét tất cả.").pack(padx=8, pady=6, anchor="w")
        fn = ttk.Frame(d)
        fn.pack(fill="x", padx=8)
        ten_pha = sorted(hrtem.CHAT_CHUAN)
        lb = tk.Listbox(d, selectmode="multiple", exportselection=False, height=18)
        for i, t in enumerate(ten_pha):
            lb.insert("end", f"{t}  -  {hrtem.MO_TA_PHA.get(t, '')}")
        hien = {x.strip() for x in self.v_pha.get().replace(";", ",").split(",") if x.strip()}
        for i, t in enumerate(ten_pha):
            if t in hien:
                lb.selection_set(i)

        def chon_nhom(ds):
            lb.selection_clear(0, "end")
            for i, t in enumerate(ten_pha):
                if t in ds:
                    lb.selection_set(i)
        for ten, ds in hrtem.NHOM_PHA.items():
            ttk.Button(fn, text=ten, command=lambda ds=ds: chon_nhom(ds)).pack(side="left", padx=2, pady=2)
        ttk.Button(fn, text="Bỏ chọn", command=lambda: lb.selection_clear(0, "end")).pack(side="left", padx=2)
        lb.pack(fill="both", expand=True, padx=8, pady=6)

        def ok():
            self.v_pha.set(", ".join(ten_pha[i] for i in lb.curselection()))
            d.destroy()
            if self.dinh_ds:
                self.cap_nhat_dinh()
        ttk.Button(d, text="OK", command=ok).pack(pady=6)

    def mat_chuan_rieng(self):
        d = tk.Toplevel(self.w)
        d.title("Mặt chuẩn riêng")
        d.transient(self.w)
        ttk.Label(d, justify="left", text="Mỗi dòng một pha, theo một trong hai dạng:\n  Tên (hkl) = d_nm      ví dụ  Cu2O (111) = 0.2465\n"
                                          "  Tên kiểu a=... [c=...]   ví dụ  Al fcc a=0.405   hoặc   Zn hcp a=0.2665 c=0.4947\n"
                                          "(kiểu: fcc, bcc, hcp, sc, tet). Dạng sau tự sinh các mặt thường gặp, hãy kiểm tra lại.\n"
                                          "Các pha này được thêm vào danh sách gợi ý.").pack(padx=8, pady=6)
        t = tk.Text(d, width=60, height=8)
        t.pack(padx=8)
        t.insert("1.0", self.chat_rieng)

        def ok():
            self.chat_rieng = t.get("1.0", "end").strip()
            d.destroy()
            if self.dinh_ds:
                self.cap_nhat_dinh()
        ttk.Button(d, text="OK", command=ok).pack(pady=6)

    # ====================== IMAGEJ ======================
    @staticmethod
    def _cfg_path():
        goc = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DienHoaOrigin")
        return os.path.join(goc, "hrtem_cai_dat.json")

    def _doc_cfg(self):
        try:
            with open(self._cfg_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _luu_cfg(self):
        try:
            os.makedirs(os.path.dirname(self._cfg_path()), exist_ok=True)
            with open(self._cfg_path(), "w", encoding="utf-8") as f:
                json.dump({"imagej": self.v_ij.get()}, f)
        except Exception:
            pass

    def chon_imagej(self):
        p = filedialog.askopenfilename(parent=self.w, title="Chọn ImageJ.exe (hoặc Fiji / ij.jar)",
                                       filetypes=[("ImageJ", "*.exe *.jar"), ("Tất cả", "*.*")])
        if p:
            self.v_ij.set(p)
            self._luu_cfg()

    def tim_imagej(self):
        p = hrtem.tim_imagej()
        if p:
            self.v_ij.set(p)
            self._luu_cfg()
            self.v_tt.set(f"Tìm thấy ImageJ: {p}")
        else:
            messagebox.showinfo("HR-TEM", "Không tự tìm thấy ImageJ. Bấm 'Chọn...' và trỏ tới ImageJ.exe (hoặc Fiji, ij.jar).", parent=self.w)

    def _thong_so_ij(self):
        """(x0, y0, n, d, theta) của đốm đang chọn, hoặc None kèm thông báo."""
        if self.a is None or self.vung is None or self.chon is None or not self.dinh_ds:
            messagebox.showinfo("HR-TEM", "Hãy bấm chọn một vùng và một đốm trước.", parent=self.w)
            return None
        cx, cy, n = self.vung
        d = self.dinh_ds[self.chon]
        return int(round(cx - n / 2)), int(round(cy - n / 2)), int(n), d["d"], d["theta"]

    def chay_imagej(self):
        ts = self._thong_so_ij()
        if ts is None:
            return
        x0, y0, n, d, theta = ts
        try:
            self.ij_h = hrtem.khoi_chay_imagej(self.v_ij.get().strip(), self.duong_dan, self.nm_px, x0, y0, n, d, theta,
                                               an=self.v_ij_an.get())
        except Exception as e:
            messagebox.showerror("HR-TEM", f"Không chạy được ImageJ: {e}", parent=self.w)
            return
        self._luu_cfg()
        self.ij_h["dinh_idx"] = self.chon
        self.v_tt.set("Đã gửi macro cho ImageJ, đang chờ kết quả... (lần đầu ImageJ có thể mở chậm vài chục giây)")
        self.w.after(700, self._cho_imagej)

    def _cho_imagej(self):
        h = self.ij_h
        if not h:
            return
        kq = hrtem.kiem_ketqua_imagej(h)
        if kq is None:
            if time.time() - h["bat_dau"] > 240:
                self.v_tt.set("ImageJ chưa trả kết quả sau 4 phút. Dừng ở bước: " + (hrtem.tien_trinh_imagej(h) or "(chưa bắt đầu macro)") +
                              ". Kiểm tra cửa sổ ImageJ xem có hộp thoại lỗi không. Macro nằm ở: " + h["macro"])
                self.ij_h = None
                return
            b = hrtem.tien_trinh_imagej(h)
            self.v_tt.set("Đang chờ ImageJ" + (f" - bước {b}" if b else "") + " ...")
            self.w.after(700, self._cho_imagej)
            return
        self.ij_h = None
        if not kq["ok"]:
            self.v_tt.set(f"ImageJ báo lỗi: {kq['loi']} Dừng ở bước: {kq.get('buoc') or '(chưa bắt đầu)'}. Macro: {h['macro']}")
            return
        self.nhan_ketqua_imagej(h, kq)

    def nhan_ketqua_imagej(self, h, kq):
        """Gắn kết quả ImageJ vào đốm đã chạy và in so sánh với phép đo của app."""
        i = h.get("dinh_idx")
        if i is not None and i < len(self.ket_qua_ds):
            self.ket_qua_ds[i]["imagej"] = kq
        app = self.ket_qua_ds[i] if i is not None and i < len(self.ket_qua_ds) else None
        ds = []
        for khoa, ten in (("loc", "ảnh vân lọc"), ("tho", "ảnh gốc")):
            pt = kq.get(khoa)
            if pt and pt.get("d_dinh"):
                ds.append(f"{ten}: {pt['d_dinh']:.3f} ± {pt['d_sd']:.3f} nm ({pt['n_van']} vân)")
            else:
                ds.append(f"{ten}: không đo được")
        dd = f"d FFT của app = {app['d_fft']:.3f} nm" if app else ""
        loi = ""
        pt = kq.get("loc")
        if app and pt and pt.get("d_dinh"):
            lech = 100 * (pt["d_dinh"] - app["d_fft"]) / app["d_fft"]
            loi = f" Lệch ImageJ so với app: {lech:+.1f}%" + (" (> 3%: kiểm tra lại)" if abs(lech) > 3 else " (khớp)")
        self.v_tt.set(f"ImageJ {kq.get('ij_version', '')} xong. Profile ImageJ - " + "; ".join(ds) + f". {dd}.{loi} Kết quả ở: {kq['thu_muc']}")

    # ---------- kiểm chứng hàng loạt bằng ImageJ ----------
    def kiem_chung_imagej(self):
        if not self.do_ds:
            messagebox.showinfo("ImageJ", "Chưa có phép đo nào để kiểm chứng (hãy quét theo thành phần hoặc thêm đốm).", parent=self.w)
            return
        if self.ij_kc is not None:
            return
        try:
            ds = [hrtem.vung_cho_imagej(m) for m in self.do_ds]
            self.ij_kc = hrtem.khoi_chay_imagej_lo(self.v_ij.get().strip(), self.duong_dan, self.nm_px, ds, an=self.v_ij_an.get())
        except Exception as e:
            self.ij_kc = None
            messagebox.showerror("ImageJ", f"Không chạy được ImageJ: {e}", parent=self.w)
            return
        self._luu_cfg()
        self.ij_kc["do_ds"] = list(self.do_ds)
        self.v_quet_tt.set(f"Đã gửi {len(ds)} vùng cho ImageJ...")
        self.w.after(700, self._cho_kc)

    def _cho_kc(self):
        h = self.ij_kc
        if not h:
            return
        kq = hrtem.kiem_ketqua_imagej_lo(h)
        if kq is None:
            if time.time() - h["bat_dau"] > 120 + 25 * len(h["ds"]):
                self.v_quet_tt.set("ImageJ không trả kết quả kịp. Dừng ở: " + (hrtem.tien_trinh_imagej(h) or "(chưa bắt đầu)"))
                self.ij_kc = None
                return
            self.v_quet_tt.set("ImageJ đang kiểm chứng: " + (hrtem.tien_trinh_imagej(h) or "đang mở..."))
            self.w.after(700, self._cho_kc)
            return
        self.ij_kc = None
        if not kq["ok"]:
            self.v_quet_tt.set(f"ImageJ báo lỗi: {kq['loi']} (bước: {kq.get('buoc') or '-'})")
            return
        self.nhan_kiem_chung(h, kq)

    def nhan_kiem_chung(self, h, kq):
        """Gộp kết quả ImageJ vào từng phép đo: d chung, trạng thái xác nhận; tùy chọn dùng d chung / bỏ đốm không xác nhận."""
        try:
            sai = self._so(self.v_sai, 3, "Dung sai") / 100.0
        except ValueError:
            sai = 0.03
        ds_m = h.get("do_ds", self.do_ds)
        xn = kt = 0
        for m, r in zip(ds_m, kq["ds"]):
            t = hrtem.tong_hop_xac_nhan(m, r, 3.0, sai)
            m["imagej"] = {"loc": r.get("loc"), "tho": r.get("tho"), "d_fft_ij": r.get("d_fft_ij"),
                           "fft_dom.png": r.get("fft_dom.png"), "van_loc.png": r.get("van_loc.png"), "thu_muc": r["thu_muc"]}
            m["xac_nhan"] = t
            if self.v_dung_chung.get() and t["d_chung"] and t["tan_pct"] is not None:
                m.setdefault("d_app", m["d"])
                m["d"] = t["d_chung"]
            if t["trang_thai"] == "xac_nhan":
                xn += 1
            else:
                kt += 1
        if self.v_bo_kxn.get():
            self.do_ds = [m for m in self.do_ds if (m.get("xac_nhan") or {}).get("trang_thai") != "kiem_tra"]
        self.cap_nhat_bang()
        self.ve_lai_lop_phu()
        loi = []
        for i, m in enumerate(ds_m, 1):
            for c in (m.get("xac_nhan") or {}).get("canh_bao", []):
                loi.append(f"#{i}: {c}")
        self.v_quet_tt.set(f"ImageJ: {xn} xác nhận, {kt} cần kiểm tra.")
        self.v_tt.set(f"Kiểm chứng ImageJ xong: {xn} vùng xác nhận (5 phép đo độc lập cùng d trong 3%), {kt} vùng cần kiểm tra. "
                      + (" ".join(loi[:4]) if loi else "") + f" Ảnh/kết quả ImageJ ở: {kq['thu_muc']}")

    def luu_macro(self):
        ts = self._thong_so_ij()
        if ts is None:
            return
        thu_muc = filedialog.askdirectory(parent=self.w, title="Chọn thư mục để lưu macro và ảnh vào (nên chọn đường dẫn không dấu)")
        if not thu_muc:
            return
        x0, y0, n, d, theta = ts
        try:
            m = hrtem.ghi_macro_thu_cong(os.path.join(thu_muc, "ij_" + time.strftime("%H%M%S")), self.duong_dan, self.nm_px,
                                         x0, y0, n, d, theta, self.v_ij_an.get())
        except Exception as e:
            messagebox.showerror("HR-TEM", f"Không ghi được macro: {e}", parent=self.w)
            return
        messagebox.showinfo("HR-TEM", f"Đã lưu macro:\n{m}\n\nTrong ImageJ: Plugins > Macros > Run... rồi chọn file này. "
                                      f"Kết quả (ketqua.txt và các ảnh .png) được ghi cùng thư mục.", parent=self.w)

    # ====================== XUẤT ======================
    def xuat(self):
        if self.a is None or not self.do_ds:
            messagebox.showinfo("HR-TEM", "Chưa có phép đo nào được thêm vào hình.", parent=self.w)
            return
        thu_muc = filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu kết quả", initialdir=os.path.dirname(self.duong_dan))
        if not thu_muc:
            return
        try:
            kq = self.xuat_ra(thu_muc)
        except Exception as e:
            messagebox.showerror("HR-TEM", f"Không xuất được: {e}", parent=self.w)
            return
        self.v_tt.set("Đã xuất: " + ", ".join(os.path.basename(p) for p in kq[:4]) + (f" ... (+{len(kq) - 4} file)" if len(kq) > 4 else "") +
                      f"\nThư mục: {thu_muc}")

    def xuat_ra(self, thu_muc, dpi=300):
        """Ghi ảnh chú thích (PNG+PDF), bảng CSV và hình từng vùng. Trả về list đường dẫn."""
        self._dong_bo_nhan()
        os.makedirs(thu_muc, exist_ok=True)
        ten = os.path.splitext(os.path.basename(self.duong_dan))[0][:40]
        kq = []
        for ext in ("png", "pdf"):
            kq.append(hrtem.ve_chu_thich(self.a, self.nm_px, self.do_ds, os.path.join(thu_muc, f"{ten}_chuthich.{ext}"), dpi,
                                         self.v_hien_vung.get()))
        kq.append(hrtem.ghi_csv(os.path.join(thu_muc, f"{ten}_bang_do.csv"), self.do_ds, self.nm_px))
        if self.ij_luu:
            p = os.path.join(thu_muc, f"{ten}_chon_imagej.csv")
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                f.write("stt,loai,x_px,y_px,rong_px,cao_px,gia_tri,x_nm,y_nm\n")
                for i, c in enumerate(self.ij_luu, 1):
                    nm = self.nm_px or 0
                    f.write(f"{i},{c['ten']},{c['x']:.2f},{c['y']:.2f},{c['w']:.2f},{c['h']:.2f},{c.get('gt', '')},"
                            f"{c['x'] * nm:.4f},{c['y'] * nm:.4f}\n")
            kq.append(p)
        for i, m in enumerate(self.do_ds, 1):
            ij = m.get("imagej") or {}
            for tenf in ("vung.png", "fft_dom.png", "van_loc.png", "profile_loc.png"):
                if ij.get(tenf) and os.path.isfile(ij[tenf]):
                    dich = os.path.join(thu_muc, f"{ten}_imagej{i:02d}_{tenf}")
                    shutil.copyfile(ij[tenf], dich)
                    kq.append(dich)
            kq.append(hrtem.ve_tung_vung(self.a, self.nm_px, m, m["dinh"], os.path.join(thu_muc, f"{ten}_vung_{i:02d}.png"), self.PAD))
        return kq
