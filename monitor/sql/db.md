# Database  Documentation

## 1. `country`

**Purpose:**  
Stores ISO country codes and names.

**Relationships:**  
Referenced by `song.origin_country`.

| Column        | Type   | Description                                      |
|---------------|--------|--------------------------------------------------|
| `country_code`| TEXT   | Primary key. ISO 3166-1 alpha-2 code (e.g., `IT`, `US`). |
| `name`        | TEXT   | Country name (e.g., *Italy*, *United States*).  |

---

## 2. `station`

**Purpose:**  
Represents radio stations being monitored.

**Relationships:**  
Referenced by `play.station_id`.

| Column         | Type    | Description                                      |
|----------------|---------|--------------------------------------------------|
| `station_id`   | INTEGER | Primary key. Unique station identifier.          |
| `station_code` | TEXT    | Short unique code for the station.               |
| `display_name` | TEXT    | Full display name of the station.                |
| `active`       | INTEGER | 1 = active, 0 = inactive. CHECK constraint ensures only 0 or 1. |

**Indexes:**  

- `idx_station_country` (**unique**, for filtering by country if added later).

---

## 3. `play`

**Purpose:**  
Stores raw ingestion data from stations.

**Relationships:**

- `station_id` → `station.station_id`

| Column            | Type    | Description                                      |
|-------------------|---------|--------------------------------------------------|
| `play_id`         | INTEGER | Primary key. Unique play record.                |
| `station_id`      | INTEGER | FK to `station`. Station where the play occurred.|
| `observed_at`     | TEXT    | Timestamp in ISO8601 UTC format.                |
| `title_raw`       | TEXT    | Song title as captured from radio.              |
| `performer_raw`   | TEXT    | Performer name as captured from radio.          |
| `acquisition_id`  | TEXT    | Batch/job identifier for ingestion lineage.     |
| `source_payload`  | TEXT    | Optional raw JSON or metadata blob.             |
| `inserted_at`     | TEXT    | Auto timestamp when inserted.                   |

---

## 4. `artist`

**Purpose:**  
Canonical list of artists (normalized names).

**Relationships:**

- Linked to `song_artist` for many-to-many association with songs.

| Column        | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `artist_id`   | INTEGER | Primary key. Unique artist identifier.           |
| `artist_name` | TEXT    | Canonical artist name. Unique index enforced.    |

---

## 5. `song`

**Purpose:**  
Canonical representation of songs (title + performers) with enrichment attributes.

**Relationships:**

- Linked to `song_artist` for featured artists.
- Not enforced `origin_country` → `country.country_code`.

| Column             | Type    | Description                                      |
|--------------------|---------|--------------------------------------------------|
| `song_id`          | INTEGER | Primary key. Unique song identifier.            |
| `song_title`       | TEXT    | Canonical song title.                           |
| `song_performers`  | TEXT    | Canonical performers (main artist or combined string). |
| `isrc`             | TEXT    | Optional ISRC code for precise identification.  |
| `year`             | INTEGER | Year of release/origin. CHECK: 1900–2100.       |
| `country`          | TEXT    | Country of origin.                              |
| `duration`         | INTEGER | Duration in seconds. Must be ≥ 0 if present.    |

**Constraints:**

- `UNIQUE(song_title, song_performers)` prevents duplicates.
- CHECK constraints for year and duration.

---

## 6. `song_artist`

**Purpose:**  
Associates songs with multiple artists (featured, remixers, etc.).

**Relationships:**

- `song_id` → `song.song_id`
- `artist_id` → `artist.artist_id`

| Column      | Type    | Description                                      |
|-------------|---------|--------------------------------------------------|
| `song_id`   | INTEGER | FK to `song`.                                   |
| `artist_id` | INTEGER | FK to `artist`.                                 |

**Primary Key:**  
(`song_id`, `artist_id`) ensures uniqueness of association.

---

## 7. `song_alias`

**Purpose:**  
Stores songs and artits to support fuzzy matching and normalization.

Entries in table `song` are mirrored here by triggers.

**Relationships:**

- `song_id` refers to `song.song_id`.

| Column             | Type    | Description                                      |
|--------------------|---------|--------------------------------------------------|
| `song_alias_id`    | INTEGER | Primary key. Unique alias identifier.            |
| `song_id`          | INTEGER | FK to `song`.                                    |
| `kind`             | INTEGER | Kind of entry 'canonical' or 'alias'             |
| `title`            | TEXT    | Song title (see `song`).                         |
| `performers`       | TEXT    | Performers (see `song`).                         |
| `source`           | TEXT    | Optional note about alias origin.                |

**Constraints:**

- `UNIQUE(song_id, kind, title, performer)` prevents duplicate aliases.

---

## 8. `match_candidate`

**Purpose:**  
Stores all candidate matches for a play, useful for audit and human review.

| Column           | Type    | Description                                      |
|------------------|---------|--------------------------------------------------|
| `candidate_id`   | INTEGER | Primary key. Unique candidate identifier.        |
| `play_id`        | INTEGER | FK to `play`. The raw play being matched.        |
| `song_id`        | INTEGER | FK to `song`. Candidate song (nullable).         |
| `candidate_score`| REAL    | Score (0–100) indicating match confidence.       |
| `method`         | TEXT    | Matching method (e.g., `alias-fts`, `token-fuzzy`). |
| `generated_at`   | TEXT    | Timestamp when candidate was generated.          |

---

## 9. `play_resolution`

**Purpose:**  
Stores the final resolution of a play to a canonical song.

| Column         | Type    | Description                                      |
|----------------|---------|--------------------------------------------------|
| `play_id`      | INTEGER | Primary key. FK to `play`.                       |
| `song_id`      | INTEGER | FK to `song`. The chosen canonical song.         |
| `chosen_score` | REAL    | Score of the chosen candidate.                   |
| `status`       | TEXT    | Resolution status: `pending`, `auto`, `human`.   |
| `decided_by`   | TEXT    | Who decided (system or username).                |
| `decided_at`   | TEXT    | Timestamp of decision.                           |
| `notes`        | TEXT    | Optional notes for audit.                        |
