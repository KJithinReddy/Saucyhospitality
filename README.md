# Saucy Hospitality

An end-to-end restaurant maintenance marketplace prototype: report an issue, receive an AI-assisted triage, match a qualified contractor, and track the repair through restaurant confirmation.

## Stack

- `frontend/`: Next.js 16, TypeScript, Tailwind CSS
- `backend/`: FastAPI, SQLAlchemy, SQLite
- AI: OpenRouter free model router (`openrouter/free`) with conservative deterministic fallback

## Run locally

Copy `.env.example` values to `backend/.env` and `frontend/.env.local`. An OpenRouter key is optional: without one, the full demo uses the fallback assessment path.

```bash
# Terminal 1
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/restaurant`.

## Demo script

1. On the Restaurant dashboard select **Report an issue**.
2. Keep the supplied walk-in refrigerator description or add a photo and submit.
3. Review the advisory AI assessment and contractor matches.
4. Use the role switcher to select **Contractor**, then accept the matching job.
5. Advance it through **En route**, **Start repair**, and **Mark repair complete**.
6. Switch back to Restaurant and select **Confirm repair complete**.

## Deploy

Deploy `backend/` as a Railway service. Add a persistent volume mounted to `/app/backend/runtime`, set Railway variables from `.env.example`, then generate a public domain.

Deploy `frontend/` to Vercel and set `NEXT_PUBLIC_API_URL` to the Railway API domain. Update the backend `CORS_ORIGINS` to the Vercel production URL.

## Verification

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q
cd frontend && npm run build
```

## Boundaries

This is a demo prototype. Identity, contractor availability, ETA, and service area are seeded. Video is stored for technician evidence but not analyzed. AI output is advisory and an onsite technician must verify every diagnosis.
