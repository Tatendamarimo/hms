import { ApiError } from "../../api/client";
import type { Patient } from "../../api/types";
import type { RegistrationInput } from "./usePatients";

export type PatientFields = Omit<RegistrationInput, "consent_confirmed" | "create_anyway">;

export function emptyPatient(): PatientFields {
  return {
    first_name: "",
    last_name: "",
    date_of_birth: "",
    sex: "",
    national_id: "",
    phone: "",
    address: "",
    next_of_kin_name: "",
    next_of_kin_phone: "",
    blood_group: "",
    medical_aid_provider: "",
    medical_aid_number: "",
  };
}

export function fieldsFrom(patient: Patient): PatientFields {
  return {
    first_name: patient.first_name,
    last_name: patient.last_name,
    date_of_birth: patient.date_of_birth,
    sex: patient.sex,
    national_id: patient.national_id,
    phone: patient.phone,
    address: patient.address,
    next_of_kin_name: patient.next_of_kin_name,
    next_of_kin_phone: patient.next_of_kin_phone,
    blood_group: patient.blood_group,
    medical_aid_provider: patient.medical_aid_provider,
    medical_aid_number: patient.medical_aid_number,
  };
}

/** DRF's {field: [messages]} error body → per-field message map. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || typeof error.body !== "object" || !error.body) {
    return {};
  }
  const out: Record<string, string> = {};
  for (const [field, messages] of Object.entries(error.body as Record<string, unknown>)) {
    if (Array.isArray(messages)) out[field] = messages.join(" ");
    else if (typeof messages === "string" && field !== "detail") out[field] = messages;
  }
  return out;
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="text-slate-600">{label}</span>
      {children}
      {error && <span className="mt-0.5 block text-xs text-rose-600">{error}</span>}
    </label>
  );
}

const inputClass = "mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm";

export default function PatientForm({
  value,
  onChange,
  errors,
}: {
  value: PatientFields;
  onChange: (next: PatientFields) => void;
  errors: Record<string, string>;
}) {
  const set = (key: keyof PatientFields) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...value, [key]: e.target.value });

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <Field label="First name *" error={errors.first_name}>
        <input value={value.first_name} onChange={set("first_name")} className={inputClass} />
      </Field>
      <Field label="Last name *" error={errors.last_name}>
        <input value={value.last_name} onChange={set("last_name")} className={inputClass} />
      </Field>
      <Field label="Date of birth *" error={errors.date_of_birth}>
        <input
          type="date"
          value={value.date_of_birth}
          onChange={set("date_of_birth")}
          className={inputClass}
        />
      </Field>
      <Field label="Sex *" error={errors.sex}>
        <select value={value.sex} onChange={set("sex")} className={inputClass}>
          <option value="">—</option>
          <option value="M">Male</option>
          <option value="F">Female</option>
        </select>
      </Field>
      <Field label="National ID" error={errors.national_id}>
        <input value={value.national_id} onChange={set("national_id")} className={inputClass} />
      </Field>
      <Field label="Phone" error={errors.phone}>
        <input value={value.phone} onChange={set("phone")} className={inputClass} />
      </Field>
      <div className="sm:col-span-2">
        <Field label="Address" error={errors.address}>
          <input value={value.address} onChange={set("address")} className={inputClass} />
        </Field>
      </div>
      <Field label="Next of kin" error={errors.next_of_kin_name}>
        <input
          value={value.next_of_kin_name}
          onChange={set("next_of_kin_name")}
          className={inputClass}
        />
      </Field>
      <Field label="Next of kin phone" error={errors.next_of_kin_phone}>
        <input
          value={value.next_of_kin_phone}
          onChange={set("next_of_kin_phone")}
          className={inputClass}
        />
      </Field>
      <Field label="Blood group" error={errors.blood_group}>
        <select value={value.blood_group} onChange={set("blood_group")} className={inputClass}>
          <option value="">Unknown</option>
          {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((group) => (
            <option key={group} value={group}>
              {group}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Medical aid provider" error={errors.medical_aid_provider}>
        <input
          value={value.medical_aid_provider}
          onChange={set("medical_aid_provider")}
          className={inputClass}
        />
      </Field>
      <Field label="Medical aid number" error={errors.medical_aid_number}>
        <input
          value={value.medical_aid_number}
          onChange={set("medical_aid_number")}
          className={inputClass}
        />
      </Field>
    </div>
  );
}
