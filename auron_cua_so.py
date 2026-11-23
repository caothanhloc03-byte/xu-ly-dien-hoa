# -*- coding: utf-8 -*-
"""AURON trong Echem Studio: trợ lý hologram hỏi đáp & trợ giúp, mở thành CỬA SỔ RIÊNG của app (không mở trình duyệt, không mở trang web).

Cách làm: tiến trình con (giống các worker vẽ Origin) chạy một máy chủ HTTP chỉ nghe 127.0.0.1 để phát thư mục auron_web/ (kèm three.js và WebLLM
đã đóng gói sẵn) và /kien_thuc.json (dựng từ huong_dan_phep_do.py + HUONG_DAN.md), rồi mở cửa sổ WebView2 (thư viện pywebview) trỏ vào đó.
Cổng cố định để bộ nhớ đệm của mô hình (IndexedDB/Cache theo "origin" gồm cả cổng) được giữ giữa các lần mở.
Lõi (dựng kiến thức, máy chủ) không cần pywebview nên kiểm thử được; chỉ cửa sổ mới cần.
"""
import json
import mimetypes
import os
import re
import socket
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

THU_MUC = os.path.dirname(os.path.abspath(__file__))
THU_MUC_WEB = os.path.join(THU_MUC, "auron_web")
CONG_MAC_DINH = 47615
TIEU_DE = "AURON · Trợ lý Echem Studio"
MIME = {".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8",
        ".png": "image/png", ".wasm": "application/wasm", ".svg": "image/svg+xml"}


# ====================== KIẾN THỨC ======================
def _cat_chuong(md, toi_da=1800):
    """HUONG_DAN.md → các mục '## vNN - ...' (tên + nội dung đã bỏ dấu định dạng, cắt gọn)."""
    muc = []
    for phan in re.split(r"(?m)^## ", md)[1:]:
        dong = phan.split("\n", 1)
        ten = dong[0].strip()
        nd = re.sub(r"[*`|]", "", dong[1] if len(dong) > 1 else "")
        nd = re.sub(r"\n-{3,}.*", "", nd)
        nd = re.sub(r"[ \t]+", " ", nd)
        nd = re.sub(r"\n{3,}", "\n\n", nd).strip()
        if ten and nd:
            muc.append((ten, nd[:toi_da]))
    return muc


def xay_kien_thuc(thu_muc=THU_MUC):
    """→ {'muc': [{id, ten, tu_khoa[], tom_tat, buoc[], phep_tinh[], tieu_chi[], loi[], noi_dung}], 'phien_ban': n}"""
    muc = []
    try:
        import huong_dan_phep_do as h
        for t in h.TOPICS:
            pt = [f"{a}: {b}" + (f" ({c})" if c else "") for a, b, c in t.get("phep_tinh") or []]
            nd = h.van_ban(t["id"])
            muc.append(dict(id=t["id"], ten=t["ten"], tu_khoa=[t["id"]] + list(t.get("bi_danh") or []), tom_tat=t.get("tom_tat", ""),
                            buoc=list(t.get("buoc") or []), phep_tinh=pt, tieu_chi=list(t.get("tieu_chi") or []), loi=list(t.get("loi") or []), noi_dung=nd))
    except Exception:  # noqa: BLE001  (thiếu file hướng dẫn thì AURON vẫn chạy, chỉ ít kiến thức)
        pass
    pb = 0
    try:
        with open(os.path.join(thu_muc, "version.json"), encoding="utf-8") as f:
            pb = int(json.load(f).get("phien_ban_hien_tai", 0))
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(os.path.join(thu_muc, "HUONG_DAN.md"), encoding="utf-8") as f:
            for ten, nd in _cat_chuong(f.read()):
                muc.append(dict(id="md-" + re.sub(r"\W+", "-", ten.lower())[:40], ten=ten, tu_khoa=re.findall(r"\bv\d+\b", ten.lower()), phu=True,
                                tom_tat="", buoc=[], phep_tinh=[], tieu_chi=[], loi=[], noi_dung=nd))
    except Exception:  # noqa: BLE001
        pass
    try:
        import huong_dan_phep_do as h2
        muc.append(dict(id="nap-file", ten="Nạp file, chọn loại phép đo, lỗi thường gặp khi nạp", tu_khoa=["nap file", "them file", "keo tha", "loi doc file", "khong nhan file", "dinh dang file", "loai phep do", "sai loai"],
                        tom_tat="Mọi phép đo đều bắt đầu ở tab Dữ liệu: thêm file, kiểm tra cột Loại phép đo, rồi mới phân tích.", buoc=list(h2.CHUNG_BUOC_NAP),
                        phep_tinh=[], tieu_chi=[], loi=["File có chữ ở giữa số liệu hoặc thiếu cột: mở bằng Notepad kiểm tra, bấm ⚙ cạnh mẫu (nếu có) để chọn lại cột.", "Loại phép đo tự điền sai: chọn lại ở nhóm Phép đo (ô Loại).",
                                                          "Không có cột dòng (GCD): nhập dòng không đổi (mA)."], noi_dung="\n".join(h2.CHUNG_BUOC_NAP)))
    except Exception:  # noqa: BLE001
        pass
    muc.append(dict(id="tong-quan", ten="Echem Studio là gì, có những phần nào", tu_khoa=["echem studio", "app", "phan mem", "tong quan", "gioi thieu", "tab", "lam duoc gi"],
                    tom_tat=f"Echem Studio (phiên bản {pb}) nạp file đo điện hóa thô (CV, LSV, Tafel, IT, EIS, ECSA, GCD...), tự quy đổi RHE/mA·cm⁻², bù iR, vẽ hình theo chuẩn tạp chí "
                            "(matplotlib hoặc Origin), xuất báo cáo Excel có công thức, và có các công cụ riêng cho XPS, XRD, HRTEM, siêu tụ lai/pin.",
                    buoc=["Tab Dữ liệu: thêm file, chọn loại phép đo.", "Tab Phân tích: chọn phép tính và các công cụ riêng (XPS, XRD, GCD...).", "Tab Hình/Xuất: vẽ và xuất báo cáo.",
                          "Tab Hỏi đáp: hỏi số liệu của chính các file đã nạp (điện thế tại 10 mA, Tafel, ECSA...).", "Tab Trợ giúp: hướng dẫn từng phép đo."],
                    phep_tinh=[], tieu_chi=[], loi=[],
                    noi_dung="Echem Studio gồm các tab Dữ liệu, Phân tích, Hình, Xuất, Phổ, Hỏi đáp, Trợ giúp. Hỏi số liệu của file đã nạp thì dùng tab Hỏi đáp; AURON trả lời cách làm, công thức, tiêu chí và lỗi thường gặp."))
    return dict(muc=muc, phien_ban=pb)


# ====================== MÁY CHỦ CỤC BỘ ======================
class _XuLy(SimpleHTTPRequestHandler):
    kien_thuc_json = b"{}"
    thu_muc_web = THU_MUC_WEB

    def __init__(self, *a, **k):
        super().__init__(*a, directory=self.thu_muc_web, **k)

    def log_message(self, *a):          # không in log (exe ẩn console)
        pass

    def handle(self):                   # trình duyệt hủy giữa chừng (đóng cửa sổ, chuyển trang) không phải lỗi
        try:
            super().handle()
        except (ConnectionError, BrokenPipeError):
            pass

    def guess_type(self, path):
        return MIME.get(os.path.splitext(path)[1].lower()) or mimetypes.guess_type(path)[0] or "application/octet-stream"

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/su_kien":                    # nhận xét của AURON về dữ liệu vừa xử lý (app ghi file, trang hỏi định kỳ)
            q = parse_qs(urlparse(self.path).query)
            try:
                sau = int((q.get("sau") or ["0"])[0])
                tuoi = float((q.get("tuoi") or ["0"])[0])
            except ValueError:
                sau, tuoi = 0, 0.0
            try:
                import auron_danh_gia as dg
                ds = dg.doc_su_kien(sau)
            except Exception:  # noqa: BLE001
                ds = []
            if tuoi > 0:
                ds = [e for e in ds if time.time() - e.get("epoch", 0) <= tuoi]
            nd = json.dumps(ds, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", MIME[".json"])
            self.send_header("Content-Length", str(len(nd)))
            self.end_headers()
            self.wfile.write(nd)
            return
        if self.path.split("?")[0] == "/kien_thuc.json":
            self.send_response(200)
            self.send_header("Content-Type", MIME[".json"])
            self.send_header("Content-Length", str(len(self.kien_thuc_json)))
            self.end_headers()
            self.wfile.write(self.kien_thuc_json)
            return
        super().do_GET()


def khoi_dong_may_chu(thu_muc=THU_MUC, thu_muc_web=None, cong=None):
    """Mở máy chủ ở 127.0.0.1:cong (bận thì lấy cổng khác). → (httpd, cong). Chạy trong luồng nền."""
    web = thu_muc_web or os.path.join(thu_muc, "auron_web")
    if not os.path.isfile(os.path.join(web, "index.html")):
        raise FileNotFoundError(f"Thiếu {os.path.join(web, 'index.html')}")
    kt = json.dumps(xay_kien_thuc(thu_muc), ensure_ascii=False).encode("utf-8")
    xl = type("XuLy", (_XuLy,), dict(kien_thuc_json=kt, thu_muc_web=web))
    httpd = None
    for c in (CONG_MAC_DINH if cong is None else cong, 0):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", c), xl)
            break
        except OSError:
            continue
    if httpd is None:
        raise OSError("Không mở được cổng cục bộ cho AURON.")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def co_webview():
    try:
        import importlib.util
        return importlib.util.find_spec("webview") is not None
    except Exception:  # noqa: BLE001
        return False


def thu_muc_luu():
    goc = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(goc, "DienHoaOrigin", "auron_webview")


def main(argv=None):
    """Worker: python auron_cua_so.py | exe --worker-auron."""
    try:
        import webview
    except ImportError:
        sys.stderr.write("THIEU_PYWEBVIEW\n")
        return 3
    httpd, cong = khoi_dong_may_chu()
    os.makedirs(thu_muc_luu(), exist_ok=True)
    webview.create_window(TIEU_DE, f"http://127.0.0.1:{cong}/index.html", width=1180, height=800, min_size=(900, 620), background_color="#05080D")
    try:
        webview.start(private_mode=False, storage_path=thu_muc_luu())     # giữ mô hình đã tải & lựa chọn giữa các lần mở
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0


def kiem_tra_cong_bi_dung(cong=CONG_MAC_DINH):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", cong)) == 0


if __name__ == "__main__":
    sys.exit(main())
