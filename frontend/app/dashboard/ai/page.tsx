"use client";

import { useEffect, useState } from "react";
import { Brain, CheckCircle2, AlertTriangle, TrendingUp, Wallet, Shield } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { SectionHeader, StatusBadge, Btn } from "@/components/ui";
import { getAIRecommendations, runAIAnalysis } from "@/lib/apiExtended";

const PRIORITY_ICON: Record<string, any> = {
  critical: AlertTriangle,
  high: AlertTriangle,
  medium: TrendingUp,
  low: TrendingUp,
};

const CATEGORY_AR: Record<string, string> = {
  schedule: "الجدول الزمني",
  cost: "التكلفة",
  risk: "المخاطر",
  hr_compliance: "الامتثال الإداري",
  executive: "تنفيذي",
  productivity: "الإنتاجية",
};

export default function AIPage() {
  const [recs, setRecs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatResult, setChatResult] = useState<string | null>(null);

  useEffect(() => {
    getAIRecommendations()
      .then(setRecs)
      .catch(() => setRecs([]))
      .finally(() => setLoading(false));
  }, []);

  async function askGeneral() {
    if (!chatInput.trim()) return;
    setChatLoading(true);
    setChatResult(null);
    try {
      const r = await runAIAnalysis({ analysis_type: "chat", language: "ar", question: chatInput });
      setChatResult(r.result);
    } catch (e: any) {
      setChatResult("حدث خطأ: " + e.message);
    } finally {
      setChatLoading(false);
    }
  }

  const unread = recs.filter((r) => !r.acknowledged);

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-xl font-semibold text-white">مركز الذكاء الاصطناعي</h1>
          <p className="text-xs text-ink3 mt-0.5">محرك القرارات التلقائية — مدعوم بـ Claude</p>
        </div>
        {unread.length > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-warn/10 border border-warn/30 rounded-lg">
            <AlertTriangle size={13} className="text-warn" />
            <span className="text-xs text-warn">{unread.length} توصية تحتاج مراجعة</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Left: Recommendations */}
        <div className="lg:col-span-3 space-y-3">
          <SectionHeader
            title="التوصيات التلقائية"
            subtitle={loading ? "جارٍ التحميل..." : `${recs.length} توصية`}
          />
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 bg-surface border border-line rounded-xl animate-pulse" />
              ))}
            </div>
          ) : recs.length === 0 ? (
            <div className="bg-surface border border-line rounded-xl p-8 text-center">
              <CheckCircle2 size={28} className="text-ok mx-auto mb-2" />
              <p className="text-sm text-white">لا توجد توصيات معلقة</p>
              <p className="text-xs text-ink3 mt-1">جميع المشاريع تسير حسب الخطة</p>
            </div>
          ) : (
            recs.map((rec) => {
              const Icon = PRIORITY_ICON[rec.priority] || TrendingUp;
              const border = {
                critical: "border-danger/30 bg-danger/5",
                high: "border-warn/30 bg-warn/5",
                medium: "border-copper/30 bg-copper/5",
                low: "border-line bg-surface",
              }[rec.priority as string] ?? "border-line bg-surface";

              return (
                <div key={rec.id} className={`border rounded-xl p-4 ${border}`}>
                  <div className="flex items-start gap-3">
                    <Icon size={14} className={
                      rec.priority === "critical" || rec.priority === "high" ? "text-danger mt-0.5" : "text-copper mt-0.5"
                    } strokeWidth={2} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-xs font-semibold text-white">{rec.title_ar || rec.title}</p>
                        <StatusBadge status={rec.priority} />
                        {rec.category && (
                          <span className="text-[10px] text-ink3">{CATEGORY_AR[rec.category] || rec.category}</span>
                        )}
                      </div>
                      <p className="text-xs text-ink2 leading-relaxed">
                        {rec.recommendation_ar || rec.recommendation}
                      </p>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-[10px] num text-ink3">{rec.created_at?.split("T")[0]}</span>
                        <Btn variant="ghost" size="sm">تأكيد المراجعة</Btn>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: AI Chat */}
        <div className="lg:col-span-2">
          <div className="bg-surface border border-line rounded-xl p-5 sticky top-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-signal/10 border border-signal/20 flex items-center justify-center">
                <Brain size={15} className="text-signal" />
              </div>
              <div>
                <p className="text-sm font-display font-semibold text-white">المساعد الذكي</p>
                <p className="text-[10px] text-ink3">اسأل عن أي مشروع أو قرار</p>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              {[
                "ما المشاريع المتأخرة حالياً؟",
                "ما المخاطر الحرجة المفتوحة؟",
                "هل يوجد موظفون إقامتهم على وشك الانتهاء؟",
                "ما توصيتك لتسريع التقدم في مشروع KAIA؟",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setChatInput(q)}
                  className="w-full text-right text-xs text-ink2 hover:text-white px-3 py-2 rounded-lg hover:bg-line-soft border border-transparent hover:border-line transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>

            <div className="border-t border-line pt-4 space-y-3">
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="اكتب سؤالك هنا..."
                rows={3}
                className="w-full bg-ink border border-line rounded-lg px-3 py-2 text-sm text-white placeholder:text-ink3 resize-none focus:border-signal/50 transition-colors"
              />
              <Btn
                variant="primary"
                onClick={askGeneral}
                disabled={chatLoading || !chatInput.trim()}
                className="w-full justify-center"
              >
                {chatLoading ? "جارٍ التحليل..." : "تحليل"}
              </Btn>
            </div>

            {chatResult && (
              <div className="mt-4 p-3 bg-ink border border-signal/20 rounded-lg max-h-64 overflow-y-auto">
                <p className="text-xs text-signal mb-2">الرد:</p>
                <p className="text-xs text-ink2 leading-relaxed whitespace-pre-wrap">{chatResult}</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
}
