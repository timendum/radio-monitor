from datetime import datetime

import requests

import utils


def main() -> None:
    r = requests.get("https://www.deejay.it/api/broadcast_airplay/?get=now")
    r.raise_for_status()
    d = r.json()["result"]
    timestamp = None
    try:
        timestamp = datetime.fromisoformat(d["datePlay"]).timestamp()
    except BaseException:
        pass
    utils.insert_into_radio("deejay", d["artist"], d["title"], timestamp)


if __name__ == "__main__":
    main()
