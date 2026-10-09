import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, create_autospec, patch
from app import main
from app.reports import build_reports, classify

NOW = '2026-10-09T03:00:00+00:00'
APPS = [{'key': 'app', 'package_name': 'com.example'}]


def order(oid, state='PROCESSED', currency='USD', amount='10', base='premium-weekly-auto', product='premium', date='2026-10-01T00:00:00Z', revenue='7'):
    details = {'productId': product, 'subscriptionDetails': {'basePlanId': base, 'offerId': 'trial-offer',
        'offerPhaseDetails': {'baseDetails': {}}, 'servicePeriodStartTime': date, 'servicePeriodEndTime': '2026-10-08T00:00:00Z'}}
    return dict(app_key='app', order_id=oid, state=state, order_date=date, country='VN', product=product,
        currency=currency, charged=amount, developer_revenue=revenue, checked_at=NOW,
        payload=json.dumps({'lineItems': [details], 'tax': {'currencyCode': currency, 'units': '1'}}))


def event(oid, env='production', product='premium:premium-weekly-auto', date=NOW, name='subscription_started'):
    return dict(app_key='app', order_id=oid, product_id=product, environment=env, event_time=date,
        event_name=name, country_ip='US', received_at=date, event_key=oid+env)


class ReportsTest(unittest.TestCase):
    def build(self, orders, events=(), apps=APPS):
        return build_reports(orders, list(events), [], apps, NOW)

    def rows(self, report, name):
        name = 'Diagnostics' if name == 'Dashboard' else name
        return [dict(zip(main.SHEETS_HEADERS[name], row)) for row in report[name]]

    def test_base_plans_split_product_and_dashboard_currency_month(self):
        report = self.build([order('GPA.1'), order('GPA.2', base='premium-yearly'),
            order('GPA.3', currency='VND', amount='25000', revenue='18000', date='2026-09-30T23:30:00Z')])
        products = self.rows(report, 'Product_Analysis')
        self.assertEqual(len(products), 3)
        self.assertEqual({p['Plan Type'] for p in products}, {'WEEKLY', 'YEARLY'})
        metrics = self.rows(report, 'Dashboard')
        charged = {(m['Currency'], m['Order Month UTC']): m['Value'] for m in metrics
            if m['Metric'] == 'Charged amount (processed)' and m['Plan Type'] == 'ALL'}
        self.assertEqual(charged[('USD', 'ALL')], 20)
        self.assertEqual(charged[('VND', 'ALL')], 25000)
        self.assertEqual(charged[('VND', '2026-09')], 25000)
        self.assertNotIn(('', 'ALL'), charged)
        tx = self.rows(report, 'Transactions')
        self.assertTrue(tx[2]['Order Date Local'].startswith('2026-10-01'))
        self.assertEqual(tx[2]['Order Month UTC'], '2026-09')

    def test_refunds_unknown_amounts_and_other_states_are_not_paid(self):
        report = self.build([order('GPA.1'), order('GPA.2', state='REFUNDED'),
            order('GPA.3', state='PARTIALLY_REFUNDED', revenue='3'),
            order('GPA.4', amount='', revenue=''), order('GPA.5', state='PENDING_REFUND'),
            order('GPA.6', state='FUTURE_STATE')])
        country = self.rows(report, 'Country_Analysis')[0]
        self.assertEqual(country['Total Orders'], 6)
        self.assertEqual(country['Processed Orders'], 2)
        self.assertEqual(country['Charged Amount (processed)'], 10)
        self.assertEqual(country['Developer Revenue (processed and partially refunded)'], 10)
        self.assertEqual(country['Processed Amount Known Orders'], 1)
        self.assertEqual(country['Developer Revenue Known Orders'], 2)
        self.assertEqual(country['Average Charged (processed, known amounts)'], 10)
        self.assertEqual(country['Processed Positive Amount Orders'], 1)
        self.assertEqual(country['Processed Zero Amount Orders'], 0)
        self.assertEqual(country['Pending Refund Orders'], 1)
        self.assertEqual(country['Other State Orders'], 1)
        self.assertEqual(self.rows(report, 'Transactions')[3]['Charged Amount'], '')

    def test_sandbox_never_enriches_verified_order_and_latest_event_is_chronological(self):
        events = [event('GPA.1', date='2026-10-01T01:00:00Z'),
            event('GPA.1', date='2026-10-02T01:00:00Z', name='subscription_canceled'),
            event('GPA.1', env='sandbox', name='subscription_renewed')]
        report = self.build([order('GPA.1')], events)
        tx = self.rows(report, 'Transactions')[0]
        self.assertEqual(tx['Qonversion Events'], 2)
        self.assertEqual(tx['Latest Qonversion Event'], 'subscription_canceled')
        self.assertEqual(tx['Country (buyer)'], 'VN')
        self.assertEqual(tx['Qonversion Country (IP)'], 'US')
        metrics = {m['Metric']: m['Value'] for m in self.rows(report, 'Dashboard') if m['App'] == 'app' and not m['Currency']}
        self.assertEqual(metrics['Sandbox/test events'], 1)
        self.assertEqual(metrics['Production events'], 2)

    def test_webhook_base_plan_fallback_and_explicit_lifetime(self):
        o = order('GPA.1', base='')
        report = self.build([o], [event('GPA.1')])
        self.assertEqual(self.rows(report, 'Transactions')[0]['Plan Type'], 'WEEKLY')
        self.assertEqual(classify('premium', {})[0], 'UNKNOWN')
        self.assertEqual(classify('premium', {'premium': 'LIFETIME'})[0], 'LIFETIME')
        report = self.build([o], [event('GPA.1', product='different:annual')])
        self.assertEqual(self.rows(report, 'Transactions')[0]['Plan Type'], 'UNKNOWN')

    def test_lifetime_and_trial_counts_do_not_invent_subscription_activity(self):
        life = order('GPA.life', product='premium_lifetime', base='')
        payload = json.loads(life['payload'])
        payload['lineItems'] = [{'productId': 'premium_lifetime', 'oneTimePurchaseDetails': {}}]
        life['payload'] = json.dumps(payload)
        trial = order('GPA.trial', amount='0', revenue='0')
        payload = json.loads(trial['payload'])
        payload['lineItems'][0]['subscriptionDetails']['offerPhaseDetails'] = {'freeTrialDetails': {}}
        trial['payload'] = json.dumps(payload)
        report = self.build([life, trial])
        tx = self.rows(report, 'Transactions')
        self.assertEqual(tx[0]['Plan Type'], 'LIFETIME')
        self.assertEqual(tx[0]['Purchase Kind'], 'ONE_TIME')
        country = self.rows(report, 'Country_Analysis')[0]
        self.assertEqual(country['LIFETIME Orders'], 1)
        self.assertEqual(country['Free Trial Phase Orders'], 1)
        self.assertEqual(country['Processed Zero Amount Orders'], 1)
        self.assertEqual(country['Processed Positive Amount Orders'], 1)
        self.assertEqual(country['Charged Amount (processed)'], 10)

    def test_empty_and_multiline_order_preserve_row_width_and_one_order_count(self):
        for report in (self.build([]), self.build([order('GPA.1')])):
            for name, rows in report.items():
                for row in rows:
                    self.assertEqual(len(row), len(main.SHEETS_HEADERS[name]), name)
        o = order('GPA.1')
        payload = json.loads(o['payload'])
        payload['lineItems'].append({'productId': 'premium_lifetime', 'oneTimePurchaseDetails': {}})
        o['payload'] = json.dumps(payload)
        report = self.build([o])
        self.assertEqual(self.rows(report, 'Transactions')[0]['Plan Type'], 'MIXED')
        self.assertEqual(sum(r['Total Orders'] for r in self.rows(report, 'Product_Analysis')), 1)

    def test_export_expands_existing_tabs_and_preserves_numeric_and_safe_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            sheet = MagicMock()
            worksheets = {}
            for name in main.SHEETS_HEADERS:
                ws = create_autospec(main.gspread.Worksheet, instance=True)
                ws.row_count, ws.col_count = 100, 12
                worksheets[name] = ws
            sheet.worksheet.side_effect = lambda name: worksheets[name]
            with patch.object(main, 'DB', os.path.join(temp, 'db.sqlite3')), patch.object(main, 'creds'), \
                    patch.object(main, 'config_apps', return_value=APPS), \
                    patch.dict(os.environ, {'SHEET_ID': 'test', 'ENABLE_SHEETS': 'true'}), \
                    patch.object(main.gspread, 'authorize') as authorize:
                authorize.return_value.open_by_key.return_value = sheet
                main.init_db()
                o = order('GPA.1')
                payload = json.loads(o['payload'])
                payload['lineItems'][0]['productTitle'] = '=BAD()'
                payload.update(orderId='GPA.1', state='PROCESSED', createTime=o['order_date'],
                    total={'currencyCode': 'USD', 'units': '10'}, buyerAddress={'buyerCountry': 'VN'})
                main.ingest_order('app', payload)
                with main.database() as db:
                    db.execute('''INSERT INTO events(event_key,app_key,order_id,event_time,event_name,product_id,country_ip,environment,raw_json,received_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?)''', ('user-event', 'app', 'GPA.1', NOW, 'subscription_started', 'premium', 'VN', 'production',
                        json.dumps({'user_id': 'QON_saved', 'custom_user_id': '=UNSAFE()', 'identity_id': 'identity-saved', 'transaction': {'original_transaction_id': 'GPA.root'}}), NOW))
                main.export_sheets()
            tx = worksheets['Transactions']
            tx.resize.assert_called_once()
            data = tx.update.call_args.kwargs['values']
            self.assertEqual(data[1][data[0].index('Charged Amount')], 10)
            title_index = data[0].index('Product Title')
            self.assertEqual(data[1][title_index], "'=BAD()")
            self.assertEqual(tx.update.call_args.kwargs['value_input_option'], 'RAW')
            self.assertEqual(data[0][:3], ['App', 'User ID', 'Plan Type'])
            self.assertEqual(data[0][-1], 'Last Checked UTC')
            users_data = worksheets['Users'].update.call_args.kwargs['values']
            self.assertEqual(users_data[1][users_data[0].index('User ID')], 'QON_saved')
            self.assertEqual(users_data[1][users_data[0].index('Payment Count')], 1)
            self.assertEqual(users_data[1][users_data[0].index('Custom User IDs')], "'=UNSAFE()")
            description_data = worksheets['Description'].update.call_args.kwargs['values']
            self.assertEqual(len(description_data), 1 + sum(len(cols) for cols in main.SHEETS_HEADERS.values()))
            worksheets['Description'].resize.assert_called_once()
            sheet.batch_update.assert_called_once()
            formatting = sheet.batch_update.call_args.args[0]['requests']
            self.assertEqual(len([r for r in formatting if 'updateSheetProperties' in r]), len(main.EXPORT_HEADERS))
            self.assertEqual([r['updateSheetProperties']['properties']['index'] for r in formatting if 'updateSheetProperties' in r], list(range(len(main.EXPORT_HEADERS))))
            self.assertTrue(any(r.get('repeatCell', {}).get('cell', {}).get('userEnteredFormat', {}).get('numberFormat', {}).get('type') == 'PERCENT' for r in formatting))
            desc = [dict(zip(description_data[0], row)) for row in description_data[1:]]
            user_column = next(row for row in desc if row['Tab'] == 'Transactions' and row['Column'] == 'User ID')
            self.assertEqual(user_column['Column Letter'], 'B')
            self.assertEqual(users_data[0][:3], ['App', 'User ID', 'Payment Count'])


if __name__ == '__main__':
    unittest.main()