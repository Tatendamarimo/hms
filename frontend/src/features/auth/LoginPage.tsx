import { FormEvent, useState } from "react";
import { useLogin } from "./useAuth";
import { useTheme } from "../../theme/ThemeProvider";
import { Button } from "../../ui/components";

export default function LoginPage() {
  const login = useLogin();
  const theme = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ username, password });
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4"
      style={{ background: `linear-gradient(135deg, var(--hms-bg) 0%, var(--hms-primary-light) 100%)` }}
    >
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-6 rounded-2xl bg-[var(--hms-bg-card)] p-8 shadow-xl"
        style={{ boxShadow: "var(--hms-shadow-xl)" }}
      >
        {/* Clinic branding */}
        <div className="flex flex-col items-center gap-3 text-center">
          {theme.logoUrl ? (
            <img
              src={theme.logoUrl}
              alt={theme.clinicName}
              className="h-14 w-14 rounded-xl object-contain"
            />
          ) : (
            <div
              className="flex h-14 w-14 items-center justify-center rounded-xl text-xl font-bold text-white"
              style={{ backgroundColor: "var(--hms-primary)" }}
            >
              {theme.clinicName.charAt(0)}
            </div>
          )}
          <div>
            <h1 className="text-xl font-semibold text-[var(--hms-text)]">
              {theme.clinicName}
            </h1>
            <p className="text-sm text-[var(--hms-text-muted)]">
              {theme.tagline || "Sign in to your clinic"}
            </p>
          </div>
        </div>

        {/* Form fields */}
        <div className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="login-username" className="block text-sm font-medium text-[var(--hms-text-secondary)]">
              Username
            </label>
            <input
              id="login-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
              className="w-full rounded-lg border border-[var(--hms-border)] bg-white px-3 py-2.5 text-sm text-[var(--hms-text)] placeholder:text-[var(--hms-text-muted)] transition-colors focus:border-[var(--hms-border-focus)] focus:outline-none focus:ring-1 focus:ring-[var(--hms-border-focus)]"
              placeholder="Enter your username"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="login-password" className="block text-sm font-medium text-[var(--hms-text-secondary)]">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="w-full rounded-lg border border-[var(--hms-border)] bg-white px-3 py-2.5 text-sm text-[var(--hms-text)] placeholder:text-[var(--hms-text-muted)] transition-colors focus:border-[var(--hms-border-focus)] focus:outline-none focus:ring-1 focus:ring-[var(--hms-border-focus)]"
              placeholder="Enter your password"
            />
          </div>
        </div>

        {login.isError && (
          <div className="rounded-lg border-l-4 border-[var(--hms-danger)] bg-[var(--hms-danger-light)] px-4 py-3 text-sm text-[var(--hms-danger-dark)]" role="alert">
            {login.error instanceof Error ? login.error.message : "Login failed."}
          </div>
        )}

        <Button
          type="submit"
          loading={login.isPending}
          className="w-full"
          size="lg"
        >
          Sign in
        </Button>
      </form>
    </div>
  );
}
