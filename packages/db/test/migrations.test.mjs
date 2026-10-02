// Applies every migration to TEST_DATABASE_URL (a throwaway database: the test rolls
// migrations down and up again) and checks the schema. Skipped when the variable is unset.
import { execFileSync } from "node:child_process";
import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import postgres from "postgres";

const url = process.env.TEST_DATABASE_URL;
const opts = { skip: url ? false : "TEST_DATABASE_URL not set" };
const dbmate = (...args) =>
  execFileSync("dbmate", ["--migrations-dir", "migrations", "--no-dump-schema", ...args], {
    env: { ...process.env, DATABASE_URL: url },
    stdio: "pipe",
  });

let sql;
before(() => {
  if (!url) return;
  dbmate("--wait", "up");
  sql = postgres(url, { onnotice: () => {} });
});
after(() => sql?.end());

const TABLES = [
  "existing_complex", "micro_market", "pipeline_run", "project", "project_fact",
  "project_location", "rera_project_raw", "schema_migrations",
];

test("all tables exist", opts, async () => {
  const rows = await sql`select table_name from information_schema.tables
                         where table_schema = 'public' and table_type = 'BASE TABLE'`;
  const names = rows.map((r) => r.table_name).filter((n) => n !== "spatial_ref_sys").sort();
  assert.deepEqual(names, TABLES);
});

// Each case runs in a transaction that is rolled back.
async function attempt(fn) {
  try {
    await sql.begin(async (tx) => {
      await fn(tx);
      throw new Error("__rollback__");
    });
  } catch (e) {
    if (e.message !== "__rollback__") throw e;
  }
}

async function project(tx, mm = null) {
  const [p] = await tx`insert into project (name, micro_market_id) values ('T', ${mm}) returning id`;
  return p.id;
}

test("location methods used by the pipeline are accepted", opts, async () => {
  for (const method of ["osm_name", "nominatim", "photon", "village_centroid",
    "locality_name", "ward_centroid", "pin_centroid", "manual"]) {
    await attempt(async (tx) => {
      const id = await project(tx);
      await tx`insert into project_location (project_id, point, method, confidence)
               values (${id}, 'POINT(77.6 12.9)', ${method}, 'medium')`;
    });
  }
});

test("unknown method is rejected", opts, async () => {
  await assert.rejects(attempt(async (tx) => {
    const id = await project(tx);
    await tx`insert into project_location (project_id, point, method, confidence)
             values (${id}, 'POINT(77.6 12.9)', 'google_geocode', 'high')`;
  }), /project_location_method_check/);
});

test("google_candidate rows can only be low confidence", opts, async () => {
  await attempt(async (tx) => {
    const id = await project(tx);
    await tx`insert into project_location (project_id, point, method, confidence)
             values (${id}, 'POINT(77.6 12.9)', 'google_candidate', 'low')`;
  });
  await assert.rejects(attempt(async (tx) => {
    const id = await project(tx);
    await tx`insert into project_location (project_id, point, method, confidence)
             values (${id}, 'POINT(77.6 12.9)', 'google_candidate', 'high')`;
  }), /google_candidate_is_low/);
});

test("project.micro_market_id must reference a micro_market", opts, async () => {
  await attempt(async (tx) => {
    const [m] = await tx`insert into micro_market (name, boundary) values
      ('Whitefield', 'MULTIPOLYGON(((77.7 12.9,77.8 12.9,77.8 13,77.7 13,77.7 12.9)))')
      returning id`;
    await project(tx, m.id);
  });
  await assert.rejects(attempt((tx) => project(tx, 999999)), /micro_market_id_fkey/);
});

test("down migration reverses up cleanly", opts, async () => {
  dbmate("rollback");
  const [{ n }] = await sql`select count(*)::int as n from information_schema.tables
                            where table_schema = 'public' and table_name = 'project'`;
  assert.equal(n, 0);
  dbmate("up");
});
