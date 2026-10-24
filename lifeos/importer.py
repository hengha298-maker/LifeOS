"""台账导入：内存预览、严格校验、去重、显式确认后事务写入。"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
import sqlite3

import pandas as pd
from .storage import EDITABLE, STATUSES, _connect, init_db, list_records, validate
from .catalog import sync_from_records

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 5000
ALIASES = {
    "unit": ("unit", "机组", "机组编号"),
    "system": ("system", "系统", "系统编号", "磨煤机编号"),
    "equipment": ("equipment", "设备", "设备名称"),
    "event_date": ("event_date", "日期", "检修日期", "发生日期"),
    "symptom": ("symptom", "缺陷现象", "检修内容", "故障描述", "缺陷/检修"),
    "cause": ("cause", "原因", "原因分析"),
    "action": ("action", "措施", "处理措施", "处理方案"),
    "status": ("status", "状态", "处理状态"),
    "notes": ("notes", "备注"),
}
LABELS = {"unit": "机组", "system": "系统编号", "equipment": "设备",
          "event_date": "日期", "symptom": "缺陷/检修", "cause": "原因",
          "action": "措施", "status": "状态", "notes": "备注"}


def read_table(filename, content):
    if len(content) > MAX_BYTES:
        raise ValueError("文件不能超过 10 MB")
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        source = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                source = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if source is None:
            raise ValueError("CSV 编码无法识别，请保存为 UTF-8 或 GB18030")
        frame = pd.read_csv(StringIO(source), dtype=str, keep_default_na=False)
    elif suffix == ".xlsx":
        frame = pd.read_excel(BytesIO(content), dtype=str, keep_default_na=False,
                              engine="openpyxl")
    else:
        raise ValueError("只接受 CSV 或 .xlsx 文件")
    if frame.empty:
        raise ValueError("文件中没有记录")
    if len(frame) > MAX_ROWS:
        raise ValueError(f"每次最多预览 {MAX_ROWS} 行")
    frame.columns = [str(name).strip() for name in frame.columns]
    if len(set(frame.columns)) != len(frame.columns):
        raise ValueError("存在重复的表头，请先修改 Excel")
    return frame.fillna("")


def guess_mapping(columns):
    result = {}
    for field, candidates in ALIASES.items():
        result[field] = next(
            (column for column in columns if column.strip().casefold() in
             {name.casefold() for name in candidates}), "")
    return result


def fingerprint(row):
    return tuple(" ".join(str(row[key]).split()).casefold()
                 for key in ("unit", "system", "equipment", "event_date", "symptom"))


def preview_import(frame, mapping, defaults=None, path=None):
    """不写入维护记录；返回可导入项、重复项和错误信息。"""
    defaults = defaults or {}
    existing = {fingerprint(row) for row in list_records(path=path)}
    seen = set(existing)
    result = {"ready": [], "duplicates": [], "errors": [], "total": len(frame)}
    for offset, (_, source) in enumerate(frame.iterrows(), start=2):
        row = {}
        for field in EDITABLE:
            column = mapping.get(field, "")
            raw = source[column] if column in frame.columns else defaults.get(field, "")
            row[field] = str(raw).strip() if raw is not None else ""
        row["status"] = row["status"] or "待处理"
        try:
            date_value = pd.to_datetime(row["event_date"], errors="raise")
            if pd.isna(date_value):
                raise ValueError("空日期")
            row["event_date"] = date_value.date().isoformat()
            row = validate(row)
        except (ValueError, TypeError, OverflowError) as error:
            result["errors"].append({"row": offset, "reason": str(error)})
            continue
        key = fingerprint(row)
        if key in seen:
            result["duplicates"].append({"row": offset, "reason": "相同机组、系统、设备、日期和描述"})
        else:
            seen.add(key)
            result["ready"].append(row)
    return result


def backup_db(path=None):
    """SQLite 官方 backup API 创建一致性快照；不覆盖任何现有备份。"""
    from .storage import _path
    db_path = _path(path)
    init_db(db_path)
    folder = db_path.parent.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = folder / f"lifeos-before-import-{stamp}.db"
    source = sqlite3.connect(db_path)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return dest


def import_records(rows, path=None):
    """显式调用时才写库：事务整体提交，失败自动回滚。"""
    if not rows:
        return 0, None
    if len(rows) > MAX_ROWS:
        raise ValueError("一次导入行数超限")
    checked = [validate(row) for row in rows]
    init_db(path)
    backup = backup_db(path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cols = EDITABLE + ("created_at", "updated_at")
    slots = ",".join("?" for _ in cols)
    with _connect(path) as con:
        # 再次去重，避免预览以后库中新增了相同记录。
        existing = {fingerprint(row) for row in con.execute(
            "SELECT * FROM maintenance_records")}
        to_insert = []
        for item in checked:
            key = fingerprint(item)
            if key not in existing:
                existing.add(key)
                to_insert.append([item[field] for field in EDITABLE] + [now, now])
        con.executemany(
            f"INSERT INTO maintenance_records({','.join(cols)}) VALUES({slots})", to_insert)
    sync_from_records(path)
    return len(to_insert), backup
