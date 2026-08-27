# 数据库部署资产

`dbops_mysql/` 是从 [fanderchan/dbops](https://gitee.com/fanderchan/dbops) 集成并安全裁剪的 MySQL Ansible 自动化资产。平台目前支持 **单节点**、**一主多从** 与 **MySQL Group Replication（MGR）** 三类拓扑，MySQL 版本限定为 5.7.x、8.0.x 和 8.4.x。

部署任务由后端异步工作进程创建临时工作区，按资产库中的 `Host` 和 `Credential` 生成动态 inventory 与变量文件，再执行 `db_ai_safe_*.yml` 包装剧本。临时 inventory 仅在任务执行期间保存，并以 `0600` 权限保护；任务结束后会被删除。任务结果中的标准输出与错误输出会对已知的 SSH 与数据库密码进行脱敏。

> **安全边界。** 上游 `pre_check_and_set` 角色会禁用 SELinux、停止 firewalld、修改内核参数和处理网络接口检查。平台的包装剧本没有调用该角色，因此这些高影响系统修改不会被自动执行。上游 MySQL 角色仍会创建服务账户、目录、服务、软链接和数据库账号；只应在已经审批的空白目标主机上执行。

## 部署控制器配置

生产执行前，需要为后端与 Celery 工作进程配置以下环境变量。`docker-compose.yml` 已提供容器内默认路径。

| 变量 | 用途 | 示例 |
| --- | --- | --- |
| `DEPLOYMENT_DBOPS_ROOT` | 本目录中 `dbops_mysql` 的绝对路径 | `/app/deployments/dbops_mysql` |
| `DEPLOYMENT_KNOWN_HOSTS_PATH` | 已审核 SSH 主机指纹文件的只读路径 | `/app/deployments/known_hosts/known_hosts` |
| `DEPLOYMENT_WORK_DIR` | 可选：每次任务的临时工作目录 | `/var/lib/db-ai-ops/deployment-work` |

请在受控部署控制器中通过独立、可信的变更流程建立 `known_hosts`，然后将它保存为 `deployments/known_hosts/known_hosts` 并限制权限：

```bash
chmod 600 deployments/known_hosts/known_hosts
```

系统不会在首次连接时自动接受 SSH 指纹；未设置或不存在该文件时，真实部署任务会被拒绝。`dry_run=true` 只进行参数、资产和拓扑预演，不连接目标主机。

## 凭据约定

每台主机需在资产库配置 SSH 用户及密码或 SSH 凭据。数据库初始化凭据必须为 `DB_PASSWORD` 或 `GENERIC` 类型，任务仅引用其 ID。凭据内容可为一个管理员密码文本，或一个 JSON 对象：

```json
{
  "mysql_admin_password": "替换为强密码",
  "mysql_admin_127_password": "可选；缺省时与管理员密码相同",
  "mysql_rple_password": "可选；缺省时任务生成并只在本次执行中使用"
}
```

不得在任务请求中传入 `password`、`mysql_admin_password` 或 `ssh_password` 字段；服务会拒绝此类请求。数据库部署功能仅允许管理员角色发起，并要求 `confirmed=true` 明确确认。
