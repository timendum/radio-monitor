import sqlite3


def main() -> None:
    conn = sqlite3.Connection("radio.sqlite3")
    aradios = conn.execute("SELECT DISTINCT radio FROM radio_logs").fetchall()
    to_delete = []
    for (radio,) in aradios:
        rows = conn.execute(
            "SELECT id, artist, title FROM radio_logs WHERE radio = ? ORDER BY dtime asc",
            (radio,),
        )
        pa, pt = "", ""
        for row in rows:
            id, na, nt = row
            if na == pa and nt == pt:
                to_delete.append(id)
            pa, pt = na, nt

    conn.executemany(
        "DELETE FROM radio_logs WHERE id = ?",
        [(id,) for id in to_delete],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
