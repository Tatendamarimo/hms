import type { ReactNode, ButtonHTMLAttributes } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: ReactNode;
}

const base =
  "inline-flex items-center justify-center gap-2 font-medium transition-all rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none";

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "text-white shadow-sm hover:opacity-90 focus-visible:ring-[var(--hms-primary)]",
  secondary:
    "text-white shadow-sm hover:opacity-90 focus-visible:ring-[var(--hms-secondary)]",
  outline:
    "border border-[var(--hms-border-strong)] text-[var(--hms-text-secondary)] bg-white hover:bg-[var(--hms-bg-muted)] focus-visible:ring-[var(--hms-primary)]",
  ghost:
    "text-[var(--hms-text-secondary)] hover:bg-[var(--hms-bg-muted)] focus-visible:ring-[var(--hms-primary)]",
  danger:
    "bg-[var(--hms-danger)] text-white shadow-sm hover:bg-[var(--hms-danger-dark)] focus-visible:ring-[var(--hms-danger)]",
};

const sizes: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-2.5 text-base",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  children,
  className = "",
  disabled,
  style,
  ...props
}: ButtonProps) {
  // Inline background for themed variants so CSS variable is respected
  const inlineStyle: React.CSSProperties = { ...style };
  if (variant === "primary") {
    inlineStyle.backgroundColor = "var(--hms-primary)";
  } else if (variant === "secondary") {
    inlineStyle.backgroundColor = "var(--hms-secondary)";
  }

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      style={inlineStyle}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
