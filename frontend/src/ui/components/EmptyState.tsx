import type { ReactNode } from "react";

export default function EmptyState({
  icon,
  title = "Nothing here",
  description,
  action,
  className = "",
}: {
  icon?: ReactNode;
  title?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-[var(--hms-border-strong)] py-16 text-center ${className}`}>
      {icon && <div className="text-3xl text-[var(--hms-text-muted)]">{icon}</div>}
      <div>
        <p className="font-medium text-[var(--hms-text-secondary)]">{title}</p>
        {description && (
          <p className="mt-1 text-sm text-[var(--hms-text-muted)]">{description}</p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
