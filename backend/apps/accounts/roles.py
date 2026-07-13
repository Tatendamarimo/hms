"""The seven FRD §3 roles. Groups are created by `manage.py seed_roles`;
module-level permissions are attached to these groups as each phase lands
(Phase 1 adds patient/encounter/billing perms, etc.)."""

RECEPTIONIST = "Receptionist"
NURSE = "Nurse"
DOCTOR = "Doctor"
LAB_TECHNICIAN = "Lab Technician"
PHARMACIST = "Pharmacist"
CASHIER = "Cashier"
ADMIN = "Admin"

ALL_ROLES = [RECEPTIONIST, NURSE, DOCTOR, LAB_TECHNICIAN, PHARMACIST, CASHIER, ADMIN]
