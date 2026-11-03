# ETL Pipeline Guide

This project runs a three-stage ETL pipeline:

```text
P1 Extract → P2 Transform → P3 Datamart
```

All stages use the same SQL Server database, with a separate schema for each
data layer:

```text
Data Lake → staging → dwh → dmart → Dashboard
```

## Pipeline stages

### P1: Extract

**Code:** `src/extract/run.py`

P1 reads raw CSV files from the data lake, validates the extracted data, and
reloads the `staging` schema.

```text
data/lake/instacart/*.csv → staging.stg_*
```

Run it with:

```powershell
python -m src.extract.run
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
python -m src.extract.run
python -m src.transform.run
python -m src.datamart.build
```

Each stage depends on the output of the previous stage:

```text
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

### Run P1

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

To run all three stages through the API:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/pipeline/run `
  -H "Content-Type: application/json" `
  -d '{\"stage\":\"all\"}'
```

## What happens internally

The API maps each requested stage to its module-level `run()` function:

```python
jobs = {
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
for job in (p1.run, p2.run, p3.run):
    job()
```

This is equivalent to:

```python
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
- The database has three schemas: `staging`, `dwh`, and `dmart`.
- P1 reads from the data lake and writes to `staging`.
- P2 reads from `staging` and writes to `dwh`.
- P3 reads from `dwh` and writes to `dmart`.
- Dashboard consumers should read from `dmart`.
- Each stage can be rerun after a failure.
