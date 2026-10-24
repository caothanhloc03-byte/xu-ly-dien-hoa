# -*- coding: utf-8 -*-
"""
Xuất BÁO CÁO TỔNG HỢP (Excel .xlsx) cho mọi file đã xử lý:
  • Sheet "CV-LSV": Epa, Ipa, Epc, Ipc, E1/2, I max, điện thế (và quá thế) tại mật độ dòng mục tiêu
  • Sheet "Tafel", "IT", "EIS", "ECSA" (tùy phép đo)
  • Sheet "Cảnh báo": các cảnh báo/gợi ý tự động
  • Sheet "Thông tin": thông số quy đổi, phiên bản, thời gian -> để tái lập kết quả

Nếu máy chưa có openpyxl thì tự xuất file CSV (bao_cao_tong_hop.csv, mở được bằng Excel) để không mất báo cáo.
"""
import csv
import datetime
import os
import platform

LUU = {"tafel": [], "ecsa_diem": None, "ecsa": None}
TEN_FILE = "bao_cao_tong_hop"


def reset():
    LUU["tafel"] = []
    LUU["ecsa_diem"] = None
    LUU["ecsa"] = None


def ghi(ten, gia_tri):
    """Các hàm xử lý gọi hàm này để gửi kết quả vào báo cáo."""
    if ten == "tafel":
        for i, c in enumerate(LUU["tafel"]):           # cùng nhãn -> thay bằng kết quả mới nhất
            if c.get("nhan") == gia_tri.get("nhan"):
                LUU["tafel"][i] = gia_tri
                return
        LUU["tafel"].append(gia_tri)
    else:
        LUU[ten] = gia_tri


def _so(x, nd=None):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return x
    if v != v:       # NaN
        return None
    return round(v, nd) if nd is not None else v


def _doc_phien_ban():
    try:
        import json
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.json"), encoding="utf-8") as f:
            return json.load(f).get("phien_ban_hien_tai", "?")
    except Exception:
        return "?"


# ====================== TẠO NỘI DUNG CÁC SHEET ======================
def _bang_cv_lsv(nc, ds_idx, i_muc_tieu, e_cb):
    import xu_ly_dien_hoa as xl
    hang = []
    for k in ds_idx:
        _, m = nc.lay(k + 1)
        d, loai = m["d"], m["loai"]
        ck = xl.chon_chu_ky(d, None) if loai == "CV" else 1
        h = {"Nhãn": nc.files[k][1], "File": os.path.basename(nc.files[k][0]), "Loại": loai, "Số điểm": len(d)}
        if loai == "CV":
            h["Chu kỳ dùng"] = f"{ck}/{int(d['chu_ky'].max())}"
        h["Tốc độ quét (mV/s)"] = _so(xl.toc_do_quet(d) * 1000, 3)
        ts = nc.thong_so(k + 1)
        rows = ts.get("bang_thong_so", [])
        r = next((r for r in rows if int(r.get("chu_ky", 0)) == ck), rows[-1] if rows else {})
        for ten, v in r.items():
            if ten != "chu_ky":
                h[ten] = _so(v, 4)
        for j in i_muc_tieu:
            kq = nc.the_tai_dong(k + 1, j, e_cb)
            h[f"E tại {j:g} mA/cm² (V vs RHE)"] = _so(kq.get("E_V_vs_RHE"), 4) if "loi" not in kq else None
            if e_cb is not None:
                h[f"Quá thế tại {j:g} mA/cm² (mV)"] = _so(kq.get("qua_the_mV"), 1) if "loi" not in kq else None
        hang.append(h)
    return hang


def _bang_it(nc, ds_idx):
    hang = []
    for k in ds_idx:
        ts = nc.thong_so(k + 1)
        h = {"Nhãn": nc.files[k][1], "File": os.path.basename(nc.files[k][0])}
        for ten, v in ts.items():
            if ten != "loai":
                h[ten] = _so(v, 4)
        hang.append(h)
    return hang


def _bang_eis(nc, ds_idx):
    return _bang_it(nc, ds_idx)


def _bang_tafel():
    return [{"Nhãn": t["nhan"], "Hệ số Tafel (mV/dec)": _so(t["he_so_Tafel (mV/dec)"], 2), "Số điểm": t["so_diem"],
             "Vùng dòng (mA/cm²)": t["vung_dong (mA/cm2)"]} for t in LUU["tafel"]]


def _bang_ecsa():
    kq = []
    if LUU["ecsa"] is not None:
        for _, r in LUU["ecsa"].iterrows():
            kq.append({"Mục": "Tổng hợp", **{k: _so(v, 5) for k, v in r.items()}})
    return kq, ([{k: (_so(v, 5) if not isinstance(v, str) else v) for k, v in r.items()}
                 for _, r in LUU["ecsa_diem"].iterrows()] if LUU["ecsa_diem"] is not None else [])


def _thong_tin(a, ds):
    return [
        ("Phần mềm", "Echem Studio"),
        ("Phiên bản", _doc_phien_ban()),
        ("Thời gian xuất", datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
        ("Hệ điều hành", platform.platform()),
        ("pH", getattr(a, "ph", "")),
        ("Điện thế điện cực so sánh Eref (V)", getattr(a, "eref", "")),
        ("Hệ số nhân dòng", getattr(a, "nhan_i", "")),
        ("Hệ số chia dòng (diện tích)", getattr(a, "chia_i", "")),
        ("Công thức E", f"E(RHE) = E + 0.0592 × {getattr(a, 'ph', '')} + {getattr(a, 'eref', '')}"),
        ("Công thức I", f"I (mA/cm²) = i × 1000 × {getattr(a, 'nhan_i', '')} ÷ {getattr(a, 'chia_i', '')}"),
        ("Loại phép đo", getattr(a, "loai", None) or "Tự nhận dạng"),
        ("Chu kỳ CV dùng", getattr(a, "chu_ky", None) or "Chu kỳ cuối (mặc định)"),
        ("Vùng dòng Tafel (mA/cm²)", f"{getattr(a, 'tafel_min', '')} - {getattr(a, 'tafel_max', '')}"),
        ("Cs dùng cho ECSA (mF/cm²)", getattr(a, "cs", "")),
        ("Điện thế cân bằng dùng tính quá thế (V)", getattr(a, "e_can_bang", "")),
        ("Số file", len(ds)),
    ] + [(f"File {i + 1}", p) for i, p in enumerate(ds)]


def _bang_canh_bao():
    try:
        import canh_bao
        return [{"Mức độ": {"nang": "Nặng", "canh_bao": "Cảnh báo", "luu_y": "Lưu ý", "goi_y": "Gợi ý"}.get(c["muc_do"], c["muc_do"]),
                 "Đối tượng": c["doi_tuong"], "Nội dung": c["noi_dung"]} for c in canh_bao.DANH_SACH]
    except ImportError:
        return []


def tao_noi_dung(a, ds):
    """Trả về list[(ten_sheet, [dict hàng])] hoặc (ten, [(khóa, giá trị)]) cho 'Thông tin'."""
    import cong_cu
    loai_ep = (getattr(a, "loai", None) or "").upper() or None
    i_muc_tieu = []
    for x in str(getattr(a, "i_muc_tieu", "10")).replace(";", ",").split(","):
        try:
            if x.strip():
                i_muc_tieu.append(float(x))
        except ValueError:
            pass
    e_cb = getattr(a, "e_can_bang", None)

    sheets = []
    if getattr(a, "ecsa", False):
        tong, diem = _bang_ecsa()
        if tong:
            sheets.append(("ECSA", tong))
        if diem:
            sheets.append(("ECSA - điểm", diem))
    else:
        files = [(p, (a.nhan[k] if getattr(a, "nhan", None) and k < len(a.nhan) and a.nhan[k] else os.path.splitext(os.path.basename(p))[0]))
                 for k, p in enumerate(ds)]
        nc = cong_cu.NguCanh(files, a.ph, a.eref, a.nhan_i, a.chia_i, None if loai_ep == "TAFEL" else loai_ep)
        nhom = {}
        for k in range(len(files)):
            try:
                loai = nc.lay(k + 1)[1]["loai"]
            except Exception as e:
                nhom.setdefault("loi", []).append({"Nhãn": files[k][1], "Lỗi": str(e)})
                continue
            nhom.setdefault(loai, []).append(k)
        cv_lsv = nhom.get("CV", []) + nhom.get("LSV", [])
        if cv_lsv:
            sheets.append(("CV-LSV", _bang_cv_lsv(nc, cv_lsv, i_muc_tieu, e_cb)))
        if nhom.get("IT"):
            sheets.append(("IT", _bang_it(nc, nhom["IT"])))
        if nhom.get("EIS"):
            sheets.append(("EIS", _bang_eis(nc, nhom["EIS"])))
        if loai_ep == "TAFEL" and LUU["tafel"]:
            sheets.append(("Tafel", _bang_tafel()))
        if nhom.get("loi"):
            sheets.append(("Lỗi đọc file", nhom["loi"]))
    cb = _bang_canh_bao()
    sheets.append(("Cảnh báo", cb if cb else [{"Mức độ": "", "Đối tượng": "", "Nội dung": "Không phát hiện vấn đề nào."}]))
    sheets.append(("Thông tin", [{"Mục": k, "Giá trị": v} for k, v in _thong_tin(a, ds)]))
    return sheets


# ====================== GHI FILE ======================
def _ghi_xlsx(duong, sheets):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    wb.remove(wb.active)
    dau = PatternFill("solid", fgColor="1F3864")
    mau = {"Nặng": "F8CBAD", "Cảnh báo": "FFE699", "Lưu ý": "DDEBF7", "Gợi ý": "E2EFDA"}
    for ten, hang in sheets:
        ws = wb.create_sheet(ten[:31])
        cot = []
        for h in hang:
            for k in h:
                if k not in cot:
                    cot.append(k)
        ws.append(cot)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = dau
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for h in hang:
            ws.append([h.get(k) for k in cot])
        for j, k in enumerate(cot, 1):
            rong = max([len(str(k))] + [len(str(h.get(k, ""))) for h in hang]) + 2
            ws.column_dimensions[get_column_letter(j)].width = min(max(rong, 10), 90 if ten in ("Cảnh báo", "Thông tin") else 40)
        for r in ws.iter_rows(min_row=2):
            for c in r:
                if isinstance(c.value, float):
                    c.number_format = "0.0000"
                c.alignment = Alignment(vertical="top", wrap_text=ten in ("Cảnh báo", "Thông tin"))
            if ten == "Cảnh báo" and r and r[0].value in mau:
                for c in r:
                    c.fill = PatternFill("solid", fgColor=mau[r[0].value])
        ws.freeze_panes = "A2"
    wb.save(duong)


def _ghi_csv(duong, sheets):
    with open(duong, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for ten, hang in sheets:
            w.writerow([f"# {ten}"])
            cot = []
            for h in hang:
                for k in h:
                    if k not in cot:
                        cot.append(k)
            w.writerow(cot)
            for h in hang:
                w.writerow([h.get(k, "") for k in cot])
            w.writerow([])


def xuat(a, ds, thu_muc):
    """Xuất báo cáo vào `thu_muc`. Trả về đường dẫn file đã tạo."""
    os.makedirs(thu_muc, exist_ok=True)
    sheets = tao_noi_dung(a, ds)
    try:
        import openpyxl  # noqa: F401
        duong = os.path.join(thu_muc, TEN_FILE + ".xlsx")
        _ghi_xlsx(duong, sheets)
    except ImportError:
        duong = os.path.join(thu_muc, TEN_FILE + ".csv")
        _ghi_csv(duong, sheets)
        print("  (luu y) may chua co openpyxl nen xuat bao cao dang CSV (mo duoc bang Excel).")
    except PermissionError:
        raise PermissionError(f"Không ghi được {TEN_FILE}.xlsx - hãy đóng file này nếu đang mở trong Excel rồi chạy lại.")
    return duong
