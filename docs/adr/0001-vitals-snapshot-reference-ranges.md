# ADR-0001: Vitals snapshot their reference ranges and computed flags

**Date:** 2026-07-14
**Status:** Accepted
**Supersedes:** Phase 1 Technical Design §2.3 ("flags … never stored")

## Context

The approved Phase 1 design computed abnormal-vitals flags dynamically against
the clinic's *current* reference ranges, arguing that stored flags "would lie
about history" when ranges change.

During Slice 4 review the product owner raised the opposite concern, and it is
the correct one for a clinical record: if a clinic later tightens its BP
threshold, recomputing makes historical triage entries *appear* abnormal even
though the nurse correctly saw "normal" at the time of care. A chart is a
point-in-time document; retroactively re-colouring it misrepresents the care
that was given and undermines the audit trail.

## Decision

Each `Vitals` record stores, at creation time:

- `applied_ranges` — the clinic's reference ranges in force at that moment
- `flags` — the abnormal-value flags computed against those ranges

Reads return the stored values; current clinic settings are consulted only
when a new record is created. The rows are immutable (void + re-enter for
corrections), so the snapshot can never drift.

## Consequences

- Historical records keep meaning what they meant when they were taken.
- Threshold changes take effect for future recordings only — no recompute
  tooling, no migration on settings change.
- Small storage overhead (one JSON object per vitals row) — negligible.
- **Precedent:** clinical computations snapshot their inputs. This matches
  existing practice in billing (`InvoiceItem.unit_price` snapshots the price
  list) and applies forward — e.g. Slice 6's allergy guard records the
  acknowledged allergy IDs rather than re-deriving them.
