import unittest
from decimal import Decimal
from app.main import money, normalize_webhook, sheet_safe

class CoreTest(unittest.TestCase):
    def test_dedup_same_payload(self):
        p={'event_name':'subscription_renewed', 'transaction':{'transaction_id':'GPA.123'}, 'time':123456}
        self.assertEqual(normalize_webhook(p)[0], normalize_webhook(dict(p))[0])
    def test_distinct_events(self):
        a={'event_name':'subscription_renewed', 'transaction':{'transaction_id':'GPA.123'}}
        b={'event_name':'subscription_refunded', 'transaction':{'transaction_id':'GPA.123'}}
        self.assertNotEqual(normalize_webhook(a)[0], normalize_webhook(b)[0])
    def test_nano_currency(self):
        self.assertEqual(money({'currencyCode':'USD','units':'3','nanos':250000000}), ('USD','3.25'))
    def test_missing_money(self):
        self.assertEqual(money(None), ('',''))
    def test_formula_injection(self):
        self.assertEqual(sheet_safe('=IMPORTXML("http://x")'), "'=IMPORTXML(\"http://x\")")

if __name__=='__main__':
    unittest.main()
