// JSON POST to our own API routes. A non-2xx answer is an error with the route's detail.
export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const data = (await res.json().catch(() => null)) as (T & { detail?: string }) | null;
  if (!res.ok || data === null) throw new Error(data?.detail ?? `request failed (${res.status})`);
  return data;
}
