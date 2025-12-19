from monitor import spotify
from monitor.radio import do


def main() -> None:
    do.main()

    try:
        spotify.main()
    except BaseException:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
