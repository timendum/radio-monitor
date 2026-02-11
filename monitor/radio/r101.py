from monitor import utils
from monitor.radio import virgin


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    performer, title, payload = virgin.parse(
        "https://www.r101.it/wp-json/mediaset-mediaplayer/v1/getStreamInfo",
        "http://icecast.unitedradio.it/r101",
    )
    return utils.insert_into_radio("101", performer, title, acquisition_id, None, payload)


if __name__ == "__main__":  # pragma: no cover
    print(main(utils.generate_batch("101_main")))
