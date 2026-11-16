# -*- coding: utf-8 -*-
"""Cửa sổ "Cdl nhiều mẫu": thêm các thư mục ECSA (mỗi thư mục = 1 mẫu, gồm các CV nhiều tốc độ quét) -> hình ΔJ theo tốc độ quét + Cdl.
Chạy bằng tiến trình con (xu_ly_dien_hoa.py --cdl-nhieu; vẽ Origin: ve_origin.py --cdl-nhieu), giống các công cụ khác của app."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

import cdl_nhieu

try:
    import giao_dien_dep as gd
except Exception:
    gd = None

BANG_MAU = ["#f03c3c", "#ff7f0e", "#2aa55a", "#1a5fd8", "#8a2be2", "#000000", "#9467bd", "#17becf", "#8c564b", "#7f7f7f"]
TEN_HINH = "Cdl_nhieu.png"


class CuaSoCdlNhieu:
    def __init__(self, app, thu_muc_ra_mac_dinh=None):
        self.app = app
        self.q = queue.Queue()
        self.dang = False
        self.mau = []                                    # [{"path", "nhan", "mau"}]
        w = self.w = tk.Toplevel(app.root)
        w.title("Cdl nhiều mẫu (từ các thư mục ECSA)")
        w.geometry("900x640")
        w.minsize(780, 520)
        w.transient(app.root)
        w.columnconfigure(0, weight=1)
        if gd:
            gd.dai_logo(w, "Cdl nhiều mẫu", "Echem Studio  ·  công cụ ECSA").grid(row=0, column=0, sticky="ew")
        ttk.Label(w, foreground="#444", justify="left", wraplength=860, text=(
            "Mỗi mẫu = 1 thư mục ECSA chứa các file CV ở nhiều tốc độ quét. Với từng file: lấy chu kỳ cuối (hoặc chu kỳ chọn ở tab Phân tích), "
            "ΔJ = (Ja − Jc)/2 tại điện thế E lấy dòng, rồi fit ΔJ theo tốc độ quét (V/s): độ dốc = Cdl (mF/cm²). "
            "Chỉ xuất hình Cdl chung và bảng Cdl, không vẽ ECSA.")).grid(row=1, column=0, sticky="w", padx=10, pady=(8, 4))
        f1 = ttk.LabelFrame(w, text="Mẫu (thư mục ECSA)")
        f1.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        f1.columnconfigure(0, weight=1)
        self.tv = ttk.Treeview(f1, columns=("nhan", "tm", "n"), show="headings", height=6, selectmode="browse")
        for c, t, r in (("nhan", "Nhãn (hiện ở chú thích)", 220), ("tm", "Thư mục", 500), ("n", "Số file", 60)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=r, anchor="w")
        self.tv.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        nut = ttk.Frame(f1)
        nut.grid(row=1, column=0, sticky="w", padx=6, pady=(0, 4))
        for ten, lenh in (("Thêm thư mục ECSA...", self.them_thu_muc), ("Thêm các thư mục con của...", self.them_thu_muc_con),
                          ("Xóa", self.xoa), ("Đổi nhãn", self.doi_nhan), ("Đổi màu", self.doi_mau), ("↑", lambda: self.doi_cho(-1)), ("↓", lambda: self.doi_cho(1))):
            ttk.Button(nut, text=ten, command=lenh).pack(side="left", padx=(0, 4))
        f2 = ttk.Frame(w)
        f2.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        f2.columnconfigure(1, weight=1)
        ttk.Label(f2, text="Thư mục kết quả:").grid(row=0, column=0, sticky="w")
        self.ra = tk.StringVar(value=thu_muc_ra_mac_dinh or os.path.join(app.thu_muc_ra.get(), "Cdl_nhieu"))
        ttk.Entry(f2, textvariable=self.ra).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(f2, text="Chọn...", command=self.chon_ra).grid(row=0, column=2)
        f3 = ttk.LabelFrame(w, text="Thông số")
        f3.grid(row=4, column=0, sticky="ew", padx=10, pady=4)
        self.e_chon = tk.StringVar(value="")
        self.don_vi = tk.StringVar(value="A/cm²")
        self.in_cdl = tk.BooleanVar(value=True)
        self.dung_mpl = tk.BooleanVar(value=True)
        self.dung_origin = tk.BooleanVar(value=False)
        r1 = ttk.Frame(f3)
        r1.pack(fill="x", padx=6, pady=3)
        ttk.Label(r1, text="E lấy dòng (V vs RHE, trống = giữa vùng chung của từng mẫu):").pack(side="left")
        ttk.Entry(r1, textvariable=self.e_chon, width=8).pack(side="left", padx=(4, 14))
        ttk.Label(r1, text="Đơn vị ΔJ:").pack(side="left")
        ttk.Combobox(r1, textvariable=self.don_vi, values=["A/cm²", "mA/cm²"], state="readonly", width=8).pack(side="left", padx=(4, 14))
        ttk.Checkbutton(r1, text="Ghi Cdl lên hình", variable=self.in_cdl).pack(side="left")
        r2 = ttk.Frame(f3)
        r2.pack(fill="x", padx=6, pady=3)
        ttk.Label(r2, text="Vẽ hình bằng:").pack(side="left")
        ttk.Checkbutton(r2, text="Matplotlib (Cdl_nhieu.png/.pdf)", variable=self.dung_mpl).pack(side="left", padx=8)
        ttk.Checkbutton(r2, text="Origin 2022+ (Cdl_nhieu; kiểu/cỡ chữ theo tab Hình)", variable=self.dung_origin).pack(side="left", padx=8)
        ttk.Label(r2, text="(pH, Eref, hệ số nhân/chia I, chu kỳ CV lấy ở tab Dữ liệu / Phân tích)", foreground="#666").pack(side="left", padx=8)
        fb = ttk.Frame(w)
        fb.grid(row=5, column=0, sticky="w", padx=10, pady=4)
        self.nut = ttk.Button(fb, text="▶  Tính Cdl & vẽ hình", command=self.chay)
        self.nut.pack(side="left", ipadx=14, ipady=3)
        ttk.Button(fb, text="Xem hình", command=self.xem_hinh).pack(side="left", padx=6)
        ttk.Button(fb, text="Mở thư mục kết quả", command=lambda: app.mo_duong_dan(self.ra.get())).pack(side="left", padx=2)
        ttk.Button(fb, text="Đóng", command=w.destroy).pack(side="left", padx=2)
        w.rowconfigure(6, weight=1)
        self.log = scrolledtext.ScrolledText(w, height=12, state="disabled", font=("Consolas", 9))
        self.log.grid(row=6, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.ve()
        w.after(150, self.doc_hang_doi)

    # ---- bảng mẫu
    def ve(self, chon=None):
        self.tv.delete(*self.tv.get_children())
        for k, m in enumerate(self.mau):
            self.tv.insert("", "end", iid=str(k), values=(m["nhan"], m["path"], len(cdl_nhieu.liet_ke_file(m["path"])) if os.path.isdir(m["path"]) else "?"))
        if chon is not None and 0 <= chon < len(self.mau):
            self.tv.selection_set(str(chon))

    def chon_k(self):
        s = self.tv.selection()
        if not s:
            messagebox.showinfo("Cdl nhiều mẫu", "Hãy chọn một mẫu trong bảng trước.", parent=self.w)
            return None
        return int(s[0])

    def _them(self, p):
        p = os.path.normpath(p)
        if any(m["path"] == p for m in self.mau):
            return
        self.mau.append({"path": p, "nhan": os.path.basename(p) or p, "mau": BANG_MAU[len(self.mau) % len(BANG_MAU)]})

    def them_thu_muc(self):
        p = filedialog.askdirectory(title="Thư mục ECSA của một mẫu (chứa các file CV nhiều tốc độ quét)", parent=self.w)
        if p:
            self._them(p)
            self.ve(len(self.mau) - 1)

    def them_thu_muc_con(self):
        p = filedialog.askdirectory(title="Thư mục cha: mỗi thư mục con là một mẫu ECSA", parent=self.w)
        if not p:
            return
        con = [os.path.join(p, d) for d in sorted(os.listdir(p), key=str.lower) if os.path.isdir(os.path.join(p, d))]
        con = [d for d in con if cdl_nhieu.liet_ke_file(d)]
        if not con:
            messagebox.showinfo("Cdl nhiều mẫu", "Không có thư mục con nào chứa file CV (.txt/.csv/.dat).", parent=self.w)
            return
        for d in con:
            self._them(d)
        self.ve(len(self.mau) - 1)

    def xoa(self):
        k = self.chon_k()
        if k is not None:
            del self.mau[k]
            self.ve(min(k, len(self.mau) - 1))

    def doi_nhan(self):
        k = self.chon_k()
        if k is None:
            return
        moi = simpledialog.askstring("Nhãn mẫu", "Nhãn (vd Fe,Ni-Cu2O@CuF-G; chỉ số hóa học tự hạ xuống dưới):", initialvalue=self.mau[k]["nhan"], parent=self.w)
        if moi and moi.strip():
            self.mau[k]["nhan"] = moi.strip()
            self.ve(k)

    def doi_mau(self):
        k = self.chon_k()
        if k is None:
            return
        from tkinter import colorchooser
        c = colorchooser.askcolor(color=self.mau[k]["mau"], parent=self.w)[1]
        if c:
            self.mau[k]["mau"] = c

    def doi_cho(self, h):
        k = self.chon_k()
        if k is None or not (0 <= k + h < len(self.mau)):
            return
        self.mau[k], self.mau[k + h] = self.mau[k + h], self.mau[k]
        self.ve(k + h)

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
            raise ValueError("Chưa có mẫu nào (bấm 'Thêm thư mục ECSA...' hoặc 'Thêm các thư mục con của...').")
        mat = [m["path"] for m in self.mau if not os.path.isdir(m["path"])]
        if mat:
            raise ValueError("Không tìm thấy thư mục (đã đổi tên, di chuyển hoặc ổ đĩa/USB chưa cắm):\n" + "\n".join(mat))
        trong = [m["nhan"] for m in self.mau if len(cdl_nhieu.liet_ke_file(m["path"])) < 2]
        if trong:
            raise ValueError("Các mẫu sau có dưới 2 file CV trong thư mục:\n" + "\n".join(trong))
        if not self.dung_mpl.get() and not self.dung_origin.get():
            raise ValueError("Hãy tick ít nhất một cách vẽ: Matplotlib hoặc Origin.")
        ph, eref = a.so(a.ph, "pH"), a.so(a.eref, "Eref")
        thamso = [m["path"] for m in self.mau]
        thamso += ["--cdl-nhieu", "--ph", str(ph), "--eref", str(eref), "--nernst", str(a.so(a.nernst, "hệ số Nernst", duong=True)),
                   "--nhan-i", str(a.so(a.nhan_i, "hệ số nhân I", duong=True)), "--chia-i", str(a.so(a.chia_i, "hệ số chia I", duong=True)),
                   "--loai", "CV", "--cdl-y", "mA" if self.don_vi.get().startswith("mA") else "A"]
        if a.chu_ky.get().strip():
            thamso += ["--chu-ky", str(a.so(a.chu_ky, "Chu kỳ CV", int, duong=True))]
        r_s = a.so_khong_am(a.r_s, "Rs")
        if r_s > 0:
            thamso += ["--r-s", str(r_s), "--ir-phan-tram", str(a.so(a.ir_pct, "% bù iR", duong=True))]
        if a.khong_rhe.get():
            thamso.append("--khong-rhe")
        if self.e_chon.get().strip():
            try:
                thamso += ["--e-ecsa", str(float(self.e_chon.get().strip().replace(",", ".")))]
            except ValueError:
                raise ValueError("E lấy dòng phải là số (V).")
        if not self.in_cdl.get():
            thamso.append("--cdl-khong-nhan")
        for m in self.mau:
            thamso += ["--nhan", m["nhan"], "--mau-file", m["mau"]]
        ra = os.path.abspath(self.ra.get())
        thamso += ["--thu-muc-ra", ra, "--khong-canh-bao"]
        lenhs = []
        pre = a.lenh_con("xu_ly_dien_hoa.py", "--worker-csv")
        lenhs.append(("Tính Cdl" + (" & vẽ Matplotlib" if self.dung_mpl.get() else ""), pre + thamso + ([] if self.dung_mpl.get() else ["--khong-ve"])))
        if self.dung_origin.get():
            js = os.path.join(ra, cdl_nhieu.TEN_JSON)
            co = a.lenh_con("ve_origin.py", "--worker-origin") + [js, "--cdl-nhieu", "--thu-muc-ra", ra, "--khong-canh-bao",
                 "--co-chu", str(a.so(a.co_chu, "Cỡ chữ", int, duong=True)), "--day-net", str(a.so(a.day_net, "Dày nét", duong=True)),
                 "--ti-le", str(a.so(a.ti_le, "Tỉ lệ", duong=True)), "--day-khung", str(a.so(a.day_khung, "Dày khung", duong=True)),
                 "--le-max", str(a.so(a.le_max, "Đệm trục"))] + a.khoang_args() + a.chu_vach_args()
            lenhs.append(("Vẽ bằng Origin", co))
        return lenhs

    def chay(self):
        if self.dang:
            return
        try:
            lenhs = self.lenh()
        except ValueError as e:
            messagebox.showwarning("Cdl nhiều mẫu", str(e), parent=self.w)
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
                if p.returncode:                                  # tính lỗi thì không vẽ Origin từ JSON cũ
                    break
            except Exception as e:
                self.q.put(f"[LỖI] {e}\n")
                ma = 1
                break
            self.q.put("\n")
        self.q.put(("xong", ma))

    def doc_hang_doi(self):
        try:
            while True:
                v = self.q.get_nowait()
                if isinstance(v, tuple):
                    self.dang = False
                    self.nut.config(state="normal", text="▶  Tính Cdl & vẽ hình")
                    self.ghi("\n>>> HOÀN THÀNH\n" if v[1] == 0 else "\n>>> CÓ LỖI (xem các dòng ở trên)\n")
                    if v[1] == 0 and self.dung_mpl.get() and os.path.isfile(os.path.join(self.ra.get(), TEN_HINH)):
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
        p = os.path.join(self.ra.get(), TEN_HINH)
        if not os.path.isfile(p):
            messagebox.showinfo("Cdl nhiều mẫu", "Chưa có hình Matplotlib. Bấm 'Tính Cdl & vẽ hình' (tick Matplotlib) trước.", parent=self.w)
            return
        w = tk.Toplevel(self.w)
        w.title(TEN_HINH)
        try:
            img = tk.PhotoImage(file=p)
            k = max(-(-img.width() // 900), -(-img.height() // 640), 1)
            img = img.subsample(k, k)
            lb = ttk.Label(w, image=img)
            lb.image = img
            lb.pack(padx=6, pady=6)
        except Exception as e:
            ttk.Label(w, text=f"Không hiển thị được hình: {e}").pack(padx=10, pady=10)
        ttk.Button(w, text="Mở bằng chương trình ảnh", command=lambda: self.app.mo_duong_dan(p)).pack(pady=(0, 8))
