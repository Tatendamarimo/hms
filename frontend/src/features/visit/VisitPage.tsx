import { Link, useParams } from "react-router-dom";
import type { Me } from "../../api/types";
import { EncounterStatusBadge, ErrorNotice, formatDate, formatTime } from "../../ui/format";
import ConsultationPanel from "./ConsultationPanel";
import InvoicePanel from "./InvoicePanel";
import VitalsPanel from "./VitalsPanel";
import { useEncounter, usePatientSummary } from "./useVisit";

/** The shared visit workspace (design §5): every station works this page,
 * and each panel appears only for the roles the API will let in. */
export default function VisitPage({ me }: { me: Me }) {
  const { id } = useParams();
  const encounterId = Number(id);
  const encounter = useEncounter(encounterId);
  const isClinical = me.roles.includes("Nurse") || me.roles.includes("Doctor");
  const isDesk =
    me.roles.includes("Receptionist") ||
    me.roles.includes("Cashier") ||
    me.roles.includes("Admin");
  const summary = usePatientSummary(encounter.data?.patient_id, isClinical);

  if (encounter.isLoading) {
    return <div className="p-10 text-center text-slate-400">Loading visit…</div>;
  }
  if (!encounter.data) {
    return <ErrorNotice error={encounter.error ?? "Visit not found."} />;
  }
  const visit = encounter.data;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-lg font-semibold text-slate-800">
            <Link to={`/patients/${visit.patient_id}`} className="hover:underline">
              {visit.patient_name}
            </Link>
            <EncounterStatusBadge status={visit.status} />
            {visit.type === "emergency" && (
              <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">
                Emergency
              </span>
            )}
          </h1>
          <p className="text-sm text-slate-500">
            {visit.patient_mrn} · arrived {formatDate(visit.arrived_at)}{" "}
            {formatTime(visit.arrived_at)}
            {visit.assigned_doctor_name && <> · {visit.assigned_doctor_name}</>}
          </p>
        </div>
        <Link to="/queue" className="text-sm text-slate-500 hover:underline">
          ← Queue
        </Link>
      </div>

      {/* Allergy banner — always visible to clinical roles (design §5) */}
      {isClinical && summary.data && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            summary.data.allergies.length > 0
              ? "border-rose-300 bg-rose-50"
              : "border-emerald-200 bg-emerald-50"
          }`}
        >
          {summary.data.allergies.length > 0 ? (
            <div className="space-y-1">
              <span className="font-semibold text-rose-800">
                ⚠ Allergies ({summary.data.allergies.length})
              </span>
              <ul className="text-rose-700">
                {summary.data.allergies.map((allergy) => (
                  <li key={allergy.id}>
                    <span className="font-medium">{allergy.substance}</span>
                    {allergy.reaction && <> — {allergy.reaction}</>} ({allergy.severity})
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <span className="text-emerald-700">No known allergies documented.</span>
          )}
          {summary.data.conditions.length > 0 && (
            <p className="mt-1 text-slate-600">
              Chronic: {summary.data.conditions.map((c) => c.condition).join(", ")}
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          {isClinical && <VitalsPanel me={me} visit={visit} />}
          {me.roles.includes("Doctor") && <ConsultationPanel me={me} visit={visit} />}
        </div>
        <div className="space-y-4">
          {isDesk && <InvoicePanel me={me} visit={visit} />}
          {!isDesk && !isClinical && (
            <p className="text-sm text-slate-500">Nothing to show for your role.</p>
          )}
        </div>
      </div>
    </div>
  );
}
