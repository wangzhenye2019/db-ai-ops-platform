import { describe, expect, it } from "vitest";
import { adapterMatrix, builtInRunbooks, getCatalogRunbook } from "./catalog";

describe("运维能力矩阵", () => {
  it("覆盖用户要求的多类数据库引擎", () => {
    const engines = new Set(adapterMatrix.map(item => item.engine));
    ["mysql", "postgresql", "oracle", "sql_server", "dameng", "kingbase", "oceanbase", "polardb", "gaussdb", "tidb", "goldendb", "gbase", "tdsql", "opengauss"].forEach(engine => {
      expect(engines.has(engine)).toBe(true);
    });
  });

  it("为每种引擎声明巡检与备份恢复能力", () => {
    adapterMatrix.forEach(adapter => {
      expect(adapter.inspection).toBe(true);
      expect(adapter.backupRecovery).toBe(true);
    });
  });
});

describe("标准 Runbook 风险策略", () => {
  it("对高风险备份、自愈和部署动作强制人工确认", () => {
    const risky = builtInRunbooks.filter(item => ["backup_recovery", "self_healing", "deployment"].includes(item.category));
    expect(risky.length).toBeGreaterThan(0);
    risky.forEach(item => expect(item.approvalRequired).toBe(true));
  });

  it("可根据稳定标识检索标准 Runbook", () => {
    const runbook = getCatalogRunbook("baseline-inspection");
    expect(runbook?.title).toContain("巡检");
    expect(getCatalogRunbook("missing-template")).toBeUndefined();
  });
});
