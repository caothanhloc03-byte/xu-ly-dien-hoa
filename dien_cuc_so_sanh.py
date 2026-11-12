# -*- coding: utf-8 -*-
"""Danh sách điện cực so sánh thường dùng và điện thế so với SHE (V, ~25 °C) để điền ô Eref.
Các số là GIÁ TRỊ THAM KHẢO (phụ thuộc nồng độ dung dịch trong điện cực, nhiệt độ, hãng): nếu datasheet điện cực của bạn khác thì sửa ô Eref.
Không dùng thư viện ngoài (cả giao_dien.pyw và công cụ GCD cùng import)."""

TUY_CHINH = "Tùy chỉnh (tự nhập Eref)"
DIEN_CUC = [
    ("Hg/HgO (1 M KOH)  0.098 V", 0.098),
    ("Hg/HgO (1 M NaOH)  0.140 V", 0.140),
    ("Ag/AgCl (KCl bão hòa)  0.197 V", 0.197),
    ("Ag/AgCl (3 M KCl)  0.210 V", 0.210),
    ("SCE calomel (KCl bão hòa)  0.241 V", 0.241),
    ("Hg/Hg₂SO₄ (K₂SO₄ bão hòa)  0.640 V", 0.640),
    ("SHE / NHE  0 V", 0.0),
    (TUY_CHINH, None),
]
TEN = [t for t, _ in DIEN_CUC]
NERNST_25C = 0.0592   # 2.303RT/F ở 25 °C (chính xác 0.05916 V)


def eref_cua(ten):
    """Eref (V so với SHE) của lựa chọn; None nếu là 'Tùy chỉnh' hoặc tên lạ."""
    for t, v in DIEN_CUC:
        if t == ten:
            return v
    return None


def ten_theo_eref(eref, dung_sai=1e-6):
    """Tên điện cực khớp với giá trị Eref đang đặt (để hiện lại trong hộp chọn); không khớp → 'Tùy chỉnh'."""
    try:
        x = float(str(eref).replace(",", "."))
    except (TypeError, ValueError):
        return TUY_CHINH
    for t, v in DIEN_CUC:
        if v is not None and abs(v - x) <= dung_sai:
            return t
    return TUY_CHINH


def sang_rhe(e, ph, eref, nernst=0.059):
    """E(RHE) = E đo + nernst × pH + Eref."""
    return e + float(nernst) * float(ph) + float(eref)
