import { createHmac, timingSafeEqual } from "crypto";

export const LEASE_WINDOW_MS = 10 * 60 * 1000;

export function hasMatchingSecret(candidate: string | undefined, secret: string | undefined) {
  if (!candidate || !secret) return false;
  const received = Buffer.from(candidate);
  const expected = Buffer.from(secret);
  return received.length === expected.length && timingSafeEqual(received, expected);
}

export function createLeaseToken(nodeKey: string, executionKey: string, expiresAt: number, secret: string) {
  return createHmac("sha256", secret).update(`${nodeKey}:${executionKey}:${expiresAt}`).digest("base64url");
}

export function hasValidLease(nodeKey: string, executionKey: string, expiresAt: number, token: string, secret: string, now = Date.now()) {
  if (!Number.isFinite(expiresAt) || expiresAt < now || expiresAt > now + LEASE_WINDOW_MS + 10_000) return false;
  return hasMatchingSecret(token, createLeaseToken(nodeKey, executionKey, expiresAt, secret));
}
