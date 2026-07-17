# ADR-0002: The consultation fee is billed at check-in, never at sign

**Date:** 2026-07-14
**Status:** Accepted
**Amends:** Phase 1 Technical Design §2.4 ("Signing … appends the consultation
invoice line")

## Context

The original design had consultation signing append the consultation fee line
to the invoice. That design predates decision Q2 (payment-first is the pilot
default). Under payment-first, the fee line is created at check-in so the desk
can collect before triage — sign-time billing would create a **second**
consultation line on the same invoice.

The alternatives — deduplicating at sign time ("add the line only if absent")
or letting the doctor pick a billable service at sign — either hide billing
logic inside a clinical action or put price-list decisions in the doctor's
workflow, both of which violate the separation the design fights for.

## Decision

Signing a consultation NEVER mutates the invoice. Its only cross-app side
effect is the encounter transition (`in_consultation → awaiting_payment`,
taken through the encounter state machine, and only when the encounter is
currently in consultation — signing an amendment later never moves a visit).

Consultation fees originate at **check-in** in both billing modes:
payment-first clinics require `checkin_service` (enforced since Slice 3);
pay-after clinics may pass the same field, and any additional services are
added as manual invoice lines by the desk (Slice 7).

## Consequences

- No double-billing path exists; a regression test asserts sign touches no
  billing rows.
- Clinical actions and billing actions stay in separate domains; doctors
  never handle prices (FRD §3).
- Slice 7's scope shrinks slightly (no sign-time billing hook to build).
- If a clinic ever wants consult fees derived from the consultation itself
  (e.g. tiered by length), that becomes an explicit billing feature, not a
  side effect of signing.
- *(Addendum, 2026-07-16, Slice 7 design)* The design §2.5 source-link text
  ("exactly one of consultation / lab_order") predates this ADR: since no code
  path ever creates an invoice line **from** a consultation, `InvoiceItem`
  never grew a `consultation` FK. Phase 1 source links are `lab_order` only;
  the dispense link arrives with Phase 2 pharmacy.
