"""Optional GA4 aggregate import, isolated from financial verification."""
import re
from datetime import date, timedelta
from itertools import product
from app.grouping import ALL

SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
DIMENSIONS = ['country', 'customEvent:data_type', 'customEvent:data_id',
              'customEvent:data_name', 'customEvent:entry_source', 'eventName']
EVENTS = ['premium_item_tap', 'premium_item_dismiss', 'premium_item_purchase',
          'paywall_view', 'paywall_dismiss', 'paywall_purchase', 'premium_item_trial',
          'premium_item_converted', 'premium_item_renew', 'premium_item_cancel',
          'trial_started', 'trial_converted', 'subscription_renewed', 'subscription_canceled',
          'trial_canceled', 'trial_billing_retry', 'subscription_billing_retry']


def fetch_events(apps, session, today=None, include_all=False):
    """Paginate complete report windows; never sum daily distinct users.

    A failed property produces an ERROR status, never partial successful rows.
    """
    rows = []
    today = today or date.today()
    for app in apps:
        cfg = app.get('ga4') or {}
        prop = str(cfg.get('property_id') or '')
        start = str(cfg.get('start_date') or (today - timedelta(days=30)).isoformat())
        end = str(cfg.get('end_date') or 'yesterday')
        if not prop:
            rows.append([app['key'], start, end, '', '', '', '', '', '', '', '', 'DISABLED',
                         'Chưa cấu hình ga4.property_id; không có nghĩa event = 0.'])
            continue
        try:
            if not re.fullmatch(r'[0-9]+', prop):
                raise ValueError('ga4.property_id must be numeric')
            date.fromisoformat(start)
            if end not in ('yesterday', 'today'):
                date.fromisoformat(end)
            request = {
                'dateRanges': [{'startDate': start, 'endDate': end}],
                'dimensions': [{'name': d} for d in DIMENSIONS],
                'metrics': [{'name': 'eventCount'}, {'name': 'totalUsers'}],
                'dimensionFilter': {'filter': {'fieldName': 'eventName',
                    'inListFilter': {'values': EVENTS}}},
                'orderBys': [{'dimension': {'dimensionName': d}} for d in DIMENSIONS],
                'limit': 10000,
            }
            result = []
            notes = set()
            masks = product((True, False), repeat=len(DIMENSIONS)) if include_all else [(True,) * len(DIMENSIONS)]
            for mask in masks:
                selected = [d for d, keep in zip(DIMENSIONS, mask) if keep]
                scoped_request = {**request, 'dimensions': [{'name': d} for d in selected],
                                  'orderBys': [{'dimension': {'dimensionName': d}} for d in selected]}
                offset = 0
                while True:
                    response = session.post(f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport',
                                            json={**scoped_request, 'offset': offset}, timeout=60)
                    response.raise_for_status()
                    payload = response.json()
                    metadata = payload.get('metadata') or {}
                    if metadata.get('subjectToThresholding'):
                        notes.add('GA4 áp dụng thresholding; có thể thiếu dòng.')
                    if metadata.get('dataLossFromOtherRow'):
                        notes.add('GA4 có dòng (other); cardinality có thể mất chi tiết.')
                    if metadata.get('samplingMetadatas'):
                        notes.add('GA4 sampling: số liệu là ước tính.')
                    batch = payload.get('rows') or []
                    for row in batch:
                        dims = [v.get('value', '') for v in row.get('dimensionValues', [])]
                        metrics = [int(v['value']) for v in row['metricValues']]
                        if len(dims) != len(selected) or len(metrics) != 2:
                            raise ValueError('Unexpected GA4 response shape')
                        values = dict(zip(selected, dims))
                        result.append([app['key'], start, end, *[values.get(d, ALL) for d in DIMENSIONS], *metrics, 'OK', ''])
                    offset += len(batch)
                    if offset >= int(payload.get('rowCount', 0)):
                        break
                    if not batch:
                        raise ValueError('Incomplete GA4 pagination')
            note = 'User distinct theo từng dòng/cửa sổ; không SUM qua event. GA4 timezone có thể khác TZ báo cáo. ' + ' '.join(sorted(notes))
            if not result:
                result = [[app['key'], start, end, '', '', '', '', '', '', 0, 0, 'OK', 'Không có dòng event trong cửa sổ.']]
            for row in result:
                row[-1] += note
            rows.extend(result)
        except Exception:
            # Never export API error bodies or credentials to Sheets.
            rows.append([app['key'], start, end, '', '', '', '', '', '', '', '', 'ERROR',
                         'GA4 chưa lấy được: kiểm tra API, quyền Viewer, property ID, ngày và custom dimensions.'])
    return rows
