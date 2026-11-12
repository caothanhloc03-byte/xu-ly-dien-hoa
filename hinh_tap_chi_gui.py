# -*- coding: utf-8 -*-
"""Phần giao diện cho hình ghép theo tạp chí: tóm tắt quy cách, xem quy cách chi tiết, tùy chọn định dạng."""
import tkinter as tk
from tkinter import ttk

import hinh_tap_chi as htc

COT = ["Cột đơn", "Cột 1.5", "Cột đôi"]


def ma_cot(app):
    t = app.hinh_cot.get()
    return 1 if t.startswith("Cột đơn") else (15 if t.startswith("Cột 1.5") else 2)


def tom_tat(app):
    m = htc.mau(app.hinh_tap_chi.get())
    cot = ma_cot(app)
    w = htc.rong_cm(m, cot)
    dpi = app.hinh_dpi.get().strip() or str(m["dpi"])
    mf = f" · chữ ≥ {m['min_font']:g} pt" if m.get("min_font") else ""
    ghi = " (tạp chí không có 1.5 cột: dùng cột đôi)" if cot == 15 and not m.get("rd") else ""
    app.tom_tat_tap_chi.set(f"{m['ten']}: {w:g} cm rộng · cao ≤ {m['cao']:g} cm{mf} · {dpi} dpi{ghi}")


def mo_quy_cach(app):
    m = htc.mau(app.hinh_tap_chi.get())
    top = tk.Toplevel(app.root)
    top.title(f"Quy cách hình: {m['ten']}")
    t = tk.Text(top, width=90, height=14, wrap="word")
    t.pack(fill="both", expand=True, padx=6, pady=6)
    dong = [f"Cột đơn {m['don']:g} cm" + (f" · 1.5 cột {m['rd']:g} cm" if m.get("rd") else "") + f" · cột đôi {m['doi']:g} cm · cao tối đa {m['cao']:g} cm",
            f"Chữ app dùng (pt): số trục {m['tick']:g} · nhãn trục {htc.kieu_chu(m)['nhan']:g} · chú thích {htc.kieu_chu(m)['ct']:g} · nhãn ô {m['nhan_o']:g} (đậm)",
            f"Nét dữ liệu {m['lw']:g} pt · khung {m['khung']:g} pt · {m['dpi']} dpi", ""] + m["ghi_chu"]
    if m["nguon"]:
        dong += ["", "Nguồn (trang hướng dẫn tác giả): " + m["nguon"]]
    dong += ["", "Sau mỗi lần xuất, app ghi file Hinh_bai_bao_kiem_tra_tap_chi.txt đối chiếu hình thực tế với các số trên.",
             "Quy cách có thể thay đổi và nhiều tạp chí trong cùng nhà xuất bản có quy cách riêng: luôn đối chiếu hướng dẫn tác giả của tạp chí bạn nộp."]
    t.insert("1.0", "\n".join(dong))
    t.config(state="disabled")


def mo_tuy_chon(app):
    top = tk.Toplevel(app.root)
    top.title("Tùy chọn hình ghép")
    f = ttk.Frame(top, padding=8)
    f.pack()
    for c, (nh, b) in enumerate((("PNG", app.hb_png), ("PDF", app.hb_pdf), ("TIFF", app.hb_tiff))):
        ttk.Checkbutton(f, text=nh, variable=b).grid(row=0, column=c, sticky="w", padx=6)
    ttk.Label(f, text="dpi (trống = theo tạp chí):").grid(row=1, column=0, columnspan=2, sticky="e", pady=4)
    ttk.Entry(f, textvariable=app.hinh_dpi, width=7).grid(row=1, column=2, sticky="w")
    ttk.Label(f, text="Chữ ô:").grid(row=2, column=0, sticky="e")
    ttk.Combobox(f, textvariable=app.hinh_chu, values=["(A) (B) (C)", "(a) (b) (c)"], state="readonly", width=12).grid(row=2, column=1, columnspan=2, sticky="w", pady=4)
    ttk.Label(f, foreground="#666", wraplength=300, justify="left",
              text="Nature luôn dùng chữ thường a, b, c theo quy định. Đồ thị nên nộp dạng PDF (vector); ảnh raster theo dpi của tạp chí.").grid(row=3, column=0, columnspan=3, pady=4)
    ttk.Button(f, text="Đóng", command=lambda: (app.luu_cai_dat(), tom_tat(app), top.destroy())).grid(row=4, column=2, sticky="e")
