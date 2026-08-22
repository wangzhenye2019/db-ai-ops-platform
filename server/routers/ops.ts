import { z } from "zod";
import { databaseEngineValues, environmentValues, healthStatusValues, integrationProviderValues, riskLevelValues, runbookCategoryValues } from "../../drizzle/schema";
import { protectedProcedure, router } from "../_core/trpc";
import { adapterMatrix, builtInRunbooks } from "../ops/catalog";
import * as ops from "../ops/service";

const jsonRecord = z.record(z.string(), z.unknown());
export const assetInputSchema = z.object({
  name: z.string().min(2).max(128), engine: z.enum(databaseEngineValues), host: z.string().min(1).max(255), port: z.number().int().min(1).max(65535),
  databaseName: z.string().max(128).optional(), version: z.string().max(80).optional(), environment: z.enum(environmentValues).default("production"),
  healthStatus: z.enum(healthStatusValues).default("unknown"), healthScore: z.number().int().min(0).max(100).default(0),
  owner: z.string().max(128).optional(), credentialRef: z.string().max(160).optional(), capacityGb: z.number().int().positive().optional(), usedCapacityGb: z.number().int().nonnegative().optional(),
  capabilities: z.array(z.string().max(48)).max(20).default([]), tags: z.array(z.string().max(48)).max(20).default([]),
});
export const executionInputSchema = z.object({ templateKey: z.string().max(64).optional(), runbookId: z.number().int().positive().optional(), instanceId: z.number().int().positive().optional(), executorNodeId: z.number().int().positive().optional(), parameters: jsonRecord.optional() }).refine(value => Boolean(value.templateKey || value.runbookId), "请选择一个 Runbook");
export const approvalInputSchema = z.object({ executionKey: z.string().min(8).max(64), confirmed: z.literal(true), note: z.string().max(1000).optional() });
export const incidentOutputSchema = z.object({ rootCause: z.string(), confidence: z.number(), impact: z.string(), risk: z.string(), evidence: z.array(z.string()), recommendations: z.array(z.string()), runbookDraft: z.object({ title: z.string(), category: z.enum(runbookCategoryValues), riskLevel: z.enum(riskLevelValues), approvalRequired: z.boolean(), compatibleEngines: z.array(z.enum(databaseEngineValues)), parameters: jsonRecord, steps: z.array(z.object({ name: z.string(), action: z.string(), requiresConfirmation: z.boolean() })).min(1) }), requiresHumanConfirmation: z.boolean() });

export const opsRouter = router({
  overview: protectedProcedure.query(() => ops.getOverview()),
  activity: router({ recent: protectedProcedure.query(() => ops.listRecentDispositionRecords()) }),
  risks: protectedProcedure.query(() => ops.listPerformanceRisks()),
  catalog: protectedProcedure.query(() => ({ adapters: adapterMatrix, runbooks: builtInRunbooks })),
  assets: router({
    list: protectedProcedure.query(() => ops.listInstances()),
    create: protectedProcedure.input(assetInputSchema).mutation(({ input, ctx }) => ops.createInstance({ ...input, createdBy: ctx.user.openId })),
  }),
  runbooks: router({
    list: protectedProcedure.query(() => ops.listRunbooks()),
    create: protectedProcedure.input(z.object({
      title: z.string().min(2).max(160), category: z.enum(runbookCategoryValues), description: z.string().max(4000).optional(), compatibleEngines: z.array(z.enum(databaseEngineValues)).min(1),
      riskLevel: z.enum(riskLevelValues).default("medium"), approvalRequired: z.boolean().default(true), status: z.enum(["draft", "active"]).default("draft"),
      steps: z.array(z.object({ name: z.string().min(1).max(120), action: z.string().min(1).max(120), requiresConfirmation: z.boolean().optional() })).min(1).max(20),
    })).mutation(({ input, ctx }) => ops.createRunbook({ ...input, createdBy: ctx.user.openId })),
    executions: protectedProcedure.query(() => ops.listExecutions()),
    executionLogs: protectedProcedure.input(z.object({ executionKey: z.string().min(8).max(64) })).query(({ input }) => ops.listExecutionLogs(input.executionKey)),
    createExecution: protectedProcedure.input(executionInputSchema).mutation(({ input, ctx }) => ops.createExecution({ ...input, createdBy: ctx.user.openId })),
    approveExecution: protectedProcedure.input(approvalInputSchema).mutation(({ input, ctx }) => ops.approveExecution(input.executionKey, ctx.user.openId, input.note)),
  }),
  integrations: router({
    list: protectedProcedure.query(() => ops.listIntegrations()),
    create: protectedProcedure.input(z.object({ name: z.string().min(2).max(128), provider: z.enum(integrationProviderValues), endpoint: z.string().url().max(512), secretRef: z.string().max(160).optional(), mapping: jsonRecord.optional() })).mutation(({ input }) => ops.createIntegration({ ...input, status: "unconfigured" })),
  }),
  executors: router({
    list: protectedProcedure.query(() => ops.listNodes()),
    register: protectedProcedure.input(z.object({ name: z.string().min(2).max(128), nodeKey: z.string().min(8).max(64), environment: z.enum(environmentValues).default("production"), endpoint: z.string().url().max(512).optional(), zone: z.string().max(128).optional(), capabilities: z.array(z.string().max(64)).max(30).default([]), supportedEngines: z.array(z.enum(databaseEngineValues)).min(1) })).mutation(({ input }) => ops.registerNode({ ...input, status: "unverified" })),
  }),
  alerts: router({
    list: protectedProcedure.query(() => ops.listAlerts()),
    record: protectedProcedure.input(z.object({ title: z.string().min(2).max(255), severity: z.enum(["critical", "high", "medium", "low", "info"]), instanceId: z.number().int().positive().optional(), integrationId: z.number().int().positive().optional(), externalId: z.string().max(128).optional(), metric: z.string().max(128).optional(), currentValue: z.string().max(128).optional(), threshold: z.string().max(128).optional(), context: jsonRecord.optional() })).mutation(({ input }) => ops.recordAlert({ ...input, status: "open" })),
  }),
  intelligence: router({
    analyze: protectedProcedure.input(z.object({ context: z.string().max(12000).optional(), instanceId: z.number().int().positive().optional(), alertId: z.number().int().positive().optional() }).refine(value => Boolean(value.context?.trim() || value.instanceId || value.alertId), "请提供诊断上下文，或选择实例 / 告警")).mutation(({ input, ctx }) => ops.generateIncidentAnalysis({ ...input, createdBy: ctx.user.openId })),
  }),
});
