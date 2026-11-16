# -*- coding: utf-8 -*-
"""
CDL NHIỀU MẪU (từ các thư mục ECSA)

Mỗi mẫu = 1 thư mục chứa các file CV đo ở nhiều tốc độ quét (vùng điện dung, không có phản ứng Faraday).
Với từng file: lấy chu kỳ được chọn (mặc định chu kỳ cuối), nội suy dòng nhánh anodic Ja và cathodic Jc tại điện thế E lấy dòng
(mặc định: giữa vùng điện thế chung của các file của mẫu), ΔJ = (Ja − Jc)/2.
Fit tuyến tính ΔJ theo tốc độ quét v (V/s): độ dốc = Cdl (mF/cm²)  (mA/cm² chia V/s = mF/cm²).

Kết quả: một hình chung (ΔJ theo tốc độ quét, mỗi mẫu một màu/ký hiệu, đường fit nét đứt, ghi Cdl), bảng Cdl tổng hợp,
bảng điểm từng mẫu và JSON để vẽ Origin. KHÔNG tính/vẽ ECSA ở mục này.
"""
import json
import logging
import math
import os
import re

import numpy as np
import pandas as pd

DUOI = (".txt", ".csv", ".dat")
KY_HIEU = ["s", "o", "^", "v", "D", "<", ">", "p", "h", "*"]
TEN_JSON = "Cdl_nhieu.json"


def liet_ke_file(thu_muc):
    """File dữ liệu CV trong một thư mục (không đệ quy), theo thứ tự tên."""
    if os.path.isfile(thu_muc):
        return [thu_muc]
    ds = [os.path.join(thu_muc, f) for f in sorted(os.listdir(thu_muc), key=str.lower)
          if f.lower().endswith(DUOI) and os.path.isfile(os.path.join(thu_muc, f))]
    return ds


def _lam_tron_v(v):
    """Tốc độ quét đo từ file hay lệch nhẹ (0.00499): làm tròn 3 chữ số có nghĩa."""
    if not (v and math.isfinite(v)):
        return v
    return float(f"{v:.3g}")


def tinh_mau(thu_muc, nhan, mau, a, e_chon=None, chu_ky=None):
    """Trả về dict kết quả của một mẫu hoặc ném ValueError (thiếu file CV / dưới 2 tốc độ quét)."""
    import xu_ly_dien_hoa as xl
    cac = []
    for p in liet_ke_file(thu_muc):
        try:
            tho, _ = xl.doc_file_tho(p)
            d, loai = xl.xu_ly_cv_lsv(tho, a)
        except Exception as e:                                           # file không đọc được: bỏ qua, báo
            print(f"  [{nhan}] bo qua {os.path.basename(p)}: {e}")
            continue
        if loai != "CV":
            print(f"  [{nhan}] bo qua {os.path.basename(p)} (khong phai CV)")
            continue
        v = _lam_tron_v(xl.toc_do_quet(d))
        if not (v and math.isfinite(v) and v > 0):
            print(f"  [{nhan}] bo qua {os.path.basename(p)} (khong xac dinh duoc toc do quet)")
            continue
        g = d[d["chu_ky"] == xl.chon_chu_ky(d, chu_ky)]
        cac.append((p, g, v))
    if len(cac) < 2:
        raise ValueError(f"Mẫu '{nhan}': cần ít nhất 2 file CV ở 2 tốc độ quét khác nhau trong thư mục (tìm thấy {len(cac)}).")
    lo = max(g[xl.COT_E].min() for _, g, _ in cac)
    hi = min(g[xl.COT_E].max() for _, g, _ in cac)
    if e_chon is None:
        if hi <= lo:
            raise ValueError(f"Mẫu '{nhan}': các file CV không có vùng điện thế chung để lấy dòng.")
        e_chon = (lo + hi) / 2
    elif not (lo <= e_chon <= hi):
        print(f"  [{nhan}] (luu y) E = {e_chon:g} V nam ngoai vung chung {lo:.3f} ~ {hi:.3f} V: ket qua duoc noi suy/ngoai suy.")
    hang = []
    for p, g, v in cac:
        ja, jc = xl.noi_suy_dong(g, e_chon)
        hang.append({"Mẫu": nhan, "File": os.path.basename(p), "v (V/s)": v, "Ja (mA/cm2)": ja, "Jc (mA/cm2)": jc,
                     "ΔJ=(Ja-Jc)/2 (mA/cm2)": (ja - jc) / 2})
    b = pd.DataFrame(hang).sort_values("v (V/s)").reset_index(drop=True)
    v = b["v (V/s)"].to_numpy()
    y = b["ΔJ=(Ja-Jc)/2 (mA/cm2)"].to_numpy()
    cdl, tung = np.polyfit(v, y, 1)
    ss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - (cdl * v + tung)) ** 2)) / ss if ss > 0 else float("nan")
    if len(b) < 3:
        print(f"  [{nhan}] (canh bao) chi co {len(b)} toc do quet, Cdl kem tin cay.")
    if np.isfinite(r2) and r2 < 0.98:
        print(f"  [{nhan}] (canh bao) R2 = {r2:.4f} < 0.98: ΔJ khong tuyen tinh theo toc do quet (kiem tra vung dien the / chu ky).")
    return {"nhan": nhan, "mau": mau, "thu_muc": os.path.abspath(thu_muc), "e_chon": float(e_chon), "cdl": float(cdl),
            "tung_mA": float(tung), "r2": r2, "so_diem": int(len(b)), "bang": b,
            "v": [float(x) for x in v], "dj_mA": [float(x) for x in y]}


def tinh_tat_ca(thu_mucs, nhans, maus, a, e_chon=None, chu_ky=None):
    kq, loi = [], []
    for k, tm in enumerate(thu_mucs):
        nhan = nhans[k] if k < len(nhans) and nhans[k] else os.path.basename(os.path.normpath(tm))
        mau = maus[k] if k < len(maus) and maus[k] else None
        try:
            kq.append(tinh_mau(tm, nhan, mau, a, e_chon, chu_ky))
        except ValueError as e:
            loi.append(str(e))
            print("  [LOI] " + str(e))
    return kq, loi


def ghi_json(duong, kq, don_vi_y="A"):
    ra = {"don_vi_y": don_vi_y, "mau": []}
    for r in kq:
        ra["mau"].append({k: r[k] for k in ("nhan", "mau", "thu_muc", "e_chon", "cdl", "tung_mA", "r2", "so_diem", "v", "dj_mA")})
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False)


def doc_json(duong):
    with open(duong, encoding="utf-8") as f:
        return json.load(f)


def he_y(don_vi_y):
    """(hệ số nhân từ mA/cm², nhãn trục) theo đơn vị ΔJ hiển thị."""
    if str(don_vi_y).lower().startswith("m"):
        return 1.0, "ΔJ (mA.cm$^{-2}$)"
    return 1e-3, "ΔJ (A.cm$^{-2}$)"


def cong_thuc_hoa(ten):
    """Cu2O@CuF -> Cu$_{2}$O@CuF (chỉ số dưới cho công thức hóa học trong chú thích)."""
    if "$" in ten:
        return ten
    return re.sub(r"([A-Z][a-z]?|\))(\d+)", r"\1$_{\2}$", ten)


def cong_thuc_origin(ten):
    """Cu2O -> Cu\\-(2)O (chỉ số dưới theo cú pháp văn bản của Origin)."""
    return re.sub(r"([A-Z][a-z]?|\))(\d+)", r"\1\\-(\2)", ten)


def dinh_dang_cdl(c):
    return f"{c:.0f}" if c >= 10 else f"{c:.1f}".rstrip("0").rstrip(".")


def ve_mpl(kq, duong_png, don_vi_y="A", in_cdl=True, in_dam=True, co_chu=14, x_max=None, y_max=None):
    """Hình như bài báo: ΔJ theo tốc độ quét; điểm theo mẫu, đường fit nét đứt cùng màu, nhãn Cdl xoay theo đường."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import xu_ly_dien_hoa as xl
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    nhan_y, lab_y = he_y(don_vi_y)
    dam = "bold" if in_dam else "normal"
    from matplotlib import font_manager
    co_arial = any(f.name == "Arial" for f in font_manager.fontManager.ttflist)
    with plt.rc_context({"font.weight": dam, "axes.labelweight": dam, "font.family": "Arial" if co_arial else "DejaVu Sans"}):
        fig, ax = plt.subplots(figsize=(7.4, 5.8))
        xs_all, ys_all = [], []
        for k, r in enumerate(kq):
            mau = r["mau"] or xl.BANG_MAU[k % len(xl.BANG_MAU)]
            v = np.array(r["v"])
            y = np.array(r["dj_mA"]) * nhan_y
            ax.plot(v, y, KY_HIEU[k % len(KY_HIEU)], color=mau, ms=7, ls="none", label=cong_thuc_hoa(r["nhan"]), zorder=3)
            xf = np.array([v.min(), v.max()])
            yf = (r["cdl"] * xf + r["tung_mA"]) * nhan_y
            ax.plot(xf, yf, "--", color=mau, lw=1.8, zorder=2)
            xs_all += list(v)
            ys_all += list(y) + list(yf)
            r["_xf"], r["_yf"], r["_mau"] = xf, yf, mau
        xm = x_max if x_max else max(xs_all) * 1.2
        ym = y_max if y_max else max(ys_all) * 1.15
        ax.set_xlim(0, xm)
        ax.set_ylim(0, ym)
        ax.set_xlabel("Scan rate (V.s$^{-1}$)", fontsize=co_chu + 2)
        ax.set_ylabel(lab_y, fontsize=co_chu + 2)
        xl.kieu_khung(ax)
        ax.tick_params(which="major", labelsize=co_chu)
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            t.set_fontweight(dam)
        leg = ax.legend(loc="upper left", frameon=False, fontsize=co_chu, handletextpad=0.6, labelspacing=0.5)
        for t, r in zip(leg.get_texts(), kq):
            t.set_color(r["_mau"])
        fig.tight_layout()
        if in_cdl:                                         # nhãn xoay theo độ dốc hiển thị: cần tọa độ đã chốt
            fig.canvas.draw()
            for r in kq:
                p0 = ax.transData.transform((r["_xf"][0], r["_yf"][0]))
                p1 = ax.transData.transform((r["_xf"][1], r["_yf"][1]))
                goc = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
                ax.annotate(f"C$_{{dl}}$ = {dinh_dang_cdl(r['cdl'])} mF.cm$^{{-2}}$", xy=(r["_xf"][1], r["_yf"][1]),
                            xytext=(-6, 9), textcoords="offset points", rotation=goc, rotation_mode="anchor",
                            ha="right", va="bottom", color=r["_mau"], fontsize=co_chu - 2, fontweight=dam)
        fig.savefig(duong_png, dpi=200)
        if duong_png.lower().endswith(".png"):
            fig.savefig(duong_png[:-4] + ".pdf")
        plt.close(fig)


def luu_bang(kq, ra):
    tong = pd.DataFrame([{"Mẫu": r["nhan"], "Thư mục": r["thu_muc"], "E lấy dòng (V vs RHE)": r["e_chon"],
                          "Cdl (mF/cm2)": r["cdl"], "R2": r["r2"], "Số tốc độ quét": r["so_diem"],
                          "Hệ số chặn (mA/cm2)": r["tung_mA"]} for r in kq])
    diem = pd.concat([r["bang"] for r in kq], ignore_index=True) if kq else pd.DataFrame()
    tong.to_csv(os.path.join(ra, "Cdl_nhieu_tong_hop.csv"), index=False, encoding="utf-8-sig")
    diem.to_csv(os.path.join(ra, "Cdl_nhieu_diem.csv"), index=False, encoding="utf-8-sig")
    return tong, diem


def chay(thu_mucs, a, ra, ve=True):
    """Điểm vào từ dòng lệnh (--cdl-nhieu): thu_mucs = các thư mục ECSA; a.nhan / a.mau_file theo thứ tự thư mục."""
    os.makedirs(ra, exist_ok=True)
    kq, loi = tinh_tat_ca(thu_mucs, a.nhan, a.mau_file, a, getattr(a, "e_ecsa", None), a.chu_ky)
    if not kq:
        raise SystemExit("[LOI] Khong tinh duoc Cdl cho mau nao.\n" + "\n".join(loi))
    don_vi = getattr(a, "cdl_y", "A")
    ghi_json(os.path.join(ra, TEN_JSON), kq, don_vi)
    tong, _ = luu_bang(kq, ra)
    if ve:
        ve_mpl(kq, os.path.join(ra, "Cdl_nhieu.png"), don_vi, in_cdl=not getattr(a, "cdl_khong_nhan", False))
        print("  hinh: " + os.path.join(ra, "Cdl_nhieu.png"))
    print(tong.round(4).to_string(index=False))
    if loi:
        print("\nMẫu bị bỏ qua:\n" + "\n".join(loi))
