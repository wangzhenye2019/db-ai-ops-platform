import { describe, expect, it } from "vitest";
import { LEASE_WINDOW_MS, createLeaseToken, hasMatchingSecret, hasValidLease } from "./executorSecurity";

describe("受控执行节点安全策略", () => {
  it("使用恒定时间比较验证共享密钥，并拒绝缺失或不匹配的密钥", () => {
    expect(hasMatchingSecret("correct-secret", "correct-secret")).toBe(true);
    expect(hasMatchingSecret("incorrect-secret", "correct-secret")).toBe(false);
    expect(hasMatchingSecret(undefined, "correct-secret")).toBe(false);
    expect(hasMatchingSecret("correct-secret", undefined)).toBe(false);
  });

  it("只接受当前节点、执行单和有效期均匹配的未过期租约", () => {
    const now = 1_750_000_000_000;
    const expiresAt = now + 60_000;
    const token = createLeaseToken("node-prod-01", "exec_abc", expiresAt, "gateway-secret");
    expect(hasValidLease("node-prod-01", "exec_abc", expiresAt, token, "gateway-secret", now)).toBe(true);
    expect(hasValidLease("node-prod-02", "exec_abc", expiresAt, token, "gateway-secret", now)).toBe(false);
    expect(hasValidLease("node-prod-01", "exec_abc", now - 1, token, "gateway-secret", now)).toBe(false);
    const tooFar = now + LEASE_WINDOW_MS + 10_001;
    expect(hasValidLease("node-prod-01", "exec_abc", tooFar, createLeaseToken("node-prod-01", "exec_abc", tooFar, "gateway-secret"), "gateway-secret", now)).toBe(false);
  });
});
