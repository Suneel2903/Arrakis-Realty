import postgres from "postgres";

let client: postgres.Sql | undefined;

/**
 * postgres.js ignores a socket path in the URL, so Cloud SQL's
 * `postgres://user:pass@localhost/db?host=/cloudsql/PROJECT:REGION:INSTANCE`
 * is split here into the URL and a `host` option.
 */
export function connection(url: string): { url: string; host?: string } {
  const u = new URL(url);
  const socket = u.searchParams.get("host");
  if (!socket?.startsWith("/")) return { url };
  u.searchParams.delete("host");
  return { url: u.toString(), host: socket };
}

/** Shared Postgres client. Created on first use so builds never need a database. */
export function db(): postgres.Sql {
  if (!client) {
    const env = process.env.DATABASE_URL;
    if (!env) throw new Error("DATABASE_URL is not set");
    const { url, host } = connection(env);
    client = postgres(url, { max: 5, idle_timeout: 30, connect_timeout: 5, ...(host && { host }) });
  }
  return client;
}
