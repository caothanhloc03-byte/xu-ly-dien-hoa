#!/usr/bin/env python3
"""
Xử lý file điện hóa thô và VẼ TRỰC TIẾP TRONG ORIGIN (Origin 2024).
Hỗ trợ vẽ Nyquist EIS so sánh, CV ECSA đa tốc độ quét và Biểu đồ Tafel.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

import xu_ly_dien_hoa as xl

try:
    import originpro as op
except ImportError:
    sys.exit("Chua cai originpro. Hay chay:  python -m pip install originpro   (can Windows + Origin 2024)")


# ====================== TIỆN ÍCH ORIGIN ======================
def chu_cot(n):
    n += 1
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def lt(doi_tuong, lenh):
    try:
        doi_tuong.lt_exec(lenh)
    except Exception as e:
        print(f"  (canh bao) lenh Origin that bai: {lenh[:60]}  [{e}]")


def tao_so(ten):
    book = op.new_book("w")
    try:
        book.lname = ten
    except Exception:
        pass
    return book, book[0]


def ghi_cot(wks, vi_tri, du_lieu, ten, don_vi="", ghi_chu="", truc="Y"):
    wks.from_list(vi_tri, [float(x) for x in du_lieu], lname=ten, units=don_vi, comments=ghi_chu, axis=truc)


def tao_do_thi(ten, template):
    mau = template if (template and os.path.exists(template)) else (template or "line")
    try:
        return op.new_graph(lname=ten, template=mau)
    except TypeError:
        return op.new_graph(template=mau)


def them_duong(gl, wks, cot_x, cot_y, mau, a, kieu=200):
    p = gl.add_plot(wks, coly=chu_cot(cot_y), colx=chu_cot(cot_x), type=kieu)
    if mau:
        p.color = mau
    if kieu != 201:
        try:
            p.set_cmd(f"-w {int(round(500 * a.day_net))}")
        except Exception:
            pass
    if kieu in (201, 202):
        try:
            p.symbol_size = a.co_diem
        except Exception:
            pass
    return p


def dat_truc(gl, nhan_x, nhan_y, log_x=False):
    try:
        gl.axis("x").title = nhan_x
        gl.axis("y").title = nhan_y
    except Exception:
        pass
    if log_x:
        try:
            gl.axis("x").scale = "log10"
        except Exception:
            pass
    gl.rescale()


def dinh_dang_khung(gl, a):
    cs = a.co_chu
    d = a.day_khung
    cac_lenh = [
        "layer.x.showAxes=3", "layer.y.showAxes=3",
        "layer.x.ticks=10", "layer.y.ticks=10",
        "layer.x2.ticks=0", "layer.y2.ticks=0",
        "layer.x.minorTicks=1", "layer.y.minorTicks=1",
        f"layer.x.thickness={d}", f"layer.y.thickness={d}",
        f"layer.x2.thickness={d}", f"layer.y2.thickness={d}",
        f"layer.x.label.pt={cs}", f"layer.y.label.pt={cs}",
    ]
    for c in cac_lenh:
        lt(gl, c + ";")
    lt(gl, f"double dPW=page.width; double dPH=page.height; layer.unit=1; "
           f"layer.width=min(76, 72*dPH/dPW*{a.ti_le}); layer.height=layer.width*dPW/(dPH*{a.ti_le}); "
           f"layer.left=17; layer.top=8;")


def cuc_dai(*mang):
    """Gia tri lon nhat cua nhieu day so (bo qua NaN)."""
    v = [float(np.nanmax(np.asarray(m, dtype=float))) for m in mang if len(m)]
    return max(v) if v else None


def dat_khoang_truc(gl, x_max, y_max, le):
    """Dau tren cua moi truc chi cach du lieu lon nhat `le` x buoc chia chinh (mac dinh 0.5 buoc)."""
    for tr, vmax in (("x", x_max), ("y", y_max)):
        if vmax is None or le is None or le < 0:
            continue
        try:
            dau = gl.get_float(f"{tr}.from")
            buoc = gl.get_float(f"{tr}.inc")
            cuoi = vmax + le * buoc
            if cuoi <= dau or buoc <= 0:
                continue
            (gl.set_xlim if tr == "x" else gl.set_ylim)(begin=dau, end=cuoi, step=buoc)
        except Exception as e:
            print(f"  (canh bao) khong dat duoc khoang truc {tr}: {e}")


def dinh_dang_chu(gl, a, so_duong=0, chu_thich=True):
    """Dat co chu tieu de truc & chu thich bang API (khong dung lenh LabTalk xb./yl./legend)."""
    cac = [("XB", a.co_chu), ("YL", a.co_chu)]
    if chu_thich:
        cac.append(("Legend", round(a.co_chu * 0.85)))
    for ten, co in cac:
        try:
            o = gl.label(ten)
            if o:
                o.set_int("fsize", int(co))
        except Exception as e:
            print(f"  (canh bao) khong dat duoc co chu {ten}: {e}")
    if chu_thich and so_duong > 0:
        try:
            lg = gl.label("Legend")
            if lg:
                lg.text = "\n".join(f"\\l({i}) %({i})" for i in range(1, so_duong + 1))
        except Exception as e:
            print(f"  (canh bao) khong dat duoc noi dung chu thich: {e}")


def hoan_tat_hinh(gp, gl, a, thu_muc, ten, nhan_x, nhan_y, log_x=False, chu_thich=True,
                  x_max=None, y_max=None, so_duong=0):
    dat_truc(gl, nhan_x, nhan_y, log_x)
    if not log_x:
        dat_khoang_truc(gl, x_max, y_max, a.le_max)
    dinh_dang_khung(gl, a)
    if not a.khong_chinh_chu:
        dinh_dang_chu(gl, a, so_duong, chu_thich)
    duong = os.path.join(thu_muc, ten + ".png")
    gp.save_fig(duong, width=a.rong)
    print(f"  hinh: {duong}")


# ====================== CV / LSV / TAFEL ======================
def ve_cv_lsv_chong(loai, muc, a):
    ten = f"So_sanh_{loai}"
    _, wks = tao_so(ten)
    xs, ys = [], []
    for k, m in enumerate(muc):
        x, y = xl.duong_cv_lsv(m, a.chu_ky)
        xs.append(x)
        ys.append(y)
        ghi_cot(wks, 2 * k, x, "E", "V vs RHE", m["nhan"], "X")
        ghi_cot(wks, 2 * k + 1, y, m["nhan"], "mA/cm2", m["nhan"], "Y")
    gp = tao_do_thi(ten, a.template)
    gl = gp[0]
    for k, m in enumerate(muc):
        them_duong(gl, wks, 2 * k, 2 * k + 1, m["mau"], a)
    hoan_tat_hinh(gp, gl, a, a.thu_muc_ra, ten, xl.NHAN_E, xl.NHAN_I,
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc))


def ve_tafel_chong(muc, a):
    ten = "So_sanh_Tafel"
    _, wks = tao_so(ten)
    xs, ys = [], []
    for k, m in enumerate(muc):
        df_t, slope, _, _ = xl.xu_ly_tafel(m["d"], a.tafel_min, a.tafel_max)
        nhan_s = f"{m['nhan']} ({slope:.1f} mV/dec)"
        xs.append(df_t["Log(J)"].to_numpy())
        ys.append(df_t["Potential (V vs RHE)"].to_numpy())
        ghi_cot(wks, 2 * k, df_t["Log(J)"], "Log(J)", "", nhan_s, "X")
        ghi_cot(wks, 2 * k + 1, df_t["Potential (V vs RHE)"], nhan_s, "V vs RHE", nhan_s, "Y")
    gp = tao_do_thi(ten, a.template)
    gl = gp[0]
    for k, m in enumerate(muc):
        them_duong(gl, wks, 2 * k, 2 * k + 1, m["mau"], a, kieu=202)
    hoan_tat_hinh(gp, gl, a, a.thu_muc_ra, ten, "Log(J)", "Potential (V vs RHE)",
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc))


# ====================== EIS SO SÁNH ======================
def ve_eis(muc, ten, a):
    _, wks = tao_so(ten)
    xs, ys = [], []
    for k, m in enumerate(muc):
        d, b = m["d"], 3 * k
        xs.append(d["Z' (ohm)"].to_numpy())
        ys.append(d["-Z'' (ohm)"].to_numpy())
        ghi_cot(wks, b, d["Z' (ohm)"], "Z'", "ohm", m["nhan"], "X")
        ghi_cot(wks, b + 1, d["-Z'' (ohm)"], m["nhan"], "ohm", m["nhan"], "Y")
    gp = tao_do_thi(f"{ten}_Nyquist", a.template)
    gl = gp[0]
    for k, m in enumerate(muc):
        them_duong(gl, wks, 3 * k, 3 * k + 1, m["mau"], a, kieu=202)
    hoan_tat_hinh(gp, gl, a, a.thu_muc_ra, f"{ten}_Nyquist", "Z' (Ω)", "-Z'' (Ω)", False,
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc))


# ====================== ECSA ======================
def ve_ecsa(ds, a):
    goc = os.path.join(a.thu_muc_ra, os.path.splitext(os.path.basename(ds[0]))[0])
    
    # 1. Vẽ chuỗi CV đa tốc độ quét
    ten_cv = "ECSA_CV_DaTocDo"
    _, wks_cv = tao_so(ten_cv)
    gp_cv = tao_do_thi(ten_cv, a.template)
    gl_cv = gp_cv[0]
    xs_cv, ys_cv = [], []
    
    for k, p in enumerate(ds):
        tho, _ = xl.doc_file_tho(p)
        d, loai = xl.xu_ly_cv_lsv(tho, a)
        ck = a.chu_ky if a.chu_ky is not None else int(d["chu_ky"].max())
        g = d[d["chu_ky"] == ck]
        v_rate = xl.toc_do_quet(d) * 1000
        nhan_v = f"{v_rate:.0f} mV/s"
        
        xs_cv.append(g[xl.COT_E].to_numpy())
        ys_cv.append(g[xl.COT_I].to_numpy())
        ghi_cot(wks_cv, 2 * k, g[xl.COT_E], "E", "V vs RHE", nhan_v, "X")
        ghi_cot(wks_cv, 2 * k + 1, g[xl.COT_I], nhan_v, "mA/cm2", nhan_v, "Y")
        mau = xl.BANG_MAU[k % len(xl.BANG_MAU)]
        them_duong(gl_cv, wks_cv, 2 * k, 2 * k + 1, mau, a, kieu=200)
        
    hoan_tat_hinh(gp_cv, gl_cv, a, a.thu_muc_ra, ten_cv, xl.NHAN_E, xl.NHAN_I,
                  x_max=cuc_dai(*xs_cv), y_max=cuc_dai(*ys_cv), so_duong=len(ds))

    # 2. Vẽ đường tuyến tính Cdl
    b, he_so, tung, r2, e_chon, kq = xl.tinh_ecsa(ds, a, a.e_ecsa, a.cs, a.chu_ky, goc, ve=False)
    v = b["toc_do_quet (mV/s)"].to_numpy()
    y = b["(Ja-Jc)/2 (mA/cm2)"].to_numpy()
    xs = np.linspace(0, v.max(), 50)
    
    ten = "ECSA_Cdl"
    _, wks = tao_so(ten)
    ghi_cot(wks, 0, v, "Scan rate", "mV/s", "", "X")
    ghi_cot(wks, 1, y, "(Ja-Jc)/2", "mA/cm2", f"E = {e_chon:.4f} V vs RHE", "Y")
    ghi_cot(wks, 2, xs, "Scan rate (fit)", "mV/s", "", "X")
    ghi_cot(wks, 3, he_so * xs + tung, "Fit", "mA/cm2", f"Cdl = {he_so:.4f} mF/cm2", "Y")
    
    gp = tao_do_thi(ten, a.template)
    gl = gp[0]
    them_duong(gl, wks, 0, 1, xl.MAU, a, kieu=201)
    them_duong(gl, wks, 2, 3, xl.MAU, a, kieu=200)
    hoan_tat_hinh(gp, gl, a, a.thu_muc_ra, ten, "Scan rate (mV/s)", "(Ja − Jc)/2 (mA/cm²)", chu_thich=False,
                  x_max=cuc_dai(v), y_max=cuc_dai(y, he_so * xs + tung))
    
    ecsa_val = float(kq["ECSA (cm2_ECSA / cm2_hinh_hoc)"].iloc[0])
    print(f"\n======== KẾT QUẢ ECSA ========")
    print(f"Cdl = {he_so:.4f} mF/cm2")
    print(f"ECSA = {ecsa_val:.4f} cm2")
    print(f"==============================\n")


# ====================== CHÍNH ======================
def main():
    ap = argparse.ArgumentParser()
    xl.them_tham_so_chung(ap)
    ap.add_argument("--template", default=None)
    ap.add_argument("--ten-du-an", default="dien_hoa.opju")
    ap.add_argument("--rong", type=int, default=1200)
    ap.add_argument("--co-chu", type=int, default=22)
    ap.add_argument("--day-net", type=float, default=2.0)
    ap.add_argument("--day-khung", type=float, default=3.0)
    ap.add_argument("--le-max", type=float, default=0.5,
                    help="khoang cach tu du lieu lon nhat den dau truc, tinh theo buoc chia chinh")
    ap.add_argument("--khong-chinh-chu", action="store_true",
                    help="khong chinh co chu tieu de/chu thich (dung de kiem tra loi gach tren chu)")
    ap.add_argument("--co-diem", type=float, default=8)
    ap.add_argument("--ti-le", type=float, default=1.28)
    ap.add_argument("--dong-origin", action="store_true")
    a = ap.parse_args()

    ds = xl.mo_rong_file(a.files)
    a.thu_muc_ra = os.path.abspath(a.thu_muc_ra or "origin_out")
    os.makedirs(a.thu_muc_ra, exist_ok=True)

    if getattr(op, "oext", False):
        op.set_show(True)

    if a.ecsa:
        ve_ecsa(ds, a)
    else:
        muc = [xl.nap_muc(p, a, k) for k, p in enumerate(ds)]
        loai_set = set(m["loai"] for m in muc)
        for loai in loai_set:
            nhom = [m for m in muc if m["loai"] == loai]
            if not nhom:
                continue
            if loai in ("CV", "LSV"):
                ve_cv_lsv_chong(loai, nhom, a)
            elif loai == "TAFEL":
                ve_tafel_chong(nhom, a)
            elif loai == "EIS":
                ve_eis(nhom, "So_sanh_EIS", a)

    du_an = os.path.join(a.thu_muc_ra, a.ten_du_an)
    op.save(du_an)
    if a.dong_origin and getattr(op, "oext", False):
        op.exit()


if __name__ == "__main__":
    main()
