# 受控执行节点协议

控制面通过 HTTPS 暴露受控执行节点接口。节点部署于数据库网络内，负责实际调用数据库驱动、厂商工具或受限 SSH；控制面只保存任务状态、审计证据和密钥引用，不保存数据库密码。

| 接口 | 方法 | 用途 | 必需身份材料 |
| --- | --- | --- | --- |
| `/api/executor/health` | `GET` | 验证控制面连通性与共享认证 | `x-executor-secret` |
| `/api/executor/heartbeat` | `POST` | 上报节点在线状态及能力声明 | `x-executor-secret`、`nodeKey` |
| `/api/executor/claim` | `POST` | 领取已审批且已排队的执行单 | `x-executor-secret`、`nodeKey` |
| `/api/executor/result` | `POST` | 回传最终状态、结构化结果和脱敏日志 | `x-executor-secret`、`nodeKey`、执行租约 |

任务领取时，控制面为指定节点生成一个十分钟有效的 HMAC 执行租约。结果回传时必须携带相同的 `executionKey`、`leaseExpiresAt` 和 `leaseToken`，且节点必须与领取节点一致。备份恢复和故障自愈任务回传失败时，控制面会记录高优先级通知事件并尝试通知平台负责人。

> 节点应只执行本地适配器白名单中的动作，所有日志必须脱敏，且不应将数据库密码、连接串、私钥或完整备份内容回传到控制面。
