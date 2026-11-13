import copy
import unittest

from app import main
from app.grouping import ALL
from app.reports import build_reports
from test_ua_reports import APP, NOW, order, event


class CountryCurrencyTest(unittest.TestCase):
    def report(self, orders, events):
        tables = build_reports(orders, events, [], [APP], NOW,
                              include_all=True, combine_currencies=True)
        for tab, rows in tables.items():
            for row in rows:
                self.assertEqual(len(row), len(main.SHEETS_HEADERS[tab]), tab)
        return {tab: [dict(zip(main.SHEETS_HEADERS[tab], row)) for row in rows]
                for tab, rows in tables.items()}

    def fixture(self):
        usd, vnd, other = order('usd', trial=False), order('vnd', trial=False), order('other', trial=False)
        usd['country'] = vnd['country'] = 'VN'
        vnd['currency'], vnd['charged'] = 'VND', '250000'
        other['country'] = 'US'
        return [usd, vnd, other], [event('usd'), event('vnd'), event('other')]

    def test_country_combines_currency_but_deduplicates_users(self):
        orders, events = self.fixture()
        before = copy.deepcopy(orders)
        result = self.report(orders, events)
        self.assertEqual(orders, before)
        vn = [r for r in result['Country_Performance'] if r['Country (buyer)'] == 'VN']
        self.assertEqual(len(vn), 1)
        self.assertEqual(vn[0]['Paying Users'], 1)
        self.assertEqual(vn[0]['Total Revenue'], '10 USD; 250000 VND')
        self.assertEqual(vn[0]['ARPPU'], '10 USD; 250000 VND')
        total = next(r for r in result['Country_Performance'] if r['Country (buyer)'] == ALL)
        self.assertEqual(total['Paying Users'], 1)
        self.assertEqual(total['Total Revenue'], '20 USD; 250000 VND')
        comparison = next(r for r in result['Plan_Comparison'] if all(r[k] == ALL for k in
                          ('Country (buyer)', 'Plan Type', 'Plan Identifier', 'Offer ID')))
        self.assertEqual(comparison['Observed Payers'], 1)
        self.assertEqual(comparison['Verified Payment Orders'], 3)
        self.assertEqual(comparison['Charged Amount (processed)'], '20 USD; 250000 VND')

    def test_overview_country_all_includes_all_currencies(self):
        result = self.report(*self.fixture())
        rows = [r for r in result['Overview'] if r['Local Date'] == 'ALL']
        self.assertEqual({r['Country (buyer)'] for r in rows}, {'VN', 'US', ALL})
        total = next(r for r in rows if r['Country (buyer)'] == ALL)
        self.assertEqual(total['Paying Users'], 1)
        self.assertEqual(total['Total Revenue'], '20 USD; 250000 VND')
        vn = next(r for r in rows if r['Country (buyer)'] == 'VN')
        self.assertEqual(vn['Total Revenue'], '10 USD; 250000 VND')

    def test_retention_preserves_money_and_chain_totals_across_steps(self):
        orders, events = self.fixture()
        for e in events:
            e['event_name'] = 'subscription_renewed'
        result = self.report(orders, events)
        total = next(r for r in result['Cohort_Retention'] if all(r[k] == ALL for k in (
            'Cohort Month', 'Country (buyer)', 'User ID', 'Original Transaction ID', 'Plan Identifier', 'Renewal Number')))
        self.assertEqual(total['Renewal Users'], 1)
        self.assertEqual(total['Renewal Orders'], 3)
        self.assertEqual(total['Total Revenue'], '20 USD; 250000 VND')
        self.assertEqual(total['Revenue at Step'], '20 USD; 250000 VND')

    def test_raw_and_user_money_retains_original_currency(self):
        result = self.report(*self.fixture())
        raw = {r['Order ID']: r for r in result['RAW_Data'] if r['Row Type'] == 'ORDER'}
        self.assertEqual(raw['vnd']['Charged Amount'], '250000 VND')
        self.assertEqual(raw['usd']['Charged Amount'], '10 USD')
        user = next(r for r in result['Users'] if r['Country (buyer)'] == ALL)
        self.assertEqual(user['Payment Count'], 3)
        self.assertEqual(user['Charged Amount (processed)'], '20 USD; 250000 VND')
        self.assertTrue(all('Currency' not in cols for cols in main.EXPORT_HEADERS.values()))
        for tab in ('Overview', 'Country_Performance', 'Product_Analysis', 'Users', 'User_Timeline'):
            self.assertIn('Country (buyer)', main.EXPORT_HEADERS[tab])

    def test_trial_rates_use_episodes_and_overview_lifecycle_is_not_doubled(self):
        orders = [order('trial-usd'), order('trial-vnd', currency='VND'),
                  order('converted', trial=False, start='2026-10-04T00:00:00Z')]
        events = [event('trial-usd', root='root1'), event('trial-vnd', root='root2'),
                  event('converted', root='root1', name='trial_converted')]
        result = self.report(orders, events)
        vn = next(r for r in result['Country_Performance'] if r['Country (buyer)'] == 'VN')
        self.assertEqual(vn['Trial Users'], 1)
        self.assertEqual((vn['Mature Trials'], vn['Converted Trials'], vn['Conversion Rate']), (2, 1, 0.5))
        total = next(r for r in result['Overview'] if r['Local Date'] == 'ALL' and r['Country (buyer)'] == ALL)
        self.assertEqual(total['Observed Subscription Chains'], 2)
        self.assertEqual(total['New Subscriptions'], 2)

    def test_refunds_missing_amounts_and_zero_keep_their_meaning(self):
        orders = [order('zero', trial=False, amount='0'),
                  order('refund', trial=False, state='REFUNDED', currency='VND'),
                  order('missing', trial=False)]
        orders[2]['charged'] = ''
        result = self.report(orders, [event(o['order_id']) for o in orders])
        vn = next(r for r in result['Country_Performance'] if r['Country (buyer)'] == 'VN')
        self.assertEqual(vn['Paying Users'], 1)
        self.assertEqual(vn['Total Revenue'], '0 USD; 0 VND')
        self.assertEqual(vn['Missing Revenue Orders'], 1)
        raw = next(r for r in result['RAW_Data'] if r['Row Type'] == 'ORDER' and r['Order ID'] == 'missing')
        self.assertEqual(raw['Charged Amount'], '')

    def test_webhook_only_users_are_in_all_countries_scope(self):
        orders, events = self.fixture()
        events.append(event('unverified', user='new-user'))
        result = self.report(orders, events)
        user = next(r for r in result['Users'] if r['User ID'] == 'new-user' and r['Country (buyer)'] == ALL)
        self.assertEqual(user['Payment Count'], 0)
        self.assertEqual(user['Charged Amount (processed)'], '')


if __name__ == '__main__':
    unittest.main()
