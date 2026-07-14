# Phase 1 Technical Design — Core Clinical Loop

**Status:** Draft for approval — no Phase 1 code until this is signed off
**FRD basis:** FRD v2 §2.1, §4, §5.1–5.3, §5.7, §6, §7, §10 (Phase 1)
**Foundation:** Phase 0 (sessions, roles, tenancy, base models, audit) — complete

---

## 1. Scope

**In:** patient registry (MRN, search, dedupe check, consent, allergies, chronic
conditions), Encounter + live queue, triage vitals with abnormal flagging,
doctor consultation (draft → sign → amend), diagnoses (coded + free text),
prescriptions (print), lab/imaging orders (create + print only), service catalog
+ versioned price list, invoices with linked lines, payments (partial, multi-method),
discounts/write-offs, cash-up, unpaid balances, printable forms, break-glass
clinical access for Admin, clinical read auditing.

**Out (explicitly):** lab results workflow (Phase 2), dispensing/stock (Phase 2),
patient merge tool (Phase 2), maternity (Phase 3), SMS (Phase 3), reports (Phase 3),
appointments (see Open Question Q1), medical-aid claims (Phase 4).

Two entities are created in Phase 1 in **minimal form** because Phase 1 features
need rows to reference, and free-text would violate FRD "mistake #5" (no catalogs):

| Entity | Phase 1 form | Phase 2 extends with |
|---|---|---|
| `Medication` | id, name, form, strength, is_active — a picklist, no stock | batches, ledger, prices |
| `LabOrder` | ordered items + status `ordered`/`cancelled`, printable request | sample tracking, results, verification |

---

## 2. Domain Model

All models: `TimeStampedModel + ClinicScopedModel + AuditedModel`; clinical and
financial models additionally `SoftDeleteModel`. Only deviations are noted.

### 2.1 Patients app (`apps.patients`)

**Patient** *(soft-delete)*
| Field | Type / rule |
|---|---|
| mrn | char, **unique per clinic**, generated `"{CLINIC_CODE}-{seq:06d}"`, immutable |
| first_name, last_name | required |
| date_of_birth | date, required (never age — FRD) |
| sex | enum M/F |
| national_id | char, nullable, indexed — primary dedupe key |
| phone, address, next_of_kin_name, next_of_kin_phone | optional |
| blood_group | enum, nullable |
| medical_aid_provider, medical_aid_number | char, optional (billing uses them on paper only in v1) |
| consent_given_at, consent_captured_by | required at registration (FRD §4.1) |
| status | enum `active / deceased / merged` (merge tooling Phase 2; enum now so no migration later) |

**PatientAllergy** *(soft-delete)*: patient FK, substance (char), reaction (char),
severity enum `mild/moderate/severe`, notes. **PatientCondition** *(soft-delete)*:
patient FK, condition (char), notes. Structured-list-plus-free-text per FRD §4.1;
coded allergy/condition vocabularies are a later refinement.

**MRN generation:** `ClinicCounter(clinic, key, value)` in `core`, incremented
under `select_for_update` inside the registration transaction. Same mechanism
issues invoice and receipt numbers (`key ∈ {mrn, invoice, receipt}`). A unit test
hammers it concurrently.

**Dedupe (Phase 1 = prevent, Phase 2 = repair):** `GET /patients/search` is the
registration entry point (by MRN, national ID, phone, name). `POST /patients/`
runs an exact-match check on national_id and phone; matches are returned as a
`409` with candidate summaries unless the client re-submits with
`"create_anyway": true` (that override is audited). No merge tool yet.

### 2.2 Encounters app (`apps.encounters`)

**Encounter** *(soft-delete)*
patient FK · type enum `walk_in / follow_up / emergency` (+`appointment`,`anc`
reserved) · status (below) · arrived_at · closed_at · assigned_doctor FK nullable ·
notes. Emergency sorts first in every queue, then arrival time.

**Status state machine** — single source of truth, one guarded `transition()`
method; illegal jumps raise; every transition audited (they're normal field
updates, so Phase 0 auditing covers them):

```
                       ┌──────────────► left_without_being_seen (from any pre-consultation state)
waiting ──► in_triage ──► awaiting_doctor ──► in_consultation ──► awaiting_payment ──► closed
   │                          ▲     │                                    ▲
   └──────────────────────────┘     └── (Phase 2: at_lab / at_pharmacy loops) ──┘
```

- `waiting → in_triage`: Nurse. `in_triage → awaiting_doctor`: Nurse (auto on vitals save).
- `waiting → awaiting_doctor`: Receptionist skip-triage (some clinics; permitted, audited).
- `awaiting_doctor → in_consultation`: Doctor **claims** the patient — row locked
  (`select_for_update`), sets `assigned_doctor`; two doctors cannot claim the same patient.
- `in_consultation → awaiting_payment`: automatic on consultation sign.
- `awaiting_payment → closed`: Cashier/Receptionist when invoice is settled **or**
  explicitly closed with balance (permission `close_with_balance`, reason required).
- `at_lab / at_pharmacy` states exist in the enum now (no enum migration in Phase 2)
  but no Phase 1 transition targets them.
- **Payment-first mode** (clinic setting): consultation fee is added to the invoice
  and payable at check-in; encounter cannot leave `waiting` until that line is paid
  (guard on the transition, not a separate state — keeps the machine identical
  in both modes).

**Queue:** `GET /encounters/queue?status=…` returns open encounters for the active
clinic, emergency-first. Frontend polls every 10 s via TanStack Query
(`refetchInterval`). **No WebSockets in Phase 1** — a clinic queue changes every
few minutes; polling is operationally simpler and works on flaky connections.
Revisit only with evidence.

**ClinicSettings:** `Clinic.settings` JSONField, schema-validated, defaults in code:
`payment_before_consultation: bool`, `allow_skip_triage: bool`,
`vitals_reference_ranges: {...}` (FRD §5.10). Admin-editable; every change audited.

### 2.3 Triage (`apps.encounters.vitals`)

**Vitals** *(soft-delete — corrections = void + re-enter, never edit)*
encounter FK (never patient directly — FRD) · systolic + diastolic (separate ints,
required for flagging) · pulse · temperature · weight_kg · height_cm · spo2 nullable ·
symptoms text · recorded_by.

Flagging is computed server-side against the clinic's reference ranges at
creation, and **both the applied ranges and the computed flags are snapshotted
onto the record** so historical entries keep meaning what they meant at the
time of care — threshold changes affect future recordings only. *(Amended from
the original "never stored" design — see ADR-0001.)* UI renders red/amber from
the stored flags.

### 2.4 Clinical app (`apps.clinical`)

**Consultation** *(soft-delete)* — the append-only heart of the system:
encounter FK · doctor FK · presenting_complaint · clinical_notes · treatment_plan ·
status `draft / signed` · signed_at · **amended_from** self-FK nullable · version int.

Lifecycle rules (enforced in model + serializer, not just UI):
1. Created as `draft` by the doctor who holds the encounter's `in_consultation` claim.
2. Draft: editable **by its author only**.
3. `sign`: sets signed_at, freezes the record — any later save attempt raises.
   Typed name + timestamp + audit entry = the FRD's v1 e-signature. Signing
   transitions the encounter and appends the consultation invoice line.
4. `amend`: creates a **new** Consultation (`amended_from=old, version=old+1`,
   copy of fields, status draft). Old record stays visible, marked "amended".
   Printables always render the latest signed version with an amendment notice.

**Diagnosis** (reference table, not clinic-scoped): code, name, is_active. Seeded
per Open Question Q3; ICD-10 import is a data exercise later, not a schema change.
**ConsultationDiagnosis**: consultation FK, diagnosis FK *nullable*, free_text —
coded-plus-free-text per FRD §5.3; at least one of (diagnosis, free_text) required.

**Prescription** *(soft-delete)*: consultation FK, status `issued / cancelled`.
**PrescriptionItem**: prescription FK, **medication FK** (minimal catalog),
dose (char, e.g. "500 mg"), frequency (char), duration_days (int), quantity (int),
instructions. Free-text `medication_note` only when the picklist lacks the drug
(flagged for Admin to add — keeps the catalog converging).

**Allergy guard (FRD §5.3):** on prescription save, substring/keyword match of
medication name vs the patient's `PatientAllergy.substance` entries → response
includes `allergy_warnings`; UI forces an explicit "prescribe anyway" which is
sent as `acknowledged_allergy_ids` and **audited**. This is a dumb-but-honest
banner, not an interaction engine (deferred per FRD).

**LabOrder** *(soft-delete)*: consultation FK, status `ordered / cancelled`,
instructions. **LabOrderItem**: lab_order FK, service_item FK (catalog, type
`lab`/`imaging`), price snapshot → invoice line on creation.

**SickNote**: consultation FK, unfit_from, unfit_to, remarks.
**ReferralLetter**: consultation FK, destination_facility, reason.
Both exist to be printed and to appear in the timeline (FRD §6).

### 2.5 Billing app (`apps.billing`)

**ServiceItem** (catalog): code, name, type enum `consultation / lab / imaging /
procedure / other`, is_active. **ServicePrice**: service FK, price decimal,
effective_from date, created_by — *current price = newest effective_from ≤ today*.
Prices are never edited: a change is a new row (FRD §5.10 "versioned — price
changes never rewrite history"). Unique (service, effective_from).

**Invoice** *(soft-delete)*: encounter **OneToOne** · number
(`INV-{CODE}-{YYYY}-{seq:06d}` via ClinicCounter) · issued_at. Created lazily on
first billable event (or at check-in in payment-first mode). **Status is always
derived** — annotation/property over payments: `unpaid / part_paid / paid` — never
a column (FRD).

**InvoiceItem** *(soft-delete)*: invoice FK · description · qty · unit_price
(snapshot at creation) · **source links**: `service_item` FK + exactly one of
`consultation` / `lab_order` FK, or none for manual catalog additions
(DB CheckConstraint) · item_type enum `service / discount`. Discount lines:
negative amount, require `billing.apply_discount` permission + reason (audited).
No free-text prices anywhere — unit_price always originates from ServicePrice.

**Payment** (**no soft delete — append-only**; a wrong payment is reversed, never
voided silently): invoice FK · amount > 0 · method enum `cash / ecocash / card /
other` · reference · receipt_number (ClinicCounter) · received_by · cash_up FK
nullable · `reversal_of` self-FK nullable (reversal = negative-effect row with
reason, permission-gated). Overpayment rejected; change is handled at the desk.

**CashUp**: clinic · cashier · period_start/end · expected_total (computed: sum of
that cashier's cash payments since their last cash-up) · counted_total ·
variance (derived) · notes · status `open / closed`. Closing stamps `cash_up` on
the covered payments. Variance ≠ 0 requires notes.

**Unpaid balances:** `GET /billing/unpaid/` — per-patient outstanding, from
derived invoice status (FRD §5.7).

### 2.6 Break-glass (in `core`) — FRD §3, §5.10

Admin has **no** standing clinical read access. `POST /break-glass/` with
`patient_id` + mandatory reason writes a high-visibility `AuditLog` entry
(action `break_glass`, new enum value) and stores a session grant
`{patient_id, expires_at: now+15min}`. Clinical view permissions accept
Doctor/Nurse roles **or** a live grant. Every read under a grant is read-audited
as usual. No model needed — session + audit log is the record.

---

## 3. Printable Forms — design decision (FRD refinement)

FRD §6 says "PDFs generated by background jobs". For **at-desk printing** a queued
PDF is the wrong tool: the receptionist needs the registration form *now*, and a
Celery round-trip + poll adds seconds and failure modes to every patient.

**Decision:** Phase 1 printables are **server-rendered, print-optimized HTML**
(Django templates, `@media print` CSS, clinic header from settings) opened in a
new tab → browser print dialog. They are session-authenticated, role-gated, and
**read-audited** (they render clinical data). Async PDF generation (Celery +
WeasyPrint) arrives in Phase 3 where the FRD actually needs files (reports,
exports). If sign-off requires literal PDFs at the desk, WeasyPrint can render
the same templates synchronously — the templates are the investment either way.

Routes: `/print/registration/{patient}/ · /print/prescription/{rx}/ ·
/print/lab-request/{order}/ · /print/sick-note/{id}/ · /print/referral/{id}/ ·
/print/invoice/{invoice}/ · /print/receipt/{payment}/`.

---

## 4. API Surface (all under `/api/v1/`, clinic-scoped, cursor-paginated)

| Endpoint | Methods | Roles (Admin ⇒ via break-glass where marked †) |
|---|---|---|
| `patients/search/?q=` | GET | Receptionist, Nurse, Doctor, Cashier |
| `patients/` | POST | Receptionist |
| `patients/{id}/` | GET, PATCH | Receptionist (demographics); clinical summary fields † |
| `patients/{id}/summary/` | GET | Nurse, Doctor — allergies + conditions banner payload |
| `patients/{id}/timeline/` | GET † | Doctor, Nurse — chronological encounters (read-audited) |
| `patients/{id}/allergies/`, `…/conditions/` | GET, POST, void | Nurse, Doctor |
| `encounters/` | POST | Receptionist |
| `encounters/queue/?status=` | GET | all clinical roles (payload trimmed per role) |
| `encounters/{id}/transition/` | POST | per-transition (see §2.2) |
| `encounters/{id}/vitals/` | GET†, POST | Nurse (POST); Nurse/Doctor (GET) |
| `encounters/{id}/consultation/` | POST | Doctor (claim-holder) |
| `consultations/{id}/` | GET†, PATCH | Doctor; PATCH draft+author only (read-audited) |
| `consultations/{id}/sign/`, `…/amend/` | POST | Doctor (author) |
| `consultations/{id}/prescriptions/`, `…/lab-orders/`, `…/sick-notes/`, `…/referrals/` | POST | Doctor (author, draft or signed-same-visit) |
| `medications/?q=`, `diagnoses/?q=` | GET | Doctor (picklists) |
| `billing/catalog/`, `billing/prices/` | GET; POST (prices) | all read; Admin manage |
| `encounters/{id}/invoice/` | GET | Receptionist, Cashier, Admin |
| `invoices/{id}/items/` | POST | Receptionist, Cashier (catalog items; discounts permission-gated) |
| `invoices/{id}/payments/` | POST | Cashier, Receptionist |
| `payments/{id}/reverse/` | POST | Cashier + `reverse_payment` perm |
| `billing/cashup/` | GET current, POST close | Cashier |
| `billing/unpaid/` | GET | Cashier, Admin |
| `break-glass/` | POST | Admin |
| `/print/...` | GET | role-gated per document, read-audited |

**Permission implementation:** one `RolePermission` class driven by a declarative
`ROLE_MATRIX` (viewset × action → groups), plus object-level checks (author-only
edits, claim-holder rules) in `has_object_permission`. The matrix is a single
reviewable file mirroring FRD §3, and a **parametrized test walks every cell** —
role × endpoint × expected status — so a permissions regression is a failing test,
not an incident. Receptionist/Cashier requests never receive clinical fields:
separate serializers per role tier, not field hiding in the client.

---

## 5. Frontend

Routes (role-aware shell from Phase 0):

- `/queue` — landing for clinical roles; columns/actions differ per role
  (Nurse: start triage · Doctor: claim/resume · Reception: check-in, monitor)
- `/patients` search-first registration; `/patients/:id` profile + timeline
- `/visit/:encounterId` — the shared visit workspace: allergy banner (always),
  vitals panel, consultation editor (doctor), orders/prescriptions, invoice panel
- `/billing/cashup`, `/billing/unpaid` — cashier
- `/admin/catalog` — Admin: services, prices, medications, diagnoses, settings

State: TanStack Query throughout; queue at `refetchInterval: 10_000`; mutations
invalidate encounter + queue keys. Print buttons open `/print/...` in a new tab.
Forms: controlled components + server-side validation surfaced inline (DRF error
shape → field errors). No client-side-only validation of anything clinical.

---

## 6. Testing Strategy

1. **State machine matrix** — every (state, transition, role) combination
   asserted legal/illegal; concurrency test for double-claim.
2. **Permission matrix walk** — parametrized over `ROLE_MATRIX` (§4).
3. **Billing math** — property-style tests: partial payments, discounts,
   reversals, derived status; price snapshotting when ServicePrice changes;
   invoice/receipt number uniqueness under concurrency.
4. **Consultation immutability** — signed records reject writes at the model
   layer; amendment chains render correctly.
5. **Audit assertions in feature tests** — each workflow test also asserts its
   expected audit entries (sign, void, override, break-glass, reads).
6. **One end-to-end flow test** — register → check-in → triage → claim → sign →
   prescribe → invoice → pay → close, exercised through the API as four different
   role sessions.

---

## 7. Work Breakdown (PR-sized, in dependency order)

| # | Slice | Contents |
|---|---|---|
| 1 | Billing foundations | ClinicCounter, ServiceItem/ServicePrice, catalog admin + seed command |
| 2 | Patients | Patient + MRN, allergies/conditions, search, dedupe-409, consent, summary endpoint |
| 3 | Encounters | state machine, queue API, clinic settings (payment-first, skip-triage). *Resequenced (consequence of decision Q2):* minimal Invoice/InvoiceItem/Payment models + check-in fee flow moved here from slice 7, because the payment-first guard needs them; slice 7 keeps discounts, reversals, manual items | 
| 4 | Vitals | model, flagging, auto-transition |
| 5 | Consultations | draft/sign/amend, diagnoses, break-glass, read-audit wiring |
| 6 | Orders & printables | prescriptions + allergy guard, minimal Medication + LabOrder, sick note, referral, all print views |
| 7 | Invoices & payments | invoice lifecycle, items, payments, reversals, discounts |
| 8 | Cash-up & unpaid | cash-up close flow, unpaid balances |
| 9 | Frontend | queue → registration → visit workspace → billing screens (4 sub-PRs, shippable after each) |
| 10 | Hardening | permission-matrix test walk, E2E flow test, seed data polish |

Backend slices 1–8 ≈ 4–5 weeks; frontend overlaps from slice 3. Matches the FRD's
6–8 week Phase 1 estimate with slack for go-live feedback.

---

## 8. Decisions (resolved with product owner, 2026-07-13)

**Q1 — Appointments: deferred to Phase 3.** Built alongside SMS reminders where
they deliver value. `Encounter.type` reserves the enum value now.

**Q2 — Payment timing: pilot clinic collects the consultation fee up front.**
`payment_before_consultation` defaults to **true**; the check-in → pay → triage
path is the primary flow for UX polish and testing. Pay-after remains fully
supported behind the toggle and covered by tests.

**Q3 — Diagnosis seed: ICD-10 primary-care subset** (~800 codes), seeded by a
management command in slice 5. Per-clinic "frequently used" pinning noted as a
Phase 3 UX enhancement, not built now.
