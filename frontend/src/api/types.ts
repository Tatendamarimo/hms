export interface Branding {
  logo_url: string;
  favicon_url: string;
  primary_color: string;
  secondary_color: string;
  tagline: string;
}

export interface Clinic {
  id: number;
  name: string;
  code: string;
  address: string;
  phone: string;
  branding?: Branding;
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

export interface Allergy {
  id: number;
  substance: string;
  reaction: string;
  severity: string;
  notes: string;
  created_at: string;
}

export interface Condition {
  id: number;
  condition: string;
  notes: string;
  created_at: string;
}

export interface PatientSummary {
  id: number;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  age: number;
  sex: string;
  blood_group: string;
  status: string;
  allergies: Allergy[];
  conditions: Condition[];
}

export interface VitalsFlag {
  field: string;
  value: string;
  low: string;
  high: string;
  direction: "low" | "high";
}

export interface Vitals {
  id: number;
  systolic: number;
  diastolic: number;
  pulse: number;
  temperature: string;
  weight_kg: string | null;
  height_cm: string | null;
  spo2: number | null;
  symptoms: string;
  flags: VitalsFlag[];
  applied_ranges: Record<string, unknown>;
  recorded_by_name: string | null;
  created_at: string;
}

export interface Medication {
  id: number;
  name: string;
  strength: string;
  form: string;
  label: string;
}

export interface Diagnosis {
  id: number;
  code: string;
  name: string;
}

export interface ConsultationDiagnosis {
  id: number;
  diagnosis: number | null;
  code: string | null;
  name: string | null;
  free_text: string;
}

export interface PrescriptionItem {
  id: number;
  medication: number | null;
  medication_note: string;
  display_name: string;
  dose: string;
  frequency: string;
  duration_days: number;
  quantity: number;
  instructions: string;
}

export interface Prescription {
  id: number;
  consultation: number;
  status: string;
  items: PrescriptionItem[];
  created_at: string;
}

export interface SickNote {
  id: number;
  consultation: number;
  unfit_from: string;
  unfit_to: string;
  remarks: string;
  created_at: string;
}

export interface Referral {
  id: number;
  consultation: number;
  destination_facility: string;
  reason: string;
  created_at: string;
}

export interface LabOrderItem {
  id: number;
  service_item: number;
  name: string;
  type: string;
  price: string;
}

export interface LabOrder {
  id: number;
  consultation: number;
  status: string;
  instructions: string;
  items: LabOrderItem[];
  created_at: string;
}

export interface Consultation {
  id: number;
  encounter: number;
  doctor_name: string;
  status: "draft" | "signed" | "cancelled";
  version: number;
  amended_from: number | null;
  amended_by_id: number | null;
  amendment_reason: string;
  presenting_complaint: string;
  clinical_notes: string;
  treatment_plan: string;
  diagnoses: ConsultationDiagnosis[];
  prescriptions: Prescription[];
  sick_notes: SickNote[];
  referrals: Referral[];
  signed_at: string | null;
  created_at: string;
}

export interface AllergyWarning {
  allergy_id: number;
  substance: string;
  medication: string;
}

export interface InvoiceItem {
  id: number;
  description: string;
  quantity: number;
  unit_price: string;
  line_total: string;
  item_type: "service" | "discount";
  discount_reason: string;
  service_item: number | null;
  created_at: string;
}

export interface Payment {
  id: number;
  amount: string;
  method: string;
  reference: string;
  receipt_number: string;
  received_by_name: string;
  reversal_of: number | null;
  created_at: string;
}

export interface InvoiceDetail {
  id: number;
  number: string;
  encounter: number;
  issued_at: string;
  total: string;
  paid_total: string;
  balance: string;
  status: InvoiceStatus;
  items: InvoiceItem[];
  payments: Payment[];
}
