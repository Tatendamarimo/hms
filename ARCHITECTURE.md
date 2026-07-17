# HMS Architecture

Modular Django monolith + React SPA. Source of truth for requirements: FRD v2;
for Phase 1 structure: `docs/phase1-technical-design.md`; deviations from
approved designs are recorded in `docs/adr/`.

## Apps and dependency directions

```
core        ← everyone (base models, audit, permissions, clinic scoping, counters, print plumbing)
clinics     ← accounts, and every ClinicScopedModel (tenancy)
accounts    ← views everywhere (roles module), user FKs via settings.AUTH_USER_MODEL
patients    ← encounters, clinical
encounters  ← clinical, billing (Invoice.encounter FK — by string reference only)
billing     ← (called BY encounters and laboratory through apps.billing.services only)
clinical    → encounters (FK + state transition via encounters.services), patients (reads),
              pharmacy (Medication FK on PrescriptionItem)
pharmacy    ← clinical (leaf app: Medication picklist only, no stock)
laboratory  → clinical (consultation FK + document-window/author rules),
              billing (ensure_invoice/add_service_line/void_lines_for_lab_order)
```

**Boundary rules (enforced in review):**

1. Cross-app **writes** go through the owning app's `services.py` — e.g.
   encounters never creates an Invoice directly; it calls
   `billing.services.ensure_invoice/add_service_line`. Local (in-function)
   imports are used for these calls to keep module graphs acyclic.
2. Cross-app **reads** of public models (picklist querysets, FK targets) are
   allowed — idiomatic Django, no wrappers for wrappers' sake.
3. FKs to another app's model use string references (`"encounters.Encounter"`).
4. URL shape does not dictate code location: `/patients/{id}/timeline/` is
   served by `encounters` because it renders encounters.

## Non-negotiable conventions (FRD §7.1)

- Every business table: `created_at/updated_at/created_by` (TimeStampedModel)
  and `clinic` FK (ClinicScopedModel). Querysets are clinic-scoped through
  `ClinicScopedViewSetMixin` — membership re-validated per request.
- Clinical/financial data is soft-delete only: `void(by=…, reason=…)`;
  `.delete()` raises. Payments are append-only (not even voidable) — mistakes
  are corrected by reversal rows.
- Status/lifecycle fields are mutated ONLY by domain services
  (`encounters.services.transition`, `record_vitals`) — never by views,
  serializers, or the Django admin (Encounter admin is read-only).
- Business rules live in `services.py` / pure rule modules
  (`state_machine.py`, `vitals_rules.py`); serializers validate transport,
  views translate exceptions to HTTP.
- Concurrency-sensitive operations take a row lock (`select_for_update`):
  counters, doctor claim, payment recording, vitals + auto-transition,
  consultation sign/amend, prescription + lab-order cancellation, invoice
  adjustments (manual lines, discounts, line voids) + payment reversal,
  cash-up close (locks the payments being stamped).
- Clinical computations snapshot their inputs (ADR-0001): vitals store applied
  ranges + flags; invoice items and lab-order items store unit prices.
- Printables (`/print/…`, outside `/api/v1/`) are server-rendered HTML built
  only from stored rows — no recomputation at print time, so a document prints
  the same tomorrow as today (plus a printed-by/-at footer). Every print view
  is wrapped by `core.printing.print_view(roles)` (session + role + active
  clinic); prints of clinical documents also write a `log_read` audit entry.
- Clinical documents (prescription, sick note, referral, lab order) attach to
  the **author's** consultation — draft or signed — only while the visit is
  open (`require_open_document_window`); cancellation is status-flip +
  reason, never deletion, and lab-order cancellation voids its linked
  invoice lines through `billing.services`.
- Signed consultations are immutable at the MODEL layer
  (`Consultation.save()` raises except for void fields); corrections are
  versioned amendments chained by a OneToOne `amended_from`. Clinical actions
  never mutate billing (ADR-0002).
- Break-glass (core/break_glass.py): Admin clinical access is session-scoped
  per patient, read-only, 15-minute expiry, announced by a BREAK_GLASS audit
  entry; reads under a grant are flagged in the audit log.
- Auditing: every mutation of an `AuditedModel` is logged automatically with
  before/after diffs; clinical READS are logged via `log_read`/`AuditedReadMixin`;
  privileged overrides (duplicate-override, transition reasons) write explicit
  entries. `AuditLog` is append-only and read-only in admin.
- Permissions: declarative `role_map` per view (deny-by-default, no
  Admin/superuser bypass) + Django permissions for named privileges
  (`encounters.close_with_balance`, `billing.apply_discount`,
  `billing.reverse_payment`), seeded by `seed_roles`; named-permission checks
  live in the service layer so they hold no matter which view calls in.

## Testing standard

Every slice ships with: edge cases before happy paths, a permission test for
every endpoint/role pair it adds, state-machine legality tests where relevant,
audit assertions inside feature tests, and a green run on BOTH SQLite (default
local) and PostgreSQL (`DATABASE_URL=…`, what CI runs). Concrete test models
for base-class contracts live in `apps.testapp` (test settings only).
