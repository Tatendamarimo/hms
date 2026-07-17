import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import type {
  AllergyWarning,
  Consultation,
  Encounter,
  Me,
} from "../../api/types";
import { ErrorNotice, formatDate } from "../../ui/format";
import LabOrdersSection from "./LabOrdersSection";
import PrescribeDialog from "./PrescribeDialog";
import {
  useAddDiagnosis,
  useCancelPrescription,
  useConsultationAction,
  useConsultations,
  useCreateDraft,
  useCreateReferral,
  useCreateSickNote,
  useDiagnosisSearch,
  useEditConsultation,
} from "./useVisit";

export default function ConsultationPanel({ me, visit }: { me: Me; visit: Encounter }) {
  const consultations = useConsultations(visit.id, true);
  const createDraft = useCreateDraft(visit.id);

  const chain = consultations.data ?? [];
  const current = chain.length > 0 ? chain[chain.length - 1] : null;

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800">Consultation</h2>
        {current === null && visit.status === "in_consultation" && (
          <button
            onClick={() => createDraft.mutate()}
            disabled={createDraft.isPending}
            className="rounded-md bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            Start consultation
          </button>
        )}
      </div>
      <ErrorNotice error={createDraft.error} />

      {current === null ? (
        <p className="text-sm text-slate-400">
          {visit.status === "in_consultation"
            ? "No consultation started yet."
            : "The consultation opens once the visit is claimed."}
        </p>
      ) : (
        <ConsultationEditor me={me} visit={visit} consultation={current} chain={chain} />
      )}
    </section>
  );
}

function ConsultationEditor({
  me,
  visit,
  consultation,
  chain,
}: {
  me: Me;
  visit: Encounter;
  consultation: Consultation;
  chain: Consultation[];
}) {
  const isDraft = consultation.status === "draft";
  const isMine = consultation.doctor_name === me.full_name;
  const edit = useEditConsultation(visit.id);
  const action = useConsultationAction(visit.id);
  const [fields, setFields] = useState({
    presenting_complaint: consultation.presenting_complaint,
    clinical_notes: consultation.clinical_notes,
    treatment_plan: consultation.treatment_plan,
  });
  useEffect(() => {
    setFields({
      presenting_complaint: consultation.presenting_complaint,
      clinical_notes: consultation.clinical_notes,
      treatment_plan: consultation.treatment_plan,
    });
  }, [consultation.id, consultation.presenting_complaint, consultation.clinical_notes, consultation.treatment_plan]);

  const dirty =
    fields.presenting_complaint !== consultation.presenting_complaint ||
    fields.clinical_notes !== consultation.clinical_notes ||
    fields.treatment_plan !== consultation.treatment_plan;

  const sign = () => {
    if (dirty) {
      edit.mutate(
        { id: consultation.id, ...fields },
        { onSuccess: () => action.mutate({ id: consultation.id, action: "sign" }) },
      );
    } else {
      action.mutate({ id: consultation.id, action: "sign" });
    }
  };

  const amend = () => {
    const reason = window.prompt("Amendment reason (required):");
    if (!reason) return;
    action.mutate({ id: consultation.id, action: "amend", body: { reason } });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span>
          v{consultation.version} · {consultation.doctor_name}
        </span>
        {consultation.status === "signed" ? (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800">
            Signed {consultation.signed_at && formatDate(consultation.signed_at)}
          </span>
        ) : (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800">
            Draft
          </span>
        )}
        {consultation.amendment_reason && (
          <span>Amendment: {consultation.amendment_reason}</span>
        )}
        {chain.length > 1 && <span>({chain.length} versions)</span>}
      </div>

      {(["presenting_complaint", "clinical_notes", "treatment_plan"] as const).map((key) => (
        <label key={key} className="block text-sm">
          <span className="capitalize text-slate-600">{key.replace(/_/g, " ")}</span>
          <textarea
            value={fields[key]}
            onChange={(e) => setFields({ ...fields, [key]: e.target.value })}
            disabled={!isDraft || !isMine}
            rows={key === "clinical_notes" ? 4 : 2}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-50 disabled:text-slate-500"
          />
        </label>
      ))}

      <DiagnosesSection visit={visit} consultation={consultation} editable={isDraft && isMine} />

      <ErrorNotice error={edit.error ?? action.error} />

      <div className="flex flex-wrap gap-2">
        {isDraft && isMine && (
          <>
            {dirty && (
              <button
                onClick={() => edit.mutate({ id: consultation.id, ...fields })}
                disabled={edit.isPending}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Save draft
              </button>
            )}
            <button
              onClick={sign}
              disabled={action.isPending || edit.isPending}
              className="rounded-md bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
            >
              Sign (locks the record)
            </button>
          </>
        )}
        {consultation.status === "signed" && isMine && !consultation.amended_by_id && (
          <button
            onClick={amend}
            disabled={action.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Amend (new version)
          </button>
        )}
      </div>

      <DocumentsSection me={me} visit={visit} consultation={consultation} isMine={isMine} />
    </div>
  );
}

function DiagnosesSection({
  visit,
  consultation,
  editable,
}: {
  visit: Encounter;
  consultation: Consultation;
  editable: boolean;
}) {
  const [query, setQuery] = useState("");
  const search = useDiagnosisSearch(query);
  const add = useAddDiagnosis(visit.id);

  return (
    <div className="space-y-2">
      <span className="text-sm text-slate-600">Diagnoses (ICD-10)</span>
      <div className="flex flex-wrap gap-2">
        {consultation.diagnoses.map((diagnosis) => (
          <span
            key={diagnosis.id}
            className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
          >
            {diagnosis.code ? `${diagnosis.code} — ${diagnosis.name}` : diagnosis.free_text}
          </span>
        ))}
        {consultation.diagnoses.length === 0 && (
          <span className="text-xs text-slate-400">None recorded.</span>
        )}
      </div>
      {editable && (
        <div className="relative">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search ICD-10 or type free text…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {query.trim().length >= 2 && (
            <div className="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-slate-200 bg-white shadow-lg">
              {(search.data ?? []).map((hit) => (
                <button
                  key={hit.id}
                  onClick={() => {
                    add.mutate({
                      consultationId: consultation.id,
                      diagnosis: hit.id,
                      free_text: "",
                    });
                    setQuery("");
                  }}
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                >
                  <span className="font-mono text-xs text-slate-500">{hit.code}</span> {hit.name}
                </button>
              ))}
              <button
                onClick={() => {
                  add.mutate({
                    consultationId: consultation.id,
                    diagnosis: null,
                    free_text: query.trim(),
                  });
                  setQuery("");
                }}
                className="block w-full border-t border-slate-100 px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50"
              >
                Add “{query.trim()}” as free text
              </button>
            </div>
          )}
        </div>
      )}
      <ErrorNotice error={add.error} />
    </div>
  );
}

function DocumentsSection({
  me,
  visit,
  consultation,
  isMine,
}: {
  me: Me;
  visit: Encounter;
  consultation: Consultation;
  isMine: boolean;
}) {
  const [prescribing, setPrescribing] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [referralOpen, setReferralOpen] = useState(false);
  const cancelPrescription = useCancelPrescription(visit.id);
  const canWrite = isMine && me.roles.includes("Doctor") && consultation.status !== "cancelled";

  return (
    <div className="space-y-3 border-t border-slate-100 pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-700">Documents</span>
        {canWrite && (
          <>
            <SmallButton onClick={() => setPrescribing(true)}>+ Prescription</SmallButton>
            <SmallButton onClick={() => setNoteOpen(true)}>+ Sick note</SmallButton>
            <SmallButton onClick={() => setReferralOpen(true)}>+ Referral</SmallButton>
          </>
        )}
      </div>

      {consultation.prescriptions.map((prescription) => (
        <div key={prescription.id} className="rounded-md bg-slate-50 px-3 py-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-700">
              Prescription #{prescription.id}
              {prescription.status === "cancelled" && (
                <span className="ml-2 text-xs text-rose-600">cancelled</span>
              )}
            </span>
            <span className="flex gap-2 text-xs">
              <PrintLink href={`/print/prescription/${prescription.id}/`} />
              {canWrite && prescription.status !== "cancelled" && (
                <button
                  onClick={() => {
                    const reason = window.prompt("Cancel reason (required):");
                    if (reason)
                      cancelPrescription.mutate({ prescriptionId: prescription.id, reason });
                  }}
                  className="text-rose-600 hover:underline"
                >
                  cancel
                </button>
              )}
            </span>
          </div>
          <ul className="mt-1 text-xs text-slate-600">
            {prescription.items.map((item) => (
              <li key={item.id}>
                {item.display_name} — {item.dose}, {item.frequency}, {item.duration_days}d ×
                {item.quantity}
              </li>
            ))}
          </ul>
        </div>
      ))}

      {consultation.sick_notes.map((note) => (
        <div
          key={note.id}
          className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm"
        >
          <span className="text-slate-700">
            Sick note: unfit {note.unfit_from} → {note.unfit_to}
          </span>
          <PrintLink href={`/print/sick-note/${note.id}/`} />
        </div>
      ))}

      {consultation.referrals.map((referral) => (
        <div
          key={referral.id}
          className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm"
        >
          <span className="text-slate-700">Referral → {referral.destination_facility}</span>
          <PrintLink href={`/print/referral/${referral.id}/`} />
        </div>
      ))}

      <LabOrdersSection visit={visit} consultation={consultation} canWrite={canWrite} />

      {prescribing && (
        <PrescribeDialog
          visit={visit}
          consultationId={consultation.id}
          onClose={() => setPrescribing(false)}
        />
      )}
      {noteOpen && (
        <SickNoteDialog
          visitId={visit.id}
          consultationId={consultation.id}
          onClose={() => setNoteOpen(false)}
        />
      )}
      {referralOpen && (
        <ReferralDialog
          visitId={visit.id}
          consultationId={consultation.id}
          onClose={() => setReferralOpen(false)}
        />
      )}
    </div>
  );
}

function SickNoteDialog({
  visitId,
  consultationId,
  onClose,
}: {
  visitId: number;
  consultationId: number;
  onClose: () => void;
}) {
  const create = useCreateSickNote(visitId);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [remarks, setRemarks] = useState("");
  return (
    <Dialog title="Sick note" onClose={onClose}>
      <label className="block text-sm">
        <span className="text-slate-600">Unfit from</span>
        <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
      </label>
      <label className="block text-sm">
        <span className="text-slate-600">Unfit to</span>
        <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
      </label>
      <label className="block text-sm">
        <span className="text-slate-600">Remarks</span>
        <input value={remarks} onChange={(e) => setRemarks(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
      </label>
      <ErrorNotice error={create.error} />
      <button
        onClick={() =>
          create.mutate(
            { consultationId, unfit_from: from, unfit_to: to, remarks },
            { onSuccess: onClose },
          )
        }
        disabled={create.isPending}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        Issue sick note
      </button>
    </Dialog>
  );
}

function ReferralDialog({
  visitId,
  consultationId,
  onClose,
}: {
  visitId: number;
  consultationId: number;
  onClose: () => void;
}) {
  const create = useCreateReferral(visitId);
  const [facility, setFacility] = useState("");
  const [reason, setReason] = useState("");
  return (
    <Dialog title="Referral letter" onClose={onClose}>
      <label className="block text-sm">
        <span className="text-slate-600">Destination facility</span>
        <input value={facility} onChange={(e) => setFacility(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
      </label>
      <label className="block text-sm">
        <span className="text-slate-600">Reason</span>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
      </label>
      <ErrorNotice error={create.error} />
      <button
        onClick={() =>
          create.mutate(
            { consultationId, destination_facility: facility, reason },
            { onSuccess: onClose },
          )
        }
        disabled={create.isPending}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        Issue referral
      </button>
    </Dialog>
  );
}

export function Dialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-lg space-y-3 rounded-xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function SmallButton({
  onClick,
  children,
}: {
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
    >
      {children}
    </button>
  );
}

export function PrintLink({ href }: { href: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="text-slate-500 hover:underline">
      print
    </a>
  );
}

export function allergyWarningsFrom(error: unknown): AllergyWarning[] {
  if (error instanceof ApiError && error.status === 409 && error.body) {
    const body = error.body as { allergy_warnings?: AllergyWarning[] };
    return body.allergy_warnings ?? [];
  }
  return [];
}
