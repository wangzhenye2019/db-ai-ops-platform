import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../db", () => ({ getDb: vi.fn() }));
import { getDb } from "../db";
import { createIncidentRunbookExecution } from "./service";

describe("智能处置编排", () => {
  beforeEach(() => vi.clearAllMocks());
  it("使用新建 Runbook 的返回标识创建 incident_auto 执行单", async () => {
    const writes: unknown[] = []; let insertIndex = 0;
    const customRunbook = { id: 70, title: "智能连接缓解", category: "self_healing" as const, riskLevel: "high" as const, approvalRequired: true, compatibleEngines: ["mysql"], status: "active" as const };
    const createdExecution = { id: 71, executionKey: "exec_incident_chain" }; const selections = [[customRunbook], [createdExecution]];
    const db = { select: vi.fn(() => ({ from: vi.fn(() => ({ where: vi.fn(() => ({ limit: vi.fn(async () => selections.shift() ?? []) })) })) })), insert: vi.fn(() => ({ values: vi.fn((value: unknown) => { writes.push(value); return insertIndex++ === 0 ? { $returningId: async () => [{ id: 70 }] } : Promise.resolve(); }) })) };
    vi.mocked(getDb).mockResolvedValue(db as never);
    await expect(createIncidentRunbookExecution({ draft: { title: "智能连接缓解", category: "self_healing", compatibleEngines: ["mysql"], riskLevel: "high", approvalRequired: true, parameters: { action: "relieve" }, steps: [{ name: "评估", action: "assess" }] }, alertId: 12, createdBy: "operator-01" })).resolves.toMatchObject({ status: "awaiting_approval" });
    expect(writes[0]).toMatchObject({ title: "智能连接缓解", status: "active" });
    expect(writes[1]).toMatchObject({ runbookId: 70, triggerSource: "incident_auto", input: { action: "relieve", analysisSource: "incident_auto", alertId: 12 } });
  });
});
