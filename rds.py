import requests

import utils


def main() -> None:
    r = requests.get("https://cdnapi.rds.it/v2/site/get_player_info")
    r.raise_for_status()
    d = r.json()["song_status"]["current_song"]
    print(d)
    if d["artist"] == "RDS":
        return
    utils.insert_into_radio("rds", d["artist"], d["title"], None)


if __name__ == "__main__":
    main()
