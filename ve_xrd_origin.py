#!/usr/bin/env python3
"""Vẽ XRD xếp chồng trực tiếp trong Origin (kiểu bài báo: khung kín, nhãn mẫu màu bên trái, không vạch trục Y, nhãn pha trên đỉnh).
Đọc các file do xrd.xuat_tat_ca ghi: *_xep.csv (cặp cột 2θ, I đã xếp chồng) và *_nhan.json."""
import argparse
import json
import os

import pandas as pd

import ve_origin as vo
from ve_origin import op, lt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-xep", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--ten", default="XRD")
    ap.add_argument("--thu-muc-ra", default=".")
    ap.add_argument("--rong", type=int, default=1400)
    ap.add_argument("--co-chu", type=int, default=22)
    ap.add_argument("--day-duong", type=float, default=2.0)
    ap.add_argument("--dong-origin", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.thu_muc_ra, exist_ok=True)
    if getattr(op, "oext", False):
        op.set_show(True)
    vo.phien_ban_origin()
    with open(a.json, encoding="utf-8") as fh:
        kd = json.load(fh)
    df = pd.read_csv(a.csv_xep, encoding="utf-8-sig")
    book, wks = vo.tao_so(a.ten + "_xep")
    wks.from_df(df)
    n = len(kd["mau"])
    for i in range(2 * n):
        try:
            wks.cols_axis("x" if i % 2 == 0 else "y", i, i)
        except Exception:
            pass
    gp = vo.tao_do_thi(a.ten, "line")
    gl = gp[0]
    for i, m in enumerate(kd["mau"]):
        p = gl.add_plot(wks, coly=vo.chu_cot(2 * i + 1), colx=vo.chu_cot(2 * i), type=200)
        vo.dat_mau(p, m["mau"])
        try:
            p.set_cmd(f"-w {int(round(500 * a.day_duong / 2))}")
        except Exception:
            pass
    gl.rescale()
    top = (n - 1) * kd.get("doi", 1.35) + 1.45
    try:
        gl.set_xlim(begin=kd["x_min"], end=kd["x_max"])
        gl.set_ylim(begin=-0.05, end=top)
    except Exception:
        lt(gl, f"layer.x.from={kd['x_min']}; layer.x.to={kd['x_max']}; layer.y.from=-0.05; layer.y.to={top};")
    for lenh in ("layer.y.showLabels=0;", "layer.y.ticks=0;", "layer.y.minorTicks=0;", "layer.x2.ticks=0;", "layer.y2.ticks=0;",
                 "layer.x.showAxes=3;", "layer.y.showAxes=3;", f"layer.x.label.pt={a.co_chu};", "layer.x.thickness=2;",
                 "layer.y.thickness=2;", "layer.x.minorTicks=1;"):
        lt(gl, lenh)
    try:
        gl.axis("x").title = "2θ (degree)"
        gl.axis("y").title = ""
    except Exception:
        pass
    try:
        lg = gl.label("Legend")
        if lg:
            lg.remove()
    except Exception:
        pass

    def chu(text, x, y, mau, pt, doc=False):
        """Đặt chữ theo toạ độ dữ liệu (best-effort; khác nhau theo bản Origin)."""
        try:
            t = gl.add_label(text, x, y)
            try:
                t.set_int("fsize", pt)
                t.set_int("color", 0)
                lt(gl, f'{t.name}.color=color({int(mau[1:3], 16)},{int(mau[3:5], 16)},{int(mau[5:7], 16)});')
            except Exception:
                pass
            return True
        except Exception:
            return False

    for m in kd["mau"]:
        chu(m["ten"], kd["x_min"] + 0.01 * (kd["x_max"] - kd["x_min"]), m["offset"] + 0.35, m["mau"], 22)
    if kd.get("ve_nhan", True):
        for q in kd["nhan"]:
            if q["loai"] in ("pha", "goi_y"):
                chu(q["glyph"], q["x"], q["y"] + 0.07, q["mau_kh"], 20)               # ký hiệu pha (★ ● ■ ◆ ...) cùng màu
                chu(q["hkl"] + ("?" if q["loai"] == "goi_y" else ""), q["x"] + 0.02 * (kd["x_max"] - kd["x_min"]), q["y"] + 0.07, q["mau_kh"], 14)
            elif q["loai"] == "la":
                chu("?", q["x"], q["y"] + 0.05, "#cc0000", 16)
        top_y = (n - 1) * kd.get("doi", 1.35) + 1.45
        for i, c in enumerate(kd.get("chu_giai", [])):
            y = top_y - 0.12 - 0.17 * i
            chu(c["glyph"], kd["x_min"] + 0.03 * (kd["x_max"] - kd["x_min"]), y, c["mau"], 18)
            chu(c["ten"], kd["x_min"] + 0.06 * (kd["x_max"] - kd["x_min"]), y, "#222222", 16)
    png = os.path.join(a.thu_muc_ra, a.ten + "_origin.png")
    try:
        gp.save_fig(png, width=a.rong)
        print("  hinh Origin:", png)
    except Exception as e:
        print("  (canh bao) khong luu duoc hinh:", e)
    du_an = os.path.join(a.thu_muc_ra, a.ten + "_xrd.opju")
    op.save(du_an)
    print("  du an Origin:", du_an)
    if a.dong_origin and getattr(op, "oext", False):
        op.exit()


if __name__ == "__main__":
    main()
