import os
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app import main


class ManualSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(main, 'DB', os.path.join(self.temp.name, 'test.sqlite3'))
        self.db_patch.start()
        self.env_patch = patch.dict(os.environ, {'WEBHOOK_TOKEN': 'a' * 32})
        self.env_patch.start()
        main.init_db()

    def tearDown(self):
        self.env_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def test_auth_rejects_before_sync(self):
        with patch.object(main, 'sync_job') as job:
            for token in (None, 'wrong'):
                with self.assertRaises(HTTPException) as error:
                    main.manual_sync(token)
                self.assertEqual(error.exception.status_code, 401)
            job.assert_not_called()

    def test_short_configured_token_rejected(self):
        with patch.dict(os.environ, {'WEBHOOK_TOKEN': 'short'}):
            with self.assertRaises(HTTPException) as error:
                main.manual_sync('short')
            self.assertEqual(error.exception.status_code, 401)

    def test_success_runs_play_and_sheets(self):
        with patch.object(main, 'sync_orders', return_value='Checked 1') as play, patch.object(main, 'export_sheets', return_value='Exported 1') as sheets:
            result = main.manual_sync('a' * 32)
        self.assertEqual(result, {'status': 'ok', 'detail': 'Checked 1; Exported 1'})
        play.assert_called_once_with()
        sheets.assert_called_once_with()
        with main.database() as db:
            self.assertEqual(db.execute('SELECT result FROM sync_log').fetchone()[0], 'OK_PLAY')
        self.assertFalse(main.LOCK.locked())

    def test_concurrent_sync_returns_conflict_without_work(self):
        main.LOCK.acquire()
        try:
            with patch.object(main, 'sync_orders') as play, patch.object(main, 'export_sheets') as sheets:
                with self.assertRaises(HTTPException) as error:
                    main.manual_sync('a' * 32)
                self.assertEqual(error.exception.status_code, 409)
                play.assert_not_called()
                sheets.assert_not_called()
        finally:
            main.LOCK.release()

    def test_failure_reports_error_logs_and_releases_lock(self):
        with patch.object(main, 'sync_orders', side_effect=RuntimeError('Play failed')), patch.object(main, 'export_sheets') as sheets:
            with self.assertRaises(HTTPException) as error:
                main.manual_sync('a' * 32)
            self.assertEqual(error.exception.status_code, 500)
            sheets.assert_not_called()
        with main.database() as db:
            self.assertEqual(db.execute('SELECT result,detail FROM sync_log').fetchone()[:], ('ERROR', 'Play failed'))
        self.assertFalse(main.LOCK.locked())

    def test_export_failure_is_not_reported_as_success(self):
        with patch.object(main, 'sync_orders', return_value='Checked 1'), patch.object(main, 'export_sheets', side_effect=RuntimeError('Sheets failed')):
            with self.assertRaises(HTTPException) as error:
                main.manual_sync('a' * 32)
            self.assertEqual(error.exception.status_code, 500)
        self.assertFalse(main.LOCK.locked())

    def test_page_does_not_embed_secret(self):
        response = main.sync_page()
        self.assertNotIn(b'a' * 32, response.body)
        self.assertIn(b'/admin/sync', response.body)
        self.assertEqual(response.headers['cache-control'], 'no-store')


if __name__ == '__main__':
    unittest.main()
