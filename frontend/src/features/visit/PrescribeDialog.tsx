import { useState } from "react";
import type { Encounter, Medication } from "../../api/types";
import { ErrorNotice } from "../../ui/format";
import { Dialog, allergyWarningsFrom } from "./ConsultationPanel";
import {
  useMedications,
  usePrescribe,
  type PrescriptionItemInput,
} from "./useVisit";

const EMPTY_ITEM: PrescriptionItemInput = {
  medication: null,
  medication_note: "",
  dose: "",
  frequency: "",
  duration_days: 1,
  quantity: 1,
  instructions: "",
};

/** Prescription entry with the allergy guard: a 409 lists the matched
 * allergies, and prescribing anyway requires acknowledging each one
 * explicitly (FRD §5.3 — the acknowledgement is loud-audited server-side). */
export default function PrescribeDialog({
  visit,
  consultationId,
  onClose,
}: {
  visit: Encounter;
  consultationId: number;
  onClose: () => void;
}) {
  const prescribe = usePrescribe(visit.id);
  const [items, setItems] = useState<(PrescriptionItemInput & { label: string })[]>([]);
  const [draft, setDraft] = useState({ ...EMPTY_ITEM, label: "" });
  const [medQuery, setMedQuery] = useState("");
  const medications = useMedications(medQuery);
  const [acknowledged, setAcknowledged] = useState<number[]>([]);

  const warnings = allergyWarningsFrom(prescribe.error);

  const pickMedication = (medication: Medication) => {
    setDraft({ ...draft, medication: medication.id, medication_note: "", label: medication.label });
    setMedQuery("");
  };

  const addItem = () => {
    if (!draft.dose || !draft.frequency) return;
    if (draft.medication === null && !draft.medication_note.trim()) return;
    setItems([...items, draft]);
    setDraft({ ...EMPTY_ITEM, label: "" });
  };

  const submit = (withAcknowledgements: boolean) => {
    prescribe.mutate(
      {
        consultationId,
        items: items.map(({ label: _label, ...item }) => item),
        acknowledged_allergy_ids: withAcknowledgements ? acknowledged : [],
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Dialog title="New prescription" onClose={onClose}>
      {items.length > 0 && (
        <ul className="space-y-1 text-sm">
          {items.map((item, index) => (
            <li
              key={index}
              className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5"
            >
              <span className="text-slate-700">
                {item.label || item.medication_note} — {item.dose}, {item.frequency},{" "}
                {item.duration_days}d ×{item.quantity}
              </span>
              <button
                onClick={() => setItems(items.filter((_, i) => i !== index))}
                className="text-xs text-rose-600 hover:underline"
              >
                remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-2 rounded-md border border-slate-200 p-3">
        {draft.medication === null ? (
          <div className="relative">
            <input
              value={medQuery || draft.medication_note}
              onChange={(e) => {
                setMedQuery(e.target.value);
                setDraft({ ...draft, medication_note: e.target.value });
              }}
              placeholder="Search catalog or type medication…"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            {medQuery.trim().length >= 2 && (medications.data?.length ?? 0) > 0 && (
              <div className="absolute z-10 mt-1 max-h-40 w-full overflow-y-auto rounded-md border border-slate-200 bg-white shadow-lg">
                {medications.data?.map((medication) => (
                  <button
                    key={medication.id}
                    onClick={() => pickMedication(medication)}
                    className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                  >
                    {medication.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm">
            <span className="text-slate-700">{draft.label}</span>
            <button
              onClick={() => setDraft({ ...draft, medication: null, label: "" })}
              className="text-xs text-slate-500 underline"
            >
              change
            </button>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <input
            value={draft.dose}
            onChange={(e) => setDraft({ ...draft, dose: e.target.value })}
            placeholder="Dose (e.g. 500mg) *"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
          <input
            value={draft.frequency}
            onChange={(e) => setDraft({ ...draft, frequency: e.target.value })}
            placeholder="Frequency (e.g. TDS) *"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
          <label className="text-xs text-slate-500">
            Days
            <input
              type="number"
              min={1}
              value={draft.duration_days}
              onChange={(e) => setDraft({ ...draft, duration_days: Number(e.target.value) })}
              className="mt-0.5 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs text-slate-500">
            Quantity
            <input
              type="number"
              min={1}
              value={draft.quantity}
              onChange={(e) => setDraft({ ...draft, quantity: Number(e.target.value) })}
              className="mt-0.5 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
          </label>
        </div>
        <input
          value={draft.instructions}
          onChange={(e) => setDraft({ ...draft, instructions: e.target.value })}
          placeholder="Instructions (optional)"
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          onClick={addItem}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Add item
        </button>
      </div>

      {warnings.length > 0 ? (
        <div className="space-y-2 rounded-md border border-rose-300 bg-rose-50 p-3 text-sm">
          <p className="font-semibold text-rose-800">
            ⚠ Allergy match — prescribing anyway is recorded with your acknowledgement:
          </p>
          {warnings.map((warning) => (
            <label key={`${warning.allergy_id}-${warning.medication}`} className="flex items-center gap-2 text-rose-700">
              <input
                type="checkbox"
                checked={acknowledged.includes(warning.allergy_id)}
                onChange={(e) =>
                  setAcknowledged(
                    e.target.checked
                      ? [...acknowledged, warning.allergy_id]
                      : acknowledged.filter((id) => id !== warning.allergy_id),
                  )
                }
              />
              {warning.medication} matches documented allergy “{warning.substance}”
            </label>
          ))}
          <button
            onClick={() => submit(true)}
            disabled={
              prescribe.isPending ||
              !warnings.every((warning) => acknowledged.includes(warning.allergy_id))
            }
            className="rounded-md border border-rose-400 px-3 py-1.5 text-xs font-medium text-rose-800 hover:bg-rose-100 disabled:opacity-50"
          >
            Prescribe anyway (audited)
          </button>
        </div>
      ) : (
        prescribe.error && <ErrorNotice error={prescribe.error} />
      )}

      <button
        onClick={() => submit(false)}
        disabled={prescribe.isPending || items.length === 0}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {prescribe.isPending ? "Saving…" : `Issue prescription (${items.length} item${items.length === 1 ? "" : "s"})`}
      </button>
    </Dialog>
  );
}
