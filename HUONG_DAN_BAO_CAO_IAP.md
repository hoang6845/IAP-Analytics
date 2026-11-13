# Báo cáo IAP cho marketing / product

Code tạo các tab dưới đây ở lần **Sync** kế tiếp sau deploy. Chưa chạy Sync online trong lần sửa này.
Các tab kỹ thuật cũ vẫn được cập nhật nhưng ẩn để giảm rối; dùng Sheets → View → Hidden sheets để mở lại. Dashboard hiện hiển thị quốc gia thay cho tiền tệ.

## Lọc “Tất cả” trong Sheets

- Các cột phân nhóm của báo cáo tổng hợp có giá trị **Tất cả**: quốc gia, gói/offer, nguồn paywall, loại/ID/tên nội dung, cohort/user/chuỗi/lần renew. Đây là nhóm số liệu tính lại từ dữ liệu gốc, không phải dòng cộng cuối bảng.
- Mở bộ lọc ở tiêu đề cột, bỏ chọn các giá trị khác rồi chọn riêng **Tất cả** để xem số liệu gộp. Hoặc bỏ Tất cả và chọn quốc gia/gói/nguồn cụ thể. Các chiều lọc khác vẫn áp dụng; ví dụ quốc gia=Tất cả, gói=weekly là tổng mọi quốc gia của gói weekly.
- Mỗi lần Sync, bộ lọc mặc định chọn phạm vi Tất cả ở các chiều hỗ trợ, tránh hiển thị chồng chi tiết và tổng hợp. Bộ lọc do người dùng chỉnh sẽ được đặt lại ở lần Sync sau.
- Không chọn đồng thời Tất cả và từng quốc gia/gói rồi SUM các dòng, vì các phạm vi chồng nhau. User được đếm distinct trong từng phạm vi; tỷ lệ tính lại từ tử số/mẫu số, không lấy tổng/trung bình các tỷ lệ.
- **Không còn cột tiền tệ riêng** trên các tab xuất. Số tiền ghi kèm mã, ví dụ `20 USD; 100000 VND`. Báo cáo tổng hợp gộp mọi tiền tệ theo quốc gia; chọn quốc gia **Tất cả** để xem mọi quốc gia. User được đếm distinct từ dữ liệu gốc, không cộng các dòng tiền tệ. Không có nguồn tỷ giá nên chưa quy đổi sang USD.
- Overview có cột quốc gia và bộ lọc Tất cả cho ngày/quốc gia. Country_Performance không chia thành nhiều dòng theo tiền tệ. ARPPU vẫn tính riêng mẫu số payer trong từng tiền tệ rồi ghi mã bên cạnh kết quả. Tab bản ghi như RAW_Data/Transactions/User_Timeline giữ từng bản ghi; dùng Chọn tất cả của bộ lọc để xem toàn bộ.
- RAW_Data, Transactions, Users, User_Timeline, log và Description giữ bản ghi gốc; dùng **Chọn tất cả** có sẵn trong bộ lọc Sheets để hiện mọi bản ghi. Không tạo bản ghi giao dịch/user giả mang ID Tất cả.
- Firebase_Events lấy nhóm Tất cả trực tiếp từ GA4 cho từng tổ hợp chiều (tối đa 64 truy vấn/phân trang cho mỗi app/cửa sổ), để số distinct user không bị cộng trùng từ các nhóm chi tiết.

| Tab | Dùng để trả lời |
| --- | --- |
| Dashboard | So sánh quốc gia hoặc chọn Tất cả quốc gia; user trả phí, lượt trả tiền/renew/refund và tiền thu có mã tiền tệ. |
| Overview | Tổng chuỗi thuê bao đã quan sát; thuê bao mới, hủy theo ngày; trial, payer và tiền thu. Lọc ALL hoặc ngày, không cộng cả hai. |
| RAW_Data | Ngày giờ, user ID, order ID, ID chuỗi, country, gói, offer, tiền/currency, trạng thái, event, nội dung và nguồn paywall. ORDER có tiền; EVENT không có tiền để tránh cộng trùng. |
| Country_Performance | User trial, user trả phí, ARPPU, trial conversion 7 ngày, user từng Billing Retry và tỷ lệ. |
| Cohort_Retention | Lọc country/user ID/ID chuỗi/gói. Step 0 là mua đầu/convert/khác; step 1,2,3… là renew. Có số người, số đơn và tiền từng bước; tổng tiền renew/convert/khác. |
| Package_Performance | Sort lượt mua giảm dần để xem gói mua nhiều; so sánh tỷ lệ convert khi dữ liệu đủ điều kiện. |
| Plan_Upgrades | Gói cũ → gói mới, số user/lượt upgrade, tiền. Dùng webhook upgrade rõ ràng; lifetime dùng gói active mà app chụp trước mua. |
| Theme_Performance | Không chỉ theme: cả font/effect/background/keycap/sound/DIY/text-art/sticker/kaomoji. Số user trial/convert/renew/cancel và tiền theo nội dung. |
| Screen_Performance | So sánh nguồn onboarding, icon Premium Home/Settings, banner Home, feature khóa và limited offer. |
| Firebase_Events | Tự động lấy event count và distinct user từ GA4 Data API theo country/nội dung/nguồn. Tách khỏi số đơn/tiền để không cộng trùng. |
| Data_Quality / Description | Dữ liệu thiếu và công thức từng cột. |

## Cách đọc đúng

- Mọi số tiền tách theo **currency**; không cộng VND với USD. Không có tỷ giá quy đổi tự động.
- **Tổng tiền thu** dùng charged của đơn Google PROCESSED; không phải lợi nhuận hay tiền developer sau phí/thuế. RAW giữ cả Developer Revenue nếu Google có. Đơn hoàn toàn bộ bị loại khỏi tổng tiền thu; đơn hoàn một phần không được đoán số tiền còn giữ.
- `Total Revenue = Renewal Revenue + Conversion Revenue + Other Revenue`. Other gồm mua trực tiếp và giao dịch chưa đủ dữ liệu phân loại. Webhook không tự tạo thêm tiền.
- **ARPPU** = tiền thu PROCESSED của đơn gắn rõ user / số user từng trả tiền quan sát. Số payer gồm lịch sử payer có đơn hoàn tiền; không phải số thuê bao active.
- **Conversion rate** dùng cohort trial đã qua 7 ngày sau ngày kết thúc, ghép đúng app/user/chuỗi/gói; không lấy tất cả payer chia tất cả trial. Chỉ mở tỷ lệ khi lịch sử đầy đủ đã được xác nhận; nếu thiếu, hiển thị N/A.
- **Retry rate** = user từng vào Billing Retry / user thuê bao đã quan sát trong nhóm, toàn lịch sử. Đây là tỷ lệ user gặp retry, không phải tỷ lệ lần thu tiền thất bại. Daily Overview để N/A cho chỉ số này.
- **Renewal Number** ưu tiên `subscription_renew_count` của Qonversion. Nếu thiếu thì chỉ đếm 1,2,3… khi có acquisition và coverage lịch sử đầy đủ; còn lại UNKNOWN. Không gọi renew đầu tiên nhận được là renew lần 1.
- Trong Cohort_Retention, tiền từng bước có thể cộng; các cột tổng chuỗi lặp trên từng bước, **không SUM các tổng đó qua các bước**. Số user là distinct từng dòng, không SUM qua nhiều chuỗi để ra unique user toàn app. Đây là retention theo lần renew đã quan sát, chưa phải xác suất renew của toàn population đủ điều kiện.
- Tổng subscription là số chuỗi subscription đã xác minh trong lịch sử. **Active subscriptions để N/A** vì hiện không có snapshot quyền truy cập live. Cancel là hủy gia hạn, không đồng nghĩa mất Premium ngay.
- Cancel/retry thiếu đơn xác minh hoặc thiếu user/chuỗi không thể gán chắc chắn vào buyer country/gói; xem RAW và Data_Quality. IP country của webhook và country GA4 tách riêng với buyer country Google.

## Attribution: nội dung/màn nào đem lại doanh thu

Android gửi snapshot ngay **trước khi gọi billing**, bằng Qonversion custom user properties:

`iap_data_type`, `iap_data_id`, `iap_data_name`, `iap_entry_source`, `iap_visit_id`, `iap_selected_plan`, `iap_from_plan`.

Backend lấy snapshot ở event acquisition production (`trial_started`, `subscription_started`, `in_app_purchase`) của đúng chuỗi, rồi giữ nguyên cho convert/renew/cancel sau đó. Việc user mở theme khác sau khi mua không được chuyển doanh thu renew sang theme mới. Thiếu snapshot: UNKNOWN; không suy đoán lịch sử cũ.

Đây là attribution **paywall dẫn tới lần mua đầu chuỗi**, không phải last click marketing/campaign attribution. SDK gửi properties bất đồng bộ; cần kiểm tra payload thật để xác nhận snapshot đã tới Qonversion trước acquisition. Không trì hoãn hoặc chặn mua chỉ để chờ analytics.

Nguồn hiện có được đo gồm:

- `onboarding`: paywall sau onboarding.
- `home_btn_premium`: icon Premium Home.
- `home_banner`: banner IAP Home (override analytics riêng, giữ nguyên PAYWALL_SOURCE và event legacy).
- `setting_premium`, `setting_view_benefits`: các nút Premium Settings hiện có.
- `preview_theme_download`, `premium_day_night_theme`, `my_premium_day_night_theme`: theme cụ thể.
- `preview_font_art`, `preview_text_art`, `preview_kaomoji`, `preview_sticker`: preview nội dung cụ thể.
- `customize_theme_premium`: thành phần DIY cụ thể, có type và ID.
- `edit_theme_premium`: chặn lưu theme premium trong editor, nguồn/feature được ghi nhận; chưa có catalog ID khi chỉ chặn ở mức toàn bản thiết kế.
- `limited_offer_dialog`: luồng mua riêng của dialog, không đi qua PaywallActivity.

Chưa có điểm vào banner Settings riêng trong source hiện tại; không thêm UI/banner mới. Nguồn mới có thể truyền `IAP_ENTRY_SOURCE` để phân biệt mà không đổi điều hướng.

## Firebase: event chuẩn và ý nghĩa

| Event app phát | Khi phát |
| --- | --- |
| paywall_view | Mở paywall/limited offer, một lần cho phiên được lưu qua rotation. |
| paywall_dismiss | Đóng mà không mua/restore thành công; chờ callback nếu đang purchase. |
| paywall_purchase | Callback mua thành công; **không khẳng định trial hay conversion**. |
| premium_item_tap | Đi vào paywall từ nội dung premium có ID cụ thể. Không phải mọi lần chạm vào ảnh preview hoặc nút xem quảng cáo. |
| premium_item_dismiss | Phiên có nội dung cụ thể đóng không mua/restore. |
| premium_item_purchase | Callback mua thành công trong phiên có nội dung cụ thể. |

Params: `data_type`, `data_id`, `data_name`, `entry_source`, `visit_id`; thêm `plan` ở callback mua. Giữ event legacy `premium_data_iap_*` cho các điểm đã có ID, không xóa tracking cũ.

Ví dụ hello kitty: `premium_item_tap` + `data_name=Hello Kitty` + `data_id=<ID catalog>`; không tạo hàng nghìn tên event `premium_item_tap_<theme>`.

Trial/converted/renew/cancel/billing retry phải được xác nhận từ Qonversion/Google, vì xảy ra cả lúc app đóng. Qonversion → Firebase integration hiện đã có đường gửi App Instance ID trong app; **vẫn cần cấu hình console và xác minh delivery**. Có thể đặt tên lifecycle trong integration thành `premium_item_trial`, `premium_item_converted`, `premium_item_renew`, `premium_item_cancel` hoặc giữ `trial_started`, `trial_converted`, `subscription_renewed`... Backend đã đọc lifecycle trực tiếp từ webhook để làm các báo cáo nội dung/màn.

Không tự phát trial/conversion từ nút mua; không tự phát renew bằng bộ đếm local. Không dùng tên event động `premium_item_renew_1/2/...`: số lần renew lấy từ webhook counter trong retention. Firebase integration mặc định **không bảo đảm kèm params data_id/entry_source/renewal_number**; lifecycle Firebase có thể là `(not set)` cho các dimension này. Muốn drill-down event-level Firebase theo user/transaction, dùng BigQuery để join; không gán giả nội dung bằng tổng GA4.

## Bật GA4 Data API tự động

1. Enable **Google Analytics Data API** trong Google Cloud project của service account đang dùng.
2. Trong GA4 → Admin → Property access management: thêm email service account với quyền **Viewer**.
3. Trong GA4 → Admin → Custom definitions, tạo **event-scoped custom dimensions** cho `data_type`, `data_id`, `data_name`, `entry_source`. Không đăng ký `visit_id`/user ID làm custom dimension vì cardinality cao.
4. Thêm cấu hình dưới app tương ứng trong `config/apps.yaml` (không thay key/package/Qonversion app ID hiện có):

```yaml
    analytics_coverage_start_utc: '2026-11-13T00:00:00Z' # chỉ đặt khi đã xác nhận đủ lịch sử từ mốc này
    ga4:
      property_id: '123456789' # GA4 Property ID dạng số; không phải Firebase App ID hay Measurement ID
      start_date: '2026-11-13'
      end_date: yesterday
```

5. Deploy code và config, giữ nguyên volume database/service account/SHEET_ID; bấm Sync. Scheduler hiện có cũng lấy GA4 ở mỗi lần export. API đã có pagination, cảnh báo thresholding/sampling/(other), và không làm hỏng báo cáo đơn nếu GA4 lỗi.
6. Tab Firebase_Events có `DISABLED` nếu chưa cấu hình; `ERROR` nếu quyền/API/dimension/ngày chưa đúng; `OK` nếu truy vấn xong. ERROR không được biến thành số 0. API lấy lại toàn cửa sổ, không cộng chồng dữ liệu mỗi lần sync.

GA4 có thời gian xử lý; dimension mới không khôi phục params lịch sử. User count là distinct trong toàn cửa sổ **từng dòng**, không cộng qua event/nguồn/nội dung. Country dùng timezone/cách xác định của GA4, khác Google buyer country.

**GA4 Data API là báo cáo tổng hợp, không phải API tải RAW event/user ID.** RAW giao dịch trong báo cáo lấy SQLite/Qonversion/Google. Nếu cần RAW Firebase từng user/session/transaction và tự tính funnel/retention event-level, bật Firebase/GA4 BigQuery Export; cần thêm project/dataset và quyền BigQuery. Phần kết nối BigQuery chưa được cấu hình trong lần sửa này.

Tài liệu chính thức:

- https://developers.google.com/analytics/devguides/reporting/data/v1/basics
- https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema
- https://support.google.com/analytics/answer/7029846
- https://documentation.qonversion.io/docs/webhooks
- https://documentation.qonversion.io/docs/firebase

## Kiểm tra trước dùng số liệu production

Chạy `python -m unittest discover -s tests`. Kiểm tra thiết bị: mở onboarding/Home icon/banner/Settings/locked theme/font/effect/DIY; xác nhận event params trong DebugView, rotation không đếm lại view, đóng không mua có dismiss, restore không bị tính purchase. Mua sandbox để kiểm tra webhook acquisition có properties và liên kết đúng user/root; không đưa sandbox vào các chỉ số production. Kiểm tra renew/convert ở webhook khi app đóng. Compile/unit test không chứng minh Firebase/GA4/Google Sheets online đã nhận dữ liệu.

## Cột chưa có giá trị sử dụng

Mỗi lần xuất Sheet, cột chỉ có `N/A` trong toàn bộ dữ liệu sẽ được bỏ khỏi bố cục và tab Description. Cột tự xuất hiện lại khi có ít nhất một giá trị hợp lệ, kể cả số 0. Cột có dữ liệu một phần vẫn được giữ.

Tab chưa có bản ghi và cột đang chờ dữ liệu nguồn (rỗng, `UNKNOWN`, GA4 chưa cấu hình) vẫn được giữ. Quy tắc này chỉ thay đổi phần hiển thị, không thay đổi dữ liệu gốc hay phép tính báo cáo. `N/A` không tự chứng minh lỗi tính toán: tỷ lệ trial có thể chưa xác nhận được do thiếu lịch sử/coverage.
