// Every page except the sign-in page, the API and the icons needs a valid session cookie.
// The finance data lives inside public/index.html, so it is never sent without one.
import { next } from '@vercel/functions';
import { COOKIE, verify, readCookie, allowed } from './lib/session.js';

export const config = {
  matcher: ['/((?!login|api/|favicon\\.png|apple-touch-icon\\.png|logo-192\\.png).*)'],
};

export default async function middleware(request) {
  const session = await verify(readCookie(request, COOKIE), process.env.SESSION_SECRET);
  if (session && allowed(session.e)) return next({ headers: { 'Cache-Control': 'private, no-store' } });
  return Response.redirect(new URL('/login', request.url), 307);
}
