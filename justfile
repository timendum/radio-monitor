set dotenv-load

default:
  just --list

run:
  @uv run --env-file .env do.py

checks:
  uv run check_song.py

resetdb:
  uv run reset_db.py

missings:
  uv run missing_song.py

sql_last := "
SELECT
    substr(p.observed_at,6,11) as \"at\",
    r.display_name as \"station\",
    coalesce(s.song_title, p.title_raw) as title,
    coalesce(s.song_performers, p.performer_raw) as performer,
    coalesce(pr.status, 'todo') AS resolution_status
FROM play AS p
LEFT JOIN play_resolution AS pr
    ON pr.play_id = p.play_id
LEFT JOIN song AS s
    ON s.song_id = pr.song_id
LEFT JOIN station AS r
    ON r.station_id = p.station_id
ORDER BY p.observed_at DESC
"

last:
  @sqlite3 radio.sqlite3 -readonly -table "{{sql_last}}"

cmissing:
  @sqlite3 radio.sqlite3 -readonly -table ""
