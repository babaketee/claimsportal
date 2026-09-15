import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { AppShell } from "@/components/AppShell";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.authenticated) redirect("/login");

  return (
    <AppShell role={session.role} email={session.email} fullName={session.full_name}>
      {children}
    </AppShell>
  );
}
