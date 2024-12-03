import requests

import utils


def parse(url: str, host: str) -> tuple[str, str]:
    r = requests.get(url, {"host": host})
    r.raise_for_status()
    d = r.json()
    return d["artist"], d["song"]


def main() -> None | tuple[str, str, str]:
    artist, title = parse(
        "https://www.virginradio.it/custom_widget/finelco/getStreamInfo.jsp?",
        "https://icy.unitedradio.it/Virgin.mp3",
    )
    return utils.insert_into_radio("virgin", artist, title, None)


if __name__ == "__main__":
    print(main())
