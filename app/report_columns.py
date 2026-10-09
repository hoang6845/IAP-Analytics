"""Column dictionary exported with each Sheets snapshot."""
DESCRIPTION_HEADERS = ['Tab', 'Column', 'Column Letter', 'Meaning', 'Source', 'Unit / Scope', 'Missing Values', 'Notes']
MEANINGS = {
    'App': 'Key của ứng dụng trong cấu hình; cùng user ID ở app khác được thống kê riêng.',
    'Order ID': 'Mã đơn Google Play; mỗi (App, Order ID) là một giao dịch duy nhất.',
    'Date UTC': 'Thời điểm tạo đơn do Google Play trả về, theo UTC.',
    'Country (buyer)': 'Quốc gia người mua do Google Play cung cấp; không thay bằng quốc gia IP.',
    'Product': 'Store product ID; đơn nhiều sản phẩm giữ danh sách nối bằng dấu chấm phẩy.',
    'State': 'Trạng thái hiện tại của đơn thanh toán, không phải trạng thái active của thuê bao.',
    'Currency': 'Đơn vị tiền gốc. Không cộng số tiền của các currency khác nhau.',
    'Charged Amount': 'Tổng tiền trên đơn Google, gồm thuế; không tự trừ tiền hoàn một phần.',
    'Developer Revenue': 'Tiền developer theo currency người mua, chỉ khi Google cung cấp.',
    'Google Verified': 'YES: đơn được lấy thành công từ Google Play; không có nghĩa thuê bao còn active.',
    'Qonversion Events': 'Số sự kiện không phải sandbox/test liên kết với đúng App và Order ID, lấy toàn bộ database.',
    'Plan Type': 'WEEKLY/tuần, MONTHLY/tháng, YEARLY/năm, LIFETIME/trọn đời, UNKNOWN/chưa rõ, MIXED/nhiều loại trong một đơn.',
    'Plan Identifier': 'Product ID kèm base plan nếu có; dùng để tách các gói của cùng sản phẩm.',
    'Plan Type Source': 'Configured product_plan_types: khai báo rõ; Inferred from ID naming: suy luận tên; Insufficient or ambiguous ID: chưa rõ.',
    'Purchase Kind': 'SUBSCRIPTION, ONE_TIME, PAID_APP hoặc UNKNOWN từ chi tiết Google; mua một lần chưa đồng nghĩa lifetime.',
    'Base Plan ID': 'Mã base plan Google; có thể bổ sung từ webhook cùng đơn và cùng product nếu không xung đột.',
    'Offer ID': 'Mã ưu đãi Google trả về cho gói của đơn.',
    'Product Title': 'Tên sản phẩm Google trả về theo ngôn ngữ người mua.',
    'Pricing Phase': 'Giai đoạn giá Google: freeTrialDetails, introductoryPriceDetails, baseDetails, prorationPeriodDetails hoặc enum cũ.',
    'Service Period Start UTC (snapshot)': 'Bắt đầu kỳ dịch vụ được đơn này chi trả, snapshot từ Google.',
    'Service Period End UTC (snapshot)': 'Kết thúc kỳ dịch vụ được đơn này chi trả; không xác nhận hạn hiện tại hoặc active.',
    'Order Month UTC': 'Tháng tạo đơn theo UTC, dạng YYYY-MM. Dashboard ALL là tổng mọi tháng.',
    'Order Date Local': 'Ngày tạo đơn chuyển sang TZ cấu hình, mặc định Asia/Bangkok UTC+7.',
    'Last Checked UTC': 'Lần gần nhất hệ thống xác minh/cập nhật đơn Google thành công.',
    'Last Google Event UTC': 'Thời gian thay đổi đơn gần nhất do Google trả về.',
    'Tax (order currency)': 'Thuế của đơn; chỉ hiển thị khi currency thuế khớp currency đơn.',
    'Latest Qonversion Event': 'Tên sự kiện không phải sandbox/test gần nhất của cùng mã đơn; không suy ra active.',
    'Latest Qonversion Event UTC': 'Thời điểm sự kiện Qonversion gần nhất liên kết với đơn.',
    'Qonversion Country (IP)': 'Quốc gia suy ra từ IP trong webhook, tách riêng khỏi quốc gia người mua Google.',
    'Total Orders': 'Tổng số đơn đã xác minh trong nhóm, gồm tất cả trạng thái.',
    'Other State Orders': 'Đơn có trạng thái ngoài PROCESSED/PENDING/CANCELED/REFUNDED/PARTIALLY_REFUNDED/PENDING_REFUND.',
    'Charged Amount (processed)': 'Cộng charged của đơn PROCESSED có giá trị; không cộng đơn đã hoàn hoặc chờ hoàn.',
    'Developer Revenue (processed and partially refunded)': 'Cộng developer revenue có dữ liệu của đơn PROCESSED và PARTIALLY_REFUNDED.',
    'Average Charged (processed, known amounts)': 'Charged Amount (processed) chia số đơn PROCESSED có charged; bỏ qua giá trị thiếu.',
    'Processed Amount Known Orders': 'Số đơn PROCESSED có giá trị charged, kể cả giá trị 0.',
    'Developer Revenue Known Orders': 'Số đơn PROCESSED/PARTIALLY_REFUNDED có developer revenue, kể cả giá trị 0.',
    'First Order UTC': 'Ngày tạo đơn đầu tiên trong nhóm đơn đã xác minh.',
    'Last Order UTC': 'Ngày tạo đơn cuối cùng trong nhóm đơn đã xác minh.',
    'Processed Positive Amount Orders': 'Đơn PROCESSED có charged lớn hơn 0.',
    'Processed Zero Amount Orders': 'Đơn PROCESSED có charged bằng 0; không coi charged thiếu là 0.',
    'Free Trial Phase Orders': 'Đơn có pricing phase Google là free trial; không suy ra trial từ giá 0.',
    'Plan Variants': 'Số mã plan khác nhau trong nhóm; Dashboard phân biệt thêm App.',
    'Buyer Countries': 'Country/Product Analysis: số quốc gia khác nhau. Users: danh sách quốc gia người mua đã biết.',
    'Metric': 'Tên chỉ số Dashboard; đọc cùng App, Currency, tháng và Plan Type để biết phạm vi.',
    'Value': 'Giá trị chỉ số: có thể là số đếm, số tiền, ngày giờ hoặc nội dung; đơn vị tùy Metric.',
    'Notes': 'Ghi chú phạm vi, nguồn suy luận và giới hạn của dòng báo cáo.',
    'Last Run UTC': 'Thời điểm ghi bản ghi sync theo UTC.',
    'Result': 'OK_PLAY: bước xác minh hoàn tất; ERROR: lần sync có lỗi. Không tự chứng minh đã có đơn hoặc export thành công.',
    'Details': 'Thông tin bước sync hoặc lỗi để chẩn đoán; Sheet có thể chậm hơn logs nếu export lỗi.',
    'Event Time UTC': 'Thời gian sự kiện time/created_at của Qonversion, chuẩn hóa số timestamp sang UTC.',
    'Event': 'Tên sự kiện vòng đời Qonversion, không tương đương một lần thanh toán.',
    'Environment': 'Môi trường từ webhook: production, sandbox hoặc test; rỗng là chưa biết.',
    'Event Key': 'SHA-256 của payload canonical, dùng giữ một bản cho payload retry giống hệt.',
    'User ID': 'Qonversion user_id. Liên kết theo (App, Order ID); không gộp các Qonversion user_id khác nhau.',
    'Custom User IDs': 'custom_user_id của webhook. Users: danh sách giá trị đã quan sát của user; Qonversion_Events: giá trị của sự kiện.',
    'Identity IDs': 'identity_id của webhook. Chỉ dùng đối chiếu, không tự gộp user khác nhau theo identity.',
    'User Link Status': 'MATCHED: đúng một user_id không phải sandbox/test. MISSING_USER_ID: chưa có ID. CONFLICTING_USERS: nhiều ID trên cùng đơn. NO_VERIFIED_ORDERS: user mới có webhook.',
    'Payment Count': 'Số Order ID đã xác minh có charged > 0 và trạng thái PROCESSED/REFUNDED/PARTIALLY_REFUNDED/PENDING_REFUND. Một đơn đếm một lần, gồm đơn đã hoàn.',
    'Total Verified Orders': 'Tổng đơn đã xác minh thuộc nhóm user và currency, gồm cả trial và mọi trạng thái.',
    'Payment Order Face Amount (includes refunded)': 'Tổng charged gốc của các đơn trong Payment Count; có cả đơn đã hoàn, không phải số tiền còn giữ hoặc doanh thu ròng.',
    'First Payment UTC': 'Ngày tạo đơn thanh toán có charged > 0 đầu tiên trong nhóm.',
    'Last Payment UTC': 'Ngày tạo đơn thanh toán có charged > 0 cuối cùng trong nhóm.',
    'Plan Types': 'Danh sách loại gói trong các đơn đã xác minh của user/currency.',
    'Plan Identifiers': 'Danh sách product:base-plan trong các đơn đã xác minh của user/currency.',
    'Verified Order IDs': 'Danh sách các mã đơn đã xác minh thuộc user/currency, mỗi đơn một lần.',
    'Production Events (user, all currencies)': 'Số sự kiện production của user trên toàn bộ currency; lặp lại trên từng dòng currency của user.',
    'Sandbox/Test Events (user, all currencies)': 'Số sự kiện sandbox/test của user; không tính vào thanh toán. Lặp lại trên từng dòng currency.',
    'Unknown Environment Events (user, all currencies)': 'Số sự kiện có environment ngoài production/sandbox/test hoặc rỗng. Lặp lại trên từng dòng currency.',
    'Non-Sandbox IDs Without Verified Order (user, all currencies)': 'Số mã đơn khác nhau từ webhook không phải sandbox/test của user nhưng chưa có đơn đã xác minh; gồm mã không phải GPA, không chứng minh lỗi Google.',
    'First Webhook Received UTC': 'Thời gian server nhận webhook đầu tiên của user, toàn bộ currency và môi trường.',
    'Last Webhook Received UTC': 'Thời gian server nhận webhook cuối cùng của user, toàn bộ currency và môi trường.',
    'Tab': 'Tên tab được mô tả; bao gồm cả Description.',
    'Column': 'Tên cột chính xác trong hàng tiêu đề của tab.',
    'Column Letter': 'Vị trí cột kiểu Google Sheets: A, B, ... AA.',
    'Meaning': 'Ý nghĩa của cột và quy tắc tính.',
    'Source': 'Nguồn dữ liệu hoặc phép tổng hợp tạo ra cột.',
    'Unit / Scope': 'Đơn vị/phạm vi của cột; đối chiếu currency và các chiều của dòng.',
    'Missing Values': 'Cách biểu diễn khi dữ liệu nguồn thiếu hoặc chưa xác minh.',
}
from app.ua_reports import UA_MEANINGS
MEANINGS.update(UA_MEANINGS)

STATE_MEANINGS = {
    'Processed': 'PROCESSED: đơn xử lý thành công, có thể là 0 đồng; chưa chắc là thanh toán có tiền.',
    'Pending': 'PENDING: đơn đang chờ xử lý.',
    'Canceled': 'CANCELED: đơn hủy trước khi xử lý; khác sự kiện subscription_canceled.',
    'Refunded': 'REFUNDED: đơn hoàn tiền toàn bộ.',
    'Partially Refunded': 'PARTIALLY_REFUNDED: đơn hoàn tiền một phần.',
    'Pending Refund': 'PENDING_REFUND: đơn đang chờ hoàn tiền.',
}
for label, meaning in STATE_MEANINGS.items():
    MEANINGS[label + ' Orders'] = 'Số đơn có trạng thái ' + meaning
for label in ('Processed', 'Refunded', 'Partially Refunded', 'Pending Refund'):
    MEANINGS[label + ' Paid Orders'] = 'Số đơn trong Payment Count có trạng thái ' + STATE_MEANINGS[label]
for plan, meaning in {'WEEKLY': 'tuần', 'MONTHLY': 'tháng', 'YEARLY': 'năm', 'LIFETIME': 'trọn đời', 'UNKNOWN': 'chưa phân loại', 'MIXED': 'nhiều loại gói trong một đơn'}.items():
    MEANINGS[plan + ' Orders'] = 'Số đơn được phân loại gói ' + meaning + '; xem Plan Type Source để biết nguồn.'


def column_letter(index):
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def description_rows(headers):
    rows = []
    for tab, columns in headers.items():
        for index, column in enumerate(columns, 1):
            meaning = MEANINGS[column]  # Missing documentation is an error, not a vague placeholder.
            source = 'Google Play Orders API + tổng hợp database'
            if tab == 'Description':
                source = 'Schema và quy tắc báo cáo trong code'
            elif tab == 'Sync_Log':
                source = 'SQLite sync_log'
            elif tab == 'Qonversion_Events' or 'Webhook' in column or 'Events (user' in column or column in ('Qonversion Country (IP)', 'Latest Qonversion Event', 'Latest Qonversion Event UTC', 'Qonversion Events', 'User ID', 'Custom User IDs', 'Identity IDs', 'User Link Status'):
                source = 'Webhook Qonversion lưu trong SQLite + liên kết đơn'
            elif column in ('Plan Type', 'Plan Type Source', 'Plan Identifier', 'Plan Types', 'Plan Identifiers') or column.endswith(' Orders') and column.split(' ', 1)[0] in ('WEEKLY', 'MONTHLY', 'YEARLY', 'LIFETIME', 'UNKNOWN', 'MIXED'):
                source = 'Google product/basePlanId; webhook phù hợp; product_plan_types hoặc suy luận tên ID'
            elif tab in ('Dashboard', 'Diagnostics', 'Plan_Comparison', 'Trial_Cohorts', 'User_Timeline', 'Data_Quality'):
                source = 'Đơn Google, sự kiện Qonversion, cấu hình và sync_log theo Metric'
            scope = 'Một đơn (App, Order ID)' if tab == 'Transactions' else 'Một sự kiện' if tab == 'Qonversion_Events' else 'Một lần ghi sync' if tab == 'Sync_Log' else 'Một cột báo cáo' if tab == 'Description' else 'Phạm vi nhóm trong dòng'
            note = ''
            if tab == 'Users':
                scope = 'App + Qonversion User ID + Currency + trạng thái liên kết'
                note = 'Dòng user rỗng là nhóm đơn chưa gán được user, không phải một người. Số tiền tách theo currency.'
                if 'all currencies' in column or column in ('First Webhook Received UTC', 'Last Webhook Received UTC', 'Custom User IDs', 'Identity IDs'):
                    scope = 'Toàn user trên mọi currency; lặp trên từng dòng currency'
                    note += ' Không SUM cột này qua các dòng currency của cùng user.'
                if column == 'Payment Count' or 'Paid Orders' in column:
                    note += ' Chỉ đếm charged đã biết > 0; tiền thiếu không được đoán. Sự kiện retry/cancel không tạo thêm lần thanh toán.'
            elif tab == 'Country_Analysis':
                scope = 'App + Country (buyer) + Currency'
            elif tab == 'Product_Analysis':
                scope = 'App + Product + Currency + Plan Type + Plan Identifier'
            elif tab == 'Diagnostics':
                scope = 'Metric + App + Currency + Order Month UTC + Plan Type'
                note = 'ALL và từng tháng/loại gói chồng nhau; lọc trước khi SUM. Tiền tháng là snapshot theo tháng tạo đơn, không phải quyết toán.'
            missing = 'Rỗng khi nguồn chưa cung cấp.'
            if column.endswith(' Orders') or column.endswith('Paid Orders') or column in ('Payment Count', 'Total Verified Orders', 'Total Orders', 'Qonversion Events', 'Plan Variants') or 'Known Orders' in column or 'Events (user' in column or column.startswith('Non-Sandbox IDs'):
                missing = '0 khi không có bản ghi đủ điều kiện; không suy ra tiền thiếu là 0.'
            elif column in ('Plan Type', 'Plan Types', 'User Link Status', 'Purchase Kind', 'Order Month UTC'):
                missing = 'UNKNOWN hoặc trạng thái liên kết giải thích dữ liệu thiếu; xem Meaning.'
            elif column == 'Currency':
                missing = 'UNKNOWN khi đơn thiếu currency; rỗng ở Users chỉ có webhook hoặc Dashboard chỉ số không phải tiền.'
            elif column in ('Charged Amount (processed)', 'Developer Revenue (processed and partially refunded)'):
                missing = 'Users: rỗng nếu không có giá trị đã biết. Tab tổng hợp khác: 0 tổng giá trị đã biết; đọc cột Known Orders.'
            if column in ('Observed Users', 'Observed Payers', 'Verified Payment Orders', 'Repeat Payment Users (observed)',
                    'Verified Renewal Payment Orders', 'Trial Users (observed)', 'Trial Orders', 'Refunded Payment Orders',
                    'Unattributed Verified Orders', 'Observed Trial Episodes', 'Mature Trial Episodes (7d after end)',
                    'Immature Trial Episodes', 'Unknown Trial End Episodes', 'Missing Chain Episodes',
                    'Verified Conversions within 7d after Trial End'):
                missing = '0 khi kh?ng c? b?n ghi ?? ?i?u ki?n trong d? li?u quan s?t; kh?ng ch?ng minh to?n b? l?ch s? b?ng 0.'
            if column == 'Trial to Paid 7d Rate':
                missing = 'N/A khi ch?a ?? d? li?u/coverage/th?i gian. Khi AVAILABLE, 0 l? t? l? quan s?t b?ng 0.'
            if 'Amount' in column or 'Revenue' in column or column == 'Tax (order currency)':
                note += ' Tiền theo currency của dòng; không cộng đa tiền tệ. Số Known Orders là số đếm, không phải tiền.'
            rows.append([tab, column, column_letter(index), meaning, source, scope, missing, note.strip()])
    return rows
# Reorder presentation only; report calculations keep their existing canonical schemas.
COLUMN_PRIORITY = {
    'Transactions': ['App', 'User ID', 'Plan Type', 'Plan Identifier', 'Order Date Local',
        'Charged Amount', 'Currency', 'Developer Revenue', 'State', 'Country (buyer)',
        'Product Title', 'Order ID', 'Latest Qonversion Event'],
    'Country_Analysis': ['App', 'Country (buyer)', 'Currency', 'Total Orders',
        'Charged Amount (processed)', 'Developer Revenue (processed and partially refunded)',
        'Average Charged (processed, known amounts)', 'Processed Positive Amount Orders',
        'WEEKLY Orders', 'MONTHLY Orders', 'YEARLY Orders', 'LIFETIME Orders',
        'Processed Orders', 'Refunded Orders', 'Partially Refunded Orders'],
    'Product_Analysis': ['App', 'Plan Type', 'Plan Identifier', 'Product', 'Currency',
        'Total Orders', 'Charged Amount (processed)', 'Developer Revenue (processed and partially refunded)',
        'Average Charged (processed, known amounts)', 'Processed Positive Amount Orders',
        'Processed Orders', 'Refunded Orders', 'Partially Refunded Orders', 'Buyer Countries'],
    'Users': ['App', 'User ID', 'Payment Count', 'Currency',
        'Payment Order Face Amount (includes refunded)', 'Charged Amount (processed)',
        'Developer Revenue (processed and partially refunded)', 'Plan Types', 'Plan Identifiers',
        'First Payment UTC', 'Last Payment UTC', 'Total Verified Orders',
        'Processed Paid Orders', 'Refunded Paid Orders', 'Partially Refunded Paid Orders',
        'Pending Refund Paid Orders', 'Buyer Countries', 'User Link Status'],
    'Dashboard': ['Metric', 'Value', 'App', 'Currency', 'Order Month UTC', 'Plan Type', 'Notes'],
    'Qonversion_Events': ['App', 'User ID', 'Event', 'Product', 'Environment', 'Event Time UTC', 'Order ID'],
    'Sync_Log': ['Last Run UTC', 'Result', 'Details'],
    'Description': ['Tab', 'Column', 'Meaning', 'Source', 'Unit / Scope', 'Missing Values', 'Notes', 'Column Letter'],
}
COLUMN_TAIL = {
    'Transactions': ['Product', 'Date UTC', 'Order Month UTC', 'Purchase Kind', 'Base Plan ID', 'Offer ID',
        'Plan Type Source', 'User Link Status', 'Google Verified', 'Qonversion Events',
        'Qonversion Country (IP)', 'Latest Qonversion Event UTC', 'Last Google Event UTC', 'Last Checked UTC'],
    'Country_Analysis': ['Other State Orders', 'Processed Amount Known Orders',
        'Developer Revenue Known Orders', 'First Order UTC', 'Last Order UTC', 'Last Checked UTC'],
    'Product_Analysis': ['Other State Orders', 'Processed Amount Known Orders',
        'Developer Revenue Known Orders', 'First Order UTC', 'Last Order UTC', 'Last Checked UTC'],
    'Users': ['Processed Amount Known Orders', 'Developer Revenue Known Orders', 'First Order UTC',
        'Last Order UTC', 'Last Checked UTC', 'Production Events (user, all currencies)',
        'Sandbox/Test Events (user, all currencies)', 'Unknown Environment Events (user, all currencies)',
        'Non-Sandbox IDs Without Verified Order (user, all currencies)', 'Custom User IDs', 'Identity IDs',
        'Verified Order IDs', 'First Webhook Received UTC', 'Last Webhook Received UTC', 'Notes'],
    'Qonversion_Events': ['Qonversion Country (IP)', 'Custom User IDs', 'Identity IDs', 'Event Key'],
}


COLUMN_PRIORITY['Diagnostics'] = COLUMN_PRIORITY['Dashboard'][:]
COLUMN_PRIORITY['Dashboard'] = ['App', 'Currency', 'Observed Payers', 'Verified Payment Orders',
    'Trial Users (observed)', 'Trial Orders', 'Charged Amount (processed)',
    'Developer Revenue (processed and partially refunded)', 'Repeat Payment Users (observed)']


def display_headers(headers):
    result = {}
    for tab, columns in headers.items():
        first, last = COLUMN_PRIORITY.get(tab, []), COLUMN_TAIL.get(tab, [])
        if len(set(first + last)) != len(first + last) or any(c not in columns for c in first + last):
            raise ValueError('Invalid column layout for ' + tab)
        result[tab] = first + [c for c in columns if c not in first and c not in last] + last
    return result


def display_rows(rows, source_headers, target_headers):
    positions = [source_headers.index(column) for column in target_headers]
    return [[row[index] for index in positions] for row in rows]