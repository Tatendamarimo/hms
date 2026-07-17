import { useState } from "react";
import type { Encounter, InvoiceDetail, Me } from "../../api/types";
import { ErrorNotice, InvoiceStatusBadge } from "../../ui/format";
import { Dialog, PrintLink, SmallButton } from "./ConsultationPanel";
import {
  useAddInvoiceItem,
  useBillableServices,
  useInvoice,
  useRecordPayment,
  useReversePayment,
  useVoidInvoiceItem,
} from "./useVisit";

export default function InvoicePanel({ me, visit }: { me: Me; visit: Encounter }) {
  const invoiceId = visit.invoice?.id;
  const invoice = useInvoice(invoiceId, true);
  const [adding, setAdding] = useState(false);
  const [paying, setPaying] = useState(false);
  const [discounting, setDiscounting] = useState(false);

  const isTill = me.roles.includes("Cashier") || me.roles.includes("Receptionist");
  const isAdmin = me.roles.includes("Admin");
  const canReverse = me.roles.includes("Cashier") || isAdmin;
  const voidItem = useVoidInvoiceItem(invoiceId);
  const reverse = useReversePayment();

  if (!visit.invoice) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="font-semibold text-slate-800">Invoice</h2>
        <p className="mt-2 text-sm text-slate-400">No invoice on this visit yet.</p>
      </section>
    );
  }

  const detail = invoice.data;

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
          Invoice
          <InvoiceStatusBadge status={(detail ?? visit.invoice).status} />
        </h2>
        <PrintLink href={`/print/invoice/${visit.invoice.id}/`} />
      </div>

      {detail && (
        <>
          <div className="space-y-1 text-sm">
            {detail.items.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-2">
                <span
                  className={
                    item.item_type === "discount" ? "text-emerald-700" : "text-slate-700"
                  }
                >
                  {item.description}
                  {item.quantity > 1 && ` ×${item.quantity}`}
                </span>
                <span className="flex items-center gap-2">
                  <span className="tabular-nums text-slate-700">{item.line_total}</span>
                  {isAdmin && item.item_type !== "discount" && (
                    <button
                      onClick={() => {
                        const reason = window.prompt("Void reason (required):");
                        if (reason) voidItem.mutate({ itemId: item.id, reason });
                      }}
                      className="text-xs text-rose-500 hover:underline"
                    >
                      void
                    </button>
                  )}
                </span>
              </div>
            ))}
            {detail.items.length === 0 && (
              <p className="text-slate-400">No charges yet.</p>
            )}
          </div>

          <div className="space-y-0.5 border-t border-slate-100 pt-2 text-sm">
            <Row label="Total" value={detail.total} />
            <Row label="Paid" value={detail.paid_total} />
            <Row label="Balance" value={detail.balance} bold />
          </div>

          {detail.payments.length > 0 && (
            <div className="space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-600">
              {detail.payments.map((payment) => (
                <div key={payment.id} className="flex items-center justify-between">
                  <span>
                    {payment.receipt_number} · {payment.method} · {payment.amount}
                    {payment.reversal_of !== null && (
                      <span className="ml-1 text-rose-600">(reversal)</span>
                    )}
                  </span>
                  <span className="flex gap-2">
                    <PrintLink href={`/print/receipt/${payment.id}/`} />
                    {canReverse && payment.reversal_of === null && (
                      <button
                        onClick={() => {
                          const reason = window.prompt("Reversal reason (required):");
                          if (reason) reverse.mutate({ paymentId: payment.id, reason });
                        }}
                        className="text-rose-600 hover:underline"
                      >
                        reverse
                      </button>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}

          <ErrorNotice error={voidItem.error ?? reverse.error} />

          <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            {isTill && <SmallButton onClick={() => setAdding(true)}>+ Service</SmallButton>}
            {isAdmin && (
              <SmallButton onClick={() => setDiscounting(true)}>+ Discount</SmallButton>
            )}
            {isTill && Number(detail.balance) > 0 && (
              <button
                onClick={() => setPaying(true)}
                className="rounded-md bg-emerald-700 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-600"
              >
                Record payment
              </button>
            )}
          </div>
        </>
      )}

      {adding && invoiceId !== undefined && (
        <AddServiceDialog invoiceId={invoiceId} onClose={() => setAdding(false)} />
      )}
      {discounting && invoiceId !== undefined && (
        <DiscountDialog invoiceId={invoiceId} onClose={() => setDiscounting(false)} />
      )}
      {paying && invoiceId !== undefined && detail && (
        <PaymentDialog invoiceId={invoiceId} detail={detail} onClose={() => setPaying(false)} />
      )}
    </section>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between ${bold ? "font-semibold text-slate-800" : "text-slate-600"}`}>
      <span>{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}

function AddServiceDialog({ invoiceId, onClose }: { invoiceId: number; onClose: () => void }) {
  const services = useBillableServices();
  const add = useAddInvoiceItem(invoiceId);
  const [serviceId, setServiceId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1);

  return (
    <Dialog title="Add catalog service" onClose={onClose}>
      <select
        value={serviceId}
        onChange={(e) => setServiceId(e.target.value === "" ? "" : Number(e.target.value))}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      >
        <option value="">Choose a service…</option>
        {(services.data ?? []).map((service) => (
          <option key={service.id} value={service.id}>
            {service.name} — {service.current_price}
          </option>
        ))}
      </select>
      <label className="block text-sm">
        <span className="text-slate-600">Quantity</span>
        <input
          type="number"
          min={1}
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <ErrorNotice error={add.error} />
      <button
        onClick={() =>
          add.mutate({ service_item: serviceId, quantity }, { onSuccess: onClose })
        }
        disabled={add.isPending || serviceId === ""}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        Add to invoice
      </button>
    </Dialog>
  );
}

function DiscountDialog({ invoiceId, onClose }: { invoiceId: number; onClose: () => void }) {
  const add = useAddInvoiceItem(invoiceId);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");

  return (
    <Dialog title="Apply discount" onClose={onClose}>
      <label className="block text-sm">
        <span className="text-slate-600">Amount</span>
        <input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          inputMode="decimal"
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="text-slate-600">Reason (required, audited)</span>
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <ErrorNotice error={add.error} />
      <button
        onClick={() =>
          add.mutate(
            { item_type: "discount", amount, reason },
            { onSuccess: onClose },
          )
        }
        disabled={add.isPending || !amount || !reason.trim()}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        Apply discount
      </button>
    </Dialog>
  );
}

function PaymentDialog({
  invoiceId,
  detail,
  onClose,
}: {
  invoiceId: number;
  detail: InvoiceDetail;
  onClose: () => void;
}) {
  const pay = useRecordPayment(invoiceId);
  const [amount, setAmount] = useState(detail.balance);
  const [method, setMethod] = useState("cash");
  const [reference, setReference] = useState("");

  return (
    <Dialog title={`Record payment (balance ${detail.balance})`} onClose={onClose}>
      <label className="block text-sm">
        <span className="text-slate-600">Amount</span>
        <input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          inputMode="decimal"
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        <span className="text-slate-600">Method</span>
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        >
          <option value="cash">Cash</option>
          <option value="ecocash">EcoCash</option>
          <option value="card">Card</option>
          <option value="other">Other</option>
        </select>
      </label>
      {method !== "cash" && (
        <label className="block text-sm">
          <span className="text-slate-600">Reference</span>
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </label>
      )}
      <ErrorNotice error={pay.error} />
      <button
        onClick={() => pay.mutate({ amount, method, reference }, { onSuccess: onClose })}
        disabled={pay.isPending || !amount}
        className="w-full rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
      >
        {pay.isPending ? "Recording…" : "Record payment"}
      </button>
    </Dialog>
  );
}
