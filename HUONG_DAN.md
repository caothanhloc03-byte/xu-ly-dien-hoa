# Hướng dẫn nhanh Echem Studio

## Thanh công cụ (giống Origin)
Hàng chữ trên cùng là thanh công cụ gồm 7 nhóm: **Dữ liệu · Phân tích · Hình · Xuất · Phổ · Hỏi đáp · Trợ giúp**. Bấm tên nhóm để hiện các tính năng của nhóm đó, bấm lần nữa để thu gọn và nhường chỗ cho bảng file và ô báo cáo. Ô "Cấu hình" (lưu/nạp bộ thông số) nằm bên phải thanh công cụ.
- **Dữ liệu**: loại phép đo, chu kỳ CV, quy đổi điện thế/dòng, không quy đổi RHE (điện thế tế bào), bù iR.
- **Phân tích**: Tafel, ECSA, so sánh mẫu, nhóm lặp & bảng tài liệu, hoạt độ khối & TOF, hiệu suất Faraday, fit EIS.
- **Hình**: Origin (độ dày, cỡ chữ, vạch chia, khoảng trục) và hình ghép chuẩn bài báo.
- **Xuất**: thư mục kết quả, CSV/ảnh, báo cáo Excel.
- **Phổ**: xếp chồng phổ XRD/Raman/XPS/FTIR.

## Bắt đầu trong 3 bước
- Bấm **Dữ liệu mẫu** để nạp thử số liệu giả lập, hoặc **Thêm file...** / **Thêm thư mục...** (kéo-thả nếu máy có tkinterdnd2).
- Chọn **Loại phép đo** (hoặc để "Tự nhận dạng"), kiểm tra pH, Eref và hệ số quy đổi dòng.
- Bấm **Xem trước hình** để xem nhanh, rồi **CHẠY XỬ LÝ & VẼ** để vẽ bằng Origin và xuất báo cáo.

## Các loại phép đo
- **LSV / CV**: vẽ đường E (V vs RHE) – I (mA/cm²). CV mặc định dùng chu kỳ cuối, có thể đổi ở ô "Chu kỳ CV dùng".
- **IT**: dòng theo thời gian (giờ).
- **EIS**: đồ thị Nyquist Z' – (−Z'').
- **ECSA**: cần ít nhất 2 file CV ở các tốc độ quét khác nhau (khuyến nghị 5 trở lên). App lấy (Ja−Jc)/2 tại một điện thế, fit theo tốc độ quét (V/s) để ra Cdl, rồi ECSA = Cdl / Cs.
  - **Chọn E bằng đồ thị** (tab Phân tích → nhóm ECSA → "Chọn E bằng đồ thị..."): hiện các đường CV, bấm/kéo chuột để chọn điện thế lấy dòng điện dung (vạch đỏ), Cdl - R² - ECSA tính lại ngay. "Gợi ý E có R² cao nhất" tự quét vùng điện thế chung (chỉ là gợi ý - hãy chọn vùng phẳng, không có pic oxi hóa-khử).
  - **Bỏ tick tốc độ quét lệch**: trong cùng cửa sổ, bỏ tick tốc độ nào lệch để loại khỏi phép fit; file không bị xóa. Bấm "Dùng kết quả này" để ghi E vào ô và đánh dấu "[bỏ khỏi ECSA]" ở bảng file; khi CHẠY, các file đó bị bỏ qua. Còn 2 điểm thì R² luôn = 1 (không có ý nghĩa).
- **Tafel**: E theo log|J| trong vùng dòng bạn chọn (mặc định 9–11 mA/cm²).

## Công thức quy đổi
- E (RHE) = E đo + 0.0592 × pH + Eref
- I (mA/cm²) = i × 1000 × (hệ số nhân) ÷ (hệ số chia, thường là diện tích điện cực)
- Quá thế = E (RHE) − E cân bằng (OER: 1.23 V)

## Cảnh báo thông minh
App tự cảnh báo bằng dòng chữ cam trong ô báo cáo, ví dụ: R² của fit Cdl thấp, một điểm tốc độ quét lệch khỏi đường thẳng, CV bị cụt, vùng Tafel quá hẹp. Mỗi cảnh báo kèm gợi ý cách xử lý.

## Báo cáo Excel
Tick "Xuất báo cáo Excel" để có bao_cao_tong_hop.xlsx trong thư mục kết quả: điện thế/quá thế tại các mật độ dòng mục tiêu, Tafel, ECSA, cảnh báo và thông số đã dùng. Nếu máy thiếu thư viện openpyxl, app xuất file CSV thay thế.

## Cấu hình (preset)
Ô "Cấu hình" lưu bộ thông số (pH, Eref, diện tích, cỡ chữ...) theo tên, ví dụ "OER Cu pH 13.8". Mỗi lần chạy, app còn lưu file thong_so_chay_*.json trong thư mục `_lich_su_chay` để tái lập kết quả; có thể nạp lại bằng "Nạp từ file...".

## Tùy chọn nâng cao
Tick "Hiện tùy chọn nâng cao" để chỉnh khoảng trục, bước chia, cỡ chữ, độ dày khung, vạch chia chính/phụ. Khi tắt, các giá trị đã chỉnh vẫn được áp dụng.

## Bù iR, so sánh mẫu, hoạt độ khối và TOF (mục 3c)
- **Bù iR**: nhập Rs (Ω) hoặc bấm "Lấy Rs từ file EIS..." (ước lượng từ Z' ở tần số cao). App tính E thật = E đo − i × Rs, với i là dòng đo thực (A) chưa chia diện tích. Rs nên lấy từ EIS đo cùng điều kiện; app báo mức dịch điện thế tối đa để bạn kiểm tra.
- **So sánh mẫu**: tick "Bảng so sánh & biểu đồ cột các mẫu" để có `so_sanh_tong_hop.png/.csv` và sheet "So sánh mẫu" trong Excel. Mẫu có quá thế (η) tại dòng mục tiêu thấp nhất được xếp hạng 1. Dòng mục tiêu đặt ở ô "I mục tiêu", điện thế cân bằng ở ô "E cân bằng".
- **Hoạt độ khối** (A/g) = J ÷ tải trọng (mg/cm²), tính tại các quá thế khảo sát (mặc định 300 mV).
- **TOF** (s⁻¹) = J ÷ (n × F × số mol tâm hoạt động/cm²). Nhập trực tiếp µmol/cm², hoặc nhập tải trọng + M (g/mol) + tỉ lệ tâm; khi coi mọi nguyên tử kim loại là tâm hoạt động (tỉ lệ 1), TOF là cận dưới. n = 4 cho OER, 2 cho HER.

## Tính năng cho bài báo khoa học
- **Tafel**: chọn vùng theo dòng (mA/cm²) hoặc theo điện thế (V). Hình Tafel có điểm đo và đường fit, chú thích ghi hệ số mV/dec.
- **Điện thế tế bào** (hai điện cực): tick "Không quy đổi RHE" để giữ nguyên E đo; trục hiển thị "Cell voltage (V)".
- **Không tính quá thế** (vd oxi hóa glucose): tick "Không tính quá thế"; bảng xếp hạng theo điện thế tại dòng mục tiêu.
- **Nhóm lặp (trung bình ± SD)**: ở bảng file, bấm đúp cột "Nhóm lặp" (hoặc nút "Đặt nhóm lặp") và gõ cùng tên cho các lần đo lặp. Biểu đồ cột có thanh sai số (SD, n−1); nhóm chỉ có 1 mẫu không có SD.
- **Bảng tài liệu**: nút "Tạo file mẫu" tạo CSV mẫu; điền các nghiên cứu khác rồi chọn file. App xuất sheet "So sánh tài liệu" gồm kết quả của bạn và các dòng đó.
- **Hiệu suất Faraday**: nhập thể tích khí (mL) cho từng file IT theo thứ tự, nhiệt độ, áp suất, n electron (H₂ = 2, O₂ = 4). FE = n·F·n_khí / Q × 100%, Q = ∫|i|dt; mặc định trừ áp suất hơi nước. Tốc độ sinh khí tính theo mmol cm⁻² h⁻¹ với diện tích = hệ số chia dòng. FE > 105% hoặc < 50% sẽ có cảnh báo.
- **Fit EIS**: tick "Fit mạch Rs + (Rct ‖ CPE)" để lấy Rs, Rct, Q, n, C_eff (Brug) và sai số RMS; có hình Nyquist kèm đường fit. Mô hình này chưa có phần Warburg hay nhiều cung.
- **Hình ghép chuẩn bài báo**: tab Hình, nhóm "Hình ghép chuẩn bài báo". Chọn khổ cột đôi 17.8 cm hoặc cột đơn 8.6 cm, định dạng PNG/PDF/TIFF và dpi (mặc định 600). Các ô (A)(B)(C)... tự chọn theo dữ liệu hoặc nhập "lsv,tafel,eis,it,cot".
- **Phổ XRD/Raman/XPS**: chọn Loại = "Phổ (XRD / Raman / XPS)", thêm file 2 cột (x, y), cài ở tab Phổ (kiểu phổ, khoảng đổi, số đỉnh đánh dấu). Chỉ xuất ảnh Matplotlib và CSV; chưa tách đỉnh XPS.
- Nhớ ghi trong bài báo: có bù iR hay không (và Rs), pH, điện cực so sánh, tốc độ quét, vùng Tafel đã chọn. Các thông số này nằm trong sheet "Thông tin" của báo cáo Excel.

## Hỏi đáp dữ liệu
Gõ câu hỏi tiếng Việt, ví dụ: "điện thế tại 10 mA của các mẫu", "quá thế tại 10 mA", "dòng tại 1.6 V", "tafel", "ecsa", "liệt kê các file". Không cần Internet hay AI.

## Khi gặp lỗi
- Đọc phần "GỢI Ý XỬ LÝ" in ngay dưới dòng lỗi.
- Bấm **Mở nhật ký** để lấy chi tiết kỹ thuật gửi cho người hỗ trợ.
- Origin: mở Origin một lần cho đến khi thấy giao diện chính, đóng các hộp thoại, rồi chạy lại.
- Đóng file Excel/ảnh đang mở trong thư mục kết quả trước khi chạy lại.

## Phím tắt
- Ctrl + lăn chuột, Ctrl + / Ctrl − : thu phóng giao diện; Ctrl 0: về 100%.

## Cập nhật
App tự kiểm tra bản mới khi mở. Có thể chọn "Cập nhật ngay", "Để sau" hoặc "Bỏ qua phiên bản này". Cập nhật chỉ thay mã nguồn, không đụng tới dữ liệu và cài đặt của bạn; nếu lỗi, app tự khôi phục bản cũ.


## Quét cả thư mục
Tab Dữ liệu → "Quét thư mục & phân loại...": chọn một thư mục, app tìm mọi file .txt/.csv/.dat (cả thư mục con, bỏ qua thư mục kết quả do app tạo), tự nhận dạng loại (CV/LSV/IT/EIS), cho tick chọn rồi:
- "Thêm, để app tự nhận dạng từng file": đưa vào bảng với Loại phép đo = Tự nhận dạng (có thể tick "Chạy ngay sau khi thêm").
- "Thêm các CV → ECSA": nếu có ≥ 2 file CV (cùng một mẫu ở nhiều tốc độ quét), chuyển sang loại ECSA và mở luôn cửa sổ chọn E.

## Soạn hình bài báo & tên mẫu
Tab Hình → nhóm "Hình ghép chuẩn bài báo" → "Soạn hình & tên mẫu...":
- Tạo một hoặc nhiều hình (mỗi hình là file Hinh_bai_bao_1, _2...). Với mỗi hình chọn các loại ô (J–E, Tafel, Nyquist, i–t, cột so sánh), sắp thứ tự bằng ▲▼: thứ tự từ trên xuống chính là (A), (B), (C)... Một loại ô được thêm nhiều lần.
- "Chữ ô" chọn kiểu (A)(B)(C) hoặc (a)(b)(c).
- Bảng bên phải: nhấp đúp để đặt tên mẫu riêng chỉ cho hình bài báo (có thể dùng mathtext, ví dụ Ni$_3$S$_2$). Để trống = dùng nhãn ở bảng file. Tên này không đổi nhãn ở các hình/báo cáo khác.
- Để trống mọi hình thì app tự chọn ô theo dữ liệu như trước. Tick "Xuất hình nhiều ô" và bấm CHẠY.

## Công cụ Qs-LSV & TOF (tab Phân tích → "Qs-LSV & TOF" → "Mở công cụ...")
- **Qs-LSV**: đo nhiều bước điện thế; với MỖI bước chỉ lấy điểm CUỐI (E, I) rồi ghép lại thành một bộ dữ liệu. E đã quy đổi RHE (pH, Eref, bù iR như thường); I là dòng ĐÃ QUY ĐỔI (mA/cm², theo hệ số nhân/chia ở tab Dữ liệu). Mỗi file Qs-LSV có thể là một bước (i–t ở một điện thế) hoặc nhiều bước bậc thang trong một file: app tự tách bước khi E nhảy quá "Ngưỡng bước" (mặc định 3 mV) hoặc khi trục thời gian bị đặt lại. "TB % điểm cuối" > 0 sẽ lấy trung bình phần cuối của bước để giảm nhiễu.
- **TOF** = |I| / (n·F·N), với **N = Q / (n·F)**, **Q = diện tích CV / tốc độ quét** (CV của chính mẫu đó), I lấy từ bộ dữ liệu Qs-LSV. I và Q đều dùng giá trị đã quy đổi (mật độ dòng trên cm²), nên N tính bằng µmol/cm² và TOF là s⁻¹. Hình TOF chỉ vẽ khi có CV và file Qs-LSV của mẫu.
- **Cách dùng**: (1) mẫu CV lấy từ bảng file (loại CV/LSV) hoặc bấm "Thêm CV..."; (2) gom file Qs-LSV vào một thư mục, chọn ở "Thư mục Qs-LSV chung" - app tự ghép với mẫu theo tên (tên thư mục con hoặc tên file chứa nhãn mẫu như một từ riêng, nhãn dài nhất được ưu tiên, ví dụ "Ag@NF" khác "NF"); hoặc gán thủ công cho từng mẫu (thư mục hoặc các file); (3) chỉnh n, n tính N (để trống = bằng n), tốc độ quét CV (trống = lấy từ dữ liệu), cửa sổ E của CV (mặc định -1.5 đến -1.1 V theo điện thế trong file; trống cả hai ô = cả chu kỳ), kiểu diện tích (vòng kín |∮I dE| hoặc tổng |I| hai chiều); (4) bấm "Tính Qs-LSV & vẽ TOF".
- **Kết quả** (thư mục Qs_LSV_TOF trong thư mục kết quả): TOF_QsLSV.png/.pdf (2 đồ thị: (A) CV, (B) TOF theo E vs RHE), QsLSV_J-E.png (đường phân cực Qs-LSV), QsLSV_<mẫu>.csv (E RHE, I thô, J quy đổi, TOF, bước, file), QsLSV_TOF_tong_hop.csv (Q, N, số điểm, TOF lớn nhất).
- **Vẽ bằng Origin**: trong công cụ có hai ô tick "Origin" và "Matplotlib". Origin vẽ 3 hình riêng (Qs_CV, Qs_TOF, Qs_LSV_J-E, lưu .png và trong file .opju) theo kiểu/cỡ chữ/khoảng trục ở tab Hình; Matplotlib vẽ TOF_QsLSV.png/.pdf gồm 2 đồ thị (A) CV và (B) TOF. Hình Origin chưa ghép (A)(B) trong cùng một trang - có thể ghép trong Origin bằng Merge Graph Windows.

## Phiên bản Origin được hỗ trợ
App vẽ được với **Origin 2021 trở lên** (thư viện điều khiển originpro yêu cầu Origin 2021+); khuyến nghị 2022 trở lên. Khi vẽ, log in dòng "Origin phien ban noi bo ..." (2021 = 9.8, 2022 = 9.9, 2023 = 10.0, 2024 = 10.1, 2025 = 10.2) để bạn biết app đang điều khiển bản nào. Máy cài nhiều bản Origin thì mở bản bạn muốn dùng trước khi bấm CHẠY. Nếu một lệnh nào đó không được bản Origin cũ hỗ trợ (ví dụ đặt màu), app tự chuyển sang lệnh thay thế hoặc chỉ in cảnh báo rồi vẫn vẽ tiếp.
Origin cũ hơn 2021 (2019, 2020...) không dùng được vì originpro không hỗ trợ; khi đó dùng "Xuất CSV & ảnh Matplotlib".
