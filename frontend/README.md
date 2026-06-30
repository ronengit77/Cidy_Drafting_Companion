# CIdy Drafting Companion — Frontend

A React + Vite + TypeScript single-page app for drafting UN funding artifacts (RPTC
activity proposals, DA concept notes). It talks to the CIdy backend API and provides
the full drafting loop: passwordless sign-in → dashboard → a schema-driven form editor
→ save with optimistic versioning → validation → AI assist (shape a field, coherence
review, SDG-target suggestion) → preview.

Design: a refined institutional aesthetic — IBM Plex type, ink-on-parchment palette,
restrained brass accent.

## Run it locally

1. **Start the backend** (from the repo's `backend/` dir, with Postgres running):
   ```bash
   # dev mode returns the magic-link directly (no email needed); export the key for AI assist
   export OPENAI_API_KEY=...        # optional; AI buttons return 503 gracefully without it
   export CIDY_DEV_MODE=true
   python -m uvicorn cidy_api.app:create_app --factory --port 8000
   ```
   The API allows the dev frontend origin (`http://localhost:5173`) via CORS by default
   (`CIDY_CORS_ORIGINS`).

2. **Start the frontend** (from `frontend/`):
   ```bash
   npm install
   npm run dev          # http://localhost:5173
   ```

3. Open http://localhost:5173, enter any email, and click **Enter →** (dev shortcut).

## Configuration

- `VITE_API_BASE_URL` — backend base URL (default `http://localhost:8000`). Set this in a
  `frontend/.env` for a deployed backend.

## Scripts

- `npm run dev` — dev server with HMR
- `npm run build` — type-check + production build to `dist/`
- `npm run preview` — preview the production build

## Notes

- The AI-assist features require the backend to have a funded `OPENAI_API_KEY`. Without
  quota the API returns `503` and the UI shows a non-blocking error — drafting,
  validation, and preview keep working.
- Build output (`dist/`) deploys as static files (e.g. S3 + CloudFront).
