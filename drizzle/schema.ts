import { boolean, foreignKey, int, json, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

export const localAccounts = mysqlTable("local_accounts", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().unique().references(() => users.id),
  username: varchar("username", { length: 64 }).notNull().unique(),
  passwordHash: varchar("passwordHash", { length: 255 }).notNull(),
  mustChangePassword: boolean("mustChangePassword").notNull().default(true),
  sessionVersion: int("sessionVersion").notNull().default(1),
  passwordChangedAt: timestamp("passwordChangedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const databaseEngineValues = [
  "mysql", "postgresql", "oracle", "sql_server", "dameng", "kingbase", "oceanbase",
  "polardb", "gaussdb", "tidb", "goldendb", "gbase", "tdsql", "opengauss",
] as const;
export const environmentValues = ["production", "staging", "test", "development"] as const;
export const healthStatusValues = ["healthy", "warning", "critical", "unknown"] as const;
export const runbookCategoryValues = ["deployment", "backup_recovery", "inspection", "self_healing"] as const;
export const riskLevelValues = ["low", "medium", "high", "critical"] as const;
export const executionStatusValues = ["scheduled", "awaiting_approval", "queued", "dispatched", "running", "succeeded", "failed", "cancelled"] as const;
export const executionTriggerValues = ["manual", "incident_auto", "scheduled", "retry"] as const;
export const integrationProviderValues = ["zabbix", "prometheus", "xxl_job"] as const;
export const serverStatusValues = ["online", "degraded", "offline", "unknown"] as const;
export const changeRequestStatusValues = ["draft", "pending_review", "approved", "rejected", "executing", "succeeded", "failed", "cancelled"] as const;
export const queryAuditStatusValues = ["pending", "approved", "rejected", "executed", "failed"] as const;

export const databaseInstances = mysqlTable("database_instances", {
  id: int("id").autoincrement().primaryKey(),
  serverAssetId: int("serverAssetId").references(() => serverAssets.id),
  name: varchar("name", { length: 128 }).notNull(),
  engine: mysqlEnum("engine", databaseEngineValues).notNull(),
  host: varchar("host", { length: 255 }).notNull(),
  port: int("port").notNull(),
  databaseName: varchar("databaseName", { length: 128 }),
  version: varchar("version", { length: 80 }),
  metadata: json("metadata").$type<Record<string, unknown>>(),
  metadataSyncedAt: timestamp("metadataSyncedAt"),
  environment: mysqlEnum("environment", environmentValues).notNull().default("production"),
  healthStatus: mysqlEnum("healthStatus", healthStatusValues).notNull().default("unknown"),
  healthScore: int("healthScore").notNull().default(0),
  connectionStatus: mysqlEnum("connectionStatus", ["connected", "degraded", "disconnected", "unknown"]).notNull().default("unknown"),
  capacityGb: int("capacityGb"),
  usedCapacityGb: int("usedCapacityGb"),
  owner: varchar("owner", { length: 128 }),
  credentialRef: varchar("credentialRef", { length: 160 }),
  capabilities: json("capabilities").$type<string[]>(),
  tags: json("tags").$type<string[]>(),
  lastCheckedAt: timestamp("lastCheckedAt"),
  createdBy: varchar("createdBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const serverAssets = mysqlTable("server_assets", {
  id: int("id").autoincrement().primaryKey(),
  name: varchar("name", { length: 128 }).notNull(),
  hostname: varchar("hostname", { length: 255 }).notNull(),
  ipAddress: varchar("ipAddress", { length: 64 }),
  operatingSystem: varchar("operatingSystem", { length: 128 }),
  environment: mysqlEnum("environment", environmentValues).notNull().default("production"),
  status: mysqlEnum("status", serverStatusValues).notNull().default("unknown"),
  zone: varchar("zone", { length: 128 }),
  owner: varchar("owner", { length: 128 }),
  credentialRef: varchar("credentialRef", { length: 160 }),
  capabilities: json("capabilities").$type<string[]>(),
  metadata: json("metadata").$type<Record<string, unknown>>(),
  lastCheckedAt: timestamp("lastCheckedAt"),
  probeRequestedAt: timestamp("probeRequestedAt"),
  lastProbeMessage: text("lastProbeMessage"),
  createdBy: varchar("createdBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const controlledExecutorNodes = mysqlTable("controlled_executor_nodes", {
  id: int("id").autoincrement().primaryKey(),
  serverAssetId: int("serverAssetId").references(() => serverAssets.id),
  nodeKey: varchar("nodeKey", { length: 64 }).notNull().unique(),
  name: varchar("name", { length: 128 }).notNull(),
  environment: mysqlEnum("environment", environmentValues).notNull().default("production"),
  status: mysqlEnum("status", ["online", "degraded", "offline", "unverified"]).notNull().default("unverified"),
  endpoint: varchar("endpoint", { length: 512 }),
  zone: varchar("zone", { length: 128 }),
  capabilities: json("capabilities").$type<string[]>(),
  supportedEngines: json("supportedEngines").$type<string[]>(),
  lastHeartbeatAt: timestamp("lastHeartbeatAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const runbooks = mysqlTable("runbooks", {
  id: int("id").autoincrement().primaryKey(),
  title: varchar("title", { length: 160 }).notNull(),
  category: mysqlEnum("category", runbookCategoryValues).notNull(),
  description: text("description"),
  compatibleEngines: json("compatibleEngines").$type<string[]>(),
  riskLevel: mysqlEnum("riskLevel", riskLevelValues).notNull().default("medium"),
  approvalRequired: boolean("approvalRequired").notNull().default(true),
  steps: json("steps").$type<Array<{ name: string; action: string; requiresConfirmation?: boolean }>>(),
  status: mysqlEnum("status", ["draft", "active", "archived"]).notNull().default("draft"),
  createdBy: varchar("createdBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const runbookExecutions = mysqlTable("runbook_executions", {
  id: int("id").autoincrement().primaryKey(),
  executionKey: varchar("executionKey", { length: 64 }).notNull().unique(),
  runbookId: int("runbookId").references(() => runbooks.id),
  templateKey: varchar("templateKey", { length: 64 }),
  runbookTitle: varchar("runbookTitle", { length: 160 }).notNull(),
  instanceId: int("instanceId").references(() => databaseInstances.id),
  executorNodeId: int("executorNodeId"),
  category: mysqlEnum("category", runbookCategoryValues).notNull(),
  riskLevel: mysqlEnum("riskLevel", riskLevelValues).notNull(),
  status: mysqlEnum("status", executionStatusValues).notNull().default("awaiting_approval"),
  triggerSource: mysqlEnum("triggerSource", executionTriggerValues).notNull().default("manual"),
  retryOfExecutionId: int("retryOfExecutionId"),
  input: json("input").$type<Record<string, unknown>>(),
  confirmationRequired: boolean("confirmationRequired").notNull().default(true),
  scheduledAt: timestamp("scheduledAt"),
  approvalNote: text("approvalNote"),
  approvedBy: varchar("approvedBy", { length: 64 }),
  approvedAt: timestamp("approvedAt"),
  dispatchedAt: timestamp("dispatchedAt"),
  startedAt: timestamp("startedAt"),
  completedAt: timestamp("completedAt"),
  result: json("result").$type<Record<string, unknown>>(),
  createdBy: varchar("createdBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
}, (table) => [
  foreignKey({
    columns: [table.executorNodeId],
    foreignColumns: [controlledExecutorNodes.id],
    name: "rb_exec_node_fk",
  }),
]);

export const executionLogs = mysqlTable("execution_logs", {
  id: int("id").autoincrement().primaryKey(),
  executionId: int("executionId").notNull().references(() => runbookExecutions.id),
  level: mysqlEnum("level", ["info", "warning", "error", "audit"]).notNull().default("info"),
  phase: varchar("phase", { length: 64 }).notNull().default("control_plane"),
  message: text("message").notNull(),
  metadata: json("metadata").$type<Record<string, unknown>>(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const monitoringIntegrations = mysqlTable("monitoring_integrations", {
  id: int("id").autoincrement().primaryKey(),
  name: varchar("name", { length: 128 }).notNull(),
  provider: mysqlEnum("provider", integrationProviderValues).notNull(),
  endpoint: varchar("endpoint", { length: 512 }).notNull(),
  status: mysqlEnum("status", ["connected", "degraded", "disconnected", "unconfigured"]).notNull().default("unconfigured"),
  secretRef: varchar("secretRef", { length: 160 }),
  mapping: json("mapping").$type<Record<string, unknown>>(),
  lastSyncAt: timestamp("lastSyncAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const monitoringMetricSnapshots = mysqlTable("monitoring_metric_snapshots", {
  id: int("id").autoincrement().primaryKey(),
  integrationId: int("integrationId"),
  instanceId: int("instanceId"),
  metric: varchar("metric", { length: 128 }).notNull(),
  value: varchar("value", { length: 128 }).notNull(),
  unit: varchar("unit", { length: 32 }),
  labels: json("labels").$type<Record<string, unknown>>(),
  occurredAt: timestamp("occurredAt").defaultNow().notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
}, (table) => [
  foreignKey({ columns: [table.integrationId], foreignColumns: [monitoringIntegrations.id], name: "metric_int_fk" }),
  foreignKey({ columns: [table.instanceId], foreignColumns: [databaseInstances.id], name: "metric_inst_fk" }),
]);

export const operationalAlerts = mysqlTable("operational_alerts", {
  id: int("id").autoincrement().primaryKey(),
  externalId: varchar("externalId", { length: 128 }),
  integrationId: int("integrationId").references(() => monitoringIntegrations.id),
  instanceId: int("instanceId").references(() => databaseInstances.id),
  title: varchar("title", { length: 255 }).notNull(),
  severity: mysqlEnum("severity", ["critical", "high", "medium", "low", "info"]).notNull().default("medium"),
  status: mysqlEnum("status", ["open", "acknowledged", "resolved"]).notNull().default("open"),
  metric: varchar("metric", { length: 128 }),
  currentValue: varchar("currentValue", { length: 128 }),
  threshold: varchar("threshold", { length: 128 }),
  context: json("context").$type<Record<string, unknown>>(),
  occurredAt: timestamp("occurredAt").defaultNow().notNull(),
  resolvedAt: timestamp("resolvedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const incidentAnalyses = mysqlTable("incident_analyses", {
  id: int("id").autoincrement().primaryKey(),
  analysisKey: varchar("analysisKey", { length: 64 }).notNull().unique(),
  alertId: int("alertId").references(() => operationalAlerts.id),
  instanceId: int("instanceId").references(() => databaseInstances.id),
  status: mysqlEnum("status", ["completed", "failed"]).notNull(),
  model: varchar("model", { length: 96 }),
  contextDigest: text("contextDigest"),
  result: json("result").$type<Record<string, unknown>>(),
  createdBy: varchar("createdBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const sqlReviewPolicies = mysqlTable("sql_review_policies", {
  id: int("id").autoincrement().primaryKey(),
  name: varchar("name", { length: 128 }).notNull(),
  engine: varchar("engine", { length: 32 }),
  enabled: boolean("enabled").notNull().default(true),
  rules: json("rules").$type<Array<{ key: string; severity: "error" | "warning" | "info"; message: string }>>(),
  createdBy: varchar("createdBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const changeRequests = mysqlTable("change_requests", {
  id: int("id").autoincrement().primaryKey(),
  requestKey: varchar("requestKey", { length: 64 }).notNull().unique(),
  title: varchar("title", { length: 160 }).notNull(),
  instanceId: int("instanceId").references(() => databaseInstances.id),
  serverAssetId: int("serverAssetId").references(() => serverAssets.id),
  engine: varchar("engine", { length: 32 }).notNull(),
  sqlText: text("sqlText").notNull(),
  rollbackSql: text("rollbackSql"),
  riskLevel: mysqlEnum("riskLevel", riskLevelValues).notNull().default("medium"),
  status: mysqlEnum("status", changeRequestStatusValues).notNull().default("draft"),
  reviewResult: json("reviewResult").$type<{ passed: boolean; findings: Array<{ rule: string; severity: string; message: string }> }>(),
  plan: json("plan").$type<Record<string, unknown>>(),
  approver: varchar("approver", { length: 64 }),
  approvedAt: timestamp("approvedAt"),
  linkedExecutionKey: varchar("linkedExecutionKey", { length: 64 }),
  requestedBy: varchar("requestedBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const queryAuditRecords = mysqlTable("query_audit_records", {
  id: int("id").autoincrement().primaryKey(),
  queryKey: varchar("queryKey", { length: 64 }).notNull().unique(),
  instanceId: int("instanceId").references(() => databaseInstances.id),
  engine: varchar("engine", { length: 32 }).notNull(),
  sqlHash: varchar("sqlHash", { length: 128 }).notNull(),
  status: mysqlEnum("status", queryAuditStatusValues).notNull().default("pending"),
  maskedColumns: json("maskedColumns").$type<string[]>(),
  requestedBy: varchar("requestedBy", { length: 64 }),
  reviewedBy: varchar("reviewedBy", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const notificationEvents = mysqlTable("notification_events", {
  id: int("id").autoincrement().primaryKey(),
  category: varchar("category", { length: 64 }).notNull(),
  severity: mysqlEnum("severity", ["critical", "high", "medium", "low", "info"]).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  content: text("content").notNull(),
  status: mysqlEnum("status", ["delivered", "failed", "pending"]).notNull().default("pending"),
  sourceExecutionKey: varchar("sourceExecutionKey", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  deliveredAt: timestamp("deliveredAt"),
});
