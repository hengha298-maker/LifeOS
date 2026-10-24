"""LifeOS V0.1：仅供本人在本地电脑使用。"""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from lifeos.storage import (
    STATUSES, add_record, delete_record, get_record, init_db,
    list_records, records_csv, update_record,
)

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'lifeos.db'
NOTES = ROOT / 'knowledge'
st.set_page_config(page_title='LifeOS 个人数据中心', page_icon='🌿', layout='wide')
init_db(DB)
NOTES.mkdir(parents=True, exist_ok=True)

st.sidebar.title('🌿 LifeOS')
st.sidebar.caption('V0.1 | 数据只保存在本机')
page = st.sidebar.radio('模块', ['🏠 首页', '💰 财富', '🔧 制粉检修', '📚 知识库', '🌱 成长'])
st.sidebar.divider()
st.sidebar.caption('仅限本机 127.0.0.1')


def entry_fields(prefix, item=None):
    item = item or {}
    a, b, c = st.columns(3)
    with a:
        unit = st.text_input('机组 *', item.get('unit', ''), key=prefix+'_unit')
    with b:
        system = st.text_input('系统/磨煤机编号 *', item.get('system', ''), key=prefix+'_system')
    with c:
        equipment = st.text_input('设备名称 *', item.get('equipment', ''), key=prefix+'_equipment')
    a, b = st.columns(2)
    with a:
        dt = st.date_input('日期 *', date.fromisoformat(item.get('event_date', date.today().isoformat())),
                           key=prefix+'_date')
    with b:
        previous = item.get('status', STATUSES[0])
        status = st.selectbox('处理状态', STATUSES, index=STATUSES.index(previous),
                              key=prefix+'_status')
    symptom = st.text_area('缺陷现象/检修内容 *', item.get('symptom', ''), key=prefix+'_symptom')
    cause = st.text_area('原因分析', item.get('cause', ''), key=prefix+'_cause')
    action = st.text_area('处理措施', item.get('action', ''), key=prefix+'_action')
    notes = st.text_area('备注', item.get('notes', ''), key=prefix+'_notes')
    return {'unit': unit, 'system': system, 'equipment': equipment,
            'event_date': dt.isoformat(), 'symptom': symptom, 'cause': cause,
            'action': action, 'status': status, 'notes': notes}


if page == '🏠 首页':
    st.title('🌿 LifeOS · 个人数据中心')
    data = list_records(path=DB)
    a, b, c = st.columns(3)
    a.metric('检修记录', len(data))
    b.metric('待处理', sum(x['status'] == '待处理' for x in data))
    c.metric('已完成', sum(x['status'] == '已完成' for x in data))
    st.info('第一版优先完成制粉检修台账。财富、成长模块暂时只是入口。')
    st.write('本地 SQLite | Markdown 笔记 | CSV 导出 | 不上传个人数据')

elif page == '🔧 制粉检修':
    st.title('🔧 制粉检修台账')
    browse, add, edit = st.tabs(['📋 查询与导出', '➕ 新增记录', '✏️ 修改与删除'])
    with browse:
        whole = list_records(path=DB)
        systems = sorted({x['system'] for x in whole})
        a, b, c = st.columns(3)
        with a:
            selected_system = st.selectbox('系统筛选', ['全部'] + systems)
        with b:
            selected_status = st.selectbox('状态筛选', ['全部'] + list(STATUSES))
        with c:
            keyword = st.text_input('关键词')
        start, end = '', ''
        if st.checkbox('按日期筛选'):
            a, b = st.columns(2)
            with a:
                start = st.date_input('开始日期', date.today().replace(month=1, day=1)).isoformat()
            with b:
                end = st.date_input('结束日期', date.today()).isoformat()
        if start and end and start > end:
            st.error('开始日期不能晚于结束日期')
        else:
            items = list_records(
                path=DB, system='' if selected_system == '全部' else selected_system,
                status='' if selected_status == '全部' else selected_status,
                keyword=keyword, start_date=start, end_date=end)
            st.caption(f'找到 {len(items)} 条记录')
            if items:
                labels = {'id': '编号', 'event_date': '日期', 'unit': '机组',
                          'system': '系统', 'equipment': '设备', 'symptom': '缺陷/检修',
                          'cause': '原因', 'action': '措施', 'status': '状态', 'notes': '备注'}
                st.dataframe(pd.DataFrame(items)[list(labels)].rename(columns=labels),
                             hide_index=True, use_container_width=True)
            else:
                st.info('暂无记录，可以先到「新增记录」填写第一条。')
            st.download_button('⬇️ 导出当前结果 CSV', records_csv(items),
                               'lifeos_maintenance.csv', 'text/csv')
    with add:
        with st.form('create', clear_on_submit=True):
            values = entry_fields('new')
            if st.form_submit_button('💾 保存', type='primary'):
                try:
                    key = add_record(values, DB)
                    st.success(f'保存成功，编号 #{key}')
                except ValueError as error:
                    st.error(str(error))
    with edit:
        items = list_records(path=DB)
        if not items:
            st.info('还没有记录可修改。')
        else:
            record_ids = [x['id'] for x in items]
            labels = {x['id']: f"#{x['id']} | {x['event_date']} | {x['system']} | {x['equipment']}"
                      for x in items}
            selected_id = st.selectbox('选择记录', record_ids, format_func=lambda x: labels[x])
            current = get_record(selected_id, DB)
            with st.form(f'edit_{selected_id}'):
                modified = entry_fields(f'edit_{selected_id}', current)
                if st.form_submit_button('保存修改', type='primary'):
                    try:
                        update_record(selected_id, modified, DB)
                        st.success('修改成功')
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
            st.warning('删除无法撤销，建议先备份数据库。')
            confirm = st.checkbox('我确认删除此条记录', key=f'confirm_{selected_id}')
            if st.button('永久删除', disabled=not confirm):
                delete_record(selected_id, DB)
                st.rerun()

elif page == '📚 知识库':
    st.title('📚 我的 Markdown 笔记')
    markdown_files = sorted(
        p for p in NOTES.rglob('*.md')
        if p.is_file() and p.resolve().is_relative_to(NOTES.resolve()))
    if not markdown_files:
        st.info('knowledge 文件夹暂无 .md 文件，先在电脑上添加笔记。')
    else:
        names = [str(p.relative_to(NOTES)) for p in markdown_files]
        index = st.selectbox('选择笔记', range(len(names)), format_func=lambda i: names[i])
        try:
            st.markdown(markdown_files[index].read_text(encoding='utf-8'))
        except (OSError, UnicodeError) as error:
            st.error(f'无法读取笔记：{error}')
elif page == '💰 财富':
    st.title('💰 财富中心')
    st.info('占位模块；目前不接入真实资产、券商与现有量化项目。')
else:
    st.title('🌱 个人成长')
    st.info('占位模块；未来加入学习计划、目标和复盘。')
