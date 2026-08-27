import { describe, expect, it } from "vitest";
import { validateExecutionPolicy } from "./executionPolicy";

const activeMysqlRunbook = { title: "MySQL 备份校验", status: "active" as const, compatibleEngines: ["mysql"] };
const mysqlInstance = { id: 1, engine: "mysql" };
const onlineMysqlNode = { id: 11, status: "online" as const, supportedEngines: ["mysql", "postgresql"] };

describe("Runbook 执行策略", () => {
  it("允许已启用且实例、节点、引擎均兼容的生产执行单", () => {
    const result = validateExecutionPolicy({ runbook: activeMysqlRunbook, requestedInstanceId: 1, instance: mysqlInstance, requestedExecutorNodeId: 11, executor: onlineMysqlNode });
    expect(result).toEqual({ allowed: true, errors: [] });
  });

  it("拒绝未启用的自定义 Runbook 与不存在的目标资源", () => {
    const result = validateExecutionPolicy({ runbook: { ...activeMysqlRunbook, status: "draft" }, requestedInstanceId: 9, requestedExecutorNodeId: 99 });
    expect(result.allowed).toBe(false);
    expect(result.errors).toEqual(expect.arrayContaining(["该自定义 Runbook 尚未启用，不能创建执行单", "目标数据库实例不存在", "受控执行节点不存在"]));
  });

  it("拒绝数据库引擎或节点适配器不兼容的执行请求", () => {
    const result = validateExecutionPolicy({ runbook: activeMysqlRunbook, requestedInstanceId: 2, instance: { id: 2, engine: "oracle" }, requestedExecutorNodeId: 11, executor: onlineMysqlNode });
    expect(result.allowed).toBe(false);
    expect(result.errors).toEqual(expect.arrayContaining(["MySQL 备份校验 不支持 oracle 实例", "执行节点不具备 oracle 适配器能力"]));
  });

  it("拒绝已选定但未在线的受控执行节点", () => {
    const result = validateExecutionPolicy({ runbook: activeMysqlRunbook, requestedInstanceId: 1, instance: mysqlInstance, requestedExecutorNodeId: 12, executor: { ...onlineMysqlNode, id: 12, status: "offline" } });
    expect(result.allowed).toBe(false);
    expect(result.errors).toContain("受控执行节点未在线，不能领取生产任务");
  });
});
