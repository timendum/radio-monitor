from check_song import print_ascii_table
from spotify import find_releases, get_token


def main():
    token = get_token()
    while True:
        title = input("Title (or q): ").strip()
        if not title:
            continue
        if title.lower() == "q":
            break
        artist = input("Artist: ").strip()
        if not artist:
            continue
        r = find_releases(title, artist, token)
        if not r:
            print(" -> Not found")
            continue
        print(" -> Found")
        print_ascii_table([[r.title, r.artist, r.year, r.country]])


if __name__ == "__main__":
    main()
