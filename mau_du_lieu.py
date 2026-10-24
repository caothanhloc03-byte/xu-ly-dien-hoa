# -*- coding: utf-8 -*-
"""
Sinh dữ liệu MẪU MINH HỌA (số liệu giả lập, KHÔNG phải kết quả thí nghiệm thật) theo đúng định dạng file thô
của app (CS Studio): cột E (V), i (A/cm²), T (s).

Dùng cho: nút "Dữ liệu mẫu" trong app (để người mới thử ngay) và cho kiểm thử tự động.
Chỉ dùng thư viện chuẩn của Python (math, random), không cần numpy.
"""
import math
import os
import random

# Hệ số quy đổi mặc định của app: E_RHE = E + 0.0592*pH + Eref ;  I(mA/cm2) = i*1000*nhan/chia
PH, EREF, NHAN_I, CHIA_I = 13.8, 0.098, 2.0, 2.15
DICH_E = 0.0592 * PH + EREF           # E_RHE - E_raw


def _viet(duong_dan, nhan_id, E, i, t, tieu_de="E(V)\ti(A/cm²)\tT(s)"):
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    with open(duong_dan, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"CSStudioFile,{nhan_id},\n{tieu_de}\n")
        for a, b, c in zip(E, i, t):
            f.write(f"{a:.5E}\t{b:.5E}\t{c:.5f}\n")


def _i_tho(j_mA_cm2):
    """Mật độ dòng (mA/cm2) -> dòng thô i (A/cm2) theo hệ số quy đổi mặc định."""
    return j_mA_cm2 * CHIA_I / (1000.0 * NHAN_I)


# ====================== LSV ======================
def tao_lsv(duong_dan, he_so=1.0, toc_do=0.010, e_rhe=(0.415, 1.915), nhieu=0.02, seed=1):
    """LSV kiểu OER: pic oxi hóa nhỏ ở ~0.87 V và dòng tăng nhanh từ ~1.3 V. he_so điều chỉnh độ lớn."""
    rnd = random.Random(seed)
    n = int(round((e_rhe[1] - e_rhe[0]) / 0.001)) + 1
    E, i, t = [], [], []
    for k in range(n):
        e = e_rhe[0] + k * 0.001
        pic = 14.0 * math.exp(-((e - 0.87) / 0.07) ** 2)
        x = 0.02 * he_so * math.exp((e - 1.2) / 0.05)          # OER: ~115 mV/dec, bão hòa dần ở ~300 mA/cm2
        oer = x / (1 + x / (300.0 * he_so))
        j = he_so * pic + oer
        j *= (1 + nhieu * rnd.uniform(-1, 1) * 0.1)
        E.append(e - DICH_E)
        i.append(_i_tho(j))
        t.append(k * 0.001 / toc_do)
    _viet(duong_dan, "ID_LSV", E, i, t)


# ====================== CV ======================
def tao_cv(duong_dan, toc_do_mV_s=20, so_chu_ky=3, cdl_mF_cm2=0.5, e_rhe=(0.515, 0.615), faraday=0.0, seed=3,
           cat_cuoi=False, bien_do_chu_ky1=0.5):
    """CV vùng điện dung: dòng ≈ ±Cdl·v (hình bình hành). Chu kỳ 1 có độ lệch tăng dần rồi ổn định.
    faraday > 0: thêm dòng Faraday anodic (làm Ja, Jc không đối xứng -> dùng để thử cảnh báo).
    cat_cuoi: bỏ nửa sau của chu kỳ cuối (mô phỏng phép đo dừng giữa chừng)."""
    rnd = random.Random(seed)
    v = toc_do_mV_s / 1000.0
    dE = 0.0002
    n_nua = int(round((e_rhe[1] - e_rhe[0]) / dE))
    E, J, T = [], [], []
    j_cu, t_cu = 0.0, 0.0
    tong_nua = 2 * so_chu_ky
    for h in range(tong_nua):
        chieu = 1 if h % 2 == 0 else -1
        chu_ky = h // 2
        muc_tieu = chieu * cdl_mF_cm2 * v        # mA/cm2
        troi = bien_do_chu_ky1 * cdl_mF_cm2 * v * math.exp(-chu_ky * 1.5)    # độ trôi giảm dần theo chu kỳ
        for k in range(n_nua):
            e = e_rhe[0] + k * dE if chieu > 0 else e_rhe[1] - k * dE
            j = muc_tieu + (j_cu - muc_tieu) * math.exp(-k * dE / 0.01) + troi * (e - e_rhe[0]) / (e_rhe[1] - e_rhe[0])
            if faraday and chieu > 0:
                j += faraday * math.exp((e - e_rhe[0]) / 0.05) * math.sqrt(v / 0.02)
            j += 0.002 * cdl_mF_cm2 * v * rnd.uniform(-1, 1)
            E.append(e - DICH_E)
            J.append(j)
            T.append(t_cu + k * dE / v)
        j_cu, t_cu = J[-1], T[-1] + dE / v
    if cat_cuoi:
        cat = len(E) - n_nua
        E, J, T = E[:cat], J[:cat], T[:cat]
    _viet(duong_dan, "ID_CV", E, [_i_tho(j) for j in J], T)


# ====================== IT ======================
def tao_it(duong_dan, thoi_gian_s=3600, e_rhe=1.515, j0=20.0, suy_giam=0.15, seed=5):
    rnd = random.Random(seed)
    dt = 2.0
    n = int(thoi_gian_s / dt) + 1
    E, i, t = [], [], []
    for k in range(n):
        tt = k * dt
        j = j0 * ((1 - suy_giam) + suy_giam * math.exp(-tt / 400.0)) * (1 + 0.01 * rnd.uniform(-1, 1))
        E.append(e_rhe - DICH_E)
        i.append(_i_tho(j))
        t.append(tt)
    _viet(duong_dan, "ID_IT", E, i, t)


# ====================== EIS (Randles) ======================
def tao_eis(duong_dan, rs=1.2, rct=8.0, cdl=2e-4, f_max=1e5, f_min=0.1, so_diem=51):
    dong = []
    for k in range(so_diem):
        f = f_max * (f_min / f_max) ** (k / (so_diem - 1))
        w = 2 * math.pi * f
        den = 1 + (w * rct * cdl) ** 2
        zr = rs + rct / den
        zi = -rct * (w * rct * cdl) / den           # Z'' âm (điện dung)
        dong.append((f, math.hypot(zr, zi), math.degrees(math.atan2(zi, zr)), 0.0, zr, zi))
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    with open(duong_dan, "w", encoding="utf-8", newline="\n") as fo:
        fo.write("CSStudioFile,ID_EIS,\nFreq (Hz)\tZmod\tPhase\tIdc\tZ'(Ohm)\tZ''(Ohm)\n")
        for r in dong:
            fo.write("\t".join(f"{x:.6E}" for x in r) + "\n")


# ====================== BỘ MẪU ======================
BO_MAU = {
    "lsv": "LSV so sánh 3 mẫu (quá thế, Tafel)",
    "ecsa": "ECSA: 6 file CV ở các tốc độ quét khác nhau",
    "it": "IT (dòng theo thời gian) 2 mẫu",
    "eis": "EIS (Nyquist) 3 mẫu",
}


def tao_bo(ten_bo, thu_muc):
    """Tạo bộ mẫu trong `thu_muc`. Trả về (danh_sach [{path, nhan}], loai_goi_y)."""
    os.makedirs(thu_muc, exist_ok=True)
    kq = []

    def them(ten_file, nhan):
        kq.append({"path": os.path.join(thu_muc, ten_file), "nhan": nhan})
        return kq[-1]["path"]

    if ten_bo == "lsv":
        for k, (nhan, hs) in enumerate((("Mẫu A", 1.0), ("Mẫu B", 1.35), ("Mẫu C", 0.5))):
            tao_lsv(them(f"LSV_mau_{'ABC'[k]}.txt", nhan), he_so=hs, seed=10 + k)
        return kq, "Tự nhận dạng"
    if ten_bo == "ecsa":
        for v in (10, 20, 40, 60, 80, 100):
            tao_cv(them(f"CV_ECSA_{v}mVs.txt", f"{v} mV/s"), toc_do_mV_s=v, seed=v)
        return kq, "ECSA (nhiều file CV)"
    if ten_bo == "it":
        for k, (nhan, j0, sg) in enumerate((("Mẫu A", 20.0, 0.10), ("Mẫu B", 25.0, 0.30))):
            tao_it(them(f"IT_mau_{'AB'[k]}.txt", nhan), j0=j0, suy_giam=sg, seed=20 + k)
        return kq, "IT"
    if ten_bo == "eis":
        for k, (nhan, rs, rct) in enumerate((("Mẫu A", 1.2, 8.0), ("Mẫu B", 1.1, 4.5), ("Mẫu C", 1.3, 14.0))):
            tao_eis(them(f"EIS_mau_{'ABC'[k]}.txt", nhan), rs=rs, rct=rct)
        return kq, "EIS"
    raise ValueError(f"Không có bộ mẫu '{ten_bo}'")
