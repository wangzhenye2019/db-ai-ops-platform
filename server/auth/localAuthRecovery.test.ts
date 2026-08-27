import { describe, expect, it, vi } from "vitest";
import { isBootstrapRecoveryAttempt } from "./localAuthService";

describe("本地管理员受控密码恢复", () => {
  it("只允许已存在账户匹配初始化凭据时进入恢复分支", () => {
    vi.stubEnv("LOCAL_BOOTSTRAP_USERNAME", "recovery-admin");
    vi.stubEnv("LOCAL_BOOTSTRAP_PASSWORD", "Recovery-Temp-2026!");
    expect(isBootstrapRecoveryAttempt(true, "recovery-admin", "Recovery-Temp-2026!")).toBe(true);
    expect(isBootstrapRecoveryAttempt(true, "recovery-admin", "wrong-password")).toBe(false);
    expect(isBootstrapRecoveryAttempt(true, "another-admin", "Recovery-Temp-2026!")).toBe(false);
    expect(isBootstrapRecoveryAttempt(false, "recovery-admin", "Recovery-Temp-2026!")).toBe(false);
    vi.unstubAllEnvs();
  });
});
