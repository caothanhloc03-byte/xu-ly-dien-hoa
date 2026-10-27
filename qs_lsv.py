# -*- coding: utf-8 -*-
"""
CÔNG CỤ Qs-LSV (quasi-steady-state LSV) VÀ TOF

Qs-LSV: đo nhiều bước điện thế (mỗi bước giữ đủ lâu để dòng ổn định). Với MỖI bước chỉ lấy điểm CUỐI (E, I)
(hoặc trung bình % điểm cuối) -> ghép lại thành một đường phân cực "gần ổn định": bộ dữ liệu Qs-LSV.
  - Mỗi file có thể là 1 bước (i–t ở một điện thế) hoặc nhiều bước nối tiếp (bậc thang): app tự tách bước khi E nhảy
    quá ngưỡng (mặc định 3 mV) hoặc khi trục thời gian bị đặt lại.
  - E: quy đổi sang RHE như thường (pH, Eref, bù iR nếu có).  I: dòng ĐÃ QUY ĐỔI (mA/cm², hệ số nhân/chia của app).

TOF (s⁻¹) = |J_Qs-LSV(E)| / (n · F · N),   N (mol/cm²) = Q / (n_Q · F),   Q (C/cm²) = diện tích CV / tốc độ quét
(J, Q đều theo dòng đã quy đổi trên cm² điện cực; Q lấy từ một vòng CV của cùng mẫu - xem tof_cv.tinh_q).
Tùy chọn --qs-dung-tho: dùng dòng thô (A) cho cả I và Q.

Hình: (A) đường CV (J theo E vs RHE), (B) TOF theo E vs RHE (các điểm Qs-LSV).
Ghép mẫu: mỗi mẫu CV có thư mục/ file Qs-LSV riêng (--qs-lsv), hoặc để app tự ghép theo tên trong một thư mục chung (--qs-thu-muc).
"""
import copy
import os
import re

import numpy as np
import pandas as pd

import tof_cv

DUOI = (".txt", ".csv", ".dat")
C_E, C_I, C_J, C_TOF = "E RHE (V)", "I_tho (A)", "J (mA/cm2)", "TOF (s-1)"


# ---------------------------------------------------------------- đọc & tách bước
def liet_ke_file(p):
    """File dữ liệu trong p (file đơn, thư mục - gồm thư mục con)."""
    if os.path.isfile(p):
        return [p]
    kq = []
    for goc, ds_con, ds_file in os.walk(p):
        ds_con[:] = sorted(d for d in ds_con if not d.startswith(("_", ".")))
        kq += [os.path.join(goc, f) for f in sorted(ds_file) if f.lower().endswith(DUOI) and not f.startswith("~$")]
    return kq


def tach_buoc(e, t, nguong_v):
    """Chỉ số [đầu, cuối] của từng bước: E nhảy > nguong_v hoặc thời gian lùi lại."""
    n = len(e)
    cat = [k + 1 for k in range(n - 1) if abs(e[k + 1] - e[k]) > nguong_v or t[k + 1] < t[k]]
    dau = [0] + cat
    cuoi = [c - 1 for c in cat] + [n - 1]
    return list(zip(dau, cuoi))


def diem_cuoi_file(p, a, nguong_mv=3.0, duoi_pct=0.0, canh_bao=None):
    """Bảng các điểm cuối của mọi bước trong 1 file (E đã quy đổi RHE, I thô)."""
    import xu_ly_dien_hoa as xl
    tho, _ = xl.doc_file_tho(p)
    a2 = copy.copy(a)
    if getattr(a, "qs_da_rhe", False):
        a2.khong_rhe = True                              # E trong file đã là RHE -> không cộng pH/Eref
    d = xl.quy_doi(tho, a2)
    e_tho = d["E (V)"].to_numpy(float)
    t = d["T (s)"].to_numpy(float)
    hang = []
    for k, (i0, i1) in enumerate(tach_buoc(e_tho, t, nguong_mv / 1000.0)):
        if i1 - i0 + 1 >= 20 and np.ptp(e_tho[i0:i1 + 1]) > 5 * nguong_mv / 1000 and canh_bao is not None:
            canh_bao.append(f"{os.path.basename(p)}: bước {k + 1} có E đổi {np.ptp(e_tho[i0:i1 + 1]) * 1000:.0f} mV - có vẻ là LSV liên tục, "
                            "không phải bước điện thế; chỉ lấy điểm cuối.")
        so = i1 - i0 + 1
        m = max(1, int(round(so * duoi_pct / 100.0))) if duoi_pct and duoi_pct > 0 else 1
        sl = slice(i1 - m + 1, i1 + 1)
        hang.append({C_E: float(d[xl.COT_E].to_numpy(float)[sl].mean()), C_I: float(d["i (A/cm2)"].to_numpy(float)[sl].mean()),
                     C_J: float(d[xl.COT_I].to_numpy(float)[sl].mean()), "T cuối (s)": float(t[i1]), "bước": k + 1,
                     "số điểm bước": so, "file": os.path.basename(p)})
    return pd.DataFrame(hang)


def doc_qs_lsv(ds_file, a, canh_bao=None):
    nguong = float(getattr(a, "qs_nguong", 3.0) or 3.0)
    duoi = float(getattr(a, "qs_duoi", 0.0) or 0.0)
    kq = []
    for p in ds_file:
        try:
            b = diem_cuoi_file(p, a, nguong, duoi, canh_bao)
        except ValueError as e:
            print(f"  (canh bao) bo qua {os.path.basename(p)}: {e}")
            continue
        if not b.empty:
            kq.append(b)
    if not kq:
        return pd.DataFrame()
    return pd.concat(kq, ignore_index=True).sort_values(C_E).reset_index(drop=True)


# ---------------------------------------------------------------- ghép mẫu CV với file Qs-LSV
def ghep_tu_dong(nhan_cv, thu_muc):
    """{nhan: [file Qs]}: thư mục con trùng tên nhãn, hoặc file có tên chứa nhãn (nhãn dài nhất thắng).
    Chỉ 1 mẫu mà không khớp tên nào -> lấy mọi file trong thư mục."""
    tat_ca = liet_ke_file(thu_muc)
    kq = {n: [] for n in nhan_cv}
    def chuan(x):
        return re.sub(r"[^0-9a-z]+", "_", x.lower()).strip("_")
    thap = {n: chuan(n) for n in nhan_cv if n}
    for p in tat_ca:
        phan = [chuan(x) for x in os.path.relpath(p, thu_muc).replace("\\", "/").split("/")]
        tot = None
        for n, l in thap.items():
            if l in phan[:-1] or re.search(r"(?<![0-9a-z])" + re.escape(l) + r"(?![0-9a-z])", phan[-1]):
                if tot is None or len(l) > len(tot[1]):
                    tot = (n, l)
        if tot:
            kq[tot[0]].append(p)
    if len(nhan_cv) == 1 and not any(kq.values()):
        kq[nhan_cv[0]] = tat_ca
    return kq


# ---------------------------------------------------------------- tính & vẽ
def chay(muc, a, thu_muc, ve=True):
    """muc: các mẫu CV (xl.nap_muc). Trả về (bảng tổng hợp, danh sách dict) hoặc None."""
    import xu_ly_dien_hoa as xl
    cv = [m for m in muc if m["loai"] in ("CV", "LSV")]
    if not cv:
        raise ValueError("Cần ít nhất một file CV.")
    n_e = float(getattr(a, "tof_n", 2.0) or 2.0)
    n_q = float(getattr(a, "tof_n_q", None) or n_e)
    if n_e <= 0 or n_q <= 0:
        raise ValueError("n (số electron) phải dương.")
    e1, e2 = getattr(a, "tof_e_min", None), getattr(a, "tof_e_max", None)
    e1 = None if e1 is None else float(e1)
    e2 = None if e2 is None else float(e2)
    if e1 is None or e2 is None:
        e1 = e2 = None
    rhe = bool(getattr(a, "tof_rhe", False))
    kieu_dt = getattr(a, "tof_dien_tich", "kin") or "kin"
    tho = bool(getattr(a, "qs_dung_tho", False))
    ds_v = tof_cv._ds_so(getattr(a, "tof_v", None), len(cv), "Tốc độ quét (mV/s)")
    qs_rieng = list(getattr(a, "qs_lsv", None) or [])
    thu_chung = getattr(a, "qs_thu_muc", None)
    tu_dong = ghep_tu_dong([m["nhan"] for m in cv], thu_chung) if thu_chung else {}
    os.makedirs(thu_muc, exist_ok=True)
    hang, cac = [], []
    for k, (m, v) in enumerate(zip(cv, ds_v)):
        ds_file = []
        if k < len(qs_rieng) and qs_rieng[k]:
            for dd_ in str(qs_rieng[k]).split("|"):
                if dd_.strip():
                    ds_file += liet_ke_file(dd_.strip())
        elif m["nhan"] in tu_dong:
            ds_file = tu_dong[m["nhan"]]
        if not ds_file:
            print(f"  (canh bao) {m['nhan']}: khong co file Qs-LSV - bo qua mau nay.")
            continue
        try:
            tp, cv_chu_ky = tof_cv.tinh_q(m["d"], getattr(a, "chu_ky", None), e1, e2, v, rhe, xl.chon_chu_ky, kieu_dt, tho)
        except ValueError as e:
            print(f"  (canh bao) {m['nhan']}: khong tinh duoc Q tu CV - {e}")
            continue
        if tp.get("canh_bao"):
            print(f"  (canh bao) {m['nhan']}: {tp['canh_bao']}")
        cb = []
        qs = doc_qs_lsv(ds_file, a, cb)
        for c in dict.fromkeys(cb):
            print(f"  (canh bao) {c}")
        if qs.empty:
            print(f"  (canh bao) {m['nhan']}: khong doc duoc diem nao tu {len(ds_file)} file Qs-LSV.")
            continue
        n_mol = tp["Q_C"] / (n_q * tof_cv.FARADAY)
        i_dung = np.abs(qs[C_I]) if tho else np.abs(qs[C_J]) / 1000.0              # A (thô) hoặc A/cm² (quy đổi)
        qs[C_TOF] = i_dung / (n_e * tof_cv.FARADAY * n_mol)
        k_max = int(qs[C_TOF].idxmax())
        hang.append({"Nhãn": m["nhan"], "Tốc độ quét CV (mV/s)": tp["v_mV_s"], "Diện tích CV (A·V)": tp["dien_tich_AV"],
                     ("Q (mC)" if tho else "Q (mC/cm2)"): tp["Q_C"] * 1e3,
                     ("N (µmol)" if tho else "N (µmol/cm2)"): n_mol * 1e6, "n (TOF)": n_e, "n (tính N)": n_q,
                     "Số điểm Qs-LSV": len(qs), "Số file Qs-LSV": len(ds_file),
                     "E RHE nhỏ nhất (V)": float(qs[C_E].min()), "E RHE lớn nhất (V)": float(qs[C_E].max()),
                     "TOF lớn nhất (s-1)": float(qs.loc[k_max, C_TOF]), "E RHE tại TOF lớn nhất (V)": float(qs.loc[k_max, C_E])})
        cac.append({"m": m, "qs": qs, "cv": cv_chu_ky})
        ten = "".join(c if c.isalnum() or c in "-_" else "_" for c in m["nhan"])
        try:
            qs.to_csv(os.path.join(thu_muc, f"QsLSV_{ten}.csv"), index=False, encoding="utf-8-sig")
        except PermissionError:
            print(f"  (canh bao) khong ghi duoc QsLSV_{ten}.csv - hay dong file dang mo.")
    if not hang:
        return None
    tong = pd.DataFrame(hang)
    print("\n======== Qs-LSV & TOF  (TOF = |I| / (n·F·N), N = Q/(n·F), Q = diện tích CV / tốc độ quét; "
          + ("I thô, A" if tho else "I quy đổi, mA/cm²") + ") ========")
    for r in hang:
        print(f"  {r['Nhãn']}: {r['Số điểm Qs-LSV']} điểm Qs-LSV ({r['Số file Qs-LSV']} file) | Q = {r['Q (mC)' if tho else 'Q (mC/cm2)']:.4g} {'mC' if tho else 'mC/cm²'} | "
              f"N = {r['N (µmol)' if tho else 'N (µmol/cm2)']:.4g} {'µmol' if tho else 'µmol/cm²'} | "
              f"TOF max = {r['TOF lớn nhất (s-1)']:.4g} s⁻¹ tại {r['E RHE tại TOF lớn nhất (V)']:.3f} V vs RHE")
    print(f"  (n = {n_e:g}, n tính N = {n_q:g}; diện tích CV: {'vòng kín |∮I dE|' if kieu_dt == 'kin' else 'tổng |I||dE|'})")
    print("====================================================================================================")
    try:
        tong.to_csv(os.path.join(thu_muc, "QsLSV_TOF_tong_hop.csv"), index=False, encoding="utf-8-sig")
    except PermissionError:
        print("  (canh bao) khong ghi duoc QsLSV_TOF_tong_hop.csv - hay dong file dang mo.")
    try:
        import bao_cao
        bao_cao.ghi("tof_cv", tong.to_dict("records"))
    except ImportError:
        pass
    if ve:
        ve_hinh(cac, os.path.join(thu_muc, "TOF_QsLSV"))
    return tong, cac


def ve_hinh(cac, goc):
    """2 đồ thị: (A) CV, (B) TOF theo E vs RHE (điểm Qs-LSV)."""
    import hinh_bai_bao
    import xu_ly_dien_hoa as xl
    plt = hinh_bai_bao._plt()
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.4))
    dam = {"fontsize": 12, "fontweight": "bold"}
    for ax, chu, nhan_y in ((axs[0], "(A)", "Current density (mA cm$^{-2}$)"), (axs[1], "(B)", "TOF (s$^{-1}$)")):
        for c in cac:
            m = c["m"]
            if chu == "(A)":
                ax.plot(c["cv"][xl.COT_E], c["cv"][xl.COT_I], lw=1.8, color=m["mau"], label=m["nhan"])
            else:
                ax.plot(c["qs"][C_E], c["qs"][C_TOF], "-o", lw=1.6, ms=4, color=m["mau"], label=m["nhan"])
        ax.set_xlabel("Potential (V vs RHE)", **dam)
        ax.set_ylabel(nhan_y, **dam)
        hinh_bai_bao._khung(ax, 10)
        for s in ax.spines.values():
            s.set_linewidth(1.5)
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            t.set_fontweight("bold")
        ax.text(0.02, 0.97, chu, transform=ax.transAxes, fontsize=12, va="top", ha="left")
        leg = ax.legend(loc="best", frameon=False, fontsize=10, handlelength=2.2, prop={"weight": "bold", "size": 10})
        for txt, c in zip(leg.get_texts(), cac):
            txt.set_color(c["m"]["mau"])
    fig.tight_layout(w_pad=2.5)
    ra = []
    for ext in ("png", "pdf"):
        try:
            fig.savefig(f"{goc}.{ext}", dpi=300)
            ra.append(f"{os.path.basename(goc)}.{ext}")
        except PermissionError:
            print(f"  (canh bao) khong ghi duoc {os.path.basename(goc)}.{ext} - hay dong file dang mo.")
        except Exception as e:                      # vd exe thieu backend_pdf -> van giu PNG
            print(f"  (canh bao) khong luu duoc {os.path.basename(goc)}.{ext}: {e}")
    plt.close(fig)
    # đường phân cực Qs-LSV (J theo E) riêng
    fig, ax = plt.subplots(figsize=(5.0, 4.4))
    for c in cac:
        ax.plot(c["qs"][C_E], c["qs"][C_J], "-o", lw=1.6, ms=4, color=c["m"]["mau"], label=c["m"]["nhan"])
    ax.set_xlabel("Potential (V vs RHE)", **dam)
    ax.set_ylabel("Current density (mA cm$^{-2}$)", **dam)
    hinh_bai_bao._khung(ax, 10)
    leg = ax.legend(loc="best", frameon=False, prop={"weight": "bold", "size": 10})
    for txt, c in zip(leg.get_texts(), cac):
        txt.set_color(c["m"]["mau"])
    fig.tight_layout()
    try:
        fig.savefig(os.path.join(os.path.dirname(goc), "QsLSV_J-E.png"), dpi=300)
        ra.append("QsLSV_J-E.png")
    except Exception as e:
        print(f"  (canh bao) khong luu duoc QsLSV_J-E.png: {e}")
    plt.close(fig)
    print("  hinh: " + ", ".join(ra))
