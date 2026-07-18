import { useState, type ReactNode } from "react";

interface Tab {
  key: string;
  label: string;
  content: ReactNode;
}

export default function Tabs({
  tabs,
  defaultTab,
  className = "",
}: {
  tabs: Tab[];
  defaultTab?: string;
  className?: string;
}) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.key ?? "");

  return (
    <div className={className}>
      <div className="flex border-b border-[var(--hms-border)]" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={active === tab.key}
            onClick={() => setActive(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors -mb-px
              ${active === tab.key
                ? "border-b-2 text-[var(--hms-text)]"
                : "text-[var(--hms-text-muted)] hover:text-[var(--hms-text-secondary)]"
              }`}
            style={active === tab.key ? { borderColor: "var(--hms-primary)" } : undefined}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="pt-4" role="tabpanel">
        {tabs.find((t) => t.key === active)?.content}
      </div>
    </div>
  );
}
