# -*- coding: utf-8 -*-
"""
HÌNH GHÉP CHUẨN BÀI BÁO: nhiều ô (A), (B), (C)... trong một hình, kích thước theo cột tạp chí,
phông chữ Arial/Helvetica (nếu có), màu đồng bộ theo từng mẫu, xuất PNG/PDF/TIFF 600 dpi.

Các ô tự chọn theo dữ liệu đang có (hoặc chỉ định bằng --hinh-o):
  lsv   : đường J–E (CV: chu kỳ được chọn) + vạch dòng mục tiêu
  tafel : E theo log J + đường fit, hệ số Tafel ghi ở chú thích
  eis   : Nyquist (kèm đường fit Randles–CPE nếu fit được)
  it    : dòng theo thời gian
  cot   : biểu đồ cột so sánh (quá thế hoặc E tại dòng mục tiêu)
"""
import math
import os

import numpy as np

import xu_ly_dien_hoa as xl

CM = 1 / 2.54
RONG_1_COT = 8.6 * CM        # cột đơn (~ 8.6 cm)
RONG_2_COT = 17.8 * CM       # cột đôi (~ 17.8 cm)
ALL_O = ("lsv", "tafel", "eis", "it", "cot")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    ten = {f.name for f in font_manager.fontManager.ttflist}
    for f in ("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"):
        if f in ten:
            plt.rcParams["font.family"] = f
            break
    plt.rcParams.update({"axes.linewidth": 1.0, "xtick.direction": "in", "ytick.direction": "in",
                         "xtick.major.width": 1.0, "ytick.major.width": 1.0, "xtick.minor.width": 0.8,
                         "ytick.minor.width": 0.8, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "mathtext.default": "regular"})
    return plt


def _khung(ax, co=8):
    ax.minorticks_on()
    ax.tick_params(which="major", length=3.5, labelsize=co, top=False, right=False)
    ax.tick_params(which="minor", length=2, top=False, right=False)
    for s in ax.spines.values():
        s.set_linewidth(1.0)


def _chu_o(ax, chu, kieu="hoa"):
    if kieu == "thuong":
        chu = chu.lower()
    ax.text(-0.02, 1.03, f"({chu})", transform=ax.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="left")


def _o_lsv(ax, muc, a):
    for m in muc:
        x, y = xl.duong_cv_lsv(m, getattr(a, "chu_ky", None))
        ax.plot(x, y, lw=1.5, color=m["mau"], label=m["nhan"])
    try:
        j = float(str(getattr(a, "i_muc_tieu", "10")).replace(";", ",").split(",")[0])
        ax.axhline(j, color="0.45", lw=0.8, ls="--")
    except ValueError:
        pass
    ax.set_xlabel(xl.NHAN_E, fontsize=9)
    ax.set_ylabel(xl.NHAN_I, fontsize=9)
    ax.legend(fontsize=7, frameon=False, loc="upper left")


def _o_tafel(ax, muc, a):
    for m in muc:
        try:
            df, slope, a_s, b = xl.tafel_a(m["d"], a)
        except Exception:
            continue
        ax.plot(df["Log(J)"], df["Potential (V vs RHE)"], "o", ms=2.5, color=m["mau"])
        xx = np.array([df["Log(J)"].min(), df["Log(J)"].max()])
        ax.plot(xx, a_s * xx + b, "-", lw=1.4, color=m["mau"], label=f"{m['nhan']} ({abs(slope):.0f} mV dec$^{{-1}}$)")
    ax.set_xlabel("log |J| (mA cm$^{-2}$)", fontsize=9)
    ax.set_ylabel(xl.NHAN_POT, fontsize=9)
    ax.legend(fontsize=7, frameon=True, framealpha=0.85, edgecolor="none", loc="best")


def _o_eis(ax, muc, a):
    try:
        import fit_eis
    except ImportError:
        fit_eis = None
    for m in muc:
        d = m["d"]
        ax.plot(d["Z' (ohm)"], d["-Z'' (ohm)"], "o", ms=2.8, color=m["mau"], label=m["nhan"])
        if fit_eis:
            try:
                r = fit_eis.fit(d["f (Hz)"], d["Z' (ohm)"], d["-Z'' (ohm)"])
                ax.plot(*r["_duong_fit"], "-", lw=1.2, color=m["mau"])
            except Exception:
                pass
    ax.set_xlabel("Z' (Ω)", fontsize=9)
    ax.set_ylabel("−Z'' (Ω)", fontsize=9)
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(fontsize=7, frameon=True, framealpha=0.85, edgecolor="none", loc="best")


def _o_it(ax, muc, a):
    for m, t, i in xl.duong_it(muc, getattr(a, "noi_tiep", False)):
        ax.plot(t, i, lw=1.3, color=m["mau"], label=m["nhan"])
    ax.set_xlabel("Time (h)", fontsize=9)
    ax.set_ylabel(xl.NHAN_I, fontsize=9)
    ax.legend(fontsize=7, frameon=False, loc="best")


def _o_cot(ax, muc, a):
    import so_sanh
    df, info = so_sanh.tong_hop(muc, a)
    if df is None:
        return
    j = info["ds_j"][0]
    cot = f"η tại {j:g} mA/cm² (mV)"
    nhan_y = f"η @ {j:g} mA cm$^{{-2}}$ (mV)"
    if cot not in df:
        cot, nhan_y = f"E tại {j:g} mA/cm² (V)", f"E @ {j:g} mA cm$^{{-2}}$ (V)"
    v = df[cot].astype(float).fillna(0).to_numpy()
    ax.bar(range(len(v)), v, color=list(df["_mau"]), edgecolor="black", linewidth=0.8, width=0.65)
    for k, x in enumerate(v):
        ax.text(k, x, f"{x:.3g}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(v)))
    ax.set_xticklabels([str(x) for x in df["Nhãn"]], rotation=30, ha="right", fontsize=7)
    ax.set_ylabel(nhan_y, fontsize=9)
    ax.set_ylim(0, max(v.max(), 1e-9) * 1.18)
    ax.minorticks_off()


def chon_o(muc, yeu_cau=None):
    co = {m["loai"] for m in muc}
    ds = [o.strip().lower() for o in (yeu_cau or "").replace(";", ",").split(",") if o.strip()]
    if ds:
        return [o for o in ds if o in ALL_O]   # giữ NGUYÊN thứ tự người dùng chọn (có thể lặp lại)
    kq = []
    cv_lsv = [m for m in muc if m["loai"] in ("CV", "LSV")]
    if cv_lsv:
        kq.append("lsv")
        kq.append("tafel")
    if "EIS" in co:
        kq.append("eis")
    if "IT" in co:
        kq.append("it")
    if len(cv_lsv) >= 2:
        kq.append("cot")
    return kq


def _ds_hinh(a):
    """--hinh-o có thể lặp lại: mỗi lần là MỘT hình. Trả về list các chuỗi (None = tự chọn)."""
    v = getattr(a, "hinh_o", None)
    if v is None:
        return [None]
    if isinstance(v, str):
        v = [v]
    kq = [x for x in v if x is not None and str(x).strip()]
    return kq or [None]


def _muc_doi_ten(muc, a):
    """Áp dụng tên mẫu riêng cho hình bài báo (--nhan-hinh, theo thứ tự file); rỗng = giữ nhãn gốc."""
    ten = getattr(a, "nhan_hinh", None) or []
    kq = []
    for k, m in enumerate(muc):
        if k < len(ten) and str(ten[k]).strip():
            m = dict(m, nhan=str(ten[k]).strip())
        kq.append(m)
    return kq


def tao_hinh(muc, a, thu_muc):
    """Trả về danh sách file đã tạo (một hoặc nhiều hình; mỗi --hinh-o là một hình)."""
    muc = _muc_doi_ten(muc, a)
    ds = _ds_hinh(a)
    ra = []
    for k, yc in enumerate(ds):
        ten = "Hinh_bai_bao" if len(ds) == 1 else f"Hinh_bai_bao_{k + 1}"
        ra += _tao_mot(muc, a, thu_muc, yc, ten)
    return ra


def _tao_mot(muc, a, thu_muc, yeu_cau, ten_file):
    plt = _plt()
    ds_o = chon_o(muc, yeu_cau)
    if not ds_o:
        print("  (canh bao) khong co du lieu phu hop de ghep hinh bai bao.")
        return []
    nhom = {"lsv": [m for m in muc if m["loai"] in ("CV", "LSV")], "tafel": [m for m in muc if m["loai"] in ("CV", "LSV", "TAFEL")],
            "eis": [m for m in muc if m["loai"] == "EIS"], "it": [m for m in muc if m["loai"] == "IT"],
            "cot": [m for m in muc if m["loai"] in ("CV", "LSV", "TAFEL")]}
    ds_o = [o for o in ds_o if nhom[o]]
    if not ds_o:
        print("  (canh bao) cac o duoc chon khong co du lieu tuong ung.")
        return []
    n = len(ds_o)
    rong_cot = int(getattr(a, "hinh_cot", 2) or 2)
    if rong_cot == 1:
        w, hang, cot = RONG_1_COT, n, 1
        h = 2.5 * hang
    else:
        w = RONG_2_COT
        cot = 1 if n == 1 else (2 if n <= 4 else 3)
        hang = math.ceil(n / cot)
        h = (w / cot) * 0.8 * hang
    fig, axs = plt.subplots(hang, cot, figsize=(w, h), squeeze=False)
    ham = {"lsv": _o_lsv, "tafel": _o_tafel, "eis": _o_eis, "it": _o_it, "cot": _o_cot}
    for k, ten in enumerate(ds_o):
        ax = axs[k // cot][k % cot]
        ham[ten](ax, nhom[ten], a)
        _khung(ax)
        _chu_o(ax, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[k % 26], getattr(a, "hinh_chu", "hoa"))
    for k in range(n, hang * cot):
        axs[k // cot][k % cot].axis("off")
    fig.tight_layout(w_pad=1.2, h_pad=1.2)
    os.makedirs(thu_muc, exist_ok=True)
    dpi = int(getattr(a, "hinh_dpi", 600) or 600)
    ra = []
    for dang in [x.strip().lower() for x in str(getattr(a, "hinh_dang", "png,pdf,tiff")).replace(";", ",").split(",") if x.strip()]:
        ext = {"tif": "tiff", "jpeg": "jpg"}.get(dang, dang)
        if ext not in ("png", "pdf", "tiff", "svg", "jpg"):
            continue
        duong = os.path.join(thu_muc, f"{ten_file}.{ext}")
        try:
            kw = {"pil_kwargs": {"compression": "tiff_lzw"}} if ext == "tiff" else {}
            fig.savefig(duong, dpi=dpi, **kw)
            ra.append(duong)
        except PermissionError:
            print(f"  (canh bao) khong ghi duoc {os.path.basename(duong)} - hay dong file dang mo.")
        except Exception as e:
            print(f"  (canh bao) khong luu duoc {ext}: {e}")
    plt.close(fig)
    if ra:
        print(f"  hinh bai bao [{ten_file}] ({n} o: {', '.join(ds_o)}; {w / CM:.1f} cm rong; {dpi} dpi): " + ", ".join(os.path.basename(x) for x in ra))
    return ra
