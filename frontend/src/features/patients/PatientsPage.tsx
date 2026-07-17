import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../../api/client";
import type { Me, Patient } from "../../api/types";
import { ErrorNotice } from "../../ui/format";
import PatientForm, { emptyPatient, fieldErrors, type PatientFields } from "./PatientForm";
import { usePatientSearch, useRegisterPatient } from "./usePatients";

/** Search-first registration (design §2.1): the form only opens after a
 * search, and the API's duplicate 409 shows candidates before create-anyway. */
export default function PatientsPage({ me }: { me: Me }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [registering, setRegistering] = useState(false);
  const [fields, setFields] = useState<PatientFields>(emptyPatient());
  const [consent, setConsent] = useState(false);
  const search = usePatientSearch(query);
  const register = useRegisterPatient();
  const canRegister = me.roles.includes("Receptionist");

  const searched = query.trim().length >= 2;
  const duplicates =
    register.error instanceof ApiError && register.error.status === 409
      ? ((register.error.body as { candidates?: Patient[] })?.candidates ?? [])
      : [];

  const submit = (createAnyway: boolean) => {
    register.mutate(
      { ...fields, consent_confirmed: consent, create_anyway: createAnyway },
      { onSuccess: (patient) => navigate(`/patients/${patient.id}`) },
    );
  };

  const openForm = () => {
    const words = query.trim().split(/\s+/);
    setFields({
      ...emptyPatient(),
      first_name: words[0] ?? "",
      last_name: words.slice(1).join(" "),
    });
    register.reset();
    setConsent(false);
    setRegistering(true);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Patients</h1>

      <input
        autoFocus
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setRegistering(false);
        }}
        placeholder="Search by name, MRN, national ID or phone…"
        className="w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm shadow-sm"
      />

      {searched && !registering && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          {(search.data ?? []).map((patient) => (
            <Link
              key={patient.id}
              to={`/patients/${patient.id}`}
              className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-sm last:border-0 hover:bg-slate-50"
            >
              <span className="font-medium text-slate-800">
                {patient.first_name} {patient.last_name}
              </span>
              <span className="text-xs text-slate-500">
                {patient.mrn} · {patient.sex} · {patient.age}y · {patient.phone || "no phone"}
              </span>
            </Link>
          ))}
          <div className="flex items-center justify-between px-4 py-3 text-sm text-slate-500">
            <span>
              {search.data?.length
                ? `${search.data.length} match(es).`
                : "No matching patients."}
            </span>
            {canRegister && (
              <button
                onClick={openForm}
                className="rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
              >
                Register new patient
              </button>
            )}
          </div>
        </div>
      )}

      {!searched && (
        <p className="text-sm text-slate-500">
          Start with a search — registration opens only when no record matches
          (search-first, FRD §4.1).
        </p>
      )}

      {registering && (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-800">New patient</h2>
          <PatientForm value={fields} onChange={setFields} errors={fieldErrors(register.error)} />

          <label className="flex items-start gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5"
            />
            The patient consents to their information being stored for care and
            billing (required).
          </label>

          {duplicates.length > 0 ? (
            <div className="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
              <p className="font-medium text-amber-800">
                Possible existing record(s) — open one instead of re-registering:
              </p>
              {duplicates.map((candidate) => (
                <Link
                  key={candidate.id}
                  to={`/patients/${candidate.id}`}
                  className="block rounded-md bg-white px-3 py-2 text-slate-700 hover:bg-slate-50"
                >
                  {candidate.first_name} {candidate.last_name} · {candidate.mrn} ·{" "}
                  {candidate.phone || candidate.national_id}
                </Link>
              ))}
              <button
                onClick={() => submit(true)}
                disabled={register.isPending}
                className="rounded-md border border-amber-400 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100 disabled:opacity-50"
              >
                None of these — create anyway (audited)
              </button>
            </div>
          ) : (
            register.error && <ErrorNotice error={register.error} />
          )}

          <div className="flex gap-3">
            <button
              onClick={() => submit(false)}
              disabled={register.isPending || !consent}
              className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {register.isPending ? "Registering…" : "Register"}
            </button>
            <button
              onClick={() => setRegistering(false)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
