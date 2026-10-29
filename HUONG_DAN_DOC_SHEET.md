# Đọc Sheet để đánh giá gói

Chỉ cần đọc 3 tab đầu. Các tab còn lại dùng để tra cứu khi cần.

## 1. Dashboard — Tổng quan (7 cột)

Chọn **Ứng dụng** và **Tiền tệ**, rồi đọc 5 số:

| Cột | Giúp biết điều gì? |
|---|---|
| Người đã trả tiền | Có bao nhiêu người mua xác định được từ dữ liệu đã nhận? |
| Lượt thanh toán | Có bao nhiêu đơn có trả tiền, kể cả đơn sau đó đã hoàn? |
| Lượt gia hạn | Có bao nhiêu lần trả tiền gia hạn đã xác minh? |
| Lượt hoàn tiền toàn bộ | Có bao nhiêu đơn có trả tiền đã hoàn toàn bộ? |
| Tiền thu từ đơn thành công | Tổng tiền trên các đơn thành công, gồm thuế; loại đơn đã hoàn hoặc chờ hoàn. |

## 2. Plan_Comparison — So sánh gói (11 cột)

Cũng dùng 5 số trên, kèm **Ứng dụng · Loại gói · Mã gói · Mã ưu đãi · Quốc gia người mua · Tiền tệ**.

Lọc cùng ứng dụng, quốc gia và tiền tệ trước khi so sánh. Mã gói và mã ưu đãi phân biệt các lựa chọn bán khác nhau; không phải cột kỹ thuật có thể bỏ tùy ý.

- **Có người mua:** xem Người đã trả tiền và Lượt thanh toán.
- **Có mua tiếp:** xem Lượt gia hạn. Đây là số lượt, không phải tỷ lệ giữ chân; gói cũ và gói tuần có nhiều cơ hội gia hạn hơn gói mới hoặc gói năm.
- **Ít hoàn tiền:** đọc Lượt hoàn tiền toàn bộ cùng Lượt thanh toán. Ví dụ 5 lượt hoàn trên 100 lượt thanh toán khác với 5 trên 10. Chỉ phản ánh hoàn toàn bộ, không bao gồm hoàn một phần/chờ hoàn.
- **Tạo tiền thu:** xem Tiền thu từ đơn thành công. Đây không phải lợi nhuận hay doanh thu ròng.

Nhiều tiền hơn chưa đủ kết luận gói tốt hơn: có thể do lượng người tiếp cận lớn hơn hoặc thời gian bán lâu hơn. Sheet chưa có chi phí quảng cáo/lượt xem gói nên chưa đánh giá được ROAS hay tỷ lệ mua trên lượt xem.

## 3. Trial_Cohorts — Dùng thử có chuyển sang mua? (11 cột)

Lọc cùng gói, ưu đãi, quốc gia, tiền tệ và tuần bắt đầu dùng thử. Đọc:

| Cột | Cách hiểu |
|---|---|
| Kỳ đã đủ thời gian theo dõi | Số kỳ dùng thử đã kết thúc ít nhất 7 ngày; là cỡ mẫu để đọc tỷ lệ. |
| Kỳ chuyển sang trả tiền | Trong nhóm đủ thời gian, số kỳ có thanh toán khớp chuỗi giao dịch từ lúc bắt đầu đến 7 ngày sau khi kết thúc. |
| Tỷ lệ dùng thử sang trả tiền | Tỷ lệ chuyển đổi của nhóm đủ thời gian; không lấy người mua chia người dùng thử trên Dashboard. |
| Độ đầy đủ dữ liệu chuyển đổi | AVAILABLE: có thể đọc tỷ lệ. N/A hoặc trạng thái khác: chưa đủ dữ liệu/thời gian, không coi là 0%. |

Ưu tiên so sánh tỷ lệ khi cỡ mẫu đủ lớn và các nhóm có điều kiện tương đương.

## Các tab còn lại

| Tab | Khi nào cần mở? |
|---|---|
| Country_Analysis / Product_Analysis | Xem tiền thu, đơn thành công có thu tiền và đơn hoàn toàn bộ theo quốc gia/sản phẩm. |
| Users / Transactions | Tra người dùng hoặc đơn cụ thể. Trạng thái đơn vẫn cho biết hoàn một phần/chờ hoàn. |
| Data_Quality | Kiểm tra dữ liệu thiếu trước khi quyết định. |
| User_Timeline / Qonversion_Events | Đối chiếu lịch sử sự kiện. |
| Diagnostics / Sync_Log | Kiểm tra kỹ thuật và lần đồng bộ. |
| Description | Tra ý nghĩa từng cột ngay trong Sheet. |

Không cộng khác tiền tệ. Một người có thể mua nhiều gói nên không cộng số người giữa các gói. Người đã trả tiền không đồng nghĩa thuê bao đang hoạt động. Tổng tiền chỉ cộng giá trị đã biết; dữ liệu thiếu có thể khiến tổng thấp hơn thực tế. Báo cáo chỉ phản ánh lịch sử hệ thống đã nhận.

## Cập nhật Railway

Deploy code mới vào service hiện tại, giữ nguyên volume SQLite, DB_PATH và SHEET_ID. Mở trang chủ `/`, nhập WEBHOOK_TOKEN và bấm **Sync ngay**.

Sync tự thay bộ cột trên Sheet hiện có. Dữ liệu gốc và cách tính giữ nguyên; các trường bỏ khỏi giao diện không bị xóa khỏi dữ liệu nguồn. Không cần tạo Sheet mới. Ghi chú tự nhập nên để ở tab riêng vì vùng báo cáo được ghi lại khi sync.
