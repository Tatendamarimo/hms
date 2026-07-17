# ADR-0003: Refunds are recorded as full payment reversals

**Date:** 2026-07-16
**Status:** Proposed (Slice 7 design review)
**Refines:** Phase 1 Technical Design §2.5 (Payment: `reversal_of` self-FK,
"reversal = negative-effect row with reason"); FRD §5.7

## Context

The slice roadmap names "payment reversals, refunds" but neither the FRD nor
the Phase 1 design defines a refund record. Two money-out scenarios exist:

1. **Mistaken entry** — cashier recorded a payment that didn't happen or keyed
   the wrong amount/method.
2. **Genuine refund** — money returned to the patient, typically the surplus
   created when paid-for lines are voided (e.g. a cancelled lab order,
   documented in Slice 6).

A dedicated Refund model would be a second money ledger with its own numbering,
cash-up interaction, and reconciliation rules — none of which the FRD asks for.
Partial reversals would break the one-to-one `reversal_of` link and force
amount-level bookkeeping on top of the append-only payment log.

## Decision

Both scenarios are recorded the same way: a **full reversal row** against the
original payment.

- A reversal is a `Payment` row with `reversal_of` set, `amount` equal to the
  original (stored positive; derived totals *exclude* both the reversed
  payment and the reversal row), same method, its own REC- receipt number,
  `received_by` = the reversing cashier.
- The one-to-one `reversal_of` makes double reversal impossible at the DB;
  a reversal row itself can never be reversed (service rule).
- A reason is mandatory and written as an explicit high-visibility AuditLog
  entry alongside the automatic model-diff audit.
- **Partial refunds are not supported.** Returning part of a payment =
  reverse the original in full, then record a new payment for the correct
  amount — two rows, each receipted, nothing edited.

## Consequences

- The payment log stays strictly append-only; cash-up (Slice 8) reconciles
  from one ledger.
- The desk workflow for a partial refund is two steps. Acceptable at pilot
  scale; revisit only if cash-up data shows it causing real friction.
- Reversal receipts are printable like any payment receipt, so the patient
  leaves with paper for the money returned.
- Invoice `status` stays fully derived: reversing payments can move an
  invoice from `paid` back to `part_paid`/`unpaid` with no stored state to
  migrate.
