#!/usr/bin/env python3
"""Vẽ phổ XPS đã fit (xps.py) trực tiếp trong Origin: đường bao + các thành phần, trục BE đảo chiều, không vạch trục Y.
Đọc 2 file CSV do xps.py ghi: *_fit.csv (dữ liệu thô) và *_muot.csv (đường cong mịn đã trừ nền)."""
import argparse
import os
import sys

import pandas as pd

import ve_origin as vo
from ve_origin import op, lt

MAU = ["#6baed6", "#fdd49e", "#fb9a8a", "#b2df8a", "#cab2d6", "#a6cee3"]


def to_mau_fill(p, mau, alpha=0.9):
    """Tô màu vùng dưới đường (thử vài cách vì lệnh khác nhau theo bản Origin; không được thì để đường màu, người dùng bật
    Plot Details > Line > Fill Area Under Curve)."""
    h = str(mau).lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    ok = False
    trong = int(round(100 * (1 - max(0.0, min(1.0, alpha)))))              # % trong suốt
    for lenh in (f"-fc color({r},{g},{b})", "-fa 1", f"-f color({r},{g},{b})", f"-ft {trong}"):
        try:
            p.set_cmd(lenh)
            ok = True
        except Exception:
            pass
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-muot", required=True)
    ap.add_argument("--csv-fit", default=None)
    ap.add_argument("--ten", default="XPS")
    ap.add_argument("--thu-muc-ra", default=".")
    ap.add_argument("--x-min", type=float, default=None)
    ap.add_argument("--x-max", type=float, default=None)
    ap.add_argument("--rong", type=int, default=1200)
    ap.add_argument("--day-bao", type=float, default=4.0)
    ap.add_argument("--co-chu", type=int, default=22)
    ap.add_argument("--dong-origin", action="store_true")
    ap.add_argument("--kieu", default=None, help="file JSON kiểu vẽ do app ghi (màu từng thành phần, tô/không tô, độ đậm, màu đường bao)")
    a = ap.parse_args()
    os.makedirs(a.thu_muc_ra, exist_ok=True)
    if getattr(op, "oext", False):
        op.set_show(True)
    vo.phien_ban_origin()

    df = pd.read_csv(a.csv_muot, encoding="utf-8-sig")
    cot = list(df.columns)
    import json
    kieu = {}
    if a.kieu and os.path.isfile(a.kieu):
        with open(a.kieu, encoding="utf-8") as fh:
            kieu = json.load(fh)
    mau = list(kieu.get("mau") or MAU)
    to = list(kieu.get("to") or [])
    alpha = float(kieu.get("alpha", 0.9))
    mau_bao = kieu.get("mau_bao", "#595959")
    if "day_bao" in kieu:
        a.day_bao = float(kieu["day_bao"])                          # BE_eV, Envelope_sub, thanh phan...
    book, wks = vo.tao_so(a.ten + "_fit_muot")
    wks.from_df(df)
    for i, c in enumerate(cot):
        try:
            wks.cols_axis("x" if i == 0 else "y", i, i)
        except Exception:
            pass
    if a.csv_fit and os.path.isfile(a.csv_fit):
        b2, w2 = vo.tao_so(a.ten + "_du_lieu")
        w2.from_df(pd.read_csv(a.csv_fit, encoding="utf-8-sig"))

    gp = vo.tao_do_thi(a.ten, "line")
    gl = gp[0]
    # vẽ thành phần trước (nằm dưới), đường bao sau cùng (nằm trên)
    so_tp = len(cot) - 2
    for k in range(so_tp):
        p = gl.add_plot(wks, coly=vo.chu_cot(2 + k), colx="A", type=200)
        mk = mau[k % len(mau)]
        vo.dat_mau(p, mk)
        if k >= len(to) or to[k]:                       # tô vùng dưới đường theo lựa chọn của người dùng
            to_mau_fill(p, mk, alpha)
        try:
            p.set_cmd("-w 500")
        except Exception:
            pass
    pb = gl.add_plot(wks, coly="B", colx="A", type=200)
    vo.dat_mau(pb, mau_bao)
    try:
        pb.set_cmd(f"-w {int(round(500 * a.day_bao / 2))}")
    except Exception:
        pass
    gl.rescale()
    lo = a.x_min if a.x_min is not None else float(df[cot[0]].min())
    hi = a.x_max if a.x_max is not None else float(df[cot[0]].max())
    try:
        gl.set_xlim(begin=hi, end=lo, step=2)           # begin > end: trục BE đảo chiều
    except Exception as e:
        print(f"  (canh bao) khong dao duoc truc BE: {e}")
        lt(gl, f"layer.x.from={hi}; layer.x.to={lo};")
    try:
        ymax = float(df["Envelope_sub"].max())
        gl.set_ylim(begin=-0.04 * ymax, end=1.1 * ymax)
    except Exception:
        pass
    for lenh in ("layer.y.showLabels=0;", "layer.y.ticks=0;", "layer.y.minorTicks=0;", "layer.x2.ticks=0;", "layer.y2.ticks=0;",
                 "layer.x.showAxes=3;", "layer.y.showAxes=3;", f"layer.x.label.pt={a.co_chu};", "layer.x.thickness=2;",
                 "layer.y.thickness=2;", "layer.x.minorTicks=1;"):
        lt(gl, lenh)
    try:
        gl.axis("x").title = "Binding Energy (eV)"
        gl.axis("y").title = ""
    except Exception:
        pass
    try:
        lg = gl.label("Legend")
        if lg:
            lg.remove()
    except Exception:
        pass
    try:
        t = gl.add_label(a.ten, 0.06, 0.92) if hasattr(gl, "add_label") else None
    except Exception:
        t = None
    if t is None:
        lt(gl, f'label -a 0.06 0.92 -n title "{a.ten}";')
    png = os.path.join(a.thu_muc_ra, a.ten + "_origin.png")
    try:
        gp.save_fig(png, width=a.rong)
        print("  hinh Origin:", png)
    except Exception as e:
        print("  (canh bao) khong luu duoc hinh:", e)
    du_an = os.path.join(a.thu_muc_ra, a.ten + "_xps.opju")
    op.save(du_an)
    print("  du an Origin:", du_an)
    if a.dong_origin and getattr(op, "oext", False):
        op.exit()


if __name__ == "__main__":
    main()
