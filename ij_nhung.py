# -*- coding: utf-8 -*-
"""Nhúng cửa sổ ImageJ thật (thanh công cụ + cửa sổ ảnh) vào một khung của app (chỉ Windows).

Cách làm: chạy ImageJ bình thường, tìm cửa sổ Java (lớp SunAwtFrame) theo tiêu đề rồi dùng
SetParent của Win32 để gắn vào khung tk. Mọi thao tác chuột/phím trong khung đó là của ImageJ thật.
Hạn chế: thanh menu của ImageJ không hiện khi cửa sổ trở thành cửa sổ con (dùng nút trên thanh công cụ,
phím tắt, hoặc bấm "Tách ImageJ" để có lại menu)."""
import os
import shutil
import subprocess
import sys
import time

HOP_LE = sys.platform == "win32"
TIEU_DE_CHINH = ("ImageJ", "(Fiji Is Just) ImageJ")

if HOP_LE:                                    # pragma: no cover - chỉ chạy trên Windows
    import ctypes
    from ctypes import wintypes

    _u = ctypes.windll.user32
    _u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _u.GetWindowLongW.restype = ctypes.c_long
    _u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    _u.SetWindowLongW.restype = ctypes.c_long
    _u.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    _u.SetParent.restype = wintypes.HWND
    _u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    _u.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
    _u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _u.IsWindowVisible.argtypes = [wintypes.HWND]
    _u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    _u.IsWindow.argtypes = [wintypes.HWND]
    _u.RedrawWindow.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    _PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _u.EnumWindows.argtypes = [_PROC, wintypes.LPARAM]

GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_CHILD, WS_POPUP, WS_CAPTION, WS_THICKFRAME = 0x40000000, 0x80000000, 0x00C00000, 0x00040000
WS_SYSMENU, WS_MINBOX, WS_MAXBOX, WS_VISIBLE = 0x00080000, 0x00020000, 0x00010000, 0x10000000
SWP_NOZORDER, SWP_FRAMECHANGED, SWP_SHOWWINDOW, SWP_NOACTIVATE = 0x0004, 0x0020, 0x0040, 0x0010


def bo_cuc(rong, cao, cao_thanh, rong_thanh=None):
    """Chia khung rong x cao: thanh công cụ ở trên, cửa sổ ảnh chiếm phần còn lại. Trả về ((x,y,w,h) thanh, (x,y,w,h) ảnh)."""
    cao_thanh = max(0, min(int(cao_thanh), int(cao) - 40))
    rt = int(rong) if rong_thanh is None else min(int(rong_thanh), int(rong))
    return (0, 0, rt, cao_thanh), (0, cao_thanh, int(rong), max(int(cao) - cao_thanh, 40))


LOAI_CHON = {0: "Rectangle", 1: "Oval", 2: "Polygon", 3: "Freehand", 4: "Traced", 5: "Line", 6: "Polyline",
             7: "Freeline", 8: "Angle", 9: "Composite", 10: "Point"}

_VONG_DONG_BO = r"""
id=getImageID();
f="%(chon)s";
cf="%(lenh)s";
t=f+".tmp";
last="";
while (isOpen(id)) {
    if (File.exists(cf)) {
        c=File.openAsString(cf);
        File.delete(cf);
        c=String.trim(c);
        if (startsWith(c,"tool:")) {
            setTool(substring(c,5));
        } else if (startsWith(c,"run:")) {
            c=substring(c,4);
            i=indexOf(c,"|");
            if (i<0) run(c);
            else run(substring(c,0,i),substring(c,i+1));
        }
    }
    s="TYPE=-1";
    st=-1;
    act=isActive(id);
    if (!act) s=last;
    if (act) st=selectionType();
    if (st>=0) {
        getSelectionBounds(bx,by,bw,bh);
        s="TYPE="+st+"\nX="+bx+"\nY="+by+"\nW="+bw+"\nH="+bh;
        getSelectionCoordinates(xs,ys);
        n=xs.length;
        if (n>200) n=200;
        sx="";
        sy="";
        for (i=0;i<n;i++) {
            sx=sx+d2s(xs[i],2)+";";
            sy=sy+d2s(ys[i],2)+";";
        }
        s=s+"\nXS="+sx+"\nYS="+sy;
    }
    if (s!=last) {
        File.saveString(s,t);
        File.delete(f);
        File.rename(t,f);
        last=s;
    }
    wait(250);
}
"""


CAO_THANH_TOI_THIEU = 110          # ImageJ: tiêu đề + menu + hàng công cụ + dòng trạng thái


def chieu_cao_thanh(cao_do_duoc):
    """Chiều cao dùng cho cửa sổ thanh công cụ: không để thấp hơn mức tối thiểu (đo quá sớm sẽ bị cắt mất hàng biểu tượng)."""
    return max(int(cao_do_duoc), CAO_THANH_TOI_THIEU)


# Lệnh app được phép gửi sang ImageJ (tên sai làm macro dừng nên chỉ dùng danh sách đã biết chắc)
CONG_CU_IJ = (("rectangle", "Rect"), ("oval", "Oval"), ("polygon", "Poly"), ("freehand", "Free"), ("line", "Line"),
              ("angle", "Angle"), ("point", "Point"), ("wand", "Wand"), ("text", "Text"), ("zoom", "Zoom"),
              ("hand", "Hand"), ("dropper", "Picker"))
MENU_IJ = {
    "Edit": (("Undo", "Undo"), ("Select None", "Select None"), ("To Bounding Box", "To Bounding Box")),
    "Image": (("Duplicate...", "Duplicate..."), ("Crop", "Crop"), ("Brightness/Contrast...", "Brightness/Contrast..."),
              ("Scale...", "Scale..."), ("Properties...", "Properties..."), ("Invert LUT", "Invert LUT")),
    "Process": (("FFT", "FFT"), ("Inverse FFT", "Inverse FFT"), ("Smooth", "Smooth"), ("Gaussian Blur...", "Gaussian Blur..."),
                ("Subtract Background...", "Subtract Background..."), ("Enhance Contrast...", "Enhance Contrast..."),
                ("Find Edges", "Find Edges")),
    "Analyze": (("Measure", "Measure"), ("Plot Profile", "Plot Profile"), ("Histogram", "Histogram"),
                ("Set Scale...", "Set Scale...")),
    "Zoom": (("In [+]", "Phóng to"), ("Out [-]", "Thu nhỏ"), ("Original Scale", "Tỷ lệ 100%")),
}
LENH_HOP_LE = {l for m in MENU_IJ.values() for l, _ in m}


def gui_lenh(duong_lenh, noi_dung):
    """Gửi lệnh cho macro đang chạy trong ImageJ: 'tool:rectangle' hoặc 'run:Tên lệnh|tham số'. Chỉ nhận lệnh đã biết."""
    nd = noi_dung.strip()
    if nd.startswith("tool:"):
        if nd[5:] not in {k for k, _ in CONG_CU_IJ}:
            raise ValueError("Công cụ ImageJ không hợp lệ: " + nd)
    elif nd.startswith("run:"):
        if nd[4:].split("|", 1)[0] not in LENH_HOP_LE:
            raise ValueError("Lệnh ImageJ không nằm trong danh sách cho phép: " + nd)
    else:
        raise ValueError("Lệnh không hợp lệ: " + nd)
    tam = duong_lenh + ".tmp"
    with open(tam, "w", encoding="ascii", newline="\n") as f:
        f.write(nd + "\n")
    os.replace(tam, duong_lenh)


def tao_macro_mo(duong_anh, nm_px, duong_chon=None, duong_lenh=None):
    """Macro mở ảnh, đặt thang theo nm/px, chọn công cụ hình chữ nhật và (nếu có duong_chon) liên tục ghi vùng chọn
    hiện tại của ImageJ ra file để app đọc về."""
    p = duong_anh.replace("\\", "/")
    dong = ['open("%s");' % p]
    if nm_px and nm_px > 0:
        dong.append('run("Set Scale...", "distance=1 known=%.8f unit=nm");' % nm_px)
    dong.append('setTool("rectangle");')
    if duong_chon:
        dong.append(_VONG_DONG_BO % {"chon": duong_chon.replace("\\", "/"),
                                     "lenh": (duong_lenh or duong_chon + ".lenh").replace("\\", "/")})
    return "\n".join(dong) + "\n"


def doc_chon(duong):
    """Đọc file vùng chọn do macro ghi. Trả về None nếu chưa có/không có vùng chọn, ngược lại dict
    {loai, ten, x, y, w, h, xs, ys} (px ảnh)."""
    try:
        with open(duong, "r", encoding="utf-8", errors="ignore") as f:
            tx = f.read()
    except OSError:
        return None
    kv = {}
    for dong in tx.splitlines():
        if "=" in dong:
            k, v = dong.split("=", 1)
            kv[k.strip()] = v.strip()
    try:
        loai = int(kv.get("TYPE", "-1"))
        if loai < 0:
            return None

        def ds(k):
            return [float(u) for u in kv.get(k, "").split(";") if u.strip()]
        return {"loai": loai, "ten": LOAI_CHON.get(loai, "Selection"), "x": float(kv["X"]), "y": float(kv["Y"]),
                "w": float(kv["W"]), "h": float(kv["H"]), "xs": ds("XS"), "ys": ds("YS")}
    except (KeyError, ValueError):
        return None


def khoi_chay_nhung(duong_imagej, anh, nm_px, thu_muc):
    """Chép ảnh sang thư mục ASCII, sinh macro mở ảnh, chạy ImageJ (hiện cửa sổ). Trả về dict mô tả."""
    import hrtem
    if not duong_imagej or not os.path.isfile(duong_imagej):
        raise FileNotFoundError("Chưa chọn đúng file ImageJ (ImageJ.exe, Fiji hoặc ij.jar).")
    th = os.path.join(thu_muc, time.strftime("nhung_%H%M%S"))
    os.makedirs(th, exist_ok=True)
    ext = os.path.splitext(anh)[1].lower() or ".png"
    ten = "vao" + ext
    shutil.copyfile(anh, os.path.join(th, ten))
    macro = os.path.join(th, "mo_anh.ijm")
    chon = os.path.join(th, "chon.txt")
    with open(macro, "w", encoding="ascii", newline="\n") as f:
        f.write(tao_macro_mo(os.path.join(th, ten), nm_px, chon, os.path.join(th, "lenh.txt")))
    proc = subprocess.Popen(hrtem.lenh_imagej(duong_imagej, macro, False), cwd=os.path.dirname(duong_imagej) or None)
    return {"proc": proc, "ten_anh": ten, "bat_dau": time.time(), "thu_muc": th, "chon": chon, "lenh": os.path.join(th, "lenh.txt")}


def liet_ke():
    """Danh sách cửa sổ Java (SunAwt*) đang hiện: [{hwnd, title, cls}]."""
    if not HOP_LE:
        return []
    kq = []

    def cb(h, _l):
        try:
            if _u.IsWindowVisible(h):
                b = ctypes.create_unicode_buffer(256)
                _u.GetClassNameW(h, b, 256)
                if b.value.startswith("SunAwt"):
                    t = ctypes.create_unicode_buffer(512)
                    _u.GetWindowTextW(h, t, 512)
                    kq.append({"hwnd": int(h), "title": t.value, "cls": b.value})
        except Exception:
            pass
        return True

    _u.EnumWindows(_PROC(cb), 0)
    return kq


def tim_cua_so(ten_anh, ds=None):
    """(hwnd thanh công cụ ImageJ, hwnd cửa sổ ảnh) nếu cả hai đã hiện, không thì None cho phần thiếu."""
    ds = liet_ke() if ds is None else ds
    thanh = anh = None
    goc = os.path.splitext(ten_anh)[0]
    for c in ds:
        if c["title"].strip() in TIEU_DE_CHINH and thanh is None:
            thanh = c["hwnd"]
        elif c["title"].startswith(goc) and anh is None:
            anh = c["hwnd"]
    return thanh, anh


class Nhung:
    """Quản lý các cửa sổ đã gắn vào khung để có thể tách ra nguyên trạng."""

    def __init__(self):
        self.cu = {}          # hwnd -> (style, exstyle, (l, t, r, b))

    def kich_thuoc(self, hwnd):
        r = wintypes.RECT()
        _u.GetWindowRect(hwnd, ctypes.byref(r))
        return r.right - r.left, r.bottom - r.top

    def gan(self, hwnd, host, x, y, w, h):
        if hwnd in self.cu or not _u.IsWindow(hwnd):
            return
        r = wintypes.RECT()
        _u.GetWindowRect(hwnd, ctypes.byref(r))
        st, ex = _u.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF, _u.GetWindowLongW(hwnd, GWL_EXSTYLE)
        self.cu[hwnd] = (st, ex, (r.left, r.top, r.right, r.bottom))
        moi = (st & ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINBOX | WS_MAXBOX)) | WS_CHILD | WS_VISIBLE
        _u.SetWindowLongW(hwnd, GWL_STYLE, ctypes.c_long(moi - (1 << 32) if moi >= (1 << 31) else moi).value)
        _u.SetParent(hwnd, host)
        _u.SetWindowPos(hwnd, None, int(x), int(y), int(w), int(h), SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOACTIVATE)

    def dat(self, hwnd, x, y, w, h):
        if hwnd in self.cu and _u.IsWindow(hwnd):
            _u.MoveWindow(hwnd, int(x), int(y), int(w), int(h), True)

    @staticmethod
    def an_hien(hwnd, hien):
        """Thu nhỏ (ẩn) hoặc khôi phục một cửa sổ mà không gắn vào khung."""
        if _u.IsWindow(hwnd):
            _u.ShowWindow(hwnd, 9 if hien else 6)

    def lam_moi(self, hwnd, x, y, w, h):
        """Java chỉ bố trí lại thanh công cụ khi nhận sự kiện đổi kích thước: đổi lệch 1 px rồi trả về, sau đó ép vẽ lại."""
        if hwnd in self.cu and _u.IsWindow(hwnd):
            _u.MoveWindow(hwnd, int(x), int(y), int(w) + 1, int(h) + 1, True)
            _u.MoveWindow(hwnd, int(x), int(y), int(w), int(h), True)
            _u.RedrawWindow(hwnd, None, None, 0x0001 | 0x0004 | 0x0080 | 0x0100)   # INVALIDATE|ERASE|ALLCHILDREN|UPDATENOW

    def tach_het(self):
        for hwnd, (st, ex, rc) in list(self.cu.items()):
            try:
                if _u.IsWindow(hwnd):
                    _u.SetParent(hwnd, None)
                    _u.SetWindowLongW(hwnd, GWL_STYLE, ctypes.c_long(st - (1 << 32) if st >= (1 << 31) else st).value)
                    _u.SetWindowPos(hwnd, None, rc[0], rc[1], rc[2] - rc[0], rc[3] - rc[1],
                                    SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
            except Exception:
                pass
        self.cu.clear()
