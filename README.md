# DB CONTROL · 多数据库 AI 自动化运维中心

DB CONTROL 是一个面向企业数据库运维的控制中心。它将数据库资产、标准化 Runbook、审批执行、审计记录、监控告警和 AI 辅助诊断统一到同一界面，并通过受控执行节点将生产操作限制在目标数据库网络内。

> 平台定位为**运维控制面**，而非直接持有或执行数据库管理员凭据的跳板服务。生产变更必须由已登记、在线且具备相应数据库能力的受控执行节点领取，并受审批、租约与审计约束。

## 已实现能力

| 领域 | 当前能力 |
| --- | --- |
| 数据库资产 | 统一登记 MySQL、PostgreSQL、Oracle、SQL Server、达梦、金仓、OceanBase、PolarDB、GaussDB、TiDB、GoldenDB、GBase、TDSQL、openGauss 的连接端点、版本、环境、健康和能力标签。 |
| Runbook | 内置与自定义 Runbook，覆盖安装部署、备份恢复、性能巡检和故障自愈；支持风险等级、人工确认、执行记录和结果审计。 |
| 执行安全 | 受控节点心跳、已确认任务领取、限时 HMAC 租约、结果回传与备份/自愈失败通知。 |
| 智能处置 | 将告警、实例、风险信号和脱敏执行日志汇聚为上下文，使用服务端模型生成结构化根因、风险和 Runbook 草案。 |
| 监控集成 | 提供 Zabbix、Prometheus、XXL-Job 的登记模型、字段映射配置与状态视图；实际生产端点需按环境配置并联调。 |
| 运维总览 | 集中展示资产健康、执行状态、告警优先级、性能风险与近期处置记录。 |

## 技术组成

| 层次 | 采用技术 | 主要职责 |
| --- | --- | --- |
| 前端 | React 19、TypeScript、Tailwind CSS、tRPC Client | 蓝图/CAD 风格运维控制台及类型安全交互。 |
| 服务端 | Express 4、tRPC 11、TypeScript | 领域接口、会话控制、审批、智能诊断和受控节点网关。 |
| 数据层 | MySQL/TiDB、Drizzle ORM | 资产、Runbook、执行、日志、告警、通知和分析记录。 |
| 智能能力 | 服务端 LLM 集成 | 输出可审阅的结构化诊断，不替代人工批准。 |
| 本地初始化认证 | scrypt、HttpOnly 会话 Cookie、会话版本 | 提供首次管理员进入路径，完成首次改密前不开放运维接口。 |

## 本地开发

请先准备 Node.js 22+、pnpm 以及可访问的 MySQL 兼容数据库。运行时敏感变量须通过部署环境提供，不能提交到仓库。

```bash
pnpm install
pnpm check
pnpm test
pnpm dev
```

生产打包使用以下命令：

```bash
pnpm build
pnpm start
```

## 环境与安全配置

| 配置项 | 用途 | 要求 |
| --- | --- | --- |
| `DATABASE_URL` | 控制面数据库连接 | 使用最小权限账户，并启用传输加密。 |
| `JWT_SECRET` | 会话签名 | 使用高熵随机值，定期轮换。 |
| `EXECUTOR_GATEWAY_SHARED_SECRET` | 受控执行节点请求认证与租约签名 | 仅分发给受控节点和服务端，不得用于第三方监控回调。 |
| `LOCAL_BOOTSTRAP_USERNAME` | 本地初始化管理员用户名 | 仅用于首次建立本地管理员账户。 |
| `LOCAL_BOOTSTRAP_PASSWORD` | 本地初始化管理员临时密码 | 首次登录后必须修改；修改后不再作为登录口令使用。 |
| LLM 服务端凭据 | 智能诊断调用 | 仅将脱敏上下文发送到模型服务。 |
| 外部系统凭据 | Zabbix、Prometheus、XXL-Job 联调 | 存放在受控密钥管理系统，以引用方式登记。 |

## 验证与质量

项目使用 Vitest 覆盖适配器能力矩阵、输入校验、风险信号、通知分级、审批策略、执行节点认证和执行可行性策略。提交前至少执行：

```bash
pnpm check && pnpm test && pnpm build
```

本地登录通过 `POST /api/local-auth/login` 创建一小时的 HttpOnly 会话。首次登录者会被强制展示密码更新界面；新密码必须至少 16 位，并同时包含大写字母、小写字母、数字和特殊字符。成功改密会提升会话版本，使先前本地会话失效。

## 工程结构

```text
client/src/pages/        运维总览、资产、Runbook、集成、智能处置和能力矩阵页面
server/ops/catalog.ts    多数据库能力矩阵与内置 Runbook 目录
server/ops/service.ts    资产、执行、告警、诊断与通知领域服务
server/ops/executionPolicy.ts
                         独立的 Runbook 执行前置策略校验
server/ops/executorGateway.ts
                         受控执行节点 HTTP 协议与安全租约
server/routers/ops.ts    受类型约束的运维 tRPC 接口
drizzle/schema.ts        运维控制面持久化领域模型
ARCHITECTURE.md           架构、数据流、信任边界与扩展决策
```

详细架构请参阅 [ARCHITECTURE.md](./ARCHITECTURE.md)，受控节点调用约定请参阅 [executor-protocol.md](./executor-protocol.md)。
