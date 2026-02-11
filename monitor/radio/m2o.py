import httpx

from monitor import utils


def parse(url: str) -> tuple[str, str, str]:
    r = httpx.get(url)
    r.raise_for_status()
    d = r.json()
    title, author = split_song(d["title"])
    return author, title, r.text


def split_song(txt: str):
    for i in range(len(txt)):
        if not txt[i].isspace():
            continue
        # all[i] is a space
        if all((not c.isalpha() or not c.islower()) for c in txt[i:]):
            # after i all chars are not a letter or are not lowercase
            return txt[:i], txt[i + 1 :]
    raise ValueError(f"Not split: {txt}")


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    author, title, payload = parse(
        "https://www.m2o.it/api/pub/v2/all/gdwc-audio-player/onair?format=json"
    )
    return utils.insert_into_radio("m2o", author, title, acquisition_id, None, payload)


if __name__ == "__main__":  # pragma: no cover
    print(main(utils.generate_batch("m2o_main")))
