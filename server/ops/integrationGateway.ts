import { timingSafeEqual } from "crypto";
import type { Express, Request, Response } from "express";
import { normalizeIntegrationPayload } from "./integrationNormalizer";
import { getIntegrationMapping, ingestExternalAlert, ingestExternalMetric, ingestExternalTaskStatus } from "./service";

type GatewayDependencies = {
  getIntegrationMapping: typeof getIntegrationMapping;
  ingestExternalAlert: typeof ingestExternalAlert;
  ingestExternalMetric: typeof ingestExternalMetric;
  ingestExternalTaskStatus: typeof ingestExternalTaskStatus;
};

function hasMatchingSecret(candidate: string | undefined, secret: string | undefined) {
  if (!candidate || !secret) return false;
  const received = Buffer.from(candidate);
  const expected = Buffer.from(secret);
  return received.length === expected.length && timingSafeEqual(received, expected);
}

export function isAuthorizedIntegrationRequest(req: Request) {
  return hasMatchingSecret(req.header("x-integration-secret") ?? undefined, process.env.INTEGRATION_INGEST_SHARED_SECRET);
}

function rejectUnauthorized(req: Request, res: Response) {
  if (isAuthorizedIntegrationRequest(req)) return false;
  res.status(401).json({ ok: false, error: "integration authentication required" });
  return true;
}

export function registerIntegrationGateway(app: Express, overrides: Partial<GatewayDependencies> = {}) {
  const dependencies: GatewayDependencies = { getIntegrationMapping, ingestExternalAlert, ingestExternalMetric, ingestExternalTaskStatus, ...overrides };
  app.get("/api/integrations/ingest/health", (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    return res.json({ ok: true, service: "db-control-integration-ingest", timestamp: new Date().toISOString() });
  });

  app.post("/api/integrations/ingest/:provider", async (req, res) => {
    if (rejectUnauthorized(req, res)) return;
    const provider = req.params.provider;
    try {
      if (provider !== "zabbix" && provider !== "prometheus" && provider !== "xxl_job") return res.status(400).json({ ok: false, error: "unsupported integration provider" });
      const mapping = await dependencies.getIntegrationMapping(provider);
      const payload = normalizeIntegrationPayload(provider, req.body, mapping);
      const [alerts, metrics, tasks] = await Promise.all([
        Promise.all(payload.alerts.map(alert => dependencies.ingestExternalAlert({ provider, ...alert }))),
        Promise.all(payload.metrics.map(metric => dependencies.ingestExternalMetric({ provider, ...metric }))),
        Promise.all(payload.tasks.map(task => dependencies.ingestExternalTaskStatus({ provider, ...task }))),
      ]);
      return res.json({ ok: true, provider, alerts, metrics, tasks });
    } catch (error) {
      return res.status(400).json({ ok: false, error: error instanceof Error ? error.message : "integration payload rejected" });
    }
  });
}
