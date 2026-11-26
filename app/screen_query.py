"""One-row, persistent date controls for Screen_Performance."""
import json
from datetime import date
from zoneinfo import ZoneInfo

TRANSACTION = 'Ngày giao dịch'
ACQUISITION = 'Ngày mua/trial đầu chuỗi'


def parse_controls(values):
    row = (values[0] if values else []) + [''] * 9
    start, end, mode = str(row[1]).strip(), str(row[3]).strip(), row[8] or TRANSACTION
    for value in (start, end):
        if value:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError('Dùng định dạng YYYY-MM-DD')
    if start and end and start > end:
        raise ValueError('Từ ngày phải nhỏ hơn hoặc bằng Đến ngày')
    if mode not in (TRANSACTION, ACQUISITION):
        raise ValueError('Kiểu lọc không hợp lệ')
    return dict(start=start, end=end, mode=mode)


def date_match(value, query, tz):
    from app.reports import timestamp
    if not query or not (query.get('start') or query.get('end')):
        return True
    stamp = timestamp(value)
    if stamp is None:
        return False
    day = stamp.astimezone(ZoneInfo(tz)).date().isoformat()
    return (not query.get('start') or day >= query['start']) and (not query.get('end') or day <= query['end'])


def load_query(db):
    db.execute('CREATE TABLE IF NOT EXISTS report_queries (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
    row = db.execute("SELECT value FROM report_queries WHERE name='Screen_Performance'").fetchone()
    return json.loads(row[0]) if row else None


def save_query(db, query):
    load_query(db)
    db.execute("INSERT OR REPLACE INTO report_queries(name,value) VALUES('Screen_Performance',?)", (json.dumps(query),))


def ensure_controls(ws, query):
    row = ws.get('A1:I1')
    if row and row[0] and row[0][0] == 'Từ ngày':
        return
    ws.insert_row(['Từ ngày', (query or {}).get('start', ''), 'Đến ngày', (query or {}).get('end', ''),
                   'Xem ▶', False, 'Chọn ngày YYYY-MM-DD rồi bấm ô F1; xử lý trong khoảng 15 giây.',
                   'Lọc theo', (query or {}).get('mode', TRANSACTION)], index=1, value_input_option='RAW')
    sid=ws.id
    ws.spreadsheet.batch_update({'requests': [
        {'setDataValidation': {'range': {'sheetId':sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':5,'endColumnIndex':6},
            'rule': {'condition': {'type':'BOOLEAN'},'strict':True,'showCustomUi':True}}},
        {'setDataValidation': {'range': {'sheetId':sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':8,'endColumnIndex':9},
            'rule': {'condition': {'type':'ONE_OF_LIST','values':[{'userEnteredValue':TRANSACTION},{'userEnteredValue':ACQUISITION}]},'strict':True,'showCustomUi':True}}},
        {'repeatCell': {'range': {'sheetId':sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':13},
            'cell': {'userEnteredFormat': {'backgroundColor':{'red':0.88,'green':0.95,'blue':0.9},'wrapStrategy':'WRAP','textFormat':{'bold':True}}},'fields':'userEnteredFormat'}},
        {'updateDimensionProperties': {'range': {'sheetId':sid,'dimension':'ROWS','startIndex':0,'endIndex':1},'properties':{'pixelSize':64},'fields':'pixelSize'}},
        {'repeatCell': {'range': {'sheetId':sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'TEXT'}}},'fields':'userEnteredFormat.numberFormat'}},
        {'repeatCell': {'range': {'sheetId':sid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':3,'endColumnIndex':4},'cell':{'userEnteredFormat':{'numberFormat':{'type':'TEXT'}}},'fields':'userEnteredFormat.numberFormat'}},
    ]})


def pending(ws):
    value = ws.get('F1')
    return bool(value and value[0] and str(value[0][0]).upper() == 'TRUE')
