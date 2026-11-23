"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ConsoleApi, session, type Identity } from "@/lib/api";
import { Button } from "@/components/ui";

interface ConsoleSession {
  api: ConsoleApi;
  identity: Identity;
  mode: "http" | "mock";
  signOut: () => void;
}

const SessionContext = createContext<ConsoleSession | null>(null);

export function useConsole(): ConsoleSession {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useConsole must be used inside ConsoleSessionProvider");
  return ctx;
}

export function ConsoleSessionProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<ConsoleSession | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mockHint, setMockHint] = useState(false);

  const signOut = useCallback(() => {
    void session.signOut().finally(() => setCurrent(null));
  }, []);

  const adopt = useCallback(
    (info: { identity: Identity; mode: "http" | "mock" }) =>
      setCurrent({ api: new ConsoleApi(info.identity), identity: info.identity, mode: info.mode, signOut }),
    [signOut],
  );

  useEffect(() => {
    session.current().then(
      ({ info, mode }) => {
        if (info) adopt(info);
        setMockHint(mode === "mock");
        setReady(true);
      },
      (e: unknown) => {
        setError(e instanceof Error ? e.message : String(e));
        setReady(true);
      },
    );
  }, [adopt]);

  const signIn = useCallback(
    async (token: string) => {
      try {
        adopt(await session.signIn(token));
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "sign-in failed");
      }
    },
    [adopt],
  );

  if (!ready) return <p className="px-6 py-10 text-sm text-muted">Loading</p>;
  if (!current) return <SignIn onSubmit={signIn} error={error} mockHint={mockHint} />;
  return <SessionContext.Provider value={current}>{children}</SessionContext.Provider>;
}

function SignIn({ onSubmit, error, mockHint }: { onSubmit: (token: string) => Promise<void>; error: string | null; mockHint: boolean }) {
  const [token, setToken] = useState("");
  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="font-display text-2xl">Console sign-in</h1>
      <p className="mt-2 text-sm text-muted">
        Paste your API token. Your role (admin, ops, auditor, read-only) comes from the token. It is kept in a secure,
        HttpOnly cookie, never in the page.
      </p>
      {mockHint && (
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
          className="flex-1 rounded border border-line bg-surface px-3 py-2 text-sm"
          autoComplete="off"
        />
        <Button type="submit">Sign in</Button>
      </form>
      {error && (
        <p role="alert" className="mt-3 text-sm text-fail">
          {error}
        </p>
      )}
    </div>
  );
}
