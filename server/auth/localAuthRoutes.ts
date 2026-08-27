import type { Express } from "express";
import { getSessionCookieOptions } from "../_core/cookies";
import { sdk } from "../_core/sdk";
import { COOKIE_NAME } from "../../shared/const";
import { authenticateLocalAccount, changeLocalPassword } from "./localAuthService";

type LocalAuthDependencies = {
  authenticateLocalAccount: typeof authenticateLocalAccount;
  changeLocalPassword: typeof changeLocalPassword;
  authenticateRequest: typeof sdk.authenticateRequest;
  createSessionToken: typeof sdk.createSessionToken;
};

export function registerLocalAuthRoutes(app: Express, overrides: Partial<LocalAuthDependencies> = {}) {
  const dependencies: LocalAuthDependencies = { authenticateLocalAccount, changeLocalPassword, authenticateRequest: sdk.authenticateRequest.bind(sdk), createSessionToken: sdk.createSessionToken.bind(sdk), ...overrides };
  app.post("/api/local-auth/login", (req, res) => {
    const { username, password } = req.body ?? {};
    if (typeof username !== "string" || typeof password !== "string") return res.status(400).json({ ok: false, error: "username and password are required" });
    void dependencies.authenticateLocalAccount(username, password).then(async result => {
      const token = await dependencies.createSessionToken(result.user.openId, { name: result.user.name ?? username, authType: "local", mustChangePassword: result.mustChangePassword, localSessionVersion: result.sessionVersion, expiresInMs: 60 * 60 * 1000 });
      res.cookie(COOKIE_NAME, token, getSessionCookieOptions(req));
      return res.json({ ok: true, mustChangePassword: result.mustChangePassword });
    }).catch(() => res.status(401).json({ ok: false, error: "invalid username or password" }));
  });

  app.post("/api/local-auth/change-password", async (req, res) => {
    try {
      const user = await dependencies.authenticateRequest(req);
      const { currentPassword, nextPassword } = req.body ?? {};
      if (typeof currentPassword !== "string" || typeof nextPassword !== "string") return res.status(400).json({ ok: false, error: "current and next passwords are required" });
      const result = await dependencies.changeLocalPassword(user.id, currentPassword, nextPassword);
      const token = await dependencies.createSessionToken(user.openId, { name: user.name ?? user.openId, authType: "local", mustChangePassword: false, localSessionVersion: result.sessionVersion, expiresInMs: 60 * 60 * 1000 });
      res.cookie(COOKIE_NAME, token, getSessionCookieOptions(req));
      return res.json({ ok: true, mustChangePassword: false });
    } catch (error) { return res.status(400).json({ ok: false, error: error instanceof Error ? error.message : "password change failed" }); }
  });
}
