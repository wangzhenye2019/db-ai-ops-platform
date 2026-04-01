# 部署说明（Windows / Linux / macOS / Docker）

## 1. 方式 A：本地开发（跨平台）

### 后端

```bash
cd backend
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Linux / macOS：

```bash
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

后端默认监听：`http://127.0.0.1:5000`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认：`http://localhost:3000`

## 2. 方式 B：Docker Compose（一键）

前提：已安装 Docker Desktop（Windows/macOS）或 Docker Engine（Linux）。

```bash
docker compose up -d --build
```

访问：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:5000`

## 3. Redis/Celery 的两种模式

### 有 Redis（生产/准生产）

- `docker-compose.yml` 已包含 Redis + worker + beat

### 无 Redis（开发临时）

设置环境变量让 Celery “本地同步执行”：

- Windows：`set CELERY_ALWAYS_EAGER=1`
- Linux/macOS：`export CELERY_ALWAYS_EAGER=1`

这种模式适合先调 API 数据流、任务入队链路，不依赖外部组件。
