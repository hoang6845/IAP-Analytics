import json
import unittest
from app import main
from app.reports import build_reports

NOW = '2026-10-20T00:00:00Z'
APP = {'key': 'app', 'package_name': 'com.example', 'analytics_coverage_start_utc': '2026-10-01T00:00:00Z'}


def order(oid, start='2026-10-01T00:00:00Z', end='2026-10-04T00:00:00Z', trial=True, amount=None, currency='USD', base='weekly', state='PROCESSED'):
    phase = {'freeTrialDetails': {}} if trial else {'baseDetails': {}}
    payload = {'lineItems': [{'productId': 'premium', 'subscriptionDetails': {'basePlanId': base,
        'offerId': 'free-trial-7days', 'servicePeriodStartTime': start, 'servicePeriodEndTime': end,
        'offerPhaseDetails': phase}}]}
    return dict(app_key='app', order_id=oid, order_date=start, checked_at=NOW, country='VN',
        product='premium', currency=currency, charged=amount if amount is not None else '0' if trial else '10',
        developer_revenue='0' if trial else '7', state=state, payload=json.dumps(payload))


def event(oid, user='QON_1', root='GPA.root', env='production', name='trial_started'):
    return dict(app_key='app', order_id=oid, user_id=user, original_transaction_id=root, event_name=name,
        environment=env, event_time='2026-10-01T00:00:00Z', received_at=NOW, product_id='premium:weekly', country_ip='VN')


class UaReportsTest(unittest.TestCase):
    def build(self, orders, events, app=APP):
        return build_reports(orders, events, [], [app], NOW)

    def rows(self, report, name):
        return [dict(zip(main.SHEETS_HEADERS[name], row)) for row in report[name]]

    def test_dashboard_separates_trial_from_payers_and_stays_compact(self):
        orders = [order('GPA.'+str(i)) for i in range(7)] + [order('GPA.paid', trial=False)]
        events = [event(o['order_id'], user='QON_'+str(i)) for i, o in enumerate(orders)]
        report = self.build(orders, events)
        row = self.rows(report, 'Dashboard')[0]
        self.assertEqual(len(report['Dashboard']), 1)
        self.assertEqual(row['Observed Payers'], 1)
        self.assertEqual(row['Verified Payment Orders'], 1)
        self.assertEqual(row['Trial Orders'], 7)
        self.assertEqual(row['Observed Users'], 8)
        self.assertEqual(row['Charged Amount (processed)'], 10)
        self.assertGreater(len(report['Diagnostics']), len(report['Dashboard']))

    def test_mature_cohort_conversion_matches_user_chain_plan_and_not_event_count(self):
        orders = [order('GPA.trial'), order('GPA.paid', start='2026-10-05T00:00:00Z', trial=False)]
        events = [event('GPA.trial'), event('GPA.paid', name='trial_converted'), event('GPA.paid', name='trial_converted')]
        row = self.rows(self.build(orders, events), 'Trial_Cohorts')[0]
        self.assertEqual(row['Observed Trial Episodes'], 1)
        self.assertEqual(row['Mature Trial Episodes (7d after end)'], 1)
        self.assertEqual(row['Verified Conversions within 7d after Trial End'], 1)
        self.assertEqual(row['Trial to Paid 7d Rate'], 1)
        self.assertEqual(row['Conversion Rate Status'], 'AVAILABLE')

    def test_missing_history_hides_rate_but_shows_observed_counts(self):
        row = self.rows(self.build([order('GPA.trial')], [event('GPA.trial')],
            app={'key': 'app', 'package_name': 'com.example'}), 'Trial_Cohorts')[0]
        self.assertEqual(row['Trial to Paid 7d Rate'], 'N/A')
        self.assertEqual(row['Conversion Rate Status'], 'HISTORY_COVERAGE_NOT_CONFIRMED')

    def test_immature_trial_never_enters_denominator(self):
        row = self.rows(self.build([order('GPA.trial', start='2026-10-18T00:00:00Z', end='2026-10-21T00:00:00Z')],
            [event('GPA.trial')]), 'Trial_Cohorts')[0]
        self.assertEqual(row['Mature Trial Episodes (7d after end)'], 0)
        self.assertEqual(row['Immature Trial Episodes'], 1)
        self.assertEqual(row['Trial to Paid 7d Rate'], 'N/A')

    def test_unrelated_or_late_payment_not_a_trial_conversion(self):
        for root, user, base, start in [('GPA.other', 'QON_1', 'weekly', '2026-10-05T00:00:00Z'),
                ('GPA.root', 'QON_2', 'weekly', '2026-10-05T00:00:00Z'),
                ('GPA.root', 'QON_1', 'yearly', '2026-10-05T00:00:00Z'),
                ('GPA.root', 'QON_1', 'weekly', '2026-10-12T00:00:00Z')]:
            with self.subTest(root=root, user=user, base=base, start=start):
                report = self.build([order('GPA.trial'), order('GPA.paid', trial=False, base=base, start=start)],
                    [event('GPA.trial'), event('GPA.paid', root=root, user=user)])
                row = self.rows(report, 'Trial_Cohorts')[0]
                self.assertEqual(row['Verified Conversions within 7d after Trial End'], 0)

    def test_missing_chain_unknown_environment_and_conflicting_users_hide_rate(self):
        scenarios = [[event('GPA.trial', root='')], [event('GPA.trial', env='')],
            [event('GPA.trial'), event('GPA.trial', user='QON_2')]]
        for events in scenarios:
            row = self.rows(self.build([order('GPA.trial')], events), 'Trial_Cohorts')[0]
            self.assertEqual(row['Missing Chain Episodes'], 1)
            self.assertEqual(row['Trial to Paid 7d Rate'], 'N/A')

    def test_payment_after_next_trial_not_credited_to_previous_trial(self):
        orders = [order('GPA.first'), order('GPA.second', start='2026-10-05T00:00:00Z', end='2026-10-08T00:00:00Z'),
            order('GPA.paid', start='2026-10-09T00:00:00Z', trial=False)]
        report = self.build(orders, [event(o['order_id']) for o in orders])
        rows = self.rows(report, 'Trial_Cohorts')
        self.assertEqual(sum(r['Verified Conversions within 7d after Trial End'] for r in rows), 1)
        self.assertEqual(rows[0]['Verified Conversions within 7d after Trial End'], 0)

    def test_overlapping_trials_hide_rate(self):
        orders = [order('GPA.first'), order('GPA.second', start='2026-10-02T00:00:00Z', end='2026-10-05T00:00:00Z')]
        row = self.rows(self.build(orders, [event(o['order_id']) for o in orders]), 'Trial_Cohorts')[0]
        self.assertEqual(row['Trial to Paid 7d Rate'], 'N/A')
        self.assertEqual(row['Conversion Rate Status'], 'INCOMPLETE_TRIAL_LINK_OR_TIMES')

    def test_currency_and_sandbox_separation_and_renewal_requires_paid_order(self):
        orders = [order('GPA.trial'), order('GPA.paid', trial=False), order('GPA.vnd', trial=False, amount='25000', currency='VND')]
        events = [event('GPA.trial', name='subscription_renewed'), event('GPA.paid', name='subscription_renewed'),
            event('GPA.vnd', name='subscription_renewed', env='sandbox')]
        report = self.build(orders, events)
        rows = {r['Currency']: r for r in self.rows(report, 'Dashboard')}
        self.assertEqual(rows['USD']['Verified Renewal Payment Orders'], 1)
        self.assertEqual(rows['USD']['Observed Payers'], 1)
        self.assertEqual(rows['VND']['Observed Payers'], 0)
        self.assertEqual(rows['VND']['Unattributed Verified Orders'], 1)
        self.assertEqual(rows['VND']['Charged Amount (processed)'], 25000)
        timeline = self.rows(report, 'User_Timeline')
        self.assertTrue(all(r['Charged Amount'] == '' for r in timeline if r['Row Type'] == 'EVENT'))
        self.assertTrue(any(r['Environment'] == 'sandbox' for r in timeline))

    def test_offer_duration_warning_and_empty_dashboard_are_explicit(self):
        report = self.build([order('GPA.trial')], [event('GPA.trial')])
        quality = self.rows(report, 'Data_Quality')
        self.assertTrue(any(r['Issue'] == 'OFFER_NAME_VS_TRIAL_DURATION' for r in quality))
        empty = self.rows(self.build([], []), 'Dashboard')[0]
        self.assertEqual(empty['Observed Payers'], 0)
        self.assertEqual(empty['Charged Amount (processed)'], '')


if __name__ == '__main__':
    unittest.main()