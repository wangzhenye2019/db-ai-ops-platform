# AI智能运维平台

版本：v0.4.3

一个面向多种数据库（MySQL、PostgreSQL、Oracle、SQL Server 等）的 AI 自动化运维平台，采用前后端分离架构，覆盖安装部署 / 备份恢复 / 性能优化 / 故障自愈等场景。

## ✨ 特性

- 🧩 **多数据库场景**：MySQL、PostgreSQL、Oracle、SQL Server 等
- 🧰 **运维能力域**：安装部署 / 备份恢复 / 性能优化 / 故障自愈（规划与迭代中）
- 🤖 **AI 辅助**：面向运维流程的智能分析与建议（规划与迭代中）
- 📊 **可视化管理**：现代化 Web 界面统一编排与审计
- 🔄 **异步任务**：基于 Celery 的后台任务执行框架
- ⏰ **定时任务**：Cron 表达式驱动的任务编排（能力逐步补齐）
- 📥 **批量导入**：数据库 / 主机 / 中间件支持 CSV / XLSX / TXT 导入，并提供模板下载

## 🏗️ 技术栈

### 后端
- Flask - Web 框架
- Celery - 异步任务队列
- Redis - 消息代理
- SQLAlchemy - ORM
- pymysql, psycopg2, cx-Oracle, pymssql - 数据库驱动（按需安装）

### 前端
- Vue 3 - 前端框架
- Element Plus - UI 组件库
- Vite - 构建工具
- Axios - HTTP 客户端

## 📁 项目结构

```
db-ai-ops-platform/
├── backend/                 # 后端 API
│   ├── db_ai_ops/           # 后端包（Flask app / Celery / ORM）
│   │   ├── api/             # API 路由
│   │   ├── tasks/           # Celery 任务
│   │   ├── models.py        # 数据模型
│   │   ├── config.py        # 配置文件
│   │   └── celery_app.py    # Celery 入口
│   ├── requirements.txt     # Python 依赖
│   ├── requirements-drivers.txt # 可选：数据库驱动
│   ├── Dockerfile           # Docker 配置
│   └── run.py             # 启动文件
├── frontend/               # 前端 Vue
│   ├── src/
│   │   ├── api/            # API 调用
│   │   ├── views/          # 页面组件
│   │   │   ├── Dashboard.vue
│   │   │   ├── Databases.vue
│   │   │   ├── Backups.vue
│   │   │   └── Schedules.vue
│   │   ├── router/         # 路由配置
│   │   ├── App.vue         # 根组件
│   │   └── main.js         # 入口文件
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── backups/                # 备份文件存储目录
├── docker-compose.yml      # Docker Compose 配置
├── .env.example           # 环境变量示例
└── README.md              # 本文件
```

## 🚀 快速开始

更多部署方式见：[deployment.md](docs/deployment.md)

### 方式一：Docker Compose（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd db-ai-ops-platform
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，根据需要修改配置
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问应用**
- 前端: http://localhost:3000
- 后端 API: http://localhost:5000

### 方式二：本地开发

#### 后端启动

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-drivers.txt  # 可选：需要连接/备份对应数据库时再安装
```

2. **启动 Redis**
```bash
# 使用 Docker
docker run -d -p 6379:6379 redis:7-alpine

# 或本地安装 Redis
redis-server
```

3. **初始化数据库**
```bash
python -c "from db_ai_ops import create_app; from db_ai_ops.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
```

4. **启动 Flask 服务器**
```bash
python run.py
```

5. **启动 Celery Worker**
```bash
celery -A db_ai_ops.celery_app:celery worker --loglevel=info
```

6. **启动 Celery Beat（定时任务）**
```bash
celery -A db_ai_ops.celery_app:celery beat --loglevel=info
```

#### 前端启动

1. **安装依赖**
```bash
cd frontend
npm install
```

2. **启动开发服务器**
```bash
npm run dev
```

3. **访问应用**
打开浏览器访问: http://localhost:3000

#### 一键脚本（可选）

- Windows：`scripts/dev-backend.ps1`、`scripts/dev-frontend.ps1`
- Linux/macOS：`scripts/dev-backend.sh`、`scripts/dev-frontend.sh`

#### 自动化验证与发布（推荐）

- 本地验证（通过后再提交/推送）：
  - Windows：`scripts/verify.ps1`
  - Linux/macOS：`scripts/verify.sh`
- CI：提交到 GitHub 后会自动执行后端单测/前端构建（`.github/workflows/ci.yml`）

## 📖 使用指南

### 1. 添加数据库

1. 进入"数据库"页面
2. 点击"添加数据库"
3. 填写数据库连接信息：
   - 名称：自定义标识
   - 类型：MySQL/PostgreSQL/Oracle/SQL Server
   - 主机：数据库服务器地址
   - 端口：数据库端口
   - 数据库：数据库名/SID
   - 用户名：数据库用户名
   - 密码：数据库密码
4. 点击"测试连接"验证配置
5. 保存配置

### 2. 创建备份

1. 进入"备份记录"页面
2. 点击"创建备份"
3. 选择要备份的数据库
4. 点击"开始备份"
5. 在列表中查看备份进度和结果

### 3. 设置定时备份

1. 进入"定时任务"页面
2. 点击"添加定时任务"
3. 选择数据库
4. 输入 Cron 表达式，例如：
   - `0 2 * * *` - 每天凌晨 2 点
   - `0 */6 * * *` - 每 6 小时
   - `0 0 * * 0` - 每周日午夜
5. 保存配置

#### Cron 表达式格式

格式：`分 时 日 月 周`

| 字段 | 范围 | 说明 |
|------|------|------|
| 分钟 | 0-59 | 每小时的第几分钟 |
| 小时 | 0-23 | 一天的第几小时 |
| 日期 | 1-31 | 每月的第几天 |
| 月份 | 1-12 | 一年中的第几个月 |
| 星期 | 0-6 | 一周中的第几天 (0=周日) |

### 4. 查看统计

在"概览"页面可以查看：
- 数据库总数
- 备份总数
- 成功/失败次数
- 存储使用情况

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| SECRET_KEY | Flask 密钥 | 自动生成 |
| CELERY_BROKER | Celery 代理地址 | redis://localhost:6379/0 |
| CELERY_BACKEND | Celery 结果存储 | redis://localhost:6379/0 |
| DATABASE_URI | 数据库连接字符串 | sqlite:///backups.db |
| CORS_ORIGINS | 允许的跨域来源 | * |
| MAX_BACKUPS | 每个数据库最大备份数 | 10 |
| BACKUP_RETENTION_DAYS | 备份保留天数 | 30 |

### 数据库驱动要求

不同数据库类型需要安装相应的客户端工具：

- **MySQL**: `mysqldump`
- **PostgreSQL**: `pg_dump`
- **Oracle**: Oracle Instant Client + `expdp`/`exp`
- **SQL Server**: `sqlcmd`

## 🔐 安全建议

1. **修改默认密钥**
   - 修改 `.env` 中的 `SECRET_KEY`

2. **密码加密**
   - 生产环境中应该加密存储数据库密码
   - 使用环境变量或密钥管理服务

3. **限制访问**
   - 配置 `CORS_ORIGINS` 为具体的域名
   - 使用反向代理（Nginx）添加 HTTPS
   - 限制 API 访问 IP

4. **备份加密**
   - 考虑对备份文件进行加密存储
   - 使用安全的备份存储位置

## 🐛 故障排查

### 问题：备份失败

1. 检查数据库连接是否正常
2. 确认数据库客户端工具已安装（mysqldump, pg_dump 等）
3. 查看错误日志获取详细信息

### 问题：Celery 任务不执行

1. 确认 Redis 服务正在运行
2. 检查 Celery worker 是否正常启动
3. 查看日志：`celery -A db_ai_ops.celery_app:celery worker --loglevel=debug`

### 问题：前端无法连接后端

1. 确认后端服务已启动
2. 检查 `vite.config.js` 中的代理配置
3. 查看浏览器控制台的网络请求

## 📝 API 文档

### 备份 API

- `GET /api/backups` - 获取备份列表
- `POST /api/backups` - 创建备份任务
- `GET /api/backups/:id` - 获取备份详情
- `DELETE /api/backups/:id` - 删除备份
- `GET /api/backups/stats` - 获取统计信息

### 数据库 API

- `GET /api/databases` - 获取数据库列表
- `POST /api/databases` - 添加数据库
- `GET /api/databases/:id` - 获取数据库详情
- `PUT /api/databases/:id` - 更新数据库配置
- `DELETE /api/databases/:id` - 删除数据库
- `POST /api/databases/:id/test` - 测试连接

### 定时任务 API

- `GET /api/schedules` - 获取定时任务列表
- `POST /api/schedules` - 添加定时任务
- `GET /api/schedules/:id` - 获取任务详情
- `PUT /api/schedules/:id` - 更新任务
- `DELETE /api/schedules/:id` - 删除任务
- `POST /api/schedules/:id/toggle` - 启用/禁用任务

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👥 作者

王老师

---

如有问题或建议，欢迎联系！
