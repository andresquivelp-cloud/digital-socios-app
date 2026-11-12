// Signed session cookie: base64url(payload) + "." + base64url(HMAC-SHA256(payload)).
// Used by middleware.js (to let a request through) and api/session.js (to issue it).

export const COOKIE = 'ds_session';
export const MAX_AGE = 60 * 60 * 24 * 7; // 7 days

const enc = new TextEncoder();
const b64url = (buf) => {
  let s = '';
  new Uint8Array(buf).forEach((b) => { s += String.fromCharCode(b); });
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};
const fromB64url = (str) => {
  const s = str.replace(/-/g, '+').replace(/_/g, '/');
  return atob(s + '==='.slice((s.length + 3) % 4));
};

async function hmac(secret, data) {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return b64url(await crypto.subtle.sign('HMAC', key, enc.encode(data)));
}

export async function sign(payload, secret) {
  const body = b64url(enc.encode(JSON.stringify(payload)));
  return body + '.' + (await hmac(secret, body));
}

export async function verify(token, secret) {
  if (!token || !secret || token.indexOf('.') < 0) return null;
  const [body, sig] = token.split('.');
  const want = await hmac(secret, body);
  if (want.length !== sig.length) return null;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= want.charCodeAt(i) ^ sig.charCodeAt(i);
  if (diff) return null;
  try {
    const p = JSON.parse(fromB64url(body));
    return p && p.x > Date.now() ? p : null;
  } catch (e) { return null; }
}

export function readCookie(request, name) {
  const raw = request.headers.get('cookie') || '';
  const hit = raw.split(';').map((c) => c.trim()).find((c) => c.startsWith(name + '='));
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : null;
}

export function allowed(email) {
  const e = String(email || '').toLowerCase();
  const domains = (process.env.ALLOWED_DOMAINS || 'digitalsocios.com').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
  const emails = (process.env.ALLOWED_EMAILS || '').split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
  return emails.includes(e) || domains.includes(e.split('@')[1]);
}
