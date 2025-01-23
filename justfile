set dotenv-load

default:
  just --list

last:
  @sqlite3 radio.sqlite3 -readonly -table "select * from radio_logs order by dtime desc limit 20;"

run:
  uv run --env-file .env do.py

year:
  @sqlite3 radio.sqlite3 -readonly -table "select radio, year, count(id) from radio_songs group by radio, year;"

checks:
  uv run check_song.py

cleandb:
  uv run clean_db.py

missings:
  uv run missing_song.py

sql_missing := '
SELECT COUNT(ss.id) as song_missing
FROM song_skipped as ss
LEFT JOIN song_matches as sm
ON sm.title = ss.title AND sm.artist = ss.artist
LEFT JOIN log_ignored as li
ON li.id = ss.id
WHERE sm.id IS NULL
AND li.id IS NULL;'

cmissing:
  @sqlite3 radio.sqlite3 -readonly -table "{{sql_missing}}"