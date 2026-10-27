# -*- coding: utf-8 -*-
"""
HIỆU SUẤT FARADAY (FE) và TỐC ĐỘ SINH KHÍ từ phép đo i-t (chronoamperometry).

    Q (C)        = ∫ |i| dt                      (i = dòng đo thực, A; lấy từ cột thô)
    n_khí (mol)  = P_khí · V / (R · T)            (V đo bằng phương pháp dời nước)
    FE (%)       = n_e · F · n_khí / Q × 100      (n_e = 2 cho H2, 4 cho O2)
    tốc độ sinh  = n_khí / (S · t)                (mmol cm⁻² h⁻¹; S = diện tích điện cực = hệ số chia dòng)

Khí thu bằng cách dời nước bão hòa hơi nước nên P_khí = P_khí quyển − P_hơi nước (công thức Tetens);
có thể tắt hiệu chỉnh này bằng --fe-khong-hoi-nuoc.
"""
import os

import numpy as np
import pandas as pd

FARADAY = 96485.33212
R_KHI = 8.314462618


def ap_suat_hoi_nuoc_kpa(nhiet_do_c):
    return 0.61078 * np.exp(17.27 * nhiet_do_c / (nhiet_do_c + 237.3))


def dien_luong(d):
    """Điện lượng Q (C) và thời gian (h) của một phép đo i-t đã xử lý bởi xu_ly_dien_hoa.xu_ly_it."""
    t = d["T (s)"].to_numpy(dtype=float)
    i = np.abs(d["i (A/cm2)"].to_numpy(dtype=float))        # cột "i (A/cm2)" chính là dòng đo thực (A)
    if len(t) < 2:
        raise ValueError("quá ít điểm để tính điện lượng")
    return float(np.trapz(i, t) if hasattr(np, "trapz") else np.trapezoid(i, t)), float(t[-1] - t[0]) / 3600.0


def tinh_fe(d, v_ml, nhiet_do_c=25.0, ap_suat_kpa=101.325, n_e=2.0, dien_tich_cm2=1.0, tru_hoi_nuoc=True):
    q, gio = dien_luong(d)
    p_khi = ap_suat_kpa - (ap_suat_hoi_nuoc_kpa(nhiet_do_c) if tru_hoi_nuoc else 0.0)
    n_khi = p_khi * 1e3 * v_ml * 1e-6 / (R_KHI * (nhiet_do_c + 273.15))
    fe = n_e * FARADAY * n_khi / q * 100.0 if q > 0 else float("nan")
    return {"Q (C)": q, "thoi_gian (h)": gio, "V_khi (mL)": v_ml, "n_khi (mmol)": n_khi * 1e3,
            "P_khi (kPa)": p_khi, "FE (%)": fe,
            "toc_do_sinh (mmol cm-2 h-1)": n_khi * 1e3 / (dien_tich_cm2 * gio) if gio > 0 else float("nan"),
            "n_khi_ly_thuyet (mmol)": q / (n_e * FARADAY) * 1e3}


def _ds_so(chuoi):
    kq = []
    for x in str(chuoi or "").replace(";", ",").split(","):
        x = x.strip().replace(",", ".")
        if x:
            try:
                kq.append(float(x))
            except ValueError:
                kq.append(None)
    return kq


def xuat_fe(muc, a, thu_muc):
    """Tính FE cho các mẫu IT theo thứ tự (--fe-v-h2 liệt kê thể tích khí của từng mẫu IT, mL)."""
    ds_v = _ds_so(getattr(a, "fe_v_h2", None))
    if not ds_v:
        return None
    it = [m for m in muc if m["loai"] == "IT"]
    if not it:
        print("  (luu y) co nhap the tich khi nhung khong co file IT nao de tinh hieu suat Faraday.")
        return None
    if len(ds_v) < len(it):
        print(f"  (luu y) chi co {len(ds_v)} the tich khi cho {len(it)} mau IT; cac mau con lai bi bo qua.")
    nhiet = float(getattr(a, "fe_nhiet_do", 25.0) or 25.0)
    ap = float(getattr(a, "fe_ap_suat", 101.325) or 101.325)
    n_e = float(getattr(a, "fe_n", 2.0) or 2.0)
    s = float(getattr(a, "chia_i", 1.0) or 1.0)
    hoi = not getattr(a, "fe_khong_hoi_nuoc", False)
    hang = []
    try:
        import canh_bao
    except ImportError:
        canh_bao = None
    for m, v in zip(it, ds_v):
        if v is None or v <= 0:
            continue
        try:
            r = tinh_fe(m["d"], v, nhiet, ap, n_e, s, hoi)
        except Exception as e:
            print(f"  (canh bao) khong tinh duoc FE cho {m['nhan']}: {e}")
            continue
        r = {"Nhãn": m["nhan"], **r}
        hang.append(r)
        if canh_bao:
            fe = r["FE (%)"]
            if fe > 105:
                canh_bao.them(canh_bao.CANH_BAO, f"FE = {fe:.1f}% lớn hơn 100%: kiểm tra thể tích khí, điện lượng, diện tích hoặc rò rỉ/khí hòa tan.", m["nhan"])
            elif fe < 50:
                canh_bao.them(canh_bao.CANH_BAO, f"FE = {fe:.1f}% rất thấp: có thể có phản ứng phụ, thất thoát khí hoặc sai thể tích/điện lượng.", m["nhan"])
    if not hang:
        return None
    df = pd.DataFrame(hang)
    print("\n======== HIỆU SUẤT FARADAY ========")
    for r in hang:
        print(f"  {r['Nhãn']}: Q = {r['Q (C)']:.3f} C | n_khí = {r['n_khi (mmol)']:.4f} mmol "
              f"(lý thuyết {r['n_khi_ly_thuyet (mmol)']:.4f}) | FE = {r['FE (%)']:.1f}% | "
              f"tốc độ sinh = {r['toc_do_sinh (mmol cm-2 h-1)']:.4g} mmol cm⁻² h⁻¹")
    print(f"  (n_e = {n_e:g}; T = {nhiet:g} °C; P = {ap:g} kPa; {'đã trừ' if hoi else 'KHÔNG trừ'} áp suất hơi nước; S = {s:g} cm²)")
    print("===================================")
    os.makedirs(thu_muc, exist_ok=True)
    try:
        df.to_csv(os.path.join(thu_muc, "hieu_suat_faraday.csv"), index=False, encoding="utf-8-sig")
    except PermissionError:
        print("  (canh bao) khong ghi duoc hieu_suat_faraday.csv - hay dong file dang mo.")
    try:
        import bao_cao
        bao_cao.ghi("fe", df.to_dict("records"))
    except ImportError:
        pass
    return df
