// POST { credential } — a Google ID token from the sign-in button.
// Checks it with Google, checks the email domain, then sets the session cookie.
import { COOKIE, MAX_AGE, sign, allowed } from '../lib/session.js';

const json = (status, body, headers = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...headers } });

export async function POST(request) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const secret = process.env.SESSION_SECRET;
  if (!clientId || !secret) return json(503, { error: 'Sign-in is not set up yet.' });

  let credential = '';
  try { credential = (await request.json()).credential || ''; } catch (e) {}
  if (!credential) return json(400, { error: 'Missing sign-in token.' });

  const r = await fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(credential));
  if (!r.ok) return json(401, { error: 'Google could not confirm this sign-in.' });
  const t = await r.json();

  const issuerOk = t.iss === 'accounts.google.com' || t.iss === 'https://accounts.google.com';
  const verified = t.email_verified === true || t.email_verified === 'true';
  if (t.aud !== clientId || !issuerOk || !verified || Number(t.exp) * 1000 < Date.now()) {
    return json(401, { error: 'Google could not confirm this sign-in.' });
  }
  if (!allowed(t.email)) return json(403, { error: 'Only Digital Socios accounts can open this app.' });

  const token = await sign({ e: String(t.email).toLowerCase(), n: t.name || '', x: Date.now() + MAX_AGE * 1000 }, secret);
  return json(200, { ok: true }, { 'Set-Cookie': `${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}` });
}
