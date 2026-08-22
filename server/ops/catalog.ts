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
];

export function getCatalogRunbook(key: string) {
  return builtInRunbooks.find(item => item.key === key);
}
