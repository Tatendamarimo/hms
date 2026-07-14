# Changelog

All notable changes to HMS. Dates are UTC.

## [Unreleased] — Phase 1 in progress

### 2026-07-14 — Slice 4: Triage vitals
- Vitals recorded against encounters (never patients) by nurses only
- Server-side plausibility validation (typo-rejection) distinct from
  abnormal-value flagging against clinic-configurable reference ranges
- **ADR-0001:** applied ranges + flags snapshotted per record; threshold
  changes never re-colour history
- Auto-advance in_triage → awaiting_doctor via the state machine, under row lock
- Vitals reads audited; void-with-reason corrections

### 2026-07-14 — Slice 3: Encounters & state machine
- Encounter lifecycle with role-gated, guarded transitions under row lock;
  double-claim returns 409; LWBS requires an audited reason
- Live queue API (emergencies first, clinic-scoped)
- Payment-first check-in (pilot default): fee line at check-in, triage gated
  on settlement; partial payments hold the gate
- Resequenced minimal Invoice/InvoiceItem/Payment (+ no-overpay, price
  snapshotting, INV-/REC- yearly numbering) forward from slice 7
- close_with_balance permission (Cashier/Admin) with mandatory reason
- Read-audited patient timeline

### 2026-07-13 — Slice 2: Patient registry
- Patients with transactional MRN issue, DOB (never age), consent capture
- Duplicate check (national ID/phone): 409 + audited create_anyway override
- Allergies & chronic conditions: add / void-with-reason, clinical summary banner
- Search-first registration endpoint; role boundaries tested

### 2026-07-13 — Slice 1: Billing foundations
- ClinicCounter (row-locked sequences), ServiceItem + append-only ServicePrice
- Declarative RolePermission (deny-by-default, no superuser bypass)
- seed_catalog command (services without prices — prices are clinic data)

### 2026-07-13 — Phase 0: Foundations
- Django 5 + DRF modular monolith; split settings; Celery wiring
- Session auth (httpOnly, 30-min sliding timeout), axes lockout, CSRF
- Multi-role groups (7 FRD roles), Clinic + membership tenancy
- Base models: timestamps, soft delete (void), clinic scoping
- AuditLog + actor-context middleware + signal diffs; login/logout auditing
- React + TS + Tailwind + TanStack Query shell with session auth
- Docker compose (Postgres 5435 / Redis 6381), CI (ruff + pytest on Postgres
  + migration completeness), backup script + restore runbook
