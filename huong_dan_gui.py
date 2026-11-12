# -*- coding: utf-8 -*-
"""Cửa sổ 'Hướng dẫn theo phép đo': gõ tên phép đo (LSV, tafel, ragone...) → các bước làm trong app (tick ☐ từng bước),
công thức, tiêu chí, lỗi thường gặp, kèm giá trị đang đặt trong app. Nội dung nằm ở huong_dan_phep_do.py."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import huong_dan_phep_do as hd

DA_LAM = {}  # {topic_id: {chỉ số bước đã tick}} — giữ trong suốt phiên làm việc


class CuaSoHuongDan:
    def __init__(self, root, lay_ctx=None, hanh_dong=None, mo_dau=""):
        """lay_ctx() → dict giá trị hiện tại của app; hanh_dong = {'loai': f(tên_loại), 'cong_cu': f(mã)}."""
        self.lay_ctx = lay_ctx or (lambda: {})
        self.hanh_dong = hanh_dong or {}
        self.id_hien = None
        self.ds_id = []
        w = self.w = tk.Toplevel(root)
        w.title("Hướng dẫn theo phép đo")
        w.geometry("980x680")
        w.minsize(640, 420)

        top = ttk.Frame(w, padding=(8, 8, 8, 2))
        top.pack(fill="x")
        ttk.Label(top, text="Nhập tên phép đo:").pack(side="left")
        self.tu = tk.StringVar(value=mo_dau)
        self.o = ttk.Entry(top, textvariable=self.tu, width=30)
        self.o.pack(side="left", padx=6)
        self.o.bind("<Return>", lambda e: self.chon_dau())
        self.o.bind("<Down>", lambda e: (self.lb.focus_set(), self.lb.selection_set(0) if self.lb.size() else None))
        ttk.Label(top, text="ví dụ: LSV · CV · Tafel · ECSA · EIS · i-t · GCD · Ragone · XPS · XRD · nộp bài",
                  foreground="#666666").pack(side="left", padx=6)
        self.tu.trace_add("write", lambda *a: self.loc())

        pw = ttk.PanedWindow(w, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=8, pady=4)
        kt = ttk.Frame(pw)
        self.lb = tk.Listbox(kt, width=30, exportselection=False, activestyle="none")
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.chon_lb())
        pw.add(kt, weight=1)

        kp = ttk.Frame(pw)
        self.hang_nut = ttk.Frame(kp)
        self.hang_nut.pack(fill="x", pady=(0, 4))
        self.t = tk.Text(kp, wrap="word", font=("TkDefaultFont", 10), padx=10, pady=8, cursor="arrow")
        sb = ttk.Scrollbar(kp, command=self.t.yview)
        self.t.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.t.pack(fill="both", expand=True)
        pw.add(kp, weight=4)
        t = self.t
        t.tag_configure("h1", font=("TkDefaultFont", 15, "bold"), spacing1=4, spacing3=6, foreground="#1f3864")
        t.tag_configure("h2", font=("TkDefaultFont", 11, "bold"), spacing1=12, spacing3=3, foreground="#1f3864")
        t.tag_configure("p", spacing3=4)
        t.tag_configure("li", lmargin1=14, lmargin2=30, spacing3=2)
        t.tag_configure("buoc", lmargin1=6, lmargin2=34, spacing3=3)
        t.tag_configure("xong", foreground="#7a7a7a", overstrike=True)
        t.tag_configure("hop", font=("TkDefaultFont", 11, "bold"), foreground="#2e75b6")
        t.tag_configure("ct", font=("Consolas", 10), background="#f0f4fa", lmargin1=14, lmargin2=30, spacing3=3)
        t.tag_configure("canh", lmargin1=14, lmargin2=30, foreground="#9c3a00", spacing3=2)
        t.tag_configure("thuc", lmargin1=14, lmargin2=30, background="#fff8e1", spacing3=2)
        t.config(state="disabled")

        self.loc()
        if mo_dau and self.ds_id:
            self.chon(self.ds_id[0])
        elif self.ds_id:
            self.lb.selection_set(0)
        self.o.focus_set()

    # ---------- danh sách ----------
    def loc(self):
        q = self.tu.get().strip()
        self.ds_id = hd.tim(q, 30) if q else [i for i, _ in hd.danh_sach()]
        self.lb.delete(0, "end")
        for i in self.ds_id:
            self.lb.insert("end", hd.THEO_ID[i]["ten"])
        if self.ds_id and q:
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(0)
            self.chon(self.ds_id[0])
        elif not self.ds_id:
            self.hien_trong(q)

    def chon_dau(self):
        if self.ds_id:
            self.chon(self.ds_id[0])

    def chon_lb(self):
        s = self.lb.curselection()
        if s and s[0] < len(self.ds_id):
            self.chon(self.ds_id[s[0]])

    def hien_trong(self, q):
        self.id_hien = None
        self.xoa_nut()
        self.t.config(state="normal")
        self.t.delete("1.0", "end")
        self.t.insert("end", f"Không có mục nào khớp với '{q}'.\n", "h2")
        self.t.insert("end", "Thử gõ: LSV, CV, i-t, EIS, Tafel, ECSA, bù iR, so sánh, FE, TOF, GCD, Csp, Ragone, retention, CE, XPS, XRD, HR-TEM, "
                             "nộp bài, hình tạp chí, quy đổi.\n", "p")
        self.t.config(state="disabled")

    # ---------- hiển thị ----------
    def xoa_nut(self):
        for c in self.hang_nut.winfo_children():
            c.destroy()

    def chon(self, tid):
        self.id_hien = tid
        self.ve()

    def ve(self):
        tid = self.id_hien
        if not tid:
            return
        try:
            ctx = self.lay_ctx() or {}
        except Exception:
            ctx = {}
        t = self.t
        t.config(state="normal")
        t.delete("1.0", "end")
        da = DA_LAM.setdefault(tid, set())
        n = 0
        for kieu, nd in hd.khoi(tid, ctx):
            if kieu == "h1":
                t.insert("end", nd + "\n", "h1")
            elif kieu == "h2":
                t.insert("end", nd + "\n", "h2")
            elif kieu == "p":
                t.insert("end", nd + "\n", "p")
            elif kieu == "buoc":
                n += 1
                chi_so = n
                tag = f"b{chi_so}"
                xong = chi_so in da
                dau = t.index("end-1c")
                t.insert("end", "[x] " if xong else "[ ] ", ("hop", tag))
                t.insert("end", f"{chi_so}. {nd}\n", ("buoc", tag) + (("xong",) if xong else ()))
                t.tag_bind(tag, "<Button-1>", lambda e, k=chi_so: self.bam_buoc(k))
                t.tag_bind(tag, "<Enter>", lambda e: t.config(cursor="hand2"))
                t.tag_bind(tag, "<Leave>", lambda e: t.config(cursor="arrow"))
            elif kieu == "ct":
                t.insert("end", nd + "\n", "ct")
            elif kieu == "canh":
                t.insert("end", "⚠ " + nd + "\n", "canh")
            else:
                tag = "thuc" if nd and any(x in nd for x in ("Đang", "đang", "I mục tiêu", "Vùng đang", "Trong danh sách")) else "li"
                t.insert("end", "• " + nd + "\n", tag)
        t.config(state="disabled")
        self.ve_nut(tid, n, len(da))

    def bam_buoc(self, k):
        da = DA_LAM.setdefault(self.id_hien, set())
        da.symmetric_difference_update({k})
        y = self.t.yview()[0]
        self.ve()
        self.t.yview_moveto(y)

    def ve_nut(self, tid, tong, xong):
        self.xoa_nut()
        top = hd.THEO_ID[tid]
        h = self.hang_nut
        ttk.Label(h, text=f"Đã làm {len(DA_LAM.get(tid, ()))}/{tong} bước").pack(side="left", padx=(0, 8))
        ttk.Button(h, text="Bỏ tick hết", command=self.bo_tick).pack(side="left", padx=2)
        loai = top.get("loai_app")
        if loai and self.hanh_dong.get("loai"):
            ttk.Button(h, text=f"Đặt Loại phép đo = {loai}", command=lambda: self.hanh_dong["loai"](loai)).pack(side="left", padx=2)
        cc = top.get("cong_cu")
        if cc and self.hanh_dong.get("cong_cu"):
            ten = {"qs": "Qs-LSV & TOF", "gcd": "Siêu tụ lai & Pin", "xps": "XPS", "xrd": "XRD", "hrtem": "HR-TEM"}.get(cc, cc)
            ttk.Button(h, text=f"Mở công cụ {ten}", command=lambda: self.hanh_dong["cong_cu"](cc)).pack(side="left", padx=2)
        ttk.Button(h, text="Sao chép", command=self.sao_chep).pack(side="right", padx=2)
        ttk.Button(h, text="Lưu .txt...", command=self.luu).pack(side="right", padx=2)

    def bo_tick(self):
        DA_LAM[self.id_hien] = set()
        self.ve()

    def _van_ban(self):
        try:
            ctx = self.lay_ctx() or {}
        except Exception:
            ctx = {}
        return hd.van_ban(self.id_hien, ctx)

    def sao_chep(self):
        if not self.id_hien:
            return
        self.w.clipboard_clear()
        self.w.clipboard_append(self._van_ban())

    def luu(self):
        if not self.id_hien:
            return
        p = filedialog.asksaveasfilename(parent=self.w, title="Lưu hướng dẫn", defaultextension=".txt",
                                         initialfile=f"huong_dan_{self.id_hien.replace(' ', '_')}.txt", filetypes=[("Văn bản", "*.txt")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self._van_ban() + "\n")
        except OSError as e:
            messagebox.showerror("Lưu hướng dẫn", str(e), parent=self.w)
