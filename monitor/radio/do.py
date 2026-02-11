import httpx

from monitor import utils
from monitor.radio import capital, deejay, freccia, m2o, r101, r105, rds, rtl, virgin


def main() -> None:
    modules = [capital, deejay, freccia, m2o, r101, r105, rds, rtl, virgin]
    acquisition_id = utils.generate_batch("do")
    for module in modules:
        try:
            module.main(acquisition_id)
        except httpx.ReadTimeout:
            print(f"Radio {module.__name__} in timeout")
        except BaseException:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":  # pragma: no cover
    main()
