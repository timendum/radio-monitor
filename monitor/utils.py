import re
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from onlymaps import Database, connect


@contextmanager
def conn_db(path="radio.sqlite3") -> Iterator[Database]:
    conn = connect(f"sqlite:///{path}")
    conn.open()
    try:
        yield conn
    finally:
        conn.close()

class RMError(Exception):
    pass

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
        lasts = conn.fetch_many(
            tuple[str, str, str],
            """
    SELECT observed_at, title_raw, performer_raw
    FROM play
    WHERE station_id = (SELECT station_id FROM station WHERE station_code = ?)
    ORDER BY ABS(strftime('%s', observed_at) - strftime('%s', ?))
    LIMIT 2
    """,
            radio,
            timestamp.isoformat(),
        )
        for _, t, p in lasts:
            if t == title and p == performer:
                # skip
                return radio, p, t

        # Insert
        conn.exec(
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
            radio,
            timestamp.isoformat(),
            title,
            performer,
            acquisition_id,
            payload,
        )
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


def __string_match(a: str, b: str) -> float:
    sm = SequenceMatcher(None, a, b)
    return sm.ratio()


JUNK = {"and", "feat", "feature"}


def __string_smart_diff(a: str, b: str) -> float:
    """Return the similarity between two strings based on set of words appearing in each."""
    a_words = set(re.split(r"\W+", a))
    b_words = set(re.split(r"\W+", b))
    a_diff = a_words - b_words - JUNK
    b_diff = b_words - a_words - JUNK
    return 1 - ((sum(map(len, a_diff)) + sum(map(len, b_diff))) / (len(a) + len(b)))


def __normalize(txt: str) -> str:
    return (
        unicodedata.normalize("NFKD", txt.strip()).encode("ascii", "ignore").decode("ascii").lower()
    )


def calc_score(otitle: str, operformer: str, title: str, performer: str) -> float:
    otitle, operformer, title, performer = (
        __normalize(otitle),
        __normalize(operformer),
        __normalize(title),
        __normalize(performer),
    )
    """Return a measure of similarity,
    1 if the title and performer are identical, and 0 if
    they have nothing in common."""
    if otitle == title and operformer == performer:
        return 1.0
    w_title = 1.0
    w_artist = 1.0
    w_concat = 2  # TBV
    rtitle = __string_match(title, otitle)
    rartist = __string_match(performer, operformer)
    rconcat = __string_smart_diff(title + " " + performer, otitle + " " + operformer)
    return min(
        (rtitle * w_title + rartist * w_artist + rconcat * w_concat)
        / (w_artist + w_title + w_concat),
        0.99,
    )


def print_ascii_table(data: list[list[Any]], head=-1) -> None:
    """Prints a list of lists as an ASCII table."""
    # Determine the width of each column
    col_widths = [max(len(str(item)) for item in col) for col in zip(*data, strict=False)]

    # Create the table margin
    margin = "+" + "+".join([f"{'':-<{width + 2}}" for width in col_widths]) + "+"

    # Create a format string for each row
    row_format = "| " + " | ".join([f"{{:<{width}}}" for width in col_widths]) + " |"

    # Print the table
    print(margin, flush=False)
    try:
        for i, row in enumerate(data):
            print(row_format.format(*row), flush=False)
            if i == head:
                print(margin, flush=True)
        print(margin, flush=True)
    except TypeError:
        print_ascii_table([[str(cell) for cell in row] for row in data])
