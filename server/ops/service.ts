import { and, desc, eq, inArray } from "drizzle-orm";
import { nanoid } from "nanoid";
import {
  controlledExecutorNodes, databaseInstances, executionLogs, incidentAnalyses,
  monitoringIntegrations, notificationEvents, operationalAlerts, runbookExecutions, runbooks,
} from "../../drizzle/schema";
import { getDb } from "../db";
import { invokeLLM, listLLMModels } from "../_core/llm";
import { notifyOwner } from "../_core/notification";
import { getCatalogRunbook } from "./catalog";

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
  await db.insert(runbooks).values(input);
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
  const category = source?.category ?? custom!.category;
  const riskLevel = source?.riskLevel ?? custom!.riskLevel;
  const approvalRequired = source?.approvalRequired ?? custom!.approvalRequired;
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
    status: approvalRequired ? "awaiting_approval" : "queued",
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
      message: approvalRequired ? "执行单已创建，等待人工确认。" : "执行单已创建，等待受控执行节点接管。",
      metadata: { executionKey, riskLevel },
    });
  }
  return { executionKey, status: approvalRequired ? "awaiting_approval" : "queued" };
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
  if (shouldNotifySeverity(input.severity)) {
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
