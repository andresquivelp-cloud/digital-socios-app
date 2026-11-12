# Digital Socios app

Finances (P&L), Budget and Accounts for Digital Socios, built from Monarch. Served at app.digitalsocios.com.

## How it works
- `public/index.html` is the whole app: one self-contained page with the Monarch data inside it.
- `middleware.js` blocks every page until the visitor signs in with Google. Only the Google accounts listed in `ALLOWED_EMAILS` get in (right now just andres@digitalsocios.com). `ALLOWED_DOMAINS` can open it to a whole domain later; it is set to `none`.
- `api/session.js` checks the Google sign-in with Google and sets a signed cookie for 7 days. `api/logout.js` clears it.

## Environment variables (Vercel)
| Key | What |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth client ID (Web) from Google Cloud, with `https://app.digitalsocios.com` as an authorized JavaScript origin |
| `SESSION_SECRET` | Long random string that signs the session cookie |
| `ALLOWED_EMAILS` | `andres@digitalsocios.com` (comma separated to add people) |
| `ALLOWED_DOMAINS` | `none` (or a domain like `digitalsocios.com` to let the whole team in) |

## Refreshing the numbers
1. Replace `app/data/monarch-2026.json` with a fresh Monarch export.
2. Run `python3 app/build.py` (writes `public/index.html`).
3. Commit and push. Vercel deploys on push.
