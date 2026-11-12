# -*- coding: utf-8 -*-
"""
GÓI NỘP BÀI: từ kết quả đã xử lý, tạo
  • sheet "Bảng nộp bài"       : η, Tafel, độ bền... của từng mẫu trên một bảng để dán vào bài
  • sheet "Lặp lại (TB ± SD)"  : mẫu cùng tên gốc (Mau-1, Mau-2, Mau-3) -> trung bình ± độ lệch chuẩn, n
  • sheet "Kiểm tra nộp bài"   : danh sách việc còn thiếu (đối chứng, Pt/C, lặp lại, ECSA, độ bền, điều kiện đo...)
  • methods_dien_hoa.txt       : đoạn Methods (tiếng Anh + ghi chú tiếng Việt) điền từ thông số đã dùng
  • goi_tai_lap.zip            : dữ liệu thô + kết quả + thông số + phiên bản + câu "Data availability"
App chỉ tổng hợp số liệu đã xử lý; không thay đổi số liệu.
"""
import json
import math
import os
import re
import zipfile

DAU_OK, DAU_THIEU, DAU_XEM = "Đạt", "Thiếu", "Cần xem"
_RE_PT = re.compile(r"\b(pt|ruo2|iro2|ir/c|ru/c|pt/c|commercial|thuong mai|thương mại)\b", re.I)
_RE_DOI_CHUNG = re.compile(r"\b(bare|nf|cc|cp|blank|undoped|pristine|control|nen tran|nền trần|khong pha tap|không pha tạp)\b", re.I)
_RE_SAU = re.compile(r"(sau|after|post|used)", re.I)


def _so(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def goc_ten(nhan):
    """Mau-1, Mau_2, Mau (3), Mau #3 -> Mau"""
    return re.sub(r"[\s_\-]*[#(]?\d+\)?$", "", str(nhan)).strip() or str(nhan)


VAI_TRO = ["", "Mẫu chính", "Chuẩn (Pt/C, RuO₂/IrO₂)", "Đối chứng (nền trần, không pha tạp)", "Sau thử bền"]
DIEU_KIEN = [("dien_ly", "Điện ly và nồng độ (vd 1.0 M KOH)"), ("tham_chieu", "Điện cực tham chiếu (vd Hg/HgO, 1 M KOH)"),
             ("doi_cuc", "Điện cực đối (vd graphite rod)"), ("may_do", "Máy đo (vd CHI 760E)"), ("nhiet_do", "Nhiệt độ (°C)"),
             ("dien_cuc", "Điện cực làm việc / đế (vd nickel foam 1×1 cm²)"), ("muc_xt", "Mực xúc tác / cách phủ (vd 5 mg trong 1 mL ...)")]


def _json(a, ten):
    try:
        v = json.loads(getattr(a, ten, None) or "{}")
        return v if isinstance(v, dict) else {}
    except (ValueError, TypeError):
        return {}


def dk(a):
    """Điều kiện thí nghiệm người dùng khai báo (bỏ ô trống)."""
    return {k: str(v).strip() for k, v in _json(a, "dieu_kien_json").items() if str(v).strip()}


def vai_tro(a):
    """{nhãn: {'vai': ..., 'nhom': ...}} (bỏ mục trống)."""
    return {k: v for k, v in _json(a, "vai_tro_json").items() if isinstance(v, dict) and (v.get("vai") or v.get("nhom"))}


def _sheet(sheets, ten):
    return next((h for t, h in sheets if t == ten), [])


def bang_nop_bai(sheets, tafel):
    """Mỗi mẫu một dòng, gộp CV-LSV + Tafel + IT theo nhãn."""
    hang = {}
    for r in _sheet(sheets, "CV-LSV"):
        n = r.get("Nhãn")
        h = hang.setdefault(n, {"Nhãn": n})
        for k, v in r.items():
            if k.startswith(("Quá thế tại", "E tại", "Tốc độ quét")):
                h[k] = v
    for t in tafel or []:
        h = hang.setdefault(t.get("nhan"), {"Nhãn": t.get("nhan")})
        h["Tafel (mV/dec)"] = _so(t.get("he_so_Tafel (mV/dec)"))
    for r in _sheet(sheets, "IT"):
        h = hang.setdefault(r.get("Nhãn"), {"Nhãn": r.get("Nhãn")})
        for k, ten in (("thoi_gian (h)", "Thời gian đo (h)"), ("giu_dong (%)", "Giữ dòng (%)"), ("suy_giam (%)", "Suy giảm (%)"),
                       ("toc_do_suy_giam (%/h)", "Suy giảm (%/h)"), ("nhieu_da_loai (h)", "Nhiễu đã loại (h)")):
            if k in r:
                h[ten] = r[k]
    for r in _sheet(sheets, "Hiệu suất Faraday"):
        h = hang.setdefault(r.get("Nhãn"), {"Nhãn": r.get("Nhãn")})
        h["FE (%)"] = r.get("FE (%)")
    return [h for h in hang.values() if h.get("Nhãn")]


def lap_lai(bang, nhom_map=None):
    """Gộp theo nhóm người dùng gán (nếu có) hoặc tên gốc: n, TB ± SD cho mọi cột số. Chỉ nhóm có n >= 2."""
    nhom_map = nhom_map or {}
    nhom = {}
    for h in bang:
        nhom.setdefault(nhom_map.get(h["Nhãn"]) or goc_ten(h["Nhãn"]), []).append(h)
    kq = []
    for g, ds in nhom.items():
        if len(ds) < 2:
            continue
        r = {"Mẫu": g, "n": len(ds)}
        cot = [k for k in ds[0] if k != "Nhãn"]
        for k in cot:
            v = [x for x in (_so(h.get(k)) for h in ds) if x is not None]
            if len(v) >= 2:
                tb = sum(v) / len(v)
                sd = math.sqrt(sum((x - tb) ** 2 for x in v) / (len(v) - 1))
                r[k] = f"{tb:.4g} ± {sd:.2g}"
            elif v:
                r[k] = f"{v[0]:.4g}"
        kq.append(r)
    return kq


def kiem_tra(sheets, bang, a, ds, tafel):
    """Danh sách việc cần có khi nộp bài (đối chiếu các tiêu chí 5.3, 5.5, 7.1–7.7, 9.2, 10)."""
    nhan = [str(h["Nhãn"]) for h in bang] + [os.path.splitext(os.path.basename(p))[0] for p in ds]
    cot = {k for h in bang for k in h}
    out = []
    vt = vai_tro(a)
    nhom_map = {k: v.get("nhom") for k, v in vt.items() if v.get("nhom")}
    co_vai = lambda tien_to: any(str(v.get("vai", "")).startswith(tien_to) for v in vt.values())  # noqa: E731
    d_k = dk(a)

    def them(ma, noi_dung, ok, thieu="", xem=False):
        out.append({"Mục": ma, "Nội dung": noi_dung, "Trạng thái": DAU_XEM if xem else (DAU_OK if ok else DAU_THIEU), "Cần làm": "" if ok and not xem else thieu})

    them("7.1", "Quá thế tại 10 mA cm⁻²", any(k.startswith("Quá thế tại") for k in cot) and not getattr(a, "khong_qua_the", False),
         "Tick tính quá thế (nhập điện thế cân bằng) và đặt 10 trong 'mật độ dòng mục tiêu'.")
    them("7.2", "Độ dốc Tafel", bool(tafel), "Chạy phép Tafel cho các mẫu chính.")
    ecsa = bool(_sheet(sheets, "ECSA") or _sheet(sheets, "ECSA - điểm"))
    them("7.3", "ECSA / Cdl", ecsa, "Chạy ECSA (CV ở nhiều tốc độ quét trong vùng không có phản ứng).")
    gio = [_so(h.get("Thời gian đo (h)")) for h in bang if h.get("Thời gian đo (h)") is not None]
    gio = [g for g in gio if g is not None]
    if gio:
        mx = max(gio)
        them("7.4", f"Độ bền (dài nhất {mx:.4g} h)", mx >= 200, "Mốc điểm cao: ≥200 h (tối đa ở ≥500 h). Cần đo thêm hoặc nêu rõ giới hạn.", xem=mx < 200)
    else:
        them("7.4", "Độ bền (i-t / CP)", False, "Thêm phép đo i-t hoặc CP dài hạn, báo cáo giờ và % giữ dòng.")
    them("7.5", "Điện áp ô điện phân (2 điện cực)", bool(getattr(a, "khong_rhe", False)), "Nếu có đo điện phân tổng (2 điện cực), thêm LSV ở chế độ 'Không quy đổi RHE'.", xem=not getattr(a, "khong_rhe", False))
    thieu = []
    if not (getattr(a, "r_s", 0) or 0):
        thieu.append("bù iR (Rs)")
    if not getattr(a, "tai_trong", None):
        thieu.append("tải lượng xúc tác (mg cm⁻²)")
    if not any(k.startswith("Tốc độ quét") for k in cot):
        thieu.append("tốc độ quét")
    for k, ten in (("dien_ly", "điện ly"), ("tham_chieu", "điện cực tham chiếu"), ("doi_cuc", "điện cực đối")):
        if k not in d_k:
            thieu.append(ten)
    them("7.6", "Điều kiện đo (điện ly, điện cực tham chiếu/đối, RHE, bù iR, tải lượng, tốc độ quét)", not thieu,
         "Chưa khai báo: " + ", ".join(thieu) + ". Điền ở nút 🧪 Điều kiện đo (tab Xuất, gồm tải lượng) và Rs ở tab Phân tích.")
    def _so_dong(k):
        m = re.search(r"tại\s*([\d.]+)\s*mA", k)
        return float(m.group(1)) if m else 0.0
    them("9.3", "Dòng lớn ≥500 mA cm⁻² (quá thế/điện thế ở mật độ dòng công nghiệp)", any(_so_dong(k) >= 500 for k in cot),
         "Thêm 500 vào 'mật độ dòng mục tiêu' (ví dụ 10, 100, 500) nếu đường LSV đạt tới; nếu không, đo ở dòng lớn hoặc trong thiết bị AEM/PEM.", xem=True)
    them("7.7", "Có Pt/C (hoặc RuO₂/IrO₂) đo cùng điều kiện", co_vai("Chuẩn") or any(_RE_PT.search(n) for n in nhan),
         "Đo Pt/C (HER) hoặc RuO₂/IrO₂ (OER) cùng điện cực, điện ly, tải lượng; gán vai trò 'Chuẩn' ở nút 🏷 hoặc đặt tên có 'Pt/C'.")
    them("5.3", "Mẫu đối chứng (nền trần, không pha tạp)", co_vai("Đối chứng") or any(_RE_DOI_CHUNG.search(n) for n in nhan),
         "Thêm nền trần (NF/CC) và mẫu không pha tạp; gán vai trò 'Đối chứng' ở nút 🏷 hoặc đặt tên có 'bare', 'NF', 'undoped'.")
    n_max = max([r["n"] for r in lap_lai(bang, nhom_map)] or [0])
    them("5.5", f"Lặp lại ≥3 điện cực (hiện n = {n_max or 1})", n_max >= 3, "Đo ≥3 điện cực độc lập; điền cột Nhóm (hoặc đặt tên Mau-1, Mau-2, Mau-3) để app tính TB ± SD.", xem=0 < n_max < 3)
    them("9.2", "Có mẫu sau thử bền (post-test)", co_vai("Sau thử bền") or any(_RE_SAU.search(n) for n in nhan),
         "Đo lại XRD/XPS/SEM sau thử bền; gán vai trò 'Sau thử bền' hoặc đặt tên 'sau'/'after'.", xem=not co_vai("Sau thử bền"))
    return out


def doan_methods(a, ds):
    ph, eref = getattr(a, "ph", None), getattr(a, "eref", None)
    s = getattr(a, "chia_i", None)
    rs, pct = getattr(a, "r_s", 0) or 0, getattr(a, "ir_phan_tram", 100)
    d_k = dk(a)
    muc = []
    cau_dk = []
    if d_k.get("dien_cuc"):
        cau_dk.append(f"The working electrode was {d_k['dien_cuc']}.")
    if d_k.get("muc_xt"):
        cau_dk.append(f"The catalyst ink was prepared with {d_k['muc_xt']}.")
    ke = ", ".join(x for x in (f"{d_k['tham_chieu']} reference electrode" if d_k.get("tham_chieu") else "", f"{d_k['doi_cuc']} counter electrode" if d_k.get("doi_cuc") else "") if x)
    if d_k.get("dien_ly") or ke or d_k.get("may_do"):
        s0 = "Electrochemical measurements were performed"
        if d_k.get("may_do"):
            s0 += f" on a {d_k['may_do']}"
        s0 += " in a three-electrode configuration"
        if d_k.get("dien_ly"):
            s0 += f" in {d_k['dien_ly']}"
        if ke:
            s0 += f" with a {ke}"
        if d_k.get("nhiet_do"):
            s0 += f" at {d_k['nhiet_do']} °C"
        cau_dk.insert(0, s0 + ".")
    else:
        cau_dk.append("[Electrolyte and concentration, reference and counter electrodes, instrument, temperature.]")
    muc.append(" ".join(cau_dk) + " ")
    muc.append(f"All potentials were converted to the reversible hydrogen electrode (RHE) scale using E(RHE) = E(measured) + {getattr(a, 'nernst', 0.0592):g} × pH + {eref} V (pH = {ph}). "
               if not getattr(a, "khong_rhe", False) else "Potentials are reported as measured (two-electrode cell voltage, no RHE conversion). ")
    muc.append(f"Current densities were normalized to the geometric electrode area ({s} cm²). ")
    if rs:
        muc.append(f"Ohmic drop was compensated at {pct:g}% (Rs = {rs} Ω determined by EIS). ")
    else:
        muc.append("[Ohmic drop (iR) compensation: state whether and how it was applied.] ")
    eb = getattr(a, "e_can_bang", None)
    if eb is not None:
        muc.append(f"Overpotentials were calculated against the equilibrium potential of {eb} V. ")
    muc.append(f"Tafel slopes were obtained by linear fitting of E versus log|j| in the range {getattr(a, 'tafel_min', '')}–{getattr(a, 'tafel_max', '')} mA cm⁻². ")
    muc.append(f"The electrochemically active surface area was estimated from the double-layer capacitance (Cdl) using Cs = {getattr(a, 'cs', 0.04)} mF cm⁻². ")
    if getattr(a, "tai_trong", None):
        muc.append(f"The catalyst loading was {a.tai_trong} mg cm⁻². ")
    else:
        muc.append("[Catalyst loading (mg cm⁻²), ink composition and deposition method.] ")
    txt = "".join(muc).strip()
    tv = ("\n\nGHI CHÚ (tiếng Việt): các mục trong [ngoặc vuông] là thông tin app chưa có; điền ở nút 🧪 Điều kiện đo (tab Xuất) rồi chạy lại, "
          "hoặc tự viết thêm: tải lượng, tốc độ quét. Bài chỉ được điểm 7.6 và 10.3 khi các thông tin này đủ.\n"
          f"Đoạn trên được tạo từ thông số đã dùng khi xử lý (Echem Studio {_phien_ban()}).")
    return "ELECTROCHEMICAL MEASUREMENTS (draft)\n" + txt + tv + "\n"


def _phien_ban():
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.json"), encoding="utf-8") as f:
            return json.load(f).get("phien_ban_hien_tai", "?")
    except Exception:
        return "?"


def _thong_so_dict(a):
    kq = {}
    for k, v in sorted(vars(a).items()):
        if isinstance(v, (str, int, float, bool, type(None))) or (isinstance(v, (list, tuple)) and all(isinstance(x, (str, int, float)) for x in v)):
            kq[k] = v
    return kq


def goi_tai_lap(a, ds, thu_muc, duong_zip=None):
    """Zip: du_lieu_tho/, ket_qua/, tham_so.json, PHIEN_BAN.txt, data_availability.txt. Trả về đường dẫn zip."""
    duong_zip = duong_zip or os.path.join(thu_muc, "goi_tai_lap.zip")
    cau = ("Data availability: The raw and processed data supporting this study (raw potentiostat files, processed curves, fitted parameters "
           "and the processing parameters) are provided in the Supporting Information and deposited at [repository DOI, e.g. Zenodo]. "
           f"Data were processed with Echem Studio v{_phien_ban()}.\n")
    with zipfile.ZipFile(duong_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in ds:
            if os.path.isfile(p):
                z.write(p, "du_lieu_tho/" + os.path.basename(p))
        for goc, _, files in os.walk(thu_muc):
            for f in files:
                p = os.path.join(goc, f)
                if os.path.abspath(p) == os.path.abspath(duong_zip) or f.lower().endswith((".opju", ".opj", ".zip", ".log")):
                    continue
                if os.path.getsize(p) > 200 * 1048576:
                    continue
                z.write(p, "ket_qua/" + os.path.relpath(p, thu_muc).replace(os.sep, "/"))
        z.writestr("tham_so.json", json.dumps(_thong_so_dict(a), ensure_ascii=False, indent=2, default=str))
        z.writestr("PHIEN_BAN.txt", f"Echem Studio v{_phien_ban()}\n")
        z.writestr("data_availability.txt", cau)
    return duong_zip


def tao(sheets, a, ds, thu_muc, tafel):
    """Thêm sheet nộp bài vào `sheets` (sửa tại chỗ) và ghi methods + gói tái lập. Trả về list file đã tạo."""
    bang = bang_nop_bai(sheets, tafel)
    vt = vai_tro(a)
    if vt:
        for h in bang:
            v = vt.get(h["Nhãn"], {})
            h["Vai trò"], h["Nhóm"] = v.get("vai", ""), v.get("nhom", "")
        bang = [{"Nhãn": h["Nhãn"], "Vai trò": h["Vai trò"], "Nhóm": h["Nhóm"], **{k: x for k, x in h.items() if k not in ("Nhãn", "Vai trò", "Nhóm")}} for h in bang]
    moi = []
    if bang:
        moi.append(("Bảng nộp bài", bang))
        ll = lap_lai([{k: x for k, x in h.items() if k not in ("Vai trò", "Nhóm")} for h in bang], {k: v.get("nhom") for k, v in vt.items() if v.get("nhom")})
        if ll:
            moi.append(("Lặp lại (TB ± SD)", ll))
    moi.append(("Kiểm tra nộp bài", kiem_tra(sheets, bang, a, ds, tafel)))
    vt = next((i for i, (t, _) in enumerate(sheets) if t == "Cảnh báo"), len(sheets))
    sheets[vt:vt] = moi
    tao_ra = []
    p = os.path.join(thu_muc, "methods_dien_hoa.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(doan_methods(a, ds))
    tao_ra.append(p)
    return tao_ra
