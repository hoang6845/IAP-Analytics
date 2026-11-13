"""Decision-oriented views. Money is verified by Play, attribution by acquisition webhook.

Counts describe observed history, never a live subscription entitlement snapshot.
"""
import json
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.reports import timestamp, numeric
from app.ua_reports import paid, trial, UA_HEADERS

METRICS = ['Trial Users', 'Paying Users', 'ARPPU', 'Mature Trials', 'Converted Trials',
           'Conversion Rate', 'Retry Users', 'Retry Rate', 'Total Revenue',
           'Renewal Revenue', 'Conversion Revenue', 'Other Revenue', 'Missing Revenue Orders']
HEADERS = {
    'Overview': ['App', 'Local Date', 'Currency', 'Observed Subscription Chains',
                 'New Subscriptions', 'Canceled Subscriptions', 'Active Subscriptions'] + METRICS + ['Notes'],
    'RAW_Data': ['App', 'Row Type', 'Time Local', 'User ID', 'Order ID', 'Original Transaction ID',
                 'Country (buyer)', 'Qonversion Country (IP)', 'Plan Type', 'Plan Identifier',
                 'Offer ID', 'Currency', 'Charged Amount', 'Developer Revenue', 'State',
                 'Event', 'Environment', 'Data Type', 'Data ID', 'Data Name', 'Entry Source',
                 'Attribution Status', 'User Link Status'],
    'Country_Performance': ['App', 'Country (buyer)', 'Currency'] + METRICS + ['Notes'],
    'Cohort_Retention': ['App', 'Cohort Month', 'Country (buyer)', 'User ID',
                        'Original Transaction ID', 'Plan Identifier', 'Currency',
                        'Renewal Number', 'Renewal Users', 'Renewal Orders', 'Revenue at Step',
                        'Total Revenue', 'Renewal Revenue', 'Conversion Revenue',
                        'Other Revenue', 'Renewal Number Status', 'Notes'],
    'Package_Performance': ['App', 'Plan Type', 'Plan Identifier', 'Country (buyer)', 'Currency',
                            'Purchase Orders'] + METRICS + ['Notes'],
    'Plan_Upgrades': ['App', 'Country (buyer)', 'Currency', 'From Plan', 'To Plan',
                      'Upgrade Users', 'Upgrade Orders', 'Total Revenue', 'Notes'],
    'Theme_Performance': ['App', 'Data Type', 'Data ID', 'Data Name', 'Entry Source',
                          'Country (buyer)', 'Currency', 'Trial Users', 'Paying Users',
                          'Converted Users', 'Renewal Users', 'Cancel Users', 'Total Revenue',
                          'Renewal Revenue', 'Conversion Revenue', 'Other Revenue', 'Notes'],
    'Screen_Performance': ['App', 'Entry Source', 'Country (buyer)', 'Currency',
                           'Trial Users', 'Paying Users', 'Converted Users', 'Renewal Users',
                           'Cancel Users', 'Total Revenue', 'Renewal Revenue',
                           'Conversion Revenue', 'Other Revenue', 'Notes'],
    'Firebase_Events': ['App', 'Report Start', 'Report End', 'Country (GA4)', 'Data Type',
                         'Data ID', 'Data Name', 'Entry Source', 'Event', 'Event Count',
                         'Event Users', 'Analytics Status', 'Notes'],
}

# Each definition is also exported in Description.
DEFINITIONS = {
    'Local Date': ('Ngày (giờ địa phương)', 'ALL là toàn lịch sử; dòng ngày theo TZ, không cộng ALL với các ngày.'),
    'Observed Subscription Chains': ('Tổng chuỗi thuê bao đã ghi nhận', 'Số (app,user,original_transaction_id) có đơn subscription xác minh; không phải thuê bao active.'),
    'New Subscriptions': ('Thuê bao mới', 'Chuỗi có trial_started/subscription_started production khớp đơn xác minh; đếm một chuỗi một lần theo ngày đơn đầu.'),
    'Canceled Subscriptions': ('Chuỗi hủy gia hạn', 'Chuỗi có trial_canceled/subscription_canceled production theo ngày event; không đồng nghĩa hết Premium.'),
    'Active Subscriptions': ('Thuê bao đang active', 'N/A: cần snapshot entitlement hiện tại; không suy ra từ tổng đơn hay event cuối.'),
    'Trial Users': ('User dùng thử', 'User liên kết rõ có đơn free trial Google; distinct trong phạm vi dòng.'),
    'Paying Users': ('User trả phí', 'User liên kết rõ có đơn charged > 0 thuộc trạng thái đã thanh toán; gồm lịch sử đơn hoàn tiền.'),
    'ARPPU': ('ARPPU (tiền thu thành công/user trả phí)', 'Tiền charged PROCESSED của đơn có user rõ / số payer quan sát; tách currency, không phải doanh thu ròng.'),
    'Mature Trials': ('Trial đã đủ thời gian theo dõi', 'Tổng kỳ trial đã qua 7 ngày sau kết thúc, theo bộ tính Trial_Cohorts.'),
    'Converted Trials': ('Trial chuyển đổi trong cửa sổ 7 ngày', 'Tổng conversion đủ điều kiện từ Trial_Cohorts; không phải mọi event converted.'),
    'Conversion Rate': ('Tỷ lệ trial → trả phí (7 ngày)', 'Converted Trials / Mature Trials; N/A khi bất kỳ cohort thiếu coverage/link/thời gian, hoặc mẫu số 0.'),
    'Retry Users': ('User từng Billing Retry', 'Distinct user có trial_billing_retry/subscription_billing_retry hoặc tên _entered production và gán được nhóm qua chuỗi.'),
    'Retry Rate': ('Tỷ lệ user từng Billing Retry (quan sát)', 'Retry users / user thuê bao quan sát trong nhóm (gồm user có retry); toàn lịch sử, không phải retry attempts / payment attempts.'),
    'Total Revenue': ('Tổng tiền thu thành công', 'Tổng charged của đơn PROCESSED đã biết; không cộng currency, không phải tiền developer sau phí/thuế.'),
    'Renewal Revenue': ('Tiền thu từ renew', 'Charged PROCESSED có subscription_renewed production khớp đúng user/đơn; conflict converted+renewed xếp Other.'),
    'Conversion Revenue': ('Tiền thu từ convert', 'Charged PROCESSED có trial_converted production khớp đúng user/đơn; tách khỏi renew.'),
    'Other Revenue': ('Tiền thu khác/chưa phân loại', 'Tiền thu thành công ngoài convert/renew; Total = Renew + Convert + Other.'),
    'Missing Revenue Orders': ('Đơn thành công thiếu số tiền', 'Đơn PROCESSED không có charged; tổng tiền chỉ bao gồm giá trị đã biết.'),
    'Original Transaction ID': ('ID chuỗi thuê bao', 'original_transaction_id duy nhất từ webhook production đúng user của đơn; thiếu/conflict để trống.'),
    'Data Type': ('Loại nội dung', 'theme/font/effect/DIY/... do app gắn ở lần mua đầu chuỗi.'),
    'Data ID': ('ID nội dung', 'ID ổn định của nội dung premium, không dùng tên event động.'),
    'Data Name': ('Tên nội dung', 'Tên hiển thị tại lúc mở paywall; ID mới là khóa đối chiếu.'),
    'Entry Source': ('Màn/điểm vào paywall', 'onboarding, home_btn_premium, setting..., preview_font_art...; UNKNOWN nếu thiếu snapshot acquisition.'),
    'Attribution Status': ('Tình trạng attribution', 'ACQUISITION_SNAPSHOT: properties của event trial_started/subscription_started/in_app_purchase cùng chuỗi; không dùng properties renew hiện tại.'),
    'Cohort Month': ('Tháng bắt đầu chuỗi (UTC)', 'Tháng acquisition production xác minh; UNKNOWN nếu thiếu. Lọc country/user/ID chuỗi.'),
    'Renewal Number': ('Lần renew', '0 = mua đầu/convert/khác; ưu tiên subscription_renew_count provider; nếu thiếu chỉ đánh số khi lịch sử acquisition đầy đủ theo coverage; còn lại UNKNOWN.'),
    'Renewal Users': ('User renew', 'Distinct user có đơn paid với subscription_renewed production; ở retention là user renew đúng bước.'),
    'Renewal Orders': ('Số đơn renew', 'Số order paid duy nhất có event renew; retry event không tăng số đơn.'),
    'Revenue at Step': ('Tiền thu ở lần này', 'Charged PROCESSED tại bước; có thể SUM các bước trong cùng chuỗi/currency.'),
    'Renewal Number Status': ('Độ đầy đủ số thứ tự renew', 'PROVIDER_COUNTER khi có bộ đếm provider; AVAILABLE khi coverage/lịch sử acquisition đủ; còn lại UNKNOWN_HISTORY.'),
    'Purchase Orders': ('Lượt mua có trả tiền', 'Số đơn paid charged > 0, gồm lịch sử refund; sort giảm dần để xem gói mua nhiều.'),
    'From Plan': ('Gói cũ', 'Gói đã xác minh trước đó trong cùng chuỗi, chỉ khi webhook subscription_upgraded xác nhận thay đổi.'),
    'To Plan': ('Gói mới', 'Plan của đơn paid có subscription_upgraded; không suy ra upgrade chỉ vì user mua nhiều gói.'),
    'Upgrade Users': ('User upgrade xác nhận', 'Distinct user có subscription_upgraded và xác định được gói cũ/mới; phần thiếu được báo Data_Quality.'),
    'Upgrade Orders': ('Lượt upgrade xác nhận', 'Distinct order ID đủ bằng chứng upgrade; pending/deferred không phải một lượt paid upgrade.'),
    'Converted Users': ('User convert xác nhận', 'Distinct user có paid order với trial_converted production; khác cửa sổ conversion rate 7 ngày.'),
    'Cancel Users': ('User hủy gia hạn', 'Distinct user có cancel production gắn đúng chuỗi; không phải đóng paywall hay hết quyền truy cập.'),
    'Report Start': ('Từ ngày (GA4)', 'Ngày đầu báo cáo theo timezone của GA4 property.'),
    'Report End': ('Đến ngày (GA4)', 'Ngày cuối báo cáo GA4, mặc định yesterday; không cộng các cửa sổ chồng nhau.'),
    'Country (GA4)': ('Quốc gia (GA4)', 'Quốc gia GA4; tách riêng với buyer country của Google Play.'),
    'Event Count': ('Số event Firebase', 'eventCount từ GA4 Data API; không phải số người hay số đơn.'),
    'Event Users': ('User phát sinh event (GA4)', 'totalUsers distinct trên toàn cửa sổ từng dòng; không SUM qua event/nội dung/màn để ra tổng user.'),
    'Analytics Status': ('Tình trạng GA4', 'OK, DISABLED hoặc ERROR; lỗi không được biến thành 0 và không chặn báo cáo đơn Google.'),
}

RETRY = {'trial_billing_retry', 'subscription_billing_retry',
         'trial_billing_retry_entered', 'subscription_billing_retry_entered'}
CANCEL = {'trial_canceled', 'subscription_canceled'}
ACQUIRE = {'trial_started', 'subscription_started', 'in_app_purchase'}
NOTE = 'Lịch sử quan sát; tiền thu PROCESSED, tách currency. Không phải doanh thu ròng/thuê bao active.'


def properties(event):
    raw = event.get('raw_json') or '{}'
    payload = json.loads(raw) if isinstance(raw, str) else raw
    props = payload.get('properties') or {}
    if isinstance(props, list):
        return {p.get('key'): p.get('value') for p in props if isinstance(p, dict)}
    return props if isinstance(props, dict) else {}


def payload(event):
    raw = event.get('raw_json') or '{}'
    return json.loads(raw) if isinstance(raw, str) else raw


def build_marketing_reports(enriched, events, links, apps, cohorts, report_tz, include_all=False):
    tables = {name: [] for name in HEADERS}
    production = [e for e in events if (e.get('environment') or '').lower() == 'production']
    by_order = defaultdict(list)
    for e in production:
        by_order[(e['app_key'], e.get('order_id') or '')].append(e)
    records, chains = [], defaultdict(list)
    settings = {a['key']: a for a in apps}
    for o, d in enriched:
        key = o['app_key'], o['order_id']
        user, status = links[key]
        ev = [e for e in by_order[key] if status == 'MATCHED' and str(e.get('user_id') or '') == user]
        roots = {str(e['original_transaction_id']) for e in ev if e.get('original_transaction_id')}
        root = next(iter(roots)) if len(roots) == 1 else ''
        names = {e['event_name'] for e in ev}
        kind = 'renew' if 'subscription_renewed' in names and 'trial_converted' not in names else 'convert' if 'trial_converted' in names and 'subscription_renewed' not in names else 'other'
        record = dict(o=o, d=d, user=user if status == 'MATCHED' else '', root=root,
                      names=names, events=ev, kind=kind, date=timestamp(o.get('order_date')))
        records.append(record)
        if root and record['user']:
            chains[(o['app_key'], user, root)].append(record)

    # Freeze attribution at acquisition; later visits must not steal renewal revenue.
    attrs, starts = {}, {}
    for chain, rs in chains.items():
        acquisitions = [(timestamp(e.get('event_time')), e) for r in rs for e in r['events']
                        if e['event_name'] in ACQUIRE and timestamp(e.get('event_time'))]
        acquisitions.sort(key=lambda pair: (pair[0], pair[1].get('event_key') or ''))
        if acquisitions:
            dt, event = acquisitions[0]
            starts[chain] = dt
            # Do not pick an arbitrary snapshot if duplicate acquisition deliveries conflict.
            snapshots = {tuple(str(properties(e).get(k) or 'UNKNOWN') for k in
                         ('iap_data_type', 'iap_data_id', 'iap_data_name', 'iap_entry_source'))
                         for when, e in acquisitions if when == dt}
            if len(snapshots) == 1:
                attrs[chain] = next(iter(snapshots))

    def chain_of(r):
        return r['o']['app_key'], r['user'], r['root']

    def attribute(r):
        return attrs.get(chain_of(r), ('UNKNOWN',) * 4)

    def revenue(rs, kind=None):
        return float(sum((Decimal(r['o']['charged']) for r in rs
                          if r['o']['state'] == 'PROCESSED' and r['o'].get('charged') not in ('', None)
                          and (kind is None or r['kind'] == kind)), Decimal(0)))

    # Retry/cancel assigned by app/user/root, including webhook-only lifecycle events.
    lifecycle = defaultdict(list)
    for e in production:
        c = e['app_key'], str(e.get('user_id') or ''), str(e.get('original_transaction_id') or '')
        if c[1] and c[2]:
            lifecycle[c].append(e)

    def stat(rs, cohort_rows):
        users = {r['user'] for r in rs if r['user']}
        payers = {r['user'] for r in rs if r['user'] and paid(r['o'])}
        trial_users = {r['user'] for r in rs if r['user'] and trial(r['d'])}
        subscription_users = {r['user'] for r in rs if r['user'] and r['d']['kind'] == 'SUBSCRIPTION'}
        retry = {c[1] for c in {chain_of(r) for r in rs} if any(e['event_name'] in RETRY for e in lifecycle[c])}
        cohort_dicts = [dict(zip(UA_HEADERS['Trial_Cohorts'], c)) for c in cohort_rows]
        mature = sum(c['Mature Trial Episodes (7d after end)'] for c in cohort_dicts)
        converted = sum(c['Verified Conversions within 7d after Trial End'] for c in cohort_dicts)
        rate = converted / mature if mature and all(c['Conversion Rate Status'] == 'AVAILABLE' for c in cohort_dicts) else 'N/A'
        denominator = subscription_users | retry
        return [len(trial_users), len(payers), revenue([r for r in rs if r['user']]) / len(payers) if payers else 'N/A',
                mature, converted, rate, len(retry), len(retry) / len(denominator) if denominator else 'N/A',
                revenue(rs), revenue(rs, 'renew'), revenue(rs, 'convert'), revenue(rs, 'other'),
                sum(r['o']['state'] == 'PROCESSED' and r['o'].get('charged') in ('', None) for r in rs)]

    country, package, theme, screen, overview = (defaultdict(list) for _ in range(5))
    for r in records:
        o, d = r['o'], r['d']
        app, buyer, cur = o['app_key'], o.get('country') or 'UNKNOWN', o.get('currency') or 'UNKNOWN'
        country[(app, buyer, cur)].append(r)
        package[(app, d['plan'], d['identifier'], buyer, cur)].append(r)
        attr = attribute(r)
        theme[(app, *attr, buyer, cur)].append(r)
        screen[(app, attr[3], buyer, cur)].append(r)
        overview[(app, 'ALL', cur)].append(r)
        day = r['date'].astimezone(ZoneInfo(report_tz)).date().isoformat() if r['date'] else 'UNKNOWN'
        overview[(app, day, cur)].append(r)
        tables['RAW_Data'].append([app, 'ORDER', r['date'].astimezone(ZoneInfo(report_tz)).isoformat() if r['date'] else '',
            r['user'], o['order_id'], r['root'], buyer, '', d['plan'], d['identifier'], d['offer'], cur,
            numeric(o.get('charged')), numeric(o.get('developer_revenue')), o['state'], '', 'VERIFIED_ORDER',
            *attr, 'ACQUISITION_SNAPSHOT' if chain_of(r) in attrs else 'UNKNOWN', links[(app, o['order_id'])][1]])
    # RAW events retain sandbox and unknown environments for diagnosis; no money on EVENT rows.
    for e in events:
        dt = timestamp(e.get('event_time'))
        c = e['app_key'], str(e.get('user_id') or ''), str(e.get('original_transaction_id') or '')
        attr = attrs.get(c, ('UNKNOWN',) * 4) if (e.get('environment') or '').lower() == 'production' else ('UNKNOWN',) * 4
        tables['RAW_Data'].append([e['app_key'], 'EVENT', dt.astimezone(ZoneInfo(report_tz)).isoformat() if dt else '',
            e.get('user_id') or '', e.get('order_id') or '', c[2], '', e.get('country_ip') or '', '',
            e.get('product_id') or '', '', '', '', '', '', e.get('event_name') or '', e.get('environment') or 'UNKNOWN',
            *attr, 'ACQUISITION_SNAPSHOT' if attr != ('UNKNOWN',) * 4 else 'UNKNOWN', ''])

    from app.grouping import expand_groups, ALL
    if include_all:
        country = expand_groups(country, [(1,)])
        package = expand_groups(package, [(1,), (2,), (3,)])
        theme = expand_groups(theme, [(1,), (2,), (3,), (4,), (5,)])
        screen = expand_groups(screen, [(1,), (2,)])
    def matches(actual, selected):
        return all(want == ALL or value == want for value, want in zip(actual, selected))
    for key, rs in sorted(country.items()):
        cr = [c for c in cohorts if matches((c[0], c[5], c[6]), key)]
        tables['Country_Performance'].append([*key, *stat(rs, cr), NOTE])
    for key, rs in sorted(package.items()):
        cr = [c for c in cohorts if matches((c[0], c[2], c[3], c[5], c[6]), key)]
        tables['Package_Performance'].append([*key, sum(paid(r['o']) for r in rs), *stat(rs, cr), NOTE])

    # Daily rows count lifecycle activity by event date, not receipt date/order date.
    for c, es in lifecycle.items():
        rs = chains.get(c, [])
        if not rs:
            continue
        for e in es:
            if e['event_name'] in CANCEL | ACQUIRE:
                dt = timestamp(e.get('event_time'))
                if dt:
                    day = dt.astimezone(ZoneInfo(report_tz)).date().isoformat()
                    for cur in {r['o'].get('currency') or 'UNKNOWN' for r in rs}:
                        overview.setdefault((c[0], day, cur), [])
    for key, rs in sorted(overview.items()):
        app, day, cur = key
        def on_day(e):
            dt = timestamp(e.get('event_time'))
            return day == 'ALL' or bool(dt and dt.astimezone(ZoneInfo(report_tz)).date().isoformat() == day)
        cs = {c for c, chain_rs in chains.items() if c[0] == app and any(
            r['d']['kind'] == 'SUBSCRIPTION' and (r['o'].get('currency') or 'UNKNOWN') == cur for r in chain_rs)}
        new = {c for c in cs if c in starts and (day == 'ALL' or starts[c].astimezone(ZoneInfo(report_tz)).date().isoformat() == day)}
        canceled = {c for c in cs if any(e['event_name'] in CANCEL and on_day(e) for e in lifecycle[c])}
        cr = [c for c in cohorts if c[0] == app and c[6] == cur] if day == 'ALL' else []
        metrics = stat(rs, cr)
        if day != 'ALL':
            # All-time retry membership is not a daily failure rate.
            metrics[3:8] = ['N/A'] * 5
        tables['Overview'].append([*key, len(cs) if day == 'ALL' else 'N/A', len(new), len(canceled), 'N/A', *metrics, NOTE])

    upgrades = defaultdict(list)
    for c, rs in sorted(chains.items()):
        rs.sort(key=lambda r: (r['date'].isoformat() if r['date'] else '', r['o']['order_id']))
        start = starts.get(c)
        coverage = timestamp(settings.get(c[0], {}).get('analytics_coverage_start_utc'))
        valid = bool(start and coverage and coverage <= start and all(r['date'] and r['date'] >= start for r in rs))
        observed_renewals = [r for r in rs if r['kind'] == 'renew' and paid(r['o'])]
        for observed_index, r in enumerate(observed_renewals, 1):
            counters = {payload(e).get('subscription_renew_count') for e in r['events']
                        if e['event_name'] == 'subscription_renewed'} - {None}
            if counters and counters != {observed_index}:
                # A provider counter proves there is a gap/conflict despite configured coverage.
                valid = False
        steps, n = defaultdict(list), 0
        previous = None
        for r in rs:
            if r['kind'] == 'renew' and paid(r['o']):
                n += 1
                counters = {payload(e).get('subscription_renew_count') for e in r['events']
                            if e['event_name'] == 'subscription_renewed'}
                provider_step = next(iter(counters)) if len(counters) == 1 else None
                if isinstance(provider_step, int) and not isinstance(provider_step, bool) and provider_step > 0:
                    r['step_status'] = 'PROVIDER_COUNTER'
                    steps[provider_step].append(r)
                else:
                    r['step_status'] = 'AVAILABLE' if valid else 'UNKNOWN_HISTORY'
                    steps[n if valid else 'UNKNOWN'].append(r)
            else:
                steps[0].append(r)
            if 'subscription_upgraded' in r['names'] and paid(r['o']):
                old_ids = {str(payload(e).get('old_product_id')) for e in r['events']
                           if e['event_name'] == 'subscription_upgraded' and payload(e).get('old_product_id')
                           and str(payload(e).get('new_product_id') or r['o'].get('product')) in (r['o'].get('product'), r['d']['identifier'])}
                old = next(iter(old_ids)) if len(old_ids) == 1 else previous['d']['identifier'] if not old_ids and previous else ''
                if old and old != r['d']['identifier']:
                    key = c[0], r['o'].get('country') or 'UNKNOWN', r['o'].get('currency') or 'UNKNOWN', old, r['d']['identifier']
                    upgrades[key].append(r)
                else:
                    tables.setdefault('_quality', []).append([c[0], 'WARNING', 'UPGRADE_PREVIOUS_PLAN_UNKNOWN', 1, r['o']['order_id']])
            if paid(r['o']):
                previous = r
        # Split currencies/countries/plans but never restart the chain's ordinal per group.
        for step, step_rs in steps.items():
            groups = defaultdict(list)
            for r in step_rs:
                groups[(r['o'].get('country') or 'UNKNOWN', r['d']['identifier'], r['o'].get('currency') or 'UNKNOWN')].append(r)
            for (buyer, plan, cur), group in sorted(groups.items()):
                all_rs = [r for r in rs if (r['o'].get('country') or 'UNKNOWN', r['d']['identifier'], r['o'].get('currency') or 'UNKNOWN') == (buyer, plan, cur)]
                renewals = [r for r in group if r['kind'] == 'renew' and paid(r['o'])]
                tables['Cohort_Retention'].append([c[0], start.strftime('%Y-%m') if start else 'UNKNOWN', buyer, c[1], c[2], plan, cur,
                    step, int(bool(renewals)), len(renewals), revenue(group), revenue(all_rs), revenue(all_rs, 'renew'),
                    revenue(all_rs, 'convert'), revenue(all_rs, 'other'),
                    'PROVIDER_COUNTER' if group and all(r.get('step_status') == 'PROVIDER_COUNTER' for r in group) else 'AVAILABLE' if valid else 'UNKNOWN_HISTORY',
                    'Tổng chuỗi lặp trên từng bước: không SUM Total/Renew/Convert/Other qua các bước. Step 0 không phải renew.'])
    # A lifetime purchase can create a new store chain. Use the active-plan context
    # captured before billing, rather than guessing from unrelated previous orders.
    lifetime_upgrades = defaultdict(list)
    for r in records:
        if r['d']['plan'] != 'LIFETIME' or not r['user'] or not paid(r['o']) or 'in_app_purchase' not in r['names']:
            continue
        previous_plans = {str(properties(e).get('iap_from_plan') or '').upper() for e in r['events']
                          if e['event_name'] == 'in_app_purchase'}
        if len(previous_plans) == 1 and previous_plans <= {'WEEKLY', 'MONTHLY', 'YEARLY'}:
            key = (r['o']['app_key'], r['o'].get('country') or 'UNKNOWN', r['o'].get('currency') or 'UNKNOWN',
                   next(iter(previous_plans)), 'LIFETIME')
            lifetime_upgrades[key].append(r)
    for key, rs in lifetime_upgrades.items():
        upgrades[key].extend(rs)
    if include_all:
        upgrades = expand_groups(upgrades, [(1,), (3,), (4,)])
    for key, rs in sorted(upgrades.items()):
        tables['Plan_Upgrades'].append([*key, len({r['user'] for r in rs}), len(rs), revenue(rs),
            NOTE + ' Upgrade từ webhook subscription_upgraded; lifetime dùng gói active app chụp trong iap_from_plan.'])

    def attributed_stats(rs):
        cs = {chain_of(r) for r in rs}
        return [len({r['user'] for r in rs if r['user'] and trial(r['d'])}),
                len({r['user'] for r in rs if r['user'] and paid(r['o'])}),
                len({r['user'] for r in rs if r['user'] and paid(r['o']) and r['kind'] == 'convert'}),
                len({r['user'] for r in rs if r['user'] and paid(r['o']) and r['kind'] == 'renew'}),
                len({c[1] for c in cs if c[1] and any(e['event_name'] in CANCEL for e in lifecycle[c])}),
                revenue(rs), revenue(rs, 'renew'), revenue(rs, 'convert'), revenue(rs, 'other'),
                NOTE + ' Attribution từ acquisition snapshot; UNKNOWN không được tự gán vào nội dung/màn gần nhất. Click/đóng xem Firebase_Events.']
    for name, grouped in [('Theme_Performance', theme), ('Screen_Performance', screen)]:
        tables[name] = [[*key, *attributed_stats(rs)] for key, rs in sorted(grouped.items())]
    for app in apps:
        missing = sum(chain_of(r) not in attrs or attribute(r)[3] == 'UNKNOWN' for r in records if r['o']['app_key'] == app['key'])
        tables.setdefault('_quality', []).append([app['key'], 'WARNING' if missing else 'INFO', 'ACQUISITION_ATTRIBUTION_MISSING', missing,
            'Need properties iap_data_type/id/name/entry_source on acquisition webhook; GA4 aggregate reports cannot join individual transactions.'])
        unlinked = sum(not r['root'] or not r['user'] for r in records if r['o']['app_key'] == app['key'])
        tables['_quality'].append([app['key'], 'WARNING' if unlinked else 'INFO', 'RETENTION_CHAIN_MISSING', unlinked,
            'Orders without a unique production user/root remain in RAW/country/package; excluded from chain retention.'])
    return tables
