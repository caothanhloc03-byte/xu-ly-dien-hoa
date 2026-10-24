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
    cs = a.co_chu_so if a.co_chu_so is not None else a.co_chu      # co chu so tren truc
    d = a.day_khung
    n_phu = a.vach_phu_so
    kieu_vach = 2 + (8 if n_phu > 0 else 0)       # bit: 2 = vach chinh huong ra, 8 = vach phu huong ra
    day_chinh = a.vach_chinh_day if a.vach_chinh_day is not None else d
    day_phu = a.vach_phu_day if a.vach_phu_day is not None else d
    cac_lenh = [
        "layer.x.showAxes=3", "layer.y.showAxes=3",
        f"layer.x.ticks={kieu_vach}", f"layer.y.ticks={kieu_vach}",
        "layer.x2.ticks=0", "layer.y2.ticks=0",
        f"layer.x.minorTicks={n_phu}", f"layer.y.minorTicks={n_phu}",
        f"layer.x.tickthickness={day_chinh}", f"layer.y.tickthickness={day_chinh}",
        f"layer.x.mtickthickness={day_phu}", f"layer.y.mtickthickness={day_phu}",
        f"layer.x.thickness={d}", f"layer.y.thickness={d}",
        f"layer.x2.thickness={d}", f"layer.y2.thickness={d}",
        f"layer.x.label.pt={cs}", f"layer.y.label.pt={cs}",
    ]
    if a.vach_chinh_dai is not None:
        cac_lenh += [f"layer.x.ticklength={a.vach_chinh_dai}", f"layer.y.ticklength={a.vach_chinh_dai}"]
    if a.vach_phu_dai is not None:
        cac_lenh += [f"layer.x.mticklength={a.vach_phu_dai}", f"layer.y.mticklength={a.vach_phu_dai}"]
    for c in cac_lenh:
        lt(gl, c + ";")
    lt(gl, f"double dPW=page.width; double dPH=page.height; layer.unit=1; "
           f"layer.width=min(76, 72*dPH/dPW*{a.ti_le}); layer.height=layer.width*dPW/(dPH*{a.ti_le}); "
           f"layer.left=17; layer.top=8;")


def cuc_dai(*mang):
    """Gia tri lon nhat cua nhieu day so (bo qua NaN)."""
    v = [float(np.nanmax(np.asarray(m, dtype=float))) for m in mang if len(m)]
    return max(v) if v else None


def khoang_tu_args(a):
    """Khoang truc nguoi dung nhap: {"x": (min, max, buoc), "y": (...)}; None = de tu dong."""
    return {"x": (a.x_min, a.x_max, a.x_buoc), "y": (a.y_min, a.y_max, a.y_buoc)}


def dat_khoang_truc(gl, x_max, y_max, le, khoang=None):
    """Dat khoang truc.
    - Gia tri nguoi dung nhap (min / max / buoc) duoc uu tien.
    - Cho trong thi: min & buoc lay tu Origin tu dong, max = du lieu lon nhat + `le` x buoc chia chinh."""
    khoang = khoang or {}
    for tr, vmax in (("x", x_max), ("y", y_max)):
        t_min, t_max, t_buoc = khoang.get(tr, (None, None, None))
        if t_min is None and t_max is None and t_buoc is None and (vmax is None or le is None or le < 0):
            continue
        try:
            dau = t_min if t_min is not None else gl.get_float(f"{tr}.from")
            buoc = t_buoc if t_buoc is not None else gl.get_float(f"{tr}.inc")
            if t_max is not None:
                cuoi = t_max
            elif vmax is not None and le is not None and le >= 0:
                cuoi = vmax + le * buoc
            else:
                cuoi = gl.get_float(f"{tr}.to")
            if cuoi <= dau or buoc <= 0:
                print(f"  (canh bao) khoang truc {tr} khong hop le (min={dau}, max={cuoi}, buoc={buoc}) - bo qua")
                continue
            (gl.set_xlim if tr == "x" else gl.set_ylim)(begin=dau, end=cuoi, step=buoc)
        except Exception as e:
            print(f"  (canh bao) khong dat duoc khoang truc {tr}: {e}")


def dinh_dang_chu(gl, a, so_duong=0, chu_thich=True):
    """Dat co chu tieu de truc & chu thich bang API (khong dung lenh LabTalk xb./yl./legend)."""
    co_td = a.co_chu_td if a.co_chu_td is not None else (a.co_chu_so if a.co_chu_so is not None else a.co_chu)
    co_ct = a.co_chu_ct if a.co_chu_ct is not None else round(co_td * 0.85)
    cac = [("XB", co_td), ("YL", co_td)]
    if chu_thich:
        cac.append(("Legend", co_ct))
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
                  x_max=None, y_max=None, so_duong=0, khoang=None):
    dat_truc(gl, nhan_x, nhan_y, log_x)
    if not log_x:
        dat_khoang_truc(gl, x_max, y_max, a.le_max, khoang)
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
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc), khoang=khoang_tu_args(a))


# ====================== IT ======================
def ve_it_chong(muc, a):
    ten = "So_sanh_IT"
    _, wks = tao_so(ten)
    xs, ys = [], []
    for k, (m, t, i) in enumerate(xl.duong_it(muc, a.noi_tiep)):
        xs.append(t)
        ys.append(i)
        ghi_cot(wks, 2 * k, t, "T", "h", m["nhan"], "X")
        ghi_cot(wks, 2 * k + 1, i, m["nhan"], "mA/cm2", m["nhan"], "Y")
    gp = tao_do_thi(ten, a.template)
    gl = gp[0]
    for k, m in enumerate(muc):
        them_duong(gl, wks, 2 * k, 2 * k + 1, m["mau"], a)
    hoan_tat_hinh(gp, gl, a, a.thu_muc_ra, ten, "T (h)", xl.NHAN_I,
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc), khoang=khoang_tu_args(a))


def ve_tafel_chong(muc, a):
    ten = "So_sanh_Tafel"
    _, wks = tao_so(ten)
    xs, ys = [], []
    for k, m in enumerate(muc):
        df_t, slope, _, _ = xl.xu_ly_tafel(m["d"], a.tafel_min, a.tafel_max, ten=m["nhan"])
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
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc), khoang=khoang_tu_args(a))


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
                  x_max=cuc_dai(*xs), y_max=cuc_dai(*ys), so_duong=len(muc), khoang=khoang_tu_args(a))


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
        ck = xl.chon_chu_ky(d, a.chu_ky)
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
                  x_max=cuc_dai(*xs_cv), y_max=cuc_dai(*ys_cv), so_duong=len(ds), khoang=khoang_tu_args(a))

    # 2. Vẽ đường tuyến tính Cdl
    b, he_so, tung, r2, e_chon, kq = xl.tinh_ecsa(ds, a, a.e_ecsa, a.cs, a.chu_ky, goc, ve=False)
    v = b["toc_do_quet (mV/s)"].to_numpy()
    y = b["(Ja-Jc)/2 (mA/cm2)"].to_numpy()
    xs = np.linspace(0, v.max(), 50)          # toc do quet, mV/s
    y_fit = he_so * (xs / 1000.0) + tung      # he_so tinh theo V/s (mF/cm2) nen phai doi mV/s -> V/s
    
    ten = "ECSA_Cdl"
    _, wks = tao_so(ten)
    ghi_cot(wks, 0, v, "Scan rate", "mV/s", "", "X")
    ghi_cot(wks, 1, y, "(Ja-Jc)/2", "mA/cm2", f"E = {e_chon:.4f} V vs RHE", "Y")
    ghi_cot(wks, 2, xs, "Scan rate (fit)", "mV/s", "", "X")
    ghi_cot(wks, 3, y_fit, "Fit", "mA/cm2", f"Cdl = {he_so:.4f} mF/cm2", "Y")
    
    gp = tao_do_thi(ten, a.template)
    gl = gp[0]
    them_duong(gl, wks, 0, 1, xl.MAU, a, kieu=201)
    them_duong(gl, wks, 2, 3, xl.MAU, a, kieu=200)
    hoan_tat_hinh(gp, gl, a, a.thu_muc_ra, ten, "Scan rate (mV/s)", "(Ja − Jc)/2 (mA/cm²)", chu_thich=False,
                  x_max=cuc_dai(v), y_max=cuc_dai(y, y_fit))
    
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
    ap.add_argument("--co-chu", type=int, default=22, help="co chu mac dinh (so tren truc neu khong co --co-chu-so)")
    ap.add_argument("--co-chu-so", type=int, default=None, help="co chu so tren truc")
    ap.add_argument("--co-chu-td", type=int, default=None, help="co chu tieu de truc (mac dinh = co chu so)")
    ap.add_argument("--co-chu-ct", type=int, default=None, help="co chu chu thich (mac dinh = 85%% tieu de)")
    ap.add_argument("--vach-chinh-dai", type=float, default=None, help="chieu dai vach chia chinh (pt)")
    ap.add_argument("--vach-chinh-day", type=float, default=None, help="do day vach chinh (mac dinh = day khung)")
    ap.add_argument("--vach-phu-so", type=int, default=1, help="so vach phu giua 2 vach chinh (0 = khong co)")
    ap.add_argument("--vach-phu-dai", type=float, default=None, help="chieu dai vach phu (pt)")
    ap.add_argument("--vach-phu-day", type=float, default=None, help="do day vach phu (mac dinh = day khung)")
    ap.add_argument("--day-net", type=float, default=2.0)
    ap.add_argument("--day-khung", type=float, default=3.0)
    ap.add_argument("--le-max", type=float, default=0.5,
                    help="khoang cach tu du lieu lon nhat den dau truc, tinh theo buoc chia chinh")
    for ten in ("x-min", "x-max", "x-buoc", "y-min", "y-max", "y-buoc"):
        ap.add_argument("--" + ten, type=float, default=None)
    ap.add_argument("--khong-chinh-chu", action="store_true",
                    help="khong chinh co chu tieu de/chu thich (dung de kiem tra loi gach tren chu)")
    ap.add_argument("--co-diem", type=float, default=8)
    ap.add_argument("--ti-le", type=float, default=1.28)
    ap.add_argument("--dong-origin", action="store_true")
    a = ap.parse_args()

    ds = xl.mo_rong_file(a.files)
    a.thu_muc_ra = os.path.abspath(a.thu_muc_ra or "origin_out")
    os.makedirs(a.thu_muc_ra, exist_ok=True)
    xl.khoi_dong_canh_bao(a)

    if getattr(op, "oext", False):
        op.set_show(True)

    if a.ecsa:
        ve_ecsa(ds, a)
    else:
        muc = [xl.nap_muc(p, a, k) for k, p in enumerate(ds)]
        xl.kiem_tra_cac_muc(muc, a)
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
            elif loai == "IT":
                ve_it_chong(nhom, a)

    xl.ket_thuc(a, ds)
    du_an = os.path.join(a.thu_muc_ra, a.ten_du_an)
    op.save(du_an)
    if a.dong_origin and getattr(op, "oext", False):
        op.exit()


if __name__ == "__main__":
    main()
