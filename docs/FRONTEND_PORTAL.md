# Frontend Portal

## Overview

`frontend/` is the first-phase Next.js portal for the current FastAPI backend.

- Login: exchanges `X-API-Key` for a server-issued bearer session token, then stores the validated session locally
- Chat: calls `POST /api/v1/ai/chat`
- Inquiry: calls `GET /api/v1/knowledge/concepts` and `/search`
- Analysis: uses `GET /api/v1/ai/traces` and the per-request trace detail APIs
- Admin: uses concept, alias, relation, agent mapping, concept API mapping, agent catalog, and API catalog management APIs

## Local Run

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Default local URL:

- `http://localhost:13000` through Docker Compose
- `http://localhost:3000` when running `npm run dev` directly

## Docker Compose

`docker-compose.yml` now includes a `frontend` service.

- Port: `13000:3000`
- Backend base URL: `http://localhost:18000`

## Phase 1 Screen Map

- `/login`
- `/dashboard`
- `/ai/chat`
- `/inquiry/concepts`
- `/analysis/traces`
- `/admin/concepts`
- `/admin/aliases`
- `/admin/relations`
- `/admin/agent-mappings`
- `/admin/concept-api-mappings`
- `/admin/agents`
- `/admin/apis`

## Auth Flow

- `POST /api/v1/auth/login`: validates `X-API-Key` and returns the server-derived role plus a signed bearer token
- `GET /api/v1/auth/me`: re-validates the current bearer token on protected screens and refreshes session data
- The frontend no longer trusts a user-selected role value during login
- Normal portal API calls use `Authorization: Bearer <token>` after login
- Session TTL: 30 minutes (`SESSION_TTL_SECONDS=1800`)
- On invalid or expired session: clear local session and redirect to `/login?reason=expired`
- `SESSION_SECRET` must be overridden with a strong environment value outside local development

## Phase 2 Backend Gaps

The current backend is enough for chat, concept inquiry, concept/alias/relation create/update/delete, agent mapping create/update/delete, concept API mapping create/update/delete, agent catalog create/update/delete, API catalog create/update/delete, and trace list/detail lookup. These items still need API work before the admin portal becomes full CRUD:

- full JWT/OAuth2 or server-side revocation store if stronger enterprise auth is required
- mapping integrity guards before deleting referenced agents or APIs
