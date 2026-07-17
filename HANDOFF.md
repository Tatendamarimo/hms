# HMS — Session Handoff / Resume Point

**Last updated:** 2026-07-17
**Repo:** `/Users/tatenda/hms` · GitHub: https://github.com/Tatendamarimo/hms (⚠️ currently PUBLIC — recommend making private)
**Model note:** project pins Fable 5 via `.claude/settings.json`.

## How to resume next session

Open Claude Code in `~/hms` and say: **"Start Slice 9 per TASKS.md"** (only
after the Slice 8 architecture review is approved).
Source of truth = FRD v2 (`~/Desktop/Healthcare Management/…FRD v2.md`);
Phase 1 plan = `docs/phase1-technical-design.md`; conventions = `ARCHITECTURE.md`.

## Where things stand

- **Slice 8 (cash-up & unpaid balances) is DONE**: `CashUp` per cashier
  (expected vs counted, variance needs notes — service rule + DB constraint),
  atomic count-and-close that stamps the covered cash payments, computed
  drawer preview (`GET /billing/cashup/`), per-patient unpaid balances view
  (`GET /billing/unpaid/`, Cashier/Admin, DB-aggregated, most-owed first).
  181 tests green on SQLite AND Postgres, ruff clean. Migration billing 0006
  reviewed and applied to dev DB. ADR-0003 flipped to Accepted.
- Awaiting **architecture review approval** before Slice 9 begins (standing
  instruction: stop between slices).

### Slice 8 design notes for the review (2026-07-17)
- **No open CashUp row**: the design's `status open/closed` enum is kept on
  the model, but rows are only created closed — the "open drawer" is defined
  as the cashier's cash payments with `cash_up IS NULL`, which makes the
  period definition race-free (close row-locks exactly those payments;
  a concurrent second close finds nothing and 400s).
- **Reversals count negative** in the drawer; a cross-period refund can make
  `expected_total` negative (counted stays ≥ 0, variance explained in notes).
- **Close of an empty drawer is rejected** (400) — nothing to reconcile;
  EcoCash/card payments never enter a drawer or get stamped.
- **Unpaid view has no encounter-status filter** (FRD doesn't specify one);
  each invoice row carries `encounter_status` so the frontend can separate
  walked-out debt from in-progress visits.
- Cash-up is strictly per (clinic, cashier, received_by) — a receptionist who
  takes cash needs the Cashier role to cash up their own drawer (route table
  gates `billing/cashup/` to Cashier; FRD notes the roles may be one person).

## Slice roadmap (remaining Phase 1)
- **9 — Frontend** ← next (after approval): queue → registration → visit
  workspace → billing, 4 sub-PRs. Only the auth shell exists so far.
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
