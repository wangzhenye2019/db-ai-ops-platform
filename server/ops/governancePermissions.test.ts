import { describe, expect, it, vi } from "vitest";

const getDb = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getDb }));

import { appRouter } from "../routers";
import type { TrpcContext } from "../_core/context";

function context(role: "user" | "admin"): TrpcContext {
  const now = new Date();
  return { user: { id: role === "admin" ? 1 : 2, openId: `local:${role}`, name: role, email: null, loginMethod: "local", role, createdAt: now, updatedAt: now, lastSignedIn: now, mustChangePassword: false }, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] };
}

describe("SQL 治理权限", () => {
  it("普通用户不能登记 SQL 审核策略", async () => {
    await expect(appRouter.createCaller(context("user")).ops.governance.createSqlReviewPolicy({ name: "restricted", enabled: true, rules: [] })).rejects.toMatchObject({ code: "FORBIDDEN" });
  });

  it("管理员可进入策略登记路由", async () => {
    getDb.mockResolvedValue({ insert: () => ({ values: async () => undefined }) });
    await expect(appRouter.createCaller(context("admin")).ops.governance.createSqlReviewPolicy({ name: "admin-policy", enabled: true, rules: [] })).resolves.toBeUndefined();
  });
});
