import sqlite3
from typing import Any


def print_ascii_table(data: list[list[Any]]) -> None:
    # Determine the width of each column
    col_widths = [max(len(str(item)) for item in col) for col in zip(*data, strict=False)]

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
        select l.id, l.title, s.title, l.artist, s.artist, s.year, s.country
    from radio_logs l
    join song_check c
        on c.id = l.id
    join radio_songs s
        ON s.id = l.id
    order by l.id asc
    limit 10""")
        for id, ltitle, stitle, lartist, sartist, syear, scountry in to_check.fetchall():
            print(f"ID: {id}")
            print_ascii_table(
                [
                    ["v", "title", "artist", "year", "country"],
                    ["", ltitle, lartist, "", ""],
                    ["->", stitle, sartist, syear, scountry],
                ]
            )
            decision = input("Decision: ").strip()
            try:
                newid = int(decision)
                if newid == id:
                    conn.execute(
                        """
insert or ignore into song_matches
    (artist, title, okartist, oktitle, okyear, okcountry)
select
    l.artist, l.title, s.artist, s.title, s.year, s.country
from radio_logs l
join song_check c
    on c.id = l.id
join radio_songs s
    ON s.id = l.id
where l.id = ?""",
                        (id,),
                    )
                    print(" -> Saved!")
                    conn.execute("delete from song_check where id = ?", (id,))
                    continue
                if newid == -id:
                    conn.execute("delete from song_check where id = ?", (id,))
                    conn.execute("delete from radio_songs where id = ?", (id,))
                    conn.execute(
                        """
                    INSERT OR IGNORE INTO song_skipped
                        (artist, title) VALUES
                        (?,      ?)""",
                        (lartist, ltitle),
                    )
                    print(" -> Deleted")
                    continue
            except ValueError:
                pass
            if decision.lower() == "q":
                break
            print(" -> Skip")
        else:
            conn.commit()
            continue
        break
    conn.commit()


if __name__ == "__main__":
    main()
