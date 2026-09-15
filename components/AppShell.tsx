"use client";

import Link from "next/link";
import { useState } from "react";
import { Logo } from "./Logo";
import type { Role } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";
import { logoutAction } from "@/app/actions/auth";

export function AppShell({
  role,
  email,
  fullName,
  children,
}: {
  role: Role;
  email: string;
  fullName: string;
  children: React.ReactNode;
}) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#f4f7f6]">
      <div className="flex min-h-screen">
        <aside
          className={`fixed inset-y-0 left-0 z-30 w-64 transform bg-brand-green text-white transition-transform md:relative md:translate-x-0 ${
            navOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex h-full flex-col p-5">
            <div className="border-b border-white/15 pb-5">
              <Logo variant="white" size={26} />
              <p className="mt-2 text-[11px] italic text-white/60">You Are Definitely Covered</p>
            </div>

            <div className="mt-5 rounded-lg bg-white/10 px-3 py-2.5">
              <p className="text-[11px] uppercase tracking-wide text-white/60">Role</p>
              <p className="text-sm font-semibold">{ROLE_LABELS[role]}</p>
              <p className="mt-1 truncate text-xs text-white/70" title={fullName}>
                {fullName}
              </p>
              <p className="truncate text-[11px] text-white/50" title={email}>
                {email}
              </p>
            </div>

            <nav className="mt-5 flex-1 space-y-1 text-sm">
              <Link
                href="/app"
                className="block rounded-lg px-3 py-2 font-medium text-white/90 hover:bg-white/10"
              >
                Dashboard
              </Link>
            </nav>

            <form action={logoutAction}>
              <button
                type="submit"
                className="mt-4 w-full rounded-lg bg-brand-red px-3 py-2.5 text-sm font-bold tracking-wide text-white hover:bg-brand-red-dark"
              >
                Sign Out
              </button>
            </form>
          </div>
        </aside>

        {navOpen && (
          <button
            aria-label="Close navigation"
            className="fixed inset-0 z-20 bg-black/30 md:hidden"
            onClick={() => setNavOpen(false)}
          />
        )}

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="flex items-center gap-3 border-b-[3px] border-brand-red bg-white px-4 py-3 md:px-8">
            <button
              className="rounded-md border border-black/10 p-2 md:hidden"
              onClick={() => setNavOpen((v) => !v)}
              aria-label="Toggle navigation"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M4 6h16M4 12h16M4 18h16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
            <Logo size={20} />
          </header>

          <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
