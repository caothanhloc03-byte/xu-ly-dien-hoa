# -*- coding: utf-8 -*-
"""Cửa sổ XRD: mở file Excel/text (nhiều mẫu) -> tìm đỉnh -> xác định pha theo ngân hàng -> phân biệt đỉnh của mẫu/đế/bức xạ phụ/lạ
-> so sánh các mẫu -> minh chứng bằng lời dễ hiểu -> vẽ xếp chồng ra Origin. Lõi tính toán: xrd.py, ngân hàng: xrd_ngan_hang.py."""
import os
import numpy as np
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import xrd
import xrd_ngan_hang as nh


class CuaSoXrd:
    def __init__(self, root, lenh_origin=None):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.root = root
        self.lenh_origin = lenh_origin
        self.mau = []
        self.kq = []
        self.ss = None
        w = self.w = tk.Toplevel(root)
        w.title("XRD: xác định pha, so sánh mẫu, minh chứng, vẽ Origin")
        w.geometry("1200x820")
        self.v_file = tk.StringVar(value="(chưa mở file)")
        self.v_nt = tk.StringVar(value="")
        self.dung = []                      # [(mẫu, BooleanVar)] theo thứ tự hiển thị (tick = dùng)
        self.v_nguon = tk.StringVar(value=xrd.NGUON_MAC_DINH)
        self.v_ds = tk.StringVar(value="0.15")
        self.v_snr = tk.StringVar(value="5")
        self.v_chuan = tk.StringVar(value="")
        self.v_nhan = tk.BooleanVar(value=True)
        self.v_tt = tk.StringVar(value="Mở file Excel/text XRD (cột 2θ, cường độ; có thể nhiều mẫu trong một file).")

        f1 = ttk.Frame(w)
        f1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(f1, text="Mở file XRD...", command=self.mo_file).pack(side="left")
        ttk.Label(f1, textvariable=self.v_file, foreground="#444").pack(side="left", padx=6)
        ttk.Button(f1, text="Đổi tên mẫu...", command=self.doi_ten).pack(side="right")
        f2 = ttk.Frame(w)
        f2.pack(fill="x", padx=6, pady=2)
        ttk.Label(f2, text="Giới hạn nguyên tố (để trống = tự quét toàn bộ ngân hàng):").pack(side="left")
        ttk.Entry(f2, textvariable=self.v_nt, width=12).pack(side="left", padx=2)
        ttk.Label(f2, text="  Nguồn tia X:").pack(side="left")
        ttk.Combobox(f2, textvariable=self.v_nguon, values=list(nh.NGUON), width=16, state="readonly").pack(side="left", padx=2)
        ttk.Label(f2, text="  Dung sai ghép vạch (°):").pack(side="left")
        ttk.Entry(f2, textvariable=self.v_ds, width=5).pack(side="left", padx=2)
        ttk.Label(f2, text="  Ngưỡng đỉnh (σ):").pack(side="left")
        ttk.Entry(f2, textvariable=self.v_snr, width=4).pack(side="left", padx=2)
        ttk.Label(f2, text="  Mẫu chuẩn (đế):").pack(side="left")
        self.cb_chuan = ttk.Combobox(f2, textvariable=self.v_chuan, width=14, state="readonly")
        self.cb_chuan.pack(side="left", padx=2)
        self.fr_mau = ttk.LabelFrame(w, text=" Mẫu: tick để dùng, ▲▼ để đổi thứ tự (mẫu đầu nằm dưới cùng trên hình) ")
        self.fr_mau.pack(fill="x", padx=6, pady=2)
        f3 = ttk.Frame(w)
        f3.pack(fill="x", padx=6, pady=3)
        ttk.Button(f3, text="Phân tích + xác định pha", command=self.phan_tich).pack(side="left")
        ttk.Button(f3, text="So sánh các mẫu (đỉnh lạ?)", command=self.so_sanh).pack(side="left", padx=6)
        ttk.Button(f3, text="Ngân hàng phổ...", command=self.ngan_hang).pack(side="left", padx=2)
        ttk.Button(f3, text="Xuất CSV + báo cáo + hình...", command=self.xuat).pack(side="left", padx=(14, 2))
        ttk.Button(f3, text="Vẽ ra Origin...", command=self.ve_origin).pack(side="left", padx=2)
        ttk.Checkbutton(f3, text="Ghi nhãn pha trên đỉnh", variable=self.v_nhan).pack(side="left", padx=8)

        than = ttk.PanedWindow(w, orient="horizontal")
        than.pack(fill="both", expand=True, padx=6, pady=2)
        trai, phai = ttk.Frame(than), ttk.Frame(than, width=440)
        than.add(trai, weight=3)
        than.add(phai, weight=2)
        self.fig = Figure(figsize=(6.4, 5.6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.cv = FigureCanvasTkAgg(self.fig, master=trai)
        self.cv.get_tk_widget().pack(fill="both", expand=True)
        nb = ttk.Notebook(phai)
        nb.pack(fill="both", expand=True)
        self.txt_bc = tk.Text(nb, font=("Consolas", 10), wrap="word")
        self.txt_ss = tk.Text(nb, font=("Consolas", 10), wrap="word")
        nb.add(self.txt_bc, text="Kết quả + minh chứng")
        nb.add(self.txt_ss, text="So sánh mẫu")
        ttk.Label(w, textvariable=self.v_tt, foreground="#444", wraplength=1160, justify="left").pack(fill="x", padx=8, pady=(0, 6))

    # ---------- dữ liệu ----------
    def mo_file(self):
        p = filedialog.askopenfilename(parent=self.w, title="Chọn file XRD", filetypes=[("XRD", "*.xlsx *.xlsm *.txt *.csv *.xy *.dat"), ("Tất cả", "*.*")])
        if p:
            self.nap_file(p)

    def nap_file(self, p):
        try:
            self.mau = xrd.doc_xrd(p)
        except Exception as e:
            messagebox.showerror("XRD", f"Không đọc được file:\n{e}", parent=self.w)
            return
        self.v_file.set(os.path.basename(p))
        self.dung = [(m, tk.BooleanVar(value=True)) for m in self.mau]
        self._dung_ds()
        ten = [m["ten"] for m in self.mau]
        self.cb_chuan["values"] = [""] + ten
        ch = next((t for t in ten if t.strip().upper() == "NF"), "")
        self.v_chuan.set(ch)
        self.kq, self.ss = [], None
        self.v_tt.set(f"Đọc được {len(self.mau)} mẫu: " + ", ".join(ten) + ". Bấm 'Phân tích + xác định pha'.")
        self.ve_tho()

    def mau_dung(self):
        """Các mẫu đang được tick, theo thứ tự hiển thị."""
        if not self.dung:
            return list(self.mau)
        return [m for m, v in self.dung if v.get()]

    def _dung_ds(self):
        for c in list(self.fr_mau.winfo_children()):
            c.destroy()
        for i, (m, v) in enumerate(self.dung):
            f = ttk.Frame(self.fr_mau)
            f.pack(side="left", padx=4, pady=2)
            ttk.Checkbutton(f, text=m["ten"], variable=v, command=self._doi_ds).pack(side="left")
            ttk.Button(f, text="▲", width=2, command=lambda i=i: self._chuyen(i, -1)).pack(side="left")
            ttk.Button(f, text="▼", width=2, command=lambda i=i: self._chuyen(i, 1)).pack(side="left")

    def _chuyen(self, i, d):
        j = i + d
        if 0 <= j < len(self.dung):
            self.dung[i], self.dung[j] = self.dung[j], self.dung[i]
            self._dung_ds()
            self._doi_ds()

    def _doi_ds(self):
        """Đổi tick/thứ tự: nếu đã phân tích thì phân tích lại, chưa thì chỉ vẽ lại phổ thô."""
        if self.kq:
            self.phan_tich()
        else:
            self.ve_tho()

    def doi_ten(self):
        for m in self.mau:
            t = simpledialog.askstring("Đổi tên mẫu", f"Tên cho '{m['ten']}':", initialvalue=m["ten"], parent=self.w)
            if t:
                m["ten"] = t.strip()
        self.cb_chuan["values"] = [""] + [m["ten"] for m in self.mau]
        self._dung_ds()

    def _so(self, var, ten, mac):
        try:
            return float(var.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning("XRD", f"Giá trị '{ten}' không hợp lệ, dùng {mac}.", parent=self.w)
            return mac

    # ---------- phân tích ----------
    def phan_tich(self):
        if not self.mau:
            messagebox.showinfo("XRD", "Hãy mở file XRD trước.", parent=self.w)
            return
        mau = self.mau_dung()
        if not mau:
            messagebox.showinfo("XRD", "Hãy tick ít nhất một mẫu.", parent=self.w)
            return
        nt = nh.doc_nguyen_to(self.v_nt.get())
        bank = nh.toan_bo()
        ph = nh.loc_theo_nguyen_to(bank, nt)
        if not ph:
            messagebox.showinfo("XRD", "Không có pha nào trong ngân hàng chứa đúng các nguyên tố này.", parent=self.w)
            return
        ds, snr = self._so(self.v_ds, "dung sai", 0.15), self._so(self.v_snr, "ngưỡng", 5.0)
        self.v_tt.set("Đang phân tích...")
        self.w.update_idletasks()
        try:
            self.kq = [xrd.phan_tich_mau(m, ph, self.v_nguon.get(), snr, ds, tat_ca_pha=bank) for m in mau]
        except Exception as e:
            messagebox.showerror("XRD", f"Lỗi khi phân tích: {e}", parent=self.w)
            return
        self.ss = xrd.so_sanh(self.kq, self.v_chuan.get() or None, ds)
        self.txt_bc.delete("1.0", "end")
        self.txt_bc.insert("end", "\n\n".join(xrd.bao_cao_mau(r) for r in self.kq))
        self.txt_ss.delete("1.0", "end")
        self.txt_ss.insert("end", xrd.bao_cao_so_sanh(self.ss))
        self.ve_ket_qua()
        tim = []
        for r in self.kq:
            for q in r["chap_nhan"]:
                if q["pha"]["ten"] not in tim:
                    tim.append(q["pha"]["ten"])
        quet = f"tự quét {len(ph)} pha" if not nt else f"giới hạn {'/'.join(nt)} ({len(ph)} pha)"
        self.v_tt.set(f"Xong {len(self.kq)} mẫu ({quet}). Pha xác định được: {', '.join(tim) or 'không có'}. Tab 'So sánh mẫu' cho đỉnh lạ.")

    def so_sanh(self):
        if not self.kq:
            self.phan_tich()
            if not self.kq:
                return
        self.ss = xrd.so_sanh(self.kq, self.v_chuan.get() or None, self._so(self.v_ds, "dung sai", 0.15))
        self.txt_ss.delete("1.0", "end")
        self.txt_ss.insert("end", xrd.bao_cao_so_sanh(self.ss))
        n_moi = sum(len(c["moi"]) for c in self.ss["cac"])
        self.v_tt.set(f"So sánh với '{self.ss['chuan']}': tổng {n_moi} đỉnh mới/lạ ở các mẫu còn lại (xem tab So sánh).")
        messagebox.showinfo("So sánh", xrd.bao_cao_so_sanh(self.ss)[:3000], parent=self.w)

    # ---------- vẽ ----------
    def ve_tho(self):
        self.ax.clear()
        st = xrd.xep_chong([{"mau": m} for m in self.mau_dung()], 1.35, True, 0.5)
        for s in st:
            self.ax.plot(s["x"], s["y"], color=s["mau"], lw=0.9)
            self.ax.text(s["x"].min(), s["offset"] + 0.15, s["ten"], color=s["mau"], fontsize=9, fontweight="bold")
        self.ax.set_yticks([])
        self.ax.set_xlabel("2θ (°)")
        self.cv.draw_idle()

    def ve_ket_qua(self):
        self.ax.clear()
        st = xrd.xep_chong(self.kq, 1.35, True, 0.5)
        kyh = xrd.ky_hieu_pha(self.kq, self.v_chuan.get() or None)
        nhan = []
        for s, r in zip(st, self.kq):
            self.ax.plot(s["x"], s["y"], color=s["mau"], lw=0.9)
            self.ax.text(s["x"].min(), s["offset"] + 0.15, s["ten"], color=s["mau"], fontsize=9, fontweight="bold")
            for g in r["gan"]:
                iy = int(np.argmin(np.abs(s["x"] - g["peak"]["tt"])))
                kh = kyh.get(g["pha"]["pha"]["ten"]) if g["loai"] in ("pha", "goi_y") else None
                nhan.append({"x": g["peak"]["tt"], "y": float(s["y"][iy]), "loai": g["loai"], "hkl": xrd.nhan_hkl(g),
                             "mpl": kh["mpl"] if kh else "", "mau_kh": kh["mau"] if kh else "#cc0000"})
        if self.v_nhan.get():
            xrd.ve_nhan_mpl(self.ax, nhan, [{"ten": v["ngan"], "mpl": v["mpl"], "mau": v["mau"]} for v in kyh.values()],
                            self.ax.get_xlim()[0], self.ax.get_xlim()[1], st[-1]["offset"] + 1.45)
        self.ax.set_yticks([])
        self.ax.set_xlabel("2θ (°)")
        self.cv.draw_idle()

    # ---------- xuất ----------
    def _xuat_file(self, d):
        ten = os.path.splitext(self.v_file.get())[0] or "XRD"
        return xrd.xuat_tat_ca(self.kq, self.ss, d, ten, ve_nhan=self.v_nhan.get()), ten

    def xuat(self):
        if not self.kq:
            messagebox.showinfo("XRD", "Hãy phân tích trước.", parent=self.w)
            return
        d = filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu kết quả")
        if not d:
            return
        p, _ = self._xuat_file(d)
        self.v_tt.set("Đã ghi vào: " + d)
        messagebox.showinfo("XRD", "Đã ghi:\n" + "\n".join(os.path.basename(v) for v in p.values()), parent=self.w)

    def ve_origin(self):
        if not self.kq:
            messagebox.showinfo("XRD", "Hãy phân tích trước.", parent=self.w)
            return
        if self.lenh_origin is None:
            messagebox.showinfo("XRD", "Chưa kết nối được Origin. Dùng 'Xuất CSV + báo cáo + hình...' rồi import file *_xep.csv vào Origin.", parent=self.w)
            return
        d = filedialog.askdirectory(parent=self.w, title="Chọn thư mục lưu kết quả (CSV + dự án Origin)")
        if not d:
            return
        p, ten = self._xuat_file(d)
        lenh = list(self.lenh_origin()) + ["--csv-xep", p["csv_xep"], "--json", p["json"], "--ten", ten, "--thu-muc-ra", d]
        self.v_tt.set("Đang vẽ trong Origin (cần Origin đã cài; cửa sổ Origin sẽ hiện)...")
        kqc = {"xong": False, "out": ""}

        def chay():
            try:
                r = subprocess.run(lenh, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   creationflags=0x08000000 if os.name == "nt" else 0)
                kqc["out"] = (r.stdout or "") + (r.stderr or "")
            except Exception as e:
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

    # ---------- ngân hàng ----------
    def ngan_hang(self):
        t = tk.Toplevel(self.w)
        t.title("Ngân hàng phổ XRD")
        t.geometry("760x520")
        lb = tk.Listbox(t, font=("Consolas", 10), exportselection=False)
        lb.pack(side="left", fill="y", padx=6, pady=6)
        txt = tk.Text(t, font=("Consolas", 10), wrap="word")
        txt.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        fr = ttk.Frame(t)
        fr.pack(side="right", fill="y", padx=6)
        ds = []

        def nap():
            ds[:] = nh.toan_bo()
            lb.delete(0, "end")
            for p in ds:
                lb.insert("end", f"{p['ten']}  [{p.get('nguon', 'tích hợp')}]")

        def xem(_e=None):
            i = lb.curselection()
            if not i:
                return
            p = ds[i[0]]
            lam = nh.NGUON[self.v_nguon.get()][0]
            txt.delete("1.0", "end")
            txt.insert("end", f"{p['ten']}  {p.get('cong_thuc', '')}  PDF: {p.get('pdf') or '-'}\n{p.get('ghi_chu', '')}\n\n  2θ(°)    d(Å)    I(%)  hkl\n")
            for v in nh.vach_pha(p, lam, 5, 120, 2.0):
                txt.insert("end", f"{v['tt']:7.2f} {v['d']:7.4f} {v['I']:6.1f}  {v['hkl']}\n")

        def them_cif():
            f = filedialog.askopenfilename(parent=t, title="Chọn file CIF", filetypes=[("CIF", "*.cif"), ("Tất cả", "*.*")])
            if not f:
                return
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    p = nh.doc_cif(fh.read(), os.path.splitext(os.path.basename(f))[0])
                p["nguon"] = "người dùng (CIF)"
                nd = nh.doc_nguoi_dung()
                nd.append(p)
                nh.luu_nguoi_dung(nd)
            except Exception as e:
                messagebox.showerror("CIF", str(e), parent=t)
                return
            nap()

        def them_vach():
            ten = simpledialog.askstring("Thêm pha", "Tên pha (vd RuO2 PDF 43-1027):", parent=t)
            if not ten:
                return
            ct = simpledialog.askstring("Thêm pha", "Công thức (vd RuO2):", parent=t) or ""
            top = tk.Toplevel(t)
            top.title("Bảng vạch")
            ttk.Label(top, text="Mỗi dòng: 2theta(Cu Kα1)  I  hkl   (hoặc d=2.03  I  hkl)").pack(padx=6, pady=4)
            tx = tk.Text(top, width=50, height=14, font=("Consolas", 10))
            tx.pack(padx=6)

            def luu():
                try:
                    p = nh.pha_tu_danh_sach_vach(ten, ct, tx.get("1.0", "end"))
                    nd = nh.doc_nguoi_dung()
                    nd.append(p)
                    nh.luu_nguoi_dung(nd)
                except Exception as e:
                    messagebox.showerror("Pha", str(e), parent=top)
                    return
                top.destroy()
                nap()
            ttk.Button(top, text="Lưu", command=luu).pack(pady=6)

        def xoa():
            i = lb.curselection()
            if not i:
                return
            p = ds[i[0]]
            nd = nh.doc_nguoi_dung()
            moi = [q for q in nd if q["ten"] != p["ten"]]
            if len(moi) == len(nd):
                messagebox.showinfo("Ngân hàng", "Pha tích hợp sẵn không xoá được (chỉ xoá pha do bạn thêm).", parent=t)
                return
            nh.luu_nguoi_dung(moi)
            nap()
        lb.bind("<<ListboxSelect>>", xem)
        for ten, lenh in (("Thêm từ file CIF...", them_cif), ("Thêm từ bảng vạch (thẻ PDF)...", them_vach), ("Xoá pha đã thêm", xoa)):
            ttk.Button(fr, text=ten, command=lenh).pack(fill="x", pady=3)
        nap()
