"""Pure domain rules for triage vitals — no Django imports, no I/O.

Plausibility bounds reject data-entry errors outright (a systolic of 500 is a
typo, not a finding). Reference ranges produce flags; both the ranges applied
and the resulting flags are SNAPSHOTTED onto the record at creation (ADR-0001)
so historical records keep meaning what they meant when they were taken.
"""

from decimal import Decimal

# Hard physical plausibility — outside these is a rejected entry, not a flag.
PLAUSIBLE_BOUNDS = {
    "systolic": (40, 300),
    "diastolic": (20, 200),
    "pulse": (20, 250),
    "temperature": (Decimal("25.0"), Decimal("45.0")),
    "spo2": (40, 100),
    "weight_kg": (Decimal("0.5"), Decimal("500")),
    "height_cm": (Decimal("20"), Decimal("250")),
}

# Fields that participate in abnormal flagging (must match the keys of the
# clinic setting 'vitals_reference_ranges').
FLAGGABLE_FIELDS = ("systolic", "diastolic", "pulse", "temperature", "spo2")


def implausible_fields(measurements: dict) -> dict[str, str]:
    """Returns {field: message} for values outside physical plausibility."""
    errors = {}
    for field, (low, high) in PLAUSIBLE_BOUNDS.items():
        value = measurements.get(field)
        if value is None:
            continue
        if not (Decimal(low) <= Decimal(value) <= Decimal(high)):
            errors[field] = f"Value {value} is outside the plausible range {low}–{high}."
    return errors


def compute_flags(measurements: dict, ranges: dict) -> list[dict]:
    """[{field, value, low, high, direction}] for out-of-range measurements."""
    flags = []
    for field in FLAGGABLE_FIELDS:
        value = measurements.get(field)
        range_ = ranges.get(field)
        if value is None or not range_:
            continue
        value_d = Decimal(str(value))
        low, high = Decimal(str(range_["low"])), Decimal(str(range_["high"]))
        if value_d < low or value_d > high:
            flags.append(
                {
                    "field": field,
                    "value": str(value),
                    "low": str(range_["low"]),
                    "high": str(range_["high"]),
                    "direction": "low" if value_d < low else "high",
                }
            )
    return flags
