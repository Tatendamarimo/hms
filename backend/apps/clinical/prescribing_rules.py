"""Pure prescribing rules — no Django imports, no I/O.

The allergy guard is a deliberately simple, honest banner (design §2.4):
case-insensitive substring matching between medication names and documented
allergy substances. It catches "Penicillin V" against a "penicillin" allergy;
it does NOT know pharmacology (Amoxicillin vs a penicillin allergy passes
silently). Cross-reactivity requires the licensed interaction dataset that
the FRD explicitly defers — do not "improve" this with home-grown drug
knowledge."""


def match_allergies(medication_names: list[str], allergies) -> list[dict]:
    """allergies: iterable of (allergy_id, substance).
    Returns [{allergy_id, substance, medication}] for every match."""
    warnings = []
    for name in medication_names:
        needle = name.lower().strip()
        if not needle:
            continue
        for allergy_id, substance in allergies:
            hay = substance.lower().strip()
            if hay and (hay in needle or needle in hay):
                warnings.append(
                    {"allergy_id": allergy_id, "substance": substance, "medication": name}
                )
    return warnings
