import express from "express";
import type { AddressInfo } from "net";
import { describe, expect, it } from "vitest";
import { registerExecutorGateway } from "./executorGateway";

describe("受控执行节点认证端点", () => {
  it("接受配置的共享密钥并拒绝无密钥请求", async () => {
    const secret = process.env.EXECUTOR_GATEWAY_SHARED_SECRET;
    expect(secret).toBeTruthy();
    const app = express();
    registerExecutorGateway(app);
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => {
      const instance = app.listen(0, () => resolve(instance));
    });
    const address = server.address() as AddressInfo;
    const base = `http://127.0.0.1:${address.port}/api/executor/health`;
    try {
      const denied = await fetch(base);
      expect(denied.status).toBe(401);
      const accepted = await fetch(base, { headers: { "x-executor-secret": secret ?? "" } });
      expect(accepted.status).toBe(200);
      await expect(accepted.json()).resolves.toMatchObject({ ok: true, service: "db-control-executor-gateway" });
    } finally {
      await new Promise<void>(resolve => server.close(() => resolve()));
    }
  });
});
