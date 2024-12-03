import m2o
import utils


def main() -> None | tuple[str, str, str]:
    author, title = m2o.parse(
        "https://www.capital.it/api/pub/v2/all/gdwc-audio-player/onair?format=json"
    )
    return utils.insert_into_radio("capital", author, title, None)


if __name__ == "__main__":
    print(main())
