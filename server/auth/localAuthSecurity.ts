import { timingSafeEqual } from "crypto";

function secureEquals(received: string | undefined, expected: string | undefined) {
  if (!received || !expected) return false;
  const left = Buffer.from(received);
  const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

export function hasBootstrapCredentials() {
  return Boolean(process.env.LOCAL_BOOTSTRAP_USERNAME && process.env.LOCAL_BOOTSTRAP_PASSWORD);
}

export function verifyBootstrapCredentials(username: string | undefined, password: string | undefined) {
  return secureEquals(username, process.env.LOCAL_BOOTSTRAP_USERNAME) && secureEquals(password, process.env.LOCAL_BOOTSTRAP_PASSWORD);
}

export function isCurrentLocalSession(sessionVersion: number | undefined, accountSessionVersion: number) {
  return Number.isInteger(sessionVersion) && sessionVersion === accountSessionVersion;
}
