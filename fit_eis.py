# -*- coding: utf-8 -*-
"""
FIT EIS bằng mạch tương đương Randles có CPE:   Z(ω) = Rs + 1 / ( 1/Rct + Q·(jω)^n )

Tham số: Rs (Ω), Rct (Ω), Q (S·s^n), n (0.3–1). Điện dung hiệu dụng theo Brug:
    C_eff = Q^(1/n) · (1/Rs + 1/Rct)^((n-1)/n)
Thuật toán: Levenberg–Marquardt (numpy thuần, không cần scipy), sai số số học tương đối (trọng số 1/|Z|),
chạy nhiều điểm khởi đầu và lấy kết quả tốt nhất.
"""
import os

import numpy as np
import pandas as pd


def mo_hinh(p, w):
    rs, rct, q, n = p
    return rs + 1.0 / (1.0 / rct + q * (1j * w) ** n)


def _du(p, w, z):
    m = mo_hinh(p, w)
    s = 1.0 / np.abs(z)
    return np.concatenate([(m.real - z.real) * s, (m.imag - z.imag) * s])


def _tu_log(x):
    return np.array([np.exp(x[0]), np.exp(x[1]), np.exp(x[2]), np.clip(x[3], 0.3, 1.0)])


def _lm(x0, w, z, so_lan=200):
    x = np.array(x0, dtype=float)
    lam = 1e-2

    def f(x):
        return _du(_tu_log(x), w, z)
    r = f(x)
    cost = float(r @ r)
    for _ in range(so_lan):
        J = np.empty((len(r), len(x)))
        for k in range(len(x)):
            dx = np.zeros_like(x)
            dx[k] = 1e-6 * max(1.0, abs(x[k]))
            J[:, k] = (f(x + dx) - r) / dx[k]
        A, g = J.T @ J, J.T @ r
        tien_bo = False
        for _ in range(12):
            try:
                step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), -g)
            except np.linalg.LinAlgError:
                lam *= 10
                continue
            xm = x + step
            rm = f(xm)
            cm = float(rm @ rm)
            if np.isfinite(cm) and cm < cost:
                x, r, hoi_tu = xm, rm, abs(cost - cm) < 1e-14 * max(cost, 1e-30)
                cost = cm
                lam = max(lam / 3, 1e-9)
                tien_bo = True
                break
            lam *= 4
        if not tien_bo or hoi_tu:
            break
    return x, cost


def fit(f_hz, zr, zi_am):
    """f_hz: tần số; zr = Z'; zi_am = -Z'' (số dương cho cung điện dung). Trả về dict kết quả hoặc raise ValueError."""
    f = np.asarray(f_hz, dtype=float)
    z = np.asarray(zr, dtype=float) - 1j * np.asarray(zi_am, dtype=float)
    ok = np.isfinite(f) & np.isfinite(z.real) & np.isfinite(z.imag) & (f > 0)
    f, z = f[ok], z[ok]
    if len(f) < 6:
        raise ValueError("cần ít nhất 6 điểm tần số hợp lệ để fit EIS")
    w = 2 * np.pi * f
    rs0 = max(float(np.min(z.real)), 1e-3)
    rct0 = max(float(np.max(z.real)) - rs0, 1e-3)
    wp = float(w[np.argmax(-z.imag)])
    tot = None
    for n0 in (0.75, 0.9, 1.0):
        for he in (0.5, 1.0, 2.0):
            q0 = 1.0 / (rct0 * he * wp ** n0)
            x0 = [np.log(rs0), np.log(rct0 * he), np.log(q0), n0]
            x, c = _lm(x0, w, z)
            if np.isfinite(c) and (tot is None or c < tot[1]):
                tot = (x, c)
    if tot is None:
        raise ValueError("fit không hội tụ")
    p = _tu_log(tot[0])
    rs, rct, q, n = (float(v) for v in p)
    m = mo_hinh(p, w)
    sai_so = float(np.sqrt(np.mean(np.abs(m - z) ** 2 / np.abs(z) ** 2)) * 100)
    c_eff = q ** (1 / n) * (1 / rs + 1 / rct) ** ((n - 1) / n)
    wd = np.logspace(np.log10(f.min()), np.log10(f.max()), 200) * 2 * np.pi
    md = mo_hinh(p, wd)
    return {"Rs (ohm)": rs, "Rct (ohm)": rct, "Q (S s^n)": q, "n": n, "C_eff (F)": float(c_eff),
            "sai_so_RMS (%)": sai_so, "so_diem": int(len(f)),
            "_duong_fit": (md.real, -md.imag)}


def xuat_fit(muc, a, thu_muc):
    """Fit tất cả mẫu EIS; in bảng, ghi CSV, vẽ Nyquist có đường fit, ghi vào báo cáo."""
    eis = [m for m in muc if m["loai"] == "EIS"]
    if not eis:
        return None
    s = float(getattr(a, "chia_i", 1.0) or 1.0)
    hang, dd = [], []
    try:
        import canh_bao
    except ImportError:
        canh_bao = None
    for m in eis:
        d = m["d"]
        try:
            r = fit(d["f (Hz)"], d["Z' (ohm)"], d["-Z'' (ohm)"])
        except Exception as e:
            print(f"  (canh bao) khong fit duoc EIS cho {m['nhan']}: {e}")
            continue
        r["Rct x S (ohm cm2)"] = r["Rct (ohm)"] * s
        dd.append((m, r))
        hang.append({"Nhãn": m["nhan"], **{k: v for k, v in r.items() if not k.startswith("_")}})
        if canh_bao and r["sai_so_RMS (%)"] > 10:
            canh_bao.them(canh_bao.CANH_BAO, f"fit EIS có sai số RMS {r['sai_so_RMS (%)']:.1f}% (lớn): mạch Randles-CPE có thể chưa phù hợp "
                          "(có Warburg, nhiều cung, hoặc vùng tần số thấp bị nhiễu).", m["nhan"])
    if not hang:
        return None
    df = pd.DataFrame(hang)
    print("\n======== FIT EIS (Rs + [Rct ‖ CPE]) ========")
    for r in hang:
        print(f"  {r['Nhãn']}: Rs = {r['Rs (ohm)']:.4g} Ω | Rct = {r['Rct (ohm)']:.4g} Ω | Q = {r['Q (S s^n)']:.3g} | "
              f"n = {r['n']:.3f} | C_eff = {r['C_eff (F)']:.3g} F | sai số RMS = {r['sai_so_RMS (%)']:.2f}%")
    print("=============================================")
    os.makedirs(thu_muc, exist_ok=True)
    try:
        df.to_csv(os.path.join(thu_muc, "fit_eis.csv"), index=False, encoding="utf-8-sig")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.0, 4.8))
        for m, r in dd:
            d = m["d"]
            ax.plot(d["Z' (ohm)"], d["-Z'' (ohm)"], "o", ms=4, color=m["mau"], label=m["nhan"])
            ax.plot(*r["_duong_fit"], "-", lw=1.6, color=m["mau"])
        ax.set_xlabel("Z' (Ω)")
        ax.set_ylabel("-Z'' (Ω)")
        ax.set_aspect("equal", adjustable="datalim")
        ax.legend(frameon=True, edgecolor="black", fancybox=False, fontsize=10)
        for sp in ax.spines.values():
            sp.set_linewidth(1.3)
        fig.tight_layout()
        fig.savefig(os.path.join(thu_muc, "fit_eis_Nyquist.png"), dpi=200)
        plt.close(fig)
    except PermissionError:
        print("  (canh bao) khong ghi duoc ket qua fit EIS - hay dong file dang mo.")
    try:
        import bao_cao
        bao_cao.ghi("fit_eis", df.to_dict("records"))
    except ImportError:
        pass
    return df
