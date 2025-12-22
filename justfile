set dotenv-load

default:
  just --list

run:
  @uv run --env-file .env python -m monitor.do

resetdb:
  uv run --env-file .env python -m monitor.reset_db

sql_last := "
WITH ranked AS (
  SELECT
      substr(p.observed_at, 6, 11)                    AS \"at\",
      r.display_name                                  AS \"station\",
      substr(coalesce(s.song_title, p.title_raw), 1, 25)     AS title,
      substr(coalesce(s.song_performers, p.performer_raw), 1, 25) AS performer,
      coalesce(pr.status, 'todo')                     AS resolution_status,
      p.observed_at,
      ROW_NUMBER() OVER (
        PARTITION BY p.station_id
        ORDER BY p.observed_at DESC
      ) AS rn
  FROM play AS p
  LEFT JOIN play_resolution AS pr
    ON pr.play_id = p.play_id
  LEFT JOIN song AS s
    ON s.song_id = pr.song_id
  LEFT JOIN station AS r
    ON r.station_id = p.station_id
)
SELECT
    at, station, title, performer, resolution_status
FROM ranked
WHERE rn <= 2
ORDER BY observed_at DESC
"

last:
  @sqlite3 radio.sqlite3 -readonly -table "{{sql_last}}"

spotify:
  @uv run --env-file .env python -m monitor.spotify

mb:
  @uv run --env-file .env python -m monitor.musicbrainz

test:
  uv run --env-file .env python -m unittest discover -s tests