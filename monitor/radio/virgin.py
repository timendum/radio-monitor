import httpx

from monitor import utils


def parse(url: str, host: str) -> tuple[str, str, str]:
    r = httpx.get(url, params={"host": host})
    r.raise_for_status()
    d = r.json()
    return d["artist"], d["song"], r.text


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    performer, title, payload = parse(
        "https://www.virginradio.it/custom_widget/finelco/getStreamInfo.jsp?",
        "https://icy.unitedradio.it/Virgin.mp3",
    )
    return utils.insert_into_radio("vir", performer, title, acquisition_id, None, payload)


if __name__ == "__main__":
    print(main(utils.generate_batch("vir_main")))
