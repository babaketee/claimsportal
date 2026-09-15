import "server-only";
import { cookies } from "next/headers";
import { getIronSession, type SessionOptions } from "iron-session";
import type { Role } from "./types";

export interface SessionData {
  authenticated: boolean;
  email: string;
  role: Role;
  full_name: string;
}

const secret = process.env.SESSION_SECRET ?? "dev-only-insecure-secret-change-me-32chars!!";

export const sessionOptions: SessionOptions = {
  password: secret,
  cookieName: "da_claims_session",
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 8, // 8 hours
  },
};

export async function getSession() {
  return getIronSession<SessionData>(cookies(), sessionOptions);
}

export async function requireSession(): Promise<SessionData> {
  const session = await getSession();
  if (!session.authenticated) {
    throw new Error("UNAUTHENTICATED");
  }
  return session;
}
