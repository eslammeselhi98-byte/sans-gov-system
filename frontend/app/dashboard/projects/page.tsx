"use client";

import { useEffect, useState } from "react";
import { Building2, Plus, Search, Filter } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { StatusBadge, DataTable, THead, SkeletonRow, EmptyState, ProgressBar, PerfBadge, Btn } from "@/components/ui";
import { getProjects, Project } from "@/lib/apiExtended";

const PROJECT_TYPE_AR: Record<string, string> = {
  substation: "محطة كهرباء",
  transmission_line: "خط نقل",
  utility_network: "شبكة مرافق",
  civil: "أعمال مدنية",
  maintenance: "صيانة",
  other: "أخرى",
};

const STATUS_FILTER = [
  { value: "", label: "الكل" },
  { value: "active", label: "نشطة" },
  { value: "planning", label: "تخطيط" },
  { value: "on_hold", label: "متوقفة" },
  { value: "completed", label: "مكتملة" },
];

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    getProjects({ status: statusFilter || undefined, search: search || undefined, page, size: 20 })
      .then((r) => { setProjects(r.items); setTotal(r.total); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [search, statusFilter, page]);

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-xl font-semibold text-white">المشاريع</h1>
          <p className="text-xs text-ink3 mt-0.5 num">{total} مشروع إجمالاً</p>
        </div>
        <Btn variant="primary">
          <Plus size={15} />
          مشروع جديد
        </Btn>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink3" />
          <input
            type="text"
            placeholder="بحث بالاسم أو رقم العقد..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full bg-surface border border-line rounded-lg pr-9 pl-3 py-2 text-sm text-white placeholder:text-ink3 focus:border-signal/50 transition-colors"
          />
        </div>
        <div className="flex gap-1">
          {STATUS_FILTER.map((f) => (
            <button
              key={f.value}
              onClick={() => { setStatusFilter(f.value); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                statusFilter === f.value
                  ? "bg-copper/15 text-copper border border-copper/30"
                  : "text-ink3 hover:text-white hover:bg-line-soft border border-transparent"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <DataTable>
        <THead cols={["الكود", "اسم المشروع", "العميل", "النوع", "الحالة", "التقدم", "SPI", "CPI", "نهاية الخطة", ""]} />
        <tbody className="divide-y divide-line">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={10} />)
            : projects.map((p) => (
                <ProjectRow key={p.id} project={p} />
              ))}
        </tbody>
      </DataTable>

      {!loading && projects.length === 0 && (
        <EmptyState
          icon={<Building2 size={32} />}
          title="لا توجد مشاريع"
          subtitle="أضف أول مشروع أو غيّر فلتر البحث"
          action={<Btn variant="primary"><Plus size={14} />مشروع جديد</Btn>}
        />
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2 mt-5">
          <Btn variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
            السابق
          </Btn>
          <span className="text-xs text-ink3 self-center num">صفحة {page} من {Math.ceil(total / 20)}</span>
          <Btn variant="secondary" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(total / 20)}>
            التالي
          </Btn>
        </div>
      )}
    </DashboardLayout>
  );
}

function ProjectRow({ project: p }: { project: Project }) {
  const ev = p.earned_value;
  const progress = ev?.percent_complete ?? 0;
  const overdue = p.days_remaining !== null && p.days_remaining < 0 && p.status === "active";

  return (
    <tr className="hover:bg-surface-raised transition-colors cursor-pointer">
      <td className="px-4 py-3 num text-xs text-copper font-medium whitespace-nowrap">{p.code}</td>
      <td className="px-4 py-3 max-w-xs">
        <p className="text-sm text-white font-medium truncate">{p.name_ar || p.name}</p>
        {p.city && <p className="text-[11px] text-ink3">{p.city} — {p.region}</p>}
      </td>
      <td className="px-4 py-3 text-xs text-ink2 whitespace-nowrap">{p.client_ar || p.client}</td>
      <td className="px-4 py-3 text-xs text-ink3 whitespace-nowrap">{PROJECT_TYPE_AR[p.project_type] || p.project_type}</td>
      <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
      <td className="px-4 py-3 w-28">
        <div className="flex items-center gap-2">
          <ProgressBar value={progress} color={progress >= 70 ? "bg-ok" : progress >= 40 ? "bg-signal" : "bg-copper"} />
          <span className="text-[11px] num text-ink2 shrink-0">{progress.toFixed(0)}%</span>
        </div>
      </td>
      <td className="px-4 py-3">{ev ? <PerfBadge label="SPI" value={ev.spi} /> : <span className="text-ink3 text-xs">—</span>}</td>
      <td className="px-4 py-3">{ev ? <PerfBadge label="CPI" value={ev.cpi} /> : <span className="text-ink3 text-xs">—</span>}</td>
      <td className="px-4 py-3 text-xs num whitespace-nowrap">
        <span className={overdue ? "text-danger" : "text-ink2"}>
          {p.planned_end_date ?? "—"}
          {overdue && <span className="text-danger text-[10px] block">متأخر {Math.abs(p.days_remaining!)} يوم</span>}
        </span>
      </td>
      <td className="px-4 py-3">
        <Btn variant="ghost" size="sm">فتح</Btn>
      </td>
    </tr>
  );
}
