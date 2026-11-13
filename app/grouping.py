"""Explicit aggregate choices for native Google Sheets column filters."""
from collections import defaultdict
from itertools import product

ALL = 'Tất cả'


def expand_groups(groups, axes):
    """Build each grouping from original records, never aggregate other rollups.

    Currency and app are deliberately not collapsed here. Related identity/name
    columns can share one axis, so an ID is not detached from its name.
    """
    result = defaultdict(list)
    for key, records in groups.items():
        targets = set()
        for flags in product((False, True), repeat=len(axes)):
            target = list(key)
            for enabled, positions in zip(flags, axes):
                if enabled:
                    for position in positions:
                        target[position] = ALL
            targets.add(tuple(target))
        for target in targets:
            result[target].extend(records)
    return result


def retention_choices(rows, headers):
    """Retention totals deduplicate repeated chain totals and distinct users."""
    groups = defaultdict(list)
    dimensions = ['App', 'Cohort Month', 'Country (buyer)', 'User ID',
                  'Original Transaction ID', 'Plan Identifier', 'Currency', 'Renewal Number']
    for row in rows:
        values = dict(zip(headers, row))
        groups[tuple(values[c] for c in dimensions)].append(values)
    expanded = expand_groups(groups, [(1,), (2,), (3,), (4,), (5,), (7,)])
    result = []
    for key, members in expanded.items():
        if ALL not in key:
            continue
        out = dict(zip(dimensions, key))
        out['Renewal Users'] = len({(m['App'], m['User ID']) for m in members if m['Renewal Orders']})
        out['Renewal Orders'] = sum(m['Renewal Orders'] for m in members)
        out['Revenue at Step'] = sum(m['Revenue at Step'] for m in members)
        # These values are repeated per renewal step in the detailed report.
        chains = {tuple(m[c] for c in dimensions[:-1]): m for m in members}
        for column in ('Total Revenue', 'Renewal Revenue', 'Conversion Revenue', 'Other Revenue'):
            out[column] = sum(m[column] for m in chains.values())
        out['Renewal Number Status'] = ('UNKNOWN_HISTORY' if any(m['Renewal Number Status'] == 'UNKNOWN_HISTORY' for m in members)
                                        else 'AVAILABLE')
        out['Notes'] = 'Tổng hợp từ dữ liệu gốc; user distinct, tổng chuỗi không cộng lặp theo bước. Chọn một phạm vi chi tiết hoặc Tất cả, không SUM chồng nhau.'
        result.append([out.get(c, '') for c in headers])
    return rows + sorted(result, key=lambda r: tuple(str(v) for v in r[:8]))


def trial_choices(rows, headers):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[:7])].append(dict(zip(headers, row)))
    result = []
    for key, members in expand_groups(groups, [(1,), (2,), (3,), (4,), (5,)]).items():
        if ALL not in key:
            continue
        out = dict(zip(headers[:7], key))
        for column in headers[7:13]:
            out[column] = sum(m[column] for m in members)
        available = all(m['Conversion Rate Status'] == 'AVAILABLE' for m in members)
        mature = out['Mature Trial Episodes (7d after end)']
        out['Trial to Paid 7d Rate'] = out['Verified Conversions within 7d after Trial End'] / mature if mature and available else 'N/A'
        out['Conversion Rate Status'] = 'AVAILABLE' if mature and available else 'INCOMPLETE_OR_IMMATURE_COHORTS'
        out['History Coverage Start UTC'] = members[0]['History Coverage Start UTC']
        out['Notes'] = 'Tổng hợp các kỳ trial gốc; tỷ lệ được tính lại theo mẫu số, không cộng/trung bình các tỷ lệ.'
        result.append([out.get(c, '') for c in headers])
    return rows + sorted(result, key=lambda r: tuple(str(v) for v in r[:7]))


# Raw/log/dictionary tabs use native Select all, retaining individual records.
# Currency remains explicit; it is not an additive grouping across currencies.
FILTER_DIMENSIONS = {
    'Dashboard': ['Country (buyer)'],
    'Overview': ['Local Date'],
    'Country_Performance': ['Country (buyer)'],
    'Country_Analysis': ['Country (buyer)'],
    'Package_Performance': ['Plan Type', 'Plan Identifier', 'Country (buyer)'],
    'Plan_Comparison': ['Plan Type', 'Plan Identifier', 'Offer ID', 'Country (buyer)'],
    'Product_Analysis': ['Product', 'Plan Type', 'Plan Identifier'],
    'Trial_Cohorts': ['Trial Start Week UTC', 'Plan Type', 'Plan Identifier', 'Offer ID', 'Country (buyer)'],
    'Cohort_Retention': ['Cohort Month', 'Country (buyer)', 'User ID', 'Original Transaction ID', 'Plan Identifier', 'Renewal Number'],
    'Plan_Upgrades': ['Country (buyer)', 'From Plan', 'To Plan'],
    'Theme_Performance': ['Data Type', 'Data ID', 'Data Name', 'Entry Source', 'Country (buyer)'],
    'Screen_Performance': ['Entry Source', 'Country (buyer)'],
    'Firebase_Events': ['Country (GA4)', 'Data Type', 'Data ID', 'Data Name', 'Entry Source', 'Event'],
}


def default_filter_criteria(name, columns, rows):
    """Initially display the all-selection scope, hiding overlapping detail rows."""
    criteria = {}
    for column in FILTER_DIMENSIONS.get(name, []):
        if column not in columns:
            continue
        index = columns.index(column)
        choices = {str(row[index]) for row in rows}
        if ALL in choices:
            criteria[str(index)] = {'hiddenValues': sorted(choices - {ALL})}
    return criteria
