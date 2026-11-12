# -*- coding: utf-8 -*-
"""
HƯỚNG DẪN THEO PHÉP ĐO: gõ tên (vd "LSV", "tafel", "ragone", "xps") → các bước làm cụ thể trong app, công thức, tiêu chí, lỗi thường gặp.
Nội dung bám đúng tên nút/ô trong app và đúng ngưỡng cảnh báo của code (canh_bao.py, nop_bai.py, ...).
Mục ghi "(kiến thức chung)" là quy ước/giá trị tham khảo trong điện hóa, không phải ngưỡng do app áp đặt.
Lõi không dùng tkinter (dễ kiểm thử); cửa sổ hiển thị nằm ở huong_dan_gui.py.
"""
import difflib
import re
import unicodedata


def chuan_hoa(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")
    return re.sub(r"[^a-z0-9+/ ]+", " ", s.replace("-", " ").replace("_", " ")).strip()


def _g(ctx, k, mac="?"):
    v = (ctx or {}).get(k)
    return mac if v in (None, "") else v


# ====================== NỘI DUNG ======================
CHUNG_BUOC_NAP = ["Tab Dữ liệu ▸ bấm Thêm file... hoặc Thêm thư mục... (hoặc kéo-thả file vào bảng). Mỗi file là một dòng; bấm đúp để đổi Nhãn, Nhóm lặp, Màu.",
                  "Cột Loại phép đo tự điền; sai thì chọn lại ở nhóm Phép đo (ô Loại)."]


def _thuc_te_quy_doi(c):
    dong = [f"E (V vs RHE) = E đo + {_g(c, 'nernst', '0.059')} × {_g(c, 'ph')} + {_g(c, 'eref')}"]
    if (c or {}).get("khong_rhe"):
        dong = ["Đang tick 'Không quy đổi RHE': giữ nguyên E đo (điện thế tế bào, hai điện cực)."]
    dong.append(f"I (mA/cm²) = i(A) × 1000 × {_g(c, 'nhan_i')} ÷ {_g(c, 'chia_i')}")
    if str((c or {}).get("r_s") or "0") not in ("0", "0.0", ""):
        dong.append(f"Bù iR đang bật: Rs = {c['r_s']} Ω, bù {_g(c, 'ir_pct')} % → E_thật = E − i·Rs·{_g(c, 'ir_pct')}/100")
    return dong


def _so_file(c, *loai):
    n = sum(((c or {}).get("so_file") or {}).get(k, 0) for k in loai)
    return f"Trong danh sách file hiện tại có {n} file {'/'.join(loai)}." if (c or {}).get("so_file") is not None else ""


TOPICS = [
    dict(id="lsv", ten="LSV: quét thế tuyến tính (đường phân cực)", loai_app="LSV",
         bi_danh=["lsv", "quet the tuyen tinh", "phan cuc", "polarization", "linear sweep", "qua the", "overpotential", "oer", "her", "hoat tinh xuc tac", "eta"],
         tom_tat="Điện thế quét một chiều, ghi dòng. App đổi sang RHE và mA/cm², vẽ đường E–I, lấy điện thế/quá thế tại mật độ dòng chuẩn (mặc định 10 mA/cm²), "
                 "Tafel và so sánh các mẫu.",
         du_lieu=["File thô .txt/.csv/.dat, 3 cột: E (V), i (A), T (s); dòng đầu có thể là 'CSStudioFile,...'. Số liệu nhiều điểm, E đổi MỘT chiều (nếu E đảo chiều thì app coi là CV).",
                  "Nên có file nền trần (không xúc tác) và Pt/C hoặc RuO₂/IrO₂ đo cùng điều kiện để so sánh."],
         buoc=CHUNG_BUOC_NAP + [
             "Nhóm Quy đổi điện thế: nhập pH và Eref (mặc định 13.8 và 0.098 V). Nhóm Quy đổi dòng: nhân/chia sao cho I = i × 1000 × nhân ÷ chia, 'chia' là diện tích điện cực (cm²). "
             "Đo 2 điện cực thì tick 'Không quy đổi RHE'.",
             "(Nên làm) Nhóm Bù iR: nhập Rs (Ω) hoặc bấm 'Lấy Rs từ file EIS...' rồi đặt % bù.",
             "Tab Phân tích ▸ nhóm So sánh mẫu: ô 'I mục tiêu (mA/cm²)' (mặc định 10; nhập nhiều mức bằng dấu phẩy, vd 10, 100) và 'E cân bằng (V)' (OER 1.23 V; HER đặt 0 V). "
             "Tick 'Không tính quá thế' nếu không có E cân bằng (vd oxi hóa glucose).",
             "Tab Xuất ▸ chọn Thư mục kết quả; tick 'Xuất báo cáo Excel'.",
             "Bấm 'Xem trước hình' để xem nhanh bằng Matplotlib; hài lòng thì bấm '▶ CHẠY XỬ LÝ & VẼ' (vẽ Origin nếu đã tick 'Vẽ bằng Origin' ở tab Hình).",
             "Mở báo cáo (📊 ở tab Xuất): sheet 'CV-LSV' có E tại 10 mA/cm², quá thế (mV), I max; sheet 'Cảnh báo' liệt kê điều cần kiểm tra.",
             "Muốn Tafel: chọn Loại = Tafel (xem mục Tafel); muốn độ bền: xem mục i-t."],
         phep_tinh=[("Quy đổi điện thế", "E(RHE) = E đo + k × pH + Eref", "k (ô 'k (V/pH)') mặc định 0.059 như công thức Excel hay dùng; 0.0592 V (2.303RT/F ở 25 °C) chính xác hơn, chênh ≈ 2.8 mV ở pH 13.8."),
                    ("Quy đổi dòng", "I (mA/cm²) = i × 1000 × nhân ÷ chia", "i là dòng đo (A)."),
                    ("Quá thế", "η = E(RHE) − E cân bằng", "OER: E cân bằng = 1.23 V; η10 là quá thế tại 10 mA/cm²."),
                    ("Bù iR", "E_thật = E_đo − i × Rs × (% bù/100)", "i là dòng đo thực (A), chưa chia diện tích.")],
         tieu_chi=["Mẫu có η tại dòng mục tiêu THẤP hơn thì xếp hạng cao hơn (sheet 'So sánh mẫu').",
                   "Cảnh báo tự động: khoảng E < 0.03 V; E sau quy đổi ngoài −1.5…3.5 V vs RHE (→ kiểm pH, Eref); dòng lớn nhất > 5000 hoặc < 10⁻⁴ mA/cm² (→ kiểm hệ số nhân/chia).",
                   "Tiêu chí nộp bài của app: có quá thế tại 10 mA/cm² (7.1), có mẫu đối chứng (5.3) và chuẩn Pt/C hoặc RuO₂/IrO₂ (7.7), có dòng ≥ 500 mA/cm² (9.3), lặp ≥ 3 điện cực (5.5).",
                   "(Kiến thức chung) Tốc độ quét chậm (vài mV/s) làm giảm dòng điện dung; nên báo rõ tốc độ quét và bù iR."],
         loi=["Quá thế/điện thế lệch nhiều so với kỳ vọng → sai pH hoặc Eref.", "Dòng lớn/nhỏ bất thường → sai hệ số nhân/chia (diện tích).",
              "Đường LSV có pic ở điện thế thấp (vd Cu ~0.87 V): Tafel sẽ chỉ lấy nhánh đi lên cuối cùng, nhưng vẫn nên mô tả pic trong bài."],
         ket_qua=["Hình 'So_sanh_LSV' (Origin/Matplotlib), CSV *_xuly.csv và *_thongso.csv, bao_cao_tong_hop.xlsx (sheet CV-LSV, So sánh mẫu, Cảnh báo, Thông tin)."],
         xem_them=["tafel", "bu ir", "so sanh", "it", "nop bai", "quy doi"],
         thuc_te=lambda c: _thuc_te_quy_doi(c) + [f"I mục tiêu = {_g(c, 'i_muc_tieu')} mA/cm²; E cân bằng = {_g(c, 'e_can_bang')} V", _so_file(c, "LSV")]),

    dict(id="cv", ten="CV: quét thế vòng", loai_app="CV",
         bi_danh=["cv", "cyclic voltammetry", "quet the vong", "von ampe vong", "epa", "epc", "e1/2", "ipa", "ipc"],
         tom_tat="Điện thế quét qua lại. App dùng CHU KỲ CUỐI (hoặc chu kỳ bạn chọn), tách nhánh anodic/cathodic và tính Epa, Ipa, Epc, Ipc, ΔEp, E1/2, |Ipa/Ipc|.",
         du_lieu=["File thô 3 cột E, i, T như LSV. Nên chạy ≥ 3 chu kỳ để đường cong ổn định."],
         buoc=CHUNG_BUOC_NAP + [
             "Quy đổi điện thế/dòng như mục LSV.",
             "Tab Dữ liệu ▸ nhóm Phép đo: ô 'Chu kỳ CV' (trống = chu kỳ cuối).",
             "Tick 'Vẽ chồng các file cùng loại' để các CV chung một hình.",
             "Bấm 'Xem trước hình' rồi '▶ CHẠY XỬ LÝ & VẼ'.",
             "Mở báo cáo: sheet 'CV-LSV' có cột 'Chu kỳ dùng' (vd 3/3), Epa, Ipa, Epc, Ipc, dEp, E1/2, |Ipa/Ipc|, tốc độ quét (mV/s).",
             "Muốn ECSA: dùng nhiều CV ở các tốc độ quét khác nhau (xem mục ECSA)."],
         phep_tinh=[("Độ tách pic", "ΔEp = Epa − Epc", ""), ("Thế bán sóng", "E1/2 = (Epa + Epc)/2", ""), ("Tỉ số dòng pic", "|Ipa/Ipc|", ""),
                    ("Tốc độ quét", "ν = |dE/dt|", "App tự suy ra từ E theo T.")],
         tieu_chi=["Cảnh báo tự động: chu kỳ cuối bị cụt (< 60 % số điểm trung vị) → app dùng chu kỳ trước đó; biên độ dòng giữa 2 chu kỳ cuối lệch > 20 % → chưa ổn định, chạy thêm chu kỳ; chỉ có 1 chu kỳ → chu kỳ đầu thường chưa ổn định.",
                   "(Kiến thức chung) Cặp thuận nghịch 1 electron ở 25 °C: ΔEp ≈ 59 mV và |Ipa/Ipc| ≈ 1."],
         loi=["Dùng chu kỳ 1: đường cong chưa ổn định → đặt 'Chu kỳ CV' hoặc chạy thêm chu kỳ.", "File CV bị cụt ở cuối: app tự bỏ chu kỳ cụt nhưng nên đo lại cho đủ."],
         ket_qua=["Hình CV chồng, *_xuly.csv, sheet CV-LSV."], xem_them=["ecsa", "lsv", "bu ir"],
         thuc_te=lambda c: _thuc_te_quy_doi(c) + [f"Chu kỳ đang chọn: {_g(c, 'chu_ky', 'chu kỳ cuối')}", _so_file(c, "CV")]),

    dict(id="it", ten="i-t (chronoamperometry): độ bền dòng theo thời gian", loai_app="IT",
         bi_danh=["it", "i t", "i-t", "chronoamperometry", "do ben", "on dinh", "stability", "suy giam", "giu dong", "durability", "ca"],
         tom_tat="Giữ điện thế không đổi, ghi dòng theo thời gian (giờ). App loại đoạn nhiễu, tính % giữ dòng, tốc độ suy giảm, và có thể nối tiếp nhiều đường i-t thành một trục thời gian.",
         du_lieu=["File thô E, i, T với E gần như không đổi (dao động < 0.005 V thì app nhận là i-t)."],
         buoc=CHUNG_BUOC_NAP + [
             "Quy đổi dòng như mục LSV (I theo mA/cm²).",
             "Muốn nối các file đo liên tiếp: tab Dữ liệu ▸ tick 'Nối tiếp thời gian các đường i-t (cộng dồn)' (mỗi đường bắt đầu ngay sau đường trước).",
             "Sắp thứ tự file bằng ▲ ▼ trước khi chạy (thứ tự = thứ tự nối).",
             "Bấm '▶ CHẠY XỬ LÝ & VẼ'; xem sheet 'IT' trong báo cáo.",
             "Hiệu suất Faraday: nhập thể tích khí ở nhóm 'Hiệu suất Faraday (file IT)' (xem mục FE)."],
         phep_tinh=[("Giữ dòng", "giữ (%) = 100 × I̅_cuối / I̅_đầu", "Trung bình trong cửa sổ 200 s đầu và 200 s cuối."),
                    ("Suy giảm", "suy giảm (%) = 100 − giữ (%)", ""),
                    ("Tốc độ suy giảm", "−100 × độ dốc hồi quy tuyến tính của |I| theo giờ ÷ |I̅_đầu| (%/h)", ""),
                    ("Điểm nhiễu", "điểm có E lệch > 0.01 V so với E trung vị, và 30 s sau đó", "Thời gian nhiễu đã loại ghi ở cột 'nhieu_da_loai (h)'.")],
         tieu_chi=["Tiêu chí nộp bài của app (7.4): độ bền dài nhất ≥ 200 h là mốc điểm cao, tối đa ở ≥ 500 h; báo cáo giờ đo và % giữ dòng.",
                   "Cảnh báo tự động: > 50 % điểm bị coi là nhiễu; dòng đổi dấu trong lúc đo."],
         loi=["Nhiều điểm nhiễu → điện thế giữ không ổn định hoặc mới đổi điện thế.", "Nối tiếp sai thứ tự → thời gian cộng dồn sai; kiểm tra bảng file."],
         ket_qua=["Hình i-t (T theo giờ), *_thongso.csv, sheet IT có E_giu, thoi_gian (h), giu_dong (%), suy_giam (%), toc_do_suy_giam (%/h)."],
         xem_them=["fe", "nop bai", "lsv"], thuc_te=lambda c: [_so_file(c, "IT"), f"Nối tiếp thời gian: {'BẬT' if (c or {}).get('noi_tiep') else 'tắt'}"]),

    dict(id="eis", ten="EIS: phổ tổng trở", loai_app="EIS",
         bi_danh=["eis", "tong tro", "pho tong tro", "impedance", "nyquist", "rs", "rct", "cpe", "randles", "tro khang"],
         tom_tat="Đo Z' và −Z'' theo tần số. App vẽ Nyquist, ước lượng Rs, và (nếu tick) fit mạch Rs + (Rct ‖ CPE).",
         du_lieu=["File EIS (.z60 hoặc text có 'Freq (Hz)', Z', Z''): app đọc tần số, Z' và −Z''. Z'' được đổi dấu để vẽ −Z'' dương."],
         buoc=CHUNG_BUOC_NAP + [
             "Chọn Loại = EIS (hoặc để tự nhận dạng).",
             "Muốn fit mạch tương đương: tab Phân tích ▸ nhóm EIS ▸ tick 'Fit mạch Rs + (Rct ‖ CPE)'.",
             "Muốn bù iR: tab Dữ liệu ▸ nhóm Bù iR ▸ 'Lấy Rs từ file EIS...' (lấy Z' ở điểm gần trục thực nhất trong 1/3 vùng tần số cao).",
             "Bấm '▶ CHẠY XỬ LÝ & VẼ'; xem hình Nyquist (kèm đường fit) và sheet 'EIS'."],
         phep_tinh=[("Mô hình Randles–CPE", "Z(ω) = Rs + 1 / (1/Rct + Q·(jω)ⁿ)", "Fit Levenberg–Marquardt, nhiều điểm khởi đầu, trọng số 1/|Z|; n giới hạn 0.3–1."),
                    ("Điện dung hiệu dụng (Brug)", "C_eff = Q^(1/n) · (1/Rs + 1/Rct)^((n−1)/n)", ""),
                    ("Thông số nhanh", "Rs ≈ Z' ở tần số cao nhất; R_tổng − Rs = Z'(f thấp nhất) − Rs", "")],
         tieu_chi=["Cảnh báo tự động: có Z' âm (cảm kháng/cáp); dải tần f_max/f_min < 100 (quá hẹp).",
                   "Mô hình hiện chỉ có một cung, chưa có Warburg hay nhiều cung: không dùng cho phổ có đuôi khuếch tán rõ hoặc nhiều hằng số thời gian."],
         loi=["Rs âm hoặc quá nhỏ bất thường → kiểm tra dây dẫn, tiếp xúc.", "Fit kém (RMS lớn) → phổ không đúng mạch một cung."],
         ket_qua=["Hình Nyquist, sheet EIS (Rs, Rct, Q, n, C_eff, sai số RMS khi fit)."], xem_them=["bu ir", "lsv"],
         thuc_te=lambda c: [_so_file(c, "EIS")]),

    dict(id="tafel", ten="Tafel: hệ số Tafel (mV/dec)", loai_app="Tafel",
         bi_danh=["tafel", "he so tafel", "mv/dec", "dong hoc", "kinetics", "slope"],
         tom_tat="Fit E theo log|J| trong một vùng dòng (hoặc vùng điện thế) để lấy độ dốc Tafel b (mV/dec).",
         du_lieu=["LSV (hoặc CV một nhánh) đã quy đổi. Chọn vùng nơi E–log J tuyến tính."],
         buoc=CHUNG_BUOC_NAP + [
             "Chọn Loại = Tafel (ô Loại ở tab Dữ liệu).",
             "Tab Phân tích ▸ nhóm Tafel: chọn 'Theo dòng (mA/cm²)' và nhập từ–đến (mặc định 9–11), hoặc 'Theo điện thế (V)' và nhập E từ–đến.",
             "Bấm 'Xem trước hình' để kiểm tra điểm đo và đường fit; chỉnh vùng nếu đường không thẳng.",
             "Bấm '▶ CHẠY XỬ LÝ & VẼ'; sheet 'Tafel' có hệ số mV/dec; hình Tafel ghi mV/dec trong chú thích."],
         phep_tinh=[("Phương trình Tafel", "E = a + b · log₁₀|J|", "b (mV/dec) là độ dốc, J = mật độ dòng."),
                    ("Vùng dòng", "lấy các điểm có |I| trong [từ, đến]; nếu thiếu thì lấy điểm gần giá trị giữa vùng", "LSV có pic nhỏ: chỉ lấy NHÁNH đi lên sau cùng qua giá trị 'từ'.")],
         tieu_chi=["Cảnh báo tự động: < 5 điểm trong vùng; R² của đường Tafel < 0.98; |b| > 500 mV/dec (vùng sai hoặc bị giới hạn chuyển khối/iR); |b| < 20 mV/dec (kiểm tra lại dữ liệu).",
                   "Hệ số Tafel dùng để so sánh cơ chế/động học giữa các mẫu, không có ngưỡng 'đạt/trượt'; nên bù iR trước khi fit."],
         loi=["Vùng chọn gồm cả dòng điện dung hoặc vùng chuyển khối → độ dốc sai.", "Quên bù iR → b bị tăng ở dòng lớn."],
         ket_qua=["Hình Tafel, *_Tafel CSV, sheet Tafel."], xem_them=["lsv", "bu ir"],
         thuc_te=lambda c: [f"Vùng đang đặt: {'theo dòng' if (c or {}).get('tafel_che_do', 'dong') == 'dong' else 'theo điện thế'} "
                            f"{_g(c, 'tafel_min') if (c or {}).get('tafel_che_do', 'dong') == 'dong' else _g(c, 'tafel_e_min')} – "
                            f"{_g(c, 'tafel_max') if (c or {}).get('tafel_che_do', 'dong') == 'dong' else _g(c, 'tafel_e_max')}"]),

    dict(id="ecsa", ten="ECSA / Cdl: diện tích hoạt động điện hóa", loai_app="ECSA (nhiều file CV)",
         bi_danh=["ecsa", "cdl", "dien tich hoat dong", "dien dung lop kep", "double layer", "roughness", "rf", "dien tich dien hoa"],
         tom_tat="Từ các CV ở nhiều tốc độ quét trong vùng KHÔNG có phản ứng Faraday: lấy (Ja − Jc)/2 tại một điện thế, fit theo tốc độ quét → Cdl; ECSA = Cdl / Cs.",
         du_lieu=["≥ 2 file CV của cùng một mẫu ở các tốc độ quét khác nhau (khuyến nghị ≥ 5), vùng điện thế phẳng, không có pic oxi hóa–khử."],
         buoc=["Tab Dữ liệu ▸ Thêm file... (hoặc Thêm thư mục...): thêm các CV của MỘT mẫu.",
               "Chọn Loại = 'ECSA (nhiều file CV)', hoặc bấm 'Thêm các CV → ECSA' khi app gợi ý.",
               "Tab Phân tích ▸ nhóm ECSA: ô 'Cs (mF/cm²)' (mặc định 0.040) và 'E lấy dòng (V)'.",
               "Bấm 'Chọn E bằng đồ thị...': bấm/kéo chuột chọn điện thế (vạch đỏ) trong vùng phẳng; Cdl, R², ECSA tính lại ngay. 'Gợi ý E có R² cao nhất' chỉ là gợi ý.",
               "Trong cùng cửa sổ, bỏ tick tốc độ quét lệch khỏi đường thẳng (file không bị xóa) rồi bấm 'Dùng kết quả này'.",
               "Bấm '▶ CHẠY XỬ LÝ & VẼ'; sheet 'ECSA' và 'ECSA - điểm' có Cdl, R², ECSA."],
         phep_tinh=[("Dòng điện dung", "J_c = (J_a − J_c)/2 tại E đã chọn", ""), ("Cdl", "Cdl = độ dốc của J_c theo tốc độ quét v (V/s), đơn vị mF/cm²", ""),
                    ("ECSA", "ECSA = Cdl / Cs", "Cs là điện dung riêng của bề mặt phẳng (mặc định 0.040 mF/cm², kiến thức chung cho điện ly kiềm; hãy ghi nguồn giá trị bạn dùng)."),
                    ("Hệ số nhám", "RF = ECSA / diện tích hình học", "")],
         tieu_chi=["Cảnh báo tự động: R² < 0.98 (cảnh báo), R² < 0.90 (nặng); Ja và Jc lệch đối xứng; một điểm tốc độ quét lệch (app gợi ý bỏ nếu R² tăng > 0.02); còn 2 điểm thì R² luôn = 1 (vô nghĩa).",
                   "Tiêu chí nộp bài (7.3): có ECSA/Cdl."],
         loi=["Chọn E ở vùng có pic oxi hóa–khử → dòng Faraday lẫn vào.", "Tốc độ quét quá cao → méo CV, J không còn tuyến tính theo v."],
         ket_qua=["Hình CV đa tốc độ, hình Cdl, *_ECSA.csv và *_ECSA_diem.csv."], xem_them=["cv", "tof"],
         thuc_te=lambda c: [f"Cs đang đặt: {_g(c, 'cs')} mF/cm²; E lấy dòng: {_g(c, 'e_ecsa', '(chưa chọn)')} V", _so_file(c, "CV")]),

    dict(id="bu ir", ten="Bù iR (hiệu chỉnh sụt áp Rs)", loai_app=None,
         bi_danh=["bu ir", "ir", "ir compensation", "rs", "dien tro dung dich", "sut ap", "hieu chinh ir"],
         tom_tat="Đo điện thế bị lệch một lượng i·Rs do điện trở dung dịch. App trừ phần này trước khi tính quá thế và Tafel.",
         du_lieu=["Rs (Ω): nhập tay hoặc lấy từ file EIS đo cùng điều kiện."],
         buoc=["Tab Dữ liệu ▸ nhóm Bù iR.", "Bấm 'Lấy Rs từ file EIS...' và chọn file EIS (hoặc gõ Rs vào ô 'Rs (Ω)').", "Ô 'bù (%)': mặc định 100.",
               "Chạy xử lý: app báo mức dịch điện thế tối đa để bạn kiểm tra."],
         phep_tinh=[("E thật", "E_thật = E_đo − i × Rs × (% bù / 100)", "i là dòng đo thực (A), CHƯA chia diện tích."),
                    ("Rs từ EIS", "Z' tại điểm gần trục thực nhất trong 1/3 vùng tần số cao nhất", "")],
         tieu_chi=["Phải báo cáo có bù hay không, Rs và % bù (mục 7.6 của tiêu chí nộp bài)."],
         loi=["Rs lấy từ điều kiện khác (nồng độ, nhiệt độ, khoảng cách điện cực) → bù sai."], ket_qua=["Sheet 'Thông tin' ghi Rs và % bù."],
         xem_them=["eis", "lsv", "tafel"], thuc_te=lambda c: _thuc_te_quy_doi(c)),

    dict(id="so sanh", ten="So sánh mẫu, xếp hạng, nhóm lặp (TB ± SD)", loai_app=None,
         bi_danh=["so sanh", "xep hang", "nhom lap", "lap lai", "sd", "trung binh", "ranking", "so sanh mau"],
         tom_tat="Bảng xếp hạng và biểu đồ cột các mẫu theo quá thế (hoặc điện thế) tại dòng mục tiêu, kèm Tafel; gộp các lần đo lặp thành trung bình ± SD.",
         du_lieu=["Các LSV của nhiều mẫu; các lần đo lặp đặt cùng 'Nhóm lặp' (hoặc tên Mau-1, Mau-2, Mau-3)."],
         buoc=["Thêm các file LSV, đặt Nhãn từng mẫu.", "Lặp lại: bấm đúp cột 'Nhóm lặp' (hoặc nút 'Đặt nhóm lặp') và gõ cùng tên cho các lần đo của một mẫu.",
               "Tab Phân tích ▸ So sánh mẫu: tick 'Bảng xếp hạng + biểu đồ cột'; đặt 'I mục tiêu' và 'E cân bằng'.",
               "Chạy; xem so_sanh_tong_hop.png/.csv và sheet 'So sánh mẫu'."],
         phep_tinh=[("Hạng", "η nhỏ nhất = hạng 1", ""), ("Trung bình ± SD", "SD = độ lệch chuẩn mẫu (n − 1)", "Nhóm chỉ có 1 mẫu không có SD.")],
         tieu_chi=["Tiêu chí nộp bài (5.5): lặp ≥ 3 điện cực độc lập."], loi=["Đặt nhãn khác gốc tên → app không tự nhận nhóm lặp."],
         ket_qua=["so_sanh_tong_hop.png/.csv, sheet 'So sánh mẫu', 'Lặp lại (TB ± SD)'."], xem_them=["lsv", "nop bai"]),

    dict(id="fe", ten="Hiệu suất Faraday (FE) từ i-t", loai_app="IT",
         bi_danh=["fe", "hieu suat faraday", "faradaic efficiency", "faraday", "toc do sinh khi", "gas", "h2", "o2"],
         tom_tat="So lượng khí đo được (mL) với lượng khí lý thuyết từ điện lượng Q = ∫|i|dt.",
         du_lieu=["File i-t của từng mẫu và thể tích khí thu được (mL), nhiệt độ, áp suất."],
         buoc=["Thêm các file i-t theo ĐÚNG thứ tự mẫu.", "Tab Phân tích ▸ nhóm 'Hiệu suất Faraday (file IT)': nhập 'V khí (mL, mỗi mẫu IT)' cách nhau dấu phẩy theo thứ tự file IT.",
               "Nhập n e⁻ (H₂ = 2, O₂ = 4), T (°C), P (kPa); tick 'Trừ áp suất hơi nước' nếu khí được thu trên nước.", "Chạy; xem sheet FE (FE %, tốc độ sinh khí mmol cm⁻² h⁻¹)."],
         phep_tinh=[("Số mol khí", "n_khí = P_khí · V / (R·T), P_khí = P − P_hơi nước", ""), ("Điện lượng", "Q = ∫|i| dt (C)", ""),
                    ("FE", "FE (%) = n_e · F · n_khí / Q × 100", "F = 96485.33 C/mol"), ("Tốc độ sinh khí", "n_khí / (diện tích × thời gian) (mmol cm⁻² h⁻¹)", "Diện tích = hệ số chia dòng.")],
         tieu_chi=["Cảnh báo tự động: FE > 105 % hoặc < 50 %."], loi=["Sai thứ tự thể tích với file; quên trừ hơi nước khi thu khí trên nước."],
         ket_qua=["Sheet FE trong báo cáo."], xem_them=["it"]),

    dict(id="tof", ten="Qs-LSV & TOF (và hoạt độ khối)", loai_app=None, cong_cu="qs",
         bi_danh=["tof", "qs lsv", "qs-lsv", "turnover frequency", "hoat do khoi", "mass activity", "tam hoat dong", "quasi steady"],
         tom_tat="TOF theo điện thế từ bộ dữ liệu Qs-LSV (điểm cuối mỗi bước điện thế) và số tâm hoạt động N tính từ điện lượng Q của CV.",
         du_lieu=["Mỗi mẫu: 1 file CV (để tính Q) và dữ liệu Qs-LSV (các bước điện thế, mỗi bước giữ đủ lâu để dòng ổn định)."],
         buoc=["Tab Phân tích ▸ nhóm 'Qs-LSV & TOF' ▸ 'Mở công cụ Qs-LSV & TOF...'.", "Danh sách mẫu lấy từ các file CV/LSV trong bảng file; gán file/thư mục Qs-LSV cho từng mẫu (hoặc chọn 'Thư mục Qs-LSV chung' để app ghép theo tên).",
               "Đặt 'Diện tích CV' (vòng kín ∮ I dE hay tổng), n, ngưỡng tách bước (mặc định 3 mV), và tick 'E CV nhập theo RHE' / 'E trong file Qs-LSV đã là RHE' nếu đúng.",
               "Chọn nơi vẽ (Origin 2022+ hoặc Matplotlib) rồi bấm '▶ Tính Qs-LSV & vẽ TOF'.",
               "Hoạt độ khối: nhập tải trọng ở hộp 🧪 Điều kiện đo (tab Xuất); hỏi 'hoạt độ khối' ở tab Hỏi đáp hoặc xem sheet So sánh mẫu."],
         phep_tinh=[("Điện lượng", "Q (C/cm²) = diện tích CV ÷ tốc độ quét", ""), ("Số tâm", "N (mol/cm²) = Q / (n_Q · F)", ""),
                    ("TOF", "TOF (s⁻¹) = |J| / (n · F · N)", "J lấy từ Qs-LSV (mA/cm² đã quy đổi)."), ("Hoạt độ khối", "J ÷ tải trọng (mg/cm²) → A/g", "Tại các quá thế khảo sát (mặc định 300 mV).")],
         tieu_chi=["Khi coi mọi nguyên tử kim loại là tâm hoạt động (tỉ lệ 1), TOF chỉ là CẬN DƯỚI."], loi=["CV chứa dòng Faraday lớn → Q và N bị thổi phồng, TOF thấp giả."],
         ket_qua=["Qs_CV, Qs_TOF, Qs_LSV_J-E (Origin) hoặc TOF_QsLSV.png/.pdf (Matplotlib)."], xem_them=["ecsa", "cv"]),

    dict(id="gcd", ten="GCD: nạp–xả dòng không đổi (siêu tụ lai / pin)", loai_app=None, cong_cu="gcd",
         bi_danh=["gcd", "nap xa", "galvanostatic", "charge discharge", "sieu tu", "supercapacitor", "pin", "battery", "hybrid", "lai", "esr", "ir drop", "bo cong thuc"],
         tom_tat="Từ file GCD thô app tách từng chu kỳ nạp/xả, tính thời gian nạp/xả/chu kỳ, điện dung hoặc dung lượng riêng, IR drop/ESR, CE, E–P, retention và vẽ 6 đồ thị. "
                 "Công thức mặc định khớp file Excel của bạn (Csp = I·Δt/(m·ΔV)); có thể chuyển sang cách chuẩn bỏ IR drop.",
         du_lieu=["File BioLogic .mpt, CSV/TXT, CS Studio (E, i, T; app đọc luôn khối lượng, dòng, cửa sổ điện thế từ dòng đầu của file) hoặc Excel: cột thời gian, điện thế, dòng.",
                  "Khối lượng hoạt tính (mg) của từng mẫu (tự điền nếu file CS Studio có ghi)."],
         buoc=["Tab Phân tích ▸ nhóm 'Siêu tụ lai & Pin' ▸ '⚡ Mở công cụ...'.",
               "Tab ①: Thêm file... (hoặc lấy từ danh sách file của app); khối lượng (mg) tự điền từ file CS Studio, các file khác thì nhập; bấm ⚙ nếu app đoán sai cột.",
               "Chọn Loại tế bào: 3 điện cực/1 điện cực (C/m, như Excel của bạn), cell 2 điện cực tính theo tổng khối lượng (C/m), hoặc 2 điện cực đối xứng (4C/m).",
               "Chọn Bộ công thức: 'Kiểu file Excel của bạn' (ΔV gồm IR drop, E = ½CΔV²) hoặc 'Chuẩn' (bỏ IR drop, E tích phân); có thể chỉnh riêng ΔV, cách tính C, cách tính E.",
               "(Nếu đo 3 điện cực) mục 'Điện cực so sánh': tick 'Vẽ điện thế theo RHE', chọn Hg/HgO, Ag/AgCl... rồi nhập pH.",
               "Bấm '▶ Phân tích'; đọc bảng kết quả (gồm t nạp, t xả, chu kỳ nạp–xả) và cảnh báo.",
               "Chuyển sang các tab ②–⑦ để xem và chỉnh từng đồ thị (GCD, GCD nhiều chu kỳ, Csp/Q theo dòng, Ragone, Retention + CE, Csp/Q + CE theo chu kỳ); xuất hình/Excel hoặc 'Vẽ ra Origin'.",
               "💾 Lưu thiết lập để lần sau chỉnh tiếp."],
         phep_tinh=[("Điện dung (như Excel)", "C = I·Δt / ΔV", "Δt = thời gian xả từ lúc đảo dòng; ΔV = V đỉnh nạp − V cuối xả (gồm IR drop). Csp = C/m."),
                    ("Điện dung (chuẩn)", "C = Q/ΔV, ΔV = V_ext − V_cuối", "V_ext ngoại suy về lúc đảo dòng, đã bỏ IR drop (Stoller & Ruoff)."),
                    ("Năng lượng, công suất", "E = ½·C·ΔV²·1000/3600 (Wh/kg); P = E·3600/Δt (W/kg)", "Cách tính E khác: ½C(V²−V₀²) hoặc ∫V·I dt."),
                    ("Điện tích", "Q = ∫|I| dt; Qsp = Q/(3.6·m) (mAh/g)", ""),
                    ("ESR", "ESR = ΔV_IR / (2I)", ""),
                    ("Thời gian chu kỳ", "chu kỳ nạp–xả = t nạp + t xả", ""),
                    ("Csp 2 điện cực đối xứng", "Csp = 4C/m, m = tổng khối lượng", "Stoller & Ruoff 2010; không dùng cho cell bất đối xứng (siêu tụ lai).")],
         tieu_chi=["Đường xả tam giác (R² ≥ 0.985, ngưỡng của app) → dạng tụ, báo F/g; có plateau (R² < 0.93) → dạng pin, báo mAh/g (ngưỡng là quy ước của app).",
                   "Hai bộ công thức cho kết quả khác nhau khi IR drop lớn (ví dụ 153 so với ~199 F/g cho NiCr2O4 ở 10 A/g): hãy ghi rõ cách bạn dùng trong bài.",
                   "CE > 100 % là dấu hiệu tách nạp/xả sai hoặc phản ứng phụ; khối lượng < 1 mg app cảnh báo."],
         loi=["Chiều nạp sai (điện thế giảm khi nạp) → tick đúng 'Điện thế GIẢM khi nạp'.", "File không có cột dòng → nhập dòng không đổi (mA).",
              "Chọn nhầm Loại tế bào: 2 điện cực đối xứng nhân 4 lần so với 3 điện cực."],
         ket_qua=["Excel 7 sheet (có 'Thời gian chu kỳ'), CSV từng đồ thị, hình PNG/PDF/TIFF, file Origin."], xem_them=["gcd nhieu", "csp", "ragone", "retention", "ce", "dien cuc"]),

    dict(id="gcd nhieu", ten="GCD nhiều chu kỳ: đường V–t dài có ô phóng đại chu kỳ đầu/cuối", loai_app=None, cong_cu="gcd",
         bi_danh=["gcd nhieu", "nhieu chu ky", "cycling", "cycle life", "tuoi tho", "bien dang v t", "4500 cycles", "5000 cycles", "initial cycles", "final cycles", "o phong dai", "inset", "bo ben"],
         tom_tat="Vẽ toàn bộ đường điện thế theo thời gian của hàng nghìn chu kỳ, kèm hai ô phóng đại 'Initial cycles' và 'Final cycles' như hình bền chu kỳ trong bài báo.",
         du_lieu=["Một file GCD nhiều chu kỳ (cùng một dòng), ví dụ 5 A/g × 5000 chu kỳ.", "Khối lượng để ghi mật độ dòng (A/g) vào chú thích."],
         buoc=["Mở công cụ ⚡, nạp file, nhập khối lượng, bấm '▶ Phân tích'.", "Mở tab ③ 'GCD nhiều chu kỳ'.",
               "Chỉnh số chu kỳ trong ô phóng đại (mặc định 3 đầu, 3 cuối), nhãn ô (Initial cycles / Final cycles), chữ góc trên trái (vd NiCr2O4 // AC) và chú thích (vd 5 A g⁻¹ 4500 Cycles).",
               "Chỉ vẽ một mức dòng: điền 'Chỉ một mức dòng j' (vd 5). Vẽ nhiều mẫu: để trống ô tên mẫu; muốn một mẫu thì gõ một phần tên mẫu.",
               "Chỉnh trục, cỡ chữ, nét ở các nhóm bên dưới; '💾 Xuất hình' (PNG/PDF/TIFF/SVG) hoặc 'Vẽ ra Origin'.",
               "Tab ⑥ 'Retention + CE' cho tỉ lệ giữ dung lượng; chọn đại lượng 'Thời gian xả (s), như file Excel' nếu muốn retention theo thời gian xả."],
         phep_tinh=[("Retention theo thời gian xả", "CR(%) = t_xả(n) / t_xả(chu kỳ gốc) × 100", "Cột 'CR%' trong file Excel của bạn."),
                    ("Hiệu suất Coulomb", "CE(%) = t_xả / t_nạp × 100 (dòng không đổi)", ""),
                    ("Giảm điểm vẽ", "mỗi khối điểm giữ đỉnh và đáy", "Hình hàng trăm nghìn điểm vẫn giữ đúng biên mà không nặng.")],
         tieu_chi=["Báo rõ mật độ dòng, số chu kỳ, cửa sổ điện thế và % giữ dung lượng sau chu kỳ cuối."],
         loi=["Origin: ô phóng đại được vẽ thành hai đồ thị riêng cạnh đồ thị chính (hình Matplotlib/PNG có sẵn ô phóng đại ngay trong hình).",
              "Nếu file có dòng 'CYCLE' xen giữa số liệu, app bỏ qua các dòng đó và tự đếm chu kỳ theo dấu dòng."],
         ket_qua=["Hình GCD nhiều chu kỳ, CSV chính và hai CSV ô phóng đại, sheet 'Thời gian chu kỳ'."], xem_them=["gcd", "retention", "ce"]),

    dict(id="dien cuc", ten="Điện cực so sánh (Hg/HgO, Ag/AgCl, SCE...) và quy đổi RHE", loai_app=None,
         bi_danh=["dien cuc", "dien cuc so sanh", "hg/hgo", "hghgo", "ag/agcl", "agcl", "sce", "calomel", "reference electrode", "eref", "nernst", "he so nernst", "rhe"],
         tom_tat="Chọn điện cực so sánh để app tự điền Eref (V so với SHE), cộng hệ số Nernst × pH để đổi điện thế đo sang thang RHE.",
         du_lieu=["Loại điện cực so sánh đã dùng và pH dung dịch."],
         buoc=["Tab Dữ liệu ▸ nhóm 'Quy đổi điện thế': chọn 'Điện cực' (Hg/HgO 1 M KOH, Hg/HgO 1 M NaOH, Ag/AgCl, SCE, Hg/Hg₂SO₄, SHE).",
               "Ô '+ Eref (V)' tự điền; thấy datasheet điện cực khác thì sửa tay (hộp chọn tự về 'Tùy chỉnh').",
               "Nhập pH; chọn hệ số 'k (V/pH)': 0.059 (khớp Excel) hoặc 0.0592 (25 °C).",
               "Công cụ ⚡ GCD có hộp riêng 'Điện cực so sánh': tick 'Vẽ điện thế theo RHE' để các đồ thị GCD hiện V vs RHE (không đổi giá trị C, E).",
               "Đo hai điện cực (cell) thì tick 'Không quy đổi RHE'."],
         phep_tinh=[("RHE", "E(RHE) = E đo + k × pH + Eref", "Ví dụ Hg/HgO 1 M KOH, pH 13.8: 0.059×13.8 + 0.098 = 0.9122 V (khớp ô C5 file Excel của bạn)."),
                    ("Giá trị tham khảo (V so với SHE, ~25 °C)", "Hg/HgO 1 M KOH 0.098 · Hg/HgO 1 M NaOH 0.140 · Ag/AgCl bão hòa KCl 0.197 · Ag/AgCl 3 M KCl 0.210 · SCE 0.241 · Hg/Hg₂SO₄ bão hòa 0.640", "Phụ thuộc nồng độ dung dịch trong điện cực, nhiệt độ và hãng; ưu tiên số trên datasheet.")],
         tieu_chi=["Ghi trong bài: loại điện cực so sánh, Eref, pH và hệ số dùng (mục Methods của app tự điền).", "Hệ số 0.059 và 0.0592 chênh ≈ 2.8 mV ở pH 13.8."],
         loi=["Dùng Eref của điện cực khác loại (Ag/AgCl 0.197 thay cho Hg/HgO 0.098) → lệch ~0.1 V.", "Quy đổi RHE cho phép đo hai điện cực."], ket_qua=["Sheet 'Thông tin' ghi Eref, pH, hệ số k và công thức."],
         xem_them=["quy doi", "lsv"], thuc_te=lambda c: _thuc_te_quy_doi(c)),

    dict(id="csp", ten="Điện dung riêng và dung lượng riêng (Csp, Qsp)", loai_app=None, cong_cu="gcd",
         bi_danh=["csp", "dien dung rieng", "specific capacitance", "dung luong rieng", "specific capacity", "f/g", "mah/g", "capacitance", "rate"],
         tom_tat="Điện dung riêng F/g (tụ) hoặc dung lượng riêng mAh/g (pin, lai) theo mật độ dòng A/g.",
         du_lieu=["File GCD và khối lượng hoạt tính."],
         buoc=["Mở công cụ ⚡ (xem mục GCD) và Phân tích.", "Tab ④ 'Csp / Q theo mật độ dòng': chọn 'Đại lượng' (theo thiết lập chung, F/g hoặc mAh/g).", "Tab ⑦ 'Csp / Q + CE theo chu kỳ' để xem theo chu kỳ."],
         phep_tinh=[("Csp (kiểu Excel)", "Csp = I·Δt / (m·ΔV)", "I (A), Δt (s), m (g), ΔV (V): đúng công thức trong file Excel của bạn; giá trị mỗi mức dòng là trung vị các chu kỳ."),
                    ("Csp 2 điện cực đối xứng", "Csp = 4C/m", "m = tổng khối lượng hai điện cực (Stoller & Ruoff 2010); không dùng cho siêu tụ lai bất đối xứng."),
                    ("Qsp", "Qsp = Q/(3.6 m)", "mAh/g"), ("Mật độ dòng", "j = I/m (A/g)", "")],
         tieu_chi=["Ghi rõ 2 hay 3 điện cực, khối lượng chuẩn hóa, mật độ dòng, cửa sổ điện thế, cách tính C và ΔV.", "Khối lượng rất nhỏ làm sai số lớn (app cảnh báo < 1 mg)."],
         loi=["Báo F/g cho vật liệu kiểu pin (có plateau) → dùng mAh/g.", "Khối lượng là tổng hai điện cực nhưng chọn '3 điện cực' (hoặc ngược lại)."], ket_qua=["Sheet 'Tổng hợp theo dòng' và 'Từng chu kỳ'."], xem_them=["gcd", "ragone", "retention"]),

    dict(id="ragone", ten="Ragone: năng lượng riêng theo công suất riêng", loai_app=None, cong_cu="gcd",
         bi_danh=["ragone", "nang luong rieng", "cong suat rieng", "energy density", "power density", "wh/kg", "w/kg", "e p"],
         tom_tat="Mỗi mật độ dòng cho một điểm (P, E), vẽ log–log.",
         du_lieu=["File GCD nhiều mức dòng và khối lượng."],
         buoc=["Mở công cụ ⚡, Phân tích.", "Tab ⑤ Ragone: 'Cách tính năng lượng' mặc định theo thiết lập chung (kiểu Excel ½C·ΔV²); đổi sang ½C(V²−V₀²) hoặc ∫V·I dt nếu cần.", "Chỉnh trục/log/kiểu, rồi Xuất hình hoặc Vẽ ra Origin."],
         phep_tinh=[("Năng lượng (như Excel)", "E = ½·C·ΔV² (J/g) × 1000/3600 = Wh/kg", "C là điện dung riêng của chính cell/mẫu, ΔV như mục GCD."), ("Công suất", "P = E·3600/Δt_xả", "W/kg"),
                    ("Cách khác", "E = ∫V·|I| dt hoặc ½C(V_ext² − V_cuối²)", "arXiv 1601.05173.")],
         tieu_chi=["Ghi rõ chuẩn hóa theo khối lượng điện cực hay cả cell; trị số điện cực khác với cell đóng gói."], loi=["Trộn mẫu chuẩn hóa khác nhau trên cùng một hình."],
         ket_qua=["Sheet Ragone (cả hai cách tính), hình Ragone."], xem_them=["gcd", "csp"]),

    dict(id="retention", ten="Retention theo số chu kỳ", loai_app=None, cong_cu="gcd",
         bi_danh=["retention", "giu dung luong", "cycling", "cycle life", "chu ky", "tuoi tho", "cyclic number", "capacity retention", "cr"],
         tom_tat="Phần trăm điện dung/dung lượng (hoặc thời gian xả) còn lại sau N chu kỳ so với chu kỳ gốc.",
         du_lieu=["Một mức dòng có ≥ 3 chu kỳ (thường vài trăm đến vài nghìn)."],
         buoc=["Mở công cụ ⚡, Phân tích.", "Tab ⑥ 'Retention + CE': đặt 'Đại lượng' (Csp, Qsp hoặc 'Thời gian xả (s), như file Excel'), 'Mức dòng j' (trống = nhóm nhiều chu kỳ nhất), 'Chu kỳ gốc', bật/tắt CE.", "Chỉnh trục y (vd từ 80) và xuất hình."],
         phep_tinh=[("Retention", "retention_k = giá trị_k / giá trị_gốc × 100 (%)", "giá trị = Csp, Qsp hoặc t xả. Theo thời gian xả = cột 'CR%' của file Excel (dòng không đổi nên tương đương theo Q)."),
                    ("Hiệu suất Coulomb", "CE = t_xả / t_nạp × 100", "")],
         tieu_chi=["Báo số chu kỳ, dòng, cửa sổ điện thế và số thiết bị đo."], loi=["Chu kỳ gốc là chu kỳ đầu chưa ổn định → đặt chu kỳ gốc sau vài chu kỳ.", "Thời gian lấy mẫu 0.1 s làm CE theo t_xả/t_nạp nhảy ±5–10 %: app dùng nội suy theo điện tích nên mượt hơn Excel."],
         ket_qua=["Sheet Retention, hình hai trục."], xem_them=["ce", "gcd", "gcd nhieu"]),

    dict(id="ce", ten="Hiệu suất Coulomb (CE)", loai_app=None, cong_cu="gcd",
         bi_danh=["ce", "hieu suat coulomb", "coulombic efficiency", "coulomb", "hieu suat", "columbic"],
         tom_tat="Tỉ số điện lượng (hoặc thời gian) xả trên nạp của cùng chu kỳ.",
         du_lieu=["Chu kỳ nạp liền trước chu kỳ xả."],
         buoc=["Mở công cụ ⚡, Phân tích.", "Xem cột 'CE (%)' ở sheet Từng chu kỳ; vẽ CE ở trục phải của tab ⑥/⑦ (tick 'Hiện hiệu suất Coulomb')."],
         phep_tinh=[("CE", "CE = Q_xả / Q_nạp × 100", "dòng không đổi: = t_xả / t_nạp (cột 'columbic eff' trong file Excel)."), ("Hiệu suất năng lượng", "EE = E_xả / E_nạp × 100", "")],
         tieu_chi=["CE > 100 % là dấu hiệu báo cáo sai; app cảnh báo từ 100.5 %."], loi=["Chu kỳ đầu của pin có CE thấp do hình thành lớp SEI (kiến thức chung)."],
         ket_qua=["Cột CE/EE ở các sheet."], xem_them=["retention", "gcd"]),

    dict(id="xps", ten="XPS: fit phổ, hiệu chuẩn, chứng minh", loai_app=None, cong_cu="xps",
         bi_danh=["xps", "quang dien tu", "casa", "casaxps", "vamas", "vms", "fit pho", "c1s", "shirley", "residual"],
         tom_tat="Đọc file .vms của CasaXPS, hiệu chuẩn C1s, nền Shirley, fit GL(30) có ràng buộc hóa học, kiểm định kết quả, xuất Origin/Casa.",
         du_lieu=["File .vms (hoặc text/Excel xuất từ Casa)."],
         buoc=["Tab Phổ ▸ 🔬 XPS ▸ 'Mở file XPS...'.", "Hiệu chuẩn C1s = 284.8 eV (app cảnh báo nếu lệch).", "Nạp mẫu thành phần (⚙ Thiết lập thành phần) rồi '▶ Fit'.",
               "'✓ Chứng minh': F-test từng đỉnh, phần dư, độ bền nền/vùng, sai số Monte Carlo.", "'⬆ Origin' để vẽ; '💾 Xuất' để ghi CSV/hình; menu '◧ Casa ▾' để làm việc qua CasaXPS."],
         phep_tinh=[("Nền", "Shirley (hoặc Tougaard U2)", ""), ("Hình dạng đỉnh", "GL(30), FWHM ràng buộc ±0.1 eV", ""), ("Chất lượng fit", "Residual STD ≈ 1", "")],
         tieu_chi=["Residual STD > ~1.08: app nới dần cửa sổ vị trí và FWHM thành phần không chuẩn; không thêm đỉnh nếu F-test không đủ cơ sở."],
         loi=["Quên hiệu chuẩn C1s → BE lệch.", "File ghi 'Counts' hay CPS: app tự đổi Counts → CPS."], ket_qua=["CSV, hình, báo cáo chứng minh, file Origin/Casa."], xem_them=["xrd", "hr tem", "nop bai"]),

    dict(id="xrd", ten="XRD: xác định pha, so sánh mẫu", loai_app=None, cong_cu="xrd",
         bi_danh=["xrd", "nhieu xa", "x ray", "pho xrd", "pha", "jcpds", "cif", "scherrer", "2theta"],
         tom_tat="Đọc Excel XRD nhiều mẫu, tìm đỉnh, đối chiếu ngân hàng phổ, phân biệt đỉnh mẫu/đế/bức xạ phụ/đỉnh lạ.",
         du_lieu=["Excel: các cặp cột 2θ–cường độ (mỗi cặp một mẫu) hoặc text/CSV."],
         buoc=["Tab Phổ ▸ 📈 XRD ▸ 'Mở file XRD...'.", "Chọn nguồn tia X, dung sai ghép vạch (mặc định 0.15°), ngưỡng đỉnh (mặc định 5σ); điền nguyên tố nếu biết, hoặc để trống để quét toàn bộ ngân hàng; chọn 'Mẫu chuẩn (đế)'.",
               "'Phân tích + xác định pha' ▸ 'So sánh các mẫu (đỉnh lạ?)'.", "'Xuất CSV + báo cáo + hình...' hoặc 'Vẽ ra Origin...' (nhãn pha ★ ● ■ ◆ trên đỉnh)."],
         phep_tinh=[("Bragg", "nλ = 2d·sinθ", ""), ("Scherrer", "D = Kλ / (β·cosθ), K = 0.9", "Dùng trong mục Đối chiếu.")],
         tieu_chi=["Pha nhiều vạch khớp mới đáng tin; một đỉnh đơn không đủ kết luận."], loi=["Đỉnh của đế/hộp mẫu bị nhận nhầm → chọn 'Mẫu chuẩn (đế)'."],
         ket_qua=["CSV, báo cáo tiếng Việt, hình xếp chồng, Origin."], xem_them=["hr tem", "xps", "nop bai"]),

    dict(id="hr tem", ten="HR-TEM: đo khoảng cách mặt mạng d", loai_app=None, cong_cu="hrtem",
         bi_danh=["hr tem", "hrtem", "tem", "van mang", "fft", "imagej", "khoang cach mat mang", "d spacing", "lattice"],
         tom_tat="Bấm vào vùng có vân mạng, FFT, chọn đốm, đo d bằng FFT và profile, gán pha, xuất ảnh chú thích.",
         du_lieu=["Ảnh HR-TEM và thanh thang (nm/px)."],
         buoc=["Tab Phổ ▸ 🔭 HR-TEM ▸ 'Mở ảnh...'.", "'Tự đo thanh thang' hoặc nhập nm/px.", "Bấm vào vùng có vân; 'Dùng làm vùng đo / FFT'; chọn đốm.",
               "Gán pha: 'Chọn pha...' hoặc ô 'Chỉ xét pha' (thu hẹp theo XRD/XPS).", "'Thêm đốm đang chọn vào hình', rồi 'Xuất kết quả...'."],
         phep_tinh=[("d từ FFT", "d = 1/g (g là khoảng cách đốm tới tâm FFT)", ""), ("d từ profile", "d = khoảng cách chia số vân", ""), ("d chung", "trung vị 5 phép đo", "")],
         tieu_chi=["Nhiều pha trùng d (vd Cu(111) 0.209, NiO(200) 0.209 nm): d một mình không đủ kết luận."], loi=["Sai thang nm/px → d sai theo tỉ lệ."],
         ket_qua=["Ảnh chú thích, CSV, hình từng vùng."], xem_them=["xrd", "xps", "nop bai"]),

    dict(id="nop bai", ten="Nộp bài: tiêu chí chấm và gói nộp bài", loai_app=None,
         bi_danh=["nop bai", "tieu chi", "paperlens", "cham diem", "goi nop bai", "methods", "tai lap", "reproducibility", "kiem tra nop bai"],
         tom_tat="Tick 'Kèm gói nộp bài' (tab Xuất) để thêm vào báo cáo Excel bảng nộp bài, kiểm tra tiêu chí, đoạn Methods và gói tái lập.",
         du_lieu=["Các mẫu đã xử lý; vai trò từng mẫu; điều kiện thí nghiệm."],
         buoc=["Tab Xuất ▸ 🧪 Điều kiện thí nghiệm: điện ly, điện cực tham chiếu/đối, máy đo, nhiệt độ, điện cực, mực xúc tác.", "Tab Xuất ▸ 🏷 Vai trò từng mẫu: chuẩn (Pt/C...), đối chứng, sau thử bền, nhóm lặp.",
               "Tick 'Kèm gói nộp bài' rồi chạy.", "Bấm ✅ để xem mức sẵn sàng; mở sheet 'Kiểm tra nộp bài' để xem việc còn thiếu.", "Dùng methods_dien_hoa.txt và goi_tai_lap.zip (dữ liệu thô + kết quả + thông số + phiên bản)."],
         phep_tinh=[],
         tieu_chi=["7.1 quá thế tại 10 mA/cm² · 7.2 Tafel · 7.3 ECSA/Cdl · 7.4 độ bền (≥ 200 h mốc cao, ≥ 500 h tối đa) · 7.5 điện áp ô 2 điện cực · 7.6 điều kiện đo · 7.7 có Pt/C hoặc RuO₂/IrO₂",
                   "5.3 mẫu đối chứng · 5.5 lặp ≥ 3 điện cực · 9.2 mẫu sau thử bền · 9.3 dòng ≥ 500 mA/cm² · 8.3 đối chiếu XRD–HR-TEM–XPS"],
         loi=["Không khai điều kiện đo → mất điểm 7.6 và 10.3."], ket_qua=["Sheet 'Bảng nộp bài', 'Lặp lại (TB ± SD)', 'Kiểm tra nộp bài'; methods_dien_hoa.txt; goi_tai_lap.zip."], xem_them=["lsv", "it", "ecsa"]),

    dict(id="hinh tap chi", ten="Hình ghép theo quy cách tạp chí", loai_app=None,
         bi_danh=["hinh tap chi", "tap chi", "acs", "rsc", "elsevier", "nature", "hinh ghep", "journal", "dpi", "cot don", "cot doi"],
         tom_tat="Xuất hình nhiều ô A/B/C theo khổ cột, cỡ chữ, độ dày nét của từng tạp chí.",
         du_lieu=["Các hình đã có (LSV, Tafel, EIS, i-t...)."],
         buoc=["Tab Hình ▸ nhóm 'Hình ghép theo tạp chí': tick 'Xuất hình nhiều ô'.", "Chọn tạp chí (ACS / RSC / Elsevier / Nature / Tùy chỉnh) và cột (đơn / 1.5 / đôi).", "ℹ xem quy cách; ⚙ chọn PNG/PDF/TIFF và dpi; 🧩 soạn ô.", "Chạy; xem file *_kiem_tra_tap_chi.txt để đối chiếu."],
         phep_tinh=[], tieu_chi=["ACS 8.25/17.78 cm, chữ ≥ 5 pt, nét ≥ 1 pt, ≥ 600 dpi · RSC 8.3/17.1 cm, ≥ 600 dpi · Elsevier 9.0/14.0/19.0 cm, chữ ≥ 7 pt, 1000 dpi · Nature 8.9/12.0/18.3 cm, chữ 5–7 pt, nét 0.25–1 pt.",
                                   "Wiley, Springer... mỗi tạp chí một khác: dùng 'Tùy chỉnh' rồi đối chiếu hướng dẫn tác giả."], loi=[], ket_qua=["Hinh_bai_bao*.png/pdf/tiff + file kiểm tra quy cách."], xem_them=["nop bai"]),

    dict(id="quy doi", ten="Quy đổi điện thế (RHE) và dòng (mA/cm²)", loai_app=None,
         bi_danh=["quy doi", "rhe", "ph", "eref", "dien tich", "nhan chia", "ma/cm2", "he so"],
         tom_tat="Mọi phép đo được đổi sang cùng thang trước khi tính.",
         du_lieu=["pH dung dịch, điện thế điện cực so sánh Eref (so với SHE), diện tích điện cực (cm²)."],
         buoc=["Tab Dữ liệu ▸ Quy đổi điện thế: nhập pH và '+ Eref (V)'.", "Tab Dữ liệu ▸ Quy đổi dòng: nhập 'nhân' và '÷ chia (diện tích)'.", "Đo 2 điện cực: tick 'Không quy đổi RHE'.", "Lưu bộ thông số bằng ô 'Cấu hình' (vd 'OER Cu pH 13.8')."],
         phep_tinh=[("RHE", "E(RHE) = E đo + k × pH + Eref", "k = 0.059 (mặc định, khớp Excel) hoặc 0.0592; Eref chọn nhanh trong ô 'Điện cực' (Hg/HgO, Ag/AgCl, SCE...)."), ("Mật độ dòng", "I (mA/cm²) = i × 1000 × nhân ÷ chia", "")],
         tieu_chi=["Cảnh báo tự động: E sau quy đổi ngoài −1.5…3.5 V vs RHE; dòng > 5000 hoặc < 10⁻⁴ mA/cm²."], loi=["Nhập Eref của điện cực khác loại (Ag/AgCl vs Hg/HgO...)."],
         ket_qua=["Sheet 'Thông tin' ghi thông số đã dùng."], xem_them=["lsv", "bu ir"], thuc_te=lambda c: _thuc_te_quy_doi(c)),
]
THEO_ID = {t["id"]: t for t in TOPICS}


# ====================== TÌM KIẾM ======================
def _khoa_tim(t):
    return [chuan_hoa(x) for x in [t["id"], t["ten"]] + list(t["bi_danh"])]


def tim(chuoi, toi_da=6):
    """Danh sách id chủ đề khớp nhất với chuỗi gõ vào (không dấu, sai chính tả nhẹ cũng được)."""
    q = chuan_hoa(chuoi)
    if not q:
        return []
    diem = {}
    toks = [x for x in q.split() if len(x) >= 1]
    for t in TOPICS:
        khoa = _khoa_tim(t)
        d = 0.0
        for ik, k in enumerate(khoa):
            if q == k:
                d = max(d, 100)
            elif re.search(r"(?<![a-z0-9])" + re.escape(q) + r"(?![a-z0-9])", k):
                d = max(d, 80 if k in (chuan_hoa(t["id"]),) else 60)
            elif k.startswith(q) or q.startswith(k) and len(k) >= 2:
                d = max(d, 50)
            elif q in k and len(q) >= 3:
                d = max(d, 40)
            else:
                nhieu = sum(1 for x in toks if len(x) >= 2 and re.search(r"(?<![a-z0-9])" + re.escape(x) + r"(?![a-z0-9])", k))
                if nhieu:
                    d = max(d, 20 + 10 * nhieu)
                else:
                    r = 0 if ik == 1 else max([difflib.SequenceMatcher(None, x, w).ratio() for x in toks if len(x) >= 4 for w in k.split() if len(w) >= 4 and abs(len(w) - len(x)) <= 2] or [0])
                    if r >= 0.8:
                        d = max(d, 30 * r)
        if d:
            diem[t["id"]] = d
    return [k for k, _ in sorted(diem.items(), key=lambda kv: -kv[1])][:toi_da]


def tim_trong_cau(cau):
    """Tìm chủ đề trong một câu hỏi dài (vd 'cho tôi hướng dẫn tafel') — dùng cho tab Hỏi đáp."""
    q = chuan_hoa(cau)
    ket = []
    for t in TOPICS:
        for k in _khoa_tim(t)[:1] + [chuan_hoa(x) for x in t["bi_danh"]]:
            if len(k) >= 2 and re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", q):
                ket.append((len(k), t["id"]))
                break
    return [i for _, i in sorted(ket, reverse=True)]


# ====================== ĐỊNH DẠNG ======================
def khoi(topic_id, ctx=None):
    """Danh sách khối [(kiểu, nội dung)]. kiểu: h1, h2, p, buoc, li, ct (công thức), canh."""
    t = THEO_ID[topic_id]
    out = [("h1", t["ten"]), ("p", t["tom_tat"])]
    if t.get("du_lieu"):
        out += [("h2", "Dữ liệu cần có")] + [("li", x) for x in t["du_lieu"]]
    if t.get("buoc"):
        out += [("h2", "Các bước trong app (bấm vào ô [ ] để đánh dấu đã làm)")] + [("buoc", x) for x in t["buoc"]]
    if t.get("phep_tinh"):
        out += [("h2", "Phép tính")] + [("ct", f"{ten}:  {ct}" + (f"   — {gc}" if gc else "")) for ten, ct, gc in t["phep_tinh"]]
    if t.get("thuc_te"):
        dong = [x for x in t["thuc_te"](ctx) if x]
        if dong:
            out += [("h2", "Với thiết lập hiện tại của bạn")] + [("li", x) for x in dong]
    if t.get("tieu_chi"):
        out += [("h2", "Tiêu chí & cảnh báo")] + [("li", x) for x in t["tieu_chi"]]
    if t.get("loi"):
        out += [("h2", "Lỗi thường gặp")] + [("canh", x) for x in t["loi"]]
    if t.get("ket_qua"):
        out += [("h2", "App xuất ra")] + [("li", x) for x in t["ket_qua"]]
    if t.get("xem_them"):
        ten = [THEO_ID[x]["ten"].split(":")[0] for x in t["xem_them"] if x in THEO_ID]
        out += [("h2", "Xem thêm")] + [("li", ", ".join(ten))]
    return out


def van_ban(topic_id, ctx=None):
    """Bản chữ thường (dùng cho tab Hỏi đáp và lưu file)."""
    dong = []
    n = 0
    for kieu, nd in khoi(topic_id, ctx):
        if kieu == "h1":
            dong += [nd.upper(), ""]
        elif kieu == "h2":
            dong += ["", "■ " + nd.split(" (")[0]]
        elif kieu == "buoc":
            n += 1
            dong.append(f"  {n}. {nd}")
        elif kieu in ("li", "ct"):
            dong.append("  • " + nd)
        elif kieu == "canh":
            dong.append("  ⚠ " + nd)
        else:
            dong.append(nd)
    return "\n".join(dong).strip()


def danh_sach():
    return [(t["id"], t["ten"]) for t in TOPICS]
