import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "../features/auth/LoginPage";
import { useMe } from "../features/auth/useAuth";
import CashUpPage from "../features/billing/CashUpPage";
import UnpaidPage from "../features/billing/UnpaidPage";
import PatientProfilePage from "../features/patients/PatientProfilePage";
import PatientsPage from "../features/patients/PatientsPage";
import QueuePage from "../features/queue/QueuePage";
import VisitPage from "../features/visit/VisitPage";
import { ThemeProvider } from "../theme/ThemeProvider";
import { LoadingState } from "../ui/components";
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
      <ThemeProvider>
        <LoadingState message="Connecting…" />
      </ThemeProvider>
    );
  }

  if (!me.data) {
    return (
      <ThemeProvider>
        <LoginPage />
      </ThemeProvider>
    );
  }

  const user = me.data;

  return (
    <ThemeProvider activeClinic={user.active_clinic}>
      <Routes>
        <Route element={<Shell me={user} />}>
          {/* Role dashboards land in PR2; until then the queue is home. */}
          <Route index element={<Navigate to={canSeeQueue(user) ? "/queue" : "/patients"} replace />} />
          {canSeeQueue(user) && <Route path="queue" element={<QueuePage me={user} />} />}
          {canSeeQueue(user) && <Route path="visit/:id" element={<VisitPage me={user} />} />}
          {isFrontDesk(user) && (
            <>
              <Route path="patients" element={<PatientsPage me={user} />} />
              <Route path="patients/:id" element={<PatientProfilePage me={user} />} />
            </>
          )}
          {user.roles.includes("Cashier") && (
            <Route path="billing/cashup" element={<CashUpPage />} />
          )}
          {(user.roles.includes("Cashier") || user.roles.includes("Admin")) && (
            <Route path="billing/unpaid" element={<UnpaidPage />} />
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}


