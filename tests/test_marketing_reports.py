import json
import unittest
from unittest.mock import Mock

from app import main
from app.ga4_reports import fetch_events
from app.reports import build_reports
from test_ua_reports import order, event, APP, NOW


class MarketingReportsTest(unittest.TestCase):
    def build(self, orders, events, app=APP):
        report = build_reports(orders, events, [], [app], NOW)
        for tab, rows in report.items():
            for row in rows:
                self.assertEqual(len(row), len(main.SHEETS_HEADERS[tab]), tab)
        return {tab: [dict(zip(main.SHEETS_HEADERS[tab], r)) for r in rows] for tab, rows in report.items()}

    def fixture(self):
        orders = [order('trial'), order('convert', trial=False, start='2026-10-04T00:00:00Z'),
                  order('renew1', trial=False, start='2026-10-11T00:00:00Z'),
                  order('renew2', trial=False, start='2026-10-18T00:00:00Z')]
        events = []
        for o, name in zip(orders, ['trial_started', 'trial_converted', 'subscription_renewed', 'subscription_renewed']):
            e = event(o['order_id'], name=name)
            e['event_time'] = o['order_date']
            e['raw_json'] = json.dumps({'properties': {'iap_data_type': 'theme', 'iap_data_id': 'kitty',
                'iap_data_name': 'Hello Kitty', 'iap_entry_source': 'premium_day_night_theme'}})
            events.append(e)
        return orders, events

    def test_conversion_renewal_and_arppu_are_distinct(self):
        orders, events = self.fixture()
        events.append(dict(events[-1]))  # redelivery cannot create another payment/renewal
        result = self.build(orders, events)
        row = result['Country_Performance'][0]
        self.assertEqual((row['Trial Users'], row['Paying Users'], row['ARPPU']), (1, 1, 30))
        self.assertEqual((row['Mature Trials'], row['Converted Trials'], row['Conversion Rate']), (1, 1, 1))
        self.assertEqual((row['Total Revenue'], row['Conversion Revenue'], row['Renewal Revenue']), (30, 10, 20))
        steps = result['Cohort_Retention']
        self.assertEqual([r['Renewal Number'] for r in steps], [0, 1, 2])
        self.assertEqual([r['Renewal Orders'] for r in steps], [0, 1, 1])
        self.assertEqual(sum(r['Revenue at Step'] for r in steps), 30)
        self.assertEqual(result['Package_Performance'][0]['Purchase Orders'], 3)

    def test_acquisition_snapshot_wins_over_later_paywall_visit(self):
        orders, events = self.fixture()
        events[-1]['raw_json'] = json.dumps({'properties': {'iap_data_id': 'another-theme',
                                                          'iap_entry_source': 'setting_premium'}})
        result = self.build(orders, events)
        theme = result['Theme_Performance'][0]
        self.assertEqual((theme['Data ID'], theme['Total Revenue']), ('kitty', 30))
        self.assertEqual(result['Screen_Performance'][0]['Entry Source'], 'premium_day_night_theme')

    def test_partial_history_never_guesses_first_renewal(self):
        orders, events = self.fixture()
        result = self.build(orders[2:], events[2:])
        step = result['Cohort_Retention'][0]
        self.assertEqual(step['Renewal Number'], 'UNKNOWN')
        self.assertEqual(step['Renewal Orders'], 2)
        self.assertEqual(result['Theme_Performance'][0]['Data ID'], 'UNKNOWN')

    def test_provider_counter_works_without_acquisition_history(self):
        orders, events = self.fixture()
        events[-1]['raw_json'] = json.dumps({'subscription_renew_count': 8})
        result = self.build(orders[-1:], events[-1:])
        self.assertEqual(result['Cohort_Retention'][0]['Renewal Number'], 8)
        self.assertEqual(result['Cohort_Retention'][0]['Renewal Number Status'], 'PROVIDER_COUNTER')

    def test_retry_cancel_dates_and_sandbox_are_separate(self):
        orders, events = self.fixture()
        retry = event('renew2', name='subscription_billing_retry_entered')
        cancel = event('renew2', name='subscription_canceled')
        cancel['event_time'] = '2026-10-19T18:00:00Z'  # October 20 Bangkok
        events += [retry, dict(retry), cancel, event('renew2', env='sandbox', user='SANDBOX', name='subscription_billing_retry')]
        result = self.build(orders, events)
        row = result['Country_Performance'][0]
        self.assertEqual((row['Retry Users'], row['Retry Rate']), (1, 1))
        self.assertEqual(result['Screen_Performance'][0]['Cancel Users'], 1)
        day = next(r for r in result['Overview'] if r['Local Date'] == '2026-10-20')
        self.assertEqual(day['Canceled Subscriptions'], 1)
        self.assertEqual(day['Active Subscriptions'], 'N/A')
        self.assertEqual(day['Retry Rate'], 'N/A')
        self.assertTrue(any(r['Environment'] == 'sandbox' for r in result['RAW_Data']))
        self.assertTrue(all(r['Charged Amount'] == '' for r in result['RAW_Data'] if r['Row Type'] == 'EVENT'))

    def test_currencies_refunds_missing_money_and_identity_conflicts(self):
        orders, events = self.fixture()
        orders[-1]['currency'] = 'EUR'
        orders[-2]['state'] = 'REFUNDED'
        orders[-1]['charged'] = ''
        result = self.build(orders, events)
        by_cur = {r['Currency']: r for r in result['Country_Performance']}
        self.assertEqual(by_cur['USD']['Total Revenue'], 10)
        self.assertEqual(by_cur['EUR']['Missing Revenue Orders'], 1)
        events.append(event('convert', user='CONFLICT'))
        result = self.build(orders, events)
        raw = next(r for r in result['RAW_Data'] if r['Order ID'] == 'convert' and r['Row Type'] == 'ORDER')
        self.assertEqual(raw['User ID'], '')
        self.assertEqual(raw['Original Transaction ID'], '')

    def test_upgrade_requires_explicit_evidence(self):
        orders, events = self.fixture()
        orders[-1] = order('renew2', trial=False, base='monthly', start='2026-10-18T00:00:00Z')
        events[-1]['event_name'] = 'subscription_upgraded'
        events[-1]['product_id'] = 'premium:monthly'
        result = self.build(orders, events)
        self.assertEqual(result['Plan_Upgrades'][0]['From Plan'], 'premium:weekly')
        self.assertEqual(result['Plan_Upgrades'][0]['To Plan'], 'premium:monthly')
        events[-1]['event_name'] = 'subscription_started'
        self.assertEqual(self.build(orders, events)['Plan_Upgrades'], [])

    def test_all_export_columns_have_labels_and_documentation(self):
        from app.report_columns import MEANINGS, VI_LABELS, description_rows
        description_rows(main.EXPORT_HEADERS)
        for columns in main.EXPORT_HEADERS.values():
            for key in columns:
                self.assertIn(key, MEANINGS)
                self.assertIn(key, VI_LABELS)

    def test_lifetime_upgrade_uses_active_plan_context_and_distinct_chain(self):
        o = order('life', trial=False, base='', amount='50')
        o['product'] = 'premium_lifetime'
        o['payload'] = json.dumps({'lineItems': [{'productId': 'premium_lifetime', 'oneTimePurchaseDetails': {}}]})
        e = event('life', root='life-root', name='in_app_purchase')
        e['raw_json'] = json.dumps({'properties': {'iap_from_plan': 'weekly'}})
        row = self.build([o], [e])['Plan_Upgrades'][0]
        self.assertEqual((row['From Plan'], row['To Plan'], row['Upgrade Users']), ('WEEKLY', 'LIFETIME', 1))
        e['raw_json'] = json.dumps({'properties': {'iap_from_plan': 'none'}})
        self.assertEqual(self.build([o], [e])['Plan_Upgrades'], [])

    def test_provider_gap_invalidates_fallback_numbering(self):
        orders, events = self.fixture()
        events[2]['raw_json'] = json.dumps({'subscription_renew_count': 8})
        result = self.build(orders, events)
        steps = result['Cohort_Retention']
        self.assertIn(8, [r['Renewal Number'] for r in steps])
        self.assertIn('UNKNOWN', [r['Renewal Number'] for r in steps])
        self.assertNotIn(2, [r['Renewal Number'] for r in steps])


class Ga4ReportsTest(unittest.TestCase):
    def test_disabled_never_calls_network(self):
        session = Mock()
        rows = fetch_events([APP], session)
        session.post.assert_not_called()
        self.assertEqual(rows[0][-2], 'DISABLED')

    def test_pagination_and_distinct_users_on_whole_window(self):
        session = Mock()
        response = Mock()
        row = {'dimensionValues': [{'value': v} for v in ['Vietnam', 'theme', 'kitty', 'Hello Kitty', 'home', 'premium_item_tap']],
               'metricValues': [{'value': '10'}, {'value': '4'}]}
        response.json.side_effect = [{'rows': [row], 'rowCount': 2, 'metadata': {'subjectToThresholding': True}},
                                     {'rows': [row], 'rowCount': 2}]
        session.post.return_value = response
        rows = fetch_events([{**APP, 'ga4': {'property_id': '123'}}], session)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][9:11], [10, 4])
        self.assertIn('thresholding', rows[0][-1])
        self.assertEqual(session.post.call_args.kwargs['json']['offset'], 1)
        self.assertNotIn('date', [d['name'] for d in session.post.call_args.kwargs['json']['dimensions']])

    def test_failure_discards_partial_page_and_never_exposes_error_body(self):
        session = Mock()
        first = Mock()
        first.json.return_value = {'rows': [], 'rowCount': 5}
        session.post.return_value = first
        rows = fetch_events([{**APP, 'ga4': {'property_id': '123'}}], session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][-2], 'ERROR')
        self.assertEqual(rows[0][9:11], ['', ''])


if __name__ == '__main__':
    unittest.main()
