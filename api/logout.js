import { COOKIE } from '../lib/session.js';

export function GET(request) {
  return new Response(null, {
    status: 302,
    headers: { Location: new URL('/login', request.url).toString(), 'Set-Cookie': `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`, 'Cache-Control': 'no-store' },
  });
}
