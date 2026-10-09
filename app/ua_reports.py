"""UA/PO views of observed data. Never fabricate acquisition or active-state metrics."""
import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from app.reports import timestamp, summary, PAID_STATES

BUSINESS_COLUMNS = ['Observed Users', 'Observed Payers', 'Verified Payment Orders',
    'Repeat Payment Users (observed)', 'Verified Renewal Payment Orders', 'Trial Users (observed)',
    'Trial Orders', 'Processed Zero Amount Orders', 'Refunded Payment Orders',
    'Charged Amount (processed)', 'Developer Revenue (processed and partially refunded)',
    'Original Paid Order Amount (includes refunds)', 'Observed Original Amount per Payer',
    'Unattributed Verified Orders', 'Notes']
UA_HEADERS = {
    'Dashboard': ['App', 'Currency', 'As Of Local'] + BUSINESS_COLUMNS,
    'Plan_Comparison': ['App', 'Plan Type', 'Plan Identifier', 'Offer ID', 'Country (buyer)', 'Currency'] + BUSINESS_COLUMNS,
    'Trial_Cohorts': ['App', 'Trial Start Week UTC', 'Plan Type', 'Plan Identifier', 'Offer ID', 'Country (buyer)', 'Currency',
        'Observed Trial Episodes', 'Mature Trial Episodes (7d after end)', 'Immature Trial Episodes',
        'Unknown Trial End Episodes', 'Missing Chain Episodes', 'Verified Conversions within 7d after Trial End',
        'Trial to Paid 7d Rate', 'Conversion Rate Status', 'History Coverage Start UTC', 'Notes'],
    'User_Timeline': ['App', 'User ID', 'Time Local', 'Row Type', 'Action', 'Plan Identifier', 'Order ID',
        'Charged Amount', 'Currency', 'State', 'Environment', 'User Link Status', 'Time UTC', 'Notes'],
    'Data_Quality': ['App', 'Severity', 'Issue', 'Count', 'Details'],
}
UA_MEANINGS = {
    'As Of Local': 'Th?i ?i?m t?o snapshot b?o c?o theo TZ c?u h?nh; kh?ng ph?i ng?y ph?t sinh giao d?ch.',
    'Observed Users': 'Số user_id khác nhau liên kết được với các đơn trong nhóm; không phải toàn bộ user cài app.',
    'Observed Payers': 'Số user_id có ít nhất một đơn xác minh charged > 0, gồm cả đơn đã hoàn; chỉ tính user liên kết rõ.',
    'Verified Payment Orders': 'Số đơn xác minh charged > 0 và trạng thái đã thanh toán, gồm PROCESSED/REFUNDED/PARTIALLY_REFUNDED/PENDING_REFUND.',
    'Repeat Payment Users (observed)': 'Số user có ít nhất hai mã đơn thanh toán trong nhóm; không tự coi mua gói khác là gia hạn.',
    'Verified Renewal Payment Orders': 'Số đơn thanh toán có webhook subscription_renewed production khớp mã đơn; sự kiện đơn giá 0 không tính.',
    'Trial Users (observed)': 'Số user_id liên kết rõ có đơn trial theo pricing phase Google trong nhóm.',
    'Trial Orders': 'Số đơn có pricing phase free trial từ Google; không suy ra từ tên offer hoặc giá 0.',
    'Refunded Payment Orders': 'Số đơn đã thanh toán charged > 0 có trạng thái REFUNDED.',
    'Original Paid Order Amount (includes refunds)': 'Tổng charged gốc của các đơn thanh toán, gồm đơn đã hoàn; không phải tiền giữ lại hoặc quyết toán.',
    'Observed Original Amount per Payer': 'Tổng charged gốc của đơn thanh toán liên kết rõ user chia số observed payers; không phải LTV đầy đủ hoặc dự báo.',
    'Unattributed Verified Orders': 'Số đơn chưa gán được user duy nhất, không tính vào số user/payers.',
    'Trial Start Week UTC': 'Tuần ISO theo servicePeriodStartTime trial Google, ví dụ 2026-W41.',
    'Observed Trial Episodes': 'Số kỳ trial đã xác minh. Đơn trial nhiều line item hoặc thiếu ngày được đánh dấu thiếu dữ liệu, không đoán.',
    'Mature Trial Episodes (7d after end)': 'Kỳ trial có thời điểm kết thúc và đã qua thêm 7 ngày để quan sát chuyển đổi.',
    'Immature Trial Episodes': 'Kỳ trial chưa qua hết cửa sổ quan sát 7 ngày sau kết thúc, không vào mẫu số rate.',
    'Unknown Trial End Episodes': 'Kỳ trial thiếu/bất thường thời gian kết thúc; không vào mẫu số rate.',
    'Missing Chain Episodes': 'Kỳ trial thiếu user rõ ràng hoặc original_transaction_id duy nhất; không ghép conversion theo user đơn thuần.',
    'Verified Conversions within 7d after Trial End': 'Kỳ trial trưởng thành có đơn charged > 0 cùng app/user/original_transaction_id/plan, từ lúc bắt đầu đến 7 ngày sau kết thúc và trước trial tiếp theo.',
    'Trial to Paid 7d Rate': 'Converted/mature trial episodes. N/A nếu thiếu coverage đã xác nhận, liên kết chuỗi, ngày hoặc có chain trial chồng lấn.',
    'Conversion Rate Status': 'Giải thích N/A hoặc AVAILABLE. Chỉ mở rate khi analytics_coverage_start_utc bao phủ trial cohort và các kỳ trial có link/ngày đủ rõ.',
    'History Coverage Start UTC': 'Ngày bắt đầu lịch sử đầy đủ do người vận hành xác nhận qua analytics_coverage_start_utc; không tự lấy ngày webhook đầu tiên làm coverage.',
    'Time Local': 'Thời điểm sự kiện/đơn chuyển sang TZ cấu hình, mặc định UTC+7.',
    'Row Type': 'ORDER là đơn Google; EVENT là webhook. Chỉ ORDER có số tiền, không SUM các event như lần thanh toán.',
    'Action': 'Loại đơn trial/thanh toán hoặc tên sự kiện vòng đời. Latest event không xác nhận trạng thái thuê bao hiện tại.',
    'Time UTC': 'Thời điểm tạo đơn hoặc event_time của webhook, theo UTC. Rỗng khi thiếu thời gian nguồn.',
    'Severity': 'INFO/WARNING cho chất lượng dữ liệu; không phải đánh giá gói tốt/xấu.',
    'Issue': 'Mã vấn đề chất lượng hoặc dữ liệu cần bổ sung để phân tích.',
    'Count': 'Số bản ghi trong phạm vi vấn đề; rỗng khi chưa có dữ liệu đo.',
}


def paid(order):
    return order['state'] in PAID_STATES and order.get('charged') not in ('', None) and Decimal(order['charged']) > 0


def trial(details):
    return 'freeTrialDetails' in details['phase'] or 'FREE_TRIAL' in details['phase']


def plan_matches(a, b):
    return a['identifier'] == b['identifier'] and a['plan'] == b['plan']


def business_stats(rows, events_by_order, links):
    s = summary(rows)
    payments = [o for o, _ in rows if paid(o)]
    users = defaultdict(list)
    trial_users = set()
    for o, d in rows:
        user, status = links[(o['app_key'], o['order_id'])]
        if status == 'MATCHED':
            if paid(o):
                users[user].append(o)
            if trial(d):
                trial_users.add(user)
    attributed_money = sum((Decimal(o['charged']) for os in users.values() for o in os), Decimal(0))
    renewal = sum(any(e.get('event_name') == 'subscription_renewed' and e.get('environment', '').lower() == 'production'
        for e in events_by_order[(o['app_key'], o['order_id'])]) for o in payments)
    observed = {links[(o['app_key'], o['order_id'])][0] for o, _ in rows if links[(o['app_key'], o['order_id'])][1] == 'MATCHED'}
    note = 'Observed records only; not full population. Payment counts include refunded orders. No active subscriber, CAC or ROAS claims.'
    if len(users) < 30:
        note += ' Fewer than 30 observed payers; counts alone do not establish a winning plan.'
    return [len(observed), len(users), len(payments), sum(len(os) >= 2 for os in users.values()), renewal,
        len(trial_users), s['trials'], s['zero'], sum(o['state'] == 'REFUNDED' for o in payments),
        s['charged'] if s['amount_known'] else '', s['revenue'] if s['revenue_known'] else '',
        float(sum((Decimal(o['charged']) for o in payments), Decimal(0))) if payments else '',
        float(attributed_money / len(users)) if users else '',
        sum(links[(o['app_key'], o['order_id'])][1] != 'MATCHED' for o, _ in rows), note]


def build_ua_reports(enriched, events, links, apps, now, report_tz):
    now_dt = timestamp(now)
    ev_by_order = defaultdict(list)
    for e in events:
        if (e.get('environment') or '').lower() not in ('sandbox', 'test') and e.get('order_id'):
            ev_by_order[(e['app_key'], e['order_id'])].append(e)
    roots = {}
    for o, _ in enriched:
        key = (o['app_key'], o['order_id'])
        user, status = links[key]
        candidates = {str(e['original_transaction_id']) for e in ev_by_order[key]
            if e.get('original_transaction_id') and (e.get('environment') or '').lower() == 'production'
            and status == 'MATCHED' and str(e.get('user_id') or '') == user}
        roots[key] = next(iter(candidates)) if len(candidates) == 1 else ''
    dashboard, comparisons = defaultdict(list), defaultdict(list)
    timeline, quality = [], []
    paid_chains = defaultdict(list)
    episodes, trial_chains = [], defaultdict(list)
    for o, d in enriched:
        key = (o['app_key'], o['order_id'])
        user, status = links[key]
        dashboard[(o['app_key'], o.get('currency') or 'UNKNOWN')].append((o, d))
        comparisons[(o['app_key'], d['plan'], d['identifier'], d['offer'], o.get('country') or 'UNKNOWN', o.get('currency') or 'UNKNOWN')].append((o, d))
        dt = timestamp(o.get('order_date'))
        action = 'TRIAL_ORDER' if trial(d) else 'PAYMENT_ORDER' if paid(o) else 'OTHER_ORDER'
        timeline.append([o['app_key'], user, dt.astimezone(ZoneInfo(report_tz)).isoformat() if dt else '', 'ORDER',
            action, d['identifier'], o['order_id'], float(Decimal(o['charged'])) if o.get('charged') not in ('', None) else '',
            o.get('currency', ''), o['state'], 'VERIFIED_ORDER', status, dt.isoformat() if dt else '',
            'Current order snapshot; refunded payment remains a historical payment; not current subscription status.'])
        chain = (o['app_key'], user, roots[key])
        if paid(o) and user and roots[key] and dt:
            paid_chains[chain].append((dt, d))
        if trial(d):
            items = d['payload'].get('lineItems') or []
            sub = (items[0].get('subscriptionDetails') or {}) if len(items) == 1 else {}
            start = timestamp(sub.get('servicePeriodStartTime'))
            end = timestamp(sub.get('servicePeriodEndTime'))
            valid_time = bool(start and end and end > start)
            episode = dict(order=o, details=d, chain=chain, start=start, end=end, time_valid=valid_time,
                linked=bool(user and roots[key]), overlap=False)
            episodes.append(episode)
            if start and user and roots[key]:
                trial_chains[chain].append(episode)
            named = re.search(r'(\d+)[-_]?days?\b', d['offer'], re.I)
            if valid_time and named and abs((end - start).total_seconds() / 86400 - int(named.group(1))) > 0.05:
                quality.append([o['app_key'], 'WARNING', 'OFFER_NAME_VS_TRIAL_DURATION', 1,
                    'Order ' + o['order_id'] + ': offer=' + d['offer'] + '; Google trial snapshot=' + str(round((end-start).total_seconds()/86400, 2)) + ' days. Inspect catalog; name alone is not duration.'])
    for chain, eps in trial_chains.items():
        eps.sort(key=lambda e: e['start'])
        for index, ep in enumerate(eps):
            ep['next_start'] = eps[index + 1]['start'] if index + 1 < len(eps) else None
            if ep['next_start'] and ep['end'] and ep['next_start'] < ep['end']:
                ep['overlap'] = True
                eps[index + 1]['overlap'] = True
    grouped_cohorts = defaultdict(list)
    app_settings = {a['key']: a for a in apps}
    for ep in episodes:
        o, d = ep['order'], ep['details']
        week = ep['start'].strftime('%G-W%V') if ep['start'] else 'UNKNOWN'
        grouped_cohorts[(o['app_key'], week, d['plan'], d['identifier'], d['offer'], o.get('country') or 'UNKNOWN', o.get('currency') or 'UNKNOWN')].append(ep)
    cohorts = []
    for key, eps in sorted(grouped_cohorts.items()):
        mature = [e for e in eps if e['time_valid'] and now_dt >= e['end'] + timedelta(days=7)]
        immature = sum(e['time_valid'] and now_dt < e['end'] + timedelta(days=7) for e in eps)
        unknown_end = sum(not e['time_valid'] for e in eps)
        missing = sum(not e['linked'] for e in eps)
        converted = 0
        for ep in mature:
            if ep['linked'] and not ep['overlap']:
                deadline = ep['end'] + timedelta(days=7)
                if any(ep['start'] <= dt <= deadline and (not ep.get('next_start') or dt < ep['next_start'])
                    and plan_matches(ep['details'], pd) for dt, pd in paid_chains[ep['chain']]):
                    converted += 1
        coverage_value = app_settings[key[0]].get('analytics_coverage_start_utc') or ''
        coverage = timestamp(coverage_value)
        status = 'AVAILABLE'
        if not mature:
            status = 'NO_MATURE_TRIALS'
        elif unknown_end or missing or any(e['overlap'] for e in eps):
            status = 'INCOMPLETE_TRIAL_LINK_OR_TIMES'
        elif not coverage or any(e['start'] < coverage for e in eps):
            status = 'HISTORY_COVERAGE_NOT_CONFIRMED'
        rate = converted / len(mature) if status == 'AVAILABLE' else 'N/A'
        cohorts.append([*key, len(eps), len(mature), immature, unknown_end, missing, converted, rate, status, coverage_value,
            'Trial episodes, not event counts. Conversion window ends 7 days after Google trial end; exact user/chain/plan match. Operator must confirm complete verified history before enabling rates.'])
    for e in events:
        dt = timestamp(e.get('event_time'))
        key = (e['app_key'], e.get('order_id') or '')
        timeline.append([e['app_key'], e.get('user_id') or '', dt.astimezone(ZoneInfo(report_tz)).isoformat() if dt else '',
            'EVENT', e.get('event_name') or '', e.get('product_id') or '', e.get('order_id') or '', '', '', '',
            e.get('environment') or 'UNKNOWN', links.get(key, ('', 'NO_VERIFIED_ORDERS'))[1], dt.isoformat() if dt else '',
            'Lifecycle event, not an additional payment. Sandbox/test never contribute to payment or conversion metrics.'])
    timeline.sort(key=lambda r: (r[0], r[1], r[12], r[3], r[6]))
    for app in apps:
        if not any(key[0] == app['key'] for key in dashboard):
            dashboard[(app['key'], '')] = []
        app_orders = [o for o, _ in enriched if o['app_key'] == app['key']]
        app_events = [e for e in events if e['app_key'] == app['key']]
        observed_ids = {e['order_id'] for e in app_events if (e.get('environment') or '').lower() not in ('sandbox', 'test') and e.get('order_id')}
        known = {o['order_id'] for o in app_orders}
        for issue, count, details in [
            ('ORDERS_MISSING_USER', sum(links[(app['key'], o['order_id'])][1] == 'MISSING_USER_ID' for o in app_orders), 'Excluded from user/payer counts; inspect event history.'),
            ('ORDERS_CONFLICTING_USERS', sum(links[(app['key'], o['order_id'])][1] == 'CONFLICTING_USERS' for o in app_orders), 'No automatic transfer or merge between identities.'),
            ('UNVERIFIED_OBSERVED_IDS', len(observed_ids-known), 'Observed non-sandbox IDs without a verified order; may include non-GPA IDs.'),
            ('TRIALS_MISSING_USER_OR_CHAIN', sum(not ep['linked'] for ep in episodes if ep['order']['app_key'] == app['key']), 'Need one production user_id and original_transaction_id for exact conversion matching.'),
            ('TRIALS_INVALID_SERVICE_TIMES', sum(not ep['time_valid'] for ep in episodes if ep['order']['app_key'] == app['key']), 'Google trial service period missing, invalid or multi-line; do not infer from offer name.'),
            ('UNKNOWN_ENVIRONMENT_EVENTS', sum((e.get('environment') or '').lower() not in ('production', 'sandbox', 'test') for e in app_events), 'Unknown environment cannot establish production conversion chains.'),
            ('ORDERS_MISSING_CURRENCY', sum(not o.get('currency') for o in app_orders), 'Amounts with unknown currency cannot be compared across markets.'),
            ('HISTORY_COVERAGE_NOT_CONFIRMED', int(not timestamp(app.get('analytics_coverage_start_utc'))), 'Confirm analytics_coverage_start_utc only after complete historical events and orders for the interval are imported.'),
            ('ACQUISITION_DATA_UNAVAILABLE', '', 'No installs, attribution or spend supplied. CAC/ROAS/install-to-trial/paywall conversion are unavailable.'),
            ('ACTIVE_SUBSCRIPTION_STATE_UNAVAILABLE', '', 'Orders and lifecycle events alone are not a live active-subscriber lookup.'),
        ]:
            quality.append([app['key'], 'WARNING' if count or count == '' else 'INFO', issue, count, details])
    return {'Dashboard': [[*key, now_dt.astimezone(ZoneInfo(report_tz)).isoformat(), *business_stats(rows, ev_by_order, links)] for key, rows in sorted(dashboard.items())],
        'Plan_Comparison': [[*key, *business_stats(rows, ev_by_order, links)] for key, rows in sorted(comparisons.items())],
        'Trial_Cohorts': cohorts, 'User_Timeline': timeline, 'Data_Quality': quality}