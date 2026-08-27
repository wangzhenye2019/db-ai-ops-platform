import { describe, expect, it, vi } from "vitest";
import { COOKIE_NAME } from "../../shared/const";

const getUserByOpenId = vi.hoisted(() => vi.fn());
const getLocalAccountByUserId = vi.hoisted(() => vi.fn());
const upsertUser = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getUserByOpenId, getLocalAccountByUserId, upsertUser }));

import { sdk } from "../_core/sdk";

describe("本地会话版本真实认证", () => {
  it("改密后的旧 local session 被拒绝，当前版本通过", async () => {
    const user = { id: 7, openId: "local:admin", name: "admin", email: null, loginMethod: "local", role: "admin" as const, createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() };
    getUserByOpenId.mockResolvedValue(user);
    getLocalAccountByUserId.mockResolvedValue({ id: 1, userId: 7, username: "admin", sessionVersion: 5, mustChangePassword: false });

    const oldToken = await sdk.createSessionToken(user.openId, { name: user.name, authType: "local", mustChangePassword: false, localSessionVersion: 4, expiresInMs: 60_000 });
    await expect(sdk.authenticateRequest({ headers: { cookie: `${COOKIE_NAME}=${oldToken}` } } as never)).rejects.toThrow("Local session expired");

    const currentToken = await sdk.createSessionToken(user.openId, { name: user.name, authType: "local", mustChangePassword: false, localSessionVersion: 5, expiresInMs: 60_000 });
    await expect(sdk.authenticateRequest({ headers: { cookie: `${COOKIE_NAME}=${currentToken}` } } as never)).resolves.toMatchObject({ openId: user.openId, mustChangePassword: false });
    expect(upsertUser).toHaveBeenCalled();
  });
});
