# -*- coding: utf-8 -*-
"""Cửa sổ "Siêu tụ lai / Pin": nạp file GCD thô (nhiều mẫu) → phân tích → 5 đồ thị, mỗi đồ thị một tab với thiết lập riêng
(dữ liệu, trục, kiểu, tạp chí) → xuất Excel/hình hoặc vẽ Origin. Thiết lập lưu/mở được (JSON) và tự nhớ lần cuối.
Lõi tính toán: gcd_pin.py; vẽ Origin: ve_gcd_origin.py (tiến trình con, giống XPS/XRD)."""
import json
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import gcd_pin as gp
import dien_cuc_so_sanh as dc

KIEU_CELL = {"3 điện cực / 1 điện cực: C/m (như file Excel)": "3dc", "2 điện cực: Csp cả cell = C/m (m = tổng KL)": "2dc_cell",
             "2 điện cực đối xứng: Csp điện cực = 4C/m": "2dc"}
CHINH = {"Tự động (tụ → F/g, pin/lai → mAh/g)": "auto", "Điện dung riêng (F/g)": "dien_dung", "Dung lượng riêng (mAh/g)": "dung_luong"}
DAI_LUONG = {"Theo thiết lập chung": "theo_chung", "Điện dung riêng (F/g)": "dien_dung", "Dung lượng riêng (mAh/g)": "dung_luong"}
DAI_LUONG_CK = dict(DAI_LUONG, **{"Thời gian xả (s), như file Excel": "thoi_gian_xa"})
DAI_LUONG_CSP = {"Điện dung riêng Csp (F/g)": "dien_dung", "Dung lượng riêng (mAh/g)": "dung_luong", "Theo thiết lập chung": "theo_chung"}
KIEU_VE_CSP = {"Cột (như hình mẫu)": "cot", "Đường + điểm": "duong"}
CACH_C = {"Tích phân điện tích C = Q/ΔV = I·Δt/ΔV": "tich_phan", "Độ dốc C = I/|dV/dt|": "do_doc"}
CACH_E = {"E = ½C·ΔV² (như file Excel)": "cv2_dv", "E = ½C(V² − V₀²) (tụ lý tưởng)": "cv2", "E = ∫V·I dt (mọi đường cong)": "tich_phan"}
CACH_E_RAG = dict({"Theo thiết lập chung": None}, **CACH_E)
CACH_DV = {"ΔV = V đỉnh nạp − V cuối xả (gồm IR drop, như file Excel)": "gom_ir", "ΔV = V_ext − V cuối xả (bỏ IR drop, chuẩn)": "tru_ir"}
BO_CT = {"Kiểu file Excel của bạn": "excel", "Chuẩn (bỏ IR drop, E tích phân)": "chuan"}
TRUC_X = {"Thời gian (s)": "tg", "Dung lượng riêng": "q"}
CHIEU = {"Điện thế TĂNG khi nạp": True, "Điện thế GIẢM khi nạp": False}
CHUAN = {"Khối lượng (mg)": "khoi_luong", "Diện tích (cm²)": "dien_tich"}
VI_TRI = {"Tự động": "best", "Trên phải": "upper right", "Trên trái": "upper left", "Dưới phải": "lower right", "Dưới trái": "lower left",
          "Giữa phải": "center right", "Giữa trái": "center left"}
TAP_CHI = {"(không)": "", "ACS": "ACS", "RSC": "RSC", "Elsevier": "Elsevier", "Nature": "Nature"}
COT = {"Cột đơn": 1, "Cột 1.5": 15, "Cột đôi": 2}
DINH_DANG = ["png", "pdf", "tiff", "svg"]

# (khóa, nhãn, loại: cb|en|so|int|ck, lựa chọn, mặc định)
TRUONG_RIENG = {
    "gcd": [("x", "Trục x", "cb", TRUC_X, "Thời gian (s)"),
            ("chu_ky_ve", "Chu kỳ vẽ (vd 1,2,100; trống = mỗi mức dòng một chu kỳ)", "en", None, "")],
    "gcd_nhieu": [("mau_ten", "Chỉ vẽ mẫu có tên chứa (trống = tất cả)", "en", None, ""),
                  ("nhom_j", "Chỉ một mức dòng j (trống = cả file)", "en", None, ""),
                  ("phong_dai", "Hiện hai ô phóng đại (chu kỳ đầu / cuối)", "ck", None, True),
                  ("so_dau", "Số chu kỳ đầu trong ô phóng đại", "int", None, "3"), ("so_cuoi", "Số chu kỳ cuối trong ô phóng đại", "int", None, "3"),
                  ("nhan_dau", "Nhãn ô đầu", "en", None, "Initial cycles"), ("nhan_cuoi", "Nhãn ô cuối", "en", None, "Final cycles"),
                  ("nhan_tren", "Chữ góc trên trái (vd NiCr2O4 // AC)", "en", None, ""),
                  ("nhan_ct", "Chú thích đường (trống = j và số chu kỳ)", "en", None, "")],
    "csp_dong": [("kieu_ve", "Kiểu đồ thị", "cb", KIEU_VE_CSP, "Cột (như hình mẫu)"),
                 ("dai_luong", "Đại lượng (Csp = I·Δt / (m·ΔV))", "cb", DAI_LUONG_CSP, "Điện dung riêng Csp (F/g)")],
    "ragone": [("cach_e", "Cách tính năng lượng", "cb", CACH_E_RAG, "Theo thiết lập chung")],
    "retention": [("dai_luong", "Đại lượng", "cb", DAI_LUONG_CK, "Theo thiết lập chung"),
                  ("nhom_j", "Mức dòng j (trống = nhóm nhiều chu kỳ nhất)", "en", None, ""),
                  ("chu_ky_goc", "Chu kỳ gốc (100 %)", "int", None, ""),
                  ("hien_ce", "Hiện hiệu suất Coulomb (trục phải)", "ck", None, True)],
    "csp_chu_ky": [("dai_luong", "Đại lượng", "cb", DAI_LUONG_CK, "Theo thiết lập chung"),
                   ("nhom_j", "Mức dòng j (trống = nhóm nhiều chu kỳ nhất)", "en", None, ""),
                   ("hien_ce", "Hiện hiệu suất Coulomb (trục phải)", "ck", None, True)],
}
TRUC = [("tieu_de_x", "Tiêu đề trục x", "en", None, ""), ("tieu_de_y", "Tiêu đề trục y", "en", None, "")]
TRUC_Y2 = [("tieu_de_y2", "Tiêu đề trục y phải", "en", None, "")]
KHOANG = [("x_min", "x nhỏ nhất", "so", None, ""), ("x_max", "x lớn nhất", "so", None, ""),
          ("y_min", "y nhỏ nhất", "so", None, ""), ("y_max", "y lớn nhất", "so", None, "")]
KHOANG_Y2 = [("y2_min", "y phải nhỏ nhất", "so", None, ""), ("y2_max", "y phải lớn nhất", "so", None, "")]
LOG = [("log_x", "Trục x log", "ck", None, False), ("log_y", "Trục y log", "ck", None, False)]
KIEU = [("co_nhan", "Cỡ chữ nhãn trục (pt)", "so", None, ""), ("co_tick", "Cỡ số trên trục (pt)", "so", None, ""),
        ("co_ct", "Cỡ chữ chú thích (pt)", "so", None, ""), ("lw", "Độ dày nét (pt)", "so", None, ""),
        ("co_diem", "Cỡ điểm (pt)", "so", None, ""), ("chu_thich", "Hiện chú thích", "ck", None, True),
        ("vi_tri", "Vị trí chú thích", "cb", VI_TRI, "Tự động"), ("luoi", "Hiện lưới", "ck", None, False)]
XUAT = [("tap_chi", "Mẫu tạp chí (khi xuất hình)", "cb", TAP_CHI, "(không)"), ("cot", "Bề rộng", "cb", COT, "Cột đơn"),
        ("dpi", "dpi (trống = theo tạp chí/300)", "int", None, "")]


def _truong_cua(ma):
    t = list(TRUONG_RIENG[ma]) + TRUC + (TRUC_Y2 if ma in gp.HAI_TRUC else []) + KHOANG + (KHOANG_Y2 if ma in gp.HAI_TRUC else [])
    t += [("log_x", "Trục x log", "ck", None, ma == "ragone"), ("log_y", "Trục y log", "ck", None, ma == "ragone")] + KIEU + XUAT
    return t


SO_TAB = "②③④⑤⑥⑦"
# nhãn gọn cho tab (đưa chuột vào tab để xem tên đầy đủ)
KY_HIEU_TAB = {"gcd": "V–t", "gcd_nhieu": "V–t ×n", "csp_dong": "C–j", "ragone": "E–P", "retention": "% CE", "csp_chu_ky": "C–n"}


class CuaSoGcd:
    def __init__(self, root, lenh_origin=None, ds_file=None, tep_nho=None):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.root, self.lenh_origin, self.ds_file = root, lenh_origin, ds_file
        self.tep_nho = tep_nho if tep_nho is not None else os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DienHoaOrigin", "gcd_thiet_lap.json")
        self.hang = []
        self.kq = None
        self.json_origin = None
        w = self.w = tk.Toplevel(root)
        w.title("Siêu tụ lai / Pin: GCD · GCD nhiều chu kỳ · Csp · Ragone · Retention · CE")
        rong = min(1320, max(900, w.winfo_screenwidth() - 80))
        cao = min(900, max(620, w.winfo_screenheight() - 100))
        w.geometry(f"{rong}x{cao}+30+20")
        w.minsize(900, 600)
        self.v_tt = tk.StringVar(value="Thêm file GCD thô, nhập khối lượng rồi bấm Phân tích. Mỗi đồ thị có tab riêng với thiết lập riêng.")
        ttk.Label(w, textvariable=self.v_tt, foreground="#0a4d8c", wraplength=rong - 30, justify="left").pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        self.nb = ttk.Notebook(w)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.dung_tab_chung()
        self.tab = {}
        for k, ma in enumerate(gp.TEN_DO_THI, 2):
            self.dung_tab_do_thi(ma, k)
        self._tip = None
        self.nb.bind("<Motion>", self._tip_tab)
        self.nb.bind("<Leave>", lambda e: self._tat_tip())
        self.tu_nap()
        w.protocol("WM_DELETE_WINDOW", self.dong)
        self.doi_chuan()

    def _ten_tab(self, k):
        return "① Dữ liệu & thiết lập chung" if k == 0 else f"{SO_TAB[k - 1]} {list(gp.TEN_DO_THI.values())[k - 1]}"

    def _tip_tab(self, e):
        try:
            k = self.nb.index(f"@{e.x},{e.y}")
        except tk.TclError:
            self._tat_tip()
            return
        if self._tip is not None and getattr(self, "_tip_k", None) == k:
            return
        self._tat_tip()
        self._tip_k = k
        self._tip = tk.Toplevel(self.w)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{e.x_root + 10}+{e.y_root + 18}")
        tk.Label(self._tip, text=self._ten_tab(k), background="#ffffe0", relief="solid", borderwidth=1, padx=4, pady=1).pack()

    def _tat_tip(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
        self._tip = None

    def ap_kl_tat_ca(self):
        v = self.v_kl.get().strip().replace(",", ".")
        try:
            if float(v) <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Siêu tụ/Pin", "Khối lượng phải là số dương (mg).", parent=self.w)
            return
        for h in self.hang:
            h["v_gt"].set(v)
        self.v_tt.set(f"Đã đặt khối lượng {v} mg cho {len(self.hang)} mẫu (sửa riêng từng mẫu ở ô trong danh sách).")

    # ====================== TAB CHUNG ======================
    def dung_tab_chung(self):
        t = ttk.Frame(self.nb)
        self.nb.add(t, text="① ⚙")
        f1 = ttk.Frame(t)
        f1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(f1, text="Thêm file...", command=self.them_file).pack(side="left")
        ttk.Button(f1, text="Lấy từ danh sách file của app", command=self.lay_tu_app).pack(side="left", padx=4)
        ttk.Label(f1, text="Khối lượng (mg):").pack(side="left", padx=(14, 2))
        self.v_kl = tk.StringVar()
        o_kl = ttk.Entry(f1, textvariable=self.v_kl, width=8)
        o_kl.pack(side="left")
        o_kl.bind("<Return>", lambda e: self.ap_kl_tat_ca())
        ttk.Button(f1, text="Áp cho mọi mẫu", command=self.ap_kl_tat_ca).pack(side="left", padx=4)
        ttk.Label(f1, text="(file mới thêm lấy số này nếu header/tên file không có khối lượng)", foreground="#555").pack(side="left", padx=4)
        self.fr = ttk.LabelFrame(t, text=" Mẫu ")
        self.fr.pack(fill="x", padx=6, pady=2)

        self.cv = {}                                   # biến thiết lập chung
        c = ttk.Frame(t)
        c.pack(fill="x", padx=6, pady=2)
        g1 = ttk.LabelFrame(c, text=" Tế bào & chuẩn hóa ")
        g1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        g2 = ttk.LabelFrame(c, text=" Cách tính ")
        g2.grid(row=0, column=1, sticky="nsew", padx=4)
        g3 = ttk.LabelFrame(c, text=" Nhận dạng chu kỳ & ngưỡng ")
        g3.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        g4 = ttk.LabelFrame(c, text=" Điện cực so sánh → vẽ điện thế theo RHE (chỉ đổi trục điện thế, không đổi C, E) ")
        g4.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        c.columnconfigure((0, 1, 2), weight=1)

        def cb(cha, r, nhan, khoa, ds, mac, rong=30, lenh=None):
            ttk.Label(cha, text=nhan).grid(row=r, column=0, sticky="e", padx=(6, 2), pady=2)
            self.cv[khoa] = tk.StringVar(value=mac)
            x = ttk.Combobox(cha, textvariable=self.cv[khoa], values=list(ds), width=rong, state="readonly")
            x.grid(row=r, column=1, sticky="w", padx=(0, 6), pady=2)
            if lenh:
                x.bind("<<ComboboxSelected>>", lambda e: lenh())

        def en(cha, r, nhan, khoa, mac, rong=8):
            ttk.Label(cha, text=nhan).grid(row=r, column=0, sticky="e", padx=(6, 2), pady=2)
            self.cv[khoa] = tk.StringVar(value=mac)
            ttk.Entry(cha, textvariable=self.cv[khoa], width=rong).grid(row=r, column=1, sticky="w", padx=(0, 6), pady=2)
        cb(g1, 0, "Loại tế bào:", "cell", KIEU_CELL, next(iter(KIEU_CELL)), 34)
        cb(g1, 1, "Chuẩn hóa theo:", "chuan", CHUAN, next(iter(CHUAN)), 18, self.doi_chuan)
        cb(g1, 2, "Chiều nạp:", "chieu", CHIEU, next(iter(CHIEU)), 24)
        cb(g1, 3, "Đại lượng chính:", "chinh", CHINH, next(iter(CHINH)), 34)
        cb(g2, 0, "Bộ công thức:", "bo_ct", BO_CT, next(iter(BO_CT)), 30, self.chon_bo_ct)
        cb(g2, 1, "ΔV:", "dv", CACH_DV, next(iter(CACH_DV)), 44)
        cb(g2, 2, "Cách tính C:", "cach_c", CACH_C, next(iter(CACH_C)), 44)
        cb(g2, 3, "Cách tính E:", "cach_e", CACH_E, next(iter(CACH_E)), 44)
        en(g2, 4, "Cửa sổ độ dốc: tới V_cuối + p·ΔV, p =", "p", "0.5", 5)
        self.bo_dau = tk.BooleanVar(value=True)
        ttk.Checkbutton(g2, text="Trung vị mỗi mức dòng: bỏ chu kỳ đầu (nếu ≥ 3 chu kỳ)", variable=self.bo_dau).grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=2)
        self.cv["quy_rhe"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(g4, text="Vẽ điện thế theo RHE", variable=self.cv["quy_rhe"], command=self.ve_tat_ca_tab).grid(row=0, column=0, sticky="w", padx=6, pady=2)
        self.cv["dien_cuc"] = tk.StringVar(value=dc.TEN[0])
        ttk.Label(g4, text="Điện cực so sánh:").grid(row=0, column=1, sticky="e", padx=(10, 2))
        x = ttk.Combobox(g4, textvariable=self.cv["dien_cuc"], values=dc.TEN, width=34, state="readonly")
        x.grid(row=0, column=2, sticky="w")
        x.bind("<<ComboboxSelected>>", lambda e: self.chon_dien_cuc())
        for col, (nhan, khoa, mac, rong) in enumerate((("Eref (V vs SHE):", "e_ref", "0.098", 7), ("pH:", "ph", "13.8", 6), ("Hệ số Nernst (V/pH):", "nernst", "0.059", 7)), 3):
            ttk.Label(g4, text=nhan).grid(row=0, column=col * 2 - 3, sticky="e", padx=(10, 2))
            self.cv[khoa] = tk.StringVar(value=mac)
            ttk.Entry(g4, textvariable=self.cv[khoa], width=rong).grid(row=0, column=col * 2 - 2, sticky="w")
        ttk.Label(g4, text="E(RHE) = E đo + hệ số × pH + Eref. Hệ số 0.059 khớp file Excel của bạn; 0.0592 là giá trị chính xác ở 25 °C. Hai điện cực (cell): không tick.",
                  foreground="#666").grid(row=1, column=0, columnspan=8, sticky="w", padx=6, pady=(0, 2))
        en(g3, 0, "Dòng không đổi (mA) nếu file không có cột dòng:", "dong", "", 7)
        en(g3, 1, "Ngưỡng R² dạng tụ (≥):", "n_tu", "0.985", 6)
        en(g3, 2, "Ngưỡng R² dạng pin (<):", "n_pin", "0.93", 6)

        f3 = ttk.Frame(t)
        f3.pack(fill="x", padx=6, pady=4)
        ttk.Button(f3, text="▶ Phân tích", command=self.phan_tich).pack(side="left")
        ttk.Button(f3, text="Xuất Excel + CSV + hình (cả 6)...", command=self.xuat_tat_ca).pack(side="left", padx=(14, 2))
        ttk.Button(f3, text="Vẽ cả 6 ra Origin...", command=lambda: self.ve_origin(None)).pack(side="left", padx=2)
        ttk.Button(f3, text="💾 Lưu thiết lập...", command=self.luu_thiet_lap).pack(side="left", padx=(14, 2))
        ttk.Button(f3, text="📂 Mở thiết lập...", command=self.mo_thiet_lap).pack(side="left", padx=2)
        pw = ttk.PanedWindow(t, orient="vertical")
        pw.pack(fill="both", expand=True, padx=6, pady=2)
        nb2 = ttk.Notebook(pw)
        pw.add(nb2, weight=1)
        self.txt = tk.Text(nb2, font=("Consolas", 10), wrap="none", height=12)
        self.txt_ct = tk.Text(nb2, font=("Consolas", 10), wrap="word", height=12)
        nb2.add(self.txt, text="Kết quả")
        nb2.add(self.txt_ct, text="Công thức & lưu ý")

    # ====================== TAB TỪNG ĐỒ THỊ ======================
    def dung_tab_do_thi(self, ma, vi_tri_tab):
        t = ttk.Frame(self.nb)
        self.nb.add(t, text=f"{SO_TAB[vi_tri_tab - 2]} {KY_HIEU_TAB[ma]}")
        trai = ttk.Frame(t, width=360)
        trai.pack(side="left", fill="y", padx=(6, 2), pady=6)
        trai.pack_propagate(False)
        # thanh nút
        nut = ttk.Frame(trai)
        nut.pack(fill="x", pady=(0, 4))
        ttk.Button(nut, text="⟳ Vẽ lại", command=lambda: self.ve_tab(ma)).pack(side="left")
        ttk.Button(nut, text="↺ Mặc định", command=lambda: self.mac_dinh_tab(ma)).pack(side="left", padx=3)
        nut2 = ttk.Frame(trai)
        nut2.pack(fill="x", pady=(0, 4))
        dd = tk.StringVar(value="png")
        ttk.Button(nut2, text="💾 Xuất hình", command=lambda: self.xuat_mot(ma, dd.get())).pack(side="left")
        ttk.Combobox(nut2, textvariable=dd, values=DINH_DANG, width=5, state="readonly").pack(side="left", padx=3)
        ttk.Button(nut2, text="Vẽ ra Origin", command=lambda: self.ve_origin(ma)).pack(side="left", padx=3)
        # vùng cuộn
        kh = tk.Canvas(trai, highlightthickness=0)
        sb = ttk.Scrollbar(trai, orient="vertical", command=kh.yview)
        nd = ttk.Frame(kh)
        nd.bind("<Configure>", lambda e: kh.configure(scrollregion=kh.bbox("all")))
        kh.create_window((0, 0), window=nd, anchor="nw", width=335)
        kh.configure(yscrollcommand=sb.set)
        kh.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def cuon(e):
            kh.yview_scroll(-1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1, "units")
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            kh.bind(ev, cuon)
            nd.bind(ev, cuon)
        bien = {}
        truong = _truong_cua(ma)
        nhom = [("Dữ liệu của đồ thị này", TRUONG_RIENG[ma]), ("Trục & khoảng", [x for x in truong if x[0] in
                [y[0] for y in TRUC + TRUC_Y2 + KHOANG + KHOANG_Y2] + ["log_x", "log_y"]]), ("Kiểu hiển thị", KIEU), ("Xuất hình (tạp chí)", XUAT)]
        dung = set()
        for ten, ds in nhom:
            ds = [x for x in ds if x[0] not in dung]
            if not ds:
                continue
            lf = ttk.LabelFrame(nd, text=" " + ten + " ")
            lf.pack(fill="x", padx=2, pady=3)
            lf.columnconfigure(1, weight=1)
            for r, (khoa, nhan, loai, tuy, mac) in enumerate(ds):
                dung.add(khoa)
                if khoa in ("log_x", "log_y"):
                    mac = ma == "ragone"
                if loai == "ck":
                    bien[khoa] = tk.BooleanVar(value=bool(mac))
                    ttk.Checkbutton(lf, text=nhan, variable=bien[khoa], command=lambda: self.ve_tab(ma)).grid(row=r, column=0, columnspan=2, sticky="w", padx=6, pady=1)
                    continue
                ttk.Label(lf, text=nhan, wraplength=150, justify="right").grid(row=r, column=0, sticky="e", padx=(4, 2), pady=1)
                bien[khoa] = tk.StringVar(value=mac)
                if loai == "cb":
                    x = ttk.Combobox(lf, textvariable=bien[khoa], values=list(tuy), width=22, state="readonly")
                    x.bind("<<ComboboxSelected>>", lambda e: self.ve_tab(ma))
                else:
                    x = ttk.Entry(lf, textvariable=bien[khoa], width=24)
                    x.bind("<Return>", lambda e: self.ve_tab(ma))
                    x.bind("<FocusOut>", lambda e: self.ve_tab(ma))
                x.grid(row=r, column=1, sticky="ew", padx=(0, 4), pady=1)
        ttk.Label(nd, text="Ô trống = tự động. Xem trước dùng cỡ chữ mặc định; hình xuất ra theo đúng khổ của mẫu tạp chí đã chọn.",
                  foreground="#666", wraplength=320, justify="left").pack(fill="x", padx=4, pady=4)
        # vùng đồ thị
        phai = ttk.Frame(t)
        phai.pack(side="left", fill="both", expand=True, padx=(2, 6), pady=6)
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        fig = Figure(figsize=(6.4, 5.2), dpi=100)
        cvs = FigureCanvasTkAgg(fig, master=phai)
        cvs.get_tk_widget().pack(fill="both", expand=True)
        ghi = tk.StringVar(value="")
        ttk.Label(phai, textvariable=ghi, foreground="#555", wraplength=700, justify="left").pack(fill="x")
        self.tab[ma] = dict(bien=bien, truong=truong, fig=fig, cv=cvs, ghi=ghi, khung=t)

    def _doc_tab(self, ma):
        """Thiết lập đã đọc của một đồ thị (giá trị thật, không phải nhãn). Ném ValueError nếu nhập sai."""
        out = {}
        tb = self.tab[ma]
        for khoa, nhan, loai, tuy, mac in tb["truong"]:
            v = tb["bien"][khoa].get()
            if loai == "cb":
                out[khoa] = tuy.get(v, next(iter(tuy.values())))
            elif loai == "ck":
                out[khoa] = bool(v)
            elif loai in ("so", "int"):
                v = str(v).strip().replace(",", ".")
                if not v:
                    out[khoa] = None
                    continue
                try:
                    out[khoa] = int(float(v)) if loai == "int" else float(v)
                except ValueError:
                    raise ValueError(f"'{nhan}' phải là số.")
            else:
                out[khoa] = str(v).strip()
        return out

    def doc_tat_ca(self):
        return {ma: self._doc_tab(ma) for ma in gp.TEN_DO_THI}

    def mac_dinh_tab(self, ma):
        for khoa, nhan, loai, tuy, mac in self.tab[ma]["truong"]:
            v = self.tab[ma]["bien"][khoa]
            v.set(bool(mac) if loai == "ck" else mac)
        self.ve_tab(ma)

    def ve_tab(self, ma):
        tb = self.tab[ma]
        fig = tb["fig"]
        fig.clf()
        ax = fig.add_subplot(111)
        if not self.kq:
            ax.text(0.5, 0.5, "Chưa có kết quả.\nVào tab ① để thêm file và bấm Phân tích.", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            tb["cv"].draw()
            return
        try:
            cau = {ma: self._doc_tab(ma)}
        except ValueError as e:
            tb["ghi"].set("⚠ " + str(e))
            return
        d = gp.du_lieu_do_thi(self.kq, cau)[ma]
        if not any(len(s["x"]) for s in d["series"]):
            ax.text(0.5, 0.5, "Không đủ dữ liệu cho đồ thị này\n(retention / chu kỳ cần một mức dòng có ≥ 3 chu kỳ)", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            tb["ghi"].set("")
        else:
            try:
                gp.ve_len_truc(fig, ax, d)
            except Exception as e:  # noqa: BLE001
                tb["ghi"].set("⚠ Không vẽ được với thiết lập này: " + str(e))
                tb["cv"].draw()
                return
            tb["ghi"].set(" · ".join(d.get("ghi_chu") or []))
        tb["cv"].draw()

    def chon_bo_ct(self):
        b = BO_CT[self.cv["bo_ct"].get()]
        if b == "excel":
            self.cv["dv"].set(next(k for k, v in CACH_DV.items() if v == "gom_ir"))
            self.cv["cach_e"].set(next(k for k, v in CACH_E.items() if v == "cv2_dv"))
        else:
            self.cv["dv"].set(next(k for k, v in CACH_DV.items() if v == "tru_ir"))
            self.cv["cach_e"].set(next(k for k, v in CACH_E.items() if v == "tich_phan"))
        self.cv["cach_c"].set(next(k for k, v in CACH_C.items() if v == "tich_phan"))
        self.v_tt.set("Đã đổi bộ công thức: bấm ▶ Phân tích để tính lại.")

    def chon_dien_cuc(self):
        v = dc.eref_cua(self.cv["dien_cuc"].get())
        if v is not None:
            self.cv["e_ref"].set(f"{v:g}")
        self.ve_tat_ca_tab()

    def ve_tat_ca_tab(self):
        for ma in gp.TEN_DO_THI:
            self.ve_tab(ma)

    # ====================== DANH SÁCH MẪU ======================
    def doi_chuan(self):
        dt = CHUAN[self.cv["chuan"].get()] == "dien_tich"
        self.fr.config(text=" Mẫu  (tick = dùng · tên · " + ("diện tích cm²" if dt else "khối lượng hoạt tính mg") + " · I (mA, tùy chọn; trống = đọc từ file) · ⚙ chọn cột · ✖ bỏ) ")

    def them_file(self):
        ds = filedialog.askopenfilenames(parent=self.w, title="Chọn file GCD thô",
                                         filetypes=[("Dữ liệu", "*.txt *.csv *.dat *.mpt *.tsv *.xlsx *.xls"), ("Tất cả", "*.*")])
        for p in ds:
            self.them(p)

    def lay_tu_app(self):
        if not self.ds_file:
            messagebox.showinfo("Siêu tụ/Pin", "Chưa kết nối danh sách file của app.", parent=self.w)
            return
        ds = self.ds_file()
        if not ds:
            messagebox.showinfo("Siêu tụ/Pin", "Danh sách file trong app đang trống. Hãy thêm file ở tab Dữ liệu.", parent=self.w)
            return
        for p in ds:
            self.them(p)

    def them(self, p, ten=None, gia_tri="", cot=None, dong_ma=""):
        p = os.path.normpath(p)
        if any(h["path"] == p for h in self.hang):
            return False
        try:
            tn, arr = gp.doc_bang(p)
            ds = cot or gp.doan_cot(tn, arr)
            ghi = "t=" + (tn[ds["t"]] if ds.get("t") is not None else "?") + " · V=" + (tn[ds["v"]] if ds.get("v") is not None else "?") + \
                  " · I=" + (tn[ds["i"]] if ds.get("i") is not None else "(không có)")
        except Exception as e:  # noqa: BLE001
            messagebox.showwarning("Siêu tụ/Pin", f"Không đọc được {os.path.basename(p)}:\n{e}", parent=self.w)
            return False
        tso = gp.doc_thong_so_cs(p)
        if tso:
            ghi += " · header CS Studio: " + ", ".join(x for x in (
                f"KL {tso['khoi_luong_mg']:g} mg" if "khoi_luong_mg" in tso else "", f"{tso['dong_mA']:g} mA" if "dong_mA" in tso else "",
                f"{tso['e_thap']:g}–{tso['e_cao']:g} V" if "e_cao" in tso and "e_thap" in tso else "") if x)
            if str(gia_tri).strip() == "" and tso.get("khoi_luong_mg"):
                gia_tri = f"{tso['khoi_luong_mg']:g}"
        if str(gia_tri).strip() == "":                      # header không có khối lượng → thử đọc từ tên file/tên mẫu (vd ..._2.32mg)
            kl = gp.khoi_luong_tu_ten(p, ten)
            if kl:
                gia_tri = f"{kl:g}"
                ghi += f" · KL {kl:g} mg lấy từ tên file (hãy kiểm tra)"
        if str(gia_tri).strip() == "" and self.v_kl.get().strip():
            gia_tri = self.v_kl.get().strip().replace(",", ".")
            ghi += " · KL lấy từ ô 'Khối lượng (mg)' phía trên"
        h = {"path": p, "ten": ten or os.path.splitext(os.path.basename(p))[0], "cot": cot, "ghi_chu": ghi,
             "dung": tk.BooleanVar(value=True), "ten_cot": tn}
        h["v_ten"], h["v_gt"], h["v_i"] = tk.StringVar(value=h["ten"]), tk.StringVar(value=str(gia_tri)), tk.StringVar(value=str(dong_ma or ""))
        self.hang.append(h)
        self.lam_moi()
        return True

    def lam_moi(self):
        for c in self.fr.winfo_children():
            c.destroy()
        for k, h in enumerate(self.hang):
            r = ttk.Frame(self.fr)
            r.pack(fill="x", padx=4, pady=1)
            ttk.Checkbutton(r, variable=h["dung"]).pack(side="left")
            tk.Label(r, width=2, bg=gp.MAU_DS[k % len(gp.MAU_DS)]).pack(side="left", padx=2)
            ttk.Entry(r, textvariable=h["v_ten"], width=22).pack(side="left", padx=2)
            ttk.Entry(r, textvariable=h["v_gt"], width=8).pack(side="left", padx=2)
            ttk.Entry(r, textvariable=h["v_i"], width=8).pack(side="left", padx=2)
            ttk.Button(r, text="⚙", width=3, command=lambda h=h: self.chon_cot(h)).pack(side="left", padx=2)
            ttk.Label(r, text=h["ghi_chu"], foreground="#666").pack(side="left", padx=6)
            ttk.Button(r, text="✖", width=3, command=lambda h=h: self.bo(h)).pack(side="right")

    def bo(self, h):
        self.hang.remove(h)
        self.lam_moi()

    def chon_cot(self, h):
        t = tk.Toplevel(self.w)
        t.title("Chọn cột: " + os.path.basename(h["path"]))
        ten = ["(không có)"] + [f"{j}: {x}" for j, x in enumerate(h["ten_cot"])]
        _, arr = gp.doc_bang(h["path"])
        ds = h["cot"] or gp.doan_cot(h["ten_cot"], arr)
        bien = {}
        for r, (k, nhan) in enumerate((("t", "Thời gian"), ("v", "Điện thế"), ("i", "Dòng"))):
            ttk.Label(t, text=nhan + ":").grid(row=r, column=0, padx=8, pady=4, sticky="e")
            b = tk.StringVar(value=ten[(ds[k] + 1) if ds.get(k) is not None else 0])
            ttk.Combobox(t, textvariable=b, values=ten, width=34, state="readonly").grid(row=r, column=1, padx=8)
            bien[k] = b
        ttk.Label(t, text="Đơn vị lấy theo tên cột, vd (mA), /mA, (s), (min); mặc định A, V, s.", foreground="#555").grid(row=3, column=0, columnspan=2, padx=8, pady=2)

        def ok():
            kq = {}
            for k, b in bien.items():
                s = b.get()
                kq[k] = None if s.startswith("(") else int(s.split(":")[0])
            h["cot"] = kq
            h["ghi_chu"] = " · ".join(f"{k}=" + (h["ten_cot"][v] if v is not None else "(không có)") for k, v in kq.items())
            t.destroy()
            self.lam_moi()
        ttk.Button(t, text="OK", command=ok).grid(row=4, column=0, columnspan=2, pady=8)

    # ====================== PHÂN TÍCH ======================
    def cau_hinh(self):
        def so(khoa, ten, kieu=float):
            try:
                return kieu(self.cv[khoa].get().replace(",", "."))
            except ValueError:
                raise ValueError(f"'{ten}' phải là số.")
        p = so("p", "p")
        if not 0 <= p < 1:
            raise ValueError("p phải trong [0, 1).")
        dong = so("dong", "Dòng không đổi") if self.cv["dong"].get().strip() else None
        return dict(kieu_cell=KIEU_CELL[self.cv["cell"].get()], chuan=CHUAN[self.cv["chuan"].get()], cach_c=CACH_C[self.cv["cach_c"].get()],
                    cach_dv=CACH_DV[self.cv["dv"].get()], cach_e=CACH_E[self.cv["cach_e"].get()],
                    doc_p=p, chinh=CHINH[self.cv["chinh"].get()], v_tang_nap=CHIEU[self.cv["chieu"].get()],
                    bo_chu_ky_dau=self.bo_dau.get(), dong_hang_ma=dong, nguong_tu=so("n_tu", "Ngưỡng dạng tụ"), nguong_pin=so("n_pin", "Ngưỡng dạng pin"),
                    quy_rhe=bool(self.cv["quy_rhe"].get()), ph=so("ph", "pH"), e_ref=so("e_ref", "Eref"), nernst=so("nernst", "Hệ số Nernst"),
                    ten_dien_cuc="" if dc.eref_cua(self.cv["dien_cuc"].get()) is None else self.cv["dien_cuc"].get().split("  ")[0])

    def ds_mau(self):
        ds = []
        for k, h in enumerate(self.hang):
            if not h["dung"].get():
                continue
            try:
                gt = float(h["v_gt"].get().replace(",", "."))
            except ValueError:
                gt = 0.0
            try:
                dong = float(h["v_i"].get().replace(",", ".") or 0)
            except ValueError:
                raise ValueError(f"Dòng I (mA) của mẫu '{h['v_ten'].get()}' phải là số (hoặc để trống để đọc từ file).")
            ds.append(dict(ten=h["v_ten"].get().strip() or h["ten"], path=h["path"], gia_tri=gt, cot=h["cot"], dong_ma=dong, mau=gp.MAU_DS[k % len(gp.MAU_DS)]))
        return ds

    def phan_tich(self):
        try:
            ds = self.ds_mau()
        except ValueError as e:
            messagebox.showwarning("Siêu tụ/Pin", str(e), parent=self.w)
            return
        if not ds:
            messagebox.showinfo("Siêu tụ/Pin", "Hãy thêm và tick ít nhất một mẫu.", parent=self.w)
            return
        thieu = [d["ten"] for d in ds if d["gia_tri"] <= 0]
        if thieu and not messagebox.askyesno("Siêu tụ/Pin", "Mẫu chưa có khối lượng/diện tích: " + ", ".join(thieu) +
                                             "\nKết quả quy về F/g, mAh/g, Wh/kg sẽ vô nghĩa (chỉ C, Q, ESR, CE, retention đúng).\nVẫn phân tích?", parent=self.w):
            return
        try:
            cfg = self.cau_hinh()
        except ValueError as e:
            messagebox.showwarning("Siêu tụ/Pin", str(e), parent=self.w)
            return
        for d in ds:
            if d["gia_tri"] <= 0:
                d["gia_tri"] = 1.0
        self.v_tt.set("Đang phân tích...")
        self.w.update_idletasks()
        try:
            self.kq = gp.chay(ds, cfg)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Siêu tụ/Pin", f"Lỗi khi phân tích: {e}", parent=self.w)
            self.v_tt.set("Lỗi.")
            return
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", gp.tom_tat(self.kq))
        self.txt_ct.delete("1.0", "end")
        self.txt_ct.insert("1.0", "\n\n".join(f"{x['Mục']}: {x['Nội dung']}" for x in gp.cong_thuc_ghi_chu(self.kq)))
        self.v_tt.set(f"Xong: {len(self.kq['mau'])} mẫu. Đại lượng chính: {self.kq['ly_do']}. Chuyển sang các tab ②–⑦ để xem và chỉnh từng đồ thị.")
        self.ve_tat_ca_tab()

    # ====================== XUẤT ======================
    def _chon_thu_muc(self):
        if not self.kq:
            messagebox.showinfo("Siêu tụ/Pin", "Hãy phân tích trước.", parent=self.w)
            return None
        return filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu kết quả") or None

    def _cau(self):
        try:
            return self.doc_tat_ca()
        except ValueError as e:
            messagebox.showwarning("Siêu tụ/Pin", str(e), parent=self.w)
            return None

    def xuat_tat_ca(self):
        d = self._chon_thu_muc()
        cau = self._cau() if d else None
        if not d or cau is None:
            return
        ra = self._xuat_file(d, None, cau)
        messagebox.showinfo("Siêu tụ/Pin", "Đã ghi:\n" + "\n".join(os.path.basename(p) for p in ra) + f"\n\nThư mục: {d}", parent=self.w)

    def xuat_mot(self, ma, dang="png"):
        d = self._chon_thu_muc()
        cau = self._cau() if d else None
        if not d or cau is None:
            return
        p = gp.xuat_hinh(self.kq, d, ten="GCD", ds=[ma], dang=dang, cau_hinh_dt=cau)
        if not p:
            messagebox.showinfo("Siêu tụ/Pin", "Đồ thị này chưa có dữ liệu để xuất.", parent=self.w)
            return
        messagebox.showinfo("Siêu tụ/Pin", "Đã ghi:\n" + "\n".join(os.path.basename(x) for x in p) + f"\n\nThư mục: {d}", parent=self.w)

    def _xuat_file(self, d, ma, cau):
        ten = "GCD" if ma is None else f"GCD_{ma}"
        r = gp.xuat_tat_ca(self.kq, d, ten=ten, ds_hinh=None if ma is None else [ma], cau_hinh_dt=cau)
        png = gp.xuat_hinh(self.kq, d, ten=ten, ds=None if ma is None else [ma], cau_hinh_dt=cau)
        self.json_origin = r["json"]
        return [r["excel"]] + list(r["csv"].values()) + [r["json"]] + png

    def ve_origin(self, ma):
        d = self._chon_thu_muc()
        cau = self._cau() if d else None
        if not d or cau is None:
            return
        if self.lenh_origin is None:
            messagebox.showinfo("Siêu tụ/Pin", "Chưa kết nối được Origin. Dùng 'Xuất Excel + CSV...' rồi import các file CSV vào Origin.", parent=self.w)
            return
        self._xuat_file(d, ma, cau)
        lenh = list(self.lenh_origin()) + ["--json", self.json_origin, "--thu-muc-ra", d]
        self.v_tt.set("Đang vẽ trong Origin (cần Origin đã cài; cửa sổ Origin sẽ hiện)...")
        kqc = {"xong": False, "out": ""}

        def chay():
            try:
                r = subprocess.run(lenh, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   creationflags=0x08000000 if os.name == "nt" else 0)
                kqc["out"] = (r.stdout or "") + (r.stderr or "")
            except Exception as e:  # noqa: BLE001
                kqc["out"] = str(e)
            kqc["xong"] = True
        threading.Thread(target=chay, daemon=True).start()
        self.w.after(500, lambda: self._cho(kqc, d))

    def _cho(self, kqc, d):
        if not kqc["xong"]:
            self.w.after(500, lambda: self._cho(kqc, d))
            return
        self.v_tt.set("Origin xong.")
        messagebox.showinfo("Origin", (kqc["out"].strip()[-1500:] or "(không có thông báo)") + f"\n\nThư mục: {d}", parent=self.w)

    # ====================== LƯU / MỞ THIẾT LẬP ======================
    def thiet_lap(self, kem_mau=True):
        """Toàn bộ thiết lập dưới dạng dict JSON (nhãn người dùng đang thấy, nên đọc lại được ngay)."""
        d = {"phien_ban": 2, "chung": {k: v.get() for k, v in self.cv.items()}, "bo_chu_ky_dau": self.bo_dau.get(),
             "do_thi": {ma: {k: v.get() for k, v in tb["bien"].items()} for ma, tb in self.tab.items()}}
        if kem_mau:
            d["mau"] = [{"path": h["path"], "ten": h["v_ten"].get(), "gia_tri": h["v_gt"].get(), "dong_ma": h["v_i"].get(), "cot": h["cot"], "dung": h["dung"].get()} for h in self.hang]
        return d

    def ap_thiet_lap(self, d, nap_mau=True):
        thieu = []
        ds_nhan = {"cell": KIEU_CELL, "chuan": CHUAN, "chieu": CHIEU, "chinh": CHINH, "cach_c": CACH_C, "dv": CACH_DV, "cach_e": CACH_E, "bo_ct": BO_CT}
        for k, v in (d.get("chung") or {}).items():
            if k in self.cv:
                if k in ds_nhan and v not in ds_nhan[k]:          # nhãn cũ (bản trước) → tìm nhãn mới cùng phần đầu, không thấy thì giữ mặc định
                    v = next((x for x in ds_nhan[k] if x[:14] == str(v)[:14]), None)
                    if v is None:
                        continue
                self.cv[k].set(v)
        if "bo_chu_ky_dau" in d:
            self.bo_dau.set(bool(d["bo_chu_ky_dau"]))
        for ma, vals in (d.get("do_thi") or {}).items():
            if ma in self.tab:
                for k, v in vals.items():
                    if k in self.tab[ma]["bien"]:
                        self.tab[ma]["bien"][k].set(v)
        if nap_mau:
            for m in d.get("mau") or []:
                if os.path.isfile(m["path"]):
                    cot = m.get("cot")
                    if self.them(m["path"], m.get("ten"), m.get("gia_tri", ""), cot, m.get("dong_ma", "")):
                        self.hang[-1]["dung"].set(bool(m.get("dung", True)))
                else:
                    thieu.append(m["path"])
        self.doi_chuan()
        self.ve_tat_ca_tab()
        return thieu

    def luu_thiet_lap(self):
        p = filedialog.asksaveasfilename(parent=self.w, title="Lưu thiết lập", defaultextension=".gcd.json", filetypes=[("Thiết lập GCD", "*.json")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.thiet_lap(), f, ensure_ascii=False, indent=1)
        self.v_tt.set("Đã lưu thiết lập (gồm danh sách mẫu, khối lượng, cột và thiết lập từng đồ thị): " + p)

    def mo_thiet_lap(self):
        p = filedialog.askopenfilename(parent=self.w, title="Mở thiết lập", filetypes=[("Thiết lập GCD", "*.json"), ("Tất cả", "*.*")])
        if not p:
            return
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            thieu = self.ap_thiet_lap(d)
        except Exception as e:  # noqa: BLE001
            messagebox.showwarning("Siêu tụ/Pin", f"Không đọc được thiết lập:\n{e}", parent=self.w)
            return
        self.v_tt.set("Đã mở thiết lập." + (f" Không thấy {len(thieu)} file: " + ", ".join(os.path.basename(x) for x in thieu) if thieu else " Bấm Phân tích để tính lại."))

    def tu_nap(self):
        """Nhớ thiết lập lần trước (không nạp lại danh sách mẫu)."""
        try:
            if os.path.isfile(self.tep_nho):
                with open(self.tep_nho, encoding="utf-8") as f:
                    self.ap_thiet_lap(json.load(f), nap_mau=False)
        except Exception:
            pass

    def dong(self):
        try:
            os.makedirs(os.path.dirname(self.tep_nho), exist_ok=True)
            with open(self.tep_nho, "w", encoding="utf-8") as f:
                json.dump(self.thiet_lap(kem_mau=False), f, ensure_ascii=False, indent=1)
        except Exception:
            pass
        self.w.destroy()
