import { describe, expect, it } from "vitest";

import { health } from "./health";

describe("health", () => {
  it("is ok when the database answers", async () => {
    const res = await health(async () => 1);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true, db: true });
    expect(res.headers.get("cache-control")).toBe("no-store");
  });

  it("returns 503 when the database is down", async () => {
    const res = await health(async () => {
      throw new Error("connection refused");
    });
    expect(res.status).toBe(503);
    expect(await res.json()).toEqual({ ok: false, db: false });
  });
});
