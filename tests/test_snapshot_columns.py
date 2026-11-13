import unittest

from app.report_columns import snapshot_headers


class SnapshotColumnsTest(unittest.TestCase):
    def test_only_unavailable_columns_are_removed_and_can_return(self):
        headers = {'Report': ['Country', 'Rate', 'Pending', 'Count', 'Partial']}
        tables = {'Report': [['UNKNOWN', 'N/A', '', 0, 'N/A'],
                             ['VN', 'N/A', None, 0, 0.5]]}
        original = [row[:] for row in tables['Report']]
        self.assertEqual(snapshot_headers(headers, headers, tables)['Report'],
                         ['Country', 'Pending', 'Count', 'Partial'])
        self.assertEqual(tables['Report'], original)
        tables['Report'][0][1] = 0
        self.assertEqual(snapshot_headers(headers, headers, tables), headers)

    def test_empty_tabs_and_unconfigured_sources_keep_their_columns(self):
        headers = {'Empty': ['Plan', 'Users'], 'GA4': ['Event', 'Users', 'Status']}
        self.assertEqual(snapshot_headers(headers, headers,
                                         {'Empty': [], 'GA4': [['', '', 'DISABLED']]}), headers)


if __name__ == '__main__':
    unittest.main()
