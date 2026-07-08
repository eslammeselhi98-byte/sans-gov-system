"use client";

import { useEffect, useState } from "react";
import { ClipboardList, AlertCircle } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { StatusBadge, DataTable, THead, SkeletonRow, EmptyState, Btn } from "@/components/ui";
import { getDailyReports, DailyReport, getProjects, Project } from "@/lib/apiExtended";

const WEATHER_AR: Record<string, string> = {
  sunny: "☀️ مشمس", cloudy: "☁️ غائم", partly_cloudy: "⛅ غائم جزئياً",
  rainy: "🌧️ ممطر", stormy: "🌪️ عاصف", dusty: "💨 عاصف رملي", hot: "🌡️ حار",
};

export default function ReportsPage() {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    getProjects({ status: "active", size: 50 }).then((r) => setProjects(r.items));
  }, []);

  useEffect(() => {
    setLoading(true);
    getDailyReports({
      project_id: projectFilter || undefined,
      status: statusFilter || undefined,
    })
      .then((r) => { setReports(r.items); setTotal(r.total); })
      .finally(() => setLoading(false));
  }, [projectFilter, statusFilter]);

  const pending = reports.filter((r) => r.status === "submitted").length;

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-xl font-semibold text-white">التقارير اليومية</h1>
          <p className="text-xs text-ink3 mt-0.5 num">{total} تقرير</p>
        </div>
        {pending > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-signal/10 border border-signal/30 rounded-lg">
            <AlertCircle size={13} className="text-signal" />
            <span className="text-xs text-signal">{pending} تقرير بانتظار الاعتماد</span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="bg-surface border border-line rounded-lg px-3 py-2 text-sm text-ink2 focus:border-signal/50"
        >
          <option value="">كل المشاريع</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name_ar || p.name}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-surface border border-line rounded-lg px-3 py-2 text-sm text-ink2 focus:border-signal/50"
        >
          <option value="">كل الحالات</option>
          <option value="draft">مسودة</option>
          <option value="submitted">مقدّم</option>
          <option value="approved">معتمد</option>
          <option value="rejected">مرفوض</option>
        </select>
      </div>

      <DataTable>
        <THead cols={["التاريخ", "المشروع", "الطقس", "الأعمال المنجزة", "التقدم", "الحالة", ""]} />
        <tbody className="divide-y divide-line">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
            : reports.map((r) => (
                <tr key={r.id} className="hover:bg-surface-raised transition-colors">
                  <td className="px-4 py-3 text-xs num text-ink2 whitespace-nowrap">{r.report_date}</td>
                  <td className="px-4 py-3 text-xs text-ink2">{r.project_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-xs whitespace-nowrap">
                    {WEATHER_AR[r.weather_condition] ?? r.weather_condition}
                    {r.weather_temp && <span className="text-ink3 num"> {r.weather_temp}°C</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-ink2 max-w-xs truncate">
                    {r.work_performed ?? <span className="text-ink3">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs num text-ink2">
                    {r.overall_progress != null ? `${r.overall_progress.toFixed(0)}%` : "—"}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <Btn variant="ghost" size="sm">عرض</Btn>
                      {r.status === "submitted" && (
                        <Btn variant="secondary" size="sm">اعتماد</Btn>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
        </tbody>
      </DataTable>

      {!loading && reports.length === 0 && (
        <EmptyState
          icon={<ClipboardList size={28} />}
          title="لا توجد تقارير"
          subtitle="ابدأ باستخدام البوت على تليجرام لتقديم التقارير اليومية"
        />
      )}
    </DashboardLayout>
  );
}
