import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any


def conn_db() -> sqlite3.Connection:
    return sqlite3.Connection("radio.sqlite3")


def insert_into_radio(
    radio: str,
    performer: str,
    title: str,
    acquisition_id: str,
    timestamp: None | datetime = None,
    payload="",
) -> None | tuple[str, str, str]:
    """Insert a new play into the radio database"""
    performer = performer.strip()
    title = title.strip()
    if not performer and not title:
        return None
    with conn_db() as conn:
        if not timestamp:
            timestamp = datetime.now()
        # Avoid duplicates
        lasts = (
            conn.execute(
                """
    SELECT observed_at, title_raw, performer_raw
    FROM play
    WHERE station_id = (SELECT station_id FROM station WHERE station_code = ?)
    ORDER BY ABS(strftime('%s', observed_at) - strftime('%s', ?))
    LIMIT 2
    """,
                (radio, timestamp.isoformat()),
            ).fetchall()
            or ()
        )
        for _, t, p in lasts:
            if t == title and p == performer:
                # skip
                return radio, p, t

        # Insert
        conn.execute(
            """INSERT INTO play (
                station_id,
                observed_at,
                title_raw,
                performer_raw,
                acquisition_id,
                source_payload
            ) VALUES (
                (SELECT station_id FROM station WHERE station_code = ?),
                ?,
                ?,
                ?,
                ?,
                ?)""",
            (radio, timestamp.isoformat(), title, performer, acquisition_id, payload),
        )
        conn.commit()
        return radio, performer, title


def generate_batch(prefix="test", time: None | datetime = None) -> str:
    time = time or datetime.now()
    return f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}"


def clear_artist(artist: str) -> str:
    # get only the first artist in a list
    artist = artist.lower()
    for sep in (",", "&", " ft", " feat", " e ", " and "):
        if sep in artist:
            artist = artist[: artist.index(sep)].strip()
    return artist


def clear_title(title: str) -> str:
    # get only the first artist in a list
    for sep in ("(", " - "):
        if sep in title and title.index(sep) > 2:
            title = title[: title.index(sep)].strip()
    return title


def calc_score(otitle: str, operformer: str, title: str, performer: str) -> float:
    otitle, operformer, title, performer = (
        otitle.lower().strip(),
        operformer.lower().strip(),
        title.lower().strip(),
        performer.lower().strip(),
    )
    """Return a measure of similarity,
    1 if the title and performer are identical, and 0 if
    they have nothing in common."""
    # oartist, artist = clear_artist(oartist), clear_artist(artist)
    # otitle, title = clear_title(otitle), clear_title(title)
    # try:
    #     title = title[: title.index("(")].strip()
    # except BaseException:
    #     pass
    rtitle = SequenceMatcher(None, title, otitle).ratio()
    rartist = SequenceMatcher(None, performer, operformer).ratio()
    return (rtitle + rartist) / 2


def print_ascii_table(data: list[list[Any]]) -> None:
    """Prints a list of lists as an ASCII table."""
    # Determine the width of each column
    col_widths = [max(len(str(item)) for item in col) for col in zip(*data, strict=False)]

    # Create the table margin
    margin = "+" + "+".join([f"{'':-<{width + 2}}" for width in col_widths]) + "+"

    # Create a format string for each row
    row_format = "| " + " | ".join([f"{{:<{width}}}" for width in col_widths]) + " |"

    # Print the table
    print(margin, flush=False)
    for row in data:
        print(row_format.format(*row), flush=False)
    print(margin, flush=True)
