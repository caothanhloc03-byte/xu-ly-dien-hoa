# -*- coding: utf-8 -*-
"""
Cảnh báo dữ liệu thông minh.

App tự phát hiện những vấn đề thường gặp (R² ECSA thấp, chu kỳ cuối bị cụt, điểm lệch khỏi đường thẳng,
dòng điện dung lẫn dòng Faraday, Tafel kém tuyến tính, đơn vị đáng ngờ...) và báo bằng tiếng Việt kèm gợi ý.

Cách dùng: các hàm kiem_tra_* in ra stdout (dòng bắt đầu bằng "[CẢNH BÁO" / "[LƯU Ý" / "[GỢI Ý]")
và lưu vào DANH_SACH để báo cáo Excel dùng lại.
"""
import numpy as np

NANG = "nang"        # nghiêm trọng: kết quả có thể sai
CANH_BAO = "canh_bao"
LUU_Y = "luu_y"
GOI_Y = "goi_y"

TIEN_TO = {NANG: "[CẢNH BÁO NẶNG]", CANH_BAO: "[CẢNH BÁO]", LUU_Y: "[LƯU Ý]", GOI_Y: "[GỢI Ý]"}

DANH_SACH = []   # [{"muc_do":..., "noi_dung":..., "doi_tuong":...}]
_IM_LANG = False


def reset():
    DANH_SACH.clear()


def dat_im_lang(co=True):
    """Im lặng = vẫn ghi nhận cảnh báo nhưng không in (tránh in trùng khi chạy 2 tiến trình)."""
    global _IM_LANG
    _IM_LANG = bool(co)


def them(muc_do, noi_dung, doi_tuong=""):
    for c in DANH_SACH:
        if c["muc_do"] == muc_do and c["noi_dung"] == noi_dung and c["doi_tuong"] == doi_tuong:
            return
    DANH_SACH.append({"muc_do": muc_do, "noi_dung": noi_dung, "doi_tuong": doi_tuong})
    if not _IM_LANG:
        dau = f"{doi_tuong}: " if doi_tuong else ""
        print(f"{TIEN_TO[muc_do]} {dau}{noi_dung}")


def dem_canh_bao():
    return sum(1 for c in DANH_SACH if c["muc_do"] in (NANG, CANH_BAO))


def dong_chu(muc_do=None):
    """Danh sách chuỗi dễ đọc (dùng cho hỏi đáp / báo cáo)."""
    kq = []
    for c in DANH_SACH:
        if muc_do and c["muc_do"] != muc_do:
            continue
        dau = f"{c['doi_tuong']}: " if c["doi_tuong"] else ""
        kq.append(f"{TIEN_TO[c['muc_do']]} {dau}{c['noi_dung']}")
    return kq


def _r2(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3:
        return float("nan")
    a, b = np.polyfit(x, y, 1)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return 1 - np.sum((y - (a * x + b)) ** 2) / ss_tot if ss_tot > 0 else float("nan")


# ====================== TỪNG FILE ======================
def kiem_tra_muc(m, a=None):
    """m: dict từ xu_ly_dien_hoa.nap_muc (loai, d, nhan)."""
    ten, loai, d = m.get("nhan", ""), m["loai"], m["d"]
    n = len(d)
    if loai in ("CV", "LSV"):
        _kt_cv_lsv(ten, loai, d)
    elif loai == "IT":
        _kt_it(ten, d)
    elif loai == "EIS":
        _kt_eis(ten, d)
    if n < 20:
        them(CANH_BAO, f"chỉ có {n} điểm dữ liệu, quá ít để xử lý đáng tin cậy.", ten)


def _kt_cv_lsv(ten, loai, d):
    E, I = d["RHE (V)"].to_numpy(), d["I (mA/cm2)"].to_numpy()
    if len(E) and np.isfinite(E).all():
        if E.max() - E.min() < 0.03:
            them(CANH_BAO, f"khoảng điện thế rất hẹp ({E.min():.3f} → {E.max():.3f} V). Kiểm tra lại file/loại phép đo.", ten)
        if E.min() < -1.5 or E.max() > 3.5:
            them(CANH_BAO, f"điện thế sau quy đổi nằm ngoài vùng thường gặp ({E.min():.2f} → {E.max():.2f} V vs RHE). "
                           "Kiểm tra lại pH và điện thế điện cực so sánh (Eref).", ten)
    if len(I):
        imax = float(np.nanmax(np.abs(I)))
        if imax > 5000:
            them(CANH_BAO, f"mật độ dòng lớn bất thường (tối đa {imax:.0f} mA/cm²). Kiểm tra hệ số nhân/chia dòng (diện tích điện cực).", ten)
        elif imax < 1e-4:
            them(CANH_BAO, f"mật độ dòng rất nhỏ (tối đa {imax:.2g} mA/cm²). Kiểm tra đơn vị dòng và hệ số nhân/chia.", ten)
    if loai == "CV" and "chu_ky" in d:
        n = d.groupby("chu_ky").size()
        cks = list(n.index)
        if len(cks) >= 2:
            if n.loc[cks[-1]] < 0.6 * n.loc[cks[:-1]].median():
                them(CANH_BAO, f"chu kỳ cuối bị cụt (phép đo dừng giữa chừng). App tự dùng chu kỳ {int(cks[-2])} thay vì {int(cks[-1])}.", ten)
                cks = cks[:-1]
            if len(cks) >= 2:
                a_, b_ = d[d["chu_ky"] == cks[-1]]["I (mA/cm2)"].to_numpy(), d[d["chu_ky"] == cks[-2]]["I (mA/cm2)"].to_numpy()
                pa, pb = np.ptp(a_), np.ptp(b_)
                if pa > 0 and abs(pa - pb) / pa > 0.2:
                    them(LUU_Y, f"đường cong chưa ổn định (biên độ dòng giữa chu kỳ {int(cks[-2])} và {int(cks[-1])} lệch "
                                f"{abs(pa - pb) / pa * 100:.0f}%). Nên chạy thêm chu kỳ cho đến khi các chu kỳ trùng nhau.", ten)
        else:
            them(LUU_Y, "chỉ có 1 chu kỳ. Chu kỳ đầu thường chưa ổn định; nên chạy nhiều chu kỳ và dùng chu kỳ cuối.", ten)


def _kt_it(ten, d):
    if "nhieu" in d:
        tl = float(d["nhieu"].mean())
        if tl > 0.5:
            them(CANH_BAO, f"{tl * 100:.0f}% điểm bị coi là nhiễu (điện thế dao động hoặc mới đổi). Kiểm tra điện thế giữ không đổi.", ten)
        h = d[~d["nhieu"]]
        if len(h) >= 20:
            I = h["I (mA/cm2)"].to_numpy()
            if np.nanmin(I) < 0 < np.nanmax(I):
                them(LUU_Y, "dòng đổi dấu trong lúc đo (có cả giá trị âm và dương).", ten)


def _kt_eis(ten, d):
    zr = d["Z' (ohm)"].to_numpy()
    f = d["f (Hz)"].to_numpy()
    if (zr < 0).any():
        them(LUU_Y, "có giá trị Z' âm (thường do cảm kháng ở tần số cao). Nên kiểm tra dây dẫn/cáp.", ten)
    if len(f) > 3 and f.max() / max(f.min(), 1e-12) < 100:
        them(LUU_Y, f"dải tần số hẹp ({f.min():.3g} → {f.max():.3g} Hz).", ten)


# ====================== ECSA ======================
def kiem_tra_ecsa(b, he_so, tung, r2, e_chon, cac=None):
    """b: DataFrame điểm ECSA; cac: [(g_df, toc_do_mV_s, ten_file)] để gợi ý điện thế tốt hơn."""
    v = b["toc_do_quet (mV/s)"].to_numpy()
    y = b["(Ja-Jc)/2 (mA/cm2)"].to_numpy()
    n = len(b)
    if n < 4:
        them(LUU_Y, f"chỉ có {n} tốc độ quét. Nên dùng ít nhất 5 tốc độ để R² có ý nghĩa.", "ECSA")
    if v.max() / max(v.min(), 1e-9) < 3:
        them(CANH_BAO, "dải tốc độ quét hẹp (tỉ lệ lớn nhất/nhỏ nhất < 3), đường fit kém tin cậy.", "ECSA")
    if np.isfinite(r2):
        if r2 < 0.90:
            them(NANG, f"R² = {r2:.3f} rất thấp, giá trị Cdl/ECSA không đáng tin.", "ECSA")
        elif r2 < 0.98:
            them(CANH_BAO, f"R² = {r2:.3f} thấp (thường cần ≥ 0.98 cho đường Cdl).", "ECSA")
    if he_so <= 0:
        them(NANG, "hệ số góc (Cdl) âm hoặc bằng 0: dòng không tăng theo tốc độ quét.", "ECSA")
    if np.max(np.abs(y)) > 0 and abs(tung) > 0.2 * np.max(np.abs(y)):
        them(LUU_Y, f"đường fit không đi qua gốc tọa độ (hệ số chặn {tung:.3g} mA/cm²), có thể lẫn dòng Faraday.", "ECSA")
    if (y > 0).all() and n >= 3:
        mu = np.polyfit(np.log(v), np.log(y), 1)[0]
        if not 0.9 <= mu <= 1.1:
            them(CANH_BAO, f"dòng không tỉ lệ thuận với tốc độ quét (số mũ ≈ {mu:.2f}, lý tưởng ≈ 1). "
                           "Có thể lẫn dòng Faraday/khuếch tán hoặc điện thế lấy dòng không nằm trong vùng điện dung.", "ECSA")
    if "Ja (mA/cm2)" in b and "Jc (mA/cm2)" in b:
        ja, jc = b["Ja (mA/cm2)"].to_numpy(), b["Jc (mA/cm2)"].to_numpy()
        tong = np.abs(ja + jc).mean()
        rong = np.abs(ja - jc).mean()
        if rong > 0 and tong / rong > 0.5:
            them(CANH_BAO, f"Ja và Jc không đối xứng quanh 0 (lệch {tong / rong * 100:.0f}% so với độ rộng vòng). "
                           f"Điện thế lấy dòng {e_chon:.3f} V có thể nằm trong vùng phản ứng Faraday; hãy chọn điện thế khác ở ô 'ECSA E'.", "ECSA")
    # điểm lệch: bỏ từng điểm xem R² có tăng đáng kể không
    if n >= 5 and np.isfinite(r2) and r2 < 0.995:
        tot = None
        for i in range(n):
            m = np.arange(n) != i
            r_bo = _r2(v[m], y[m])
            if np.isfinite(r_bo) and r_bo - r2 > 0.02 and (tot is None or r_bo > tot[1]):
                tot = (i, r_bo)
        if tot:
            i, r_bo = tot
            them(GOI_Y, f"điểm {v[i]:.0f} mV/s lệch khỏi đường thẳng; nếu bỏ điểm này R² tăng từ {r2:.3f} lên {r_bo:.3f}. "
                        "Hãy xem lại đường CV ở tốc độ đó (có thể chưa ổn định hoặc đo lỗi).", "ECSA")
    if cac and np.isfinite(r2) and r2 < 0.99:
        goi = goi_y_dien_the(cac, e_chon)
        if goi:
            them(GOI_Y, f"thử điện thế lấy dòng {goi['E']:.3f} V (vs RHE): R² ≈ {goi['r2']:.4f} "
                        f"(hiện tại {e_chon:.3f} V cho R² = {r2:.4f}). Điền giá trị này vào ô 'ECSA E' rồi chạy lại.", "ECSA")


def goi_y_dien_the(cac, e_hien_tai, so_diem=41):
    """Quét điện thế trong vùng chung, chọn điện thế cho R² cao nhất và Ja/Jc đối xứng."""
    import xu_ly_dien_hoa as xl
    try:
        lo = max(g["RHE (V)"].min() for g, _, _ in cac)
        hi = min(g["RHE (V)"].max() for g, _, _ in cac)
        if hi - lo < 0.02:
            return None
        ung_vien = []
        for e in np.linspace(lo + 0.02 * (hi - lo), hi - 0.02 * (hi - lo), so_diem):
            v, y, ja_, jc_ = [], [], [], []
            for g, vr, _ in cac:
                ja, jc = xl.noi_suy_dong(g, e)
                v.append(vr / 1000.0)
                y.append((ja - jc) / 2)
                ja_.append(ja)
                jc_.append(jc)
            r = _r2(v, y)
            rong = np.abs(np.array(ja_) - np.array(jc_)).mean()
            lech = (np.abs(np.array(ja_) + np.array(jc_)).mean() / rong) if rong > 0 else 9
            if np.isfinite(r) and np.polyfit(v, y, 1)[0] > 0 and lech < 0.5:
                ung_vien.append((r, float(e)))
        if not ung_vien:
            return None
        r, e = max(ung_vien)
        if abs(e - e_hien_tai) < 0.01:
            return None
        return {"E": e, "r2": r}
    except Exception:
        return None


# ====================== TAFEL ======================
def kiem_tra_tafel(df_t, slope, v_min, v_max, ten=""):
    n = len(df_t)
    if n < 5:
        them(CANH_BAO, f"chỉ có {n} điểm trong vùng Tafel, kết quả kém tin cậy.", ten)
    I = np.abs(df_t["I (mA/cm2)"].to_numpy())
    if n and (I.min() < v_min * 0.999 or I.max() > v_max * 1.001):
        them(CANH_BAO, f"dòng không có đủ điểm trong vùng {v_min:g}–{v_max:g} mA/cm²; app đã lấy {n} điểm gần giá trị giữa vùng. "
                       "Hãy chỉnh lại vùng dòng Tafel cho phù hợp.", ten)
    r2 = _r2(df_t["Log(J)"], df_t["Potential (V vs RHE)"])
    if np.isfinite(r2) and r2 < 0.98:
        them(CANH_BAO, f"R² của đường Tafel = {r2:.3f} (thấp); vùng đã chọn có thể không tuyến tính.", ten)
    if abs(slope) > 500:
        them(CANH_BAO, f"hệ số Tafel {slope:.0f} mV/dec rất lớn, thường do vùng chọn chưa đúng hoặc dòng bị hạn chế bởi chuyển khối/iR.", ten)
    elif abs(slope) < 20:
        them(LUU_Y, f"hệ số Tafel {slope:.0f} mV/dec rất nhỏ, nên kiểm tra lại dữ liệu.", ten)
