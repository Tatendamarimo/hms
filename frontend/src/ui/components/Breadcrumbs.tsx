import { Link } from "react-router-dom";

export interface Crumb {
  label: string;
  to?: string;
}

export default function Breadcrumbs({ items, className = "" }: { items: Crumb[]; className?: string }) {
  return (
    <nav aria-label="Breadcrumb" className={`flex items-center gap-1.5 text-sm ${className}`}>
      {items.map((crumb, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && (
              <svg className="h-3.5 w-3.5 text-[var(--hms-text-muted)]" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            {isLast || !crumb.to ? (
              <span className={isLast ? "font-medium text-[var(--hms-text)]" : "text-[var(--hms-text-muted)]"}>
                {crumb.label}
              </span>
            ) : (
              <Link
                to={crumb.to}
                className="text-[var(--hms-text-muted)] transition-colors hover:text-[var(--hms-text)]"
              >
                {crumb.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
