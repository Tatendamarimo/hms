export interface Clinic {
  id: number;
  name: string;
  code: string;
  address: string;
  phone: string;
}

export type Role =
  | "Receptionist"
  | "Nurse"
  | "Doctor"
  | "Lab Technician"
  | "Pharmacist"
  | "Cashier"
  | "Admin";

export interface Me {
  id: number;
  username: string;
  full_name: string;
  roles: Role[];
  active_clinic: Clinic | null;
  clinics: Clinic[];
}

export type EncounterStatus =
  | "waiting"
  | "in_triage"
  | "awaiting_doctor"
  | "in_consultation"
  | "at_lab"
  | "at_pharmacy"
  | "awaiting_payment"
  | "closed"
  | "left_without_being_seen";

export type EncounterType =
  | "walk_in"
  | "follow_up"
  | "emergency"
  | "appointment"
  | "anc";

export type InvoiceStatus = "unpaid" | "part_paid" | "paid";

export interface InvoiceSummary {
  id: number;
  number: string;
  total: string;
  balance: string;
  status: InvoiceStatus;
}

export interface Encounter {
  id: number;
  patient_id: number;
  patient_mrn: string;
  patient_name: string;
  type: EncounterType;
  status: EncounterStatus;
  arrived_at: string;
  closed_at: string | null;
  assigned_doctor_name: string | null;
  notes: string;
  invoice: InvoiceSummary | null;
}

export interface Patient {
  id: number;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  age: number;
  sex: string;
  national_id: string;
  phone: string;
  address: string;
  next_of_kin_name: string;
  next_of_kin_phone: string;
  blood_group: string;
  medical_aid_provider: string;
  medical_aid_number: string;
  status: string;
  created_at: string;
}

export interface CatalogService {
  id: number;
  code: string;
  name: string;
  type: "consultation" | "lab" | "imaging" | "procedure" | "other";
  is_active: boolean;
  current_price: string | null;
}
