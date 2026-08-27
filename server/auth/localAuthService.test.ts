import { describe, expect, it } from "vitest";
import { validateLocalPassword } from "./localAuthService";
import { isCurrentLocalSession } from "./localAuthSecurity";

describe("本地管理员密码策略", () => {
  it("接受满足长度和字符类别的密码", () => {
    expect(() => validateLocalPassword("Strong-Password_2026!" )).not.toThrow();
  });

  it("拒绝过短或缺少必需字符类别的密码", () => {
    expect(() => validateLocalPassword("TooShort1!")).toThrow("至少需要");
    expect(() => validateLocalPassword("onlylowercasepassword!1")).toThrow("须包含");
    expect(() => validateLocalPassword("NOLOWERCASEPASSWORD!1")).toThrow("须包含");
    expect(() => validateLocalPassword("NoSpecialCharacter2026")).toThrow("须包含");
  });
});

describe("本地会话版本", () => {
  it("只接受与账户当前版本一致的会话，并拒绝改密前旧会话", () => {
    expect(isCurrentLocalSession(2, 2)).toBe(true);
    expect(isCurrentLocalSession(1, 2)).toBe(false);
    expect(isCurrentLocalSession(undefined, 2)).toBe(false);
  });
});
