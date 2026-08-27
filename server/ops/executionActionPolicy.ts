const cancellable = new Set(["scheduled", "awaiting_approval", "queued", "dispatched", "running"]);
const retryable = new Set(["failed", "cancelled"]);

export function assertCancellableExecution(status: string) {
  if (!cancellable.has(status)) throw new Error("当前执行状态不允许撤销");
}

export function assertRetryableExecution(status: string) {
  if (!retryable.has(status)) throw new Error("仅失败或已撤销的执行单允许重试");
}
