# -*- coding: utf-8 -*-
"""
Siêu tụ lai / Pin: xử lý số liệu GCD (nạp–xả dòng không đổi) THÔ rồi tính và vẽ
  1) đường GCD (V theo t hoặc theo dung lượng riêng),  2) điện dung riêng / dung lượng riêng theo mật độ dòng,
  3) Ragone (E theo P),  4) retention + hiệu suất Coulomb theo số chu kỳ,  5) Csp + CE theo số chu kỳ.
Lõi không dùng tkinter. Công thức (mỗi nửa chu kỳ xả):
  Q = ∫|I|dt;   C = Q/ΔV_eff (tích phân, hợp đường cong không tuyến tính)  hoặc  C = I/|dV/dt| (độ dốc, Gamry/BioLogic/Stoller & Ruoff);
  ΔV_eff = V_ext − V_cuối, V_ext = điện thế ngoại suy về lúc đảo dòng (đã bỏ IR drop);  ESR = ΔV_IR/(2I);
  Csp = 4C/m (tế bào 2 điện cực, m = tổng khối lượng, Stoller & Ruoff) hoặc C/m;  Qsp = Q/(3.6 m) (mAh/g);
  CE = Q_xả/Q_nạp·100;  E = ∫V·|I|dt (hoặc ½C(V_ext²−V_cuối²));  P = E/Δt_xả;  retention = giá trị_k/giá trị_gốc·100.
Bộ công thức mặc định khớp file Excel của người dùng (v88): C = I·Δt/(m·ΔV) với Δt = thời gian xả kể từ lúc đảo dòng, ΔV = V_đỉnh_nạp − V_cuối_xả
(GỒM cả IR drop); E = ½·C·ΔV²·1000/3600 (Wh/kg); P = E·3600/Δt (W/kg); retention = t_xả(n)/t_xả(gốc); CE = t_xả/t_nạp.
Chọn "tru_ir"/"tich_phan" để dùng cách chuẩn (loại IR drop khỏi ΔV, E = ∫V·I dt).
"""
import os
import re
import json

import numpy as np
import pandas as pd

CAU_HINH = dict(
    kieu_cell="3dc",          # 2dc: tế bào 2 điện cực đối xứng, Csp điện cực = 4C/m_tổng | 2dc_cell: C_cell/m_tổng | 3dc: C/m (một điện cực, như file Excel)
    cach_dv="gom_ir",         # gom_ir: ΔV = V đỉnh nạp − V cuối xả (gồm IR drop, như file Excel) | tru_ir: ΔV = V_ext − V cuối (bỏ IR drop, Stoller & Ruoff)
    chuan="khoi_luong",       # khoi_luong (m tính bằng mg) | dien_tich (cm²)
    cach_c="tich_phan",       # tich_phan: C = Q/ΔV | do_doc: C = I/|dV/dt|
    doc_p=0.5,                # cửa sổ độ dốc: từ V_ext xuống V_cuối + p·ΔV (0.5 = Vmax → ½Vmax khi V_cuối ≈ 0)
    cach_e="cv2_dv",          # cv2_dv: E = ½C·ΔV² (như file Excel) | cv2: E = ½C(V_ext² − V_cuối²) | tich_phan: E = ∫V·I dt
    chinh="auto",             # auto | dien_dung | dung_luong
    v_tang_nap=True,          # True: điện thế TĂNG khi nạp (tế bào/điện cực dương); False: điện thế giảm khi nạp
    chu_ky_goc=1,             # chu kỳ gốc (1 = đầu tiên của nhóm dòng dùng cho retention)
    chu_ky_ve="",             # chu kỳ vẽ GCD, vd "1,2,100" (trống = tự chọn mỗi mức dòng một chu kỳ)
    x_gcd="tg",               # tg: thời gian (s) | q: dung lượng riêng (mAh/g hoặc mAh/cm²)
    bo_chu_ky_dau=True,       # trung vị mỗi nhóm dòng: bỏ chu kỳ đầu nếu nhóm có ≥ 3 chu kỳ
    nguong_tu=0.985,          # R² tuyến tính ≥ ngưỡng → dạng tụ (tam giác)
    nguong_pin=0.93,          # R² < ngưỡng → dạng pin (có plateau); giữa hai ngưỡng = lai
    dong_hang_ma=None,        # dòng không đổi (mA) khi file không có cột dòng
    quy_rhe=False,            # True: đồ thị vẽ điện thế theo RHE = E + nernst·pH + Eref (chỉ để HIỂN THỊ; phép tính C, E dùng ΔV nên không đổi)
    ph=13.8, e_ref=0.098, nernst=0.059, ten_dien_cuc="",
)

BO_CONG_THUC = {
    "excel": dict(cach_dv="gom_ir", cach_e="cv2_dv", cach_c="tich_phan"),
    "chuan": dict(cach_dv="tru_ir", cach_e="tich_phan", cach_c="tich_phan"),
}

MAU_DS = ["#404040", "#f03c3c", "#1a5fd8", "#2aa55a", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22"]


# ====================== ĐỌC FILE ======================
def _so(x):
    try:
        return float(str(x).strip().replace(",", ".")) if str(x).strip() not in ("", "nan") else np.nan
    except ValueError:
        return None


def _doc_dong_van_ban(dong):
    """Trả (tên cột, mảng số) từ các dòng văn bản: tự dò dòng dữ liệu đầu tiên, dấu phân cách (tab ; , khoảng trắng), dấu thập phân phẩy."""
    dong = [d for d in dong if d.strip()]
    if dong and dong[0].startswith("CSStudioFile"):
        dong = dong[1:]
        mac_dinh = ["E (V)", "i (A)", "T (s)"]
    else:
        mac_dinh = None

    def tach(d):
        if "\t" in d:
            return [p.strip() for p in d.split("\t")]
        if ";" in d:
            return [p.strip() for p in d.split(";")]
        if "," in d:
            p = [x.strip() for x in d.split(",")]
            if len(p) >= 3 and all(_so(x) is not None for x in p):
                return p
            w = d.split()
            if len(w) >= 3 and all(_so(x) is not None for x in w):
                return w                              # cách nhau bằng khoảng trắng, dấu thập phân là phẩy
            if len(p) >= 3:
                return p                              # dòng tiêu đề kiểu "Time, Voltage, Current"
        return d.split()

    bat_dau = None
    for k, d in enumerate(dong):
        p = tach(d)
        v = [_so(x) for x in p]
        if len(p) >= 3 and sum(x is not None and not np.isnan(x) for x in v) >= 3 and all(x is not None for x in v):
            bat_dau = k
            break
    if bat_dau is None:
        raise ValueError("Không tìm thấy bảng số (cần ≥ 3 cột số).")
    ten = None
    if bat_dau > 0:
        ph = tach(dong[bat_dau - 1])
        if len(ph) >= 3 and any(_so(x) is None for x in ph):
            ten = ph
    hang = []
    n_cot = len(tach(dong[bat_dau]))
    for d in dong[bat_dau:]:
        p = tach(d)
        if len(p) < n_cot:
            continue
        v = [_so(x) for x in p[:n_cot]]
        if any(x is None for x in v):
            continue
        hang.append(v)
    arr = np.array(hang, dtype=float)
    if ten is None or len(ten) != n_cot:
        ten = mac_dinh if mac_dinh and len(mac_dinh) == n_cot else [f"Cột {j + 1}" for j in range(n_cot)]
    return ten, arr


def doc_bang(duong_dan):
    """Đọc file GCD thô (.txt/.csv/.dat/.mpt/.tsv/.xlsx/.xls) → (tên cột, mảng số n×k)."""
    ext = os.path.splitext(duong_dan)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        tot = None
        for ten_sheet, df in pd.read_excel(duong_dan, sheet_name=None, header=None).items():
            if df.shape[0] > 10 and df.shape[1] >= 3:
                tot = df if tot is None or df.shape[0] > tot.shape[0] else tot
        if tot is None:
            raise ValueError("Excel không có bảng ≥ 10 dòng và ≥ 3 cột.")
        so = tot.apply(pd.to_numeric, errors="coerce")
        dau = None
        for k in range(min(len(so), 60)):
            if so.iloc[k].notna().sum() >= 3 and so.iloc[k:k + 5].notna().all(axis=1).all():
                dau = k
                break
        if dau is None:
            raise ValueError("Không tìm thấy bảng số trong Excel.")
        ten = [str(x) for x in tot.iloc[dau - 1].tolist()] if dau > 0 else [f"Cột {j + 1}" for j in range(tot.shape[1])]
        ten = [t if t != "nan" else f"Cột {j + 1}" for j, t in enumerate(ten)]
        tho = tot.iloc[dau:]
        cot = []
        for j in range(tot.shape[1]):
            s = pd.to_numeric(tho.iloc[:, j], errors="coerce")
            if s.notna().mean() < 0.8:                      # có thể là giờ:phút:giây
                try:
                    s = pd.to_timedelta(tho.iloc[:, j].astype(str)).dt.total_seconds()
                except Exception:
                    pass
            cot.append(s.to_numpy(dtype=float))
        arr = np.column_stack(cot)
        giu = [j for j in range(arr.shape[1]) if np.isfinite(arr[:, j]).mean() > 0.8]
        arr = arr[:, giu]
        ten = [ten[j] for j in giu]
        arr = arr[np.isfinite(arr).all(axis=1)]
        return ten, arr
    for ma in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(duong_dan, "r", encoding=ma) as f:
                dong = f.read().splitlines()
            break
        except UnicodeDecodeError:
            continue
    return _doc_dong_van_ban(dong)


def _don_vi(ten, loai):
    g = ten.lower()
    if loai == "t":
        if re.search(r"[\(/\[]\s*(h|hr|hour)\b", g):
            return 3600.0
        if re.search(r"[\(/\[]\s*min", g):
            return 60.0
        if re.search(r"[\(/\[]\s*ms\b", g):
            return 1e-3
        return 1.0
    if loai == "v":
        return 1e-3 if re.search(r"[\(/\[]\s*mv\b", g) else 1.0
    if re.search(r"[\(/\[]\s*(µa|ua|μa)\b", g):
        return 1e-6
    if re.search(r"[\(/\[]\s*ma\b|<i>/ma|i/ma", g):
        return 1e-3
    return 1.0


def doan_cot(ten, arr):
    """Đoán cột thời gian / điện thế / dòng / chu kỳ (theo tên, rồi theo thống kê) + hệ số đổi về s, V, A. Trả dict chỉ số (None nếu không thấy)."""
    kq = {"t": None, "v": None, "i": None, "cyc": None}
    mau = {"t": r"time|thời gian|^t\b|^t\s*[\(/\[]|test_time",
           "v": r"ewe|ecell|voltage|potential|volt|điện thế|^e\b|^e\s*[\(/\[]|^v\b|^v\s*[\(/\[]",
           "i": r"<i>|current|dòng|^i\b|^i\s*[\(/\[]|i/ma|amp",
           "cyc": r"cycle|chu k"}
    for k, ten_c in enumerate(ten):
        g = ten_c.strip().lower()
        for ma, pat in mau.items():
            if kq[ma] is None and re.search(pat, g) and not re.search(r"capacity|energy|power|dq|charge/", g):
                kq[ma] = k
                break
    if kq["t"] is None or kq["v"] is None or kq["i"] is None:
        dung = {x for x in kq.values() if x is not None}
        con = [k for k in range(arr.shape[1]) if k not in dung]
        if kq["t"] is None:
            for k in con:
                if np.all(np.diff(arr[:, k]) >= 0) and np.ptp(arr[:, k]) > 0:
                    kq["t"] = k
                    con.remove(k)
                    break
        if kq["v"] is None or kq["i"] is None:
            def so_gia_tri(k):
                return len(np.unique(np.round(arr[:, k], 6)))
            con2 = [k for k in con if k != kq["cyc"]]
            if kq["i"] is None and kq["v"] is None and len(con2) >= 2:
                con2.sort(key=so_gia_tri)
                kq["i"], kq["v"] = con2[0], con2[-1]
            elif kq["i"] is None and con2:
                kq["i"] = con2[0]
            elif kq["v"] is None and con2:
                kq["v"] = con2[0]
    return kq


def chuan_hoa_thoi_gian(t):
    """Thời gian đơn điệu tăng: nếu có đoạn reset (thời gian từng bước) thì cộng dồn."""
    t = np.asarray(t, float)
    if len(t) < 2:
        return t
    dt = np.diff(t)
    duong = dt[dt > 0]
    buoc = float(np.median(duong)) if len(duong) else 1.0
    bu = np.zeros(len(t))
    off = 0.0
    for k in range(1, len(t)):
        if dt[k - 1] < 0:
            off += t[k - 1] - t[k] + buoc
        bu[k] = off
    return t + bu


def khoi_luong_tu_ten(*ten):
    """Đoán khối lượng (mg) từ tên file/mẫu, ví dụ 'NiCr2O4_GCD_23.2mA_0-0.55V_2.32mg' → 2.32; 'x 0.5 g' không đoán (chỉ nhận đơn vị mg).
    Chỉ là gợi ý tự điền; người dùng vẫn kiểm tra. Không thấy → None."""
    for t in ten:
        m = re.findall(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*mg(?![A-Za-z])", os.path.basename(str(t or "")), flags=re.I)
        if m:
            try:
                v = float(m[-1].replace(",", "."))
                if v > 0:
                    return v
            except ValueError:
                pass
    return None


def doc_thong_so_cs(duong_dan):
    """File CS Studio (CorrTest): dòng đầu 'CSStudioFile,<loại>,<base64 gzip>' chứa thông số thí nghiệm. Trả dict (rỗng nếu không có):
    dong_mA, khoi_luong_mg, e_cao, e_thap (V), ngay. Dùng để tự điền khối lượng/dòng; chỉ là gợi ý, người dùng vẫn kiểm tra."""
    import base64
    import gzip
    try:
        with open(duong_dan, "r", encoding="utf-8", errors="replace") as f:
            dau = f.readline().strip()
        p = dau.split(",")
        if len(p) < 3 or p[0] != "CSStudioFile":
            return {}
        b = p[2] + "=" * (-len(p[2]) % 4)
        txt = gzip.decompress(base64.b64decode(b)).decode("utf-8", errors="replace")
    except Exception:
        return {}
    kq = {}
    m = re.search(r"ExpParmas:([^\r\n]*)", txt)
    if m:
        tham = dict(x.split("=", 1) for x in m.group(1).split("&-&") if "=" in x)

        def so(k):
            try:
                return float(tham[k])
            except (KeyError, ValueError):
                return None
        dv = so("CurUnit")
        dong = so("ChargeCur")
        if dong is not None:
            # CurUnit: 0 = A, 1 = mA, 2 = µA (CorrTest); file mẫu: ChargeCur=23.2, CurUnit=1 ↔ 23.2 mA
            kq["dong_mA"] = dong * {0: 1000.0, 1: 1.0, 2: 1e-3}.get(int(dv) if dv is not None else 1, 1.0)
        if so("Mass") is not None:
            kq["khoi_luong_mg"] = so("Mass")
        if so("HighE") is not None:
            kq["e_cao"] = so("HighE")
        if so("LowE") is not None:
            kq["e_thap"] = so("LowE")
    m = re.search(r"Data:(\S+)\s+Time:(\S+)", txt)
    if m:
        kq["ngay"] = m.group(1) + " " + m.group(2)
    return kq


def nap_mau(duong_dan, cot=None, dong_hang_ma=None, ghi_de_dong=False):
    """Đọc 1 file → dict t(s), v(V), i(A, có dấu hoặc None), cyc, ten_cot, cot (chỉ số), canh_bao."""
    ten, arr = doc_bang(duong_dan)
    ds = doan_cot(ten, arr)
    if cot:
        ds.update({k: v for k, v in cot.items() if k in ds})       # None = người dùng chọn "(không có)"
    cb = []
    if ds["t"] is None or ds["v"] is None:
        raise ValueError("Không xác định được cột thời gian và điện thế. Hãy chọn cột trong bảng ánh xạ.")
    t = arr[:, ds["t"]] * _don_vi(ten[ds["t"]], "t")
    v = arr[:, ds["v"]] * _don_vi(ten[ds["v"]], "v")
    if ghi_de_dong and dong_hang_ma:
        i = None                                                      # người dùng tự nhập I cho mẫu này: dùng I đó, không đọc cột dòng
        cb.append(f"Dùng dòng I = {dong_hang_ma:g} mA do bạn nhập (không đọc cột dòng của file).")
    elif ds["i"] is not None:
        i = arr[:, ds["i"]] * _don_vi(ten[ds["i"]], "i")
    elif dong_hang_ma:
        i = None
        cb.append(f"File không có cột dòng: dùng dòng không đổi {dong_hang_ma:g} mA.")
    else:
        raise ValueError("File không có cột dòng: hãy nhập dòng không đổi (mA).")
    t = chuan_hoa_thoi_gian(t)
    return {"t": t, "v": v, "i": i, "i_const": (dong_hang_ma * 1e-3 if dong_hang_ma else None),
            "ten_cot": ten, "cot": ds, "canh_bao": cb}


# ====================== TÁCH NỬA CHU KỲ ======================
def _chay_cung_dau(s):
    """Các đoạn liên tiếp cùng giá trị khác 0: [(a, b, dấu)] (b gồm)."""
    kq, a = [], None
    for k in range(len(s)):
        if s[k] != 0 and (a is None or s[k] != s[a]):
            if a is not None:
                kq.append((a, k - 1, int(s[a])))
            a = k
        elif s[k] == 0 and a is not None:
            kq.append((a, k - 1, int(s[a])))
            a = None
    if a is not None:
        kq.append((a, len(s) - 1, int(s[a])))
    return kq


def _chay_theo_dien_the(v, hoat, nguong):
    """Khi dòng không có dấu: tách theo điểm quay đầu của điện thế (có trễ `nguong`)."""
    n = len(v)
    kq = []
    k = 0
    while k < n:
        if not hoat[k]:
            k += 1
            continue
        a = k
        while k < n and hoat[k]:
            k += 1
        b = k - 1
        # tách trong [a, b] theo chiều biến thiên
        huong, cuc, dau = 0, v[a], a
        for j in range(a, b + 1):
            if huong == 0:
                if abs(v[j] - cuc) > nguong:
                    huong = 1 if v[j] > cuc else -1
                    cuc = v[j]
            elif huong == 1:
                if v[j] > cuc:
                    cuc = v[j]
                elif cuc - v[j] > nguong:
                    kq.append((dau, j - 1, 1))
                    dau, huong, cuc = j - 1, -1, v[j]
            else:
                if v[j] < cuc:
                    cuc = v[j]
                elif v[j] - cuc > nguong:
                    kq.append((dau, j - 1, -1))
                    dau, huong, cuc = j - 1, 1, v[j]
        kq.append((dau, b, huong if huong else 1))
    return kq


def tach_nua(t, v, i, cau_hinh, i_const=None):
    """→ danh sách nửa chu kỳ [{'a','b','loai':'nap'|'xa','I':dòng_TB(A)}], theo thứ tự thời gian."""
    n = len(t)
    if i is None:
        ai = np.full(n, float(i_const))
        hoat = np.ones(n, bool)
    else:
        ai = np.abs(i)
        thr = 1e-3 * np.percentile(ai, 99)
        hoat = ai > max(thr, 1e-12)
    v_tp = float(np.ptp(v)) or 1.0
    co_dau = False
    if i is not None:
        dg, am = np.sum((i > 0) & hoat), np.sum((i < 0) & hoat)
        co_dau = min(dg, am) / max(dg + am, 1) > 0.02
    if co_dau:
        s = np.where(hoat, np.sign(i), 0).astype(int)
        chay = _chay_cung_dau(s)
    else:
        chay = _chay_theo_dien_the(v, hoat, 0.01 * v_tp)
    nua = []
    for a, b, _ in chay:
        if b - a + 1 < 5:
            continue
        dv = v[b] - v[a]
        if abs(dv) < 0.01 * v_tp:
            continue
        nap = (dv > 0) == bool(cau_hinh["v_tang_nap"])
        Itb = float(np.median(ai[a:b + 1][hoat[a:b + 1]])) if hoat[a:b + 1].any() else float(np.median(ai[a:b + 1]))
        nua.append({"a": a, "b": b, "loai": "nap" if nap else "xa", "I": Itb})
    return nua


# ====================== TÍNH TỪNG CHU KỲ ======================
def _tich_phan(y, t):
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t))) if len(t) > 1 else 0.0


def _r2(x, y):
    if len(x) < 3:
        return float("nan")
    p = np.polyfit(x, y, 1)
    ss_res = np.sum((y - np.polyval(p, x)) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def don_vi_nhan(cau_hinh):
    if cau_hinh["chuan"] == "dien_tich":
        return {"C": "F cm⁻²", "Q": "mAh cm⁻²", "j": "mA cm⁻²", "E": "mWh cm⁻²", "P": "mW cm⁻²", "ch": "cm²"}
    return {"C": "F g⁻¹", "Q": "mAh g⁻¹", "j": "A g⁻¹", "E": "Wh kg⁻¹", "P": "W kg⁻¹", "ch": "g"}


def _quy_chuan(cau_hinh, gia_tri, I_a, C, Q_c, E_wh, P_w):
    """Quy về đơn vị riêng. gia_tri: mg (khối lượng) hoặc cm² (diện tích)."""
    he = 4.0 if cau_hinh["kieu_cell"] == "2dc" else 1.0
    if cau_hinh["chuan"] == "dien_tich":
        A = gia_tri
        return dict(Csp=he * C / A, Qsp=Q_c / 3.6 / A, j=I_a * 1000.0 / A, Esp=E_wh * 1000.0 / A, Psp=P_w * 1000.0 / A)
    g = gia_tri / 1000.0
    return dict(Csp=he * C / g, Qsp=Q_c / 3.6 / g, j=I_a / g, Esp=E_wh / (g / 1000.0), Psp=P_w / (g / 1000.0))


def tinh_xa(t, v, i, nap, xa, cau_hinh, gia_tri, i_const=None):
    """Chỉ số của một nửa chu kỳ xả (và nửa nạp liền trước nếu có)."""
    a, b = xa["a"], xa["b"]
    sg = 1.0 if cau_hinh["v_tang_nap"] else -1.0          # chiều nạp ngược (điện thế giảm khi nạp): đổi dấu để xả luôn đi xuống
    td, vd = t[a:b + 1], sg * v[a:b + 1]
    if i is None:
        idat = np.full(len(td), float(i_const))
    else:
        idat = np.abs(i[a:b + 1])
    I = xa["I"]
    dt_xa = float(td[-1] - td[0])
    Q_d = _tich_phan(idat, td)
    cb = []
    if len(td) < 10:
        cb.append("Nửa xả chỉ có < 10 điểm: kết quả kém tin cậy.")
    if np.std(idat) / (np.mean(idat) or 1) > 0.05 and i is not None:
        cb.append("Dòng trong nửa xả không đổi (> 5% dao động).")
    # IR drop: ngoại suy tuyến tính phần đầu nửa xả về lúc đảo dòng
    V_nap_cuoi = t_sw = None
    if nap is not None and nap["b"] < a + 1 and a - nap["b"] <= 3:
        V_nap_cuoi, t_sw = float(sg * v[nap["b"]]), float(t[nap["b"]])
    n_td = len(td)
    k1, k2 = max(1, int(0.05 * n_td)), max(4, int(0.25 * n_td))
    k2 = min(k2, n_td)
    if k2 - k1 >= 2:
        pf = np.polyfit(td[k1:k2], vd[k1:k2], 1)
    else:
        pf = np.polyfit(td[:min(5, n_td)], vd[:min(5, n_td)], 1)
    if V_nap_cuoi is not None:
        V_ext_ir = float(np.polyval(pf, t_sw))
        dv_ir = max(0.0, V_nap_cuoi - V_ext_ir)
        if V_ext_ir > V_nap_cuoi:
            V_ext_ir = V_nap_cuoi
    else:
        V_ext_ir, dv_ir = float(vd[0]), float("nan")
        cb.append("Không có nửa nạp liền trước: không tính IR drop và CE của chu kỳ này.")
    V_cuoi = float(vd[-1])
    gom = cau_hinh.get("cach_dv", "tru_ir") == "gom_ir"
    if gom and V_nap_cuoi is not None:
        # kiểu file Excel: ΔV = V đỉnh nạp − V cuối xả (GỒM IR drop), Δt = từ lúc đảo dòng đến hết xả
        V_ext = V_nap_cuoi
        khoang_dao = max(0.0, float(td[0]) - t_sw)
        i_dau = float(i_const) if i is None else float(abs(i[nap["b"]]))
        Q_d = Q_d + 0.5 * (i_dau + float(idat[0])) * khoang_dao
        dt_xa = float(td[-1]) - t_sw
    else:
        V_ext = V_ext_ir
        if gom:
            cb.append("Chọn 'gồm IR drop' nhưng không có nửa nạp liền trước: chu kỳ này dùng V đầu xả.")
    dv = V_ext - V_cuoi
    dv_sl = V_ext_ir - V_cuoi                                   # đoạn độ dốc luôn tính sau IR drop
    ESR = dv_ir / (2 * I) if I > 0 and np.isfinite(dv_ir) else float("nan")
    if dv <= 0 or dv_sl <= 0:
        return None
    # điện dung
    C_tp = Q_d / dv
    lo = V_cuoi + float(cau_hinh["doc_p"]) * dv_sl
    sel = (vd <= V_ext_ir) & (vd >= lo)
    if sel.sum() >= 3:
        slope = np.polyfit(td[sel], vd[sel], 1)[0]
        C_dd = I / abs(slope) if slope != 0 else float("nan")
    else:
        C_dd = float("nan")
        cb.append("Cửa sổ độ dốc có < 3 điểm: dùng tích phân.")
    C = C_dd if (cau_hinh["cach_c"] == "do_doc" and np.isfinite(C_dd)) else C_tp
    # năng lượng, công suất
    E_tp = _tich_phan(np.abs(vd) * idat, td) / 3600.0
    if cau_hinh.get("cach_e") == "cv2_dv":
        E_cv2 = 0.5 * C * dv ** 2 / 3600.0                       # kiểu file Excel: ½·C·ΔV²
    else:
        E_cv2 = 0.5 * C * (V_ext ** 2 - V_cuoi ** 2) / 3600.0
    E_wh = E_cv2 if cau_hinh.get("cach_e") in ("cv2", "cv2_dv") else E_tp
    P_w = E_wh * 3600.0 / dt_xa if dt_xa > 0 else float("nan")
    r2 = _r2(td[vd <= V_ext_ir], vd[vd <= V_ext_ir])
    if not np.isfinite(r2):
        dang = "?"
    elif r2 >= cau_hinh["nguong_tu"]:
        dang = "tụ"
    elif r2 >= cau_hinh["nguong_pin"]:
        dang = "lai"
    else:
        dang = "pin"
    t_nap = float(t[nap["b"]] - t[nap["a"]]) if nap is not None else float("nan")
    kq = dict(I_A=I, dt_xa=dt_xa, Q_xa_C=Q_d, V_ext=V_ext, V_cuoi=V_cuoi, dV_IR=dv_ir, dV=dv, ESR=ESR, C_F=C,
              C_tp=C_tp, C_dd=C_dd, E_wh=E_wh, E_tp_wh=E_tp, E_cv2_wh=E_cv2, P_w=P_w, R2=r2, dang=dang,
              t_nap=t_nap, T_ck=(t_nap + dt_xa) if np.isfinite(t_nap) else float("nan"),
              t0=float(t[nap["a"]] if nap is not None else td[0]), t1=float(td[-1]))
    kq.update(_quy_chuan(cau_hinh, gia_tri, I, C, Q_d, E_wh, P_w))
    nt = _quy_chuan(cau_hinh, gia_tri, I, C, Q_d, E_tp, E_tp * 3600.0 / dt_xa if dt_xa > 0 else float("nan"))
    nc = _quy_chuan(cau_hinh, gia_tri, I, C, Q_d, E_cv2, E_cv2 * 3600.0 / dt_xa if dt_xa > 0 else float("nan"))
    kq.update(Esp_tp=nt["Esp"], Psp_tp=nt["Psp"], Esp_cv2=nc["Esp"], Psp_cv2=nc["Psp"])
    # nạp, CE
    if nap is not None:
        ac, tc = nap["a"], nap["b"]
        idc = np.full(tc - ac + 1, float(i_const)) if i is None else np.abs(i[ac:tc + 1])
        Q_c = _tich_phan(idc, t[ac:tc + 1])
        E_c = _tich_phan(np.abs(sg * v[ac:tc + 1]) * idc, t[ac:tc + 1]) / 3600.0
        kq["Q_nap_C"] = Q_c
        kq["CE"] = Q_d / Q_c * 100.0 if Q_c > 0 else float("nan")
        kq["EE"] = E_tp / E_c * 100.0 if E_c > 0 else float("nan")
        if np.isfinite(kq["CE"]) and kq["CE"] > 100.5:
            cb.append(f"CE = {kq['CE']:.1f}% > 100%: kiểm tra việc tách nạp/xả, số điểm đầu/cuối, hoặc phản ứng phụ.")
    else:
        kq["Q_nap_C"] = kq["CE"] = kq["EE"] = float("nan")
    kq["canh_bao"] = cb
    return kq


def _nhom_dong(I):
    return float(f"{I:.3g}")


def phan_tich_mau(tt, cau_hinh):
    """tt: {'ten','path','gia_tri'(mg hoặc cm²),'mau', ...} → kết quả đầy đủ cho mẫu (chu kỳ, nhóm dòng)."""
    try:
        dong_mau = float(tt.get("dong_ma") or 0)
    except (TypeError, ValueError):
        dong_mau = 0.0
    if dong_mau > 0:
        d = nap_mau(tt["path"], tt.get("cot"), dong_mau, ghi_de_dong=True)
    else:
        d = nap_mau(tt["path"], tt.get("cot"), cau_hinh.get("dong_hang_ma"))
    t, v, i = d["t"], d["v"], d["i"]
    nua = tach_nua(t, v, i, cau_hinh, d["i_const"])
    chu_ky, nap_truoc, k = [], None, 0
    for j, h in enumerate(nua):
        if h["loai"] == "nap":
            nap_truoc = h
            continue
        truoc = nua[j - 1] if j > 0 and nua[j - 1]["loai"] == "nap" else None
        r = tinh_xa(t, v, i, truoc, h, cau_hinh, float(tt["gia_tri"]), d["i_const"])
        if r is None:
            continue
        k += 1
        r.update(chu_ky=k, nhom=_nhom_dong(r["I_A"]), a_xa=h["a"], b_xa=h["b"],
                 a_nap=truoc["a"] if truoc else None, b_nap=truoc["b"] if truoc else None)
        chu_ky.append(r)
    cb = list(d["canh_bao"])
    if not chu_ky:
        cb.append("Không tách được chu kỳ xả nào: kiểm tra cột dòng/điện thế, chiều nạp (V tăng/giảm) và dấu dòng.")
    if tt["gia_tri"] is None or float(tt["gia_tri"]) <= 0:
        cb.append("Chưa nhập khối lượng/diện tích hợp lệ.")
    elif cau_hinh["chuan"] == "khoi_luong" and float(tt["gia_tri"]) < 1.0:
        cb.append("Khối lượng < 1 mg: khối lượng rất nhỏ làm sai số lớn khi quy ra F/g, mAh/g.")
    if any(r["dang"] == "pin" for r in chu_ky):
        cb.append("Đường xả có plateau (dạng pin, R² thấp): điện dung F/g không phản ánh đúng cơ chế, nên báo dung lượng mAh/g (hoặc C/g).")
    nhom = {}
    for r in chu_ky:
        nhom.setdefault(r["nhom"], []).append(r)
    tom = []
    for dong, ds in sorted(nhom.items()):
        dung = ds[1:] if (cau_hinh["bo_chu_ky_dau"] and len(ds) >= 3) else ds

        def tv(key, dung=dung):
            x = [r[key] for r in dung if np.isfinite(r[key])]
            return float(np.median(x)) if x else float("nan")
        dangs = [r["dang"] for r in dung]
        tom.append(dict(I_A=ds[0]["I_A"], nhom=dong, so_chu_ky=len(ds), chu_ky_dau=ds[0]["chu_ky"], chu_ky_cuoi=ds[-1]["chu_ky"],
                        j=tv("j"), Csp=tv("Csp"), Qsp=tv("Qsp"), Esp=tv("Esp"), Psp=tv("Psp"), Esp_tp=tv("Esp_tp"), Psp_tp=tv("Psp_tp"),
                        Esp_cv2=tv("Esp_cv2"), Psp_cv2=tv("Psp_cv2"), CE=tv("CE"), EE=tv("EE"),
                        t_nap=tv("t_nap"), t_xa=tv("dt_xa"), T_ck=tv("T_ck"),
                        ESR=tv("ESR"), dV_IR=tv("dV_IR"), R2=tv("R2"), dang=max(set(dangs), key=dangs.count)))
    lech = (float(cau_hinh.get("nernst", 0.059)) * float(cau_hinh.get("ph", 0)) + float(cau_hinh.get("e_ref", 0))) if cau_hinh.get("quy_rhe") else 0.0
    return dict(ten=tt["ten"], path=tt["path"], mau=tt.get("mau") or MAU_DS[0], gia_tri=float(tt["gia_tri"] or 0),
                chu_ky=chu_ky, nhom=tom, canh_bao=cb + [c for r in chu_ky[:3] for c in r["canh_bao"]][:3],
                t_tong=float(t[-1] - t[0]) if len(t) > 1 else 0.0, lech_v=lech,
                _raw=dict(t=t, v=v, v_hien=v + lech, i=i, i_const=d["i_const"]), cot=d["cot"], ten_cot=d["ten_cot"])


def quyet_dinh_chinh(ds_mau, cau_hinh):
    """'dien_dung' hay 'dung_luong': người dùng chọn, hoặc tự đoán (có mẫu dạng pin → dung lượng)."""
    if cau_hinh["chinh"] in ("dien_dung", "dung_luong"):
        return cau_hinh["chinh"], "theo lựa chọn của bạn"
    dang = [g["dang"] for m in ds_mau for g in m["nhom"]]
    if not dang:
        return "dien_dung", "mặc định"
    pin = sum(x == "pin" for x in dang)
    lai = sum(x == "lai" for x in dang)
    if pin:
        return "dung_luong", f"{pin}/{len(dang)} mức dòng có đường xả dạng pin (plateau, R² thấp) → báo dung lượng mAh/g"
    if lai >= len(dang) / 2:
        return "dung_luong", f"{lai}/{len(dang)} mức dòng dạng lai (không tuyến tính) → báo dung lượng mAh/g"
    return "dien_dung", "đường xả gần tam giác (tuyến tính) → báo điện dung F/g"


def chay(ds_tt, cau_hinh):
    cfg = dict(CAU_HINH, **(cau_hinh or {}))
    mau = []
    loi = []
    for k, tt in enumerate(ds_tt):
        tt = dict(tt)
        tt.setdefault("mau", MAU_DS[k % len(MAU_DS)])
        try:
            mau.append(phan_tich_mau(tt, cfg))
        except Exception as e:  # noqa: BLE001
            loi.append((tt.get("ten", tt.get("path")), str(e)))
    chinh, ly_do = quyet_dinh_chinh(mau, cfg)
    return dict(mau=mau, cfg=cfg, chinh=chinh, ly_do=ly_do, loi=loi, don_vi=don_vi_nhan(cfg))


# ====================== CÀI ĐẶT RIÊNG TỪNG ĐỒ THỊ ======================
TEN_DO_THI = {"gcd": "Đường GCD", "gcd_nhieu": "GCD nhiều chu kỳ", "csp_dong": "Csp / Q theo mật độ dòng", "ragone": "Ragone (E–P)",
              "retention": "Retention + CE theo chu kỳ", "csp_chu_ky": "Csp / Q + CE theo chu kỳ"}

# Phần hiển thị: None / "" = tự động. Mọi đồ thị dùng chung các khóa này, mỗi đồ thị giữ một bản riêng.
KIEU_MAC_DINH = dict(tieu_de_x="", tieu_de_y="", tieu_de_y2="", x_min=None, x_max=None, y_min=None, y_max=None, y2_min=None, y2_max=None,
                     log_x=None, log_y=None, co_nhan=None, co_tick=None, co_ct=None, lw=None, co_diem=None,
                     chu_thich=True, vi_tri="best", luoi=False, tap_chi="", cot=1, dpi=None)
KHOA_KIEU = tuple(KIEU_MAC_DINH)
# Phần dữ liệu riêng của từng đồ thị (None = lấy theo thiết lập chung)
DU_LIEU_MAC_DINH = {
    "gcd": dict(x=None, chu_ky_ve=None),
    "gcd_nhieu": dict(mau_ten="", nhom_j="", so_dau=3, so_cuoi=3, phong_dai=True, nhan_dau="Initial cycles", nhan_cuoi="Final cycles",
                      nhan_tren="", nhan_ct=""),
    "csp_dong": dict(dai_luong="dien_dung", kieu_ve="cot"),
    "ragone": dict(cach_e=None),
    "retention": dict(dai_luong="theo_chung", chu_ky_goc=None, nhom_j="", hien_ce=True),
    "csp_chu_ky": dict(dai_luong="theo_chung", nhom_j="", hien_ce=True),
}
HAI_TRUC = ("retention", "csp_chu_ky")


def cai_dat_do_thi(ma, cau_hinh_dt=None):
    """Thiết lập đầy đủ của một đồ thị = mặc định + phần người dùng chỉnh (cau_hinh_dt[ma])."""
    s = dict(KIEU_MAC_DINH, **DU_LIEU_MAC_DINH[ma])
    if ma == "ragone":
        s["log_x"] = s["log_y"] = True
    s.update({k: v for k, v in ((cau_hinh_dt or {}).get(ma) or {}).items() if k in s})
    return s


def _nhan_cong_thuc(ten):
    """Tên mẫu dạng công thức hóa học (không có khoảng trắng): số sau chữ → chỉ số dưới (NiCr2O4 → NiCr₂O₄ bằng mathtext). Tên khác giữ nguyên."""
    if re.fullmatch(r"[A-Za-z0-9()\-]+", ten or "") and re.search(r"[A-Za-z)]\d", ten):
        return re.sub(r"(?<=[A-Za-z)])(\d+)", r"$_{\1}$", ten)
    return ten


def _dai_luong(kq, chon):
    """('Csp'|'Qsp', nhãn) theo lựa chọn của đồ thị ('theo_chung' = theo đại lượng chính toàn bộ)."""
    c = kq["chinh"] if chon in (None, "", "theo_chung") else chon
    u = kq["don_vi"]
    if c == "thoi_gian_xa":
        return "dt_xa", "Discharge time (s)", "Discharge time"
    if c == "dien_dung":
        return "Csp", "Specific capacitance (" + u["C"] + ")", "Capacitance"
    return "Qsp", "Specific capacity (" + u["Q"] + ")", "Capacity"


# ====================== RETENTION ======================
def chon_nhom(m, nhom_j=None):
    """Nhóm dòng dùng cho chuỗi theo chu kỳ: nhóm có j gần `nhom_j` nhất; trống = nhóm có nhiều chu kỳ nhất."""
    if not m["nhom"]:
        return None
    if nhom_j not in (None, ""):
        try:
            x = float(str(nhom_j).replace(",", "."))
            return min(m["nhom"], key=lambda g: abs(g["j"] - x))
        except ValueError:
            pass
    return max(m["nhom"], key=lambda g: g["so_chu_ky"])


def chuoi_retention(m, cfg, chinh, nhom_j=None, chu_ky_goc=None):
    """Chuỗi theo chu kỳ của một nhóm dòng: (nhóm, [{k, gia_tri, CE, retention%}]). None nếu nhóm < 3 chu kỳ."""
    nh = chon_nhom(m, nhom_j)
    if nh is None or nh["so_chu_ky"] < 3:
        return None
    key = {"dien_dung": "Csp", "thoi_gian_xa": "dt_xa"}.get(chinh, "Qsp")
    ds = [r for r in m["chu_ky"] if r["nhom"] == nh["nhom"]]
    goc = cfg["chu_ky_goc"] if chu_ky_goc in (None, "") else chu_ky_goc
    g = min(max(int(goc), 1), len(ds)) - 1
    ref = ds[g][key]
    return nh, [dict(k=r["chu_ky"], gia_tri=r[key], CE=r["CE"], retention=(r[key] / ref * 100.0 if ref else float("nan"))) for r in ds]


# ====================== DỮ LIỆU CHO TỪNG ĐỒ THỊ ======================
def _chu_ky_can_ve(m, cfg, chuoi=None):
    ds = m["chu_ky"]
    if not ds:
        return []
    chuoi = str(cfg.get("chu_ky_ve") or "").strip() if chuoi is None else str(chuoi).strip()
    if chuoi:
        ks = {int(x) for x in re.findall(r"\d+", chuoi)}
        return [r for r in ds if r["chu_ky"] in ks]
    kq = []
    nhom = {}
    for r in ds:
        nhom.setdefault(r["nhom"], []).append(r)
    for dong, ls in sorted(nhom.items()):
        kq.append(ls[min(1, len(ls) - 1)])
    return kq


def _hien_thi(s):
    return {k: s[k] for k in KHOA_KIEU}


def _giam_mau(x, y, n_max=40000):
    """Giảm số điểm vẽ nhưng giữ đỉnh/đáy từng khối (min–max) để hình nhiều chu kỳ không mất biên."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) <= n_max:
        return x, y
    khoi = int(np.ceil(len(x) / (n_max / 2)))
    idx = []
    for a in range(0, len(x), khoi):
        b = min(a + khoi, len(x))
        seg = y[a:b]
        k1, k2 = a + int(np.argmin(seg)), a + int(np.argmax(seg))
        idx += sorted({k1, k2})
    idx = np.array(sorted(set(idx)))
    return x[idx], y[idx]


def _gcd_nhieu(kq, s, nhan_v):
    """Đồ thị GCD nhiều chu kỳ: toàn bộ đường V–t (hoặc của một nhóm dòng) + hai ô phóng đại (N chu kỳ đầu, N chu kỳ cuối)."""
    cfg, u = kq["cfg"], kq["don_vi"]
    ser, ins_d, ins_c = [], [], []
    ghi = []
    muc = str(s.get("mau_ten") or "").strip().lower()
    for m in kq["mau"]:
        if muc and muc not in m["ten"].lower():
            continue
        raw = m["_raw"]
        t, v = raw["t"], raw["v_hien"]
        cks = m["chu_ky"]
        nh = chon_nhom(m, s.get("nhom_j")) if s.get("nhom_j") not in (None, "") else None
        if nh is not None:
            cks = [r for r in cks if r["nhom"] == nh["nhom"]]
        if cks:
            a0 = min((r["a_nap"] if r["a_nap"] is not None else r["a_xa"]) for r in cks)
            b0 = max(r["b_xa"] for r in cks)
        else:
            a0, b0 = 0, len(t) - 1
        if nh is None and cks:
            a0, b0 = 0, len(t) - 1
        t0 = float(t[a0])
        x, y = _giam_mau(t[a0:b0 + 1] - t0, v[a0:b0 + 1])
        n_ck = len(cks)
        j_txt = f"{cks[0]['j']:.3g} {u['j']}" if cks else ""
        ten = m["ten"] if len(kq["mau"]) > 1 else (s.get("nhan_ct") or f"{j_txt} {n_ck} cycles".strip())
        ser.append(dict(ten=ten, mau=m["mau"], x=list(map(float, x)), y=list(map(float, y)), truc="y", kieu="line", goc=m["ten"]))
        ghi.append(f"{m['ten']}: {n_ck} chu kỳ, {t[b0] - t[a0]:.6g} s" + (f", j = {j_txt}" if j_txt else ""))
        if s.get("phong_dai") and n_ck >= 2:
            nd = max(1, min(int(s.get("so_dau") or 3), n_ck))
            nc = max(1, min(int(s.get("so_cuoi") or 3), n_ck))
            for lst, ds, dau in ((ins_d, cks[:nd], True), (ins_c, cks[-nc:], False)):
                a = ds[0]["a_nap"] if ds[0]["a_nap"] is not None else ds[0]["a_xa"]
                b = ds[-1]["b_xa"]
                lst.append(dict(ten=m["ten"], mau=m["mau"], x=list(map(float, t[a:b + 1] - t0)), y=list(map(float, v[a:b + 1])), truc="y", kieu="line"))
    d = dict(tieu_de="GCD cycling", x_nhan="Time (s)", y_nhan=nhan_v, log_x=False, log_y=False, series=ser, ghi_chu=ghi)
    ins = []
    if ins_d:
        ins.append(dict(nhan=s.get("nhan_dau") or "Initial cycles", pos=[0.07, 0.53, 0.40, 0.34], series=ins_d))
    if ins_c:
        ins.append(dict(nhan=s.get("nhan_cuoi") or "Final cycles", pos=[0.57, 0.53, 0.40, 0.34], series=ins_c))
    d["insets"] = ins
    d["nhan_tren"] = s.get("nhan_tren") or ""
    return d


def du_lieu_do_thi(kq, cau_hinh_dt=None):
    """→ dict id → {tieu_de, x_nhan, y_nhan, y2_nhan, log_x, log_y, series:[{ten, mau, x, y, truc, kieu}], hien_thi, ghi_chu}.
    cau_hinh_dt[id] = thiết lập riêng của đồ thị đó (xem KIEU_MAC_DINH và DU_LIEU_MAC_DINH)."""
    cfg, u = kq["cfg"], kq["don_vi"]
    dt = cfg["chuan"] == "dien_tich"
    ra = {}

    def hoan_thien(ma, d, s):
        if s["tieu_de_x"]:
            d["x_nhan"] = s["tieu_de_x"]
        if s["tieu_de_y"]:
            d["y_nhan"] = s["tieu_de_y"]
        if s["tieu_de_y2"]:
            d["y2_nhan"] = s["tieu_de_y2"]
        d["log_x"] = bool(d["log_x"] if s["log_x"] is None else s["log_x"])
        d["log_y"] = bool(d["log_y"] if s["log_y"] is None else s["log_y"])
        d["hien_thi"] = _hien_thi(s)
        d["hai_truc"] = ma in HAI_TRUC and any(x["truc"] == "y2" for x in d["series"])
        ra[ma] = d

    # 1) GCD
    s = cai_dat_do_thi("gcd", cau_hinh_dt)
    x_gcd = s["x"] or cfg["x_gcd"]
    chu_ky_ve = cfg.get("chu_ky_ve") if s["chu_ky_ve"] is None else s["chu_ky_ve"]
    ser = []
    for m in kq["mau"]:
        raw = m["_raw"]
        ch = _chu_ky_can_ve(m, cfg, chu_ky_ve)
        for r in ch:
            a0 = r["a_nap"] if r["a_nap"] is not None else r["a_xa"]
            sl = slice(a0, r["b_xa"] + 1)
            t, v = raw["t"][sl], raw["v_hien"][sl]
            i = np.abs(raw["i"][sl]) if raw["i"] is not None else np.full(len(t), raw["i_const"])
            if x_gcd == "q":
                q = np.concatenate([[0.0], np.cumsum(0.5 * (i[1:] + i[:-1]) * np.diff(t))]) / 3.6
                q = q / (m["gia_tri"] if dt else m["gia_tri"] / 1000.0)
                if r["a_nap"] is not None:
                    n_nap = r["b_nap"] - r["a_nap"] + 1
                    q_nap_cuoi = q[n_nap - 1]
                    x = np.concatenate([q[:n_nap], q_nap_cuoi - (q[n_nap:] - q_nap_cuoi)])
                else:
                    x = q
            else:
                x = t - t[0]
            ten = f"{m['ten']} · {r['j']:.3g} {u['j']}" if len(kq["mau"]) > 1 or len(ch) > 1 else m["ten"]
            ser.append(dict(ten=ten, mau=m["mau"], x=list(map(float, x)), y=list(map(float, v)), truc="y", kieu="line", chu_ky=r["chu_ky"], j=r["j"], goc=m["ten"]))
    xl = "Time (s)" if x_gcd == "tg" else ("Specific capacity (" + u["Q"] + ")")
    nhan_v = "Potential (V vs RHE)" if cfg.get("quy_rhe") else ("Potential (V vs " + cfg["ten_dien_cuc"] + ")" if cfg.get("ten_dien_cuc") else "Potential (V)")
    hoan_thien("gcd", dict(tieu_de="GCD", x_nhan=xl, y_nhan=nhan_v, log_x=False, log_y=False, series=ser), s)
    # 1b) GCD nhiều chu kỳ (cả dải thời gian + ô phóng đại các chu kỳ đầu/cuối)
    s = cai_dat_do_thi("gcd_nhieu", cau_hinh_dt)
    hoan_thien("gcd_nhieu", _gcd_nhieu(kq, s, nhan_v), s)
    # 2) Csp / Qsp theo mật độ dòng
    s = cai_dat_do_thi("csp_dong", cau_hinh_dt)
    key, nhan_c, _ = _dai_luong(kq, s["dai_luong"])
    cot = s.get("kieu_ve", "cot") != "duong"
    mau_cot = "#262626" if len([m for m in kq["mau"] if m["nhom"]]) == 1 else None          # một mẫu: cột đen như hình mẫu; nhiều mẫu: màu từng mẫu
    ser = [dict(ten=m["ten"], mau=(mau_cot or m["mau"]) if cot else m["mau"], x=[g["j"] for g in m["nhom"]], y=[g[key] for g in m["nhom"]], truc="y",
                kieu="bar" if cot else "ls") for m in kq["mau"] if m["nhom"]]
    d_csp = dict(tieu_de="Rate", x_nhan=f"Current density ({u['j']})", y_nhan=nhan_c, log_x=False, log_y=False, series=ser)
    if cot and len(ser) == 1:
        d_csp["nhan_phai"] = _nhan_cong_thuc(ser[0]["ten"])
    hoan_thien("csp_dong", d_csp, s)
    # 3) Ragone
    s = cai_dat_do_thi("ragone", cau_hinh_dt)
    cach_e = s["cach_e"] or cfg["cach_e"]
    ke, kp = ("Esp_cv2", "Psp_cv2") if cach_e in ("cv2", "cv2_dv") else ("Esp_tp", "Psp_tp")
    ser = [dict(ten=m["ten"], mau=m["mau"], x=[g[kp] for g in m["nhom"]], y=[g[ke] for g in m["nhom"]], truc="y", kieu="ls") for m in kq["mau"] if m["nhom"]]
    hoan_thien("ragone", dict(tieu_de="Ragone", x_nhan=f"Power density ({u['P']})", y_nhan=f"Energy density ({u['E']})", log_x=True, log_y=True, series=ser), s)
    # 4) retention + CE ; 5) Csp/Q + CE theo chu kỳ
    for ma in HAI_TRUC:
        s = cai_dat_do_thi(ma, cau_hinh_dt)
        key, nhan_c, tn = _dai_luong(kq, s["dai_luong"])
        chinh_ve = {"Csp": "dien_dung", "dt_xa": "thoi_gian_xa"}.get(key, "dung_luong")
        dong_ghi = []
        s_val, s_ce = [], []
        for m in kq["mau"]:
            c = chuoi_retention(m, cfg, chinh_ve, s.get("nhom_j"), s.get("chu_ky_goc"))
            if not c:
                continue
            nh, ds = c
            dong_ghi.append(f"{m['ten']}: j = {nh['j']:.3g} {u['j']}, {len(ds)} chu kỳ")
            ks = [r["k"] for r in ds]
            if ma == "retention":
                s_val.append(dict(ten=m["ten"] + " retention", mau=m["mau"], x=ks, y=[r["retention"] for r in ds], truc="y", kieu="ls"))
            else:
                s_val.append(dict(ten=m["ten"], mau=m["mau"], x=ks, y=[r["gia_tri"] for r in ds], truc="y", kieu="ls"))
            ce = [r["CE"] for r in ds]
            if s["hien_ce"] and np.isfinite(ce).any():
                s_ce.append(dict(ten=m["ten"] + " CE", mau=m["mau"], x=ks, y=ce, truc="y2", kieu="open"))
        if ma == "retention":
            d = dict(tieu_de="Retention", x_nhan="Cycle number", y_nhan=f"{tn} retention (%)", y2_nhan="Coulombic efficiency (%)", log_x=False, log_y=False, series=s_val + s_ce)
        else:
            d = dict(tieu_de="Cycling", x_nhan="Cycle number", y_nhan=nhan_c, y2_nhan="Coulombic efficiency (%)", log_x=False, log_y=False, series=s_val + s_ce)
        d["ghi_chu"] = dong_ghi
        hoan_thien(ma, d, s)
    return ra


# ====================== VẼ MATPLOTLIB ======================
def ve_len_truc(fig, ax, dl, kieu=None):
    """Vẽ một đồ thị lên (fig, ax). kieu: cỡ chữ mặc định (từ hinh_tap_chi.kieu_chu); dl['hien_thi'] (do người dùng chỉnh) được ưu tiên."""
    k = dict(tick=10, nhan=11, ct=9, lw=1.6, khung=1.0, diem=None)
    k.update(kieu or {})
    ht = dl.get("hien_thi") or {}
    for nguon, dich in (("co_nhan", "nhan"), ("co_tick", "tick"), ("co_ct", "ct"), ("lw", "lw"), ("co_diem", "diem")):
        if ht.get(nguon) not in (None, ""):
            k[dich] = float(ht[nguon])
    diem = k["diem"] if k["diem"] else max(3.0, k["ct"] * 0.5)
    ax2 = None
    co_cot = any(x["kieu"] == "bar" and len(x["x"]) for x in dl["series"])
    if co_cot:                                                       # đồ thị cột: nhiều mẫu thì chia đều bề rộng cột
        xs = sorted({float(v) for x in dl["series"] if x["kieu"] == "bar" for v in x["x"]})
        khe = min([b - a for a, b in zip(xs, xs[1:])] or [1.0])
        n_cot = sum(1 for x in dl["series"] if x["kieu"] == "bar" and len(x["x"]))
        rong_cot = 0.7 * khe / n_cot
        i_cot = 0
    for s in dl["series"]:
        if not len(s["x"]):
            continue
        a = ax
        if s["truc"] == "y2":
            if ax2 is None:
                ax2 = ax.twinx()
            a = ax2
        if s["kieu"] == "bar":
            lech = (i_cot - (n_cot - 1) / 2.0) * rong_cot
            a.bar([float(v) + lech for v in s["x"]], s["y"], width=rong_cot, color=s["mau"], edgecolor="black", linewidth=max(0.8, k["lw"] * 0.5),
                  label=s["ten"], zorder=3)
            i_cot += 1
        elif s["kieu"] == "line":
            a.plot(s["x"], s["y"], color=s["mau"], lw=k["lw"], label=s["ten"])
        elif s["kieu"] == "open":
            a.plot(s["x"], s["y"], color=s["mau"], lw=0, marker="o", mfc="none", ms=diem, mew=k["lw"] * 0.8, label=s["ten"])
        else:
            a.plot(s["x"], s["y"], color=s["mau"], lw=k["lw"], marker="o", ms=diem, label=s["ten"])
    from matplotlib.ticker import FuncFormatter, NullFormatter
    so_thuong = FuncFormatter(lambda x, _: f"{x:g}")
    if dl["log_x"]:
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(so_thuong)
        ax.xaxis.set_minor_formatter(NullFormatter())
    if dl["log_y"]:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(so_thuong)
        ax.yaxis.set_minor_formatter(NullFormatter())

    def khoang(truc_ax, lo, hi, set_fn):
        if lo not in (None, "") or hi not in (None, ""):
            set_fn(None if lo in (None, "") else float(lo), None if hi in (None, "") else float(hi))
    khoang(ax, ht.get("x_min"), ht.get("x_max"), ax.set_xlim)
    khoang(ax, ht.get("y_min"), ht.get("y_max"), ax.set_ylim)
    ax.set_xlabel(dl["x_nhan"], fontsize=k["nhan"])
    ax.set_ylabel(dl["y_nhan"], fontsize=k["nhan"])
    if ax2 is not None:
        ax2.set_ylabel(dl.get("y2_nhan", ""), fontsize=k["nhan"])
        ax2.tick_params(labelsize=k["tick"], width=k["khung"])
        ax2.set_ylim(0, 110)
        khoang(ax2, ht.get("y2_min"), ht.get("y2_max"), ax2.set_ylim)
        for sp in ax2.spines.values():
            sp.set_linewidth(k["khung"])
    ax.tick_params(labelsize=k["tick"], width=k["khung"], direction="in")
    for sp in ax.spines.values():
        sp.set_linewidth(k["khung"])
    if co_cot:                                                       # kiểu hình mẫu: khung dày, chữ đậm, vạch chia ra ngoài, trục y bắt đầu từ 0
        from matplotlib.ticker import AutoMinorLocator
        kh = max(k["khung"] * 2.2, 2.0)
        for sp in ax.spines.values():
            sp.set_linewidth(kh)
        ax.tick_params(which="major", direction="out", width=kh, length=6, labelsize=k["tick"])
        ax.tick_params(which="minor", direction="out", width=kh * 0.8, length=3.5)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        for lb in ax.get_xticklabels() + ax.get_yticklabels():
            lb.set_fontweight("bold")
        ax.xaxis.label.set_fontweight("bold")
        ax.yaxis.label.set_fontweight("bold")
        if ht.get("y_min") in (None, "") and not dl["log_y"]:
            ax.set_ylim(0, ax.get_ylim()[1] * (1.14 if dl.get("nhan_phai") else 1.04))
        if ht.get("x_min") in (None, "") and ht.get("x_max") in (None, "") and not dl["log_x"]:
            ax.set_xlim(0, (max(xs) if xs else 1) + max(khe, 1.0))
            if xs and max(xs) + max(khe, 1.0) <= 15:
                from matplotlib.ticker import MultipleLocator
                ax.xaxis.set_major_locator(MultipleLocator(1))                   # vạch chính mỗi 1 A/g như hình mẫu
                ax.xaxis.set_minor_locator(MultipleLocator(0.5))
        ax.set_axisbelow(True)
        if dl.get("nhan_phai"):
            ax.text(0.96, 0.95, dl["nhan_phai"], transform=ax.transAxes, fontsize=k["nhan"] * 1.1, fontweight="bold", va="top", ha="right")
    if ht.get("luoi"):
        ax.grid(True, alpha=0.3, lw=0.6)
    if dl.get("insets"):
        _ve_inset(ax, dl["insets"], k, ht)
    if dl.get("nhan_tren"):
        ax.text(0.02, 0.97, dl["nhan_tren"], transform=ax.transAxes, fontsize=k["nhan"], fontweight="bold", va="top", ha="left")
    h, l = ax.get_legend_handles_labels()
    if ax2 is not None:
        h2, l2 = ax2.get_legend_handles_labels()
        h, l = h + h2, l + l2
    if h and ht.get("chu_thich", True) and not dl.get("nhan_phai"):
        ax.legend(h, l, fontsize=k["ct"], frameon=False, loc=("upper right" if dl.get("insets") and (ht.get("vi_tri") or "best") == "best" else (ht.get("vi_tri") or "best")))
    fig.tight_layout()


def _ve_inset(ax, insets, k, ht):
    """Các ô phóng đại (chu kỳ đầu/cuối) nằm phía trên đồ thị chính; nâng giới hạn trục y để dữ liệu chính không bị che."""
    lo, hi = ax.get_ylim()
    if ht.get("y_max") in (None, ""):
        ax.set_ylim(lo, lo + (hi - lo) / 0.50)
    for ins in insets:
        a2 = ax.inset_axes(ins["pos"])
        for s_ in ins["series"]:
            a2.plot(s_["x"], s_["y"], color=s_["mau"], lw=max(0.6, k["lw"] * 0.6))
        a2.tick_params(labelsize=max(4.0, k["tick"] * 0.55), width=max(0.5, k["khung"] * 0.7), direction="in", pad=1.5)
        for sp in a2.spines.values():
            sp.set_linewidth(max(0.5, k["khung"] * 0.7))
        a2.margins(x=0.0)
        a2.set_title(ins["nhan"], fontsize=max(5.0, k["ct"] * 0.7), pad=2)


def xuat_hinh(kq, thu_muc, ten="GCD", tap_chi=None, cot=1, dpi=300, ds=None, dang="png", cau_hinh_dt=None):
    """Xuất hình từng đồ thị (png/pdf/tiff/svg). Mỗi đồ thị có thể có mẫu tạp chí/cột/dpi riêng (cau_hinh_dt); không có thì dùng tham số chung."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    import hinh_tap_chi as ht_
    dl = du_lieu_do_thi(kq, cau_hinh_dt)
    ra = []
    for ma in (ds or list(TEN_DO_THI)):
        d = dl[ma]
        if not d["series"] or not any(len(s["x"]) for s in d["series"]):
            continue
        h = d["hien_thi"]
        tc = h["tap_chi"] if h["tap_chi"] and not str(h["tap_chi"]).startswith("(") else tap_chi
        cot_ = h["cot"] if (h["tap_chi"] and not str(h["tap_chi"]).startswith("(")) else cot
        kieu, rong = None, 3.4
        dpi_ = h["dpi"] or dpi
        if tc:
            m = ht_.mau(tc)
            kieu = ht_.kieu_chu(m)
            rong = ht_.rong_cm(m, cot_) / 2.54
            dpi_ = dpi_ or m["dpi"]
        fig = Figure(figsize=(rong, rong * 0.8) if tc else (6.0, 4.8), dpi=dpi_ or 300)
        ax = fig.add_subplot(111)
        ve_len_truc(fig, ax, d, kieu)
        p = os.path.join(thu_muc, f"{ten}_{ma}.{dang}")
        fig.savefig(p, dpi=dpi_ or 300)
        ra.append(p)
    return ra


# ====================== XUẤT EXCEL / CSV / JSON ======================
def _hang(x):
    return {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v) for k, v in x.items()}


def bang_thoi_gian(kq):
    """Mỗi mẫu: số chu kỳ, tổng thời gian đo, thời gian nạp/xả/chu kỳ trung bình, t xả đầu và cuối (retention theo thời gian xả kiểu Excel)."""
    out = []
    for m in kq["mau"]:
        ck = m["chu_ky"]
        if not ck:
            continue

        def tb(key):
            x = [r[key] for r in ck if np.isfinite(r[key])]
            return float(np.mean(x)) if x else float("nan")
        td0, td1 = ck[0]["dt_xa"], ck[-1]["dt_xa"]
        out.append(_hang({"Mẫu": m["ten"], "Số chu kỳ xả": len(ck), "Tổng thời gian (s)": m["t_tong"], "Tổng thời gian (h)": m["t_tong"] / 3600.0,
                          "t nạp TB (s)": tb("t_nap"), "t xả TB (s)": tb("dt_xa"), "Chu kỳ nạp–xả TB (s)": tb("T_ck"),
                          "t xả chu kỳ đầu (s)": td0, "t xả chu kỳ cuối (s)": td1,
                          "Giữ thời gian xả cuối/đầu (%)": td1 / td0 * 100.0 if td0 else float("nan")}))
    return out


def bang_ket_qua(kq, cau_hinh_dt=None):
    u = kq["don_vi"]
    tong, cky, rag, ret, cb = [], [], [], [], []
    for m in kq["mau"]:
        for g in m["nhom"]:
            tong.append(_hang({"Mẫu": m["ten"], f"j ({u['j']})": g["j"], "I (mA)": g["I_A"] * 1000, "Số chu kỳ": g["so_chu_ky"],
                               f"Csp ({u['C']})": g["Csp"], f"Qsp ({u['Q']})": g["Qsp"], f"E ({u['E']})": g["Esp"], f"P ({u['P']})": g["Psp"],
                               f"E ½CV² ({u['E']})": g["Esp_cv2"], f"P ½CV² ({u['P']})": g["Psp_cv2"],
                               "t nạp (s)": g["t_nap"], "t xả (s)": g["t_xa"], "Chu kỳ nạp–xả (s)": g["T_ck"],
                               "CE (%)": g["CE"], "EE (%)": g["EE"], "IR drop (V)": g["dV_IR"], "ESR (Ω)": g["ESR"], "R² tuyến tính": g["R2"], "Dạng đường xả": g["dang"]}))
            rag.append(_hang({"Mẫu": m["ten"], f"j ({u['j']})": g["j"], f"P tích phân ({u['P']})": g["Psp_tp"], f"E tích phân ({u['E']})": g["Esp_tp"],
                              f"P ½CV² ({u['P']})": g["Psp_cv2"], f"E ½CV² ({u['E']})": g["Esp_cv2"]}))
        for r in m["chu_ky"]:
            cky.append(_hang({"Mẫu": m["ten"], "Chu kỳ": r["chu_ky"], f"j ({u['j']})": r["j"], "I (mA)": r["I_A"] * 1000,
                              "Bắt đầu (s)": r["t0"], "t nạp (s)": r["t_nap"], "t xả (s)": r["dt_xa"], "Chu kỳ nạp–xả (s)": r["T_ck"], "ΔV dùng (V)": r["dV"],
                              "V_ext (V)": r["V_ext"], "V cuối (V)": r["V_cuoi"], "IR drop (V)": r["dV_IR"], "ESR (Ω)": r["ESR"],
                              "C (F, cell)": r["C_F"], f"Csp ({u['C']})": r["Csp"], f"Qsp ({u['Q']})": r["Qsp"], f"E ({u['E']})": r["Esp"], f"P ({u['P']})": r["Psp"],
                              "CE (%)": r["CE"], "EE (%)": r["EE"], "R²": r["R2"], "Dạng": r["dang"]}))
        sr = cai_dat_do_thi("retention", cau_hinh_dt)
        key_r, _, _ = _dai_luong(kq, sr["dai_luong"])
        c = chuoi_retention(m, kq["cfg"], {"Csp": "dien_dung", "dt_xa": "thoi_gian_xa"}.get(key_r, "dung_luong"), sr.get("nhom_j"), sr.get("chu_ky_goc"))
        if c:
            nh, ds = c
            for r in ds:
                ret.append(_hang({"Mẫu": m["ten"], f"j ({u['j']})": nh["j"], "Chu kỳ": r["k"], key_r: r["gia_tri"],
                                  "Retention (%)": r["retention"], "CE (%)": r["CE"]}))
        for c_ in m["canh_bao"]:
            cb.append({"Mẫu": m["ten"], "Nội dung": c_})
    for ten, e in kq["loi"]:
        cb.append({"Mẫu": ten, "Nội dung": "LỖI: " + e})
    return tong, cky, rag, ret, cb


def cong_thuc_ghi_chu(kq):
    cfg = kq["cfg"]
    he = ("4C/m (tế bào 2 điện cực đối xứng, m = tổng khối lượng: Stoller & Ruoff 2010)" if cfg["kieu_cell"] == "2dc" else
          "C/m, m = tổng khối lượng hai điện cực (điện dung của cả cell)" if cfg["kieu_cell"] == "2dc_cell" else "C/m (một điện cực / ba điện cực)")
    gom = cfg.get("cach_dv") == "gom_ir"
    ce = cfg.get("cach_e", "tich_phan")
    return [
        {"Mục": "Đại lượng chính", "Nội dung": ("Điện dung riêng F/g" if kq["chinh"] == "dien_dung" else "Dung lượng riêng mAh/g") + " — " + kq["ly_do"]},
        {"Mục": "Bộ công thức", "Nội dung": "Kiểu file Excel của người dùng (ΔV gồm IR drop, E = ½CΔV²)" if (gom and ce == "cv2_dv") else
                                          "Chuẩn (ΔV loại IR drop, E tích phân)" if (not gom and ce == "tich_phan") else "Tùy chọn riêng (xem từng dòng bên dưới)"},
        {"Mục": "Điện tích", "Nội dung": "Q = ∫|I|dt trên nửa chu kỳ xả (tích phân hình thang); dòng không đổi: Q = I·Δt."},
        {"Mục": "ΔV", "Nội dung": ("ΔV = V_đỉnh_nạp − V_cuối_xả, GỒM IR drop; Δt = t_xả tính từ lúc đảo dòng (khớp cột 'delta T', 'delta V' trong file Excel)."
                                   if gom else "ΔV = V_ext − V_cuối_xả, V_ext = điện thế ngoại suy về lúc đảo dòng (đã bỏ IR drop; Stoller & Ruoff, BioLogic AN51).")},
        {"Mục": "Điện dung (tích phân)", "Nội dung": "C = Q/ΔV = I·Δt/ΔV (hợp đường cong không tuyến tính)."},
        {"Mục": "Điện dung (độ dốc)", "Nội dung": f"C = I/|dV/dt| trên đoạn từ V_ext (sau IR drop) xuống V_cuối + {cfg['doc_p']:g}·ΔV (Gamry; Stoller & Ruoff: Vmax → ½Vmax)."},
        {"Mục": "Đang dùng", "Nội dung": "độ dốc" if cfg["cach_c"] == "do_doc" else "tích phân điện tích"},
        {"Mục": "IR drop, ESR", "Nội dung": "Ngoại suy tuyến tính 5–25% đầu nửa xả về lúc đảo dòng → V_ext; ΔV_IR = V_nạp-cuối − V_ext; ESR = ΔV_IR/(2I) (Gamry: U_loss = ESR·I ở mỗi chiều)."},
        {"Mục": "Điện dung riêng", "Nội dung": "Csp = " + he + "; chuẩn hóa theo " + ("khối lượng (mg nhập vào)" if cfg["chuan"] == "khoi_luong" else "diện tích (cm² nhập vào)") +
                                           ". Khớp file Excel: Csp = I(A)·Δt/(m(g)·ΔV)."},
        {"Mục": "Dung lượng riêng", "Nội dung": "Qsp = Q/(3.6·m) (mAh/g), theo đúng khối lượng đã nhập."},
        {"Mục": "Hiệu suất Coulomb", "Nội dung": "CE = Q_xả/Q_nạp·100 (dòng không đổi: = t_xả/t_nạp, như cột 'columbic eff' trong file Excel). CE > 100% là dấu hiệu báo cáo sai."},
        {"Mục": "Năng lượng, công suất", "Nội dung": ("E = ½·C·ΔV² (J/g) × 1000/3600 = Wh/kg (khớp Excel)" if ce == "cv2_dv" else
                                                      "E = ½C(V_ext² − V_cuối²) (tụ lý tưởng)" if ce == "cv2" else "E = ∫V·|I|dt (mọi đường cong)") +
                                              "; P = E·3600/Δt_xả (W/kg) (arXiv 1601.05173: W = ½CV², P = W/Δt). Trị số của vật liệu/điện cực theo chuẩn hóa đã chọn, khác với cell đóng gói."},
        {"Mục": "Thời gian chu kỳ", "Nội dung": "t nạp = thời gian của nửa nạp; t xả = Δt; chu kỳ nạp–xả = t nạp + t xả; 'Bắt đầu' = thời điểm bắt đầu nạp (s)."},
        {"Mục": "Retention", "Nội dung": f"retention_k = giá trị_k / giá trị_chu kỳ {cfg['chu_ky_goc']} · 100; giá trị = Csp, Qsp hoặc thời gian xả (retention theo t xả = cột 'CR%' của file Excel)."},
        {"Mục": "Điện thế hiển thị", "Nội dung": (f"Đồ thị vẽ theo RHE: E(RHE) = E đo + {cfg.get('nernst', 0.059):g}×pH({cfg.get('ph')}) + Eref({cfg.get('e_ref')} V)" if cfg.get("quy_rhe") else
                                                  "Đồ thị vẽ điện thế đo (chưa quy đổi RHE)") + ". Quy đổi chỉ dịch trục điện thế, không ảnh hưởng ΔV, C, E."},
        {"Mục": "Giá trị mỗi mức dòng", "Nội dung": "Trung vị các chu kỳ của mức dòng đó" + (" (bỏ chu kỳ đầu nếu nhóm ≥ 3 chu kỳ)." if cfg["bo_chu_ky_dau"] else ".")},
        {"Mục": "Dạng đường xả", "Nội dung": f"R² của V–t sau IR drop: ≥ {cfg['nguong_tu']} → tụ; {cfg['nguong_pin']}–{cfg['nguong_tu']} → lai; < {cfg['nguong_pin']} → pin (plateau). Ngưỡng là quy ước của app (heuristic), không phải của một bài báo."},
        {"Mục": "Chiều nạp", "Nội dung": "Điện thế tăng = nạp" if cfg["v_tang_nap"] else "Điện thế giảm = nạp"},
    ]


def xuat_tat_ca(kq, thu_muc, ten="GCD", ds_hinh=None, cau_hinh_dt=None):
    """Excel (+CSV từng đồ thị cho Origin) + JSON mô tả. Trả dict đường dẫn."""
    os.makedirs(thu_muc, exist_ok=True)
    tong, cky, rag, ret, cb = bang_ket_qua(kq, cau_hinh_dt)
    sheets = [("Tổng hợp theo dòng", tong or [{"Mẫu": ""}]), ("Từng chu kỳ", cky or [{"Mẫu": ""}]),
              ("Thời gian chu kỳ", bang_thoi_gian(kq) or [{"Mẫu": ""}]),
              ("Ragone", rag or [{"Mẫu": ""}]), ("Retention", ret or [{"Mẫu": "(không có nhóm dòng ≥ 3 chu kỳ)"}]),
              ("Công thức", cong_thuc_ghi_chu(kq)), ("Cảnh báo", cb or [{"Mẫu": "", "Nội dung": "Không phát hiện vấn đề nào."}])]
    p_x = os.path.join(thu_muc, f"{ten}_ket_qua.xlsx")
    try:
        import bao_cao
        bao_cao._ghi_xlsx(p_x, sheets)
    except Exception:
        p_x = os.path.join(thu_muc, f"{ten}_ket_qua.csv")
        import bao_cao
        bao_cao._ghi_csv(p_x, sheets)
    dl = du_lieu_do_thi(kq, cau_hinh_dt)
    ra = {"excel": p_x, "csv": {}, "json": None}
    mo_ta = {"ten": ten, "chinh": kq["chinh"], "don_vi": kq["don_vi"], "do_thi": {}}
    for ma, d in dl.items():
        if ma not in (ds_hinh or list(dl)):
            continue
        if not d["series"]:
            continue
        cot = {}
        for k, s in enumerate(d["series"]):
            cot[f"x{k}"] = pd.Series(s["x"], dtype=float)
            cot[f"y{k}"] = pd.Series(s["y"], dtype=float)
        df = pd.DataFrame(cot)
        p_c = os.path.join(thu_muc, f"{ten}_{ma}.csv")
        df.to_csv(p_c, index=False, encoding="utf-8-sig")
        ra["csv"][ma] = p_c
        ins_ghi = []
        for kk, ins in enumerate(d.get("insets") or [], 1):
            cot_i = {}
            for k2, s2 in enumerate(ins["series"]):
                cot_i[f"x{k2}"] = pd.Series(s2["x"], dtype=float)
                cot_i[f"y{k2}"] = pd.Series(s2["y"], dtype=float)
            p_i = os.path.join(thu_muc, f"{ten}_{ma}_inset{kk}.csv")
            pd.DataFrame(cot_i).to_csv(p_i, index=False, encoding="utf-8-sig")
            ins_ghi.append(dict(nhan=ins["nhan"], csv=p_i, pos=ins["pos"], series=[{k: v for k, v in s2.items() if k not in ("x", "y")} for s2 in ins["series"]]))
        mo_ta["do_thi"][ma] = dict({k: v for k, v in d.items() if k not in ("series", "insets")}, csv=p_c, insets=ins_ghi,
                                   series=[{k: v for k, v in s.items() if k not in ("x", "y")} for s in d["series"]])
    p_j = os.path.join(thu_muc, f"{ten}_origin.json")
    with open(p_j, "w", encoding="utf-8") as f:
        json.dump(mo_ta, f, ensure_ascii=False, indent=1)
    ra["json"] = p_j
    return ra


# ====================== TÓM TẮT CHỮ ======================
def _f(x, nd=3):
    return "—" if x is None or not np.isfinite(x) else f"{x:.{nd}g}"


def tom_tat(kq):
    u = kq["don_vi"]
    d = []
    d.append("ĐẠI LƯỢNG CHÍNH: " + ("điện dung riêng (" + u["C"] + ")" if kq["chinh"] == "dien_dung" else "dung lượng riêng (" + u["Q"] + ")"))
    d.append("   lý do: " + kq["ly_do"])
    d.append("")
    for m in kq["mau"]:
        d.append(f"■ {m['ten']}  ({len(m['chu_ky'])} chu kỳ xả; {m['gia_tri']:g} {'mg' if kq['cfg']['chuan'] == 'khoi_luong' else 'cm²'})")
        if m["nhom"]:
            d.append(f"   {'j ('+u['j']+')':>14} {'n':>4} {'Csp':>9} {'Qsp':>9} {'E':>9} {'P':>10} {'CE %':>7} {'ESR Ω':>8} {'R²':>6}  dạng")
            for g in m["nhom"]:
                d.append(f"   {_f(g['j']):>14} {g['so_chu_ky']:>4} {_f(g['Csp']):>9} {_f(g['Qsp']):>9} {_f(g['Esp']):>9} {_f(g['Psp']):>10} "
                         f"{_f(g['CE'], 4):>7} {_f(g['ESR']):>8} {_f(g['R2'], 3):>6}  {g['dang']}")
            ck = m["chu_ky"]
            if ck:
                tb_ = lambda k: float(np.nanmean([r[k] for r in ck]))  # noqa: E731
                d.append(f"   Thời gian: đo {m['t_tong']:.6g} s ({m['t_tong'] / 3600:.3g} h) · nạp TB {_f(tb_('t_nap'), 4)} s · xả TB {_f(tb_('dt_xa'), 4)} s"
                         f" · chu kỳ nạp–xả TB {_f(tb_('T_ck'), 4)} s")
            c = chuoi_retention(m, kq["cfg"], kq["chinh"])
            if c:
                nh, ds = c
                d.append(f"   Retention (j = {_f(nh['j'])} {u['j']}, {len(ds)} chu kỳ): {_f(ds[-1]['retention'], 4)} % sau chu kỳ {ds[-1]['k']}")
        for c_ in m["canh_bao"]:
            d.append("   ⚠ " + c_)
        d.append("")
    for ten, e in kq["loi"]:
        d.append(f"✖ {ten}: {e}")
    d.append(f"Đơn vị: Csp {u['C']} · Qsp {u['Q']} · E {u['E']} · P {u['P']}")
    return "\n".join(d)
