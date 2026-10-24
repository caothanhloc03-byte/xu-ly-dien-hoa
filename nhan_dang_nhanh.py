# -*- coding: utf-8 -*-
"""
Nhận dạng NHANH loại phép đo của một file thô (CV / LSV / IT / EIS) bằng Python thuần (không cần numpy/pandas).
Dùng cho cột "Loại" trong bảng file của giao diện. Quy tắc giống xu_ly_dien_hoa.nhan_dang / xu_ly_cv_lsv.
"""
import os


def _doc(duong_dan):
    with open(duong_dan, "r", encoding="utf-8", errors="ignore") as f:
        dong = f.read().splitlines()
    nhan = ""
    if dong and dong[0].startswith("CSStudioFile"):
        p = dong[0].split(",")
        nhan = p[1] if len(p) > 1 else ""
    la_eis = any("Freq (Hz)" in d or "Z'(Ohm" in d for d in dong)
    c1, c2, c3 = [], [], []
    for d in dong:
        phan = d.replace(",", "\t").split()
        if not phan:
            continue
        try:
            if la_eis and len(phan) >= 6:
                v = (float(phan[0]), float(phan[4]), float(phan[5]))
            elif not la_eis and len(phan) >= 3:
                v = tuple(float(x) for x in phan[:3])
            else:
                continue
        except ValueError:
            continue
        c1.append(v[0])
        c2.append(v[1])
        c3.append(v[2])
    return nhan, c1, c2, c3


def _so_doi_chieu(E, nguong=0.002):
    n = len(E)
    if n < 3:
        return 0
    h = 1 if E[min(n - 1, 10)] >= E[0] else -1
    cuc_tri, so_doi = E[0], 0
    for x in E:
        if h == 1:
            if x > cuc_tri:
                cuc_tri = x
            elif cuc_tri - x > nguong:
                h, cuc_tri, so_doi = -1, x, so_doi + 1
        else:
            if x < cuc_tri:
                cuc_tri = x
            elif x - cuc_tri > nguong:
                h, cuc_tri, so_doi = 1, x, so_doi + 1
    return so_doi


def phat_hien(duong_dan):
    """Trả về dict: loai ('CV','LSV','IT','EIS','?'), so_chu_ky (CV), so_diem, mo_ta (chuỗi hiển thị)."""
    try:
        nhan, c1, c2, c3 = _doc(duong_dan)
    except Exception:
        return {"loai": "?", "so_chu_ky": None, "so_diem": 0, "mo_ta": "? (không đọc được)"}
    n = len(c1)
    if n == 0:
        return {"loai": "?", "so_chu_ky": None, "so_diem": 0, "mo_ta": "? (không có số liệu)"}
    g = nhan.upper()
    if "POTSTATIC" in g or g.endswith("_IT") or "CHRONOAMP" in g:
        return {"loai": "IT", "so_chu_ky": None, "so_diem": n, "mo_ta": "IT"}
    if "EIS" in g or "IMP" in g:
        return {"loai": "EIS", "so_chu_ky": None, "so_diem": n, "mo_ta": "EIS"}
    ptp1, ptp3 = max(c1) - min(c1), max(c3) - min(c3)
    if ptp1 < 0.005 and ptp3 > 10:
        return {"loai": "IT", "so_chu_ky": None, "so_diem": n, "mo_ta": "IT"}
    if n > 3 and min(c1) > 0 and max(c1) / min(c1) > 100:
        d1 = [c1[i + 1] - c1[i] for i in range(n - 1)]
        d3 = [c3[i + 1] - c3[i] for i in range(n - 1)]
        mot_chieu = all(x < 0 for x in d1) or all(x > 0 for x in d1)
        c3_deu = all(abs(x - d3[0]) <= 1e-6 + 1e-2 * abs(d3[0]) for x in d3)
        if mot_chieu and not c3_deu:
            return {"loai": "EIS", "so_chu_ky": None, "so_diem": n, "mo_ta": "EIS"}
    so_doi = _so_doi_chieu(c1)
    if so_doi >= 1:
        ck = so_doi // 2 + 1
        return {"loai": "CV", "so_chu_ky": ck, "so_diem": n, "mo_ta": f"CV ({ck} chu kỳ)"}
    return {"loai": "LSV", "so_chu_ky": None, "so_diem": n, "mo_ta": "LSV"}


def ten_ngan(duong_dan):
    return os.path.splitext(os.path.basename(duong_dan))[0]
