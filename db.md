## Songs parsed and validated


| `radio_songs` | content |
|---------------|---------|
| id            | id from `radio_logs` |
| radio         | name of the radio |
| dtime         | unix timestamp of the song |
| artist        | normalized name of the artist |
| title         | normalized title of the song |
| okyear        | normalized year of the song | 
| okcountry     | normalized country code of the song |



## Song captured by scrapers

| `radio_logs` | content |
|--------------|---------|
| id           | id of the record |
| radio        | name of the radio |
| dtime        | unix timestamp of the song |
| artist       | captured name of the artist |
| title        | captured title of the song |


## Exact matches

Between captured song and normalized song infos.

| `song_matches` | content |
|----------------|---------|
| id             | id of the match |
| artist         | captured name of the artist |
| title          | captured title of the song |
| okartist       | normalized name of the artist |
| oktitle        | normalized title of the song |
| okyear         | normalized year of the song |
| okcountry      | normalized country code of the song |

Unique by `artist` and `title`.

## Songs to be checked

Songs with info, but we are not 100% sure.

| `song_check` | content |
|--------------|---------|
| id           | id of the record from `radio_songs` (so also from `radio_logs`) |


## Skipped songs

Songs without infos.

| `song_skipped` | content |
|----------------|---------|
| id             | id of the record |
| artist         | captured name of the artist | 
| title          | captured title of the song |

Unique by `artist` and `title`.

## Ignored songs

Song captured by scrapers and ignored.

| `log_ignored` | content |
|--------------|---------|
| id           | id of the record from `radio_logs` |
