# -*- coding: utf-8 -*-
"""
Cửa sổ và nút cho GÓI NỘP BÀI (gắn vào giao diện chính, nhận `app` là CuaSoChinh):
  🧪 điều kiện đo · 🏷 vai trò mẫu · ✅ sẵn sàng nộp bài · 📐 mẫu tạp chí · 💾/📂 dự án · 🔗 đối chiếu chéo (tự lấy từ XRD/HR-TEM/XPS)
"""
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import nop_bai

DK_KHOA = [k for k, _ in nop_bai.DIEU_KIEN]

_RE_PT = re.compile(r"\b(pt|ruo2|iro2|pt/c|ir/c|ru/c)\b", re.I)
_RE_DC = re.compile(r"\b(bare|nf|cc|blank|undoped|pristine|control)\b", re.I)
_RE_SAU = re.compile(r"(sau|after|post|used)", re.I)


# ====================== THAM SỐ DÒNG LỆNH ======================
def args_nop_bai(app):
    """Điều kiện đo + vai trò/nhóm từng mẫu -> tham số cho tiến trình xử lý."""
    dk = {k: getattr(app, "dk_" + k).get().strip() for k in DK_KHOA if hasattr(app, "dk_" + k)}
    vt = {m["nhan"]: {"vai": m.get("vai_tro", ""), "nhom": m.get("nhom", "")} for m in app.muc if m.get("vai_tro") or m.get("nhom")}
    return ["--dieu-kien-json", json.dumps(dk, ensure_ascii=False), "--vai-tro-json", json.dumps(vt, ensure_ascii=False)]


def kiem_tra_thong_so(app):
    """Nhắc trước khi chạy (không chặn): thông số còn là mặc định hoặc thiếu làm báo cáo/bài yếu đi."""
    ln = []
    try:
        loai = app.loai.get()
        tho = loai.startswith(("LSV", "CV", "Tự", "Tafel"))
        if tho and not app.khong_qua_the.get() and (app.r_s.get().strip() in ("", "0", "0.0")):
            ln.append("Chưa bù iR (Rs = 0): quá thế và Tafel chưa hiệu chỉnh iR. Lấy Rs từ EIS ở tab Phân tích nếu có.")
        if (app.ph.get().strip(), app.eref.get().strip(), app.chia_i.get().strip()) == (str(app.MAC_DINH["ph"]), str(app.MAC_DINH["eref"]), str(app.MAC_DINH["chia_i"])) \
                and not getattr(app, "_da_nhac_mac_dinh", False):
            app._da_nhac_mac_dinh = True
            ln.append(f"pH ({app.ph.get()}), Eref ({app.eref.get()}) và hệ số chia dòng ({app.chia_i.get()} cm²) đang là giá trị mặc định: đúng với thí nghiệm này chưa?")
        if not app.tai_trong.get().strip() and tho:
            ln.append("Chưa nhập tải lượng xúc tác (nút 🧪 Điều kiện đo): đoạn Methods và mục 7.6 còn thiếu.")
        mt = [x.strip() for x in app.i_muc_tieu.get().replace(";", ",").split(",") if x.strip()]
        if mt and "10" not in [x.rstrip("0").rstrip(".") if "." in x else x for x in mt] and tho:
            ln.append("Mật độ dòng mục tiêu không có 10 mA/cm²: bài HER/OER thường cần quá thế tại 10 (tiêu chí 7.1).")
        n_it = sum(1 for m in app.muc if re.search(r"\bIT\b", str(m.get("loai_nhan", "")).upper()))
        if n_it >= 2 and app.chong.get() and not app.noi_tiep.get():
            ln.append(f"Có {n_it} file i-t vẽ chồng, đều bắt đầu từ 0 h. Nếu là các bước đo nối tiếp, tick 'Nối tiếp thời gian các đường i-t'.")
        if app.goi_nop_bai.get() and app.xuat_excel.get():
            thieu = [t for k, t in (("dien_ly", "điện ly"), ("tham_chieu", "điện cực tham chiếu"), ("doi_cuc", "điện cực đối"))
                     if not getattr(app, "dk_" + k).get().strip()]
            if thieu:
                ln.append("Chưa khai báo " + ", ".join(thieu) + " (nút 🧪 Điều kiện đo): đoạn Methods sẽ còn chỗ trống.")
    except Exception:  # noqa: BLE001 - phần nhắc không bao giờ được làm hỏng việc chạy
        return ln
    return ln


# ====================== 🧪 ĐIỀU KIỆN ĐO ======================
def mo_dieu_kien(app):
    top = tk.Toplevel(app.root)
    top.title("Điều kiện thí nghiệm (dùng cho đoạn Methods và mục 7.6)")
    f = ttk.Frame(top, padding=8)
    f.pack(fill="both", expand=True)
    cac = [(nhan, getattr(app, "dk_" + k)) for k, nhan in nop_bai.DIEU_KIEN] + [("Tải lượng xúc tác (mg/cm²)", app.tai_trong)]
    for r, (nhan, bien) in enumerate(cac):
        ttk.Label(f, text=nhan, anchor="w").grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=bien, width=46).grid(row=r, column=1, padx=6, pady=2)
    ttk.Label(f, foreground="#666", wraplength=520, justify="left",
              text="Các ô này được lưu cùng cài đặt. Khi chạy với 'Kèm gói nộp bài', app đưa chúng vào file methods_dien_hoa.txt "
                   "và sheet 'Kiểm tra nộp bài'. Rs nhập ở tab Phân tích.").grid(row=len(cac), column=0, columnspan=2, sticky="w", pady=6)

    def xong():
        app.luu_cai_dat()
        top.destroy()
    ttk.Button(f, text="Lưu", command=xong).grid(row=len(cac) + 1, column=1, sticky="e")


# ====================== 🏷 VAI TRÒ MẪU ======================
def goi_y_vai_tro(nhan):
    if _RE_PT.search(nhan):
        return nop_bai.VAI_TRO[2]
    if _RE_DC.search(nhan):
        return nop_bai.VAI_TRO[3]
    if _RE_SAU.search(nhan):
        return nop_bai.VAI_TRO[4]
    return ""


def mo_vai_tro(app):
    if not app.muc:
        messagebox.showinfo("Vai trò mẫu", "Chưa có file nào trong danh sách (tab Dữ liệu).", parent=app.root)
        return
    top = tk.Toplevel(app.root)
    top.title("Vai trò và nhóm của từng mẫu")
    tv = ttk.Treeview(top, columns=("nhan", "vai", "nhom"), show="headings", height=min(14, max(4, len(app.muc))))
    for c, t, w in (("nhan", "Mẫu", 220), ("vai", "Vai trò", 250), ("nhom", "Nhóm lặp lại", 130)):
        tv.heading(c, text=t)
        tv.column(c, width=w)
    tv.pack(fill="both", expand=True, padx=6, pady=6)
    tam = [dict(vai=m.get("vai_tro") or goi_y_vai_tro(m["nhan"]), nhom=m.get("nhom", "")) for m in app.muc]

    def ve():
        for i in tv.get_children():
            tv.delete(i)
        for k, (m, t) in enumerate(zip(app.muc, tam)):
            tv.insert("", "end", iid=str(k), values=(m["nhan"], t["vai"], t["nhom"]))
    ve()
    ff = ttk.Frame(top)
    ff.pack(fill="x", padx=6, pady=(0, 6))
    v_vai, v_nhom = tk.StringVar(), tk.StringVar()
    ttk.Combobox(ff, textvariable=v_vai, values=nop_bai.VAI_TRO, state="readonly", width=34).pack(side="left")
    ttk.Entry(ff, textvariable=v_nhom, width=14).pack(side="left", padx=6)

    def dat():
        for s in tv.selection():
            tam[int(s)] = dict(vai=v_vai.get(), nhom=v_nhom.get().strip())
        ve()

    def chon(_e=None):
        s = tv.selection()
        if s:
            v_vai.set(tam[int(s[0])]["vai"])
            v_nhom.set(tam[int(s[0])]["nhom"])
    tv.bind("<<TreeviewSelect>>", chon)
    ttk.Button(ff, text="Gán cho dòng chọn", command=dat).pack(side="left")

    def xong():
        for m, t in zip(app.muc, tam):
            m["vai_tro"], m["nhom"] = t["vai"], t["nhom"]
        app.lam_moi_bang()
        top.destroy()
    ttk.Button(top, text="Áp dụng", command=xong).pack(anchor="e", padx=6, pady=(0, 6))
    ttk.Label(top, foreground="#666", wraplength=560, justify="left",
              text="Cột 'Nhóm lặp lại': các mẫu cùng nhóm (cùng chữ) được tính trung bình ± độ lệch chuẩn. Vai trò gợi ý tự động từ tên mẫu, bạn sửa lại nếu sai.").pack(padx=6, pady=(0, 6))


# ====================== ✅ SẴN SÀNG NỘP BÀI ======================
def _doc_kiem_tra(thu_muc):
    """Đọc sheet 'Kiểm tra nộp bài' từ báo cáo Excel (hoặc CSV dự phòng)."""
    x = os.path.join(thu_muc, "bao_cao_tong_hop.xlsx")
    if os.path.exists(x):
        import openpyxl
        wb = openpyxl.load_workbook(x, data_only=True)
        if "Kiểm tra nộp bài" in wb.sheetnames:
            return [tuple("" if c is None else str(c) for c in r) for r in wb["Kiểm tra nộp bài"].iter_rows(min_row=2, values_only=True)]
    c = os.path.join(thu_muc, "bao_cao_tong_hop.csv")
    if os.path.exists(c):
        import csv
        with open(c, encoding="utf-8-sig", newline="") as f:
            ds, dang = [], False
            for r in csv.reader(f):
                if r and r[0].startswith("# "):
                    dang = r[0] == "# Kiểm tra nộp bài"
                    nho = 0
                    continue
                if dang and r:
                    nho += 1
                    if nho > 1:
                        ds.append(tuple(r))
            return ds
    return None


def mo_san_sang(app):
    hang = None
    try:
        hang = _doc_kiem_tra(app.thu_muc_ra.get())
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Sẵn sàng nộp bài", f"Không đọc được báo cáo:\n{e}", parent=app.root)
        return
    if not hang:
        messagebox.showinfo("Sẵn sàng nộp bài", "Chưa có sheet 'Kiểm tra nộp bài'.\nTick 'Xuất báo cáo Excel' và 'Kèm gói nộp bài' rồi bấm CHẠY.", parent=app.root)
        return
    top = tk.Toplevel(app.root)
    top.title("Sẵn sàng nộp bài?")
    dat = sum(1 for r in hang if r[2] == nop_bai.DAU_OK)
    ttk.Label(top, text=f"Đạt {dat}/{len(hang)} mục. Thiếu: {sum(1 for r in hang if r[2] == nop_bai.DAU_THIEU)} · Cần xem: {sum(1 for r in hang if r[2] == nop_bai.DAU_XEM)}",
              font=("", 11, "bold")).pack(anchor="w", padx=8, pady=6)
    tv = ttk.Treeview(top, columns=("ma", "nd", "tt", "lam"), show="headings", height=min(16, len(hang)))
    for c, t, w in (("ma", "Mục", 50), ("nd", "Nội dung", 330), ("tt", "Trạng thái", 80), ("lam", "Cần làm", 520)):
        tv.heading(c, text=t)
        tv.column(c, width=w, anchor="w")
    for k, r in enumerate(hang):
        tag = {"Đạt": "ok", "Thiếu": "thieu"}.get(r[2], "xem")
        tv.insert("", "end", values=r[:4], tags=(tag,))
    tv.tag_configure("ok", foreground="#14815a")
    tv.tag_configure("thieu", foreground="#c62828")
    tv.tag_configure("xem", foreground="#b26a00")
    tv.pack(fill="both", expand=True, padx=8, pady=(0, 8))


# ====================== 💾 / 📂 DỰ ÁN ======================
def luu_du_an(app):
    p = filedialog.asksaveasfilename(parent=app.root, title="Lưu dự án (cài đặt + danh sách mẫu + vai trò)", defaultextension=".echem",
                                     initialdir=os.path.abspath(app.thu_muc_ra.get()) if os.path.isdir(app.thu_muc_ra.get()) else None,
                                     filetypes=[("Dự án Echem", "*.echem"), ("JSON", "*.json")])
    if not p:
        return
    cd = {k: app.gia_tri(k) for k in app.KHOA_DU_AN}
    muc = [{k: m.get(k, "") for k in ("path", "nhan", "mau", "nhom", "vai_tro", "loai_nhan")} for m in app.muc]
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"ver": 1, "cai_dat": cd, "muc": muc}, f, ensure_ascii=False, indent=1)
    except OSError as e:
        messagebox.showerror("Dự án", f"Không ghi được:\n{e}", parent=app.root)
        return
    app.q.put(f"Đã lưu dự án: {p}\n")


def mo_du_an(app, p=None):
    p = p or filedialog.askopenfilename(parent=app.root, title="Mở dự án", filetypes=[("Dự án Echem", "*.echem *.json"), ("Tất cả", "*.*")])
    if not p:
        return
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        cd, muc = d["cai_dat"], d["muc"]
    except (OSError, ValueError, KeyError) as e:
        messagebox.showerror("Dự án", f"Không đọc được dự án:\n{e}", parent=app.root)
        return
    for k, v in cd.items():
        if k in app.KHOA_DU_AN:
            var = getattr(app, k)
            var.set(bool(v) if isinstance(var, tk.BooleanVar) else str(v))
    thieu = [m["path"] for m in muc if not os.path.isfile(m["path"])]
    app.muc = [dict(m) for m in muc]
    app.lam_moi_bang()
    app.cap_nhat_trang_thai()
    app.luu_cai_dat()
    app.q.put(f"Đã mở dự án: {p} ({len(muc)} mẫu)\n")
    if thieu:
        messagebox.showwarning("Dự án", "Không còn thấy các file:\n" + "\n".join(thieu[:8]) + ("\n..." if len(thieu) > 8 else ""), parent=app.root)


# ====================== 🔗 ĐỐI CHIẾU CHÉO ======================
def _song(obj):
    try:
        return obj is not None and obj.w.winfo_exists()
    except Exception:  # noqa: BLE001
        return False


def thu_so_lieu(app):
    """Lấy số liệu từ các công cụ XRD/HR-TEM/XPS đang mở -> dict ô nhập + thông báo."""
    kq, tin = {}, []
    x = getattr(app, "cs_xrd", None)
    if _song(x) and getattr(x, "kq", None):
        r = x.kq[0]
        dong = []
        for rec in r.get("gan", []):
            p = rec.get("peak", {})
            if rec.get("loai") == "pha":
                dong.append(f"{rec.get('tt_c', p.get('tt', 0)):.2f} {p.get('fwhm', 0):.3f} {rec.get('nhan', '')}".strip())
        if not dong:
            dong = [f"{rec['peak']['tt']:.2f} {rec['peak'].get('fwhm', 0):.3f}" for rec in r.get("gan", [])[:12]]
        kq["xrd"] = "\n".join(dong)
        kq["lam"] = r.get("lam")
        tin.append(f"XRD ({len(dong)} đỉnh của mẫu đầu)")
    h = getattr(app, "cs_hrtem", None)
    if _song(h) and getattr(h, "do_ds", None):
        kq["hrtem"] = "\n".join(f"{m['d']:.4f} {m.get('pha', '')} {m.get('hkl', '')}".strip() for m in h.do_ds if m.get("d"))
        tin.append(f"HR-TEM ({len(h.do_ds)} phép đo)")
    p = getattr(app, "cs_xps", None)
    if _song(p) and getattr(p, "kq", None):
        try:
            kq["xps"] = "\n".join(f"{c['vt']:.2f} {c['ten']}" for c in p.kq["fit"]["thanh_phan"])
            tin.append(f"XPS ({len(p.kq['fit']['thanh_phan'])} thành phần)")
        except (KeyError, TypeError):
            pass
    return kq, tin


def mo_doi_chieu(app):
    import doi_chieu
    top = tk.Toplevel(app.root)
    top.title("Đối chiếu chéo & trước/sau thử bền")
    o = {}
    mau = [("xrd", "XRD: 2θ [FWHM] [pha(hkl)]", "44.5 0.45 Ni(111)\n51.8 0.50 Ni(200)"), ("hrtem", "HR-TEM: d (nm hoặc Å) [pha(hkl)]", "0.203 Ni(111)"),
           ("tem", "TEM: kích thước hạt (nm)", ""), ("xps", "XPS: BE (eV) [ghi chú]", "852.6 Ni0"),
           ("truoc_xrd", "Trước thử bền: đỉnh XRD 2θ", ""), ("sau_xrd", "Sau thử bền: đỉnh XRD 2θ", ""),
           ("truoc_xps", "Trước thử bền: BE XPS", ""), ("sau_xps", "Sau thử bền: BE XPS", "")]
    f = ttk.Frame(top)
    f.pack(fill="both", expand=True, padx=6, pady=6)
    for k, (kh, nhan, vd) in enumerate(mau):
        r, c = divmod(k, 4)
        ff = ttk.Frame(f)
        ff.grid(row=r, column=c, padx=3, pady=2, sticky="n")
        ttk.Label(ff, text=nhan, wraplength=190).pack(anchor="w")
        t = tk.Text(ff, width=24, height=6)
        t.pack()
        t.insert("1.0", vd)
        o[kh] = t
    ff = ttk.Frame(top)
    ff.pack(fill="x", padx=6)
    lam = tk.StringVar(value="1.5406")
    tt = tk.StringVar(value="")
    ttk.Label(ff, text="λ (Å):").pack(side="left")
    ttk.Entry(ff, textvariable=lam, width=8).pack(side="left", padx=4)
    ra = tk.Text(top, width=120, height=16, font=("Consolas", 9), wrap="word")

    def lay():
        kq, tin = thu_so_lieu(app)
        for k in ("xrd", "hrtem", "xps"):
            if k in kq:
                o[k].delete("1.0", "end")
                o[k].insert("1.0", kq[k])
        if kq.get("lam"):
            lam.set(f"{kq['lam']:.4f}")
        tt.set("Đã lấy từ: " + ", ".join(tin) if tin else "Không thấy công cụ XRD/HR-TEM/XPS nào đang mở có kết quả. Mở công cụ, phân tích xong rồi bấm lại.")

    def chay():
        try:
            txt, _ = doi_chieu.tao_bao_cao(float(lam.get().replace(",", ".")), *[o[k].get("1.0", "end") for k in
                                           ("xrd", "hrtem", "tem", "xps", "truoc_xrd", "sau_xrd", "truoc_xps", "sau_xps")])
        except Exception as e:  # noqa: BLE001
            txt = f"Không đối chiếu được: {e}"
        ra.delete("1.0", "end")
        ra.insert("1.0", txt)

    def chep():
        top.clipboard_clear()
        top.clipboard_append(ra.get("1.0", "end"))
    ttk.Button(ff, text="⟳ Lấy từ công cụ đang mở", command=lay).pack(side="left", padx=8)
    ttk.Button(ff, text="Đối chiếu", command=chay).pack(side="left")
    ttk.Button(ff, text="📋", width=4, command=chep).pack(side="left", padx=4)
    ttk.Label(ff, textvariable=tt, foreground="#555").pack(side="left", padx=6)
    ra.pack(fill="both", expand=True, padx=6, pady=6)
    lay()
