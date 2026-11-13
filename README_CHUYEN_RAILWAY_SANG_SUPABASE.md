# Hướng dẫn giữ dữ liệu Railway và chuyển sang Supabase

Tài liệu dành cho project IAP Analytics hiện tại. Kiểm tra source và tài liệu nhà cung cấp ngày 13/11/2026; giao diện và chính sách dịch vụ có thể thay đổi.

**Không bấm Wipe Volume trước khi tải và kiểm tra bản sao dữ liệu. Wipe xóa dữ liệu volume và các backup của volume trong environment hiện tại.**

## 1. Hiểu phạm vi chuyển đổi

Project hiện chạy Python/FastAPI trong Docker, dùng SQLite, nhận webhook Qonversion, gọi Google Play Orders API và xuất Google Sheets. Scheduler chạy mỗi giờ vào phút `SYNC_MINUTE` theo `TZ`.

Database mặc định là `/data/iap.sqlite3`, gồm `events`, `orders`, `sync_log`. Phải kiểm tra `DB_PATH` trên Railway vì cấu hình thực tế có thể khác.

Supabase PostgreSQL thay được database. Supabase Edge Functions chạy TypeScript/Deno, không chạy nguyên Docker/FastAPI hiện tại. Chuyển toàn bộ cần triển khai lại backend và giao diện quản trị tương ứng.

**Trạng thái repo: hiện chưa có backend Supabase, script import hoặc Edge Functions thay thế.** Phần sao lưu dưới đây có thể thực hiện ngay; phần chuyển backend là trình tự triển khai, không phải chỉ dẫn rằng upload repo hiện tại sẽ chạy được.

| Thành phần hiện tại | Khi chuyển toàn bộ |
| --- | --- |
| SQLite trên Railway Volume | Supabase PostgreSQL |
| `/webhooks/qonversion/{app_key}` | Edge Function nhận webhook theo app |
| Google Play verification bằng Python | Logic tương đương chạy trên backend mới |
| Báo cáo Python, xuất Google Sheets | Logic tương đương trên backend mới |
| APScheduler | Supabase Cron gọi chức năng sync |
| Trang `/`, nút Sync, `/health`, `/admin/sync` | Giao diện và endpoint tương ứng cần triển khai |

Nếu chỉ chuyển database sang Supabase thì vẫn cần nơi chạy Python. Cách này giảm phần phải viết lại nhưng chưa đáp ứng yêu cầu rời Railway hoàn toàn.

## 2. Cứu dữ liệu trước khi hết thời hạn giữ volume

Theo tài liệu Railway được kiểm tra tại thời điểm viết, volume của tài khoản Trial bị xóa sau 30 ngày kể từ khi credits hết hạn. Không coi việc không bấm Wipe là cách giữ dữ liệu lâu dài.

1. Đăng nhập Railway, chọn đúng project và environment production.
2. Mở service IAP Analytics, kiểm tra trạng thái deployment và volume đang gắn.
3. Ghi lại ngày hết credits và thông báo thời hạn xóa nếu có.
4. Không xóa project, volume hoặc bấm Wipe.
5. Nếu không truy cập/tải được do Trial hết hạn: liên hệ Railway support hoặc nâng cấp tạm để lấy dữ liệu trước khi volume bị xóa. Không có bảo đảm nâng cấp sẽ khôi phục volume đã bị xóa.

Nguồn: [Railway Free Trial](https://docs.railway.com/pricing/free-trial).

## 3. Lưu cấu hình riêng

Trong Railway → service → Variables, lưu các giá trị sau vào nơi riêng an toàn, bên ngoài Git:

- `DB_PATH`, `APPS_CONFIG_YAML` và `APPS_CONFIG`.
- `GOOGLE_SERVICE_ACCOUNT_JSON` và `GOOGLE_APPLICATION_CREDENTIALS`.
- `WEBHOOK_TOKEN`, `SHEET_ID`.
- `SYNC_MINUTE`, `TZ`, `ORDER_RECHECK_DAYS`, `ENABLE_SHEETS`.
- Các biến bổ sung đang có, domain hiện tại và Start Command.

Lưu danh sách URL webhook theo app từ Qonversion. Giữ nguyên `app_key`, package, mapping sản phẩm và cấu hình báo cáo. `APPS_CONFIG_YAML` có thể chứa cấu hình nhiều hơn ví dụ trong README.

Không đưa khóa Google, token, database hoặc connection string vào commit, ảnh chụp công khai hay log. Google Sheet là báo cáo; nó không thay thế được database gốc và raw webhook.

## 4. Cài và kết nối Railway CLI

Cài Railway CLI theo [hướng dẫn chính thức](https://docs.railway.com/guides/cli). Mở PowerShell và kiểm tra:

```powershell
railway --version
railway login
railway link
```

Trong `railway link`, chọn đúng workspace, project, environment và service chứa volume production. Nếu CLI hỏi thêm volume, chọn đúng volume đang mount cho service.

Mở trình duyệt volume:

```powershell
railway volume browse /
```

`/` trong trình duyệt này là gốc volume, không nhất thiết là gốc filesystem của container. Volume mount tại `/data` có thể hiển thị `iap.sqlite3` ngay ở gốc. Dùng danh sách thực tế để xác định đường dẫn trước khi tải.

Nguồn: [Railway volume CLI](https://docs.railway.com/cli/volume).

## 5. Tạo và tải bản sao SQLite

### Trường hợp A: service còn chạy

Không tải riêng file SQLite đang bị ghi. Dùng SQLite backup API để tạo snapshot nhất quán:

1. Mở Railway SSH vào đúng container đang chạy, theo [hướng dẫn SSH](https://docs.railway.com/guides/ssh).
2. Chạy lệnh sau **trong shell Linux của container**, không chạy trong PowerShell local:

```bash
python - <<'PY'
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

source = Path(os.environ.get('DB_PATH', '/data/iap.sqlite3')).resolve()
if not source.is_file():
    raise SystemExit(f'Không tìm thấy database: {source}')
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
target = source.with_name(f'iap-backup-{stamp}.sqlite3')
src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30)
dst = sqlite3.connect(target)
try:
    src.backup(dst)
    result = dst.execute('PRAGMA integrity_check').fetchall()
    if result != [('ok',)]:
        raise SystemExit(f'Backup không đạt integrity_check: {result}')
    print('Backup OK:', target)
    for table in ('events', 'orders', 'sync_log'):
        count = dst.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        print(table, count)
finally:
    dst.close()
    src.close()
PY
```

Lệnh chỉ đọc database gốc, tạo file backup mới cùng thư mục. Cần đủ dung lượng trống; nếu thiếu, không xóa database gốc để lấy chỗ.

3. Ghi lại tên file backup và số dòng được in ra.
4. Trở về PowerShell local, mở `railway volume browse /`, tải file backup vừa tạo về thư mục riêng trên máy.

Có thể tải bằng CLI sau khi xác nhận đường dẫn. Ví dụ dưới đây phải thay bằng tên file thực tế trong volume:

```powershell
New-Item -ItemType Directory -Force C:\iap-backups
railway volume files download /iap-backup-TIMESTAMP.sqlite3 C:\iap-backups\iap-backup.sqlite3
```

Không dùng `railway run` để đọc volume remote: lệnh đó chạy process trên máy local với biến môi trường Railway.

### Trường hợp B: service đã dừng

1. Xác nhận không còn process ghi vào database.
2. Dùng trình duyệt volume tải **toàn bộ nội dung volume** vào một thư mục riêng.
3. Giữ nguyên các file phụ như `iap.sqlite3-wal`, `iap.sqlite3-shm`, `iap.sqlite3-journal` nếu có. Không bỏ file WAL vì có thể chứa dữ liệu chưa nhập vào file chính.
4. Giữ bản tải gốc nguyên vẹn; tạo bản sao thư mục để kiểm tra hoặc mở database.
5. Nếu công cụ không cho tải khi service dừng, xử lý quyền truy cập với Railway; không Wipe để thử sửa.

## 6. Kiểm tra backup trên máy

Cần Python 3. Trong PowerShell, sửa đường dẫn thành file snapshot đã tải hoặc file database trong **bản sao thư mục kiểm tra** ở trường hợp B:

```powershell
$env:IAP_BACKUP_FILE = 'C:\iap-backups\iap-backup.sqlite3'
@'
import os
import sqlite3
from pathlib import Path

p = Path(os.environ['IAP_BACKUP_FILE']).resolve()
if not p.is_file():
    raise SystemExit(f'Không tìm thấy file: {p}')
db = sqlite3.connect(p.as_uri() + '?mode=ro', uri=True)
try:
    result = db.execute('PRAGMA integrity_check').fetchall()
    print('integrity_check:', result)
    if result != [('ok',)]:
        raise SystemExit('Backup không đạt kiểm tra')
    for table in ('events', 'orders', 'sync_log'):
        print(table, db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
finally:
    db.close()
'@ | python -
Get-FileHash -Algorithm SHA256 -LiteralPath $env:IAP_BACKUP_FILE
```

Nếu máy dùng Python launcher, thay `python -` bằng `py -3 -`. Nếu database kèm journal cần phục hồi mà mở read-only báo lỗi, giữ nguyên bản gốc và thực hiện phục hồi trên bản sao bằng công cụ SQLite trước khi kiểm tra lại.

Điều kiện đạt:

- `integrity_check` trả về `ok`.
- Có đủ ba bảng, số dòng khớp snapshot đã tạo.
- Đọc được dữ liệu sự kiện và đơn hàng đại diện; bảng trống chỉ hợp lệ nếu nguồn cũng trống.
- Có thêm một bản sao ở nơi độc lập, riêng tư, ngoài Railway và ngoài repo.

Integrity check xác nhận cấu trúc SQLite hợp lệ, không chứng minh dữ liệu lịch sử đã đầy đủ. Giữ số dòng, thời điểm snapshot và hash để đối chiếu sau import.

## 7. Tạo Supabase project

1. Đăng nhập [Supabase Dashboard](https://supabase.com/dashboard).
2. Chọn organization → New project.
3. Đặt tên project, chọn region phù hợp và tạo mật khẩu database mạnh; lưu vào trình quản lý mật khẩu.
4. Chờ project sẵn sàng.
5. Mở Connect, lấy connection string phù hợp với môi trường chạy script import. Máy chỉ có IPv4 có thể cần session pooler; kiểm tra hướng dẫn kết nối.
6. Lưu project URL, project reference và thông tin kết nối ở nơi riêng.
7. Kiểm tra giới hạn gói đang chọn: database, Edge Functions, Cron và chính sách tạm dừng. Không mặc định toàn bộ workload sẽ miễn phí mãi.

Nguồn: [Kết nối PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres), [giới hạn Edge Functions](https://supabase.com/docs/guides/functions/limits).

## 8. Tạo schema và chuyển dữ liệu

**Bước này cần triển khai migration/import; repo hiện chưa có công cụ thực thi. Không dán nguyên SQLite dump vào PostgreSQL.**

1. Tạo migration PostgreSQL từ schema trong `app/main.py`, hàm `init_db()`.
2. Giữ primary key `events(event_key)` và `orders(app_key, order_id)`, index sự kiện theo app/order, cùng các ràng buộc NOT NULL.
3. Chuyển `sync_log.id` sang identity/sequence phù hợp PostgreSQL. Sau import phải cập nhật sequence theo ID lớn nhất để lần ghi tiếp theo không trùng khóa.
4. Giữ nguyên `raw_json`, `payload`, ID, giá trị rỗng/NULL và chuỗi thời gian. Nếu đổi kiểu sang JSONB hoặc timestamp, cần kiểm thử tương thích báo cáo trước.
5. `charged` và `developer_revenue` hiện lưu dạng TEXT rồi xử lý bằng Decimal. Không chuyển qua float; nếu đổi sang NUMERIC phải kiểm tra độ chính xác và cách biểu diễn.
6. Dùng script đọc SQLite và ghi PostgreSQL bằng truy vấn có tham số, import theo transaction/batch có kiểm soát. Script phải phát hiện lỗi hoặc xung đột, không âm thầm bỏ dòng.
7. Không cho frontend đọc trực tiếp dữ liệu IAP: bật RLS và cấu hình quyền phù hợp. Key đặc quyền/connection string chỉ dùng phía server.
8. Đối chiếu số dòng, tập khóa chính, trường dữ liệu và tổng tiền theo app/currency. Có thể đối chiếu hash nội dung sau khi chuẩn hóa cùng cách ở hai phía.

Nguồn: [Import dữ liệu Supabase](https://supabase.com/docs/guides/database/import-data), [bảo vệ dữ liệu](https://supabase.com/docs/guides/database/secure-data).

## 9. Triển khai backend Supabase tương đương

Phải hoàn tất các phần sau trước khi đổi webhook production:

1. **Webhook:** chuyển logic `normalize_webhook()` và endpoint Qonversion, giữ cách tạo `event_key`, xử lý trùng, giới hạn payload, kiểm tra app/package và mã phản hồi.
2. **Xác thực:** giữ hợp đồng header hiện có, bao gồm ưu tiên `Authorization`, dạng `Basic <token thô>` theo triển khai hiện tại và các header dự phòng. Không tự đổi sang Base64.
3. **Gateway:** webhook Qonversion không mang Supabase user JWT. Cấu hình xác thực gateway phù hợp cho riêng function này và bắt buộc function tự kiểm tra secret; chỉ tắt kiểm tra JWT không làm webhook an toàn.
4. **Google credentials:** lưu JSON service account trong server secrets, triển khai OAuth/service-account signing để gọi Google Play và Google Sheets.
5. **Đối soát đơn:** giữ logic app mapping, sandbox/production, cửa sổ recheck và xử lý lỗi như source hiện tại.
6. **Báo cáo:** chuyển logic trong `app/reports.py`, `app/ua_reports.py`, `app/report_columns.py`; giữ cột tiếng Việt, thứ tự tab, quy tắc doanh thu, tiền tệ và trạng thái dữ liệu thiếu.
7. **Sync:** giữ thao tác thủ công, trạng thái busy/error và khả năng tránh hai job cùng ghi. Khóa Python trong RAM không thể mang nguyên sang nhiều function; cần khóa dùng chung có cơ chế giải phóng khi lỗi.
8. **Cron:** giữ lịch tương đương `SYNC_MINUTE` và `TZ`; xác minh timezone của lịch mới. Nếu chia sync thành nhiều lần xử lý để phù hợp giới hạn function, phải đảm bảo xử lý đủ dữ liệu và phục hồi khi lỗi.
9. **Trang quản trị:** triển khai trạng thái, nút Sync và healthcheck tương ứng; bảo vệ thao tác sync bằng xác thực server.

Không đặt token hoặc key đặc quyền vào HTML/JavaScript công khai. Giữ cùng `SHEET_ID` và service account thì có thể tiếp tục dùng Sheet đã chia sẻ quyền Editor.

Nguồn: [Edge Functions](https://supabase.com/docs/guides/functions), [Function secrets](https://supabase.com/docs/guides/functions/secrets), [lập lịch](https://supabase.com/docs/guides/functions/schedule-functions).

## 10. Kiểm thử trước khi chuyển production

1. Chạy các bộ test hiện tại để lấy hành vi tham chiếu; bổ sung kiểm thử tương đương cho backend mới.
2. Kiểm tra webhook hợp lệ, sai token, sai app, JSON lỗi, payload lớn và gửi lại cùng sự kiện.
3. Kiểm tra ID/key và timestamp sinh ra giống backend hiện tại trên cùng payload.
4. Kiểm tra Google Play bằng đơn production thật có quyền đọc, không dùng đơn giả để kết luận kết nối hoạt động.
5. Xuất báo cáo vào **Sheet thử riêng**, đối chiếu cùng snapshot với báo cáo Python.
6. Kiểm tra manual sync, lỗi API, sync chồng nhau và Cron thực sự chạy đúng thời điểm.
7. Kiểm tra dữ liệu và secrets không truy cập được qua client không có quyền.

Không dùng hai backend cùng xuất vào Sheet production trong giai đoạn thử.

## 11. Chuyển webhook production và chốt dữ liệu

1. Chọn thời điểm chuyển, ghi lại mốc UTC và chuẩn bị cách quay lại backend cũ nếu còn chạy được.
2. Nếu Railway vẫn nhận webhook sau snapshot đầu: phải lấy snapshot/delta cuối và nhập các thay đổi. Không bỏ qua sự kiện hay cập nhật đơn phát sinh sau snapshot.
3. Chỉ để một scheduler xuất Sheet production. Tắt lịch cũ tại thời điểm chuyển có kiểm soát, bật lịch mới sau khi dữ liệu đã đối chiếu.
4. Trong Qonversion, cập nhật URL webhook từng app sang endpoint Supabase đã triển khai. Lấy URL thật từ deployment, không đoán đường dẫn.
5. Giữ cấu hình authorization tương thích; gửi test event và kiểm tra logs cùng dòng dữ liệu được ghi.
6. Đối chiếu sự kiện quanh mốc chuyển ở cả hai nơi; dùng khóa sự kiện để xử lý sự kiện gửi lặp. Xác minh khả năng gửi lại sự kiện với Qonversion, không mặc định mọi sự kiện bị gián đoạn sẽ tự phục hồi.
7. Nếu Railway đã dừng từ trước, xác định khoảng gián đoạn và khả năng backfill từ nguồn. Google Play Orders API không tự liệt kê toàn bộ lịch sử đơn; database thiếu order ID có thể không khôi phục đủ bằng sync.
8. Chạy sync trên hệ thống mới, xác nhận Sheet production cập nhật đúng và các lần Cron kế tiếp thành công.

Nếu phải quay lại Railway, cần đảm bảo dữ liệu nhận ở Supabase trong thời gian chuyển cũng được bảo toàn và nhập lại đúng. Không chỉ đổi URL ngược rồi bỏ dữ liệu mới.

## 12. Chỉ xóa Railway khi đã hoàn tất

- [ ] Có backup SQLite độc lập đã kiểm tra, cấu hình/secrets đã lưu an toàn.
- [ ] Có backup PostgreSQL và đã thử khôi phục ở môi trường riêng.
- [ ] Dữ liệu nguồn/đích khớp; đã xử lý phần phát sinh trong lúc chuyển.
- [ ] Tất cả app nhận webhook qua URL mới và xác thực đúng.
- [ ] Google Play verification, báo cáo, manual sync và Cron chạy đúng.
- [ ] Google Sheet production cập nhật đúng; không còn hai backend ghi đồng thời.
- [ ] Đã đánh giá khoảng gián đoạn và dữ liệu không thể backfill nếu có.

Sau đó mới cân nhắc xóa service/volume cũ để ngừng chi phí. **Không cần Wipe Volume để migrate.** Backup nằm cùng volume/Railway không thay cho bản backup bên ngoài trước khi xóa.

## Lỗi thường gặp

| Vấn đề | Cách xử lý |
| --- | --- |
| Không thấy SQLite | Kiểm tra DB_PATH, environment, service và volume mount thực tế |
| CLI thiếu lệnh volume browse | Kiểm tra/cập nhật Railway CLI theo tài liệu chính thức |
| Trial hết, không truy cập được volume | Liên hệ hỗ trợ hoặc nâng cấp tạm trước hạn xóa |
| File SQLite rỗng sau khi mở | Kiểm tra đường dẫn; dùng chế độ read-only để tránh tự tạo DB mới |
| Backup báo thiếu bảng hoặc integrity lỗi | Giữ bản gốc, lấy lại snapshot đúng DB; kiểm tra WAL/journal trên bản sao |
| Webhook Supabase báo 401 trước khi vào handler | Kiểm tra cấu hình JWT gateway và xác thực secret trong function |
| Sheets 403 hoặc không tìm thấy | Kiểm tra SHEET_ID, Sheets API và quyền Editor của service account |
| Sync bị timeout | Đo workload và thiết kế chia việc có phục hồi; không tự bỏ bớt dữ liệu |
| Volume đã bị Wipe/xóa | Tìm bản sao bên ngoài; hỏi Railway support, không bảo đảm khôi phục được |
