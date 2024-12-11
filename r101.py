import utils
import virgin


def main() -> None | tuple[str, str, str]:
    artist, title = virgin.parse(
        "https://www.r101.it/custom_widget/finelco/getStreamInfo.jsp",
        "http://icecast.unitedradio.it/r101",
    )
    return utils.insert_into_radio("r101", artist, title, None)


if __name__ == "__main__":
    print(main())
