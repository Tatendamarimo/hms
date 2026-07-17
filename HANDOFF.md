# HMS — Session Handoff / Resume Point

**Last updated:** 2026-07-17
**Repo:** `/Users/tatenda/hms` · GitHub: https://github.com/Tatendamarimo/hms (⚠️ currently PUBLIC — recommend making private)
**Model note:** project pins Fable 5 via `.claude/settings.json`.

## How to resume next session

Open Claude Code in `~/hms` and say: **"Start Slice 8 per TASKS.md"** (only
after the Slice 7 architecture review is approved).
Source of truth = FRD v2 (`~/Desktop/Healthcare Management/…FRD v2.md`);
Phase 1 plan = `docs/phase1-technical-design.md`; conventions = `ARCHITECTURE.md`.

## Where things stand

- **Slice 7 (invoices & payments completion) is DONE**: manual catalog lines,
  Admin-only discounts (`billing.apply_discount` + reason + loud audit + DB
  check constraints), Admin line voiding, full payment reversals per
  **ADR-0003** (`billing.reverse_payment`, reversal-aware receipt print).
  160 tests green on SQLite AND Postgres, ruff clean. Migration billing 0005
  reviewed and applied to dev DB.
- Awaiting **architecture review approval** before Slice 8 begins (standing
  instruction: stop between slices).

### Slice 7 wrap-up notes (2026-07-17)
- Resumed from an uncommitted working tree: implementation + tests were in
  place but 5 discount tests failed 403 — `InvoiceItemCreateView.role_map`
  only allowed the till roles, so Admin (the only seeded holder of
  `apply_discount`) never reached the service check. Fixed by adding ADMIN
  to the role gate; the named permission stays the discount gate.
- `discount_reason` made non-null (`default=""`, house style / ruff DJ001);
  check constraints compare against `""` — migration 0005 regenerated before
  first application.
- ADR-0003 status is **Proposed** — flip to Accepted at review.

## Slice roadmap (remaining Phase 1)
- **8 — Cash-up & unpaid balances** ← next (after approval).
- **9 — Frontend** (queue → registration → visit workspace → billing, 4 sub-PRs).
- **10 — Hardening** (permission-matrix walk, E2E flow, seeds).

## Open items / decisions pending clinic input
- Make GitHub repo private (recommended, before any pilot deployment).
- ICD-10 subset (46 codes) — clinician review before production use.
- Confirm 4 clinical assumptions from Slice 5 (esp. author-only amendment).
- Cross-phase backlog: Admin 2FA, Sentry PHI-scrubbing, column encryption (README).
- Known tech debt (Slice 6): no DB-level unique on LabOrderItem
  (lab_order, service_item) — guarded in service only; LabOrderItem.price and
  its InvoiceItem.unit_price call current_price() separately (could diverge
  only if a price row landed mid-request; same-day duplicates are blocked).

## Environment quick-ref
- Postgres (docker): host port **5435**; Redis **6381**. `docker compose up -d db redis`.
- Backend venv: `~/hms/backend/.venv`. Tests default to SQLite; Postgres run:
  `DATABASE_URL=postgres://hms:hms@localhost:5435/hms .venv/bin/python -m pytest`.
- Run server: `.venv/bin/python manage.py runserver` (needs repo-root `.env`).
