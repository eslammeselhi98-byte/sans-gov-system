"use client";
import { FileText } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { EmptyState } from "@/components/ui";

export default function DocumentsPage() {
  return (
    <DashboardLayout>
      <h1 className="font-display text-xl font-semibold text-white mb-6">المستندات</h1>
      <EmptyState
        icon={<FileText size={28} />}
        title="وحدة المستندات"
        subtitle="الـ API جاهز — الواجهة البصرية قيد الإنشاء في الإصدار القادم"
      />
    </DashboardLayout>
  );
}
