import { describe, expect, it, vi } from "vitest";
import { COOKIE_NAME } from "../../shared/const";

const getUserByOpenId = vi.hoisted(() => vi.fn());
const getLocalAccountByUserId = vi.hoisted(() => vi.fn());
const upsertUser = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getUserByOpenId, getLocalAccountByUserId, upsertUser }));

import { appRouter } from "../routers";
import { createContext } from "../_core/context";
import { sdk } from "../_core/sdk";

describe("受保护运维接口的本地会话门禁", () => {
  it("旧 sessionVersion 的 local JWT 调用 ops 接口时被拒绝", async () => {
    getUserByOpenId.mockResolvedValue({ id: 7, openId: "local:admin", name: "admin", email: null, loginMethod: "local", role: "admin", createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() });
    getLocalAccountByUserId.mockResolvedValue({ id: 1, userId: 7, username: "admin", sessionVersion: 5, mustChangePassword: false });
    const oldToken = await sdk.createSessionToken("local:admin", { name: "admin", authType: "local", mustChangePassword: false, localSessionVersion: 4, expiresInMs: 60_000 });
    const context = await createContext({ req: { headers: { cookie: `${COOKIE_NAME}=${oldToken}` } } as never, res: {} as never });
    expect(context.user).toBeNull();
    await expect(appRouter.createCaller(context).ops.catalog()).rejects.toMatchObject({ code: "UNAUTHORIZED" });
  });
});
