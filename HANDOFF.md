# HMS — Session Handoff / Resume Point

**Last updated:** 2026-07-16
**Repo:** `/Users/tatenda/hms` · GitHub: https://github.com/Tatendamarimo/hms (⚠️ currently PUBLIC — recommend making private)
**Model note:** project pins Fable 5 via `.claude/settings.json`.

## How to resume next session

Open Claude Code in `~/hms` and say: **"Start Slice 7 per TASKS.md"** (only
after Slice 6 architecture review is approved).
Source of truth = FRD v2 (`~/Desktop/Healthcare Management/…FRD v2.md`);
Phase 1 plan = `docs/phase1-technical-design.md`; conventions = `ARCHITECTURE.md`.

## Where things stand

- **Slice 6 (orders & printables) is DONE**: stabilized, tested, committed,
  pushed. 133 tests green on SQLite AND Postgres, ruff clean.
- Awaiting **architecture review approval** before Slice 7 begins (standing
  instruction: stop between slices).

### Slice 6 stabilization notes (2026-07-16)
- Migrations: pharmacy 0001, laboratory 0001, clinical 0002+0003,
  billing 0004 — reviewed, applied to dev DB.
- Fixes made during stabilization (all covered by tests):
  - laboratory tests: replaced `pytest_plugins` re-registration with a local
    conftest re-export (pytest collection error).
  - test settings: SQLite fallback was dead whenever repo `.env` existed —
    `DATABASE_URL_EXPLICIT` recorded before `read_env()`; Postgres tests now
    require an explicitly exported DATABASE_URL (CI unaffected).
  - `cancel_prescription` now row-locks (matches sign/cancel_lab_order
    pattern; double-cancel returns 409, no duplicate audit rows).
  - `create_lab_order` rejects duplicate services in one order
    (double-billing guard) — new test.
  - lab-order price-snapshot test used an invalid same-day ServicePrice;
    now future-dated.

## Slice roadmap (remaining Phase 1)
- **7 — Invoices & payments completion** ← next (after approval): manual
  invoice items, discounts (permission + reason), payment reversals, refunds.
- **8 — Cash-up & unpaid balances.**
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
