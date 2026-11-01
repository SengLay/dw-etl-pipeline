"""Each pipeline step tested in order (tests run top to bottom, each builds on the last)."""
import pandas as pd
import pytest
from sqlalchemy import text

from src.common.db import get_engine
from src.datamart import build as p3
from src.extract import run as p1
from src.tools import mock_data
from src.transform import run as p2


def count(table: str) -> int:
    with get_engine().connect() as c:
        return c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


@pytest.fixture(scope="module", autouse=True)
def landed():
    mock_data.generate(n_orders=1000)


def test_step0_landing_files():
    from config.settings import settings
    from pathlib import Path
    names = {p.name for p in (Path(settings.lake_path) / "instacart").glob("*.csv")}
    assert names == {"orders.csv", "order_products__prior.csv", "products.csv",
                     "aisles.csv", "departments.csv"}


def test_step1_p1_extract_to_staging():
    p1.run()
    assert count("staging.stg_orders") == 1000
    assert count("staging.stg_products") == 300
    assert count("staging.stg_order_products") > 1000


def test_step2_p2_transform_to_dwh():
    p2.run()
    assert count("dwh.dim_time") == 168
    assert count("dwh.dim_user") == 100
    assert count("dwh.dim_product") == 300
    assert count("dwh.fact_order_items") == count("staging.stg_order_products")


def test_step3_p3_datamart():
    p3.run()
    assert count("dmart.mart_department_summary") == 6
    assert count("dmart.mart_user_summary") == 100
    assert count("dmart.mart_orders_by_time") > 0
    with get_engine().connect() as c:
        total = c.execute(text("SELECT SUM(items_sold) FROM dmart.mart_department_summary")).scalar()
    assert total == count("dwh.fact_order_items")      # mart reconciles with DWH


def test_rerun_is_idempotent():
    before = (count("dwh.fact_order_items"), count("dwh.dim_product"), count("dmart.mart_user_summary"))
    p1.run(); p2.run(); p3.run()
    assert before == (count("dwh.fact_order_items"), count("dwh.dim_product"), count("dmart.mart_user_summary"))


def test_bad_data_keeps_old_staging(tmp_path):
    """A failed quality check must not touch staging."""
    from config.settings import settings
    from pathlib import Path
    from src.quality.checks import DataQualityError
    orders = Path(settings.lake_path) / "instacart" / "orders.csv"
    df = pd.read_csv(orders)
    df.loc[0, "order_hour_of_day"] = 99
    df.to_csv(orders, index=False)
    with pytest.raises(DataQualityError):
        p1.run()
    assert count("staging.stg_orders") == 1000
