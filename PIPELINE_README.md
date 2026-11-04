# ETL Pipeline Guide

This project runs a four-stage ETL pipeline:

```text
P0 Raw Landing → P1 Extract → P2 Transform → P3 Datamart
```

The pipeline uses two SQL Server databases:

```text
Source files → lake_raw.raw → dwh_proj.staging → dwh_proj.dwh
             → dwh_proj.dmart → Dashboard
```

## Pipeline stages

### P0: Raw landing

**Code:** `src/raw/run.py`

P0 copies source files into the separate `lake_raw` database. It does not
validate or load staging.

```text
source files in `data/lake/instacart/` → lake_raw.raw.*
```

Run it with:

```powershell
python -m src.pipeline.run_pipeline --stage raw
```

### P1: Extract and prepare

**Code:** `src/extract/run.py`

P1 reads existing tables from `lake_raw.raw`, applies baseline cleanup, validates
the prepared data, and reloads the `staging` schema in `dwh_proj`.

```text
lake_raw.raw.* → dwh_proj.staging.stg_*
```

Run it with:

```powershell
python -m src.pipeline.run_pipeline --stage extract
```

Inspect its output:

```powershell
python -m src.tools.inspect_layers staging
```

### P2: Transform

**Code:** `src/transform/run.py`

P2 reads staging tables and creates the warehouse dimensions and fact table in
the `dwh` schema.

```text
staging.stg_* → dwh.dim_* and dwh.fact_*
```

Run it with:

```powershell
python -m src.transform.run
```

Inspect its output:

```powershell
python -m src.tools.inspect_layers dwh
```

### P3: Datamart

**Code:** `src/datamart/build.py`

P3 runs the SQL files in `sql/datamart/` in filename order and creates the
dashboard-facing summary tables in the `dmart` schema.

```text
dwh.dim_* and dwh.fact_* → dmart.mart_*
```

Run it with:

```powershell
python -m src.datamart.build
```

Inspect its output:

```powershell
python -m src.tools.inspect_layers dmart
```

## Run step by step

Run the stages in this order:

```powershell
python -m src.pipeline.run_pipeline --stage raw
python -m src.pipeline.run_pipeline --stage extract
python -m src.pipeline.run_pipeline --stage transform
python -m src.pipeline.run_pipeline --stage datamart
```

Each stage depends on the output of the previous stage:

```text
P0 must finish before P1.
P1 must finish before P2.
P2 must finish before P3.
```

If a stage fails, fix the problem and rerun that stage before continuing.

## Run through the API

Start the API:

```powershell
python main.py
```

Then call each stage separately.

### Run P0: raw landing

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/pipeline/run `
  -H "Content-Type: application/json" `
  -d '{\"stage\":\"raw\"}'
```

### Run P1: staging preparation

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/pipeline/run `
  -H "Content-Type: application/json" `
  -d '{\"stage\":\"extract\"}'
```

### Run P2

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/pipeline/run `
  -H "Content-Type: application/json" `
  -d '{\"stage\":\"transform\"}'
```

### Run P3

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/pipeline/run `
  -H "Content-Type: application/json" `
  -d '{\"stage\":\"datamart\"}'
```

The endpoint is implemented in `api/routes/operations.py` and calls
`run_stage()` in `api/services/pipeline.py`.

To run all four stages through the API:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/pipeline/run `
  -H "Content-Type: application/json" `
  -d '{\"stage\":\"all\"}'
```

## What happens internally

The API maps each requested stage to its module-level `run()` function:

```python
jobs = {
    PipelineStage.raw: p0.run,
    PipelineStage.extract: p1.run,
    PipelineStage.transform: p2.run,
    PipelineStage.datamart: p3.run,
}
```

For example:

```python
jobs[PipelineStage.extract]()
```

calls the `run()` function from `src/extract/run.py`.

When the requested stage is `all`, the API executes the functions in order:

```python
for job in (p0.run, p1.run, p2.run, p3.run):
    job()
```

This is equivalent to:

```python
p0.run()
p1.run()
p2.run()
p3.run()
```

## Verify the pipeline

Check database availability:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Check source data quality:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/quality
```

List tables and row counts through the API:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/layers
```

Or inspect a layer from the command line:

```powershell
python -m src.tools.inspect_layers staging
python -m src.tools.inspect_layers dwh
python -m src.tools.inspect_layers dmart
```

## Important notes

- The project uses SQL Server only.
- `lake_raw` contains the `raw` schema for source-preserving tables.
- `dwh_proj` contains the `staging`, `dwh`, and `dmart` schemas.
- P0 reads source files and writes to `lake_raw.raw`.
- P1 reads from `lake_raw.raw` and writes cleaned data to `dwh_proj.staging`.
- P2 reads from `staging` and writes to `dwh`.
- P3 reads from `dwh` and writes to `dmart`.
- Dashboard consumers should read from `dmart`.
- Each stage can be rerun after a failure.
