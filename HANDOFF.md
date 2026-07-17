# HMS — Session Handoff / Resume Point

**Last updated:** 2026-07-17
**Repo:** `/Users/tatenda/hms` · GitHub: https://github.com/Tatendamarimo/hms (⚠️ currently PUBLIC — recommend making private)
**Model note:** project pins Fable 5 via `.claude/settings.json`.

## How to resume next session

Open Claude Code in `~/hms` and say: **"Start Slice 10 per TASKS.md"** (only
after the Slice 9 architecture review is approved).
Source of truth = FRD v2 (`~/Desktop/Healthcare Management/…FRD v2.md`);
Phase 1 plan = `docs/phase1-technical-design.md`; conventions = `ARCHITECTURE.md`.

## Where things stand

- **Slice 9 (frontend) is DONE** in four sub-PR commits: 9.1 queue +
  check-in, 9.2 search-first registration + profile, 9.3 visit workspace
  (allergy banner, vitals, consultation editor with allergy-guard flow,
  invoice panel), 9.4 cash-up + unpaid screens. Backend untouched
  (181 tests still green), `tsc -b && vite build` clean.
- **E2E-verified** against the dev servers as four role sessions (script:
  register → dedupe 409 → check-in with fee → payment-first gate → pay →
  triage → flagged vitals → claim → draft → ICD-10 → allergy-guard 409 →
  acknowledged prescribe → lab order → sign → settle → cash-up → unpaid;
  print views render through the dev proxy).
- Awaiting **architecture review approval** before Slice 10 (standing
  instruction: stop between slices).

### Slice 9 notes (2026-07-17)
- Router list endpoints are cursor-paginated; action/APIView lists are plain
  arrays → `api.list()` in the client handles both (catalog, lab orders).
- `ApiError.body` carries the DRF error payload: field errors inline in
  forms, duplicate-409 candidates, allergy-guard 409 acknowledgement flow.
- Vite dev proxy forwards `/print` as well as `/api`.
- Dev demo data seeder lives in the session scratchpad only (not committed):
  clinic DEMO, users rec.demo/nurse.demo/dr.demo/cash.demo/admin.demo
  (password `demo-pass-123`), priced catalog. Recreate ad hoc if needed —
  Slice 10's "seeds" item should productize this.
- UI reasons (LWBS, void, reversal, amend, cancel) use window.prompt —
  functional, not pretty; acceptable for pilot, revisit if feedback demands.

## Slice roadmap (remaining Phase 1)
- **10 — Hardening** ← next (after approval): permission-matrix walk,
  E2E flow test (port the verification script into the test suite),
  seed data polish.

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
