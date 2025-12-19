import rtl
import utils


def main() -> None | tuple[str, str, str]:
    r = rtl.parse(
        "https://cloud.rtl.it/api-play.rtl.it/media/1.0/live/17/radiofreccia-radiovisione/-1/0/"
    )
    if r:
        return utils.insert_into_radio("freccia", r[0], r[1], None)
    return None


if __name__ == "__main__":
    print(main())
