"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { apiMode, makeApi, type ConsoleApi, type Identity } from "@/lib/api";
import { Button } from "@/components/ui";

const TOKEN_KEY = "av-console-token";

interface ConsoleSession {
  api: ConsoleApi;
  identity: Identity;
  signOut: () => void;
}

const SessionContext = createContext<ConsoleSession | null>(null);

export function useConsole(): ConsoleSession {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useConsole must be used inside ConsoleSessionProvider");
  return ctx;
}

export function ConsoleSessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<ConsoleSession | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signOut = useCallback(() => {
    window.sessionStorage.removeItem(TOKEN_KEY);
    setSession(null);
  }, []);

  const signIn = useCallback(
    async (token: string) => {
      const api = makeApi(token);
      try {
        const identity = await api.whoami();
        window.sessionStorage.setItem(TOKEN_KEY, token);
        setSession({ api, identity, signOut });
        setError(null);
      } catch (e) {
        window.sessionStorage.removeItem(TOKEN_KEY);
        setError(e instanceof Error ? e.message : "sign-in failed");
      }
    },
    [signOut],
  );

  useEffect(() => {
    const saved = window.sessionStorage.getItem(TOKEN_KEY);
    const finish = () => setReady(true);
    if (saved) void signIn(saved).finally(finish);
    else finish();
  }, [signIn]);

  if (!ready) return <p className="px-6 py-10 text-sm text-muted">Loading</p>;
  if (!session) return <SignIn onSubmit={signIn} error={error} />;
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

function SignIn({ onSubmit, error }: { onSubmit: (token: string) => Promise<void>; error: string | null }) {
  const [token, setToken] = useState("");
  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="font-serif text-2xl">Console sign-in</h1>
      <p className="mt-2 text-sm text-muted">Paste your API token. Your role (admin, ops, auditor, read-only) comes from the token.</p>
      {apiMode() === "mock" && (
        <p className="mt-2 text-xs text-muted">
          Mock data layer: use dev-admin-token, dev-ops-token, dev-auditor-token or dev-ro-token.
        </p>
      )}
      <form
        className="mt-6 flex gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void onSubmit(token.trim());
        }}
      >
        <label className="sr-only" htmlFor="token">
          API token
        </label>
        <input
          id="token"
          name="token"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="flex-1 rounded border border-line bg-white px-3 py-2 text-sm"
          autoComplete="off"
        />
        <Button type="submit">Sign in</Button>
      </form>
      {error && (
        <p role="alert" className="mt-3 text-sm text-warn">
          {error}
        </p>
      )}
    </div>
  );
}
