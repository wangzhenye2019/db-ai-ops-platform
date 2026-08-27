
# Bytebase 与 Yearning 集成研究记录

## 上游快照

| 项目 | 上游提交 | 主要形态 | 许可证结论 |
| --- | --- | --- | --- |
| Bytebase | `9e117d42e20ff0846a82e218ef7572e8e6b6f487`（2026-08-27） | Go 服务端、TypeScript 前端；数据库治理控制面 | 普通源码多数为 MIT，但 enterprise 目录及控制功能、权限、角色、计划启用代码受 `LICENSE.enterprise` 约束，不能默认整体按 MIT 复制。 |
| Yearning | `6e56e685beb2fff830ddd55ac406f842d575b82c`（2025-03-11） | Go 服务端、Vue 前端；本地部署 SQL 审核平台 | AGPL-3.0。直接复制代码或把其修改版作为网络服务运行会带来源码提供、版权与界面法律声明义务。 |

## 能力映射

Bytebase README 将其定位为数据库治理控制面，核心能力包括变更申请/审核/部署/回滚、200+ SQL review 规则、RBAC、限时访问、动态数据脱敏、审计、数据分类和 AI/MCP；其支持 PostgreSQL、MySQL、SQL Server、Oracle、MongoDB、Redis、MariaDB、TiDB、Snowflake、ClickHouse、Spanner、OceanBase 等。[1]

Yearning README 的可复用产品概念包括 SQL 审核工单与审批、自动语法/安全/合规检查、DDL/DML 回滚语句、查询审计与敏感字段匿名化、检查规则、RBAC 和 AI SQL 优化/自然语言转 SQL。[2] 其上游数据源模型保存连接凭据，不能直接迁移到 DB CONTROL，因为本项目约束是仅保存密钥引用、由受控执行节点在内网使用最小权限凭据。

## 集成决策

本项目采用“借鉴产品能力与工作流，不直接复制 Yearning 代码；对 Bytebase 仅实现兼容的领域契约/适配器”的路径。第一阶段应新增服务器资产、SQL 审核规则结果、变更工单与查询审计实体，统一复用既有 Runbook、人工确认、受控执行节点、执行日志和审计记录。真实 SQL parser/linter、Bytebase/Yearning 独立服务或企业许可证功能应通过受控外部适配器接入，并在配置中记录来源、版本、许可证和失败降级策略。

### References

[1]: https://github.com/bytebase/bytebase "Bytebase 官方仓库与 README"
[2]: https://github.com/cookieY/Yearning "Yearning 官方仓库与 README"
