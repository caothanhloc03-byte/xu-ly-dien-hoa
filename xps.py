# -*- coding: utf-8 -*-
"""Xử lý & fit phổ XPS (kiểu CasaXPS) - chỉ dùng numpy.

Quy trình: đọc phổ (VAMAS .vms của CasaXPS, file text/CSV/Excel xuất từ CasaXPS) -> hiệu chuẩn năng lượng (C1s = 284.8 eV)
-> nền Shirley -> fit các thành phần GL(30) có ràng buộc hoá học -> Residual STD, thành phần, diện tích %
-> xuất CSV (để vẽ Origin) và hình matplotlib theo kiểu hình mẫu.

Nguyên tắc fit: ràng buộc vị trí/độ rộng theo hoá học (không để thuật toán tự trôi cho 'đẹp số'); thêm thành phần chỉ khi
cải thiện có ý nghĩa thống kê VÀ nằm trong cửa sổ hoá học của loại liên kết đó."""
import csv
import math
import os
import re

import numpy as np

DW_FWHM = 0.2                      # chênh FWHM tối đa giữa các thành phần cùng họ (eV); tài liệu: ±10% hoặc ±0.1 eV
F_TOI_HAN = 4.0                    # ngưỡng F (thêm 3 tham số, p < 0.01, bậc tự do ~100)
HE_SO_GL = 30.0                    # GL(30): 70% Gauss, 30% Lorentz (dạng tích) như CasaXPS
LN2_4 = 4.0 * math.log(2.0)


# ====================== ĐỌC DỮ LIỆU ======================
def _so(t):
    try:
        return float(t.replace(",", ".")) if "," in t and "." not in t else float(t)
    except ValueError:
        return None


def _sap_xep(be, y):
    be, y = np.asarray(be, float), np.asarray(y, float)
    o = np.argsort(be)
    return be[o], y[o]


def _doc_vamas_do(duong):
    """(Phương án dự phòng, dò từ khoá.) Đọc file VAMAS (.vms) do CasaXPS ghi. Trả về list vùng: dict(ten, be, y, nguon). Dò theo từ khoá (không phụ thuộc
    số dòng cố định). Nếu trục là động năng (kinetic energy) thì đổi sang năng lượng liên kết bằng hv của nguồn."""
    with open(duong, "r", encoding="latin-1", errors="ignore") as f:
        dong = [x.rstrip("\r\n").strip() for x in f.read().split("\n")]
    if not dong or not dong[0].upper().startswith("VAMAS"):
        raise ValueError("Không phải file VAMAS (.vms).")
    vung = []
    chi_so = [i for i, t in enumerate(dong) if t.upper() == "XPS"]
    for k, i in enumerate(chi_so):
        gioi_han = chi_so[k + 1] - 12 if k + 1 < len(chi_so) else len(dong)
        nhan = None
        for j in range(i, min(i + 60, len(dong))):
            if re.fullmatch(r"(binding|kinetic) energy", dong[j], re.I):
                nhan = j
                break
        if nhan is None:
            continue
        dong_nl = dong[nhan]
        try:
            bd, buoc = float(dong[nhan + 2]), float(dong[nhan + 3])
        except (ValueError, IndexError):
            continue
        pos = nhan + 4
        du_lieu = None
        for j in range(pos, min(pos + 120, len(dong) - 3)):
            if re.fullmatch(r"\d+", dong[j]):
                n = int(dong[j])
                if n < 20 or j + 3 + n > len(dong) + 1:
                    continue
                if _so(dong[j + 1]) is None or _so(dong[j + 2]) is None:
                    continue
                gt = [_so(t) for t in dong[j + 3:j + 3 + n]]
                if all(v is not None for v in gt):
                    du_lieu = np.array(gt, float)
                    break
        if du_lieu is None:
            continue
        e = bd + buoc * np.arange(len(du_lieu))
        if dong_nl.lower().startswith("kinetic"):
            hv = 1486.6
            for j in range(max(0, i - 15), i + 15):
                v = _so(dong[j]) if j < len(dong) else None
                if v is not None and 1000 < v < 1700:
                    hv = v
                    break
            e = hv - e
        ten = None
        j = i - 1
        while j > 0 and _so(dong[j]) is None:                 # bỏ các dòng chú thích
            j -= 1
        while j > 0 and _so(dong[j]) is not None:             # bỏ dãy số: số dòng chú thích + ngày giờ
            j -= 1
        mau_id = [dong[j - 1] if j >= 1 else "", dong[j]]     # [mã khối, mã mẫu]
        for t in mau_id:
            if t and t.lower() not in ("not specified", "norm", "regular"):
                ten = t
                break
        be, y = _sap_xep(e, du_lieu)
        vung.append({"ten": ten or f"Vung {k + 1}", "be": be, "y": y, "nguon": "VAMAS"})
    if not vung:
        raise ValueError("Không tìm thấy phổ nào trong file VAMAS này (có thể dùng bản ghi khác). "
                         "Hãy xuất từ CasaXPS: File > Export (text) rồi mở file text.")
    return vung


class _Dong:
    """Bộ đọc tuần tự từng dòng của file VAMAS (ISO 14976)."""

    def __init__(self, text):
        self.d = [x.rstrip("\r\n").strip() for x in text.split("\n")]
        self.i = 0

    def s(self):
        if self.i >= len(self.d):
            raise ValueError("VAMAS: hết file giữa chừng")
        t = self.d[self.i]
        self.i += 1
        return t

    def f(self):
        t = self.s()
        v = _so(t)
        if v is None:
            raise ValueError(f"VAMAS: dòng {self.i} cần số, gặp '{t}'")
        return v

    def n(self):
        return int(round(self.f()))

    def bo(self, k):
        for _ in range(k):
            self.s()


def doc_vamas(duong):
    """Đọc file VAMAS (.vms, ISO 14976) THEO ĐÚNG CẤU TRÚC chuẩn (CasaXPS ghi theo chuẩn này): header -> từng block
    (NORM/MAP, REGULAR/IRREGULAR, đủ các trường). Mỗi block là một vùng phổ; trả về list dict(ten, be, y, nguon, hv, dwell,
    scans, loai_truc, ghi_chu_casa). Trục động năng đổi sang BE = hv - KE. Nếu cấu trúc lạ thì quay về cách dò từ khoá."""
    with open(duong, "r", encoding="latin-1", errors="ignore") as fh:
        text = fh.read()
    if not text.lstrip().upper().startswith("VAMAS"):
        raise ValueError("Không phải file VAMAS (.vms).")
    try:
        vung = _doc_vamas_chuan(text)
    except (ValueError, IndexError):
        vung = []
    if not vung:
        return _doc_vamas_do(duong)
    return vung


def _doc_vamas_chuan(text, vet=None):
    r = _Dong(text)
    r.bo(5)                                   # định dạng, cơ quan, máy, người đo, mã thí nghiệm
    r.bo(r.n())                               # dòng chú thích
    mode = r.s().upper()
    scan = r.s().upper()
    ban_do = mode in ("MAP", "MAPDP")
    r.n()                                     # số vùng phổ
    if ban_do:
        r.bo(3)                               # số vị trí phân tích, số điểm x, y
    nbien = r.n()
    r.bo(2 * nbien)                           # nhãn + đơn vị biến thực nghiệm
    nbo = r.n()                               # danh sách tham số bao gồm/loại trừ
    if nbo:
        raise ValueError("VAMAS: danh sách bao gồm/loại trừ không rỗng - không hỗ trợ")
    r.bo(3)                                   # mục nhập tay, mục nâng cấp (thí nghiệm, block)
    nblock = r.n()
    vung = []
    for k in range(nblock):
        idb = r.s()
        r.s()                                 # mã mẫu
        r.bo(7)                               # ngày giờ
        nct = r.n()
        if vet is not None:
            vet.append((r.i - 1, nct))                  # chỉ số dòng 'số dòng chú thích' của khối, để ghi đè chú thích
        ghi = [r.s() for _ in range(nct)]
        ky_thuat = r.s().upper()
        if ban_do:
            r.bo(2)
        r.bo(nbien)                           # giá trị biến thực nghiệm
        r.s()                                 # nhãn nguồn
        hv = None
        if ky_thuat in ("XPS", "UPS", "XRF", "AES diff", "AES dir", "EDX", "ELS", "FABMS", "FABMS energy spec", "ISS", "SIMS",
                        "SIMS energy spec", "SNMS", "SNMS energy spec", "UPS".upper(), "AES DIFF", "AES DIR"):
            hv = r.f()
        r.bo(3)                               # cường độ nguồn, độ rộng chùm x, y
        if ban_do:
            r.bo(2)
        r.bo(2)                               # góc cực, phương vị của nguồn
        r.s()                                 # chế độ máy phân tích
        r.bo(8)                               # năng lượng qua, độ phóng đại, công thoát, thế hiệu, rộng x,y, góc
        loai = r.s()
        chuyen = r.s()
        r.s()                                 # điện tích hạt
        if scan == "REGULAR":
            nhan = r.s()
            r.s()                             # đơn vị
            e0 = r.f()
            buoc = r.f()
            nv = r.n()
            bien = [(r.s(), r.s()) for _ in range(nv)]
            nhan_y = bien[0][0] if bien else ""
        else:
            nv = r.n()
            bien = [(r.s(), r.s()) for _ in range(nv)]
            nhan = bien[0][0]
            nhan_y = bien[1][0] if len(bien) > 1 else bien[0][0]
            e0 = buoc = None
        r.s()                                 # chế độ tín hiệu
        dwell = r.f()
        scans = r.n()
        r.bo(4)                               # hiệu chỉnh thời gian, góc nghiêng, phương vị, quay mẫu
        nthem = r.n()
        r.bo(3 * nthem)
        ncu = r.n()                           # số giá trị tung độ (tổng)
        r.bo(2 * nv)                          # min, max từng biến
        if nv < 1 or ncu < 1:
            raise ValueError("VAMAS: block rỗng")
        if scan == "REGULAR":
            n_diem = ncu // nv
            gt = np.array([r.f() for _ in range(ncu)], float).reshape(n_diem, nv)
            e = e0 + buoc * np.arange(n_diem)
            y = gt[:, 0]
        else:
            n_diem = ncu // nv
            gt = np.array([r.f() for _ in range(ncu)], float).reshape(n_diem, nv)
            e = gt[:, 0]
            y = gt[:, 1] if nv > 1 else gt[:, 0]
        if "kinetic" in nhan.lower():
            e = (hv if hv and 100 < hv < 20000 else 1486.6) - e
        be, yy = _sap_xep(e, y)
        # Casa hiển thị CPS = Counts/(dwell x scan) khi nhãn tung độ là "Counts": đổi về CPS để diện tích, sigma, Residual STD khớp Casa
        nl = (nhan_y or "").strip().lower()
        he_so = 1.0
        if nl.startswith("count") and not re.search(r"per\s*s|/\s*s|cps", nl) and dwell and scans and dwell * scans > 0:
            he_so = 1.0 / (dwell * scans)
        y_dem = yy
        yy = yy * he_so
        ten = idb if idb and idb.lower() not in ("not specified", "") else (loai + (" " + chuyen if chuyen.lower() != "none" else ""))
        casa = [t for t in ghi if t.startswith("CASA ")]
        vung.append({"ten": ten, "be": be, "y": yy, "nguon": "VAMAS", "hv": hv, "dwell": dwell, "scans": scans,
                     "loai_truc": nhan, "tung_do": nhan_y, "he_so_cps": he_so, "y_dem": y_dem, "ghi_chu_casa": casa, "loai": loai, "chuyen": chuyen, "so_diem": len(be)})
    return vung


def doc_van_ban(duong):
    """File text/CSV/TSV (CasaXPS: Export text, hoặc copy-paste bảng): tìm các khối dòng số, cột 1 = năng lượng liên kết,
    các cột sau là cường độ. Mỗi khối -> một vùng (dùng cột cường độ đầu tiên, ưu tiên cột tên chứa raw/cps/count)."""
    with open(duong, "r", encoding="utf-8-sig", errors="ignore") as f:
        raw = f.read().splitlines()
    return _gom_khoi([re.split(r"[\t,;]+|\s{2,}|\s", d.strip()) for d in raw], raw)


def _gom_khoi(hang, raw):
    khoi, hien, dau = [], [], None
    for i, h in enumerate(hang):
        h = [x for x in h if x != ""]
        v = [_so(x) for x in h]
        if len(h) >= 2 and all(x is not None for x in v):
            if not hien:
                dau = i
            hien.append(v)
        else:
            if len(hien) >= 15:
                khoi.append((dau, hien))
            hien = []
    if len(hien) >= 15:
        khoi.append((dau, hien))
    vung = []
    for k, (d0, rows) in enumerate(khoi):
        a = np.array([r[:min(len(r) for r in rows)] for r in rows], float)
        ten_cot = []
        for j in range(d0 - 1, max(-1, d0 - 4), -1):
            c = [x for x in re.split(r"[\t,;]+", raw[j].strip()) if x != ""]
            if len(c) >= a.shape[1] - 1 and c and _so(c[0]) is None:
                ten_cot = c
                break
        cot = 1
        for j, t in enumerate(ten_cot[-(a.shape[1] - 1):], 1):
            if re.search(r"raw|cps|count|c/s|intens", t, re.I):
                cot = j
                break
        be, y = _sap_xep(a[:, 0], a[:, cot])
        ten = (ten_cot[-(a.shape[1] - 1) + cot - 1] if len(ten_cot) >= a.shape[1] - 1 else f"Vung {k + 1}")
        vung.append({"ten": str(ten), "be": be, "y": y, "nguon": "text"})
    if not vung:
        raise ValueError("Không thấy bảng số (cột năng lượng + cường độ) trong file.")
    return vung


def doc_excel(duong):
    import openpyxl
    wb = openpyxl.load_workbook(duong, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    hang = []
    raw = []
    for r in ws.iter_rows(values_only=True):
        c = ["" if v is None else str(v) for v in r]
        hang.append(c)
        raw.append("\t".join(c))
    return _gom_khoi(hang, raw)


def doc_xps(duong):
    ext = os.path.splitext(duong)[1].lower()
    if ext in (".vms", ".vamas"):
        return doc_vamas(duong)
    if ext in (".xlsx", ".xlsm"):
        return doc_excel(duong)
    try:
        with open(duong, "r", encoding="latin-1", errors="ignore") as f:
            if f.readline().upper().startswith("VAMAS"):
                return doc_vamas(duong)
    except OSError:
        pass
    return doc_van_ban(duong)


# ====================== HIỆU CHUẨN & NỀN ======================
def _lam_tron(y, k=5):
    if k <= 1 or len(y) < k:
        return np.asarray(y, float)
    w = np.ones(k) / k
    p = np.pad(np.asarray(y, float), k // 2, mode="edge")
    return np.convolve(p, w, mode="valid")


def tim_dinh_max(be, y, khoang=(290.0, 280.0), lam_tron=5):
    """Vị trí đỉnh cao nhất trong khoảng (như ô 'Measured' của CasaXPS), nội suy parabol trên dữ liệu làm trơn nhẹ."""
    lo, hi = min(khoang), max(khoang)
    m = (be >= lo) & (be <= hi)
    if m.sum() < 5:
        raise ValueError("Khoảng tìm đỉnh quá hẹp / ngoài dữ liệu.")
    idx = np.nonzero(m)[0]
    ys = _lam_tron(y, lam_tron)
    k = idx[int(np.argmax(ys[idx]))]
    if 1 <= k < len(be) - 1:
        a, b, c = ys[k - 1], ys[k], ys[k + 1]
        den = a - 2 * b + c
        if den != 0:
            return float(be[k] + 0.5 * (a - c) / den * (be[k + 1] - be[k]))
    return float(be[k])


def hieu_chuan(be, y, dich=284.8, khoang=(290.0, 280.0)):
    """Độ dịch (eV) để đỉnh cao nhất trong khoảng về đúng `dich`. Trả về (dich_ev, be_moi)."""
    do = tim_dinh_max(be, y, khoang)
    d = dich - do
    return d, be + d


def shirley(be, y, n_tb=3, so_lan=60):
    """Nền Shirley lặp giữa hai đầu vùng (trung bình n_tb điểm mỗi đầu). be tăng dần."""
    be, y = np.asarray(be, float), np.asarray(y, float)
    i_lo = float(np.mean(y[:n_tb]))        # đầu năng lượng liên kết thấp
    i_hi = float(np.mean(y[-n_tb:]))       # đầu năng lượng liên kết cao
    bg = np.full_like(y, i_lo)
    for _ in range(so_lan):
        d = y - bg
        tich = np.concatenate([[0.0], np.cumsum(0.5 * (d[1:] + d[:-1]) * np.diff(be))])
        tong = tich[-1]
        if abs(tong) < 1e-12:
            break
        moi = i_lo + (i_hi - i_lo) * tich / tong
        if np.max(np.abs(moi - bg)) < 1e-9 * max(1.0, abs(i_hi)):
            bg = moi
            break
        bg = moi
    return bg


def tuyen_tinh(be, y, n_tb=3):
    be, y = np.asarray(be, float), np.asarray(y, float)
    a, b = float(np.mean(y[:n_tb])), float(np.mean(y[-n_tb:]))
    return a + (b - a) * (be - be[0]) / (be[-1] - be[0])


def tougaard(be, y, n_tb=3, C=1643.0, so_diem=None):
    """Nền Tougaard 'universal' (U2): bg(E) = i_lo + B * sum_{E' < E} K(E-E') (y(E') - i_lo) dE', K(T) = T / (C + T^2)^2.
    Electron mất năng lượng khi thoát nên nền tại BE cao do các đỉnh ở BE thấp hơn đóng góp. B được chọn sao cho nền khớp
    phần đuôi BE cao của vùng. Chỉ dùng dữ liệu trong vùng đã chọn: vùng càng rộng về phía BE thấp thì nền càng đúng."""
    be, y = np.asarray(be, float), np.asarray(y, float)
    i_lo = float(np.mean(y[:n_tb]))
    i_hi = float(np.mean(y[-n_tb:]))
    h = float(np.median(np.diff(be)))
    xu = np.arange(be[0], be[-1] + h / 2, h)                       # lưới đều
    yu = np.interp(xu, be, y) - i_lo
    t = np.arange(1, len(xu)) * h
    K = t / (C + t * t) ** 2
    s = np.zeros(len(xu))
    s[1:] = np.convolve(yu, K)[: len(xu) - 1] * h                   # s[j] = sum_{i<j} yu[i] K((j-i)h) h
    if s[-1] <= 0:
        return tuyen_tinh(be, y, n_tb)
    B = (i_hi - i_lo) / s[-1]
    return np.interp(be, xu, i_lo + B * s)


def nen_theo(ten, be, y):
    t = str(ten).lower()
    if t.startswith("shirley"):
        return shirley(be, y)
    if t.startswith("tougaard"):
        return tougaard(be, y)
    return tuyen_tinh(be, y)


_trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")


# ====================== HÌNH DẠNG ĐỈNH ======================
_GL_TI_LE = {}


def _gl_ti_le(m):
    """GL(m) dạng tích có độ rộng ở nửa chiều cao KHÁC tham số FWHM trong công thức gốc (tại t = 0.5 chỉ còn ~0.4735 với m = 30).
    CasaXPS dùng FWHM THẬT (đường cong cắt mức 0.5 tại ±FWHM/2): đối chiếu số liệu Casa thật cho thấy phải co trục t theo hệ số này
    thì phần dư phẳng và Residual STD trùng (1.06 so với 1.061 của Casa)."""
    k = round(float(m), 6)
    if k not in _GL_TI_LE:
        mm = k / 100.0
        lo, hi = 0.3, 1.5
        for _ in range(80):                       # nghiệm của f(t) = 0.5, f giảm theo t
            mid = 0.5 * (lo + hi)
            f = math.exp(-LN2_4 * (1.0 - mm) * mid * mid) / (1.0 + 4.0 * mm * mid * mid)
            lo, hi = (mid, hi) if f > 0.5 else (lo, mid)
        _GL_TI_LE[k] = 2.0 * 0.5 * (lo + hi)      # t_moi = t * 2 t*
    return _GL_TI_LE[k]


def gl(x, x0, fwhm, m=HE_SO_GL):
    """GL(m) của CasaXPS (dạng tích Gauss-Lorentz), chiều cao 1 tại x0, FWHM là bề rộng thật ở nửa chiều cao."""
    t = (np.asarray(x, float) - x0) / fwhm * _gl_ti_le(m)
    mm = m / 100.0
    return np.exp(-LN2_4 * (1.0 - mm) * t * t) / (1.0 + 4.0 * mm * t * t)


def la(x, x0, fwhm, a, b, sig=0.2):
    """Đỉnh bất đối xứng kiểu CasaXPS LA(a, b): Lorentz luỹ thừa với đuôi BE thấp ^a, đuôi BE cao ^b (a=b=1: Lorentz; số mũ nhỏ = đuôi dài, nên kim loại dùng a > b), rồi chập
    với Gauss (độ lệch chuẩn = sig x FWHM, mô phỏng giãn rộng do máy). FWHM tham số chính là FWHM của phần Lorentz luỹ thừa.
    Dùng cho kim loại (Au, Pt, Ru, Ni...), đuôi về phía BE cao do electron dẫn. Chiều cao ~1."""
    x = np.asarray(x, float)
    h = max(min(0.02, fwhm / 25.0), 0.004)
    pad = 4.0 * sig * fwhm + 6.0 * fwhm
    lo, hi = float(x.min()) - pad, float(x.max()) + pad
    g = np.arange(lo, hi + h / 2, h)
    t = (g - x0) / fwhm
    e = np.where(t < 0, a, b)
    kk = np.where(t < 0, 2.0 ** (1.0 / a) - 1.0, 2.0 ** (1.0 / b) - 1.0)
    p = (1.0 + 4.0 * kk * t * t) ** (-e)
    s = sig * fwhm
    if s > 0.5 * h:
        n = int(math.ceil(4.0 * s / h))
        kg = np.exp(-0.5 * ((np.arange(-n, n + 1) * h) / s) ** 2)
        kg /= kg.sum()
        p = np.convolve(p, kg, mode="same")
    v = np.interp(x, g, p)
    pk = float(np.interp(x0, g, p))
    return v / pk if pk > 0 else v


def hinh(x, x0, w, c, m=HE_SO_GL):
    """Hình dạng đỉnh của thành phần c: GL(m) đối xứng, hoặc LA(a,b) nếu c.la có đặt."""
    if getattr(c, "la", None):
        return la(x, x0, w, c.la[0], c.la[1])
    return gl(x, x0, w, m)


class ThanhPhan:
    """Một thành phần: vị trí/độ rộng có cửa sổ cho phép (ràng buộc hoá học)."""

    def __init__(self, ten, vt, vt_lo, vt_hi, w0, w_lo, w_hi, ghi_chu="", tach=0.0, ti_le=0.0, la=None):
        self.ten, self.vt, self.vt_lo, self.vt_hi = ten, vt, vt_lo, vt_hi
        self.w0, self.w_lo, self.w_hi = w0, w_lo, w_hi
        self.ghi_chu = ghi_chu
        self.tach = tach          # doublet spin-orbit: khoảng cách (eV) tới đỉnh thứ hai (BE cao hơn); 0 = đỉnh đơn
        self.la = tuple(la) if la else None   # (a, b): đỉnh bất đối xứng LA(a,b) cho kim loại; None = GL(30) đối xứng
        self.ti_le = ti_le        # tỉ lệ diện tích đỉnh thứ hai / đỉnh chính (cùng FWHM), ví dụ 3d: 2/3, 2p: 1/2, 4f: 3/4

    def dict(self):
        return dict(self.__dict__)


# Cửa sổ hoá học mặc định (sau hiệu chuẩn C-C = 284.8 eV). Tài liệu chuẩn: C1s hữu cơ/cacbon.
MAU_C1S = [
    ThanhPhan("C-C / C=C / C-H", 284.8, 284.70, 284.90, 1.2, 0.80, 1.60, "chuẩn năng lượng (284.8 eV)"),
    ThanhPhan("C-O", 286.3, 285.80, 286.90, 1.5, 1.00, 2.00, "C-OH, C-O-C (+1.2...+2.0 eV)"),
    ThanhPhan("O-C=O", 288.5, 287.90, 289.30, 1.3, 0.90, 1.80, "cacboxyl/este/cacboxylat (+3.2...+4.5 eV)"),
]
UNG_VIEN_C1S = [   # chỉ thêm nếu cải thiện có ý nghĩa
    ThanhPhan("C=O", 287.6, 287.20, 288.10, 1.3, 0.90, 1.80, "cacbonyl/amit (+2.4...+3.3 eV)"),
    ThanhPhan("pi-pi* shake-up", 290.8, 290.20, 291.60, 2.0, 1.20, 3.50, "cacbon graphit/thơm (+5.4...+6.8 eV)"),
]
MAU_O1S = [
    ThanhPhan("O mạng (M-O)", 529.8, 529.0, 530.6, 1.2, 0.8, 1.6, "oxit kim loại"),
    ThanhPhan("OH / C=O / O defect", 531.4, 530.8, 532.0, 1.6, 1.0, 2.2, "hiđroxyl, cacbonyl, khuyết O"),
    ThanhPhan("C-O / H2O hấp phụ", 532.8, 532.2, 533.8, 1.8, 1.0, 2.4, "C-O, nước hấp phụ"),
]
MAU_N1S = [
    ThanhPhan("N pyridinic", 398.5, 398.0, 399.1, 1.3, 1.0, 1.7, "N pyridin (~398.5 eV)"),
    ThanhPhan("N pyrrolic / amin", 400.1, 399.5, 400.6, 1.4, 1.0, 1.8, "pyrrol, amin, amit (~400 eV)"),
    ThanhPhan("N graphitic / quaternary", 401.2, 400.7, 401.8, 1.4, 1.0, 1.8, "N thế chỗ trong mạng cacbon (~401 eV)"),
]
UNG_VIEN_N1S = [ThanhPhan("N-oxit", 403.5, 402.8, 404.6, 1.6, 1.0, 2.2, "N-O (~403-404 eV)")]
MAU_TI2P = [   # doublet 2p3/2 + 2p1/2: tách 5.7 eV, tỉ lệ diện tích 1:2 (0.5)
    ThanhPhan("Ti4+ (TiO2)", 458.8, 458.4, 459.2, 1.1, 0.8, 1.5, "Ti 2p3/2 của TiO2", tach=5.7, ti_le=0.5),
]
UNG_VIEN_TI2P = [ThanhPhan("Ti3+", 457.4, 456.8, 458.0, 1.3, 0.9, 1.8, "Ti2O3/khuyết O", tach=5.7, ti_le=0.5)]
MAU_S2P = [   # doublet 2p3/2 + 2p1/2: tách 1.18 eV, tỉ lệ 1:2
    ThanhPhan("S 2p (C-S / S2-)", 163.9, 163.3, 164.6, 1.0, 0.7, 1.4, "thiol, sunfua", tach=1.18, ti_le=0.5),
]
UNG_VIEN_S2P = [ThanhPhan("SOx / sunfat", 168.5, 167.5, 169.5, 1.4, 1.0, 1.9, "sunfat, sunfit", tach=1.18, ti_le=0.5)]
MAU_RU3D = [   # vùng chồng lấn Ru 3d + C 1s; Ru 3d: tách 4.17 eV, tỉ lệ 3d3/2 : 3d5/2 = 2:3
    ThanhPhan("C-C / C=C / C-H", 284.8, 284.70, 284.90, 1.2, 0.80, 1.60, "chuẩn năng lượng (284.8 eV)"),
    ThanhPhan("C-O", 286.3, 285.80, 286.90, 1.5, 1.00, 2.00, "C-O"),
    ThanhPhan("Ru0 3d", 280.0, 279.7, 280.4, 1.0, 0.7, 1.4, "Ru kim loại (3d5/2 280.0 eV; 3d3/2 chồng C-C)", tach=4.17, ti_le=0.667),
    ThanhPhan("RuO2 3d", 280.8, 280.4, 281.4, 1.4, 1.0, 1.9, "RuO2 (3d5/2 ~280.8 eV)", tach=4.17, ti_le=0.667),
]
MAU_AU4F = [   # kim loại: đỉnh bất đối xứng LA; 4f7/2 = 84.0 eV, tách 3.67 eV, tỉ lệ 4f5/2 : 4f7/2 = 3:4. Tham số LA chỉ là điểm xuất phát
    ThanhPhan("Au0 4f", 84.0, 83.8, 84.2, 0.8, 0.6, 1.1, "Au kim loại (hiệu chuẩn về 84.0 eV)", tach=3.67, ti_le=0.75, la=(1.8, 1.0)),
]
MAU = {"C1s": (MAU_C1S, UNG_VIEN_C1S), "O1s": (MAU_O1S, []), "N1s": (MAU_N1S, UNG_VIEN_N1S),
       "Ti2p": (MAU_TI2P, UNG_VIEN_TI2P), "S2p": (MAU_S2P, UNG_VIEN_S2P), "Ru3d+C1s": (MAU_RU3D, []),
       "Au4f": (MAU_AU4F, [])}
# (vùng fit từ, đến, khoảng dò đỉnh hiệu chuẩn hoặc None, dùng C-C để hiệu chuẩn)
# Thiết lập theo mẫu: vùng fit, khoảng dò đỉnh hiệu chuẩn, năng lượng chuẩn + tên thành phần chuẩn (None = dùng dịch có sẵn từ C1s)
VUNG_MAU = {
    "C1s": {"vung": (281.5, 291.0), "khoang": (290.0, 280.0), "ref": 284.8, "ten_ref": "C-C"},
    "O1s": {"vung": (527.0, 536.0), "khoang": None, "ref": None, "ten_ref": None},
    "N1s": {"vung": (395.0, 406.0), "khoang": None, "ref": None, "ten_ref": None},
    "Ti2p": {"vung": (454.0, 468.0), "khoang": None, "ref": None, "ten_ref": None},
    "S2p": {"vung": (160.0, 172.0), "khoang": None, "ref": None, "ten_ref": None},
    "Ru3d+C1s": {"vung": (277.0, 292.0), "khoang": (286.5, 283.0), "ref": 284.8, "ten_ref": "C-C"},
    "Au4f": {"vung": (80.0, 92.0), "khoang": (86.0, 82.0), "ref": 84.0, "ten_ref": "Au0"},
}


# ====================== FIT ======================
def _anh_xa(u, lo, hi):
    return lo + (hi - lo) * 0.5 * (1.0 + np.sin(u))


def _anh_xa_nguoc(x, lo, hi):
    t = 2.0 * (np.clip(x, lo, hi) - lo) / max(hi - lo, 1e-12) - 1.0
    return math.asin(max(-1.0, min(1.0, t)))


def _lm(f, u0, so_buoc=300):
    u = np.array(u0, float)
    r = f(u)
    c = float(r @ r)
    lam = 1e-2
    for _ in range(so_buoc):
        J = np.empty((len(r), len(u)))
        for j in range(len(u)):
            h = 1e-6
            up = u.copy()
            up[j] += h
            J[:, j] = (f(up) - r) / h
        A, g = J.T @ J, J.T @ r
        tot = False
        for _ in range(20):
            try:
                du = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), g)
            except np.linalg.LinAlgError:
                lam *= 10
                continue
            r2 = f(u + du)
            c2 = float(r2 @ r2)
            if c2 < c:
                tot = True
                break
            lam *= 4.0
        if not tot:
            break
        giam = c - c2
        u, r, c, lam = u + du, r2, c2, max(lam / 3.0, 1e-12)
        if giam < 1e-12 * max(c, 1e-30):
            break
    return u, c


def uoc_luong_kappa(y):
    """Hệ số kappa trong mô hình nhiễu sigma^2 = kappa * y (Poisson: kappa = 1/(dwell x số scan)), ước lượng bền vững từ sai phân
    bậc 2 của chính dữ liệu (nhiễu trắng: Var(d2) = 6 sigma^2)."""
    y = np.asarray(y, float)
    d2 = np.diff(y, 2)
    yc = np.maximum(y[1:-1], 1e-9)
    z = d2 / np.sqrt(6.0 * yc)
    mad = np.median(np.abs(z - np.median(z)))
    return float((1.4826 * mad) ** 2)


def residual_std(res, y_tho, t_thu=None, k_tham_so=0, be=None):
    """Residual STD kiểu CasaXPS: căn trung bình bình phương (sai số / nhiễu kỳ vọng). Nhiễu kỳ vọng là Poisson:
    sigma_CPS = sqrt(y/t) với t = dwell x số scan (giây); không biết t thì ước lượng kappa = 1/t từ chính dữ liệu."""
    res = np.asarray(res, float)
    y_tho = np.asarray(y_tho, float)
    n = len(res)
    kappa = (1.0 / t_thu) if (t_thu and t_thu > 0) else uoc_luong_kappa(y_tho)
    sig2 = np.maximum(y_tho, 1e-9) * kappa
    chi = float(np.sum(res ** 2 / np.maximum(sig2, 1e-30)))
    return math.sqrt(chi / max(n - k_tham_so, 1))


def tu_tuong_quan(res):
    r = np.asarray(res, float) - np.mean(res)
    den = float(r @ r)
    return float(r[:-1] @ r[1:] / den) if den > 0 else 0.0


def khop(be, y_tru_nen, thanh_phan, m=HE_SO_GL, so_lan=6, hat=0, y_tho=None, t_thu=None, dw_fwhm=DW_FWHM):
    """Fit nhiều thành phần GL(m) lên y đã trừ nền, bằng LM có biên (đổi biến sin). Nhiều điểm xuất phát, lấy SSR nhỏ nhất.
    Trả về dict: thanh_phan (vị trí, FWHM, chiều cao, diện tích, %), mo_hinh, phan_du, rstd, ..."""
    be = np.asarray(be, float)
    y = np.asarray(y_tru_nen, float)
    tp = list(thanh_phan)
    k = len(tp)
    ymax = max(float(np.max(y)), 1e-9)
    gioi_han = []
    for c in tp:
        gioi_han += [(0.0, 1.5 * ymax), (c.vt_lo, c.vt_hi), (c.w_lo, c.w_hi)]

    def xay(u):
        return np.array([_anh_xa(u[i], *gioi_han[i]) for i in range(len(u))])

    def dang(i, p):
        c = tp[i]
        v = hinh(be, p[3 * i + 1], p[3 * i + 2], c, m)
        if c.tach > 0 and c.ti_le > 0:                       # doublet: đỉnh thứ hai cùng FWHM, tách và tỉ lệ cố định
            v = v + c.ti_le * hinh(be, p[3 * i + 1] + c.tach, p[3 * i + 2], c, m)
        return p[3 * i] * v

    def mo_hinh(p):
        s = np.zeros_like(be)
        for i in range(k):
            s += dang(i, p)
        return s

    tuy = [i for i, c in enumerate(tp) if not re.search(r"shake|pi-pi|satell|\u03c0", c.ten, re.I)]
    he_pen = 50.0 * ymax

    def f(u):
        p = xay(u)
        r = y - mo_hinh(p)
        if dw_fwhm and dw_fwhm > 0 and len(tuy) > 1:           # ràng buộc mềm: FWHM các thành phần chênh nhau <= dw_fwhm
            w = np.array([p[3 * i + 2] for i in tuy])
            vuot = np.maximum(np.abs(w - np.median(w)) - dw_fwhm / 2.0, 0.0)
            r = np.concatenate([r, he_pen * vuot])
        return r

    rng = np.random.default_rng(hat)
    tot_nhat = None
    for lan in range(so_lan):
        x0 = []
        for c in tp:
            h0 = max(float(np.interp(c.vt, be, y)), 0.02 * ymax)
            vt = c.vt + (0 if lan == 0 else rng.normal(0, 0.15)) * (c.vt_hi - c.vt_lo)
            w = c.w0 * (1.0 if lan == 0 else rng.uniform(0.8, 1.2))
            x0 += [h0 * (1.0 if lan == 0 else rng.uniform(0.5, 1.5)), vt, w]
        u0 = [_anh_xa_nguoc(x0[i], *gioi_han[i]) for i in range(3 * k)]
        u, c2 = _lm(f, u0)
        if tot_nhat is None or c2 < tot_nhat[1]:
            tot_nhat = (u, c2)
    p = xay(tot_nhat[0])
    thanh = []
    tong_dt = 0.0
    cac = []
    for i, c in enumerate(tp):
        thanh_i = dang(i, p)
        dt = float(_trapz(thanh_i, be))
        cac.append(thanh_i)
        tong_dt += dt
        thanh.append({"ten": c.ten, "vt": float(p[3 * i + 1]), "fwhm": float(p[3 * i + 2]), "cao": float(p[3 * i]), "dt": dt,
                      "tach": c.tach, "ti_le": c.ti_le, "la": c.la, "o_bien": _o_bien(p, i, gioi_han)})
    for t_ in thanh:
        t_["pct"] = 100.0 * t_["dt"] / tong_dt if tong_dt > 0 else 0.0
    mo = np.sum(cac, axis=0)
    phan_du = y - mo
    ytho = y_tho if y_tho is not None else y
    rs = residual_std(phan_du, ytho, t_thu, 3 * k, be)
    return {"thanh_phan": thanh, "cac": cac, "mo_hinh": mo, "phan_du": phan_du, "rstd": rs,
            "tu_tuong_quan": tu_tuong_quan(phan_du), "ssr": float(phan_du @ phan_du), "so_tham_so": 3 * k}


def _o_bien(p, i, gh, dung_sai=0.05):
    """Thông số nào chạm biên (so với bề rộng cửa sổ) - dấu hiệu ràng buộc đang quyết định kết quả."""
    kq = []
    for j, ten in ((1, "vị trí"), (2, "FWHM")):
        lo, hi = gh[3 * i + j]
        x = p[3 * i + j]
        if x - lo < dung_sai * (hi - lo) or hi - x < dung_sai * (hi - lo):
            kq.append(ten)
    return kq


# ====================== QUY TRÌNH HOÀN CHỈNH ======================
def phan_tich_pho(be, y, mau="C1s", tp=None, ung_vien=None, vung=(281.5, 291.0), dich_chuan=284.8, khoang_do=(290.0, 280.0),
                  nen="shirley", t_thu=None, m=HE_SO_GL, tu_chon=True, tp_chuan_theo="C-C", dw_fwhm=DW_FWHM, dich_san=None, tu_chinh=True, rstd_dich=1.0):
    """Hiệu chuẩn -> cắt vùng -> nền -> fit -> (tuỳ chọn) thêm thành phần ứng viên có kiểm định -> hiệu chuẩn lại theo thành phần C-C.
    Trả về dict kết quả (energies đã hiệu chuẩn)."""
    be, y = _sap_xep(be, y)
    if tu_chinh and t_thu:
        # bước 1: fit thường (đã nới cửa sổ vị trí/FWHM nếu cần); bước 2: nếu Residual STD vẫn xa đích, thử vài biên vùng fit
        kq0 = phan_tich_pho(be, y, mau, tp, ung_vien, vung, dich_chuan, khoang_do, nen, t_thu, m, tu_chon, tp_chuan_theo, dw_fwhm, dich_san,
                            tu_chinh=False, rstd_dich=rstd_dich)
        _tu_chinh_cua_so(kq0, m, t_thu, dw_fwhm, rstd_dich, tp_chuan_theo)
        if kq0["fit"]["rstd"] <= rstd_dich + 0.08:
            return kq0
        tot = kq0
        for lo in (vung[0], vung[0] + 0.5, vung[0] - 1.0):
            for hi in (vung[1], vung[1] + 2.0):
                if (lo, hi) == tuple(vung) or lo > 282.0 or hi - lo < 8.0:
                    continue
                try:
                    k = phan_tich_pho(be, y, mau, tp, ung_vien, (lo, hi), dich_chuan, khoang_do, nen, t_thu, m, False, tp_chuan_theo, dw_fwhm,
                                      dich_san, tu_chinh=False, rstd_dich=rstd_dich)
                except ValueError:
                    continue
                if abs(k["fit"]["rstd"] - rstd_dich) < abs(tot["fit"]["rstd"] - rstd_dich) - 1e-3 and not any(c["o_bien"] for c in k["fit"]["thanh_phan"]):
                    tot = k
        if tot is not kq0:
            vg = tot["tham_so_fit"]["vung"]
            tot = phan_tich_pho(be, y, mau, tp, ung_vien, vg, dich_chuan, khoang_do, nen, t_thu, m, tu_chon, tp_chuan_theo, dw_fwhm, dich_san,
                                tu_chinh=False, rstd_dich=rstd_dich)
            _tu_chinh_cua_so(tot, m, t_thu, dw_fwhm, rstd_dich, tp_chuan_theo)
            tot["ghi"] = list(tot.get("ghi", [])) + [f"Tự chỉnh vùng fit {tuple(vung)} -> ({tot['tham_so_fit']['vung'][0]:g}, {tot['tham_so_fit']['vung'][1]:g}) eV: "
                                                      f"Residual STD {kq0['fit']['rstd']:.2f} -> {tot['fit']['rstd']:.2f} (đích ~{rstd_dich:g}); không thêm đỉnh."]
        return tot
    if tp is None:
        tp = [ThanhPhan(**c.dict()) for c in MAU[mau][0]]
    if ung_vien is None:
        ung_vien = [ThanhPhan(**c.dict()) for c in MAU.get(mau, ([], []))[1]]
    uv_goc = [ThanhPhan(**c.dict()) for c in ung_vien]
    if dich_san is not None:                      # dịch đã biết (từ vùng C1s cùng mẫu): không tự dò đỉnh
        d1, be1 = float(dich_san), be + float(dich_san)
        tp_chuan_theo = None
    else:
        d1, be1 = hieu_chuan(be, y, dich_chuan, khoang_do)
    dich_tong = d1
    ket_qua = None
    ghi_tong = []
    for vong in range(2):
        mk = (be1 >= vung[0]) & (be1 <= vung[1])
        if mk.sum() < 20:
            raise ValueError("Vùng fit quá hẹp hoặc nằm ngoài dữ liệu.")
        b, yy = be1[mk], y[mk]
        nen_y = nen_theo(nen, b, yy)
        ys = yy - nen_y
        fit = khop(b, ys, tp, m, y_tho=yy, t_thu=t_thu, dw_fwhm=dw_fwhm)
        ghi = []
        if tu_chon and ung_vien:
            hien = list(tp)
            for uv in ung_vien:
                th = hien + [uv]
                f2 = khop(b, ys, th, m, y_tho=yy, t_thu=t_thu, dw_fwhm=dw_fwhm)
                moi = f2["thanh_phan"][-1]
                t_le = moi["pct"]
                n_d = len(b)
                dfd = max(n_d - f2["so_tham_so"], 1)
                F = ((fit["ssr"] - f2["ssr"]) / 3.0) / max(f2["ssr"] / dfd, 1e-30)
                lech = list(moi["o_bien"])
                if F >= F_TOI_HAN and t_le >= 1.0 and not lech:
                    hien, fit = th, f2
                    ghi.append(f"Thêm '{uv.ten}': F = {F:.1f} (>= {F_TOI_HAN:g}, p < 0.01), chiếm {t_le:.1f}% diện tích, nằm trong cửa sổ hoá học.")
                else:
                    ly_do = (f"F = {F:.1f} < {F_TOI_HAN:g}: cải thiện không có ý nghĩa" if F < F_TOI_HAN
                             else "diện tích < 1%" if t_le < 1.0 else "chạm biên ràng buộc")
                    ghi.append(f"Không thêm '{uv.ten}' ({ly_do}).")
            tp_dung = hien
        else:
            tp_dung = tp
        ghi_tong = ghi_tong + ghi
        ket_qua = {"be": b, "y": yy, "nen": nen_y, "ys": ys, "fit": fit, "tp": tp_dung, "ghi": ghi_tong}
        # hiệu chuẩn lại để thành phần chuẩn (C-C) nằm đúng dich_chuan
        ref = next((c for c in fit["thanh_phan"] if tp_chuan_theo and tp_chuan_theo in c["ten"]), None)
        if vong == 0 and ref is not None and abs(ref["vt"] - dich_chuan) > 0.01:
            d2 = dich_chuan - ref["vt"]
            be1 = be1 + d2
            dich_tong += d2
            tp = tp_dung
            ung_vien = []
            continue
        break
    if tu_chinh and t_thu:
        _tu_chinh_cua_so(ket_qua, m, t_thu, dw_fwhm, rstd_dich, tp_chuan_theo)
    ket_qua["dich_hieu_chuan"] = dich_tong
    ket_qua["be_day_du"] = be1
    ket_qua["y_day_du"] = y
    ket_qua["tham_so_fit"] = {"t_thu": t_thu, "m": m, "nen": nen, "dw": dw_fwhm, "vung": tuple(vung), "ung_vien": uv_goc}
    ket_qua["canh_bao"] = danh_gia(ket_qua)
    return ket_qua


def _tu_chinh_cua_so(kq, m, t_thu, dw, rstd_dich, ref_ten, dung_sai=0.08):
    """Residual STD > đích (~1): nới dần cửa sổ vị trí (Pos. Constr.) và FWHM của các thành phần KHÔNG phải thành phần chuẩn,
    theo từng bước nhỏ quanh giá trị danh định (tối đa ±1.0 eV như Casa, FWHM tới 2.6 eV), dừng ngay khi Residual STD <= đích + dung_sai.
    Không thêm đỉnh nào; nếu nới hết mà chưa đạt thì giữ phương án tốt nhất và ghi rõ."""
    f0 = kq["fit"]
    if f0["rstd"] <= rstd_dich + dung_sai:
        return
    b, ys, yy = kq["be"], kq["ys"], kq["y"]
    tp0 = kq["tp"]
    tot = (f0["rstd"], tp0, f0)
    for buoc in (0.25, 0.5, 0.75, 1.0):
        tp1 = []
        for c in tp0:
            d = ThanhPhan(**c.dict())
            if not (ref_ten and ref_ten in d.ten):
                d.vt_lo = min(d.vt_lo, c.vt - buoc)
                d.vt_hi = max(d.vt_hi, c.vt + buoc)
                d.w_hi = max(d.w_hi, min(2.6, c.w_hi + 0.6 * buoc * 2))
            tp1.append(d)
        f1 = khop(b, ys, tp1, m, y_tho=yy, t_thu=t_thu, dw_fwhm=dw)
        if abs(f1["rstd"] - rstd_dich) < abs(tot[0] - rstd_dich) and f1["rstd"] > 0.0:
            tot = (f1["rstd"], tp1, f1)
        if f1["rstd"] <= rstd_dich + dung_sai:
            break
    if tot[2] is not f0:
        kq["fit"], kq["tp"] = tot[2], tot[1]
        kq["ghi"] = list(kq.get("ghi", [])) + [f"Tự chỉnh cửa sổ vị trí/FWHM (Pos. Constr.): Residual STD {f0['rstd']:.2f} -> {tot[0]:.2f} "
                                              f"(đích ~{rstd_dich:g}); không thêm đỉnh, chỉ nới ràng buộc tối đa ±1 eV quanh giá trị danh định."]
    else:
        kq["ghi"] = list(kq.get("ghi", [])) + ["Tự chỉnh cửa sổ vị trí/FWHM: nới ràng buộc không cải thiện thêm Residual STD."]


# ====================== ĐỐI CHIẾU VỚI CASA ======================
def doc_casa_ghi_chu(ghi_chu, hv):
    """Đọc vùng/nền/thành phần mà CasaXPS đã lưu trong chú thích khối .vms (dòng 'CASA region' / 'CASA comp').
    Trả về dict(nen, vung_ke=(E1,E2), vung_be=(lo,hi) theo thang BE chưa hiệu chuẩn của Casa, thanh_phan=[dict(ten, dang, dien_tich, fwhm, vt_be, vt_be_lo, vt_be_hi, fwhm_lo, fwhm_hi)])
    hoặc None nếu khối chưa có fit Casa. Số này do chính Casa tính nên là số 'chuẩn' để đối chiếu."""
    reg = comp = None
    cs = []
    for t in ghi_chu or []:
        t = t.strip()
        m = re.match(r"CASA region \(\*(.*?)\*\) \(\*(.*?)\*\)\s+(\S+)\s+(\S+)", t, re.I)
        if m:
            reg = (m.group(2), float(m.group(3)), float(m.group(4)))
            continue
        m = re.match(r"CASA comp \(\*(.*?)\*\) \(\*(.*?)\*\)\s+Area\s+(\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+MFWHM\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+\S+\s+Position\s+(\S+)\s+(\S+)\s+(\S+)", t, re.I)
        if m:
            g = [float(x) for x in m.groups()[2:]]
            cs.append({"ten": m.group(1), "dang": m.group(2), "dien_tich": g[0], "fwhm": g[1], "fwhm_lo": g[2], "fwhm_hi": g[3],
                       "vt_be": hv - g[4], "vt_be_lo": hv - g[6], "vt_be_hi": hv - g[5]})
    if not reg or not cs:
        return None
    return {"nen": reg[0], "vung_ke": (reg[1], reg[2]), "vung_be": (hv - reg[2], hv - reg[1]), "thanh_phan": cs}


def fit_kieu_casa(be_tho, y_cps, vung_be, t_thu, bat_dau, n_tb=2, m=HE_SO_GL, dv_vt=1.0):
    """Fit theo cách CasaXPS làm: dữ liệu thô ở thang BE CHƯA hiệu chuẩn, vùng = vùng Casa, nền Shirley, GL(m), vị trí ±dv_vt eV quanh giá trị
    bắt đầu, FWHM trong [0.3, 4] x giá trị bắt đầu, KHÔNG ràng buộc FWHM giữa các đỉnh, Marquardt cục bộ từ đúng giá trị bắt đầu,
    sai số Poisson sigma = sqrt(CPS/t). bat_dau = [(ten, vt_be, fwhm)]. Trả về dict(rstd, thanh_phan, n, bac_tu_do)."""
    from scipy.optimize import least_squares
    be_tho, y_cps = _sap_xep(be_tho, y_cps)
    mk = (be_tho >= vung_be[0] - 1e-6) & (be_tho <= vung_be[1] + 1e-6)
    b, yy = be_tho[mk], y_cps[mk]
    ys = yy - shirley(b, yy, n_tb=n_tb)
    sig = np.sqrt(np.maximum(yy, 1e-9) / t_thu)
    k = len(bat_dau)
    x0, lb, ub = [], [], []
    for ten, vt, w in bat_dau:
        x0 += [max(float(np.interp(vt, b, ys)), 1.0), vt, w]
        lb += [0.0, vt - dv_vt, 0.3 * w]
        ub += [np.inf, vt + dv_vt, 4.0 * w]
    cao = [float(np.max(ys))] * k
    ub = [cao[i // 3] * 3 if j == 0 else u for i, (j, u) in enumerate(zip([0, 1, 2] * k, ub))]

    def mo(q):
        return sum(q[3 * i] * gl(b, q[3 * i + 1], q[3 * i + 2], m) for i in range(k))
    r = least_squares(lambda q: (mo(q) - ys) / sig, x0, bounds=(lb, ub), x_scale=[1000.0, 0.1, 0.1] * k)
    q = r.x
    xx = np.arange(-30, 30, 0.002)
    dem = [float(np.sum(gl(xx, 0, q[3 * i + 2], m)) * 0.002) for i in range(k)]
    ar = [q[3 * i] * dem[i] for i in range(k)]
    tong = sum(ar) or 1.0
    bt = len(b) - 3 * k
    return {"rstd": float(np.sqrt(np.sum(r.fun ** 2) / max(bt, 1))), "n": len(b), "bac_tu_do": bt, "vung_be": (float(b[0]), float(b[-1])),
            "thanh_phan": [{"ten": bat_dau[i][0], "vt_be": float(q[3 * i + 1]), "fwhm": float(q[3 * i + 2]), "dien_tich": float(ar[i]),
                            "pct": 100.0 * ar[i] / tong} for i in range(k)]}


def so_sanh_casa(khoi, kq_app=None, n_tb=2):
    """Văn bản đối chiếu cho một khối .vms: (1) số do Casa đã lưu trong file (nếu có), (2) fit kiểu Casa tính lại bằng app từ vùng/giá trị bắt đầu
    của Casa (hoặc mặc định C1s), (3) fit đã hiệu chuẩn của app. Thang BE của (1)(2) là thang Casa (chưa hiệu chuẩn)."""
    L = []
    t_thu = (khoi.get("dwell") or 0) * (khoi.get("scans") or 0)
    hv = khoi.get("hv") or 1486.6
    # be của khối đã đổi sang BE = hv - KE (thang Casa, chưa hiệu chuẩn)
    be, y = khoi["be"], khoi["y"]
    cs = doc_casa_ghi_chu(khoi.get("ghi_chu_casa"), hv)
    if cs:
        L += [f"(1) SỐ CASA ĐÃ LƯU TRONG FILE  (nền {cs['nen']}, vùng BE {cs['vung_be'][0]:.2f}-{cs['vung_be'][1]:.2f} eV, thang Casa chưa hiệu chuẩn)",
              f"    {'Thành phần':<18}{'BE':>9}{'FWHM':>8}{'Diện tích':>11}"]
        for c in cs["thanh_phan"]:
            L.append(f"    {c['ten']:<18}{c['vt_be']:>9.3f}{c['fwhm']:>8.3f}{c['dien_tich']:>11.1f}")
        L.append("    (đây là số do chính Casa tính; muốn app hiện đúng như Casa: fit trong Casa rồi File > Save, mở file đó trong app)")
        vung = cs["vung_be"]
        bd = [(c["ten"], c["vt_be"], c["fwhm"]) for c in cs["thanh_phan"]]
    else:
        L.append("(1) File chưa có fit lưu bởi Casa. Trong Casa: tạo vùng + thành phần, fit, rồi File > Save để app lấy được số Casa.")
        vung = None
        bd = None
    if t_thu <= 0:
        return "\n".join(L + ["", "Thiếu dwell x scan nên không tính lại kiểu Casa."])
    if vung is None and kq_app:
        d = kq_app.get("dich_hieu_chuan", 0.0)
        vung = (kq_app["be"].min() - d, kq_app["be"].max() - d)
        bd = [(c["ten"], c["vt"] - d, c["fwhm"]) for c in kq_app["fit"]["thanh_phan"]]
    if vung is not None and bd:
        f = fit_kieu_casa(be, y, vung, t_thu, bd, n_tb=n_tb)
        L += ["", f"(2) APP TÍNH LẠI KIỂU CASA  (cùng vùng {f['vung_be'][0]:.2f}-{f['vung_be'][1]:.2f} eV, {f['n']} điểm, Shirley, GL(30), không buộc FWHM, "
                  f"vị trí ±1 eV, FWHM 0.3-4x giá trị đầu)", f"    Residual STD = {f['rstd']:.4f}   bậc tự do = {f['bac_tu_do']}",
              f"    {'Thành phần':<18}{'BE':>9}{'FWHM':>8}{'Diện tích':>11}{'%':>7}"]
        for c in f["thanh_phan"]:
            L.append(f"    {c['ten']:<18}{c['vt_be']:>9.3f}{c['fwhm']:>8.3f}{c['dien_tich']:>11.1f}{c['pct']:>7.2f}")
        if cs:
            L.append("    Lệch so với (1): " + ", ".join(f"{a['ten']}: diện tích {100 * (b2['dien_tich'] / a['dien_tich'] - 1):+.1f}%"
                                                          for a, b2 in zip(cs["thanh_phan"], f["thanh_phan"]) if a["dien_tich"]))
    L += ["", "LƯU Ý: C-C và C-O chồng nhau nhiều nên đáy hàm sai số rất phẳng; chỉ cần lệch 0.05 eV ở biên vùng fit hoặc khác cách lấy đầu nền Shirley",
          "là diện tích đổi vài %. Muốn trùng Casa tuyệt đối hãy dùng số ở mục (1) (Casa tự lưu) hoặc cùng vùng/nền như Casa."]
    return "\n".join(L)


def kq_tu_casa(khoi, t_thu, dich_chuan=284.8, ten_ref="C-C", m=HE_SO_GL, n_tb=2):
    """Dựng kết quả của app TỪ SỐ CASA đã lưu trong khối .vms (vùng, vị trí, FWHM, diện tích do chính Casa fit). Vị trí/diện tích/FWHM giữ
    nguyên số Casa (chỉ cộng dịch hiệu chuẩn để C-C về dich_chuan); app vẽ, tính phần dư, Residual STD và cho 'Chứng minh' trên mô hình đó.
    Trả về dict cùng dạng phan_tich_pho, hoặc None nếu khối không có fit Casa."""
    hv = khoi.get("hv") or 1486.6
    cs = doc_casa_ghi_chu(khoi.get("ghi_chu_casa"), hv)
    if not cs:
        return None
    ref = next((c for c in cs["thanh_phan"] if ten_ref and ten_ref.lower() in c["ten"].lower()), cs["thanh_phan"][0])
    dich = 0.0 if dich_chuan is None else dich_chuan - ref["vt_be"]       # dich_chuan=None: giữ BE đúng như Casa, không ép C-C về chuẩn
    be, y = _sap_xep(khoi["be"], khoi["y"])
    be1 = be + dich
    lo, hi = cs["vung_be"][0] + dich, cs["vung_be"][1] + dich
    mk = (be1 >= lo - 1e-6) & (be1 <= hi + 1e-6)
    if mk.sum() < 20:
        raise ValueError("Vùng Casa nằm ngoài dữ liệu.")
    b, yy = be1[mk], y[mk]
    nen = shirley(b, yy, n_tb=n_tb) if "shirley" in cs["nen"].lower() else tuyen_tinh(b, yy)
    ys = yy - nen
    xx = np.arange(-30, 30, 0.002)
    cac, thanh, tp = [], [], []
    for c in cs["thanh_phan"]:
        w, vt = c["fwhm"], c["vt_be"] + dich
        cao = c["dien_tich"] / max(float(np.sum(gl(xx, 0, w, m)) * 0.002), 1e-12)
        cac.append(cao * gl(b, vt, w, m))
        thanh.append({"ten": c["ten"], "vt": vt, "fwhm": w, "cao": cao, "dt": c["dien_tich"], "tach": 0.0, "ti_le": 0.0, "la": None, "o_bien": []})
        tp.append(ThanhPhan(c["ten"], vt, vt - 0.3, vt + 0.3, w, max(w - 0.3, 0.2), w + 0.3, "số từ Casa"))
    tong = sum(t_["dt"] for t_ in thanh) or 1.0
    for t_ in thanh:
        t_["pct"] = 100.0 * t_["dt"] / tong
    mo = np.sum(cac, axis=0)
    pd_ = ys - mo
    k = len(thanh)
    fit = {"thanh_phan": thanh, "cac": cac, "mo_hinh": mo, "phan_du": pd_, "rstd": residual_std(pd_, yy, t_thu, 3 * k, b),
           "tu_tuong_quan": tu_tuong_quan(pd_), "ssr": float(pd_ @ pd_), "so_tham_so": 3 * k}
    kq = {"be": b, "y": yy, "nen": nen, "ys": ys, "fit": fit, "tp": tp,
          "ghi": ["SỐ LẤY TRỰC TIẾP TỪ CASA (vị trí, FWHM, diện tích do Casa fit); app tính lại phần dư/Residual STD (nền Shirley của app, có thể lệch nhẹ so với Casa) và dùng cho báo cáo, chứng minh."],
          "dich_hieu_chuan": dich, "be_day_du": be1, "y_day_du": y,
          "tham_so_fit": {"t_thu": t_thu, "m": m, "nen": "shirley" if "shirley" in cs["nen"].lower() else "tuyen_tinh", "dw": DW_FWHM,
                          "vung": (lo, hi), "ung_vien": [], "tu_casa": True}}
    kq["canh_bao"] = danh_gia(kq)
    return kq


def danh_gia(kq):
    """Nhận xét trung thực về chất lượng fit - không ép Residual STD về 1 bằng cách thêm đỉnh vô nghĩa."""
    f = kq["fit"]
    cb = []
    if f["rstd"] > 1.5:
        cb.append(f"Residual STD = {f['rstd']:.2f} (> 1.5): mô hình chưa mô tả hết dữ liệu. Không nên thêm đỉnh chỉ để giảm số này; "
                  "kiểm tra vùng nền, đỉnh chồng lấn (ví dụ Ru 3d3/2 ở ~284 eV nếu có Ru kim loại), hoặc phổ có điện tích/nhiễu hệ thống.")
    elif f["rstd"] < 0.8:
        cb.append(f"Residual STD = {f['rstd']:.2f} (< 0.8): có thể thừa tham số hoặc ước lượng nhiễu quá lớn - kiểm tra lại giá trị dwell x scan.")
    if abs(f["tu_tuong_quan"]) > 0.35:
        cb.append(f"Phần dư còn cấu trúc (tự tương quan {f['tu_tuong_quan']:.2f}): có thể còn thiếu thành phần hoặc nền chưa hợp lý.")
    for c in f["thanh_phan"]:
        if c["o_bien"]:
            cb.append(f"'{c['ten']}': {', '.join(c['o_bien'])} chạm biên ràng buộc - giá trị do ràng buộc quyết định, cần cân nhắc.")
        if c["fwhm"] < 0.55:
            cb.append(f"'{c['ten']}': FWHM = {c['fwhm']:.2f} eV nhỏ hơn mức phân giải thực tế của máy (thường >= 0.5-0.7 eV với Al Kα đơn sắc) - không hợp lý vật lý.")
        if c["pct"] < 1.0:
            cb.append(f"'{c['ten']}' chỉ {c['pct']:.1f}% diện tích - gần ngưỡng phát hiện, không nên diễn giải mạnh.")
    ws = [c["fwhm"] for c in f["thanh_phan"] if not re.search(r"shake|pi-pi|\u03c0", c["ten"], re.I)]
    if len(ws) > 1 and max(ws) - min(ws) > 0.6:
        cb.append(f"FWHM các thành phần chênh nhau {max(ws) - min(ws):.2f} eV: tài liệu khuyến nghị giữ trong ±10% hoặc ±0.1 eV "
                  "trừ khi có lý do hoá học (kim loại/asymmetric, shake-up).")
    cb.append("Lưu ý hiệu chuẩn: đưa C-C về 284.8 eV chỉ đáng tin khi cacbon bề mặt là cacbon ngoại lai (adventitious) và mẫu dẫn/"
              "trung hoà điện tích tốt; với mẫu có nền cacbon thật (graphene, polymer, hỗn hợp) hay mẫu dẫn điện nên hiệu chuẩn theo "
              "Fermi/Au 4f hoặc đỉnh kim loại, kẻo kết luận về dịch chuyển hoá học bị sai.")
    return cb


# ====================== XUẤT ======================
def ghi_csv_fit(duong, kq, ten=""):
    """CSV cho Origin: BE (đã hiệu chuẩn, giảm dần như phổ XPS), thô, nền, bao (nền + tổng thành phần), phần dư và từng thành phần
    (đã trừ nền: đáy = 0) để tô màu vùng."""
    b = kq["be"]
    o = np.argsort(-b)
    f = kq["fit"]
    tieu_de = ["BE_eV", "Raw_CPS", "Background", "Envelope_CPS", "Residual", "Envelope_sub"] + [c["ten"] for c in f["thanh_phan"]]
    with open(duong, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(tieu_de)
        for i in o:
            w.writerow([f"{b[i]:.4f}", f"{kq['y'][i]:.4f}", f"{kq['nen'][i]:.4f}", f"{kq['nen'][i] + f['mo_hinh'][i]:.4f}",
                        f"{f['phan_du'][i]:.4f}", f"{f['mo_hinh'][i]:.4f}"] + [f"{c[i]:.4f}" for c in f["cac"]])
    return duong


def duong_cong(kq, buoc=0.01, m=HE_SO_GL):
    """Đường cong mịn (bước buoc eV) của từng thành phần và đường bao, tính từ tham số đã fit - để vẽ đẹp, không bị gấp khúc."""
    b = kq["be"]
    x = np.arange(float(b.min()), float(b.max()) + buoc / 2, buoc)
    cac = []
    for c in kq["fit"]["thanh_phan"]:
        d = type("D", (), {"la": c.get("la")})
        v = hinh(x, c["vt"], c["fwhm"], d, m)
        if c.get("tach", 0) > 0 and c.get("ti_le", 0) > 0:
            v = v + c["ti_le"] * hinh(x, c["vt"] + c["tach"], c["fwhm"], d, m)
        cac.append(c["cao"] * v)
    return x, cac, np.sum(cac, axis=0)


def ghi_csv_muot(duong, kq):
    x, cac, bao = duong_cong(kq)
    o = np.argsort(-x)
    with open(duong, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["BE_eV", "Envelope_sub"] + [c["ten"] for c in kq["fit"]["thanh_phan"]])
        for i in o:
            w.writerow([f"{x[i]:.3f}", f"{bao[i]:.4f}"] + [f"{c[i]:.4f}" for c in cac])
    return duong


def ghi_csv_thanh_phan(duong, kq):
    with open(duong, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Thanh_phan", "Vi_tri_eV", "FWHM_eV", "Dien_tich_CPSeV", "Phan_tram", "Cham_bien"])
        for c in kq["fit"]["thanh_phan"]:
            w.writerow([c["ten"], f"{c['vt']:.3f}", f"{c['fwhm']:.3f}", f"{c['dt']:.2f}", f"{c['pct']:.2f}", ";".join(c["o_bien"])])
        w.writerow([])
        w.writerow(["Residual_STD", f"{kq['fit']['rstd']:.3f}"])
        w.writerow(["Dich_hieu_chuan_eV", f"{kq['dich_hieu_chuan']:+.3f}"])
    return duong


MAU_VE = ["#6baed6", "#fdd49e", "#fb9a8a", "#b2df8a", "#cab2d6", "#a6cee3"]


def ve_hinh(kq, duong, ten="", dpi=300, nhan_y=False, xlim=None, cho_xem=False, kieu=None):
    """Hình kiểu mẫu: vùng tô màu từng thành phần (đã trừ nền), đường bao xám đậm, trục BE đảo chiều, không vạch trục Y."""
    import matplotlib
    if not cho_xem:
        matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.2, 3.9))
    ve_len_truc(ax, kq, ten, nhan_y, xlim, kieu)
    fig.tight_layout()
    if duong:
        fig.savefig(duong, dpi=dpi)
    if not cho_xem:
        plt.close(fig)
    return fig


def ve_len_truc(ax, kq, ten="", nhan_y=False, xlim=None, kieu=None):
    b = kq["be"]
    x, cac, bao = duong_cong(kq)
    k = chuan_kieu(kieu, len(cac))
    for i, c in enumerate(cac):
        if k["to"][i]:                                     # tô vùng dưới đường (tuỳ chọn từng thành phần)
            ax.fill_between(x, 0, c, color=k["mau"][i], alpha=k["alpha"], lw=0, zorder=2 + i)
        else:
            ax.plot(x, c, color=k["mau"][i], lw=1.8, zorder=2 + i)
    if k["hien_diem"]:
        o = np.argsort(b)
        ax.plot(b[o], kq["ys"][o], ".", ms=3, color=k["mau_diem"], zorder=8)
    ax.plot(x, bao, color=k["mau_bao"], lw=k["day_bao"], zorder=9)
    ax.axhline(0, color="#f4a582", lw=1.0, zorder=1)
    lo, hi = xlim if xlim else (float(b.min()), float(b.max()))
    ax.set_xlim(hi, lo)
    ymax = float(np.max(bao))
    ax.set_ylim(-0.04 * ymax, 1.08 * ymax)
    ax.set_yticks([])
    ax.set_xlabel("Binding Energy (eV)", fontsize=11, fontweight="bold")
    if nhan_y:
        ax.set_ylabel("Intensity (a.u.)", fontsize=11, fontweight="bold")
    if ten:
        ax.text(0.04, 0.95, ten, transform=ax.transAxes, fontsize=11, fontweight="bold", va="top")
    for s in ax.spines.values():
        s.set_linewidth(1.3)
    ax.tick_params(labelsize=10, width=1.3)
    for t in ax.get_xticklabels():
        t.set_fontweight("bold")


# ====================== BẢNG THÀNH PHẦN DẠNG VĂN BẢN ======================
CAU_TRUC_DONG = "Tên | vị trí | vị trí min | vị trí max | FWHM | FWHM min | FWHM max [| tách spin-orbit | tỉ lệ diện tích] [| LA(a,b) bất đối xứng cho kim loại]"


def mo_ta_thanh_phan(ds):
    return "\n".join(f"{c.ten} | {c.vt:g} | {c.vt_lo:g} | {c.vt_hi:g} | {c.w0:g} | {c.w_lo:g} | {c.w_hi:g}"
                     + (f" | {c.tach:g} | {c.ti_le:g}" if c.tach > 0 and c.ti_le > 0 else "")
                     + (f" | LA({c.la[0]:g},{c.la[1]:g})" if c.la else "") for c in ds)


def doc_dong_thanh_phan(text):
    """Đọc bảng thành phần do người dùng gõ: mỗi dòng 'Tên | vt | vt_min | vt_max | FWHM | FWHM_min | FWHM_max' (dòng bắt đầu bằng # bị bỏ)."""
    kq = []
    for n, d in enumerate(text.splitlines(), 1):
        d = d.strip()
        if not d or d.startswith("#"):
            continue
        p = [x.strip() for x in d.split("|")]
        la_ = None
        if len(p) > 7 and p[-1].upper().startswith("LA"):
            mm = re.fullmatch(r"LA\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", p[-1], re.I)
            if not mm:
                raise ValueError(f"Dòng {n}: cú pháp bất đối xứng là LA(a,b), ví dụ LA(1.8,1.0).")
            la_ = (float(mm.group(1)), float(mm.group(2)))
            if min(la_) < 0.5 or max(la_) > 5:
                raise ValueError(f"Dòng {n}: a, b của LA nên nằm trong 0.5-5 (1 = Lorentz).")
            p = p[:-1]
        if len(p) not in (7, 9):
            raise ValueError(f"Dòng {n}: cần 7 ô (hoặc 9 ô cho doublet): {CAU_TRUC_DONG}.")
        try:
            v = [float(x.replace(",", ".")) for x in p[1:]]
        except ValueError:
            raise ValueError(f"Dòng {n}: các ô sau tên phải là số.")
        vt, lo, hi, w0, wlo, whi = v[:6]
        tach, ti = (v[6], v[7]) if len(v) == 8 else (0.0, 0.0)
        if not (lo <= vt <= hi) or not (wlo <= w0 <= whi) or lo >= hi or wlo >= whi or wlo <= 0:
            raise ValueError(f"Dòng {n}: giá trị đầu phải nằm trong [min, max] và min < max (FWHM > 0).")
        kq.append(ThanhPhan(p[0], vt, lo, hi, w0, wlo, whi, tach=tach, ti_le=ti, la=la_))
    if not kq:
        raise ValueError("Chưa có thành phần nào.")
    return kq


# ====================== ĐỊNH LƯỢNG NGUYÊN TỐ (RSF Scofield, Al Kα - theo thư viện CasaXPS) ======================
RSF = {"C 1s": 1.0, "N 1s": 1.8, "O 1s": 2.93, "F 1s": 4.43, "Si 2p": 0.817, "S 2p": 1.677, "Ti 2p": 7.81, "Fe 2p": 16.42,
       "Co 2p": 19.16, "Ni 2p": 22.18, "Cu 2p": 25.39, "Zn 2p": 28.72, "Mo 3d": 9.5, "Ru 3d": 12.49, "Pt 4f": 15.45, "Au 4f": 17.12}


def nhan_dang_vach(ten, chuyen=""):
    """'C 1s/3', 'C1s', 'Ru 3d' -> khoá RSF ('C 1s')... hoặc None."""
    for t in (chuyen, ten):
        m = re.search(r"([A-Z][a-z]?)\s*(\d[spdf])", str(t or ""))
        if m and f"{m.group(1)} {m.group(2)}" in RSF:
            return f"{m.group(1)} {m.group(2)}"
    return None


def dien_tich_vung(be, y, lo=None, hi=None, nen="shirley"):
    """Diện tích (cường độ x eV) sau khi trừ nền trong [lo, hi] (mặc định cả vùng)."""
    be, y = _sap_xep(be, y)
    m = np.ones(len(be), bool)
    if lo is not None:
        m &= be >= min(lo, hi)
    if hi is not None:
        m &= be <= max(lo, hi)
    b, yy = be[m], y[m]
    if len(b) < 8:
        raise ValueError("Vùng quá hẹp để tính diện tích.")
    bg = nen_theo(nen, b, yy)
    return float(_trapz(np.maximum(yy - bg, 0.0), b))


def dinh_luong(vung, nen="shirley", bo_qua=("survey", "wide")):
    """Từ danh sách vùng (doc_xps) tính % nguyên tử = (A/RSF) / tổng(A/RSF) cho các vùng nhận ra được vạch (C 1s, O 1s, ...).
    Chưa hiệu chỉnh hàm truyền qua máy phân tích/độ sâu thoát: chỉ là gần đúng bán định lượng (ghi rõ trong kết quả)."""
    hang = []
    for v in vung:
        if any(k in str(v.get("ten", "")).lower() for k in bo_qua) or v.get("chuyen", "").lower() == "none":
            continue
        k = nhan_dang_vach(v.get("ten", ""), (v.get("loai", "") + " " + v.get("chuyen", "")).strip())
        if not k:
            continue
        try:
            a = dien_tich_vung(v["be"], v["y"], nen=nen)
        except ValueError:
            continue
        t = (v.get("dwell") or 0) * (v.get("scans") or 0)
        if t > 0:
            a /= t                                          # CPS: so sánh được giữa các vùng quét lâu/mau khác nhau
        hang.append({"vach": k, "ten": v.get("ten", k), "dien_tich": a, "rsf": RSF[k], "a_rsf": a / RSF[k]})
    tong = sum(h["a_rsf"] for h in hang)
    for h in hang:
        h["pct"] = 100.0 * h["a_rsf"] / tong if tong > 0 else 0.0
    return hang


# ====================== KIỂU VẼ, LƯU MÔ HÌNH, BÁO CÁO ======================
def kieu_mac_dinh(n):
    return {"mau": [MAU_VE[i % len(MAU_VE)] for i in range(n)], "to": [True] * n, "alpha": 0.9, "mau_bao": "#595959",
            "day_bao": 2.6, "hien_diem": False, "mau_diem": "#888888", "hien_nen": False}


def chuan_kieu(kieu, n):
    k = kieu_mac_dinh(n)
    if kieu:
        k.update({a: b for a, b in kieu.items() if a in k and b is not None})
    for a in ("mau", "to"):
        k[a] = (list(k[a]) + kieu_mac_dinh(n)[a])[:n]
    return k


def luu_mo_hinh(duong, kq, tham_so=None, kieu=None):
    """JSON: tham số đầu vào + kết quả (để tái lập và đưa vào phần Methods/SI của bài báo)."""
    import json
    f = kq["fit"]
    d = {"tham_so": tham_so or {}, "dich_hieu_chuan_eV": kq["dich_hieu_chuan"], "residual_std": f["rstd"],
         "tu_tuong_quan": f["tu_tuong_quan"], "thanh_phan": [{k: v for k, v in c.items()} for c in f["thanh_phan"]],
         "ghi": kq["ghi"], "canh_bao": kq["canh_bao"], "kieu": kieu or {}}
    with open(duong, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2, default=float)
    return duong


def bao_cao_van_ban(kq, ten="", tham_so=None):
    f = kq["fit"]
    ts = tham_so or {}
    d = [f"BÁO CÁO FIT XPS - {ten}", "=" * 50,
         f"Hiệu chuẩn năng lượng: dịch {kq['dich_hieu_chuan']:+.3f} eV",
         f"Hình dạng đỉnh: GL({HE_SO_GL:g}); nền: {ts.get('nen', 'shirley')}; vùng fit: {ts.get('vung', '')}",
         f"Ràng buộc: vị trí/FWHM trong cửa sổ từng thành phần; chênh FWHM <= {ts.get('dw', DW_FWHM)} eV",
         f"Residual STD = {f['rstd']:.2f}; tự tương quan phần dư = {f['tu_tuong_quan']:+.2f}; số tham số = {f['so_tham_so']}", "",
         f"{'Thành phần':<26}{'BE (eV)':>9}{'FWHM':>7}{'Diện tích':>12}{'%':>7}  Ghi chú"]
    for c in f["thanh_phan"]:
        gc = (f"doublet tách {c['tach']:g} eV, tỉ lệ {c['ti_le']:g}" if c.get("tach", 0) > 0 else "") + ("  [chạm biên]" if c["o_bien"] else "")
        d.append(f"{c['ten'][:25]:<26}{c['vt']:>9.2f}{c['fwhm']:>7.2f}{c['dt']:>12.1f}{c['pct']:>7.1f}  {gc}")
    if kq["ghi"]:
        d += ["", "Quyết định về thành phần:"] + ["- " + x for x in kq["ghi"]]
    if kq["canh_bao"]:
        d += ["", "Nhận xét/cảnh báo:"] + ["- " + x for x in kq["canh_bao"]]
    return "\n".join(d) + "\n"


# ====================== CHỨNG MINH KẾT QUẢ (kiểm định thống kê) ======================
def _betacf(a, b, x):
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-12:
            break
    return h


def _betai(a, b, x):
    """Hàm beta không đầy đủ chuẩn hoá I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def p_f(F, d1, d2):
    """P(F' >= F) của phân phối F với (d1, d2) bậc tự do (kiểm định mô hình lồng nhau)."""
    if F <= 0 or d1 <= 0 or d2 <= 0:
        return 1.0
    return 1.0 - _betai(d1 / 2.0, d2 / 2.0, d1 * F / (d1 * F + d2))


def _sigma_cps(y_tho, t_thu):
    y_tho = np.asarray(y_tho, float)
    uoc = not (t_thu and t_thu > 0)
    kappa = uoc_luong_kappa(y_tho) if uoc else 1.0 / t_thu
    return np.sqrt(np.maximum(y_tho, 1e-9) * kappa), kappa, uoc


def chan_doan_phan_du(phan_du, sigma):
    """Các phép thử trên phần dư đã chuẩn hoá (r/sigma): nếu mô hình đủ và nhiễu là Poisson thì r/sigma ~ N(0,1) và không có cấu trúc."""
    z = np.asarray(phan_du, float) / np.maximum(sigma, 1e-12)
    n = len(z)
    kq = {"n": n, "z": z, "trung_binh": float(np.mean(z)), "do_lech": float(np.std(z)),
          "trong_2": float(np.mean(np.abs(z) <= 2.0)), "trong_3": float(np.mean(np.abs(z) <= 3.0))}
    r = z - np.mean(z)
    kq["lag1"] = float(r[:-1] @ r[1:] / max(r @ r, 1e-30))
    kq["durbin_watson"] = float(np.sum(np.diff(z) ** 2) / max(np.sum(z ** 2), 1e-30))
    dau = z[z != 0] > 0
    npl, nmi = int(dau.sum()), int((~dau).sum())
    if npl > 3 and nmi > 3:
        run = 1 + int(np.sum(dau[1:] != dau[:-1]))
        mu = 2.0 * npl * nmi / (npl + nmi) + 1.0
        var = (mu - 1.0) * (mu - 2.0) / max(npl + nmi - 1, 1)
        zr = (run - mu) / math.sqrt(var) if var > 0 else 0.0
        kq.update(runs=run, runs_mong_doi=mu, runs_z=zr, runs_p=math.erfc(abs(zr) / math.sqrt(2.0)))
    else:
        kq.update(runs=0, runs_mong_doi=0.0, runs_z=0.0, runs_p=1.0)
    # tìm 'đỉnh ẩn': cửa sổ trượt ~0.4 eV của phần dư chuẩn hoá, thống kê chuẩn hoá ~ N(0,1) dưới giả thuyết đủ mô hình
    return kq


def tim_dinh_an(be, z, rong_ev=0.4):
    be = np.asarray(be, float)
    h = float(np.median(np.abs(np.diff(be)))) or 0.1
    w = max(int(round(rong_ev / h)), 3)
    if len(z) < w + 2:
        return None, 0.0
    k = np.ones(w)
    t = np.convolve(z, k, mode="valid") / math.sqrt(w)
    i = int(np.argmax(np.abs(t)))
    return float(np.mean(be[i:i + w])), float(t[i])


def _dac_trung(be, y, rong_ev=0.5, he_so=3.0):
    """Đếm số đặc trưng (đỉnh + vai) nhìn thấy: cực tiểu địa phương đủ sâu của đạo hàm bậc hai (đã làm trơn)."""
    be = np.asarray(be, float)
    h = float(np.median(np.abs(np.diff(be)))) or 0.1
    w = max(int(round(rong_ev / h)) | 1, 5)
    ys = np.convolve(np.pad(y, w // 2, mode="edge"), np.ones(w) / w, mode="valid")
    d2 = np.gradient(np.gradient(ys, be), be)
    sd = 1.4826 * np.median(np.abs(d2 - np.median(d2)))
    ngu = he_so * max(sd, 1e-12)
    vt = []
    for i in range(1, len(d2) - 1):
        if d2[i] < -ngu and d2[i] <= d2[i - 1] and d2[i] <= d2[i + 1]:
            if not vt or abs(be[i] - vt[-1]) > 0.35:
                vt.append(float(be[i]))
    return vt


def _tp_tu_ket_qua(tp, thanh):
    """Bản sao thành phần với giá trị xuất phát = kết quả fit (để fit lại nhanh từ nghiệm)."""
    kq = []
    for c, t in zip(tp, thanh):
        d = c.dict()
        d["vt"] = min(max(t["vt"], c.vt_lo), c.vt_hi)
        d["w0"] = min(max(t["fwhm"], c.w_lo), c.w_hi)
        kq.append(ThanhPhan(**d))
    return kq


def _bic(fit, n):
    return n * math.log(max(fit["ssr"], 1e-30) / n) + fit["so_tham_so"] * math.log(n)


def _danh_gia_phuong_an(ten, kq2, kq0, n, mo_ta, ghi_chu_hoa=""):
    """Đo một phương án fit và tự viết ưu/nhược điểm bằng lời dễ hiểu."""
    f2, f0 = kq2["fit"], kq0["fit"]
    pa = {"ten": ten, "mo_ta": mo_ta, "kq": kq2, "rstd": f2["rstd"], "k": f2["so_tham_so"], "so_tp": len(f2["thanh_phan"]),
          "bic": _bic(f2, n), "d_bic": _bic(f2, n) - _bic(f0, n), "o_bien": [c["ten"] for c in f2["thanh_phan"] if c["o_bien"]],
          "pct_min": min(c["pct"] for c in f2["thanh_phan"])}
    sig, _, _ = _sigma_cps(kq2["y"], kq2["tham_so_fit"]["t_thu"])
    cd = chan_doan_phan_du(f2["phan_du"], sig)
    _, tz = tim_dinh_an(kq2["be"], cd["z"])
    pa["runs_p"], pa["dinh_an"], pa["dw"] = cd["runs_p"], abs(tz), cd["durbin_watson"]
    # so % diện tích với phương án hiện tại (ghép theo tên)
    t0 = {c["ten"]: c["pct"] for c in f0["thanh_phan"]}
    chenh = [abs(c["pct"] - t0[c["ten"]]) for c in f2["thanh_phan"] if c["ten"] in t0]
    pa["chenh_pct"] = max(chenh) if chenh else 0.0
    uu, nhuoc = [], []
    rs = pa["rstd"]
    if 0.85 <= rs <= 1.15:
        uu.append(f"Residual STD = {rs:.2f}, nằm trong khoảng lý tưởng 0.85-1.15 (đường fit bám dữ liệu tới mức nhiễu)")
    elif rs > 1.15:
        nhuoc.append(f"Residual STD = {rs:.2f} còn cao: đường fit chưa bám hết dữ liệu (vẫn thiếu hoặc sai hình dạng đỉnh)")
    else:
        nhuoc.append(f"Residual STD = {rs:.2f} thấp hơn 0.85: có thể đã thừa tham số (fit cả nhiễu)")
    if pa["runs_p"] > 0.01 and pa["dinh_an"] < 3.5:
        uu.append("phần dư ngẫu nhiên, không còn đỉnh bị bỏ sót")
    else:
        nhuoc.append("phần dư còn quy luật (còn cấu trúc chưa giải thích được)")
    if pa["d_bic"] <= -6:
        uu.append(f"điểm BIC thấp hơn {abs(pa['d_bic']):.0f} so với hiện tại (tốt hơn rõ rệt, đã tính cả độ phức tạp)")
    elif pa["d_bic"] >= 6:
        nhuoc.append(f"điểm BIC cao hơn {pa['d_bic']:.0f} so với hiện tại (kém hơn rõ rệt)")
    if pa["k"] < kq0["fit"]["so_tham_so"]:
        uu.append(f"đơn giản hơn ({pa['k']} tham số so với {kq0['fit']['so_tham_so']}), ít nguy cơ 'vẽ cho đẹp số'")
    elif pa["k"] > kq0["fit"]["so_tham_so"]:
        nhuoc.append(f"phức tạp hơn ({pa['k']} tham số so với {kq0['fit']['so_tham_so']}): thêm tham số luôn làm fit đẹp hơn, nên cần có lý do hoá học")
    if pa["o_bien"]:
        nhuoc.append("thành phần chạm biên ràng buộc (" + ", ".join(pa["o_bien"]) + "): giá trị do giới hạn quyết định chứ không do dữ liệu")
    else:
        uu.append("không thành phần nào chạm biên ràng buộc")
    if pa["pct_min"] < 1.0:
        nhuoc.append(f"có thành phần chỉ {pa['pct_min']:.1f}% diện tích: gần ngưỡng phát hiện, khó tin cậy")
    if pa["chenh_pct"] >= 3.0:
        nhuoc.append(f"làm đổi % diện tích tới {pa['chenh_pct']:.1f} điểm so với hiện tại: kết luận định lượng phụ thuộc lựa chọn này")
    elif pa["chenh_pct"] > 0:
        uu.append(f"% diện tích gần như không đổi (lệch tối đa {pa['chenh_pct']:.1f} điểm)")
    if ghi_chu_hoa:
        (nhuoc if ghi_chu_hoa.startswith("!") else uu).append(ghi_chu_hoa.lstrip("!"))
    pa["uu"], pa["nhuoc"] = uu, nhuoc
    # điều kiện bắt buộc để được đề xuất: mọi thành phần >= 1%, Residual STD <= 1.3, phần dư ngẫu nhiên và không còn đỉnh ẩn
    ly = []
    if pa["pct_min"] < 1.0:
        ly.append("có thành phần < 1%")
    if rs > 1.3:
        ly.append("Residual STD > 1.3")
    if pa["runs_p"] <= 0.01 or pa["dinh_an"] >= 3.5:
        ly.append("phần dư còn quy luật")
    pa["ly_loai"] = ly
    pa["hop_le"] = not ly
    pa["bic_hc"] = pa["bic"] + 6.0 * len(pa["o_bien"])     # phạt mỗi thành phần chạm biên (giá trị do giới hạn quyết định)
    return pa


def chung_minh(kq, so_mau_boot=30, tien_do=None, hat=7):
    """Kiểm định thống kê kết quả fit và đề xuất phương án tốt nhất.
    Trả về dict cm: 'van_ban' (báo cáo dễ đọc), 'phuong_an' (danh sách phương án, mỗi phương án có 'kq' đầy đủ để áp dụng),
    'khuyen_nghi' (chỉ số phương án được đề xuất), 'dat', ... """
    def bao(t):
        if tien_do:
            tien_do(t)
    ts = kq["tham_so_fit"]
    b, yy, ys, fit = kq["be"], kq["y"], kq["ys"], kq["fit"]
    tp = list(kq["tp"])
    m, t_thu, dw = ts["m"], ts["t_thu"], ts["dw"]
    n = len(b)
    sig, kappa, uoc = _sigma_cps(yy, t_thu)
    cm = {"kappa_uoc_luong": uoc}

    # ---------- tính toán ----------
    bao("Phân tích phần dư...")
    cd = chan_doan_phan_du(fit["phan_du"], sig)
    cd["rstd"] = fit["rstd"]
    cm["phan_du"] = cd
    dinh, tz = tim_dinh_an(b, cd["z"])
    cd["dinh_an_be"], cd["dinh_an_z"] = dinh, tz
    rs = fit["rstd"]
    ok_rs, ok_runs = 0.85 <= rs <= 1.15, cd["runs_p"] > 0.01
    ok_dw, ok_an, ok_2s = 1.5 <= cd["durbin_watson"] <= 2.5, abs(tz) < 3.5, cd["trong_2"] >= 0.90

    ssr_f, k_f = fit["ssr"], fit["so_tham_so"]
    df_f = max(n - k_f, 1)
    start = _tp_tu_ket_qua(tp, fit["thanh_phan"])
    bao("Kiểm định từng thành phần...")
    can_thiet = []
    for i, c in enumerate(tp):
        con = [x for j, x in enumerate(tp) if j != i]
        if not con:
            can_thiet.append((c.ten, None, None, None))
            continue
        f2 = khop(b, ys, _tp_tu_ket_qua(con, [t for j, t in enumerate(fit["thanh_phan"]) if j != i]), m, so_lan=3, y_tho=yy, t_thu=t_thu, dw_fwhm=dw)
        d1 = k_f - f2["so_tham_so"]
        F = ((f2["ssr"] - ssr_f) / max(d1, 1)) / max(ssr_f / df_f, 1e-30)
        can_thiet.append((c.ten, F, p_f(F, max(d1, 1), df_f), f2["rstd"]))
    cm["can_thiet"] = [(a, F, p) for a, F, p, _ in can_thiet]

    bao("Thử thêm đỉnh ứng viên...")
    dung = {c.ten for c in tp}
    chua = [c for c in ts["ung_vien"] if c.ten not in dung]
    them_thu = []
    for uv in chua:
        f2 = khop(b, ys, start + [ThanhPhan(**uv.dict())], m, so_lan=4, y_tho=yy, t_thu=t_thu, dw_fwhm=dw)
        d1 = f2["so_tham_so"] - k_f
        F = ((ssr_f - f2["ssr"]) / max(d1, 1)) / max(f2["ssr"] / max(n - f2["so_tham_so"], 1), 1e-30)
        p = p_f(F, max(d1, 1), max(n - f2["so_tham_so"], 1))
        moi = f2["thanh_phan"][-1]
        ly = []
        if p >= 0.01:
            ly.append("không cải thiện có ý nghĩa")
        if moi["o_bien"]:
            ly.append("chạm biên " + "/".join(moi["o_bien"]))
        if moi["pct"] < 1.0:
            ly.append(f"chỉ {moi['pct']:.1f}% diện tích")
        them_thu.append((uv, F, p, ly, f2["rstd"]))
    cm["them_thu"] = [(u.ten, F, p, ly) for u, F, p, ly, _ in them_thu]

    d_data, d_mo = _dac_trung(b, ys), _dac_trung(b, fit["mo_hinh"])
    cm["dac_trung"] = (d_data, d_mo)

    # ---------- các phương án ----------
    bao("Thử các phương án fit khác nhau...")
    be_full, y_full = kq["be_day_du"], kq["y_day_du"]
    ten_nen = {"shirley": "Shirley", "tougaard": "Tougaard U2", "tuyen_tinh": "Tuyến tính"}

    def chay(tp_l, nen, dw_, ten, mo_ta, ghi=""):
        try:
            k2 = phan_tich_pho(be_full, y_full, "C1s", tp=[ThanhPhan(**c.dict()) for c in tp_l], ung_vien=[], vung=ts["vung"], nen=nen,
                               t_thu=t_thu, m=m, tu_chon=False, dw_fwhm=dw_, dich_san=0.0)
        except Exception:
            return None
        k2["dich_hieu_chuan"] = kq["dich_hieu_chuan"]
        k2["tham_so_fit"]["ung_vien"] = ts["ung_vien"]
        return _danh_gia_phuong_an(ten, k2, kq, n, mo_ta, ghi)

    pas = []
    base = _danh_gia_phuong_an("Giữ nguyên kết quả hiện tại", kq, kq, n,
                               f"{len(tp)} thành phần, nền {ten_nen.get(ts['nen'], ts['nen'])}, chênh FWHM tối đa {dw:g} eV")
    pas.append(base)
    for (nm, F, p, rr), c in zip(can_thiet, tp):
        if p is not None and p >= 0.01:
            pa = chay([x for x in tp if x is not c], ts["nen"], dw, f"Bỏ thành phần '{nm}'",
                      "Fit lại với ít thành phần hơn", f"F-test cho thấy thành phần này không cần thiết (p = {p:.2f})")
            if pa:
                pas.append(pa)
    for uv, F, p, ly, _ in them_thu:
        pa = chay(tp + [uv], ts["nen"], dw, f"Thêm thành phần '{uv.ten}'", f"Thêm đỉnh {uv.ten} ({uv.ghi_chu or 'ứng viên hoá học'})",
                  (f"F-test: p = {p:.1e} (< 0.01 nên có ý nghĩa thống kê)" if p < 0.01 else f"!F-test: p = {p:.2f} (>= 0.01: thêm đỉnh không cải thiện có ý nghĩa)"))
        if pa:
            pas.append(pa)
    for x in ("shirley", "tougaard", "tuyen_tinh"):
        if x != ts["nen"]:
            pa = chay(tp, x, dw, f"Đổi nền sang {ten_nen[x]}", "Giữ nguyên các thành phần, chỉ đổi cách trừ nền",
                      {"shirley": "Shirley là lựa chọn chuẩn cho hầu hết phổ lõi", "tougaard": "Tougaard hợp khi nền dốc / có nhiều electron mất năng lượng",
                       "tuyen_tinh": "!nền tuyến tính quá đơn giản nếu hai chân phổ cao thấp khác nhau nhiều"}[x])
            if pa:
                pas.append(pa)
    if dw and dw > 0:
        pa = chay(tp, ts["nen"], dw * 2, f"Nới ràng buộc độ rộng (chênh FWHM {dw * 2:g} eV)", "Cho các thành phần được rộng/hẹp khác nhau hơn",
                  "!tự do hơn nên dễ fit đẹp nhưng kém ý nghĩa hoá học: tài liệu khuyến nghị giữ ±10% hoặc ±0.1 eV")
        if pa:
            pas.append(pa)

    # chọn phương án tốt nhất: hợp lệ, điểm BIC (đã phạt chạm biên) thấp nhất; chênh < 4 thì ưu tiên ít tham số;
    # phương án hiện tại được giữ nếu nó hợp lệ và chỉ kém tốt nhất dưới 6 điểm (không đổi cách fit khi lợi ích không rõ rệt)
    hop = [(i, p) for i, p in enumerate(pas) if p["hop_le"]]
    kn = 0
    if hop:
        v_min = min(p["bic_hc"] for _, p in hop)
        gan = sorted([(i, p) for i, p in hop if p["bic_hc"] - v_min < 4.0], key=lambda t: (t[1]["k"], t[0]))
        kn = 0 if (base["hop_le"] and base["bic_hc"] - v_min < 6.0) else gan[0][0]
    cm["phuong_an"], cm["khuyen_nghi"] = pas, kn
    rec = pas[kn]

    # ---------- độ bền (đổi nền/vùng) & sai số ----------
    bao("Thử đổi nền và vùng fit...")
    bs = []
    kich = [(ten_nen[x], b, yy, x) for x in ("shirley", "tougaard", "tuyen_tinh")]
    for dl, dh in ((0.5, 0.0), (0.0, 0.5), (-0.5, 0.0), (0.0, -0.5)):
        lo, hi = ts["vung"][0] + dl, ts["vung"][1] + dh
        mk = (be_full >= lo) & (be_full <= hi)
        if mk.sum() >= 20:
            kich.append((f"Vùng fit {lo:.1f}-{hi:.1f} eV", be_full[mk], y_full[mk], ts["nen"]))
    for ten, bb, y2, nen in kich:
        try:
            f2 = khop(bb, y2 - nen_theo(nen, bb, y2), start, m, so_lan=2, y_tho=y2, t_thu=t_thu, dw_fwhm=dw)
        except Exception:
            continue
        bs.append((ten, f2["rstd"], [c["pct"] for c in f2["thanh_phan"]], [c["vt"] for c in f2["thanh_phan"]]))
    cm["ben"] = bs
    dao = {}
    for tn, g in {"cách trừ nền": bs[:3], "vùng fit": bs[3:]}.items():
        if len(g) >= 2:
            pc = np.array([x[2] for x in g])
            dao[tn] = (pc.max(axis=0) - pc.min(axis=0)).tolist()
    cm["dao_dong_pct"] = dao
    mx = max([max(v) for v in dao.values()] or [0.0])
    ok_ben = mx < 3.0

    bao(f"Monte Carlo ({so_mau_boot} lần)...")
    rng = np.random.default_rng(hat)
    mo = fit["mo_hinh"]
    thu = []
    for r in range(so_mau_boot):
        try:
            f2 = khop(b, mo + sig * rng.standard_normal(n), start, m, so_lan=1, y_tho=yy, t_thu=t_thu, dw_fwhm=dw)
        except Exception:
            continue
        thu.append([[c["vt"], c["fwhm"], c["pct"]] for c in f2["thanh_phan"]])
        if r % 5 == 4:
            bao(f"Monte Carlo {r + 1}/{so_mau_boot}...")
    sai_so = []
    if len(thu) >= 5:
        arr = np.array(thu)
        for i, t in enumerate(fit["thanh_phan"]):
            sd = arr[:, i, :].std(axis=0, ddof=1)
            sai_so.append((t["ten"], float(sd[0]), float(sd[1]), float(sd[2])))
    cm["sai_so"] = sai_so

    thieu = [x for x in cm["can_thiet"] if x[2] is not None and x[2] >= 0.01]
    them_ok = [x for x in cm["them_thu"] if not x[3]]
    ok_sl = not thieu and not them_ok
    ok_pd = ok_rs and ok_runs and ok_an and ok_dw and ok_2s
    cm.update(ok_so_luong=ok_sl, ok_phan_du=ok_pd, ok_ben=ok_ben, dat=ok_sl and ok_pd)

    # ---------- viết báo cáo dễ hiểu ----------
    nhan = lambda ok: "ĐẠT" if ok else "CHƯA ĐẠT"
    L = ["BÁO CÁO CHỨNG MINH KẾT QUẢ FIT XPS", "=" * 64, "", "TÓM TẮT (đọc phần này trước)", "-" * 64]
    L.append(f"* Mô hình hiện tại dùng {len(tp)} thành phần. Số thành phần như vậy: {nhan(ok_sl)}.")
    L.append(f"* Đường fit bám dữ liệu (Residual STD = {rs:.2f}, lý tưởng ≈ 1): {nhan(ok_rs and ok_pd)}.")
    L.append(f"* Kết quả có ổn định khi đổi cách trừ nền / vùng fit không: {'ỔN ĐỊNH' if ok_ben else 'CÒN NHẠY (xem mục 4)'}.")
    if kn == 0:
        L.append("* ĐỀ XUẤT: GIỮ NGUYÊN kết quả hiện tại - không phương án nào khác tốt hơn rõ rệt (xem mục 5).")
    else:
        L.append(f"* ĐỀ XUẤT: chuyển sang phương án \"{rec['ten']}\" (xem mục 5 để biết lý do và so sánh).")
    if uoc:
        L.append("* LƯU Ý: chưa biết dwell x scan nên con số Residual STD chỉ mang tính tham khảo (xem phần giải thích cuối).")

    L += ["", "1) ĐƯỜNG FIT CÓ BÁM SÁT DỮ LIỆU KHÔNG?  (kiểm tra 'phần dư')", "-" * 64,
          "Phần dư = dữ liệu - đường fit. Nếu mô hình đúng thì phần dư chỉ còn nhiễu ngẫu nhiên (lên xuống lộn xộn, không theo quy luật).",
          "Nếu phần dư còn 'gợn sóng' hoặc một cái bướu, nghĩa là còn thiếu một đỉnh hoặc nền chưa đúng.", "",
          f"  [{nhan(ok_rs)}] Residual STD = {rs:.2f}   - sai khác trung bình giữa fit và dữ liệu so với mức nhiễu kỳ vọng. "
          "≈ 1 là lý tưởng; > 1.15 là còn thiếu; < 0.85 là có thể thừa đỉnh.",
          f"  [{nhan(ok_2s)}] {100 * cd['trong_2']:.0f}% số điểm nằm trong ±2σ   - nếu chỉ là nhiễu thì khoảng 95% (σ = độ nhiễu kỳ vọng).",
          f"  [{nhan(ok_dw)}] Durbin-Watson = {cd['durbin_watson']:.2f}   - đo xem phần dư điểm này có 'dính' điểm bên cạnh không; ≈ 2 là tốt, 1.5-2.5 chấp nhận được.",
          f"  [{nhan(ok_runs)}] Kiểm định chuỗi dấu: p = {cd['runs_p']:.2f}   - đếm số lần phần dư đổi dấu +/-; p > 0.01 nghĩa là đổi dấu ngẫu nhiên như nhiễu.",
          f"  [{nhan(ok_an)}] Quét đỉnh ẩn: mạnh nhất tại {dinh if dinh is not None else float('nan'):.1f} eV, mức {abs(tz):.1f} (< 3.5 là không còn đỉnh bị bỏ sót)."]

    L += ["", f"2) SỐ THÀNH PHẦN ({len(tp)}) CÓ ĐÚNG KHÔNG?", "-" * 64,
          "Cách kiểm: (a) bỏ thử từng thành phần - nếu fit tệ đi rõ rệt (p nhỏ hơn 0.01) thì thành phần đó thật sự cần;",
          "(b) thử thêm từng đỉnh có thể có về mặt hoá học - nếu fit không tốt lên rõ rệt thì không nên thêm (thêm đỉnh nào cũng làm fit 'đẹp' hơn một chút,",
          "nhưng đó không phải là bằng chứng thật).", "", "  (a) Bỏ thử từng thành phần:"]
    for nm, F, p, rr in can_thiet:
        if p is None:
            continue
        L.append(f"      - {nm[:34]:<35} bỏ đi thì Residual STD tăng lên {rr:.2f}, p = {p:.1e}  ->  "
                 + ("CẦN THIẾT" if p < 0.01 else "KHÔNG đủ bằng chứng là cần"))
    L.append("  (b) Thử thêm đỉnh ứng viên:")
    if not them_thu:
        L.append("      - (không còn ứng viên nào chưa xét)")
    for uv, F, p, ly, rr2 in them_thu:
        L.append(f"      - {uv.ten[:34]:<35} thêm vào thì Residual STD {rs:.2f} -> {rr2:.2f}, p = {p:.1e}  ->  "
                 + ("KHÔNG nên thêm (" + "; ".join(ly) + ")" if ly else "NÊN thêm (cải thiện có ý nghĩa)"))
    L += ["", f"  (c) Số đỉnh/vai mắt thấy được: dữ liệu {len(d_data)} ({', '.join(f'{v:.1f}' for v in d_data) or '-'} eV), "
              f"mô hình {len(d_mo)} ({', '.join(f'{v:.1f}' for v in d_mo) or '-'} eV) -> {'khớp nhau' if len(d_data) == len(d_mo) else 'lệch nhau'}.",
          "      (Các đỉnh chồng sát nhau có thể không tạo vai riêng nhưng vẫn cần nếu ở (a) cho p nhỏ.)"]

    L += ["", "3) SAI SỐ CỦA KẾT QUẢ  (mô phỏng lại phép đo 30 lần với nhiễu ngẫu nhiên)", "-" * 64,
          "Ý nghĩa: nếu đo lại, các con số có thể dao động quanh giá trị bao nhiêu. '± sd' càng nhỏ so với giá trị thì càng đáng tin."]
    if sai_so:
        L.append(f"  {'Thành phần':<28}{'Vị trí (eV)':>16}{'FWHM (eV)':>16}{'% diện tích':>18}")
        for (nm, a, b_, c_), t in zip(sai_so, fit["thanh_phan"]):
            L.append(f"  {nm[:27]:<28}{t['vt']:>9.2f} ± {a:.2f}{t['fwhm']:>9.2f} ± {b_:.2f}{t['pct']:>11.1f} ± {c_:.1f}"
                     + ("" if t["pct"] > 3 * c_ else "   <- yếu"))
        L.append("  ('yếu' = % diện tích không lớn hơn 3 lần sai số, không nên diễn giải mạnh.)  Chưa tính sai số do cách chọn nền (mục 4).")
    else:
        L.append("  (không đủ mẫu hợp lệ)")

    L += ["", "4) KẾT QUẢ CÓ BỊ THAY ĐỔI NẾU ĐỔI CÁCH TRỪ NỀN / VÙNG FIT KHÔNG?", "-" * 64,
          f"  {'Kịch bản':<30}{'Residual STD':>13}   % diện tích từng thành phần"]
    for ten, r_, pc, _ in bs:
        L.append(f"  {ten:<30}{r_:>13.2f}   " + "  ".join(f"{v:5.1f}" for v in pc))
    for tn, v in dao.items():
        L.append(f"  Khi đổi {tn}, % diện tích dao động tối đa: " + "  ".join(f"{x:.1f}" for x in v) + " (điểm %)")
    L.append("  -> " + ("ỔN ĐỊNH (dao động < 3 điểm %)." if ok_ben else f"CÒN NHẠY (tới {mx:.1f} điểm %). Đây là sai số hệ thống: nên báo cáo kèm, "
                                                                 "và chọn nền theo bản chất vật lý, vùng fit phủ trọn đỉnh cùng hai chân phẳng."))

    L += ["", "5) CÁC PHƯƠNG ÁN FIT VÀ ĐỀ XUẤT", "-" * 64,
          "App đã thử fit lại theo nhiều cách khác nhau. 'BIC' là điểm tổng hợp độ khớp và độ phức tạp (càng THẤP càng tốt; chênh dưới 4 coi như",
          "ngang nhau, trên 6 là khác biệt rõ; mỗi thành phần chạm biên bị cộng thêm 6 điểm phạt). Phương án chỉ được đề xuất khi mọi thành phần >= 1%,",
          "Residual STD <= 1.3 và phần dư là nhiễu ngẫu nhiên. Phương án hiện tại được giữ nếu nó hợp lệ và không kém phương án tốt nhất quá 6 điểm.", "",
          f"  {'#':<3}{'Phương án':<44}{'Res.STD':>8}{'BIC so với hiện tại':>20}{'Số TP':>7}   Đánh giá"]
    for i, p in enumerate(pas):
        d = "0" if i == 0 else f"{p['d_bic']:+.1f}"
        dg = ("ĐỀ XUẤT" if i == kn else ("hợp lệ" if p["hop_le"] else "loại: " + "; ".join(p["ly_loai"])))
        L.append(f"  {i + 1:<3}{p['ten'][:43]:<44}{p['rstd']:>8.2f}{d:>20}{p['so_tp']:>7}   {dg}")
    L.append("")
    for i, p in enumerate(pas):
        L.append(f"  Phương án {i + 1}: {p['ten']}" + ("   <== ĐỀ XUẤT" if i == kn else ""))
        L.append(f"    Làm gì: {p['mo_ta']}")
        for u in p["uu"]:
            L.append(f"    + {u}")
        for u in p["nhuoc"]:
            L.append(f"    - {u}")
    L.append("")
    if kn == 0:
        L.append("  VÌ SAO ĐỀ XUẤT GIỮ NGUYÊN: " + ("kết quả hiện tại đã hợp lệ và không phương án nào có điểm BIC tốt hơn rõ rệt; "
                                                     "đổi sang phương án phức tạp hơn chỉ làm đẹp số mà không thêm bằng chứng." + (
            f" Tuy vậy thành phần {', '.join(base['o_bien'])} đang chạm biên ràng buộc: nếu có cơ sở hoá học thì nên xem lại cửa sổ vị trí/độ rộng của nó, "
            "hoặc có đỉnh khác chồng sát (ví dụ C=O cạnh O-C=O)." if base["o_bien"] else "") if base["hop_le"] else
                                                     "không phương án nào hợp lệ tốt hơn; hãy xem lại hiệu chuẩn, nền và khả năng có nguyên tố khác chồng lấn."))
    else:
        L.append(f"  VÌ SAO ĐỀ XUẤT PHƯƠNG ÁN {kn + 1}: hợp lệ và có điểm BIC "
                 + (f"thấp hơn {abs(rec['d_bic']):.0f} so với hiện tại" if rec["d_bic"] < 0 else "ngang hiện tại nhưng đơn giản hơn")
                 + f"; Residual STD = {rec['rstd']:.2f}. Bấm 'Áp dụng phương án đề xuất' để thay kết quả đang hiển thị.")

    L += ["", "6) KẾT LUẬN", "-" * 64,
          f"  [{nhan(ok_sl)}] Số thành phần: " + ("mỗi thành phần đều cần thiết, và không có đỉnh nào đáng thêm." if ok_sl else
                                                  "; ".join((["không đủ bằng chứng cho " + ", ".join(x[0] for x in thieu)] if thieu else [])
                                                            + (["nên thêm " + ", ".join(x[0] for x in them_ok)] if them_ok else []))),
          f"  [{nhan(ok_pd)}] Đường fit bám dữ liệu: Residual STD = {rs:.2f}" + ("; phần dư chỉ là nhiễu ngẫu nhiên." if ok_pd else "; phần dư còn cấu trúc (mục 1)."),
          f"  [{'ĐẠT' if ok_ben else 'LƯU Ý'}] Độ ổn định theo nền/vùng fit: " + ("tốt." if ok_ben else "còn nhạy, cần báo cáo sai số hệ thống.")]
    if not (ok_sl and ok_pd):
        L.append("  App KHÔNG tự thêm đỉnh vô nghĩa để ép Residual STD về 1. Nên kiểm tra: cách trừ nền (thử Tougaard), hiệu chuẩn năng lượng, "
                 "đỉnh của nguyên tố khác chồng lên, hoặc cửa sổ hoá học nếu có lý do vật lý.")
    L += ["", "GIẢI THÍCH THUẬT NGỮ", "-" * 64,
          "  Residual STD   : so độ lệch giữa fit và dữ liệu với độ nhiễu bắt buộc phải có (nhiễu đếm hạt Poisson). ≈ 1 nghĩa là 'fit chính xác tới mức nhiễu cho phép'.",
          "                   Chỉ có nghĩa nếu biết đúng thời gian đo (dwell x scan)" + (" - LẦN NÀY CHƯA BIẾT nên con số chỉ để tham khảo." if uoc else ", lần này đã dùng thời gian đo thật."),
          "  p (F-test)     : xác suất để một cải thiện cỡ đó xảy ra chỉ do may rủi. p < 0.01 = rất khó là may rủi, tức là cải thiện có thật.",
          "  BIC            : điểm cân bằng giữa độ khớp và số tham số; chống việc thêm đỉnh cho đẹp. Thấp hơn = tốt hơn.",
          "  FWHM           : độ rộng đỉnh ở nửa chiều cao (eV).",
          "  Chạm biên      : giá trị fit nằm sát giới hạn cho phép nên do giới hạn quyết định chứ không do dữ liệu.",
          "  Monte Carlo    : mô phỏng lặp lại phép đo bằng nhiễu ngẫu nhiên để ước lượng sai số.",
          "  Phần chứng minh này chỉ cho biết mô hình đủ và đúng về thống kê. Việc vị trí đỉnh có hợp lý hoá học hay không vẫn do cửa sổ ràng buộc và người phân tích quyết định."]
    cm["van_ban"] = "\n".join(L) + "\n"
    return cm


# ====================== XUẤT SANG CasaXPS ======================
def ghi_vamas(duong, khoi, hv=1486.6, ten_mau="Echem Studio", dwell=1.0, scans=1, loai="C", chuyen="1s", chu_thich="Echem Studio fit"):
    """Ghi file VAMAS (ISO 14976, NORM/REGULAR, XPS) để mở bằng CasaXPS. khoi = [(ten, be, y)]; mỗi khối là một phổ
    (CasaXPS hiện mỗi khối như một 'Core Line' riêng, chồng lên nhau được bằng Display > Overlay). Trục ghi theo động năng KE = hv - BE
    (CasaXPS đổi lại BE), nên vị trí BE trong Casa trùng với phổ đã hiệu chuẩn."""
    head = ["VAMAS Surface Chemical Analysis Standard Data Transfer Format 1988 May 4", "Not Specified", "Not Specified", "Not Specified", ten_mau,
            "1", "Echem Studio", "NORM", "REGULAR", str(len(khoi)), "1", "Exp Variable", "d", "0", "0", "0", "0", str(len(khoi))]
    L = list(head)
    for muc in khoi:
        ten, be, y = muc[:3]
        chu_t = list(muc[3]) if len(muc) > 3 and muc[3] else ["Echem Studio"]           # chú thích khối (có thể là 'Casa Info Follows' + vùng/thành phần)
        be = np.asarray(be, float)
        y = np.asarray(y, float)
        o = np.argsort(be)
        be, y = be[o], y[o]
        buoc = float(np.median(np.diff(be))) if len(be) > 1 else 0.1
        g = np.arange(float(be.min()), float(be.max()) + buoc / 2, buoc)
        yg = np.interp(g, be, y)
        ke = hv - g[::-1]                          # KE tăng dần
        yk = yg[::-1]
        # bố cục giống file CasaXPS tự ghi (đối chiếu với SiTemplate.vms của Casa): 2 biến (Intensity + Transmission), 1e+037 = "không xác định"
        ndiem = len(yk)
        tr = [f"{v:.8g}" for v in yk]
        L += [str(ten), ten_mau, "2024", "1", "1", "0", "0", "0", "0", str(len(chu_t))] + chu_t + ["XPS", "0", "Mono(Al (Mono))", f"{hv:g}",
              "1e+037", "1e+037", "1e+037", "1e+037", "1e+037", "FAT", "20", "1e+037", "1e+037", "1e+037", "1e+037", "1e+037", "1e+037", "1e+037",
              str(loai), str(chuyen), "-1", "Kinetic Energy", "eV", f"{ke[0]:.6f}", f"{buoc:.6f}", "2", "Intensity", "d", "Transmission", "d",
              "pulse counting", f"{dwell:g}", str(int(scans)), "0", "1e+037", "1e+037", "1e+037", "0",
              str(2 * ndiem), f"{yk.min():.8g}", f"{yk.max():.8g}", "1", "1"]
        for v in tr:
            L += [v, "1"]
    with open(duong, "w", encoding="latin-1", errors="replace", newline="") as fh:
        fh.write("\r\n".join(L) + "\r\n")                  # CRLF như file Casa
    return duong


def casa_chu_thich(kq, ten, hv, dich=0.0):
    """Các dòng chú thích 'Casa Info Follows' (cú pháp lấy từ file CasaXPS thật: SiTemplate.vms, Mo3d-Lineshapes.vms) để Casa tự dựng vùng,
    nền và các thành phần fit của chính nó khi mở khối. Vị trí/vùng tính theo động năng KE = hv - BE. Nền Shirley/Tuyến tính được giữ;
    Tougaard (tham số riêng của Casa) ghi nền 'None'. Đỉnh bất đối xứng LA được ghi dạng GL(30)."""
    f = kq["fit"]
    b = np.asarray(kq["be"], float) - dich                       # dich != 0: về thang BE gốc của file (chưa hiệu chuẩn)
    e1, e2 = hv - float(b.max()), hv - float(b.min())
    nen = str(kq.get("tham_so_fit", {}).get("nen", "shirley")).lower()
    ten_nen = "Shirley" if "shirley" in nen else ("Linear" if ("tuy" in nen or "linear" in nen) else "None")
    nhan = re.sub(r"[()*]", "", ten)
    L = [f"CASA region (*{nhan}*) (*{ten_nen}*) {e1:.5f} {e2:.5f} 1 1 0 0 299 542 275 9.3 (*{nhan}*) 0"]
    cs = []
    for c in f["thanh_phan"]:
        ten_c = re.sub(r"[()*]", "", c["ten"]).strip() or "Peak"
        parts = [(ten_c, c["vt"] - dich, c["dt"])]
        if c.get("tach", 0) > 0 and c.get("ti_le", 0) > 0:
            a1 = c["dt"] / (1.0 + c["ti_le"])
            parts = [(ten_c, c["vt"] - dich, a1), (ten_c + " 2", c["vt"] - dich + c["tach"], a1 * c["ti_le"])]
        for nm, be_c, ar in parts:
            ke = hv - be_c
            w = c["fwhm"]
            cs.append(f"CASA comp (*{nm}*) (*GL(30)*) Area {max(ar, 0.0):.6g} 4 10000000 -1 1 MFWHM {w:.6g} {0.3 * w:.6g} {4 * w:.6g} -1 1 "
                      f"Position {ke:.6g} {ke - 1.0:.6g} {ke + 1.0:.6g} -1 1 RSF 1 MASS 0 (*NoTag*)")
    return ["Casa Info Follows", "0", "0", "1"] + L + [str(len(cs))] + cs + ["Echem Studio: thanh phan da fit"]


def xuat_casa_goc(duong_vao, so_khoi, kq, ten, hv, duong_ra):
    """Chép NGUYÊN file VAMAS gốc (mọi khối khác giữ nguyên) sang duong_ra, chỉ ghi/ghi đè phần 'Casa Info' trong chú thích của khối so_khoi
    bằng vùng nền + các thành phần đã fit (về thang BE gốc, chưa hiệu chuẩn). Mở trong Casa sẽ thấy đúng cấu trúc file gốc, khối này đã có fit.
    Trả về duong_ra hoặc None nếu không đọc được cấu trúc file."""
    try:
        with open(duong_vao, "r", encoding="latin-1", newline="") as fh:
            text = fh.read()
        vet = []
        vung = _doc_vamas_chuan(text, vet)
        if not vung or so_khoi >= len(vet) or len(vet) != len(vung):
            return None
        raw = text.split("\n")
        eol = "\r" if raw and raw[0].endswith("\r") else ""
        idx, nct = vet[so_khoi]
        cu = [x.strip() for x in raw[idx + 1: idx + 1 + nct]]
        calib, tu_do = [], list(cu)
        if cu and cu[0].startswith("Casa Info Follows"):
            try:
                p = 1
                nc = int(cu[p])
                calib = cu[p + 1: p + 1 + nc]
                p += 1 + nc + 1                              # số dòng hiệu chuẩn + dòng + một số 0
                nr = int(cu[p])
                p += 1 + nr
                ncp = int(cu[p])
                p += 1 + ncp
                tu_do = cu[p:]
            except (ValueError, IndexError):
                calib, tu_do = [], cu[1:]
        ct = casa_chu_thich(kq, ten, hv, kq.get("dich_hieu_chuan", 0.0))
        moi = ["Casa Info Follows", str(len(calib))] + calib + ct[2:] + tu_do          # ct[2:] = '0', số vùng, vùng, số thành phần, thành phần, ghi chú
        raw[idx: idx + 1 + nct] = [str(len(moi)) + eol] + [x + eol for x in moi]
        with open(duong_ra, "w", encoding="latin-1", errors="replace", newline="") as fh:
            fh.write("\n".join(raw))
        return duong_ra
    except (OSError, ValueError, IndexError):
        return None


def xuat_casa(kq, thu_muc, ten="XPS", hv=1486.6, dwell_scan=None):
    """Ghi cho CasaXPS: <ten>_casa.vms (phổ thô đã hiệu chuẩn, nền, đường bao và từng thành phần đã cộng nền — chồng được trong Casa)
    và <ten>_casa_thanh_phan.txt (bảng thành phần để tạo lại trong Casa: vị trí, FWHM, diện tích, dạng đỉnh, nền)."""
    os.makedirs(thu_muc, exist_ok=True)
    import unicodedata
    ten_tep = re.sub(r"[^A-Za-z0-9_.-]+", "_", unicodedata.normalize("NFKD", ten).encode("ascii", "ignore").decode("ascii")).strip("._") or "XPS"
    b = np.asarray(kq["be"], float)
    f = kq["fit"]
    nen = np.asarray(kq["nen"], float)
    khoi = [(f"{ten} Raw", b, kq["y"]), (f"{ten} Background", b, nen), (f"{ten} Envelope", b, nen + f["mo_hinh"])]
    for c_ten, cv in zip([c["ten"] for c in f["thanh_phan"]], f["cac"]):
        khoi.append((f"{ten} {c_ten}", b, nen + cv))
    khoi.append((f"{ten} Residual", b, f["phan_du"]))
    dw, sc = (dwell_scan, 1) if dwell_scan else (1.0, 1)
    pv = ghi_vamas(os.path.join(thu_muc, f"{ten_tep}_casa.vms"), khoi, hv, dwell=dw, scans=sc,
                   chu_thich=f"Echem Studio: be da hieu chuan (dich {kq['dich_hieu_chuan']:+.3f} eV)")
    pf = ghi_vamas(os.path.join(thu_muc, f"{ten_tep}_casa_fit.vms"), [(f"{ten_tep}", b, kq["y"], casa_chu_thich(kq, ten, hv))], hv, dwell=dw, scans=sc)
    pt = os.path.join(thu_muc, f"{ten_tep}_casa_thanh_phan.txt")
    L = [f"BẢNG THÀNH PHẦN CHO CasaXPS - {ten}", "",
         f"Nền: {kq.get('tham_so_fit', {}).get('nen', 'Shirley')}; dịch hiệu chuẩn đã áp dụng vào file .vms: {kq['dich_hieu_chuan']:+.3f} eV; Residual STD = {f['rstd']:.3f}", "",
         f"{'Thành phần':<16}{'Vị trí BE (eV)':>15}{'FWHM (eV)':>11}{'Diện tích (CPS·eV)':>20}{'% diện tích':>13}  Dạng đỉnh"]
    for c in f["thanh_phan"]:
        dang = f"LA({c['la'][0]:g},{c['la'][1]:g})" if c.get("la") else "GL(30)"
        L.append(f"{c['ten']:<16}{c['vt']:>15.3f}{c['fwhm']:>11.3f}{c['dt']:>20.2f}{c['pct']:>13.2f}  {dang}")
    L += ["", "CÁCH DÙNG TRONG CasaXPS:",
          "1. File > Open, chọn file *_casa.vms. Mỗi khối (Raw, Background, Envelope, từng thành phần, Residual) là một phổ riêng.",
          "2. Chọn các khối cần hiển thị rồi dùng Display > Create/Overlay (hoặc kéo thả khối vào cùng một Display) để chồng lên nhau;",
          "   thành phần đã cộng sẵn nền nên chồng đúng lên phổ thô; tô màu vùng bằng Properties của từng khối.",
          "3. Muốn fit ngay trong Casa: chọn khối Raw, tạo vùng nền (Shirley) và thêm thành phần theo bảng trên (GL(30) là dạng mặc định,",
          "   LA(a,b) = Lorentzian bất đối xứng), rồi so với Residual STD ở trên."]
    L += ["", f"File *_casa_fit.vms: một khối phổ thô kèm vùng nền và {len(f['thanh_phan'])} thành phần ở dạng Casa tự hiểu (CASA region / CASA comp), "
          "khi mở Casa tự dựng đường bao và các thành phần ngay trên phổ. Nền Tougaard ghi 'None'; đỉnh LA ghi dạng GL(30); "
          "Casa tính lại hình đỉnh theo định nghĩa của nó nên diện tích có thể lệch nhẹ so với app."]
    with open(pt, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return [pv, pt, pf]


def duong_an_toan_casa(vms):
    """CasaXPS (bản cũ, 32-bit) hay báo 'Error Opening VAMAS File' với đường dẫn có chữ có dấu, khoảng trắng, ký tự lạ hoặc quá dài.
    Chép file sang thư mục ngắn chỉ có chữ không dấu (C:\\Users\\Public\\EchemCasa hoặc tương đương) với tên đã làm sạch; đường dẫn đã an toàn thì giữ nguyên."""
    import re as _re
    import shutil
    import unicodedata
    ten = os.path.basename(vms)
    sach = unicodedata.normalize("NFKD", ten).encode("ascii", "ignore").decode("ascii")
    sach = _re.sub(r"[^A-Za-z0-9_.-]+", "_", sach).strip("._") or "casa.vms"
    if not sach.lower().endswith(".vms"):
        sach += ".vms"
    an_toan = (vms.isascii() and " " not in vms and len(vms) <= 100 and sach == ten)
    if an_toan:
        return vms
    for g in (os.environ.get("PUBLIC"), os.environ.get("ALLUSERSPROFILE"), r"C:\\", os.path.expanduser("~")):
        if not g:
            continue
        d = os.path.join(g, "EchemCasa")
        try:
            os.makedirs(d, exist_ok=True)
            if not d.isascii():
                continue
            dich = os.path.join(d, sach)
            shutil.copyfile(vms, dich)
            return dich
        except OSError:
            continue
    return vms


def _file_casa_exe():
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DienHoaOrigin", "casa_exe.txt")


def luu_casa_exe(duong):
    p = _file_casa_exe()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(duong)


def tim_casa_exe():
    """CasaXPS.exe: đường dẫn người dùng đã chọn trước đó, rồi tìm trong thư mục cài mặc định (Windows, kể cả ổ khác); không thấy trả None."""
    try:
        with open(_file_casa_exe(), encoding="utf-8") as fh:
            p = fh.read().strip()
        if p and os.path.isfile(p):
            return p
    except OSError:
        pass
    if os.name != "nt":
        return None
    goc = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
           os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"), r"C:\CasaXPS", r"D:\CasaXPS"]
    for g in goc:
        if not g or not os.path.isdir(g):
            continue
        for ten in os.listdir(g):
            if "casa" in ten.lower():
                for r, _, fs in os.walk(os.path.join(g, ten)):
                    for f in fs:
                        if f.lower() in ("casaxps.exe", "casa.exe"):
                            return os.path.join(r, f)
    return None
