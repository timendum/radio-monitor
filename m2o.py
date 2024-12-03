import re

import requests

import utils


def main() -> None | tuple[str, str, str]:
    r = requests.get(
        "https://www.m2o.it/api/pub/v2/all/gdwc-audio-player/onair?format=json"
    )
    r.raise_for_status()
    d = r.json()
    m = re.match(r"^(.+?) ([^a-z]+)$", d["title"])
    return utils.insert_into_radio("m2o", m.groups()[1], m.groups()[0], None)


if __name__ == "__main__":
    print(main())
