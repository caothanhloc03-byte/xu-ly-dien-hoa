# -*- coding: utf-8 -*-
"""Phân tích XRD: đọc dữ liệu thô (Excel/CSV), nền, tìm và fit đỉnh (pseudo-Voigt + Kα2), xác định pha bằng ngân hàng phổ,
phân biệt đỉnh của mẫu / của đế / bức xạ phụ / tạp, so sánh nhiều mẫu và viết minh chứng bằng lời dễ hiểu. Chỉ dùng numpy."""
import math
import os
import re

import numpy as np

import xrd_ngan_hang as nh
from xps import _lm, _anh_xa, _anh_xa_nguoc

LN2_4 = 4.0 * math.log(2.0)
NGUON_MAC_DINH = "Cu Kα (1.5406)"


# ====================== ĐỌC DỮ LIỆU ======================
def _la_so(v):
    return isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool) and math.isfinite(float(v))


def _cat_mau(x, y, ten, nguon):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    o = np.argsort(x)
    x, y = x[o], y[o]
    if len(x) < 30:
        raise ValueError(f"Mẫu '{ten}' có quá ít điểm.")
    return {"ten": str(ten), "x": x, "y": y, "nguon": nguon}


def doc_excel(duong):
    """Excel: mỗi cặp cột (2θ, cường độ) là một mẫu. Tên mẫu lấy ở hàng tiêu đề phía trên (hoặc tên cột)."""
    import openpyxl
    wb = openpyxl.load_workbook(duong, read_only=True, data_only=True)
    ket_qua = []
    for ws in wb.worksheets:
        hang = [list(r) for r in ws.iter_rows(values_only=True)]
        if len(hang) < 10:
            continue
        ncot = max(len(r) for r in hang)
        for r in hang:
            r.extend([None] * (ncot - len(r)))
        # tìm hàng đầu tiên có dữ liệu số ở cả cột x
        j = 0
        while j < ncot:
            col = [r[j] for r in hang]
            so = [i for i, v in enumerate(col) if _la_so(v)]
            nxt = [r[j + 1] if j + 1 < ncot else None for r in hang]
            if len(so) >= 30 and j + 1 < ncot and sum(_la_so(v) for v in nxt) >= 30:
                i0 = so[0]
                x = [col[i] for i in so]
                y = [nxt[i] if _la_so(nxt[i]) else np.nan for i in so]
                ten = None
                for i in range(i0 - 1, -1, -1):          # hàng tiêu đề: ưu tiên tên mẫu (không chứa '2-theta', 'intensity')
                    for c in (hang[i][j], hang[i][j + 1]):
                        if isinstance(c, str) and c.strip() and not re.search(r"theta|2θ|intens|count|deg|cps", c, re.I):
                            ten = c.strip()
                            break
                    if ten:
                        break
                ten = ten or f"{ws.title}_{len(ket_qua) + 1}"
                try:
                    ket_qua.append(_cat_mau(x, y, ten, f"{os.path.basename(duong)}:{ws.title}"))
                except ValueError:
                    pass
                j += 2
            else:
                j += 1
    return ket_qua


def doc_van_ban(duong):
    """CSV/TXT/XY/DAT: cột 1 = 2θ; các cột còn lại là cường độ của từng mẫu (tên ở dòng tiêu đề nếu có)."""
    with open(duong, "r", encoding="utf-8-sig", errors="ignore") as f:
        dong = f.read().splitlines()
    cot_ten, hang = [], []
    for d in dong:
        p = [t for t in re.split(r"[\t,; ]+", d.strip()) if t != ""]
        if len(p) >= 2:
            try:
                hang.append([float(t) for t in p])
                continue
            except ValueError:
                if not hang:
                    cot_ten = p
    if len(hang) < 30:
        raise ValueError("Không đọc được bảng số (2θ, cường độ) trong file.")
    n = min(len(h) for h in hang)
    a = np.array([h[:n] for h in hang], float)
    ten0 = os.path.splitext(os.path.basename(duong))[0]
    if n == 2:
        return [_cat_mau(a[:, 0], a[:, 1], ten0, os.path.basename(duong))]
    kq = []
    for k in range(1, n):
        ten = cot_ten[k] if len(cot_ten) == n else f"{ten0}_{k}"
        kq.append(_cat_mau(a[:, 0], a[:, k], ten, os.path.basename(duong)))
    return kq


def doc_xrd(duong):
    ext = os.path.splitext(duong)[1].lower()
    ds = doc_excel(duong) if ext in (".xlsx", ".xlsm") else doc_van_ban(duong)
    if not ds:
        raise ValueError("Không tìm thấy cặp cột (2θ, cường độ) nào trong file.")
    # loại mẫu trùng hệt (cùng dữ liệu) và đặt tên duy nhất
    kq, thay = [], []
    for m in ds:
        trung = next((k for k in kq if len(k["y"]) == len(m["y"]) and np.allclose(k["y"], m["y"]) and np.allclose(k["x"], m["x"])), None)
        if trung is not None:
            thay.append(f"'{m['ten']}' trùng hệt dữ liệu của '{trung['ten']}' nên bỏ qua.")
            continue
        kq.append(m)
    dem = {}
    for m in kq:
        dem[m["ten"]] = dem.get(m["ten"], 0) + 1
    seen = {}
    for m in kq:
        if dem[m["ten"]] > 1:
            seen[m["ten"]] = seen.get(m["ten"], 0) + 1
            m["ten"] = f"{m['ten']} ({seen[m['ten']]})"
    for m in kq:
        m["ghi_doc"] = thay
    return kq


# ====================== XỬ LÝ TÍN HIỆU ======================
def _sg_he_so(n, bac=2):
    n = max(int(n) | 1, bac + 3 | 1)
    h = n // 2
    A = np.vander(np.arange(-h, h + 1), bac + 1, increasing=True)
    return np.linalg.pinv(A)[0]


def lam_tron(y, n):
    c = _sg_he_so(n)
    h = len(c) // 2
    p = np.pad(np.asarray(y, float), h, mode="reflect")
    return np.convolve(p, c[::-1], mode="valid"), float(np.sqrt(np.sum(c ** 2)))


def uoc_luong_nhieu(y):
    """Độ lệch chuẩn nhiễu từng điểm: MAD của sai phân bậc 1 (ít bị đỉnh ảnh hưởng)."""
    d = np.diff(np.asarray(y, float))
    return float(1.4826 * np.median(np.abs(d - np.median(d))) / math.sqrt(2.0)) or 1e-9


def nen_snip(y, rong_diem):
    """Nền SNIP (cửa sổ giảm dần) trên biến đổi LLS: bám chân phổ, bỏ qua đỉnh hẹp hơn cửa sổ."""
    y = np.asarray(y, float)
    mn = float(y.min())
    v = np.log(np.log(np.sqrt(y - mn + 1.0) + 1.0) + 1.0)
    n = len(v)
    for m in range(int(max(rong_diem, 2)), 0, -1):
        w = v.copy()
        w[m:n - m] = np.minimum(v[m:n - m], 0.5 * (v[:n - 2 * m] + v[2 * m:]))
        v = w
    return (np.exp(np.exp(v) - 1.0) - 1.0) ** 2 - 1.0 + mn


def pv(x, x0, w, eta):
    t = (np.asarray(x, float) - x0) / w
    return eta / (1.0 + 4.0 * t * t) + (1.0 - eta) * np.exp(-LN2_4 * t * t)


def dien_tich_pv(A, w, eta):
    return A * w * (eta * math.pi / 2.0 + (1.0 - eta) * math.sqrt(math.pi / LN2_4))


def vi_tri_ka2(tt, lam1, lam2):
    s = (lam2 / lam1) * math.sin(math.radians(tt / 2.0))
    return 2.0 * math.degrees(math.asin(min(s, 1.0)))


def _mo_hinh_nhom(x, p, nd, lam1, lam2, ti_le_ka2):
    """p = [b0, b1, b2] (nền bậc 2 quanh tâm cửa sổ) + nd * [A, x0, w, eta]; có thành phần Kα2 nếu lam2."""
    xc = x[len(x) // 2]
    t = x - xc
    s = p[0] + p[1] * t + p[2] * t * t
    for i in range(nd):
        A, x0, w, eta = p[3 + 4 * i: 7 + 4 * i]
        s = s + A * pv(x, x0, w, eta)
        if lam2:
            x2 = vi_tri_ka2(x0, lam1, lam2)
            w2 = w * math.cos(math.radians(x0 / 2)) / max(math.cos(math.radians(x2 / 2)), 1e-6) * (lam2 / lam1) ** 0 
            s = s + ti_le_ka2 * A * pv(x, x2, w2, eta)
    return s


def fit_nhom(x, y, ung, lam1, lam2, ti_le_ka2, sigma, w_min, w_max):
    """Fit chung một nhóm đỉnh gần nhau + nền bậc 2 cục bộ. ung: list (x0, cao, w). Trả về list dict tham số ± sai số, chi2 rút gọn."""
    nd = len(ung)
    # trọng số: nhiễu đếm + sai số mô hình ~2% cường độ (đuôi đỉnh mạnh không bao giờ khớp hoàn hảo) -> đỉnh mạnh không át đỉnh yếu bên cạnh
    ysm = np.convolve(np.pad(y, 2, mode="edge"), np.ones(5) / 5.0, mode="valid")
    sig_v = np.sqrt(sigma ** 2 + (0.02 * np.maximum(ysm - ysm.min(), 0.0)) ** 2)
    b0 = float(np.median(np.r_[y[:6], y[-6:]]))
    rng_y = float(np.ptp(y)) + 10 * sigma
    gh = [(b0 - 0.3 * rng_y, b0 + 0.3 * rng_y), (-rng_y / max(x[-1] - x[0], 1e-6), rng_y / max(x[-1] - x[0], 1e-6)),
          (-4 * rng_y / max(x[-1] - x[0], 1e-6) ** 2, 4 * rng_y / max(x[-1] - x[0], 1e-6) ** 2)]
    p0 = [b0, 0.0, 0.0]
    for (x0, h, w) in ung:
        gh += [(0.0, max(h * 4, 10 * sigma)), (x0 - 0.12, x0 + 0.12), (w_min, w_max), (0.0, 1.0)]
        p0 += [max(h, sigma), x0, min(max(w, w_min * 1.05), w_max * 0.95), 0.5]

    def tp(u):
        return np.array([_anh_xa(u[i], *gh[i]) for i in range(len(u))])

    def f(u):
        return (y - _mo_hinh_nhom(x, tp(u), nd, lam1, lam2, ti_le_ka2)) / sig_v

    u0 = [_anh_xa_nguoc(p0[i], *gh[i]) for i in range(len(p0))]
    u, c2 = _lm(f, u0, so_buoc=150)
    p = tp(u)
    k = len(p)
    J = np.empty((len(x), k))
    base = _mo_hinh_nhom(x, p, nd, lam1, lam2, ti_le_ka2) / sig_v
    for j in range(k):
        h = max(abs(p[j]) * 1e-5, 1e-7)
        q = p.copy()
        q[j] += h
        J[:, j] = (_mo_hinh_nhom(x, q, nd, lam1, lam2, ti_le_ka2) / sig_v - base) / h
    s2 = c2 / max(len(x) - k, 1)
    try:
        sd = np.sqrt(np.maximum(np.diag(np.linalg.pinv(J.T @ J)) * max(s2, 1.0), 0))
    except np.linalg.LinAlgError:
        sd = np.full(k, np.nan)
    kq = []
    for i in range(nd):
        A, x0, w, eta = p[3 + 4 * i: 7 + 4 * i]
        kq.append({"A": float(A), "A_sd": float(sd[3 + 4 * i]), "tt": float(x0), "tt_sd": float(sd[4 + 4 * i]), "fwhm": float(w),
                   "fwhm_sd": float(sd[5 + 4 * i]), "eta": float(eta)})
    return kq, float(s2)


def _hat_loc(buoc, fwhm):
    """Hạt nhân lọc khớp = -G'' (Mexican hat) cho đỉnh FWHM = fwhm. Triệt nền tuyến tính/đuôi chậm, khuếch đại đỉnh cùng cỡ."""
    sg = fwhm / 2.3548 / buoc
    n = int(max(4 * sg, 3))
    t = np.arange(-n, n + 1) / sg
    k = (1.0 - t * t) * np.exp(-0.5 * t * t)
    k -= k.mean()
    return k / np.sqrt(np.sum(k * k))


def tim_dinh(x, y, nguon=NGUON_MAC_DINH, k_snr=5.0, fwhm_may=None, kalpha2=True, nen_deg=3.0, ti_le_ka2=0.5):
    """Tìm và fit đỉnh nhiễu xạ bằng lọc khớp đa thang (ổn với nền cong, đuôi của đỉnh rất mạnh) rồi fit pseudo-Voigt + Kα2.
    k_snr: ngưỡng nhận biết (σ của bộ lọc). Trả về dict: peaks (đã chấp nhận), bi_loai (kèm lý do), nen, fwhm_may, sigma..."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    buoc = float(np.median(np.diff(x)))
    lam1, lam2, _ = nh.NGUON[nguon]
    lam2 = lam2 if kalpha2 else None
    sigma_raw = uoc_luong_nhieu(y)
    ys, he_so = lam_tron(y, max(5, int(round(0.1 / buoc)) | 1))
    nen = nen_snip(ys, nen_deg / buoc / 2.0)
    # bề rộng của máy: đỉnh mạnh nhất, fit riêng
    i0 = int(np.argmax(ys))
    inst = fwhm_may
    if inst is None:
        inst = 0.1
        if ys[i0] - np.median(ys) > 100 * sigma_raw * he_so:
            m = (x > x[i0] - 0.7) & (x < x[i0] + 0.7)
            try:
                f0, _ = fit_nhom(x[m], y[m], [(x[i0], ys[i0] - np.median(ys), 0.12)], lam1, lam2, ti_le_ka2, sigma_raw, 0.02, 1.0)
                inst = float(min(max(f0[0]["fwhm"], 3 * buoc), 0.5))
            except Exception:
                pass
    inst_ok = fwhm_may is not None or inst != 0.1
    # lọc khớp đa thang
    thang = [inst * f for f in (1.0, 2.0, 4.0, 8.0) if inst * f <= 3.0]
    z = np.full(len(x), -1e9)
    thang_tot = np.zeros(len(x))
    for s in thang:
        k = _hat_loc(buoc, s)
        R = np.convolve(np.pad(y, len(k) // 2, mode="reflect"), k[::-1], mode="valid")
        mad = 1.4826 * float(np.median(np.abs(R - np.median(R))))
        sg_r = max(mad, sigma_raw)                    # sigma lý thuyết (nhiễu trắng) và thực nghiệm (nhiễu màu / cấu trúc nền)
        zs = R / sg_r
        gt = zs > z
        z[gt] = zs[gt]
        thang_tot[gt] = s
    # ứng viên: cực đại địa phương của z vượt ngưỡng
    n_sep = max(int(round(inst / buoc)), 3)
    ung = []
    for i in range(n_sep, len(x) - n_sep):
        if z[i] >= k_snr and z[i] == z[i - n_sep: i + n_sep + 1].max():
            ung.append(i)
    bi_loai, ket = [], []
    if ung:
        ung = sorted(ung, key=lambda i: -z[i])
        # gom nhóm theo vị trí
        xs = sorted(ung, key=lambda i: x[i])
        nhom, cur = [], [xs[0]]
        for i in xs[1:]:
            if x[i] - x[cur[-1]] < 2.5:
                cur.append(i)
            else:
                nhom.append(cur)
                cur = [i]
        nhom.append(cur)
        for g in nhom:
            g = sorted(g, key=lambda i: -z[i])[:5]
            g.sort()
            ws = [max(thang_tot[i], inst) for i in g]
            lo, hi = x[g[0]] - max(0.8, 4 * ws[0]), x[g[-1]] + max(0.8, 4 * ws[-1])
            m = (x >= lo) & (x <= hi)
            if m.sum() < 15:
                continue
            ung_nhom = [(x[i], max(float(ys[i] - np.median(ys[m])), sigma_raw), min(ws[k], 3.0)) for k, i in enumerate(g)]
            fits = None
            for he in (1.0, 2.5, 5.0):                    # nhiều điểm xuất phát về độ rộng, giữ nghiệm có chi2 nhỏ nhất
                try:
                    f_, s_ = fit_nhom(x[m], y[m], [(a, b, min(c * he, 3.0)) for a, b, c in ung_nhom], lam1, lam2, ti_le_ka2, sigma_raw,
                                      max(buoc * 2.0, 0.5 * inst), 4.0)
                except Exception:
                    continue
                if fits is None or s_ < s2:
                    fits, s2 = f_, s_
            if fits is None:
                continue
            for k, fi in enumerate(fits):
                fi["chi2_red"] = s2
                fi["z"] = float(z[g[k]])
                ket.append(fi)
    ket.sort(key=lambda f: f["tt"])
    manh = [f for f in ket if f["A"] > 60 * sigma_raw * he_so]
    # loại: ở sát đỉnh mạnh (đuôi/vai/Kα2), quá hẹp/rộng, sai số lớn
    peaks, n_doc_lap = [], max((x[-1] - x[0]) / max(inst, 0.05), 1.0)
    for f in ket:
        ly = []
        snr_fit = f["A"] / f["A_sd"] if f["A_sd"] and f["A_sd"] > 0 else 0.0
        if f["fwhm"] < 0.7 * inst:
            ly.append(f"hẹp hơn độ phân giải máy ({f['fwhm']:.3f}° < {0.7 * inst:.3f}°): nhiều khả năng nhiễu/gai, không phải đỉnh nhiễu xạ")
        if f["fwhm"] > 3.0:
            ly.append("quá rộng (> 3°): giống nền cong/vô định hình hơn là đỉnh")
        if snr_fit < 3.0:
            ly.append(f"fit không xác định được biên độ chắc chắn (A/σ = {snr_fit:.1f} < 3)")
        if f["tt_sd"] and f["tt_sd"] > max(0.5 * f["fwhm"], 0.05):
            ly.append("vị trí không xác định được (sai số > nửa độ rộng)")
        for st in manh:
            if st is f or st["A"] < 20 * f["A"]:
                continue
            dist = abs(f["tt"] - st["tt"])
            ka2 = abs(f["tt"] - vi_tri_ka2(st["tt"], lam1, lam2)) if lam2 else 9
            if dist < 2.5 * st["fwhm"] or ka2 < 2.5 * st["fwhm"]:
                ly.append(f"nằm trong vùng đuôi/vai/Kα2 của đỉnh mạnh {st['tt']:.2f}° (không phân biệt được)")
                break
        d = nh_d(f["tt"], lam1)
        p_gia = min(1.0, n_doc_lap * 0.5 * math.erfc(min(f["z"], 40) / math.sqrt(2)))
        rec = {"tt": f["tt"], "tt_sd": f["tt_sd"], "cao": f["A"], "cao_sd": f["A_sd"], "fwhm": f["fwhm"], "fwhm_sd": f["fwhm_sd"],
               "eta": f["eta"], "dien_tich": dien_tich_pv(f["A"], f["fwhm"], f["eta"]), "z": f["z"], "snr_fit": snr_fit,
               "snr": f["A"] / max(sigma_raw * he_so, 1e-9), "p_gia": p_gia, "d": d, "nghi_van": [], "co_ka2": bool(lam2)}
        if ly:
            rec["ly_do_loai"] = ly
            bi_loai.append(rec)
        else:
            peaks.append(rec)
    return {"peaks": peaks, "bi_loai": bi_loai, "nen": nen, "ys": ys, "z": z, "sigma_raw": sigma_raw, "sigma_s": sigma_raw * he_so,
            "fwhm_may": inst, "buoc": buoc, "k_snr": k_snr, "nguon": nguon, "ghi": []}


def nh_d(tt, lam):
    s = lam / (2.0 * math.sin(math.radians(tt / 2.0)))
    return float(s)


# ====================== XÁC ĐỊNH PHA ======================
def _hkl_so(hkl):
    t = re.findall(r"-?\d", str(hkl))
    if len(t) >= 3:
        return tuple(int(v) for v in t[:3])
    return None


_CACHE_VACH = {}


def vach_cua(pha, lam, tt_min, tt_max, i_min=1.0):
    key = (pha["ten"], round(lam, 5), round(tt_min), round(tt_max), i_min, pha.get("nguon"), len(pha.get("atoms", [])), len(pha.get("vach", [])))
    if key not in _CACHE_VACH:
        _CACHE_VACH[key] = nh.vach_pha(pha, lam, tt_min - 1, tt_max + 1, i_min=i_min)
    return _CACHE_VACH[key]


def tol_dinh(p, dung_sai):
    """Dung sai ghép vạch cho một đỉnh: rộng hơn khi đỉnh rộng (tâm đỉnh rộng kém chính xác)."""
    return max(dung_sai, 0.25 * p["fwhm"], 3.0 * (p["tt_sd"] or 0.0))


def uoc_luong_dich(peaks, phases, lam, tt_min, tt_max, dung_sai=0.15):
    """Độ lệch 2θ toàn cục (do dịch mẫu/zero) từ các đỉnh RẤT mạnh khớp với pha tốt nhất; trả về (dich, sai_so, ten_pha, so_dinh)."""
    manh = [p for p in peaks if p["z"] >= 50]
    if not manh:
        return 0.0, 0.0, None, 0
    tot = None
    for ph in phases:
        refs = [v for v in vach_cua(ph, lam, tt_min, tt_max, 5.0)]
        cap = []
        for p in manh:
            c = min(refs, key=lambda v: abs(v["tt"] - p["tt"]), default=None)
            if c is not None and abs(c["tt"] - p["tt"]) <= 0.4:
                cap.append((p, c))
        if not cap:
            continue
        diem = sum(c["I"] for _, c in cap) - 20 * sum(abs(p["tt"] - c["tt"]) for p, c in cap)
        if tot is None or diem > tot[0]:
            tot = (diem, ph, cap)
    if tot is None:
        return 0.0, 0.0, None, 0
    d = np.array([p["tt"] - c["tt"] for p, c in tot[2]])
    w = np.array([max(p["tt_sd"], 0.003) ** -2 for p, _ in tot[2]])
    dich = float(np.sum(d * w) / np.sum(w))
    sd = float(np.std(d, ddof=1)) if len(d) > 1 else 0.02
    return max(-0.4, min(0.4, dich)), sd, tot[1]["ten"], len(d)


def so_khop_pha(pha, peaks, lam, tt_min, tt_max, dich, dung_sai, sigma_raw, buoc, inst, k_snr):
    """Đối chiếu một pha với danh sách đỉnh (đã trừ độ lệch). Trả về dict bằng chứng."""
    refs = vach_cua(pha, lam, tt_min + 0.5, tt_max - 0.2, 1.0)
    obs = [dict(p, tt_c=p["tt"] - dich) for p in peaks]
    cap = []
    for i, p in enumerate(obs):
        for j, r in enumerate(refs):
            dd = p["tt_c"] - r["tt"]
            if abs(dd) <= tol_dinh(p, dung_sai):
                cap.append((abs(dd) / tol_dinh(p, dung_sai), i, j, dd))
    cap.sort()
    da_i, da_j, ghep = set(), set(), []
    for _, i, j, dd in cap:
        if i in da_i or j in da_j:
            continue
        da_i.add(i)
        da_j.add(j)
        ghep.append({"obs": obs[i], "ref": refs[j], "dd": dd})
    ghep.sort(key=lambda g: g["ref"]["tt"])
    # thang cường độ theo diện tích: bình phương tối thiểu trên các vạch khớp
    if ghep:
        s_area = sum(g["obs"]["dien_tich"] * g["ref"]["I"] for g in ghep) / sum(g["ref"]["I"] ** 2 for g in ghep)
        w_tb = float(np.mean([g["obs"]["fwhm"] for g in ghep]))
    else:
        s_area, w_tb = 0.0, inst
    manh = [p for p in obs if p["z"] >= 50]
    thieu, che, duoi_nguong = [], [], []
    for j, r in enumerate(refs):
        if j in da_j:
            continue
        w = max(w_tb, inst)
        h_exp = s_area * r["I"] / dien_tich_pv(1.0, w, 0.5)
        h_lim = 2.0 * k_snr * sigma_raw / math.sqrt(0.753 * w / buoc)         # hệ số 2: nhiễu màu / sai khác dạng đỉnh
        bi_che = any(abs(r["tt"] - p["tt_c"]) < 2.5 * p["fwhm"] for p in manh)
        if bi_che:
            che.append({"ref": r, "h_exp": h_exp})
        elif 0.4 * h_exp > h_lim:                                             # cho phép lệch cường độ 2.5 lần (cấu trúc ưu tiên)
            thieu.append({"ref": r, "h_exp": h_exp, "h_lim": h_lim})
        else:
            duoi_nguong.append({"ref": r, "h_exp": h_exp, "h_lim": h_lim})
    n_obs = max(len(obs), 1)
    span = max(tt_max - tt_min, 1.0)
    tol_tb = float(np.mean([tol_dinh(g["obs"], dung_sai) for g in ghep])) if ghep else dung_sai
    p1 = min(0.95, n_obs * 2.0 * tol_tb / span)
    n_l = len(ghep) + len(thieu)
    p_ngau_nhien = 1.0
    if ghep:
        k = len(ghep)
        p_ngau_nhien = sum(math.comb(n_l, i) * p1 ** i * (1 - p1) ** (n_l - i) for i in range(k, n_l + 1))
    I_khop = sum(g["ref"]["I"] for g in ghep)
    I_can = I_khop + sum(t["ref"]["I"] for t in thieu)
    phu = I_khop / I_can if I_can > 0 else 0.0
    ten_manh = max(refs, key=lambda r: r["I"]) if refs else None
    manh_nhat_khop = any(ten_manh is g["ref"] for g in ghep) if ten_manh else False
    # mức tin cậy
    nm, nt = len(ghep), len(thieu)
    if nm == 0:
        muc = "khong"
    elif nt == 0 and nm >= 3 and p_ngau_nhien < 1e-3:
        muc = "chac"
    elif nt == 0 and nm >= 2 and p_ngau_nhien < 0.05:
        muc = "cao"
    elif nt == 0 and nm >= 2:
        muc = "cao"
    elif nt == 0 and nm == 1:
        muc = "yeu"                                          # chỉ 1 vạch, các vạch còn lại dưới giới hạn phát hiện
    elif nt >= 1 and nm >= 3 and phu >= 0.7:
        muc = "cao"
    elif nt >= 1 and nm >= 1 and p_ngau_nhien < 0.01 and phu >= 0.5:
        muc = "yeu_thieu"
    else:
        muc = "khong"
    kq = {"pha": pha, "ghep": ghep, "thieu": thieu, "che": che, "duoi_nguong": duoi_nguong, "phu": phu, "p_ngau_nhien": p_ngau_nhien,
          "muc": muc, "so_khop": nm, "so_thieu": nt, "dd_rms": float(np.sqrt(np.mean([g["dd"] ** 2 for g in ghep]))) if ghep else 0.0,
          "thang_dt": s_area, "refs": refs, "manh_nhat_khop": manh_nhat_khop}
    kq["hang_so_mang"] = tinh_hang_so_mang(pha, ghep, lam) if ghep else None
    kq["kich_thuoc"] = kich_thuoc_hat(ghep, inst, lam)
    return kq


def tinh_hang_so_mang(pha, ghep, lam):
    """Hằng số mạng từ các đỉnh khớp (bình phương tối thiểu theo 1/d²): lập phương, lục phương/tam phương, tứ phương."""
    if not pha.get("cell"):
        return None
    c = pha["cell"]
    pts = []
    for g in ghep:
        hkl = _hkl_so(g["ref"]["hkl"])
        if hkl is None:
            continue
        d = lam / (2.0 * math.sin(math.radians(g["obs"]["tt_c"] / 2.0)))
        sd_tt = max(g["obs"]["tt_sd"] or 0.0, 0.003)
        sd_d = d / math.tan(math.radians(g["obs"]["tt_c"] / 2.0)) * math.radians(sd_tt / 2.0)
        pts.append((hkl, d, sd_d))
    if not pts:
        return None
    ra, rc = c["a"], c["c"]
    kq = {}
    if abs(c["a"] - c["b"]) < 1e-6 and abs(c["a"] - c["c"]) < 1e-6 and c["alpha"] == c["beta"] == c["gamma"] == 90:
        va = np.array([d * math.sqrt(h * h + k * k + l * l) for (h, k, l), d, _ in pts])
        w = np.array([1.0 / max(sd, 1e-5) ** 2 for _, _, sd in pts])
        a = float(np.sum(va * w) / np.sum(w))
        sd = float(np.sqrt(np.sum(w * (va - a) ** 2) / np.sum(w) / max(len(va) - 1, 1))) if len(va) > 1 else float(1 / math.sqrt(np.sum(w)))
        kq = {"a": a, "a_sd": max(sd, 1 / math.sqrt(np.sum(w))), "a_ref": ra, "tham_so": ["a"]}
    elif c["gamma"] == 120 or (abs(c["a"] - c["b"]) < 1e-6 and 90 == c["alpha"] == c["beta"] and c["gamma"] == 90):
        hex_ = c["gamma"] == 120
        A = np.array([[(h * h + h * k + k * k) * (4 / 3 if hex_ else 1.0) if hex_ else (h * h + k * k), l * l] for (h, k, l), _, _ in pts], float)
        yv = np.array([1.0 / d ** 2 for _, d, _ in pts])
        sw = np.array([1.0 / (2 * d ** -3 * sd) for _, d, sd in pts])           # sai số của 1/d²
        if np.linalg.matrix_rank(A) >= 2:
            sol, *_ = np.linalg.lstsq(A / sw[:, None] * np.sqrt(1), yv / sw, rcond=None)
            a = 1.0 / math.sqrt(sol[0]) if sol[0] > 0 else None
            cc = 1.0 / math.sqrt(sol[1]) if sol[1] > 0 else None
            if a and cc:
                kq = {"a": a, "c": cc, "a_ref": ra, "c_ref": rc, "tham_so": ["a", "c"]}
        elif np.linalg.matrix_rank(A[:, :1]) >= 1 and np.all(A[:, 1] == 0):
            sol = float(np.sum(A[:, 0] * yv) / np.sum(A[:, 0] ** 2))
            kq = {"a": 1.0 / math.sqrt(sol), "a_ref": ra, "tham_so": ["a"]}
    return kq or None


def kich_thuoc_hat(ghep, inst, lam, K=0.9):
    """Kích thước tinh thể theo Scherrer từ các vạch khớp (đã trừ giãn rộng của máy). Trả về list dict và giá trị trung bình."""
    kq = []
    for g in ghep:
        w = g["obs"]["fwhm"]
        tt = g["obs"]["tt_c"]
        if w <= 1.15 * inst:
            kq.append({"tt": tt, "D": None, "ghi": "độ rộng ≈ giới hạn máy: tinh thể lớn (> ~100 nm), Scherrer không xác định"})
            continue
        beta = math.radians(math.sqrt(w * w - inst * inst))
        D = K * lam / (beta * math.cos(math.radians(tt / 2.0))) / 10.0
        kq.append({"tt": tt, "D": D, "ghi": ""})
    ok = [k["D"] for k in kq if k["D"]]
    return {"cac": kq, "tb": float(np.mean(ok)) if ok else None}


def tan_so_phu(peaks, lam1, nguon_ten):
    """Vị trí 2θ của bức xạ phụ (Kβ, W Lα1) của các đỉnh mạnh: dùng để nhận diện 'đỉnh giả' do ống phát tia."""
    _, _, lam_b = nh.NGUON[nguon_ten]
    kq = []
    for p in peaks:
        if p["z"] < 100:
            continue
        for ten, lam in (("Kβ", lam_b), ("W Lα1", nh.W_LA1)):
            if lam >= lam1:
                continue
            s = (lam / lam1) * math.sin(math.radians(p["tt"] / 2.0))
            if s < 1:
                kq.append({"cha": p, "loai": ten, "tt": 2 * math.degrees(math.asin(s)), "ti_le_max": 0.25 if ten == "Kβ" else 0.05})
    return kq


def phan_tich_mau(mau, pha_ung_vien, nguon=NGUON_MAC_DINH, k_snr=5.0, dung_sai=0.15, dich=None, fwhm_may=None, kalpha2=True,
                  tat_ca_pha=None):
    """Toàn bộ quy trình cho một mẫu: tìm đỉnh -> độ lệch 2θ -> đối chiếu ngân hàng -> gán từng đỉnh (pha / đế / bức xạ phụ / lạ)."""
    x, y = mau["x"], mau["y"]
    kd = tim_dinh(x, y, nguon, k_snr, fwhm_may, kalpha2)
    lam1 = nh.NGUON[nguon][0]
    peaks = kd["peaks"]
    tt_min, tt_max = float(x.min()), float(x.max())
    if dich is None:
        dich_v, dich_sd, pha_dich, n_dich = uoc_luong_dich(peaks, pha_ung_vien, lam1, tt_min, tt_max, dung_sai)
    else:
        dich_v, dich_sd, pha_dich, n_dich = float(dich), 0.0, None, 0
    sigma_raw, buoc, inst = kd["sigma_raw"], kd["buoc"], kd["fwhm_may"]
    pha_kq = [so_khop_pha(ph, peaks, lam1, tt_min, tt_max, dich_v, dung_sai, sigma_raw, buoc, inst, k_snr) for ph in pha_ung_vien]
    pha_kq.sort(key=lambda r: ({"chac": 0, "cao": 1, "yeu": 2, "yeu_thieu": 3, "khong": 4}[r["muc"]], -r["so_khop"]))
    chap_nhan = [r for r in pha_kq if r["muc"] in ("chac", "cao")]
    goi_y = [r for r in pha_kq if r["muc"] in ("yeu", "yeu_thieu")]
    vf = tan_so_phu(peaks, lam1, nguon)
    gan = []
    for p in peaks:
        pc = p["tt"] - dich_v
        tol = tol_dinh(p, dung_sai)
        ung = []
        for loai, ds in (("pha", chap_nhan), ("goi_y", goi_y)):
            for r in ds:
                for g in r["ghep"]:
                    if g["obs"] is not None and abs(g["obs"]["tt"] - p["tt"]) < 1e-9:
                        ung.append((loai, r, g))
        rec = {"peak": p, "tt_c": pc, "loai": None, "nhan": "", "chi_tiet": "", "trung": []}
        if ung:
            ung.sort(key=lambda t: (0 if t[0] == "pha" else 1, {"chac": 0, "cao": 1}.get(t[1]["muc"], 2), abs(t[2]["dd"])))
            loai, r, g = ung[0]
            rec.update(loai=loai, nhan=f"{r['pha']['ten']} {g['ref']['hkl']}", pha=r, ghep=g)
            # đỉnh có thể trùng với pha khác nằm trong dung sai (nhưng không được ghép)
            for r2 in pha_kq:
                if r2 is r or r2["muc"] == "khong" and not r2["refs"]:
                    continue
                for v in r2["refs"]:
                    if abs(v["tt"] - pc) <= tol and v["I"] >= 20:
                        rec["trung"].append(f"{r2['pha']['ten']} {v['hkl']}")
        else:
            sat = None
            for s in vf:
                if abs(s["tt"] - pc) < max(0.12, 0.5 * p["fwhm"]) and s["cha"] is not p and p["cao"] <= s["ti_le_max"] * s["cha"]["cao"] * 1.5:
                    sat = s
                    break
            if sat:
                rec.update(loai="bucxa", nhan=f"có thể là bức xạ {sat['loai']} của đỉnh {sat['cha']['tt']:.2f}°", sat=sat)
            else:
                rec.update(loai="la", nhan="chưa xác định chắc (không đủ vạch để kết luận)")
                # ứng viên gần nhất trong toàn ngân hàng (kể cả pha ngoài danh sách nguyên tố)
                cand = []
                for ph in (tat_ca_pha or pha_ung_vien):
                    for v in vach_cua(ph, lam1, tt_min, tt_max, 5.0):
                        if abs(v["tt"] - pc) <= max(0.35, tol):
                            cand.append((abs(v["tt"] - pc), f"{ph['ten']} {v['hkl']} ({v['tt']:.2f}°, I={v['I']:.0f}%)"))
                cand.sort()
                rec["ung_vien_gan"] = [c[1] for c in cand[:4]]
        gan.append(rec)
    return {"mau": mau, "dinh": kd, "dich": dich_v, "dich_sd": dich_sd, "dich_pha": pha_dich, "dich_n": n_dich, "pha": pha_kq,
            "chap_nhan": chap_nhan, "goi_y": goi_y, "gan": gan, "nguon": nguon, "lam": lam1, "dung_sai": dung_sai, "k_snr": k_snr,
            "tt_min": tt_min, "tt_max": tt_max}


# ====================== SO SÁNH CÁC MẪU ======================
def so_sanh(kq_cac_mau, ten_chuan=None, dung_sai=0.15):
    """So sánh từng mẫu với mẫu chuẩn (thường là đế trần NF). Đỉnh không có ở chuẩn => 'đỉnh mới/lạ' (hoặc pha mới được gán)."""
    if not kq_cac_mau:
        return None
    chuan = None
    for r in kq_cac_mau:
        if ten_chuan and r["mau"]["ten"] == ten_chuan:
            chuan = r
    if chuan is None:
        chuan = min(kq_cac_mau, key=lambda r: len(r["dinh"]["peaks"]))
    cp = [dict(g["peak"], tt_c=g["tt_c"]) for g in chuan["gan"]]
    ket = []
    for r in kq_cac_mau:
        if r is chuan:
            continue
        chung, moi, mat = [], [], []
        da = set()
        for g in r["gan"]:
            p = g["peak"]
            tol = max(dung_sai, 0.5 * p["fwhm"])
            k = None
            for i, q in enumerate(cp):
                if abs(q["tt_c"] - g["tt_c"]) <= tol and i not in da:
                    k = i
                    break
            if k is None:
                moi.append(g)
            else:
                da.add(k)
                q = cp[k]
                chung.append({"g": g, "ref": q, "ti_le": p["cao"] / q["cao"] if q["cao"] > 0 else None,
                              "dd": g["tt_c"] - q["tt_c"]})
        for i, q in enumerate(cp):
            if i not in da:
                mat.append(q)
        ket.append({"mau": r["mau"]["ten"], "kq": r, "chung": chung, "moi": moi, "mat": mat})
    return {"chuan": chuan["mau"]["ten"], "cac": ket}


# ====================== BÁO CÁO DỄ HIỂU ======================
_MUC_TXT = {"chac": "RẤT CHẮC CHẮN", "cao": "CHẮC CHẮN", "yeu": "CHƯA ĐỦ BẰNG CHỨNG", "yeu_thieu": "GỢI Ý YẾU", "khong": "không có"}


def _vai_tro(ten):
    t = ten.lower()
    if t.startswith("ni (") or t == "ni":
        return "đế Ni foam (nền)"
    return "pha trên mẫu"


def bao_cao_mau(r, ten_de="Ni"):
    L = []
    m = r["mau"]
    peaks = r["dinh"]["peaks"]
    L.append(f"=== MẪU {m['ten']} ===")
    L.append(f"TÓM TẮT: tìm thấy {len(peaks)} đỉnh nhiễu xạ thật (cao hơn nhiễu ≥ {r['k_snr']:.0f} lần và có độ rộng hợp lý).")
    for g in r["gan"]:
        p = g["peak"]
        if g["loai"] == "pha":
            ro = "đế" if g["pha"]["pha"]["ten"].startswith("Ni (") else "mẫu"
            L.append(f"  • {p['tt']:.2f}° → {g['nhan']}  [{ro}; {_MUC_TXT[g['pha']['muc']].lower()}]")
        elif g["loai"] == "goi_y":
            L.append(f"  • {p['tt']:.2f}° → có thể là {g['nhan']}  [gợi ý, cần thêm bằng chứng]")
        elif g["loai"] == "bucxa":
            L.append(f"  • {p['tt']:.2f}° → {g['nhan']}  [đỉnh giả do ống phát tia, không phải của mẫu]")
        else:
            gy = "; ".join(g.get("ung_vien_gan", [])) or "không có ứng viên gần trong ngân hàng"
            L.append(f"  • {p['tt']:.2f}° → ĐỈNH CHƯA XÁC ĐỊNH CHẮC. Ứng viên gần nhất: {gy}")
    L.append("")
    L.append("VÌ SAO KẾT QUẢ ĐÁNG TIN:")
    L.append(f"  1. Độ lệch vị trí 2θ chung của máy: {r['dich']:+.3f}° (ước từ đỉnh {r['dich_pha'] or 'mạnh nhất'}); đã trừ trước khi so với ngân hàng.")
    for q in r["chap_nhan"] + r["goi_y"]:
        ten = q["pha"]["ten"]
        tt = ", ".join(f"{g['obs']['tt']:.2f}°↔{g['ref']['hkl']} ({g['ref']['tt']:.2f}°)" for g in q["ghep"])
        L.append(f"  2. {ten}: khớp {q['so_khop']} vạch ({tt}); sai lệch trung bình bình phương {q['dd_rms']:.3f}°.")
        L.append(f"     Xác suất trùng ngẫu nhiên ≈ {q['p_ngau_nhien']:.1e} (càng nhỏ càng chắc). Mức: {_MUC_TXT[q['muc']]}.")
        if q["thieu"]:
            L.append("     Vạch đáng lẽ phải thấy nhưng KHÔNG thấy: " + ", ".join(f"{t['ref']['hkl']} {t['ref']['tt']:.1f}°" for t in q["thieu"]) + " → làm giảm độ tin cậy.")
        if q["duoi_nguong"] or q["che"]:
            L.append(f"     {len(q['duoi_nguong'])} vạch còn lại quá yếu so với nhiễu, {len(q['che'])} vạch bị đỉnh mạnh che: không dùng làm bằng chứng phản đối.")
        hs = q.get("hang_so_mang")
        if hs and hs.get("a"):
            s = f"     Hằng số mạng đo được a = {hs['a']:.4f} Å (chuẩn {hs['a_ref']:.4f} Å)"
            if hs.get("c"):
                s += f", c = {hs['c']:.4f} Å (chuẩn {hs['c_ref']:.4f} Å)"
            L.append(s + ".")
        kt = q.get("kich_thuoc") or {}
        if kt.get("tb"):
            L.append(f"     Kích thước tinh thể (Scherrer) ≈ {kt['tb']:.0f} nm.")
        elif kt.get("cac"):
            L.append("     Kích thước tinh thể: đỉnh hẹp gần giới hạn của máy → hạt lớn, không đo được bằng Scherrer.")
    khong = [q for q in r["pha"] if q["so_khop"] == 0 and q["pha"]["ten"] not in [x["pha"]["ten"] for x in r["chap_nhan"] + r["goi_y"]]]
    if khong:
        L.append("  3. Pha đã kiểm tra nhưng KHÔNG thấy: " + ", ".join(q["pha"]["ten"] for q in khong) + ".")
        L.append("     (Không thấy nghĩa là dưới giới hạn phát hiện hoặc vô định hình, chưa chắc là không có.)")
    return "\n".join(L)


def bao_cao_so_sanh(ss):
    if not ss:
        return ""
    L = [f"=== SO SÁNH VỚI MẪU CHUẨN: {ss['chuan']} ===", ""]
    for c in ss["cac"]:
        L.append(f"[{c['mau']}]")
        L.append(f"  Trùng với chuẩn: {len(c['chung'])} đỉnh; đỉnh MỚI so với chuẩn: {len(c['moi'])}; đỉnh chuẩn bị mất: {len(c['mat'])}.")
        for g in c["moi"]:
            L.append(f"   + MỚI {g['peak']['tt']:.2f}° → {g['nhan']}")
        for q in c["mat"]:
            L.append(f"   - mất {q['tt']:.2f}°")
        for x in c["chung"]:
            if x["ti_le"] and (x["ti_le"] > 1.5 or x["ti_le"] < 0.67):
                L.append(f"   ~ {x['g']['tt_c']:.2f}°: cường độ gấp {x['ti_le']:.2f} lần chuẩn")
        L.append("")
    return "\n".join(L)


# ====================== XUẤT KẾT QUẢ / VẼ ======================
MAU_MAU = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2"]
MAU_NHAN = {"pha": "#222222", "goi_y": "#777777", "bucxa": "#aa5500", "la": "#cc0000"}


KY_HIEU = [("*", "★", "#000000"), ("o", "●", "#1030e0"), ("s", "■", "#ff00ff"), ("D", "◆", "#f08c28"), ("^", "▲", "#00a050"),
           ("v", "▼", "#a020f0"), ("P", "✚", "#00a0c0"), ("X", "✖", "#8c564b")]


def pha_ngan(ten, ct=""):
    """Tên ngắn dùng trong chú giải: công thức (Ni, NiO, Cu2O...) nếu có, nếu không thì từ đầu của tên."""
    return (ct or str(ten).split(" (")[0].split()[0]).strip()


def ky_hieu_pha(cac_kq, ten_chuan=None):
    """Gán mỗi pha đã xác định (chắc chắn hoặc gợi ý) một ký hiệu + màu cố định cho mọi mẫu. Pha có trong mẫu chuẩn (đế) lấy dấu sao đen."""
    thu_tu = []
    chuan = next((r for r in cac_kq if r["mau"]["ten"] == ten_chuan), None) if ten_chuan else None
    if chuan is None and cac_kq:
        chuan = min(cac_kq, key=lambda r: len(r["dinh"]["peaks"]))
    for r in ([chuan] if chuan else []) + list(cac_kq):
        for g in r["gan"]:
            if g["loai"] in ("pha", "goi_y"):
                p = g["pha"]["pha"]
                if p["ten"] not in [t[0] for t in thu_tu]:
                    thu_tu.append((p["ten"], pha_ngan(p["ten"], p.get("cong_thuc", ""))))
    ra = {}
    for i, (ten, ngan) in enumerate(thu_tu):
        mk, gl, mau = KY_HIEU[i % len(KY_HIEU)]
        ra[ten] = {"mpl": mk, "glyph": gl, "mau": mau, "ngan": ngan}
    return ra


def nhan_hkl(g):
    m = re.findall(r"\([-\d ]+\)\s*$", g["nhan"]) if g["loai"] in ("pha", "goi_y") else []
    return m[0].replace(" ", "") if m else ""


def nhan_ngan(g):
    """Nhãn ngắn dạng chữ (dùng cho bảng/CSV): 'Ni(111)', 'NiO(200)?', '?' cho đỉnh lạ."""
    if g["loai"] in ("pha", "goi_y"):
        ten = g["nhan"].split(" (")[0].split()[0]
        return f"{ten}{nhan_hkl(g)}" + ("?" if g["loai"] == "goi_y" else "")
    if g["loai"] == "bucxa":
        return "Kβ/W"
    return "?"


def xep_chong(cac_kq, doi=1.35, chuan_hoa=True, mu=1.0):
    """Dữ liệu cho hình xếp chồng: [{ten, x, y_goc, y_xep, offset, mau}] (mẫu đầu nằm dưới cùng)."""
    ra = []
    for i, r in enumerate(cac_kq):
        m = r["mau"]
        y = np.asarray(m["y"], float)
        y = y - np.min(y)
        mx = float(np.max(y)) or 1.0
        yn = (y / mx) ** mu if chuan_hoa else y / mx
        ra.append({"ten": m["ten"], "x": np.asarray(m["x"], float), "y_goc": y, "y": yn + i * doi, "offset": i * doi,
                   "mau": MAU_MAU[i % len(MAU_MAU)], "mx": mx})
    return ra


def xuat_tat_ca(cac_kq, ss, thu_muc, ten="XRD", doi=1.35, mu=0.5, ve_nhan=True, x_min=None, x_max=None):
    """Ghi CSV (xếp chồng, bảng đỉnh), báo cáo .txt, JSON nhãn cho Origin và hình Matplotlib PNG/PDF. Trả về dict đường dẫn."""
    import csv
    import json
    os.makedirs(thu_muc, exist_ok=True)
    st = xep_chong(cac_kq, doi, True, mu)
    p = {}
    p["csv_xep"] = os.path.join(thu_muc, f"{ten}_xep.csv")
    n = max(len(s["x"]) for s in st)
    with open(p["csv_xep"], "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(sum(([f"2theta_{s['ten']}", s["ten"]] for s in st), []))
        for k in range(n):
            w.writerow(sum(([f"{s['x'][k]:.4f}", f"{s['y'][k]:.5f}"] if k < len(s["x"]) else ["", ""] for s in st), []))
    p["csv_dinh"] = os.path.join(thu_muc, f"{ten}_dinh.csv")
    with open(p["csv_dinh"], "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Mau", "2theta_do", "2theta_hieu_chinh", "d_A", "FWHM_do", "Cao", "Dien_tich", "z", "Loai", "Nhan"])
        for r in cac_kq:
            lam = r["lam"]
            for g in r["gan"]:
                q = g["peak"]
                d = lam / (2 * math.sin(math.radians(g["tt_c"] / 2)))
                w.writerow([r["mau"]["ten"], f"{q['tt']:.3f}", f"{g['tt_c']:.3f}", f"{d:.4f}", f"{q['fwhm']:.3f}", f"{q['cao']:.1f}",
                            f"{q['dien_tich']:.1f}", f"{q['z']:.1f}", g["loai"], g["nhan"]])
    txt = "\n\n".join(bao_cao_mau(r) for r in cac_kq)
    if ss:
        txt += "\n\n" + bao_cao_so_sanh(ss)
    p["bao_cao"] = os.path.join(thu_muc, f"{ten}_bao_cao.txt")
    with open(p["bao_cao"], "w", encoding="utf-8") as fh:
        fh.write(txt)
    nh_ = []
    kyh = ky_hieu_pha(cac_kq, ss["chuan"] if ss else None)
    for s, r in zip(st, cac_kq):
        for g in r["gan"]:
            q = g["peak"]
            iy = int(np.argmin(np.abs(s["x"] - q["tt"])))
            kh = kyh.get(g["pha"]["pha"]["ten"]) if g["loai"] in ("pha", "goi_y") else None
            nh_.append({"mau": s["ten"], "x": q["tt"], "y": float(s["y"][iy]), "nhan": nhan_ngan(g), "loai": g["loai"], "hkl": nhan_hkl(g),
                        "mpl": kh["mpl"] if kh else "", "glyph": kh["glyph"] if kh else "", "mau_kh": kh["mau"] if kh else "#cc0000"})
    lo = x_min if x_min is not None else float(min(s["x"].min() for s in st))
    hi = x_max if x_max is not None else float(max(s["x"].max() for s in st))
    p["json"] = os.path.join(thu_muc, f"{ten}_nhan.json")
    with open(p["json"], "w", encoding="utf-8") as fh:
        json.dump({"mau": [{"ten": s["ten"], "mau": s["mau"], "offset": s["offset"]} for s in st], "nhan": nh_, "x_min": lo, "x_max": hi,
                   "doi": doi, "ve_nhan": bool(ve_nhan),
                   "chu_giai": [{"ten": v["ngan"], "glyph": v["glyph"], "mpl": v["mpl"], "mau": v["mau"]} for v in kyh.values()]}, fh, ensure_ascii=False, indent=1)
    p.update(ve_matplotlib(st, nh_, thu_muc, ten, lo, hi, doi, ve_nhan, [{'ten': v['ngan'], 'mpl': v['mpl'], 'mau': v['mau']} for v in kyh.values()]))
    return p


def ve_nhan_mpl(ax, nhan, chu_giai=None, lo=0, hi=1, top=1):
    """Ký hiệu pha kiểu bài báo: dấu (sao, tròn, vuông, thoi...) cùng màu trên đỉnh + (hkl) bên cạnh; chú giải ở góc trên trái."""
    for n in nhan:
        if n["loai"] in ("pha", "goi_y"):
            ax.plot([n["x"]], [n["y"] + 0.07], marker=n["mpl"], color=n["mau_kh"], ms=11 if n["mpl"] == "*" else 7, ls="none",
                    markeredgecolor=n["mau_kh"], clip_on=False)
            ax.annotate(n["hkl"] + ("?" if n["loai"] == "goi_y" else ""), (n["x"], n["y"] + 0.07), xytext=(6, -2), textcoords="offset points",
                        fontsize=7, fontweight="bold", color=n["mau_kh"], ha="left", va="center")
        elif n["loai"] == "la":
            ax.annotate("?", (n["x"], n["y"]), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, color="#cc0000", fontweight="bold")
    for i, c in enumerate(chu_giai or []):
        y = top - 0.12 - 0.17 * i
        ax.plot([lo + 0.03 * (hi - lo)], [y], marker=c["mpl"], color=c["mau"], ms=9 if c["mpl"] == "*" else 6, ls="none")
        ax.text(lo + 0.06 * (hi - lo), y, c["ten"], fontsize=9, fontweight="bold", color="#222222", va="center")


def ve_matplotlib(st, nhan, thu_muc, ten, lo, hi, doi, ve_nhan=True, chu_giai=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.2, 1.5 + 1.1 * len(st)))
    for s in st:
        ax.plot(s["x"], s["y"], color=s["mau"], lw=1.2)
        ax.text(lo + 0.01 * (hi - lo), s["offset"] + 0.18, s["ten"], color=s["mau"], fontsize=11, fontweight="bold", va="bottom")
    if ve_nhan:
        ve_nhan_mpl(ax, nhan, chu_giai, lo, hi, st[-1]["offset"] + 1.45)
    ax.set_xlim(lo, hi)
    ax.set_ylim(-0.05, st[-1]["offset"] + 1.45)
    ax.set_yticks([])
    ax.set_xlabel("2θ (degree)", fontsize=12, fontweight="bold")
    for sp in ax.spines.values():
        sp.set_linewidth(1.6)
    ax.tick_params(width=1.6, labelsize=10)
    for t in ax.get_xticklabels():
        t.set_fontweight("bold")
    fig.tight_layout()
    ra = {"png": os.path.join(thu_muc, f"{ten}_mpl.png"), "pdf": os.path.join(thu_muc, f"{ten}_mpl.pdf")}
    fig.savefig(ra["png"], dpi=300)
    fig.savefig(ra["pdf"])
    plt.close(fig)
    return ra
