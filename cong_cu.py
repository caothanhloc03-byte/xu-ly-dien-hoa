# -*- coding: utf-8 -*-
"""
Các phép tính trên dữ liệu thô (tra cứu, Tafel, ECSA, thống kê...). Dùng bởi hoi_dap.py.
Mọi con số đều do code tính (xu_ly_dien_hoa.py), không cần AI hay Internet.
"""
import contextlib
import io
import os
import tempfile
from types import SimpleNamespace

import numpy as np

import xu_ly_dien_hoa as xl

# ====================== TIỆN ÍCH ======================
def _py(x):
    """Đổi numpy/pandas -> kiểu Python thuần để dump JSON."""
    import pandas as pd
    if isinstance(x, pd.DataFrame):
        return _py(x.to_dict("records"))
    if isinstance(x, dict):
        return {str(k): _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_py(v) for v in x]
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return round(v, 6) if np.isfinite(v) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def _cat_cua_so(g, bien, tu, den):
    col = xl.COT_E if bien == "E" else xl.COT_T
    if tu is not None:
        g = g[g[col] >= tu]
    if den is not None:
        g = g[g[col] <= den]
    return g


# ====================== NGỮ CẢNH + CÔNG CỤ ======================
class NguCanh:
    """Giữ danh sách file + thông số quy đổi, và cung cấp các công cụ để AI gọi."""

    def __init__(self, files, ph, eref, nhan_i, chia_i, loai=None, r_s=0.0, ir_pct=100.0, khong_rhe=False):
        self.files = list(files)  # [(duong_dan, nhan), ...]
        self.ph, self.eref, self.nhan_i, self.chia_i = ph, eref, nhan_i, chia_i
        self.a = SimpleNamespace(ph=ph, eref=eref, nhan_i=nhan_i, chia_i=chia_i, loai=loai, chu_ky=None,
                                 mau=xl.MAU, mau_theo_chu_ky=False, nhan=[n for _, n in self.files],
                                 mau_file=[], chong=False, noi_tiep=False, tafel_min=9.0, tafel_max=11.0, r_s=r_s, ir_phan_tram=ir_pct, khong_rhe=khong_rhe)
        self._cache = {}

    # ---- tra cứu file ----
    def tim(self, ref):
        n = len(self.files)
        if isinstance(ref, (int, float)) and not isinstance(ref, bool):
            k = int(ref) - 1
        else:
            s = str(ref).strip()
            if s.isdigit():
                k = int(s) - 1
            else:
                low = s.lower()
                kq = [i for i, (p, nh) in enumerate(self.files) if nh.lower() == low or os.path.basename(p).lower() == low]
                if not kq:
                    kq = [i for i, (p, nh) in enumerate(self.files) if low in nh.lower() or low in os.path.basename(p).lower()]
                if len(kq) != 1:
                    raise ValueError(f"Không xác định được file '{ref}'. Hãy gọi liet_ke_file và dùng số thứ tự.")
                k = kq[0]
        if not 0 <= k < n:
            raise ValueError(f"Số thứ tự file {k + 1} không tồn tại (có {n} file).")
        return k

    def lay(self, ref):
        k = self.tim(ref)
        if k not in self._cache:
            self._cache[k] = xl.nap_muc(self.files[k][0], self.a, k)
        return k, self._cache[k]

    def _cv_lsv(self, ref):
        k, m = self.lay(ref)
        if m["loai"] not in ("CV", "LSV"):
            raise ValueError(f"File {k + 1} là {m['loai']}, công cụ này chỉ dùng cho CV/LSV.")
        return k, m

    def _nhanh(self, m, chu_ky=None):
        """Dữ liệu CV (chu kỳ chỉ định hoặc cuối) / LSV (toàn bộ)."""
        d = m["d"]
        if m["loai"] == "CV":
            ck = xl.chon_chu_ky(d, int(chu_ky) if chu_ky else None)
            d = d[d["chu_ky"] == ck]
        return d

    # ---- công cụ ----
    def liet_ke_file(self):
        kq = []
        for k, (p, nh) in enumerate(self.files):
            info = {"stt": k + 1, "nhan": nh, "file": os.path.basename(p)}
            try:
                _, m = self.lay(k + 1)
                d, loai = m["d"], m["loai"]
                info.update(loai=loai, so_diem=len(d))
                if loai in ("CV", "LSV"):
                    info.update(E_min_V=d[xl.COT_E].min(), E_max_V=d[xl.COT_E].max(),
                                I_min_mA_cm2=d[xl.COT_I].min(), I_max_mA_cm2=d[xl.COT_I].max(),
                                so_chu_ky=int(d["chu_ky"].max()), toc_do_quet_mV_s=xl.toc_do_quet(d) * 1000)
                elif loai == "IT":
                    h = d[~d["nhieu"]]
                    info.update(thoi_gian_h=h[xl.COT_T].max() - h[xl.COT_T].min(), E_giu_V=h[xl.COT_E].median(),
                                I_trung_binh_mA_cm2=h[xl.COT_I].mean())
                else:
                    info.update(f_max_Hz=d["f (Hz)"].max(), f_min_Hz=d["f (Hz)"].min())
            except Exception as e:
                info["loi"] = str(e)
            kq.append(info)
        return _py(kq)

    def thong_so(self, file):
        k, m = self.lay(file)
        d, loai = m["d"], m["loai"]
        if loai in ("CV", "LSV"):
            return _py({"loai": loai, "toc_do_quet_mV_s": xl.toc_do_quet(d) * 1000,
                        "bang_thong_so": xl.thong_so_cv_lsv(d, loai)})
        if loai == "IT":
            return _py({"loai": loai, **xl.thong_so_it(d).iloc[0].to_dict()})
        return _py({"loai": loai, **xl.thong_so_eis(d).iloc[0].to_dict()})

    def dong_tai_the(self, file, E_V_vs_RHE, chu_ky=None):
        k, m = self._cv_lsv(file)
        E0 = float(E_V_vs_RHE)
        d = self._nhanh(m, chu_ky)
        if not d[xl.COT_E].min() <= E0 <= d[xl.COT_E].max():
            return {"loi": f"E={E0} V nằm ngoài khoảng dữ liệu {d[xl.COT_E].min():.4f} ~ {d[xl.COT_E].max():.4f} V vs RHE"}
        if m["loai"] == "LSV":
            s = d.sort_values(xl.COT_E)
            return _py({"E_V_vs_RHE": E0, "I_mA_cm2": float(np.interp(E0, s[xl.COT_E], s[xl.COT_I]))})
        ja, jc = xl.noi_suy_dong(d, E0)
        return _py({"E_V_vs_RHE": E0, "I_anodic_mA_cm2": ja, "I_cathodic_mA_cm2": jc, "chu_ky": int(d["chu_ky"].iloc[0])})

    def the_tai_dong(self, file, I_mA_cm2, E_can_bang_V=None, chu_ky=None):
        k, m = self._cv_lsv(file)
        tg = float(I_mA_cm2)
        g = self._nhanh(m, chu_ky)
        if m["loai"] == "CV":
            g = g[g["huong_quet"] == ("anodic" if tg > 0 else "cathodic")]
        E, J = g[xl.COT_E].to_numpy(), g[xl.COT_I].to_numpy()
        if len(E) < 2:
            return {"loi": "Không đủ dữ liệu"}
        df = J - tg
        cat = np.where((df[:-1] * df[1:] <= 0) & ~((df[:-1] == 0) & (df[1:] == 0)))[0]
        if len(cat) == 0:
            return {"loi": f"Dòng không đạt {tg} mA/cm2 (I chạy từ {J.min():.4f} đến {J.max():.4f} mA/cm2)"}
        i = int(cat[-1])        # điểm cắt CUỐI CÙNG: bỏ qua pic oxi hóa nhỏ ở điện thế thấp, lấy nhánh OER/HER
        Ec = E[i] if J[i + 1] == J[i] else E[i] + (tg - J[i]) * (E[i + 1] - E[i]) / (J[i + 1] - J[i])
        kq = {"I_mA_cm2": tg, "E_V_vs_RHE": Ec, "ghi_chu": "điểm cắt cuối cùng (nội suy tuyến tính)"}
        if E_can_bang_V is not None:
            kq["qua_the_mV"] = (Ec - float(E_can_bang_V)) * 1000
        return _py(kq)

    def tafel(self, file, I_min_mA_cm2=9.0, I_max_mA_cm2=11.0):
        k, m = self.lay(file)
        vmin, vmax = float(I_min_mA_cm2), float(I_max_mA_cm2)
        if not 0 < vmin < vmax:
            return {"loi": "Cần 0 < I_min < I_max"}
        df_t, slope, a_s, b = xl.xu_ly_tafel(m["d"], vmin, vmax)       # không cảnh báo ở đây; tự kiểm tra bên dưới
        x, y = df_t["Log(J)"].to_numpy(), df_t["Potential (V vs RHE)"].to_numpy()
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - np.sum((y - (a_s * x + b)) ** 2) / ss_tot if ss_tot > 0 else None
        return _py({"he_so_Tafel_mV_dec": slope, "so_diem": len(df_t), "R2": r2, "vung_dong_mA_cm2": [vmin, vmax]})

    def ecsa(self, files=None, E_V_vs_RHE=None, Cs_mF_cm2=0.040):
        if files:
            idx = [self.tim(f) for f in files]
        else:
            idx = [k for k in range(len(self.files)) if self.lay(k + 1)[1]["loai"] == "CV"]
        if len(idx) < 2:
            return {"loi": "ECSA cần ít nhất 2 file CV ở 2 tốc độ quét khác nhau"}
        paths = [self.files[k][0] for k in idx]
        e = None if E_V_vs_RHE in (None, "") else float(E_V_vs_RHE)
        cb = xl.canh_bao
        if cb:
            cb.reset()
            cb.dat_im_lang(True)
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
                b, he_so, tung, r2, e_chon, kq = xl.tinh_ecsa(paths, self.a, e, float(Cs_mF_cm2), None,
                                                              os.path.join(tmp, "x"), ve=False)
            canh = cb.dong_chu() if cb else []
        finally:
            if cb:
                cb.dat_im_lang(False)
        return _py({"E_lay_dong_V_vs_RHE": e_chon, "Cdl_mF_cm2": he_so, "R2": r2, "Cs_mF_cm2": float(Cs_mF_cm2),
                    "ECSA_cm2": kq["ECSA (cm2_ECSA / cm2_hinh_hoc)"].iloc[0], "bang_diem": b, "canh_bao": canh})

    def thong_ke_doan(self, file, bien, tu=None, den=None):
        k, m = self.lay(file)
        bien = str(bien).upper()
        if m["loai"] in ("CV", "LSV") and bien == "E":
            g = self._nhanh(m)
            g = _cat_cua_so(g, "E", None if tu is None else float(tu), None if den is None else float(den))
            if len(g) < 2:
                return {"loi": "Không có dữ liệu trong đoạn này"}
            E, J = g[xl.COT_E].to_numpy(), g[xl.COT_I].to_numpy()
            return _py({"so_diem": len(g), "I_max_mA_cm2": J.max(), "E_tai_I_max_V": E[J.argmax()],
                        "I_min_mA_cm2": J.min(), "E_tai_I_min_V": E[J.argmin()], "I_trung_binh_mA_cm2": J.mean(),
                        "dien_tich_I_dE_mA_V_cm2": float(np.sum(0.5 * (J[1:] + J[:-1]) * np.diff(E)))})
        if m["loai"] == "IT" and bien == "T":
            g = m["d"][~m["d"]["nhieu"]]
            g = _cat_cua_so(g, "T", None if tu is None else float(tu), None if den is None else float(den))
            if len(g) < 2:
                return {"loi": "Không có dữ liệu trong đoạn này"}
            J = g[xl.COT_I].to_numpy()
            return _py({"so_diem": len(g), "I_trung_binh_mA_cm2": J.mean(), "I_dau_mA_cm2": J[0],
                        "I_cuoi_mA_cm2": J[-1], "I_max_mA_cm2": J.max(), "I_min_mA_cm2": J.min()})
        return {"loi": f"Không hỗ trợ bien='{bien}' cho file loại {m['loai']} (CV/LSV dùng bien='E', IT dùng bien='T' tính bằng giờ)"}
