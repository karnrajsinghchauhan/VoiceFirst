// Passcode form for the private pages. Posts to /api/gate, which sets the gate cookie.
export const metadata = { title: "Private | Agoda Voice", robots: { index: false, follow: false } };

const ALLOWED = new Set(["/demo", "/agoda"]);

export default async function GatePage({ searchParams }: { searchParams: Promise<{ next?: string; error?: string }> }) {
  const { next, error } = await searchParams;
  const target = next !== undefined && ALLOWED.has(next) ? next : "/demo";
  return (
    <main className="mx-auto max-w-sm px-4 py-24">
      <h1 className="font-display text-2xl">Private page</h1>
      <p className="mt-2 text-sm text-muted">Enter the passcode you were given.</p>
      <form method="post" action="/api/gate" className="mt-6 space-y-3">
        <input type="hidden" name="next" value={target} />
        <label className="block text-sm" htmlFor="passcode">
          Passcode
        </label>
        <input
          id="passcode"
          name="passcode"
          type="password"
          required
          autoComplete="off"
          className="w-full rounded border border-line bg-surface px-3 py-2"
        />
        {error ? (
          <p role="alert" className="text-sm text-fail">
            That passcode did not match.
          </p>
        ) : null}
        <button type="submit" className="motion w-full rounded bg-ink px-4 py-2 text-sm text-paper hover:bg-accent">
          Continue
        </button>
      </form>
    </main>
  );
}
