import { FormEvent, useState } from "react";
import { useLogin } from "./useAuth";

export default function LoginPage() {
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ username, password });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-4 rounded-xl bg-white p-8 shadow"
      >
        <div>
          <h1 className="text-xl font-semibold text-slate-800">HMS</h1>
          <p className="text-sm text-slate-500">Sign in to your clinic</p>
        </div>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </label>

        {login.isError && (
          <p role="alert" className="text-sm text-red-600">
            {login.error instanceof Error ? login.error.message : "Login failed."}
          </p>
        )}

        <button
          type="submit"
          disabled={login.isPending}
          className="w-full rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {login.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
