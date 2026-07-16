# Changelog

All notable changes to HMS. Dates are UTC.

## [Unreleased] — Phase 1 in progress

### 2026-07-16 — Slice 6: Orders & printables
- Prescriptions (coded Medication FK or free-text item, DB check enforces one
  or the other): issue on the author's consultation (draft or signed) while
  the visit is open; cancel with mandatory reason under row lock
- Allergy guard: substring match of prescription items against documented
  allergies → 409 with details; prescribe-anyway requires explicit
  acknowledgement and writes a loud audit entry (FRD §5.3)
- Minimal Medication catalog (`apps.pharmacy`, no stock) with doctor picklist
- Lab/imaging orders (`apps.laboratory`): author-only, priced-services-only,
  price snapshotted per item; ordering appends linked invoice lines, cancel
  voids them with the reason (refunds arrive with slice 7 reversals);
  duplicate service in one order rejected (double-billing guard)
- Sick notes (date-range validated) and referral letters
- Print views under `/print/` (session + role + clinic gated, server-rendered):
  prescription, sick note, referral, lab request, registration (demographics
  only), invoice, receipt; clinical prints are read-audited
- `InvoiceItem.lab_order` source link; `add_service_line` accepts the link
- Fixed: test settings' SQLite fallback was dead code whenever a repo `.env`
  existed (read_env exports DATABASE_URL into os.environ) — Postgres now only
  used when DATABASE_URL is exported explicitly (CI/manual)

### 2026-07-14 — Slice 5: Consultations, ICD-10, break-glass
- Consultation lifecycle: draft (claim-holder only) → sign (row-locked,
  content required, author only) → versioned amendments with mandatory reason;
  OneToOne amended_from chain makes double-amendment impossible at the DB
- Signed consultations immutable at the model layer; void = retraction only
- **ADR-0002:** signing never mutates the invoice — consult fees originate at
  check-in (regression-tested)
- ICD-10 diagnosis catalog (bundled ~46-code primary-care subset,
  seed_diagnoses, expandable by data file swap); coded and/or free-text
  diagnoses per consultation, draft-only editing with audited removals
- Break-glass: Admin-only, reason-mandatory, patient-scoped, read-only,
  15-min session grants; BREAK_GLASS audit action; all reads under a grant
  flagged; wired into summary/timeline/vitals/consultation reads
- Consultation reads audited for doctors too

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
