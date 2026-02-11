from monitor import utils
from monitor.radio import m2o


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    author, title, payload = m2o.parse(
        "https://www.capital.it/api/pub/v2/all/gdwc-audio-player/onair?format=json"
    )
    return utils.insert_into_radio("cap", author, title, acquisition_id, None, payload)


if __name__ == "__main__":  # pragma: no cover
    print(main(utils.generate_batch("capitalmain")))
