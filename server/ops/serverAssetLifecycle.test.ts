import { describe, expect, it, vi } from "vitest";
import { serverAssets } from "../../drizzle/schema";

const getDb = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getDb }));

import { createServerAsset, getServerAsset, listServerAssets, recordServerProbeResult, requestServerProbe } from "./service";

describe("服务器资产生命周期", () => {
  it("支持登记、详情读取、受控探活排队和真实回报更新", async () => {
    const records: Record<string, unknown>[] = [];
    const db = {
      select: () => ({
        from: (table: unknown) => ({
          orderBy: async () => table === serverAssets ? records : [],
          where: () => ({ limit: async () => records.filter(item => item.id === 1) }),
        }),
      }),
      insert: () => ({ values: async (value: Record<string, unknown>) => { records.push({ id: 1, ...value }); } }),
      update: () => ({ set: (values: Record<string, unknown>) => ({ where: async () => Object.assign(records[0], values) }) }),
    };
    getDb.mockResolvedValue(db);

    await createServerAsset({ name: "ops-node-01", hostname: "ops-node-01.internal", status: "unknown", capabilities: ["agent"] });
    await expect(listServerAssets()).resolves.toHaveLength(1);
    await expect(getServerAsset(1)).resolves.toMatchObject({ hostname: "ops-node-01.internal" });

    const queued = await requestServerProbe(1, "local:admin");
    expect(queued.status).toBe("queued");
    expect(records[0].lastProbeMessage).toContain("等待受控执行节点回报");

    const result = await recordServerProbeResult(1, "online", "agent heartbeat ok");
    expect(result).toMatchObject({ id: 1, status: "online" });
    expect(records[0]).toMatchObject({ status: "online", lastProbeMessage: "agent heartbeat ok" });
  });
});
