import { AuthLayoutClient } from "./AuthLayoutClient";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthLayoutClient>{children}</AuthLayoutClient>;
}
