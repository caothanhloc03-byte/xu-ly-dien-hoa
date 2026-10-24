# Hướng dẫn nhanh Echem Studio

## Bắt đầu trong 3 bước
- Bấm **Dữ liệu mẫu** để nạp thử số liệu giả lập, hoặc **Thêm file...** / **Thêm thư mục...** (kéo-thả nếu máy có tkinterdnd2).
- Chọn **Loại phép đo** (hoặc để "Tự nhận dạng"), kiểm tra pH, Eref và hệ số quy đổi dòng.
- Bấm **Xem trước hình** để xem nhanh, rồi **CHẠY XỬ LÝ & VẼ** để vẽ bằng Origin và xuất báo cáo.

## Các loại phép đo
- **LSV / CV**: vẽ đường E (V vs RHE) – I (mA/cm²). CV mặc định dùng chu kỳ cuối, có thể đổi ở ô "Chu kỳ CV dùng".
- **IT**: dòng theo thời gian (giờ).
- **EIS**: đồ thị Nyquist Z' – (−Z'').
- **ECSA**: cần ít nhất 2 file CV ở các tốc độ quét khác nhau (khuyến nghị 5 trở lên). App lấy (Ja−Jc)/2 tại một điện thế, fit theo tốc độ quét (V/s) để ra Cdl, rồi ECSA = Cdl / Cs.
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

## Hỏi đáp dữ liệu
Gõ câu hỏi tiếng Việt, ví dụ: "điện thế tại 10 mA của các mẫu", "quá thế tại 10 mA", "dòng tại 1.6 V", "tafel", "ecsa", "liệt kê các file". Không cần Internet hay AI.

## Khi gặp lỗi
- Đọc phần "GỢI Ý XỬ LÝ" in ngay dưới dòng lỗi.
- Bấm **Mở nhật ký** để lấy chi tiết kỹ thuật gửi cho người hỗ trợ.
- Origin: mở Origin 2024 một lần cho đến khi thấy giao diện chính, đóng các hộp thoại, rồi chạy lại.
- Đóng file Excel/ảnh đang mở trong thư mục kết quả trước khi chạy lại.

## Phím tắt
- Ctrl + lăn chuột, Ctrl + / Ctrl − : thu phóng giao diện; Ctrl 0: về 100%.

## Cập nhật
App tự kiểm tra bản mới khi mở. Có thể chọn "Cập nhật ngay", "Để sau" hoặc "Bỏ qua phiên bản này". Cập nhật chỉ thay mã nguồn, không đụng tới dữ liệu và cài đặt của bạn; nếu lỗi, app tự khôi phục bản cũ.
