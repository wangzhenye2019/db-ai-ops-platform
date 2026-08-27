import express from "express";
import type { AddressInfo } from "net";
import { describe, expect, it, vi } from "vitest";

const getDb = vi.hoisted(() => vi.fn());
const recordServerProbeResult = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getDb }));
vi.mock("./service", () => ({ recordServerProbeResult }));

import { registerExecutorGateway } from "./executorGateway";

describe("受控服务器探活回传网关", () => {
  it("要求共享密钥并校验节点与服务器资产关联", async () => {
    const secret = process.env.EXECUTOR_GATEWAY_SHARED_SECRET;
    expect(secret).toBeTruthy();
    const node = { id: 8, nodeKey: "probe-node-01", serverAssetId: 21 };
    getDb.mockResolvedValue({ select: () => ({ from: () => ({ where: () => ({ limit: async () => [node] }) }) }) });
    recordServerProbeResult.mockResolvedValue({ id: 21, status: "online", message: "heartbeat ok" });
    const app = express(); app.use(express.json()); registerExecutorGateway(app);
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const instance = app.listen(0, () => resolve(instance)); });
    const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}/api/executor/server-probe-result`;
    try {
      const denied = await fetch(base, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ nodeKey: node.nodeKey, serverAssetId: 21, status: "online" }) });
      expect(denied.status).toBe(401);
      const mismatch = await fetch(base, { method: "POST", headers: { "content-type": "application/json", "x-executor-secret": secret ?? "" }, body: JSON.stringify({ nodeKey: node.nodeKey, serverAssetId: 22, status: "online" }) });
      expect(mismatch.status).toBe(403);
      const accepted = await fetch(base, { method: "POST", headers: { "content-type": "application/json", "x-executor-secret": secret ?? "" }, body: JSON.stringify({ nodeKey: node.nodeKey, serverAssetId: 21, status: "online", message: "heartbeat ok" }) });
      expect(accepted.status).toBe(200);
      await expect(accepted.json()).resolves.toMatchObject({ ok: true, id: 21, status: "online", nodeKey: node.nodeKey });
      expect(recordServerProbeResult).toHaveBeenCalledWith(21, "online", "heartbeat ok");
    } finally { await new Promise<void>(resolve => server.close(() => resolve())); }
  });
});
