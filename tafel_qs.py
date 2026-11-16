# -*- coding: utf-8 -*-
"""
TAFEL TỪ BỘ DỮ LIỆU Qs-LSV (thay cho cách vẽ Tafel cũ trên đường LSV/CV).

Qs-LSV cho các điểm (E vs RHE, J mA/cm²) ở trạng thái gần ổn định (điểm cuối mỗi bước điện thế), nên Tafel được fit trên chính các điểm này:
    E = a + b · log10|J|          b (mV/dec) = độ dốc × 1000

Chọn điểm để fit (lần lượt):
  1) vùng: theo DÒNG (|J| từ–đến, mA/cm²) hoặc theo ĐIỆN THẾ (E từ–đến, V vs RHE) hoặc tất cả điểm;
  2) bỏ riêng từng điểm (loại_bo = chỉ số điểm trong bảng Qs-LSV);
  3) số điểm N (>= 3) và cách lấy trong vùng:
       'tat_ca'   : mọi điểm trong vùng,
       'dau'      : N điểm có |J| nhỏ nhất của vùng,
       'cuoi'     : N điểm có |J| lớn nhất của vùng,
       'tot_nhat' : N điểm LIÊN TIẾP (theo |J|) có R² cao nhất (cùng R² thì chọn cửa sổ trải rộng hơn theo log|J|).
Không dùng thư viện ngoài ngoài numpy/pandas (matplotlib chỉ import khi vẽ).
"""
import json
import os
import re

import numpy as np

CHE_DO = ("dong", "dien_the", "tat_ca")
KIEU_CHON = ("tat_ca", "dau", "cuoi", "tot_nhat")
C_E, C_J = "E RHE (V)", "J (mA/cm2)"
NGUONG_R2 = 0.98


def _r2(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) == 0:
        return float("nan")
    p = np.polyfit(x, y, 1)
    ss_res = float(np.sum((y - np.polyval(p, x)) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0


def _so(v, mac_dinh=None):
    if v is None or str(v).strip() == "":
        return mac_dinh
    return float(str(v).strip().replace(",", "."))


def vung_theo_dong(e, j, lo, hi, loai_bo=None):
    """Mặt nạ các điểm có lo <= |J| <= hi (mA/cm²)."""
    a, b = sorted((float(lo), float(hi)))
    aj = np.abs(np.asarray(j, float))
    m = (aj >= a) & (aj <= b) & (aj > 0)
    return _bo_diem(m, loai_bo)


def vung_theo_e(e, j, lo, hi, loai_bo=None):
    """Mặt nạ các điểm có lo <= E <= hi (V vs RHE)."""
    a, b = sorted((float(lo), float(hi)))
    e = np.asarray(e, float)
    m = (e >= a) & (e <= b) & (np.abs(np.asarray(j, float)) > 0)
    return _bo_diem(m, loai_bo)


def _bo_diem(m, loai_bo):
    m = m.copy()
    for k in loai_bo or ():
        if 0 <= int(k) < len(m):
            m[int(k)] = False
    return m


def chon_diem(e, j, che_do="dong", lo=None, hi=None, so_diem=None, kieu="tat_ca", loai_bo=None):
    """→ mặt nạ bool (độ dài = số điểm Qs-LSV) của các điểm dùng để fit. ValueError nếu < 3 điểm."""
    e, j = np.asarray(e, float), np.asarray(j, float)
    if che_do == "dong":
        if lo is None or hi is None:
            raise ValueError("Vùng theo dòng: hãy nhập cả 'từ' và 'đến' (mA/cm²).")
        m = vung_theo_dong(e, j, lo, hi, loai_bo)
    elif che_do == "dien_the":
        if lo is None or hi is None:
            raise ValueError("Vùng theo điện thế: hãy nhập cả 'từ' và 'đến' (V vs RHE).")
        m = vung_theo_e(e, j, lo, hi, loai_bo)
    elif che_do == "tat_ca":
        m = _bo_diem(np.abs(j) > 0, loai_bo)
    else:
        raise ValueError(f"Chế độ vùng không hợp lệ: {che_do}")
    idx = np.where(m)[0]
    if len(idx) < 3:
        raise ValueError(f"Vùng đã chọn chỉ có {len(idx)} điểm Qs-LSV (cần ≥ 3). Hãy mở rộng vùng hoặc bỏ bớt điểm loại.")
    if kieu == "tat_ca" or not so_diem:
        return m
    n = int(so_diem)
    if n < 3:
        raise ValueError("Số điểm N phải ≥ 3.")
    thu_tu = idx[np.argsort(np.log10(np.abs(j[idx])), kind="stable")]
    if n >= len(thu_tu):
        return m
    if kieu == "dau":
        chon = thu_tu[:n]
    elif kieu == "cuoi":
        chon = thu_tu[-n:]
    elif kieu == "tot_nhat":
        lg = np.log10(np.abs(j[thu_tu]))
        tot, chon = None, None
        for s in range(0, len(thu_tu) - n + 1):
            w = thu_tu[s:s + n]
            r2 = _r2(lg[s:s + n], e[w])
            r2 = -1.0 if not np.isfinite(r2) else r2
            khoa = (round(r2, 9), float(np.ptp(lg[s:s + n])))
            if tot is None or khoa > tot:
                tot, chon = khoa, w
    else:
        raise ValueError(f"Cách chọn điểm không hợp lệ: {kieu}")
    kq = np.zeros(len(e), bool)
    kq[chon] = True
    return kq


def fit(e, j, mask):
    """Fit E = a + b·log10|J| trên các điểm của mask. → dict (b, a, r2, sai_so_b, n, log_j_min, log_j_max)."""
    e, j = np.asarray(e, float)[mask], np.asarray(j, float)[mask]
    lg = np.log10(np.abs(j))
    if len(lg) < 3 or np.ptp(lg) == 0:
        raise ValueError("Không đủ điểm hoặc các điểm có cùng dòng: không fit được.")
    b, a = np.polyfit(lg, e, 1)
    res = e - (a + b * lg)
    n = len(lg)
    sxx = float(np.sum((lg - lg.mean()) ** 2))
    se = float(np.sqrt(np.sum(res ** 2) / (n - 2) / sxx)) if n > 2 and sxx > 0 else float("nan")
    return dict(b_mV=float(b) * 1000.0, a_V=float(a), r2=_r2(lg, e), sai_so_mV=se * 1000.0, n=n,
                log_j_min=float(lg.min()), log_j_max=float(lg.max()),
                j_min=float(np.abs(j).min()), j_max=float(np.abs(j).max()), e_min=float(e.min()), e_max=float(e.max()))


def canh_bao(kq, ten=""):
    """Danh sách cảnh báo tiếng Việt cho một kết quả fit."""
    p = f"{ten}: " if ten else ""
    ds = []
    if kq["n"] < 5:
        ds.append(f"{p}chỉ có {kq['n']} điểm trong vùng Tafel, kết quả kém tin cậy.")
    if np.isfinite(kq["r2"]) and kq["r2"] < NGUONG_R2:
        ds.append(f"{p}R² của đường Tafel = {kq['r2']:.3f} (< {NGUONG_R2}); vùng đã chọn có thể không tuyến tính.")
    if abs(kq["b_mV"]) > 500:
        ds.append(f"{p}hệ số Tafel {kq['b_mV']:.0f} mV/dec rất lớn, thường do vùng chọn chưa đúng hoặc dòng bị hạn chế bởi chuyển khối/iR.")
    elif abs(kq["b_mV"]) < 20:
        ds.append(f"{p}hệ số Tafel {kq['b_mV']:.0f} mV/dec rất nhỏ, nên kiểm tra lại dữ liệu.")
    if kq.get("decades", 1.0) < 0.5:
        ds.append(f"{p}vùng fit chỉ trải {kq['decades']:.2f} decade dòng; nên ≥ 1 decade để độ dốc đáng tin.")
    return ds


def cau_hinh_mac_dinh():
    return dict(che_do="dong", lo=1.0, hi=10.0, so_diem=None, kieu="tat_ca", loai_bo=[])


def phan_tich(e, j, cfg):
    """e, j: mảng điểm Qs-LSV của một mẫu; cfg: che_do, lo, hi, so_diem, kieu, loai_bo. → dict kết quả (kèm 'mask')."""
    c = dict(cau_hinh_mac_dinh(), **(cfg or {}))
    mask = chon_diem(e, j, c["che_do"], _so(c["lo"]), _so(c["hi"]), c["so_diem"], c["kieu"], c["loai_bo"])
    kq = fit(e, j, mask)
    kq["decades"] = kq["log_j_max"] - kq["log_j_min"]
    kq["mask"] = mask
    kq["cfg"] = c
    kq["vung"] = mo_ta_vung(c, kq)
    kq["canh_bao"] = canh_bao(kq)
    return kq


def mo_ta_vung(c, kq=None):
    if c["che_do"] == "dong":
        s = f"|J| {_so(c['lo']):g} – {_so(c['hi']):g} mA/cm²"
    elif c["che_do"] == "dien_the":
        s = f"E {_so(c['lo']):g} – {_so(c['hi']):g} V vs RHE"
    else:
        s = "tất cả điểm Qs-LSV"
    ten = {"dau": "N điểm đầu vùng (|J| nhỏ)", "cuoi": "N điểm cuối vùng (|J| lớn)", "tot_nhat": "N điểm liên tiếp có R² cao nhất"}.get(c.get("kieu"))
    if ten and c.get("so_diem"):
        s += f"; {ten.replace('N', str(int(c['so_diem'])), 1)}"
    if c.get("loai_bo"):
        s += f"; bỏ {len(c['loai_bo'])} điểm"
    return s


def ban_ghi(nhan, kq):
    """Bản ghi chuẩn cho bảng tổng hợp/báo cáo/nộp bài (khóa giống bao_cao.LUU['tafel'])."""
    return {"nhan": nhan, "he_so_Tafel (mV/dec)": kq["b_mV"], "so_diem": kq["n"], "vung_dong (mA/cm2)": kq["vung"],
            "R2": kq["r2"], "sai_so (mV/dec)": kq["sai_so_mV"], "a (V vs RHE)": kq["a_V"],
            "j_min (mA/cm2)": kq["j_min"], "j_max (mA/cm2)": kq["j_max"]}


# ---------------------------------------------------------------- lưu / nạp kết quả (để so sánh, nộp bài, báo cáo dùng lại)
NHO = {}


def luu_json(duong_dan, ds_ban_ghi):
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    with open(duong_dan, "w", encoding="utf-8") as f:
        json.dump(list(ds_ban_ghi), f, ensure_ascii=False, indent=1)


def nap_json(duong_dan):
    """Nạp kết quả Tafel (Qs-LSV) đã lưu vào NHO {nhãn: bản ghi}. Không có file/lỗi → NHO rỗng."""
    NHO.clear()
    try:
        with open(duong_dan, encoding="utf-8") as f:
            for b in json.load(f):
                NHO[str(b["nhan"])] = b
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return NHO


def cua(nhan):
    """Bản ghi Tafel Qs-LSV của mẫu (so khớp nhãn không phân biệt hoa thường/ký tự lạ); None nếu chưa có."""
    def chuan(x):
        return re.sub(r"[^0-9a-z]+", "_", str(x).lower()).strip("_")
    k = chuan(nhan)
    for n, b in NHO.items():
        if chuan(n) == k:
            return b
    return None


def luu_diem_json(duong_dan, cac, kieu_y="e", e0=0.0):
    """Ghi điểm + đường fit của các mẫu để công cụ vẽ Origin đọc: {kieu_y, e0, mau: [{nhan, mau, e, j, dung, b_mV, a_V, log_j_min, log_j_max}]}."""
    out = {"kieu_y": kieu_y, "e0": float(e0), "mau": []}
    for c in cac:
        kq = c.get("kq")
        if kq is None:
            continue
        out["mau"].append({"nhan": c["nhan"], "mau": c["mau"], "e": [float(x) for x in c["e"]], "j": [float(x) for x in c["j"]],
                           "dung": [bool(x) for x in kq["mask"]], "b_mV": kq["b_mV"], "a_V": kq["a_V"],
                           "log_j_min": kq["log_j_min"], "log_j_max": kq["log_j_max"]})
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    with open(duong_dan, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)


# ---------------------------------------------------------------- vẽ
def y_hien_thi(e, kieu_y="e", e0=0.0):
    """kieu_y 'e': E (V vs RHE); 'eta': quá thế η (mV) = (E − E0)·1000."""
    e = np.asarray(e, float)
    return (e - float(e0)) * 1000.0 if kieu_y == "eta" else e


def ve_len_truc(ax, cac, kieu_y="e", e0=0.0, co_chu=11, hien_diem_loai=True, hien_chu_thich=True):
    """cac: [{nhan, mau, e, j, kq (hoặc None)}]. Điểm đã dùng = ô đặc, điểm không dùng = ô rỗng mờ, đường fit kéo dài nhẹ hai đầu."""
    for c in cac:
        e, j = np.asarray(c["e"], float), np.asarray(c["j"], float)
        ok = np.abs(j) > 0
        lg = np.log10(np.where(ok, np.abs(j), np.nan))
        kq = c.get("kq")
        dung = kq["mask"] if kq is not None else np.zeros(len(e), bool)
        mau = c["mau"]
        if hien_diem_loai:
            kh = ok & ~dung
            ax.plot(lg[kh], y_hien_thi(e[kh], kieu_y, e0), "o", ms=5, mfc="none", mec=mau, alpha=0.45, lw=0)
        ax.plot(lg[dung], y_hien_thi(e[dung], kieu_y, e0), "o", ms=6, color=mau, lw=0, label=None)
        if kq is not None:
            x0, x1 = kq["log_j_min"], kq["log_j_max"]
            d = max(0.08 * (x1 - x0), 0.02)
            xs = np.array([x0 - d, x1 + d])
            ys = kq["a_V"] + kq["b_mV"] / 1000.0 * xs
            ten = f"{c['nhan']}: {abs(kq['b_mV']):.1f} mV dec$^{{-1}}$"
            ax.plot(xs, y_hien_thi(ys, kieu_y, e0), "-", lw=2.0, color=mau, label=ten)
    ax.set_xlabel("log |J| (mA cm$^{-2}$)", fontsize=co_chu, fontweight="bold")
    ax.set_ylabel("Potential (V vs RHE)" if kieu_y == "e" else "Overpotential (mV)", fontsize=co_chu, fontweight="bold")
    ax.tick_params(labelsize=co_chu - 1, width=1.4)
    for s in ax.spines.values():
        s.set_linewidth(1.5)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontweight("bold")
    if hien_chu_thich:
        h, l = ax.get_legend_handles_labels()
        if h:
            leg = ax.legend(h, l, frameon=False, fontsize=co_chu - 1, prop={"weight": "bold", "size": co_chu - 1})
            for t, c in zip(leg.get_texts(), [c for c in cac if c.get("kq") is not None]):
                t.set_color(c["mau"])


def xuat(cac, thu_muc, ten="Tafel_QsLSV", kieu_y="e", e0=0.0, dang=("png", "pdf"), dpi=300):
    """Ghi hình + CSV (tổng hợp, điểm từng mẫu) + JSON. cac như ve_len_truc. → danh sách tên file đã ghi."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    import pandas as pd
    os.makedirs(thu_muc, exist_ok=True)
    ra = []
    fig = Figure(figsize=(5.2, 4.6))
    ax = fig.add_subplot(111)
    ve_len_truc(ax, cac, kieu_y, e0)
    fig.tight_layout()
    for ext in dang:
        try:
            fig.savefig(os.path.join(thu_muc, f"{ten}.{ext}"), dpi=dpi)
            ra.append(f"{ten}.{ext}")
        except Exception as ex:  # noqa: BLE001  (PermissionError, thiếu backend pdf...)
            print(f"  (canh bao) khong luu duoc {ten}.{ext}: {ex}")
    bang = []
    for c in cac:
        kq = c.get("kq")
        if kq is None:
            continue
        b = ban_ghi(c["nhan"], kq)
        bang.append({"Nhãn": c["nhan"], "Hệ số Tafel (mV/dec)": b["he_so_Tafel (mV/dec)"], "Sai số (mV/dec)": b["sai_so (mV/dec)"], "R²": b["R2"],
                     "Số điểm": b["so_diem"], "Vùng chọn": b["vung_dong (mA/cm2)"], "a (V vs RHE)": b["a (V vs RHE)"],
                     "|J| nhỏ nhất (mA/cm²)": b["j_min (mA/cm2)"], "|J| lớn nhất (mA/cm²)": b["j_max (mA/cm2)"]})
        ten_f = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(c["nhan"]))
        e, j = np.asarray(c["e"], float), np.asarray(c["j"], float)
        pd.DataFrame({"E RHE (V)": e, "J (mA/cm2)": j, "log|J|": np.log10(np.where(j != 0, np.abs(j), np.nan)),
                      "Dùng để fit": kq["mask"].astype(int)}).to_csv(os.path.join(thu_muc, f"{ten}_{ten_f}_diem.csv"), index=False, encoding="utf-8-sig")
        ra.append(f"{ten}_{ten_f}_diem.csv")
    if bang:
        pd.DataFrame(bang).to_csv(os.path.join(thu_muc, f"{ten}_tong_hop.csv"), index=False, encoding="utf-8-sig")
        ra.append(f"{ten}_tong_hop.csv")
        luu_json(os.path.join(thu_muc, "Tafel_QsLSV.json"), [ban_ghi(c["nhan"], c["kq"]) for c in cac if c.get("kq") is not None])
        ra.append("Tafel_QsLSV.json")
    return ra
