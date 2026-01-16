from monitor import smatcher
from monitor.radio import do as radio


def main() -> None:
    radio.main()

    try:
        smatcher.main()
    except BaseException:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
