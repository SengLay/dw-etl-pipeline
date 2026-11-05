"""P2: D1 Staging -> D2 DWH (dimensions first, then facts)."""
from src.database.connection import init_db
from src.common.logger import get_logger
from src.transform import dimensions, facts

log = get_logger("P2.transform_load")


def run() -> None:
    init_db()
    dimensions.build_dim_time()
    dimensions.build_dim_user()
    dimensions.build_dim_product()
    log.info("Dimensions loaded")
    facts.build_fact_order_items()


if __name__ == "__main__":
    run()
