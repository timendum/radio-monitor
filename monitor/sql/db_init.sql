-- SQLite setup

PRAGMA journal_mode = WAL;          -- better concurrency
PRAGMA synchronous = NORMAL;        -- durability/speed tradeoff
PRAGMA foreign_keys = ON;           -- enforce FK constraints


-- COUNTRIES
CREATE TABLE country (
  country_code   TEXT PRIMARY KEY,      -- ISO 3166-1 alpha-2 (e.g., 'IT', 'US')
  name           TEXT NOT NULL
);

-- STATIONS
CREATE TABLE station (
  station_id     INTEGER PRIMARY KEY,
  station_code   TEXT UNIQUE NOT NULL,  -- short code
  display_name   TEXT NOT NULL,
  active         INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

-- RAW DATA for ingestion
CREATE TABLE play (
  play_id            INTEGER PRIMARY KEY,
  station_id         INTEGER NOT NULL REFERENCES station(station_id) ON DELETE RESTRICT,
  observed_at        TEXT NOT NULL,           -- ISO8601 'YYYY-MM-DDTHH:MM:SSZ'
  title_raw          TEXT NOT NULL,           -- as captured from radio
  performer_raw      TEXT NOT NULL,           -- as captured from radio
  acquisition_id     TEXT,                    -- ingestion batch/job id
  source_payload     TEXT,                    -- raw JSON/text as string if needed
  inserted_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_play_observed_at ON play(observed_at);

-- ARTISTS
CREATE TABLE artist (
  artist_id        INTEGER PRIMARY KEY,
  artist_name      TEXT NOT NULL            -- canonical name
);

CREATE UNIQUE INDEX ux_artist_name ON artist(artist_name);

-- SONGS
CREATE TABLE song (
  song_id          INTEGER PRIMARY KEY,
  song_title       TEXT NOT NULL,            -- canonical title
  song_performers  TEXT NOT NULL,            -- canonical performers
  song_key         TEXT NOT NULL UNIQUE,     -- unique key (normalized title+performers)
  -- Optional industry identifiers & enrichment
  isrc             TEXT,                     -- if/when available
  year             INTEGER,                  -- enrichment (year of release/origin)
  country          TEXT,                     -- check country.country_code
  duration         INTEGER,                  -- optional if known

  -- Prevent duplicate, light check
  UNIQUE (song_title, song_performers),
  -- Light sanity checks
  CHECK (year IS NULL OR year BETWEEN 1900 AND 2100),
  CHECK (duration IS NULL OR duration BETWEEN 0 AND 3600)
);

CREATE INDEX idx_song_title ON song(song_title);
CREATE INDEX idx_song_song_performers ON song(song_performers);

-- Many-to-many for featured artists/remixers/etc.
CREATE TABLE song_artist (
  song_id     INTEGER NOT NULL REFERENCES song(song_id) ON DELETE CASCADE,
  artist_id   INTEGER NOT NULL REFERENCES artist(artist_id) ON DELETE CASCADE,
  PRIMARY KEY (song_id, artist_id)
);

CREATE INDEX idx_song_artist_artist ON song_artist(artist_id);

-- ALIASES - to track other names of entites

-- Unified variant table: holds canonical and alias rows
CREATE TABLE IF NOT EXISTS song_alias (
  song_alias_id   INTEGER PRIMARY KEY,
  song_id      INTEGER NOT NULL,
  kind         TEXT NOT NULL CHECK (kind IN ('canonical','alias')),
  title        TEXT NOT NULL,           -- canonical title OR alias title
  performers   TEXT NOT NULL,           -- canonical performers OR alias performers
  source       TEXT,           -- optional metadata for alias provenance
  -- avoid exact duplicates for same song
  UNIQUE (song_id, kind, title, performers),
  FOREIGN KEY (song_id) REFERENCES song(song_id) ON DELETE CASCADE
);

-- FTS5 index that OUTSOURCES CONTENT to song_alias (only title+performers)
CREATE VIRTUAL TABLE IF NOT EXISTS song_fts USING fts5(
  title,
  performers,
  content = 'song_alias',
  content_rowid = 'song_alias_id',
  tokenize = "unicode61 remove_diacritics 1"
);

-- Keep FTS in sync

-- On canonical insert: create a 'canonical' alias and mirror to FTS
CREATE TRIGGER IF NOT EXISTS trg_song_ai_alias
AFTER INSERT ON song
FOR EACH ROW
BEGIN
  INSERT INTO song_alias (song_id, kind, title, performers)
  VALUES (NEW.song_id, 'canonical', NEW.song_title, NEW.song_performers);

  INSERT INTO song_fts(rowid, title, performers)
  VALUES (last_insert_rowid(), NEW.song_title, NEW.song_performers);
END;

-- On canonical update: refresh its alias + FTS
CREATE TRIGGER IF NOT EXISTS trg_song_au_alias
AFTER UPDATE ON song
FOR EACH ROW
BEGIN
  UPDATE song_alias
  SET title = NEW.song_title,
      performers = NEW.song_performers
  WHERE song_id = NEW.song_id AND kind = 'canonical';

  DELETE FROM song_fts
  WHERE rowid IN (
    SELECT song_alias_id FROM song_alias
    WHERE song_id = NEW.song_id AND kind = 'canonical'
  );
  INSERT INTO song_fts(rowid, title, performers)
  SELECT song_alias_id, title, performers
  FROM song_alias
  WHERE song_id = NEW.song_id AND kind = 'canonical';
END;

-- On canonical delete: remove all aliases + FTS
CREATE TRIGGER IF NOT EXISTS trg_song_ad_alias
AFTER DELETE ON song
FOR EACH ROW
BEGIN
  DELETE FROM song_fts
  WHERE rowid IN (
    SELECT song_alias_id FROM song_alias
    WHERE song_id = OLD.song_id
  );

  DELETE FROM song_alias
  WHERE song_id = OLD.song_id;
END;

-- If you add aliases directly to song_alias (kind='alias'):
-- Insert alias + mirror to FTS
CREATE TRIGGER IF NOT EXISTS trg_song_alias_ai_fts
AFTER INSERT ON song_alias
FOR EACH ROW
WHEN NEW.kind = 'alias'
BEGIN
  INSERT INTO song_fts(rowid, title, performers)
  VALUES (NEW.song_alias_id, NEW.title, NEW.performers);
END;

-- Update alias + refresh FTS
CREATE TRIGGER IF NOT EXISTS trg_song_alias_au_fts
AFTER UPDATE ON song_alias
FOR EACH ROW
WHEN NEW.kind = 'alias'
BEGIN
  DELETE FROM song_fts WHERE rowid = NEW.song_alias_id;
  INSERT INTO song_fts(rowid, title, performers)
  VALUES (NEW.song_alias_id, NEW.title, NEW.performers);
END;

-- Delete alias + remove from FTS
CREATE TRIGGER IF NOT EXISTS trg_song_alias_ad_fts
AFTER DELETE ON song_alias
FOR EACH ROW
WHEN OLD.kind = 'alias'
BEGIN
  DELETE FROM song_fts WHERE rowid = OLD.song_alias_id;
END;

-- Store all candidate matches per play for auditability and human review.
CREATE TABLE match_candidate (
  candidate_id     INTEGER PRIMARY KEY,
  play_id          INTEGER NOT NULL REFERENCES play(play_id) ON DELETE CASCADE,
  song_id          INTEGER REFERENCES song(song_id) ON DELETE SET NULL,
  candidate_score  REAL NOT NULL,               -- 0..100
  method           TEXT NOT NULL,               -- e.g., 'alias-fts','token-fuzzy','phonetic','exact'
  generated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE UNIQUE INDEX ux_candidate_play_song ON match_candidate(play_id, song_id);
CREATE INDEX idx_candidate_play ON match_candidate(play_id);
CREATE INDEX idx_candidate_song ON match_candidate(song_id);


-- Final mapping of a play to its canonical song
CREATE TABLE play_resolution (
  play_id        INTEGER PRIMARY KEY REFERENCES play(play_id) ON DELETE CASCADE,
  song_id        INTEGER NOT NULL REFERENCES song(song_id) ON DELETE RESTRICT,
  chosen_score   REAL,                         -- score of the chosen candidate
  status         TEXT NOT NULL CHECK (status IN ('pending','auto','human')) DEFAULT 'auto',
  decided_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  notes          TEXT
);

CREATE INDEX idx_resolution_song ON play_resolution(song_id);
CREATE INDEX idx_resolution_status ON play_resolution(status);
