#!/usr/bin/env python3
"""
Xử lý file điện hóa thô (CS Studio): LSV, CV, IT, EIS, ECSA và Tafel. Hỗ trợ VẼ CHỒNG nhiều mẫu lên một hình.

QUY ĐỔI (mặc định):
    E   -> RHE (V)   = E + 0.0592 * 13.8 + 0.098
    i   -> I (mA/cm2) = i * 1000 * 2 / 2.15
    T(s)-> T (h)     = T / 3600
    Z'  giữ nguyên;   Z''  ->  Z'' * (-1)
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

try:                      # cảnh báo dữ liệu & báo cáo: tùy chọn (thiếu file thì bỏ qua)
    import canh_bao
except ImportError:
    canh_bao = None
try:
    import bao_cao
except ImportError:
    bao_cao = None

# ---- mặc định quy đổi ----
PH_MAC_DINH = 13.8
EREF_MAC_DINH = 0.098
NHAN_I_MAC_DINH = 2.0
CHIA_I_MAC_DINH = 2.15
CS_MAC_DINH = 0.040

# ---- tên cột sau quy đổi ----
COT_E = "RHE (V)"
COT_I = "I (mA/cm2)"
COT_T = "T (h)"
NHAN_E = "E (V vs. RHE)"
NHAN_POT = "Potential (V vs RHE)"
NHAN_I = "I (mA/cm²)"

MAU = "#1f77b4"
BANG_MAU = ["#404040", "#f03c3c", "#1a5fd8", "#2aa55a", "#ff7f0e", "#9467bd",
            "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
FIG = (6.0, 4.8)


# ====================== ĐỌC FILE ======================
def doc_file_tho(duong_dan):
    with open(duong_dan, "r", encoding="utf-8", errors="ignore") as f:
        dong = f.read().splitlines()
    nhan = ""
    if dong and dong[0].startswith("CSStudioFile"):
        p = dong[0].split(",")
        nhan = p[1] if len(p) > 1 else ""
    
    # Kiểm tra xem đây có phải là file dữ liệu EIS (.z60) hay không dựa vào từ khóa
    la_file_eis = any("Freq (Hz)" in d or "Z'(Ohm" in d for d in dong)
    
    du_lieu = []
    for d in dong:
        phan = d.replace(",", "\t").split()
        if not phan:
            continue
        try:
            if la_file_eis and len(phan) >= 6:
                # Đối với file EIS: lấy Freq (cột 0), Z' (cột 4), -Z'' (cột 5)
                du_lieu.append([float(phan[0]), float(phan[4]), float(phan[5])])
            elif not la_file_eis and len(phan) >= 3:
                # Đối với các file CV, LSV, IT thông thường
                du_lieu.append([float(x) for x in phan[:3]])
        except ValueError:
            continue
            
    if not du_lieu:
        raise ValueError(f"Không đọc được số liệu trong {duong_dan}")
    return pd.DataFrame(du_lieu, columns=["c1", "c2", "c3"]), nhan


def nhan_dang(nhan, df, ep=None):
    if ep:
        ep = ep.upper()
        if ep in ("CV", "LSV", "TAFEL"):
            return "CV_LSV"
        return ep
    g = nhan.upper()
    if "POTSTATIC" in g or g.endswith("_IT") or "CHRONOAMP" in g:
        return "IT"
    if "EIS" in g or "IMP" in g:
        return "EIS"
    c1, c3 = df["c1"].to_numpy(), df["c3"].to_numpy()
    if np.ptp(c1) < 0.005 and np.ptp(c3) > 10:
        return "IT"
    if len(c1) > 3 and c1.min() > 0 and c1.max() / c1.min() > 100:
        dc1, dc3 = np.diff(c1), np.diff(c3)
        mot_chieu = np.all(dc1 < 0) or np.all(dc1 > 0)
        c3_deu = np.allclose(dc3, dc3[0], rtol=1e-2, atol=1e-6)
        if mot_chieu and not c3_deu:
            return "EIS"
    return "CV_LSV"


# ====================== QUY ĐỔI CHUNG ======================
def quy_doi(df, a):
    d = pd.DataFrame({"E (V)": df["c1"], "i (A/cm2)": df["c2"], "T (s)": df["c3"]})
    if getattr(a, "khong_rhe", False):      # dien the te bao (2 dien cuc): khong quy doi sang RHE
        d[COT_E] = d["E (V)"]
    else:
        d[COT_E] = d["E (V)"] + 0.0592 * a.ph + a.eref
    r_s = float(getattr(a, "r_s", 0.0) or 0.0)
    if r_s:        # bu iR: E_that = E_do - i*Rs*(phan tram bu/100); i la DONG DO THUC (A, cot tho)
        d[COT_E] = d[COT_E] - d["i (A/cm2)"] * r_s * float(getattr(a, "ir_phan_tram", 100.0)) / 100.0
    d[COT_I] = d["i (A/cm2)"] * 1000 * a.nhan_i / a.chia_i
    d[COT_T] = d["T (s)"] / 3600.0
    return d


def rs_tu_eis(duong_dan):
    """Ước lượng Rs (ohm) từ file EIS: Z' tại điểm gần trục thực nhất trong 1/3 vùng tần số cao nhất."""
    tho, _ = doc_file_tho(duong_dan)
    d = xu_ly_eis(tho)
    cao = d.iloc[:max(3, len(d) // 3)]
    k = (cao["-Z'' (ohm)"].abs()).idxmin()
    return float(d.loc[k, "Z' (ohm)"])


# ====================== CV / LSV ======================
def tim_chu_ky(E, nguong=0.002):
    n = len(E)
    huong = np.zeros(n, dtype=int)
    if n < 3:
        return np.ones(n, dtype=int), huong, 0
    h = 1 if E[min(n - 1, 10)] >= E[0] else -1
    cuc_tri, so_doi = E[0], 0
    for j in range(n):
        if h == 1:
            if E[j] > cuc_tri:
                cuc_tri = E[j]
            elif cuc_tri - E[j] > nguong:
                h, cuc_tri, so_doi = -1, E[j], so_doi + 1
        else:
            if E[j] < cuc_tri:
                cuc_tri = E[j]
            elif E[j] - cuc_tri > nguong:
                h, cuc_tri, so_doi = 1, E[j], so_doi + 1
        huong[j] = h
    doi = np.concatenate([[0], np.cumsum(np.diff(huong) != 0)])
    return doi // 2 + 1, huong, so_doi


def xu_ly_cv_lsv(df, a):
    d = quy_doi(df, a)
    chu_ky, huong, so_doi = tim_chu_ky(d["E (V)"].to_numpy())
    d["chu_ky"] = chu_ky
    d["huong_quet"] = np.where(huong > 0, "anodic", "cathodic")
    loai = "CV" if so_doi >= 1 else "LSV"
    if loai == "LSV":
        d["chu_ky"] = 1
    return d[["E (V)", COT_E, "i (A/cm2)", COT_I, "T (s)", COT_T, "chu_ky", "huong_quet"]], loai


def toc_do_quet(d):
    dE = np.diff(d["E (V)"].to_numpy())
    dT = np.diff(d["T (s)"].to_numpy())
    ok = dT > 0
    return float(np.median(np.abs(dE[ok] / dT[ok]))) if ok.any() else float("nan")


def thong_so_cv_lsv(d, loai):
    hang = []
    for ck, g in d.groupby("chu_ky"):
        E, i = g[COT_E].to_numpy(), g[COT_I].to_numpy()
        if loai == "LSV":
            hang.append({"chu_ky": ck, "I_max (mA/cm2)": i.max(), "E tai I_max (V vs RHE)": E[i.argmax()],
                         "E_bat_dau (V vs RHE)": E[0], "E_ket_thuc (V vs RHE)": E[-1]})
            continue
        an, ca = g[g["huong_quet"] == "anodic"], g[g["huong_quet"] == "cathodic"]
        if an.empty or ca.empty:
            continue
        ia, Ea = an[COT_I].to_numpy(), an[COT_E].to_numpy()
        ic, Ec = ca[COT_I].to_numpy(), ca[COT_E].to_numpy()
        Epa, ipa, Epc, ipc = Ea[ia.argmax()], ia.max(), Ec[ic.argmin()], ic.min()
        hang.append({"chu_ky": ck, "Epa (V)": Epa, "Ipa (mA/cm2)": ipa, "Epc (V)": Epc, "Ipc (mA/cm2)": ipc,
                     "dEp (V)": Epa - Epc, "E1/2 (V)": (Epa + Epc) / 2,
                     "|Ipa/Ipc|": abs(ipa / ipc) if ipc != 0 else np.nan})
    return pd.DataFrame(hang)


def chon_chu_ky(d, chu_ky=None):
    """Chu ky dung de ve / tinh toan.
    - Nguoi dung chon (--chu-ky) thi dung dung chu ky do.
    - Mac dinh: chu ky CUOI (da on dinh nhat khi chay nhieu chu ky). Neu chu ky cuoi bi cut ngan
      (do dung do chua xong, < 60% so voi cac chu ky truoc) thi lui ve chu ky day du ngay truoc no."""
    if chu_ky is not None:
        return int(chu_ky)
    cks = sorted(d["chu_ky"].unique())
    if len(cks) >= 2:
        n = d.groupby("chu_ky").size()
        if n.loc[cks[-1]] < 0.6 * n.loc[cks[:-1]].median():
            return int(cks[-2])
    return int(cks[-1])


def duong_cv_lsv(m, chu_ky=None):
    d = m["d"]
    if m["loai"] == "CV":
        ck = chon_chu_ky(d, chu_ky)
        d = d[d["chu_ky"] == ck]
    return d[COT_E].to_numpy(), d[COT_I].to_numpy()


# ====================== TAFEL ======================
def xu_ly_tafel(d, v_min=9.0, v_max=11.0, ten=None, e_min=None, e_max=None):
    i_val = d[COT_I].to_numpy()
    e_val = d[COT_E].to_numpy()

    # LSV có pic oxi hóa nhỏ ở điện thế thấp (vd Cu ~0.87 V): chỉ lấy NHÁNH SAU CÙNG đi lên qua v_min,
    # để pic không lọt vào vùng Tafel. Chỉ áp dụng khi E đơn điệu (LSV); CV hai chiều giữ nguyên.
    theo_e = e_min is not None and e_max is not None
    dE = np.diff(e_val)
    if not theo_e and len(dE) and (np.all(dE >= -1e-9) or np.all(dE <= 1e-9)):
        duoi = np.where(np.abs(i_val) < v_min)[0]
        if len(duoi) and duoi[-1] < len(i_val) - 3:
            i_val, e_val = i_val[duoi[-1] + 1:], e_val[duoi[-1] + 1:]

    # Lấy vùng từ 9mA đến 11mA (hoặc -9mA đến -11mA đối với dòng khử); hoặc theo khoảng điện thế nếu được chọn
    if theo_e:
        mask = (e_val >= min(e_min, e_max)) & (e_val <= max(e_min, e_max)) & (np.abs(i_val) > 0)
        if mask.sum() < 3:
            raise ValueError(f"Vùng điện thế Tafel {e_min:g}~{e_max:g} V có quá ít điểm dữ liệu (<3).")
    else:
        mask = (np.abs(i_val) >= v_min) & (np.abs(i_val) <= v_max)
    sub_i = i_val[mask]
    sub_e = e_val[mask]
    
    if len(sub_i) < 3 and not theo_e:
        # Nếu dòng không đủ rộng, lấy khoảng tự động quanh 10mA
        idx_sort = np.argsort(np.abs(np.abs(i_val) - (v_min + v_max) / 2))
        sel = idx_sort[:min(30, len(i_val))]
        sub_i = i_val[sel]
        sub_e = e_val[sel]
    
    log_j = np.log10(np.abs(sub_i))
    a_slope, b_int = np.polyfit(log_j, sub_e, 1)
    tafel_slope = a_slope * 1000.0  # mV/dec
    
    df_tafel = pd.DataFrame({
        "Log(J)": log_j,
        "Potential (V vs RHE)": sub_e,
        "I (mA/cm2)": sub_i
    }).sort_values("Log(J)").reset_index(drop=True)

    if ten is not None and canh_bao:          # ten=None: không cảnh báo (vd gọi từ hỏi đáp)
        canh_bao.kiem_tra_tafel(df_tafel, tafel_slope, v_min, v_max, ten, theo_e=theo_e)
        if bao_cao:
            bao_cao.ghi("tafel", {"nhan": ten, "he_so_Tafel (mV/dec)": tafel_slope, "so_diem": len(df_tafel),
                                  "vung_dong (mA/cm2)": (f"E {min(e_min, e_max):g} - {max(e_min, e_max):g} V" if theo_e else f"{v_min:g} - {v_max:g}")})
    return df_tafel, tafel_slope, a_slope, b_int


def tafel_a(d, a, ten=None):
    """xu_ly_tafel voi cac tuy chon trong a (vung dong hoac vung dien the)."""
    return xu_ly_tafel(d, float(getattr(a, "tafel_min", 9.0)), float(getattr(a, "tafel_max", 11.0)), ten=ten,
                       e_min=getattr(a, "tafel_e_min", None), e_max=getattr(a, "tafel_e_max", None))


# ====================== IT ======================
def xu_ly_it(df, a, nguong_e=0.01, thoi_gian_on_dinh=30.0):
    d = quy_doi(df, a)
    co = (d["E (V)"] - d["E (V)"].median()).abs() > nguong_e
    t = d["T (s)"].to_numpy()
    lan_cuoi = np.maximum.accumulate(np.where(co.to_numpy(), t, -np.inf))
    d["nhieu"] = (t - lan_cuoi) <= thoi_gian_on_dinh
    return d


def thong_so_it(d, cua_so=200.0):
    d = d[~d["nhieu"]]
    t, i = d["T (s)"].to_numpy(), d[COT_I].to_numpy()
    cuoi = i[t >= t[-1] - cua_so]
    dau = i[t <= t[0] + cua_so]
    return pd.DataFrame([{
        "E_giu (V vs RHE)": d[COT_E].median(),
        "thoi_gian (h)": (t[-1] - t[0]) / 3600,
        "I_dau (mA/cm2)": i[0],
        f"I_TB {int(cua_so)}s_dau (mA/cm2)": dau.mean(),
        f"I_TB {int(cua_so)}s_cuoi (mA/cm2)": cuoi.mean(),
        "I_cuoi (mA/cm2)": i[-1],
        "giu_dong (%)": 100 * cuoi.mean() / dau.mean(),
        "suy_giam (%)": 100 * (1 - cuoi.mean() / dau.mean()),
    }])


def duong_it(muc, noi_tiep=False):
    kq, off = [], 0.0
    for m in muc:
        d = m["d"]
        h = d[~d["nhieu"]]
        t = h[COT_T].to_numpy() + (off if noi_tiep else 0.0)
        kq.append((m, t, h[COT_I].to_numpy()))
        if noi_tiep:
            off += float(d[COT_T].iloc[-1])
    return kq


# ====================== EIS ======================
def xu_ly_eis(df):
    f, zr, zi = df["c1"].to_numpy(), df["c2"].to_numpy(), df["c3"].to_numpy()
    
    d = pd.DataFrame({
        "f (Hz)": f, 
        "Z' (ohm)": zr, 
        "-Z'' (ohm)": -zi  
    })
    
    d["|Z| (ohm)"] = np.hypot(zr, zi)
    d["pha (do)"] = np.degrees(np.arctan2(zi, zr)) 
    return d.sort_values("f (Hz)", ascending=False).reset_index(drop=True)


def thong_so_eis(d):
    Rs = d["Z' (ohm)"].iloc[0]
    Rlow = d["Z' (ohm)"].iloc[-1]
    return pd.DataFrame([{"Rs ~ Z' tai f cao nhat (ohm)": Rs, "Z' tai f thap nhat (ohm)": Rlow,
                          "R_tong - Rs (ohm)": Rlow - Rs, "f_max (Hz)": d["f (Hz)"].iloc[0],
                          "f_min (Hz)": d["f (Hz)"].iloc[-1]}])


# ====================== NẠP MẪU ======================
def mau_cua(a, k):
    if a.mau_file and k < len(a.mau_file) and a.mau_file[k]:
        return a.mau_file[k]
    return BANG_MAU[k % len(BANG_MAU)] if a.chong else a.mau


def nap_muc(p, a, k):
    tho, ghi = doc_file_tho(p)
    ep = (a.loai or "").upper() or None
    nhom = nhan_dang(ghi, tho, ep)
    ten = os.path.splitext(os.path.basename(p))[0]
    nhan = a.nhan[k] if a.nhan and k < len(a.nhan) and a.nhan[k] else ten
    if nhom == "IT":
        d, loai = xu_ly_it(tho, a), "IT"
    elif nhom == "EIS":
        d, loai = xu_ly_eis(tho), "EIS"
    else:
        d, loai = xu_ly_cv_lsv(tho, a)
        if ep in ("CV", "LSV", "TAFEL"):
            loai = ep
    nhom_lap = a.nhom[k] if getattr(a, "nhom", None) and k < len(a.nhom) and a.nhom[k] else ""
    return {"duong_dan": p, "ten": ten, "nhan": nhan, "mau": mau_cua(a, k), "loai": loai, "d": d, "nhom": nhom_lap}


# ====================== VẼ (MATPLOTLIB) ======================
def kieu_khung(ax):
    for s in ax.spines.values():
        s.set_linewidth(1.3)
    ax.minorticks_on()
    ax.tick_params(which="major", direction="out", length=6, width=1.2, top=False, right=False, labelsize=11)
    ax.tick_params(which="minor", direction="out", length=3, width=1.0, top=False, right=False)
    ax.grid(False)


def hoan_thien(fig, ax, ten_ra, legend=False):
    kieu_khung(ax)
    if legend:
        ax.legend(loc="upper left", frameon=True, edgecolor="black", fancybox=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(ten_ra, dpi=200)
    import matplotlib.pyplot as plt
    plt.close(fig)


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def ve_don(m, goc, a):
    plt = _plt()
    loai, d = m["loai"], m["d"]
    if loai in ("CV", "LSV", "TAFEL"):
        fig, ax = plt.subplots(figsize=FIG)
        cac = [chon_chu_ky(d, a.chu_ky)]          # mac dinh: chu ky cuoi
        if a.mau_theo_chu_ky:
            cac = sorted(d["chu_ky"].unique())    # tuy chon: ve tat ca cac chu ky
        for ck in cac:
            g = d[d["chu_ky"] == ck]
            if a.mau_theo_chu_ky:
                ax.plot(g[COT_E], g[COT_I], lw=1.6, label=f"Chu kỳ {ck}")
            else:
                ax.plot(g[COT_E], g[COT_I], lw=1.6, color=m["mau"])
        ax.set_xlabel(NHAN_E)
        ax.set_ylabel(NHAN_I)
        hoan_thien(fig, ax, goc + "_xuly.png", legend=a.mau_theo_chu_ky and len(cac) > 1)
    elif loai == "IT":
        h = d[~d["nhieu"]]
        fig, ax = plt.subplots(figsize=FIG)
        ax.plot(h[COT_T], h[COT_I], lw=1.6, color=m["mau"])
        ax.set_xlabel("T (h)")
        ax.set_ylabel(NHAN_I)
        hoan_thien(fig, ax, goc + "_xuly.png")
    else:
        fig, ax = plt.subplots(figsize=FIG)
        ax.plot(d["Z' (ohm)"], d["-Z'' (ohm)"], "o-", ms=3, lw=1.2, color=m["mau"])
        ax.set_xlabel("Z' (Ω)")
        ax.set_ylabel("-Z'' (Ω)")
        ax.set_aspect("equal", adjustable="datalim")
        hoan_thien(fig, ax, goc + "_Nyquist.png")


def ve_chong(loai, muc, goc, a):
    plt = _plt()
    if loai in ("CV", "LSV"):
        fig, ax = plt.subplots(figsize=FIG)
        for m in muc:
            x, y = duong_cv_lsv(m, a.chu_ky)
            ax.plot(x, y, lw=2, color=m["mau"], label=m["nhan"])
        ax.set_xlabel(NHAN_E)
        ax.set_ylabel(NHAN_I)
        hoan_thien(fig, ax, goc + ".png", legend=True)
    elif loai == "IT":
        fig, ax = plt.subplots(figsize=FIG)
        for m, t, i in duong_it(muc, a.noi_tiep):
            ax.plot(t, i, lw=1.6, color=m["mau"], label=m["nhan"])
        ax.set_xlabel("T (h)")
        ax.set_ylabel(NHAN_I)
        hoan_thien(fig, ax, goc + ".png", legend=True)
    elif loai == "TAFEL":
        fig, ax = plt.subplots(figsize=FIG)
        for m in muc:
            df_t, slope, a_s, b_i = tafel_a(m["d"], a)
            ax.plot(df_t["Log(J)"], df_t["Potential (V vs RHE)"], "o", ms=4, color=m["mau"])
            xx = np.array([df_t["Log(J)"].min(), df_t["Log(J)"].max()])
            ax.plot(xx, a_s * xx + b_i, "-", lw=1.8, color=m["mau"], label=f"{m['nhan']} ({slope:.1f} mV/dec)")
        ax.set_xlabel("Log(J)")
        ax.set_ylabel(NHAN_POT)
        hoan_thien(fig, ax, goc + ".png", legend=True)
    else:
        fig, ax = plt.subplots(figsize=FIG)
        for m in muc:
            ax.plot(m["d"]["Z' (ohm)"], m["d"]["-Z'' (ohm)"], "o-", ms=3, lw=1.4,
                    color=m["mau"], label=m["nhan"])
        ax.set_xlabel("Z' (Ω)")
        ax.set_ylabel("-Z'' (Ω)")
        ax.set_aspect("equal", adjustable="datalim")
        hoan_thien(fig, ax, f"{goc}_Nyquist.png", legend=True)


def bang_so_sanh(loai, muc, a):
    cot = {}
    def them(ten, v):
        k = ten
        while k in cot:
            k += "_"
        cot[k] = pd.Series(v)

    if loai in ("CV", "LSV"):
        for m in muc:
            x, y = duong_cv_lsv(m, a.chu_ky)
            them(f"{m['nhan']} | {NHAN_E}", x)
            them(f"{m['nhan']} | {NHAN_I}", y)
    elif loai == "IT":
        for m, t, i in duong_it(muc, a.noi_tiep):
            them(f"{m['nhan']} | T (h)", t)
            them(f"{m['nhan']} | {NHAN_I}", i)
    elif loai == "TAFEL":
        for m in muc:
            df_t, slope, _, _ = tafel_a(m["d"], a, ten=m["nhan"])
            them(f"{m['nhan']} | Log(J)", df_t["Log(J)"].to_numpy())
            them(f"{m['nhan']} | Potential (V vs RHE)", df_t["Potential (V vs RHE)"].to_numpy())
    else:
        for m in muc:
            for c in ("f (Hz)", "Z' (ohm)", "-Z'' (ohm)"):
                them(f"{m['nhan']} | {c}", m["d"][c].to_numpy())
    return pd.DataFrame(cot)


# ====================== ECSA ======================
def noi_suy_dong(g, e_chon):
    kq = {}
    for h in ("anodic", "cathodic"):
        s = g[g["huong_quet"] == h].sort_values(COT_E)
        kq[h] = float(np.interp(e_chon, s[COT_E], s[COT_I]))
    return kq["anodic"], kq["cathodic"]


def tinh_ecsa(files, a, e_chon, cs, chu_ky, goc_ra, ve=True):
    cac = []
    plt = _plt() if ve else None
    fig, ax = plt.subplots(figsize=FIG) if ve else (None, None)
    
    bo_qua = {os.path.normcase(os.path.abspath(x)) for x in (getattr(a, "ecsa_bo_qua", None) or [])}
    for k, p in enumerate(files):
        if os.path.normcase(os.path.abspath(p)) in bo_qua:
            print(f"  bo qua {os.path.basename(p)} (nguoi dung bo tick khoi ECSA)")
            continue
        tho, _ = doc_file_tho(p)
        d, loai = xu_ly_cv_lsv(tho, a)
        if loai != "CV":
            print(f"  bo qua {os.path.basename(p)} (khong phai CV)")
            continue
        ck = chon_chu_ky(d, chu_ky)
        g = d[d["chu_ky"] == ck]
        v_rate = toc_do_quet(d) * 1000  # mV/s
        print(f"  {os.path.basename(p)}: dung chu ky {ck}/{int(d['chu_ky'].max())}")
        cac.append((p, d, g, v_rate))
        if ve:
            ax.plot(g[COT_E], g[COT_I], lw=1.4, label=f"{v_rate:.0f} mV/s")

    if len(cac) < 2:
        raise ValueError("ECSA can it nhat 2 file CV o 2 toc do quet khac nhau (sau khi bo cac file da bo tick)")

    if ve:
        ax.set_xlabel(NHAN_E)
        ax.set_ylabel(NHAN_I)
        hoan_thien(fig, ax, goc_ra + "_CV_DaTocDo.png", legend=True)

    lo = max(g[COT_E].min() for _, _, g, _ in cac)
    hi = min(g[COT_E].max() for _, _, g, _ in cac)
    if e_chon is None:
        if hi <= lo:
            raise ValueError("Cac file CV khong co vung dien the chung de lay diem chinh giua")
        e_chon = (lo + hi) / 2
        print(f"  Dien the lay dong tu dong = {e_chon:.4f} V vs RHE (giua vung {lo:.3f} ~ {hi:.3f} V)")

    hang = []
    for p, d, g, v_rate in cac:
        ja, jc = noi_suy_dong(g, e_chon)
        hang.append({"file": os.path.basename(p), "chu_ky": int(g["chu_ky"].iloc[0]), "toc_do_quet (mV/s)": v_rate,
                     "Ja (mA/cm2)": ja, "Jc (mA/cm2)": jc, "(Ja-Jc)/2 (mA/cm2)": (ja - jc) / 2})
    b = pd.DataFrame(hang).sort_values("toc_do_quet (mV/s)").reset_index(drop=True)
    v = b["toc_do_quet (mV/s)"].to_numpy() / 1000
    y = b["(Ja-Jc)/2 (mA/cm2)"].to_numpy()
    he_so, tung = np.polyfit(v, y, 1)
    r2 = 1 - np.sum((y - (he_so * v + tung)) ** 2) / np.sum((y - y.mean()) ** 2)
    ecsa = he_so / cs
    kq = pd.DataFrame([{"E_lay_dong (V vs RHE)": e_chon, "Cdl (mF/cm2)": he_so, "R2": r2,
                        "Cs (mF/cm2)": cs, "ECSA (cm2_ECSA / cm2_hinh_hoc)": ecsa, "so_diem": len(b)}])
    b.to_csv(goc_ra + "_ECSA_diem.csv", index=False)
    kq.to_csv(goc_ra + "_ECSA.csv", index=False)
    if canh_bao:
        canh_bao.kiem_tra_ecsa(b, he_so, tung, r2, e_chon,
                               [(g, vr, os.path.basename(p)) for p, _, g, vr in cac])
    if bao_cao:
        bao_cao.ghi("ecsa_diem", b)
        bao_cao.ghi("ecsa", kq)
    
    if ve:
        fig, ax = plt.subplots(figsize=FIG)
        ax.plot(b["toc_do_quet (mV/s)"], y, "o", color=MAU, ms=7)
        xs = np.linspace(0, v.max(), 50)
        ax.plot(xs * 1000, he_so * xs + tung, "-", color=MAU, lw=1.8)
        ax.set_xlabel("Tốc độ quét (mV/s)")
        ax.set_ylabel("(Ja − Jc)/2 (mA/cm²)")
        ax.set_title(f"Cdl = {he_so:.3f} mF/cm², ECSA = {ecsa:.3f} cm²", fontsize=11)
        hoan_thien(fig, ax, goc_ra + "_ECSA.png")
        
    print(b.round(4).to_string(index=False))
    print(kq.round(4).to_string(index=False))
    return b, he_so, tung, r2, e_chon, kq


def xuat_cv_json(files, a, chu_ky, duong):
    """Ghi dữ liệu CV (chu kỳ được chọn) ra JSON cho cửa sổ ECSA tương tác của giao diện."""
    import json
    ra = []
    for k, p in enumerate(files):
        try:
            tho, _ = doc_file_tho(p)
            d, loai = xu_ly_cv_lsv(tho, a)
        except Exception as e:
            print(f"  bo qua {os.path.basename(p)}: {e}")
            continue
        if loai != "CV":
            print(f"  bo qua {os.path.basename(p)} (khong phai CV)")
            continue
        ck = chon_chu_ky(d, chu_ky)
        g = d[d["chu_ky"] == ck]
        nhan = a.nhan[k] if getattr(a, "nhan", None) and k < len(a.nhan) and a.nhan[k] else os.path.splitext(os.path.basename(p))[0]
        mau = a.mau_file[k] if getattr(a, "mau_file", None) and k < len(a.mau_file) and a.mau_file[k] else BANG_MAU[k % len(BANG_MAU)]
        ra.append({"path": os.path.abspath(p), "nhan": nhan, "mau": mau, "v": float(toc_do_quet(d) * 1000), "chu_ky": int(ck),
                   "e": [float(x) for x in g[COT_E]], "i": [float(x) for x in g[COT_I]],
                   "a": [1 if h == "anodic" else 0 for h in g["huong_quet"]]})
    with open(duong, "w", encoding="utf-8") as f:
        json.dump({"cv": ra}, f)
    print(f"  da xuat {len(ra)} duong CV: {duong}")


# ====================== THAM SỐ DÒNG LỆNH ======================
def them_tham_so_chung(ap):
    ap.add_argument("files", nargs="+")
    ap.add_argument("--ph", type=float, default=PH_MAC_DINH)
    ap.add_argument("--eref", type=float, default=EREF_MAC_DINH)
    ap.add_argument("--nhan-i", type=float, default=NHAN_I_MAC_DINH)
    ap.add_argument("--chia-i", type=float, default=CHIA_I_MAC_DINH)
    ap.add_argument("--loai", default=None)
    ap.add_argument("--chu-ky", type=int, default=None)
    ap.add_argument("--mau", default=MAU)
    ap.add_argument("--mau-theo-chu-ky", action="store_true")
    ap.add_argument("--nhan", action="append", default=[])
    ap.add_argument("--mau-file", action="append", default=[])
    ap.add_argument("--chong", action="store_true")
    ap.add_argument("--noi-tiep", action="store_true")
    ap.add_argument("--ecsa", action="store_true")
    ap.add_argument("--e-ecsa", type=float, default=None)
    ap.add_argument("--ecsa-bo-qua", action="append", default=[], help="file CV bỏ khỏi ECSA (có thể lặp lại)")
    ap.add_argument("--xuat-cv-json", default=None, help="chỉ ghi dữ liệu CV ra JSON (cho cửa sổ ECSA tương tác)")
    ap.add_argument("--cs", type=float, default=CS_MAC_DINH)
    ap.add_argument("--tafel-min", type=float, default=9.0)
    ap.add_argument("--tafel-max", type=float, default=11.0)
    ap.add_argument("--thu-muc-ra", default=None)
    ap.add_argument("--khong-canh-bao", action="store_true", help="khong in canh bao (van ghi nhan)")
    ap.add_argument("--bao-cao", default=None, help="thu muc de xuat bao_cao_tong_hop.xlsx (bo trong = khong xuat)")
    ap.add_argument("--i-muc-tieu", default="10", help="cac mat do dong muc tieu (mA/cm2) cho bao cao, cach nhau dau phay")
    ap.add_argument("--e-can-bang", type=float, default=1.23, help="dien the can bang (V) de tinh qua the trong bao cao")
    ap.add_argument("--tafel-e-min", type=float, default=None, help="vung Tafel theo dien the (V): can ca --tafel-e-min va --tafel-e-max")
    ap.add_argument("--tafel-e-max", type=float, default=None)
    ap.add_argument("--khong-rhe", action="store_true", help="khong quy doi sang RHE (dien the te bao 2 dien cuc)")
    ap.add_argument("--khong-qua-the", action="store_true", help="khong tinh qua the (vd oxi hoa glucose): xep hang theo dien the")
    ap.add_argument("--nhom", action="append", default=[], help="ten nhom lap lai cua tung file (cung thu tu file)")
    ap.add_argument("--fe-v-h2", default=None, help="the tich khi thu duoc (mL) cua tung mau IT, cach nhau dau phay")
    ap.add_argument("--fe-nhiet-do", type=float, default=25.0)
    ap.add_argument("--fe-ap-suat", type=float, default=101.325, help="kPa")
    ap.add_argument("--fe-n", type=float, default=2.0, help="so electron (H2: 2, O2: 4)")
    ap.add_argument("--fe-khong-hoi-nuoc", action="store_true")
    ap.add_argument("--fit-eis", action="store_true", help="fit EIS bang mach Rs + (Rct // CPE)")
    ap.add_argument("--tai-lieu", default=None, help="file CSV cac nghien cuu khac de so sanh")
    ap.add_argument("--tof-cv", action="store_true", help="tinh TOF = |I|/(n F N), N = Q/(n F), Q = dien tich CV / toc do quet")
    ap.add_argument("--tof-e-min", type=float, default=None)
    ap.add_argument("--tof-e-max", type=float, default=None)
    ap.add_argument("--tof-n", type=float, default=2.0, help="so electron trao doi trong cong thuc TOF")
    ap.add_argument("--qs-tof", action="store_true", help="cong cu Qs-LSV + TOF: file CV -> N; thu muc Qs-LSV -> I theo E")
    ap.add_argument("--qs-thu-muc", default=None, help="thu muc chung chua file Qs-LSV (tu ghep theo ten mau)")
    ap.add_argument("--qs-lsv", action="append", default=[], help="Qs-LSV cua tung file CV theo thu tu (thu muc hoac file; nhieu muc cach nhau '|'; rong = ghep tu dong)")
    ap.add_argument("--qs-nguong", type=float, default=3.0, help="mV: E nhay qua nguong nay = buoc dien the moi")
    ap.add_argument("--qs-duoi", type=float, default=0.0, help="%% diem cuoi cua moi buoc de lay trung binh (0 = diem cuoi cung)")
    ap.add_argument("--qs-dung-tho", action="store_true", help="dung dong tho (A) thay cho dong da quy doi (mA/cm2)")
    ap.add_argument("--qs-da-rhe", action="store_true", help="E trong file Qs-LSV da la RHE (khong cong pH, Eref)")
    ap.add_argument("--tof-n-q", type=float, default=None, help="so electron khi tinh N = Q/(n F); bo trong = bang --tof-n")
    ap.add_argument("--tof-v", default=None, help="toc do quet (mV/s) de tinh Q; 1 so chung hoac moi mau 1 so (cach nhau dau ;); bo trong = lay tu du lieu")
    ap.add_argument("--tof-dien-tich", default="kin", choices=["kin", "tong"], help="kin = |tich phan vong kin I dE|; tong = tich phan |I||dE| hai chieu")
    ap.add_argument("--tof-chieu", default="ca_hai", choices=["ca_hai", "catot", "anot"], help="chieu quet dung de ve TOF")
    ap.add_argument("--tof-rhe", action="store_true", help="loc cua so theo dien the da quy doi RHE (mac dinh: dien the trong file)")
    ap.add_argument("--hinh-bai-bao", action="store_true", help="xuat hinh ghep nhieu o chuan bai bao")
    ap.add_argument("--hinh-cot", type=int, default=2, help="1 = cot don (8.6 cm), 2 = cot doi (17.8 cm)")
    ap.add_argument("--hinh-dang", default="png,pdf,tiff")
    ap.add_argument("--hinh-dpi", type=int, default=600)
    ap.add_argument("--hinh-o", action="append", default=None,
                    help="cac o cua MOT hinh theo thu tu (A,B,C...): lsv,tafel,eis,it,cot; lap lai de tao nhieu hinh; bo trong = tu chon")
    ap.add_argument("--nhan-hinh", action="append", default=[], help="ten mau rieng trong hinh bai bao (theo thu tu file; rong = dung nhan goc)")
    ap.add_argument("--hinh-chu", default="hoa", choices=["hoa", "thuong"], help="(A) hay (a)")
    ap.add_argument("--pho-kieu", default="xrd", help="xrd | raman | xps | ftir | khac")
    ap.add_argument("--pho-doi", type=float, default=1.1, help="khoang doi giua cac pho khi xep chong")
    ap.add_argument("--pho-dinh", type=int, default=0, help="so dinh danh dau tren moi pho")
    ap.add_argument("--pho-khong-chuan-hoa", action="store_true")
    ap.add_argument("--pho-x-min", type=float, default=None)
    ap.add_argument("--pho-x-max", type=float, default=None)
    ap.add_argument("--pho-nhan-x", default=None)
    ap.add_argument("--thu-muc-tong-hop", default=None, help="thu muc chua cac ket qua tong hop (so sanh, FE, fit EIS, hinh bai bao)")
    ap.add_argument("--r-s", type=float, default=0.0, help="dien tro dung dich Rs (ohm) de bu iR; 0 = khong bu")
    ap.add_argument("--ir-phan-tram", type=float, default=100.0, help="phan tram iR duoc bu (mac dinh 100)")
    ap.add_argument("--so-sanh", action="store_true", help="xuat bang + bieu do so sanh cac mau (can thu-muc-ra)")
    ap.add_argument("--qua-the-ht", default="300", help="cac qua the khao sat (mV) de tinh hoat do khoi/TOF, cach nhau dau phay")
    ap.add_argument("--tai-trong", default=None, help="tai trong xuc tac (mg/cm2) -> hoat do khoi (A/g)")
    ap.add_argument("--so-mol-tam", default=None, help="so tam hoat dong (umol/cm2) -> TOF")
    ap.add_argument("--khoi-luong-mol", default=None, help="khoi luong mol M (g/mol) de uoc tinh so tam tu tai trong")
    ap.add_argument("--ti-le-tam", default="1", help="ti le nguyen tu hoat dong (0-1) khi tinh so tam tu tai trong")
    ap.add_argument("--n-e", default="4", help="so electron cho moi phan tu san pham (OER 4, HER 2)")


def ap_dung_che_do(a):
    """Nhan truc theo che do (RHE / dien the te bao)."""
    global NHAN_E, NHAN_POT
    if getattr(a, "khong_rhe", False):
        NHAN_E, NHAN_POT = "Cell voltage (V)", "Cell voltage (V)"
    else:
        NHAN_E, NHAN_POT = "E (V vs. RHE)", "Potential (V vs RHE)"


def khoi_dong_canh_bao(a):
    ap_dung_che_do(a)
    if canh_bao:
        canh_bao.reset()
        canh_bao.dat_im_lang(getattr(a, "khong_canh_bao", False))
    if bao_cao:
        bao_cao.reset()


def kiem_tra_cac_muc(muc, a):
    r_s = float(getattr(a, "r_s", 0.0) or 0.0)
    if r_s and canh_bao:
        pt = float(getattr(a, "ir_phan_tram", 100.0))
        for m in muc:
            if m["loai"] in ("CV", "LSV", "TAFEL"):
                dmax = float(np.abs(m["d"]["i (A/cm2)"]).max()) * r_s * pt / 100.0 * 1000
                canh_bao.them(canh_bao.LUU_Y, f"đã bù iR với Rs = {r_s:g} Ω ({pt:g}%): E dịch tối đa {dmax:.0f} mV ở dòng lớn nhất. "
                              "Hãy chắc chắn Rs lấy từ EIS đo ở cùng điều kiện.", m["nhan"])
                if dmax > 300:
                    canh_bao.them(canh_bao.CANH_BAO, f"mức bù iR rất lớn ({dmax:.0f} mV): kiểm tra lại Rs (đơn vị Ω) và hệ số nhân/chia dòng.", m["nhan"])
    if canh_bao:
        for m in muc:
            try:
                canh_bao.kiem_tra_muc(m, a)
            except Exception as e:
                print(f"  (canh bao) khong kiem tra duoc {m.get('nhan', '')}: {e}")


def thu_tong_hop(a):
    return getattr(a, "thu_muc_tong_hop", None) or getattr(a, "bao_cao", None) or getattr(a, "thu_muc_ra", None)


def ket_thuc(a, ds, muc=None):
    """Xuất bảng so sánh, FE, fit EIS + báo cáo Excel (nếu được yêu cầu) và tổng kết cảnh báo."""
    thu_ra = thu_tong_hop(a)
    if thu_ra and getattr(a, "hinh_bai_bao", False) and not getattr(a, "ecsa", False):
        try:
            import hinh_bai_bao
            if muc is None:
                muc = [nap_muc(p, a, k) for k, p in enumerate(ds)]
            hinh_bai_bao.tao_hinh(muc, a, thu_ra)
        except Exception as e:
            print(f"  (canh bao) khong tao duoc hinh bai bao: {e}")
    if thu_ra and getattr(a, "tof_cv", False) and not getattr(a, "ecsa", False):
        try:
            import tof_cv
            if muc is None:
                muc = [nap_muc(p, a, k) for k, p in enumerate(ds)]
            tof_cv.chay(muc, a, thu_ra, ve=not getattr(a, "da_ve_tof_origin", False))
        except Exception as e:
            print(f"  (canh bao) khong tinh duoc TOF tu CV: {e}")
    if thu_ra and not getattr(a, "ecsa", False) and (getattr(a, "fe_v_h2", None) or getattr(a, "fit_eis", False)):
        try:
            if muc is None:
                muc = [nap_muc(p, a, k) for k, p in enumerate(ds)]
            if getattr(a, "fe_v_h2", None):
                import hieu_suat
                hieu_suat.xuat_fe(muc, a, thu_ra)
            if getattr(a, "fit_eis", False):
                import fit_eis
                fit_eis.xuat_fit(muc, a, thu_ra)
        except Exception as e:
            print(f"  (canh bao) khong hoan thanh FE/fit EIS: {e}")
    if getattr(a, "so_sanh", False) and thu_tong_hop(a):
        try:
            import so_sanh
            if muc is None and not getattr(a, "ecsa", False):
                muc = [nap_muc(p, a, k) for k, p in enumerate(ds)]
            if muc:
                so_sanh.xuat_so_sanh(muc, a, thu_tong_hop(a))
        except Exception as e:
            print(f"  (canh bao) khong tao duoc bang so sanh: {e}")
    if getattr(a, "bao_cao", None) and bao_cao:
        try:
            duong = bao_cao.xuat(a, ds, a.bao_cao)
            print(f"  bao cao: {duong}")
        except Exception as e:
            print(f"  (canh bao) khong xuat duoc bao cao: {e}")
    if canh_bao and canh_bao.DANH_SACH:
        n = canh_bao.dem_canh_bao()
        print(f"\n>>> TỔNG KẾT: {n} cảnh báo, {len(canh_bao.DANH_SACH) - n} lưu ý/gợi ý (xem các dòng [CẢNH BÁO] / [LƯU Ý] / [GỢI Ý] ở trên).")


def mo_rong_file(files):
    ds = []
    for p in files:
        ds += glob.glob(p) or [p]
    return ds


def goc_ra(a, p):
    ten = os.path.splitext(os.path.basename(p))[0]
    if a.thu_muc_ra:
        os.makedirs(a.thu_muc_ra, exist_ok=True)
        return os.path.join(a.thu_muc_ra, ten)
    return os.path.splitext(p)[0]


def main():
    ap = argparse.ArgumentParser()
    them_tham_so_chung(ap)
    ap.add_argument("--khong-ve", action="store_true")
    a = ap.parse_args()
    ds = mo_rong_file(a.files)
    mat = [p for p in ds if not os.path.isfile(p)]
    if mat:
        print("[LOI] Khong tim thay file (da doi ten/di chuyen, hoac o dia/USB chua cam):")
        for p in mat:
            print("   - " + p)
        sys.exit(2)
    khoi_dong_canh_bao(a)

    if (a.loai or "").upper() == "PHO":
        import pho_xy
        pho_xy.chay(ds, a)
        return
    if getattr(a, "qs_tof", False):
        import qs_lsv
        a.chong = False
        muc = [nap_muc(p, a, k) for k, p in enumerate(ds)]
        qs_lsv.chay(muc, a, a.thu_muc_ra or os.path.dirname(os.path.abspath(ds[0])), ve=not a.khong_ve)
        return
    if getattr(a, "xuat_cv_json", None):
        xuat_cv_json(ds, a, a.chu_ky, a.xuat_cv_json)
        return
    if a.ecsa:
        goc = goc_ra(a, ds[0])
        tinh_ecsa(ds, a, a.e_ecsa, a.cs, a.chu_ky, goc, ve=not a.khong_ve)
        ket_thuc(a, ds)
        return

    muc = [nap_muc(p, a, k) for k, p in enumerate(ds)]
    kiem_tra_cac_muc(muc, a)
    for m in muc:
        goc = goc_ra(a, m["duong_dan"])
        d, loai = m["d"], m["loai"]
        d.to_csv(goc + "_xuly.csv", index=False)
        if loai in ("CV", "LSV", "TAFEL"):
            t = thong_so_cv_lsv(d, "CV" if loai == "CV" else "LSV")
        elif loai == "IT":
            t = thong_so_it(d)
        else:
            t = thong_so_eis(d)
        t.to_csv(goc + "_thongso.csv", index=False)
        if not a.khong_ve and not a.chong:
            ve_don(m, goc, a)

    if a.chong:
        thu_muc = a.thu_muc_ra or os.path.dirname(os.path.abspath(ds[0]))
        os.makedirs(thu_muc, exist_ok=True)
        loai_list = set(m["loai"] for m in muc)
        for loai in loai_list:
            nhom = [m for m in muc if m["loai"] == loai]
            if not nhom:
                continue
            goc = os.path.join(thu_muc, "so_sanh_" + loai)
            bang_so_sanh(loai, nhom, a).to_csv(goc + ".csv", index=False)
            if not a.khong_ve:
                ve_chong(loai, nhom, goc, a)
    ket_thuc(a, ds, muc)


if __name__ == "__main__":
    main()
