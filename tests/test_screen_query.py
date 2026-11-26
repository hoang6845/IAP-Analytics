import sqlite3
import unittest
from unittest.mock import Mock, patch
from app.screen_query import parse_controls, date_match, load_query, save_query, ensure_controls, TRANSACTION, ACQUISITION
from app.reports import build_reports
from app import main
import test_marketing_reports as fixtures
from test_ua_reports import APP, NOW


class ScreenQueryTest(unittest.TestCase):
    def fixture(self):
        return fixtures.MarketingReportsTest().fixture()

    def report(self, query):
        orders, events = self.fixture()
        return build_reports(orders, events, [], [APP], NOW, screen_query=query)

    def test_renewal_window_preserves_original_acquisition(self):
        baseline = self.report(None)
        filtered = self.report(dict(start='2026-10-11', end='2026-10-18', mode=TRANSACTION))
        headers = main.SHEETS_HEADERS['Screen_Performance']
        row = dict(zip(headers, filtered['Screen_Performance'][0]))
        self.assertEqual(row['Entry Source'], 'premium_day_night_theme')
        self.assertEqual(row['Total Revenue'], 20)
        self.assertEqual(row['Trial Users'], 0)
        for name in baseline:
            if name != 'Screen_Performance':
                self.assertEqual(filtered[name], baseline[name], name)

    def test_acquisition_window_excludes_old_chain_renewals(self):
        self.assertEqual(self.report(dict(start='2026-10-11', end='', mode=ACQUISITION))['Screen_Performance'], [])
        self.assertEqual(self.report(dict(start='2026-10-01', end='2026-10-01', mode=ACQUISITION))['Screen_Performance'], self.report(None)['Screen_Performance'])

    def test_empty_and_outside_windows(self):
        self.assertEqual(self.report(dict(start='',end='',mode=TRANSACTION))['Screen_Performance'],self.report(None)['Screen_Performance'])
        self.assertEqual(self.report(dict(start='2027-01-01',end='',mode=TRANSACTION))['Screen_Performance'],[])

    def test_local_day_boundaries(self):
        q=dict(start='2026-10-02',end='2026-10-02',mode=TRANSACTION)
        self.assertFalse(date_match('2026-10-01T16:59:59Z',q,'Asia/Bangkok'))
        self.assertTrue(date_match('2026-10-01T17:00:00Z',q,'Asia/Bangkok'))
        self.assertTrue(date_match('2026-10-02T16:59:59Z',q,'Asia/Bangkok'))
        self.assertFalse(date_match('2026-10-02T17:00:00Z',q,'Asia/Bangkok'))
        self.assertFalse(date_match(None,q,'Asia/Bangkok'))

    def test_invalid_controls_and_inclusive_date(self):
        def controls(start,end,mode=TRANSACTION):
            return [['Từ ngày',start,'Đến ngày',end,'Xem',True,'','Lọc theo',mode]]
        for start,end in [('2026-02-30',''),('2026-11-26','2026-11-25'),('26/11/2026',''),('20261126','')]:
            with self.assertRaises(ValueError):
                parse_controls(controls(start,end))
        self.assertEqual(parse_controls(controls('2026-11-26','2026-11-26'))['end'],'2026-11-26')
        with self.assertRaises(ValueError):
            parse_controls(controls('','','bad'))

    def test_query_persistence(self):
        from contextlib import closing
        with closing(sqlite3.connect(':memory:')) as db:
            self.assertIsNone(load_query(db))
            q=dict(start='2026-11-13',end='',mode=ACQUISITION)
            save_query(db,q)
            self.assertEqual(load_query(db),q)

    def test_existing_controls_preserve_user_edits(self):
        ws=Mock()
        ws.get.return_value=[['Từ ngày','2026-11-26']]
        ensure_controls(ws,None)
        ws.insert_row.assert_not_called()
        ws.spreadsheet.batch_update.assert_not_called()

    def test_action_worker_does_not_refresh_without_click(self):
        ws=Mock()
        ws.get.return_value=[['FALSE']]
        with patch.object(main,'creds'), patch.object(main.gspread,'authorize') as auth, patch.object(main,'export_sheets') as export:
            auth.return_value.open_by_key.return_value.worksheet.return_value=ws
            with patch.dict('os.environ',{'SHEET_ID':'test'}):
                main.screen_query_job()
            export.assert_not_called()
            ws.get.return_value=[['TRUE']]
            with patch.dict('os.environ',{'SHEET_ID':'test'}):
                main.screen_query_job()
            export.assert_called_once_with(screen_only=True,apply_screen_query=True)
        self.assertFalse(main.LOCK.locked())
