"""Currency-preserving report values; no exchange rates or mixed-currency sums."""
from collections import defaultdict
from decimal import Decimal


def currency(order):
    return order.get('_report_currency', order.get('currency')) or 'UNKNOWN'


def format_amount(value, code):
    if value in ('', None, 'N/A'):
        return value
    amount = format(Decimal(str(value)), 'f').rstrip('0').rstrip('.') if '.' in str(value) else str(value)
    return f'{amount or "0"} {code or "UNKNOWN"}'


def format_parts(parts):
    return '; '.join(format_amount(value, code) for code, value in sorted(parts.items()) if value not in ('', None))


def sum_values(values):
    values = list(values)
    if not any(isinstance(v, str) and ' ' in v for v in values):
        return sum(values)
    totals = defaultdict(Decimal)
    for value in values:
        if value in ('', None):
            continue
        for part in value.split('; '):
            amount, code = part.rsplit(' ', 1)
            totals[code] += Decimal(amount)
    return format_parts(totals)
