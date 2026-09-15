import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { ClientDashboard } from "@/components/dashboards/ClientDashboard";
import { OfficerDashboard } from "@/components/dashboards/OfficerDashboard";
import { HeadOfClaimsDashboard } from "@/components/dashboards/HeadOfClaimsDashboard";
import { ServiceProviderDashboard } from "@/components/dashboards/ServiceProviderDashboard";
import { FinanceDashboard } from "@/components/dashboards/FinanceDashboard";
import { SparePartsDashboard } from "@/components/dashboards/SparePartsDashboard";
import { LegalDashboard } from "@/components/dashboards/LegalDashboard";
import { AdminDashboard } from "@/components/dashboards/AdminDashboard";
import { SuperAdminDashboard } from "@/components/dashboards/SuperAdminDashboard";

export default async function AppHome({
  searchParams,
}: {
  searchParams: { status?: string; category?: string; q?: string };
}) {
  const session = await getSession();
  if (!session.authenticated) redirect("/login");

  const { status, category, q } = searchParams;

  switch (session.role) {
    case "client":
      return <ClientDashboard email={session.email} fullName={session.full_name} />;
    case "claims_officer":
      return <OfficerDashboard email={session.email} status={status} category={category} q={q} />;
    case "head_of_claims":
      return <HeadOfClaimsDashboard />;
    case "assessor":
    case "garage":
    case "investigator":
      return <ServiceProviderDashboard role={session.role} />;
    case "finance":
    case "finance_head":
      return <FinanceDashboard />;
    case "spare_parts":
      return <SparePartsDashboard fullName={session.full_name} />;
    case "legal":
      return <LegalDashboard />;
    case "admin":
      return <AdminDashboard />;
    case "super_admin":
      return <SuperAdminDashboard />;
    default:
      return <p>Unknown role. Contact your administrator.</p>;
  }
}
