# Bộ chọn khoảng thời gian — Screen_Performance

Sau khi deploy backend mới, chạy Sync ngay một lần. Backend tự chèn đúng một dòng điều khiển trên đầu tab Screen_Performance. Không thêm cột thời gian.

- B1: Từ ngày, D1: Đến ngày; nhập YYYY-MM-DD. Bao gồm cả ngày đầu và ngày cuối theo TZ của backend (mặc định Asia/Bangkok).
- E1/F1: Xem ▶ và checkbox action. Bấm checkbox F1 để gửi yêu cầu. Backend kiểm tra mỗi 15 giây; nếu một lần sync đang chạy thì đợi lần đó hoàn tất.
- G1: trạng thái và khoảng đã áp dụng. Chỉ sửa ngày chưa làm thay đổi kết quả; cần bấm Xem.
- I1: chọn Ngày giao dịch (mặc định) hoặc Ngày mua/trial đầu chuỗi.
- Để trống hai ngày rồi bấm Xem để xem toàn bộ lịch sử.

Ngày giao dịch: tính lại từ các đơn có ngày giao dịch trong khoảng, vẫn đọc đầy đủ lịch sử để xác định nguồn mua ban đầu. Renew từ chuỗi cũ vẫn có thể UNKNOWN.
Ngày mua/trial đầu chuỗi: chỉ giữ chuỗi có ngày acquisition đã xác minh trong khoảng, sau đó tính các đơn quan sát được của các chuỗi đó. Không giới hạn ngày renew; chuỗi thiếu acquisition bị loại khi có giới hạn ngày.

Số user trả phí/dùng thử/renew được đếm distinct lại từ dữ liệu gốc. Tiền vẫn tách theo currency. Với Ngày giao dịch, số hủy chỉ gồm sự kiện hủy trong khoảng của các chuỗi có đơn được chọn. Các tab khác giữ toàn bộ lịch sử.

Bộ lọc đã áp dụng được lưu trong SQLite report_queries và giữ qua sync/restart với cùng volume database. Orders/events không bị sửa. Chỉ query từ dữ liệu backend đã có, không fetch lại Google Play khi bấm Xem.

Triển khai: cập nhật image/code trên deployment hiện tại, giữ nguyên volume database và cấu hình SHEET_ID, sau đó Sync ngay. Không tạo dòng điều khiển thủ công trước khi cập nhật backend vì bản cũ sẽ ghi đè dòng đó.

Kiểm tra thực tế sau deploy: chọn ngày bằng nhau; khoảng rỗng; ngày sai; chế độ acquisition; bấm Xem rồi sync lại; xác nhận G1, header ở hàng 2 và các bộ lọc bảng vẫn hoạt động. Local unit tests không chứng minh kết nối Sheet production.
