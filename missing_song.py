import sqlite3

from check_song import print_ascii_table
from spotify import find_releases, get_token


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    token = get_token()
    last_id = -1
    while True:
        to_check = conn.execute(
            """
        select id, title, artist
    from song_skipped
    where id > ?
    order by id asc
    limit 10""",
            (last_id,),
        )
        for id, title, artist in to_check.fetchall():
            last_id = id
            print(f"ID: {id}")
            print_ascii_table([[title, artist]])
            ntitle = input("Title (or q): ").strip()
            if not ntitle:
                continue
            if ntitle.lower() == "s":
                stitle = input("Title (for spotify): ").strip()
                if not stitle:
                    continue
                if stitle.lower() == "q":
                    break
                sartist = input("Artist (for spotify): ").strip()
                if not sartist:
                    continue
                r = find_releases(stitle, sartist, token)
                if not r:
                    print(" -> Not found")
                    continue
                print(" -> Found")
                print_ascii_table([[r.title, r.artist, r.year, r.country]])
                decision = input("Ok (Commit?): ").strip()
                if decision.lower == "ok" or decision.lower() == "k":
                    conn.execute(
                        """
        insert or ignore into song_matches
            (artist, title, okartist, oktitle, okyear, okcountry) values
            (?,      ?,     ?,        ?,       ?,      ?)""",
                        (artist, title, r.artist, r.title, r.year, r.country),
                    )
                    conn.execute("delete from song_skipped where id = ?", (id,))
                    conn.commit()
                    print(" -> Saved!")
            else:
                if ntitle.lower() == "q":
                    break
                nartist = input("Artist: ").strip()
                if not nartist:
                    continue
                nyear = -1
                while nyear == -1:
                    tyear = input("Year: ").strip()
                    if not tyear:
                        continue
                    try:
                        nyear = int(tyear)
                    except ValueError:
                        continue
                ncountry = input("Country: ").strip().upper()
                if not ncountry:
                    continue
                conn.execute(
                    """
    insert or ignore into song_matches
        (artist, title, okartist, oktitle, okyear, okcountry) values
        (?,      ?,     ?,        ?,       ?,      ?)""",
                    (artist, title, nartist, ntitle, nyear, ncountry),
                )
                conn.execute("delete from song_skipped where id = ?", (id,))
                conn.commit()
                print(" -> Saved!")
        else:
            continue
        break


if __name__ == "__main__":
    main()
