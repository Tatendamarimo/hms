import { useState } from "react";
import Button from "./Button";
import Modal from "./Modal";

export interface ReasonModalProps {
  open: boolean;
  /** Dialog heading — e.g. "Mark LWBS" or "Void invoice line" */
  title: string;
  /** Explanatory text shown below the title — use for audit wording */
  description?: string;
  /** Label for the text field. Default: "Reason (required)" */
  reasonLabel?: string;
  /** Placeholder text. Default: "Enter reason…" */
  placeholder?: string;
  /** Confirm button label. Default: "Confirm" */
  confirmLabel?: string;
  /** Confirm button variant. Default: "primary" */
  confirmVariant?: "primary" | "danger";
  /** Whether the mutation is in progress */
  loading?: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

/**
 * Purpose-built modal that replaces every `window.prompt("Reason…")` in
 * the codebase. Enforces a non-empty reason and gives the user a cancel
 * option — two things window.prompt does poorly.
 */
export default function ReasonModal({
  open,
  title,
  description,
  reasonLabel = "Reason (required)",
  placeholder = "Enter reason…",
  confirmLabel = "Confirm",
  confirmVariant = "primary",
  loading = false,
  onConfirm,
  onCancel,
}: ReasonModalProps) {
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);

  const trimmed = reason.trim();
  const valid = trimmed.length > 0;

  const handleConfirm = () => {
    setTouched(true);
    if (!valid) return;
    onConfirm(trimmed);
  };

  const handleClose = () => {
    setReason("");
    setTouched(false);
    onCancel();
  };

  return (
    <Modal open={open} onClose={handleClose} title={title}>
      <div className="space-y-4">
        {description && (
          <p className="text-sm text-[var(--hms-text-secondary)]">{description}</p>
        )}

        <div className="space-y-1">
          <label htmlFor="reason-modal-input" className="block text-sm font-medium text-[var(--hms-text-secondary)]">
            {reasonLabel}
          </label>
          <textarea
            id="reason-modal-input"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onBlur={() => setTouched(true)}
            placeholder={placeholder}
            rows={3}
            className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors
              bg-white text-[var(--hms-text)] placeholder:text-[var(--hms-text-muted)]
              focus:outline-none focus:ring-1
              ${touched && !valid
                ? "border-[var(--hms-danger)] focus:border-[var(--hms-danger)] focus:ring-[var(--hms-danger)]"
                : "border-[var(--hms-border)] focus:border-[var(--hms-border-focus)] focus:ring-[var(--hms-border-focus)]"
              }`}
            aria-invalid={touched && !valid ? "true" : undefined}
          />
          {touched && !valid && (
            <p className="text-xs text-[var(--hms-danger)]">A reason is required for audit purposes.</p>
          )}
        </div>

        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant={confirmVariant}
            onClick={handleConfirm}
            loading={loading}
            disabled={!valid}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
