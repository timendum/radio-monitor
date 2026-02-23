from monitor import smatcher
from monitor.radio import do as radio
from monitor.utils import RMError


def main() -> None:
    radio.main()

    try:
        smatcher.main()
    except RMError as e:
        print(e)
    except BaseException:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
