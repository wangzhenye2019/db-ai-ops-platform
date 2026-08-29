# DB AI Ops Platform 优化审查报告

## 审查范围

本次审查基于 `wangzhenye2019/db-ai-ops-platform` 的 `main` 分支提交 `76f1969`，覆盖 Flask/Celery 后端、Vue/Vite 前端、备份恢复任务、SSH 运维任务、测试脚本和生产构建配置。

## 已完成优化

后端备份与恢复任务已统一通过 `db_ai_ops.security.run_argv` 使用参数数组和 `shell=False` 执行，MySQL 的输出重定向改为私密文件句柄，MySQL 密码改用 `MYSQL_PWD` 环境变量，PostgreSQL 继续使用 `PGPASSWORD`。同时加入数据库标识符白名单校验，避免数据库名被解释为命令控制语法。所有 `backend/db_ai_ops` 下的 `shell=True` 调用均已移除。

SSH 运维任务不再使用 `paramiko.AutoAddPolicy()` 自动信任未知主机。现在必须存在配置的 `SSH_KNOWN_HOSTS_PATH` 或默认 `~/.ssh/known_hosts`，并使用 `RejectPolicy` 拒绝未知主机，从而避免中间人风险。新增测试覆盖 known_hosts 缺失时在连接前失败。

前端路由已改为统一异步组件工厂，避免同一 router 模块同时被静态和动态导入。Vite 增加 Vue、Element Plus 和工具库 vendor 分包。生产构建的入口主 chunk 从约 1.48MB 降至约 1.22MB，并拆出独立 vendor chunk；Element Plus vendor 仍约 1.05MB，后续可继续按功能拆分。

## 验证结果

| 验证项 | 结果 | 说明 |
| --- | --- | --- |
| Python 编译 | 通过 | `python3 -m compileall -q backend/db_ai_ops` |
| 后端测试 | 通过 | `PYTHONPATH=backend pytest -q backend/tests`，17 passed |
| 前端构建 | 通过 | `npm ci` 与 `npm run build` 成功 |
| 安全扫描 | 通过 | `backend/db_ai_ops` 未发现 `shell=True` 或 `AutoAddPolicy` |
| 工作区差异 | 可提交 | 仅包含安全执行辅助模块、备份/SSH 改造、前端路由分包和本报告 |

## 生产边界

Oracle 和 SQL Server 客户端的认证参数仍受厂商 CLI 能力限制，部分密码会作为独立进程参数传递；虽然已消除 shell 解释和命令注入，但生产环境应优先改为受控节点密钥引用、临时凭据或厂商支持的安全认证文件。真实 SSH 探活必须配置经过校验的 known_hosts 文件，不应通过关闭主机密钥校验来绕过失败。

本次未直接向远程 `main` 强制推送。优化代码应通过独立分支和 Pull Request 审阅后合并。
