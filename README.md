# 🌿 LifeOS V0.1 个人数据中心

本地 Python + Streamlit + SQLite 应用。第一版包含首页、财富、制粉检修、知识和成长模块；其中制粉检修台账已经实现录入、查询、修改、删除和 CSV 导出。知识库可查看本地 Markdown。财富与成长暂为占位，不连接量化/券商账户。

## Windows 安装

1. 准备 Python 3.13（执行 py -3.13 --version 检查）。
2. 从 GitHub 克隆或下载此仓库至 D:\LifeOS （无 D 盘可自行更换）。
3. 双击 start_lifeos.bat，首次运行需联网安装依赖。
4. 浏览器打开 http://127.0.0.1:8501（仅本机地址）。

## 目录说明

- app.py：中文界面
- lifeos/storage.py：SQLite 检修记录存储模块
- data/lifeos.db：真实数据库（首次运行生成；被 git 忽略）
- knowledge/：私有 Markdown 笔记（被 git 忽略）
- imports/：本地原始资料（被 git 忽略）
- backups/：本地备份（被 git 忽略）
- tests/：仅使用临时虚构数据的自动化测试

## 隐私与安全

**仓库当前可能公开。请不要提交数据库、真实资产、个人身份信息、工作原始资料、API 密钥、笔记或备份文件。** .gitignore 只是第一层防线，不能阻止强制提交。该版本不上传用户数据，不开放公网，也没有手机远程访问和身份认证。

### 备份

关闭 LifeOS 后，将 data/lifeos.db 和 knowledge/ 复制到另一可靠磁盘或加密备份位置。恢复前关闭应用；覆盖前保留原数据库副本。单独放在同一硬盘的 backups/ 目录不算异地备份。

## 手动运行

1. py -3.13 -m venv .venv
2. .venv\Scripts\python.exe -m pip install -r requirements.txt
3. .venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1

测试命令：py -3.13 -m unittest discover -s tests -v

待验证：用户 Windows 机器上的图形界面、依赖兼容性和启动脚本。暂不接入养鹅计划，未来计划添加导入校验、自动备份、时间轴、财富只读看板与安全手机访问。
