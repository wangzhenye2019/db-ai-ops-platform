import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../db", () => ({ getDb: vi.fn() }));

import { getDb } from "../db";
import { cancelExecution, retryExecution } from "./service";

function sampleExecution(status: "scheduled" | "failed" | "cancelled" = "failed") {
  return { id: 41, executionKey: "exec_original_001", runbookId: 8, templateKey: "backup-verify", runbookTitle: "备份执行与可恢复性校验", instanceId: 3, executorNodeId: 4, category: "backup_recovery" as const, riskLevel: "high" as const, status, triggerSource: "manual" as const, input: { scope: "full", retention: 7 }, confirmationRequired: true };
}

function buildDb(selectRows: unknown[][]) {
  const updates: unknown[] = []; const inserts: unknown[] = [];
  const db = {
    select: vi.fn(() => ({ from: vi.fn(() => ({ where: vi.fn(() => ({ limit: vi.fn(async () => selectRows.shift() ?? []) })) })) })),
    update: vi.fn(() => ({ set: vi.fn((value: unknown) => { updates.push(value); return { where: vi.fn(async () => undefined) }; }) })),
    insert: vi.fn(() => ({ values: vi.fn(async (value: unknown) => { inserts.push(value); }) })),
  };
  return { db, updates, inserts };
}

describe("执行单生命周期服务", () => {
  beforeEach(() => vi.clearAllMocks());

  it("撤销可撤销任务并写入审计记录", async () => {
    const fixture = buildDb([[sampleExecution("scheduled")]]);
    vi.mocked(getDb).mockResolvedValue(fixture.db as never);
    await expect(cancelExecution("exec_original_001", "admin-01")).resolves.toEqual({ executionKey: "exec_original_001", status: "cancelled" });
    expect(fixture.updates[0]).toMatchObject({ status: "cancelled" });
    expect(fixture.inserts[0]).toMatchObject({ executionId: 41, phase: "control_plane", metadata: { action: "cancel", cancelledBy: "admin-01" } });
  });

  it("从失败任务复制参数创建可审批的重试执行单，并记录来源和审计日志", async () => {
    const retryRecord = { ...sampleExecution("awaiting_approval"), id: 42, executionKey: "exec_retry_002", triggerSource: "retry" as const, retryOfExecutionId: 41 };
    const fixture = buildDb([[sampleExecution("failed")], [retryRecord]]);
    vi.mocked(getDb).mockResolvedValue(fixture.db as never);
    const result = await retryExecution("exec_original_001", "admin-01");
    expect(result.status).toBe("awaiting_approval");
    expect(fixture.inserts[0]).toMatchObject({ triggerSource: "retry", retryOfExecutionId: 41, input: { scope: "full", retention: 7 }, createdBy: "admin-01" });
    expect(fixture.inserts[1]).toMatchObject({ executionId: 42, phase: "control_plane", metadata: { action: "retry", retryOf: "exec_original_001" } });
  });
});
