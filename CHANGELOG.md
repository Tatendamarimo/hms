# Changelog

All notable changes to HMS. Dates are UTC.

## [Unreleased] — Phase 1 in progress

### 2026-07-18 — Slice 10 PR1: Design system, app shell, white-label
- White-label branding per tenant in `clinic.settings` (logo/favicon URLs,
  primary/secondary colors, tagline; defaults in code, overrides merged,
  unknown keys dropped). Public `GET /clinics/branding/` for the login page
  (single active clinic → its identity; else neutral defaults). `/auth/me/`
  clinics carry branding; print headers show the logo + primary color
- ThemeProvider maps branding → CSS custom properties (derived hover/light
  shades), document title, favicon; active clinic wins after login
- Design system under `src/ui/components/`: Button, Input, Select, Card,
  Table, Modal (portal/focus-trap/Escape), Drawer, ReasonModal (wired to
  screens in PR3), Alert, Toast, Badge, Tabs, Pagination, Breadcrumbs,
  Spinner, Loading/Empty/Error states — themed via `design-tokens.css`
- Application shell: fixed sidebar with grouped role-aware nav (mobile
  drawer), header with clinic switcher/notifications/user menu,
  breadcrumbs; branded login page
- Frontend test harness (vitest + Testing Library), 12 component tests;
  7 new backend branding tests (188 total, both DBs)

### 2026-07-17 — Slice 9: Frontend (4 sub-PRs)
- **9.1 Queue**: /queue polling at 10s with invoice status/balance per row;
  role-aware actions (Nurse triage, Doctor claim, Reception LWBS-with-reason);
  search-first check-in dialog with optional priced consultation fee;
  role-filtered nav + landing
- **9.2 Patients**: search-first registration (form opens only after a
  search), duplicate-409 candidates with open-instead links before the
  audited create-anyway, mandatory consent; profile with receptionist edit
  (DRF field errors inline), clinical-only visit timeline, print-registration
- **9.3 Visit workspace**: /visit/:id per-role panels — always-on allergy
  banner + chronic conditions (clinical); nurse vitals with flag highlighting
  (applied ranges shown); doctor consultation editor (draft/sign/amend,
  ICD-10 search + free text, prescriptions with allergy-guard 409 →
  per-allergy acknowledgement, sick notes, referrals, lab/imaging orders
  that bill the invoice); desk invoice panel (add service, Admin
  discount/void, record payment, reverse); print buttons throughout
- **9.4 Billing screens**: /billing/cashup drawer preview + count-and-close
  with live variance hint; /billing/unpaid per-patient balances
- Client: ApiError carries the DRF error body (field errors, 409 payloads);
  api.list() handles cursor-paginated router lists; /print proxied in dev
- Verified end-to-end against the dev server as four role sessions
  (register → … → cash-up), print views included

### 2026-07-17 — Slice 8: Cash-up & unpaid balances
- `CashUp` per cashier (FRD §5.7): expected vs counted, variance derived,
  variance ≠ 0 requires notes (service rule + DB check constraint). Append-only
  like `Payment` — a wrong count is explained in notes, never edited
- The "open drawer" is the cashier's cash payments not yet stamped with a
  `cash_up` FK — no open row accumulates state. `GET /billing/cashup/` returns
  a computed preview (expected total, payment list, period); `POST` counts and
  closes in one atomic step (row born closed, covered payments row-locked then
  stamped one by one so each stamp hits the audit trail). Cashier-only
- Reversal rows count **negative** in the drawer (cash handed back), so a
  same-period reverse nets to zero and a cross-period refund can leave a
  negative expected total — reconciling from the one payment ledger (ADR-0003)
- Non-cash payments (EcoCash/card) never enter a drawer and are never stamped
- `GET /billing/unpaid/` (Cashier, Admin): per-patient outstanding from derived
  invoice status, aggregated in the database (voided lines excluded, reversed
  pairs cancel), most-owed first; rows carry encounter status so the desk can
  tell walked-out debt from an in-progress visit. Desk-tier fields only
- ADR-0003 status flipped Proposed → Accepted (slice 7 review)

### 2026-07-17 — Slice 7: Invoices & payments completion
- Desk-added catalog lines (`POST /invoices/<id>/items/`): till roles + Admin,
  price snapshotted at entry, quantity multiplies, inactive / unpriced /
  foreign-clinic services rejected; invoice row-locked like payments
- Discounts: negative `InvoiceItem` gated by the named `billing.apply_discount`
  permission (seeded **Admin-only** — fraud surface; a trusting clinic grants
  it explicitly), mandatory structured reason, loud audit entry; DB check
  constraints keep discount lines negative/sourceless/reasoned and service
  lines non-negative/unreasoned; cannot exceed the total or undercut what is
  already paid
- Line voiding (Admin, mandatory reason): desk lines only — lab lines are
  retracted by cancelling the order; blocked if it would leave the invoice
  below its paid total
- **ADR-0003:** refunds are full payment reversals — a reversal is a `Payment`
  row (`reversal_of` one-to-one, own REC- number, same method) excluded with
  its original from derived totals; partial refund = full reverse + re-record;
  reversals need `billing.reverse_payment` (Cashier/Admin) + reason + loud
  audit; a reversal can't be reversed, double reversal is a 409
- Reversal-aware receipt print (shows the reversed receipt number and
  "Amount returned")
- ADR-0002 addendum: `InvoiceItem` has no `consultation` FK in Phase 1
  (design §2.5 text predates the ADR); source links are `lab_order` only

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
