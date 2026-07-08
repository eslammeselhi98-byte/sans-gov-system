"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  CalendarRange, FileSpreadsheet, Wallet, ClipboardList,
  ShieldAlert, Brain, ArrowRight, TrendingUp, Gauge, Activity,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import SCurveChart from "@/components/SCurveChart";
import {
  StatusBadge, ProgressBar, PerfBadge, DataTable, THead,
  SkeletonRow, EmptyState, SectionHeader, Btn,
} from "@/components/ui";
import {
  getProject, getProjectStats, getSchedule, getBOQ, getCostSummary,
  getDailyReports, getRisks, runAIAnalysis,
  Project, WBSItem, BOQItem, Risk, DailyReport,
} from "@/lib/apiExtended";

type Tab = "schedule" | "boq" | "cost" | "reports" | "risks" | "ai";

const TABS: { id: Tab; label: string; icon: any }[] = [
  { id: "schedule", label: "الجدول الزمني", icon: CalendarRange },
  { id: "boq", label: "جداول الكميات", icon: FileSpreadsheet },
  { id: "cost", label: "التكلفة", icon: Wallet },
  { id: "reports", label: "التقارير", icon: ClipboardList },
  { id: "risks", label: "المخاطر", icon: ShieldAlert },
  { id: "ai", label: "الذكاء الاصطناعي", icon: Brain },
];

export default function ProjectDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<Tab>("schedule");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getProject(id), getProjectStats(id)])
      .then(([proj, st]) => { setProject(proj); setStats(st); })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !project) {
    return (
      <DashboardLayout>
        <div className="py-24 text-center text-ink3 text-sm">جارٍ تحميل بيانات المشروع...</div>
      </DashboardLayout>
    );
  }

  const ev = project.earned_value;

  return (
    <DashboardLayout>
      {/* Project Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs num text-copper font-medium">{project.code}</span>
              <StatusBadge status={project.status} />
            </div>
            <h1 className="font-display text-xl font-semibold text-white">
              {project.name_ar || project.name}
            </h1>
            <p className="text-sm text-ink3 mt-1">{project.client_ar || project.client}</p>
          </div>
          <div className="flex gap-4 text-right">
            {ev && (
              <>
                <PerfBadge label="SPI" value={ev.spi} />
                <PerfBadge label="CPI" value={ev.cpi} />
                <div className="text-right">
                  <p className="text-[10px] text-ink3">نسبة الإنجاز</p>
                  <p className="text-base font-display font-semibold num text-signal">{ev.percent_complete.toFixed(1)}%</p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
          {[
            { label: "إجمالي الأنشطة", value: stats?.activities?.total ?? "—", sub: `${stats?.activities?.critical ?? 0} حرج` },
            { label: "أنشطة متأخرة", value: stats?.activities?.overdue ?? "—", danger: (stats?.activities?.overdue ?? 0) > 0 },
            { label: "مخاطر مفتوحة", value: stats?.risks?.open ?? "—", danger: (stats?.risks?.open ?? 0) > 0 },
            { label: "تقارير يومية", value: stats?.reports?.total_submitted ?? "—" },
          ].map((k) => (
            <div key={k.label} className="bg-surface border border-line rounded-lg p-3">
              <p className="text-[11px] text-ink3">{k.label}</p>
              <p className={`font-display num text-2xl font-semibold mt-1 ${k.danger ? "text-danger" : "text-white"}`}>
                {k.value}
              </p>
              {k.sub && <p className="text-[10px] text-ink3 mt-0.5">{k.sub}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-line overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "text-copper border-copper"
                : "text-ink3 border-transparent hover:text-white"
            }`}
          >
            <tab.icon size={14} strokeWidth={2} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "schedule" && <ScheduleTab projectId={id} />}
      {activeTab === "boq" && <BOQTab projectId={id} />}
      {activeTab === "cost" && <CostTab projectId={id} project={project} />}
      {activeTab === "reports" && <ReportsTab projectId={id} />}
      {activeTab === "risks" && <RisksTab projectId={id} />}
      {activeTab === "ai" && <AITab projectId={id} />}
    </DashboardLayout>
  );
}

// ─── Schedule Tab ─────────────────────────────────────────────

function ScheduleTab({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<WBSItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSchedule(projectId).then((r) => setItems(r.items)).finally(() => setLoading(false));
  }, [projectId]);

  return (
    <div className="space-y-5">
      <SCurveChart />
      <DataTable>
        <THead cols={["الكود", "اسم النشاط", "البداية المخططة", "النهاية المخططة", "% إنجاز", "Float", "حرج"]} />
        <tbody className="divide-y divide-line">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
            : items.filter((i) => i.is_activity).map((item) => (
                <tr key={item.id} className={`hover:bg-surface-raised transition-colors ${item.is_critical ? "border-r-2 border-danger" : ""}`}>
                  <td className="px-4 py-2.5 text-xs num text-ink3">{item.code ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <p className="text-xs text-white" style={{ paddingRight: `${(item.level - 1) * 16}px` }}>
                      {item.is_critical && <span className="inline-block w-1.5 h-1.5 rounded-full bg-danger mr-1.5 mb-0.5" />}
                      {item.name_ar || item.name}
                    </p>
                  </td>
                  <td className="px-4 py-2.5 text-xs num text-ink2">{item.planned_start ?? "—"}</td>
                  <td className="px-4 py-2.5 text-xs num text-ink2">{item.planned_finish ?? "—"}</td>
                  <td className="px-4 py-2.5 w-28">
                    <div className="flex items-center gap-1.5">
                      <ProgressBar value={item.percent_complete} height="h-1" />
                      <span className="text-[11px] num text-ink2 shrink-0">{item.percent_complete.toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className={`px-4 py-2.5 text-xs num ${item.total_float <= 0 ? "text-danger" : "text-ok"}`}>
                    {item.total_float}د
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {item.is_critical && <span className="text-[10px] text-danger">●</span>}
                  </td>
                </tr>
              ))}
        </tbody>
      </DataTable>
    </div>
  );
}

// ─── BOQ Tab ──────────────────────────────────────────────────

function BOQTab({ projectId }: { projectId: string }) {
  const [data, setData] = useState<{ total_value: number; items: BOQItem[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBOQ(projectId).then(setData).finally(() => setLoading(false));
  }, [projectId]);

  const fmtSAR = (n: number) =>
    n.toLocaleString("ar-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 });

  return (
    <div>
      {data && (
        <div className="bg-surface border border-line rounded-xl p-4 mb-4 flex items-center justify-between">
          <p className="text-sm text-ink2">إجمالي قيمة العقد (BOQ)</p>
          <p className="font-display font-semibold text-xl text-copper num">{fmtSAR(data.total_value)}</p>
        </div>
      )}
      <DataTable>
        <THead cols={["م", "البند", "الوحدة", "الكمية", "سعر الوحدة", "الإجمالي", "الكمية الفعلية"]} />
        <tbody className="divide-y divide-line">
          {loading
            ? Array.from({ length: 10 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
            : data?.items.map((item) => (
                <tr key={item.id} className={`hover:bg-surface-raised ${item.is_parent ? "bg-surface-raised" : ""}`}>
                  <td className="px-4 py-2.5 text-xs num text-ink3">{item.item_number ?? "—"}</td>
                  <td className="px-4 py-2.5 max-w-xs">
                    <p className={`text-xs ${item.is_parent ? "font-semibold text-copper" : "text-ink2"}`}
                       style={{ paddingRight: `${(item.level - 1) * 16}px` }}>
                      {item.description_ar || item.description}
                    </p>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-ink3">{item.unit ?? "—"}</td>
                  <td className="px-4 py-2.5 text-xs num text-ink2">{item.quantity.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-xs num text-ink2">{item.unit_rate.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-xs num text-white font-medium">
                    {item.total_amount.toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-xs num">
                    <span className={item.actual_quantity > item.quantity ? "text-danger" : "text-ink3"}>
                      {item.actual_quantity.toLocaleString()}
                    </span>
                  </td>
                </tr>
              ))}
        </tbody>
      </DataTable>
    </div>
  );
}

// ─── Cost Tab ─────────────────────────────────────────────────

function CostTab({ projectId, project }: { projectId: string; project: Project }) {
  const [cost, setCost] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCostSummary(projectId).then(setCost).finally(() => setLoading(false));
  }, [projectId]);

  const ev = project.earned_value;
  const fmtSAR = (n: number) => n.toLocaleString("ar-SA", { maximumFractionDigits: 0 }) + " ر.س";
  const CATEGORIES_AR: Record<string, string> = {
    labor: "عمالة", equipment: "معدات", material: "مواد",
    subcontract: "مقاولو باطن", overhead: "مصاريف عامة", other: "أخرى",
  };

  return (
    <div className="space-y-5">
      {/* EVM Cards */}
      {ev && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "القيمة المخططة (BCWS)", value: ev.bcws, color: "text-ink2" },
            { label: "القيمة المكتسبة (BCWP)", value: ev.bcwp, color: "text-signal" },
            { label: "التكلفة الفعلية (ACWP)", value: ev.acwp, color: "text-copper" },
            { label: "التقدير عند الاكتمال (EAC)", value: ev.eac, color: ev.eac > ev.bac ? "text-danger" : "text-ok" },
          ].map((k) => (
            <div key={k.label} className="bg-surface border border-line rounded-xl p-4">
              <p className="text-[11px] text-ink3 mb-2">{k.label}</p>
              <p className={`font-display num text-lg font-semibold ${k.color}`}>{fmtSAR(k.value)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Actual cost by category */}
      {!loading && cost && (
        <div className="bg-surface border border-line rounded-xl p-5">
          <SectionHeader title="التكلفة الفعلية حسب التصنيف" />
          <div className="space-y-3">
            {Object.entries(cost.by_category as Record<string, number>).map(([cat, amount]) => (
              <div key={cat} className="flex items-center gap-3">
                <p className="text-xs text-ink2 w-28 shrink-0">{CATEGORIES_AR[cat] || cat}</p>
                <div className="flex-1">
                  <ProgressBar
                    value={amount}
                    max={cost.total_actual_cost || 1}
                    color="bg-copper"
                    height="h-2"
                  />
                </div>
                <p className="text-xs num text-ink2 w-32 text-left">{fmtSAR(amount)}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-line flex justify-between">
            <span className="text-xs text-ink3">نسبة الاستهلاك</span>
            <span className={`text-sm font-display font-semibold num ${cost.utilization_pct > 90 ? "text-danger" : "text-ok"}`}>
              {cost.utilization_pct.toFixed(1)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Reports Tab ──────────────────────────────────────────────

function ReportsTab({ projectId }: { projectId: string }) {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [loading, setLoading] = useState(true);

  const WEATHER_AR: Record<string, string> = {
    sunny: "☀️ مشمس", cloudy: "☁️ غائم", partly_cloudy: "⛅ غائم جزئياً",
    rainy: "🌧️ ممطر", stormy: "🌪️ عاصف", dusty: "💨 عاصف رملي",
  };

  useEffect(() => {
    getDailyReports({ project_id: projectId, size: 30 } as any)
      .then((r) => setReports(r.items))
      .finally(() => setLoading(false));
  }, [projectId]);

  return (
    <DataTable>
      <THead cols={["التاريخ", "الطقس", "أعمال اليوم", "التقدم", "الحالة"]} />
      <tbody className="divide-y divide-line">
        {loading
          ? Array.from({ length: 7 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
          : reports.map((r) => (
              <tr key={r.id} className="hover:bg-surface-raised transition-colors">
                <td className="px-4 py-3 text-xs num text-ink2">{r.report_date}</td>
                <td className="px-4 py-3 text-xs">{WEATHER_AR[r.weather_condition] ?? r.weather_condition}
                  {r.weather_temp && <span className="text-ink3 num"> {r.weather_temp}°C</span>}
                </td>
                <td className="px-4 py-3 text-xs text-ink2 max-w-xs truncate">
                  {r.work_performed ?? <span className="text-ink3">لا يوجد وصف</span>}
                </td>
                <td className="px-4 py-3 w-24">
                  {r.overall_progress != null ? (
                    <div className="flex items-center gap-1.5">
                      <ProgressBar value={r.overall_progress} height="h-1" />
                      <span className="text-[11px] num shrink-0">{r.overall_progress.toFixed(0)}%</span>
                    </div>
                  ) : <span className="text-ink3">—</span>}
                </td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
              </tr>
            ))}
      </tbody>
    </DataTable>
  );
}

// ─── Risks Tab ────────────────────────────────────────────────

const RISK_LEVEL_COLOR: Record<string, string> = {
  critical: "bg-danger/10 border-danger/30 text-danger",
  high: "bg-warn/10 border-warn/30 text-warn",
  medium: "bg-copper/10 border-copper/30 text-copper",
  low: "bg-ok/10 border-ok/30 text-ok",
};

function RisksTab({ projectId }: { projectId: string }) {
  const [data, setData] = useState<{ items: Risk[]; open_count: number } | null>(null);

  useEffect(() => { getRisks(projectId).then(setData); }, [projectId]);

  return (
    <div className="space-y-3">
      {data?.items.map((r) => (
        <div key={r.id} className={`border rounded-xl p-4 ${RISK_LEVEL_COLOR[r.risk_level] ?? "border-line"}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-white">{r.title_ar || r.title}</p>
              {r.category && <p className="text-[11px] text-ink3 mt-0.5">{r.category}</p>}
              {r.mitigation_plan && (
                <p className="text-xs text-ink2 mt-2 leading-relaxed">{r.mitigation_plan}</p>
              )}
            </div>
            <div className="text-right shrink-0">
              <StatusBadge status={r.risk_level} />
              <p className="text-[11px] num text-ink3 mt-1">درجة {r.risk_score}/25</p>
            </div>
          </div>
        </div>
      ))}
      {data?.items.length === 0 && (
        <EmptyState icon={<ShieldAlert size={28} />} title="لا توجد مخاطر مسجلة" />
      )}
    </div>
  );
}

// ─── AI Tab ───────────────────────────────────────────────────

const AI_ANALYSIS_TYPES = [
  { id: "schedule", label: "تحليل الجدول الزمني", icon: CalendarRange },
  { id: "cost", label: "تحليل التكلفة والقيمة المكتسبة", icon: Wallet },
  { id: "risk", label: "تحليل المخاطر", icon: ShieldAlert },
  { id: "executive", label: "تقرير تنفيذي شامل", icon: TrendingUp },
];

function AITab({ projectId }: { projectId: string }) {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [selectedType, setSelectedType] = useState("executive");

  async function runAnalysis(type: string) {
    setLoading(true);
    setResult(null);
    try {
      const r = await runAIAnalysis({ project_id: projectId, analysis_type: type, language: "ar" });
      setResult(r.result);
    } catch (e: any) {
      setResult("حدث خطأ أثناء التحليل: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function askQuestion() {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await runAIAnalysis({ project_id: projectId, analysis_type: "chat", language: "ar", question });
      setResult(r.result);
    } catch (e: any) {
      setResult("حدث خطأ: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Quick analysis */}
      <div className="bg-surface border border-line rounded-xl p-5">
        <SectionHeader title="تحليل فوري بالذكاء الاصطناعي" subtitle="اختر نوع التحليل" />
        <div className="grid grid-cols-2 gap-2 mb-4">
          {AI_ANALYSIS_TYPES.map((t) => (
            <button
              key={t.id}
              onClick={() => { setSelectedType(t.id); runAnalysis(t.id); }}
              disabled={loading}
              className={`flex items-center gap-2 p-3 rounded-lg border text-right text-xs transition-colors disabled:opacity-40 ${
                selectedType === t.id
                  ? "border-copper/40 bg-copper/10 text-copper"
                  : "border-line hover:border-line-soft text-ink2 hover:text-white"
              }`}
            >
              <t.icon size={14} strokeWidth={2} />
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Free question */}
      <div className="bg-surface border border-line rounded-xl p-5">
        <p className="text-xs text-ink3 mb-2">اسأل سؤالاً محدداً عن المشروع</p>
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && askQuestion()}
            placeholder="مثال: ما هو سبب تأخر نشاط الحفريات؟"
            className="flex-1 bg-ink border border-line rounded-lg px-3 py-2 text-sm text-white placeholder:text-ink3 focus:border-signal/50"
          />
          <Btn variant="primary" onClick={askQuestion} disabled={loading || !question.trim()}>
            تحليل
          </Btn>
        </div>
      </div>

      {/* Result */}
      {loading && (
        <div className="bg-surface border border-line rounded-xl p-6 text-center">
          <p className="text-sm text-ink3 animate-pulse">⏳ جارٍ تحليل بيانات المشروع بالذكاء الاصطناعي...</p>
        </div>
      )}
      {result && (
        <div className="bg-surface border border-signal/20 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={16} className="text-signal" />
            <p className="text-xs font-medium text-signal">تحليل الذكاء الاصطناعي</p>
          </div>
          <div className="text-sm text-ink2 leading-relaxed whitespace-pre-wrap">{result}</div>
        </div>
      )}
    </div>
  );
}
