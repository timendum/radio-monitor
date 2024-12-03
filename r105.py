import virgin
import utils


def main() -> None | tuple[str, str, str]:
    artist, title = virgin.parse(
        "https://www.105.net/custom_widget/finelco/getStreamInfo.jsp",
        "https://icy.unitedradio.it/Radio105.aac",
    )
    return utils.insert_into_radio("r105", artist, title, None)


if __name__ == "__main__":
    print(main())
