import { useState } from "react";
import type { Encounter, Me, Vitals } from "../../api/types";
import { ErrorNotice, formatTime } from "../../ui/format";
import { useRecordVitals, useVitals } from "./useVisit";

const EMPTY = {
  systolic: "",
  diastolic: "",
  pulse: "",
  temperature: "",
  weight_kg: "",
  height_cm: "",
  spo2: "",
  symptoms: "",
};

export default function VitalsPanel({ me, visit }: { me: Me; visit: Encounter }) {
  const vitals = useVitals(visit.id, true);
  const record = useRecordVitals(visit.id);
  const [form, setForm] = useState(EMPTY);
  const canRecord = me.roles.includes("Nurse") && visit.status === "in_triage";

  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  const submit = () => {
    const body: Record<string, unknown> = { symptoms: form.symptoms };
    for (const key of ["systolic", "diastolic", "pulse", "temperature"] as const) {
      body[key] = form[key];
    }
    for (const key of ["weight_kg", "height_cm", "spo2"] as const) {
      if (form[key] !== "") body[key] = form[key];
    }
    record.mutate(body, { onSuccess: () => setForm(EMPTY) });
  };

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="font-semibold text-slate-800">Vitals</h2>

      {(vitals.data ?? []).map((entry) => (
        <VitalsRow key={entry.id} entry={entry} />
      ))}
      {vitals.data?.length === 0 && (
        <p className="text-sm text-slate-400">No vitals recorded yet.</p>
      )}

      {canRecord && (
        <div className="space-y-3 border-t border-slate-100 pt-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <LabeledInput label="Systolic *" value={form.systolic} onChange={set("systolic")} />
            <LabeledInput label="Diastolic *" value={form.diastolic} onChange={set("diastolic")} />
            <LabeledInput label="Pulse *" value={form.pulse} onChange={set("pulse")} />
            <LabeledInput
              label="Temp °C *"
              value={form.temperature}
              onChange={set("temperature")}
            />
            <LabeledInput label="Weight kg" value={form.weight_kg} onChange={set("weight_kg")} />
            <LabeledInput label="Height cm" value={form.height_cm} onChange={set("height_cm")} />
            <LabeledInput label="SpO₂ %" value={form.spo2} onChange={set("spo2")} />
          </div>
          <label className="block text-sm">
            <span className="text-slate-600">Presenting symptoms</span>
            <input
              value={form.symptoms}
              onChange={set("symptoms")}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <ErrorNotice error={record.error} />
          <button
            onClick={submit}
            disabled={record.isPending}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {record.isPending ? "Saving…" : "Record vitals (moves to Awaiting doctor)"}
          </button>
        </div>
      )}
    </section>
  );
}

function VitalsRow({ entry }: { entry: Vitals }) {
  const flagged = new Set(entry.flags.map((flag) => flag.field));
  return (
    <div className="rounded-md bg-slate-50 px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="text-xs text-slate-400">{formatTime(entry.created_at)}</span>
        <Metric
          label="BP"
          value={`${entry.systolic}/${entry.diastolic}`}
          flagged={flagged.has("systolic") || flagged.has("diastolic")}
        />
        <Metric label="Pulse" value={String(entry.pulse)} flagged={flagged.has("pulse")} />
        <Metric
          label="Temp"
          value={`${entry.temperature}°C`}
          flagged={flagged.has("temperature")}
        />
        {entry.spo2 !== null && (
          <Metric label="SpO₂" value={`${entry.spo2}%`} flagged={flagged.has("spo2")} />
        )}
        {entry.weight_kg && <Metric label="Wt" value={`${entry.weight_kg}kg`} />}
        {entry.recorded_by_name && (
          <span className="text-xs text-slate-400">by {entry.recorded_by_name}</span>
        )}
      </div>
      {entry.flags.length > 0 && (
        <p className="mt-1 text-xs font-medium text-rose-600">
          Flagged:{" "}
          {entry.flags
            .map((flag) => `${flag.field} ${flag.value} (${flag.direction}, ref ${flag.low}–${flag.high})`)
            .join(" · ")}
        </p>
      )}
      {entry.symptoms && <p className="mt-1 text-xs text-slate-600">{entry.symptoms}</p>}
    </div>
  );
}

function Metric({ label, value, flagged }: { label: string; value: string; flagged?: boolean }) {
  return (
    <span className={flagged ? "font-semibold text-rose-700" : "text-slate-700"}>
      <span className="text-xs text-slate-400">{label} </span>
      {value}
    </span>
  );
}

function LabeledInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="text-xs text-slate-600">{label}</span>
      <input
        value={value}
        onChange={onChange}
        inputMode="decimal"
        className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5"
      />
    </label>
  );
}
