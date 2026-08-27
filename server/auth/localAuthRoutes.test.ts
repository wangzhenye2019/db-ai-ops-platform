import express from "express";
import type { AddressInfo } from "net";
import { describe, expect, it, vi } from "vitest";
import { registerLocalAuthRoutes } from "./localAuthRoutes";
import { appRouter } from "../routers";
import type { TrpcContext } from "../_core/context";

describe("本地初始化凭据", () => {
  it("拒绝错误密码并接受经安全配置的首次登录凭据", async () => {
    expect(process.env.LOCAL_BOOTSTRAP_USERNAME).toBeTruthy();
    expect(process.env.LOCAL_BOOTSTRAP_PASSWORD).toBeTruthy();
    const now = new Date();
    const app = express(); app.use(express.json()); registerLocalAuthRoutes(app, {
      authenticateLocalAccount: async (username, password) => {
        if (username !== process.env.LOCAL_BOOTSTRAP_USERNAME || password !== process.env.LOCAL_BOOTSTRAP_PASSWORD) throw new Error("invalid credentials");
        return { user: { id: 1, openId: "local:test-admin", name: "test-admin", email: null, loginMethod: "local", role: "admin", createdAt: now, updatedAt: now, lastSignedIn: now }, mustChangePassword: true, sessionVersion: 1 };
      },
      createSessionToken: async () => "local-test-session",
    });
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const listener = app.listen(0, () => resolve(listener)); });
    const { port } = server.address() as AddressInfo;
    try {
      const rejected = await fetch(`http://127.0.0.1:${port}/api/local-auth/login`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ username: process.env.LOCAL_BOOTSTRAP_USERNAME, password: "incorrect" }) });
      expect(rejected.status).toBe(401);
      const accepted = await fetch(`http://127.0.0.1:${port}/api/local-auth/login`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ username: process.env.LOCAL_BOOTSTRAP_USERNAME, password: process.env.LOCAL_BOOTSTRAP_PASSWORD }) });
      expect(accepted.status).toBe(200);
      await expect(accepted.json()).resolves.toEqual({ ok: true, mustChangePassword: true });
      expect(accepted.headers.get("set-cookie")).toContain("session");
      expect(accepted.headers.get("set-cookie")).toContain("HttpOnly");
    } finally { await new Promise<void>(resolve => server.close(() => resolve())); }
  });

  it("改密后签发新版本本地会话，并解除受保护运维接口的首次登录门禁", async () => {
    const issuedOptions: Array<Record<string, unknown>> = [];
    const now = new Date();
    const user = { id: 77, openId: "local:bootstrap-admin", name: "bootstrap-admin", email: null, loginMethod: "local", role: "admin" as const, createdAt: now, updatedAt: now, lastSignedIn: now, mustChangePassword: true };
    const app = express(); app.use(express.json());
    registerLocalAuthRoutes(app, {
      authenticateRequest: async () => user,
      changeLocalPassword: async () => ({ sessionVersion: 2 }),
      createSessionToken: async (_openId, options) => { issuedOptions.push(options); return "local-session-v2"; },
    });
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const listener = app.listen(0, () => resolve(listener)); });
    const { port } = server.address() as AddressInfo;
    try {
      const changed = await fetch(`http://127.0.0.1:${port}/api/local-auth/change-password`, { method: "POST", headers: { "content-type": "application/json", cookie: "session=local-session-v1" }, body: JSON.stringify({ currentPassword: "initial", nextPassword: "Strong-Password_2026!" }) });
      expect(changed.status).toBe(200);
      expect(changed.headers.get("set-cookie")).toContain("local-session-v2");
      expect(issuedOptions[0]).toMatchObject({ authType: "local", mustChangePassword: false, localSessionVersion: 2 });
      const context: TrpcContext = { user: { ...user, mustChangePassword: false }, req: { protocol: "https", headers: {} } as TrpcContext["req"], res: {} as TrpcContext["res"] };
      await expect(appRouter.createCaller(context).ops.catalog()).resolves.toMatchObject({ adapters: expect.any(Array), runbooks: expect.any(Array) });
    } finally { await new Promise<void>(resolve => server.close(() => resolve())); }
  });

  it("首次改密缺少当前临时密码时拒绝请求且不调用改密服务", async () => {
    const changeLocalPassword = vi.fn();
    const app = express(); app.use(express.json());
    registerLocalAuthRoutes(app, { authenticateRequest: async () => ({ id: 9, openId: "local:bootstrap", name: "bootstrap", email: null, loginMethod: "local", role: "admin", createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date(), mustChangePassword: true }), changeLocalPassword, createSessionToken: async () => "must-not-issue" });
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const listener = app.listen(0, () => resolve(listener)); });
    const { port } = server.address() as AddressInfo;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/local-auth/change-password`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ nextPassword: "Strong-Password_2026!" }) });
      expect(response.status).toBe(400);
      expect(changeLocalPassword).not.toHaveBeenCalled();
    } finally { await new Promise<void>(resolve => server.close(() => resolve())); }
  });
});
