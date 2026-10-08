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
4. Endpoint yêu cầu header `X-Webhook-Token` khớp `WEBHOOK_TOKEN` đã đặt trong Railway Variables, dài ít nhất 24 ký tự. Kiểm tra Qonversion có hỗ trợ header này; nếu không, cần proxy xác thực webhook rồi chèn header và dùng URL HTTPS của proxy làm destination.
5. Lưu cấu hình, bật tích hợp và gửi test webhook. Kiểm tra phản hồi cùng Railway logs; xác minh App ID trong payload khớp `qonversion_app_id`.
6. Kiểm tra một giao dịch production thật để xác nhận Google Play Order ID được nhận và xác minh thành công.

Có thể chạy lại test PowerShell ở bước 2 với URL Railway để kiểm tra endpoint riêng. Đợi phút SYNC_MINUTE tiếp theo, kiểm tra logs và các tab Sheets. /health thành công chưa xác nhận quyền Google hoặc sync thành công.

Có thể chạy unittest qua Railway SSH trong container đang chạy. `railway run` chạy trên máy local, không tự truy cập volume remote. Tránh chạy process sync riêng đồng thời với scheduler: khóa sync chỉ bảo vệ trong cùng process.

### Sync ngay bằng nút bấm

Sau khi deploy phiên bản có tính năng này, mở trang gốc `https://<RAILWAY_DOMAIN>/` (local: `http://127.0.0.1:8000/`), nhập WEBHOOK_TOKEN của deployment và bấm **Sync ngay**.

Trang gọi POST /admin/sync với header X-Webhook-Token. Token không được nhúng vào trang hoặc lưu vào browser storage. Chỉ chia sẻ token cho người được phép chạy sync.

Chờ kết quả hoàn tất trước khi đóng trang. Nếu đã có lần sync đang chạy, trang báo chờ; nếu mất kết nối/timeout, kiểm tra logs trước khi thử lại vì lần sync có thể vẫn chạy. Lịch sync mỗi giờ tiếp tục như cũ, dùng cùng khóa với sync thủ công. Sync chỉ kiểm tra Order ID đã nhận, không tự nhập đơn lịch sử.

Để cập nhật Railway, push source mới lên repo/branch đã kết nối rồi deploy; chờ healthcheck thành công trước khi mở trang. Cập nhật local bằng docker compose up -d --build.


### 4. Xử lý lỗi

| Hiện tượng | Kiểm tra |
|---|---|
| Webhook 401 | Header thiếu/sai hoặc token dưới 24 ký tự |
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

> **Webhook compatibility:** The endpoint expects an `X-Webhook-Token` header. Confirm that your Qonversion webhook configuration can send a custom header. If it cannot, use a protected webhook ingress/proxy that injects the header after authenticating the sender, or adapt the receiver after checking Qonversion's exact webhook security mechanism. Do **not** expose the endpoint without verification or put secrets in public source code.

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
4. Set and verify webhook authentication. This template checks `X-Webhook-Token` against `WEBHOOK_TOKEN`. Configure that header in the provider if supported, or authenticate upstream in your reverse proxy and inject it.
5. Send a test webhook and inspect `docker compose logs -f`. Real payload shapes/transaction ID availability vary; test the Google Play Order ID mapping with one **real, non-sandbox transaction**.
6. Keep the project ID (Qonversion `app_id`) in `config/apps.yaml` to reject obvious cross-app routing mistakes if present in payload.

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
| `Dashboard` | Global counts and export time; deliberately avoids misleading summed multicurrency revenue. |
| `Qonversion_Events` | Qonversion lifecycle event log and separately labeled IP country; excludes raw PII-rich JSON. |
| `Sync_Log` | Sync successes/errors for diagnosis. |

For a country bar chart in Sheets: Insert → Chart; use `Country_Analysis` and filter to one app plus one currency; X axis = Country, Y axis = `Charged Amount (processed)` or developer revenue. Avoid mixing currencies in one bar chart.

**Important accounting limitations:** `Charged Amount (processed)` is a current-state gross proxy (including tax), not settlement revenue, does not subtract partial refunds and excludes fully refunded orders. `Developer Revenue` applies only where Play provides that field and is not a substitute for Play earnings reports. Partial refunds are tracked separately; do not treat order `total` as cash recognized across a period. Aggregation of current order snapshots by create date is **not** a proper historical cashflow or month-end settlement report.

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

Note: The source package is syntax-checked, but this environment could not install external Python dependencies or exercise live third-party APIs. Run tests inside your built container with `docker compose exec iap-analytics python -m unittest discover -s tests -v` before production use.

