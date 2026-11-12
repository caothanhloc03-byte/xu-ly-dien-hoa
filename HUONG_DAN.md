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



## Đo khoảng cách mặt mạng từ ảnh HR-TEM (thay ImageJ)

Tab **Phổ** -> nhóm "Ảnh HR-TEM" -> **Mở công cụ HR-TEM (FFT)...**

1. **Mở ảnh** (jpg/png/tif). App tự đo thanh thang (viền đen dài ở góc dưới) và tính nm/px. Có thể nhập tay độ dài thanh (px) = nm, hoặc nhập thẳng nm/px.
2. **Bấm vào ảnh** tại vùng có vân mạng: app cắt vùng vuông (mặc định 10 nm), tính FFT, tự tìm các đốm nhiễu xạ và đo d theo hai cách độc lập: vị trí đốm trong FFT và khoảng cách giữa các đỉnh trên profile vuông góc vân (trên ảnh gốc, kèm ± SD và số vân).
3. **Chọn đốm** (chọn dòng trong bảng, hoặc bấm vào đốm trên hình FFT; bấm chỗ khác để thêm đốm thủ công). Hai giá trị d lệch > 3%, đốm nổi yếu hoặc ít vân -> app cảnh báo.
4. **Gán pha**: cột "Gợi ý pha" liệt kê mọi mặt chuẩn trong dung sai (Cu, Cu2O, Ni, NiO, Ni(OH)2, Fe, Fe3O4, Fe2O3, CuO; thêm mặt riêng bằng "Mặt chuẩn riêng..."). Nếu nhiều pha cùng khớp (ví dụ Cu(111) 0.209, NiO(200) 0.209, Cu2O(200) 0.214 nm) thì d một mình KHÔNG đủ để kết luận; ô "Chỉ xét pha" giúp lọc theo những pha bạn đã biết từ XRD/XPS.
5. **Thêm vào hình**: mũi tên + nhãn "Pha (hkl) d nm" hiện trên ảnh; kéo nhãn để đặt lại vị trí.
6. **Xuất kết quả**: ảnh chú thích (PNG + PDF 300 dpi), bảng CSV (d FFT, d profile ± SD, góc, z, d chuẩn, lệch %) và hình 4 ô cho từng vùng (vùng, FFT, vân lọc, profile).

Lưu ý độ chính xác: sai số thang thường 1-3% (viền thanh thang dày vài px). Nên kiểm tra bằng một mặt mạng chắc chắn (ví dụ Cu(111) = 0.2087 nm) bằng nút "Hiệu chuẩn theo d chuẩn". Cần bản exe mới (build lại) để cửa sổ này chạy trong bản đóng gói.


### Chạy lại bằng ImageJ (kiểm chứng chéo)

Trong cửa sổ HR-TEM có hàng **ImageJ**: chọn `ImageJ.exe` (hoặc Fiji, `ij.jar`) một lần (nút "Chọn..." hoặc "Tự tìm"), chọn một vùng và một đốm, rồi bấm **Chạy bằng ImageJ (đốm đang chọn)**.

App tự sinh macro `.ijm` làm đúng các bước thủ công: Set Scale (thang nm/px của app), Duplicate vùng, đổi 32-bit, Process > FFT, khoanh đốm + Fill trắng (cả đốm đối xứng), Inverse FFT, Plot Profile vuông góc vân (cả trên ảnh lọc và ảnh gốc). ImageJ chạy, app đọc profile về, đo d và so với phép đo của chính app (lệch > 3% sẽ cảnh báo). Ảnh chụp các bước (vùng, FFT đã khoanh, vân lọc, profile) được lưu và chép kèm khi xuất kết quả.

- Mặc định ImageJ mở cửa sổ để bạn thấy từng bước; tick "Chạy nền" để chạy không hiện cửa sổ.
- Ảnh và macro được chép sang thư mục tạm không dấu (ImageJ đọc đường dẫn tiếng Việt dễ lỗi). Nếu ImageJ không trả kết quả, thanh trạng thái cho biết macro dừng ở bước nào; hộp thoại lỗi (nếu có) hiện trong cửa sổ ImageJ.
- Nút **Lưu macro .ijm...** ghi macro và ảnh vào một thư mục để bạn tự chạy: ImageJ > Plugins > Macros > Run...
- Cột `d_ImageJ_loc_nm` và `d_ImageJ_tho_nm` trong file CSV là d đo từ profile của ImageJ (trên ảnh vân lọc và trên ảnh gốc).


### Danh sách pha và thêm pha riêng

App có sẵn gần 50 pha (kim loại: Cu, Ni, Co, Fe, Au, Ag, Pt, Pd, Ir, Rh, Ru, Al, Pb, Ti, Zn, Mg, Cr, Mo, W, V, Nb, Ta, Sn, Si, Ge, graphit, FeNi3; oxit và hiđroxit: Cu2O, CuO, NiO, CoO, FeO, MnO, MgO, ZnO, TiO2 anatase/rutile, SnO2, CeO2, Al2O3, Cr2O3, Fe2O3, Fe3O4, Co3O4, NiFe2O4, Ni(OH)2, Co(OH)2). Khoảng cách mặt được tính từ hằng số mạng; nên đối chiếu lại với thẻ tinh thể (JCPDS/ICDD) khi viết bài.

- Nút **Chọn pha...** mở hộp chọn pha cần xét (có nhóm sẵn: mẫu Cu-Ni-Fe, kim loại quý, kim loại chuyển tiếp, oxit, hiđroxit). Thu hẹp theo kết quả XRD/XPS để gợi ý bớt nhập nhằng.
- Nút **Mặt chuẩn riêng...** thêm pha khác, mỗi dòng một pha:
  - `Tên (hkl) = d_nm`, ví dụ `Mau X (101) = 0.3333`;
  - hoặc theo hằng số mạng: `Al fcc a=0.405`, `Zn hcp a=0.2665 c=0.4947`, `TiO2 tet a=0.3785 c=0.9514` (kiểu: fcc, bcc, hcp, sc, tet). Dạng này tự sinh các mặt thường gặp, chưa lọc theo quy tắc tắt tiêu, nên hãy kiểm tra lại.

### HR-TEM: thanh công cụ kiểu ImageJ trên ảnh
Thanh công cụ phía trên ảnh (thay cho thanh matplotlib):
- ▭ **Rectangle**: bấm = chọn vùng có cỡ cài sẵn; kéo = tự vẽ vùng vuông (cỡ nm tự điền) → FFT, đo d.
- ╱ **Straight line**: kéo để đo độ dài (px, nm) và góc; **Plot Profile (K)** hiện profile dọc đường, đỉnh và d ± SD.
- ✛ **Point**: bấm để xem x, y, giá trị điểm ảnh.
- 🔍 **Magnifier**: bấm trái phóng to, bấm phải thu nhỏ; cuộn chuột trên ảnh cũng zoom; phím + / -.
- ✋ **Scrolling**: kéo để dịch ảnh. Nút "Zoom 100%" và "Toàn ảnh".
- Góc phải thanh công cụ hiện x, y, giá trị theo con trỏ như ImageJ.
Lưu ý: đây là bộ công cụ do app tự vẽ mô phỏng thao tác ImageJ, không phải cửa sổ ImageJ nhúng vào app.

### HR-TEM: gắn ImageJ thật vào khung ảnh (Windows)
1. Chọn đúng `ImageJ.exe` ở hàng "ImageJ:", mở ảnh trong app, đặt thang nm/px.
2. Bấm **Gắn ImageJ vào ảnh**. App mở ImageJ (tự mở ảnh và đặt thang), chờ 10-30 giây rồi gắn thanh công cụ ImageJ + cửa sổ ảnh ImageJ vào khung bên trái. Thao tác trong khung là ImageJ thật.
3. Bấm lại nút (đang ghi "Tách ImageJ ra...") để trả ImageJ về cửa sổ riêng và quay về ảnh của app. Đóng cửa sổ HR-TEM cũng tự tách trước.
- Hạn chế: thanh menu ImageJ không hiện khi đã gắn (dùng thanh công cụ và phím tắt, hoặc tách ra). Nếu cửa sổ nhận phím/chuột lạ, bấm tách rồi gắn lại.
- Ảnh gắn vào là bản chép; kết quả đo trong ImageJ không tự chuyển về bảng của app.

### Giảm giật lag khi zoom/kéo ảnh
Ảnh lớn (2560x2560...) nay chỉ vẽ phần đang xem, giảm mẫu theo cỡ khung và gộp các lần kéo liên tiếp, nên zoom/dịch ảnh mượt hơn (đo thử: khung vẽ ảnh đầy đủ nhanh gấp ~3 lần).

### Điểm/vùng chọn trong ImageJ tự lưu lên ảnh của app (v38)
- Khi ImageJ đã được app mở (nút "Gắn ImageJ vào ảnh"), một macro nhỏ chạy nền trong ImageJ, cứ 0,25 giây ghi vùng chọn hiện tại ra file để app đọc.
- **Point**: bấm điểm bằng công cụ Point của ImageJ → app tự lưu điểm (đánh số, màu xanh lơ) lên ảnh và vào bảng "Điểm / vùng lấy từ ImageJ" kèm giá trị điểm ảnh. Bấm nhiều điểm (giữ Shift) cũng được.
- **Vùng khác** (Rectangle, Oval, Polygon, Line...): hiện tạm bằng nét đứt vàng trên ảnh app; bấm **Lưu vùng chọn hiện tại** để lưu.
- **Dùng làm vùng đo / FFT**: điểm → vùng đo đặt tại điểm; hình chữ nhật/đa giác → vùng vuông theo cạnh lớn; Line → mở Plot Profile.
- Điểm/vùng đã lưu hiện trên ảnh của app (khi tách ImageJ ra), và xuất ra file `*_chon_imagej.csv` cùng nút Xuất kết quả.
- Thanh công cụ ảnh của app đổi sang nhãn chữ (Chữ nhật, Đường, Điểm, Zoom, Dịch) vì biểu tượng đặc biệt hay hiện thành ô vuông trên Windows; phím K, +, - hoạt động sau khi bấm vào ảnh.

### Thanh công cụ ImageJ bị trống/bị cắt (v39)
Nếu sau khi gắn chỉ thấy dòng menu mà không thấy hàng biểu tượng công cụ: bấm **Làm mới ImageJ** (ép ImageJ bố trí và vẽ lại). App cũng đã đợi ImageJ mở xong hẳn rồi mới gắn và luôn chừa chiều cao tối thiểu cho thanh công cụ.

### Thanh công cụ ImageJ đầy đủ trong app (v40)
Khi bấm "Gắn ImageJ vào ảnh", app gắn **cửa sổ ảnh** ImageJ thật vào khung và dựng **thanh công cụ ImageJ** phía trên:
- Hàng công cụ: Rect, Oval, Poly, Free, Line, Angle, Point, Wand, Text, Zoom, Hand, Picker. Chọn công cụ rồi thao tác trực tiếp trên ảnh ImageJ.
- Menu: Edit (Undo, Select None...), Image (Duplicate, Crop, Brightness/Contrast, Scale...), Process (FFT, Inverse FFT, Smooth, Gaussian Blur, Subtract Background...), Analyze (Measure, Plot Profile, Histogram, Set Scale), Zoom.
- Các nút này gửi lệnh cho ImageJ thật (qua macro nền), nên kết quả (Results, FFT, Plot Profile...) là của ImageJ. "Hiện cửa sổ ImageJ gốc" mở lại cửa sổ ImageJ đầy đủ menu nếu cần lệnh khác.

### Hai mũi tên kẹp đúng một vân (v41)
Khoảng cách giữa hai đầu mũi tên nay đúng bằng "Số vân giữa 2 mũi tên" × d (mặc định **1** = một vân), không còn khoảng hở tối thiểu làm mũi tên bị rộng. Muốn đo trên nhiều vân hơn thì nhập 2, 3...

### Nhập thành phần mẫu → app tự quét và định vị đốm (v42)
Ô **"Thành phần trong mẫu"** (hàng phía trên): nhập tên các pha có trong mẫu, ngăn cách bằng dấu phẩy, kèm số đốm muốn lấy sau dấu `:` — ví dụ `Cu:3, NiO, Fe3O4:2, Ni(OH)2:1`. Tên không kèm số dùng số ở ô "Mặc định". `Co` gồm cả Co (fcc)/(hcp), `TiO2` gồm anatase và rutile. Pha tự thêm ở "Mặt chuẩn riêng..." cũng dùng được.
Bấm **Quét ảnh & tìm đốm** (nút Dừng để hủy). App sẽ:
1. Trượt cửa sổ (cỡ theo ô "Cỡ vùng", bước nửa cửa sổ) trên cả ảnh, FFT từng cửa sổ và tìm đốm.
2. Ghép d của đốm với mặt chuẩn của đúng các thành phần đã nhập (theo dung sai), chấm điểm theo độ nổi z và độ lệch d.
3. Với mỗi thành phần chọn ra đúng số vị trí bạn yêu cầu (tốt nhất trước; các vị trí cách nhau ≥ ~0,9 cỡ vùng, không trùng giữa các thành phần).
4. Đo lại kỹ từng vị trí (FFT + profile) và **loại** nếu d không còn khớp mặt chuẩn, d FFT/profile lệch > 3%, hoặc khoảng cách vân dao động > 6% (vùng giáp ranh). Vì vậy có thể tìm được **ít hơn** số bạn yêu cầu; app báo "chỉ có … ứng viên" — khi đó tăng dung sai, giảm ngưỡng z hoặc đổi cỡ vùng.
Kết quả hiện ngay trên ảnh (nhãn kéo được, bảng "Các phép đo đã thêm"); bấm Xóa dòng để bỏ đốm không ưng. Quét lại sẽ thay các kết quả tự động trước đó, không đụng các phép đo bạn thêm tay.
Lưu ý: chỉ là gợi ý từ d và thành phần bạn khai báo; nhiều pha có d trùng nhau (Cu(111) 0,2087 ≈ NiO(200) 0,2088) nên nhập sát thành phần thật của mẫu sẽ giảm nhầm lẫn.

### Kiểm chứng bằng ImageJ để d chính xác hơn (v43)
Sau khi quét theo thành phần (hoặc bất cứ lúc nào có phép đo trong bảng), bấm **Kiểm chứng tất cả bằng ImageJ** (hoặc để ô "Tự kiểm chứng sau khi quét" được tích; cần đã chọn đúng `ImageJ.exe`):
- App gửi **tất cả vùng** sang ImageJ trong **một phiên** (macro tự tạo): với mỗi vùng ImageJ tự Duplicate → FFT → **tự tìm tâm đốm trong FFT của ImageJ** (độc lập với app) → Fill đốm → Inverse FFT → Plot Profile (ảnh lọc và ảnh gốc).
- Mỗi vùng thu được 5 ước lượng d độc lập: d FFT & d profile của app; d FFT (đỉnh), d profile ảnh lọc, d profile ảnh gốc của ImageJ. **d chung = trung vị** của 5 giá trị.
- Cột "ImageJ" trong bảng: ✓ = 5 phép đo lệch nhau ≤ 3% và d chung vẫn khớp mặt chuẩn trong dung sai, ! = cần kiểm tra (kèm lý do ở dòng trạng thái: lệch nhau, không còn khớp mặt chuẩn, hoặc ImageJ tìm đốm ở hướng khác > 8°).
- Tùy chọn: "Dùng d chung cho nhãn" (mặc định bật; d gốc của app lưu ở `d_app`), "Bỏ đốm không xác nhận". Các cột `d_ImageJ_FFT_nm`, `d_chung_nm`, `xac_nhan_ImageJ` có trong CSV xuất ra; ảnh FFT khoanh đốm và ảnh vân lọc của ImageJ được chép kèm khi xuất.
- Lưu ý: FFT của ImageJ có lưới 512x512 nên d FFT của ImageJ thô hơn (±1%); vì dùng trung vị nên một ước lượng lệch không kéo d chung đi. Chưa được chạy thử trên ImageJ thật — nếu macro báo lỗi, gửi tôi bước dừng ở dòng trạng thái.

### XPS: hiệu chuẩn, fit thành phần kiểu CasaXPS, vẽ Origin (v44)
Mở tab **Phổ → Mở công cụ XPS...**. App **không điều khiển được phần mềm CasaXPS** (CasaXPS không có giao diện lệnh); thay vào đó app đọc dữ liệu từ CasaXPS và tự làm lại đúng các bước: hiệu chuẩn, nền Shirley, fit GL(30), Residual STD.
1. **Mở file XPS**: file `.vms` (VAMAS) của CasaXPS, hoặc file text/CSV/Excel xuất từ Casa (File > Export, hoặc copy bảng số). Chọn vùng C1s (khoảng 296–280 eV). Nếu `.vms` không đọc được, hãy xuất text từ CasaXPS rồi mở file đó.
2. **Hiệu chuẩn**: tìm đỉnh cao nhất trong khoảng 290–280 eV (giống ô *Measured* của CasaXPS) rồi dịch phổ để đỉnh về **284.8 eV**. Sau khi fit, nếu thành phần C-C lệch khỏi 284.8 thì dịch lại để C-C đúng 284.8 (chính xác hơn dùng đỉnh bao). Độ dịch tổng được báo ở kết quả; cùng độ dịch có thể áp cho Ni2p, O1s... của cùng mẫu.
3. **Thành phần**: bảng văn bản, mỗi dòng `Tên | vị trí | vị trí min | vị trí max | FWHM | FWHM min | FWHM max`. Mẫu C1s có sẵn: C-C/C=C/C-H (284.8), C-O (285.8–286.9), O-C=O (287.9–289.3), FWHM 0.8–2.0 eV. Cửa sổ vị trí/độ rộng là **ràng buộc hoá học** nên kết quả không trôi cho "đẹp số". Sửa tự do theo mẫu của bạn.
4. **Thành phần ứng viên** (C=O, π-π*): chỉ được thêm khi **kiểm định F** (p < 0.01) cho thấy cải thiện có ý nghĩa, chiếm ≥ 1% diện tích và nằm trong cửa sổ hoá học. Lý do thêm/không thêm được ghi rõ.
5. **Residual STD**: kiểu CasaXPS (phần dư chia nhiễu Poisson kỳ vọng); nhập **dwell × số scan (giây)** nếu biết để chính xác (không nhập thì ước lượng nhiễu từ dữ liệu, kém chắc hơn). Mục tiêu ≈ 1. App **không ép** số này: nếu > 1.5 hoặc phần dư còn cấu trúc, mục "Nhận xét" nói rõ nguyên nhân có thể (nền, đỉnh chồng lấn như Ru 3d3/2 ở ~284 eV, tích điện) thay vì thêm đỉnh vô nghĩa. Thành phần chạm biên ràng buộc được đánh dấu `*` và nêu trong Nhận xét.
6. **Xuất CSV + hình**: `*_fit.csv` (BE, thô, nền, bao, phần dư, từng thành phần), `*_muot.csv` (đường cong mịn đã trừ nền, dùng vẽ), `*_thanh_phan.csv` (vị trí, FWHM, diện tích, %, Residual STD, độ dịch), hình PNG/PDF đúng kiểu hình mẫu (vùng tô màu, đường bao xám đậm, trục BE đảo, không vạch trục Y).
7. **Vẽ ra Origin**: ghi các file trên rồi mở Origin, tạo sổ dữ liệu + đồ thị (đường bao + thành phần, trục BE đảo chiều, ẩn vạch trục Y, tên hình ở góc). Nếu Origin không tô màu vùng dưới đường (lệnh khác nhau theo phiên bản), bật bằng Plot Details > Line > Fill Area Under Curve.
Lưu ý khoa học: gán thành phần chỉ là gợi ý từ vị trí; với mẫu có Ru, kiểm tra Ru 3d3/2 (~284 eV) chồng lên C1s và dùng Ni2p/O1s/Ru3d để đối chiếu.


## v46 - XPS theo hướng dẫn chuẩn
- Đọc file .vms của CasaXPS theo đúng chuẩn VAMAS (từng block, trục KE tự đổi sang BE = hv − KE); tự điền dwell×scan.
- Ô "Chênh FWHM tối đa" (mặc định 0.2 eV): các thành phần cùng họ giữ độ rộng gần nhau, theo khuyến nghị ±10% / ±0.1 eV. Shake-up không bị ràng buộc. Nhập 0 để tắt.
- Cảnh báo: FWHM nhỏ hơn phân giải máy, FWHM lệch nhiều, và lưu ý khi hiệu chuẩn C1s = 284.8 eV không phù hợp với mẫu.
- File .vms không phải XPS (ví dụ dữ liệu SIMS) sẽ báo không có phổ.


## v47 - XPS: các tính năng mới
- **Màu & tô vùng...**: chọn màu từng thành phần, bật/tắt tô vùng dưới đường, độ đậm, màu và độ dày đường bao, hiện điểm thô. Áp dụng cho hình xem trước, PNG/PDF và hình vẽ trong Origin (app ghi file `*_kieu.json` cho Origin). Nếu bản Origin của bạn không nhận lệnh tô, mở Plot Details > Line > Fill Area Under Curve.
- **Doublet spin-orbit**: thêm 2 ô cuối vào dòng thành phần: `| tách (eV) | tỉ lệ diện tích`. Ví dụ Ti 2p: `| 5.7 | 0.5`. Đỉnh thứ hai cùng FWHM, tách và tỉ lệ cố định.
- **Mẫu mới**: N1s, Ti2p, S2p, Ru3d+C1s. Chọn mẫu sẽ tự đặt vùng fit.
- **Dịch sẵn / Dùng dịch này cho vùng khác**: fit C1s xong, bấm nút để dùng cùng độ dịch cho O1s, N1s, Ti2p... của cùng mẫu (các vùng không có C-C không tự hiệu chuẩn theo C-C).
- **Định lượng nguyên tố (RSF)**: % nguyên tử từ diện tích sau nền Shirley chia RSF Scofield (lấy từ thư viện CasaXPS), chia thêm dwell×scan. Bán định lượng, chưa hiệu chỉnh hàm truyền máy.
- **Lưu/Nạp mô hình** (.json) và khi xuất có thêm `*_bao_cao.txt`, `*_mo_hinh.json` để ghi vào phần Methods/SI.


## v48 - XPS: Tougaard, đỉnh bất đối xứng, chọn vùng bằng chuột
- **Nền Tougaard U2**: chọn trong ô "Nền". Nền dựa trên tiết diện mất năng lượng phổ quát (C = 1643 eV²), hệ số B tự khớp với đuôi BE cao. Vùng fit nên kéo rộng về phía BE thấp để nền đúng. Dùng khi nền có bậc rõ (Shirley không đủ).
- **Đỉnh bất đối xứng cho kim loại**: thêm ô cuối `| LA(a,b)` vào dòng thành phần. a là số mũ đuôi BE thấp, b là số mũ đuôi BE cao (1 = Lorentz, số mũ nhỏ = đuôi dài), nên kim loại thường a > b, ví dụ `LA(1.8,1.0)`. Đỉnh được chập với Gauss (độ lệch = 0.2 × FWHM). Mẫu mới **Au4f** (doublet + LA) hiệu chuẩn Au 4f7/2 về 84.0 eV. Tham số LA chỉ là điểm xuất phát: nên tối ưu trên mẫu kim loại chuẩn của chính máy bạn rồi cố định cho mẫu thật.
- **Kéo chuột chọn vùng**: mở file là thấy phổ thô. Bấm "Kéo chuột chọn vùng fit" hoặc "Kéo chuột chọn khoảng dò đỉnh", rồi kéo trên hình; các ô số tự cập nhật. Sau khi fit, bấm nút kéo chuột sẽ hiện lại phổ thô; bấm "Hiệu chuẩn + Fit" để quay lại kết quả.


## v49 - XPS: chứng minh kết quả
Sau khi fit, bấm **Chứng minh kết quả...** (mất vài chục giây). App tự kiểm định và ghi báo cáo `*_chung_minh.txt` khi xuất:
1. **Phần dư**: Residual STD (cần 0.85-1.15), tỉ lệ điểm trong ±2σ (~95%), Durbin-Watson, kiểm định chuỗi dấu, quét "đỉnh ẩn" trên phần dư.
2. **Số thành phần**: bỏ từng thành phần rồi fit lại (F-test, p < 0.01 = cần thiết); thử thêm từng ứng viên chưa dùng (p, chạm biên, % diện tích); đối chiếu số đỉnh/vai nhìn thấy (đạo hàm bậc hai) giữa dữ liệu và mô hình.
3. **Độ bền**: đổi nền (Shirley/Tougaard/Tuyến tính) và dịch vùng fit ±0.5 eV; báo biên độ dao động % diện tích và vị trí.
4. **Sai số**: Monte Carlo 30 mẫu theo nhiễu Poisson: ± sd cho vị trí, FWHM, % diện tích.
5. **Kết luận** từng tiêu chí (ĐẠT / CHƯA / LƯU Ý). Nếu chưa đạt, app không thêm đỉnh để ép Residual STD về 1 mà nói rõ lý do.
Lưu ý: nhập đúng dwell×scan (file .vms tự điền) thì "Residual STD ≈ 1" mới có sức chứng minh.


## v50 - XPS: báo cáo chứng minh dễ hiểu + đề xuất phương án
- Báo cáo mở đầu bằng **TÓM TẮT** 4-5 dòng, mỗi mục có câu hỏi và giải thích bằng lời thường, cuối có bảng **giải thích thuật ngữ**.
- Mục 5 liệt kê các **phương án fit** app đã thử (giữ nguyên, bỏ/thêm thành phần, đổi nền Shirley/Tougaard/Tuyến tính, nới ràng buộc FWHM), mỗi phương án có **ưu điểm / nhược điểm** và bảng so sánh (Residual STD, điểm BIC, số thành phần).
- App **đề xuất một phương án**: chỉ xét phương án hợp lệ (mọi thành phần >= 1%, Residual STD <= 1.3, phần dư ngẫu nhiên), chọn BIC thấp nhất (đã phạt chạm biên); giữ nguyên nếu kết quả hiện tại hợp lệ và không kém quá 6 điểm.
- Dưới cửa sổ báo cáo có ô chọn phương án và nút **Áp dụng phương án này** để thay kết quả đang hiển thị.


## v51 - Công cụ XRD (tab Phổ -> "Mở công cụ XRD...")
Thay cho nhóm "Phổ XRD / Raman / XPS" cũ (các tuỳ chọn cũ vẫn dùng được ngầm khi chọn Loại = Phổ ở tab Dữ liệu).
1. **Mở file XRD**: Excel (nhiều cặp cột 2θ - cường độ, mỗi cặp một mẫu) hoặc text/CSV. Mẫu trùng hệt dữ liệu sẽ bị bỏ qua. Có nút đổi tên mẫu.
2. **Phân tích + xác định pha**: nhập các nguyên tố có thể có (vd `Ni Ru C O`), chọn nguồn tia X (Cu Kα...). App tìm đỉnh (tách cả Kα2), ước độ lệch 2θ chung, rồi đối chiếu với ngân hàng phổ.
3. **Ngân hàng phổ**: ~20 pha tích hợp (Ni, NiO, Ni(OH)2, Ru, RuO2, graphite, ...) có vạch tính từ cấu trúc tinh thể (số PDF chỉ để tham khảo, cường độ là gần đúng). Nút "Ngân hàng phổ..." cho thêm pha từ **file CIF** hoặc **bảng vạch gõ tay từ thẻ JCPDS**; lưu trong `%APPDATA%\DienHoaOrigin\ngan_hang_xrd.json`.
4. **Phân loại từng đỉnh**: đỉnh của pha mẫu / của đế (Ni foam) / gợi ý chưa đủ bằng chứng / bức xạ phụ (Kβ, W Lα) / đỉnh lạ chưa xác định.
5. **Minh chứng** (tab "Kết quả + minh chứng"): độ lệch 2θ, vạch khớp và sai lệch, vạch đáng lẽ phải thấy mà không thấy, xác suất trùng ngẫu nhiên, hằng số mạng đo được so với chuẩn, kích thước tinh thể (Scherrer), pha đã kiểm tra nhưng không thấy. "Không thấy" nghĩa là dưới giới hạn phát hiện, chưa chắc không có.
6. **So sánh các mẫu**: chọn mẫu chuẩn (thường NF). App liệt kê đỉnh MỚI so với chuẩn (kèm pha gán được), đỉnh bị mất và đỉnh đổi cường độ trên 1.5 lần.
7. **Xuất / vẽ Origin**: `*_xep.csv`, `*_dinh.csv`, `*_bao_cao.txt`, `*_nhan.json`, hình Matplotlib PNG/PDF; "Vẽ ra Origin..." tạo hình xếp chồng (khung kín, tên mẫu màu bên trái, không vạch trục Y, nhãn pha trên đỉnh). Nhãn chữ trong Origin đặt theo toạ độ dữ liệu, có thể cần chỉnh tay tuỳ bản Origin; hình Matplotlib luôn có đủ nhãn.


## v52 - XRD: ký hiệu pha kiểu bài báo
Hình xếp chồng không còn ghi tên pha dọc theo đỉnh. Mỗi pha có **một ký hiệu và một màu cố định** (★ đen cho pha của đế/mẫu chuẩn, rồi ● ■ ◆ ▲ ...), đặt trên đỉnh kèm **(hkl)** cùng màu; **chú giải pha** ở góc trên bên trái. Đỉnh gợi ý yếu có dấu `?` sau (hkl); đỉnh chưa xác định chỉ có dấu `?` đỏ. Áp dụng cho hình xem trong app, hình Matplotlib và hình Origin (ký hiệu vẽ bằng chữ ★ ● ■ ◆, có thể chỉnh cỡ/vị trí trong Origin). File `*_nhan.json` chứa ký hiệu, màu và chú giải nếu bạn muốn vẽ lại bằng công cụ khác.


## v53 - XRD: ngân hàng phổ phong phú hơn (66 pha)
Ngân hàng tích hợp tăng từ 17 lên **66 pha**, chọn theo vật liệu điện hoá thường gặp. Vạch của mọi pha được **tính từ cấu trúc tinh thể** (hằng số mạng + vị trí nguyên tử + nhóm không gian), vị trí và cường độ đã đối chiếu với đỉnh JCPDS đã biết (có bài kiểm tra tự động).
- **Kim loại**: Ni, Co, Fe, Cu, Ag, Au, Pt, Pd, Al, Ru, Ir, Rh, Pb, Mo, W, Cr, V, Nb, Ta, Ti, Zr, Zn, Mg, Cd, Re, Os, Si, kim cương.
- **Oxit đơn giản**: NiO, CoO, FeO, MnO, MgO, CdO, Cu2O, CuO, Ag2O, ZnO, TiO2 (rutil, anatas), RuO2, IrO2, SnO2, MnO2 (β), CeO2, ZrO2 (lập phương), Cr2O3, α-Fe2O3.
- **Spinel / perovskit**: Co3O4, Fe3O4, NiCo2O4, NiFe2O4, ZnCo2O4, SrTiO3, LiCoO2.
- **Hiđroxit**: Ni(OH)2, Co(OH)2, Mn(OH)2, Fe(OH)2, Mg(OH)2 (đã bỏ qua H nên cường độ vạch (001) chỉ gần đúng).
- **Khác**: MoS2, WS2, WC, TiN, graphit.
Lưu ý: số PDF chỉ ghi cho các thẻ chắc chắn, các thẻ khác để trống (bạn thêm bằng CIF/bảng vạch). Cường độ tương đối là gần đúng (không tính định hướng ưu tiên, không tính tạp). Pha phức tạp chưa có (ITO, NiOOH, Mn3O4, perovskit La-Ni-Co-O...): dùng "Thêm từ file CIF" hoặc "Thêm từ bảng vạch (thẻ PDF)".
Mẹo: ô "Nguyên tố có thể có" càng sát thực tế thì kết luận càng chắc; để trống để thử toàn bộ 66 pha (trên dữ liệu Rug_NF kết quả vẫn không đổi, không có pha nào bị gán nhầm).


## v54 - XPS xuất sang CasaXPS; XRD tự quét ngân hàng, tick và sắp xếp mẫu
**XPS -> CasaXPS**
- Sau khi fit, bấm **Xuất sang CasaXPS...** hoặc tick **"Vẽ Origin thì xuất luôn sang CasaXPS"** (mặc định bật) rồi bấm "Vẽ ra Origin...": app vừa vẽ Origin vừa ghi file cho Casa.
- File `*_casa.vms` (chuẩn VAMAS, đọc lại được bằng chính bộ đọc đã thử trên file Casa thật) gồm các khối: **Raw** (phổ đã hiệu chuẩn), **Background**, **Envelope**, từng **thành phần** (đã cộng nền nên chồng đúng lên phổ thô) và **Residual**. Trong Casa: File > Open, rồi chồng các khối bằng Display > Overlay.
- File `*_casa_thanh_phan.txt`: bảng vị trí, FWHM, diện tích, %, dạng đỉnh (GL(30)/LA) để tạo lại thành phần trong Casa nếu muốn fit ngay trong Casa.
- Nếu máy Windows có cài CasaXPS ở thư mục mặc định, app hỏi có mở luôn không.
- Giới hạn: Casa không có giao diện lệnh bên ngoài nên các thành phần xuất ra là các phổ riêng, không phải "component" gốc của Casa.

**XRD**
- Ô nguyên tố mặc định **để trống = tự quét toàn bộ 66 pha** của ngân hàng; vẫn có thể gõ nguyên tố (vd `Ni O`) để giới hạn. Thanh trạng thái cho biết đã quét bao nhiêu pha và pha nào xác định được.
- Hàng **"Mẫu"**: tick/bỏ tick để dùng hoặc loại một phổ; nút **▲▼** đổi thứ tự (mẫu đầu nằm dưới cùng trên hình). Đổi tick hoặc thứ tự thì phân tích và hình tự cập nhật; file xuất ra cũng theo đúng thứ tự và các mẫu đã tick.


## v55 - Sửa: mở CasaXPS sau khi vẽ
- "Vẽ ra Origin..." kèm tick Casa: sau khi Origin vẽ xong, app **tự mở CasaXPS** với file `*_casa.vms` (bản v54 chỉ ghi file, không mở).
- Tìm `CasaXPS.exe` tự động; không thấy thì hỏi bạn chọn file `CasaXPS.exe` **một lần** (nhớ trong `%APPDATA%\DienHoaOrigin\casa_exe.txt`). Nếu bỏ qua, app nhờ Windows mở bằng chương trình mặc định của file `.vms`.
- Casa không tự vẽ chồng các khối: khi đã mở, chọn các khối rồi Display > Overlay.


## v56 - Sửa file .vms cho CasaXPS
Bản v54-v55 ghi file `*_casa.vms` theo bố cục tối giản nên Casa có thể báo "Error Opening VAMAS File". Bản này ghi đúng bố cục file Casa tự ghi (đối chiếu từng dòng với `SiTemplate.vms` trong gói Casa): header 5 dòng + dòng chú thích, khai báo biến thí nghiệm, xuống dòng kiểu Windows (CRLF), hai biến Intensity và Transmission, giá trị không xác định 1e+037. Nếu Casa vẫn báo lỗi, gửi file `*_casa.vms` bị lỗi để đối chiếu tiếp.


## v57 - Sửa lỗi "Error Opening VAMAS File" trong CasaXPS
Nguyên nhân nghi ngờ nhất: dòng chú thích "Casa Info Follows" khiến Casa đọc thêm các dòng thông tin riêng của Casa (hiệu chuẩn, vùng, thành phần) mà file do app ghi không có, nên Casa đọc lệch dòng. Bản này ghi chú thích thường ("Echem Studio") thay cho dấu đó. Nếu vẫn lỗi, gửi file `*_casa.vms` bị lỗi để đối chiếu tiếp.


## v58 - Sửa lỗi Casa "Error Opening VAMAS File" do đường dẫn
Thử nghiệm cho thấy cùng file mở được khi đặt ra màn hình chính, nên nguyên nhân là **đường dẫn**: CasaXPS bản cũ không đọc được đường dẫn có chữ có dấu, khoảng trắng, ký tự lạ hoặc quá dài. App nay: (1) đặt tên file `*_casa.vms` chỉ gồm chữ không dấu; (2) trước khi mở Casa, chép file sang thư mục ngắn không dấu (`C:\Users\Public\EchemCasa`) nếu đường dẫn gốc không an toàn. Nếu tự mở file trong Casa, hãy để file ở thư mục có đường dẫn ngắn, không dấu (ví dụ `C:\XPS`).


## v59 - CasaXPS tự dựng thành phần fit
Khi xuất sang CasaXPS, ngoài `*_casa.vms` (các khối chồng bằng Display > Overlay) app ghi thêm **`*_casa_fit.vms`**: một khối phổ thô kèm vùng nền và các thành phần ở dạng Casa tự hiểu (dòng `CASA region` / `CASA comp`, cú pháp lấy từ file Casa thật). Mở file này, Casa tự dựng đường bao và các thành phần ngay trên phổ, như khi bạn tự fit. App mở file này trước.
Giới hạn: Casa tính lại hình đỉnh theo định nghĩa của nó nên diện tích/% có thể lệch nhẹ so với app; nền Tougaard ghi "None"; đỉnh bất đối xứng LA ghi dạng GL(30); doublet được tách thành hai thành phần độc lập (không ràng buộc diện tích/vị trí với nhau). Nếu `*_casa_fit.vms` báo lỗi, vẫn dùng `*_casa.vms`.


## v60 - Casa hiện giống như tự fit trong Casa
Nếu bạn mở file `.vms` gốc (từ Casa/máy đo) rồi fit trong app, khi xuất sang CasaXPS app ghi thêm **`*_casa_goc.vms`**: bản sao **nguyên file gốc** (mọi khối C 1s, Ni 2p, O 1s, Ru 3d, Survey... giữ nguyên) trong đó khối bạn đã fit được thêm vùng nền và các thành phần ở dạng Casa tự hiểu. Mở file này trong Casa sẽ thấy đúng bố cục file gốc, khối đã chọn có đường bao và từng thành phần có màu. App mở file này trước.
- Vị trí thành phần ghi về **thang BE gốc** của file (chưa hiệu chuẩn); trong Casa muốn hiển thị BE đã hiệu chuẩn thì dùng chức năng hiệu chuẩn của Casa với cùng độ dịch (app ghi trong báo cáo).
- **Residual, "Residual STD", nhãn tên thành phần trên đỉnh, tiêu đề** là cài đặt hiển thị của Casa (lưu trong cấu hình của Casa, không nằm trong file .vms). Muốn hiện: trong Casa mở hộp thoại thông số hiển thị và bật các mục Residual, Residual StDev (và tên thành phần). Bật một lần là các file sau đều hiện.
- Màu thành phần do Casa tự gán theo thứ tự (đỏ, xanh lá, xanh dương...) và đổi được trong bảng Components.
- Casa tính lại hình đỉnh theo định nghĩa của nó, nên diện tích/% có thể lệch nhẹ so với app.


## v61 - Số liệu XPS khớp Casa (Counts → CPS)
- File .vms có nhãn tung độ "Counts": Casa hiển thị **CPS = Counts/(dwell × scan)**. Trước đây app dùng thẳng số đếm nên diện tích lớn gấp (dwell×scan) lần (ví dụ 1.5 lần với 0.05 s × 30 scan) và Residual STD sai.
- Nay app tự đổi sang CPS khi đọc file (nhãn "Intensity"/CPS giữ nguyên). Diện tích tính bằng CPS·eV như Casa; file *_casa_goc.vms dùng cùng thang.
- Mở lại file gốc, fit lại rồi xuất Casa để dùng số liệu mới.


## v62 - Tự chỉnh để Residual STD ≈ 1
- Khi Residual STD > ~1.08, app tự: (1) nới cửa sổ vị trí (Pos. Constr., tối đa ±1 eV như Casa) và FWHM của các thành phần không phải C-C; (2) thử vài biên vùng fit gần vùng bạn chọn; chọn phương án có Residual STD gần 1 nhất, không chạm biên.
- Không ép số bằng đỉnh vô nghĩa: đỉnh mới chỉ thêm khi qua kiểm định F. Mọi thay đổi ghi trong phần nhận xét của báo cáo.
- Cần biết dwell×scan (file .vms có sẵn) thì mới chạy. Một lần fit có thể mất vài chục giây.


## v63 - So với Casa
- Nút **So với Casa...** (cửa sổ XPS): (1) số Casa đã lưu trong file .vms (fit trong Casa rồi File > Save, mở file đó trong app - số này do chính Casa tính nên trùng tuyệt đối); (2) app tính lại kiểu Casa trên cùng vùng và giá trị bắt đầu của Casa, kèm % lệch từng diện tích.
- Lệch còn lại (vài %) đến từ vùng fit lệch ~0.05 eV, cách lấy đầu nền Shirley và điểm xuất phát; C-C/C-O chồng nhau nên đáy sai số rất phẳng.


## v64 - Quy trình app → Casa → app
1. Mở file thô, bấm **Hiệu chuẩn + Fit** (app nhận diện đỉnh, ràng buộc, kiểm định).
2. **Vẽ ra Origin** có tick "vẽ kèm Casa" hoặc **Xuất sang CasaXPS** → Casa mở file *_casa_goc.vms với vùng, nền và thành phần của app.
3. Trong Casa bấm **Fit Components** (Casa tự tinh chỉnh bằng thuật toán của nó) rồi **File > Save**.
4. Về app bấm **Nhận kết quả từ Casa...**, chọn file vừa lưu: bảng, hình, Origin, báo cáo và **Chứng minh kết quả** dùng đúng số Casa.
Phần Residual STD hiển thị trong app tính bằng nền Shirley của app nên có thể lệch nhẹ so với số Casa hiện; vị trí, FWHM, diện tích giữ nguyên số Casa.


## v65 - Tự động fit trong Casa
- Cần: Windows, `pip install pywinauto` (build.bat đã thêm; bản chạy từ mã nguồn thì tự cài).
- Fit trong app xong, bấm **Tự động fit trong Casa**: app ghi file Casa, mở Casa, bấm **Fit Components** (2 lần), **File > Save**, rồi tự nhận số Casa vào bảng/hình/chứng minh. Đừng chạm chuột/bàn phím trong Casa khi chạy.
- Nếu lỗi: xem `casa_tu_dong_log.txt` (cùng thư mục file tạm, đường dẫn hiện trên thanh trạng thái) - file liệt kê cửa sổ và nút của Casa; gửi file này để chỉnh đúng tên nút/menu của bản Casa bạn dùng.
- Mở sẵn cửa sổ Quantification Parameters (tab Components) trong Casa nếu app báo không tìm thấy nút Fit Components.


## v66 - Giao diện XPS gọn
- Một hàng nút chính: **▶ Fit**, **✓ Chứng minh**, **⬆ Origin**, **💾 Xuất**; hai menu **◧ Casa ▾** (xuất sang Casa, tự động fit, nhận kết quả, so với Casa) và **🛠 Công cụ ▾** (kéo chuột chọn vùng, màu, dịch, RSF, lưu/nạp mô hình). Rê chuột lên nút để xem chú thích.
- **⚙ Thiết lập thành phần ▸** bấm để mở/thu gọn (mẫu, dịch sẵn, FWHM tối đa, bảng thành phần). Mặc định thu gọn.
- Hàng thông số tách thành hai hàng (hiệu chuẩn / vùng fit - nền - dwell×scan) nên cửa sổ nhỏ vẫn thấy đủ.


## v67 - Tự động Casa dùng F7
- Casa của bạn mở cửa sổ Quantification Parameters bằng **F7**; tự động hoá nay gửi F7 (tối đa 3 lần), chọn tab Components rồi bấm Fit Components. Vẫn lỗi thì gửi lại file casa_tu_dong_log.txt.


## v68 - Tự động Casa: tìm nút Fit Components chắc hơn
- Nút của Casa có thể là điều khiển tự vẽ (không có chữ để tìm): app tìm theo chữ trước, không được thì bấm theo vị trí tương đối (≈50% ngang, 64% cao) trong hộp Quantification Parameters. Nếu bấm sai chỗ, gửi lại casa_tu_dong_log.txt để chỉnh tỉ lệ.


## v69 - Fit bằng Casa
- Số liệu đáng tin là số do Casa tính. Tick **Fit bằng Casa** (mặc định bật trên Windows): bấm **▶ Fit** → app dựng mô hình → mở Casa → F7 → tab **Components** → Fit Components (2 lần) → File > Save → số Casa về app (bảng, hình, Chứng minh, Origin).
- Lỗi cũ: hộp Quantification Parameters mở ở tab Regions nên bấm trượt; nay luôn bấm sang tab Components trước.
- Bỏ tick nếu chỉ muốn fit bằng app. Lỗi thì gửi casa_tu_dong_log.txt.


## v70 - Số nhận từ Casa sát Casa hơn
- Vị trí, FWHM, diện tích: giữ NGUYÊN số Casa. Nền Shirley dùng một điểm mỗi đầu (Casa: Av. Width 0), nên đường nền, phần dư và Residual STD hiển thị sát số trong Casa.


## v71 - Giữ BE đúng như Casa
- Khi nhận số từ Casa, tick **Giữ BE đúng như Casa** (mặc định bật): vị trí C-C và mọi đỉnh giữ đúng giá trị Casa đã fit (ví dụ 285.29 eV), không ép C-C về 284.8. Bỏ tick nếu muốn app hiệu chuẩn C-C về năng lượng chuẩn.


## v72 - Sửa lỗi gốc: hình dạng đỉnh GL(30) khớp Casa
- Nguyên nhân app lệch Casa: đường cong GL(30) của app chỉ cắt mức 0.5 tại ±0.474×FWHM thay vì ±0.5×FWHM (Casa dùng FWHM thật). Nên cùng một số liệu, đỉnh app hẹp hơn ~4%: phần dư có vết lõm ở đỉnh C-C (-157 CPS), FWHM app lớn hơn Casa ~4%, Residual STD cao (1.43 so với 1.061).
- Đã sửa: GL(m) co trục để FWHM là bề rộng thật. Thử với số Casa của bạn (C-C 5361.1 / 1.23 / 285.2931; C-O 268.2 / 0.956 / 286.6399; O-C=O 649.8 / 2.177 / 288.5863): vết lõm ở đỉnh biến mất (-157 → ~-3 CPS), Residual STD 1.10 (Casa 1.061).
- Phần còn lệch nhỏ (0.04) do đầu nền Shirley: Casa lấy đầu nền theo cách riêng (điểm đầu nhiễu), app dùng trung bình 2 điểm mỗi đầu khi nhận số từ Casa.
- Fit đã lưu trước v72 (mô hình .json) có FWHM theo kiểu cũ: nên fit lại.


## v73 - Lấy nguyên số liệu từ Casa
- Sau Fit Components + File > Save, app tự: quét các nút thanh công cụ Casa (đọc mô tả trên thanh trạng thái, nhớ vào `~/.echem_casa_toolbar.json`), bấm nút **Copy Spectra to Clipboard TAB ASCII** (hoặc Save TAB ASCII), tick các ô Background/Component/Envelope/Residual nếu có hộp thoại, đọc clipboard và lưu `*_casa_so_lieu.txt` cạnh file .vms.
- Bảng, hình, Chứng minh, Origin dùng đúng các cột Casa: phổ thô, nền, đường bao, từng thành phần, phần dư. Vị trí/FWHM/diện tích lấy từ file .vms Casa đã lưu. App không tính lại nền/phần dư; kèm dòng đối chiếu "căn tổng bình phương phần dư (counts)" để so với **RMS** trong cửa sổ Components của Casa.
- Nếu bước xuất không chạy, app báo lý do và dùng số trong file .vms (như v71-72). Lỗi: gửi `casa_tu_dong_log.txt` (có danh sách mô tả mọi nút thanh công cụ) và `*_casa_so_lieu.txt` nếu có.
- Muốn quét lại nút (Casa đổi bố cục): xoá `~/.echem_casa_toolbar.json`.


## v76 - Bản 73 chỉ bỏ tự động click Casa
- Mọi chức năng như bản 73 (giao diện gọn, ▶ Fit, ✓ Chứng minh, ⬆ Origin kèm Casa, ◧ Casa ▾: Xuất sang CasaXPS / Nhận kết quả từ Casa / So với Casa, 🛠 Công cụ ▾, GL(30) khớp FWHM thật như Casa).
- Đã bỏ: nút "Tự động fit trong Casa", ô "Fit bằng Casa" (tự bấm) và thư viện pywinauto.
- Fit bằng Casa làm tay: **Xuất sang CasaXPS** (hoặc Origin kèm Casa) → trong Casa bấm **F7**, tab **Components**, **Fit Components**, **File > Save** → **Nhận kết quả từ Casa...**.


## v77 - Vẽ Origin từ file Casa
- Menu **◧ Casa ▾ > Vẽ Origin từ file Casa...**: chọn file `.vms` bạn đã fit xong và File > Save trong Casa → app nạp đúng vị trí/FWHM/diện tích của Casa → chọn thư mục lưu → Origin vẽ hình từ số đó (nền, đường bao, từng thành phần, phần dư).
- Không cần mở file trước hay bấm Fit. Tick "Giữ BE đúng như Casa" quyết định có ép C-C về 284.8 hay giữ nguyên BE Casa.


## v79 - Nối tiếp thời gian i-t
- Tab điện hóa, nhóm vẽ chồng: tick **Nối tiếp thời gian các đường i-t (cộng dồn)** (cùng với "Vẽ chồng các file cùng loại"). Các file i-t được nối đuôi nhau theo thứ tự đã chọn; file sau bắt đầu ngay khi file trước kết thúc. Áp dụng cho hình Matplotlib, hình bài báo và Origin.


## v80 - Gói nộp bài
- Tab **Xuất**: tick **Kèm gói nộp bài** (cùng với Xuất báo cáo Excel) rồi CHẠY.
- Báo cáo Excel có thêm: **Bảng nộp bài** (mỗi mẫu một dòng: quá thế, Tafel, thời gian đo, % giữ dòng, FE), **Lặp lại (TB ± SD)** (đặt tên mẫu `Mau-1`, `Mau-2`, `Mau-3` để app tự gộp), **Kiểm tra nộp bài** (Đạt / Thiếu / Cần xem kèm việc cần làm).
- Thư mục kết quả có thêm `methods_dien_hoa.txt` (đoạn Methods tiếng Anh; phần [trong ngoặc vuông] bạn tự điền: điện ly, điện cực tham chiếu, tải lượng...) và `goi_tai_lap.zip` (dữ liệu thô, kết quả, tham số, phiên bản, câu Data availability) để đưa vào SI hoặc Zenodo.
- Mẹo để được nhận diện: đặt tên có `Pt/C` cho mẫu chuẩn, `bare`/`NF`/`undoped` cho đối chứng, `sau`/`after` cho mẫu sau thử bền.
- Hàng nút biểu tượng ở "Mở nhanh": 📁 thư mục · 📊 báo cáo · 📝 Methods · 📦 gói tái lập · 🧾 nhật ký (rê chuột để xem chú thích).


## v81 - Đối chiếu chéo & trước/sau thử bền
- Tab **Phổ**, nhóm cuối, nút **🔗**: nhập đỉnh XRD (2θ, FWHM), d HR-TEM, kích thước hạt TEM, BE XPS; bấm **Đối chiếu**. App báo Khớp / Không khớp cho d HR-TEM so với d tính từ XRD (Bragg, dung sai 3%), Scherrer so với TEM, BE XPS so với bảng tham khảo (chỉ để định hướng, phải dẫn tài liệu).
- Ô "trước/sau thử bền": đỉnh XRD và BE XPS được phân loại Giữ (kèm độ dịch), Biến mất, Mới. Nút 📋 chép kết quả.
- Sheet "Kiểm tra nộp bài" thêm mục 9.3: nhớ thêm 500 vào "mật độ dòng mục tiêu" nếu LSV đạt tới.


## v82 - Hoàn thiện gói nộp bài
Tab **Xuất**, nhóm "Nộp bài & dự án" (rê chuột vào nút để xem chú thích):
- 🧪 **Điều kiện đo**: điện ly, điện cực tham chiếu/đối, máy đo, nhiệt độ, điện cực làm việc, mực xúc tác. Tự điền vào `methods_dien_hoa.txt` và mục 7.6.
- 🏷 **Vai trò mẫu**: gán Mẫu chính / Chuẩn (Pt/C, RuO₂/IrO₂) / Đối chứng / Sau thử bền và **nhóm lặp lại** (các mẫu cùng nhóm tính TB ± SD). Vai trò được gợi ý từ tên mẫu; bấm "Áp dụng" để lưu.
- ✅ **Sẵn sàng nộp bài**: đọc sheet "Kiểm tra nộp bài" của lần chạy gần nhất, hiện Đạt/Thiếu/Cần xem bằng màu.
- 📐 **Mẫu tạp chí** (ACS, RSC, Elsevier, Wiley, Nature; cột đơn/đôi): đặt khổ hình, 600 dpi, PNG + PDF + TIFF. Kích thước thật của tạp chí lệch vài mm so với hai khổ của app, hãy đối chiếu hướng dẫn tác giả.
- 💾 / 📂 **Dự án**: lưu/mở toàn bộ cài đặt + danh sách mẫu + vai trò + điều kiện đo (file `.echem`).
- Trước khi chạy, app nhắc (không chặn): chưa bù iR, pH/Eref/diện tích còn mặc định, chưa nhập tải lượng, thiếu 10 mA/cm² trong mật độ dòng mục tiêu, nhiều file i-t chưa tick nối tiếp, chưa khai báo điện ly/điện cực.
Tab **Phổ**: các công cụ gọn thành nút 🔬 XPS · 📈 XRD · 🔭 HR-TEM · 🔗 Đối chiếu. Nút 🔗 có "⟳ Lấy từ công cụ đang mở": lấy đỉnh XRD của mẫu đầu, d các phép đo HR-TEM đã thêm, các thành phần XPS đã fit.
Công cụ XPS, menu ◧ Casa ▾: **Nhận kết quả + bảng số Casa (.txt)...** chọn file .vms rồi file bảng số TAB ASCII Casa xuất để dùng đúng nền/đường bao/phần dư của Casa.
i-t: báo cáo thêm "Suy giảm (%/h)" (độ dốc hồi quy của |I| theo giờ so với dòng đầu) và "Nhiễu đã loại (h)".


## v83 - Gỡ phần dư thừa
- Đã gỡ khung **Hình ghép chuẩn bài báo** (xuất hình nhiều ô A/B/C) và khung **Hoạt độ khối & TOF** (tâm hoạt động, M, n e⁻, quá thế khảo sát) khỏi giao diện, cùng nút 📐 mẫu tạp chí. Công cụ **Qs-LSV & TOF** riêng vẫn còn.
- **Tải lượng xúc tác** nay nhập trong hộp 🧪 Điều kiện đo (tab Xuất).
- Hình nhiều ô luôn tắt, kể cả khi cài đặt cũ đang bật.


## v84 - Hình ghép theo quy cách tạp chí (làm lại)
Tab **Hình**, nhóm "Hình ghép theo tạp chí": tick **Xuất hình nhiều ô**, chọn **tạp chí** (ACS / RSC / Elsevier / Nature / Tùy chỉnh) và **cột** (đơn / 1.5 / đôi). Dòng dưới tóm tắt quy cách đang áp. Nút: **ℹ** xem số đo chi tiết và nguồn; **⚙** PNG/PDF/TIFF, dpi, chữ ô; **🧩** soạn ô của từng hình.
| Tạp chí | Cột đơn | 1.5 cột | Cột đôi | Cao tối đa | Chữ | Nét | dpi |
|---|---|---|---|---|---|---|---|
| ACS | 8.25 cm | — | 17.78 cm | 24.13 cm | ≥ 5 pt | ≥ 1 pt | ≥ 600 |
| RSC | 8.3 cm | — | 17.1 cm | 23.3 cm | ≥ 7 pt (app chọn) | — | ≥ 600 |
| Elsevier | 9.0 cm | 14.0 cm | 19.0 cm | (không nêu; app 24 cm) | ≥ 7 pt, chỉ số ≥ 6 pt | — | 1000 (nét) |
| Nature | 8.9 cm | 12.0 cm | 18.3 cm | 24.7 cm | 5–7 pt, nhãn ô 8 pt đậm | 0.25–1 pt | 300–600, nên PDF vector |
- Nature dùng nhãn ô **chữ thường** (a, b, c) bất kể tùy chọn.
- Hình tự thu thấp nếu vượt chiều cao tối đa. Ô dpi để trống = theo tạp chí.
- Mỗi lần xuất có file `Hinh_bai_bao_kiem_tra_tap_chi.txt` ghi Đạt/Lưu ý cho từng số đo (bề rộng, chiều cao, chữ, chỉ số trên/dưới, nét, dpi) và đường dẫn nguồn.
- Wiley, Springer và nhiều tạp chí khác có quy cách riêng cho từng tạp chí: dùng "Tùy chỉnh" rồi đối chiếu hướng dẫn tác giả. Quy cách tra cứu 11/2026, có thể đổi: luôn kiểm tra lại trước khi nộp.


## v85 - Siêu tụ lai / Pin (tab Phân tích → nhóm "Siêu tụ lai & Pin" → ⚡ Mở công cụ...)
Thay cho khung "Hoạt độ khối & TOF" cũ (đã gỡ ở v83). Dùng **data GCD thô**: nạp file, nhập khối lượng, bấm Phân tích, xem 5 đồ thị, xuất Excel/hình hoặc vẽ thẳng ra Origin.
1. **Nạp file**: *Thêm file...* hoặc *Lấy từ danh sách file của app*. Đọc BioLogic `.mpt` (dấu phẩy thập phân), CSV/TXT, file CS Studio (E, i, T), Excel (Neware...). Mỗi file = một mẫu; nhiều mức dòng và nhiều chu kỳ trong cùng file đều được. Cột thời gian/điện thế/dòng và đơn vị (s/min/h, V/mV, A/mA/µA) lấy theo tên cột; sai thì bấm ⚙ để chọn lại. File không có cột dòng: nhập dòng không đổi (mA).
2. **Nhập khối lượng hoạt tính (mg)** cho từng mẫu (hoặc diện tích cm² nếu chọn chuẩn hóa theo diện tích).
3. **Thiết lập**: loại tế bào (2 điện cực: Csp = 4C/m với m là tổng khối lượng; 2 điện cực theo cell: C/m; ba điện cực: C/m), đại lượng chính (tự động / F/g / mAh/g), cách tính C (tích phân điện tích hoặc độ dốc), cách tính năng lượng, chiều nạp (điện thế tăng hay giảm), chu kỳ gốc cho retention, chu kỳ vẽ GCD, trục x của GCD (thời gian hoặc dung lượng riêng), hình theo mẫu tạp chí (ACS/RSC/Elsevier/Nature, cột đơn/1.5/đôi).
4. **Năm đồ thị**: Đường GCD · Csp (hoặc Q) theo mật độ dòng · Ragone (E–P, log–log) · Retention + hiệu suất Coulomb theo chu kỳ (hai trục Y) · Csp (hoặc Q) + CE theo chu kỳ. Retention cần một mức dòng có ≥ 3 chu kỳ.
5. **Công thức** (sheet "Công thức" trong Excel ghi đầy đủ): Q = ∫|I|dt; C = Q/ΔV (hoặc I/|dV/dt|); IR drop và ESR = ΔV_IR/(2I); Csp = 4C/m; Qsp = Q/(3.6m); CE = Q_xả/Q_nạp·100; E = ∫V·I dt (hoặc ½CV²), P = E/Δt; retention = giá trị_k/giá trị gốc·100.
6. **Tụ hay pin?** App đo độ tuyến tính của đường xả (R²): ≥ 0.985 coi là tụ (F/g), 0.93–0.985 lai, < 0.93 dạng pin (plateau) và tự chuyển sang dung lượng mAh/g. Ngưỡng này là quy ước của app, không phải của một bài báo; bạn có thể ép chọn F/g hoặc mAh/g.
7. **Xuất**: *Xuất Excel + CSV + hình...* (xlsx 6 sheet: tổng hợp theo dòng, từng chu kỳ, Ragone, retention, công thức, cảnh báo; CSV từng đồ thị; PNG). *Vẽ ra Origin...* ghi các file trên rồi vẽ 5 đồ thị trong Origin (cần Origin đã cài; retention dùng mẫu hai trục Y của Origin, nếu Origin không tạo được thì bỏ CE khỏi hình, dữ liệu vẫn có trong CSV).
**Lưu ý khi báo cáo** (theo Stoller & Ruoff 2010, BioLogic AN51, Gamry): ghi rõ tế bào 2 hay 3 điện cực, khối lượng chuẩn hóa, mật độ dòng (A/g), cửa sổ điện thế và cách tính C; khối lượng rất nhỏ (< 1 mg app cảnh báo) và quá điện thế làm sai số lớn; CE > 100% là dấu hiệu sai. Trị số E, P ở đây là của vật liệu/điện cực theo chuẩn hóa đã chọn, không phải của cell đóng gói.


## v86 - Siêu tụ lai / Pin: mỗi đồ thị một tab, thiết lập riêng
Cửa sổ ⚡ chia thành 6 tab:
- **① Dữ liệu & thiết lập chung**: danh sách mẫu (tên, khối lượng/diện tích, chọn cột), loại tế bào, chuẩn hóa, chiều nạp, đại lượng chính, cách tính C, cửa sổ độ dốc, dòng không đổi, ngưỡng tụ/pin; nút Phân tích, Xuất Excel + CSV + hình (cả 5), Vẽ cả 5 ra Origin, 💾 Lưu / 📂 Mở thiết lập. Các thiết lập này ảnh hưởng đến phép tính nên cần bấm Phân tích lại khi đổi.
- **②–⑥ Đường GCD · Csp/Q theo mật độ dòng · Ragone · Retention + CE · Csp/Q + CE theo chu kỳ**: mỗi tab có đồ thị xem trước và ba nhóm thiết lập riêng, đổi là vẽ lại ngay (Enter hoặc chọn xong):
  - *Dữ liệu của đồ thị*: GCD (trục x thời gian/dung lượng, chu kỳ vẽ); Csp/Q theo dòng (F/g hay mAh/g); Ragone (E = ∫V·I dt hay ½CV²); Retention và Csp/Q theo chu kỳ (đại lượng, mức dòng j, chu kỳ gốc, bật/tắt CE).
  - *Trục & khoảng*: tiêu đề trục x/y/y phải, giới hạn x/y/y phải, trục log.
  - *Kiểu hiển thị*: cỡ chữ nhãn, cỡ số trên trục, cỡ chú thích, độ dày nét, cỡ điểm, chú thích (hiện/ẩn, vị trí), lưới.
  - *Xuất hình*: mẫu tạp chí (ACS/RSC/Elsevier/Nature), cột, dpi, riêng cho từng đồ thị.
  Nút trên mỗi tab: ⟳ Vẽ lại · ↺ Mặc định · 💾 Xuất hình (PNG/PDF/TIFF/SVG) · Vẽ ra Origin (chỉ đồ thị này). Ô trống = tự động. Cỡ chữ, nét, điểm, khoảng trục, tiêu đề, chú thích, lưới và trục log cũng được áp dụng khi vẽ Origin.
- **Lưu/mở thiết lập**: file `.json` gồm danh sách mẫu, khối lượng, cột và thiết lập của cả 5 đồ thị, để lần sau chỉnh tiếp. App cũng tự nhớ thiết lập lần đóng cửa sổ gần nhất (không nạp lại mẫu).
- Sheet Ragone trong Excel có cả hai cách tính năng lượng (tích phân và ½CV²).


## v87 - Hướng dẫn theo phép đo (tab Trợ giúp → "Hướng dẫn theo phép đo")
Gõ tên phép đo rồi bấm **Tra cứu** (hoặc Enter), ví dụ `LSV`, `CV`, `i-t`, `EIS`, `Tafel`, `ECSA`, `bù iR`, `so sánh`, `FE`, `TOF`, `GCD`, `Csp`, `Ragone`, `retention`, `CE`, `XPS`, `XRD`, `HR-TEM`, `nộp bài`, `hình tạp chí`, `quy đổi`. Gõ có dấu hay không dấu đều được; gõ sai nhẹ (`ragon`) vẫn tìm ra. Trong cửa sổ, danh sách bên trái lọc theo chữ đang gõ.
Mỗi mục có: **Dữ liệu cần có** · **Các bước trong app** (bấm vào `[ ]` để tick bước đã làm, giữ trong phiên làm việc) · **Phép tính** (công thức và giải thích) · **Với thiết lập hiện tại của bạn** (pH, Eref, hệ số nhân/chia, I mục tiêu, vùng Tafel, Cs, số file LSV/CV/IT/EIS đang nạp...) · **Tiêu chí & cảnh báo** (đúng ngưỡng app dùng, ví dụ Tafel: < 5 điểm, R² < 0.98, |b| > 500 hoặc < 20 mV/dec) · **Lỗi thường gặp** · **App xuất ra** · **Xem thêm**.
- Nút *Đặt Loại phép đo = ...* chọn sẵn loại ở tab Dữ liệu; *Mở công cụ ...* mở thẳng Qs-LSV & TOF, Siêu tụ lai & Pin, XPS, XRD hoặc HR-TEM; *Sao chép* và *Lưu .txt...* để dán vào sổ thí nghiệm.
- Tab **Hỏi đáp** cũng hiểu "hướng dẫn tafel", "cách đo LSV", "các bước ecsa" và trả lời ngay cả khi chưa nạp file.
- Giá trị tham khảo chung trong điện hóa (ví dụ ΔEp ≈ 59 mV cho cặp thuận nghịch 1 electron, Cs ≈ 0.040 mF/cm²) được ghi rõ là kiến thức chung, không phải ngưỡng do app áp đặt; hãy đối chiếu hướng dẫn của tạp chí/nhóm nghiên cứu của bạn.


## v88 - Siêu tụ lai / Pin theo công thức file Excel, GCD nhiều chu kỳ, điện cực so sánh
**1. Bộ công thức** (tab ① ▸ "Bộ công thức"): mặc định *Kiểu file Excel của bạn*: Csp = I·Δt/(m·ΔV), Δt = thời gian xả tính từ lúc đảo dòng, ΔV = V đỉnh nạp − V cuối xả (**gồm IR drop**), E = ½·Csp·ΔV²·1000/3600 (Wh/kg), P = E·3600/Δt, CE = t_xả/t_nạp·100, retention = t_xả(n)/t_xả(gốc)·100. Chọn *Chuẩn* để bỏ IR drop (ngoại suy về lúc đảo dòng) và tính E bằng tích phân; các ô ΔV / cách tính C / cách tính E vẫn chỉnh riêng được. Ví dụ NiCr2O4 10 A/g, chu kỳ 3: bản cũ 199.4 F/g → bản mới 155.0 F/g (Excel của bạn 153.57; lệch nhỏ do làm tròn theo bước lấy mẫu 0.1 s).
**2. Loại tế bào** mặc định đổi thành *3 điện cực / 1 điện cực (C/m)* như Excel; 2 điện cực đối xứng (4C/m) và cell 2 điện cực theo tổng khối lượng vẫn chọn được.
**3. GCD nhiều chu kỳ** (tab ③): đường V–t của cả nghìn chu kỳ kèm hai ô phóng đại *Initial cycles* / *Final cycles*, chữ góc (vd `NiCr2O4 // AC`) và chú thích (vd `5 A g⁻¹ 4500 Cycles`), giống hình bạn gửi. File lớn được giảm điểm giữ đỉnh/đáy. Ở Origin, hai ô phóng đại được vẽ thành hai đồ thị riêng cạnh đồ thị chính (chưa kiểm thử trên Origin thật).
**4. Thời gian nạp / xả / chu kỳ**: sheet Excel mới "Thời gian chu kỳ" và cột "Chu kỳ nạp–xả (s)" ở sheet "Từng chu kỳ"; Retention có thêm đại lượng *Thời gian xả (s)* (cột CR% của Excel).
**5. Khối lượng, dòng, cửa sổ điện thế** tự đọc từ dòng đầu file CS Studio (ví dụ 23.2 mA, 0–0.55 V, 2.32 mg → 10 A/g).
**6. Điện cực so sánh**: hộp chọn Hg/HgO (1 M KOH 0.098 V; 1 M NaOH 0.140 V), Ag/AgCl (0.197 / 0.210 V), SCE 0.241 V, Hg/Hg₂SO₄ 0.640 V, SHE, hoặc tự nhập Eref; công thức RHE = E + k·pH + Eref với k mặc định **0.059** (khớp Excel; 0.0592 chọn được, chênh ≈ 2.8 mV ở pH 13.8). Có ở app chính (tab Dữ liệu, mọi phép đo quy đổi) và trong công cụ GCD (chỉ đổi trục điện thế, không đổi giá trị C, E). Các giá trị Eref là số tham khảo, hãy đối chiếu datasheet điện cực của bạn.
**7. EIS**: giữ quy ước −Z″ như Excel; định dạng bảng EIS không đổi.
**8. Hướng dẫn theo phép đo** có thêm mục "GCD nhiều chu kỳ" và "Điện cực so sánh", các mục GCD/Csp/Ragone/Retention/CE được viết lại theo công cụ mới.


## v89 - Tự điền khối lượng từ tên file
Nếu file không có header CS Studio (hoặc header không ghi khối lượng), công cụ ⚡ đọc số đứng trước "mg" trong tên file/mẫu (vd `NiCr2O4_GCD_23.2mA_0-0.55V_2.32mg.txt` → 2.32 mg) và ghi chú "lấy từ tên file (hãy kiểm tra)". Không thấy thì ô để trống và app vẫn hỏi như cũ.


## v90 - Ô khối lượng chung và tab ký hiệu
- Tab ① có ô **Khối lượng (mg)** cạnh nút *Thêm file...*: gõ số rồi bấm *Áp cho mọi mẫu* (hoặc Enter) để đặt cho tất cả mẫu đang có; file thêm sau lấy số này nếu header CS Studio và tên file không ghi khối lượng. Từng mẫu vẫn sửa riêng ở ô trong danh sách.
- Tab đã rút gọn: ① ⚙ (dữ liệu & thiết lập chung) · ② V–t (GCD) · ③ V–t ×n (nhiều chu kỳ) · ④ C–j (Csp/Q theo mật độ dòng) · ⑤ E–P (Ragone) · ⑥ % CE (Retention + CE) · ⑦ C–n (Csp/Q + CE theo chu kỳ). Đưa chuột vào tab để hiện tên đầy đủ.


## v91 - Csp theo mật độ dòng dạng cột
- **Công thức**: Csp = I × Δt / (m × ΔV), tính cho từng chu kỳ xả từ đường GCD: Δt = thời gian xả của chu kỳ đó (s), ΔV = chênh điện thế của chu kỳ (với bộ công thức "Kiểu file Excel": V đỉnh nạp − V cuối xả), I và m là số bạn nhập. Mỗi mức dòng lấy trung vị các chu kỳ (có thể bỏ chu kỳ đầu).
- **Nhập I và m**: ở danh sách mẫu tab ① có hai ô: khối lượng (mg) và **I (mA)**. Ô I để trống thì app đọc dòng từ file; có số thì app dùng đúng số đó (và không đọc cột dòng). Mật độ dòng j = I/m (A/g) là vị trí cột trên trục x. Chọn nhiều file cùng một vật liệu (mỗi file một dòng) hoặc một file có nhiều mức dòng đều được.
- **Đồ thị ② C–j (tab ④)**: mặc định là **đồ thị cột** như hình mẫu: cột đen, khung dày, chữ đậm, vạch chia ra ngoài, trục y từ 0, tên mẫu ở góc trên phải (NiCr2O4 tự thành NiCr₂O₄). Nhiều mẫu: các cột đặt cạnh nhau theo màu từng mẫu. Đổi sang "Đường + điểm" ở ô *Kiểu đồ thị*; đại lượng mặc định là Csp (F/g). Ở Origin đồ thị được vẽ bằng kiểu cột (chưa kiểm thử trên Origin thật).
