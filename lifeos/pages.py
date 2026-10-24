"""系统树和台账导入的界面。"""
import pandas as pd
import streamlit as st
from .catalog import KINDS, add_equipment, add_system, seed_example_structure, system_tree, system_timeline
from .importer import LABELS, guess_mapping, import_records, preview_import, read_table


def render_catalog(db):
    st.title("🌳 制粉系统知识树")
    st.caption("机组 → 制粉系统 → 设备 → 历史检修；V0.1 旧记录不会被改写。")
    tree = system_tree(db)
    with st.expander("⚙️ 系统与设备目录维护", expanded=not tree):
        st.caption("常用的1A～1E、2A～2E只是可选占位编号，请核对后再使用。")
        if st.button("建立10个常见编号"):
            seed_example_structure(db)
            st.rerun()
        with st.form("new_system"):
            unit = st.text_input("机组", placeholder="1号机组")
            code = st.text_input("系统编号", placeholder="1E")
            label = st.text_input("系统显示名称（可选）")
            if st.form_submit_button("新建系统"):
                try:
                    add_system(unit, code, label, db)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        tree = system_tree(db)
        if tree:
            with st.form("new_equipment"):
                parents = {x["id"]: x for x in tree}
                parent = st.selectbox("所属系统", list(parents),
                                      format_func=lambda i: f'{parents[i]["unit"]} / {parents[i]["code"]}')
                name = st.text_input("设备名称")
                kind = st.selectbox("设备类别", KINDS)
                if st.form_submit_button("新增设备"):
                    try:
                        add_equipment(parent, name, kind, db)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
    tree = system_tree(db)
    if not tree:
        st.info("目录尚无系统。可先新建系统。")
        return
    st.subheader("📁 设备目录")
    units = sorted({x["unit"] for x in tree})
    for unit in units:
        st.markdown(f"**🏭 {unit}**")
        for system in [x for x in tree if x["unit"] == unit]:
            with st.expander(f'{system["code"]} · {system["display_name"]}（{system["count"]} 条记录）'):
                if not system["equipment"]:
                    st.caption("暂无设备")
                for item in system["equipment"]:
                    st.write(f'↳ {item["name"]} · {item["kind"]} · {item["count"]} 条记录')
    st.divider()
    st.subheader("📅 设备检修时间轴")
    unit = st.selectbox("机组", units, key="axis_unit")
    systems = [x for x in tree if x["unit"] == unit]
    system = st.selectbox("系统", systems,
                          format_func=lambda x: x["display_name"], key="axis_system")
    equipment = st.selectbox("设备", ["全部设备"] + [e["name"] for e in system["equipment"]],
                              key="axis_device")
    rows = system_timeline(unit, system["code"],
                           "" if equipment == "全部设备" else equipment, db)
    st.caption(f"共 {len(rows)} 条；按日期倒序")
    if not rows:
        st.info("该选择下暂无记录")
    for entry in rows[:100]:
        with st.expander(f'{entry["event_date"]} · {entry["equipment"]} · {entry["symptom"][:40]}'):
            st.write("状态：", entry["status"])
            st.write("内容：", entry["symptom"])
            st.write("原因：", entry["cause"] or "未记录")
            st.write("措施：", entry["action"] or "未记录")
            st.write("备注：", entry["notes"] or "无")
    if len(rows) > 100:
        st.caption("时间轴仅展示最近100条；更多记录请在检修台账查询。")


def render_import(db):
    st.title("📥 旧台账导入")
    st.warning("GitHub 仓库目前公开！真实 Excel 文件仅在本地运行的 LifeOS 内打开，不要提交到 GitHub。")
    st.caption("上传本机文件只用于本机解析；不会自动导入。先预览和检查，最终由你确认。")
    upload = st.file_uploader("选择 CSV / XLSX，最大10MB、5000行", type=["csv", "xlsx"])
    if upload is None:
        return
    try:
        table = read_table(upload.name, upload.getvalue())
    except Exception as exc:
        st.error(f"无法读取：{exc}")
        return
    st.dataframe(table.head(10), hide_index=True, use_container_width=True)
    st.subheader("列名映射")
    columns = list(table.columns)
    guesses = guess_mapping(columns)
    options = ["（不使用）"] + columns
    mapping = {}
    a, b, c = st.columns(3)
    for i, (key, label) in enumerate(LABELS.items()):
        with [a, b, c][i % 3]:
            guess = guesses.get(key) or "（不使用）"
            selected = st.selectbox(label, options, index=options.index(guess),
                                    key=f"mapping_{key}")
            mapping[key] = "" if selected == "（不使用）" else selected
    a, b, c = st.columns(3)
    with a:
        default_unit = st.text_input("缺少机组列的默认机组", "")
    with b:
        default_system = st.text_input("缺少系统列的默认编号", "")
    with c:
        default_status = st.selectbox("默认处理状态", ["待处理", "处理中", "已完成"])
    result = preview_import(table, mapping, {"unit": default_unit,
                            "system": default_system, "status": default_status}, db)
    a, b, c = st.columns(3)
    a.metric("可导入", len(result["ready"]))
    b.metric("重复跳过", len(result["duplicates"]))
    c.metric("错误待修正", len(result["errors"]))
    if result["errors"]:
        st.dataframe(pd.DataFrame(result["errors"]).head(100), hide_index=True)
    if result["duplicates"]:
        with st.expander("重复记录"):
            st.dataframe(pd.DataFrame(result["duplicates"]).head(100), hide_index=True)
    if result["ready"]:
        st.write("可导入内容预览")
        st.dataframe(pd.DataFrame(result["ready"]).head(20),
                     hide_index=True, use_container_width=True)
    accepted = st.checkbox("我已核对并确认写入本机数据库")
    if st.button("确认批量导入", disabled=not (accepted and result["ready"]), type="primary"):
        try:
            count, backup = import_records(result["ready"], db)
            st.success(f"已新增 {count} 条记录；导入前备份位于 {backup}")
        except Exception as exc:
            st.error(f"导入失败：{exc}")
