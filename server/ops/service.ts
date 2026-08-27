import { and, desc, eq, inArray } from "drizzle-orm";
import { createHash } from "node:crypto";
import { nanoid } from "nanoid";
import {
  changeRequests, controlledExecutorNodes, databaseInstances, executionLogs, incidentAnalyses,
  monitoringIntegrations, monitoringMetricSnapshots, notificationEvents, operationalAlerts, queryAuditRecords, runbookExecutions, runbooks,
  serverAssets, sqlReviewPolicies,
} from "../../drizzle/schema";
import { getDb } from "../db";
import { invokeLLM, listLLMModels } from "../_core/llm";
import { notifyOwner } from "../_core/notification";
import { getCatalogRunbook } from "./catalog";
import { assertExecutionPolicy } from "./executionPolicy";
import { assertCancellableExecution, assertRetryableExecution } from "./executionActionPolicy";

const emptyOverview = {
  instances: { total: 0, healthy: 0, warning: 0, critical: 0 },
  alerts: { open: 0, critical: 0, high: 0 },
  executions: { active: 0, awaitingApproval: 0, failed: 0 },
  integrations: { configured: 0, connected: 0 },
};

type RiskAsset = Pick<typeof databaseInstances.$inferSelect, "id" | "name" | "healthStatus" | "capacityGb" | "usedCapacityGb">;
type RiskAlert = Pick<typeof operationalAlerts.$inferSelect, "id" | "title" | "severity" | "status" | "metric" | "currentValue" | "threshold">;

export function shouldNotifySeverity(severity?: string | null) {
  return severity === "critical" || severity === "high";
}

export function buildPerformanceRisks(instances: RiskAsset[], alerts: RiskAlert[]) {
  const capacitySignals = instances.flatMap(instance => {
    if (!instance.capacityGb || instance.usedCapacityGb === null || instance.usedCapacityGb === undefined) return [];
    const utilization = Math.round((instance.usedCapacityGb / instance.capacityGb) * 100);
    if (utilization < 80) return [];
    return [{ key: `capacity-${instance.id}`, title: `${instance.name} 容量利用率 ${utilization}%`, source: "capacity", severity: utilization >= 92 ? "critical" : "high", detail: `${instance.usedCapacityGb} / ${instance.capacityGb} GB`, instanceId: instance.id }];
  });
  const healthSignals = instances.filter(instance => instance.healthStatus === "warning" || instance.healthStatus === "critical").map(instance => ({ key: `health-${instance.id}`, title: `${instance.name} 健康状态异常`, source: "health", severity: instance.healthStatus === "critical" ? "critical" : "high", detail: "等待监控指标、节点检测或 Runbook 处置", instanceId: instance.id }));
  const alertSignals = alerts.filter(alert => alert.status === "open" && (alert.severity === "critical" || alert.severity === "high")).map(alert => ({ key: `alert-${alert.id}`, title: alert.title, source: "monitoring", severity: alert.severity, detail: [alert.metric, alert.currentValue && `当前 ${alert.currentValue}`, alert.threshold && `阈值 ${alert.threshold}`].filter(Boolean).join(" · ") || "外部监控事件", instanceId: undefined }));
  return [...capacitySignals, ...healthSignals, ...alertSignals].sort((left, right) => (left.severity === "critical" ? -1 : 1) - (right.severity === "critical" ? -1 : 1)).slice(0, 8);
}

export async function getOverview() {
  const db = await getDb();
  if (!db) return emptyOverview;
  const [instances, alerts, executions, integrations] = await Promise.all([
    db.select().from(databaseInstances),
    db.select().from(operationalAlerts),
    db.select().from(runbookExecutions),
    db.select().from(monitoringIntegrations),
  ]);
  return {
    instances: {
      total: instances.length,
      healthy: instances.filter(item => item.healthStatus === "healthy").length,
      warning: instances.filter(item => item.healthStatus === "warning").length,
      critical: instances.filter(item => item.healthStatus === "critical").length,
    },
    alerts: {
      open: alerts.filter(item => item.status === "open").length,
      critical: alerts.filter(item => item.status === "open" && item.severity === "critical").length,
      high: alerts.filter(item => item.status === "open" && item.severity === "high").length,
    },
    executions: {
      active: executions.filter(item => ["queued", "dispatched", "running"].includes(item.status)).length,
      awaitingApproval: executions.filter(item => item.status === "awaiting_approval").length,
      failed: executions.filter(item => item.status === "failed").length,
    },
    integrations: {
      configured: integrations.length,
      connected: integrations.filter(item => item.status === "connected").length,
    },
  };
}

export async function listServerAssets() {
  const db = await getDb();
  return db ? db.select().from(serverAssets).orderBy(desc(serverAssets.updatedAt)) : [];
}

export async function createServerAsset(input: typeof serverAssets.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.insert(serverAssets).values(input);
}

export async function getServerAsset(id: number) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  return (await db.select().from(serverAssets).where(eq(serverAssets.id, id)).limit(1))[0] ?? null;
}

export async function requestServerProbe(id: number, requestedBy: string) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const asset = await getServerAsset(id);
  if (!asset) throw new Error("未找到服务器资产");
  const requestedAt = new Date();
  await db.update(serverAssets).set({ probeRequestedAt: requestedAt, lastProbeMessage: `探活请求已由 ${requestedBy} 排队，等待受控执行节点回报。` }).where(eq(serverAssets.id, id));
  return { id, status: "queued" as const, requestedAt };
}

export async function recordServerProbeResult(id: number, status: "online" | "degraded" | "offline" | "unknown", message: string) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.update(serverAssets).set({ status, lastCheckedAt: new Date(), lastProbeMessage: message }).where(eq(serverAssets.id, id));
  return { id, status, message };
}

export async function listSqlReviewPolicies() {
  const db = await getDb();
  return db ? db.select().from(sqlReviewPolicies).orderBy(desc(sqlReviewPolicies.updatedAt)) : [];
}

export async function createSqlReviewPolicy(input: typeof sqlReviewPolicies.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.insert(sqlReviewPolicies).values(input);
}

export function reviewSqlText(sqlText: string) {
  const normalized = sqlText.trim().replace(/\s+/g, " ");
  const findings: Array<{ rule: string; severity: "error" | "warning" | "info"; message: string }> = [];
  if (!normalized) findings.push({ rule: "SQL_EMPTY", severity: "error", message: "SQL 不能为空。" });
  if (/\b(drop\s+(database|table)|truncate\s+table)\b/i.test(normalized)) findings.push({ rule: "DDL_DESTRUCTIVE", severity: "error", message: "检测到不可逆高风险结构变更，必须人工复核并提供回滚方案。" });
  if (/\b(delete|update)\b/i.test(normalized) && !/\bwhere\b/i.test(normalized)) findings.push({ rule: "DML_NO_WHERE", severity: "error", message: "UPDATE/DELETE 缺少 WHERE 条件，已阻止进入自动执行流程。" });
  if (/select\s+\*/i.test(normalized)) findings.push({ rule: "SELECT_STAR", severity: "warning", message: "建议显式列出字段，避免查询审计与敏感字段控制失效。" });
  if (!findings.length) findings.push({ rule: "SQL_REVIEW_PASS", severity: "info", message: "未命中内置阻断规则，仍需按风险等级完成审批。" });
  return { passed: !findings.some(item => item.severity === "error"), findings };
}

export async function createChangeRequest(input: { title: string; engine: string; sqlText: string; rollbackSql?: string; instanceId?: number; serverAssetId?: number; riskLevel?: "low" | "medium" | "high" | "critical"; requestedBy: string }) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const reviewResult = reviewSqlText(input.sqlText);
  const requestKey = `chg_${nanoid(14)}`;
  const status = reviewResult.passed ? "pending_review" : "rejected";
  await db.insert(changeRequests).values({ requestKey, title: input.title, engine: input.engine, sqlText: input.sqlText, rollbackSql: input.rollbackSql, instanceId: input.instanceId, serverAssetId: input.serverAssetId, riskLevel: input.riskLevel ?? "medium", status, reviewResult, requestedBy: input.requestedBy });
  return { requestKey, status, reviewResult };
}

export async function listChangeRequests() {
  const db = await getDb();
  return db ? db.select().from(changeRequests).orderBy(desc(changeRequests.updatedAt)).limit(30) : [];
}

export async function listQueryAuditRecords() {
  const db = await getDb();
  return db ? db.select().from(queryAuditRecords).orderBy(desc(queryAuditRecords.updatedAt)).limit(30) : [];
}

export async function createQueryAuditRecord(input: { instanceId?: number; engine: string; sqlText: string; requestedBy: string; maskedColumns?: string[] }) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const queryKey = `qry_${nanoid(14)}`;
  const sqlHash = createHash("sha256").update(input.sqlText).digest("hex");
  await db.insert(queryAuditRecords).values({ queryKey, instanceId: input.instanceId, engine: input.engine, sqlHash, status: "pending", maskedColumns: input.maskedColumns ?? [], requestedBy: input.requestedBy });
  return { queryKey, status: "pending" as const };
}

export async function listInstances() {
  const db = await getDb();
  return db ? db.select().from(databaseInstances).orderBy(desc(databaseInstances.updatedAt)) : [];
}

export async function createInstance(input: typeof databaseInstances.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.insert(databaseInstances).values(input);
}

export async function listRunbooks() {
  const db = await getDb();
  return db ? db.select().from(runbooks).orderBy(desc(runbooks.updatedAt)) : [];
}

export async function createRunbook(input: typeof runbooks.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const created = await db.insert(runbooks).values(input).$returningId();
  return created[0]?.id;
}

export async function createIncidentRunbookExecution(input: {
  draft: { title: string; category: typeof runbooks.$inferInsert.category; description?: string; compatibleEngines: string[]; riskLevel: typeof runbooks.$inferInsert.riskLevel; approvalRequired: boolean; steps: Array<{ name: string; action: string; requiresConfirmation?: boolean }>; parameters: Record<string, unknown> };
  instanceId?: number;
  alertId?: number;
  createdBy: string;
}) {
  const runbookId = await createRunbook({ title: input.draft.title, category: input.draft.category, description: input.draft.description, compatibleEngines: input.draft.compatibleEngines, riskLevel: input.draft.riskLevel, approvalRequired: input.draft.approvalRequired, status: "active", steps: input.draft.steps, createdBy: input.createdBy });
  if (!runbookId) throw new Error("智能 Runbook 创建失败");
  return createExecution({ runbookId, instanceId: input.instanceId, triggerSource: "incident_auto", parameters: { ...input.draft.parameters, analysisSource: "incident_auto", alertId: input.alertId }, createdBy: input.createdBy });
}

export async function listExecutions() {
  const db = await getDb();
  return db ? db.select().from(runbookExecutions).orderBy(desc(runbookExecutions.updatedAt)).limit(30) : [];
}

export async function listRecentDispositionRecords() {
  const db = await getDb();
  if (!db) return [];
  return db.select({ executionKey: runbookExecutions.executionKey, runbookTitle: runbookExecutions.runbookTitle, status: runbookExecutions.status, riskLevel: runbookExecutions.riskLevel, updatedAt: runbookExecutions.updatedAt, approvedAt: runbookExecutions.approvedAt, completedAt: runbookExecutions.completedAt }).from(runbookExecutions).orderBy(desc(runbookExecutions.updatedAt)).limit(8);
}

export async function listPerformanceRisks() {
  const db = await getDb();
  if (!db) return [];
  const [instances, alerts] = await Promise.all([db.select().from(databaseInstances), db.select().from(operationalAlerts)]);
  return buildPerformanceRisks(instances, alerts);
}

export async function listExecutionLogs(executionKey: string) {
  const db = await getDb();
  if (!db) return [];
  const execution = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, executionKey)).limit(1))[0];
  if (!execution) return [];
  return db.select().from(executionLogs).where(eq(executionLogs.executionId, execution.id)).orderBy(desc(executionLogs.createdAt));
}

export async function createExecution(input: {
  templateKey?: string;
  runbookId?: number;
  instanceId?: number;
  executorNodeId?: number;
  scheduledAt?: Date;
  triggerSource?: "manual" | "incident_auto" | "scheduled" | "retry";
  parameters?: Record<string, unknown>;
  createdBy: string;
}) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  let source = input.templateKey ? getCatalogRunbook(input.templateKey) : undefined;
  let custom: typeof runbooks.$inferSelect | undefined;
  if (!source && input.runbookId) {
    custom = (await db.select().from(runbooks).where(eq(runbooks.id, input.runbookId)).limit(1))[0];
  }
  if (!source && !custom) throw new Error("未找到可执行的 Runbook");
  const [instance, executor] = await Promise.all([
    input.instanceId ? db.select().from(databaseInstances).where(eq(databaseInstances.id, input.instanceId)).limit(1) : [],
    input.executorNodeId ? db.select().from(controlledExecutorNodes).where(eq(controlledExecutorNodes.id, input.executorNodeId)).limit(1) : [],
  ]);
  assertExecutionPolicy({
    runbook: { title: source?.title ?? custom!.title, compatibleEngines: source?.compatibleEngines ?? custom!.compatibleEngines, status: custom?.status },
    requestedInstanceId: input.instanceId,
    instance: instance[0],
    requestedExecutorNodeId: input.executorNodeId,
    executor: executor[0],
  });
  const category = source?.category ?? custom!.category;
  const riskLevel = source?.riskLevel ?? custom!.riskLevel;
  const approvalRequired = source?.approvalRequired ?? custom!.approvalRequired;
  const scheduledAt = input.scheduledAt && input.scheduledAt.getTime() > Date.now() ? input.scheduledAt : undefined;
  const initialStatus = scheduledAt ? "scheduled" : approvalRequired ? "awaiting_approval" : "queued";
  const triggerSource = scheduledAt ? "scheduled" : input.triggerSource ?? "manual";
  const executionKey = `exec_${nanoid(14)}`;
  await db.insert(runbookExecutions).values({
    executionKey,
    runbookId: custom?.id,
    templateKey: source?.key,
    runbookTitle: source?.title ?? custom!.title,
    instanceId: input.instanceId,
    executorNodeId: input.executorNodeId,
    category,
    riskLevel,
    status: initialStatus,
    triggerSource,
    scheduledAt,
    input: input.parameters ?? {},
    confirmationRequired: approvalRequired,
    createdBy: input.createdBy,
  });
  const execution = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, executionKey)).limit(1))[0];
  if (execution) {
    await db.insert(executionLogs).values({
      executionId: execution.id,
      level: "audit",
      phase: "control_plane",
      message: scheduledAt ? `执行单已创建，计划于 ${scheduledAt.toISOString()} 进入调度流程。` : approvalRequired ? "执行单已创建，等待人工确认。" : "执行单已创建，等待受控执行节点接管。",
      metadata: { executionKey, riskLevel },
    });
  }
  return { executionKey, status: initialStatus };
}

export async function cancelExecution(executionKey: string, cancelledBy: string) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const execution = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, executionKey)).limit(1))[0];
  if (!execution) throw new Error("未找到执行单");
  assertCancellableExecution(execution.status);
  await db.update(runbookExecutions).set({ status: "cancelled", completedAt: new Date() }).where(eq(runbookExecutions.id, execution.id));
  await db.insert(executionLogs).values({ executionId: execution.id, level: "audit", phase: "control_plane", message: `执行单已由 ${cancelledBy} 撤销。`, metadata: { action: "cancel", cancelledBy } });
  return { executionKey, status: "cancelled" as const };
}

export async function retryExecution(executionKey: string, createdBy: string) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const source = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, executionKey)).limit(1))[0];
  if (!source) throw new Error("未找到执行单");
  assertRetryableExecution(source.status);
  const nextKey = `exec_${nanoid(14)}`;
  const nextStatus = source.confirmationRequired ? "awaiting_approval" : "queued";
  await db.insert(runbookExecutions).values({ executionKey: nextKey, runbookId: source.runbookId, templateKey: source.templateKey, runbookTitle: source.runbookTitle, instanceId: source.instanceId, executorNodeId: source.executorNodeId, category: source.category, riskLevel: source.riskLevel, status: nextStatus, triggerSource: "retry", retryOfExecutionId: source.id, input: source.input, confirmationRequired: source.confirmationRequired, createdBy });
  const retry = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, nextKey)).limit(1))[0];
  if (retry) await db.insert(executionLogs).values({ executionId: retry.id, level: "audit", phase: "control_plane", message: `由执行单 ${executionKey} 触发重试，参数已复制并等待后续处理。`, metadata: { action: "retry", retryOf: executionKey } });
  return { executionKey: nextKey, status: nextStatus };
}

export async function approveExecution(executionKey: string, approvedBy: string, note?: string) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  const execution = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, executionKey)).limit(1))[0];
  if (!execution) throw new Error("未找到执行单");
  if (execution.status !== "awaiting_approval") throw new Error("该执行单当前无需确认或已被处理");
  await db.update(runbookExecutions).set({ status: "queued", approvedBy, approvalNote: note, approvedAt: new Date() }).where(eq(runbookExecutions.id, execution.id));
  await db.insert(executionLogs).values({ executionId: execution.id, level: "audit", phase: "approval", message: "人工确认已完成，任务已进入派发队列。", metadata: { approvedBy } });
}

export async function listIntegrations() {
  const db = await getDb();
  return db ? db.select().from(monitoringIntegrations).orderBy(desc(monitoringIntegrations.updatedAt)) : [];
}

export async function getIntegrationMapping(provider: "zabbix" | "prometheus" | "xxl_job") {
  const db = await getDb();
  if (!db) throw new Error("operations database unavailable");
  const integration = (await db.select().from(monitoringIntegrations).where(eq(monitoringIntegrations.provider, provider)).orderBy(desc(monitoringIntegrations.updatedAt)).limit(1))[0];
  if (!integration) throw new Error(`no configured ${provider} integration`);
  return integration.mapping ?? {};
}

export async function createIntegration(input: typeof monitoringIntegrations.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.insert(monitoringIntegrations).values(input);
}

export async function listNodes() {
  const db = await getDb();
  return db ? db.select().from(controlledExecutorNodes).orderBy(desc(controlledExecutorNodes.updatedAt)) : [];
}

export async function registerNode(input: typeof controlledExecutorNodes.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.insert(controlledExecutorNodes).values(input);
}

export async function listAlerts() {
  const db = await getDb();
  return db ? db.select().from(operationalAlerts).orderBy(desc(operationalAlerts.occurredAt)).limit(30) : [];
}

export async function buildIncidentContext(input: { context?: string; instanceId?: number; alertId?: number }) {
  const fragments = input.context?.trim() ? [`人工补充上下文：${input.context.trim()}`] : [];
  const db = await getDb();
  if (!db) return fragments.join("\n\n");
  const alert = input.alertId ? (await db.select().from(operationalAlerts).where(eq(operationalAlerts.id, input.alertId)).limit(1))[0] : undefined;
  const targetInstanceId = input.instanceId ?? alert?.instanceId ?? undefined;
  const instance = targetInstanceId ? (await db.select().from(databaseInstances).where(eq(databaseInstances.id, targetInstanceId)).limit(1))[0] : undefined;
  if (alert) fragments.push(`平台告警：标题=${alert.title}；严重度=${alert.severity}；状态=${alert.status}；指标=${alert.metric ?? "未映射"}；当前值=${alert.currentValue ?? "未提供"}；阈值=${alert.threshold ?? "未提供"}；上下文=${JSON.stringify(alert.context ?? {})}`);
  if (instance) fragments.push(`实例上下文：名称=${instance.name}；引擎=${instance.engine}；版本=${instance.version ?? "未采集"}；环境=${instance.environment}；健康=${instance.healthStatus}；健康分=${instance.healthScore}；连接=${instance.connectionStatus}；容量=${instance.usedCapacityGb ?? "未采集"}/${instance.capacityGb ?? "未采集"}GB；标签=${(instance.tags ?? []).join(",")}`);
  const [allInstances, allAlerts] = await Promise.all([db.select().from(databaseInstances), db.select().from(operationalAlerts)]);
  const risks = buildPerformanceRisks(allInstances, allAlerts).filter(risk => !targetInstanceId || risk.instanceId === targetInstanceId || risk.source === "monitoring");
  if (risks.length) fragments.push(`平台风险信号：${risks.map(risk => `${risk.severity}:${risk.title}(${risk.detail})`).join("；")}`);
  if (targetInstanceId) {
    const executions = await db.select().from(runbookExecutions).where(eq(runbookExecutions.instanceId, targetInstanceId)).orderBy(desc(runbookExecutions.updatedAt)).limit(3);
    if (executions.length) fragments.push(`近期执行单：${executions.map(item => `${item.runbookTitle}/${item.status}/${item.executionKey}`).join("；")}`);
    const executionIds = executions.map(item => item.id);
    if (executionIds.length) {
      const logs = await db.select({ phase: executionLogs.phase, level: executionLogs.level, message: executionLogs.message, createdAt: executionLogs.createdAt }).from(executionLogs).where(inArray(executionLogs.executionId, executionIds)).orderBy(desc(executionLogs.createdAt)).limit(8);
      if (logs.length) fragments.push(`近期脱敏执行日志：${logs.map(log => `${log.level}/${log.phase}:${log.message}`).join("；")}`);
    }
  }
  return fragments.join("\n\n");
}

export async function recordAlert(input: typeof operationalAlerts.$inferInsert) {
  const db = await getDb();
  if (!db) throw new Error("运维数据服务不可用");
  await db.insert(operationalAlerts).values(input);
  if (input.status !== "resolved" && shouldNotifySeverity(input.severity)) {
    const title = `[${input.severity.toUpperCase()}] 数据库运维事件`;
    const content = `${input.title}${input.metric ? `；指标：${input.metric}` : ""}${input.currentValue ? `；当前值：${input.currentValue}` : ""}`;
    let status: "delivered" | "failed" = "delivered";
    try {
      const delivered = await notifyOwner({ title, content });
      if (!delivered) status = "failed";
    } catch {
      status = "failed";
    }
    await db.insert(notificationEvents).values({ category: "high_priority_alert", severity: input.severity, title, content, status, deliveredAt: status === "delivered" ? new Date() : undefined });
  }
}

export async function ingestExternalAlert(input: { provider: string; externalId?: string; title: string; severity: "critical" | "high" | "medium" | "low" | "info"; status: "open" | "acknowledged" | "resolved"; metric?: string; currentValue?: string; threshold?: string; instanceId?: number; context: Record<string, unknown> }) {
  const db = await getDb();
  if (!db) throw new Error("operations database unavailable");
  const integration = (await db.select().from(monitoringIntegrations).where(eq(monitoringIntegrations.provider, input.provider as "zabbix" | "prometheus" | "xxl_job")).orderBy(desc(monitoringIntegrations.updatedAt)).limit(1))[0];
  if (!integration) throw new Error(`no configured ${input.provider} integration`);
  const existing = input.externalId ? (await db.select().from(operationalAlerts).where(and(eq(operationalAlerts.integrationId, integration.id), eq(operationalAlerts.externalId, input.externalId))).limit(1))[0] : undefined;
  await db.update(monitoringIntegrations).set({ status: "connected", lastSyncAt: new Date() }).where(eq(monitoringIntegrations.id, integration.id));
  if (existing) {
    await db.update(operationalAlerts).set({ title: input.title, severity: input.severity, status: input.status, metric: input.metric, currentValue: input.currentValue, threshold: input.threshold, context: input.context, resolvedAt: input.status === "resolved" ? new Date() : undefined }).where(eq(operationalAlerts.id, existing.id));
    return { id: existing.id, action: "updated" as const };
  }
  await recordAlert({ externalId: input.externalId, integrationId: integration.id, instanceId: input.instanceId, title: input.title, severity: input.severity, status: input.status, metric: input.metric, currentValue: input.currentValue, threshold: input.threshold, context: input.context, resolvedAt: input.status === "resolved" ? new Date() : undefined });
  return { action: "created" as const };
}

export async function ingestExternalMetric(input: { provider: string; metric: string; value: string; unit?: string; instanceId?: number; labels: Record<string, unknown> }) {
  const db = await getDb();
  if (!db) throw new Error("operations database unavailable");
  const integration = (await db.select().from(monitoringIntegrations).where(eq(monitoringIntegrations.provider, input.provider as "zabbix" | "prometheus")).orderBy(desc(monitoringIntegrations.updatedAt)).limit(1))[0];
  if (!integration) throw new Error(`no configured ${input.provider} integration`);
  await db.insert(monitoringMetricSnapshots).values({ integrationId: integration.id, instanceId: input.instanceId, metric: input.metric, value: input.value, unit: input.unit, labels: input.labels });
  await db.update(monitoringIntegrations).set({ status: "connected", lastSyncAt: new Date() }).where(eq(monitoringIntegrations.id, integration.id));
  return { metric: input.metric, action: "recorded" as const };
}

export async function ingestExternalTaskStatus(input: { provider: string; executionKey: string; status: "queued" | "dispatched" | "running" | "succeeded" | "failed" | "cancelled"; message?: string; result?: Record<string, unknown> }) {
  if (input.provider !== "xxl_job") throw new Error("task status sync is only supported for xxl_job");
  const db = await getDb();
  if (!db) throw new Error("operations database unavailable");
  const execution = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, input.executionKey)).limit(1))[0];
  if (!execution) throw new Error("runbook execution not found");
  const completedAt = ["succeeded", "failed", "cancelled"].includes(input.status) ? new Date() : undefined;
  await db.update(runbookExecutions).set({ status: input.status, completedAt, result: input.result }).where(eq(runbookExecutions.id, execution.id));
  await db.insert(executionLogs).values({ executionId: execution.id, level: input.status === "failed" ? "error" : "info", phase: "xxl_job_sync", message: input.message ?? `XXL-Job 状态同步：${input.status}`, metadata: { provider: input.provider, status: input.status } });
  return { executionKey: execution.executionKey, status: input.status };
}

export async function listRecentMetrics() {
  const db = await getDb();
  return db ? db.select().from(monitoringMetricSnapshots).orderBy(desc(monitoringMetricSnapshots.occurredAt)).limit(30) : [];
}

export async function generateIncidentAnalysis(input: { context?: string; instanceId?: number; alertId?: number; createdBy: string }) {
  const assembledContext = await buildIncidentContext(input);
  if (!assembledContext) throw new Error("请提供诊断上下文，或选择已登记实例 / 告警");
  const { data: models } = await listLLMModels();
  const model = models.find(item => item.id === "gpt-5")?.id ?? models.find(item => item.id.startsWith("gpt-5"))?.id;
  if (!model) throw new Error("当前没有可用于智能诊断的模型");
  const response = await invokeLLM({
    model,
    reasoning: { effort: "low" },
    messages: [
      { role: "system", content: "你是资深数据库 SRE。只基于提供的脱敏运维上下文诊断。不能把建议描述为已执行，不能索要或输出口令、连接串或私钥。输出应保守、可审计，并将任何高风险动作标为需要人工确认。" },
      { role: "user", content: `请分析以下数据库运维上下文：\n${assembledContext}` },
    ],
    response_format: {
      type: "json_schema",
      json_schema: {
        name: "db_incident_analysis",
        strict: true,
        schema: {
          type: "object",
          properties: {
            rootCause: { type: "string" },
            confidence: { type: "number" },
            impact: { type: "string" },
            risk: { type: "string" },
            evidence: { type: "array", items: { type: "string" } },
            recommendations: { type: "array", items: { type: "string" } },
            runbookDraft: {
              type: "object",
              properties: {
                title: { type: "string" },
                category: { type: "string", enum: ["deployment", "backup_recovery", "inspection", "self_healing"] },
                riskLevel: { type: "string", enum: ["low", "medium", "high", "critical"] },
                approvalRequired: { type: "boolean" },
                compatibleEngines: { type: "array", items: { type: "string" } },
                parameters: { type: "object", additionalProperties: true },
                steps: { type: "array", items: { type: "object", properties: { name: { type: "string" }, action: { type: "string" }, requiresConfirmation: { type: "boolean" } }, required: ["name", "action", "requiresConfirmation"], additionalProperties: false } },
              },
              required: ["title", "category", "riskLevel", "approvalRequired", "compatibleEngines", "parameters", "steps"],
              additionalProperties: false,
            },
            requiresHumanConfirmation: { type: "boolean" },
          },
          required: ["rootCause", "confidence", "impact", "risk", "evidence", "recommendations", "runbookDraft", "requiresHumanConfirmation"],
          additionalProperties: false,
        },
      },
    },
  });
  const content = response.choices[0]?.message.content;
  if (!content || typeof content !== "string") throw new Error("智能诊断未返回有效结果");
  const result = JSON.parse(content) as Record<string, unknown>;
  const analysisKey = `ana_${nanoid(14)}`;
  const db = await getDb();
  if (db) {
    await db.insert(incidentAnalyses).values({ analysisKey, instanceId: input.instanceId, alertId: input.alertId, status: "completed", model, contextDigest: assembledContext.slice(0, 1200), result, createdBy: input.createdBy });
  }
  return { analysisKey, model, result };
}
