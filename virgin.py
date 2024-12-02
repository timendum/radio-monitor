import requests

import utils


def main() -> None:
    r = requests.get(
        "https://www.virginradio.it/custom_widget/finelco/getStreamInfo.jsp?",
        {
            "host": "https://icy.unitedradio.it/Virgin.mp3",
        },
    )
    r.raise_for_status()
    d = r.json()
    utils.insert_into_radio("virgin", d["artist"], d["song"], None)


if __name__ == "__main__":
    main()
