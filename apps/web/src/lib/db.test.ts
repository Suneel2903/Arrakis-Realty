import postgres from "postgres";
import { describe, expect, it } from "vitest";

import { connection } from "./db";

describe("connection", () => {
  it("leaves TCP URLs alone", () => {
    const url = "postgres://u:p@db:5432/arrakis?sslmode=disable";
    expect(connection(url)).toEqual({ url });
  });

  it("turns a Cloud SQL socket into the host option postgres.js understands", () => {
    const c = connection("postgres://u:p@localhost/arrakis?host=/cloudsql/proj:asia-south1:pg");
    expect(c.host).toBe("/cloudsql/proj:asia-south1:pg");
    const sql = postgres(c.url, { host: c.host });
    expect(sql.options.path).toBe("/cloudsql/proj:asia-south1:pg/.s.PGSQL.5432");
    expect(sql.options.database).toBe("arrakis");
  });
});
