export type Health = { ok: boolean; db: boolean };

/** Liveness plus a database round trip. 503 when the database is unreachable. */
export async function health(ping: () => Promise<unknown>): Promise<Response> {
  let dbOk = false;
  try {
    await ping();
    dbOk = true;
  } catch {
    dbOk = false;
  }
  const body: Health = { ok: dbOk, db: dbOk };
  return Response.json(body, {
    status: dbOk ? 200 : 503,
    headers: { "cache-control": "no-store" },
  });
}
