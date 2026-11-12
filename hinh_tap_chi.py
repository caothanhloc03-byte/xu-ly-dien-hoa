# -*- coding: utf-8 -*-
"""
Quy cách hình theo TỪNG TẠP CHÍ (lấy từ trang hướng dẫn tác giả chính thức, tra cứu 11/2026) cho hình ghép nhiều ô.
Mỗi mẫu: bề rộng cột (cm), chiều cao tối đa, cỡ chữ (pt) ở KÍCH THƯỚC CUỐI, độ dày nét (pt), dpi, chữ ô.
Wiley, Springer... mỗi tạp chí một khác nên KHÔNG có mẫu: dùng "Tùy chỉnh" rồi đối chiếu hướng dẫn riêng của tạp chí.
"""
import math

CHE_DO_SUB = 0.7      # matplotlib thu chỉ số trên/dưới còn ~70% cỡ chữ gốc (mathtext)

MAU = {
    "Tùy chỉnh": dict(
        don=8.6, rd=None, doi=17.8, cao=24.0, tick=8, nhan=9, ct=7, nhan_o=11, lw=1.5, khung=1.0, dpi=600, dang=("png", "pdf", "tiff"),
        chu_o=None, min_font=None, max_font=None, sub_min=None, lw_min=None, lw_max=None, nguon="",
        ghi_chu=["Quy cách tự đặt (khổ 8.6 / 17.8 cm), không theo tạp chí nào: hãy đối chiếu hướng dẫn tác giả."]),
    "ACS": dict(
        don=8.25, rd=None, doi=17.78, cao=24.13, tick=7, nhan=8, ct=6, nhan_o=8, lw=1.2, khung=1.0, dpi=600, dang=("tiff", "pdf", "png"),
        chu_o=None, min_font=5, max_font=None, sub_min=5, lw_min=1.0, lw_max=None,
        nguon="https://pubsapp.acs.org/paragonplus/submission/general/graphics_prep.html",
        ghi_chu=["ACS: cột đơn 3.25 in (8.25 cm), cột đôi 7 in, cao tối đa 9.5 in; chữ ≥ 5 pt ở kích thước cuối; nét ≥ 1 pt; ≥ 600 dpi."]),
    "RSC": dict(
        don=8.3, rd=None, doi=17.1, cao=23.3, tick=7, nhan=8, ct=7, nhan_o=8, lw=1.2, khung=1.0, dpi=600, dang=("tiff", "pdf", "png"),
        chu_o=None, min_font=7, max_font=None, sub_min=None, lw_min=None, lw_max=None,
        nguon="https://www.rsc.org/journals-books-databases/author-and-reviewer-hub/authors-information/prepare-and-format/figures-graphics-images",
        ghi_chu=["RSC: cột đơn 8.3 cm, cột đôi 17.1 cm, cao tối đa 23.3 cm; ≥ 600 dpi; ưu tiên TIFF.",
                 "RSC không nêu cỡ chữ chung cho đồ thị (chỉ cấu trúc hóa học: 7 pt Arial/Helvetica); app dùng ≥ 7 pt cho an toàn."]),
    "Elsevier": dict(
        don=9.0, rd=14.0, doi=19.0, cao=24.0, tick=7, nhan=9, ct=8.6, nhan_o=9, lw=1.2, khung=1.0, dpi=1000, dang=("tiff", "pdf", "png"),
        chu_o=None, min_font=7, max_font=None, sub_min=6, lw_min=None, lw_max=None,
        nguon="https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions/artwork-sizing",
        ghi_chu=["Elsevier: cột đơn 90 mm, 1.5 cột 140 mm, cột đôi 190 mm; chữ ≥ 7 pt, chỉ số trên/dưới ≥ 6 pt; 1000 dpi cho nét (500 dpi hình ghép ảnh, 300 dpi ảnh).",
                 "Elsevier không nêu chiều cao tối đa (app đặt 24 cm). Nhiều tạp chí Elsevier có quy cách riêng: kiểm tra hướng dẫn của tạp chí."]),
    "Nature": dict(
        don=8.9, rd=12.0, doi=18.3, cao=24.7, tick=6, nhan=7, ct=6, nhan_o=8, lw=1.0, khung=0.75, dpi=600, dang=("pdf", "tiff", "png"),
        chu_o="thuong", min_font=5, max_font=7, sub_min=None, lw_min=0.25, lw_max=1.0,
        nguon="https://www.nature.com/nature/for-authors/final-submission",
        ghi_chu=["Nature: cột đơn 89 mm, 1.5 cột 120–136 mm, cột đôi 183 mm, cao tối đa 247 mm; sans-serif (Helvetica/Arial); nhãn ô a, b, c in đậm 8 pt;",
                 "chữ khác 5–7 pt; nét 0.25–1 pt; ảnh raster 300–600 dpi, đồ thị nên xuất vector (PDF/EPS).",
                 "Lưu ý: chỉ số trên/dưới trong nhãn (mũ, chỉ số) bị thu còn ~70% cỡ chữ, tức ~4.9 pt khi chữ trục 7 pt: sát giới hạn 5 pt, kiểm tra bản in thử."]),
}
TEN_MAU = list(MAU)


def mau(ten):
    return dict(MAU.get(ten) or MAU["Tùy chỉnh"], ten=ten if ten in MAU else "Tùy chỉnh")


def rong_cm(m, cot):
    """cot: 1 = đơn, 15 = 1.5 cột, 2 = đôi. Mẫu không có 1.5 cột thì dùng cột đôi."""
    if cot == 1:
        return m["don"]
    if cot == 15 and m.get("rd"):
        return m["rd"]
    return m["doi"]


def kieu_chu(m):
    """Cỡ chữ thực dùng: chữ có mathtext (nhãn trục, chú thích) phải đủ lớn để chỉ số trên/dưới không nhỏ hơn mức tối thiểu."""
    sm = m.get("sub_min")
    nhan, ct = m["nhan"], m["ct"]
    if sm:
        can = math.ceil(sm / CHE_DO_SUB * 10) / 10
        nhan, ct = max(nhan, can), max(ct, can)
    return {"tick": m["tick"], "nhan": nhan, "ct": ct, "nhan_o": m["nhan_o"], "lw": m["lw"], "khung": m["khung"]}


def kiem_chuan(m, st, w_cm, h_cm, dpi, dang):
    """Danh sách (trạng thái, nội dung) đối chiếu hình thực tế với quy cách của mẫu."""
    kq = []
    kq.append(("Đạt" if w_cm <= m["doi"] + 1e-6 else "Lưu ý", f"Bề rộng {w_cm:.2f} cm (cột đơn {m['don']} cm{f', 1.5 cột {m['rd']} cm' if m.get('rd') else ''}, cột đôi {m['doi']} cm)."))
    kq.append(("Đạt" if h_cm <= m["cao"] + 1e-6 else "Lưu ý", f"Chiều cao {h_cm:.2f} cm (tối đa {m['cao']} cm)."))
    mf = m.get("min_font")
    nho = min(st["tick"], st["ct"], st["nhan"], st["nhan_o"])
    if mf:
        kq.append(("Đạt" if nho >= mf else "Lưu ý", f"Chữ nhỏ nhất {nho:g} pt (yêu cầu ≥ {mf:g} pt)."))
    if m.get("max_font"):
        lon = max(st["tick"], st["ct"], st["nhan"])
        kq.append(("Đạt" if lon <= m["max_font"] else "Lưu ý", f"Chữ trục/chú thích lớn nhất {lon:g} pt (yêu cầu ≤ {m['max_font']:g} pt; nhãn ô riêng {st['nhan_o']:g} pt)."))
    if m.get("sub_min"):
        sub = min(st["nhan"], st["ct"]) * CHE_DO_SUB
        kq.append(("Đạt" if sub >= m["sub_min"] - 1e-6 else "Lưu ý", f"Chỉ số trên/dưới ≈ {sub:.1f} pt (yêu cầu ≥ {m['sub_min']:g} pt)."))
    if m.get("lw_min") is not None:
        kq.append(("Đạt" if st["lw"] >= m["lw_min"] and st["khung"] >= m["lw_min"] else "Lưu ý", f"Nét dữ liệu {st['lw']:g} pt, khung {st['khung']:g} pt (yêu cầu ≥ {m['lw_min']:g} pt)."))
    if m.get("lw_max") is not None:
        kq.append(("Đạt" if st["lw"] <= m["lw_max"] and st["khung"] <= m["lw_max"] else "Lưu ý", f"Nét dữ liệu {st['lw']:g} pt, khung {st['khung']:g} pt (yêu cầu {m.get('lw_min', 0):g}–{m['lw_max']:g} pt)."))
    kq.append(("Đạt" if dpi >= m["dpi"] else "Lưu ý", f"{dpi} dpi (khuyến nghị ≥ {m['dpi']})."))
    if m.get("chu_o") == "thuong":
        kq.append(("Đạt", "Nhãn ô dùng chữ thường a, b, c (Nature)."))
    return kq
