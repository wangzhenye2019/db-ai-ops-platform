import { describe, expect, it } from "vitest";
import { assertCancellableExecution, assertRetryableExecution } from "./executionActionPolicy";

describe("执行单操作策略", () => {
  it("允许撤销尚未完成的执行单，拒绝撤销已完成执行单", () => {
    expect(() => assertCancellableExecution("scheduled")).not.toThrow();
    expect(() => assertCancellableExecution("running")).not.toThrow();
    expect(() => assertCancellableExecution("succeeded")).toThrow("不允许撤销");
  });
  it("仅允许失败或已撤销的执行单创建重试", () => {
    expect(() => assertRetryableExecution("failed")).not.toThrow();
    expect(() => assertRetryableExecution("cancelled")).not.toThrow();
    expect(() => assertRetryableExecution("running")).toThrow("允许重试");
  });
});
