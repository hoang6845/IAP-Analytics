# IAP Analytics — Qonversion → Google Play → Google Sheets

## Hướng dẫn setup local và deploy Railway

### 1. Thiết lập Google từng bước

Chuẩn bị tài khoản có quyền tạo project/bật API trong Google Cloud, quyền mời người dùng trong Play Console và quyền chia sẻ Google Sheet. Cài Docker Desktop hoặc Docker Engine + Compose V2 để chạy local.

Thực hiện theo thứ tự **1.1 → 1.7**. Tên menu bên dưới dùng giao diện tiếng Anh để dễ tìm; nếu giao diện khác, dùng ô tìm kiếm của Console.

#### 1.1. Tạo Google Cloud project

1. Mở [Google Cloud Console](https://console.cloud.google.com/), đăng nhập.
2. Bấm bộ chọn project ở thanh trên cùng → **New Project**.
3. Đặt **Project name**, ví dụ `iap-analytics`. Chọn Organization/Location phù hợp nếu tài khoản thuộc công ty.
4. Bấm **Create**, chờ tạo xong rồi chọn project mới trên thanh trên cùng.
5. Ghi lại **Project ID** trong trang thông tin project. Giữ project này được chọn khi bật API và tạo service account.
<!-- iap-analytics-511009 -->
Nếu đã có project dùng cho hệ thống, chọn project đó thay vì tạo mới.

#### 1.2. Bật Google Play Android Developer API

1. Trong project đã chọn, vào **☰ → APIs & Services → Library**.
2. Tìm chính xác **Google Play Android Developer API**.
3. Mở kết quả có service name `androidpublisher.googleapis.com`, bấm **Enable**.
4. Nếu hiện **Manage**, API đã được bật.
5. Vào **APIs & Services → Enabled APIs & services** để kiểm tra API có trong danh sách.

Có thể mở trực tiếp [trang bật Google Play Android Developer API](https://console.cloud.google.com/apis/library/androidpublisher.googleapis.com); kiểm tra project ở thanh trên trước khi bấm Enable.

API này cung cấp `orders.get` mà ứng dụng sử dụng. **Google Play Developer Reporting API** là API khác, không thay thế API này.

Google hiện không yêu cầu liên kết developer account với Cloud project để dùng Play Developer API. Bật API trong Cloud và cấp quyền service account trong Play Console ở bước 1.5 là hai việc riêng. Nguồn: [Google Play API Getting Started](https://developers.google.com/android-publisher/getting_started).

#### 1.3. Bật Google Sheets API

1. Giữ nguyên Cloud project ở bước 1.1.
2. Vào **APIs & Services → Library**.
3. Tìm **Google Sheets API**, mở kết quả có service name `sheets.googleapis.com`.
4. Bấm **Enable**, hoặc kiểm tra đã hiện **Manage**.
5. Trong **Enabled APIs & services**, xác nhận cả Play Android Developer API và Sheets API đều đã bật.

Link trực tiếp: [Google Sheets API trong Cloud Console](https://console.cloud.google.com/apis/library/sheets.googleapis.com). Nguồn: [Google Sheets API setup](https://developers.google.com/workspace/sheets/api/quickstart/python).

Mã hiện tại mở Sheet bằng ID và dùng Sheets API; không cần Drive API cho luồng này. Nếu mở rộng sang tìm file bằng tên/quản lý file Drive, cần bật Drive API và cấu hình scope phù hợp.

#### 1.4. Tạo service account và tải JSON key

**Tạo tài khoản**

1. Trong Cloud Console, vào **☰ → IAM & Admin → Service Accounts**, hoặc [mở Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts).
2. Kiểm tra đúng project, bấm **Create service account**.
3. Điền tên `iap-analytics`; để Console tạo Service account ID.
4. Bấm **Create and continue**.
5. Ở bước cấp quyền truy cập Cloud project, để trống role cho cấu hình này. Quyền Play và Sheet được cấp riêng; không cần cấp Owner/Editor của Cloud project cho service account.
6. Bấm **Continue**, để trống phần cấp quyền người dùng lên service account nếu không có yêu cầu nội bộ, rồi **Done**.
7. Sao chép email service account, dạng `iap-analytics@YOUR_PROJECT_ID.iam.gserviceaccount.com`.
<!-- iap-analytics@iap-analytics-511009.iam.gserviceaccount.com -->
Nguồn: [Google Cloud — tạo service account](https://docs.cloud.google.com/iam/docs/service-accounts-create).

**Tạo key**

1. Trong danh sách Service Accounts, bấm email tài khoản vừa tạo.
2. Mở tab **Keys** → **Add key** → **Create new key**.
3. Chọn **JSON** → **Create**. Trình duyệt tải file JSON.
4. Lưu file an toàn; Google không cho tải lại chính key này sau khi đóng bước tải.
5. Mở file bằng editor local, kiểm tra `type` là `service_account` và `client_email` đúng email vừa sao chép. Không gửi nội dung private_key cho người khác.

Nếu nút tạo key bị chặn do organization policy, liên hệ quản trị viên tổ chức để xử lý quyền/chính sách cho project; đổi tên file không giải quyết được. Nguồn: [Google Cloud — tạo JSON key](https://docs.cloud.google.com/iam/docs/keys-create-delete).

**Dùng key trong dự án**

- Local: tạo thư mục `secrets`, lưu file thành `secrets/google-service-account.json`.
- Railway: dán toàn bộ nội dung JSON vào biến `GOOGLE_SERVICE_ACCOUNT_JSON` theo phần deploy bên dưới.
- Dùng chính email `client_email` của key này ở cả Play Console và Google Sheet. Không dùng email đăng nhập cá nhân để thay thế.
<!-- google-service-account -->
#### 1.5. Cấp quyền service account trong Google Play Console

1. Mở [Google Play Console](https://play.google.com/console/), chọn đúng developer account sở hữu app.
2. Ở cấp developer account, vào **Users and permissions** → **Invite new users**.
3. Dán email service account từ bước 1.4 vào trường Email.
4. Mở **App permissions** → **Add app**, chọn từng app cần theo dõi.
5. Với từng app, cấp quyền đọc thông tin app (**View app information (read-only)** nếu giao diện yêu cầu) và quyền đọc dữ liệu tài chính/đơn hàng. Nhãn có thể là **View financial data** hoặc **View financial data, orders, and cancellation survey responses**, tùy phạm vi quyền/giao diện.
6. Kiểm tra phạm vi chỉ gồm app cần dùng; không cấp Admin, quyền phát hành hoặc chỉnh sửa app.
7. Bấm **Invite user** / lưu lời mời. Service account không có hộp thư cá nhân để bạn đăng nhập và bấm nhận thư.
8. Kiểm tra lại mục người dùng: email service account và danh sách app/quyền đã được ghi nhận.
9. Lấy package name của từng app, ví dụ từ URL Store `https://play.google.com/store/apps/details?id=com.example.keyboard`; điền đúng vào `config/apps.yaml`.

Bật API trong Cloud không tự cấp quyền đọc app. Thêm service account vào Cloud IAM cũng không thay cho bước mời trong Play Console. Nguồn: [Play Console — quyền người dùng và app](https://support.google.com/googleplay/android-developer/answer/9844686).

Dự án chỉ gọi `orders.get`. Bắt đầu với quyền đọc và kiểm tra bằng đơn thật. Hướng dẫn Google cho Billing APIs nói chung liệt kê thêm quyền **Manage orders and subscriptions**; quyền này rộng hơn nhu cầu đọc. Nếu vẫn gặp 403 sau khi xác minh key, API và app permissions, đối chiếu lỗi với [hướng dẫn Google](https://developers.google.com/android-publisher/getting_started) và xác nhận với chủ tài khoản trước khi cấp thêm quyền quản lý đơn.

#### 1.6. Tạo Google Sheet và chia sẻ cho service account

1. Mở [Google Sheets](https://sheets.google.com/) bằng tài khoản Google của bạn.
2. Tạo **Blank spreadsheet**, đặt tên, ví dụ `IAP Analytics`. Nên dùng file riêng vì ứng dụng cập nhật các tab báo cáo.
3. Bấm **Share** ở góc trên phải.
4. Trong ô thêm người dùng, dán email service account ở bước 1.4.
5. Chọn **Editor** → **Send** hoặc **Share** để lưu. Không cần bật chia sẻ công khai.
6. Mở lại Share để kiểm tra service account đã xuất hiện với quyền Editor.
7. Sao chép ID từ URL:

```text
https://docs.google.com/spreadsheets/d/1AbC_EXAMPLE_SHEET_ID/edit#gid=0
                                      ^^^^^^^^^^^^^^^^^^^^^
SHEET_ID=1AbC_EXAMPLE_SHEET_ID
```

Chỉ lấy chuỗi giữa `/d/` và `/edit`, không lấy URL đầy đủ và không lấy `gid=0`.

Điền ID vào `.env` khi chạy local hoặc Railway Variables khi deploy. Ứng dụng tự tạo các tab báo cáo khi sync thành công; không cần tạo thủ công trước.
<!-- 1a_XlkSuas2-_654CBmk3KxiNKoH4YprQUi7XUmuOPZs -->
Service account không tự nhìn thấy Sheet trong tài khoản cá nhân. Nếu thiếu chia sẻ có thể gặp `SpreadsheetNotFound` hoặc lỗi quyền. Nếu Workspace chặn chia sẻ ngoài tổ chức, cần quản trị viên cho phép chia sẻ phù hợp. Nguồn: [gspread — service account và chia sẻ Sheet](https://docs.gspread.org/en/latest/oauth2.html).

#### 1.7. Kiểm tra cấu hình Google trước khi nhận dữ liệu thật

Trước khi chạy, xác nhận:

- Play Android Developer API và Sheets API bật trong project của JSON key.
- JSON có đúng client_email, service account được cấp quyền cho đúng app.
- package_name là package thật, không phải tên hiển thị.
- Google Sheet đã chia sẻ Editor cho đúng client_email.
- SHEET_ID là ID, không phải URL.
- JSON key ở đường dẫn local hoặc Railway Variables như hướng dẫn.

Sau khi chạy Docker Compose ở phần 2, kiểm tra key có thể lấy access token, không in token/khóa ra terminal:

```bash
docker compose exec iap-analytics python -c "from app.main import creds; from google.auth.transport.requests import Request; c=creds(); c.refresh(Request()); print('Google authentication OK')"
```

Kiểm tra đọc metadata của Sheet:

```bash
docker compose exec iap-analytics python -c "import os,gspread; from app.main import creds; s=gspread.authorize(creds()).open_by_key(os.environ['SHEET_ID']); print('Google Sheet accessible:', s.title)"
```

Hai lệnh này không ghi dữ liệu Sheet và chưa chứng minh quyền ghi. Kiểm tra quyền Editor trong Share, sau đó xác nhận export ở lần sync thật.

Để kiểm tra Play bằng **Order ID production thật của đúng app**, thay package và Order ID trong lệnh sau:

```bash
docker compose exec iap-analytics python -c "from app.main import creds,fetch_order; from google.auth.transport.requests import AuthorizedSession; s=AuthorizedSession(creds()); o=fetch_order(s,'com.example.keyboard','YOUR_REAL_GPA_ORDER_ID'); print('Google Play order accessible' if o else 'Order not found: check package/order ID')"
```

Lệnh chỉ đọc Play, không lưu đơn vào SQLite. Nếu 403: kiểm tra API/quyền/app; nếu không tìm thấy: kiểm tra package, Order ID và môi trường giao dịch. Không dùng ID giả trong ví dụ để kết luận quyền API đã hoạt động.

#### 1.8. Lấy Qonversion App ID để chuẩn bị cấu hình

1. Đăng nhập Qonversion Dashboard và chọn project/app tương ứng với app Google Play cần theo dõi.
2. Lấy App ID của project/app để điền vào `qonversion_app_id` trong `config/apps.yaml` ở bước 2. Giá trị phải khớp trường `app_id` mà Qonversion gửi trong payload.
3. Chọn `app_key` ổn định, ví dụ `cute_keyboard`, để dùng trong YAML và đường dẫn webhook sau này.

Sau bước này, tiếp tục **bước 2: setup local → bước 3: deploy Railway và tạo domain → kết nối Qonversion**. Cấu hình URL webhook sau khi đã có domain public HTTPS và kiểm tra `/health` thành công.

Không commit JSON key, token hoặc dữ liệu SQLite lên Git.

### 2. Setup local

Tại thư mục dự án, chạy PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item config/apps.example.yaml config/apps.yaml
New-Item -ItemType Directory -Force secrets, data
```

Linux/macOS:

```bash
cp .env.example .env
cp config/apps.example.yaml config/apps.yaml
mkdir -p secrets data
```

Đặt JSON key tại `secrets/google-service-account.json`. Chỉnh `config/apps.yaml` bằng dữ liệu thật:

```yaml
apps:
  - key: cute_keyboard
    package_name: com.example.keyboard
    qonversion_app_id: YOUR_REAL_QONVERSION_APP_ID
```

Mỗi key phải duy nhất và khớp đường dẫn webhook. Xóa các app mẫu không dùng.

Chỉnh `.env`:

| Biến | Giá trị / ý nghĩa |
|---|---|
| SHEET_ID | ID Google Sheet |
| WEBHOOK_TOKEN | Secret ngẫu nhiên, ít nhất 24 ký tự |
| GOOGLE_APPLICATION_CREDENTIALS | /run/secrets/google-service-account.json |
| APPS_CONFIG | /code/config/apps.yaml |
| DB_PATH | /data/iap.sqlite3 |
| SYNC_MINUTE | 5: sync vào phút 05 mỗi giờ |
| TZ | Asia/Bangkok |
| ORDER_RECHECK_DAYS | 45: cửa sổ kiểm tra lại đơn |
| ENABLE_SHEETS | true để xuất Sheets |

`ORDER_BATCH_SIZE` có trong file mẫu nhưng mã hiện tại chưa sử dụng.

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f iap-analytics
docker compose exec iap-analytics python -m unittest discover -s tests -v
```

Mở `http://127.0.0.1:8000/health`, mong đợi `"status":"ok"`. Compose chỉ mở cổng trên localhost; cần public HTTPS qua reverse proxy/tunnel để nhận webhook từ Qonversion.

Test bằng PowerShell:

```powershell
$headers = @{ 'X-Webhook-Token' = 'YOUR_WEBHOOK_TOKEN' }
$body = '{"event_name":"subscription_started","environment":"sandbox","transaction":{"transaction_id":"GPA.EXAMPLE-DO-NOT-USE"}}'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/webhooks/qonversion/cute_keyboard' -Headers $headers -ContentType 'application/json' -Body $body
```

Mong đợi `accepted: true`; gửi lại có `duplicate: true`. Sandbox được lưu nhưng không dùng để kiểm tra đơn production. Cần giao dịch production thật để kiểm tra quyền Google và mapping Order ID.

### 3. Deploy Railway

Railway build Dockerfile ở root repo. Bind mount của Compose cần cấu hình riêng; xem [hướng dẫn Railway](https://docs.railway.com/guides/docker-compose).

**Tạo service**

1. Push source lên GitHub, gồm Dockerfile, requirements.txt, app/ và tests/. Nếu chưa là Git repo, khởi tạo Git và cấu hình remote trước.
2. Kiểm tra không commit .env, secrets/, data/ hoặc config/apps.yaml; .gitignore đã loại các đường dẫn này.
3. Tạo Railway project, chọn GitHub repo/branch. Root Directory là thư mục chứa Dockerfile.
4. Thêm **Volume** mount tại **/data** để SQLite tồn tại qua redeploy. File ngoài volume là lưu trữ tạm thời; xem [Railway Services](https://docs.railway.com/services).
5. Giữ **1 replica**, **1 Uvicorn worker** để tránh nhiều scheduler chạy trùng. Giữ service chạy liên tục nếu có tùy chọn tự sleep.

**Variables**

Thêm vào tab Variables:

```dotenv
PORT=8000
DB_PATH=/data/iap.sqlite3
APPS_CONFIG=/tmp/apps.yaml
GOOGLE_APPLICATION_CREDENTIALS=/tmp/google-service-account.json
SHEET_ID=YOUR_REAL_SHEET_ID
WEBHOOK_TOKEN=YOUR_RANDOM_SECRET_AT_LEAST_24_CHARACTERS
SYNC_MINUTE=5
TZ=Asia/Bangkok
ORDER_RECHECK_DAYS=45
ENABLE_SHEETS=true
```

Thêm hai biến bằng trình chỉnh sửa từng biến để giữ nội dung nhiều dòng:

- `GOOGLE_SERVICE_ACCOUNT_JSON`: toàn bộ JSON key Google, gồm dấu { ... }. Giữ nguyên escape `\n` trong private_key, không thêm dấu nháy bao quanh toàn bộ JSON. Đây là secret.
- `APPS_CONFIG_YAML`: toàn bộ YAML cấu hình app thật theo ví dụ local.

Ứng dụng đọc file; Start Command sau chuyển các biến này thành file khi khởi động.

**Start Command**

Trong **Settings → Deploy → Start Command**, dán nguyên lệnh **một dòng**:

```bash
python -c 'import os,json,pathlib; p=pathlib.Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]); p.write_text(json.dumps(json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])), encoding="utf-8"); p.chmod(0o600); pathlib.Path(os.environ["APPS_CONFIG"]).write_text(os.environ["APPS_CONFIG_YAML"], encoding="utf-8"); os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", os.environ["PORT"], "--workers", "1"])'
```

Lệnh tạo khóa Google và YAML tại /tmp rồi chạy Uvicorn; SQLite lưu trên volume /data. Dùng **Start Command**, không dùng Pre-deploy vì file phải được tạo trong container chạy app.

**Healthcheck và domain**

1. Đặt **Healthcheck Path** là `/health`.
2. Trong Networking, chọn **Generate Domain**, target port **8000**.
3. Apply thay đổi và deploy/redeploy.
4. Kiểm tra logs có `Scheduler ready` và server chạy tại `0.0.0.0:8000`.
5. Mở `https://<RAILWAY_DOMAIN>/health`, mong đợi status: ok.
<!-- https://iap-analytics-production.up.railway.app/health -->
PORT=8000 khớp server và healthcheck. Railway kiểm tra healthcheck khi deploy, không giám sát liên tục sau deploy; deployment có volume có thể gián đoạn ngắn. Xem [Railway Healthchecks](https://docs.railway.com/deployments/healthchecks).

**Kết nối Qonversion — sau khi Railway có domain**

Thực hiện phần này sau khi deployment Railway chạy thành công, đã Generate Domain và mở được `https://<RAILWAY_DOMAIN>/health`.

1. Trong Qonversion Dashboard, chọn đúng project/app rồi mở tích hợp **Webhooks**.
2. Bật các sự kiện production cần theo dõi: mua hàng, subscription, renewal và refund.
3. Điền URL `https://<RAILWAY_DOMAIN>/webhooks/qonversion/<app_key>`, ví dụ `https://<RAILWAY_DOMAIN>/webhooks/qonversion/cute_keyboard`. Thay domain bằng domain Railway và app_key bằng key trong YAML.
4. Điền **Header Authorization-Token Value** bằng `WEBHOOK_TOKEN` nguyên bản (ít nhất 24 ký tự), không thêm Basic hoặc Bearer. Qonversion tự gửi `Authorization: Basic <token>`; token không được base64. Receiver vẫn hỗ trợ các header cũ; Authorization được ưu tiên nếu có.
5. Lưu cấu hình, bật tích hợp và gửi test webhook. Kiểm tra phản hồi cùng Railway logs; xác minh `app_id` trong payload Android khớp `package_name` (không phải ID project Qonversion).
6. Kiểm tra một giao dịch production thật để xác nhận Google Play Order ID được nhận và xác minh thành công.

Có thể chạy lại test PowerShell ở bước 2 với URL Railway để kiểm tra endpoint riêng. Đợi phút SYNC_MINUTE tiếp theo, kiểm tra logs và các tab Sheets. /health thành công chưa xác nhận quyền Google hoặc sync thành công.

Có thể chạy unittest qua Railway SSH trong container đang chạy. `railway run` chạy trên máy local, không tự truy cập volume remote. Tránh chạy process sync riêng đồng thời với scheduler: khóa sync chỉ bảo vệ trong cùng process.

### Kiểm tra webhook Qonversion đã hoạt động chưa

Kiểm tra riêng việc nhận webhook và việc xác minh đơn. `/health` trả `ok` hoặc `Sync_Log` ghi `OK_PLAY` chưa chứng minh webhook production hoạt động.

**1. Kiểm tra cấu hình Qonversion**

- Chọn đúng project/app, mở Webhooks, kiểm tra tích hợp đã bật và chọn các sự kiện production cần nhận. Tham khảo [Qonversion Webhooks](https://qonversion.io/integrations/webhooks).
- Nếu vẫn dùng deployment hiện tại, destination là `https://iap-analytics-production.up.railway.app/webhooks/qonversion/cute_keyboard`. Đối chiếu domain đang chạy trong Railway.
- `app_key` phải khớp YAML đang deploy; hiện tại là `cute_keyboard`.
- Điền **Header Authorization-Token Value** bằng `WEBHOOK_TOKEN` nguyên bản. Theo [tài liệu Qonversion](https://documentation.qonversion.io/docs/webhooks), request dùng `Authorization: Basic <token>` (token không base64). Không tự thêm Basic/Bearer vào trường cấu hình. Receiver vẫn hỗ trợ `Authorization-Token` và `X-Webhook-Token`; nếu có Authorization, header này được ưu tiên.
- Nếu payload có `app_id`, giá trị Android phải khớp `package_name` đang deploy: `com.emoji.cutekeyboard.themes.fontkeyboard`. `9Wu57CCs` là ID project Qonversion, không phải store app_id. Receiver kiểm tra package để ngăn sự kiện từ app khác.

**2. Test endpoint riêng bằng PowerShell**

Lệnh này ghi sự kiện sandbox vào deployment nhưng không tính thành đơn thật. Nó kiểm tra endpoint và token; chưa chứng minh Qonversion tự gửi webhook.

```powershell
$baseUrl = 'https://iap-analytics-production.up.railway.app'
Invoke-RestMethod -Uri "$baseUrl/health"
$secureToken = Read-Host 'Nhập WEBHOOK_TOKEN của Railway' -AsSecureString
$credential = [System.Management.Automation.PSCredential]::new('webhook', $secureToken)
$headers = @{ 'X-Webhook-Token' = $credential.GetNetworkCredential().Password }
$body = @{
    event_name = 'subscription_started'
    environment = 'sandbox'
    time = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    transaction = @{ transaction_id = 'GPA.EXAMPLE-DO-NOT-USE' }
} | ConvertTo-Json -Depth 3
try {
    Invoke-RestMethod -Method Post -Uri "$baseUrl/webhooks/qonversion/cute_keyboard" -Headers $headers -ContentType 'application/json' -Body $body
} finally {
    $headers.Clear()
    Remove-Variable credential, secureToken
}
```

Mong đợi HTTP 200 với `accepted: true`, `duplicate: false` và `event_key`. Gửi lại payload y hệt có thể trả `duplicate: true`: đã nhận request nhưng không thêm dòng trùng. Mở URL webhook bằng trình duyệt dùng GET có thể trả 405 vì endpoint chỉ nhận POST.

**3. Xác nhận request đến từ Qonversion**

Nếu giao diện có chức năng gửi test hoặc lịch sử delivery, gửi test rồi xem URL đích, HTTP status và response. Nếu không có, theo dõi một sự kiện mới phát sinh qua app dùng Qonversion SDK. Đối chiếu thời điểm với Railway HTTP access logs và mã đơn trong dữ liệu sự kiện. Request tự gửi ở bước 2 không thay thế bước này.

| Kết quả | Kiểm tra |
|---|---|
| 200, accepted: true | Receiver đã lưu sự kiện hoặc nhận lại payload trùng; kiểm tra tiếp môi trường và mã đơn. |
| 401 | Token thiếu/sai hoặc dưới 24 ký tự; Qonversion cần gửi Authorization: Basic <token nguyên bản>. Không thêm Basic/Bearer vào giá trị cấu hình. |
| 404, Unknown app | app_key trên URL không có trong cấu hình đang deploy. |
| 422 | Thiếu event_name, payload không phải object hoặc app_id không khớp. |
| 400 / 413 | JSON sai / payload vượt 256 KiB. |
| 405 | Sai phương thức; cần POST. |
| 5xx / timeout | Xem Railway logs; chưa thể kết luận sự kiện đã lưu. |
| Không thấy request | Kiểm tra tích hợp đã bật, đúng project, URL và sự kiện đã phát sinh. |

**4. Kiểm tra luồng production tới Sheet**

Mở trang gốc deployment, nhập token và bấm **Sync ngay**, hoặc đợi phút `SYNC_MINUTE` mỗi giờ (mặc định phút 05). Webhook ghi SQLite; Sheet chỉ cập nhật khi sync/export thành công.

1. `Qonversion_Events` phải có sự kiện thật khớp giao dịch. Môi trường `sandbox` và `test` bị bỏ qua khi xác minh Google Play.
2. `Order ID` phải là mã Google Play thật bắt đầu bằng `GPA.`. Code lấy từ `transaction.transaction_id` hoặc `order_id`; thiếu mã hoặc mã không bắt đầu bằng `GPA.` sẽ bị bỏ qua. Product trống ở tab sự kiện chưa chứng minh lỗi: sản phẩm trong Transactions lấy từ Google Play.
3. `Sync_Log` có `verified` lớn hơn 0 nghĩa là có đơn được xác minh, có thể gồm đơn kiểm tra lại. `not_found` lớn hơn 0 nghĩa là gọi Google Play nhận 404. `verified=0, not_found=0` chưa chứng minh quyền đọc Google Play hoạt động.
4. `Transactions` phải có mã đơn tương ứng và `Google Verified = YES`; `Product_Analysis` tổng hợp các đơn đã xác minh. Xem `Last export UTC` ở Diagnostics hoặc As Of Local ở Dashboard để tránh đọc snapshot cũ; cộng 7 giờ để đổi sang giờ Việt Nam.

Nếu sync lỗi trước export, Sheet có thể chưa chứa sự kiện hoặc lỗi mới nhất. Xem Railway logs; Sheet cũ không đủ kết luận webhook chưa nhận.

**Đăng ký cũ:** sync không tự tải toàn bộ người đăng ký. Nó chỉ xác minh Order ID đã nhận; sự kiện production có mã đơn được chọn trong cửa sổ `ORDER_RECHECK_DAYS` theo thời gian sự kiện hoặc thời gian nhận (mặc định 45 ngày). Lịch sử chưa từng nhận qua webhook cần luồng nhập dữ liệu riêng.

### Sync ngay bằng nút bấm

Sau khi deploy phiên bản có tính năng này, mở trang gốc `https://<RAILWAY_DOMAIN>/` (local: `http://127.0.0.1:8000/`), nhập WEBHOOK_TOKEN của deployment và bấm **Sync ngay**.

Trang gọi POST /admin/sync với header X-Webhook-Token. Token không được nhúng vào trang hoặc lưu vào browser storage. Chỉ chia sẻ token cho người được phép chạy sync.

Chờ kết quả hoàn tất trước khi đóng trang. Nếu đã có lần sync đang chạy, trang báo chờ; nếu mất kết nối/timeout, kiểm tra logs trước khi thử lại vì lần sync có thể vẫn chạy. Lịch sync mỗi giờ tiếp tục như cũ, dùng cùng khóa với sync thủ công. Sync chỉ kiểm tra Order ID đã nhận, không tự nhập đơn lịch sử.

Để cập nhật Railway, push source mới lên repo/branch đã kết nối rồi deploy; chờ healthcheck thành công trước khi mở trang. Cập nhật local bằng docker compose up -d --build.


### 4. Xử lý lỗi

| Hiện tượng | Kiểm tra |
|---|---|
| Webhook 401 | Token thiếu/sai hoặc dưới 24 ký tự; Qonversion cần gửi Authorization: Basic <token nguyên bản>. Không thêm Basic/Bearer vào giá trị cấu hình. |
| 404 Unknown app | Key trên URL không có trong YAML |
| 422 | Thiếu event_name, payload không phải object hoặc app_id không khớp |
| 413 | Payload vượt 262.144 byte |
| Không tìm thấy YAML/JSON | File/mount local hoặc Railway Variables/Start Command |
| JSONDecodeError khi khởi động | JSON key sai định dạng/escape |
| Google API 403 | API đã bật, quyền service account và quyền Editor trên Sheet |
| Không thấy Sheets | SHEET_ID, ENABLE_SHEETS, logs, lịch sync, sự kiện production |
| Healthcheck/domain lỗi | Bind 0.0.0.0, PORT/target port 8000 và path /health |
| Mất SQLite sau redeploy | Volume /data và DB_PATH nằm trong volume |

Sao lưu SQLite định kỳ bằng backup API hoặc khi service đã dừng; kiểm tra khôi phục. Orders API không tự lấy toàn bộ lịch sử; báo cáo giữ nguyên tiền tệ, phản ánh trạng thái hiện tại và chưa thay thế Sales/Earnings reports cho đối soát tài chính. Xem chi tiết bên dưới.

Hướng dẫn cần được kiểm thử với credentials thật và deployment Railway trong môi trường của bạn.

---


A runnable **multi-app pilot** that receives Qonversion events, verifies **known Google Play order IDs** every hour, deduplicates records in SQLite, and exports country/product-level analytics into Google Sheets. No production credentials are supplied.

> **Coverage:** Google Play Orders API does **not** list all historical orders. This system observes Order IDs received through incoming Qonversion webhooks. It will **not reconstruct historic orders** that have not been captured, and the paid-order population is incomplete until a separately sourced history is imported. A production-scale financial reconciliation pipeline should additionally ingest Play **Sales/Earnings reports** from the developer reports Cloud Storage bucket. These are distinct financial/settlement datasets and must not be blindly combined with Orders API data.

> **Webhook authentication:** Set Qonversion **Header Authorization-Token Value** to the raw `WEBHOOK_TOKEN`, without Basic/Bearer prefixes. Qonversion sends `Authorization: Basic <token>` without base64 encoding, as described in [official docs](https://documentation.qonversion.io/docs/webhooks). Authorization takes precedence; legacy Authorization-Token and X-Webhook-Token remain supported. Admin sync still uses X-Webhook-Token.

## Architecture

Qonversion → `/webhooks/qonversion/{app_key}` → SQLite `events` → hourly APScheduler → Google Play `orders.get` → SQLite `orders` (UPSERT) → Sheets snapshot.

- One app is identified by a stable `key` and a Play package name.
- Webhook event payloads are stored verbatim and also indexed.
- Exact webhook duplicate payloads collapse by SHA-256 hash; distinct lifecycle events for the same order remain separate.
- Purchases are deduplicated by the composite `(app_key, order_id)` key; rechecks update the existing row.
- Google Play fields `state`, `buyerAddress.buyerCountry`, `total`, and `developerRevenueInBuyerCurrency` take precedence.
- Qonversion `country` may be IP-derived, and is reported separately (not substituted for Google's buyer country).
- We preserve original currencies; there is no fake USD conversion or cross-currency total.
- Neither cancel-subscription events nor price/trial notifications count as paid orders.
- `Qonversion_Events` contains up to 20,000 recent events; verified orders have no cap in SQLite, but full-Sheets snapshots may become slow at scale.

## 1. Google Cloud setup

1. Create a Google Cloud project (or reuse one with permission).
2. Enable **Google Play Android Developer API** and **Google Sheets API** in the service account project. The current ID-based Sheets workflow does not require the Drive API.
3. Create a **service account**, download its JSON key as `secrets/google-service-account.json`. Treat JSON as a password; restrict file permissions and never commit it.
4. In Google Play Console, grant that service account access to each selected app with the minimum **order/financial-data viewing** permissions needed to read Orders API. Account/console menus and role names can change. Avoid refund/manage permissions unless needed.
5. Open the Google Sheets file you want to use and share it with the service account email as **Editor**. Copy the spreadsheet ID from `https://docs.google.com/spreadsheets/d/<ID>/edit`.
6. Cloud project linking is no longer required. Invite the service account through Play Console Users and permissions and grant access to the selected apps; see the detailed Vietnamese setup above.

References: https://developer.android.com/google/play/developer-api , https://developers.google.com/android-publisher/api-ref/rest/v3/orders and https://docs.gspread.org/en/latest/

## 2. Qonversion setup (for each app)

Before deployment, collect the Qonversion App ID for your YAML configuration. Perform the webhook activation and destination steps below only after your Railway deployment or VPS has a working public HTTPS URL.

1. In Qonversion Dashboard, enable **Webhooks** integration for the correct project/application.
2. Enable relevant production subscription, renewal, refund and in-app purchase events.
3. Configure destination `https://YOUR_HOST/webhooks/qonversion/cute_keyboard` (or the correct unique `app_key`).
4. Set **Header Authorization-Token Value** to the raw `WEBHOOK_TOKEN` (at least 24 characters). Qonversion adds the Basic prefix in the Authorization header; do not add it yourself or base64-encode the token.
5. Send a test webhook and inspect `docker compose logs -f`. Real payload shapes/transaction ID availability vary; test the Google Play Order ID mapping with one **real, non-sandbox transaction**.
6. Webhook `app_id` is the store app ID (Android package name), not the Qonversion project ID. The receiver checks it against `package_name` to reject cross-app routing mistakes. The legacy `qonversion_app_id` setting is not used for this validation.

Reference: https://qonversion.io/integrations/webhooks

## 3. Prepare files

```bash
cp .env.example .env
cp config/apps.example.yaml config/apps.yaml
```

Edit `.env`:

- `SHEET_ID`: Google Sheet ID.
- `WEBHOOK_TOKEN`: a random secret with >=24 characters (for example `openssl rand -hex 32`).
- `ORDER_RECHECK_DAYS`: days to recheck observed past transactions (default 45); PENDING/PENDING_REFUND are always rechecked. Old refunds outside the window may not be caught unless you import changes through webhook or reports.
- `SYNC_MINUTE=5`: run at hh:05 every hour in Asia/Bangkok.
- `ENABLE_SHEETS=true`: export when API works.

Edit `config/apps.yaml` with your real package names. Remove placeholder app entries rather than use them in production. Multiple apps may share the same service account provided it has Play Console access to each.

## 4. Run on VPS or another computer

Prerequisites: Docker Engine + Compose V2 (or Docker Desktop). For public webhooks, you also need a **public HTTPS domain** and a properly configured reverse proxy (Caddy/Nginx/Cloudflare Tunnel); this starter does not automatically provision TLS or a public ingress.

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
curl http://127.0.0.1:8000/health
```

Local test (the endpoint requires the secret):

```bash
curl -X POST http://127.0.0.1:8000/webhooks/qonversion/cute_keyboard \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Token: YOUR_WEBHOOK_TOKEN' \
  -d '{"event_name":"subscription_started","time":1760000000,"environment":"sandbox","transaction":{"transaction_id":"GPA.EXAMPLE-DO-NOT-USE"}}'
```

The test event is saved but filtered out of Google Play production reconciliation. Check `/health`; inspect the database/Sheet. To force a manual sync for testing, use a one-off container process (avoid competing with the running server):

```bash
docker compose exec iap-analytics python -c 'from app.main import sync_job; sync_job()'
```

## 5. What appears in Google Sheets

| Tab | Meaning |
|---|---|
| `Transactions` | One row per verified `(app, order_id)`; state, buyer country, product, original currency, charged total, Play developer revenue. |
| `Country_Analysis` | Per-app, per-buyer-country, per-currency processed/pending/canceled/refunded counts and financial amounts. |
| `Product_Analysis` | Per-app, per-product, per-currency order stats. |
| `Dashboard` | Compact UA/PO summary per app and currency: observed payers, trials, paid transactions and amounts. |
| `Qonversion_Events` | Qonversion lifecycle event log and separately labeled IP country; excludes raw PII-rich JSON. |
| `Sync_Log` | Sync successes/errors for diagnosis. |

For a country bar chart in Sheets: Insert → Chart; use `Country_Analysis` and filter to one app plus one currency; X axis = Country, Y axis = `Charged Amount (processed)` or developer revenue. Avoid mixing currencies in one bar chart.

**Important accounting limitations:** `Charged Amount (processed)` is a current-state gross proxy (including tax), not settlement revenue, does not subtract partial refunds and excludes fully refunded orders. `Developer Revenue` applies only where Play provides that field and is not a substitute for Play earnings reports. Partial refunds are tracked separately; do not treat order `total` as cash recognized across a period. Aggregation of current order snapshots by create date is **not** a proper historical cashflow or month-end settlement report.

### Báo cáo chi tiết: loại gói, quốc gia và Dashboard

Sau khi deploy mã mới, bấm **Sync ngay**. Các tab hiện có tự mở rộng số cột/dòng, giữ đầy đủ các cột, đưa thông tin quan trọng lên đầu, thêm tiêu đề nổi bật và bộ lọc. Không cần đổi Railway Variables nếu tên product/base plan đã thể hiện rõ loại gói.

| Tab | Chi tiết bổ sung |
|---|---|
| Transactions | Plan Type, mã product:base-plan, nguồn phân loại, subscription/one-time, base plan, offer, tên sản phẩm, pricing phase, kỳ dịch vụ tại thời điểm đơn, tháng UTC, ngày local, lần xác minh cuối, thuế, sự kiện Qonversion gần nhất và quốc gia IP riêng. |
| Country_Analysis | Tổng đơn, mọi trạng thái, số gói tuần/tháng/năm/lifetime/unknown/mixed, số biến thể gói, tiền trung bình, số đơn có dữ liệu tiền, đơn có tiền lớn hơn 0, đơn 0 đồng, trial và ngày giao dịch đầu/cuối. |
| Product_Analysis | Tách theo app + product + currency + loại gói + mã plan cụ thể. Có đơn hủy, hoàn một phần, chờ hoàn, doanh thu Google cung cấp, tổng đơn, số quốc gia, dữ liệu tiền và trial. Các base plan khác nhau của cùng product không bị gộp. |
| Dashboard | Tổng quan UA/PO gọn theo app/currency: observed payers, paid transactions, trial, repeat payment và số tiền. Báo cáo chi tiết cũ chuyển sang Diagnostics. |

**Thứ tự cột để xem nhanh:** Transactions ưu tiên user, loại gói, ngày local, tiền và trạng thái; Users ưu tiên user, Payment Count, currency, tiền và gói; Country/Product ưu tiên nhóm, tổng đơn và số tiền. Nguồn phân loại, mã offer/base plan, số liệu chẩn đoán và thời gian kiểm tra chuyển về sau. Description tự cập nhật chữ cái vị trí cột. Phép tính và dữ liệu giữ nguyên; công thức/biểu đồ tham chiếu vị trí cột cần đối chiếu lại sau sync.
**Cách xác định loại gói**

`WEEKLY` = tuần, `MONTHLY` = tháng, `YEARLY` = năm, `LIFETIME` = trọn đời. `UNKNOWN` là chưa đủ dữ liệu; `MIXED` là một đơn có nhiều loại gói. Ưu tiên product và basePlanId từ đơn Google Play; nếu thiếu base plan và chỉ có một product, có thể dùng product_id của webhook cùng mã đơn và cùng store product, loại trừ sandbox/test. Không suy ra lifetime chỉ vì đây là sản phẩm mua một lần.

Tên ID có token week/weekly, month/monthly, year/yearly/annual/annually hoặc lifetime được phân loại theo quy ước đặt tên và đánh dấu **Inferred from ID naming**. Ví dụ `premium_subscription:premium-weekly-auto` được nhận là WEEKLY. Đây là suy luận từ tên ID, không phải xác nhận chu kỳ từ catalog.

Nếu ID không thể hiện rõ chu kỳ, thêm mapping chính xác trong cấu hình app. Với Railway, chỉnh `APPS_CONFIG_YAML` rồi redeploy; local chỉnh `config/apps.yaml`. Dùng ID thật của app, ví dụ:

```yaml
apps:
  - key: cute_keyboard
    package_name: com.emoji.cutekeyboard.themes.fontkeyboard
    product_plan_types:
      "premium_subscription:premium-weekly-auto": WEEKLY
      "YOUR_YEARLY_PRODUCT:YOUR_YEARLY_BASE_PLAN": YEARLY
      "YOUR_LIFETIME_PRODUCT": LIFETIME
```

Mapping này chỉ phục vụ phân loại báo cáo, không thay đổi mua hàng hoặc xác minh đơn. Thay các ID YOUR_... bằng ID thật; giữ các cấu hình khác đang dùng.

**Cách đọc số liệu**

- Transactions/Country_Analysis/Product_Analysis vẫn chỉ chứa đơn đã xác minh. Dashboard có thêm đếm sự kiện sandbox riêng để kiểm tra luồng webhook; không cộng sandbox vào số tiền.
- Diagnostics có dòng tổng `Order Month UTC = ALL`, dòng từng tháng và `Plan Type = ALL`/từng loại gói. Các mức này chồng nhau: lọc App, Currency, tháng và loại gói trước khi SUM hoặc vẽ biểu đồ. Số tiền không có tổng đa tiền tệ.
- Phân tích tháng dựa trên tháng tạo đơn UTC và trạng thái hiện tại; không phải lịch sử dòng tiền hoặc báo cáo quyết toán. Ngày local trong Transactions dùng TZ, mặc định Asia/Bangkok (UTC+7).
- Charged Amount chỉ cộng đơn PROCESSED; Developer Revenue chỉ cộng PROCESSED/PARTIALLY_REFUNDED có giá trị Google cung cấp. Tiền thiếu để trống ở giao dịch; tổng được tính từ giá trị đã biết và có cột số đơn có dữ liệu. Tiền trung bình chia cho số đơn processed có giá trị, không coi tiền thiếu là 0.
- PROCESSED có thể có số tiền 0: xem riêng Processed Positive Amount Orders, Processed Zero Amount Orders và Free Trial Phase Orders. Trial chỉ đếm khi Google có pricing phase tương ứng.
- Số đơn và số sự kiện không phải số người đăng ký duy nhất. Subscription canceled là sự kiện vòng đời; không tự đổi trạng thái đơn đã thanh toán thành CANCELED.
- Service Period End là snapshot của kỳ được đơn chi trả, không xác nhận thuê bao hiện còn active. Không xuất purchase token, email hoặc raw payload. User ID/custom_user_id/identity_id được xuất để thống kê theo user như phần Users bên dưới.
- Qonversion_Events vẫn chỉ hiển thị 20.000 sự kiện gần nhất; thống kê và liên kết sự kiện của báo cáo lấy toàn bộ sự kiện lưu trong database.

### Users và Description: xem mỗi user đã thanh toán bao nhiêu lần

Sau khi deploy và sync, hệ thống tự tạo **Users** và **Description**. Không cần đổi Variables hoặc tạo database mới. User ID được đọc từ raw webhook đã lưu trước đây; chỉ đơn có liên kết đủ rõ mới được gán cho user.

**Users** có một dòng cho mỗi App + Qonversion User ID + Currency. Để xem một người, lọc App và User ID:

- **Payment Count:** số mã đơn đã xác minh có charged lớn hơn 0, ở trạng thái PROCESSED, REFUNDED, PARTIALLY_REFUNDED hoặc PENDING_REFUND. Mỗi mã đơn chỉ đếm một lần dù có nhiều sự kiện started/renewed/canceled hoặc retry. Trial 0 đồng, đơn pending/canceled và tiền thiếu không được coi là một lần thanh toán.
- **Payment Order Face Amount (includes refunded):** tổng tiền gốc của các đơn trong Payment Count, bao gồm đơn đã hoàn. Đây không phải tiền còn giữ hoặc doanh thu ròng. **Charged Amount (processed)** chỉ cộng đơn PROCESSED; **Developer Revenue** chỉ cộng dữ liệu Google cung cấp cho PROCESSED/PARTIALLY_REFUNDED.
- Có số đơn theo từng trạng thái, số đơn trial/0 đồng, ngày thanh toán đầu/cuối, các gói tuần/năm/lifetime, mã đơn và quốc gia. Số lần thanh toán có thể cộng qua các dòng currency của cùng user; số tiền phải giữ riêng từng currency.
- Các cột webhook ghi rõ **user, all currencies** là tổng sự kiện của user và lặp lại trên mỗi dòng currency. Không cộng các cột này qua nhiều dòng currency. Một sự kiện không tương đương một lần thanh toán.
- **MATCHED:** đúng một user_id trên các webhook không phải sandbox/test của cùng (App, Order ID). **MISSING_USER_ID:** chưa có ID. **CONFLICTING_USERS:** một đơn có nhiều user_id; không tự gán cho bất kỳ user nào. Dòng User ID rỗng là nhóm đơn chưa gán được user, không phải một người thật.
- **NO_VERIFIED_ORDERS:** user mới có webhook, chưa có đơn đã xác minh; số lần thanh toán là 0, số tiền chưa có để trống. Sandbox chỉ xuất hiện trong đếm sự kiện, không được dùng để liên kết user với đơn thật.
- custom_user_id và identity_id hiển thị để đối chiếu, không tự gộp các Qonversion user_id khác nhau. Nếu cần thống kê một tài khoản app qua nhiều ID, cần có quy tắc liên kết đã xác nhận.

Ví dụ: user có một đơn ban đầu, hai mã đơn gia hạn đã thanh toán và một sự kiện hủy thì **Payment Count = 3**, không phải 4. Nếu một trong ba đơn được hoàn tiền toàn bộ, Payment Count vẫn là 3 và Refunded Paid Orders là 1.

**Description** mô tả mọi cột của mọi tab, kể cả Description: tên tab, tên cột, chữ cái vị trí cột, ý nghĩa, nguồn, phạm vi/đơn vị, dữ liệu thiếu và ghi chú. Nội dung tự cập nhật theo schema, có bộ lọc để tìm cột nhanh. Description và Users cũng được ghi lại mỗi lần sync, không dùng làm nơi lưu ghi chú thủ công.

Transactions thêm User ID và User Link Status; Qonversion_Events thêm user_id/custom_user_id/identity_id. Diagnostics giữ số user quan sát, user có đơn, user có thanh toán và số đơn thiếu/xung đột user; Dashboard mới ưu tiên chỉ số kinh doanh theo currency. Báo cáo chỉ phản ánh lịch sử đã lưu và xác minh, không tự nhập đăng ký cũ hoặc khẳng định thuê bao còn active.

### Đọc báo cáo dưới góc nhìn UA/PO

Thứ tự tab mới: **Dashboard → Plan_Comparison → Trial_Cohorts → Users → Country_Analysis → Product_Analysis → Transactions → User_Timeline → Data_Quality → Description → Diagnostics → Sync_Log → Qonversion_Events**. Tiêu đề và hai cột đầu được cố định. Tab ngoài danh sách không bị xóa; các tab báo cáo tiếp tục được ghi lại theo snapshot.

| Tab | Cách dùng |
|---|---|
| Dashboard | Một dòng cho mỗi app/currency, ưu tiên observed payers, số giao dịch có tiền, trial và số tiền. Không cộng số user giữa currencies: một user có thể xuất hiện nhiều dòng. As Of Local là thời điểm tạo snapshot. |
| Plan_Comparison | So sánh gói tuần/năm/lifetime theo plan identifier + offer + country + currency. Phân biệt trial 0 đồng với người đã trả tiền. User mua nhiều gói có thể nằm ở nhiều dòng. |
| Trial_Cohorts | Nhóm kỳ trial theo tuần bắt đầu UTC, gói, offer, quốc gia và currency. Hiển thị trial đủ thời gian quan sát, trial chưa đủ thời gian, conversion đã xác minh và trạng thái chất lượng của rate. |
| User_Timeline | Lọc App/User ID để xem chuỗi ORDER và EVENT theo thời gian. Chỉ ORDER có số tiền; EVENT không phải lần thanh toán mới. Lọc Environment để tách sandbox. |
| Data_Quality | Các vấn đề thiếu user/chuỗi thuê bao/thời gian, mã chưa xác minh, coverage lịch sử và tên offer không khớp số ngày trial Google trả về. |
| Diagnostics | Giữ báo cáo Dashboard dạng Metric/Value cũ, gồm tổng ALL, tháng, loại gói, webhook và sync. Các dòng có phạm vi chồng lấn, không cộng tất cả. |

**Quy tắc đọc chỉ số**

- **Observed Payers** là số user liên kết rõ với ít nhất một đơn charged > 0 ở trạng thái đã thanh toán, gồm cả đơn đã hoàn. Không phải số user active hoặc toàn bộ khách hàng của app.
- **Verified Payment Orders** không đếm trial 0 đồng. Nhiều webhook cho cùng mã đơn vẫn chỉ là một đơn. **Repeat Payment Users (observed)** là user có ít nhất hai đơn thanh toán trong nhóm, không tự coi đổi gói là gia hạn. **Verified Renewal Payment Orders** cần webhook production subscription_renewed khớp đơn có tiền.
- **Original Paid Order Amount (includes refunds)** là tổng tiền gốc trên các đơn đã thanh toán, có cả đơn đã hoàn. **Observed Original Amount per Payer** chỉ dùng tiền của đơn gán rõ user chia cho số observed payers; không phải LTV đầy đủ hoặc dự báo. Charged Amount (processed) và developer revenue giữ quy tắc của báo cáo trước.
- **Trial to Paid 7d Rate** dùng trial đã qua 7 ngày sau servicePeriodEndTime Google. Conversion cần đơn có tiền cùng app + user_id + original_transaction_id + plan, sau trial bắt đầu và không quá 7 ngày sau kết thúc. Nếu có trial tiếp theo trong cùng chuỗi, không gán thanh toán sau trial tiếp theo vào trial trước. Trial chồng lấn, thiếu user/chain/ngày hoặc chưa xác nhận coverage thì rate là N/A.
- Cột conversion đếm **kỳ trial**, không đếm số event. Kỳ trial mới bắt đầu chưa vào mẫu số. Đơn nhiều line item không được đoán thời điểm trial. original_transaction_id dùng nội bộ để ghép chuỗi, không xuất purchase token.
- OFFER_NAME_VS_TRIAL_DURATION chỉ là yêu cầu đối chiếu. Ví dụ tên free-trial-7days nhưng snapshot trial Google dài 3 ngày: không tự đổi offer hoặc kết luận cấu hình sai.
- Số mẫu ít chưa đủ chọn gói thắng. Thay đổi quốc gia, giá/offer và độ dài thời gian quan sát đều cần xét khi so sánh; gói năm và gói tuần chưa thể dùng một số lần thanh toán để suy ra retention tương đương.

**Xác nhận coverage lịch sử để mở rate**

Mặc định không cần đổi Variables; các tab mới vẫn xuất số lượng quan sát và N/A khi chưa đủ lịch sử. Chỉ sau khi đã nhập và đối chiếu đầy đủ sự kiện production, user/chain và đơn đã xác minh từ một ngày nhất định đến hiện tại, thêm vào từng app trong APPS_CONFIG_YAML hoặc config/apps.yaml:

```yaml
analytics_coverage_start_utc: "2026-10-01T00:00:00Z" # Ví dụ; chỉ đặt ngày thực sự đã xác nhận đầy đủ.
```

Không dùng ngày webhook đầu tiên nhận được làm bằng chứng coverage. Cấu hình này là khai báo độ đầy đủ dữ liệu cho phân tích, không tự tải lịch sử và không thay đổi xử lý giao dịch. Những cohort bắt đầu trước coverage vẫn N/A.

**Dữ liệu UA chưa có:** installs, paywall views, checkout, network/campaign/creative, spend và A/B variant chưa có nguồn nhập. Data_Quality ghi rõ các giới hạn; báo cáo không tự tính CAC/ROAS, install-to-trial hoặc active subscribers từ số event. Các chỉ số đó cần pipeline dữ liệu bổ sung, không thể suy ra từ Orders/webhook hiện tại.

## 6. How to inspect data

```bash
docker compose exec iap-analytics python - <<'PY'
import sqlite3
c=sqlite3.connect('/data/iap.sqlite3')
for row in c.execute('select app_key,state,country,currency,count(*) from orders group by 1,2,3,4'):
    print(row)
PY
```

Run tests locally (requires pip dependencies):

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## 7. Production hardening / extensions

- Configure a reverse proxy with HTTPS, authenticated webhooks, body limits, and rate limiting. Current Docker port is bound to `127.0.0.1` intentionally.
- Validate webhook origin according to Qonversion's supported authentication/signature scheme. The shared-header design is secure only if the provider actually sends it or a trusted proxy authenticates before injection.
- Backup SQLite (`data/iap.sqlite3`) every day; protect service-account credentials and webhook secrets.
- Increase sync reliability with per-order retries/backoff, request quotas, partial-error retry queues and Sheets batching for larger data.
- Set a long-term report import and status recheck policy; Qonversion may omit Play ID in certain webhook events and those cannot be verified without a correct join ID.
- Add Google Play monthly Sales/Earnings CSV ingestion for history and actual accounting totals; preserve source line type, UTC/timezone, order ID, currency, buyer country, refunds, taxes and conversion rates. Establish a unique source-row key to avoid double-counting settlement lines.
- Use Google Play real-time developer notifications (RTDN) if prompt subscription lifecycle updates are important. Avoid indefinite subscription status polling as a substitute for RTDN.
- For hundreds of thousands of orders, move raw data from SQLite to PostgreSQL/BigQuery and expose only aggregated tables in Sheets.
- Set alerting if sync log records errors or no new webhook events for an unexpectedly long time.

## 8. Safety & scope

This code reads order data (`orders.get`), does **not** issue refunds, change subscription state or call mutating Play APIs. No Qonversion API key is required for webhook-received events. The scheduler uses one Uvicorn worker; running multiple replicas creates overlapping schedulers, so use an external scheduler/leader election if scaling out.

Validation: 44 local tests pass, including HTTP webhook authentication, event persistence, duplicate responses and manual sync. Live Qonversion delivery and Google Play/Sheets integration still require validation after deployment.
