# -*- coding: utf-8 -*-
"""Lấy NGUYÊN số liệu do CasaXPS tạo (phổ thô, nền, đường bao, từng thành phần, phần dư) thay vì để app tự tính lại.
Casa có lệnh trên thanh công cụ 'Copy Spectra to Clipboard TAB ASCII' / 'Save TAB ASCII to Clipboard' / 'Save Tab Spaced ASCII File'
(tên lấy từ chuỗi trong CasaXPS.exe 2.3.24). Module này: (1) rê chuột qua từng nút thanh công cụ để đọc tooltip và ghi vào nhật ký,
(2) bấm nút xuất, tự tick các ô Component/Envelope/Residual/Background trong hộp thoại tuỳ chọn, (3) đọc clipboard (hoặc file),
(4) phân tích bảng TAB thành các cột. Không có phần nào được tính lại: số trong app = số Casa."""
import re
import time

TOOLTIP_UU_TIEN = [r"Copy Spectra to Clipboard TAB ASCII", r"Save TAB ASCII to Clipboard", r"Save Tab Spaced ASCII", r"Save TAB ASCII Data from Display Tiles",
                   r"Save Tab ASCII"]


def _so(s):
    try:
        return float(str(s).strip().replace(",", "."))
    except ValueError:
        return None


def doc_bang_tab(text):
    """Bảng TAB/CSV của Casa -> dict(cot=[(ten, np.array)], ghi_chu). Tìm khối dòng số dài nhất (cột đầu là năng lượng tăng/giảm đều),
    tên cột ghép từ tối đa 4 dòng chữ ngay phía trên. Ném ValueError nếu không thấy bảng số."""
    import numpy as np
    dong = [l.rstrip("\r") for l in text.replace("\r\n", "\n").split("\n")]
    sep = "\t" if sum(l.count("\t") for l in dong) >= sum(l.count(",") for l in dong) else ","
    cells = [l.split(sep) for l in dong]

    def la_so(c):
        return len(c) >= 3 and _so(c[0]) is not None and sum(_so(x) is not None for x in c[1:]) >= 2
    tot, bd = (0, 0), None
    i = 0
    while i < len(cells):
        if la_so(cells[i]):
            j = i
            while j < len(cells) and la_so(cells[j]):
                j += 1
            if j - i > tot[1] - tot[0]:
                tot = (i, j)
            i = j
        else:
            i += 1
    if tot[1] - tot[0] < 20:
        raise ValueError("Không thấy bảng số liệu trong dữ liệu Casa xuất ra.")
    a, b = tot
    nc = max(len(c) for c in cells[a:b])
    bang = np.full((b - a, nc), np.nan)
    for r in range(b - a):
        for k, x in enumerate(cells[a + r]):
            v = _so(x)
            if v is not None:
                bang[r, k] = v
    ten = []
    tren = [c for c in cells[max(0, a - 4):a] if any(x.strip() for x in c)]
    for k in range(nc):
        ps = [c[k].strip() for c in tren if k < len(c) and c[k].strip()]
        ten.append(" ".join(ps) if ps else f"cot{k}")
    cot = [(ten[k], bang[:, k]) for k in range(nc) if not np.all(np.isnan(bang[:, k]))]
    return {"cot": cot, "dau": [l for l in dong[:a] if l.strip()][:12]}


def phan_loai_cot(cot, ten_thanh_phan=()):
    """Gán cột theo tên: x (năng lượng), tho, nen, bao, du, thanh_phan[]. Trả về dict hoặc ném ValueError nếu không đủ."""
    r = {"x": cot[0], "tho": None, "nen": None, "bao": None, "du": None, "tp": []}
    for ten, v in cot[1:]:
        t = ten.lower()
        if "resid" in t and r["du"] is None:
            r["du"] = (ten, v)
        elif re.search(r"backgr|\bbg\b", t) and r["nen"] is None:
            r["nen"] = (ten, v)
        elif re.search(r"envelope|synthetic.*env|\bfit\b|\bsum\b", t) and r["bao"] is None:
            r["bao"] = (ten, v)
        elif any(n and n.lower() in t for n in ten_thanh_phan) or re.search(r"comp|synthetic", t):
            r["tp"].append((ten, v))
        elif r["tho"] is None:
            r["tho"] = (ten, v)
    if r["tho"] is None or r["bao"] is None or r["du"] is None:
        raise ValueError("Bảng Casa thiếu cột: " + ", ".join(k for k in ("tho", "bao", "du") if r[k] is None))
    return r


def kq_tu_cot_casa(r, khoi, t_thu, hv, comps_casa, dich=0.0):
    """Dựng kết quả app TRỰC TIẾP từ các cột của Casa (không tính lại gì). comps_casa = kết quả doc_casa_ghi_chu (vị trí/FWHM/diện tích)."""
    import numpy as np
    import xps
    x = np.asarray(r["x"][1], float)
    ten_x = r["x"][0].lower()
    be = hv - x if "kinetic" in ten_x or "ke" == ten_x.strip() else x
    tho = np.asarray(r["tho"][1], float)
    # đơn vị: Casa có thể xuất CPS hoặc Counts; so với phổ trong file để biết hệ số
    hs = 1.0
    y_file = np.interp(be, *(lambda o: (khoi["be"][o], khoi["y"][o]))(np.argsort(khoi["be"])))
    m = np.nanmedian(tho / np.maximum(y_file, 1e-9))
    if t_thu and abs(m - t_thu) < 0.05 * t_thu:
        hs = 1.0 / t_thu
    if not r["nen"]:
        raise ValueError("Bảng Casa không có cột nền (Background) - hãy tick Background trong hộp tuỳ chọn xuất.")
    nen = np.asarray(r["nen"][1], float) * hs
    bao = np.asarray(r["bao"][1], float) * hs
    du = np.asarray(r["du"][1], float) * hs
    tho = tho * hs
    cac = [np.asarray(v, float) * hs for _, v in r["tp"]]
    o = np.argsort(be)
    be, tho, nen, bao, du = be[o] + dich, tho[o], nen[o], bao[o], du[o]
    cac = [c[o] for c in cac]
    # cột thành phần của Casa có thể đã cộng nền (đường cong vẽ trên nền) hoặc không: nếu trung bình ngang nền thì trừ nền để có dạng đỉnh
    cac = [c - nen if float(np.nanmean(c)) > 0.5 * float(np.nanmean(nen)) else c for c in cac]
    thanh = []
    tong = sum(c["dien_tich"] for c in comps_casa["thanh_phan"]) or 1.0
    for c in comps_casa["thanh_phan"]:
        thanh.append({"ten": c["ten"], "vt": c["vt_be"] + dich, "fwhm": c["fwhm"], "cao": 0.0, "dt": c["dien_tich"], "tach": 0.0, "ti_le": 0.0, "la": None,
                      "o_bien": [], "pct": 100.0 * c["dien_tich"] / tong})
    # phần dư trong cột Casa có thể đã gồm nền (phổ - đường bao) hoặc không; dùng đúng như Casa đưa
    k = len(thanh)
    rstd = xps.residual_std(du, tho, t_thu, 3 * k, be)
    fit = {"thanh_phan": thanh, "cac": cac, "mo_hinh": bao - nen, "phan_du": du, "rstd": rstd, "tu_tuong_quan": xps.tu_tuong_quan(du), "ssr": float(du @ du), "so_tham_so": 3 * k}
    kq = {"be": be, "y": tho, "nen": nen, "ys": tho - nen, "fit": fit, "tp": [],
          "ghi": ["SỐ LIỆU LẤY NGUYÊN TỪ CASA (phổ thô, nền, đường bao, thành phần, phần dư do Casa xuất); app không tính lại."],
          "dich_hieu_chuan": dich, "be_day_du": be, "y_day_du": tho,
          "tham_so_fit": {"t_thu": t_thu, "m": 30.0, "nen": "shirley", "dw": xps.DW_FWHM, "vung": (float(be.min()), float(be.max())), "ung_vien": [], "tu_casa": True}}
    if t_thu:
        kq["ghi"].append(f"Đối chiếu: căn tổng bình phương phần dư của Casa = {float(np.sqrt(np.sum(du ** 2))) * t_thu:.4g} (counts) - so với 'RMS =' trong cửa sổ Components của Casa.")
    kq["canh_bao"] = xps.danh_gia(kq)
    return kq
