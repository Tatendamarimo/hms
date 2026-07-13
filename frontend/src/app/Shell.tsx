import { Outlet } from "react-router-dom";
import { useLogout, useSwitchClinic } from "../features/auth/useAuth";
import type { Me } from "../api/types";

export default function Shell({ me }: { me: Me }) {
  const logout = useLogout();
  const switchClinic = useSwitchClinic();

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-slate-800">HMS</span>
          {me.clinics.length > 1 ? (
            <select
              value={me.active_clinic?.id ?? ""}
              onChange={(e) => switchClinic.mutate(Number(e.target.value))}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            >
              {me.clinics.map((clinic) => (
                <option key={clinic.id} value={clinic.id}>
                  {clinic.name}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm text-slate-500">{me.active_clinic?.name}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-600">
            {me.full_name || me.username}
            {me.roles.length > 0 && (
              <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                {me.roles.join(", ")}
              </span>
            )}
          </span>
          <button
            onClick={() => logout.mutate()}
            className="rounded-md border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50"
          >
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
