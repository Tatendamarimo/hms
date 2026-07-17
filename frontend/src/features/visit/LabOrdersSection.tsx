import { useState } from "react";
import type { Consultation, Encounter } from "../../api/types";
import { ErrorNotice } from "../../ui/format";
import { Dialog, PrintLink, SmallButton } from "./ConsultationPanel";
import {
  useCancelLabOrder,
  useCreateLabOrder,
  useLabOrders,
  useOrderableServices,
} from "./useVisit";

/** Lab/imaging orders bill the invoice as they are placed; cancelling the
 * order retracts its charges (slice 6 rule — never void the line directly). */
export default function LabOrdersSection({
  visit,
  consultation,
  canWrite,
}: {
  visit: Encounter;
  consultation: Consultation;
  canWrite: boolean;
}) {
  const orders = useLabOrders(consultation.id);
  const cancel = useCancelLabOrder(visit.id);
  const [ordering, setOrdering] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-slate-700">Lab / imaging orders</span>
        {canWrite && <SmallButton onClick={() => setOrdering(true)}>+ Order</SmallButton>}
      </div>

      {(orders.data ?? []).map((order) => (
        <div key={order.id} className="rounded-md bg-slate-50 px-3 py-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-700">
              Order #{order.id}
              {order.status === "cancelled" && (
                <span className="ml-2 text-xs text-rose-600">cancelled</span>
              )}
            </span>
            <span className="flex gap-2 text-xs">
              <PrintLink href={`/print/lab-request/${order.id}/`} />
              {canWrite && order.status !== "cancelled" && (
                <button
                  onClick={() => {
                    const reason = window.prompt(
                      "Cancel reason (required — also retracts the invoice charges):",
                    );
                    if (reason) cancel.mutate({ orderId: order.id, reason });
                  }}
                  className="text-rose-600 hover:underline"
                >
                  cancel
                </button>
              )}
            </span>
          </div>
          <ul className="mt-1 text-xs text-slate-600">
            {order.items.map((item) => (
              <li key={item.id}>
                {item.name} — {item.price}
              </li>
            ))}
          </ul>
          {order.instructions && (
            <p className="mt-1 text-xs text-slate-500">{order.instructions}</p>
          )}
        </div>
      ))}
      <ErrorNotice error={cancel.error} />

      {ordering && (
        <OrderDialog
          visitId={visit.id}
          consultationId={consultation.id}
          onClose={() => setOrdering(false)}
        />
      )}
    </div>
  );
}

function OrderDialog({
  visitId,
  consultationId,
  onClose,
}: {
  visitId: number;
  consultationId: number;
  onClose: () => void;
}) {
  const services = useOrderableServices();
  const create = useCreateLabOrder(visitId);
  const [selected, setSelected] = useState<number[]>([]);
  const [instructions, setInstructions] = useState("");

  const toggle = (id: number) =>
    setSelected(
      selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id],
    );

  return (
    <Dialog title="Order lab / imaging" onClose={onClose}>
      <div className="max-h-56 space-y-1 overflow-y-auto">
        {(services.data ?? []).map((service) => (
          <label
            key={service.id}
            className="flex items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-slate-50"
          >
            <span className="flex items-center gap-2 text-slate-700">
              <input
                type="checkbox"
                checked={selected.includes(service.id)}
                onChange={() => toggle(service.id)}
              />
              {service.name}
              <span className="text-xs uppercase text-slate-400">{service.type}</span>
            </span>
            <span className="text-xs text-slate-500">{service.current_price}</span>
          </label>
        ))}
        {services.data?.length === 0 && (
          <p className="px-3 py-4 text-center text-sm text-slate-400">
            No priced lab/imaging services in the catalog.
          </p>
        )}
      </div>
      <input
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
        placeholder="Instructions (optional)"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <ErrorNotice error={create.error} />
      <p className="text-xs text-slate-500">
        Ordering adds the charges to the visit invoice immediately.
      </p>
      <button
        onClick={() =>
          create.mutate(
            { consultationId, service_items: selected, instructions },
            { onSuccess: onClose },
          )
        }
        disabled={create.isPending || selected.length === 0}
        className="w-full rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {create.isPending ? "Ordering…" : `Order ${selected.length} service(s)`}
      </button>
    </Dialog>
  );
}
