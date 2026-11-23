# -*- coding: utf-8 -*-
"""Sheet dữ liệu THÔ + dữ liệu ĐÃ XỬ LÝ bằng CÔNG THỨC Excel (bố cục giống worksheet Origin: Long Name / Units / Comments / F(x)=).

Mục đích: người đọc/phản biện mở file Excel là kiểm chứng được từng con số - mọi ô "đã xử lý" là công thức trỏ về ô số liệu thô
và các ô trong sheet "Thông số xử lý" (đổi pH, Eref, Rs... thì kết quả tự cập nhật). Giá trị công thức = đúng giá trị app dùng để vẽ hình.
"""
import os

import numpy as np

CAU_HINH_TEN = (("pH_dd", "pH", "pH dung dịch", "ph"),
                ("E_ref", "Eref (V)", "Điện thế điện cực so sánh so với SHE", "eref"),
                ("k_Nernst", "k (V/pH)", "Hệ số Nernst: E_RHE = E + k·pH + Eref", "nernst"),
                ("RHE_bat", "Quy đổi RHE (1 = có, 0 = không)", "0 khi đo tế bào 2 điện cực (không quy đổi)", None),
                ("I_nhan", "Hệ số nhân dòng", "J = i × 1000 × nhân / chia", "nhan_i"),
                ("I_chia", "Hệ số chia dòng (cm²)", "Diện tích điện cực (hoặc hệ số chia)", "chia_i"),
                ("R_s", "Rs (Ω)", "Điện trở dung dịch dùng bù iR (0 = không bù)", "r_s"),
                ("iR_pct", "% bù iR", "E_thật = E_đo − i·Rs·%/100", "ir_phan_tram"))
TEN_THONG_SO = "Thông số xử lý"
HANG_DAU = 4           # 4 hàng tiêu đề (Long Name, Units, Comments, F(x)=); số liệu bắt đầu từ hàng 5
HANG_DAU_SO_LIEU = HANG_DAU + 1


def _cot(n):
    from openpyxl.utils import get_column_letter
    return get_column_letter(n)


def _q(ten):
    return "'" + ten.replace("'", "''") + "'"


def _gia_tri_tham_so(a):
    kq = {}
    for ten, _, _, thuoc_tinh in CAU_HINH_TEN:
        if ten == "RHE_bat":
            kq[ten] = 0 if getattr(a, "khong_rhe", False) else 1
        else:
            v = getattr(a, thuoc_tinh, None)
            if ten == "k_Nernst" and v is None:
                v = 0.0592
            if ten == "R_s":
                v = float(v or 0.0)
            if ten == "iR_pct" and v is None:
                v = 100.0
            kq[ten] = float(v) if v is not None else 0.0
    return kq


def _sheet_thong_so(wb, a):
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.workbook.defined_name import DefinedName
    ws = wb.create_sheet(TEN_THONG_SO)
    ws.append(["Tên (dùng trong công thức)", "Giá trị", "Ý nghĩa", "Ghi chú"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    gt = _gia_tri_tham_so(a)
    for i, (ten, y_nghia, ghi_chu, _) in enumerate(CAU_HINH_TEN, 2):
        ws.append([ten, gt[ten], y_nghia, ghi_chu])
        ws.cell(row=i, column=2).fill = PatternFill("solid", fgColor="FFF2CC")       # ô được phép sửa
        wb.defined_names[ten] = DefinedName(ten, attr_text=f"{_q(TEN_THONG_SO)}!$B${i}")
    n = len(CAU_HINH_TEN) + 3
    ws.cell(row=n, column=1, value="Công thức đã dùng").font = Font(bold=True)
    for j, t in enumerate((
            "E_RHE (V) = E_thô + RHE_bat × (k_Nernst × pH_dd + E_ref) − i_thô × R_s × iR_pct / 100",
            "J (mA/cm²) = i_thô (A) × 1000 × I_nhan / I_chia",
            "T (h) = T_thô (s) / 3600",
            "Tafel: Log(J) = LOG10(|J|); hệ số b (mV/dec) = SLOPE(E, Log(J)) × 1000",
            "ECSA: Cdl (mF/cm²) = SLOPE(ΔJ, v), ΔJ = (Ja − Jc)/2, v (V/s); ECSA = Cdl / Cs",
            "Ô nền vàng ở cột B là tham số: sửa giá trị thì toàn bộ sheet 'Xử lý ...' và hệ số Tafel/Cdl tự tính lại."), n + 1):
        ws.cell(row=j, column=1, value=t)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 36
    ws.column_dimensions["D"].width = 60
    ws.freeze_panes = "A2"
    return ws


def _dau_trang(ws, so_cot, nhan_hang):
    """Cột A: nhãn hàng kiểu Origin + số thứ tự; 4 hàng tiêu đề nền vàng nhạt."""
    from openpyxl.styles import Alignment, Font, PatternFill
    vang = PatternFill("solid", fgColor="FFFFCC")
    for r, t in enumerate(nhan_hang, 1):
        c = ws.cell(row=r, column=1, value=t)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="right")
        for j in range(2, so_cot + 2):
            ws.cell(row=r, column=j).fill = vang
            ws.cell(row=r, column=j).alignment = Alignment(horizontal="center", wrap_text=False)
    ws.column_dimensions["A"].width = 11
    for j in range(2, so_cot + 2):
        ws.column_dimensions[_cot(j)].width = 16
    ws.freeze_panes = ws.cell(row=HANG_DAU_SO_LIEU, column=2)


def _ghi_tieu_de(ws, cot, ln, don_vi, ghi_chu, fx):
    ws.cell(row=1, column=cot, value=ln)
    ws.cell(row=2, column=cot, value=don_vi)
    ws.cell(row=3, column=cot, value=ghi_chu)
    ws.cell(row=4, column=cot, value=fx)


def _bieu_do(ws, cap, n_hang, x_ten, y_ten, mau, o_dat, tieu_de=None, kieu_diem=None):
    """cap: [(cot_x, cot_y, cot_ten)]; hàng số liệu 5..4+n_hang. kieu_diem[i]: True = chấm (không nối), False = đường."""
    from openpyxl.chart import Reference, ScatterChart, Series
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.data_source import StrRef
    ch = ScatterChart()
    ch.style = 2
    ch.scatterStyle = "lineMarker"
    ch.height, ch.width = 11, 18
    if tieu_de:
        ch.title = tieu_de
    ch.x_axis.title, ch.y_axis.title = x_ten, y_ten
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.legend.position = "b"
    for i, (cx, cy, ct, n) in enumerate(cap):
        x = Reference(ws, min_col=cx, min_row=HANG_DAU_SO_LIEU, max_row=HANG_DAU + n)
        y = Reference(ws, min_col=cy, min_row=HANG_DAU_SO_LIEU, max_row=HANG_DAU + n)
        sr = Series(y, x)
        sr.tx = SeriesLabel(strRef=StrRef(f"{_q(ws.title)}!${_cot(ct)}$1"))
        m = mau[i] if i < len(mau) else None
        diem = bool(kieu_diem and kieu_diem[i])
        if diem:
            sr.marker.symbol = "circle"
            sr.marker.size = 5
            sr.graphicalProperties.line.noFill = True
            if m:
                sr.marker.graphicalProperties.solidFill = m
                sr.marker.graphicalProperties.line.solidFill = m
        else:
            sr.marker.symbol = "none"
            sr.smooth = False
            sr.graphicalProperties.line.width = 19050
            if m:
                sr.graphicalProperties.line.solidFill = m
            if kieu_diem is not None:
                sr.graphicalProperties.line.dashStyle = "dash"
        ch.series.append(sr)
    ws.add_chart(ch, o_dat)


def _hex(m):
    try:
        from matplotlib.colors import to_hex
        return to_hex(m).lstrip("#").upper()
    except Exception:
        return None


def _doc_tho(duong_dan):
    import xu_ly_dien_hoa as xl
    tho, _ = xl.doc_file_tho(duong_dan)
    return tho


def _nap_mau(a, ds):
    import xu_ly_dien_hoa as xl
    muc = []
    bo_qua = {os.path.normcase(os.path.abspath(x)) for x in (getattr(a, "ecsa_bo_qua", None) or [])}
    for k, p in enumerate(ds):
        if getattr(a, "ecsa", False) and os.path.normcase(os.path.abspath(p)) in bo_qua:
            continue
        try:
            m = xl.nap_muc(p, a, k)
            m["tho"] = _doc_tho(p)
            muc.append(m)
        except Exception as e:  # noqa: BLE001
            print(f"  (luu y) bo qua {os.path.basename(p)} khi xuat sheet cong thuc: {e}")
    return muc


def _sheet_tho_xu_ly(wb, ten_tho, ten_xl, nhom, a, loai):
    """Tạo sheet thô + sheet xử lý (công thức) cho 1 nhóm mẫu cùng loại (CV/LSV/TAFEL/IT).
    Trả về thông tin vị trí cột để các sheet phân tích (Tafel...) trỏ tiếp: [{muc, cot_e, cot_j, hang_cua_vt: {vị trí gốc: số hàng}}]."""
    import xu_ly_dien_hoa as xl
    wt = wb.create_sheet(ten_tho)
    wx = wb.create_sheet(ten_xl)
    nhan_hang = ["Long Name", "Units", "Comments", "F(x)="]
    cot_t = 2
    cot_x = 2
    info, cap_bd, mau, tong_hang = [], [], [], []
    off = 0.0
    for m in nhom:
        tho, d = m["tho"], m["d"]
        n_tho = len(tho)
        # ----- sheet THÔ: E (V), i (A), T (s)[, chu kỳ] -----
        ten_m = m["nhan"]
        cac_cot = [("E", "V", "c1"), ("i", "A", "c2"), ("T", "s", "c3")]
        if loai in ("CV", "LSV", "TAFEL"):
            cac_cot.append(("chu kỳ", "", None))
        c0 = cot_t
        for j, (ln, dv, ten_c) in enumerate(cac_cot):
            col = c0 + j
            _ghi_tieu_de(wt, col, ln, dv, ten_m, "số liệu thô từ file" if j == 0 else "")
            if ten_c:
                vals = tho[ten_c].to_numpy()
            else:
                vals = d["chu_ky"].to_numpy()
            for r in range(n_tho):
                wt.cell(row=HANG_DAU_SO_LIEU + r, column=col, value=float(vals[r]) if ten_c else int(vals[r]))
        cE, cI, cT = _cot(c0), _cot(c0 + 1), _cot(c0 + 2)
        cot_t += len(cac_cot)
        # ----- sheet XỬ LÝ: công thức -----
        if loai == "IT":
            vt = np.where(~d["nhieu"].to_numpy())[0]
            tt = d[xl.COT_T].to_numpy(dtype=float)
            t0 = float(tt[0]) if len(tt) else 0.0
            dich = (off - t0) if getattr(a, "noi_tiep", False) else 0.0
            if getattr(a, "noi_tiep", False) and len(tt):
                off += float(tt[-1]) - t0
            cx, cy = cot_x, cot_x + 1
            _ghi_tieu_de(wx, cx, "T", "h", ten_m, "T/3600" + (f"+{dich:.6g}" if dich else ""))
            _ghi_tieu_de(wx, cy, ten_m, "mA/cm2", ten_m, "i×1000×nhân/chia")
            for r, p in enumerate(vt):
                hr = HANG_DAU_SO_LIEU + r
                src = HANG_DAU_SO_LIEU + int(p)
                f_t = f"={_q(ten_tho)}!{cT}{src}/3600" + (f"+{dich:.10g}" if dich else "")
                wx.cell(row=hr, column=cx, value=f_t)
                wx.cell(row=hr, column=cy, value=f"={_q(ten_tho)}!{cI}{src}*1000*I_nhan/I_chia")
            n_d, nho = len(vt), {"cot_x": cx, "cot_y": cy}
            ten_x, ten_y = "T (h)", xl.NHAN_I
        else:
            if loai == "CV":
                ck = xl.chon_chu_ky(d, getattr(a, "chu_ky", None))
                vt = np.where(d["chu_ky"].to_numpy() == ck)[0]
            else:
                vt = np.arange(len(d))
            cx, cy = cot_x, cot_x + 1
            ln_y = m.get("nhan_hien_thi", ten_m)
            _ghi_tieu_de(wx, cx, "E", "V vs RHE", ln_y, "E+k·pH+Eref−i·Rs")
            _ghi_tieu_de(wx, cy, ln_y, "mA/cm2", ln_y, "i×1000×nhân/chia")
            for r, p in enumerate(vt):
                hr = HANG_DAU_SO_LIEU + r
                src = HANG_DAU_SO_LIEU + int(p)
                wx.cell(row=hr, column=cx, value=f"={_q(ten_tho)}!{cE}{src}+RHE_bat*(k_Nernst*pH_dd+E_ref)-{_q(ten_tho)}!{cI}{src}*R_s*iR_pct/100")
                wx.cell(row=hr, column=cy, value=f"={_q(ten_tho)}!{cI}{src}*1000*I_nhan/I_chia")
            n_d = len(vt)
            nho = {"cot_x": cx, "cot_y": cy}
            ten_x, ten_y = xl.NHAN_E, xl.NHAN_I
        cot_x += 2
        info.append({"muc": m, "cot_e": nho["cot_x"], "cot_j": nho["cot_y"], "hang_cua_vt": {int(p): HANG_DAU_SO_LIEU + r for r, p in enumerate(vt)}, "n": n_d})
        cap_bd.append((nho["cot_x"], nho["cot_y"], nho["cot_y"], n_d))
        mau.append(_hex(m["mau"]))
    _dau_trang(wt, cot_t - 2, nhan_hang)
    _dau_trang(wx, cot_x - 2, nhan_hang)
    if cap_bd and any(n for *_, n in cap_bd):
        try:
            _bieu_do(wx, cap_bd, 0, ten_x, ten_y, mau, f"{_cot(cot_x + 1)}2")
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) khong dung duoc bieu do cho sheet {ten_xl}: {e}")
    return info


def _sheet_eis(wb, nhom, a):
    wt = wb.create_sheet("Thô EIS")
    wx = wb.create_sheet("Xử lý EIS")
    nhan_hang = ["Long Name", "Units", "Comments", "F(x)="]
    ct = cx = 2
    cap, mau = [], []
    for m in nhom:
        tho, d = m["tho"], m["d"]
        f, zr, zi = (tho[c].to_numpy() for c in ("c1", "c2", "c3"))
        n = len(f)
        for j, (ln, dv, ten_c) in enumerate((("f", "Hz", "c1"), ("Z'", "Ohm", "c2"), ("Z'' (cột 3 file)", "Ohm", "c3"))):
            _ghi_tieu_de(wt, ct + j, ln, dv, m["nhan"], "số liệu thô từ file" if j == 0 else "")
            for r in range(n):
                wt.cell(row=HANG_DAU_SO_LIEU + r, column=ct + j, value=float(tho[ten_c].iloc[r]))
        cF, cR, cI = _cot(ct), _cot(ct + 1), _cot(ct + 2)
        ct += 3
        thu_tu = np.argsort(-f, kind="stable")           # xu_ly_eis sắp theo f giảm dần
        if not np.allclose(f[thu_tu], d["f (Hz)"].to_numpy(), rtol=0, atol=0):
            thu_tu = np.arange(n)
        cols = (("f", "Hz", "f_thô", lambda s: f"={_q('Thô EIS')}!{cF}{s}"),
                ("Z'", "Ohm", "Z'_thô", lambda s: f"={_q('Thô EIS')}!{cR}{s}"),
                ("-Z''", "Ohm", "−Z''_thô (đảo dấu cột 3)", lambda s: f"=-{_q('Thô EIS')}!{cI}{s}"),
                ("|Z|", "Ohm", "√(Z'² + Z''²)", lambda s: f"=SQRT({_q('Thô EIS')}!{cR}{s}^2+{_q('Thô EIS')}!{cI}{s}^2)"),
                ("pha", "độ", "DEGREES(ATAN2(Z', Z''))", lambda s: f"=DEGREES(ATAN2({_q('Thô EIS')}!{cR}{s},{_q('Thô EIS')}!{cI}{s}))"))
        for j, (ln, dv, fx, fn) in enumerate(cols):
            _ghi_tieu_de(wx, cx + j, ln, dv, m["nhan"], fx)
            for r, p in enumerate(thu_tu):
                wx.cell(row=HANG_DAU_SO_LIEU + r, column=cx + j, value=fn(HANG_DAU_SO_LIEU + int(p)))
        cap.append((cx + 1, cx + 2, cx + 2, n))
        mau.append(_hex(m["mau"]))
        cx += 5
    _dau_trang(wt, ct - 2, nhan_hang)
    _dau_trang(wx, cx - 2, nhan_hang)
    try:
        _bieu_do(wx, cap, 0, "Z' (Ω)", "-Z'' (Ω)", mau, f"{_cot(cx + 1)}2")
    except Exception as e:  # noqa: BLE001
        print(f"  (canh bao) khong dung duoc bieu do EIS: {e}")


def _sheet_tafel(wb, info, ten_xl, a):
    """Tafel bằng công thức: Log(J) = LOG10(|J|) trỏ về sheet 'Xử lý ...'; hệ số = SLOPE/INTERCEPT/RSQ; đường fit từ hệ số đó."""
    import xu_ly_dien_hoa as xl
    ws = wb.create_sheet("Tafel (công thức)")
    wt = wb.create_sheet("Tafel hệ số (công thức)")
    wt.append(["Mẫu", "Số điểm", "b (mV/dec) = SLOPE×1000", "a (V) = INTERCEPT", "R² = RSQ", "b app tính (mV/dec)", "Chênh lệch (mV/dec)", "Vùng chọn"])
    from openpyxl.styles import Alignment, Font, PatternFill
    for c in wt[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cot, cap, mau, kd = 2, [], [], []
    xs_n = []
    for i, it in enumerate(info):
        m = it["muc"]
        try:
            df_t, slope, a_s, b_i = xl.tafel_a(m["d"], a)
        except Exception as e:  # noqa: BLE001
            print(f"  (luu y) khong tinh duoc Tafel (cong thuc) cho {m['nhan']}: {e}")
            continue
        vt = df_t.attrs.get("vi_tri_dong_goc") or []
        hang = [it["hang_cua_vt"].get(p) for p in vt]
        if not vt or any(h is None for h in hang):
            continue
        n = len(hang)
        nh = m["nhan"]
        cE, cJ = _cot(it["cot_e"]), _cot(it["cot_j"])
        c_lj, c_e, c_xf, c_yf = cot, cot + 1, cot + 2, cot + 3
        _ghi_tieu_de(ws, c_lj, "Log(J)", "", nh, "LOG10(|J|)")
        _ghi_tieu_de(ws, c_e, nh, "V vs RHE", nh, "E (điểm dùng fit)")
        _ghi_tieu_de(ws, c_xf, "Log(J) fit", "", nh, "MIN / MAX của Log(J)")
        _ghi_tieu_de(ws, c_yf, nh + " fit", "V vs RHE", nh, "a + b×Log(J)")
        for r, h in enumerate(hang):
            hr = HANG_DAU_SO_LIEU + r
            ws.cell(row=hr, column=c_lj, value=f"=LOG10(ABS({_q(ten_xl)}!{_cot(it['cot_j'])}{h}))")
            ws.cell(row=hr, column=c_e, value=f"={_q(ten_xl)}!{cE}{h}")
        rng_x = f"{_cot(c_lj)}${HANG_DAU_SO_LIEU}:{_cot(c_lj)}${HANG_DAU + n}"
        rng_y = f"{_cot(c_e)}${HANG_DAU_SO_LIEU}:{_cot(c_e)}${HANG_DAU + n}"
        hr_t = i + 2
        wt.cell(row=hr_t, column=1, value=nh)
        wt.cell(row=hr_t, column=2, value=f"=COUNT({_q(ws.title)}!{rng_x})")
        wt.cell(row=hr_t, column=3, value=f"=SLOPE({_q(ws.title)}!{rng_y},{_q(ws.title)}!{rng_x})*1000")
        wt.cell(row=hr_t, column=4, value=f"=INTERCEPT({_q(ws.title)}!{rng_y},{_q(ws.title)}!{rng_x})")
        wt.cell(row=hr_t, column=5, value=f"=RSQ({_q(ws.title)}!{rng_y},{_q(ws.title)}!{rng_x})")
        wt.cell(row=hr_t, column=6, value=float(slope))
        wt.cell(row=hr_t, column=7, value=f"=C{hr_t}-F{hr_t}")
        theo_e = getattr(a, "tafel_e_min", None) is not None and getattr(a, "tafel_e_max", None) is not None
        wt.cell(row=hr_t, column=8, value=(f"E {min(a.tafel_e_min, a.tafel_e_max):g} - {max(a.tafel_e_min, a.tafel_e_max):g} V" if theo_e
                                           else f"|J| {float(getattr(a, 'tafel_min', 9)):g} - {float(getattr(a, 'tafel_max', 11)):g} mA/cm²"))
        ws.cell(row=HANG_DAU_SO_LIEU, column=c_xf, value=f"=MIN({rng_x})")
        ws.cell(row=HANG_DAU_SO_LIEU + 1, column=c_xf, value=f"=MAX({rng_x})")
        for r in (HANG_DAU_SO_LIEU, HANG_DAU_SO_LIEU + 1):
            ws.cell(row=r, column=c_yf, value=f"={_q(wt.title)}!$D${hr_t}+{_q(wt.title)}!$C${hr_t}/1000*{_cot(c_xf)}{r}")
        cap += [(c_lj, c_e, c_e, n), (c_xf, c_yf, c_yf, 2)]
        mau += [_hex(m["mau"])] * 2
        kd += [True, False]
        cot += 4
    for j, w in enumerate((26, 10, 24, 18, 12, 20, 18, 26), 1):
        wt.column_dimensions[_cot(j)].width = w
    for r in wt.iter_rows(min_row=2):
        for c in r[2:7]:
            c.number_format = "0.0000"
    _dau_trang(ws, cot - 2, ["Long Name", "Units", "Comments", "F(x)="])
    if cap:
        try:
            _bieu_do(ws, cap, 0, "Log(J)", xl.NHAN_POT, mau, f"{_cot(cot + 1)}2", kieu_diem=kd)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) khong dung duoc bieu do Tafel: {e}")


def _sheet_ecsa(wb, a):
    """ECSA bằng công thức từ bảng điểm app đã nội suy (Ja, Jc tại E lấy dòng): ΔJ = (Ja−Jc)/2; Cdl = SLOPE(ΔJ, v); R²; ECSA = Cdl/Cs."""
    import bao_cao
    diem, kq = bao_cao.LUU.get("ecsa_diem"), bao_cao.LUU.get("ecsa")
    if diem is None or kq is None or len(diem) == 0:
        return
    from openpyxl.styles import Alignment, Font, PatternFill
    ws = wb.create_sheet("ECSA (công thức)")
    ws.append(["File", "Chu kỳ", "Tốc độ quét (mV/s)", "v (V/s) = mV/s ÷ 1000", "Ja (mA/cm²) tại E lấy dòng", "Jc (mA/cm²) tại E lấy dòng", "ΔJ = (Ja − Jc)/2 (mA/cm²)"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    n = len(diem)
    for i, (_, r) in enumerate(diem.iterrows(), 2):
        ws.append([r["file"], int(r["chu_ky"]), float(r["toc_do_quet (mV/s)"]), f"=C{i}/1000", float(r["Ja (mA/cm2)"]), float(r["Jc (mA/cm2)"]), f"=(E{i}-F{i})/2"])
    k0 = n + 3
    k = kq.iloc[0]
    items = [("E lấy dòng (V vs RHE)", float(k["E_lay_dong (V vs RHE)"])),
             ("Cdl (mF/cm²) = SLOPE(ΔJ, v)", f"=SLOPE(G2:G{n + 1},D2:D{n + 1})"),
             ("R² = RSQ(ΔJ, v)", f"=RSQ(G2:G{n + 1},D2:D{n + 1})"),
             ("Cs (mF/cm²)", float(k["Cs (mF/cm2)"])),
             ("ECSA = Cdl / Cs", f"=B{k0 + 1}/B{k0 + 3}"),
             ("Cdl app tính (mF/cm²)", float(k["Cdl (mF/cm2)"])),
             ("Chênh lệch Cdl (công thức − app)", f"=B{k0 + 1}-B{k0 + 5}")]
    for j, (t, v) in enumerate(items):
        ws.cell(row=k0 + j, column=1, value=t).font = Font(bold=True)
        ws.cell(row=k0 + j, column=2, value=v)
    ws.cell(row=k0 + len(items) + 1, column=1, value="Ja, Jc là giá trị nội suy tuyến tính từ sheet 'ECSA_CV_DaTocDo' tại E lấy dòng (app tính); các ô còn lại là công thức.")
    for j, w in enumerate((34, 12, 18, 18, 24, 24, 24), 1):
        ws.column_dimensions[_cot(j)].width = w
    for r in ws.iter_rows(min_row=2):
        for c in r[3:]:
            if c.value is not None:
                c.number_format = "0.0000"


def them_vao(wb, a, ds):
    """Thêm các sheet: Thông số xử lý, Thô/Xử lý theo loại (công thức), Tafel (công thức), ECSA (công thức). Lỗi 1 phần không làm mất phần khác."""
    import xu_ly_dien_hoa as xl
    try:
        _sheet_thong_so(wb, a)
    except Exception as e:  # noqa: BLE001
        print(f"  (canh bao) khong tao duoc sheet Thong so xu ly: {e}")
        return
    muc = _nap_mau(a, ds)
    if getattr(a, "ecsa", False):
        cv = []
        for m in muc:
            if m["loai"] != "CV":
                continue
            m = dict(m)
            m["nhan_hien_thi"] = f"{xl.toc_do_quet(m['d']) * 1000:.0f} mV/s"
            m["nhan"] = m["nhan_hien_thi"]
            cv.append(m)
        if cv:
            try:
                _sheet_tho_xu_ly(wb, "Thô ECSA_CV", "ECSA_CV_DaTocDo", cv, a, "CV")
            except Exception as e:  # noqa: BLE001
                print(f"  (canh bao) khong tao duoc sheet ECSA_CV_DaTocDo: {e}")
        try:
            _sheet_ecsa(wb, a)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) khong tao duoc sheet ECSA (cong thuc): {e}")
        return
    for loai in ("CV", "LSV", "TAFEL", "IT"):
        nhom = [m for m in muc if m["loai"] == loai]
        if not nhom:
            continue
        ten_t, ten_x = f"Thô {loai}", f"Xử lý {loai}"
        try:
            info = _sheet_tho_xu_ly(wb, ten_t, ten_x, nhom, a, loai)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) khong tao duoc sheet {ten_x}: {e}")
            continue
        if loai == "TAFEL":
            try:
                _sheet_tafel(wb, info, ten_x, a)
            except Exception as e:  # noqa: BLE001
                print(f"  (canh bao) khong tao duoc sheet Tafel (cong thuc): {e}")
    nhom = [m for m in muc if m["loai"] == "EIS"]
    if nhom:
        try:
            _sheet_eis(wb, nhom, a)
        except Exception as e:  # noqa: BLE001
            print(f"  (canh bao) khong tao duoc sheet EIS (cong thuc): {e}")
