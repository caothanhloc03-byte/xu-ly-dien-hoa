#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Giao diện điều khiển chương trình xử lý điện hóa & vẽ Origin.
"""
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, simpledialog, ttk

THU_MUC = os.path.dirname(os.path.abspath(__file__))
CAI_DAT = os.path.join(THU_MUC, "cai_dat.json")
PHIEN_BAN_CAI_DAT = 3
LOAI = ["Tự nhận dạng", "LSV", "CV", "IT", "EIS", "ECSA (nhiều file CV)", "Tafel"]
BANG_MAU = ["#404040", "#f03c3c", "#1a5fd8", "#2aa55a", "#ff7f0e", "#9467bd",
            "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
CO_CONSOLE = 0x08000000 if os.name == "nt" else 0


def python_exe():
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(cand):
            return cand
    return exe


class App:
    def __init__(self, root):
        self.root = root
        root.title("Xử lý và vẽ số liệu điện hóa  (LSV · CV · IT · EIS · ECSA · Tafel)")
        root.minsize(960, 750)
        cd = self.doc_cai_dat()

        self.q = queue.Queue()
        self.dang_chay = False
        self.muc = []

        S = tk.StringVar
        B = tk.BooleanVar
        self.loai = S(value=cd.get("loai", LOAI[0]))
        self.chong = B(value=cd.get("chong", True))
        self.noi_tiep = B(value=cd.get("noi_tiep", False))
        self.mau_chu_ky = B(value=cd.get("mau_chu_ky", False))
        self.chu_ky = S(value=cd.get("chu_ky", ""))
        self.ph = S(value=cd.get("ph", "13.8"))
        self.eref = S(value=cd.get("eref", "0.098"))
        self.nhan_i = S(value=cd.get("nhan_i", "2"))
        self.chia_i = S(value=cd.get("chia_i", "2.15"))
        self.e_ecsa = S(value=cd.get("e_ecsa", ""))
        self.cs = S(value=cd.get("cs", "0.040"))
        self.tafel_min = S(value=cd.get("tafel_min", "9.0"))
        self.tafel_max = S(value=cd.get("tafel_max", "11.0"))
        self.dung_origin = B(value=cd.get("dung_origin", True))
        self.dung_csv = B(value=cd.get("dung_csv", True))
        self.template = S(value=cd.get("template", ""))
        self.thu_muc_ra = S(value=cd.get("thu_muc_ra", os.path.join(THU_MUC, "ket_qua")))
        self.rong = S(value=cd.get("rong", "1200"))
        self.co_chu = S(value=cd.get("co_chu", "22"))
        self.day_net = S(value=cd.get("day_net", "2"))
        self.ti_le = S(value=cd.get("ti_le", "1.28"))

        self.dung_giao_dien()
        self.cap_nhat_trang_thai()
        self.doc_hang_doi()

    def dung_giao_dien(self):
        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self.root, padding=6)
        main.pack(fill="both", expand=True)

        # 1. File table
        f1 = ttk.LabelFrame(main, text=" 1. File số liệu thô ")
        f1.pack(fill="x", **pad)
        cot = ("nhan", "mau", "file")
        self.tv = ttk.Treeview(f1, columns=cot, show="headings", height=6, selectmode="browse")
        self.tv.heading("nhan", text="Nhãn chú thích")
        self.tv.heading("mau", text="Màu")
        self.tv.heading("file", text="File")
        self.tv.column("nhan", width=210, anchor="w")
        self.tv.column("mau", width=80, anchor="center")
        self.tv.column("file", width=420, anchor="w")
        self.tv.grid(row=0, column=0, rowspan=7, sticky="nsew", padx=(8, 0), pady=6)
        sb = ttk.Scrollbar(f1, command=self.tv.yview)
        sb.grid(row=0, column=1, rowspan=7, sticky="ns", pady=6)
        self.tv.config(yscrollcommand=sb.set)
        self.tv.bind("<Double-1>", self.bam_dup)

        for i, (ten, lenh) in enumerate([("Thêm file...", self.them_file), ("Đổi nhãn", self.doi_nhan),
                                         ("Đổi màu", self.doi_mau), ("▲ Lên", lambda: self.di_chuyen(-1)),
                                         ("▼ Xuống", lambda: self.di_chuyen(1)), ("Xóa mục chọn", self.xoa_chon),
                                         ("Xóa hết", self.xoa_het)]):
            ttk.Button(f1, text=ten, command=lenh).grid(row=i, column=2, sticky="ew", padx=8, pady=1)
        f1.columnconfigure(0, weight=1)

        # 2 & 3
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
        ttk.Entry(f2, textvariable=self.ph, width=6).grid(row=1, column=1, sticky="w")
        ttk.Label(f2, text="+").grid(row=1, column=2)
        ttk.Entry(f2, textvariable=self.eref, width=6).grid(row=1, column=3, sticky="w")

        ttk.Label(f2, text="I = i × 1000 ×").grid(row=2, column=0, sticky="e", padx=8, pady=3)
        ttk.Entry(f2, textvariable=self.nhan_i, width=6).grid(row=2, column=1, sticky="w")
        ttk.Label(f2, text="÷").grid(row=2, column=2)
        ttk.Entry(f2, textvariable=self.chia_i, width=6).grid(row=2, column=3, sticky="w")

        ttk.Checkbutton(f2, text="Vẽ chồng các file cùng loại", variable=self.chong).grid(
            row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 0))

        # Tafel options
        ttk.Label(f2, text="Vùng dòng Tafel (mA):").grid(row=4, column=0, sticky="w", padx=8, pady=(6, 2))
        f_tafel = ttk.Frame(f2)
        f_tafel.grid(row=4, column=1, columnspan=3, sticky="w")
        self.en_tf_min = ttk.Entry(f_tafel, textvariable=self.tafel_min, width=5)
        self.en_tf_min.pack(side="left")
        ttk.Label(f_tafel, text=" đến ").pack(side="left")
        self.en_tf_max = ttk.Entry(f_tafel, textvariable=self.tafel_max, width=5)
        self.en_tf_max.pack(side="left")

        # ECSA options
        ttk.Label(f2, text="ECSA E (V vs RHE):").grid(row=5, column=0, sticky="w", padx=8, pady=3)
        self.en_e_ecsa = ttk.Entry(f2, textvariable=self.e_ecsa, width=6)
        self.en_e_ecsa.grid(row=5, column=1, sticky="w")
        ttk.Label(f2, text="Cs (mF/cm²):").grid(row=5, column=2, sticky="e")
        self.en_cs = ttk.Entry(f2, textvariable=self.cs, width=6)
        self.en_cs.grid(row=5, column=3, sticky="w")

        # 3. Output options
        ttk.Checkbutton(f3, text="Vẽ bằng Origin 2024", variable=self.dung_origin).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=3)
        ttk.Checkbutton(f3, text="Xuất CSV & Ảnh Matplotlib", variable=self.dung_csv).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=8)

        ttk.Label(f3, text="Thư mục kết quả:").grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 0))
        ttk.Entry(f3, textvariable=self.thu_muc_ra).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(8, 0))
        ttk.Button(f3, text="Chọn...", command=self.chon_thu_muc).grid(row=3, column=2, padx=6)

        sub = ttk.Frame(f3)
        sub.grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))
        for c, (nhan, bien, rong) in enumerate([("Cỡ chữ", self.co_chu, 4), ("Dày nét", self.day_net, 4),
                                                ("Tỉ lệ R:C", self.ti_le, 5)]):
            ttk.Label(sub, text=nhan).grid(row=0, column=c * 2, sticky="e", padx=(0, 2))
            ttk.Entry(sub, textvariable=bien, width=rong).grid(row=0, column=c * 2 + 1, padx=(0, 6))

        f3.columnconfigure(1, weight=1)

        # Control buttons
        fb = ttk.Frame(main)
        fb.pack(fill="x", **pad)
        self.nut_chay = ttk.Button(fb, text="▶  CHẠY XỬ LÝ & VẼ", command=self.bam_chay)
        self.nut_chay.pack(side="left", ipadx=28, ipady=6)
        ttk.Button(fb, text="Mở thư mục kết quả", command=self.mo_thu_muc).pack(side="left", padx=10)

        fl = ttk.LabelFrame(main, text=" Báo cáo & Thông số tính toán ")
        fl.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(fl, height=10, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=6, pady=6)

    def cap_nhat_trang_thai(self):
        loai_val = self.loai.get()
        ecsa = loai_val.startswith("ECSA")
        tafel = loai_val.startswith("Tafel")

        self.en_e_ecsa.config(state="normal" if ecsa else "disabled")
        self.en_cs.config(state="normal" if ecsa else "disabled")
        self.en_tf_min.config(state="normal" if tafel else "disabled")
        self.en_tf_max.config(state="normal" if tafel else "disabled")

    def lam_moi_bang(self, chon=None):
        for i in self.tv.get_children():
            self.tv.delete(i)
        for k, m in enumerate(self.muc):
            tag = f"c{k}"
            self.tv.insert("", "end", iid=str(k), values=(m["nhan"], m["mau"], m["path"]), tags=(tag,))
            try:
                self.tv.tag_configure(tag, foreground=m["mau"])
            except Exception:
                pass
        if chon is not None and 0 <= chon < len(self.muc):
            self.tv.selection_set(str(chon))

    def chi_so_chon(self):
        s = self.tv.selection()
        return int(s[0]) if s else None

    def them_file(self):
        ds = filedialog.askopenfilenames(title="Chọn file", filetypes=[("Dữ liệu", "*.txt *.csv *.dat"), ("Tất cả", "*.*")])
        for p in ds:
            if any(m["path"] == p for m in self.muc):
                continue
            k = len(self.muc)
            self.muc.append({"path": p, "nhan": os.path.splitext(os.path.basename(p))[0],
                             "mau": BANG_MAU[k % len(BANG_MAU)]})
        self.lam_moi_bang()

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
        if cot == "#2":
            self.doi_mau()
        else:
            self.doi_nhan()

    def chon_thu_muc(self):
        p = filedialog.askdirectory(title="Chọn thư mục")
        if p:
            self.thu_muc_ra.set(p)

    def mo_thu_muc(self):
        p = self.thu_muc_ra.get()
        os.makedirs(p, exist_ok=True)
        try:
            os.startfile(p)
        except AttributeError:
            messagebox.showinfo("Thư mục", p)

    def doc_cai_dat(self):
        try:
            with open(CAI_DAT, "r", encoding="utf-8") as f:
                cd = json.load(f)
            return cd if cd.get("ver") == PHIEN_BAN_CAI_DAT else {}
        except Exception:
            return {}

    def luu_cai_dat(self):
        cd = {"ver": PHIEN_BAN_CAI_DAT}
        for ten in ("loai", "chong", "noi_tiep", "mau_chu_ky", "chu_ky", "ph", "eref", "nhan_i", "chia_i",
                    "e_ecsa", "cs", "tafel_min", "tafel_max", "dung_origin", "dung_csv", "template",
                    "thu_muc_ra", "rong", "co_chu", "day_net", "ti_le"):
            cd[ten] = getattr(self, ten).get()
        try:
            with open(CAI_DAT, "w", encoding="utf-8") as f:
                json.dump(cd, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    @staticmethod
    def so(bien, ten, kieu=float, duong=False):
        try:
            v = kieu(bien.get().strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"'{ten}' phải là số.")
        if duong and v <= 0:
            raise ValueError(f"'{ten}' phải lớn hơn 0.")
        return v

    def lam_lenh(self):
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

        files = [m["path"] for m in self.muc]
        nhan_mau = []
        for m in self.muc:
            nhan_mau += ["--nhan", m["nhan"], "--mau-file", m["mau"]]

        py = python_exe()
        lenh = []
        if self.dung_origin.get():
            c = [py, "-u", os.path.join(THU_MUC, "ve_origin.py")] + files + chung + nhan_mau
            c += ["--thu-muc-ra", thu_muc, "--co-chu", str(self.so(self.co_chu, "Cỡ chữ", int, duong=True)),
                  "--day-net", str(self.so(self.day_net, "Dày nét", duong=True)),
                  "--ti-le", str(self.so(self.ti_le, "Tỉ lệ", duong=True))]
            lenh.append(("Vẽ bằng Origin 2024", c))
        if self.dung_csv.get():
            c = [py, "-u", os.path.join(THU_MUC, "xu_ly_dien_hoa.py")] + files + chung + nhan_mau
            c += ["--thu-muc-ra", os.path.join(thu_muc, "csv_va_anh_nhanh")]
            lenh.append(("Xuất CSV & Ảnh nhanh", c))
        return lenh

    def bam_chay(self):
        if self.dang_chay:
            return
        try:
            lenh = self.lam_lenh()
        except ValueError as e:
            messagebox.showwarning("Thông báo", str(e))
            return
        self.luu_cai_dat()
        self.dang_chay = True
        self.nut_chay.config(state="disabled", text="Đang xử lý...")
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        threading.Thread(target=self.chay_nen, args=(lenh,), daemon=True).start()

    def chay_nen(self, lenh):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        tot = True
        for ten, c in lenh:
            self.q.put(f"=== {ten} ===\n")
            try:
                p = subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace", cwd=THU_MUC, env=env,
                                     creationflags=CO_CONSOLE)
                for dong in p.stdout:
                    self.q.put(dong)
                p.wait()
                if p.returncode != 0:
                    tot = False
            except Exception as e:
                tot = False
                self.q.put(f"[LỖI] {e}\n")
            self.q.put("\n")
        self.q.put(">>> HOÀN THÀNH\n" if tot else ">>> CÓ LỖI XẢY RA\n")
        self.q.put(None)

    def doc_hang_doi(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m is None:
                    self.dang_chay = False
                    self.nut_chay.config(state="normal", text="▶  CHẠY XỬ LÝ & VẼ")
                else:
                    self.log.config(state="normal")
                    self.log.insert("end", m)
                    self.log.see("end")
                    self.log.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.doc_hang_doi)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
