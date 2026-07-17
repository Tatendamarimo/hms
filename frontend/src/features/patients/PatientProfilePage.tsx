import { useState } from "react";
import { useParams } from "react-router-dom";
import type { Me } from "../../api/types";
import {
  EncounterStatusBadge,
  ErrorNotice,
  formatDate,
  formatTime,
  InvoiceStatusBadge,
} from "../../ui/format";
import PatientForm, { fieldErrors, fieldsFrom, type PatientFields } from "./PatientForm";
import { usePatient, useTimeline, useUpdatePatient } from "./usePatients";

export default function PatientProfilePage({ me }: { me: Me }) {
  const { id } = useParams();
  const patientId = Number(id);
  const patient = usePatient(patientId);
  const canEdit = me.roles.includes("Receptionist");
  const isClinical = me.roles.includes("Nurse") || me.roles.includes("Doctor");
  const timeline = useTimeline(patientId, isClinical);
  const [editing, setEditing] = useState(false);

  if (patient.isLoading) {
    return <div className="p-10 text-center text-slate-400">Loading…</div>;
  }
  if (!patient.data) {
    return <ErrorNotice error={patient.error ?? "Patient not found."} />;
  }
  const record = patient.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-800">
            {record.first_name} {record.last_name}
          </h1>
          <p className="text-sm text-slate-500">
            {record.mrn} · {record.sex === "M" ? "Male" : "Female"} · {record.age}y · DOB{" "}
            {formatDate(record.date_of_birth)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`/print/registration/${record.id}/`}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Print registration
          </a>
          {canEdit && !editing && (
            <button
              onClick={() => setEditing(true)}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              Edit details
            </button>
          )}
        </div>
      </div>

      {editing ? (
        <EditPanel
          patientId={patientId}
          initial={fieldsFrom(record)}
          onDone={() => setEditing(false)}
        />
      ) : (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 rounded-xl border border-slate-200 bg-white p-6 text-sm sm:grid-cols-3">
          <Item label="Phone" value={record.phone} />
          <Item label="National ID" value={record.national_id} />
          <Item label="Address" value={record.address} />
          <Item label="Next of kin" value={record.next_of_kin_name} />
          <Item label="Next of kin phone" value={record.next_of_kin_phone} />
          <Item label="Blood group" value={record.blood_group} />
          <Item label="Medical aid" value={record.medical_aid_provider} />
          <Item label="Medical aid no." value={record.medical_aid_number} />
          <Item label="Registered" value={formatDate(record.created_at)} />
        </dl>
      )}

      {isClinical && (
        <section className="space-y-2">
          <h2 className="font-semibold text-slate-800">Visit history</h2>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            {(timeline.data ?? []).map((visit) => (
              <div
                key={visit.id}
                className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-sm last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="text-slate-600">
                    {formatDate(visit.arrived_at)} {formatTime(visit.arrived_at)}
                  </span>
                  <EncounterStatusBadge status={visit.status} />
                  <span className="text-slate-500">{visit.type.replace("_", " ")}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {visit.assigned_doctor_name && <span>{visit.assigned_doctor_name}</span>}
                  {visit.invoice && <InvoiceStatusBadge status={visit.invoice.status} />}
                </div>
              </div>
            ))}
            {timeline.data?.length === 0 && (
              <div className="px-4 py-6 text-center text-sm text-slate-400">No visits yet.</div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase text-slate-400">{label}</dt>
      <dd className="text-slate-700">{value || "—"}</dd>
    </div>
  );
}

function EditPanel({
  patientId,
  initial,
  onDone,
}: {
  patientId: number;
  initial: PatientFields;
  onDone: () => void;
}) {
  const [fields, setFields] = useState(initial);
  const update = useUpdatePatient(patientId);

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
      <PatientForm value={fields} onChange={setFields} errors={fieldErrors(update.error)} />
      {update.error && Object.keys(fieldErrors(update.error)).length === 0 && (
        <ErrorNotice error={update.error} />
      )}
      <div className="flex gap-3">
        <button
          onClick={() => update.mutate(fields, { onSuccess: onDone })}
          disabled={update.isPending}
          className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {update.isPending ? "Saving…" : "Save"}
        </button>
        <button
          onClick={onDone}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
