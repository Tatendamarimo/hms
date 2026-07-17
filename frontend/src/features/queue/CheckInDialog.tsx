import { useState } from "react";
import { Link } from "react-router-dom";
import type { Patient } from "../../api/types";
import { ErrorNotice } from "../../ui/format";
import { usePatientSearch } from "../patients/usePatients";
import { useCheckIn, useConsultationServices } from "./useQueue";

/** Search-first check-in (design §5). Picking a priced consultation service
 * adds the fee line at check-in — the payment-first gate then holds triage
 * until the invoice is settled (server-enforced either way). */
export default function CheckInDialog({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [patient, setPatient] = useState<Patient | null>(null);
  const [type, setType] = useState("walk_in");
  const [serviceId, setServiceId] = useState<number | "">("");
  const [notes, setNotes] = useState("");

  const search = usePatientSearch(query);
  const services = useConsultationServices();
  const checkIn = useCheckIn();

  const submit = () => {
    if (!patient) return;
    checkIn.mutate(
      {
        patient: patient.id,
        type,
        notes,
        checkin_service: serviceId === "" ? null : serviceId,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-lg space-y-4 rounded-xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">Check in patient</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            ✕
          </button>
        </div>

        {patient === null ? (
          <div className="space-y-2">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, MRN, national ID or phone…"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="max-h-64 divide-y divide-slate-100 overflow-y-auto rounded-md border border-slate-200">
              {(search.data ?? []).map((hit) => (
                <button
                  key={hit.id}
                  onClick={() => setPatient(hit)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
                >
                  <span className="font-medium text-slate-800">
                    {hit.first_name} {hit.last_name}
                  </span>
                  <span className="text-xs text-slate-500">
                    {hit.mrn} · {hit.sex} · {hit.age}y
                  </span>
                </button>
              ))}
              {query.trim().length >= 2 && search.data?.length === 0 && (
                <div className="space-y-1 px-3 py-4 text-center text-sm text-slate-500">
                  <div>No matches.</div>
                  <Link to="/patients" className="text-slate-700 underline" onClick={onClose}>
                    Register a new patient
                  </Link>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
              <span className="font-medium text-slate-800">
                {patient.first_name} {patient.last_name}
                <span className="ml-2 text-xs text-slate-500">{patient.mrn}</span>
              </span>
              <button
                onClick={() => setPatient(null)}
                className="text-xs text-slate-500 underline"
              >
                change
              </button>
            </div>

            <label className="block text-sm">
              <span className="text-slate-600">Visit type</span>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="walk_in">Walk-in</option>
                <option value="follow_up">Follow-up</option>
                <option value="emergency">Emergency</option>
              </select>
            </label>

            <label className="block text-sm">
              <span className="text-slate-600">Consultation fee (added to the invoice)</span>
              <select
                value={serviceId}
                onChange={(e) =>
                  setServiceId(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="">No fee at check-in</option>
                {(services.data ?? []).map((service) => (
                  <option key={service.id} value={service.id}>
                    {service.name} — {service.current_price}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm">
              <span className="text-slate-600">Notes (optional)</span>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              />
            </label>

            <ErrorNotice error={checkIn.error} />

            <button
              onClick={submit}
              disabled={checkIn.isPending}
              className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {checkIn.isPending ? "Checking in…" : "Check in"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
