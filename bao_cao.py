# -*- coding: utf-8 -*-
"""
Xuất BÁO CÁO TỔNG HỢP (Excel .xlsx) cho mọi file đã xử lý:
  • Sheet "CV-LSV": Epa, Ipa, Epc, Ipc, E1/2, I max, điện thế (và quá thế) tại mật độ dòng mục tiêu
  • Sheet "Tafel" (Tafel từ LSV/CV), "Tafel (Qs-LSV)" (nếu đã chạy Tafel trong công cụ Qs-LSV), "IT", "EIS", "ECSA" (tùy phép đo)
  • Sheet "Cảnh báo": các cảnh báo/gợi ý tự động
  • Sheet "Thông tin": thông số quy đổi, phiên bản, thời gian -> để tái lập kết quả

Nếu máy chưa có openpyxl thì tự xuất file CSV (bao_cao_tong_hop.csv, mở được bằng Excel) để không mất báo cáo.
"""
import csv
import datetime
import os
import platform

LUU = {"tafel": [], "tafel_qs": [], "ecsa_diem": None, "ecsa": None, "so_sanh": None, "so_sanh_nhom": None, "so_sanh_tai_lieu": None, "fe": None, "fit_eis": None, "tof_cv": None}
TEN_FILE = "bao_cao_tong_hop"


def reset():
    LUU["tafel"] = []
    LUU["tafel_qs"] = []
    LUU["ecsa_diem"] = None
    LUU["ecsa"] = None
    for k in ("so_sanh", "so_sanh_nhom", "so_sanh_tai_lieu", "fe", "fit_eis", "tof_cv"):
        LUU[k] = None


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


def _bang_tafel_qs():
    return [{"Nhãn": t["nhan"], "Hệ số Tafel (mV/dec)": _so(t["he_so_Tafel (mV/dec)"], 2), "Sai số (mV/dec)": _so(t.get("sai_so (mV/dec)"), 2),
             "R²": _so(t.get("R2"), 4), "Số điểm": t["so_diem"], "Vùng chọn": t["vung_dong (mA/cm2)"]} for t in LUU["tafel_qs"]]


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
        ("Hệ số Nernst (V/pH)", getattr(a, "nernst", 0.0592)),
        ("Công thức E", f"E(RHE) = E + {getattr(a, 'nernst', 0.0592):g} × {getattr(a, 'ph', '')} + {getattr(a, 'eref', '')}"),
        ("Công thức I", f"I (mA/cm²) = i × 1000 × {getattr(a, 'nhan_i', '')} ÷ {getattr(a, 'chia_i', '')}"),
        ("Loại phép đo", getattr(a, "loai", None) or "Tự nhận dạng"),
        ("Chu kỳ CV dùng", getattr(a, "chu_ky", None) or "Chu kỳ cuối (mặc định)"),
        ("Vùng dòng Tafel (mA/cm²)", f"{getattr(a, 'tafel_min', '')} - {getattr(a, 'tafel_max', '')}"),
        ("Vùng Tafel theo điện thế (V)", f"{getattr(a, 'tafel_e_min', '')} - {getattr(a, 'tafel_e_max', '')}" if getattr(a, "tafel_e_min", None) is not None else ""),
        ("Tafel Qs-LSV", "Lấy từ công cụ Qs-LSV (fit E theo log|J| trên điểm Qs-LSV; vùng, số điểm ghi ở sheet 'Tafel (Qs-LSV)')"),
        ("Cs dùng cho ECSA (mF/cm²)", getattr(a, "cs", "")),
        ("Điện thế cân bằng dùng tính quá thế (V)", getattr(a, "e_can_bang", "")),
        ("Bù iR: Rs (Ω) / phần trăm bù", f"{getattr(a, 'r_s', 0) or 0} / {getattr(a, 'ir_phan_tram', 100)}"),
        ("Tải trọng xúc tác (mg/cm²)", getattr(a, "tai_trong", None) or ""),
        ("Số tâm hoạt động (µmol/cm²) / M (g/mol) / tỉ lệ tâm", f"{getattr(a, 'so_mol_tam', None) or ''} / {getattr(a, 'khoi_luong_mol', None) or ''} / {getattr(a, 'ti_le_tam', '')}"),
        ("Quá thế khảo sát (mV) / n electron", f"{getattr(a, 'qua_the_ht', '')} / {getattr(a, 'n_e', '')}"),
        ("Chế độ điện thế", "Điện thế tế bào (không quy đổi RHE)" if getattr(a, "khong_rhe", False) else "RHE"),
        ("FE: thể tích khí (mL) / T (°C) / P (kPa) / n", f"{getattr(a, 'fe_v_h2', None) or ''} / {getattr(a, 'fe_nhiet_do', '')} / {getattr(a, 'fe_ap_suat', '')} / {getattr(a, 'fe_n', '')}"),
        ("Số file", len(ds)),
    ] + [(f"File {i + 1}", p) for i, p in enumerate(ds)]


def _bang_canh_bao():
    try:
        import canh_bao
        return [{"Mức độ": {"nang": "Nặng", "canh_bao": "Cảnh báo", "luu_y": "Lưu ý", "goi_y": "Gợi ý"}.get(c["muc_do"], c["muc_do"]),
                 "Đối tượng": c["doi_tuong"], "Nội dung": c["noi_dung"]} for c in canh_bao.DANH_SACH]
    except ImportError:
        return []


# ====================== SỐ LIỆU ĐÃ XỬ LÝ ĐỂ VẼ HÌNH ======================
# CAU_TRUC[tên sheet] = mô tả sheet "Số liệu vẽ": số cột/mẫu, loại biểu đồ và tên trục (để _ghi_xlsx vẽ sẵn biểu đồ Excel).
CAU_TRUC = {}


def _cot_dai(cot):
    """dict {tên cột: dãy số} (độ dài khác nhau) -> list[dict hàng] (ô thiếu = None) để ghi sheet dạng cột song song."""
    n = max((len(v) for v in cot.values()), default=0)
    hang = []
    for i in range(n):
        h = {}
        for k, v in cot.items():
            h[k] = _so(v[i]) if i < len(v) else None
        hang.append(h)
    return hang


def _them_cot(cot, ten, v):
    k = ten
    while k in cot:
        k += "_"
    cot[k] = list(v)


def _so_lieu_ve(a, ds):
    """Số liệu đã xử lý từ file thô (quy đổi RHE, đổi sang mA/cm², bù iR, chọn chu kỳ, vùng Tafel...) đúng như dùng để vẽ hình:
    mỗi mẫu 1 cặp cột X-Y cạnh nhau (Tafel: 2 cặp - điểm và đường fit), kèm biểu đồ Excel dựng sẵn."""
    import xu_ly_dien_hoa as xl
    CAU_TRUC.clear()
    muc = []
    for k, p in enumerate(ds):
        try:
            muc.append(xl.nap_muc(p, a, k))
        except Exception as e:  # noqa: BLE001 - file lỗi đã được báo ở sheet "Lỗi đọc file"
            print(f"  (luu y) bo qua {os.path.basename(p)} khi xuat so lieu ve: {e}")
    sheets = []
    loai_ep = (getattr(a, "loai", None) or "").upper()
    ck = getattr(a, "chu_ky", None)
    for loai, ten_sheet, x_ten, y_ten in (("CV", "Vẽ CV", xl.NHAN_E, xl.NHAN_I), ("LSV", "Vẽ LSV", xl.NHAN_E, xl.NHAN_I)):
        nhom = [m for m in muc if m["loai"] == loai]
        if not nhom:
            continue
        cot = {}
        for m in nhom:
            x, y = xl.duong_cv_lsv(m, ck)
            _them_cot(cot, f"{m['nhan']} | {x_ten}", x)
            _them_cot(cot, f"{m['nhan']} | {y_ten}", y)
        sheets.append((ten_sheet, _cot_dai(cot)))
        CAU_TRUC[ten_sheet] = {"cot": 2, "kieu": "duong", "x": x_ten, "y": y_ten, "mau": [m["mau"] for m in nhom]}
    nhom = [m for m in muc if m["loai"] == "IT"]
    if nhom:
        cot = {}
        for m, t, i in xl.duong_it(nhom, getattr(a, "noi_tiep", False)):
            _them_cot(cot, f"{m['nhan']} | T (h)", t)
            _them_cot(cot, f"{m['nhan']} | {xl.NHAN_I}", i)
        sheets.append(("Vẽ IT", _cot_dai(cot)))
        CAU_TRUC["Vẽ IT"] = {"cot": 2, "kieu": "duong", "x": "T (h)", "y": xl.NHAN_I, "mau": [m["mau"] for m in nhom]}
    nhom = [m for m in muc if m["loai"] == "EIS"]
    if nhom:
        cot = {}
        for m in nhom:
            for c in ("Z' (ohm)", "-Z'' (ohm)", "f (Hz)", "|Z| (ohm)", "pha (do)"):
                _them_cot(cot, f"{m['nhan']} | {c}", m["d"][c].to_numpy())
        sheets.append(("Vẽ EIS", _cot_dai(cot)))
        CAU_TRUC["Vẽ EIS"] = {"cot": 5, "kieu": "duong", "x": "Z' (Ω)", "y": "-Z'' (Ω)", "mau": [m["mau"] for m in nhom]}
    if loai_ep == "TAFEL":
        cot, mau = {}, []
        for m in muc:
            if m["loai"] not in ("CV", "LSV", "TAFEL"):
                continue
            try:
                df_t, slope, a_s, b_i = xl.tafel_a(m["d"], a)
            except Exception as e:  # noqa: BLE001
                print(f"  (luu y) khong tinh duoc Tafel cho {m['nhan']} khi xuat so lieu ve: {e}")
                continue
            lj = df_t["Log(J)"].to_numpy()
            xf = [float(lj.min()), float(lj.max())]
            nh = f"{m['nhan']} ({slope:.1f} mV/dec)"
            _them_cot(cot, f"{nh} | Log(J)", lj)
            _them_cot(cot, f"{nh} | {xl.NHAN_POT}", df_t["Potential (V vs RHE)"].to_numpy())
            _them_cot(cot, f"{nh} | Log(J) fit", xf)
            _them_cot(cot, f"{nh} | E fit = a*logJ + b", [a_s * x + b_i for x in xf])
            mau.append(m["mau"])
        if cot:
            sheets.append(("Vẽ Tafel", _cot_dai(cot)))
            CAU_TRUC["Vẽ Tafel"] = {"cot": 4, "kieu": "tafel", "x": "Log(J)", "y": xl.NHAN_POT, "mau": mau}
    return sheets



def tao_noi_dung(a, ds, so_lieu_gia_tri=False):
    """Trả về list[(ten_sheet, [dict hàng])] hoặc (ten, [(khóa, giá trị)]) cho 'Thông tin'."""
    CAU_TRUC.clear()
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
    if getattr(a, "khong_qua_the", False) or getattr(a, "khong_rhe", False):
        e_cb = None

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
        nc = cong_cu.NguCanh(files, a.ph, a.eref, a.nhan_i, a.chia_i, None if loai_ep == "TAFEL" else loai_ep,
                             r_s=getattr(a, "r_s", 0.0) or 0.0, ir_pct=getattr(a, "ir_phan_tram", 100.0),
                             khong_rhe=getattr(a, "khong_rhe", False), nernst=getattr(a, "nernst", 0.0592))
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
        try:                                           # Tafel từ công cụ Qs-LSV: lấy kết quả đã lưu, khớp theo nhãn mẫu
            import tafel_qs
            LUU["tafel_qs"] = []
            for _, nh in files:
                b = tafel_qs.cua(nh)
                if b and not any(x["nhan"] == b["nhan"] for x in LUU["tafel_qs"]):
                    LUU["tafel_qs"].append(b)
        except ImportError:
            pass
        if loai_ep == "TAFEL" and LUU["tafel"]:
            sheets.append(("Tafel", _bang_tafel()))
        if LUU["tafel_qs"]:
            sheets.append(("Tafel (Qs-LSV)", _bang_tafel_qs()))
        if nhom.get("loi"):
            sheets.append(("Lỗi đọc file", nhom["loi"]))
        if so_lieu_gia_tri and not getattr(a, "khong_so_lieu_ve", False):      # chỉ khi KHÔNG có openpyxl (xuất CSV): số liệu vẽ dạng giá trị
            try:
                sheets.extend(_so_lieu_ve(a, ds))
            except Exception as e:  # noqa: BLE001 - lỗi phần phụ không được làm mất báo cáo chính
                print(f"  (canh bao) khong xuat duoc so lieu ve hinh: {e}")
    for khoa, ten_sheet in (("so_sanh", "So sánh mẫu"), ("so_sanh_nhom", "Nhóm (TB ± SD)"), ("so_sanh_tai_lieu", "So sánh tài liệu"),
                            ("fe", "Hiệu suất Faraday"), ("fit_eis", "Fit EIS"), ("tof_cv", "TOF từ CV")):
        if LUU.get(khoa):
            sheets.append((ten_sheet, LUU[khoa]))
    cb = _bang_canh_bao()
    sheets.append(("Cảnh báo", cb if cb else [{"Mức độ": "", "Đối tượng": "", "Nội dung": "Không phát hiện vấn đề nào."}]))
    sheets.append(("Thông tin", [{"Mục": k, "Giá trị": v} for k, v in _thong_tin(a, ds)]))
    return sheets


# ====================== GHI FILE ======================
def _ghi_xlsx(duong, sheets, a=None, ds=None):
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
    if a is not None and not getattr(a, "khong_so_lieu_ve", False):
        try:
            import bao_cao_cong_thuc
            truoc = len(wb.sheetnames)
            bao_cao_cong_thuc.them_vao(wb, a, ds or [])
            moi = wb._sheets[truoc:]                      # đặt các sheet công thức trước "Cảnh báo" / "Thông tin"
            if moi:
                wb._sheets = wb._sheets[:truoc]
                vt = next((i for i, w in enumerate(wb._sheets) if w.title == "Cảnh báo"), len(wb._sheets))
                wb._sheets[vt:vt] = moi
        except Exception as e:  # noqa: BLE001 - lỗi phần phụ không được làm mất báo cáo chính
            print(f"  (canh bao) khong tao duoc cac sheet cong thuc: {e}")
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
    try:
        import openpyxl  # noqa: F401
        co_xlsx = True
    except ImportError:
        co_xlsx = False
    sheets = tao_noi_dung(a, ds, so_lieu_gia_tri=not co_xlsx)
    nop = getattr(a, "goi_nop_bai", False)
    if nop:
        try:
            import nop_bai
            nop_bai.tao(sheets, a, ds, thu_muc, LUU["tafel_qs"] or LUU["tafel"])
        except Exception as e:  # noqa: BLE001 - không để lỗi phần phụ làm mất báo cáo chính
            print(f"  (canh bao) khong tao duoc goi nop bai: {e}")
            nop = False
    try:
        import openpyxl  # noqa: F401
        duong = os.path.join(thu_muc, TEN_FILE + ".xlsx")
        _ghi_xlsx(duong, sheets, a, ds)
    except ImportError:
        duong = os.path.join(thu_muc, TEN_FILE + ".csv")
        _ghi_csv(duong, sheets)
        print("  (luu y) may chua co openpyxl nen xuat bao cao dang CSV (mo duoc bang Excel).")
    except PermissionError:
        raise PermissionError(f"Không ghi được {TEN_FILE}.xlsx - hãy đóng file này nếu đang mở trong Excel rồi chạy lại.")
    if nop:
        try:
            nop_bai.goi_tai_lap(a, ds, thu_muc)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) khong tao duoc goi_tai_lap.zip: {e}")
    return duong
