import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "../features/auth/LoginPage";
import { useMe } from "../features/auth/useAuth";
import Shell from "./Shell";

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

  return (
    <Routes>
      <Route element={<Shell me={me.data} />}>
        <Route index element={<Home />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function Home() {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500">
      Phase 0 complete — clinical modules arrive in Phase 1.
    </div>
  );
}
