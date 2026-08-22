import { MetricCard, PageHeader, StatusPill, TechCard } from "@/components/Blueprint";
import { Button } from "@/components/ui/button";
import { trpc } from "@/lib/trpc";
import { Activity, AlertTriangle, ArrowUpRight, Database, Gauge, ListChecks, Plus, ShieldCheck, Waves } from "lucide-react";
import { Link } from "wouter";

const categoryLabel: Record<string, string> = { deployment: "安装部署", backup_recovery: "备份恢复", inspection: "性能巡检", self_healing: "故障自愈" };

export default function Dashboard() {
  const overview = trpc.ops.overview.useQuery();
  const assets = trpc.ops.assets.list.useQuery();
  const alerts = trpc.ops.alerts.list.useQuery();
  const executions = trpc.ops.runbooks.executions.useQuery();
  const nodes = trpc.ops.executors.list.useQuery();
  const risks = trpc.ops.risks.useQuery();
  const activity = trpc.ops.activity.recent.useQuery();
  const data = overview.data;

  return (
    <div className="mx-auto max-w-[1600px] space-y-6">
      <PageHeader eyebrow="CONTROL ROOM · R02" title="数据库运维总览" description="统一观察实例健康、任务流转、监控事件和受控执行节点状态。所有高风险动作均经过人工确认与审计。" action={<Link href="/assets"><Button className="gap-2 bg-cyan-200 text-[#061b51] hover:bg-cyan-100"><Plus className="h-4 w-4" />登记数据库资产</Button></Link>} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="受管实例" value={data?.instances.total ?? "—"} detail={`${data?.instances.healthy ?? 0} 个健康 · ${data?.instances.warning ?? 0} 个预警`} icon={Database} />
        <MetricCard label="运行任务" value={data?.executions.active ?? "—"} detail={`${data?.executions.awaitingApproval ?? 0} 个等待人工确认`} icon={ListChecks} accent="blue" />
        <MetricCard label="待处置告警" value={data?.alerts.open ?? "—"} detail={`${data?.alerts.critical ?? 0} 个严重 · ${data?.alerts.high ?? 0} 个高优先级`} icon={AlertTriangle} accent={data?.alerts.critical ? "rose" : "amber"} />
        <MetricCard label="执行节点" value={nodes.data?.length ?? "—"} detail={`${nodes.data?.filter(item => item.status === "online").length ?? 0} 个已在线 · 仅允许受控派发`} icon={ShieldCheck} accent="cyan" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_.7fr]">
        <TechCard label="INSTANCE HEALTH">
          <div className="flex items-center justify-between gap-4">
            <div><h2 className="font-display text-lg font-semibold text-white">实例健康与容量</h2><p className="mt-1 text-xs text-blue-100/55">数据来自已登记资产；连接与容量由受控节点或已接入监控源回传。</p></div>
            <Link href="/assets" className="mono inline-flex items-center gap-1 text-xs text-cyan-200 hover:text-white">资产中心 <ArrowUpRight className="h-3.5 w-3.5" /></Link>
          </div>
          <div className="mt-5 space-y-3">
            {(assets.data ?? []).slice(0, 5).map(asset => {
              const used = asset.capacityGb && asset.usedCapacityGb ? Math.min(100, Math.round(asset.usedCapacityGb / asset.capacityGb * 100)) : 0;
              return <div key={asset.id} className="grid gap-3 border-b border-blue-300/12 pb-3 last:border-0 last:pb-0 sm:grid-cols-[1fr_150px_100px] sm:items-center">
                <div><p className="text-sm font-medium text-white">{asset.name}</p><p className="mono mt-1 text-[10px] uppercase tracking-wider text-blue-100/50">{asset.engine} · {asset.environment} · {asset.host}:{asset.port}</p></div>
                <div><div className="flex justify-between text-[10px] text-blue-100/55"><span>CAPACITY</span><span>{asset.capacityGb ? `${used}%` : "—"}</span></div><div className="mt-1.5 h-1 overflow-hidden bg-blue-100/10"><div className="h-full bg-cyan-200" style={{ width: `${used}%` }} /></div></div>
                <StatusPill status={asset.healthStatus} />
              </div>;
            })}
            {!assets.data?.length ? <EmptyLine icon={Database} text="暂无数据库资产。先登记实例，并由受控执行节点提交健康检查结果。" /> : null}
          </div>
        </TechCard>

        <TechCard label="CONTROL PLANE">
          <h2 className="font-display text-lg font-semibold text-white">闭环状态</h2>
          <div className="mt-5 space-y-4">
            <Signal label="监控集成" value={`${data?.integrations.connected ?? 0} / ${data?.integrations.configured ?? 0}`} hint="已连接 / 已登记" tone="cyan" />
            <Signal label="人工确认" value={String(data?.executions.awaitingApproval ?? 0)} hint="高风险执行单待处理" tone="amber" />
            <Signal label="关键事件" value={String((data?.alerts.critical ?? 0) + (data?.alerts.high ?? 0))} hint="严重与高优先级事件" tone={data?.alerts.critical ? "rose" : "cyan"} />
          </div>
          <div className="mt-6 border-t border-blue-300/12 pt-4"><p className="mono text-[10px] tracking-wider text-blue-100/45">CONTROL PRINCIPLE</p><p className="mt-2 text-xs leading-5 text-blue-100/65">控制面不保留数据库密码，不直接执行厂商命令；变更由部署在受控网络中的执行节点获取已审批任务后完成。</p></div>
        </TechCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <TechCard label="PERFORMANCE RISK">
          <div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold text-white">容量与性能风险</h2><p className="mono text-[10px] tracking-wider text-cyan-200">{risks.data?.length ?? 0} SIGNALS</p></div>
          <p className="mt-1 text-xs text-blue-100/55">聚合高容量利用率、健康异常和已接入监控源的高优先级事件。</p>
          <div className="mt-4 space-y-3">{(risks.data ?? []).map(item => <div key={item.key} className="flex items-center justify-between gap-3 border-b border-blue-300/12 pb-3 last:border-0 last:pb-0"><div><p className="text-sm text-white">{item.title}</p><p className="mono mt-1 text-[10px] text-blue-100/45">{item.source} · {item.detail}</p></div><StatusPill status={item.severity} /></div>)}{!risks.data?.length ? <EmptyLine icon={Gauge} text="暂无性能风险信号。容量、健康或高优先级告警出现异常后将在此集中显示。" /> : null}</div>
        </TechCard>
        <TechCard label="RECENT DISPOSITION">
          <div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold text-white">近期处置记录</h2><Link href="/runbooks" className="mono text-xs text-cyan-200 hover:text-white">审计与日志</Link></div>
          <p className="mt-1 text-xs text-blue-100/55">按最新状态变更显示 Runbook 的创建、审批与执行进度。</p>
          <div className="mt-4 space-y-3">{(activity.data ?? []).map(item => <div key={item.executionKey} className="grid grid-cols-[12px_1fr_auto] items-start gap-3"><span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-cyan-200 shadow-[0_0_12px_rgba(165,243,252,.7)]" /><div><p className="text-sm text-white">{item.runbookTitle}</p><p className="mono mt-1 text-[10px] text-blue-100/45">{new Date(item.updatedAt).toLocaleString()} · {item.executionKey}</p></div><StatusPill status={item.status} /></div>)}{!activity.data?.length ? <EmptyLine icon={Activity} text="尚无处置记录。创建执行单后，将在这里形成审批与执行时间线。" /> : null}</div>
        </TechCard>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <TechCard label="RECENT EXECUTIONS">
          <div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold text-white">最近执行记录</h2><Link href="/runbooks" className="mono text-xs text-cyan-200 hover:text-white">进入 Runbook 中心</Link></div>
          <div className="mt-4 space-y-3">
            {(executions.data ?? []).slice(0, 5).map(item => <div key={item.executionKey} className="flex items-center justify-between gap-3 border-b border-blue-300/12 pb-3 last:border-0 last:pb-0"><div><p className="text-sm text-white">{item.runbookTitle}</p><p className="mono mt-1 text-[10px] uppercase tracking-wider text-blue-100/45">{categoryLabel[item.category]} · {item.executionKey}</p></div><StatusPill status={item.status} /></div>)}
            {!executions.data?.length ? <EmptyLine icon={ListChecks} text="尚无执行单。可从标准 Runbook 模板创建任务。" /> : null}
          </div>
        </TechCard>
        <TechCard label="ALERT PRIORITY">
          <div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold text-white">告警优先级</h2><Link href="/intelligence" className="mono text-xs text-cyan-200 hover:text-white">智能处置分析</Link></div>
          <div className="mt-4 space-y-3">
            {(alerts.data ?? []).slice(0, 5).map(item => <div key={item.id} className="flex items-center justify-between gap-3 border-b border-blue-300/12 pb-3 last:border-0 last:pb-0"><div><p className="text-sm text-white">{item.title}</p><p className="mono mt-1 text-[10px] uppercase tracking-wider text-blue-100/45">{item.metric ?? "UNMAPPED METRIC"} · {item.currentValue ?? "—"}</p></div><StatusPill status={item.severity} /></div>)}
            {!alerts.data?.length ? <EmptyLine icon={Waves} text="暂无待处置告警。接入监控源或记录事件后将在此呈现。" /> : null}
          </div>
        </TechCard>
      </div>
    </div>
  );
}

function Signal({ label, value, hint, tone }: { label: string; value: string; hint: string; tone: "cyan" | "amber" | "rose" }) {
  const color = tone === "rose" ? "text-rose-100" : tone === "amber" ? "text-amber-100" : "text-cyan-200";
  return <div className="flex items-end justify-between border-l border-blue-300/20 pl-3"><div><p className="mono text-[10px] uppercase tracking-[.14em] text-blue-100/50">{label}</p><p className="mt-1 text-xs text-blue-100/60">{hint}</p></div><p className={`font-display text-2xl font-semibold ${color}`}>{value}</p></div>;
}

function EmptyLine({ icon: Icon, text }: { icon: typeof Gauge; text: string }) { return <div className="flex items-center gap-3 border border-dashed border-blue-300/20 px-4 py-5 text-xs leading-5 text-blue-100/55"><Icon className="h-4 w-4 shrink-0 text-cyan-200/60" />{text}</div>; }
