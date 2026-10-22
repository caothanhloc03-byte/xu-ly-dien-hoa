# -*- coding: utf-8 -*-
"""
Tự động cập nhật mã nguồn từ GitHub.

Quy trình:
  1. Đọc version.json trên GitHub (raw) và so với version.json đang có trên máy.
  2. Nếu bản trên GitHub mới hơn -> tải zip, kiểm tra cú pháp, sao lưu file cũ, ghi đè.
  3. Lỗi giữa chừng -> tự khôi phục file cũ. version.json luôn được ghi CUỐI CÙNG,
     nên một lần cập nhật dở dang sẽ không bị coi là "đã xong".

Yêu cầu: repository GitHub phải để chế độ Public.
"""
import json
import os
import shutil
import tempfile
import time
import urllib.request
import zipfile

GITHUB_USER = "caothanhloc03-byte"
GITHUB_REPO = "xu-ly-dien-hoa"
NHANH = "main"

VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{NHANH}/version.json"
ZIP_URL_MAC_DINH = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/{NHANH}.zip"

THU_MUC = os.path.dirname(os.path.abspath(__file__))
DUOI_FILE_CAP_NHAT = (".py", ".pyw", ".ico", ".json")
KHONG_GHI_DE = {"cai_dat.json", "launcher.py"}   # file cấu hình người dùng / file khởi động
UA = {"User-Agent": "DienHoaOrigin-Updater"}


def _lay_so_phien_ban(d):
    for k in ("phien_ban_hien_tai", "version"):
        if k in d:
            return int(d[k])
    raise ValueError("version.json thiếu khóa 'phien_ban_hien_tai'")


def doc_thong_tin_cuc_bo(thu_muc=THU_MUC):
    try:
        with open(os.path.join(thu_muc, "version.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def doc_phien_ban_cuc_bo(thu_muc=THU_MUC):
    try:
        return _lay_so_phien_ban(doc_thong_tin_cuc_bo(thu_muc))
    except Exception:
        return 0


def _them_tham_so_chong_cache(url):
    if url.startswith("http"):
        return url + ("&" if "?" in url else "?") + f"t={int(time.time())}"
    return url


def _tai_json(url):
    req = urllib.request.Request(_them_tham_so_chong_cache(url), headers=UA)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def kiem_tra_cap_nhat(version_url=VERSION_URL, thu_muc=THU_MUC):
    """Trả về (co_ban_moi: bool, thong_tin_server: dict, loi: str | None)."""
    try:
        tt = _tai_json(version_url)
        moi = _lay_so_phien_ban(tt)
    except Exception as e:
        return False, {}, f"Không kiểm tra được cập nhật (mất mạng hoặc repository chưa Public): {e}"
    return moi > doc_phien_ban_cuc_bo(thu_muc), tt, None


def _tim_thu_muc_nguon(goc):
    """Tìm thư mục (nông nhất) chứa xu_ly_dien_hoa.py trong gói giải nén."""
    tot = None
    for dp, _, fs in os.walk(goc):
        if "xu_ly_dien_hoa.py" in fs:
            if tot is None or len(dp) < len(tot):
                tot = dp
    return tot


def cap_nhat(thong_tin, thu_muc=THU_MUC, log=print):
    """Tải & ghi đè mã nguồn. Trả về (thanh_cong: bool, thong_bao: str)."""
    url = thong_tin.get("link_tai_zip") or ZIP_URL_MAC_DINH
    tmp = tempfile.mkdtemp(prefix="dienhoa_upd_")
    sao_luu = os.path.join(thu_muc, "_sao_luu")
    da_ghi = {}  # ten_file -> True nếu trước đó đã tồn tại (có bản sao lưu)
    try:
        zip_path = os.path.join(tmp, "update.zip")
        log("Đang tải bản cập nhật từ GitHub...")
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r, open(zip_path, "wb") as f:
            shutil.copyfileobj(r, f)

        log("Đang giải nén...")
        giai_nen = os.path.join(tmp, "x")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(giai_nen)
        nguon = _tim_thu_muc_nguon(giai_nen)
        if nguon is None:
            raise ValueError("Gói tải về không chứa xu_ly_dien_hoa.py")

        ds = []
        for ten in sorted(os.listdir(nguon)):
            if (os.path.isfile(os.path.join(nguon, ten)) and ten not in KHONG_GHI_DE
                    and ten.lower().endswith(DUOI_FILE_CAP_NHAT)):
                ds.append(ten)
        if "version.json" in ds:            # ghi version.json sau cùng
            ds.remove("version.json")
            ds.append("version.json")

        log("Đang kiểm tra cú pháp các file mới...")
        for ten in ds:
            if ten.lower().endswith((".py", ".pyw")):
                with open(os.path.join(nguon, ten), "rb") as f:
                    compile(f.read(), ten, "exec")

        shutil.rmtree(sao_luu, ignore_errors=True)
        os.makedirs(sao_luu, exist_ok=True)
        for ten in ds:
            dst = os.path.join(thu_muc, ten)
            co_cu = os.path.exists(dst)
            if co_cu:
                shutil.copy2(dst, os.path.join(sao_luu, ten))
            da_ghi[ten] = co_cu
            shutil.copyfile(os.path.join(nguon, ten), dst + ".new")
            os.replace(dst + ".new", dst)
            log(f"  đã cập nhật: {ten}")
        return True, "Cập nhật thành công."
    except Exception as e:
        for ten, co_cu in da_ghi.items():          # khôi phục
            dst = os.path.join(thu_muc, ten)
            try:
                if co_cu:
                    shutil.copy2(os.path.join(sao_luu, ten), dst)
                elif os.path.exists(dst):
                    os.remove(dst)
            except Exception:
                pass
        return False, f"Cập nhật thất bại, đã khôi phục bản cũ: {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    co, tt, loi = kiem_tra_cap_nhat()
    if loi:
        print(loi)
    elif co:
        print("Có bản mới:", tt.get("ghi_chu", ""))
        print(cap_nhat(tt)[1])
    else:
        print("Đang dùng bản mới nhất.")
