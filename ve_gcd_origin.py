#!/usr/bin/env python3
"""Vẽ các đồ thị siêu tụ lai / pin (GCD, GCD nhiều chu kỳ, Csp theo dòng, Ragone, retention + CE, Csp + CE) trực tiếp trong Origin.
Đọc file *_origin.json và các *.csv do gcd_pin.xuat_tat_ca ghi (cặp cột x0,y0,x1,y1,...)."""
import argparse
import json
import os

import pandas as pd

import ve_origin as vo
from ve_origin import op, lt


def _chuoi(df, k):
    x, y = df[f"x{k}"], df[f"y{k}"]
    ok = x.notna() & y.notna()
    return [float(v) for v in x[ok]], [float(v) for v in y[ok]]


def _so(x, mac_dinh):
    try:
        return float(x) if x not in (None, "") else mac_dinh
    except (TypeError, ValueError):
        return mac_dinh


def _kieu_duong(p, s, co_diem, lw=2.0):
    """Đặt kiểu đường/ký hiệu (best-effort, thuộc tính khác nhau giữa các bản Origin). lw: độ dày nét (pt)."""
    try:
        p.set_cmd(f"-w {int(round(500 * lw))}")
    except Exception:
        pass
    if s["kieu"] in ("line", "bar"):
        return
    for thuoc, gia_tri in (("symbol_kind", 2), ("symbol_size", co_diem), ("symbol_interior", 0 if s["kieu"] == "open" else 1)):
        try:
            setattr(p, thuoc, gia_tri)
        except Exception:
            pass


def ve_inset(ma, k, ins, d, a, ten, thu_muc):
    """Ô phóng đại (chu kỳ đầu/cuối) của GCD nhiều chu kỳ: Origin vẽ thành một đồ thị riêng (đặt vào đồ thị chính bằng cách kéo/thả layer
    hoặc Merge Graph Windows); bản Matplotlib/PNG có sẵn ô phóng đại."""
    df = pd.read_csv(ins["csv"], encoding="utf-8-sig")
    ten_k = f"{ten}_{ma}_phongdai{k}"
    book, wks = vo.tao_so(ten_k)
    for j, s in enumerate(ins["series"]):
        x, y = _chuoi(df, j)
        vo.ghi_cot(wks, 2 * j, x, "X", truc="X")
        vo.ghi_cot(wks, 2 * j + 1, y, s["ten"], truc="Y")
    gp = vo.tao_do_thi(ten_k, "line")
    gl = gp[0]
    lw = _so((d.get("hien_thi") or {}).get("lw"), a.day_khung)
    for j, s in enumerate(ins["series"]):
        try:
            p = gl.add_plot(wks, coly=vo.chu_cot(2 * j + 1), colx=vo.chu_cot(2 * j), type=200)
            vo.dat_mau(p, s["mau"])
            _kieu_duong(p, dict(s, kieu="line"), 0, lw * 0.6)
        except Exception as e:
            print(f"  (canh bao) phong dai: {e}")
    try:
        gl.rescale()
        gl.axis("x").title = d["x_nhan"]
        gl.axis("y").title = d["y_nhan"]
    except Exception:
        pass
    try:
        o = gl.label("Legend")
        if o:
            o.remove()
    except Exception:
        pass
    png = os.path.join(thu_muc, f"{ten_k}_origin.png")
    try:
        gp.save_fig(png, width=max(a.rong // 2, 600))
        print("  hinh Origin (ô phóng đại):", png, "-", ins.get("nhan", ""))
    except Exception as e:
        print("  (canh bao) khong luu duoc hinh phong dai:", e)


def ve_mot(ma, d, a, ten, thu_muc):
    df = pd.read_csv(d["csv"], encoding="utf-8-sig")
    series = d["series"]
    ht = d.get("hien_thi") or {}
    lw = _so(ht.get("lw"), a.day_khung)
    co_diem = int(_so(ht.get("co_diem"), a.co_diem))
    co_nhan = int(_so(ht.get("co_nhan"), a.co_chu + 2))
    co_tick = int(_so(ht.get("co_tick"), a.co_chu))
    co_ct = int(_so(ht.get("co_ct"), max(a.co_chu - 2, 8)))
    book, wks = vo.tao_so(f"{ten}_{ma}")
    for k, s in enumerate(series):
        x, y = _chuoi(df, k)
        vo.ghi_cot(wks, 2 * k, x, "X", truc="X")
        vo.ghi_cot(wks, 2 * k + 1, y, s["ten"], truc="Y")
    co_y2 = any(s["truc"] == "y2" for s in series)
    gp = None
    if co_y2:
        try:
            gp = vo.tao_do_thi(f"{ten}_{ma}", "DoubleY")
        except Exception:
            gp = None
    if gp is None:
        gp = vo.tao_do_thi(f"{ten}_{ma}", "line")
        co_y2 = False
    gl = gp[0]
    gl2 = gp[1] if (co_y2 and len(gp) > 1) else None
    co_y2 = gl2 is not None
    for k, s in enumerate(series):
        if s["truc"] == "y2" and not co_y2:
            continue                      # Origin không tạo được trục Y phải: bỏ CE khỏi hình (CSV vẫn có)
        lop = gl2 if s["truc"] == "y2" else gl
        loai = 203 if s["kieu"] == "bar" else (200 if s["kieu"] == "line" else (201 if s["kieu"] == "open" else 202))
        try:
            p = lop.add_plot(wks, coly=vo.chu_cot(2 * k + 1), colx=vo.chu_cot(2 * k), type=loai)
        except Exception as e:
            print(f"  (canh bao) khong them duoc duong {s['ten']}: {e}")
            continue
        vo.dat_mau(p, s["mau"])
        _kieu_duong(p, s, co_diem, lw)
    for l_ in (gl, gl2):
        if l_ is not None:
            try:
                l_.rescale()
            except Exception:
                pass
    try:
        gl.axis("x").title = d["x_nhan"]
        gl.axis("y").title = d["y_nhan"]
        if gl2 is not None:
            gl2.axis("y").title = d.get("y2_nhan", "")
            gl2.set_ylim(begin=0, end=110)
    except Exception:
        pass
    if d.get("log_x"):
        try:
            gl.axis("x").scale = "log10"
        except Exception:
            pass
    if d.get("log_y"):
        try:
            gl.axis("y").scale = "log10"
        except Exception:
            pass
    for lop, lo_k, hi_k, truc in ((gl, "x_min", "x_max", "x"), (gl, "y_min", "y_max", "y"), (gl2, "y2_min", "y2_max", "y")):
        if lop is None or (ht.get(lo_k) in (None, "") and ht.get(hi_k) in (None, "")):
            continue
        try:
            cu = lop.xlim if truc == "x" else lop.ylim
            lo, hi = _so(ht.get(lo_k), cu[0]), _so(ht.get(hi_k), cu[1])
            (lop.set_xlim if truc == "x" else lop.set_ylim)(begin=lo, end=hi)
        except Exception as e:
            print(f"  (canh bao) khong dat duoc khoang truc {lo_k}: {e}")
    for lenh in ("layer.x.showAxes=3;", "layer.y.showAxes=3;", "layer.x.ticks=2;", "layer.y.ticks=2;",
                 f"layer.x.label.pt={co_tick};", f"layer.y.label.pt={co_tick};",
                 f"layer.x.thickness={a.day_khung};", f"layer.y.thickness={a.day_khung};"):
        lt(gl, lenh)
    if ht.get("luoi"):
        lt(gl, "layer.x.showGrids=1; layer.y.showGrids=1;")
    for lop, ten_nhan, co in ((gl, "XB", co_nhan), (gl, "YL", co_nhan), (gl, "Legend", co_ct)):
        try:
            o = lop.label(ten_nhan)
            if o:
                o.set_int("fsize", int(co))
        except Exception:
            pass
    if ht.get("chu_thich", True) is False:
        try:
            lg = gl.label("Legend")
            if lg:
                lg.remove()
        except Exception:
            pass
    png = os.path.join(thu_muc, f"{ten}_{ma}_origin.png")
    try:
        gp.save_fig(png, width=a.rong)
        print("  hinh Origin:", png)
    except Exception as e:
        print("  (canh bao) khong luu duoc hinh:", e)
    for k, ins in enumerate(d.get("insets") or [], 1):
        try:
            ve_inset(ma, k, ins, d, a, ten, thu_muc)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) loi khi ve o phong dai {k}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--thu-muc-ra", default=".")
    ap.add_argument("--rong", type=int, default=1400)
    ap.add_argument("--co-chu", type=int, default=22)
    ap.add_argument("--co-diem", type=int, default=9)
    ap.add_argument("--day-khung", type=float, default=2.0)
    ap.add_argument("--chi", default="", help="chỉ vẽ các đồ thị này (cách nhau bằng dấu phẩy)")
    ap.add_argument("--dong-origin", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.thu_muc_ra, exist_ok=True)
    if getattr(op, "oext", False):
        op.set_show(True)
    vo.phien_ban_origin()
    with open(a.json, encoding="utf-8") as fh:
        mo_ta = json.load(fh)
    chi = {x for x in a.chi.split(",") if x}
    for ma, d in mo_ta["do_thi"].items():
        if chi and ma not in chi:
            continue
        try:
            ve_mot(ma, d, a, mo_ta["ten"], a.thu_muc_ra)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) loi khi ve {ma}: {e}")
    du_an = os.path.join(a.thu_muc_ra, mo_ta["ten"] + "_gcd.opju")
    op.save(du_an)
    print("  du an Origin:", du_an)
    if a.dong_origin and getattr(op, "oext", False):
        op.exit()


if __name__ == "__main__":
    main()
