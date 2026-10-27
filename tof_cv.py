# -*- coding: utf-8 -*-
"""
TOF TỪ MỘT VÒNG CV  (cửa sổ điện thế, mặc định -1.5 → -1.1 V)

    TOF (s⁻¹) = |I| / (n · F · N)          I : dòng ĐO THÔ (A) trong file - không chia diện tích, không nhân/chia hệ số
    N (mol)   = Q / (n_Q · F)              số mol tâm hoạt động suy ra từ điện lượng của chính vòng CV
    Q (C)     = (diện tích CV, A·V) / (tốc độ quét, V/s)

  n   : số electron trao đổi của phản ứng (ô nhập, mặc định 2)
  n_Q : số electron trao đổi khi tính N (ô nhập, mặc định 2; để trống = bằng n; nếu n = n_Q thì TOF = I / Q)
  F   : 96485.33212 C/mol
  Diện tích CV: 'kin'  = |∮ I dE| (phần bao quanh đường CV, trapezoid, khép kín)
                'tong' = ∫|I| |dE| trên cả hai chiều quét
  Tốc độ quét : nhập tay (mV/s, có thể mỗi mẫu một số, cách nhau dấu ;) hoặc để trống để lấy từ dữ liệu.

Cửa sổ điện thế lọc theo điện thế GHI TRONG FILE (chưa quy đổi RHE); tick --tof-rhe để lọc theo điện thế đã quy đổi RHE.
Trục E vẽ luôn là điện thế đã quy đổi RHE. Chỉ dùng MỘT chu kỳ (chu kỳ cuối nếu không chọn).
"""
import os

import numpy as np
import pandas as pd

FARADAY = 96485.33212
COT_E_THO, COT_E_RHE, COT_I_THO, COT_TOF, COT_J = "E (V)", "E RHE (V)", "I_tho (A)", "TOF (s-1)", "J (mA/cm2)"


def dien_tich_cv(e, i, kieu="kin"):
    """Diện tích (A·V) của đường CV từ các điểm theo thứ tự đo."""
    e, i = np.asarray(e, float), np.asarray(i, float)
    if len(e) < 3:
        return 0.0
    de = np.diff(e)
    tb = (i[1:] + i[:-1]) / 2
    if kieu == "tong":
        return float(np.sum(np.abs(tb) * np.abs(de)))
    kin = float(np.sum(tb * de) + (i[0] + i[-1]) / 2 * (e[0] - e[-1]))      # đoạn khép kín từ điểm cuối về điểm đầu
    return abs(kin)


def _ds_so(gia_tri, so_mau, ten, bat_buoc=False):
    """'50' hoặc '50; 20; 10' -> danh sách cho từng mẫu; trống -> [None]*so_mau."""
    if gia_tri is None or str(gia_tri).strip() == "":
        if bat_buoc:
            raise ValueError(f"Chưa nhập {ten}.")
        return [None] * so_mau
    ds = [float(x.replace(",", ".")) for x in str(gia_tri).replace(",", ".").replace(";", " ").split() if x.strip()]
    if not ds or any(x <= 0 for x in ds):
        raise ValueError(f"{ten} phải là số dương.")
    if len(ds) == 1:
        ds = ds * so_mau
    if len(ds) != so_mau:
        raise ValueError(f"{ten}: nhập 1 số (dùng chung) hoặc đúng {so_mau} số theo thứ tự các mẫu CV/LSV, bạn nhập {len(ds)} số.")
    return ds


def tinh_mot(d, chu_ky, e_min, e_max, n_e, n_q, v_mv, dung_rhe=False, chon_chu_ky=None, kieu_dt="kin", chieu="ca_hai"):
    """Trả về (bảng điểm, thông số) hoặc (rỗng, None). d: bảng xu_ly_cv_lsv."""
    import xu_ly_dien_hoa as xl
    g = d[d["chu_ky"] == chon_chu_ky(d, chu_ky)] if (chon_chu_ky is not None and "chu_ky" in d) else d
    cot_loc = "RHE (V)" if dung_rhe else "E (V)"
    x = g[cot_loc].to_numpy(dtype=float)
    m = (x >= min(e_min, e_max)) & (x <= max(e_min, e_max))
    g = g[m]
    if len(g) < 3:
        return pd.DataFrame(), None
    e_tho = g["E (V)"].to_numpy(float)
    i_tho = g["i (A/cm2)"].to_numpy(float)            # cột thô: dòng đo (A), chưa quy đổi gì
    v_do = v_mv if v_mv else xl.toc_do_quet(d) * 1000
    if not np.isfinite(v_do) or v_do <= 0:
        raise ValueError("Không xác định được tốc độ quét - hãy nhập tay vào ô 'Tốc độ quét'.")
    dt = dien_tich_cv(e_tho, i_tho, kieu_dt)
    q = dt / (v_do / 1000.0)
    if q <= 0:
        return pd.DataFrame(), None
    n_mol = q / (n_q * FARADAY)
    tof = np.abs(i_tho) / (n_e * FARADAY * n_mol)
    huong = g["huong_quet"].to_numpy() if "huong_quet" in g else np.array([""] * len(g))
    b = pd.DataFrame({COT_E_THO: e_tho, COT_E_RHE: g["RHE (V)"].to_numpy(float), COT_I_THO: i_tho, COT_TOF: tof,
                      COT_J: g["I (mA/cm2)"].to_numpy(float), "huong_quet": huong})
    if chieu in ("catot", "anot"):
        ten = "cathodic" if chieu == "catot" else "anodic"
        b_ve = b[b["huong_quet"] == ten]
    else:
        b_ve = b
    tp = {"v_mV_s": v_do, "dien_tich_AV": dt, "Q_C": q, "N_mol": n_mol}
    return b, dict(tp, ve=b_ve)


def tinh_q(d, chu_ky, e_min, e_max, v_mv, dung_rhe=False, chon_chu_ky=None, kieu_dt="kin", dung_tho=False):
    """Điện lượng Q của MỘT vòng CV (cửa sổ điện thế tùy chọn; e_min/e_max = None -> cả chu kỳ).
    Mặc định dùng dòng ĐÃ QUY ĐỔI (mA/cm², hệ số nhân/chia của app) -> Q tính trên cm² điện cực (C/cm²);
    dung_tho=True dùng dòng thô (A) -> Q là cả điện cực (C).
    Trả về (dict {v_mV_s, dien_tich_AV, Q_C, so_diem}, bảng chu kỳ đầy đủ) hoặc raise ValueError."""
    import xu_ly_dien_hoa as xl
    g = d[d["chu_ky"] == chon_chu_ky(d, chu_ky)] if (chon_chu_ky is not None and "chu_ky" in d) else d
    toan = g
    if e_min is not None and e_max is not None:
        x = g["RHE (V)" if dung_rhe else "E (V)"].to_numpy(dtype=float)
        g = g[(x >= min(e_min, e_max)) & (x <= max(e_min, e_max))]
    canh_bao = None
    if len(g) < 3:
        if len(toan) < 3:
            raise ValueError("CV có ít hơn 3 điểm.")
        x = toan["RHE (V)" if dung_rhe else "E (V)"].to_numpy(dtype=float)
        canh_bao = (f"cửa sổ E {min(e_min, e_max):g} ~ {max(e_min, e_max):g} V không có điểm nào của CV (CV này đo từ {x.min():.3f} đến "
                    f"{x.max():.3f} V {'RHE' if dung_rhe else 'theo điện thế ghi trong file'}) -> dùng CẢ chu kỳ CV để tính Q. "
                    "Hãy sửa 'E từ / đến' (hoặc để trống cả hai ô) nếu muốn dùng một đoạn khác.")
        g = toan
    v_do = v_mv if v_mv else xl.toc_do_quet(d) * 1000
    if not np.isfinite(v_do) or v_do <= 0:
        raise ValueError("Không xác định được tốc độ quét - hãy nhập tay vào ô 'Tốc độ quét'.")
    i_cv = g["i (A/cm2)"].to_numpy(float) if dung_tho else g["I (mA/cm2)"].to_numpy(float) / 1000.0     # A hoặc A/cm2
    dt = dien_tich_cv(g["E (V)"].to_numpy(float), i_cv, kieu_dt)
    if dt <= 0:
        raise ValueError("diện tích CV bằng 0 (thử đổi kiểu diện tích hoặc cửa sổ điện thế).")
    return {"v_mV_s": v_do, "dien_tich_AV": dt, "Q_C": dt / (v_do / 1000.0), "so_diem": len(g), "canh_bao": canh_bao}, toan


def chay(muc, a, thu_muc, ve=True):
    """Tính cho mọi mẫu CV/LSV. Trả về (bảng tổng hợp, [(m, bảng điểm đã chọn chiều quét)]) hoặc None."""
    import xu_ly_dien_hoa as xl
    cv = [m for m in muc if m["loai"] in ("CV", "LSV")]
    if not cv:
        print("  (canh bao) TOF tu CV: khong co file CV/LSV.")
        return None
    n_e = float(getattr(a, "tof_n", 2.0) or 2.0)
    n_q = float(getattr(a, "tof_n_q", None) or n_e)
    if n_e <= 0 or n_q <= 0:
        raise ValueError("n (số electron) phải dương.")
    e1 = float(getattr(a, "tof_e_min", -1.5) if getattr(a, "tof_e_min", None) is not None else -1.5)
    e2 = float(getattr(a, "tof_e_max", -1.1) if getattr(a, "tof_e_max", None) is not None else -1.1)
    rhe = bool(getattr(a, "tof_rhe", False))
    kieu_dt = getattr(a, "tof_dien_tich", "kin") or "kin"
    chieu = getattr(a, "tof_chieu", "ca_hai") or "ca_hai"
    ds_v = _ds_so(getattr(a, "tof_v", None), len(cv), "Tốc độ quét (mV/s)")
    os.makedirs(thu_muc, exist_ok=True)
    hang, dd = [], []
    for m, v in zip(cv, ds_v):
        b, tp = tinh_mot(m["d"], getattr(a, "chu_ky", None), e1, e2, n_e, n_q, v, rhe, xl.chon_chu_ky, kieu_dt, chieu)
        if tp is None:
            print(f"  (canh bao) TOF tu CV: {m['nhan']} khong tinh duoc trong cua so {min(e1, e2):g} ~ {max(e1, e2):g} V "
                  f"({'RHE' if rhe else 'dien the ghi trong file'}): it hon 3 diem hoac dien tich CV bang 0.")
            continue
        bv = tp["ve"].reset_index(drop=True)
        if bv.empty:
            print(f"  (canh bao) TOF tu CV: {m['nhan']} khong co diem nao o chieu quet da chon.")
            continue
        k = int(bv[COT_TOF].idxmax())
        hang.append({"Nhãn": m["nhan"], "Tốc độ quét (mV/s)": tp["v_mV_s"], "Diện tích CV (A·V)": tp["dien_tich_AV"],
                     "Q (mC)": tp["Q_C"] * 1e3, "N (µmol)": tp["N_mol"] * 1e6, "n (TOF)": n_e, "n (tính N)": n_q,
                     "Cửa sổ E (V)": f"{min(e1, e2):g} ~ {max(e1, e2):g}", "Số điểm": len(bv),
                     "TOF lớn nhất (s-1)": float(bv.loc[k, COT_TOF]), "E RHE tại TOF lớn nhất (V)": float(bv.loc[k, COT_E_RHE])})
        dd.append((m, bv))
        goc = os.path.join(thu_muc, "TOF_" + "".join(c if c.isalnum() or c in "-_" else "_" for c in m["nhan"]))
        try:
            b.to_csv(goc + ".csv", index=False, encoding="utf-8-sig")
        except PermissionError:
            print(f"  (canh bao) khong ghi duoc {os.path.basename(goc)}.csv - hay dong file dang mo.")
    if not hang:
        return None
    tong = pd.DataFrame(hang)
    print("\n======== TOF TỪ CV  (TOF = |I| / (n·F·N), N = Q/(n·F), Q = diện tích CV / tốc độ quét) ========")
    for r in hang:
        print(f"  {r['Nhãn']}: v = {r['Tốc độ quét (mV/s)']:.4g} mV/s | Q = {r['Q (mC)']:.4g} mC | N = {r['N (µmol)']:.4g} µmol | "
              f"TOF max = {r['TOF lớn nhất (s-1)']:.4g} s⁻¹ tại {r['E RHE tại TOF lớn nhất (V)']:.3f} V vs RHE")
    print(f"  (n = {n_e:g}, n tính N = {n_q:g}; diện tích: {'vòng kín |∮I dE|' if kieu_dt == 'kin' else 'tổng |I||dE| hai chiều'})")
    print("===========================================================================================")
    try:
        tong.to_csv(os.path.join(thu_muc, "TOF_CV_tong_hop.csv"), index=False, encoding="utf-8-sig")
    except PermissionError:
        print("  (canh bao) khong ghi duoc TOF_CV_tong_hop.csv - hay dong file dang mo.")
    try:
        import bao_cao
        bao_cao.ghi("tof_cv", tong.to_dict("records"))
    except ImportError:
        pass
    if ve:
        ve_matplotlib(dd, os.path.join(thu_muc, "TOF_CV"), a)
    return tong, dd


def ve_matplotlib(dd, goc, a=None):
    """Hình 2 ô: (A) đường CV (J theo E vs RHE), (B) TOF theo E vs RHE. Kiểu bài báo: khung dày, chữ đậm, chú thích tô màu."""
    import hinh_bai_bao
    plt = hinh_bai_bao._plt()
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.4))
    nhan_dam = {"fontsize": 12, "fontweight": "bold"}
    for ax, cot, nhan_y, chu in ((axs[0], COT_J, "Current density (mA cm$^{-2}$)", "(A)"), (axs[1], COT_TOF, "TOF (s$^{-1}$)", "(B)")):
        for m, b in dd:
            ax.plot(b[COT_E_RHE], b[cot], lw=1.8, color=m["mau"], label=m["nhan"])
        ax.set_xlabel("Potential (V vs RHE)", **nhan_dam)
        ax.set_ylabel(nhan_y, **nhan_dam)
        hinh_bai_bao._khung(ax, 10)
        for s in ax.spines.values():
            s.set_linewidth(1.5)
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            t.set_fontweight("bold")
        ax.text(0.02, 0.97, chu, transform=ax.transAxes, fontsize=12, va="top", ha="left")
        leg = ax.legend(loc="best", frameon=False, fontsize=10, handlelength=2.2,
                        prop={"weight": "bold", "size": 10})
        for txt, (m, _) in zip(leg.get_texts(), dd):
            txt.set_color(m["mau"])
    fig.tight_layout(w_pad=2.5)
    import matplotlib.pyplot as plt2
    ra = []
    for ext in ("png", "pdf"):
        try:
            fig.savefig(f"{goc}.{ext}", dpi=300)
            ra.append(f"{os.path.basename(goc)}.{ext}")
        except PermissionError:
            print(f"  (canh bao) khong ghi duoc {os.path.basename(goc)}.{ext} - hay dong file dang mo.")
        except Exception as e:                      # vd exe thieu backend_pdf -> van giu PNG
            print(f"  (canh bao) khong luu duoc {os.path.basename(goc)}.{ext}: {e}")
    plt2.close(fig)
    if ra:
        print("  hinh TOF (2 do thi: CV va TOF-E): " + ", ".join(ra))
