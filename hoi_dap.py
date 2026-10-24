# -*- coding: utf-8 -*-
"""
Hỏi đáp về dữ liệu bằng tiếng Việt - KHÔNG dùng AI, không cần Internet.

Cách hoạt động: nhận diện từ khóa + con số trong câu hỏi (có dấu hoặc không dấu đều được),
chọn phép tính phù hợp trong cong_cu.py rồi trả lời bằng số liệu do code tính.
Câu hỏi nào không nhận diện được thì app nói rõ và gợi ý cách hỏi.
"""
import re
import unicodedata

from cong_cu import NguCanh  # noqa: F401  (để giao diện import từ một chỗ)

GOI_Y = """Bạn có thể hỏi (có dấu hoặc không dấu đều được):
  • liệt kê các file                       → loại phép đo, khoảng E, I, tốc độ quét
  • thông số của mẫu A / thông số file 2   → Epa, Ipa, Epc, Ipc, E1/2, I max, suy giảm dòng, Rs...
  • điện thế tại 10 mA                     → điện thế đạt 10 mA/cm² (có thể nhiều giá trị: 10 và 100 mA)
  • quá thế tại 10 mA                      → như trên, trừ điện thế cân bằng (mặc định 1.23 V; "cân bằng 0 V" để đổi)
  • dòng tại 1.6 V                         → mật độ dòng tại điện thế 1.6 V vs RHE
  • tafel / tafel vùng 5 đến 15 mA         → hệ số Tafel (mV/dec)
  • ecsa / ecsa cs 0.04 tại 1.0 V          → Cdl và ECSA từ các file CV
  • dòng lớn nhất / dòng trung bình từ 1.4 đến 1.9 V   → thống kê một đoạn E
  • dòng trung bình từ 0 đến 2 giờ         → thống kê một đoạn thời gian (file IT)
Thêm tên mẫu hoặc "file 2" để chỉ hỏi mẫu đó; không nói gì thì hỏi tất cả các file."""


# ====================== TIỆN ÍCH ======================
def chuan_hoa(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")
    s = s.replace("²", "2").replace("³", "3").replace("−", "-").replace("–", "-")
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    return s


NUM = r"-?\d+(?:\.\d+)?"


def fmt(x, nd=4):
    if x is None:
        return "—"
    try:
        return f"{float(x):.{nd}f}".rstrip("0").rstrip(".") if abs(float(x)) < 1e5 else f"{float(x):.4g}"
    except Exception:
        return str(x)


def chon_file(q, nc):
    """Trả về (danh_sach_chi_so, da_chi_dinh). q đã chuẩn hóa."""
    chon = []
    for m in re.finditer(r"(?:file|mau|so|sample)\s*(?:thu\s*)?(\d+)", q):
        k = int(m.group(1)) - 1
        if 0 <= k < len(nc.files) and k not in chon:
            chon.append(k)
    for k, (p, nh) in enumerate(nc.files):
        import os
        for ten in {chuan_hoa(nh).strip(), chuan_hoa(os.path.splitext(os.path.basename(p))[0]).strip()}:
            if len(ten) >= 2 and re.search(r"(?<![a-z0-9])" + re.escape(ten) + r"(?![a-z0-9])", q) and k not in chon:
                chon.append(k)
    if chon:
        return sorted(chon), True
    return list(range(len(nc.files))), False


def bo_tham_chieu_file(q):
    return re.sub(r"(?:file|mau|so|sample)\s*(?:thu\s*)?\d+", " ", q)


def nhan(nc, k):
    return nc.files[k][1]


def dong_loi(nc, k, kq):
    return f"  • {nhan(nc, k)}: không tính được - {kq['loi']}"


# ====================== TỪNG LOẠI CÂU HỎI ======================
def _liet_ke(nc, _q, _ds):
    kq = nc.liet_ke_file()
    dong = ["Các file đã nạp:"]
    for r in kq:
        if "loi" in r:
            dong.append(f"  {r['stt']}) {r['nhan']}: lỗi đọc file - {r['loi']}")
            continue
        if r["loai"] in ("CV", "LSV"):
            chi_tiet = (f"E {fmt(r['E_min_V'], 3)} → {fmt(r['E_max_V'], 3)} V vs RHE, "
                        f"I {fmt(r['I_min_mA_cm2'], 3)} → {fmt(r['I_max_mA_cm2'], 3)} mA/cm², "
                        f"{r['so_chu_ky']} chu kỳ, tốc độ quét ≈ {fmt(r['toc_do_quet_mV_s'], 1)} mV/s")
        elif r["loai"] == "IT":
            chi_tiet = (f"{fmt(r['thoi_gian_h'], 3)} giờ, E giữ {fmt(r['E_giu_V'], 3)} V, "
                        f"I trung bình {fmt(r['I_trung_binh_mA_cm2'], 3)} mA/cm²")
        else:
            chi_tiet = f"f từ {fmt(r['f_max_Hz'], 1)} Hz xuống {fmt(r['f_min_Hz'], 2)} Hz"
        dong.append(f"  {r['stt']}) {r['nhan']} [{r['loai']}, {r['so_diem']} điểm]: {chi_tiet}")
    return "\n".join(dong)


def _thong_so(nc, _q, ds):
    dong = ["Thông số tổng quát:"]
    for k in ds:
        try:
            kq = nc.thong_so(k + 1)
        except Exception as e:
            dong.append(f"  • {nhan(nc, k)}: không tính được - {e}")
            continue
        dong.append(f"  • {nhan(nc, k)} [{kq['loai']}]")
        if "bang_thong_so" in kq:
            for r in kq["bang_thong_so"]:
                dong.append("      " + ", ".join(f"{a} = {fmt(b)}" for a, b in r.items()))
        else:
            dong.append("      " + ", ".join(f"{a} = {fmt(b)}" for a, b in kq.items() if a != "loai"))
    return "\n".join(dong)


def _the_tai_dong(nc, q, ds):
    q2 = bo_tham_chieu_file(q)
    gia_tri = [float(m.group(1)) for m in re.finditer(rf"({NUM})\s*ma(?![a-z])", q2)]
    if not gia_tri:
        return "Bạn muốn điện thế tại mật độ dòng bao nhiêu? Ví dụ: “điện thế tại 10 mA”."
    e0 = None
    if re.search(r"qua the|overpotential|\beta\b", q2):
        m = re.search(rf"can bang\s*(?:la|=)?\s*({NUM})", q2)
        e0 = float(m.group(1)) if m else 1.23
    dong = ["Điện thế (V vs RHE) tại mật độ dòng cho trước:"]
    for k in ds:
        for j in gia_tri:
            kq = nc.the_tai_dong(k + 1, j, e0)
            if "loi" in kq:
                dong.append(dong_loi(nc, k, kq))
                continue
            s = f"  • {nhan(nc, k)}: E = {fmt(kq['E_V_vs_RHE'])} V tại {fmt(j)} mA/cm²"
            if e0 is not None:
                s += f"  →  quá thế = {fmt(kq['qua_the_mV'], 1)} mV (so với E cân bằng {fmt(e0)} V)"
            dong.append(s)
    return "\n".join(dong)


def _dong_tai_the(nc, q, ds):
    q2 = bo_tham_chieu_file(q)
    gia_tri = [float(m.group(1)) for m in re.finditer(rf"({NUM})\s*v(?![a-z])", q2)]
    if not gia_tri:
        return "Bạn muốn dòng tại điện thế bao nhiêu? Ví dụ: “dòng tại 1.6 V”."
    dong = ["Mật độ dòng tại điện thế cho trước:"]
    for k in ds:
        for e in gia_tri:
            kq = nc.dong_tai_the(k + 1, e) if True else None
            if "loi" in kq:
                dong.append(dong_loi(nc, k, kq))
            elif "I_mA_cm2" in kq:
                dong.append(f"  • {nhan(nc, k)}: I = {fmt(kq['I_mA_cm2'])} mA/cm² tại {fmt(e)} V")
            else:
                dong.append(f"  • {nhan(nc, k)}: I anodic = {fmt(kq['I_anodic_mA_cm2'])}, "
                            f"I cathodic = {fmt(kq['I_cathodic_mA_cm2'])} mA/cm² tại {fmt(e)} V (chu kỳ {kq['chu_ky']})")
    return "\n".join(dong)


def _tafel(nc, q, ds):
    q2 = bo_tham_chieu_file(q)
    vmin, vmax = 9.0, 11.0
    m = re.search(rf"({NUM})\s*(?:-|den|toi|~)\s*({NUM})", q2)
    if m:
        vmin, vmax = sorted((float(m.group(1)), float(m.group(2))))
    dong = [f"Hệ số Tafel (fit E theo log|J|, vùng {fmt(vmin)}–{fmt(vmax)} mA/cm²):"]
    for k in ds:
        kq = nc.tafel(k + 1, vmin, vmax)
        if "loi" in kq:
            dong.append(dong_loi(nc, k, kq))
        else:
            dong.append(f"  • {nhan(nc, k)}: {fmt(kq['he_so_Tafel_mV_dec'], 1)} mV/dec "
                        f"(R² = {fmt(kq['R2'], 4)}, {kq['so_diem']} điểm)")
    return "\n".join(dong)


def _ecsa(nc, q, ds, da_chi_dinh):
    q2 = bo_tham_chieu_file(q)
    cs = 0.040
    m = re.search(rf"\bcs\s*(?:=|la)?\s*({NUM})", q2)
    if m:
        cs = float(m.group(1))
    e = None
    m = re.search(rf"(?:tai|o|at)\s*({NUM})\s*v(?![a-z])", q2)
    if m:
        e = float(m.group(1))
    kq = nc.ecsa([k + 1 for k in ds] if da_chi_dinh else None, e, cs)
    if "loi" in kq:
        return "ECSA: " + kq["loi"]
    dong = [f"ECSA (lấy dòng tại E = {fmt(kq['E_lay_dong_V_vs_RHE'])} V vs RHE, Cs = {fmt(kq['Cs_mF_cm2'])} mF/cm²):",
            f"  • Cdl = {fmt(kq['Cdl_mF_cm2'])} mF/cm²   (R² = {fmt(kq['R2'], 5)})",
            f"  • ECSA = {fmt(kq['ECSA_cm2'])} cm²",
            "  Bảng điểm:"]
    for r in kq["bang_diem"]:
        dong.append(f"      {r['file']}: v = {fmt(r['toc_do_quet (mV/s)'], 1)} mV/s, (Ja−Jc)/2 = {fmt(r['(Ja-Jc)/2 (mA/cm2)'], 5)} mA/cm²")
    for c in kq.get("canh_bao", []):
        dong.append("  " + c)
    return "\n".join(dong)


def _thong_ke(nc, q, ds):
    q2 = bo_tham_chieu_file(q)
    tu = den = None
    don_vi = ""
    m = re.search(rf"({NUM})\s*(v|h|gio)?\s*(?:-|den|toi|~)\s*({NUM})\s*(v|h|gio)?(?![a-z])", q2)
    if m:
        tu, den = sorted((float(m.group(1)), float(m.group(3))))
        don_vi = m.group(4) or m.group(2) or ""
    dong = ["Thống kê" + (f" trong đoạn {fmt(tu)} – {fmt(den)} {({'gio': 'giờ', 'h': 'giờ', 'v': 'V'}).get(don_vi, '')}".rstrip() if m else " toàn bộ dữ liệu") + ":"]
    for k in ds:
        try:
            loai = nc.lay(k + 1)[1]["loai"]
        except Exception as e:
            dong.append(f"  • {nhan(nc, k)}: lỗi đọc file - {e}")
            continue
        if loai == "EIS":
            dong.append(f"  • {nhan(nc, k)}: file EIS, chưa hỗ trợ thống kê đoạn")
            continue
        bien = "T" if loai == "IT" else "E"
        if m and ((don_vi == "v" and bien == "T") or (don_vi in ("h", "gio") and bien == "E")):
            dong.append(f"  • {nhan(nc, k)}: file {loai} cần đoạn tính bằng {'giờ' if bien == 'T' else 'V'}")
            continue
        kq = nc.thong_ke_doan(k + 1, bien, tu, den)
        if "loi" in kq:
            dong.append(dong_loi(nc, k, kq))
        elif bien == "E":
            dong.append(f"  • {nhan(nc, k)}: I max = {fmt(kq['I_max_mA_cm2'])} mA/cm² (tại {fmt(kq['E_tai_I_max_V'])} V), "
                        f"I min = {fmt(kq['I_min_mA_cm2'])}, I trung bình = {fmt(kq['I_trung_binh_mA_cm2'])} mA/cm², "
                        f"diện tích ∫I dE = {fmt(kq['dien_tich_I_dE_mA_V_cm2'])} mA·V/cm²")
        else:
            dong.append(f"  • {nhan(nc, k)}: I trung bình = {fmt(kq['I_trung_binh_mA_cm2'])} mA/cm², "
                        f"đầu = {fmt(kq['I_dau_mA_cm2'])}, cuối = {fmt(kq['I_cuoi_mA_cm2'])}, "
                        f"max = {fmt(kq['I_max_mA_cm2'])}, min = {fmt(kq['I_min_mA_cm2'])} mA/cm²")
    return "\n".join(dong)


# ====================== ĐIỀU PHỐI ======================
def tra_loi(cau_hoi, nc):
    """Trả lời câu hỏi về dữ liệu. Luôn trả về chuỗi (kể cả khi không hiểu)."""
    q = chuan_hoa(cau_hoi).strip()
    if not q:
        return GOI_Y
    if not nc.files:
        return "Chưa chọn file số liệu nào (mục 1)."
    ds, da_chi_dinh = chon_file(q, nc)
    q2 = bo_tham_chieu_file(q)
    ket_qua = []

    co_ma = re.search(rf"{NUM}\s*ma(?![a-z])", q2) is not None
    co_v = re.search(rf"{NUM}\s*v(?![a-z])", q2) is not None
    co_khoang = re.search(rf"{NUM}\s*(?:v|h|gio)?\s*(?:-|den|toi|~)\s*{NUM}", q2) is not None

    if re.search(r"\b(?:goi y|huong dan|giup|help)\b|\bhoi (?:gi|nhung gi)\b", q):
        return GOI_Y
    if re.search(r"liet ke|danh sach|co nhung file|co file nao|file nao|tong quan file|\bcac file\b.*\bnao\b", q):
        ket_qua.append(_liet_ke(nc, q, ds))
    if re.search(r"\becsa\b|\bcdl\b|dien tich hoat dong", q):
        ket_qua.append(_ecsa(nc, q, ds, da_chi_dinh))
    if re.search(r"\btafel\b", q):
        ket_qua.append(_tafel(nc, q, ds))
    if co_ma and re.search(r"dien the|\be\b|qua the|overpotential|\beta\b|\bthe\b", q2):
        ket_qua.append(_the_tai_dong(nc, q, ds))
    if co_v and re.search(r"\bdong\b|mat do dong|\bi\b|\bj\b", q2) and not co_ma and not co_khoang:
        ket_qua.append(_dong_tai_the(nc, q, ds))
    if re.search(r"trung binh|lon nhat|nho nhat|\bmax\b|\bmin\b|dien tich|tich phan|thong ke", q2):
        ket_qua.append(_thong_ke(nc, q, ds))
    if not ket_qua and re.search(r"thong so|\bepa\b|\bipa\b|\bepc\b|\bipc\b|e1/2|\brs\b|\brct\b|r tong|suy giam|giu dong|"
                                 r"tong quat|ket qua|phan tich|\bnhan xet\b", q2):
        ket_qua.append(_thong_so(nc, q, ds))
    if not ket_qua:
        return "Mình chưa hiểu câu hỏi này.\n\n" + GOI_Y
    return "\n\n".join(ket_qua)
