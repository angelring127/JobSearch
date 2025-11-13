-- JobMap Database Schema
-- PostgreSQL + PostGIS required

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Regions table
CREATE TABLE regions (
  id SERIAL PRIMARY KEY,
  city TEXT NOT NULL,
  bbs INTEGER NOT NULL,
  listing_url TEXT NOT NULL,
  center GEOGRAPHY(Point, 4326) NOT NULL
);

CREATE INDEX regions_bbs_idx ON regions(bbs);

-- Job sources table
CREATE TABLE job_sources (
  id BIGSERIAL PRIMARY KEY,
  msgid BIGINT NOT NULL,
  source_url TEXT UNIQUE NOT NULL,
  region_hint TEXT,
  title TEXT,
  wage_min INTEGER,
  wage_max INTEGER,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  geom GEOGRAPHY(Point,4326),
  category TEXT,
  confidence FLOAT DEFAULT 0.8,
  posted_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX job_sources_geom_idx ON job_sources USING GIST(geom);
CREATE INDEX job_sources_msgid_idx ON job_sources(msgid);
CREATE INDEX job_sources_posted_at_idx ON job_sources(posted_at DESC);

-- Crawl log table
CREATE TABLE crawl_log (
  id SERIAL PRIMARY KEY,
  bbs INTEGER NOT NULL,
  last_seen_msgid BIGINT,
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX crawl_log_bbs_idx ON crawl_log(bbs);

-- Initial regions data (Vancouver, Victoria, Toronto, Whistler, Other Cities)
-- 실제 JPCanada BBS URL 구조: https://bbs.jpcanada.com/listing.php?bbs={bbs_id}
INSERT INTO regions (city, bbs, listing_url, center) VALUES
  ('Vancouver', 4, 'https://bbs.jpcanada.com/listing.php?bbs=4', ST_GeogFromText('POINT(-123.1207 49.2827)')),
  ('Victoria', 62, 'https://bbs.jpcanada.com/listing.php?bbs=62', ST_GeogFromText('POINT(-123.3656 48.4284)')),
  ('Toronto', 53, 'https://bbs.jpcanada.com/listing.php?bbs=53', ST_GeogFromText('POINT(-79.3832 43.6532)')),
  ('Vancouver', 56, 'https://bbs.jpcanada.com/listing.php?bbs=56', ST_GeogFromText('POINT(-123.1207 49.2827)')),
  ('Other Cities', 59, 'https://bbs.jpcanada.com/listing.php?bbs=59', ST_GeogFromText('POINT(-123.1207 49.2827)'));


