import capital
import db_init
import deejay
import m2o
import r101
import r105
import radioairplay
import rds
import rtl
import spotify
import virgin

if __name__ == "__main__":
    db_init.main()

    modules = [deejay, rds, rtl, r105, virgin, r101, m2o, capital, radioairplay, spotify]
    for modu in modules:
        try:
            modu.main()
        except BaseException:
            import traceback

            traceback.print_exc()
