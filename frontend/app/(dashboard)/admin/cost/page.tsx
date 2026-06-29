import type { Metadata } from "next";
import AdminCostPageClient from "./AdminCostPageClient";

export const metadata: Metadata = {
  title: "Cost dashboard",
  robots: { index: false, follow: false },
};

export default function AdminCostPage() {
  return <AdminCostPageClient />;
}
