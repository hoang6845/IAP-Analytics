"""Report snapshots of verified orders; these are not live subscription statuses."""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

STATES = ('PROCESSED', 'PENDING', 'CANCELED', 'REFUNDED', 'PARTIALLY_REFUNDED', 'PENDING_REFUND')
PLANS = ('WEEKLY', 'MONTHLY', 'YEARLY', 'LIFETIME', 'UNKNOWN', 'MIXED')
EXTRA_GROUP_HEADERS = ['Total Orders', 'Pending Refund Orders', 'Other State Orders',
    'Average Charged (processed, known amounts)', 'Processed Amount Known Orders',
    'Developer Revenue Known Orders', 'First Order UTC', 'Last Order UTC', 'Last Checked UTC',
    'Processed Positive Amount Orders', 'Processed Zero Amount Orders', 'Free Trial Phase Orders']


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def month(value):
    dt = timestamp(value)
    return dt.strftime('%Y-%m') if dt else 'UNKNOWN'


def numeric(value):
    return float(Decimal(value)) if value not in ('', None) else ''


def classify(identifier, mapping):
    if identifier in mapping:
        plan = str(mapping[identifier]).upper()
        if plan not in PLANS[:-1]:
            raise ValueError('Unsupported report plan type: ' + plan)
        return plan, 'Configured product_plan_types'
    tokens = set(re.split(r'[^a-z0-9]+', identifier.lower()))
    matches = [plan for plan, names in (
        ('WEEKLY', {'week', 'weekly'}), ('MONTHLY', {'month', 'monthly'}),
        ('YEARLY', {'year', 'yearly', 'annual', 'annually'}),
        ('LIFETIME', {'lifetime'})) if tokens & names]
    return (matches[0], 'Inferred from ID naming') if len(matches) == 1 else ('UNKNOWN', 'Insufficient or ambiguous ID')


def order_details(order, linked, mapping):
    payload = json.loads(order.get('payload') or '{}')
    items = payload.get('lineItems') or []
    ids, bases, offers, titles, phases, starts, ends, types = [], [], [], [], [], [], [], []
    for item in items:
        product = str(item.get('productId') or '')
        sub = item.get('subscriptionDetails') or {}
        base = str(sub.get('basePlanId') or '')
        ids.append(product + (':' + base if base else ''))
        bases.append(base)
        offers.append(str(sub.get('offerId') or ''))
        titles.append(str(item.get('productTitle') or ''))
        phase = sub.get('offerPhaseDetails') or {}
        phases.append(next((name for name in ('freeTrialDetails', 'introductoryPriceDetails', 'baseDetails', 'prorationPeriodDetails') if name in phase), str(sub.get('offerPhase') or '')))
        starts.append(str(sub.get('servicePeriodStartTime') or ''))
        ends.append(str(sub.get('servicePeriodEndTime') or ''))
        types.append('SUBSCRIPTION' if 'subscriptionDetails' in item else 'ONE_TIME' if 'oneTimePurchaseDetails' in item else 'PAID_APP' if 'paidAppDetails' in item else 'UNKNOWN')
    latest = max(linked, key=lambda e: (timestamp(e.get('event_time')) or timestamp(e.get('received_at')) or datetime.min.replace(tzinfo=timezone.utc), e.get('received_at', '')), default={})
    webhook_ids = {e['product_id'] for e in linked if e.get('product_id')}
    # Never attach a plan from a lifecycle event for a different store product.
    if len(ids) <= 1 and (not ids or ':' not in ids[0]):
        store_product = ids[0] if ids else order.get('product', '')
        compatible = {p for p in webhook_ids if p.split(':', 1)[0] == store_product}
        if len(compatible) == 1:
            ids = [next(iter(compatible))]
            if ':' in ids[0]:
                bases = [ids[0].split(':', 1)[1]]
    identifiers = [p for p in ids if p] or [order.get('product') or 'UNKNOWN']
    classified = [classify(p, mapping) for p in identifiers]
    plans = {p for p, _ in classified}
    plan = next(iter(plans)) if len(plans) == 1 else 'MIXED'
    source = '; '.join(sorted({source for _, source in classified}))
    join = lambda values: ';'.join(v for v in values if v)
    return dict(plan=plan, source=source, identifier=join(identifiers), base=join(bases),
        offer=join(offers), title=join(titles), phase=join(phases), start=join(starts), end=join(ends),
        kind=join(sorted(set(types))) or 'UNKNOWN', latest=latest, payload=payload)


def summary(rows):
    states = Counter(o.get('state') for o, _ in rows)
    processed = [o for o, _ in rows if o['state'] == 'PROCESSED' and o.get('charged') not in ('', None)]
    revenue = [o for o, _ in rows if o['state'] in ('PROCESSED', 'PARTIALLY_REFUNDED') and o.get('developer_revenue') not in ('', None)]
    charged = sum((Decimal(o['charged']) for o in processed), Decimal(0))
    dates = sorted((timestamp(o.get('order_date')) for o, _ in rows if timestamp(o.get('order_date'))))
    checks = sorted((timestamp(o.get('checked_at')) for o, _ in rows if timestamp(o.get('checked_at'))))
    return dict(states=states, total=len(rows), charged=float(charged),
        revenue=float(sum((Decimal(o['developer_revenue']) for o in revenue), Decimal(0))),
        amount_known=len(processed), revenue_known=len(revenue),
        average=float(charged / len(processed)) if processed else '',
        first=dates[0].isoformat() if dates else '', last=dates[-1].isoformat() if dates else '',
        checked=checks[-1].isoformat() if checks else '', plans=Counter(d['plan'] for _, d in rows),
        positive=sum(Decimal(o['charged']) > 0 for o in processed),
        zero=sum(Decimal(o['charged']) == 0 for o in processed),
        trials=sum('freeTrialDetails' in d['phase'] or 'FREE_TRIAL' in d['phase'] for _, d in rows))


def extra_stats(s):
    return [s['total'], s['states']['PENDING_REFUND'], sum(v for k, v in s['states'].items() if k not in STATES),
        s['average'], s['amount_known'], s['revenue_known'], s['first'], s['last'], s['checked'],
        s['positive'], s['zero'], s['trials']]


def build_reports(orders, events, syncs, apps, now, report_tz='Asia/Bangkok'):
    linked = defaultdict(list)
    for e in events:
        if (e.get('environment') or '').lower() not in ('sandbox', 'test') and e.get('order_id'):
            linked[(e['app_key'], e['order_id'])].append(e)
    mappings = {a['key']: a.get('product_plan_types') or {} for a in apps}
    enriched = [(o, order_details(o, linked[(o['app_key'], o['order_id'])], mappings.get(o['app_key'], {}))) for o in orders]
    links = user_links(orders, events)
    countries, products, dashboards = defaultdict(list), defaultdict(list), defaultdict(list)
    transactions = []
    for o, d in enriched:
        country, currency = o.get('country') or 'UNKNOWN', o.get('currency') or 'UNKNOWN'
        countries[(o['app_key'], country, currency)].append((o, d))
        products[(o['app_key'], o.get('product') or 'UNKNOWN', currency, d['plan'], d['identifier'])].append((o, d))
        for period in ('ALL', month(o.get('order_date'))):
            dashboards[(o['app_key'], currency, period, 'ALL')].append((o, d))
            dashboards[(o['app_key'], currency, period, d['plan'])].append((o, d))
        dt = timestamp(o.get('order_date'))
        last = d['latest']
        tax = d['payload'].get('tax') or {}
        tax_value = float(Decimal(str(tax.get('units', 0))) + Decimal(str(tax.get('nanos', 0))) / Decimal(10**9)) if tax.get('currencyCode') == o.get('currency') else ''
        transactions.append([o['app_key'], o['order_id'], o.get('order_date', ''), o.get('country', ''), o.get('product', ''), o['state'], o.get('currency', ''),
            numeric(o.get('charged')), numeric(o.get('developer_revenue')), 'YES', len(linked[(o['app_key'], o['order_id'])]),
            d['plan'], d['identifier'], d['source'], d['kind'], d['base'], d['offer'], d['title'], d['phase'], d['start'], d['end'],
            month(o.get('order_date')), dt.astimezone(ZoneInfo(report_tz)).isoformat() if dt else '', o.get('checked_at', ''),
            d['payload'].get('lastEventTime', ''), tax_value, last.get('event_name', ''), last.get('event_time', ''), last.get('country_ip', ''), *links[(o['app_key'], o['order_id'])]])
    country_rows = []
    for k, rows in sorted(countries.items()):
        s = summary(rows)
        country_rows.append([*k, *[s['states'][x] for x in STATES[:5]], s['charged'], s['revenue'], *extra_stats(s),
            *[s['plans'][p] for p in PLANS], len({d['identifier'] for _, d in rows})])
    product_rows = []
    for k, rows in sorted(products.items()):
        s = summary(rows)
        product_rows.append([*k[:3], s['states']['PROCESSED'], s['states']['PENDING'], s['states']['REFUNDED'], s['charged'],
            k[3], k[4], s['states']['CANCELED'], s['states']['PARTIALLY_REFUNDED'], s['revenue'], *extra_stats(s), len({o.get('country') for o, _ in rows})])
    dashboard = []
    def metric(name, value, app='ALL', currency='', period='ALL', plan='ALL', note=''):
        dashboard.append([name, value, app, currency, period, plan, note])
    metric('Last export UTC', now)
    metric('Last export local', timestamp(now).astimezone(ZoneInfo(report_tz)).isoformat())
    metric('Applications', len(apps))
    metric('Orders verified', len(orders))
    for state in STATES:
        metric(state.replace('_', ' ').capitalize() + ' orders', sum(o['state'] == state for o in orders))
    metric('Buyer countries known', len({o['country'] for o in orders if o.get('country')}))
    metric('Plan variants', len({(o['app_key'], d['identifier']) for o, d in enriched}))
    for plan in PLANS:
        metric(plan + ' orders', sum(d['plan'] == plan for _, d in enriched))
    metric('Qonversion users observed (all environments)', len({(e['app_key'], str(e['user_id'])) for e in events if e.get('user_id')}))
    metric('Users linked to verified orders', len({(app, user) for (app, _), (user, status) in links.items() if status == 'MATCHED'}))
    paid_users = {(o['app_key'], links[(o['app_key'], o['order_id'])][0]) for o in orders
        if links[(o['app_key'], o['order_id'])][1] == 'MATCHED' and o['state'] in PAID_STATES
        and o.get('charged') not in ('', None) and Decimal(o['charged']) > 0}
    metric('Users with verified positive-amount payments', len(paid_users))
    metric('Verified orders missing user ID', sum(status == 'MISSING_USER_ID' for _, status in links.values()))
    metric('Verified orders with conflicting users', sum(status == 'CONFLICTING_USERS' for _, status in links.values()))
    metric('Note', 'Verified known IDs only; not the full Play order population.')
    metric('Note', 'Monthly rows group current order snapshots by creation month UTC, not historical cashflow.')
    metric('Note', 'Order states and service period snapshots do not indicate current active subscribers.')
    metric('Note', 'ALL and monthly/plan rows overlap; filter dimensions before summing. No cross-currency sums.')
    metric('Note', 'ID-based plan types are inferred; product_plan_types mappings provide explicit classification.')
    order_keys = {(o['app_key'], o['order_id']) for o in orders}
    for app in apps:
        ev = [e for e in events if e['app_key'] == app['key']]
        prod = [e for e in ev if (e.get('environment') or '').lower() == 'production']
        sandbox = [e for e in ev if (e.get('environment') or '').lower() in ('sandbox', 'test')]
        unknown = [e for e in ev if (e.get('environment') or '').lower() not in ('production', 'sandbox', 'test')]
        eligible = {e['order_id'] for e in ev if (e.get('environment') or '').lower() not in ('sandbox', 'test') and (e.get('order_id') or '').startswith('GPA.')}
        for name, value in [('Webhook events', len(ev)), ('Production events', len(prod)), ('Sandbox/test events', len(sandbox)),
                ('Unknown environment events', len(unknown)), ('Observed non-sandbox GPA IDs', len(eligible)),
                ('Observed IDs without verified order', sum((app['key'], oid) not in order_keys for oid in eligible)),
                ('Events missing Order ID (non-sandbox)', sum(not e.get('order_id') for e in ev if (e.get('environment') or '').lower() not in ('sandbox', 'test'))),
                ('Events with non-GPA Order ID (non-sandbox)', sum(bool(e.get('order_id')) and not e['order_id'].startswith('GPA.') for e in ev if (e.get('environment') or '').lower() not in ('sandbox', 'test'))),
                ('Last webhook received UTC', max((e.get('received_at') or '' for e in ev), default=''))]:
            metric(name, value, app=app['key'])
        for (env, name), count in sorted(Counter(((e.get('environment') or 'UNKNOWN'), e.get('event_name') or 'UNKNOWN') for e in ev).items()):
            metric('Webhook: ' + name, count, app=app['key'], note='Environment=' + env + '; events are not unique subscribers')
        webhook_plans = Counter(((e.get('environment') or 'UNKNOWN'), classify(e.get('product_id') or '', mappings[app['key']])[0]) for e in ev)
        for (env, plan), count in sorted(webhook_plans.items()):
            metric('Webhook events by plan', count, app=app['key'], plan=plan,
                note='Environment=' + env + '; inferred/configured ID type; events are not subscribers')
    if syncs:
        metric('Last sync result', syncs[0]['result'])
        metric('Last sync UTC', syncs[0]['ran_at'])
        metric('Last sync details', syncs[0]['detail'])
        metric('Errors in latest 100 sync log rows', sum(s['result'] == 'ERROR' for s in syncs))
    for (app, currency, period, plan), rows in sorted(dashboards.items()):
        s = summary(rows)
        metric('Orders', s['total'], app, currency, period, plan)
        for state in STATES:
            metric(state + ' orders', s['states'][state], app, currency, period, plan)
        metric('Other state orders', sum(v for k, v in s['states'].items() if k not in STATES), app, currency, period, plan)
        for label, field in [('Processed positive amount orders', 'positive'), ('Processed zero amount orders', 'zero'),
                ('Free trial phase orders', 'trials'), ('Charged amount (processed)', 'charged'), ('Developer revenue (processed and partially refunded)', 'revenue'),
                ('Average charged (processed, known amounts)', 'average'), ('Processed amount known orders', 'amount_known'),
                ('Developer revenue known orders', 'revenue_known'), ('First order UTC', 'first'), ('Last order UTC', 'last')]:
            metric(label, s[field], app, currency, period, plan)
    from app.ua_reports import build_ua_reports
    result = {'Transactions': transactions, 'Country_Analysis': country_rows,
        'Product_Analysis': product_rows, 'Diagnostics': dashboard, 'Users': build_users(enriched, events, links)}
    result.update(build_ua_reports(enriched, events, links, apps, now, report_tz))
    return result
USER_HEADERS = ['App', 'User ID', 'Custom User IDs', 'Identity IDs', 'Currency', 'User Link Status',
    'Payment Count', 'Processed Paid Orders', 'Refunded Paid Orders', 'Partially Refunded Paid Orders',
    'Pending Refund Paid Orders', 'Total Verified Orders', 'Processed Orders', 'Pending Orders',
    'Canceled Orders', 'Refunded Orders', 'Partially Refunded Orders', 'Pending Refund Orders',
    'Other State Orders', 'Processed Positive Amount Orders', 'Processed Zero Amount Orders',
    'Free Trial Phase Orders', 'Payment Order Face Amount (includes refunded)',
    'Charged Amount (processed)', 'Developer Revenue (processed and partially refunded)',
    'Processed Amount Known Orders', 'Developer Revenue Known Orders', 'First Payment UTC',
    'Last Payment UTC', 'First Order UTC', 'Last Order UTC', 'Last Checked UTC', 'Plan Types',
    'Plan Identifiers', 'Buyer Countries', 'Verified Order IDs', 'Production Events (user, all currencies)',
    'Sandbox/Test Events (user, all currencies)', 'Unknown Environment Events (user, all currencies)',
    'Non-Sandbox IDs Without Verified Order (user, all currencies)', 'First Webhook Received UTC',
    'Last Webhook Received UTC', 'Notes']
PAID_STATES = {'PROCESSED', 'REFUNDED', 'PARTIALLY_REFUNDED', 'PENDING_REFUND'}


def user_links(orders, events):
    candidates = defaultdict(set)
    for e in events:
        if (e.get('environment') or '').lower() not in ('sandbox', 'test') and e.get('order_id') and e.get('user_id'):
            candidates[(e['app_key'], e['order_id'])].add(str(e['user_id']))
    result = {}
    for o in orders:
        key = (o['app_key'], o['order_id'])
        users = candidates[key]
        result[key] = (next(iter(users)), 'MATCHED') if len(users) == 1 else ('', 'CONFLICTING_USERS' if users else 'MISSING_USER_ID')
    return result


def build_users(enriched, events, links):
    grouped = defaultdict(list)
    profiles = defaultdict(list)
    for e in events:
        user = str(e.get('user_id') or '')
        if user:
            profiles[(e['app_key'], user)].append(e)
    for o, d in enriched:
        user, status = links[(o['app_key'], o['order_id'])]
        grouped[(o['app_key'], user, o.get('currency') or 'UNKNOWN', status)].append((o, d))
    users_with_orders = {(app, user) for app, user, _, _ in grouped if user}
    for app, user in profiles:
        if (app, user) not in users_with_orders:
            grouped[(app, user, '', 'NO_VERIFIED_ORDERS')] = []
    verified_ids = {(o['app_key'], o['order_id']) for o, _ in enriched}
    rows = []
    for (app, user, currency, status), orders in sorted(grouped.items()):
        s = summary(orders)
        paid = [o for o, _ in orders if o['state'] in PAID_STATES and o.get('charged') not in ('', None) and Decimal(o['charged']) > 0]
        paid_states = Counter(o['state'] for o in paid)
        dates = sorted(timestamp(o.get('order_date')) for o in paid if timestamp(o.get('order_date')))
        ev = profiles.get((app, user), []) if user else []
        prod = sum((e.get('environment') or '').lower() == 'production' for e in ev)
        sandbox = sum((e.get('environment') or '').lower() in ('sandbox', 'test') for e in ev)
        unknown = len(ev) - prod - sandbox
        pending_ids = {e['order_id'] for e in ev if (e.get('environment') or '').lower() not in ('sandbox', 'test') and e.get('order_id') and (app, e['order_id']) not in verified_ids}
        received = sorted(timestamp(e.get('received_at')) for e in ev if timestamp(e.get('received_at')))
        join = lambda values: ';'.join(sorted({str(v) for v in values if v}))
        note = 'Payment Count = distinct known positive-amount verified orders in this currency, including refunded; not active subscriptions. Webhook columns cover this user across all currencies and repeat on each currency row.'
        if not user:
            note = 'Unattributed orders grouped for reconciliation, not one person. ' + note
        elif not orders:
            note = 'Webhook-only user; no verified orders. ' + note
        rows.append([app, user, join(e.get('custom_user_id') for e in ev), join(e.get('identity_id') for e in ev), currency, status,
            len(paid), paid_states['PROCESSED'], paid_states['REFUNDED'], paid_states['PARTIALLY_REFUNDED'], paid_states['PENDING_REFUND'],
            s['total'], *[s['states'][x] for x in STATES], sum(v for k, v in s['states'].items() if k not in STATES),
            s['positive'], s['zero'], s['trials'],
            float(sum((Decimal(o['charged']) for o in paid), Decimal(0))) if paid else '',
            s['charged'] if s['amount_known'] else '', s['revenue'] if s['revenue_known'] else '',
            s['amount_known'], s['revenue_known'], dates[0].isoformat() if dates else '', dates[-1].isoformat() if dates else '',
            s['first'], s['last'], s['checked'], join(d['plan'] for _, d in orders), join(d['identifier'] for _, d in orders),
            join(o.get('country') for o, _ in orders), join(o['order_id'] for o, _ in orders), prod, sandbox, unknown, len(pending_ids),
            received[0].isoformat() if received else '', received[-1].isoformat() if received else '', note])
    return rows