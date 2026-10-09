import json
import unittest
from app import main
from app.reports import build_reports
from app.report_columns import description_rows, column_letter

NOW = '2026-10-09T03:00:00Z'
APPS = [{'key': 'app', 'package_name': 'com.example'}]


def order(oid, state='PROCESSED', amount='10', currency='USD', app='app'):
    return dict(app_key=app, order_id=oid, state=state, order_date=NOW, country='VN',
        product='weekly', currency=currency, charged=amount, developer_revenue='7', checked_at=NOW,
        payload=json.dumps({'lineItems': [{'productId': 'weekly', 'subscriptionDetails': {}}]}))


def event(oid, user='QON_one', env='production', name='subscription_started', app='app'):
    return dict(app_key=app, order_id=oid, user_id=user, custom_user_id='account-1', identity_id='identity-1',
        environment=env, event_time=NOW, received_at=NOW, event_name=name, product_id='weekly', country_ip='VN')


class UserReportsTest(unittest.TestCase):
    def build(self, orders, events, apps=APPS):
        return build_reports(orders, events, [], apps, NOW)

    def rows(self, report, tab='Users'):
        return [dict(zip(main.SHEETS_HEADERS[tab], row)) for row in report[tab]]

    def test_retry_cancel_and_renewal_events_do_not_multiply_payments(self):
        report = self.build([order('GPA.1')], [event('GPA.1'), event('GPA.1'),
            event('GPA.1', name='subscription_renewed'), event('GPA.1', name='subscription_canceled')])
        user = self.rows(report)[0]
        self.assertEqual(user['Payment Count'], 1)
        self.assertEqual(user['Payment Order Face Amount (includes refunded)'], 10)
        self.assertEqual(user['Production Events (user, all currencies)'], 4)
        self.assertEqual(user['User ID'], 'QON_one')
        self.assertEqual(self.rows(report, 'Transactions')[0]['User Link Status'], 'MATCHED')

    def test_refunded_payments_count_but_pending_canceled_zero_and_missing_do_not(self):
        orders = [order('GPA.1'), order('GPA.2', state='REFUNDED'), order('GPA.3', state='PARTIALLY_REFUNDED'),
            order('GPA.4', state='PENDING_REFUND'), order('GPA.5', state='PENDING'),
            order('GPA.6', state='CANCELED'), order('GPA.7', amount='0'), order('GPA.8', amount='')]
        report = self.build(orders, [event(o['order_id']) for o in orders])
        user = self.rows(report)[0]
        self.assertEqual(user['Payment Count'], 4)
        self.assertEqual(user['Processed Paid Orders'], 1)
        self.assertEqual(user['Refunded Paid Orders'], 1)
        self.assertEqual(user['Payment Order Face Amount (includes refunded)'], 40)
        self.assertEqual(user['Charged Amount (processed)'], 10)
        self.assertEqual(user['Processed Zero Amount Orders'], 1)
        self.assertEqual(user['Total Verified Orders'], 8)

    def test_currencies_and_apps_are_separate_and_shared_identity_is_not_merged(self):
        orders = [order('GPA.1'), order('GPA.2', currency='VND', amount='25000'), order('GPA.3', app='other')]
        events = [event('GPA.1'), event('GPA.2'), event('GPA.3', app='other'), event('GPA.unverified', user='QON_two')]
        report = self.build(orders, events, APPS + [{'key': 'other', 'package_name': 'com.other'}])
        users = self.rows(report)
        self.assertEqual(len(users), 4)
        self.assertEqual({(u['App'], u['User ID'], u['Currency']) for u in users},
            {('app', 'QON_one', 'USD'), ('app', 'QON_one', 'VND'), ('other', 'QON_one', 'USD'), ('app', 'QON_two', '')})
        self.assertEqual(sum(u['Payment Count'] for u in users), 3)
        webhook_only = next(u for u in users if u['User ID'] == 'QON_two')
        self.assertEqual(webhook_only['User Link Status'], 'NO_VERIFIED_ORDERS')
        self.assertEqual(webhook_only['Charged Amount (processed)'], '')
        self.assertEqual(webhook_only['Non-Sandbox IDs Without Verified Order (user, all currencies)'], 1)

    def test_sandbox_does_not_attribute_orders_or_create_payments(self):
        report = self.build([order('GPA.1')], [event('GPA.1', env='sandbox')])
        users = self.rows(report)
        identified = next(u for u in users if u['User ID'])
        missing = next(u for u in users if not u['User ID'])
        self.assertEqual(identified['Payment Count'], 0)
        self.assertEqual(identified['Sandbox/Test Events (user, all currencies)'], 1)
        self.assertEqual(missing['User Link Status'], 'MISSING_USER_ID')
        self.assertEqual(self.rows(report, 'Transactions')[0]['User ID'], '')

    def test_conflicting_user_ids_never_assign_payment_to_either_user(self):
        report = self.build([order('GPA.1')], [event('GPA.1'), event('GPA.1', user='QON_two')])
        users = self.rows(report)
        self.assertEqual(sum(u['Payment Count'] for u in users if u['User ID']), 0)
        unassigned = next(u for u in users if not u['User ID'])
        self.assertEqual(unassigned['User Link Status'], 'CONFLICTING_USERS')
        self.assertEqual(unassigned['Payment Count'], 1)
        self.assertEqual(self.rows(report, 'Transactions')[0]['User Link Status'], 'CONFLICTING_USERS')

    def test_every_column_is_documented_including_description_itself(self):
        rows = description_rows(main.SHEETS_HEADERS)
        expected = {(tab, col) for tab, columns in main.SHEETS_HEADERS.items() for col in columns}
        self.assertEqual({(row[0], row[1]) for row in rows}, expected)
        self.assertEqual(len(rows), sum(len(cols) for cols in main.SHEETS_HEADERS.values()))
        self.assertTrue(all(len(row) == 8 and row[3] and row[4] and row[5] for row in rows))
        self.assertEqual(column_letter(27), 'AA')
        self.assertEqual(column_letter(43), 'AQ')
        users = self.rows(self.build([order('GPA.1')], [event('GPA.1')]))
        self.assertEqual(len(users[0]), len(main.SHEETS_HEADERS['Users']))


if __name__ == '__main__':
    unittest.main()