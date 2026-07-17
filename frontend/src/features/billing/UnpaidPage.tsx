import { Link } from "react-router-dom";
import { ErrorNotice, formatDate } from "../../ui/format";
import { useUnpaidBalances } from "./useBilling";

/** Per-patient outstanding balances (FRD §5.7), most owed first. Encounter
 * status separates walked-out debt from visits still in progress. */
export default function UnpaidPage() {
  const unpaid = useUnpaidBalances();

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Unpaid balances</h1>
      <ErrorNotice error={unpaid.error} />

      {unpaid.data && unpaid.data.count === 0 && (
        <p className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
          No outstanding balances. 🎉
        </p>
      )}

      {(unpaid.data?.results ?? []).map((entry) => (
        <div key={entry.patient.id} className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
            <Link
              to={`/patients/${entry.patient.id}`}
              className="font-medium text-slate-800 hover:underline"
            >
              {entry.patient.full_name}
              <span className="ml-2 text-xs font-normal text-slate-500">
                {entry.patient.mrn}
              </span>
            </Link>
            <span className="text-lg font-semibold tabular-nums text-rose-700">
              {entry.outstanding}
            </span>
          </div>
          <div className="divide-y divide-slate-50 px-5 py-2 text-sm">
            {entry.invoices.map((invoice) => (
              <div key={invoice.id} className="flex items-center justify-between py-1.5">
                <span className="text-slate-600">
                  {invoice.number} · {formatDate(invoice.issued_at)}
                  <span className="ml-2 text-xs text-slate-400">
                    visit {invoice.encounter_status.replace(/_/g, " ")}
                  </span>
                </span>
                <span className="tabular-nums text-slate-700">
                  {invoice.outstanding}
                  <span className="ml-2 text-xs text-slate-400">
                    of {invoice.total} (paid {invoice.paid})
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
