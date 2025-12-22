from monitor import utils
from monitor.radio import rtl


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    r = rtl.parse(
        "https://cloud.rtl.it/api-play.rtl.it/media/1.0/live/17/radiofreccia-radiovisione/-1/0/"
    )
    if r:
        return utils.insert_into_radio("freccia", r[0], r[1], acquisition_id)
    return None


if __name__ == "__main__":
    print(main(utils.generate_batch("freccia_main")))
