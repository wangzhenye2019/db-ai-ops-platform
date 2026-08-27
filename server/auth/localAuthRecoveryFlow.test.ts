import { promisify } from "node:util";
import { randomBytes, scrypt as scryptCallback } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { localAccounts, users } from "../../drizzle/schema";

const getDb = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getDb }));

import { authenticateLocalAccount, changeLocalPassword } from "./localAuthService";

const scrypt = promisify(scryptCallback);
async function encodePassword(password: string) {
  const salt = randomBytes(16).toString("base64url");
  const derived = await scrypt(password, salt, 64) as Buffer;
  return `scrypt$${salt}$${derived.toString("base64url")}`;
}

describe("本地管理员恢复完整领域流程", () => {
  beforeEach(() => {
    vi.stubEnv("LOCAL_BOOTSTRAP_USERNAME", "admin");
    vi.stubEnv("LOCAL_BOOTSTRAP_PASSWORD", "Recovery-Temp-2026!");
  });

  it("已有账户使用恢复凭据后强制改密并轮换会话版本", async () => {
    const account = { id: 1, userId: 7, username: "admin", passwordHash: await encodePassword("Old-Password_2026!"), mustChangePassword: false, sessionVersion: 10, passwordChangedAt: new Date() };
    const user = { id: 7, openId: "local:admin", name: "admin", email: null, loginMethod: "local", role: "admin" as const, createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() };
    const db = {
      select: () => ({ from: (table: unknown) => ({ where: () => ({ limit: async () => table === localAccounts ? [account] : [user] }) }) }),
      update: (table: unknown) => ({ set: (values: Record<string, unknown>) => ({ where: async () => { if (table === localAccounts) Object.assign(account, values); } }) }),
    };
    getDb.mockResolvedValue(db);

    const recovered = await authenticateLocalAccount("admin", "Recovery-Temp-2026!");
    expect(recovered.mustChangePassword).toBe(true);
    expect(recovered.sessionVersion).toBe(11);
    expect(account.mustChangePassword).toBe(true);

    const changed = await changeLocalPassword(7, "Recovery-Temp-2026!", "New-Strong-Password_2026!");
    expect(changed.sessionVersion).toBe(12);
    expect(account.mustChangePassword).toBe(false);
    expect(account.sessionVersion).toBe(12);
    await expect(changeLocalPassword(7, "Old-Password_2026!", "Another-Strong-Password_2026!")).rejects.toThrow("当前密码错误");
    vi.unstubAllEnvs();
  });
});
