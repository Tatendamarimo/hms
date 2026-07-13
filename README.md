# HMS — Healthcare Management System

Production healthcare management system for outpatient clinics, built to the approved
**FRD v2** (see `docs/`). Walk-in-first clinical workflow: registration → queue → triage →
consultation → lab/pharmacy → billing.

## Stack

- **Backend:** Django 5 + Django REST Framework (modular monolith, apps per business domain)
- **Database:** PostgreSQL 16
- **Jobs:** Celery + Redis (SMS, PDFs, reports — never in request handlers)
- **Auth:** Django sessions (httpOnly cookies, CSRF), 30-min sliding idle timeout, account lockout
- **Frontend:** React + TypeScript + Vite + Tailwind + TanStack Query
- **Files (later phases):** private S3-compatible object storage, signed URLs

## Repository layout

```
backend/
  config/            # settings (base/dev/prod/test), celery, urls
  apps/
    core/            # base models, audit log + middleware, clinic scoping
    accounts/        # custom user, session auth API, role seeding
    clinics/         # tenancy: Clinic, ClinicMembership
frontend/
  src/
    api/             # fetch client (CSRF-aware) + query hooks
    features/auth/   # login, session
docs/                # ops runbooks (backup/restore)
scripts/             # backup.sh
```

## Local development

Prereqs: Python 3.12, Node 20+, Docker.

```bash
# 1. Infrastructure (Postgres on host port 5435, Redis on 6381)
docker compose up -d db redis

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env          # then edit values
python manage.py migrate
python manage.py seed_roles
python manage.py createsuperuser
python manage.py runserver          # http://localhost:8000

# 3. Worker (separate shell)
celery -A config worker -l info

# 4. Frontend (separate shell)
cd frontend
npm install
npm run dev                          # http://localhost:5173 (proxies /api to :8000)
```

Run tests: `cd backend && pytest`. Lint: `ruff check .`

API schema: `/api/v1/schema/` (OpenAPI), Swagger UI at `/api/v1/schema/swagger/`.

## Conventions (enforced, non-negotiable — FRD §7.1)

- Every business table: `created_at`, `updated_at`, `created_by`, `clinic` FK.
- Clinical/financial data is **soft-deleted only** (`void(by=…, reason=…)`). `.delete()` raises.
- Clinical records are append-only; amendments link via `amended_from` (Phase 1).
- All timestamps UTC. All querysets clinic-scoped via `ClinicScopedViewSetMixin`.
- Every mutation is audited automatically; clinical reads are audited via `AuditedReadMixin`.
- Raw SQL is banned. ORM only.

## Phase status

- [x] **Phase 0 — Foundations**: project setup, Docker, auth, multi-role, multi-clinic,
      base models, audit, CI, backups
- [ ] Phase 1 — Core clinical loop (patients, encounters, queue, vitals, consultations, billing)
- [ ] Phase 2 — Lab & pharmacy
- [ ] Phase 3 — Maternity, SMS, reports
- [ ] Phase 4 — Scale-out

### Pre-go-live hardening backlog (FRD §9, tracked, not Phase 0)

- Mandatory 2FA for Admin accounts (django-otp)
- PHI-scrubbed Sentry integration
- Column-level encryption evaluation for highest-sensitivity fields
