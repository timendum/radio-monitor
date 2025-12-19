from monitor import utils
from monitor.radio import capital, deejay, m2o, r101, r105, rds, rtl, virgin


def main() -> None:
    modules = [capital, deejay, m2o, r101, r105, rds, rtl, virgin]
    acquisition_id = utils.generate_batch("do")
    for modu in modules:
        try:
            modu.main(acquisition_id)
        except BaseException:
            import traceback

            traceback.print_exc()

if __name__ == "__main__":
    main()
