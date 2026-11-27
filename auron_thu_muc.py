# -*- coding: utf-8 -*-
"""
AURON làm việc trong một thư mục do người dùng chỉ định.

  quet(goc)                → danh sách "bài" (mỗi thư mục chứa dữ liệu = một bài) kèm loại phép đo nhận diện được
  phan_tich_lenh(cau)      → hiểu câu lệnh gõ trong khung chat ("chạy toàn bộ data", "chỉ chạy EIS và GCD"...), None nếu chỉ là câu hỏi
  ghi_lenh / lay_lenh      → kênh AURON → app (file JSON trong thư mục tạm, app đọc mỗi giây)
  chay_gcd / chay_xps / chay_xrd → phân tích + vẽ không cần cửa sổ (CV/LSV/IT/EIS/ECSA/Tafel do chính đường chạy của app xử lý)

Nhận diện theo TÊN thư mục (rồi thư mục cha, rồi tên file), sau đó đối chiếu với NỘI DUNG file; nếu hai bên mâu thuẫn thì giao cho app tự nhận dạng từng file.
Dữ liệu gốc không bao giờ bị sửa: mọi kết quả ghi vào <thư mục>/Ket_qua_AURON/.
"""
import json
import os
import re
import tempfile
import threading
import time
import unicodedata

TEN_KET_QUA = "Ket_qua_AURON"
LOAI_HIEN = {"CV": "CV", "LSV": "LSV", "IT": "i-t (độ bền)", "EIS": "EIS", "ECSA": "ECSA (Cdl)", "TAFEL": "Tafel", "AUTO": "tự nhận dạng từng file",
             "GCD": "GCD (siêu tụ/pin)", "XPS": "XPS", "XRD": "XRD", "HRTEM": "HR-TEM", "?": "không rõ"}
# loại do đường chạy chung của app xử lý
LOAI_DUONG_APP = ("CV", "LSV", "IT", "EIS", "ECSA", "TAFEL", "AUTO")
# thứ tự ưu tiên khi tên thư mục chứa nhiều từ khóa (từ cụ thể đến chung)
_TU_KHOA = [
    ("ECSA", ("ecsa", "cdl", "ecsa-cv")),
    ("TAFEL", ("tafel",)),
    ("GCD", ("gcd", "galvanostatic", "chargedischarge", "charge-discharge", "nap-xa", "napxa", "supercap", "supercapacitor")),
    ("XPS", ("xps", "casa", "vamas")),
    ("XRD", ("xrd", "xray", "x-ray")),
    ("HRTEM", ("hrtem", "hr-tem", "tem", "fft", "saed")),
    ("EIS", ("eis", "impedance", "nyquist", "tong-tro", "tongtro")),
    ("CV", ("cv", "cyclic", "voltammetry", "voltam")),
    ("LSV", ("lsv", "oer", "her", "orr", "polarization", "polarisation", "linear-sweep", "phan-cuc")),
    ("IT", ("it", "i-t", "chrono", "chronoamperometry", "stability", "do-ben", "durability")),
]
DUOI_SO_LIEU = (".txt", ".csv", ".dat", ".xlsx", ".xlsm", ".xls", ".vms", ".vamas", ".xy", ".mpt")
DUOI_ANH_TEM = (".tif", ".tiff", ".dm3", ".dm4", ".emi", ".ser")
DUOI_ANH_CHUNG = (".png", ".jpg", ".jpeg", ".bmp")
BO_QUA_THU_MUC = {TEN_KET_QUA.lower(), "csv_va_anh_nhanh", "_lich_su_chay", "_sao_luu", "xem_truoc", "__pycache__", "ket_qua", "results"}
BO_QUA_HAU_TO = ("_xuly.csv", "_thongso.csv", "_ecsa.csv", "_ecsa_diem.csv", "_tafel.csv", "fit_eis.csv", "pho_xep_chong.csv")


def bo_dau(s):
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _tu(s):
    """Tách thành các từ (chữ-số), giữ 'i-t' và 'hr-tem' như một từ."""
    s = bo_dau(s)
    s = s.replace("i-t", "i~t").replace("hr-tem", "hr~tem").replace("charge-discharge", "charge~discharge").replace("linear-sweep", "linear~sweep")
    return [t.replace("~", "-") for t in re.split(r"[^a-z0-9~]+", s) if t]


def doan_theo_ten(ten, chat=False):
    """Loại phép đo suy từ một chuỗi tên (thư mục/file/lệnh). chat=True: 'it' chỉ tính khi viết dạng i-t (tránh nhầm với 'ít')."""
    ds = doan_nhieu(ten, chat)
    return ds[0] if ds else None


def doan_nhieu(ten, chat=False):
    tu = _tu(ten)
    ra = []
    for loai, kws in _TU_KHOA:
        for k in kws:
            if any(t == k or re.fullmatch(re.escape(k) + r"\d+", t) or (len(k) >= 4 and t.startswith(k)) for t in tu):
                if chat and loai == "IT" and k == "it":
                    continue
                if loai not in ra:
                    ra.append(loai)
                break
    return ra


# ====================== QUÉT THƯ MỤC ======================
def _hop_le_thu_muc(ten):
    t = ten.lower()
    return t not in BO_QUA_THU_MUC and not t.startswith(("_", "."))


def _lay_file(thu_muc):
    so_lieu, anh = [], []
    try:
        ds = sorted(os.listdir(thu_muc))
    except OSError:
        return [], []
    for ten in ds:
        p = os.path.join(thu_muc, ten)
        t = ten.lower()
        if not os.path.isfile(p) or t.startswith("~$") or t.startswith("bao_cao") or t.endswith(BO_QUA_HAU_TO):
            continue
        if t.endswith(DUOI_SO_LIEU):
            so_lieu.append(p)
        elif t.endswith(DUOI_ANH_TEM):
            anh.append(p)
        elif t.endswith(DUOI_ANH_CHUNG):
            anh.append(p)
    return so_lieu, anh


def _doc_dau(p, n=25):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return "".join(f.readline() for _ in range(n))
    except OSError:
        return ""


def _loai_noi_dung(files):
    """Loại suy từ nội dung (tối đa 5 file đầu): trả (loai, ghi_chu)."""
    dem = {}
    for p in files[:5]:
        t = p.lower()
        if t.endswith((".vms", ".vamas")):
            dem["XPS"] = dem.get("XPS", 0) + 1
            continue
        if t.endswith((".xlsx", ".xlsm", ".xls")):
            continue
        dau = bo_dau(_doc_dau(p))
        if "2theta" in dau or "2-theta" in dau or "two theta" in dau:
            dem["XRD"] = dem.get("XRD", 0) + 1
            continue
        if dau.startswith("vamas"):
            dem["XPS"] = dem.get("XPS", 0) + 1
            continue
        if t.endswith((".txt", ".csv", ".dat")):
            try:
                import nhan_dang_nhanh as nd
                r = nd.phat_hien(p)["loai"]
            except Exception:  # noqa: BLE001
                r = "?"
            if r in ("CV", "LSV", "IT", "EIS"):
                dem[r] = dem.get(r, 0) + 1
    if not dem:
        return None
    loai = max(dem, key=dem.get)
    return loai


def phan_loai(thu_muc, goc, files, anh):
    """→ (loai, nguon, ghi_chu)."""
    chuoi = []                                       # tên thư mục từ gần đến xa (không lấy phần trên thư mục gốc)
    p = thu_muc
    while True:
        chuoi.append(os.path.basename(p) or p)
        if os.path.normpath(p) == os.path.normpath(goc) or os.path.dirname(p) == p:
            break
        p = os.path.dirname(p)
    loai, nguon = None, ""
    for k, ten in enumerate(chuoi):
        loai = doan_theo_ten(ten)
        if loai:
            nguon = "tên thư mục" if k == 0 else f"tên thư mục cha '{ten}'"
            break
    if not loai and files:
        ds = [doan_theo_ten(os.path.splitext(os.path.basename(f))[0]) for f in files]
        dem = {}
        for d in ds:
            if d:
                dem[d] = dem.get(d, 0) + 1
        if dem:
            loai = max(dem, key=dem.get)
            nguon = "tên file"
    nd_loai = _loai_noi_dung(files) if files else None
    ghi = ""
    if loai in ("CV", "LSV", "IT", "EIS") and nd_loai in ("CV", "LSV", "IT", "EIS") and nd_loai != loai:
        ghi = f"tên ghi {LOAI_HIEN[loai]} nhưng nội dung giống {LOAI_HIEN[nd_loai]}: để app tự nhận dạng từng file"
        loai = "AUTO"
    if not loai:
        if nd_loai:
            loai, nguon = nd_loai, "nội dung file"
        elif anh and any(a.lower().endswith(DUOI_ANH_TEM) for a in anh):
            loai, nguon = "HRTEM", "định dạng ảnh"
        elif any(f.lower().endswith((".txt", ".csv", ".dat")) for f in files):
            loai, nguon, ghi = "AUTO", "mặc định", "không rõ phép đo từ tên: để app tự nhận dạng từng file"
        else:
            loai = "?"
    return loai, nguon, ghi


def quet(goc, toi_da_cap=6):
    """Mọi thư mục (kể cả chính thư mục gốc) có file dữ liệu → danh sách bài. Mỗi bài: id, ten, thu_muc, loai, nguon, files, so_file, chay, ghi_chu."""
    goc = os.path.abspath(goc)
    bai = []
    if not os.path.isdir(goc):
        return bai
    for d, ds_con, _ in os.walk(goc):
        ds_con[:] = sorted(x for x in ds_con if _hop_le_thu_muc(x))
        if d[len(goc):].count(os.sep) >= toi_da_cap:
            ds_con[:] = []
        so_lieu, anh = _lay_file(d)
        # ảnh PNG/JPG chỉ tính khi thư mục được gọi tên là HR-TEM (tránh nhận nhầm hình do app xuất)
        ten_loai = doan_theo_ten(os.path.basename(d))
        anh_tem = [a for a in anh if a.lower().endswith(DUOI_ANH_TEM) or ten_loai == "HRTEM"]
        if not so_lieu and not anh_tem:
            continue
        loai, nguon, ghi = phan_loai(d, goc, so_lieu or anh_tem, anh_tem)
        files = anh_tem if loai == "HRTEM" else so_lieu
        if loai == "XPS":
            files = [f for f in so_lieu if f.lower().endswith((".vms", ".vamas", ".xlsx", ".xlsm", ".txt"))]
        if loai in LOAI_DUONG_APP:
            files = [f for f in so_lieu if f.lower().endswith((".txt", ".csv", ".dat"))]
            if not files:
                continue
        rel = os.path.relpath(d, goc)
        bai.append(dict(id=len(bai) + 1, ten=os.path.basename(goc) if rel == "." else rel, thu_muc=d, loai=loai, nguon=nguon, files=files,
                        so_file=len(files), chay=loai not in ("?", "HRTEM"), ghi_chu=ghi
                        + ("HR-TEM cần chọn vùng ảnh và thang nm/px nên AURON không tự chạy: mở công cụ HR-TEM để đo." if loai == "HRTEM" else "")
                        + ("Không nhận diện được phép đo." if loai == "?" else "")))
    return bai


def tom_tat_ke_hoach(bai, goc=""):
    if not bai:
        return "Không tìm thấy thư mục nào có file số liệu (.txt, .csv, .dat, .xlsx, .vms...)" + (f" trong {goc}." if goc else ".")
    dong = [f"Tìm thấy {len(bai)} thư mục có dữ liệu" + (f" trong {goc}" if goc else "") + ":"]
    for b in bai:
        s = f"{b['id']}. {b['ten']} → {LOAI_HIEN.get(b['loai'], b['loai'])} ({b['so_file']} file" + (f"; theo {b['nguon']}" if b["nguon"] else "") + ")"
        if b["ghi_chu"]:
            s += " — " + b["ghi_chu"]
        dong.append(s)
    dem = {}
    for b in bai:
        dem[b["loai"]] = dem.get(b["loai"], 0) + 1
    dong.append("Gồm: " + ", ".join(f"{LOAI_HIEN.get(k, k)} ×{v}" for k, v in dem.items()) + ". Kết quả sẽ lưu trong thư mục con " + TEN_KET_QUA + "; dữ liệu gốc không bị sửa.")
    return "\n".join(dong)


def loc_bai(bai, loai=None, ten=None, chi_chay_duoc=True):
    """loai: tập mã loại (None = mọi loại); ten: danh sách chuỗi con của tên thư mục/ số thứ tự."""
    ra = []
    for b in bai:
        if chi_chay_duoc and not b["chay"]:
            continue
        if loai and b["loai"] not in loai and not (b["loai"] == "AUTO" and loai & {"CV", "LSV", "IT", "EIS"}):
            continue
        if ten:
            bt = bo_dau(b["ten"])
            if not any((t.isdigit() and int(t) == b["id"]) or bo_dau(t) in bt for t in ten):
                continue
        ra.append(b)
    return ra


# ====================== HIỂU LỆNH ======================
_RE_DUONG_DAN = re.compile(r"""(?:"([^"]+)"|'([^']+)'|([A-Za-z]:[\\/][^"'<>|?*\r\n]*)|(\\\\[^\s"'<>|?*]+(?:[\\/][^"'<>|?*\r\n]*)?))""")
_HOI = ("cach ", "nhu the nao", "lam sao", "lam the nao", "huong dan", "la gi", "tai sao", "vi sao", "co the khong", "duoc khong", "nghia la")


def _lam_sach_duong_dan(s):
    return s.strip().rstrip(" .,;!")


def phan_tich_lenh(cau):
    """Câu gõ trong chat → dict lệnh hoặc None (câu hỏi bình thường).
    Các lệnh: chon_thu_muc(duong_dan?), quet, chay(tat_ca, loai, ten), dung, trang_thai."""
    if not cau or not cau.strip():
        return None
    s = re.sub(r"^[^a-z0-9]+", "", bo_dau(cau).strip())
    if "?" in cau or any(x in s + " " for x in _HOI):
        return None
    m = _RE_DUONG_DAN.search(cau)
    duong = _lam_sach_duong_dan(next(g for g in m.groups() if g)) if m else None
    dau = re.match(r"^(?:hay |vui long |nho |ban |auron |giup toi |giup |xin |lam on |chi |cu |chi can )*", s).end()
    s2 = s[dau:]
    if re.match(r"^(dung|huy|ngung|stop|thoi)\b", s2) and not re.search(r"\bthu muc\b", s2):
        return dict(lenh="dung")
    if re.search(r"\b(tien do|den dau roi|dang lam gi|trang thai|xong chua)\b", s2):
        return dict(lenh="trang_thai")
    co_thu_muc = bool(re.search(r"\bthu muc\b", s2))
    if re.match(r"^(chon|mo|dat|doi|lam viec (trong|voi|o)|vao|cd|nap)\b", s2) and (co_thu_muc or duong):
        return dict(lenh="chon_thu_muc", duong_dan=duong)
    if duong and not re.match(r"^(chay|ve|phan tich|xu ly|tinh)\b", s2):
        return dict(lenh="chon_thu_muc", duong_dan=duong)
    if re.match(r"^(quet|nhan dien|nhan dang|liet ke|kiem tra thu muc|xem thu muc|co gi trong)\b", s2):
        return dict(lenh="quet")
    if re.match(r"^(chay|ve|phan tich|xu ly|tinh|lam|bat dau|tien hanh|thuc hien)\b", s2):
        s3 = re.sub(r"^(chay lai|chay|ve lai|ve|phan tich|xu ly|tinh toan|tinh|lam|bat dau|tien hanh|thuc hien)\s*", "", s2)
        tat_ca = bool(re.search(r"\b(toan bo|tat ca|het|moi thu|moi du lieu|cac thu muc|all)\b", s2))
        loai = set(doan_nhieu(cau, chat=True))
        # "it" viết hoa/ i-t được nhận qua chat=True; lọc thêm các từ thường gặp không phải phép đo
        ten = [a for a, _ in re.findall(r"""["']([^"']+)["']()""", cau) if a]
        ten += re.findall(r"\bthu muc\s+([a-z0-9_\-.]+)", s2)
        ten = [t for t in ten if bo_dau(t) not in ("nay", "do", "hien tai", "tren", "nao", "chi", "dinh", "da", "chon")]
        m_so = re.search(r"\b(?:bai|so|muc)\s+(\d+(?:\s*(?:,|va|and|\+)\s*\d+)*)", s2)
        if m_so:
            ten += re.findall(r"\d+", m_so.group(1))
        return dict(lenh="chay", tat_ca=tat_ca, loai=sorted(loai), ten=ten, nguyen_van=cau.strip(), con_lai=s3)
    return None


def mo_ta_lenh(c):
    k = c["lenh"]
    if k == "chon_thu_muc":
        return ("Đã nhận: mở thư mục " + c["duong_dan"]) if c.get("duong_dan") else "Đã nhận: ngài chọn thư mục làm việc trong hộp thoại vừa mở trên Echem Studio."
    if k == "quet":
        return "Đã nhận: quét và nhận diện lại thư mục làm việc."
    if k == "dung":
        return "Đã nhận: dừng việc đang chạy."
    if k == "trang_thai":
        return "Đã nhận: tôi báo tiến độ ngay."
    if k == "chay":
        pham_vi = "toàn bộ dữ liệu" if c["tat_ca"] and not c["loai"] and not c["ten"] else (
            ", ".join(LOAI_HIEN.get(x, x) for x in c["loai"]) + (" · " if c["loai"] and c["ten"] else "") + (", ".join(c["ten"]) if c["ten"] else ""))
        return f"Đã nhận: chạy {pham_vi or 'dữ liệu'} trong thư mục làm việc." if (c["tat_ca"] or c["loai"] or c["ten"]) else \
            "Ngài muốn chạy toàn bộ hay chỉ một số phép đo (ví dụ: 'chạy toàn bộ data', 'chỉ chạy EIS và GCD')? Tôi cần ngài nói rõ để không chạy nhầm."
    return ""


# ====================== KÊNH AURON → APP ======================
def duong_dan_lenh():
    return os.environ.get("ECHEM_AURON_LENH") or os.path.join(tempfile.gettempdir(), "echem_auron_lenh.json")


_KHOA = threading.Lock()


def ghi_lenh(lenh, p=None):
    p = p or duong_dan_lenh()
    with _KHOA:
        try:
            with open(p, "r", encoding="utf-8") as f:
                ds = json.load(f)
            if not isinstance(ds, list):
                ds = []
        except (OSError, ValueError):
            ds = []
        ds.append(dict(lenh, luc=time.time()))
        tam = p + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(ds[-20:], f, ensure_ascii=False)
        os.replace(tam, p)


def lay_lenh(p=None):
    """Đọc và XÓA các lệnh đang chờ (app gọi mỗi giây)."""
    p = p or duong_dan_lenh()
    if not os.path.isfile(p):
        return []
    with _KHOA:
        try:
            with open(p, "r", encoding="utf-8") as f:
                ds = json.load(f)
            os.remove(p)
        except (OSError, ValueError):
            try:
                os.remove(p)
            except OSError:
                pass
            return []
    return [d for d in ds if isinstance(d, dict) and time.time() - d.get("luc", 0) < 600]


# ====================== CHẠY KHÔNG CỬA SỔ: GCD / XPS / XRD ======================
def _ra(job, goc_ra):
    d = os.path.join(goc_ra, re.sub(r"[^\w\-. ]+", "_", job["ten"]).strip() or "bai")
    os.makedirs(d, exist_ok=True)
    return d


def chay_gcd(job, goc_ra, log=print):
    import gcd_pin as gp
    ds, loi = [], []
    for p in job["files"]:
        if not p.lower().endswith((".txt", ".csv", ".dat", ".xlsx", ".xlsm", ".mpt")):
            continue
        ten = os.path.splitext(os.path.basename(p))[0]
        cs = gp.doc_thong_so_cs(p)
        kl = cs.get("khoi_luong_mg") or gp.khoi_luong_tu_ten(ten)
        if not kl:
            loi.append(f"{ten}: bỏ qua vì không thấy khối lượng (tên file ghi dạng 2.32mg hoặc file CS Studio có Mass); nhập khối lượng trong công cụ Siêu tụ/Pin.")
            continue
        tt = dict(ten=ten, path=p, gia_tri=float(kl))
        dong = cs.get("dong_mA") or _dong_tu_ten(ten)
        if dong:
            tt["dong_ma"] = dong
        ds.append(tt)
    if not ds:
        raise ValueError("Không có file GCD nào đủ thông tin" + (": " + "; ".join(loi[:2]) if loi else "") + ".")
    kq = gp.chay(ds, {})
    loi += [f"{t}: {e}" for t, e in kq.get("loi", [])]
    if not kq["mau"]:
        raise ValueError("Không phân tích được mẫu GCD nào: " + "; ".join(loi[:3]))
    d = _ra(job, goc_ra)
    tep = []
    try:
        gp.xuat_hinh(kq, d, ten="GCD")
        tep.append("hình GCD (PNG)")
    except Exception as e:  # noqa: BLE001
        loi.append(f"không vẽ được hình: {e}")
    try:
        import csv
        tong = gp.bang_ket_qua(kq)[0]
        if tong:
            with open(os.path.join(d, "GCD_ket_qua.csv"), "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=list(tong[0].keys()))
                w.writeheader()
                w.writerows(tong)
            tep.append("GCD_ket_qua.csv")
    except Exception as e:  # noqa: BLE001
        loi.append(f"không ghi được bảng: {e}")
    try:
        import auron_danh_gia as ag
        ag.thu_ghi(ag.tu_gcd, kq)
    except Exception:  # noqa: BLE001
        pass
    return dict(tep=tep, loi=loi, thu_muc_ra=d, tom_tat=f"{len(kq['mau'])} mẫu GCD")


def _dong_tu_ten(ten):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*mA", ten, re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def chay_xps(job, goc_ra, log=print):
    import xps
    d = _ra(job, goc_ra)
    tep, loi, tom, bo_qua = [], [], [], []
    for p in job["files"]:
        if not p.lower().endswith((".vms", ".vamas", ".xlsx", ".xlsm", ".txt")):
            continue
        base = os.path.splitext(os.path.basename(p))[0]
        try:
            vung = xps.doc_xps(p)
        except Exception as e:  # noqa: BLE001
            loi.append(f"{base}: không đọc được ({e})")
            continue
        if isinstance(vung, dict):
            vung = vung.get("vung") or [vung]
        dich_c1s = None
        sap = sorted(vung, key=lambda v: 0 if "c1s" in bo_dau(v.get("ten", "")).replace(" ", "") else 1)
        for v in sap:
            ten = (v.get("ten") or "").replace(" ", "")
            khoa = bo_dau(ten).replace("scan", "")
            khoa_l = bo_dau(v.get("loai") or "").replace(" ", "")
            mau = next((k for k in xps.MAU if bo_dau(k).replace(" ", "") in (khoa, khoa_l)), None)
            if not mau and khoa in ("ru3d", "ru3d+c1s") and "Ru3d+C1s" in xps.MAU:
                mau = "Ru3d+C1s"
            if not mau:
                if khoa != "survey":
                    bo_qua.append(f"{base}·{v.get('ten', '?').strip()}")
                continue
            cfg = xps.VUNG_MAU.get(mau)
            if not cfg:
                continue
            try:
                ds, uv = xps.MAU[mau]
                t = (v["dwell"] * v["scans"]) if v.get("dwell") and v.get("scans") and v["dwell"] < 100 else None
                dich_san = None if cfg.get("ten_ref") else (dich_c1s if dich_c1s is not None else 0.0)
                kq = xps.phan_tich_pho(v["be"], v["y"], mau, tp=[xps.ThanhPhan(**c.dict()) for c in ds], ung_vien=[], vung=cfg["vung"],
                                       dich_chuan=cfg["ref"] or 284.8, khoang_do=cfg["khoang"] or (cfg["vung"][1], cfg["vung"][0]),
                                       nen="shirley", t_thu=t, tu_chon=False, dich_san=dich_san, tp_chuan_theo=cfg.get("ten_ref") or "C-C")
            except Exception as e:  # noqa: BLE001
                loi.append(f"{base} · {ten}: fit không được ({str(e)[:120]})")
                continue
            if mau.startswith("C1s") and dich_c1s is None:
                dich_c1s = float(kq["dich_hieu_chuan"])
            ten_ra = f"{base}_{mau}"
            try:
                xps.ve_hinh(kq, os.path.join(d, ten_ra + ".png"), ten=f"{base} · {mau}")
                tep.append(ten_ra + ".png")
                with open(os.path.join(d, ten_ra + "_bao_cao.txt"), "w", encoding="utf-8") as f:
                    f.write(xps.bao_cao_van_ban(kq, ten=ten_ra))
            except Exception as e:  # noqa: BLE001
                loi.append(f"{ten_ra}: không vẽ/ghi được ({str(e)[:100]})")
            tom.append(f"{base}·{mau}")
            try:
                import auron_danh_gia as ag
                ag.thu_ghi(ag.tu_xps, kq, mau, base)
            except Exception:  # noqa: BLE001
                pass
    if not tom:
        raise ValueError("Không có vùng phổ nào khớp mẫu có sẵn (C1s, O1s, N1s, Ti2p, S2p...)" + (": " + "; ".join(loi[:3]) if loi else "") + ".")
    if bo_qua:
        loi.append("Chưa có mẫu fit cho vùng: " + ", ".join(bo_qua) + " (mở công cụ XPS để tự đặt thành phần).")
    return dict(tep=tep, loi=loi, thu_muc_ra=d, tom_tat=f"{len(tom)} vùng XPS ({', '.join(tom[:4])}{'...' if len(tom) > 4 else ''})")


def chay_xrd(job, goc_ra, log=print):
    import xrd
    import xrd_ngan_hang as nh
    d = _ra(job, goc_ra)
    tep, loi, cac = [], [], []
    for p in job["files"]:
        try:
            cac += xrd.doc_xrd(p)
        except Exception as e:  # noqa: BLE001
            loi.append(f"{os.path.basename(p)}: không đọc được ({str(e)[:100]})")
    if not cac:
        raise ValueError("Không đọc được mẫu XRD nào" + (": " + "; ".join(loi[:3]) if loi else "") + ".")
    bank = nh.toan_bo()
    kq = [xrd.phan_tich_mau(m, bank, xrd.NGUON_MAC_DINH, 5.0, 0.15, tat_ca_pha=bank) for m in cac]
    chuan = next((m["ten"] for m in cac if m["ten"].strip().upper() == "NF"), None)
    ss = xrd.so_sanh(kq, chuan, 0.15)
    ra = xrd.xuat_tat_ca(kq, ss, d, ten="XRD")
    tep += [os.path.basename(v) for v in (ra or {}).values() if isinstance(v, str)]
    try:
        import auron_danh_gia as ag
        ag.thu_ghi(ag.tu_xrd, kq, ss)
    except Exception:  # noqa: BLE001
        pass
    return dict(tep=tep, loi=loi, thu_muc_ra=d, tom_tat=f"{len(kq)} mẫu XRD")


CHAY_RIENG = {"GCD": chay_gcd, "XPS": chay_xps, "XRD": chay_xrd}
