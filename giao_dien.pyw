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
et = _nhap("ecsa_tuong_tac")

THU_MUC_RA_MD = os.path.join(os.path.expanduser("~"), "Documents", "DienHoa_KetQua")
PHIEN_BAN_CAI_DAT = 3
LOAI = ["Tự nhận dạng", "LSV", "CV", "IT", "EIS", "ECSA (nhiều file CV)", "Tafel", "Phổ (XRD / Raman / XPS)"]
TABS = ["Dữ liệu", "Phân tích", "Hình", "Xuất", "Phổ", "Hỏi đáp", "Trợ giúp"]
KHO_HINH = ["Cột đôi 17.8 cm", "Cột đơn 8.6 cm"]
KIEU_PHO = ["xrd", "raman", "xps", "ftir", "khac"]
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
    "r_s": "0", "ir_pct": "100", "tai_trong": "", "qua_the_ht": "300", "so_mol_tam": "", "khoi_luong_mol": "",
    "ti_le_tam": "1", "n_e": "4", "so_sanh": True,
    "khong_rhe": False, "khong_qua_the": False, "tafel_che_do": "dong", "tafel_e_min": "", "tafel_e_max": "",
    "fe_v_h2": "", "fe_nhiet_do": "25", "fe_ap_suat": "101.325", "fe_n": "2", "fe_hoi_nuoc": True, "fit_eis": False,
    "tai_lieu": "", "hinh_bai_bao": False, "hinh_cot": KHO_HINH[0], "hb_png": True, "hb_pdf": True, "hb_tiff": True,
    "hinh_dpi": "600", "tof_e_min": "-1.5", "tof_e_max": "-1.1", "tof_n": "2", "tof_n_q": "2", "tof_v": "", "tof_dien_tich": "Vòng kín (∮ I dE)", "tof_rhe": False, "qs_thu_muc": "", "qs_nguong": "3", "qs_duoi": "0", "qs_da_rhe": False, "qs_origin": True, "qs_matplotlib": True,
    "hinh_o": "", "hinh_chu": "(A) (B) (C)", "pho_kieu": "xrd", "pho_doi": "1.1", "pho_dinh": "0", "pho_chuan_hoa": True,
    "pho_x_min": "", "pho_x_max": "", "tab_chon": "Dữ liệu",
    "zoom": "90", "xuat_excel": True, "i_muc_tieu": "10", "e_can_bang": "1.23",
}
KHOA_KHONG_VAO_CAU_HINH = {"zoom", "thu_muc_ra", "tab_chon", "tai_lieu"}
KHOA_CAU_HINH = [k for k in MAC_DINH if k not in KHOA_KHONG_VAO_CAU_HINH]
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
    "r_s": "Điện trở dung dịch Rs (Ω) để bù iR: E thật = E đo − i × Rs. 0 = không bù.\nLấy từ EIS đo cùng điều kiện (nút 'Lấy Rs từ EIS'). i là dòng đo thực (A) chưa chia diện tích.",
    "ir_pct": "Phần trăm iR được bù (thường 85–100%).",
    "tai_trong": "Tải trọng xúc tác trên điện cực (mg/cm²). Dùng tính hoạt độ khối = J ÷ tải trọng (A/g).",
    "qua_the_ht": "Các quá thế khảo sát (mV) để tính J, hoạt độ khối và TOF, cách nhau dấu phẩy. VD: 300 hoặc 250, 300, 350.",
    "so_mol_tam": "Số tâm hoạt động (µmol/cm²), ví dụ tính từ điện lượng pic oxi hóa-khử. Nếu để trống, app có thể tính từ tải trọng và M.",
    "khoi_luong_mol": "Khối lượng mol M (g/mol) của xúc tác. Dùng cùng tải trọng và tỉ lệ tâm để ước tính số mol tâm (TOF theo tổng nguyên tử kim loại).",
    "ti_le_tam": "Tỉ lệ nguyên tử hoạt động (0–1) khi tính số tâm từ tải trọng và M. Mặc định 1 (coi mọi nguyên tử đều hoạt động → TOF là cận dưới).",
    "n_e": "Số electron trên mỗi phân tử sản phẩm: OER = 4 (O₂), HER = 2 (H₂).",
    "tof_e": "Cửa sổ điện thế của vòng CV dùng để tính diện tích/Q (V). Mặc định -1.5 đến -1.1, theo ĐIỆN THẾ GHI TRONG FILE (chưa quy đổi RHE). Để trống cả hai ô = dùng cả chu kỳ CV.",
    "tof_n": "n: số electron trao đổi của phản ứng trong TOF = I / (n·F·N). HER: 2. Tự đổi theo phản ứng.",
    "tof_n_q": "n dùng khi tính N = Q / (n·F) (số e⁻ trao đổi của cặp oxi hóa-khử đo bằng điện lượng Q). Để trống = bằng n ở trên. Nếu hai số bằng nhau thì TOF = I / Q.",
    "tof_v": "Tốc độ quét (mV/s) dùng để tính Q = diện tích / tốc độ quét. Để trống = lấy từ dữ liệu. Nhiều mẫu khác tốc độ: cách nhau dấu CHẤM PHẨY theo thứ tự mẫu CV/LSV trong bảng (VD: 50; 20; 50).",
    "tof_dien_tich": "Vòng kín: |∮ I dE| = diện tích bao quanh đường CV (mặc định). Tổng |I|: tích phân |I||dE| trên cả hai chiều quét (gồm cả phần dòng HER).",
    "qs_nguong": "Ngưỡng nhảy điện thế (mV): E đổi quá ngưỡng này (hoặc thời gian bị đặt lại) = bước điện thế mới. Mặc định 3 mV.",
    "qs_duoi": "Lấy trung bình bao nhiêu % điểm cuối của mỗi bước (giảm nhiễu). 0 = chỉ lấy đúng điểm cuối cùng.",
    "qs_da_rhe": "Tick nếu E trong file Qs-LSV đã là RHE (app sẽ không cộng pH và Eref nữa).",
    "tof_rhe": "Tick nếu cửa sổ điện thế ở trên là điện thế đã quy đổi sang RHE (theo pH và Eref ở tab Dữ liệu) thay vì điện thế ghi trong file.",
    "so_sanh": "Xuất bảng xếp hạng và biểu đồ cột so sánh các mẫu: quá thế, Tafel, hoạt độ khối, TOF (so_sanh_tong_hop.png/.csv).",
    "khong_rhe": "Dùng cho phép đo hai điện cực (điện thế tế bào, vd 1.61 V để đạt 10 mA/cm²): giữ nguyên E đo, không cộng 0.0592×pH + Eref.",
    "khong_qua_the": "Phản ứng không có điện thế cân bằng rõ ràng (vd oxi hóa glucose): bỏ cột quá thế, xếp hạng theo điện thế tại dòng mục tiêu.",
    "tafel_e": "Vùng điện thế (V) dùng để fit Tafel, ví dụ 1.40 đến 1.55. Chọn 'Theo điện thế' ở bên trái. Cần ít nhất 3 điểm trong vùng.",
    "tai_lieu": "File CSV các nghiên cứu khác (cột: Xúc tác, Điện giải, E tại 10 mA/cm² (V vs RHE), Tafel (mV/dec), Tài liệu). App ghép với kết quả của bạn thành sheet 'So sánh tài liệu'.",
    "fe_v_h2": "Thể tích khí thu được (mL) bằng phương pháp dời nước, theo thứ tự các file IT, cách nhau dấu phẩy. VD: 3.2, 4.0. Để trống = không tính FE.\nFE = n·F·n_khí / Q × 100%, Q = ∫|i|dt.",
    "fe_n": "Số electron mỗi phân tử khí: H₂ = 2, O₂ = 4.",
    "fe_nhiet_do": "Nhiệt độ lúc đo thể tích khí (°C).",
    "fe_ap_suat": "Áp suất khí quyển (kPa), mặc định 101.325.",
    "fe_hoi_nuoc": "Khí thu bằng cách dời nước bão hòa hơi nước; trừ áp suất hơi nước (công thức Tetens) để có áp suất riêng phần của khí.",
    "fit_eis": "Fit mô hình Rs + (Rct ‖ CPE) bằng Levenberg–Marquardt: xuất Rs, Rct, Q, n, C_eff và sai số; vẽ Nyquist có đường fit.",
    "hinh_bai_bao": "Ghép các hình (LSV, Tafel, Nyquist, i–t, cột so sánh) thành một hình nhiều ô, đúng khổ cột tạp chí, xuất PNG/PDF/TIFF.",
    "hinh_o": "Danh sách ô của từng hình (soạn bằng nút 'Soạn hình & tên mẫu'). Để trống = tự chọn theo dữ liệu.",
    "pho_doi": "Khoảng cách giữa các phổ khi xếp chồng (1.1 = hơn một chiều cao phổ chuẩn hóa).",
    "pho_dinh": "Số đỉnh cao nhất được ghi giá trị x trên mỗi phổ (0 = không ghi).",
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


LOAI_O_HINH = [("lsv", "Đường J–E (LSV/CV)"), ("tafel", "Đồ thị Tafel + đường fit"), ("eis", "Nyquist (EIS, có fit)"),
               ("it", "Dòng theo thời gian (i–t)"), ("cot", "Biểu đồ cột so sánh")]


class CongCuQsTof:
    """Công cụ riêng: file CV -> N (qua Q); thư mục Qs-LSV -> I theo E; vẽ CV và TOF theo E (RHE)."""

    def __init__(self, app):
        self.app = app
        self.q = queue.Queue()
        self.dang = False
        self.mau = [{"path": m["path"], "nhan": m["nhan"], "mau": m["mau"], "qs": ""} for m in app.muc
                    if str(m.get("loai_nhan", "")).startswith(("CV", "LSV"))]
        w = self.w = tk.Toplevel(app.root)
        w.title("Công cụ Qs-LSV & TOF")
        w.geometry("1020x760")
        w.minsize(900, 600)
        w.transient(app.root)
        w.columnconfigure(0, weight=1)
        ttk.Label(w, foreground="#444", justify="left", wraplength=980, text=(
            "TOF = |I| / (n·F·N);  N = Q / (n·F);  Q = diện tích CV / tốc độ quét.  I lấy từ bộ dữ liệu Qs-LSV: với MỖI bước điện thế chỉ lấy điểm (E, I) CUỐI "
            "(E đã quy đổi RHE, I là dòng ĐÃ QUY ĐỔI mA/cm² theo hệ số nhân/chia ở tab Dữ liệu; Q và N cũng tính trên cm²). Mỗi file Qs-LSV có thể là một bước hoặc nhiều bước bậc thang. "
            "Gom file Qs-LSV vào một thư mục: app tự ghép với mẫu CV theo tên (tên thư mục con hoặc tên file chứa nhãn mẫu), "
            "hoặc gán thủ công cho từng mẫu.")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
        f1 = ttk.LabelFrame(w, text="Mẫu (mỗi mẫu = 1 file CV + dữ liệu Qs-LSV của nó)")
        f1.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        f1.columnconfigure(0, weight=1)
        self.tv = ttk.Treeview(f1, columns=("nhan", "cv", "qs"), show="headings", height=5, selectmode="browse")
        for c, t, r in (("nhan", "Nhãn", 140), ("cv", "File CV", 380), ("qs", "Qs-LSV (trống = tự ghép theo tên trong thư mục chung)", 420)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=r, anchor="w")
        self.tv.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        nut = ttk.Frame(f1)
        nut.grid(row=1, column=0, sticky="w", padx=6, pady=(0, 4))
        for ten, lenh in (("Thêm CV...", self.them_cv), ("Xóa mẫu", self.xoa), ("Đổi nhãn", self.doi_nhan),
                          ("Gán thư mục Qs-LSV cho mẫu chọn...", self.gan_thu_muc), ("Gán file Qs-LSV...", self.gan_file),
                          ("Xóa gán (tự ghép)", self.xoa_gan)):
            ttk.Button(nut, text=ten, command=lenh).pack(side="left", padx=(0, 4))
        f2 = ttk.Frame(w)
        f2.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        f2.columnconfigure(1, weight=1)
        ttk.Label(f2, text="Thư mục Qs-LSV chung:").grid(row=0, column=0, sticky="w")
        ttk.Entry(f2, textvariable=app.qs_thu_muc).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(f2, text="Chọn...", command=self.chon_chung).grid(row=0, column=2)
        ttk.Label(f2, text="Thư mục kết quả:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.ra = tk.StringVar(value=os.path.join(app.thu_muc_ra.get(), "Qs_LSV_TOF"))
        ttk.Entry(f2, textvariable=self.ra).grid(row=1, column=1, sticky="ew", padx=6, pady=(4, 0))
        ttk.Button(f2, text="Chọn...", command=self.chon_ra).grid(row=1, column=2, pady=(4, 0))
        f3 = ttk.LabelFrame(w, text="Thông số")
        f3.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        r1 = ttk.Frame(f3)
        r1.pack(fill="x", padx=6, pady=3)
        r2 = ttk.Frame(f3)
        r2.pack(fill="x", padx=6, pady=3)
        r3 = ttk.Frame(f3)
        r3.pack(fill="x", padx=6, pady=3)
        for fr, ds in ((r1, (("n (e⁻) của TOF", app.tof_n, 5, "tof_n"), ("n tính N", app.tof_n_q, 5, "tof_n_q"),
                             ("Tốc độ quét CV (mV/s)", app.tof_v, 10, "tof_v"))),
                       (r2, (("CV: E từ (V)", app.tof_e_min, 6, "tof_e"), ("đến (V)", app.tof_e_max, 6, "tof_e"))),
                       (r3, (("Ngưỡng bước (mV)", app.qs_nguong, 5, "qs_nguong"), ("TB % điểm cuối", app.qs_duoi, 5, "qs_duoi")))):
            for ten, bien, rong, goi in ds:
                ttk.Label(fr, text=ten).pack(side="left", padx=(0, 3))
                e = ttk.Entry(fr, textvariable=bien, width=rong)
                e.pack(side="left", padx=(0, 12))
                GoiY(e, GOI_Y.get(goi, ""))
        ttk.Label(r2, text="Diện tích CV:").pack(side="left", padx=(8, 3))
        ttk.Combobox(r2, textvariable=app.tof_dien_tich, values=["Vòng kín (∮ I dE)", "Tổng |I| hai chiều"], state="readonly", width=18).pack(side="left")
        ttk.Checkbutton(r2, text="E CV nhập theo RHE", variable=app.tof_rhe).pack(side="left", padx=12)
        ttk.Checkbutton(r3, text="E trong file Qs-LSV đã là RHE", variable=app.qs_da_rhe).pack(side="left", padx=8)
        r4 = ttk.Frame(f3)
        r4.pack(fill="x", padx=6, pady=3)
        ttk.Label(r4, text="Vẽ hình bằng:").pack(side="left")
        ttk.Checkbutton(r4, text="Origin 2022+ (Qs_CV, Qs_TOF, Qs_LSV_J-E; kiểu/cỡ chữ theo tab Hình)", variable=app.qs_origin).pack(side="left", padx=8)
        ttk.Checkbutton(r4, text="Matplotlib (TOF_QsLSV.png/.pdf: 2 đồ thị A, B)", variable=app.qs_matplotlib).pack(side="left", padx=8)
        ttk.Label(r3, text="(pH, Eref, hệ số nhân/chia I, bù iR lấy ở tab Dữ liệu / Phân tích của app)", foreground="#666").pack(side="left", padx=8)
        fb = ttk.Frame(w)
        fb.grid(row=4, column=0, sticky="w", padx=10, pady=4)
        self.nut = ttk.Button(fb, text="▶  Tính Qs-LSV & vẽ TOF", command=self.chay)
        self.nut.pack(side="left", ipadx=14, ipady=3)
        ttk.Button(fb, text="Xem hình", command=self.xem_hinh).pack(side="left", padx=6)
        ttk.Button(fb, text="Mở thư mục kết quả", command=lambda: self.app.mo_duong_dan(self.ra.get())).pack(side="left", padx=2)
        ttk.Button(fb, text="Đóng", command=w.destroy).pack(side="left", padx=2)
        w.rowconfigure(5, weight=1)
        self.log = scrolledtext.ScrolledText(w, height=14, state="disabled", font=("Consolas", 9))
        self.log.grid(row=5, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.ve()
        w.after(150, self.doc_hang_doi)

    # ---- bảng mẫu
    def ve(self, chon=None):
        self.tv.delete(*self.tv.get_children())
        for k, m in enumerate(self.mau):
            self.tv.insert("", "end", iid=str(k), values=(m["nhan"], m["path"], m["qs"] or "(tự ghép)"))
        if chon is not None and 0 <= chon < len(self.mau):
            self.tv.selection_set(str(chon))

    def chon_k(self):
        s = self.tv.selection()
        if not s:
            messagebox.showinfo("Qs-LSV & TOF", "Hãy chọn một mẫu trong bảng trước.", parent=self.w)
            return None
        return int(s[0])

    def them_cv(self):
        ds = filedialog.askopenfilenames(title="Chọn file CV", filetypes=[("Dữ liệu", "*.txt *.csv *.dat"), ("Tất cả", "*.*")], parent=self.w)
        for p in ds:
            p = os.path.normpath(p)
            if any(m["path"] == p for m in self.mau):
                continue
            self.mau.append({"path": p, "nhan": os.path.splitext(os.path.basename(p))[0],
                             "mau": BANG_MAU[len(self.mau) % len(BANG_MAU)], "qs": ""})
        self.ve()

    def xoa(self):
        k = self.chon_k()
        if k is not None:
            del self.mau[k]
            self.ve(min(k, len(self.mau) - 1))

    def doi_nhan(self):
        k = self.chon_k()
        if k is None:
            return
        moi = simpledialog.askstring("Nhãn mẫu", "Nhãn (cũng dùng để ghép tên file/thư mục Qs-LSV):", initialvalue=self.mau[k]["nhan"], parent=self.w)
        if moi and moi.strip():
            self.mau[k]["nhan"] = moi.strip()
            self.ve(k)

    def gan_thu_muc(self):
        k = self.chon_k()
        if k is None:
            return
        p = filedialog.askdirectory(title="Thư mục Qs-LSV của mẫu này", parent=self.w)
        if p:
            self.mau[k]["qs"] = os.path.normpath(p)
            self.ve(k)

    def gan_file(self):
        k = self.chon_k()
        if k is None:
            return
        ds = filedialog.askopenfilenames(title="File Qs-LSV của mẫu này", filetypes=[("Dữ liệu", "*.txt *.csv *.dat"), ("Tất cả", "*.*")], parent=self.w)
        if ds:
            self.mau[k]["qs"] = "|".join(os.path.normpath(x) for x in ds)
            self.ve(k)

    def xoa_gan(self):
        k = self.chon_k()
        if k is not None:
            self.mau[k]["qs"] = ""
            self.ve(k)

    def chon_chung(self):
        p = filedialog.askdirectory(title="Thư mục chứa các file Qs-LSV", parent=self.w)
        if p:
            self.app.qs_thu_muc.set(p)

    def chon_ra(self):
        p = filedialog.askdirectory(title="Thư mục kết quả", parent=self.w)
        if p:
            self.ra.set(p)

    # ---- chạy
    def ghi(self, s):
        self.log.config(state="normal")
        self.log.insert("end", s)
        self.log.see("end")
        self.log.config(state="disabled")

    def lenh(self):
        a = self.app
        if not self.mau:
            raise ValueError("Chưa có mẫu CV nào (bấm 'Thêm CV...').")
        mat = [m["path"] for m in self.mau if not os.path.isfile(m["path"])]
        if mat:
            raise ValueError("Không tìm thấy file CV (đã bị đổi tên, di chuyển hoặc ổ đĩa/USB chưa cắm):\n" + "\n".join(mat) +
                             "\n\nHãy bấm 'Xóa mẫu' rồi 'Thêm CV...' để chọn lại file.")
        mat = [m["qs"] for m in self.mau if m["qs"] and any(not os.path.exists(x) for x in m["qs"].split("|"))]
        if mat:
            raise ValueError("Không tìm thấy dữ liệu Qs-LSV đã gán:\n" + "\n".join(mat))
        if not a.qs_thu_muc.get().strip() and not any(m["qs"] for m in self.mau):
            raise ValueError("Hãy chọn 'Thư mục Qs-LSV chung' hoặc gán Qs-LSV cho từng mẫu.")
        if a.qs_thu_muc.get().strip() and not os.path.isdir(a.qs_thu_muc.get().strip()):
            raise ValueError("Không tìm thấy thư mục Qs-LSV chung.")
        ph, eref = a.so(a.ph, "pH"), a.so(a.eref, "Eref")
        c = a.lenh_con("xu_ly_dien_hoa.py", "--worker-csv") + [m["path"] for m in self.mau]
        c += ["--loai", "CV", "--ph", str(ph), "--eref", str(eref), "--nhan-i", str(a.so(a.nhan_i, "hệ số nhân I", duong=True)),
              "--chia-i", str(a.so(a.chia_i, "hệ số chia I", duong=True))]
        if a.chu_ky.get().strip():
            c += ["--chu-ky", str(a.so(a.chu_ky, "Chu kỳ CV", int, duong=True))]
        r_s = a.so_khong_am(a.r_s, "Rs")
        if r_s > 0:
            c += ["--r-s", str(r_s), "--ir-phan-tram", str(a.so(a.ir_pct, "% bù iR", duong=True))]
        if a.khong_rhe.get():
            c.append("--khong-rhe")
        for m in self.mau:
            c += ["--nhan", m["nhan"], "--mau-file", m["mau"], "--qs-lsv", m["qs"]]
        c += ["--qs-tof", "--tof-n", str(a.so(a.tof_n, "n (e⁻)", duong=True)),
              "--tof-dien-tich", "tong" if a.tof_dien_tich.get().startswith("Tổng") else "kin",
              "--qs-nguong", str(a.so(a.qs_nguong, "Ngưỡng bước", duong=True)), "--qs-duoi", str(a.so_khong_am(a.qs_duoi, "% điểm cuối"))]
        if a.tof_n_q.get().strip():
            c += ["--tof-n-q", str(a.so(a.tof_n_q, "n tính N", duong=True))]
        if a.qs_thu_muc.get().strip():
            c += ["--qs-thu-muc", a.qs_thu_muc.get().strip()]
        ds_v = [x.strip().replace(",", ".") for x in a.tof_v.get().split(";") if x.strip()]
        try:
            if any(float(x) <= 0 for x in ds_v):
                raise ValueError
        except ValueError:
            raise ValueError("Tốc độ quét (mV/s) phải là số dương; nhiều mẫu thì cách nhau bằng dấu chấm phẩy.")
        if ds_v and len(ds_v) not in (1, len(self.mau)):
            raise ValueError(f"Tốc độ quét: nhập 1 số chung hoặc đúng {len(self.mau)} số (bằng số mẫu), bạn nhập {len(ds_v)}.")
        if ds_v:
            c += ["--tof-v", ";".join(ds_v)]
        if a.tof_e_min.get().strip() or a.tof_e_max.get().strip():
            e1, e2 = a.so(a.tof_e_min, "CV: E từ"), a.so(a.tof_e_max, "CV: E đến")
            if e1 >= e2:
                raise ValueError("CV: 'E từ' phải nhỏ hơn 'E đến'.")
            c += ["--tof-e-min", str(e1), "--tof-e-max", str(e2)]
        if a.tof_rhe.get():
            c.append("--tof-rhe")
        if a.qs_da_rhe.get():
            c.append("--qs-da-rhe")
        c += ["--thu-muc-ra", os.path.abspath(self.ra.get()), "--khong-canh-bao"]
        if not a.qs_origin.get() and not a.qs_matplotlib.get():
            raise ValueError("Hãy tick ít nhất một cách vẽ: Origin hoặc Matplotlib.")
        pre = a.lenh_con("xu_ly_dien_hoa.py", "--worker-csv")
        thamso = c[len(pre):]
        lenhs = []
        if a.qs_origin.get():
            co = a.lenh_con("ve_origin.py", "--worker-origin") + thamso
            co += ["--co-chu", str(a.so(a.co_chu, "Cỡ chữ", int, duong=True)), "--day-net", str(a.so(a.day_net, "Dày nét", duong=True)),
                   "--ti-le", str(a.so(a.ti_le, "Tỉ lệ", duong=True)), "--day-khung", str(a.so(a.day_khung, "Dày khung", duong=True)),
                   "--le-max", str(a.so(a.le_max, "Đệm trục"))] + a.khoang_args() + a.chu_vach_args()
            lenhs.append(("Vẽ bằng Origin", co))
        if a.qs_matplotlib.get():
            lenhs.append(("Tính & vẽ bằng Matplotlib", c if not a.qs_origin.get() else c + ["--khong-ve"]))
        return lenhs

    def chay(self):
        if self.dang:
            return
        try:
            lenhs = self.lenh()
        except ValueError as e:
            messagebox.showwarning("Qs-LSV & TOF", str(e), parent=self.w)
            return
        self.dang = True
        self.nut.config(state="disabled", text="Đang tính...")
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        threading.Thread(target=self.nen, args=(lenhs,), daemon=True).start()

    def nen(self, lenhs):
        ma = 0
        for ten, c in lenhs:
            self.q.put(f"=== {ten} ===\n")
            try:
                p = self.app.mo_tien_trinh(c, dict(os.environ, PYTHONIOENCODING="utf-8"))
                for dong in p.stdout:
                    self.q.put(dong)
                p.wait()
                ma = ma or p.returncode
            except Exception as e:
                self.q.put(f"[LỖI] {e}\n")
                ma = 1
            self.q.put("\n")
        self.q.put(("xong", ma))

    def doc_hang_doi(self):
        try:
            while True:
                v = self.q.get_nowait()
                if isinstance(v, tuple):
                    self.dang = False
                    self.nut.config(state="normal", text="▶  Tính Qs-LSV & vẽ TOF")
                    self.ghi("\n>>> HOÀN THÀNH\n" if v[1] == 0 else "\n>>> CÓ LỖI (xem các dòng ở trên)\n")
                    if v[1] == 0 and os.path.isfile(os.path.join(self.ra.get(), "TOF_QsLSV.png")):
                        self.xem_hinh()
                else:
                    self.ghi(v)
        except queue.Empty:
            pass
        try:
            if self.w.winfo_exists():
                self.w.after(150, self.doc_hang_doi)
        except tk.TclError:
            pass

    def xem_hinh(self):
        p = os.path.join(self.ra.get(), "TOF_QsLSV.png")
        if not os.path.isfile(p):
            messagebox.showinfo("Qs-LSV & TOF", "Chưa có hình. Bấm 'Tính Qs-LSV & vẽ TOF' trước.", parent=self.w)
            return
        w = tk.Toplevel(self.w)
        w.title("TOF_QsLSV.png")
        try:
            img = tk.PhotoImage(file=p)
            k = max(-(-img.width() // 1100), -(-img.height() // 520), 1)
            img = img.subsample(k, k)
            lb = ttk.Label(w, image=img)
            lb.image = img
            lb.pack(padx=6, pady=6)
        except Exception as e:
            ttk.Label(w, text=f"Không hiển thị được hình: {e}").pack(padx=10, pady=10)
        ttk.Button(w, text="Mở thư mục kết quả", command=lambda: self.app.mo_duong_dan(self.ra.get())).pack(pady=4)


class HopThoaiSoanHinh:
    """Soạn các hình bài báo: mỗi hình gồm danh sách ô theo thứ tự (A)(B)(C)...; đặt tên mẫu riêng cho hình."""

    def __init__(self, app):
        self.app = app
        self.hinh = app.ds_hinh() or [[]]
        self.cur = 0
        self.nhan = [m.get("nhan_hinh", "") or "" for m in app.muc]
        w = self.w = tk.Toplevel(app.root)
        w.title("Soạn hình & tên mẫu cho bài báo")
        w.geometry("1000x580")
        w.transient(app.root)
        w.columnconfigure(1, weight=1)
        w.rowconfigure(0, weight=1)
        ttk.Label(w, foreground="#555", justify="left", wraplength=860, text=(
            "Mỗi 'hình' là một file Hinh_bai_bao_N. Trong mỗi hình, thứ tự ô từ trên xuống = (A), (B), (C)... "
            "Một loại ô có thể xuất hiện nhiều lần. Để trống mọi hình = app tự chọn ô theo dữ liệu.")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 0))
        w.rowconfigure(1, weight=1)
        a = ttk.LabelFrame(w, text="Các hình")
        a.grid(row=1, column=0, sticky="ns", padx=(10, 4), pady=6)
        self.lb_hinh = tk.Listbox(a, width=14, height=10, exportselection=False)
        self.lb_hinh.pack(padx=6, pady=6)
        self.lb_hinh.bind("<<ListboxSelect>>", self.chon_hinh)
        ttk.Button(a, text="Thêm hình", command=self.them_hinh).pack(fill="x", padx=6)
        ttk.Button(a, text="Xóa hình", command=self.xoa_hinh).pack(fill="x", padx=6, pady=3)
        b = ttk.LabelFrame(w, text="Các ô của hình đang chọn (thứ tự = A, B, C...)")
        b.grid(row=1, column=1, sticky="nsew", padx=4, pady=6)
        b.columnconfigure(0, weight=1)
        b.rowconfigure(0, weight=1)
        self.lb_o = tk.Listbox(b, height=10, exportselection=False)
        self.lb_o.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        nut = ttk.Frame(b)
        nut.grid(row=0, column=1, sticky="n", pady=6, padx=(0, 6))
        ttk.Button(nut, text="▲", width=4, command=lambda: self.doi_cho(-1)).pack(pady=1)
        ttk.Button(nut, text="▼", width=4, command=lambda: self.doi_cho(1)).pack(pady=1)
        ttk.Button(nut, text="Xóa ô", command=self.xoa_o).pack(pady=(8, 1))
        them = ttk.Frame(b)
        them.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
        ttk.Label(them, text="Thêm ô:").grid(row=0, column=0, rowspan=3, sticky="n", padx=(0, 4))
        for k, (ma, ten) in enumerate(LOAI_O_HINH):
            ttk.Button(them, text=ten, command=lambda m=ma: self.them_o(m)).grid(row=k // 2, column=1 + k % 2, sticky="ew", padx=2, pady=1)
        c = ttk.LabelFrame(w, text="Tên mẫu trong hình (nhấp đúp để sửa; trống = dùng nhãn ở bảng file)")
        c.grid(row=1, column=2, sticky="nsew", padx=(4, 10), pady=6)
        self.tv = ttk.Treeview(c, columns=("goc", "moi"), show="headings", height=12, selectmode="browse")
        self.tv.heading("goc", text="Nhãn trong bảng")
        self.tv.heading("moi", text="Tên trong hình")
        self.tv.column("goc", width=130)
        self.tv.column("moi", width=160)
        self.tv.pack(fill="both", expand=True, padx=6, pady=6)
        self.tv.bind("<Double-1>", self.sua_ten)
        d = ttk.Frame(w)
        d.grid(row=2, column=0, columnspan=3, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(d, text="Áp dụng", command=self.ap_dung).pack(side="left", padx=4)
        ttk.Button(d, text="Hủy", command=w.destroy).pack(side="left", padx=4)
        self.ve()

    def ve(self):
        self.lb_hinh.delete(0, "end")
        for k in range(len(self.hinh)):
            self.lb_hinh.insert("end", f"Hình {k + 1}")
        self.cur = min(self.cur, len(self.hinh) - 1)
        self.lb_hinh.selection_set(self.cur)
        self.ve_o()
        self.tv.delete(*self.tv.get_children())
        for k, m in enumerate(self.app.muc):
            self.tv.insert("", "end", iid=str(k), values=(m["nhan"], self.nhan[k]))

    def ve_o(self, chon=None):
        thuong = self.app.hinh_chu.get().startswith("(a")
        chu = "abcdefghijklmnopqrstuvwxyz" if thuong else "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ten = dict(LOAI_O_HINH)
        self.lb_o.delete(0, "end")
        for k, o in enumerate(self.hinh[self.cur]):
            self.lb_o.insert("end", f"({chu[k % 26]})  {ten.get(o, o)}")
        if chon is not None and 0 <= chon < len(self.hinh[self.cur]):
            self.lb_o.selection_set(chon)

    def chon_hinh(self, _=None):
        s = self.lb_hinh.curselection()
        if s:
            self.cur = s[0]
            self.ve_o()

    def them_hinh(self):
        self.hinh.append([])
        self.cur = len(self.hinh) - 1
        self.ve()

    def xoa_hinh(self):
        if len(self.hinh) > 1:
            del self.hinh[self.cur]
        else:
            self.hinh[0] = []
        self.ve()

    def them_o(self, ma):
        self.hinh[self.cur].append(ma)
        self.ve_o(len(self.hinh[self.cur]) - 1)

    def xoa_o(self):
        s = self.lb_o.curselection()
        if s:
            del self.hinh[self.cur][s[0]]
            self.ve_o(min(s[0], len(self.hinh[self.cur]) - 1))

    def doi_cho(self, h):
        s = self.lb_o.curselection()
        if not s:
            return
        k, j = s[0], s[0] + h
        ds = self.hinh[self.cur]
        if 0 <= j < len(ds):
            ds[k], ds[j] = ds[j], ds[k]
            self.ve_o(j)

    def sua_ten(self, ev):
        iid = self.tv.identify_row(ev.y)
        if not iid:
            return
        k = int(iid)
        moi = simpledialog.askstring("Tên mẫu trong hình", f"Tên hiển thị cho '{self.app.muc[k]['nhan']}' trong hình bài báo\n"
                                     "(có thể dùng chỉ số dưới/trên kiểu mathtext, ví dụ Ni$_3$S$_2$; để trống = nhãn gốc):",
                                     initialvalue=self.nhan[k], parent=self.w)
        if moi is not None:
            self.nhan[k] = moi.strip()
            self.tv.set(iid, "moi", self.nhan[k])

    def ap_dung(self):
        self.app.hinh_o.set("|".join(",".join(h) for h in self.hinh if h))
        for m, t in zip(self.app.muc, self.nhan):
            m["nhan_hinh"] = t
        self.app.cap_nhat_tom_tat_hinh()
        self.w.destroy()


class HopThoaiQuet:
    """Danh sách file tìm thấy trong thư mục: tick chọn, xem loại tự nhận dạng, thêm vào bảng."""

    def __init__(self, app, goc, ket_qua):
        self.app, self.goc, self.kq = app, goc, ket_qua
        self.chon = {p: True for p, _ in ket_qua}
        w = self.w = tk.Toplevel(app.root)
        w.title("Quét thư mục")
        w.geometry("820x520")
        w.transient(app.root)
        dem = nd.tom_tat(ket_qua)
        tt = ", ".join(f"{v} {k}" for k, v in sorted(dem.items()))
        ttk.Label(w, text=f"Thư mục: {goc}\nTìm thấy {len(ket_qua)} file: {tt}", justify="left").pack(anchor="w", padx=10, pady=(10, 2))
        self.goi_y = ttk.Label(w, text="", foreground="#1a5e1a", justify="left", wraplength=780)
        self.goi_y.pack(anchor="w", padx=10)
        kh = ttk.Frame(w)
        kh.pack(fill="both", expand=True, padx=10, pady=6)
        self.tv = ttk.Treeview(kh, columns=("c", "loai", "file"), show="headings", selectmode="browse")
        for c, t, r in (("c", "Chọn", 50), ("loai", "Loại tự nhận dạng", 150), ("file", "File (đường dẫn trong thư mục)", 560)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=r, anchor="center" if c == "c" else "w")
        sb = ttk.Scrollbar(kh, command=self.tv.yview)
        self.tv.config(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<Button-1>", self.bam)
        self.ve()
        n1 = ttk.Frame(w)
        n1.pack(fill="x", padx=10)
        ttk.Button(n1, text="Chọn tất cả", command=lambda: self.dat_het(True)).pack(side="left", padx=2)
        ttk.Button(n1, text="Bỏ chọn tất cả", command=lambda: self.dat_het(False)).pack(side="left", padx=2)
        for loai in sorted(dem):
            ttk.Button(n1, text=f"Chỉ {loai}", command=lambda l=loai: self.chi_loai(l)).pack(side="left", padx=2)
        n2 = ttk.Frame(w)
        n2.pack(fill="x", padx=10, pady=10)
        self.chay_ngay = tk.BooleanVar(value=False)
        ttk.Checkbutton(n2, text="Chạy ngay sau khi thêm", variable=self.chay_ngay).pack(side="left")
        ttk.Button(n2, text="Đóng", command=w.destroy).pack(side="right", padx=2)
        ttk.Button(n2, text="Thêm, để app tự nhận dạng từng file", command=lambda: self.them(LOAI[0])).pack(side="right", padx=2)
        self.nut_ecsa = ttk.Button(n2, text="Thêm các CV → ECSA", command=self.them_ecsa)
        self.nut_ecsa.pack(side="right", padx=2)
        if dem.get("CV", 0) >= 3:
            self.goi_y.config(text=f"Gợi ý: có {dem['CV']} file CV - nếu là cùng một mẫu ở các tốc độ quét khác nhau, dùng 'Thêm các CV → ECSA' "
                                   "(sau đó mở 'Chọn E bằng đồ thị' ở tab Phân tích).")
        else:
            self.nut_ecsa.config(state="disabled")

    def ve(self):
        self.tv.delete(*self.tv.get_children())
        for k, (p, r) in enumerate(self.kq):
            self.tv.insert("", "end", iid=str(k), values=("☑" if self.chon[p] else "☐", r["mo_ta"], os.path.relpath(p, self.goc)))

    def bam(self, ev):
        if self.tv.identify_region(ev.x, ev.y) != "cell":
            return
        iid = self.tv.identify_row(ev.y)
        if iid and self.tv.identify_column(ev.x) == "#1":
            p = self.kq[int(iid)][0]
            self.chon[p] = not self.chon[p]
            self.tv.set(iid, "c", "☑" if self.chon[p] else "☐")

    def dat_het(self, v):
        for p in self.chon:
            self.chon[p] = v
        self.ve()

    def chi_loai(self, loai):
        for p, r in self.kq:
            self.chon[p] = r["loai"] == loai
        self.ve()

    def ds_chon(self, loai=None):
        return [p for p, r in self.kq if self.chon[p] and (loai is None or r["loai"] == loai)]

    def them(self, loai_dat):
        ds = self.ds_chon()
        if not ds:
            messagebox.showinfo("Quét thư mục", "Chưa tick file nào.", parent=self.w)
            return
        self.w.destroy()
        self.app.them_tu_quet(ds, loai_dat, self.chay_ngay.get())

    def them_ecsa(self):
        ds = self.ds_chon("CV")
        if len(ds) < 2:
            messagebox.showinfo("Quét thư mục", "Cần tick ít nhất 2 file CV.", parent=self.w)
            return
        self.w.destroy()
        self.app.them_tu_quet(ds, next(x for x in LOAI if x.startswith("ECSA")), False)
        self.app.mo_ecsa_tuong_tac()


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
        for k, mac in MAC_DINH.items():
            v = cd.get(k, mac)
            setattr(self, k, tk.BooleanVar(value=bool(v)) if isinstance(mac, bool) else tk.StringVar(value=str(v)))
        self.tom_tat_hinh = tk.StringVar(value="")
        self.nhan_truc_x = tk.StringVar(value="Trục X:")
        self.nhan_truc_y = tk.StringVar(value="Trục Y:")
        self.hd_cau_hoi = tk.StringVar(value="")
        self.dang_hd = False
        self.cau_hinh_chon = tk.StringVar(value=TEN_MAC_DINH_CAU_HINH)
        if self.tab_chon.get() not in TABS:
            self.tab_chon.set("")

        self.dung_giao_dien()
        self.cap_nhat_trang_thai()
        self.doc_hang_doi()
        if cn:
            self.root.after(1500, lambda: self.kiem_tra_cap_nhat(im_lang=True))

    # ====================== XÂY DỰNG GIAO DIỆN ======================
    def o_nhap(self, cha, nhan, bien, rong, goi_y, hang, cot, ghi_chu=None):
        """Nhãn + ô nhập trên lưới. Trả về ô nhập."""
        ttk.Label(cha, text=nhan).grid(row=hang, column=cot, sticky="e", padx=(6, 2), pady=2)
        e = ttk.Entry(cha, textvariable=bien, width=rong)
        e.grid(row=hang, column=cot + 1, sticky="w", padx=(0, 4), pady=2)
        if goi_y:
            GoiY(e, GOI_Y[goi_y])
        return e

    def nhom_ribbon(self, cha, tieu_de, hang=None):
        lf = ttk.LabelFrame(cha, text=f" {tieu_de} ")
        lf.pack(side="left", fill="y", padx=4, pady=3, anchor="n")
        return lf

    def tick(self, cha, nhan, bien, goi_y=None, **grid):
        c = ttk.Checkbutton(cha, text=nhan, variable=bien)
        c.grid(**grid)
        if goi_y:
            GoiY(c, GOI_Y[goi_y])
        return c

    def dung_giao_dien(self):
        pad = {"padx": 6, "pady": 3}
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
        main = ttk.Frame(self.canvas, padding=4)
        self.main = main
        self.cua_so_main = self.canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind("<Configure>", lambda e: self.cap_nhat_cuon())
        self.canvas.bind("<Configure>", lambda e: self.cap_nhat_cuon())

        # ================= THANH CÔNG CỤ (ribbon): bấm tên nhóm để mở/đóng =================
        self.tabbar = ttk.Frame(main)
        self.tabbar.pack(fill="x", padx=4, pady=(2, 0))
        ttk.Style().configure("Toolbutton", padding=(10, 4))
        for t in TABS:
            ttk.Radiobutton(self.tabbar, text=t, value=t, variable=self.tab_chon, style="Toolbutton",
                            command=lambda t=t: self.bam_tab(t)).pack(side="left", padx=1)
        # cấu hình (preset) nằm bên phải thanh công cụ
        ttk.Button(self.tabbar, text="Nạp từ file...", command=self.nap_tu_file).pack(side="right", padx=(2, 0))
        ttk.Button(self.tabbar, text="Xóa", width=4, command=self.xoa_cau_hinh).pack(side="right", padx=2)
        ttk.Button(self.tabbar, text="Lưu...", width=6, command=self.luu_cau_hinh).pack(side="right")
        self.cb_ch = ttk.Combobox(self.tabbar, textvariable=self.cau_hinh_chon, state="readonly", width=18)
        self.cb_ch.pack(side="right", padx=4)
        self.cb_ch.bind("<<ComboboxSelected>>", lambda e: self.nap_cau_hinh())
        GoiY(self.cb_ch, "Bộ thông số đã lưu (pH, Eref, diện tích, khoảng trục, cỡ chữ...). Chọn để áp dụng ngay.")
        ttk.Label(self.tabbar, text="Cấu hình:").pack(side="right")
        self.lam_moi_ds_cau_hinh()

        self.khung_tab = ttk.Frame(main, relief="groove", borderwidth=2, padding=2)
        self.nd_tab = {t: ttk.Frame(self.khung_tab) for t in TABS}
        self.dung_tab_du_lieu(self.nd_tab["Dữ liệu"])
        self.dung_tab_phan_tich(self.nd_tab["Phân tích"])
        self.dung_tab_hinh(self.nd_tab["Hình"])
        self.dung_tab_xuat(self.nd_tab["Xuất"])
        self.dung_tab_pho(self.nd_tab["Phổ"])
        self.dung_tab_hoi_dap(self.nd_tab["Hỏi đáp"])
        self.dung_tab_tro_giup(self.nd_tab["Trợ giúp"])

        # ================= BẢNG FILE =================
        self.f1 = ttk.LabelFrame(main, text=" File số liệu thô  (kéo-thả file vào bảng nếu máy có tkinterdnd2; bấm đúp để đổi nhãn / nhóm / màu) ")
        self.f1.pack(fill="x", **pad)
        f1 = self.f1
        cot = ("nhan", "nhom", "loai", "mau", "file")
        self.tv = ttk.Treeview(f1, columns=cot, show="headings", height=5, selectmode="browse")
        for c, t in (("nhan", "Nhãn chú thích"), ("nhom", "Nhóm lặp"), ("loai", "Loại phép đo"), ("mau", "Màu"), ("file", "File")):
            self.tv.heading(c, text=t)
        self.tv.column("nhan", width=150, anchor="w")
        self.tv.column("nhom", width=70, anchor="w")
        self.tv.column("loai", width=100, anchor="w")
        self.tv.column("mau", width=60, anchor="center")
        self.tv.column("file", width=290, anchor="w")
        self.tv.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(4, 2))
        sb = ttk.Scrollbar(f1, command=self.tv.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=(4, 2))
        self.tv.config(yscrollcommand=sb.set)
        self.tv.bind("<Double-1>", self.bam_dup)
        nut = ttk.Frame(f1)
        nut.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))
        for ten, lenh in [("Thêm file...", self.them_file), ("Thêm thư mục...", self.them_thu_muc), ("Quét thư mục & phân loại...", self.quet_thu_muc),
                          ("Đổi nhãn", self.doi_nhan), ("Đặt nhóm lặp", self.doi_nhom), ("Đổi màu", self.doi_mau),
                          ("▲", lambda: self.di_chuyen(-1)), ("▼", lambda: self.di_chuyen(1)),
                          ("Xóa mục chọn", self.xoa_chon), ("Xóa hết", self.xoa_het)]:
            ttk.Button(nut, text=ten, command=lenh, width=0).pack(side="left", padx=(0, 4))
        f1.columnconfigure(0, weight=1)
        self.bat_keo_tha()

        # ================= NÚT CHẠY =================
        fb = ttk.Frame(main)
        fb.pack(fill="x", **pad)
        self.nut_chay = ttk.Button(fb, text="▶  CHẠY XỬ LÝ & VẼ", command=self.bam_chay)
        self.nut_chay.pack(side="left", ipadx=20, ipady=5)
        self.nut_dung = ttk.Button(fb, text="Dừng", command=self.bam_dung, state="disabled")
        self.nut_dung.pack(side="left", padx=(6, 0), ipady=5)
        self.nut_xem = ttk.Button(fb, text="Xem trước hình", command=lambda: self.bam_chay(xem_truoc=True))
        self.nut_xem.pack(side="left", padx=(6, 0), ipady=5)
        GoiY(self.nut_xem, "Vẽ nhanh bằng Matplotlib và xem ngay trong app (không cần Origin, không ghi vào thư mục kết quả).")
        ttk.Button(fb, text="Mở thư mục kết quả", command=self.mo_thu_muc).pack(side="left", padx=(6, 0), ipady=5)
        ttk.Button(fb, text="Mở báo cáo Excel", command=self.mo_bao_cao).pack(side="left", padx=(6, 0), ipady=5)
        self.thanh = ttk.Progressbar(fb, mode="indeterminate", length=90)
        self.thanh.pack(side="left", padx=8)
        fz = ttk.Frame(fb)
        fz.pack(side="right")
        ttk.Label(fz, text="Thu phóng:").pack(side="left")
        ttk.Button(fz, text="−", width=3, command=lambda: self.doi_zoom(-10)).pack(side="left", padx=(4, 0))
        ttk.Label(fz, textvariable=self.nhan_zoom, width=5, anchor="center").pack(side="left")
        ttk.Button(fz, text="+", width=3, command=lambda: self.doi_zoom(10)).pack(side="left")
        ttk.Button(fz, text="100%", width=5, command=lambda: self.doi_zoom(dat=100)).pack(side="left", padx=(4, 0))

        fl = ttk.LabelFrame(main, text=" Báo cáo & Thông số tính toán ")
        fl.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(fl, height=9, state="disabled", font=self.font_log)
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
        self._tab_dang = None
        if self.tab_chon.get() in TABS:
            self.hien_tab(self.tab_chon.get(), cap_nhat_kich_thuoc=False)
        self.ap_dung_zoom()

    # ---------------------------- các tab của thanh công cụ ----------------------------
    def bam_tab(self, t):
        if t == self._tab_dang:          # bấm lại tab đang mở -> thu gọn
            self.tab_chon.set("")
            self.hien_tab(None)
        else:
            self.hien_tab(t)
        self.luu_cai_dat()

    def hien_tab(self, t, cap_nhat_kich_thuoc=True):
        for nd_ in self.nd_tab.values():
            nd_.pack_forget()
        self.khung_tab.pack_forget()
        self._tab_dang = t
        if t:
            self.nd_tab[t].pack(fill="x")
            self.khung_tab.pack(fill="x", padx=4, pady=2, after=self.tabbar)
        if cap_nhat_kich_thuoc:
            self.vua_man_hinh()

    def dung_tab_du_lieu(self, tab):
        g = self.nhom_ribbon(tab, "Phép đo")
        ttk.Label(g, text="Loại:").grid(row=0, column=0, sticky="e", padx=(6, 2), pady=2)
        cb = ttk.Combobox(g, textvariable=self.loai, values=LOAI, state="readonly", width=24)
        cb.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.cap_nhat_trang_thai())
        self.o_nhap(g, "Chu kỳ CV:", self.chu_ky, 5, "chu_ky", 1, 0)
        ttk.Label(g, text="(trống = chu kỳ cuối)", foreground="#666").grid(row=1, column=2, sticky="w")
        self.tick(g, "Vẽ chồng các file cùng loại", self.chong, "chong", row=2, column=0, columnspan=3, sticky="w", padx=6)
        g = self.nhom_ribbon(tab, "Quy đổi điện thế")
        ttk.Label(g, text="E → RHE = E + 0.0592 ×").grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=2)
        self.o_nhap(g, "pH", self.ph, 6, "ph", 1, 0)
        self.o_nhap(g, "+ Eref (V)", self.eref, 6, "eref", 2, 0)
        self.tick(g, "Không quy đổi RHE (điện thế tế bào)", self.khong_rhe, "khong_rhe", row=3, column=0, columnspan=2, sticky="w", padx=6)
        g = self.nhom_ribbon(tab, "Quy đổi dòng")
        ttk.Label(g, text="I (mA/cm²) = i × 1000 ×").grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=2)
        self.o_nhap(g, "nhân", self.nhan_i, 6, "nhan_i", 1, 0)
        self.o_nhap(g, "÷ chia (diện tích)", self.chia_i, 6, "chia_i", 2, 0)
        g = self.nhom_ribbon(tab, "Bù iR")
        self.o_nhap(g, "Rs (Ω)", self.r_s, 7, "r_s", 0, 0)
        self.o_nhap(g, "bù (%)", self.ir_pct, 5, "ir_pct", 1, 0)
        ttk.Button(g, text="Lấy Rs từ file EIS...", command=self.lay_rs_tu_eis).grid(row=2, column=0, columnspan=2, padx=6, pady=3, sticky="w")

    def dung_tab_phan_tich(self, tab):
        h1 = ttk.Frame(tab)
        h1.pack(fill="x")
        h2 = ttk.Frame(tab)
        h2.pack(fill="x")
        g = self.nhom_ribbon(h1, "Tafel")
        ttk.Radiobutton(g, text="Theo dòng (mA/cm²)", value="dong", variable=self.tafel_che_do).grid(row=0, column=0, columnspan=4, sticky="w", padx=6)
        self.en_tf_min = self.o_nhap(g, "từ", self.tafel_min, 5, "tafel", 1, 0)
        self.en_tf_max = self.o_nhap(g, "đến", self.tafel_max, 5, "tafel", 1, 2)
        ttk.Radiobutton(g, text="Theo điện thế (V)", value="e", variable=self.tafel_che_do).grid(row=2, column=0, columnspan=4, sticky="w", padx=6)
        self.o_nhap(g, "từ", self.tafel_e_min, 5, "tafel_e", 3, 0)
        self.o_nhap(g, "đến", self.tafel_e_max, 5, "tafel_e", 3, 2)
        g = self.nhom_ribbon(h1, "ECSA (loại = ECSA)")
        self.en_e_ecsa = self.o_nhap(g, "E lấy dòng (V)", self.e_ecsa, 6, "e_ecsa", 0, 0)
        self.en_cs = self.o_nhap(g, "Cs (mF/cm²)", self.cs, 6, "cs", 1, 0)
        ttk.Button(g, text="Chọn E bằng đồ thị...", command=self.mo_ecsa_tuong_tac).grid(row=2, column=0, columnspan=2, padx=6, pady=3, sticky="w")
        g = self.nhom_ribbon(h1, "So sánh mẫu")
        self.tick(g, "Bảng xếp hạng + biểu đồ cột", self.so_sanh, "so_sanh", row=0, column=0, columnspan=4, sticky="w", padx=6)
        self.tick(g, "Không tính quá thế (xếp theo E)", self.khong_qua_the, "khong_qua_the", row=1, column=0, columnspan=4, sticky="w", padx=6)
        self.o_nhap(g, "I mục tiêu (mA/cm²)", self.i_muc_tieu, 8, "i_muc_tieu", 2, 0)
        self.o_nhap(g, "E cân bằng (V)", self.e_can_bang, 6, "e_can_bang", 3, 0)
        g = self.nhom_ribbon(h1, "Lặp lại & tài liệu")
        ttk.Label(g, text="Nhóm lặp: đặt ở cột 'Nhóm lặp' trong bảng file\n(→ trung bình ± SD)", foreground="#666", justify="left").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=6, pady=2)
        ttk.Label(g, text="Bảng tài liệu (CSV):").grid(row=1, column=0, sticky="w", padx=6)
        e = ttk.Entry(g, textvariable=self.tai_lieu, width=22)
        e.grid(row=2, column=0, sticky="w", padx=6)
        GoiY(e, GOI_Y["tai_lieu"])
        ttk.Button(g, text="Chọn...", width=7, command=self.chon_tai_lieu).grid(row=2, column=1, padx=2)
        ttk.Button(g, text="Tạo file mẫu", command=self.tao_mau_tai_lieu).grid(row=2, column=2, padx=2)
        g = self.nhom_ribbon(h2, "Hoạt độ khối & TOF")
        self.o_nhap(g, "Tải trọng (mg/cm²)", self.tai_trong, 7, "tai_trong", 0, 0)
        self.o_nhap(g, "Quá thế khảo sát (mV)", self.qua_the_ht, 9, "qua_the_ht", 0, 2)
        self.o_nhap(g, "Tâm hoạt động (µmol/cm²)", self.so_mol_tam, 7, "so_mol_tam", 1, 0)
        self.o_nhap(g, "n e⁻ / phân tử", self.n_e, 4, "n_e", 1, 2)
        self.o_nhap(g, "hoặc M (g/mol)", self.khoi_luong_mol, 7, "khoi_luong_mol", 2, 0)
        self.o_nhap(g, "tỉ lệ tâm (0–1)", self.ti_le_tam, 5, "ti_le_tam", 2, 2)
        g = self.nhom_ribbon(h2, "Qs-LSV & TOF")
        ttk.Label(g, text="Công cụ riêng: CV → N (từ Q),\nthư mục Qs-LSV → I; vẽ CV và TOF theo E", foreground="#555", justify="left").grid(
            row=0, column=0, padx=6, pady=2, sticky="w")
        ttk.Button(g, text="Mở công cụ Qs-LSV & TOF...", command=self.mo_cong_cu_qs).grid(row=1, column=0, padx=6, pady=4, sticky="w")
        g = self.nhom_ribbon(h2, "Hiệu suất Faraday (file IT)")
        self.o_nhap(g, "V khí (mL, mỗi mẫu IT)", self.fe_v_h2, 10, "fe_v_h2", 0, 0)
        self.o_nhap(g, "n e⁻", self.fe_n, 4, "fe_n", 0, 2)
        self.o_nhap(g, "T (°C)", self.fe_nhiet_do, 6, "fe_nhiet_do", 1, 0)
        self.o_nhap(g, "P (kPa)", self.fe_ap_suat, 8, "fe_ap_suat", 1, 2)
        self.tick(g, "Trừ áp suất hơi nước", self.fe_hoi_nuoc, "fe_hoi_nuoc", row=2, column=0, columnspan=4, sticky="w", padx=6)
        g = self.nhom_ribbon(h2, "EIS")
        self.tick(g, "Fit mạch Rs + (Rct ‖ CPE)", self.fit_eis, "fit_eis", row=0, column=0, sticky="w", padx=6, pady=4)

    def dung_tab_hinh(self, tab):
        h1 = ttk.Frame(tab)
        h1.pack(fill="x")
        h2 = ttk.Frame(tab)
        h2.pack(fill="x")
        g = self.nhom_ribbon(h1, "Origin")
        self.tick(g, "Vẽ bằng Origin", self.dung_origin, row=0, column=0, columnspan=4, sticky="w", padx=6)
        self.o_nhap(g, "Dày nét", self.day_net, 4, "day_net", 1, 0)
        self.o_nhap(g, "Tỉ lệ R:C", self.ti_le, 5, "ti_le", 1, 2)
        self.o_nhap(g, "Dày khung", self.day_khung, 4, "day_khung", 2, 0)
        self.o_nhap(g, "Đệm trục (bước)", self.le_max, 4, "le_max", 2, 2)
        g = self.nhom_ribbon(h1, "Cỡ chữ (pt) & vạch chia")
        self.o_nhap(g, "Số trên trục", self.co_chu, 5, "co_chu", 0, 0)
        self.o_nhap(g, "Tiêu đề trục", self.co_chu_td, 5, "co_chu_td", 0, 2)
        self.o_nhap(g, "Chú thích", self.co_chu_ct, 5, "co_chu_ct", 0, 4)
        self.o_nhap(g, "Vạch chính: dài", self.vc_dai, 5, "vc_dai", 1, 0)
        self.o_nhap(g, "dày", self.vc_day, 5, None, 1, 2)
        self.o_nhap(g, "Vạch phụ: số", self.vp_so, 5, "vp_so", 2, 0)
        self.o_nhap(g, "dài", self.vp_dai, 5, None, 2, 2)
        self.o_nhap(g, "dày", self.vp_day, 5, None, 2, 4)
        g = self.nhom_ribbon(h2, "Khoảng trục Origin (trống = tự động)")
        for r, (nh, cac) in enumerate([(self.nhan_truc_x, ("x_min", "x_max", "x_buoc")), (self.nhan_truc_y, ("y_min", "y_max", "y_buoc"))]):
            ttk.Label(g, textvariable=nh, width=24, anchor="w").grid(row=r, column=0, padx=6, pady=2, sticky="w")
            for c, (ten, nhan) in enumerate(zip(cac, ("Từ", "Đến", "Bước"))):
                self.o_nhap(g, nhan, getattr(self, ten), 6, "khoang", r, 1 + c * 2)
        ttk.Button(g, text="Xóa (tự động)", command=self.xoa_khoang).grid(row=0, column=7, rowspan=2, padx=8)
        g = self.nhom_ribbon(h2, "Hình ghép chuẩn bài báo")
        self.tick(g, "Xuất hình nhiều ô (A)(B)(C)...", self.hinh_bai_bao, "hinh_bai_bao", row=0, column=0, columnspan=4, sticky="w", padx=6)
        ttk.Label(g, text="Khổ:").grid(row=1, column=0, sticky="e", padx=(6, 2))
        ttk.Combobox(g, textvariable=self.hinh_cot, values=KHO_HINH, state="readonly", width=16).grid(row=1, column=1, columnspan=2, sticky="w")
        self.o_nhap(g, "dpi", self.hinh_dpi, 5, None, 1, 3)
        for c, (nh, bien) in enumerate((("PNG", self.hb_png), ("PDF", self.hb_pdf), ("TIFF", self.hb_tiff))):
            ttk.Checkbutton(g, text=nh, variable=bien).grid(row=2, column=c, sticky="w", padx=6)
        ttk.Label(g, text="Chữ ô:").grid(row=3, column=0, sticky="e", padx=(6, 2))
        cb_chu = ttk.Combobox(g, textvariable=self.hinh_chu, values=["(A) (B) (C)", "(a) (b) (c)"], state="readonly", width=12)
        cb_chu.grid(row=3, column=1, columnspan=2, sticky="w")
        cb_chu.bind("<<ComboboxSelected>>", lambda e: self.cap_nhat_tom_tat_hinh())
        b = ttk.Button(g, text="Soạn hình & tên mẫu...", command=self.soan_hinh)
        b.grid(row=4, column=0, columnspan=3, sticky="w", padx=6, pady=3)
        GoiY(b, GOI_Y["hinh_o"])
        ttk.Label(g, textvariable=self.tom_tat_hinh, foreground="#555", wraplength=260, justify="left").grid(
            row=5, column=0, columnspan=4, sticky="w", padx=6)

    def dung_tab_xuat(self, tab):
        g = self.nhom_ribbon(tab, "Kết quả")
        ttk.Label(g, text="Thư mục kết quả:").grid(row=0, column=0, columnspan=3, sticky="w", padx=6)
        ttk.Entry(g, textvariable=self.thu_muc_ra, width=44).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(6, 0))
        ttk.Button(g, text="Chọn...", command=self.chon_thu_muc).grid(row=1, column=2, padx=6)
        self.tick(g, "Xuất CSV & ảnh Matplotlib (thư mục csv_va_anh_nhanh)", self.dung_csv, row=2, column=0, columnspan=3, sticky="w", padx=6)
        self.tick(g, "Xuất báo cáo Excel (bao_cao_tong_hop.xlsx)", self.xuat_excel, "xuat_excel", row=3, column=0, columnspan=3, sticky="w", padx=6)
        g2 = self.nhom_ribbon(tab, "Mở nhanh")
        for ten, lenh in (("Mở thư mục kết quả", self.mo_thu_muc), ("Mở báo cáo Excel", self.mo_bao_cao), ("Mở nhật ký", self.mo_nhat_ky)):
            ttk.Button(g2, text=ten, command=lenh).pack(fill="x", padx=6, pady=2)

    def dung_tab_pho(self, tab):
        g = self.nhom_ribbon(tab, "Phổ XRD / Raman / XPS (chọn Loại = Phổ ở tab Dữ liệu)")
        ttk.Label(g, text="Kiểu phổ:").grid(row=0, column=0, sticky="e", padx=(6, 2), pady=2)
        ttk.Combobox(g, textvariable=self.pho_kieu, values=KIEU_PHO, state="readonly", width=10).grid(row=0, column=1, sticky="w")
        self.o_nhap(g, "Khoảng đổi", self.pho_doi, 5, "pho_doi", 0, 2)
        self.o_nhap(g, "Số đỉnh đánh dấu", self.pho_dinh, 4, "pho_dinh", 0, 4)
        self.o_nhap(g, "x từ", self.pho_x_min, 7, None, 1, 0)
        self.o_nhap(g, "đến", self.pho_x_max, 7, None, 1, 2)
        self.tick(g, "Chuẩn hóa 0–1", self.pho_chuan_hoa, row=1, column=4, columnspan=2, sticky="w", padx=6)
        ttk.Label(g, foreground="#666", text="File 2 cột (x, y). Chỉ xuất ảnh Matplotlib (PNG/PDF) + CSV; chưa tách đỉnh XPS.").grid(
            row=2, column=0, columnspan=6, sticky="w", padx=6, pady=(2, 4))

    def dung_tab_hoi_dap(self, tab):
        g = ttk.LabelFrame(tab, text=" Hỏi đáp về dữ liệu (tiếng Việt, không cần AI / Internet) ")
        g.pack(fill="x", padx=4, pady=3)
        self.f5 = g
        self.en_hd = ttk.Entry(g, textvariable=self.hd_cau_hoi, width=60)
        self.en_hd.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=6)
        self.en_hd.bind("<Return>", lambda e: self.hoi_dap())
        self.nut_hd = ttk.Button(g, text="Hỏi", command=self.hoi_dap)
        self.nut_hd.grid(row=0, column=1, padx=4, ipadx=14)
        ttk.Button(g, text="Gợi ý câu hỏi", command=self.goi_y_hoi_dap).grid(row=0, column=2, padx=(0, 8))
        ttk.Label(g, foreground="#666",
                  text="VD: điện thế tại 10 mA của các mẫu · quá thế tại 10 mA · dòng tại 1.6 V · tafel · ecsa · so sánh các mẫu · liệt kê các file").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))
        g.columnconfigure(0, weight=1)

    def dung_tab_tro_giup(self, tab):
        g = self.nhom_ribbon(tab, "Trợ giúp")
        for ten, lenh in (("Hướng dẫn", self.mo_huong_dan), ("Dữ liệu mẫu", self.mo_du_lieu_mau), ("Giới thiệu", self.mo_gioi_thieu)):
            ttk.Button(g, text=ten, command=lenh).pack(side="left", padx=4, pady=4)
        g = self.nhom_ribbon(tab, "Bảo trì")
        for ten, lenh in (("Mở nhật ký", self.mo_nhat_ky), ("Kiểm tra cập nhật", lambda: self.kiem_tra_cap_nhat(False))):
            ttk.Button(g, text=ten, command=lenh).pack(side="left", padx=4, pady=4)

    def chon_tai_lieu(self):
        p = filedialog.askopenfilename(title="Chọn file CSV các nghiên cứu để so sánh", filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if p:
            self.tai_lieu.set(p)

    def tao_mau_tai_lieu(self):
        p = filedialog.asksaveasfilename(title="Lưu file CSV mẫu", defaultextension=".csv", initialfile="bang_tai_lieu.csv",
                                         filetypes=[("CSV", "*.csv")])
        if not p:
            return
        try:
            import so_sanh
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                f.write(so_sanh.MAU_TAI_LIEU)
        except Exception as e:
            messagebox.showerror("Bảng tài liệu", f"Không tạo được file: {e}")
            return
        self.tai_lieu.set(p)
        self.q.put(f"Đã tạo file mẫu {p}. Mở bằng Excel, thay dòng ví dụ bằng các nghiên cứu cần so sánh rồi lưu (giữ định dạng CSV).\n")

    # ====================== THU PHÓNG ======================
    def khoi_tao_zoom(self):
        self.font_goc = {}
        for ten in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                    "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
            try:
                self.font_goc[ten] = tkfont.nametofont(ten).cget("size")
            except Exception:
                pass
        self.font_log = tkfont.Font(family="Consolas", size=9)
        self.cot_goc = {"nhan": 150, "nhom": 70, "loai": 100, "mau": 60, "file": 290}
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
                            loai if loai in ("LSV", "CV", "IT", "EIS") else None,
                            r_s=self.so_khong_am(self.r_s, "Rs"), ir_pct=self.so(self.ir_pct, "% bù iR", duong=True),
                            khong_rhe=self.khong_rhe.get())
            for ten, bien in (("tai_trong", self.tai_trong), ("so_mol_tam", self.so_mol_tam),
                              ("khoi_luong_mol", self.khoi_luong_mol), ("ti_le_tam", self.ti_le_tam),
                              ("qua_the_ht", self.qua_the_ht), ("n_e", self.n_e), ("i_muc_tieu", self.i_muc_tieu),
                              ("e_can_bang", self.e_can_bang)):
                setattr(nc.a, ten, bien.get().strip() or None)
            nc.a.e_can_bang = self.so(self.e_can_bang, "E cân bằng")
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
        self.en_e_ecsa.config(state="normal" if ecsa else "disabled")
        self.en_cs.config(state="normal" if ecsa else "disabled")
        self.cap_nhat_tom_tat_hinh()

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
            self.tv.insert("", "end", iid=str(k), values=(m["nhan"], m.get("nhom", ""), m.get("loai_nhan", "?") + ("  [bỏ khỏi ECSA]" if m.get("ecsa_bo") else ""), m["mau"], m["path"]), tags=(tag,))
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
                             "mau": BANG_MAU[k % len(BANG_MAU)], "loai_nhan": self.nhan_dang(p), "nhom": ""})
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

    MODULE_CAN = ("xu_ly_dien_hoa", "ve_origin", "so_sanh", "cong_cu", "hoi_dap", "canh_bao", "bao_cao", "hieu_suat", "fit_eis", "hinh_bai_bao",
                  "pho_xy", "ecsa_tuong_tac", "tof_cv", "qs_lsv", "nhan_dang_nhanh", "loi_than_thien", "mau_du_lieu", "tu_dong_cap_nhat")

    def kiem_file_ma_nguon(self):
        """Báo rõ nếu thư mục ma_nguon thiếu file .py (thường do build cũ / cập nhật dở)."""
        thieu = [m for m in self.MODULE_CAN if not os.path.isfile(os.path.join(THU_MUC, m + ".py"))]
        if thieu:
            self.q.put("[CẢNH BÁO] Thiếu file trong thư mục chương trình: " + ", ".join(m + ".py" for m in thieu) +
                       ".\nMột số chức năng (vd TOF, Qs-LSV, ECSA tương tác) sẽ báo lỗi 'No module named ...'. "
                       "Cách sửa: bấm 'Kiểm tra cập nhật' hoặc chép các file này vào thư mục ma_nguon.\n")

    def mo_cong_cu_qs(self):
        CongCuQsTof(self)

    # ====================== SOẠN HÌNH BÀI BÁO ======================
    def ds_hinh(self):
        """hinh_o dạng 'lsv,tafel|eis,it' -> [['lsv','tafel'], ['eis','it']]"""
        kq = []
        for h in self.hinh_o.get().replace(";", ",").split("|"):
            ds = [x.strip().lower() for x in h.split(",") if x.strip()]
            if ds:
                kq.append(ds)
        return kq

    def cap_nhat_tom_tat_hinh(self):
        hs = self.ds_hinh()
        if not hs:
            self.tom_tat_hinh.set("Tự chọn ô theo dữ liệu.")
            return
        thuong = self.hinh_chu.get().startswith("(a")
        chu = "abcdefghijklmnopqrstuvwxyz" if thuong else "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.tom_tat_hinh.set("  |  ".join(f"Hình {i + 1}: " + " ".join(f"({chu[k % 26]}){o}" for k, o in enumerate(h)) for i, h in enumerate(hs)))

    def soan_hinh(self):
        HopThoaiSoanHinh(self)

    # ====================== ECSA TƯƠNG TÁC ======================
    def mo_ecsa_tuong_tac(self):
        if et is None:
            messagebox.showerror("ECSA", "Thiếu module ecsa_tuong_tac.py (hãy cập nhật app).")
            return
        loai_ecsa = next(x for x in LOAI if x.startswith("ECSA"))
        cu = self.loai.get()
        self.loai.set(loai_ecsa)
        try:
            lenh = self.lam_lenh(xem_truoc=True)
        except ValueError as e:
            self.loai.set(cu)
            messagebox.showwarning("ECSA", str(e))
            return
        self.cap_nhat_trang_thai()
        c = [x for x in lenh[0][1]]
        tmp = os.path.join(THU_MUC_XEM_TRUOC, "cv_ecsa.json")
        os.makedirs(THU_MUC_XEM_TRUOC, exist_ok=True)
        try:
            os.remove(tmp)
        except OSError:
            pass
        c += ["--xuat-cv-json", tmp]
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            p = self.mo_tien_trinh(c, dict(os.environ, PYTHONIOENCODING="utf-8"))
            try:
                out, _ = p.communicate(timeout=300)
            except subprocess.TimeoutExpired:
                p.kill()
                out = "Quá thời gian chờ."
        except Exception as e:
            out = str(e)
        finally:
            self.root.config(cursor="")
        if not os.path.isfile(tmp):
            messagebox.showerror("ECSA", "Không đọc được dữ liệu CV:\n" + (out or "")[-800:])
            return
        with open(tmp, "r", encoding="utf-8") as f:
            cv = json.load(f)["cv"]
        try:
            e0 = float(self.e_ecsa.get().replace(",", ".")) if self.e_ecsa.get().strip() else None
            cs = self.so(self.cs, "Cs", duong=True)
            bo = {os.path.abspath(m["path"]) for m in self.muc if m.get("ecsa_bo")}
            et.CuaSo(self.root, cv, e0, cs, bo, self.ap_dung_ecsa)
        except ValueError as e:
            messagebox.showwarning("ECSA", str(e))

    def ap_dung_ecsa(self, e, bo_qua):
        self.e_ecsa.set(f"{e:.4f}")
        for m in self.muc:
            m["ecsa_bo"] = os.path.abspath(m["path"]) in bo_qua
        self.lam_moi_bang()
        n = len(bo_qua)
        self.q.put(f"ECSA: lấy dòng tại E = {e:.4f} V" + (f"; bỏ {n} tốc độ quét khỏi phép fit." if n else ".") + " Bấm CHẠY để xuất kết quả.\n")

    # ====================== QUÉT THƯ MỤC ======================
    def quet_thu_muc(self):
        if nd is None or not hasattr(nd, "quet_thu_muc"):
            messagebox.showerror("Quét thư mục", "Thiếu module nhan_dang_nhanh (hãy cập nhật app).")
            return
        p = filedialog.askdirectory(title="Chọn thư mục chứa dữ liệu (quét cả thư mục con)")
        if not p:
            return
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            kq = nd.quet_thu_muc(p)
        finally:
            self.root.config(cursor="")
        if not kq:
            messagebox.showinfo("Quét thư mục", "Không tìm thấy file .txt/.csv/.dat nào.")
            return
        HopThoaiQuet(self, p, kq)

    def them_tu_quet(self, ds, loai_dat=None, chay=False):
        n = self.them_cac_file(ds)
        if loai_dat:
            self.loai.set(loai_dat)
            self.cap_nhat_trang_thai()
        self.q.put(f"Đã thêm {n} file từ thư mục." + (f" Loại phép đo: {loai_dat}." if loai_dat else "") + "\n")
        if chay:
            self.bam_chay()

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

    def doi_nhom(self):
        k = self.chi_so_chon()
        if k is None:
            messagebox.showinfo("Nhóm lặp", "Hãy chọn một file trong bảng trước.")
            return
        moi = simpledialog.askstring("Nhóm lặp", "Tên nhóm (các file cùng tên nhóm được lấy trung bình ± SD).\nĐể trống = không thuộc nhóm nào:",
                                     initialvalue=self.muc[k].get("nhom", ""), parent=self.root)
        if moi is not None:
            self.muc[k]["nhom"] = moi.strip()
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
        if cot == "#4":
            self.doi_mau()
        elif cot == "#5":
            return
        elif cot == "#2":
            self.doi_nhom()
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
        self.cap_nhat_trang_thai()
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
                        m["nhom"] = x.get("nhom", "")
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

    def so_khong_am(self, bien, ten):
        if not bien.get().strip():
            return 0.0
        v = self.so(bien, ten)
        if v < 0:
            raise ValueError(f"'{ten}' không được âm.")
        return v

    def so_tuy_chon(self, bien, ten, duong=True):
        if not bien.get().strip():
            return None
        return self.so(bien, ten, duong=duong)

    def lay_rs_tu_eis(self):
        k = self.chi_so_chon()
        p = None
        if k is not None and str(self.muc[k].get("loai_nhan", "")).startswith("EIS"):
            p = self.muc[k]["path"]
        if p is None:
            p = filedialog.askopenfilename(title="Chọn file EIS để lấy Rs", filetypes=[("Dữ liệu", "*.txt *.csv *.dat"), ("Tất cả", "*.*")])
        if not p:
            return
        try:
            import xu_ly_dien_hoa as xl
            rs = xl.rs_tu_eis(p)
        except Exception as e:
            messagebox.showerror("Rs từ EIS", f"Không lấy được Rs từ file này:\n{e}")
            return
        self.r_s.set(f"{rs:.4g}")
        self.q.put(f"Rs ≈ {rs:.4g} Ω (Z' gần trục thực nhất ở vùng tần số cao của {os.path.basename(p)}). "
                   "Đây là ước lượng; có thể chỉnh lại ô Rs.\n")

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

        pho = loai.startswith("Phổ")
        tafel_min = self.so(self.tafel_min, "Tafel: dòng từ")
        tafel_max = self.so(self.tafel_max, "Tafel: dòng đến")
        chung += ["--tafel-min", str(tafel_min), "--tafel-max", str(tafel_max)]
        if self.tafel_che_do.get() == "e":
            e1 = self.so(self.tafel_e_min, "Tafel: điện thế từ")
            e2 = self.so(self.tafel_e_max, "Tafel: điện thế đến")
            if e1 >= e2:
                raise ValueError("Tafel theo điện thế: 'từ' phải nhỏ hơn 'đến'.")
            chung += ["--tafel-e-min", str(e1), "--tafel-e-max", str(e2)]
        if self.khong_rhe.get():
            chung.append("--khong-rhe")
        if self.khong_qua_the.get():
            chung.append("--khong-qua-the")

        if pho:
            chung += ["--loai", "PHO", "--pho-kieu", self.pho_kieu.get() or "xrd",
                      "--pho-doi", str(self.so(self.pho_doi, "Khoảng đổi", duong=True)),
                      "--pho-dinh", str(int(self.so(self.pho_dinh, "Số đỉnh", int))) if self.pho_dinh.get().strip() else "0"]
            if not self.pho_chuan_hoa.get():
                chung.append("--pho-khong-chuan-hoa")
            for bien, co, ten in ((self.pho_x_min, "--pho-x-min", "x từ"), (self.pho_x_max, "--pho-x-max", "x đến")):
                v = self.so_tuy_chon(bien, ten, duong=False)
                if v is not None:
                    chung += [co, str(v)]
        elif ecsa:
            giu = [m for m in self.muc if not m.get("ecsa_bo")]
            if len(giu) < 2:
                raise ValueError("ECSA cần ít nhất 2 file CV (chưa bị bỏ tick khỏi ECSA).")
            cs = self.so(self.cs, "Cs", duong=True)
            chung += ["--ecsa", "--cs", str(cs)]
            for m in self.muc:
                if m.get("ecsa_bo"):
                    chung += ["--ecsa-bo-qua", os.path.abspath(m["path"])]
            if self.e_ecsa.get().strip():
                chung += ["--e-ecsa", str(self.so(self.e_ecsa, "E lấy dòng"))]
        elif tafel:
            chung += ["--loai", "TAFEL"]
        elif loai in ("LSV", "CV", "IT", "EIS"):
            chung += ["--loai", loai]

        r_s = self.so_khong_am(self.r_s, "Rs")
        if r_s > 0:
            pt = self.so(self.ir_pct, "% bù iR", duong=True)
            if pt > 100:
                raise ValueError("'% bù iR' không được lớn hơn 100.")
            chung += ["--r-s", str(r_s), "--ir-phan-tram", str(pt)]
        for bien, co, ten in ((self.tai_trong, "--tai-trong", "Tải trọng"), (self.so_mol_tam, "--so-mol-tam", "Tâm hoạt động"),
                              (self.khoi_luong_mol, "--khoi-luong-mol", "M (g/mol)")):
            v = self.so_tuy_chon(bien, ten)
            if v is not None:
                chung += [co, str(v)]
        tl = self.so_tuy_chon(self.ti_le_tam, "Tỉ lệ tâm")
        if tl is not None:
            if not 0 < tl <= 1:
                raise ValueError("'Tỉ lệ tâm' phải trong khoảng (0, 1].")
            chung += ["--ti-le-tam", str(tl)]
        ds_eta = [x.strip().replace(",", ".") for x in self.qua_the_ht.get().replace(";", ",").split(",") if x.strip()]
        try:
            for x in ds_eta:
                float(x)
        except ValueError:
            raise ValueError("'Quá thế khảo sát' phải là các số (mV) cách nhau dấu phẩy, ví dụ: 300 hoặc 250, 300.")
        if ds_eta:
            chung += ["--qua-the-ht", ",".join(ds_eta)]
        chung += ["--n-e", str(self.so(self.n_e, "n electron", duong=True))]
        if self.chong.get() and not ecsa:
            chung.append("--chong")

        # ---- các kết quả tổng hợp (chỉ thêm vào MỘT tiến trình để khỏi làm trùng) ----
        tong_hop = not xem_truoc and not ecsa and not pho
        xuat_bao_cao = self.xuat_excel.get() and not xem_truoc and not pho
        extra = []
        if tong_hop:
            if self.so_sanh.get():
                extra.append("--so-sanh")
                tl_path = self.tai_lieu.get().strip()
                if tl_path:
                    if not os.path.isfile(tl_path):
                        raise ValueError(f"Không tìm thấy file bảng tài liệu: {tl_path}")
                    extra += ["--tai-lieu", tl_path]
            if self.fit_eis.get():
                extra.append("--fit-eis")
            vfe = self.fe_v_h2.get().replace(";", ",").strip()
            if vfe:
                try:
                    for x in vfe.split(","):
                        if x.strip():
                            float(x.replace(",", "."))
                except ValueError:
                    raise ValueError("'V khí' phải là các số (mL) cách nhau dấu phẩy, ví dụ: 3.2, 4.0.")
                extra += ["--fe-v-h2", ",".join(x.strip() for x in vfe.split(",") if x.strip()),
                          "--fe-nhiet-do", str(self.so(self.fe_nhiet_do, "Nhiệt độ", duong=False)),
                          "--fe-ap-suat", str(self.so(self.fe_ap_suat, "Áp suất", duong=True)),
                          "--fe-n", str(self.so(self.fe_n, "n electron (FE)", duong=True))]
                if not self.fe_hoi_nuoc.get():
                    extra.append("--fe-khong-hoi-nuoc")
            if self.hinh_bai_bao.get():
                dang = [n for n, b in (("png", self.hb_png), ("pdf", self.hb_pdf), ("tiff", self.hb_tiff)) if b.get()]
                if not dang:
                    raise ValueError("Hình bài báo: hãy tick ít nhất một định dạng (PNG / PDF / TIFF).")
                extra += ["--hinh-bai-bao", "--hinh-cot", "1" if self.hinh_cot.get().startswith("Cột đơn") else "2",
                          "--hinh-dang", ",".join(dang), "--hinh-dpi", str(int(self.so(self.hinh_dpi, "dpi", int, duong=True)))]
                for hinh in self.ds_hinh():
                    extra += ["--hinh-o", ",".join(hinh)]
                if self.hinh_chu.get().startswith("(a"):
                    extra += ["--hinh-chu", "thuong"]
                if any(m.get("nhan_hinh") for m in self.muc):
                    for m in self.muc:
                        extra += ["--nhan-hinh", m.get("nhan_hinh", "") or ""]
        co_tong_hop = bool(extra) or xuat_bao_cao
        if co_tong_hop:
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
            nhan_mau += ["--nhan", m["nhan"], "--mau-file", m["mau"], "--nhom", m.get("nhom", "") or ""]

        lenh = []
        da_bao_cao = False

        def them_bao_cao():
            nonlocal da_bao_cao
            kq = []
            if not da_bao_cao and co_tong_hop:
                da_bao_cao = True
                kq += ["--thu-muc-tong-hop", thu_muc]
                if xuat_bao_cao:
                    kq += ["--bao-cao", thu_muc]
                kq += extra
                kq += ["--i-muc-tieu", ",".join(x.replace(",", ".") for x in mt), "--e-can-bang", str(e_cb)]
            return kq

        if self.dung_origin.get() and not xem_truoc and not pho:
            c = self.lenh_con("ve_origin.py", "--worker-origin") + files + chung + nhan_mau
            c += ["--thu-muc-ra", thu_muc, "--co-chu", str(self.so(self.co_chu, "Cỡ chữ", int, duong=True)),
                  "--day-net", str(self.so(self.day_net, "Dày nét", duong=True)),
                  "--ti-le", str(self.so(self.ti_le, "Tỉ lệ", duong=True)),
                  "--day-khung", str(self.so(self.day_khung, "Dày khung", duong=True)),
                  "--le-max", str(self.so(self.le_max, "Đệm trục"))] + self.khoang_args() + self.chu_vach_args()
            c += them_bao_cao()
            lenh.append(("Vẽ bằng Origin", c))
        if self.dung_csv.get() or xem_truoc or pho:
            c = self.lenh_con("xu_ly_dien_hoa.py", "--worker-csv") + files + chung + nhan_mau
            if xem_truoc:
                c += ["--thu-muc-ra", THU_MUC_XEM_TRUOC]
            elif pho:
                c += ["--thu-muc-ra", thu_muc]
            else:
                c += ["--thu-muc-ra", os.path.join(thu_muc, "csv_va_anh_nhanh")]
                if lenh:
                    c.append("--khong-canh-bao")      # Origin đã in cảnh báo rồi
                c += them_bao_cao()
            lenh.append(("Xem trước (Matplotlib)" if xem_truoc else ("Vẽ phổ xếp chồng" if pho else "Xuất CSV & Ảnh nhanh"), c))
        if not lenh:
            raise ValueError("Hãy tick ít nhất một đầu ra: 'Vẽ bằng Origin' hoặc 'Xuất CSV & ảnh Matplotlib' (tab Xuất / Hình).")
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
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, stdin=subprocess.DEVNULL, creationflags=CO_CONSOLE)
                else:
                    p.terminate()
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    def mo_tien_trinh(self, c, env):
        """Mở tiến trình con. Sau FreeConsole() app không còn console nên PHẢI đặt stdin=DEVNULL,
        nếu không Windows báo [WinError 50] The request is not supported. Thử lại không cờ console nếu vẫn lỗi."""
        kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                  encoding="utf-8", errors="replace", cwd=THU_MUC, env=env)
        try:
            return subprocess.Popen(c, creationflags=CO_CONSOLE, **kw)
        except OSError:
            if os.name != "nt":
                raise
            return subprocess.Popen(c, **kw)

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
                self.proc = self.mo_tien_trinh(c, env)
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
                info = {"path": m["path"], "nhan": m["nhan"], "mau": m["mau"], "loai_nhan_dang": m.get("loai_nhan", "?"), "nhom": m.get("nhom", "")}
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
    app = App(root, dnd)
    app.kiem_file_ma_nguon()
    root.mainloop()


if __name__ == "__main__":
    main()
