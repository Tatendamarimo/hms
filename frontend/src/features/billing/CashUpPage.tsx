import { useState } from "react";
import { ErrorNotice, formatDate, formatTime } from "../../ui/format";
import { useCloseCashUp, useDrawer, type CashUp } from "./useBilling";

/** End-of-day drawer reconciliation (FRD §5.7): the preview is the open
 * drawer; count-and-close happens in one step, variance must be explained. */
export default function CashUpPage() {
  const drawer = useDrawer();
  const close = useCloseCashUp();
  const [counted, setCounted] = useState("");
  const [notes, setNotes] = useState("");
  const [closed, setClosed] = useState<CashUp | null>(null);

  const preview = drawer.data;
  const variance =
    preview && counted !== ""
      ? (Number(counted) - Number(preview.expected_total)).toFixed(2)
      : null;

  const submit = () => {
    close.mutate(
      { counted_total: counted, notes },
      {
        onSuccess: (cashUp) => {
          setClosed(cashUp);
          setCounted("");
          setNotes("");
        },
      },
    );
  };

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Cash-up</h1>

      {closed && (
        <div className="space-y-1 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <p className="font-semibold">Cash-up closed.</p>
          <p>
            Expected {closed.expected_total} · counted {closed.counted_total} · variance{" "}
            {closed.variance}
          </p>
          <p className="text-xs">
            Period {formatDate(closed.period_start)} {formatTime(closed.period_start)} →{" "}
            {formatTime(closed.period_end)}
          </p>
        </div>
      )}

      {preview && (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-slate-600">Expected in drawer (cash)</span>
            <span className="text-2xl font-semibold tabular-nums text-slate-800">
              {preview.expected_total}
            </span>
          </div>
          <p className="text-xs text-slate-500">
            {preview.payment_count} cash movement(s)
            {preview.period_start && (
              <>
                {" "}
                since {formatDate(preview.period_start)} {formatTime(preview.period_start)}
              </>
            )}
            {preview.previous_cash_up_at && (
              <> · previous cash-up {formatDate(preview.previous_cash_up_at)}</>
            )}
          </p>

          {preview.payments.length > 0 && (
            <div className="max-h-56 space-y-1 overflow-y-auto border-t border-slate-100 pt-2 text-xs text-slate-600">
              {preview.payments.map((payment) => (
                <div key={payment.id} className="flex justify-between">
                  <span>
                    {payment.receipt_number}
                    {payment.reversal_of !== null && (
                      <span className="ml-1 text-rose-600">(reversal — cash out)</span>
                    )}
                  </span>
                  <span className="tabular-nums">
                    {payment.reversal_of !== null ? "−" : ""}
                    {payment.amount}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-3 border-t border-slate-100 pt-3">
            <label className="block text-sm">
              <span className="text-slate-600">Counted total</span>
              <input
                value={counted}
                onChange={(e) => setCounted(e.target.value)}
                inputMode="decimal"
                placeholder="What is actually in the drawer"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              />
            </label>
            {variance !== null && variance !== "0.00" && (
              <p className="text-sm font-medium text-amber-700">
                Variance {variance} — a note is required.
              </p>
            )}
            <label className="block text-sm">
              <span className="text-slate-600">Notes</span>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Required when counted ≠ expected"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              />
            </label>
            <ErrorNotice error={close.error} />
            <button
              onClick={submit}
              disabled={close.isPending || counted === ""}
              className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {close.isPending ? "Closing…" : "Count & close"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
