import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../db", () => ({ getDb: vi.fn() }));

import { getDb } from "../db";
import { createExecution } from "./service";

describe("智能自愈执行单", () => {
  beforeEach(() => vi.clearAllMocks());

  it("对已创建的智能 Runbook 发起执行时持久化 incident_auto 触发来源", async () => {
    const createdValues: unknown[] = [];
    const customRunbook = { id: 25, title: "连接池受控缓解", category: "self_healing" as const, riskLevel: "high" as const, approvalRequired: true, compatibleEngines: ["mysql"], status: "active" as const };
    const createdExecution = { id: 91, executionKey: "exec_incident_auto_01" };
    const selectRows = [[customRunbook], [createdExecution]];
    const db = {
      select: vi.fn(() => ({ from: vi.fn(() => ({ where: vi.fn(() => ({ limit: vi.fn(async () => selectRows.shift() ?? []) })) })) })),
      insert: vi.fn(() => ({ values: vi.fn(async (value: unknown) => { createdValues.push(value); }) })),
    };
    vi.mocked(getDb).mockResolvedValue(db as never);

    const result = await createExecution({ runbookId: 25, triggerSource: "incident_auto", parameters: { alertId: 88, analysisSource: "incident_auto" }, createdBy: "operator-01" });

    expect(result.status).toBe("awaiting_approval");
    expect(createdValues[0]).toMatchObject({ runbookId: 25, triggerSource: "incident_auto", status: "awaiting_approval", input: { alertId: 88, analysisSource: "incident_auto" } });
    expect(createdValues[1]).toMatchObject({ executionId: 91, phase: "control_plane" });
  });
});
