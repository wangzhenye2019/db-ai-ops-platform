import express from "express";
import type { AddressInfo } from "net";
import { describe, expect, it } from "vitest";
import { registerIntegrationGateway } from "./integrationGateway";
import { normalizeIntegrationPayload } from "./integrationNormalizer";

describe("外部集成回调认证", () => {
  it("拒绝无回调密钥的请求并接受独立共享密钥", async () => {
    const secret = process.env.INTEGRATION_INGEST_SHARED_SECRET;
    expect(secret).toBeTruthy();
    const app = express();
    registerIntegrationGateway(app);
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const listener = app.listen(0, () => resolve(listener)); });
    const { port } = server.address() as AddressInfo;
    try {
      expect((await fetch(`http://127.0.0.1:${port}/api/integrations/ingest/health`)).status).toBe(401);
      const accepted = await fetch(`http://127.0.0.1:${port}/api/integrations/ingest/health`, { headers: { "x-integration-secret": secret ?? "" } });
      expect(accepted.status).toBe(200);
      await expect(accepted.json()).resolves.toMatchObject({ ok: true, service: "db-control-integration-ingest" });
    } finally {
      await new Promise<void>(resolve => server.close(() => resolve()));
    }
  });

  it("将已授权 Prometheus 回调按配置映射后分发给告警和指标服务", async () => {
    const secret = process.env.INTEGRATION_INGEST_SHARED_SECRET;
    const received: { alerts: unknown[]; metrics: unknown[] } = { alerts: [], metrics: [] };
    const app = express(); app.use(express.json());
    registerIntegrationGateway(app, {
      getIntegrationMapping: async () => ({ alerts: { title: "annotations.headline", severity: "labels.priority", instanceId: "labels.assetKey" }, metrics: { metric: "payload.name", value: "payload.reading", instanceId: "payload.asset" } }),
      ingestExternalAlert: async alert => { received.alerts.push(alert); return { action: "created" as const }; },
      ingestExternalMetric: async metric => { received.metrics.push(metric); return { action: "recorded" as const, metric: metric.metric }; },
    });
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const listener = app.listen(0, () => resolve(listener)); });
    const { port } = server.address() as AddressInfo;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/integrations/ingest/prometheus`, { method: "POST", headers: { "content-type": "application/json", "x-integration-secret": secret ?? "" }, body: JSON.stringify({ alerts: [{ status: "firing", labels: { priority: "critical", assetKey: "7" }, annotations: { headline: "自定义告警" } }], metrics: [{ payload: { name: "custom_qps", reading: 58, asset: "7" } }] }) });
      expect(response.status).toBe(200);
      await expect(response.json()).resolves.toMatchObject({ ok: true, provider: "prometheus", alerts: [{ action: "created" }], metrics: [{ action: "recorded", metric: "custom_qps" }] });
      expect(received.alerts[0]).toMatchObject({ provider: "prometheus", title: "自定义告警", severity: "critical", instanceId: 7 });
      expect(received.metrics[0]).toMatchObject({ provider: "prometheus", metric: "custom_qps", value: "58", instanceId: 7 });
    } finally { await new Promise<void>(resolve => server.close(() => resolve())); }
  });

  it("将已授权 XXL-Job 回调按配置映射后分发给任务状态服务", async () => {
    const secret = process.env.INTEGRATION_INGEST_SHARED_SECRET;
    const received: unknown[] = [];
    const app = express(); app.use(express.json());
    registerIntegrationGateway(app, {
      getIntegrationMapping: async () => ({ tasks: { executionKey: "context.runKey", status: "context.state", message: "context.note", result: "context.result" } }),
      ingestExternalTaskStatus: async task => { received.push(task); return { executionKey: task.executionKey, status: task.status }; },
    });
    const server = await new Promise<ReturnType<typeof app.listen>>(resolve => { const listener = app.listen(0, () => resolve(listener)); });
    const { port } = server.address() as AddressInfo;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/integrations/ingest/xxl_job`, { method: "POST", headers: { "content-type": "application/json", "x-integration-secret": secret ?? "" }, body: JSON.stringify({ context: { runKey: "exec_abc123", state: "succeeded", note: "任务完成", result: { durationMs: 420 } } }) });
      expect(response.status).toBe(200);
      await expect(response.json()).resolves.toMatchObject({ ok: true, provider: "xxl_job", tasks: [{ executionKey: "exec_abc123", status: "succeeded" }] });
      expect(received[0]).toMatchObject({ provider: "xxl_job", executionKey: "exec_abc123", status: "succeeded", message: "任务完成", result: { durationMs: 420 } });
    } finally { await new Promise<void>(resolve => server.close(() => resolve())); }
  });
});

describe("外部负载标准化", () => {
  it("映射 Prometheus 告警与指标，并映射 XXL-Job 执行状态", () => {
    const prometheus = normalizeIntegrationPayload("prometheus", { alerts: [{ status: "firing", labels: { alertname: "MysqlConnectionsHigh", severity: "critical", instanceId: 8 }, annotations: { summary: "连接数过高" } }], metrics: [{ metric: "mysql_connections", value: 980, unit: "sessions", instanceId: 8 }] });
    expect(prometheus.alerts[0]).toMatchObject({ title: "连接数过高", severity: "critical", status: "open", instanceId: 8 });
    expect(prometheus.metrics[0]).toMatchObject({ metric: "mysql_connections", value: "980", unit: "sessions", instanceId: 8 });
    const xxl = normalizeIntegrationPayload("xxl_job", { executionKey: "exec_demo_123", status: "succeeded", result: { durationMs: 1200 } });
    expect(xxl.tasks[0]).toMatchObject({ executionKey: "exec_demo_123", status: "succeeded" });
  });

  it("拒绝不支持的提供方和不完整的 XXL-Job 负载", () => {
    expect(() => normalizeIntegrationPayload("unknown", { event: "x" })).toThrow("unsupported integration provider");
    expect(() => normalizeIntegrationPayload("xxl_job", { status: "running" })).toThrow("requires executionKey");
  });

  it("使用配置字段路径覆盖默认解析，并在路径缺失时安全回退", () => {
    const mapped = normalizeIntegrationPayload("prometheus", { alerts: [{ status: "firing", labels: { assetKey: "9", priority: "high" }, annotations: { headline: "自定义连接告警" } }], metrics: [{ payload: { name: "custom_qps", reading: 52, asset: "9" } }] }, { alerts: { title: "annotations.headline", severity: "labels.priority", instanceId: "labels.assetKey" }, metrics: { metric: "payload.name", value: "payload.reading", instanceId: "payload.asset" } });
    expect(mapped.alerts[0]).toMatchObject({ title: "自定义连接告警", severity: "high", instanceId: 9 });
    expect(mapped.metrics[0]).toMatchObject({ metric: "custom_qps", value: "52", instanceId: 9 });
    const fallback = normalizeIntegrationPayload("zabbix", { title: "保留默认标题", severity: "high" }, { alerts: { title: "missing.title" } });
    expect(fallback.alerts[0]?.title).toBe("保留默认标题");
  });
});
