from datetime import datetime

import httpx

from monitor import utils


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    r = httpx.get("https://www.deejay.it/api/broadcast_airplay/?get=now")
    r.raise_for_status()
    d = r.json()["result"]
    timestamp = None
    try:
        timestamp = datetime.fromisoformat(d["datePlay"])
    except BaseException:
        pass
    return utils.insert_into_radio("dj", d["artist"], d["title"], acquisition_id, timestamp, r.text)


if __name__ == "__main__":
    print(main(utils.generate_batch("dj_main")))
