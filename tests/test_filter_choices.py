import json
import unittest
from unittest.mock import Mock

from app import main
from app.ga4_reports import DIMENSIONS, fetch_events
from app.grouping import ALL, default_filter_criteria
from app.reports import build_reports
from test_ua_reports import order, event, APP, NOW


class FilterChoicesTest(unittest.TestCase):
    def rows(self, orders, events):
        report = build_reports(orders, events, [], [APP], NOW, include_all=True)
        for tab, rows in report.items():
            for row in rows:
                self.assertEqual(len(row), len(main.SHEETS_HEADERS[tab]), tab)
        return {tab: [dict(zip(main.SHEETS_HEADERS[tab], r)) for r in rows] for tab, rows in report.items()}

    def test_dashboard_country_replaces_currency_and_all_counts_unique_users(self):
        vn, us = order('vn', trial=False), order('us', trial=False)
        us['country'], us['currency'] = 'US', 'VND'
        report = self.rows([vn, us], [event('vn'), event('us')])
        self.assertIn('Country (buyer)', main.EXPORT_HEADERS['Dashboard'])
        self.assertNotIn('Currency', main.EXPORT_HEADERS['Dashboard'])
        rows = {r['Country (buyer)']: r for r in report['Dashboard']}
        self.assertEqual(set(rows), {'VN', 'US', ALL})
        self.assertEqual(rows[ALL]['Observed Payers'], 1)
        self.assertEqual(rows[ALL]['Verified Payment Orders'], 2)
        self.assertEqual(rows[ALL]['Charged Amount (processed)'], 'USD: 10; VND: 10')

    def test_country_and_package_all_recompute_user_counts(self):
        vn, us = order('vn', trial=False), order('us', trial=False, base='monthly')
        us['country'] = 'US'
        report = self.rows([vn, us], [event('vn'), event('us')])
        total = next(r for r in report['Country_Performance'] if r['Country (buyer)'] == ALL)
        self.assertEqual(total['Paying Users'], 1)
        self.assertEqual(total['Total Revenue'], 20)
        self.assertEqual(total['ARPPU'], 20)
        total = next(r for r in report['Package_Performance'] if all(r[k] == ALL for k in ('Plan Type', 'Plan Identifier', 'Country (buyer)')))
        self.assertEqual((total['Paying Users'], total['Purchase Orders']), (1, 2))

    def test_trial_rate_is_weighted_not_summed_or_averaged(self):
        orders, events = [], []
        for i in range(3):
            t = order('trial' + str(i))
            t['country'] = 'VN' if i == 0 else 'US'
            orders.append(t)
            events.append(event(t['order_id'], user='user' + str(i), root='root' + str(i)))
        payment = order('paid', trial=False, start='2026-10-04T00:00:00Z')
        orders.append(payment)
        events.append(event('paid', user='user0', root='root0', name='trial_converted'))
        report = self.rows(orders, events)
        country = next(r for r in report['Country_Performance'] if r['Country (buyer)'] == ALL)
        self.assertEqual(country['Conversion Rate'], 1 / 3)
        cohort = next(r for r in report['Trial_Cohorts'] if all(r[k] == ALL for k in (
            'Trial Start Week UTC', 'Plan Type', 'Plan Identifier', 'Offer ID', 'Country (buyer)')))
        self.assertEqual(cohort['Trial to Paid 7d Rate'], 1 / 3)

    def test_retention_all_steps_does_not_sum_repeated_chain_revenue(self):
        orders = [order('start', trial=False), order('r1', trial=False, start='2026-10-08T00:00:00Z'),
                  order('r2', trial=False, start='2026-10-15T00:00:00Z')]
        events = [event('start', name='subscription_started'), event('r1', name='subscription_renewed'),
                  event('r2', name='subscription_renewed')]
        report = self.rows(orders, events)
        row = next(r for r in report['Cohort_Retention'] if all(r[k] == ALL for k in (
            'Cohort Month', 'Country (buyer)', 'User ID', 'Original Transaction ID', 'Plan Identifier', 'Renewal Number')))
        self.assertEqual((row['Renewal Users'], row['Renewal Orders']), (1, 2))
        self.assertEqual((row['Revenue at Step'], row['Total Revenue'], row['Renewal Revenue']), (30, 30, 20))

    def test_source_and_content_can_be_selected_independently(self):
        o = order('paid', trial=False)
        e = event('paid', name='subscription_started')
        e['raw_json'] = json.dumps({'properties': {'iap_data_type': 'theme', 'iap_data_id': 'kitty',
            'iap_data_name': 'Hello Kitty', 'iap_entry_source': 'home_banner'}})
        report = self.rows([o], [e])
        row = next(r for r in report['Theme_Performance'] if r['Data ID'] == 'kitty' and all(r[k] == ALL for k in (
            'Data Type', 'Data Name', 'Entry Source', 'Country (buyer)')))
        self.assertEqual(row['Total Revenue'], 10)
        self.assertEqual(report['RAW_Data'][0]['Row Type'], 'ORDER')
        self.assertEqual(len(report['RAW_Data']), 2)

    def test_initial_filters_show_only_total_scope(self):
        cols = ['App', 'Country (buyer)', 'Currency', 'Total Revenue']
        rows = [['app', 'VN', 'USD', 10], ['app', ALL, 'USD', 10]]
        self.assertEqual(default_filter_criteria('Country_Performance', cols, rows), {'1': {'hiddenValues': ['VN']}})
        self.assertEqual(default_filter_criteria('RAW_Data', cols, rows), {})

    def test_ga4_all_users_are_queried_instead_of_summed(self):
        session = Mock()
        def post(url, json, timeout):
            response = Mock()
            dims = [{'value': 'value'} for _ in json['dimensions']]
            response.json.return_value = {'rowCount': 1, 'rows': [{'dimensionValues': dims,
                'metricValues': [{'value': '10'}, {'value': '3'}]}]}
            return response
        session.post.side_effect = post
        rows = fetch_events([{**APP, 'ga4': {'property_id': '123'}}], session, include_all=True)
        self.assertEqual(session.post.call_count, 2 ** len(DIMENSIONS))
        total = next(r for r in rows if r[3:9] == [ALL] * 6)
        self.assertEqual(total[9:11], [10, 3])


if __name__ == '__main__':
    unittest.main()
