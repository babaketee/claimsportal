"use server";

import { redirect } from "next/navigation";
import { DEMO_ACCOUNTS } from "@/lib/accounts";
import { getSession } from "@/lib/session";

export interface LoginState {
  error?: string;
}

export async function loginAction(_prev: LoginState, formData: FormData): Promise<LoginState> {
  const identifier = String(formData.get("identifier") ?? "").trim();
  const password = String(formData.get("password") ?? "").trim();

  if (!identifier || !password) {
    return { error: "Please fill in all fields." };
  }

  const account = DEMO_ACCOUNTS[identifier];
  if (!account || account.password !== password) {
    return { error: "Invalid email or password." };
  }

  const session = await getSession();
  session.authenticated = true;
  session.email = identifier;
  session.role = account.role;
  session.full_name = account.full_name;
  await session.save();

  redirect("/app");
}

export async function logoutAction() {
  const session = await getSession();
  session.destroy();
  redirect("/login");
}
