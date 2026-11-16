# -*- coding: utf-8 -*-
"""Giao diện chung của Echem Studio: logo cho MỌI cửa sổ (kể cả cửa sổ con / hộp thoại), dải logo, màu chủ đạo.
Không đổi bố cục cũ; chỉ tinh chỉnh bề ngoài. Mọi hàm đều không ném lỗi (thiếu logo/PIL/tk cũ vẫn chạy)."""
import os
import sys
import tkinter as tk
from tkinter import ttk

THU_MUC = os.path.dirname(os.path.abspath(__file__))
XANH = "#1B6CB0"            # màu chủ đạo lấy từ logo
XANH_DAM = "#14558C"
XANH_NHAT = "#E6F0FA"
CHU = "#1F2A37"
CHU_PHU = "#5B6778"
VIEN = "#D3DAE3"
NEN_LOG = "#14202E"
CHU_LOG = "#CFE0F2"
_anh = {}                  # giữ tham chiếu ảnh (tk sẽ xóa ảnh nếu mất tham chiếu)
_da_va = False


def _duong(ten):
    for d in (THU_MUC, getattr(sys, "_MEIPASS", ""), os.path.dirname(sys.executable)):
        p = os.path.join(d, ten) if d else ""
        if p and os.path.isfile(p):
            return p
    return None


def anh_logo(root, kich_thuoc=32):
    """PhotoImage logo vuông kich_thuoc px (None nếu không có). Thu nhỏ bằng PIL nếu có, không thì subsample."""
    khoa = ("logo", kich_thuoc)
    if khoa in _anh:
        return _anh[khoa]
    p = _duong("logo_256.png") or _duong("logo_1024.png")
    img = None
    if p:
        try:
            from PIL import Image, ImageTk
            im = Image.open(p).convert("RGBA").resize((kich_thuoc, kich_thuoc), Image.LANCZOS)
            img = ImageTk.PhotoImage(im, master=root)
        except Exception:
            try:
                goc = tk.PhotoImage(file=p, master=root)
                k = max(1, goc.width() // kich_thuoc)
                img = goc.subsample(k, k)
            except Exception:
                img = None
    _anh[khoa] = img
    return img


def gan_bieu_tuong(cua_so):
    """Đặt logo cho 1 cửa sổ (thanh tiêu đề + thanh tác vụ). Windows: logo.ico; nơi khác: iconphoto."""
    try:
        ico = _duong("logo.ico")
        if ico and sys.platform.startswith("win"):
            cua_so.iconbitmap(ico)
            return True
    except Exception:
        pass
    try:
        a = anh_logo(cua_so, 64)
        if a is not None:
            cua_so.iconphoto(False, a)
            return True
    except Exception:
        pass
    return False


def cai_logo_toan_app(root):
    """Gọi 1 lần khi khởi động. Mọi tk.Toplevel tạo sau đó (công cụ, hộp thoại, cửa sổ phụ) đều có logo."""
    global _da_va
    gan_bieu_tuong(root)
    try:
        ico = _duong("logo.ico")
        if ico and sys.platform.startswith("win"):
            root.iconbitmap(default=ico)        # mặc định cho mọi cửa sổ con và hộp thoại hệ thống
    except Exception:
        pass
    if _da_va:
        return
    _da_va = True
    goc_init = tk.Toplevel.__init__

    def init_moi(self, *a, **k):
        goc_init(self, *a, **k)
        try:
            if not self.overrideredirect():     # bỏ qua tooltip / cửa sổ không viền
                gan_bieu_tuong(self)
        except Exception:
            pass
    tk.Toplevel.__init__ = init_moi


def dai_logo(cha, tieu_de, phu_de="", kich_thuoc=36):
    """Dải đầu cửa sổ: logo + tiêu đề + dòng phụ. Trả về tk.Frame (người gọi tự pack/grid)."""
    f = tk.Frame(cha, bg=XANH_NHAT, highlightthickness=0)
    a = anh_logo(cha, kich_thuoc)
    if a is not None:
        l = tk.Label(f, image=a, bg=XANH_NHAT)
        l.image = a
        l.pack(side="left", padx=(12, 8), pady=6)
    t = tk.Frame(f, bg=XANH_NHAT)
    t.pack(side="left", pady=6)
    tk.Label(t, text=tieu_de, bg=XANH_NHAT, fg=CHU, font=("TkDefaultFont", 12, "bold"), anchor="w").pack(anchor="w")
    if phu_de:
        tk.Label(t, text=phu_de, bg=XANH_NHAT, fg=CHU_PHU, font=("TkDefaultFont", 9), anchor="w").pack(anchor="w")
    return f


def ap_kieu(root):
    """Tinh chỉnh ttk nhẹ nhàng, an toàn với mọi theme (không đổi theme)."""
    try:
        s = ttk.Style(root)
        s.configure("TLabelframe.Label", foreground=CHU_PHU, font=("TkDefaultFont", 9, "bold"))
        s.configure("Treeview.Heading", font=("TkDefaultFont", 9, "bold"))
        s.configure("Toolbutton", padding=(12, 5))
    except Exception:
        pass


def nut_chinh(cha, text, command, **kw):
    """Nút hành động chính (xanh, chữ trắng). Là tk.Button nên màu hiển thị đúng cả trên theme Windows."""
    b = tk.Button(cha, text=text, command=command, bg=XANH, fg="white", activebackground=XANH_DAM, activeforeground="white",
                  disabledforeground="#DCE6F1", relief="flat", bd=0, cursor="hand2",
                  font=("TkDefaultFont", 10, "bold"), **kw)
    b.bind("<Enter>", lambda e: b["state"] == "normal" and b.config(bg=XANH_DAM))
    b.bind("<Leave>", lambda e: b.config(bg=XANH if b["state"] == "normal" else "#8FB4D6"))
    return b


def kieu_nhat_ky(text_widget):
    """Khung nhật ký/báo cáo nền tối, chữ sáng; màu thẻ cảnh báo/lỗi/tốt đọc được trên nền tối."""
    try:
        text_widget.config(bg=NEN_LOG, fg=CHU_LOG, insertbackground=CHU_LOG, selectbackground="#2F5E8E",
                           relief="flat", padx=10, pady=8)
        text_widget.tag_configure("canh_bao", foreground="#F2B66B")
        text_widget.tag_configure("loi", foreground="#FF8A80")
        text_widget.tag_configure("tot", foreground="#69DB7C")
    except Exception:
        pass
