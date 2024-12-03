import requests

import utils


def main() -> None | tuple[str, str, str]:
    r = requests.get(
        "https://www.r101.it/custom_widget/finelco/getStreamInfo.jsp",
        {
            "host": "http://icecast.unitedradio.it/r101",
        },
    )
    r.raise_for_status()
    d = r.json()
    return utils.insert_into_radio("r101", d["artist"], d["song"], None)


if __name__ == "__main__":
    print(main())
