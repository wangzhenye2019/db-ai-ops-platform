export type RunbookPolicyTarget = {
  title: string;
  compatibleEngines?: string[] | null;
  status?: "draft" | "active" | "archived";
};

export type InstancePolicyTarget = { id: number; engine: string };
export type ExecutorPolicyTarget = { id: number; status: "online" | "degraded" | "offline" | "unverified"; supportedEngines?: string[] | null };

export function validateExecutionPolicy(input: {
  runbook: RunbookPolicyTarget;
  requestedInstanceId?: number;
  instance?: InstancePolicyTarget;
  requestedExecutorNodeId?: number;
  executor?: ExecutorPolicyTarget;
}) {
  const errors: string[] = [];
  if (input.runbook.status && input.runbook.status !== "active") errors.push("该自定义 Runbook 尚未启用，不能创建执行单");
  if (input.requestedInstanceId && !input.instance) errors.push("目标数据库实例不存在");
  if (input.requestedExecutorNodeId && !input.executor) errors.push("受控执行节点不存在");
  if (input.executor && input.requestedExecutorNodeId && input.executor.status !== "online") errors.push("受控执行节点未在线，不能领取生产任务");
  if (input.instance && input.runbook.compatibleEngines?.length && !input.runbook.compatibleEngines.includes(input.instance.engine)) errors.push(`${input.runbook.title} 不支持 ${input.instance.engine} 实例`);
  if (input.instance && input.executor?.supportedEngines?.length && !input.executor.supportedEngines.includes(input.instance.engine)) errors.push(`执行节点不具备 ${input.instance.engine} 适配器能力`);
  return { allowed: errors.length === 0, errors };
}

export function assertExecutionPolicy(input: Parameters<typeof validateExecutionPolicy>[0]) {
  const policy = validateExecutionPolicy(input);
  if (!policy.allowed) throw new Error(policy.errors.join("；"));
}
