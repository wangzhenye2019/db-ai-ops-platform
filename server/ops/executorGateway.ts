import { and, asc, eq, isNull, or } from "drizzle-orm";
import type { Express, Request } from "express";
import { controlledExecutorNodes, executionLogs, notificationEvents, runbookExecutions } from "../../drizzle/schema";
import { recordServerProbeResult } from "./service";
import { getDb } from "../db";
import { notifyOwner } from "../_core/notification";
import { LEASE_WINDOW_MS, createLeaseToken, hasMatchingSecret, hasValidLease } from "./executorSecurity";

function getGatewaySecret() {
  return process.env.EXECUTOR_GATEWAY_SHARED_SECRET;
}

function stringList(value: unknown) {
  return Array.isArray(value) ? value.filter(item => typeof item === "string").slice(0, 30) : undefined;
}

export function isAuthorizedExecutorRequest(req: Request) {
  const received = req.header("x-executor-secret") ?? undefined;
  return hasMatchingSecret(received, getGatewaySecret());
}

function rejectUnauthorized(req: Request, res: Parameters<Express["get"]>[1] extends (req: Request, res: infer Res) => unknown ? Res : never) {
  if (isAuthorizedExecutorRequest(req)) return false;
  res.status(401).json({ ok: false, error: "executor authentication required" });
  return true;
}

export function registerExecutorGateway(app: Express) {
  app.get("/api/executor/health", (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    return res.json({ ok: true, service: "db-control-executor-gateway", timestamp: new Date().toISOString() });
  });

  app.post("/api/executor/heartbeat", async (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    const nodeKey = typeof req.body?.nodeKey === "string" ? req.body.nodeKey.trim() : "";
    if (!nodeKey) return res.status(400).json({ ok: false, error: "nodeKey required" });
    const db = await getDb();
    if (!db) return res.status(503).json({ ok: false, error: "operations database unavailable" });
    const node = (await db.select().from(controlledExecutorNodes).where(eq(controlledExecutorNodes.nodeKey, nodeKey)).limit(1))[0];
    if (!node) return res.status(404).json({ ok: false, error: "executor node not registered" });
    await db.update(controlledExecutorNodes).set({ status: "online", lastHeartbeatAt: new Date(), capabilities: stringList(req.body?.capabilities) ?? node.capabilities, supportedEngines: stringList(req.body?.supportedEngines) ?? node.supportedEngines }).where(eq(controlledExecutorNodes.id, node.id));
    return res.json({ ok: true, nodeKey, heartbeatAt: new Date().toISOString() });
  });

  app.post("/api/executor/claim", async (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    const nodeKey = typeof req.body?.nodeKey === "string" ? req.body.nodeKey.trim() : "";
    if (!nodeKey) return res.status(400).json({ ok: false, error: "nodeKey required" });
    const db = await getDb();
    if (!db) return res.status(503).json({ ok: false, error: "operations database unavailable" });
    const node = (await db.select().from(controlledExecutorNodes).where(eq(controlledExecutorNodes.nodeKey, nodeKey)).limit(1))[0];
    if (!node) return res.status(404).json({ ok: false, error: "executor node not registered" });
    if (node.status !== "online") return res.status(409).json({ ok: false, error: "executor node is not online" });
    const execution = (await db.select().from(runbookExecutions).where(and(eq(runbookExecutions.status, "queued"), or(eq(runbookExecutions.executorNodeId, node.id), isNull(runbookExecutions.executorNodeId)))).orderBy(asc(runbookExecutions.createdAt)).limit(1))[0];
    if (!execution) return res.json({ ok: true, task: null });
    const now = new Date();
    await db.update(runbookExecutions).set({ executorNodeId: node.id, status: "running", dispatchedAt: now, startedAt: now }).where(and(eq(runbookExecutions.id, execution.id), eq(runbookExecutions.status, "queued")));
    await db.insert(executionLogs).values({ executionId: execution.id, level: "audit", phase: "executor_dispatch", message: "受控执行节点已领取已确认任务。", metadata: { nodeKey } });
    const expiresAt = Date.now() + LEASE_WINDOW_MS;
    const secret = getGatewaySecret();
    if (!secret) return res.status(503).json({ ok: false, error: "executor gateway secret unavailable" });
    return res.json({ ok: true, task: { executionKey: execution.executionKey, runbookTitle: execution.runbookTitle, templateKey: execution.templateKey, category: execution.category, riskLevel: execution.riskLevel, parameters: execution.input ?? {}, lease: { expiresAt, token: createLeaseToken(nodeKey, execution.executionKey, expiresAt, secret) } } });
  });

  app.post("/api/executor/server-probe-result", async (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    const nodeKey = typeof req.body?.nodeKey === "string" ? req.body.nodeKey.trim() : "";
    const serverAssetId = Number(req.body?.serverAssetId);
    const status = req.body?.status;
    const message = typeof req.body?.message === "string" ? req.body.message.slice(0, 4000) : "受控节点回传服务器探活结果。";
    if (!nodeKey || !Number.isInteger(serverAssetId) || serverAssetId <= 0 || !["online", "degraded", "offline", "unknown"].includes(status)) return res.status(400).json({ ok: false, error: "nodeKey, serverAssetId and valid status required" });
    const db = await getDb();
    if (!db) return res.status(503).json({ ok: false, error: "operations database unavailable" });
    const node = (await db.select().from(controlledExecutorNodes).where(eq(controlledExecutorNodes.nodeKey, nodeKey)).limit(1))[0];
    if (!node) return res.status(404).json({ ok: false, error: "executor node not registered" });
    if (node.serverAssetId !== serverAssetId) return res.status(403).json({ ok: false, error: "executor node is not assigned to this server asset" });
    const result = await recordServerProbeResult(serverAssetId, status as "online" | "degraded" | "offline" | "unknown", message);
    return res.json({ ok: true, ...result, nodeKey });
  });

  app.post("/api/executor/result", async (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    const nodeKey = typeof req.body?.nodeKey === "string" ? req.body.nodeKey.trim() : "";
    const executionKey = typeof req.body?.executionKey === "string" ? req.body.executionKey.trim() : "";
    const leaseToken = typeof req.body?.leaseToken === "string" ? req.body.leaseToken : "";
    const leaseExpiresAt = typeof req.body?.leaseExpiresAt === "number" ? req.body.leaseExpiresAt : Number.NaN;
    const status = req.body?.status;
    if (!nodeKey || !executionKey || !["succeeded", "failed", "cancelled"].includes(status)) return res.status(400).json({ ok: false, error: "nodeKey, executionKey and terminal status required" });
    const secret = getGatewaySecret();
    if (!secret || !hasValidLease(nodeKey, executionKey, leaseExpiresAt, leaseToken, secret)) return res.status(403).json({ ok: false, error: "invalid or expired execution lease" });
    const db = await getDb();
    if (!db) return res.status(503).json({ ok: false, error: "operations database unavailable" });
    const node = (await db.select().from(controlledExecutorNodes).where(eq(controlledExecutorNodes.nodeKey, nodeKey)).limit(1))[0];
    const execution = (await db.select().from(runbookExecutions).where(eq(runbookExecutions.executionKey, executionKey)).limit(1))[0];
    if (!node || !execution || execution.executorNodeId !== node.id || execution.status !== "running") return res.status(409).json({ ok: false, error: "execution is not leased by this node" });
    const result = typeof req.body?.result === "object" && req.body.result !== null ? req.body.result as Record<string, unknown> : {};
    const message = typeof req.body?.message === "string" ? req.body.message.slice(0, 4000) : `执行节点回传最终状态：${status}`;
    await db.update(runbookExecutions).set({ status, completedAt: new Date(), result }).where(eq(runbookExecutions.id, execution.id));
    await db.insert(executionLogs).values({ executionId: execution.id, level: status === "succeeded" ? "info" : "error", phase: "executor_result", message, metadata: { nodeKey, terminalStatus: status } });
    if (status === "failed" && (execution.category === "backup_recovery" || execution.category === "self_healing")) {
      const title = `[${execution.category === "backup_recovery" ? "BACKUP" : "SELF-HEALING"} FAILED] ${execution.runbookTitle}`;
      const content = `执行单 ${execution.executionKey} 由节点 ${nodeKey} 回传失败。${message}`;
      let notificationStatus: "delivered" | "failed" = "delivered";
      try { if (!await notifyOwner({ title, content })) notificationStatus = "failed"; } catch { notificationStatus = "failed"; }
      await db.insert(notificationEvents).values({ category: "execution_failure", severity: "high", title, content, status: notificationStatus, sourceExecutionKey: execution.executionKey, deliveredAt: notificationStatus === "delivered" ? new Date() : undefined });
    }
    return res.json({ ok: true, executionKey, status });
  });
}
