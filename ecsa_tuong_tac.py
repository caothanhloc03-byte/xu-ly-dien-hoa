# -*- coding: utf-8 -*-
"""
ECSA TƯƠNG TÁC: vẽ các đường CV, kéo chuột để chọn điện thế lấy dòng điện dung, tick/bỏ tick từng tốc độ quét,
Cdl - R² - ECSA cập nhật ngay. Phần tính toán là Python thuần (không cần numpy) để cửa sổ mở nhanh;
công thức giống hệt xu_ly_dien_hoa.tinh_ecsa:  Cdl = hệ số góc của (Ja - Jc)/2 theo tốc độ quét (V/s).
"""
import bisect
import math


# ---------------------------------------------------------------- tính toán thuần
def noi_suy(xs, ys, x):
    """Nội suy tuyến tính, xs tăng dần; ngoài biên lấy giá trị biên (giống numpy.interp)."""
    if not xs:
        raise ValueError("không có điểm")
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    k = bisect.bisect_right(xs, x)
    x0, x1 = xs[k - 1], xs[k]
    if x1 == x0:
        return ys[k]
    return ys[k - 1] + (ys[k] - ys[k - 1]) * (x - x0) / (x1 - x0)


def chuan_bi(cv_json):
    """Từ danh sách dict JSON (e, i, a = 1 nếu quét anot) → mỗi file có 2 nhánh đã sắp xếp theo E."""
    kq = []
    for c in cv_json:
        nhanh = {}
        for ten, co in (("a", 1), ("c", 0)):
            p = sorted((e, i) for e, i, h in zip(c["e"], c["i"], c["a"]) if h == co)
            nhanh[ten] = ([x[0] for x in p], [x[1] for x in p])
        if not nhanh["a"][0] or not nhanh["c"][0]:
            continue            # không đủ hai chiều quét -> không dùng cho ECSA
        kq.append({"path": c["path"], "nhan": c.get("nhan", ""), "mau": c.get("mau", "#1f77b4"), "v": float(c["v"]),
                   "e": c["e"], "i": c["i"], "a": c["a"], "nhanh": nhanh})
    return kq


def vung_chung(cac, bo_qua=()):
    dung = [c for c in cac if c["path"] not in bo_qua] or cac
    lo = max(min(c["e"]) for c in dung)
    hi = min(max(c["e"]) for c in dung)
    return lo, hi


def tinh(cac, e, cs, bo_qua=()):
    """Trả về dict: diem (mỗi file), he_so (Cdl, mF/cm²), tung, r2, ecsa; None nếu chưa đủ 2 điểm khác tốc độ."""
    diem = []
    for c in cac:
        ja = noi_suy(*c["nhanh"]["a"], e)
        jc = noi_suy(*c["nhanh"]["c"], e)
        diem.append({"path": c["path"], "nhan": c["nhan"], "v": c["v"], "ja": ja, "jc": jc, "y": (ja - jc) / 2,
                     "dung": c["path"] not in bo_qua})
    kq = {"diem": diem, "he_so": None, "tung": None, "r2": None, "ecsa": None, "n": 0}
    d = [x for x in diem if x["dung"]]
    kq["n"] = len(d)
    if len(d) >= 2 and len({x["v"] for x in d}) >= 2:
        xs = [x["v"] / 1000.0 for x in d]
        ys = [x["y"] for x in d]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        he_so = sxy / sxx
        tung = my - he_so * mx
        sst = sum((y - my) ** 2 for y in ys)
        ssr = sum((y - (he_so * x + tung)) ** 2 for x, y in zip(xs, ys))
        kq.update(he_so=he_so, tung=tung, r2=(1 - ssr / sst) if sst > 0 else None,
                  ecsa=(he_so / cs) if cs else None)
    return kq


def tu_dong_e(cac, cs, bo_qua=(), so_buoc=200):
    """Quét điện thế trong vùng chung, trả về E cho R² cao nhất (chỉ xét Cdl > 0). None nếu không tìm được."""
    lo, hi = vung_chung(cac, bo_qua)
    if hi <= lo:
        return None
    tot = None
    for k in range(so_buoc + 1):
        e = lo + (hi - lo) * k / so_buoc
        r = tinh(cac, e, cs, bo_qua)
        if r["he_so"] is None or r["r2"] is None or r["he_so"] <= 0:
            continue
        if tot is None or r["r2"] > tot[0] + 1e-12:
            tot = (r["r2"], e)
    return tot[1] if tot else None


def nice_ticks(a, b, n=5):
    if not b > a:
        return [a]
    tho = (b - a) / n
    mu = 10 ** math.floor(math.log10(tho))
    buoc = mu
    for m in (1, 2, 2.5, 5, 10):
        if tho <= m * mu:
            buoc = m * mu
            break
    t = math.ceil(a / buoc - 1e-9) * buoc
    ra = []
    while t <= b + 1e-9:
        ra.append(round(t, 10))
        t += buoc
    return ra


# ---------------------------------------------------------------- cửa sổ Tk
class CuaSo:
    """ap_dung(e, bo_qua:set[path]) được gọi khi bấm 'Dùng kết quả này'."""

    def __init__(self, root, cv_json, e0, cs, bo_qua, ap_dung):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.cac = chuan_bi(cv_json)
        if len(self.cac) < 2:
            raise ValueError("Cần ít nhất 2 file CV (có cả chiều quét anot và catot) để làm ECSA.")
        self.cs = cs
        self.ap_dung = ap_dung
        self.bo = {c["path"]: tk.BooleanVar(value=(c["path"] not in bo_qua)) for c in self.cac}
        lo, hi = vung_chung(self.cac, self.bo_qua())
        self.vung = (lo, hi)
        self.e = e0 if e0 is not None else ((lo + hi) / 2 if hi > lo else (min(min(c["e"]) for c in self.cac) +
                                                                              max(max(c["e"]) for c in self.cac)) / 2)
        self.w = tk.Toplevel(root)
        self.w.title("ECSA - chọn điện thế bằng đồ thị")
        self.w.geometry("1060x640")
        self.w.minsize(820, 520)
        try:
            self.w.transient(root)
        except Exception:
            pass
        self.w.columnconfigure(0, weight=3)
        self.w.columnconfigure(1, weight=2)
        self.w.rowconfigure(1, weight=1)
        ttk.Label(self.w, justify="left", foreground="#444",
                  text="Bấm hoặc kéo chuột trên đồ thị CV để chọn điện thế lấy dòng điện dung (chọn vùng phẳng, KHÔNG có pic oxi hóa-khử). "
                       "Bỏ tick tốc độ quét nào lệch (outlier) để loại khỏi phép fit - file không bị xóa."
                  ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2))
        self.cv = tk.Canvas(self.w, bg="white", highlightthickness=1, highlightbackground="#bbb", cursor="sb_h_double_arrow")
        self.cv.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=6)
        phai = ttk.Frame(self.w)
        phai.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=6)
        phai.columnconfigure(0, weight=1)
        phai.rowconfigure(0, weight=1)
        self.fit = tk.Canvas(phai, bg="white", highlightthickness=1, highlightbackground="#bbb", height=260)
        self.fit.grid(row=0, column=0, sticky="nsew")
        kh = ttk.LabelFrame(phai, text="Tốc độ quét dùng để fit")
        kh.grid(row=1, column=0, sticky="ew", pady=6)
        for k, c in enumerate(sorted(self.cac, key=lambda x: x["v"])):
            ttk.Checkbutton(kh, text=f"{c['v']:g} mV/s  -  {c['nhan']}", variable=self.bo[c["path"]], command=self.ve_lai
                            ).grid(row=k % 6, column=k // 6, sticky="w", padx=8, pady=1)
        hang = ttk.Frame(phai)
        hang.grid(row=2, column=0, sticky="ew")
        ttk.Label(hang, text="E lấy dòng (V):").pack(side="left")
        self.bien_e = tk.StringVar(value=f"{self.e:.4f}")
        en = ttk.Entry(hang, textvariable=self.bien_e, width=9)
        en.pack(side="left", padx=4)
        en.bind("<Return>", self.nhap_e)
        en.bind("<FocusOut>", self.nhap_e)
        ttk.Button(hang, text="Gợi ý E có R² cao nhất", command=self.goi_y).pack(side="left", padx=6)
        self.kq_nhan = ttk.Label(phai, text="", font=("Segoe UI", 11, "bold"), justify="left")
        self.kq_nhan.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.ghi_chu = ttk.Label(phai, text="", foreground="#a05a00", wraplength=380, justify="left")
        self.ghi_chu.grid(row=4, column=0, sticky="w")
        nut = ttk.Frame(self.w)
        nut.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(nut, text="Dùng kết quả này (ghi vào ô E và danh sách file)", command=self.dung).pack(side="left", padx=4)
        ttk.Button(nut, text="Đóng", command=self.w.destroy).pack(side="left", padx=4)
        for ev in ("<Button-1>", "<B1-Motion>"):
            self.cv.bind(ev, self.keo)
        self.cv.bind("<Configure>", lambda e: self.ve_lai())
        self.fit.bind("<Configure>", lambda e: self.ve_lai())
        self.ve_lai()

    # ---- trạng thái
    def bo_qua(self):
        return {p for p, v in self.bo.items() if not v.get()}

    def dat_e(self, e):
        lo = min(min(c["e"]) for c in self.cac)
        hi = max(max(c["e"]) for c in self.cac)
        self.e = min(max(e, lo), hi)
        self.bien_e.set(f"{self.e:.4f}")
        self.ve_lai()

    def nhap_e(self, _=None):
        try:
            self.dat_e(float(self.bien_e.get().replace(",", ".")))
        except ValueError:
            self.bien_e.set(f"{self.e:.4f}")

    def goi_y(self):
        e = tu_dong_e(self.cac, self.cs, self.bo_qua())
        if e is None:
            self.ghi_chu.config(text="Không tìm được điện thế cho Cdl dương và R² hợp lệ (kiểm tra tốc độ quét đã tick).")
        else:
            self.dat_e(e)

    def dung(self):
        if self.ap_dung:
            self.ap_dung(self.e, self.bo_qua())
        self.w.destroy()

    # ---- vẽ
    def keo(self, ev):
        if not hasattr(self, "hop_cv"):
            return
        l, t, r, b, x0, x1 = self.hop_cv
        if r <= l:
            return
        self.dat_e(x0 + (min(max(ev.x, l), r) - l) / (r - l) * (x1 - x0))

    def _khung(self, cn, l, t, r, b, x0, x1, y0, y1, nx, ny):
        cn.create_rectangle(l, t, r, b, outline="#222")
        for v in nice_ticks(x0, x1):
            x = l + (v - x0) / (x1 - x0) * (r - l)
            cn.create_line(x, b, x, b + 4, fill="#222")
            cn.create_text(x, b + 6, text=f"{v:.4g}", anchor="n", font=("Segoe UI", 8))
        for v in nice_ticks(y0, y1):
            y = b - (v - y0) / (y1 - y0) * (b - t)
            cn.create_line(l - 4, y, l, y, fill="#222")
            cn.create_text(l - 6, y, text=f"{v:.4g}", anchor="e", font=("Segoe UI", 8))
        cn.create_text((l + r) / 2, b + 24, text=nx, font=("Segoe UI", 9))
        cn.create_text(12, (t + b) / 2, text=ny, angle=90, font=("Segoe UI", 9))

    def ve_lai(self):
        r = tinh(self.cac, self.e, self.cs, self.bo_qua())
        self._ve_cv(r)
        self._ve_fit(r)
        if r["he_so"] is None:
            self.kq_nhan.config(text="Cần tick ít nhất 2 tốc độ quét khác nhau.")
            self.ghi_chu.config(text="")
            return
        txt = f"Cdl = {r['he_so']:.4g} mF/cm²\nR² = {r['r2']:.4f}" if r["r2"] is not None else f"Cdl = {r['he_so']:.4g} mF/cm²"
        if r["ecsa"] is not None:
            txt += f"\nECSA = {r['ecsa']:.4g} cm² (Cs = {self.cs:g} mF/cm²)"
        self.kq_nhan.config(text=txt)
        ghi = []
        if r["r2"] is not None and r["r2"] < 0.98:
            ghi.append("R² < 0.98: thử đổi điện thế sang vùng phẳng hơn hoặc bỏ tick tốc độ quét lệch.")
        if r["he_so"] <= 0:
            ghi.append("Cdl ≤ 0: điện thế đang nằm trong vùng có phản ứng faraday; hãy chọn vùng khác.")
        if r["n"] == 2:
            ghi.append("Chỉ còn 2 điểm: R² luôn bằng 1, không còn ý nghĩa thống kê.")
        self.ghi_chu.config(text="\n".join(ghi))

    def _ve_cv(self, r):
        cn = self.cv
        cn.delete("all")
        W, H = max(cn.winfo_width(), 200), max(cn.winfo_height(), 160)
        l, t, rr, b = 62, 14, W - 16, H - 42
        xs = [e for c in self.cac for e in c["e"]]
        ys = [i for c in self.cac for i in c["i"]]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        if y1 <= y0:
            y1 = y0 + 1
        pad = (y1 - y0) * 0.05
        y0, y1 = y0 - pad, y1 + pad
        if x1 <= x0:
            x1 = x0 + 1
        self.hop_cv = (l, t, rr, b, x0, x1)
        px = lambda v: l + (v - x0) / (x1 - x0) * (rr - l)
        py = lambda v: b - (v - y0) / (y1 - y0) * (b - t)
        self._khung(cn, l, t, rr, b, x0, x1, y0, y1, "E (V vs RHE)", "I (mA/cm²)")
        bo = self.bo_qua()
        for c in self.cac:
            n = len(c["e"])
            buoc = max(1, n // 700)
            pts = []
            for k in range(0, n, buoc):
                pts += [px(c["e"][k]), py(c["i"][k])]
            if len(pts) >= 4:
                if c["path"] in bo:
                    cn.create_line(*pts, fill="#c8c8c8", dash=(3, 3))
                else:
                    cn.create_line(*pts, fill=c["mau"], width=1.6)
        xe = px(self.e)
        cn.create_line(xe, t, xe, b, fill="#d00000", width=2)
        cn.create_text(xe + 4, t + 8, text=f"{self.e:.3f} V", anchor="w", fill="#d00000", font=("Segoe UI", 9, "bold"))
        for d in r["diem"]:
            if d["dung"]:
                for j in (d["ja"], d["jc"]):
                    cn.create_oval(xe - 3, py(j) - 3, xe + 3, py(j) + 3, fill="#d00000", outline="white")

    def _ve_fit(self, r):
        cn = self.fit
        cn.delete("all")
        W, H = max(cn.winfo_width(), 200), max(cn.winfo_height(), 160)
        l, t, rr, b = 58, 12, W - 14, H - 40
        vs = [d["v"] for d in r["diem"]]
        ys = [d["y"] for d in r["diem"]]
        x0, x1 = 0.0, max(vs) * 1.08
        y0, y1 = min(0.0, min(ys)), max(ys)
        if r["he_so"] is not None:
            y1 = max(y1, r["he_so"] * x1 / 1000 + r["tung"])
            y0 = min(y0, r["tung"])
        if y1 <= y0:
            y1 = y0 + 1
        pad = (y1 - y0) * 0.08
        y1 += pad
        y0 = y0 - pad if y0 < 0 else y0
        px = lambda v: l + (v - x0) / (x1 - x0) * (rr - l)
        py = lambda v: b - (v - y0) / (y1 - y0) * (b - t)
        self._khung(cn, l, t, rr, b, x0, x1, y0, y1, "Tốc độ quét (mV/s)", "(Ja − Jc)/2 (mA/cm²)")
        if r["he_so"] is not None:
            cn.create_line(px(x0), py(r["tung"]), px(x1), py(r["he_so"] * x1 / 1000 + r["tung"]), fill="#1f4e9c", width=2)
        for d in r["diem"]:
            if d["dung"]:
                cn.create_oval(px(d["v"]) - 5, py(d["y"]) - 5, px(d["v"]) + 5, py(d["y"]) + 5, fill="#1f4e9c", outline="white")
            else:
                cn.create_oval(px(d["v"]) - 5, py(d["y"]) - 5, px(d["v"]) + 5, py(d["y"]) + 5, outline="#999", width=2)
