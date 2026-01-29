import httpx

from monitor import utils


def parse(url: str, stream: str) -> tuple[str, str, str]:
    r = httpx.get(url, params={"stream": stream})
    r.raise_for_status()
    d = r.json()
    try:
        return d["title"], d["artist"], r.text
    except KeyError:
        print(d)
        return "", "", ""


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    performer, title, payload = parse(
        "https://www.virginradio.it/wp-json/mediaset-mediaplayer/v1/getStreamInfo",
        "https://icy.unitedradio.it/Virgin.mp3",
    )
    return utils.insert_into_radio("vir", performer, title, acquisition_id, None, payload)


if __name__ == "__main__":
    print(main(utils.generate_batch("vir_main")))
