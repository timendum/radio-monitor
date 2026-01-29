from monitor import utils
from monitor.radio import virgin


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    performer, title, payload = virgin.parse(
        "https://www.105.net/wp-json/mediaset-mediaplayer/v1/getStreamInfo",
        "https://icy.unitedradio.it/Radio105.aac",
    )
    return utils.insert_into_radio("105", performer, title, acquisition_id, None, payload)


if __name__ == "__main__":
    print(main(utils.generate_batch("105_main")))
