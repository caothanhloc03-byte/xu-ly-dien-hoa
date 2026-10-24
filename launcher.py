# -*- coding: utf-8 -*-
"""
Trình khởi động (đây là file được đóng gói thành DienHoaOrigin.exe).

exe chỉ chứa Python + thư viện (numpy, pandas, matplotlib, originpro...).
Mã nguồn thật nằm ở thư mục "ma_nguon" cạnh exe nên có thể cập nhật từ GitHub
mà KHÔNG cần build lại exe.
"""
import importlib.util
import os
import sys
from importlib.machinery import SourceFileLoader

BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "ma_nguon") if os.path.isdir(os.path.join(BASE, "ma_nguon")) else BASE


def _gom_thu_vien():
    """Không bao giờ được gọi - chỉ để PyInstaller biết cần gom những thư viện này vào exe."""
    import argparse, glob, json, queue, shutil, subprocess, tempfile, threading, urllib.request, zipfile  # noqa
    import tkinter, tkinter.ttk, tkinter.colorchooser, tkinter.filedialog  # noqa
    import tkinter.messagebox, tkinter.scrolledtext, tkinter.simpledialog  # noqa
    import tkinter.font, hashlib, datetime, platform, ctypes, csv, re, math, random  # noqa
    import numpy, pandas, matplotlib, matplotlib.pyplot  # noqa
    import openpyxl  # noqa
    try:
        import tkinterdnd2  # noqa  (keo-tha file, tuy chon)
    except ImportError:
        pass
    import originpro  # noqa


def main():
    sys.path.insert(0, SRC)
    duong = os.path.join(SRC, "giao_dien.pyw")
    if not os.path.exists(duong):
        duong = os.path.join(SRC, "giao_dien.py")
    if not os.path.exists(duong):
        try:
            import tkinter.messagebox as mb
            mb.showerror("Thiếu file", f"Không tìm thấy giao_dien.pyw trong:\n{SRC}")
        except Exception:
            print("Khong tim thay giao_dien.pyw trong", SRC)
        return
    loader = SourceFileLoader("giao_dien", duong)
    spec = importlib.util.spec_from_file_location("giao_dien", duong, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["giao_dien"] = mod
    loader.exec_module(mod)
    mod.main()


if __name__ == "__main__":
    main()
