# -*- coding: utf-8 -*-
"""
Lỗi dễ hiểu bằng tiếng Việt + kiểm tra trước khi chạy + nhật ký.

  • goi_y_sua(text)        : đọc toàn bộ đầu ra của tiến trình, nhận diện lỗi quen thuộc, trả về lời giải thích + cách xử lý.
  • kiem_tra_truoc(...)    : kiểm tra file, thư mục kết quả, Origin... TRƯỚC khi chạy.
  • ghi_nhat_ky(...)       : ghi nhat_ky.log (tự xoay vòng khi quá lớn).
Chỉ dùng thư viện chuẩn.
"""
import datetime
import os
import re
import sys
import tempfile

# (mẫu regex, tiêu đề, cách xử lý)  -- thứ tự quan trọng: cụ thể trước, chung sau
MAU_LOI = [
    (r"Chua cai originpro|No module named ['\"]originpro['\"]",
     "Chưa có thư viện điều khiển Origin (originpro).",
     "Cài bằng:  python -m pip install originpro  (cần Windows + Origin 2021 trở lên, khuyến nghị 2022+). Với bản exe, build lại bằng build.bat. "
     "Nếu không có Origin, bỏ tick 'Vẽ bằng Origin' và chỉ dùng 'Xuất CSV & Ảnh Matplotlib'."),
    (r"com_error|pywintypes|Failed to (start|connect)|could not (start|connect)|RPC server|OriginExt",
     "Không kết nối được Origin.",
     "Mở Origin một lần cho đến khi thấy giao diện chính (đóng hộp thoại kích hoạt/cập nhật nếu có), "
     "đóng các hộp thoại đang mở rồi chạy lại. Kiểm tra bản quyền Origin còn hạn và Origin là bản 2022 trở lên (originpro cần Origin 2021 trở lên)."),
    (r"UnicodeEncodeError|UnicodeDecodeError",
     "Lỗi mã hóa ký tự tiếng Việt.",
     "Bấm 'Kiểm tra cập nhật' để lấy bản mới nhất. Nếu vẫn lỗi, tên file/thư mục có thể chứa ký tự lạ: thử đổi sang tên đơn giản."),
    (r"PermissionError|Permission denied|\[Errno 13\]",
     "Không ghi được file kết quả.",
     "Đóng file đang mở trong Excel/Origin/trình xem ảnh (đặc biệt bao_cao_tong_hop.xlsx, *.opju, *.png trong thư mục kết quả), "
     "hoặc chọn thư mục kết quả khác (không đặt trong thư mục hệ thống như C:\\Windows)."),
    (r"FileNotFoundError|No such file or directory|\[Errno 2\]",
     "Không tìm thấy file hoặc thư mục.",
     "File có thể đã bị di chuyển/xóa hoặc đường dẫn quá dài. Thêm lại file vào danh sách ở mục 1."),
    (r"Không đọc được số liệu",
     "File không đúng định dạng số liệu thô (cần 3 cột E, i, T; hoặc file EIS có Freq/Z'/Z'').",
     "Kiểm tra file có đúng là xuất từ CS Studio không và không bị rỗng."),
    (r"ECSA can it nhat 2 file CV",
     "ECSA cần ít nhất 2 file CV ở 2 tốc độ quét khác nhau.",
     "Thêm các file CV (khuyến nghị ≥ 5 tốc độ quét), hoặc kiểm tra file có đúng là CV (cột 'Loại' trong bảng)."),
    (r"khong co vung dien the chung",
     "Các file CV không có vùng điện thế chung.",
     "Các CV phải quét cùng một khoảng điện thế. Kiểm tra pH/Eref hoặc loại bỏ file lệch khoảng quét."),
    (r"SVD did not converge|array must not contain infs or NaNs|Input contains NaN|nan values",
     "Dữ liệu chứa giá trị rỗng/NaN nên không fit được.",
     "Kiểm tra file thô có dòng thiếu số hoặc hỏng; thử bỏ file đó ra khỏi danh sách."),
    (r"zero-size array|empty sequence|Không có dữ liệu|index out of bounds|IndexError",
     "Dữ liệu quá ít hoặc rỗng sau khi xử lý.",
     "Kiểm tra loại phép đo đã chọn có đúng với file không (vd chọn CV nhưng file là IT)."),
    (r"KeyError: ['\"]Z",
     "File được nhận dạng sai loại (không phải EIS).",
     "Ở mục 2 hãy chọn đúng loại phép đo thay vì 'Tự nhận dạng'."),
    (r"MemoryError",
     "Hết bộ nhớ khi xử lý file quá lớn.",
     "Đóng bớt chương trình khác, hoặc xử lý ít file hơn mỗi lần."),
    (r"No module named ['\"]([\w\.]+)['\"]",
     "Thiếu thư viện Python: '{0}'.",
     "Cài bằng:  python -m pip install {0}   (với bản exe: cần build lại bằng build.bat)."),
    (r"mã thoát -?(9|15|1073741510)\b",
     "Tiến trình bị dừng đột ngột.",
     "Có thể bạn đã bấm Dừng hoặc chương trình bị tắt bởi hệ thống/antivirus."),
]


def goi_y_sua(text):
    """Trả về list[str] các gợi ý (rỗng nếu không nhận diện được lỗi nào)."""
    kq, da = [], set()
    for mau, tieu_de, cach in MAU_LOI:
        m = re.search(mau, text or "", re.IGNORECASE if mau.startswith("(?i)") else 0)
        if m:
            nhom = m.groups() if m.groups() else ()
            if nhom and nhom[0] == "originpro" and any("originpro" in x for x in da):
                continue          # đã có gợi ý riêng cho originpro
            td = tieu_de.format(*nhom) if "{" in tieu_de else tieu_de
            ca = cach.format(*nhom) if "{" in cach else cach
            if td in da:
                continue
            da.add(td)
            kq.append(f"• {td}\n   → {ca}")
    return kq


# ====================== KIỂM TRA TRƯỚC KHI CHẠY ======================
def origin_da_cai():
    """True / False nếu biết chắc; None nếu không kiểm tra được (không phải Windows)."""
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for sub in (r"SOFTWARE\OriginLab", r"SOFTWARE\WOW6432Node\OriginLab"):
            try:
                winreg.CloseKey(winreg.OpenKey(hive, sub))
                return True
            except OSError:
                continue
    return False


def kiem_tra_truoc(muc, dung_origin, thu_muc_ra, loai_chon="Tự nhận dạng"):
    """muc: list dict {path, nhan, loai_nhan(optional)}. Trả về (loi, luu_y): loi chặn việc chạy, luu_y chỉ nhắc."""
    loi, luu_y = [], []
    if not muc:
        return ["Chưa chọn file số liệu nào (mục 1)."], []
    thay = {}
    for m in muc:
        p = m["path"]
        if not os.path.isfile(p):
            loi.append(f"Không tìm thấy file: {p}")
            continue
        try:
            if os.path.getsize(p) == 0:
                loi.append(f"File rỗng: {os.path.basename(p)}")
                continue
            with open(p, "rb") as f:
                f.read(1)
        except OSError as e:
            loi.append(f"Không đọc được file {os.path.basename(p)}: {e}")
        thay.setdefault(m["nhan"], []).append(os.path.basename(p))
    for nhan, ds in thay.items():
        if len(ds) > 1:
            luu_y.append(f"Có {len(ds)} file cùng nhãn '{nhan}' ({', '.join(ds)}): chú thích trên hình sẽ khó phân biệt.")
    # thư mục kết quả ghi được?
    try:
        os.makedirs(thu_muc_ra, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=thu_muc_ra, delete=True):
            pass
    except OSError as e:
        loi.append(f"Không ghi được vào thư mục kết quả '{thu_muc_ra}': {e}")
    # Origin
    if dung_origin:
        if os.name != "nt":
            loi.append("Vẽ bằng Origin chỉ chạy được trên Windows. Hãy bỏ tick 'Vẽ bằng Origin'.")
        elif origin_da_cai() is False:
            luu_y.append("Không tìm thấy Origin trong danh sách phần mềm đã cài. Nếu Origin đã cài, bạn có thể bỏ qua lưu ý này.")
    # loại phép đo chọn so với nhận dạng
    loai_goc = (loai_chon or "").split(" ")[0].upper()
    if loai_goc in ("LSV", "CV", "IT", "EIS", "ECSA", "TAFEL"):
        mong = {"LSV": {"LSV", "CV"}, "CV": {"CV", "LSV"}, "TAFEL": {"LSV", "CV"}, "ECSA": {"CV"}, "IT": {"IT"}, "EIS": {"EIS"}}[loai_goc]
        for m in muc:
            lt = (m.get("loai_nhan") or "?").split(" ")[0]
            if lt in ("LSV", "CV", "IT", "EIS") and lt not in mong:
                luu_y.append(f"'{m['nhan']}' trông giống {m['loai_nhan']} nhưng bạn đang chọn loại phép đo '{loai_chon}'.")
    return loi, luu_y


# ====================== NHẬT KÝ ======================
DUNG_LUONG_TOI_DA = 1_500_000


def ghi_nhat_ky(thu_muc, tieu_de, noi_dung=""):
    """Ghi vào <thu_muc>/nhat_ky.log; trả về đường dẫn (hoặc None nếu không ghi được)."""
    try:
        os.makedirs(thu_muc, exist_ok=True)
        duong = os.path.join(thu_muc, "nhat_ky.log")
        if os.path.exists(duong) and os.path.getsize(duong) > DUNG_LUONG_TOI_DA:
            cu = os.path.join(thu_muc, "nhat_ky.old.log")
            if os.path.exists(cu):
                os.remove(cu)
            os.replace(duong, cu)
        with open(duong, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {tieu_de} =====\n")
            if noi_dung:
                f.write(noi_dung.rstrip("\n") + "\n")
        return duong
    except OSError:
        return None


def thong_tin_may():
    import platform
    return f"Python {sys.version.split()[0]} | {platform.platform()} | frozen={getattr(sys, 'frozen', False)}"
