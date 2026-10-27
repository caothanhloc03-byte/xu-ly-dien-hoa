# -*- coding: utf-8 -*-
"""
SO SÁNH CÁC MẪU + HOẠT ĐỘ KHỐI (mass activity) + TOF.

Với mỗi mẫu CV/LSV tính:
  • E và quá thế (η = E - E_cân_bằng) tại các mật độ dòng mục tiêu (mặc định 10 mA/cm²), lấy giao điểm SAU CÙNG
  • hệ số Tafel (mV/dec) trong vùng dòng đã chọn
  • tại các quá thế khảo sát η_ht (mặc định 300 mV): mật độ dòng J, hoạt độ khối (A/g) và TOF (s⁻¹)
Rồi xếp hạng theo η (thấp = tốt) và vẽ biểu đồ cột so sánh.

CÔNG THỨC
  mass activity (A/g) = J (mA/cm²) / tải_trọng (mg/cm²)
  TOF (s⁻¹)           = J (A/cm²) / (n_e × F × số_mol_tâm_hoạt_động (mol/cm²))
  số mol tâm: nhập trực tiếp (µmol/cm²) HOẶC tính = tải_trọng/M × tỉ_lệ_tâm_hoạt_động
              (cách thứ hai cho TOF "theo tổng nguyên tử kim loại" = cận dưới của TOF thật)
"""
import os

import numpy as np
import pandas as pd

import xu_ly_dien_hoa as xl

FARADAY = 96485.33212
TEN_PNG = "so_sanh_tong_hop.png"
TEN_CSV = "so_sanh_tong_hop.csv"


def _ds_so(chuoi, mac_dinh):
    kq = []
    for x in str(chuoi if chuoi is not None else "").replace(";", ",").split(","):
        x = x.strip().replace(",", ".")
        if x:
            try:
                kq.append(float(x))
            except ValueError:
                pass
    return kq or list(mac_dinh)


def _so_hoac_none(v):
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def nhanh_phan_ung(m, a, chieu=None):
    """Dữ liệu (E, I) dùng để so sánh: LSV = toàn bộ; CV = chu kỳ được chọn, nhánh anodic/cathodic.
    chieu: +1 anodic, -1 cathodic, None = tự chọn theo dấu dòng lớn hơn."""
    d = m["d"]
    if m["loai"] == "CV":
        d = d[d["chu_ky"] == xl.chon_chu_ky(d, getattr(a, "chu_ky", None))]
    i = d[xl.COT_I].to_numpy()
    if chieu is None:
        chieu = 1 if i.max() >= -i.min() else -1
    if m["loai"] == "CV":
        d = d[d["huong_quet"] == ("anodic" if chieu > 0 else "cathodic")]
    return d, chieu


def e_tai_j(d, j_muc_tieu):
    """E (V vs RHE) tại J cho trước - giao điểm SAU CÙNG (tránh pic nhỏ ở điện thế thấp). None nếu không đạt."""
    e, i = d[xl.COT_E].to_numpy(), d[xl.COT_I].to_numpy()
    if len(e) < 2:
        return None
    s = np.sign(i - j_muc_tieu)
    cat = np.where((s[:-1] * s[1:] <= 0) & (s[:-1] != s[1:]))[0]
    if len(cat) == 0:
        return None
    k = cat[-1]
    if i[k + 1] == i[k]:
        return float(e[k])
    return float(e[k] + (j_muc_tieu - i[k]) * (e[k + 1] - e[k]) / (i[k + 1] - i[k]))


def j_tai_e(d, e0):
    """J (mA/cm²) tại E (V vs RHE) bằng nội suy; None nếu E ngoài khoảng dữ liệu."""
    s = d.sort_values(xl.COT_E)
    e = s[xl.COT_E].to_numpy()
    if len(e) < 2 or not (e[0] <= e0 <= e[-1]):
        return None
    return float(np.interp(e0, e, s[xl.COT_I].to_numpy()))


def so_mol_tam_cm2(tai_trong, so_mol_umol, khoi_luong_mol, ti_le_tam):
    """mol tâm hoạt động trên cm² điện cực, hoặc (None, lý do)."""
    if so_mol_umol is not None and so_mol_umol > 0:
        return so_mol_umol * 1e-6, "nhập trực tiếp"
    if tai_trong and khoi_luong_mol and khoi_luong_mol > 0:
        return tai_trong * 1e-3 / khoi_luong_mol * (ti_le_tam if ti_le_tam else 1.0), "tính từ tải trọng và M"
    return None, ""


def tinh_mot_mau(m, a, ds_j, ds_eta):
    """Trả về dict kết quả cho một mẫu CV/LSV."""
    e_cb = None if (getattr(a, "khong_qua_the", False) or getattr(a, "khong_rhe", False)) else float(getattr(a, "e_can_bang", 1.23))
    tai_trong = _so_hoac_none(getattr(a, "tai_trong", None))
    n_e = _so_hoac_none(getattr(a, "n_e", None)) or 4.0
    tam, _ = so_mol_tam_cm2(tai_trong, _so_hoac_none(getattr(a, "so_mol_tam", None)),
                            _so_hoac_none(getattr(a, "khoi_luong_mol", None)),
                            _so_hoac_none(getattr(a, "ti_le_tam", None)) or 1.0)
    d, chieu = nhanh_phan_ung(m, a)
    h = {"Nhãn": m["nhan"], "_mau": m["mau"], "Nhóm": m.get("nhom", ""), "Loại": m["loai"], "Chiều": "anodic (OER)" if chieu > 0 else "cathodic (HER)"}
    for j in ds_j:
        e = e_tai_j(d, chieu * j)
        h[f"E tại {j:g} mA/cm² (V)"] = e
        if e_cb is not None:
            h[f"η tại {j:g} mA/cm² (mV)"] = None if e is None else (e - e_cb) * 1000.0
    try:
        _, slope, _, _ = xl.tafel_a(d, a)
        h["Tafel (mV/dec)"] = abs(slope)
    except Exception as e:
        h["Tafel (mV/dec)"] = None
        print(f"  (luu y) khong tinh duoc Tafel cho {m['nhan']}: {e}")
    for eta in (ds_eta if e_cb is not None else []):
        e0 = e_cb + chieu * abs(eta) / 1000.0
        j = j_tai_e(d, e0)
        h[f"J tại η={eta:g} mV (mA/cm²)"] = j
        if tai_trong and tai_trong > 0:
            h[f"Hoạt độ khối tại η={eta:g} mV (A/g)"] = None if j is None else abs(j) / tai_trong
        if tam:
            h[f"TOF tại η={eta:g} mV (s⁻¹)"] = None if j is None else abs(j) * 1e-3 / (n_e * FARADAY * tam)
    return h


def tong_hop(muc, a):
    """DataFrame so sánh các mẫu CV/LSV (đã xếp hạng) + dict mô tả tham số."""
    ds_j = _ds_so(getattr(a, "i_muc_tieu", "10"), [10.0])
    ds_eta = _ds_so(getattr(a, "qua_the_ht", "300"), [300.0])
    hang = []
    for m in muc:
        if m["loai"] in ("CV", "LSV", "TAFEL"):
            try:
                hang.append(tinh_mot_mau(m, a, ds_j, ds_eta))
            except Exception as e:
                hang.append({"Nhãn": m["nhan"], "_mau": m["mau"], "Lỗi": str(e)})
    if not hang:
        return None, {}
    df = pd.DataFrame(hang)
    cot_hang = f"η tại {ds_j[0]:g} mA/cm² (mV)"
    if cot_hang not in df:                       # khong co qua the (vd oxi hoa glucose): xep hang theo dien the
        cot_hang = f"E tại {ds_j[0]:g} mA/cm² (V)"
    if cot_hang in df and df[cot_hang].notna().sum() >= 2:
        df.insert(1, "Hạng", df[cot_hang].rank(method="min", ascending=True, na_option="bottom").astype("Int64"))
        df.loc[df[cot_hang].isna(), "Hạng"] = pd.NA
    info = {"ds_j": ds_j, "ds_eta": ds_eta, "cot_hang": cot_hang}
    return df, info


def gop_nhom(df):
    """Gộp các mẫu cùng 'Nhóm' (lặp lại) thành trung bình ± SD. Mẫu không có nhóm giữ nguyên (n=1).
    Trả về DataFrame (hoặc None nếu không có nhóm nào có từ 2 mẫu trở lên)."""
    if "Nhóm" not in df or not (df["Nhóm"].fillna("").astype(str).str.strip() != "").any():
        return None
    ten = df["Nhóm"].fillna("").astype(str).str.strip()
    khoa = [t if t else str(n) for t, n in zip(ten, df["Nhãn"])]
    df = df.assign(_khoa=khoa)
    cot_so = [c for c in df.columns if c not in ("Nhãn", "_mau", "Nhóm", "Loại", "Chiều", "Hạng", "_khoa", "Lỗi")
              and pd.api.types.is_numeric_dtype(df[c])]
    hang = []
    for k, g in df.groupby("_khoa", sort=False):
        r = {"Nhãn": k, "_mau": g["_mau"].iloc[0], "n": len(g)}
        for c in cot_so:
            v = pd.to_numeric(g[c], errors="coerce").dropna().to_numpy(dtype=float)
            r[c] = float(v.mean()) if len(v) else None
            r[c + " ± SD"] = float(v.std(ddof=1)) if len(v) > 1 else None
        hang.append(r)
    if not any(r["n"] > 1 for r in hang):
        return None
    out = pd.DataFrame(hang)
    cot_hang = next((c for c in out.columns if c.startswith("η tại") and not c.endswith("SD")), None) or \
        next((c for c in out.columns if c.startswith("E tại") and not c.endswith("SD")), None)
    if cot_hang and out[cot_hang].notna().sum() >= 2:
        out.insert(1, "Hạng", out[cot_hang].rank(method="min", ascending=True, na_option="bottom").astype("Int64"))
    return out


def them_tai_lieu(df, info, duong_csv):
    """Ghép kết quả của mình với bảng tài liệu (CSV có cột tự do). Trả về list[dict]."""
    import csv
    with open(duong_csv, "r", encoding="utf-8-sig", newline="") as f:
        doc = list(csv.DictReader(f))
    j = info["ds_j"][0]
    ten_e = f"E tại {j:g} mA/cm² (V)"
    ten_eta = f"η tại {j:g} mA/cm² (mV)"
    kq = []
    for _, r in df.iterrows():
        h = {"Xúc tác": r["Nhãn"], "Tài liệu": "Nghiên cứu này"}
        h[f"E tại {j:g} mA/cm² (V vs RHE)"] = r.get(ten_e)
        if ten_eta in df:
            h[f"η tại {j:g} mA/cm² (mV)"] = r.get(ten_eta)
        h["Tafel (mV/dec)"] = r.get("Tafel (mV/dec)")
        kq.append(h)
    for r in doc:
        kq.append({("Xúc tác" if k.lower().startswith(("xuc tac", "xúc tác", "catalyst")) else k): v for k, v in r.items()})
    return kq


MAU_TAI_LIEU = ("Xúc tác,Điện giải,E tại 10 mA/cm² (V vs RHE),Tafel (mV/dec),Tài liệu\n"
                "Ví dụ: Ni(OH)2/NF,1 M KOH + 0.1 M glucose,1.37,60,Tác giả et al., Tạp chí, năm\n")


def _fmt(v, nd=1):
    return "-" if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA else f"{v:.{nd}f}"


def in_bang(df, info):
    ds_j = info["ds_j"]
    print("\n======== SO SÁNH CÁC MẪU ========")
    for _, r in df.iterrows():
        if "Lỗi" in r and isinstance(r.get("Lỗi"), str):
            print(f"  {r['Nhãn']}: lỗi {r['Lỗi']}")
            continue
        hang = r.get("Hạng")
        dau = f"#{int(hang)} " if hang is not None and not pd.isna(hang) else "   "
        phan = [f"{dau}{r['Nhãn']}"]
        for j in ds_j:
            if f"η tại {j:g} mA/cm² (mV)" in df:
                phan.append(f"η{j:g}={_fmt(r.get(f'η tại {j:g} mA/cm² (mV)'), 0)} mV")
            else:
                phan.append(f"E@{j:g}={_fmt(r.get(f'E tại {j:g} mA/cm² (V)'), 4)} V")
        phan.append(f"Tafel={_fmt(r.get('Tafel (mV/dec)'), 1)} mV/dec")
        for c in df.columns:
            if c.startswith("Hoạt độ khối"):
                phan.append(f"MA={_fmt(r.get(c), 1)} A/g")
            elif c.startswith("TOF"):
                phan.append(f"TOF={r.get(c):.3g} s⁻¹" if r.get(c) is not None and not pd.isna(r.get(c)) else "TOF=-")
        print("  " + " | ".join(phan))
    print("  (giá trị thấp hơn = hoạt tính tốt hơn; hạng 1 = tốt nhất)")
    print("=================================")


def ve_bieu_do(df, info, duong_png, co_sai_so=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ds_j = info["ds_j"]
    if f"η tại {ds_j[0]:g} mA/cm² (mV)" in df:
        tieu_chi = [(f"η tại {ds_j[0]:g} mA/cm² (mV)", f"η @ {ds_j[0]:g} mA/cm² (mV)", True)]
    else:
        tieu_chi = [(f"E tại {ds_j[0]:g} mA/cm² (V)", f"E @ {ds_j[0]:g} mA/cm² (V)", True)]
    tieu_chi.append(("Tafel (mV/dec)", "Tafel (mV/dec)", True))
    for c in df.columns:
        if c.startswith("Hoạt độ khối"):
            tieu_chi.append((c, c.replace("Hoạt độ khối tại ", "Hoạt độ khối @ "), False))
            break
    for c in df.columns:
        if c.startswith("TOF"):
            tieu_chi.append((c, c.replace("tại ", "@ "), False))
            break
    tieu_chi = [t for t in tieu_chi if t[0] in df and df[t[0]].notna().any()]
    if not tieu_chi:
        return None
    n = len(tieu_chi)
    fig, axs = plt.subplots(1, n, figsize=(3.4 * n + 0.6, 4.2), squeeze=False)
    nhan = [str(x) for x in df["Nhãn"]]
    mau = list(df["_mau"])
    for ax, (cot, tieu_de, thap_la_tot) in zip(axs[0], tieu_chi):
        v = pd.to_numeric(df[cot], errors="coerce").to_numpy(dtype=float)
        vv = np.where(np.isnan(v), 0, v)
        sd = None
        if co_sai_so and cot + " ± SD" in df:
            sd = pd.to_numeric(df[cot + " ± SD"], errors="coerce").fillna(0).to_numpy(dtype=float)
        ax.bar(range(len(vv)), vv, color=mau, edgecolor="black", linewidth=1.0, width=0.65,
               yerr=sd if sd is not None and sd.any() else None, capsize=4, error_kw={"elinewidth": 1.3, "capthick": 1.3})
        for k, x in enumerate(v):
            ax.text(k, vv[k], "n/a" if np.isnan(x) else (f"{x:.3g}" if abs(x) < 1000 else f"{x:.0f}"),
                    ha="center", va="bottom", fontsize=9)
        ax.set_xticks(range(len(vv)))
        ax.set_xticklabels(nhan, rotation=30 if max(len(s) for s in nhan) > 6 else 0, ha="right" if max(len(s) for s in nhan) > 6 else "center", fontsize=9)
        ax.set_ylabel(tieu_de.replace("s⁻¹", "s$^{-1}$"), fontsize=10)
        ax.set_ylim(0, ((np.nanmax(vv + (sd if sd is not None else 0))) if np.nanmax(vv) > 0 else 1) * 1.18)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_linewidth(1.3)
        ax.set_title("thấp = tốt" if thap_la_tot else "cao = tốt", fontsize=9, color="#666")
    fig.tight_layout()
    fig.savefig(duong_png, dpi=200)
    plt.close(fig)
    return duong_png


def xuat_so_sanh(muc, a, thu_muc):
    """Gọi từ xu_ly_dien_hoa.ket_thuc. Trả về DataFrame (hoặc None)."""
    df, info = tong_hop(muc, a)
    if df is None:
        return None
    in_bang(df, info)
    os.makedirs(thu_muc, exist_ok=True)
    cong = df.drop(columns=["_mau"], errors="ignore")
    nhom = gop_nhom(df)
    if nhom is not None:
        print("\n--- Trung bình ± SD theo nhóm lặp lại ---")
        for _, r in nhom.iterrows():
            phan = [f"{r['Nhãn']} (n={int(r['n'])})"]
            for c in nhom.columns:
                if c.startswith(("η tại", "E tại", "Tafel")) and not c.endswith("SD"):
                    sd = r.get(c + " ± SD")
                    phan.append(f"{c.split(' (')[0]} = {_fmt(r[c], 2)}" + (f" ± {_fmt(sd, 2)}" if sd is not None and not pd.isna(sd) else ""))
            print("  " + " | ".join(phan))
        try:
            nhom.drop(columns=["_mau"]).to_csv(os.path.join(thu_muc, "so_sanh_nhom.csv"), index=False, encoding="utf-8-sig")
        except PermissionError:
            pass
    try:
        cong.to_csv(os.path.join(thu_muc, TEN_CSV), index=False, encoding="utf-8-sig")
        if nhom is not None:
            png = ve_bieu_do(nhom, info, os.path.join(thu_muc, TEN_PNG), co_sai_so=True)
        else:
            png = ve_bieu_do(df, info, os.path.join(thu_muc, TEN_PNG)) if len(df) >= 1 else None
        print(f"  so sanh: {os.path.join(thu_muc, TEN_CSV)}" + (f" , {png}" if png else ""))
    except PermissionError:
        print("  (canh bao) khong ghi duoc file so sanh - hay dong file dang mo roi chay lai.")
    tl = getattr(a, "tai_lieu", None)
    if tl:
        try:
            import bao_cao
            kq_tl = them_tai_lieu(df, info, tl)
            bao_cao.ghi("so_sanh_tai_lieu", kq_tl)
            pd.DataFrame(kq_tl).to_csv(os.path.join(thu_muc, "so_sanh_tai_lieu.csv"), index=False, encoding="utf-8-sig")
            print(f"  so sanh voi tai lieu: {len(kq_tl)} dong")
        except Exception as e:
            print(f"  (canh bao) khong doc duoc bang tai lieu '{tl}': {e}")
    if nhom is not None:
        try:
            import bao_cao
            bao_cao.ghi("so_sanh_nhom", [{k: (None if (v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v))) else
                                            (int(v) if k in ("Hạng", "n") else v)) for k, v in r.items() if k != "_mau"}
                                         for r in nhom.to_dict("records")])
        except ImportError:
            pass
    try:
        import bao_cao
        bao_cao.ghi("so_sanh", [{k: (None if (v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v))) else
                                      (int(v) if k == "Hạng" else v)) for k, v in r.items()}
                                for r in cong.to_dict("records")])
    except ImportError:
        pass
    return df
