import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import main


class WebhookAuthTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(main, 'DB', os.path.join(self.temp.name, 'test.sqlite3'))
        self.db_patch.start()
        self.env_patch = patch.dict(os.environ, {'WEBHOOK_TOKEN': 'a' * 32})
        self.env_patch.start()
        self.apps_patch = patch.object(main, 'config_apps', return_value=[{
            'key': 'cute_keyboard', 'package_name': 'com.example', 'qonversion_app_id': 'app1',
        }])
        self.apps_patch.start()
        main.init_db()
        self.client = TestClient(main.app)
        self.payload = {
            'event_name': 'subscription_started', 'environment': 'sandbox',
            'app_id': 'com.example', 'transaction': {'transaction_id': 'GPA.TEST'},
        }

    def tearDown(self):
        self.client.close()
        self.apps_patch.stop()
        self.env_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def post(self, headers):
        return self.client.post('/webhooks/qonversion/cute_keyboard', headers=headers, json=self.payload)

    def test_qonversion_header_accepts_and_preserves_duplicate_contract(self):
        for duplicate in (False, True):
            response = self.post({'Authorization-Token': 'a' * 32})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['accepted'])
            self.assertEqual(response.json()['duplicate'], duplicate)
        with main.database() as db:
            row = db.execute('SELECT app_key,order_id,event_name,environment FROM events').fetchone()
            self.assertEqual(tuple(row), ('cute_keyboard', 'GPA.TEST', 'subscription_started', 'sandbox'))
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 1)

    def test_documented_qonversion_basic_header(self):
        response = self.post({'Authorization': 'Basic ' + 'a' * 32})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['accepted'])
        with main.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 1)

    def test_invalid_authorization_does_not_fall_back(self):
        import base64
        for value in ('Basic wrong', 'Bearer ' + 'a' * 32, 'a' * 32, 'Basic ',
                      'Basic ' + base64.b64encode(('a' * 32).encode()).decode()):
            response = self.post({'Authorization': value, 'X-Webhook-Token': 'a' * 32})
            self.assertEqual(response.status_code, 401)
        with main.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 0)

    def test_existing_header_still_accepted(self):
        self.assertEqual(self.post({'X-Webhook-Token': 'a' * 32}).status_code, 200)

    def test_invalid_auth_never_saves_event(self):
        for headers in ({}, {'Authorization-Token': 'wrong'}, {'X-Webhook-Token': 'wrong'},
                        {'Authorization-Token': 'Bearer ' + 'a' * 32},
                        {'Authorization-Token': 'wrong', 'X-Webhook-Token': 'a' * 32}):
            self.assertEqual(self.post(headers).status_code, 401)
        with main.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 0)

    def test_short_configured_token_rejected(self):
        with patch.dict(os.environ, {'WEBHOOK_TOKEN': 'short'}):
            self.assertEqual(self.post({'Authorization-Token': 'short'}).status_code, 401)

    def test_project_id_is_not_store_app_id(self):
        self.payload['app_id'] = 'app1'
        self.assertEqual(self.post({'Authorization': 'Basic ' + 'a' * 32}).status_code, 422)
        with main.database() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 0)

    def test_missing_event_name_still_rejected(self):
        del self.payload['event_name']
        self.assertEqual(self.post({'Authorization': 'Basic ' + 'a' * 32}).status_code, 422)

    def test_app_validation_preserved(self):
        self.payload['app_id'] = 'different-app'
        self.assertEqual(self.post({'Authorization-Token': 'a' * 32}).status_code, 422)


if __name__ == '__main__':
    unittest.main()