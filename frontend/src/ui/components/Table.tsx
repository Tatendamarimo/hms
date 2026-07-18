import type { ReactNode } from "react";

interface Column<T> {
  key: string;
  header: string;
  className?: string;
  render: (item: T) => ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (item: T) => string | number;
  /** Optional row class function for conditional styling (e.g. emergency highlighting) */
  rowClassName?: (item: T) => string;
  /** Shown when data is empty */
  emptyMessage?: string;
  className?: string;
  onRowClick?: (item: T) => void;
}

export default function Table<T>({
  columns,
  data,
  rowKey,
  rowClassName,
  emptyMessage = "No data available.",
  className = "",
  onRowClick,
}: TableProps<T>) {
  return (
    <div className={`overflow-x-auto rounded-xl border border-[var(--hms-border)] bg-[var(--hms-bg-card)] ${className}`}>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--hms-border)] bg-[var(--hms-bg-muted)]">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--hms-text-muted)] ${col.className ?? ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--hms-border)]">
          {data.map((item) => (
            <tr
              key={rowKey(item)}
              className={`transition-colors ${onRowClick ? "cursor-pointer hover:bg-[var(--hms-bg-muted)]" : ""} ${rowClassName?.(item) ?? ""}`}
              onClick={onRowClick ? () => onRowClick(item) : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 ${col.className ?? ""}`}>
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
          {data.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-10 text-center text-[var(--hms-text-muted)]"
              >
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
