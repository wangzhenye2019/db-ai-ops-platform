import { describe, expect, it } from "vitest";
import { approvalInputSchema, assetInputSchema, executionInputSchema, incidentOutputSchema } from "../routers/ops";
import { buildPerformanceRisks, shouldNotifySeverity } from "./service";

describe("运维输入契约", () => {
  it("接受受控资产登记的有效输入并拒绝非法端口", () => {
    const valid = assetInputSchema.safeParse({ name: "orders-mysql-prod", engine: "mysql", host: "10.0.2.15", port: 3306, environment: "production", healthStatus: "unknown", healthScore: 0, capabilities: [], tags: ["核心"] });
    expect(valid.success).toBe(true);
    const invalid = assetInputSchema.safeParse({ name: "bad", engine: "mysql", host: "db", port: 70000, environment: "production", healthStatus: "unknown", healthScore: 0, capabilities: [], tags: [] });
    expect(invalid.success).toBe(false);
    const invalidCapacity = assetInputSchema.safeParse({ name: "capacity-invalid", engine: "mysql", host: "db", port: 3306, capacityGb: 100, usedCapacityGb: 101, environment: "production", healthStatus: "unknown", healthScore: 0, capabilities: [], tags: [] });
    expect(invalidCapacity.success).toBe(false);
  });

  it("要求执行单选择 Runbook，且审批操作必须显式确认", () => {
    expect(executionInputSchema.safeParse({ parameters: {} }).success).toBe(false);
    expect(executionInputSchema.safeParse({ templateKey: "backup-verify", parameters: { scope: "full" } }).success).toBe(true);
    const scheduled = executionInputSchema.safeParse({ templateKey: "baseline-inspection", scheduledAt: "2026-08-28T09:30:00.000Z", parameters: { scope: "metrics" } });
    expect(scheduled.success).toBe(true);
    if (scheduled.success) expect(scheduled.data.scheduledAt).toBeInstanceOf(Date);
    expect(executionInputSchema.safeParse({ templateKey: "connection-relief", triggerSource: "incident_auto" }).success).toBe(true);
    expect(executionInputSchema.safeParse({ templateKey: "backup-verify", runbookId: 1 }).success).toBe(false);
    expect(approvalInputSchema.safeParse({ executionKey: "exec_123456789", confirmed: false }).success).toBe(false);
    expect(approvalInputSchema.safeParse({ executionKey: "exec_123456789", confirmed: true }).success).toBe(true);
  });

  it("要求智能分析输出完整且可审计的结构", () => {
    const output = incidentOutputSchema.safeParse({ rootCause: "连接泄漏", confidence: 0.76, impact: "请求超时", risk: "会话耗尽", evidence: ["连接数持续上升"], recommendations: ["限制新建连接"], runbookDraft: { title: "连接池压力缓解", category: "self_healing", riskLevel: "high", approvalRequired: true, compatibleEngines: ["mysql"], parameters: { scope: "sessions" }, steps: [{ name: "采集会话快照", action: "assess_sessions", requiresConfirmation: false }] }, requiresHumanConfirmation: true });
    expect(output.success).toBe(true);
    expect(incidentOutputSchema.safeParse({ rootCause: "缺字段" }).success).toBe(false);
  });
});

describe("风险与通知策略", () => {
  it("识别高容量、健康异常与监控告警信号，并将严重信号置顶", () => {
    const risks = buildPerformanceRisks(
      [{ id: 1, name: "finance-primary", healthStatus: "critical", capacityGb: 100, usedCapacityGb: 95 }],
      [{ id: 8, title: "连接数过高", severity: "high", status: "open", metric: "connections", currentValue: "980", threshold: "800" }],
    );
    expect(risks).toHaveLength(3);
    expect(risks[0]?.severity).toBe("critical");
    expect(risks.map(item => item.source)).toContain("monitoring");
  });

  it("仅向负责人升级严重和高优先级事件", () => {
    expect(shouldNotifySeverity("critical")).toBe(true);
    expect(shouldNotifySeverity("high")).toBe(true);
    expect(shouldNotifySeverity("medium")).toBe(false);
    expect(shouldNotifySeverity(undefined)).toBe(false);
  });
});
