import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { Logo } from "@/components/Logo";
import { LoginForm } from "@/components/LoginForm";

export default async function LoginPage() {
  const session = await getSession();
  if (session.authenticated) redirect("/app");

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-brand-green-10 to-white px-4 py-10">
      <div className="w-full max-w-3xl">
        <div className="mb-8 text-center">
          <div className="inline-block">
            <Logo size={44} showTagline />
          </div>
        </div>
        <LoginForm />
        <p className="mt-6 text-center text-xs text-black/40">
          Definite Assurance Co. Ltd — Claims Portal v3.0 (revamp) · Demo environment
        </p>
      </div>
    </main>
  );
}
