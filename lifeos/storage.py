"""本地 SQLite 检修台账；不包含任何网络上传功能。"""
from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / 'data' / 'lifeos.db'
STATUSES = ('待处理', '处理中', '已完成')
REQUIRED = ('unit', 'system', 'equipment', 'event_date', 'symptom')
EDITABLE = ('unit', 'system', 'equipment', 'event_date', 'symptom',
            'cause', 'action', 'status', 'notes')
CSV_FIELDS = ('id',) + EDITABLE + ('created_at', 'updated_at')


def _path(path=None):
    return Path(path) if path is not None else DEFAULT_DB


def _connect(path=None):
    db = _path(path)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def init_db(path=None):
    with _connect(path) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS maintenance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit TEXT NOT NULL, system TEXT NOT NULL,
            equipment TEXT NOT NULL, event_date TEXT NOT NULL,
            symptom TEXT NOT NULL, cause TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT '待处理',
            notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_event_date ON maintenance_records(event_date)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_system ON maintenance_records(system)")
    return _path(path)


def validate(data):
    values = {k: str(data.get(k, '') or '').strip() for k in EDITABLE}
    for name in REQUIRED:
        if not values[name]:
            raise ValueError(f'请填写必填项：{name}')
    for name, value in values.items():
        limit = 10000 if name in ('symptom', 'cause', 'action', 'notes') else 200
        if len(value) > limit:
            raise ValueError(f'{name} 超出长度限制')
    try:
        date.fromisoformat(values['event_date'])
    except ValueError as exc:
        raise ValueError('日期应为 YYYY-MM-DD') from exc
    if values['status'] not in STATUSES:
        raise ValueError('处理状态无效')
    return values


def add_record(data, path=None):
    item = validate(data)
    init_db(path)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    cols = EDITABLE + ('created_at', 'updated_at')
    with _connect(path) as con:
        result = con.execute(
            f"INSERT INTO maintenance_records ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
            [item[f] for f in EDITABLE] + [now, now])
        return result.lastrowid


def get_record(record_id, path=None):
    init_db(path)
    with _connect(path) as con:
        row = con.execute('SELECT * FROM maintenance_records WHERE id=?', (record_id,)).fetchone()
        return dict(row) if row else None


def update_record(record_id, data, path=None):
    item = validate(data)
    init_db(path)
    fields = ', '.join(f'{key}=?' for key in EDITABLE)
    with _connect(path) as con:
        cursor = con.execute(
            f'UPDATE maintenance_records SET {fields}, updated_at=? WHERE id=?',
            [item[f] for f in EDITABLE] +
            [datetime.now(timezone.utc).isoformat(timespec='seconds'), record_id])
        return cursor.rowcount > 0


def delete_record(record_id, path=None):
    init_db(path)
    with _connect(path) as con:
        return con.execute('DELETE FROM maintenance_records WHERE id=?', (record_id,)).rowcount > 0


def list_records(*, system='', status='', keyword='', start_date='', end_date='', path=None):
    init_db(path)
    clauses, params = [], []
    if system.strip():
        clauses.append('system=?')
        params.append(system.strip())
    if status.strip():
        clauses.append('status=?')
        params.append(status.strip())
    if keyword.strip():
        val = keyword.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = '%' + val + '%'
        clauses.append("(equipment LIKE ? ESCAPE '\\' OR symptom LIKE ? ESCAPE '\\' "
                       "OR cause LIKE ? ESCAPE '\\' OR action LIKE ? ESCAPE '\\' "
                       "OR notes LIKE ? ESCAPE '\\')")
        params.extend([pattern] * 5)
    if start_date:
        clauses.append('event_date>=?')
        params.append(start_date)
    if end_date:
        clauses.append('event_date<=?')
        params.append(end_date)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with _connect(path) as con:
        query = 'SELECT * FROM maintenance_records' + where + ' ORDER BY event_date DESC, id DESC'
        return [dict(row) for row in con.execute(query, params)]


def records_csv(records):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=CSV_FIELDS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(records)
    return out.getvalue().encode('utf-8-sig')
