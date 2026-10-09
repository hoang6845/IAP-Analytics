"""Qonversion ingestion, Google Play verification and Google Sheets analytics.
The Qonversion webhook is an event feed; order totals/status are sourced from Google Play.
"""
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import threading
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import requests
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('iap')
DB = os.getenv('DB_PATH', '/data/iap.sqlite3')
LOCK = threading.Lock()
SCOPES = ['https://www.googleapis.com/auth/androidpublisher', 'https://www.googleapis.com/auth/spreadsheets']
SHEETS_HEADERS = {
    'Transactions': ['App', 'Order ID', 'Date UTC', 'Country (buyer)', 'Product', 'State', 'Currency', 'Charged Amount', 'Developer Revenue', 'Google Verified', 'Qonversion Events'],
    'Country_Analysis': ['App', 'Country (buyer)', 'Currency', 'Processed Orders', 'Pending Orders', 'Canceled Orders', 'Refunded Orders', 'Partially Refunded Orders', 'Charged Amount (processed)', 'Developer Revenue (processed and partially refunded)'],
    'Product_Analysis': ['App', 'Product', 'Currency', 'Processed Orders', 'Pending Orders', 'Refunded Orders', 'Charged Amount (processed)'],
    'Dashboard': ['Metric', 'Value'],
    'Sync_Log': ['Last Run UTC', 'Result', 'Details'],
    'Qonversion_Events': ['App', 'Event Time UTC', 'Event', 'Order ID', 'Product', 'Qonversion Country (IP)', 'Environment', 'Event Key'],
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def config_apps():
    with open(os.getenv('APPS_CONFIG', '/code/config/apps.yaml'), encoding='utf-8') as f:
        apps = yaml.safe_load(f)['apps']
    keys = [x['key'] for x in apps]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate app keys')
    return apps


@contextmanager
def database():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS events (
            event_key TEXT PRIMARY KEY, app_key TEXT NOT NULL, order_id TEXT,
            event_time TEXT, event_name TEXT, product_id TEXT, country_ip TEXT,
            environment TEXT, raw_json TEXT NOT NULL, received_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_order ON events(app_key, order_id);
        CREATE TABLE IF NOT EXISTS orders (
            app_key TEXT NOT NULL, order_id TEXT NOT NULL, state TEXT,
            order_date TEXT, country TEXT, product TEXT, currency TEXT,
            charged TEXT, developer_revenue TEXT, payload TEXT,
            checked_at TEXT NOT NULL, PRIMARY KEY(app_key, order_id)
        );
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT, result TEXT, detail TEXT
        );
        ''')


def normal_time(t):
    if isinstance(t, (float, int)):
        return datetime.fromtimestamp(t, timezone.utc).isoformat()
    return str(t or '')


def normalize_webhook(payload):
    """Do not infer Qonversion IDs from guessed fields: only known transaction paths."""
    t = payload.get('transaction') if isinstance(payload.get('transaction'), dict) else {}
    oid = t.get('transaction_id') or payload.get('order_id')
    name = payload.get('event_name') or ''
    event_time = normal_time(payload.get('time') or payload.get('created_at'))
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    # Exact duplicate retries are collapsed; distinct lifecycle payloads retained.
    key = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return key, str(oid or ''), str(name), event_time, str(payload.get('product_id') or ''), str(payload.get('country') or ''), str(payload.get('environment') or '')


def money(m):
    if not isinstance(m, dict):
        return '', ''
    currency = m.get('currencyCode') or ''
    if not currency:
        return '', ''
    val = Decimal(str(m.get('units', 0))) + Decimal(str(m.get('nanos', 0))) / Decimal(10**9)
    return currency, format(val, 'f')


def ingest_order(app_key, order):
    oid = str(order['orderId'])
    currency, charged = money(order.get('total'))
    rev_currency, rev = money(order.get('developerRevenueInBuyerCurrency'))
    if rev_currency and currency and rev_currency != currency:
        raise ValueError('Unexpected differing currencies on order')
    if not currency:
        currency = rev_currency
    item = order.get('lineItems') or []
    product = ';'.join(str(i.get('productId') or '') for i in item)
    buyer = order.get('buyerAddress') or {}
    with database() as db:
        db.execute('''INSERT INTO orders(app_key,order_id,state,order_date,country,product,currency,charged,developer_revenue,payload,checked_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(app_key,order_id) DO UPDATE SET
            state=excluded.state, order_date=excluded.order_date, country=excluded.country,
            product=excluded.product, currency=excluded.currency, charged=excluded.charged,
            developer_revenue=excluded.developer_revenue, payload=excluded.payload, checked_at=excluded.checked_at''',
            (app_key, oid, order.get('state', ''), order.get('createTime', ''), buyer.get('buyerCountry', ''),
             product, currency, charged, rev, json.dumps(order), utc_now()))


def creds():
    return service_account.Credentials.from_service_account_file(os.environ['GOOGLE_APPLICATION_CREDENTIALS'], scopes=SCOPES)


def fetch_order(session, pkg, oid):
    url = f'https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{pkg}/orders/{oid}'
    response = session.get(url, timeout=25)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def sync_orders():
    apps = config_apps()
    today = datetime.now(timezone.utc)
    cutoff = (today - timedelta(days=int(os.getenv('ORDER_RECHECK_DAYS', '45')))).isoformat()
    session = AuthorizedSession(creds())
    checked = 0
    not_found = 0
    for app in apps:
        key, pkg = app['key'], app['package_name']
        with database() as db:
            # New Qonversion IDs + all orders with recent activity; bounded recheck window.
            rows = db.execute('''SELECT DISTINCT order_id FROM events WHERE app_key=? AND order_id IS NOT NULL
                                  AND order_id!='' AND lower(environment) NOT IN ('sandbox','test') AND (event_time>=? OR received_at>=?)
                                  UNION SELECT order_id FROM orders WHERE app_key=? AND
                                  (order_date>=? OR state IN ('PENDING','PENDING_REFUND'))''',
                              (key, cutoff, cutoff, key, cutoff)).fetchall()
        for row in rows:
            oid = row['order_id']
            if not oid.startswith('GPA.'):
                continue
            try:
                order = fetch_order(session, pkg, oid)
                if order:
                    ingest_order(key, order)
                    checked += 1
                else:
                    not_found += 1
            except requests.HTTPError as exc:
                log.exception('Google Play request error for app=%s order=%s', key, oid)
                raise RuntimeError(f'Google Play HTTP error: {exc.response.status_code}') from exc
    return f'Google Play verified={checked}, not_found={not_found}'


def sheet_safe(value):
    # Prevent cell formula injection from external payloads.
    s = str(value if value is not None else '')
    if s.startswith(('=', '+', '-', '@')):
        return "'" + s
    return s


def export_sheets():
    if os.getenv('ENABLE_SHEETS', 'true').lower() != 'true':
        return 'Sheets disabled'
    spreadsheet = gspread.authorize(creds()).open_by_key(os.environ['SHEET_ID'])
    with database() as db:
        orders = [dict(row) for row in db.execute('SELECT * FROM orders ORDER BY order_date DESC')]
        events = [dict(row) for row in db.execute('SELECT * FROM events ORDER BY received_at DESC LIMIT 20000')]
        syncs = [dict(row) for row in db.execute('SELECT * FROM sync_log ORDER BY id DESC LIMIT 100')]
    event_counts = defaultdict(int)
    for e in events:
        if e['environment'].lower() in ('sandbox', 'test'):
            continue
        if e['order_id']:
            event_counts[(e['app_key'], e['order_id'])] += 1
    transactions = []
    countries = defaultdict(lambda: defaultdict(int))
    products = defaultdict(lambda: defaultdict(int))
    for o in orders:
        key = (o['app_key'], o['country'] or 'UNKNOWN', o['currency'] or 'UNKNOWN')
        prod_key = (o['app_key'], o['product'] or 'UNKNOWN', o['currency'] or 'UNKNOWN')
        status = o['state']
        for group, index in ((countries, key), (products, prod_key)):
            group[index][status] += 1
        if status == 'PROCESSED':
            countries[key]['charged'] += Decimal(o['charged'] or '0')
            products[prod_key]['charged'] += Decimal(o['charged'] or '0')
        if status in ('PROCESSED', 'PARTIALLY_REFUNDED') and o['developer_revenue'] != '':
            countries[key]['revenue'] += Decimal(o['developer_revenue'] or '0')
        transactions.append([o['app_key'], o['order_id'], o['order_date'], o['country'], o['product'], status,
                             o['currency'], o['charged'], o['developer_revenue'], 'YES', event_counts[(o['app_key'], o['order_id'])]])
    country_rows = [[*k, v['PROCESSED'], v['PENDING'], v['CANCELED'], v['REFUNDED'],
                     v['PARTIALLY_REFUNDED'], float(v['charged']), float(v['revenue'])] for k, v in sorted(countries.items())]
    product_rows = [[*k, v['PROCESSED'], v['PENDING'], v['REFUNDED'], float(v['charged'])] for k, v in sorted(products.items())]
    dashboard = [
        ['Last export UTC', utc_now()], ['Applications', len(config_apps())],
        ['Orders verified', len(orders)], ['Pending orders', sum(o['state']=='PENDING' for o in orders)],
        ['Processed orders', sum(o['state']=='PROCESSED' for o in orders)],
        ['Refunded orders', sum(o['state']=='REFUNDED' for o in orders)],
        ['Note', 'Amounts stay in original currencies; no cross-currency sums.'],
        ['Note', 'Order data = verified known IDs only; not full Play order population.'],
    ]
    tables = {
        'Transactions': transactions,
        'Country_Analysis': country_rows,
        'Product_Analysis': product_rows,
        'Dashboard': dashboard,
        'Sync_Log': [[s['ran_at'], s['result'], s['detail']] for s in syncs],
        'Qonversion_Events': [[e['app_key'], e['event_time'], e['event_name'], e['order_id'],
                              e['product_id'], e['country_ip'], e['environment'], e['event_key']] for e in events]
    }
    for name, header in SHEETS_HEADERS.items():
        try:
            ws = spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=name, rows=100, cols=max(12, len(header)))
        values = [header] + [[c if isinstance(c, (float, int)) and not isinstance(c, bool) else sheet_safe(c) for c in row] for row in tables[name]]
        # Full snapshot replacement eliminates duplicate rows and stale values.
        ws.clear()
        ws.update(range_name='A1', values=values, value_input_option='RAW')
        ws.freeze(rows=1)
    return f'Exported orders={len(orders)}, events={len(events)}'


def sync_job():
    if not LOCK.acquire(blocking=False):
        log.warning('Sync skipped; previous run active')
        return {'status': 'busy'}
    try:
        detail = sync_orders()
        with database() as db:
            db.execute('INSERT INTO sync_log(ran_at,result,detail) VALUES(?,?,?)', (utc_now(), 'OK_PLAY', detail))
        detail += '; ' + export_sheets()
        log.info('Sync complete: %s', detail)
        return {'status': 'ok', 'detail': detail}
    except Exception as ex:
        log.exception('Sync failed')
        with database() as db:
            db.execute('INSERT INTO sync_log(ran_at,result,detail) VALUES(?,?,?)', (utc_now(), 'ERROR', str(ex)[:1000]))
        return {'status': 'error'}
    finally:
        LOCK.release()


app = FastAPI(title='IAP Analytics')
scheduler = BackgroundScheduler(timezone=ZoneInfo(os.getenv('TZ', 'Asia/Bangkok')))


@app.on_event('startup')
def startup():
    init_db()
    config_apps()
    scheduler.add_job(sync_job, 'cron', minute=int(os.getenv('SYNC_MINUTE', '5')), id='hourly-sync', max_instances=1, coalesce=True, replace_existing=True)
    scheduler.start()
    log.info('Scheduler ready; hourly at minute %s', os.getenv('SYNC_MINUTE', '5'))


@app.on_event('shutdown')
def shutdown():
    scheduler.shutdown(wait=False)


@app.get('/health')
def health():
    return {'status': 'ok', 'time': utc_now()}



@app.get('/', response_class=HTMLResponse)
def sync_page():
    return HTMLResponse("""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IAP Analytics</title><style>
body{font-family:system-ui,sans-serif;max-width:560px;margin:60px auto;padding:24px;background:#f5f7fb;color:#182235}
input,button{box-sizing:border-box;width:100%;padding:14px;margin-top:12px;font:inherit;border-radius:8px;border:1px solid #ccd3df}
button{background:#2458d6;color:white;cursor:pointer}button:disabled{opacity:.6;cursor:wait}
#result{white-space:pre-wrap;overflow-wrap:anywhere}label{display:block}
</style></head><body><h1>IAP Analytics</h1>
<p>Kiểm tra đơn Google Play đã nhận và cập nhật Google Sheets ngay. Lịch sync mỗi giờ vẫn hoạt động.</p>
<form id="sync-form"><label for="token">WEBHOOK_TOKEN</label>
<input id="token" type="password" autocomplete="off" required placeholder="Nhập token của deployment này">
<button id="sync-button" type="submit">Sync ngay</button></form>
<p id="result" role="status" aria-live="polite"></p>
<script>
const form=document.getElementById('sync-form'),button=document.getElementById('sync-button'),result=document.getElementById('result');
form.addEventListener('submit',async event=>{
  event.preventDefault();button.disabled=true;result.textContent='Đang sync, vui lòng chờ…';
  try{
    const response=await fetch('/admin/sync',{method:'POST',headers:{'X-Webhook-Token':document.getElementById('token').value}});
    const data=await response.json();
    if(response.status===401) result.textContent='Token không hợp lệ.';
    else if(response.status===409) result.textContent='Một lần sync đang chạy. Vui lòng chờ hoàn tất.';
    else if(!response.ok) result.textContent='Sync thất bại. Kiểm tra logs và Sync_Log.';
    else result.textContent='Sync hoàn tất: '+data.detail;
  }catch(error){result.textContent='Không nhận được kết quả. Kiểm tra logs trước khi thử lại; lần sync có thể vẫn đang chạy.';}
  finally{button.disabled=false;}
});
</script></body></html>""", headers={'Cache-Control': 'no-store'})


@app.post('/admin/sync')
def manual_sync(x_webhook_token: str | None = Header(default=None)):
    expected = os.getenv('WEBHOOK_TOKEN', '')
    if len(expected) < 24 or not x_webhook_token or not hmac.compare_digest(x_webhook_token, expected):
        raise HTTPException(401, 'Unauthorized')
    result = sync_job()
    if result['status'] == 'busy':
        raise HTTPException(409, 'Sync already running')
    if result['status'] == 'error':
        raise HTTPException(500, 'Sync failed; check logs')
    return result


@app.post('/webhooks/qonversion/{app_key}')
async def qonversion(
    app_key: str,
    request: Request,
    x_webhook_token: str | None = Header(default=None),
    authorization_token: str | None = Header(default=None, alias='Authorization-Token'),
    authorization: str | None = Header(default=None),
):
    expected = os.getenv('WEBHOOK_TOKEN', '')
    # Qonversion sends Basic followed by the raw configured token (not base64).
    # Preserve existing clients, but a supplied Authorization header takes precedence.
    if authorization is not None:
        scheme, separator, value = authorization.partition(' ')
        supplied = value if separator and scheme.lower() == 'basic' else None
    else:
        supplied = authorization_token if authorization_token is not None else x_webhook_token
    if len(expected) < 24 or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, 'Unauthorized')
    apps = {a['key']: a for a in config_apps()}
    if app_key not in apps:
        raise HTTPException(404, 'Unknown app')
    body = await request.body()
    if len(body) > 262144:
        raise HTTPException(413, 'Payload too large')
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise HTTPException(400, 'Bad JSON')
    if not isinstance(payload, dict) or not payload.get('event_name'):
        raise HTTPException(422, 'Expected Qonversion event_name payload')
    declared_app = payload.get('app_id')
    configured_app = apps[app_key].get('qonversion_app_id')
    if declared_app and configured_app and not str(configured_app).startswith('REPLACE') and str(declared_app) != str(configured_app):
        raise HTTPException(422, 'Qonversion app_id does not match configured app')
    k, oid, name, event_time, product, country, environment = normalize_webhook(payload)
    with database() as db:
        cur = db.execute('''INSERT OR IGNORE INTO events(event_key,app_key,order_id,event_time,event_name,product_id,country_ip,environment,raw_json,received_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?)''', (k,app_key,oid,event_time,name,product,country,environment,json.dumps(payload),utc_now()))
    return {'accepted': True, 'duplicate': cur.rowcount == 0, 'event_key': k}
