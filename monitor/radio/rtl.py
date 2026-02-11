import json
import subprocess

import httpx

from monitor import utils


def parse(url: str) -> None | tuple[str, str, str]:
    r = httpx.get(url)
    r.raise_for_status()
    playlist_url = r.json()["data"]["mediaInfo"]["uri"]

    ffprobe = [
        "ffprobe",
        "-v",
        "debug",
        "-print_format",
        "json",
        "-show_streams",
        playlist_url,
    ]

    result = subprocess.run(ffprobe, capture_output=True, text=True, check=True)

    txt = result.stdout
    metadata = json.loads(txt)

    songinfo = json.loads(metadata["streams"][0]["tags"]["TEXT"])["songInfo"]
    if "present" not in songinfo:
        return None

    present = songinfo["present"]
    if present["class"] != "Music":
        return None
    return present["mus_art_name"], present["mus_sng_title"], txt


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    r = parse("https://cloud.rtl.it/api-play.rtl.it/media/1.0/live/1/radiovisione/-1/0/")
    if r:
        performer, title, payload = r
        return utils.insert_into_radio("rtl", performer, title, acquisition_id, None, payload)
    return None


if __name__ == "__main__":  # pragma: no cover
    print(main(utils.generate_batch("rtl_main")))
