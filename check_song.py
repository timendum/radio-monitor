import sqlite3
from typing import Any

from spotify import db_find


def print_ascii_table(data: list[list[Any]]) -> None:
    """Prints a list of lists as an ASCII table."""
    # Determine the width of each column
    col_widths = [max(len(str(item)) for item in col) for col in zip(*data, strict=False)]

    # Create the table margin
    margin = "+" + "+".join([f"{'':-<{width+2}}" for width in col_widths]) + "+"

    # Create a format string for each row
    row_format = "| " + " | ".join([f"{{:<{width}}}" for width in col_widths]) + " |"

    # Print the table
    print(margin, flush=False)
    for row in data:
        print(row_format.format(*row), flush=False)
    print(margin, flush=True)


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    while True:
        to_check = conn.execute("""
            SELECT l.id, l.title, s.title, l.artist, s.artist, s.year, s.country
            FROM radio_logs l
            JOIN song_check c ON c.id = l.id
            JOIN radio_songs s ON s.id = l.id
            ORDER BY l.id ASC
            """).fetchall()
        if not to_check:
            break
        for id, ltitle, stitle, lartist, sartist, syear, scountry in to_check:
            if db_find(ltitle, lartist, conn) is not None:
                continue
            print(f"ID: {id}")
            print_ascii_table(
                [
                    ["v", "title", "artist", "year", "country"],
                    ["", ltitle, lartist, "", ""],
                    ["->", stitle, sartist, syear, scountry],
                ]
            )
            decision = input(
                "Decision (q to quit, id to save, -id to remove, other continue): "
            ).strip()
            try:
                newid = int(decision)
                if newid == id:
                    save_song_match(conn, id, ltitle, lartist)
                    continue
                if newid == -id:
                    remove_song(conn, id, ltitle, lartist)
                    continue
            except ValueError:
                pass
            if decision.lower() == "q":
                break
            print(" -> Skip")
        else:
            continue
        break
    conn.close()


def remove_song(conn, _, ltitle, lartist):
    conn.execute(
        "DELETE FROM song_check WHERE id IN ("
        + "SELECT id FROM radio_logs l WHERE l.title = ? AND l.artist = ?)",
        (ltitle, lartist),
    )
    conn.execute(
        "DELETE FROM radio_songs WHERE id IN ("
        + "SELECT id FROM radio_logs l WHERE l.title = ? AND l.artist = ?)",
        (ltitle, lartist),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO song_skipped
        (artist, title) VALUES
        (?,      ?)""",
        (lartist, ltitle),
    )
    conn.commit()
    print(" -> Deleted")


def save_song_match(conn, id, ltitle, lartist):
    conn.execute(
        """
        INSERT OR IGNORE INTO song_matches
            (artist,  title,   okartist, oktitle, okyear, okcountry)
        SELECT
            l.artist, l.title, s.artist, s.title, s.year, s.country
        FROM radio_logs l
        JOIN song_check c ON c.id = l.id
        JOIN radio_songs s ON s.id = l.id
        WHERE l.id = ?""",
        (id,),
    )
    conn.execute(
        "DELETE FROM song_check WHERE id IN ("
        + "SELECT id FROM radio_logs l WHERE l.title = ? AND l.artist = ?)",
        (ltitle, lartist),
    )
    print(" -> Saved!")
    conn.commit()


if __name__ == "__main__":
    main()
