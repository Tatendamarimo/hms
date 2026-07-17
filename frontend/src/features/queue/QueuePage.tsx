import { useState } from "react";
import { Link } from "react-router-dom";
import type { Encounter, Me } from "../../api/types";
import {
  EncounterStatusBadge,
  ErrorNotice,
  InvoiceStatusBadge,
  formatTime,
} from "../../ui/format";
import CheckInDialog from "./CheckInDialog";
import { useQueue, useTransition } from "./useQueue";

/** Role-aware next steps offered per row (design §5). The server's state
 * machine stays the authority — a rejected transition surfaces its reason. */
function actionsFor(me: Me, encounter: Encounter) {
  const actions: { label: string; to: Encounter["status"]; needsReason?: boolean }[] = [];
  const roles = new Set(me.roles);
  if (roles.has("Nurse")) {
    if (encounter.status === "waiting") actions.push({ label: "Start triage", to: "in_triage" });
    if (encounter.status === "in_triage")
      actions.push({ label: "Ready for doctor", to: "awaiting_doctor" });
  }
  if (roles.has("Doctor") && encounter.status === "awaiting_doctor") {
    actions.push({ label: "Claim", to: "in_consultation" });
  }
  if (roles.has("Receptionist") && encounter.status === "waiting") {
    actions.push({ label: "Mark LWBS", to: "left_without_being_seen", needsReason: true });
  }
  return actions;
}

export default function QueuePage({ me }: { me: Me }) {
  const queue = useQueue();
  const transition = useTransition();
  const [checkInOpen, setCheckInOpen] = useState(false);
  const isReception = me.roles.includes("Receptionist");

  const act = (encounter: Encounter, to: Encounter["status"], needsReason?: boolean) => {
    let reason = "";
    if (needsReason) {
      const entered = window.prompt("Reason (required):", "");
      if (entered === null) return;
      reason = entered;
    }
    transition.mutate({ encounterId: encounter.id, to, reason });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-800">Queue</h1>
        {isReception && (
          <button
            onClick={() => setCheckInOpen(true)}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Check in patient
          </button>
        )}
      </div>

      <ErrorNotice error={transition.error} />

      {queue.isLoading ? (
        <div className="p-10 text-center text-slate-400">Loading queue…</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Patient</th>
                <th className="px-4 py-3">Arrived</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Doctor</th>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {(queue.data ?? []).map((encounter) => (
                <tr
                  key={encounter.id}
                  className={`border-b border-slate-100 last:border-0 ${
                    encounter.type === "emergency" ? "bg-rose-50" : ""
                  }`}
                >
                  <td className="px-4 py-3">
                    <Link to={`/visit/${encounter.id}`} className="block">
                      <div className="font-medium text-slate-800 hover:underline">
                        {encounter.patient_name}
                      </div>
                      <div className="text-xs text-slate-500">{encounter.patient_mrn}</div>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatTime(encounter.arrived_at)}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {encounter.type === "emergency" ? (
                      <span className="font-semibold text-rose-700">Emergency</span>
                    ) : (
                      encounter.type.replace("_", " ")
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <EncounterStatusBadge status={encounter.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {encounter.assigned_doctor_name ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    {encounter.invoice ? (
                      <div className="flex items-center gap-2">
                        <InvoiceStatusBadge status={encounter.invoice.status} />
                        {encounter.invoice.status !== "paid" && (
                          <span className="text-xs text-slate-500">
                            owes {encounter.invoice.balance}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {actionsFor(me, encounter).map((action) => (
                        <button
                          key={action.to}
                          disabled={transition.isPending}
                          onClick={() => act(encounter, action.to, action.needsReason)}
                          className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {queue.data?.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-400">
                    No open visits.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {checkInOpen && <CheckInDialog onClose={() => setCheckInOpen(false)} />}
    </div>
  );
}
