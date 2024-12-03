import requests

import utils


def main() -> None | tuple[str, str, str]:
    r = requests.get(
        "https://www.105.net/custom_widget/finelco/getStreamInfo.jsp",
        {
            "host": "https://icy.unitedradio.it/Radio105.aac",
        },
    )
    r.raise_for_status()
    d = r.json()
    return utils.insert_into_radio("r105", d["artist"], d["song"], None)


if __name__ == "__main__":
    print(main())
