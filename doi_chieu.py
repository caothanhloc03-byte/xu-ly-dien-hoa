# -*- coding: utf-8 -*-
"""
ĐỐI CHIẾU CHÉO XRD – HR-TEM – XPS (tiêu chí 8.3) và SO SÁNH TRƯỚC/SAU THỬ BỀN (tiêu chí 9.2).
Nhập số liệu từ các công cụ XRD/HR-TEM/XPS (mỗi dòng một giá trị); app kiểm tra chúng có nhất quán không.
  • d(HR-TEM) phải trùng d tính từ vị trí đỉnh XRD (Bragg) trong dung sai
  • kích thước tinh thể Scherrer (XRD) phải ≤ hoặc cùng bậc với kích thước hạt TEM
  • năng lượng liên kết XPS so với giá trị tham khảo của trạng thái oxy hóa (chỉ để định hướng, cần đối chiếu tài liệu)
  • đỉnh XRD / BE XPS trước và sau thử bền: giữ, mới xuất hiện, biến mất, dịch
"""
import math
import re

LAM_CU = 1.5406

# BE tham khảo (eV) vạch chính, chỉ để định hướng; cần đối chiếu NIST XPS / tài liệu trước khi kết luận
THAM_CHIEU_XPS = {
    "Ni0 (2p3/2)": 852.6, "Ni2+ (2p3/2)": 855.6, "Ni3+ (2p3/2)": 856.3,
    "Co0 (2p3/2)": 778.1, "Co3+ (2p3/2)": 779.8, "Co2+ (2p3/2)": 781.0,
    "Fe0 (2p3/2)": 706.8, "Fe2+ (2p3/2)": 709.8, "Fe3+ (2p3/2)": 711.0,
    "Cu0 (2p3/2)": 932.6, "Cu2+ (2p3/2)": 934.4, "Pt0 (4f7/2)": 71.2, "Ru0 (3d5/2)": 280.0, "Ru4+ (3d5/2)": 280.8,
    "Mo4+ (3d5/2)": 229.2, "Mo6+ (3d5/2)": 232.6, "P (2p, phosphide)": 129.5, "P5+ (phosphate)": 133.5,
    "S2- (2p3/2)": 161.9, "O lattice (1s)": 529.8, "O-H (1s)": 531.4, "N pyridinic (1s)": 398.5,
}


def d_tu_2theta(tt, lam=LAM_CU):
    return lam / (2.0 * math.sin(math.radians(tt) / 2.0))


def scherrer_nm(fwhm_deg, tt, lam=LAM_CU, K=0.9, inst_deg=0.0):
    b2 = fwhm_deg ** 2 - inst_deg ** 2
    if b2 <= 0:
        return None
    b = math.radians(math.sqrt(b2))
    return K * lam / (b * math.cos(math.radians(tt) / 2.0)) / 10.0


def doc_dong(text):
    """Mỗi dòng: số đầu, các số sau, phần chữ còn lại. Trả về list[(list_so, nhan)]."""
    kq = []
    for ln in str(text or "").replace(",", ".").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        tok, so = ln.split(), []
        while tok and len(so) < 3:
            try:
                so.append(float(tok[0]))
            except ValueError:
                break
            tok.pop(0)
        if tok and tok[0].lower() in ("nm", "å", "a", "ang", "deg", "°", "ev"):
            tok.pop(0)
        nhan = " ".join(tok).strip(" ,;:")
        if so:
            kq.append((so, nhan))
    return kq


def _d_nm(v):
    """HR-TEM nhập nm (0.2) hoặc Å (2.0): >1 coi là Å."""
    return v / 10.0 if v > 1.0 else v


def doi_chieu(xrd, hrtem, tem_nm, xps, lam=LAM_CU, dung_sai_d=0.03, fwhm_may=0.0):
    """xrd: [(2θ, FWHM?), nhan]; hrtem: d; tem_nm: list kích thước hạt; xps: BE. Trả về (list dòng kết quả, tóm tắt)."""
    out, ok, bad = [], 0, 0
    dx = [(d_tu_2theta(s[0], lam) / 10.0, s, n) for s, n in xrd]
    for s, n in hrtem:
        d = _d_nm(s[0])
        if not dx:
            out.append(("8.3", f"HR-TEM d = {d:.4f} nm", "Cần xem", "chưa nhập đỉnh XRD để đối chiếu"))
            continue
        g = min(dx, key=lambda x: abs(x[0] - d))
        sl = (d - g[0]) / g[0]
        if abs(sl) <= dung_sai_d:
            ok += 1
            out.append(("8.3", f"HR-TEM d = {d:.4f} nm {n}", "Khớp", f"XRD 2θ = {g[1][0]:.2f}° → d = {g[0]:.4f} nm (lệch {sl * 100:+.1f}%) {g[2]}"))
        else:
            bad += 1
            out.append(("8.3", f"HR-TEM d = {d:.4f} nm {n}", "Không khớp", f"đỉnh XRD gần nhất 2θ = {g[1][0]:.2f}° → d = {g[0]:.4f} nm (lệch {sl * 100:+.1f}%): "
                                                                  "kiểm tra hiệu chuẩn pixel HR-TEM, pha vô định hình/bề mặt, hoặc gán sai mặt"))
    kt = []
    for s, n in xrd:
        if len(s) >= 2 and s[1] > 0:
            L = scherrer_nm(s[1], s[0], lam, inst_deg=fwhm_may)
            if L:
                kt.append(L)
                out.append(("8.3", f"Scherrer 2θ = {s[0]:.2f}°, FWHM = {s[1]:.3f}°", "Thông tin", f"kích thước tinh thể ≈ {L:.1f} nm {n}"))
    if kt and tem_nm:
        tl, tm = sum(kt) / len(kt), sum(tem_nm) / len(tem_nm)
        r = tl / tm
        if 0.4 <= r <= 1.3:
            ok += 1
            out.append(("8.3", "Scherrer ↔ TEM", "Khớp", f"Scherrer TB {tl:.1f} nm; TEM TB {tm:.1f} nm (tỉ lệ {r:.2f}; Scherrer thường ≤ hạt TEM vì hạt có thể đa tinh thể)"))
        else:
            bad += 1
            out.append(("8.3", "Scherrer ↔ TEM", "Không khớp", f"Scherrer TB {tl:.1f} nm so với TEM TB {tm:.1f} nm (tỉ lệ {r:.2f}): "
                                                           "có thể do giãn nở ứng suất, hạt đa tinh thể hoặc chưa trừ độ rộng máy"))
    for s, n in xps:
        be = s[0]
        g = min(THAM_CHIEU_XPS.items(), key=lambda kv: abs(kv[1] - be))
        if abs(g[1] - be) <= 0.8:
            out.append(("8.3", f"XPS BE = {be:.2f} eV {n}", "Gần tham khảo", f"gần {g[0]} = {g[1]} eV (lệch {be - g[1]:+.2f} eV); cần dẫn tài liệu"))
        else:
            out.append(("8.3", f"XPS BE = {be:.2f} eV {n}", "Cần xem", f"không gần giá trị tham khảo nào trong bảng (gần nhất {g[0]} = {g[1]} eV); tra tài liệu/NIST"))
    tt = f"{ok} mục khớp, {bad} mục không khớp." + (" Nên xử lý các mục không khớp trước khi nộp." if bad else " Bức tranh đa kỹ thuật nhất quán trên các số đã nhập.")
    return out, tt


def so_truoc_sau(truoc, sau, dung_sai, don_vi):
    """Danh sách vị trí đỉnh trước/sau: giữ (dịch), biến mất, mới."""
    out, dung = [], set()
    for v in truoc:
        if not sau:
            break
        j = min(range(len(sau)), key=lambda k: abs(sau[k] - v))
        if abs(sau[j] - v) <= dung_sai:
            dung.add(j)
            ds = sau[j] - v
            out.append(("9.2", f"{v:.2f} {don_vi}", "Giữ", f"sau thử bền {sau[j]:.2f} {don_vi} (dịch {ds:+.2f})"))
        else:
            out.append(("9.2", f"{v:.2f} {don_vi}", "Biến mất", "không còn đỉnh tương ứng sau thử bền: nêu rõ trong bài (hòa tan/tái cấu trúc)"))
    for k, v in enumerate(sau):
        if k not in dung:
            out.append(("9.2", f"{v:.2f} {don_vi}", "Mới", "đỉnh mới sau thử bền: có thể là pha hoạt động thật (oxy-hydroxit...) hoặc nhiễm bẩn; gán pha"))
    return out


def tao_bao_cao(lam, xrd, hrtem, tem, xps, truoc_xrd, sau_xrd, truoc_xps, sau_xps, dung_sai_d=0.03):
    cx, hr = doc_dong(xrd), doc_dong(hrtem)
    tm = [s[0] for s, _ in doc_dong(tem)]
    xp = doc_dong(xps)
    kq, tt = doi_chieu(cx, hr, tm, xp, lam, dung_sai_d)
    a, b = [s[0] for s, _ in doc_dong(truoc_xrd)], [s[0] for s, _ in doc_dong(sau_xrd)]
    c, d = [s[0] for s, _ in doc_dong(truoc_xps)], [s[0] for s, _ in doc_dong(sau_xps)]
    if a or b:
        kq += [("9.2 XRD",) + r[1:] for r in so_truoc_sau(a, b, 0.3, "° 2θ")]
    if c or d:
        kq += [("9.2 XPS",) + r[1:] for r in so_truoc_sau(c, d, 0.5, "eV")]
    dong = ["ĐỐI CHIẾU CHÉO & TRƯỚC/SAU THỬ BỀN", f"Tóm tắt: {tt}", ""]
    for m, nd, tr, gc in kq:
        dong.append(f"[{m}] {tr:<13} {nd}  →  {gc}")
    dong += ["", "Lưu ý: bảng BE XPS chỉ để định hướng; mọi gán trạng thái oxy hóa phải dẫn tài liệu hoặc NIST XPS."]
    return "\n".join(dong), kq
