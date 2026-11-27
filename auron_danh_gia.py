# -*- coding: utf-8 -*-
"""AURON đánh giá dữ liệu: sau khi app phân tích/vẽ xong, tạo một "sự kiện" (nhận xét bằng chữ, số liệu do code tính) để cửa sổ AURON hiển thị.

Nhận xét viết bằng quy tắc (không dùng mô hình AI) nên số liệu luôn khớp với kết quả của app. Ngưỡng ghi "(tham khảo)" là kiến thức chung trong điện hóa,
không phải ngưỡng bắt buộc. AURON (khi bật bộ não) còn dùng sự kiện gần nhất làm ngữ cảnh để giải thích thêm.
Giao tiếp app → AURON: file JSON trong thư mục tạm (app ghi, máy chủ cục bộ của AURON đọc qua /su_kien). Lõi không cần tkinter nên kiểm thử được.
"""
import json
import math
import os
import tempfile
import threading
import time

_KHOA = threading.Lock()
TOI_DA = 60


def duong_dan_file():
    return os.environ.get("ECHEM_AURON_SU_KIEN") or os.path.join(tempfile.gettempdir(), "echem_auron_su_kien.json")


# ====================== FILE SỰ KIỆN ======================
def _doc_tat_ca(p=None):
    try:
        with open(p or duong_dan_file(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def ghi_su_kien(ev, p=None):
    """Thêm một sự kiện (dict: nguon, tieu_de, mood, tom_tat, chi_tiet). Trả về id."""
    p = p or duong_dan_file()
    with _KHOA:
        ds = _doc_tat_ca(p)
        if ds and ds[-1].get("nguon") == ev.get("nguon") and ds[-1].get("chi_tiet") == ev.get("chi_tiet"):
            return ds[-1]["id"]                         # cùng nhận xét như lần trước (vd bấm lại cùng một kết quả): không lặp
        ev = dict(ev)
        ev["id"] = (max([e.get("id", 0) for e in ds]) if ds else int(time.time())) + 1
        ev["luc"] = time.strftime("%H:%M:%S")
        ev["epoch"] = time.time()
        ds = (ds + [ev])[-TOI_DA:]
        tam = p + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(ds, f, ensure_ascii=False)
        os.replace(tam, p)
    return ev["id"]


def doc_su_kien(sau=0, p=None):
    """Các sự kiện có id > sau."""
    return [e for e in _doc_tat_ca(p) if e.get("id", 0) > sau]


# ====================== TIỆN ÍCH ======================
def _co(x):
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _f(x, nd=0):
    return "—" if not _co(x) else f"{float(x):.{nd}f}"


def _cat(s, n=170):
    s = str(s).strip().replace("\n", " ")
    return s if len(s) <= n else s[:n - 1] + "…"


def _canh_bao_log(log):
    """Các dòng [CẢNH BÁO...] trong nhật ký chạy → (số lượng, vài dòng đầu)."""
    ds = [d.strip() for d in str(log or "").splitlines() if d.startswith("[CẢNH BÁO")]
    return len(ds), [_cat(d) for d in ds[:3]]


def _hoan_thien(nguon, tieu_de, mood, tom_tat, dong, log_cb=None):
    n, vai = log_cb if log_cb else (0, [])
    if n:
        dong = list(dong) + [f"Cảnh báo của app: {n} mục, ví dụ:"] + ["  • " + v for v in vai] + (["  (xem đủ ở nhật ký chạy)"] if n > len(vai) else [])
    return dict(nguon=nguon, tieu_de=tieu_de, mood=mood, tom_tat=tom_tat, chi_tiet="\n".join(dong))


# ====================== CV / LSV: SO SÁNH CÁC MẪU ======================
def tu_so_sanh(df, info):
    """df, info từ so_sanh.tong_hop. → (mood, tom_tat, [dòng]) hoặc None nếu không có gì để nói."""
    if df is None or len(df) == 0:
        return None
    cot = info.get("cot_hang", "")
    ds_j = info.get("ds_j") or [10.0]
    dang_eta = cot.startswith("η")
    don_vi = "mV" if dang_eta else "V"
    hang = [r for _, r in df.iterrows() if _co(r.get(cot))]
    dong, canh = [], []
    chieu = str(df.iloc[0].get("Chiều", ""))
    if len(hang) == 0:
        return "confused", "Chưa đọc được điện thế tại mật độ dòng mục tiêu của các mẫu CV/LSV.", \
            ["Không có mẫu CV/LSV nào đạt mật độ dòng mục tiêu: kiểm tra khoảng điện thế, mật độ dòng mục tiêu (ô 'i mục tiêu') và hệ số nhân/chia dòng."]
    hang.sort(key=lambda r: float(r[cot]))
    tot = hang[0]
    nhan = lambda r: str(r["Nhãn"])  # noqa: E731
    tieu = f"η tại {ds_j[0]:g} mA/cm²" if dang_eta else f"E tại {ds_j[0]:g} mA/cm²"
    if len(hang) == 1:
        dong.append(f"Chỉ có 1 mẫu CV/LSV ({nhan(tot)}): {tieu} = {_f(tot[cot], 0 if dang_eta else 3)} {don_vi}. Chưa so sánh được; nên có thêm mẫu nền "
                    "(không xúc tác) và chất chuẩn (Pt/C hoặc RuO₂/IrO₂) đo cùng điều kiện.")
        mood, tom = "neutral", f"Mẫu {nhan(tot)} có {tieu} = {_f(tot[cot], 0 if dang_eta else 3)} {don_vi}; cần thêm mẫu để so sánh."
    else:
        thu2 = hang[1]
        kc = float(thu2[cot]) - float(tot[cot])
        dong.append(f"So sánh {len(hang)} mẫu CV/LSV ({chieu}). Tốt nhất: {nhan(tot)} với {tieu} = {_f(tot[cot], 0 if dang_eta else 3)} {don_vi}, "
                    f"thấp hơn mẫu đứng thứ hai ({nhan(thu2)}) {_f(kc, 0 if dang_eta else 3)} {don_vi}.")
        dong.append("Xếp hạng: " + " > ".join(f"{nhan(r)} ({_f(r[cot], 0 if dang_eta else 3)})" for r in hang) + f"  [{don_vi}, càng thấp càng tốt]")
        if dang_eta and kc < 10:
            canh.append(f"Chênh lệch giữa hai mẫu đầu chỉ {kc:.0f} mV, có thể nằm trong sai số lặp lại: nên đo lặp vài lần trước khi kết luận.")
        mood = "happy" if (not dang_eta or kc >= 10) else "thinking"
        tom = f"{nhan(tot)} tốt nhất với {tieu} = {_f(tot[cot], 0 if dang_eta else 3)} {don_vi}, hơn {nhan(thu2)} {_f(kc, 0 if dang_eta else 3)} {don_vi}."
    if dang_eta:
        bat_thuong = [nhan(r) for r in hang if not -50 <= float(r[cot]) <= 900]
        if bat_thuong:
            canh.append("η bất thường (ngoài −50…900 mV) ở: " + ", ".join(bat_thuong) + ". Kiểm tra pH, Eref, E cân bằng và hệ số nhân/chia dòng.")
            mood = "confused"
    tafel = [(nhan(r), r.get("Tafel (mV/dec)")) for _, r in df.iterrows()]
    co_tafel = [(n, float(v)) for n, v in tafel if _co(v)]
    if co_tafel:
        dong.append("Độ dốc Tafel (mV/dec): " + "; ".join(f"{n} = {v:.0f}" for n, v in co_tafel) +
                    ". Cùng điều kiện, b nhỏ hơn thường là động học thuận lợi hơn; chỉ tin khi vùng fit đủ rộng (≥ 0,3 decade) và R² cao.")
        if len(co_tafel) >= 2 and max(v for _, v in co_tafel) - min(v for _, v in co_tafel) < 10:
            dong.append("Độ dốc Tafel của các mẫu gần như bằng nhau (chênh < 10 mV/dec): khác biệt hoạt tính chủ yếu nằm ở lượng/độ đặt tâm hoạt động chứ chưa chắc ở cơ chế.")
        la = [n for n, v in co_tafel if not 20 <= v <= 300]
        if la:
            canh.append("Tafel ngoài 20–300 mV/dec (tham khảo) ở: " + ", ".join(la) + ": thường do vùng fit quá hẹp hoặc còn iR/khuếch tán; xem lại vùng dòng Tafel.")
        if len(co_tafel) >= 2 and len(hang) >= 2:
            tot_tafel = min(co_tafel, key=lambda x: x[1])[0]
            if tot_tafel != nhan(tot):
                canh.append(f"Xếp hạng theo η ({nhan(tot)}) và theo Tafel ({tot_tafel}) không trùng: kết luận về động học nên thận trọng.")
    else:
        dong.append("Chưa có độ dốc Tafel cho các mẫu này (cần vùng dòng phù hợp hoặc chạy Tafel).")
    for c in df.columns:
        if str(c).startswith("TOF") or str(c).startswith("Hoạt độ khối"):
            dong.append("Đã có " + str(c).split(" tại")[0] + " trong bảng so sánh.")
            break
    if canh:
        dong.append("Lưu ý:")
        dong += ["  • " + c for c in canh]
        if mood == "happy":
            mood = "thinking"
    return mood, tom, dong


# ====================== IT / EIS ======================
def tu_it(ds_it):
    """ds_it: [(nhãn, dict thong_so_it)]."""
    if not ds_it:
        return None
    dong, mood, tom = [], "happy", ""
    for n, r in ds_it:
        giu, sg, th, tb = r.get("giu_dong (%)"), r.get("suy_giam (%)"), r.get("thoi_gian (h)"), r.get("toc_do_suy_giam (%/h)")
        nx = ("rất ổn định" if _co(giu) and giu >= 95 else "ổn định" if _co(giu) and giu >= 90 else "suy giảm vừa" if _co(giu) and giu >= 70
              else "suy giảm mạnh" if _co(giu) else "chưa đánh giá được")
        dong.append(f"{n}: giữ {_f(giu, 1)} % dòng sau {_f(th, 1)} h (suy giảm {_f(sg, 1)} %, tốc độ {_f(tb, 2)} %/h) → {nx} (ngưỡng tham khảo: ≥ 90 % là tốt).")
        if _co(th) and th < 10:
            dong.append(f"   Lưu ý: {n} chỉ đo {_f(th, 1)} h; thường cần ≥ 10 h (nhiều bài báo dùng 24–100 h) mới kết luận độ bền.")
        if _co(giu) and giu < 70:
            mood = "thinking"
    tom = "; ".join(f"{n}: giữ {_f(r.get('giu_dong (%)'), 0)} % dòng" for n, r in ds_it[:3])
    return mood, "Độ bền IT — " + tom + ".", ["Đánh giá phép đo độ bền (IT):"] + dong


def tu_eis(ds_eis):
    """ds_eis: [(nhãn, dict thong_so_eis)]."""
    if not ds_eis:
        return None
    ck = [(n, r.get("Rs ~ Z' tai f cao nhat (ohm)"), r.get("R_tong - Rs (ohm)")) for n, r in ds_eis]
    dong = ["Đánh giá EIS (Rs xấp xỉ Z' ở tần số cao nhất; R_tong−Rs xấp xỉ điện trở chuyển điện tích + khuếch tán):"]
    dong += [f"{n}: Rs ≈ {_f(rs, 2)} Ω; R_tong−Rs ≈ {_f(rc, 2)} Ω" for n, rs, rc in ck]
    hop = [(n, rc) for n, _, rc in ck if _co(rc)]
    tom = "EIS đã tính."
    if len(hop) >= 2:
        t = min(hop, key=lambda x: float(x[1]))
        dong.append(f"Điện trở chuyển điện tích thấp nhất: {t[0]} ({_f(t[1], 2)} Ω): thường ứng với động học nhanh hơn (cần so cùng điện thế và cùng điện cực).")
        tom = f"EIS: {t[0]} có R_tong−Rs thấp nhất ({_f(t[1], 2)} Ω)."
    dong.append("Muốn tách Rs/Rct chính xác hơn: dùng 'Fit EIS' trong app.")
    return "neutral", tom, dong


# ====================== LẤY SỐ TỪ APP (luồng chính) ======================
def tu_ngu_canh(nc, log=""):
    """Phân tích lại các file đang chọn bằng NguCanh (như tab Hỏi đáp) và viết nhận xét. Trả về sự kiện (dict) hoặc None."""
    import so_sanh
    import xu_ly_dien_hoa as xl
    cv, it, eis = [], [], []
    for k in range(len(nc.files)):
        try:
            m = nc.lay(k + 1)[1]
        except Exception:  # noqa: BLE001
            continue
        if m["loai"] in ("CV", "LSV"):
            cv.append(m)
        elif m["loai"] == "IT":
            try:
                it.append((m["nhan"], xl.thong_so_it(m["d"]).iloc[0].to_dict()))
            except Exception:  # noqa: BLE001
                pass
        elif m["loai"] == "EIS":
            try:
                eis.append((m["nhan"], xl.thong_so_eis(m["d"]).iloc[0].to_dict()))
            except Exception:  # noqa: BLE001
                pass
    a = nc.a
    for ten, mac in (("i_muc_tieu", "10"), ("qua_the_ht", "300"), ("e_can_bang", 1.23), ("n_e", "4"), ("ti_le_tam", "1")):
        if getattr(a, ten, None) in (None, ""):
            setattr(a, ten, mac)
    phan = []
    if cv:
        df, info = so_sanh.tong_hop(cv, a)
        r = tu_so_sanh(df, info)
        if r:
            phan.append(("So sánh CV/LSV", r))
    for ten, f, d in (("Độ bền IT", tu_it, it), ("EIS", tu_eis, eis)):
        r = f(d)
        if r:
            phan.append((ten, r))
    if not phan:
        return None
    mood = "thinking" if any(r[0] in ("thinking", "confused") for _, r in phan) else phan[0][1][0]
    dong = []
    for _, r in phan:
        dong += r[2] + [""]
    nguon = " + ".join(t for t, _ in phan)
    return _hoan_thien(nguon, "Đánh giá dữ liệu vừa phân tích", mood, " ".join(r[1] for _, r in phan), dong[:-1], _canh_bao_log(log))


# ====================== GCD (siêu tụ lai / pin) ======================
def tu_gcd(kq):
    """kq: kết quả gcd_pin.chay. → sự kiện hoặc None."""
    import gcd_pin as gp
    if not kq or not kq.get("mau"):
        return None
    u = kq["don_vi"]
    dien_dung = kq["chinh"] == "dien_dung"
    dong, tom, mood, xau = [], [], "happy", False
    dong.append(f"Đã phân tích {len(kq['mau'])} mẫu GCD. Báo cáo theo " + ("điện dung riêng (F/g)" if dien_dung else "dung lượng riêng (mAh/g)") + f" ({kq['ly_do']}).")
    for m in kq["mau"]:
        if not m["nhom"]:
            dong.append(f"• {m['ten']}: không tách được chu kỳ xả nào, kiểm tra chiều nạp và cột dòng/điện thế.")
            mood, xau = "confused", True
            continue
        g0 = m["nhom"][0]
        gtr = g0["Csp"] if dien_dung else g0["Qsp"]
        dv = u["C"] if dien_dung else u["Q"]
        dang = {"tụ": "dạng tụ (tam giác)", "lai": "dạng lai", "pin": "dạng pin (có plateau)"}.get(g0["dang"], g0["dang"])
        s = f"• {m['ten']}: {gtr:.4g} {dv} ở j = {g0['j']:.3g} {u['j']}, {dang}; CE ≈ {_f(g0['CE'], 1)} %; ESR ≈ {_f(g0['ESR'], 2)} Ω."
        ret = gp.chuoi_retention(m, kq["cfg"], kq["chinh"])
        if ret:
            nh, ds = ret
            s += f" Retention {_f(ds[-1]['retention'], 1)} % sau {ds[-1]['k']} chu kỳ."
            if ds[-1]["retention"] < 80:
                xau = True
        if m.get("toc_do"):
            b = m["toc_do"][-1]
            gk = b["giu_Csp"] if dien_dung else b["giu_Qsp"]
            s += f" Khả năng tốc độ {_f(gk, 0)} % khi j tăng từ {m['nhom'][0]['j']:.3g} lên {b['j']:.3g} {u['j']}."
        dong.append(s)
        tom.append(f"{m['ten']} {gtr:.3g} {dv}")
        ce = g0["CE"]
        if _co(ce) and ce > 100.5:
            xau = True
            dong.append(f"   ⚠ CE = {ce:.1f} % > 100 %: kiểm tra tách nạp/xả.")
    if kq.get("canh_bao_chung"):
        dong.append("Lưu ý về thiết lập:")
        dong += ["  • " + c for c in kq["canh_bao_chung"][:3]]
    if any(m["canh_bao"] for m in kq["mau"]):
        dong.append(f"Cảnh báo dữ liệu: {sum(len(m['canh_bao']) for m in kq['mau'])} mục (xem tab 'Công thức & lưu ý' và sheet 'Cảnh báo' khi xuất).")
    if xau:
        mood = "thinking" if mood != "confused" else mood
    return dict(nguon="Siêu tụ lai & Pin (GCD)", tieu_de="Đánh giá dữ liệu GCD", mood=mood, tom_tat="GCD: " + "; ".join(tom[:3]) + ".", chi_tiet="\n".join(dong))


# ====================== GỌI TỪ APP ======================
def danh_gia_nen(tao_ngu_canh, log=""):
    """Chạy trong luồng nền: dựng NguCanh, đánh giá, ghi sự kiện. Mọi lỗi bị nuốt (đánh giá chỉ là phần thêm, không được làm hỏng luồng chính). Trả về id hoặc None."""
    try:
        ev = tu_ngu_canh(tao_ngu_canh(), log)
        return ghi_su_kien(ev) if ev else None
    except Exception:  # noqa: BLE001
        return None


def thu_ghi(ham, *a, **k):
    """Gọi ham(...) → sự kiện → ghi. Mọi lỗi bị nuốt: nhận xét chỉ là phần thêm, không được làm hỏng công cụ đang dùng."""
    try:
        ev = ham(*a, **k)
        return ghi_su_kien(ev) if ev else None
    except Exception:  # noqa: BLE001
        return None


# ====================== XPS ======================
def tu_xps(kq, mau="", ten=""):
    """kq: xps.phan_tich_pho. Nhận xét chất lượng fit và từng thành phần (số do app tính; các ngưỡng 'tham khảo' là kiến thức chung)."""
    f = kq["fit"]
    tp = f["thanh_phan"]
    rs = f["rstd"]
    dong = [f"Fit XPS {mau or ''}{(' · ' + ten) if ten else ''}: {len(tp)} thành phần, Residual STD = {rs:.2f} "
            + ("(trong khoảng 0,85–1,15 thường coi là hợp lý)" if 0.85 <= rs <= 1.15 else "(ngoài 0,85–1,15)") + f", tự tương quan phần dư {f['tu_tuong_quan']:+.2f}."]
    for c in sorted(tp, key=lambda c: -c["pct"]):
        dong.append(f"• {c['ten']}: {c['vt']:.2f} eV, FWHM {c['fwhm']:.2f} eV, {c['pct']:.1f} % diện tích" + (" (chạm biên ràng buộc)" if c["o_bien"] else ""))
    for g in kq.get("ghi", []):
        if g.startswith(("Có đỉnh phụ", "Mô hình chuẩn không mô tả")):
            dong.append("Vùng fit: " + _cat(g, 260))
    dich = kq.get("dich_hieu_chuan")
    if dich is not None and math.isfinite(dich):
        dong.append(f"Dịch hiệu chuẩn đã áp dụng: {dich:+.3f} eV" + (" — lớn (> 1 eV): kiểm tra mẫu có nhiễm điện hoặc chọn nhầm đỉnh chuẩn." if abs(dich) > 1.0 else "."))
    canh = []
    for c in kq.get("canh_bao", []):
        if c.startswith("Lưu ý hiệu chuẩn"):
            continue                                              # câu nhắc chung, đã có trong báo cáo của công cụ
        canh.append(_cat(c, 230))
    if canh:
        dong.append("Lưu ý:")
        dong += ["  • " + c for c in canh[:5]]
        if len(canh) > 5:
            dong.append(f"  (còn {len(canh) - 5} lưu ý nữa trong ô Nhận xét của công cụ)")
    xau = rs > 1.5 or any(c["o_bien"] for c in tp) or bool(canh)
    mood = "confused" if rs > 1.5 else "thinking" if xau else "happy"
    tom = f"XPS {mau}: {len(tp)} thành phần, Residual STD {rs:.2f}" + (", có lưu ý cần xem." if xau else ", fit hợp lý.")
    return dict(nguon="XPS", tieu_de="Đánh giá fit XPS", mood=mood, tom_tat=tom, chi_tiet="\n".join(dong))


# ====================== XRD ======================
def tu_xrd(cac_kq, ss=None):
    """cac_kq: list kết quả xrd.phan_tich_mau; ss: xrd.so_sanh."""
    if not cac_kq:
        return None
    dong, mood = [f"Đã phân tích {len(cac_kq)} mẫu XRD."], "happy"
    for r in cac_kq:
        ten = r["mau"]["ten"]
        n_dinh = len(r["dinh"]["peaks"])
        if n_dinh == 0:
            dong.append(f"• {ten}: không tìm thấy đỉnh nhiễu xạ nào trên ngưỡng nhiễu (có thể vô định hình hoặc tín hiệu yếu; thử giảm ngưỡng SNR).")
            mood = "confused"
            continue
        la = sum(1 for g in r["gan"] if g["loai"] == "la")
        pha = ", ".join(f"{q['pha']['ten']} ({'rất chắc' if q['muc'] == 'chac' else 'chắc'}, {q['so_khop']} vạch)" for q in r["chap_nhan"]) or "chưa có pha nào đủ bằng chứng"
        dong.append(f"• {ten}: {n_dinh} đỉnh; pha xác định: {pha}; {la} đỉnh chưa xác định chắc; độ lệch 2θ chung {r['dich']:+.3f}°.")
        for q in r["chap_nhan"]:
            hs = q.get("hang_so_mang") or {}
            if hs.get("a") and hs.get("a_ref"):
                dl = 100.0 * (hs["a"] - hs["a_ref"]) / hs["a_ref"]
                s = f"   {q['pha']['ten']}: a = {hs['a']:.4f} Å (chuẩn {hs['a_ref']:.4f}, lệch {dl:+.2f} %)"
                if abs(dl) > 0.5:
                    s += " — lệch > 0,5 % (tham khảo): có thể do pha tạp/ứng suất hoặc lệch chiều cao mẫu."
                dong.append(s)
            kt = q.get("kich_thuoc") or {}
            if kt.get("tb"):
                dong.append(f"   Kích thước tinh thể (Scherrer) ≈ {kt['tb']:.0f} nm (miền kết hợp, không đồng nghĩa kích thước hạt).")
            if q.get("thieu"):
                dong.append(f"   {len(q['thieu'])} vạch đáng lẽ thấy nhưng không thấy: độ tin cậy giảm.")
        if r["goi_y"] and not r["chap_nhan"]:
            dong.append("   Chỉ có gợi ý yếu: " + ", ".join(q["pha"]["ten"] for q in r["goi_y"][:3]) + " — cần thêm bằng chứng (SAED, XPS, Raman...).")
            mood = "thinking" if mood == "happy" else mood
        if la >= max(2, n_dinh // 3):
            dong.append(f"   {la}/{n_dinh} đỉnh chưa gán được: có thể còn pha lạ ngoài ngân hàng hoặc ngưỡng/dung sai chưa hợp lý.")
            mood = "thinking" if mood == "happy" else mood
        if not r["chap_nhan"]:
            mood = "thinking" if mood == "happy" else mood
    if ss and ss.get("cac"):
        dong.append(f"So với mẫu chuẩn '{ss['chuan']}':")
        for c in ss["cac"]:
            dong.append(f"• {c['mau']}: trùng {len(c['chung'])} đỉnh, MỚI {len(c['moi'])}, mất {len(c['mat'])}.")
    tom = "XRD: " + "; ".join(f"{r['mau']['ten']} → " + (", ".join(q['pha']['ten'] for q in r['chap_nhan'][:2]) or "chưa xác định pha") for r in cac_kq[:3]) + "."
    return dict(nguon="XRD", tieu_de="Đánh giá pha XRD", mood=mood, tom_tat=tom, chi_tiet="\n".join(dong))


# ====================== HR-TEM ======================
def tu_hrtem_dom(dinh_ds, ket_qua_ds, goi_y_fn, nm_px=None):
    """Các đốm FFT tìm được trong vùng đang chọn. goi_y_fn(d) → list (pha, hkl, d_chuan, lech%)."""
    if not dinh_ds:
        return None
    dong = [f"Tìm được {len(dinh_ds)} đốm FFT trong vùng chọn" + (f" (thang {nm_px:.4g} nm/px)" if nm_px else "") + "."]
    mood, nhieu_pha = "happy", False
    for k, (dinh, kq) in enumerate(zip(dinh_ds[:4], ket_qua_ds[:4]), 1):
        s = f"• Đốm {k}: d(FFT) = {dinh['d']:.3f} nm"
        if kq.get("d_dinh"):
            s += f", d(profile) = {kq['d_dinh']:.3f} ± {kq['d_sd']:.3f} nm ({kq.get('n_van', '?')} vân)"
        gy = goi_y_fn(dinh["d"])
        if not gy:
            s += " → không khớp pha nào trong ngân hàng (dung sai hiện tại)."
            mood = "thinking"
        else:
            s += " → khớp: " + "; ".join(f"{p} {h} (lệch {l:+.1f} %)" for p, h, _, l in gy[:3])
            if len(gy) > 1:
                nhieu_pha = True
        dong.append(s)
        for c in kq.get("canh_bao", [])[:1]:
            dong.append("   ⚠ " + _cat(c, 200))
            mood = "thinking"
    if nhieu_pha:
        dong.append("Lưu ý: nhiều pha cùng khớp một giá trị d, nên d một mình không phân biệt được pha; cần thêm bằng chứng (XRD, SAED, XPS).")
    return dict(nguon="HR-TEM", tieu_de="Đánh giá đốm FFT", mood=mood, tom_tat=f"HR-TEM: {len(dinh_ds)} đốm FFT, đốm 1 có d = {dinh_ds[0]['d']:.3f} nm.", chi_tiet="\n".join(dong))


def tu_hrtem_phep_do(do_ds):
    """Danh sách phép đo đã thêm (mỗi phần tử: pha, hkl, d, d_chuan?, n_van?, xac_nhan?)."""
    if not do_ds:
        return None
    dong, mood = [f"Đã có {len(do_ds)} phép đo khoảng cách mặt mạng."], "happy"
    for k, m in enumerate(do_ds, 1):
        nhan = (f"{m.get('pha', '')} {m.get('hkl', '')}").strip() or "(chưa gán pha)"
        s = f"• #{k} {nhan}: d = {m['d']:.3f} nm"
        if m.get("d_chuan"):
            lech = 100.0 * (m["d"] - m["d_chuan"]) / m["d_chuan"]
            s += f", chuẩn {m['d_chuan']:.3f} nm, lệch {lech:+.1f} %"
            if abs(lech) > 3.0:
                s += " — lệch > 3 % (tham khảo): xem lại thang nm/px hoặc việc gán pha"
                mood = "thinking"
        else:
            s += " (chưa có d chuẩn để so)"
        if m.get("n_van") is not None and m["n_van"] < 5:
            s += f"; chỉ {m['n_van']} vân: nên đo trên ≥ 5–10 vân"
        x = m.get("xac_nhan")
        if x and x.get("tan_pct") is not None:
            s += f"; kiểm chứng: tản {x['tan_pct']:.1f} %" + (" (đạt)" if x.get("trang_thai") == "xac_nhan" else " (chưa đạt)")
            if x.get("trang_thai") != "xac_nhan":
                mood = "thinking"
        dong.append(s)
    return dict(nguon="HR-TEM", tieu_de="Đánh giá phép đo d", mood=mood, tom_tat=f"HR-TEM: {len(do_ds)} phép đo d" + ("; có phép lệch chuẩn." if mood == "thinking" else "."), chi_tiet="\n".join(dong))


# ====================== ECSA TƯƠNG TÁC ======================
def tu_ecsa(kq, e, cs, bo_qua=0):
    """kq: ecsa_tuong_tac.tinh(...); e: điện thế lấy dòng (V vs RHE); cs: Cs (mF/cm²)."""
    d = [x for x in kq["diem"] if x["dung"]]
    if kq.get("he_so") is None:
        return dict(nguon="ECSA", tieu_de="Đánh giá ECSA", mood="confused", tom_tat="ECSA: chưa đủ điểm để fit Cdl.",
                    chi_tiet=f"Chỉ có {len(d)} điểm dùng được tại E = {e:.3f} V: cần ít nhất 2 tốc độ quét khác nhau (khuyến nghị ≥ 4–5).")
    cdl = kq["he_so"]
    r2t = f"{kq['r2']:.4f}" if kq["r2"] is not None else "n/a"
    dong = [f"ECSA tại E = {e:.3f} V vs RHE: Cdl = {cdl:.3f} mF/cm² (độ dốc ΔJ = (Ja−Jc)/2 theo tốc độ quét), R² = {r2t}, {kq['n']} tốc độ quét"
            + (f" (bỏ {len(bo_qua) if hasattr(bo_qua, '__len__') else bo_qua})" if bo_qua else "") + "."]
    if kq.get("ecsa") is not None:
        dong.append(f"ECSA = Cdl/Cs = {kq['ecsa']:.1f} (Cs = {cs:g} mF/cm²).")
    canh = []
    if cdl <= 0:
        canh.append("Cdl ≤ 0: không hợp lý; điện thế chọn có thể nằm ngoài vùng lớp kép (có phản ứng faraday) hoặc quét sai chiều.")
    if kq["r2"] is not None and kq["r2"] < 0.99:
        canh.append(f"R² = {kq['r2']:.3f} < 0,99 (tham khảo): ΔJ không tuyến tính theo tốc độ quét; thử đổi điện thế lấy dòng hoặc bỏ tốc độ quét bất thường.")
    if kq["n"] < 4:
        canh.append(f"Chỉ {kq['n']} tốc độ quét: nên ≥ 4–5 để đường thẳng đáng tin.")
    if cdl > 0 and not 0.005 <= cdl <= 50:
        canh.append("Cdl ngoài 0,005–50 mF/cm² (tham khảo cho điện cực xúc tác thường gặp): kiểm tra diện tích điện cực và đơn vị.")
    if kq.get("tung") is not None and cdl > 0 and abs(kq["tung"]) > 0.5 * max(abs(x["y"]) for x in d):
        canh.append("Giao điểm trục tung lớn so với ΔJ: có thể còn dòng nền không do lớp kép.")
    if canh:
        dong.append("Lưu ý:")
        dong += ["  • " + c for c in canh]
    mood = "confused" if cdl <= 0 else "thinking" if canh else "happy"
    return dict(nguon="ECSA", tieu_de="Đánh giá ECSA / Cdl", mood=mood, tom_tat=f"ECSA: Cdl = {cdl:.2f} mF/cm²" + (f", R² = {kq['r2']:.3f}" if kq['r2'] is not None else "") + (" (có lưu ý)." if canh else "."),
                chi_tiet="\n".join(dong))


# ====================== TAFEL Qs-LSV ======================
def tu_tafel_qs(cac):
    """cac: [{'nhan':..., 'kq': tafel_qs.phan_tich(...)}]."""
    cac = [c for c in cac if c.get("kq")]
    if not cac:
        return None
    dong, canh = [], []
    for c in cac:
        k = c["kq"]
        dong.append(f"• {c['nhan']}: b = {abs(k['b_mV']):.1f} ± {k['sai_so_mV']:.1f} mV/dec, R² = {k['r2']:.4f}, {k['n']} điểm trải {k['decades']:.2f} decade.")
        canh += [_cat(x, 200) for x in k.get("canh_bao", [])]
    dong.insert(0, f"Tafel từ Qs-LSV cho {len(cac)} mẫu:")
    hop = sorted(cac, key=lambda c: abs(c["kq"]["b_mV"]))
    mood, tom = "neutral", f"Tafel Qs-LSV: {len(cac)} mẫu."
    if len(hop) >= 2:
        t = hop[0]
        dong.append(f"b nhỏ nhất: {t['nhan']} ({abs(t['kq']['b_mV']):.0f} mV/dec); cùng điều kiện, b nhỏ hơn thường là động học thuận lợi hơn "
                    f"(chênh {abs(hop[-1]['kq']['b_mV']) - abs(t['kq']['b_mV']):.0f} mV/dec so với mẫu lớn nhất).")
        tom = f"Tafel Qs-LSV: {t['nhan']} có b nhỏ nhất ({abs(t['kq']['b_mV']):.0f} mV/dec)."
        mood = "happy"
    thap = [c["nhan"] for c in cac if c["kq"]["decades"] < 1.0]
    if thap:
        dong.append("Vùng fit < 1 decade (khuyến nghị ≥ 1) ở: " + ", ".join(thap) + ": độ dốc kém tin cậy.")
    if canh:
        dong.append("Cảnh báo của công cụ:")
        dong += ["  • " + c for c in canh[:5]]
    if canh or thap:
        mood = "thinking"
    return dict(nguon="Tafel Qs-LSV", tieu_de="Đánh giá Tafel Qs-LSV", mood=mood, tom_tat=tom, chi_tiet="\n".join(dong))
