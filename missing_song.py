import sqlite3

from check_song import print_ascii_table
from spotify import Record, db_find, find_releases, get_token


def query_spotify(token: str) -> Record | None:
    title = input("Title (for spotify): ").strip()
    if not title:
        return None
    if title.lower() == "q":
        return None
    artist = input("Artist (for spotify): ").strip()
    if not artist:
        return None
    r = find_releases(title, artist, token)
    if not r:
        print(" -> Not found")
        return None
    print(" -> Found")
    print_ascii_table([[r.title, r.artist, r.year, r.country]])
    decision = input("Ok (Commit?): ").strip()
    if decision.lower == "ok" or decision.lower() in ("k", "o"):
        return r
    return None


def retry_spotify(title: str, artist: str, token: str) -> Record | None:
    r = find_releases(title, artist, token)
    if not r:
        print(" -> Not found")
        return None
    print(" -> Found")
    print_ascii_table([[r.title, r.artist, r.year, r.country]])
    decision = input("Ok (Commit?): ").strip()
    if decision.lower == "ok" or decision.lower() in ("k", "o"):
        return r
    return None


def ask_user() -> Record | None:
    title = input("Title (manual): ").strip()
    if not title:
        return None
    artist = input("Artist (manual): ").strip()
    if not artist:
        return None
    year = -1
    while year == -1:
        tyear = input("Year (manual): ").strip()
        if not tyear:
            return None
        try:
            year = int(tyear)
        except ValueError:
            continue
    country = input("Country (manual): ").strip().upper()
    if not country:
        return None
    return Record(year, country, title, artist, 1)


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    token = get_token()
    last_id = -1
    while True:
        to_check = conn.execute(
            """
            SELECT ss.id, ss.title, ss.artist
            FROM song_skipped as ss
            LEFT JOIN song_matches as sm
            ON sm.title = ss.title AND sm.artist = ss.artist
            LEFT JOIN log_ignored as li
            ON li.id = ss.id
            WHERE ss.id > ?
            AND sm.id IS NULL
            AND li.id IS NULL
            ORDER BY ss.id ASC
            LIMIT 10""",
            (last_id,),
        )
        for id, title, artist in to_check.fetchall():
            last_id = id
            if db_find(title, artist, conn) is not None:
                continue
            print(f"ID: {id}")
            print_ascii_table([[title, artist]])
            decision = input("Action (quit,retry,spotify,iGnore,enter): ").strip().lower()
            r = None
            match decision:
                case "q":
                    break
                case "r":
                    r = retry_spotify(title, artist, token)
                    if not r:
                        decision = input("Action (skip,enter): ").strip().lower()
                        match decision:
                            case "e":
                                r = ask_user()
                            case "i":
                                r = ask_user()
                            case _:
                                print(" -> Skipped!")
                                continue
                case "s":
                    r = query_spotify(token)
                    if not r:
                        last_id -= 1
                        continue
                case "e":
                    r = ask_user()
                case "i":
                    r = ask_user()
                case "g":
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO log_ignored
                        (id) values (?)""",
                        (id,),
                    )
                    conn.commit()

                case _:
                    print(" -> Skipped!")
                    continue
            if r:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO song_matches
                    (artist, title, okartist, oktitle, okyear, okcountry) values
                    (?,      ?,     ?,        ?,       ?,      ?)""",
                    (artist, title, r.artist, r.title, r.year, r.country),
                )
                conn.execute("DELETE FROM song_skipped WHERE id = ?", (id,))
                conn.commit()
                print(" -> Saved!")
        else:
            continue
        break


if __name__ == "__main__":
    main()
