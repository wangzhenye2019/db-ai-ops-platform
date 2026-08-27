# 第三方组件声明

本仓库在 `deployments/dbops_mysql/` 中集成了 [fanderchan/dbops](https://gitee.com/fanderchan/dbops) 的 MySQL Ansible 自动化资产，用于数据库部署功能。集成基线固定为上游提交 `e016eb288bb0181d1f906329d96e9583567271e4`，上游许可证为 **Apache License 2.0**；对应许可证副本见 [`deployments/dbops_mysql/UPSTREAM_LICENSE`](deployments/dbops_mysql/UPSTREAM_LICENSE)。

该目录保留了对部署实现必要的文本、模板与配置文件，但明确排除了上游预编译二进制、RPM 和压缩包，以避免未经审计的可执行资产被随项目分发。项目通过 `db_ai_safe_*.yml` 安全包装剧本调用上游 MySQL 安装与复制角色。包装剧本不执行上游 `pre_check_and_set` 角色，因此**不会**自动禁用 SELinux、停止防火墙、修改 `vm.swappiness` 或强制改变网络配置。

运行时配置、SSH 密码和 MySQL 初始化密码均由平台凭据库引用并解密到临时工作区，不会写入 Git、部署任务载荷或可见日志。部署完成或失败后，该临时工作区将被清理。
