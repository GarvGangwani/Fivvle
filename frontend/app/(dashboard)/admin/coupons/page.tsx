import type { Metadata } from "next";
import AdminCouponsPageClient from "./AdminCouponsPageClient";

export const metadata: Metadata = {
  title: "Coupon management",
  robots: { index: false, follow: false },
};

export default function AdminCouponsPage() {
  return <AdminCouponsPageClient />;
}
