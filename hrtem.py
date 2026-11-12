# -*- coding: utf-8 -*-
"""Đo khoảng cách mặt mạng (d) từ ảnh HR-TEM: FFT -> tìm đốm -> lọc ngược -> profile vuông góc vân.

Thay cho chuỗi thao tác ImageJ (Set Scale, Duplicate, FFT, Fill, Inverse FFT, Plot Profile, chia tay).
Chỉ dùng numpy (+ PIL để đọc ảnh, matplotlib để vẽ), không cần scipy.

Quy ước: ảnh gốc là mảng float (hàng = y hướng xuống, cột = x). Vùng đo (ROI) là hình vuông n x n px.
d tính bằng nm = (kích thước FFT đệm) * nm_px / (bán kính đốm tính bằng px FFT đệm).
"""
import math
import os
import re
import csv
import numpy as np

# ====================== ĐỌC ẢNH & THANG ======================


def doc_anh(duong_dan):
    """Đọc ảnh (jpg/png/tif, 8 hoặc 16 bit) thành mảng float xám."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(duong_dan)
    if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
        a = np.asarray(im).astype(float)
    else:
        a = np.asarray(im.convert("L")).astype(float)
    if a.ndim != 2:
        raise ValueError("Ảnh không đọc được thành ảnh xám 2 chiều.")
    return a


def tim_thanh_thang(a, vung=0.15):
    """Tìm thanh thang (viền đen dài nằm ngang) ở vùng dưới ảnh. Trả về dict hoặc None.

    'px' là độ dài mép ngoài của viền đen. Viền thường dày vài px nên thanh thật có thể ngắn hơn một chút:
    người dùng nên kiểm tra bằng một mặt mạng đã biết (hàm hieu_chuan_theo_d)."""
    h, w = a.shape
    y0 = int(h * (1 - vung))
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        return None
    nguong = lo + 0.16 * (hi - lo)
    toi = a[y0:, : int(w * 0.7)] <= nguong
    tot = []
    for i in range(toi.shape[0]):
        hang = toi[i]
        dai = 0
        dau = 0
        for j, v in enumerate(np.append(hang, False)):
            if v:
                dai += 1
            else:
                if dai >= 40:
                    tot.append((dai, i + y0, j - dai, j - 1))
                dai = 0
    if not tot:
        return None
    # nhóm theo (x0, x1) gần giống nhau, chọn nhóm có độ dài lớn nhất và xuất hiện >= 3 hàng
    tot.sort(reverse=True)
    for dai, y, x0, x1 in tot:
        nhom = [t for t in tot if abs(t[2] - x0) <= 3 and abs(t[3] - x1) <= 3]
        if len(nhom) >= 3:
            return {"px": int(x1 - x0 + 1), "x0": int(x0), "x1": int(x1), "y": int(np.mean([t[1] for t in nhom]))}
    return None


# ====================== FFT ======================


def _lam_tron(a, sigma):
    """Làm trơn Gauss bằng FFT (biên tuần hoàn). Đủ cho phổ công suất."""
    ky = np.fft.fftfreq(a.shape[0])[:, None]
    kx = np.fft.rfftfreq(a.shape[1])[None, :]
    h = np.exp(-2 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * h, s=a.shape)


def cat_vung(a, cx, cy, n):
    """Cắt ROI vuông n x n tâm (cx, cy); dịch vào trong nếu chạm biên. Trả về (roi, x0, y0, n)."""
    n = int(max(32, min(n, min(a.shape))))
    n -= n % 2
    x0 = int(round(cx - n / 2))
    y0 = int(round(cy - n / 2))
    x0 = max(0, min(x0, a.shape[1] - n))
    y0 = max(0, min(y0, a.shape[0] - n))
    return a[y0:y0 + n, x0:x0 + n].copy(), x0, y0, n


def pho_cong_suat(roi, pad=4):
    """Phổ công suất (đã dịch DC ra giữa) của ROI, có cửa sổ Hann và đệm 0 lên pad lần."""
    n = roi.shape[0]
    t = roi - roi.mean()
    w = np.outer(np.hanning(n), np.hanning(n))
    m = n * pad
    f = np.fft.fftshift(np.fft.fft2(t * w, s=(m, m)))
    return np.abs(f) ** 2


def _parabol(ym, y0, yp):
    den = ym - 2 * y0 + yp
    if abs(den) < 1e-12:
        return 0.0
    return float(np.clip(0.5 * (ym - yp) / den, -1, 1))


def _pho_z(roi, pad):
    """Phổ log đã làm trơn và bản đồ độ nổi z (so với trung bình/độ lệch chuẩn của vòng cùng bán kính)."""
    n = roi.shape[0]
    m = n * pad
    ls = _lam_tron(np.log(pho_cong_suat(roi, pad) + 1e-12), pad * 0.6)
    c = m // 2
    yy, xx = np.indices((m, m))
    rr = np.hypot(xx - c, yy - c)
    rb = rr.astype(int).ravel()
    dem = np.bincount(rb)
    mu = np.bincount(rb, ls.ravel()) / np.maximum(dem, 1)
    s2 = np.bincount(rb, (ls ** 2).ravel()) / np.maximum(dem, 1) - mu ** 2
    sd = np.sqrt(np.maximum(s2, 1e-9))
    z = (ls - mu[rb].reshape(m, m)) / sd[rb].reshape(m, m)
    return ls, z, rr, yy, xx, m, c


def _dinh_tai(ls, z, y, x, m, c, nm_px):
    if 1 <= y < m - 1 and 1 <= x < m - 1:
        dy = _parabol(ls[y - 1, x], ls[y, x], ls[y + 1, x])
        dx = _parabol(ls[y, x - 1], ls[y, x], ls[y, x + 1])
    else:
        dy = dx = 0.0
    py, px = y + dy, x + dx
    r = math.hypot(px - c, py - c)
    theta = math.degrees(math.atan2(c - py, px - c)) % 180.0
    return {"d": m * nm_px / r, "theta": theta, "z": float(z[y, x]), "py": py, "px": px, "r_pad": r, "m": m}


def tim_dinh(roi, nm_px, d_min=0.15, d_max=0.45, so_dinh=8, z_min=3.0, pad=4):
    """Tìm các đốm nhiễu xạ trong FFT của ROI.

    Độ nổi z = (log công suất - trung bình vòng cùng bán kính) / độ lệch chuẩn vòng.
    Mỗi đốm chỉ tính một lần (nửa mặt phẳng, vì phổ đối xứng). Trả về list dict, mạnh nhất trước:
      d (nm), theta (độ, hướng vectơ sóng = pháp tuyến mặt mạng, 0..180), z, py, px (vị trí trong phổ đệm)."""
    ls, z, rr, yy, xx, m, c = _pho_z(roi, pad)
    with np.errstate(divide="ignore"):
        d = np.where(rr > 0, m * nm_px / np.maximum(rr, 1e-9), np.inf)
    ok = (d >= d_min) & (d <= d_max) & ((yy < c) | ((yy == c) & (xx > c)))
    zw = np.where(ok, z, -np.inf)
    kq = []
    rad = 3 * pad
    for _ in range(max(1, so_dinh) * 4):
        k = int(np.argmax(zw))
        zv = zw.flat[k]
        if not np.isfinite(zv) or zv < z_min:
            break
        y, x = divmod(k, m)
        zw[max(0, y - rad):y + rad + 1, max(0, x - rad):x + rad + 1] = -np.inf
        kq.append(_dinh_tai(ls, z, y, x, m, c, nm_px))
        if len(kq) >= so_dinh:
            break
    return kq


def dinh_thu_cong(roi, nm_px, py, px, pad=4, ban_kinh=6):
    """Đốm do người dùng bấm vào phổ (toạ độ px phổ đệm): lấy cực đại cục bộ gần nhất, đưa về nửa mặt phẳng trên."""
    ls, z, rr, yy, xx, m, c = _pho_z(roi, pad)
    y0, x0 = int(round(py)), int(round(px))
    if y0 > c or (y0 == c and x0 < c):
        y0, x0 = 2 * c - y0, 2 * c - x0
    y1, y2 = max(1, y0 - ban_kinh), min(m - 1, y0 + ban_kinh + 1)
    x1, x2 = max(1, x0 - ban_kinh), min(m - 1, x0 + ban_kinh + 1)
    sub = ls[y1:y2, x1:x2]
    j = np.unravel_index(int(np.argmax(sub)), sub.shape)
    y, x = y1 + j[0], x1 + j[1]
    if y > c or (y == c and x < c):
        y, x = 2 * c - y, 2 * c - x
    if math.hypot(x - c, y - c) < 3:
        return None
    return _dinh_tai(ls, z, y, x, m, c, nm_px)


def anh_pho(roi, pad=4, nua_rong=None):
    """Ảnh log phổ công suất (đã cắt quanh tâm) để hiển thị. nua_rong tính bằng px phổ đệm."""
    p = np.log(pho_cong_suat(roi, pad) + 1e-12)
    m = p.shape[0]
    c = m // 2
    if nua_rong:
        nua_rong = int(min(nua_rong, c - 1))
        p = p[c - nua_rong:c + nua_rong + 1, c - nua_rong:c + nua_rong + 1]
    return p


def loc_dinh(roi, dinh, pad=4, sigma_bin=1.2):
    """Ảnh vân thực (float, giữ dấu) chỉ chứa đốm 'dinh' và đốm đối xứng - thay cho Fill + Inverse FFT."""
    n = roi.shape[0]
    m = n * pad
    c = m // 2
    f = np.fft.fft2(roi - roi.mean(), s=(m, m))
    yy, xx = np.indices((m, m))
    s = sigma_bin * pad
    py, px = dinh["py"], dinh["px"]
    mask = (np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * s * s)) +
            np.exp(-((xx - (2 * c - px)) ** 2 + (yy - (2 * c - py)) ** 2) / (2 * s * s)))
    mask = np.fft.ifftshift(mask)
    return np.fft.ifft2(f * mask).real[:n, :n]


# ====================== PROFILE VUÔNG GÓC VÂN ======================


def _song_tuyen_tinh(a, x, y):
    h, w = a.shape
    x = np.clip(x, 0, w - 1.0001)
    y = np.clip(y, 0, h - 1.0001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = x - x0
    fy = y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) +
            a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def _gauss_1d(v, sigma):
    if sigma < 0.5:
        return v.copy()
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    vp = np.pad(v, r, mode="edge")
    return np.convolve(vp, k, mode="valid")


def do_profile(roi, nm_px, theta_deg, d_du_kien):
    """Profile trung bình dọc pháp tuyến của vân (theta = hướng vectơ sóng), đo d trực tiếp trên ảnh GỐC.

    Hai cách ước lượng độc lập với FFT 2D:
      - d_dinh : khoảng cách trung bình giữa các đỉnh liên tiếp (kèm độ lệch chuẩn, số vân);
      - d_fft1d: đỉnh FFT 1 chiều của profile (đệm 0 nhiều lần, nội suy parabol).
    Trả về dict (t_nm, giá trị đã trừ nền, vị trí đỉnh nm, ...)."""
    n = roi.shape[0]
    c = (n - 1) / 2.0
    th = math.radians(theta_deg)
    u = (math.cos(th), -math.sin(th))
    p = (math.sin(th), math.cos(th))
    t = np.arange(-0.35 * n, 0.35 * n + 1e-9, 1.0)
    s = np.arange(-0.25 * n, 0.25 * n + 1e-9, 1.0)
    X = c + t[:, None] * u[0] + s[None, :] * p[0]
    Y = c + t[:, None] * u[1] + s[None, :] * p[1]
    v = _song_tuyen_tinh(roi, X, Y).mean(axis=1)
    pt = phan_tich_chuoi(v, nm_px, d_du_kien)
    pt["t_nm"] = (t - t[0]) * nm_px
    return pt


def mau_song_tuyen(a, x, y):
    """Lấy mẫu nội suy song tuyến của ảnh a tại các toạ độ (x, y) (mảng)."""
    h, w = a.shape
    x = np.clip(np.asarray(x, dtype=float), 0, w - 1.001)
    y = np.clip(np.asarray(y, dtype=float), 0, h - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
            + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def uoc_luong_chu_ky(v, dx_nm, d_min=0.15, d_max=0.6, mac_dinh=0.25):
    """Ước lượng chu kỳ trội (nm) của profile v trong khoảng d_min..d_max bằng FFT 1D."""
    v = np.asarray(v, dtype=float)
    if len(v) < 16:
        return mac_dinh
    v = v - np.polyval(np.polyfit(np.arange(len(v)), v, 2), np.arange(len(v)))
    zp = 1 << int(math.ceil(math.log2(len(v) * 8)))
    sp = np.abs(np.fft.rfft(v * np.hanning(len(v)), zp)) ** 2
    d = dx_nm / np.maximum(np.fft.rfftfreq(zp), 1e-12)
    ok = (d >= d_min) & (d <= d_max)
    if not ok.any():
        return mac_dinh
    idx = np.nonzero(ok)[0]
    return float(d[idx[int(np.argmax(sp[idx]))]])


def phan_tich_chuoi(v, dx_nm, d_du_kien):
    """Đo chu kỳ của một chuỗi 1 chiều (profile) lấy mẫu cách nhau dx_nm.

    Dùng chung cho profile do app lấy và profile do ImageJ trả về.
      - d_dinh/d_sd/n_van: khoảng cách trung bình giữa các đỉnh liên tiếp (loại khoảng lệch > 25%), độ lệch chuẩn, số vân;
      - d_fft1d: đỉnh FFT 1 chiều (đệm 0 nhiều lần, nội suy parabol)."""
    v = np.asarray(v, dtype=float)
    chu_ky = max(3.0, d_du_kien / dx_nm)
    v = v - _gauss_1d(v, 1.5 * chu_ky)
    vs = _gauss_1d(v, chu_ky / 8.0)
    sd = float(np.std(vs)) or 1.0
    dinh = []
    min_kc = 0.6 * chu_ky
    for i in range(1, len(vs) - 1):
        if vs[i] > vs[i - 1] and vs[i] >= vs[i + 1] and vs[i] > 0.25 * sd:
            if dinh and i - dinh[-1][0] < min_kc:
                if vs[i] > vs[dinh[-1][0]]:
                    dinh[-1] = (i, vs[i])
                continue
            dinh.append((i, vs[i]))
    vt = []
    for i, _ in dinh:
        vt.append(i + _parabol(vs[i - 1], vs[i], vs[i + 1]))
    vt = np.array(vt, dtype=float)
    d_dinh = d_sd = None
    n_van = len(vt)
    if len(vt) >= 3:
        kc = np.diff(vt) * dx_nm
        med = float(np.median(kc))
        giu = kc[np.abs(kc - med) <= 0.25 * med]
        if len(giu) >= 2:
            d_dinh = float(giu.mean())
            d_sd = float(giu.std(ddof=1))
            n_van = len(giu) + 1
    w = np.hanning(len(v))
    zp = 1 << int(math.ceil(math.log2(len(v) * 32)))
    spec = np.abs(np.fft.rfft(v * w, zp)) ** 2
    f = np.fft.rfftfreq(zp)
    ok = (f >= 1 / (1.6 * chu_ky)) & (f <= 1 / (0.625 * chu_ky))
    d_f = None
    if ok.any():
        idx = np.nonzero(ok)[0]
        k = idx[int(np.argmax(spec[idx]))]
        if 1 <= k < len(spec) - 1:
            k = k + _parabol(np.log(spec[k - 1] + 1e-30), np.log(spec[k] + 1e-30), np.log(spec[k + 1] + 1e-30))
            d_f = float(dx_nm / (k / zp))
    return {"t_nm": np.arange(len(v)) * dx_nm, "v": v, "vs": vs, "dinh_nm": vt * dx_nm if len(vt) else vt,
            "d_dinh": d_dinh, "d_sd": d_sd, "n_van": int(n_van), "d_fft1d": d_f}


def do_mot_vung(a, cx, cy, n, nm_px, dinh, pad=4):
    """Đo đầy đủ một đốm của một vùng: trả về dict gồm d_fft, d_dinh ± sd, d_fft1d, lệch %, cảnh báo."""
    roi, x0, y0, n = cat_vung(a, cx, cy, n)
    pr = do_profile(roi, nm_px, dinh["theta"], dinh["d"])
    kq = {"x": x0 + n / 2.0, "y": y0 + n / 2.0, "n": n, "d_fft": dinh["d"], "theta": dinh["theta"], "z": dinh["z"],
          "d_dinh": pr["d_dinh"], "d_sd": pr["d_sd"], "n_van": pr["n_van"], "d_fft1d": pr["d_fft1d"], "profile": pr,
          "dinh": dict(dinh)}
    ref = pr["d_dinh"] or pr["d_fft1d"]
    kq["lech_pct"] = None if ref is None else 100.0 * (ref - dinh["d"]) / dinh["d"]
    canh = []
    if ref is None:
        canh.append("Không đo được khoảng cách đỉnh trên profile (ít hơn 3 vân rõ) - nên chọn vùng lớn hơn hoặc đốm khác.")
    elif abs(kq["lech_pct"]) > 3.0:
        canh.append(f"d từ FFT và d từ profile lệch {kq['lech_pct']:+.1f}% (> 3%): đốm có thể là nhiễu hoặc vân không thẳng.")
    if dinh["z"] < 3.5:
        canh.append(f"Đốm nổi yếu (z = {dinh['z']:.1f}σ) - kiểm tra lại có phải vân thật không.")
    if kq["n_van"] < 8:
        canh.append(f"Chỉ có {kq['n_van']} vân trong vùng đo - sai số lớn.")
    kq["canh_bao"] = canh
    return kq


def hieu_chuan_theo_d(nm_px, d_do, d_chuan):
    """Hệ số hiệu chuẩn thang khi biết chắc một mặt mạng: nm_px_moi = nm_px * d_chuan / d_do."""
    return nm_px * d_chuan / d_do


# ====================== CƠ SỞ DỮ LIỆU MẶT MẠNG ======================


def _lap_phuong(a, kieu, hkl_list):
    kq = []
    for h, k, l in hkl_list:
        kq.append((f"({h}{k}{l})", a / math.sqrt(h * h + k * k + l * l)))
    return kq


def _luc_giac(a, c, hkl_list):
    """Hệ lục giác: 1/d^2 = 4/3 (h^2 + hk + k^2)/a^2 + l^2/c^2."""
    kq = []
    for h, k, l in hkl_list:
        inv = 4.0 / 3.0 * (h * h + h * k + k * k) / (a * a) + l * l / (c * c)
        kq.append((f"({h}{k}{l})", 1.0 / math.sqrt(inv)))
    return kq


CHAT_CHUAN = {
    "Cu": _lap_phuong(0.3615, "fcc", [(1, 1, 1), (2, 0, 0), (2, 2, 0), (3, 1, 1)]),
    "Cu2O": _lap_phuong(0.4267, "cuprit", [(1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 1, 1), (2, 2, 0), (3, 1, 1)]),
    "Ni": _lap_phuong(0.3524, "fcc", [(1, 1, 1), (2, 0, 0), (2, 2, 0)]),
    "NiO": _lap_phuong(0.4177, "muoi", [(1, 1, 1), (2, 0, 0), (2, 2, 0)]),
    "Fe": _lap_phuong(0.2866, "bcc", [(1, 1, 0), (2, 0, 0), (2, 1, 1)]),
    "Fe3O4": _lap_phuong(0.8396, "spinel", [(2, 2, 0), (3, 1, 1), (4, 0, 0), (4, 2, 2), (5, 1, 1), (4, 4, 0)]),
    "Ni(OH)2": _luc_giac(0.3126, 0.4605, [(1, 0, 0), (1, 0, 1), (1, 0, 2), (1, 1, 0)]),
    "Fe2O3": _luc_giac(0.5035, 1.3747, [(0, 1, 2), (1, 0, 4), (1, 1, 0), (1, 1, 3), (0, 2, 4), (1, 1, 6)]),
    # CuO đơn tà - giá trị tham khảo (JCPDS), nên kiểm tra lại
    "CuO": [("(110)", 0.2752), ("(-111)", 0.2531), ("(002)", 0.2523), ("(111)", 0.2324), ("(-202)", 0.1868)],
}


def _tu_giac(a, c, hkl_list):
    """Hệ tứ phương: 1/d^2 = (h^2 + k^2)/a^2 + l^2/c^2."""
    return [(f"({h}{k}{l})", 1.0 / math.sqrt((h * h + k * k) / (a * a) + l * l / (c * c))) for h, k, l in hkl_list]


_FCC = [(1, 1, 1), (2, 0, 0), (2, 2, 0), (3, 1, 1)]
_BCC = [(1, 1, 0), (2, 0, 0), (2, 1, 1), (2, 2, 0)]
_HCP = [(1, 0, 0), (0, 0, 2), (1, 0, 1), (1, 0, 2), (1, 1, 0)]
_SPINEL = [(2, 2, 0), (3, 1, 1), (2, 2, 2), (4, 0, 0), (4, 2, 2), (5, 1, 1), (4, 4, 0)]
_MUOI = [(1, 1, 1), (2, 0, 0), (2, 2, 0), (3, 1, 1), (2, 2, 2)]
_CORUND = [(0, 1, 2), (1, 0, 4), (1, 1, 0), (1, 1, 3), (0, 2, 4), (1, 1, 6)]

# (tên, kiểu, tham số mạng nm, danh sách hkl, mô tả). Tham số mạng lấy theo dữ liệu tinh thể học phổ biến (JCPDS/ICDD);
# danh sách hkl chỉ gồm các mặt thường thấy trong HR-TEM (d >= ~0.1 nm). Tự kiểm tra lại khi viết bài.
_PHA_THEM = [
    ("Au", "cubic", (0.4078,), _FCC, "Au fcc"), ("Ag", "cubic", (0.4086,), _FCC, "Ag fcc"),
    ("Pt", "cubic", (0.3924,), _FCC, "Pt fcc"), ("Pd", "cubic", (0.3890,), _FCC, "Pd fcc"),
    ("Ir", "cubic", (0.3839,), _FCC, "Ir fcc"), ("Rh", "cubic", (0.3803,), _FCC, "Rh fcc"),
    ("Al", "cubic", (0.4050,), _FCC, "Al fcc"), ("Pb", "cubic", (0.4950,), _FCC, "Pb fcc"),
    ("Co (fcc)", "cubic", (0.3545,), _FCC, "β-Co fcc"), ("FeNi3", "cubic", (0.3555,), _FCC[:3], "Awaruite FeNi3 (gần đúng, phụ thuộc thành phần)"),
    ("Cr", "cubic", (0.2884,), _BCC, "Cr bcc"), ("Mo", "cubic", (0.3147,), _BCC, "Mo bcc"), ("W", "cubic", (0.3165,), _BCC, "W bcc"),
    ("V", "cubic", (0.3024,), _BCC, "V bcc"), ("Nb", "cubic", (0.3300,), _BCC, "Nb bcc"), ("Ta", "cubic", (0.3303,), _BCC, "Ta bcc"),
    ("Si", "cubic", (0.5431,), [(1, 1, 1), (2, 2, 0), (3, 1, 1)], "Si kim cương"),
    ("Ge", "cubic", (0.5658,), [(1, 1, 1), (2, 2, 0), (3, 1, 1)], "Ge kim cương"),
    ("Co (hcp)", "hex", (0.2507, 0.4069), _HCP, "α-Co lục giác"), ("Ti", "hex", (0.2951, 0.4684), _HCP, "Ti lục giác"),
    ("Zn", "hex", (0.2665, 0.4947), [(0, 0, 2), (1, 0, 0), (1, 0, 1), (1, 0, 2), (1, 0, 3), (1, 1, 0)], "Zn lục giác"),
    ("Mg", "hex", (0.3209, 0.5211), _HCP, "Mg lục giác"), ("Ru", "hex", (0.2706, 0.4282), _HCP, "Ru lục giác"),
    ("C (graphit)", "hex", (0.2464, 0.6711), [(0, 0, 2), (1, 0, 0), (1, 0, 1), (0, 0, 4), (1, 1, 0)], "Graphit"),
    ("Sn", "tet", (0.5831, 0.3182), [(2, 0, 0), (1, 0, 1), (2, 2, 0), (2, 1, 1)], "β-Sn tứ phương"),
    ("CoO", "cubic", (0.4260,), _MUOI[:3], "CoO muối ăn"), ("FeO", "cubic", (0.4302,), _MUOI[:3], "FeO wüstite (Fe1-xO)"),
    ("MnO", "cubic", (0.4445,), _MUOI[:3], "MnO muối ăn"), ("MgO", "cubic", (0.4212,), _MUOI[:4], "MgO muối ăn"),
    ("CeO2", "cubic", (0.5411,), _FCC, "CeO2 fluorit"),
    ("Co3O4", "cubic", (0.8084,), _SPINEL, "Co3O4 spinel"), ("NiFe2O4", "cubic", (0.8339,), _SPINEL, "NiFe2O4 spinel"),
    ("ZnO", "hex", (0.3250, 0.5207), [(1, 0, 0), (0, 0, 2), (1, 0, 1), (1, 0, 2), (1, 1, 0), (1, 0, 3), (1, 1, 2)], "ZnO wurtzit"),
    ("Al2O3", "hex", (0.4759, 1.2991), _CORUND, "α-Al2O3 corundum"), ("Cr2O3", "hex", (0.4959, 1.3594), _CORUND, "Cr2O3 eskolait"),
    ("Co(OH)2", "hex", (0.3186, 0.4653), [(0, 0, 1), (1, 0, 0), (1, 0, 1), (1, 0, 2), (1, 1, 0)], "β-Co(OH)2 brucit"),
    ("TiO2 anatase", "tet", (0.3785, 0.9514), [(1, 0, 1), (0, 0, 4), (2, 0, 0), (1, 0, 5), (2, 1, 1)], "TiO2 anatase"),
    ("TiO2 rutile", "tet", (0.4594, 0.2959), [(1, 1, 0), (1, 0, 1), (2, 0, 0), (1, 1, 1), (2, 1, 0), (2, 1, 1), (2, 2, 0)], "TiO2 rutile"),
    ("SnO2", "tet", (0.4738, 0.3187), [(1, 1, 0), (1, 0, 1), (2, 0, 0), (2, 1, 1), (2, 2, 0)], "SnO2 cassiterit"),
]


def _xay_them():
    kq, mo_ta = {}, {}
    for ten, kieu, tham, hkl, mt in _PHA_THEM:
        if kieu == "cubic":
            kq[ten] = _lap_phuong(tham[0], "", hkl)
            mo_ta[ten] = f"{mt}, a = {tham[0]} nm"
        elif kieu == "hex":
            kq[ten] = _luc_giac(tham[0], tham[1], hkl)
            mo_ta[ten] = f"{mt}, a = {tham[0]}, c = {tham[1]} nm"
        else:
            kq[ten] = _tu_giac(tham[0], tham[1], hkl)
            mo_ta[ten] = f"{mt}, a = {tham[0]}, c = {tham[1]} nm"
    return kq, mo_ta


_them, MO_TA_PHA = _xay_them()
CHAT_CHUAN.update(_them)
MO_TA_PHA.update({
    "Cu": "Cu fcc, a = 0.3615 nm", "Cu2O": "Cu2O cuprit, a = 0.4267 nm", "CuO": "CuO đơn tà (giá trị tham khảo)",
    "Ni": "Ni fcc, a = 0.3524 nm", "NiO": "NiO muối ăn, a = 0.4177 nm", "Ni(OH)2": "β-Ni(OH)2, a = 0.3126, c = 0.4605 nm",
    "Fe": "α-Fe bcc, a = 0.2866 nm", "Fe3O4": "Fe3O4 spinel, a = 0.8396 nm", "Fe2O3": "α-Fe2O3 hematit, a = 0.5035, c = 1.3747 nm"})
for _k in CHAT_CHUAN:
    MO_TA_PHA.setdefault(_k, _k)

NHOM_PHA = {
    "Mẫu Cu - Ni - Fe": ["Cu", "Cu2O", "CuO", "Ni", "NiO", "Ni(OH)2", "Fe", "Fe3O4", "Fe2O3", "FeNi3", "NiFe2O4", "Co3O4"],
    "Kim loại quý": ["Au", "Ag", "Pt", "Pd", "Ir", "Rh", "Ru"],
    "Kim loại chuyển tiếp": ["Cu", "Ni", "Co (fcc)", "Co (hcp)", "Fe", "Cr", "Mo", "W", "V", "Ti", "Zn", "Nb", "Ta"],
    "Oxit kim loại": ["Cu2O", "CuO", "NiO", "CoO", "FeO", "MnO", "MgO", "ZnO", "TiO2 anatase", "TiO2 rutile", "SnO2", "CeO2", "Al2O3",
                      "Cr2O3", "Fe2O3", "Fe3O4", "Co3O4", "NiFe2O4"],
    "Hiđroxit": ["Ni(OH)2", "Co(OH)2"],
}


_HKL_MAC_DINH = {"fcc": _FCC, "bcc": _BCC, "hcp": _HCP, "sc": [(1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 1, 0), (2, 1, 1)],
                 "tet": [(1, 0, 0), (1, 0, 1), (1, 1, 0), (0, 0, 2), (1, 1, 1), (2, 0, 0), (2, 1, 1), (2, 2, 0)]}


def doc_chat_tuy_chinh(van_ban):
    """Thêm pha riêng. Mỗi dòng một trong hai dạng (dấu phẩy thập phân được):
        Tên (hkl) = d_nm                      ví dụ  Mau X (101) = 0.3333
        Tên kiểu a=... [c=...]                ví dụ  Al fcc a=0.405   |   Zn hcp a=0.2665 c=0.4947
    kiểu: fcc, bcc, hcp, sc (lập phương đơn giản), tet (tứ phương). Dạng thứ hai tự sinh các mặt thường gặp (chưa lọc tắt tiêu)
    nên hãy kiểm tra lại. Trả về dict giống CHAT_CHUAN."""
    kq = {}
    so = r"([0-9]+[.,]?[0-9]*)"
    for dong in (van_ban or "").splitlines():
        m = re.match(r"\s*(.+?)\s+(fcc|bcc|hcp|sc|tet)\s+a\s*=\s*" + so + r"(?:\s+c\s*=\s*" + so + r")?\s*$", dong, re.I)
        if m:
            ten, kieu = m.group(1).strip(), m.group(2).lower()
            a = float(m.group(3).replace(",", "."))
            c = float(m.group(4).replace(",", ".")) if m.group(4) else None
            if kieu in ("hcp", "tet") and not c:
                continue
            if kieu == "hcp":
                kq.setdefault(ten, []).extend(_luc_giac(a, c, _HKL_MAC_DINH[kieu]))
            elif kieu == "tet":
                kq.setdefault(ten, []).extend(_tu_giac(a, c, _HKL_MAC_DINH[kieu]))
            else:
                kq.setdefault(ten, []).extend(_lap_phuong(a, "", _HKL_MAC_DINH[kieu]))
            continue
        m = re.match(r"\s*(.+?)\s*(\([^)]*\))\s*=\s*" + so, dong)
        if m:
            kq.setdefault(m.group(1), []).append((m.group(2), float(m.group(3).replace(",", "."))))
    return kq


def ghep_pha(d, dung_sai=0.03, tuy_chinh=None, chi_pha=None):
    """Các mặt chuẩn có |d_chuan - d| <= dung_sai * d_chuan. Trả về list (pha, hkl, d_chuan, lệch%) xếp theo |lệch|."""
    bang = dict(CHAT_CHUAN)
    for k, v in (tuy_chinh or {}).items():
        bang[k] = bang.get(k, []) + list(v)
    kq = []
    for pha, ds in bang.items():
        if chi_pha and pha not in chi_pha:
            continue
        for hkl, dc in ds:
            lech = 100.0 * (d - dc) / dc
            if abs(lech) <= dung_sai * 100:
                kq.append((pha, hkl, dc, lech))
    kq.sort(key=lambda t: abs(t[3]))
    return kq


# ====================== QUÉT TỰ ĐỘNG THEO THÀNH PHẦN ======================


def _chuan_ten(s):
    return re.sub(r"[\s_]+", "", s).lower()


def doc_thanh_phan(text, mac_dinh=2, tuy_chinh=None):
    """'Cu:3, NiO, Fe3O4:2' -> ({'Cu': 3, 'NiO': 2, 'Fe3O4': 2}, [tên không nhận ra]).
    Mỗi tên có thể kèm ':số' hoặc '=số' (số đốm cần tìm), không có thì dùng mac_dinh.
    Tên nhận không phân biệt hoa thường/dấu cách; 'Co' gồm cả Co (fcc) và Co (hcp), 'TiO2' gồm cả anatase và rutile.
    Pha thêm qua tuy_chinh (dict tên -> [(hkl, d)]) cũng được nhận."""
    bang = list(CHAT_CHUAN) + [k for k in (tuy_chinh or {}) if k not in CHAT_CHUAN]
    chuan = {_chuan_ten(k): k for k in bang}
    kq, la = {}, []
    for tok in re.split(r"[,;\n]+", text or ""):
        tok = tok.strip()
        if not tok:
            continue
        so = mac_dinh
        m = re.match(r"^(.*?)\s*[:=]\s*(\d+)\s*$", tok)
        if m:
            tok, so = m.group(1).strip(), int(m.group(2))
        t = _chuan_ten(tok)
        if t in chuan:
            ds = [chuan[t]]
        else:    # 'Co' -> 'Co (fcc)', 'Co (hcp)'; 'TiO2' -> 'TiO2 anatase', 'TiO2 rutile' (tên gốc có dấu cách sau tên nhập)
            ds = [k for k in bang if tok and re.match(r"^" + re.escape(tok) + r" ", k, re.I)]
        if not ds:
            la.append(tok)
            continue
        for k in ds:
            kq[k] = max(0, so)
    return kq, la


def quet_theo_thanh_phan(a, nm_px, thanh_phan, nm_vung=10.0, dung_sai=0.03, d_min=0.15, d_max=0.45, z_min=3.0,
                         tuy_chinh=None, pad_quet=2, buoc=0.5, tien_do=None, huy=None, pad=4):
    """Quét cả ảnh bằng cửa sổ trượt, tìm các vùng có vân khớp mặt mạng của các thành phần đã nhập.

    thanh_phan: dict tên pha -> số đốm muốn lấy (mỗi pha lấy tối đa số này, các vị trí cách nhau >= ~0,9 cỡ vùng và không trùng
    giữa các pha). Với mỗi vùng được chọn, đo lại d (FFT pad=4 + profile) như phép đo thủ công.
    Trả về (ds_phep_do, thong_ke) với thong_ke = {pha: {"can": k, "tim_duoc": j, "ung_vien": u}}.
    ds_phep_do: các dict cùng dạng do_mot_vung + {pha, hkl, d, d_chuan, lech_pct, diem}."""
    H, W = a.shape
    n = int(round(nm_vung / nm_px))
    n = max(32, min(n, H, W))
    buoc_px = max(8, int(n * buoc))
    cx_ds = list(range(n // 2, W - n // 2 + 1, buoc_px)) or [W // 2]
    cy_ds = list(range(n // 2, H - n // 2 + 1, buoc_px)) or [H // 2]
    chi = {k for k, v in thanh_phan.items() if v > 0}
    ung = []
    tong, xong = len(cx_ds) * len(cy_ds), 0
    for cy in cy_ds:
        for cx in cx_ds:
            if huy is not None and huy():
                return [], {k: {"can": v, "tim_duoc": 0, "ung_vien": 0} for k, v in thanh_phan.items()}
            xong += 1
            if tien_do is not None:
                tien_do(xong, tong)
            roi, x0, y0, nn = cat_vung(a, cx, cy, n)
            if float(np.std(roi)) < 1e-6:
                continue
            for p in tim_dinh(roi, nm_px, d_min, d_max, so_dinh=6, z_min=z_min, pad=pad_quet):
                ms = ghep_pha(p["d"], dung_sai, tuy_chinh, chi)
                if ms:
                    pha, hkl, dc, lech = ms[0]
                    diem = p["z"] * (1.0 - 0.5 * abs(lech) / (100.0 * dung_sai))
                    ung.append({"pha": pha, "hkl": hkl, "d_chuan": dc, "lech_pct": lech, "x": x0 + nn / 2.0, "y": y0 + nn / 2.0,
                                "n": nn, "d": p["d"], "theta": p["theta"], "z": p["z"], "diem": diem})
    ung.sort(key=lambda c: -c["diem"])
    chon, dem = [], {k: 0 for k in thanh_phan}
    for c in ung:
        if dem.get(c["pha"], 0) >= thanh_phan.get(c["pha"], 0):
            continue
        if any(math.hypot(c["x"] - o["x"], c["y"] - o["y"]) < 0.9 * n for o in chon):
            continue
        chon.append(c)
        dem[c["pha"]] += 1
    kq = []
    for c in chon:
        roi, x0, y0, nn = cat_vung(a, c["x"], c["y"], c["n"])
        ds = tim_dinh(roi, nm_px, d_min, d_max, so_dinh=10, z_min=min(z_min, 2.5), pad=pad)
        if not ds:
            continue
        p = min(ds, key=lambda q: abs(q["d"] - c["d"]) / c["d"] + abs(((q["theta"] - c["theta"]) + 90) % 180 - 90) / 20.0)
        if abs(p["d"] - c["d"]) / c["d"] > 0.05:
            continue
        r = do_mot_vung(a, c["x"], c["y"], nn, nm_px, p, pad)
        d_cuoi = r["d_dinh"] if r.get("d_dinh") else p["d"]
        lech = 100.0 * (d_cuoi - c["d_chuan"]) / c["d_chuan"]
        if abs(lech) > 100.0 * dung_sai:         # đo lại kỹ mà không còn khớp mặt chuẩn trong dung sai -> bỏ, không bịa nhãn
            continue
        if r.get("lech_pct") is not None and abs(r["lech_pct"]) > 3.0:   # d FFT và d profile không thống nhất (nhiễu / vùng giáp ranh)
            continue
        if r.get("d_sd") and r["d_sd"] / max(d_cuoi, 1e-9) > 0.06:        # khoảng cách giữa các vân dao động quá lớn (vùng giáp ranh hai miền)
            continue
        r.update({"pha": c["pha"], "hkl": c["hkl"], "d_chuan": c["d_chuan"], "lech_chuan_pct": lech, "z_quet": c["z"], "d": d_cuoi})
        kq.append(r)
    tk = {}
    for k, v in thanh_phan.items():
        tk[k] = {"can": v, "tim_duoc": sum(1 for r in kq if r["pha"] == k), "ung_vien": sum(1 for c in ung if c["pha"] == k)}
    return kq, tk


# ====================== NHÃN & VẼ ======================


def nhan_mathtext(pha, hkl):
    """'Cu2O', '(111)' -> 'Cu$_2$O $(111)$' (chỉ số dưới cho công thức, chỉ số Miller nghiêng, gạch trên cho âm)."""
    ct = re.sub(r"(\d+)", r"$_{\1}$", pha)
    inner = hkl.strip("()")
    inner = re.sub(r"-(\d)", r"\\bar{\1}", inner)
    return f"{ct} ${{({inner})}}$" if hkl else ct


def tach_nhan(nhan):
    """'Cu2O (111)' -> ('Cu2O', '(111)'); 'Ni(OH)2 (101)' -> ('Ni(OH)2', '(101)'); 'Co (hcp) (002)' -> ('Co (hcp)', '(002)').
    Chỉ coi cụm cuối dạng (số) là chỉ số Miller; nhãn không có thì hkl rỗng."""
    nhan = (nhan or "").strip()
    m = re.match(r"^(.*?)\s*(\(-?\d{3,4}\))$", nhan)
    if m and m.group(1):
        return m.group(1).strip(), m.group(2)
    return nhan, ""


def nhan_van_ban(pha, hkl):
    return f"{pha} {hkl}".strip()


BANG_MAU = ["#ffffff", "#ffd75e", "#9be29b", "#7fd6ff", "#ff9f9f", "#d9a7ff"]


def mau_theo_nhan(nhan, bang=None):
    bang = bang if bang is not None else {}
    if nhan not in bang:
        bang[nhan] = BANG_MAU[len(bang) % len(BANG_MAU)]
    return bang[nhan]


def ve_chu_thich(a, nm_px, do_ds, duong_dan, dpi=300, hien_vung=False, tieu_de=None):
    """Vẽ ảnh gốc + mũi tên/nhãn cho từng phép đo (giống hình thủ công). do_ds: list dict
    {x, y, n, d, theta, pha, hkl, mau, so_van(=1), lx, ly (tuỳ chọn, vị trí nhãn tính theo px ảnh)}."""
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    h, w = a.shape
    lo, hi = np.percentile(a, [0.5, 99.5])
    fig = plt.figure(figsize=(8, 8 * h / w))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(a, cmap="gray", vmin=lo, vmax=hi, interpolation="lanczos")
    ax.set_axis_off()
    ve_lop_phu(ax, a.shape, nm_px, do_ds, hien_vung=hien_vung, chu=max(7, 9))
    if tieu_de:
        ax.set_title(tieu_de, fontsize=8)
    fig.savefig(duong_dan, dpi=dpi)
    plt.close(fig)
    return duong_dan


def bo_tri_nhan(do_ds, shape):
    """Vị trí nhãn tự động, tránh chồng lên nhãn khác: thử 8 hướng quanh điểm đo, lấy hướng xa nhãn khác nhất."""
    h, w = shape
    ban_kinh = (0.07 * w, 0.11 * w, 0.15 * w)
    dat = [(m["lx"], m["ly"]) for m in do_ds if m.get("lx") is not None and m.get("ly") is not None]
    kq = []
    for m in do_ds:
        if m.get("lx") is not None and m.get("ly") is not None:
            kq.append((m["lx"], m["ly"]))
            continue
        tot, diem_tot = None, None
        for r in ban_kinh:
            for k in range(8):
                g = math.radians(45 * k + 20)
                x, y = m["x"] + r * math.cos(g), m["y"] - r * math.sin(g)
                if not (0.06 * w < x < 0.94 * w and 0.04 * h < y < 0.96 * h):
                    continue
                kc = min([math.hypot(x - p[0], y - p[1]) for p in dat] + [9e9])
                # nhãn cũng không nên đè lên điểm đo khác
                kd = min([math.hypot(x - o["x"], y - o["y"]) for o in do_ds] + [9e9])
                diem = min(kc, kd * 1.3) - 0.2 * r
                if tot is None or diem > tot:
                    tot, diem_tot = diem, (x, y)
            if tot is not None and tot > 0.10 * w:
                break
        if diem_tot is None:
            diem_tot = vi_tri_nhan_mac_dinh(m, shape)
        dat.append(diem_tot)
        kq.append(diem_tot)
    return kq


def vi_tri_nhan_mac_dinh(m, shape):
    h, w = shape
    dx = 0.06 * w * (1 if m["x"] < w * 0.55 else -1)
    dy = -0.07 * h if m["y"] > h * 0.15 else 0.07 * h
    return m["x"] + dx, m["y"] + dy


def ve_lop_phu(ax, shape, nm_px, do_ds, hien_vung=False, chu=9, keo_duoc=False):
    """Vẽ mũi tên + nhãn lên trục ax (toạ độ px ảnh). Trả về list annotation (để đọc lại vị trí sau khi kéo)."""
    from matplotlib.patches import Rectangle
    import matplotlib.patheffects as pe
    ann_ds = []
    h, w = shape
    vitri = bo_tri_nhan(do_ds, shape)
    for m, (lx0, ly0) in zip(do_ds, vitri):
        th = math.radians(m["theta"])
        u = np.array([math.cos(th), -math.sin(th)])
        p = np.array([math.sin(th), math.cos(th)])
        c = np.array([m["x"], m["y"]], dtype=float)
        d_px = m["d"] / nm_px
        khe = max(d_px * m.get("so_van", 1), 1.5)   # đúng so_van khoảng d giữa hai đầu mũi tên (1 = một vân)
        dai = 0.03 * w
        mau = m.get("mau", "#ffffff")
        for s in (-1, 1):
            a0 = c + s * u * (khe / 2 + dai)
            a1 = c + s * u * (khe / 2)
            ax.annotate("", xy=tuple(a1), xytext=tuple(a0),
                        arrowprops=dict(arrowstyle="-|>", color=mau, lw=1.3, shrinkA=0, shrinkB=0, mutation_scale=9))
            l0 = c + s * u * (khe / 2) - p * dai * 0.7
            l1 = c + s * u * (khe / 2) + p * dai * 0.7
            ax.plot([l0[0], l1[0]], [l0[1], l1[1]], color=mau, lw=1.0)
        if hien_vung:
            ax.add_patch(Rectangle((m["x"] - m["n"] / 2, m["y"] - m["n"] / 2), m["n"], m["n"], fill=False,
                                   ec=mau, lw=0.6, ls="--"))
        lx, ly = lx0, ly0
        txt = nhan_mathtext(m.get("pha", ""), m.get("hkl", "")) + f"\n{m['d']:.2f} nm"
        t = ax.annotate(txt, xy=(m["x"], m["y"]), xytext=(lx, ly), textcoords="data", color=mau, fontsize=chu,
                        ha="center", va="center",
                        path_effects=[pe.withStroke(linewidth=1.8, foreground="black")],
                        arrowprops=dict(arrowstyle="-", color=mau, lw=0.4, alpha=0.6, shrinkA=6, shrinkB=2))
        if keo_duoc:
            t.draggable(True)
        t._do = m
        ann_ds.append(t)
    return ann_ds


def ve_tung_vung(a, nm_px, m, dinh, duong_dan, pad=4, dpi=200):
    """Hình 4 ô cho một vùng: ROI | FFT (khoanh đốm) | ảnh vân đã lọc | profile + đỉnh. Thay cho ảnh chụp ImageJ."""
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    roi, x0, y0, n = cat_vung(a, m["x"], m["y"], m["n"])
    lc = loc_dinh(roi, dinh, pad)
    pr = m.get("profile") or do_profile(roi, nm_px, dinh["theta"], dinh["d"])
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.8))
    lo, hi = np.percentile(roi, [1, 99])
    ax[0].imshow(roi, cmap="gray", vmin=lo, vmax=hi)
    ax[0].set_title(f"Vùng {n} px = {n * nm_px:.1f} nm", fontsize=9)
    mm = n * pad
    c = mm // 2
    ex = max(int(1.15 * dinh["r_pad"]), 40)
    ex = int(min(c - 2, ex))
    fm = anh_pho(roi, pad, ex)
    ax[1].imshow(fm, cmap="gray", vmin=np.percentile(fm, 5), vmax=np.percentile(fm, 99.8),
                 extent=[c - ex - 0.5, c + ex + 0.5, c + ex + 0.5, c - ex - 0.5])
    for s in (1, -1):
        ax[1].plot([c + s * (dinh["px"] - c)], [c + s * (dinh["py"] - c)], "o", mfc="none", mec="#ffd75e", ms=14)
    ax[1].set_title(f"FFT: d = {dinh['d']:.3f} nm (z = {dinh['z']:.1f})", fontsize=9)
    ax[2].imshow(lc, cmap="gray")
    ax[2].set_title("Vân sau lọc đốm", fontsize=9)
    ax[3].plot(pr["t_nm"], pr["v"], lw=1, color="#555")
    if len(pr["dinh_nm"]):
        pk = np.interp(pr["dinh_nm"], pr["t_nm"], pr["vs"])
        ax[3].plot(pr["dinh_nm"], pk, "v", color="#d62728", ms=5)
    ds = f"{pr['d_dinh']:.3f} ± {pr['d_sd']:.3f}" if pr["d_dinh"] else "n/a"
    ax[3].set_title(f"Profile: d = {ds} nm ({pr['n_van']} vân)", fontsize=9)
    ax[3].set_xlabel("Khoảng cách (nm)")
    for k in range(3):
        ax[k].set_xticks([])
        ax[k].set_yticks([])
    fig.tight_layout()
    fig.savefig(duong_dan, dpi=dpi)
    plt.close(fig)
    return duong_dan


# ====================== XUẤT BẢNG ======================

COT_CSV = ["stt", "nhan", "x_px", "y_px", "vung_px", "d_FFT_nm", "d_profile_nm", "d_profile_sd_nm", "so_van",
           "d_FFT1D_nm", "lech_%", "goc_do", "z", "chuan_nm", "lech_chuan_%", "nm_tren_px", "d_ImageJ_loc_nm", "d_ImageJ_tho_nm",
           "d_ImageJ_FFT_nm", "d_chung_nm", "xac_nhan_ImageJ"]


def _d_ij(m, khoa):
    ij = m.get("imagej") or {}
    pt = ij.get(khoa)
    if not pt or not pt.get("d_dinh"):
        return ""
    return f"{pt['d_dinh']:.4f}"


def ghi_csv(duong_dan, do_ds, nm_px):
    with open(duong_dan, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COT_CSV)
        for i, m in enumerate(do_ds, 1):
            dc = m.get("d_chuan")
            w.writerow([i, nhan_van_ban(m.get("pha", ""), m.get("hkl", "")), round(m["x"]), round(m["y"]), m["n"],
                        f"{m['d_fft']:.4f}",
                        "" if m.get("d_dinh") is None else f"{m['d_dinh']:.4f}",
                        "" if m.get("d_sd") is None else f"{m['d_sd']:.4f}", m.get("n_van", ""),
                        "" if m.get("d_fft1d") is None else f"{m['d_fft1d']:.4f}",
                        "" if m.get("lech_pct") is None else f"{m['lech_pct']:.2f}",
                        f"{m['theta']:.1f}", f"{m['z']:.1f}",
                        "" if dc is None else f"{dc:.4f}",
                        "" if dc is None else f"{100 * (m['d'] - dc) / dc:.2f}", f"{nm_px:.6f}",
                        _d_ij(m, "loc"), _d_ij(m, "tho"),
                        "" if not (m.get("imagej") or {}).get("d_fft_ij") else f"{m['imagej']['d_fft_ij']:.4f}",
                        "" if not (m.get("xac_nhan") or {}).get("d_chung") else f"{m['xac_nhan']['d_chung']:.4f}",
                        {"xac_nhan": "xac nhan", "kiem_tra": "kiem tra"}.get((m.get("xac_nhan") or {}).get("trang_thai"), "")])
    return duong_dan


# ====================== ĐIỀU KHIỂN IMAGEJ BẰNG MACRO ======================
# App sinh macro .ijm làm đúng chuỗi thao tác thủ công (Set Scale, Duplicate, FFT, Fill, Inverse FFT, Plot Profile),
# chạy ImageJ, rồi đọc kết quả (profile, ảnh chụp) về để so với phép đo của app.

MACRO_IJ = r"""// Echem Studio - do mat mang bang ImageJ (file tu dong tao, khong can sua tay)
// OUT=@@OUT@@
setBatchMode(@@BATCH@@);
var out = "@@OUT@@";
var res = out + "ketqua.txt";
function tien(s) { File.append(s, out + "tien_trinh.txt"); }
function ghi(tag, xs, ys) {
  sx = tag + "_X="; sy = tag + "_Y=";
  for (i = 0; i < ys.length; i++) {
    sx = sx + d2s(xs[i], 6);
    sy = sy + d2s(ys[i], 6);
    if (i < ys.length - 1) { sx = sx + ","; sy = sy + ","; }
  }
  File.append(sx, res);
  File.append(sy, res);
}
function profile(x1, y1, x2, y2, tag, ten_png) {
  makeLine(x1, y1, x2, y2);
  if (getVersion() >= "1.52a") {
    run("Plot Profile");
    Plot.getValues(px, py);
    if (ten_png != "") saveAs("PNG", out + ten_png);
  } else {
    py = getProfile();
    px = newArray(py.length);
    dx = sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1)) / (py.length - 1) * @@NMPX@@;
    for (i = 0; i < py.length; i++) px[i] = i * dx;
  }
  ghi(tag, px, py);
}
File.delete(out + "tien_trinh.txt");
File.delete(res);
File.delete(out + "xong.txt");
nmpx = @@NMPX@@;
x0 = @@X0@@; y0 = @@Y0@@; n = @@N@@;
d = @@D@@; th = @@THETA@@;
tien("1 mo anh");
open(out + "@@INPUT@@");
tien("2 dat thang (Set Scale)");
run("Set Scale...", "distance=1 known=" + d2s(nmpx, 8) + " pixel=1 unit=nm");
tien("3 cat vung (Duplicate)");
makeRectangle(x0, y0, n, n);
run("Duplicate...", "title=vung");
saveAs("PNG", out + "vung.png");
run("32-bit");
vung = getImageID();
tien("4 FFT (Process > FFT)");
selectImage(vung);
run("FFT");
fft = getImageID();
N = getWidth();
tien("5 khoanh dom + Fill");
r = N * nmpx / d;
cx = N / 2; cy = N / 2;
rad = maxOf(3, N / 128);
setForegroundColor(255, 255, 255);
for (s = -1; s <= 1; s += 2) {
  x = cx + s * r * cos(th * PI / 180);
  y = cy - s * r * sin(th * PI / 180);
  makeOval(x - rad, y - rad, 2 * rad, 2 * rad);
  run("Fill", "slice");
}
run("Select None");
saveAs("PNG", out + "fft_dom.png");
tien("6 Inverse FFT");
selectImage(fft);
run("Inverse FFT");
inv = getImageID();
saveAs("PNG", out + "van_loc.png");
tien("7 Plot Profile");
File.append("IJ_VERSION=" + getVersion(), res);
File.append("N_FFT=" + N, res);
File.append("R_DOM=" + d2s(r, 4), res);
File.append("NM_PX=" + d2s(nmpx, 8), res);
L = 0.35 * n; c = n / 2;
ux = cos(th * PI / 180); uy = -sin(th * PI / 180);
run("Line Width...", "line=" + round(0.5 * n));
selectImage(inv);
profile(c - L * ux, c - L * uy, c + L * ux, c + L * uy, "LOC", "profile_loc.png");
selectImage(vung);
profile(c - L * ux, c - L * uy, c + L * ux, c + L * uy, "THO", "");
run("Line Width...", "line=1");
tien("8 xong");
File.saveString("ok", out + "xong.txt");
"""


def tim_imagej():
    """Đoán đường dẫn ImageJ/Fiji: biến môi trường ECHEM_IMAGEJ rồi các vị trí hay gặp. Không thấy -> chuỗi rỗng."""
    ung = []
    if os.environ.get("ECHEM_IMAGEJ"):
        ung.append(os.environ["ECHEM_IMAGEJ"])
    goc = []
    for ev in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "USERPROFILE"):
        if os.environ.get(ev):
            goc.append(os.environ[ev])
    goc += ["C:\\", "D:\\", os.path.expanduser("~")]
    for g in goc:
        for ten in ("ImageJ\\ImageJ.exe", "ImageJ\\ij.jar", "Fiji.app\\ImageJ-win64.exe", "Fiji\\ImageJ-win64.exe",
                    "ImageJ/ImageJ.exe", "Fiji.app/ImageJ-win64.exe", "Fiji.app/ImageJ-linux64", "ImageJ/ij.jar"):
            ung.append(os.path.join(g, ten.replace("\\", os.sep)))
    for p in ung:
        if p and os.path.isfile(p):
            return p
    return ""


def _so_ij(x, nhieu=6):
    return repr(round(float(x), nhieu))


def tao_macro_imagej(thu_muc_ra, ten_anh, nm_px, x0, y0, n, d, theta, an=False):
    """Sinh nội dung macro .ijm. Mọi đường dẫn dùng dấu / (ImageJ chấp nhận trên Windows); không có ký tự ngoài ASCII."""
    out = thu_muc_ra.replace("\\", "/")
    if not out.endswith("/"):
        out += "/"
    kq = MACRO_IJ
    for k, v in (("@@OUT@@", out), ("@@INPUT@@", ten_anh), ("@@BATCH@@", "true" if an else "false"),
                 ("@@NMPX@@", _so_ij(nm_px, 8)), ("@@X0@@", str(int(x0))), ("@@Y0@@", str(int(y0))), ("@@N@@", str(int(n))),
                 ("@@D@@", _so_ij(d, 6)), ("@@THETA@@", _so_ij(theta, 3))):
        kq = kq.replace(k, v)
    return kq


def lenh_imagej(duong, macro, an=False):
    """Dòng lệnh chạy macro: ImageJ.exe/Fiji -macro (hiện cửa sổ) hoặc -batch (chạy nền, tự thoát)."""
    co = "-batch" if an else "-macro"
    if duong.lower().endswith(".jar"):
        java = os.path.join(os.path.dirname(duong), "jre", "bin", "java.exe")
        if not os.path.isfile(java):
            java = "java"
        return [java, "-jar", duong, co, macro]
    return [duong, co, macro]


def thu_muc_tam_ascii():
    """Thư mục tạm không có dấu cách/ký tự lạ (ImageJ đọc macro theo bảng mã hệ thống, đường dẫn tiếng Việt dễ hỏng)."""
    import tempfile
    ung = [os.path.join(tempfile.gettempdir(), "echem_ij"), "C:\\echem_ij", os.path.join(os.path.expanduser("~"), "echem_ij")]
    for p in ung:
        try:
            p.encode("ascii")
        except UnicodeEncodeError:
            continue
        if " " in p:
            continue
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except OSError:
            continue
    p = ung[0]
    os.makedirs(p, exist_ok=True)
    return p


def khoi_chay_imagej(duong_imagej, anh, nm_px, x0, y0, n, d, theta, an=False, thu_muc=None):
    """Chép ảnh vào thư mục tạm, sinh macro, chạy ImageJ không chặn. Trả về 'tay cầm' dict cho kiem_ketqua_imagej."""
    import shutil
    import subprocess
    import time
    if not duong_imagej or not os.path.isfile(duong_imagej):
        raise FileNotFoundError("Chưa chọn đúng file ImageJ (ImageJ.exe, Fiji hoặc ij.jar).")
    goc = thu_muc or thu_muc_tam_ascii()
    th = os.path.join(goc, time.strftime("lan_%H%M%S"))
    os.makedirs(th, exist_ok=True)
    ext = os.path.splitext(anh)[1].lower() or ".png"
    ten_anh = "vao" + ext
    shutil.copyfile(anh, os.path.join(th, ten_anh))
    macro = os.path.join(th, "do_mat_mang.ijm")
    with open(macro, "w", encoding="ascii", newline="\n") as f:
        f.write(tao_macro_imagej(th, ten_anh, nm_px, x0, y0, n, d, theta, an))
    cmd = lenh_imagej(duong_imagej, macro, an)
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000   # CREATE_NO_WINDOW cho tiến trình java chạy nền
    proc = subprocess.Popen(cmd, cwd=os.path.dirname(duong_imagej) or None, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    return {"thu_muc": th, "macro": macro, "proc": proc, "cmd": cmd, "bat_dau": time.time(),
            "nm_px": nm_px, "d_ref": d, "n": n}


def _doc_kv(duong):
    kq = {}
    with open(duong, encoding="utf-8", errors="ignore") as f:
        for dong in f.read().splitlines():
            if "=" in dong:
                k, v = dong.split("=", 1)
                kq[k.strip()] = v.strip()
    return kq


def _mang(kv, khoa):
    t = kv.get(khoa, "")
    if not t:
        return None
    try:
        return np.array([float(x) for x in t.split(",")])
    except ValueError:
        return None


def tien_trinh_imagej(h):
    p = os.path.join(h["thu_muc"], "tien_trinh.txt")
    if not os.path.isfile(p):
        return ""
    with open(p, encoding="utf-8", errors="ignore") as f:
        dong = [x for x in f.read().splitlines() if x.strip()]
    return dong[-1] if dong else ""


def kiem_ketqua_imagej(h):
    """None = còn chạy; dict {ok: False, loi} nếu hỏng; dict {ok: True, ...} khi macro đã chạy xong và đọc được kết quả."""
    th = h["thu_muc"]
    if not os.path.isfile(os.path.join(th, "xong.txt")):
        rc = h["proc"].poll() if h.get("proc") is not None else None
        # ImageJ.exe có thể thoát ngay vì chuyển việc cho cửa sổ ImageJ đang mở -> không coi là lỗi
        if rc not in (None, 0):
            return {"ok": False, "loi": f"ImageJ thoát với mã {rc}.", "buoc": tien_trinh_imagej(h)}
        return None
    kv = _doc_kv(os.path.join(th, "ketqua.txt")) if os.path.isfile(os.path.join(th, "ketqua.txt")) else {}
    kq = {"ok": True, "thu_muc": th, "ij_version": kv.get("IJ_VERSION", ""), "n_fft": kv.get("N_FFT", "")}
    for tag, ten in (("LOC", "loc"), ("THO", "tho")):
        x, y = _mang(kv, tag + "_X"), _mang(kv, tag + "_Y")
        if x is None or y is None or len(x) < 8:
            kq[ten] = None
            continue
        dx = float(np.median(np.diff(x)))
        pt = phan_tich_chuoi(y, dx, h["d_ref"])
        pt["t_nm"] = x - x[0]
        kq[ten] = pt
    for ten in ("vung.png", "fft_dom.png", "van_loc.png", "profile_loc.png"):
        p = os.path.join(th, ten)
        kq[ten] = p if os.path.isfile(p) else None
    return kq


# ---- kiểm chứng hàng loạt bằng ImageJ: mọi vùng đã đo chạy trong MỘT phiên ImageJ ----
MACRO_IJ_LO = r"""// Echem Studio - kiem chung nhieu vung bang ImageJ (file tu dong tao, khong can sua tay)
// OUT=@@OUT@@
setBatchMode(@@BATCH@@);
var out = "@@OUT@@";
var res = out + "ketqua.txt";
function tien(s) { File.append(s, out + "tien_trinh.txt"); }
function ghi(tag, xs, ys) {
  sx = tag + "_X="; sy = tag + "_Y=";
  for (i = 0; i < ys.length; i++) {
    sx = sx + d2s(xs[i], 6);
    sy = sy + d2s(ys[i], 6);
    if (i < ys.length - 1) { sx = sx + ","; sy = sy + ","; }
  }
  File.append(sx, res);
  File.append(sy, res);
}
function profile(x1, y1, x2, y2, tag) {
  makeLine(x1, y1, x2, y2);
  if (getVersion() >= "1.52a") {
    run("Plot Profile");
    Plot.getValues(px, py);
    close();
  } else {
    py = getProfile();
    px = newArray(py.length);
    dx = sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1)) / (py.length - 1) * @@NMPX@@;
    for (i = 0; i < py.length; i++) px[i] = i * dx;
  }
  ghi(tag, px, py);
}
File.delete(out + "tien_trinh.txt");
File.delete(res);
File.delete(out + "xong.txt");
nmpx = @@NMPX@@;
nreg = @@NREG@@;
x0s = newArray(@@X0S@@);
y0s = newArray(@@Y0S@@);
ns = newArray(@@NS@@);
ds = newArray(@@DS@@);
ths = newArray(@@THS@@);
open(out + "@@INPUT@@");
run("Set Scale...", "distance=1 known=" + d2s(nmpx, 8) + " pixel=1 unit=nm");
orig = getImageID();
setForegroundColor(255, 255, 255);
for (k = 0; k < nreg; k++) {
  tien("vung " + (k + 1) + "/" + nreg);
  p = "R" + k + "_";
  n = ns[k]; d = ds[k]; th = ths[k];
  selectImage(orig);
  makeRectangle(x0s[k], y0s[k], n, n);
  run("Duplicate...", "title=vung");
  run("32-bit");
  vung = getImageID();
  run("FFT");
  fft = getImageID();
  N = getWidth();
  File.append(p + "N_FFT=" + N, res);
  r = N * nmpx / d;
  cx = N / 2; cy = N / 2;
  ex = cx + r * cos(th * PI / 180);
  ey = cy - r * sin(th * PI / 180);
  w = maxOf(4, round(N / 48));
  pmax = -1; bx = round(ex); by = round(ey);
  for (yy = round(ey) - w; yy <= round(ey) + w; yy++)
    for (xx = round(ex) - w; xx <= round(ex) + w; xx++)
      if (xx >= 0 && yy >= 0 && xx < N && yy < N) {
        v = getPixel(xx, yy);
        if (v > pmax) { pmax = v; bx = xx; by = yy; }
      }
  pmin = pmax;
  for (yy = by - w; yy <= by + w; yy++)
    for (xx = bx - w; xx <= bx + w; xx++)
      if (xx >= 0 && yy >= 0 && xx < N && yy < N) pmin = minOf(pmin, getPixel(xx, yy));
  thr = pmax - 0.5 * (pmax - pmin);
  sw = 0; sxw = 0; syw = 0;
  for (yy = by - w; yy <= by + w; yy++)
    for (xx = bx - w; xx <= bx + w; xx++)
      if (xx >= 0 && yy >= 0 && xx < N && yy < N) {
        v = getPixel(xx, yy);
        if (v > thr) { sw = sw + (v - thr); sxw = sxw + (v - thr) * xx; syw = syw + (v - thr) * yy; }
      }
  if (sw > 0) { bx = sxw / sw; by = syw / sw; }
  File.append(p + "PEAK_X=" + d2s(bx, 4), res);
  File.append(p + "PEAK_Y=" + d2s(by, 4), res);
  rad = maxOf(3, N / 128);
  for (s = -1; s <= 1; s += 2) {
    x = cx + s * r * cos(th * PI / 180);
    y = cy - s * r * sin(th * PI / 180);
    makeOval(x - rad, y - rad, 2 * rad, 2 * rad);
    run("Fill", "slice");
  }
  run("Select None");
  saveAs("PNG", out + "r" + k + "_fft_dom.png");
  selectImage(fft);
  run("Inverse FFT");
  inv = getImageID();
  saveAs("PNG", out + "r" + k + "_van_loc.png");
  L = 0.35 * n; c = n / 2;
  ux = cos(th * PI / 180); uy = -sin(th * PI / 180);
  run("Line Width...", "line=" + round(0.5 * n));
  selectImage(inv);
  profile(c - L * ux, c - L * uy, c + L * ux, c + L * uy, p + "LOC");
  selectImage(vung);
  profile(c - L * ux, c - L * uy, c + L * ux, c + L * uy, p + "THO");
  run("Line Width...", "line=1");
  selectImage(inv); close();
  selectImage(fft); close();
  selectImage(vung); close();
}
tien("xong");
File.saveString("ok", out + "xong.txt");
"""


def tao_macro_imagej_lo(thu_muc_ra, ten_anh, nm_px, ds, an=True):
    """ds: list dict {x0, y0, n, d, theta}. Trả về nội dung macro kiểm chứng hàng loạt (ASCII, đường dẫn dùng dấu /)."""
    out = thu_muc_ra.replace("\\", "/")
    if not out.endswith("/"):
        out += "/"

    def ds_so(khoa, f):
        return ",".join(f(v[khoa]) for v in ds)
    kq = MACRO_IJ_LO
    for k, v in (("@@OUT@@", out), ("@@INPUT@@", ten_anh), ("@@BATCH@@", "true" if an else "false"),
                 ("@@NMPX@@", _so_ij(nm_px, 8)), ("@@NREG@@", str(len(ds))),
                 ("@@X0S@@", ds_so("x0", lambda x: str(int(x)))), ("@@Y0S@@", ds_so("y0", lambda x: str(int(x)))),
                 ("@@NS@@", ds_so("n", lambda x: str(int(x)))), ("@@DS@@", ds_so("d", lambda x: _so_ij(x, 6))),
                 ("@@THS@@", ds_so("theta", lambda x: _so_ij(x, 3)))):
        kq = kq.replace(k, v)
    return kq


def vung_cho_imagej(m):
    """Thông số một phép đo -> dict cho macro kiểm chứng (x0, y0 là góc trên-trái của vùng vuông)."""
    n = int(m["n"])
    dinh = m["dinh"]
    return {"x0": max(0, int(round(m["x"] - n / 2.0))), "y0": max(0, int(round(m["y"] - n / 2.0))), "n": n,
            "d": float(dinh["d"]), "theta": float(dinh["theta"])}


def khoi_chay_imagej_lo(duong_imagej, anh, nm_px, ds, an=True, thu_muc=None):
    """Chép ảnh, sinh macro cho nhiều vùng, chạy ImageJ không chặn. Trả về tay cầm cho kiem_ketqua_imagej_lo."""
    import shutil
    import subprocess
    import time
    if not duong_imagej or not os.path.isfile(duong_imagej):
        raise FileNotFoundError("Chưa chọn đúng file ImageJ (ImageJ.exe, Fiji hoặc ij.jar).")
    if not ds:
        raise ValueError("Chưa có vùng nào để kiểm chứng.")
    goc = thu_muc or thu_muc_tam_ascii()
    import tempfile
    th = tempfile.mkdtemp(prefix=time.strftime("kiemchung_%H%M%S_"), dir=goc)
    ext = os.path.splitext(anh)[1].lower() or ".png"
    ten_anh = "vao" + ext
    shutil.copyfile(anh, os.path.join(th, ten_anh))
    macro = os.path.join(th, "kiem_chung.ijm")
    with open(macro, "w", encoding="ascii", newline="\n") as f:
        f.write(tao_macro_imagej_lo(th, ten_anh, nm_px, ds, an))
    cmd = lenh_imagej(duong_imagej, macro, an)
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000
    proc = subprocess.Popen(cmd, cwd=os.path.dirname(duong_imagej) or None, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    return {"thu_muc": th, "macro": macro, "proc": proc, "cmd": cmd, "bat_dau": time.time(), "nm_px": nm_px,
            "ds": list(ds), "lo": True}


def kiem_ketqua_imagej_lo(h):
    """None = còn chạy; {ok: False, loi} nếu hỏng; {ok: True, ds: [ {d_fft_ij, theta_ij, loc, tho, n_fft, ảnh...} ]} khi xong."""
    th = h["thu_muc"]
    if not os.path.isfile(os.path.join(th, "xong.txt")):
        rc = h["proc"].poll() if h.get("proc") is not None else None
        if rc not in (None, 0):
            return {"ok": False, "loi": f"ImageJ thoát với mã {rc}.", "buoc": tien_trinh_imagej(h)}
        return None
    kv = _doc_kv(os.path.join(th, "ketqua.txt")) if os.path.isfile(os.path.join(th, "ketqua.txt")) else {}
    nm_px = h["nm_px"]
    ds = []
    for k, v in enumerate(h["ds"]):
        p = f"R{k}_"
        r = {"thu_muc": th}
        try:
            N = int(float(kv[p + "N_FFT"]))
            px, py = float(kv[p + "PEAK_X"]), float(kv[p + "PEAK_Y"])
            rr = math.hypot(px - N / 2.0, py - N / 2.0)
            r["n_fft"] = N
            r["d_fft_ij"] = N * nm_px / rr if rr > 1e-6 else None
            r["theta_ij"] = math.degrees(math.atan2(N / 2.0 - py, px - N / 2.0)) % 180.0
        except (KeyError, ValueError):
            r["d_fft_ij"] = r["theta_ij"] = None
        for tag, ten in (("LOC", "loc"), ("THO", "tho")):
            x, y = _mang(kv, p + tag + "_X"), _mang(kv, p + tag + "_Y")
            if x is None or y is None or len(x) < 8:
                r[ten] = None
                continue
            pt = phan_tich_chuoi(y, float(np.median(np.diff(x))), v["d"])
            pt["t_nm"] = x - x[0]
            r[ten] = pt
        for ten in ("fft_dom", "van_loc"):
            f = os.path.join(th, f"r{k}_{ten}.png")
            r[ten + ".png"] = f if os.path.isfile(f) else None
        ds.append(r)
    return {"ok": True, "thu_muc": th, "ds": ds}


def tong_hop_xac_nhan(m, r, nguong_pct=3.0, dung_sai=0.03):
    """Gộp các ước lượng độc lập của cùng một vùng: d FFT & d profile của app, d FFT (đỉnh) & d profile (ảnh lọc, ảnh gốc) của ImageJ.
    d chung = trung vị. Trạng thái: 'xac_nhan' nếu độ tản (max-min)/trung vị <= nguong_pct và còn khớp mặt chuẩn trong dung_sai,
    ngược lại 'kiem_tra'. Trả về dict (không sửa m)."""
    cac = {"app_fft": m.get("d_fft"), "app_profile": m.get("d_dinh"), "ij_fft": r.get("d_fft_ij"),
           "ij_loc": (r.get("loc") or {}).get("d_dinh"), "ij_tho": (r.get("tho") or {}).get("d_dinh")}
    cac = {k: float(v) for k, v in cac.items() if v}
    if not any(k.startswith("ij_") for k in cac) or len(cac) < 3:      # phải có ít nhất một ước lượng từ ImageJ
        return {"cac": cac, "d_chung": m.get("d"), "tan_pct": None, "trang_thai": "kiem_tra",
                "canh_bao": ["ImageJ không đo được đủ ước lượng độc lập."]}
    v = np.array(list(cac.values()))
    d_chung = float(np.median(v))
    tan = 100.0 * float(v.max() - v.min()) / d_chung
    canh = []
    dc = m.get("d_chuan")
    lech_chuan = None if dc is None else 100.0 * (d_chung - dc) / dc
    if tan > nguong_pct:
        canh.append(f"các phương pháp lệch nhau {tan:.1f}% (> {nguong_pct:.0f}%).")
    if lech_chuan is not None and abs(lech_chuan) > 100.0 * dung_sai:
        canh.append(f"d chung {d_chung:.3f} nm lệch {lech_chuan:+.1f}% so với mặt chuẩn: không còn khớp trong dung sai.")
    th_ij, th_app = r.get("theta_ij"), (m.get("dinh") or {}).get("theta")
    if th_ij is not None and th_app is not None and abs(((th_ij - th_app) + 90) % 180 - 90) > 8:
        canh.append("ImageJ tìm đốm ở hướng khác app (> 8°).")
    return {"cac": cac, "d_chung": d_chung, "tan_pct": tan, "lech_chuan_pct": lech_chuan,
            "trang_thai": "xac_nhan" if not canh else "kiem_tra", "canh_bao": canh}


def ghi_macro_thu_cong(thu_muc, anh, nm_px, x0, y0, n, d, theta, an=False):
    """Để người dùng tự chạy trong ImageJ (Plugins > Macros > Run...): chép ảnh + ghi macro vào thu_muc. Trả về đường dẫn macro."""
    import shutil
    os.makedirs(thu_muc, exist_ok=True)
    ext = os.path.splitext(anh)[1].lower() or ".png"
    shutil.copyfile(anh, os.path.join(thu_muc, "vao" + ext))
    macro = os.path.join(thu_muc, "do_mat_mang.ijm")
    with open(macro, "w", encoding="ascii", newline="\n") as f:
        f.write(tao_macro_imagej(thu_muc, "vao" + ext, nm_px, x0, y0, n, d, theta, an))
    return macro
