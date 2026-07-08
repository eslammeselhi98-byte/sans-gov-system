"use client";

import { useEffect, useState } from "react";
import { Users, AlertTriangle, Search, UserPlus } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import {
  StatusBadge, DataTable, THead, SkeletonRow, EmptyState,
  SectionHeader, Btn,
} from "@/components/ui";
import { getEmployees, getExpiringDocs, Employee } from "@/lib/apiExtended";

const TABS = [
  { id: "all", label: "كل الموظفين" },
  { id: "expiring", label: "وثائق منتهية / قاربت" },
];

export default function EmployeesPage() {
  const [tab, setTab] = useState("all");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [expiring, setExpiring] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getEmployees({ search: search || undefined, is_active: true }),
      getExpiringDocs(30),
    ])
      .then(([emp, exp]) => {
        setEmployees(emp.items);
        setTotal(emp.total);
        setExpiring(exp);
      })
      .finally(() => setLoading(false));
  }, [search]);

  const displayed = tab === "all" ? employees : expiring;

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-xl font-semibold text-white">الموظفون</h1>
          <p className="text-xs text-ink3 mt-0.5 num">{total} موظف نشط</p>
        </div>
        <div className="flex gap-2">
          {expiring.length > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-danger/10 border border-danger/30 rounded-lg">
              <AlertTriangle size={13} className="text-danger" />
              <span className="text-xs text-danger">{expiring.length} وثيقة منتهية / قاربت</span>
            </div>
          )}
          <Btn variant="primary"><UserPlus size={14} />إضافة موظف</Btn>
        </div>
      </div>

      {/* Tabs + search */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex gap-1 border-b border-line">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-xs font-medium border-b-2 -mb-px transition-colors ${
                tab === t.id ? "text-copper border-copper" : "text-ink3 border-transparent hover:text-white"
              }`}
            >
              {t.label}
              {t.id === "expiring" && expiring.length > 0 && (
                <span className="ml-1.5 num text-danger">{expiring.length}</span>
              )}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink3" />
          <input
            placeholder="بحث..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface border border-line rounded-lg pr-8 pl-3 py-1.5 text-xs text-white placeholder:text-ink3"
          />
        </div>
      </div>

      <DataTable>
        <THead cols={["رقم الموظف", "الاسم", "المسمى الوظيفي", "المشروع الحالي", "حالة الإقامة", "تاريخ انتهاء الإقامة", ""]} />
        <tbody className="divide-y divide-line">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={7} />)
            : displayed.map((emp) => <EmployeeRow key={emp.id} employee={emp} />)}
        </tbody>
      </DataTable>

      {!loading && displayed.length === 0 && (
        <EmptyState
          icon={<Users size={28} />}
          title={tab === "expiring" ? "لا توجد وثائق منتهية خلال 30 يوم" : "لا يوجد موظفون"}
          subtitle={tab === "expiring" ? "جميع وثائق الموظفين سارية" : undefined}
        />
      )}
    </DashboardLayout>
  );
}

function EmployeeRow({ employee: e }: { employee: Employee }) {
  const iqamaStatus = e.iqama_status;
  const daysLeft = e.iqama_expiry
    ? Math.ceil((new Date(e.iqama_expiry).getTime() - Date.now()) / 86400000)
    : null;

  return (
    <tr className="hover:bg-surface-raised transition-colors">
      <td className="px-4 py-3 text-xs num text-copper">{e.employee_number}</td>
      <td className="px-4 py-3">
        <p className="text-sm text-white">{e.full_name_ar || e.full_name}</p>
        {e.nationality && <p className="text-[11px] text-ink3">{e.nationality}</p>}
      </td>
      <td className="px-4 py-3 text-xs text-ink2">{e.position_name ?? "—"}</td>
      <td className="px-4 py-3 text-xs text-ink2">{e.current_project_id ? "مشروع نشط" : "—"}</td>
      <td className="px-4 py-3">
        {iqamaStatus ? <StatusBadge status={iqamaStatus} /> : <span className="text-ink3 text-xs">—</span>}
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs num ${iqamaStatus === "expired" ? "text-danger" : iqamaStatus === "expiring_soon" ? "text-warn" : "text-ink2"}`}>
          {e.iqama_expiry ?? "—"}
          {daysLeft !== null && daysLeft <= 30 && daysLeft >= 0 && (
            <span className="block text-[10px]">({daysLeft} يوم متبقي)</span>
          )}
          {daysLeft !== null && daysLeft < 0 && (
            <span className="block text-[10px] text-danger">(منتهية منذ {Math.abs(daysLeft)} يوم)</span>
          )}
        </span>
      </td>
      <td className="px-4 py-3">
        <Btn variant="ghost" size="sm">تفاصيل</Btn>
      </td>
    </tr>
  );
}
