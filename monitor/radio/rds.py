from datetime import datetime

import httpx

from monitor import utils


def main(acquisition_id: str) -> None | tuple[str, str, str]:
    r = httpx.get("https://cdnapi.rds.it/v2/site/get_player_info")
    r.raise_for_status()
    d = r.json()["song_status"]["current_song"]
    if d["artist"] == "RDS":
        return ("RDS", "RDS", "None")
    timestamp = None
    try:
        timestamp = datetime.fromisoformat(d["mid"].split("#")[2])
    except BaseException:
        pass
    return utils.insert_into_radio(
        "rds", d["artist"], d["title"], acquisition_id, timestamp, r.text
    )


if __name__ == "__main__":  # pragma: no cover
    print(main(utils.generate_batch("rds_main")))
