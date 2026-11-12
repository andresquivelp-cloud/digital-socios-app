// Public sign-in settings for the login page (no secrets here).
export function GET() {
  return new Response(JSON.stringify({ clientId: process.env.GOOGLE_CLIENT_ID || '', domain: ((process.env.ALLOWED_EMAILS || '').split(',')[0].split('@')[1] || 'digitalsocios.com').trim() }), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}
