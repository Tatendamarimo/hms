import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useLogout, useSwitchClinic } from "../features/auth/useAuth";
import { useTheme } from "../theme/ThemeProvider";
import { Drawer } from "../ui/components";
import type { Me, Role } from "../api/types";

/* ── Navigation definition ─────────────────────────────────────────── */

interface NavItem {
  to: string;
  label: string;
  roles: Role[];
  /** Group for sidebar sections */
  group: "main" | "billing" | "admin";
  icon: React.ReactNode;
}

const NAV: NavItem[] = [
  {
    to: "/queue",
    label: "Queue",
    roles: ["Receptionist", "Nurse", "Doctor", "Cashier", "Lab Technician", "Pharmacist"],
    group: "main",
    icon: <QueueIcon />,
  },
  {
    to: "/patients",
    label: "Patients",
    roles: ["Receptionist", "Nurse", "Doctor", "Cashier"],
    group: "main",
    icon: <PatientsIcon />,
  },
  {
    to: "/billing/cashup",
    label: "Cash-up",
    roles: ["Cashier"],
    group: "billing",
    icon: <CashUpIcon />,
  },
  {
    to: "/billing/unpaid",
    label: "Unpaid",
    roles: ["Cashier", "Admin"],
    group: "billing",
    icon: <UnpaidIcon />,
  },
];

const GROUPS: { key: NavItem["group"]; label: string }[] = [
  { key: "main", label: "Clinical" },
  { key: "billing", label: "Billing" },
  { key: "admin", label: "Admin" },
];

/* ── Shell component ──────────────────────────────────────────────── */

export default function Shell({ me }: { me: Me }) {
  const logout = useLogout();
  const switchClinic = useSwitchClinic();
  const theme = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const links = NAV.filter((item) => item.roles.some((role) => me.roles.includes(role)));

  const sidebarContent = (
    <SidebarContent
      links={links}
      theme={theme}
      onNavigate={() => setSidebarOpen(false)}
    />
  );

  return (
    <div className="flex min-h-screen bg-[var(--hms-bg)]">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:w-[var(--hms-sidebar-width)] border-r border-[var(--hms-border)] bg-[var(--hms-bg-card)]">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar drawer */}
      <Drawer open={sidebarOpen} onClose={() => setSidebarOpen(false)} side="left" width="w-[var(--hms-sidebar-width)]">
        {sidebarContent}
      </Drawer>

      {/* Main content area */}
      <div className="flex flex-1 flex-col lg:pl-[var(--hms-sidebar-width)]">
        {/* Header */}
        <header className="sticky top-0 flex h-[var(--hms-header-height)] items-center justify-between border-b border-[var(--hms-border)] bg-[var(--hms-bg-card)] px-4 lg:px-6"
          style={{ zIndex: "var(--hms-z-sticky)" }}
        >
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-1.5 text-[var(--hms-text-muted)] hover:bg-[var(--hms-bg-muted)] lg:hidden"
              aria-label="Open navigation"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z" clipRule="evenodd" />
              </svg>
            </button>

            {/* Clinic switcher (multi-clinic) */}
            {me.clinics.length > 1 ? (
              <select
                value={me.active_clinic?.id ?? ""}
                onChange={(e) => switchClinic.mutate(Number(e.target.value))}
                className="rounded-lg border border-[var(--hms-border)] bg-white px-3 py-1.5 text-sm text-[var(--hms-text-secondary)]"
              >
                {me.clinics.map((clinic) => (
                  <option key={clinic.id} value={clinic.id}>
                    {clinic.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-sm font-medium text-[var(--hms-text-secondary)] hidden lg:inline">
                {me.active_clinic?.name}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Notification placeholder */}
            <button
              className="relative rounded-lg p-2 text-[var(--hms-text-muted)] hover:bg-[var(--hms-bg-muted)]"
              aria-label="Notifications"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 2a6 6 0 00-6 6c0 1.887-.454 3.665-1.257 5.234a.75.75 0 00.515 1.076 32.91 32.91 0 003.256.508 3.5 3.5 0 006.972 0 32.903 32.903 0 003.256-.508.75.75 0 00.515-1.076A11.448 11.448 0 0116 8a6 6 0 00-6-6zM8.05 14.943a33.54 33.54 0 003.9 0 2 2 0 01-3.9 0z" clipRule="evenodd" />
              </svg>
            </button>

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-[var(--hms-bg-muted)]"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold text-white"
                  style={{ backgroundColor: "var(--hms-primary)" }}
                >
                  {(me.full_name || me.username).charAt(0).toUpperCase()}
                </div>
                <div className="hidden text-left md:block">
                  <div className="font-medium text-[var(--hms-text)]">
                    {me.full_name || me.username}
                  </div>
                  <div className="text-xs text-[var(--hms-text-muted)]">
                    {me.roles.join(", ")}
                  </div>
                </div>
                <svg className="h-4 w-4 text-[var(--hms-text-muted)] hidden md:block" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                </svg>
              </button>

              {userMenuOpen && (
                <>
                  <div className="fixed inset-0" onClick={() => setUserMenuOpen(false)} />
                  <div className="absolute right-0 mt-1 w-56 rounded-xl border border-[var(--hms-border)] bg-[var(--hms-bg-card)] py-1 shadow-lg"
                    style={{ zIndex: "var(--hms-z-dropdown)" }}
                  >
                    <div className="border-b border-[var(--hms-border)] px-4 py-3">
                      <p className="text-sm font-medium text-[var(--hms-text)]">{me.full_name || me.username}</p>
                      <p className="text-xs text-[var(--hms-text-muted)]">{me.roles.join(", ")}</p>
                    </div>
                    <button
                      onClick={() => { logout.mutate(); setUserMenuOpen(false); }}
                      className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-[var(--hms-text-secondary)] hover:bg-[var(--hms-bg-muted)]"
                    >
                      <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z" clipRule="evenodd" />
                        <path fillRule="evenodd" d="M19 10a.75.75 0 00-.75-.75H8.704l1.048-.943a.75.75 0 10-1.004-1.114l-2.5 2.25a.75.75 0 000 1.114l2.5 2.25a.75.75 0 101.004-1.114l-1.048-.943h9.546A.75.75 0 0019 10z" clipRule="evenodd" />
                      </svg>
                      Sign out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto" style={{ maxWidth: "var(--hms-content-max-width)" }}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

/* ── Sidebar content ─────────────────────────────────────────────── */

function SidebarContent({
  links,
  theme,
  onNavigate,
}: {
  links: NavItem[];
  theme: ReturnType<typeof useTheme>;
  onNavigate: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      {/* Logo / Clinic name */}
      <div className="flex h-[var(--hms-header-height)] items-center gap-3 border-b border-[var(--hms-border)] px-5">
        {theme.logoUrl ? (
          <img src={theme.logoUrl} alt={theme.clinicName} className="h-8 w-8 rounded-lg object-contain" />
        ) : (
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold text-white"
            style={{ backgroundColor: "var(--hms-primary)" }}
          >
            {theme.clinicName.charAt(0)}
          </div>
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[var(--hms-text)]">
            {theme.clinicName}
          </p>
          {theme.tagline && (
            <p className="truncate text-xs text-[var(--hms-text-muted)]">{theme.tagline}</p>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {GROUPS.map((group) => {
          const groupLinks = links.filter((l) => l.group === group.key);
          if (groupLinks.length === 0) return null;
          return (
            <div key={group.key} className="mb-4">
              <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-[var(--hms-text-muted)]">
                {group.label}
              </p>
              <ul className="space-y-0.5">
                {groupLinks.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                          isActive
                            ? "bg-[var(--hms-primary-light)] text-[var(--hms-primary)]"
                            : "text-[var(--hms-text-secondary)] hover:bg-[var(--hms-bg-muted)] hover:text-[var(--hms-text)]"
                        }`
                      }
                    >
                      <span className="h-5 w-5 shrink-0">{item.icon}</span>
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      {/* Sidebar footer */}
      <div className="border-t border-[var(--hms-border)] px-4 py-3">
        <p className="text-xs text-[var(--hms-text-muted)]">
          © {new Date().getFullYear()} {theme.clinicName}
        </p>
      </div>
    </div>
  );
}

/* ── SVG icons (inline, no dependency) ───────────────────────────── */

function QueueIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
      <path fillRule="evenodd" d="M6 4.75A.75.75 0 016.75 4h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 4.75zM6 10a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 10zm0 5.25a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75a.75.75 0 01-.75-.75zM1.99 4.75a1 1 0 011-1h.01a1 1 0 010 2h-.01a1 1 0 01-1-1zm1 5.25a1 1 0 011-1h.01a1 1 0 010 2h-.01a1 1 0 01-1-1zm0 5.25a1 1 0 011-1h.01a1 1 0 010 2h-.01a1 1 0 01-1-1z" clipRule="evenodd" />
    </svg>
  );
}

function PatientsIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
      <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
    </svg>
  );
}

function CashUpIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
      <path fillRule="evenodd" d="M1 4a1 1 0 011-1h16a1 1 0 011 1v8a1 1 0 01-1 1H2a1 1 0 01-1-1V4zm12 4a3 3 0 11-6 0 3 3 0 016 0zM4 9a1 1 0 100-2 1 1 0 000 2zm10-1a1 1 0 11-2 0 1 1 0 012 0zM2 14a1 1 0 011-1h2a1 1 0 010 2H3a1 1 0 01-1-1zm5-1a1 1 0 100 2h2a1 1 0 100-2H7zm5 1a1 1 0 011-1h2a1 1 0 010 2h-2a1 1 0 01-1-1z" clipRule="evenodd" />
    </svg>
  );
}

function UnpaidIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
    </svg>
  );
}
