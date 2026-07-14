# Phase 1 Task Board

Work breakdown per `docs/phase1-technical-design.md` §7. A slice is *done* only
when its tests are green on SQLite + Postgres, lint passes, and it is committed.

| # | Slice | Status | Notes |
|---|-------|--------|-------|
| 1 | Billing foundations (counters, catalog, versioned prices) | ✅ done | |
| 2 | Patient registry (MRN, dedupe, consent, allergies) | ✅ done | |
| 3 | Encounters (state machine, queue, clinic settings) | ✅ done | Resequenced: minimal Invoice/Payment pulled forward from slice 7 (Q2 payment-first) |
| 4 | Vitals (flagging, range snapshot, auto-transition) | ✅ done | ADR-0001 |
| 5 | Consultations (draft/sign/amend, diagnoses, break-glass) | ⏳ next — awaiting approval | ICD-10 seed command included |
| 6 | Orders & printables (prescriptions, allergy guard, Medication/LabOrder minimal, print views) | ▢ | |
| 7 | Invoices & payments completion (manual items, discounts, reversals) | ▢ | Reduced scope after resequencing |
| 8 | Cash-up & unpaid balances | ▢ | |
| 9 | Frontend (queue → registration → visit workspace → billing) | ▢ | 4 sub-PRs |
| 10 | Hardening (permission-matrix walk, E2E flow test, seeds) | ▢ | |

Cross-phase backlog (not Phase 1): Admin 2FA, Sentry PHI-scrubbing, column
encryption evaluation (see README), appointments + clinic-favourite diagnoses
(Phase 3, decisions Q1/Q3).
