# -*- coding: utf-8 -*-
"""Ngân hàng phổ XRD tự tính từ cấu trúc tinh thể (thay cho thẻ JCPDS/PDF có bản quyền).

Mỗi pha = ô mạng (a, b, c, alpha, beta, gamma) + toạ độ nguyên tử trong ô. Vị trí vạch (2theta) tính từ d_hkl theo bước sóng bất kỳ;
cường độ tính từ hệ số cấu trúc F(hkl) (hệ số tán xạ Cromer-Mann), nhân Lorentz-phân cực và độ bội (cộng các phản xạ cùng d).
Người dùng thêm pha mới từ file CIF (tải miễn phí ở COD/Materials Project) hoặc từ danh sách vạch (d, I, hkl) gõ từ thẻ PDF.
Mã thẻ PDF ghi kèm chỉ để tham chiếu - hãy đối chiếu thẻ gốc nếu cần công bố.
"""
import itertools
import json
import math
import os
import re

import numpy as np

# ---- nguyên tố ----
_SYM = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd "
        "In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi").split()
Z = {s: i + 1 for i, s in enumerate(_SYM)}

# Cromer-Mann: f(s) = sum a_i exp(-b_i s^2) + c, s = sin(theta)/lambda (1/Angstrom). (a1,b1,a2,b2,a3,b3,a4,b4,c)
CM = {
    "C": (2.31, 20.8439, 1.02, 10.2075, 1.5886, 0.5687, 0.865, 51.6512, 0.2156),
    "N": (12.2126, 0.0057, 3.1322, 9.8933, 2.0125, 28.9975, 1.1663, 0.5826, -11.529),
    "O": (3.0485, 13.2771, 2.2868, 5.7011, 1.5463, 0.3239, 0.867, 32.9089, 0.2508),
    "Al": (6.4202, 3.0387, 1.9002, 0.7426, 1.5936, 31.5472, 1.9646, 85.0886, 1.1151),
    "Si": (6.2915, 2.4386, 3.0353, 32.3337, 1.9891, 0.6785, 1.541, 81.6937, 1.1407),
    "Ti": (9.7595, 7.8508, 7.3558, 0.5, 1.6991, 35.6338, 1.9021, 116.105, 1.7807),
    "Fe": (11.7695, 4.7611, 7.3573, 0.3072, 3.5222, 15.3535, 2.3045, 76.8805, 1.0369),
    "Co": (12.2841, 4.2791, 7.3409, 0.2784, 4.0034, 13.5359, 2.3488, 71.1692, 1.0118),
    "Ni": (12.8376, 3.8785, 7.292, 0.2565, 4.4438, 12.1763, 2.38, 66.3421, 1.0341),
    "Cu": (13.338, 3.5828, 7.1676, 0.247, 5.6158, 11.3966, 1.6735, 64.8126, 1.191),
    "Zn": (14.0743, 3.2655, 7.0318, 0.2333, 5.1652, 10.3163, 2.41, 58.7097, 1.3041),
    "Ru": (19.2674, 0.80852, 12.9182, 8.43467, 4.86337, 24.7997, 1.56756, 94.2928, 5.37874),
    "Pd": (19.3319, 0.698655, 15.5017, 7.98929, 5.29537, 25.2052, 0.605844, 76.8986, 5.26593),
    "Ag": (19.2808, 0.6446, 16.6885, 7.4726, 4.8045, 24.6605, 1.0463, 99.8156, 5.179),
    "Pt": (27.0059, 1.51293, 17.7639, 8.81174, 15.7131, 0.424593, 5.7837, 38.6103, 11.6883),
    "Au": (16.8819, 0.4611, 18.5913, 8.6216, 25.5582, 1.4826, 5.86, 36.3956, 12.0658),
}


# Hệ số cho các nguyên tố ngoài bảng Cromer-Mann: f(s) = Z - 41.78214 s^2 sum a_i exp(-b_i s^2) (dạng Mott-Bethe, nguồn: bảng tham số của pymatgen, sai khác vài % so với bảng quốc tế)
MB = {"B":[[0.945,46.444],[1.312,14.178],[0.419,3.223],[0.116,0.377]],"Ba":[[7.821,117.657],[6.004,18.778],[3.28,3.263],[1.103,0.376]],"Bi":[[3.841,50.261],[4.679,11.999],[3.192,2.56],[1.363,0.318]],"Ca":[[4.47,99.523],[2.971,22.696],[1.97,4.195],[0.482,0.417]],"Cd":[[2.574,55.675],[3.259,11.838],[2.547,2.784],[0.838,0.322]],"Ce":[[5.007,28.283],[3.98,5.183],[1.678,0.589],[0,0]],"Cl":[[1.452,30.935],[2.292,9.98],[0.787,2.234],[0.322,0.323]],"Cr":[[2.307,78.405],[2.334,15.785],[1.823,3.157],[0.49,0.364]],"F":[[0.387,20.239],[0.811,6.609],[0.475,1.931],[0.146,0.279]],"Ga":[[2.321,65.602],[2.486,15.458],[1.688,2.581],[0.599,0.351]],"Ge":[[2.447,55.893],[2.702,14.393],[1.616,2.446],[0.601,0.342]],"Hf":[[5.588,29.001],[4.619,5.164],[1.997,0.579],[0,0]],"In":[[3.153,66.649],[3.557,14.449],[2.818,2.976],[0.884,0.335]],"Ir":[[5.754,29.159],[4.851,5.152],[2.096,0.57],[0,0]],"K":[[3.951,137.075],[2.545,22.402],[1.98,4.532],[0.482,0.434]],"La":[[4.94,28.716],[3.968,5.245],[1.663,0.594],[0,0]],"Li":[[1.611,107.638],[1.246,30.48],[0.326,4.533],[0.099,0.495]],"Mg":[[2.268,73.67],[1.803,20.175],[0.839,3.013],[0.289,0.405]],"Mn":[[2.747,67.786],[2.456,15.674],[1.792,3.0],[0.498,0.357]],"Mo":[[3.12,72.464],[3.906,14.642],[2.361,3.237],[0.85,0.366]],"Na":[[2.241,108.004],[1.333,24.505],[0.907,3.391],[0.286,0.435]],"Nb":[[4.237,27.415],[3.105,5.074],[1.234,0.593],[0,0]],"Os":[[5.75,28.933],[4.773,5.139],[2.079,0.573],[0,0]],"P":[[1.888,44.876],[2.469,13.538],[0.805,2.642],[0.32,0.361]],"Pb":[[3.51,52.914],[4.552,11.884],[3.154,2.571],[1.359,0.321]],"Re":[[5.695,28.968],[4.74,5.156],[2.064,0.575],[0,0]],"Rh":[[4.431,27.911],[3.343,5.153],[1.345,0.592],[0,0]],"S":[[1.659,36.65],[2.386,11.488],[0.79,2.469],[0.321,0.34]],"Sb":[[3.564,50.487],[3.844,13.316],[2.687,2.691],[0.864,0.316]],"Sc":[[3.966,88.96],[2.917,20.606],[1.925,3.856],[0.48,0.399]],"Sn":[[3.45,59.104],[3.735,14.179],[2.118,2.855],[0.877,0.327]],"Sr":[[5.848,104.972],[4.003,19.367],[2.342,3.737],[0.88,0.414]],"Ta":[[5.659,28.807],[4.63,5.114],[2.014,0.578],[0,0]],"V":[[3.245,76.379],[2.698,17.726],[1.86,3.363],[0.486,0.374]],"W":[[5.709,28.782],[4.677,5.084],[2.019,0.572],[0,0]],"Y":[[4.129,27.548],[3.012,5.088],[1.179,0.591],[0,0]],"Zr":[[4.105,28.492],[3.144,5.277],[1.229,0.601],[0,0]]}


def f_tan_xa(sym, s):
    """Hệ số tán xạ nguyên tử f(s). Không có trong bảng: xấp xỉ Z·exp(-2.8 s^2) (đánh dấu trong ghi chú pha)."""
    s2 = np.asarray(s, float) ** 2
    if sym in CM:
        a1, b1, a2, b2, a3, b3, a4, b4, c = CM[sym]
        return a1 * np.exp(-b1 * s2) + a2 * np.exp(-b2 * s2) + a3 * np.exp(-b3 * s2) + a4 * np.exp(-b4 * s2) + c
    if sym in MB:
        c = np.array(MB[sym], float)
        return Z[sym] - 41.78214 * s2 * np.sum(c[:, 0][None, :] * np.exp(-c[:, 1][None, :] * s2.reshape(-1, 1)), axis=1).reshape(s2.shape)
    return Z.get(sym, 10) * np.exp(-2.8 * s2)


# ---- bước sóng (Angstrom): (Ka1, Ka2, Kbeta) ----
NGUON = {
    "Cu Kα (1.5406)": (1.540562, 1.544390, 1.392250),
    "Co Kα (1.7890)": (1.788965, 1.792850, 1.620830),
    "Mo Kα (0.7093)": (0.709300, 0.713590, 0.632305),
    "Fe Kα (1.9360)": (1.936042, 1.939980, 1.756610),
    "Cr Kα (2.2897)": (2.289700, 2.293606, 2.084870),
    "Ag Kα (0.5594)": (0.559420, 0.563798, 0.497685),
}
W_LA1 = 1.47639        # tạp W Lα1 (ống Cu cũ bị lắng W)


# ---- ô mạng ----
def ma_tran_mang(a, b, c, al, be, ga):
    al, be, ga = (math.radians(v) for v in (al, be, ga))
    cg = math.cos(ga)
    v = a * b * c * math.sqrt(max(1 - math.cos(al) ** 2 - math.cos(be) ** 2 - math.cos(ga) ** 2 + 2 * math.cos(al) * math.cos(be) * cg, 1e-12))
    return v


def d_hkl(h, k, l, a, b, c, al, be, ga):
    """Khoảng cách mặt d (Angstrom) cho ô mạng tổng quát (công thức tam tà)."""
    al, be, ga = (math.radians(v) for v in (al, be, ga))
    ca, cb, cg = math.cos(al), math.cos(be), math.cos(ga)
    sa, sb, sg = math.sin(al), math.sin(be), math.sin(ga)
    v2 = 1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg
    s11, s22, s33 = (b * c * sa) ** 2, (a * c * sb) ** 2, (a * b * sg) ** 2
    s12, s23, s13 = a * b * c * c * (ca * cb - cg), a * a * b * c * (cb * cg - ca), a * b * b * c * (cg * ca - cb)
    inv = (s11 * h * h + s22 * k * k + s33 * l * l + 2 * s12 * h * k + 2 * s23 * k * l + 2 * s13 * h * l) / (a * b * c) ** 2 / v2
    return 1.0 / math.sqrt(inv) if inv > 0 else float("inf")


def vach_pha(pha, lam, tt_min=5.0, tt_max=90.0, i_min=0.3, b_dw=0.4):
    """Danh sách vạch nhiễu xạ của pha: list dict(tt, d, hkl, I) với I% so với vạch mạnh nhất (cùng d được gộp).
    Nếu pha có 'vach' (nhập tay d, I, hkl) thì đổi d -> 2theta theo bước sóng."""
    if pha.get("vach"):
        kq = []
        for d, i, hkl in pha["vach"]:
            s = lam / (2.0 * d)
            if s < 1:
                tt = 2.0 * math.degrees(math.asin(s))
                if tt_min <= tt <= tt_max:
                    kq.append({"tt": tt, "d": float(d), "hkl": hkl, "I": float(i)})
        m = max([v["I"] for v in kq] or [1.0])
        for v in kq:
            v["I"] = 100.0 * v["I"] / m
        return [v for v in kq if v["I"] >= i_min]
    a, b, c, al, be, ga = (pha["cell"][k] for k in ("a", "b", "c", "alpha", "beta", "gamma"))
    at = pha["atoms"]
    sym = [x[0] for x in at]
    pos = np.array([[x[1], x[2], x[3]] for x in at], float)
    occ = np.array([x[4] if len(x) > 4 else 1.0 for x in at], float)
    d_min = lam / (2.0 * math.sin(math.radians(min(tt_max, 175.0) / 2.0)))
    hm = int(a / d_min) + 1
    km = int(b / d_min) + 1
    lm = int(c / d_min) + 1
    cac = {}
    for h in range(-hm, hm + 1):
        for k in range(-km, km + 1):
            for l in range(-lm, lm + 1):
                if h == k == l == 0:
                    continue
                d = d_hkl(h, k, l, a, b, c, al, be, ga)
                if d < d_min or lam / (2 * d) >= 1:
                    continue
                s = 1.0 / (2.0 * d)
                th = math.asin(lam / (2 * d))
                ph = 2j * np.pi * (pos @ np.array([h, k, l]))
                F = 0j
                for sy in set(sym):
                    m = np.array([x == sy for x in sym])
                    F += float(f_tan_xa(sy, s)) * np.sum(occ[m] * np.exp(ph[m])) * math.exp(-b_dw * s * s)
                I = (abs(F) ** 2) * (1 + math.cos(2 * th) ** 2) / (math.sin(th) ** 2 * math.cos(th))
                if I < 1e-6:
                    continue
                key = round(d, 3)
                e = cac.get(key)
                if e is None:
                    cac[key] = {"d": d, "I": I, "hkl": [(h, k, l)]}
                else:
                    e["I"] += I
                    e["hkl"].append((h, k, l))
    kq = []
    for e in cac.values():
        tt = 2.0 * math.degrees(math.asin(lam / (2 * e["d"])))
        if tt_min <= tt <= tt_max:
            cand = sorted(e["hkl"], key=lambda t: (-(t[0] >= 0) - (t[1] >= 0) - (t[2] >= 0), -t[0], -t[1], -t[2]))
            kq.append({"tt": tt, "d": e["d"], "hkl": "(%d%d%d)" % cand[0] if max(map(abs, cand[0])) < 10 else str(cand[0]), "I": e["I"]})
    m = max([v["I"] for v in kq] or [1.0])
    kq = [dict(v, I=100.0 * v["I"] / m) for v in kq]
    kq = [v for v in kq if v["I"] >= i_min]
    kq.sort(key=lambda v: v["tt"])
    return kq


# ---- dựng pha tiện dụng ----
def _fcc(sym):
    return [(sym, 0, 0, 0), (sym, .5, .5, 0), (sym, .5, 0, .5), (sym, 0, .5, .5)]


def _bcc(sym):
    return [(sym, 0, 0, 0), (sym, .5, .5, .5)]


def _hcp(sym):
    return [(sym, 1 / 3, 2 / 3, .25), (sym, 2 / 3, 1 / 3, .75)]


def _rocksalt(m, x):
    return [(m, p[0], p[1], p[2]) for p in ((0, 0, 0), (.5, .5, 0), (.5, 0, .5), (0, .5, .5))] + \
           [(x, p[0], p[1], p[2]) for p in ((.5, .5, .5), (0, 0, .5), (0, .5, 0), (.5, 0, 0))]


def _rutile(m, x, u):
    return [(m, 0, 0, 0), (m, .5, .5, .5), (x, u, u, 0), (x, -u, -u, 0), (x, .5 + u, .5 - u, .5), (x, .5 - u, .5 + u, .5)]


def _cell(a, b=None, c=None, al=90, be=90, ga=90):
    return {"a": a, "b": b or a, "c": c or a, "alpha": al, "beta": be, "gamma": ga}


def _pha(ten, ct, he, cell, atoms, pdf="", ghi=""):
    return {"ten": ten, "cong_thuc": ct, "he": he, "cell": cell, "atoms": atoms, "pdf": pdf, "ghi_chu": ghi, "nguon": "tích hợp",
            "nguyen_to": sorted({a[0] for a in atoms})}


BANG_TICH_HOP = [
    _pha("Ni (fcc)", "Ni", "lập phương", _cell(3.5238), _fcc("Ni"), "04-0850", "niken kim loại; bọt niken (NF)"),
    _pha("NiO (bunsenit)", "NiO", "lập phương", _cell(4.1771), _rocksalt("Ni", "O"), "47-1049", "lớp oxit bề mặt niken"),
    _pha("Ni(OH)2 (β)", "Ni(OH)2", "lục phương", _cell(3.126, c=4.605, ga=120),
         [("Ni", 0, 0, 0), ("O", 1 / 3, 2 / 3, 0.22), ("O", 2 / 3, 1 / 3, -0.22)], "14-0117", "bỏ qua H"),
    _pha("Ru (hcp)", "Ru", "lục phương", _cell(2.7058, c=4.2811, ga=120), _hcp("Ru"), "06-0663", "ruteni kim loại"),
    _pha("RuO2 (rutile)", "RuO2", "tứ phương", _cell(4.4994, c=3.1071), _rutile("Ru", "O", 0.306), "43-1027", "ruteni đioxit"),
    _pha("Graphit (C)", "C", "lục phương", _cell(2.4704, c=6.7244, ga=120),
         [("C", 0, 0, .25), ("C", 0, 0, .75), ("C", 1 / 3, 2 / 3, .25), ("C", 2 / 3, 1 / 3, .75)], "41-1487", "graphit/graphene nhiều lớp (002 ≈ 26.5°)"),
    _pha("Co (hcp)", "Co", "lục phương", _cell(2.5071, c=4.0695, ga=120), _hcp("Co"), "05-0727"),
    _pha("Co (fcc)", "Co", "lập phương", _cell(3.5447), _fcc("Co"), "15-0806"),
    _pha("Fe (α, bcc)", "Fe", "lập phương", _cell(2.8665), _bcc("Fe"), "06-0696"),
    _pha("Cu (fcc)", "Cu", "lập phương", _cell(3.6149), _fcc("Cu"), "04-0836"),
    _pha("Au (fcc)", "Au", "lập phương", _cell(4.0786), _fcc("Au"), "04-0784"),
    _pha("Pt (fcc)", "Pt", "lập phương", _cell(3.9231), _fcc("Pt"), "04-0802"),
    _pha("Pd (fcc)", "Pd", "lập phương", _cell(3.8907), _fcc("Pd"), "05-0681"),
    _pha("Ag (fcc)", "Ag", "lập phương", _cell(4.0862), _fcc("Ag"), "04-0783"),
    _pha("Al (fcc)", "Al", "lập phương", _cell(4.0495), _fcc("Al"), "04-0787"),
    _pha("TiO2 (rutile)", "TiO2", "tứ phương", _cell(4.5937, c=2.9587), _rutile("Ti", "O", 0.3053), "21-1276"),
    _pha("ZnO (wurtzit)", "ZnO", "lục phương", _cell(3.2498, c=5.2066, ga=120),
         [("Zn", 1 / 3, 2 / 3, 0), ("Zn", 2 / 3, 1 / 3, .5), ("O", 1 / 3, 2 / 3, .382), ("O", 2 / 3, 1 / 3, .882)], "36-1451"),
]


# ---- mở rộng ngân hàng: nhóm không gian dựng từ phần tử sinh (kiểm chứng bằng số phần tử nhóm và kích thước quỹ đạo) ----
def _khoa(p):
    return tuple(round(v % 1.0, 4) % 1.0 for v in p)


def _quy_dao(pt, phep, tinh_tien):
    """Quỹ đạo của một điểm dưới nhóm sinh bởi các phép 'phep' (chuỗi) và tịnh tiến tâm (khử trùng theo khoá làm tròn, giữ giá trị chính xác)."""
    gen = [lambda q, t=t: tuple(_ap_dung_phep(t, q)) for t in phep]
    gen += [lambda q, t=t: tuple(q[i] + t[i] for i in range(3)) for t in tinh_tien]
    pt = tuple(v % 1.0 for v in pt)
    xong = {_khoa(pt): pt}
    hang = [pt]
    while hang:
        q = hang.pop()
        for g in gen:
            r = tuple(v % 1.0 for v in g(q))
            k = _khoa(r)
            if k not in xong:
                xong[k] = r
                hang.append(r)
    return [xong[k] for k in sorted(xong)]


_FCC_T = [(0, .5, .5), (.5, 0, .5), (.5, .5, 0)]
_FD3M = ["-x+3/4,-y+1/4,z+1/2", "-x+1/4,y+1/2,-z+3/4", "z,x,y", "y+3/4,x+1/4,-z+1/2", "-x,-y,-z"]
_R_T = [(2 / 3, 1 / 3, 1 / 3), (1 / 3, 2 / 3, 2 / 3)]
_R3C = ["-y,x-y,z", "y,x,-z+1/2", "-x,-y,-z"]


def _lap(sym, pt, phep, tt, occ=1.0):
    return [(sym, q[0], q[1], q[2], occ) if occ != 1.0 else (sym, q[0], q[1], q[2]) for q in _quy_dao(pt, phep, tt)]


def _spinel(a, u, tet, octa, ten, ct, pdf="", ghi=""):
    """Spinel Fd-3m (gốc 2): tet = [(nguyên tố, tỉ lệ chiếm)] ở vị trí 8a, octa ở 16d, O ở 32e (x=u)."""
    at = []
    for sym, oc in tet:
        at += _lap(sym, (1 / 8, 1 / 8, 1 / 8), _FD3M, _FCC_T, oc)
    for sym, oc in octa:
        at += _lap(sym, (.5, .5, .5), _FD3M, _FCC_T, oc)
    at += _lap("O", (u, u, u), _FD3M, _FCC_T)
    return _pha(ten, ct, "lập phương", _cell(a), at, pdf, ghi)


def _bang_mo_rong():
    kq = []
    A = kq.append
    # --- kim loại ---
    for ten, ct, a, kieu, pdf in (("Ir (fcc)", "Ir", 3.8394, "f", ""), ("Rh (fcc)", "Rh", 3.8034, "f", ""), ("Pb (fcc)", "Pb", 4.9505, "f", ""),
                                  ("Mo (bcc)", "Mo", 3.1472, "b", ""), ("W (bcc)", "W", 3.1652, "b", ""), ("Cr (bcc)", "Cr", 2.8839, "b", ""),
                                  ("V (bcc)", "V", 3.0274, "b", ""), ("Nb (bcc)", "Nb", 3.3004, "b", ""), ("Ta (bcc)", "Ta", 3.3031, "b", "")):
        A(_pha(ten, ct, "lập phương", _cell(a), _fcc(ct) if kieu == "f" else _bcc(ct), pdf, "kim loại"))
    for ten, ct, a, c in (("Ti (hcp)", "Ti", 2.9508, 4.6855), ("Zr (hcp)", "Zr", 3.2312, 5.1477), ("Zn (hcp)", "Zn", 2.6649, 4.9468),
                          ("Mg (hcp)", "Mg", 3.2094, 5.2105), ("Cd (hcp)", "Cd", 2.9794, 5.6186), ("Re (hcp)", "Re", 2.761, 4.456),
                          ("Os (hcp)", "Os", 2.7341, 4.3197)):
        A(_pha(ten, ct, "lục phương", _cell(a, c=c, ga=120), _hcp(ct), "", "kim loại"))
    A(_pha("Si (kim cương)", "Si", "lập phương", _cell(5.4309), _fcc("Si") + [("Si", x + .25, y + .25, z + .25) for _, x, y, z in _fcc("Si")], "27-1402", "đế silic"))
    A(_pha("Kim cương (C)", "C", "lập phương", _cell(3.5668), _fcc("C") + [("C", x + .25, y + .25, z + .25) for _, x, y, z in _fcc("C")], "", "kim cương"))
    # --- oxit đá muối ---
    for ten, ct, m, a, pdf in (("MgO (periclase)", "MgO", "Mg", 4.2112, "45-0946"), ("CoO (đá muối)", "CoO", "Co", 4.2667, ""),
                               ("FeO (wüstit)", "FeO", "Fe", 4.3088, ""), ("MnO (manganosit)", "MnO", "Mn", 4.4446, ""),
                               ("CdO", "CdO", "Cd", 4.6953, ""), ("TiN", "TiN", "Ti", 4.2417, "38-1420")):
        A(_pha(ten, ct, "lập phương", _cell(a), _rocksalt(m, "N" if ct == "TiN" else "O"), pdf))
    # --- fluorit, perovskit, cuprit ---
    for ten, ct, m, a, pdf in (("CeO2 (fluorit)", "CeO2", "Ce", 5.4113, "34-0394"), ("ZrO2 (lập phương)", "ZrO2", "Zr", 5.09, "")):
        A(_pha(ten, ct, "lập phương", _cell(a), _fcc(m) + [("O", x, y, z) for x in (.25, .75) for y in (.25, .75) for z in (.25, .75)], pdf))
    A(_pha("SrTiO3 (perovskit)", "SrTiO3", "lập phương", _cell(3.905),
           [("Sr", 0, 0, 0), ("Ti", .5, .5, .5), ("O", .5, .5, 0), ("O", .5, 0, .5), ("O", 0, .5, .5)], "35-0734"))
    cup = lambda m, x_: [(x_, 0, 0, 0), (x_, .5, .5, .5)] + [(m, .25, .25, .25), (m, .75, .75, .25), (m, .75, .25, .75), (m, .25, .75, .75)]
    A(_pha("Cu2O (cuprit)", "Cu2O", "lập phương", _cell(4.2696), cup("Cu", "O"), "05-0667", "oxit đồng(I) trên bọt Cu"))
    A(_pha("Ag2O", "Ag2O", "lập phương", _cell(4.7294), cup("Ag", "O"), "", "oxit bạc(I)"))
    # --- CuO (C2/c) ---
    cuo = []
    for sym, pt in (("Cu", (.25, .25, 0)), ("O", (0, .418, .25))):
        for q in _quy_dao(pt, ["-x,y,-z+1/2", "-x,-y,-z"], [(.5, .5, 0)]):
            cuo.append((sym,) + q)
    A(_pha("CuO (tenorit)", "CuO", "đơn tà", _cell(4.6837, 3.4226, 5.1288, be=99.54), cuo, "48-1548", "oxit đồng(II)"))
    # --- rutil ---
    for ten, ct, m, a, c, u, pdf in (("MnO2 (pyrolusit, β)", "MnO2", "Mn", 4.398, 2.874, 0.302, ""), ("SnO2 (cassiterit)", "SnO2", "Sn", 4.7382, 3.1871, 0.3056, "41-1445"),
                                     ("IrO2 (rutil)", "IrO2", "Ir", 4.4983, 3.1544, 0.308, "")):
        A(_pha(ten, ct, "tứ phương", _cell(a, c=c), _rutile(m, "O", u), pdf))
    # --- anatase TiO2 (I41/amd) ---
    z = 0.2081
    ti = [("Ti", 0, 0, 0), ("Ti", 0, .5, .25)]
    ox = [("O", 0, 0, z), ("O", 0, 0, -z), ("O", 0, .5, .25 + z), ("O", 0, .5, .25 - z)]
    A(_pha("TiO2 (anatas)", "TiO2", "tứ phương", _cell(3.7845, c=9.5143), [(s_, (x + t) % 1, (y + t) % 1, (zz + t) % 1) for s_, x, y, zz in ti + ox for t in (0, .5)],
           "21-1272", "pha anatas"))
    # --- spinel ---
    A(_spinel(8.0837, 0.2637, [("Co", 1.0)], [("Co", 1.0)], "Co3O4 (spinel)", "Co3O4", "42-1467", "oxit coban hỗn hợp"))
    A(_spinel(8.396, 0.2549, [("Fe", 1.0)], [("Fe", 1.0)], "Fe3O4 (magnetit)", "Fe3O4", "19-0629", "magnetit (gần giống γ-Fe2O3)"))
    A(_spinel(8.114, 0.263, [("Co", 1.0)], [("Co", .5), ("Ni", .5)], "NiCo2O4 (spinel)", "NiCo2O4", "", "coban niken oxit"))
    A(_spinel(8.339, 0.2565, [("Fe", 1.0)], [("Fe", .5), ("Ni", .5)], "NiFe2O4 (spinel)", "NiFe2O4", "", "spinel nghịch"))
    A(_spinel(8.0948, 0.2635, [("Zn", 1.0)], [("Co", 1.0)], "ZnCo2O4 (spinel)", "ZnCo2O4", "", ""))
    # --- corundum R-3c ---
    for ten, ct, m, a, c, zm, xo, pdf in (("α-Fe2O3 (hematit)", "Fe2O3", "Fe", 5.0356, 13.7489, 0.3553, 0.3059, "33-0664"),
                                          ("Cr2O3 (eskolait)", "Cr2O3", "Cr", 4.9587, 13.5942, 0.3475, 0.3059, "38-1479")):
        at = _lap(m, (0, 0, zm), _R3C, _R_T) + _lap("O", (xo, 0, .25), _R3C, _R_T)
        A(_pha(ten, ct, "lục phương (R)", _cell(a, c=c, ga=120), at, pdf))
    # --- hiđroxit brucit ---
    for ten, ct, m, a, c in (("Co(OH)2 (β)", "Co(OH)2", "Co", 3.183, 4.653), ("Mn(OH)2", "Mn(OH)2", "Mn", 3.322, 4.734),
                             ("Fe(OH)2", "Fe(OH)2", "Fe", 3.258, 4.605), ("Mg(OH)2 (brucit)", "Mg(OH)2", "Mg", 3.1442, 4.7770)):
        A(_pha(ten, ct, "lục phương", _cell(a, c=c, ga=120), [(m, 0, 0, 0), ("O", 1 / 3, 2 / 3, 0.22), ("O", 2 / 3, 1 / 3, -0.22)], "", "bỏ qua H"))
    # --- MoS2 / WS2 ---
    for ten, ct, m, a, c, zs, pdf in (("MoS2 (2H)", "MoS2", "Mo", 3.16, 12.29, 0.621, "37-1492"), ("WS2 (2H)", "WS2", "W", 3.153, 12.323, 0.623, "")):
        A(_pha(ten, ct, "lục phương", _cell(a, c=c, ga=120),
               [(m, 1 / 3, 2 / 3, .25), (m, 2 / 3, 1 / 3, .75), ("S", 1 / 3, 2 / 3, zs), ("S", 2 / 3, 1 / 3, 1 - zs), ("S", 2 / 3, 1 / 3, zs - .5), ("S", 1 / 3, 2 / 3, 1.5 - zs)],
               pdf, "xúc tác HER"))
    A(_pha("WC", "WC", "lục phương", _cell(2.906, c=2.837, ga=120), [("W", 0, 0, 0), ("C", 1 / 3, 2 / 3, .5)], "51-0939", "vonfram cacbua"))
    # --- LiCoO2 (R-3m) ---
    zo = 0.2395
    A(_pha("LiCoO2", "LiCoO2", "lục phương (R)", _cell(2.816, c=14.05, ga=120),
           [(s_, (x + t[0]) % 1, (y + t[1]) % 1, (zz + t[2]) % 1) for s_, x, y, zz in (("Li", 0, 0, 0), ("Co", 0, 0, .5), ("O", 0, 0, zo), ("O", 0, 0, -zo))
            for t in ((0, 0, 0),) + tuple(_R_T)], "50-0653", "vật liệu catot pin Li-ion"))
    return kq


# ---- ngân hàng người dùng ----
def duong_file_nguoi_dung():
    thu_muc = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DienHoaOrigin")
    return os.path.join(thu_muc, "ngan_hang_xrd.json")


def doc_nguoi_dung(duong=None):
    duong = duong or duong_file_nguoi_dung()
    try:
        with open(duong, encoding="utf-8") as f:
            ds = json.load(f)
        return [dict(p, nguon="người dùng") for p in ds if isinstance(p, dict) and p.get("ten")]
    except (OSError, ValueError):
        return []


def luu_nguoi_dung(ds, duong=None):
    duong = duong or duong_file_nguoi_dung()
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in p.items() if k != "nguon"} for p in ds], f, ensure_ascii=False, indent=1)
    return duong


def toan_bo(duong_nd=None):
    return list(BANG_TICH_HOP) + doc_nguoi_dung(duong_nd)


def loc_theo_nguyen_to(ds, nguyen_to):
    """Giữ pha chỉ chứa nguyên tố trong danh sách (vd Ni Ru C O). Rỗng = giữ hết."""
    if not nguyen_to:
        return list(ds)
    ok = set(nguyen_to)
    return [p for p in ds if set(p.get("nguyen_to") or [a[0] for a in p.get("atoms", [])]) <= ok]


def doc_nguyen_to(text):
    kq = []
    for t in re.split(r"[\s,;]+", str(text or "").strip()):
        t = t.strip().capitalize()
        if t in Z:
            kq.append(t)
    return kq


# ---- CIF ----
def _phan_so(t):
    t = t.strip()
    if "/" in t:
        a, b = t.split("/")
        return float(a) / float(b)
    return float(t)


def _ap_dung_phep(phep, p):
    """phep: 'x,-y+1/2,z+1/4' -> toạ độ mới."""
    kq = []
    for bieu in phep.replace(" ", "").lower().split(","):
        v = 0.0
        for dau, he, bien in re.findall(r"([+-]?)(\d*/?\d*\.?\d*)\*?([xyz])", bieu):
            hs = _phan_so(he) if he not in ("", ".") else 1.0
            v += (-1 if dau == "-" else 1) * hs * p["xyz".index(bien)]
        for dau, so in re.findall(r"([+-])(\d+/\d+|\d*\.\d+|\d+)(?![\d/*xyz])", re.sub(r"[+-]?\d*/?\d*\.?\d*\*?[xyz]", "", bieu)):
            v += (-1 if dau == "-" else 1) * _phan_so(so)
        kq.append(v)
    return kq


BANG_TICH_HOP += _bang_mo_rong()


def doc_cif(text, ten=None):
    """Đọc CIF đơn giản (một khối dữ liệu): ô mạng, phép đối xứng, nguyên tử -> pha. Ném ValueError nếu thiếu dữ liệu."""
    dong = [d.strip() for d in text.splitlines()]
    thong_so = {}
    for d in dong:
        m = re.match(r"_cell_(length_[abc]|angle_(?:alpha|beta|gamma))\s+([\d.]+)", d)
        if m:
            thong_so[m.group(1)] = float(m.group(2))
        m = re.match(r"_chemical_formula_sum\s+['\"]?(.+?)['\"]?$", d)
        if m:
            thong_so["ct"] = m.group(1)
        m = re.match(r"_chemical_name_mineral\s+['\"]?(.+?)['\"]?$", d)
        if m and not ten:
            ten = m.group(1)
    if not all(k in thong_so for k in ("length_a", "length_b", "length_c")):
        raise ValueError("CIF thiếu thông số ô mạng (_cell_length_a/b/c).")
    cell = {"a": thong_so["length_a"], "b": thong_so["length_b"], "c": thong_so["length_c"],
            "alpha": thong_so.get("angle_alpha", 90.0), "beta": thong_so.get("angle_beta", 90.0), "gamma": thong_so.get("angle_gamma", 90.0)}

    def bang(tieu_de_khoa):
        i = 0
        while i < len(dong):
            if dong[i] == "loop_":
                j = i + 1
                cot = []
                while j < len(dong) and dong[j].startswith("_"):
                    cot.append(dong[j])
                    j += 1
                if any(c.startswith(tieu_de_khoa) for c in cot):
                    hang = []
                    while j < len(dong) and dong[j] and not dong[j].startswith(("_", "loop_", "#")):
                        hang.append(re.findall(r"'[^']*'|\"[^\"]*\"|\S+", dong[j]))
                        j += 1
                    return cot, hang
                i = j
            else:
                i += 1
        return [], []

    cot, hang = bang("_symmetry_equiv_pos_as_xyz")
    if not cot:
        cot, hang = bang("_space_group_symop_operation_xyz")
    ten_cot_phep = next((c for c in cot if c.endswith("xyz")), None)
    cac_phep = []
    if ten_cot_phep:
        ix = cot.index(ten_cot_phep)
        cac_phep = [h[ix].strip("'\"") for h in hang if len(h) > ix]
    if not cac_phep:
        cac_phep = ["x,y,z"]
    cot, hang = bang("_atom_site")
    need = ["_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z"]
    if not all(n in cot for n in need):
        raise ValueError("CIF thiếu toạ độ nguyên tử (_atom_site_fract_x/y/z).")
    ixs = [cot.index(n) for n in need]
    ik = cot.index("_atom_site_type_symbol") if "_atom_site_type_symbol" in cot else cot.index("_atom_site_label")
    io = cot.index("_atom_site_occupancy") if "_atom_site_occupancy" in cot else None
    atoms = []
    for h in hang:
        if len(h) <= max(ixs + [ik]):
            continue
        sym = re.match(r"[A-Za-z]+", h[ik]).group(0).capitalize()
        sym = sym if sym in Z else sym[:1]
        p0 = [float(re.sub(r"\(.*?\)", "", h[i])) for i in ixs]
        oc = float(re.sub(r"\(.*?\)", "", h[io])) if io is not None and len(h) > io else 1.0
        da = []
        for phep in cac_phep:
            q = [v % 1.0 for v in _ap_dung_phep(phep, p0)]
            q = [0.0 if abs(v - 1.0) < 1e-4 else v for v in q]
            if not any(all(abs(((q[i] - e[i] + 0.5) % 1.0) - 0.5) < 1e-3 for i in range(3)) for e in da):
                da.append(q)
        atoms += [(sym, q[0], q[1], q[2], oc) for q in da]
    if not atoms:
        raise ValueError("Không đọc được nguyên tử nào từ CIF.")
    ct = thong_so.get("ct", "".join(sorted({a[0] for a in atoms})))
    return {"ten": ten or ct, "cong_thuc": ct, "he": "từ CIF", "cell": cell, "atoms": atoms, "pdf": "", "ghi_chu": "nhập từ CIF",
            "nguon": "người dùng", "nguyen_to": sorted({a[0] for a in atoms})}


def pha_tu_danh_sach_vach(ten, cong_thuc, text, lam=1.540562):
    """Nhập pha từ bảng vạch gõ tay. Mỗi dòng: '2theta  I  hkl' (2theta theo bước sóng lam) hoặc 'd=2.03  I  hkl'.
    Lưu dưới dạng d (không phụ thuộc bước sóng)."""
    vach = []
    for d in text.splitlines():
        d = d.strip()
        if not d or d.startswith("#"):
            continue
        p = re.split(r"[\s,;]+", d)
        if len(p) < 2:
            continue
        try:
            if p[0].lower().startswith("d="):
                dd = float(p[0][2:])
            else:
                tt = float(p[0])
                dd = lam / (2 * math.sin(math.radians(tt / 2)))
            vach.append([dd, float(p[1]), p[2] if len(p) > 2 else ""])
        except ValueError:
            raise ValueError(f"Dòng không đọc được: '{d}'")
    if len(vach) < 2:
        raise ValueError("Cần ít nhất 2 vạch.")
    ng = sorted({m for m in re.findall(r"[A-Z][a-z]?", cong_thuc) if m in Z})
    return {"ten": ten, "cong_thuc": cong_thuc, "he": "bảng vạch", "vach": vach, "pdf": "", "ghi_chu": "nhập tay từ thẻ PDF",
            "nguon": "người dùng", "nguyen_to": ng}
