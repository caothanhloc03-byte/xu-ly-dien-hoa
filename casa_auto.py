# -*- coding: utf-8 -*-
"""Tự động hoá CasaXPS (Windows): mở file .vms, bấm 'Fit Components', lưu (File > Save), rồi trả về đường dẫn file đã lưu.
Dùng pywinauto (backend win32): tìm cửa sổ và nút theo TÊN nên không phụ thuộc vị trí/độ phân giải. Mọi bước ghi vào file log;
khi không tìm thấy nút/menu, danh sách cửa sổ và điều khiển của Casa được ghi vào log để chỉnh lại cho đúng bản Casa đang dùng."""
import json
import os
import re
import subprocess
import time


class LoiCasa(Exception):
    pass


def co_pywinauto():
    try:
        import pywinauto  # noqa: F401
        return True
    except ImportError:
        return False


class _Log:
    def __init__(self, duong):
        self.duong = duong
        self.dong = []

    def __call__(self, s):
        d = time.strftime("%H:%M:%S ") + str(s)
        self.dong.append(d)
        try:
            with open(self.duong, "a", encoding="utf-8") as f:
                f.write(d + "\n")
        except OSError:
            pass


def _mo_ta_dieu_khien(app, ghi):
    """Ghi vào log mọi cửa sổ và điều khiển (loại, chữ) của tiến trình Casa - để biết tên thật khi script không tìm thấy."""
    try:
        for w in app.windows():
            ghi(f"[cửa sổ] '{w.window_text()}' lớp={w.friendly_class_name()}")
            try:
                for c in w.descendants():
                    t = c.window_text()
                    if t:
                        ghi(f"    - {c.friendly_class_name()}: '{t[:80]}'")
            except Exception as e:  # noqa: BLE001
                ghi(f"    (không liệt kê được: {e})")
    except Exception as e:  # noqa: BLE001
        ghi(f"(không liệt kê được cửa sổ: {e})")


def _tim_nut(app, mau):
    rx = re.compile(mau, re.I)
    for w in app.windows():
        try:
            for c in w.descendants():
                if c.friendly_class_name() == "Button" and rx.search(c.window_text() or ""):
                    return c
        except Exception:  # noqa: BLE001
            continue
    return None


def _tim_hop_qp(app):
    """Cửa sổ 'Quantification Parameters': tìm trong tiến trình Casa, không thấy thì tìm trên toàn màn hình."""
    for w in app.windows():
        try:
            if re.search(r"Quantification", w.window_text() or "", re.I):
                return w
        except Exception:  # noqa: BLE001
            continue
    try:
        from pywinauto import Desktop
        for w in Desktop(backend="win32").windows(title_re=".*Quantification Parameters.*"):
            return w
    except Exception:  # noqa: BLE001
        pass
    return None


def _tim_nut_chu(hop, mau):
    """Điều khiển có chữ khớp mau, KHÔNG phụ thuộc lớp (nút của Casa có thể tự vẽ)."""
    rx = re.compile(mau, re.I)
    try:
        for c in hop.descendants():
            if rx.search(c.window_text() or ""):
                return c
    except Exception:  # noqa: BLE001
        pass
    return None


def _bam_theo_ti_le(hop, tx, ty, ghi, ten):
    r = hop.rectangle()
    x = int(r.left + tx * (r.right - r.left))
    y = int(r.top + ty * (r.bottom - r.top))
    ghi(f"Bấm {ten} theo vị trí tương đối ({x},{y}) trong hộp {r}")
    from pywinauto import mouse
    mouse.click(coords=(x, y))


def _bam_fit(hop, ghi):
    """Hộp Quantification Parameters mở ở tab Regions: bấm sang tab Components (bên phải tab Regions, ~24% ngang, ~6.7% cao hộp), rồi bấm
    Fit Components (~50% ngang, ~64% cao hộp; đo trên ảnh Casa 2.3.24). Tìm theo chữ trước, không có chữ mới bấm theo vị trí."""
    try:
        hop.set_focus()
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.3)
    _bam_theo_ti_le(hop, 0.24, 0.067, ghi, "tab Components")
    time.sleep(0.8)
    nut = _tim_nut_chu(hop, r"Fit\s*Components")
    if nut is not None:
        ghi("Bấm nút theo chữ 'Fit Components'")
        try:
            nut.click()
        except Exception:  # noqa: BLE001
            nut.click_input()
        return True
    _bam_theo_ti_le(hop, 0.50, 0.64, ghi, "Fit Components")
    return True


def _chon_tab_components(app, ghi):
    """Chọn tab 'Components' của cửa sổ Quantification Parameters (nếu có thanh tab)."""
    for w in app.windows():
        try:
            for c in w.descendants():
                if c.friendly_class_name() == "TabControl":
                    c.select("Components")
                    ghi("Đã chọn tab Components")
                    time.sleep(0.5)
                    return
        except Exception as e:  # noqa: BLE001
            ghi(f"Không chọn được tab Components: {e}")


def _bam_hop_thoai(app, ghi, nhan=r"^(&?Yes|&?OK|&?Có|&?Save|&?Lưu|&?Replace)"):
    """Bấm các nút trả lời của hộp thoại xác nhận (lớp #32770) nếu có."""
    rx = re.compile(nhan, re.I)
    n = 0
    for w in app.windows():
        try:
            if w.class_name() != "#32770":
                continue
            for c in w.children():
                if c.friendly_class_name() == "Button" and rx.search(c.window_text() or ""):
                    ghi(f"Hộp thoại '{w.window_text()}': bấm '{c.window_text()}'")
                    c.click()
                    n += 1
                    break
        except Exception:  # noqa: BLE001
            continue
    return n


# ====================== XUẤT SỐ LIỆU TỪ CASA (nền, đường bao, thành phần, phần dư) ======================
def _clipboard_text():
    """Đọc clipboard Windows (PowerShell Get-Clipboard) - ổn định hơn các API Python khi Casa là chương trình 32-bit."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                           capture_output=True, timeout=20, creationflags=0x08000000)
        return r.stdout.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def _xoa_clipboard():
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $null"], capture_output=True, timeout=20, creationflags=0x08000000)
    except Exception:  # noqa: BLE001
        pass


def _doc_status(app):
    """Chữ trên thanh trạng thái của Casa (MFC hiện mô tả lệnh khi rê chuột lên nút thanh công cụ)."""
    out = []
    for w in app.windows():
        try:
            for c in w.descendants():
                if c.friendly_class_name() in ("StatusBar", "msctls_statusbar32"):
                    out += [t for t in c.texts() if t]
        except Exception:  # noqa: BLE001
            continue
    return " | ".join(out)


def _doc_tooltip():
    try:
        from pywinauto import Desktop
        for w in Desktop(backend="win32").windows(class_name="tooltips_class32", visible_only=True):
            t = (w.window_text() or "").strip()
            if t:
                return t
            try:
                from pywinauto.controls.common_controls import ToolTipsWrapper
                tw = ToolTipsWrapper(w.handle)
                for i in range(tw.tool_count()):
                    tt = tw.get_tip_text(i)
                    if tt:
                        return tt
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return ""


def liet_ke_thanh_cong_cu(app, ghi, cache):
    """Rê chuột qua từng nút của mọi thanh công cụ Casa, đọc mô tả (thanh trạng thái hoặc tooltip). Kết quả nhớ trong file cache để lần sau khỏi quét."""
    from pywinauto import mouse
    if os.path.exists(cache):
        try:
            d = json.load(open(cache, encoding="utf-8"))
            if d:
                ghi(f"Dùng bảng nút thanh công cụ đã lưu ({len(d)} nút)")
                return d
        except Exception:  # noqa: BLE001
            pass
    main = None
    for w in app.windows():
        if re.search(r"casa", w.window_text() or "", re.I) and not re.search(r"Quantification", w.window_text() or "", re.I):
            main = w
            break
    if main is None:
        return []
    try:
        main.set_focus()
    except Exception:  # noqa: BLE001
        pass
    kq = []
    tbs = [c for c in main.descendants() if c.friendly_class_name() in ("Toolbar", "ToolbarWindow32")]
    ghi(f"Quét {len(tbs)} thanh công cụ")
    for ti, tb in enumerate(tbs):
        try:
            n = tb.button_count()
        except Exception:  # noqa: BLE001
            continue
        for i in range(n):
            try:
                r = tb.button(i).rectangle()
                if r.width() <= 2:
                    continue
                mouse.move(coords=((r.left + r.right) // 2, (r.top + r.bottom) // 2))
            except Exception:  # noqa: BLE001
                continue
            time.sleep(0.9)
            mo_ta = _doc_status(app) or _doc_tooltip()
            kq.append({"tb": ti, "i": i, "mo_ta": mo_ta})
            ghi(f"[nút {ti}.{i}] {mo_ta}")
    try:
        json.dump(kq, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    except OSError:
        pass
    return kq


def _chinh_hop_thoai_xuat(app, ghi):
    """Hộp thoại tuỳ chọn xuất ASCII: tick các ô Background/Component/Envelope/Residual/Spectra, bấm OK."""
    rx = re.compile(r"backgr|component|envelope|synthetic|residual|fit", re.I)
    xong = False
    for w in app.windows():
        try:
            if w.class_name() != "#32770" or re.search(r"Quantification", w.window_text() or "", re.I):
                continue
            ghi(f"Hộp thoại '{w.window_text()}':")
            for c in w.children():
                ghi(f"    - {c.friendly_class_name()}: '{c.window_text()}'")
            for c in w.children():
                if c.friendly_class_name() in ("CheckBox", "Button") and rx.search(c.window_text() or ""):
                    try:
                        if c.get_check_state() == 0:
                            c.check()
                            ghi(f"    tick '{c.window_text()}'")
                    except Exception:  # noqa: BLE001
                        pass
            for c in w.children():
                if c.friendly_class_name() == "Button" and re.match(r"^&?(OK|Save|Export|Yes)", c.window_text() or "", re.I):
                    ghi(f"    bấm '{c.window_text()}'")
                    c.click()
                    xong = True
                    break
        except Exception:  # noqa: BLE001
            continue
    return xong


def xuat_so_lieu(app, ghi, cache):
    """Gọi lệnh xuất TAB ASCII của Casa lên clipboard, trả về chữ. Ném LoiCasa nếu không tìm/không lấy được."""
    from pywinauto import keyboard
    bang = liet_ke_thanh_cong_cu(app, ghi, cache)
    chon = None
    for mau in TOOLTIP_UU_TIEN:
        for b in bang:
            if re.search(mau, b.get("mo_ta") or "", re.I):
                chon = b
                break
        if chon:
            break
    if chon is None:
        raise LoiCasa("Không tìm thấy nút xuất TAB ASCII trên thanh công cụ Casa. Gửi file nhật ký để chỉnh (danh sách mô tả nút đã ghi trong đó).")
    ghi(f"Chọn nút xuất: [{chon['tb']}.{chon['i']}] {chon['mo_ta']}")
    main = [w for w in app.windows() if re.search(r"casa", w.window_text() or "", re.I) and not re.search(r"Quantification", w.window_text() or "", re.I)][0]
    tbs = [c for c in main.descendants() if c.friendly_class_name() in ("Toolbar", "ToolbarWindow32")]
    _xoa_clipboard()
    tbs[chon["tb"]].button(chon["i"]).click_input()
    t0 = time.time()
    txt = ""
    while time.time() - t0 < 30:
        time.sleep(1.0)
        _chinh_hop_thoai_xuat(app, ghi)
        _bam_hop_thoai(app, ghi)
        txt = _clipboard_text()
        if len(txt.strip()) > 200:
            break
    if len(txt.strip()) <= 200:
        raise LoiCasa("Casa không đưa dữ liệu vào clipboard (hộp thoại tuỳ chọn có thể cần chọn tay). Xem nhật ký.")
    ghi(f"Đã lấy {len(txt)} ký tự từ clipboard của Casa")
    return txt


def tu_dong_fit(vms, casa_exe, duong_log, cho_mo=40, cho_fit=6.0, cho_toi_da=120, so_lan_fit=2, ghi=None, xuat=True):
    """Mở vms bằng casa_exe, bấm Fit Components (so_lan_fit lần để hội tụ), lưu File > Save. Trả về vms (đã được Casa ghi đè).
    Ném LoiCasa kèm nội dung dễ hiểu nếu bước nào thất bại."""
    ghi = ghi or _Log(duong_log)
    if os.name != "nt":
        raise LoiCasa("Chức năng tự động chỉ chạy trên Windows.")
    if not co_pywinauto():
        raise LoiCasa("Thiếu thư viện pywinauto. Cài bằng: pip install pywinauto (bản exe cần được đóng gói kèm).")
    from pywinauto import Application, keyboard
    mt0 = os.path.getmtime(vms)
    ghi(f"Mở Casa: {casa_exe} {vms}")
    p = subprocess.Popen([casa_exe, vms])
    app = None
    t0 = time.time()
    while time.time() - t0 < cho_mo:
        try:
            app = Application(backend="win32").connect(process=p.pid, timeout=2)
            if any("casa" in (w.window_text() or "").lower() for w in app.windows()):
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.0)
    if app is None:
        raise LoiCasa("Không kết nối được cửa sổ CasaXPS (hết thời gian chờ).")
    time.sleep(3.0)
    _bam_hop_thoai(app, ghi)
    hop = _tim_hop_qp(app)
    if hop is None:
        ghi("Chưa thấy cửa sổ Quantification Parameters - gửi phím F7.")
        for lan in range(3):
            try:
                chinh = [w for w in app.windows() if re.search(r"casa", w.window_text() or "", re.I) and not re.search(r"Quantification", w.window_text() or "", re.I)]
                (chinh[0] if chinh else app.windows()[0]).set_focus()
                time.sleep(0.5)
                keyboard.send_keys("{F7}")
            except Exception as e:  # noqa: BLE001
                ghi(f"Không gửi được F7: {e}")
            t1 = time.time()
            while time.time() - t1 < 4.0 and hop is None:
                time.sleep(0.5)
                hop = _tim_hop_qp(app)
            if hop is not None:
                break
    if hop is None:
        _mo_ta_dieu_khien(app, ghi)
        raise LoiCasa("Không thấy cửa sổ Quantification Parameters sau khi gửi F7; hãy bấm F7 trong Casa rồi chạy lại. "
                      f"Danh sách cửa sổ/nút đã ghi trong {duong_log}.")
    ghi(f"Đã thấy hộp: '{hop.window_text()}' {hop.rectangle()}")
    _mo_ta_dieu_khien(app, ghi)                      # luôn ghi danh sách điều khiển để chỉnh khi cần
    for i in range(so_lan_fit):
        ghi(f"Fit Components (lần {i + 1})")
        _bam_fit(hop, ghi)
        time.sleep(cho_fit)
        _bam_hop_thoai(app, ghi)
    # lưu: File > Save của cửa sổ chính
    luu = False
    for w in app.windows():
        try:
            if re.search(r"casa", w.window_text() or "", re.I) and w.menu() is not None:
                for duong in ("File->Save", "&File->&Save", "File->Save As...", "&File->Save &As..."):
                    try:
                        w.menu_select(duong)
                        ghi(f"Menu: {duong}")
                        luu = True
                        break
                    except Exception:  # noqa: BLE001
                        continue
            if luu:
                break
        except Exception:  # noqa: BLE001
            continue
    if not luu:
        ghi("Không chọn được menu - thử Ctrl+S")
        try:
            keyboard.send_keys("^s")
            luu = True
        except Exception as e:  # noqa: BLE001
            ghi(f"Ctrl+S lỗi: {e}")
    t0 = time.time()
    while time.time() - t0 < cho_toi_da:
        time.sleep(1.0)
        _bam_hop_thoai(app, ghi)
        try:
            if os.path.getmtime(vms) > mt0 + 0.5:
                ghi("File đã được Casa ghi lại.")
                time.sleep(1.0)
                txt = None
                if xuat:
                    try:
                        txt = xuat_so_lieu(app, ghi, os.path.join(os.path.expanduser("~"), ".echem_casa_toolbar.json"))
                        with open(os.path.splitext(vms)[0] + "_casa_so_lieu.txt", "w", encoding="utf-8") as fh:
                            fh.write(txt)
                    except Exception as e:  # noqa: BLE001
                        ghi(f"Không xuất được số liệu từ Casa: {e}")
                return {"vms": vms, "so_lieu": txt}
        except OSError:
            pass
    _mo_ta_dieu_khien(app, ghi)
    raise LoiCasa(f"Casa chưa ghi lại file sau {cho_toi_da}s (có thể đang hiện hộp thoại lạ). Chi tiết trong {duong_log}.")
