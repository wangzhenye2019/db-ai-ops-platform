import { randomBytes, scrypt as scryptCallback, timingSafeEqual } from "crypto";
import { promisify } from "util";
import { and, eq } from "drizzle-orm";
import { localAccounts, users } from "../../drizzle/schema";
import { getDb } from "../db";
import { verifyBootstrapCredentials } from "./localAuthSecurity";

const scrypt = promisify(scryptCallback);
const PASSWORD_MIN_LENGTH = 16;

export function validateLocalPassword(password: string) {
  if (password.length < PASSWORD_MIN_LENGTH) throw new Error(`密码至少需要 ${PASSWORD_MIN_LENGTH} 个字符`);
  if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) throw new Error("密码须包含大写字母、小写字母、数字和特殊字符");
}

async function hashPassword(password: string) {
  const salt = randomBytes(16).toString("base64url");
  const derived = await scrypt(password, salt, 64) as Buffer;
  return `scrypt$${salt}$${derived.toString("base64url")}`;
}

async function matchesPassword(password: string, encoded: string) {
  const [algorithm, salt, expected] = encoded.split("$");
  if (algorithm !== "scrypt" || !salt || !expected) return false;
  const received = await scrypt(password, salt, 64) as Buffer;
  const expectedBytes = Buffer.from(expected, "base64url");
  return received.length === expectedBytes.length && timingSafeEqual(received, expectedBytes);
}

export async function authenticateLocalAccount(username: string, password: string) {
  const db = await getDb();
  if (!db) throw new Error("本地认证服务不可用");
  let account = (await db.select().from(localAccounts).where(eq(localAccounts.username, username)).limit(1))[0];
  if (!account) {
    if (!verifyBootstrapCredentials(username, password)) throw new Error("用户名或密码错误");
    const openId = `local:${username}`;
    await db.insert(users).values({ openId, name: username, loginMethod: "local", role: "admin", lastSignedIn: new Date() }).onDuplicateKeyUpdate({ set: { lastSignedIn: new Date() } });
    const user = (await db.select().from(users).where(eq(users.openId, openId)).limit(1))[0];
    if (!user) throw new Error("无法创建初始化管理员");
    await db.insert(localAccounts).values({ userId: user.id, username, passwordHash: await hashPassword(password), mustChangePassword: true, sessionVersion: 1 }).onDuplicateKeyUpdate({ set: { passwordHash: await hashPassword(password), mustChangePassword: true, sessionVersion: 1 } });
    account = (await db.select().from(localAccounts).where(eq(localAccounts.username, username)).limit(1))[0];
  }
  if (!account || !await matchesPassword(password, account.passwordHash)) throw new Error("用户名或密码错误");
  const user = (await db.select().from(users).where(eq(users.id, account.userId)).limit(1))[0];
  if (!user) throw new Error("本地账户关联用户不存在");
  await db.update(users).set({ lastSignedIn: new Date() }).where(eq(users.id, user.id));
  return { user, mustChangePassword: account.mustChangePassword, sessionVersion: account.sessionVersion };
}

export async function getLocalAccountForUser(userId: number) {
  const db = await getDb();
  return db ? (await db.select().from(localAccounts).where(eq(localAccounts.userId, userId)).limit(1))[0] : undefined;
}

export async function changeLocalPassword(userId: number, currentPassword: string | undefined, nextPassword: string) {
  const db = await getDb();
  if (!db) throw new Error("本地认证服务不可用");
  const account = (await db.select().from(localAccounts).where(eq(localAccounts.userId, userId)).limit(1))[0];
  if (!account) throw new Error("当前账户不是本地管理员账户");
  if (!account.mustChangePassword && (!currentPassword || !await matchesPassword(currentPassword, account.passwordHash))) throw new Error("当前密码错误");
  if (account.mustChangePassword && currentPassword && !await matchesPassword(currentPassword, account.passwordHash)) throw new Error("初始密码错误");
  validateLocalPassword(nextPassword);
  const sessionVersion = account.sessionVersion + 1;
  await db.update(localAccounts).set({ passwordHash: await hashPassword(nextPassword), mustChangePassword: false, sessionVersion, passwordChangedAt: new Date() }).where(and(eq(localAccounts.id, account.id), eq(localAccounts.sessionVersion, account.sessionVersion)));
  return { sessionVersion };
}
