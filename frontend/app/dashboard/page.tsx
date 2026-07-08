"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Building2, TrendingUp, Wallet, Users,
  ShieldAlert, ClipboardList, Gauge, Activity,
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import KpiCard from "@/components/KpiCard";
import SCurveChart from "@/components/SCurveChart";
import AlertsPanel from "@/components/AlertsPanel";
import { getExecutiveDashboard, getAlerts, ExecutiveDashboard, AlertItem } from "@/lib/api";

function fmtSAR(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toFixed(0);
}

function spiCpiAccent(value: number): "ok" | "warn" | "danger" {
  if (value >= 0.97) return "ok";
  if (value >= 0.9) return "warn";
  return "danger";
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<ExecutiveDashboard | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [dash, alertsRes] = await Promise.all([
          getExecutiveDashboard(),
          getAlerts(),
        ]);
        setData(dash);
        setAlerts(alertsRes.alerts);
      } catch (err: any) {
        if (err.message?.includes("401")) {
          router.push("/login");
          return;
        }
        setError(err.message || "تعذر تحميل البيانات");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <div className="flex-1 blueprint-bg bg-ink">
        <TopBar alertCount={alerts.length} />

        <main className="p-6 max-w-7xl mx-auto">
          {loading && (
            <div className="py-24 text-center text-ink3 text-sm">جارٍ تحميل البيانات...</div>
          )}

          {error && (
            <div className="bg-danger/10 border border-danger/30 rounded-xl p-4 text-sm text-danger">
              {error}
            </div>
          )}

          {data && (
            <>
              {/* Portfolio KPIs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <KpiCard
                  label="إجمالي المشاريع"
                  value={data.portfolio.total_projects}
                  icon={Building2}
                  accent="copper"
                  sublabel={`${data.portfolio.active} نشط حالياً`}
                />
                <KpiCard
                  label="القيمة التعاقدية الإجمالية"
                  value={fmtSAR(data.portfolio.total_value_sar)}
                  unit="ر.س"
                  icon={Wallet}
                  accent="signal"
                />
                <KpiCard
                  label="مؤشر أداء الجدول SPI"
                  value={data.performance.avg_spi.toFixed(2)}
                  icon={TrendingUp}
                  accent={spiCpiAccent(data.performance.avg_spi)}
                  sublabel={data.performance.avg_spi >= 1 ? "متقدم عن الخطة" : "متأخر عن الخطة"}
                />
                <KpiCard
                  label="مؤشر أداء التكلفة CPI"
                  value={data.performance.avg_cpi.toFixed(2)}
                  icon={Gauge}
                  accent={spiCpiAccent(data.performance.avg_cpi)}
                  sublabel={data.performance.avg_cpi >= 1 ? "ضمن الميزانية" : "تجاوز في التكلفة"}
                />
              </div>

              {/* Chart + Alerts */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                <div className="lg:col-span-2">
                  <SCurveChart />
                </div>
                <AlertsPanel alerts={alerts} />
              </div>

              {/* Secondary KPIs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiCard
                  label="الأنشطة المتأخرة"
                  value={data.performance.overdue_activities}
                  icon={Activity}
                  accent={data.performance.overdue_activities > 0 ? "danger" : "ok"}
                />
                <KpiCard
                  label="المخاطر المفتوحة"
                  value={data.alerts.open_risks}
                  icon={ShieldAlert}
                  accent={data.alerts.open_risks > 0 ? "warn" : "ok"}
                />
                <KpiCard
                  label="الموظفون النشطون"
                  value={data.workforce.active_employees}
                  icon={Users}
                  accent="neutral"
                  sublabel={`نسبة الحضور اليوم ${data.workforce.attendance_rate}%`}
                />
                <KpiCard
                  label="تقارير بانتظار التقديم"
                  value={data.alerts.pending_reports}
                  icon={ClipboardList}
                  accent={data.alerts.pending_reports > 0 ? "warn" : "ok"}
                />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
