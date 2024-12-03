import db_init
import deejay
import r105
import radioairplay
import rds
import rtl
import virgin

if __name__ == "__main__":
    db_init.main()

    modules = [deejay, rds, rtl, r105, virgin, radioairplay]
    for modu in modules:
        try:
            modu.main()
        except BaseException:
            import traceback

            traceback.print_exc()
