import type { ReactNode, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

interface BaseProps {
  label?: string;
  error?: string;
  hint?: string;
}

/* ── Text input ───────────────────────────────────────────────────────── */

type InputFieldProps = BaseProps & InputHTMLAttributes<HTMLInputElement>;

export function InputField({ label, error, hint, className = "", id, ...props }: InputFieldProps) {
  const fieldId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={fieldId} className="block text-sm font-medium text-[var(--hms-text-secondary)]">
          {label}
        </label>
      )}
      <input
        id={fieldId}
        className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors
          border-[var(--hms-border)] bg-white text-[var(--hms-text)]
          placeholder:text-[var(--hms-text-muted)]
          focus:border-[var(--hms-border-focus)] focus:outline-none focus:ring-1 focus:ring-[var(--hms-border-focus)]
          disabled:bg-[var(--hms-bg-muted)] disabled:text-[var(--hms-text-muted)] disabled:cursor-not-allowed
          ${error ? "border-[var(--hms-danger)] focus:border-[var(--hms-danger)] focus:ring-[var(--hms-danger)]" : ""}
          ${className}`}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined}
        {...props}
      />
      {error && <p id={`${fieldId}-error`} className="text-xs text-[var(--hms-danger)]">{error}</p>}
      {!error && hint && <p id={`${fieldId}-hint`} className="text-xs text-[var(--hms-text-muted)]">{hint}</p>}
    </div>
  );
}

/* ── Select ───────────────────────────────────────────────────────────── */

type SelectFieldProps = BaseProps & SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode };

export function SelectField({ label, error, hint, className = "", id, children, ...props }: SelectFieldProps) {
  const fieldId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={fieldId} className="block text-sm font-medium text-[var(--hms-text-secondary)]">
          {label}
        </label>
      )}
      <select
        id={fieldId}
        className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors
          border-[var(--hms-border)] bg-white text-[var(--hms-text)]
          focus:border-[var(--hms-border-focus)] focus:outline-none focus:ring-1 focus:ring-[var(--hms-border-focus)]
          disabled:bg-[var(--hms-bg-muted)] disabled:text-[var(--hms-text-muted)] disabled:cursor-not-allowed
          ${error ? "border-[var(--hms-danger)] focus:border-[var(--hms-danger)] focus:ring-[var(--hms-danger)]" : ""}
          ${className}`}
        aria-invalid={error ? "true" : undefined}
        {...props}
      >
        {children}
      </select>
      {error && <p className="text-xs text-[var(--hms-danger)]">{error}</p>}
      {!error && hint && <p className="text-xs text-[var(--hms-text-muted)]">{hint}</p>}
    </div>
  );
}

/* ── Textarea ─────────────────────────────────────────────────────────── */

type TextareaFieldProps = BaseProps & TextareaHTMLAttributes<HTMLTextAreaElement>;

export function TextareaField({ label, error, hint, className = "", id, ...props }: TextareaFieldProps) {
  const fieldId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={fieldId} className="block text-sm font-medium text-[var(--hms-text-secondary)]">
          {label}
        </label>
      )}
      <textarea
        id={fieldId}
        className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors
          border-[var(--hms-border)] bg-white text-[var(--hms-text)]
          placeholder:text-[var(--hms-text-muted)]
          focus:border-[var(--hms-border-focus)] focus:outline-none focus:ring-1 focus:ring-[var(--hms-border-focus)]
          disabled:bg-[var(--hms-bg-muted)] disabled:text-[var(--hms-text-muted)] disabled:cursor-not-allowed
          ${error ? "border-[var(--hms-danger)] focus:border-[var(--hms-danger)] focus:ring-[var(--hms-danger)]" : ""}
          ${className}`}
        aria-invalid={error ? "true" : undefined}
        {...props}
      />
      {error && <p className="text-xs text-[var(--hms-danger)]">{error}</p>}
      {!error && hint && <p className="text-xs text-[var(--hms-text-muted)]">{hint}</p>}
    </div>
  );
}
