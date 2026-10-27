# -*- coding: utf-8 -*-
"""
PHỔ XRD / Raman / XPS / FTIR... (file 2 cột x, y) xếp chồng, chuẩn hóa, đánh dấu đỉnh.
Dùng khi chọn Loại phép đo = "Phổ (XRD / Raman / XPS)". Chỉ xuất ảnh Matplotlib (PNG, PDF) + CSV.
KHÔNG fit/tách đỉnh XPS (chưa hỗ trợ).
"""
import os

import numpy as np
import pandas as pd

KIEU = {
    "xrd": ("2θ (deg)", False),
    "raman": ("Raman shift (cm$^{-1}$)", False),
    "xps": ("Binding energy (eV)", True),        # XPS: trục năng lượng liên kết đảo chiều
    "ftir": ("Wavenumber (cm$^{-1}$)", True),
    "khac": ("x", False),
}


def doc_xy(duong_dan):
    x, y = [], []
    with open(duong_dan, "r", encoding="utf-8", errors="ignore") as f:
        for d in f:
            p = d.replace(",", " ").replace(";", " ").replace("\t", " ").split()
            if len(p) < 2:
                continue
            try:
                x.append(float(p[0]))
                y.append(float(p[1]))
            except ValueError:
                continue
    if len(x) < 5:
        raise ValueError(f"Không đọc được phổ 2 cột (x, y) trong {os.path.basename(duong_dan)}")
    x, y = np.array(x), np.array(y)
    o = np.argsort(x)
    return x[o], y[o]


def tim_dinh(x, y, so_dinh, do_noi_bat=0.06, cua_so=None):
    """Tìm tối đa so_dinh đỉnh cao nhất (cực đại cục bộ có độ nổi bật >= do_noi_bat × biên độ)."""
    n = len(y)
    if so_dinh <= 0 or n < 7:
        return []
    cs = cua_so or max(3, n // 60)
    k = np.ones(max(3, cs // 2 * 2 + 1)) / max(3, cs // 2 * 2 + 1)
    ys = np.convolve(y, k, mode="same")
    bien_do = ys.max() - ys.min()
    if bien_do <= 0:
        return []
    ung_vien = []
    for i in range(cs, n - cs):
        win = ys[i - cs:i + cs + 1]
        if ys[i] == win.max() and ys[i] > win.min():
            trai, phai = ys[max(0, i - 6 * cs):i].min(), ys[i + 1:i + 6 * cs + 1].min()
            noi_bat = ys[i] - max(trai, phai)
            if noi_bat >= do_noi_bat * bien_do:
                ung_vien.append((noi_bat, i))
    ung_vien.sort(reverse=True)
    chon = []
    for _, i in ung_vien:
        if all(abs(x[i] - x[j]) > (x.max() - x.min()) * 0.015 for j in chon):
            chon.append(i)
        if len(chon) >= so_dinh:
            break
    return sorted(chon)


def chay(ds, a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import hinh_bai_bao
    hinh_bai_bao._plt()
    kieu = str(getattr(a, "pho_kieu", "xrd") or "xrd").lower()
    nhan_x, dao = KIEU.get(kieu, KIEU["khac"])
    chuan = not getattr(a, "pho_khong_chuan_hoa", False)
    buoc = float(getattr(a, "pho_doi", 1.1) or 1.1)
    so_dinh = int(getattr(a, "pho_dinh", 0) or 0)
    ra = getattr(a, "thu_muc_ra", None) or os.path.dirname(os.path.abspath(ds[0]))
    os.makedirs(ra, exist_ok=True)

    from xu_ly_dien_hoa import BANG_MAU
    du_lieu = []
    for k, p in enumerate(ds):
        x, y = doc_xy(p)
        nhan = a.nhan[k] if getattr(a, "nhan", None) and k < len(a.nhan) and a.nhan[k] else os.path.splitext(os.path.basename(p))[0]
        mau = a.mau_file[k] if getattr(a, "mau_file", None) and k < len(a.mau_file) and a.mau_file[k] else BANG_MAU[k % len(BANG_MAU)]
        du_lieu.append((nhan, mau, x, y))

    x0 = getattr(a, "pho_x_min", None)
    x1 = getattr(a, "pho_x_max", None)
    fig, ax = plt.subplots(figsize=(6.0, 4.8 + 0.25 * max(0, len(ds) - 3)))
    cot_csv = {}
    for k, (nhan, mau, x, y) in enumerate(du_lieu):
        m = np.ones(len(x), dtype=bool)
        if x0 is not None:
            m &= x >= x0
        if x1 is not None:
            m &= x <= x1
        x, y = x[m], y[m]
        if len(x) < 5:
            print(f"  (canh bao) {nhan}: it diem trong khoang x da chon, bo qua.")
            continue
        yn = (y - y.min()) / (y.max() - y.min() if y.max() > y.min() else 1.0) if chuan else y - y.min()
        off = k * buoc * (1.0 if chuan else float(np.max([np.ptp(d[3]) for d in du_lieu])))
        ax.plot(x, yn + off, lw=1.3, color=mau)
        ax.text(x.max() if not dao else x.min(), off + (0.06 if chuan else 0.06 * yn.max()), nhan, color=mau, fontsize=10,
                ha="right" if not dao else "left", va="bottom")
        for i in tim_dinh(x, yn, so_dinh):
            ax.annotate(f"{x[i]:.4g}" if x[i] < 1000 else f"{x[i]:.0f}", (x[i], yn[i] + off), xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color=mau, rotation=90)
        cot_csv[f"{nhan} | x"] = pd.Series(x)
        cot_csv[f"{nhan} | y"] = pd.Series(yn)
    ax.set_xlabel(getattr(a, "pho_nhan_x", None) or nhan_x, fontsize=11)
    ax.set_ylabel("Intensity (a.u.)", fontsize=11)
    ax.set_yticks([])
    if dao:
        ax.invert_xaxis()
    hinh_bai_bao._khung(ax, 10)
    ax.tick_params(axis="y", which="both", left=False)
    ax.minorticks_on()
    ax.tick_params(axis="y", which="minor", left=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        try:
            fig.savefig(os.path.join(ra, f"Pho_xep_chong.{ext}"), dpi=300)
        except PermissionError:
            print(f"  (canh bao) khong ghi duoc Pho_xep_chong.{ext} - hay dong file dang mo.")
        except Exception as e:
            print(f"  (canh bao) khong luu duoc Pho_xep_chong.{ext}: {e}")
    plt.close(fig)
    try:
        pd.DataFrame(cot_csv).to_csv(os.path.join(ra, "Pho_xep_chong.csv"), index=False, encoding="utf-8-sig")
    except PermissionError:
        pass
    print(f"  pho: {os.path.join(ra, 'Pho_xep_chong.png')} ({len(du_lieu)} pho, {'chuan hoa 0-1' if chuan else 'giu cuong do'}, "
          f"{'tim ' + str(so_dinh) + ' dinh' if so_dinh else 'khong danh dau dinh'})")
