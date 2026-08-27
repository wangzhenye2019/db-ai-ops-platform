import type { runbookCategoryValues, riskLevelValues } from "../../drizzle/schema";

export type CatalogRunbook = {
  key: string;
  title: string;
  category: (typeof runbookCategoryValues)[number];
  riskLevel: (typeof riskLevelValues)[number];
  approvalRequired: boolean;
  description: string;
  compatibleEngines: string[];
  steps: Array<{ name: string; action: string; requiresConfirmation?: boolean }>;
};

export const adapterMatrix = [
  { engine: "mysql", label: "MySQL", tier: "通用", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "postgresql", label: "PostgreSQL", tier: "通用", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "oracle", label: "Oracle", tier: "商业", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "sql_server", label: "SQL Server", tier: "商业", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "dameng", label: "达梦", tier: "信创", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "kingbase", label: "金仓", tier: "信创", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "oceanbase", label: "OceanBase", tier: "分布式", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "polardb", label: "PolarDB", tier: "云原生", deployment: false, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "gaussdb", label: "GaussDB", tier: "信创", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "tidb", label: "TiDB", tier: "分布式", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "goldendb", label: "GoldenDB", tier: "信创", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "gbase", label: "GBase", tier: "信创", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "tdsql", label: "TDSQL", tier: "云原生", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
  { engine: "opengauss", label: "openGauss", tier: "信创", deployment: true, backupRecovery: true, inspection: true, selfHealing: true },
] as const;

export const builtInRunbooks: CatalogRunbook[] = [
  {
    key: "baseline-inspection",
    title: "数据库基线与性能巡检",
    category: "inspection",
    riskLevel: "low",
    approvalRequired: false,
    description: "采集连接、容量、会话、慢查询与高可用状态，生成可审阅的巡检结论。",
    compatibleEngines: adapterMatrix.map(item => item.engine),
    steps: [{ name: "安全采集", action: "collect_metrics" }, { name: "规则评估", action: "evaluate_baseline" }, { name: "生成报告", action: "render_report" }],
  },
  {
    key: "backup-verify",
    title: "备份执行与可恢复性校验",
    category: "backup_recovery",
    riskLevel: "high",
    approvalRequired: true,
    description: "按数据库能力执行备份、校验完整性并记录恢复演练证据。",
    compatibleEngines: adapterMatrix.map(item => item.engine),
    steps: [{ name: "预检查", action: "preflight" }, { name: "执行备份", action: "backup", requiresConfirmation: true }, { name: "完整性校验", action: "verify_backup" }],
  },
  {
    key: "connection-relief",
    title: "连接池压力缓解",
    category: "self_healing",
    riskLevel: "high",
    approvalRequired: true,
    description: "识别异常连接、评估影响后执行受限会话治理与验证。",
    compatibleEngines: ["mysql", "postgresql", "oracle", "sql_server", "dameng", "kingbase", "gaussdb", "opengauss"],
    steps: [{ name: "影响评估", action: "assess_sessions" }, { name: "人工确认", action: "human_confirm", requiresConfirmation: true }, { name: "受限治理", action: "relieve_connections", requiresConfirmation: true }, { name: "回归验证", action: "verify_service" }],
  },
  {
    key: "cluster-install",
    title: "数据库实例标准化部署",
    category: "deployment",
    riskLevel: "critical",
    approvalRequired: true,
    description: "通过已登记的执行节点进行安装前检查、部署、基线初始化和验收。",
    compatibleEngines: adapterMatrix.filter(item => item.deployment).map(item => item.engine),
    steps: [{ name: "主机与依赖检查", action: "preflight" }, { name: "审批确认", action: "human_confirm", requiresConfirmation: true }, { name: "部署", action: "deploy", requiresConfirmation: true }, { name: "验收", action: "validate_install" }],
  },
  { key: "logical-backup", title: "逻辑备份与恢复点校验", category: "backup_recovery", riskLevel: "medium", approvalRequired: true, description: "执行一致性逻辑备份，校验恢复点、对象完整性与保留策略。", compatibleEngines: adapterMatrix.map(item => item.engine), steps: [{ name: "备份前检查", action: "preflight" }, { name: "逻辑备份", action: "logical_backup", requiresConfirmation: true }, { name: "校验清单", action: "verify_manifest" }] },
  { key: "point-in-time-recovery", title: "时间点恢复演练", category: "backup_recovery", riskLevel: "critical", approvalRequired: true, description: "在隔离目标环境验证日志恢复链路与指定恢复点。", compatibleEngines: ["mysql", "postgresql", "oracle", "sql_server", "dameng", "kingbase", "gaussdb", "opengauss"], steps: [{ name: "恢复链校验", action: "validate_recovery_chain" }, { name: "人工确认", action: "human_confirm", requiresConfirmation: true }, { name: "隔离恢复", action: "point_in_time_recovery", requiresConfirmation: true }] },
  { key: "capacity-forecast", title: "容量趋势预测", category: "inspection", riskLevel: "low", approvalRequired: false, description: "采集容量增长速率，识别未来容量阈值与扩容窗口。", compatibleEngines: adapterMatrix.map(item => item.engine), steps: [{ name: "采集容量", action: "collect_capacity" }, { name: "趋势评估", action: "forecast_capacity" }] },
  { key: "slow-sql-analysis", title: "慢 SQL 专项分析", category: "inspection", riskLevel: "low", approvalRequired: false, description: "分析慢查询、执行计划与索引命中，输出可审阅优化建议。", compatibleEngines: adapterMatrix.map(item => item.engine), steps: [{ name: "采集慢 SQL", action: "collect_slow_sql" }, { name: "计划分析", action: "analyze_execution_plan" }] },
  { key: "replication-health", title: "复制链路健康检查", category: "inspection", riskLevel: "low", approvalRequired: false, description: "核对复制延迟、日志位点和副本一致性，生成高可用风险证据。", compatibleEngines: ["mysql", "postgresql", "oracle", "sql_server", "dameng", "kingbase", "gaussdb", "opengauss", "tidb"], steps: [{ name: "采集复制状态", action: "collect_replication" }, { name: "一致性评估", action: "evaluate_replication" }] },
  { key: "replication-relief", title: "复制延迟受控缓解", category: "self_healing", riskLevel: "high", approvalRequired: true, description: "评估复制延迟成因并在审批后执行限流、追赶或重连措施。", compatibleEngines: ["mysql", "postgresql", "oracle", "dameng", "kingbase", "gaussdb", "opengauss", "tidb"], steps: [{ name: "定位延迟", action: "diagnose_lag" }, { name: "人工确认", action: "human_confirm", requiresConfirmation: true }, { name: "受控缓解", action: "relieve_lag", requiresConfirmation: true }] },
  { key: "lock-contention", title: "锁等待与阻塞治理", category: "self_healing", riskLevel: "high", approvalRequired: true, description: "识别阻塞链路并在影响评估后执行受限的会话治理。", compatibleEngines: adapterMatrix.map(item => item.engine), steps: [{ name: "阻塞链采集", action: "collect_lock_chain" }, { name: "影响确认", action: "human_confirm", requiresConfirmation: true }, { name: "受限处置", action: "resolve_lock_contention", requiresConfirmation: true }] },
  { key: "instance-baseline", title: "实例基线初始化", category: "deployment", riskLevel: "medium", approvalRequired: true, description: "应用参数、账号、审计和备份基线，输出实例合规检查结果。", compatibleEngines: adapterMatrix.filter(item => item.deployment).map(item => item.engine), steps: [{ name: "基线预检", action: "validate_baseline" }, { name: "应用基线", action: "apply_baseline", requiresConfirmation: true }, { name: "合规验证", action: "verify_baseline" }] },
  { key: "ha-readiness", title: "高可用切换演练", category: "deployment", riskLevel: "critical", approvalRequired: true, description: "在受控窗口验证高可用角色切换、连接漂移和回切预案。", compatibleEngines: ["mysql", "postgresql", "oracle", "sql_server", "dameng", "kingbase", "oceanbase", "gaussdb", "tidb", "opengauss"], steps: [{ name: "演练预检", action: "preflight_ha" }, { name: "双重确认", action: "human_confirm", requiresConfirmation: true }, { name: "切换演练", action: "ha_switchover", requiresConfirmation: true }, { name: "回切验证", action: "verify_failback" }] },
  { key: "service-restart", title: "数据库服务受控重启", category: "self_healing", riskLevel: "critical", approvalRequired: true, description: "在健康检查与审批完成后执行节点级服务重启和应用连通性验证。", compatibleEngines: adapterMatrix.map(item => item.engine), steps: [{ name: "业务影响检查", action: "assess_service_impact" }, { name: "人工确认", action: "human_confirm", requiresConfirmation: true }, { name: "受控重启", action: "restart_service", requiresConfirmation: true }, { name: "可用性验证", action: "verify_service" }] },
];

export function getCatalogRunbook(key: string) {
  return builtInRunbooks.find(item => item.key === key);
}
