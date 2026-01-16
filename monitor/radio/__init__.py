from monitor import utils
from monitor.radio import capital, deejay, m2o, r101, r105, rds, rtl, virgin

if __name__ == "__main__":
    # modules = [deejay, rds, rtl, r105, virgin, r101, m2o, capital, spotify]
    modules = [capital, deejay, m2o, r101, r105, rds, rtl, virgin]
    acquisition_id = utils.generate_batch("do")
    for modu in modules:
        try:
            modu.main(acquisition_id)
        except BaseException:
            import traceback

            traceback.print_exc()
