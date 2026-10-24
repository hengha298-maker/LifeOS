# 🌿 LifeOS V0.2 个人数据中心

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


## V0.2：制粉知识树与安全导入

新功能：机组 → 制粉系统 → 设备三级目录，可按机组、系统、设备查看历史检修时间轴。V0.1 的 maintenance_records 表不删除、不重建、不更改任何原记录，新的目录表由旧记录补充信息。系统编号按原始文字精确匹配，像「1E」和「1E磨」会被视为不同系统，避免错误合并。

- 「系统树」可手动创建任意系统及设备；也可点击生成常用 1A～1E、2A～2E 共10个空系统节点。这是可选示例编号，需核实现场编号。
- 「导入台账」仅在本机解析 CSV 和 XLSX（最大10MB、5000行）；支持手工映射列名、补默认机组/系统、校验日期与必填字段、按机组+系统+设备+日期+描述跳过重复记录。
- 所有文件先预览；只有勾选人工确认并点击「确认批量导入」才写入数据。导入前自动在 backups 目录使用 SQLite 备份 API 保存数据库快照，批量写入使用事务。
- XLSX 默认读取第一张工作表；CSV 支持 UTF-8 和 GB18030。
- 注意：仓库依旧公开。真实台账、资产、个人信息、Markdown 笔记、备份、密钥不得上传 GitHub。

## 从 V0.1 升级（保留旧数据）

1. 关闭 V0.1 命令窗口，确保旧 LifeOS 不再运行。
2. 从旧目录复制 data/lifeos.db 和 knowledge 文件夹（如有），保存一份到独立备份位置，例如 U 盘。
3. 从 V0.2 分支下载 ZIP，解压至新的 LifeOS-v0.2 文件夹；先不要删旧文件夹。
4. 把旧 data/lifeos.db 复制到新目录相同位置（没有旧数据可省略），有笔记则复制 knowledge 文件夹。
5. 运行新的 start_lifeos.bat。旧数据库仍能被读取；新系统目录表自动建立。
6. 检查旧检修记录是否完整、时间轴是否对应正确后，再考虑将新目录作为正式工作目录。

请不要直接把新 ZIP 覆盖旧 data 目录，更不要上传旧数据库到 GitHub。首次在 Windows 安装运行尚需实机验证。
