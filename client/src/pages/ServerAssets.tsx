import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Activity, CheckCircle2, Database, FileCode2, Globe2, Plus, Server, ShieldCheck, TerminalSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader, TechCard, MetricCard, StatusPill } from "@/components/Blueprint";
import { trpc } from "@/lib/trpc";

const emptyReview = { passed: false, findings: [] as Array<{ rule: string; severity: string; message: string }> };

export default function ServerAssets() {
  const [showAssetForm, setShowAssetForm] = useState(false);
  const [selectedServerId, setSelectedServerId] = useState<number | null>(null);
  const [asset, setAsset] = useState({ name: "", hostname: "", ipAddress: "", operatingSystem: "Linux", zone: "", owner: "", credentialRef: "", capabilities: "ssh,agent" });
  const [change, setChange] = useState({ title: "", engine: "mysql", sqlText: "", rollbackSql: "" });
  const utils = trpc.useUtils();
  const servers = trpc.ops.serverAssets.list.useQuery();
  const serverDetail = trpc.ops.serverAssets.get.useQuery({ id: selectedServerId! }, { enabled: selectedServerId !== null });
  const changes = trpc.ops.governance.changeRequests.useQuery();
  const queryAudits = trpc.ops.governance.queryAuditRecords.useQuery();
  const reviewInput = useMemo(() => ({ sqlText: change.sqlText }), [change.sqlText]);
  const review = trpc.ops.governance.reviewSql.useQuery(reviewInput, { enabled: change.sqlText.trim().length > 0 });
  const createServer = trpc.ops.serverAssets.create.useMutation({ onSuccess: async () => { toast.success("服务器资产已登记"); setShowAssetForm(false); setAsset({ name: "", hostname: "", ipAddress: "", operatingSystem: "Linux", zone: "", owner: "", credentialRef: "", capabilities: "ssh,agent" }); await utils.ops.serverAssets.list.invalidate(); }, onError: error => toast.error(error.message) });
  const probeServer = trpc.ops.serverAssets.requestProbe.useMutation({ onSuccess: async () => { toast.success("探活请求已排队，等待受控节点回报"); await utils.ops.serverAssets.list.invalidate(); await utils.ops.serverAssets.get.invalidate(); }, onError: error => toast.error(error.message) });
  const createChange = trpc.ops.governance.createChangeRequest.useMutation({ onSuccess: async data => { toast.success(data.status === "pending_review" ? "SQL 已通过初检并进入审核工单" : "SQL 被规则阻断，请修正后重试"); setChange({ title: "", engine: "mysql", sqlText: "", rollbackSql: "" }); await utils.ops.governance.changeRequests.invalidate(); }, onError: error => toast.error(error.message) });
  const serverList = servers.data ?? [];
  const changeList = changes.data ?? [];
  const queryAuditList = queryAudits.data ?? [];
  const reviewData = review.data ?? emptyReview;
  const onlineCount = serverList.filter(item => item.status === "online").length;
  const unknownCount = serverList.filter(item => item.status === "unknown").length;

  const submitServer = () => {
    if (!asset.name.trim() || !asset.hostname.trim()) return toast.error("请填写服务器名称和主机名");
    createServer.mutate({ ...asset, ipAddress: asset.ipAddress || undefined, operatingSystem: asset.operatingSystem || undefined, zone: asset.zone || undefined, owner: asset.owner || undefined, credentialRef: asset.credentialRef || undefined, capabilities: asset.capabilities.split(",").map(value => value.trim()).filter(Boolean), metadata: { source: "manual_registry" } });
  };

  const requestProbe = (id: number) => probeServer.mutate({ id });

  const submitChange = () => {
    if (!change.title.trim() || !change.sqlText.trim()) return toast.error("请填写工单标题和 SQL");
    createChange.mutate({ ...change, rollbackSql: change.rollbackSql || undefined, riskLevel: reviewData.passed ? "medium" : "high" });
  };

  return <main className="space-y-6">
    <PageHeader eyebrow="SERVER FABRIC · S02" title="服务器资产与数据库治理" description="统一登记受控服务器、审阅 SQL 变更并关联数据库资产。控制面仅保存密钥引用，探活与生产执行由受控节点完成。" action={<Button className="bg-cyan-200 text-slate-950 hover:bg-cyan-100" onClick={() => setShowAssetForm(value => !value)}><Plus className="mr-2 h-4 w-4" />登记服务器</Button>} />

    <div className="grid gap-4 md:grid-cols-4">
      <MetricCard label="服务器资产" value={serverList.length} detail="来自真实登记记录" icon={Server} />
      <MetricCard label="在线节点" value={onlineCount} detail="以节点最后探活为准" icon={Activity} accent="cyan" />
      <MetricCard label="待探活" value={unknownCount} detail="未返回有效探活结果" icon={Globe2} accent="amber" />
      <MetricCard label="治理记录" value={changeList.length + queryAuditList.length} detail={`${changeList.length} 条变更 · ${queryAuditList.length} 条查询审计`} icon={FileCode2} accent="blue" />
    </div>

    {showAssetForm && <TechCard label="REGISTER SERVER ASSET" className="animate-in fade-in-0 slide-in-from-top-2 duration-200"><div className="grid gap-4 md:grid-cols-3">
      <Input placeholder="资产名称 *" value={asset.name} onChange={event => setAsset({ ...asset, name: event.target.value })} />
      <Input placeholder="主机名 / FQDN *" value={asset.hostname} onChange={event => setAsset({ ...asset, hostname: event.target.value })} />
      <Input placeholder="IP 地址" value={asset.ipAddress} onChange={event => setAsset({ ...asset, ipAddress: event.target.value })} />
      <Input placeholder="操作系统" value={asset.operatingSystem} onChange={event => setAsset({ ...asset, operatingSystem: event.target.value })} />
      <Input placeholder="网络区域" value={asset.zone} onChange={event => setAsset({ ...asset, zone: event.target.value })} />
      <Input placeholder="负责人" value={asset.owner} onChange={event => setAsset({ ...asset, owner: event.target.value })} />
      <Input placeholder="密钥引用（不填写明文密码）" value={asset.credentialRef} onChange={event => setAsset({ ...asset, credentialRef: event.target.value })} />
      <Input placeholder="能力标签：ssh,agent" value={asset.capabilities} onChange={event => setAsset({ ...asset, capabilities: event.target.value })} />
      <div className="flex items-center gap-2"><Button className="bg-cyan-200 text-slate-950 hover:bg-cyan-100" onClick={submitServer} disabled={createServer.isPending}>保存资产</Button><Button variant="ghost" onClick={() => setShowAssetForm(false)}>取消</Button></div>
    </div></TechCard>}

    <div className="grid gap-6 xl:grid-cols-[1.15fr_.85fr]">
      <TechCard label="SERVER INVENTORY"><div className="flex items-center justify-between gap-4"><div><h2 className="text-xl font-semibold text-white">服务器资产清单</h2><p className="mt-1 text-sm text-slate-400">登记主机、网络区域和受控能力；状态由探活回报更新。</p></div><Server className="h-7 w-7 text-cyan-200" /></div><div className="mt-5 overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="border-b border-slate-700 text-xs text-slate-500"><tr><th className="pb-3">服务器 / 主机</th><th className="pb-3">系统 / 区域</th><th className="pb-3">状态</th><th className="pb-3">凭据边界</th><th className="pb-3">操作</th></tr></thead><tbody>{serverList.length === 0 ? <tr><td colSpan={5} className="py-14 text-center text-slate-500">尚未登记服务器资产。登记后，受控节点可在内网执行探活。</td></tr> : serverList.map(item => <tr key={item.id} onClick={() => setSelectedServerId(item.id)} className="cursor-pointer border-b border-slate-800 transition-colors hover:bg-slate-800/40"><td className="py-4"><p className="font-medium text-white">{item.name}</p><p className="mt-1 font-mono text-xs text-slate-500">{item.hostname}{item.ipAddress ? ` · ${item.ipAddress}` : ""}</p></td><td className="py-4 text-slate-300">{item.operatingSystem ?? "—"}<span className="block text-xs text-slate-500">{item.zone ?? "未分区"}</span></td><td className="py-4"><StatusPill status={item.status} /></td><td className="py-4 font-mono text-xs text-slate-400">{item.credentialRef ? "密钥引用" : "未配置"}</td><td className="py-4"><Button size="sm" variant="outline" className="border-cyan-200/30 text-cyan-100" onClick={event => { event.stopPropagation(); requestProbe(item.id); }} disabled={probeServer.isPending}>探活</Button></td></tr>)}</tbody></table></div></TechCard>

      {selectedServerId !== null && <TechCard label="SERVER DETAIL"><div className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-semibold text-white">服务器详情</h2><p className="mt-1 text-sm text-slate-400">详情数据来自真实服务器资产记录；探活只通过受控节点回报。</p></div><Button variant="ghost" onClick={() => setSelectedServerId(null)}>关闭</Button></div>{serverDetail.data ? <div className="mt-5 grid gap-4 sm:grid-cols-2"><div><p className="text-xs text-slate-500">主机</p><p className="mt-1 text-sm text-white">{serverDetail.data.asset.hostname}{serverDetail.data.asset.ipAddress ? ` · ${serverDetail.data.asset.ipAddress}` : ""}</p></div><div><p className="text-xs text-slate-500">状态</p><div className="mt-1"><StatusPill status={serverDetail.data.asset.status} /></div></div><div><p className="text-xs text-slate-500">操作系统 / 区域</p><p className="mt-1 text-sm text-slate-300">{serverDetail.data.asset.operatingSystem ?? "—"} · {serverDetail.data.asset.zone ?? "未分区"}</p></div><div><p className="text-xs text-slate-500">负责人 / 凭据</p><p className="mt-1 text-sm text-slate-300">{serverDetail.data.asset.owner ?? "—"} · {serverDetail.data.asset.credentialRef ? "密钥引用" : "未配置"}</p></div><div className="sm:col-span-2"><p className="text-xs text-slate-500">能力标签</p><p className="mt-1 font-mono text-xs text-cyan-100">{serverDetail.data.asset.capabilities?.join(" · ") || "—"}</p></div><div className="sm:col-span-2"><p className="text-xs text-slate-500">探活时间 / 最近消息</p><p className="mt-1 text-sm text-slate-300">{serverDetail.data.asset.lastCheckedAt ? new Date(serverDetail.data.asset.lastCheckedAt).toLocaleString() : "尚无真实探活回报"} · {serverDetail.data.asset.lastProbeMessage ?? "未请求探活"}</p></div><div><p className="text-xs text-slate-500">关联数据库实例</p><p className="mt-1 text-sm text-slate-300">{serverDetail.data.instances.length ? serverDetail.data.instances.map(instance => `${instance.name} · ${instance.engine}${instance.version ? ` · ${instance.version}` : ""}${instance.metadata ? ` · 对象 ${String(instance.metadata.objectCount ?? instance.metadata.tableCount ?? "—")}` : ""}${instance.metadataSyncedAt ? ` · 同步 ${new Date(instance.metadataSyncedAt).toLocaleString()}` : ""}`).join("，") : "暂无关联实例"}</p></div><div><p className="text-xs text-slate-500">关联执行节点</p><p className="mt-1 text-sm text-slate-300">{serverDetail.data.nodes.length ? serverDetail.data.nodes.map(node => `${node.name} · ${node.status}`).join("，") : "暂无关联节点"}</p></div><div className="sm:col-span-2"><Button className="bg-cyan-200 text-slate-950 hover:bg-cyan-100" onClick={() => serverDetail.data && requestProbe(serverDetail.data.asset.id)} disabled={probeServer.isPending}><Activity className="mr-2 h-4 w-4" />请求受控探活</Button></div></div> : <p className="mt-6 text-sm text-slate-500">正在读取详情…</p>}</TechCard>}

      <TechCard label="SQL REVIEW GATE"><div className="flex items-center justify-between"><div><h2 className="text-xl font-semibold text-white">SQL 审核闸门</h2><p className="mt-1 text-sm text-slate-400">借鉴 Bytebase / Yearning 的规则审核与变更工单工作流。</p></div><ShieldCheck className="h-7 w-7 text-emerald-200" /></div><div className="mt-5 space-y-3"><Input placeholder="变更标题 *" value={change.title} onChange={event => setChange({ ...change, title: event.target.value })} /><div className="grid grid-cols-2 gap-3"><Input placeholder="数据库引擎" value={change.engine} onChange={event => setChange({ ...change, engine: event.target.value })} /><div className="flex items-center rounded-md border border-slate-700 bg-slate-900/50 px-3 text-xs text-slate-400"><TerminalSquare className="mr-2 h-4 w-4 text-cyan-200" />仅生成审核结果</div></div><Textarea className="min-h-36 font-mono text-xs" placeholder="输入待审核 SQL，不会在控制面直接执行" value={change.sqlText} onChange={event => setChange({ ...change, sqlText: event.target.value })} /><Textarea className="min-h-20 font-mono text-xs" placeholder="可选：回滚 SQL" value={change.rollbackSql} onChange={event => setChange({ ...change, rollbackSql: event.target.value })} />{change.sqlText && <div className={`rounded-md border p-3 text-xs ${reviewData.passed ? "border-emerald-300/30 bg-emerald-300/10" : "border-amber-300/30 bg-amber-300/10"}`}><div className="flex items-center gap-2 font-medium text-white">{reviewData.passed ? <CheckCircle2 className="h-4 w-4 text-emerald-300" /> : <ShieldCheck className="h-4 w-4 text-amber-200" />}审核{reviewData.passed ? "通过初检" : "发现需处理项"}</div><div className="mt-2 space-y-1 text-slate-300">{reviewData.findings.map((finding, index) => <p key={`${finding.rule}-${index}`}><span className="font-mono text-slate-500">{finding.rule}</span> · {finding.message}</p>)}</div></div>}<Button className="w-full bg-cyan-200 text-slate-950 hover:bg-cyan-100" onClick={submitChange} disabled={createChange.isPending}><FileCode2 className="mr-2 h-4 w-4" />创建变更审核工单</Button></div></TechCard>
    </div>

    <TechCard label="CHANGE MANAGEMENT"><div className="flex items-center justify-between"><div><h2 className="text-xl font-semibold text-white">变更工单与查询审计</h2><p className="mt-1 text-sm text-slate-400">每条工单保留规则结果、风险和后续受控执行关联；查询只记录审计摘要，不在控制面执行。</p></div><Database className="h-7 w-7 text-cyan-200" /></div><div className="mt-5 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-slate-700 text-xs text-slate-500"><tr><th className="pb-3">工单</th><th className="pb-3">引擎</th><th className="pb-3">风险</th><th className="pb-3">状态</th><th className="pb-3">审核结果</th></tr></thead><tbody>{changeList.length === 0 ? <tr><td colSpan={5} className="py-14 text-center text-slate-500">暂无真实变更工单。创建工单后将在这里显示 SQL 审核与审批状态。</td></tr> : changeList.map(item => <tr key={item.id} className="border-b border-slate-800"><td className="py-4"><p className="font-medium text-white">{item.title}</p><p className="font-mono text-xs text-slate-500">{item.requestKey}</p></td><td className="py-4 font-mono text-xs text-slate-300">{item.engine}</td><td className="py-4"><StatusPill status={item.riskLevel} /></td><td className="py-4"><StatusPill status={item.status} /></td><td className="py-4 text-xs text-slate-400">{item.reviewResult?.findings?.length ?? 0} 条规则结果</td></tr>)}</tbody></table></div></TechCard>
  </main>;
}
