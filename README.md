# Scoreboard

Lightweight Valorant match follower with live notifications.

## Local Run (Recommended)

This project uses a local API server for development (to avoid Vercel CLI routing issues).

### 1) Install
```
npm install
```

### 2) Configure `.env`
Create `.env` in the repo root (already present) and set:
- `DATABASE_URL`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `VITE_FCM_VAPID_KEY`
- `VITE_FIREBASE_*` variables

Example (password may need URL encoding):
```
DATABASE_URL="postgresql://postgres:ENCODED_PASSWORD@db.your-project.supabase.co:5432/postgres"
```

If your DB password contains special characters (`?`, `&`, `#`, `@`, `:`), URL-encode them.

### 3) Run API + Frontend
Terminal A (API):
```
npm run dev:api
```

Terminal B (Frontend):
```
npm run dev
```

Open the Vite URL (usually `http://localhost:5173` or `http://localhost:5174`).

### 4) Health Check
```
http://localhost:3000/api/health
```
Expected response:
```
{ "ok": true }
```

## Tests
```
npm run typecheck
npm test
```

## Env Notes

Required:
- `DATABASE_URL` (Postgres connection string)
- `FIREBASE_SERVICE_ACCOUNT_JSON` (one-line JSON string)
- `VITE_FCM_VAPID_KEY`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_MEASUREMENT_ID`

## Deployment (Vercel)
This project is set up for Vercel with `/api` serverless functions.
If you later deploy:
1. Import repo into Vercel.
2. Set Root Directory to repo root (`.`).
3. Add the environment variables above in Vercel Settings.
4. Deploy.
