#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Echem Studio - giao diện điều khiển chương trình xử lý điện hóa & vẽ Origin.
"""
import datetime
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, simpledialog, ttk
from tkinter import font as tkfont

FROZEN = getattr(sys, "frozen", False)
THU_MUC = os.path.dirname(os.path.abspath(__file__))   # thư mục chứa mã nguồn (ma_nguon khi chạy bằng exe)
DATA_DIR = os.path.join(os.environ.get("APPDATA", THU_MUC), "DienHoaOrigin")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = THU_MUC
CAI_DAT = os.path.join(DATA_DIR, "cai_dat.json")
THU_MUC_CAU_HINH = os.path.join(DATA_DIR, "cau_hinh")
THU_MUC_XEM_TRUOC = os.path.join(DATA_DIR, "xem_truoc")
THU_MUC_MAU = os.path.join(DATA_DIR, "du_lieu_mau")


def _nhap(ten):
    try:
        return __import__(ten)
    except Exception:
        return None


cn = _nhap("tu_dong_cap_nhat")
hd = _nhap("hoi_dap")
nd = _nhap("nhan_dang_nhanh")
lt = _nhap("loi_than_thien")
md = _nhap("mau_du_lieu")

THU_MUC_RA_MD = os.path.join(os.path.expanduser("~"), "Documents", "DienHoa_KetQua")
PHIEN_BAN_CAI_DAT = 3
LOAI = ["Tự nhận dạng", "LSV", "CV", "IT", "EIS", "ECSA (nhiều file CV)", "Tafel"]
BANG_MAU = ["#404040", "#f03c3c", "#1a5fd8", "#2aa55a", "#ff7f0e", "#9467bd",
            "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
CO_CONSOLE = 0x08000000 if os.name == "nt" else 0

# Giá trị mặc định của mọi tùy chọn (kiểu bool -> BooleanVar, còn lại -> StringVar)
MAC_DINH = {
    "loai": LOAI[0], "chong": True, "noi_tiep": False, "mau_chu_ky": False, "chu_ky": "",
    "ph": "13.8", "eref": "0.098", "nhan_i": "2", "chia_i": "2.15", "e_ecsa": "", "cs": "0.040",
    "tafel_min": "9.0", "tafel_max": "11.0", "dung_origin": True, "dung_csv": True, "template": "",
    "thu_muc_ra": THU_MUC_RA_MD, "rong": "1200", "co_chu": "22", "day_net": "2", "ti_le": "1.28",
    "day_khung": "3", "le_max": "0.5", "co_chu_td": "", "co_chu_ct": "", "vc_dai": "8", "vc_day": "",
    "vp_so": "1", "vp_dai": "4", "vp_day": "",
    "x_min": "", "x_max": "", "x_buoc": "", "y_min": "", "y_max": "", "y_buoc": "",
    "zoom": "90", "nang_cao": False, "xuat_excel": True, "i_muc_tieu": "10", "e_can_bang": "1.23",
}
KHOA_KHONG_VAO_CAU_HINH = {"zoom", "thu_muc_ra", "nang_cao"}
KHOA_CAU_HINH = [k for k in MAC_DINH if k not in KHOA_KHONG_VAO_CAU_HINH]
KHOA_NANG_CAO = ["day_net", "ti_le", "day_khung", "le_max", "co_chu", "co_chu_td", "co_chu_ct", "vc_dai", "vc_day",
                 "vp_so", "vp_dai", "vp_day", "x_min", "x_max", "x_buoc", "y_min", "y_max", "y_buoc", "template", "rong"]
TEN_MAC_DINH_CAU_HINH = "(Mặc định)"

GOI_Y = {
    "ph": "pH của dung dịch điện giải.\nE (RHE) = E đo + 0.0592 × pH + Eref.",
    "eref": "Điện thế chuẩn của điện cực so sánh so với SHE (V), ví dụ Hg/HgO 1M KOH ≈ 0.098 V.",
    "nhan_i": "Hệ số nhân dòng: I (mA/cm²) = i × 1000 × (hệ số nhân) ÷ (hệ số chia).",
    "chia_i": "Hệ số chia dòng, thường là diện tích điện cực (cm²) dùng để quy ra mật độ dòng.",
    "tafel": "Vùng mật độ dòng (mA/cm²) dùng để fit đường Tafel (E theo log|J|).\nVới LSV có pic nhỏ, app chỉ lấy nhánh đi lên sau cùng.",
    "e_ecsa": "Điện thế (V vs RHE) lấy dòng điện dung cho ECSA.\nĐể trống: app lấy giữa vùng chung. Chọn vùng KHÔNG có pic oxi hóa-khử để R² cao.",
    "cs": "Điện dung riêng Cs của bề mặt phẳng lý tưởng (mF/cm²). Thường 0.020–0.060 trong kiềm; mặc định 0.040.",
    "chu_ky": "Chu kỳ CV dùng để vẽ/tính. Để trống = chu kỳ cuối (ổn định nhất).",
    "chong": "Vẽ nhiều file cùng loại lên một hình để so sánh.",
    "xuat_excel": "Tạo file bao_cao_tong_hop.xlsx: Epa/Ipa, quá thế, Tafel, ECSA, cảnh báo và thông số đã dùng.",
    "i_muc_tieu": "Các mật độ dòng mục tiêu (mA/cm²) để báo cáo điện thế/quá thế, cách nhau dấu phẩy. Ví dụ: 10, 100.",
    "e_can_bang": "Điện thế cân bằng (V vs RHE) để tính quá thế. OER: 1.23 V; HER: 0 V.",
    "le_max": "Khoảng cách từ dữ liệu lớn nhất đến đầu trục, tính theo số bước chia chính (0.5 = nửa bước).",
    "day_khung": "Độ dày đường khung và trục (pt).",
    "day_net": "Độ dày đường dữ liệu.",
    "ti_le": "Tỉ lệ chiều rộng : chiều cao của khung đồ thị.",
    "co_chu": "Cỡ chữ của các số trên trục (pt).",
    "co_chu_td": "Cỡ chữ tiêu đề trục. Để trống = bằng cỡ chữ số trên trục.",
    "co_chu_ct": "Cỡ chữ chú thích. Để trống = 85% cỡ chữ tiêu đề.",
    "vc_dai": "Chiều dài vạch chia chính (pt).",
    "vp_so": "Số vạch phụ giữa 2 vạch chính. 0 = không có vạch phụ.",
    "khoang": "Để trống = tự động. 'Bước chia' là khoảng cách giữa 2 vạch chính.",
}


def python_exe():
    ghi_de = os.environ.get("ECHEM_PYTHON")
    if ghi_de:
        return ghi_de
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(cand):
            return cand
    return exe


class GoiY:
    """Chú thích nhỏ hiện khi rê chuột vào một ô."""

    def __init__(self, widget, text, tre=550):
        self.w, self.text, self.tre, self.tip, self.job = widget, text, tre, None, None
        widget.bind("<Enter>", self.len_lich, add="+")
        widget.bind("<Leave>", self.an, add="+")
        widget.bind("<ButtonPress>", self.an, add="+")

    def len_lich(self, _e=None):
        self.an()
        self.job = self.w.after(self.tre, self.hien)

    def hien(self):
        try:
            x, y = self.w.winfo_rootx() + 12, self.w.winfo_rooty() + self.w.winfo_height() + 4
            self.tip = tk.Toplevel(self.w)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=self.text, justify="left", background="#fffbe6", foreground="#222",
                     relief="solid", borderwidth=1, wraplength=340, padx=6, pady=3).pack()
        except Exception:
            self.tip = None

    def an(self, _e=None):
        if self.job:
            try:
                self.w.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


class App:
    def __init__(self, root, dnd=None):
        self.root = root
        self.dnd = dnd
        self.phien_ban = cn.doc_phien_ban_cuc_bo(THU_MUC) if cn else 0
        root.title(f"Echem Studio - Xử lý & vẽ số liệu điện hóa (LSV · CV · IT · EIS · ECSA · Tafel)  -  phiên bản {self.phien_ban}")
        root.minsize(560, 420)
        cd = self.doc_cai_dat()
        root.report_callback_exception = self.loi_khong_mong_doi

        self.q = queue.Queue()
        self.dang_chay = False
        self.che_do = None            # "chay" | "xem_truoc" | None
        self.huy = False
        self.proc = None
        self.duong_json_chay = None
        self.muc = []
        self.cd_phu = {"bo_qua_pb": int(cd.get("bo_qua_pb", 0) or 0)}
        self.nhan_zoom = tk.StringVar(value="")
        self.nhan_nc = tk.StringVar(value="")
        for k, mac in MAC_DINH.items():
            v = cd.get(k, mac)
            setattr(self, k, tk.BooleanVar(value=bool(v)) if isinstance(mac, bool) else tk.StringVar(value=str(v)))
        self.nhan_truc_x = tk.StringVar(value="Trục X:")
        self.nhan_truc_y = tk.StringVar(value="Trục Y:")
        self.hd_cau_hoi = tk.StringVar(value="")
        self.dang_hd = False
        self.cau_hinh_chon = tk.StringVar(value=TEN_MAC_DINH_CAU_HINH)

        self.dung_giao_dien()
        self.cap_nhat_trang_thai()
        self.doc_hang_doi()
        if cn:
            self.root.after(1500, lambda: self.kiem_tra_cap_nhat(im_lang=True))

    # ====================== XÂY DỰNG GIAO DIỆN ======================
    def entry(self, cha, bien, rong=6, goi_y=None, **grid):
        e = ttk.Entry(cha, textvariable=bien, width=rong)
        e.grid(**grid)
        if goi_y:
            GoiY(e, GOI_Y[goi_y])
        return e

    def dung_giao_dien(self):
        pad = {"padx": 8, "pady": 4}
        self.pad = pad
        self.khoi_tao_zoom()
        goc = ttk.Frame(self.root)
        goc.pack(fill="both", expand=True)
        nen = ttk.Style().lookup("TFrame", "background") or "#f0f0f0"
        self.canvas = tk.Canvas(goc, highlightthickness=0, bg=nen)
        self.vsb = ttk.Scrollbar(goc, orient="vertical", command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(goc, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.hsb.pack(side="bottom", fill="x")
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        main = ttk.Frame(self.canvas, padding=6)
        self.main = main
        self.cua_so_main = self.canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind("<Configure>", lambda e: self.cap_nhat_cuon())
        self.canvas.bind("<Configure>", lambda e: self.cap_nhat_cuon())

        # ---- Thanh cấu hình (preset) ----
        ft = ttk.Frame(main)
        ft.pack(fill="x", **pad)
        ttk.Label(ft, text="Cấu hình:").pack(side="left")
        self.cb_ch = ttk.Combobox(ft, textvariable=self.cau_hinh_chon, state="readonly", width=22)
        self.cb_ch.pack(side="left", padx=4)
        self.cb_ch.bind("<<ComboboxSelected>>", lambda e: self.nap_cau_hinh())
        GoiY(self.cb_ch, "Bộ thông số đã lưu (pH, Eref, diện tích, khoảng trục, cỡ chữ...). Chọn để áp dụng ngay.")
        ttk.Button(ft, text="Lưu...", width=7, command=self.luu_cau_hinh).pack(side="left")
        ttk.Button(ft, text="Xóa", width=5, command=self.xoa_cau_hinh).pack(side="left", padx=2)
        ttk.Button(ft, text="Nạp từ file...", command=self.nap_tu_file).pack(side="left")
        ttk.Checkbutton(ft, text="Hiện tùy chọn nâng cao", variable=self.nang_cao, command=self.bam_nang_cao).pack(side="left", padx=(14, 4))
        ttk.Label(ft, textvariable=self.nhan_nc, foreground="#b45f06").pack(side="left")
        self.lam_moi_ds_cau_hinh()

        # ---- 1. Bảng file ----
        f1 = ttk.LabelFrame(main, text=" 1. File số liệu thô (kéo-thả file vào bảng nếu máy có tkinterdnd2) ")
        f1.pack(fill="x", **pad)
        cot = ("nhan", "loai", "mau", "file")
        self.tv = ttk.Treeview(f1, columns=cot, show="headings", height=6, selectmode="browse")
        for c, t in (("nhan", "Nhãn chú thích"), ("loai", "Loại phép đo"), ("mau", "Màu"), ("file", "File")):
            self.tv.heading(c, text=t)
        self.tv.column("nhan", width=170, anchor="w")
        self.tv.column("loai", width=110, anchor="w")
        self.tv.column("mau", width=70, anchor="center")
        self.tv.column("file", width=330, anchor="w")
        self.tv.grid(row=0, column=0, rowspan=8, sticky="nsew", padx=(8, 0), pady=6)
        sb = ttk.Scrollbar(f1, command=self.tv.yview)
        sb.grid(row=0, column=1, rowspan=8, sticky="ns", pady=6)
        self.tv.config(yscrollcommand=sb.set)
        self.tv.bind("<Double-1>", self.bam_dup)

        for i, (ten, lenh) in enumerate([("Thêm file...", self.them_file), ("Thêm thư mục...", self.them_thu_muc),
                                         ("Đổi nhãn", self.doi_nhan), ("Đổi màu", self.doi_mau),
                                         ("▲ Lên", lambda: self.di_chuyen(-1)), ("▼ Xuống", lambda: self.di_chuyen(1)),
                                         ("Xóa mục chọn", self.xoa_chon), ("Xóa hết", self.xoa_het)]):
            ttk.Button(f1, text=ten, command=lenh).grid(row=i, column=2, sticky="ew", padx=8, pady=1)
        f1.columnconfigure(0, weight=1)
        self.bat_keo_tha()

        # ---- 2 & 3 ----
        hang = ttk.Frame(main)
        hang.pack(fill="x")
        f2 = ttk.LabelFrame(hang, text=" 2. Phép đo, quy đổi & Tafel ")
        f2.pack(side="left", fill="both", expand=True, **pad)
        f3 = ttk.LabelFrame(hang, text=" 3. Tùy chọn xuất & Origin ")
        f3.pack(side="left", fill="both", expand=True, **pad)

        ttk.Label(f2, text="Loại phép đo:").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        cb = ttk.Combobox(f2, textvariable=self.loai, values=LOAI, state="readonly", width=22)
        cb.grid(row=0, column=1, columnspan=3, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self.cap_nhat_trang_thai())

        ttk.Label(f2, text="E → RHE = E + 0.0592 ×").grid(row=1, column=0, sticky="w", padx=8)
        self.entry(f2, self.ph, 6, "ph", row=1, column=1, sticky="w")
        ttk.Label(f2, text="+").grid(row=1, column=2)
        self.entry(f2, self.eref, 6, "eref", row=1, column=3, sticky="w")

        ttk.Label(f2, text="I = i × 1000 ×").grid(row=2, column=0, sticky="e", padx=8, pady=3)
        self.entry(f2, self.nhan_i, 6, "nhan_i", row=2, column=1, sticky="w")
        ttk.Label(f2, text="÷").grid(row=2, column=2)
        self.entry(f2, self.chia_i, 6, "chia_i", row=2, column=3, sticky="w")

        cc = ttk.Checkbutton(f2, text="Vẽ chồng các file cùng loại", variable=self.chong)
        cc.grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 0))
        GoiY(cc, GOI_Y["chong"])

        ttk.Label(f2, text="Vùng dòng Tafel (mA):").grid(row=4, column=0, sticky="w", padx=8, pady=(6, 2))
        f_tafel = ttk.Frame(f2)
        f_tafel.grid(row=4, column=1, columnspan=3, sticky="w")
        self.en_tf_min = ttk.Entry(f_tafel, textvariable=self.tafel_min, width=5)
        self.en_tf_min.pack(side="left")
        ttk.Label(f_tafel, text=" đến ").pack(side="left")
        self.en_tf_max = ttk.Entry(f_tafel, textvariable=self.tafel_max, width=5)
        self.en_tf_max.pack(side="left")
        GoiY(self.en_tf_min, GOI_Y["tafel"])
        GoiY(self.en_tf_max, GOI_Y["tafel"])

        ttk.Label(f2, text="ECSA E (V vs RHE):").grid(row=5, column=0, sticky="w", padx=8, pady=3)
        self.en_e_ecsa = self.entry(f2, self.e_ecsa, 6, "e_ecsa", row=5, column=1, sticky="w")
        ttk.Label(f2, text="Cs (mF/cm²):").grid(row=5, column=2, sticky="e")
        self.en_cs = self.entry(f2, self.cs, 6, "cs", row=5, column=3, sticky="w")

        ttk.Label(f2, text="Chu kỳ CV dùng:").grid(row=6, column=0, sticky="w", padx=8, pady=3)
        self.entry(f2, self.chu_ky, 6, "chu_ky", row=6, column=1, sticky="w")
        ttk.Label(f2, foreground="#666", text="(để trống = chu kỳ cuối)").grid(row=6, column=2, columnspan=2, sticky="w")

        ttk.Checkbutton(f3, text="Vẽ bằng Origin 2024", variable=self.dung_origin).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=3)
        ttk.Checkbutton(f3, text="Xuất CSV & Ảnh Matplotlib", variable=self.dung_csv).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=8)
        ttk.Label(f3, text="Thư mục kết quả:").grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 0))
        ttk.Entry(f3, textvariable=self.thu_muc_ra).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(8, 0))
        ttk.Button(f3, text="Chọn...", command=self.chon_thu_muc).grid(row=3, column=2, padx=6)

        self.sub_f3 = ttk.Frame(f3)
        self.sub_f3.grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))
        for r, cac in enumerate([[("Dày nét", "day_net", 4), ("Tỉ lệ R:C", "ti_le", 5)],
                                 [("Dày khung", "day_khung", 4), ("Đệm trục (bước)", "le_max", 4)]]):
            for c, (nhan, k, rong) in enumerate(cac):
                ttk.Label(self.sub_f3, text=nhan).grid(row=r, column=c * 2, sticky="e", padx=(0, 2), pady=1)
                self.entry(self.sub_f3, getattr(self, k), rong, k, row=r, column=c * 2 + 1, padx=(0, 6), pady=1)

        cx = ttk.Checkbutton(f3, text="Xuất báo cáo Excel (bao_cao_tong_hop.xlsx)", variable=self.xuat_excel)
        cx.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 0))
        GoiY(cx, GOI_Y["xuat_excel"])
        fr = ttk.Frame(f3)
        fr.grid(row=6, column=0, columnspan=3, sticky="w", padx=8, pady=(2, 4))
        ttk.Label(fr, text="I mục tiêu (mA/cm²):").grid(row=0, column=0, sticky="e")
        self.entry(fr, self.i_muc_tieu, 9, "i_muc_tieu", row=0, column=1, padx=(2, 8))
        ttk.Label(fr, text="E cân bằng (V):").grid(row=0, column=2, sticky="e")
        self.entry(fr, self.e_can_bang, 6, "e_can_bang", row=0, column=3, padx=(2, 0))
        f3.columnconfigure(1, weight=1)

        # ---- 3b & 4 (nâng cao) ----
        self.f3b = ttk.LabelFrame(main, text=" 3b. Cỡ chữ & vạch chia trục (Origin) ")
        nhom = [("Cỡ chữ (pt):", [("Số trên trục", "co_chu"), ("Tiêu đề trục", "co_chu_td"), ("Chú thích", "co_chu_ct")]),
                ("Vạch chính:", [("Dài", "vc_dai"), ("Dày", "vc_day")]),
                ("Vạch phụ:", [("Số vạch giữa 2 vạch chính", "vp_so"), ("Dài", "vp_dai"), ("Dày", "vp_day")])]
        for r, (tieu_de, cac) in enumerate(nhom):
            ttk.Label(self.f3b, text=tieu_de).grid(row=r, column=0, sticky="w", padx=8, pady=2)
            for c, (nh, k) in enumerate(cac):
                ttk.Label(self.f3b, text=nh).grid(row=r, column=1 + c * 2, sticky="e", padx=(6, 2))
                self.entry(self.f3b, getattr(self, k), 6, k if k in GOI_Y else None, row=r, column=2 + c * 2, padx=(0, 4), sticky="w")
        ttk.Label(self.f3b, foreground="#666", text="Để trống: tiêu đề = cỡ chữ số trục; chú thích = 85% tiêu đề; độ dày vạch = dày khung. "
                  "Bước chia chính chỉnh ở ô \"Bước chia\" mục 4.").grid(row=3, column=0, columnspan=8, sticky="w", padx=8, pady=(0, 4))

        self.f4 = ttk.LabelFrame(main, text=" 4. Khoảng trục đồ thị Origin  (để trống = tự động) ")
        for r, (nh, cac) in enumerate([(self.nhan_truc_x, ("x_min", "x_max", "x_buoc")),
                                       (self.nhan_truc_y, ("y_min", "y_max", "y_buoc"))]):
            ttk.Label(self.f4, textvariable=nh, width=26, anchor="w").grid(row=r, column=0, padx=8, pady=2, sticky="w")
            for c, (ten, nhan) in enumerate(zip(cac, ("Từ", "Đến", "Bước chia"))):
                ttk.Label(self.f4, text=nhan).grid(row=r, column=1 + c * 2, sticky="e", padx=(6, 2))
                self.entry(self.f4, getattr(self, ten), 8, "khoang", row=r, column=2 + c * 2, padx=(0, 4))
        ttk.Button(self.f4, text="Xóa (tự động)", command=self.xoa_khoang).grid(row=0, column=8, rowspan=2, padx=12)

        # ---- 5. Hỏi đáp ----
        self.f5 = ttk.LabelFrame(main, text=" 5. Hỏi đáp về dữ liệu (tiếng Việt, không cần AI / Internet) ")
        self.f5.pack(fill="x", **pad)
        self.en_hd = ttk.Entry(self.f5, textvariable=self.hd_cau_hoi)
        self.en_hd.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=6)
        self.en_hd.bind("<Return>", lambda e: self.hoi_dap())
        self.nut_hd = ttk.Button(self.f5, text="Hỏi", command=self.hoi_dap)
        self.nut_hd.grid(row=0, column=1, padx=4, ipadx=14)
        ttk.Button(self.f5, text="Gợi ý câu hỏi", command=self.goi_y_hoi_dap).grid(row=0, column=2, padx=(0, 8))
        ttk.Label(self.f5, foreground="#666",
                  text="VD: điện thế tại 10 mA của các mẫu · quá thế tại 10 mA · dòng tại 1.6 V · tafel · ecsa · liệt kê các file").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))
        self.f5.columnconfigure(0, weight=1)

        # ---- Nút điều khiển ----
        fb = ttk.Frame(main)
        fb.pack(fill="x", **pad)
        self.nut_chay = ttk.Button(fb, text="▶  CHẠY XỬ LÝ & VẼ", command=self.bam_chay)
        self.nut_chay.pack(side="left", ipadx=24, ipady=6)
        self.nut_dung = ttk.Button(fb, text="Dừng", command=self.bam_dung, state="disabled")
        self.nut_dung.pack(side="left", padx=(8, 0), ipady=6)
        self.nut_xem = ttk.Button(fb, text="Xem trước hình", command=lambda: self.bam_chay(xem_truoc=True))
        self.nut_xem.pack(side="left", padx=(8, 0), ipady=6)
        GoiY(self.nut_xem, "Vẽ nhanh bằng Matplotlib và xem ngay trong app (không cần Origin, không ghi vào thư mục kết quả).")
        ttk.Button(fb, text="Mở thư mục kết quả", command=self.mo_thu_muc).pack(side="left", padx=(8, 0), ipady=6)
        ttk.Button(fb, text="Mở báo cáo Excel", command=self.mo_bao_cao).pack(side="left", padx=(8, 0), ipady=6)
        self.thanh = ttk.Progressbar(fb, mode="indeterminate", length=110)
        self.thanh.pack(side="left", padx=10)

        fb2 = ttk.Frame(main)
        fb2.pack(fill="x", padx=8, pady=(0, 4))
        for ten, lenh in (("Hướng dẫn", self.mo_huong_dan), ("Dữ liệu mẫu", self.mo_du_lieu_mau),
                          ("Mở nhật ký", self.mo_nhat_ky), ("Kiểm tra cập nhật", lambda: self.kiem_tra_cap_nhat(False)),
                          ("Giới thiệu", self.mo_gioi_thieu)):
            ttk.Button(fb2, text=ten, command=lenh).pack(side="left", padx=(0, 6))
        fz = ttk.Frame(fb2)
        fz.pack(side="right")
        ttk.Label(fz, text="Thu phóng:").pack(side="left")
        ttk.Button(fz, text="−", width=3, command=lambda: self.doi_zoom(-10)).pack(side="left", padx=(4, 0))
        ttk.Label(fz, textvariable=self.nhan_zoom, width=5, anchor="center").pack(side="left")
        ttk.Button(fz, text="+", width=3, command=lambda: self.doi_zoom(10)).pack(side="left")
        ttk.Button(fz, text="100%", width=5, command=lambda: self.doi_zoom(dat=100)).pack(side="left", padx=(4, 0))

        fl = ttk.LabelFrame(main, text=" Báo cáo & Thông số tính toán ")
        fl.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(fl, height=10, state="disabled", font=self.font_log)
        self.log.pack(fill="both", expand=True, padx=6, pady=6)
        self.log.tag_configure("canh_bao", foreground="#b45f06")
        self.log.tag_configure("loi", foreground="#c00000")
        self.log.tag_configure("tot", foreground="#1b7f3b")

        r = self.root
        r.bind_all("<Control-MouseWheel>", lambda e: (self.doi_zoom(10 if e.delta > 0 else -10), "break")[1])
        for k in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            r.bind_all(k, lambda e: self.doi_zoom(10))
        for k in ("<Control-minus>", "<Control-KP_Subtract>"):
            r.bind_all(k, lambda e: self.doi_zoom(-10))
        for k in ("<Control-Key-0>", "<Control-KP_0>"):
            r.bind_all(k, lambda e: self.doi_zoom(dat=100))
        r.bind_all("<MouseWheel>", self.cuon_chuot)
        self.hien_nang_cao(ap_dung_kich_thuoc=False)
        self.ap_dung_zoom()

    # ====================== NÂNG CAO / THU PHÓNG ======================
    def bam_nang_cao(self):
        self.hien_nang_cao()
        self.luu_cai_dat()

    def hien_nang_cao(self, ap_dung_kich_thuoc=True):
        bat = self.nang_cao.get()
        self.f3b.pack_forget()
        self.f4.pack_forget()
        if bat:
            self.f3b.pack(fill="x", before=self.f5, **self.pad)
            self.f4.pack(fill="x", before=self.f5, **self.pad)
            self.sub_f3.grid()
            self.nhan_nc.set("")
        else:
            self.sub_f3.grid_remove()
            khac = [k for k in KHOA_NANG_CAO if self.gia_tri(k) != MAC_DINH[k]]
            self.nhan_nc.set("(đang áp dụng cài đặt nâng cao đã lưu)" if khac else "")
        if ap_dung_kich_thuoc:
            self.vua_man_hinh()

    def khoi_tao_zoom(self):
        self.font_goc = {}
        for ten in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                    "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
            try:
                self.font_goc[ten] = tkfont.nametofont(ten).cget("size")
            except Exception:
                pass
        self.font_log = tkfont.Font(family="Consolas", size=9)
        self.cot_goc = {"nhan": 170, "loai": 110, "mau": 70, "file": 330}
        self.kieu = ttk.Style()
        try:
            self.dpi = max(1.0, min(3.0, self.root.winfo_fpixels("1i") / 96.0))
        except Exception:
            self.dpi = 1.0

    def lay_zoom(self):
        try:
            return max(60, min(200, int(float(self.zoom.get()))))
        except ValueError:
            return 90

    def doi_zoom(self, delta=None, dat=None):
        z = dat if dat is not None else self.lay_zoom() + delta
        self.zoom.set(str(max(60, min(200, z))))
        self.ap_dung_zoom()
        self.luu_cai_dat()

    def ap_dung_zoom(self):
        z = self.lay_zoom()
        self.nhan_zoom.set(f"{z}%")
        for ten, co in self.font_goc.items():
            try:
                moi = max(6, int(round(abs(co) * z / 100)))
                tkfont.nametofont(ten).configure(size=moi if co > 0 else -moi)
            except Exception:
                pass
        self.font_log.configure(size=max(6, int(round(9 * z / 100))))
        self.kieu.configure("Treeview", rowheight=max(14, int(round(22 * z / 100 * self.dpi))))
        for c, w in self.cot_goc.items():
            self.tv.column(c, width=int(w * z / 100 * self.dpi))
        self.vua_man_hinh()

    def vua_man_hinh(self):
        """Đặt cửa sổ vừa nội dung nhưng không vượt quá màn hình."""
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w = min(self.main.winfo_reqwidth() + self.vsb.winfo_reqwidth() + 8, sw - 40)
        h = min(self.main.winfo_reqheight() + self.hsb.winfo_reqheight() + 8, sh - 90)
        self.root.geometry(f"{max(w, 560)}x{max(h, 420)}")
        self.cap_nhat_cuon()

    def cap_nhat_cuon(self):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        rw, rh = self.main.winfo_reqwidth(), self.main.winfo_reqheight()
        w, h = max(cw, rw), max(ch, rh)
        self.canvas.itemconfigure(self.cua_so_main, width=w, height=h)
        self.canvas.configure(scrollregion=(0, 0, w, h))

    def cuon_chuot(self, event):
        try:
            if event.widget.winfo_class() in ("Text", "Treeview", "Listbox", "TCombobox"):
                return
        except Exception:
            return
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    # ====================== HỎI ĐÁP ======================
    def goi_y_hoi_dap(self):
        if hd:
            self.q.put("\n" + hd.GOI_Y + "\n")

    def hoi_dap(self):
        if self.dang_hd or hd is None:
            return
        cau = self.hd_cau_hoi.get().strip()
        if not cau:
            return
        try:
            if not self.muc:
                raise ValueError("Chưa chọn file số liệu nào (mục 1).")
            loai = self.loai.get()
            nc = hd.NguCanh([(m["path"], m["nhan"]) for m in self.muc],
                            self.so(self.ph, "pH"), self.so(self.eref, "Eref"),
                            self.so(self.nhan_i, "hệ số nhân I", duong=True),
                            self.so(self.chia_i, "hệ số chia I", duong=True),
                            loai if loai in ("LSV", "CV", "IT", "EIS") else None)
        except ValueError as e:
            messagebox.showwarning("Thông báo", str(e))
            return
        self.dang_hd = True
        self.nut_hd.config(state="disabled")
        self.hd_cau_hoi.set("")
        self.q.put(f"\n=== Hỏi: {cau} ===\n")

        def nen():
            try:
                self.q.put(hd.tra_loi(cau, nc) + "\n")
            except Exception as e:
                self.q.put(f"[LỖI] {e}\n")
            self.q.put(("hd_xong",))
        threading.Thread(target=nen, daemon=True).start()

    def xoa_khoang(self):
        for k in ("x_min", "x_max", "x_buoc", "y_min", "y_max", "y_buoc"):
            getattr(self, k).set("")

    def cap_nhat_trang_thai(self):
        loai_val = self.loai.get()
        nhan_truc = {"LSV": ("E (V vs RHE)", "I (mA/cm²)"), "CV": ("E (V vs RHE)", "I (mA/cm²)"),
                     "IT": ("T (h)", "I (mA/cm²)"), "EIS": ("Z' (Ω)", "-Z'' (Ω)"),
                     "ECSA": ("E (V vs RHE)", "I (mA/cm²)"), "Tafel": ("Log(J)", "E (V vs RHE)")}
        nx, ny = next((v for k, v in nhan_truc.items() if loai_val.startswith(k)), ("E / T / Z' / Log(J)", "I / -Z'' / E"))
        self.nhan_truc_x.set(f"Trục X - {nx}")
        self.nhan_truc_y.set(f"Trục Y - {ny}")
        ecsa = loai_val.startswith("ECSA")
        tafel = loai_val.startswith("Tafel")
        self.en_e_ecsa.config(state="normal" if ecsa else "disabled")
        self.en_cs.config(state="normal" if ecsa else "disabled")
        self.en_tf_min.config(state="normal" if tafel else "disabled")
        self.en_tf_max.config(state="normal" if tafel else "disabled")

    # ====================== BẢNG FILE ======================
    def nhan_dang(self, p):
        if nd is None:
            return "?"
        try:
            return nd.phat_hien(p)["mo_ta"]
        except Exception:
            return "?"

    def lam_moi_bang(self, chon=None):
        for i in self.tv.get_children():
            self.tv.delete(i)
        for k, m in enumerate(self.muc):
            tag = f"c{k}"
            self.tv.insert("", "end", iid=str(k), values=(m["nhan"], m.get("loai_nhan", "?"), m["mau"], m["path"]), tags=(tag,))
            try:
                self.tv.tag_configure(tag, foreground=m["mau"])
            except Exception:
                pass
        if chon is not None and 0 <= chon < len(self.muc):
            self.tv.selection_set(str(chon))

    def chi_so_chon(self):
        s = self.tv.selection()
        return int(s[0]) if s else None

    def them_cac_file(self, ds):
        """Thêm file hoặc thư mục (lấy các file .txt/.csv/.dat bên trong)."""
        moi = []
        for p in ds:
            p = os.path.normpath(p)
            if os.path.isdir(p):
                for ten in sorted(os.listdir(p)):
                    if ten.lower().endswith((".txt", ".csv", ".dat")):
                        moi.append(os.path.join(p, ten))
            else:
                moi.append(p)
        so_them = 0
        for p in moi:
            if any(m["path"] == p for m in self.muc):
                continue
            k = len(self.muc)
            self.muc.append({"path": p, "nhan": os.path.splitext(os.path.basename(p))[0],
                             "mau": BANG_MAU[k % len(BANG_MAU)], "loai_nhan": self.nhan_dang(p)})
            so_them += 1
        self.lam_moi_bang()
        return so_them

    def them_file(self):
        ds = filedialog.askopenfilenames(title="Chọn file", filetypes=[("Dữ liệu", "*.txt *.csv *.dat"), ("Tất cả", "*.*")])
        if ds:
            self.them_cac_file(ds)

    def them_thu_muc(self):
        p = filedialog.askdirectory(title="Chọn thư mục chứa file số liệu")
        if p:
            n = self.them_cac_file([p])
            if n == 0:
                messagebox.showinfo("Thông báo", "Không tìm thấy file .txt/.csv/.dat mới trong thư mục này.")

    def bat_keo_tha(self):
        if not self.dnd:
            return
        try:
            self.tv.drop_target_register(self.dnd[1])
            self.tv.dnd_bind("<<Drop>>", lambda e: self.them_cac_file(self.root.tk.splitlist(e.data)))
        except Exception:
            pass

    def xoa_chon(self):
        k = self.chi_so_chon()
        if k is not None:
            del self.muc[k]
            self.lam_moi_bang(min(k, len(self.muc) - 1))

    def xoa_het(self):
        self.muc.clear()
        self.lam_moi_bang()

    def di_chuyen(self, huong):
        k = self.chi_so_chon()
        if k is None:
            return
        j = k + huong
        if 0 <= j < len(self.muc):
            self.muc[k], self.muc[j] = self.muc[j], self.muc[k]
            self.lam_moi_bang(j)

    def doi_nhan(self):
        k = self.chi_so_chon()
        if k is None:
            return
        moi = simpledialog.askstring("Đổi nhãn", "Nhãn hiển thị:", initialvalue=self.muc[k]["nhan"], parent=self.root)
        if moi is not None and moi.strip():
            self.muc[k]["nhan"] = moi.strip()
            self.lam_moi_bang(k)

    def doi_mau(self):
        k = self.chi_so_chon()
        if k is None:
            return
        kq = colorchooser.askcolor(color=self.muc[k]["mau"], title="Chọn màu")
        if kq and kq[1]:
            self.muc[k]["mau"] = kq[1]
            self.lam_moi_bang(k)

    def bam_dup(self, event):
        hang = self.tv.identify_row(event.y)
        cot = self.tv.identify_column(event.x)
        if not hang:
            return
        self.tv.selection_set(hang)
        if cot == "#3":
            self.doi_mau()
        elif cot == "#4":
            return
        else:
            self.doi_nhan()

    def chon_thu_muc(self):
        p = filedialog.askdirectory(title="Chọn thư mục")
        if p:
            self.thu_muc_ra.set(p)

    # ====================== MỞ FILE / THƯ MỤC ======================
    def mo_duong_dan(self, p):
        try:
            os.startfile(p)
        except AttributeError:
            messagebox.showinfo("Đường dẫn", p)
        except OSError as e:
            messagebox.showwarning("Không mở được", f"{p}\n\n{e}")

    def mo_thu_muc(self):
        p = self.thu_muc_ra.get()
        os.makedirs(p, exist_ok=True)
        self.mo_duong_dan(p)

    def mo_bao_cao(self):
        d = self.thu_muc_ra.get()
        for ten in ("bao_cao_tong_hop.xlsx", "bao_cao_tong_hop.csv"):
            p = os.path.join(d, ten)
            if os.path.exists(p):
                self.mo_duong_dan(p)
                return
        messagebox.showinfo("Báo cáo", "Chưa có báo cáo trong thư mục kết quả.\nHãy tick 'Xuất báo cáo Excel' rồi bấm CHẠY.")

    def mo_nhat_ky(self):
        p = os.path.join(DATA_DIR, "nhat_ky.log")
        if not os.path.exists(p):
            messagebox.showinfo("Nhật ký", "Chưa có nhật ký (chưa chạy lần nào hoặc chưa có lỗi).")
            return
        self.mo_duong_dan(p)

    # ====================== CÀI ĐẶT & CẤU HÌNH ======================
    def gia_tri(self, k):
        return getattr(self, k).get()

    def doc_cai_dat(self):
        try:
            with open(CAI_DAT, "r", encoding="utf-8") as f:
                cd = json.load(f)
            return cd if cd.get("ver") == PHIEN_BAN_CAI_DAT else {}
        except Exception:
            return {}

    def luu_cai_dat(self):
        cd = {"ver": PHIEN_BAN_CAI_DAT, "bo_qua_pb": self.cd_phu.get("bo_qua_pb", 0)}
        for k in MAC_DINH:
            cd[k] = self.gia_tri(k)
        try:
            with open(CAI_DAT, "w", encoding="utf-8") as f:
                json.dump(cd, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def ds_cau_hinh(self):
        try:
            return sorted(os.path.splitext(f)[0] for f in os.listdir(THU_MUC_CAU_HINH) if f.lower().endswith(".json"))
        except OSError:
            return []

    def lam_moi_ds_cau_hinh(self):
        self.cb_ch.config(values=[TEN_MAC_DINH_CAU_HINH] + self.ds_cau_hinh())

    def du_lieu_cau_hinh(self):
        return {k: self.gia_tri(k) for k in KHOA_CAU_HINH}

    def ap_dung_cau_hinh(self, d):
        for k in KHOA_CAU_HINH:
            if k in d:
                var = getattr(self, k)
                var.set(bool(d[k]) if isinstance(var, tk.BooleanVar) else str(d[k]))
        if any(self.gia_tri(k) != MAC_DINH[k] for k in KHOA_NANG_CAO):
            self.nang_cao.set(True)
        self.cap_nhat_trang_thai()
        self.hien_nang_cao()
        self.luu_cai_dat()

    def nap_cau_hinh(self):
        ten = self.cau_hinh_chon.get()
        if ten == TEN_MAC_DINH_CAU_HINH:
            self.ap_dung_cau_hinh({k: MAC_DINH[k] for k in KHOA_CAU_HINH})
            self.q.put("Đã khôi phục thông số mặc định.\n")
            return
        try:
            with open(os.path.join(THU_MUC_CAU_HINH, ten + ".json"), "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            messagebox.showerror("Cấu hình", f"Không đọc được cấu hình '{ten}':\n{e}")
            return
        self.ap_dung_cau_hinh(d.get("cai_dat", d))
        self.q.put(f"Đã áp dụng cấu hình '{ten}'.\n")

    def luu_cau_hinh(self):
        ten = simpledialog.askstring("Lưu cấu hình", "Tên cấu hình (vd: OER Cu pH 13.8):", parent=self.root)
        if not ten or not ten.strip():
            return
        an_toan = "".join(c for c in ten.strip() if c not in '\\/:*?"<>|')[:60].strip()
        if not an_toan or an_toan == TEN_MAC_DINH_CAU_HINH:
            messagebox.showwarning("Cấu hình", "Tên không hợp lệ.")
            return
        try:
            os.makedirs(THU_MUC_CAU_HINH, exist_ok=True)
            with open(os.path.join(THU_MUC_CAU_HINH, an_toan + ".json"), "w", encoding="utf-8") as f:
                json.dump({"ten": an_toan, "phien_ban": self.phien_ban, "cai_dat": self.du_lieu_cau_hinh()},
                          f, ensure_ascii=False, indent=1)
        except OSError as e:
            messagebox.showerror("Cấu hình", f"Không lưu được: {e}")
            return
        self.lam_moi_ds_cau_hinh()
        self.cau_hinh_chon.set(an_toan)
        self.q.put(f"Đã lưu cấu hình '{an_toan}'.\n")

    def xoa_cau_hinh(self):
        ten = self.cau_hinh_chon.get()
        if ten == TEN_MAC_DINH_CAU_HINH:
            return
        if not messagebox.askyesno("Xóa cấu hình", f"Xóa cấu hình '{ten}'?"):
            return
        try:
            os.remove(os.path.join(THU_MUC_CAU_HINH, ten + ".json"))
        except OSError:
            pass
        self.lam_moi_ds_cau_hinh()
        self.cau_hinh_chon.set(TEN_MAC_DINH_CAU_HINH)

    def nap_tu_file(self):
        p = filedialog.askopenfilename(title="Chọn file cấu hình hoặc thong_so_chay*.json",
                                       filetypes=[("JSON", "*.json"), ("Tất cả", "*.*")])
        if not p:
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            messagebox.showerror("Cấu hình", f"Không đọc được file:\n{e}")
            return
        self.ap_dung_cau_hinh(d.get("cai_dat", d))
        files = d.get("files") or []
        con_lai = [x["path"] for x in files if isinstance(x, dict) and os.path.exists(x.get("path", ""))]
        if con_lai and messagebox.askyesno("Nạp lại danh sách file", f"File này có kèm {len(files)} file số liệu.\n"
                                           f"Nạp lại {len(con_lai)} file còn tồn tại vào bảng?"):
            self.muc.clear()
            self.them_cac_file(con_lai)
            for m in self.muc:
                for x in files:
                    if x.get("path") == m["path"]:
                        m["nhan"], m["mau"] = x.get("nhan", m["nhan"]), x.get("mau", m["mau"])
            self.lam_moi_bang()
        self.q.put(f"Đã nạp thông số từ {os.path.basename(p)}.\n")

    @staticmethod
    def so(bien, ten, kieu=float, duong=False):
        try:
            v = kieu(bien.get().strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"'{ten}' phải là số.")
        if duong and v <= 0:
            raise ValueError(f"'{ten}' phải lớn hơn 0.")
        return v

    # ====================== DỰNG LỆNH CHẠY ======================
    @staticmethod
    def lenh_con(ten_script, mode):
        if FROZEN:
            return [sys.executable, mode]
        return [python_exe(), "-u", os.path.join(THU_MUC, ten_script)]

    def chu_vach_args(self):
        kq = []
        for k, co, ten, kieu, duong in (
                ("co_chu_td", "--co-chu-td", "Cỡ chữ tiêu đề", int, True),
                ("co_chu_ct", "--co-chu-ct", "Cỡ chữ chú thích", int, True),
                ("vc_dai", "--vach-chinh-dai", "Vạch chính - dài", float, True),
                ("vc_day", "--vach-chinh-day", "Vạch chính - dày", float, True),
                ("vp_so", "--vach-phu-so", "Số vạch phụ", int, False),
                ("vp_dai", "--vach-phu-dai", "Vạch phụ - dài", float, True),
                ("vp_day", "--vach-phu-day", "Vạch phụ - dày", float, True)):
            bien = getattr(self, k)
            if bien.get().strip():
                v = self.so(bien, ten, kieu, duong=duong)
                if v < 0:
                    raise ValueError(f"'{ten}' không được âm.")
                kq += [co, str(v)]
        return kq

    def khoang_args(self):
        kq, gt = [], {}
        for k, ten in (("x_min", "Trục X - Từ"), ("x_max", "Trục X - Đến"), ("x_buoc", "Trục X - Bước"),
                       ("y_min", "Trục Y - Từ"), ("y_max", "Trục Y - Đến"), ("y_buoc", "Trục Y - Bước")):
            if getattr(self, k).get().strip():
                gt[k] = self.so(getattr(self, k), ten)
                kq += ["--" + k.replace("_", "-"), str(gt[k])]
        for t in "xy":
            if f"{t}_min" in gt and f"{t}_max" in gt and gt[f"{t}_min"] >= gt[f"{t}_max"]:
                raise ValueError(f"Trục {t.upper()}: 'Từ' phải nhỏ hơn 'Đến'.")
            if f"{t}_buoc" in gt and gt[f"{t}_buoc"] <= 0:
                raise ValueError(f"Trục {t.upper()}: 'Bước chia' phải lớn hơn 0.")
        return kq

    def lam_lenh(self, xem_truoc=False):
        if not self.muc:
            raise ValueError("Chưa chọn file số liệu nào.")
        loai = self.loai.get()
        ecsa = loai.startswith("ECSA")
        tafel = loai.startswith("Tafel")

        ph = self.so(self.ph, "pH")
        eref = self.so(self.eref, "Eref")
        nhan_i = self.so(self.nhan_i, "hệ số nhân I", duong=True)
        chia_i = self.so(self.chia_i, "hệ số chia I", duong=True)
        chung = ["--ph", str(ph), "--eref", str(eref), "--nhan-i", str(nhan_i), "--chia-i", str(chia_i)]
        if self.chu_ky.get().strip():
            chung += ["--chu-ky", str(self.so(self.chu_ky, "Chu kỳ CV", int, duong=True))]
        thu_muc = os.path.abspath(self.thu_muc_ra.get())

        if ecsa:
            if len(self.muc) < 2:
                raise ValueError("ECSA cần ít nhất 2 file CV.")
            cs = self.so(self.cs, "Cs", duong=True)
            chung += ["--ecsa", "--cs", str(cs)]
            if self.e_ecsa.get().strip():
                chung += ["--e-ecsa", str(self.so(self.e_ecsa, "E lấy dòng"))]
        elif tafel:
            tf_min = self.so(self.tafel_min, "Tafel min")
            tf_max = self.so(self.tafel_max, "Tafel max")
            chung += ["--loai", "TAFEL", "--tafel-min", str(tf_min), "--tafel-max", str(tf_max)]
        elif loai in ("LSV", "CV", "IT", "EIS"):
            chung += ["--loai", loai]

        if self.chong.get() and not ecsa:
            chung.append("--chong")

        xuat_bao_cao = self.xuat_excel.get() and not xem_truoc
        if xuat_bao_cao:
            mt = [x.strip() for x in self.i_muc_tieu.get().replace(";", ",").split(",") if x.strip()]
            try:
                for x in mt:
                    float(x.replace(",", "."))
            except ValueError:
                raise ValueError("'I mục tiêu' phải là các số cách nhau dấu phẩy, ví dụ: 10, 100.")
            e_cb = self.so(self.e_can_bang, "E cân bằng")

        files = [m["path"] for m in self.muc]
        nhan_mau = []
        for m in self.muc:
            nhan_mau += ["--nhan", m["nhan"], "--mau-file", m["mau"]]

        lenh = []
        da_bao_cao = False

        def them_bao_cao():
            nonlocal da_bao_cao
            if xuat_bao_cao and not da_bao_cao:
                da_bao_cao = True
                return ["--bao-cao", thu_muc, "--i-muc-tieu", ",".join(x.replace(",", ".") for x in mt), "--e-can-bang", str(e_cb)]
            return []

        if self.dung_origin.get() and not xem_truoc:
            c = self.lenh_con("ve_origin.py", "--worker-origin") + files + chung + nhan_mau
            c += ["--thu-muc-ra", thu_muc, "--co-chu", str(self.so(self.co_chu, "Cỡ chữ", int, duong=True)),
                  "--day-net", str(self.so(self.day_net, "Dày nét", duong=True)),
                  "--ti-le", str(self.so(self.ti_le, "Tỉ lệ", duong=True)),
                  "--day-khung", str(self.so(self.day_khung, "Dày khung", duong=True)),
                  "--le-max", str(self.so(self.le_max, "Đệm trục"))] + self.khoang_args() + self.chu_vach_args()
            c += them_bao_cao()
            lenh.append(("Vẽ bằng Origin 2024", c))
        if self.dung_csv.get() or xem_truoc:
            c = self.lenh_con("xu_ly_dien_hoa.py", "--worker-csv") + files + chung + nhan_mau
            if xem_truoc:
                c += ["--thu-muc-ra", THU_MUC_XEM_TRUOC]
            else:
                c += ["--thu-muc-ra", os.path.join(thu_muc, "csv_va_anh_nhanh")]
                if lenh:
                    c.append("--khong-canh-bao")      # Origin đã in cảnh báo rồi
                c += them_bao_cao()
            lenh.append(("Xem trước (Matplotlib)" if xem_truoc else "Xuất CSV & Ảnh nhanh", c))
        if not lenh:
            raise ValueError("Hãy tick ít nhất một đầu ra: 'Vẽ bằng Origin 2024' hoặc 'Xuất CSV & Ảnh Matplotlib'.")
        return lenh

    # ====================== CHẠY / DỪNG ======================
    def bam_chay(self, xem_truoc=False):
        if self.dang_chay:
            return
        try:
            lenh = self.lam_lenh(xem_truoc)
        except ValueError as e:
            messagebox.showwarning("Thông báo", str(e))
            return
        thu_muc_ra = os.path.abspath(self.thu_muc_ra.get())
        if lt:
            loi, luu_y = lt.kiem_tra_truoc(self.muc, self.dung_origin.get() and not xem_truoc,
                                           THU_MUC_XEM_TRUOC if xem_truoc else thu_muc_ra, self.loai.get())
            if loi:
                messagebox.showerror("Chưa thể chạy", "\n".join("• " + x for x in loi))
                return
            if luu_y and not messagebox.askyesno("Lưu ý trước khi chạy", "\n".join("• " + x for x in luu_y) + "\n\nVẫn tiếp tục?"):
                return
        self.luu_cai_dat()
        if xem_truoc:
            import shutil
            shutil.rmtree(THU_MUC_XEM_TRUOC, ignore_errors=True)
            os.makedirs(THU_MUC_XEM_TRUOC, exist_ok=True)
        self.dang_chay = True
        self.huy = False
        self.che_do = "xem_truoc" if xem_truoc else "chay"
        self.nut_chay.config(state="disabled", text="Đang xử lý...")
        self.nut_xem.config(state="disabled")
        self.nut_dung.config(state="normal")
        self.thanh.start(12)
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.duong_json_chay = None if xem_truoc else self.ghi_thong_so_chay(lenh, thu_muc_ra)
        threading.Thread(target=self.chay_nen, args=(lenh, self.che_do), daemon=True).start()

    def bam_dung(self):
        if not self.dang_chay or self.che_do not in ("chay", "xem_truoc"):
            return
        self.huy = True
        self.nut_dung.config(state="disabled")
        p = self.proc
        if p is not None and p.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, creationflags=CO_CONSOLE)
                else:
                    p.terminate()
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    def chay_nen(self, lenh, che_do):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        tot, toan_bo, so_canh_bao = True, [], 0
        if lt:
            lt.ghi_nhat_ky(DATA_DIR, f"BẮT ĐẦU ({che_do}) v{self.phien_ban}", lt.thong_tin_may() + "\n" +
                           "\n".join(" ".join(c[:2]) + " ..." for _, c in lenh))
        for ten, c in lenh:
            if self.huy:
                break
            self.q.put(f"=== {ten} ===\n")
            try:
                self.proc = subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                             encoding="utf-8", errors="replace", cwd=THU_MUC, env=env,
                                             creationflags=CO_CONSOLE)
                for dong in self.proc.stdout:
                    toan_bo.append(dong)
                    if dong.startswith("[CẢNH BÁO"):
                        so_canh_bao += 1
                    self.q.put(dong)
                self.proc.wait()
                if self.huy:
                    tot = False
                elif self.proc.returncode != 0:
                    tot = False
                    self.q.put(f"[LỖI] '{ten}' kết thúc với mã thoát {self.proc.returncode}\n")
                    toan_bo.append(f"mã thoát {self.proc.returncode}\n")
            except Exception as e:
                tot = False
                self.q.put(f"[LỖI] {e}\n")
                toan_bo.append(str(e))
            finally:
                self.proc = None
            self.q.put("\n")
        van_ban = "".join(toan_bo)
        if self.huy:
            ket = "dung"
            self.q.put(">>> ĐÃ DỪNG THEO YÊU CẦU\n")
        elif tot:
            ket = "thanh_cong"
            self.q.put(">>> HOÀN THÀNH" + (f"  ({so_canh_bao} cảnh báo - xem các dòng [CẢNH BÁO] ở trên)" if so_canh_bao else "") + "\n")
        else:
            ket = "loi"
            self.q.put(">>> CÓ LỖI XẢY RA\n")
            goi_y = lt.goi_y_sua(van_ban) if lt else []
            if goi_y:
                self.q.put("\nGỢI Ý XỬ LÝ:\n" + "\n".join(goi_y) + "\n")
            self.q.put("\n(Chi tiết kỹ thuật đã lưu trong nhật ký - bấm 'Mở nhật ký' rồi gửi cho người hỗ trợ nếu cần.)\n")
        if lt:
            lt.ghi_nhat_ky(DATA_DIR, f"KẾT THÚC ({che_do}): {ket}", van_ban if ket == "loi" else f"{so_canh_bao} cảnh báo")
        self.cap_nhat_json_chay(ket)
        self.q.put(("chay_xong", che_do, ket))

    # ---------- lưu thông số mỗi lần chạy (để tái lập kết quả) ----------
    def ghi_thong_so_chay(self, lenh, thu_muc_ra):
        try:
            thu = os.path.join(thu_muc_ra, "_lich_su_chay")
            os.makedirs(thu, exist_ok=True)
            files = []
            for m in self.muc:
                info = {"path": m["path"], "nhan": m["nhan"], "mau": m["mau"], "loai_nhan_dang": m.get("loai_nhan", "?")}
                try:
                    st = os.stat(m["path"])
                    info["kich_thuoc"] = st.st_size
                    info["sua_doi"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
                    h = hashlib.sha256()
                    with open(m["path"], "rb") as f:
                        for kh in iter(lambda: f.read(1 << 20), b""):
                            h.update(kh)
                    info["sha256"] = h.hexdigest()
                except OSError:
                    pass
                files.append(info)
            du_lieu = {"phan_mem": "Echem Studio", "phien_ban": self.phien_ban,
                       "thoi_gian": datetime.datetime.now().isoformat(timespec="seconds"),
                       "may": lt.thong_tin_may() if lt else "", "ket_qua": "dang_chay",
                       "cai_dat": self.du_lieu_cau_hinh(), "files": files,
                       "lenh": [{"ten": t, "argv": c} for t, c in lenh]}
            duong = os.path.join(thu, f"thong_so_chay_{datetime.datetime.now():%Y%m%d_%H%M%S}.json")
            with open(duong, "w", encoding="utf-8") as f:
                json.dump(du_lieu, f, ensure_ascii=False, indent=1)
            return duong
        except OSError:
            return None

    def cap_nhat_json_chay(self, ket):
        p = self.duong_json_chay
        if not p:
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            d["ket_qua"] = ket
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
        except (OSError, ValueError):
            pass

    # ====================== XEM TRƯỚC ======================
    def mo_xem_truoc(self):
        anh = []
        for dp, _, fs in os.walk(THU_MUC_XEM_TRUOC):
            anh += [os.path.join(dp, f) for f in fs if f.lower().endswith(".png")]
        anh.sort()
        if not anh:
            messagebox.showinfo("Xem trước", "Không tạo được hình nào. Xem ô báo cáo để biết lý do.")
            return
        w = tk.Toplevel(self.root)
        w.title("Xem trước hình (Matplotlib) - bản nháp, hình cuối cùng do Origin vẽ")
        w.transient(self.root)
        lb = ttk.Label(w, anchor="center")
        lb.pack(padx=8, pady=8)
        tt = ttk.Label(w, text="")
        tt.pack()
        chi = {"i": 0}
        anh_goc = {}

        def hien():
            p = anh[chi["i"]]
            try:
                img = tk.PhotoImage(file=p)
                he_so = max(1, -(-max(img.width() // 680, img.height() // 520, 0) // 1))
                if img.width() > 680 or img.height() > 520:
                    he_so = max(-(-img.width() // 680), -(-img.height() // 520))
                    img = img.subsample(he_so, he_so)
                anh_goc["img"] = img
                lb.config(image=img)
            except Exception as e:
                lb.config(text=f"Không hiển thị được hình: {e}", image="")
            tt.config(text=f"{chi['i'] + 1}/{len(anh)}  -  {os.path.basename(p)}")

        def doi(h):
            chi["i"] = (chi["i"] + h) % len(anh)
            hien()
        fb = ttk.Frame(w)
        fb.pack(pady=6)
        ttk.Button(fb, text="◀ Trước", command=lambda: doi(-1)).pack(side="left", padx=4)
        ttk.Button(fb, text="Sau ▶", command=lambda: doi(1)).pack(side="left", padx=4)
        ttk.Button(fb, text="Mở thư mục ảnh", command=lambda: self.mo_duong_dan(THU_MUC_XEM_TRUOC)).pack(side="left", padx=4)
        ttk.Button(fb, text="Đóng", command=w.destroy).pack(side="left", padx=4)
        hien()
        self.cua_so_xem_truoc = w

    # ====================== CẬP NHẬT TỰ ĐỘNG ======================
    def kiem_tra_cap_nhat(self, im_lang=False):
        if cn is None:
            if not im_lang:
                messagebox.showwarning("Cập nhật", "Không tìm thấy tu_dong_cap_nhat.py")
            return
        if self.dang_chay:
            return

        def nen():
            co, tt, loi = cn.kiem_tra_cap_nhat(thu_muc=THU_MUC)
            self.q.put(("kiem_tra", im_lang, co, tt, loi))
        threading.Thread(target=nen, daemon=True).start()

    def bat_dau_cap_nhat(self, tt):
        self.dang_chay = True
        self.che_do = "cap_nhat"
        self.nut_chay.config(state="disabled", text="Đang cập nhật...")

        def nen():
            ok, msg = cn.cap_nhat(tt, thu_muc=THU_MUC, log=lambda d: self.q.put(d + "\n"))
            self.q.put(("xong_cap_nhat", ok, msg))
        threading.Thread(target=nen, daemon=True).start()

    def hop_thoai_cap_nhat(self, tt, da_bo_qua=False):
        """Trả về 'ngay' | 'sau' | 'bo_qua'."""
        kq = {"v": "sau"}
        w = tk.Toplevel(self.root)
        w.title("Có bản cập nhật mới")
        w.transient(self.root)
        w.grab_set()
        ttk.Label(w, text=f"Phiên bản mới: {tt.get('phien_ban_hien_tai')}   (đang dùng: {self.phien_ban})",
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        if da_bo_qua:
            ttk.Label(w, text="(Bạn đã chọn bỏ qua phiên bản này trước đó)", foreground="#666").pack(anchor="w", padx=12)
        ttk.Label(w, text="Có gì mới:").pack(anchor="w", padx=12, pady=(6, 0))
        t = tk.Text(w, width=62, height=7, wrap="word")
        t.insert("1.0", tt.get("ghi_chu", "(không có ghi chú)"))
        t.config(state="disabled")
        t.pack(padx=12, pady=4)
        ttk.Label(w, text="Cập nhật chỉ thay mã nguồn của chương trình; thiết lập và dữ liệu của bạn không bị ảnh hưởng.",
                  foreground="#666", wraplength=440).pack(anchor="w", padx=12)

        def chon(v):
            kq["v"] = v
            w.destroy()
        fb = ttk.Frame(w)
        fb.pack(pady=10)
        ttk.Button(fb, text="Cập nhật ngay", command=lambda: chon("ngay")).pack(side="left", padx=4)
        ttk.Button(fb, text="Để sau", command=lambda: chon("sau")).pack(side="left", padx=4)
        ttk.Button(fb, text="Bỏ qua phiên bản này", command=lambda: chon("bo_qua")).pack(side="left", padx=4)
        w.protocol("WM_DELETE_WINDOW", lambda: chon("sau"))
        self.root.wait_window(w)
        return kq["v"]

    def xu_ly_ui(self, m):
        if m[0] == "kiem_tra":
            _, im_lang, co, tt, loi = m
            if loi:
                if not im_lang:
                    messagebox.showwarning("Cập nhật", loi)
            elif co:
                try:
                    ver = int(tt.get("phien_ban_hien_tai"))
                except (TypeError, ValueError):
                    ver = 0
                da_bo = ver == self.cd_phu.get("bo_qua_pb", 0)
                if im_lang and da_bo:
                    return
                kq = self.hop_thoai_cap_nhat(tt, da_bo)
                if kq == "ngay":
                    self.bat_dau_cap_nhat(tt)
                elif kq == "bo_qua":
                    self.cd_phu["bo_qua_pb"] = ver
                    self.luu_cai_dat()
                    self.q.put(f"Đã bỏ qua phiên bản {ver}. Bấm 'Kiểm tra cập nhật' nếu muốn cập nhật sau.\n")
            elif not im_lang:
                messagebox.showinfo("Cập nhật", "Bạn đang dùng phiên bản mới nhất.")
        elif m[0] == "hd_xong":
            self.dang_hd = False
            self.nut_hd.config(state="normal")
        elif m[0] == "chay_xong":
            _, che_do, ket = m
            self.dang_chay = False
            self.che_do = None
            self.proc = None
            self.thanh.stop()
            self.nut_chay.config(state="normal", text="▶  CHẠY XỬ LÝ & VẼ")
            self.nut_xem.config(state="normal")
            self.nut_dung.config(state="disabled")
            if che_do == "xem_truoc" and ket == "thanh_cong":
                self.mo_xem_truoc()
        elif m[0] == "xong_cap_nhat":
            _, ok, msg = m
            self.dang_chay = False
            self.che_do = None
            self.nut_chay.config(state="normal", text="▶  CHẠY XỬ LÝ & VẼ")
            if ok:
                messagebox.showinfo("Cập nhật", "Cập nhật thành công!\nPhần mềm sẽ đóng lại, hãy mở lại để dùng bản mới.")
                self.root.destroy()
            else:
                messagebox.showerror("Cập nhật", msg)

    def them_log(self, van_ban):
        self.log.config(state="normal")
        tag = ()
        if van_ban.startswith("[CẢNH BÁO") or van_ban.startswith("[LƯU Ý") or van_ban.startswith("[GỢI Ý"):
            tag = ("canh_bao",)
        elif van_ban.startswith("[LỖI") or van_ban.startswith(">>> CÓ LỖI"):
            tag = ("loi",)
        elif van_ban.startswith(">>> HOÀN THÀNH"):
            tag = ("tot",)
        self.log.insert("end", van_ban, tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def doc_hang_doi(self):
        try:
            while True:
                m = self.q.get_nowait()
                if isinstance(m, tuple):
                    self.xu_ly_ui(m)
                else:
                    self.them_log(m)
        except queue.Empty:
            pass
        self.root.after(100, self.doc_hang_doi)

    # ====================== HƯỚNG DẪN / MẪU / GIỚI THIỆU ======================
    def mo_huong_dan(self):
        van_ban = "Chưa tìm thấy file HUONG_DAN.md. Hãy bấm 'Kiểm tra cập nhật' để tải về."
        try:
            with open(os.path.join(THU_MUC, "HUONG_DAN.md"), "r", encoding="utf-8") as f:
                van_ban = f.read()
        except OSError:
            pass
        w = tk.Toplevel(self.root)
        w.title("Hướng dẫn sử dụng Echem Studio")
        w.geometry("760x600")
        t = scrolledtext.ScrolledText(w, wrap="word", font=("TkDefaultFont", 10), padx=10, pady=8)
        t.pack(fill="both", expand=True)
        t.tag_configure("h1", font=("TkDefaultFont", 15, "bold"), spacing1=8, spacing3=6, foreground="#1f3864")
        t.tag_configure("h2", font=("TkDefaultFont", 12, "bold"), spacing1=10, spacing3=4, foreground="#1f3864")
        t.tag_configure("h3", font=("TkDefaultFont", 10, "bold"), spacing1=6)
        t.tag_configure("code", font=("Consolas", 9), background="#f0f0f0")
        t.tag_configure("li", lmargin1=18, lmargin2=32)
        code = False
        for dong in van_ban.splitlines():
            if dong.strip().startswith("```"):
                code = not code
                continue
            if code:
                t.insert("end", dong + "\n", "code")
            elif dong.startswith("### "):
                t.insert("end", dong[4:] + "\n", "h3")
            elif dong.startswith("## "):
                t.insert("end", dong[3:] + "\n", "h2")
            elif dong.startswith("# "):
                t.insert("end", dong[2:] + "\n", "h1")
            elif dong.lstrip().startswith(("- ", "* ")):
                t.insert("end", "•  " + dong.lstrip()[2:].replace("**", "") + "\n", "li")
            else:
                t.insert("end", dong.replace("**", "").replace("`", "") + "\n")
        t.config(state="disabled")

    def mo_du_lieu_mau(self):
        if md is None:
            messagebox.showwarning("Dữ liệu mẫu", "Không tìm thấy mau_du_lieu.py")
            return
        w = tk.Toplevel(self.root)
        w.title("Dữ liệu mẫu")
        w.transient(self.root)
        w.grab_set()
        ttk.Label(w, text="Chọn bộ dữ liệu mẫu để thử ngay (số liệu GIẢ LẬP minh họa, không phải kết quả thí nghiệm thật).",
                  wraplength=420).pack(padx=12, pady=(12, 6))

        def chon(ten):
            w.destroy()
            self.nap_du_lieu_mau(ten)
        for ten, mo_ta in md.BO_MAU.items():
            ttk.Button(w, text=mo_ta, command=lambda t=ten: chon(t)).pack(fill="x", padx=12, pady=3)
        ttk.Button(w, text="Mở thư mục chứa dữ liệu mẫu", command=lambda: (os.makedirs(THU_MUC_MAU, exist_ok=True), self.mo_duong_dan(THU_MUC_MAU))).pack(
            fill="x", padx=12, pady=(10, 3))
        ttk.Button(w, text="Đóng", command=w.destroy).pack(pady=(4, 10))

    def nap_du_lieu_mau(self, ten):
        try:
            ds, loai = md.tao_bo(ten, THU_MUC_MAU)
        except Exception as e:
            messagebox.showerror("Dữ liệu mẫu", f"Không tạo được dữ liệu mẫu: {e}")
            return
        self.muc.clear()
        self.them_cac_file([x["path"] for x in ds])
        for m, x in zip(self.muc, ds):
            m["nhan"] = x["nhan"]
        self.loai.set(loai)
        if ten == "ecsa":
            self.e_ecsa.set("")
        self.lam_moi_bang()
        self.cap_nhat_trang_thai()
        self.q.put(f"Đã nạp bộ dữ liệu mẫu '{md.BO_MAU[ten]}' ({len(ds)} file) vào bảng. Bấm 'Xem trước hình' hoặc 'CHẠY' để thử.\n"
                   f"(File nằm ở: {THU_MUC_MAU})\n")

    def mo_gioi_thieu(self):
        w = tk.Toplevel(self.root)
        w.title("Giới thiệu")
        w.transient(self.root)
        w.resizable(False, False)
        try:
            self.anh_logo = tk.PhotoImage(file=os.path.join(THU_MUC, "logo_256.png"))
            ttk.Label(w, image=self.anh_logo).pack(pady=(14, 4))
        except Exception:
            pass
        ttk.Label(w, text="Echem Studio", font=("TkDefaultFont", 14, "bold")).pack()
        ttk.Label(w, text="Xử lý & vẽ số liệu điện hóa: LSV · CV · IT · EIS · ECSA · Tafel").pack()
        ttk.Label(w, text=f"Phiên bản mã nguồn: {self.phien_ban}").pack(pady=(6, 0))
        kho = f"{cn.GITHUB_USER}/{cn.GITHUB_REPO}" if cn else "?"
        ttk.Label(w, text=f"Kho mã nguồn: github.com/{kho}", foreground="#1a5fd8").pack()
        ttk.Label(w, text=f"Thư mục dữ liệu: {DATA_DIR}", foreground="#666", wraplength=420).pack(pady=(6, 0), padx=12)
        ttk.Label(w, text=lt.thong_tin_may() if lt else "", foreground="#666", wraplength=420).pack(padx=12)
        fb = ttk.Frame(w)
        fb.pack(pady=10)
        ttk.Button(fb, text="Mở thư mục dữ liệu", command=lambda: self.mo_duong_dan(DATA_DIR)).pack(side="left", padx=4)
        ttk.Button(fb, text="Mở nhật ký", command=self.mo_nhat_ky).pack(side="left", padx=4)
        ttk.Button(fb, text="Đóng", command=w.destroy).pack(side="left", padx=4)

    # ====================== LỖI KHÔNG MONG MUỐN ======================
    def loi_khong_mong_doi(self, exc, val, tb):
        import traceback
        chi_tiet = "".join(traceback.format_exception(exc, val, tb))
        if lt:
            lt.ghi_nhat_ky(DATA_DIR, "LỖI GIAO DIỆN", chi_tiet)
        try:
            messagebox.showerror("Đã xảy ra lỗi không mong muốn",
                                 f"{val}\n\nChi tiết đã được lưu vào nhật ký (nút 'Mở nhật ký').\n"
                                 "Bạn có thể tiếp tục dùng chương trình; nếu lỗi lặp lại hãy gửi nhật ký cho người hỗ trợ.")
        except Exception:
            pass


def main():
    # Che do worker: exe tu goi lai chinh no de xu ly / ve
    if len(sys.argv) > 1 and sys.argv[1] in ("--worker-origin", "--worker-csv"):
        mode = sys.argv.pop(1)
        # exe PyInstaller bo qua PYTHONIOENCODING -> ep stdout/stderr dung UTF-8 de in duoc tieng Viet
        for luong in (sys.stdout, sys.stderr):
            try:
                luong.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if mode == "--worker-origin":
            import ve_origin as m
        else:
            import xu_ly_dien_hoa as m
        m.main()
        return

    # Che do giao dien: an cua so console den
    if FROZEN and os.name == "nt":
        try:
            import ctypes
            h = ctypes.windll.kernel32.GetConsoleWindow()
            if h:
                ctypes.windll.user32.ShowWindow(h, 0)
            ctypes.windll.kernel32.FreeConsole()      # dong han console (ca khi dung Windows Terminal)
            # sau FreeConsole, print() co the loi -> chuyen sang devnull
            sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
    # Chu sac net tren man hinh Windows co scale 125-150%
    if os.name == "nt":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    dnd = None
    try:                                   # kéo-thả file: tùy chọn, cần  pip install tkinterdnd2
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        dnd = (TkinterDnD, DND_FILES)
    except Exception:
        root = tk.Tk()
    try:
        root.iconbitmap(os.path.join(THU_MUC, "logo.ico"))
    except Exception:
        pass
    App(root, dnd)
    root.mainloop()


if __name__ == "__main__":
    main()
