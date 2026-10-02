-- migrate:up
-- Map and data-pipeline tables (docs/DATA-MODEL.sql). App tables (users, leads,
-- payments) come in their own migrations.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE rera_project_raw (
  project_id        text PRIMARY KEY,           -- portal id
  fetched_at        timestamptz NOT NULL,
  raw_uri           text NOT NULL,              -- gs://.../project_id.html.gz
  parser_version    text NOT NULL,
  data              jsonb NOT NULL              -- every parsed field
);

CREATE TABLE micro_market (
  id                serial PRIMARY KEY,
  name              text NOT NULL,
  zone              text,
  boundary          geography(MultiPolygon,4326) NOT NULL
);

CREATE TABLE project (
  id                bigserial PRIMARY KEY,
  rera_project_id   text UNIQUE REFERENCES rera_project_raw(project_id),
  reg_number        text UNIQUE,
  name              text NOT NULL,
  promoter_name     text,
  project_type      text,                       -- residential | mixed | plotted | commercial
  rera_status       text,                       -- approved | withdrawn | transferred ...
  build_status      text,                       -- new_launch | ongoing | completed
  district          text, taluk text, address text, pin text,
  registration_date date, completion_date date,
  land_area_sqm     numeric, far numeric, towers int, total_units int,
  micro_market_id   int REFERENCES micro_market(id),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE project_location (
  project_id        bigint PRIMARY KEY REFERENCES project(id),
  point             geography(Point,4326) NOT NULL,
  site              geography(Polygon,4326),
  method            text NOT NULL CHECK (method IN (
                      'portal_latlng','portal_boundary',          -- RERA portal
                      'osm_name','nominatim','photon',            -- OpenStreetMap name match / search
                      'web_lookup','address_geocode',
                      'village_centroid','locality_name','ward_centroid','pin_centroid',
                      'google_candidate',                         -- QA queue only, see below
                      'manual')),
  confidence        text NOT NULL CHECK (confidence IN ('verified','high','medium','low')),
  source_url        text,
  note              text,
  checked_by        text, checked_at timestamptz,
  -- Google Maps results are suggestions for an operator (CLAUDE.md rule 5), never a trusted
  -- location: once confirmed the operator's pin is stored as method 'manual'.
  CONSTRAINT google_candidate_is_low CHECK (method <> 'google_candidate' OR confidence = 'low')
);

CREATE TABLE project_fact (
  id                bigserial PRIMARY KEY,
  project_id        bigint REFERENCES project(id),
  field             text NOT NULL,              -- floors_per_tower | total_units | possession_actual | bhk_mix | size_range ...
  value             text NOT NULL,
  source            text NOT NULL,              -- rera_doc | developer_site | listing | operator
  source_url        text,
  extracted_at      timestamptz NOT NULL DEFAULT now(),
  confidence        text NOT NULL,
  note              text
);

CREATE TABLE existing_complex (                 -- non-RERA communities (OSM / Overture)
  id                bigserial PRIMARY KEY,
  name              text NOT NULL,
  source            text NOT NULL CHECK (source IN ('osm','overture')),
  source_ref        text NOT NULL,              -- e.g. osm way/123
  site              geography(Polygon,4326),
  point             geography(Point,4326) NOT NULL,
  tags              jsonb
);

CREATE TABLE pipeline_run (
  id bigserial PRIMARY KEY, started_at timestamptz, finished_at timestamptz,
  stage text, listed int, fetched int, failed int, status text, notes text
);

CREATE INDEX ON project_location USING gist (point);
CREATE INDEX ON existing_complex USING gist (point);
CREATE INDEX ON micro_market USING gist (boundary);
CREATE INDEX ON project_fact (project_id, field);
CREATE INDEX ON project (micro_market_id);

-- migrate:down
DROP TABLE pipeline_run;
DROP TABLE existing_complex;
DROP TABLE project_fact;
DROP TABLE project_location;
DROP TABLE project;
DROP TABLE micro_market;
DROP TABLE rera_project_raw;
