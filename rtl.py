import json
import subprocess


import requests

import utils


def parse(url: str) -> None | tuple[str, str]:
    r = requests.get(url)
    r.raise_for_status()
    playlist_url = r.json()["data"]["mediaInfo"]["uri"]

    ffprobe = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        playlist_url,
    ]

    result = subprocess.run(
        ffprobe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    metadata = json.loads(result.stdout)

    songInfo = json.loads(metadata["streams"][0]["tags"]["TEXT"])["songInfo"]
    if "present" not in songInfo:
        return

    present = songInfo["present"]
    if present["class"] != "Music":
        return
    return present["mus_art_name"], present["mus_sng_title"]


def main() -> None | tuple[str, str, str]:
    r = parse(
        "https://cloud.rtl.it/api-play.rtl.it/media/1.0/live/1/radiovisione/-1/0/"
    )
    if r:
        return utils.insert_into_radio("rtl", r[0], r[1], None)
    return None


if __name__ == "__main__":
    print(main())
