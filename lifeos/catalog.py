"""制粉系统树：只增加关联目录，不改动旧 maintenance_records 表。"""
from __future__ import annotations
import sqlite3
from .storage import _connect, init_db

KINDS = ("磨煤机", "给煤机", "煤粉管道", "风道", "阀门/执行机构", "其他")


def init_catalog(path=None):
    init_db(path)
    with _connect(path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("""CREATE TABLE IF NOT EXISTS powder_systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit TEXT NOT NULL, code TEXT NOT NULL, display_name TEXT NOT NULL,
            UNIQUE(unit, code))""")
        con.execute("""CREATE TABLE IF NOT EXISTS equipment_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id INTEGER NOT NULL REFERENCES powder_systems(id),
            name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT '其他',
            UNIQUE(system_id, name))""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_equipment_parent ON equipment_nodes(system_id)")


def _short(value, field, required=True):
    value = str(value or "").strip()
    if required and not value:
        raise ValueError(f"请填写{field}")
    if len(value) > 200:
        raise ValueError(f"{field}不能超过200字")
    return value


def add_system(unit, code, name="", path=None):
    unit = _short(unit, "机组")
    code = _short(code, "系统编号")
    name = _short(name, "系统名称", required=False) or f"{code}制粉系统"
    init_catalog(path)
    with _connect(path) as con:
        con.execute("INSERT OR IGNORE INTO powder_systems(unit, code, display_name) VALUES(?, ?, ?)",
                    (unit, code, name))
        return con.execute("SELECT id FROM powder_systems WHERE unit=? AND code=?",
                           (unit, code)).fetchone()["id"]


def add_equipment(system_id, name, kind="其他", path=None):
    name = _short(name, "设备名称")
    if kind not in KINDS:
        raise ValueError("不支持的设备分类")
    init_catalog(path)
    with _connect(path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        parent = con.execute("SELECT id FROM powder_systems WHERE id=?", (system_id,)).fetchone()
        if not parent:
            raise ValueError("系统不存在")
        con.execute("INSERT OR IGNORE INTO equipment_nodes(system_id, name, kind) VALUES(?, ?, ?)",
                    (system_id, name, kind))
        return con.execute("SELECT id FROM equipment_nodes WHERE system_id=? AND name=?",
                           (system_id, name)).fetchone()["id"]


def seed_example_structure(path=None):
    """用户主动点击后创建常见的 1A~1E、2A~2E 占位系统，可继续增补。"""
    for number in (1, 2):
        for letter in "ABCDE":
            code = f"{number}{letter}"
            add_system(f"{number}号机组", code, f"{code}制粉系统", path)


def sync_from_records(path=None):
    """兼容旧库：从历史记录补充目录，不改写任何旧记录内容。可反复执行。"""
    init_catalog(path)
    with _connect(path) as con:
        rows = con.execute("""SELECT DISTINCT unit, system, equipment
            FROM maintenance_records
            WHERE TRIM(unit)<>'' AND TRIM(system)<>'' AND TRIM(equipment)<>''""").fetchall()
        for row in rows:
            unit, code, equipment = (row["unit"].strip(), row["system"].strip(),
                                     row["equipment"].strip())
            con.execute("INSERT OR IGNORE INTO powder_systems(unit, code, display_name) VALUES(?,?,?)",
                        (unit, code, f"{code}制粉系统"))
            parent = con.execute("SELECT id FROM powder_systems WHERE unit=? AND code=?",
                                 (unit, code)).fetchone()["id"]
            con.execute("""INSERT OR IGNORE INTO equipment_nodes(system_id, name, kind)
                VALUES(?, ?, '其他')""", (parent, equipment))


def system_tree(path=None):
    sync_from_records(path)
    with _connect(path) as con:
        systems = [dict(row) for row in con.execute(
            "SELECT * FROM powder_systems ORDER BY unit, code")]
        equipment = [dict(row) for row in con.execute(
            "SELECT * FROM equipment_nodes ORDER BY kind, name")]
        counts = {(r["unit"], r["system"], r["equipment"]): r["count"]
                  for r in con.execute("""SELECT unit, system, equipment, COUNT(*) AS count
                      FROM maintenance_records GROUP BY unit, system, equipment""")}
    for system in systems:
        system["equipment"] = []
        system["count"] = 0
        for device in equipment:
            if device["system_id"] == system["id"]:
                entry = {**device, "count": counts.get(
                    (system["unit"], system["code"], device["name"]), 0)}
                system["equipment"].append(entry)
                system["count"] += entry["count"]
    return systems


def system_timeline(unit, code, equipment="", path=None):
    """按机组、系统、可选设备返回历史，旧记录保持原样。"""
    init_catalog(path)
    sql = ("SELECT * FROM maintenance_records WHERE unit=? AND system=?")
    params = [unit, code]
    if equipment:
        sql += " AND equipment=?"
        params.append(equipment)
    sql += " ORDER BY event_date DESC, id DESC"
    with _connect(path) as con:
        return [dict(row) for row in con.execute(sql, params)]
