import os
import json
import urllib.request
import zipfile
import shutil

# THAY THẾ TEN_USER và TEN_REPO bằng tài khoản và tên kho chứa (repository) trên GitHub của bạn
GITHUB_USER = "TEN_USER"
GITHUB_REPO = "TEN_REPO"

VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"
ZIP_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/main.zip"

def kiem_tra_cap_nhat_moi(phien_ban_hien_tai):
    """Kiểm tra file version.json trên GitHub xem có phiên bản mới hơn không."""
    try:
        with urllib.request.urlopen(VERSION_URL, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            server_version = data.get("version", 1)
            if server_version > phien_ban_hien_tai:
                return True, data.get("ghi_chu", "Có bản cập nhật mới.")
    except Exception as e:
        print(f"Không thể kiểm tra cập nhật (có thể mất mạng): {e}")
    return False, ""

def thuc_hien_tai_va_va_loi():
    """Tự động tải mã nguồn zip từ GitHub, giải nén và ghi đè các file cũ."""
    try:
        thu_muc_hien_tai = os.path.dirname(os.path.abspath(__file__))
        zip_path = os.path.join(thu_muc_hien_tai, "update_temp.zip")
        
        print("Đang tải bản cập nhật từ GitHub...")
        urllib.request.urlretrieve(ZIP_URL, zip_path)
        
        print("Đang giải nén bản vá...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(thu_muc_hien_tai)
            
        # Tìm thư mục giải nén của GitHub (thường có dạng repo-main)
        thu_muc_giai_nen = None
        for item in os.listdir(thu_muc_hien_tai):
            duong_dan_item = os.path.join(thu_muc_hien_tai, item)
            if os.path.isdir(duong_dan_item) and item not in ["ket_qua", "origin_out", "csv_va_anh_nhanh"]:
                if os.path.exists(os.path.join(duong_dan_item, "xu_ly_dien_hoa.py")):
                    thu_muc_giai_nen = duong_dan_item
                    break
        
        if thu_muc_giai_nen:
            # Copy đè các file mã nguồn mới vào thư mục hiện tại
            for file_name in os.listdir(thu_muc_giai_nen):
                src_file = os.path.join(thu_muc_giai_nen, file_name)
                dst_file = os.path.join(thu_muc_hien_tai, file_name)
                if os.path.isfile(src_file):
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    shutil.copy(src_file, dst_file)
            
            # Xóa thư mục tạm sau khi copy xong
            shutil.rmtree(thu_muc_giai_nen)
            
        # Xóa file zip tạm
        if os.path.exists(zip_path):
            os.remove(zip_path)
            
        print("Cập nhật và vá lỗi thành công!")
        return True
    except Exception as e:
        print(f"Lỗi trong quá trình tải/cập nhật: {e}")
        return False