import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "../features/auth/LoginPage";
import { useMe } from "../features/auth/useAuth";
import PatientProfilePage from "../features/patients/PatientProfilePage";
import PatientsPage from "../features/patients/PatientsPage";
import QueuePage from "../features/queue/QueuePage";
import type { Me } from "../api/types";
import Shell from "./Shell";

const QUEUE_ROLES = [
  "Receptionist",
  "Nurse",
  "Doctor",
  "Cashier",
  "Lab Technician",
  "Pharmacist",
] as const;

const FRONT_DESK = ["Receptionist", "Nurse", "Doctor", "Cashier"] as const;

export function canSeeQueue(me: Me): boolean {
  return me.roles.some((role) => (QUEUE_ROLES as readonly string[]).includes(role));
}

function isFrontDesk(me: Me): boolean {
  return me.roles.some((role) => (FRONT_DESK as readonly string[]).includes(role));
}

export default function App() {
  const me = useMe();

  if (me.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }

  if (!me.data) {
    return <LoginPage />;
  }

  const user = me.data;

  return (
    <Routes>
      <Route element={<Shell me={user} />}>
        <Route index element={<Home me={user} />} />
        {canSeeQueue(user) && <Route path="queue" element={<QueuePage me={user} />} />}
        {isFrontDesk(user) && (
          <>
            <Route path="patients" element={<PatientsPage me={user} />} />
            <Route path="patients/:id" element={<PatientProfilePage me={user} />} />
          </>
        )}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function Home({ me }: { me: Me }) {
  if (canSeeQueue(me)) {
    return <Navigate to="/queue" replace />;
  }
  return (
    <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500">
      Nothing to show for your role yet.
    </div>
  );
}
