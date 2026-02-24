set dotenv-load

default:
  just --list

run:
  @uv run --env-file .env python -m monitor.do

sql:
  @sqlite3 radio.sqlite3

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

sql_count := "
WITH cdata AS (
  SELECT '0_total_plays' AS metric, COUNT(*) AS count FROM play
  UNION ALL
  SELECT '2_with_candidates', COUNT(DISTINCT p.play_id)
  FROM play p
  INNER JOIN match_candidate mc ON p.play_id = mc.play_id
  UNION ALL
  SELECT '3_to_check', COUNT(*)
  FROM play_resolution
  WHERE status = 'pending'
  UNION ALL
  SELECT '4_resolved', COUNT(*)
  FROM play_resolution
  WHERE status IN ('auto', 'human')
  UNION
  SELECT '8_songs', COUNT(*)
  FROM song
)
SELECT * from cdata
UNION
SELECT '1_todo_plays',
  (SELECT count FROM cdata WHERE metric = '0_total_plays') - 
  (SELECT count FROM cdata WHERE metric = '2_with_candidates')
UNION
SELECT '9_no_resolution',
  (SELECT count FROM cdata WHERE metric = '2_with_candidates') - 
  (SELECT count FROM cdata WHERE metric = '3_to_check') - 
  (SELECT count FROM cdata WHERE metric = '4_resolved')
ORDER BY metric
"

count:
  @sqlite3 radio.sqlite3 -readonly -table "{{sql_count}}"

spotify:
  @uv run --env-file .env python -m monitor.spotify

mb:
  @uv run --env-file .env python -m monitor.musicbrainz

test:
  uv run --env-file .env python -m unittest discover -s tests

pyfix:
  uvx ruff format .
  uvx ruff check  --fix .
  uvx ty check .

check:
  @uv run --env-file .env python -m monitor.check_song

dupes:
  @uv run --env-file .env python -m monitor.dupes

diff:
  @uv run --env-file .env python -m monitor.utils

clean:
  rm test_*.sqlite3