# DFD Pipeline: Instacart sample

Data Lake → **P1** Extract → **D1** Staging → **P2** Transform & Load → **D2** DWH (star schema) → **P3** Build Data Mart → **D3** D-Mart → Power BI.
Orchestrated by Airflow / ADF / cron.

```
Kaggle ─(landing)─▶ data/lake/instacart/*.csv
                          │ P1 (src/extract)   quality gate: src/quality
                          ▼
                   staging.stg_*          D1  raw copy, truncate & reload
                          │ P2 (src/transform)
                          ▼
                   dwh.dim_* / dwh.fact_*  D2  star schema
                          │ P3 (src/datamart + sql/datamart)
                          ▼
                   dmart.mart_*            D3  → Power BI
```

P1, P2 and P3 never call each other; they only communicate through D1, D2 and D3.
D1/D2/D3 are three **schemas** (`staging`, `dwh`, `dmart`) in one SQL Server database.

## Data model

| Layer | Tables |
|---|---|
| D1 staging | `stg_orders`, `stg_order_products`, `stg_products`, `stg_aisles`, `stg_departments` (+ `_loaded_at`) |
| D2 dwh | `dim_user`, `dim_product` (with aisle + department), `dim_time` (day-of-week x hour, 168 rows), `fact_order_items` |
| D3 dmart | `mart_department_summary`, `mart_orders_by_time`, `mart_product_summary`, `mart_user_summary` |

Instacart has no calendar dates, so there is no `dim_date`; time is day-of-week + hour.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

The default backend is **SQLite** (zero setup). For SQL Server, install **ODBC Driver 18 for SQL Server**, create an empty database, and set `DB_BACKEND=mssql` plus the connection settings in `.env`. Schemas and tables are created automatically.

## Mock data -> CSV files -> pipeline

The mock generator is **separate from the pipeline**. It only writes CSV files into the data lake folder. P1 reads those files exactly as it would read real ones.

```
python -m src.tools.mock_data      ->  data/lake/instacart/*.csv   (the "Data Lake")
python -m src.pipeline.run_pipeline    P1 -> P2 -> P3 read from those files
```

| File | Columns |
|---|---|
| `orders.csv` | order_id, user_id, eval_set, order_number, order_dow, order_hour_of_day, days_since_prior_order |
| `order_products__prior.csv` | order_id, product_id, add_to_cart_order, reordered |
| `products.csv` | product_id, product_name, aisle_id, department_id |
| `aisles.csv` | aisle_id, aisle |
| `departments.csv` | department_id, department |

Size is set by `SAMPLE_ORDERS` in `.env` (default 1000) or `--orders N`. Replace the CSVs with real data later and nothing else changes.

## Test each step

| Step | Command | Check |
|---|---|---|
| 0 Mock data to CSV | `python -m src.tools.mock_data` | 5 CSVs in `data/lake/instacart/` |
| 1 P1 to D1 | `python -m src.pipeline.run_pipeline --stage extract` | `python -m src.tools.inspect_layers staging` |
| 2 P2 to D2 | `python -m src.pipeline.run_pipeline --stage transform` | `python -m src.tools.inspect_layers dwh` |
| 3 P3 to D3 | `python -m src.pipeline.run_pipeline --stage datamart` | `python -m src.tools.inspect_layers dmart` |
| All steps at once | `python -m src.tools.demo --reset` | prints row counts per layer |
| Automated | `pytest` | steps 0-3, re-run, bad-data test |

Optional: `python -m src.tools.download_instacart` (needs `pip install kagglehub`) writes a real 1000-order sample into the same CSV folder.

## Adapting to your real data later

Only these places know about the data shape; the rest is generic:

1. CSV files in `data/lake/instacart/` (or point `registry.py` at new files)
2. `src/extract/registry.py`: which file feeds which staging table
3. `src/quality/checks.py`: rules and relationships
4. `src/warehouse/schema.py`, `src/transform/dimensions.py`, `facts.py`: star schema and mappings
5. `sql/datamart/*.sql` and the mart tables in `schema.py`

## Orchestration

- Airflow: `orchestration/airflow_dag.py` (`P1 >> P2 >> P3`, every 30 min, 2 retries)
- cron: `orchestration/crontab.example`
- Plain loop: `python -m src.pipeline.run_pipeline --every 15`

Airflow and cron run P1 -> P3 against whatever is in the lake. Refreshing the lake itself (the landing step) is separate.

## Failure and re-run behavior

- Quality checks run on **all** tables before anything is written; staging is reloaded in one transaction. A failed check leaves the previous staging data untouched.
- Dimensions: update-then-insert (SCD Type 1). Facts: delete by `order_id`, then insert. Marts: delete and rebuild. Every stage is safe to re-run.
- Facts with no matching dimension key raise an error instead of loading NULL keys.

## Layout

```
config/settings.py            env config, schema names
src/common/db.py              engine, init_db(), run_sql_file()
src/warehouse/schema.py       D2 + D3 table definitions
src/extract/                  P1 (registry.py lists the sources)
src/staging/loader.py         D1 reload
src/quality/checks.py         quality gate
src/transform/                P2 (dimensions, facts, dwh_loader)
src/datamart/build.py         P3 (runs sql/datamart/*.sql)
src/tools/                    download_instacart, fake_data, inspect_layers
src/extract/optional/         API + Kafka extractors (not used for Instacart)
orchestration/                Airflow DAG, crontab
tests/
```
