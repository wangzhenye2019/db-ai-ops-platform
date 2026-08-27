import { describe, expect, it } from "vitest";
import { reviewSqlText } from "./service";

describe("SQL governance review", () => {
  it("blocks destructive DDL and DML without a predicate", () => {
    expect(reviewSqlText("DROP TABLE customer_data").passed).toBe(false);
    expect(reviewSqlText("UPDATE customer_data SET email = 'x'").findings.some(item => item.rule === "DML_NO_WHERE")).toBe(true);
  });

  it("warns on wildcard reads without blocking the change", () => {
    const result = reviewSqlText("SELECT * FROM orders WHERE id = 1");
    expect(result.passed).toBe(true);
    expect(result.findings.some(item => item.rule === "SELECT_STAR")).toBe(true);
  });

  it("passes a constrained change and returns an auditable finding", () => {
    const result = reviewSqlText("ALTER TABLE orders ADD COLUMN archived_at TIMESTAMP");
    expect(result.passed).toBe(true);
    expect(result.findings).toEqual([{ rule: "SQL_REVIEW_PASS", severity: "info", message: "未命中内置阻断规则，仍需按风险等级完成审批。" }]);
  });
});
