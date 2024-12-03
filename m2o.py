import re

import requests

import utils


def parse(url: str) -> tuple[str, str]:
    r = requests.get(url)
    r.raise_for_status()
    d = r.json()
    m = re.match(r"^(.+?) ([^a-z]+)$", d["title"])
    return m.groups()[1], m.groups()[0]


def main() -> None | tuple[str, str, str]:
    author, title = parse(
        "https://www.m2o.it/api/pub/v2/all/gdwc-audio-player/onair?format=json"
    )
    return utils.insert_into_radio("m2o", author, title, None)


if __name__ == "__main__":
    print(main())
