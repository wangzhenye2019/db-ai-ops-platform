import { describe, expect, it } from "vitest";
import { appRouter } from "../routers";
import type { TrpcContext } from "../_core/context";

function createFirstLoginContext(): TrpcContext {
  const now = new Date();
  return { user: { id: 99, openId: "local:bootstrap-admin", name: "bootstrap-admin", email: null, loginMethod: "local", role: "admin", createdAt: now, updatedAt: now, lastSignedIn: now, mustChangePassword: true }, req: { protocol: "https", headers: {} } as TrpcContext["req"], res: {} as TrpcContext["res"] };
}

describe("首次改密门禁", () => {
  it("允许改密状态查询，但在改密前拒绝任何受保护运维查询", async () => {
    const caller = appRouter.createCaller(createFirstLoginContext());
    await expect(caller.auth.localPasswordStatus()).resolves.toEqual({ mustChangePassword: true, isLocalAccount: true });
    await expect(caller.ops.catalog()).rejects.toMatchObject({ code: "FORBIDDEN", message: "首次登录后必须先修改初始密码" });
  });
});
