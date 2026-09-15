import { NextRequest, NextResponse } from "next/server";

// Fast pre-check only — redirects unauthenticated requests away from /app.
// The authoritative check (session decrypt + role) happens server-side in
// app/app/layout.tsx via requireSession().
export function middleware(req: NextRequest) {
  const hasSession = req.cookies.has("da_claims_session");
  const { pathname } = req.nextUrl;

  if (pathname.startsWith("/app") && !hasSession) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*"],
};
