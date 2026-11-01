import pandas as pd
import pytest

from src.quality.checks import DataQualityError, run_staging_checks


def test_passes_clean_data():
    run_staging_checks({"stg_aisles": pd.DataFrame({"aisle_id": [1, 2], "aisle": ["a", "b"]})})


def test_fails_on_duplicates():
    with pytest.raises(DataQualityError, match="duplicates"):
        run_staging_checks({"stg_aisles": pd.DataFrame({"aisle_id": [1, 1], "aisle": ["a", "b"]})})


def test_fails_on_out_of_range_hour():
    orders = pd.DataFrame({"order_id": [1], "user_id": [1], "order_number": [1],
                           "order_dow": [0], "order_hour_of_day": [25]})
    with pytest.raises(DataQualityError, match="outside"):
        run_staging_checks({"stg_orders": orders})


def test_fails_on_orphan_items():
    frames = {
        "stg_orders": pd.DataFrame({"order_id": [1], "user_id": [1], "order_number": [1],
                                    "order_dow": [0], "order_hour_of_day": [5]}),
        "stg_order_products": pd.DataFrame({"order_id": [1, 99], "product_id": [1, 1],
                                            "add_to_cart_order": [1, 2], "reordered": [0, 1]}),
    }
    with pytest.raises(DataQualityError, match="without a match"):
        run_staging_checks(frames)


def test_fails_on_empty():
    with pytest.raises(DataQualityError):
        run_staging_checks({"stg_orders": pd.DataFrame()})
