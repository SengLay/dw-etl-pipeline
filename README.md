# DFD Pipeline: Instacart sample

Source files → **lake_raw** → **P1** Extract & Prepare → **D1** Staging → **P2** Transform & Load → **D2** DWH (star schema) → **P3** Build Data Mart → **D3** D-Mart → Power BI.
Orchestrated by Airflow / ADF / cron.

```
Kaggle ─(landing)─▶ data/lake/instacart/*.csv
                          │ P0 (src/raw)                 raw landing
                          ▼
                   lake_raw.raw.*          raw source tables
                          │ P1 (src/extract) prepare + quality gate
                          ▼
                   dwh_proj.staging.stg_*  cleaned source-shaped data
                          │ P2 (src/transform)
                          ▼
                   dwh.dim_* / dwh.fact_*  D2  star schema
                          │ P3 (src/datamart + sql/datamart)
                          ▼
                   dmart.mart_*            D3  → Power BI
```

P0, P1, P2 and P3 never call each other; they communicate through database layers.
`lake_raw` is a separate SQL Server database; D1/D2/D3 are schemas
(`staging`, `dwh`, `dmart`) in `dwh_proj`.

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

The project uses SQL Server only. Install **ODBC Driver 17 or later for SQL
Server** and set the SQL Server connection settings in `.env`. The application
creates `lake_raw`, `dwh_proj`, and their schemas/tables automatically when the
configured account has permission to create databases.

Use one authentication mode:

```dotenv
# Windows authentication. The Windows account running VS Code must be a
# SQL Server login with access to DB_NAME and permission to create databases.
DB_TRUSTED=yes

# SQL Server authentication.
DB_TRUSTED=no
DB_USER=your_sql_login
DB_PASSWORD=your_sql_password
```

If Windows authentication reports `Login failed for user 'DOMAIN\\user'`,
grant that Windows login access in SQL Server, or switch to SQL Server
authentication. The account also needs permission to create schemas and
tables in the configured database.

## API

The maintainable FastAPI application is split into routes, services, schemas, and middleware:

```
main.py                 # local Uvicorn entrypoint
api/app.py              # application factory and lifecycle
api/routes/             # system, data, and pipeline endpoints
api/services/           # database and pipeline business logic
api/schemas.py          # request/response models
api/middleware.py       # request IDs, timing, and access logging
```

Start it with:

```bash
python main.py
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.
For VS Code debugging, open **Run and Debug**, select **Debug FastAPI**, and
press `F5`. Breakpoints will work in `api/routes/`, `api/services/`, and the
existing `src/` pipeline modules.
The API provides health checks, layer/table metadata, paginated read-only table
data, source quality checks, and pipeline stage execution:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Database health |
| GET | `/api/v1/layers` | Row counts for every layer |
| GET | `/api/v1/{layer}/tables` | Tables in `staging`, `dwh`, or `dmart` |
| GET | `/api/v1/{layer}/{table}` | Paginated table rows |
| GET | `/api/v1/quality` | Validate landed source data |
| POST | `/api/v1/pipeline/run` | Run `raw`, `extract`, `transform`, `datamart`, or `all` |

For example:

```bash
curl "http://127.0.0.1:8000/api/v1/dmart/mart_product_summary?limit=20"
curl -X POST http://127.0.0.1:8000/api/v1/pipeline/run ^
  -H "Content-Type: application/json" -d "{\"stage\":\"all\"}"
```

## Mock data -> CSV files -> pipeline

The mock generator is **separate from the pipeline**. It writes CSV files into
the landing folder. P0 lands those files into `lake_raw`; P1 then reads the
raw tables, prepares the data, and loads cleaned staging tables.

```
python -m src.tools.mock_data
python -m src.pipeline.run_pipeline --stage raw       # CSV -> lake_raw.raw
python -m src.pipeline.run_pipeline --stage extract   # lake_raw -> staging
python -m src.pipeline.run_pipeline --stage transform # staging -> dwh
python -m src.pipeline.run_pipeline --stage datamart  # dwh -> dmart
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
| 1 P0 to raw | `python -m src.pipeline.run_pipeline --stage raw` | Query `lake_raw.raw.*` |
| 2 P1 to D1 | `python -m src.pipeline.run_pipeline --stage extract` | `python -m src.tools.inspect_layers staging` |
| 3 P2 to D2 | `python -m src.pipeline.run_pipeline --stage transform` | `python -m src.tools.inspect_layers dwh` |
| 4 P3 to D3 | `python -m src.pipeline.run_pipeline --stage datamart` | `python -m src.tools.inspect_layers dmart` |
| All steps at once | `python -m src.pipeline.run_pipeline` | runs P0 through P3 |
| Automated | `pytest` | pipeline and quality tests |

Optional: `python -m src.tools.download_instacart` (needs `pip install kagglehub`) writes a real 1000-order sample into the same CSV folder.

## Adapting to your real data later

Only these places know about the data shape; the rest is generic:

1. CSV files in `data/lake/instacart/` (or update the raw landing source list)
2. `src/raw/run.py`: which source file feeds which raw table
3. `src/extract/registry.py`: which raw table feeds which staging table
4. `src/quality/checks.py`: rules and relationships
5. `src/warehouse/schema.py`, `src/transform/dimensions.py`, `facts.py`: star schema and mappings
6. `sql/datamart/*.sql` and the mart tables in `schema.py`

## Orchestration

- Airflow: `orchestration/airflow_dag.py` (`P0 >> P1 >> P2 >> P3`, every 30 min, 2 retries)
- cron: `orchestration/crontab.example`
- Plain loop: `python -m src.pipeline.run_pipeline --every 15`

Airflow and cron run P0 -> P3. P0 refreshes raw tables from the source files;
P1 can be rerun independently against the existing raw database.

## Failure and re-run behavior

- Quality checks run on **all** tables before anything is written; staging is reloaded in one transaction. A failed check leaves the previous staging data untouched.
- Dimensions: update-then-insert (SCD Type 1). Facts: delete by `order_id`, then insert. Marts: delete and rebuild. Every stage is safe to re-run.
- Facts with no matching dimension key raise an error instead of loading NULL keys.

## Layout

```
config/settings.py            env config, schema names
src/common/db.py              engine, init_db(), run_sql_file()
src/warehouse/schema.py       D2 + D3 table definitions
src/raw/                      P0 raw landing into lake_raw
src/extract/                  P1 (reads raw tables and prepares staging)
src/staging/loader.py         D1 reload
src/quality/checks.py         quality gate
src/transform/                P2 (dimensions, facts, dwh_loader)
src/datamart/build.py         P3 (runs sql/datamart/*.sql)
src/tools/                    download_instacart, fake_data, inspect_layers
src/extract/optional/         API + Kafka extractors (not used for Instacart)
orchestration/                Airflow DAG, crontab
tests/
```
